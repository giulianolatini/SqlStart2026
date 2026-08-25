#!/usr/bin/env bash
# Scarica le immagini del lab e le pinna per digest, oppure verifica che siano
# già presenti in locale. Il talk gira senza rete: il digest è ciò che lo garantisce.
#
# Un tag come `mongo:7.0` è un puntatore mobile. Se l'immagine locale manca, o se il
# tag si è spostato, `docker compose up` va in rete — e la mattina del talk la rete
# non è un'ipotesi su cui costruire. Un digest no: identifica un contenuto preciso, e
# se quel contenuto è già nella cache locale Compose non ha motivo di uscire.
set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FILE_IMMAGINI="${RADICE}/tools/images.env"

# NOME_VARIABILE=riferimento:tag — gli stack Compose si agganciano con ${NOME_VARIABILE}.
# `mongo:7.0` porta con sé mongosh e i Database Tools: una sola immagine copre mongod,
# la shell e mongodump. Se una feature successiva ne richiederà un'altra, si aggiunge qui.
# La versione è 7.0 e non 8.0 per il motivo scritto in ADR-0028: sul kernel della VM di
# Docker Desktop nessuna MongoDB 8 pubblicata si avvia. Il traguardo resta la 8.0.30.
declare -a IMMAGINI=(
  "MONGO_IMAGE=mongo:7.0"
)

# Impostare PIATTAFORMA (per esempio a linux/arm64) solo per forzare un'architettura
# diversa da quella dell'host. Lasciata vuota, docker sceglie da sé.
PIATTAFORMA="${PIATTAFORMA:-}"

uso() {
  cat <<'FINE'
Uso: tools/pull-images.sh --pull | --verify

  --pull     Scarica ogni immagine e ne scrive il digest in tools/images.env.
             Richiede rete. Da eseguire quando si aggiorna una versione.
  --verify   Controlla che ogni digest di tools/images.env sia già presente in
             locale. Non tocca la rete: è il controllo da fare prima del talk.

Variabili d'ambiente:
  PIATTAFORMA   passata a `docker pull --platform` quando valorizzata.
FINE
}

richiede_docker() {
  if ! docker version >/dev/null 2>&1; then
    echo "✗ Il demone Docker non risponde. Avvia Docker Desktop e riprova." >&2
    exit 2
  fi
}

scarica() {
  richiede_docker
  local righe=()
  local voce nome riferimento digest
  for voce in "${IMMAGINI[@]}"; do
    nome="${voce%%=*}"
    riferimento="${voce#*=}"
    echo "→ ${riferimento}"
    if [[ -n "${PIATTAFORMA}" ]]; then
      docker pull --platform "${PIATTAFORMA}" "${riferimento}"
    else
      docker pull "${riferimento}"
    fi
    digest="$(docker image inspect --format '{{index .RepoDigests 0}}' "${riferimento}")"
    if [[ -z "${digest}" || "${digest}" != *"@sha256:"* ]]; then
      echo "✗ ${riferimento} non espone un digest utilizzabile: «${digest}»." >&2
      echo "  Succede alle immagini costruite in locale e mai spinte in un registro." >&2
      exit 1
    fi
    echo "  ${nome}=${digest}"
    righe+=("${nome}=${digest}")
  done

  # L'apostrofo va tenuto fuori da ${...:-...}: dentro l'espansione bash lo legge
  # come apertura di quote e lo script non compila più.
  local descrizione_piattaforma="quella dell'host"
  [[ -n "${PIATTAFORMA}" ]] && descrizione_piattaforma="${PIATTAFORMA}"

  {
    echo "# Immagini del lab, pinnate per digest. Generato da tools/pull-images.sh --pull."
    echo "# Data: $(date +%F) · Piattaforma: ${descrizione_piattaforma}"
    echo "#"
    echo "# Non modificare a mano: rigenerare con \`make images-pull\` quando si cambia"
    echo "# versione. Questo file è versionato perché è il lasciapassare offline del talk."
    printf '%s\n' "${righe[@]}"
  } > "${FILE_IMMAGINI}"

  echo "✓ Scritto tools/images.env — immagini pinnate: ${#righe[@]}."
}

verifica() {
  richiede_docker
  if [[ ! -r "${FILE_IMMAGINI}" ]]; then
    echo "✗ Manca tools/images.env. Eseguilo una volta con rete:" >&2
    echo "    make images-pull" >&2
    exit 1
  fi

  local mancanti=() presenti=0 riga nome riferimento
  while IFS= read -r riga; do
    [[ -z "${riga}" || "${riga}" == \#* ]] && continue
    nome="${riga%%=*}"
    riferimento="${riga#*=}"
    if docker image inspect "${riferimento}" >/dev/null 2>&1; then
      presenti=$((presenti + 1))
      echo "✓ ${nome}"
    else
      mancanti+=("${riferimento}")
      echo "✗ ${nome} — ${riferimento}"
    fi
  done < "${FILE_IMMAGINI}"

  if (( ${#mancanti[@]} > 0 )); then
    echo >&2
    echo "Immagini assenti dalla cache locale: ${#mancanti[@]}. Con rete disponibile:" >&2
    printf '    docker pull %s\n' "${mancanti[@]}" >&2
    exit 1
  fi

  echo "✓ Immagini presenti in locale: ${presenti}. Il lab parte senza rete."
}

case "${1:-}" in
  --pull)   scarica ;;
  --verify) verifica ;;
  -h|--help) uso ;;
  *)        uso >&2; exit 2 ;;
esac
