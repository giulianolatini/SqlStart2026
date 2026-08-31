# Citazioni da riportare in slide

Sede unica delle citazioni letterali che meritano una slide, raccolte man mano che emergono
durante lo sviluppo. Serve a non perderle: una frase trovata a fine agosto verificando una
fonte è inutile se a settembre nessuno ricorda dove stava.

**Regola d'oro.** Qui entrano solo **citazioni letterali** da fonti verificate. Ogni voce
rimanda alla fonte in [`Sources.md`](Sources.md), dove sono registrati URL, editore, versione
documentata e data di consultazione. Una parafrasi non è una citazione: se la frase esatta non
regge, la voce non entra.

**Come si aggiunge una voce.** Titolo breve, testo originale in inglese fra virgolette
caporali, traduzione o resa italiana solo se serve alla comprensione, riferimento alla fonte,
e una riga su *perché* vale una slide. Se la citazione smentisce un'assunzione comune, dirlo:
è quello il motivo per cui il pubblico se la ricorderà.

---

## Blocco 0 — La versione, che si dice prima di tutto il resto

### Il lab gira su MongoDB 7.0, e va detto dal palco

**Promemoria del relatore, 2026-08-25:** «Sulle architetture del talk 7.0 e 8.0 non
differiscono; va detto dal palco, non lasciato scoprire dal prompt di `mongosh`.»

