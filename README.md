# MongoDB: dalla singola istanza al cluster

Un laboratorio riproducibile che porta MongoDB dalla singola istanza al replica set allo
sharded cluster, tre stack Docker Compose sulla stessa macchina, più un'applicazione
Python che ne mostra il comportamento sotto guasto e sotto carico. È il materiale del talk
omonimo a **SqlStart 2026**, e resta consultabile per conto proprio da chi al talk non era.

Serve a chi amministra o sviluppa su MongoDB e vuole vedere, non sentir raccontare, cosa
cambia fra le tre architetture: chi risponde quando un nodo cade, cosa costa un backup a
caldo, come si comporta la latenza quando le connessioni concorrenti crescono.

## Il talk

**SqlStart 2026** — Ancona, venerdì 18 settembre 2026. Sessanta minuti, di cui circa metà
di dimostrazioni dal vivo.

Il repository è più esteso di quanto entri in un'ora, per scelta: i criteri di rinuncia
valgono per l'esecuzione dal palco, non per il materiale scritto. Chi c'era e vuole
approfondire trova qui proprio le parti che dal vivo sono state saltate.

## Cosa contiene

| Cartella | Contenuto | Stato |
|---|---|---|
| [`docs/`](docs/README.md) | tutta la documentazione: architetture, installazione, amministrazione, `mongosh`, decisioni e fonti | presente, con le sezioni mancanti dichiarate nell'[indice](docs/README.md) |
| `docker/` | i tre stack Compose, uno per architettura | tutti e tre nel repository: [`01-standalone`](docker/01-standalone/compose.yaml), [`02-replicaset`](docker/02-replicaset/compose.yaml), [`03-sharded`](docker/03-sharded/compose.yaml) |
| `app/` | l'applicazione dimostrativa in Python, `mongolab` | **nel repository**, con la sua documentazione in [`app/docs/`](app/docs/README.md) |
| `tools/` | strumenti di repository: preflight, pre-scaricamento delle immagini, prova end-to-end dello stack, e i tre controllori che verificano citazioni, file Compose e collegamenti | presente |

La tabella dice cosa il repository conterrà: quello che manca è dichiarato riga per riga,
invece di lasciarlo scoprire a chi clona.

Due file meritano una menzione a parte, perché sono il modo in cui questo materiale prova
quello che afferma:

- [`docs/Sources.md`](docs/Sources.md) — ogni fonte consultata con URL, versione
  documentata, data, un verdetto su cosa la pagina afferma davvero e le **riserve**, cioè
  il punto in cui smette di coprirci. Nessuna affermazione tecnica entra nella
  documentazione senza un riferimento qui.
- [`docs/Decision.md`](docs/Decision.md) — le decisioni architetturali in ordine
  cronologico, con contesto, conseguenze e alternative scartate. Le decisioni superate
  restano, con il rimando a quella che le sostituisce.

Il legame fra le due è verificato da un controllo automatico che fallisce se un ADR cita
una fonte inesistente o se una fonte non è citata da nessuno.

## Stato di avanzamento

Il repository è in costruzione fino a metà settembre 2026. Questo è quello che c'è oggi:

| Stack | Stato | Branch |
|---|---|---|
| `docker/01-standalone` | **nel repository** | `feature/01-stack-standalone` |
| `docker/02-replicaset` | **nel repository** | `feature/02-stack-replicaset` |
| `docker/03-sharded` | **nel repository** | `feature/03-stack-sharded` |

