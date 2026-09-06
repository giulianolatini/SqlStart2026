---
name: changelog-di-chiusura
description: Use when closing a feature branch onto develop in a repository that keeps a CHANGELOG.md, or when a CHANGELOG entry looks wrong, duplicated or out of date. SqlStart2026 has NO CHANGELOG.md and does not want one: here the story of what changed is told by docs/registro-operativo-sviluppo.md and by the commit messages. Do not run this skill's script in SqlStart2026 — it is kept as reference material.
---

# changelog-di-chiusura — il racconto dei commit

> [!IMPORTANT]
> **In SqlStart2026: non governa.** Questo repository non ha un `CHANGELOG.md`, e non gli manca: la cronologia di che cosa è cambiato la tiene `docs/registro-operativo-sviluppo.md`, che però è un diario e non un derivato dei commit. Lo script `scripts/changelog.sh` qui non ha un file su cui lavorare. Resta come materiale di riferimento — e come promemoria che un changelog, se un giorno servisse, si genera dai commit e non si scrive a mano.
>
> Il corpo qui sotto è quello del repository d'origine, intatto. In caso di conflitto fra
> questa skill e una scheda accettata di [`docs/Decision.md`](../../../docs/Decision.md),
> **vince la scheda**. La provenienza e le divergenze misurate stanno in
> [`concetti-generali/README.md`](../../../docs/06-sviluppo/concetti-generali/README.md).

Standard del repository d'origine. Trasforma i commit di una feature in un `CHANGELOG.md`
leggibile, e lo rifà da capo ogni volta invece di accodare: il file è **derivato**, non scritto a
mano.

La sorgente è il commit message. Se un commit è scritto male il CHANGELOG lo dice invece di
nasconderlo — vedi *Fuori convenzione* più sotto.

## A che serve

Un progetto qui vive su un ramo solo e poi sparisce dentro `develop`. Chi lo riapre sei mesi dopo ha
davanti la cartella finale e nessun racconto di come ci si è arrivati. `git log` c'è sempre, ma
richiede di sapere già quale intervallo guardare — e l'intervallo giusto (`develop..feature/<prj>`)
non è ovvio a chi non ha letto [`Docs/Decision.md`](../../../Docs/Decision.md).

Il CHANGELOG è quell'intervallo, già calcolato e già tradotto in italiano.

## Che cosa NON è

**Non decide quando una feature è chiusa.** Lo decide il Product Owner. La skill si occupa di che
cosa produrre *una volta* deciso.

**Non è un file che si modifica a mano.** Fra due marcatori `<!-- changelog:… -->` il contenuto
viene sostituito a ogni generazione. Quello che scrivi lì dentro sparisce; quello che scrivi fuori
resta.

**Non sostituisce il registro di sviluppo.** Il registro racconta la giornata di lavoro, dubbi
compresi; il CHANGELOG elenca che cosa è cambiato nel prodotto. Vedi il confine in fondo.

## Il protocollo

Tutti i comandi sono `.claude/skills/changelog-di-chiusura/scripts/changelog.sh`.

| Comando | Che cosa fa | Dove scrive |
|---|---|---|
| `feature <prj>` | sezione della feature, in anteprima | niente |
| `feature <prj> --scrivi` | la stessa sezione, sul file | `<prj>/CHANGELOG.md` |
| `rilascio <prj> <n>` | sezione del rilascio, in anteprima | niente |
| `rilascio <prj> <n> --scrivi` | la stessa sezione, sul file | `CHANGELOG.md` di radice |
| `messaggio <prj> <n>` | corpo del commit di rilascio, su stdout | niente |
| `verifica <prj>` | esce 0 se il CHANGELOG copre l'ultimo commit | niente |

**Senza `--scrivi` non tocca nulla.** È il modo giusto di guardare prima di scrivere, e l'anteprima
è identica al carattere a quello che finirà nel file.

### Alla chiusura di una feature

Dentro il cantiere dell'ultimo step, prima di `step.sh chiudi`:

```bash
.claude/skills/changelog-di-chiusura/scripts/changelog.sh feature <prj>            # guarda
.claude/skills/changelog-di-chiusura/scripts/changelog.sh feature <prj> --scrivi   # scrivi
```

Il file aggiornato entra nell'**ultimo commit dello step**, insieme alla Memory. Così arriva su
`develop` con il lavoro che racconta, e non in un commit orfano dopo il merge.

> [!IMPORTANT]
> `feature` rifiuta di scrivere se non sei su `feature/<prj>` o su uno dei suoi `step/<prj>/…`. Non
> è pignoleria: `<prj>/CHANGELOG.md` sta dentro la cartella del progetto, che **esiste solo su quel
> ramo**. Da `develop` il comando creerebbe una cartella nuova con dentro un solo file.

### All'archiviazione su `main`

```bash
changelog.sh rilascio <prj> <n> --scrivi   # sezione nel CHANGELOG.md di radice
changelog.sh messaggio <prj> <n>           # corpo del commit di snapshot
```

