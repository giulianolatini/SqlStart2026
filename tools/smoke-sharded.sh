#!/usr/bin/env bash
# Prova end-to-end dello stack 03 — sharded cluster. Presuppone lo stack già avviato
# (`make up-03`). Errori bloccanti -> uscita 1.
#
# Niente `set -e`, per la ragione di smoke-01 e di smoke-02: una prova che si ferma al
# primo problema costringe a tre giri. Deve dire tutto quello che non va in una volta
# sola.
#
# Non verifica che il file Compose sia scritto bene — quello è `make stack-check`, che
# legge il file. Qui si verifica che i container che ne sono nati si comportino come il
# file prometteva.
#
# LA DIFFERENZA RISPETTO A smoke-02 non è la lunghezza: è che qui esistono i RUOLI. Un
# nodo non è più intercambiabile con un altro, e metà dei controlli riguarda cose che un
# replica set non ha — un router senza storage, due shard registrati, una collezione
# spezzata in chunk, e soprattutto la DISTRIBUZIONE, che è l'unica misura capace di
# distinguere uno sharded cluster funzionante da uno che ha messo tutto su uno shard e
# funziona benissimo lo stesso.
#
# IL PROFILO SI SCEGLIE CON UNA VARIABILE, perché lo stack ne ha due e i controlli
# devono contare cose diverse: `PROFILO=palco` (predefinito) o `PROFILO=completo`.
set -uo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="${RADICE}/docker/03-sharded/compose.yaml"
AMBIENTE="${RADICE}/tools/images.env"
SEGRETI="${RADICE}/docker/03-sharded/.env"

PROFILO="${PROFILO:-palco}"

# Valori attesi. Non sono numeri magici: ognuno è misurato e registrato in Sources.md.
VERSIONE_ATTESA="7.0.40"        # ADR-0028
MEMORIA_CFG_BYTE=536870912      # 512 MiB — compose.yaml, design §5.1
MEMORIA_SHARD_BYTE=671088640    # 640 MiB
MEMORIA_MONGOS_BYTE=268435456   # 256 MiB
CACHE_ATTESA="cache_size=256M"  # 0,25 GiB, come sugli altri due stack (V-009, V-012)
PERMESSI_KEYFILE="400"          # V-021: mongod rifiuta un keyfile più aperto
SHARD_ATTESI=2                  # ADR-0010: con uno solo non si partiziona niente

# L'impronta del dataset, misurata in V-058. I tre numeri hanno una proprietà che vale
# la pena conoscere: questi 20 000 documenti sono i PRIMI 20 000 di quei 50 000 degli
# stack 01 e 02 — stesso generatore, stesso seme, stesso ordine di chiamate — quindi
# l'impronta qui è diversa da quella di smoke-01 e smoke-02 e deve esserlo. Se
# cambiasse senza che nessuno abbia toccato il seed, è il generatore ad essere cambiato.
DOCUMENTI_ATTESI=20000
IMPORTO_ATTESO="50083417.93"
RIGHE_ATTESE=60278

# La distribuzione. Quattro chunk non è un caso: distribuendo una collezione VUOTA con
# una chiave hashed MongoDB crea due chunk per shard, ed è il valore predefinito
# documentato (S-066). Due shard, quattro chunk.
#
# Quattro però NON è un invariante, e pretenderlo ha fatto fallire questo smoke la prima
# volta che lo stack è stato spento e riacceso sugli stessi volumi. Dalla 7.0 il balancer
# fonde da sé i chunk contigui che stanno sullo stesso shard (S-072), e i quattro
# diventano due senza che un solo documento si sposti (V-062, ADR-0069).
#
# Il pavimento è due, e non è una stima: un chunk non può stare a cavallo di due shard,
# quindi finché gli shard con documenti sono due i chunk non possono essere meno di due.
# Quello che questo controllo deve bocciare è UNO — cioè tutto su uno shard solo.
CHUNK_MINIMI=2
CHUNK_INIZIALI=4
# La quota minima per shard. Misurata: 49,3 % / 50,7 %. La soglia è larga perché la
# distribuzione è statistica e non esatta: quello che deve fallire è il caso vero, cioè
# uno shard a zero, non una fluttuazione di qualche punto.
QUOTA_MINIMA=40

INDICI_ATTESI="_id_,_id_hashed"

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

confronta() {
  local descrizione="$1" atteso="$2" ottenuto="$3"
  if [[ "${ottenuto}" == "${atteso}" ]]; then
    ok "${descrizione}: ${ottenuto}"
  else
    errore "${descrizione}: atteso ${atteso}, ottenuto «${ottenuto}»"
  fi
}

