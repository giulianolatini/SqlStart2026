#!/usr/bin/env bash
# Prova end-to-end dello stack 01 — istanza singola. Presuppone lo stack già avviato
# (`make up-01`). Errori bloccanti -> uscita 1.
#
# Niente `set -e`, per la stessa ragione del preflight: una prova che si ferma al primo
# problema costringe a tre giri. Deve dire tutto quello che non va in una volta sola.
#
# Non verifica che il file Compose sia scritto bene — quello è `make stack-check`, che
# legge il file. Qui si verifica che il container che ne è nato si comporti come il file
# prometteva: sono due domande diverse, e la seconda è l'unica che il pubblico vedrà.
set -uo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="${RADICE}/docker/01-standalone/compose.yaml"
AMBIENTE="${RADICE}/tools/images.env"
SERVIZIO="mongo-standalone"

# Valori attesi. Non sono numeri magici: ognuno è misurato e registrato in Sources.md.
# Se il seed cambia, questi cambiano con lui — deliberatamente, non per caso. È il senso
# della prova: il dataset è deterministico, e qui si verifica che lo sia ancora.
VERSIONE_ATTESA="7.0.40"       # ADR-0028
MEMORIA_ATTESA_MIB=1024        # compose.yaml, mem_limit
CACHE_ATTESA_BYTE=268435456    # 0.25 GiB = 256 MiB esatti, V-009 e V-012
DOCUMENTI_ATTESI=50000         # V-013
IMPORTO_ATTESO="124861860.70"  # V-013, impronta del dataset
RIGHE_ATTESE=150281            # V-013, impronta del dataset

if [[ -t 1 ]]; then
  VERDE=$'\033[32m'; ROSSO=$'\033[31m'; GRIGIO=$'\033[90m'; NEUTRO=$'\033[0m'
else
  VERDE=''; ROSSO=''; GRIGIO=''; NEUTRO=''
fi

SUPERATI=0
ERRORI=0

ok()     { printf '  %s✓%s %s\n' "${VERDE}" "${NEUTRO}" "$1"; SUPERATI=$((SUPERATI + 1)); }
errore() { printf '  %s✗%s %s\n' "${ROSSO}" "${NEUTRO}" "$1"; ERRORI=$((ERRORI + 1)); }
nota()   { printf '    %s%s%s\n' "${GRIGIO}" "$1" "${NEUTRO}"; }
titolo() { printf '\n%s\n' "$1"; }

compose() { docker compose --env-file "${AMBIENTE}" -f "${COMPOSE}" "$@"; }

# Esegue JavaScript dentro il container e restituisce l'ultima riga stampata. `-T`
# perché senza terminale allocato l'output resta pulito e utilizzabile in una pipe.
interroga() {
  compose exec -T "${SERVIZIO}" mongosh lab --quiet --eval "$1" 2>/dev/null | tail -1 | tr -d '\r'
}

confronta() {
  local descrizione="$1" atteso="$2" ottenuto="$3"
  if [[ "${ottenuto}" == "${atteso}" ]]; then
    ok "${descrizione}: ${ottenuto}"
  else
    errore "${descrizione}: atteso ${atteso}, ottenuto «${ottenuto}»"
  fi
}

printf 'Prova dello stack 01 — istanza singola — %s\n' "$(date '+%F %H:%M')"

# --- Il container c'è ed è sano ------------------------------------------------------
titolo "Stato del nodo"

salute="$(docker inspect "${SERVIZIO}" --format '{{.State.Health.Status}}' 2>/dev/null)"
if [[ -z "${salute}" ]]; then
  errore "il container ${SERVIZIO} non esiste — esegui prima «make up-01»"
  printf '\nSuperati: %d · Errori: %d\n' "${SUPERATI}" "${ERRORI}"
  exit 1
fi
confronta "salute del container" "healthy" "${salute}"

# `mongod` come PID 1 riceve direttamente il SIGTERM di `docker stop` e chiude pulito.
# Con una shell di mezzo il segnale si fermerebbe a lei, e la chiusura durerebbe i dieci
# secondi di grazia prima del SIGKILL — su un lab che dimostra il guasto di un nodo è
# esattamente ciò che non si vuole.
comando="$(docker exec "${SERVIZIO}" cat /proc/1/cmdline 2>/dev/null | tr '\0' ' ' | sed 's/ *$//')"
case "${comando}" in
  mongod*) ok "mongod è PID 1: ${comando}" ;;
  *)       errore "PID 1 non è mongod: «${comando}»" ;;
esac

# Non è un difetto: lo aggiunge l'entrypoint ufficiale, non il nostro file (S-034). Si
# verifica perché lo stack 01 gira senza autenticazione, e le due cose insieme vanno
# sapute: l'unica barriera è la porta pubblicata su localhost.
case "${comando}" in
  *--bind_ip_all*) ok "--bind_ip_all presente, aggiunto dall'entrypoint (atteso)" ;;
  *)               nota "--bind_ip_all assente: l'entrypoint ha cambiato comportamento" ;;
