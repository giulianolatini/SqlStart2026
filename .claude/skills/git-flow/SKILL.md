---
name: git-flow
description: Use when the repository in question is NOT SqlStart2026 and adopts (or should adopt) the original Git Flow branching model by Driessen — feature, release and hotfix branches with main/develop, correct merge directions, back-merges, annotated version tags. Use it to set up Git Flow elsewhere, or as the reference text when comparing branching models. SqlStart2026's own model has the shape of Git Flow but closes every branch with a reviewed pull request: `git flow feature finish` is FORBIDDEN here. Do not run this skill's commands against SqlStart2026.
---

# Git Flow

> [!IMPORTANT]
> **In SqlStart2026: è testo di riferimento, e i suoi comandi non si eseguono.** Il modello di questo repository **ha la forma** di Git Flow — `main`, `develop`, `feature/NN-nome`, `release/1.0` — e per questo la somiglianza inganna. La differenza che conta è la chiusura: qui un ramo si chiude con una **pull request rivista e unita dal Product Owner**, mai con `git flow feature finish`. Quel comando salta la revisione, ed è già successo una volta, sulla PR #1. Il file [`references/comandi.md`](references/comandi.md) lo elenca fra gli equivalenti AVH: è la riga da non copiare. La procedura vera sta in [`docs/06-sviluppo/worktree-e-branch-di-lavoro.md`](../../../docs/06-sviluppo/worktree-e-branch-di-lavoro.md).
>
> Il corpo qui sotto è quello del repository d'origine, intatto. In caso di conflitto fra
> questa skill e una scheda accettata di [`docs/Decision.md`](../../../docs/Decision.md),
> **vince la scheda**. La provenienza e le divergenze misurate stanno in
> [`concetti-generali/README.md`](../../../docs/06-sviluppo/concetti-generali/README.md).

