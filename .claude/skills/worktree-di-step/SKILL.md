---
name: worktree-di-step
description: Use at the START of any working step on a project of the origin repository, and again at its end, to open and close an isolated git worktree for that step. It lets two agents work on two different projects in the same repository at the same time without colliding, and closes the step by fast-forwarding the feature branch the work started from. Use also to resume a step after a dead session, or to abandon one.
---

# worktree-di-step — lo spazio isolato di uno step

Standard del repository d'origine. È il livello più basso del ciclo di vita dei rami: governa lo
step dentro la feature, e nient'altro. Il resto — feature verso `develop`, `develop` verso `main`
— sta in [`Docs/Decision.md`](../../../Docs/Decision.md).

## A che serve

Due problemi diversi, che hanno la stessa soluzione.

**Il primo:** nel repository d'origine feature e progetto coincidono uno a uno, e **la cartella di
un progetto esiste soltanto sul suo ramo**. `develop` porta l'infrastruttura e nessun progetto;
`main` è l'archivio delle release. Un agent che apra uno spazio di lavoro con i default degli
strumenti si ritrova a diramare da `origin/main` e quindi in una cartella praticamente vuota:
niente progetto, niente `CLAUDE.md`, niente skill. Fra il 21 e il 28 agosto 2026 è successo almeno
cinque volte.

**Il secondo:** due agent sullo stesso PC devono poter lavorare su due progetti diversi senza
pestarsi i piedi.

## Che cosa NON è

**Non decide quando uno step è finito.** Lo decide la Definition of Done del piano di sviluppo del
progetto, se un piano c'è, oppure il Product Owner in chat. La skill si occupa di che cosa fare
*una volta* deciso.

**Non governa la chiusura della feature né il rilascio.** Quelli sono `Docs/Decision.md`.

**Non riallinea le feature con `develop`.** Se ne accorge e lo segnala; riallineare è del
proprietario, e le istruzioni stanno in [`Docs/riallineamento-feature.md`](../../../Docs/riallineamento-feature.md).

## Le due regole che rendono sicuro tutto il resto

1. **Un agent, una feature.** Git tiene **un solo checkout per ramo**, per costruzione: due agent
   che rispettano questa regola non possono collidere neanche volendo, perché il conflitto viene
   rifiutato dal database dei riferimenti e non da una convenzione che qualcuno deve ricordarsi.
   La protezione però è sul *ramo*, non sulla cartella di progetto: se due feature toccassero la
   stessa cartella, git tacerebbe. La mappatura uno a uno è ciò che rende la garanzia sufficiente.
2. **Uno step alla volta per feature.** È questa regola, e non la fortuna, a rendere il
   fast-forward di chiusura *garantito*: se nessun altro committa su `feature/<prj>` mentre lo step
   è aperto, il ramo non può essersi mosso.

## Dove vivono i cantieri

| | Forma | Esempio |
|---|---|---|
| Ramo di step | `step/<prj>/<nome-step>` | `step/create-VM/collaudo-debian` |
| Cartella del cantiere | `.claude/worktrees/<prj>--<nome-step>/` | `.claude/worktrees/create-VM--collaudo-debian/` |

`<prj>` è il nome **esatto** della cartella di progetto, lo stesso che si usa come scope nei commit.
Il separatore `--` non è estetico: con `/` il cantiere finirebbe dentro una cartella che potrebbe
essere a sua volta un worktree.

`feature/<prj>` **non viene mai estratta.** Vive solo in `.git`, e si avanza in fast-forward senza
checkout. È il motivo per cui la chiusura funziona da qualunque cantiere.

## Il protocollo

Tutti i comandi sono `.claude/skills/worktree-di-step/scripts/step.sh`.

| Fase | Comando | Dove |
|---|---|---|
| 0. Orientamento | `step.sh stato` | checkout principale |
| 1. Ingaggio | `git show feature/<prj>:<prj>/Memory/stato-del-lavoro.md` | checkout principale |
| 2. Apertura | `step.sh apri <prj> <nome>`, poi `EnterWorktree(path: …)` | checkout principale |
| 3. Lavoro | commit logici | cantiere |
| 4. Chiusura | `step.sh chiudi`, poi `ExitWorktree(keep)`, poi `step.sh smonta <prj> <nome>` | cantiere, poi principale |

### Fase 0 — Orientamento

`step.sh stato` dice quali cantieri sono aperti e quali feature sono indietro rispetto a `develop`.

**Se esiste già un cantiere per il progetto su cui stai per lavorare, fermati e riferisci.** O ci
sta lavorando un altro agent, o è il relitto di una sessione morta: in entrambi i casi la decisione
è del proprietario.

### Fase 1 — Ingaggio della feature

La memoria di progetto si legge senza estrarre la feature:

```bash
rtk git show feature/<prj>:<prj>/Memory/stato-del-lavoro.md
```

Leggila **prima di qualunque altra cosa** — vedi la skill `project-memory`. Se il progetto ha un
piano in `<prj>/Docs/plans/`, leggi anche quello: è lì che sta la Definition of Done, quando c'è.

### Fase 2 — Apertura del cantiere

```bash
step.sh apri <prj> <nome-step>
```

Il nome dello step è in minuscolo con trattini, e dice **che cosa si sta per fare**, non «step-3».
Il comando rifiuta se la feature non esiste, se è estratta da qualche parte, se un cantiere è già
aperto su quel progetto, o se il ramo di step esiste già.

