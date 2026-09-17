#!/usr/bin/env bash
# Scarica le immagini del lab e le pinna per digest, oppure verifica che siano
# già presenti in locale.
#
# Un tag come `mongo:7.0` è un puntatore mobile: domani può indicare un altro
# contenuto. Un digest no, identifica un contenuto preciso — ed è tutto ciò che il
# digest fa. Stabilisce **quale** immagine si usa, non **se** si va in rete: sono due
# proprietà distinte, e la seconda il pinning non la dà. Lo dice la nota di revisione
# di ADR-0009, che ritira la motivazione contraria, e il punto 2 di
# docs/00-progetto/limiti-noti.md: nessuna pagina Docker afferma che un'immagine
# pinnata e già in cache eviti il registry.
#
# Il talk gira senza rete grazie a due cose che stanno altrove: questo script,
# eseguito prima quando la rete c'è, e `pull_policy: never` scritto fisso in ogni
# servizio di ogni file Compose (ADR-0027, ADR-0039) — l'unico meccanismo con una
# frase documentale esplicita sul non contattare il registry. Qui si prepara la cache e si verifica che sia piena;
# a non uscire ci pensa Compose.
set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FILE_IMMAGINI="${RADICE}/tools/images.env"

# NOME_VARIABILE=riferimento:tag — gli stack Compose si agganciano con ${NOME_VARIABILE}.
# `mongo:7.0` porta con sé mongosh e i Database Tools: una sola immagine copre mongod,
# la shell e mongodump. Se una feature successiva ne richiederà un'altra, si aggiunge qui.
# La versione è 7.0 e non 8.0 per il motivo scritto in ADR-0028: sul kernel della VM di
# Docker Desktop nessuna MongoDB 8 pubblicata si avvia. Il traguardo resta la 8.0.30.
#
# Le due immagini di base dell'applicazione (Task 12, ADR-0012) servono a **costruire**,
# non ad avviare: l'immagine `mongolab` è costruita in locale e non si scarica da nessun
# registro. Stanno qui lo stesso perché sono l'unica parte della costruzione che venga
# dalla rete, e il digest è ciò che rende quella parte ripetibile.
declare -a IMMAGINI=(
  "MONGO_IMAGE=mongo:7.0"
  "PYTHON_IMAGE=python:3.13-slim"
  "UV_IMAGE=ghcr.io/astral-sh/uv:0.12.9"
)

# Impostare PIATTAFORMA (per esempio a linux/arm64) solo per forzare un'architettura
# diversa da quella dell'host. Lasciata vuota, docker sceglie da sé.
PIATTAFORMA="${PIATTAFORMA:-}"

uso() {
  cat <<'FINE'
Uso: tools/pull-images.sh --pull [NOME...] | --verify

  --pull     Scarica ogni immagine e ne scrive il digest in tools/images.env.
             Richiede rete. Da eseguire quando si aggiorna una versione.
             Con uno o piu` NOME scarica soltanto quelli e conserva i digest
             degli altri: aggiungere un'immagine non deve aggiornarne un'altra.
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

# Il digest gia` scritto in tools/images.env per quel nome, vuoto se non c'e`.
# Niente array associativi: su macOS `/bin/bash` e` ancora la 3.2, dove `declare -A`
# non esiste e lo script morirebbe alla prima riga invece che al primo uso.
digest_esistente() {
  [[ -r "${FILE_IMMAGINI}" ]] || return 0
  sed -n "s/^$1=//p" "${FILE_IMMAGINI}" | head -1
}

nominata() {
  local cercato="$1"; shift
  local voce
  for voce in "$@"; do
    [[ "${voce}" == "${cercato}" ]] && return 0
  done
  return 1
}

# `scarica` accetta i nomi da aggiornare. Senza nomi li aggiorna tutti, che e` il
# comportamento di sempre; con dei nomi tocca solo quelli e **conserva** gli altri
# digest cosi` come sono.
#
# La distinzione non e` un vezzo: `mongo:7.0` e` un tag mobile, e riscaricarlo per
# aggiungere `python:3.13-slim` sposterebbe il lab su una patch di MongoDB che nessuno
# ha deciso di adottare — mentre ADR-0080 dice che il lab resta sulla 7.0.40 finche` la
# 8.0.30 non esce. Un effetto collaterale del genere non ha nessun sintomo: il file
# cambia di due righe, gli stack ripartono, e la versione sotto la demo e` un'altra.
scarica() {
  richiede_docker
  local scelte=("$@")
  local righe=()
  local voce nome riferimento digest aggiornate=()

  # I nomi si validano prima di scaricare qualunque cosa: un refuso deve fermare il
  # comando, non lasciare il file a meta` con un'immagine aggiornata e una no.
  for nome in "${scelte[@]}"; do
    local conosciuto=0
    for voce in "${IMMAGINI[@]}"; do
      [[ "${voce%%=*}" == "${nome}" ]] && conosciuto=1
    done
    if (( ! conosciuto )); then
      echo "✗ «${nome}» non è un'immagine di questo lab." >&2
      printf '  I nomi sono: %s\n' "$(printf '%s ' "${IMMAGINI[@]%%=*}")" >&2
      exit 2
    fi
  done

  for voce in "${IMMAGINI[@]}"; do
    nome="${voce%%=*}"
    riferimento="${voce#*=}"

    if (( ${#scelte[@]} > 0 )) && ! nominata "${nome}" "${scelte[@]}"; then
      digest="$(digest_esistente "${nome}")"
      if [[ -z "${digest}" ]]; then
        echo "✗ ${nome} non è mai stata scaricata e non è fra quelle richieste." >&2
        echo "  Con rete: tools/pull-images.sh --pull ${nome}" >&2
        exit 1
      fi
      echo "· ${nome} conservata — ${digest}"
      righe+=("${nome}=${digest}")
      continue
    fi

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
    aggiornate+=("${nome}")
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
    # Quali righe sono nuove di questa corsa e quali arrivano dalla precedente. Senza
    # questa riga la data in cima varrebbe per tutte, e sarebbe falsa per quelle
    # conservate: il file direbbe di aver verificato oggi un digest di tre settimane fa.
    if (( ${#aggiornate[@]} < ${#righe[@]} )); then
      echo "# Rigenerate in questa corsa: ${aggiornate[*]} — le altre sono state conservate."
    fi
    printf '%s\n' "${righe[@]}"
  } > "${FILE_IMMAGINI}"

  echo "✓ Scritto tools/images.env — immagini pinnate: ${#righe[@]}, scaricate: ${#aggiornate[@]}."
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

  # Ciò che è stato misurato è la cache, non il comportamento di Compose: a non
  # uscire in rete ci pensa `pull_policy: never`. Il messaggio dice l'una cosa.
  echo "✓ Immagini presenti nella cache locale: ${presenti}. Niente da scaricare."
}

case "${1:-}" in
  --pull)   shift; scarica "$@" ;;
  --verify) verifica ;;
  -h|--help) uso ;;
  *)        uso >&2; exit 2 ;;
esac
