#!/usr/bin/env bash
# La scena centrale del talk: un nodo se ne va e il cluster se ne accorge.
#
#   ./tools/failover-replicaset.sh spegni     # docker kill sul primario
#   ./tools/failover-replicaset.sh termina    # il processo esce da sé (shutdown)
#
# DUE scene, non una, e la differenza è il contenuto della slide (ADR-0034, ADR-0044).
#
#   spegni   `docker kill` manda SIGKILL. Nessuno avvisa nessuno: i superstiti se ne
#            accorgono subito — «Member is now in state DOWN», connessione rifiutata —
#            ma non possono eleggere finché non scade `electionTimeoutMillis`, che vale
#            10 000 ms. Misurato: ~10 secondi. E il container resta giù: per il demone
#            un `docker kill` è una fermata voluta da un umano, quindi
#            `restart: unless-stopped` non lo rialza (V-017, V-029).
#
#   termina  Il primario esegue `shutdownServer()`: cede il ruolo e lo dice. Nessuno
#            aspetta un timeout. Misurato: ~0,5 secondi, venti volte più veloce. E qui
#            sì che il container torna su da solo, con `RestartCount` che avanza.
#
# La frase da dire ad alta voce mentre si esegue «spegni» è «sto spegnendo un nodo»,
# NON «sto simulando un crash»: è il punto 1 di ADR-0034, ed è la ragione per cui
# questo script stampa da sé la differenza invece di lasciarla alla memoria di chi parla.
#
# Lo script CRONOMETRA quello che fa: i numeri sullo schermo sono di quella esecuzione,
# non quelli scritti nelle slide. Se in sala l'elezione dura il doppio, si vede.
set -uo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="${RADICE}/docker/02-replicaset/compose.yaml"
AMBIENTE="${RADICE}/tools/images.env"
SEGRETI="${RADICE}/docker/02-replicaset/.env"

LIMITE_ATTESA=120   # secondi prima di dichiarare che l'elezione non è avvenuta

if [[ -t 1 ]]; then
  VERDE=$'\033[32m'; ROSSO=$'\033[31m'; GIALLO=$'\033[33m'; GRIGIO=$'\033[90m'; NEUTRO=$'\033[0m'
else
  VERDE=''; ROSSO=''; GIALLO=''; GRIGIO=''; NEUTRO=''
fi
ok()     { printf '  %s✓%s %s\n' "${VERDE}" "${NEUTRO}" "$1"; }
errore() { printf '  %s✗%s %s\n' "${ROSSO}" "${NEUTRO}" "$1"; }
attesa() { printf '  %s…%s %s\n' "${GIALLO}" "${NEUTRO}" "$1"; }
nota()   { printf '    %s%s%s\n' "${GRIGIO}" "$1" "${NEUTRO}"; }
titolo() { printf '\n%s\n' "$1"; }

uso() {
  printf 'Uso: %s <spegni|termina>\n' "$(basename "$0")" >&2
  printf '  spegni   docker kill sul primario: ~10 s di elezione, il container resta giù\n' >&2
  printf '  termina  il processo esce da sé: ~0,5 s di elezione, il container torna su\n' >&2
  exit 2
}

