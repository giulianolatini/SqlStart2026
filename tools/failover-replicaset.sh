#!/usr/bin/env bash
# La scena centrale del talk: un nodo se ne va e il cluster se ne accorge.
#
#   ./tools/failover-replicaset.sh spegni       # docker kill sul primario
#   ./tools/failover-replicaset.sh termina      # il processo esce da sé (shutdown)
#   ./tools/failover-replicaset.sh maggioranza  # due membri su tre: il set va in sola lettura
#
# TRE scene, non una, e la differenza è il contenuto della slide (ADR-0034, ADR-0044,
# ADR-0045).
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
#   maggioranza  Le prime due scene mostrano un set che si ripara. Questa mostra che cosa
#            compra il terzo membro. Se ne fermano DUE: il superstite è vivo, sano e
#            raggiungibile, e dopo ~9 secondi si degrada da solo a SECONDARY perché non
#            vede più una maggioranza. Da lì le scritture rispondono `NotWritablePrimary`
#            e le letture continuano. Nessuno lo rialza: non c'è nessuno che possa
#            eleggerlo, ed è esattamente il punto (V-031).
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
  printf 'Uso: %s <spegni|termina|maggioranza>\n' "$(basename "$0")" >&2
  printf '  spegni       docker kill sul primario: ~10 s di elezione, il container resta giù\n' >&2
  printf '  termina      il processo esce da sé: ~0,5 s di elezione, il container torna su\n' >&2
  printf '  maggioranza  due membri su tre: dopo ~9 s il superstite passa in sola lettura\n' >&2
  exit 2
}

[[ $# -eq 1 ]] || uso
SCENA="$1"
case "${SCENA}" in spegni|termina|maggioranza) ;; *) uso ;; esac

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

# --- Leggere il log di un membro ---------------------------------------------------------
#
# Il gesto naturale è `docker logs`, e per la maggior parte del tempo va benissimo. Ma quel
# flusso può essere MORTO mentre il container è vivissimo: se il demone Docker si ferma e
# riparte — un riavvio della macchina, o solo il coperchio del portatile chiuso a metà
# giornata — i container tornano su da soli e mongod continua a scrivere, mentre la cattura
# dello stdout resta congelata all'istante in cui il demone è caduto. Non dà errore: dà
# silenzio, che è peggio, perché la sezione «righe di log» stamperebbe il nulla e si
# concluderebbe che l'evento non ha lasciato traccia (V-032, e la nota di metodo 58).
#
# Perciò la freschezza si CONTROLLA, confrontando l'ultima riga catturata con l'istante in
# cui il container è partito: se il log è più vecchio dell'avvio, non può essere di questa
# esecuzione. In quel caso le righe si chiedono a mongod, che ne tiene in memoria le ultime
# mille e non dipende da Docker per niente.
FILTRO_LOG='
import json, sys
interessanti = set(int(x) for x in sys.argv[1].split(","))
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

log_catturato_e_fresco() {
  local contenitore="$1" avvio ultima
  avvio="$(docker inspect "${contenitore}" --format '{{.State.StartedAt}}' 2>/dev/null)"
  [[ -n "${avvio}" ]] || return 1
  ultima="$(docker logs --tail 1 "${contenitore}" 2>&1 | python3 -c '
import json, sys
r = sys.stdin.read().strip()
print(json.loads(r)["t"]["$date"] if r.startswith("{") else "")
' 2>/dev/null)"
  [[ -n "${ultima}" ]] || return 1
  # I due istanti si confrontano al secondo, perché i formati non coincidono: Docker scrive
  # i nanosecondi e chiude con «Z», mongod si ferma ai millisecondi e chiude con «+00:00».
  # Il confronto è STRETTO di proposito: se l'ultima riga catturata è dello stesso secondo
  # in cui il container è partito non si può dire di chi sia, e chiederlo a mongod non
  # costa niente — mentre credere a un log vecchio costa la scena.
  python3 -c 'import sys; sys.exit(0 if sys.argv[1] > sys.argv[2] else 1)' \
    "${ultima:0:19}" "${avvio:0:19}"
}

righe_di_log() {
  local contenitore="$1" ids="$2"
  if log_catturato_e_fresco "${contenitore}"; then
    docker logs "${contenitore}" 2>&1 | tail -600 | python3 -c "${FILTRO_LOG}" "${ids}"
  else
    nota "«docker logs» è fermo a prima dell'avvio del container: le righe le chiede a mongod (V-032)"
    docker exec "${contenitore}" mongosh --quiet --host localhost \
      --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
      --eval 'db.getSiblingDB("admin").adminCommand({ getLog: "global" }).log.forEach(r => print(r))' \
      2>/dev/null | python3 -c "${FILTRO_LOG}" "${ids}"
  fi
}

