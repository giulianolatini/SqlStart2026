# Runbook: Installazione e collaudo delle skill di flusso di lavoro

**Owner:** Giuliano | **Frequenza:** una tantum per macchina (installazione personale) o per repository (installazione di progetto)
**Ultimo aggiornamento:** 2026-09-06 | **Ultima esecuzione:** 2026-09-06 (installazione di progetto in SqlStart2026)

> [!NOTE]
> **Documento importato.** Viene dal repository d'origine, ramo
> `step/azure-policy/allineamento-e-fase-1`, ripreso il 6 settembre 2026. I numeri di ADR
> che cita — ADR-025, ADR-026, ADR-027, ADR-028 — sono del registro **di quel**
> repository, non di [`docs/Decision.md`](../../Decision.md) che qui arriva a ADR-0122:
> per questo sono scritti in grassetto e non come collegamenti, che sarebbero rotti. La
> provenienza, e in che cosa questo materiale diverge dalla pratica di qui, stanno in
> [`README.md`](README.md).

## Scopo

Installare in Claude Code le quattro skill che rendono ripetibile la procedura "dal brainstorming all'ADR reale" e la scelta della politica dei rami, definite nel documento *Dall'idea al software funzionante*, verificarne l'attivazione e collaudarle riproducendo l'ADR di esempio `esempio-adr-0001.md`. Al termine, ogni sessione di Claude Code saprà condurre decisioni architetturali documentate, impostare le convenzioni di un repository come primi ADR e scegliere con cognizione fra i modelli di branching.

Le quattro skill sono `adr-brainstorm`, `workflow-conventions`, `git-flow` e `github-flow`. Se il repository di destinazione è **quello d'origine**, la procedura è diversa e più corta: salta alla sezione «Il caso del repository d'origine», perché lì le skill sono già installate, personalizzate, e due di esse non governano nulla.

## Le skill in sintesi

### `adr-brainstorm` — dal brainstorming all'Architecture Decision Record

*Cosa fa:* guida una conversazione decisionale in cinque fasi — filtro di significatività (con facoltà di dire "questa decisione non merita un ADR"), elicitazione del contesto e dei decision driver, enumerazione delle opzioni con pro/contro, decisione con razionale, trade-off e confidence level, scrittura del record in `docs/adr/NNNN-slug.md` con indice aggiornato. Applica le regole di ciclo di vita: registro append-only, stati Proposed → Accepted → Superseded, superseding con link incrociati, approvazione via PR. Si attiva anche proattivamente quando una scelta significativa emerge durante un altro task o quando una proposta contraddice un ADR esistente.

*Contenuto del pacchetto:*

| File | Ruolo |
|------|-------|
| `SKILL.md` | Flusso in cinque fasi + regole di ciclo di vita |
| `references/razionale.md` | Anatomia del razionale, errori tipici, fonti ed evidenza empirica |
| `assets/template-nygard.md` | Template di default (4 sezioni + Y-statement) |
| `assets/template-madr.md` | Template per confronti strutturati a 3+ opzioni |

### `workflow-conventions` — le convenzioni del repo come primi ADR

*Cosa fa:* conduce le sei decisioni di bootstrap di un repository — merge strategy, standard dei messaggi di commit, branch naming e protezione, template di PR, convenzioni di review, Definition of Done — una alla volta, ancorando i trade-off all'evidenza empirica raccolta nel documento v2. Ogni scelta viene registrata come ADR (delegando ad `adr-brainstorm` se installata) e produce gli artefatti concreti: `.github/pull_request_template.md`, `docs/DEFINITION_OF_DONE.md`, eventuale configurazione commitlint. In un repo esistente parte sempre dal formalizzare ciò che già funziona.

*Contenuto del pacchetto:*

| File | Ruolo |
|------|-------|
| `SKILL.md` | Le sei decisioni guidate + output finale |
| `references/evidenza.md` | Numeri e fonti per ancorare i pro/contro (PR size, SmartBear, DORA, tangled commits…) |
| `assets/pull_request_template.md` | Scheletro del template di PR (cosa/perché/come verificare + checklist DoD) |
| `assets/definition_of_done.md` | Scheletro della Definition of Done da adattare allo stack |

### `git-flow` — il modello a due branch permanenti