# --- Chi c'è, secondo il profilo ------------------------------------------------------
#
# I due profili non sono due stack diversi: sono lo stesso stack con un membro o con tre
# per componente. Ma i controlli che CONTANO — quanti membri ha un replica set, quanti
# router rispondono — hanno risposte diverse, e uno smoke che ne sapesse una sola
# fallirebbe sull'altro profilo raccontando la cosa sbagliata.
case "${PROFILO}" in
  palco)
    CONFIG=(cfg1)
    SHARD1=(shard1a)
    SHARD2=(shard2a)
    ROUTER=(mongos)
    ;;
  completo)
    CONFIG=(cfg1 cfg2 cfg3)
    SHARD1=(shard1a shard1b shard1c)
    SHARD2=(shard2a shard2b shard2c)
    ROUTER=(mongos mongos2)
    ;;
  *)
    printf 'PROFILO=«%s» non esiste: sono «palco» e «completo».\n' "${PROFILO}" >&2
    exit 1
    ;;
esac

MONGOD=("${CONFIG[@]}" "${SHARD1[@]}" "${SHARD2[@]}")
MEMBRI_PER_SET=${#CONFIG[@]}
# I cinque one-shot della catena, nell'ordine in cui devono essere morti bene.
UNOSHOT=(keyfile-init cfg-init shard1-init shard2-init add-shard seed)

# --- Le credenziali, che non stanno nel repository ------------------------------------
#
# Il file arriva da fuori (ADR-0014). Se manca, non c'è prova possibile: qui si esce
# subito, perché ogni controllo successivo fallirebbe per lo stesso motivo e stamperebbe
# venti righe rosse che dicono tutte la stessa cosa.
if [[ ! -f "${SEGRETI}" ]]; then
  printf 'Manca %s.\n' "${SEGRETI}" >&2
  printf 'Crearlo con: cp %s.example %s, poi riempire PASSWORD_AMMINISTRATORE.\n' \
    "${SEGRETI}" "${SEGRETI}" >&2
  exit 1
fi
set -a; . "${SEGRETI}"; set +a
UTENTE="${UTENTE_AMMINISTRATORE:-admin}"
PASSWORD="${PASSWORD_AMMINISTRATORE:-}"
REPLICA_CFG="${NOME_REPLICA_CFG:-cfgrs}"
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

# Tutto passa dal router, e non è una comodità: è la sola porta da cui il cluster si vede
# per intero. Un config server sa dove stanno i chunk ma non serve i documenti; uno shard
# serve i suoi e non sa degli altri.
#
# Sulla password: `mongosh` la riceve con `--password`, e dentro il container non resta
# leggibile — la 2.10.0 riscrive il proprio argv. Dove resterebbe leggibile è
# sull'host, nella riga di comando del client `docker`, che nessuno riscrive: per questo
# NON si passa con `-e` (ADR-0054, misurato in V-047). Quello che protegge davvero è che
# sia una password di laboratorio e che il file che la porta stia fuori dal repository.
interroga() {
  compose exec -T mongos \
    mongosh --quiet --host localhost \
      --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
      lab --eval "$1" 2>/dev/null | tail -1 | tr -d '\r'
}

printf 'Prova dello stack 03 — sharded cluster — profilo %s — %s\n' \
  "${PROFILO}" "$(date '+%F %H:%M')"

# --- I container ci sono e sono sani --------------------------------------------------
titolo "Stato dei nodi"

ASSENTI=0
for servizio in "${MONGOD[@]}" "${ROUTER[@]}"; do
  salute="$(docker inspect "sh-${servizio}" --format '{{.State.Health.Status}}' 2>/dev/null)"
  if [[ -z "${salute}" ]]; then
    errore "il container sh-${servizio} non esiste — esegui prima «make up-03»"
    ASSENTI=$((ASSENTI + 1))
  else
    confronta "salute di ${servizio}" "healthy" "${salute}"
  fi
done

# Ci si ferma solo se un container manca del tutto, non se è malato: la distinzione è
# quella di smoke-02. Con un nodo malato le domande interessanti hanno ancora una
# risposta; con un container inesistente non esiste nemmeno la connessione.
if (( ASSENTI > 0 )); then
  printf '\nSuperati: %d · Errori: %d\n' "${SUPERATI}" "${ERRORI}"
  printf 'Mancano %d container: lo stack non è avviato nel profilo %s.\n' \
    "${ASSENTI}" "${PROFILO}"
  exit 1
fi

# I sei one-shot devono essere MORTI, e morti bene. È il verdetto vero della catena:
# `up --wait` da solo non lo dà, perché a un one-shot senza healthcheck applica la
# soglia `running`, soddisfatta nell'istante in cui parte (V-056).
for unoshot in "${UNOSHOT[@]}"; do
  stato="$(docker inspect "sh-${unoshot}" --format '{{.State.Status}}/{{.State.ExitCode}}' 2>/dev/null)"
  confronta "${unoshot} ha finito bene" "exited/0" "${stato}"
done

# La sentinella invece deve essere VIVA, ed è l'unico servizio dello stack per cui
# «running» è il verdetto giusto: esiste per non partire finché la catena non è finita
# (ADR-0062). Se è in `Created` la catena si è rotta a monte.
stato_sentinella="$(docker inspect sh-up-03 --format '{{.State.Status}}' 2>/dev/null)"
confronta "la sentinella up-03 è in piedi" "running" "${stato_sentinella}"
if [[ "${stato_sentinella}" == "created" ]]; then
  nota "up-03 in «created» significa che seed o add-shard non sono usciti 0"
fi

# `mongod` e `mongos` come PID 1 ricevono direttamente il SIGTERM di `docker stop` e
# chiudono puliti. Qui conta anche per il router: la scena del Blocco 3 ne ferma uno.
for servizio in "${MONGOD[@]}"; do
  comando="$(docker exec "sh-${servizio}" cat /proc/1/cmdline 2>/dev/null | tr '\0' ' ' | sed 's/ *$//')"
  case "${comando}" in
    mongod*) ok "mongod è PID 1 su ${servizio}" ;;
    *)       errore "PID 1 non è mongod su ${servizio}: «${comando}»" ;;
  esac
