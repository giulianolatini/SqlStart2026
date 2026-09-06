---
name: workflow-conventions
description: Bootstrap a repository's working conventions — merge strategy, commit message standard, branch naming, PR template, Definition of Done, review rules — through short guided decisions grounded in empirical evidence, and record every choice as an ADR. Use whenever someone sets up a NEW repository or has one with undocumented conventions. In SqlStart2026 the conventions are already in force and written: read the block at the top before proposing anything, and do not re-open decisions that the register already contains.
---

# Workflow Conventions

> [!IMPORTANT]
> **In SqlStart2026: non governa: le convenzioni ci sono già.** Questo repository lavora da fine agosto con convenzioni in vigore e scritte — messaggi di commit in italiano con prefisso convenzionale, rami `feature/NN-nome` da `develop`, chiusura per pull request rivista dal Product Owner, e una Definition of Done di fatto: `make docs-check` verde, le prove di `tools` e dell'applicazione verdi, e ogni affermazione tecnica con la sua fonte. Le sei decisioni di bootstrap qui **non si riaprono**. Il materiale in `references/evidenza.md` resta prezioso come argomento, non come proposta.
>
> Il corpo qui sotto è quello del repository d'origine, intatto. In caso di conflitto fra
> questa skill e una scheda accettata di [`docs/Decision.md`](../../../docs/Decision.md),
> **vince la scheda**. La provenienza e le divergenze misurate stanno in
> [`concetti-generali/README.md`](../../../docs/06-sviluppo/concetti-generali/README.md).

