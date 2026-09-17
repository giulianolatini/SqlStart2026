#!/usr/bin/env bash
# Banco di prova di step.sh.
#
# Costruisce repository usa e getta in una cartella temporanea, con un remoto
# bare vero. I comportamenti da verificare coinvolgono piu' worktree, un
# remoto e i rifiuti di git: non sono simulabili, e una suite che li simulasse
# verificherebbe soltanto che il codice chiama git come il test si aspetta.
#
# Copre i punti 1-6 del collaudo dichiarato nella spec. Il punto 7, la
# coerenza dei registri di radice, si verifica con:
#   python3 .claude/skills/decision-md/scripts/check-crosslinks.py Docs

set -uo pipefail

STEP="$(cd "$(dirname "$0")/../scripts" && pwd)/step.sh"
BANCO="$(mktemp -d)"
# La pulizia e' piu' difensiva di quanto sembri necessario, e la ragione e'
# concreta: gli indicizzatori di codice - tokensave, e chiunque altro osservi
# la comparsa di un repository - creano i propri file dentro un checkout
# appena nato. Se lo fanno mentre rm sta camminando l'albero, la cartella si
# ripopola sotto e rm esce con "Directory not empty" pur avendo quasi finito,
# e la suite sembra rotta pur essendo tutta verde. Il `cd /` serve invece a
# non restare dentro l'albero che si sta cancellando.
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

# Verifica una condizione booleana gia' valutata dal chiamante.
vero () { if [ "$1" = "0" ]; then ok "$2"; else ko "$2"; fi; }

# Lascia in $1 un repo con origin bare, develop e le feature alfa e beta.
crea_repo_di_prova () {
  local d="$1" p
  git init -q --bare "$d/origin.git"
  git init -q -b main "$d/repo"
  git -C "$d/repo" config user.email banco@prova
  git -C "$d/repo" config user.name Banco
  # Senza questi, git lancia processi di manutenzione in background che
  # continuano a scrivere dentro .git mentre il trap cancella la cartella
  # temporanea: rm fallisce con "Directory not empty" e la suite sembra rotta
  # pur essendo tutta verde.
  git -C "$d/repo" config gc.auto 0
  git -C "$d/repo" config maintenance.auto false
  git -C "$d/origin.git" config gc.auto 0
  git -C "$d/origin.git" config maintenance.auto false
  git -C "$d/repo" remote add origin "$d/origin.git"
  echo licenza > "$d/repo/LICENSE"
  git -C "$d/repo" add LICENSE
  git -C "$d/repo" commit -qm "commit iniziale"
  git -C "$d/repo" checkout -qb develop
  mkdir -p "$d/repo/.claude/skills"
  echo infrastruttura > "$d/repo/.claude/skills/segnaposto"
  git -C "$d/repo" add .claude/skills/segnaposto
  git -C "$d/repo" commit -qm "infrastruttura di repo"
  for p in alfa beta; do
    git -C "$d/repo" checkout -q -b "feature/$p" develop
    mkdir -p "$d/repo/$p"
    echo "progetto $p" > "$d/repo/$p/README.md"
    git -C "$d/repo" add "$p/README.md"
    git -C "$d/repo" commit -qm "$p nasce"
  done
  git -C "$d/repo" checkout -q develop
  git -C "$d/repo" push -q --all origin
}

# Fabbrica un commit sulla feature $2 senza lasciarla estratta: e' l'unico
# modo di produrre un vero non-fast-forward. Spostare la feature ALL'INDIETRO
# non basta — la renderebbe antenata dello step, e la chiusura riuscirebbe a
# ragione.
commit_esterno_sulla_feature () {
  local repo="$1" prj="$2"
  # Due `local` distinti e non uno solo: in bash le espansioni di una singola
  # istruzione avvengono tutte PRIMA delle assegnazioni, quindi "$prj" qui
  # sarebbe ancora vuoto.
  local tmp="$repo/../esterno-$prj"
  git -C "$repo" worktree add -q "$tmp" "feature/$prj"
  echo esterno > "$tmp/esterno.txt"
  git -C "$tmp" add esterno.txt
  git -C "$tmp" commit -qm "commit arrivato sulla feature da fuori"
  git -C "$repo" worktree remove "$tmp"
}