# --- Scena 3: la maggioranza persa -------------------------------------------------------
#
# Le altre due scene finiscono bene: il set si ripara da sé, e chi guarda conclude che un
# replica set «regge ai guasti». Questa scena serve a dire di quanti guasti si parla, ed è
# l'unica che spiega perché i membri sono tre e non due. Si fermano DUE membri: il terzo
# resta vivo, sano, raggiungibile e con tutti i dati — e smette comunque di accettare
# scritture, perché un membro solo su tre non è una maggioranza e nessuno può eleggerlo.
#
# Il cronometro qui gira sul PRIMARIO stesso, non su un superstite: l'evento da misurare è
# il momento in cui quel nodo smette di dirsi scrivibile. È la sua propria retrocessione,
# ed è l'unico che possa datarla.
scena_maggioranza() {
  local primario_host="${PRIMARIO%%:*}"
  local vittime=()
  local m
  for m in mongo-rs-1 mongo-rs-2 mongo-rs-3; do
    [[ "${m}" == "${primario_host}" ]] || vittime+=("${m}")
  done

  # --- Primo membro: due su tre sono ancora una maggioranza ------------------------------
  titolo "Fermo il primo membro: ${vittime[0]}"
  nota "due su tre restano una maggioranza — è il caso già coperto dallo smoke (V-028)"
  docker kill "${vittime[0]}" > /dev/null
  sleep 2
  local prova
  prova="$(docker exec "${primario_host}" mongosh --quiet --host localhost \
    --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin --eval '
    try {
      db.getSiblingDB("lab").prova_maggioranza.insertOne(
        { scena: "un membro fermo", quando: new Date() },
        { writeConcern: { w: "majority", wtimeout: 8000 } });
      print("passa");
    } catch (e) { print("fallisce: " + e.codeName); }' 2>/dev/null | tail -1 | tr -d '\r')"
  if [[ "${prova}" == "passa" ]]; then
    ok "scrittura con w: \"majority\" — passa ancora, ${primario_host} è sempre primario"
  else
    errore "scrittura con w: \"majority\" — ${prova} (inatteso con due membri su tre)"
  fi

  # --- Il cronometro, acceso PRIMA del secondo colpo -------------------------------------
  local osserva cronometro
  osserva="$(mktemp)"; cronometro="$(mktemp)"
  trap 'rm -f "'"${osserva}"'" "'"${cronometro}"'"' EXIT

  cat > "${cronometro}" <<'JS'
const admin = db.getSiblingDB("admin");
let pronto = false;
for (let i = 0; i < 50 && !pronto; i++) {
  try { pronto = admin.hello().isWritablePrimary === true; } catch (e) { sleep(100); }
}
if (!pronto) { print("ERRORE non sono un primario scrivibile"); quit(1); }
print("PRONTO");
const scadenza = Date.now() + 60000;
let quando = null, giri = 0, eccezioni = 0;
while (Date.now() < scadenza) {
  try {
    const h = admin.hello();
    if (h.isWritablePrimary !== true) { quando = Date.now(); break; }
  } catch (e) { eccezioni++; }
  giri++;
  sleep(20);
}
print(JSON.stringify({ quando: quando, giri: giri, eccezioni: eccezioni }));
JS

  docker cp "${cronometro}" "${primario_host}:/cronometro-maggioranza.js" > /dev/null
  docker exec "${primario_host}" mongosh --quiet --host localhost \
    --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
    --file /cronometro-maggioranza.js > "${osserva}" 2>&1 &
  local pid=$!
  local _
  for _ in $(seq 1 200); do
    grep -q '^PRONTO' "${osserva}" && break
    sleep 0.1
  done
  if ! grep -q '^PRONTO' "${osserva}"; then
    errore "l'osservatore non è mai stato pronto:"
    cat "${osserva}"
    kill "${pid}" 2>/dev/null
    return 1
  fi

  titolo "Fermo il secondo membro: ${vittime[1]}"
  nota "da qui il superstite è solo, e «solo» su tre membri vuol dire senza maggioranza"
  local t0
  t0="$(ora_ms)"
  docker kill "${vittime[1]}" > /dev/null
  ok "docker kill ${vittime[1]} — ${primario_host} resta l'unico in piedi"

  # --- L'attesa: il primario si retrocede da sé ------------------------------------------
  titolo "La retrocessione"
  attesa "aspetto che ${primario_host} smetta di dirsi scrivibile…"
  local giro
  for ((giro = 0; giro < LIMITE_ATTESA; giro++)); do
    kill -0 "${pid}" 2>/dev/null || break
    sleep 1
  done
  wait "${pid}" 2>/dev/null
  local esito
  esito="$(grep '^{' "${osserva}" | tail -1)"
  if [[ -z "${esito}" ]]; then
    errore "l'osservatore non ha prodotto un esito. Contenuto grezzo:"
    cat "${osserva}"
    return 1
  fi

  local quando
  quando="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["quando"] or 0)' "${esito}")"
  local esito_scena=0
  if [[ "${quando}" == "0" ]]; then
    errore "${primario_host} si dice ancora scrivibile: non è quello che deve succedere"
    esito_scena=1
  else
    local ms=$(( quando - t0 ))
    ok "${primario_host} è passato a SECONDARY in ${ms} ms ($(python3 -c "print('%.1f' % (${ms}/1000.0))") s)"
    # Non sono dieci secondi tondi, e la ragione è precisa: il conto di
    # `electionTimeoutMillis` parte dall'ultimo battito ricevuto da una maggioranza, non
    # dal colpo. I battiti vanno ogni `heartbeatIntervalMillis` = 2 000 ms, quindi il
    # colpo cade in un punto qualsiasi di quella finestra e la misura vale 8-10 s (V-031).
    nota "il conto dei 10 000 ms parte dall'ultimo battito riuscito, non dal colpo:"
    nota "i battiti vanno ogni 2 000 ms, quindi la misura cade fra 8 e 10 secondi"
  fi

  # --- Che cosa risponde, adesso ---------------------------------------------------------
  titolo "Che cosa risponde adesso"
  docker exec "${primario_host}" mongosh --quiet --host localhost \
    --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin --eval '
    const admin = db.getSiblingDB("admin");
    const h = admin.hello();
    print("  si presenta come: isWritablePrimary=" + h.isWritablePrimary +
          " secondary=" + h.secondary + " primary=" + (h.primary || "nessuno"));
    try {
      print("  lettura: lab.ordini ha " + db.getSiblingDB("lab").ordini.countDocuments() + " documenti");
    } catch (e) { print("  lettura: " + e.codeName + " — " + e.message); }
    try {
      db.getSiblingDB("lab").prova_maggioranza.insertOne({ scena: "due membri fermi" });
      print("  scrittura: accettata (INATTESO)");
    } catch (e) { print("  scrittura: " + e.codeName + " (code " + e.code + ") — " + e.message); }
    rs.status().members.forEach(m =>
      print("  " + m.name + " → " + m.stateStr + " (health=" + m.health + ")"));
    ' 2>/dev/null
  nota "legge perché mongosh è collegata DIRETTAMENTE a quel nodo: un'applicazione che usa"
  nota "l'URI del replica set con readPreference primary non trova nessun server (V-031)"

  # --- Le righe di log -------------------------------------------------------------------
  #
  # 21216 il membro dato per DOWN · 21809 la riga che vale la scena, «Can't see a majority
  # of the set, relinquishing primary» · 21475 la retrocessione in risposta al battito ·
  # 21343 le operazioni degli utenti interrotte — è la ragione per cui le connessioni aperte
  # cadono · 21358 il cambio di stato · 5123007 i servizi da primario fermati.
  titolo "Le righe di log che lo raccontano"
  nota "si cercano per id, mai per testo del messaggio (ADR-0035)"
  nota "fra 21216 e 21809 il log ripete id=23974 «Heartbeat failed after max retries» ogni"
  nota "2 s: quelle righe SONO l'attesa, e sono omesse qui per non coprire le altre"
  righe_di_log "${primario_host}" "21216,21809,21475,21343,21358,5123007"

  titolo "Come si torna indietro"
  nota "i due container sono «exited» e nessuno li rialza: ./tools/reset-demo.sh 02"
  nota "il rientro misurato costa 9-12 s, il tempo di riavviare i due mongod e rieleggere"
  printf '\n'
  return ${esito_scena}
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

if [[ "${SCENA}" == "maggioranza" ]]; then
  # Con un membro già fermo la scena non ha niente da mostrare: ne resterebbe uno solo
  # da fermare, e il contrasto fra «due su tre reggono» e «uno su tre no» sparirebbe.
  IN_PIEDI=0
  for membro in mongo-rs-1 mongo-rs-2 mongo-rs-3; do
    [[ "$(docker inspect "${membro}" --format '{{.State.Status}}' 2>/dev/null)" == "running" ]] \
      && IN_PIEDI=$(( IN_PIEDI + 1 ))
  done
  if [[ "${IN_PIEDI}" -ne 3 ]]; then
    errore "servono tre membri in piedi, ce ne sono ${IN_PIEDI}: ./tools/reset-demo.sh 02"
    exit 1
  fi
  ok "tre membri in piedi: la scena può cominciare"
  scena_maggioranza
  exit $?
fi

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
# 21216 il primario dato per DOWN · 4615652 la decisione di indire l'elezione, con
# electionTimeoutPeriodMillis nell'attributo · 21438 e 21444 il giro a vuoto e il suo
# esito · 6015300 il voto messo su disco · 51799 le risposte degli altri · 21450 e
# 21358 il ruolo assunto. Sono gli id che ADR-0035 aspettava da feature/01.
ELETTO="${NUOVO%%:*}"
if [[ -n "${ELETTO}" ]]; then
  nota "log di ${ELETTO}, il nodo eletto"
  righe_di_log "${ELETTO}" "21216,4615652,21438,21444,6015300,51799,21450,21358,23980,21215"
fi

printf '\n'
exit ${ESITO_ELEZIONE}