*Cosa fa:* rende operativo e ripetibile Git Flow nella forma originale di Driessen — `main` di produzione e `develop` di integrazione, più i tre branch di supporto (feature, release, hotfix) con origini e destinazioni fisse. Il valore della skill sta nei back-merge: sono il passo che i team dimenticano, e la skill lo verifica esplicitamente, incluso il rientro di un hotfix in un release branch aperto. Si attiva per aprire o chiudere una release, per un hotfix, o per controllare che i branch rispettino il modello.

*Contenuto del pacchetto:*

| File | Ruolo |
|------|-------|
| `SKILL.md` | Controlli preliminari, le tre operazioni, guardrail |
| `references/comandi.md` | Sequenze esatte: git puro, variante PR con `gh`, equivalenti `git flow` AVH |

### `github-flow` — il modello a un solo branch permanente

*Cosa fa:* rende operativo GitHub Flow — un solo `main`, sempre deployable, e branch a vita breve che rientrano via pull request. Le sei mosse (branch, commit, PR presto anche in draft, review, CI verde, merge e cancellazione) più i due guardrail su cui poggia tutto: dimensione della PR e durata del branch. Dice anche quando il modello **non** basta — più versioni in produzione, release da congelare, hotfix su una versione vecchia — invece di improvvisare.

*Contenuto del pacchetto:*

| File | Ruolo |
|------|-------|
| `SKILL.md` | Le sei mosse, i guardrail, i limiti noti del modello |
| `references/comandi.md` | Sequenze con `git` e `gh`, incluse merge queue e revert |

Le due skill di branching sono alternative fra loro: si sceglie il modello, e la scelta è essa stessa una decisione da registrare come ADR. `github-flow` e `git-flow` si rimandano a vicenda proprio su questo punto.

## Prerequisiti

- [ ] Claude Code installato e funzionante (`claude --version` risponde)
- [ ] I quattro file `adr-brainstorm.skill`, `workflow-conventions.skill`, `git-flow.skill` e `github-flow.skill` scaricati da questa conversazione (es. in `~/Downloads/`)
- [ ] `unzip` disponibile (i file `.skill` sono archivi zip)
- [ ] Decisione presa: installazione **personale** (`~/.claude/skills/`, disponibile su tutti i progetti — consigliata per il tuo caso) oppure **di progetto** (`.claude/skills/` nel repo, versionata con il codice e condivisa via Git)

## Procedura

### Step 1: Creare la directory delle skill personali

```bash
mkdir -p ~/.claude/skills
```

**Risultato atteso:** la directory esiste (nessun output; `ls -d ~/.claude/skills` la mostra).
**Se fallisce:** verifica i permessi sulla home; su Windows usa `C:\Users\<utente>\.claude\skills`.

### Step 2: Estrarre le skill nella directory

```bash
cd ~/Downloads
unzip -o adr-brainstorm.skill -d ~/.claude/skills/
unzip -o workflow-conventions.skill -d ~/.claude/skills/
unzip -o git-flow.skill -d ~/.claude/skills/
unzip -o github-flow.skill -d ~/.claude/skills/
```

**Risultato atteso:** gli archivi contengono già la cartella con il nome della skill, quindi si creano quattro cartelle sotto `~/.claude/skills/`, ciascuna con `SKILL.md` al primo livello:

```
~/.claude/skills/
├── adr-brainstorm/
│   ├── SKILL.md
│   ├── references/razionale.md
│   └── assets/ (template-nygard.md, template-madr.md)
├── workflow-conventions/
│   ├── SKILL.md
│   ├── references/evidenza.md
│   └── assets/ (pull_request_template.md, definition_of_done.md)
├── git-flow/
│   ├── SKILL.md
│   └── references/comandi.md
└── github-flow/
    ├── SKILL.md
    └── references/comandi.md
```

**Se fallisce:** se `unzip` non trova i file, verifica il percorso di download; se compare una cartella doppia (`adr-brainstorm/adr-brainstorm/SKILL.md`), sposta la cartella interna un livello sopra e rimuovi quella vuota.

*Variante — installazione di progetto:* stessi comandi con destinazione `<repo>/.claude/skills/`; poi committa la cartella, così le convenzioni viaggiano col repository.

### Step 3: Verificare la struttura

```bash
for s in adr-brainstorm workflow-conventions git-flow github-flow; do head -3 ~/.claude/skills/$s/SKILL.md; done
```

