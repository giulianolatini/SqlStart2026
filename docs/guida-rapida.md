# Guida rapida — da clone a tutto acceso

Questa pagina serve a chi apre il repository la prima volta e vuole **vedere qualcosa girare**,
senza prima leggere le architetture. Sono quattro cose, in quest'ordine: accendere i tre stack,
lanciare l'applicazione contro ognuno, guardare le tre scene, e registrare un filmato.

Ogni comando qui è un bersaglio del `Makefile`, e `make help` li elenca tutti con le variabili
che accettano. Quando un comando ha un output atteso, è scritto accanto: se non torna, il
[runbook della demo](05-talk/runbook-demo.md) dice cosa fare, ed è la pagina da tenere aperta il
giorno del talk. Questa qui è il gradino prima.

- [Prima di tutto: una volta sola](#prima-di-tutto)
- [I tre stack](#i-tre-stack)
- [L'applicazione `mongolab` sulle tre architetture](#applicazione)
- [Le scene](#le-scene)
- [Registrare un filmato](#filmato)
- [Quando qualcosa non torna](#non-torna)

<a id="prima-di-tutto"></a>
## Prima di tutto: una volta sola

Tre cose che si fanno al primo clone e poi non si ripetono.

**1. Le immagini.** È l'unico comando che vuole rete: le scarica e le pinna per digest, così da
lì in poi tutto parte anche con la rete staccata ([ADR-0018](Decision.md#adr-0018)).

```bash
make images-pull
```

**2. Le due password di laboratorio.** L'istanza singola non ha utenti e non ha password. Il
replica set sì, e lo sharded cluster pure: **due file distinti**, uno per stack. Il valore non è
nel repository e non ci sarà mai ([ADR-0040](Decision.md#adr-0040)).

```bash
cp docker/02-replicaset/.env.example docker/02-replicaset/.env
cp docker/03-sharded/.env.example docker/03-sharded/.env
# poi aprire i due file e scrivere la password dopo «PASSWORD_AMMINISTRATORE=»
```

**3. Il controllo preliminare.** Dice se la macchina ce la fa — memoria della VM Docker, porte
libere, immagini presenti — prima di scoprirlo a metà di un avvio.

```bash
make preflight
```

Sulla memoria: standalone, replica set e profilo `palco` dello sharded stanno in circa 6 GiB
assegnati al runtime. Il profilo `completo` — undici container — ne vuole 12
([ADR-0025](Decision.md#adr-0025)).

<a id="i-tre-stack"></a>
## I tre stack

I tre si accendono allo stesso modo: `up-NN` avvia **e attende** che la topologia esista davvero,
`smoke-NN` la prova da capo a fondo, `down-NN` ferma conservando i dati.

```bash
# 01 — istanza singola: nessuna password, nessun keyfile
make up-01
make smoke-01      # dodici controlli end-to-end

# 02 — replica set a tre membri
make up-02
make smoke-02      # atteso: Superati: 42 · Errori: 0

# 03 — sharded cluster
make up-03         # PROFILO=palco è il predefinito
make smoke-03
```

**Lo sharded cluster ha due taglie, e la variabile è `PROFILO`.**

| `PROFILO` | Cosa accende | Quando si usa |
|---|---|---|
| `palco` (predefinito) | un membro per shard, i componenti tutti presenti | è quello che entra in un portatile, ed è quello che si mostra dal vivo ([ADR-0010](Decision.md#adr-0010)) |
| `completo` | tre membri per ogni componente, undici container | mostra l'architettura vera, e serve per la scena in cui un membro di shard viene eletto |

```bash
make up-03 PROFILO=completo
make smoke-03 PROFILO=completo
```

`PROFILO` va ripetuto su **ogni** comando dello stack 03, `down` compreso: è il file Compose che
cambia, e un `down` con il profilo sbagliato lascerebbe in piedi i container dell'altro.

Per spegnere:

```bash
make down-01
make down-02
make down-03       # o make down-03 PROFILO=completo
```

`down` conserva i dati e il keyfile. Per cancellare **anche** i dati c'è `reset-NN`, che è
un'altra cosa e lo dice nel nome.

<a id="applicazione"></a>
## L'applicazione `mongolab` sulle tre architetture

`mongolab` è un client Python che guarda gli stack e ne racconta il comportamento: fotografa la
topologia, la osserva mentre cambia, manda carico, e mette in scena il failover, il backup a caldo
e la chiave di shard. Ogni comando ha un bersaglio nel `Makefile`, e i bersagli prendono **due
variabili**, che sono la cosa da imparare di questa sezione.

| Variabile | Valori | Predefinito | Cosa sceglie |
|---|---|---|---|
| `TARGET` | `standalone` \| `rs` \| `sharded` | **nessuno**, va scritta | contro quale dei tre stack gira |
| `DOVE` | `rete` \| `host` | `rete` | da dove guarda: dentro la rete Compose, o dal portatile |

`TARGET` non ha un predefinito di proposito: l'applicazione si rifiuta di indovinare contro quale
stack la stai lanciando, e il `Makefile` non reintroduce l'assunzione che la CLI evita.

**`DOVE` è la differenza che conta più di quanto sembri.** Con `DOVE=rete` il client gira in un
container **dentro** la rete Compose: scopre i membri del replica set con i nomi che loro stessi
si danno, e parla col primario. È il punto di vista che il talk mostra. Con `DOVE=host` la stessa
riga gira sul portatile con `uv run`: comodo mentre si sviluppa — nessun container da ricostruire,
il debugger attaccato — ma sul replica set vede una topologia che dall'esterno non è la stessa
([ADR-0012](Decision.md#adr-0012)).

### Le tre fotografie, una per architettura

Con i tre stack accesi, questo è il giro completo:

```bash
make app-stats TARGET=standalone
make app-stats TARGET=rs
make app-stats TARGET=sharded
```

`stats` stampa topologia, versione del server, **dettaglio per collezione**, totale del database e
distribuzione. La riga da guardare è `collezioni`, non `database`
([ADR-0121](Decision.md#adr-0121)):

```unknown
collezioni  ordini · 50000 documenti
```

Questi sono i numeri attesi su un lab appena seminato — e sono anche il modo di accorgersi che una
demo precedente ha lasciato lo stack a metà:

| Stack | `TARGET` | Documenti attesi in `lab.ordini` |
|---|---|---:|
| 01 standalone | `standalone` | **50 000** |
| 02 replica set | `rs` | **50 000** |
| 03 sharded | `sharded` | **20 000** |

Se un numero non torna, `./tools/reset-demo.sh 02` — o `01`, o `03` — riporta lo stack allo stato
di partenza senza ricostruirlo.

### Gli altri tre comandi

```bash
# Il carico: connessioni concorrenti, ritmo, latenze, tentativi del driver.
make app-workload TARGET=rs ARGS="--duration 20"

# La topologia mentre cambia: una riga per transizione, e i tempi veri.
make app-watch TARGET=rs ARGS="--duration 60"

# Le opzioni per esteso, senza accendere niente:
uv run --directory app mongolab --help
uv run --directory app mongolab stats --help
```

`ARGS` è la via per passare qualunque opzione alla CLI. Le due che ricorrono sono `--step`, che
mette una pausa fra un atto e l'altro perché dal palco si parla in mezzo, e `--sink plain`, che
stampa una riga per evento invece della resa grafica.

<a id="le-scene"></a>
## Le scene

Quattro scene già montate. Ognuna è un comando solo, e ognuna finisce dichiarando i numeri che ha
misurato — non li si legge da un log, li dice lei.

```bash
# L'Atto II: carico attivo, il primario cade, l'elezione, i due numeri.
make app-demo TARGET=rs ARGS="--step --sink plain"

# L'Atto III, che gira solo dall'host: il dump a caldo mentre il carico scrive.
make app-backup TARGET=rs ARGS="--step --sink plain"
make app-restore TARGET=rs ARGS="--step --sink plain"

# Il Blocco 3: lo stesso carico due volte, e la chiave di shard è l'unica differenza.
make app-sharding TARGET=sharded ARGS="--step --sink plain"
```

`app-backup` e `app-restore` accettano **solo** `TARGET=rs` e girano **solo dall'host**: `mongodump`
non è nell'immagine dell'applicazione, e il container non ha il socket del demone Docker. Il
bersaglio ci pensa da sé, non serve scrivere `DOVE`.

Accanto ci sono le tre scene dello sharded cluster, che non passano dall'applicazione ma da
`mongosh`:

```bash
make stato-03            # sh.status() e le righe che contano
make distribuzione-03    # dove stanno davvero i documenti, shard per shard
make guasto-03           # ferma il primario di uno shard e misura cosa risponde ancora (~40 s)
```

E le tre del replica set, che sono la stessa scena vista in tre modi:

```bash
make failover-02              # docker kill sul primario: ~10 s di elezione
make failover-02-termina      # il primario esce da sé: ~0,5 s
make failover-02-maggioranza  # due membri su tre giù: il superstite va in sola lettura
```

Le prime due vanno guardate **una dopo l'altra**: il punto non è nessuna delle due, è che il gesto
brutale costa dieci secondi e quello educato uno — il contrario di quello che ci si aspetta.

<a id="filmato"></a>
## Registrare un filmato

I filmati `.mp4` sono la riserva del talk e il materiale da allegare alla presentazione. Si girano
con un bersaglio, e le passate sono **due**:

```bash
make filmato NOME=02-failover-muto AUDIO=no   # prima il muto: si guarda
make filmato NOME=02-failover                 # poi con la voce: si racconta
```

Il file esce in `~/SqlStart2026-registrazioni` — la cartella che `make preflight` conta, e che si
sposta con `DEMO_VIDEOS_DIR`. Senza `DURATA` si registra finché non si preme **`q`**; con
`DURATA=120` si ferma da sé. Alla fine lo strumento rilegge il file e dice cosa contiene davvero,
tracce audio comprese: se hai chiesto la voce e la traccia non c'è, si ferma con un errore invece
di dire «fatto».

Si gira prima il muto perché una elezione dura i secondi che dura, non quelli che ci si ricorda:
guardarla prima è ciò che permette di raccontarla. E il muto non si butta — è il filmato da mettere
**dentro** le slide, dove una voce registrata sopra a quella di chi parla dal vivo dà fastidio
([ADR-0140](Decision.md#adr-0140)).

> **La prima volta serve `ffmpeg`** (`brew install ffmpeg`, l'unica installazione che questo
> repository chiede) **e due permessi di macOS**: «Registrazione schermo» e «Microfono». Concedere
> il secondo **fa ripartire il terminale**. Si fa adesso, non la sera prima del talk.

La procedura completa, con l'elenco delle scene da girare, sta nella
[pagina delle registrazioni](05-talk/registrazioni/README.md#filmati).

<a id="non-torna"></a>
## Quando qualcosa non torna

```bash
make preflight     # la macchina ce la fa? porte, memoria, immagini
make logs-02       # i log di uno stack, in coda
make docs-check    # ADR, fonti e collegamenti: non accende niente
make tools-test    # la suite degli strumenti di repository
make app-test      # la suite unitaria dell'applicazione, senza Docker
```

Gli ultimi tre girano su qualunque clone, anche senza Docker: sono il modo di verificare che il
repository sia sano prima ancora di avere una VM in piedi.

Per i guasti che capitano davvero — un `up` che riesce e un replica set che non c'è, un `smoke`
che fallisce sulla cache, un container che riparte da solo — la sede è il
[runbook della demo](05-talk/runbook-demo.md), che li elenca con il rimedio accanto, e le
[trappole di MongoDB in Docker](02-architetture/trappole-mongodb-in-docker.md), che spiegano
perché succedono.

---

**Dove andare adesso:** l'[indice della documentazione](README.md) per il quadro completo; le tre
architetture per capire cosa si è appena acceso —
[istanza singola](02-architetture/standalone.md), [replica set](02-architetture/replica-set.md),
[sharded cluster](02-architetture/sharded-cluster.md) — e il
[runbook](05-talk/runbook-demo.md) per l'esecuzione dal vivo.
