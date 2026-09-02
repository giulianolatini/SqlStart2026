#!/usr/bin/env bash
# Riporta uno stack allo stato da cui una demo comincia, SENZA ricostruirlo da zero.
#
#   ./tools/reset-demo.sh 01
#   ./tools/reset-demo.sh 02
#   ./tools/reset-demo.sh 03          # profilo palco
#   PROFILO=completo ./tools/reset-demo.sh 03
#
# Non è `reset-01` / `reset-02`: quelli fermano lo stack e cancellano i volumi, e
# ricostruire da zero costa mezzo minuto. Questo serve al caso opposto — la prova
# generale in cui la stessa scena si ripete tre volte di fila — e lavora sui container
# in piedi. Il debito viene da feature/01, dove ci si era accorti che fra una prova e
# l'altra si finiva a rifare l'intero stack per rimettere a posto due collezioni.
#
# Lo stack è un ARGOMENTO e non un ramo dentro il codice: feature/03 ha aggiunto il suo
# caso qui sotto invece di scriversi il proprio script, e il diff di quel commit è un
# ramo in più — le funzioni condivise, i tempi di attesa e il verdetto finale sono gli
# stessi per tutti e tre.
#
# Che cosa rimette a posto, in ordine:
#   1. i container fermati a mano durante una demo di failover — li riavvia;
#   2. la topologia — aspetta che i tre membri siano sani e che ci sia un primario, e
#      che sia tornato quello con priorità 2, perché la scena successiva comincia da lì;
#   3. le collezioni che la demo ha lasciato in giro — in `lab` sopravvive solo `ordini`;
#   4. il dataset — ricaricato, così l'impronta torna quella di V-013.
#
# Niente `set -e`: come per gli smoke, deve dire tutto quello che non va in una volta
# sola invece di costringere a tre giri.
set -uo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AMBIENTE="${RADICE}/tools/images.env"

# Quanto si aspetta prima di dichiarare che qualcosa non torna. Generosi: su una
# macchina carica un membro può metterci parecchio a diventare sano, e uno script che
# si arrende troppo presto durante una prova generale è peggio di uno lento.
ATTESA_SALUTE=90     # secondi, per container
ATTESA_PRIMARIO=60   # secondi, perché l'elezione dopo un `docker kill` costa ~10 s (V-029)
ATTESA_PRIORITA=45   # secondi, per il rientro del membro a priorità 2

if [[ -t 1 ]]; then
  VERDE=$'\033[32m'; ROSSO=$'\033[31m'; GRIGIO=$'\033[90m'; NEUTRO=$'\033[0m'
else
  VERDE=''; ROSSO=''; GRIGIO=''; NEUTRO=''
fi

ERRORI=0
ok()     { printf '  %s✓%s %s\n' "${VERDE}" "${NEUTRO}" "$1"; }
errore() { printf '  %s✗%s %s\n' "${ROSSO}" "${NEUTRO}" "$1"; ERRORI=$((ERRORI + 1)); }
nota()   { printf '    %s%s%s\n' "${GRIGIO}" "$1" "${NEUTRO}"; }
titolo() { printf '\n%s\n' "$1"; }

uso() {
  printf 'Uso: %s <stack>\n' "$(basename "$0")" >&2
  printf '  01  istanza singola\n' >&2
  printf '  02  replica set a tre membri\n' >&2
  printf '  03  sharded cluster (PROFILO=palco predefinito, oppure completo)\n' >&2
  exit 2
}

