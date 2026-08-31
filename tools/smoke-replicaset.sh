#!/usr/bin/env bash
# Prova end-to-end dello stack 02 — replica set a tre membri. Presuppone lo stack già
# avviato (`make up-02`). Errori bloccanti -> uscita 1.
#
# Niente `set -e`, per la stessa ragione del preflight e di smoke-01: una prova che si
# ferma al primo problema costringe a tre giri. Deve dire tutto quello che non va in una
# volta sola.
#
# Non verifica che il file Compose sia scritto bene — quello è `make stack-check`, che
# legge il file. Qui si verifica che i container che ne sono nati si comportino come il
# file prometteva.
#
# La differenza rispetto a smoke-01 non è la lunghezza: è che metà dei controlli qui
# riguardano cose che su un'istanza singola non esistono. Un solo primario, due
# secondari, una scrittura che sopravvive alla maggioranza, e — soprattutto — una
# connessione senza credenziali che viene RIFIUTATA. Su smoke-01 lo stesso controllo
# esiste al contrario, e va detto ad alta voce: là passa, e passa apposta (ADR-0005).
set -uo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="${RADICE}/docker/02-replicaset/compose.yaml"
AMBIENTE="${RADICE}/tools/images.env"
SEGRETI="${RADICE}/docker/02-replicaset/.env"

# Valori attesi. Non sono numeri magici: ognuno è misurato e registrato in Sources.md.
VERSIONE_ATTESA="7.0.40"       # ADR-0028
MEMORIA_ATTESA_MIB=768         # compose.yaml, mem_limit dei membri — design §5.1
CACHE_ATTESA_BYTE=268435456    # 0,25 GiB = 256 MiB esatti, V-009 e V-012
MEMBRI_ATTESI=3
PERMESSI_KEYFILE="400"         # V-021: mongod rifiuta un keyfile più aperto

# L'impronta del dataset. Sono GLI STESSI TRE NUMERI di smoke-01, e la coincidenza è il
# controllo: i due stack devono produrre lo stesso dataset documento per documento,
# perché una parte della demo confronta la stessa interrogazione sull'uno e sull'altro.
# Se questi tre numeri divergono da quelli di smoke-01, uno dei due seed è stato
# modificato senza l'altro.
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

confronta() {
  local descrizione="$1" atteso="$2" ottenuto="$3"
  if [[ "${ottenuto}" == "${atteso}" ]]; then
    ok "${descrizione}: ${ottenuto}"
  else
    errore "${descrizione}: atteso ${atteso}, ottenuto «${ottenuto}»"
  fi
}

# --- Le credenziali, che non stanno nel repository -----------------------------------
#
# Il file arriva da fuori (ADR-0014). Se manca, non c'è prova possibile: qui si esce
# subito, perché ogni controllo successivo fallirebbe per lo stesso motivo e stamperebbe
# dieci righe rosse che dicono tutte la stessa cosa.
if [[ ! -f "${SEGRETI}" ]]; then
  printf 'Manca %s.\n' "${SEGRETI}" >&2
  printf 'Crearlo con: cp %s.example %s, poi riempire PASSWORD_AMMINISTRATORE.\n' \
    "${SEGRETI}" "${SEGRETI}" >&2
  exit 1
fi
set -a; . "${SEGRETI}"; set +a
UTENTE="${UTENTE_AMMINISTRATORE:-admin}"
PASSWORD="${PASSWORD_AMMINISTRATORE:-}"
REPLICA="${NOME_REPLICA:-rs0}"

if [[ -z "${PASSWORD}" ]]; then
  printf 'PASSWORD_AMMINISTRATORE è vuota in %s.\n' "${SEGRETI}" >&2
  exit 1
fi

compose() {
  docker compose --env-file "${AMBIENTE}" --env-file "${SEGRETI}" -f "${COMPOSE}" "$@"
}

# Esegue JavaScript sul PRIMARIO, chiunque esso sia: `--host rs0/localhost:27017` fa
# scoprire la topologia al driver invece di fidarsi che mongo-rs-1 sia ancora primario.
# Dopo una demo di failover non lo è, e una prova che lo dà per scontato fallisce
# raccontando la cosa sbagliata.
#
# La password passa per `-e` e non sulla riga di comando di mongosh: dentro il container
# resta comunque leggibile in `ps`, ma è una password di lab e il file che la porta sta
# fuori dal repository. La riga esiste per non prendere l'abitudine, non per illusione
# di segretezza.
interroga() {
  compose exec -T -e SEGRETO="${PASSWORD}" mongo-rs-1 \
    mongosh --quiet --host "${REPLICA}/localhost:27017" \
      --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
      lab --eval "$1" 2>/dev/null | tail -1 | tr -d '\r'
}

