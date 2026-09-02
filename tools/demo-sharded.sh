#!/usr/bin/env bash
# Le scene del Blocco 3 del talk. Presuppone lo stack già avviato (`make up-03`).
#
#   ./tools/demo-sharded.sh stato          # il cluster come si presenta: sh.status()
#   ./tools/demo-sharded.sh distribuzione  # dove stanno davvero i ventimila documenti
#   ./tools/demo-sharded.sh guasto         # cade uno shard: che cosa risponde ancora
#
# PERCHÉ UNO SCRIPT E NON DUE RIGHE DI `docker exec`. Le registrazioni di riserva
# (ADR-0050) si girano registrando un comando, e un comando che nessuno può rieseguire
# non è una riserva: è un filmato. Le quattro scene di `feature/02` sono `make` bersagli
# per questo motivo, e queste seguono la stessa forma. La seconda ragione è la password:
# passarla sulla riga di comando significherebbe mostrarla a schermo mentre si registra,
# e leggerla qui da `.env` è quello che fanno già `smoke-sharded.sh` e `reset-demo.sh`
# (ADR-0014, ADR-0054).
#
# NON È UNO SMOKE TEST. `smoke-sharded.sh` verifica sessantaquattro cose e stampa ✓ o ✗;
# qui non si verifica niente, si MOSTRA. Un solo numero sbagliato in una prova è un
# errore da riparare; in una scena è una domanda dal pubblico, e le due cose vogliono
# due programmi diversi.
#
# LE SCENE SONO TRE E NON UNA, e la divisione non è estetica. `sh.status()` racconta la
# struttura — chi sono gli shard, com'è spezzata la collezione, che cosa fa il balancer —
# e la si guarda una volta sola. La distribuzione racconta l'unica cosa che distingue uno
# sharded cluster funzionante da uno che ha messo tutto su un nodo, e va guardata ogni
# volta che si tocca la chiave. Metterle insieme significa che la seconda scorre via
# dietro le centodiciannove righe della prima. Il guasto è la terza perché è l'unica che
# TOCCA il cluster invece di guardarlo: ferma un nodo e lo rimette in piedi, e va potuta
# rieseguire da sola quando la sala chiede «e se cade?».
set -uo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="${RADICE}/docker/03-sharded/compose.yaml"
AMBIENTE="${RADICE}/tools/images.env"
SEGRETI="${RADICE}/docker/03-sharded/.env"

PROFILO="${PROFILO:-palco}"

# I ventimila di ADR-0064, ripetuti qui perché una scena che dice «20000 documenti»
# mentre il seed ne ha messi altri sta mentendo al pubblico con la faccia seria.
DOCUMENTI_ATTESI=20000

if [[ -t 1 ]]; then
  VERDE=$'\033[32m'; ROSSO=$'\033[31m'; GIALLO=$'\033[33m'
  GRIGIO=$'\033[90m'; NEUTRO=$'\033[0m'
else
  VERDE=''; ROSSO=''; GIALLO=''; GRIGIO=''; NEUTRO=''
fi

titolo()  { printf '\n%s%s%s\n' "${GIALLO}" "$1" "${NEUTRO}"; }
voce()    { printf '  %s•%s %s\n' "${VERDE}" "${NEUTRO}" "$1"; }
nota()    { printf '    %s%s%s\n' "${GRIGIO}" "$1" "${NEUTRO}"; }
comando() { printf '\n%s$ %s%s\n\n' "${GRIGIO}" "$1" "${NEUTRO}"; }
guasto()  { printf '  %s✗%s %s\n' "${ROSSO}" "${NEUTRO}" "$1" >&2; }

uso() {
  printf 'Uso: %s <scena>\n\n' "${0##*/}" >&2
  printf '  stato           il cluster come si presenta: shard, chunk, balancer\n' >&2
  printf '  distribuzione   dove stanno i %s documenti di lab.ordini\n' "${DOCUMENTI_ATTESI}" >&2
  printf '  guasto          ferma il primario di uno shard e misura che cosa resta\n\n' >&2
  printf 'Il profilo si sceglie con PROFILO=palco (predefinito) o PROFILO=completo.\n' >&2
}

