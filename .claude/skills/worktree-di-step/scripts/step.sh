#!/usr/bin/env bash
# step.sh — apre e chiude gli spazi di lavoro isolati del repository d'origine.
#
# Il guasto ricorrente non e' che git sia difficile: e' che la sequenza viene
# improvvisata, ogni volta in modo un po' diverso. Qui c'e' un comando per
# fase, e i controlli di sicurezza smettono di dipendere dal fatto che
# qualcuno si ricordi di farli.
#
# Il modello: un worktree per step, sotto .claude/worktrees/<prj>--<nome>, sul
# ramo step/<prj>/<nome>. Il ramo feature/<prj> non viene MAI estratto: si
# avanza con `git fetch . <step>:<feature>`, che impone il fast-forward e in
# caso di rifiuto lascia il ramo esattamente dov'era.
#
# Le decisioni che spiegano ogni controllo stanno in Docs/Decision.md.

set -uo pipefail

errore () { printf 'step: %s\n' "$1" >&2; exit 1; }

git rev-parse --git-dir >/dev/null 2>&1 || errore "non sei dentro un repository git."

# Dentro un worktree collegato, --show-toplevel darebbe il worktree; a noi
# serve il checkout principale, che e' la cartella che contiene il git-dir
# comune. E' li' che vivono i cantieri.
comune="$(git rev-parse --path-format=absolute --git-common-dir)"
principale="$(dirname "$comune")"
cantieri="$principale/.claude/worktrees"

# Stampa "<ref> <percorso>" per ogni worktree che abbia un ramo estratto.
# Il ref viene PRIMA di proposito: cosi' i filtri si ancorano con ^ e non
# dipendono da un carattere di tabulazione dentro un'espressione regolare,
# che grep in modalita' base non interpreta.
worktree_e_rami () {
  git worktree list --porcelain \
    | awk '/^worktree /{w=substr($0,10)} /^branch /{print substr($0,8)" "w}'
}

progetto_del_ramo_di_step () {   # step/<prj>/<nome> -> <prj>
  local r="${1#step/}"; printf '%s' "${r%%/*}"
}

# ---------------------------------------------------------------- stato -----

cmd_stato () {
  printf 'Checkout principale: %s\n\n' "$principale"

  printf 'Cantieri aperti:\n'
  local righe ref percorso ramo prj avanti
  righe="$(worktree_e_rami | grep '^refs/heads/step/' || true)"
  if [ -z "$righe" ]; then
    printf '  nessun cantiere aperto.\n'
  else
    while read -r ref percorso; do
      ramo="${ref#refs/heads/}"
      prj="$(progetto_del_ramo_di_step "$ramo")"
      avanti="$(git rev-list --count "feature/$prj..$ramo" 2>/dev/null || echo '?')"
      printf '  %-36s %s (%s commit da portare)\n' "$ramo" "$percorso" "$avanti"
    done <<< "$righe"
  fi

  printf '\nRami di feature, rispetto a develop:\n'
  local f conteggio indietro
  for f in $(git for-each-ref --format='%(refname:short)' 'refs/heads/feature/*'); do
    conteggio="$(git rev-list --left-right --count "develop...$f" 2>/dev/null || echo '0 0')"
    read -r indietro avanti <<< "$conteggio"
    if [ "$indietro" != "0" ]; then
      printf '  %-32s %s avanti, %s INDIETRO — da riallineare\n' "$f" "$avanti" "$indietro"
    else
      printf '  %-32s %s avanti\n' "$f" "$avanti"
    fi
  done
}

# ----------------------------------------------------------------- apri -----