# ---------------------------------------------------------------------------

caso "lo script esiste ed e' eseguibile"
[ -x "$STEP" ]; vero $? "step.sh eseguibile"

caso "stato, a repo pulito"
crea_repo_di_prova "$BANCO/a"
uscita="$(cd "$BANCO/a/repo" && "$STEP" stato 2>&1)"
echo "$uscita" | grep -q "feature/alfa"; vero $? "nomina feature/alfa"
echo "$uscita" | grep -q "feature/beta"; vero $? "nomina feature/beta"
echo "$uscita" | grep -qi "nessun cantiere"; vero $? "dichiara l'assenza di cantieri"

caso "apri crea ramo e cantiere, e indica come entrarci"
cd "$BANCO/a/repo" || exit 1
uscita="$("$STEP" apri alfa primo-passo 2>&1)"
git show-ref --verify --quiet refs/heads/step/alfa/primo-passo
vero $? "il ramo step/alfa/primo-passo esiste"
[ -d "$BANCO/a/repo/.claude/worktrees/alfa--primo-passo" ]
vero $? "il cantiere esiste"
echo "$uscita" | grep -q 'EnterWorktree(path:'; vero $? "indica EnterWorktree con path:"
echo "$uscita" | grep -q 'name:'; vero $? "avverte di non usare name:"

caso "apri rifiuta la seconda apertura sullo stesso progetto"
"$STEP" apri alfa altro-passo >/dev/null 2>&1
[ $? -ne 0 ]; vero $? "rifiuta il secondo cantiere su alfa"

caso "isolamento: un cantiere su un altro progetto e' ammesso"
"$STEP" apri beta suo-passo >/dev/null 2>&1
vero $? "apre il cantiere su beta mentre alfa e' occupato"

caso "apri rifiuta cio' che non esiste o e' occupato"
"$STEP" apri inesistente x >/dev/null 2>&1
[ $? -ne 0 ]; vero $? "rifiuta un progetto senza ramo di feature"
"$STEP" apri alfa Nome_Sbagliato >/dev/null 2>&1
[ $? -ne 0 ]; vero $? "rifiuta un nome di step non in minuscolo con trattini"

caso "chiusura in fast-forward, con push"
cd "$BANCO/a/repo/.claude/worktrees/alfa--primo-passo" || exit 1
echo uno >> alfa/README.md; git commit -qam "feat(alfa): primo commit logico"
echo due >> alfa/README.md; git commit -qam "feat(alfa): secondo commit logico"
"$STEP" chiudi >/dev/null 2>&1; vero $? "chiudi riesce"
[ "$(git rev-parse feature/alfa)" = "$(git rev-parse step/alfa/primo-passo)" ]
vero $? "feature/alfa e' avanzata fino allo step"
[ "$(git rev-list --count --merges feature/alfa)" = "0" ]
vero $? "nessun merge commit: e' stato un fast-forward"
[ "$(git rev-parse origin/feature/alfa)" = "$(git rev-parse feature/alfa)" ]
vero $? "il remoto ha ricevuto il push"

caso "chiudi rifiuta dentro un albero sporco"
cd "$BANCO/a/repo/.claude/worktrees/beta--suo-passo" || exit 1
echo b >> beta/README.md; git commit -qam "feat(beta): lavoro dello step"
echo sporco > non-committato
"$STEP" chiudi >/dev/null 2>&1
[ $? -ne 0 ]; vero $? "rifiuta con modifiche non committate"
rm non-committato

