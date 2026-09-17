# Sequenze di comandi — quelle di questo repository

> [!CAUTION]
> **Qui ci sono solo le sequenze del repository d'origine.** Quelle di Git Flow originale —
> feature, release, hotfix, tag annotati, back-merge — stanno nella skill accanto,
> `.claude/skills/git-flow/references/comandi.md`, e **non vanno eseguite in questo repository**:
> si leggono per confronto, o si applicano a un repo diverso da questo.

I percorsi sono dalla radice del repository, con il case esatto: su Linux `Docs/` e `docs/` sono due
cartelle diverse.

```bash
step=.claude/skills/worktree-di-step/scripts/step.sh
chg=.claude/skills/changelog-di-chiusura/scripts/changelog.sh

# stato: chi lavora su cosa, chi e' indietro
$step stato

# aprire un lavoro (crea ramo step/<prj>/<nome> e il cantiere)
$step apri <progetto> <nome-step>
# poi EnterWorktree(path: ".claude/worktrees/<progetto>--<nome-step>")   <- mai name:

# ... lavoro, commit logici, percorsi espliciti (mai 'git add .') ...

# il racconto di che cosa e' cambiato, dal ramo della feature,
# nell'ultimo commit dello step insieme alla Memory
$chg feature <progetto> --scrivi

# chiudere: fast-forward sulla feature e push. Se rifiuta, ci si ferma
$step chiudi
# poi ExitWorktree(action: "keep")   <- keep, mai remove
$step smonta <progetto> <nome-step>
```

Quello che **non** c'è, e non è una dimenticanza:

| Gesto di Git Flow | Qui | Perché |
|---|---|---|
| `git merge --no-ff feature/… ` in `develop` | fast-forward | ADR-010, ADR-015 |
| `git branch -d feature/…` dopo la chiusura | il ramo resta finché il progetto vive | ADR-002 |
| `release/x.y.z` | non esiste: si valida sul ramo di feature | ADR-009 |
| `git tag -a vX.Y.Z` su `main` | istantanea con un commit per progetto archiviato | ADR-009 |
| `hotfix/…` da `main` | un progetto archiviato non si riapre: nasce una feature nuova | ADR-009 |

Per cancellare un ramo di step dopo la chiusura, l'ancestralità si accerta prima:

```bash
rtk git merge-base --is-ancestor step/<prj>/<nome> feature/<prj> && rtk git branch -D step/<prj>/<nome>
```

`-D` e non `-d`: `-d` verifica rispetto all'upstream o a `HEAD` e in questo flusso mente (ADR-015).

## L'archiviazione su `main`

Non è una release di Git Flow e non produce tag. La procedura sta in
[ADR-009](../../../../Docs/Decision.md#adr-009); il corpo del commit di istantanea e la sezione del
`CHANGELOG.md` di radice si generano dai commit:

```bash
$chg rilascio <progetto> <n>
$chg messaggio <progetto> <n>
```
