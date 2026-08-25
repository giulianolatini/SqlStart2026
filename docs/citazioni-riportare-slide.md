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

**Perché una slide:** due pagine ufficiali correnti che si contraddicono sono il modo più
onesto di spiegare perché in demo si guarda `db.hostInfo()` invece di fidarsi. Il manuale v5.0
archiviato era affermativo: la formulazione è stata **indebolita**, non chiarita.

### La dimensione predefinita della cache, con gli estremi

> «The default WiredTiger internal cache size is the larger of either: 50% of (RAM - 1GB), or
> 0.256 GB.» — e «ensure the RAM does not exceed the bounds of 0.256GB to 10000GB».

Fonte: [S-001](Sources.md#s-001).

**Perché una slide:** il minimo è `0.256 GB`, non `256 MB`, e non è un dettaglio estetico —
sotto quella soglia il valore potrebbe essere rifiutato. Da confermare con la verifica
empirica dello spike prima di portarlo sul palco come numero certo.

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