done
for servizio in "${ROUTER[@]}"; do
  comando="$(docker exec "sh-${servizio}" cat /proc/1/cmdline 2>/dev/null | tr '\0' ' ' | sed 's/ *$//')"
  case "${comando}" in
    mongos*) ok "mongos è PID 1 su ${servizio}" ;;
    *)       errore "PID 1 non è mongos su ${servizio}: «${comando}»" ;;
  esac
done

# --- Il keyfile: esiste, è uguale ovunque, ed è chiuso --------------------------------
titolo "Keyfile"

# Qui i file da confrontare sono di più che sullo stack 02, e includono i ROUTER: anche
# `mongos` si autentica verso il cluster con lo stesso segreto. Un keyfile diverso sul
# solo router dà un cluster in cui i nodi si parlano fra loro e nessuno parla al router.
IMPRONTE=()
DISCORDI=0
for servizio in "${MONGOD[@]}" "${ROUTER[@]}"; do
  impronta="$(docker exec "sh-${servizio}" sha256sum /keyfile/mongo-keyfile 2>/dev/null | cut -d' ' -f1)"
  IMPRONTE+=("${servizio}=${impronta:0:12}")
  if [[ -z "${impronta}" || ( -n "${PRIMA:-}" && "${impronta}" != "${PRIMA}" ) ]]; then
    DISCORDI=$((DISCORDI + 1))
  fi
  PRIMA="${impronta}"
done
if (( DISCORDI == 0 )); then
  ok "lo stesso keyfile su ${#MONGOD[@]} mongod e ${#ROUTER[@]} mongos (${PRIMA:0:12}…)"
else
  errore "i keyfile non coincidono: ${IMPRONTE[*]}"
fi

# 400 e non 644: mongod rifiuta di partire con un keyfile che considera «too open», ed è
# la ragione per cui il file nasce dentro un volume nominato e non arriva dall'host, dove
# macOS non conserva i permessi (ADR-0014, V-021).
permessi="$(docker exec sh-cfg1 stat -c '%a' /keyfile/mongo-keyfile 2>/dev/null)"
confronta "permessi del keyfile" "${PERMESSI_KEYFILE}" "${permessi}"

if docker exec sh-cfg1 sh -c 'touch /keyfile/prova 2>/dev/null'; then
  errore "sh-cfg1 può scrivere nel volume del keyfile: il montaggio non è :ro"
  docker exec sh-cfg1 rm -f /keyfile/prova 2>/dev/null
else
  ok "il volume del keyfile è montato in sola lettura sui nodi"
fi

# --- I tre ruoli, e il fatto che siano tre --------------------------------------------
titolo "Topologia dello sharded cluster"

# `isdbgrid` è la risposta che solo un router dà, e la differenza fra «c'è un mongod
# sulla porta 27117» e «c'è un router» è tutta qui.
confronta "mongos è un router" "isdbgrid" "$(interroga 'print(db.hello().msg)')"

# LA RIGA CHE PRENDE IL REFUSO. Il caso più cattivo dei sei misurati in V-057 è un nome
# di replica set sbagliato di due lettere dentro `--configdb`: tutto parte, il router
# resta unhealthy, e nel suo log il nome giusto non compare mai. `make stack-check` lo
# prende leggendo il file; questo lo prende sul cluster acceso, e i due controlli si
# coprono a vicenda perché guardano due cose diverse — quello che è scritto e quello che
# gira.
configsvr="$(interroga 'const s = db.serverStatus().sharding; print(s ? s.configsvrConnectionString.split("/")[0] : "assente")')"
confronta "il router punta al replica set dei config server" "${REPLICA_CFG}" "${configsvr}"

# `sh.status()` è il comando da mostrare dal vivo, ma STAMPA e non restituisce niente:
# da uno script si interroga `config.shards`, che è la verità del cluster. È la stessa
# distinzione fra presentazione e verità che fa `20-add-shard.js`.
confronta "shard registrati" "${SHARD_ATTESI}" \
  "$(interroga 'print(db.getSiblingDB("config").shards.countDocuments({}))')"

confronta "shard registrati per nome" "${REPLICA_SHARD1},${REPLICA_SHARD2}" \
  "$(interroga 'print(db.getSiblingDB("config").shards.find({}, {_id: 1}).toArray().map(s => s._id).sort().join(","))')"

