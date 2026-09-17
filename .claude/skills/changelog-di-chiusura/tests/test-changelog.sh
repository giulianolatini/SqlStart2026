#!/usr/bin/env bash
# Banco di prova di changelog.sh.
#
# Costruisce un repository usa e getta con develop, due feature e una rinomina
# di cartella, perche' le cose che possono davvero andare storte sono:
#   - raccogliere commit che non appartengono alla feature,
#   - perdere i commit precedenti a una rinomina al momento del rilascio,
#   - duplicare il blocco rigenerandolo due volte,
#   - scrivere il file nel checkout sbagliato.
# Nessuna delle quattro si vede su un repository finto a un commit solo.

set -uo pipefail

CL="$(cd "$(dirname "$0")/../scripts" && pwd)/changelog.sh"
BANCO="$(mktemp -d)"

# Stessa cautela della suite di step.sh: gli indicizzatori di codice scrivono
# dentro un checkout appena nato, e se lo fanno mentre rm cammina l'albero la
# cartella si ripopola sotto e rm esce con "Directory not empty".
ripulisci () {
  cd /
  rm -rf "$BANCO" 2>/dev/null || rm -rf "$BANCO" 2>/dev/null
  [ -d "$BANCO" ] && printf "\nnota: %s non è stata rimossa del tutto (non è un fallimento delle prove).\n" "$BANCO"
  return 0
}
trap ripulisci EXIT
PASSATI=0; FALLITI=0

ok ()   { PASSATI=$((PASSATI+1)); printf '  ok   %s\n' "$1"; }
ko ()   { FALLITI=$((FALLITI+1)); printf '  KO   %s\n' "$1"; }
caso () { printf '\n== %s\n' "$1"; }

# La descrizione viene prima del comando: cosi' l'esito si legge senza passare
# da $?, che shellcheck segnala a ragione come fragile.
prova ()    { local d="$1"; shift; if "$@"; then ok "$d"; else ko "$d"; fi; }
prova_no () { local d="$1"; shift; if "$@"; then ko "$d"; else ok "$d"; fi; }
muto ()     { "$@" >/dev/null 2>&1; }

contiene ()  { case "$1" in *"$2"*) return 0 ;; *) return 1 ;; esac; }
conta_uno () { [ "$(grep -c "$2" "$1")" = "${3:-1}" ]; }

R="$BANCO/repo"

commit () {   # commit <percorso> <soggetto> [corpo]
  local percorso="$1" soggetto="$2" corpo="${3:-}"
  mkdir -p "$R/$(dirname "$percorso")"
  echo "$RANDOM" >> "$R/$percorso"
  git -C "$R" add "$percorso"
  if [ -n "$corpo" ]; then
    git -C "$R" commit -q -m "$soggetto" -m "$corpo"
  else
    git -C "$R" commit -q -m "$soggetto"
  fi
}

# --------------------------------------------------------------- il banco ---

git init -q -b main "$R"
git -C "$R" config user.email banco@prova
git -C "$R" config user.name Banco
git -C "$R" config gc.auto 0
git -C "$R" config maintenance.auto false

echo licenza > "$R/LICENSE"
git -C "$R" add LICENSE
git -C "$R" commit -qm "commit iniziale"
git -C "$R" checkout -qb develop
commit "Docs/Decision.md" "docs: apre il registro delle decisioni"

# feature/alfa — nata sotto Tools/, poi promossa a cartella di primo livello.
git -C "$R" checkout -q -b feature/alfa develop
commit "Tools/alfa/alfa.sh" "Init alfa tool"
commit "Tools/alfa/alfa.sh" "feat(alfa): aggiunge la scansione"
git -C "$R" mv Tools/alfa alfa
git -C "$R" commit -qm "refactor(alfa): promuove il progetto a cartella di primo livello"
commit "alfa/alfa.sh" "fix(alfa)!: rinomina il flag --scan in --analizza"
commit "alfa/README.md" "docs(alfa): riscrive la presentazione" \
       "BREAKING CHANGE: l'opzione --vecchia non esiste più."

# feature/beta — serve a provare che il rilascio non la raccoglie.
git -C "$R" checkout -q -b feature/beta develop
commit "beta/beta.sh" "feat(beta): primo abbozzo"

git -C "$R" checkout -q develop

# changelog.sh lavora sul repository della cartella corrente: senza questo cd
# le prove girerebbero contro il repository d'origine, e fallirebbero tutte dicendo che
# feature/alfa non esiste - il che sarebbe vero, e completamente fuorviante.
cd "$R" || exit 1

# ------------------------------------------------------------- 1. feature ---

caso "1. feature: raccoglie l'intervallo giusto"
u="$("$CL" feature alfa 2>/dev/null)"

prova    "conta tutti e cinque i commit della feature"        contiene "$u" "5 commit"
prova    "tiene il commit anteriore alla rinomina"            contiene "$u" "Init alfa tool"
prova    "segnala il fuori convenzione invece di perderlo"    contiene "$u" "fuori convenzione: 1"
prova    "e lo etichetta"                                     contiene "$u" "**Fuori convenzione** — Init alfa tool"
prova_no "NON raccoglie i commit di develop"                  contiene "$u" "apre il registro delle decisioni"
prova_no "NON raccoglie i commit dell'altra feature"          contiene "$u" "primo abbozzo"