esac

# --- La porta risponde dall'host -----------------------------------------------------
titolo "Raggiungibilità"

porta="$(compose port "${SERVIZIO}" 27017 2>/dev/null | tail -1)"
if [[ -z "${porta}" ]]; then
  errore "nessuna porta pubblicata per ${SERVIZIO}:27017"
elif python3 -c "import socket,sys; socket.create_connection(('127.0.0.1', int(sys.argv[1])), 3).close()" \
       "${porta##*:}" 2>/dev/null; then
  ok "la porta ${porta} risponde dall'host"
else
  errore "la porta ${porta} non risponde dall'host"
fi

# --- Quello che gira è quello che abbiamo pinnato ------------------------------------
titolo "Versione e limiti"

confronta "versione di mongod" "${VERSIONE_ATTESA}" "$(interroga 'print(db.version())')"

digest_atteso="$(sed -n 's/^MONGO_IMAGE=.*@\(sha256:[0-9a-f]*\)$/\1/p' "${AMBIENTE}")"
digest_reale="$(docker inspect "${SERVIZIO}" --format '{{index .Image}}' 2>/dev/null)"
digest_immagine="$(docker inspect "${digest_reale}" --format '{{index .RepoDigests 0}}' 2>/dev/null)"
confronta "digest dell'immagine" "${digest_atteso}" "${digest_immagine##*@}"

# `Number(...)` non è ornamentale: memLimitMB è un Long, e `print()` di un Long stampa
# «Long('1024')», non «1024».
confronta "memoria vista da mongod (MiB)" "${MEMORIA_ATTESA_MIB}" \
  "$(interroga 'print(Number(db.hostInfo().system.memLimitMB))')"

# Il controllo che MongoDB non fa: una cache più grande del limite di memoria viene
# accettata senza un avviso che colleghi le due cifre (V-009).
cache="$(interroga 'print(db.serverStatus().wiredTiger.cache["maximum bytes configured"])')"
confronta "cache WiredTiger (byte)" "${CACHE_ATTESA_BYTE}" "${cache}"
if [[ "${cache}" =~ ^[0-9]+$ ]] && (( cache > MEMORIA_ATTESA_MIB * 1024 * 1024 )); then
  errore "la cache supera il limite di memoria del container"
fi

# --- I dati di demo sono quelli, e sono sempre quelli --------------------------------
titolo "Dati di demo"

impronta="$(interroga 'const a = db.ordini.aggregate([{$group:{_id:null, n:{$sum:1}, tot:{$sum:"$importo"}, righe:{$sum:"$righe"}}}]).toArray()[0]; print(a ? a.n + " " + a.tot.toFixed(2) + " " + a.righe : "collezione vuota")')"
confronta "impronta di lab.ordini" \
  "${DOCUMENTI_ATTESI} ${IMPORTO_ATTESO} ${RIGHE_ATTESE}" "${impronta}"
if [[ "${impronta}" != "${DOCUMENTI_ATTESI} ${IMPORTO_ATTESO} ${RIGHE_ATTESE}" ]]; then
  nota "il seed gira solo su un volume non inizializzato (V-014): «make seed-01» lo"
  nota "riesegue su uno stack avviato, «make reset-01» riparte da volume vuoto"
fi

# Il confronto fra la stessa interrogazione con e senza indice è una delle demo:
# un indice creato in anticipo toglierebbe il «prima» (ADR-0031).
indici="$(interroga 'print(db.ordini.getIndexes().map(i => i.name).join(","))')"
confronta "indici su lab.ordini" "_id_" "${indici}"

# --- Il canale di log è quello deciso ------------------------------------------------
titolo "Log"

# ADR-0030: nessun --logpath, perché è una redirezione e spegnerebbe questo comando.
righe_log="$(compose logs --tail 20 2>/dev/null | grep -c 'msg')"
if (( righe_log > 0 )); then
  ok "docker compose logs restituisce righe (${righe_log} nelle ultime 20)"
else
  errore "docker compose logs è muto: qualcuno ha aggiunto --logpath?"
fi

# Senza questi due limiti il file di log cresce finché c'è disco: il driver json-file
# non ruota niente per impostazione predefinita (V-011).
rotazione="$(docker inspect "${SERVIZIO}" --format '{{index .HostConfig.LogConfig.Config "max-size"}} {{index .HostConfig.LogConfig.Config "max-file"}}' 2>/dev/null)"
confronta "rotazione dei log (max-size max-file)" "10m 3" "${rotazione}"

# --- Esito ---------------------------------------------------------------------------
printf '\nSuperati: %d · Errori: %d\n' "${SUPERATI}" "${ERRORI}"
if (( ERRORI > 0 )); then
  printf 'Lo stack 01 non si comporta come promesso.\n'
  exit 1
fi
printf 'Lo stack 01 fa quello che il file Compose promette.\n'
