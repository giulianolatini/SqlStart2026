#!/usr/bin/env bash
# revisione.sh — fa revisionare una PR da due modelli esterni e prepara il triage.
#
# Il giro completo:
#   dossier   <n>              raccoglie la PR in un unico file leggibile
#   interroga <n> [--invia]    la manda a Gemini Pro e a Codex — SENZA --invia non parte
#   rilievi   <n>              unisce le due risposte in un foglio di triage
#   archivia  <n> [--scrivi]   controlla che il triage sia completo e lo mette nel repo
#
# Piu' due di servizio:
#   segreti   <n>              scansione del dossier, da sola
#   stato     [<n>]            che cosa c'e' nella cartella di lavoro
#
# LA REGOLA CHE GOVERNA TUTTO IL FILE: `interroga` senza `--invia` non manda
# niente a nessuno. Mandare un diff a Google e a OpenAI e' una pubblicazione
# verso terzi, irreversibile: quello che esce non rientra. Il default e' quindi
# la prova a vuoto, che stampa a chi si manderebbe cosa e quanto grande e'.
# Prima di spedire, il dossier viene passato al setaccio dei segreti, e un
# segreto trovato ferma l'invio senza scorciatoie da riga di comando.

set -uo pipefail

errore () { printf 'revisione: %s\n' "$1" >&2; exit 1; }
avviso () { printf 'revisione: %s\n' "$1" >&2; }

# Gli eseguibili esterni si possono sostituire: e' cosi' che le prove girano
# senza rete e senza spendere token, mettendo al loro posto dei finti.
GH="${REVISIONE_GH:-gh}"
AGY="${REVISIONE_AGY:-agy}"
CODEX="${REVISIONE_CODEX:-codex}"
MODELLO_AGY="${REVISIONE_MODELLO_AGY:-gemini-3.1-pro-high}"
ATTESA="${REVISIONE_ATTESA:-15m}"

# Oltre questa soglia il prompt non entra piu' negli argomenti di un processo
# su macOS, e agy lo riceve troncato senza dirlo. Meglio fermarsi prima.
LIMITE_INVIO="${REVISIONE_LIMITE_INVIO:-700000}"
SOGLIA_AVVISO="${REVISIONE_SOGLIA_AVVISO:-200000}"

git rev-parse --git-dir >/dev/null 2>&1 || errore "non sei dentro un repository git."
radice="$(git rev-parse --show-toplevel)"
skill="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Una revisione ha un nome: il numero della PR, oppure - quando la PR non c'e'
# ancora - l'etichetta dell'area. I due non si confondono, perche' un numero
# non e' un'etichetta valida e un'etichetta non e' fatta di sole cifre.
cartella_di () {
  case "$1" in
    ''|*[!0-9]*) printf '%s/.revisioni/%s' "$radice" "$1" ;;
    *)           printf '%s/.revisioni/pr-%s' "$radice" "$1" ;;
  esac
}

numero_valido () {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
    *) return 0 ;;
  esac
}

# L'etichetta diventa un nome di cartella, quindi niente barre; minuscola e
# senza spazi perche' i percorsi di questo repository si scrivono cosi'; e non
# puo' cominciare per trattino, che a un comando sembra un'opzione.
etichetta_valida () {
  case "$1" in
    ''|-*) return 1 ;;
    *[!a-z0-9-]*) return 1 ;;
    *) return 0 ;;
  esac
}

# Chi viene dopo il dossier - setaccio, interrogatorio, triage, archivio - non
# ha motivo di sapere se sta lavorando su una PR o su un intervallo.
identificativo_valido () {
  numero_valido "$1" || etichetta_valida "$1"
}

# `Docs` con la maiuscola e' la convenzione del repository d'origine; qui la cartella e'
# `docs`. Su macOS le due si confondono, su Linux diventano due cartelle
# diverse, ed e' un guasto che si vede solo dopo il clone. Quindi non si
# presume: si guarda quale delle due il repository ha davvero.
nome_docs () {
  if [ -d "$radice/docs" ]; then printf 'docs'
  elif [ -d "$radice/Docs" ]; then printf 'Docs'
  else printf 'Docs'
  fi
}

# --------------------------------------------------------------- dossier -----