# `state: 1` è la riga che dice «questo shard partecipa». Uno shard a 0 è drenato o in
# uscita, e un cluster con uno shard a 0 continua a rispondere.
confronta "shard in stato attivo (state: 1)" "${SHARD_ATTESI}" \
  "$(interroga 'print(db.getSiblingDB("config").shards.countDocuments({state: 1}))')"

# Gli shard sono replica set, e nel profilo `completo` hanno tre membri: il conteggio si
# legge dalla stringa registrata nel config server, che è quella che i client ricevono.
for insieme in "${REPLICA_SHARD1}" "${REPLICA_SHARD2}"; do
  membri="$(interroga "const s = db.getSiblingDB('config').shards.findOne({_id: '${insieme}'}); print(s ? s.host.split('/')[1].split(',').length : 0)")"
  confronta "membri registrati per ${insieme}" "${MEMBRI_PER_SET}" "${membri}"
done

# I nomi con cui gli shard sono registrati finiscono nei metadati del cluster e da lì
# tornano a ogni client: devono essere nomi di servizio Compose con la porta INTERNA
# (ADR-0021). Un indirizzo IP qui è un indirizzo IP nella configurazione del cluster.
ospiti="$(interroga 'print(db.getSiblingDB("config").shards.find().toArray().map(s => s.host).join(" "))')"
if [[ "${ospiti}" =~ ([0-9]{1,3}\.){3}[0-9]{1,3} ]]; then
  errore "gli shard sono registrati con indirizzi IP: ${ospiti}"
elif [[ "${ospiti}" =~ 2711[78] ]]; then
  errore "gli shard sono registrati con le porte pubblicate: ${ospiti}"
else
  ok "shard registrati per nome di servizio e porta interna"
fi

# Il balancer acceso non sposta niente su un cluster equilibrato, e la sua utilità qui è
# di essere una cosa in più che può essere spenta per sbaglio: un cluster con il balancer
# fermo funziona finché non serve.
confronta "balancer attivo" "true" "$(interroga 'print(sh.getBalancerState())')"

# Ogni database ha uno shard PRIMARIO, dove finiscono le collezioni NON distribuite. È il
# concetto che manca a chi arriva dal replica set, e la prova sta più sotto: la
# collezione della prova di scrittura non è distribuita e vive tutta lì.
primario="$(interroga 'const d = db.getSiblingDB("config").databases.findOne({_id: "lab"}); print(d ? d.primary : "assente")')"
if [[ "${primario}" == "${REPLICA_SHARD1}" || "${primario}" == "${REPLICA_SHARD2}" ]]; then
  ok "il database lab ha uno shard primario: ${primario}"
else
  errore "il database lab non ha uno shard primario riconoscibile: «${primario}»"
fi

# --- Il router non è un database ------------------------------------------------------
titolo "Il router non ha storage"

# È la differenza che rende `mongos` sostituibile e i suoi container privi di volume, ed
# è verificabile in una riga: nella risposta di `serverStatus()` la sezione `wiredTiger`
# semplicemente NON C'È. Non è vuota, non è a zero: manca.
confronta "sezione wiredTiger su mongos" "assente" \
  "$(interroga 'print(db.serverStatus().wiredTiger ? "presente" : "assente")')"

# La controprova dal lato dei container, e dentro c'è una sorpresa che è costata un
# falso allarme: l'immagine di MongoDB dichiara `VOLUME /data/db` nel proprio
# Dockerfile, quindi Docker crea un volume ANONIMO su ogni container che ne nasce —
# anche su `mongos`, che là dentro non scriverà mai niente. Cercare `/data/db` fra le
# destinazioni montate lo trova su tutti e non distingue niente (misurato in V-058).
#
# Quello che distingue davvero un nodo da un router è il volume NOMINATO: `dati-cfg1`,
# `dati-shard1a`, … sono gli unici che il file Compose chiede per nome, gli unici che
# sopravvivono a un `down` e gli unici che `down -v` cancella. Il router non ne ha, e
# per questo è l'unico servizio dello stack che si può buttare via e rifare.
for servizio in "${ROUTER[@]}"; do
  nominati="$(docker inspect "sh-${servizio}" --format '{{range .Mounts}}{{.Name}} {{end}}' 2>/dev/null)"
  if [[ "${nominati}" == *"dati-"* ]]; then
    errore "${servizio} ha un volume dati nominato: un router non ha niente da conservare"
  else
    ok "${servizio} non ha volumi dati nominati (solo l'anonimo che l'immagine impone)"
  fi
done