Il `CHANGELOG.md` di radice è l'indice dei rilasci: una sezione per rilascio, le più recenti in
alto, e dentro ciascuna le voci in ordine cronologico. `messaggio` produce lo stesso elenco di
titoli nel corpo del commit di snapshot, così il racconto è leggibile anche da `git show` senza
aprire il file.

## Le due scelte che spiegano il formato

**Ordine cronologico, non raggruppato per tipo.** Keep a Changelog raggruppa in *Added / Changed /
Fixed*, ed è la scelta giusta quando il lettore è un utente che vuole sapere cosa è cambiato nella
versione. Qui il lettore è chi deve **ricostruire come si è arrivati a una decisione**, spesso
mesi dopo, e per quello serve la sequenza: prima questo, poi quello, quindi la correzione. È anche
ciò che rende il file utile come evidenza di tracciabilità. I tipi restano, come etichetta di ogni
voce, e il riepilogo in testa dà comunque il colpo d'occhio per categoria.

**L'intervallo è `develop..feature/<prj>`, senza filtri sui percorsi.** Sembra fragile e invece è
la cosa più solida disponibile: per ADR-002 una feature **è** un progetto, uno a uno. Quell'invariante
fa da filtro meglio di qualunque euristica sui percorsi — che infatti, provata, perdeva il commit
di fondazione dei progetti nati sotto `Tools/` prima di ADR-016.

Al rilascio il filtro sui percorsi torna, perché lì l'intervallo è `main..develop` e contiene anche
l'infrastruttura. Lì il pathspec è `*/<prj>/*` **con l'asterisco finale**: senza magia esplicita git
confronta il pathspec con il percorso intero, quindi `*/alfa/` non trova `Tools/alfa/alfa.sh`.

## Fuori convenzione

Un commit che non rispetta `tipo(ambito): soggetto` non viene scartato: compare come **Fuori
convenzione**, e il riepilogo lo conta. È deliberato. Un CHANGELOG che tace i commit che non sa
classificare mente su quanto lavoro c'è stato, e nessuno se ne accorge.

Se ne vedi uno, la domanda giusta non è «come lo nascondo» ma «quel commit andava scritto meglio».

## Rotture di compatibilità

Vengono riconosciute in due modi, come da specifica Conventional Commits: `!` prima dei due punti
nel soggetto, oppure `BREAKING CHANGE:` nel corpo. Finiscono in un blocco `> [!WARNING]` in testa
alla sezione, e la voce nell'elenco porta `⚠️`.

## Le cose da non fare

| # | Cosa | Perché | Che cosa fare invece |
|---|---|---|---|
| 1 | Scrivere a mano fra i marcatori | la generazione successiva sostituisce tutto | correggere il commit message, o scrivere fuori dai marcatori |
| 2 | Generare da `develop` | la cartella del progetto non c'è | generare dal cantiere di step |
| 3 | Un commit di CHANGELOG dopo il merge | arriva staccato dal lavoro che racconta | dentro l'ultimo commit dello step |
| 4 | Nascondere i *Fuori convenzione* | il file mentirebbe sul lavoro fatto | riscrivere meglio i prossimi commit |

## Verifica

```bash
.claude/skills/changelog-di-chiusura/tests/test-changelog.sh
```

Costruisce un repository usa e getta con `develop`, due feature, una rinomina di cartella e una
rottura di compatibilità, ed esercita i quattro comandi compresi i rifiuti. Quaranta controlli. Se
tocchi `changelog.sh`, questo deve restare verde.

Le quattro cose che le prove esistono per impedire — e che non si vedono su un repository finto a un
commit solo — sono: raccogliere commit che non appartengono alla feature, perdere i commit anteriori
a una rinomina al momento del rilascio, duplicare la sezione rigenerandola, e scrivere il file nel
checkout sbagliato.

## Il confine con gli altri registri

| Domanda | Documento | Disciplina |
|---|---|---|
| Che cosa è cambiato nel prodotto | `<prj>/CHANGELOG.md`, `CHANGELOG.md` (questa skill) | **derivato**, si rigenera |
| Che cosa è successo, e quando | `<prj>/Docs/registro/…` (`registro-di-sviluppo`) | append-only |
| Perché abbiamo deciso così | `Docs/Decision.md` (`decision-md`) | normativo |
| Dove siamo adesso | `<prj>/Memory/stato-del-lavoro.md` (`project-memory`) | si sovrascrive |
| Come si apre e si chiude uno step | `worktree-di-step` | procedura |

## Commit

```
docs(<scope>): aggiorna il CHANGELOG di chiusura
```

Di norma non è un commit a sé: il CHANGELOG entra nell'ultimo commit dello step. Se lo è, `<scope>`
è il nome esatto della cartella di progetto.

## Il costo in token

Il racconto si genera dai commit, e i commit si guardano con `rtk git log`: il filtro compatta circa
il 60-80% dell'output, che su un intervallo di feature e' la voce di spesa principale. `rtk git show`
per un singolo commit.

Il `CHANGELOG.md` prodotto si rilegge dal disco, non dall'indice: e' appena stato scritto.

Le regole per esteso — che cosa copre l'indice, che cosa no, e come si scavalca il hook quando
il server non risponde — stanno in «Il costo in token» di `CLAUDE.md`.