Poi entra nel cantiere, **con `path:` e non con `name:`**:

```
EnterWorktree(path: ".claude/worktrees/<prj>--<nome-step>")
```

È l'unico cambio di sessione dell'intero step.

### Fase 3 — Lavoro

Commit logici, Conventional, soggetto in italiano minuscolo, scope uguale al nome esatto della
cartella di progetto. Mai `git add .`: percorsi espliciti.

Le voci del **registro di sviluppo** si scrivono qui, dentro lo step, non dopo: così arrivano sulla
feature insieme al lavoro che descrivono. Vale lo stesso per l'aggiornamento della **Memory**, che
va nell'ultimo commit dello step.

### Fase 4 — Chiusura

Si chiude sulla Definition of Done del piano, oppure quando il Product Owner lo dice in chat.

```bash
step.sh chiudi                      # dentro il cantiere: fast-forward + push
# ExitWorktree(action: "keep")      <- keep, mai remove
step.sh smonta <prj> <nome-step>    # dal checkout principale
```

`chiudi` verifica che l'albero sia pulito, che ci sia qualcosa da portare, avanza `feature/<prj>` in
fast-forward e spinge su `origin`. `smonta` accerta che il ramo sia davvero dentro la feature prima
di distruggere qualsiasi cosa.

## Le sei cose da non fare mai

| # | Cosa | Perché | Che cosa fare invece |
|---|---|---|---|
| 1 | `EnterWorktree(name: …)` | dirama da `origin/main`, che qui ha `LICENSE` e `README.md` e basta | `step.sh apri`, poi `EnterWorktree(path: …)` |
| 2 | `ExitWorktree(action: "remove")` | conta i commit scartati rispetto a `main`: annuncia disastri inesistenti | `keep`, poi `step.sh smonta` |
| 3 | Aggirare il rifiuto di `chiudi` | il rifiuto **è un'informazione**: dice che la feature si è mossa | fermarsi e riferire |
| 4 | Due step aperti sullo stesso progetto | rompe la garanzia del fast-forward | uno alla volta |
| 5 | `git add .` | alcune cartelle sono untracked di proposito | percorsi espliciti |
| 6 | Abbandonare uno step di propria iniziativa | è l'unica azione irreversibile del ciclo | riferire, e attendere il mandato |

## Quando le cose vanno male

**La sessione muore a metà step.** Non si perde niente: cantiere e ramo restano su disco e in
`.git`. `step.sh stato` ritrova il cantiere; si rientra con `EnterWorktree(path: …)` e si guarda
dove ci si era fermati:

```bash
rtk git log --oneline feature/<prj>..step/<prj>/<nome>
```

**Il fast-forward viene rifiutato.** `feature/<prj>` si è mossa mentre lo step era aperto. Il ramo è
rimasto fermo, ed è la cosa giusta. **Non inventare un merge**: o è saltata la regola di uno step
alla volta, o qualcuno ha committato sulla feature da fuori. Fermati e riferisci.

**Una cartella di cantiere è sparita** senza passare da `step.sh smonta`. `git worktree prune`
ripulisce le registrazioni orfane; il ramo `step/…` resta, e che farne è una decisione, non
un'operazione.

**Lo step va abbandonato.** **Non è una decisione dell'agent.** Constata, riferisci, fermati. Il
Product Owner approva, e solo allora:

```bash
step.sh abbandona <prj> <nome-step> --mandato
```

La feature non è mai stata toccata: è esattamente la proprietà per cui il cantiere esiste. Si perde
il lavoro dello step, e si perde su mandato esplicito.

## Il confine con gli altri registri

| Domanda | Documento | Disciplina |
|---|---|---|
| Come si apre e si chiude uno step | questa skill | procedura |
| Perché il repository funziona così | `Docs/Decision.md` (`decision-md`) | normativo, di **repository** |
| Su quali fonti poggia | `Docs/Sources.md` (`sources-md`) | append-only, di **repository** |
| Dove siamo adesso, cosa fare dopo | `<prj>/Memory/stato-del-lavoro.md` (`project-memory`) | si sovrascrive |
| Che cosa è successo, e quando | `<prj>/Docs/registro/…` (`registro-di-sviluppo`) | append-only |
| Perché abbiamo deciso così, nel progetto | `<prj>/Docs/Decision.md` (`decision-md`) | normativo, di progetto |

## Verifica

```bash
.claude/skills/worktree-di-step/tests/test-step.sh
```

Costruisce repository usa e getta con un remoto vero ed esercita il ciclo completo, compresi i
rifiuti. Trentaquattro controlli. Se tocchi `step.sh`, questo deve restare verde.

## Commit

```
feat(<scope>): <che cosa fa ora il codice>
```

`<scope>` è il nome esatto della cartella di progetto. Il corpo dice **perché**, non ripete il
diff. Trailer `Co-Authored-By` come nel resto del repo.

## Il costo in token

I comandi mostrati sopra sono gia' prefissati con `rtk`, e vanno copiati cosi'. `step.sh` non ha un
filtro dedicato e passa inalterato — il che non e' un motivo per togliere il prefisso, ma la ragione
per cui metterlo e' sempre sicuro.

Lo script vive in `.claude/`, che tokensave non indicizza: per capire che cosa fa si legge con
`rtk read`, non si interroga l'indice.

Le regole per esteso — che cosa copre l'indice, che cosa no, e come si scavalca il hook quando
il server non risponde — stanno in «Il costo in token» di `CLAUDE.md`.