# E il contrario, che è la metà della coppia che conta: ogni mongod deve avere il SUO
# volume nominato. Un nodo che gira sul volume anonimo dell'immagine funziona benissimo
# e perde tutto al primo `docker compose down`, senza dire niente a nessuno.
#
# Fino al Task 7 il controllo finiva qui, e per questo ha approvato per quattro giorni
# uno stack rotto. Che il volume nominato ESISTA non dice niente su DOVE il processo
# scrive: i config server avevano `dati-cfgN` regolarmente montato su /data/db e
# scrivevano in /data/configdb, perché l'entrypoint dell'immagine porta là il dbpath
# predefinito quando trova `--configsvr`. Il volume nominato restava vuoto, i
# metadati stavano nell'anonimo, e `down` li buttava: al riavvio il cluster non
# riconosceva più i propri shard (V-060, ADR-0067).
#
# Da qui in avanti il controllo confronta le due cose. Il dbpath si ricava dal comando
# del container con la stessa regola di `check_stack.py`, e le due guardie sono apposta
# ridondanti: quella statica giudica il file, questa il processo che sta girando, e
# solo la seconda vede un container avviato con un file diverso da quello del repo.
dbpath_di() {
  comando="$(docker inspect "sh-$1" --format '{{join .Config.Cmd " "}}' 2>/dev/null)"
  if [[ "${comando}" == *"--dbpath "* ]]; then
    resto="${comando#*--dbpath }"
    printf '%s' "${resto%% *}"
  elif [[ "${comando}" == *"--configsvr"* ]]; then
    printf '/data/configdb'
  else
    printf '/data/db'
  fi
}

SENZA_VOLUME=0
for servizio in "${MONGOD[@]}"; do
  nominati="$(docker inspect "sh-${servizio}" --format '{{range .Mounts}}{{.Name}} {{end}}' 2>/dev/null)"
  if [[ "${nominati}" != *"dati-${servizio}"* ]]; then
    errore "${servizio} non ha il volume nominato dati-${servizio}: i dati non sopravvivono a down"
    SENZA_VOLUME=$((SENZA_VOLUME + 1))
    continue
  fi
  destinazione="$(docker inspect "sh-${servizio}" \
    --format '{{range .Mounts}}{{.Name}}={{.Destination}}
{{end}}' 2>/dev/null | grep "dati-${servizio}=" | cut -d= -f2)"
  percorso="$(dbpath_di "${servizio}")"
  if [[ "${destinazione}" != "${percorso}" ]]; then
    errore "${servizio}: dati-${servizio} è montato su «${destinazione}» ma mongod scrive in «${percorso}»"
    SENZA_VOLUME=$((SENZA_VOLUME + 1))
  fi
done
if (( SENZA_VOLUME == 0 )); then
  ok "ciascuno dei ${#MONGOD[@]} mongod scrive nel proprio volume nominato dati-…"
fi

# --- Senza credenziali non si entra ---------------------------------------------------
titolo "Autenticazione"

# Una connessione anonima al router deve essere RIFIUTATA, e il codice atteso è 13
# (Unauthorized) — non un errore di rete, non un timeout: il router risponde, e dice no.
anonimo="$(compose exec -T mongos mongosh --quiet --host localhost lab \
  --eval 'try { db.ordini.countDocuments(); print("PASSATO") } catch (e) { print(e.codeName + "/" + e.code) }' \
  2>/dev/null | tail -1 | tr -d '\r')"
confronta "connessione senza credenziali al router" "Unauthorized/13" "${anonimo}"
if [[ "${anonimo}" == "PASSATO" ]]; then
  nota "una lettura anonima è riuscita: il keyfile non sta attivando l'autorizzazione"
fi

# Una password sbagliata deve fallire per il motivo giusto: se qui uscisse Unauthorized
# invece di AuthenticationFailed, vorrebbe dire che la connessione non ha nemmeno provato
# ad autenticarsi, e il controllo di sopra proverebbe meno di quanto sembra.
sbagliata="$(compose exec -T mongos mongosh --quiet --host localhost \
  --username "${UTENTE}" --password "password-che-non-e-quella" --authenticationDatabase admin lab \
  --eval 'print("PASSATO")' 2>&1 | grep -o 'MongoServerError.*' | head -1)"
if [[ "${sbagliata}" =~ [Aa]uthentication ]]; then
  ok "una password sbagliata viene rifiutata come errore di autenticazione"
else
  errore "una password sbagliata non è stata rifiutata come atteso: «${sbagliata}»"
fi

# IL CONTROLLO CHE SULLO STACK 02 NON ESISTE, e che è una lezione prima di essere una
# verifica: l'amministratore del cluster NON È un utente degli shard. In uno sharded
# cluster gli utenti stanno nel database `admin` dei config server, e un `mongod` di
# shard interrogato in diretta autentica contro i propri, che non ci sono. Misurato: la
# stessa coppia utente/password che funziona sul router risponde «Authentication failed»
# su shard1a (V-058).
#
# Va verificato perché è la porta di servizio del cluster: se un giorno passasse,
# significherebbe che qualcuno ha creato utenti direttamente sugli shard, e da lì in poi
# esisterebbero due anagrafiche che nessuno tiene allineate.
diretto="$(compose exec -T "${SHARD1[0]}" mongosh --quiet --host localhost \
  --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
  --eval 'print("PASSATO")' 2>&1 | grep -o 'MongoServerError.*' | head -1)"
