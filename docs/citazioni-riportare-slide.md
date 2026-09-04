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

### Cercare `null` trova anche i documenti che quel campo non ce l'hanno

> «The `{ metacritic : null }` query matches documents that contain the `metacritic` field with a
> `null` value **or** do not contain the `metacritic` field.»

Fonte: [`app/docs/Sources.md` A-006](../app/docs/Sources.md#a-006) — MongoDB Database Manual, *Query
for Null or Missing Fields*.

**Perché una slide:** è la differenza fra «l'ordine è stato annullato con motivazione vuota» e «il
campo motivazione non è mai stato scritto», e in un documento senza schema quei due casi convivono
nella stessa collezione. Chi arriva da SQL legge `= NULL` e si aspetta il primo. Per distinguerli
servono altri operatori — `{ $type: 10 }` per il solo `null` esplicito, `{ $exists: false }` per il
solo campo assente — e il fatto che ne servano due dice tutto: nel modello a documenti «assente» e
«vuoto» sono due stati, non uno.

---

### Confrontare un sottodocumento intero confronta anche l'ordine dei campi

> «MongoDB does not recommend comparisons on embedded documents because the operations require an
> *exact* match of the specified `<value>` document, **including the field order**.»
>
> «Queries that use comparisons on embedded documents can result in unpredictable behavior when used
> with a driver that does not use ordered data structures for expressing queries.»

Fonte: [`app/docs/Sources.md` A-007](../app/docs/Sources.md#a-007) — MongoDB Database Manual, *Query
on Embedded/Nested Documents*.

**Perché una slide:** `{w: 21, h: 14}` e `{h: 14, w: 21}` sono lo stesso oggetto in ogni linguaggio
che il pubblico usa tutti i giorni, e non sono lo stesso filtro in MongoDB. È la seconda frase a fare
paura più della prima: il comportamento dipende dalla struttura dati con cui il **driver** esprime la
query, cioè da qualcosa che chi scrive il codice non vede. La soluzione sta nella stessa pagina, ed
è la notazione con il punto: si interroga **per campo annidato** — `{ "size.w": 21 }` — non per
documento intero.

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

---

### I chunk erano quattro. Adesso sono due. Nessuno ha toccato niente

> Spengo il cluster conservando i volumi, lo riaccendo, e i chunk sono la metà. Ventimila documenti
> prima, ventimila dopo, distribuiti uguale al byte. Non è una migrazione: è una **fusione**, e il
> registro dice l'ora — tre secondi e otto dopo l'avvio del config server, sei secondi prima che il
> router esistesse. Dalla 7.0 il balancer fa due mestieri, e in questo laboratorio ne esercita
> esattamente uno: quello che nessuno guarda.

Fonte: [V-062](Sources.md#v-062) primo e terzo punto, [S-072](Sources.md#s-072),
[ADR-0069](Decision.md#adr-0069).

**Perché una slide:** perché è una scena da fare dal vivo in un comando — distribuire, contare
quattro, spegnere, riaccendere, contare due — e perché smonta l'equazione «balancer = migrazione»
che la documentazione stessa incoraggia. È anche una lezione su come si sbaglia una pagina: la
misura era giusta, l'aspettativa no.

---

### Un container che condivide la rete di uno shard è amministratore di quello shard

> Il cluster è autenticato: dal router, senza password, non fai niente. Ma gli utenti del cluster
> vivono sui config server, e gli shard non ne ricevono copia: ogni shard è un replica set **senza
> utenti**, e per un deployment senza utenti l'eccezione localhost è aperta. Dalla porta pubblicata
> sull'host non passi — la connessione arriva dal gateway di Docker. Da un container che condivide
> la rete dello shard sì, perché `localhost` appartiene al network namespace, non al container. E
> non ti serve il keyfile.

Fonte: [V-064](Sources.md#v-064) terzo, quarto e quinto punto, [S-074](Sources.md#s-074),
[ADR-0070](Decision.md#adr-0070).

**Perché una slide:** è la frase che fa la differenza fra sapere che l'eccezione localhost esiste e
sapere dove finisce. Il manuale la enuncia — «applies to each shard individually» — e la misura
mostra la conseguenza in Docker, che il manuale non può conoscere. Da dire con il comando a
schermo: due righe, e un `root` che non esisteva.

**Seguito, e va detto sulla stessa slide:** su questo stack, da [ADR-0071](Decision.md#adr-0071),
quel comando risponde `Unauthorized`. I due shard hanno un amministratore locale, creato dal loro
init sul primario appena eletto, e il primo utente chiude l'eccezione dietro di sé. La slide non
perde niente — la falla è di **qualunque** shard senza utenti, che è la condizione predefinita di
ogni replica set appena inizializzato — ma finire con «e questo è come si chiude» vale più che
finire con lo spavento. Chiuderla ha un prezzo che sta in una riga: prima le porte pubblicate degli
shard non accettavano nessuna credenziale, perché non c'era nessun utente; adesso ne accettano una
([V-066](Sources.md#v-066)).

---

### Il messaggio d'errore che nasconde quello vero

> `mongodump --oplog` su un cluster: «can't use `--oplog` option when dumping from a mongos».
> Chiaro. Ma se insieme hai messo anche `--db`, la risposta cambia: «`--oplog` mode only supported
> on full dumps». Non nomina più il router. Togli `--db`, riprovi, e **solo allora** scopri che il
> problema era un altro. Le due regole sono verificate in quest'ordine, e la prima nasconde la
> seconda.

Fonte: [V-065](Sources.md#v-065) primo e secondo punto, [S-011](Sources.md#s-011),
[ADR-0070](Decision.md#adr-0070).

**Perché una slide:** dice una cosa sui messaggi d'errore che vale oltre MongoDB — chi sbaglia due
cose ne vede riferita una sola, e non è detto che sia quella che conta. Costa dieci secondi e
resta.

---

### Il restore è riuscito. La collezione non è più distribuita

> Ventimila documenti ripristinati, zero errori, e persino l'indice hashed ricreato. Guardi il
> conteggio, torna. Guardi dove stanno: **tutti su un solo shard**. `mongorestore` ricrea gli
> indici e non chiama `shardCollection`. Hai la chiave che serve a distribuire e non hai la
> distribuzione, e niente te lo dice: hai appena trasformato uno sharded cluster in un replica set
> con un indice inutile.

Fonte: [V-065](Sources.md#v-065) sesto punto, [ADR-0070](Decision.md#adr-0070).

**Perché una slide:** è il caso peggiore per chi ripristina — nessun errore, nessun avviso, e il
controllo che verrebbe naturale fare (contare i documenti) conferma che è tutto a posto. Se il
Blocco 3 ha tempo per un solo avvertimento operativo, è questo.


---

### Il ruolo minimo che si promuove da solo

> Il manuale, per l'amministratore di uno shard, prescrive `userAdminAnyDatabase`: amministra gli
> utenti, **non legge i dati**. Provato: `lab.ordini` risponde `Unauthorized`. Poi quello stesso
> utente si concede `root` — è un comando, ed è esattamente ciò che «amministra gli utenti»
> significa — e la collezione la legge. Fra il ruolo minimo e `root`, su quel nodo, non c'è una
> barriera di privilegio: c'è un comando in più. La barriera vera è **chi conosce la password**.

Fonte: [V-066](Sources.md#v-066) quinto punto, [S-075](Sources.md#s-075),
[ADR-0071](Decision.md#adr-0071).

**Perché una slide:** smonta l'automatismo per cui «ruolo minimo» equivale a «più sicuro», che in
sala pensano tutti e nessuno ha provato. È anche l'onestà del lab: spiega perché questo stack usa
`root` invece di fingere una separazione che con una password sola non esisterebbe. Tre righe di
console, e si vede.

---

### Abbiamo chiuso un buco, e con il buco se n'è andato l'unico segnale

> Fino a ieri, chiedere a uno shard lo stato del bilanciatore rispondeva «non sei autorizzato»: un
> errore reticente, ma un errore. Oggi risponde **`true`**. Non è cambiato MongoDB — abbiamo dato
> agli shard un amministratore, come prescrive il manuale, e adesso quella lettura riesce: legge una
> collezione che su uno shard non esiste, non trova niente, e dal niente conclude che il bilanciatore
> è acceso. Il vuoto ha l'aspetto di una risposta.

Fonte: [V-067](Sources.md#v-067) quinto punto, [ADR-0071](Decision.md#adr-0071),
[ADR-0072](Decision.md#adr-0072).

**Perché una slide:** è il prezzo di una scelta giusta, e non sta scritto in nessun manuale. Chiude
il paio con «Il messaggio d'errore che nasconde quello vero»: là una regola ne nascondeva un'altra,
qui a nascondere era un permesso mancante, e a toglierlo siamo stati noi. Due minuti, e in sala
resta l'idea che rimuovere un errore può togliere un'informazione.

---

### La disponibilità non è del cluster: è di ogni singolo shard

> Lo stesso comando, due configurazioni. Con un membro per shard, fermato quel membro, il router
> aspetta **quindici secondi** e poi dice che per `shard1rs` non trova un primario: metà dei
> ventimila documenti è irraggiungibile, mentre l'altra metà continua a rispondere in un secondo.
> Con tre membri per shard lo stesso guasto quasi non si vede — il conteggio torna ventimila in
> **zero secondi**, e il primario nel frattempo è passato da `shard1a` a `shard1b`. Uno sharded
> cluster non cade intero: cade a pezzi, e ogni pezzo si porta via i propri documenti.

Fonte: [V-068](Sources.md#v-068) quarto esito, [ADR-0010](Decision.md#adr-0010).

**Perché una slide:** corregge l'idea che chi arriva dal replica set si porta dietro senza
accorgersene — «più nodi, più resistenza». Nello sharding la ridondanza sta **dentro** ogni shard, e
fra shard non c'è: se uno shard non ha un secondario, la sua fetta di dati sparisce e il cluster
continua a rispondere benissimo per tutto il resto. Le due misure vanno mostrate una accanto
all'altra, perché è il confronto a dire la cosa vera: la differenza non è il prodotto, è il numero
di membri per shard.

---

### Un profilo che non esiste non è un errore: è un cluster fatto di un container solo

> Compose non protesta se gli si chiede un profilo che nel file non c'è. Un profilo sconosciuto non
> seleziona niente, quindi restano i soli servizi che non appartengono a nessun profilo — nel nostro
> file uno, il one-shot che genera il keyfile. `make up-03 PROFILO=complteo` avvia quel container,
> lo aspetta, lo vede uscire **0**, e muore dicendo `container sh-keyfile-init exited (0)`. Accusa
> l'unico pezzo che ha fatto esattamente il suo mestiere. In cinque righe di errore la parola
> «profilo» non compare mai.

Fonte: [V-069](Sources.md#v-069) secondo esito, [ADR-0074](Decision.md#adr-0074).

**Perché una slide:** completa il paio con «Nominare un servizio non è attivare il suo profilo». Là
il profilo c'era e non bastava nominarlo; qui il profilo non c'è e nessuno lo dice. Chi porta a casa
i nostri file Compose incontrerà il secondo caso al primo refuso, e la lezione generale vale oltre
Docker: quando una selezione non trova niente, il risultato vuoto **è** una risposta valida, e a
valle nessuno sa più che la domanda era sbagliata.

---

### Un errore risponde alla domanda che gli hai fatto, non a quella che volevi fare

> Due messaggi raccolti nello stesso pomeriggio. `container sh-keyfile-init exited (0)`: vero — quel
> container è uscito 0 — e il problema era un profilo scritto male. `no containers for project
> "sqlstart-02-replicaset"`: vero anche questo, perché il comando cerca container **vivi** e quello
> che aspettava aveva finito; nello stesso istante il progetto ne aveva **cinque**, e `ps` li
> elencava tutti. Nessuno dei due strumenti ha mentito. Tutt'e due hanno risposto benissimo alla
> domanda letterale, e il tempo perso è tutto nella distanza fra quella e la domanda vera.

Fonte: [V-069](Sources.md#v-069) secondo e quinto esito, [ADR-0074](Decision.md#adr-0074),
[ADR-0075](Decision.md#adr-0075).

**Perché una slide:** è la lezione trasversale del blocco, e in sala si spende in un minuto perché i
due messaggi si mostrano affiancati. Vale per il debug di uno sharded cluster quanto per quello dei
container: prima di credere a un messaggio d'errore conviene chiedersi **quale domanda** lo strumento
si è posto. È lo stesso meccanismo per cui un cluster senza shard risponde `[]` invece di dire che è
rotto.

---

### Un avviso che non cambia il codice d'uscita è un avviso che nessuno legge

> Due punti della catena dello sharded sapevano di essere in guasto e lo scrivevano. Il seed
> stampava «ATTENZIONE: lab.ordini non risulta distribuita» — corretto, in italiano, esatto — e
> usciva **0**. Il router ripeteva `Command find requires authentication` e restava `unhealthy`
> senza che nessuno gli chiedesse perché. Le frasi erano giuste; finivano in uno stream che il
> chiamante automatico non guarda. `up --wait` raccoglie codici d'uscita e stati di salute, e una
> catena di sei anelli esiste proprio perché nessuno debba leggere sei log.

Fonte: [V-071](Sources.md#v-071), [V-072](Sources.md#v-072), [ADR-0077](Decision.md#adr-0077), nota
di metodo 135.

**Perché una slide:** un messaggio diagnostico e un codice d'uscita non sono due modi di dire la
stessa cosa. Il primo serve a chi è **già andato** a guardare, il secondo serve a **farcelo andare**.
In sala si mostra affiancando le due righe — l'avviso e lo `exited with code 0` sotto — e la platea
lo riconosce subito, perché è il difetto che tutti hanno in produzione da qualche parte. Il corollario
operativo sta in una domanda: se una condizione merita la frase, merita anche il codice? Quando la
risposta è no, va scritto perché.

---

### Due revisori che trovano cose diverse non sono uno bravo e uno no

> La stessa PR è stata letta da due modelli. Il primo ha guardato una funzione e ha ragionato sul
> valore di ritorno: ha trovato un difetto di messaggio e ha sbagliato la diagnosi. Il secondo ha
> guardato la catena di avvio e ha ragionato sul codice d'uscita: ha trovato tre falsi verdi e non ha
> sbagliato niente. Nessuno dei due ha visto quello che ha visto l'altro.

Fonte: [ADR-0076](Decision.md#adr-0076), [ADR-0077](Decision.md#adr-0077), nota di metodo 136.

**Perché una slide:** la conclusione comoda sarebbe «chiediamo al migliore», e non regge alla prova
dei fatti. La domanda che si pone al revisore decide che cosa può trovare: il prompt della seconda
review nominava esplicitamente codici d'uscita e comandi che falliscono in silenzio, e i tre rilievi
sono arrivati esattamente da lì. Vale per i modelli e vale per le persone, ed è il motivo per cui una
checklist di review è uno strumento e non una formalità.

---

### `frozen` protegge da una distrazione, `slots` protegge anche da chi conosce la scorciatoia

> Congelare una dataclass Python blocca l'assegnazione normale, e basta: l'istanza conserva un
> `__dict__`, e da lì passano sia `object.__setattr__` sia la scrittura diretta. Misurato sulle due
> varianti della stessa classe, la differenza è netta. Senza `slots`: assegnazione bloccata,
> `object.__setattr__` **riesce**, scrittura nel `__dict__` **riesce**. Con `slots`: il `__dict__`
> non esiste, e con esso spariscono entrambe le vie. La documentazione lo dice fin dalla prima riga
> e nessuno la legge fino in fondo — «It is not possible to create truly immutable Python objects.
> However, by passing `frozen=True` […] you can **emulate** immutability».

Fonte: [`app/docs/Sources.md` M-003](../app/docs/Sources.md#m-003) e
[A-002](../app/docs/Sources.md#a-002), [ADR-0019](Decision.md#adr-0019).

**Perché una slide:** l'oggetto che attraversa la coda fra il thread del driver e quello del disegno
è il punto in cui la demo del failover può mentire, e «l'ho congelato» è la rassicurazione che tutti
danno per buona. La misura mostra che protegge dalla svista e non dalla scorciatoia, che è
esattamente la distinzione utile: `frozen` difende dal codice scritto in buona fede, `slots` chiude
anche la porta di servizio. Vale oltre Python — ogni garanzia di immutabilità va guardata chiedendo
*da chi* protegge, non *se* protegge.

---

### Rompere una guardia apposta ha tre esiti, non due

> Scritto il controllo che verifica che tutti gli eventi siano congelati, l'ho rotto apposta
> aggiungendo un nono evento mutabile. Non è fallito: **la classe non è arrivata a esistere** —
> `TypeError: cannot inherit non-frozen dataclass from a frozen one`. Il controllo scatta e va bene;
> il controllo tace e va corretto; oppure la violazione **non è costruibile**, perché il linguaggio
> la vieta prima. Il terzo somiglia al primo, perché entrambi finiscono con la suite verde, ma
> significa che l'asserzione sta controllando il compilatore.

Fonte: [`app/docs/Sources.md` M-002](../app/docs/Sources.md#m-002),
[registro operativo, nota 144](registro-operativo-sviluppo.md).

**Perché una slide:** è il seguito naturale di «un controllo scritto quando non può fallire va rotto
apposta», e ne mostra il limite. La disciplina di rompere le proprie guardie non basta se poi si
legge il verde come conferma: bisogna sapere quale dei due verdi si sta guardando. E la conseguenza
pratica è controintuitiva — un'asserzione che non può fallire va **tolta**, non lasciata lì «che male
non fa», perché chi la legge crede che stia sorvegliando qualcosa.

---

### Una citazione plausibile è più pericolosa di una mancante

> Scrivendo la documentazione dell'applicazione avevo attribuito a un ADR una regola che quell'ADR
> non contiene, e che **nessun ADR** del repository contiene: è una pratica costante, mai scritta
> come decisione. Il rimando era plausibile, il numero era di un documento vero, e proprio per questo
> nessuno l'avrebbe aperto. Un'affermazione senza fonte è nuda e chi legge sa di doversi fidare
> dell'autore; un'affermazione con accanto un numero sembra già verificata.

Fonte: [ADR-0081](Decision.md#adr-0081),
[registro operativo, nota 146](registro-operativo-sviluppo.md).

**Perché una slide:** in un repository dove citare è la norma, la presenza del rimando diventa il
segnale di qualità e smette di essere una domanda — cioè la disciplina delle fonti produce, come
effetto collaterale, il posto perfetto in cui nascondere un'affermazione non verificata. Vale il
doppio quando si cita a memoria un documento che si è scritto: la fiducia nella propria memoria è più
alta, e la memoria non lo sa. La difesa è banale e va detta ad alta voce — si apre il documento nel
momento in cui si scrive il numero, non dopo.

---

### Un doppio che tace su ciò che non sa è più pericoloso di uno che non c'è

> Un doppio mancante si nota: il codice non compila, la prova non parte. Un doppio che riceve un
> operatore che non conosce e lo **ignora** restituisce un risultato plausibile — tutti i documenti,
> invece di quelli che il filtro avrebbe scelto — e la prova diventa verde per il motivo sbagliato.
> Nessuno ha scritto una riga di codice difettoso: il difetto è nell'attrezzo di misura, che è il
> posto in cui si guarda per ultimo.

Fonte: [`app/docs/Sources.md` M-006](../app/docs/Sources.md#m-006),
[registro operativo, nota 149](registro-operativo-sviluppo.md).

**Perché una slide:** capovolge l'idea intuitiva che un doppio incompleto sia un problema piccolo,
da colmare quando serve. La misura lo mostra: rompendo il filtro dell'archivio in memoria perché
accetti tutto, due delle sette prove rosse falliscono con `DID NOT RAISE` — cioè il **rifiuto** era
provato quanto il comportamento. La regola che ne esce è breve: un doppio dichiara il dialetto che
parla e solleva su tutto il resto, nominando ciò che non sa fare. E quando l'eccezione arriva in
faccia a qualcuno c'è una risposta sola — insegnarglielo insieme alla prova che lo verifica, mai
riscrivere la prova per chiedergli qualcosa di più semplice.

---

### Un errore di *quando* non è un errore di tipo

> «The execution starts when one of the generator's methods is called.»
>
> Una funzione generatrice e una funzione che restituisce un generatore hanno la stessa annotazione,
> `Iterator[T]`. Scritta nella forma sbagliata, la nostra fallisce **una** prova e lascia
> `mypy --strict` **verde**.

Fonte: [`app/docs/Sources.md` A-005](../app/docs/Sources.md#a-005) — Python Language Reference,
*Yield expressions* — e [M-007](../app/docs/Sources.md#m-007),
[registro operativo, nota 151](registro-operativo-sviluppo.md).

**Perché una slide:** è un baco che sopravvive a tutto ciò che di solito rassicura — tipi stretti,
revisione, nome della funzione — perché non sbaglia *che cosa* fa il codice, sbaglia *quando* lo fa.
Un `dump()` scritto con `yield` nel corpo non avvia `mongodump` alla chiamata: lo avvia se e quando
qualcuno scorre il risultato. Il pubblico che scrive Python lo riconosce subito e non ci ha mai
pensato: i sistemi di tipi controllano *che cosa*, quasi mai *quando*.

---

### Anche una riserva è un'affermazione

> Avevo scritto, sotto una misura, che le prove non avrebbero visto un `$limit` che taglia dalla coda
> invece che dalla testa. Sembrava una concessione onesta. Sono andato a guardare: la prova
> asserisce `[1, 2]`, quindi quel taglio lo vede benissimo. L'esempio di lacuna era inventato — e una
> lacuna vera esisteva, due tentativi più in là.

Fonte: [`app/docs/Sources.md` M-006, riserve](../app/docs/Sources.md#m-006),
[registro operativo, nota 152](registro-operativo-sviluppo.md).

**Perché una slide:** è la nota sulla citazione plausibile applicata al proprio codice invece che
alle proprie fonti, e con un'aggravante — la riserva è il punto della pagina che sembra più al riparo
dall'errore, perché è quello in cui l'autore sta ammettendo un limite. Nessuno controlla una
modestia. Il modo di trovare una lacuna vera è **rompere e guardare**, non immaginare; e chi rompe a
caso scopre anche l'altra faccia della cosa, cioè che una guardia scritta per prudenza e mai provata
sopravvive alla revisione ma non alla mutazione.


---

### «p95» da solo non è un numero: sullo stesso campione vale 1,0 oppure 47,55

> Novantacinque latenze da 1 ms, poi 50, 60, 70, 80 e 900. Il novantacinquesimo percentile di questo
> campione vale **1,0** per rango più vicino, **3,45** con `statistics.quantiles(method='inclusive')`,
> **47,55** con `'exclusive'`. Quarantasette volte l'uno dall'altro, e nessuno dei tre sbaglia.

Fonte: [`app/docs/Sources.md` M-009](../app/docs/Sources.md#m-009) e
[A-009](../app/docs/Sources.md#a-009) — «The cut points are linearly interpolated from the two
nearest data points… if a cut point falls one-third of the distance between two sample values, 100
and 112, the cut-point will evaluate to 104» —
[registro operativo, nota 154](registro-operativo-sviluppo.md).

**Perché una slide:** perché «p95» è la parola con cui in sala si chiude una discussione, e la slide
mostra che da sola non chiude niente. I tre numeri rispondono a tre domande diverse: chi **stima** un
quantile della popolazione interpola, e ottiene un valore che nessuno ha misurato; chi **riferisce**
ciò che ha misurato prende un valore osservato, e paga con l'effetto pianerottolo. Il difetto non è
scegliere male: è pubblicare il numero senza dire quale delle due cose si sta facendo.

---

### Zero è la peggiore risposta mancante, perché ha la faccia di una misura

> Un p95 di zero millisecondi su una corsa in cui ogni scrittura è fallita legge «velocissimo» dove
> la verità è «mai arrivato». E a differenza di un'eccezione, non lo dice a nessuno.

Fonte: [registro operativo, nota 155](registro-operativo-sviluppo.md),
[`app/docs/06-carico-tentativi-e-latenze.md`](../app/docs/06-carico-tentativi-e-latenze.md).

**Perché una slide:** è la regola del doppio che solleva, portata dai doppi ai dati. Uno zero al
posto di una misura che non c'è attraversa i controlli di tipo, si somma, si stampa e si media —
sopravvive a tutto ciò che di solito ferma un errore, perché non ha la forma di un errore. La riga
che chiude il punto è breve: dove non c'è una risposta giusta, il tipo deve poter dire di non averla.

---

### C'è un quarto esito, e non è un fallimento: la suite si pianta

> Ho spostato di due righe la garanzia che un thread segnali sempre di aver finito, aspettandomi un
> rosso. La suite si è fermata al 68 % e ci è rimasta. Nessun `FAILED`, nessun messaggio, nessun
> punto del codice indicato: solo un `timeout` e un codice d'uscita.

Fonte: [`app/docs/Sources.md` M-010](../app/docs/Sources.md#m-010),
[registro operativo, nota 153](registro-operativo-sviluppo.md) — che estende la
[nota 144](registro-operativo-sviluppo.md), «rompere una guardia apposta ha tre esiti, non due».

**Perché una slide:** perché arriva **dopo** la slide dei tre esiti, e la corregge in diretta. È il
caso peggiore da leggere non per gravità ma per somiglianza: un blocco senza messaggio somiglia a un
guasto dell'ambiente, e la reazione naturale è sospettare Docker, la rete, il portatile — cioè
cercare il difetto ovunque tranne che nella modifica appena fatta. La regola pratica sta in una riga:
le prove concorrenti si eseguono sotto un `timeout`, sempre.

---

### Il codice di prova va tipizzato più di quello di produzione, non meno

> Un aiutante di tre righe filtrava gli eventi per specie e restituiva il tipo di partenza.
> `mypy --strict` ha bocciato **dieci** asserzioni in un colpo: `"Evento" has no attribute
> "durata_ms"`. A runtime sarebbero passate tutte.

Fonte: [registro operativo, nota 156](registro-operativo-sviluppo.md),
[`app/docs/06-carico-tentativi-e-latenze.md`](../app/docs/06-carico-tentativi-e-latenze.md).

**Perché una slide:** perché il pubblico che scrive Python conosce l'aiutante di tre righe e non lo
rilegge mai. Un filtro che perde il tipo lo perde esattamente dove le asserzioni sono più specifiche,
cioè dove il controllo serviva di più, e lo perde in silenzio. La correzione è una riga di PEP 695 —
`def specie[E: Evento](eventi: list[Evento], tipo: type[E]) -> list[E]` — ma il punto non è la
sintassi: è che quando un aiutante *sa* qualcosa che il chiamante userà, glielo si deve far dire.
---

### Una guardia si prova solo con un caso in cui, se non ci fosse, si vedrebbe

> La prova asseriva che gli eventi escono in ordine di indirizzo. Ho tolto l'ordinamento: è rimasta
> verde. Nel suo scenario i server comparivano già in ordine alfabetico. Osservava il risultato
> giusto per il motivo sbagliato.

Fonte: [registro operativo, nota 159](registro-operativo-sviluppo.md),
[`app/docs/Sources.md` M-011](../app/docs/Sources.md#m-011).

**Perché una slide:** perché è la prova inutile più difficile da riconoscere. Non è sbagliata, non è
incompleta, asserisce esattamente ciò che deve — e non potrebbe fallire. Il pubblico che scrive prove
riconosce all'istante la sensazione, perché la copertura la contava come coperta. La regola sta prima
della prova, nella sua costruzione: si nomina la modifica al codice di produzione che la farebbe
fallire, e se non se ne trova una, il caso scelto è complice.

---

### Il caso pericoloso non è la prova che fallisce: è la prova che non è stata eseguita

> Lo script diceva ventuno su ventuno. Non aveva eseguito una sola prova: un'opzione scritta male
> faceva uscire `pytest` con **4** — errore d'uso — e «diverso da zero» era stato letto come «la
> guardia ha scattato».

Fonte: [registro operativo, nota 157](registro-operativo-sviluppo.md),
[`app/docs/Sources.md` M-011](../app/docs/Sources.md#m-011), che estende
[M-005](../app/docs/Sources.md#m-005) — «nessuna prova raccolta» esce con **5**.

**Perché una slide:** perché il verdetto era il migliore possibile, e per questo nessuno lo avrebbe
messo in dubbio. `pytest` risponde con almeno quattro cose diverse — 0, 1, 4, 5 — e solo l'**1**
significa che una prova ha fallito. Un arnese che classifica esiti elenca i codici che conosce e
tratta come guasto quello che non riconosce. Il segnale d'allarme, in sala come al terminale, è lo
stesso: **un rapporto troppo pulito**.

---

### Due rotture della stessa dimensione, scritte nello stesso secondo, sono la stessa rottura

> Il rapporto attribuiva a due mutazioni diverse la stessa prova fallita, che è un'impossibilità
> logica. Python decide se ricompilare guardando data di modifica **in secondi** e dimensione **in
> byte**: 16 036 e 16 036, nello stesso secondo. La seconda corsa eseguiva il bytecode della prima.

Fonte: [registro operativo, nota 158](registro-operativo-sviluppo.md),
[`app/docs/Sources.md` M-011](../app/docs/Sources.md#m-011).

**Perché una slide:** perché la cache di CPython è pensata per un umano che salva un file ogni tanto,
e uno script di mutazione ne salva venti al minuto — viola entrambe le ipotesi implicite, la
risoluzione dell'orologio e la variazione di lunghezza. Vale oltre Python: **ogni cache ha un
criterio di invalidazione, e va conosciuto prima di metterla in un ciclo automatico.**

---

### Un numero può sbagliare verso il rassicurante, e può sbagliare verso lo spettacolare

> Un'interruzione già in corso al primo sguardo, misurata da lì, dà un minimo: sbaglia per difetto, e
> chi legge lo sospetta. Un'interruzione già chiusa, se ogni sguardo ne spostasse la fine, cresce a
> ogni giro: sbaglia per eccesso, e nessuno lo sospetta — perché il numero grosso conferma la tesi.

Fonte: [registro operativo, nota 160](registro-operativo-sviluppo.md), che continua la
[nota 155](registro-operativo-sviluppo.md),
[`app/docs/07-topologia-failover-e-i-due-numeri.md`](../app/docs/07-topologia-failover-e-i-due-numeri.md).

**Perché una slide:** perché arriva subito dopo lo «zero che sembra una misura» e ne mostra il lato
scomodo. Delle due direzioni dell'errore, l'attenzione ne guarda una sola, ed è quella che non
conviene a chi sta parlando. La riga che chiude: quando un numero finisce su una slide a sostegno di
un'affermazione, la prova che serve è quella che **gli impedirebbe di crescere**.

---

### `IRRAGGIUNGIBILE` è un'osservazione, `SCONOSCIUTO` è l'assenza di un'osservazione

> Un server che sparisce dall'elenco non è un server che ha smesso di rispondere. Nel primo caso
> nessuno l'ha interrogato; nel secondo qualcuno ci ha provato e non ha ottenuto risposta. Metterli
> nello stesso stato significa dire in cronaca che un membro è caduto, quando è stato solo tolto.

Fonte: [`app/docs/07-topologia-failover-e-i-due-numeri.md`](../app/docs/07-topologia-failover-e-i-due-numeri.md).

**Perché una slide:** perché è la stessa disciplina dei doppi che sollevano invece di inventare, e
della latenza che vale `None` invece di zero, applicata a un `enum`. Un tipo che ha uno stato per «non
lo so» permette di non mentire; uno che non ce l'ha costringe a scegliere una bugia plausibile. Dal
palco vale come domanda al pubblico: **quanti dei vostri `enum` hanno lo stato per «non lo so»?**

---

### Un listener lento non rallenta la grafica: rallenta il driver

> «Events are delivered synchronously. Application threads block waiting for event handlers to
> return.» Il thread che aspetta è il monitor, cioè quello che deve accorgersi che il primario è
> caduto. Un callback che disegna una tabella allunga **proprio il failover che sta cronometrando**:
> il numero sulla slide diventa più grande per colpa dello strumento che lo misura.

Fonte: [S-010](Sources.md#s-010), [ADR-0019](Decision.md#adr-0019),
[`app/docs/08-il-ponte-sdam-e-i-thread-del-driver.md`](../app/docs/08-il-ponte-sdam-e-i-thread-del-driver.md).

**Perché una slide:** perché rovescia l'intuizione. Tutti sanno che un'interfaccia lenta è
sgradevole; quasi nessuno si aspetta che una riga di stampa dentro un callback **falsifichi una
misura**. Non è una degradazione delle prestazioni, è un dato sbagliato. Dal palco vale come regola
in tre parole: costruisci, deposita, ritorna.

---

### Il driver fa già quello che ci siamo imposti di fare

> Metà dei listener di PyMongo non vengono chiamati dal codice che scopre il cambiamento: quel
> codice mette in coda, e un thread di nome `pymongo_events_thread` drena e consegna. Lo schema che
> abbiamo scelto per l'applicazione è quello che il driver applica a sé stesso — e nessuna pagina di
> documentazione lo dice.

Fonte: [`app/docs/Sources.md`, M-014](../app/docs/Sources.md#m-014),
[ADR-0019](Decision.md#adr-0019).

**Perché una slide:** perché trasforma una scelta di disegno in una conferma indipendente. Non è il
relatore che consiglia una coda: è quello che fa il codice di chi ha scritto il driver, sotto lo
stesso vincolo. Vale anche come invito: la documentazione di una dipendenza dice che cosa promette,
il suo sorgente dice come vive.

---

### La documentazione diceva microsecondi. Il codice passava secondi

> La docstring dell'evento afferma «the duration of this heartbeat in microseconds». Il valore che
> arriva è una differenza di `time.monotonic()`. Se ci avessimo creduto, ogni battito sarebbe finito
> nella cronaca come 0,000002 ms, e la tabella dei percentili avrebbe mostrato **zeri** — la peggiore
> risposta mancante, prodotta non da una nostra scelta ma da una riga scritta da altri.

Fonte: [`app/docs/Sources.md`, M-012](../app/docs/Sources.md#m-012), che continua la
[nota 155](registro-operativo-sviluppo.md).

**Perché una slide:** perché è il caso concreto della regola «la misura e la fonte si tengono
distinte». Il repository lo prevedeva in astratto da settimane; è la prima volta che la fonte
ufficiale sbaglia davvero. La domanda al pubblico si scrive da sé: **quante delle unità di misura
che usate le avete lette, e quante verificate?**

---

### Una rottura che non rompe

> Abbiamo cambiato una riga apposta, e la suite è rimasta verde. La prima ipotesi — manca una prova —
> era falsa: le due scritture erano **la stessa lettura per due strade**, perché il driver garantisce
> che quei due valori coincidano. Inventare una prova per farla fallire avrebbe aggiunto copertura
> senza aggiungere verità.

Fonte: [registro operativo, nota 161](registro-operativo-sviluppo.md),
[`app/docs/Sources.md`, M-016](../app/docs/Sources.md#m-016).

**Perché una slide:** perché è la trappola del testing per mutazione, e chi usa quegli strumenti la
incontrerà. Una mutazione sopravvissuta non significa sempre «prova mancante»: può significare
«mutazione equivalente», e la differenza è tutta. La riga da tenere: **prima di concludere che manca
una guardia, escludi che manchi la differenza.**

---

### Una soglia che non dichiara che cosa non prende è una riserva non scritta

> La prova chiede che il callback costi meno di dieci volte un inserimento in coda. Il caso onesto
> sta a 2,9; una tabella di Rich arriva a 883. In mezzo c'è una `f-string` a 5,5, che il codice
> vieta e la prova **lascia passare**. È scritto accanto alla prova, perché una soglia scelta e non
> spiegata lascia credere che la copertura arrivi fino al divieto.

Fonte: [registro operativo, nota 162](registro-operativo-sviluppo.md),
[`app/docs/Sources.md`, M-013](../app/docs/Sources.md#m-013).

**Perché una slide:** perché ogni progetto ha una soglia scritta a occhio, e nessuno ricorda più da
dove venga. Le due metà della regola stanno in una frase: si misura prima di scriverla, e si
dichiara che cosa resta fuori. Il resto è il motivo per cui non si stringe: una prova che fallisce a
caso viene disattivata da qualcuno, prima o poi.

---

### Il terzo stato dell'assenza: quando il client sa benissimo, e la scena non lo nomina

> `SCONOSCIUTO` è l'assenza di un'osservazione. `IRRAGGIUNGIBILE` è un'osservazione. `ALTRO` è il
> contrario di entrambi: il client ha capito perfettamente che cosa ha davanti, ed è qualcosa che
> questa storia non racconta. Un membro che riparte è `RSOther` per qualche secondo — e sono
> esattamente i secondi in cui la sala guarda quella riga.

Fonte: [`app/docs/08-il-ponte-sdam-e-i-thread-del-driver.md`](../app/docs/08-il-ponte-sdam-e-i-thread-del-driver.md).

**Perché una slide:** perché completa la coppia della slide precedente e mostra che gli stati «non
so» sono più di uno. Il valore di ripiego di una traduzione è una decisione, non un dettaglio:
mandare l'ignoto e il fuori-scena nello stesso posto fa scrivere «non so» proprio nel momento in cui
si sapeva.

---

### Un doppio che si comporta diversamente dall'originale è un doppio che mente

> Ogni volta che una prova passa contro il doppio, chi la legge conclude qualcosa sul comportamento
> contro il database vero. Quella conclusione vale quanto la somiglianza fra i due — e la
> somiglianza non l'aveva mai misurata nessuno.

Fonte: [`app/docs/09-adattatori-veri-e-contratto-condiviso.md`](../app/docs/09-adattatori-veri-e-contratto-condiviso.md).

**Perché una slide:** perché in sala c'è chi ha una suite verde di doppi e la considera una
garanzia. La frase non dice di buttarli: dice che la fedeltà è una quantità, che oggi vale un
numero — dodici comportamenti verificati da entrambe le parti — e che senza quel numero la suite
verde è una fiducia, non una misura.

---

### Il contratto ha trovato il bugiardo prima che l'originale esistesse

> Il file condiviso è stato scritto per girare in due posti, ed è bastato eseguirlo in **uno**.
> Prima esecuzione, contro il solo doppio: `1 failed, 10 passed`. Un difetto che stava lì da quattro
> task, invisibile perché nessuna prova aveva mai chiesto quel caso.

Fonte: [registro operativo, nota 163](registro-operativo-sviluppo.md),
[`app/docs/Sources.md`, M-017](../app/docs/Sources.md#m-017).

**Perché una slide:** perché ribalta l'aspettativa. Ci si prepara al confronto con il server vero e
il difetto salta fuori prima, per una ragione che vale in generale: scrivere una verifica pensando
«deve valere anche contro l'originale» costringe a formularla in termini di comportamento
osservabile, e le domande che ne escono sono diverse da quelle che si pongono guardando il doppio.

---

### `$count` su zero documenti non risponde zero: non risponde

> `risultato[0]["quanti"]` dà **0** sul doppio e **`IndexError`** contro MongoDB. La suite veloce
> resta verde. La demo si rompe al primo fotogramma, quando la collezione è ancora vuota.

Fonte: [`app/docs/Sources.md`, M-017](../app/docs/Sources.md#m-017).

**Perché una slide:** perché è la trappola SQL più economica da mostrare. `COUNT(*)` su zero righe
dà zero; una pipeline di aggregazione su zero documenti non emette niente, e nemmeno `$group` con
`_id: null` lo fa. Chi arriva da SQL scrive la riga sbagliata al primo tentativo, e non se ne accorge
finché la collezione non è vuota davvero.

---

### `limit(0)` non vuol dire «nessun documento», vuol dire «nessun limite»

> «A `limit()` value of 0 (i.e. `.limit(0)`) is equivalent to setting no limit.» Il valore non lo
> digita nessuno: ci si arriva per sottrazione — quanti mancano alla fine dell'elenco — cioè nel
> caso limite di un calcolo, che è quello che nessuno prova a mano.

Fonte: [`app/docs/Sources.md`, A-011](../app/docs/Sources.md#a-011) e
[M-022](../app/docs/Sources.md#m-022).

**Perché una slide:** perché è una fonte che inverte l'ovvio in una riga, e la conseguenza è
spettacolare: cinquantamila righe che scorrono dove ne erano state chieste zero. In più mostra la
tecnica — la guardia è stata scritta dopo aver visto la stessa verifica passare da una parte e
fallire dall'altra.

---

### Un replica set sano, guardato da fuori, si legge «nessun primario»

> Quattro secondi e due decimi, `ReplicaSetNoPrimary`, tutti e tre i membri irrisolvibili. Il set
> risponde con i nomi di servizio della rete Compose, che dentro esistono e fuori no. È
> indistinguibile da un primario caduto davvero.

Fonte: [`app/docs/Sources.md`, M-019](../app/docs/Sources.md#m-019),
[ADR-0021](Decision.md#adr-0021).

**Perché una slide:** perché è ADR-0021 visto dal lato che fa male, ed è l'errore che chiunque
provi un replica set in Docker incontra il primo giorno. La parte che la rende una slide e non un
aneddoto: la diagnosi sbagliata **è la stessa** che il talk mostra come diagnosi giusta nel Blocco 2.
Stesso messaggio, due cause opposte.

---

### Il difetto che non fallisce è l'unico che giustifica una guardia

> `tz_aware` è predefinito a `False`. Le date tornano ingenue, il confronto con quelle scritte
> riesce lo stesso, e lo sbaglio si vede come un orario storto sullo schermo — sbagliato di quante
> ore vale il fuso.

Fonte: [`app/docs/09-adattatori-veri-e-contratto-condiviso.md`](../app/docs/09-adattatori-veri-e-contratto-condiviso.md).

**Perché una slide:** perché dà un criterio, non un consiglio. Le guardie difensive si moltiplicano
finché non si sa quando smettere; la regola per smettere è questa — si mette una guardia dove
l'alternativa non è un errore ma un risultato plausibile e sbagliato.

---

### Zero chunk su uno shard che ne ha due

> Su 7.0.40 nessun chunk ha il campo `ns`, e cercarlo restituisce zero **senza sollevare**. Zero
> chunk è la conclusione «i dati non sono distribuiti», detta esattamente nel momento in cui lo sono.

Fonte: [`app/docs/Sources.md`, M-020](../app/docs/Sources.md#m-020) e
[A-013](../app/docs/Sources.md#a-013).

**Perché una slide:** perché è il difetto silenzioso in forma pura, sul tema del Blocco 3. E perché
la correzione è didattica quanto il difetto: il manuale prescrive di unire per `uuid`, e non afferma
da nessuna parte che `ns` sia stato tolto — la prima cosa è una fonte, la seconda una misura, e
scriverle come se fossero la stessa cosa è come nascono le leggende.

---

### Misurare quello che tutti consigliano

> `ordered=False` è la raccomandazione standard per il caricamento massivo. Ventimila documenti per
> configurazione, tre giri alternati: mediane fra 2,48 e 2,70 ms **da entrambe le parti**. Due
> minuti per misurarlo. Una riga che nessuno avrebbe più rimesso in discussione, per non misurarlo.

Fonte: [registro operativo, nota 165](registro-operativo-sviluppo.md),
[`app/docs/Sources.md`, M-021](../app/docs/Sources.md#m-021).

**Perché una slide:** perché il caso della soglia inventata a occhio è noto, e questo è quello
complementare e più insidioso: non c'è un numero da inventare, c'è un consenso da ereditare. Vale
anche la riserva, che è metà della slide: la misura è su loopback e istanza singola, e le tre
condizioni in cui potrebbe ribaltarsi — rete, `w: majority`, sharding — sono tutte fuori.

---

### Le prove accendono lo stack che il pubblico eseguirà, non un facsimile

> Da `make down-01` a diciannove prove verdi in 8,1 secondi, senza che nessuno digiti `make up-01`.
> E alla fine gli stack restano accesi: fermare uno stack che l'operatore aveva già su sarebbe un
> effetto che le prove non hanno causato.

Fonte: [ADR-0020](Decision.md#adr-0020),
[`app/docs/09-adattatori-veri-e-contratto-condiviso.md`](../app/docs/09-adattatori-veri-e-contratto-condiviso.md).

**Perché una slide:** perché la scelta di non usare testcontainers va giustificata, e la
giustificazione è di una riga: un container di prova configurato altrove sarebbe verde mentre lo
stack del lab è rotto. La seconda metà — quello che le prove smontano sono i **dati**, non
l'infrastruttura — è la regola pratica che rende sopportabile la prima.

---

### Lo strumento che ha perso cinquantamila documenti ed è uscito zero

> `mongorestore` ha dichiarato `0 document(s) restored successfully. 50000 document(s) failed to
> restore.` e ha restituito **0** al sistema operativo. Chi controlla il processo nel modo in cui si
> controlla un processo riceve «riuscito».

Fonte: [ADR-0084](Decision.md#adr-0084), [`app/docs/Sources.md`, M-024](../app/docs/Sources.md#m-024).

**Perché una slide:** perché il codice d'uscita è il modo in cui *tutti* controllano un processo
esterno, e questo è un caso in cui mente — non un caso limite costruito ad arte, ma il secondo giro
di qualunque restore sulla stessa destinazione. La morale sta in una riga: quando lo strumento di
qualcun altro non dà il verdetto, l'adattatore che lo incapsula è il posto in cui si ripara.

---

### La lista di argomenti non basta: `argv` è pubblico comunque

> La tabella dei processi legge `argv`, e ad `argv` non importa da dove è arrivato. Con `-p` nella
> lista, senza nessuna shell di mezzo, `ps` dentro il container mostra la password
> dell'amministratore per tutto il tempo in cui il dump gira.

Fonte: [`app/docs/Sources.md`, M-025](../app/docs/Sources.md#m-025),
[`app/docs/10-processi-esterni-e-il-verdetto-che-manca.md`](../app/docs/10-processi-esterni-e-il-verdetto-che-manca.md).

**Perché una slide:** perché «usa la lista, non la stringa di shell» è il consiglio che tutti danno
e che tutti fermano un passo prima. La lista serve — protegge dagli spazi e dagli apici, non dagli
occhi. Il segreto si tiene fuori da `argv`, e per `mongodump` la strada è omettere `-p` e scrivere
la password sullo `stdin`, che lo strumento legge anche quando non è un terminale.

---

### La prova diceva una cosa falsa, e a scoprirlo è stato il codice

> Avevo scritto, nella docstring di una prova, che un restore ripetuto è idempotente. Non lo è:
> `mongorestore` inserisce, e il secondo giro collide su ogni `_id`. L'adattatore ha sollevato, e la
> parte sbagliata era la mia premessa.

Fonte: [registro operativo, Task 9](registro-operativo-sviluppo.md),
[`app/docs/Sources.md`, M-024](../app/docs/Sources.md#m-024).

**Perché una slide:** perché rovescia l'immagine abituale — la prova che giudica il codice — e mostra
l'altro verso, che capita più spesso di quanto si ammetta. Una docstring di prova è un'asserzione
come le altre, scritta nel punto in cui nessuno la rilegge, e un codice che solleva quando non te lo
aspetti è la cosa più vicina a una revisione paritaria che si possa avere alle undici di sera.

---

### Una promessa mantenuta per caso è una promessa che nessuno sta controllando

> Un ADR di questo repository prometteva «un solo thread tocca `Live`». Con le impostazioni
> predefinite di Rich i thread erano **due**: `Live.start()` ne avvia uno demone che ridisegna per
> conto suo. Non succedeva niente di male — dentro `Live` c'è un lucchetto — e proprio per questo
> la promessa sarebbe rimasta scritta, falsa, finché qualcosa non avesse smesso di funzionare.

Fonte: [`app/docs/Sources.md`, M-027](../app/docs/Sources.md#m-027) e
[A-015](../app/docs/Sources.md#a-015), [ADR-0085](Decision.md#adr-0085).

**Perché una slide:** perché è il caso peggiore di tutti — l'assunzione sbagliata che *funziona*.
Un'assunzione sbagliata che rompe qualcosa si scopre da sola; una che regge grazie a una protezione
altrui, di cui non si sapeva niente, si scopre solo andando a guardare. E ci si va a guardare
soltanto se si prende sul serio l'idea che «corretto per caso» e «corretto per costruzione» siano
due stati diversi del software, non due modi di dire la stessa cosa.

---

### Quando una decisione si giustifica con un silenzio, quel silenzio va misurato

> La documentazione di Rich non nomina mai i thread. Il progetto aveva letto quel silenzio come
> «non ce ne sono» e ci aveva costruito sopra un ADR. Le due letture di un silenzio sono «non
> succede» e «non è documentato», e la seconda è quasi sempre quella giusta.

Fonte: [`docs/Sources.md`, S-018](Sources.md#s-018),
[`app/docs/Sources.md`, A-015](../app/docs/Sources.md#a-015),
[registro operativo, nota 173](registro-operativo-sviluppo.md).

**Perché una slide:** perché la reazione prudente a una lacuna — cambiare disegno invece di
indovinare — era quella giusta, e non è bastata. Quello che è stato scritto accanto alla scelta non
era prudenza, era una proprietà attribuita a una libreria senza verificarla. Se una lacuna è
abbastanza importante da entrare in una decisione, è abbastanza importante da farsi cinque minuti
di sorgente installato: sta sul disco, si apre, risponde.

---

### Il numero c'era. La misura no

> Nella docstring che giustificava il ritmo di aggiornamento avevo scritto «0,86 ms misurati», con
> accanto un codice `M-0NN` perfettamente formato che rimandava a una misura che non esisteva
> ancora. Quando l'ho fatta davvero, la misura smentiva il segnaposto del 35%.

Fonte: [`app/docs/Sources.md`, M-028](../app/docs/Sources.md#m-028),
[registro operativo, nota 174](registro-operativo-sviluppo.md).

**Perché una slide:** è il seguito esatto di *«Una citazione plausibile è più pericolosa di una
mancante»*, un giro più in là. Un repository con una regola severa sulle fonti si difende benissimo
dal numero **senza** citazione: la mancanza salta all'occhio, perché la regola esiste apposta. Non
si difende affatto dal numero scritto insieme a una citazione conforme che si ha intenzione di
onorare dopo. La conformità della forma è precisamente ciò che ferma la rilettura — la disciplina
delle fonti costruisce, come effetto collaterale, il nascondiglio migliore per un dato inventato.
La regola pratica sta in una riga: la citazione si scrive **dopo** la fonte, mai prima.

---

### Otto righe riservate a server che non esistono

> Avevo riservato otto righe della schermata all'elenco dei server, giustificandole così: «due
> shard da due membri, tre config server, un `mongos`». Gli shard di membri ne hanno tre. E
> soprattutto: la tabella non elenca i container dello stack, elenca quello che il **driver** vede,
> e un client collegato a un `mongos` vede il `mongos`. Il numero vero è tre.

Fonte: [`app/docs/Sources.md`, M-029](../app/docs/Sources.md#m-029),
[registro operativo, nota 175](registro-operativo-sviluppo.md).

**Perché una slide:** perché mostra la differenza fra un errore di conteggio e un errore di
modello, e quale dei due sopravvive. Un numero nudo invita a chiedere «da dove viene?»; un numero
con una derivazione plausibile scritta accanto **chiude** la domanda, e la chiude per anni. Vale
anche come promemoria su MongoDB sharded, che è il punto in cui l'intuizione tradisce più spesso:
la topologia che il client conosce non è la topologia del cluster, ed è per questo che i conteggi
per shard si chiedono a `$shardedDataDistribution` e non alla lista dei server.

---

### Un elenco troncato in silenzio si legge come un cluster più piccolo di quello che è

> Mostrare tre server su cinque senza dirlo non produce una schermata incompleta: produce una
> schermata che afferma il falso. Chi guarda legge «il cluster ha tre membri», e non ha modo di
> sospettare il contrario. Il costo di dirlo è una riga: «… e altri 2».

Fonte: [`app/docs/11-tre-rese-e-un-solo-thread-che-disegna.md`](../app/docs/11-tre-rese-e-un-solo-thread-che-disegna.md),
[registro operativo, nota 178](registro-operativo-sviluppo.md).

**Perché una slide:** perché ogni cruscotto, ogni `top`, ogni pagina di risultati ha un budget di
spazio e quindi tronca, e quasi nessuno dichiara di averlo fatto. In una dimostrazione dal vivo
questo conta il doppio: la schermata proiettata è l'unica prova che il pubblico ha, e un'omissione
non dichiarata diventa un'affermazione. Il dato più importante fra quelli che stanno per essere
nascosti è **quanti** ne vengono nascosti.

---

### Un divieto di provare si onora spostando ciò che va provato, non rinunciando a provarlo

> «Non provare la TUI» significa «non provare Rich», e Rich ha già le sue prove. Non significa che
> le decisioni prese lì dentro restino senza guardia. Rompendo il codice una riga alla volta, le
> due sole mutazioni sopravvissute su undici erano nel modulo che il divieto proteggeva — ed erano
> le due righe che il resto del progetto cita.

Fonte: [`app/docs/11-tre-rese-e-un-solo-thread-che-disegna.md`](../app/docs/11-tre-rese-e-un-solo-thread-che-disegna.md),
[registro operativo, nota 177](registro-operativo-sviluppo.md).

**Perché una slide:** perché «questo non si prova» è una frase che in ogni progetto copre due cose
molto diverse — ciò che davvero non ha senso provare, e ciò che è scomodo. La domanda che le separa
è *che cosa esattamente vieta il divieto*: qui vietava di guardare i pixel, non di contare i thread
o di chiedere se una coda è vuota. Le due mutazioni sopravvissute stavano proprio lì, ed è un esito
che si ripete: le righe senza guardia tendono a essere quelle su cui poggia la documentazione.

---

### Una suite verde non prova che il programma sia mai stato eseguito

> 425 prove unitarie, 43 d'integrazione, `mypy --strict` su 57 file: tutto verde. Poi lo stack è
> stato acceso, e due comandi su tre erano sbagliati. Nessuno dei due difetti apparteneva a un
> componente: uno stava fra un generatore che numera da zero e una collezione già numerata, l'altro
> fra due osservatori della stessa struttura. Le prove di componente non possono vedere le
> giunture.

Fonte: [`app/docs/12-la-radice-di-composizione-e-la-prima-esecuzione-vera.md`](../app/docs/12-la-radice-di-composizione-e-la-prima-esecuzione-vera.md),
[registro operativo, nota 179](registro-operativo-sviluppo.md).

**Perché una slide:** perché la copertura è la metrica che si mostra, e questa è la sua ombra. Un
difetto di giuntura non ha un file in cui vive, quindi non ha un file in cui provarlo, quindi non
compare in nessun rapporto di copertura — e resta l'unico che una demo dal vivo rivelerà, davanti a
tutti. Il rimedio non è più prove: è mettere in conto la prima esecuzione contro l'ambiente vero
come un **passo del lavoro**, non come una formalità dopo il commit.

---

### Il guasto da temere non è quello che solleva: è quello che esce con zero

> Il carico rotto usciva con codice zero. La cronaca scorreva, 4 833 letture su 4 833 riuscivano,
> lo schermo era pieno di attività. Solo una riga del consuntivo diceva la verità: «38 scritture, 0
> confermate». Dal fondo della sala era una demo che funziona.

Fonte: [`app/docs/Sources.md`, M-032](../app/docs/Sources.md#m-032),
[ADR-0088](Decision.md#adr-0088), [registro operativo, nota 180](registro-operativo-sviluppo.md).

**Perché una slide:** perché è successo tre volte in questo progetto e ogni volta con una faccia
diversa — un `mongorestore` che perde documenti e esce zero ([ADR-0084](Decision.md#adr-0084)), una
latenza negativa che entra nei percentili ([ADR-0086](Decision.md#adr-0086)), un carico che non
scrive niente e sembra lavorare. Un'eccezione si vede; un numero plausibile no. La domanda pratica
da portare via: **quale numero di questo consuntivo sarebbe zero se tutto fosse rotto?** — e poi
guardarlo.

---

### Su uno stesso fatto, un narratore solo

> `watch` raccontava ogni transizione due volte. PyMongo la emette una volta sola: a raddoppiarla
> erano due osservatori nostri sulla stessa struttura, uno che riceve i callback e uno che
> interroga ogni mezzo secondo. Uno spinto e uno tirato: non era un rischio, era una certezza.

Fonte: [`app/docs/Sources.md`, M-033](../app/docs/Sources.md#m-033),
[ADR-0089](Decision.md#adr-0089), [registro operativo, nota 182](registro-operativo-sviluppo.md).

**Perché una slide:** perché la cura sbagliata è la prima che viene in mente — deduplicare a valle
— e in un contesto di failover è peggio della malattia: due transizioni identiche e ravvicinate
sono anche la firma di un membro che *flappa*, cioè esattamente la cosa che si sta cercando di
mostrare. Un filtro non sa distinguere il doppione dal fatto ripetuto. Si guarisce togliendo un
osservatore. Vale per ogni cruscotto che unisce una fonte a eventi e una fonte a polling, che è
quasi ogni cruscotto.

---

### L'orologio da parete non promette di andare avanti, e lo dichiara

> `time.get_clock_info("time")` risponde `monotonic=False, adjustable=True`. È scritto, si legge in
> una riga, e quasi nessuno lo legge prima di sottrarre due `datetime.now()` e chiamare il
> risultato «latenza». Quando NTP corregge una deriva, quella sottrazione dà un numero negativo —
> che non solleva niente, ed entra nei percentili.

Fonte: [`app/docs/Sources.md`, M-030](../app/docs/Sources.md#m-030),
[ADR-0086](Decision.md#adr-0086), [registro operativo, nota 184](registro-operativo-sviluppo.md).

**Perché una slide:** perché misurare una latenza è la cosa che chiunque in sala fa tutte le
settimane, ed è il caso in cui l'implementazione ovvia di un'astrazione ovvia sbaglia. La domanda
che separa i due usi è una sola: *questo istante lo devo datare o lo devo sottrarre?* Datare vuole
l'ora vera, sottrarre vuole un contatore che non torna indietro, e un `datetime.now()` fa bene solo
la prima. Un'ancora letta una volta più un contatore monotono fa bene entrambe.

---

### Un valore predefinito comodo è un errore silenzioso in attesa

> `--target` non ha un predefinito, e non lo avrà. Durante il talk si cambia stack tre volte: con
> un predefinito, una distrazione manda il carico al bersaglio sbagliato — e quel comando non
> fallisce. **Riesce**, altrove.

Fonte: [`app/docs/12-la-radice-di-composizione-e-la-prima-esecuzione-vera.md`](../app/docs/12-la-radice-di-composizione-e-la-prima-esecuzione-vera.md),
[ADR-0087](Decision.md#adr-0087), [registro operativo, nota 185](registro-operativo-sviluppo.md).

**Perché una slide:** perché il criterio è generale e si enuncia in una riga — *se sbagliare il
predefinito produce un errore visibile, mettilo; se produce un risultato plausibile ma di un'altra
cosa, non metterlo* — e perché nel mondo dei database questo caso ha una versione famosa: il
`--host` che, mancando, punta a `localhost`. La stessa severità vale per gli strumenti attorno: qui
`make app-stats` senza `TARGET` esce con **2** invece di indovinare, che è lo stesso codice con cui
Typer rifiuta un parametro sbagliato.

---

### La stringa di connessione non è un indirizzo: è un punto di partenza

> La specifica che tutti i driver MongoDB implementano definisce la *seed list* come «server
> addresses provided client in initial configuration», e prescrive che il client **MUST add**
> i server che gli altri membri gli nominano. Misurato: un seme solo, `mongo-rs-2`, e il client
> finisce per scrivere su `mongo-rs-1` — un nome che nessuno gli aveva dato.

Fonte: [`app/docs/Sources.md`, A-016](../app/docs/Sources.md#a-016) e
[M-036](../app/docs/Sources.md#m-036), [ADR-0012](Decision.md#adr-0012),
[registro operativo, nota 187](registro-operativo-sviluppo.md).

**Perché una slide:** perché è la cosa che tutti hanno scritto mille volte senza pensarci — un URI
in un file di configurazione — e quasi nessuno sa che quell'indirizzo è **solo l'inizio**. Da lì
discendono conseguenze pratiche molto concrete: perché un firewall aperto sul solo seme non basta,
perché i nomi che il set restituisce devono essere risolvibili dal client, e perché la stessa
applicazione che funziona dentro Docker non funziona da fuori. Una demo che parte da un seme
secondario e finisce a scrivere sul primario lo mostra in dieci secondi.

---

### Lo stesso cluster ha due indirizzi, e dal lato sbagliato la verità non è raggiungibile

> Da fuori la rete Compose, un replica set con tre membri sani si legge `ReplicaSetNoPrimary`. Per
> farlo funzionare bisogna spegnere la scoperta con `directConnection=true` — e allora la topologia
> si legge `singola` mentre il ruolo del server è `RSPrimary`. Due affermazioni false insieme,
> nessuna delle quali solleva un errore.

Fonte: [`app/docs/Sources.md`, M-019](../app/docs/Sources.md#m-019),
[`app/docs/13-il-container-sulla-rete-e-la-scoperta-che-si-vede.md`](../app/docs/13-il-container-sulla-rete-e-la-scoperta-che-si-vede.md),
[ADR-0012](Decision.md#adr-0012), [ADR-0090](Decision.md#adr-0090).

**Perché una slide:** perché è la trappola in cui cade chiunque provi un replica set in Docker dal
proprio portatile, e perché la reazione naturale — mettere `directConnection=true` finché non
funziona — non ripara niente: nasconde. Il cluster non è raggiungibile «un po' meno bene» da fuori;
è raggiungibile in un modo che **non è quello che l'applicazione userà in produzione**. La
conseguenza operativa è che una demo di failover ha senso solo dal lato in cui la scoperta è accesa.

---

### Una prova che non potrebbe fallire non dimostra niente, anche quando passa

> Misurare la scoperta dei membri partendo dai tre semi della configurazione è circolare: trovare
> tre server avendone dati tre è compatibile con un driver che non scopre nulla. Il disegno che
> dimostra è un seme solo, scelto fra i **non** primari.

Fonte: [`app/docs/Sources.md`, M-036](../app/docs/Sources.md#m-036),
[registro operativo, nota 187](registro-operativo-sviluppo.md).

**Perché una slide:** perché vale per ogni prova, non solo per le misure sui driver, e perché la
domanda che la rende operativa sta in una riga: *quale osservazione falsificherebbe questa
asserzione?* Se non ce n'è nessuna, la prova è verde per costruzione. È la stessa idea che rende
obbligatorio far fallire una prova almeno una volta prima di fidarsene — qui applicata a un
esperimento invece che a un test.

---

### Una premessa plausibile e mai verificata sopravvive a tutte le revisioni

> «Un'immagine costruita in locale non ha un digest» suona ovvio ed è falso: con l'archivio immagini
> di containerd, l'`Id` di un'immagine **è** il digest del suo manifesto, anche per ciò che nessuno
> ha mai pubblicato. Era già scritta in cinque posti quando un `docker image inspect` l'ha smentita.

Fonte: [`app/docs/Sources.md`, M-037](../app/docs/Sources.md#m-037),
[ADR-0093](Decision.md#adr-0093), [registro operativo, nota 188](registro-operativo-sviluppo.md).

**Perché una slide:** perché la decisione presa su quella premessa era **giusta** — il digest di
un'immagine costruita in casa non va in `images.env` — e questo è precisamente ciò che rende
l'errore interessante: una motivazione sbagliata sotto una conclusione corretta non viene corretta
da niente, perché niente si rompe. E c'è l'aggravante che con il vecchio archivio a grafo di Docker
la premessa sarebbe stata vera per caso. Le frasi che cominciano con «ovviamente» sono candidate a
diventare una misura.

---

### Prima di segnare chiuso un punto aperto, guardare se lo è

> Il registro dava per chiuso il limite del `docker exec` sul dump, con una motivazione scritta tre
> task prima: «dal container non c'è più nessun `docker exec` in mezzo». Un comando ha mostrato che
> nell'immagine `mongodump` non c'è affatto.

Fonte: [`app/docs/Sources.md`, M-039](../app/docs/Sources.md#m-039),
[registro operativo, nota 193](registro-operativo-sviluppo.md).

**Perché una slide:** perché ogni progetto tiene un elenco di cose «da sistemare al prossimo giro»,
e le scadenze scritte lì dentro sono **previsioni**, non fatti. Un punto chiuso per inerzia è
peggio di un punto aperto: sparisce dall'elenco e riappare quando c'è pubblico. Il costo di
verificarlo, qui, è stato un comando di una riga.

---

### Una scena che gira non è una scena che dice il vero

> Fra un failover mostrato e un failover finto non c'è nessuna differenza visibile: le fasi
> scorrono uguali, il carico riprende uguale. La differenza sta in due numeri — e se il guasto
> non è arrivato, quei due numeri dicono «interruzione zero, scritture perse zero», cioè
> **failover perfetto**.

Fonte: [`app/docs/Sources.md`, M-043](../app/docs/Sources.md#m-043),
[ADR-0096](Decision.md#adr-0096), [registro operativo, nota 197](registro-operativo-sviluppo.md).

**Perché una slide:** perché è la giustificazione di tutto il Blocco 2, e vale ben oltre le demo.
Un'operazione fallita che produce un risultato *plausibile* invece di un errore è la peggiore
categoria di guasto che esista: nessuno la cerca, perché niente sembra rotto. Da qui la scelta di
far **fermare** la scena quando `docker compose kill` esce diverso da zero, e quella di confrontare
i numeri dell'applicazione con una misura fatta settimane prima per un'altra strada.

---

### «Fermare un nodo» non è un'operazione sola, e spegnere bene è venti volte più rapido

> `docker compose stop` manda `SIGTERM`, e `mongod` cede il ruolo prima di uscire: **574, 480, 486
> ms**, senza nessuna elezione. `docker kill` lo fa sparire senza cedere niente: **9 812, 10 619,
> 10 943 ms**, e il replica set deve votare.

Fonte: [V-029](Sources.md#v-029), [V-031](Sources.md#v-031),
[ADR-0097](Decision.md#adr-0097).

**Perché una slide:** perché va contro l'intuizione di tutti — «staccare la spina» dovrebbe essere
la strada rapida, e invece è venti volte la più lenta — e perché spiega in una riga *perché* esiste
un'elezione. Il primario che si spegne con ordine **dice** di andarsene; quello che sparisce va
scoperto assente, e scoprirlo costa. È anche l'unico punto in cui il piano di questo progetto ha
avuto torto contro una misura, e la correzione è stata scritta invece che applicata in silenzio.

---

### Guardare non è aspettare

> Contro un replica set sanissimo, il comando usciva con «nessun primario in vista». Non era il
> cluster: la topologia che il driver espone è la descrizione che **ha già**, e nei primi
> millisecondi dopo la connessione è vuota, perché la scoperta comincia in quel momento.

Fonte: [`app/docs/Sources.md`, M-042](../app/docs/Sources.md#m-042),
[`app/docs/Sources.md`, A-017](../app/docs/Sources.md#a-017),
[registro operativo, nota 198](registro-operativo-sviluppo.md).

**Perché una slide:** perché una lettura pura e una chiamata bloccante hanno la stessa firma e
sembrano intercambiabili — e contro un doppio lo **sono**, perché il doppio risponde subito.
Cinquecento prove verdi non hanno visto niente. La correzione è una riga, `admin.command("ping")`,
e funziona per un motivo che vale la pena dire: un comando su `admin` va sul primario per
impostazione predefinita, quindi la selezione del server **è** l'attesa.

---

### Nessuno qui ha chiesto `majority`: è il server che ha scelto bene

> Il write concern del client è vuoto — l'applicazione non chiede niente. Il `w: majority` che
> salva le 15 229 scritture arriva dal server come default **implicito**, e
> `getDefaultRWConcern` lo dichiara.

Fonte: [`app/docs/Sources.md`, M-041](../app/docs/Sources.md#m-041),
[V-016](Sources.md#v-016), [registro operativo, nota 202](registro-operativo-sviluppo.md).

**Perché una slide:** perché è la differenza fra una frase vera e una falsa che si somigliano
molto. «Zero scritture perse» è misurato; «la mia applicazione usa `w: majority`» sarebbe
inventato. E la versione corretta è più utile, perché è prevedibile: da MongoDB 5.0 il default
implicito è `majority`, quindi chi non tocca niente è protetto — e chi ha impostato un default di
cluster più debole, o chiede `w: 1` esplicitamente, vede l'altro numero
([V-016](Sources.md#v-016): cento perse).

---

### Quando due requisiti legittimi non stanno nello stesso processo, il vincolo è la lezione

> La cronaca dell'elezione si vede solo da **dentro** la rete Compose. Il comando che uccide il
> primario si può dare solo da **fuori**, perché il container non ha il socket del demone — e non
> deve averlo. Un processo solo non può fare questa scena.

Fonte: [ADR-0095](Decision.md#adr-0095),
[`app/docs/Sources.md`, M-043](../app/docs/Sources.md#m-043),
[registro operativo, nota 195](registro-operativo-sviluppo.md).

**Perché una slide:** perché la scorciatoia era a portata di mano — montare `/var/run/docker.sock`
nel container — e sarebbe stata proiettata in sala, insegnando senza dirlo il modo più diretto di
prendere la macchina che ospita. Dichiarare il verbo come una porta e darle due implementazioni,
una che esegue e una che **annuncia e aspetta un umano**, ha lasciato intatti entrambi i vincoli e
ha reso visibile quello che conta.

---

### Una banda larga scelta apposta prova più di una soglia stretta

> La prova accetta un'interruzione fra 5 e 15 secondi, non i 10 019 ms misurati. Quello che deve
> intercettare è l'errore di **categoria**: zero, cioè il guasto non è arrivato; sessanta secondi,
> cioè l'elezione non è avvenuta.

Fonte: [`app/docs/Sources.md`, M-043](../app/docs/Sources.md#m-043),
[registro operativo, nota 201](registro-operativo-sviluppo.md).

**Perché una slide:** perché è il rimedio a una malattia comune delle suite — la soglia stretta su
un numero misurato una volta, che fallisce sul portatile di qualcun altro e viene spenta entro un
mese. La distinzione utile è fra ciò che la suite deve **impedire** e ciò che il registro deve
**ricordare**: il numero preciso vive nel registro delle misure, la prova sorveglia la categoria.

---

### Una finestra più larga dell'evento è una misura che non può smentire la propria tesi

> Il dump dura mezzo secondo. Se lo misuri su venti, un crollo totale del throughput ti compare
> come un calo del due per cento — e la tua tesi risulta confermata da un numero incapace di
> smentirla.

Fonte: [ADR-0101](Decision.md#adr-0101),
[`app/docs/Sources.md`, M-045](../app/docs/Sources.md#m-045),
[`app/docs/Sources.md`, M-047](../app/docs/Sources.md#m-047),
[registro operativo, nota 204](registro-operativo-sviluppo.md).

**Perché una slide:** perché è l'errore di misura più diffuso e il meno visibile — nessuno lo
scopre, dato che il risultato conferma quello che si sperava. La domanda che lo previene sta in
sette parole: *quale risultato smentirebbe la mia tesi?* Se nessuno lo può, la finestra è
sbagliata, non lo strumento. Nell'applicazione la conseguenza è concreta: la fase di carico sotto
dump non ha una durata, **finisce quando finisce il dump**.

---

### Il calo ha un segno, e chi conclude al posto del pubblico ha già perso

> `ritmo prima 595/s · durante 692/s · calo -16.2%`. Il calo è negativo: il ritmo è **salito**. Il
> rapporto scrive la percentuale con il segno e non scrive «il dump non ha impatto», che pure quel
> giorno sarebbe stato vero.

Fonte: [`app/docs/Sources.md`, M-047](../app/docs/Sources.md#m-047),
[`app/docs/Sources.md`, M-046](../app/docs/Sources.md#m-046).

**Perché una slide:** perché è la stessa disciplina che il talk rimprovera ai benchmark altrui,
applicata al proprio. I numeri da leggere sono quelli assoluti accanto — 279 scritture durante il
dump, tutte confermate, p95 da 66,3 a 68,7 ms — e la percentuale cambia a ogni giro. C'è anche una
ragione **misurata** per cui il primario non se ne accorge: con `--readPreference=secondary` le
letture del dump gli passano da +15 a **+0**.

---

### Il `build` riesce, e il container si ferma alla prima esecuzione

> Copiare `mongodump` dall'immagine `mongo` dentro quella dell'applicazione **si costruisce senza
> un avviso**. Poi esce con 127: `libgssapi_krb5.so.2: cannot open shared object file`.

Fonte: [`app/docs/Sources.md`, M-044](../app/docs/Sources.md#m-044),
[ADR-0100](Decision.md#adr-0100),
[registro operativo, nota 203](registro-operativo-sviluppo.md).

**Perché una slide:** perché una verifica che si ferma al «compila?» avrebbe concluso l'opposto, e
il guasto sarebbe arrivato in sala. Cinque minuti di prova hanno prodotto un fatto invece di
un'argomentazione, e la decisione che ne segue ha una simmetria che si difende da sé: gli strumenti
restano **dove sono già**, dentro i nodi, e la scena li raggiunge da fuori.

---

### Non «perse»: mancano nella copia, e sono ancora nell'originale

> `restore 3908 all'origine · 3802 nella copia · differenza 106`. I 106 non sono scritture perse:
> sono i documenti arrivati **mentre la fotografia veniva scattata**. Nel database ci sono tutti.

Fonte: [ADR-0102](Decision.md#adr-0102),
[`app/docs/Sources.md`, M-047](../app/docs/Sources.md#m-047),
[`app/docs/Sources.md`, M-024](../app/docs/Sources.md#m-024).

**Perché una slide:** perché è il prezzo di non aver fermato il servizio, detto con un numero
invece che con un aggettivo — e perché usare «perse», la parola dell'Atto II, proprio nel momento
in cui la sala sta imparando la differenza sarebbe l'errore più costoso possibile. Da qui anche il
rifiuto di restaurare **sopra** l'originale: i conteggi combacerebbero, e la differenza sparirebbe
proprio perché il restore è riuscito.

---

### La pulizia va scritta per il cammino che fallisce

> L'helper della prova chiamava `check_returncode()` prima di restituire l'output. Ma il nome della
> collezione da cancellare lo annuncia la scena, sulla prima riga: sollevando prima, nessuno sapeva
> più che cosa pulire — e la collezione era già piena.

Fonte: [registro operativo, nota 206](registro-operativo-sviluppo.md).

**Perché una slide:** perché il fallimento è **esattamente** il caso in cui la pulizia serve di
più, ed è l'unico che di solito non si prova. La forma che funziona è banale una volta vista: un
helper di prova non solleva, restituisce il codice di uscita insieme all'output, e l'asserzione
viene dopo che il chiamante ha raccolto ciò che gli serve per rimettere a posto.

---

### Il balancer è acceso, ha fatto 1 153 giri, e non ha mai migrato niente

> `balancerStatus` dice `mode: "full"` e **1 153 giri**. Il `changelog` del cluster, che conserva le
> voci dal giorno dell'`addShard`, ha due fusioni e **zero** migrazioni: non una sola voce
> `moveChunk`.

Fonte: [`app/docs/Sources.md`, M-049](../app/docs/Sources.md#m-049),
[ADR-0103](Decision.md#adr-0103),
[ADR-0069](Decision.md#adr-0069).

**Perché una slide:** perché è la risposta a «e il balancer quando si vede lavorare?», ed è una
risposta che spiega invece di scusarsi. Con una chiave `{_id: "hashed"}` i documenti si sparpagliano
**all'inserimento**: i due shard restano pari per costruzione, e il balancer non ha nessuno
squilibrio da correggere. Lo zero non è un difetto del lab, è il comportamento corretto di una
chiave scelta bene — e ha portato con sé la conseguenza più netta del task, un evento del dominio
**rimosso** perché nessuno può emetterlo.

---

### Un evento che nessuno può emettere non è un campo vuoto: è una decisione

> `ChunkMigrated` era nel design fin dal §6.3. È uscito dal dominio quando si è misurato che in
> questo cluster non è mai avvenuta una migrazione. La guardia dei nomi scende da dieci a nove, e al
> suo posto resta un commento che dice quando è uscito e con quale numero accanto.

Fonte: [ADR-0103](Decision.md#adr-0103),
[`app/docs/Sources.md`, M-049](../app/docs/Sources.md#m-049),
[registro operativo, nota 208](registro-operativo-sviluppo.md).

**Perché una slide:** perché la scelta alternativa — lasciare il nome nel codice «per quando
servirà» — produce un campo che sembra funzionante e non lo è, e nessuno se ne accorge finché non
serve davvero. Rimuoverlo costa il cambio di un elenco in una guardia, cioè costa **accorgersene**.
È anche un cambio di ordine nelle domande: prima di chiedersi «come lo emetto», chiedersi «quante
volte è successo finora».

---

### Una sola colonna non dimostra niente

> ```
> non sharded  carico-20260904-140333 non è distribuita · 5000 documenti su shard1rs
> arrivati     shard1rs 2507 (50%) · shard2rs 2493 (50%)
> ```
> Lo stesso identico carico, due volte: una collezione che nessuno ha distribuito se lo prende
> tutto, quella distribuita lo divide a metà.

Fonte: [ADR-0106](Decision.md#adr-0106),
[ADR-0107](Decision.md#adr-0107),
[`app/docs/16`](../app/docs/16-la-chiave-di-shard-e-lo-stesso-carico-due-volte.md).

**Perché una slide:** perché mostrare due colonne di numeri equilibrati non prova che lo sharding
faccia qualcosa — serve accanto il caso in cui non lo fa. Costa quattro secondi di scaletta in più
ed è l'unica forma in cui la scena dimostra la sua tesi. Da sola, la prima riga è anche la risposta
alla domanda che il pubblico fa sempre: *cosa succede a una collezione che non ho distribuito?* Va
tutta sullo shard primario.

---

### La riga di garanzia ha funzionato, e denunciava un difetto di disegno

> `carico 4288 senza chiave · 4415 con chiave · non è lo stesso carico`. Due corse da sei secondi
> l'una non scrivono lo stesso numero di documenti, perché il throughput non è lo stesso. Da lì il
> limite della scena non è più una durata: è un conteggio.

Fonte: [`app/docs/Sources.md`, M-052](../app/docs/Sources.md#m-052),
[ADR-0107](Decision.md#adr-0107),
[registro operativo, nota 209](registro-operativo-sviluppo.md).

**Perché una slide:** perché nessuna prova unitaria poteva vederlo — i doppi scrivono esattamente
quanto il copione chiede — e il fatto vive nel punto in cui un limite di tempo incontra due
throughput diversi, cioè in nessuno dei due. La riga resta a schermo anche adesso che le due corse
sono uguali per costruzione: **una garanzia che nessuno controlla è una speranza**, e il costo di
tenerla è una riga.

---

### `SCONOSCIUTO` non è «non c'è»: è «non ho ancora guardato»

> Un client PyMongo appena costruito non conosce nessun server: la scoperta avviene alla prima
> operazione, non alla costruzione. L'ispettore leggeva quello stato e concludeva «non è uno sharded
> cluster» — cioè leggeva il proprio non aver guardato, e negava un cluster acceso.

Fonte: [`app/docs/Sources.md`, M-053](../app/docs/Sources.md#m-053),
[ADR-0108](Decision.md#adr-0108),
[`app/docs/Sources.md`, M-042](../app/docs/Sources.md#m-042).

**Perché una slide:** perché è la distinzione che tutta l'architettura del dominio prende sul serio
— «assenza di un'osservazione» contro «osservato assente» — colta nel momento in cui è stata
violata, per la seconda volta, dal codice che l'aveva dichiarata. La correzione è un `ping`, e la
parte da non sbagliare è la preferenza di lettura: `NEAREST`, perché un comando su `admin` aspetta
un primario che su un mongos non esiste.

---

### La fixture preparava anche ciò che nessuno le aveva chiesto

> Il difetto del client freddo era in produzione da due task, e la suite d'integrazione non poteva
> vederlo: la fixture di sessione pulisce il database prima di consegnare il client, e la scoperta
> avveniva come **effetto collaterale della pulizia**. Ogni prova partiva da un client caldo. Solo
> la sala partiva da uno freddo.

Fonte: [registro operativo, nota 210](registro-operativo-sviluppo.md),
[`app/docs/Sources.md`, M-053](../app/docs/Sources.md#m-053).

**Perché una slide:** perché è il modo più comune in cui una suite verde convive con un difetto
riproducibile a mano in dieci secondi. Il primo istante di vita di un oggetto non è coperto da
nessuna prova che riceva quell'oggetto già usato — e la correzione non è una fixture migliore, è una
prova che si costruisce il proprio client apposta, con scritto accanto perché.

---

### Il seed diluiva lo squilibrio fino a farlo sparire

> Misurata sui totali di `lab.ordini`, una corsa finita per l'**ottanta per cento** su un solo shard
> risultava sbilanciata di **tre centesimi di punto**. I ventimila documenti del seed coprono
> qualunque cosa faccia il carico. La scena misura gli arrivi: dopo meno prima.

Fonte: [ADR-0106](Decision.md#adr-0106),
[`app/docs/16`](../app/docs/16-la-chiave-di-shard-e-lo-stesso-carico-due-volte.md#perché-gli-arrivi-e-non-i-totali).

**Perché una slide:** perché è la stessa trappola della finestra di misura più larga dell'evento, in
un'altra forma: **una misura che non può smentire la tesi non la sta verificando**. Qui il numero
sbagliato sarebbe stato un equilibrio perfetto mostrato mentre il carico andava tutto da una parte —
cioè la conferma più convincente possibile della cosa falsa.

---

### `SINGLE_SHARD` e `SHARD_MERGE`, con le parole del server

> ```
> mirata    {"_id": 4242}          · SINGLE_SHARD · 1 shard
> su tutti  {"citta": "Ancona"}    · SHARD_MERGE  · 2 shard
> ```
> Lo stadio va a schermo **verbatim**: sono le parole che chi guarda ritroverà in `explain()` la
> prima volta che proverà da solo.

Fonte: [`app/docs/Sources.md`, M-051](../app/docs/Sources.md#m-051),
[ADR-0105](Decision.md#adr-0105).

**Perché una slide:** perché è la differenza fra chiedere a **un** shard e chiedere a **tutti**,
mostrata in due righe e senza spiegazioni — e perché tradurre lo stadio in un booleano significherebbe
tenere aggiornato un dizionario al posto del server. Nota per chi presenta: l'ordine degli shard che
il server restituisce **non è stabile**, e la scena li ordina apposta.

---

### Il numero non misurava il server, misurava il client

> Stesso carico, stesso dataset, tre architetture. Lo standalone fa **1 712** scritture al secondo.
> Si alza da una a quattro CPU il **solo** container dell'applicazione, e lo standalone fa
> **2 334**: +40 %. Il replica set e il cluster si muovono del 3 % e del 9 %, cioè restano fermi.

Fonte: [V-079](Sources.md#v-079),
[`app/docs/Sources.md`, M-056](../app/docs/Sources.md#m-056),
[ADR-0111](Decision.md#adr-0111).

**Perché una slide:** perché è la lezione che il pubblico può portarsi a casa e usare lunedì. Non
c'era niente nel riepilogo che denunciasse il problema — zero errori, zero ritentativi, latenze
plausibili — e la verifica costa una corsa sola: si alza il limite del **solo** client e si guarda
se le altre condizioni restano ferme. Se si muovono tutte, il sospetto è la macchina; se si muove
una sola, il numero era del misuratore.

---

### Una mediana intatta con una coda quattro volte più lunga

> `p50 2,8 ms → 2,8 ms` · `p99 40,6 ms → 11,0 ms`. La metà delle operazioni non si accorge di
> niente. **Contesa dal lato di chi chiede, non lentezza dal lato di chi risponde.**

Fonte: [`app/docs/Sources.md`, M-056](../app/docs/Sources.md#m-056),
[V-079](Sources.md#v-079).

**Perché una slide:** perché insegna a leggere due colonne che di solito si guardano separate.
Chiunque abbia un cruscotto ha una mediana e un p99 davanti agli occhi ogni giorno; la coppia dice
*dove* sta il collo di bottiglia, e il grafico della sola mediana non lo dirà mai.

---

### Il thread che soffre di più è il meno rappresentato

> Con `maxPoolSize` a uno **in meno** del numero di scrittori, p50, p95 e p99 sono indistinguibili
> dal caso sano. Solo il massimo dice qualcosa: **20 004 ms**, cioè un thread che ha aspettato per
> tutta la corsa e non ha mai scritto. Se aspetta non scrive, e se non scrive non compare.

Fonte: [V-080](Sources.md#v-080),
[`app/docs/Sources.md`, M-054](../app/docs/Sources.md#m-054).

**Perché una slide:** perché è controintuitivo e si dimostra in una riga: i percentili pesano le
**operazioni**, non i thread. È anche la difesa del massimo, la statistica che tutti tolgono per
prima dai cruscotti perché «è rumore» — ed è l'unica colonna che qui vede la fame.

---

### `j: true`: la perdita si azzera davvero, e costa un terzo

> Senza giornale: **2** documenti confermati e spariti dopo un `SIGKILL`, ≈ 4 900 scritture/s.
> Con `j: true`: **0** persi, ≈ 3 330 scritture/s. **−32 %.**

Fonte: [V-075](Sources.md#v-075), [V-016](Sources.md#v-016),
[ADR-0109](Decision.md#adr-0109).

**Perché una slide:** perché le due metà stanno sulla stessa riga. È facile mostrare lo zero e
tacere il prezzo, o mostrare il prezzo e tacere che il problema esiste davvero: un confronto che
riporta solo la buona notizia non è un confronto. E il numero vero è −32 % solo dopo aver tolto
l'avvio dell'interprete dal tempo a orologio — sui tempi lordi sembrava −23 %.

---

### «Può fare solo 6 chunk»

> `analyzeShardKey` su `{stato: 1}` non risponde «è una chiave mediocre». Rifiuta: quella chiave
> può produrre **sei** chunk, e sei chunk non si distribuiscono su niente. Una chiave a bassa
> cardinalità non è lenta — è **inutilizzabile**, e il server lo dice prima che tu ci provi.

Fonte: [V-081](Sources.md#v-081),
[`02-architetture/sharded-cluster.md`](02-architetture/sharded-cluster.md#cosa-questa-pagina-non-dice).

**Perché una slide:** perché la cardinalità della shard key è il primo errore che si fa, e questo è
il modo più breve di spiegarla: non un consiglio, un rifiuto con un numero dentro.

---

### Il replica set legge più in fretta dello standalone, e non è un merito

> Sotto lo stesso carico, mediana di lettura: replica set **2,0 ms**, standalone **3,4 ms**. Non
> perché legga meglio — perché scrivendo cinque volte meno tiene i nodi molto meno occupati.

Fonte: [V-079](Sources.md#v-079).

**Perché una slide:** perché è il promemoria che in una misura di sistema nessuna colonna è
indipendente dalle altre, e che il numero migliore della tabella può essere il sintomo del numero
peggiore. Chi cita la riga delle letture senza quella delle scritture sta vendendo un vantaggio che
non esiste.

---

### Un controllo che nessuno controlla è una firma in bianco

> `RIGA_FONTI = re.compile(r"^\*\*Fonti:\*\* (.+)$", re.MULTILINE)` — `.` non attraversa il
> newline. Un elenco di fonti che va a capo perde tutto ciò che sta sotto la prima riga, **in
> silenzio**. Il difetto è emerso solo quando ha bocciato un file corretto: finché ha promosso
> file rotti, nessuno poteva accorgersene.

Fonte: [registro operativo, nota 217](registro-operativo-sviluppo.md),
[`app/docs/17`](../app/docs/17-le-quattro-opzioni-e-i-debiti-di-misura.md#il-controllo-che-approvava-un-file-rotto).

**Perché una slide:** perché è la stessa classe di rischio delle prove che passano per il motivo
sbagliato, applicata all'automazione che dovrebbe proteggerci. Su centoundici ADR il buco ne
toccava esattamente uno; per gli altri centodieci l'abitudine aveva funzionato **per caso**.

---

### Il ritardo di replica di un insieme sano vale diecimila millisecondi

> Su un replica set sano e a riposo, il ritardo letto nel modo standard dichiara **10 000 ms**,
> quantizzati al secondo. Chiesto al secondario invece che al primario, lo stesso ritardo diventa
> **negativo**. Il ritardo vero di questo lab, misurato altrimenti, è ≈ **1,6 ms**.
> Fonte: [V-084](Sources.md#v-084), [V-027](Sources.md#v-027).

**Perché una slide:** perché è la metrica che tutti citano, e su un insieme in ottima salute produce
il numero più allarmante della serata. Non misura il ritardo: misura la distanza fra l'ultima
scrittura replicata e adesso, e a riposo non ci sono scritture da replicare. È il caso più puro di
allarme falso strutturale — cresce quando il sistema **non ha niente da fare**. La pagina sul
monitoraggio ha deciso di non mostrarla dal vivo e di dire perché
([ADR-0112](Decision.md#adr-0112)).

---

### Il server dichiara 67 microsecondi, il client ne misura 2 800

> Sotto lo stesso carico: `opLatencies.writes` lato server **67 µs**, p50 misurato dal client
> **2,8 ms**. Un fattore quaranta. Nessuno dei due numeri è sbagliato: misurano due cose diverse, e
> quella che l'utente subisce è la seconda.
> Fonte: [V-083](Sources.md#v-083), [V-079](Sources.md#v-079).

**Perché una slide:** perché il numero del server è quello che finisce sui cruscotti, ed è quello
che assolve il database. La differenza è tutto ciò che sta fuori dal cronometro del server —
attraversamento di rete, driver, attesa in coda lato client — cioè quasi tutta la latenza. Sullo
stesso campo, sul primario di un replica set, il valore sale a **18 390 µs**: non è la stessa
metrica più grande, è una metrica che **cambia significato** con l'architettura.

---

### Il pool dei ticket di scrittura non è 128, e non sta fermo

> Il numero 128 circola come una costante di WiredTiger. Misurato dentro questi container, il pool
> di scrittura sta fra **7 e 12**, e si muove da solo mentre il carico gira: nella 7.0 lo dimensiona
> un controllore.
> Fonte: [V-083](Sources.md#v-083).

**Perché una slide:** perché è la premessa nascosta di ogni allarme scritto come «ticket disponibili
sotto la soglia X». La soglia si sceglie rispetto a un totale che non è costante e che nessuno
dichiara: l'allarme non misura la saturazione, misura quanto il controllore ha deciso di concedere
in quel momento.

---

### `dataSize` non è spazio su disco: tre volte sui dati veri, zero sulla zavorra

> Stessa istanza, stesso motore, stessa compressione. `lab.ordini`: `size`/`storageSize` = **3,06×**.
> La collezione di carico: **0,97×** — l'archiviazione è più grande dei dati. La zavorra è base64 di
> uno `shake_128`, cioè byte pseudocasuali, e i byte casuali non si comprimono.
> Fonte: [V-087](Sources.md#v-087).

**Perché una slide:** perché il rapporto di compressione non è una proprietà del database ma **dei
dati**, e un solo numero medio su un database misto non dice quanto disco serve né quanto si sta
risparmiando. Il corollario pratico costa poco e si dimentica sempre: si misura sulla collezione,
non si stima sul database.

---

### Il ritorno di un'architettura si misura in secondi, non in aggettivi

> 634 prove unitarie, **3,86 secondi**, con la variabile d'ambiente del client Docker puntata a un
> socket che non esiste. La suite di integrazione, sulle stesse macchine, ne chiede **circa 110** e
> undici container.
> Fonte: [M-058](../app/docs/Sources.md#m-058).

**Perché una slide:** perché «le dipendenze puntano verso l'interno» è una frase che nessuno può
contestare e nessuno può verificare, mentre quattro secondi contro due minuti si contano. Ed è la
differenza fra una suite che si esegue dopo ogni modifica e una che si esegue quando ci si ricorda —
cioè fra una rete di sicurezza e un rituale.

---

### Un contratto copiato non è un contratto

> Dodici verifiche scritte **una volta sola**, eseguite in due posti: dal doppio in memoria nella
> suite veloce, dall'adattatore vero contro lo stack acceso. Alla prima esecuzione hanno trovato due
> bugiardi, e il secondo era MongoDB.
> Fonte: [`docs/06-sviluppo/tdd-e-doppi.md`](06-sviluppo/tdd-e-doppi.md),
> [M-017](../app/docs/Sources.md#m-017), [M-022](../app/docs/Sources.md#m-022).

**Perché una slide:** perché la tentazione è duplicare il corpo delle verifiche nei due file, e
sembra innocua: sono identiche. Divergono al primo fallimento, quando qualcuno corregge la copia che
ha davanti per farla passare e l'altra resta indietro **senza che niente diventi rosso**. Un doppio
ben scritto è convincente, ed è precisamente per questo che serve qualcuno che lo interroghi con le
stesse domande dell'originale.

---

### Una regola che nessuna prova esegue non è una regola: è un commento

> «Dopo trenta secondi senza primario, smetti di ritentare» è rimasta una frase nel documento di
> design per mesi, perché nessuno mette in una suite veloce una prova che aspetta mezzo minuto. Con
> il tempo preso da una porta invece che dall'orologio di sistema, la stessa regola si verifica in
> centesimi di secondo, con il valore atteso **esatto** invece che tollerante: sei letture; e con la
> pazienza a 1001 ms, sette.
> Fonte: [`docs/06-sviluppo/tdd-e-doppi.md`](06-sviluppo/tdd-e-doppi.md).

**Perché una slide:** perché mostra che cosa compra davvero l'inversione delle dipendenze, in un
caso in cui il guadagno non è teorico: non solo la prova diventa istantanea, ma diventa **più
severa**. Un millisecondo di pazienza in più è un giro in più — cioè si verifica che la soglia
scatti quando deve *e non prima*, distinzione che con un'attesa vera non sarebbe misurabile.