cmd_dossier () {
  local n="${1:-}"
  numero_valido "$n" || errore "uso: revisione.sh dossier <numero-pr>"
  command -v "$GH" >/dev/null 2>&1 || errore "manca gh. Vedi INSTALL-ENV.md."
  command -v jq   >/dev/null 2>&1 || errore "manca jq. Vedi INSTALL-ENV.md."

  local lav; lav="$(cartella_di "$n")"
  mkdir -p "$lav"

  local campi='number,title,author,baseRefName,headRefName,state,url,body,commits,files'
  "$GH" pr view "$n" --json "$campi" > "$lav/meta.json" 2>"$lav/gh.err" \
    || errore "gh non ha trovato la PR #$n. Dettagli in $lav/gh.err"

  "$GH" pr diff "$n" > "$lav/diff.patch" 2>>"$lav/gh.err" \
    || errore "gh non ha restituito il diff della PR #$n. Dettagli in $lav/gh.err"

  # Il dossier e' un file solo, e non e' un vezzo: e' l'unica cosa che esce dal
  # perimetro. Averlo in un file solo vuol dire poterlo leggere prima di
  # spedirlo, e poterlo passare a un setaccio solo.
  local d="$lav/dossier.md"
  {
    jq -r '
      "# Dossier della PR #\(.number) — \(.title)\n",
      "| Campo | Valore |",
      "|---|---|",
      "| Autore | \(.author.login) |",
      "| Da | `\(.headRefName)` |",
      "| Verso | `\(.baseRefName)` |",
      "| Stato | \(.state) |",
      "| File toccati | \(.files | length) |",
      "",
      "## Descrizione della PR\n",
      (.body // "_(nessuna descrizione)_"),
      "",
      "## Commit, in ordine cronologico\n",
      (.commits | to_entries[] |
        "### \(.key + 1). `\(.value.oid[0:8])` — \(.value.messageHeadline)\n" +
        (if (.value.messageBody // "") == "" then "_(nessun corpo)_\n"
         else "```\n" + .value.messageBody + "\n```\n" end)),
      "## File toccati\n",
      (.files[] | "- `\(.path)` (+\(.additions) −\(.deletions))"),
      ""
    ' "$lav/meta.json"
    printf '## Diff\n\n```diff\n'
    cat "$lav/diff.patch"
    printf '```\n'
  } > "$d" || errore "non sono riuscito a comporre il dossier."

  printf 'dossier: %s (%s byte)\n' "$d" "$(wc -c < "$d" | tr -d ' ')"
}

# --------------------------------------------------- dossier da rami --------

# Una release non ha una PR finche' non la apre chi la fonde, ma va revisionata
# prima - altrimenti la revisione arriva quando la decisione e' gia' presa. E
# non entra in un dossier solo: undici megabyte non sono una revisione, sono
# uno scorrimento. Per questo si prende un intervallo e, se serve, una fetta
# dell'albero.
cmd_dossier_rami () {
  local etichetta="${1:-}" intervallo="${2:-}"
  shift 2 2>/dev/null || true

  etichetta_valida "$etichetta" \
    || errore "uso: revisione.sh dossier-rami <etichetta> <base>..<head> [percorso...]
L'etichetta e' minuscola, senza spazi ne' barre: diventa un nome di cartella."
  case "$intervallo" in
    *..*) : ;;
    *) errore "uso: revisione.sh dossier-rami <etichetta> <base>..<head> [percorso...]
Serve un intervallo, non un ramo solo: e' il confronto che si revisiona." ;;
  esac

  local base="${intervallo%%..*}" head="${intervallo##*..}"
  git rev-parse --verify --quiet "$base^{commit}" >/dev/null \
    || errore "«$base» non è un commit di questo repository."
  git rev-parse --verify --quiet "$head^{commit}" >/dev/null \
    || errore "«$head» non è un commit di questo repository."

  local lav; lav="$(cartella_di "$etichetta")"
  mkdir -p "$lav"

  # Tre punti e non due: si revisiona quello che il ramo ha aggiunto dal punto
  # in cui si e' staccato, non anche quello che nel frattempo e' successo
  # altrove. Con due punti un merge nella base comparirebbe nel diff come una
  # rimozione, e il revisore inseguirebbe codice che nessuno ha tolto.
  local diff="$lav/diff.patch"
  git diff "$base...$head" -- "$@" > "$diff" \
    || errore "git diff ha rifiutato «$base...$head»."

  local commit; commit="$(git rev-list --reverse "$base..$head" -- "$@")"
  local quanti; quanti="$(printf '%s' "$commit" | grep -c . || true)"
  # L'apostrofo dentro un'espansione ${:-} apre una quota anche fra doppi
  # apici: il valore di riserva si mette fuori, e la riga resta leggibile.
  local percorsi="$*"
  [ -n "$percorsi" ] || percorsi="tutto l'albero"

  local d="$lav/dossier.md"
  {
    printf '# Dossier dell'\''intervallo `%s..%s` — %s\n\n' "$base" "$head" "$etichetta"
    printf '| Campo | Valore |\n|---|---|\n'
    printf '| Etichetta | `%s` |\n' "$etichetta"
    printf '| Da | `%s` |\n' "$base"
    printf '| A | `%s` |\n' "$head"
    printf '| Percorsi guardati | `%s` |\n' "$percorsi"
    printf '| Commit | %s |\n' "$quanti"
    printf '| Peso del diff | %s byte |\n' "$(wc -c < "$diff" | tr -d ' ')"
    printf '\n> Questa revisione non nasce da una pull request: il ramo e'\'' aperto e la PR\n'
    printf '> la apre chi la fonde. Quello che segue e'\'' l'\''intervallo cosi'\'' com'\''e'\'' oggi.\n\n'

    # La nota inquadra: senza, il revisore deve indovinare che cosa sta
    # guardando dal diff, e indovina male.
    printf '## Che cosa si sta revisionando\n\n'
    if [ -f "$lav/nota.md" ]; then
      cat "$lav/nota.md"
      printf '\n'
    else
      printf '_(nessuna nota: scrivila in `%s` e rilancia)_\n\n' "$lav/nota.md"
    fi

    printf '## Commit, in ordine cronologico\n\n'
    if [ -z "$commit" ]; then
      printf '_(nessun commit in questo intervallo per i percorsi indicati)_\n\n'
    else
      local i=0 sha
      while IFS= read -r sha; do
        [ -n "$sha" ] || continue
        i=$((i+1))
        printf '### %s. `%s` — %s\n\n' "$i" "${sha:0:8}" "$(git log -1 --format=%s "$sha")"
        local corpo; corpo="$(git log -1 --format=%b "$sha")"
        if [ -z "$corpo" ]; then
          printf '_(nessun corpo)_\n\n'
        else
          printf '```\n%s\n```\n\n' "$corpo"
        fi
      done <<< "$commit"
    fi

    printf '## File toccati\n\n'
    git diff --numstat "$base...$head" -- "$@" \
      | awk '{ printf "- `%s` (+%s −%s)\n", $3, $1, $2 }'
    printf '\n## Diff\n\n```diff\n'
    cat "$diff"
    printf '```\n'
  } > "$d" || errore "non sono riuscito a comporre il dossier."

  local peso; peso="$(wc -c < "$d" | tr -d ' ')"
  printf 'dossier: %s (%s byte, %s commit)\n' "$d" "$peso" "$quanti"
  if [ "$peso" -gt "$LIMITE_INVIO" ]; then
    avviso "oltre il limite d'invio di $LIMITE_INVIO byte: cosi' non parte. Restringi i percorsi."
  elif [ "$peso" -gt "$SOGLIA_AVVISO" ]; then
    avviso "sopra la soglia di attenzione ($SOGLIA_AVVISO byte): una revisione distratta e' quasi una revisione mancata."
  fi
  return 0
}