caso "smonta, dopo una chiusura riuscita"
cd "$BANCO/a/repo" || exit 1
"$STEP" smonta alfa primo-passo >/dev/null 2>&1; vero $? "smonta riesce"
[ ! -d .claude/worktrees/alfa--primo-passo ]; vero $? "il cantiere e' sparito"
git show-ref --verify --quiet refs/heads/step/alfa/primo-passo
[ $? -ne 0 ]; vero $? "il ramo di step e' sparito"

caso "sessione morta: si rientra nel cantiere e si chiude"
"$STEP" apri alfa ripreso >/dev/null 2>&1
cd "$BANCO/a/repo/.claude/worktrees/alfa--ripreso" || exit 1
echo tre >> alfa/README.md; git commit -qam "feat(alfa): lavoro interrotto"
cd "$BANCO/a/repo" || exit 1                       # la sessione "muore"
uscita="$("$STEP" stato 2>&1)"
echo "$uscita" | grep -q "step/alfa/ripreso"; vero $? "stato ritrova il cantiere orfano"
cd "$BANCO/a/repo/.claude/worktrees/alfa--ripreso" || exit 1   # si "rientra"
"$STEP" chiudi >/dev/null 2>&1; vero $? "lo step ripreso si chiude regolarmente"
cd "$BANCO/a/repo" || exit 1
"$STEP" smonta alfa ripreso >/dev/null 2>&1; vero $? "e si smonta"

caso "il non-fast-forward viene rifiutato, e la feature resta ferma"
commit_esterno_sulla_feature "$BANCO/a/repo" beta
atteso="$(git rev-parse feature/beta)"
cd "$BANCO/a/repo/.claude/worktrees/beta--suo-passo" || exit 1
"$STEP" chiudi >/dev/null 2>&1
[ $? -ne 0 ]; vero $? "rifiuta il non-fast-forward"
[ "$(git rev-parse feature/beta)" = "$atteso" ]
vero $? "feature/beta e' rimasta esattamente dov'era"

caso "smonta rifiuta un ramo non fuso"
cd "$BANCO/a/repo" || exit 1
"$STEP" smonta beta suo-passo >/dev/null 2>&1
[ $? -ne 0 ]; vero $? "rifiuta di smontare un ramo non fuso"
[ -d .claude/worktrees/beta--suo-passo ]; vero $? "il cantiere e' ancora li'"

caso "l'abbandono esige il mandato, e non tocca la feature"
"$STEP" abbandona beta suo-passo >/dev/null 2>&1
[ $? -ne 0 ]; vero $? "rifiuta l'abbandono senza mandato"
[ -d .claude/worktrees/beta--suo-passo ]; vero $? "il cantiere e' intatto"
prima="$(git rev-parse feature/beta)"
"$STEP" abbandona beta suo-passo --mandato >/dev/null 2>&1
vero $? "abbandona riesce col mandato"
[ ! -d .claude/worktrees/beta--suo-passo ]; vero $? "il cantiere e' sparito"
[ "$(git rev-parse feature/beta)" = "$prima" ]; vero $? "feature/beta e' intatta"

caso "git rifiuta lo stesso ramo in due worktree"
# E' la garanzia di isolamento fra agent, e non costa nulla: git tiene un solo
# checkout per ramo, per costruzione. Vale la pena verificarlo, perche' tutto
# il modello ci si appoggia.
git worktree add -q "$BANCO/a/doppione" feature/alfa >/dev/null 2>&1
vero $? "il primo checkout di feature/alfa riesce"
git worktree add "$BANCO/a/doppione-2" feature/alfa >/dev/null 2>&1
[ $? -ne 0 ]; vero $? "il secondo checkout dello stesso ramo e' rifiutato da git"
# Smontato subito: un checkout lasciato in piedi attira gli indicizzatori, che
# gli scrivono dentro proprio mentre il trap cancella la cartella temporanea.
git worktree remove --force "$BANCO/a/doppione" >/dev/null 2>&1

# ---------------------------------------------------------------------------

printf '\n%d passati, %d falliti\n' "$PASSATI" "$FALLITI"
[ "$FALLITI" -eq 0 ]
