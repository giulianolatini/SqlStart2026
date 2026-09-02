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

### L'eccezione si chiama «localhost» e la fonte non definisce «localhost»

> «The localhost exception allows you to create the first user or role in the system after
> enabling access control. You can also use it to initiate a replica set.»

> «You must wait until the replica set elects a primary before you can add the first user.»

Fonte: [S-055](Sources.md#s-055) — MongoDB Manual v7.0, Localhost Exception. Misura in
[V-023](Sources.md#v-023).

**Perché una slide:** perché quello che la pagina **non** dice pesa quanto quello che dice. Le
stringhe `127.0.0.1`, `::1`, «loopback» e «same host» non compaiono da nessuna parte, né sulla v7.0
né sulla 8.3; la formulazione più vicina è «connect to the localhost interface», che nomina
un'interfaccia senza dire quale sia. Eppure il vincolo esiste: un sidecar sulla rete Compose si
prende `Command replSetInitiate requires authentication`. È il caso più pulito del talk di una
regola che il prodotto applica e la documentazione non scrive — e la diapositiva può mostrare
insieme la pagina e il messaggio d'errore.

### Se il problema è l'indirizzo di provenienza, si cambia l'indirizzo di provenienza

> ```
> NAMESPACE_CONDIVISO_OK {"ok":1}
> UTENTE_CREATO da sidecar in namespace condiviso
> CHIUSA_DOPO_IL_PRIMO_UTENTE codeName=Unauthorized code=13
> ```

Fonte: [V-023](Sources.md#v-023) — misura del 2026-08-31, decisione in
[ADR-0040](Decision.md#adr-0040).

**Perché una slide:** tre righe raccontano l'eccezione localhost per intero — si apre, concede
`replSetInitiate` e `createUser`, si richiude — e insieme mostrano il trucco che le fa da cornice:
un container avviato con `network_mode: "service:mongo-rs-1"` non ha un'interfaccia di rete propria,
usa quella del membro, e il suo `localhost` è il `localhost` del `mongod`. È il momento in cui la
platea capisce che «localhost» in Docker è una proprietà del namespace, non della macchina.

### Tre membri, maggioranza due: un guasto tollerato, e al secondo il set cede da solo

> ```text
> 08:28:47.193  id=21216    Member is now in state DOWN    ← il secondo, 0,4 s dopo il colpo
>
>      ... nove secondi, e «Heartbeat failed after max retries» ogni due ...
>
> 08:28:56.092  id=21809    Can't see a majority of the set, relinquishing primary
> 08:28:56.092  id=21475    Stepping down from primary in response to heartbeat
> ```

Fonte: [V-031](Sources.md#v-031) — sei esecuzioni sullo stack `02-replicaset`, log del superstite,
mediana 9 329 ms. Decisione in [ADR-0045](Decision.md#adr-0045).

**Perché una slide:** perché è l'unica che risponde alla domanda che le scene di failover lasciano
aperta. Quelle finiscono bene — cade un membro, il set se ne dà un altro — e chi guarda ne ricava
che un replica set «regge ai guasti», senza sentirsi mai dire *a quanti*. La risposta è una
sottrazione: la maggioranza di tre è due, quindi si tollera **uno**. Con due membri la maggioranza
sarebbe ancora due, cioè **zero** guasti tollerati in scrittura: ecco perché i membri sono tre, e
non è una questione di prestazioni né di copie dei dati.

Al secondo guasto non succede niente di drammatico da vedere, ed è questo che va detto: il
superstite è **vivo, sano, raggiungibile e con tutti i dati**, e smette di scrivere lo stesso.
Il verbo del log è `relinquishing`, cedere — non «ho perso la connessione», ma «non vedo una
maggioranza, quindi mi tolgo». È una decisione, non un guasto, e ha la stessa forma dei dieci
secondi dell'elezione (vedi «L'elezione dura sei millisecondi», più sotto): il set si accorge in
quattro decimi di secondo e **aspetta apposta** i nove che seguono.

La coda cattiva sta nella prova: da `mongosh --host` quel nodo restituisce ancora tutti e 50 000 i
documenti, perché una connessione diretta parla a lui e non cerca un primario
([S-045](Sources.md#s-045)). Chi verifica la demo così conclude che il set funziona. Le scritture
rispondono `NotWritablePrimary`, e l'applicazione, che usa l'URI del replica set, non trova nessun
server a cui parlare.

---

### Cento contro zero, misurato sulla stessa prova

> | | istanza singola, `w: 1` | replica set, `w: "majority"` |
> |---|---:|---:|
> | scritture confermate all'applicazione | 41 558 | 12 901 |
> | **confermate e perdute** | **100** | **0** |

Fonte: [V-016](Sources.md#v-016) e [V-033](Sources.md#v-033) — stesso gesto, `docker kill` sul
processo che scrive, sulle due architetture. Decisione in [ADR-0046](Decision.md#adr-0046).

**Perché una slide:** perché è il numero che l'alta disponibilità di solito non porta. Si parla di
failover in secondi, che è la parte visibile, e quasi mai di quante scritture già confermate
all'applicazione svaniscono nel frattempo — che è la parte che finisce in un ticket sei mesi dopo.
Cento è un numero piccolo e concreto: sta in una riga, e chi lo sente pensa subito ai propri cento.

Ma la slide va detta intera, perché la metà scomoda è la lezione vera. Nel caso a destra
l'applicazione **un errore l'ha visto**: uno, per il documento `n=2698` — che nel database **c'è**.
Scritto, e mai confermato. La bugia non sparisce, **cambia verso**: sull'istanza singola il client
crede di avere dati che non ha, sul replica set crede di non avere dati che ha. Il secondo caso si
sopravvive, a una condizione da dire ad alta voce: che la scrittura si possa rifare senza danno.

E una precisazione di onestà, perché la scena sembra più bella di com'è: quasi tutta l'invisibilità
del guasto la fanno i **retryable write**, attivi per impostazione predefinita nel driver, che hanno
tenuto appesa una `insertOne` per dieci secondi invece di farla fallire. La replica ha salvato i
dati; il driver ha salvato la faccia all'applicazione. Sono due cose diverse, e vale la pena non
attribuirle alla stessa.

### Nel comando non c'è `--auth`, e senza credenziali non passa niente

> ```text
> ["mongod","--replSet","rs0","--keyFile","/keyfile/mongo-keyfile",
>  "--bind_ip_all","--wiredTigerCacheSizeGB","0.25"]
> ```
>
> ```text
> hello()                            -> OK: setName=rs0 primary=mongo-rs-1:27017
> admin.system.users.countDocuments  -> Unauthorized: requires authentication
> replSetGetStatus                   -> Unauthorized: requires authentication
> lab.ordini.countDocuments          -> Unauthorized: requires authentication
> createUser                         -> Unauthorized: requires authentication
> ```

Fonte: [V-038](Sources.md#v-038); dichiarato da [S-002](Sources.md#s-002) — «`--keyFile` implies
`--auth`» — e da [S-005](Sources.md#s-005). Decisione in [ADR-0048](Decision.md#adr-0048).

**Perché una slide:** perché la platea legge il comando e cerca `--auth`, e non lo trova. Il
keyfile non è solo autenticazione **fra** i membri: attiva anche quella dei client, e nessuno lo ha
chiesto. La riga da dire mentre la seconda schermata è a video è che passa **una cosa sola**,
`hello()`, perché altrimenti un driver non saprebbe nemmeno a chi presentare le credenziali. Ed è
anche la spiegazione del paradosso che rende complicata l'inizializzazione: prima di un utente
nessuno può inizializzare la replica, e senza replica non si crea un utente.

### La migrazione a X.509 non comincia da X.509

> ```text
> mongod --clusterAuthMode x509         BadValue: need to enable TLS via the tlsMode flag
> mongod --clusterAuthMode sendX509     BadValue: need to enable TLS via the tlsMode flag
> mongod --clusterAuthMode sendKeyFile  BadValue: need to enable TLS via the tlsMode flag
> uscita = 1
> ```

Fonte: [V-039](Sources.md#v-039), sull'immagine pinnata. La procedura è
[S-062](Sources.md#s-062). Decisione in [ADR-0048](Decision.md#adr-0048).

**Perché una slide:** perché ribalta la stima dei tempi. `sendKeyFile` è il modo *di transizione*,
quello che continua a mandare il keyfile e serve solo a non fermare il cluster — e non parte se il
TLS non c'è. Quindi il primo passo della migrazione non riguarda i certificati di membro: riguarda
TLS, cioè **tutti i client**, cioè persone che non lavorano nel gruppo che amministra il database.
Da dire subito dopo: la scala è a senso unico, `Illegal state transition` in tutte e due le
direzioni, e chi sbaglia tappa riavvia il nodo invece di annullare il comando.

### Un utente locale a un nodo non esiste, e MongoDB lo dice a chiare lettere

> ```text
> createUser su un secondario   -> NotWritablePrimary: not primary
> createUser sul database local -> BadValue: Cannot create users in the local database
> ```
>
> ```text
> mongo-rs-1  utenti=2  admin.admin  admin.lettore-demo
> mongo-rs-2  utenti=2  admin.admin  admin.lettore-demo
> mongo-rs-3  utenti=2  admin.admin  admin.lettore-demo
> ```

Fonte: [V-038](Sources.md#v-038). Decisione in [ADR-0048](Decision.md#adr-0048).

**Perché una slide:** perché la domanda «devo creare l'utente su tutti e tre?» arriva sempre, e la
risposta migliore non è «no, si replica»: è il secondo messaggio d'errore. L'unico database che non
viene replicato è `local`, ed è precisamente l'unico in cui non si possono mettere utenti. Il posto
dove un utente «solo di questo nodo» potrebbe vivere è l'unico posto che gli è vietato.

Terza riga, se c'è tempo: `__system`, l'identità con cui i membri parlano fra loro, **non è un
documento** — non sta in nessuna collezione, sta nel keyfile. È il motivo per cui perdere il
keyfile non è come perdere una password: non c'è niente da riscrivere, c'è un file da
ridistribuire ovunque.

---

### Il primario si dimette in otto millisecondi, e undici secondi dopo si riprende il posto

> | come lo si toglie | quanto ci mette il set a darsi un primario |
> |---|---:|
> | `rs.stepDown()` | **8 ms** · 101 ms · 87 ms |
> | `db.shutdownServer()` | ~500 ms |
> | `docker kill` | ~10 000 ms |
>
> ```text
> … e poi, da solo, senza che nessuno tocchi niente:
> mongo-rs-1 (priorità 2) torna primario dopo  11 308 · 11 293 · 11 021 ms
> ```

Fonte: [V-042](Sources.md#v-042) — tre `rs.stepDown()` cronometrati sullo stack `02-replicaset`,
con l'osservatore su un terzo nodo. Gli altri due tempi sono [V-029](Sources.md#v-029). Decisione
in [ADR-0049](Decision.md#adr-0049).

**Perché una slide:** perché completa la scala che le altre due misure lasciano a metà, e lo fa nel
verso che sorprende. Il gesto brutale è il **più lento** — dieci secondi — e il gesto educato è
mille volte più veloce, perché chi si dimette **avvisa**, e non c'è nessun timeout da far scadere.
Detto in una riga: la velocità di un failover non dipende da quanto è potente il cluster, dipende
da quanto è stato educato chi se n'è andato.

La seconda riga della slide è quella che serve a chi la demo la deve *fare*. Nel lab `mongo-rs-1`
ha priorità 2, quindi dopo undici secondi si riprende il posto **da solo**. È comodo — la scena si
ripulisce, lo stack non resta storto per le prove successive — ed è una trappola da palco: chi
proietta `rs.status()` e comincia a spiegare che «adesso il primario è mongo-rs-2» ha una decina di
secondi prima che lo schermo lo smentisca. Se la spiegazione è lunga, il gesto giusto è
`docker stop`, che non si annulla da sé.

---

### Tre modi di diventare primario, e solo la prima riga del log li distingue

> ```text
> id=4615652  «since we've seen no PRIMARY in election timeout period»  → è un GUASTO
> id=4615661  «due to step up request»                                  → è MANUTENZIONE
> id=4615660  «for a priority takeover»                                 → è la CONFIGURAZIONE
>
> id=21450    «Election succeeded, assuming primary role»               → identica in tutti e tre
> ```

Fonte: [V-044](Sources.md#v-044) — log di tre elezioni vere sullo stack `02-replicaset`. Decisione
in [ADR-0049](Decision.md#adr-0049).

**Perché una slide:** perché è la risposta alla domanda che si fa il lunedì mattina guardando un
log, e perché questo repository ci aveva sbagliato. In `docs/03-amministrazione/log.md` stava
scritto — ragionando sulla documentazione, senza aver visto un'elezione — che «la manutenzione
ordinaria produce lo stesso tracciato nel log di un incidente». È falso, e si vede alla **prima
riga**: le tre cause hanno tre `id` diversi, e il testo dice in chiaro che cosa è successo.

Il punto da portare in sala è quale riga **non** proiettare. `21450` «Election succeeded» è la riga
che tutti mostrano, ed è l'unica delle quattro che non insegna niente: è identica se il primario è
morto, se si è dimesso o se un collega più titolato è tornato al suo posto. La riga che risponde è
la prima, ed è quella che nei tutorial non c'è mai.

Se c'è tempo, la coda: `id=4615601` «Scheduling priority takeover» compare **tre millisecondi dopo
la dimissione** e porta nell'attributo l'ora esatta in cui il rientro avverrà. Chi legge il log sa
dieci secondi prima che il primario sta per tornare — il log non racconta solo il passato.

---

### Il driver prova a raggiungere un host che nessuno ha scritto

> ```text
> $ mongosh "mongodb://…@host.docker.internal:27021/?replicaSet=rs0"
> MongoNetworkError: getaddrinfo ENOTFOUND mongo-rs-2
>                                          ^^^^^^^^^^
>                        nella stringa non c'è. E al tentativo dopo il nome cambia.
> ```

Fonte: [V-043](Sources.md#v-043) — dallo host verso lo stack `02-replicaset`. Decisione in
[ADR-0049](Decision.md#adr-0049), voce [13](02-architetture/trappole-mongodb-in-docker.md#t-13)
della pagina delle trappole.

**Perché una slide:** perché è il momento in cui si capisce che cos'è davvero un client di replica
set. L'indirizzo che si scrive nella stringa **serve solo a bussare**: subito dopo il driver chiede
al nodo com'è fatto il set, riceve `["mongo-rs-1:27017", "mongo-rs-2:27017", "mongo-rs-3:27017"]`,
adotta quei nomi e butta via quello con cui era entrato. Da lì in poi parla a nomi che fuori dalla
rete Docker non esistono. Non è un errore di configurazione: è il protocollo che funziona come
deve, dentro una rete in cui chi si connette non sta.

La seconda metà della slide è la mossa che peggiora le cose, e viene in mente a tutti: elencare
**tutti e tre** gli indirizzi pubblicati. Stesso errore, perché una seed list con più di un host è
una delle quattro eccezioni che spengono `directConnection` ([S-045](Sources.md#s-045)). Più
indirizzi buoni si scrivono, più si convince il driver a scoprire la topologia e a buttarli via
tutti e tre. È il caso raro in cui la soluzione è **scriverne uno solo**, e dire al driver di non
guardarsi intorno.

---

### La priorità non decide solo chi vince: decide anche quanto ci mette

> «The `priority` settings of replica set members affect both the timing and the outcome of
> elections for primary. Higher-priority members are more likely to call elections, and are more
> likely to win. Use this setting to ensure that some members are more likely to become primary
> and that others can never become primary.»

Fonte: [S-065](Sources.md#s-065) — MongoDB Manual 7.0, Adjust Priority for Replica Set Member.

E il campo ha un intervallo, con un valore predefinito che rende tutti i membri equivalenti:

> «The value of `priority` can be any floating point (i.e. decimal) number between `0` and `1000`.
> The default value for the `priority` field is `1`.»

Fonte: [S-065](Sources.md#s-065).

**Perché una slide:** spiega in una riga perché nel laboratorio il primario si può **nominare in
anticipo** — `mongo-rs-1` ha `priority: 2`, gli altri due `1` ([ADR-0051](Decision.md#adr-0051)) — e
prepara la sorpresa della demo di failover: il nodo che si è ucciso, quando torna, **si riprende il
ruolo da solo**. Misurato: undici secondi dopo uno `rs.stepDown(10)`
([V-042](Sources.md#v-042)). Va detto prima, altrimenti il pubblico vede una scena che si annulla
mentre la si commenta e non capisce se ha appena assistito a un guasto o a una guarigione.

### Chi maneggia il segreto lo nasconde, chi lo lancia lo lascia scritto

> ```text
> dentro il container:   mongosh mongodb://<credentials>@127.0.0.1:27017/?directConnection=true…
> sull'host:             /usr/local/bin/docker exec … mongosh --username admin --password <password> …
> ```

Fonte: [V-047](Sources.md#v-047) — misura del 2026-09-01 su `mongosh` 2.10.0; decisione in
[ADR-0054](Decision.md#adr-0054). Nella riga dell'host `<password>` è sostituita a mano: lì la
password c'è per davvero, ed è il punto.

**Perché una slide:** perché smonta l'abitudine di guardare nel posto sbagliato. La domanda «la
password si vede in `ps`?» ha due risposte opposte a seconda di quale tabella dei processi si
guarda, e quasi tutti guardano quella del container. Lì non si vede: `mongosh` riscrive il proprio
`argv` e mette `<credentials>` al posto delle credenziali. Si vede **sull'host**, nella riga del
client `docker`, che nessuno riscrive — e l'host è la macchina dove girano anche i programmi di
tutti gli altri. La morale sta in una riga e vale ben oltre MongoDB: quando si mette un comando
dentro un container, il confine di sicurezza non è dove sembra, ed è di là dal confine che il
segreto resta scritto. Sotto, la coda della storia: nello script c'era un `-e SEGRETO=` messo per
prudenza, che nessuno leggeva e che di quella password metteva una **seconda** copia proprio sulla
riga che la espone.

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

### Il volume c'era, aveva il nome giusto, ed era vuoto

> Il config server aveva il suo volume `dati-cfg1`, montato su `/data/db` come tutti gli altri
> nodi. Dentro: zero file. Scriveva in `/data/configdb`, perché con `--configsvr` l'immagine
> cambia il dbpath predefinito, e là Docker gli aveva messo un volume anonimo — che `down`
> butta via. Gli shard ricordavano i loro dati, i config server dimenticavano i propri, e al
> riavvio il cluster non riconosceva più i propri shard.

Fonte: [V-060](Sources.md#v-060), [ADR-0067](Decision.md#adr-0067).

**Perché una slide:** perché il messaggio d'errore accusava la persona sbagliata — parlava di un
database `lab` di troppo su uno shard — mentre la riga che spiegava tutto era «shard già
registrati: nessuno». È l'esempio migliore che ho di un guasto in cui la diagnosi sta due righe
sopra l'errore, e di uno stato che sopravvive dove non dovrebbe accanto a uno che sparisce dove
dovrebbe restare.

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

### Il dump fallito pesa 1,8 GB e non è un backup

> ```text
> 10:03:46.673  done dumping `lab.grandi` (15000 documents)
> 10:03:46.678  Failed: oplog overflow: mongodump was unable to capture
>                       all new oplog entries during execution
> uscita = 1
> ```
>
> ```text
> /tmp/dump-mini/lab/grandi.bson     1 536 555 000 byte
> /tmp/dump-mini/lab/disturbo.bson     320 525 373 byte
> /tmp/dump-mini/oplog.bson                  assente
> /tmp/dump-mini/prelude.json                assente
> ```

Fonte: [V-036](Sources.md#v-036), riprodotto su un'istanza usa-e-getta con oplog da 1 MB.
Decisione in [ADR-0047](Decision.md#adr-0047).

**Perché una slide:** perché il fallimento non ha l'aspetto di un fallimento. `mongodump` si ferma
**dopo** aver scritto tutte le collezioni: sul disco resta un albero completo, pesante, che si apre
senza errori e non è coerente rispetto a nessun istante. Mancano due file soli — `oplog.bson` e
`prelude.json` — e nessuno li guarda. L'unico segnale è il codice di uscita **1**, cioè la cosa che
gli script di backup scritti in fretta non controllano mai. In sala la domanda da fare prima di
mostrare la seconda schermata è: «quanti di voi controllano il valore di ritorno di `mongodump`?».

Da dire nello stesso respiro, perché altrimenti è un trucco: la prova è **forzata**. Un oplog da
1 MB con un checkpoint al secondo non esiste in produzione. Il caso vero è l'opposto — un oplog
normale e un dump che dura ore — e qui i due termini sono stati compressi per farli stare in tre
secondi. Il meccanismo e il messaggio sono quelli veri; la scala no.

### `mongodump` è dichiarato per installazioni piccole, dalla sua stessa documentazione

> «`mongodump` and `mongorestore` are tools for backing up and restoring **small** MongoDB
> deployments.»

> Nella tabella di confronto, la stessa pagina assegna alla coppia: RTO **High**, RPO **High**,
> ripristino continuo a un punto nel tempo **No**, coerenza **Not guaranteed**, backup di uno
> sharded cluster «High, requires extra steps».

Fonte: [S-060](Sources.md#s-060) — MongoDB Manual 7.0, *Backup Methods for a Self-Managed
Deployment*.

**Perché una slide:** perché la riserva più importante di una demo di backup non è un'opinione di
chi parla, è una riga del manuale. Chiude in anticipo la domanda «e in produzione?» senza doverla
argomentare. Va però detto anche il buco: «small» **non è quantificato da nessuna parte**, quindi la
frase orienta e non decide. E una riga della tabella — «impact on source: High, requires write lock»
— **non corrisponde** a quello che si vede sullo stack: durante i cinquanta millisecondi del dump le
scritture sono proseguite ([V-035](Sources.md#v-035)).

### Il punto nel tempo cade dentro il comando, non alla sua ultima riga

> | | senza `--oplogReplay` | con `--oplogReplay` |
> |---|---:|---:|
> | `lab.movimenti` ripristinati | **733** | **740** |
> | documenti presenti a fine dump | | **741** |

Fonte: [V-035](Sources.md#v-035), stesso file di dump ripristinato due volte.
Decisione in [ADR-0047](Decision.md#adr-0047).

**Perché una slide:** perché sostituisce una formula con un numero. «Coerente a un punto nel tempo»
non dice quale punto; questi tre numeri lo dicono. I **sette** documenti fra 733 e 740 sono quanto
vale `--oplogReplay` su un dump di cinquanta millisecondi — su un dump di mezz'ora sono mezz'ora di
scritture. E il documento che manca fra 740 e 741 è la definizione operativa del punto di
ripristino: **l'ultima voce di oplog catturata**, che cade dentro l'esecuzione del comando. Chi
scrive durante quel respiro finale ha il dato nel database e non nel backup.

Riserva da tenere sulla slide, non a voce: gli istanti nei documenti li scrive il **client**, quindi
il confine 740/741 è approssimato al millisecondo fra due orologi diversi.

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

### Lo stesso stack, scritto in due modi equivalenti: uno passa il controllo, l'altro no

> ```console
> $ check_stack.py senza-mongod.yaml     # command: [--replSet, rs0, --bind_ip_all]
> Stack conformi: 1.
>
> $ check_stack.py con-mongod.yaml       # command: [mongod, --replSet, rs0, --bind_ip_all]
> ✗ membro: avvia mongod senza «--wiredTigerCacheSizeGB».
> ```

Fonte: misura del Task 3 di `feature/02`, verbalizzata in
[`registro-operativo-sviluppo.md`](registro-operativo-sviluppo.md). L'entrypoint ufficiale
antepone `mongod` quando il primo argomento comincia per trattino: per Docker i due file
avviano lo stesso identico processo.

**Perché una slide:** è la lezione dei controlli automatici in sei righe. Lo strumento non
sbaglia una regola, sbaglia a riconoscere il bersaglio — e chi legge il verde non ha modo di
saperlo. Vale per ogni linter di configurazione: l'insieme delle scritture equivalenti nel
formato è parte del formato, e un controllo che ne conosce una sola è una convenzione
travestita da regola.

---

### `up` ha detto di sì, e per quattordici secondi la replica non c'era

> ```console
> $ docker compose ... up -d --wait
> $ echo $?
> 0
> $ docker inspect rs-init --format '{{.State.Status}}'
> running
> $ mongosh --quiet --eval 'rs.status()'
> NotYetInitialized (94)
> ```

Fonte: [V-025](Sources.md#v-025), misurata sullo stack `02-replicaset`. `--wait` è documentato
come «Wait services be running|healthy» ([S-057](Sources.md#s-057)); il servizio che inizializza
il replica set non ha un healthcheck, quindi la soglia che gli si applica è `running` — e un
container che deve morire è `running` nell'istante esatto in cui comincia. Il rimedio è un secondo
comando, `docker compose wait rs-init`, che «blocca fino a che i container si fermano» e ne
restituisce il codice di uscita.

**Perché una slide:** perché l'opzione fa esattamente ciò che dichiara, e la dichiarazione è stata
letta male da chi l'ha usata — cioè da me. In uno stesso file convivono due generi di servizio:
quelli per cui «pronto» significa *essere su*, e quelli per cui significa *essere finiti*. Una sola
opzione risponde alla prima domanda, e chi non si accorge di avere anche la seconda ottiene uno
zero che non vale niente. In sala funziona come esempio della classe di bug peggiore: quella che
riesce quasi sempre, perché su una macchina veloce lo scarto si accorcia e il test rosso arriva una
volta ogni tanto, su un'altra macchina, davanti a qualcun altro.

**Il numero è cambiato, e va detto così.** Da quando il caricamento dei dati di demo sta dentro
`rs-init` ([ADR-0043](Decision.md#adr-0043)) lo scarto misurato è di **ventidue** secondi
([V-028](Sources.md#v-028)). Sul palco si dica quello che si è misurato la mattina stessa, non un
numero imparato a memoria: il punto della slide non è il quattordici, è che lo zero arrivava prima.

---

### Chiedere la maggioranza costa un millisecondo, e questo è il numero più pericoloso della demo

> ```text
> ritardo primario -> secondario   mediana 1 ms
> scrittura con w: 1               mediana 1 ms
> scrittura con w: "majority"      mediana 2 ms
> ```

Fonte: [V-027](Sources.md#v-027), tre esecuzioni da dieci giri sullo stack `02-replicaset` a riposo.
`w: "majority"` restituisce l'ack quando la scrittura è arrivata a una maggioranza di membri, quindi
sopravvive alla caduta del primario ([S-035](Sources.md#s-035)); è il write concern con cui lo stack
02 carica i suoi 50 000 ordini.

**Perché una slide:** perché la garanzia più citata dei replica set, qui, costa un millisecondo — e
perché quel millisecondo non vale niente fuori da questa macchina. I tre membri girano sullo stesso
portatile, su un bridge Docker: `w: "majority"` è per definizione un giro fino al secondo membro più
veloce, e su due datacenter quel giro è la latenza fra i due datacenter — il termine dominante, non
un millisecondo. La slide serve a dire due cose insieme: *la maggioranza è quasi gratis qui*, e *chi
riporta questo numero altrove sta citando la propria rete, non MongoDB*. È anche l'occasione per
mostrare la misura sbagliata: `optimeDate` in `rs.status()`, che tutti usano per il ritardo di
replica, ha granularità di un secondo e su questo set risponde `0 ms` sempre — uno strumento che
dà sempre ragione non sta misurando.

---

### L'elezione dura sei millisecondi. I dieci secondi sono l'attesa prima di cominciarla

> ```text
> 19:01:47.369  id=21216    Member is now in state DOWN        ← 0,3 s dopo il colpo
>
>      ... nove secondi, e diciannove «Heartbeat failed after max retries» ...
>
> 19:01:56.558  id=4615652  Starting an election, since we've seen no PRIMARY
>                           in election timeout period
>                           electionTimeoutPeriodMillis: 10000
> 19:01:56.564  id=21450    Election succeeded, assuming primary role
> ```

Fonte: [V-030](Sources.md#v-030), un'elezione vera sullo stack `02-replicaset`, log del nodo
eletto. I tempi complessivi sono in [V-029](Sources.md#v-029): `docker kill` sul primario costa
**~10 s**, uno `shutdown` **~0,5 s**.

**Perché una slide:** perché smonta due frasi che si dicono sempre. La prima è «l'elezione è
lenta»: non lo è, dura sei millisecondi. Il tempo se ne va tutto ad **aspettare**, e il log lo dice
in un attributo invece che in una nota a piè di pagina. La seconda è che il set «si accorge dopo
dieci secondi»: se ne accorge dopo tre decimi, con `Connection refused` scritto nell'attributo, e
poi *decide di non fare niente* — perché un membro irraggiungibile per un istante non è un membro
morto, e indire un'elezione a ogni singhiozzo di rete costerebbe più di quello che salva. È la
differenza fra un timeout e un ritardo, e in sala è il punto in cui si capisce che quei dieci
secondi sono una scelta di progetto, non una lentezza.

Il seguito naturale è il confronto delle due scene: il gesto brutale — `docker kill` — costa dieci
secondi, quello educato mezzo. Chi si aspetta l'opposto ha ragione a sorprendersi, e la risposta è
sempre la stessa riga di log: con lo `shutdown` il primario **avvisa**, quindi non c'è nessun
timeout da far scadere.

---

### Il dollaro se lo mangia Compose, e nel container arriva una stringa vuota

> «You can use a `$$` (double-dollar sign) when your configuration needs a literal dollar sign.»

Fonte: [S-064](Sources.md#s-064) — Docker Docs, Compose file reference: Interpolation.

E quando non trova niente da sostituire, Compose non si ferma:

> «If Compose can't resolve a substituted variable and no default value is defined, it displays a
> warning and substitutes»

— e ciò che sostituisce è la stringa vuota. Un avviso, non un errore: il file resta valido, e
sbagliato.

Fonte: [S-064](Sources.md#s-064).

**Perché una slide:** è la trappola che si prende chiunque scriva un `command: sh -c` dentro un
`compose.yaml` — e nel laboratorio di MongoDB capita subito, perché i `mongosh --eval` di
inizializzazione ne sono pieni. La variabile è dichiarata due righe sopra, in `environment:`, e
dentro il container risulta vuota: Compose ha interpolato il `$` prima ancora che il file
diventasse un container, non ha trovato quella variabile **nel proprio ambiente** e ha messo una
stringa vuota. Misurato: `singolo=[]  doppio=[valore-del-container]`, e con la stessa variabile
esportata nella shell che lancia, il dollaro singolo stampa il valore **dell'host**
([V-046](Sources.md#v-046)). `docker compose config` esce `0` e si limita a un avviso.

### Con i profili, `down` spegne solo quello che il profilo dichiara

> Acceso in `completo`, spento con `--profile palco`: undici container rimossi, sette rimasti
> accesi, la rete che non si lascia togliere perché «resource is still in use». Codice di
> uscita: **zero**. E `down` senza `--profile` fa esattamente la stessa cosa, perché i servizi
> sempre attivi sono soltanto quelli che un profilo non ce l'hanno.

Fonte: [V-059](Sources.md#v-059), [S-068](Sources.md#s-068), [ADR-0066](Decision.md#adr-0066).

**Perché una slide:** è il tranello dei profili, e non ha nessun segnale — nessun errore, nessuna
riga rossa, e `docker compose ps` interrogato con lo stesso profilo sbagliato risponde «zero
container», cioè conferma l'idea sbagliata. La regola pratica sta in una riga: si accende con il
profilo che si vuole, si spegne con `--profile "*"`, perché al momento di spegnere non si sa con
quale profilo qualcun altro ha acceso.

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

---

### La riserva della demo pesa tredici kilobyte

> Quattro scene registrate — lo smoke completo, `docker kill` sul primario, la terminazione
> pulita, la maggioranza persa — occupano **13 KB** in tutto: 118 righe di JSON con accanto
> il secondo in cui ogni cosa è comparsa sullo schermo.

Fonte: [V-045](Sources.md#v-045) — le quattro registrazioni del branch `feature/02`.

**Perché una slide:** sta subito dopo i numeri di [S-021](Sources.md#s-021) e li ribalta. I filmati
restano fuori dal repository perché pesano; il tracciato del terminale ci sta dentro perché è testo,
e per lo stesso motivo si può leggere con `cat`, confrontare con `diff` e riprodurre senza
installare niente. Sono due riserve diverse, non due copie della stessa cosa: il filmato copre il
caso «la demo non parte», la registrazione di terminale il caso «la demo parte ma il tempo è
finito».

---

### Un config server sano che nessun healthcheck ragionevole vedrebbe

> Su un `mongod` avviato con `--replSet` e mai inizializzato, `db.hello()` risponde:
> `isWritablePrimary: false`, `secondary: false`, `isreplicaset: true`.
> I primi due termini sono falsi. Il terzo è l'unico vero — ed è quello che apre la strada a
> `rs.initiate()`.

Fonte: [V-052](Sources.md#v-052) — lo scheletro dello stack 03, e prima
[V-023](Sources.md#v-023) sullo stack 02.

**Perché una slide:** è la trappola dell'healthcheck in tre righe, e si racconta come un
indovinello. Un membro che deve ancora entrare nella replica non è primario e non è secondario:
qualunque sonda scritta con «primario oppure secondario» — la forma che viene naturale, e che il
design di questo progetto suggeriva — resta rossa per sempre, e la catena di avvio non arriva mai a
inizializzare il set che renderebbe la sonda verde. Il guasto si presenta come un `up --wait` che
non ritorna, e nessuno guarda l'healthcheck perché l'healthcheck «è giusto».

---

### Il codice che ha funzionato altrove non è neutro

> Il file Compose dello spike si poteva riportare così com'era. Dentro c'erano due decisioni, non
> una: gli ancoraggi YAML, visibili e discutibili, e una sonda `ping` che non aveva l'aria di una
> scelta. La prima si vede aprendo il file. La seconda si sarebbe scoperta al primo avvio che
> dichiara pronto un cluster senza cluster.

Fonte: [ADR-0059](Decision.md#adr-0059) — la nota di metodo 92 del
[registro](registro-operativo-sviluppo.md).

**Perché una slide:** vale ben oltre MongoDB, e il pubblico di SqlStart la riconosce subito — è
quello che succede ogni volta che si copia un `docker-compose.yml` trovato funzionante. Un
artefatto che gira porta con sé tutte le scelte di chi l'ha scritto, comprese quelle che non ha
saputo di prendere, e passa la frontiera tutto insieme se nessuno lo ferma. Le righe che nessuno
commenterebbe sono quelle da guardare.

---

### Tre replica set che non si conoscono

> Uno sharded cluster senza `mongos` non è uno sharded cluster a cui manca un pezzo. Sono tre
> replica set separati, ognuno funzionante, nessuno dei quali sa che gli altri esistono.

Fonte: l'intestazione di `docker/03-sharded/compose.yaml` a fine Task 2, e
[V-054](Sources.md#v-054).

**Perché una slide:** è la definizione di `mongos` data per sottrazione, e regge una slide intera
del Blocco 3. Il pubblico che conosce i replica set arriva allo sharding pensando «un replica set
più grande»: questa frase gli dice che i pezzi che ha già in testa ci sono tutti e non bastano, e
che la cosa nuova da capire è quella che li unisce. Funziona bene subito prima di far vedere
`sh.status()`.

---

### «Healthy» accanto a un container morto

> `docker compose up --wait` ha stampato `Container sh-cfg-init Healthy` per un container che
> `docker inspect` descriveva come uscito con codice 5. Per `--wait`, un servizio senza healthcheck
> è a posto nell'istante in cui parte.

Fonte: [V-054](Sources.md#v-054), che riconferma [V-025](Sources.md#v-025) su uno stack diverso;
la decisione è [ADR-0041](Decision.md#adr-0041).

**Perché una slide:** è la trappola dell'automazione che dice «fatto» quando non lo è, e qui si
vede con gli occhi invece di doverla spiegare. Vale per ogni pipeline, non solo per Compose: un
comando che esce 0 sta rispondendo alla domanda che gli è stata fatta, e quasi mai è la domanda
che interessava. Nel lab la risposta è due comandi e non uno.

---

### Nominare un servizio non è attivare il suo profilo

> Con `--profile palco`, un servizio che dipende da uno spento fa fallire l'intero progetto.
> Nominando lo stesso servizio sulla riga di comando, quella dipendenza spenta viene accesa e tutto
> parte. Due modi di selezionare la stessa cosa, comportamento opposto davanti alla stessa
> dipendenza.

Fonte: [V-053](Sources.md#v-053) — quattro casi, quattordici righe di `busybox`, e la riserva che
[ADR-0010](Decision.md#adr-0010) teneva aperta dal 24 agosto.

**Perché una slide:** se resta tempo. È una finezza di Compose, non di MongoDB, ma è la prova
visibile che una riserva dichiarata si chiude in dieci minuti quando qualcuno decide di misurarla —
e questa era aperta da otto giorni perché il progetto le girava intorno con eleganza.

---

### Il confine di un permesso non si trova al centro

> «L'eccezione localhost permette di creare il primo utente.» Due comandi confermavano quella
> frase. Sette dicono altro: `replSetGetStatus` risponde per intero, `listDatabases` risponde con
> un elenco vuoto, `serverStatus` e le letture no. Il confine ha una forma. Con due misure si
> disegna una retta, e la retta è quasi sempre la risposta sbagliata a una domanda sul perimetro.

Fonte: [V-054](Sources.md#v-054), che restringe la conclusione di [V-052](Sources.md#v-052); note
di metodo 93 e 95 del [registro](registro-operativo-sviluppo.md).

**Perché una slide:** è la slide della sicurezza detta bene, e ha il pregio raro di mostrare il
relatore che corregge se stesso a distanza di poche ore con una misura in più. Il messaggio che
resta non è su MongoDB: un permesso descritto in prosa va provato dove smette di funzionare, non
dove funziona.

---

### Un cluster senza shard non dice di essere rotto: risponde `[]`

> Un `mongos` a cui non è stato registrato nessuno shard è `healthy` per Docker, risponde a
> `hello()`, a `ping`, a `listDatabases`. E a una lettura risponde `[]` — la stessa cosa che
> risponderebbe un cluster sano con la collezione vuota. Solo la scrittura dice la verità:
> `No shards found`. Il guasto che risponde bene costa più di quello che risponde male.

Fonte: [V-055](Sources.md#v-055); [ADR-0061](Decision.md#adr-0061) e la nota di metodo 98 del
[registro](registro-operativo-sviluppo.md).

**Perché una slide:** è la slide che giustifica perché lo smoke del lab **scrive** invece di
leggere, e vale ben oltre MongoDB. Si può mostrare dal vivo in venti secondi: `find` prima di
`sh.addShard()`, `insertOne` subito dopo, e la stessa riga di codice che prima taceva e adesso
parla.

---

### Fra tre replica set e uno sharded cluster c'è una riga scritta da qualche parte

> Prima di `sh.addShard()` ci sono `cfgrs`, `shard1rs` e `shard2rs`: tre replica set funzionanti,
> nessuno dei quali sa che gli altri esistono. Dopo, c'è un cluster. Sui nove `mongod` non è
> cambiato niente — stessi processi, stessi dati, stessi file. È cambiata una riga in
> `config.shards`.

Fonte: [V-055](Sources.md#v-055) e `docker/03-sharded/init/20-add-shard.js`.

**Perché una slide:** è il momento del Blocco 3 in cui lo sharding smette di sembrare un'altra
tecnologia e torna a essere MongoDB con un registro in più. Serve a smontare l'idea che passare a
sharded significhi rifare tutto.

---

### La sonda più severa non è sempre la più rigorosa

> «Che `healthy` voglia dire davvero pronto» sembra rigore. Se l'healthcheck di `mongos` avesse
> preteso gli shard registrati, il servizio che li registra — che gira dentro `mongos` e lo
> aspetta sano — non sarebbe mai partito. E Compose avrebbe accusato `mongos`, che era innocente.

Fonte: [ADR-0061](Decision.md#adr-0061), nota di metodo 97 del
[registro](registro-operativo-sviluppo.md).

**Perché una slide:** se resta tempo, come chiusura del Blocco 3. Non parla di MongoDB ma di come
si progettano le catene di avvio, e la regola sta in una riga: quando B aspetta la sonda di A e il
lavoro di B è cambiare ciò che quella sonda misura, la sonda di A può solo chiedere se A è vivo.

---

### Il router è l'unico pezzo del cluster che si può buttare via

> Nove `mongod` hanno un volume ciascuno. I due `mongos` non ne hanno nessuno: niente `--replSet`,
> niente cache dello storage engine — passargliela lo fa proprio fallire, perché uno storage
> engine non ce l'ha. Ho fermato il primo router in mezzo a una demo e ho scritto sul secondo.
> Non si è perso niente, perché non c'era niente da perdere.

Fonte: [V-055](Sources.md#v-055), sesto punto.

**Perché una slide:** è la mezza slide del Blocco 3 sui router, e si dimostra dal vivo con un
`docker stop`. Le tre assenze — replica set, volume, cache — sono la definizione operativa di
«senza stato» detta con tre righe di `compose.yaml` invece che con una definizione.

---

### C'è un container nello stack che non fa niente, e c'è per un motivo

> `docker compose up --wait` esce 0 diciotto secondi dopo l'avvio, con zero shard registrati. Ed
> esce 0 anche quando la catena è rotta e nessuno shard esisterà mai. La proprietà «esce 0 solo
> quando il cluster serve» non si poteva verificare: si è dovuta costruire, e per costruirla serve
> un servizio che stampa una riga e dorme.

Fonte: [V-056](Sources.md#v-056), [ADR-0062](Decision.md#adr-0062).

**Perché una slide:** è la slide onesta sul lab. Il pubblico vede in `docker ps` un container che
non è MongoDB e ha diritto di chiedere perché; la risposta insegna più di quanto costi. Si mostra
con due `docker compose up --wait` cronometrati, uno per verso.

---

### La ricetta giusta per uno stack è quella sbagliata per l'altro

> Sullo stack a replica set l'avvio è di due comandi, perché `up --wait` torna troppo presto. Sullo
> stack sharded il secondo comando fallisce **sempre**: `docker compose wait` vuole un container
> vivo, e a quel punto il one-shot ha già finito. Stessa famiglia di problema, due risposte
> opposte, e copiare la prima nella seconda dà un bersaglio che non funziona mai.

Fonte: [ADR-0062](Decision.md#adr-0062), che non tocca [ADR-0041](Decision.md#adr-0041).

**Perché una slide:** se resta tempo. È il rimedio contro la generalizzazione affrettata, che nel
lab si vede in dieci righe di Makefile.

---

### Un ramo d'errore che non è mai stato eseguito non è codice: è un'intenzione

> Sei righe scritte bene: nominavano le due cause frequenti, uscivano con il codice giusto. Erano
> irraggiungibili, perché `sh.addShard()` solleva invece di rispondere `ok: 0`. Ho scoperto che
> non funzionavano solo perché una verifica mi ha costretto a rompere la catena apposta.

Fonte: nota di metodo 101 del [registro](registro-operativo-sviluppo.md),
[V-056](Sources.md#v-056) quinto punto.

**Perché una slide:** è la gemella della slide sui messaggi d'errore, e chiude il cerchio: scrivere
un buon messaggio non basta, bisogna averlo letto almeno una volta con gli occhi.

---

### La sonda severa si mette solo dove non aspetta nessuno

> Un healthcheck che pretende un cluster completo su `mongos` è uno stallo, perché è il servizio in
> coda a doverlo completare. Lo stesso healthcheck su un servizio da cui non dipende nessuno è
> gratis. Non cambia la sonda: cambia chi la sta aspettando.

Fonte: [ADR-0061](Decision.md#adr-0061) e [ADR-0062](Decision.md#adr-0062), note di metodo 97 e 102.

**Perché una slide:** chiusura del Blocco 3 se resta tempo. È una regola di progettazione delle
catene di avvio che vale ovunque ci siano dipendenze e sonde, non solo in Compose.

---

### Due lettere, novantaquattro secondi, e la parola giusta che non compare mai

> `cfgsr` invece di `cfgrs` dentro `--configdb`. Tutti i container partono. Dopo novantaquattro
> secondi il router è ancora `unhealthy` e non ha mai aperto la porta. Nel suo log il nome giusto
> del replica set — `cfgrs` — compare **zero volte**: quello che si legge è «host irraggiungibile»
> su due host che dovevano essere irraggiungibili, e un errore di read preference sull'unico host
> che sta rispondendo benissimo. La diagnosi indica la rete. La causa sono due lettere.

Fonte: [V-057](Sources.md#v-057) quarto punto, [ADR-0063](Decision.md#adr-0063).

**Perché una slide:** è il caso più forte del Blocco 3 per giustificare un controllo statico, e non
ha bisogno di sapere che cos'è uno sharded cluster per fare effetto. Chiunque abbia debuggato una
rete che non era la rete la riconosce.

---

### Il guadagno non è capire l'errore: è quando lo incontri

> Cinque errori su sei nello sharded cluster te li dice il server, per nome e in chiaro: «Cannot run
> addShard on a node started without --shardsvr». Non sono muti. Il controllo statico non serve a
> tradurli — serve a incontrarli in due secondi su un file fermo, invece che al minuto e ventuno
> dell'avvio, con dieci container accesi e il pubblico che guarda.

Fonte: [ADR-0063](Decision.md#adr-0063), [V-057](Sources.md#v-057) sesto punto.

**Perché una slide:** è la giustificazione onesta di ogni linter, e va contro quella che si dà di
solito. Sposta il valore dal contenuto del messaggio al momento in cui arriva.

---

### Misurare non serve a sapere se la regola serve: serve a sapere perché

> La regola l'avrei scritta identica senza misurare niente. Quello che sarebbe cambiato è la frase
> accanto: avrei scritto «senza questo controllo l'errore è illeggibile», che è comodo, plausibile,
> e falso. E sarebbe rimasto scritto in un documento come il motivo di una decisione.

Fonte: nota di metodo 103 del [registro](registro-operativo-sviluppo.md).

**Perché una slide:** se resta tempo. Vale per ogni difesa che si costruisce senza aver mai provato
l'attacco: il codice viene uguale, la ragione no, e la ragione è la parte che gli altri leggono.

---

### Un commento su un altro file è un'affermazione a termine, e nessuno le mette la scadenza

> «Questa riga fa X» invecchia con la riga sotto, che è nello stesso schermo. «Questo serve perché
> altrove succede Y» invecchia quando cambia Y, che è in un altro file, e nessun controllo
> automatico se ne accorge. Ne ho trovati due nello stesso file, scritti da me, tutti e due giusti
> il giorno in cui li ho scritti.

Fonte: nota di metodo 104 del [registro](registro-operativo-sviluppo.md).

**Perché una slide:** se resta tempo, nel blocco sulla manutenzione. La contromossa costa poco —
citare la misura accanto all'affermazione, così chi rilegge sa dove andare a verificare.

---

### Uno sharded cluster rotto risponde benissimo

> Ho scritto sessantadue controlli. Sessantuno passerebbero identici su un cluster che ha messo
> tutti i ventimila documenti su un solo shard: risponde, scrive, legge, e `sh.status()` gli mostra
> due shard belli attivi. Uno solo se ne accorge, ed è quello che conta i documenti per shard.

Fonte: [ADR-0065](Decision.md#adr-0065), [V-058](Sources.md#v-058) settimo punto.

**Perché una slide:** è il Blocco 3 in una frase. Distingue «funziona» da «fa quello per cui l'hai
messo in piedi», che in uno sharded cluster non sono la stessa cosa e non lo sembrano nemmeno.

---

### O distribuisci le scritture, o tieni vicine le letture

> Con la chiave hashed, `{_id: 42}` interroga uno shard e `{_id: {$gte: 100, $lt: 200}}` li
> interroga tutti e due. Stessa collezione, stessa chiave, due righe di distanza. Non è un difetto
> della configurazione: è il prezzo, ed è scritto nel manuale.

Fonte: [ADR-0064](Decision.md#adr-0064), [S-066](Sources.md#s-066), misurato in
[V-058](Sources.md#v-058) terzo punto.

**Perché una slide:** il baratto della shard key in due comandi che si possono eseguire dal vivo. È
la cosa che chi torna in ufficio applicherà, e l'unica di questa architettura che non si corregge
senza rifare la collezione.

---

### Il collo di bottiglia non sparisce: cambia nodo

> La versione breve dice che una chiave che cresce sempre manda tutte le scritture su un nodo. Il
> manuale aggiunge una riga che quasi nessuno riporta: il chunk caldo non resta fermo, quando si
> divide il pezzo con `MaxKey` finisce su un altro shard. Quindi il nodo cambia. Quello che non
> cambia è che in ogni istante stanno scrivendo tutti nello stesso posto — più il costo di
> spostarlo.

Fonte: [S-067](Sources.md#s-067) secondo punto, [ADR-0064](Decision.md#adr-0064).

**Perché una slide:** perché la versione caricaturale si smonta alla prima domanda del pubblico, e
questa no. Vale anche come metodo: la riga che rovina la spiegazione semplice è di solito quella che
la rende vera.

---

### Le credenziali del cluster non aprono uno shard

> Stessa utenza, stessa password. Sul router entra; su uno shard interrogato in diretta risponde
> «Authentication failed». Non è un guasto: gli utenti di uno sharded cluster vivono nel database
> `admin` dei config server, e uno shard autentica contro i propri, che non ci sono.

Fonte: [V-058](Sources.md#v-058) quarto punto, [ADR-0065](Decision.md#adr-0065).

**Perché una slide:** se resta tempo. È la sorpresa più pratica dello stack — chi prova a
diagnosticare uno shard collegandocisi sopra la incontra al primo tentativo — e dice in un esempio
dove sta davvero il centro di un cluster sharded.

---

### Il cluster considera «bilanciata» una distribuzione cento a zero

> Ventimila documenti, chiave `{_id: 1}`: ventimila su uno shard, zero sull'altro. Poi si chiede al
> cluster se è bilanciato, e risponde `balancerCompliant: true`. Non è un guasto del balancer: è la
> sua specifica, perché la differenza fra i due shard è 1,2 MB e la soglia perché si muova è 384 MB.
> La shard key sbagliata non ha sintomo, e lo strumento che dovrebbe accorgersene conferma che va
> tutto bene.

Fonte: [V-061](Sources.md#v-061) quarto punto, [S-070](Sources.md#s-070) terzo punto,
[ADR-0068](Decision.md#adr-0068).

**Perché una slide:** è il cuore del Blocco 3, e la sola frase di tutto il talk in cui lo strumento
di diagnosi mente dicendo la verità. Un errore irreversibile che nessun controllo segnala vale più
di dieci raccomandazioni su come scegliere una chiave.

---

### La trappola colpisce chi ha scelto bene

> Chiave hashed, `insertMany` di ventimila documenti: **11 328 ms**. Stessa chiave, stessi
> documenti, `ordered: false`: **336 ms**. Con la chiave monotona le due forme costano uguale. Il
> costo non è la chiave giusta: è la chiave giusta insieme al predefinito che nessuno cambia, perché
> mantenere l'ordine fra shard diversi vuol dire aspettare, e con l'hash lo shard cambia quasi a
> ogni documento.

Fonte: [V-061](Sources.md#v-061) sesto punto, [S-071](Sources.md#s-071) primo punto,
[ADR-0068](Decision.md#adr-0068).

**Perché una slide:** perché ribalta l'aspettativa. Il pubblico si aspetta che a pagare sia chi
sbaglia la chiave, e invece paga chi l'ha azzeccata e non ha toccato il codice di caricamento che
funzionava sul replica set. Un ordine di grandezza, senza un errore e senza un avviso.