case "${PROFILO}" in
  palco)    SHARD1=(shard1a); SHARD2=(shard2a) ;;
  completo) SHARD1=(shard1a shard1b shard1c); SHARD2=(shard2a shard2b shard2c) ;;
  *) printf 'PROFILO=«%s» non esiste: sono «palco» e «completo».\n' "${PROFILO}" >&2; exit 1 ;;
esac

# --- Le credenziali, che non stanno nel repository ------------------------------------
if [[ ! -f "${SEGRETI}" ]]; then
  printf 'Manca %s.\n' "${SEGRETI}" >&2
  printf 'Crearlo con: cp %s.example %s, poi riempire PASSWORD_AMMINISTRATORE.\n' \
    "${SEGRETI}" "${SEGRETI}" >&2
  exit 1
fi
set -a; . "${SEGRETI}"; set +a
UTENTE="${UTENTE_AMMINISTRATORE:-admin}"
PASSWORD="${PASSWORD_AMMINISTRATORE:-}"
REPLICA_SHARD1="${NOME_REPLICA_SHARD1:-shard1rs}"
REPLICA_SHARD2="${NOME_REPLICA_SHARD2:-shard2rs}"

if [[ -z "${PASSWORD}" ]]; then
  printf 'PASSWORD_AMMINISTRATORE è vuota in %s.\n' "${SEGRETI}" >&2
  exit 1
fi

compose() {
  docker compose --env-file "${AMBIENTE}" --env-file "${SEGRETI}" \
    -f "${COMPOSE}" --profile "${PROFILO}" "$@"
}

# Dal router: è la porta da cui il cluster si vede intero. Sulla password vale la nota
# di `smoke-sharded.sh` — `--password` dentro il container, mai `-e` al client `docker`,
# che sull'host resterebbe leggibile nella riga di comando (ADR-0054, V-047).
router() {
  compose exec -T mongos \
    mongosh --quiet --host localhost \
      --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
      lab --eval "$1" 2>/dev/null | tr -d '\r'
}

# Da un singolo shard, scavalcando il router. Fino ad ADR-0071 questa funzione non
# poteva esistere: gli shard non avevano utenti, e le credenziali del cluster — che
# vivono sui config server — su di essi non valevano niente. L'amministratore locale a
# ogni shard è precisamente ciò che ADR-0026 prevedeva «dove una demo debba ispezionare
# un singolo shard», ed è questa demo.
shard() {
  local nodo="$1"
  compose exec -T "${nodo}" \
    mongosh --quiet --host localhost \
      --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
      lab --eval "$2" 2>/dev/null | tr -d '\r' | tail -1
}

acceso() {
  if ! docker inspect sh-mongos --format '{{.State.Status}}' >/dev/null 2>&1; then
    guasto "il router sh-mongos non esiste — esegui prima «make up-03»"
    exit 1
  fi
}

# --- Scena 1 — lo stato ---------------------------------------------------------------
#
# `sh.status()` PRIMA e la lettura DOPO, non il contrario. Il comando è quello che
# chiunque digiterebbe, e va visto per quello che è: centodiciannove righe in cui le
# quattro che contano stanno sparse. Se la lettura venisse prima, il pubblico
# guarderebbe le righe cercando la conferma di quello che gli è già stato detto; venendo
# dopo, resta a schermo — ed è l'ultima cosa che si vede quando la scena finisce.
scena_stato() {
  acceso
  printf 'Lo sharded cluster come si presenta — profilo %s — %s\n' \
    "${PROFILO}" "$(date '+%F %H:%M')"
  comando "mongosh --eval 'sh.status()'          # dal router, sh-mongos"
  router 'sh.status()'

  titolo "Le quattro righe che contano"
  local shard chunk chiave bilanciere router_attivi

  shard="$(router 'db.getSiblingDB("config").shards.find({}, {_id: 1}).toArray().map(s => s._id).join(", ")' | tail -1)"
  voce "shard registrati: ${shard}"
  nota "sono due perché con uno solo non si partiziona niente (ADR-0010)"

  # La chiave si stampa nella forma in cui la si scrive — { _id: "hashed" } — e non come
  # JSON compatto: chi guarda la scena deve riconoscere quello che digiterebbe.
  chiave="$(router 'var k = db.getSiblingDB("config").collections.findOne({_id: "lab.ordini"}).key; "{ " + Object.keys(k).map(c => c + ": " + JSON.stringify(k[c])).join(", ") + " }"' | tail -1)"
  chunk="$(router 'db.getSiblingDB("config").chunks.countDocuments({uuid: db.getSiblingDB("config").collections.findOne({_id: "lab.ordini"}).uuid})' | tail -1)"
  voce "lab.ordini è distribuita con chiave ${chiave}, in ${chunk} chunk"
  nota "alla creazione erano quattro, due per shard, ed è il valore predefinito (S-066)"
  nota "dalla 7.0 l'AutoMerger fonde i contigui dello stesso shard: quattro diventano due"
  nota "senza che un documento si sposti (V-062, ADR-0069). Il pavimento è due, non quattro"

  bilanciere="$(router 'sh.getBalancerState() ? "abilitato" : "fermo"' | tail -1)"
  voce "balancer: ${bilanciere}"
  nota "abilitato non vuol dire che stia migrando: con due chunk equilibrati non ha lavoro"

  router_attivi="$(router 'db.getSiblingDB("config").mongos.countDocuments({})' | tail -1)"
  voce "router che si sono annunciati: ${router_attivi}"
  nota "il profilo palco ne ha uno; «completo» ne ha due, e il secondo serve a mostrare"
  nota "che un router non è uno stato da perdere ma un processo da rimpiazzare (ADR-0010)"
}