# Come sopra, ma su un membro preciso e senza passare dalla replica: serve per chiedere
# a un secondario che cosa vede lui, che è una domanda diversa da «che cosa c'è nel set».
interroga_membro() {
  local membro="$1"
  compose exec -T "${membro}" \
    mongosh --quiet --host localhost \
      --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
      lab --eval "$2" 2>/dev/null | tail -1 | tr -d '\r'
}

printf 'Prova dello stack 02 — replica set — %s\n' "$(date '+%F %H:%M')"

# --- I container ci sono e sono sani -------------------------------------------------
titolo "Stato dei nodi"

ASSENTI=0
for membro in mongo-rs-1 mongo-rs-2 mongo-rs-3; do
  salute="$(docker inspect "${membro}" --format '{{.State.Health.Status}}' 2>/dev/null)"
  if [[ -z "${salute}" ]]; then
    errore "il container ${membro} non esiste — esegui prima «make up-02»"
    ASSENTI=$((ASSENTI + 1))
  else
    confronta "salute di ${membro}" "healthy" "${salute}"
  fi
done

# Ci si ferma qui SOLO se un container manca del tutto, non se è malato — ed è una
# distinzione misurata, non di principio. Fermando mongo-rs-3 la prima versione di questo
# script si arrestava dopo tre righe, e lasciava senza risposta le due domande che uno si
# fa proprio in quel momento: c'è ancora un primario? le scritture passano lo stesso? Con
# tre membri quelle risposte esistono e sono la lezione del talk; con un container
# inesistente non esiste nemmeno la connessione, e insistere produce dieci righe rosse
# che dicono tutte «non c'è».
if (( ASSENTI > 0 )); then
  printf '\nSuperati: %d · Errori: %d\n' "${SUPERATI}" "${ERRORI}"
  printf 'Mancano %d container su 3: lo stack non è avviato.\n' "${ASSENTI}"
  exit 1
fi

# I due one-shot devono essere MORTI, e morti bene. Un keyfile-init ancora in piedi
# significherebbe un `restart` sbagliato; un rs-init a zero è l'unico verdetto che dice
# che la replica esiste davvero (ADR-0041).
for unoshot in rs-keyfile-init rs-init; do
  stato="$(docker inspect "${unoshot}" --format '{{.State.Status}}/{{.State.ExitCode}}' 2>/dev/null)"
  confronta "${unoshot} ha finito bene" "exited/0" "${stato}"
done

# `mongod` come PID 1 riceve direttamente il SIGTERM di `docker stop` e chiude pulito.
# Qui conta il doppio rispetto allo stack 01: la scena di failover ferma un membro, e un
# membro che impiega i dieci secondi di grazia prima del SIGKILL rende la scena illeggibile.
for membro in mongo-rs-1 mongo-rs-2 mongo-rs-3; do
  comando="$(docker exec "${membro}" cat /proc/1/cmdline 2>/dev/null | tr '\0' ' ' | sed 's/ *$//')"
  case "${comando}" in
    mongod*) ok "mongod è PID 1 su ${membro}" ;;
    *)       errore "PID 1 non è mongod su ${membro}: «${comando}»" ;;
  esac
done

# --- Il keyfile: esiste, è uguale ovunque, ed è chiuso -------------------------------
titolo "Keyfile"

# Tre file identici byte per byte, o i membri si rifiutano a vicenda con un errore di
# autenticazione che sembra tutt'altro. Arrivano dallo stesso volume, quindi il controllo
# verifica soprattutto che il volume sia davvero lo stesso e sia davvero montato.
impronte=()
for membro in mongo-rs-1 mongo-rs-2 mongo-rs-3; do
  impronte+=("$(docker exec "${membro}" sha256sum /keyfile/mongo-keyfile 2>/dev/null | cut -d' ' -f1)")
done
if [[ -n "${impronte[0]}" && "${impronte[0]}" == "${impronte[1]}" && "${impronte[1]}" == "${impronte[2]}" ]]; then
  ok "lo stesso keyfile sui tre membri (${impronte[0]:0:12}…)"