cmd_apri () {
  local prj="${1:-}" nome="${2:-}"
  [ -n "$prj" ] && [ -n "$nome" ] || errore "uso: step.sh apri <progetto> <nome-step>"
  case "$nome" in
    *[!a-z0-9-]*) errore "il nome dello step va in minuscolo con trattini: '$nome' non lo è." ;;
  esac

  git show-ref --verify --quiet "refs/heads/feature/$prj" \
    || errore "il ramo feature/$prj non esiste. I progetti sono: $(git for-each-ref --format='%(refname:short)' 'refs/heads/feature/*' | sed 's|feature/||' | tr '\n' ' ')"

  # Se la feature fosse estratta, la chiusura in fast-forward verrebbe
  # rifiutata da git con codice 128. Meglio dirlo adesso che fra due ore.
  if worktree_e_rami | grep -q "^refs/heads/feature/$prj "; then
    errore "feature/$prj è estratta in un worktree. Finché lo è, la chiusura in fast-forward verrebbe rifiutata da git. Liberala, poi riprova."
  fi

  local aperto
  aperto="$(worktree_e_rami | grep "^refs/heads/step/$prj/" || true)"
  if [ -n "$aperto" ]; then
    errore "c'è già un cantiere aperto su $prj:
  $aperto
O ci sta lavorando un altro agent, o è il relitto di una sessione morta. La decisione è del proprietario: fermati e riferisci."
  fi

  git show-ref --verify --quiet "refs/heads/step/$prj/$nome" \
    && errore "il ramo step/$prj/$nome esiste già. Scegli un altro nome, oppure riprendi quel lavoro rientrando nel suo cantiere."

  local conteggio indietro avanti
  conteggio="$(git rev-list --left-right --count "develop...feature/$prj" 2>/dev/null || echo '0 0')"
  read -r indietro avanti <<< "$conteggio"
  if [ "$indietro" != "0" ]; then
    printf 'step: attenzione — feature/%s è %s commit indietro rispetto a develop.\n' "$prj" "$indietro" >&2
    printf '      Il riallineamento è del proprietario: segnalalo e prosegui.\n' >&2
  fi

  local dir="$cantieri/$prj--$nome"
  git worktree add -b "step/$prj/$nome" "$dir" "feature/$prj" >/dev/null \
    || errore "git worktree add è fallito."

  printf 'Cantiere aperto.\n  ramo:      step/%s/%s\n  cartella:  %s\n\n' "$prj" "$nome" "$dir"
  printf 'Ora entraci, e non con name: — con path:\n'
  printf '  EnterWorktree(path: ".claude/worktrees/%s--%s")\n' "$prj" "$nome"
}

# --------------------------------------------------------------- chiudi -----

cmd_chiudi () {
  local ramo
  ramo="$(git branch --show-current)"
  case "$ramo" in
    step/*) ;;
    *) errore "questo comando si esegue dentro un cantiere. Il ramo estratto qui è '$ramo', che non è uno step." ;;
  esac

  local prj nome
  prj="$(progetto_del_ramo_di_step "$ramo")"
  nome="${ramo##*/}"

  [ -z "$(git status --porcelain)" ] \
    || errore "ci sono modifiche non committate. Uno step si chiude con commit logici, non con un albero sporco:
$(git status --short)"

  local avanti
  avanti="$(git rev-list --count "feature/$prj..$ramo")"
  [ "$avanti" -gt 0 ] \
    || errore "non c'è niente da portare su feature/$prj. Se lo step è andato male non chiuderlo: riferiscilo, e aspetta il mandato di abbandonarlo."

  # Il codice di uscita di git fetch basta, ed e' preferibile a leggere il
  # messaggio, che e' localizzato: 0 se il fast-forward passa, 1 se lo
  # rifiuta, 128 se il ramo bersaglio e' estratto altrove.
  local esito=0
  git fetch . "$ramo:feature/$prj" >/dev/null 2>&1 || esito=$?
  case "$esito" in
    0) ;;
    1) errore "fast-forward rifiutato: feature/$prj si è mossa mentre lo step era aperto.
Il ramo è rimasto fermo, ed è la cosa giusta. NON inventare un merge: fermati e riferisci, perché o è saltata la regola di uno step alla volta, o qualcuno ha committato sulla feature da fuori." ;;
    *) errore "git ha rifiutato di avanzare feature/$prj (codice $esito). Il caso tipico è che il ramo sia estratto in un altro worktree: controlla con 'step.sh stato'." ;;
  esac

  [ "$(git rev-parse "feature/$prj")" = "$(git rev-parse "$ramo")" ] \
    || errore "feature/$prj non è arrivata al commit dello step. Fermati e riferisci."

  git push -q origin "feature/$prj" \
    || errore "il fast-forward locale è riuscito ma il push è fallito. Il lavoro è salvo in locale su feature/$prj: riprova il push, non rifare la chiusura."

  printf 'Step chiuso. %s commit portati su feature/%s in fast-forward, e spinti su origin.\n\n' "$avanti" "$prj"
  printf 'Restano due mosse, in questo ordine:\n'
  printf '  1. ExitWorktree(action: "keep")   <- keep, mai remove\n'
  printf '  2. step.sh smonta %s %s\n' "$prj" "$nome"
}

