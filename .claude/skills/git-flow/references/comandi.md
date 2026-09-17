# Git Flow — sequenze di comandi

> [!CAUTION]
> **Nessuna di queste sequenze va eseguita nel repository d'origine.** Sono il modello originale,
> e valgono per un repository diverso da questo. Le sequenze reali di qui sono in
> `.claude/skills/modello-dei-rami/references/comandi.md`, e passano tutte da `step.sh`.

Sostituisci i nomi dei branch permanenti con quelli reali del repo. Prima di ogni sequenza: `git fetch --all --prune` e working tree pulito.

## Init

```bash
git checkout main && git pull
git checkout -b develop
git push -u origin develop
# poi, sulla piattaforma: default branch = develop; protezione su main e develop
```

## Feature

```bash
# start
git checkout develop && git pull
git checkout -b feature/slug-descrittivo

# finish — variante PR (preferita se le branch policy sono attive)
git push -u origin feature/slug-descrittivo
gh pr create --base develop --fill        # review, CI, poi merge dalla piattaforma
git checkout develop && git pull
git branch -d feature/slug-descrittivo

# finish — variante merge locale (modello originale)
git checkout develop && git pull
git merge --no-ff feature/slug-descrittivo
git push origin develop
git branch -d feature/slug-descrittivo && git push origin --delete feature/slug-descrittivo
```

## Release

```bash
# start (versione confermata dall'utente)
git checkout develop && git pull
git checkout -b release/1.2.0
# ... version bump, fix di stabilizzazione, CHANGELOG ...
git push -u origin release/1.2.0

# finish
git checkout main && git pull
git merge --no-ff release/1.2.0
git tag -a v1.2.0 -m "Release 1.2.0"
git push origin main --follow-tags
git checkout develop && git pull
git merge --no-ff release/1.2.0          # back-merge: NON opzionale
git push origin develop
git branch -d release/1.2.0 && git push origin --delete release/1.2.0
```

## Hotfix

```bash
# start
git checkout main && git pull
git checkout -b hotfix/1.2.1
# ... fix minimo + bump patch ...

# finish
git checkout main
git merge --no-ff hotfix/1.2.1
git tag -a v1.2.1 -m "Hotfix 1.2.1"
git push origin main --follow-tags
git checkout develop && git pull
git merge --no-ff hotfix/1.2.1           # back-merge in develop
git push origin develop
git branch -r | grep origin/release/ || true   # se esiste una release aperta:
# git checkout release/X.Y.Z && git merge --no-ff hotfix/1.2.1 && git push
git branch -d hotfix/1.2.1 && git push origin --delete hotfix/1.2.1
```

## Equivalenti con l'estensione git-flow (AVH edition)

Solo se l'utente la usa già (`git flow version` risponde). Config standard: `git flow init -d`.

```bash
git flow feature start slug   |  git flow feature finish slug
git flow release start 1.2.0  |  git flow release finish 1.2.0   # fa merge+tag+back-merge
git flow hotfix start 1.2.1   |  git flow hotfix finish 1.2.1
```

Attenzione: `finish` dell'estensione esegue merge locali — poi serve comunque il push di main, develop e dei tag. Il back-merge dell'hotfix in un release branch aperto resta manuale.