caso "2. feature: traduce i tipi Conventional Commit"
prova "feat, con l'ambito"  contiene "$u" "**Funzionalità** · \`alfa\` — aggiunge la scansione"
prova "refactor"            contiene "$u" "**Rifattorizzazione**"
prova "docs"                contiene "$u" "**Documentazione**"
prova "fix"                 contiene "$u" "**Correzione**"

caso "3. feature: riconosce le rotture di compatibilità"
prova "apre il blocco di avviso"          contiene "$u" "> [!WARNING]"
prova "prende il ! nel soggetto"          contiene "$u" "rinomina il flag"
prova "prende BREAKING CHANGE nel corpo"  contiene "$u" "riscrive la presentazione"

caso "4. feature: ordine cronologico crescente"
# Si numerano le sole righe dell'elenco, non l'output intero: il blocco di
# avviso sulle rotture di compatibilita' cita gli stessi commit e sta piu' in
# alto, quindi misurando tutto l'output l'ultimo commit sembrerebbe il primo.
elenco="$(printf '%s\n' "$u" | grep '^- \*\*')"
riga_init="$(printf '%s\n' "$elenco" | grep -n 'Init alfa tool' | head -1 | cut -d: -f1)"
riga_fine="$(printf '%s\n' "$elenco" | grep -n 'riscrive la presentazione' | head -1 | cut -d: -f1)"
prova "il più vecchio compare prima del più recente" test "$riga_init" -lt "$riga_fine"

# -------------------------------------------------------------- 5. scrivi ---

caso "5. --scrivi: rifiuta di scrivere dal ramo sbagliato"
prova_no "da develop esce in errore" muto "$CL" feature alfa --scrivi
prova    "e non crea nulla"          test ! -f "$R/alfa/CHANGELOG.md"

caso "6. --scrivi: dal ramo della feature crea il file"
git -C "$R" checkout -q feature/alfa
prova "esce senza errore"       muto "$CL" feature alfa --scrivi
prova "crea alfa/CHANGELOG.md"  test -f "$R/alfa/CHANGELOG.md"
c="$(cat "$R/alfa/CHANGELOG.md")"
prova "ci mette l'intestazione" contiene "$c" "# CHANGELOG — alfa"
prova "e le voci"               contiene "$c" "aggiunge la scansione"

caso "7. --scrivi due volte: nessun duplicato"
muto "$CL" feature alfa --scrivi
prova "una sola sezione dopo due generazioni" conta_uno "$R/alfa/CHANGELOG.md" '^## Feature alfa' 1
prova "i marcatori restano una coppia sola"   conta_uno "$R/alfa/CHANGELOG.md" 'changelog:feature/alfa' 2

caso "8. --scrivi dopo un commit nuovo: aggiorna, non accoda"
commit "alfa/alfa.sh" "perf(alfa): dimezza il tempo di scansione"
muto "$CL" feature alfa --scrivi
prova "resta una sola sezione"        conta_uno "$R/alfa/CHANGELOG.md" '^## Feature alfa' 1
prova "la voce nuova c'è"             grep -q "dimezza il tempo" "$R/alfa/CHANGELOG.md"
prova "il riepilogo è ricalcolato"    grep -q "6 commit" "$R/alfa/CHANGELOG.md"

# ------------------------------------------------------------ 9. verifica ---

caso "9. verifica"
prova "allineato: esce 0" muto "$CL" verifica alfa
commit "alfa/alfa.sh" "fix(alfa): corregge un fuori-uno"
prova_no "con un commit non raccontato: esce diverso da 0" muto "$CL" verifica alfa
git -C "$R" checkout -q feature/beta
prova_no "senza CHANGELOG: esce diverso da 0"              muto "$CL" verifica beta

# ----------------------------------------------------------- 10. rilascio ---

caso "10. rilascio: filtra per progetto e sopravvive alla rinomina"
git -C "$R" checkout -q develop
git -C "$R" merge -q --ff-only feature/alfa
u="$("$CL" rilascio alfa 1 2>/dev/null)"
prova    "raccoglie i commit anteriori alla rinomina"  contiene "$u" "Init alfa tool"
prova    "e quelli successivi"                         contiene "$u" "dimezza il tempo"
prova_no "esclude l'infrastruttura di develop"         contiene "$u" "apre il registro delle decisioni"
prova    "intesta il rilascio"                         contiene "$u" "## Rilascio 1 — alfa"

caso "11. rilascio --scrivi: CHANGELOG di radice"
prova "esce senza errore"           muto "$CL" rilascio alfa 1 --scrivi
prova "crea CHANGELOG.md in radice" test -f "$R/CHANGELOG.md"
muto "$CL" rilascio alfa 1 --scrivi
prova "rigenerando non duplica"     conta_uno "$R/CHANGELOG.md" '^## Rilascio 1' 1

caso "12. messaggio: corpo del commit di rilascio"
u="$("$CL" messaggio alfa 1 2>/dev/null)"
prova "soggetto Conventional"                contiene "$u" "release(alfa): archivia alfa con il rilascio 1"
prova "elenca i titoli, rinomina compresa"   contiene "$u" "Init alfa tool"

# -------------------------------------------------------------- 13. errori --

caso "13. errori"
prova_no "ramo di feature inesistente: errore" muto "$CL" feature inesistente
prova_no "comando sconosciuto: errore"         muto "$CL" comando-che-non-esiste
prova    "--help esce 0"                       muto "$CL" --help

# ------------------------------------------------------------------ esito ---

printf '\n%d passate, %d fallite\n' "$PASSATI" "$FALLITI"
[ "$FALLITI" -eq 0 ]