# --------------------------------------------------------------- segreti -----

# Esce 0 se il file e' pulito, 1 se qualcosa somiglia a una credenziale.
scansiona () {
  local file="$1"
  local pat esc trovati
  pat="$(mktemp)"; esc="$(mktemp)"; trovati="$(mktemp)"

  grep -vE '^[[:space:]]*(#|$)' "$skill/scripts/segreti.pattern" > "$pat"
  grep -vE '^[[:space:]]*(#|$)' "$skill/scripts/segreti.esclusioni" > "$esc"

  grep -nEf "$pat" "$file" 2>/dev/null | grep -vEf "$esc" > "$trovati"

  local esito=0
  if [ -s "$trovati" ]; then
    esito=1
    printf 'SEGRETI SOSPETTI nel dossier — l'\''invio si ferma qui:\n\n' >&2
    # Di ogni sequenza lunga restano sei caratteri, e il resto va via. Un
    # controllo che per avvisarti del segreto te lo ristampa nel terminale - e
    # quindi nel transcript della sessione, che e' un altro file su disco - ha
    # appena peggiorato le cose che doveva proteggere. Sei caratteri bastano a
    # riconoscere di quale credenziale si tratta (`pplx-4…`, `ghp_9f…`) e non
    # bastano a usarla.
    sed -E 's/([A-Za-z0-9_-]{6})[A-Za-z0-9/+_=.-]{6,}/\1…/g' "$trovati" \
      | cut -c1-100 | sed 's/^/  /' >&2
    printf '\nGuarda le righe indicate in %s.\n' "$file" >&2
    printf 'Se e'\'' un falso positivo, la riga giusta da aggiungere sta in\n' >&2
    printf '%s — con il commento che dice perche'\''.\n' "$skill/scripts/segreti.esclusioni" >&2
  fi

  rm -f "$pat" "$esc" "$trovati"
  return "$esito"
}

