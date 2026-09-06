#!/usr/bin/env bash
# changelog.sh — costruisce i CHANGELOG del repository d'origine dai messaggi di commit.
#
# Il repository ha gia' quattro registri scritti a mano. Questo NON e' il
# quinto: e' l'unico documento del repo che si genera, e si genera perche' la
# fonte c'e' gia' ed e' affidabile. I commit seguono Conventional Commits, e un
# messaggio conforme e' meta' di una voce di changelog.
#
# Due momenti, due comandi:
#   feature   <prj>          prima del merge feature -> develop
#   rilascio  <prj> <n>      quando il progetto viene archiviato su main
#
# Piu' due di servizio:
#   messaggio <prj> <n>      il corpo del commit di rilascio (ADR-009)
#   verifica  <prj>          il CHANGELOG e' allineato ai commit?
#
# ORDINE CRONOLOGICO, non "Keep a Changelog". La scelta e' in ADR-019: qui
# serve la sequenza degli eventi, non un catalogo per categoria.

set -uo pipefail

errore () { printf 'changelog: %s\n' "$1" >&2; exit 1; }

git rev-parse --git-dir >/dev/null 2>&1 || errore "non sei dentro un repository git."

# Si scrive nel worktree CORRENTE, non nel checkout principale. Il CHANGELOG di
# una feature si genera stando sulla feature - dentro un cantiere di step - ed
# e' li' che la cartella del progetto esiste. Puntare al checkout principale,
# che sta su develop, scriverebbe il file dove il progetto non c'e'.
radice="$(git rev-parse --show-toplevel)"
ramo_corrente="$(git rev-parse --abbrev-ref HEAD)"

US=$'\x1f'   # separatore di campo
RS=$'\x1e'   # separatore di record: i corpi dei commit sono multilinea

# --------------------------------------------------------------- il motore --

# Trasforma un elenco di commit in una sezione markdown.
# Legge da stdin i record prodotti da git log, scrive markdown su stdout.
formatta () {
  awk -v RS="$RS" -v FS="$US" '
    function etichetta (t) {
      if (t == "feat")     return "Funzionalità"
      if (t == "fix")      return "Correzione"
      if (t == "docs")     return "Documentazione"
      if (t == "refactor") return "Rifattorizzazione"
      if (t == "perf")     return "Prestazioni"
      if (t == "test")     return "Test"
      if (t == "build")    return "Build"
      if (t == "ci")       return "Integrazione continua"
      if (t == "style")    return "Forma"
      if (t == "chore")    return "Manutenzione"
      if (t == "revert")   return "Ripristino"
      if (t == "release")  return "Rilascio"
      return ""
    }
    {
      sha = $1; data = $2; sogg = $3; corpo = $4
      gsub(/^[ \t\n]+|[ \t\n]+$/, "", sha)
      if (sha == "") next
      n++

      tipo = ""; ambito = ""; rottura = 0; testo = sogg

      # type(scope)!: soggetto — lo scope e il ! sono facoltativi.
      if (match(sogg, /^[a-z]+(\([^)]*\))?!?: /)) {
        intestazione = substr(sogg, 1, RLENGTH - 2)
        testo        = substr(sogg, RLENGTH + 1)
        if (index(intestazione, "!") > 0) { rottura = 1; sub(/!$/, "", intestazione) }
        if (match(intestazione, /\([^)]*\)$/)) {
          ambito       = substr(intestazione, RSTART + 1, RLENGTH - 2)
          intestazione = substr(intestazione, 1, RSTART - 1)
        }
        tipo = intestazione
      }
      if (corpo ~ /BREAKING[ -]CHANGE/) rottura = 1

      et = etichetta(tipo)
      if (et == "") { et = "Fuori convenzione"; fuori++ } else { conteggio[et]++ }

      voce = "- **" et "**"
      if (ambito != "" ) voce = voce " · `" ambito "`"
      voce = voce " — " testo " (`" sha "`)"
      if (rottura) { voce = voce " ⚠️"; rotture[++nr] = "> - `" sha "` — " testo }

      if (data != ultima) { ultima = data; righe[++nrighe] = ""; righe[++nrighe] = "### " data }
      righe[++nrighe] = voce

      if (prima == "") prima = data
      dopo = data
    }
    END {
      if (n == 0) { print "NESSUN_COMMIT"; exit 0 }

      riepilogo = n " commit"
      if (prima == dopo) riepilogo = riepilogo " del " prima
      else               riepilogo = riepilogo ", dal " prima " al " dopo
      sep = " — "
      for (k in conteggio) { riepilogo = riepilogo sep tolower(k) ": " conteggio[k]; sep = ", " }
      if (fuori) riepilogo = riepilogo sep "fuori convenzione: " fuori
      print riepilogo "."

      if (nr > 0) {
        print ""
        print "> [!WARNING]"
        print "> **Rotture di compatibilità introdotte qui:**"
        for (i = 1; i <= nr; i++) print rotture[i]
      }

      for (i = 1; i <= nrighe; i++) print righe[i]
    }
  '
}