# --- Scena 2 — la distribuzione -------------------------------------------------------
#
# L'ORDINE È IL CONTENUTO. Prima il totale dal router, che è quello che un'applicazione
# vede e che non cambierebbe di una virgola se tutti i documenti stessero su un solo
# nodo; poi i due shard interrogati uno per uno, che è l'unico modo di sapere se il
# cluster sta davvero partizionando. La somma torna a fine scena, e quella somma è la
# domanda a cui il Blocco 3 esiste per rispondere.
scena_distribuzione() {
  acceso
  printf 'Dove stanno i documenti di lab.ordini — profilo %s — %s\n' \
    "${PROFILO}" "$(date '+%F %H:%M')"

  titolo "Dal router, che li vede tutti"
  local totale
  totale="$(router 'db.ordini.countDocuments({})' | tail -1)"
  voce "lab.ordini attraverso mongos: ${totale} documenti"
  nota "è quello che vede l'applicazione, e sarebbe identico con un solo shard:"
  nota "da qui la distribuzione NON si vede, ed è il punto di tutta la scena"

  titolo "Dai due shard, interrogati uno per uno"
  local primo secondo somma
  primo="$(shard "${SHARD1[0]}" 'db.ordini.countDocuments({})')"
  secondo="$(shard "${SHARD2[0]}" 'db.ordini.countDocuments({})')"
  voce "${REPLICA_SHARD1} (${SHARD1[0]}): ${primo} documenti"
  voce "${REPLICA_SHARD2} (${SHARD2[0]}): ${secondo} documenti"

  if [[ "${primo}" =~ ^[0-9]+$ && "${secondo}" =~ ^[0-9]+$ ]]; then
    somma=$((primo + secondo))
    voce "${primo} + ${secondo} = ${somma}"
    if (( somma == totale )); then
      nota "nessun documento in due posti, nessuno perso: la collezione è partizionata,"
      nota "non copiata. La replica è dentro ogni shard, fra shard non c'è ridondanza"
    else
      guasto "la somma non torna: dal router ${totale}, dagli shard ${somma}"
      nota "documenti orfani da una migrazione interrotta? «sh.status()» li conta"
    fi
  fi
  nota "queste due righe si leggono perché ogni shard ha un amministratore locale:"
  nota "prima di ADR-0071 le credenziali del cluster su uno shard non valevano niente"

  comando "mongosh lab --eval 'db.ordini.getShardDistribution()'"
  router 'db.ordini.getShardDistribution()'

  titolo "Perché è venuta così"
  nota "la chiave è { _id: \"hashed\" }: l'hash di un ObjectId monotono distribuisce"
  nota "in modo uniforme, e le quote misurate sono 49,3 % e 50,7 % (V-058)"
  nota "con una chiave monotona non hashed gli stessi ventimila documenti finiscono"
  nota "tutti sull'ultimo chunk, e il cluster risponde «balancerCompliant: true» lo stesso"
}