else
  errore "i tre keyfile differiscono o mancano: ${impronte[*]}"
fi

# 400 e non 644: mongod rifiuta di partire con un keyfile che considera «too open», ed è
# la ragione per cui il file nasce dentro un volume nominato e non arriva dall'host, dove
# macOS non conserva i permessi (ADR-0014, V-021).
permessi="$(docker exec mongo-rs-1 stat -c '%a' /keyfile/mongo-keyfile 2>/dev/null)"
confronta "permessi del keyfile" "${PERMESSI_KEYFILE}" "${permessi}"

# In sola lettura per i membri: un membro non ha ragione di riscrivere il segreto.
if docker exec mongo-rs-1 sh -c 'touch /keyfile/prova 2>/dev/null'; then
  errore "mongo-rs-1 può scrivere nel volume del keyfile: il montaggio non è :ro"
  docker exec mongo-rs-1 rm -f /keyfile/prova 2>/dev/null
else
  ok "il volume del keyfile è montato in sola lettura sui membri"
fi

# --- La replica esiste, ed è fatta come la volevamo ----------------------------------
titolo "Topologia"

confronta "nome del replica set" "${REPLICA}" "$(interroga 'print(rs.status().set)')"
confronta "numero di membri" "${MEMBRI_ATTESI}" "$(interroga 'print(rs.status().members.length)')"

primari="$(interroga 'print(rs.status().members.filter(m => m.stateStr === "PRIMARY").length)')"
confronta "primari" "1" "${primari}"
secondari="$(interroga 'print(rs.status().members.filter(m => m.stateStr === "SECONDARY").length)')"
confronta "secondari" "2" "${secondari}"

malati="$(interroga 'print(rs.status().members.filter(m => m.health !== 1).map(m => m.name).join(",") || "nessuno")')"
confronta "membri non in salute" "nessuno" "${malati}"

# LA trappola del talk, e nasce dentro rs.initiate(). I nomi con cui i membri sono
# registrati finiscono nella configurazione della replica, e sono i nomi che il driver
# riceve quando scopre la topologia: un client fuori dalla rete Compose li riceve e non
# li risolve. Devono essere nomi di servizio con la porta INTERNA, mai indirizzi, mai le
# porte pubblicate (ADR-0021).
nomi="$(interroga 'print(rs.status().members.map(m => m.name).sort().join(" "))')"
confronta "membri registrati per nome di servizio" \
  "mongo-rs-1:27017 mongo-rs-2:27017 mongo-rs-3:27017" "${nomi}"
if [[ "${nomi}" =~ 2702[123] ]]; then
  nota "compaiono le porte pubblicate: la replica è stata inizializzata dall'host"
  nota "invece che dall'interno, e nessun container riuscirà a raggiungere i membri"
fi

# `priority: 2` sul primo membro rende PREVEDIBILE chi è primario all'avvio, che per una
# demo cronometrata vale più della simmetria. Non si pretende che sia primario ADESSO —
# dopo una prova di failover potrebbe non esserlo — si pretende che la priorità ci sia.
priorita="$(interroga 'const c = rs.conf(); print(c.members.map(m => m.host + "=" + m.priority).sort().join(" "))')"
confronta "priorità dei membri" \
  "mongo-rs-1:27017=2 mongo-rs-2:27017=1 mongo-rs-3:27017=1" "${priorita}"

# --- Senza credenziali non si entra --------------------------------------------------
titolo "Autenticazione"

# Il controllo che sullo stack 01 esiste al contrario. Qui una connessione anonima deve
# essere RIFIUTATA, e il codice atteso è 13 (Unauthorized) — non un errore di rete, non
# un timeout: il nodo risponde, e dice di no.
anonimo="$(compose exec -T mongo-rs-1 mongosh --quiet --host localhost lab \
  --eval 'try { db.ordini.countDocuments(); print("PASSATO") } catch (e) { print(e.codeName + "/" + e.code) }' \
  2>/dev/null | tail -1 | tr -d '\r')"
confronta "connessione senza credenziali" "Unauthorized/13" "${anonimo}"
if [[ "${anonimo}" == "PASSATO" ]]; then
  nota "una lettura anonima è riuscita: il keyfile non sta attivando l'autorizzazione"
fi