È l'unica voce di questo file che non nasce da una fonte esterna: è una decisione di regia,
registrata qui perché è in slide che deve finire. La ragione tecnica sta in
[ADR-0028](Decision.md#adr-0028) — sul kernel della VM di Docker Desktop nessuna MongoDB 8
pubblicata si avvia.

**Attenzione, la frase va detta nella forma esatta.** La verifica contro le note di
compatibilità della 8.0 le ha tolto l'assoluto: «non differiscono» regge su replica set,
sharding, `mongodump` e `mongorestore` — termini che in quella pagina non compaiono affatto —
ma **due differenze esistono**, ed entrambe toccano proprio ciò che si mostra. Sono le due
citazioni qui sotto. Sulla slide vale la versione circostanziata: *su ciò che vedete oggi, 7.0
e 8.0 si comportano allo stesso modo, con due eccezioni che vi dico subito.* Promettere
identità piena è una promessa che il manuale smentisce in due righe.

### Dalla 8.0 non ci si collega più direttamente a uno shard

> «Starting in MongoDB 8.0, you can only run certain commands on nodes in sharded clusters. If
> you attempt to connect directly to a node and run an unsupported command, MongoDB returns an
> error: *"You are connecting to a sharded cluster improperly by connecting directly to a
> shard. Please connect to the cluster via a router (mongos)."*»

> «To run a non-supported database command directly against a node in a sharded cluster, you
> must either connect to `mongos` or have the maintenance-only `directShardOperations` role.»

Fonte: [S-029](Sources.md#s-029) — MongoDB Manual, Compatibility Changes in MongoDB 8.0,
sezione *Backward-Incompatible Features*.

**Perché una slide:** è la differenza che il pubblico può toccare. Nello spike ci si è
collegati direttamente a uno shard per leggere `hostInfo`, ed è servito
[V-006](Sources.md#v-006): su 8.0 quella stessa mossa sarebbe stata respinta. Chi torna a casa
e rifà la demo su una 8 incontra l'errore, quindi va anticipato. Nota il dettaglio che quasi
tutti perdono: il vincolo scatta «once the cluster has more than one shard» — con un solo
shard la connessione diretta resta ammessa, perché serve alla transizione da replica set a
cluster.

### Dalla 8.0 `majority` conferma sulla scrittura, non sull'applicazione

> «Starting in MongoDB 8.0, write operations that use the `"majority"` write concern return an
> acknowledgment when the majority of replica set members have **written the oplog entry** for
> the change. This improves the performance of `"majority"` writes. In previous releases, these
> operations would wait and return an acknowledgment after the majority of replica set members
> **applied** the change.»

Fonte: [S-029](Sources.md#s-029).

**Perché una slide:** scritto contro applicato è una distinzione da mezza riga che cambia i
numeri, e i numeri sono ciò che l'applicazione del talk cronometra durante il failover. Se
qualcuno in sala confronta le proprie latenze con quelle proiettate, è qui la spiegazione della
differenza — non nell'hardware.

### La 8.0 è la versione che ha cambiato allocatore

> «Starting in MongoDB 8.0, MongoDB uses an upgraded version of TCMalloc that uses **per-CPU
> caches, instead of per-thread caches**, to reduce memory fragmentation and make your database
> more resilient to high-stress workloads.»

Fonte: [S-029](Sources.md#s-029).

**Perché una slide:** chiude il cerchio sulla trappola del kernel. La cache per-CPU è il
meccanismo che dal kernel 6.19 in poi non è più tollerato, ed è entrato **con la 8.0**: la 7.0
non aggira il problema per fortuna, lo precede per costruzione. Vale come esempio di come si
indaga un blocco — la causa stava nelle note di compatibilità, non nel messaggio d'errore, che
rimandava a due ticket Jira di cui uno chiuso «Gone away».

---

## Blocco 1 — Standalone e fondamenta in Docker

### La cache WiredTiger va impostata a mano nei container

> «If you run `mongod` in a container (for example, `lxc`, `cgroups`, Docker, etc.) that does
> *not* have access to all of the RAM available in a system, you **must** set
> `--wiredTigerCacheSizeGB` or `--wiredTigerCacheSizePct` to a value less than the amount of
> RAM available in the container.»

Fonte: [S-001](Sources.md#s-001) — MongoDB Manual, WiredTiger Storage Engine, 8.3.

**Perché una slide:** è un `must` esplicito del produttore, non una raccomandazione di
buon senso. Chiude in anticipo la domanda «ma non se ne accorge da solo?».

### La documentazione MongoDB si contraddice sul rilevamento del limite del container

> «WiredTiger **may not** account for the memory limits of the specific container in certain
> cases.» — WiredTiger Storage Engine

> «This memory limit, rather than the total system memory, is used as the maximum RAM
> available to calculate WiredTiger internal cache.» — `hostInfo`

Fonti: [S-001](Sources.md#s-001) e [S-026](Sources.md#s-026), stesso manuale, stessa versione 8.3.

**Perché una slide, e come è finita.** La contraddizione era **apparente**, e va portata sul
palco così: prima le due frasi, poi la misura che le riconcilia. Le due pagine parlano di campi
diversi. `hostInfo.system.memSizeMB` riporta la memoria della macchina — 11.946 MiB, la VM —
mentre `hostInfo.system.memLimitMB` riporta il `mem_limit` del container. È il secondo a
guidare la cache, misurato su sei configurazioni [V-009](Sources.md#v-009): il rilevamento
automatico **funziona**.

Resta il fatto che le due pagine, lette di seguito, dicono cose opposte, e resta la
prescrizione di impostare la cache a mano — ma per renderla leggibile nel file Compose, non
perché mongod non sappia leggerla. La slide vale ancora, con la conclusione capovolta: non
«fidarsi è pericoloso», ma «leggere due pagine non basta, si guarda `db.hostInfo()` e si
smette di discutere». Nota storica che regge: il manuale v5.0 archiviato era affermativo, e la
formulazione è stata **indebolita**, non chiarita.

Il rischio vero è altrove, e la misura l'ha trovato: una cache **maggiore** del `mem_limit`
viene accettata senza un solo avviso. Vedi
[gestione delle risorse in Compose](06-sviluppo/gestione-risorse-compose.md).

### La dimensione predefinita della cache, con gli estremi

> «The default WiredTiger internal cache size is the larger of either: 50% of (RAM - 1GB), or
> 0.256 GB.» — e «ensure the RAM does not exceed the bounds of 0.256GB to 10000GB».

Fonte: [S-001](Sources.md#s-001).

**Perché una slide:** perché la cifra sulla slide sarebbe stata **sbagliata**, e la verifica
l'ha presa in tempo. La formula è confermata su sei misure [V-009](Sources.md#v-009), ma il
minimo dichiarato non è quello vero, e le unità non sono quelle scritte.

> `storage.wiredTiger.engineConfig.cacheSizeGB must be greater than or equal to **0.25**`

Fonte: il binario stesso, MongoDB 7.0.40, che rifiuta l'avvio con `0.1`
[V-009](Sources.md#v-009).

Il minimo imposto è `0.25`, non `0.256`. E `0.25` configura `268435456` byte, cioè
**esattamente 256 MiB**: l'opzione si chiama `cacheSizeGB` ma è letta in **GiB**. Il `0.256`
del manuale, preso alla lettera, produce 262 MiB — un valore che non corrisponde a nulla, né
alla formula né al pavimento. La riserva registrata qui il 2026-08-25 chiedeva la verifica
empirica prima del palco: è arrivata, e ha smentito la fonte. **Questa è la slide**, più della
formula: una cifra ufficiale, un binario che dice altro, e la differenza fra citare e provare.

### Le variabili di inizializzazione non fanno nulla su un volume già popolato

> «Do note that none of the variables below will have any effect if you start the container
> with a data directory that already contains a database.»

Fonte: [S-009](Sources.md#s-009) — Docker Hub, immagine ufficiale `mongo`.

**Perché una slide:** è la spiegazione della domanda più frequente di chiunque abbia provato
MongoDB in Docker — «ho cambiato la password nel Compose e non funziona». Vale anche come
avvertenza operativa a noi: fra una prova e l'altra i volumi vanno azzerati, altrimenti la
demo parte con lo stato della prova precedente.

---

## Blocco 2 — Replica set, failover, sicurezza

### MongoDB documenta la trappola dei replica set in Docker

> «When a replica set runs in Docker, it might expose only one MongoDB endpoint. In this case,
> the replica set is not discoverable, and specifying `directConnection=false` can prevent
> your application from connecting to it. In a test or development environment, you can
> connect to the replica set by specifying `directConnection=true` in your connection URI. In
> a production environment, we recommend configuring the cluster to make each MongoDB instance
> accessible outside of the Docker virtual network.»

Fonte: [S-007](Sources.md#s-007) — MongoDB Manual, Connection String Options, 8.3.

**Perché una slide:** è la nostra trappola, descritta da MongoDB con parole sue. Vale più di
qualsiasi spiegazione: il pubblico vede che non è un'idiosincrasia del lab ma un caso noto e
documentato.

### I nomi host sono nella configurazione, e dalla 5.0 gli IP nudi non partono

> «Starting in MongoDB 5.0, nodes that are only configured with an IP address fail startup
> validation and do not start.»

> «Always use resolvable hostnames for the value of the `members[n].host` field in the replica
> set configuration to avoid confusion and complexity.»

Fonte: [S-020](Sources.md#s-020) — MongoDB Manual, Change Hostnames in a Self-Managed Replica Set, 8.3.

**Perché una slide:** vincolo duro e versionato. Spiega in una riga perché nel nostro
`rs.initiate()` non compare un solo indirizzo IP, e perché chi ci prova a casa vede i nodi
non avviarsi.

### Il keyfile è per test e sviluppo, non per la produzione

> «Use keyfiles only for testing and development environments because of their limited
> manageability and cryptographic strength. For production environments, use X.509
> certificates.»

Fonte: [S-005](Sources.md#s-005) — MongoDB Manual, Deploy Self-Managed Replica Set With Keyfile Authentication, 8.3.

**Perché una slide:** dirlo prima che lo chieda il pubblico. Il lab usa il keyfile perché è
l'autenticazione interna minima che rende dimostrabile il replica set, non perché sia la
scelta giusta in produzione. La trattazione estesa di keyfile contro X.509 va nella
documentazione di amministrazione, non liquidata in una battuta.

### Il perimetro esatto dell'eccezione localhost

> «On a `mongod` instance, the localhost exception only applies when there are **no users or
> roles** created in the MongoDB instance.»

> «In a sharded cluster, the localhost exception applies to each shard individually as well as
> to the cluster as a whole.»

Fonte: [S-006](Sources.md#s-006) — MongoDB Manual, Localhost Exception, 8.3.

**Perché una slide:** quasi tutti ricordano «finché non crei il primo utente». La condizione
vera è più stretta — vale anche per i **ruoli** — ed è esattamente il tipo di precisione che
distingue una spiegazione verificata da una ripetuta a memoria.

### L'immagine ufficiale smonta il replica set per creare l'utente root

> `# remove "--auth" and "--replSet" for our initial startup`

Fonte: [S-022](Sources.md#s-022) — `docker-library/mongo`, `8.0/docker-entrypoint.sh`, commit `7c24b37`.

**Perché una slide:** è **codice sorgente, non documentazione** — e va detto sul palco. Il
README ufficiale non nomina mai `--replSet` né `--keyFile`. Il mongod di inizializzazione
parte standalone e senza autenticazione, e `rs.initiate()` non lo esegue nessuno al posto
nostro. Comportamento controintuitivo, condizionale e non documentato: sapere dove sta scritto
vale più che saperlo e basta.

---

## Blocco 3 — Sharded cluster

### Shard e config server devono essere replica set

> «Each shard contains a subset of the sharded data. **Each shard must be deployed as a
> replica set.**»

> «Config servers store metadata and configuration settings for the cluster. **Config servers
> must be deployed as a replica set (CSRS).**»

Fonte: [S-008](Sources.md#s-008) — MongoDB Manual, Sharded Cluster Components, 8.3.

**Perché una slide:** è la ragione per cui uno sharded cluster minimo ha comunque tanti
container. Non è una scelta del lab: è un `must` della documentazione.

### Ma per i test un replica set a un solo membro è esplicitamente ammesso

> «For a production deployment, deploy a config server replica set with at least three
> members. **For testing purposes, you can create a single-member replica set.**»

> «For a production deployment, use a replica set with at least three members. **For testing
> purposes, you can create a single-member replica set.**»

Fonte: [S-024](Sources.md#s-024) — MongoDB Manual, Deploy a Self-Managed Sharded Cluster, 8.3.

**Perché una slide:** è la difesa del profilo `palco`. Detta due volte da MongoDB, una per i
config server e una per gli shard. Attenzione: la citazione **non** sta sulla pagina dei
componenti, dove istintivamente si andrebbe a cercarla.

### Nessun arbitro nei config server

> «Must have zero arbiters. / Must have no delayed members. / Must build indexes (i.e. no
> member should have `members[n].buildIndexes` setting set to false).»

> «The config server replica set must not use the same name as any of the shard replica sets.»

Fonte: [S-025](Sources.md#s-025) — MongoDB Manual, Config Servers, 8.3.

**Perché una slide:** risposta pronta a «non si può mettere un arbitro per risparmiare RAM?».
No, ed è scritto.

---

## Backup e restore

### `--oplog` non funziona su uno sharded cluster

> «You can't run `mongodump` with `--oplog` on a sharded cluster.»

> «`--oplog` only works against nodes that maintain an oplog. This includes all members of a
> replica set.»

Fonte: [S-011](Sources.md#s-011) — MongoDB Database Tools, `mongodump`.

**Perché una slide:** delimita la demo di backup a caldo. Spiega perché avviene sul replica
set e non sullo sharded, prima che qualcuno lo interpreti come una svista.

### Senza `--oplog` il dump non è coerente a un istante

> «Without `--oplog`, if there are write operations during the dump operation, the dump will
> not reflect a single moment in time.»

Fonte: [S-011](Sources.md#s-011).

**Perché una slide:** è il cuore della differenza fra copiare i file e fare un backup. Da
segnalare con onestà: le espressioni «point in time» e «does not guarantee» **non** compaiono
nella documentazione, e il caso dello standalone — dove `--oplog` non è nemmeno utilizzabile —
non è trattato esplicitamente.

---

## Docker e Compose

### `latest` viene scaricato comunque

> «The `latest` tag is always pulled even when the `missing` pull policy is used.»

Fonte: [S-019](Sources.md#s-019) — Docker Docs, `docker compose up` e riferimento dei servizi.

**Perché una slide:** una sola riga che giustifica il pinning. Chi usa `latest` credendo di
lavorare offline scoprirà il contrario in sala.

### L'unico meccanismo documentato per non contattare il registry

> «`never`: Compose doesn't pull the image from a registry and relies on the platform cached
> image. If there is no cached image, a failure is reported.»

Fonte: [S-019](Sources.md#s-019).

**Perché una slide:** il digest garantisce *quale* immagine, non *se* si va in rete. Nessuna
pagina Docker afferma che un'immagine pinnata a digest e già in cache eviti il registry: la
garanzia offline poggia su `pull_policy`, non sul digest.

### `mem_limit` e `deploy` non sono alternative

> «When set, `mem_limit` must be consistent with the `limits.memory` attribute in the Deploy
> Specification.»

Fonte: [S-003](Sources.md#s-003) — Docker Docs, Define services in Docker Compose.

**Perché una slide:** smonta la narrazione corrente, che le presenta come due strade fra cui
scegliere. La documentazione chiede coerenza, non alternativa. E la frase storica «ignored by
`docker-compose up`» **non esiste più**: apparteneva al riferimento v3, ritirato.

### La forma breve di `depends_on` non aspetta nulla

> «With short syntax, Compose does not wait for dependency services to be "healthy" before
> starting a dependent service.»

> «Compose waits for healthchecks to pass on dependencies marked with `service_healthy`.»

Fonte: [S-012](Sources.md#s-012) — Docker Docs, `depends_on`.

**Perché una slide:** due frasi affiancate spiegano l'intera differenza fra un lab che parte e
uno che parte a volte. È l'unica fonte Docker che la verifica ha confermato senza riserve.

### `version:` è obsoleto, non deprecato

> «The top-level `version` property is defined by the Compose Specification for backward
> compatibility. It is only informative and you'll receive a warning message that it is
> obsolete if used.»

Fonte: [S-016](Sources.md#s-016) — Docker Docs, Version and name top-level elements.

**Perché una slide:** la parola esatta è **obsolete**, e il comportamento è «only informative»
più un avviso — non «ignored». Se in slide si scrive «deprecato e ignorato», la citazione non
regge alla verifica.

### Il riferimento che diceva «ignorato fuori da Swarm» non è più mantenuto

> «The legacy versions of the Compose file reference has moved to the V1 branch of the Compose
> repository. They are no longer being actively maintained.»

Fonte: [S-004](Sources.md#s-004) — Docker Docs, Compose Deploy Specification.

**Perché una slide:** è l'origine di una convinzione diffusissima. La frase secondo cui gli
attributi sotto `deploy` sarebbero ignorati fuori da Swarm stava nel riferimento del formato
v3, oggi ritirato. Nella documentazione attuale «Swarm», «ignored» e «not supported» hanno
zero occorrenze nel corpo della pagina: non è che la risposta sia cambiata, è che la domanda
non ha più una risposta scritta. Da qui la scelta di dimostrarlo con `docker inspect`.

### I servizi senza `profiles` sono sempre attivi

> «Services without a `profiles` attribute are always enabled.»

Fonte: [S-015](Sources.md#s-015) — Docker Docs, Using profiles with Compose.

**Perché una slide:** una riga che chiude il dubbio ricorrente su cosa parta quando si usa un
profilo. È la regola su cui poggia la distinzione fra il profilo di palco e quello completo
dello stack sharded.

### Il gesto con cui tutti simulano un guasto non simula un guasto

> «If you manually stop a container, the restart policy is ignored until the Docker daemon
> restarts or the container is manually restarted. This prevents a restart loop.»

Fonte: [S-039](Sources.md#s-039) — Docker Docs, politiche di riavvio.

E la pagina di `docker kill` dice soltanto questo:

> «The `docker kill` subcommand kills one or more containers. The main process inside the
> container is sent `SIGKILL` signal (default)»

Fonte: [S-040](Sources.md#s-040) — Docker Docs, `docker kill`.

**Perché una slide:** la parola «restart» non compare da nessuna parte nella pagina di
`docker kill`. Per il demone quel comando è una fermata voluta da un umano; per chi guarda lo
schermo è un crash. Misurato: con `restart: unless-stopped` in vigore, `docker kill -s KILL`
lascia il container `exited` e `RestartCount` a **zero**, mentre lo stesso container riparte da
solo con `RestartCount=1` se `mongod` termina da sé ([V-017](Sources.md#v-017)). Regge il
Blocco 2 meglio di qualunque diagramma sulle politiche di riavvio
([ADR-0034](Decision.md#adr-0034)).

### Dentro il container, `kill -9 1` non fa niente e dice che è andato bene

> «Only signals for which the "init" process has established a signal handler can be sent to
> the "init" process by other members of the PID namespace. This restriction applies even to
> privileged processes, and prevents other members of the PID namespace from accidentally
> killing the "init" process.»

> «`SIGKILL` or `SIGSTOP` are treated exceptionally: these signals are forcibly delivered when
> sent from an ancestor PID namespace.»

Fonte: [S-041](Sources.md#s-041) — `pid_namespaces(7)`, manuale Linux.

**Perché una slide:** due frasi che spiegano perché lo stesso segnale funziona da fuori e non
da dentro. `SIGKILL` non è gestibile per definizione, quindi dall'interno del namespace non
raggiunge PID 1 — e il comando ritorna successo senza aver fatto niente. Il demone Docker sta
invece nel namespace antenato, e passa. Chi entra nel container per «uccidere `mongod`» si
convince di averlo fatto.

---

## Installazione su una macchina vera

### MongoDB non è supportato su WSL

> «MongoDB is not supported on Windows Subsystem for Linux (WSL). To run MongoDB on Linux, use
> a supported Linux system.»

Fonte: [S-049](Sources.md#s-049) — MongoDB Manual, Install on Windows.

**Perché una slide:** non è un'avvertenza sulle prestazioni, è un'esclusione dal supporto, e
smentisce la scorciatoia più diffusa fra chi sviluppa su Windows. Le due strade sostenute
restano una macchina virtuale vera oppure un container.

### Su Windows la shell va installata a parte

> «The MongoDB Shell (`mongosh`) is not installed with MongoDB Server. You need to follow the
> `mongosh` installation instructions to download and install `mongosh` separately.»

> «The `.msi` installer does not include `mongosh`.»

Fonte: [S-049](Sources.md#s-049).

**Perché una slide:** la documentazione lo dice due volte nella stessa pagina, il che è già una
misura di quante volte è stato chiesto. Su Ubuntu il pacchetto `mongodb-org` si porta dietro
`mongodb-mongosh`; su Windows, finita l'installazione, la macchina non ha ancora un modo per
parlare con il database.

### I permessi del keyfile, su Windows, non vengono controllati

> «On UNIX systems, the keyfile must not have group or world permissions. On Windows systems,
> keyfile permissions are not checked.»

Fonte: [S-005](Sources.md#s-005) — MongoDB Manual, autenticazione con keyfile.

**Perché una slide:** un controllo che su un sistema impedisce l'avvio e sull'altro non esiste.
Su Linux un keyfile con i permessi sbagliati blocca `mongod`; su Windows non produce nessun
errore, nessun avviso e nessuna riga di log — e chi riesce a leggere quel file si autentica
come membro del replica set. È la rete di sicurezza che una procedura portata da Linux a
Windows perde senza che nessuno lo segnali.

### Ogni connessione costa due descrittori, non uno

> «Incoming connections to a `mongod` or `mongos` instance require two file descriptors.»

Fonte: [S-052](Sources.md#s-052) — MongoDB Manual, impostazioni `ulimit` su UNIX.

**Perché una slide:** il numero da reggere non è quello delle connessioni, è il doppio. Serve
esattamente nella demo di carico, quando il pubblico vede salire le connessioni concorrenti e
si chiede dove sia il limite.
---

## Applicazione Python

### I callback di pymongo bloccano chi li chiama

> «Events are delivered synchronously. Application threads block waiting for event handlers
> (e.g. `started()`) to return. Care must be taken to ensure that your event handlers are
> efficient enough to not adversely affect overall application performance.»

Fonte: [S-010](Sources.md#s-010) — PyMongo 4.17.0, `monitoring`.

**Perché una slide:** è il motivo per cui il listener non disegna nulla e si limita a
depositare un evento in coda. Un handler lento non rallenta la grafica: rallenta il driver, e
falsa proprio le misure di failover che la demo sta cronometrando.

---

## Repository e distribuzione

### I limiti di GitHub sui file grandi

> «If you attempt to add or update a file that is larger than 50 MiB, you will receive a
> warning from Git.»

> «GitHub blocks files larger than 100 MiB. To track files beyond this limit, you must use Git
> Large File Storage (Git LFS).»

> «We recommend repositories remain small, ideally less than 1 GB, and less than 5 GB is
> strongly recommended.»

Fonte: [S-021](Sources.md#s-021) — GitHub Docs, About large files on GitHub.

**Perché una slide:** giustifica in tre numeri la scelta di tenere i filmati fuori dal
repository. Le unità sono **MiB**, non MB: vedi i [limiti noti](00-progetto/limiti-noti.md).
