# Fonti

Registro delle fonti consultate. Ogni affermazione tecnica in `docs/` cita almeno una voce
di questo file; ogni voce di questo file è citata da almeno un ADR di
[`Decision.md`](Decision.md). Il vincolo è verificato da `tools/check_citations.py`.

| Prefisso | Tipo |
|---|---|
| `S-NNN` | fonte ufficiale — URL, editore, versione documentata, data di consultazione |
| `V-NNN` | verifica empirica su questo lab — comando eseguito, output osservato, data |
| `C-NNN` | fonte comunitaria — indizio, mai unica base di una decisione |

## Come sono state verificate

Ogni URL è stato aperto e letto integralmente il **2026-08-25**, salvo le voci aggiunte in
seguito, che portano la propria data nel campo **Consultata**. Per ciascuna fonte è
registrato un **verdetto** su ciò che la pagina afferma davvero, confrontato con
l'assunzione che avevamo dato per buona in fase di progettazione:

| Verdetto | Significato |
|---|---|
| conferma | la pagina dice quello che assumevamo, alla lettera |
| conferma parziale | una parte è confermata, il resto non è scritto o è scritto diversamente |
| non trovato | la pagina non tratta l'argomento: l'assunzione non è né confermata né smentita |
| contraddice | la pagina afferma qualcosa di incompatibile con l'assunzione |

Il campo **Riserve** esiste perché una fonte serve a poco se non si sa dove smette di
coprirci. Quando una riserva è presente, l'affermazione corrispondente non va portata sul
palco come citazione: o si riformula, o si sostiene con una verifica empirica `V-NNN`.

Due note di metodo utili a chi ripete la verifica:

- **`mongodb.com/docs` serve una variante Markdown della stessa pagina**, allo stesso URL
  con suffisso `.md` (per esempio `core/wiredtiger.md`). La resa HTML recuperata da
  strumenti automatici risultava in più casi compressa, con parole funzione mancanti: non
  utilizzabile per citare alla lettera. Tutte le citazioni qui sotto provengono dalla
  variante Markdown quando indicato.
- **`docs.docker.com` fa lo stesso**, ed è l'endpoint dietro il pulsante «View Markdown»
  delle sue pagine.

## Assunzioni di progetto non confermate dalle fonti

Sintesi di ciò che la verifica ha smontato. Il dettaglio è nella voce indicata.