# Una password sbagliata deve fallire per il motivo giusto: 18 è AuthenticationFailed.
# Se qui uscisse 13 vorrebbe dire che la connessione non ha nemmeno provato ad
# autenticarsi, e il controllo di sopra proverebbe meno di quanto sembra.
sbagliata="$(compose exec -T mongo-rs-1 mongosh --quiet --host localhost \
  --username "${UTENTE}" --password "password-che-non-e-quella" --authenticationDatabase admin lab \
  --eval 'print("PASSATO")' 2>&1 | grep -o 'MongoServerError.*' | head -1)"
if [[ "${sbagliata}" =~ [Aa]uthentication ]]; then
  ok "una password sbagliata viene rifiutata come errore di autenticazione"
else
  errore "una password sbagliata non è stata rifiutata come atteso: «${sbagliata}»"
fi

# --- Quello che gira è quello che abbiamo pinnato ------------------------------------
titolo "Versione e limiti"

confronta "versione di mongod" "${VERSIONE_ATTESA}" "$(interroga 'print(db.version())')"

digest_atteso="$(sed -n 's/^MONGO_IMAGE=.*@\(sha256:[0-9a-f]*\)$/\1/p' "${AMBIENTE}")"
for membro in mongo-rs-1 mongo-rs-2 mongo-rs-3; do
  digest_reale="$(docker inspect "${membro}" --format '{{index .Image}}' 2>/dev/null)"
  digest_immagine="$(docker inspect "${digest_reale}" --format '{{index .RepoDigests 0}}' 2>/dev/null)"
  confronta "digest di ${membro}" "${digest_atteso}" "${digest_immagine##*@}"
done

# `Number(...)` non è ornamentale: memLimitMB è un Long, e `print()` di un Long stampa
# «Long('768')», non «768».
for membro in mongo-rs-1 mongo-rs-2 mongo-rs-3; do
  confronta "memoria vista da ${membro} (MiB)" "${MEMORIA_ATTESA_MIB}" \
    "$(interroga_membro "${membro}" 'print(Number(db.hostInfo().system.memLimitMB))')"
done

# Il controllo che MongoDB non fa: una cache più grande del limite di memoria viene
# accettata senza un avviso che colleghi le due cifre (V-009). Con tre membri l'errore
# costerebbe il triplo, e su un portatile che intanto proietta si paga subito.
for membro in mongo-rs-1 mongo-rs-2 mongo-rs-3; do
  cache="$(interroga_membro "${membro}" 'print(db.serverStatus().wiredTiger.cache["maximum bytes configured"])')"
  confronta "cache WiredTiger di ${membro} (byte)" "${CACHE_ATTESA_BYTE}" "${cache}"
  if [[ "${cache}" =~ ^[0-9]+$ ]] && (( cache > MEMORIA_ATTESA_MIB * 1024 * 1024 )); then
    errore "la cache di ${membro} supera il limite di memoria del container"
  fi
done

# --- Le porte pubblicate, una per membro ---------------------------------------------
titolo "Raggiungibilità"

for membro in mongo-rs-1 mongo-rs-2 mongo-rs-3; do
  porta="$(compose port "${membro}" 27017 2>/dev/null | tail -1)"
  if [[ -z "${porta}" ]]; then
    errore "nessuna porta pubblicata per ${membro}:27017"
  elif python3 -c "import socket,sys; socket.create_connection(('127.0.0.1', int(sys.argv[1])), 3).close()" \
         "${porta##*:}" 2>/dev/null; then
    ok "${membro} risponde su ${porta}"
  else
    errore "${membro}: la porta ${porta} non risponde dall'host"
  fi
done

# --- I dati di demo sono quelli, e sono gli stessi dello stack 01 --------------------
titolo "Dati di demo"

impronta="$(interroga 'const a = db.ordini.aggregate([{$group:{_id:null, n:{$sum:1}, tot:{$sum:"$importo"}, righe:{$sum:"$righe"}}}]).toArray()[0]; print(a ? a.n + " " + a.tot.toFixed(2) + " " + a.righe : "collezione vuota")')"
confronta "impronta di lab.ordini" \
  "${DOCUMENTI_ATTESI} ${IMPORTO_ATTESO} ${RIGHE_ATTESE}" "${impronta}"