# --- Scena 3 — il guasto di uno shard -------------------------------------------------
#
# QUESTA SCENA TOCCA IL CLUSTER, e la differenza rispetto alle prime due va detta a chi
# la esegue: ferma un container e lo riaccende. Se qualcosa va storto nel mezzo — un
# Ctrl-C, un errore — il nodo resta giù, e per questo c'è una trappola che lo rialza.
#
# LA STESSA SCENA IN DUE PROFILI, e non perché si adatti: perché la risposta è diversa e
# la differenza È il contenuto. In `palco` ogni shard ha un membro solo: fermarlo non
# provoca nessuna elezione, perché non c'è nessuno da eleggere, e metà della collezione
# diventa irraggiungibile. In `completo` i membri sono tre: fermare il primario provoca
# l'elezione di un altro, e il router riprende a rispondere da solo. Il copione non
# decide quale delle due storie raccontare — conta i membri e misura i tempi. Se un
# giorno il profilo cambia, la scena racconta la verità nuova senza che nessuno la
# riscriva.
#
# I DUE DOCUMENTI NON SONO SCELTI A MANO. Servono un `_id` che viva sullo shard che cade
# e uno che viva sull'altro, e prenderli dai due shard direttamente — invece di scrivere
# in chiaro «42» e «7» come farebbe un copione — significa che la scena regge anche se
# un giorno la chiave, il seme o il numero di shard cambiano. È la stessa ragione per cui
# la scena 2 somma quello che legge invece di stampare le quote misurate.

# Il tempo fa parte della misura: un errore che arriva dopo diciassette secondi racconta
# un'attesa, non un rifiuto. `SECONDS` è un contatore della shell, si azzera assegnandolo
# e non chiede né `date` né `python3`.
INIZIO=0
cronometro() { INIZIO=${SECONDS}; }

# «1 membro/i» si legge in una diagnostica, non si dice a voce alta davanti a una sala.
membri_di() { (( $1 == 1 )) && printf '1 membro' || printf '%d membri' "$1"; }
secondi()    { printf '%d' $((SECONDS - INIZIO)); }

# Come `router()`, ma l'errore lo stampa invece di lasciarlo cadere: qui l'errore È la
# scena, e il `2>/dev/null` di `router()` lo butterebbe via. La coda del messaggio dopo
# l'ultimo «::» è la parte che nomina il problema; quello che sta prima è la catena di
# chi l'ha riferito a chi.
router_esito() {
  router "try { ${1} } catch (e) { print('✗ ' + e.codeName + ': ' + e.message.split('::').pop().trim()) }" \
    | tail -1
}

FERMATO=""
rialza() {
  if [[ -n "${FERMATO}" ]]; then
    printf '\n%s… rimetto in piedi %s%s\n' "${GIALLO}" "${FERMATO}" "${NEUTRO}"
    compose start "${FERMATO}" >/dev/null 2>&1 || true
    FERMATO=""
  fi
}