> [!IMPORTANT]
> **Nel repository d'origine quattro delle sei decisioni sono già prese**, e riaprirle non è il
> compito di questa skill: sono schede accettate di `Docs/Decision.md`, e in caso di conflitto
> vince la scheda.
>
> | Decisione | Qui è già | Scheda |
> |---|---|---|
> | 1. Merge strategy | fast-forward, mai `--no-ff`, mai squash | ADR-010, ADR-015 |
> | 2. Messaggi di commit | Conventional Commits, soggetto in italiano minuscolo, scope = nome esatto della cartella di progetto | ADR-018, ADR-019 |
> | 3. Branch naming | `feature/<progetto>` uno a uno col progetto, `step/<prj>/<n>` sotto | ADR-002, ADR-026 |
> | 5. Convenzioni di review | due revisori esterni che propongono, verdetto di chi conduce, tre esiti | ADR-021, ADR-023 |
>
> Restano davvero aperte la **4 (template di PR)** e la **6 (Definition of Done)**. E gli ADR si
> scrivono in `Docs/Decision.md` con la skill `decision-md`, non in `docs/adr/`: un file per
> decisione qui non esiste ([ADR-025](../../../Docs/Decision.md#adr-025)).
>
> La versione originale, non adattata, si ripesca con
> `rtk git show fdd70c5:.claude/skills/workflow-conventions/SKILL.md`.

Guida la definizione delle convenzioni operative di un repository e le trasforma in artefatti concreti + ADR. Le convenzioni non scritte non esistono: questo skill le rende esplicite, motivate e versionate.

Principio di funzionamento: ogni convenzione è una **decisione** — quindi ogni scelta va registrata come ADR con il suo razionale. Se lo skill `adr-brainstorm` è disponibile, usalo per condurre e registrare ogni decisione; altrimenti applica direttamente i template in `assets/` di quello skill o un template Nygard minimale (Contesto / Decisione / Conseguenze, stato, data).

Prima di proporre qualsiasi cosa, ispeziona il repo: convenzioni già in uso (log dei commit, PR passate, file `.github/`, `CONTRIBUTING.md`, il registro delle decisioni — qui `Docs/Decision.md`, altrove tipicamente `docs/adr/`), linguaggi e tooling presenti. Le convenzioni si adattano al repo, non viceversa. In un repo esistente, la prima proposta è sempre "formalizzare ciò che già funziona", non stravolgerlo.

## Le sei decisioni, in ordine

Conduci le decisioni una alla volta, in questo ordine (le prime vincolano le successive). Per ogni decisione presenta le opzioni con trade-off, ancora i pro/contro all'evidenza in `references/evidenza.md` (leggilo prima di iniziare), lascia scegliere l'utente, registra l'ADR.

### 1. Merge strategy (vincola la politica di commit)

Opzioni: squash merge (main lineare, un commit per PR; i commit intermedi sono liberi ma il messaggio finale va curato) · merge commit (storia fedele; richiede commit atomici e curati nel branch) · rebase (lineare conservando i commit; richiede commit atomici). Punti chiave: la scelta determina *dove* si applica lo standard dei messaggi; squash sconsigliato su branch a vita lunga.

### 2. Standard dei messaggi di commit

Opzioni: Conventional Commits (`type(scope): description`; abilita changelog e SemVer automatici; proponi commitlint solo se esiste già una pipeline Node/CI dove innestarlo) · regola 50/72 semplice (subject imperativo ≤50, body a 72 con il *perché*) · Conventional Commits solo sul messaggio di squash (compromesso comune con la strategy 1=squash).

### 3. Branch naming e protezione

Convenzione di naming (`feature/…`, `fix/…`, `hotfix/…`, eventuale `users/nome/…`) e regole del branch protetto: PR obbligatoria, build verde, numero di approvazioni (due reviewer è l'ottimo misurato; in un team di una persona + AI: una review umana del lavoro dell'agente, o viceversa). Genera la checklist dei comandi `gh` per applicare la protezione solo se l'utente la chiede.

### 4. Template di PR

Genera `.github/pull_request_template.md` partendo da `assets/pull_request_template.md`: cosa cambia / perché / come verificarlo + checklist derivata dalla DoD (decisione 6 — se non ancora presa, lascia un segnaposto e torna ad aggiornare il template dopo). Dimensione target delle PR: dichiara nel template il limite indicativo scelto (default suggerito: ~200–400 righe modificate; oltre, valutare lo split o uno stack).

### 5. Convenzioni di review

Severità dei commenti: prefisso informale `Nit:` oppure tassonomia Conventional Comments (`issue:`, `suggestion:`, `nitpick:`, `question:`… con `(blocking)`/`(non-blocking)`). Regole di ingaggio: l'autore risponde a ogni commento; i suggerimenti fuori scope diventano issue, non allargano la PR; tempi di risposta attesi.

### 6. Definition of Done (e Definition of Ready se si lavora a iterazioni)

Genera la Definition of Done partendo da `assets/definition_of_done.md`, adattata allo stack del repo (test, lint, build, docs, review). Il percorso dipende dal repository: qui è `Docs/DEFINITION_OF_DONE.md`, con `Docs/` maiuscolo — vedi in fondo — altrove tipicamente `docs/`. La DoD è unica per tutto il lavoro; la DoR si aggiunge solo se il progetto usa un backlog a iterazioni.

## Output finale

Al termine produci sempre:

1. Gli ADR nel registro del repository. **Qui**: schede in `Docs/Decision.md` con la skill
   `decision-md` — numerazione a tre cifre, `**Stato: accettata**` in italiano, blocco `**Fonti.**`
   obbligatorio, indice aggiornato, e `python3 .claude/skills/decision-md/scripts/check-crosslinks.py Docs`
   prima del commit. **Altrove**: `docs/adr/NNNN-slug.md`, un file per decisione, con indice.
2. Gli artefatti: `.github/pull_request_template.md` (`.github/` è minuscolo perché lo impone
   GitHub), la Definition of Done nel percorso del repo, eventuale config commitlint.
3. Un riepilogo in chat: decisioni prese, trade-off accettati, cosa resta da decidere.
4. Se il repo ha un `CLAUDE.md` (o `AGENTS.md`), proponi di aggiungervi un puntatore alle convenzioni
   e al registro delle decisioni. Nel repository d'origine il puntatore c'è già e `CLAUDE.md` è la
   sede della regola: non duplicarlo, semmai aggiornalo.

Non imporre tutte e sei le decisioni in una sessione: se l'utente vuole solo la merge strategy, fai quella (con ADR) ed elenca le altre come passi futuri. Meglio due convenzioni vive che sei imposte.

## I percorsi si scrivono con il case esatto

Questo repository vive su macOS, dove il filesystem non distingue maiuscole e minuscole, ma può
essere clonato su Linux, dove le distingue. Generare `docs/DEFINITION_OF_DONE.md` su macOS **non** dà
errore — il file finisce dentro `Docs/` — ma git registra la stringa in minuscolo, e sulla macchina
Linux successiva compaiono due cartelle. È il modo tipico in cui gli artefatti di questa skill si
sdoppiano senza che nessuno se ne accorga ([ADR-027](../../../Docs/Decision.md#adr-027)).

Si scrive `Docs/` e non `docs/`, `Docs/Decision.md` e `Docs/DEFINITION_OF_DONE.md` con le maiuscole,
`.claude/skills/` in minuscolo. `.github/` è minuscolo perché lo impone GitHub, ed è l'unica
eccezione — e vale per il percorso che passi a `git add`, non solo per quello che scrivi nel file.

## Il costo in token

Il primo passo di questa skill è ispezionare il repository, ed è il più caro se fatto leggendo tutto.
Si parte da `tokensave_context` con la domanda in italiano — «quali convenzioni sono già decise?» —
e solo dopo si aprono i file, per intervallo di righe. `Docs/Decision.md` supera i 50 KB.

I comandi si prefissano con `rtk`: `rtk git log` per guardare come sono scritti i commit esistenti,
`rtk gh pr view` per una PR passata, `rtk grep` per cercare una convenzione. Il filtro c'è o il
comando passa inalterato, quindi prefissare non è mai sbagliato.

Le regole per esteso — che cosa copre l'indice, che cosa no, e come si scavalca il hook quando
il server non risponde — stanno in «Il costo in token» di `CLAUDE.md`.