if [[ "${impronta}" != "${DOCUMENTI_ATTESI} ${IMPORTO_ATTESO} ${RIGHE_ATTESE}" ]]; then
  nota "il seed non ricarica se i documenti ci sono già: «make seed-02» forza il giro"
  nota "e «make reset-02» riparte da volumi dati vuoti conservando il keyfile"
fi

indici="$(interroga 'print(db.ordini.getIndexes().map(i => i.name).join(","))')"
confronta "indici su lab.ordini" "_id_" "${indici}"

# --- La cosa che l'istanza singola non sa fare ---------------------------------------
titolo "Scrittura con w: majority e rilettura da un secondario"

# Collezione separata da lab.ordini, e cancellata alla fine: se questa prova scrivesse
# nella collezione della demo, l'impronta di sopra cambierebbe a ogni esecuzione e il
# controllo che la sorveglia diventerebbe rumore.
#
# `wtimeout` non è prudenza formale: senza, una scrittura con w: "majority" su un set che
# ha perso la maggioranza aspetta per sempre, e una prova che non finisce è peggio di una
# che fallisce.
scritto="$(interroga 'const r = db.prova_smoke.insertOne({_id: "smoke", quando: new Date()}, {writeConcern: {w: "majority", wtimeout: 10000}}); print(r.acknowledged)')"
confronta "scrittura con w: majority accettata" "true" "${scritto}"

# La rilettura si chiede a un SECONDARIO, e con `readPref` esplicito: senza, un secondario
# risponde «not primary» e la prova fallirebbe raccontando la cosa sbagliata. Che il
# documento sia già là subito dopo una w: "majority" non è fortuna — è la definizione:
# la maggioranza l'ha preso prima che la scrittura tornasse indietro.
riletto="$(interroga_membro mongo-rs-2 'db.getMongo().setReadPref("secondary"); print(db.prova_smoke.countDocuments({_id: "smoke"}))')"
confronta "rilettura da mongo-rs-2 (secondario)" "1" "${riletto}"

interroga 'db.prova_smoke.drop({writeConcern: {w: "majority", wtimeout: 10000}})' > /dev/null

# Il ritardo a riposo è di pochi millisecondi (V-027) e `optimeDate` ha granularità di un
# secondo, quindi qui ci si aspetta 0 e uno 0 non prova niente. Il controllo serve
# all'altro estremo: un ritardo di decine di secondi è un membro che sta faticando, e
# durante una demo è il genere di cosa che si vuole sapere prima di salire sul palco.
ritardo="$(interroga 'const s = rs.status(); const p = s.members.find(m => m.stateStr === "PRIMARY"); const max = Math.max(...s.members.filter(m => m.stateStr === "SECONDARY").map(m => (p.optimeDate - m.optimeDate) / 1000)); print(max)')"
if [[ "${ritardo}" =~ ^-?[0-9]+$ ]] && (( ritardo <= 10 )); then
  ok "ritardo di replica al più ${ritardo} s (granularità di optimeDate: 1 s)"
else
  errore "ritardo di replica anomalo: «${ritardo}» s"
fi

# --- Il canale di log è quello deciso ------------------------------------------------
titolo "Log"

# ADR-0030: nessun --logpath, perché è una redirezione e spegnerebbe questo comando.
righe_log="$(compose logs --tail 20 mongo-rs-1 2>/dev/null | grep -c 'msg')"
if (( righe_log > 0 )); then
  ok "docker compose logs restituisce righe (${righe_log} nelle ultime 20)"
else
  errore "docker compose logs è muto: qualcuno ha aggiunto --logpath?"
fi

# Senza questi due limiti il file di log cresce finché c'è disco, e qui i file sono tre:
# la scena di failover produce log di elezione a raffica proprio quando servono
# leggibili (V-011).
for membro in mongo-rs-1 mongo-rs-2 mongo-rs-3; do
  rotazione="$(docker inspect "${membro}" --format '{{index .HostConfig.LogConfig.Config "max-size"}} {{index .HostConfig.LogConfig.Config "max-file"}}' 2>/dev/null)"
  confronta "rotazione dei log di ${membro}" "10m 3" "${rotazione}"
done

# --- Esito ---------------------------------------------------------------------------
printf '\nSuperati: %d · Errori: %d\n' "${SUPERATI}" "${ERRORI}"
if (( ERRORI > 0 )); then
  printf 'Lo stack 02 non si comporta come promesso.\n'
  exit 1
fi
printf 'Lo stack 02 fa quello che il file Compose promette.\n'
