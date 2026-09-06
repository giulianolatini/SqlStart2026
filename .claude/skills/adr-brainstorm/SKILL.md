---
name: adr-brainstorm
description: Guide a brainstorming conversation into a documented Architecture Decision Record with an explicit rationale, and manage the ADR lifecycle (numbering, status, superseding, index). Use whenever the user wants to record, discuss or revisit a technical or architectural decision — phrases like "registriamo questa decisione", "scriviamo un ADR", "meglio X o Y?", "perché avevamo scelto…?" — even when the word ADR never appears, and proactively whenever a significant design choice emerges in the middle of another task. In SqlStart2026 phase 4 is different: the record does NOT go to docs/adr/NNNN-slug.md, it goes into the single append-only register docs/Decision.md — hand that phase to the skill decision-md.
---

# ADR Brainstorm

> [!IMPORTANT]
> **In SqlStart2026: governa, tranne la fase 4.** Le fasi 0-3 valgono come sono scritte. La fase 4 no: qui le schede non stanno in `docs/adr/NNNN-slug.md` con un indice accanto, ma tutte dentro `docs/Decision.md`, in ordine cronologico, numerate a quattro cifre e con l'ancora `<a id="adr-NNNN"></a>` scritta a mano prima del titolo. La scheda **deve** chiudersi con `**Fonti:**`, altrimenti `make docs-check` fallisce. La forma esatta la sa la skill `decision-md`: arrivato alla scrittura, passale il lavoro.
>
> Il corpo qui sotto è quello del repository d'origine, intatto. In caso di conflitto fra
> questa skill e una scheda accettata di [`docs/Decision.md`](../../../docs/Decision.md),
> **vince la scheda**. La provenienza e le divergenze misurate stanno in
> [`concetti-generali/README.md`](../../../docs/06-sviluppo/concetti-generali/README.md).

Trasforma una conversazione di brainstorming in una decisione documentata con il suo razionale. L'architettura di un sistema è l'accumulo delle sue decisioni: questo skill serve a non perderle.

> [!IMPORTANT]
> **Qui questa skill conduce la conversazione; la forma del record la decide `decision-md`.** Nel
> repository d'origine gli ADR non stanno in `docs/adr/NNNN-slug.md` un file per decisione: stanno
> **tutti** in un unico `Docs/Decision.md`, con `Docs/Sources.md` accanto e un verificatore dei
> link incrociati. Le fasi 0–3 qui sotto valgono immutate — è il *come si arriva* alla decisione;
> la fase 4 è stata riscritta per questo repository.
>
> In caso di conflitto fra questa skill e una scheda accettata di `Docs/Decision.md`, vince la
> scheda. La versione originale, non adattata, si ripesca con
> `git show fdd70c5:.claude/skills/adr-brainstorm/SKILL.md`.

Lingua di lavoro: rispondi nella lingua dell'utente. Gli ADR di questo repository si scrivono in
**italiano**, come quelli già presenti.

## Fase 0 — Filtro di significatività

Prima di tutto chiediti: la decisione è *architetturalmente significativa*? Lo è se incide sulla struttura del sistema, su attributi di qualità chiave (prestazioni, sicurezza, manutenibilità, costi), o se è difficile/costosa da invertire. Esempi sì: SQL vs NoSQL, monolite vs microservizi, scelta del framework, strategia di autenticazione, convenzioni di processo del repo. Esempi no: rinominare una variabile, un fix locale, una preferenza di formattazione già coperta dal linter.

Se NON è significativa: dillo esplicitamente, proponi l'alternativa proporzionata (una riga nel body del commit o nella descrizione della PR) e fermati. Un registro pieno di micro-decisioni muore di burocrazia — l'evidenza empirica mostra che la maggior parte dei team abbandona gli ADR proprio così.

## Fase 1 — Elicitazione del contesto

Conduci il brainstorming con domande brevi, una alla volta, senza interrogatori. Devi arrivare a poter riempire:

- **Problema**: cosa stiamo cercando di risolvere, in una o due frasi.
- **Vincoli**: tecnici, di budget, di tempo, di competenze, normativi.
- **Decision driver**: i requisiti (funzionali e non) che pesano sulla scelta, in ordine di importanza.

Se il contesto è già emerso nella conversazione precedente, estrailo e riassumilo per conferma invece di richiederlo.

## Fase 2 — Opzioni

Enumera le opzioni considerate: minimo due, includendo "non fare nulla / status quo" quando è un'opzione reale. Per ciascuna: pro e contro rispetto ai decision driver, non in astratto. Se l'utente ha già una preferenza forte, esplora comunque almeno un'alternativa seria: un ADR con una sola opzione non documenta una decisione, documenta un fatto compiuto.

Se servono dati per confrontare le opzioni (benchmark, documentazione, esperienze di altri team), proponi di raccoglierli prima di decidere; una decisione a bassa confidenza si può comunque registrare, dichiarandola tale.

## Fase 3 — Decisione e razionale

Quando l'utente sceglie, fissa per iscritto:

- **La decisione**, assertiva e autosufficiente (comprensibile senza leggere altro).
- **Il razionale**: perché questa opzione vince rispetto ai driver; quali alternative sono state scartate e perché.
- **I trade-off accettati** consapevolmente (mai nasconderli: un record senza conseguenze negative è sospetto).
- **Il confidence level** (alto/medio/basso): dichiarare bassa confidenza è utile per sapere quando riconsiderare.

