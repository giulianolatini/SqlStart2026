---
name: github-flow
description: Use when the repository in question is NOT the origin one and needs a branching model — a repo with a single main branch and no develop, where work happens on short-lived branches merged via pull request. Use also when comparing branching models, when someone mentions "github flow", "trunk based", "deploy da main", or when deciding which model a new repository should adopt. In the origin repository itself the model is a different one: see the skill modello-dei-rami.
---

# GitHub Flow

> [!IMPORTANT]
> **Nel repository d'origine questo modello non si applica**, e la ragione è strutturale: qui esiste
> `develop`, `main` è un archivio di istantanee e non una linea deployabile, e i rami di feature
> vivono quanto il progetto invece che pochi giorni. Il modello di questo repo è nella skill
> `modello-dei-rami`, e le sue regole stanno in `Docs/Decision.md` (ADR-002, ADR-009, ADR-010).
>
> Questa skill resta perché il proprietario lavora anche su repository che GitHub Flow lo usano
> davvero, e perché serve a confrontare i modelli quando se ne sceglie uno per un repo nuovo.

Rendi operativo e ripetibile GitHub Flow: un solo branch permanente — `main`, sempre deployable — e branch descrittivi a vita breve che rientrano via pull request. Tutta la sicurezza del modello poggia su due pilastri: la protezione di `main` (PR obbligatoria + CI verde) e la brevità dei branch. Il tuo lavoro è difendere questi due pilastri.

Lingua: rispondi nella lingua dell'utente. Le sequenze di comandi esatte (git + `gh` CLI) sono in `references/comandi.md`: leggilo prima di eseguire un'operazione che non hai già fatto in questa sessione.

## Le sei mosse

1. **Branch.** Da `main` aggiornato, crea un branch con nome breve e descrittivo (`tipo/slug`, es. `fix/timeout-export`, `feature/filtro-piva`; includi il numero della issue se esiste: `feature/123-filtro-piva`). Il nome comunica il lavoro in corso: chiunque legga l'elenco dei branch deve capire cosa sta succedendo.
2. **Commit e push regolari.** Messaggi curati secondo la convenzione del repo (Conventional Commits o 50/72; controlla gli ADR e il log). Idealmente ogni commit è un cambiamento isolato e completo — rende i revert chirurgici. Pusha presto e spesso: il branch remoto è anche il backup.
3. **PR presto, anche draft.** Apri la PR appena il lavoro ha una forma, in draft se non è pronto per la review formale: la conversazione parte prima e i CODEOWNERS non vengono notificati finché non dichiari la PR pronta. Descrizione secondo il template del repo (cosa cambia / perché / come verificarlo).
4. **Review e iterazione.** Rispondi a ogni commento: accogli o motiva. I suggerimenti buoni ma fuori scope diventano issue nuove, non allargano la PR.
5. **CI verde, poi merge.** `main` è sempre deployable: niente entra senza build e test verdi. Usa la merge strategy decisa nel repo (ADR; in assenza di decisione, proponi squash e suggerisci di registrare la scelta). Con merge queue attiva, accodala e lascia fare alla coda.
6. **Cancella il branch e verifica il deploy.** Il branch mergiato si cancella subito — i branch morti sono rumore. Se il repo fa continuous deployment, verifica che il deploy da main sia andato a buon fine prima di considerare chiuso il lavoro.

## Guardrail

- **Dimensione.** Target PR: sotto le ~400 righe modificate (limite del repo se un ADR ne fissa uno). Se il lavoro cresce oltre: fermati e proponi lo split — più PR sequenziali o uno stack. Mai "finire tanto ormai".
- **Durata.** Un branch vive giorni, non settimane. Se un branch invecchia: riallinealo a `main` subito (`git pull --rebase origin main` o merge di main nel branch, secondo la convenzione del repo) e spingi a chiudere o spezzare.
- **Mai commit diretti su `main`**, nemmeno per "una riga": tutto passa dalla PR. Se la protezione non è configurata, segnalalo e proponi di attivarla (è il presupposto del modello, non un optional).
- **Rollback = revert della PR** (nuova PR che annulla), non force-push né reset di main.
- **Lavoro incompleto** che deve arrivare su main (integrazione continua di feature lunghe): proponi feature flag, non branch a vita lunga.

## Quando il modello non basta

Se emergono richieste che GitHub Flow non copre nativamente — supportare più versioni in produzione, congelare una release per stabilizzazione/QA, hotfix su una versione vecchia — non improvvisare: segnala che è un limite noto del modello e apri la discussione di policy (release branch in stile GitLab Flow/Release Flow, oppure Git Flow — la skill `git-flow` ne conserva il testo originale, e `modello-dei-rami` mostra come il repository d'origine se ne discosta). La scelta della politica di branching è una decisione da registrare come ADR (skill `adr-brainstorm`). In caso di conflitto tra questo skill e un ADR accettato del repo, vince l'ADR — e fallo notare.

## I percorsi si scrivono con il case esatto

Questo repository vive su macOS, dove il filesystem non distingue maiuscole e minuscole, ma può
essere clonato su Linux, dove le distingue. Un percorso scritto con il case sbagliato funziona sulla
prima macchina e crea **una seconda cartella** sulla seconda — e git registra la stringa che gli hai
dato, non quella che il filesystem ti mostra.

Si scrive `Docs/` e non `docs/`, `Docs/Decision.md` e non `DECISION.md`, `.claude/skills/` in
minuscolo. `.github/` è minuscolo perché lo impone GitHub, ed è l'unica eccezione.

## Il costo in token

Le sequenze qui non sono prefissate perche' valgono per repository diversi da questo, dove RTK puo'
non esserci. Dove c'e', ogni comando si prefissa con `rtk`: `rtk git push`, `rtk gh pr create`,
`rtk gh pr checks` — quest'ultimo taglia circa l'80% dell'output.

Le regole per esteso — che cosa copre l'indice, che cosa no, e come si scavalca il hook quando
il server non risponde — stanno in «Il costo in token» di `CLAUDE.md`.
