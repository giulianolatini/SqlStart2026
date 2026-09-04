#!/usr/bin/env bash
# Controlli della mattina del talk. Errori bloccanti -> uscita 1. Avvisi -> uscita 0.
#
# Niente `set -e`: un preflight che si ferma al primo problema costringe a tre giri.
# Deve dire tutto quello che non va, subito, mentre c'è ancora tempo per rimediare.
set -uo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CARTELLA_FILMATI="${DEMO_VIDEOS_DIR:-${HOME}/SqlStart2026-registrazioni}"
# Sovrascrivibile solo per collaudare il comportamento del giorno del talk senza
# aspettare il 18 settembre.
GIORNO_DEL_TALK="${GIORNO_DEL_TALK:-2026-09-18}"

# Porte del lab, da §5.2 della specifica: standalone, membri del replica set, mongos,
# config server, shard1, shard2.
PORTE=(27017 27021 27022 27023 27117 27118 27131 27132 27133 27141 27142 27143 27151 27152 27153)

if [[ -t 1 ]]; then
  VERDE=$'\033[32m'; GIALLO=$'\033[33m'; ROSSO=$'\033[31m'; GRIGIO=$'\033[90m'; NEUTRO=$'\033[0m'
else
  VERDE=''; GIALLO=''; ROSSO=''; GRIGIO=''; NEUTRO=''
fi

SUPERATI=0
AVVISI=0
ERRORI=0

ok()      { printf '  %s✓%s %s\n' "${VERDE}"  "${NEUTRO}" "$1"; SUPERATI=$((SUPERATI + 1)); }
avviso()  { printf '  %s!%s %s\n' "${GIALLO}" "${NEUTRO}" "$1"; AVVISI=$((AVVISI + 1)); }
errore()  { printf '  %s✗%s %s\n' "${ROSSO}"  "${NEUTRO}" "$1"; ERRORI=$((ERRORI + 1)); }
nota()    { printf '    %s%s%s\n' "${GRIGIO}" "$1" "${NEUTRO}"; }
titolo()  { printf '\n%s\n' "$1"; }

printf 'Preflight del lab MongoDB — %s\n' "$(date '+%F %H:%M')"

# --- Docker -----------------------------------------------------------------------
titolo "Docker"

demone_vivo=0
if docker info >/dev/null 2>&1; then
  demone_vivo=1
  ok "il demone risponde"
  ok "contesto attivo: $(docker context show 2>/dev/null || echo sconosciuto)"
else
  errore "il demone Docker non risponde — avvia Docker Desktop e riesegui"
fi

# Il 2026-08-24 `docker` risolveva al binario di Rancher Desktop mentre il contesto
# puntava al socket di Docker Desktop. Si manifestava come un errore di socket
# incomprensibile: da allora il PATH si controlla prima di ogni altra cosa.
percorso_docker="$(command -v docker || true)"
case "${percorso_docker}" in
  *"/.rd/"*) errore "docker risolve a Rancher Desktop: ${percorso_docker}" ;;
  "")        errore "docker non è nel PATH" ;;
  *)         ok "docker: ${percorso_docker}" ;;
esac
if [[ -d "${HOME}/.rd" ]]; then
  avviso "residui di Rancher Desktop in ~/.rd: valuta la rimozione"
  nota "rm -rf ~/.rd, e togli la riga ~/.rd/bin da .zshrc o .zprofile"
fi

# --- Memoria della VM -------------------------------------------------------------
titolo "Risorse della VM Docker"

if (( demone_vivo )); then
  memoria_byte="$(docker info --format '{{.MemTotal}}' 2>/dev/null || true)"
  if [[ ! "${memoria_byte}" =~ ^[0-9]+$ ]]; then
    errore "non riesco a leggere la memoria della VM"
  else
    gib="$(awk -v b="${memoria_byte}" 'BEGIN { printf "%.2f", b / 1073741824 }')"
    soglia() { awk -v b="${memoria_byte}" -v g="$1" 'BEGIN { exit !(b < g * 1073741824) }'; }
    if soglia 6; then
      errore "VM Docker: ${gib} GiB — sotto i 6 GiB gli stack del lab non stanno in piedi"
    elif soglia 10; then
      avviso "VM Docker: ${gib} GiB — bastano per standalone, replica set e il profilo palco"
      nota "il profilo completo dello sharded ne vuole circa 12 (ADR-0025)"
    else
      ok "VM Docker: ${gib} GiB"
    fi
  fi
  ok "CPU assegnate: $(docker info --format '{{.NCPU}}' 2>/dev/null || echo '?')"
else
  errore "risorse non verificabili: il demone non risponde"
fi

# --- Porte ------------------------------------------------------------------------
titolo "Porte del lab"

if ! command -v lsof >/dev/null 2>&1; then
  avviso "lsof non disponibile: le porte non sono state controllate"
