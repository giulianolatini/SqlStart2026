# GitHub Flow — sequenze di comandi

Prima di ogni sequenza: `git fetch --all --prune` e working tree pulito (`git status`).

## Iniziare un lavoro

```bash
git checkout main && git pull
git checkout -b feature/123-slug-descrittivo     # tipo/issue-slug
```

## Durante

```bash
git add -p                                        # staging selettivo: commit isolati
git commit                                        # messaggio secondo convenzione del repo
git push -u origin feature/123-slug-descrittivo   # presto e spesso
```

## Aprire la PR (presto, in draft)

```bash
gh pr create --draft --fill --base main           # --fill usa titolo/corpo dai commit
# oppure interattiva con template del repo:
gh pr create --base main
# quando è pronta per la review formale:
gh pr ready
```

## Tenere il branch allineato a main

```bash
git fetch origin
git rebase origin/main            # storia lineare (se il branch è solo tuo)
# oppure, convenzione alternativa:
git merge origin/main
git push --force-with-lease       # SOLO dopo rebase, SOLO sul proprio topic branch
```

## Merge (CI verde, review approvata)

```bash
gh pr checks                       # stato CI
gh pr merge --squash --delete-branch      # o --merge / --rebase secondo l'ADR del repo
# con merge queue attiva: il merge lo esegue la coda, tu accodi dalla piattaforma
git checkout main && git pull
```

## Rollback di una PR mergiata

```bash
gh pr view <numero> --json mergeCommit -q .mergeCommit.oid
git revert -m 1 <sha-del-merge>    # -m 1 solo se merge commit; con squash: git revert <sha>
# poi push su un branch e nuova PR di revert (mai push diretto su main)
# scorciatoia piattaforma: bottone "Revert" sulla PR, che apre la PR di revert
```

## Igiene dei branch

```bash
git branch --merged main           # candidati alla cancellazione locale
git branch -d nome-branch
git push origin --delete nome-branch
git fetch --prune
```