if [[ "${diretto}" =~ [Aa]uthentication ]]; then
  ok "l'amministratore del cluster non è un utente dello shard (è la regola, non un guasto)"
  nota "gli utenti di uno sharded cluster vivono sui config server, non sugli shard"
else
  errore "una connessione diretta a ${SHARD1[0]} con le credenziali del cluster non è stata rifiutata: «${diretto}»"
fi

# --- Quello che gira è quello che abbiamo pinnato -------------------------------------
titolo "Versione e limiti"

confronta "versione servita dal router" "${VERSIONE_ATTESA}" "$(interroga 'print(db.version())')"

digest_atteso="$(sed -n 's/^MONGO_IMAGE=.*@\(sha256:[0-9a-f]*\)$/\1/p' "${AMBIENTE}")"
DIVERSI=0
for servizio in "${MONGOD[@]}" "${ROUTER[@]}"; do
  reale="$(docker inspect "sh-${servizio}" --format '{{index .Image}}' 2>/dev/null)"
  digest="$(docker inspect "${reale}" --format '{{index .RepoDigests 0}}' 2>/dev/null)"
  [[ "${digest##*@}" == "${digest_atteso}" ]] || {
    errore "digest diverso su ${servizio}: ${digest##*@}"
    DIVERSI=$((DIVERSI + 1))
  }
done
if (( DIVERSI == 0 )); then
  ok "tutti i nodi girano sullo stesso digest pinnato (${digest_atteso:0:19}…)"
fi

# I limiti si leggono dai container e non con `hostInfo()`, e la ragione è la scoperta
# di sopra: su uno shard non ci si può autenticare in diretta, quindi `hostInfo()` non è
# raggiungibile là dove servirebbe. `docker inspect` invece risponde per tutti e legge
# la stessa cosa che il file ha chiesto.
for servizio in "${CONFIG[@]}"; do
  confronta "memoria di ${servizio} (byte)" "${MEMORIA_CFG_BYTE}" \
    "$(docker inspect "sh-${servizio}" --format '{{.HostConfig.Memory}}' 2>/dev/null)"
done
for servizio in "${SHARD1[@]}" "${SHARD2[@]}"; do
  confronta "memoria di ${servizio} (byte)" "${MEMORIA_SHARD_BYTE}" \
    "$(docker inspect "sh-${servizio}" --format '{{.HostConfig.Memory}}' 2>/dev/null)"
done
for servizio in "${ROUTER[@]}"; do
  confronta "memoria di ${servizio} (byte)" "${MEMORIA_MONGOS_BYTE}" \
    "$(docker inspect "sh-${servizio}" --format '{{.HostConfig.Memory}}' 2>/dev/null)"
done

# La cache che WiredTiger ha davvero aperto, letta dalla riga di avvio del motore. È il
# controllo che MongoDB non fa da sé: una cache più grande del limite del container viene
# accettata senza un avviso che colleghi le due cifre (V-009). Qui i nodi sono fino a
# nove, e l'errore costerebbe nove volte.
for servizio in "${MONGOD[@]}"; do
  cache="$(docker logs "sh-${servizio}" 2>&1 | grep -o 'cache_size=[0-9]*[MG]' | head -1)"
  if [[ -z "${cache}" ]]; then
    errore "nessuna riga di apertura di WiredTiger nel log di ${servizio}"
    nota "la rotazione del log può averla mangiata: «docker compose restart ${servizio}»"
  else
    confronta "cache di WiredTiger su ${servizio}" "${CACHE_ATTESA}" "${cache}"
  fi
done

# E il router, che una cache non ce l'ha proprio: `mongos` rifiuta di partire se gliela
# si chiede — «unrecognised option '--wiredTigerCacheSizeGB'» (V-057) — quindi nel suo
# log la parola non deve comparire nemmeno una volta.
for servizio in "${ROUTER[@]}"; do
  occorrenze="$(docker logs "sh-${servizio}" 2>&1 | grep -c 'cache_size')"
  confronta "occorrenze di cache_size nel log di ${servizio}" "0" "${occorrenze}"
done

# --- Le porte pubblicate, una per router ----------------------------------------------
titolo "Raggiungibilità"

# Solo i router pubblicano una porta, e l'assenza sugli altri è deliberata: un client
# entra dal router, e i nodi si parlano dentro la rete Compose (ADR-0021).
for servizio in "${ROUTER[@]}"; do
  porta="$(compose port "${servizio}" 27017 2>/dev/null | tail -1)"
  if [[ -z "${porta}" ]]; then
    errore "nessuna porta pubblicata per ${servizio}:27017"
  elif python3 -c "import socket,sys; socket.create_connection(('127.0.0.1', int(sys.argv[1])), 3).close()" \
         "${porta##*:}" 2>/dev/null; then
    ok "${servizio} risponde su ${porta}"
  else
    errore "${servizio}: la porta ${porta} non risponde dall'host"
  fi
done

# --- I dati di demo sono quelli ------------------------------------------------------
titolo "Dati di demo"