# ------------------------------------------------- smonta e abbandona -------

percorso_cantiere () {
  local dir="$cantieri/$1--$2"
  [ -d "$dir" ] || errore "il cantiere $1--$2 non esiste. Vedi 'step.sh stato'."
  case "$PWD/" in
    "$dir"/*) errore "sei dentro il cantiere che vuoi smontare. Prima ExitWorktree(action: \"keep\"), poi riprova da fuori." ;;
  esac
  printf '%s' "$dir"
}

cmd_smonta () {
  local prj="${1:-}" nome="${2:-}" dir ramo
  [ -n "$prj" ] && [ -n "$nome" ] || errore "uso: step.sh smonta <progetto> <nome-step>"
  ramo="step/$prj/$nome"
  dir="$(percorso_cantiere "$prj" "$nome")"

  # `git branch -d` verifica la fusione "in its upstream branch, or in HEAD if
  # no upstream was set". Un ramo di step non ha upstream — non viene mai
  # pushato — quindi ricade su HEAD, che nel checkout principale e' develop e
  # non feature/<prj>. Rifiuterebbe un ramo perfettamente fuso stampando "is
  # not fully merged", che sarebbe falso. L'ancestralita' si chiede
  # esplicitamente, e si distrugge solo dopo averla accertata: a quel punto -D
  # non e' una forzatura, e' la conseguenza di un controllo gia' fatto.
  git merge-base --is-ancestor "$ramo" "feature/$prj" \
    || errore "il ramo $ramo NON è fuso su feature/$prj: andrebbero perduti $(git rev-list --count "feature/$prj..$ramo") commit. Chiudi lo step con 'step.sh chiudi', oppure chiedi al proprietario il mandato di abbandonarlo."

  git worktree remove "$dir" \
    || errore "git worktree remove è fallito: nel cantiere ci sono file non committati. Se il lavoro va buttato serve 'step.sh abbandona', e il mandato del proprietario."
  git branch -D "$ramo" >/dev/null

  printf 'Smontato. Il ramo %s era fuso su feature/%s ed è stato cancellato.\n' "$ramo" "$prj"
}

cmd_abbandona () {
  local prj="${1:-}" nome="${2:-}" mandato="${3:-}" dir
  [ -n "$prj" ] && [ -n "$nome" ] || errore "uso: step.sh abbandona <progetto> <nome-step> --mandato"
  [ "$mandato" = "--mandato" ] || errore "l'abbandono distrugge il lavoro dello step ed è l'unica azione irreversibile dell'intero ciclo.
Non è una decisione dell'agent: la approva il proprietario. Ottenuta l'approvazione, ripeti con --mandato."

  dir="$(percorso_cantiere "$prj" "$nome")"
  local perduti
  perduti="$(git rev-list --count "feature/$prj..step/$prj/$nome" 2>/dev/null || echo 0)"

  git worktree remove --force "$dir" || errore "git worktree remove --force è fallito."
  git branch -D "step/$prj/$nome" >/dev/null

  printf 'Step abbandonato: %s commit distrutti. feature/%s non è stata toccata.\n' "$perduti" "$prj"
}

# ------------------------------------------------------------ smistamento ---

case "${1:-}" in
  stato)     shift; cmd_stato "$@" ;;
  apri)      shift; cmd_apri "$@" ;;
  chiudi)    shift; cmd_chiudi "$@" ;;
  smonta)    shift; cmd_smonta "$@" ;;
  abbandona) shift; cmd_abbandona "$@" ;;
  *) errore "uso: step.sh {stato | apri <prj> <nome> | chiudi | smonta <prj> <nome> | abbandona <prj> <nome> --mandato}" ;;
esac