> [!IMPORTANT]
> **Nel repository d'origine questo modello non si applica**, e il testo qui sotto è tenuto
> **volutamente intatto** proprio per questo: è Git Flow originale, e serve come riferimento
> quando il repository di destinazione è un altro. La politica dei rami di questo repository è
> quella della skill `modello-dei-rami`, per decisione del proprietario registrata in
> [ADR-026](../../../Docs/Decision.md#adr-026).
>
> Le differenze non sono di dettaglio: `develop` **esiste** anche qui, ma i rami di feature vivono
> quanto il progetto e rientrano in **fast-forward**; `main` è un archivio di istantanee, senza tag
> di versione; `release/…` e `hotfix/…` non esistono affatto. Eseguire le sequenze qui sotto in
> questo repository rompe l'invariante di ADR-002. Le quattro divergenze sono nella tabella di
> `modello-dei-rami`, e le schede che le fissano sono ADR-002, ADR-009, ADR-010, ADR-015.

Rendi operativo e ripetibile il modello Git Flow: due branch permanenti (`main` = produzione, `develop` = integrazione) e tre tipi di branch di supporto con origini e destinazioni fisse. La disciplina del modello sta tutta nelle direzioni dei merge e nei back-merge: è lì che si concentrano gli errori, ed è lì che devi essere rigoroso.

Lingua: rispondi nella lingua dell'utente. Prima di ogni operazione leggi lo stato reale del repo, non assumerlo.

## Controlli preliminari (sempre, prima di qualsiasi operazione)

1. `git fetch --all --prune` e working tree pulito (`git status`): mai iniziare un'operazione di flusso con modifiche pendenti.
2. Rileva i nomi reali dei branch permanenti (`main` o `master`; `develop` esistente?) e lo schema di versione in uso (tag esistenti `git tag --sort=-v:refname | head`, file di versione, SemVer da Conventional Commits). Adattati ai nomi trovati.
3. Se `develop` non esiste: il repo non è (ancora) in Git Flow. Chiedi se inizializzare (vedi Init) o se il modello giusto sia un altro — non imporre Git Flow a un repo che fa continuous delivery su versione singola; in dubbio, apri la discussione di policy (skill `adr-brainstorm` se disponibile: la politica di branching è una decisione da ADR).
4. Identifica se il team integra via PR (branch policy attive) o via merge locale: preferisci sempre la variante via PR quando la piattaforma lo consente — le regole del modello restano identiche, cambia solo il gesto del merge.

## Operazioni

Le sequenze di comandi esatte (variante git puro, variante PR/`gh`, equivalenti `git flow` AVH) sono in `references/comandi.md`: leggilo prima di eseguire un'operazione che non hai già fatto in questa sessione.

### Init (una tantum)
Crea `develop` da `main` e pushalo; proponi di impostare `develop` come default branch della piattaforma e di proteggere entrambi i permanenti (PR obbligatoria, build verde). Registra l'adozione del modello come ADR.

### Feature
- **Start:** da `develop` aggiornato → `feature/<slug-descrittivo>`. Un branch = una feature; vita breve (giorni, non settimane).
- **Finish:** rientro in `develop` — via PR, oppure merge locale `--no-ff` (preserva la traccia del branch, coerente col modello originale). Poi cancella il branch. Mai far rientrare una feature direttamente in `main`.

### Release
- **Start:** quando `develop` contiene tutto ciò che entra nel rilascio → `release/x.y.z` da `develop`. Il numero di versione lo decide l'utente: proponi il bump coerente con i cambiamenti (SemVer) ma chiedi conferma esplicita, mai inventarlo. Da qui in poi sul release branch entrano solo stabilizzazione, fix e version bump — nessuna nuova feature (le feature nuove continuano su develop).
- **Finish:** (1) merge `--no-ff` in `main`; (2) tag **annotato** `vX.Y.Z` su main; (3) back-merge in `develop` per riportare i fix di stabilizzazione; (4) cancella il release branch. Il back-merge non è opzionale ed è il passo che i team dimenticano: eseguilo nella stessa sessione del rilascio.

### Hotfix
- **Start:** da `main` (la produzione rotta) → `hotfix/x.y.(z+1)`. Solo il fix minimo.
- **Finish:** (1) merge in `main` + tag annotato; (2) back-merge in `develop`; (3) **se esiste un release branch aperto, back-merge anche lì** — altrimenti la release in stabilizzazione uscirà senza il fix di produzione. Questo triplo rientro è l'errore classico del modello: verificalo esplicitamente con `git branch -r | grep release/`.

## Guardrail

- Mai commit diretti su `main` o `develop`; mai force-push su branch condivisi.
- Tag sempre annotati (`git tag -a`), sempre pushati (`git push --tags` o `--follow-tags`).
- Conflitti nei back-merge: risolvili subito, con l'utente, nel verso giusto (il fix di produzione vince, salvo diversa indicazione); non lasciare mai un back-merge "per dopo".
- Prima di operazioni distruttive o di rilascio (tag, merge in main) riepiloga cosa stai per fare e ottieni conferma.
- Se noti sintomi di disallineamento dal modello (feature partite da main, release senza tag, develop più indietro di main), segnalalo e proponi la riconciliazione prima di procedere.
- Rispetta le convenzioni già decise nel repo (ADR in `docs/adr/`, template, merge strategy): in caso di conflitto tra questo skill e un ADR accettato, vince l'ADR — e fallo notare.

## I percorsi si scrivono con il case esatto

Questo repository vive su macOS, dove il filesystem non distingue maiuscole e minuscole, ma può
essere clonato su Linux, dove le distingue. Un percorso scritto con il case sbagliato funziona sulla
prima macchina e crea **una seconda cartella** sulla seconda: git registra la stringa che gli hai
dato, non quella che il filesystem ti mostra.

L'ultimo guardrail qui sopra cita `docs/adr/` perché è la convenzione tipica di un repository
generico, ed è parte del testo originale. Nel repository d'origine le decisioni stanno in
`Docs/Decision.md`, con `Docs/Sources.md` accanto — con le maiuscole. `.claude/skills/` è
minuscolo; `.github/` è minuscolo perché lo impone GitHub, ed è l'unica eccezione.

## Il costo in token

Le sequenze qui sono volutamente **non** prefissate, perche' sono il testo originale e valgono per
repository che possono non avere RTK installato. Se il repository di destinazione ce l'ha, prefissa
ogni comando con `rtk` — `rtk git merge`, `rtk git tag`, `rtk gh pr create` — anche dentro le catene
con `&&`.

Nel repository d'origine non si esegue nulla di tutto questo: vedi il blocco in testa e la skill
`modello-dei-rami`.

Le regole per esteso — che cosa copre l'indice, che cosa no, e come si scavalca il hook quando
il server non risponde — stanno in «Il costo in token» di `CLAUDE.md`.