L'applicazione Python `mongolab` è in `app/`, sviluppata su `feature/04-app-python`:
genera carico, osserva la topologia mentre cambia, e mette in scena il failover, il backup a
caldo e il ripristino. Ogni comando ha un bersaglio nel `Makefile` — `make app-stats`, `app-watch`,
`app-workload` e le quattro scene: `app-demo` (failover), `app-backup`, `app-restore`,
`app-sharding` ([ADR-0120](docs/Decision.md#adr-0120)). `make help` li elenca con le variabili che
accettano; le opzioni per esteso le dà `mongolab --help`. La sua documentazione sta in [`app/docs/`](app/docs/README.md), e
[`docs/06-sviluppo/architettura-app.md`](docs/06-sviluppo/architettura-app.md) la racconta a
chi non aprirà i sorgenti.

Le sezioni della documentazione non ancora scritte sono elencate
nell'[indice](docs/README.md) con la feature che le produrrà.

## Requisiti

- **Docker Desktop** o un runtime equivalente che fornisca `docker compose`. Gli stack sono
  stati sviluppati con Docker 29.7.2 e Compose v5.4.0.
- **RAM.** Lo standalone, il replica set e il profilo `palco` dello sharded cluster stanno
  in 4 GiB assegnati al runtime. Il profilo `completo` — tre membri per ogni componente,
  undici container — ne vuole 12 assegnati alla VM Docker, su un host che ne abbia 16
  [ADR-0025](docs/Decision.md#adr-0025). È il motivo per cui lo stack sharded ha due
  profili invece di uno: il primo entra ovunque, il secondo mostra l'architettura vera.
- **`make`** per i comandi di uso quotidiano, e **[`uv`](https://docs.astral.sh/uv/)** per
  eseguire gli strumenti Python senza installare nulla a mano.

## Avvio rapido

Su un clone appena fatto, l'istanza singola parte senza premesse:

```bash
git clone https://github.com/giulianolatini/SqlStart2026.git
cd SqlStart2026

# Scarica le immagini e le pinna per digest: è l'unico comando che vuole rete.
make images-pull

# Avvia l'istanza singola e attende che il container sia sano.
make up-01

# Dodici controlli end-to-end sullo stack avviato.
make smoke-01

# Ferma lo stack conservando i dati nel volume.
make down-01
```

Dopo `make images-pull` lo stack parte anche con la rete staccata, che è il motivo per cui
le immagini sono pinnate per digest ([ADR-0018](docs/Decision.md#adr-0018)). Cosa fa ognuno
di quei comandi, e cosa succede dentro il container mentre li esegui, sta nella pagina
sull'[istanza singola](docs/02-architetture/standalone.md); `make help` elenca gli altri
target.

### Dal secondo stack in poi serve un file che il repository non contiene

L'istanza singola non ha utenti, quindi non ha password. Il replica set sì, e lo sharded
cluster pure: sono **due file distinti**, uno per stack, con la stessa riga da riempire. Quella
password **non è nel repository e non ci sarà mai**:
`.env.example` è versionato e porta un segnaposto vuoto, `.env` è ignorato da git e porta il
valore ([ADR-0040](docs/Decision.md#adr-0040)). È il motivo per cui il file non si può
scaricare insieme al resto: va creato una volta, sulla propria macchina.

```bash
cp docker/02-replicaset/.env.example docker/02-replicaset/.env
cp docker/03-sharded/.env.example docker/03-sharded/.env
# poi aprire i file e scrivere la password dopo «PASSWORD_AMMINISTRATORE=»
```

Sono credenziali da **laboratorio**, su uno stack che non va esposto fuori dalla macchina di
chi lo esegue: una password semplice va benissimo. Quello che non va bene è che stia in un
file versionato, dove sopravvive alla demo e viene copiata altrove insieme al resto.

Chi salta il passo non rompe niente e non resta senza indizi: `make up-02` e `make up-03` si
fermano prima di toccare Docker e stampano quale file manca e come crearlo, invece di lasciare a
Compose un «env file not found» che non spiega perché quel file non c'è. Il resto di `.env.example` ha già i
valori del lab: **l'unica riga da riempire è la password**.

Fatto quello, il replica set si accende come l'istanza singola:

```bash
make up-02     # due comandi in uno: il secondo attende che la replica esista davvero
make smoke-02  # quarantadue controlli end-to-end
make down-02   # ferma conservando i dati e il keyfile
```

Senza avviare niente, quello che si può eseguire su qualunque clone è l'impianto
documentale:

```bash
# Verifica che ogni ADR citi fonti esistenti, che nessuna fonte sia orfana
# e che nessun rimando fra le pagine sia rotto.
make docs-check

# Esegue la suite degli strumenti di repository.
make tools-test
```

Entrambi scaricano le dipendenze di sviluppo alla prima esecuzione, quindi vogliono rete
una volta sola.

## Licenza

[GPL-3.0](LICENSE). Il materiale è pensato per essere riusato: se lo porti in aula o in
azienda, la licenza chiede solo che resti libero.