[[ $# -eq 1 ]] || uso
STACK="$1"

# --- Riavvia i container fermati a mano ----------------------------------------------
#
# `docker start` su un container già in piedi non è un errore e non fa niente, quindi
# non serve chiedere prima com'è messo. Su uno che non esiste, invece, sì: e in quel
# caso il rimedio non è questo script, è `make up-0N`.
rialza() {
  local nome="$1"
  local stato
  stato="$(docker inspect "${nome}" --format '{{.State.Status}}' 2>/dev/null)"
  if [[ -z "${stato}" ]]; then
    errore "il container ${nome} non esiste — questo script non ricostruisce lo stack, usa «make up-${STACK}»"
    return 1
  fi
  if [[ "${stato}" == "running" ]]; then
    ok "${nome} era già in piedi"
    return 0
  fi
  nota "${nome} era ${stato}, lo riavvio"
  if docker start "${nome}" > /dev/null 2>&1; then
    ok "${nome} riavviato"
  else
    errore "${nome} non è ripartito"
    return 1
  fi
}

attendi_salute() {
  local nome="$1" i salute
  for ((i = 0; i < ATTESA_SALUTE; i++)); do
    salute="$(docker inspect "${nome}" --format '{{.State.Health.Status}}' 2>/dev/null)"
    [[ "${salute}" == "healthy" ]] && { ok "${nome} è sano"; return 0; }
    sleep 1
  done
  errore "${nome} non è diventato sano in ${ATTESA_SALUTE} s (ultimo stato: «${salute:-nessuno}»)"
  return 1
}

# --- Stack 01 — istanza singola -------------------------------------------------------
if [[ "${STACK}" == "01" ]]; then
  COMPOSE="${RADICE}/docker/01-standalone/compose.yaml"
  compose() { docker compose --env-file "${AMBIENTE}" -f "${COMPOSE}" "$@"; }

  titolo "Container"
  rialza mongo-standalone && attendi_salute mongo-standalone

  titolo "Collezioni lasciate in giro dalla demo"
  # `ordini` è il dataset; tutto il resto è residuo. Il conto delle collezioni tolte
  # si stampa perché una demo che non lascia niente e una che lascia sei collezioni
  # sono due situazioni diverse, e chi sta provando vuole saperlo.
  tolte="$(compose exec -T mongo-standalone mongosh --quiet lab --eval '
    const superstiti = ["ordini"];
    const via = db.getCollectionNames().filter(n => !superstiti.includes(n));
    via.forEach(n => db.getCollection(n).drop());
    print(via.length === 0 ? "nessuna" : via.join(", "));
  ' 2>/dev/null | tail -1 | tr -d '\r')"
  ok "collezioni rimosse: ${tolte:-nessuna}"

  titolo "Dataset"
  compose exec -T mongo-standalone \
    mongosh --quiet --file /docker-entrypoint-initdb.d/10-dati-demo.js > /dev/null 2>&1 \
    || errore "il seed non è andato a buon fine"
  # La stessa terna che sorvegliano i due smoke: 50000 124861860.70 150281 (V-013).
  impronta="$(compose exec -T mongo-standalone mongosh --quiet lab --eval \
    'const a = db.ordini.aggregate([{$group:{_id:null, n:{$sum:1}, tot:{$sum:"$importo"}, righe:{$sum:"$righe"}}}]).toArray()[0]; print(a ? a.n + " " + a.tot.toFixed(2) + " " + a.righe : "collezione vuota")' \
    2>/dev/null | tail -1 | tr -d '\r')"
  ok "impronta di lab.ordini: ${impronta}"

# --- Stack 02 — replica set -----------------------------------------------------------
elif [[ "${STACK}" == "02" ]]; then
  COMPOSE="${RADICE}/docker/02-replicaset/compose.yaml"
  SEGRETI="${RADICE}/docker/02-replicaset/.env"

  if [[ ! -f "${SEGRETI}" ]]; then
    printf 'Manca %s.\n' "${SEGRETI}" >&2
    printf 'Contiene la password dell'\''amministratore e sta fuori dal repository (ADR-0014).\n' >&2
    exit 1
  fi
  set -a; . "${SEGRETI}"; set +a
  UTENTE="${UTENTE_AMMINISTRATORE:-admin}"
  PASSWORD="${PASSWORD_AMMINISTRATORE:-}"
  REPLICA="${NOME_REPLICA:-rs0}"
  PREFERITO="mongo-rs-1"   # il membro a priorità 2: la scena comincia con lui primario

  compose() { docker compose --env-file "${AMBIENTE}" --env-file "${SEGRETI}" -f "${COMPOSE}" "$@"; }

  # Sul PRIMARIO, chiunque sia. Dopo un failover non è più `mongo-rs-1`, e uno script
  # che lo desse per scontato fallirebbe raccontando la cosa sbagliata.
  sul_primario() {
    compose exec -T mongo-rs-1 mongosh --quiet --host "${REPLICA}/localhost:27017" \
      --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
      lab --eval "$1" 2>/dev/null | tail -1 | tr -d '\r'
  }

  # Chiede a un membro preciso chi è il primario secondo lui. Il membro deve essere
  # vivo: se è quello appena riavviato, la risposta arriva quando è pronto.
  chi_primario() {
    local membro="$1"
    docker exec "${membro}" mongosh --quiet --host localhost \
      --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
      --eval 'const h = db.getSiblingDB("admin").hello(); print(h.primary || "nessuno")' \
      2>/dev/null | tail -1 | tr -d '\r'
  }

  titolo "Container"
  for membro in mongo-rs-1 mongo-rs-2 mongo-rs-3; do
    rialza "${membro}"
  done
  for membro in mongo-rs-1 mongo-rs-2 mongo-rs-3; do
    attendi_salute "${membro}"
  done

  titolo "Topologia"
  primario=""
  for ((i = 0; i < ATTESA_PRIMARIO; i++)); do
    primario="$(chi_primario mongo-rs-2)"
    [[ -n "${primario}" && "${primario}" != "nessuno" ]] && break
    sleep 1
  done
  if [[ -z "${primario}" || "${primario}" == "nessuno" ]]; then
    errore "nessun primario dopo ${ATTESA_PRIMARIO} s — la maggioranza non si è formata"
  else
    ok "primario: ${primario}"
    # Il rientro del membro a priorità 2 non è immediato: deve raggiungere gli altri
    # nell'oplog prima di poter vincere un'elezione. Se non torna, NON è un errore
    # dello stack — è un'informazione, e chi sta provando decide se aspettare ancora.
    if [[ "${primario}" != "${PREFERITO}:27017" ]]; then
      nota "aspetto che ${PREFERITO} (priorità 2) si riprenda il ruolo"
      for ((i = 0; i < ATTESA_PRIORITA; i++)); do
        primario="$(chi_primario mongo-rs-2)"
        [[ "${primario}" == "${PREFERITO}:27017" ]] && break
        sleep 1
      done
      if [[ "${primario}" == "${PREFERITO}:27017" ]]; then
        ok "${PREFERITO} è tornato primario"
      else
        errore "dopo ${ATTESA_PRIORITA} s il primario è ancora ${primario} invece di ${PREFERITO}:27017"
        nota "non è rotto: ${PREFERITO} sta probabilmente ancora recuperando l'oplog. Rilanciare fra poco."
      fi
    fi
  fi

  titolo "Collezioni lasciate in giro dalla demo"
  tolte="$(sul_primario '
    const superstiti = ["ordini"];
    const via = db.getCollectionNames().filter(n => !superstiti.includes(n));
    via.forEach(n => db.getCollection(n).drop({ writeConcern: { w: "majority", wtimeout: 10000 } }));
    print(via.length === 0 ? "nessuna" : via.join(", "));
  ')"
  ok "collezioni rimosse: ${tolte:-nessuna}"

  titolo "Dataset"
  # Lo STESSO servizio che semina all'avvio, con RICARICA=1. Una sorgente sola.
  if ! compose run --rm -e RICARICA=1 rs-init > /dev/null 2>&1; then
    errore "il seed non è andato a buon fine — «make logs-02» per il motivo"
  fi
  # La stessa terna che sorvegliano i due smoke: 50000 124861860.70 150281 (V-013).
  impronta="$(sul_primario 'const a = db.ordini.aggregate([{$group:{_id:null, n:{$sum:1}, tot:{$sum:"$importo"}, righe:{$sum:"$righe"}}}]).toArray()[0]; print(a ? a.n + " " + a.tot.toFixed(2) + " " + a.righe : "collezione vuota")')"
  ok "impronta di lab.ordini: ${impronta}"

# --- Stack 03 — sharded cluster -------------------------------------------------------
#
# Le differenze dal caso 02 sono tre, e nessuna cambia la forma. La prima: i container
# da rialzare dipendono dal PROFILO, perché in `palco` gli altri sei non esistono e
# chiederne lo stato darebbe sei errori veri su una situazione sana. La seconda: qui non
# si aspetta un primario preferito. La scena del guasto (`make guasto-03`) rimette in
# piedi da sé il nodo che ha fermato, e nel profilo del talk non c'è nessun ruolo da
# spostare perché ogni shard ha un membro solo: si aspetta che i due shard risultino
# registrati, che è la condizione da cui il Blocco 3 riparte. La terza: il verdetto
# sui dati non è solo l'impronta, è anche che i documenti stiano su ENTRAMBI gli shard,
# perché una demo che li lascia tutti su uno è esattamente il guasto che il Blocco 3
# vuole scongiurare.
elif [[ "${STACK}" == "03" ]]; then
  COMPOSE="${RADICE}/docker/03-sharded/compose.yaml"
  SEGRETI="${RADICE}/docker/03-sharded/.env"
  PROFILO="${PROFILO:-palco}"

  if [[ ! -f "${SEGRETI}" ]]; then
    printf 'Manca %s.\n' "${SEGRETI}" >&2
    printf 'Contiene la password dell'"'"'amministratore e sta fuori dal repository (ADR-0014).\n' >&2
    exit 1
  fi
  set -a; . "${SEGRETI}"; set +a
  UTENTE="${UTENTE_AMMINISTRATORE:-admin}"
  PASSWORD="${PASSWORD_AMMINISTRATORE:-}"

  case "${PROFILO}" in
    palco)    MONGOD=(sh-cfg1 sh-shard1a sh-shard2a); ROUTER=(sh-mongos) ;;
    completo) MONGOD=(sh-cfg1 sh-cfg2 sh-cfg3
                      sh-shard1a sh-shard1b sh-shard1c
                      sh-shard2a sh-shard2b sh-shard2c)
              ROUTER=(sh-mongos sh-mongos2) ;;
    *) printf 'Profilo sconosciuto: «%s». Sono «palco» e «completo».\n' "${PROFILO}" >&2; exit 2 ;;
  esac

  compose() {
    docker compose --env-file "${AMBIENTE}" --env-file "${SEGRETI}" \
      -f "${COMPOSE}" --profile "${PROFILO}" "$@"
  }

  # Tutto passa dal router, che è il punto in cui il client parla al cluster. Chiedere
  # a un mongod direttamente adesso funzionerebbe — da ADR-0071 ogni shard ha un
  # amministratore locale con le stesse credenziali — e risponderebbe male: uno shard
  # conosce solo la propria metà dei documenti e non ha l'anagrafe del cluster
  # (V-067). Fino a quel commit non entrava nemmeno, e l'errore faceva da chiavistello
  # (V-058); adesso il chiavistello non c'è e la regola resta.
  dal_router() {
    compose exec -T mongos \
      mongosh --quiet --host localhost \
        --username "${UTENTE}" --password "${PASSWORD}" --authenticationDatabase admin \
        lab --eval "$1" 2>/dev/null | tail -1 | tr -d '\r'
  }

  titolo "Container (profilo ${PROFILO})"
  for nodo in "${MONGOD[@]}" "${ROUTER[@]}"; do
    rialza "${nodo}"
  done
  for nodo in "${MONGOD[@]}" "${ROUTER[@]}"; do
    attendi_salute "${nodo}"
  done

  titolo "Topologia"
  registrati=""
  for ((i = 0; i < ATTESA_PRIMARIO; i++)); do
    registrati="$(dal_router 'print(db.getSiblingDB("config").shards.countDocuments({state: 1}))')"
    [[ "${registrati}" == "2" ]] && break
    sleep 1
  done
  if [[ "${registrati}" == "2" ]]; then
    ok "due shard registrati e attivi"
  else
    errore "shard attivi: «${registrati:-nessuna risposta}» invece di 2 dopo ${ATTESA_PRIMARIO} s"
  fi
  # Il balancer si può spegnere per sbaglio da mongosh durante una prova, e da spento
  # non dà nessun segnale finché non serve. Rimetterlo acceso fa parte del riportare
  # lo stack allo stato da cui la demo comincia.
  if [[ "$(dal_router 'print(sh.getBalancerState())')" == "true" ]]; then
    ok "balancer attivo"
  else
    nota "balancer spento, lo riaccendo"
    dal_router 'sh.startBalancer()' > /dev/null
    if [[ "$(dal_router 'print(sh.getBalancerState())')" == "true" ]]; then
      ok "balancer riacceso"
    else
      errore "il balancer non si è riacceso"
    fi
  fi

  titolo "Collezioni lasciate in giro dalla demo"
  tolte="$(dal_router '
    const superstiti = ["ordini"];
    const via = db.getCollectionNames().filter(n => !superstiti.includes(n));
    via.forEach(n => db.getCollection(n).drop({ writeConcern: { w: "majority", wtimeout: 10000 } }));
    print(via.length === 0 ? "nessuna" : via.join(", "));
  ')"
  ok "collezioni rimosse: ${tolte:-nessuna}"

  titolo "Dataset"
  # Lo STESSO servizio che semina all'avvio, con RICARICA=1: una sorgente sola, e
  # `sh.shardCollection()` dentro lo script è idempotente, quindi la collezione resta
  # distribuita anche se la demo l'aveva lasciata cadere.
  if ! compose run --rm -e RICARICA=1 seed > /dev/null 2>&1; then
    errore "il seed non è andato a buon fine — «make logs-03» per il motivo"
  fi
  # Ventimila, non cinquantamila: lo stack 03 usa i primi 20 000 del dataset (ADR-0064),
  # quindi l'impronta è diversa da quella di V-013 e deve esserlo.
  impronta="$(dal_router 'const a = db.ordini.aggregate([{$group:{_id:null, n:{$sum:1}, tot:{$sum:"$importo"}, righe:{$sum:"$righe"}}}]).toArray()[0]; print(a ? a.n + " " + a.tot.toFixed(2) + " " + a.righe : "collezione vuota")')"
  ok "impronta di lab.ordini: ${impronta}"

  # L'unico controllo che distingue uno sharded cluster da un replica set travestito.
  distribuzione="$(dal_router '
    const per = {};
    db.getSiblingDB("admin").aggregate([{$shardedDataDistribution: {}}])
      .toArray()
      .filter(d => d.ns === "lab.ordini")
      .forEach(d => d.shards.forEach(s => { per[s.shardName] = s.numOwnedDocuments; }));
    const nomi = Object.keys(per).sort();
    print(nomi.length === 0 ? "nessun dato" : nomi.map(n => n + "=" + per[n]).join(" "));
  ')"
  if [[ "${distribuzione}" == *" "* ]]; then
    ok "documenti su entrambi gli shard: ${distribuzione}"
  else
    errore "i documenti non risultano distribuiti: ${distribuzione:-nessuna risposta}"
  fi

else
  printf 'Stack sconosciuto: «%s».\n' "${STACK}" >&2
  uso
fi

printf '\n'
if (( ERRORI == 0 )); then
  printf 'Stack %s riportato allo stato di partenza.\n' "${STACK}"
  exit 0
fi
printf 'Stack %s: %d cose non tornano. Se insistono, «make reset-%s» ricostruisce da zero.\n' \
  "${STACK}" "${ERRORI}" "${STACK}"
exit 1
