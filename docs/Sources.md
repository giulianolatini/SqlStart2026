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
- **Usata da:** ADR-0005, ADR-0014, ADR-0037

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
- **Usata da:** ADR-0005, ADR-0040

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
- **Usata da:** ADR-0009, ADR-0018, ADR-0039

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
- **Usata da:** ADR-0005, ADR-0026, ADR-0040, ADR-0042, ADR-0043

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
- **Usata da:** ADR-0030, ADR-0045

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
- **Usata da:** ADR-0030, ADR-0031, ADR-0033

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
- **Usata da:** ADR-0032, ADR-0043, ADR-0045, ADR-0046

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
- **Usata da:** ADR-0032, ADR-0046

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

<a id="s-039"></a>
### S-039 — Docker Docs: Start containers automatically

- **URL:** https://docs.docker.com/engine/containers/start-containers-automatically/
- **Editore:** Docker, Inc. — Docker Docs
- **Versione documentata:** pagina viva, consultata contro Docker Engine 29.7.2
- **Consultata:** 2026-08-28
- **Verdetto:** conferma parziale
- **Cosa afferma, primo punto — che cosa significa `unless-stopped`.** Nella tabella delle
  politiche: «Similar to `always`, except that when the container is stopped (manually or
  otherwise), it isn't restarted even after Docker daemon restarts.» E poco sotto, in prosa:
  «Docker restarts the container if it exits or if the daemon restarts, but not if you stopped
  the container yourself.»
- **Cosa afferma, secondo punto — la politica si disattiva dopo una fermata.** «If you manually
  stop a container, the restart policy is ignored until the Docker daemon restarts or the
  container is manually restarted. This prevents a restart loop.»
- **Cosa afferma, terzo punto — e non copre chi non è mai partito.** «A restart policy only takes
  effect after a container starts successfully. In this case, starting successfully means that
  the container is up for at least 10 seconds and Docker has started monitoring it.»