# Legge i commit di un intervallo in ordine cronologico. I percorsi sono
# facoltativi: passarne zero significa "tutto l'intervallo".
commit_di () {
  local intervallo="$1"; shift
  if [ "$#" -eq 0 ]; then
    git log --no-merges --reverse --date=short \
        --format="%h${US}%ad${US}%s${US}%b${RS}" "$intervallo"
  else
    git log --no-merges --reverse --date=short \
        --format="%h${US}%ad${US}%s${US}%b${RS}" "$intervallo" -- "$@"
  fi
}

# Al rilascio il filtro sui percorsi serve, e ne servono DUE. Il secondo
# esiste perche' ADR-016 ha promosso headroom-scan da Tools/headroom-scan/ a
# cartella di primo livello: filtrare solo sul percorso di oggi perderebbe
# tutti i commit precedenti alla rinomina, a cominciare da quello che ha creato
# il progetto. Uso: commit_di develop "$prj/" "*/$prj/*"
#
# L'asterisco finale del secondo NON e' ornamentale: senza magia esplicita git
# confronta il pathspec con il percorso INTERO, quindi "*/alfa/" non trova
# "Tools/alfa/alfa.sh" mentre "*/alfa/*" si'. Il primo pathspec invece finisce
# con / e basta, perche' li' e' un prefisso di cartella letterale.

# Sostituisce (o inserisce) un blocco delimitato da marcatori dentro un file.
# I marcatori esistono perche' rigenerare due volte non deve produrre due
# copie: senza un delimitatore stabile la deduplica dipenderebbe dal titolo,
# che cambia appena cambia una data.
#
# Il blocco arriva in un FILE e non in una variabile: `awk -v` non accetta
# valori che contengono un a capo, e passandogli la sezione intera awk si
# ferma con "newline in string" scrivendo un file troncato. Il difetto era
# silenzioso quel tanto che basta - il file veniva creato lo stesso.
inserisci_blocco () {
  local file="$1" chiave="$2" file_blocco="$3" intestazione="$4"
  local apre="<!-- changelog:$chiave -->"
  local chiude="<!-- /changelog:$chiave -->"
  local senza testa coda
  senza="$(mktemp)"; testa="$(mktemp)"; coda="$(mktemp)"

  [ -f "$file" ] || printf '%s\n' "$intestazione" > "$file"

  # 1. via il blocco vecchio, se c'e'.
  awk -v a="$apre" -v c="$chiude" '
    $0 == a { dentro = 1; next }
    $0 == c { dentro = 0; next }
    !dentro { print }
  ' "$file" > "$senza"

  # 2. taglia in due: intestazione, poi tutto dalla prima sezione in giu'.
  awk -v t="$testa" -v k="$coda" '
    /^## / { messo = 1 }
    { if (messo) print > k; else print > t }
  ' "$senza"

  # 3. il blocco nuovo va in mezzo: il piu' recente resta in alto.
  {
    cat "$testa"
    printf '%s\n' "$apre"
    cat "$file_blocco"
    printf '%s\n\n' "$chiude"
    cat "$coda"
  } > "$file"

  rm -f "$senza" "$testa" "$coda"
}

intestazione_progetto () {
  printf '# CHANGELOG — %s\n\n%s\n%s\n' "$1" \
    "Generato da \`.claude/skills/changelog-di-chiusura/scripts/changelog.sh\` dai messaggi di" \
    "commit, in ordine cronologico. Non si scrive a mano: si rigenera."
}

# -------------------------------------------------------------- feature -----

cmd_feature () {
  local prj="${1:-}"; shift || true
  [ -n "$prj" ] || errore "uso: changelog.sh feature <progetto> [--scrivi]"
  local scrivi=0
  [ "${1:-}" = "--scrivi" ] && scrivi=1

  git show-ref --verify --quiet "refs/heads/feature/$prj" \
    || errore "il ramo feature/$prj non esiste."

  # Nessun filtro sui percorsi, ed e' voluto: develop..feature/<prj> contiene
  # esattamente i commit scritti su quel ramo. Quelli arrivati da develop con i
  # riallineamenti sono raggiungibili da develop, quindi fuori intervallo; i
  # commit di merge li toglie --no-merges. Per ADR-002 una feature E' un
  # progetto: l'invariante fa da filtro, meglio di qualunque euristica.
  local sezione
  sezione="$(commit_di "develop..feature/$prj" | formatta)"
  [ "$sezione" = "NESSUN_COMMIT" ] \
    && errore "nessun commit in develop..feature/$prj — non c'è niente da raccontare."

  local blocco; blocco="$(mktemp)"
  printf '## Feature %s — chiusa il %s\n\n%s\n' "$prj" "$(date '+%Y-%m-%d')" "$sezione" > "$blocco"

  if [ "$scrivi" -eq 0 ]; then
    cat "$blocco"; rm -f "$blocco"
    printf '\n--- anteprima. Aggiungi --scrivi per aggiornare %s/CHANGELOG.md ---\n' "$prj" >&2
    return 0
  fi

  case "$ramo_corrente" in
    "feature/$prj"|"step/$prj/"*) ;;
    *) errore "sei su '$ramo_corrente'. Il CHANGELOG di $prj si scrive stando sul suo ramo:
apri un cantiere con 'step.sh apri $prj changelog', entraci, e rilancia da lì." ;;
  esac
  [ -d "$radice/$prj" ] \
    || errore "la cartella $prj/ non esiste in questo worktree, pur essendo sul ramo giusto."

  local file="$radice/$prj/CHANGELOG.md"
  inserisci_blocco "$file" "feature/$prj" "$blocco" "$(intestazione_progetto "$prj")"
  rm -f "$blocco"
  printf 'aggiornato %s\n' "$file"
}

# ------------------------------------------------------------- rilascio -----

cmd_rilascio () {
  local prj="${1:-}" num="${2:-}"; shift 2 2>/dev/null || true
  [ -n "$prj" ] && [ -n "$num" ] || errore "uso: changelog.sh rilascio <progetto> <numero> [--scrivi]"
  local scrivi=0
  [ "${1:-}" = "--scrivi" ] && scrivi=1

  # Al rilascio il progetto e' gia' su develop, e su develop c'e' anche tutto
  # il resto: qui il filtro sui percorsi serve davvero.
  local sezione
  sezione="$(commit_di "develop" "$prj/" "*/$prj/*" | formatta)"
  [ "$sezione" = "NESSUN_COMMIT" ] \
    && errore "nessun commit su develop che tocchi $prj/ — il progetto è stato fuso?"

  local blocco; blocco="$(mktemp)"
  printf '## Rilascio %s — %s, archiviato il %s\n\n%s\n' \
    "$num" "$prj" "$(date '+%Y-%m-%d')" "$sezione" > "$blocco"

  if [ "$scrivi" -eq 0 ]; then
    cat "$blocco"; rm -f "$blocco"
    printf '\n--- anteprima. Aggiungi --scrivi per aggiornare CHANGELOG.md ---\n' >&2
    return 0
  fi

  inserisci_blocco "$radice/CHANGELOG.md" "rilascio/$num" "$blocco" \
    "$(printf '# CHANGELOG\n\n%s\n%s\n' \
        "Un rilascio archivia un progetto su \`main\`. Le voci sono in ordine cronologico dentro" \
        "ogni rilascio, e i rilasci in ordine inverso: il più recente in alto.")"
  rm -f "$blocco"
  printf 'aggiornato %s\n' "$radice/CHANGELOG.md"
}

# ------------------------------------------------------------ messaggio -----

cmd_messaggio () {
  local prj="${1:-}" num="${2:-}"
  [ -n "$prj" ] && [ -n "$num" ] || errore "uso: changelog.sh messaggio <progetto> <numero>"

  printf 'release(%s): archivia %s con il rilascio %s\n\n' "$prj" "$prj" "$num"
  printf 'Titoli dei commit archiviati, in ordine cronologico:\n\n'
  git log --no-merges --reverse --date=short --format='%ad %h %s' develop -- "$prj/" "*/$prj/*"
}

# ------------------------------------------------------------- verifica -----

cmd_verifica () {
  local prj="${1:-}"
  [ -n "$prj" ] || errore "uso: changelog.sh verifica <progetto>"

  local file="$radice/$prj/CHANGELOG.md"
  local ultimo
  ultimo="$(git log --no-merges -1 --format='%h' "develop..feature/$prj" 2>/dev/null || true)"

  if [ -z "$ultimo" ]; then
    printf 'nessun commit da raccontare per %s: niente da fare.\n' "$prj"
    return 0
  fi
  if [ ! -f "$file" ]; then
    printf 'MANCA %s/CHANGELOG.md — da generare prima del merge su develop.\n' "$prj" >&2
    return 1
  fi
  if grep -q "$ultimo" "$file"; then
    printf '%s/CHANGELOG.md è allineato (ultimo commit %s presente).\n' "$prj" "$ultimo"
    return 0
  fi
  printf 'DA RIGENERARE: %s/CHANGELOG.md non contiene l'\''ultimo commit %s.\n' "$prj" "$ultimo" >&2
  return 1
}

# ----------------------------------------------------------------- uso ------

uso () {
  cat <<'AIUTO'
uso: changelog.sh <comando> [argomenti]

  feature   <prj> [--scrivi]        sezione per la chiusura della feature su develop
  rilascio  <prj> <n> [--scrivi]    sezione per l'archiviazione su main
  messaggio <prj> <n>               corpo del commit di rilascio
  verifica  <prj>                   il CHANGELOG copre l'ultimo commit?

Senza --scrivi i due comandi di generazione stampano l'anteprima e non toccano
nulla: e' il modo giusto di guardare prima di scrivere.
AIUTO
}

case "${1:-}" in
  feature)   shift; cmd_feature   "$@" ;;
  rilascio)  shift; cmd_rilascio  "$@" ;;
  messaggio) shift; cmd_messaggio "$@" ;;
  verifica)  shift; cmd_verifica  "$@" ;;
  ''|-h|--help|aiuto) uso ;;
  *) errore "comando sconosciuto: '$1'. Prova 'changelog.sh --help'." ;;
esac
