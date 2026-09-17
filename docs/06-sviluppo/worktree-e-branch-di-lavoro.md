# Worktree e branch di lavoro

Questa pagina dice come si apre un branch di feature con il suo worktree, come lo si chiude dopo
che la PR è stata unita, e che cosa fare se la chiusura lascia una sessione bloccata. Non è
documentazione di MongoDB: è la procedura operativa del repository, e sta qui perché un errore in
questa manovra costa un pomeriggio e non si vede finché non è successo.

È scritta il 2 settembre 2026 perché il blocco **è** successo, alla chiusura della PR #4. La
ricostruzione del guasto sta in [V-073](../Sources.md#v-073), la decisione in
[ADR-0079](../Decision.md#adr-0079). Quello che segue è la forma corretta della stessa manovra.

---

## Perché si lavora in worktree

Un worktree è una seconda directory di lavoro sullo stesso repository, con il suo branch agganciato.
Serve a due cose che in questo progetto contano:

- **`develop` resta fermo e leggibile** mentre un branch corre. Chi vuole guardare lo stato unito
  non deve chiedere a nessuno di cambiare ramo.
- **Più sessioni possono lavorare insieme** senza contendersi l'albero, che è la ragione per cui
  il repository ne ha aperti fino a due contemporaneamente.

I worktree stanno in `.claude/worktrees/`, che è ignorato da git (riga 13 di `.gitignore`): la
directory di lavoro non entra nella cronologia, il branch sì.

---

## Aprire: branch e worktree

Tutti i comandi si danno **dal checkout principale**. Nel testo `<repo>` sta per
`~/Sviluppo/GITHUB/SqlStart2026` e `NN-nome` per il nome del branch senza prefisso, per esempio
`04-app-python`.

**1. Portare `develop` alla punta.**

```
git -C <repo> fetch --prune
git -C <repo> merge --ff-only origin/develop
```

Il `--ff-only` è voluto: se non può avanzare per fast-forward, qualcosa è divergente e va guardato
prima di aprire un branch sopra.

**2. Creare branch e worktree in un colpo.**

```
git -C <repo> worktree add -b feature/NN-nome \
    .claude/worktrees/feature-NN-nome develop
```

Questo produce **lo stesso branch** che darebbe `git flow feature start NN-nome`: `.git/config`
configura `gitflow "branch.feature"` con `prefix = feature/` e `startPoint = develop`, quindi nome
e punto di partenza coincidono. La differenza, ed è la ragione per cui si usa questa forma, è che
`git flow feature start` **sposta il checkout principale** sul branch nuovo, mentre `worktree add`
lo lascia su `develop`.

**3. Impostare subito la traccia remota.**

```
git -C <repo> push -u origin feature/NN-nome
```

Si fa adesso e non alla fine: con l'upstream già impostato, l'apertura della PR è un comando solo, e
il branch esiste sul remoto anche se il portatile si spegne.

**4. Copiare ciò che il worktree non riceve.** Un worktree contiene solo i file tracciati. Tutto
quello che è ignorato — a partire dai `.env` degli stack, che contengono la password
dell'amministratore e sono ignorati per decisione ([ADR-0014](../Decision.md#adr-0014)) — **non
c'è**. Se il branch deve avviare uno stack, i `.env` vanno copiati dal checkout principale, che per
[ADR-0056](../Decision.md#adr-0056) è la loro sede:

```
cp <repo>/docker/02-replicaset/.env <repo>/.claude/worktrees/feature-NN-nome/docker/02-replicaset/.env
cp <repo>/docker/03-sharded/.env    <repo>/.claude/worktrees/feature-NN-nome/docker/03-sharded/.env
```

**5. Portare la sessione dentro.** Una delle due, non entrambe:

- avviare una sessione nuova da lì — `cd <repo>/.claude/worktrees/feature-NN-nome && claude`;
- oppure, da una sessione **non agganciata** ad alcun worktree, usare `EnterWorktree` con il
  parametro `path`.

**6. Controllare prima di scrivere una riga.**

```
git -C <repo>/.claude/worktrees/feature-NN-nome rev-parse --abbrev-ref HEAD
make docs-check
```

Il primo deve rispondere `feature/NN-nome`. Il secondo deve essere verde **prima** di qualunque
modifica: un `docs-check` rosso all'apertura è un debito ereditato, e va distinto da uno che hai
introdotto tu.

---

## Chiudere: dopo che la PR è unita

L'ordine di questi passi è **vincolante**, e il primo è quello che si dimentica.

**1. La PR è unita in `develop` sul remoto.** La fusione la fa il Product Owner. Mai
`git flow feature finish`: salta la revisione, ed è già andata male una volta.

**2. Sganciare la sessione — prima di toccare il disco.** Se una sessione sta lavorando dentro il
worktree, va tolta di lì **adesso**, non dopo:

- `ExitWorktree` con `action: "keep"` se è una sessione agganciata;
- oppure chiuderla, se era stata avviata da un terminale dentro il worktree.

Saltare questo passo è precisamente ciò che produce il blocco descritto più sotto. Il motivo per cui
non se ne accorge nessuno è che il comando che segue **funziona**: git non ha modo di sapere che
qualcuno sta in piedi lì dentro.

**3. Riallineare il checkout principale.**

```
git -C <repo> fetch --prune
git -C <repo> merge --ff-only origin/develop
```

**4. Guardare dentro il worktree prima di cancellarlo.** `git worktree remove` si rifiuta di
cancellare un worktree con file non tracciati, ma cancella **senza dire niente** uno che contiene
solo file ignorati ([V-050](../Sources.md#v-050)). In questo repository quella categoria contiene i
`.env`:

```
git -C <repo>/.claude/worktrees/feature-NN-nome status --porcelain --ignored -uall \
  | grep -v -e '/\.venv/' -e '__pycache__' -e '\.pytest_cache'
```

Il filtro toglie ciò che si rigenera da solo. Quello che resta si legge riga per riga, e ciò che non
si ricostruisce con un comando si copia prima di rimuovere.

**5. Rimuovere.**

```
git -C <repo> worktree remove .claude/worktrees/feature-NN-nome
git -C <repo> branch -d feature/NN-nome
git -C <repo> worktree prune
```

Il `-d` minuscolo è voluto: si rifiuta se il branch non è unito, ed è l'ultima rete prima di
perdere lavoro. Il `prune` costa nulla e ripulisce eventuali voci amministrative rimaste.

**6. Verificare.**

```
git -C <repo> worktree list
git -C <repo> branch
```

Devono restare il solo checkout principale e i branch `develop` e `main`.

---

## Se sei già bloccato

Sintomo: ogni comando di shell risponde qualcosa come

```
This session is isolated in the worktree /…/.claude/worktrees/feature-NN-nome,
but this command's working directory resolved to … Refusing to run it there
```

e ogni scrittura viene respinta con l'invito a modificare «la copia nel worktree» di un worktree che
non esiste più. La lettura continua a funzionare, il resto no.

**Non serve chiudere la sessione.** La manovra è di due passi, in quest'ordine:

1. **`ExitWorktree` con `action: "keep"`.** Sgancia il pin e riporta la sessione nel checkout
   principale. Funziona anche se il worktree agganciato è già stato cancellato, e anche se la
   sessione era stata isolata all'avvio invece che con `EnterWorktree` — la sua documentazione dice
   il contrario, la misura dice che funziona ([V-073](../Sources.md#v-073)). Usare sempre `keep`,
   mai `remove`.
2. **`EnterWorktree` con `path:`** puntato al worktree in cui si vuole lavorare.

Due cose da sapere, entrambe verificate:

- `ExitWorktree` annuncia di aver salvato il lavoro «su branch `worktree-<nome>`». Quando la
  directory era già sparita, **quel branch non viene creato**: non compare in `git branch`, e non
  c'è niente da andare a cercare né da cancellare.
- Il rientro diretto non funziona, quindi non perderci tempo. `EnterWorktree` rifiuta se la
  directory corrente non è dentro un repository git, e rifiuta anche se il bersaglio **è già** la
  directory corrente. Si esce e poi si entra, in quest'ordine.

---

## Perché il blocco è possibile

Vale la pena capirlo, perché la stessa forma si ripresenta altrove.

L'isolamento di una sessione è un **percorso assoluto registrato all'avvio**, e vive nello stato
della sessione. Non è un file, non è un ref, non è niente che git possieda. Quando
`git worktree remove` cancella la directory, quel percorso resta dov'era: la guardia continua a
pretendere che ogni comando risolva dentro una directory che non esiste, e nessun comando può
riuscirci.

Il comando che fa il danno è il comando giusto, dato nel momento sbagliato. È la stessa forma di
`umount` prima di staccare il disco: chi tiene aperto il riferimento non è chi cancella, e il
secondo non ha modo di accorgersi del primo. La difesa non può essere un controllo di git — git
guarda il working tree, e una sessione viva non ci lascia niente da guardare — quindi è un ordine
scritto.

È anche la seconda volta che questo repository scopre la stessa cosa su questo stesso comando.
[ADR-0056](../Decision.md#adr-0056) riguardava i file che git ha ricevuto istruzione di **non
guardare**; [ADR-0079](../Decision.md#adr-0079) riguarda i processi che git non ha modo di
**vedere**. Un worktree contiene cose che git non conta, e vanno tolte prima.

---

## Cosa questa pagina non dice

- **Se `ExitWorktree` si comporti allo stesso modo con il worktree ancora in piedi.** Nella misura
  del 2 settembre la directory era già sparita. È il caso normale della chiusura ordinata, e la
  prima volta che lo si fa vale la pena guardare che cosa risponde.
- **Se il blocco si presenti identico su Linux o Windows.** La misura è di una macchina sola, macOS
  26.6.2 arm64.
- **Come si recuperano modifiche non committate perse con il worktree.** Non si recuperano: la
  difesa è il rifiuto di `git worktree remove` davanti ai file non tracciati, e l'abitudine di
  committare a ogni task.

---

**Decisioni correlate:** [ADR-0014](../Decision.md#adr-0014) (il keyfile e i segreti fuori dal
repository), [ADR-0056](../Decision.md#adr-0056) (guardare dentro prima di rimuovere; i `.env` nel
checkout principale), [ADR-0079](../Decision.md#adr-0079) (sganciare la sessione prima di
rimuovere).

**Fonti:** [V-050](../Sources.md#v-050), [V-073](../Sources.md#v-073)