impronta="$(interroga 'const a = db.ordini.aggregate([{$group:{_id:null, n:{$sum:1}, tot:{$sum:"$importo"}, righe:{$sum:"$righe"}}}]).toArray()[0]; print(a ? a.n + " " + a.tot.toFixed(2) + " " + a.righe : "collezione vuota")')"
confronta "impronta di lab.ordini" \
  "${DOCUMENTI_ATTESI} ${IMPORTO_ATTESO} ${RIGHE_ATTESE}" "${impronta}"
if [[ "${impronta}" != "${DOCUMENTI_ATTESI} ${IMPORTO_ATTESO} ${RIGHE_ATTESE}" ]]; then
  nota "il seed non ricarica se i documenti ci sono già: «make seed-03» forza il giro"
  nota "e «make reset-03» riparte da volumi dati vuoti conservando il keyfile"
fi

# Due indici, e uno non l'ha chiesto nessuno: `shardCollection` con una chiave hashed
# crea l'indice che le serve. È l'unica differenza rispetto agli altri due stack, dove
# `lab.ordini` ha il solo `_id_` perché la demo confronta una query con e senza indice.
confronta "indici su lab.ordini" "${INDICI_ATTESI}" \
  "$(interroga 'print(db.ordini.getIndexes().map(i => i.name).sort().join(","))')"

# --- LA MISURA CHE DISTINGUE UNO SHARDED CLUSTER DA UN REPLICA SET --------------------
titolo "Distribuzione"

# Tutto quello che sta sopra passerebbe identico su un cluster che ha messo i ventimila
# documenti su un solo shard. Un cluster così funziona: risponde, scrive, legge, mostra
# due shard in `sh.status()`. Non partiziona niente, e questa è l'unica sezione che se
# ne accorge.

confronta "shard key di lab.ordini" '{"_id":"hashed"}' \
  "$(interroga 'const m = db.getSiblingDB("config").collections.findOne({_id: "lab.ordini"}); print(m ? JSON.stringify(m.key) : "non distribuita")')"

chunk="$(interroga 'const c = db.getSiblingDB("config"); const m = c.collections.findOne({_id: "lab.ordini"}); print(m ? c.chunks.countDocuments({uuid: m.uuid}) : 0)')"
if [[ ! "${chunk}" =~ ^[0-9]+$ ]] || (( chunk < CHUNK_MINIMI )); then
  errore "chunk di lab.ordini: ${chunk}, attesi almeno ${CHUNK_MINIMI} (uno per shard)"
elif (( chunk == CHUNK_INIZIALI )); then
  ok "chunk di lab.ordini: ${chunk} — la geometria iniziale, due per shard"
elif (( chunk == CHUNK_MINIMI )); then
  ok "chunk di lab.ordini: ${chunk} — uno per shard: l'AutoMerger ha già fuso"
else
  ok "chunk di lab.ordini: ${chunk}"
  nota "né ${CHUNK_INIZIALI} né ${CHUNK_MINIMI}: o gli shard sono aumentati, o qualcuno"
  nota "ha passato numInitialChunks, o un chunk si è diviso"
fi

# `getShardDistribution()` è il comando da mostrare dal vivo e stampa soltanto;
# `$shardedDataDistribution` restituisce documenti, e da uno script serve questo.
distribuzione="$(interroga 'const r = db.getSiblingDB("admin").aggregate([{$shardedDataDistribution: {}}, {$match: {ns: "lab.ordini"}}]).toArray(); if (!r.length) { print("nessuna") } else { print(r[0].shards.map(s => s.shardName + "=" + s.numOwnedDocuments).sort().join(" ")) }')"

if [[ "${distribuzione}" == "nessuna" ]]; then
  errore "lab.ordini non risulta distribuita su nessuno shard"
else
  CON_DOCUMENTI=0
  SQUILIBRIO=0
  for pezzo in ${distribuzione}; do
    nome="${pezzo%%=*}"; quanti="${pezzo##*=}"
    # In decimi di punto, perché fra 49 % e 51 % la differenza è tutta lì: bash conta
    # solo interi, quindi si moltiplica per mille e si rimette la virgola a mano.
    decimi=$(( quanti * 1000 / DOCUMENTI_ATTESI ))
    quota=$(( decimi / 10 ))
    if (( quanti > 0 )); then
      CON_DOCUMENTI=$((CON_DOCUMENTI + 1))
    fi
    if (( quota < QUOTA_MINIMA )); then
      SQUILIBRIO=$((SQUILIBRIO + 1))
    fi
    nota "${nome}: ${quanti} documenti (${quota},$(( decimi % 10 )) %)"
  done

  confronta "shard che contengono documenti" "${SHARD_ATTESI}" "${CON_DOCUMENTI}"
  if (( CON_DOCUMENTI < SHARD_ATTESI )); then
    nota "tutti i documenti su un solo shard: la shard key non sta distribuendo."
    nota "È il sintomo di una chiave monotona, e il cluster non se ne lamenta."
  fi

  if (( SQUILIBRIO == 0 )); then
    ok "nessuno shard sotto il ${QUOTA_MINIMA} % dei documenti"
  else
    errore "${SQUILIBRIO} shard sotto il ${QUOTA_MINIMA} % dei documenti"
  fi
