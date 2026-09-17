# Concetti generali: il flusso di lavoro, e da dove viene

Questa cartella contiene materiale **importato da un altro repository**. Non descrive MongoDB e
non descrive il laboratorio del talk: descrive il modo di lavorare — come si prende una decisione
e come la si scrive, come si tiene un registro delle fonti, come si sceglie una politica dei rami,
come si fa revisionare il proprio lavoro da qualcuno che non l'ha scritto.

Sta qui, e non in una cartella a parte, perché è la stessa domanda a cui rispondono le altre pagine
di [`06-sviluppo`](../../README.md#06-sviluppo--come-è-fatto-il-lab): non «che cosa fa il lab», ma
«come è stato costruito».

---

## Provenienza

| | |
|---|---|
| **Repository** | _privato, non pubblicato_ |
| **Ramo** | `step/azure-policy/allineamento-e-fase-1` |
| **Origine dei documenti** | `Docs/Concetti-Generali/` |
| **Origine delle skill** | `.claude/skills/` |
| **Ripreso il** | 6 settembre 2026 |
| **Entrato con** | `3f22d6f` (skill, verbatim), `71f4e00` (adattamento delle skill) |

Sono arrivate due cose insieme, e vanno tenute distinte perché hanno statuto diverso.

**I tre documenti**, in questa cartella, sono **testi di riferimento**. Si leggono, si citano, non
governano niente.

| Documento | Che cos'è |
|---|---|
| [`introduzione-flusso-di-lavoro.md`](introduzione-flusso-di-lavoro.md) | *Dall'idea al software funzionante*, v3.1 — sei temi con bibliografia annotata: commit atomici contro commit raggruppati, ADR e razionale, pull request, review, piano di lavoro, politiche di branching. È il documento sorgente da cui le skill sono state derivate |
| [`runbook-installazione-skill.md`](runbook-installazione-skill.md) | come si installano e si collaudano le skill, con in coda la sezione «Il caso di SqlStart2026» che racconta l'installazione del 6 settembre |
| [`esempio-adr-0001.md`](esempio-adr-0001.md) | l'ADR di riferimento prodotto dal collaudo: serve a vedere che forma deve avere il risultato. **Attenzione al percorso che nomina**: `docs/adr/0001-<slug>.md` è la forma di quel repository, non di questo |

**Le dodici skill**, in `.claude/skills/` alla radice del repository, sono **operative**: si accendono
da sole durante una sessione di Claude Code e cambiano il modo in cui il lavoro viene fatto. Per
questo hanno richiesto un adattamento, e per questo la regola che segue esiste.

---

## La regola che governa tutto

> **In caso di conflitto fra una skill e una scheda accettata di
> [`docs/Decision.md`](../../Decision.md), vince la scheda.**

Non è una formalità. Le skill arrivano da un repository che ha preso decisioni proprie, alcune
diverse dalle nostre e prese per ragioni che qui non valgono. Una skill è un testo persuasivo che
si presenta al momento giusto: senza una regola di precedenza scritta, un giorno riscriverà una
decisione presa senza che nessuno se ne accorga.

La stessa regola è ripetuta nel blocco in testa a **ognuna** delle dodici skill, perché è lì che
serve — nel momento in cui la skill viene letta, non in una pagina che si potrebbe non aprire.

---

## Che cosa è stato misurato, e perché l'adattamento non era rimandabile

Importate verbatim, le skill non funzionavano qui. La `description` del frontmatter è la superficie
che decide se una skill si accende, e nella versione originale:

| | Quante | Effetto in SqlStart2026 |
|---|---|---|
| nominano il repository d'origine **come condizione** | 9 | non si accendono mai: inerti |
| lo nominano **per negazione** («NOT the origin one») | 2 | si accendono, e propongono un modello che qui è già stato scelto |
| generiche | 1 | si accende, ma scrive nel posto sbagliato |

Undici su dodici erano quindi o mute o fuori bersaglio. In più il pacchetto conteneva 95 occorrenze
di `Docs/` con la maiuscola, che qui è `docs/`.

**Il caso che valeva da solo l'adattamento è `git-flow`.** La sua descrizione diceva «use when the
repository in question is NOT the origin one», quindi *qui si accendeva*; e il suo file
`references/comandi.md` elenca `git flow feature finish` fra gli equivalenti AVH. Quel comando in
questo repository è vietato, da quando saltò la revisione sulla PR #1 e la fusione avvenne senza
che nessuno l'avesse guardata. Il modello di qui **ha la forma** di Git Flow — `main`, `develop`,
`feature/NN-nome`, `release/1.0` — ed è proprio la somiglianza a rendere la trappola efficace: la
differenza sta tutta nella chiusura, che qui è una pull request rivista e unita dal Product Owner.

---

## Le dodici skill, e che cosa fa ciascuna qui

| Skill | Qui | In una riga |
|---|---|---|
| [`decision-md`](../../../.claude/skills/decision-md/SKILL.md) | **governa** | il registro delle decisioni. Qui è un file solo, `docs/Decision.md`, numerazione a quattro cifre, ancora `<a id="adr-NNNN"></a>` scritta a mano, `**Fonti:**` obbligatorio, controllo `make docs-check` |
| [`sources-md`](../../../.claude/skills/sources-md/SKILL.md) | **governa** | il registro delle fonti. Qui le voci sono `V-NNN` con Verdetto, Riserve, Data e «Usata da» |
| [`registro-di-sviluppo`](../../../.claude/skills/registro-di-sviluppo/SKILL.md) | **governa** | il diario append-only. Qui è un file solo, con le note di metodo numerate di seguito |
| [`adr-brainstorm`](../../../.claude/skills/adr-brainstorm/SKILL.md) | **governa**, tranne la fase 4 | conduce la conversazione fino alla decisione; la scrittura passa a `decision-md` |
| [`revisione-pr`](../../../.claude/skills/revisione-pr/SKILL.md) | **governa**, estesa | due revisori esterni e un triage con verdetto scritto. Qui una release si revisiona prima che la PR esista |
| [`git-flow`](../../../.claude/skills/git-flow/SKILL.md) | riferimento | Git Flow originale di Driessen. I suoi comandi **non si eseguono qui** |
| [`github-flow`](../../../.claude/skills/github-flow/SKILL.md) | riferimento | presuppone un solo ramo permanente; qui ce ne sono due |
| [`modello-dei-rami`](../../../.claude/skills/modello-dei-rami/SKILL.md) | non governa | è il modello del repository d'origine, dove una feature *è* un progetto |
| [`worktree-di-step`](../../../.claude/skills/worktree-di-step/SKILL.md) | non governa | qui non esiste il livello dello step: la procedura è [`worktree-e-branch-di-lavoro.md`](../worktree-e-branch-di-lavoro.md) |
| [`workflow-conventions`](../../../.claude/skills/workflow-conventions/SKILL.md) | non governa | le sei decisioni di bootstrap qui sono già prese |
| [`changelog-di-chiusura`](../../../.claude/skills/changelog-di-chiusura/SKILL.md) | non governa | questo repository non ha un `CHANGELOG.md` |
| [`project-memory`](../../../.claude/skills/project-memory/SKILL.md) | non governa | la memoria di lavoro sta fuori dal repository, nella memoria di sessione di Claude Code |

---

## Il collaudo, e che cosa dice davvero

Le skill si portano dietro tre suite di prove, lanciate qui il 6 settembre: **127 prove, tutte
passate** — 53 di `revisione-pr`, 40 di `changelog-di-chiusura`, 34 di `worktree-di-step`. Girano
senza rete e senza spendere token: si costruiscono da sole un repository temporaneo e sostituiscono
`gh`, `agy` e `codex` con dei finti.

Che passino dice una cosa sola, e conviene non farle dire di più: **gli script sono portabili**. Non
dice che le skill siano adatte a questo repository — quella è la domanda a cui risponde la tabella
qui sopra, e la risposta è che sette su dodici non lo sono.

---

## Il prezzo, dichiarato

Queste sono **copie**. Divergeranno da quelle del repository d'origine, e un miglioramento fatto
là andrà riportato qui a mano. Per tenere quel costo basso l'adattamento tocca due cose per file —
la `description` e un blocco in testa — e **lascia i corpi intatti**: così un aggiornamento a
monte resta un `diff` leggibile invece di una fusione.

Due cose che questa cartella **non** copre, e vale la pena saperlo:

- I documenti importati descrivono pratiche che questo repository in parte non segue — lo squash
  merge, gli ADR come file separati numerati, il template di PR. Sono buone pratiche argomentate
  con evidenza empirica, non decisioni di qui.
- Questo repository **non ha una scheda** che fissi il proprio modello dei rami, la strategia di
  merge o lo standard dei messaggi di commit. La pratica esiste, è coerente ed è descritta in
  [`worktree-e-branch-di-lavoro.md`](../worktree-e-branch-di-lavoro.md), ma non è mai stata
  registrata come decisione. È un vuoto vero, ed è emerso proprio importando le skill che quelle
  decisioni le pretendono.
