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