- **Cosa non afferma:** quali comandi contino come «stop». La pagina dice «manually or
  otherwise» e «if you manually stop a container», e non elenca mai i sottocomandi. In
  particolare `docker kill` non compare in nessun punto della pagina. Il lettore normale legge
  «kill» come «il processo è morto» e «stop» come «`docker stop`»; il demone li mette nella
  stessa casella. La differenza è misurata in [V-017](#v-017).
- **Riserve:** «manually or otherwise» copre il caso solo perché è abbastanza vaga da coprire
  tutto. Non è una frase da cui prevedere un comportamento, ed è la ragione per cui il
  comportamento è stato misurato invece che dedotto ([ADR-0024](Decision.md#adr-0024)).
- **Usata da:** ADR-0034

---

<a id="s-040"></a>
### S-040 — Docker Docs: `docker container kill`

- **URL:** https://docs.docker.com/reference/cli/docker/container/kill/
- **Editore:** Docker, Inc. — Docker Docs / CLI reference
- **Versione documentata:** pagina viva, consultata contro Docker Engine 29.7.2
- **Consultata:** 2026-08-28
- **Verdetto:** conferma parziale
- **Cosa afferma:** «The `docker kill` subcommand kills one or more containers. The main process
  inside the container is sent `SIGKILL` signal (default)». Il segnale arriva a **PID 1** del
  container, ed è il demone a mandarlo — cioè un processo del namespace antenato, il che secondo
  [S-041](#s-041) è esattamente il caso in cui `SIGKILL` viene consegnato per forza.
- **Cosa non afferma:** la parola «restart» non compare da nessuna parte nella pagina. Nulla
  avverte che un `docker kill` metta il container nello stato in cui la politica di riavvio non
  si applica più. Chi cerca «come simulo la caduta di un nodo» arriva qui, legge «kills», e non
  ha modo di sospettare che stia chiedendo una fermata invece di un guasto. Misurato in
  [V-017](#v-017).
- **Riserve:** l'assenza della parola «restart» è stata contata sulla pagina come resa il
  2026-08-28. È una pagina viva: l'assenza di oggi non è una garanzia per domani, ed è il tipo
  di affermazione che va ricontrollata prima di ripeterla dal palco.
- **Usata da:** ADR-0034

---

<a id="s-041"></a>
### S-041 — Linux man-pages: `pid_namespaces(7)`

- **URL:** https://man7.org/linux/man-pages/man7/pid_namespaces.7.html
- **Editore:** The Linux man-pages project
- **Versione documentata:** `man-pages-6.18`, come dichiarato nel colophon della pagina resa
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — dall'interno, PID 1 è intoccabile.** «Only signals for which the
  "init" process has established a signal handler can be sent to the "init" process by other
  members of the PID namespace. This restriction applies even to privileged processes, and
  prevents other members of the PID namespace from accidentally killing the "init" process.»
  Poiché `SIGKILL` non è gestibile per definizione, `kill -9 1` eseguito **dentro** un container
  non può funzionare — e infatti non funziona, senza però dare errore ([V-017](#v-017)).
- **Cosa afferma, secondo punto — dall'esterno, sì.** «`SIGKILL` or `SIGSTOP` are treated
  exceptionally: these signals are forcibly delivered when sent from an ancestor PID namespace.»
  Il demone Docker sta in quel namespace antenato: `docker kill` arriva a destinazione.
- **Cosa afferma, terzo punto — e se PID 1 muore, muoiono tutti.** «If the "init" process of a
  PID namespace terminates, the kernel terminates all of the processes in the namespace via a
  `SIGKILL` signal.» È il motivo per cui un container è vivo esattamente quanto il suo PID 1.
- **Cosa non afferma:** non nomina Docker, né i container, né `mongod`. Il collegamento — «PID 1
  del container è `mongod`, il demone Docker sta nel namespace antenato, quindi `docker kill`
  passa e `kill -9 1` no» — è nostro, e vale quanto la verifica che lo sostiene
  ([V-017](#v-017), [ADR-0024](Decision.md#adr-0024)).
- **Riserve:** è la documentazione del kernel Linux, non del runtime. Descrive un comportamento
  stabile da anni, ma la pagina è viva e la sua numerazione segue i rilasci di `man-pages`. Su
  macOS il kernel in gioco è quello della VM di Docker Desktop, non quello del portatile.
- **Usata da:** ADR-0034

---

<a id="s-042"></a>
### S-042 — MongoDB Manual 7.0: Log Messages

- **URL:** https://www.mongodb.com/docs/v7.0/reference/log-messages/ (consultata nella variante
  `log-messages.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** v7.0
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — il formato è JSON, ovunque.** «All log output is in JSON format
  including output sent to: Log file · Syslog · Stdout (standard out)». Ogni voce è «a
  self-contained JSON object which follows the Relaxed Extended JSON v2.0 specification», con
  ordine dei campi fissato:

  ```javascript
  {
    "t": <Datetime>, // timestamp
    "s": <String>, // severity
    "c": <String>, // component
    "id": <Integer>, // unique identifier
    "ctx": <String>, // context
    "msg": <String>, // message body
    "attr": <Object> // additional attributes (optional)
    "tags": <Array of strings> // tags (optional)
    "truncated": <Object> // truncation info (if truncated)
    "size": <Object> // original size of entry (if truncated)
  }
  ```

- **Cosa afferma, secondo punto — `id` è un identificatore univoco.** La tabella dei campi lo
  descrive come «Unique identifier for the log statement», e la pagina dedica un esempio al
  «Filtering by Known Log ID». È il campo su cui si filtra: il `msg` è testo, l'`id` è una
  chiave.
- **Cosa afferma, terzo punto — le severità.** «Severity levels range from "Fatal" (most severe)
  to "Debug" (least severe)»: `F` Fatal, `E` Error, `W` Warning, `I` Informational (verbosità
  `0`), `D1`–`D5` Debug (verbosità > `0`). E sulla verbosità: «Severity categories above these
  levels are always shown.»
- **Cosa afferma, quarto punto — i componenti hanno una gerarchia.** `REPL` è il componente
  genitore di `ELECTION`, `INITSYNC`, `REPL_HB` e `ROLLBACK`; `STORAGE` lo è di `JOURNAL` e
  `RECOVERY`. Se la verbosità del figlio non è impostata, MongoDB usa quella del genitore. Sui
  due che servono al talk: `ELECTION` raccoglie i «messages related specifically to replica set
  elections», `REPL_HB` quelli «related specifically to replica set heartbeats».
- **Cosa afferma, quinto punto — c'è un tag per gli avvisi d'avvio.** Fra gli esempi di `tags`,
  testuale: `["startupWarnings"]`.
- **Cosa non afferma:** quali `id` compaiano in quale situazione. Non esiste nella pagina un
  catalogo degli identificatori: si scoprono leggendo il log di un'installazione vera. Quelli di
  questo stack sono censiti in [V-019](#v-019).
- **Riserve:** la pagina descrive il formato, non il contenuto. Dice che `id` è univoco, e non
  promette da nessuna parte che il testo di `msg` sia stabile fra versioni — che è esattamente
  la ragione per cui in questo repository si cita l'`id` ([ADR-0035](Decision.md#adr-0035)).
- **Usata da:** ADR-0035

---

<a id="s-043"></a>
### S-043 — MongoDB Manual 7.0: `logRotate` (database command)

- **URL:** https://www.mongodb.com/docs/v7.0/reference/command/logRotate/ (consultata nella
  variante `logRotate.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** v7.0
- **Consultata:** 2026-08-28
- **Verdetto:** conferma parziale
- **Cosa afferma, primo punto — a cosa serve e come si invoca.** Il comando «allows you to rotate
  the MongoDB server log and/or audit log to prevent a single logfile from consuming too much
  disk space», e va emesso sul database `admin`. L'argomento `1` ruota entrambi i log,
  `"server"` solo quello del server, `"audit"` solo quello di audit.
- **Cosa afferma, secondo punto — c'è anche la via del segnale.** «You may also rotate the logs
  by sending a `SIGUSR1` signal to the `mongod` process.»
- **Cosa afferma, terzo punto — e questa è la riga che conta.** Sotto *Limitations*, testuale:
  «Your `mongod` instance needs to be running with the `--logpath [file]` option in order to use
  `logRotate`». Il limite **è documentato**.
- **Cosa afferma, quarto punto — le due modalità.** Con `systemLog.logRotate` a `rename` il file
  esistente viene rinominato aggiungendo un timestamp nella forma
  `<YYYY>-<mm>-<DD>T<HH>-<MM>-<SS>` e ne viene creato uno nuovo; con `reopen` il file viene
  chiuso e riaperto con lo stesso nome, lasciando a un altro processo il compito di rinominarlo.
- **Cosa non afferma:** che cosa succeda se si invoca il comando **senza** `--logpath`. La
  sezione *Limitations* dice che serve, e non dice che il comando fallisca. Non fallisce:
  risponde `{ok: 1}` e non fa niente ([V-010](#v-010)). Fra «documentato come limite» e
  «applicato dal server» c'è la distanza che rende utile questo repository.
- **Riserve:** il limite riguarda il file di log, non il log in sé. In container, dove il log va
  su stdout per scelta ([ADR-0030](Decision.md#adr-0030)), il comando non ha semplicemente
  nulla su cui agire, e la rotazione è affare del runtime.
- **Usata da:** ADR-0035

---

<a id="s-044"></a>
### S-044 — MongoDB Manual 7.0: Replica Set Elections

- **URL:** https://www.mongodb.com/docs/v7.0/core/replica-set-elections/ (consultata nella
  variante `replica-set-elections.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** v7.0
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — quando parte un'elezione.** Fra gli eventi elencati: l'aggiunta
  di un nodo, `rs.initiate()`, la manutenzione con `rs.stepDown()` o `rs.reconfig()`, e «the
  secondary members losing connectivity to the primary for more than the configured timeout (10
  seconds by default)».
- **Cosa afferma, secondo punto — i battiti e la soglia.** «Replica set members send heartbeats
  (pings) to each other every two seconds. If a heartbeat does not return within 10 seconds, the
  other members mark the delinquent member as inaccessible.»
- **Cosa afferma, terzo punto — quanto dura, e cosa si ferma nel frattempo.** «The median time
  before a cluster elects a new primary should not typically exceed 12 seconds, assuming default
  replica configuration settings.» E, prima: «The replica set cannot process write operations
  until the election completes successfully», mentre le letture possono continuare se sono
  configurate per andare sui secondari.
- **Cosa non afferma:** quali righe di log accompagnino un'elezione. La pagina descrive il
  meccanismo, mai il suo tracciato nel log. I componenti in cui guardare si ricavano da
  [S-042](#s-042) — `ELECTION` e `REPL_HB` — ma gli `id` delle righe si conoscono solo dopo
  averne vista una.
- **Riserve:** è la fonte su cui poggia la sezione «cosa cercare durante un'elezione» di
  `docs/03-amministrazione/log.md`, che per questa ragione è **dichiarata non verificata** su
  questo branch: qui non esiste un replica set. La verifica è dovuta a `feature/02`
  ([ADR-0035](Decision.md#adr-0035)).
- **Usata da:** ADR-0035, ADR-0036, ADR-0044, ADR-0045, ADR-0046

---

<a id="s-045"></a>
### S-045 — MongoDB Shell: Connect to a Deployment

- **URL:** https://www.mongodb.com/docs/mongodb-shell/connect/ (consultata nella variante
  `connect.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / MongoDB Shell
- **Versione documentata:** `mongosh` corrente alla consultazione; il lab usa la **2.10.0**
  contenuta nell'immagine `mongo:7.0.40`
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — senza argomenti va su localhost.** «To connect to a MongoDB
  deployment running on **localhost** with **default port** 27017, run `mongosh` without any
  options». E per le opzioni separate: «The `--host` and `--port` command-line options. If you
  omit the `--port` option, `mongosh` uses the default port 27017.»
- **Cosa afferma, secondo punto — il database predefinito è `test`.** «To connect to a specific
  default database, specify a database in your connection string URI path. If unspecified by the
  connection string, the default database is the `test` database.» Da cui la forma
  `mongosh "mongodb://localhost:27017/qa"`.
- **Cosa afferma, terzo punto — la connessione diretta è implicita, e ha quattro eccezioni.**
  «When you specify individual replica set members in the connection string, `mongosh`
  automatically adds the `directConnection=true` parameter, unless at least one of the following
  is true»: c'è il parametro `replicaSet`; la stringa usa il formato `mongodb+srv://`; la stringa
  contiene una seed list con più host; la stringa contiene già `directConnection`. È la regola che
  decide se si sta parlando con **un nodo** o con **un replica set**, e da `feature/02` in poi
  fa la differenza fra leggere un secondario e leggere il primario.
- **Cosa afferma, quarto punto — `+srv` implica TLS.** «When you use the `+srv` connection string
  modifier, MongoDB automatically sets the `--tls` option to `true`.»
- **Cosa non afferma:** il valore predefinito di `serverSelectionTimeoutMS`. La pagina non lo
  nomina. `mongosh` 2.10.0 lo imposta a **2000 ms** e lo si scopre solo leggendo la stringa che
  costruisce da sé ([V-020](#v-020)) — un dettaglio che conta quando il server dall'altra parte è
  un replica set in mezzo a un'elezione, che [S-044](#s-044) dà per lunga fino a dodici secondi.
- **Riserve:** la pagina è scritta pensando ad Atlas e a installazioni sull'host. Il caso di
  questo lab — `mongosh` che vive **dentro** il container a cui si connette — non è contemplato,
  e cambia il significato di «localhost» ([V-018](#v-018)).
- **Usata da:** ADR-0036, ADR-0045

---

<a id="s-046"></a>
### S-046 — MongoDB Shell: Options (riferimento della riga di comando)

- **URL:** https://www.mongodb.com/docs/mongodb-shell/reference/options/ (consultata nella
  variante `options.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / MongoDB Shell
- **Versione documentata:** `mongosh` corrente alla consultazione; misurata la 2.10.0
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — `--eval` si può ripetere, e stampa solo l'ultimo.** «Evaluates a
  JavaScript expression. You can use a single `--eval` argument or multiple `--eval` arguments
  together.» E poi la regola che sorprende: «After `mongosh` evaluates the `--eval` argument, it
  prints the results to your command line. If you use multiple `--eval` statements, `mongosh`
  only prints the results of the last `--eval`.»
- **Cosa afferma, secondo punto — `--quiet` è già acceso quando non c'è un umano.** Sotto
  `--no-quiet`: «Disables the default `--quiet` option mode for non-interactive shell sessions.
  When specified, `mongosh` displays all messages during startup.» E, esplicitamente: «For
  non-interactive shell sessions, MongoDB enables `--quiet` by default.» Di `--quiet` dice che
  «Skips all messages during startup (such as welcome messages and startup warnings) and goes
  directly to the prompt».
- **Cosa afferma, terzo punto — `--json` e le sue due modalità.** «You can use the `--json` flag
  with `--eval` to return `mongosh` results in Extended JSON format. `mongosh` supports both
  `--json=canonical` and `--json=relaxed` modes. If you omit the mode, `mongosh` defaults to the
  `canonical` mode. The `--json` flag is mutually exclusive with `--shell`.»
- **Cosa afferma, quarto punto — due opzioni che rendono ripetibile uno script.**
  `--norc`: «Prevents the shell from sourcing and evaluating `~/.mongoshrc.js` on startup.»
  `--nodb`: avvia la shell senza collegarsi ad alcun server.
- **Cosa non afferma:** **i codici di uscita.** In tutta la pagina non c'è una tabella, né una
  frase, che dica con quale codice `mongosh` termini in caso di errore. Chi scrive uno script di
  automazione deve misurarlo, ed è quello che fa [V-020](#v-020).
- **Riserve:** il comportamento predefinito di `--quiet` dipende dal fatto che la sessione sia
  «non interattiva», nozione che la pagina non definisce. Nel lab la stessa riga di comando può
  finire in uno script o essere incollata in un terminale, e per questo `--quiet` si scrive
  comunque ([ADR-0036](Decision.md#adr-0036)).
- **Usata da:** ADR-0036

---

<a id="s-047"></a>
### S-047 — MongoDB Shell: Write Scripts

- **URL:** https://www.mongodb.com/docs/mongodb-shell/write-scripts/ (consultata nella variante
  `write-scripts.md`)
- **Editore:** MongoDB, Inc. — MongoDB Docs / MongoDB Shell
- **Versione documentata:** `mongosh` corrente alla consultazione; misurata la 2.10.0
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — i file si passano con `--file`.** «To specify the filename, use
  the `--file` or `-f` parameter to specify the filename», e più oltre, in grassetto nella
  pagina: «To pass filenames always use `--file` or `-f`.» L'opzione si ripete:
  `mongosh --file loadMovies.js --file queryMovies.js` esegue i due file in ordine.
- **Cosa afferma, secondo punto — `load()` non cerca da nessuna parte.** «There is no search path
  for the `load()` method. If the target script is not in the current working directory or the
  full specified path, the MongoDB Shell cannot access the file.» Dentro un container, dove la
  directory di lavoro non è quella da cui si è digitato il comando, è la differenza fra uno script
  che parte e uno che non si trova.
- **Cosa afferma, terzo punto — uscire è una scelta esplicita.** «It is often useful to terminate
  a running script if an exception is thrown, or in the case of unexpected results.» Il modo è
  uno: «To terminate a script, you can call the `exit(<code>)` method, where the `<code>` is any
  user-specified value.» E la buona pratica: «As a best practice, wrap code in a `try - catch`,
  calling the `exit` method in the `catch` block. Likewise, to check the results of a query or
  any command, you can add an `if - else` statement and call the `exit` method if the results are
  not what is expected.»
- **Cosa non afferma:** che cosa succeda **senza** `exit()`. La pagina raccomanda di uscire
  esplicitamente e tace su quale codice restituisca `mongosh` quando un'eccezione non viene
  catturata, o quando la connessione fallisce. Sono i due casi che contano di più in
  automazione, e sono misurati in [V-020](#v-020).
- **Riserve:** «any user-specified value» va preso alla lettera solo fin dove arriva il sistema
  operativo. Misurato: `exit(300)` fa uscire il processo con **44** (cioè 300 modulo 256) ed
  `exit(-1)` con **255** ([V-020](#v-020)). Il valore che lo script sceglie e il valore che lo
  script di chiamata legge non sono la stessa cosa, e la pagina non avvisa.
- **Usata da:** ADR-0036

---

<a id="s-048"></a>
### S-048 — MongoDB Manual: Install MongoDB Community Edition on Ubuntu

- **URL:** https://www.mongodb.com/docs/v7.0/tutorial/install-mongodb-on-ubuntu/
- **Editore:** MongoDB, Inc. — MongoDB Manual v7.0
- **Versione documentata:** MongoDB 7.0 Community Edition, la stessa riga di versione del lab
  ([ADR-0028](Decision.md#adr-0028))
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — il pacchetto della distribuzione non va usato.** In evidenza:
  «The `mongodb` package provided by Ubuntu is **not** maintained by MongoDB Inc. and conflicts
  with the official `mongodb-org` package. If you already installed the `mongodb` package on your
  Ubuntu system, you **must** first uninstall the `mongodb` package before proceeding with these
  instructions.» Le piattaforme dichiarate per la 7.0 sono Ubuntu 22.04 LTS «Jammy» e 20.04 LTS
  «Focal», solo a 64 bit.
- **Cosa afferma, secondo punto — la procedura, in quattro passi.** Importare la chiave GPG
  pubblica (`curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o
  /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor`); creare il file di elenco
  `/etc/apt/sources.list.d/mongodb-org-7.0.list`; `sudo apt-get update`; `sudo apt-get install -y
  mongodb-org`.
- **Cosa afferma, terzo punto — che cosa crea l'installazione.** «If you installed through the
  package manager, the data directory `/var/lib/mongodb` and the log directory `/var/log/mongodb`
  are created during the installation», e «By default, MongoDB runs using the `mongodb` user
  account. If you change the user that runs the MongoDB process, you **must** also modify the
  permission to the data and log directories to give this user access to these directories.» Il
  file di configurazione è `/etc/mongod.conf`, e «if you change the configuration file while the
  MongoDB instance is running, you must restart the instance for the changes to take effect».
- **Cosa afferma, quarto punto — il servizio.** L'avvio passa dall'init system; per riconoscerlo,
  `ps --no-headers -o comm 1`. Con `systemd`: `sudo systemctl start mongod`,
  `sudo systemctl status mongod`, `sudo systemctl enable mongod` per l'avvio al riavvio,
  `stop` e `restart`. «You can follow the state of the process for errors or important messages by
  watching the output in the `/var/log/mongodb/mongod.log` file.»
- **Cosa afferma, quinto punto — `ulimit` e il `bindIp`.** «If the `ulimit` value for number of
  open files is under `64000`, MongoDB generates a startup warning.» E: «By default, MongoDB
  launches with `bindIp` set to `127.0.0.1`, which binds to the localhost network interface. This
  means that the `mongod` can only accept connections from clients that are running on the same
  machine.» Da cui il fatto che un `mongod` appena installato **non** può nemmeno inizializzare un
  replica set finché non gli si cambia quel valore.
- **Cosa non afferma:** niente su come si mette in sicurezza l'istanza dopo l'installazione, se
  non un rimando. La procedura si ferma a un server che parte, senza autenticazione, in ascolto
  su localhost.
- **Riserve:** **questa procedura non è stata eseguita.** La macchina di sviluppo è macOS con
  Docker Desktop ([V-020](#v-020)); l'unico Ubuntu 22.04 disponibile qui è quello **dentro**
  l'immagine `mongo:7.0.40`, che è installata dallo stesso repository apt ma senza `systemd`, senza
  `/etc/mongod.conf` e con percorsi diversi ([V-021](#v-021)). La pagina di installazione dichiara
  la riserva in testa ([ADR-0037](Decision.md#adr-0037)).
- **Usata da:** ADR-0037

---

<a id="s-049"></a>
### S-049 — MongoDB Manual: Install MongoDB Community Edition on Windows

- **URL:** https://www.mongodb.com/docs/v7.0/tutorial/install-mongodb-on-windows/
- **Editore:** MongoDB, Inc. — MongoDB Manual v7.0
- **Versione documentata:** MongoDB 7.0 Community Edition
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — la shell non è inclusa, e va detto due volte.** «The MongoDB Shell
  (`mongosh`) is not installed with MongoDB Server. You need to follow the `mongosh` installation
  instructions to download and install `mongosh` separately», e più avanti, per non lasciare
  scampo: «The `.msi` installer does not include `mongosh`.»
- **Cosa afferma, secondo punto — le piattaforme, e una esclusione netta.** Windows Server 2022,
  Windows Server 2019 e Windows 11, solo a 64 bit su x86\_64. E: «MongoDB is not supported on
  Windows Subsystem for Linux (WSL). To run MongoDB on Linux, use a supported Linux system.»
- **Cosa afferma, terzo punto — l'installazione è una procedura guidata.** Il `.msi` installa
  binari e file di configurazione predefinito; «The configuration file is located in the
  installation directory at `bin\mongod.cfg`». Il tipo di installazione è *Complete* o *Custom*.
  Nella schermata *Service Configuration* si sceglie se installare MongoDB come servizio di
  Windows: nome del servizio (predefinito `MongoDB`), utente con cui gira, *Data Directory* che
  corrisponde a `--dbpath` e *Log Directory* che corrisponde a `--logpath`; se le directory non
  esistono, «the installer will create the directory and sets the directory access to the service
  user».
- **Cosa afferma, quarto punto — il servizio si governa dalla console dei servizi.** Avvio e
  arresto passano da lì; per personalizzare la configurazione «you must stop the service» e poi
  modificare `<install directory>\bin\mongod.cfg`. Fuori dal servizio si può lanciare a mano:
  `"C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe" --dbpath="c:\data\db"`, dopo aver creato
  la directory dei dati, e con l'avvertenza «You must open the command interpreter as an
  Administrator». Il segnale che tutto va bene è la riga `[initandlisten] waiting for
  connections`.
- **Cosa afferma, quinto punto — il firewall e gli aggiornamenti.** Windows Defender Firewall può
  mostrare un avviso di sicurezza e bloccare «some features» di `mongod.exe`. E sugli
  aggiornamenti: «If you installed MongoDB with the Windows installer (`.msi`), the `.msi`
  automatically upgrades within its release series (e.g. 7.2.1 to 7.2.2). Upgrading a full release
  series (e.g. 6.0 to 7.0) requires a new installation.»
- **Cosa non afferma:** non contiene alcuna sezione `ulimit` — non esiste su Windows — né alcuna
  raccomandazione su THP, che è un meccanismo del kernel Linux. Le due mezze pagine di messa a
  punto che valgono su Ubuntu qui semplicemente non ci sono, e questo va detto invece di lasciarlo
  intuire.
- **Riserve:** **questa procedura non è stata eseguita.** Nessuna macchina Windows in questo
  progetto. Ogni affermazione della pagina di installazione su Windows viene da qui e da
  [S-005](#s-005), e la riserva è dichiarata in testa ([ADR-0037](Decision.md#adr-0037)).
- **Usata da:** ADR-0037

---

<a id="s-050"></a>
### S-050 — MongoDB Manual: Production Notes (Self-Managed Deployments)

- **URL:** https://www.mongodb.com/docs/v7.0/administration/production-notes/
- **Editore:** MongoDB, Inc. — MongoDB Manual v7.0
- **Versione documentata:** MongoDB 7.0
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — il filesystem.** «When running MongoDB in production on Linux, you
  should use Linux kernel version 2.6.36 or later, with either the XFS or EXT4 filesystem. If
  possible, use XFS as it generally performs better with MongoDB.» E con più forza: «With the
  WiredTiger storage engine, using XFS is **strongly recommended** for data bearing nodes to avoid
  performance issues that may occur when using EXT4 with WiredTiger.» È la raccomandazione che il
  server ripete a ogni avvio con l'`id` 22297 ([V-019](#v-019)).
- **Cosa afferma, secondo punto — RAM e CPU.** «At a minimum, ensure that each `mongod` or
  `mongos` instance has access to two real cores or one multi-core physical CPU.» Su WiredTiger:
  «Throughput *increases* as the number of concurrent active operations increases up to the number
  of CPUs», e diminuisce oltre una soglia che dipende dall'applicazione.
- **Cosa afferma, terzo punto — lo swap, con due strategie e nessuna terza.** «MongoDB performs
  best where swapping can be avoided or kept to a minimum… However, if the system hosting MongoDB
  runs out of RAM, swapping can prevent the Linux OOM Killer from terminating the `mongod`
  process.» Le due strategie ammesse: assegnare spazio di swap e configurare il kernel perché lo
  usi solo sotto forte pressione, oppure non assegnarne affatto e disabilitare del tutto lo
  scambio.
- **Cosa afferma, quarto punto — NUMA.** «Running MongoDB on a system with Non-Uniform Memory
  Access (NUMA) can cause a number of operational problems, including slow performance for periods
  of time and high system process usage.» Il rimedio è una politica di *memory interleave*: su
  Linux `sudo sysctl -w vm.zone_reclaim_mode=0` e l'avvio tramite `numactl`, sotto `systemd` da
  configurare nel file di servizio; su Windows «memory interleaving must be enabled through the
  machine's BIOS». «MongoDB checks NUMA settings on start up… If the NUMA configuration may degrade
  performance, MongoDB prints a warning.»
- **Cosa afferma, quinto punto — la rete è la prima difesa.** «Always run MongoDB in a *trusted
  environment*, with network rules that prevent access from *all* unknown computers, systems, and
  networks», e in evidenza: «By default, authorization is not enabled.»
- **Cosa non afferma:** non dà soglie numeriche per la maggior parte delle raccomandazioni — non
  dice quanto swap, non dice quanta RAM oltre il minimo di due core. Sono indicazioni di direzione,
  non un dimensionamento.
- **Riserve:** nessuna di queste messe a punto è stata applicata **né misurata su una macchina di
  produzione**. Ciò che è stato misurato è l'opposto ed è istruttivo: il container del lab viola
  tre di queste raccomandazioni e il server lo dichiara all'avvio ([V-021](#v-021)).
- **Usata da:** ADR-0037

---

<a id="s-051"></a>
### S-051 — MongoDB Manual: Disable Transparent Huge Pages (THP)

- **URL:** https://www.mongodb.com/docs/v7.0/tutorial/transparent-huge-pages/
- **Editore:** MongoDB, Inc. — MongoDB Manual v7.0
- **Versione documentata:** MongoDB 7.0
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — che cos'è e perché disturba.** «Transparent Huge Pages (THP) is a
  Linux memory management system that reduces the overhead of Translation Lookaside Buffer (TLB)
  lookups on machines with large amounts of memory by using larger memory pages.» E poi la
  ragione: «However, database workloads often perform poorly with THP enabled, because they tend to
  have sparse rather than contiguous memory access patterns. When running MongoDB on Linux, THP
  should be disabled for best performance.»
- **Cosa afferma, secondo punto — si disabilita prima che `mongod` parta.** Il modo raccomandato è
  un servizio dell'init system. Sotto `systemd`, il file
  `/etc/systemd/system/disable-transparent-huge-pages.service` con `Before=mongod.service`,
  `Type=oneshot` e
  `ExecStart=/bin/sh -c 'echo never | tee /sys/kernel/mm/transparent_hugepage/enabled > /dev/null
  && echo never | tee /sys/kernel/mm/transparent_hugepage/defrag > /dev/null'`.
- **Cosa afferma, terzo punto — il percorso non è sempre lo stesso.** «Some versions of Red Hat
  Enterprise Linux, and potentially other Red Hat-based derivatives, use a different path for the
  THP `enabled` file: `/sys/kernel/mm/redhat_transparent_hugepage/enabled`. Verify which path is in
  use on your system and update the `disable-transparent-huge-pages.service` file accordingly.» Su
  RHEL/CentOS con `tuned` o `ktune` serve in più un profilo personalizzato.
- **Cosa non afferma:** quanto si perde tenendo THP acceso. Non c'è un numero, né un intervallo:
  la pagina raccomanda e non quantifica, e questo è esattamente il motivo per cui in questo
  repository la raccomandazione viene riportata e **non** trasformata in una promessa di
  prestazioni.
- **Riserve:** non applicabile a un container. Il valore di THP appartiene al kernel dell'host —
  qui la macchina virtuale Linux di Docker Desktop, dove risulta `[always] madvise never`, cioè
  acceso, e non modificabile da dentro il container ([V-021](#v-021)). È la ragione per cui il
  `mongod` del lab emette l'avviso `9068900` a ogni avvio e non c'è niente da fare, se non saperlo.
- **Usata da:** ADR-0037

---

<a id="s-052"></a>
### S-052 — MongoDB Manual: UNIX `ulimit` Settings for Self-Managed Deployments

- **URL:** https://www.mongodb.com/docs/v7.0/reference/ulimit/
- **Editore:** MongoDB, Inc. — MongoDB Manual v7.0
- **Versione documentata:** MongoDB 7.0
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — i sette valori raccomandati.** «The following settings are
  particularly important for `mongod` and `mongos` deployments»: `-f` (file size) `unlimited`,
  `-t` (cpu time) `unlimited`, `-v` (virtual memory) `unlimited`, `-l` (locked-in-memory size)
  `unlimited`, `-n` (open files) **`64000`**, `-m` (memory size) `unlimited`, `-u`
  (processes/threads) **`64000`**. E: «Restart your `mongod` and `mongos` instances after changing
  the `ulimit` settings to apply the changes.»
- **Cosa afferma, secondo punto — perché i descrittori si consumano a due a due.** «Incoming
  connections to a `mongod` or `mongos` instance require **two** file descriptors.» Il numero da
  reggere non è quello delle connessioni: è il doppio.
- **Cosa afferma, terzo punto — sotto `systemd` non si usa `ulimit`.** «If you start a `mongod` or
  `mongos` instance as a `systemd` service, you can specify limits within the `[Service]` section
  of its service file», con `LimitFSIZE=infinity`, `LimitCPU=infinity`, `LimitAS=infinity`,
  `LimitMEMLOCK=infinity`, `LimitNOFILE=64000`, `LimitNPROC=64000`. E l'avvertenza che evita un
  errore comune: «Each `systemd` limit directive sets both the "hard" and "soft" limits to the
  value specified.»
- **Cosa afferma, quarto punto — macOS è un caso a parte.** «For the macOS platform, the
  recommended process limit is `2500`, which is the maximum configurable value for this platform.»
  Su RHEL/CentOS 7 il limite predefinito dei processi è 4096 e sta in
  `/etc/security/limits.d/20-nproc.conf`.
- **Cosa non afferma:** che cosa succede in un container. La pagina presuppone un sistema
  operativo intero con il suo init system; sotto Docker i limiti li fissa il runtime, e nel lab
  risultano già ampiamente oltre il raccomandato senza che nessuno li abbia scritti
  ([V-021](#v-021)).
- **Usata da:** ADR-0037

---

<a id="s-053"></a>
### S-053 — GitHub Docs: Basic writing and formatting syntax — Section links

- **URL:** https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax
- **Editore:** GitHub, Inc. — GitHub Docs
- **Versione documentata:** GitHub.com, versione corrente
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — le ancore le genera GitHub, non chi scrive.** «You can link
  directly to any section that has a heading. To view the automatically generated anchor in a
  rendered file, hover over the section heading to expose the icon and click the icon to display
  the anchor in your browser.» Il rimando `#1-prima-di-cominciare` funziona senza che nessuno
  abbia dichiarato quell'ancora: è il titolo a produrla.
- **Cosa afferma, secondo punto — le cinque regole di trasformazione.** «If you need to determine
  the anchor for a heading in a file you are editing, you can use the following basic rules:
  Letters are converted to lower-case. Spaces are replaced by hyphens ( - ). Any other whitespace
  or punctuation characters are removed. Leading and trailing whitespace are removed. Markup
  formatting is removed, leaving only the contents (for example, `_italics_` becomes italics). If
  the automatically generated anchor for a heading is identical to an earlier anchor in the same
  document, a unique identifier is generated by appending a hyphen and an auto-incrementing
  integer.»
- **Cosa afferma, terzo punto — lo spazio e gli altri spazi bianchi non sono la stessa cosa.** La
  seconda regola distingue: lo spazio **diventa** un trattino, ogni altro spazio bianco **sparisce**.
  Ne segue che due spazi consecutivi producono due trattini, e che nessuno li accorpa: in
  «S-001 — WiredTiger» il trattino lungo viene rimosso come punteggiatura e lascia due spazi, così
  l'ancora è `s-001--wiredtiger` e non `s-001-wiredtiger`.
- **Cosa afferma, quarto punto — le ancore esplicite sono un'altra cosa.** La sezione «Custom
  anchors» documenta la forma `<a id="..."></a>` come alternativa dichiarata, che questo
  repository usa per ADR e fonti perché un identificatore stabile non deve dipendere dal titolo.
- **Cosa non afferma:** quale sia esattamente l'insieme dei caratteri considerati «punctuation».
  La pagina dà la regola, non la classe di caratteri; per quella serve
  [S-054](#s-054).
- **Usata da:** ADR-0038

---

<a id="s-054"></a>
### S-054 — `github-slugger` — l'algoritmo delle ancore, in codice

- **URL:** https://github.com/Flet/github-slugger
- **Editore:** Dave Fletcher e collaboratori (progetto indipendente)
- **Versione documentata:** ramo `master`, file `index.js` e `regex.js`
- **Consultata:** 2026-08-28
- **Verdetto:** conferma
- **Cosa afferma, primo punto — a che cosa serve.** «Generate a slug just like GitHub does for
  markdown headings. It also ensures slugs are unique in the same way GitHub does it. The overall
  goal of this package is to emulate the way GitHub handles generating markdown heading anchors as
  close as possible.»
- **Cosa afferma, secondo punto — l'algoritmo, in tre operazioni.** Il corpo della funzione è una
  riga sola: `if (!maintainCase) value = value.toLowerCase()`, poi
  `return value.replace(regex, '').replace(/ /g, '-')`. Minuscole, via la punteggiatura, e **ogni
  singolo spazio** diventa un trattino — `/ /g`, non `/ +/g`. È la conferma eseguibile della terza
  osservazione di [S-053](#s-053).
- **Cosa afferma, terzo punto — la classe di caratteri rimossi comincia dai controlli.** La
  costante di `regex.js` si apre con `[\0-\x1F!-,\.\/:-@\[-\^`\{-\xA9...`: il primo intervallo è
  quello dei caratteri di controllo, che comprende il tabulatore (`\x09`), mentre lo spazio
  (`\x20`) resta fuori da tutta la classe. Il tabulatore quindi sparisce e lo spazio sopravvive
  fino alla sostituzione finale: esattamente la distinzione che [S-053](#s-053) enuncia a parole.
- **Cosa afferma, quarto punto — non è un parser.** «This project is not a markdown or HTML
  parser: passing `alpha *bravo* charlie` or `alpha <em>bravo</em> charlie` doesn't work.» La
  rimozione della formattazione — quarta regola di [S-053](#s-053) — avviene **prima**, quando il
  titolo viene reso; chi riproduce l'algoritmo deve toglierla per conto proprio.
- **Cosa non afferma:** di essere la fonte normativa. È un'emulazione dichiarata, mantenuta da
  terzi; qui vale come conferma di dettaglio su ciò che [S-053](#s-053) afferma in prosa, non come
  sostituto della documentazione di GitHub.
- **Usata da:** ADR-0038

<a id="s-055"></a>
### S-055 — MongoDB Manual v7.0: Localhost Exception (la variante della versione pinnata)

- **URL:** https://www.mongodb.com/docs/v7.0/core/localhost-exception/
- **Editore:** MongoDB, Inc. — MongoDB Docs / Database Manual
- **Versione documentata:** v7.0 — la stessa serie dell'immagine che il lab pinna (`mongo:7.0.40`)
- **Consultata:** 2026-08-31
- **Verdetto:** conferma parziale
- **Perché una voce separata da [S-006](#s-006):** S-006 è stata letta il 2026-08-25 sulla pagina
  `manual/`, che serve la versione **8.3 (Current)**. Gli stack del lab girano su 7.0.40
  ([ADR-0028](Decision.md#adr-0028)), e una regola di autenticazione è esattamente il genere di
  cosa che può cambiare fra due major. La pagina è stata quindi riletta sulla variante `v7.0/`
  prima di fondarci sopra la catena di inizializzazione del replica set.
- **Cosa afferma:** la definizione è identica a quella di 8.3 — «On a `mongod` instance, the
  localhost exception only applies when there are **no users or roles** created in the MongoDB
  instance» — e così l'elenco delle operazioni ammesse, che comprende `createUser` e `createRole`
  («This ends the localhost exception» per entrambi), `grantRole` verso sistemi esterni,
  **`replSetInitiate` «to initiate a new replica set»**, `replSetGetStatus`, `replSetReconfig` sul
  primario, e su `mongos` `addShard` «if the cluster is hosted on `localhost`». La frase di
  apertura dichiara i due usi insieme: «The localhost exception allows you to create the first user
  or role in the system after enabling access control. **You can also use it to initiate a replica
  set.**»
- **Cosa afferma in più rispetto a [S-006](#s-006), ed è operativamente decisivo:** «You can use
  the localhost exception to initiate a replica set, following the steps in Deploy a Self-Managed
  Replica Set. **You must wait until the replica set elects a primary before you can add the first
  user.**» È l'ordine dei passi, enunciato dalla fonte: prima `rs.initiate()`, poi l'attesa
  dell'elezione, poi `createUser` — e non un ordine qualsiasi. Il riquadro di avvertimento stringe
  ancora: «Connections using the localhost exception have access to create *only* the **first user
  OR role**. Only create a role first if you are authorizing users with LDAP.»
- **Come si spegne:** «Disable the localhost exception at startup. To disable the localhost
  exception, set the `enableLocalhostAuthBypass` parameter to `0`.» Il che dice, per complemento,
  che a `1` — cioè acceso — ci sta di suo.
- **Riserve:** la riserva che [S-006](#s-006) aveva dichiarato il 2026-08-25 **vale identica sulla
  v7.0**. Le stringhe `127.0.0.1`, `::1`, «loopback» e «same host» non compaiono da nessuna parte
  nella pagina; la formulazione più vicina al vincolo che tutti danno per ovvio è «connect to the
  localhost interface», che nomina un'interfaccia senza dire quale sia né da dove debba arrivare la
  connessione. La fonte, insomma, chiama l'eccezione «localhost» e non definisce «localhost». Non è
  una lacuna accademica: è la differenza fra un sidecar che riesce a inizializzare il replica set e
  uno che non ci riesce, e la misura sta in [V-023](#v-023).
- **Usata da:** ADR-0040

<a id="s-056"></a>
### S-056 — Docker Docs: Environment variables — Interpolation (`--env-file`)

- **URL:** https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/
- **Editore:** Docker Inc. — Docker Docs
- **Versione documentata:** riferimento Compose v2
- **Consultata:** 2026-08-31
- **Verdetto:** conferma
- **Cosa afferma:** che il `.env` accanto al progetto si legge da solo, ma solo finché non si
  passa la flag: «If the `--env-file` is not used in the command line, the `.env` file is loaded
  by default», e «Passing the `--env-file` argument **overrides** the default file path». La
  stessa cosa detta dal lato opposto: «Your `.env` file can be overridden by another `.env` if it
  is substituted with `--env-file`». Il rimedio è nella riga successiva: «You can use multiple
  `--env-file` options to specify multiple environment files, and Docker Compose reads them in
  order», con la regola di fusione esplicita — «Later files can override variables from earlier
  files». Un percorso sbagliato non viene ignorato: «When an invalid file path is being passed as
  an `--env-file` argument, Compose returns an error». I percorsi si risolvono «relative to the
  current working directory where the Docker Compose command is executed». Sulla directory di
  progetto — quella dove il `.env` implicito viene cercato — la pagina dà tre passi in ordine:
  «`--project-directory` if set», altrimenti la «directory of the first Compose file specified
  with `-f`/`--file`», altrimenti `PWD`. L'ordine di precedenza complessivo mette prima le
  variabili di shell, poi i file passati con `--env-file`, poi il `.env` della directory di
  progetto.
- **Riserve:** la frase che conta **non sta sulla pagina che si andrebbe a leggere**. La pagina
  intitolata «Environment variables precedence», che è quella dove uno cerca, non contiene mai
  l'affermazione che `--env-file` sostituisce il `.env`: dice solo «When `--env-file` is not set,
  Compose may load up to two `.env` files», e lascia dedurre il resto. L'affermazione esplicita è
  su questa pagina, sotto un titolo — «Interpolation» — che non lascia sospettare di contenerla.
  Seconda riserva: «overrides the default file path» va combinato con la regola dei tre passi per
  arrivare alla conseguenza che serve qui, cioè che passando `--env-file` sparisce anche il `.env`
  che sta **accanto al file indicato con `-f`**. Sono due frasi distanti sulla stessa pagina, e la
  conclusione è una deduzione: la misura diretta è in [V-025](#v-025).
- **Usata da:** ADR-0041, ADR-0042

<a id="s-057"></a>
### S-057 — `docker compose wait` e `docker compose up --wait`: che cosa dichiarano di attendere

- **URL:** https://docs.docker.com/reference/cli/docker/compose/wait/
- **Editore:** Docker Inc. — Docker Docs, e la guida del comando installato
- **Versione documentata:** Docker Compose v5.4.0
- **Consultata:** 2026-08-31
- **Verdetto:** conferma parziale
- **Cosa afferma:** `docker compose wait --help` dà la definizione in una riga — «Block until
  containers of all (or specified) services stop.» — con la forma d'uso `docker compose wait
  SERVICE [SERVICE...] [OPTIONS]` e una sola opzione propria, `--down-project` («Drops project
  when the first container stops»). Il riferimento in rete di `docker compose up` descrive
  l'opzione omonima ma diversa: `--wait` è «Wait services be running|healthy. Implies detached
  mode», e `--wait-timeout` è la «Maximum duration in seconds wait project to be running|healthy».
  Le due formulazioni non dicono la stessa cosa: `up --wait` attende che i servizi **siano** in
  esecuzione o sani, `compose wait` attende che i container **si fermino**.
- **Riserve:** la pagina in rete di `docker compose wait` non è stata leggibile in forma
  utilizzabile — la lettura ha restituito soltanto la tabella delle opzioni, senza il testo di
  descrizione. La definizione citata qui viene quindi dalla guida del comando installato sulla
  versione pinnata, che è una fonte primaria ma **locale**: su un'altra versione di Compose la
  formulazione può cambiare, e chi rilegge queste righe dovrebbe rieseguire `docker compose wait
  --help` prima di darle per attuali. La riserva che pesa davvero è però un'altra, ed è un
  silenzio: **nessuno dei due testi dice che cosa faccia `--wait` con un servizio che finisce il
  suo lavoro ed esce.** La distinzione fra un container che resta su e uno che muore per
  progetto non compare da nessuna parte sulla pagina di `up`. Non è un dettaglio di lettura: è
  esattamente il buco in cui cade lo stack di questo repository, misurato in [V-025](#v-025).
- **Usata da:** ADR-0041

---

<a id="s-058"></a>
### S-058 — MongoDB Manual 7.0: Read Preference

- **URL:** https://www.mongodb.com/docs/v7.0/core/read-preference/
- **Editore:** MongoDB, Inc. — MongoDB Manual, versione v7.0 (la stessa dell'immagine pinnata)
- **Consultata:** 2026-09-01
- **Verdetto:** conferma
- **Cosa afferma:** definisce il read preference come il modo in cui «MongoDB clients route read
  operations to the members of a replica set», ed elenca i cinque modi. Il predefinito è
  esplicito: «By default, an application directs its read operations to the primary member in a
  replica set (that is, read preference mode `primary`)», e per quel modo «All read operations use
  only the current replica set primary. This is the default read mode. **If the primary is
  unavailable, read operations produce an error or throw an exception.**» Gli altri quattro:
  `primaryPreferred` — «In most situations, operations read from the primary but if it is
  unavailable, operations read from secondary members»; `secondary` — «All operations read from the
  secondary members of the replica set»; `secondaryPreferred` — «Operations typically read data from
  secondary members of the replica set. If the replica set has only one single primary member and no
  other members, operations read data from the primary member»; `nearest` — «Operations read from a
  random eligible replica set member, irrespective of whether that member is a primary or secondary,
  based on a specified latency threshold».

  La frase che conta più di tutte sta nella sezione *Behavior*: «**All read preference modes except
  `primary` may return stale data** because secondaries replicate operations from the primary in an
  asynchronous process. Ensure that your application can tolerate stale data if you choose to use a
  non-`primary` mode.» E subito dopo, un avvertimento che si legge di rado: «Read preference does
  not affect the visibility of data. Clients can see the results of writes before they are
  acknowledged or have propagated to a majority of replica set members.» Il rimedio nominato dalla
  pagina, per ciascuno dei modi non predefiniti, è sempre lo stesso: «Use the `maxStalenessSeconds`
  option to avoid reading from secondaries that the client estimates are overly stale.»
- **Riserve:** la pagina descrive il **contratto**, non il costo: non dà nessun numero sul ritardo
  di replica, che dipende dalla distribuzione e va misurato dove gira ([V-027](#v-027)). Le
  descrizioni dei modi nominano più volte gli *hedged read*, che valgono sugli sharded cluster e
  non su un replica set: non riguardano lo stack 02 e non sono stati provati. `maxStalenessSeconds`
  è citato dalla pagina come rimedio ma **non è stato usato né misurato** in questo repository.
- **Usata da:** ADR-0046

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
- **Usata da:** ADR-0025, ADR-0026, ADR-0027, ADR-0033, ADR-0039

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
- **Usata da:** ADR-0027, ADR-0028, ADR-0033

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
- **Usata da:** ADR-0030, ADR-0035

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
- **Usata da:** ADR-0031, ADR-0043

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
- **Usata da:** ADR-0031, ADR-0033, ADR-0043

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
- **Usata da:** ADR-0032, ADR-0046

---

<a id="v-017"></a>
### V-017 — Tre modi di far morire `mongod`, e solo uno fa ripartire il container

- **Comandi:** `docker inspect` (politica e `RestartCount`) · `docker kill -s KILL
  mongo-standalone` · `docker exec mongo-standalone kill -9 1` · `docker exec … mongosh --eval
  "db.adminCommand({shutdown: 1, force: true})"`
- **Ambiente:** stack `docker/01-standalone` con `restart: unless-stopped`, Docker Engine 29.7.2
  su Docker Desktop (macOS), `mongo` 7.0.40 pinnata per digest, 2026-08-28

La politica dichiarata è la stessa in tutte e tre le prove:
`{"Name": "unless-stopped", "MaximumRetryCount": 0}`. Cambia solo **chi manda il segnale**, e
l'esito cambia con lui.

| Come muore | Chi manda il segnale | Esito osservato | `RestartCount` |
|---|---|---|---:|
| `docker kill -s KILL` | il demone, dal namespace **antenato** | container `exited`, `ExitCode=137`, `OOMKilled=false`; ancora `exited` dopo 12 s | **0** |
| `kill -9 1` **dentro** il container | un processo dello **stesso** namespace | **niente**: il comando esce con `rc=0`, il container resta `running` e `healthy` | 0 |
| `shutdown` chiesto a `mongod` | il processo a se stesso | il container **riparte da solo**, `healthy` di nuovo in pochi secondi | **1** |

**1. `docker kill` non fa ripartire niente, ed è il contrario di quello che quasi tutti si
aspettano.** Il container resta `exited` a tempo indeterminato: dodici secondi dopo il segnale
`RestartCount` è ancora `0`, cioè il demone non ha nemmeno *provato*. Ci vuole un `docker start`
a mano, dopo il quale il nodo torna `healthy` in **6 secondi** e `RestartCount` resta `0`.

La spiegazione sta in [S-039](#s-039): la politica «is ignored until the Docker daemon restarts
or the container is manually restarted» dopo che il container «is stopped (manually or
otherwise)». Un `docker kill` è, per il demone, una fermata chiesta da un umano — non un guasto.
Nessuna delle due pagine ([S-039](#s-039), [S-040](#s-040)) lo scrive in modo che un lettore
possa prevederlo: la prima dice «manually or otherwise», la seconda non nomina mai la parola
«restart».

**Conseguenza pratica, ed è quella che conta:** `docker kill` **non simula un guasto**. Simula
uno spegnimento. Chi dimostra la resilienza di un cluster uccidendo un container sta mostrando
uno scenario in cui l'infrastruttura ha deliberatamente scelto di non intervenire.

**2. Dall'interno del container, `kill -9 1` non fa assolutamente niente — e non lo dice.** Il
PID 1 visto da dentro è `mongod` (letto in `/proc/1/comm`). Il comando ritorna `rc=0`, senza
stdout e senza stderr: sembra riuscito. Cinque secondi dopo il container è `running` e
`healthy`, `RestartCount=0`.

Non è una stranezza di Docker, è il kernel: [S-041](#s-041) dice che solo i segnali per cui il
processo «init» ha installato un gestore possono essergli inviati dagli altri membri del suo
namespace, «even to privileged processes». `SIGKILL` non è gestibile per definizione, quindi
viene semplicemente scartato. Il successo apparente di `kill` è il fatto più insidioso della
prova: nessun errore, nessun effetto.

**3. Se `mongod` termina da sé, la politica funziona come ci si aspetta.** Chiesto lo `shutdown`
al server, il container riparte **da solo**: entro tre secondi è già `running` con
`RestartCount=1` e stato di salute `starting`; entro cinque è `healthy`. Nessun intervento
manuale.

Dettaglio da conoscere se si ripete la prova: il `mongosh` che manda lo `shutdown` esce con
`rc=137`, perché il server chiude la connessione del client che gli ha appena chiesto di
spegnersi. Non è un fallimento del comando.

**4. Il dataset attraversa tutte e tre le prove.** `make smoke-01` dopo la sequenza completa:
dodici controlli verdi, impronta invariata.

- **Riserve:** una esecuzione per ciascuna delle tre prove, su una sola macchina, con Docker
  Desktop su macOS — quindi il kernel in gioco è quello della VM. Non è stata isolata la regola
  dei «at least 10 seconds» di [S-039](#s-039): il container era in piedi da molto più tempo in
  tutte e tre le prove, quindi la politica era certamente attiva. Non è stato provato `docker
  stop`, che [S-039](#s-039) copre esplicitamente ed è il caso non interessante. Il numero
  `RestartCount` è cumulativo sulla vita del container: azzerarlo richiede ricrearlo.
- **Data:** 2026-08-28
- **Usata da:** ADR-0034, ADR-0044

---

<a id="v-018"></a>
### V-018 — `localhost` non è un posto: è un punto di vista, e sbagliarlo dà due errori diversi

- **Comandi:** `mongosh --host <nome> --eval "db.adminCommand('ping').ok"` da quattro posizioni
  diverse · `nc -z <nome> 27017` dall'host
- **Ambiente:** stack `docker/01-standalone` avviato e `healthy`, rete
  `sqlstart-01-standalone_default` creata da Compose, `mongo` 7.0.40, macOS, 2026-08-28

| Da dove | Nome chiesto | Esito |
|---|---|---|
| dentro `mongo-standalone` | `localhost` | `1` |
| dentro `mongo-standalone` | `127.0.0.1` | `1` |
| dentro `mongo-standalone` | `mongo-standalone` | `1` |
| da un **altro** container sulla stessa rete | `localhost` | `MongoNetworkError: connect ECONNREFUSED 127.0.0.1:27017` |
| da un **altro** container sulla stessa rete | `mongo-standalone` | `1` |
| da un container **fuori** da quella rete | `mongo-standalone` | `MongoNetworkError: getaddrinfo ENOTFOUND mongo-standalone` |
| dall'host | `localhost:27017` | connessione TCP riuscita |
| dall'host | `mongo-standalone:27017` | `nc: getaddrinfo: nodename nor servname provided, or not known` |

**I due errori non sono lo stesso errore, ed è tutta la lezione.**

- `ECONNREFUSED` significa che il nome **ha risolto** — verso 127.0.0.1, che dal punto di vista
  di quel container è quel container. Il client ha bussato alla porta giusta della macchina
  sbagliata: se stesso. È l'errore di chi ha copiato una stringa di connessione da un contesto
  all'altro.
- `ENOTFOUND` significa che il nome **non ha risolto affatto**. Il DNS interno di Docker
  risponde solo ai container attaccati a quella rete; da fuori, `mongo-standalone` non esiste.

L'unico nome che funziona da tutte le posizioni interne alla rete è quello del servizio, ed è la
ragione della regola di [ADR-0021](Decision.md#adr-0021). Su un'istanza singola la differenza è
un fastidio di dieci secondi; su un replica set diventa un guasto vero, perché i membri si
scambiano gli indirizzi con cui sono stati configurati e un client che riceve `localhost` dal
`hello` prova a connettersi a se stesso ([S-020](#s-020)).

- **Riserve:** dall'host la prova è a livello TCP (`nc`), non MongoDB, perché su questa macchina
  `mongosh` non è installato fuori dai container: dimostra che la porta pubblicata è
  raggiungibile, non che il server risponda — per quello valgono l'healthcheck e `make smoke-01`.
  La risoluzione dei nomi **sull'host** non dipende da Docker ma dal sistema operativo: su una
  macchina con una voce in `/etc/hosts`, o con un resolver aziendale che rispondesse a quel nome,
  l'ultima riga della tabella cambierebbe. Rete singola creata da Compose; con reti multiple o
  alias di rete il quadro si arricchisce e non è stato esplorato.
- **Data:** 2026-08-28
- **Usata da:** ADR-0033, ADR-0036

---

<a id="v-019"></a>
### V-019 — Novemilanovecentotrentuno righe, e il 92 % dice «sto bene»

- **Domanda:** che cosa c'è davvero nel log di un'istanza singola che non sta facendo niente, e
  quanto ne cresce al minuto?
- **Ambiente:** stack `01-standalone` di questo repository, immagine `mongo:7.0.40`, container
  `mongo-standalone` avviato il 2026-08-28 alle 11:53:25 UTC con `RestartCount=1`. Scatto preso
  alle **12:19:02 UTC**, dopo gli esperimenti di [V-017](#v-017) e [V-018](#v-018). Analisi con
  uno script Python che legge `docker logs mongo-standalone` e conta.
- **Comandi:** `docker logs mongo-standalone`, più `db.adminCommand({getLog: "startupWarnings"})`
  attraverso `docker compose exec -T mongo-standalone mongosh --quiet --eval`.

**Primo risultato — la composizione.** Nove­mila­nove­cento­trentuno righe: **9922 JSON e 9 non-JSON**.
Centotredici `id` distinti. Nessuna severità oltre `I` e `W`:

| severità | righe | quota |
| --- | ---: | ---: |
| `I` (informativa) | 9892 | 99,70 % |
| `W` (avviso) | 30 | 0,30 % |
| `E` (errore) | 0 | — |
| `F` (fatale) | 0 | — |

**Secondo risultato — i componenti, e chi domina.** `NETWORK` e `ACCESS` insieme fanno **9117
righe, il 91,9 %** del log:

| componente | righe | quota |
| --- | ---: | ---: |
| `NETWORK` | 7146 | 72,0 % |
| `ACCESS` | 1971 | 19,9 % |
| `STORAGE` | 388 | 3,9 % |
| `CONTROL` | 89 | 0,9 % |
| `EXECUTOR` | 88 | 0,9 % |
| `WTCHKPT` | 61 | 0,6 % |

**Terzo risultato — una connessione costa quattro righe, e `mongosh` ne apre cinque.** Gli `id`
più frequenti sono sempre gli stessi quattro, nello stesso ordine, per ogni connessione:

| `id` | componente | `msg` | occorrenze |
| --- | --- | --- | ---: |
| `22943` | `NETWORK` | `Connection accepted` | 1982 |
| `51800` | `NETWORK` | `client metadata` | 1971 |
| `10483900` | `ACCESS` | `Connection not authenticating` | 1971 |
| `22944` | `NETWORK` | `Connection ended` | 1971 |
| `6788700` | `NETWORK` | `Received first command on ingress connection since session start or auth handshake` | 1170 |

Una singola invocazione di `mongosh --quiet --eval "db.adminCommand('ping').ok"` apre **cinque**
connessioni, non una: `connectionId` da 804 a 808 in 99 millisecondi
(`12:18:17.803` → `12:18:17.902`), tutte chiuse insieme all'uscita, `12:18:17.909`. Sono venti
righe di connessione più tre `6788700`, ventitré righe per un `ping`.

**Quarto risultato — la crescita a riposo.** Fra due letture distanti **60,1 secondi**, senza
alcun carico applicativo, sono comparse **139 righe**. Scomposte per `id`:

| `id` | righe nell'intervallo | origine |
| --- | ---: | --- |
| `22943`, `51800`, `10483900`, `22944` | 30 ciascuno = **120** | 6 healthcheck × 5 connessioni × 4 righe |
| `6788700` | 18 | 3 per healthcheck |
| `22430` (`WTCHKPT`) | 1 | checkpoint periodico di WiredTiger |

L'aritmetica chiude: l'healthcheck del file Compose gira ogni dieci secondi
([V-012](#v-012)), sei volte al minuto, e produce **138 delle 139 righe**. Il **99,3 %** di ciò
che un'istanza a riposo scrive nel log è la risposta alla domanda «stai bene?».

**Quinto risultato — le nove righe non-JSON sono tutte e sole quelle che non scrive `mongod`.**
In un log che [S-042](#s-042) dichiara interamente JSON, le nove eccezioni sono l'entrypoint
dell'immagine e lo script di inizializzazione di questo repository:

```text
about to fork child process, waiting until server is ready for connections.
forked process: 28
child process started successfully, parent exiting
/usr/local/bin/docker-entrypoint.sh: running /docker-entrypoint-initdb.d/10-dati-demo.js
Carico 50000 ordini in lab.ordini...
Caricati 50000 ordini in 1711 ms.
Nessun indice creato: il confronto con e senza indice è parte della demo.
Killing process with pid: 28
MongoDB init process complete; ready for start up.
```

Sono la ricevuta dell'inizializzazione: la loro assenza è il sintomo della
[trappola 1](02-architetture/trappole-mongodb-in-docker.md#t-01).

**Sesto risultato — cinque avvii nello stesso log, e quindici avvisi d'avvio.** L'`id` `4615611`
(`MongoDB starting`) compare **cinque** volte: `docker logs` conserva l'intera vita del
container, riavvii compresi, e il `mongod` temporaneo dell'entrypoint conta come uno. Le righe
con `tags: ["startupWarnings"]` sono **quindici**: tre per avvio, sempre le stesse.
`db.adminCommand({getLog: "startupWarnings"})` risponde `totalLinesWritten: 3` e restituisce
solo quelle dell'avvio corrente:

| severità | `id` | messaggio |
| --- | --- | --- |
| `I` | `22297` | `Using the XFS filesystem is strongly recommended with the WiredTiger storage engine.` |
| `W` | `22120` | `Access control is not enabled for the database. Read and write access to data and configuration is unrestricted` |
| `W` | `9068900` | `For customers running MongoDB 7.0, we suggest changing the contents of the following sysfsFile` |

L'ultima porta in `attr` il dettaglio: `{"sysfsFile": "/sys/kernel/mm/transparent_hugepage",
"currentValue": "always", "desiredValue": "never"}` — è la VM Linux di Docker Desktop, non il
Mac. La seconda è la prova che il server **avvisa** di essere senza autenticazione
([ADR-0005](Decision.md#adr-0005)): l'avviso c'è, in trentamila righe non lo legge nessuno.

**Settimo risultato — `REPL` esiste anche su un'istanza singola.** Il componente compare 42
volte pur non essendoci alcun replica set: sono le inizializzazioni dei sottosistemi di
replicazione, che `mongod` costruisce comunque. La presenza di righe `REPL` non prova che il
nodo replichi qualcosa.

- **Interpretazione:** il log di MongoDB non è un diario degli eventi interessanti, è un
  tracciato del traffico. Chi lo legge scorrendo dall'alto legge per il 92 % le connessioni di un
  controllo di salute. Le trenta righe che contano — le `W` — sono lo 0,3 %, e nove volte su dieci
  sono le stesse tre ripetute a ogni avvio. Le due domande che rendono il log leggibile sono
  quindi: *quale componente* e *quale `id`*.
- **Riserve:** i numeri assoluti dipendono da quanto è vissuto il container e da quanti
  esperimenti ha subito; sono validi come proporzioni, non come costanti. La quota del 91,9 % è
  quella di un'istanza **senza carico applicativo**: sotto carico `COMMAND` e `WRITE` crescono e
  la proporzione cambia. Le 139 righe al minuto valgono per l'healthcheck di questo repository —
  chi lo togliesse, o lo portasse a `interval: 60s`, otterrebbe un log molto più magro e una
  diagnosi di guasto molto più lenta. L'assenza di `E` e `F` non è una proprietà di MongoDB: è il
  resoconto di un'istanza che, in questa finestra, non ha mai sbagliato niente.
- **Data:** 2026-08-28
- **Usata da:** ADR-0035

---

<a id="v-020"></a>
### V-020 — `mongosh` in automazione: ogni errore vale 1, e il silenzio vale 0

- **Domanda:** che cosa può promettere uno script che chiama `mongosh`? Il codice di uscita
  distingue un errore del server da un server irraggiungibile? E una ricerca che non trova
  niente è un errore?
- **Ambiente:** stack `01-standalone`, immagine `mongo:7.0.40`, `mongosh` **2.10.0** eseguito
  dentro il container `mongo-standalone`. Macchina di sviluppo: macOS 26.6.2 (Darwin 25.6.0),
  Docker Desktop. Data: 2026-08-28.
- **Comandi:** una quarantina di invocazioni non interattive, ciascuna con il proprio codice
  di uscita raccolto dal processo chiamante.

**Primo risultato — sull'host `mongosh` non c'è, e non serve.**

```console
$ which mongosh
mongosh not found
$ which mongo
mongo not found
$ docker exec mongo-standalone sh -c 'command -v mongosh; command -v mongod; command -v mongodump'
/usr/bin/mongosh
/usr/bin/mongod
/usr/bin/mongodump
$ docker exec mongo-standalone mongosh --version
2.10.0
```

L'immagine porta con sé la shell, il server e gli strumenti di backup. Nessuna installazione sul
portatile, e una versione sola: quella misurata qui.

**Secondo risultato — la stringa che `mongosh` costruisce da sé.** Invocato senza argomenti si
collega a `localhost:27017` ([S-045](#s-045)); interrogato su dove sia andato, risponde:

```text
mongodb://127.0.0.1:27017/?directConnection=true&serverSelectionTimeoutMS=2000&appName=mongosh+2.10.0
```

Tre valori impliciti che nessuno ha scritto: `directConnection=true`, `appName`, e soprattutto
**`serverSelectionTimeoutMS=2000`**. Due secondi. [S-044](#s-044) dà un'elezione per lunga fino a
dodici. Un `mongosh` invocato senza pensarci, contro un replica set che sta rieleggendo, si
arrende **dieci secondi prima** che il cluster abbia finito — e l'errore che stampa somiglia a
quello di un cluster morto. Nessuna delle pagine consultate nomina questo valore predefinito.

Il database predefinito è `test`, come dichiarato:

```console
$ mongosh --quiet --eval "db.getName()"
test
$ mongosh --quiet "mongodb://localhost:27017/lab" --eval "db.getName()"
lab
```

**Terzo risultato — `--quiet` è già acceso, quando non c'è un umano.**

| invocazione | prima riga stampata |
| --- | --- |
| `mongosh --eval "1 + 1"` | `2` |
| `mongosh --quiet --eval "1 + 1"` | `2` |
| `mongosh --no-quiet --eval "1 + 1"` | `Current Mongosh Log ID:	6a91801e…` |

Conferma di [S-046](#s-046): in sessione non interattiva il silenzio è il valore predefinito, e
`--no-quiet` serve a **ri**accendere il preambolo. Con `--no-quiet` compaiono sei righe di
intestazione — identificativo di sessione, stringa di connessione, versione del server, versione
della shell — prima del risultato.

**Quarto risultato — con più `--eval`, si stampa solo l'ultimo valore.**

| comando | stampa |
| --- | --- |
| `--eval "1 + 1" --eval "2 + 2"` | `4` |
| `--eval "print('uno')" --eval "print('due')" --eval "3 + 3"` | `uno`, `due`, `6` |
| `--eval "use lab" --eval "db.getName()"` | `lab` |

Il **valore** dell'espressione viene stampato solo per l'ultimo `--eval` ([S-046](#s-046)),
mentre `print()` scrive sempre. E lo stato attraversa i frammenti: un `use lab` nel primo
`--eval` vale ancora nel secondo. Chi vuole vedere i risultati intermedi deve chiedere `print()`;
chi si limita a scrivere l'espressione ottiene silenzio, non un errore.

**Quinto risultato — la tabella dei codici di uscita.** Nessuna delle pagine consultate la
contiene. Misurata:

| situazione | codice |
| --- | ---: |
| espressione valutata senza errori | **0** |
| `countDocuments` che non trova nulla (restituisce `0`) | **0** |
| `throw new Error("rotto")` non catturato | **1** |
| `TypeError` — metodo che non esiste | **1** |
| `ReferenceError` — identificatore non definito | **1** |
| `MongoServerError` — `no such command` | **1** |
| `MongoServerError` — `E11000 duplicate key error` | **1** |
| `MongoServerError` — `cannot use 'w' > 1 when a host is not replicated` | **1** |
| `MongoNetworkError` — `getaddrinfo ENOTFOUND` | **1** |
| `MongoNetworkError` — `connect ECONNREFUSED` | **1** |
| `--file` su un percorso che non esiste (`ENOENT`) | **1** |
| `exit(3)` | **3** |
| `quit(7)` | **7** |
| `exit(300)` | **44** |
| `exit(-1)` | **255** |

Tre conclusioni, e sono tutte scomode.

1. **Ogni errore vale `1`.** Dal codice di uscita non si distingue «il server ha risposto di no»
   da «il server non l'ho trovato». Chi deve distinguere deve leggere `stderr`, oppure catturare
   l'eccezione e uscire con un codice proprio, come raccomanda [S-047](#s-047).
2. **Il silenzio vale `0`.** Una ricerca che non trova niente termina con successo. Uno script di
   verifica che si limiti a interrogare, e che giudichi dal codice di uscita, **dichiara sano un
   database vuoto**. È lo stesso genere di trappola di `logRotate` che risponde `ok: 1`
   ([V-010](#v-010)): l'operazione riesce, il fatto non è avvenuto.
3. **Il codice scelto non è sempre il codice consegnato.** `exit(300)` diventa 44 (300 modulo
   256) ed `exit(-1)` diventa 255. Restare fra 1 e 125 evita anche la sovrapposizione con i
   codici che le shell si riservano.

**Sesto risultato — `load()` non cerca da nessuna parte, e `--file` neanche.** Con lo script in
`/tmp/controllo.js` e la directory di lavoro in `/etc`:

```console
$ mongosh --quiet --eval 'load("controllo.js")'
Error: ENOENT: no such file or directory, open '/etc/controllo.js'
    rc = 1
$ mongosh --quiet --eval 'load("/tmp/controllo.js")'
ordini: 50000
true
    rc = 0
```

Conferma letterale di [S-047](#s-047). Dentro un container la directory di lavoro non è quella da
cui si è digitato il comando: i percorsi vanno assoluti, sempre.

**Settimo risultato — non si passa uno script per pipe.** `mongosh` legge lo standard input come
una sessione interattiva e ci stampa sopra i suoi prompt:

```console
$ echo 'print("dallo standard input: " + …)' | docker compose exec -T mongo-standalone mongosh --quiet
test> dallo standard input: 50000

test>     rc = 0
```

Il risultato c'è, ma è annegato fra due `test>`. E `--file -` non è una scorciatoia: `mongosh`
cerca un file che si chiama `-` (`ENOENT: … open '/-'`, codice 1). Gli unici due modi puliti
restano `--eval` e `--file <percorso assoluto>`.

**Ottavo risultato — `-T` non è il colpevole che si crede.** Le prove:

| comando | stdin | esito |
| --- | --- | --- |
| `docker compose exec mongo-standalone mongosh …` | `/dev/null` | `2`, codice 0 |
| `docker compose exec mongo-standalone mongosh …` | **chiuso** | `2`, codice 0 |
| `docker compose exec -T mongo-standalone mongosh …` | chiuso | `2`, codice 0 |
| `docker exec -it mongo-standalone mongosh …` | `/dev/null` | **fallisce**, codice 1 |

L'ultima riga stampa `cannot attach stdin to a TTY-enabled container because stdin is not a
terminal`. Non è l'assenza di `-T` a rompere gli script: è la **presenza di `-it`**, l'abitudine
copiata da mille esempi interattivi. `docker compose exec` da solo si arrangia; `-T` è esplicito
e non costa niente.

- **Interpretazione:** `mongosh` è un ottimo strumento interattivo e un pessimo oracolo
  automatico, se lo si interroga solo con il codice di uscita. Uno script che deve **verificare**
  qualcosa deve dirlo: controllare il risultato e chiamare `exit()` con un codice scelto da chi
  scrive. Questa è la ragione per cui gli strumenti di verifica di questo repository non si
  limitano a lanciare comandi e guardare se tornano zero.
- **Riserve:** tutti i codici valgono per `mongosh` 2.10.0; la documentazione non li dichiara, il
  che significa che non sono un contratto e possono cambiare senza preavviso — motivo in più per
  uscire esplicitamente. I codici `3`, `7`, `44` e `255` sono stati scelti per la prova e non
  hanno alcun significato convenzionale. Il comportamento di `-T` è stato misurato su Docker
  Desktop per macOS e su `docker compose` v2: su altre versioni del client, e nelle CI dove lo
  standard input è chiuso in modi diversi, l'esito potrebbe non essere lo stesso.
- **Nota di percorso.** Durante queste prove un `insertOne({_id: 1})` ha incontrato un `_id`
  che nel dataset di demo esisteva già, e la pulizia successiva ha cancellato il documento
  originale: l'impronta di `lab.ordini` è scesa a 49999. `make seed-01` ha ricaricato il dataset e
  l'impronta è tornata **`50000 124861860.70 150281`**, identica. È la prima volta che il dataset
  deterministico di [ADR-0031](Decision.md#adr-0031) ha ripagato il proprio costo.
- **Data:** 2026-08-28
- **Usata da:** ADR-0036

---

<a id="v-021"></a>
### V-021 — Il container del lab è un'installazione Ubuntu con tre note di produzione disattese, e il server lo dice all'avvio

- **Domanda:** le pagine di installazione e le note di produzione descrivono un `mongod` installato
  su un sistema operativo. Quanto di quel mondo sopravvive dentro un container, e dove il lab si
  discosta da quello che il manuale raccomanda?
- **Ambiente:** stack `01-standalone`, immagine `mongo:7.0.40`, macchina di sviluppo macOS 26.6.2
  (Darwin 25.6.0) con Docker Desktop. Data: 2026-08-28.
- **Comandi:** ispezione del container con `sh -c`, più
  `db.adminCommand({getLog: "startupWarnings"})`.

**Primo risultato — l'immagine *è* l'installazione descritta da [S-048](#s-048).**

```console
$ cat /etc/os-release | head -2
PRETTY_NAME="Ubuntu 22.04.5 LTS"
NAME="Ubuntu"
$ cat /etc/apt/sources.list.d/mongodb-org.list
deb [ signed-by=/etc/apt/keyrings/mongodb.asc ] http://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse
```

Ubuntu 22.04 «Jammy», e il file di elenco `apt` che punta allo stesso repository ufficiale del
tutorial — solo con il portachiavi in `/etc/apt/keyrings/mongodb.asc` invece che in
`/usr/share/keyrings/`. Chi impara la procedura di [S-048](#s-048) sta imparando come è stata
costruita l'immagine che usa.

**Secondo risultato — quello che l'immagine ha buttato via.**

| elemento di [S-048](#s-048) | nel container |
| --- | --- |
| `/etc/mongod.conf` | **assente**: `ls: cannot access '/etc/mongod.conf': No such file or directory` |
| `systemd` e `systemctl` | assenti: il processo 1 **è** `mongod` |
| `/var/lib/mongodb`, `/var/log/mongodb` | sostituiti da `/data/db` e da `stdout` ([ADR-0030](Decision.md#adr-0030)) |
| utente `mongodb` | **conservato**: `ps -o user,pid,comm -p 1` risponde `mongodb 1 mongod` |

L'ultima riga merita attenzione perché è controintuitiva: `docker compose exec` entra come `root`
(`uid=0(root)`), ma il **server** gira come `mongodb`, esattamente come dopo un
`apt-get install mongodb-org`. La shell che si apre non ha i privilegi del processo che osserva, e
viceversa.

**Terzo risultato — tre note di produzione disattese, tutte dichiarate dal server.**

```console
$ mongosh --quiet --eval 'db.adminCommand({getLog: "startupWarnings"}).log
    .forEach(r => { const o = JSON.parse(r); print(o.id + "  " + o.msg.substring(0, 78)) })'
22297   Using the XFS filesystem is strongly recommended with the WiredTiger storage
22120   Access control is not enabled for the database. Read and write access to dat
9068900 For customers running MongoDB 7.0, we suggest changing the contents of the f
```

Tre avvisi, tre raccomandazioni, e per ognuna la misura che la conferma:

| avviso | raccomandazione | misurato qui |
| --- | --- | --- |
| `22297` | XFS «strongly recommended» ([S-050](#s-050)) | `/data/db` sta su **ext4**: `/dev/vda1 /data/db ext4` |
| `9068900` | THP disabilitato ([S-051](#s-051)) | `/sys/kernel/mm/transparent_hugepage/enabled` → `[always] madvise never` |
| `22120` | autorizzazione abilitata ([S-050](#s-050)) | scelta deliberata del lab ([ADR-0005](Decision.md#adr-0005)) |

Le prime due **non si possono correggere da dentro il container**. Il filesystem è quello del
volume creato da Docker Desktop; THP appartiene al kernel della macchina virtuale Linux, non al
container e tantomeno al Mac. È la differenza fra un avviso da risolvere e un avviso da
riconoscere, e sapere in quale dei due casi ci si trova vale più che saperlo far sparire.

**Quarto risultato — i `ulimit` sono già oltre il raccomandato, senza che nessuno li abbia
scritti.**

```console
$ grep -E 'Max open files|Max processes' /proc/1/limits
Max processes             unlimited            unlimited            processes
Max open files            1048576              1048576              files
```

[S-052](#s-052) raccomanda `-n 64000` e `-u 64000`; qui i descrittori aperti sono **1 048 576**,
sedici volte tanto, e i processi sono illimitati. È il runtime dei container a fissarli, e per
questo il `mongod` del lab non emette l'avviso d'avvio sui file aperti che [S-048](#s-048)
promette sotto i 64000. Una prova che avesse voluto mostrare quell'avviso avrebbe dovuto
abbassarli apposta.

**Quinto risultato — lo swap c'è, e non è quello del Mac.**

```console
$ free -m | tail -2
Mem:           11946        1001       10126           0         818       10775
Swap:           2047           0        2047
```

Due gigabyte di swap, zero usati: sono della macchina virtuale Linux, come gli 11 946 MiB di
memoria che `hostInfo` riporta ([V-020](#v-020)). Delle due strategie di [S-050](#s-050) — swap
assegnato e usato solo sotto pressione, oppure nessuno swap — Docker Desktop ha scelto la prima
per conto nostro.

- **Interpretazione:** un container non è una scorciatoia per saltare le note di produzione: è un
  posto dove **metà** di quelle note non si applicano e l'altra metà si applica a un livello
  diverso — l'host, o la macchina virtuale, o il runtime. La conseguenza pratica per il talk è che
  gli avvisi d'avvio non vanno nascosti né «risolti»: vanno letti, e per ciascuno si deve saper
  dire se è un difetto del lab o una proprietà del posto in cui il lab gira. Delle tre righe qui
  sopra, due sono proprietà del posto e una sola è una scelta nostra.
- **Riserve:** i valori dei `ulimit`, la dimensione dello swap e il tipo di filesystem dipendono da
  Docker Desktop per macOS e dalla sua macchina virtuale; su Docker Engine nativo su Linux
  cambiano, e su un `mongod` installato con `apt` cambiano ancora. Nessuna delle procedure di
  [S-048](#s-048), [S-049](#s-049), [S-051](#s-051) e [S-052](#s-052) è stata eseguita: questa
  verifica misura il **contrasto** con quelle pagine, non le pagine stesse.
- **Data:** 2026-08-28
- **Usata da:** ADR-0037

---

<a id="v-022"></a>
### V-022 — La politica di pull scritta nel file: lo stack parte, e senza cache fallisce in un decimo di secondo

- **Domanda:** tre domande, nate da una review esterna della PR #2. Che cosa fa Compose quando una
  variabile è dichiarata ma **vuota**? Con `pull_policy: never` scritto fisso, lo stack del lab si
  avvia ancora? E quando l'immagine non è in cache, il fallimento è immediato o passa dalla rete?
- **Ambiente:** macchina di sviluppo macOS 26.6.2 (Darwin 25.6.0), Docker Desktop, server Docker
  29.7.2, `docker compose version` **v5.4.0**. Stack `01-standalone`, immagine `mongo:7.0.40`
  pinnata per digest. Data: 2026-08-31.

**Primo risultato — nelle forme con i due punti, una variabile vuota vale quanto una assente.**

```console
$ cat vuota.env
PULL_POLICY=
$ docker compose -f prova.yaml --env-file vuota.env config
services:
  prova:
    image: busybox
    pull_policy: missing

$ MONGO_IMAGE= docker compose -f obbligatoria.yaml config
error while interpolating services.prova.image: required variable MONGO_IMAGE is missing a value:
assente — eseguire «make images-pull»
```

`${PULL_POLICY:-missing}` con `PULL_POLICY=` non dà la stringa vuota: dà `missing`. E
`${MONGO_IMAGE:?…}` con `MONGO_IMAGE=` non passa: fallisce come se la variabile non ci fosse. Sono
le due forme che i file Compose del lab usano, ed è la ragione per cui `tools/check_stack.py` le
modella così e non altrimenti.

**Secondo risultato — con `never` fisso lo stack si avvia e la prova di fumo passa intera.**

```console
$ make up-01
 Container mongo-standalone  Healthy
$ make smoke-01
Superati: 12 · Errori: 0
Lo stack 01 fa quello che il file Compose promette.
```

**Terzo risultato — senza l'immagine in cache il fallimento è immediato.**

```console
$ time docker compose --env-file finta.env -f docker/01-standalone/compose.yaml up -d
 Container mongo-standalone  Creating
Error response from daemon: No such image:
mongo@sha256:0000000000000000000000000000000000000000000000000000000000000000
docker compose ... up -d  0,06s user  0,03s system  82% cpu  0,113 total
```

Centotredici millesimi di secondo. Non è un tentativo di rete andato male: è un tentativo mai
iniziato, e conferma su questo file quello che [V-006](#v-006) aveva misurato sullo spike.

- **Conseguenza:** la politica di pull smette di dipendere da una variabile d'ambiente che si può
  dimenticare di passare e diventa una proprietà del file Compose, leggibile da chi lo apre. Il
  costo — `make images-pull` obbligatorio prima del primo avvio — è pagato a casa, con la rete, non
  in sala.
- **Riserve:** le misure di tempo vengono da una macchina sola e da una sola esecuzione; servono a
  distinguere un ordine di grandezza (decimi di secondo) da un altro (secondi di attesa di rete),
  non a essere confrontate fra loro. La prova con la rete fisicamente staccata resta da fare.
- **Data:** 2026-08-31
- **Usata da:** ADR-0039

---

<a id="v-023"></a>
### V-023 — Chi inizializza il replica set: tre strade provate, e una terza che non era scritta da nessuna parte

> **Nota di precisione, 2026-08-31 (Task 3).** Nella «misura di contorno» qui sotto il blocco di
> console riporta `isWritablePrimary=false secondary=true` attribuendolo a un membro «non ancora
> inizializzato». La *conclusione* tratta lì è giusta e oggi è confermata sullo stack vero — un
> controllo «sei primario o secondario?» resterebbe rosso fino a `rs.initiate()` — ma quei due
> valori vengono da un membro che l'inizializzazione l'aveva già ricevuta. Su un membro davvero
> vergine i tre `mongod` dello stack rispondono `isWritablePrimary=false secondary=false
> **isreplicaset=true**`, e `isreplicaset` è il marcatore che il Task 5 può usare. Il corpo non
> viene toccato: si legge com'era, con questa nota davanti.

- **Domanda:** il design (§5.4) e [ADR-0026](Decision.md#adr-0026) dicono due cose diverse su chi
  crea l'utente amministratore di uno stack a replica set sotto keyfile. Il design mette
  `MONGO_INITDB_ROOT_USERNAME`/`_PASSWORD` sul primo membro e fa inizializzare il set a un sidecar
  già autenticato; ADR-0026 vuole i `mongod` **senza** variabili di root e l'utente creato sotto
  eccezione localhost. Non è una sfumatura: cambia se nel repository finisce una password. Il
  Task 1 del piano di `feature/02` ha rifiutato di scegliere a tavolino e ha montato entrambe le
  strade. Tre domande: la strada di ADR-0026 funziona su un replica set (e non solo su uno sharded
  cluster)? La strada del design funziona, cioè l'entrypoint crea davvero l'utente anche con
  `--replSet` e `--keyFile` addosso? E l'affermazione del design secondo cui «l'eccezione localhost
  non copre un container sidecar» è vera?
- **Ambiente:** macchina di sviluppo macOS 26.6.2 (Darwin 25.6.0), Docker Desktop, server Docker
  29.7.2, `docker compose version` v5.4.0. Immagine `mongo:7.0.40` pinnata per digest
  `sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b`. Tre stack usa-e-getta
  (`spike-rs-a`, `spike-rs-b`, `spike-rs-c`) montati **fuori dal repository**, nella cartella
  temporanea della sessione, e smontati con `down -v` a misura presa. Nessuna porta pubblicata.
  Data: 2026-08-31.

**Prima strada — ADR-0026: nessuna variabile di root, `rs.initiate()` dentro il container.**

Tre `mongod` con `--replSet rs0 --keyFile /keyfile/mongo-keyfile --bind_ip_all`, il keyfile
generato da un servizio one-shot, e l'inizializzazione eseguita con `docker exec` **dentro** il
membro 1, senza passare credenziali:

```console
$ docker exec spike-a-rs-1 mongosh --quiet --eval 'rs.initiate({_id:"rs0", members:[...]})'
{"ok":1}
$ docker exec spike-a-rs-1 mongosh --quiet --eval 'db.getSiblingDB("admin").createUser({user:"lab-admin", pwd:"...", roles:["root"]})'
{ ok: 1 }
$ docker exec spike-a-rs-1 mongosh --quiet --eval 'db.getSiblingDB("prova").c.insertOne({x:1})'
MongoServerError[Unauthorized]: command insert requires authentication
```

Funziona, e funziona nell'ordine che [S-055](#s-055) prescrive: `replSetInitiate` passa,
`createUser` passa, e il primo comando successivo **non** passa più. L'ultima riga non è un
fallimento: è la ricevuta che l'eccezione si è chiusa da sé, esattamente dove la fonte dice che si
chiude. Il costo è tutto architetturale: `docker exec` non è un servizio Compose, quindi
`docker compose up -d` da solo **non** produce un replica set funzionante. Serve un passo fuori dal
file — uno script, un `make`, o le dita di chi presenta.

**Seconda strada — il design §5.4: variabili di root sul membro 1, sidecar autenticato.**

Prima domanda da sciogliere: l'entrypoint dell'immagine ufficiale, che per creare l'utente avvia un
`mongod` temporaneo togliendo `--replSet` ([S-022](#s-022)), sopravvive alla presenza di
`--keyFile`? Sì — nei log del membro compare `Successfully added user: { "user" : "lab-admin",
"roles" : [ "root" ] }`. Il caso che ADR-0026 aveva incontrato era `--configsvr`, che l'entrypoint
**non** toglie e che da solo non esiste: è quello a rompersi, non `--replSet`. La differenza fra i
due casi non era scritta da nessuna parte, e per sei giorni ADR-0026 è stato letto come se valesse
per entrambi.

Poi il sidecar, al primo colpo, è fallito:

```console
$ docker logs spike-b-rs-init
MongoNetworkError: connect ECONNREFUSED 172.20.0.3:27017
```

`depends_on` con `condition: service_started` è arrivato mentre il membro era ancora nella fase del
`mongod` temporaneo, che ascolta solo su loopback. È esattamente la corsa che il Task 5 del piano
aveva previsto, misurata prima di scrivere il file definitivo. Ripetuta l'inizializzazione a membri
avviati, la strada regge:

```console
$ mongosh --host mongo-rs-1 -u lab-admin -p ... --eval 'rs.initiate({...})'
{"ok":1}
$ mongosh ... --eval 'rs.status().members.map(m => m.stateStr).join(",")'
PRIMARY,SECONDARY,SECONDARY
```

E i membri 2 e 3, partiti **vuoti** e senza alcuna variabile di root, accettano le credenziali di
`lab-admin`: la sincronizzazione iniziale porta con sé anche la collezione `admin.system.users`.
Un utente creato su un membro solo diventa, senza altri passi, l'utente di tutto il set.

**Terza prova — l'affermazione del design sul sidecar è vera.**

Uno stack con un membro non inizializzato e un sidecar sulla rete Compose, che prova
`rs.initiate()` dall'esterno del container:

```console
$ docker logs spike-c-rs-init
ERRORE codeName=Unauthorized code=13
Command replSetInitiate requires authentication
```

L'affermazione del design regge. Il sidecar raggiunge il `mongod` — non è un problema di rete — ma
arriva da un altro indirizzo, e l'eccezione non lo riconosce. Ed è qui che si chiude una riserva
aperta da sei giorni: [S-006](#s-006) aveva dichiarato il 2026-08-25 che il vincolo «solo da
loopback» **non è enunciato da nessuna fonte primaria**, e [S-055](#s-055) ha confermato che
neppure la pagina della v7.0 lo enuncia. Adesso c'è la misura. Il vincolo esiste, il prodotto lo
applica, la documentazione non lo scrive: la riserva passa da «vero per convenzione» a «vero,
misurato qui, e ancora non scritto dalla fonte».

**Quarta prova — la terza via: un sidecar che condivide il namespace di rete del membro.**

Se il problema è l'indirizzo di provenienza, si può cambiare l'indirizzo di provenienza invece di
rinunciare all'eccezione. Un container avviato con `--network container:<membro>` — in Compose
`network_mode: "service:mongo-rs-1"` — non ha una propria interfaccia di rete: **usa quella del
membro**, e `localhost` dentro il sidecar è lo stesso `localhost` del `mongod`.

```console
$ docker run --rm --network container:spike-c-rs-1 mongo@sha256:b642... \
    mongosh --quiet --host localhost --eval '...'
NAMESPACE_CONDIVISO_OK {"ok":1}
UTENTE_CREATO da sidecar in namespace condiviso
CHIUSA_DOPO_IL_PRIMO_UTENTE codeName=Unauthorized code=13
```

Le tre righe sono la strada intera in tre battute: l'eccezione si apre a un container che non è il
membro, concede `replSetInitiate` e poi `createUser`, e si chiude subito dopo. Questa via non sta
né nel design né in ADR-0026: è saltata fuori chiedendosi *perché* la prova C fallisse, invece di
prendere atto che falliva.

**Misura di contorno, raccolta di passaggio e utile al Task 5.** Su un `mongod` avviato con
`--keyFile` e non ancora inizializzato, `hello()` risponde **senza credenziali**:

```console
$ docker exec spike-c-rs-1 mongosh --quiet --eval 'const h = hello(); print("isWritablePrimary=" + h.isWritablePrimary + " secondary=" + h.secondary)'
isWritablePrimary=false secondary=true
```

Serve a disinnescare l'uovo e la gallina dell'healthcheck: un controllo che chiede «`hello()`
risponde?» diventa verde **prima** dell'inizializzazione, e quindi un servizio di inizializzazione
può dipendere da `service_healthy` senza aspettare qualcosa che solo lui può produrre. Un controllo
che chiedesse «sei primario o secondario?» resterebbe rosso fino a `rs.initiate()`, e
l'inizializzazione non partirebbe mai.

- **Conseguenza:** le tre strade funzionano tutte, quindi la scelta non è tecnica ma di prezzo.
  ADR-0026 costa un passo fuori da Compose; il design costa una password nel repository; la terza
  via non costa nessuno dei due e paga con un costrutto Docker che va spiegato. La decisione è
  registrata in [ADR-0040](Decision.md#adr-0040).
- **Riserve:** tutto su una macchina sola, su Docker Desktop, con una sola ripetizione per strada;
  le prove dicono *che* una strada funziona, non quanto sia stabile sotto ripetizione o su Linux
  nativo. La corsa del sidecar della strada B è stata osservata una volta e aggirata a mano: non è
  stato misurato dopo quanto tempo il membro smette di rifiutare la connessione, perché la
  soluzione scelta non passa da un'attesa a tempo. Il comportamento di `network_mode:` con
  `service:` è stato provato nella forma equivalente da riga di comando (`docker run --network
  container:…`), e non ancora dentro un file Compose del repository: la conferma nella forma
  definitiva spetta al Task 2.
- **Data:** 2026-08-31
- **Usata da:** ADR-0040

---

<a id="v-024"></a>
### V-024 — La terza via nella forma definitiva: un container che non ha una rete propria, e per questo può creare il primo utente

- **Comandi:** `docker compose --env-file tools/images.env --env-file docker/02-replicaset/.env -f
  docker/02-replicaset/compose.yaml up -d --wait` · `docker inspect` · `docker logs rs-init` ·
  `mongosh`
- **Ambiente:** macOS 26.6.2 arm64, Docker 29.7.2, Compose v5.4.0, immagine
  `mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b` (MongoDB 7.0.40),
  stack `docker/02-replicaset/compose.yaml` del repository, volumi vuoti
- **Che cosa restava da dimostrare:** [V-023](#v-023) chiudeva con una riserva scritta a chiare
  lettere — il comportamento di `network_mode: "service:"` era stato provato «nella forma
  equivalente da riga di comando (`docker run --network container:…`), e non ancora dentro un file
  Compose del repository». Su quella prova incompleta è stato deciso [ADR-0040](Decision.md#adr-0040).
  Questa voce salda il debito: stessa terza via, ma nello stack vero, scritta come la leggerà chi
  clona.
- **Esito, il namespace è davvero condiviso:** Compose non copia la configurazione di rete del
  membro, aggancia `rs-init` al suo container. L'identificatore che compare in `NetworkMode` è, cifra
  per cifra, l'identificatore di `mongo-rs-1`:

```
NetworkMode di rs-init: container:fdf722b35d3d782d47a5e97caef7ce21ab0ebd3581795d6566cd1fff735fa8d7
id di mongo-rs-1:       fdf722b35d3d782d47a5e97caef7ce21ab0ebd3581795d6566cd1fff735fa8d7
indirizzo di mongo-rs-1: 172.18.0.3
```

C'è un solo indirizzo, e appartiene al membro. `rs-init` non ne ha uno suo: quando parla a
`localhost` parla all'interfaccia del `mongod`, che è la ragione per cui l'eccezione localhost lo
riconosce.

- **Esito, la catena arriva in fondo da sola:** quattro righe, nell'ordine previsto, con codice di
  uscita 0.

```
inizializzo il replica set «rs0»
primario eletto: mongo-rs-1:27017
utente amministratore «admin» creato
catena completata
```

- **Esito, il set esiste ed è chiuso:** con le credenziali si vede il set formato; senza, la stessa
  interrogazione viene rifiutata. L'eccezione localhost si è richiusa da sé alla creazione del primo
  utente, come [S-055](#s-055) prescrive.

```
set=rs0
  mongo-rs-1:27017  PRIMARY  health=1
  mongo-rs-2:27017  SECONDARY  health=1
  mongo-rs-3:27017  SECONDARY  health=1
--- senza credenziali ---
rifiutato: Unauthorized (13)
```

Una scrittura con `w: "majority"` sul primario torna `inserito=true` e il documento si legge sul
membro 3: la replica non è solo dichiarata, trasporta dati.

- **Esito, l'healthcheck è verde in tutte e due le fasi, per due motivi diversi:** è il punto che
  vale la pena guardare due volte. La condizione scritta nel file è
  `h.isWritablePrimary || h.secondary || h.isreplicaset === true`, ed è un `or` di tre termini
  perché nessuno dei tre da solo copre entrambe le fasi. Prima di `rs.initiate()` i tre membri
  rispondono `isWritablePrimary=false secondary=false isreplicaset=true` ([V-023](#v-023), con la
  nota di precisione in testa a quella voce): passa il terzo termine. Dopo, `isreplicaset` sparisce
  e passano i primi due:

```
mongo-rs-1  isWritablePrimary=true secondary=false isreplicaset=undefined
mongo-rs-2  isWritablePrimary=false secondary=true isreplicaset=undefined
mongo-rs-3  isWritablePrimary=false secondary=true isreplicaset=undefined
```

Un healthcheck che avesse chiesto solo «sei primario o secondario?» sarebbe rimasto rosso nella
prima fase, e `rs-init` — che dipende da `service_healthy` — non sarebbe mai partito per produrre
proprio ciò che gli si chiedeva di avere già. Un healthcheck che avesse chiesto solo
`isreplicaset === true` sarebbe diventato rosso appena il set si forma, cioè avrebbe segnato come
malato uno stack perfettamente sano.

- **Conseguenza:** la riserva di [V-023](#v-023) è scaricata, e [ADR-0040](Decision.md#adr-0040)
  regge nella forma definitiva senza modifiche. Il resto delle conseguenze — quando la catena si
  possa dire finita — sta in [V-025](#v-025) e in [ADR-0041](Decision.md#adr-0041).
- **Riserve:** una macchina sola, Docker Desktop, nessuna prova su Linux nativo. `NetworkMode` dice
  `container:<identificatore>`, non `service:mongo-rs-1`: Compose risolve il nome del servizio in un
  identificatore **al momento della creazione**, il che implica che `mongo-rs-1` debba esistere
  prima di `rs-init`. Qui quell'ordine è garantito dal `depends_on`, e **non è stato misurato** che
  cosa succeda togliendolo — la prova non è stata fatta perché il `depends_on` serve comunque per la
  condizione `service_healthy`, ma resta un'affermazione che questo repository non ha verificato.
  Infine, che `rs-init` non possa pubblicare porte né essere raggiunto per nome sulla rete Compose è
  dedotto dal non avere un'interfaccia propria, non provato tentandolo.
- **Data:** 2026-08-31
- **Usata da:** ADR-0041

---

<a id="v-025"></a>
### V-025 — «Fatto» detto due volte: `up --wait` esce con successo quattordici secondi prima che la replica esista

> **Nota di allineamento, 2026-08-31.** Il fenomeno descritto qui regge intatto, il numero no.
> Al Task 7 il caricamento dei dati di demo è entrato dentro `rs-init` ([ADR-0043](Decision.md#adr-0043)),
> quindi quel servizio dura di più e lo scarto misurato è salito a **ventidue** secondi
> ([V-028](#v-028)). Il titolo resta com'era perché così è stato misurato quel giorno, su quella
> configurazione: chi cita lo scarto citi la voce che corrisponde allo stack che ha davanti, e
> soprattutto lo rimisuri invece di impararlo a memoria — è la conclusione, non il quattordici.

- **Comandi:** `docker compose … up -d --wait` · `docker compose … wait rs-init` ·
  `docker compose … config` · `docker inspect`
- **Ambiente:** macOS 26.6.2 arm64, Docker 29.7.2, Compose v5.4.0, stack
  `docker/02-replicaset/compose.yaml`, immagine `mongo@sha256:b6421fd6…` (MongoDB 7.0.40)
- **Esito, lo scarto:** `up -d --wait` termina con codice 0 dopo otto secondi. In quell'istante
  `rs-init` è in stato `running` — ha appena cominciato — e chi si collega al membro 1 riceve un
  errore:

```
«up -d --wait» uscita=0 dopo 8 secondi
stato di rs-init in quell'istante: running
--- che cosa vede un client in quell'istante ---
NotYetInitialized (94)

rs-init uscito dopo 22 secondi dall'avvio, codice=0
scarto fra «up dice fatto» e «la replica c'e'»: 14 secondi
```

Quattordici secondi in cui il comando ha già detto di sì e il replica set non esiste. Il perché sta
nella definizione: [S-057](#s-057) documenta `--wait` come «Wait services be running|healthy», e
`rs-init` non ha un healthcheck — quindi la soglia applicabile è `running`. Un container che deve
morire è `running` **nel momento esatto in cui comincia**, e `--wait` si dichiara soddisfatto lì.
Non è un difetto di Compose: è l'opzione che fa quello che dichiara, applicata a un servizio per cui
la parola «pronto» significa il contrario di «in esecuzione».

- **Esito, come si chiude lo scarto:** `docker compose wait rs-init` — «Block until containers of
  all (or specified) services stop», [S-057](#s-057) — blocca fino all'uscita e ne riporta il
  codice.

```
«up -d --wait» + «wait rs-init»: 20 secondi, uscita=0
stampato da «compose wait»: container "6727c2a2386e…" exited with status code 0
subito dopo wait: set=rs0
```

Le due opzioni non sono alternative e non si somigliano: `up --wait` serve ai tre membri, che devono
essere **sani**; `compose wait` serve a `rs-init`, che deve essere **finito**. Lo stack ne ha bisogno
di entrambe perché contiene i due generi di servizio.

- **Esito, un solo `--env-file` non basta, e si vede:** lo stack ha bisogno di due file d'ambiente —
  il pin dell'immagine in `tools/images.env`, la password in `docker/02-replicaset/.env`. Passando
  solo il primo, il secondo **non viene letto**, benché stia accanto al file indicato con `-f`:

```
uscita di «config» con un solo --env-file: 1
error while interpolating services.rs-init.environment.PASSWORD_AMMINISTRATORE: required variable
PASSWORD_AMMINISTRATORE is missing a value: assente — copiare docker/02-replicaset/.env.example in
.env e riempire la password
```

È la conferma diretta di [S-056](#s-056): «Passing the `--env-file` argument overrides the default
file path». La flag non aggiunge un file, ne prende il posto. Con entrambe le occorrenze lo stesso
comando esce 0. Vale la pena notare **come** si è manifestato l'errore: non con un utente creato con
password vuota, ma con un rifiuto che nomina il file da copiare. Quel messaggio esiste perché la
variabile è scritta nella forma `${PASSWORD_AMMINISTRATORE:?…}`; nella forma senza `:?` la stessa
dimenticanza sarebbe passata in silenzio.

- **Esito, l'idempotenza:** rieseguendo l'avvio su uno stack già inizializzato, `rs-init` riconosce
  il set e non tocca niente, uscendo di nuovo 0. `docker logs rs-init` mostra **entrambe** le
  esecuzioni una dopo l'altra, perché Compose riavvia il container one-shot esistente invece di
  crearne uno nuovo: le prime quattro righe sono del primo avvio, le seconde quattro del secondo.

```
inizializzo il replica set «rs0»
primario eletto: mongo-rs-1:27017
utente amministratore «admin» creato
catena completata
replica set «rs0» già formato: non lo reinizializzo
primario eletto: mongo-rs-1:27017
utente amministratore già presente: non lo ricreo
catena completata
```

- **Esito, i tempi, con una sorpresa:** misurati dal lancio alla fine di `compose wait rs-init`,
  cioè fino alla replica realmente formata.

```
freddo, giro 1: 21 secondi
freddo, giro 2: 21 secondi
freddo, giro 3: 19 secondi
caldo (volumi conservati): 24 secondi
```

Il riavvio **a caldo è più lento** dell'avvio da volumi vuoti. Controintuitivo, e utile a chi deve
riavviare lo stack in sala: non conviene fare `down` e `up` sperando che «tanto i dati ci sono già».
Dopo uno smontaggio completo si spengono tre membri, e alla ripartenza il set deve rieleggere un
primario prima che qualunque cosa funzioni; da volumi vuoti l'elezione è la prima e avviene su un
set appena costruito. Questa è però una **spiegazione**, non una misura: vedi le riserve.

- **Conseguenza:** l'avvio dello stack 02 è di due comandi, non di uno, e gli ambienti si passano
  con due `--env-file`. Registrato in [ADR-0041](Decision.md#adr-0041), che ne fa la forma
  obbligatoria per il Makefile del Task 7.
- **Riserve:** i secondi valgono per questa macchina e per questa immagine, e non vanno riportati
  come previsione altrove: quello che non cambia è **che lo scarto esista**, perché discende dalla
  definizione di `--wait` e non dalla velocità dell'host. Il numero 14 è di una sola esecuzione. La
  lentezza dell'avvio a caldo è stata osservata **una volta sola**, contro tre giri a freddo: la
  differenza è larga (24 contro 19÷21) ma un solo campione non stabilisce una regola, e la causa
  proposta — la rielezione del primario dopo lo spegnimento — non è stata isolata da nessuna misura,
  è un'ipotesi coerente con il funzionamento noto del protocollo. Va rifatta con più ripetizioni
  prima di dirla in sala. Infine `compose wait` è stato osservato solo su un'uscita 0: che riporti
  fedelmente anche un codice diverso da zero è documentato ma non provato qui, e conviene provarlo
  al Task 7, dove quel codice diventa il verdetto di un bersaglio del Makefile.
- **Data:** 2026-08-31
- **Usata da:** ADR-0041

---

<a id="v-026"></a>
### V-026 — Sei mutazioni sul file vero: un controllo che non si è visto fallire lì dove serve non è un controllo

- **Comandi:** `uv run --project tools python tools/check_stack.py --variabile
  PASSWORD_AMMINISTRATORE=… <copia mutata di docker/02-replicaset/compose.yaml>`, ripetuto su sei
  copie, ognuna con un solo difetto introdotto
- **Ambiente:** macOS 26.6.2 arm64, Python 3.13 via `uv`, `tools/check_stack.py` dopo il Task 6 di
  `feature/02`, `tools/images.env` come file d'ambiente predefinito
- **Che cosa restava da dimostrare:** le quattro regole nuove del Task 6 erano rosse sui campioni
  costruiti nei test, e verdi sui due file veri. Verde su un campione costruito prova che la regola
  esiste; verde sul file vero **non prova niente**, perché non distingue «la regola ha guardato e ha
  approvato» da «la regola non è mai entrata in funzione». Le regole 2 e 4 si autolimitano leggendo
  il file — la 2 si accende solo se qualcuno dichiara `--replSet`, la 4 solo se qualcuno dichiara
  `depends_on` — e una guardia scritta male le spegne in silenzio proprio sul file che contava.
- **Metodo:** si prende il file vero, se ne fa una copia, si introduce **un solo** difetto, si passa
  la copia allo strumento. Se il messaggio giusto compare, la regola era accesa su quel file. Il
  difetto viene introdotto con `sed` o con una sostituzione che verifica prima quante occorrenze
  esistono, così una modifica che non ha attecchito si presenta come un errore invece che come un
  verde.
- **Esito, sei difetti e sei messaggi distinti:**

```
regola 1 — keyfile da bind mount
  ✗ mongo-rs-1: il keyfile «/keyfile/mongo-keyfile» arriva da «./keyfile», che è un
    percorso dell'host. […] serve un volume nominato (ADR-0014)

regola 2 — membro senza --keyFile
  ✗ mongo-rs-1: avvia un membro di replica set senza «--keyFile». Parte lo stesso e resta
    fuori dalla replica: gli altri lo rifiutano all'handshake […] (ADR-0014)

regola 3 — one-shot con restart che lo rialza
  ✗ keyfile-init: «mongo-rs-1» lo attende come completato, ma «keyfile-init» non dichiara
    «restart: "no"». Compose lo rialza appena esce […] (ADR-0023)

regola 4 — service_started verso un mongod
  ✗ rs-init attende «mongo-rs-1» con «service_started», ma «mongo-rs-1» avvia un mongod:
    la condizione scatta quando il container esiste, non quando il server risponde […]

regola 4 — service_started verso un one-shot
  ✗ mongo-rs-1 attende «keyfile-init» con «service_started», ma «keyfile-init» è un
    one-shot […]: riesce sulla macchina veloce e fallisce in sala […]

difetto vecchio — forma abbreviata senza cache
  ✗ mongo-rs-1: avvia mongod senza «--wiredTigerCacheSizeGB» […] (ADR-0004)
```

- **Esito, il file intatto:**

```
Stack conformi: 1.
uscita: 0
```

L'ultima delle sei merita una riga a parte, perché non è una regola nuova: è una regola vecchia che
non poteva fallire. `avvia_mongod()` riconosceva solo i comandi che cominciano con la parola
`mongod`; l'entrypoint ufficiale dell'immagine antepone `mongod` da sé quando il primo argomento
comincia per trattino ([S-022](#s-022)), e nella forma abbreviata — quella che gira in metà degli
esempi in rete — lo strumento non vedeva un mongod, quindi non pretendeva né la cache né il keyfile.
Una regola che dorme è peggio di una regola assente: dà la ricevuta senza aver guardato.

- **Conseguenza:** `make stack-check` passa ora entrambi i file Compose e non solo il primo; le
  quattro regole nuove e la correzione della forma abbreviata sono registrate in
  [ADR-0042](Decision.md#adr-0042).
- **Riserve:** sei difetti non sono tutti i difetti. Questa prova stabilisce che ogni regola nuova
  è **accesa** sul file vero, non che l'insieme delle regole sia completo: un file Compose può
  restare conforme a tutte e sei e non funzionare comunque, e infatti la conformità statica non ha
  mai sostituito l'avvio dello stack, che resta il verdetto di [V-024](#v-024) e [V-025](#v-025).
  Le mutazioni sono state introdotte a mano, una volta sola, e non da un generatore sistematico:
  non c'è un numero di copertura da citare, c'è un elenco di sei casi che si possono rileggere.
- **Data:** 2026-08-31
- **Usata da:** ADR-0042

---

<a id="v-027"></a>
### V-027 — Il ritardo di replica a riposo, e quanto costa davvero chiedere la maggioranza

- **Comandi:** `mongosh --file` di uno script che scrive sul primario e interroga un secondario in
  un ciclo stretto finché il documento non compare; 10 giri per esecuzione, 3 esecuzioni
- **Ambiente:** macOS 26.6.2 arm64, Docker 29.7.2, Compose v5.4.0, stack
  `docker/02-replicaset/compose.yaml`, tre membri con 768 MiB e 0,75 CPU ciascuno, replica formata
  e `lab.ordini` già caricata, nessun altro carico
- **Che cosa si voleva sapere:** la pagina del Task 9 parla di «ritardo di replica» e senza un
  numero non lo mostra. Serviva anche il prezzo di `w: "majority"`, perché il dataset dello stack 02
  si scrive così e dire «costa di più» senza dire quanto è un'affermazione che non impegna nessuno.
- **La misura ovvia non funziona, ed è il primo risultato.** `rs.status()` porta `optimeDate` per
  ogni membro, e la differenza fra primario e secondari è il modo in cui il ritardo si misura in
  tutti gli esempi che si trovano. Su questo set, a riposo, tre letture a cinque secondi di
  distanza:

```
mongo-rs-2:27017  ritardo 0 ms
mongo-rs-3:27017  ritardo 0 ms
```

`optimeDate` deriva dal timestamp dell'oplog, che ha **granularità di un secondo**: quello zero non
significa «nessun ritardo», significa «meno di un secondo, e più in là non vedo». Per un set che
replica in millisecondi è uno strumento che risponde sempre la stessa cosa.

- **La misura vera:** si scrive sul primario con `w: 1` — che torna appena il primario ha preso la
  scrittura, quindi il cronometro parte prima che i secondari sappiano qualcosa — e si interroga un
  secondario in un ciclo finché il documento non compare.

```
esecuzione 1
ritardo primario -> secondario     min 1  mediana 1  max 3   media 1.6 ms
costo di una scrittura w: 1        min 0  mediana 1  max 58  media 7.0 ms
costo di una w: majority           min 2  mediana 2  max 68  media 8.9 ms
valori grezzi del ritardo: 3 1 1 1 1 3 2 2 1 1

esecuzione 2
ritardo primario -> secondario     min 1  mediana 1  max 9   media 1.9 ms
costo di una scrittura w: 1        min 0  mediana 1  max 9   media 1.6 ms
costo di una w: majority           min 1  mediana 2  max 3   media 2.0 ms
valori grezzi del ritardo: 9 1 1 2 1 1 1 1 1 1

esecuzione 3
ritardo primario -> secondario     min 1  mediana 1  max 46  media 6.2 ms
costo di una scrittura w: 1        min 0  mediana 1  max 8   media 1.8 ms
costo di una w: majority           min 2  mediana 2  max 82  media 10.4 ms
valori grezzi del ritardo: 46 1 3 6 1 1 1 1 1 1
```

**I due numeri da tenere sono le mediane, e le medie vanno ignorate.** Ritardo mediano **1 ms**;
`w: 1` mediana **1 ms**, `w: "majority"` mediana **2 ms**. Le medie sono più alte perché ogni
esecuzione ha esattamente un valore fuori scala — 3, 9, 46 — ed è sempre **il primo giro**: i valori
grezzi lo mostrano a occhio. Non è ritardo di replica, è la prima connessione al secondario che si
apre e si autentica. Una media su dieci giri di cui uno è il riscaldamento non descrive niente.

- **Conseguenza:** chiedere la maggioranza costa **un millisecondo in più** che non chiederla, su
  questa configurazione. Registrato in [ADR-0043](Decision.md#adr-0043) come il motivo per cui il
  dataset dello stack 02 si scrive con `w: "majority"` senza rimpianti: la garanzia si prende perché
  è quasi gratis, non perché il prezzo non conti.
- **Riserve:** e sono la parte importante di questa voce. **I tre membri girano sulla stessa
  macchina**, dentro la stessa rete Docker: fra loro non c'è una rete vera, c'è un bridge locale.
  Il costo di `w: "majority"` è, per definizione, un giro fino al secondo membro più veloce — qui
  vale un millisecondo, su due datacenter varrebbe la latenza fra i due datacenter, e sarebbe il
  termine dominante. Il numero **non va portato sul palco come se descrivesse la produzione**: va
  detto insieme alla frase che lo qualifica. Seconda riserva: il ciclo di attesa costa un giro di
  rete per ogni tentativo, quindi il ritardo misurato ha un pavimento di circa un giro — il ritardo
  vero potrebbe essere sotto il millisecondo e questo metodo non saprebbe distinguerlo. Terza: il
  set è a riposo e la collezione di prova è vuota; sotto il carico della demo dell'applicazione i
  numeri saranno altri, e vanno rimisurati là invece che estrapolati da qui.
- **Data:** 2026-08-31
- **Usata da:** ADR-0043, ADR-0046

---

<a id="v-028"></a>
### V-028 — Lo stack 02 dall'avvio alla prova: 42 controlli, e lo stesso dataset dello stack 01

- **Comandi:** `make up-02` · `make seed-02` · `make reset-02` · `make down-02` · `make smoke-02` ·
  `docker stop mongo-rs-3`
- **Ambiente:** macOS 26.6.2 arm64, Docker 29.7.2, Compose v5.4.0, immagine
  `mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b` (MongoDB 7.0.40)
- **Che cosa si voleva sapere:** se i sei bersagli del `Makefile`, il seed dentro `rs-init` e
  `tools/smoke-replicaset.sh` fanno quello che dicono — e, soprattutto, se lo smoke sa diventare
  rosso. Un `Superati: 42 · Errori: 0` che non si è mai visto fallire vale quanto il verde del
  Task 6 prima di [V-026](#v-026).
- **Esito, l'avvio a freddo:**

```
up --wait uscita=0
container "4955bdf1…" exited with status code 0
compose wait rs-init uscita=0

up --wait ha impiegato   8 secondi
compose wait ha aggiunto 22 secondi
totale                   30 secondi

=== log di rs-init ===
inizializzo il replica set «rs0»
primario eletto: mongo-rs-1:27017
utente amministratore «admin» creato
catena completata
Carico 50000 ordini in lab.ordini con w: "majority"...
Caricati 50000 ordini in 6439 ms.
```

Il divario fra i due comandi è ora di **22 secondi**, non dei 14 misurati in [V-025](#v-025): il
seed vive dentro `rs-init`, quindi `rs-init` dura di più, quindi il tratto che `up --wait` non copre
si allunga. Il fenomeno è lo stesso e la conclusione di [ADR-0041](Decision.md#adr-0041) non cambia
— cambia il numero, ed è il motivo per cui il numero non va imparato a memoria.

- **Esito, l'impronta del dataset:**

```
✓ impronta di lab.ordini: 50000 124861860.70 150281
```

Sono **gli stessi tre numeri** dello stack 01 ([V-013](#v-013)), ottenuti da un file diverso, su una
topologia diversa, con un write concern diverso. È il controllo che tiene insieme i due stack: una
parte della demo confronta la stessa interrogazione sull'uno e sull'altro, e con dataset diversi il
confronto sarebbe una recita. I due script di prova sorvegliano la stessa terna, quindi modificarne
uno solo fa fallire l'altro.

- **Esito, lo smoke sa diventare rosso.** Con `docker stop mongo-rs-3`:

```
uscita=1
  ✗ salute di mongo-rs-3: atteso healthy, ottenuto «unhealthy»
  ✗ PID 1 non è mongod su mongo-rs-3: «»
  ✗ i tre keyfile differiscono o mancano: 33257423… 33257423…
  ✗ secondari: atteso 2, ottenuto «1»
  ✗ membri non in salute: atteso nessuno, ottenuto «mongo-rs-3:27017»
  ✗ memoria vista da mongo-rs-3 (MiB): atteso 768, ottenuto «»
  ✗ cache WiredTiger di mongo-rs-3 (byte): atteso 268435456, ottenuto «»
  ✗ nessuna porta pubblicata per mongo-rs-3:27017
Superati: 34 · Errori: 8
```

E, nella stessa esecuzione, le risposte che contano:

```
  ✓ primari: 1
  ✓ scrittura con w: majority accettata: true
  ✓ rilettura da mongo-rs-2 (secondario): 1
  ✓ impronta di lab.ordini: 50000 124861860.70 150281
```

Questo è un risultato di progetto, non solo una prova: la prima versione dello script si fermava
dopo tre righe, perché aveva ereditato da `smoke-standalone.sh` un cancello che esce appena un nodo
non è sano. Su un'istanza singola quel cancello è giusto — senza il nodo non c'è niente da chiedere.
Su tre membri butta via esattamente le risposte che uno cerca in quel momento. Il cancello è stato
ristretto al caso «il container non esiste»:

```
  ✗ il container mongo-rs-3 non esiste — esegui prima «make up-02»
Superati: 0 · Errori: 3
Mancano 3 container su 3: lo stack non è avviato.
```

- **Esito, `reset-02` conserva il segreto:**

```
prima:  volumi dati-1 dati-2 dati-3 keyfile   keyfile sha 33257423c039b2a2
dopo:   volumi keyfile                        keyfile sha 33257423c039b2a2
```

- **Esito, i tempi degli altri bersagli:** `make up-02` a caldo (dati conservati) 16 s; dopo
  `reset-02`, cioè con i dati da rifare e il keyfile già buono, 29 s; `make seed-02` su uno stack in
  piedi ricarica 50 000 documenti in 7 658 ms e stampa da sé le due righe dell'idempotenza
  («replica set già formato: non lo reinizializzo», «utente amministratore già presente»).
  `make smoke-02` è stato eseguito quattro volte di fila su stack sano: `Superati: 42 · Errori: 0`
  tutte e quattro.
- **Conseguenza:** i sei bersagli, il seed dentro `rs-init` e lo script di prova sono registrati in
  [ADR-0043](Decision.md#adr-0043).
- **Riserve:** una macchina sola, Docker Desktop, nessun Linux nativo — vale per i tempi, non per
  gli esiti. Lo smoke è stato visto fallire su **un** guasto, un membro fermato: gli altri 34
  controlli restano verdi perché il resto funzionava, non perché siano stati messi alla prova uno
  per uno come in [V-026](#v-026). Il caso «due membri fermi su tre», che è quello interessante —
  il set perde la maggioranza e diventa di sola lettura — non è stato provato qui: è la scena del
  Task 8, e va misurato là. Infine `make down-02` e `make reset-02` sono stati eseguiti su uno stack
  che non aveva mai perso un volume per errore: che si comportino bene su uno stato sporco non è
  stato verificato.
- **Data:** 2026-08-31
- **Usata da:** ADR-0043

---

<a id="v-029"></a>
### V-029 — Dieci secondi contro mezzo: le due morti di un primario non costano lo stesso

- **Comandi:** `docker kill <primario>` · `db.adminCommand({shutdown: 1})` · un `mongosh` che
  gira dentro un membro superstite e interroga `hello()` in un ciclo da 20 ms · `docker inspect`
- **Ambiente:** macOS 26.6.2 arm64, Docker 29.7.2, Compose v5.4.0, stack
  `docker/02-replicaset/compose.yaml`, tre membri sani, `mongo-rs-1` primario per priorità 2,
  nessun carico applicativo. Tre esecuzioni per scena.
- **Che cosa si voleva sapere:** quanto dura, cronometrato, l'intervallo fra la caduta del
  primario e il momento in cui un client può di nuovo scrivere. Il numero serve alla pagina del
  Task 9 e serve a decidere se la scena regge dal vivo — dieci secondi di schermo fermo davanti a
  cento persone sono una cosa diversa da due.
- **Come si è misurato, e perché non nel modo ovvio.** Il cronometro non poteva partire *dopo* il
  colpo: `mongosh` impiega quasi un secondo ad avviarsi e ad autenticarsi, e quel secondo sarebbe
  finito dentro la misura. L'osservatore viene quindi avviato **prima**, dentro un membro
  superstite; quando è connesso e caldo stampa `PRONTO`, e solo allora chi lo ha lanciato uccide il
  primario e segna `t0`. Il ciclo interroga `hello()` ogni 20 ms fino a vedere un `primary` diverso
  da quello di partenza.

- **Esito, scena 1 — `docker kill` sul primario:**

```
giro 1   nuovo primario mongo-rs-3:27017   elezione in  9812 ms
giro 2   nuovo primario mongo-rs-2:27017   elezione in 10619 ms
giro 3   nuovo primario mongo-rs-3:27017   elezione in 10943 ms
stato del container ucciso, tutte e tre le volte:
  Status=exited  RestartCount=0  ExitCode=137
```

- **Esito, scena 2 — il processo esce da sé (`shutdownServer()`):**

```
giro 1   nuovo primario mongo-rs-2:27017   elezione in 574 ms
giro 2   nuovo primario mongo-rs-2:27017   elezione in 480 ms
giro 3   nuovo primario mongo-rs-2:27017   elezione in 486 ms
stato del container terminato:
  Status=running  RestartCount=1, poi 2, poi 3  ExitCode=0
```

**Venti volte più veloce, e nel verso che nessuno si aspetta.** Il gesto brutale è quello lento; il
gesto educato è quello rapido. Il motivo sta nel log ([V-030](#v-030)) e non è misterioso: con
`docker kill` nessuno avvisa nessuno, quindi i superstiti devono aspettare che scada
`electionTimeoutMillis` — che vale 10 000 ms, e infatti i tre numeri della scena 1 stanno tutti
poco sopra i dieci secondi. Con `shutdown` il primario cede il ruolo *e lo dice*: non c'è nessun
timeout da far scadere, e restano solo i millisecondi del voto.

- **`RestartCount=0` è la seconda metà del risultato.** Su un replica set vale quello che
  [V-017](#v-017) aveva misurato su un'istanza singola: dopo un `docker kill` la politica
  `restart: unless-stopped` **non interviene**, perché per il demone quella fermata l'ha voluta un
  umano. Il container resta `exited` con `ExitCode=137`, e ci resta finché qualcuno non lo riavvia.
  Dopo lo `shutdown`, invece, `RestartCount` avanza a ogni giro e il membro torna su da sé: è la
  prova che la politica funziona e che il problema non era mai la politica.
- **Conseguenza:** le due scene sono due bersagli distinti — `make failover-02` e
  `make failover-02-termina` — registrati in [ADR-0044](Decision.md#adr-0044). La misura conferma
  su tre membri quanto [ADR-0034](Decision.md#adr-0034) aveva deciso su uno solo, e le dà il numero
  che le mancava.
- **Riserve:** tre membri sulla stessa macchina, senza carico e senza rete vera: i dieci secondi
  sono dominati da un timeout di configurazione e quindi reggeranno altrove, ma il mezzo secondo
  della scena 2 no — è tempo di rete e di voto, e su datacenter separati vale di più.
  `electionTimeoutMillis` non è stato modificato: abbassarlo accorcerebbe la scena 1, e non lo si è
  fatto apposta, perché il valore predefinito è quello che il pubblico troverà. Le tre esecuzioni
  per scena sono poche per parlare di distribuzione; bastano per dire che i due ordini di grandezza
  non si sovrappongono. Infine il primario è sempre stato `mongo-rs-1`: il caso in cui cade un
  **secondario** — che non provoca nessuna elezione — non è cronometrato qui perché non ha niente
  da cronometrare.
- **Data:** 2026-08-31
- **Usata da:** ADR-0044, ADR-0046

---

<a id="v-030"></a>
### V-030 — Le righe di un'elezione, finalmente viste: il voto dura sei millisecondi, il resto è attesa

- **Comandi:** `docker kill <primario>` · `docker logs mongo-rs-2` · filtro per `id` sul JSON
- **Ambiente:** come [V-029](#v-029). Log del membro **eletto** (`mongo-rs-2`), non di chi ha votato.
- **Che cosa si voleva sapere:** [ADR-0035](Decision.md#adr-0035) aveva lasciato aperto un debito
  dichiarato: la sezione sull'elezione di `docs/03-amministrazione/log.md` poggiava solo su
  [S-044](#s-044), che descrive il meccanismo ma **non nomina una sola riga di log**. Gli `id`
  andavano inseriti «in `feature/02`, dopo averne vista una». Questa è quella.

- **Esito, la sequenza completa** (orari veri, un'elezione sola):

```
19:01:47.369  id=21216    REPL      Member is now in state DOWN
              attr: hostAndPort=mongo-rs-1:27017, heartbeatMessage="Connection refused"

   ... nove secondi, e diciannove ripetizioni di id=23974 «Heartbeat failed after max retries» ...

19:01:56.558  id=4615652  ELECTION  Starting an election, since we've seen no PRIMARY in
                                    election timeout period
              attr: electionTimeoutPeriodMillis=10000
19:01:56.558  id=21438    ELECTION  Conducting a dry run election to see if we could be elected
              attr: currentTerm=13
19:01:56.560  id=51799    ELECTION  VoteRequester processResponse
              attr: dryRun=true, vote="yes", from=mongo-rs-3:27017
19:01:56.560  id=21444    ELECTION  Dry election run succeeded, running for election
              attr: newTerm=14
19:01:56.560  id=6015300  ELECTION  Storing last vote document in local storage for my election
19:01:56.564  id=51799    ELECTION  VoteRequester processResponse
              attr: dryRun=false, vote="yes", from=mongo-rs-3:27017
19:01:56.564  id=21450    ELECTION  Election succeeded, assuming primary role
              attr: term=14
19:01:56.564  id=21358    REPL      Replica set state transition
              attr: newState="PRIMARY", oldState="SECONDARY"
```

Sul membro che ha **votato** e non è stato eletto compaiono invece solo `id=23980` «Responding to
vote request», due volte — una per il giro a vuoto e una per quello vero — e `id=21215` «Member is
in new state».

**Il numero che cambia il racconto: 56.558 → 56.564 sono sei millisecondi.** L'elezione vera —
giro a vuoto, voto scritto su disco, richiesta di voto, ruolo assunto — dura quanto un battito di
ciglia. I dieci secondi di [V-029](#v-029) non sono l'elezione: sono l'**attesa prima di
cominciarla**, e il log lo dice per esteso in un attributo, `electionTimeoutPeriodMillis: 10000`.
Ancora più preciso: la caduta è **notata subito**, a `19:01:47.369`, tre decimi di secondo dopo il
colpo, con «Connection refused» scritto nell'attributo. Il set sa che il primario è morto quasi
istantaneamente e aspetta comunque dieci secondi prima di reagire — perché un membro irraggiungibile
per un istante non è un membro morto, e indire un'elezione a ogni singhiozzo di rete costerebbe più
di quello che salva.

- **Conseguenza:** gli `id` entrano in `docs/03-amministrazione/log.md` al Task 12, e la riserva
  dichiarata da [ADR-0035](Decision.md#adr-0035) può essere tolta. Lo script
  `tools/failover-replicaset.sh` filtra il log **per questi `id`** e non per il testo dei
  messaggi, secondo la regola 1 di quell'ADR. Registrato in [ADR-0044](Decision.md#adr-0044).
- **Riserve:** una sola elezione osservata riga per riga, su un set a tre membri con priorità
  2/1/1 e senza carico. Il numero di termine (`term`) qui è 13→14 perché il set aveva già subìto
  altre prove: su un set appena creato sarebbe 1→2, e chi confronta i propri log non deve
  aspettarsi lo stesso valore. La sequenza è stata letta sul nodo **eletto**: guardare il log del
  votante fa concludere che l'elezione non lasci quasi traccia, ed è l'errore più facile da
  commettere. Infine non è stata osservata un'elezione *contesa* — due candidati nello stesso
  termine, con un `dry run` che fallisce — che è il caso in cui `21438` e `21444` divergono.
- **Data:** 2026-08-31
- **Usata da:** ADR-0044, ADR-0046

---

<a id="v-031"></a>
### V-031 — La maggioranza persa: il superstite è vivo, è sano, e non scrive più

- **Comandi:** `./tools/failover-replicaset.sh maggioranza` (cioè `make failover-02-maggioranza`)
  · `docker kill` su due membri, il primario lasciato in piedi · `hello()` interrogato in ciclo
  stretto dentro il primario stesso · `rs.conf()`, `rs.status()`, e una scrittura provata a mano
- **Ambiente:** stack `docker/02-replicaset`, `mongo@sha256:b6421f…` (MongoDB 7.0.40), tre membri
  con priorità 2/1/1, macOS 26.6.2 arm64, Docker 29.7.2, Compose v5.4.0. Nessun carico.
  Impostazioni lette da `rs.conf()`, non supposte: `heartbeatIntervalMillis: 2000`,
  `electionTimeoutMillis: 10000`, `heartbeatTimeoutSecs: 10`.
- **Che cosa si voleva sapere:** [V-029](#v-029) e [V-030](#v-030) misurano due scene che
  **finiscono bene** — il set perde il primario e se ne dà un altro. Chi guarda ne ricava che un
  replica set «regge ai guasti», senza mai sentir dire *a quanti*. Il caso che risponde è l'altro:
  due membri su tre fermi. È dichiarato scoperto in [ADR-0043](Decision.md#adr-0043) e in
  [ADR-0044](Decision.md#adr-0044), ed è l'unica scena che spieghi perché i membri sono tre.

- **Esito, primo numero — il primario si retrocede da solo, e ci mette nove secondi.** Sei
  esecuzioni, stesso protocollo: si ferma un secondario (il set non se ne accorge), poi si ferma
  il secondo e si cronometra da lì.

```
9 364 · 9 136 · 9 331 · 9 334 · 9 327 · 9 316  ms      mediana 9 329 ms
```

  Il cronometro gira **dentro il primario**, in una `mongosh` collegata e autenticata prima del
  colpo, che interroga `hello()` ogni 20 ms e si ferma al primo `isWritablePrimary` diverso da
  `true`. È la sua stessa retrocessione: nessun altro nodo può datarla, perché non ne resta
  nessuno.

- **Perché nove e non dieci.** `electionTimeoutMillis` vale 10 000 ms, ma il conto non parte dal
  colpo: parte dall'**ultimo battito ricevuto da una maggioranza**. I battiti vanno ogni
  `heartbeatIntervalMillis` = 2 000 ms ([S-044](#s-044) lo dice a parole: «Replica set members
  send heartbeats (pings) to each other every two seconds»), quindi il colpo cade in un punto
  qualunque di quella finestra e la misura vale fra 8 e 10 secondi. Le sei esecuzioni stanno in
  9,1–9,4 s: coerente, e appunto per questo **il numero non va imparato a memoria**.

- **Esito, la sequenza nel log** (esecuzione del 2026-09-01, `id` sul superstite `mongo-rs-1`):

```
08:28:45.164  id=21216    REPL   Member is now in state DOWN      ← il primo membro fermato
08:28:47.193  id=21216    REPL   Member is now in state DOWN      ← il secondo, 0,4 s dopo il colpo

   ... nove secondi, e id=23974 «Heartbeat failed after max retries» ripetuto ogni 2 s ...

08:28:56.092  id=21809    REPL   Can't see a majority of the set, relinquishing primary
08:28:56.092  id=21475    REPL   Stepping down from primary in response to heartbeat
08:28:56.092  id=21343    REPL   Starting to kill user operations
08:28:56.093  id=21358    REPL   Replica set state transition
08:28:56.094  id=5123007  REPL   Interrupting PrimaryOnlyService due to stepDown
```

  **`id=21809` è la riga che vale la scena**, e dice in inglese esatto quello che si fatica a far
  passare a parole: non «ho perso la connessione», ma «non vedo una maggioranza, quindi **cedo**».
  La forma è la stessa di [V-030](#v-030): la caduta è notata in quattro decimi di secondo, e la
  reazione arriva nove secondi dopo perché è **decisa**, non subita. `id=21343` spiega di
  passaggio perché le connessioni aperte cadono: le operazioni degli utenti vengono interrotte.

- **Esito, che cosa risponde da lì in poi.**

| richiesta | come | risposta |
|---|---|---|
| scrittura | qualunque | `NotWritablePrimary` (code **10107**) — «not primary» |
| lettura | `mongosh --host localhost`, connessione **diretta** | `lab.ordini` → 50 000 documenti |
| lettura | URI con `replicaSet=rs0`, `readPreference` predefinita | `MongoServerSelectionError` |
| lettura | URI con `replicaSet=rs0`, `readPreference=secondaryPreferred` | 50 000 documenti |

  Il superstite si presenta come `isWritablePrimary=false, secondary=true, primary=nessuno`, e
  `rs.status()` lo dà `SECONDARY health=1` con gli altri due «(not reachable/healthy)». La
  differenza fra le due letture non è un capriccio: [S-045](#s-045) documenta che `mongosh`
  aggiunge `directConnection=true` da sé *a meno che* la stringa non contenga `replicaSet`. Con
  la connessione diretta si parla a **quel** nodo e si legge; con l'URI del replica set si chiede
  al driver di trovare un primario, e un primario non c'è. **Chi prova la demo con `mongosh
  --host` conclude che il set funziona ancora.** L'applicazione, no.

- **Esito, il rientro.** Riavviando i due membri fermati, il primario torna dopo 9 207 · 12 348 ·
  12 425 ms: il tempo di far ripartire due `mongod` e di rieleggere. Nessuno lo fa da sé — i
  container sono `exited` dopo un `docker kill` ([V-017](#v-017)) — e il gesto è
  `./tools/reset-demo.sh 02`, che li rialza, aspetta le priorità e ripulisce la collezione di
  scarto lasciata dalla scena.

- **Conseguenza:** la scena entra in `tools/failover-replicaset.sh` come terzo bersaglio e nel
  `Makefile` come `failover-02-maggioranza`; i numeri vanno in `docs/02-architetture/replica-set.md`
  al Task 9. Registrata in [ADR-0045](Decision.md#adr-0045). Il debito dichiarato in
  [ADR-0043](Decision.md#adr-0043) e in [ADR-0044](Decision.md#adr-0044) è saldato.
- **Riserve:** il messaggio d'errore dell'URI di replica set è, alla lettera,
  `MongoServerSelectionError: getaddrinfo ENOTFOUND mongo-rs-2` — un errore di **risoluzione del
  nome**, non di selezione del server. È un artefatto dei container: un container fermo sparisce
  dal DNS della rete Compose, mentre su macchine vere il nome risolverebbe e la connessione
  verrebbe rifiutata, con un testo diverso. Chi riconosce la situazione dal testo dell'errore
  sbaglierà: è la stessa lezione di [ADR-0035](Decision.md#adr-0035), un piano più in là. Poi:
  la finestra 8–10 s è dedotta dai due parametri e corroborata da sei valori che stanno tutti in
  9,1–9,4 s, ma gli estremi non sono stati osservati — un colpo che cadesse subito dopo un battito
  dovrebbe dare ~8 s, e non è capitato. La scena ferma sempre **due secondari**, lasciando in
  piedi il primario; il caso simmetrico — primario più un secondario, con un secondario solo
  superstite — non è cronometrato, perché lì non c'è nessuna retrocessione da datare. Infine
  «ecco perché i membri sono tre e non due» resta un **ragionamento** sulla stessa regola, non una
  misura: un set a due membri non è stato costruito, e la sua maggioranza sarebbe 2, cioè zero
  guasti tollerati in scrittura.
- **Data:** 2026-09-01
- **Usata da:** ADR-0045, ADR-0046

---

<a id="v-032"></a>
### V-032 — Il container lavora, `docker logs` tace: la cattura si congela quando il demone riparte

- **Comandi:** `docker logs <membro>` · `docker inspect --format '{{.State.StartedAt}}'` ·
  `db.adminCommand({ getLog: "global" })` · un container creato apposta come controllo
- **Ambiente:** Docker Desktop 29.7.2 su macOS 26.6.2 arm64. Il demone era stato **fermo tutta la
  notte** — la sessione si è aperta con `Cannot connect to the Docker daemon` — ed è stato
  riavviato la mattina del 2026-09-01. I tre membri dello stack 02 sono tornati su da soli, come
  prescrive `restart: unless-stopped`, e risultavano `healthy`.
- **Che cosa si voleva sapere:** niente. È stata trovata cercando dell'altro, ed è il motivo per
  cui è finita qui: `tools/failover-replicaset.sh` legge il log con `docker logs`, e in queste
  condizioni non avrebbe stampato **niente**, senza dire perché.

- **Esito, il fatto nudo.** Su `mongo-rs-1`, alle 08:12 del 2026-09-01:

```
docker inspect  → StartedAt = 2026-09-01T08:05:55.098Z   RestartCount = 0
docker logs     → 13 944 righe, l'ultima delle quali del 2026-08-31T19:19:50.378
getLog global   → totalLinesWritten = 2 548, righe da 08:08:31.096 a 08:12:03.430
```

  Il container è partito **stamattina**, mongod ha scritto **2 548 righe** da allora, e
  `docker logs` non ne mostra una. Non dà errore: dà silenzio, che è la forma peggiore, perché
  chi legge conclude che l'evento non ha lasciato traccia.

- **Esito, il controllo.** Un container creato in quel momento (`docker run -d alpine …`) è stato
  catturato normalmente. Quindi non è il demone a non catturare: è la cattura dei container
  **preesistenti** al suo riavvio a non ripartire.

- **Esito, e non è nemmeno stabile.** Ricontrollando un'ora dopo, la cattura era ripresa **da
  sola** su due membri su tre, lasciando un buco:

| membro | ultima riga di ieri | prima riga di oggi | buco |
|---|---|---|---|
| `mongo-rs-1` | 2026-08-31T19:19:50.378 | 2026-09-01T08:15:23.610 | 9 min 28 s dall'avvio |
| `mongo-rs-2` | 2026-08-31T19:19:50.378 | 2026-09-01T08:20:01.936 | ripresa dopo un riavvio |
| `mongo-rs-3` | 2026-08-31T19:20:05.557 | *nessuna* | tutta la mattina |

  Le righe del buco non sono ricomparse più: per chi legge `docker logs`, sono perse. Su
  `mongo-rs-3` la cattura è tornata solo dopo che `reset-demo.sh` ne ha ricreato l'esecuzione.
  Nessun campanello: `docker ps` dice `healthy`, `docker inspect` dice `running`, l'healthcheck
  passa. Lo stato del container non racconta niente dello stato del suo log.

- **Conseguenza:** `tools/failover-replicaset.sh` non si fida più. Prima di leggere confronta
  l'ultima riga catturata con l'istante di avvio del container: se il log è più vecchio
  dell'avvio non può essere di quella esecuzione, e le righe si chiedono a **mongod**, che le
  tiene in memoria e non dipende da Docker. Il confronto è coperto da
  `tools/tests/test_failover_log.py`, costruito sugli istanti veri di questa verifica —
  perché un rilevatore la cui condizione di scatto si presenta di rado può rompersi senza che
  nessuno se ne accorga, fino alla sera in cui serve. Registrata in
  [ADR-0045](Decision.md#adr-0045).
- **Riserve:** **la causa non è stata identificata**, e nemmeno il motivo per cui la cattura
  riprende. Un solo riavvio del demone osservato, non provocato apposta e non riprodotto: questa
  voce dice *che succede*, non *quando*. Osservata su Docker Desktop, dove fra il container e il
  file di log c'è una macchina virtuale in più; su un `dockerd` nativo di Linux il meccanismo è
  diverso e non è stato provato. [S-033](#s-033) documenta il driver `json-file` e non nomina
  questo caso — la pagina parla di rotazione e di dimensioni, mai di una cattura che si ferma.
  Infine il ripiego ha un orizzonte suo: `getLog: "global"` è un anello di **1 024 righe**
  (misurato: `totalLinesWritten` 2 548, `log.length` 1 023), quindi su un nodo chiacchierone le
  righe che interessano possono esserne già uscite. Lo stesso vale, dall'altro lato, per il
  `tail -600` con cui si legge `docker logs`: un ciclo d'attesa che riapre una `mongosh` ogni
  mezzo secondo ha prodotto circa 800 righe di `NETWORK` e `ACCESS` in pochi minuti, e ha spinto
  fuori dalla finestra proprio le righe di `REPL` che si cercavano.
- **Data:** 2026-09-01
- **Usata da:** ADR-0045

---

<a id="v-033"></a>
### V-033 — La controprova di V-016: dodicimila scritture confermate, il primario ucciso, zero perse

- **Comandi:** uno scrittore `mongosh` collegato con l'URI del replica set che inserisce documenti
  uno alla volta con `w: "majority"` e stampa l'`_id` **dopo** la conferma del server; a metà corsa
  `docker kill` sul primario; a membro rialzato, si verifica quali dei confermati esistano ancora,
  leggendo con `readConcern: "majority"`
- **Ambiente:** stack `docker/02-replicaset`, MongoDB 7.0.40, tre membri con priorità 2/1/1, macOS
  26.6.2 arm64, Docker 29.7.2. Lo scrittore gira **dentro un membro che non verrà ucciso**, così il
  colpo non porta via anche il cliente. Due esecuzioni da 45 secondi.
- **Che cosa si voleva sapere:** [ADR-0032](Decision.md#adr-0032) rimanda esplicitamente a
  `feature/02` il confronto sulla perdita di dati, e la pagina dell'istanza singola ha un numero che
  fa male: **100 scritture confermate al client e sparite** dopo un `SIGKILL`, con la write concern
  predefinita ([V-016](#v-016)). Il confronto senza il numero gemello è una discussione; con il
  numero gemello è una misura.

- **Esito, il numero gemello.**

| | istanza singola ([V-016](#v-016)) | replica set, `w: "majority"` |
|---|---:|---:|
| scritture confermate al client | 41 558 | 12 901 |
| **confermate e perdute** | **100** | **0** |

  E non è che siano sopravvissute «quasi tutte»: nella collezione ci sono **12 902** documenti e il
  massimo `n` scritto è **12 902**, quindi l'insieme è completo, senza buchi. Prima esecuzione,
  senza istanti nei documenti: 11 937 confermate, 11 937 sopravvissute, zero errori.

- **Esito, che cosa ha visto l'applicazione.** Quasi niente, ed è il secondo risultato. Su 12 902
  tentativi, **un solo errore**:

```
ERR 2698 connection 1 to 172.18.0.3:27017 closed
```

  Poi lo scrittore è ripartito da sé, senza che nessuno lo toccasse. Il prezzo è stato una **pausa**,
  e si vede negli istanti che il client scrive dentro i documenti:

```
n=2697  t=08:49:50.524
n=2698  t=08:49:50.527   ← l'errore, e il colpo: docker kill alle 08:49:50
n=2699  t=08:49:50.669
n=2700  t=08:50:00.824   ← 10 155 ms dopo
```

  **Varco massimo 10 155 ms**; i quattro salti successivi per grandezza sono 142, 132, 99 e 92 ms.
  Un'unica `insertOne` è rimasta appesa dieci secondi dentro il driver e poi è riuscita: è
  l'elezione di [V-029](#v-029) vista dal lato dell'applicazione, che non sa niente di elezioni e si
  limita ad aspettare. Su 45 secondi di corsa, 12 902 scritture: circa **287 al secondo**, con dieci
  secondi buttati in mezzo.

- **Esito, il caso incerto — e vale il resto della voce.** Il documento `n=2698`, quello per cui il
  client ha ricevuto un **errore**, nel database **c'è**. Scritto e mai confermato. È l'immagine
  speculare esatta di [V-016](#v-016): là il client aveva in mano un `acknowledged: true` per dati
  che non esistevano, qui ha in mano un errore per dati che esistono. In tutti e due i casi ciò che
  il client crede non coincide con ciò che il database ha, e la differenza fra i due è che **questo
  si sopravvive** — a patto che la scrittura si possa rifare senza danno. Un'applicazione che
  reagisce a un errore riscrivendo, e la cui riscrittura non è idempotente, qui si fa un duplicato.
- **Conseguenza:** chiude il rimando di [ADR-0032](Decision.md#adr-0032). Il numero va in
  `docs/02-architetture/replica-set.md` accanto al suo gemello, registrato in
  [ADR-0046](Decision.md#adr-0046).
- **Riserve:** **la quasi invisibilità del guasto non è merito della replica, è merito dei
  retryable write**, che nel driver sono attivi per impostazione predefinita: senza di essi
  l'applicazione avrebbe visto una raffica di errori e avrebbe dovuto decidere lei che fare. La
  prova con `retryWrites=false` **non è stata fatta**, e sarebbe la naturale da aggiungere. Poi:
  gli istanti nei documenti li scrive il **client** quando costruisce il documento, cioè all'inizio
  della chiamata — il varco fra due istanti consecutivi è quindi la durata della chiamata in mezzo,
  che è proprio quello che si voleva, ma è un orologio di client e non del server. Due esecuzioni
  sole. In tutte e due è stato ucciso il **primario mentre gli altri due erano sani**, cioè con la
  maggioranza superstite: non dice niente sul caso di [V-031](#v-031), dove le scritture si fermano
  del tutto. E `w: "majority"` qui vuol dire «due container su tre sullo stesso portatile»: la
  garanzia è la stessa che si avrebbe altrove, il costo no ([V-027](#v-027)).
- **Data:** 2026-09-01
- **Usata da:** ADR-0046

---