**Risultato atteso:** ogni file inizia con il frontmatter YAML (`---` seguito dalla riga `name:` con il nome della skill, che deve coincidere con quello della cartella).
**Se fallisce:** file mancante o troncato → ripeti lo Step 2; frontmatter assente → l'archivio è corrotto, riscaricalo.

### Step 4: Avviare una nuova sessione di Claude Code

```bash
cd <un-repo-qualsiasi>
claude
```

**Risultato atteso:** la sessione parte. Le skill sono scoperte automaticamente all'avvio della sessione: quelle installate a sessione già aperta non vengono viste — serve una sessione nuova.
**Se fallisce:** vedi Troubleshooting.

### Step 5: Verifica di attivazione

Nella sessione, digita il comando esplicito della skill (il nome del comando deriva dal nome della directory):

```
/adr-brainstorm
```

oppure chiedi in linguaggio naturale: `Quali skill hai a disposizione per gli ADR?`

**Risultato atteso:** Claude riconosce la skill e descrive il flusso in cinque fasi (o la elenca tra le skill disponibili).
**Se fallisce:** vedi Troubleshooting, sintomo "la skill non si attiva".

## Collaudo con l'Esempio ADR-0001

Il collaudo riproduce il test di accettazione già eseguito in fase di creazione: il file `esempio-adr-0001.md` (consegnato insieme alle skill) è l'output di riferimento.

### Step C1: Preparare un repo di prova

```bash
mkdir -p /tmp/collaudo-adr && cd /tmp/collaudo-adr && git init -q
claude
```

### Step C2: Prompt di collaudo per `adr-brainstorm`

Incolla nella sessione:

```
Dobbiamo decidere la merge strategy del repo: squash, merge commit o rebase.
Lavoro da solo con il tuo supporto via Claude Code, le PR sono piccole e voglio
una main leggibile. Registriamo la decisione.
```

**Risultato atteso (criteri di accettazione, confronta con `esempio-adr-0001.md`):**

- [ ] La skill si attiva senza doverla nominare (il prompt non contiene la parola "ADR" nel comando)
- [ ] Fase 0 superata: la decisione è riconosciuta come significativa
- [ ] Vengono poste poche domande di contesto mirate (non un interrogatorio) e proposte le tre opzioni con trade-off ancorati ai driver, inclusa l'avvertenza sullo squash dei branch a vita lunga
- [ ] Alla scelta, viene creato `docs/adr/0001-<slug>.md` con: riga Y-statement in apertura; campi Stato (`Proposed`), Data, Decisori, Confidence con condizione di rivalutazione; sezione Contesto con i decision driver; sezione Decisione con le alternative scartate e il perché; sezione Conseguenze con trade-off dichiarati (non solo positivi)
- [ ] Viene creato/aggiornato l'indice `docs/adr/README.md` con la riga della decisione
- [ ] Lo stato resta `Proposed` finché non confermi esplicitamente l'accettazione

**Se fallisce:** confronta punto per punto con `esempio-adr-0001.md` e annota gli scostamenti nella History di questo runbook; per correzioni al comportamento, modifica direttamente `~/.claude/skills/adr-brainstorm/SKILL.md` (o riporta il problema nella WebUI per iterare sulla skill).

### Step C3 (opzionale): Collaudo di `workflow-conventions`

Nello stesso repo di prova:

```
Definiamo le convenzioni di questo repo.
```