| Assunzione iniziale | Esito | Voce |
|---|---|---|
| Cache WiredTiger a `0.25` GB | il minimo documentato è `0.256 GB` | [S-002](#s-002) |
| In container mongod legge il limite del cgroup | la pagina corrente dice l'opposto, e due pagine ufficiali si contraddicono | [S-001](#s-001), [S-026](#s-026) |
| `deploy.resources.limits` è ignorato fuori da Swarm | non documentato in nessuna direzione: la frase storica è stata ritirata | [S-004](#s-004) |
| Il digest garantisce il funzionamento offline | il digest garantisce *quale* immagine, non *se* si va in rete | [S-019](#s-019) |
| `testcontainers-python` copre i replica set | `MongoDbContainer` avvia solo istanze standalone | [S-013](#s-013) |
| I listener pymongo girano su un thread separato | sono consegnati **sincronamente** e bloccano il chiamante | [S-010](#s-010) |
| Rich documenta vincoli di thread su `Live` | la parola «thread» non compare nella documentazione | [S-018](#s-018) |
| L'eccezione localhost vale solo da loopback | vero per convenzione, ma non enunciato da alcuna fonte primaria | [S-006](#s-006) |
| Il keyfile ammette `600` | documentato solo `chmod 400` | [S-005](#s-005) |

---

## Fonti ufficiali

<a id="s-001"></a>
### S-001 — MongoDB Manual: WiredTiger Storage Engine

- **URL:** https://www.mongodb.com/docs/manual/core/wiredtiger/ (citazioni dalla variante `core/wiredtiger.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** Database Manual 8.3 (Current)
- **Consultata:** 2026-08-25
- **Verdetto:** conferma parziale
- **Cosa afferma:** la dimensione predefinita della cache interna è «the larger of either:
  50% of (RAM - 1GB), or 0.256 GB», con estremi dichiarati «ensure the RAM does not exceed
  the bounds of 0.256GB to 10000GB». Sui container prescrive di impostarla a mano: «If you
  run `mongod` in a container (for example, `lxc`, `cgroups`, Docker, etc.) that does *not*
  have access to all of the RAM available in a system, you **must** set
  `--wiredTigerCacheSizeGB` or `--wiredTigerCacheSizePct` to a value less than the amount
  of RAM available in the container».
- **Riserve:** la pagina **non** afferma che mongod legga il limite del cgroup. Afferma il
  contrario: «WiredTiger may not account for the memory limits of the specific container in
  certain cases». Contraddice [S-026](#s-026), che è sullo stesso manuale. Il manuale
  archiviato v5.0 era invece affermativo e scriveva `256 MB` anziché `0.256 GB`: la
  formulazione è stata **indebolita** fra la 5.0 e la 8.3. Nessun marcatore di versione
  («Starting in MongoDB 3.4/5.0») è associato alla formula: l'attribuzione di versione che
  davamo per nota **non esiste** nel testo.
- **Usata da:** ADR-0004, ADR-0025

<a id="s-002"></a>
### S-002 — MongoDB Manual: `mongod` Instances

- **URL:** https://www.mongodb.com/docs/manual/reference/program/mongod/ (citazioni dalla variante `mongod.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** manuale 8.x (marcatori interni «Changed in version 6.1», «Starting in MongoDB 8.0»)
- **Consultata:** 2026-08-25
- **Verdetto:** contraddice
- **Cosa afferma:** «Avoid increasing the WiredTiger internal cache size above its default
  value. If your use case requires to do so, you can use `--wiredTigerCacheSizePct` to
  specify a percentage of up to 80% of available memory. **Values can range from 0.256GB to
  10000GB.**» La stessa pagina documenta inoltre, per l'autenticazione interna:
  «`--keyFile` implies `--auth`».
- **Riserve:** il valore `0.25` che il progetto aveva scelto per la cache **è sotto il
  minimo dichiarato**. Onestà sulla forza della fonte: la frase compare dentro la voce
  `--wiredTigerCacheSizeGB` ma in un periodo che parla di `--wiredTigerCacheSizePct`, quindi
  non è sintatticamente certo che il minimo sia normativo per l'opzione in GB — ragione in
  più per la verifica empirica. Il tipo dell'opzione (intero o frazionario) e il suo default
  non sono pubblicati: la pagina `reference/configuration-options` viene servita troncata
  prima delle Storage Options.
- **Usata da:** ADR-0004, ADR-0005

<a id="s-003"></a>
### S-003 — Docker Docs: Define services in Docker Compose

- **URL:** https://docs.docker.com/reference/compose-file/services/
- **Editore:** Docker Inc. — Docker Docs
- **Versione documentata:** Compose Specification (nessun numero di versione sulla pagina)
- **Consultata:** 2026-08-25
- **Verdetto:** conferma parziale
- **Cosa afferma:** «`mem_limit` configures a limit on the amount of memory a container can
  allocate, set as a string expressing a byte value»; «`cpus` define the number of
  (potentially virtual) CPUs to allocate to service containers. This is a fractional number.
  `0.000` means no limit». Le unità ammesse sono `b`, `k`/`kb`, `m`/`mb`, `g`/`gb`. Sul
  reperimento dell'immagine: «If the image does not exist on the platform, Compose attempts
  to pull it based on the `pull_policy`». Il digest è una forma valida di riferimento:
  «must follow the OCI addressable image format, as
  `[<registry>/][<project>/]<image>[:<tag>|@<digest>]`».
- **Riserve:** due punti che davamo per acquisiti non sono scritti. Primo, la pagina **non
  dice** che questi attributi siano applicati da `docker compose` fuori da Swarm: la parola
  «Swarm» compare una sola volta nell'intera pagina, a proposito di `ports.mode`. Secondo, e
  controintuitivo, la documentazione **non** presenta la sintassi breve come alternativa a
  `deploy`, ma ne impone la coerenza: «When set, `mem_limit` must be consistent with the
  `limits.memory` attribute in the Deploy Specification». La narrazione «usa `mem_limit`
  *invece di* `deploy`» non è sostenuta dalla fonte. Nota favorevole: nessun marcatore di
  deprecazione su `mem_limit` o `cpus` — l'ipotesi che fossero attributi legacy è falsa.
- **Usata da:** ADR-0004, ADR-0013, ADR-0018

<a id="s-004"></a>
### S-004 — Docker Docs: Compose Deploy Specification

- **URL:** https://docs.docker.com/reference/compose-file/deploy/
- **Editore:** Docker Inc. — Docker Docs
- **Versione documentata:** nessuna indicata
- **Consultata:** 2026-08-25
- **Verdetto:** non trovato
- **Cosa afferma:** «Deploy is an optional part of the Compose Specification. It provides a
  set of deployment specifications for managing the behavior of containers across different
  environments.» I vincoli sono espressi in termini astratti di piattaforma: «`limits`: The
  platform must prevent the container from allocating more resources.»
- **Riserve:** è il risultato più importante della verifica su Docker. Nel corpo
  dell'articolo (303 righe di sorgente Markdown) i termini «Swarm», «ignored», «not
  supported» e «docker compose up» hanno **zero occorrenze**; le occorrenze di «swarm»
  nell'HTML stanno tutte nella barra di navigazione. Non esiste alcun elenco di attributi
  `deploy` ignorati fuori da Swarm. La frase storica che lo affermava apparteneva al
  riferimento del formato v3, oggi ritirato: «The legacy versions of the Compose file
  reference has moved to the V1 branch of the Compose repository. They are no longer being
  actively maintained.» Conseguenza: **la documentazione odierna non conferma né smentisce**
  che i limiti sotto `deploy` siano applicati da `docker compose up`. Qualunque affermazione
  in merito va presentata come verifica empirica — `docker inspect` sui campi
  `HostConfig.Memory` e `HostConfig.NanoCpus` — non come citazione.
- **Usata da:** ADR-0013

<a id="s-005"></a>
### S-005 — MongoDB Manual: Deploy Self-Managed Replica Set With Keyfile Authentication

- **URL:** https://www.mongodb.com/docs/manual/tutorial/deploy-replica-set-with-keyfile-access-control/
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** Self-Managed Deployments 8.3 (Current)
- **Consultata:** 2026-08-25
- **Verdetto:** conferma parziale
- **Cosa afferma:** «On UNIX systems, the keyfile must not have group or world permissions.
  On Windows systems, keyfile permissions are not checked.» e «Ensure that the user running
  the `mongod` instances is the owner of the file and can access the keyfile». Sulla chiave:
  «A key's length must be between 6 and 1024 characters and may only contain characters in
  the base64 set. All members of the replica set must share at least one common key»,
  generata con `openssl rand -base64 756 > <path-to-keyfile>`. L'esecuzione con `--keyFile`
  «enforces both Self-Managed Internal/Membership Authentication and Role-Based Access
  Control».
- **Riserve:** l'esempio ufficiale usa **solo** `chmod 400`; `600` non compare in nessun
  punto. Dire «400 o 600» è una deduzione corretta ma non una citazione. Anche
  l'affermazione «altrimenti mongod rifiuta di avviarsi» **non è scritta**: la pagina pone
  il requisito ma non descrive il comportamento in caso di violazione, e su Windows dichiara
  che i permessi non vengono controllati affatto. Avvertenza da anticipare al pubblico:
  «Use keyfiles only for testing and development environments because of their limited
  manageability and cryptographic strength. For production environments, use X.509
  certificates».
- **Usata da:** ADR-0005, ADR-0014

<a id="s-006"></a>
### S-006 — MongoDB Manual: Localhost Exception in Self-Managed Deployments

- **URL:** https://www.mongodb.com/docs/manual/core/localhost-exception/ (citazioni dalla variante `localhost-exception.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** Self-Managed Deployments 8.3 (Current)
- **Consultata:** 2026-08-25
- **Verdetto:** conferma parziale
- **Cosa afferma:** «On a `mongod` instance, the localhost exception only applies when there
  are **no users or roles** created in the MongoDB instance», e decade con «Run the
  `createUser` command or `db.createUser()` method. This ends the localhost exception». In
  cluster sharded: «In a sharded cluster, the localhost exception applies to each shard
  individually as well as to the cluster as a whole», con l'obbligo di impedire comunque
  l'accesso non autorizzato ai singoli shard. Operazioni ammesse sotto eccezione:
  `createUser`, `createRole`, `grantRole` verso sistemi esterni, `replSetInitiate`,
  `replSetGetStatus`, `replSetReconfig`, e su mongos `addShard` «if the cluster is hosted on
  `localhost`».
- **Riserve:** il vincolo che tutti danno per ovvio — la connessione deve arrivare da
  `127.0.0.1`/`::1` — **non è enunciato in nessuna fonte primaria trovata**. Le stringhe
  `127.0.0.1`, `::1`, «loopback», «same host» non compaiono nella pagina letta
  integralmente, né nella voce `enableLocalhostAuthBypass` di `reference/parameters`. Se lo
  si afferma, va qualificato come comportamento noto, non come citazione. Correzione
  all'assunzione di progetto: l'eccezione decade anche con `createRole`, e non si attiva
  affatto se esiste già un ruolo — perimetro più stretto di quello che avevamo scritto. I
  config server non sono menzionati.
- **Usata da:** ADR-0005

<a id="s-007"></a>
### S-007 — MongoDB Manual: Connection String Options

- **URL:** https://www.mongodb.com/docs/manual/reference/connection-string-options/
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** Database Manual 8.3 (Current)
- **Consultata:** 2026-08-25
- **Verdetto:** conferma parziale
- **Cosa afferma:** su `directConnection` — «Specifies whether the client connects directly
  to the `host[:port]` in the connection URI: `true`: The client sends operations only to
  the specified host and does not attempt to discover other replica set members.; `false`:
  The client attempts to discover all servers in the replica set, and sends operations to
  the primary member. This is the default value.» Su `replicaSet`: «When connecting to a
  replica set, provide a seed list of the replica set members in the `host[:port]`
  component.» La pagina contiene un avviso specifico per Docker, che descrive esattamente la
  trappola del nostro lab: «When a replica set runs in Docker, it might expose only one
  MongoDB endpoint. In this case, the replica set is not discoverable, and specifying
  `directConnection=false` can prevent your application from connecting to it. In a test or
  development environment, you can connect to the replica set by specifying
  `directConnection=true` in your connection URI. In a production environment, we recommend
  configuring the cluster to make each MongoDB instance accessible outside of the Docker
  virtual network.»
- **Riserve:** l'URL che il progetto citava, `reference/connection-string/`, **non contiene
  più** la descrizione delle opzioni: è diventato una pagina di ingresso con selettore. Chi
  fosse andato a verificare non avrebbe trovato nulla. Inoltre la pagina dice «attempts to
  discover all servers in the replica set» ma **non** dice che il driver usi i nomi host
  memorizzati nella configurazione del replica set: il meccanismo — la risposta a `hello`
  che restituisce `members[n].host` — non è enunciato qui.
- **Usata da:** ADR-0012

<a id="s-008"></a>
### S-008 — MongoDB Manual: Sharded Cluster Components

- **URL:** https://www.mongodb.com/docs/manual/core/sharded-cluster-components/
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** Database Manual 8.3 (Current)
- **Consultata:** 2026-08-25
- **Verdetto:** conferma
- **Cosa afferma:** «shard: Each shard contains a subset of the sharded data. **Each shard
  must be deployed as a replica set.**» e «config servers: Config servers store metadata and
  configuration settings for the cluster. **Config servers must be deployed as a replica set
  (CSRS).**» Sul numero minimo: «Sharding requires at least two shards to distribute sharded
  data.» Novità 8.0 utile a un lab con poca RAM: «A cluster requires a config server, but it
  can be a config shard instead of a dedicated config server. Using a config shard reduces
  the number of nodes required and can simplify your deployment.» Avvertenza: «Use the test
  cluster architecture for testing and development only.»
- **Riserve:** questa pagina **non dice nulla** sui replica set a un solo membro — non
  nomina mai «single-member». La sezione «Development Configuration» elenca «A single shard
  replica set», dove «single shard» significa *un solo shard*, non *un solo membro*. La
  risposta esiste ed è favorevole al lab, ma sta su [S-024](#s-024): è quella la fonte da
  citare.
- **Usata da:** ADR-0010

<a id="s-009"></a>
### S-009 — Docker Hub: immagine ufficiale `mongo`

- **URL:** https://hub.docker.com/_/mongo (testo mantenuto in `docker-library/docs`, directory `mongo/`)
- **Editore:** Docker, Inc. — Docker Official Images
- **Versione documentata:** snapshot al 2026-08-25; tag `8.0.29`/`8.0` su base Ubuntu Noble
- **Consultata:** 2026-08-25
- **Verdetto:** conferma parziale
- **Cosa afferma:** «These variables, used in conjunction, create a new user and set that
  user's password. This user is created in the `admin` authentication database and given the
  role of `root`, which is a "superuser" role.» Sull'inizializzazione: «Do note that none of
  the variables below will have any effect if you start the container with a data directory
  that already contains a database» e «When a container is started for the first time it
  will execute files with extensions `.sh` and `.js` that are found in
  `/docker-entrypoint-initdb.d`». Architetture dichiarate: «Supported architectures:
  `amd64`, `arm64v8`, `windows-amd64`» — la presenza di `linux/arm64/v8` nel manifest del tag
  `8.0` è stata confermata sull'API di Docker Hub.
- **Riserve:** la pagina **non copre il punto che ci serve davvero**. Né `--replSet` né
  `--keyFile` vi compaiono: la replicazione è liquidata con un rimando al manuale. Non
  descrive la fase di mongod temporaneo — la parola «temporary» è assente — e non pubblica
  UID e GID. Per questi tre punti si vedano [S-022](#s-022) e [S-023](#s-023), che sono
  **codice sorgente, non prosa documentale**: vanno citati come tali.
- **Usata da:** ADR-0008

<a id="s-010"></a>
### S-010 — PyMongo: `monitoring` — Tools for monitoring driver events

- **URL:** https://pymongo.readthedocs.io/en/stable/api/pymongo/monitoring.html
- **Editore:** MongoDB, Inc. — documentazione PyMongo su Read the Docs
- **Versione documentata:** PyMongo 4.17.0
- **Consultata:** 2026-08-25
- **Verdetto:** conferma
- **Cosa afferma:** cinque classi astratte di listener — `CommandListener`, `ServerListener`,
  `ServerHeartbeatListener`, `TopologyListener`, `ConnectionPoolListener` — registrabili
  globalmente o per singolo client: «Use `register()` to register global listeners for
  specific events», con la forma per client `MongoClient(event_listeners=[CommandLogger()])`.
  Gli eventi che servono a cronometrare un failover: `ServerDescriptionChangedEvent`
  («Published when server description changes»), `ServerHeartbeatFailedEvent` — il momento in
  cui il client si accorge della caduta — e `TopologyDescriptionChangedEvent` («Published
  when the topology description changes»). Tutte le classi sono «Added in version 3.3».
- **Riserve:** la documentazione afferma **l'opposto** di quanto il progetto assumeva sui
  thread: «Events are delivered synchronously. Application threads block waiting for event
  handlers (e.g. `started()`) to return. Care must be taken to ensure that your event
  handlers are efficient enough to not adversely affect overall application performance.» Un
  handler lento non rallenta solo la UI: rallenta il driver, e falsa proprio le misure di
  failover che la demo vuole mostrare. Ulteriore avvertenza se si registrano i comandi: «The
  command documents published through this API are not copies.»
- **Usata da:** ADR-0006, ADR-0019

<a id="s-011"></a>
### S-011 — MongoDB Database Tools: `mongodump`

- **URL:** https://www.mongodb.com/docs/database-tools/mongodump/
- **Editore:** MongoDB, Inc. — MongoDB Database Tools (prodotto distinto dal server)
- **Versione documentata:** Database Tools ≥ 100.18.0 (marcatori interni «New in version 100.3.0», «Starting in Database Tools 100.18.0»)
- **Consultata:** 2026-08-25
- **Verdetto:** conferma
- **Cosa afferma:** `--oplog` «Creates a file named `oplog.bson` as part of the `mongodump`
  output. The `oplog.bson` file, located in the top level of the output directory, contains
  oplog entries that occur during the `mongodump` operation.» Ambito: «`--oplog` only works
  against nodes that maintain an oplog. This includes all members of a replica set», e il
  divieto netto «**You can't run `mongodump` with `--oplog` on a sharded cluster.**» Senza
  l'opzione: «if there are write operations during the dump operation, the dump will not
  reflect a single moment in time». `--readPreference=secondary` permette di scaricare da un
  secondario, e «the command-line `--readPreference` overrides the read preference specified
  in the URI string».
- **Riserve:** limitazione operativa che condiziona il copione della demo: `--oplog`
  **fallisce** se combinato con `--db`, `--collection`, `--dumpDbUsersAndRoles` o `--query`
  — «To use `mongodump` with `--oplog`, you must create a full dump of a replica set
  member» — e fallisce se durante il dump un client esegue `renameCollection`, `$out`,
  `mapReduce`, operazioni su utenti o ruoli, o `setDefaultRWConcern`. Le espressioni «point
  in time» e «does not guarantee» non compaiono: il paradosso dello standalone — senza oplog
  `--oplog` non è utilizzabile, quindi il dump non può essere coerente a un istante — è vero
  ma **non è scritto**.
- **Usata da:** ADR-0022

<a id="s-012"></a>
### S-012 — Docker Docs: `depends_on`

- **URL:** https://docs.docker.com/reference/compose-file/services/#depends_on
- **Editore:** Docker Inc. — Docker Docs
- **Versione documentata:** Compose Specification; i singoli attributi sono datati alle release Compose 2.17.0 e 2.20.0
- **Consultata:** 2026-08-25
- **Verdetto:** conferma
- **Cosa afferma:** la forma lunga ammette esattamente tre condizioni — `service_started`
  («An equivalent of the short syntax described previously»), `service_healthy`
  («Specifies that a dependency is expected to be "healthy" (as indicated by `healthcheck`)
  before starting a dependent service») e `service_completed_successfully` («Specifies that
  a dependency is expected to run to successful completion before starting a dependent
  service»). Il contrasto fra le due forme è esplicito e citabile: «With short syntax,
  Compose does not wait for dependency services to be "healthy" before starting a dependent
  service» contro «Compose waits for healthchecks to pass on dependencies marked with
  `service_healthy`». Esistono inoltre `restart` (booleano, Compose 2.17.0) e `required`
  («When set to `false` Compose only warns you when the dependency service isn't started or
  available», default `true`, Compose 2.20.0).
- **Riserve:** nessuna. È l'unica fonte Docker confermata senza riserve.
- **Usata da:** ADR-0023

<a id="s-013"></a>
### S-013 — testcontainers-python

- **URL:** https://testcontainers-python.readthedocs.io/en/latest/ e https://testcontainers-python.readthedocs.io/en/latest/modules/mongodb/README.html
- **Editore:** Sergey Pirogov e i contributori Testcontainers Python, su Read the Docs
- **Versione documentata:** testcontainers 2.0.0
- **Consultata:** 2026-08-25
- **Verdetto:** contraddice
- **Cosa afferma:** «class `MongoDbContainer`(image: str = 'mongo:latest', port: int = 27017,
  username: str | None = None, password: str | None = None, dbname: str | None = None,
  **kwargs) — Mongo document-based database container.» I parametri sono esattamente questi
  cinque.
- **Riserve:** il modulo **non supporta i replica set**. Le stringhe «replica», «replSet» e
  «rs.initiate» non compaiono in nessun punto della pagina, e il sorgente
  (`src/testcontainers/community/mongodb/__init__.py`) imposta solo
  `MONGO_INITDB_ROOT_USERNAME`, `MONGO_INITDB_ROOT_PASSWORD` e `MONGO_DB`, attendendo la
  stringa di log `waiting for connections`: **avvia un'istanza standalone**. Per una demo di
  failover il componente non serve. L'alternativa interna alla libreria, la classe
  `DockerCompose`, **esiste nel codice** (`src/testcontainers/compose/compose.py`) ma ha zero
  occorrenze nell'indice, nella pagina Core e nel `genindex` della documentazione
  pubblicata: costruirci sopra significa dipendere da un'API non documentata. Aggravante: il
  sito Read the Docs descrive un layout di pacchetti superato rispetto al repository, che
  punta a un nuovo sito `python.testcontainers.org` non ancora raggiungibile alla data di
  consultazione. Il vecchio percorso `testcontainers.mongodb` è già uno shim che avverte
  «testcontainers.mongodb is deprecated, use testcontainers.community.mongodb instead».
- **Usata da:** ADR-0011, ADR-0020

<a id="s-014"></a>
### S-014 — MongoDB Resources: Come configurare un cluster MongoDB

- **URL:** https://www.mongodb.com/it-it/resources/products/fundamentals/mongodb-cluster-setup
- **Editore:** MongoDB, Inc. — sezione `/resources/products/fundamentals/`, **non** `/docs/`
- **Versione documentata:** nessuna. Pagina senza numero di versione e senza data di pubblicazione o aggiornamento
- **Consultata:** 2026-08-25
- **Verdetto:** conferma parziale
- **Cosa afferma:** «Un replica set di MongoDB è un gruppo di uno o più server che contiene
  una copia esatta dei dati. Sebbene sia tecnicamente possibile avere uno o due nodi, il
  minimo consigliato è tre.» Introduce i due significati di «cluster», poi passa quasi
  interamente alla creazione di un cluster su MongoDB Atlas.
- **Riserve:** **non è utilizzabile come riferimento normativo.** È materiale divulgativo:
  nessun comando, nessun file di configurazione, nessun esempio di codice; l'unica procedura
  è un percorso di clic a cinque passi nella interfaccia di Atlas, fra due inviti alla prova
  gratuita. Senza versione e senza data, non può sostenere affermazioni versionate. Resta
  utile come **raccolta di collegamenti** verso il manuale, dove risiedono le affermazioni
  citabili. La frase sul minimo di tre nodi è coerente con [S-008](#s-008), ma se qualcuno
  dal pubblico contesta il replica set a nodo singolo la difesa va costruita su
  [S-024](#s-024), non su questa pagina.
- **Usata da:** ADR-0024

<a id="s-015"></a>
### S-015 — Docker Docs: Using profiles with Compose

- **URL:** https://docs.docker.com/compose/how-tos/profiles/
- **Editore:** Docker Inc. — Docker Docs
- **Versione documentata:** nessuna indicata
- **Consultata:** 2026-08-25
- **Verdetto:** conferma
- **Cosa afferma:** «Services without a `profiles` attribute are always enabled.»
  L'attivazione avviene con «the `--profile` command-line option or [...] the
  `COMPOSE_PROFILES` environment variable»; «If you want to enable all profiles at the same
  time, you can run `docker compose --profile "*"`». Un servizio con profilo può essere
  avviato nominandolo esplicitamente: «When you explicitly target a service on the command
  line that has one or more profiles assigned, you do not need to enable the profile manually
  as Compose runs that service regardless of whether its profile is activated», e in tal caso
  «Only the targeted service (and any of its declared dependencies via `depends_on`) is
  started». I nomi dei profili seguono «the regex format of `[a-zA-Z0-9][a-zA-Z0-9_.-]+`».
- **Riserve:** la documentazione copre **una sola direzione** della relazione con
  `depends_on`: servizio con profilo → sue dipendenze. Il caso inverso — un servizio *senza*
  profilo che dichiara `depends_on` verso un servizio *con* profilo non attivo — non è
  trattato né qui né nella voce `profiles` del riferimento dei servizi. Se il lab vi si
  appoggia, va verificato empiricamente e non citato come documentato.
- **Usata da:** ADR-0010

<a id="s-016"></a>
### S-016 — Docker Docs: Version and name top-level elements

- **URL:** https://docs.docker.com/reference/compose-file/version-and-name/
- **Editore:** Docker Inc. — Docker Docs
- **Versione documentata:** Compose Specification
- **Consultata:** 2026-08-25
- **Verdetto:** conferma
- **Cosa afferma:** il titolo di sezione è «Version top-level element (**obsolete**)», e
  l'avviso è esplicito: «The top-level `version` property is defined by the Compose
  Specification for backward compatibility. It is only informative and you'll receive a
  warning message that it is obsolete if used.» Inoltre: «Compose always uses the most recent
  schema to validate the Compose file, regardless of the `version` field.»
- **Riserve:** l'URL che il progetto citava, `reference/compose-file/`, è una pagina indice
  di ventitré righe che **non nomina mai** la chiave `version`: l'assunzione non vi era
  verificabile. Correzione terminologica per le slide: la documentazione dice «obsolete», non
  «deprecated», e dice «only informative» più «warning message», non «ignored». La resa
  fedele è «obsoleto, puramente informativo, produce un avviso; lo schema di validazione
  usato è comunque il più recente».
- **Usata da:** ADR-0001

<a id="s-017"></a>
### S-017 — Docker Docs: Specify a project name

- **URL:** https://docs.docker.com/compose/how-tos/project-name/
- **Editore:** Docker Inc. — Docker Docs
- **Versione documentata:** nessuna indicata
- **Consultata:** 2026-08-25
- **Verdetto:** conferma parziale
- **Cosa afferma:** «Compose uses a project name to isolate environments from each other», e
  fra i casi d'uso «On a shared or development host: Avoid interference between different
  projects that might share the same service names». La precedenza è enumerata: «The
  precedence order for each method, from highest to lowest, is as follows: 1. The `-p`
  command line flag. 2. The COMPOSE_PROJECT_NAME environment variable. 3. The top-level
  `name:` attribute in your Compose file [...] 4. The base name of the project directory
  containing your Compose file [...] 5. The base name of the current directory if no Compose
  file is specified.» Vincolo sui nomi: «Project names must contain only lowercase letters,
  decimal digits, dashes, and underscores, and must begin with a lowercase letter or decimal
  digit.»
- **Riserve:** la pagina **non enumera mai** reti, volumi e container come le risorse
  isolate: dice genericamente «isolate environments from each other». L'affermazione «isola
  reti, volumi e container», che il progetto dava per acquisita, è più specifica di quanto la
  fonte sostenga. Inoltre i livelli di precedenza sono **cinque**, non quattro.
- **Usata da:** ADR-0003

<a id="s-018"></a>
### S-018 — Rich: Live Display

- **URL:** https://rich.readthedocs.io/en/stable/live.html
- **Editore:** Will McGugan / Textualize, su Read the Docs
- **Versione documentata:** Rich 14.1.0
- **Consultata:** 2026-08-25
- **Verdetto:** conferma parziale
- **Cosa afferma:** «By default, the live display will refresh 4 times a second. You can set
  the refresh rate with the `refresh_per_second` argument on the Live constructor», con la
  raccomandazione «You should set this to something lower than 4 if you know your updates
  will not be that frequent or higher for a smoother feeling». Stampare mentre il display è
  attivo è previsto, in due modi: «The Live class will create an internal Console object
  which you can access via `live.console`. If you print or log to this console, the output
  will be displayed above the live display», e «To avoid breaking the live display visuals,
  Rich will redirect `stdout` and `stderr` so that you can use the builtin `print`
  statement». Sul nidificare due display: «If you create a `Live` instance within the context
  of an existing `Live` instance, then the content of the inner `Live` will be displayed
  below the outer `Live`. Prior to version 14.0.0 this would have resulted in a `LiveError`
  exception.»
- **Riserve:** l'assunzione di progetto sui vincoli di thread è **infondata**: la parola
  «thread» non compare **nemmeno una volta**, né in questa pagina né nell'API reference
  `reference/live.html`; non compaiono neppure «concurrent» o «lock». Non esiste alcuna
  avvertenza documentata sull'aggiornamento di `Live` da più thread, né in un senso né
  nell'altro. Se la domanda arriva dal pubblico, la risposta onesta è che la documentazione
  tace.
- **Usata da:** ADR-0007, ADR-0019

<a id="s-019"></a>
### S-019 — Docker Docs: `docker compose up`

- **URL:** https://docs.docker.com/reference/cli/docker/compose/up/
- **Editore:** Docker Inc. — Docker Docs
- **Versione documentata:** riferimento CLI Compose v2
- **Consultata:** 2026-08-25
- **Verdetto:** conferma parziale
- **Cosa afferma:** l'opzione `--pull` ha valore predefinito `policy` e accetta
  `"always"|"missing"|"never"`. I valori di `pull_policy` documentati sul riferimento dei
  servizi sono: `always` («Compose always pulls the image from the registry»), **`never`
  («Compose doesn't pull the image from a registry and relies on the platform cached image.
  If there is no cached image, a failure is reported»)**, `missing` («Compose pulls the image
  only if it's not available in the platform cache», predefinito), `build`, `daily`,
  `weekly`, `every_<duration>`.
- **Riserve:** tre punti pesano su un lab che deve funzionare senza rete. Primo: **la parola
  «offline» non compare** su nessuna delle pagine consultate — non esiste una modalità
  offline globale documentata di Compose; il solo meccanismo con una frase esplicita sul non
  contattare il registry è `pull_policy: never`. Secondo, la trappola: «The `latest` tag is
  always pulled even when the `missing` pull policy is used». Terzo, la documentazione Docker
  è internamente incoerente sui valori ammessi — `up` ne elenca tre, `create` ne elenca
  quattro aggiungendo `build`, e `docker compose pull` usa una flag diversa, `--policy`, con
  due soli valori. Infine: nessuna pagina ufficiale dice se `compose up` contatti il registry
  per un'immagine **pinnata a digest e già presente in locale**. La deduzione è ragionevole
  ma non è una citazione: **il digest garantisce *quale* immagine, non *se* si va in rete**.
- **Usata da:** ADR-0009, ADR-0018

<a id="s-020"></a>
### S-020 — MongoDB Manual: Change Hostnames in a Self-Managed Replica Set

- **URL:** https://www.mongodb.com/docs/manual/tutorial/change-hostnames-in-a-replica-set/ (citazioni dalla variante `.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** Database Manual 8.3
- **Consultata:** 2026-08-25
- **Verdetto:** conferma parziale
- **Cosa afferma:** i nomi host risiedono nella configurazione del replica set — «For most
  replica sets, the hostnames in the `members[n].host` field never change» — e si cambiano
  con `rs.reconfig()`, nella sequenza `cfg = rs.conf()` / `cfg.members[1].host =
  "mongodb1.example.net:27017"` / `rs.reconfig(cfg)`. Raccomandazione esplicita: «Always use
  resolvable hostnames for the value of the `members[n].host` field in the replica set
  configuration to avoid confusion and complexity». Vincolo duro e versionato, decisivo per
  un lab in Docker: «**Starting in MongoDB 5.0, nodes that are only configured with an IP
  address fail startup validation and do not start.**»
- **Riserve:** la pagina dimostra che gli host stanno in configurazione, ma **non enuncia**
  né che siano i nomi con cui i membri si raggiungono fra loro, né che i client li usino per
  connettersi. Su quest'ultimo punto esiste solo evidenza operativa indiretta: «you must
  configure your applications to connect to the replica set at both the old and new
  locations». Il nesso è deducibile, non citabile.
- **Usata da:** ADR-0021

<a id="s-021"></a>
### S-021 — GitHub Docs: About large files on GitHub

- **URL:** https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
- **Editore:** GitHub, Inc.
- **Versione documentata:** GitHub.com, piani Free, Pro e Team
- **Consultata:** 2026-08-25
- **Verdetto:** conferma
- **Cosa afferma:** «We recommend repositories remain small, ideally less than 1 GB, and less
  than 5 GB is strongly recommended. Smaller repositories are faster to clone and easier to
  work with and maintain.» Sui singoli file: «If you attempt to add or update a file that is
  larger than 50 MiB, you will receive a warning from Git» e «GitHub blocks files larger than
  100 MiB. To track files beyond this limit, you must use Git Large File Storage (Git LFS).»
  Limite ulteriore: «If you add a file to a repository via a browser, the file can be no
  larger than 25 MiB.»
- **Riserve:** le unità sono **MiB**, non MB: scrivere «100 MB» in slide è impreciso ed è
  esattamente il dettaglio che viene fatto notare. I valori valgono per GitHub.com; su
  GitHub Enterprise Server «a site administrator can configure a different limit».
- **Usata da:** ADR-0016, ADR-0031

<a id="s-022"></a>
### S-022 — `docker-library/mongo`: `8.0/docker-entrypoint.sh`

- **URL:** https://github.com/docker-library/mongo/blob/7c24b37b8e53a41b56c450b653c582ff7c3f7fcb/8.0/docker-entrypoint.sh
- **Editore:** Docker Official Images — repository `docker-library/mongo`
- **Versione documentata:** branch `8.0`, commit `7c24b37b8e53a41b56c450b653c582ff7c3f7fcb`, lo stesso referenziato dal README per il tag `8.0.29-noble`
- **Consultata:** 2026-08-25
- **Verdetto:** conferma
- **Cosa afferma:** **è codice sorgente, non documentazione** — va citato come tale. Un
  mongod temporaneo viene avviato con `--fork`, forzato su `--bind_ip 127.0.0.1 --port
  27017`, e arrestato con `--shutdown` prima di `exec "$@"`. I commenti nel sorgente sono
  espliciti: `# remove "--auth" and "--replSet" for our initial startup` e `# "keyFile
  implies security.authorization"`. Il comportamento esatto sui tre flag: `--auth` e
  `--keyFile` sono **sempre** rimossi dal mongod temporaneo; `--replSet` è rimosso **solo
  se entrambe** le variabili root sono presenti. La condizione di inizializzazione non è
  «directory vuota» ma la presenza di uno fra `$dbPath/WiredTiger`, `$dbPath/journal`,
  `$dbPath/local.0`, `$dbPath/storage.bson`. Se manca una sola delle due variabili root,
  l'entrypoint termina con `error: missing 'MONGO_INITDB_ROOT_USERNAME' or
  'MONGO_INITDB_ROOT_PASSWORD'`.
- **Riserve:** conseguenza pratica **non documentata da nessuna parte**: passando
  `MONGO_INITDB_ROOT_USERNAME` insieme a `--replSet` e `--keyFile`, il mongod di
  inizializzazione parte standalone, senza replica set e senza autenticazione; l'utente root
  viene creato in quel contesto; poi il processo definitivo riparte con `--replSet` e
  `--keyFile`. **`rs.initiate()` non viene mai eseguito dall'immagine: resta a nostro
  carico.** Trattandosi di sorgente, l'API non ha garanzie di stabilità fra versioni: la
  citazione deve indicare commit e riga.
- **Usata da:** ADR-0005, ADR-0026

<a id="s-023"></a>
### S-023 — `docker-library/mongo`: `8.0/Dockerfile`

- **URL:** https://github.com/docker-library/mongo/blob/7c24b37b8e53a41b56c450b653c582ff7c3f7fcb/8.0/Dockerfile
- **Editore:** Docker Official Images — repository `docker-library/mongo`
- **Versione documentata:** MongoDB 8.0 su base Ubuntu Noble, stesso commit di [S-022](#s-022)
- **Consultata:** 2026-08-25
- **Verdetto:** conferma
- **Cosa afferma:** `groupadd --gid 999 --system mongodb;` e `useradd --uid 999 --system
  --gid mongodb --home-dir /data/db mongodb;`. Utente e gruppo `mongodb` hanno entrambi
  identificativo **999**; `/data/db` e `/data/configdb` appartengono a `mongodb:mongodb`. La
  scelta è motivata nel sorgente: «add our user and group first to make sure their IDs get
  assigned consistently, regardless of whatever dependencies get added».
- **Riserve:** il valore **non è pubblicato su Docker Hub**: è vero, ma leggibile solo dal
  Dockerfile. È il numero da usare per un eventuale `chown` su bind mount — ed è la ragione
  per cui il keyfile sta in un volume nominato.
- **Usata da:** ADR-0014, ADR-0026

<a id="s-024"></a>
### S-024 — MongoDB Manual: Deploy a Self-Managed Sharded Cluster

- **URL:** https://www.mongodb.com/docs/manual/tutorial/deploy-shard-cluster/ (citazioni dalla variante `.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** Database Manual 8.3 (Current)
- **Consultata:** 2026-08-25
- **Verdetto:** conferma
- **Cosa afferma:** è la fonte che autorizza esplicitamente il replica set a un solo membro,
  e lo fa **due volte**. Per i config server: «For a production deployment, deploy a config
  server replica set with at least three members. **For testing purposes, you can create a
  single-member replica set.**» Per gli shard: «For a production deployment, use a replica
  set with at least three members. **For testing purposes, you can create a single-member
  replica set.**»
- **Riserve:** l'autorizzazione è circoscritta agli scopi di test, e va presentata come tale.
  Non è la pagina che si troverebbe cercando i componenti di uno sharded cluster: chi
  verifica su [S-008](#s-008) non trova nulla in merito.
- **Usata da:** ADR-0010

<a id="s-025"></a>
### S-025 — MongoDB Manual: Config Servers

- **URL:** https://www.mongodb.com/docs/manual/core/sharded-cluster-config-servers/ (citazioni dalla variante `.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** Database Manual 8.3 (Current)
- **Consultata:** 2026-08-25
- **Verdetto:** conferma
- **Cosa afferma:** vincoli sul replica set dei config server, da opporre a chi propone un
  arbitro per risparmiare risorse: «Must have zero arbiters. / Must have no delayed members.
  / Must build indexes (i.e. no member should have `members[n].buildIndexes` setting set to
  false).» Vincolo sui nomi: «The config server replica set must not use the same name as any
  of the shard replica sets.»
- **Riserve:** nessuna.
- **Usata da:** ADR-0010

<a id="s-026"></a>
### S-026 — MongoDB Manual: `hostInfo`

- **URL:** https://www.mongodb.com/docs/manual/reference/command/hostInfo/ (citazioni dalla variante `hostInfo.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** Database Manual 8.3 (Current)
- **Consultata:** 2026-08-25
- **Verdetto:** contraddice
- **Cosa afferma:** «For example, running in a container may impose memory limits that are
  lower than the total system memory. This memory limit, rather than the total system memory,
  is used as the maximum RAM available to calculate WiredTiger internal cache.»
- **Riserve:** questa frase è **incompatibile** con [S-001](#s-001), che sullo stesso manuale
  e alla stessa versione afferma che WiredTiger «may not account for the memory limits of the
  specific container in certain cases» e prescrive di impostare la cache a mano. Non è una
  divergenza fra versioni: **le due pagine correnti si contraddicono**. Conseguenza pratica:
  non affermare sul palco che il rilevamento del limite avviene automaticamente; mostrarlo
  con `db.hostInfo()` in demo, e impostare comunque la cache in modo esplicito.
- **Sciolta il 2026-08-25:** la contraddizione era apparente e la misura la spiega
  [V-006](#v-006). Le due pagine parlano di campi diversi: `hostInfo.system.memSizeMB` riporta
  la memoria della macchina — 11946 MiB, la VM — mentre `hostInfo.system.memLimitMB` riporta il
  `mem_limit` del container, 640 MiB. È il secondo a guidare la cache: senza
  `--wiredTigerCacheSizeGB`, un container limitato a 640 MiB sceglie 256 MiB e uno limitato a
  4.096 MiB sceglie 1.536 MiB, cioè 0,5 × (limite − 1 GiB). La prescrizione qui sopra resta
  valida — impostare la cache a mano — ma per rendere il valore esplicito e leggibile, non
  perché il rilevamento non funzioni.
- **Usata da:** ADR-0004

<a id="s-027"></a>
### S-027 — MongoDB Manual: MongoDB Versioning

- **URL:** https://www.mongodb.com/docs/manual/reference/versioning/ (citazioni dalla variante `versioning.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** Database Manual 8.3 (Current)
- **Consultata:** 2026-08-25
- **Verdetto:** conferma, e cambia una premessa del progetto
- **Cosa afferma:** dalla 8.2 lo schema di rilascio è cambiato. «Starting with MongoDB 8.2,
  MongoDB adopts a new versioning and release strategy». Le *Major Releases* escono «every two
  years and have a five-year lifecycle»; le *Minor Releases* «are as stable as major releases
  and suitable for production workloads». La frase che decide, però, è sulle minor: «After a
  new minor release becomes available, MongoDB does not continue patching the previous minor
  release.»
- **Riserve:** la pagina non nomina versioni specifiche oltre agli esempi (`7.0`, `8.0` per le
  major, `8.2` per le minor), quindi la classificazione della 8.3 si deduce dallo schema e dal
  fatto che l'indice delle release notes la elenchi come stabile corrente, non da
  un'affermazione esplicita. La pagina non dice nulla sui vincoli di piattaforma né sui kernel.
- **Usata da:** ADR-0028

<a id="s-028"></a>
### S-028 — MongoDB Manual: Release Notes for MongoDB 8.0 — Changelog

- **URL:** https://www.mongodb.com/docs/manual/release-notes/8.0-changelog/ (consultata nella variante `8.0-changelog.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** serie 8.0
- **Consultata:** 2026-08-25
- **Verdetto:** conferma
- **Cosa afferma:** sotto la voce **8.0.30**, sezione *Internals*, compare `SERVER-125742` —
  il ticket che restringe l'uscita anticipata ai soli kernel dalla versione 7.0.14 in su. È la
  correzione che renderebbe di nuovo avviabile la 8.0 sul kernel `7.0.12-linuxkit` della VM di
  Docker Desktop.
- **Riserve:** due, entrambe rilevanti. La pagina è servita in forma compressa e troncata:
  molte voci perdono il testo descrittivo e restano il solo identificatore, `SERVER-125742`
  compreso — il numero è confermato, il contenuto va letto sul ticket. E la presenza di una
  voce nel changelog **non implica** che i binari siano pubblicati: al 2026-08-25 la 8.0.30 non
  compare né in `downloads.mongodb.org/current.json`, né fra i tag di `library/mongo`, né fra
  quelli di `mongodb/mongodb-community-server` [V-007](#v-007). Il changelog documenta il ramo
  di rilascio, non la disponibilità.
- **Usata da:** ADR-0028

---

<a id="s-029"></a>
### S-029 — MongoDB Manual: Compatibility Changes in MongoDB 8.0

- **URL:** https://www.mongodb.com/docs/manual/release-notes/8.0-compatibility/ (letta nella
  variante `8.0-compatibility.md`, che restituisce il testo integrale)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** serie 8.0
- **Consultata:** 2026-08-25
- **Verdetto:** conferma una causa, e smentisce un'assunzione del progetto
- **Cosa afferma, primo punto — la causa del blocco, finalmente documentata.** Sezione
  *Upgraded TCMalloc*: «Starting in MongoDB 8.0, MongoDB uses an upgraded version of TCMalloc
  that uses per-CPU caches, instead of per-thread caches, to reduce memory fragmentation and
  make your database more resilient to high-stress workloads.» È **la 8.0** a introdurre la
  cache per-CPU, cioè esattamente il meccanismo che sul kernel dal 6.19 in su viola l'ABI di
  `rseq`. Spiega in una riga perché la 7.0 si avvia e la 8.0 no, senza passare dai ticket
  Jira, e scioglie in parte la riserva di [V-007](#v-007).
- **Cosa afferma, secondo punto — una differenza fra 7.0 e 8.0 che tocca la demo.** Sezione
  *Cannot Connect Directly to Shard and Run Commands*, elencata fra le **Backward-Incompatible
  Features**: «Starting in MongoDB 8.0, you can only run certain commands on nodes in sharded
  clusters. If you attempt to connect directly to a node and run an unsupported command,
  MongoDB returns an error» — e l'errore è «You are connecting to a sharded cluster improperly
  by connecting directly to a shard. Please connect to the cluster via a router (mongos).»
  Segue la via d'uscita: «you must either connect to `mongos` or have the maintenance-only
  `directShardOperations` role», con la precisazione che il vincolo vale «once the cluster has
  more than one shard».
- **Cosa afferma, terzo punto — la semantica di `majority` cambia.** Sezione *Write Concern
  Majority*: «Starting in MongoDB 8.0, write operations that use the `"majority"` write concern
  return an acknowledgment when the majority of replica set members have written the oplog
  entry for the change. […] In previous releases, these operations would wait and return an
  acknowledgment after the majority of replica set members applied the change.» Scritto contro
  applicato: è una differenza osservabile proprio nelle misure di latenza sotto failover.
- **Cosa non afferma:** le stringhe `mongodump`, `mongorestore`, `rs.initiate`, `sh.addShard`,
  `keyfile` e `config server` **non compaiono** nella pagina. Su quei punti la 8.0 non dichiara
  incompatibilità.
- **Riserve:** una pagina di *compatibility changes* elenca ciò che rompe, non ciò che resta
  uguale. L'assenza di una voce è un indizio forte, non una prova di identità di comportamento:
  non esiste una pagina che affermi «7.0 e 8.0 si comportano allo stesso modo». La lettura
  copre inoltre la sola 8.0; per la 8.2 e la 8.3 esistono pagine analoghe non consultate.
- **Usata da:** ADR-0028

---

<a id="s-030"></a>
### S-030 — POSIX, Base Definitions capitolo 9: Regular Expressions

- **URL:** https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap09.html
- **Editore:** IEEE e The Open Group — The Open Group Base Specifications Issue 7, 2018 edition
- **Versione documentata:** Issue 7, edizione 2018 (IEEE Std 1003.1-2017, revisione di IEEE
  Std 1003.1-2008)
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — due quantificatori attaccati sono indefiniti.** Sezione
  **9.4.6**, *EREs Matching Multiple Characters*, in chiusura di sottosezione: «The behavior of
  multiple adjacent duplication symbols ( '+', '\*', '?', and intervals) produces undefined
  results.» Una frase gemella sta in **9.3.6** per le BRE, con l'elenco ridotto a `*` e agli
  intervalli. È la regola sotto cui cade `.*?`: negli ERE il non-greedy non esiste, quindi
  quella `?` non è un modificatore ma un secondo quantificatore attaccato al primo.
- **Cosa afferma, secondo punto — e qui «indefinito» viene definito.** Sezione **9.1**, voce
  *invalid*: «When invalid is not used, violations of the specified syntax or semantics for REs
  produce undefined results: this may entail an error, enabling an extended syntax for that RE,
  or using the construct in error as literal characters to be matched.» Tre esiti, tutti
  leciti: errore, estensione, oppure trattamento come caratteri letterali. Nessuno è
  prescritto, e un programma portabile non può contare su nessuno dei tre.
- **Cosa afferma, terzo punto — il permesso di estendere è esplicito.** Dopo l'elenco dei
  costrutti che la grammatica ERE accetta ma lascia indefiniti: «Implementations are permitted
  to extend the language to allow these. Strictly Conforming applications cannot use such
  constructs.»
- **Cosa non afferma:** che `*?` sia un errore, o che rompa qualcosa. Nel capitolo non compare
  alcun quantificatore non-greedy, né la nozione di corrispondenza minima: la semantica
  descritta è quella più a sinistra e più lunga.
- **Riserve:** lo standard descrive gli ERE, non una particolare implementazione. Proprio le
  frasi citate al secondo e al terzo punto rendono la pagina inservibile per **prevedere** cosa
  faccia un `awk` reale: un'implementazione può definire `*?` come estensione e restare
  conforme. Serve a stabilire cosa **non è garantito**, non cosa succede — quello va misurato.
  Consultata l'edizione 2018; la pagina segnala l'esistenza di un'edizione più recente, non
  aperta.
- **Usata da:** ADR-0029

---

<a id="s-031"></a>
### S-031 — POSIX, Shell and Utilities: `awk`

- **URL:** https://pubs.opengroup.org/onlinepubs/9699919799/utilities/awk.html
- **Editore:** IEEE e The Open Group — The Open Group Base Specifications Issue 7, 2018 edition
- **Versione documentata:** Issue 7, edizione 2018 (IEEE Std 1003.1-2017)
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — quale dialetto parla `awk`.** «The `awk` utility shall make use
  of the extended regular expression notation (see XBD *Extended Regular Expressions*)», con
  un'eccezione dichiarata per le sequenze di escape in stile C. È il collegamento che porta il
  capitolo 9 [S-030](#s-030) a valere anche dentro un `FS`.
- **Cosa afferma, secondo punto — ma è un soprainsieme.** La *RATIONALE* dichiara l'intento di
  «make them a pure superset of extended regular expressions, as defined by POSIX.1-2017»,
  indicando nell'internazionalizzazione e nelle interval expressions le aggiunte principali.
- **Cosa non afferma:** non nomina il non-greedy né `*?`, in nessuna sezione.
- **Riserve:** «pure superset» è esattamente il motivo per cui il capitolo 9 non basta a
  prevedere il comportamento di un `awk` installato: sopra gli ERE un'implementazione può
  aggiungere ciò che vuole e restare conforme. La conseguenza pratica è quella registrata in
  [ADR-0029](Decision.md#adr-0029): un costrutto indefinito non è rotto, è soltanto non
  garantito, e la differenza fra le due cose si stabilisce eseguendo.
- **Usata da:** ADR-0029

---

<a id="s-032"></a>
### S-032 — MongoDB Manual: Configuration File Options — `systemLog`

- **URL:** https://www.mongodb.com/docs/v7.0/reference/configuration-options/
- **Editore:** MongoDB, Inc. — MongoDB Manual
- **Versione documentata:** v7.0
- **Consultata:** 2026-08-28
- **Verdetto:** smentita — di un assunto del design, non di un'altra fonte
- **Cosa afferma, primo punto — le destinazioni sono alternative, non cumulative.** «The
  destination to which MongoDB sends all log output. Specify either `file` or `syslog`. If you
  specify `file`, you must also specify `systemLog.path`.» *Either*: una, non due.
- **Cosa afferma, secondo punto — stdout non è un canale, è il ripiego.** «If you do not specify
  `systemLog.destination`, MongoDB sends all log output to standard output.» Standard output è
  dove finisce il log quando non si è scelto niente, e smette di esserlo appena si sceglie.
- **Cosa afferma, terzo punto — `systemLog.path` è definito per sottrazione.** «The path of the
  log file to which `mongod` or `mongos` should send all diagnostic logging information,
  **rather than the standard output** or the host's syslog.» `--logpath` è la forma da riga di
  comando della stessa impostazione.
- **Cosa non afferma:** non esiste, in nessun punto della pagina, un'opzione per scrivere su due
  destinazioni contemporaneamente. Non è nascosta: non c'è.
- **Riserve:** la pagina del riferimento di `mongod`, che è dove si arriva cercando `--logpath`,
  dice la stessa cosa in modo molto meno netto. Chi parte da lì fatica a trovare la risposta —
  ed è il motivo per cui l'assunto sbagliato è entrato nel design senza che nessuno lo notasse.
  Il comportamento è comunque verificato eseguendo, [V-010](#v-010), e confermato dall'aiuto del
  binario dentro l'immagine del lab.
- **Usata da:** ADR-0030

---

<a id="s-033"></a>
### S-033 — Docker Docs: JSON File logging driver

- **URL:** https://docs.docker.com/engine/logging/drivers/json-file/
- **Editore:** Docker, Inc. — Docker Docs
- **Versione documentata:** pagina viva, consultata contro Docker Engine 29.7.2
- **Consultata:** 2026-08-28
- **Verdetto:** conferma parziale
- **Cosa afferma, primo punto — `max-size` non ha limite.** «The maximum size of the log before
  it is rolled», con valore predefinito dichiarato in tabella: «Defaults to -1 (unlimited)».
- **Cosa afferma, secondo punto — `max-file` da solo non serve a niente.** «The maximum number
  of log files that can be present. If rolling the logs creates excess files, the oldest file is
  removed», predefinito `1`, e nella stessa tabella, in grassetto: «Only effective when
  `max-size` is also set». Sono due opzioni che funzionano solo in coppia.
- **Cosa afferma, terzo punto — la rotazione è una cosa da accendere.** L'esempio che imposta i
  due parametri è introdotto come il modo «to enable automatic log-rotation».
- **Cosa non afferma:** in nessun punto della pagina c'è una frase che dica che senza
  configurazione la rotazione non avviene. Lo si ricava da un valore predefinito in una cella di
  tabella e dal verbo «enable» in una didascalia. Non c'è nemmeno un avviso sullo spazio disco:
  l'unico riquadro di avvertimento della pagina riguarda l'accesso ai file da parte di strumenti
  esterni, non il disco che si riempie.
- **Riserve:** «il predefinito è illimitato, quindi non ruota» è una deduzione, e qui una
  deduzione non sostituisce una misura che costa un comando. Misurata in [V-011](#v-011).
- **Usata da:** ADR-0030

---

<a id="s-034"></a>
### S-034 — `docker-library/mongo`: `7.0/docker-entrypoint.sh`

- **URL:** https://github.com/docker-library/mongo/blob/master/7.0/docker-entrypoint.sh
- **Editore:** docker-library — Docker Official Images
- **Versione documentata:** la copia che sta in `/usr/local/bin/docker-entrypoint.sh` dentro
  l'immagine `mongo` 7.0.40 pinnata per digest. Le righe citate sotto sono lette lì, dentro
  l'immagine che il lab esegue davvero, non dal repository.
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — quando gli script di inizializzazione si saltano, e su quale
  criterio.** Il commento è esplicito: «check for a few known paths (to determine whether we've
  already initialized and should thus skip our initdb scripts)». Segue un ciclo su quattro
  percorsi — `$dbPath/WiredTiger`, `$dbPath/journal`, `$dbPath/local.0`, `$dbPath/storage.bson` —
  e se anche uno solo esiste, `shouldPerformInitdb` viene azzerato. La regola non è «se la
  cartella è vuota»: è «se non trovo traccia di un'inizializzazione precedente», e le tracce sono
  un elenco scritto a mano.
- **Cosa afferma, secondo punto — il `mongod` temporaneo della fase di init forka.** L'ultima
  riga della sua invocazione è `"${mongodHackedArgs[@]}" --fork`, e `--fork` obbliga a dichiarare
  un `--logpath`.
- **Cosa afferma, terzo punto — e per non perdere quei log, li manda su un descrittore.**
  `if stat "/proc/$$/fd/1" > /dev/null && [ -w "/proc/$$/fd/1" ]; then` →
  `--logpath "/proc/$$/fd/1"`, con ripiego su un file dentro `dbPath` e avviso esplicito:
  «warning: initdb logs cannot write to '/proc/$$/fd/1', so they are in '$initdbLogPath'
  instead». Chi ha scritto l'entrypoint sapeva perfettamente che `--logpath` porta via i log da
  stdout, e ha dovuto aggirarlo — corrobora [S-032](#s-032) e [V-010](#v-010) dal lato di chi
  costruisce l'immagine.
- **Cosa non afferma:** quando decide di saltare gli script di init, **non stampa niente**. Il
  ramo che azzera `shouldPerformInitdb` non ha un `echo`, non ha un `warning`, non lascia una
  riga di log. Il salto è muto. Verificato in [V-014](#v-014).
- **Riserve:** [S-022](#s-022) documenta lo stesso file per la 8.0. Il lab gira sulla 7.0
  [ADR-0028](Decision.md#adr-0028), quindi per gli stack vale questa voce e non quella. I due
  file si somigliano molto, ed è esattamente il motivo per cui citare quello sbagliato non si
  noterebbe fino al giorno in cui cambia.
- **Usata da:** ADR-0030, ADR-0031

---

<a id="s-035"></a>
### S-035 — MongoDB Manual 7.0: Write Concern

- **URL:** https://www.mongodb.com/docs/v7.0/reference/write-concern/ (consultata nella variante
  `write-concern.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** v7.0, cioè la versione che il lab esegue ([ADR-0028](Decision.md#adr-0028))
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — che cosa promette l'ack su un'istanza singola.** «A standalone
  `mongod` acknowledges a write operation after applying the write in memory **or** after writing
  to the on-disk journal.» Quale delle due lo decide la tabella che segue, ed è la riga che
  riguarda il lab:

  | | `j` non specificato | `j:true` | `j:false` |
  |---|---|---|---|
  | `w: 1` | In memory | On-disk journal | In memory |

  Con `w: 1` e `j` non specificato — il caso predefinito, quello che scrive chiunque non abbia
  letto questa tabella — **l'acknowledgement è la memoria**. Il disco non c'entra.
- **Cosa afferma, secondo punto — il limite superiore su un nodo solo.** «`w` greater than 1
  requires acknowledgment from the primary and as many data-bearing secondaries as needed to meet
  the specified write concern». Su un'istanza singola i secondari non esistono, e il server
  rifiuta: misurato in [V-015](#v-015).
- **Cosa non afferma:** che `w: "majority"` su un'istanza singola sia un errore. Non lo è, e la
  pagina non lo dice in nessuna direzione — la maggioranza di un nodo è quel nodo. Chiedere
  «maggioranza» a uno standalone riesce, e riesce senza dare niente in più di `w: 1`. Misurato in
  [V-015](#v-015).
- **Riserve:** la tabella dello standalone descrive il momento dell'*acknowledgement*, non la
  durabilità. Quanto dura la finestra fra l'ack in memoria e il disco non sta qui: sta in
  [S-036](#s-036), ed è il numero che rende la finestra misurabile.
- **Usata da:** ADR-0032

---

<a id="s-036"></a>
### S-036 — MongoDB Manual 7.0: Journaling

- **URL:** https://www.mongodb.com/docs/v7.0/core/journaling/ (consultata nella variante
  `journaling.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** v7.0
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — il journal non si può spegnere.** «Starting in MongoDB 6.1,
  journaling is always enabled. As a result, MongoDB removes the `storage.journal.enabled` option
  and the corresponding `--journal` and `--nojournal` command-line options.» Sulla 7.0 la domanda
  «e se lo disattivo?» non ha più risposta: l'opzione non esiste.
- **Cosa afferma, secondo punto — ogni quanto il journal tocca il disco.** WiredTiger sincronizza
  «At every 100 milliseconds (See `storage.journal.commitIntervalMs`)», oltre che a ogni scrittura
  con `j: true` e quando crea un nuovo file di journal (limite di 100 MB per file).
- **Cosa afferma, terzo punto — e quindi che cosa si perde.** In grassetto, come Importante:
  «In between write operations, while the journal records remain in the WiredTiger buffers,
  updates can be lost following a hard shutdown of `mongod`.» È la frase che autorizza a dire
  «l'ack non è il disco» senza aggettivi: lo dice il manuale.
- **Cosa afferma, quarto punto — a cosa serve il journal alla ripartenza.** «if MongoDB exits
  unexpectedly in between checkpoints, journaling is required to recover information that occurred
  after the last checkpoint».
- **Riserve:** la pagina dà l'intervallo (100 ms) ma non dice **quanti** documenti stiano in quella
  finestra, perché dipende dal ritmo delle scritture. Il numero per il lab è misurato in
  [V-016](#v-016): cento documenti confermati e perduti, su un `SIGKILL` durante un inserimento
  uno alla volta.
- **Usata da:** ADR-0032

---

<a id="s-037"></a>
### S-037 — MongoDB Manual 7.0: Replica Set Oplog

- **URL:** https://www.mongodb.com/docs/v7.0/core/replica-set-oplog/ (consultata nella variante
  `replica-set-oplog.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** v7.0
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma:** «The oplog (operations log) is a special capped collection that keeps a rolling
  record of all operations that modify the data stored in your databases»; e su dove vive: «All
  replica set members contain a copy of the oplog, in the `local.oplog.rs` collection, which allows
  them to maintain the current state of the database.»
- **Cosa non afferma:** che un'istanza singola non abbia l'oplog. Non c'è una frase che lo dica —
  c'è il titolo della pagina, «**Replica Set** Oplog», e il fatto che ogni frase parli di membri di
  un replica set. La conferma diretta è nostra: su `mongo-standalone` il database `local` contiene
  la sola `startup_log`, e `local.oplog.rs` non esiste ([V-015](#v-015)).
- **Riserve:** questa è una fonte che si cita per ciò che *implica*, ed è il tipo di citazione da
  maneggiare con cura. L'affermazione «un'istanza singola non ha oplog» qui non è scritta: è
  dedotta dalla pagina e **verificata eseguendo**, come impone la gerarchia di
  [ADR-0024](Decision.md#adr-0024). Chi ripete l'affermazione senza la verifica sta citando un
  titolo.
- **Usata da:** ADR-0032

---

<a id="s-038"></a>
### S-038 — MongoDB Manual 7.0: Change Streams

- **URL:** https://www.mongodb.com/docs/v7.0/changeStreams/ (consultata nella variante
  `changeStreams.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** v7.0
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma:** in apertura della sezione *Availability*, senza giri di parole: «Change streams
  are available for **replica sets** and **sharded clusters**». E sul perché uno se ne accorga solo
  quando serve: «Change streams allow applications to access real-time data changes without the
  prior complexity and risk of manually tailing the oplog» — cioè poggiano sull'oplog
  ([S-037](#s-037)), che su un'istanza singola non c'è.
- **Cosa non afferma:** con quale errore fallisce chi ci prova comunque. La pagina elenca dove i
  change stream *sono* disponibili e tace su cosa succede altrove. Il messaggio esatto — `Location
  40573`, «The $changeStream stage is only supported on replica sets» — è misurato in
  [V-015](#v-015), ed è quello che si legge in produzione quando qualcuno sposta un'applicazione da
  un replica set a un'istanza singola per «semplificare».
- **Riserve:** la pagina è scritta per chi ha già un replica set. Non contiene una sezione
  «migrazione da standalone», che è invece il percorso reale di chi incontra il limite.
- **Usata da:** ADR-0032

---

## Verifiche empiriche

<a id="v-001"></a>
### V-001 — Apple `container` non espone un subcomando `compose`

- **Comando:** `container --help` · `container compose --help`
- **Ambiente:** macOS 26.6.2, Apple `container` 1.2.2
- **Esito:** nessun subcomando `compose`; il secondo comando termina con errore.
- **Data:** 2026-08-24
- **Usata da:** ADR-0002

<a id="v-002"></a>
### V-002 — Inventario dell'ambiente di sviluppo e di palco

- **Comandi:** `docker version` · `docker info` · `sysctl hw.memsize`
- **Esito:** host macOS 26.6.2 arm64, 8 CPU, 16 GiB; VM Docker 7,65 GiB e 8 CPU;
  Docker 29.7.2 con Compose v5.4.0, contesto `desktop-linux`.
- **Data:** 2026-08-24
- **Usata da:** ADR-0008, ADR-0009, ADR-0010, ADR-0025

<a id="v-003"></a>
### V-003 — Digest dell'immagine `mongo:8.0` e verifica offline

- **Comandi:** `tools/pull-images.sh --pull` · `tools/pull-images.sh --verify`
- **Ambiente:** Docker 29.7.2, host macOS arm64
- **Esito:** `mongo:8.0` risolve a
  `mongo@sha256:02a0cc7939f5ed38f30f9bc714ef5f682d49baf9350c54acf302ce833087fe8a`;
  immagine `linux/arm64/v8`, costruita il 2026-08-18, 302 MB. Con il digest presente in
  cache `--verify` esce 0; guastando una cifra del digest esce 1 in 0,15 s — un tempo che
  esclude qualsiasi tentativo di contattare il registro, perché `docker image inspect`
  interroga solo il demone locale.
- **Data:** 2026-08-25
- **Usata da:** ADR-0008, ADR-0009

<a id="v-004"></a>
### V-004 — Memoria della VM Docker dopo l'aumento

- **Comando:** `docker info --format '{{.MemTotal}}'`
- **Ambiente:** Docker 29.7.2, host macOS arm64 da 16 GiB
- **Esito:** 11,67 GiB e 8 CPU assegnati alla VM, contro i 7,65 GiB rilevati il giorno
  prima [V-002](#v-002). L'aumento deciso in [ADR-0025](Decision.md#adr-0025) è applicato.
  Resta non misurato se undici container ci stiano davvero: quello è lo spike sharded.
- **Data:** 2026-08-25
- **Usata da:** ADR-0025

<a id="v-005"></a>
### V-005 — Prima esecuzione del preflight

- **Comando:** `make preflight`
- **Ambiente:** Docker 29.7.2, host macOS arm64, 2026-08-25
- **Esito:** sette controlli superati, un avviso, nessun errore. Demone attivo su contesto
  `desktop-linux`, `docker` risolto a `/usr/local/bin/docker` e nessun residuo in `~/.rd`,
  VM da 11,67 GiB e 8 CPU, quindici porte del lab libere, immagini pinnate presenti.
  L'unico avviso è l'assenza della cartella dei filmati di riserva, che diventa errore
  bloccante dal giorno del talk.
- **Percorsi di fallimento provati:** porta 27017 tenuta da un processo estraneo → errore e
  uscita 1; digest guastato in `images.env` → errore e uscita 1; demone irraggiungibile
  (`DOCKER_HOST` inesistente) → tre errori e uscita 1, con gli altri controlli comunque
  eseguiti; data del talk simulata al passato senza filmati → l'avviso diventa errore.
- **Data:** 2026-08-25
- **Usata da:** ADR-0009

<a id="v-006"></a>
### V-006 — Spike dello sharded cluster: topologia, memoria, profili

- **Comandi:** `docker compose --profile completo up -d --wait` · `rs.initiate()` ·
  `sh.addShard()` · `sh.status()` · `getShardDistribution()` · `docker stats --no-stream` ·
  `db.adminCommand({hostInfo: 1})` · `db.serverStatus()`
- **Ambiente:** Docker 29.7.2, Compose v5.4.0, VM `7.0.12-linuxkit` con 11.946 MiB e 8 CPU,
  host macOS arm64. Immagine `mongo:7.0` (7.0.40) pinnata per digest — la 8.0 non parte su
  questo kernel [V-007](#v-007).
- **Esito:** la catena keyfile → `rs.initiate()` → `createUser()` → `mongos` → `sh.addShard()`
  funziona su entrambi i profili. Undici container in esecuzione occupano **1.356 MiB reali
  contro 6.144 MiB di `mem_limit` dichiarati**; nella VM restano 9.021 MiB disponibili.
  Cinquantamila documenti con shard key `{_id: "hashed"}` si distribuiscono su entrambi gli
  shard (a ventimila documenti: 4 chunk, 50,7 % / 49,3 %). Fermato il primario di uno shard,
  un secondario è stato eletto e il cluster ha continuato a servire letture e scritture
  attraverso mongos; riavviato il nodo, è rientrato come `SECONDARY` senza intervento.
  `docker compose --profile palco config --services` elenca 5 servizi, `--profile completo` 12,
  senza profilo 1.
- **Misure collaterali:** `hostInfo.system.memSizeMB` riporta 11946 — la memoria della VM —
  mentre `hostInfo.system.memLimitMB` riporta 640, cioè il `mem_limit` del container. Due
  mongod avviati senza `--wiredTigerCacheSizeGB` scelgono da soli 256 MiB con limite 640 MiB e
  1.536 MiB con limite 4.096 MiB: la formula `max(0,5 × (RAM − 1 GiB), pavimento)` si applica
  alla memoria del **container**. Con `pull_policy: never`, un digest presente in cache avvia
  in 0,674 s e uno inesistente fallisce in **0,110 s** con `No such image`, senza contattare
  il registro.
- **Fallimenti incontrati:** `MONGO_INITDB_ROOT_USERNAME`/`_PASSWORD` su un nodo `--configsvr`
  lo fanno uscire con `BadValue: Cannot start a configsvr as a standalone server`, perché
  l'entrypoint toglie `--replSet` per creare l'utente [S-022](#s-022) ma non `--configsvr`.
  L'eccezione localhost non copre `hostInfo`: consente solo di creare il primo utente o ruolo.
  Dopo `sh.addShard()`, una connessione diretta a uno shard con le credenziali del cluster
  risponde `Authentication failed`: servono utenti locali allo shard.
- **Riserve:** misurato su MongoDB 7.0.40, non sulla versione che finirà nel lab; i consumi di
  memoria della 8.x possono differire. Il cluster era a riposo salvo gli inserimenti: sotto il
  carico dell'applicazione del talk i numeri saliranno verso i tetti. Il profilo `palco` è
  stato provato con un solo membro per componente, quindi non dimostra nulla sul failover in
  quel profilo — dove infatti non ce n'è.
- **Verbale completo:** [`00-progetto/2026-08-25-spike-sharded.md`](00-progetto/2026-08-25-spike-sharded.md)
- **Data:** 2026-08-25
- **Usata da:** ADR-0025, ADR-0026, ADR-0027

<a id="v-007"></a>
### V-007 — Quali versioni di MongoDB si avviano sul kernel della VM Docker

- **Comandi:** `docker run --rm --entrypoint mongod mongo:<tag> --version` ·
  `docker info --format '{{.KernelVersion}}'` · `curl downloads.mongodb.org/current.json` ·
  interrogazione dei tag di `library/mongo` e `mongodb/mongodb-community-server`
- **Ambiente:** VM Docker Desktop, kernel `7.0.12-linuxkit`, `aarch64`, 2026-08-25
- **Esito:** `mongo:8.0` (8.0.29), `mongo:8.0.29` e `mongo:8.3` (8.3.8) escono con codice
  diverso da zero e messaggio fatale `id: 12257600` — «Linux kernel versions 6.19 and newer has
  a known incompatibility with this version of MongoDB». `mongo:8.2` (8.2.12) e `mongo:7.0`
  (7.0.40) si avviano. Il controllo scatta in `ctx: main`, prima della lettura dei parametri.
- **Tentativi di aggiramento, tutti falliti:** `GLIBC_TUNABLES=glibc.pthread.rseq=0`;
  `--setParameter tcmallocEnablePerCPUCaches=false`. Nel binario compaiono i simboli
  `isKernelVersionSafeForTCMallocPerCPUCache` e `validateRseqKernelCompat`, ma nessuna
  variabile o parametro che li disattivi.
- **Disponibilità della correzione:** `downloads.mongodb.org/current.json` elenca 8.3.8,
  8.2.12, 8.0.29, 7.0.40, 6.0.29, 5.0.34, 4.4.31. La **8.0.30** — che contiene il ticket
  correttivo [S-028](#s-028) — non compare, né lì né fra i tag delle due immagini. Fra i tag
  correnti di `library/mongo` la 8.2 non è più pubblicata: restano 8.3.8, 8.0.29 e 7.0.40.
- **Riserve:** la ricostruzione della causa — TCMalloc che usa `rseq` violando l'ABI del
  kernel — poggia sui ticket `SERVER-121912` e `SERVER-121911`, linkati dal messaggio di errore
  stesso. Sono tracce di lavoro, non documentazione: il primo è chiuso con risoluzione «Gone
  away» e senza *Fix Version*. Che la 8.2.12 si avvii **non significa** che sia sana: si avvia
  perché precede l'introduzione del controllo, e per la stessa famiglia è segnalato un ciclo di
  crash con SIGSEGV sul kernel 6.19 (`SERVER-122741`). Non è stato verificato per quanto tempo
  la 8.2.12 regga sotto carico, e non lo si è verificato di proposito: una versione che non
  riceve più patch [S-027](#s-027) è comunque fuori scelta.
- **Data:** 2026-08-25
- **Usata da:** ADR-0027, ADR-0028

<a id="v-008"></a>
### V-008 — Ripinnatura alla 7.0.40: digest, piattaforme, strumenti a bordo

- **Comandi:** `make images-pull` · `docker manifest inspect mongo:7.0` ·
  `docker run --rm --entrypoint {mongod,mongosh,mongodump} mongo:7.0 --version` ·
  `make preflight`
- **Ambiente:** Docker 29.7.2, host macOS 26.6.2 arm64, 2026-08-25
- **Esito:** `mongo:7.0` risolve a
  `mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b`. Il manifest
  dichiara `linux/amd64`, `linux/arm64/v8` e `windows/amd64`: il requisito arm64 della macchina
  di palco è soddisfatto anche sulla versione nuova. L'immagine porta a bordo `mongod` 7.0.40,
  `mongosh` 2.10.0 e `mongodump` 100.18.0 — una sola immagine copre demone, shell e strumenti,
  come nella 8.0. Con la ripinnatura `make preflight` torna verde: `Superati: 8 · Avvisi: 1 ·
  Errori: 0`, dove l'unico avviso è l'assenza dei filmati di riserva, non ancora girati.
- **Riserve:** verifica il ritorno alla normalità del preflight, non il comportamento del lab:
  gli stack Compose non esistono ancora su questo branch. La versione degli strumenti a bordo
  (`mongosh`, `mongodump`) non è pinnata separatamente e segue l'immagine.
- **Data:** 2026-08-25
- **Usata da:** ADR-0028

<a id="v-009"></a>
### V-009 — Limiti di risorsa in Compose: le due sintassi, la cache, l'OOM, la CPU

- **Comandi:** `docker compose up -d` su tre servizi identici salvo i limiti ·
  `docker inspect --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}}'` ·
  `docker stats --no-stream` · `db.adminCommand({hostInfo: 1})` ·
  `db.serverStatus().wiredTiger.cache` · `docker inspect --format '{{.State.OOMKilled}}'`
- **Ambiente:** Docker 29.7.2, Compose v5.4.0, VM `7.0.12-linuxkit` con 11.946 MiB e 8 CPU,
  host macOS 26.6.2 arm64, immagine `mongo:7.0` (7.0.40) pinnata per digest, 2026-08-25

**1. `deploy.resources.limits` è applicato da `docker compose up`.** È la domanda che
[S-004](#s-004) lascia senza risposta e che [ADR-0013](Decision.md#adr-0013) prometteva di
risolvere con `docker inspect`. Tre servizi nello stesso file, stessa immagine, stesso comando:

| Servizio | Come sono dichiarati i limiti | `HostConfig.Memory` | `HostConfig.NanoCpus` |
|---|---|---|---|
| `breve` | `mem_limit: 640m` + `cpus: 0.5` | `671088640` | `500000000` |
| `deploy_solo` | `deploy.resources.limits` | `671088640` | `500000000` |
| `nessun_limite` | niente | `0` | `0` |

I due valori sono **identici byte per byte**. La convinzione diffusa secondo cui `deploy`
sarebbe ignorato fuori da Swarm è falsa su questa versione di Compose: apparteneva al
riferimento del formato v3, ritirato [S-004](#s-004). `671088640` è esattamente 640 × 1024²,
cioè `640m` letto in **MiB**; `500000000` nanoCPU è mezza CPU.

**2. La cache WiredTiger si dimensiona sul limite del container, e ha un pavimento.** Nessun
`--wiredTigerCacheSizeGB`, solo `mem_limit` variabile, cache letta da `serverStatus()`:

| `mem_limit` | `hostInfo.system.memLimitMB` | Cache scelta | `0,5 × (limite − 1 GiB)` |
|---|---|---|---|
| 640 MiB | 640 | **256 MiB** | negativo → pavimento |
| 768 MiB | 768 | **256 MiB** | negativo → pavimento |
| 1.024 MiB | 1024 | **256 MiB** | 0 → pavimento |
| 2.048 MiB | 2048 | **512 MiB** | 512 MiB |
| 4.096 MiB | 4096 | **1.536 MiB** | 1.536 MiB [V-006](#v-006) |
| nessuno | 11946 | **5.461 MiB** | 5.461 MiB |

`hostInfo.system.memSizeMB` riporta sempre 11946, cioè la VM. È `memLimitMB` a guidare il
calcolo, e senza `mem_limit` i due campi coincidono. Il pavimento misurato è **256 MiB**, non
«0.256 GB» = 244 MiB: l'unità dichiarata dal manuale è GB, quella applicata è GiB.

**3. Il minimo accettato per `--wiredTigerCacheSizeGB` è `0.25`, non `0.256`.** Con `0.1`
mongod esce prima di aprire il database: `BadValue: storage.wiredTiger.engineConfig.cacheSizeGB
must be greater than or equal to 0.25`. Con `0.25` parte e configura `268435456` byte, cioè
**esattamente 256 MiB** — lo stesso valore che sceglierebbe da solo. Con `0.256` configura
`274726912` byte, 262 MiB. Il valore `0.25` scelto in [ADR-0004](Decision.md#adr-0004) era
dunque legittimo: è il minimo, e coincide con il pavimento automatico.

**4. Una cache più grande del container non impedisce l'avvio.** `mem_limit: 512m` con
`--wiredTigerCacheSizeGB 4` parte senza errori e configura 4.096 MiB di cache in un container
da 512. Nessun avviso mette in relazione le due cifre. Compare invece, e solo quando un limite
c'è, l'avviso `id: 20720` — «Memory available to mongo process is less than total system
memory», con `availableMemSizeMB: 512` e `systemMemSizeMB: 11946`. Nel container senza limite
quell'avviso ha **zero occorrenze**: è il modo più diretto per mostrare dal vivo che mongod il
limite lo vede.

**5. L'OOM non lascia traccia nel log del container.** Un processo che alloca oltre
`mem_limit` in un container da 256 MiB senza swap viene ucciso con `SIGKILL`: `docker logs`
restituisce **zero righe**, e l'unico posto dove il fatto è registrato è
`docker inspect`, che riporta `OOMKilled=true`, `ExitCode=137` ed `Error=""` — vuoto. 137 è
128 + 9.

**6. `cpus` strozza davvero, e nella proporzione dichiarata.** Un ciclo occupato in bash,
tempo di CPU sul tempo di parete: senza limite 3,946 s su 3,947 s, rapporto **1,00**; con
`--cpus 0.5` 1,541 s su 3,069 s, rapporto **0,502**. `docker stats` mostra la colonna
`MEM USAGE / LIMIT` come `228.2MiB / 640MiB` nel container limitato e `78.48MiB / 11.67GiB` in
quello libero: è la lettura più leggibile su un proiettore.

- **Riserve:** il punto 1 vale per Compose v5.4.0; la documentazione continua a non affermarlo
  [S-004](#s-004), quindi resta una misura, non una garanzia, e va rifatta se la versione di
  Compose cambia. Il punto 5 è stato prodotto con un allocatore artificiale, non con un mongod
  sotto carico: che l'OOM di un mongod reale si presenti allo stesso modo è plausibile ma non
  misurato qui. Il punto 6 misura una CPU occupata in un ciclo, non un carico MongoDB, dove il
  rapporto dipende anche dall'attesa su I/O. Tutto è misurato su MongoDB 7.0.40: il minimo
  della cache e il pavimento potrebbero differire su altre versioni.
- **Data:** 2026-08-25
- **Usata da:** ADR-0004, ADR-0013, ADR-0025

---

<a id="v-010"></a>
### V-010 — `--logpath` redirige, non duplica; e `logRotate` su stdout dice «ok» senza fare niente

- **Comandi:** `docker run -d mongo@sha256:… mongod` · lo stesso con
  `mongod --logpath /tmp/mongod.log` · `docker logs` · `docker exec … wc -l /tmp/mongod.log` ·
  `mongod --help` · `db.adminCommand({logRotate: 1})` · `ls -la /tmp/`
- **Ambiente:** Docker 29.7.2, immagine `mongo` 7.0.40 pinnata per digest, host macOS 26.6.2
  arm64, 2026-08-28

**1. Le stesse righe, in un posto o nell'altro, mai in tutti e due.** Due container dalla stessa
immagine, avviati a un minuto di distanza, con una sola differenza nel comando:

| Comando | righe in `docker logs` | righe nel file |
|---|---|---|
| `mongod` | **65** | nessun file |
| `mongod --logpath /tmp/mongod.log` | **0** | **65** |

Sessantacinque righe in entrambi i casi. La somma non cambia, cambia solo dove finiscono. Il
container con `--logpath` è vivo e servente — risponde a `ping` e scrive nel file — ma
`docker logs` su di lui non restituisce nemmeno una riga.

**2. Lo dice il binario stesso, non solo il manuale.** `mongod --help` dentro l'immagine del lab:

> `--logpath arg` — «Log file to send write to instead of stdout - has to be a file, not
> directory»

*Instead of*. È la stessa parola del manuale [S-032](#s-032), ma detta dall'eseguibile che
gireremo davvero, alla versione che gireremo davvero: la fonte più difficile da contestare.

**3. Quindi l'assunto del design è falso.** Il design §5.3 prevedeva un «doppio canale di log
deliberato: stdout (per `docker compose logs`) **e** file `--logpath`». Quel canale doppio non
esiste, e non si tratta di un'opzione da trovare: le destinazioni sono tre — stdout, file,
syslog — e sono mutuamente esclusive. Deciso in [ADR-0030](Decision.md#adr-0030).

**4. `logRotate` riporta successo anche quando non ha niente da ruotare.** Stesso comando sui due
container:

| Destinazione del log | Risposta | Nel log | Effetto sul filesystem |
|---|---|---|---|
| stdout | `{"ok":1}` | `"msg":"Log rotation initiated"`, `"logType":null` | **nessuno** |
| file | `{"ok":1}` | idem | `mongod.log` rinominato in `mongod.log.2026-08-28T10-53-19`, nuovo `mongod.log` da 2.667 byte |

Le due risposte sono indistinguibili. Un amministratore che ruota i log di un container e
controlla il valore di ritorno riceve conferma di un'operazione che non è avvenuta. È il tipo di
successo apparente che si scopre mesi dopo, quando serve il log vecchio e non c'è.

- **Riserve:** misurato senza `--fork`, che nel container non si usa mai perché `mongod` deve
  restare in primo piano come PID 1. Con `--fork` il manuale richiede `--logpath`, quindi il caso
  «entrambi i canali» non si ripresenta nemmeno lì. Non è stato provato `--syslog`: nel container
  non c'è un demone syslog a cui scrivere.
- **Data:** 2026-08-28
- **Usata da:** ADR-0030

---

<a id="v-011"></a>
### V-011 — Il driver `json-file` non ruota niente se non glielo si chiede

- **Comandi:** `docker info --format '{{.LoggingDriver}}'` ·
  `docker inspect --format '{{json .HostConfig.LogConfig}}'` · `docker logs … | wc -l` ·
  `docker logs … | wc -c` · `docker logs … | grep -c 'Connection ended'`
- **Ambiente:** Docker 29.7.2, host macOS 26.6.2 arm64, 2026-08-28

**1. Il driver predefinito è `json-file` e nasce senza configurazione.**

```
docker info --format '{{.LoggingDriver}}'   →  json-file
docker inspect … '{{json .HostConfig.LogConfig}}'  →  {"Type":"json-file","Config":{}}
```

`Config` vuoto significa nessun `max-size` e nessun `max-file`. Con `max-size` predefinito a
`-1 (unlimited)` [S-033](#s-033), il file di log del container cresce finché c'è disco. Il
manuale non lo dice in una frase: lo si mette insieme da una cella di tabella e da un oggetto
JSON vuoto.

**2. Un nodo che non fa niente scrive comunque, e non poco.** Lo stack 01 lasciato acceso senza
alcun carico, misurato dopo 10 minuti e 33 secondi di funzionamento:

| Grandezza | Valore |
|---|---|
| righe in `docker logs` | **1.498** |
| byte in `docker logs` | **551.856** |
| di cui `"Connection ended"` | **305** |
| ritmo | ≈ 142 righe/minuto, ≈ 52 KiB/minuto |

Non c'era nessun client collegato. Le 305 connessioni sono l'**healthcheck**: sessantatré
esecuzioni di `mongosh` a dieci secondi l'una dall'altra, cinque connessioni per esecuzione. Il
controllo che serve a sapere se il nodo sta bene è, a nodo fermo, la sorgente pressoché unica del
suo log. Estrapolando: un'ora di talk con lo stack acceso e inoperoso fa circa 3 MiB.

**3. E sotto carico è la demo stessa a scrivere.** `mongod` registra una riga all'apertura e una
alla chiusura di ogni connessione. La demo sulle prestazioni apre e chiude connessioni a raffica,
per definizione — è quello che misura. Il canale di log scelto in
[ADR-0030](Decision.md#adr-0030) è stdout, e su stdout `logRotate` risponde `ok` senza fare
niente [V-010](#v-010). Sommate le tre cose — nessun limite predefinito, un flusso che non si
ferma nemmeno a vuoto, e il comando di rotazione che non morde — la demo che dimostra le
prestazioni è anche quella che riempie il disco. Con `max-size: 10m` e `max-file: 3` il tetto è
30 MiB e la questione non si pone.

- **Riserve:** `docker info` riporta il driver predefinito di *questo* daemon. Su un host che ha
  già configurato `log-driver` in `/etc/docker/daemon.json` il valore è un altro, e i due limiti
  scritti nel file Compose potrebbero non applicarsi allo stesso modo. È il motivo per cui il
  file Compose dichiara anche `driver: json-file` invece di limitarsi alle opzioni.
- **Data:** 2026-08-28
- **Usata da:** ADR-0030

---

<a id="v-012"></a>
### V-012 — Lo stack 01 alla prima accensione: salute, cache, limiti, e un'opzione che non abbiamo scritto

- **Comandi:** `docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml up -d` ·
  `docker inspect --format '{{json .State.Health}}'` · `db.serverStatus()` · `db.hostInfo()` ·
  `cat /proc/1/cmdline` · connessione TCP alla 27017 dall'host
- **Ambiente:** Docker 29.7.2, Compose v5.4.0, immagine `mongo` 7.0.40 pinnata per digest, host
  macOS 26.6.2 arm64, 2026-08-28

**1. Sano in 5,46 secondi.** Container avviato alle `10:55:05.631`, primo controllo di salute
concluso con esito `0` alle `10:55:11.093`. Il `start_period: 20s` dichiarato nel file non è
stato consumato nemmeno per un terzo — ed è giusto così: serve al caso peggiore, non al caso
normale.

Un dettaglio inatteso: il primo controllo è partito a **+5,07 s**, non a +10 s come farebbe
supporre `interval: 10s`. Il secondo è partito a +15,4 s, cioè dieci secondi dopo il primo. La
spiegazione più probabile è che durante lo `start_period` Docker sondi a un ritmo più fitto, ma
questo è un comportamento osservato e non una lettura del manuale: qui è registrato come
osservazione, non come regola.

**2. I limiti dichiarati sono quelli che `mongod` vede.** Conferma di [V-009](#v-009) sullo stack
vero invece che su un banco di prova:

| Grandezza | Dichiarato nel Compose | Letto da dentro |
|---|---|---|
| memoria | `mem_limit: 1024m` | `hostInfo().system.memLimitMB` = **1024** |
| cache | `--wiredTigerCacheSizeGB 0.25` | `maximum bytes configured` = **268435456** = 256 MiB esatti |
| versione | digest `sha256:b6421fd…` | `serverStatus().version` = **7.0.40** |

`0.25` GiB fa 256 MiB tondi. È la cifra che [V-009](#v-009) aveva già isolato smontando il
`0.256` del manuale, e che qui si conferma sul file che andrà in scena.

**3. Il costo dell'healthcheck.** `mongosh --quiet --eval "db.adminCommand('ping').ok"`:

| Condizione | Durata |
|---|---|
| container senza limiti di CPU | 317 ms |
| dentro `cpus: 1.0` | 392 ms e 385 ms |

Circa quattro decimi di secondo ogni dieci, cioè il 4% di una CPU che è tutta la CPU che il nodo
ha. Non è gratis, ed è il motivo per cui `interval` resta a 10 secondi e non scende. `mongosh` è
un processo Node: il costo è quasi tutto avvio dell'interprete, non lavoro del database.

C'è un secondo costo, meno ovvio, che si vede solo guardando il log: ogni esecuzione apre cinque
connessioni, e ciascuna lascia due righe. A nodo fermo l'healthcheck è la sorgente pressoché
unica del log, 142 righe al minuto [V-011](#v-011). Il controllo che dice se il nodo sta bene è
anche la cosa che scrive di più quando il nodo non fa nient'altro.

**4. L'immagine aggiunge un'opzione che non abbiamo scritto.** Il comando dichiarato nel Compose
è `mongod --wiredTigerCacheSizeGB 0.25`. Quello che gira è:

```
mongod --wiredTigerCacheSizeGB 0.25 --bind_ip_all
```

`--bind_ip_all` lo mette l'entrypoint ufficiale [S-022](#s-022), non noi. Fuori da un container
sarebbe una decisione da prendere con attenzione: qui è ragionevole, perché l'unica strada verso
il processo è la porta che `ports:` pubblica. Ma va detto ad alta voce, perché lo stack 01 gira
**anche senza autenticazione**: le due cose insieme fanno un `mongod` che accetta chiunque
raggiunga la porta, e il solo motivo per cui non è un problema è che la porta è mappata su
`localhost`. Cambiare quella riga senza accorgersene apre il database alla rete.

`mongod` è **PID 1**: riceve direttamente il `SIGTERM` di `docker stop`, quindi chiude in modo
pulito senza bisogno di un init intermedio.

**5. La porta risponde dall'host.** Connessione TCP a `127.0.0.1:27017` riuscita entro il timeout
di 3 secondi, a container sano.

- **Riserve:** il tempo di salute è misurato con l'immagine già in cache locale e con il volume
  `dati` appena creato, cioè vuoto. Al primo avvio con dati dentro e cache WiredTiger da
  ricostruire il numero sarà più alto; il `start_period` esiste per quello. Il costo di `mongosh`
  è misurato su questo host arm64: su una macchina più lenta cresce, e con esso la pressione sul
  `timeout: 5s`.
- **Data:** 2026-08-28
- **Usata da:** ADR-0030

---

<a id="v-013"></a>
### V-013 — Il dataset di demo è deterministico; e il generatore che sembrava buono non lo era

- **Comandi:** `docker compose … down -v` seguito da `up -d`, due volte ·
  `db.ordini.aggregate([{$group:{_id:"$citta", n:{$sum:1}}}])` ·
  `$group` su `null` con `$sum` di `importo` e `righe` · `db.ordini.findOne({_id: 0})`
- **Ambiente:** stack `docker/01-standalone`, immagine `mongo` 7.0.40 pinnata per digest,
  `mongosh` 2.10.0, host macOS 26.6.2 arm64, 2026-08-28

**1. Il primo generatore distribuiva malissimo, e si vedeva solo contando.** La prima versione di
`10-dati-demo.js` usava il congruenziale lineare che si scrive a memoria,
`seme = (seme * 1103515245 + 12345) % 2147483648`, e sceglieva la città con `seme % 10`. Su
50.000 ordini e dieci città:

| Città | LCG, `% 10` | xorshift 32 bit |
|---|---:|---:|
| Ancona | 9.862 | 4.992 |
| Bologna | **20** | 4.977 |
| Cagliari | 9.956 | 5.068 |
| Firenze | **57** | 4.899 |
| Genova | 10.076 | 5.038 |
| Milano | **28** | 5.090 |
| Napoli | 9.592 | 5.045 |
| Palermo | **49** | 4.904 |
| Roma | 10.285 | 4.968 |
| Torino | **75** | 5.019 |

Cinque città con diecimila ordini e cinque con qualche decina. Sono due difetti sovrapposti. Il
noto: in un LCG i **bit bassi hanno periodo cortissimo**, e `% 10` guarda proprio quelli. Il meno
noto, e specifico di JavaScript: `seme * 1103515245` arriva a 2,4·10^18 e **sfonda i 2^53 interi
rappresentabili in modo esatto** in un `Number`, quindi il modulo viene applicato a un valore già
arrotondato. Il generatore non era quello che il codice sembrava dire.

Lo xorshift a 32 bit usa solo operatori bit a bit, che JavaScript definisce su interi a 32 bit
con segno: nessun arrotondamento è possibile, e i bit bassi valgono quanto gli altri. La
distribuzione risultante sta fra 4.899 e 5.090 contro 5.000 attesi. Sui cinque stati, fra 9.882 e
10.178 contro 10.000.

Perché conta per una demo e non solo per l'eleganza: la demo confronta la stessa interrogazione
con e senza indice. Con la prima distribuzione, `{citta: "Bologna"}` avrebbe restituito venti
documenti e `{citta: "Roma"}` diecimila — la differenza fra le due misure sarebbe stata la
selettività, non l'indice.

**2. Due caricamenti da volume vuoto danno lo stesso dataset, byte per byte.** Ciclo completo
`down -v` → `up -d` eseguito due volte di fila, e ogni volta:

| Impronta | Valore |
|---|---|
| documenti | 50.000 |
| somma di `importo` | 124.861.860,70 |
| somma di `righe` | 150.281 |
| `_id: 0` | `cliente-1279`, Torino, in lavorazione, 4121.44, 2026-05-24 |

Identiche. È la proprietà che serve davvero: se la demo dal vivo va storta e si passa alla
registrazione di riserva, i numeri sullo schermo devono essere gli stessi, altrimenti il pubblico
vede il salto.

**3. Il caricamento non pesa sull'avvio.** 50.000 documenti in **1.745 ms**, in dieci `insertMany`
da 5.000. Lo `start_period: 20s` dell'healthcheck copre il caricamento con un margine ampio: la
fase di init avviene prima che `mongod` accetti connessioni TCP, quindi un seed lento si
presenterebbe come un nodo che tarda a diventare sano.

- **Riserve:** l'uguaglianza è verificata su tre aggregati e un documento, non confrontando i
  50.000 documenti uno per uno. Tre somme indipendenti che coincidono sono una prova forte, non
  una dimostrazione. La riproducibilità è garantita dalla semantica di JavaScript sugli interi a
  32 bit, che è specificata: non dipende dalla macchina, ma dipende dal fatto che il motore sia
  conforme, e qui è stato provato solo su `mongosh` 2.10.0.
- **Data:** 2026-08-28
- **Usata da:** ADR-0031

---

<a id="v-014"></a>
### V-014 — L'entrypoint salta gli script di inizializzazione su un volume popolato, e non lo dice

- **Comandi:** `db.ordini.deleteMany({})` · `docker compose … down` (**senza** `-v`) ·
  `docker compose … up -d` · `db.ordini.countDocuments()` ·
  `docker logs … | grep -ciE 'initdb|Carico|Caricati'`
- **Ambiente:** stack `docker/01-standalone` con `./init` montata su
  `/docker-entrypoint-initdb.d`, immagine `mongo` 7.0.40 pinnata per digest, 2026-08-28

**1. La sequenza.** Volume popolato dai 50.000 ordini del seed. Si svuota la collezione, si ferma
lo stack **conservando il volume**, si riavvia:

| Momento | `lab.ordini.countDocuments()` |
|---|---:|
| dopo il seed iniziale | 50.000 |
| dopo `deleteMany({})` | 0 |
| dopo `down` e `up -d` | **0** |

I dati non tornano. Lo script è nel container, montato, leggibile, e non viene eseguito.

**2. E il log non ne parla.** Sul container riavviato:

```
docker logs mongo-standalone | grep -ciE 'initdb|Carico|Caricati'   →  0
```

Zero occorrenze. Non «script saltato», non un avviso: **niente**. Il container ha comunque
prodotto 130 righe di log ed è arrivato a `healthy`, quindi il silenzio non è un log mancante: è
un silenzio scelto. Il ramo dell'entrypoint che decide di saltare non stampa nulla
[S-034](#s-034).

**3. Il criterio non è «la cartella è vuota».** L'entrypoint cerca quattro percorsi noti dentro
`dbPath` — `WiredTiger`, `journal`, `local.0`, `storage.bson` — e se ne trova uno considera il
volume già inizializzato [S-034](#s-034). Il modo di riportare il volume allo stato iniziale è
quindi `docker compose down -v`, che rimuove il volume, non `docker compose restart` e nemmeno
cancellare le collezioni.

Vale la pena dire perché la trappola morde forte proprio qui: chi lavora al lab modifica il file
del seed, riavvia, e non vede cambiare niente. Il ciclo di lavoro naturale — modifica, riavvia,
guarda — dà un esito che sembra dire «la mia modifica non funziona», mentre quello che sta
succedendo è «la mia modifica non è stata nemmeno letta».

- **Riserve:** provato sullo stack 01 con volume nominato. Con un bind mount di `/data/db` il
  criterio è lo stesso — sono gli stessi quattro percorsi — ma `down -v` non basta a ripulire,
  perché il volume non è di Docker: bisogna cancellare la cartella sull'host. Non provato qui,
  perché il lab non usa bind mount per i dati.
- **Data:** 2026-08-28
- **Usata da:** ADR-0031

---

<a id="v-015"></a>
### V-015 — Cosa un'istanza singola rifiuta, e cosa accetta senza dare niente in cambio

- **Comandi:** `db.getSiblingDB("local").getCollectionNames()` · `db.ordini.watch()` ·
  `rs.status()` · `insertOne(…, {writeConcern: {w: 2}})` ·
  `insertOne(…, {writeConcern: {w: "majority"}})` · `mongodump --oplog --out=…`
- **Ambiente:** stack `docker/01-standalone` avviato e `healthy`, `mongo` 7.0.40 pinnata per
  digest, `mongodump` 100.18.0 (dentro l'immagine), 2026-08-28

**1. L'oplog non c'è, e si vede da dentro.**

```
collezioni in local: startup_log
```

Una sola collezione. Nessuna `oplog.rs`. È la verifica diretta di ciò che [S-037](#s-037) lascia
solo intendere.

**2. Le quattro risposte, affiancate.** La colonna che conta è l'ultima.

| Richiesta | Esito | Messaggio | Chi se ne accorge |
|---|---|---|---|
| `db.ordini.watch()` | errore | `Location40573` · «The $changeStream stage is only supported on replica sets» | subito, ed è chiarissimo |
| `rs.status()` | errore | `NoReplicationEnabled` (76) · «not running with --replSet» | subito, ed è chiarissimo |
| `w: 2` | errore | `BadValue` (2) · «cannot use 'w' > 1 when a host is not replicated» | subito, ed è chiarissimo |
| `w: "majority"` | **riesce**, `acknowledged: true` | nessuno | **nessuno** |

Le prime tre sono buone notizie: il server dice di no, dice perché, e lo dice al primo tentativo.
La quarta è la sola che vale la pena raccontare dal palco. Un'applicazione scritta per un replica
set, che chiede diligentemente `w: "majority"` a ogni scrittura importante, puntata su
un'istanza singola **continua a funzionare**: nessun errore, nessun avviso, e una garanzia in meno
di quella che il codice crede di avere. La maggioranza di un nodo è quel nodo.

**3. `mongodump --oplog`, e il messaggio che manda fuori strada.** Due tentativi, due errori
diversi, nessuno dei quali nomina il problema vero:

```
$ mongodump --oplog --db=lab --out=/tmp/dump-prova
Failed: bad option: --oplog mode only supported on full dumps

$ mongodump --oplog --out=/tmp/dump-prova
Failed: error getting oplog start: error getting recent oplog entry: mongo: no documents in result
```

Il primo messaggio è corretto e utile. Il secondo è corretto e inutile: «no documents in result»
descrive il sintomo — la collezione interrogata è vuota, perché non esiste — e non la causa, che è
«questa istanza non è un membro di un replica set, quindi un backup a caldo coerente non è
ottenibile qui». Chi legge quella riga alle due di notte cerca il documento mancante. Nessuna
cartella viene creata: il comando fallisce prima di scrivere.

- **Riserve:** provato su `mongodump` 100.18.0, quello che viaggia dentro l'immagine `mongo` 7.0.40.
  Il testo dei messaggi appartiene ai Database Tools e ha una numerazione di versione propria
  ([S-011](#s-011)): può cambiare senza che cambi MongoDB. Il comportamento — fallire — è la parte
  stabile; le parole no.
- **Data:** 2026-08-28
- **Usata da:** ADR-0032

---

<a id="v-016"></a>
### V-016 — Cento documenti confermati all'applicazione e persi: la finestra di `w: 1`, misurata

- **Comandi:** `mongosh --eval 'for (let i = 1; i <= 500000; i++) { db.prova_durabilita.insertOne({_id: i}); print(i); }'`
  (uscita rediretta su file) · `docker kill -s KILL mongo-standalone` · `docker inspect` ·
  `docker compose up -d --wait` · `db.prova_durabilita.countDocuments()`
- **Ambiente:** stack `docker/01-standalone`, `mongo` 7.0.40 pinnata per digest, collezione
  `lab.prova_durabilita` separata dal dataset di demo, 2026-08-28

**1. La misura.** Uno scrittore inserisce documenti **uno alla volta**, con la write concern
predefinita (`w: 1`, `j` non specificato), e stampa l'`_id` di ogni inserimento **dopo** che il
server lo ha confermato. A metà corsa, `SIGKILL` al container: nessuna chiusura pulita, nessun
flush di cortesia.

| Grandezza | Valore |
|---|---:|
| ultimo `_id` confermato al client | 41.558 |
| documenti sopravvissuti al riavvio | 41.458 |
| `_id` massimo sopravvissuto | 41.458 |
| **documenti confermati e perduti** | **100** |

Cento scritture per cui l'applicazione aveva ricevuto un `acknowledged: true` non esistono più.
Non è un difetto di MongoDB: è esattamente ciò che [S-035](#s-035) descrive («In memory») e
[S-036](#s-036) quantifica («At every 100 milliseconds»), letto su un'installazione vera invece
che su una tabella.

**La prova è a senso unico, ed è giusto dirlo.** L'uscita dello scrittore passa per una pipe, che
può essere bufferizzata: il file potrebbe contenere **meno** ack di quanti il client ne abbia
davvero ricevuti, mai di più. Quindi la perdita misurata è un **minimo**: sono almeno cento. Se il
conteggio dei sopravvissuti fosse risultato maggiore dell'ultimo ack registrato, la prova sarebbe
stata inconcludente e andava dichiarata tale.

**2. Cosa dice il log alla ripartenza.** Il nodo riparte da solo, e la riga che denuncia la
chiusura sporca è una sola, di severità `W`:

```json
{"t":{"$date":"2026-08-28T11:32:59.268+00:00"},"s":"W","c":"STORAGE","id":22302,
 "ctx":"initandlisten","msg":"Recovering data from the last clean checkpoint."}
```

Seguono le righe del componente `WTRECOV`, fra cui «recovery log replay has successfully finished
and ran for 173 milliseconds». Da `Recovering data…` a «Waiting for connections» (`id` 23016)
passano **1,1 secondi**: il recovery di WiredTiger su questo dataset non è la parte lenta di
niente.

**3. Il dataset di demo attraversa il kill intatto.** Dopo la ripartenza, `make smoke-01` dà dodici
controlli verdi e l'impronta invariata — `50000 124861860.70 150281`. I 50.000 ordini erano in un
checkpoint da tempo; a cadere è solo ciò che stava nella finestra. La differenza fra i due esiti
sulla stessa macchina, nello stesso istante, è tutta lì.

**4. Lo stato del container dopo il kill.**

```
Status=exited OOMKilled=false ExitCode=137 RestartCount=0
```

`OOMKilled=false` con `ExitCode=137` è la conferma, arrivata per un'altra strada, di ciò che
[V-009](#v-009) dichiarava già: il 137 da solo non dice chi ha ucciso il processo. Il
`RestartCount=0` su un container con `restart: unless-stopped` è un fatto separato e più
sorprendente, misurato nella stessa sessione e registrato dove gli compete, in
[V-017](#v-017).

- **Riserve:** un solo tentativo, su una sola macchina, con inserimenti uno alla volta. Il numero
  «cento» non è una costante di MongoDB: è quanti inserimenti stavano nella finestra **su questo
  hardware, a questo ritmo**. Con inserimenti in lotto, con `j: true`, o su un disco diverso il
  numero cambia; quello che non cambia è che la finestra esista. Non è stato provato lo stesso
  esperimento con `j: true`, che secondo [S-035](#s-035) dovrebbe azzerare la perdita al prezzo
  della velocità: è la misura naturale da aggiungere quando l'applicazione Python
  (`feature/04`) potrà farla sotto carico controllato.
- **Data:** 2026-08-28
- **Usata da:** ADR-0032