[[ $# -eq 1 ]] || uso
SCENA="$1"
[[ "${SCENA}" == "spegni" || "${SCENA}" == "termina" ]] || uso

if [[ ! -f "${SEGRETI}" ]]; then
  printf 'Manca %s (ADR-0014).\n' "${SEGRETI}" >&2
  exit 1
fi
set -a; . "${SEGRETI}"; set +a
UTENTE="${UTENTE_AMMINISTRATORE:-admin}"
PASSWORD="${PASSWORD_AMMINISTRATORE:-}"

# Millisecondi. `date +%s%3N` è una estensione GNU e su macOS non esiste: darebbe
# «1788202659N», che sembra un numero e non lo è. Python c'è ovunque serva a questo
# repository, ed è la ragione per cui la riga è questa e non quella dell'idioma diffuso.
ora_ms() { python3 -c 'import time; print(int(time.time()*1000))'; }

chi_primario() {
  local membro="$1"
  docker exec "${membro}" mongosh --quiet --host localhost \
    --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
    --eval 'const h = db.getSiblingDB("admin").hello(); print(h.primary || "nessuno")' \
    2>/dev/null | tail -1 | tr -d '\r'
}

# --- Chi è il primario, e chi guarda --------------------------------------------------
titolo "Prima"

PRIMARIO=""
for membro in mongo-rs-1 mongo-rs-2 mongo-rs-3; do
  risposta="$(chi_primario "${membro}")"
  if [[ -n "${risposta}" && "${risposta}" != "nessuno" ]]; then PRIMARIO="${risposta}"; break; fi
done
if [[ -z "${PRIMARIO}" || "${PRIMARIO}" == "nessuno" ]]; then
  errore "nessun primario: lo stack non è pronto. «make up-02», o «./tools/reset-demo.sh 02»."
  exit 1
fi
BERSAGLIO="${PRIMARIO%%:*}"
ok "primario: ${PRIMARIO}"

# L'osservatore deve essere un superstite, altrimenti misura la propria morte.
if [[ "${BERSAGLIO}" == "mongo-rs-2" ]]; then OSSERVATORE=mongo-rs-3; else OSSERVATORE=mongo-rs-2; fi
ok "osservatore: ${OSSERVATORE}"

# --- Il cronometro, avviato PRIMA del colpo -------------------------------------------
#
# Il ciclo di attesa gira dentro l'osservatore, in un mongosh che si collega e si
# autentica PRIMA che il primario cada e che stampa PRONTO quando è caldo. Se lo si
# lanciasse dopo il colpo, il tempo di avvio di mongosh — quasi un secondo — finirebbe
# dentro la misura e la scena sembrerebbe più lenta di quello che è.
OSSERVA="$(mktemp)"
CRONOMETRO="$(mktemp)"
trap 'rm -f "${OSSERVA}" "${CRONOMETRO}"' EXIT

cat > "${CRONOMETRO}" <<'JS'
const admin = db.getSiblingDB("admin");
let iniziale = null;
for (let i = 0; i < 50 && !iniziale; i++) {
  try { iniziale = admin.hello().primary || null; } catch (e) { sleep(100); }
}
if (!iniziale) { print("ERRORE nessun primario prima di cominciare"); quit(1); }
print("PRONTO " + iniziale);
const scadenza = Date.now() + 120000;
let nuovo = null, quando = null, senza = 0;
while (Date.now() < scadenza) {
  try {
    const h = admin.hello();
    if (!h.primary) { senza++; }
    else if (h.primary !== iniziale) { nuovo = h.primary; quando = Date.now(); break; }
  } catch (e) { senza++; }
  sleep(20);
}
print(JSON.stringify({ nuovo: nuovo, quando: quando, senza: senza }));
JS

docker cp "${CRONOMETRO}" "${OSSERVATORE}:/cronometro-failover.js" > /dev/null
docker exec "${OSSERVATORE}" mongosh --quiet --host localhost \
  --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
  --file /cronometro-failover.js > "${OSSERVA}" 2>&1 &
PID_OSSERVATORE=$!

for _ in $(seq 1 200); do
  grep -q '^PRONTO' "${OSSERVA}" && break
  sleep 0.1
done
if ! grep -q '^PRONTO' "${OSSERVA}"; then
  errore "l'osservatore non è mai stato pronto:"
  cat "${OSSERVA}"
  kill "${PID_OSSERVATORE}" 2>/dev/null
  exit 1
fi

# --- Il colpo -------------------------------------------------------------------------
if [[ "${SCENA}" == "spegni" ]]; then
  titolo "Spengo ${BERSAGLIO}"
  nota "da dire ad alta voce: «sto SPEGNENDO un nodo», non «sto simulando un crash» (ADR-0034)"
  T0="$(ora_ms)"
  docker kill "${BERSAGLIO}" > /dev/null
  ok "docker kill ${BERSAGLIO} — SIGKILL, nessun preavviso a nessuno"
else
  titolo "Faccio uscire ${BERSAGLIO} da sé"
  nota "questa è la via in cui la politica di riavvio interviene davvero (ADR-0034, punto 2)"
  T0="$(ora_ms)"
  docker exec "${BERSAGLIO}" mongosh --quiet --host localhost \
    --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
    --eval 'try { db.getSiblingDB("admin").shutdownServer() } catch (e) { }' > /dev/null 2>&1
  ok "shutdownServer() su ${BERSAGLIO} — il primario cede il ruolo e lo dice"
fi

# --- L'attesa -------------------------------------------------------------------------
titolo "L'elezione"
attesa "aspetto che ${OSSERVATORE} veda un primario diverso…"

ESITO=""
for ((i = 0; i < LIMITE_ATTESA; i++)); do
  kill -0 "${PID_OSSERVATORE}" 2>/dev/null || break
  sleep 1
done
wait "${PID_OSSERVATORE}" 2>/dev/null
ESITO="$(grep '^{' "${OSSERVA}" | tail -1)"

if [[ -z "${ESITO}" ]]; then
  errore "l'osservatore non ha prodotto un esito. Contenuto grezzo:"
  cat "${OSSERVA}"
  exit 1
fi

NUOVO="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["nuovo"] or "")' "${ESITO}")"
QUANDO="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["quando"] or 0)' "${ESITO}")"
SENZA="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["senza"])' "${ESITO}")"

ESITO_ELEZIONE=0
if [[ -z "${NUOVO}" ]]; then
  errore "nessuna elezione entro il limite: la maggioranza non c'è più"
  ESITO_ELEZIONE=1
else
  MS=$(( QUANDO - T0 ))
  ok "nuovo primario: ${NUOVO}"
  ok "elezione completata in ${MS} ms ($(python3 -c "print('%.1f' % (${MS}/1000.0))") s)"
  nota "giri in cui il set non aveva primario: ${SENZA}"
fi

# --- Che ne è stato del container -----------------------------------------------------
#
# È la mezza riga per cui esistono ADR-0034 e questo script. Con `docker kill` il conto
# dei riavvii resta a zero e il container resta `exited`: la politica non è intervenuta,
# perché per il demone quella fermata l'ha voluta un umano. Con `shutdown` avanza.
titolo "Il container"
sleep 6
stato="$(docker inspect "${BERSAGLIO}" --format 'Status={{.State.Status}} RestartCount={{.RestartCount}} ExitCode={{.State.ExitCode}}' 2>/dev/null)"
printf '  %s\n' "${stato}"
if [[ "${SCENA}" == "spegni" ]]; then
  nota "atteso: exited, RestartCount=0, ExitCode=137 — «restart: unless-stopped» NON lo rialza"
  nota "è la domanda che arriva dal pubblico, ed è nella pagina delle trappole (ADR-0033)"
  nota "per rimetterlo in piedi: ./tools/reset-demo.sh 02"
else
  nota "atteso: running, RestartCount avanzato, ExitCode=0 — qui la politica ha fatto il suo lavoro"
fi

titolo "Le righe di log che lo raccontano"
nota "si cercano per id, mai per testo del messaggio (ADR-0035)"

# Le righe interessanti stanno sul nodo che è stato ELETTO, non su chi ha votato: chi
# vota registra `23980 Responding to vote request` e basta. L'osservatore, che è chi
# guardava, il più delle volte NON è l'eletto — e leggere il log sbagliato è il modo
# più facile di concludere che l'elezione non lascia traccia.
ELETTO="${NUOVO%%:*}"
if [[ -n "${ELETTO}" ]]; then
  nota "log di ${ELETTO}, il nodo eletto"
  docker logs "${ELETTO}" 2>&1 | tail -600 | python3 -c '
import json, sys
# 21216 il primario dato per DOWN · 4615652 la decisione di indire l’elezione, con
# electionTimeoutPeriodMillis nell’attributo · 21438 e 21444 il giro a vuoto e il suo
# esito · 6015300 il voto messo su disco · 51799 le risposte degli altri · 21450 e
# 21358 il ruolo assunto. Sono gli id che ADR-0035 aspettava da feature/01.
interessanti = {21216, 4615652, 21438, 21444, 6015300, 51799, 21450, 21358, 23980, 21215}
for r in sys.stdin:
    r = r.strip()
    if not r.startswith("{"):
        continue
    try:
        d = json.loads(r)
    except Exception:
        continue
    if d.get("id") in interessanti:
        print("  %s  id=%-8s %-8s %s" % (d["t"]["$date"][11:23], d["id"], d["c"], d["msg"]))
'
fi

printf '\n'
exit ${ESITO_ELEZIONE}