cmd_segreti () {
  local n="${1:-}"
  identificativo_valido "$n" || errore "uso: revisione.sh segreti <numero-pr|etichetta>"
  local d; d="$(cartella_di "$n")/dossier.md"
  [ -f "$d" ] || errore "manca $d. Lancia prima 'revisione.sh dossier $n'."
  if scansiona "$d"; then
    printf 'nessun segreto riconoscibile in %s.\n' "$d"
    return 0
  fi
  return 1
}

# ------------------------------------------------------------- interroga -----

cmd_interroga () {
  local n="${1:-}"; shift || true
  identificativo_valido "$n" || errore "uso: revisione.sh interroga <numero-pr|etichetta> [--invia]"
  local invia=0
  [ "${1:-}" = "--invia" ] && invia=1

  local lav; lav="$(cartella_di "$n")"
  local d="$lav/dossier.md"
  [ -f "$d" ] || errore "manca $d. Lancia prima 'revisione.sh dossier $n'."

  local istruzioni="$skill/prompt/revisione.md"
  local schema="$skill/prompt/rilievi.schema.json"
  local prompt="$lav/prompt.txt"
  cat "$istruzioni" > "$prompt"
  printf '\n\n---\n\n' >> "$prompt"
  cat "$d" >> "$prompt"

  local peso; peso="$(wc -c < "$prompt" | tr -d ' ')"

  if [ "$invia" -eq 0 ]; then
    printf 'PROVA A VUOTO — non e'\'' stato mandato niente a nessuno.\n\n'
    printf 'Manderei %s byte a due destinatari fuori da questa macchina:\n' "$peso"
    printf '  - Google (Gemini, via %s), modello %s\n' "$AGY" "$MODELLO_AGY"
    printf '  - OpenAI (Codex, via %s)\n\n' "$CODEX"
    printf 'Il testo esatto che uscirebbe e'\'' in %s.\n' "$prompt"
    printf 'Leggilo prima di autorizzare: quello che esce non rientra.\n\n'
    if scansiona "$d"; then
      printf 'Setaccio dei segreti: pulito.\n'
    else
      printf '\nCon --invia questo invio verrebbe RIFIUTATO.\n'
      return 1
    fi
    if [ "$peso" -gt "$SOGLIA_AVVISO" ]; then
      avviso "il dossier e' grosso ($peso byte). Una revisione su un diff enorme e' una revisione distratta: valuta di chiudere la PR in due."
    fi
    printf '\nPer procedere davvero:\n  revisione.sh interroga %s --invia\n' "$n"
    return 0
  fi

  scansiona "$d" || errore "invio rifiutato: prima si toglie il segreto dal ramo, poi si revisiona."
  [ "$peso" -le "$LIMITE_INVIO" ] \
    || errore "il prompt e' di $peso byte, oltre il limite di $LIMITE_INVIO: arriverebbe troncato senza che nessuno lo dica. Chiudi la PR in due."

  command -v "$AGY" >/dev/null 2>&1 || avviso "manca agy: salto Gemini."
  command -v "$CODEX" >/dev/null 2>&1 || avviso "manca codex: salto Codex."

  # I due revisori partono insieme: sono indipendenti, e in serie
  # raddoppierebbero l'attesa senza dare niente in piu'.
  local pid_agy=0 pid_codex=0
  if command -v "$AGY" >/dev/null 2>&1; then
    "$AGY" --print "$(cat "$prompt")" \
           --model "$MODELLO_AGY" --effort high \
           --output-format json --json-schema "$schema" \
           --print-timeout "$ATTESA" --sandbox \
           > "$lav/gemini.txt" 2> "$lav/gemini.err" &
    pid_agy=$!
    printf 'Gemini interrogato (pid %s)…\n' "$pid_agy"
  fi
  if command -v "$CODEX" >/dev/null 2>&1; then
    "$CODEX" exec - --sandbox read-only --ephemeral --color never \
             --output-schema "$schema" \
             < "$prompt" > "$lav/codex.txt" 2> "$lav/codex.err" &
    pid_codex=$!
    printf 'Codex interrogato (pid %s)…\n' "$pid_codex"
  fi

  [ "$pid_agy" -ne 0 ] || [ "$pid_codex" -ne 0 ] \
    || errore "nessuno dei due revisori e' installato: non c'e' niente da interrogare."

  [ "$pid_agy"   -ne 0 ] && { wait "$pid_agy"   || avviso "agy ha chiuso male: vedi $lav/gemini.err"; }
  [ "$pid_codex" -ne 0 ] && { wait "$pid_codex" || avviso "codex ha chiuso male: vedi $lav/codex.err"; }

  printf '\nRisposte in %s. Ora: revisione.sh rilievi %s\n' "$lav" "$n"
  return 0
}