else
  porte_dei_container="$(docker ps --format '{{.Ports}}' 2>/dev/null || true)"
  estranee=()
  del_lab=0
  for porta in "${PORTE[@]}"; do
    lsof -nP -iTCP:"${porta}" -sTCP:LISTEN >/dev/null 2>&1 || continue
    # Una porta tenuta da un container già in piedi non è un problema: è il lab stesso.
    if [[ "${porte_dei_container}" == *":${porta}->"* ]]; then
      del_lab=$((del_lab + 1))
    else
      estranee+=("${porta}")
    fi
  done

  if (( ${#estranee[@]} > 0 )); then
    errore "porte occupate da processi estranei: ${estranee[*]}"
    nota "chi le tiene: lsof -nP -iTCP:${estranee[0]} -sTCP:LISTEN"
  else
    ok "tutte le ${#PORTE[@]} porte del lab sono libere o tenute dal lab stesso"
  fi
  (( del_lab > 0 )) && nota "${del_lab} già in uso da container del lab in esecuzione"
fi

# --- Immagini -------------------------------------------------------------------
titolo "Immagini"

# Bloccante: senza immagini non c'è demo, e in sala non si scarica.
if esito_immagini="$("${RADICE}/tools/pull-images.sh" --verify 2>&1)"; then
  ok "tutte le immagini pinnate sono nella cache locale"
else
  errore "immagini mancanti — il lab non parte senza rete"
  while IFS= read -r riga; do nota "${riga}"; done <<< "${esito_immagini}"
fi

# «Presente» e «funzionante» sono due proprietà diverse, e fino al 2026-08-25 il preflight
# misurava solo la prima: le immagini erano tutte in cache e nessuna si avviava, perché
# MongoDB 8 rifiuta i kernel dal 6.19 in su. Da allora l'immagine si esegue (ADR-0027).
immagine_mongo="$(sed -n 's/^MONGO_IMAGE=//p' "${RADICE}/tools/images.env" 2>/dev/null | head -1)"
if ! (( demone_vivo )); then
  errore "avvio dell'immagine non verificabile: il demone non risponde"
elif [[ -z "${immagine_mongo}" ]]; then
  errore "MONGO_IMAGE non è definita in tools/images.env"
elif esito_avvio="$(docker run --rm --entrypoint mongod "${immagine_mongo}" --version 2>&1)"; then
  ok "l'immagine pinnata si avvia — $(printf '%s\n' "${esito_avvio}" | head -1)"
else
  errore "l'immagine pinnata non si avvia su questo kernel"
  nota "kernel della VM: $(docker info --format '{{.KernelVersion}}' 2>/dev/null || echo '?')"
  while IFS= read -r riga; do nota "${riga}"; done < <(printf '%s\n' "${esito_avvio}" | head -2)
fi

# L'immagine dell'applicazione è l'unica del lab che **non** si scarica: la costruisce
# `make app-image` a partire da questo repository. Un digest ce l'ha — misurato, M-037,
# perché l'archivio immagini di containerd ne calcola uno anche per ciò che nessuno ha
# pubblicato — ma è un digest che nessun registro ha mai servito e che cambia a ogni
# ricostruzione: in images.env sarebbe una cosa da verificare in rete che in rete non
# c'è (ADR-0093). Resta però una cosa che deve essere in cache prima del talk esattamente
# come le altre, e l'unico controllo possibile è il più semplice: c'è o non c'è.
#
# Il tag si legge dal file Compose e non si riscrive qui, perché il numero che conta è
# quello che `docker compose run` andrà a cercare. Che i tre stack lo scrivano uguale, e
# uguale alla versione in app/pyproject.toml, lo prova tools/tests/test_coerenza_repo.py.
immagine_app="$(sed -n 's|^ *image: *\(mongolab:[^ ]*\).*|\1|p' \
  "${RADICE}/docker/01-standalone/compose.yaml" 2>/dev/null | head -1)"
if ! (( demone_vivo )); then
  errore "presenza dell'immagine dell'applicazione non verificabile: il demone non risponde"
elif [[ -z "${immagine_app}" ]]; then
  errore "nessun servizio con immagine mongolab: in docker/01-standalone/compose.yaml"
elif docker image inspect "${immagine_app}" >/dev/null 2>&1; then
  ok "l'immagine dell'applicazione è in cache — ${immagine_app}"
else
  errore "l'immagine dell'applicazione manca: ${immagine_app}"
  nota "costruirla ora, finché c'è rete: make app-image"
fi

# --- Filmati di riserva (ADR-0016) --------------------------------------------------
titolo "Filmati di riserva"

# Oggi è un avviso; dal giorno del talk diventa bloccante, perché il piano B senza
# filmati non è un piano B.
if [[ "$(date +%F)" < "${GIORNO_DEL_TALK}" ]]; then
  manca_filmati=avviso
else
  manca_filmati=errore
fi

if [[ ! -d "${CARTELLA_FILMATI}" ]]; then
  "${manca_filmati}" "cartella dei filmati assente: ${CARTELLA_FILMATI}"
  nota "impostabile con DEMO_VIDEOS_DIR"
else
  quanti="$(find "${CARTELLA_FILMATI}" -maxdepth 1 -type f -name '*.mp4' | wc -l | tr -d ' ')"
  if (( quanti == 0 )); then
    "${manca_filmati}" "nessun .mp4 in ${CARTELLA_FILMATI}"
  else
    ok "filmati locali disponibili: ${quanti}"
  fi
fi
if [[ "${manca_filmati}" == "avviso" ]]; then
  nota "dal ${GIORNO_DEL_TALK} l'assenza dei filmati diventa un errore bloccante"
fi

# --- Esito --------------------------------------------------------------------------
printf '\nSuperati: %d · Avvisi: %d · Errori: %d\n' "${SUPERATI}" "${AVVISI}" "${ERRORI}"

if (( ERRORI > 0 )); then
  printf '%sNon sei pronto.%s Risolvi gli errori qui sopra e riesegui.\n' "${ROSSO}" "${NEUTRO}"
  exit 1
fi
printf '%sPronto.%s\n' "${VERDE}" "${NEUTRO}"
exit 0