fi

# --- Il baratto della shard key, misurato ---------------------------------------------
titolo "Instradamento"

# Le due righe che rendono visibile quello che la shard key compra e quello che costa, e
# sono la stessa interrogazione con due filtri diversi. Con l'UGUAGLIANZA sulla chiave il
# router sa dove andare e chiede a UNO shard. Con un INTERVALLO sulla stessa chiave non
# lo sa più — l'hash sparpaglia apposta i valori contigui — e chiede a TUTTI.
#
# Non è un difetto della configurazione: è il prezzo dichiarato di una chiave hashed
# («mongos can target queries with equality matches to a single shard», S-066), e uno
# smoke che lo misura impedisce che diventi una sorpresa il giorno in cui una query lenta
# viene attribuita alla rete.
mirata="$(interroga 'const e = db.ordini.find({_id: 42}).explain(); const s = e.queryPlanner.winningPlan.shards; print(s ? s.length : -1)')"
confronta "shard interrogati da una uguaglianza su _id" "1" "${mirata}"

larga="$(interroga 'const e = db.ordini.find({_id: {$gte: 100, $lt: 200}}).explain(); const s = e.queryPlanner.winningPlan.shards; print(s ? s.length : -1)')"
confronta "shard interrogati da un intervallo su _id" "${SHARD_ATTESI}" "${larga}"
if [[ "${larga}" == "1" ]]; then
  nota "un intervallo servito da un solo shard significa chiave NON hashed:"
  nota "le letture contigue sarebbero veloci e le scritture andrebbero tutte là"
fi

documento="$(interroga 'const d = db.ordini.findOne({_id: 42}); print(d ? d._id + "|" + d.citta + "|" + d.stato : "assente")')"
confronta "lettura mirata di _id 42" "42|Ancona|spedito" "${documento}"

# --- Scrittura con w: majority attraverso il router -----------------------------------
titolo "Scrittura con w: majority e rilettura"

# Collezione separata da lab.ordini, e cancellata alla fine: se questa prova scrivesse
# nella collezione della demo, l'impronta di sopra cambierebbe a ogni esecuzione e il
# controllo che la sorveglia diventerebbe rumore.
#
# `wtimeout` non è prudenza formale: senza, una scrittura con w: "majority" su un set che
# ha perso la maggioranza aspetta per sempre, e una prova che non finisce è peggio di una
# che fallisce.
#
# Attraverso il router `w: "majority"` vale sulla maggioranza dello shard che riceve il
# documento, non sulla somma dei nodi del cluster: è una distinzione che sul palco vale la
# pena dire, perché «maggioranza» qui non significa più «di tutto».
scritto="$(interroga 'const r = db.prova_smoke.insertOne({_id: "smoke", quando: new Date()}, {writeConcern: {w: "majority", wtimeout: 10000}}); print(r.acknowledged)')"
confronta "scrittura con w: majority accettata" "true" "${scritto}"

riletto="$(interroga 'print(db.prova_smoke.countDocuments({_id: "smoke"}))')"
confronta "rilettura del documento scritto" "1" "${riletto}"

# E la prova dello shard primario: una collezione che nessuno ha distribuito non compare
# fra le collezioni distribuite, e sta tutta su un nodo solo.
confronta "prova_smoke non è distribuita" "no" \
  "$(interroga 'print(db.getSiblingDB("config").collections.findOne({_id: "lab.prova_smoke"}) ? "sì" : "no")')"

interroga 'db.prova_smoke.drop({writeConcern: {w: "majority", wtimeout: 10000}})' > /dev/null

# --- Il canale di log è quello deciso -------------------------------------------------
titolo "Log"

# ADR-0030: nessun --logpath, perché è una redirezione e spegnerebbe questo comando.
righe_log="$(compose logs --tail 20 mongos 2>/dev/null | grep -c 'msg')"
if (( righe_log > 0 )); then
  ok "docker compose logs restituisce righe (${righe_log} nelle ultime 20 di mongos)"
else
  errore "docker compose logs è muto: qualcuno ha aggiunto --logpath?"
fi

# Senza questi due limiti il file di log cresce finché c'è disco, e qui i file sono fino
# a undici.
for servizio in "${MONGOD[@]}" "${ROUTER[@]}"; do
  rotazione="$(docker inspect "sh-${servizio}" --format '{{index .HostConfig.LogConfig.Config "max-size"}} {{index .HostConfig.LogConfig.Config "max-file"}}' 2>/dev/null)"
  confronta "rotazione dei log di ${servizio}" "10m 3" "${rotazione}"
done

# --- Esito ----------------------------------------------------------------------------
printf '\nSuperati: %d · Errori: %d\n' "${SUPERATI}" "${ERRORI}"
if (( ERRORI > 0 )); then
  printf 'Lo stack 03 non si comporta come promesso (profilo %s).\n' "${PROFILO}"
  exit 1
fi
printf 'Lo stack 03 fa quello che il file Compose promette (profilo %s).\n' "${PROFILO}"