# --------------------------------------------------------------- rilievi -----

cmd_rilievi () {
  local n="${1:-}"
  identificativo_valido "$n" || errore "uso: revisione.sh rilievi <numero-pr|etichetta>"
  local lav; lav="$(cartella_di "$n")"
  [ -d "$lav" ] || errore "non c'è nessuna revisione aperta con il nome «$n»."
  [ -f "$lav/gemini.txt" ] || [ -f "$lav/codex.txt" ] \
    || errore "nessuna risposta in $lav. Hai lanciato 'interroga $n --invia'?"
  command -v python3 >/dev/null 2>&1 || errore "manca python3. Vedi INSTALL-ENV.md."

  python3 "$skill/scripts/normalizza.py" "$lav" "$n" || errore "la normalizzazione è fallita."
  printf '\nOra tocca a chi decide: ogni scheda di %s/rilievi.md\n' "$lav"
  printf 'ha un "Verdetto" da compilare. Finché ne resta uno, archivia rifiuta.\n'
}

# -------------------------------------------------------------- archivia -----

# Il progetto si ricava dal ramo di partenza della PR: per ADR-002 una feature
# e' un progetto, quindi feature/create-VM porta la revisione dentro create-VM/.
# Una PR che parte da un ramo d'infrastruttura non ha un progetto, e la sua
# revisione va nella radice.
progetto_di () {
  local lav="$1" head
  head="$(jq -r '.headRefName // ""' "$lav/meta.json" 2>/dev/null)"
  case "$head" in
    feature/*) printf '%s' "${head#feature/}" ;;
    step/*)    printf '%s' "$(printf '%s' "${head#step/}" | cut -d/ -f1)" ;;
    *)         printf '' ;;
  esac
}

cmd_archivia () {
  local n="${1:-}"; shift || true
  identificativo_valido "$n" || errore "uso: revisione.sh archivia <numero-pr|etichetta> [--scrivi]"
  local scrivi=0
  [ "${1:-}" = "--scrivi" ] && scrivi=1

  local lav; lav="$(cartella_di "$n")"
  local f="$lav/rilievi.md"
  [ -f "$f" ] || errore "manca $f. Lancia prima 'revisione.sh rilievi $n'."

  local aperti; aperti="$(grep -c '_da compilare_' "$f" || true)"
  if [ "$aperti" -ne 0 ]; then
    errore "restano $aperti verdetti da compilare in $f.
Un rilievo senza verdetto non e' stato valutato, e archiviarlo direbbe il contrario."
  fi

  local prj destinazione doc
  prj="$(progetto_di "$lav")"
  doc="$(nome_docs)"
  if [ -n "$prj" ] && [ -d "$radice/$prj" ]; then
    destinazione="$radice/$prj/$doc/revisioni"
  else
    destinazione="$radice/$doc/revisioni"
  fi

  # Una revisione senza PR non si chiama «pr-qualcosa»: il nome del file dice
  # da dove viene, altrimenti fra un anno nessuno sa che cosa ha guardato.
  local nome
  if numero_valido "$n"; then
    nome="$(date '+%Y-%m-%d')-pr-$n.md"
  else
    nome="$(date '+%Y-%m-%d')-$n.md"
  fi
  if [ "$scrivi" -eq 0 ]; then
    printf 'PROVA A VUOTO — copierei\n  %s\nin\n  %s/%s\n' "$f" "$destinazione" "$nome"
    printf '\nPer procedere: revisione.sh archivia %s --scrivi\n' "$n"
    return 0
  fi

  mkdir -p "$destinazione"
  cp "$f" "$destinazione/$nome"
  printf 'archiviata in %s/%s\n' "$destinazione" "$nome"
  printf 'Aggiungila al commit di chiusura con un percorso esplicito.\n'
}

# ----------------------------------------------------------------- stato -----

cmd_stato () {
  local base="$radice/.revisioni"
  [ -d "$base" ] || { printf 'nessuna revisione aperta.\n'; return 0; }
  local trovate=0 dir n etichetta
  for dir in "$base"/*; do
    [ -d "$dir" ] || continue
    trovate=1
    etichetta="$(basename "$dir")"
    case "$etichetta" in
      pr-*) n="${etichetta#pr-}"
            if numero_valido "$n"; then printf 'PR #%s — %s\n' "$n" "$dir"
            else printf 'intervallo %s — %s\n' "$etichetta" "$dir"; fi ;;
      *)    printf 'intervallo %s — %s\n' "$etichetta" "$dir" ;;
    esac
    [ -f "$dir/dossier.md" ] && printf '  dossier   %s byte\n' "$(wc -c < "$dir/dossier.md" | tr -d ' ')"
    [ -f "$dir/gemini.txt" ] && printf '  gemini    risposto\n'
    [ -f "$dir/codex.txt"  ] && printf '  codex     risposto\n'
    if [ -f "$dir/rilievi.md" ]; then
      printf '  rilievi   %s da compilare\n' "$(grep -c '_da compilare_' "$dir/rilievi.md" || true)"
    fi
  done
  [ "$trovate" -eq 1 ] || printf 'nessuna revisione aperta.\n'
  return 0
}

# ------------------------------------------------------------------- uso -----

uso () {
  cat <<'AIUTO'
uso: revisione.sh <comando> [argomenti]

  dossier   <n>              raccoglie la PR in un unico file leggibile
  interroga <id> [--invia]   lo manda a Gemini Pro e a Codex
  rilievi   <id>             unisce le risposte in un foglio di triage
  archivia  <id> [--scrivi]  controlla che il triage sia completo e lo mette nel repo

  dossier-rami <etichetta> <base>..<head> [percorso...]
                             come dossier, ma da un intervallo di rami: serve
                             quando si revisiona prima che la PR esista, e
                             quando l'intervallo intero non entra in un prompt

  segreti   <id>             passa il dossier al setaccio, da solo
  stato                      che cosa c'e' nelle cartelle di lavoro

<id> e' il numero di una PR oppure l'etichetta di un intervallo.

Senza --invia non esce niente da questa macchina: si vede solo che cosa
uscirebbe, verso chi e quanto grande. Il dossier viene comunque passato al
setaccio dei segreti, e un segreto trovato ferma l'invio.
AIUTO
}

case "${1:-}" in
  dossier)      shift; cmd_dossier      "$@" ;;
  dossier-rami) shift; cmd_dossier_rami "$@" ;;
  segreti)   shift; cmd_segreti   "$@" ;;
  interroga) shift; cmd_interroga "$@" ;;
  rilievi)   shift; cmd_rilievi   "$@" ;;
  archivia)  shift; cmd_archivia  "$@" ;;
  stato)     shift; cmd_stato     "$@" ;;
  ''|-h|--help|aiuto) uso ;;
  *) errore "comando sconosciuto: '$1'. Prova 'revisione.sh --help'." ;;
esac