scena_guasto() {
  acceso
  trap 'rialza; exit 130' INT TERM

  printf 'Se cade uno shard — profilo %s — %s\n' "${PROFILO}" "$(date '+%F %H:%M')"

  titolo "Prima: chi tiene che cosa"
  local membri primario servizio totale id_vivo id_morto
  membri="${#SHARD1[@]}"
  primario="$(shard "${SHARD1[0]}" 'db.hello().primary')"
  servizio="${primario%%:*}"
  totale="$(router 'db.ordini.countDocuments({})' | tail -1)"
  voce "lab.ordini dal router: ${totale} documenti"
  voce "${REPLICA_SHARD1}: $(membri_di "${membri}"), primario ${primario}"
  voce "${REPLICA_SHARD2}: $(membri_di "${#SHARD2[@]}")"

  # Un documento per shard, chiesto allo shard stesso: è l'unico modo di essere certi di
  # dove vive senza fidarsi di come l'hash ha diviso il mondo.
  id_morto="$(shard "${SHARD1[0]}" 'db.ordini.findOne()._id')"
  id_vivo="$(shard "${SHARD2[0]}" 'db.ordini.findOne()._id')"
  nota "l'ordine _id ${id_morto} vive su ${REPLICA_SHARD1}, l'ordine _id ${id_vivo} su ${REPLICA_SHARD2}"
  nota "li ho chiesti ai due shard, non indovinati: la scena regge anche se cambia la chiave"

  titolo "Il guasto"
  comando "docker compose stop ${servizio}"
  FERMATO="${servizio}"
  cronometro
  compose stop "${servizio}" >/dev/null 2>&1
  voce "${servizio} fermato in $(secondi) s — SIGTERM, non SIGKILL (ADR-0034)"

  titolo "Che cosa risponde ancora"
  local risposta
  cronometro
  risposta="$(router_esito "print('trovato: ' + JSON.stringify(db.ordini.findOne({_id: ${id_vivo}})._id))")"
  voce "l'ordine su ${REPLICA_SHARD2}: ${risposta}   [$(secondi) s]"
  nota "il cluster non è caduto: è caduto uno shard, e le query che non lo toccano passano"

  cronometro
  risposta="$(router_esito "print('trovato: ' + JSON.stringify(db.ordini.findOne({_id: ${id_morto}})._id))")"
  voce "l'ordine su ${REPLICA_SHARD1}: ${risposta}   [$(secondi) s]"

  cronometro
  risposta="$(router_esito 'print(db.ordini.countDocuments({}))')"
  voce "il conteggio totale: ${risposta}   [$(secondi) s]"

  if [[ "${risposta}" == "${totale}" ]]; then
    # «È stato eletto un altro primario» è una frase che si può dire o si può mostrare, e
    # in questo repository si mostra. Lo si chiede a un membro rimasto in piedi — e che
    # risponda anche lui alle credenziali dice, di passaggio, che l'amministratore locale
    # di ADR-0071 è replicato dentro lo shard come qualunque altro documento.
    local superstite nuovo
    for superstite in "${SHARD1[@]}"; do
      [[ "${superstite}" != "${servizio}" ]] && break
    done
    nuovo="$(shard "${superstite}" 'db.hello().primary')"
    voce "il primario di ${REPLICA_SHARD1} adesso è ${nuovo}, era ${primario}"
    nota "il totale è tornato senza che nessuno intervenisse: dentro ${REPLICA_SHARD1} i"
    nota "membri rimasti hanno eletto, e il router se n'è accorto da solo"
  else
    nota "l'attesa non è indecisione: il router cerca un primario per ${REPLICA_SHARD1} e"
    nota "non lo trova, perché quello shard ha $(membri_di "${membri}") e non c'è nessuno da eleggere"
    nota "la metà dei documenti che sta lì è irraggiungibile finché il nodo non torna"
  fi

  titolo "Il ritorno"
  comando "docker compose start ${servizio}"
  cronometro
  compose start "${servizio}" >/dev/null 2>&1
  local atteso=0
  while (( SECONDS - INIZIO < 120 )); do
    risposta="$(router "try { print(db.ordini.countDocuments({})) } catch (e) { print('—') }" | tail -1)"
    if [[ "${risposta}" == "${totale}" ]]; then atteso=1; break; fi
    sleep 1
  done
  FERMATO=""
  trap - INT TERM
  if (( atteso )); then
    voce "${servizio} è tornato e il totale è di nuovo ${totale}   [$(secondi) s dal comando]"
  else
    guasto "dopo $(secondi) s il totale è ancora «${risposta}»: guarda «docker compose ps»"
  fi

  titolo "Che cosa portarsi via"
  nota "uno sharded cluster non cade intero: cade a pezzi, e ogni pezzo si porta via i"
  nota "propri documenti. La disponibilità non è del cluster, è di ogni singolo shard"
  nota "la ridondanza sta DENTRO lo shard — è il suo replica set — e fra shard non c'è:"
  nota "nessun altro nodo ha una copia di quello che teneva ${REPLICA_SHARD1}"
  if (( membri == 1 )); then
    nota "il profilo palco tiene un membro per shard perché entri nel portatile, ed è"
    nota "esattamente ciò che in produzione non si fa: «completo» ne ha tre, e con tre"
    nota "questa stessa scena finisce con un'elezione invece che con un'attesa"
  fi
}

case "${1:-}" in
  stato)         scena_stato ;;
  distribuzione) scena_distribuzione ;;
  guasto)        scena_guasto ;;
  ""|-h|--help|aiuto) uso; exit 1 ;;
  *) printf 'scena «%s» non esiste.\n\n' "$1" >&2; uso; exit 1 ;;
esac