**Risultato atteso:** la skill ispeziona il repo, propone le sei decisioni una alla volta partendo dalla merge strategy (riusando l'ADR-0001 se già presente invece di ridiscuterlo), cita l'evidenza empirica nei pro/contro, e al termine delle decisioni affrontate produce ADR numerati + `.github/pull_request_template.md` + `docs/DEFINITION_OF_DONE.md`, con riepilogo di cosa resta da decidere. Non deve forzare tutte e sei le decisioni se ne chiedi una sola.

### Step C4: Pulizia

```bash
rm -rf /tmp/collaudo-adr
```

## Il caso del repository d'origine

In questo repository le quattro skill sono già installate — **di progetto**, in `.claude/skills/`,
versionate col codice — e non vanno reinstallate. La procedura qui sopra serve per gli *altri*
repository. Quello che conta sapere, se ci si lavora, è che qui sono state **personalizzate**, e
perché.

Il 29 agosto 2026 sono entrate verbatim con il commit `fdd70c5` — che resta l'archivio degli
originali intatti — e subito dopo sono state adattate, perché due di esse dicevano cose già decise
diversamente nel registro del repository.

| Skill | Che cosa è cambiato | Scheda |
|---|---|---|
| `git-flow` | **Nulla nel corpo**: il testo di Driessen è intatto. Sono cambiate la `description`, per non farla attivare qui, e un blocco in testa che dice che nel repository d'origine non si applica | **ADR-026** |
| `modello-dei-rami` | È la variante locale, **nuova**: descrive il modello di qui e le quattro divergenze da Git Flow. È la skill che governa i rami | **ADR-026** |
| `github-flow` | `description` e blocco in testa: vale per repository con un solo branch permanente, che questo non è | **ADR-025** |
| `adr-brainstorm` | Fasi 0–3 immutate. La fase 4 riscritta: le schede vanno in `Docs/Decision.md`, non in `docs/adr/NNNN-slug.md` | **ADR-025** |
| `workflow-conventions` | Un blocco in testa dichiara che quattro delle sei decisioni sono già prese qui; l'output punta al registro di questo repo | **ADR-025** |

Tre cose valgono per **tutte**, e sono la parte che conviene riportare anche altrove:

1. **In caso di conflitto vince la scheda di `Docs/Decision.md`, non la skill.** La regola è ripetuta
   in `CLAUDE.md`, che è l'unico documento letto a ogni sessione — cioè l'unico posto dove agisce
   *prima* del conflitto invece che dopo.
2. **I percorsi si scrivono con il case esatto.** Ogni skill porta in coda una sezione che lo dice:
   `Docs/` e non `docs/`, perché il repository deve poter vivere anche su Linux, dove le due sono
   cartelle diverse (**ADR-027**).
3. **I comandi si mostrano già prefissati con `rtk`** e il promemoria sul costo in token sta in coda a
   ogni skill, tarato sul file che quella skill apre davvero (**ADR-028**).

Personalizzare non ha costo di biforcazione: queste sono copie **di progetto**, e le copie personali
in `~/.claude/skills/` usate negli altri repository non ne sono toccate. Il prezzo è l'opposto — le
due versioni divergono nel tempo, e un aggiornamento a monte va riportato a mano.

## Il caso di SqlStart2026

Qui l'installazione è avvenuta il **6 settembre 2026**, ed è anch'essa **di progetto**:
`.claude/skills/`, versionata col repository. Tre cose la distinguono da quella descritta
sopra, e conviene saperle prima di seguire la procedura.

**Sono dodici, non quattro.** La procedura in questa pagina copre le quattro skill
originarie; il pacchetto ripreso dal repository d'origine ne contiene dodici, perché nel frattempo
quel repository ne ha scritte altre otto — `decision-md`, `sources-md`,
`registro-di-sviluppo`, `project-memory`, `revisione-pr`, `changelog-di-chiusura`,
`worktree-di-step` e `modello-dei-rami`. La pagina che le elenca tutte, con che cosa fa
ciascuna e se qui governa o è di riferimento, è [`README.md`](README.md).

**Non sono arrivate da un file `.skill`.** Gli Step 1 e 2 qui sopra estraggono degli
archivi zip scaricati; qui il pacchetto è stato copiato da un clone del repository di
provenienza, il che rende superfluo il rimedio dello «unzip annidato» e rende invece
necessario un controllo che là non serviva: che la copia sia byte per byte l'originale
(`diff -r`, verificato) e che non porti dentro credenziali di un altro repository
(setaccio dei segreti della skill `revisione-pr`, un solo colpo e su un valore finto delle
sue stesse prove).

**Il collaudo non è quello del C2.** Lo Step C2 chiede di produrre un ADR conforme a
`esempio-adr-0001.md`, che atterra in `docs/adr/0001-<slug>.md` — una forma che questo
repository non usa: qui le schede stanno tutte in `docs/Decision.md`, in ordine
cronologico e con l'ancora esplicita. Il collaudo eseguito è stato un altro, e più severo:
le tre suite di prove che le skill si portano dietro, lanciate qui.

| Suite | Prove | Esito |
|---|---|---|
| `.claude/skills/revisione-pr/tests/test-revisione.sh` | 53 | tutte passate |
| `.claude/skills/changelog-di-chiusura/tests/test-changelog.sh` | 40 | tutte passate |
| `.claude/skills/worktree-di-step/tests/test-step.sh` | 34 | tutte passate |

Centoventisette prove, senza rete e senza spendere token: le suite si costruiscono da sole
un repository temporaneo e sostituiscono `gh`, `agy` e `codex` con dei finti. Che passino
qui dice una cosa precisa e non di più — **gli script sono portabili**. Non dice che le
skill siano adatte a questo repository, che è una domanda diversa e ha una risposta
misurata in [`README.md`](README.md).

## Verifica finale

- [ ] `ls ~/.claude/skills/*/SKILL.md` mostra tutte e quattro le skill
- [ ] Il collaudo C2 ha prodotto un ADR conforme all'esempio
- [ ] (Se installazione di progetto) la cartella `.claude/skills/` è committata nel repo
- [ ] È stato deciso **quale** modello di branching adotta il repo — `git-flow` o `github-flow` non convivono, e la scelta è a sua volta un ADR

## Troubleshooting

| Sintomo | Causa probabile | Rimedio |
|---------|-----------------|---------|
| La skill non si attiva sul prompt naturale | Sessione avviata prima dell'installazione | Chiudi e riavvia `claude` (nuova sessione) |
| `/adr-brainstorm` non riconosciuto | `SKILL.md` non è al primo livello della cartella (unzip annidato) o nome cartella diverso | Verifica `~/.claude/skills/adr-brainstorm/SKILL.md`; il comando deriva dal nome della directory |
| Errore di parsing del frontmatter | Chiavi YAML inattese o file modificato | Ripristina dal `.skill`; il frontmatter deve restare nei campi dello standard |
| La skill si attiva ma ignora template/evidenza | File in `references/` o `assets/` mancanti | Ri-estrai l'archivio completo (Step 2) |
| Su claude.ai il pulsante "Save skill" non appare | L'organizzazione non consente la creazione di skill | Usa l'installazione filesystem in Claude Code |
| Trigger troppo frequente/invadente | Descrizione volutamente "spinta" | Ammorbidisci la frase dei trigger nel campo `description` del `SKILL.md` |

## Rollback

Disinstallazione definitiva:

```bash
rm -rf ~/.claude/skills/adr-brainstorm ~/.claude/skills/workflow-conventions ~/.claude/skills/git-flow ~/.claude/skills/github-flow
```

Disattivazione temporanea (la skill resta su disco ma non viene caricata):

```bash
mv ~/.claude/skills/adr-brainstorm ~/.claude/skills/_adr-brainstorm
```

Gli ADR e gli artefatti già generati nei repo non vengono toccati dal rollback: sono file normali versionati in Git.

## Riferimenti

- Documentazione ufficiale skill in Claude Code (percorsi, discovery, invocazione) — https://code.claude.com/docs/en/skills
- Panoramica Agent Skills (superfici supportate, formato SKILL.md) — https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- Documento sorgente delle pratiche: *Dall'idea al software funzionante* (`introduzione-flusso-di-lavoro.md`, in questa stessa cartella)
- Output di riferimento del collaudo: `esempio-adr-0001.md`
- Nel repository d'origine: le schede **ADR-025**, **ADR-026**, **ADR-027** e **ADR-028**, e la sezione «Le skill: quali governano e quali sono di riferimento» di `CLAUDE.md`

## History

| Data | Eseguito da | Note |
|------|-------------|------|
| 2026-08-07 | Claude (test inline in fase di creazione) | Collaudo C2 simulato: prodotto `esempio-adr-0001.md`, conforme ai criteri |
| 2026-08-29 | Claude Code, ramo `infra/pr-review-e-ambiente` | Installazione **di progetto** nel repository d'origine delle quattro skill (commit `fdd70c5`, verbatim), poi personalizzazione e nuova skill `modello-dei-rami`. Runbook esteso a quattro skill e alla sezione «Il caso del repository d'origine» |
| 2026-09-06 | Claude Code, ramo `release/1.0` di SqlStart2026 | Installazione **di progetto** delle dodici skill (commit `3f22d6f`, verbatim), copia verificata con `diff -r` e passata al setaccio dei segreti. Collaudo con le tre suite delle skill: 127 prove, tutte passate. Runbook esteso con «Il caso di SqlStart2026» |