Per l'anatomia completa del razionale e gli errori tipici, leggi `references/razionale.md`.

## Fase 4 — Scrittura, nel formato di questo repository

**Invoca la skill `decision-md`**: definisce il formato ed è normativa. Quello che segue è il minimo
per non sbagliare la destinazione.

1. **Dove.** Una decisione che riguarda il repository va in `Docs/Decision.md`; una che riguarda un
   progetto va in `<progetto>/Docs/Decision.md`. Non si creano cartelle `docs/adr/`.
2. **Numerazione a tre cifre**, mai riusata e mai rinumerata: `ADR-NNN` = massimo esistente + 1, con
   l'ancora `<a id="adr-0NN"></a>` prima della scheda.
3. **Ordine cronologico** nel file, non tematico, e l'**Indice** in testa si aggiorna sempre.
4. **Stato in italiano**: `**Stato: accettata** (data, ora)` oppure
   `**Stato: superata da [ADR-NNN](#adr-nnn)**`. Non `Proposed`/`Accepted`.
5. **Le quattro parti**: `**Contesto.**` (che deve dire **qual era l'alternativa ovvia scartata**),
   `**Decisione.**`, `**Conseguenze.**` (con il **prezzo pagato** dichiarato: una scheda senza costi
   è quasi sempre scritta male), `**Fonti.**` — che non può mancare, nemmeno per dire che non ce ne
   sono: le formule ammesse sono `nessuna: decisione del committente`, `nessuna: scelta di metodo`,
   `nessuna: comportamento del prodotto, verificabile sul campo`.
6. **Il titolo è la decisione**, non il problema: «Tre selettori complementari invece di uno», non
   «Come filtrare gli eventi».
7. **Le fonti** consultate si registrano in `Docs/Sources.md` con la skill `sources-md`, numerate
   `SNN`, e ogni scheda dichiara `Sostiene:` le ADR che regge. I due file si citano a vicenda.

Prima del commit, sempre:

```bash
python3 .claude/skills/decision-md/scripts/check-crosslinks.py Docs
```

Verifica link nei due sensi, ancore, fonti orfane e numerazione contigua. Esce 1 se trova qualcosa.

I template in `assets/` restano utili per il **contenuto** — il sommario in stile *Y-statement*
(«Nel contesto di …, di fronte a …, abbiamo deciso … per ottenere …, accettando …»), i decision
driver, il confronto strutturato a 3+ opzioni di MADR — ma **non** per la forma del file: quella è
di `decision-md`. Il Y-statement, qui, diventa la prima frase del `**Contesto.**` o della
`**Decisione.**`.

## Ciclo di vita — regole non negoziabili

- Il registro è **append-only**: una scheda accettata non si modifica mai nel contenuto.
- Se una decisione cambia: scrivi una **nuova** scheda che la supera. Nella vecchia lo stato diventa
  `**Stato: superata da [ADR-NNN](#adr-nnn)**` e si aggiunge un paragrafo **Perché è stata superata**;
  la nuova dichiara `supera [ADR-MMM](#adr-mmm)`. Una decisione che è stata davvero in vigore spiega
  comportamenti del codice che altrimenti sembrano incoerenti: per questo non si cancella.
- Se una decisione ha fasi (breve/medio/lungo termine), una scheda per fase.
- Se l'utente chiede di "correggere" una scheda accettata, distingui: refuso o link rotto →
  correzione ok; cambiamento di sostanza → si supera.

## Quando riemergono decisioni passate

Se l'utente chiede "perché avevamo scelto…?" o propone qualcosa che contraddice una scheda esistente:
cerca prima in `Docs/Decision.md` e in `<progetto>/Docs/Decision.md`, cita la scheda pertinente, e
chiedi se il contesto è cambiato abbastanza da giustificare una nuova scheda che la superi. Mai
contraddire silenziosamente una decisione accettata.

## I percorsi si scrivono con il case esatto

Questo repository vive su macOS, dove il filesystem non distingue maiuscole e minuscole, ma può
essere clonato su Linux, dove le distingue. Scrivere `docs/adr/` su macOS **non** dà errore: il file
finisce dentro `Docs/`, ma git registra il percorso in minuscolo, e sulla macchina Linux successiva
compaiono due cartelle diverse. È esattamente il modo in cui un registro si sdoppia senza che nessuno
se ne accorga.

Si scrive `Docs/` e non `docs/`, `Docs/Decision.md` e `Docs/Sources.md` con le maiuscole,
`.claude/skills/` in minuscolo. `.github/` è minuscolo perché lo impone GitHub, ed è l'unica
eccezione. Vale per i percorsi che scrivi nei file **e** per quelli che passi a `git add`.

## Il costo in token

La fase piu' costosa non e' scrivere la scheda: e' cercare se la decisione esiste gia'. Per quella
ricerca — «perche' avevamo scelto…?», «questa contraddice qualcosa?» — si usa `tokensave_context` con
la domanda in italiano, non la lettura integrale di `Docs/Decision.md`, che supera i 50 KB.

Quando poi la scheda si scrive, si legge il file dal disco: l'indice non ha ancora visto le modifiche
della sessione. I comandi si prefissano con `rtk`.

Le regole per esteso — che cosa copre l'indice, che cosa no, e come si scavalca il hook quando
il server non risponde — stanno in «Il costo in token» di `CLAUDE.md`.
