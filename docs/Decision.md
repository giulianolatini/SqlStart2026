# Registro delle decisioni architetturali

Le decisioni sono in ordine cronologico e non vengono riscritte: una decisione superata
resta, con lo stato aggiornato e il rimando a quella che la sostituisce. Ogni ADR cita le
fonti di [`Sources.md`](Sources.md) che lo sostengono; il legame è verificato da
`tools/check_citations.py`.

Tre ADR — [ADR-0004](#adr-0004), [ADR-0009](#adr-0009) e [ADR-0013](#adr-0013) — portano
una **nota di revisione**: la verifica sulle fonti primarie del 2026-08-25 ha smontato la
motivazione con cui erano state prese, senza toccarne il merito. La decisione è rimasta, il
perché è cambiato. Sembrava più onesto scriverlo che riscrivere il passato.

---

<a id="adr-0001"></a>
## ADR-0001 — Docker Compose come formato dell'artefatto

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** il lab deve essere eseguibile da chi ascolta, sulla propria macchina, senza
installare nulla oltre a ciò che ha già. Docker Desktop è il runtime che il pubblico di
SqlStart trova installato più spesso. Resta da decidere la forma dell'artefatto: uno script
che concatena `docker run`, oppure un file dichiarativo. C'è anche una scelta di dettaglio
che pesa più di quanto sembri: quasi tutti gli esempi Compose in circolazione aprono con
`version: "3.8"`, e la documentazione oggi definisce quella chiave «obsolete», «only
informative», con un avviso a ogni avvio. Compose valida comunque con lo schema più
recente, qualunque cosa dica il campo.

**Decisione:** ogni architettura è descritta da un file Compose conforme alla Compose
Specification, senza chiave `version:`. Docker Desktop è il runtime di riferimento
dichiarato; gli altri runtime compatibili con Compose restano possibili ma non garantiti.

**Conseguenze:** l'artefatto è leggibile a voce alta e proiettabile. Niente avviso di
obsolescenza all'avvio, che dal vivo è rumore. L'assenza di `version:` diventa essa stessa
un contenuto: mostra al pubblico una convenzione diffusa che non serve più.

**Alternative scartate:** una sequenza di `docker run` in uno script (le reti e le
dipendenze restano implicite, e su slide è illeggibile); Kubernetes (sposta l'argomento
dalla topologia MongoDB all'orchestratore, e alza la soglia di ingresso per il pubblico).

**Fonti:** [S-016](Sources.md#s-016)

---

<a id="adr-0002"></a>
## ADR-0002 — Apple `container` escluso dai runtime supportati

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** macOS 26 include `container`, il runtime di Apple: leggero, nativo, senza VM
Linux permanente. Sarebbe stato interessante mostrarlo. La verifica sull'ambiente di
sviluppo ha però stabilito che alla versione 1.2.2 non espone alcun subcomando `compose`:
`container compose --help` termina con errore.

**Decisione:** `container` è escluso dai runtime supportati. Il lab richiede Docker Desktop
o un runtime che implementi la Compose Specification.

**Conseguenze:** un solo formato da mantenere e da provare. Chi usa `container` non può
eseguire il lab, e va detto nel README anziché lasciarglielo scoprire.

**Alternative scartate:** descrivere gli stack due volte, in Compose e in comandi
`container` a mano (raddoppia la manutenzione e perde proprio il valore didattico del file
dichiarativo); rimandare la decisione (il lab va provato, non ipotizzato).

**Fonti:** [V-001](Sources.md#v-001)

---

<a id="adr-0003"></a>
## ADR-0003 — Tre stack Compose indipendenti, non profili di un file unico

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** le tre architetture — standalone, replica set, sharded cluster — potrebbero
stare in un solo file, distinte da profili o assemblate con `include`. La tentazione è di
risparmiare righe. Ma i tre stack usano le stesse porte e gli stessi nomi di servizio, e il
file unico diventerebbe illeggibile proprio nel momento in cui deve essere letto: sul
proiettore. Compose usa il nome di progetto «to isolate environments from each other», e la
precedenza con cui lo determina ha cinque livelli, il terzo dei quali è la chiave `name:`
dentro il file.

**Decisione:** tre directory sotto `docker/`, tre file Compose autonomi, ciascuno con la
propria chiave `name:` esplicita. Nessun profilo usato per separare le architetture — i
profili restano riservati alla distinzione fra palco e configurazione completa dentro un
singolo stack ([ADR-0010](#adr-0010)).

**Conseguenze:** ogni file si legge da solo, senza dover tenere a mente cosa è attivo. Gli
stack possono coesistere, o essere fermati singolarmente, senza collisioni. Il nome di
progetto è scritto nel file e non dipende dal nome della directory in cui uno l'ha clonato:
è la ragione per cui va dichiarato invece di lasciarlo dedurre.

**Alternative scartate:** un file unico con tre profili (le porte collidono e la lettura
richiede un modello mentale in più); `include` con frammenti condivisi (la fattorizzazione
è comoda per chi mantiene, ostile a chi legge una volta sola).

**Nota sulla fonte:** la documentazione dice «isolate environments», non elenca reti, volumi
e container come le risorse isolate. L'affermazione più specifica, che pure è vera nella
pratica, va sostenuta da verifica empirica e non citata come documentata.

**Fonti:** [S-017](Sources.md#s-017)

---

<a id="adr-0004"></a>
## ADR-0004 — Limiti di memoria e CPU espliciti per ogni servizio

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** la dimensione predefinita della cache interna di WiredTiger è «the larger of
either: 50% of (RAM - 1GB), or 0.256 GB». Sulla VM Docker della macchina di palco — 7,65
GiB — ogni mongod senza limite calcolerebbe per sé oltre 3 GiB: tre membri di un replica set
arrivano a rivendicare quasi il doppio della memoria esistente, e l'OOM killer si presenta
davanti al pubblico.

Si potrebbe sperare che mongod se ne accorga da solo leggendo il limite del proprio cgroup.
Qui la verifica ha trovato qualcosa di scomodo: **due pagine del manuale MongoDB, alla
stessa versione, si contraddicono.** La pagina su WiredTiger dice che il motore «may not
account for the memory limits of the specific container in certain cases» e prescrive di
intervenire — «you **must** set `--wiredTigerCacheSizeGB` or `--wiredTigerCacheSizePct` to a
value less than the amount of RAM available in the container». La pagina su `hostInfo` dice
l'opposto: «This memory limit, rather than the total system memory, is used as the maximum
RAM available to calculate WiredTiger internal cache». Non è una divergenza fra versioni:
sono entrambe correnti.

**Decisione:** ogni servizio dichiara `mem_limit` e `cpus`. Ogni mongod riceve un
`--wiredTigerCacheSizeGB` esplicito, dimensionato sotto il proprio `mem_limit` e non
inferiore a `0.256`, che è il minimo dichiarato dal riferimento di `mongod`. Il valore
esatto è fissato dalla verifica empirica dello spike sharded, non stimato a tavolino.

**Conseguenze:** gli stack sono prevedibili e coesistono nella stessa VM. Il file Compose
diventa esso stesso materiale didattico: mostra il calcolo invece di nasconderlo. `cpus`
diventa uno strumento narrativo — si può strozzare deliberatamente un secondario per
mostrarne il ritardo di replica. E la contraddizione fra le due pagine si può mostrare dal
vivo con `db.hostInfo()`, invece di sceglierne una e sperare che nessuno controlli.

**Alternative scartate:** lasciare i valori predefiniti (l'OOM killer arriva sul palco);
alzare la memoria assegnata alla VM Docker (non risolve il problema, e chi ascolta può avere
meno RAM di chi parla); affidarsi al rilevamento automatico del limite (due pagine ufficiali
non sono d'accordo su cosa faccia).

**Nota di revisione (2026-08-25):** la motivazione originale affermava che «dalla versione
5.0 mongod dimensiona la cache leggendo il limite del proprio cgroup». Nel testo non esiste
alcun marcatore di versione associato alla formula, e la pagina corrente afferma il
contrario di ciò che davamo per acquisito. Anche il valore che avevamo scelto per la cache,
`0.25` GB, risulta sotto il minimo documentato di `0.256` GB. La decisione era giusta per il
motivo opposto a quello scritto: la cache va impostata a mano non perché mongod legga il
cgroup, ma perché la documentazione avverte che potrebbe non leggerlo.

**Seconda nota di revisione (2026-08-25), che corregge la prima:** «`0.25` GB risulta sotto
il minimo documentato di `0.256` GB» è **falso**, e la misura lo dimostra
[V-009](Sources.md#v-009). Il minimo che il binario impone è `0.25`, dichiarato alla lettera
dal messaggio di rifiuto: `storage.wiredTiger.engineConfig.cacheSizeGB must be greater than
or equal to 0.25`. Con `0.25` mongod configura `268435456` byte, cioè **esattamente 256
MiB** — lo stesso valore che sceglierebbe da solo. La cifra `0.256` del manuale è un GB
decimale scritto dove l'implementazione usa GiB: `0.256` produce 262 MiB, un valore che non
corrisponde a nulla. Il valore del lab resta `0.25`, ora per una ragione misurata invece che
temuta. Cade anche il timore residuo sul rilevamento automatico: `hostInfo.system.memLimitMB`
riporta il `mem_limit` e la cache lo segue su sei misure. Si continua a dichiararla a mano
perché sia **leggibile nel file Compose**, che è materiale didattico, non perché mongod non
sappia leggerla. Il rischio vero è un altro, e la misura l'ha trovato: una cache **maggiore**
del `mem_limit` viene accettata senza un solo avviso che metta in relazione le due cifre.

**Fonti:** [S-001](Sources.md#s-001), [S-002](Sources.md#s-002), [S-003](Sources.md#s-003), [S-026](Sources.md#s-026), [V-009](Sources.md#v-009)

---

<a id="adr-0005"></a>
## ADR-0005 — Sicurezza graduata sui tre stack

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** mettere autenticazione e TLS ovunque dal primo minuto trasformerebbe il lab in
un esercizio di configurazione, e il pubblico perderebbe di vista MongoDB. Non metterla mai
insegnerebbe l'abitudine sbagliata. Serve una progressione. Gli elementi verificati su cui
costruirla: `--keyFile implies --auth`, quindi il keyfile porta con sé il controllo degli
accessi senza doverlo chiedere due volte; l'eccezione localhost «only applies when there are
no users or roles created in the MongoDB instance» e decade eseguendo `createUser` **oppure**
`createRole`; il keyfile va da 6 a 1024 caratteri dell'alfabeto base64, si genera con
`openssl rand -base64 756`, e l'esempio ufficiale gli assegna `chmod 400`.

Un dettaglio dell'immagine ufficiale cambia il modo in cui gli stack vanno scritti:
l'entrypoint avvia un mongod temporaneo per creare l'utente root, e da quel mongod rimuove
**sempre** `--auth` e `--keyFile`, mentre rimuove `--replSet` **solo se entrambe** le
variabili root sono presenti. Conseguenza pratica, non documentata in prosa da nessuna
parte: l'utente root nasce in un contesto standalone e non autenticato, e `rs.initiate()`
non viene mai eseguito dall'immagine. Resta a carico nostro.

**Decisione:** tre livelli. Lo standalone gira aperto, senza autenticazione, ed è presentato
come esempio negativo. Il replica set e lo sharded cluster usano keyfile per
l'autenticazione interna e SCRAM per gli utenti. TLS è documentato ma non attivato negli
stack.

**Conseguenze:** la sicurezza diventa narrazione invece che attrito: si parte da ciò che non
si deve fare e si arriva a un cluster chiuso. L'inizializzazione del replica set è un passo
esplicito degli stack, il che è anche didatticamente preferibile: il pubblico vede
`rs.initiate()` invece di trovarselo già fatto.

**Alternative scartate:** tutto aperto (comodo, ma insegna il contrario di quel che serve);
tutto con X.509 dal primo stack (il tempo di configurazione mangerebbe la demo).

**Riserva dichiarata:** la documentazione MongoDB avverte che i keyfile vanno usati «only for
testing and development environments because of their limited manageability and cryptographic
strength» e raccomanda X.509 in produzione. È un'avvertenza da anticipare al pubblico, non da
lasciar scoprire. Inoltre non è scritto da nessuna parte che mongod rifiuti di avviarsi con
permessi errati: la pagina pone il requisito e su Windows dichiara che i permessi non vengono
controllati affatto.

**Fonti:** [S-002](Sources.md#s-002), [S-005](Sources.md#s-005), [S-006](Sources.md#s-006), [S-022](Sources.md#s-022)

---

<a id="adr-0006"></a>
## ADR-0006 — Applicazione in Python con `pymongo`

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** la parte più difficile da mostrare di un failover non è quello che succede sul
server: è quello che vede il client. Serve un driver che esponga il proprio modello di
scoperta della topologia. PyMongo lo fa: cinque classi astratte di listener, registrabili per
singolo client con `MongoClient(event_listeners=[...])`. Tre eventi bastano a cronometrare un
failover — `ServerHeartbeatFailedEvent`, il momento esatto in cui il client si accorge della
caduta, `ServerDescriptionChangedEvent` e `TopologyDescriptionChangedEvent`. Tutte le classi
esistono dalla versione 3.3.

**Decisione:** l'applicazione dimostrativa è scritta in Python e usa `pymongo` con i listener
di monitoraggio registrati per client.

**Conseguenze:** il failover diventa cronaca in diretta invece che un'affermazione. C'è però
una conseguenza da gestire, e non è piccola: gli eventi sono consegnati in modo sincrono e
bloccano il thread chiamante. Il modo in cui la si gestisce è [ADR-0019](#adr-0019).

**Alternative scartate:** `mongosh` e basta (non dà accesso agli eventi di topologia:
mostrerebbe il risultato del failover, non il suo svolgersi); un altro linguaggio. Su
quest'ultimo punto la motivazione è di leggibilità in sala e di brevità del codice
proiettato, non di capacità del driver.

**Fonti:** [S-010](Sources.md#s-010)

---

<a id="adr-0007"></a>
## ADR-0007 — Interfaccia Rich con nucleo disaccoppiato da un `EventSink`

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** l'output va letto dall'ultima fila di una sala, quindi serve qualcosa di più di
righe di log; e va testato, quindi il nucleo non può dipendere dal disegno. Rich offre un
display che «will refresh 4 times a second» per impostazione predefinita, regolabile con
`refresh_per_second`, e permette di stampare sopra il display senza romperlo, sia tramite
`live.console` sia perché «Rich will redirect `stdout` and `stderr`».

**Decisione:** il nucleo dell'applicazione non conosce Rich. Emette eventi verso
un'interfaccia `EventSink`; l'interfaccia Rich è un adattatore che la implementa. La
frequenza di aggiornamento è dichiarata esplicitamente, non lasciata al valore predefinito.

**Conseguenze:** il nucleo si prova con un sink che accumula gli eventi in una lista —
nessun terminale, nessun timing, test deterministici. Lo stesso punto di estensione serve a
produrre un sink che scrive JSON, utile per le registrazioni di riserva. È l'applicazione
del principio di inversione delle dipendenze nel punto in cui serve davvero.

**Alternative scartate:** `print` diretti dal nucleo (nessuna testabilità e nessuna
possibilità di cambiare resa); una TUI più strutturata come Textual (costo di apprendimento
e di codice sproporzionato rispetto a quello che il talk deve mostrare).

**Riserva dichiarata:** la documentazione di Rich non contiene la parola «thread», né qui né
nel riferimento dell'API. Non esiste alcuna indicazione documentata sull'aggiornamento di
`Live` da più thread, in nessuna delle due direzioni. Il progetto non ci si appoggia: vedi
[ADR-0019](#adr-0019).

**Fonti:** [S-018](Sources.md#s-018)

---

<a id="adr-0008"></a>
## ADR-0008 — MongoDB 8.0, immagine ufficiale pinnata per digest

**Data:** 2026-08-24 · **Stato:** **Superata da [ADR-0028](#adr-0028)** il 2026-08-25

**Contesto:** il lab deve produrre lo stesso risultato sulla macchina di chi parla, su quella
di chi ascolta e fra dodici mesi. Un tag mobile non lo garantisce. L'immagine ufficiale
`mongo` dichiara come architetture supportate `amd64`, `arm64v8` e `windows-amd64`, e la
presenza di `linux/arm64/v8` nel manifest del tag `8.0` è stata confermata: è un requisito,
non un dettaglio, perché la macchina di palco è arm64.

**Decisione:** MongoDB 8.0, immagine ufficiale referenziata nella forma `mongo:8.0@sha256:…`.
Il digest è dichiarato una sola volta, in `docker/images.env`, e riferito dagli stack.

**Conseguenze:** tutti eseguono la stessa immagine, bit per bit. L'aggiornamento diventa un
atto deliberato e tracciabile invece di un cambiamento silenzioso fra due prove. Le variabili
`MONGO_INITDB_ROOT_USERNAME` e `MONGO_INITDB_ROOT_PASSWORD` creano l'utente root nel database
`admin` con ruolo `root`, ma «none of the variables below will have any effect if you start
the container with a data directory that already contains a database»: i volumi vanno
azzerati fra una prova e l'altra, e il preflight deve saperlo.

**Alternative scartate:** il tag `latest` (oltre all'imprevedibilità, ha un comportamento
specifico che lo rende incompatibile con il funzionamento offline: vedi
[ADR-0018](#adr-0018)); il tag `8.0` senza digest (si muove a ogni patch release).

**Riserva dichiarata:** la pagina di Docker Hub non copre i punti che servono davvero al lab
— né `--replSet` né `--keyFile` vi compaiono, la fase del mongod temporaneo non è descritta,
UID e GID non sono pubblicati. Per quei tre punti le fonti sono il codice sorgente
dell'immagine, citato come tale in [ADR-0005](#adr-0005) e [ADR-0014](#adr-0014).

**Motivo del superamento:** non la forma, ma il numero. La decisione di pinnare per digest
l'immagine ufficiale in una variabile sola è rimasta valida ed è stata ereditata da
[ADR-0028](#adr-0028) — anzi, è ciò che ha reso il cambio di versione un'operazione da un
file solo. A cadere è «MongoDB 8.0»: sul kernel della VM di Docker Desktop nessuna 8.0
pubblicata si avvia, e la patch che lo risolve esiste nel changelog ma non in distribuzione.
Anche la verifica su `linux/arm64/v8` è stata rifatta sulla versione nuova. Tutto il resto
di questo ADR — il perché del digest, il comportamento di `MONGO_INITDB_ROOT_*` su un volume
già popolato, la riserva sulla documentazione di Docker Hub — vale ancora e non è stato
toccato.

**Fonti:** [S-009](Sources.md#s-009), [V-002](Sources.md#v-002), [V-003](Sources.md#v-003)

---

<a id="adr-0009"></a>
## ADR-0009 — Funzionamento completamente offline obbligatorio

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** la connettività in sala non è garantita, e il Product Owner l'ha dichiarato
come rischio fin dal primo incontro. Una demo che scarica qualcosa è una demo che può non
partire. La verifica sulla documentazione Docker ha però prodotto un risultato scomodo: **la
parola «offline» non compare in nessuna delle pagine Compose consultate.** Non esiste una
modalità offline documentata. L'unico meccanismo con una frase esplicita sul non contattare
il registry è `pull_policy: never`.

**Decisione:** nessun passo del lab può richiedere rete. Le immagini si scaricano prima con
`tools/pull-images.sh`; gli stack dichiarano una politica di pull parametrica e il profilo di
palco impone `never` ([ADR-0018](#adr-0018)); i dati di esempio si generano localmente; i
filmati di riserva hanno una copia sul disco ([ADR-0016](#adr-0016)). Il preflight verifica
che tutto sia in casa prima di salire sul palco.

**Conseguenze:** una fase di preparazione in più, da eseguire quando la rete c'è. In compenso
il fallimento, se c'è, è immediato e leggibile: con `never`, se l'immagine non è in cache, «a
failure is reported» — meglio di un timeout di trenta secondi davanti al pubblico.

**Alternative scartate:** confidare che la cache locale basti (la documentazione non dice se
`compose up` contatti il registry per un'immagine già presente); portarsi un hotspot (sposta
il rischio, non lo toglie, e in una sala affollata la banda cellulare è la prima cosa che
cede).

**Nota di revisione (2026-08-25):** la motivazione originale faceva poggiare la garanzia
offline sul pinning per digest. Non regge: **il digest stabilisce *quale* immagine, non *se*
si va in rete.** Sono due proprietà distinte, e la seconda si ottiene solo con `pull_policy`.
Il pinning resta, per la ragione sua propria, in [ADR-0008](#adr-0008).

**Fonti:** [S-019](Sources.md#s-019), [V-002](Sources.md#v-002), [V-003](Sources.md#v-003), [V-005](Sources.md#v-005)

---

<a id="adr-0010"></a>
## ADR-0010 — Sharded cluster con due profili Compose, `palco` e `completo`

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** uno sharded cluster non è negoziabile nella forma: «Each shard must be deployed
as a replica set», «Config servers must be deployed as a replica set (CSRS)», e «Sharding
requires at least two shards to distribute sharded data». Con tre membri per componente si
arriva a undici container, che su una VM da 7,65 GiB non stanno in piedi insieme al resto. La
via d'uscita è documentata, e vale la pena sapere dove: **non** sulla pagina dei componenti,
che non nomina mai i replica set a un solo membro, ma sul tutorial di dispiegamento, che lo
autorizza due volte — per i config server e per gli shard — con la stessa frase: «For testing
purposes, you can create a single-member replica set».

**Decisione:** un solo stack sharded con due profili. Il profilo `palco` usa replica set a un
membro per ciascuno shard e per il config server. Il profilo `completo` usa tre membri per
componente, resta nel repository, è documentato ed eseguibile su una macchina capiente. I
servizi comuni non portano `profiles` e sono quindi sempre attivi.

**Conseguenze:** la demo entra nel budget di memoria senza rinunciare a mostrare
l'architettura vera, e il repository resta esaustivo come vuole [ADR-0017](#adr-0017). I
vincoli del replica set dei config server vanno documentati perché sono la risposta a chi,
dal pubblico, propone di risparmiare risorse con un arbitro: «Must have zero arbiters. / Must
have no delayed members. / Must build indexes». E il nome del replica set dei config server
deve differire da quello di ogni shard.

**Alternative scartate:** un arbitro nel CSRS per risparmiare un nodo (esplicitamente
vietato); il config shard introdotto nella 8.0, che «reduces the number of nodes required»
(tecnicamente attraente, ma fonde due ruoli che il talk deve mostrare distinti — resta
materiale per la documentazione); rinunciare allo sharded cluster dal vivo (è uno dei tre
blocchi del talk).

**Riserva dichiarata:** la documentazione dei profili copre una sola direzione della relazione
con `depends_on` — servizio con profilo verso le sue dipendenze. Il caso inverso, un servizio
senza profilo che dipende da un servizio con profilo non attivo, non è trattato in nessuna
pagina. Va verificato nello spike, non dato per scontato.

**Fonti:** [S-008](Sources.md#s-008), [S-015](Sources.md#s-015), [S-024](Sources.md#s-024), [S-025](Sources.md#s-025), [V-002](Sources.md#v-002)

---

<a id="adr-0011"></a>
## ADR-0011 — `testcontainers-python` per i test di integrazione

**Data:** 2026-08-24 · **Stato:** **Superata da [ADR-0020](#adr-0020)** il 2026-08-25

**Contesto:** l'idea era di rendere i test di integrazione dell'applicazione indipendenti
dagli stack Compose, così che il branch dell'applicazione potesse procedere senza attendere
quelli dell'infrastruttura.

**Decisione (superata):** usare `testcontainers-python` per avviare le istanze MongoDB
necessarie ai test di integrazione.

**Conseguenze:** nessuna. La decisione non è mai stata implementata.

**Motivo del superamento:** la verifica ha stabilito che `MongoDbContainer` accetta cinque
parametri — immagine, porta, utente, password, nome del database — e nient'altro. Le stringhe
«replica», «replSet» e «rs.initiate» non compaiono in alcun punto della documentazione del
modulo, e il sorgente conferma che avvia un'istanza standalone. Per una demo di failover il
componente non serve. L'alternativa interna alla libreria, la classe `DockerCompose`, esiste
nel codice ma ha zero occorrenze nella documentazione pubblicata: costruirci sopra
significherebbe dipendere da un'API non documentata.

**Fonti:** [S-013](Sources.md#s-013)

---

<a id="adr-0012"></a>
## ADR-0012 — Applicazione containerizzata sulla rete degli stack

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** un client che si collega a un replica set non parla solo con l'host che gli è
stato indicato: con `directConnection=false`, che è il valore predefinito, «the client
attempts to discover all servers in the replica set, and sends operations to the primary
member». Quella scoperta è esattamente ciò che il talk vuole mostrare, ed è anche ciò che si
rompe per primo quando l'applicazione gira sull'host e il cluster dentro Docker. La
documentazione MongoDB descrive la trappola parola per parola: «When a replica set runs in
Docker, it might expose only one MongoDB endpoint. In this case, the replica set is not
discoverable, and specifying `directConnection=false` can prevent your application from
connecting to it.»

**Decisione:** l'applicazione gira in un container collegato alla stessa rete Compose dello
stack, e si connette usando i nomi dei servizi. `directConnection=true` è usato solo nella
demo dello standalone, dove non c'è nulla da scoprire.

**Conseguenze:** non serve mappare le porte di tutti i membri sull'host, né toccare
`/etc/hosts` sulla macchina di chi ascolta. Il pubblico vede la topologia scoperta davvero,
non simulata. In cambio, l'immagine dell'applicazione entra nell'elenco delle immagini da
avere in cache prima del talk ([ADR-0009](#adr-0009)).

**Alternative scartate:** `directConnection=true` ovunque (spegne la scoperta, e con essa la
demo del failover); mappare tutte le porte e aggiungere alias in `/etc/hosts` (fragile,
richiede privilegi di amministratore sulla macchina di chi prova il lab).

**Riserva dichiarata:** la pagina dice che il driver «attempts to discover all servers», ma
non dice che usi i nomi host memorizzati nella configurazione del replica set. Il meccanismo
— la risposta al comando `hello`, che restituisce `members[n].host` — non è enunciato lì. Se
serve affermarlo, va mostrato in demo.

**Fonti:** [S-007](Sources.md#s-007)

---

<a id="adr-0013"></a>
## ADR-0013 — Sintassi breve nei file, `deploy.resources` nella documentazione

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** i limiti di risorsa in Compose si possono esprimere in due modi: la coppia
`mem_limit`/`cpus` a livello di servizio, oppure `deploy.resources.limits`. Il progetto aveva
scelto la prima sulla base di due convinzioni diffuse. La verifica le ha smontate entrambe.
Nella pagina della Deploy Specification i termini «Swarm», «ignored», «not supported» e
«docker compose up» hanno **zero occorrenze** nel corpo dell'articolo: la frase storica
secondo cui `deploy` sarebbe ignorato fuori da Swarm apparteneva al riferimento del formato
v3, oggi ritirato e non più mantenuto. E la sintassi breve non è presentata come
un'alternativa a `deploy`: la documentazione ne impone la coerenza — «When set, `mem_limit`
must be consistent with the `limits.memory` attribute in the Deploy Specification».

**Decisione:** i file Compose del lab usano la sintassi breve. La forma `deploy.resources` è
mostrata nella documentazione come forma equivalente e da mantenere coerente, non come
alternativa scartata.

**Conseguenze:** i file restano corti e proiettabili, ed è la ragione principale. L'effetto
dei limiti non si afferma citando la documentazione — che sul punto tace — ma si dimostra con
`docker inspect` sui campi `HostConfig.Memory` e `HostConfig.NanoCpus`: una verifica empirica
di due righe, che sul palco vale più di una citazione.

**Alternative scartate:** usare `deploy.resources` nei file (più righe da proiettare, e
l'efficacia fuori da Swarm resterebbe comunque da dimostrare allo stesso modo); dichiarare
entrambe le forme (ridondanza da tenere sincronizzata a mano, con il rischio di divergenza
che la documentazione stessa mette in guardia).

**Nota di revisione (2026-08-25):** cadono entrambe le gambe della motivazione originale. La
decisione resta, con motivazione nuova: leggibilità su proiettore, portabilità verso Podman,
ed efficacia dimostrata invece che citata. Nota favorevole emersa dalla stessa verifica: su
`mem_limit` e `cpus` non esiste alcun marcatore di deprecazione. L'ipotesi che fossero
attributi legacy è falsa.

**Nota di verifica (2026-08-25):** la dimostrazione promessa qui sopra è stata eseguita, e ha
un esito che vale più della decisione che doveva sostenere [V-009](Sources.md#v-009). Due
servizi identici, uno con `mem_limit`/`cpus` e uno con `deploy.resources.limits`, producono
`HostConfig.Memory` e `HostConfig.NanoCpus` **identici byte per byte**: `671088640` e
`500000000`. `deploy` **non** è ignorato fuori da Swarm su Compose v5.4.0. La decisione non
cambia — la sintassi breve resta, per leggibilità su proiettore e portabilità — ma il suo
unico argomento residuo cade: non si sceglie la forma breve perché l'altra non funzioni, si
sceglie perché è più corta. Chi migra verso `deploy` non perde nulla.

**Fonti:** [S-003](Sources.md#s-003), [S-004](Sources.md#s-004), [V-009](Sources.md#v-009)

---

<a id="adr-0014"></a>
## ADR-0014 — Keyfile generato in un volume nominato, non in bind mount

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** il keyfile dell'autenticazione interna ha requisiti sui permessi: «On UNIX
systems, the keyfile must not have group or world permissions», e chi esegue mongod deve
esserne il proprietario. L'esempio ufficiale usa `chmod 400`. Nell'immagine ufficiale l'utente
e il gruppo `mongodb` hanno entrambi identificativo **999** — un valore leggibile solo dal
Dockerfile, non pubblicato su Docker Hub — e `/data/db` e `/data/configdb` appartengono a
`mongodb:mongodb`. Un bind mount da macOS non conserva né proprietario né permessi in modo
affidabile: il file arriverebbe nel container con attributi che non soddisfano il requisito.

**Decisione:** il keyfile si genera dentro un container di servizio, direttamente in un volume
nominato, con `openssl rand -base64 756`, `chmod 400` e proprietario `999:999`. Il volume è
montato dai mongod che ne hanno bisogno. Nessun keyfile transita dall'host.

**Conseguenze:** lo stack si comporta allo stesso modo su macOS, Linux e Windows, il che per
un lab che il pubblico esegue sulla propria macchina è il punto. Il passo di generazione
diventa esso stesso un contenuto della demo, e si incastra con l'ordine di avvio dichiarato in
[ADR-0023](#adr-0023). Il keyfile non finisce mai nel repository.

**Alternative scartate:** bind mount con `chmod` sull'host (non regge la traversata del
filesystem virtualizzato di macOS); keyfile incluso nell'immagine o nel repository (una
credenziale versionata resta versionata per sempre, e sarebbe un pessimo esempio da mostrare).

**Riserva dichiarata:** la documentazione non descrive cosa accade se i permessi sono errati —
pone il requisito e basta — e su Windows dichiara che i permessi non vengono controllati.
L'affermazione «altrimenti mongod non parte», per quanto diffusa, non è citabile.

**Fonti:** [S-005](Sources.md#s-005), [S-023](Sources.md#s-023)

---

<a id="adr-0015"></a>
## ADR-0015 — Runbook del talk come documento unico

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** sul palco, sotto pressione, cercare l'informazione giusta in quattro file
diversi è un modo affidabile per perderla. La scaletta, i comandi da digitare, i tempi, i
piani di ripiego e i criteri per tagliare devono stare in un posto solo, e quel posto deve
essere leggibile a colpo d'occhio.

**Decisione:** il runbook del talk è un unico documento, con i criteri di rinuncia in appendice
anziché sparsi nel testo.

**Conseguenze:** un file da tenere aggiornato, ma è quello che si stampa e si tiene aperto sul
secondo schermo. Duplica deliberatamente qualche informazione presente altrove nella
documentazione: è un costo accettato, perché l'alternativa è saltare fra documenti mentre si
parla.

**Alternative scartate:** un documento per blocco del talk (moltiplica i punti in cui
guardare); affidarsi alle note del presentatore delle slide (non contengono i comandi, e non
sono consultabili se le slide vanno in crisi).

**Fonti:** nessuna (decisione organizzativa)

---

<a id="adr-0016"></a>
## ADR-0016 — Filmati sul canale YouTube del relatore, copia locale obbligatoria

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** le registrazioni di riserva delle demo sono l'assicurazione contro il fallimento
dal vivo, e pesano. GitHub «recommend repositories remain small, ideally less than 1 GB»,
avverte sui file oltre i 50 MiB e blocca quelli oltre i 100 MiB. Un repository con dentro i
filmati diventa lento da clonare proprio per chi vorrebbe provarlo in sala.

**Decisione:** i filmati sono pubblicati sul canale YouTube del relatore e collegati
dall'indice della documentazione. Una copia locale sul portatile è obbligatoria e fa parte
della checklist del preflight.

**Conseguenze:** il repository resta clonabile in pochi secondi. Il piano di riserva non
dipende dalla rete della sala, che è esattamente il rischio da cui ci si sta difendendo: un
filmato di riserva raggiungibile solo online non è un piano di riserva.

**Alternative scartate:** Git LFS (consuma quota e aggiunge un passo a chi clona, che
scoprirebbe la cosa nel momento peggiore); comprimere i filmati fino a rientrare nei limiti
(su un proiettore la perdita di qualità si vede, e un terminale illeggibile non dimostra
niente).

**Nota sulle unità:** i limiti di GitHub sono espressi in **MiB**, non in MB. Scrivere «100
MB» su una slide è impreciso, ed è precisamente il genere di dettaglio che qualcuno in sala fa
notare.

**Fonti:** [S-021](Sources.md#s-021)

---

<a id="adr-0017"></a>
## ADR-0017 — Il repository resta esaustivo, i tagli valgono solo dal vivo

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** sessanta minuti impongono scelte, e i criteri di rinuncia servono a farle in
fretta quando il tempo stringe. C'è però il rischio di lasciare che quei criteri
impoveriscano anche il materiale scritto, che invece ha tutt'altro vincolo: chi consulta il
repository dopo il talk ha tempo, e cerca proprio quello che dal vivo è stato saltato.

**Decisione:** il repository resta completo. I criteri di rinuncia riguardano esclusivamente
l'esecuzione dal vivo. Nulla viene tolto dalla documentazione, dagli stack o
dall'applicazione perché «non entra nei tempi».

**Conseguenze:** il materiale scritto e quello parlato divergono deliberatamente, e la
divergenza va gestita: il runbook dice cosa si mostra, l'indice della documentazione dice
cosa esiste. Ciò che non entra dal vivo resta disponibile a chi approfondisce, ed è la
ragione per cui il repository ha valore anche dopo il 18 settembre.

**Alternative scartate:** allineare il repository al copione (si perderebbe il lavoro già
fatto e il valore duraturo); pubblicare una versione «estesa» separata (due artefatti da
tenere allineati, e nessuno dei due completo).

**Fonti:** nessuna (decisione organizzativa)

---

<a id="adr-0018"></a>
## ADR-0018 — `pull_policy` parametrico, `never` sul profilo di palco

**Data:** 2026-08-25 · **Stato:** **Superata da [ADR-0039](#adr-0039)** il 2026-08-31

**Contesto:** [ADR-0009](#adr-0009) impone il funzionamento offline, ma la verifica ha
mostrato che Compose non ha una modalità offline documentata. L'unico meccanismo con una frase
esplicita è `pull_policy: never` — «Compose doesn't pull the image from a registry and relies
on the platform cached image. If there is no cached image, a failure is reported». Attorno c'è
un terreno accidentato: `--pull` ha valore predefinito `policy`; la documentazione è
internamente incoerente sui valori ammessi, perché `up` ne elenca tre, `create` quattro e
`docker compose pull` usa una flag diversa con due; e soprattutto «The `latest` tag is always
pulled even when the `missing` pull policy is used».

**Decisione:** ogni servizio dichiara `pull_policy: ${PULL_POLICY:-missing}`. Il profilo di
palco esporta `PULL_POLICY=never`. Nessuna immagine del lab usa il tag `latest`, in nessuna
circostanza.

**Conseguenze:** durante lo sviluppo il comportamento predefinito è comodo — le immagini
mancanti si scaricano da sole. Sul palco lo stack è blindato: se qualcosa manca, il fallimento
è immediato e dice cosa manca, invece di aprire una connessione che non ci sarà. La variabile
è una sola, sta nel file d'ambiente del profilo di palco e il preflight la controlla.

**Alternative scartate:** `pull_policy: never` fisso nei file (rende scomodo il primo avvio per
chi clona il repository, che è il momento in cui la rete serve davvero); passare `--pull never`
da riga di comando (si dimentica, e soprattutto non è scritto nel file: l'artefatto non
documenterebbe più il proprio comportamento).

**Motivo del superamento:** non il fine, ma il mezzo. L'obiettivo — nessun accesso al registro il
giorno del talk — è rimasto ed è quello di [ADR-0039](#adr-0039). A cadere è la forma parametrica.
Due ragioni. La prima è che [ADR-0027](#adr-0027), preso lo stesso giorno e più tardi, prescrive
`never` fisso e scarta `missing` per nome: due decisioni Accettata e opposte sono peggio di
entrambe, perché chi legge ne applica una a caso. La seconda è che l'ultima riga delle alternative
scartate qui sopra — «non è scritto nel file: l'artefatto non documenterebbe più il proprio
comportamento» — è l'argomento che smonta la decisione presa. Vale contro `--pull never` da riga di
comando e vale, identico, contro una variabile d'ambiente. Nemmeno la promessa «il preflight la
controlla» è stata mantenuta.

**Fonti:** [S-003](Sources.md#s-003), [S-019](Sources.md#s-019)

---

<a id="adr-0019"></a>
## ADR-0019 — I listener depositano in coda e ritornano subito

**Data:** 2026-08-25 · **Stato:** Accettata

**Contesto:** due lacune, scoperte separatamente, hanno la stessa soluzione. Da un lato
PyMongo è esplicito: «Events are delivered synchronously. Application threads block waiting
for event handlers (e.g. `started()`) to return. Care must be taken to ensure that your event
handlers are efficient enough to not adversely affect overall application performance.» Un
listener che disegna una tabella non rallenta soltanto l'interfaccia: rallenta il driver, e
falsa proprio le misure di failover che la demo esiste per mostrare. Dall'altro lato, la
documentazione di Rich non dice nulla sulla sicurezza di `Live` rispetto ai thread — la parola
non compare.

**Decisione:** il listener costruisce un evento immutabile, lo deposita in una `queue.Queue` e
ritorna. Il ciclo di disegno gira sul thread principale, svuota la coda a ogni giro e aggiorna
`Live`.

**Conseguenze:** il tempo trascorso dentro il listener è quello di un inserimento in coda,
quindi il driver non viene rallentato e le misure restano oneste. Un solo thread tocca `Live`,
quindi la domanda non documentata sulla sicurezza rispetto ai thread semplicemente non si
pone: non serve una risposta a una domanda che non ci si mette nella condizione di fare. In
più la coda è il punto naturale dove intercettare gli eventi per registrarli su file, che è
ciò che serve alle registrazioni di riserva ([ADR-0007](#adr-0007)).

**Alternative scartate:** disegnare direttamente dentro il listener (falsa le misure, ed è il
difetto che la documentazione PyMongo mette in guardia per primo); proteggere `Live` con un
lock (difenderebbe da un rischio che la documentazione non descrive, e serializzerebbe
comunque il driver dietro il disegno).

**Fonti:** [S-010](Sources.md#s-010), [S-018](Sources.md#s-018)

---

<a id="adr-0020"></a>
## ADR-0020 — Niente `testcontainers`: i test di integrazione usano gli stack del repository

**Data:** 2026-08-25 · **Stato:** Accettata — sostituisce [ADR-0011](#adr-0011)

**Contesto:** `MongoDbContainer` avvia un'istanza standalone e non conosce i replica set: il
modulo non nomina mai «replica», «replSet» o «rs.initiate», e il sorgente si limita alle tre
variabili di inizializzazione dell'immagine ufficiale, attendendo la riga di log `waiting for
connections`. La classe `DockerCompose` esiste nel codice della libreria ma non compare
nell'indice, nella pagina Core né nel `genindex` della documentazione pubblicata. Il quadro
complessivo non è rassicurante: il vecchio percorso `testcontainers.mongodb` è già uno shim
che avverte della propria deprecazione, e il sito descrive un layout di pacchetti superato
rispetto al repository.

**Decisione:** nessuna dipendenza da `testcontainers`. I test di integrazione avviano gli
stack Compose del repository e ci girano contro.

**Conseguenze:** una dipendenza in meno da tenere allineata, e soprattutto i test verificano
l'artefatto che il pubblico eseguirà davvero, non un facsimile costruito da una libreria. In
cambio i test di integrazione sono più lenti e richiedono Docker: restano separati dagli
unitari, con un obiettivo `make` distinto, così che la suite veloce resti veloce.

**Alternative scartate:** `MongoDbContainer` (standalone: per una demo di failover non serve);
`DockerCompose` della stessa libreria (dipendere da un'API non documentata, per ottenere ciò
che `docker compose` fa già).

**Fonti:** [S-013](Sources.md#s-013)

---

<a id="adr-0021"></a>
## ADR-0021 — Nomi host risolvibili ovunque, mai indirizzi IP

**Data:** 2026-08-25 · **Stato:** Accettata

**Contesto:** i membri di un replica set sono identificati dal campo `members[n].host` della
configurazione, e la raccomandazione è esplicita: «Always use resolvable hostnames for the
value of the `members[n].host` field in the replica set configuration to avoid confusion and
complexity». Ma c'è di più di una raccomandazione, e riguarda direttamente un lab in Docker:
«**Starting in MongoDB 5.0, nodes that are only configured with an IP address fail startup
validation and do not start.**» Con MongoDB 8.0 non è una questione di stile.

**Decisione:** i membri dei replica set e i riferimenti negli stack usano i nomi dei servizi
Compose, che la rete del progetto risolve. Nessun indirizzo IP compare in alcuna
configurazione.

**Conseguenze:** gli stack sopravvivono ai riavvii e alla riassegnazione degli indirizzi da
parte di Docker, che è un modo frequente e poco divertente di rompere un replica set fra una
prova e l'altra. L'applicazione in container risolve gli stessi nomi ([ADR-0012](#adr-0012)),
quindi la configurazione del cluster e quella del client parlano la stessa lingua.

**Alternative scartate:** indirizzi IP fissi su una rete Compose con sottorete statica (dalla
5.0 il nodo non parte proprio); nomi risolti tramite `/etc/hosts` dell'host (funziona per
l'host, non per i container, e richiede privilegi sulla macchina di chi prova il lab).

**Riserva dichiarata:** la pagina dimostra che i nomi host stanno nella configurazione, ma non
enuncia né che siano i nomi con cui i membri si raggiungono fra loro, né che i client li usino
per connettersi. Il nesso è deducibile, non citabile.

**Fonti:** [S-020](Sources.md#s-020)

---

<a id="adr-0022"></a>
## ADR-0022 — Il backup a caldo si dimostra sul replica set, mai sullo sharded cluster

**Data:** 2026-08-25 · **Stato:** Accettata

**Contesto:** la demo del backup sotto scrittura poggia su `--oplog`, che «creates a file named
`oplog.bson`» contenente le scritture avvenute durante il dump. L'opzione ha però un perimetro
stretto e documentato: «`--oplog` only works against nodes that maintain an oplog. This
includes all members of a replica set», e il divieto è netto — «**You can't run `mongodump`
with `--oplog` on a sharded cluster.**» Senza l'opzione, «if there are write operations during
the dump operation, the dump will not reflect a single moment in time».

**Decisione:** la demo del backup a caldo con carico di scrittura attivo si esegue sullo stack
replica set, con dump completo e `--readPreference=secondary`. Sullo standalone si mostra il
limite; sullo sharded cluster si mostra il divieto.

**Conseguenze:** il copione è vincolato all'ordine degli stack, il che va bene perché coincide
con la progressione del talk. Il limite diventa contenuto invece che imbarazzo: il motivo per
cui un backup coerente richiede un replica set è una delle cose che il pubblico si porta a
casa. Attenzione operativa: `--oplog` **fallisce** se combinato con `--db`, `--collection`,
`--dumpDbUsersAndRoles` o `--query` — «you must create a full dump of a replica set member» —
e fallisce anche se durante il dump un client esegue `renameCollection`, `$out`, `mapReduce`,
operazioni su utenti o ruoli, o `setDefaultRWConcern`. Il generatore di carico della demo non
deve fare nessuna di queste cose.

**Alternative scartate:** dump del singolo database con `--oplog` (fallisce, ed è documentato
che fallisca); backup a freddo con lo stack fermo (non dimostra il problema che la demo esiste
per mostrare).

**Nota sulla fonte:** il paradosso dello standalone — senza oplog non si può usare `--oplog`,
quindi il dump non può essere coerente a un istante — è vero e ricavabile, ma non è scritto in
questi termini. Le espressioni «point in time» e «does not guarantee» non compaiono nella
pagina.

**Fonti:** [S-011](Sources.md#s-011)

---

<a id="adr-0023"></a>
## ADR-0023 — L'ordine di avvio si esprime con `depends_on` e healthcheck

**Data:** 2026-08-25 · **Stato:** Accettata

**Contesto:** un replica set va inizializzato dopo che i mongod rispondono, e uno shard va
aggiunto dopo che il config server è pronto: l'ordine conta, e sbagliarlo dal vivo produce
errori che sembrano bug di MongoDB e non lo sono. La documentazione di `depends_on` distingue
le due forme senza ambiguità: «With short syntax, Compose does not wait for dependency
services to be "healthy" before starting a dependent service», contro «Compose waits for
healthchecks to pass on dependencies marked with `service_healthy`». Le condizioni disponibili
nella forma lunga sono esattamente tre: `service_started`, `service_healthy` e
`service_completed_successfully`.

**Decisione:** gli stack usano la forma lunga. `service_healthy` ovunque esista un healthcheck
significativo, `service_completed_successfully` per i lavori una tantum — la generazione del
keyfile, `rs.initiate()`, `addShard`. Nessuna attesa a tempo, in nessun punto: niente `sleep`
negli entrypoint, niente ritardi di avvio.

**Conseguenze:** l'avvio è deterministico e si comporta allo stesso modo su una macchina veloce
e su una lenta, il che dal vivo è tutto. Il costo è reale: ogni servizio deve avere un
healthcheck che verifichi qualcosa di vero, non che il processo esista. Sono righe in più nel
file, e sono righe che vale la pena mostrare.

**Alternative scartate:** la forma breve (non attende la salute, quindi non risolve il
problema); `sleep` negli entrypoint (funziona finché la macchina è quella su cui si è provato,
e fallisce davanti al pubblico su una più carica).

**Nota sulle versioni:** la forma lunga ammette anche `restart`, introdotto in Compose 2.17.0,
e `required`, in 2.20.0. Il repository dichiara la versione minima di Compose richiesta e il
preflight la verifica.

**Fonti:** [S-012](Sources.md#s-012)

---

<a id="adr-0024"></a>
## ADR-0024 — Gerarchia delle fonti: il materiale divulgativo non è documentazione normativa

**Data:** 2026-08-25 · **Stato:** Accettata

**Contesto:** cercando come si configura un cluster MongoDB si arriva facilmente alle pagine
`resources/products/fundamentals/` del sito del produttore. Sembrano documentazione: stesso
dominio, stesso marchio. Non lo sono. La pagina esaminata non contiene un comando, un file di
configurazione o un esempio di codice; l'unica procedura è un percorso di clic a cinque passi
nell'interfaccia di Atlas, fra due inviti alla prova gratuita. Non porta numero di versione né
data di pubblicazione, quindi non può sostenere alcuna affermazione versionata.

**Decisione:** la documentazione del progetto adotta una gerarchia esplicita delle fonti, in
ordine di precedenza decrescente: manuale ufficiale versionato; riferimento del formato o
della CLI; codice sorgente dell'immagine o della libreria, citato per commit e riga; verifica
empirica registrata come `V-NNN`; materiale divulgativo del produttore, mai come unica base di
un'affermazione; fonte comunitaria `C-NNN`, solo come indizio da verificare altrove.

**Conseguenze:** ogni affermazione tecnica in `docs/` è difendibile davanti a chi la controlla
dal fondo della sala, che è il criterio che conta. Le pagine divulgative restano utili come
raccolta di collegamenti verso il manuale, dove risiedono le frasi citabili. La gerarchia è
anche il motivo per cui `Sources.md` registra per ogni voce un verdetto e le riserve: sapere
dove una fonte smette di coprirci vale quanto sapere cosa afferma.

**Alternative scartate:** accettare qualunque pagina del produttore come normativa (comodo,
finché qualcuno non chiede a quale versione si riferisca); citare solo il manuale ed escludere
il resto (si perderebbero il codice sorgente delle immagini e le verifiche empiriche, che in
più di un punto sono le uniche fonti esistenti).

**Fonti:** [S-014](Sources.md#s-014)

---

<a id="adr-0025"></a>
## ADR-0025 — Dodici GiB alla VM Docker per il profilo `completo`

**Data:** 2026-08-25 · **Stato:** Accettata

**Contesto:** [ADR-0010](#adr-0010) ha diviso lo sharded cluster in due profili perché undici
container non stanno su una VM Docker da 7,65 GiB [V-002](Sources.md#v-002). Quella misura
però non era un limite dell'host, che di GiB ne ha 16: era il valore che Docker Desktop si era
assegnato da solo. Il profilo `completo` risultava così previsto come «eseguibile su una
macchina capiente» senza che una macchina capiente esistesse. Un profilo dichiarato nel file
Compose che nessuno ha mai visto partire non è documentazione: è una promessa. E il suo
destinatario non è il palco, è chi clona il repository per studiare le architetture.

**Decisione:** portare a 12 GiB la memoria assegnata alla VM Docker sulla macchina di sviluppo
e di palco. Il profilo `completo` diventa eseguibile in locale; il profilo `palco` resta quello
che va in scena.

**Conseguenze:** chi clona il repository può avviare lo sharded cluster nella sua forma
canonica — tre membri per ogni componente — invece di limitarsi a leggerne la descrizione. Di
riflesso, anche i filmati di riserva del blocco sharded possono mostrare quella forma. La
ripartizione dei ruoli resta quella di [ADR-0010](#adr-0010) e la decisione non la tocca:
`palco` è il profilo della presentazione, `completo` è il profilo dello studio, e i 12 GiB
servono a rendere il secondo eseguibile invece che teorico. All'host ne restano 4 per macOS, le
slide, il browser e la registrazione dello schermo: abbastanza quando non gira altro, stretti
durante il talk — un'altra ragione per cui dal vivo si esegue `palco`. Due obblighi ne
discendono: il `preflight` deve leggere la memoria effettiva della VM e avvisare quando è
inferiore a quanto il profilo richiesto pretende, invece di lasciare che sia Compose a
scoprirlo a metà avvio; e
[`06-sviluppo/gestione-risorse-compose.md`](06-sviluppo/gestione-risorse-compose.md) deve dire
in modo esplicito a chi serve ciascun profilo, quanto costa e con quale comando si sceglie.

**Alternative scartate:** restare a 7,65 GiB e registrare il profilo `completo` altrove (non
c'è un'altra macchina, e introdurrebbe nel repository un ambiente non riproducibile); salire
oltre i 12 GiB (lascerebbe all'host meno di quanto macOS occupa a riposo, e la registrazione
dello schermo è la prima cosa che ne soffrirebbe); comprimere i limiti per container fino a far
stare undici nodi in 7,65 GiB (si scenderebbe verso il minimo della cache WiredTiger, `0.256`
GB: il nodo parte, ma il comportamento sotto carico smette di essere rappresentativo, e sotto
carico è esattamente ciò che il talk mostra).

**Riserva dichiarata:** l'assegnazione è stata applicata e verificata — 11,67 GiB alla VM
[V-004](Sources.md#v-004) — ma che undici container ci entrino davvero non è misurato. La
verifica appartiene allo spike sharded, che deve produrre il numero e, se non torna, far
rientrare questa decisione con una che la superi.

**Nota di verifica (2026-08-25), che scioglie la riserva:** lo spike ha eseguito il profilo
`completo` per intero. Undici container occupano **1.356 MiB reali contro 6.144 MiB di
`mem_limit` dichiarati**, e nella VM restano 9.021 MiB disponibili
[V-006](Sources.md#v-006). La decisione non rientra: i 12 GiB bastano, e con margine. Il
numero però va letto per quello che è. `mem_limit` è un tetto, non una prenotazione, e durante
la misura il cluster era a riposo salvo gli inserimenti: il caso che consuma davvero è il
carico concorrente che l'applicazione del talk produrrà, e quello non esiste ancora. Il margine
va quindi considerato dimostrato per l'avvio e la topologia, non per il picco.

Una correzione minore alle alternative scartate, dove si legge che il minimo della cache
WiredTiger è `0.256` GB: il minimo imposto dal binario è `0.25`, e `0.25` configura esattamente
256 MiB perché l'opzione è letta in GiB [V-009](Sources.md#v-009). Il corpo non viene riscritto
e la seconda nota di revisione di [ADR-0004](#adr-0004) porta la correzione per esteso.
L'argomento regge invariato — comprimere undici nodi verso il pavimento della cache resta
scartato perché il comportamento sotto carico smetterebbe di essere rappresentativo — a
cambiare è soltanto la cifra.

**Fonti:** [S-001](Sources.md#s-001), [V-002](Sources.md#v-002), [V-004](Sources.md#v-004), [V-006](Sources.md#v-006), [V-009](Sources.md#v-009)

---

<a id="adr-0026"></a>
## ADR-0026 — La catena di inizializzazione dello sharded cluster

**Data:** 2026-08-25 · **Stato:** Accettata

> **Nota di allineamento, 2026-08-31.** La *decisione* di questo ADR regge intatta. Una sua
> *conseguenza* è stata misurata falsa: la frase «l'inizializzazione non può stare tutta in
> `docker-compose.yml`: serve un passo esterno» non vale, e [ADR-0040](#adr-0040) mostra come farla
> stare dentro Compose senza rinunciare a niente di quanto deciso qui. Il corpo non viene toccato:
> si legge com'era, con questo rimando davanti.

**Contesto:** il design descriveva lo sharded cluster come una topologia — un config server,
due shard, un router — senza dire come i pezzi arrivano a conoscersi sotto autenticazione a
keyfile. Lo spike del 2026-08-25 ha provato a montarlo davvero
[V-006](Sources.md#v-006), e tre passaggi che sembravano meccanici si sono rivelati sbagliati.
Il primo: passare `MONGO_INITDB_ROOT_USERNAME` e `MONGO_INITDB_ROOT_PASSWORD` a un nodo
`--configsvr` lo fa uscire con `BadValue`, perché l'entrypoint dell'immagine ufficiale toglie
`--replSet` per avviare un mongod temporaneo con cui creare l'utente
[S-022](Sources.md#s-022), ma non toglie `--configsvr`, e un config server standalone non
esiste. Il secondo: `rs.initiate()` senza argomenti registra come host l'ID del container,
irraggiungibile dagli altri. Il terzo: l'eccezione localhost concede meno di quanto il nome
suggerisca — solo la creazione del primo utente o ruolo, non comandi diagnostici — e dopo
`sh.addShard()` una connessione diretta a uno shard con le credenziali del cluster viene
rifiutata.

**Decisione:** la catena di inizializzazione è fissata in sei passi, nell'ordine, ed è la
stessa per entrambi i profili. Un servizio one-shot genera il keyfile con `openssl rand
-base64 756`, lo assegna a `999:999` — l'utente `mongodb` dell'immagine
[S-023](Sources.md#s-023) — e lo porta a `chmod 400`. I `mongod` partono con `--keyFile` e
**senza** variabili di root. Si esegue `rs.initiate()` elencando i membri per nome di servizio
Compose. Si crea l'utente amministratore sul config server, sotto eccezione localhost. Si
avviano i `mongos`. Si eseguono le `sh.addShard()` autenticati. Dove una demo debba ispezionare
un singolo shard, quel nodo riceve anche un utente locale, creato apposta.

**Conseguenze:** l'inizializzazione non può stare tutta in `docker-compose.yml`: serve un passo
esterno, che sia uno script o un servizio dedicato, perché `rs.initiate()` va eseguito dopo che
i nodi sono `healthy` e prima che il router serva. Lo stesso vale per il replica set di
`feature/02`, che è la stessa catena senza gli shard: le due feature condividono il
meccanismo e vanno scritte per condividerlo. La documentazione ne guadagna: la distinzione fra
utenti del cluster e utenti locali allo shard è materia da
`03-amministrazione/sicurezza-keyfile-x509.md`, e il fatto che `MONGO_INITDB_ROOT_*` non serva
a niente su un config server è materia da `02-architetture/trappole-mongodb-in-docker.md`.
Sulla topologia lo spike non lascia dubbi: cinquantamila documenti si sono distribuiti sui due
shard, e fermando il primario di uno shard il cluster ha continuato a leggere e scrivere
attraverso mongos, con il nodo rientrato da solo come secondario al riavvio.

**Alternative scartate:** usare `MONGO_INITDB_ROOT_*` solo sugli shard e non sul config server
(funzionerebbe, ma renderebbe l'avvio di due componenti simili asimmetrico per un motivo che
nessuno ricorderebbe sei mesi dopo); affidarsi a `rs.initiate()` senza argomenti e correggere
dopo la configurazione con `rs.reconfig()` (due passi invece di uno, e uno stato intermedio
sbagliato che può essere osservato); montare il keyfile dall'host anziché generarlo in un
volume (i permessi dei file montati da macOS non sono governabili con `chmod`, ed è
esattamente il tipo di dettaglio che funziona sulla macchina di chi scrive e fallisce su
quella di chi clona).

**Riserva dichiarata:** lo spike ha usato MongoDB 7.0.40, non la versione che finirà nel lab —
vedi [ADR-0028](#adr-0028). La catena non dipende dalla versione in nessuno dei suoi passi, ma
questo non è stato verificato su una 8.x, perché su questo kernel nessuna 8.x pubblicata si
avvia.

**Fonti:** [S-022](Sources.md#s-022), [S-023](Sources.md#s-023), [V-006](Sources.md#v-006)

---

<a id="adr-0027"></a>
## ADR-0027 — `pull_policy: never`, e un preflight che avvia l'immagine invece di censirla

**Data:** 2026-08-25 · **Stato:** Accettata

**Contesto:** [ADR-0009](#adr-0009) lasciava aperta una domanda: se un'immagine è pinnata per
digest ed è già nella cache locale, `docker compose up` contatta comunque il registro? La
domanda era mal posta. Invece di cercare una prova che Compose non esca, conviene toglierli la
possibilità di farlo: la Compose Specification prevede `pull_policy`, e il valore `never`
significa che l'immagine non viene mai scaricata. Nel frattempo lo spike ha messo in luce un
buco più serio [V-007](Sources.md#v-007). Il `preflight` verificava che le immagini pinnate
fossero presenti in cache, e passava — mentre nessuna di quelle immagini era in grado di
avviarsi su questo kernel. «Presente» e «funzionante» sono due proprietà diverse, e il
controllo ne misurava una sola.

**Decisione:** ogni servizio di ogni stack porta `pull_policy: never`. E il `preflight` esegue
l'immagine pinnata — `mongod --version` in un container usa e getta — trattando un'uscita
diversa da zero come errore bloccante.

**Conseguenze:** l'assenza di rete smette di essere una speranza e diventa una proprietà del
file Compose, leggibile da chi lo apre. Il fallimento è immediato e dice la cosa giusta:
digest presente, container avviato in 0,674 s; digest inesistente, `No such image` in 0,110 s
[V-006](Sources.md#v-006). Un decimo di secondo non è un tentativo di rete andato male: è un
tentativo di rete mai iniziato. Il costo è che `make images-pull` diventa obbligatorio prima
del primo avvio, invece di essere una comodità: chi clona il repository e lancia direttamente
`compose up` riceve un errore anziché uno scaricamento implicito. È il compromesso giusto —
l'errore arriva a casa propria, con la rete, non in sala. Sul preflight, il controllo aggiunto
costa mezzo secondo e copre l'unica classe di guasto che sarebbe passata indenne attraverso
tutti gli altri fino al `compose up` sul palco.

**Alternative scartate:** `pull_policy: missing`, il comportamento predefinito (scarica se
manca: esattamente ciò che non deve accadere il 18 settembre); lasciare che sia
`tools/pull-images.sh --verify` l'unico presidio (verifica la presenza, che è la proprietà
sbagliata, come questo spike ha dimostrato); far provare al preflight un avvio completo dello
stack (dura minuti, richiede porte libere e lascia volumi da ripulire — `mongod --version`
esercita lo stesso percorso di codice che fallisce, in mezzo secondo e senza effetti).

**Fonti:** [V-006](Sources.md#v-006), [V-007](Sources.md#v-007)

---

<a id="adr-0028"></a>
## ADR-0028 — La versione di MongoDB del lab

**Data:** 2026-08-25 · **Stato:** Accettata — sostituisce [ADR-0008](#adr-0008)

**Contesto:** [ADR-0008](#adr-0008) fissa MongoDB 8.0, immagine ufficiale pinnata per digest.
Lo spike del 2026-08-25 ha scoperto che quella decisione non è eseguibile
[V-007](Sources.md#v-007): sul kernel `7.0.12-linuxkit` della VM di Docker Desktop, `mongod`
esce prima di leggere i parametri con un messaggio fatale — «Linux kernel versions 6.19 and
newer has a known incompatibility with this version of MongoDB». Riguarda la 8.0.29, che è
l'ultima patch pubblicata della 8.0, e la 8.3.8, che è la stabile corrente. Nessuna variabile
d'ambiente e nessun parametro di avvio lo aggira. La causa è l'allocatore TCMalloc, che nella
cache per-CPU usa `rseq` in un modo che il kernel dal 6.19 non tollera più; MongoDB ha reagito
prima trasformando il crash in un'uscita pulita, poi restringendo il controllo ai soli kernel
dal 7.0.14 in su. La correzione esiste, ed è datata: compare nel changelog sotto la **8.0.30**
[S-028](Sources.md#s-028). Ma i binari della 8.0.30 non sono pubblicati — né su Docker Hub, né
sull'immagine di MongoDB, né nel feed dei download.

Restano in piedi due versioni: la 8.2.12 e la 7.0.40. La 8.2.12 si avvia, ma non perché sia
sana: è *precedente* all'introduzione del controllo, quindi gira sul percorso difettoso, ed è
la famiglia per cui è segnalato un ciclo di crash con SIGSEGV. Ha inoltre un difetto
amministrativo che da solo basterebbe: con il nuovo schema di rilascio adottato dalla 8.2, «After
a new minor release becomes available, MongoDB does not continue patching the previous minor
release» [S-027](Sources.md#s-027). Uscita la 8.3, la 8.2 non riceve più patch, e infatti fra i
tag correnti dell'immagine ufficiale non compare più.

**Decisione:** adottare **MongoDB 7.0.40** come versione del lab, con la 8.0.30 come
traguardo. Si sviluppa e si documenta su 7.0.40 adesso; si ripinna alla 8.0.30 appena i binari
escono, rigenerando `tools/images.env` con `make images-pull`. Se questo accade prima del 18
settembre, si ripinna e si rigirano i filmati; se non accade, il lab funziona lo stesso. Il
costo del cambio è basso per costruzione: la versione è una variabile sola, `${MONGO_IMAGE}`,
e questo è il motivo per cui [ADR-0008](#adr-0008) la teneva fuori dai file Compose.

**Conseguenze:** [ADR-0008](#adr-0008) è superata — non riscritta — da questa: lo stato è
aggiornato e il rimando è al suo posto. Il pinning per digest **non** è in discussione, resta
la regola e viene ereditato qui; a cambiare è solo quale versione si pinna. Le pagine che nominano una versione vanno allineate, e
non sono molte proprio perché la versione è parametrica. Il talk parla di una 7.0 anziché di
una 8.0: sulle architetture non cambia nulla, perché replica set, sharding, `mongodump` e
`mongorestore` si comportano allo stesso modo, ma va detto dal palco invece che lasciato
scoprire a chi legge il prompt di `mongosh`. In compenso il progetto guadagna un contenuto che
non aveva: l'incompatibilità è **di tutti**, non nostra, e chiunque in sala avvii oggi MongoDB
8 su Docker Desktop incontra lo stesso muro. È materiale da
`02-architetture/trappole-mongodb-in-docker.md`, e vale più di una slide teorica sulla scelta
delle versioni.

**Alternative scartate:** la 8.2.12, perché non riceve più patch e si avvia solo in quanto
precede il controllo — sarebbe scegliere la versione difettosa fra quelle disponibili, per il
solo gusto di scrivere «8» sulle slide; aspettare la 8.0.30 come piano unico, perché mancano
ventiquattro giorni al talk e la data di pubblicazione non esiste; cambiare runtime o
retrocedere la versione di Docker Desktop per ottenere un kernel più vecchio, perché
imporrebbe a chi clona il repository di replicare una versione precisa di un prodotto che si
aggiorna da solo, ed è la definizione di lab non riproducibile.

**Riserva dichiarata, sciolta in parte il 2026-08-25:** la ricostruzione della causa poggiava
su ticket Jira linkati dal messaggio d'errore, non su documentazione di piattaforma; il primo
è chiuso con risoluzione «Gone away» e senza *Fix Version* [V-007](Sources.md#v-007). Il
manuale però la conferma dove non si pensava di cercarla, cioè nelle note di compatibilità:
«Starting in MongoDB 8.0, MongoDB uses an upgraded version of TCMalloc that uses **per-CPU
caches, instead of per-thread caches**» [S-029](Sources.md#s-029). È la 8.0 a introdurre il
meccanismo che il kernel dal 6.19 non tollera più: la scelta della 7.0 non aggira il problema
per fortuna, lo precede per costruzione. Il fatto osservabile — quali
versioni si avviano e quali no — è invece misurato e ripetibile. Non è stato verificato se la
8.0.30, una volta pubblicata, si avvii davvero su questo kernel: al momento non esiste nulla
da provare.

**Nota di verifica (2026-08-25):** la frase «sulle architetture non cambia nulla», scritta
qui sopra, è stata controllata contro le note di compatibilità della 8.0 e va corretta.
Regge su replica set, sharding, `mongodump` e `mongorestore`, che nella pagina non compaiono
affatto — ma la 8.0 elenca fra le *Backward-Incompatible Features* il divieto di eseguire
comandi collegandosi **direttamente** a uno shard: «you must either connect to `mongos` or
have the maintenance-only `directShardOperations` role», e il vincolo scatta «once the
cluster has more than one shard» [S-029](Sources.md#s-029). Lo spike ha fatto esattamente
quello per leggere `hostInfo` da uno shard: su 8.0 sarebbe stato respinto. Cambia anche la
semantica di `majority`, che dalla 8.0 conferma sulla **scrittura** dell'oplog invece che
sull'**applicazione** — una differenza osservabile proprio nelle misure di failover che
l'applicazione cronometra. Nessuna delle due ribalta la decisione: la prima rende la 7.0 più
comoda per la demo, la seconda va detta quando si mostrano i tempi. Va detta anche la forma
del ragionamento: una pagina di *compatibility changes* elenca ciò che rompe, non ciò che
resta uguale, e l'assenza di una voce è un indizio forte, non una prova.

**Fonti:** [S-027](Sources.md#s-027), [S-028](Sources.md#s-028), [S-029](Sources.md#s-029), [V-007](Sources.md#v-007), [V-008](Sources.md#v-008)

---

<a id="adr-0029"></a>
## ADR-0029 — Gli strumenti di repository non poggiano su comportamenti indefiniti

**Data:** 2026-08-28 · **Stato:** Accettata

**Contesto:** il `Makefile`, `tools/pull-images.sh`, `tools/preflight.sh` e
`tools/check_citations.py` sono la prima cosa che esegue chi clona, e la eseguono su una
macchina che non abbiamo mai visto. Fino a oggi nessuna decisione li governava: il criterio in
vigore era implicito, ed era «funziona sulla macchina di sviluppo».

La review esterna di PR #1 ne ha mostrato il limite su un caso minuscolo e istruttivo. Il
target `help`, che è anche quello predefinito, separava i campi con `FS = ":.*?## "` — l'idioma
che circola in migliaia di Makefile. Il rilievo prediceva che `awk` cercasse un `?` letterale e
che `make help` fosse rotto. Non è così, ed è falsificabile in un comando: le descrizioni si
stampano e l'uscita è `0`. Ma sotto la diagnosi sbagliata c'era un'osservazione giusta. `awk`
usa gli ERE — «The `awk` utility shall make use of the extended regular expression notation»
[S-031](Sources.md#s-031) — e negli ERE il non-greedy non esiste: quella `?` non è un
modificatore, è un secondo quantificatore attaccato al primo, e «The behavior of multiple
adjacent duplication symbols ( '+', '\*', '?', and intervals) produces undefined results»
[S-030](Sources.md#s-030).

Il punto interessante non è che sia indefinito, è che lo standard dice **cosa può succedere**:
«this may entail an error, enabling an extended syntax for that RE, or using the construct in
error as literal characters to be matched» [S-030](Sources.md#s-030). Tre esiti, tutti leciti.
La previsione del rilievo era il terzo; quello che accade davvero sull'`awk` della macchina di
sviluppo è il secondo. Entrambi sono ammessi — ed è esattamente il punto: il comportamento non
è sbagliato, è **non garantito**. POSIX lo dice anche in positivo: «Strictly Conforming
applications cannot use such constructs.»

**Decisione:** gli strumenti di repository si attengono al comportamento definito dallo
standard che li governa, anche quando il costrutto indefinito funziona qui. Dove esiste una
forma definita ed equivalente si usa quella; la ragione si scrive nell'artefatto, accanto alla
riga, con il rimando alla fonte, perché è lì che la legge chi si chiede perché il codice non
somigli all'idioma diffuso. Prima applicazione: `FS = ":.*## "`, con l'output verificato
identico byte per byte prima e dopo la modifica.

**Conseguenze:** la regola costa quasi niente da applicare e compra la sola proprietà che
serve, cioè che lo strumento si comporti allo stesso modo sulla macchina di chi clona. Non
promette portabilità: toglie una classe di sorpresa, non tutte. Introduce invece un obbligo di
prova — chi afferma che un costrutto è indefinito deve citare dove sta scritto — e apre la
sede che mancava. Questo è il primo ADR che governa `tools/` e il `Makefile`, ed è il posto
naturale per le fonti future sullo stesso argomento.

C'è un effetto collaterale che vale la pena registrare, perché riguarda il metodo e non il
codice. Il 2026-08-28 la fonte POSIX era rimasta fuori da [`Sources.md`](Sources.md) per una
ragione puramente strutturale: ogni voce dev'essere citata da un ADR, altrimenti il controllo
la dichiara orfana, e nessun ADR copriva gli strumenti. La regola anti-orfane, che esiste per
impedire la bibliografia decorativa, stava impedendo di registrare una fonte legittima solo
perché troppo piccola. Questo ADR scioglie il nodo: le due voci hanno una casa.

**Alternative scartate:** lasciare `*?` e annotarne l'innocuità (documenterebbe che un
costrutto non garantito oggi funziona, cioè la premessa che invecchia peggio); verificare
l'espressione su più implementazioni di `awk` invece di cambiarla (sposta il costo su chi
rilegge e non copre comunque l'implementazione che non abbiamo provato); imporre agli
strumenti la conformità stretta a POSIX (nessuno degli script lo è né vuole esserlo: usano
`bash` con array, `local` e `[[ ]]`, per scelta consapevole e dichiarata nello shebang. La
regola qui è più modesta e riguarda i costrutti che lo standard applicabile dichiara
indefiniti, non l'adesione integrale a un profilo).

**Fonti:** [S-030](Sources.md#s-030), [S-031](Sources.md#s-031)

---

<a id="adr-0030"></a>
## ADR-0030 — Il log del lab sta su stdout, e a ruotarlo pensa il runtime

**Data:** 2026-08-28 · **Stato:** Accettata

**Contesto:** il design del 24 agosto, al §5.3, dava per acquisito un «doppio canale di log
deliberato: stdout (per `docker compose logs`) **e** file `--logpath`». L'idea era comoda: il
comando che tutti conoscono per guardare i log di un container, e insieme un file dentro il
container su cui mostrare le procedure amministrative. Il piano di `feature/01` ha messo questo
assunto in cima al task invece che in fondo, con la formula «questo task comincia con una misura,
non con del codice». Ha fatto bene: l'assunto è falso.

`--logpath` è una **redirezione**, non una duplicazione. Due container identici salvo quel flag
producono le stesse sessantacinque righe di avvio, ma o in `docker logs` o nel file, mai in
entrambi [V-010](Sources.md#v-010). Non è una sottigliezza da scoprire eseguendo: lo dice
l'aiuto del binario dentro l'immagine del lab — «Log file to send write to **instead of**
stdout» — e lo dice il manuale, che tratta le tre destinazioni come alternative esplicite,
«Specify **either** `file` or `syslog`», con stdout come ripiego di chi non sceglie
[S-032](Sources.md#s-032). Il canale doppio non esiste e non c'è un'opzione per costruirlo.

Bisogna quindi scegliere, e la scelta ha una conseguenza che va guardata prima di deciderla.
`logRotate`, il comando che il capitolo di amministrazione deve insegnare, su un `mongod` che
scrive su stdout risponde `{"ok":1}`, scrive a log «Log rotation initiated» e **non fa
assolutamente niente**. La risposta è indistinguibile da quella del caso in cui il file c'è ed è
stato davvero rinominato [V-010](Sources.md#v-010). Rinunciare al file non toglie un comando
dall'insegnamento: lo trasforma in un comando che mente.

C'è poi un secondo fatto, che scegliere stdout tira dentro per forza. Il driver `json-file`, che
è il predefinito, nasce con `LogConfig` vuoto: nessun `max-size`, nessun `max-file`, e `max-size`
vale `-1 (unlimited)` [S-033](Sources.md#s-033), [V-011](Sources.md#v-011). `mongod` scrive una
riga per ogni connessione aperta e una per ogni connessione chiusa, e la demo sulle prestazioni
apre e chiude connessioni a raffica perché è precisamente ciò che misura. Su stdout, senza
limiti, la demo che dimostra le prestazioni è anche quella che riempie il disco.

**Decisione:** tre clausole, che sono la stessa decisione vista da tre lati.

1. **Nessuno stack del lab dichiara `--logpath`.** Il log di ogni `mongod` e di ogni `mongos` va
   su stdout, e si guarda con `docker compose logs`. Dal palco «adesso vi mostro i log» deve
   essere un comando solo, quello che il pubblico ha già visto mille volte.
2. **Ogni servizio dichiara `logging:` con `driver: json-file`, `max-size: "10m"` e
   `max-file: "3"`.** Trenta MiB per container: molto più di quanto qualunque demo produca, e
   molto meno di un disco pieno a metà talk. Il driver è dichiarato per esteso e non solo le
   opzioni, perché su un host che ha già cambiato `log-driver` nel proprio `daemon.json` le sole
   opzioni potrebbero applicarsi a un driver diverso.
3. **La rotazione con `logRotate` si insegna dove ha senso, cioè sull'installazione su ferro.**
   Il capitolo `docs/03-amministrazione/log.md` mostra le due situazioni una accanto all'altra e
   dice qual è la differenza: dentro un container il log lo possiede il runtime e lo ruota il
   runtime; su una macchina dove `mongod` è un servizio di sistema, il log lo possiede `mongod` e
   lo ruota `logRotate`, in coppia con `logrotate(8)` e `--logRotate reopen`. La dimostrazione di
   `logRotate` si fa su un container avviato apposta con `--logpath`, fuori dagli stack.

**Conseguenze:** `docker compose logs -f` funziona su tutti e tre gli stack, il che è la
proprietà che serve dal palco e che si sarebbe persa in silenzio. Il capitolo sui log ci guadagna
la distinzione che vale davvero la pena portare a casa — dove sta il log dipende da come hai
avviato il processo, chi lo ruota dipende da chi lo possiede — e la porta con una misura sotto
invece che come opinione. Nel conto ci va anche l'onestà di aver corretto il design: il §5.3
resta come sta, perché i documenti storici non si riscrivono, e questo ADR è il posto dove è
scritto che quella riga descriveva una cosa che non esiste.

Il costo è un container in più da avviare quando si dimostra la rotazione, e una tentazione da
disinnescare: chi copia un file Compose del lab e ci aggiunge `--logpath` perde
`docker compose logs` senza capire perché. Per questo il commento accanto al comando, dentro il
file, dice che l'assenza di `--logpath` è deliberata e rimanda alla misura.

**Alternative scartate:** tenere `--logpath` e guardare i log con `docker exec … tail -f` (si
ottiene il file, si perde il comando che tutti conoscono; e in una demo il comando familiare vale
più del file); usare `mongod … | tee /var/log/mongod.log` come comando del container (metterebbe
una shell come PID 1, e il `SIGTERM` di `docker stop` arriverebbe alla shell invece che a
`mongod`: chiusura sporca, e i dieci secondi di grazia prima del `SIGKILL`. Su un lab che
dimostra il guasto di un nodo, rovinare la chiusura pulita è l'esatto contrario di ciò che
serve); `--logpath /dev/stdout` (si ottiene l'output su stdout dichiarando però a `mongod` che
esiste un file, con `logRotate` che proverebbe a rinominare `/dev/stdout`: un modo elaborato di
ottenere il comportamento predefinito, più un modo nuovo di rompersi); non dichiarare `logging:`
e fidarsi del daemon (il predefinito è nessun limite, misurato, e due righe costano meno di un
disco pieno); `max-size` più generoso (dieci MiB di JSON sono decine di migliaia di righe: il
limite non si incontra in una demo, si incontra in un ciclo impazzito, che è appunto il caso da
contenere).

**Una nota su un'apparente contraddizione.** Fra le alternative appena scartate c'è `--logpath`
puntato su un descrittore invece che su un file — e l'entrypoint ufficiale fa esattamente questo:
`--logpath "/proc/$$/fd/1"` per il `mongod` temporaneo della fase di inizializzazione
[S-034](Sources.md#s-034). Non è una smentita, è un caso diverso, e vale la pena dirlo prima che
lo dica una review. Quel `mongod` è avviato con `--fork`, e `--fork` **obbliga** a dichiarare un
`--logpath`: l'entrypoint non sta scegliendo fra file e stdout, sta scegliendo fra un file e un
descrittore, perché la terza possibilità gli è preclusa. E lo fa su un processo che vive qualche
secondo, su cui nessuno chiamerà mai `logRotate`. Il nostro `mongod` non forka, quindi la scelta
ce l'ha; e vive quanto dura il talk, quindi la rotazione lo riguarda davvero.

Resta però l'osservazione che conta di più: per far uscire su stdout i log di un `mongod` con
`--logpath`, chi costruisce l'immagine ufficiale ha dovuto ricorrere a un espediente, corredato
di due link di giustificazione nel codice. È la conferma, dal lato di chi l'immagine la scrive,
che il canale doppio non esiste.

**Fonti:** [S-032](Sources.md#s-032), [S-033](Sources.md#s-033), [S-034](Sources.md#s-034), [V-010](Sources.md#v-010), [V-011](Sources.md#v-011), [V-012](Sources.md#v-012)

---

<a id="adr-0031"></a>
## ADR-0031 — Il dataset di demo è deterministico, e chi decide se esiste è il volume

**Data:** 2026-08-28 · **Stato:** Accettata

**Contesto:** tutte le demo hanno bisogno di dati, e tre vincoli decidono che dati.

Il primo viene dal palco. Le demo sono dal vivo con una registrazione di riserva
[ADR-0016](#adr-0016): se qualcosa va storto e si passa al filmato, i numeri sullo schermo devono
essere gli stessi di prima, altrimenti il salto lo vede il pubblico. Un dataset che cambia a ogni
avvio rende la riserva inutilizzabile proprio nel momento in cui serve.

Il secondo viene dal riuso. Gli stessi dati serviranno agli stack 02 e 03 e all'applicazione
Python: nascere in una forma copiabile costa poco adesso e molto dopo.

Il terzo viene dal meccanismo. In Docker il caricamento iniziale passa da
`/docker-entrypoint-initdb.d`, e quel meccanismo ha un comportamento che nessuno si aspetta: gli
script vengono eseguiti **solo** se il volume non è già inizializzato, e quando non lo sono
l'entrypoint **non stampa niente** — verificato eseguendo, con i dati cancellati che non tornano
e zero righe di log a dirlo [V-014](Sources.md#v-014). Il criterio non è nemmeno «la cartella è
vuota»: è la presenza di uno fra quattro percorsi noti dentro `dbPath`
[S-034](Sources.md#s-034). Chi sviluppa il lab incontrerà questa trappola il primo giorno,
modificando il seed e non vedendo cambiare niente.

**Decisione:** cinque clausole.

1. **Il dataset è uno script JavaScript versionato, non un dump binario.** Si legge in una
   review, si confronta con un `diff`, non pesa sul repository [S-021](Sources.md#s-021) e non
   va rigenerato quando cambia la versione di MongoDB.
2. **Ogni sorgente di variabilità è bandita.** Nessun `Math.random()`, nessun `new Date()` senza
   argomento, `_id` espliciti e sequenziali, epoca fissa dichiarata come costante. Il generatore
   è uno **xorshift a 32 bit** con seme fisso, e non un congruenziale lineare: in JavaScript il
   prodotto di un LCG sfonda i 2^53 interi esatti, e i suoi bit bassi hanno periodo cortissimo.
   La prima versione di questo file sbagliava su entrambi i fronti e produceva cinque città con
   diecimila ordini e cinque con qualche decina [V-013](Sources.md#v-013).
3. **Il seed non crea indici.** Il confronto fra la stessa interrogazione con e senza indice è
   una delle demo: crearlo qui toglierebbe il «prima».
4. **Il file vive in un posto solo** e gli stack successivi lo riusano invece di copiarlo.
5. **La semantica dell'entrypoint si accetta e si documenta, non si aggira.** Il modo di
   ricaricare da zero è `docker compose down -v`; e perché non sia l'unico modo, il `Makefile`
   espone `make seed-01`, che esegue lo stesso file su uno stack già in piedi. Due strade
   esplicite sono meglio di una implicita che ogni tanto non parte.

**Conseguenze:** la riserva registrata diventa davvero intercambiabile con la demo dal vivo, che
era il punto. La distribuzione uniforme rende onesto il confronto con e senza indice: con la
prima versione del generatore, la differenza fra due misure sarebbe stata la selettività della
città e non l'indice, e sarebbe passata per un risultato. Il caricamento costa 1,7 secondi e sta
comodamente dentro lo `start_period` dell'healthcheck [V-013](Sources.md#v-013).

Il prezzo è una trappola che resta nel prodotto e che quindi va insegnata invece che nascosta:
finisce in `docs/02-architetture/trappole-mongodb-in-docker.md` e in un commento dentro il file
Compose, accanto alla riga del montaggio. Questa è la forma che qui prende il principio secondo
cui un comportamento sorprendente documentato vale più di un comportamento sorprendente
aggirato — chi copia il file si porta dietro anche la spiegazione.

**Alternative scartate:** un dump con `mongorestore` (binario, illeggibile in review, pesante nel
repository, e da rigenerare a ogni cambio di versione); un servizio «seeder» separato che attende
`service_healthy` e carica (più parti mobili, e dovrebbe decidere da sé se i dati ci sono già,
cioè reimplementare male il controllo che l'entrypoint fa già); `Math.random()` con un seme
(JavaScript non permette di seminare `Math.random`: non è una preferenza, non si può);
sostituire l'entrypoint con uno script nostro per forzare il seed a ogni avvio (si perde
l'allineamento con l'immagine ufficiale e si guadagna un file da mantenere, per un problema che
si risolve con un target del `Makefile`); ridurre il dataset a poche centinaia di documenti per
velocizzare l'avvio (1,7 secondi non sono un problema, e con poche centinaia di documenti la
differenza fra scansione e indice non si vede).

**Fonti:** [S-021](Sources.md#s-021), [S-034](Sources.md#s-034), [V-013](Sources.md#v-013), [V-014](Sources.md#v-014)

---

<a id="adr-0032"></a>
## ADR-0032 — L'istanza singola si presenta con quattro limiti citabili, non con un aggettivo

**Data:** 2026-08-28 · **Stato:** Accettata

**Contesto:** il talk apre con l'istanza singola e dura sessanta minuti perché quell'istanza non
basta. La frase che regge tutto il resto — «un nodo solo non basta» — è però anche la più facile
da dire male: si può dire in modo vago («non è affidabile»), in modo apocalittico («si perdono i
dati»), o in modo sbagliato («non va mai bene in produzione»). Le prime due non si possono
verificare, la terza è falsa, e un pubblico di professionisti se ne accorge in tutti e tre i casi.

C'è poi un rischio specifico del formato. Chi presenta tre architetture in fila ha un incentivo a
far sembrare la prima peggiore di quanto sia, perché rende più interessanti le altre due. È
esattamente il tipo di scorciatoia che [ADR-0024](#adr-0024) esiste per impedire: quella gerarchia
distingue ciò che è documentato da ciò che è stato verificato da ciò che è opinione, e «lo standalone
è fragile» non appartiene a nessuna delle tre categorie.

Nel corso del Task 7 sono emerse due cose che la sola lettura del manuale non avrebbe dato.

La prima è che i limiti dell'istanza singola non si comportano allo stesso modo. Tre su quattro
sono **rumorosi**: si chiede un change stream e arriva `Location40573`, si chiede `rs.status()` e
arriva `NoReplicationEnabled`, si chiede `w: 2` e arriva `BadValue`. Il quarto è **silenzioso**:
`w: "majority"` su un'istanza singola riesce, restituisce `acknowledged: true`, e non dà nulla in
più di `w: 1` [V-015](Sources.md#v-015). Un'applicazione scritta per un replica set, diligentemente
piena di `w: "majority"`, puntata su un nodo solo continua a funzionare con una garanzia in meno di
quella che il suo codice crede di avere. Nessun messaggio la avverte.

La seconda è che la perdita di dati si può misurare invece di evocarla. Con `w: 1` e `j` non
specificato — il caso predefinito — [S-035](Sources.md#s-035) dice che l'acknowledgement è «In
memory», e [S-036](Sources.md#s-036) dice che il journal tocca il disco «At every 100
milliseconds» e che «updates can be lost following a hard shutdown». Messe insieme, le due frasi
descrivono una finestra. Aprirla è bastato un `SIGKILL`: il client aveva ricevuto conferma fino al
documento 41.558, ne sono sopravvissuti 41.458, **cento scritture confermate e perdute**
[V-016](Sources.md#v-016).

**Decisione:** `docs/02-architetture/standalone.md` dichiara i limiti dell'istanza singola in
quattro affermazioni, e ciascuna porta la fonte primaria che la sostiene.

1. **Nessuna ridondanza e nessun failover.** Il processo che muore è il servizio che finisce. Non
   c'è nulla da eleggere: `rs.status()` risponde `NoReplicationEnabled` perché non c'è replica set
   [V-015](Sources.md#v-015).
2. **`w: 1` è tutto ciò che si può chiedere, e `w: "majority"` è la stessa cosa travestita.**
   `w > 1` viene rifiutato [S-035](Sources.md#s-035); `w: "majority"` viene accettato in silenzio.
   La pagina spiega che l'ack di `w: 1` è la memoria e mostra i cento documenti persi
   [V-016](Sources.md#v-016).
3. **Nessun oplog, quindi nessun change stream e nessun backup a caldo coerente.** `local` contiene
   la sola `startup_log` [V-015](Sources.md#v-015); i change stream «are available for replica sets
   and sharded clusters» [S-038](Sources.md#s-038); `mongodump --oplog` fallisce, e fallisce con un
   messaggio che parla d'altro. Il seguito è in [ADR-0022](#adr-0022).
4. **La manutenzione richiede una finestra di fermo.** Aggiornare la versione, cambiare
   configurazione, spostare i dati: ogni operazione che ferma il processo ferma il servizio, perché
   non c'è nessun altro a rispondere.

Alle quattro si affianca, **nella stessa pagina e con lo stesso peso tipografico**, la sezione su
quando un'istanza singola basta davvero. Non è una cortesia: è la parte che rende credibile il
resto.

**Conseguenze:** la pagina è più lunga e più lenta da scrivere di un elenco puntato di paure, e in
compenso regge una domanda dal pubblico. Ogni affermazione ha un comando che la riproduce, il che
la rende utilizzabile anche come materiale di demo: le quattro righe di [V-015](Sources.md#v-015)
si eseguono in venti secondi davanti a chiunque.

La misura di [V-016](Sources.md#v-016) porta con sé un debito onesto: non abbiamo provato lo stesso
esperimento con `j: true`, che dovrebbe azzerare la perdita al prezzo della velocità. È scritto
nella riserva della verifica e va fatto quando l'applicazione Python potrà generare carico
controllato (`feature/04`).

Resta un rischio da sorvegliare: le tre risposte «rumorose» dipendono da messaggi d'errore, e i
messaggi cambiano fra versioni più facilmente dei comportamenti. La pagina cita i codici
(`40573`, `76`, `2`) accanto ai testi, perché i codici sono la parte stabile.

**Alternative scartate:** presentare i limiti solo a parole, senza comandi (più breve, ma
indistinguibile dal marketing al contrario, e non riproducibile da chi legge); dedurre tutto dal
manuale senza eseguire (avremmo scritto che i change stream «non sono disponibili» senza sapere che
l'errore è `Location40573`, e soprattutto **non avremmo mai trovato** il caso di `w: "majority"`
accettato in silenzio, che è il più interessante dei quattro); rimandare la dimostrazione della
perdita a `feature/02`, dove ci sarà un replica set con cui confrontarla (il confronto sarà più
bello lì, ma la pagina dell'istanza singola sarebbe rimasta senza la sua prova, e un'affermazione
senza prova in questo repository ha una scadenza breve).

**Fonti:** [S-035](Sources.md#s-035), [S-036](Sources.md#s-036), [S-037](Sources.md#s-037), [S-038](Sources.md#s-038), [V-015](Sources.md#v-015), [V-016](Sources.md#v-016)

---

<a id="adr-0033"></a>
## ADR-0033 — Le trappole si raccolgono in una pagina sola, e ogni voce comincia dal sintomo

**Data:** 2026-08-28 · **Stato:** Accettata

**Contesto:** durante `feature/00` e `feature/01` sono emersi diversi punti in cui MongoDB e
Docker si fraintendono, e hanno una caratteristica in comune: **nessuno di essi produce un
messaggio d'errore che nomini la causa**. Gli script di inizializzazione vengono saltati in
silenzio su un volume popolato ([V-014](Sources.md#v-014)); una versione di MongoDB che il
kernel della VM non regge esce senza dire perché ([V-007](Sources.md#v-007)); le variabili
`MONGO_INITDB_ROOT_*` su un config server producono un avvio apparentemente riuscito e un
cluster che non si forma ([V-006](Sources.md#v-006), [S-034](Sources.md#s-034));
`localhost` risolve verso la macchina sbagliata invece di non risolvere
([V-018](Sources.md#v-018)).

Chi incontra uno di questi casi non parte dalla causa: parte dal sintomo. Ha davanti un
container che è uscito, o un dataset che non c'è, o un `ECONNREFUSED`, e cerca quello. Una
documentazione organizzata per argomento — «volumi», «rete», «entrypoint» — è inutile a
quella persona, perché per trovare la sezione giusta dovrebbe già sapere la risposta.

C'è anche un problema di proprietà. Le trappole non appartengono a una feature: nascono qui, ma
`feature/02` ne aggiungerà sui permessi del keyfile e sulla scoperta della topologia, e
`feature/03` sui config server e sul bilanciamento. Se ognuna se le tiene nella propria pagina,
la stessa trappola viene raccontata tre volte e nessuna delle tre versioni è quella completa.

**Decisione:** `docs/02-architetture/trappole-mongodb-in-docker.md` è la sede unica. Il suo
contratto, che i branch successivi ereditano:

1. **Una sezione per trappola, numerata**, e le sezioni esistenti non si riscrivono: i branch
   successivi ne aggiungono in coda. La numerazione diventa così un riferimento stabile.
2. **Il titolo della sezione è il sintomo, non la causa.** «Il container esce e il log non dice
   niente», non «incompatibilità fra kernel e versione». Chi cerca, cerca il sintomo.
3. **Quattro voci fisse in ogni sezione:** *sintomo* (cosa si vede), *causa* (cosa sta davvero
   succedendo), *rimedio* (cosa fare), *fonte* (dove è scritto o dove è stato misurato).
4. **Ogni trappola porta almeno un riferimento verificabile**, come ovunque in `docs/`. Una
   trappola raccontata a memoria è un aneddoto, e gli aneddoti in questo repository hanno una
   scadenza breve ([ADR-0024](#adr-0024)).
5. **Se una trappola ha una decisione dietro, la sezione la nomina e non la ripete.** La pagina
   dice cosa si vede e cosa fare; il perché sta nell'ADR.

**Conseguenze:** la pagina cresce per aggiunta e non per riscrittura, il che la rende
modificabile da tre branch diversi senza conflitti di merito. Il costo è la ridondanza: la
stessa informazione compare nella pagina dell'architettura e nella pagina delle trappole, con
angolazioni diverse. È una ridondanza voluta, perché i due lettori sono diversi — uno sta
studiando, l'altro sta cercando di far ripartire qualcosa.

Il vincolo del sintomo-come-titolo ha un effetto collaterale utile: obbliga a ricordare **cosa
si vedeva** prima di sapere cosa fosse. È l'informazione che si perde per prima, subito dopo
aver risolto il problema, ed è l'unica che serve a chi il problema ce l'ha ancora.

**Alternative scartate:** una sezione «problemi noti» in fondo a ciascuna pagina di architettura
(la stessa trappola andrebbe ripetuta tre volte, e chi cerca non sa in quale pagina guardare);
un file per trappola (comodo da versionare, ostile da sfogliare, e il valore di questa pagina è
proprio poterla scorrere); rimandare la pagina a fine progetto, quando le trappole saranno tutte
note (è esattamente il momento in cui nessuno ricorda più il sintomo).

**Fonti:** [S-034](Sources.md#s-034), [V-006](Sources.md#v-006), [V-007](Sources.md#v-007), [V-014](Sources.md#v-014), [V-018](Sources.md#v-018)

---

<a id="adr-0034"></a>
## ADR-0034 — `docker kill` non simula un guasto, e il lab lo dirà invece di fingere

**Data:** 2026-08-28 · **Stato:** Accettata

**Contesto:** la demo che regge la seconda metà del talk è la caduta di un nodo. Il gesto ovvio
per provocarla è `docker kill`, ed è il gesto che si vede in quasi tutte le presentazioni su
MongoDB in container. Misurandolo è saltato fuori che quel gesto non fa quello che sembra.

Con `restart: unless-stopped` in vigore, un `docker kill -s KILL` lascia il container `exited` e
`RestartCount` a **zero**: il demone non prova nemmeno a rialzarlo, né subito né dodici secondi
dopo ([V-017](Sources.md#v-017)). Lo stesso container, se `mongod` termina da sé, riparte da
solo in pochi secondi con `RestartCount=1`. Stessa politica, stesso container, esito opposto: a
cambiare è soltanto chi ha mandato il segnale.

La documentazione lo copre, ma non in modo che qualcuno potesse prevederlo.
[S-039](Sources.md#s-039) dice che la politica «is ignored until the Docker daemon restarts or
the container is manually restarted» dopo che il container «is stopped (manually or otherwise)»,
e la pagina di `docker kill` ([S-040](Sources.md#s-040)) non contiene la parola «restart». Per
il demone un `docker kill` è una fermata voluta da un umano. Per chi guarda lo schermo è un
crash.

Nella stessa sessione è emerso il caso simmetrico: `kill -9 1` **dentro** il container non fa
niente e ritorna successo. Non è una stranezza del runtime, è il kernel: solo i segnali per cui
«init» ha installato un gestore possono raggiungerlo dagli altri membri del suo namespace, e
`SIGKILL` non è gestibile ([S-041](Sources.md#s-041)).

**Decisione:** il lab non finge che `docker kill` sia un guasto.

1. Le demo di caduta nodo **dichiarano cosa stanno simulando**. `docker kill` resta lo strumento
   — è immediato, è riproducibile, è quello che il pubblico si aspetta — ma la narrazione dice
   «sto spegnendo un nodo», non «sto simulando un crash».
2. **Dove serve mostrare la ripartenza automatica**, il nodo si fa terminare da sé (comando
   `shutdown`), che è la via misurata in cui la politica di riavvio interviene davvero.
3. La trappola sta in `trappole-mongodb-in-docker.md` con il suo sintomo per titolo — «ho ucciso
   il container e `restart: unless-stopped` non l'ha rialzato» — secondo il contratto di
   [ADR-0033](#adr-0033).
4. `restart: unless-stopped` **resta** nei tre file Compose. Serve al caso per cui esiste: la
   macchina che si riavvia, il demone che riparte, il processo che muore da solo. Toglierlo
   perché non copre un caso che non gli compete sarebbe la reazione sbagliata alla scoperta.

**Conseguenze:** la demo di failover di `feature/02` va progettata sapendo questo, e il runbook
del talk ([ADR-0015](#adr-0015)) deve contenere la frase giusta accanto al comando — perché è
esattamente il momento in cui un ascoltatore attento chiede «ma allora non riparte da solo?», e
la risposta onesta è più interessante della domanda.

C'è un guadagno inatteso. «Il gesto con cui tutti simulano un guasto non simula un guasto» è un
aneddoto migliore di qualunque diagramma sulle politiche di riavvio, e viene con tre fonti e una
tabella di misure. Va in [`citazioni-riportare-slide.md`](citazioni-riportare-slide.md).

**Alternative scartate:** togliere `restart: unless-stopped` dai file per evitare l'imbarazzo
(nasconde il fenomeno invece di spiegarlo, e priva gli stack di una protezione che serve
davvero); usare `docker stop` nelle demo perché «è più onesto» (è più lento e mette in mezzo un
arresto pulito, che è un terzo scenario ancora diverso); tacere e lasciare che la demo suggerisca
una conclusione sbagliata (funziona finché in sala non c'è nessuno che conosce Docker).

**Fonti:** [S-039](Sources.md#s-039), [S-040](Sources.md#s-040), [S-041](Sources.md#s-041), [V-017](Sources.md#v-017)

---

<a id="adr-0035"></a>
## ADR-0035 — Le righe di log si citano per `id`, e la pagina distingue ciò che è stato letto da ciò che sarà letto

**Data:** 2026-08-28 · **Stato:** Accettata

**Contesto:** il talk mostra dal vivo un nodo che cade e un cluster che se ne accorge. L'unica
prova che l'ha notato è il log, e sarà proiettato. Serve una pagina che insegni a leggerlo prima
che serva, perché sul palco non c'è tempo per imparare.

Il primo problema è che il log non è fatto per essere letto dall'alto. Misurandolo su questo
stack — novemilanovecentotrentuno righe, nessun carico applicativo — il **91,9 %** appartiene a
`NETWORK` e `ACCESS`, e il **99,3 %** di quanto viene scritto al minuto è l'healthcheck che
apre cinque connessioni ogni dieci secondi ([V-019](Sources.md#v-019)). Le righe che
interessano un amministratore sono trenta su novemilanovecentoventidue, e quindici delle trenta
sono lo stesso avviso d'avvio ripetuto. Chi scorre, non trova.

Il secondo problema è la citabilità. [S-042](Sources.md#s-042) descrive `id` come «Unique
identifier for the log statement» e dedica un esempio al filtro per `id`; del testo di `msg` non
promette niente. Una pagina didattica che dicesse «cerca la riga *Connection accepted*» invecchia
alla prima versione che riformula il messaggio, e invecchia in silenzio: il lettore cerca, non
trova, e conclude che il server non ha fatto quella cosa.

Il terzo problema è che metà della materia qui non è verificabile. Le righe di un'elezione
esistono solo dove c'è un replica set, e su questo branch non c'è. [S-044](Sources.md#s-044)
descrive il meccanismo — battiti ogni due secondi, nodo dato per irraggiungibile dopo dieci,
«The median time before a cluster elects a new primary should not typically exceed 12 seconds» —
ma non nomina una sola riga di log. Scrivere quella sezione adesso significa scrivere qualcosa
che non è stato visto.

**Decisione:** quattro regole per `docs/03-amministrazione/log.md` e per ogni altra pagina che
citi un log.

1. **Il riferimento è l'`id`.** Ogni riga citata nel repository porta il suo numero. Il testo di
   `msg` compare come illustrazione, mai come chiave di ricerca: si cerca `"id":22943`, non
   «Connection accepted». Dove il lettore deve filtrare, il repository mostra il filtro sull'`id`.
2. **La pagina dichiara riga per riga cosa è stato misurato e cosa no.** Le sezioni sul formato e
   su `logRotate` poggiano su misure fatte qui e le citano ([V-010](Sources.md#v-010),
   [V-019](Sources.md#v-019)). La sezione sull'elezione poggia solo su
   [S-044](Sources.md#s-044) e si apre con una riserva esplicita: **gli `id` verranno inseriti in
   `feature/02`, dopo averne vista una**. Nessuna riga inventata per rendere la pagina completa.
3. **Gli avvisi d'avvio si mostrano con `getLog`, non scorrendo.**
   `db.adminCommand({getLog: "startupWarnings"})` restituisce tre righe invece di
   novemilanovecento ([V-019](Sources.md#v-019)), ed è il gesto che va sullo schermo. Fra le tre
   c'è `22120`, «Access control is not enabled for the database»: il lab senza autenticazione
   ([ADR-0005](Decision.md#adr-0005)) **è** avvisato dal server, e la pagina lo dice invece di
   lasciarlo scoprire a un revisore.
4. **Su `logRotate` la pagina riporta il limite documentato e la misura che lo contraddice.**
   [S-043](Sources.md#s-043) scrive che «Your `mongod` instance needs to be running with the
   `--logpath [file]` option in order to use `logRotate`»; il server, senza `--logpath`, risponde
   comunque `{ok: 1}` senza ruotare niente ([V-010](Sources.md#v-010)). Le due frasi stanno
   accanto, e la pagina conclude che in container la rotazione è affare del runtime
   ([ADR-0030](Decision.md#adr-0030)), non del database.

**Conseguenze:** la pagina resiste a un cambio di versione, perché ciò che cita è stabile per
dichiarazione della fonte. Chi la legge impara a filtrare, che è l'unico modo di usare un log
in cui il 92 % delle righe parla di connessioni. La sezione sull'elezione resta con un debito
scritto in chiaro, e `feature/02` non può chiudersi senza saldarlo: è il prezzo di non scrivere
righe mai viste.

Il costo è di leggibilità. Una riga citata come `id 22943` è meno evocativa di «Connection
accepted», e la pagina deve quindi riportarle entrambe, allungandosi. Va accettato: la seconda
serve a capire, la prima a ritrovare.

**Alternative scartate:** citare i messaggi per testo (leggibile, e fragile in modo silenzioso —
la fonte non promette stabilità); rimandare tutta la pagina a `feature/02`, quando ci sarà un
replica set (ma il formato del log serve prima, e su un'istanza singola è già interamente
osservabile); alzare la verbosità a `D1` per la demo, così «si vede di più» (si vede di più del
rumore: le righe interessanti annegano, e [S-042](Sources.md#s-042) ricorda che le severità
superiori sono mostrate comunque); togliere l'healthcheck per avere un log pulito (si baratta la
leggibilità del log con la diagnosi di uno stack che non parte, che è il problema più frequente).

**Fonti:** [S-042](Sources.md#s-042), [S-043](Sources.md#s-043), [S-044](Sources.md#s-044), [V-010](Sources.md#v-010), [V-019](Sources.md#v-019)

---

<a id="adr-0036"></a>
## ADR-0036 — `mongosh` si usa dentro il container, e in automazione non si crede al codice di uscita

**Data:** 2026-08-28 · **Stato:** Accettata

**Contesto:** la guida a `mongosh` deve servire due lettori diversi con la stessa pagina. Il
primo è chi segue il talk e riproduce i comandi: per lui conta che la riga da incollare funzioni
al primo colpo. Il secondo è chi scrive uno strumento di verifica del repository — `smoke-01`,
`stack-check`, e domani l'applicazione Python: per lui conta sapere che cosa il comando promette
quando nessuno lo guarda.

Il primo fatto è che sul portatile di sviluppo `mongosh` **non esiste**. `which mongosh` non
trova niente; la shell, il server e gli strumenti di backup vivono dentro l'immagine
`mongo:7.0.40`, nella versione **2.10.0** ([V-020](Sources.md#v-020)). Una guida scritta come le
guide di [S-045](Sources.md#s-045), che presuppongono `mongosh` installato accanto al database,
manderebbe il lettore a installare un pacchetto che non serve e a collegarsi a un «localhost» che
per lui significa un'altra macchina ([V-018](Sources.md#v-018)).

Il secondo fatto è che `mongosh` sceglie da sé tre parametri che nessuno ha scritto. Interrogato
su dove sia andato risponde
`mongodb://127.0.0.1:27017/?directConnection=true&serverSelectionTimeoutMS=2000&appName=mongosh+2.10.0`.
Il terzo è il pericoloso: **due secondi** di attesa per trovare un server, contro un'elezione che
[S-044](Sources.md#s-044) dà per lunga fino a dodici. Nessuna delle pagine consultate nomina
quel valore predefinito.

Il terzo fatto è la tabella dei codici di uscita, che non esiste in nessuna pagina di
[S-046](Sources.md#s-046) né di [S-047](Sources.md#s-047). Misurata su quindici casi
([V-020](Sources.md#v-020)) dice due cose scomode: **ogni errore vale `1`** — un `throw`, un
`TypeError`, un `MongoServerError` e un server irraggiungibile sono indistinguibili dal codice di
uscita — e **il silenzio vale `0`**: un `countDocuments` che restituisce zero termina con
successo. Uno script di verifica che si limiti a interrogare e a guardare se torna zero
**dichiara sano un database vuoto**.

**Decisione.**

1. **Ogni comando della guida passa da `docker compose exec`.** La pagina apre dichiarando che
   `mongosh` non è sull'host, e non offre la variante «installalo e collegati»: non è il lab.
   L'invocazione canonica del repository è
   `docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml exec -T mongo-standalone mongosh --quiet --eval "…"`,
   e la sua forma breve è il bersaglio del `Makefile`.
2. **Negli script si scrive `-T`, e non si scrive mai `-it`.** Misurato: senza `-T` i comandi
   funzionano lo stesso, anche con lo standard input chiuso; è `docker exec -it` a fallire con
   `cannot attach stdin to a TTY-enabled container because stdin is not a terminal`. `-T` resta
   perché è esplicito e non costa niente, ma la pagina dice qual è il vero colpevole, perché la
   diagnosi sbagliata circola più della giusta.
3. **In automazione si scrive `--quiet` anche dove sarebbe già implicito.** [S-046](Sources.md#s-046)
   accende `--quiet` da sé nelle sessioni non interattive, ma non definisce «non interattiva», e
   la stessa riga di comando nel lab finisce ora in uno script ora incollata a mano. Scriverlo
   rende l'output indipendente da quella distinzione.
4. **Uno script che verifica qualcosa esce con un codice scelto da chi lo scrive.** Mai affidarsi
   al codice implicito: si controlla il risultato e si chiama `exit(<codice>)`, come raccomanda
   [S-047](Sources.md#s-047), restando fra 1 e 125 perché `exit(300)` arriva al chiamante come 44
   ed `exit(-1)` come 255.
5. **I file di script si passano con `--file` e con percorso assoluto.** Dentro un container la
   directory di lavoro non è quella da cui si è digitato il comando, e `load()` non ha percorso di
   ricerca ([S-047](Sources.md#s-047)). Niente script per pipe: `mongosh` tratta lo standard input
   come una sessione interattiva e ci stampa sopra i prompt.
6. **Le sezioni non eseguibili su questo branch sono dichiarate tali.** I comandi di
   amministrazione di un replica set e di uno sharded cluster stanno nella pagina perché servono
   al talk, ma sono marcati come **non eseguiti qui**: la verifica è dovuta a `feature/02` e
   `feature/03`. È la stessa regola di [ADR-0035](#adr-0035).

**Conseguenze:** i comandi della guida sono lunghi, e la pagina lo ammette invece di accorciarli
barando. In cambio si incollano e funzionano, anche a chi non ha mai visto questo repository, e
sono gli stessi che girano nel `Makefile`. La regola 4 spiega perché gli strumenti di verifica del
repository non si limitano a lanciare comandi: `smoke-01` conta i documenti e confronta
un'impronta, e questa ADR è la ragione scritta di quella scelta.

Il costo è che la guida è meno portabile di quanto sembri: chi ha `mongosh` installato sull'host
deve tradurre. La pagina lo dice in apertura e mostra una volta la forma equivalente, poi non ci
torna più.

**Alternative scartate:** installare `mongosh` sul portatile e scrivere la guida «normale» (una
versione in più da tenere allineata, e il rischio che in sala si parli a un server diverso da
quello che si crede — [V-018](Sources.md#v-018)); avvolgere ogni comando in un bersaglio del
`Makefile` e documentare solo quelli (comodo e opaco: chi guarda le slide non impara `mongosh`,
impara questo repository); fidarsi del codice di uscita e scrivere strumenti più corti (è
esattamente la trappola che [V-020](Sources.md#v-020) misura); rimandare la pagina a quando
esisterà l'applicazione Python (la shell serve prima, ed è ciò che si proietta quando la demo si
inceppa).

**Fonti:** [S-044](Sources.md#s-044), [S-045](Sources.md#s-045), [S-046](Sources.md#s-046), [S-047](Sources.md#s-047), [V-018](Sources.md#v-018), [V-020](Sources.md#v-020)

---

<a id="adr-0037"></a>
## ADR-0037 — Le pagine di installazione sul sistema operativo si scrivono da fonte e si dichiarano non eseguite

**Data:** 2026-08-28 · **Stato:** Accettata

**Contesto:** buona parte del pubblico di SqlStart non tornerà in ufficio a scrivere un file
Compose. Tornerà a installare MongoDB su una macchina Linux o su un server Windows, perché è così
che sta il database in azienda. Le due pagine di `01-installazione` sono le uniche del branch che
non parlano di Docker, e sono quelle che verranno riaperte più spesso dopo il talk.

Il problema è che **non si possono eseguire qui**. La macchina di sviluppo è un Mac; non esiste un
Ubuntu su cui provare `apt-get install mongodb-org`, non esiste una macchina Windows su cui
lanciare il `.msi`. Le tre strade possibili erano: non scrivere le pagine; scriverle presentandole
come verificate; scriverle dichiarando che non lo sono.

La prima strada lascia scoperta la domanda più frequente che il talk riceverà. La seconda è il
primo posto in cui questo repository mentirebbe, e mentirebbe in un punto controllabile: chiunque
segua le istruzioni e trovi una differenza scoprirebbe che «verificato» qui non vuol dire niente,
e da quel momento non varrebbe niente nemmeno dove è vero. [ADR-0024](#adr-0024) esiste per
distinguere ciò che è stato osservato da ciò che è stato letto, e non ammette eccezioni comode.

C'è però un fatto che rende le pagine meno teoriche di quanto sembri. L'immagine del lab **è**
un'installazione Ubuntu: `PRETTY_NAME="Ubuntu 22.04.5 LTS"`, e dentro c'è
`/etc/apt/sources.list.d/mongodb-org.list` che punta allo stesso repository ufficiale del tutorial
([V-021](Sources.md#v-021)). Quello che l'immagine ha tolto — `systemd`, `/etc/mongod.conf`,
`/var/log/mongodb` — è esattamente l'elenco di ciò che le pagine devono spiegare. E gli avvisi che
il server emette a ogni avvio (`22297` sul filesystem, `9068900` su THP) sono le note di produzione
che si presentano da sole.

**Decisione.**

1. **Le due pagine si scrivono, complete, e portano una riserva in testa.** Un riquadro in
   apertura dichiara: la procedura non è stata eseguita, la fonte è la documentazione ufficiale
   MongoDB per la 7.0, e il lettore è il primo a provarla davvero. Nessun avverbio che ammorbidisca
   («dovrebbe funzionare», «in genere»): la riserva è un fatto, non un'attenuante.
2. **Ogni comando riportato viene da una fonte primaria, e la fonte è citata accanto.** Niente
   comandi ricostruiti a memoria, niente varianti «più comode» inventate qui. Dove la fonte dà una
   forma sola, si riporta quella; dove ne dà due, si riportano entrambe.
3. **Ciò che è stato misurato viene marcato come tale, e tenuto separato.** Le misure di
   [V-021](Sources.md#v-021) — il filesystem `ext4`, THP acceso, i `ulimit` a 1 048 576, l'utente
   `mongodb` del processo 1 — stanno nelle pagine in blocchi riconoscibili, che dicono «questo è
   stato eseguito, ma dentro un container, e per questo vale come contrasto e non come conferma».
4. **La messa a punto del sistema operativo sta nella pagina Linux, non altrove.** `ulimit`, THP,
   swap, NUMA, filesystem: sono cinque argomenti che un amministratore incontra il primo giorno e
   che nessuna pagina su Docker gli darà mai. Vanno insieme alla procedura che li rende necessari.
5. **Le differenze di Windows si dicono per intero, comprese quelle che riguardano la sicurezza.**
   La più concreta è sul keyfile: «On UNIX systems, the keyfile must not have group or world
   permissions. On Windows systems, keyfile permissions are not checked»
   ([S-005](Sources.md#s-005)). Un controllo che su un sistema esiste e sull'altro no non è un
   dettaglio da nota a piè di pagina.
6. **Il debito è scritto.** Se in futuro il progetto disporrà di una macchina Ubuntu o Windows, le
   pagine vanno rieseguite e la riserva sostituita con una verifica. Fino ad allora la riserva
   resta, e nessuna revisione può toglierla senza aver eseguito la procedura.

**Conseguenze:** il repository guadagna le due pagine che il pubblico userà di più, e le guadagna
senza spendere la propria credibilità. Il lettore sa esattamente su che cosa poggia ogni riga: la
documentazione ufficiale, che è la fonte migliore disponibile, ma non un'esecuzione. La riserva ha
anche un effetto collaterale utile — rende evidente che il resto del repository, dove la riserva
non c'è, è stato invece eseguito.

Il costo è che le pagine sono meno autorevoli di quelle che le circondano, e si nota. Va bene
così: l'alternativa era essere autorevoli senza averne diritto.

**Alternative scartate:** avviare una macchina virtuale Ubuntu sul Mac e provare davvero
(possibile, e fuori tempo: la sola messa a punto di NUMA, THP e `ulimit` in una VM non
rappresentativa avrebbe prodotto misure che non valgono per nessun server reale — un costo alto per
una verifica finta); limitarsi a un rimando alla documentazione MongoDB (è la risposta che il
pubblico può darsi da solo, e lascia fuori proprio le cinque messe a punto che nessuno legge finché
non fanno male); scrivere una pagina sola «installazione su sistema operativo» con due colonne
(Linux e Windows divergono su percorsi, init system, sicurezza e messa a punto: una tabella a due
colonne sarebbe più corta da leggere e più facile da sbagliare); usare il container come prova
sostitutiva, dichiarando le procedure verificate «in sostanza» (è la scorciatoia che
[ADR-0024](#adr-0024) esclude, e [V-021](Sources.md#v-021) mostra quanto sarebbe stata sbagliata:
metà delle note di produzione, dentro un container, non si applicano affatto).

**Fonti:** [S-005](Sources.md#s-005), [S-048](Sources.md#s-048), [S-049](Sources.md#s-049), [S-050](Sources.md#s-050), [S-051](Sources.md#s-051), [S-052](Sources.md#s-052), [V-021](Sources.md#v-021)

---

<a id="adr-0038"></a>
## ADR-0038 — Le decisioni che una macchina può controllare le controlla una macchina

**Data:** 2026-08-28 · **Stato:** Accettata

**Contesto:** [ADR-0029](#adr-0029) ha aperto la sede che mancava — una decisione che governa
`tools/` e il `Makefile` — ma ha risolto una domanda sola: come devono essere scritti gli
strumenti. Resta l'altra, che in questo branch si è presentata due volte: **quando** una
decisione merita uno strumento che la faccia rispettare.

Il caso che l'ha posta per primo è quello delle risorse. [ADR-0004](#adr-0004) dice che il
limite di memoria e la cache di WiredTiger vanno dichiarati entrambi e che la seconda è un
quarto del primo; [ADR-0009](#adr-0009) dice che le immagini si pinnano per digest;
[ADR-0018](#adr-0018) dice che il vincolo offline dipende da una variabile sola;
[ADR-0023](#adr-0023) dice che `depends_on` usa la forma lunga con `condition`. Sono quattro
frasi in un documento e quattro righe in un file YAML, e fino al 2026-08-28 niente le teneva
nella stessa stanza. Un `mem_limit` cambiato in fretta durante una prova, e la decisione resta
scritta mentre l'artefatto racconta un'altra cosa — senza che nessuno se ne accorga, perché lo
stack parte lo stesso.

Il secondo caso è più piccolo e più istruttivo. Un collegamento relativo rotto **non rompe
niente**: la pagina si apre, il link porta a un 404 o in cima al documento invece che al punto
giusto, e i test passano tutti. Il 2026-08-28 uno script scritto per l'occasione ha trovato
quattro collegamenti rotti nel piano di `feature/00` ([`8af49a0`](https://github.com/giulianolatini/SqlStart2026/commit/8af49a0)):
un documento riletto più volte, in un repository dove la disciplina delle citazioni è
automatica. Nessuno li aveva visti perché non c'era niente da vedere. Quel commit ha preso un
impegno esplicito — «diventerà un tool del repository nel giro di chiusura di feature/01» — ed
è l'impegno che questa decisione salda.

C'è un dettaglio tecnico che merita di essere registrato, perché è il punto in cui un
controllore fatto male direbbe bugie. I rimandi interni di questo repository si scrivono nella
forma naturale `#1-prima-di-cominciare`, e quell'ancora **nessuno l'ha dichiarata**: la genera
GitHub dal testo del titolo. Chi vuole verificarli deve riprodurre la stessa trasformazione,
comprese le regole che nessuno indovina: «Spaces are replaced by hyphens ( - ). Any other
whitespace or punctuation characters are removed» ([S-053](Sources.md#s-053)) — ogni singolo
spazio, senza accorpare, il che significa che «S-001 — WiredTiger» produce `s-001--wiredtiger`
con **due** trattini, perché il trattino lungo sparisce e lascia due spazi. Il codice
dell'emulazione ufficiosa lo conferma in una riga: `value.replace(regex, '').replace(/ /g, '-')`
([S-054](Sources.md#s-054)). Un controllore che accorpasse gli spazi segnalerebbe come rotti
proprio i rimandi scritti bene, e verrebbe spento dopo tre falsi allarmi.

**Decisione.**

1. **Un ADR il cui vincolo si può esprimere come predicato su un file riceve un controllore in
   `tools/`.** Il criterio è meccanico quanto il controllo: se la decisione si può violare
   modificando un file, e la violazione si può riconoscere leggendo quel file, allora la
   rilettura umana non è lo strumento giusto. Gli ADR che riguardano il metodo, il taglio o il
   contenuto restano fuori: nessuna macchina sa se una pagina dice il vero.
2. **Il controllore nasce prima dell'artefatto che controlla, con i propri test.**
   `check_stack.py` è stato scritto prima del file Compose dello stack 01: il file è nato già
   conforme, invece di essere corretto dopo. È la stessa disciplina TDD che vale per
   l'applicazione, applicata al repository.
3. **Ogni messaggio di errore cita l'ADR che si sta violando.** Un controllo che dice «non
   conforme» senza dire a quale decisione è un ostacolo; uno che dice «il digest manca, e la
   ragione è ADR-0009» è documentazione che si presenta al momento giusto.
4. **Ogni controllore entra in un target `make`, e nel target che si esegue senza sapere che
   esiste.** `make docs-check` ora ne lancia due, `check_citations.py` e `check_links.py`;
   `make stack-check` lancia `check_stack.py`. Uno strumento che va invocato a mano è uno
   strumento che dopo tre settimane nessuno invoca.
5. **Il controllore riproduce il comportamento del sistema che verifica, non un'approssimazione
   comoda, e cita la fonte accanto alla riga.** È [ADR-0029](#adr-0029) applicato al caso
   nuovo: la funzione `slug()` di `check_links.py` implementa le cinque regole di
   [S-053](Sources.md#s-053), e il commento accanto spiega perché non accorpa gli spazi.
6. **Quello che i controllori non fanno si dichiara.** Nessuno di loro tocca la rete: gli
   indirizzi `https:` non vengono verificati, perché il repository deve restare controllabile
   con il Wi-Fi spento — è lo stesso vincolo di [ADR-0018](#adr-0018), e vale anche per i
   propri strumenti. `check_links.py` non verifica l'unicità delle ancore generate, che GitHub
   risolve appendendo `-1` e `-2` ([S-053](Sources.md#s-053)): qui non è mai servito, e il
   giorno che servisse si vedrebbe subito. Nessuno guarda dentro i blocchi recintati da ```` ``` ````,
   dove un `# commento` non è un titolo e un `[testo](url)` è un esempio.

**Conseguenze:** il repository ha tre controllori e sessanta test che li tengono onesti. Il
guadagno vero non è aver trovato quattro link rotti: è che d'ora in poi le decisioni sulle
risorse e i rimandi fra le pagine non possono divergere in silenzio dall'artefatto. La classe
di errore che questo branch ha incontrato — vero quando è stato scritto, falso tre commit dopo,
e nessuno se ne accorge — è la stessa che rende inutili le documentazioni vecchie.

Il costo è codice da mantenere, e un controllore sbagliato è peggio di nessun controllore:
insegna a ignorare i suoi messaggi. È il motivo del punto 2, ed è il motivo per cui la regola
dello slug è stata verificata contro il codice dell'emulazione e non contro l'intuizione. Resta
il limite di fondo, che va detto: questi strumenti vedono la forma. Che una pagina sia vera lo
decide chi la legge, e per quello esistono la [gerarchia delle fonti](#adr-0024) e le riserve
dichiarate.

**Alternative scartate:** adottare un linter Markdown generico (`markdownlint` e simili
controllano lo stile — righe lunghe, spazi doppi, livelli di titolo saltati — non le decisioni
di *questo* repository, e porterebbero una dipendenza Node in un progetto che ha scelto Python e
`uv`; il controllo che serviva qui, «l'ancora esiste nel file di destinazione», nessuno di loro
lo fa fra file diversi); verificare i collegamenti con una richiesta HTTP (trasformerebbe un
controllo deterministico in un test di rete, che fallisce per motivi che non riguardano il
repository, e violerebbe il vincolo offline proprio nello strumento che dovrebbe difenderlo);
delegare i controlli a GitHub Actions (girerebbero dopo il commit e non prima, e il giorno del
talk, in una sala senza rete garantita, non girerebbero affatto); continuare a rileggere
(misurato: quattro collegamenti rotti sono sopravvissuti alle riletture, e sono stati trovati in
un secondo da venti righe di Python).

**Fonti:** [S-053](Sources.md#s-053), [S-054](Sources.md#s-054)

<a id="adr-0039"></a>
## ADR-0039 — `pull_policy: never` scritto nel file, non dedotto dall'ambiente

**Data:** 2026-08-31 · **Stato:** Accettata — sostituisce [ADR-0018](#adr-0018)

**Contesto:** una review esterna della PR #2 ha segnalato che
`docker/01-standalone/compose.yaml` non rispetta [ADR-0027](#adr-0027). Verificando il rilievo è
emerso che il conflitto sta a monte dell'artefatto: [ADR-0018](#adr-0018) prescrive
`pull_policy: ${PULL_POLICY:-missing}` con `never` esportato dal profilo di palco, ADR-0027
prescrive `never` fisso in ogni servizio di ogni stack e scarta `missing` per nome — «esattamente
ciò che non deve accadere il 18 settembre». **Erano entrambe Accettata, e nessuna superava
l'altra.** L'artefatto implementava la prima; `tools/check_stack.py` la faceva rispettare come
regola, e quindi difendeva attivamente la decisione sbagliata. In più, la promessa di ADR-0018 «il
preflight la controlla» non è mai stata implementata: il preflight verifica che l'immagine sia in
cache, non che la variabile valga `never`.

Sul merito, la ragione che ADR-0018 dava per la forma parametrica — non rendere scomodo il primo
avvio a chi clona il repository — è stata smontata da ADR-0027 stesso: `make images-pull` esiste,
è un passo solo, e l'errore che riceve chi lo salta arriva a casa propria, con la rete, non in
sala.

**Decisione:** ogni servizio di ogni stack porta `pull_policy: never` **scritto letteralmente nel
file Compose**. La variabile `PULL_POLICY` non esiste più: né in `docker/*/.env.example`, né in
`tools/images.env`, né in un profilo di palco. `tools/check_stack.py` rovescia la propria regola e
ne aggiunge una seconda: il valore deve essere `never`, e non deve provenire da un'interpolazione.
Per poterlo fare lo strumento legge il file **due volte**, prima e dopo la sostituzione delle
variabili: le altre regole giudicano lo stack che si avvia, questa giudica ciò che il file promette
a chi lo apre.

**Conseguenze:** la garanzia offline diventa una proprietà leggibile dell'artefatto invece di una
proprietà dell'ambiente in cui l'artefatto viene lanciato. È la differenza che conta in sala: un
file si proietta, una variabile d'ambiente dimenticata no. Misurato dopo la modifica
([V-022](Sources.md#v-022)): `make up-01` porta il container a `Healthy` e `make smoke-01` passa
dodici prove su dodici; con un digest che non è in cache, `up` fallisce in **0,113 s** con `No
such image`, che conferma su questo file la misura di [V-006](Sources.md#v-006). Il costo resta
quello che ADR-0027 aveva già accettato: `make images-pull` è obbligatorio prima del primo avvio.

Una conseguenza minore ma didattica: `.env.example` non elenca più `PULL_POLICY` e spiega al suo
posto perché non c'è. Un parametro tolto lascia un buco, e il buco va spiegato dove qualcuno
andrebbe a cercarlo.

**Alternative scartate:** lasciare i due ADR in conflitto e allineare solo l'artefatto (il
repository sarebbe rimasto con due regole scritte e opposte, e il prossimo che legge `Decision.md`
avrebbe applicato quella sbagliata a caso); riscrivere ADR-0018 invece di superarlo (il repository
non riscrive le decisioni: [ADR-0008](#adr-0008) e [ADR-0028](#adr-0028) sono il precedente);
tenere la forma parametrica e implementare finalmente il controllo del preflight promesso da
ADR-0018 (aggiunge un controllo per difendere una variabile che non serve — la stessa garanzia
costa zero controlli se è scritta nel file); controllare il valore solo dopo l'interpolazione
(passa un file parametrico purché l'ambiente del momento sia quello giusto, cioè verifica proprio
la cosa che si è deciso di non dover più verificare).

**Fonti:** [S-019](Sources.md#s-019), [V-006](Sources.md#v-006), [V-022](Sources.md#v-022)

<a id="adr-0040"></a>
## ADR-0040 — Chi crea l'utente amministratore del replica set, e dove gira l'inizializzazione

**Data:** 2026-08-31 · **Stato:** Accettata il 2026-08-31 — nata `Proposta`, scelta dal Product
Owner lo stesso giorno

**Perché è nato con uno stato nuovo.** È il primo ADR di questo repository che non è nato già
deciso. Gli altri trentanove registrano scelte prese da un vincolo tecnico: una misura le imponeva,
e l'ADR le verbalizzava. Qui le misure dicono che **tutte** le strade funzionano
([V-023](Sources.md#v-023)), e quindi non decidono niente: quello che restava da scegliere era
quale prezzo pagare, e il prezzo lo sceglie chi presenta, non chi implementa. Lo stato `Proposta` è
durato fino alla risposta — arrivata il 2026-08-31, strada C — e questo passaggio da `Proposta` ad
`Accettata` è l'unico caso in cui il corpo di un ADR viene modificato invece che superato: vale solo
perché una proposta non è ancora una decisione. Da qui in avanti su questo ADR torna a valere piena
la regola normale, si supera e non si riscrive.

**Contesto:** il design (§5.4) e [ADR-0026](#adr-0026) prescrivono due catene di inizializzazione
diverse per lo stesso problema. Il design mette `MONGO_INITDB_ROOT_USERNAME` e
`MONGO_INITDB_ROOT_PASSWORD` sul primo membro e affida `rs.initiate()` a un sidecar già
autenticato. ADR-0026 vuole i `mongod` **senza** variabili di root e l'utente creato sotto eccezione
localhost, e aggiunge che il replica set di `feature/02` «è la stessa catena senza gli shard». Le
due prescrizioni non sono conciliabili, e la differenza non è di stile: da una parte una password di
laboratorio finisce in `.env.example`, dall'altra no.

Il Task 1 del piano di `feature/02` ha rifiutato di scegliere leggendo e ha montato tre stack
usa-e-getta fuori dal repository. Il verbale completo, con i comandi e le risposte, è in
[V-023](Sources.md#v-023). In breve: la strada di ADR-0026 funziona anche su un replica set;
la strada del design funziona, perché l'entrypoint dell'immagine crea l'utente anche con `--replSet`
e `--keyFile` addosso — il caso che rompeva in ADR-0026 era `--configsvr`, che è un'altra cosa
([S-022](Sources.md#s-022)); e l'affermazione del design secondo cui un sidecar non gode
dell'eccezione localhost è vera, misurata (`Command replSetInitiate requires authentication`).

Provando a capire **perché** quel sidecar fallisse è emersa una terza via che non sta in nessuno dei
due documenti. Se l'eccezione dipende dall'indirizzo di provenienza, si cambia l'indirizzo di
provenienza: un container avviato con `network_mode: "service:mongo-rs-1"` non ha un'interfaccia di
rete propria, usa quella del membro, e il suo `localhost` è il `localhost` del `mongod`. Provata,
concede `replSetInitiate` e `createUser`, e si richiude subito dopo come la fonte prescrive
([S-055](Sources.md#s-055)).

**Decisione:** lo stack `02-replicaset` usa la terza via. Nessun `mongod` riceve
`MONGO_INITDB_ROOT_*`. Un servizio one-shot `rs-init`, dichiarato in `compose.yaml` con
`network_mode: "service:mongo-rs-1"`, esegue `rs.initiate()` con i tre membri elencati per nome di
servizio, attende l'elezione del primario — che [S-055](Sources.md#s-055) impone di attendere prima
di creare il primo utente — e crea l'amministratore sotto eccezione localhost. Le credenziali
arrivano al servizio da `.env`, non da `.env.example`, che porta solo un segnaposto.

**Conseguenze:** `docker compose up -d` da solo produce un replica set completo e autenticato,
senza passi manuali e senza alcuna password nel repository. Il che smentisce, misura alla mano, una
**conseguenza** di [ADR-0026](#adr-0026): «l'inizializzazione non può stare tutta in
`docker-compose.yml`: serve un passo esterno». Non serve. La *decisione* di ADR-0026 invece regge
intatta — niente variabili di root, utente creato sotto eccezione, membri elencati per nome — e
questa proposta la conferma per una via che allora non era stata considerata. ADR-0026 non viene
superato: gli si mette in testa una nota di allineamento che rimanda qui, perché chi lo legge fra sei
mesi non prenda per buona una conseguenza che è stata misurata falsa.

Due conseguenze minori, entrambe già utili ai task successivi. La prima: l'healthcheck dei membri
deve chiedere «`hello()` risponde?» e non «sei primario o secondario?», altrimenti resta rosso fino
a `rs.initiate()` e blocca il servizio che dovrebbe eseguirlo — l'uovo e la gallina che il Task 5
aveva previsto. La misura che lo consente è in [V-023](Sources.md#v-023): su un `mongod` con
`--keyFile` non ancora inizializzato, `hello()` risponde senza credenziali. La seconda: `rs-init`
condivide il namespace di rete del membro 1, quindi non è raggiungibile per nome sulla rete Compose
e non può pubblicare porte. Non gli serve nessuna delle due cose, ma va scritto nel file, perché è
il genere di vincolo che qualcuno tenterà di violare.

Resta un costo, ed è didattico prima che tecnico: `network_mode: "service:…"` è un costrutto che
la maggior parte di chi usa Compose non ha mai scritto. Va spiegato in
`02-architetture/trappole-mongodb-in-docker.md`, non lasciato nel file come un trucco.

**Alternative scartate:** seguire il design (`MONGO_INITDB_ROOT_*` sul membro 1) — funziona, ed è la
strada che chiunque riconosce a colpo d'occhio, ma mette una password nel repository e obbliga il
sidecar a un'attesa che nella prova è fallita al primo colpo con `ECONNREFUSED`, perché
`service_started` scatta mentre l'entrypoint è ancora nella fase del `mongod` temporaneo; seguire
ADR-0026 alla lettera (`rs.initiate()` con `docker exec` dentro il membro) — funziona, non costa
password, ma l'inizializzazione esce da Compose e `docker compose up -d` smette di bastare, che in
sala è un passo in più da ricordare mentre si parla; creare l'utente con uno script in
`/docker-entrypoint-initdb.d` — l'entrypoint esegue quegli script sul `mongod` temporaneo, cioè
prima che il set esista, e [S-055](Sources.md#s-055) impone l'ordine opposto: prima il primario,
poi il primo utente; lasciare i due documenti in conflitto e decidere nel file Compose — è
esattamente l'errore che [ADR-0039](#adr-0039) ha appena finito di correggere su `pull_policy`, sei
giorni fa e nello stesso repository.

**Fonti:** [S-006](Sources.md#s-006), [S-022](Sources.md#s-022), [S-055](Sources.md#s-055), [V-023](Sources.md#v-023)

<a id="adr-0041"></a>
## ADR-0041 — Quando lo stack si può dire pronto, e come gli si passano gli ambienti

**Data:** 2026-08-31 · **Stato:** Accettata

**Contesto:** il Task 4/5 di `feature/02` ha chiuso la catena — `keyfile-init`, i tre `mongod`,
`rs-init` — e nel misurarla ha trovato due cose che nessun documento del repository copre, e che non
sono misure ma decisioni da prendere una volta per tutte.

La prima è che **`docker compose up -d --wait` esce con successo prima che il replica set esista**.
Non di poco: quattordici secondi, misurati in [V-025](Sources.md#v-025), durante i quali il comando
ha già restituito zero e chi si collega riceve `NotYetInitialized (94)`. Non è un difetto da
segnalare a Docker. `--wait` è documentato come «Wait services be running|healthy»
([S-057](Sources.md#s-057)), `rs-init` non ha un healthcheck, quindi la soglia che gli si applica è
`running` — e un container che deve morire è `running` nell'istante in cui comincia. L'opzione fa
esattamente ciò che dichiara; è la parola «pronto» a significare due cose diverse per due generi di
servizio che stanno nello stesso file. I tre membri sono pronti quando **sono su e sani**; `rs-init`
è pronto quando **è finito**.

La seconda è che lo stack ha bisogno di due file d'ambiente — il pin dell'immagine in
`tools/images.env`, condiviso da tutti gli stack, e la password dell'amministratore in
`docker/02-replicaset/.env`, che è di questo stack soltanto — e che `--env-file` **non aggiunge un
file, ne prende il posto**: «Passing the `--env-file` argument overrides the default file path»
([S-056](Sources.md#s-056)). Passandone uno solo, il `.env` che sta accanto al file indicato con
`-f` smette di essere letto, benché sia lì. Misurato in [V-025](Sources.md#v-025).

**Decisione.** Tre punti, tutti e tre vincolanti per il Makefile del Task 7 e per la procedura che
si esegue in sala.

*Uno.* L'avvio dello stack `02-replicaset` è di **due comandi, non di uno**:

```
docker compose … up -d --wait
docker compose … wait rs-init
```

Il verdetto è il codice di uscita del secondo, non del primo. Chi scrive automazione contro questo
stack — il Makefile, l'applicazione di `feature/03`, uno script di dimostrazione — non può assumere
che il ritorno di `up` significhi «la replica c'è». Nessun bersaglio del Makefile scrive solo la
prima riga.

*Due.* Gli ambienti si passano con **due `--env-file`, in quest'ordine**: prima
`tools/images.env`, poi `docker/02-replicaset/.env`. L'ordine non è indifferente — «Later files can
override variables from earlier files» ([S-056](Sources.md#s-056)) — e mette lo stack in condizione
di sovrascrivere il pin comune, non il contrario. Non zero, perché il pin non verrebbe risolto; non
uno, perché il secondo file sparirebbe insieme al `.env` implicito.

*Tre.* **`rs-init` resta senza healthcheck**, ed è una scelta, non una dimenticanza. La tentazione,
davanti allo scarto del punto uno, è di dargliene uno perché `--wait` lo aspetti. Non regge: un
healthcheck descrive un container che resta vivo e continua a rispondere, mentre `rs-init` deve
morire, e il suo verdetto è un codice di uscita. Leggere un codice di uscita è precisamente ciò per
cui `docker compose wait` è documentato — «Block until containers of all (or specified) services
stop» ([S-057](Sources.md#s-057)). Lo strumento giusto esiste già: va usato quello, invece di
piegare il concetto di salute a descrivere una cosa morta.

**Conseguenze.** Il Task 7 scrive nel Makefile entrambi i comandi e entrambe le occorrenze di
`--env-file`; senza questo ADR li avrebbe scritti sbagliati, perché la forma sbagliata **funziona
quasi sempre** — su una macchina veloce lo scarto si accorcia e l'errore si presenta come un test
che fallisce una volta ogni tanto. Il Task 12 eredita due trappole per la pagina
`02-architetture/trappole-mongodb-in-docker.md`: «`up --wait` ha detto di sì» e «`--env-file` toglie
il `.env` che credevi di avere». La documentazione operativa di `feature/02` non scrive mai il primo
comando da solo, neanche negli esempi abbreviati.

Una conseguenza che vale oltre questo stack, ed è il motivo per cui è stata registrata qui invece
che in una nota: il fallimento del punto due è stato **rumoroso** solo perché la variabile è scritta
nella forma `${PASSWORD_AMMINISTRATORE:?messaggio}`. Nella forma senza `:?` la stessa dimenticanza
avrebbe prodotto un utente amministratore con password vuota, e lo stack sarebbe partito. La forma
con `:?` va usata per **ogni** variabile senza un valore predefinito sensato, negli stack che
verranno.

Infine, [ADR-0040](#adr-0040) è confermato nella forma definitiva: la terza via — `rs-init` con
`network_mode: "service:mongo-rs-1"` — funziona dentro un file Compose del repository e non solo
nella prova da riga di comando su cui era stata decisa. La riserva che
[V-023](Sources.md#v-023) aveva dichiarato è scaricata da [V-024](Sources.md#v-024).

**Alternative scartate:** aumentare `--wait-timeout` — non c'entra niente, `--wait` non è andato in
timeout, si è dichiarato soddisfatto, e un timeout più lungo non cambia una condizione già vera;
dare un healthcheck a `rs-init` — il punto tre; mettere un'attesa a tempo dopo `up` (`sleep 20`) —
funziona sulla macchina su cui la si è tarata e su nessun'altra, ed è esattamente il genere di riga
che in sala si scopre insufficiente davanti a cento persone; unire i due file d'ambiente in uno solo
alla radice — eviterebbe la doppia flag, ma metterebbe il pin dell'immagine, che è comune ai tre
stack, nello stesso file della password, che è di uno solo: o si copia il pin in tre posti, o si
mette una password nel file che leggono anche gli altri due; leggere l'esito dai log invece che dal
codice di uscita — `docker logs` va interrogato al momento giusto, che è il problema che si sta
cercando di risolvere.

**Fonti:** [S-056](Sources.md#s-056), [S-057](Sources.md#s-057), [V-024](Sources.md#v-024), [V-025](Sources.md#v-025)

<a id="adr-0042"></a>
## ADR-0042 — Che cosa `check_stack.py` deve saper bocciare quando lo stack ha un replica set

**Data:** 2026-08-31 · **Stato:** Accettata

**Contesto.** `tools/check_stack.py` nasce con lo stack 01 e conosce il mondo di quello stack: una
sola istanza, nessuna autenticazione, nessuna catena di avvio. Lo stack 02 introduce tre cose che il
primo non aveva — un replica set, un keyfile condiviso e una catena di dipendenze fra quattro
servizi — e ognuna delle tre porta un modo di sbagliare che non produce un errore leggibile ma un
sintomo spostato: un membro che resta fuori dalla replica e nei log sembra un problema di rete, un
`mongod` che rifiuta un keyfile con i permessi larghi e muore all'avvio, un `depends_on` con la
condizione sbagliata che riesce sulla macchina di chi scrive e fallisce in sala. Sono esattamente i
tre errori che questa feature ha commesso davvero, uno per Task, e che sono costati misure.

C'è poi un vincolo che rende il problema meno banale di quanto sembri: **il controllo deve girare su
un clone appena fatto**, dove il file `docker/02-replicaset/.env` non esiste, perché contiene la
password ed è fuori dal repository per decisione di [ADR-0014](#adr-0014). Lo stack 02 dichiara
quella variabile nella forma `${PASSWORD_AMMINISTRATORE:?…}`, che è una forma che **si rifiuta di
risolversi** quando la variabile manca — è la stessa qualità che al Task 4 ha reso rumoroso
l'errore, e qui diventa un ostacolo: senza un valore, `check_stack.py` si ferma prima di guardare una
sola regola.

**Decisione.** Quattro regole nuove, una correzione a una regola vecchia, e due modi di passare le
variabili.

*Le quattro regole.* Sono descritte dai messaggi che stampano, che restano la loro documentazione
vera:

1. dove c'è `--keyFile`, il percorso indicato deve essere coperto da un **volume nominato** e non da
   un percorso dell'host;
2. dove c'è `--replSet`, ci deve essere anche `--keyFile`;
3. un servizio atteso con `service_completed_successfully` deve dichiarare `restart: "no"`;
4. la condizione deve corrispondere al genere di servizio atteso — `service_healthy` verso un
   `mongod`, `service_completed_successfully` verso un one-shot, mai `service_started` verso nessuno
   dei due.

Ogni regola **si autolimita leggendo il file**, non un elenco di nomi da tenere aggiornato a mano:
la 2 si accende solo se qualcuno nel file dichiara `--replSet`, la 4 solo se qualcuno dichiara
`depends_on`. È così che lo stack 01, che gira senza autenticazione per scelta didattica
([ADR-0005](#adr-0005)), resta verde senza comparire in nessuna lista di eccezioni. Le liste di
eccezioni invecchiano in silenzio; una guardia che legge il file no.

*La correzione.* `avvia_mongod()` riconosceva un `mongod` solo quando il comando comincia con quella
parola. L'entrypoint ufficiale dell'immagine antepone `mongod` da sé quando il primo argomento
comincia per trattino ([S-022](Sources.md#s-022)), e la forma abbreviata — `command: ["--replSet",
"rs0"]` — è quella che gira in metà degli esempi in rete. Su quella forma lo strumento non vedeva un
`mongod`, quindi non pretendeva né la cache né il keyfile: dava la ricevuta senza aver guardato. Da
ora il riconoscimento accetta entrambe le scritture, e ignora il percorso davanti al nome.

*I due modi di passare le variabili.* `--ambiente` diventa **ripetibile**, con gli ultimi file che
vincono sui primi, e ha `tools/images.env` come valore predefinito. La semantica non è stata
inventata qui: è la stessa di `--env-file` di Compose ([S-056](Sources.md#s-056)), e la coincidenza
è voluta — chi impara una delle due impara l'altra, e chi le confonde non sbaglia. Accanto arriva
`--variabile NOME=valore`, ripetibile, che vince su tutti i file. È il posto della password nel
bersaglio `stack-check` del `Makefile`: un valore che dichiara di essere finto, che non raggiunge mai
un `mongod` perché lo strumento legge i file e non avvia niente.

**Conseguenze.** `make stack-check` passa ora entrambi i file Compose. Le regole sono state provate
sul file vero, non solo sui campioni dei test: sei copie dello stack 02, un difetto ciascuna, sei
messaggi distinti, e il file intatto verde — [V-026](Sources.md#v-026). La prova serviva perché
verde su un file vero non distingue «la regola ha guardato e ha approvato» da «la regola non è mai
entrata in funzione», ed è precisamente l'ambiguità in cui la regola sulla cache è rimasta finché
nessuno l'ha messa alla prova sulla forma abbreviata.

Resta un limite da non nascondere: sei difetti non sono tutti i difetti, e la conformità statica non
ha mai sostituito l'avvio dello stack. `check_stack.py` risparmia il tempo di scoprire in sala un
errore che si vedeva nel file; non dice che lo stack funziona, dice che non contiene gli errori che
questa feature ha già pagato.

**Alternative scartate:** committare un `docker/02-replicaset/.env.esempio` con una password
segnaposto, e leggerlo nel `Makefile` — funziona, ed è la soluzione più diffusa, ma mette nel
repository un file che *ha la forma* di un file di credenziali, e la prima cosa che fa chi clona è
copiarlo e usarlo così com'è: è l'abitudine che [ADR-0014](#adr-0014) e [ADR-0040](#adr-0040)
cercano di non insegnare, e in un materiale didattico l'esempio pesa più dell'avvertenza che lo
accompagna; togliere il `:?` dalla password per far girare il controllo — sarebbe piegare la
sostanza dello stack alla comodità di uno strumento, e riporterebbe la password vuota che al Task 4
era stata evitata per un soffio; tenere un elenco dei servizi esenti dalle regole nuove — invecchia
al primo stack aggiunto, e invecchia in silenzio; lasciare `stack-check` sul solo stack 01 e
verificare il 02 a mano — è lo stato da cui si parte, ed è il motivo per cui i tre errori sono stati
scoperti eseguendo invece che leggendo.

**Fonti:** [S-022](Sources.md#s-022), [S-056](Sources.md#s-056), [V-026](Sources.md#v-026)

<a id="adr-0043"></a>
## ADR-0043 — I dati di demo sullo stack 02: dentro `rs-init`, con la maggioranza, e uguali a quelli dello stack 01

**Data:** 2026-08-31 · **Stato:** Accettata

**Contesto.** Lo stack 02 sa formare un replica set, sa proteggerlo con un keyfile e sa creare
l'amministratore ([ADR-0038](#adr-0038), [ADR-0039](#adr-0039), [ADR-0040](#adr-0040)), ma finisce
con un database vuoto. Metà della demo è un confronto: la stessa interrogazione sullo stack 01 e
sullo stack 02, per mostrare che cosa cambia e che cosa no. Con due dataset diversi quel confronto
non dimostra niente, quindi la prima cosa che serve non è «dei dati», sono **gli stessi dati**.

La strada ovvia è quella dello stack 01: uno script in `/docker-entrypoint-initdb.d`. Sul replica
set non funziona, e il motivo è istruttivo. L'entrypoint ufficiale esegue quegli script sotto un
`mongod` **temporaneo e non replicato** — nessun `--replSet`, un processo che nasce e muore prima
che il server vero parta ([S-022](Sources.md#s-022)). Uno script che scrivesse là chiederebbe
`w: "majority"` a un'istanza che non ha una maggioranza, e più in generale scriverebbe prima che il
set esista. Lo stesso entrypoint salta quegli script quando il volume è già popolato, senza dirlo
([V-014](Sources.md#v-014)): la seconda ragione per non affidargli il seed è che il suo silenzio,
sullo stack 01, è già costato una diagnosi.

**Decisione.** Cinque scelte, e la prima è la sola discutibile.

*Il seed è l'ultimo passo di `rs-init`, non un quarto servizio.* La catena resta a **tre anelli**.
Un servizio `dati-init` separato sarebbe più pulito da guardare, e sarebbe la scelta di default; ha
però un costo preciso: chi avvia lo stack dovrebbe attendere **due** one-shot invece di uno, cioè un
secondo `docker compose wait`, e [ADR-0041](#adr-0041) ha appena stabilito che il verdetto
dell'avvio è il codice di uscita di *quel* comando lì. Due comandi d'attesa sono due verdetti, e due
verdetti sono la premessa di un `make up-02` che ne guarda uno e ignora l'altro. In cambio si ottiene
anche una cosa che non si era cercata: il caricamento dei dati è **la prima connessione
autenticata** dello stack, e sta nel file subito sotto il `createUser` che ha chiuso l'eccezione
localhost. Chi legge `10-rs-initiate.js` e poi `20-dati-demo.js` vede la sequenza per intero — prima
non serve la password, da qui in poi sì.

*Si scrive con `w: "majority"`, e con un `wtimeout`.* È la prima cosa tangibile che un replica set
offre e che un'istanza singola non può offrire: l'ack torna quando la scrittura è su una maggioranza
di membri, quindi sopravvive alla caduta del primario ([S-035](Sources.md#s-035)). Il prezzo è stato
misurato invece che stimato: **un millisecondo in più** di `w: 1`, su questa configurazione
([V-027](Sources.md#v-027)). Il `wtimeout: 10000` c'è perché senza di esso una scrittura che non
raggiunge la maggioranza aspetta per sempre; con esso, dopo dieci secondi, fallisce dicendolo — e
[ADR-0041](#adr-0041) fa fallire l'avvio invece di dichiararlo riuscito.

*Il caricamento è condizionato, con una via d'uscita esplicita.* Se `lab.ordini` ha già i 50 000
documenti attesi, lo script non fa niente e lo stampa. `RICARICA=1` forza la ricarica, ed è ciò che
`make seed-02` passa. La ragione è che `make down-02` promette di conservare i dati: un seed
incondizionato li cancellerebbe e li rifarebbe a ogni riavvio, cioè smentirebbe il bersaglio
accanto. La ragione didattica è la seconda: è la stessa regola che l'entrypoint ufficiale applica
in silenzio, scritta in tre righe che si leggono.

*Il file è una copia deliberata di quello dello stack 01, non un modulo condiviso.* Generatore,
seme, epoca e liste sono identici — è l'unico modo perché l'impronta coincida. Fattorizzare i due
script in un file solo li legherebbe: una modifica pensata per lo stack 02 cambierebbe di nascosto
il dataset dello stack 01, e i due stack devono poter divergere quando la loro topologia lo impone,
come è già successo per il write concern. La duplicazione è dichiarata in testa a entrambi i file, e
sorvegliata dove conta: **i due script di prova controllano la stessa terna di numeri**, quindi
toccarne uno solo fa diventare rosso l'altro.

*`reset-02` cancella i volumi dati per nome, non con `down -v`.* `down -v` porterebbe via anche il
volume del keyfile, e i tre membri dovrebbero ricostruire da zero un segreto condiviso che non
c'entra niente con i dati. Verificato: dopo `reset-02` resta in piedi il solo volume del keyfile, e
il segreto è byte per byte lo stesso ([V-028](Sources.md#v-028)).

**Conseguenze.** Sei bersagli nuovi nel `Makefile` — `up-02`, `down-02`, `reset-02`, `logs-02`,
`seed-02`, `smoke-02` — e `tools/smoke-replicaset.sh`, che esegue **42 controlli**: salute dei tre
membri, keyfile identico e a 400 su tutti e tre, esattamente un primario e due secondari, il rifiuto
di una connessione anonima e di una password sbagliata, versione e limiti di memoria, l'impronta del
dataset, e una scrittura con `w: "majority"` riletta da un secondario. L'impronta è
`50000 124861860.70 150281`, cioè **la stessa dello stack 01** ([V-013](Sources.md#v-013)).

Lo script è stato visto fallire, e la forma di quel fallimento ha cambiato lo script. Fermando un
membro, la prima versione usciva dopo tre righe — aveva ereditato dallo smoke dello stack 01 il
cancello «se un nodo non è sano, smetti», che su un'istanza singola è ovvio e su tre membri butta
via proprio le risposte che uno cerca in quel momento: *c'è ancora un primario? le scritture passano
ancora?* Ora il cancello scatta solo quando un container **non esiste**, e con un membro fermo lo
script riporta 34 verdi e 8 rossi dicendo, fra i verdi, «primari: 1» e «scrittura con w: majority
accettata» ([V-028](Sources.md#v-028)).

Resta scoperto il caso che conta di più: **due membri su tre fermi**, cioè la maggioranza persa e il
set in sola lettura. Non è stato provato qui perché è la scena del Task 8, e va misurato là.

**Alternative scartate:** un quarto servizio `dati-init` — più leggibile, ma aggiunge un secondo
comando d'attesa e toglie ad [ADR-0041](#adr-0041) il suo verdetto unico; lo script in
`/docker-entrypoint-initdb.d` — girerebbe su un `mongod` senza replica, dove `w: "majority"` non
vuol dire niente ([S-022](Sources.md#s-022)); un `mongorestore` da un dump versionato nel repository
— più veloce all'avvio, ma mette in git un file binario di alcune decine di MB che nessuno può
leggere in una code review, e toglie dalla vista il generatore, che è materiale didattico di per sé;
caricare con `w: 1` per far partire lo stack un secondo prima — il secondo non c'è ([V-027](Sources.md#v-027)),
e si rinuncerebbe alla sola cosa che distingue questo stack dal precedente; `down -v` in `reset-02` —
un `reset` che distrugge anche ciò che non è dato è un `reset` che si smette di usare.

**Fonti:** [S-022](Sources.md#s-022), [S-035](Sources.md#s-035), [V-013](Sources.md#v-013), [V-014](Sources.md#v-014), [V-027](Sources.md#v-027), [V-028](Sources.md#v-028)

<a id="adr-0044"></a>
## ADR-0044 — Due scene di failover, non una, e uno script che cronometra invece di ricordare

**Data:** 2026-08-31 · **Stato:** Accettata

**Contesto.** [ADR-0034](#adr-0034) aveva stabilito che il lab non finge che `docker kill` sia un
guasto, e aveva rimandato a `feature/02` il compito di progettare la demo sapendolo. Adesso i
numeri ci sono. `docker kill` sul primario costa **~10 secondi** di elezione e lascia il container
`exited` con `RestartCount=0`; lo `shutdown` costa **~0,5 secondi** e il container torna su da sé
([V-029](Sources.md#v-029)). Venti volte di differenza, e nel verso opposto all'intuizione: il
gesto brutale è quello lento.

Il log spiega perché, e con una precisione che nessuna parafrasi migliora: la caduta è notata in
tre decimi di secondo — `id=21216`, «Connection refused» nell'attributo — e poi non succede niente
per nove secondi, finché `id=4615652` dichiara di indire l'elezione «since we've seen no PRIMARY in
election timeout period», con `electionTimeoutPeriodMillis: 10000` scritto accanto. **L'elezione
vera dura sei millisecondi** ([V-030](Sources.md#v-030)). I dieci secondi non sono l'elezione: sono
l'attesa prima di cominciarla.

**Decisione.**

*Due bersagli distinti, non uno con una variabile.* `make failover-02` esegue la scena con
`docker kill`; `make failover-02-termina` quella con lo `shutdown`. Un bersaglio solo con un
parametro invita a mostrarne una sola, e la sola che si mostrerebbe è la prima — quella che dà il
numero sbagliato a chi generalizza.

*Lo script cronometra la propria esecuzione.* `tools/failover-replicaset.sh` non stampa i numeri di
[V-029](Sources.md#v-029): li rimisura ogni volta e stampa quelli. Se in sala l'elezione dura il
doppio, si vede sullo schermo invece di essere smentita da una slide. Il cronometro parte **prima**
del colpo — l'osservatore si collega, si autentica, dichiara `PRONTO`, e solo allora il primario
cade — perché avviare `mongosh` dopo metterebbe il suo secondo di avvio dentro la misura.

*Il log si filtra per `id`.* Lo script stampa dieci `id` e nessun testo di messaggio, secondo la
regola 1 di [ADR-0035](#adr-0035). Legge il log del nodo **eletto** e non dell'osservatore: chi ha
solo votato registra `23980` e basta, e guardare il log sbagliato porta a concludere che
un'elezione non lasci traccia.

*La frase giusta è nello script, non nella memoria di chi parla.* Prima del `docker kill` lo script
stampa: «da dire ad alta voce: *sto SPEGNENDO un nodo*, non *sto simulando un crash*». È il punto 1
di [ADR-0034](#adr-0034) messo dove non si può dimenticare.

*`tools/reset-demo.sh <stack>` salda il debito di `feature/01`.* Riporta uno stack allo stato di
partenza **senza ricostruirlo**: riavvia i container fermati a mano, aspetta che i tre membri siano
sani, che esista un primario e che sia tornato quello a priorità 2, cancella dal database `lab`
tutto ciò che non è `ordini`, ricarica il dataset. Non è `reset-02`, che ferma lo stack e cancella i
volumi: serve al caso opposto, la prova generale in cui la stessa scena si ripete tre volte. Lo
stack è un **argomento**, così `feature/03` lo eredita invece di riscriverlo.

**Conseguenze.** Provato sul vero: dopo un `make failover-02` che lascia `mongo-rs-1` `exited`,
`reset-demo.sh 02` lo riavvia, aspetta che si riprenda il ruolo, e lo smoke torna 42/0. Sporcando
il database di proposito — due collezioni di scarto e cento documenti cancellati — lo script
riporta l'impronta a `50000 124861860.70 150281` e stampa i nomi di ciò che ha tolto.

Il debito di [ADR-0035](#adr-0035) è saldato: gli `id` di un'elezione vera esistono e sono in
[V-030](Sources.md#v-030). La riserva scritta in quella pagina — «gli `id` verranno inseriti in
`feature/02`, dopo averne vista una» — può essere tolta al Task 12.

Resta scoperto il caso della **maggioranza persa**, due membri su tre fermi, in cui il set diventa
di sola lettura: è la variante che spiega meglio di ogni diagramma perché i membri sono tre e non
due, e non è ancora stata misurata.

**Alternative scartate:** un bersaglio solo con `SCENA=kill|shutdown` — comodo, e finisce che se ne
mostra una; stampare i numeri misurati invece di rimisurarli — una slide che dice «dieci secondi»
mentre lo schermo ne conta venti è peggio di nessun numero; abbassare `electionTimeoutMillis` per
accorciare la scena — renderebbe la demo più agile e mostrerebbe un cluster che il pubblico non
troverà, visto che il valore predefinito è quello che si eredita installando; usare `docker stop`
al posto di `docker kill` — è più gentile ma soffre dello stesso equivoco sulla politica di
riavvio, e in più aggiunge dieci secondi di attesa del `SIGTERM` che non insegnano niente;
`kill -9 1` dentro il container — non fa niente e ritorna successo, misurato in
[ADR-0034](#adr-0034), e sarebbe una scena che non succede.

**Fonti:** [S-044](Sources.md#s-044), [V-017](Sources.md#v-017), [V-029](Sources.md#v-029), [V-030](Sources.md#v-030)

<a id="adr-0045"></a>
## ADR-0045 — La terza scena, e un lettore di log che non si fida di `docker logs`

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto.** [ADR-0044](#adr-0044) si chiude dichiarando che cosa manca: «Resta scoperto il caso
della **maggioranza persa**, due membri su tre fermi, in cui il set diventa di sola lettura».
Adesso è misurato ([V-031](Sources.md#v-031)).

Il motivo per cui mancava vale più del caso in sé. Le due scene di [ADR-0044](#adr-0044)
**finiscono bene**: il set perde un membro e se ne dà un altro. Chi le guarda ne ricava che un
replica set «regge ai guasti» — senza mai sentirsi dire *a quanti*. La risposta è una sottrazione:
la maggioranza di tre è due, quindi si tollera **un** guasto. Al secondo, il superstite resta vivo,
sano, raggiungibile, con tutti i dati, e dopo circa nove secondi **si retrocede da solo**. Da lì le
scritture rispondono `NotWritablePrimary` e le letture continuano.

Il numero è 9 329 ms di mediana su sei esecuzioni, in una forbice di 9,1–9,4 s, e la forbice non è
rumore: `electionTimeoutMillis` vale 10 000 ms ma si conta dall'**ultimo battito ricevuto**, e i
battiti vanno ogni 2 000 ms ([S-044](Sources.md#s-044)), quindi la misura cade fra 8 e 10 secondi a
seconda di dove capita il colpo. La riga di log che chiude la scena è `id=21809`, «Can't see a
majority of the set, relinquishing primary»: non «ho perso la connessione», ma «non vedo una
maggioranza, quindi **cedo**».

Lavorando alla scena è saltato fuori dell'altro, e non era previsto: dopo un riavvio del demone
Docker, `docker logs` può restare **fermo per sempre** all'istante in cui il demone è caduto,
mentre il container è tornato su da solo e mongod continua a scrivere. Senza errori: silenzio.
Misurato su un membro partito alle 08:05 con 2 548 righe scritte, di cui `docker logs` ne mostrava
zero ([V-032](Sources.md#v-032)). La sezione «righe di log» di tutte e tre le scene legge proprio
`docker logs`.

**Decisione.**

*Una terza scena, e non una variante delle prime due.* `make failover-02-maggioranza` esegue
`./tools/failover-replicaset.sh maggioranza`. Ferma un secondario — il caso già coperto dallo
smoke, che passa e non insegna niente di nuovo — poi ferma il secondo e cronometra la
retrocessione. Sta accanto alle altre due per la stessa ragione per cui quelle sono due e non una
([ADR-0044](#adr-0044)): un bersaglio solo con un parametro invita a mostrarne uno, e quello che si
mostrerebbe è sempre il primo.

*La scena finisce con il set rotto, e nessuno lo rialza.* Non c'è un ripristino automatico in coda,
perché non ci sarebbe nemmeno nella realtà: **non esiste nessuno che possa eleggere il
superstite**, ed è esattamente il punto. Lo script lo dice e indica il gesto —
`./tools/reset-demo.sh 02` — invece di eseguirlo. Una scena che si ripara da sola cancella la sola
cosa che aveva da mostrare.

*La differenza fra connessione diretta e URI del replica set si mostra, non si racconta.* Il
superstite retrocesso **legge**: `mongosh --host localhost` restituisce i 50 000 documenti, perché
`mongosh` aggiunge `directConnection=true` da sé quando la stringa non nomina un `replicaSet`
([S-045](Sources.md#s-045)). Chi prova la demo così conclude che il set funziona ancora; con l'URI
del replica set e `readPreference` predefinita il driver non trova nessun server. Lo script stampa
tutte e due le risposte, perché è la confusione più facile da fare e la più cara da fare in
produzione.

*Il numero si rimisura e si spiega, come in [ADR-0044](#adr-0044).* Il cronometro gira dentro il
primario stesso — una `mongosh` collegata e autenticata prima del colpo, che interroga `hello()`
ogni 20 ms — perché nessun altro nodo può datare quella retrocessione: non ne resta nessuno. E
subito sotto il numero lo script stampa la forbice 8–10 s e il perché, così una sala che vede 8,7
non sente una smentita.

*Il lettore di log controlla la propria fonte prima di crederle.* Prima di leggere, lo script
confronta l'ultima riga catturata con `.State.StartedAt` del container: se il log è più vecchio
dell'avvio non può essere di questa esecuzione, e le righe si chiedono a **mongod** con
`getLog: "global"`, che le tiene in memoria e non dipende da Docker. Il ripiego stampa una riga che
dice di essere scattato: il tranello si insegna, non si nasconde. Il confronto è **stretto** — a
parità di secondo si ripiega — perché credere a un log vecchio costa la scena, mentre chiedere a
mongod non costa niente. Vale per tutte e tre le scene, non solo per quella nuova.

*Quel rilevatore ha un test.* `tools/tests/test_failover_log.py` estrae la funzione dallo script,
senza tenerne una copia che divergerebbe, e la esegue con `docker` sostituito da un finto che
risponde con gli istanti veri di [V-032](Sources.md#v-032). Un rilevatore la cui condizione di
scatto si presenta di rado può rompersi in silenzio e restare rotto fino alla sera in cui serve; il
test è stato verificato non vuoto rimettendo il difetto e vedendolo fallire.

**Conseguenze.** Il debito dichiarato in [ADR-0043](#adr-0043) e in [ADR-0044](#adr-0044) è
saldato. Provato sul vero: la scena misura 9 316 ms, stampa le sette righe di log che la
raccontano, e `reset-demo.sh 02` riporta l'impronta a `50000 124861860.70 150281` con `mongo-rs-1`
primario, cancellando la collezione di scarto che la scena lascia. `make tools-test` passa 100
prove, cinque più di prima.

I numeri vanno in `docs/02-architetture/replica-set.md` al Task 9, ed è lì che la sottrazione «tre
membri, maggioranza due, un guasto tollerato» va scritta per esteso: la scena la mostra, la pagina
la deve dire.

Resta una riserva nuova per il Task 12, accanto a quelle già in coda: l'errore che il driver
restituisce quando manca il primario è, nel lab, `getaddrinfo ENOTFOUND mongo-rs-2` — un errore di
risoluzione del nome, perché un container fermo sparisce dal DNS di Compose. Su macchine vere il
testo sarebbe un altro. Chi riconosce la situazione dal testo dell'errore sbaglia, ed è la regola 1
di [ADR-0035](#adr-0035) applicata ai messaggi dei driver invece che a quelli di mongod. Anche il
congelamento di `docker logs` merita quella pagina.

**Alternative scartate:** fermare il primario e un secondario invece di due secondari — la
maggioranza si perde uguale, ma il superstite non è mai stato primario e non c'è nessuna
retrocessione da cronometrare, cioè sparisce il numero; far rialzare il set in coda alla scena —
comodo in prova generale e distruttivo in sala, perché toglie di mezzo la sola cosa che si voleva
far vedere; costruire un quarto stack a due membri per dimostrare che non tollera guasti — uno
stack da mantenere per sempre per illustrare un'aritmetica che si dice in una frase; leggere sempre
da `getLog` invece di `docker logs` — più uniforme e più robusto, ma è un anello di 1 024 righe
([V-032](Sources.md#v-032)) e insegnerebbe un comando che nessuno userà mai per guardare i log di
un container, mentre il ripiego scatta quando serve e lo dichiara; trattare il congelamento come
una stranezza di Docker Desktop da ignorare — è successo alla prima mattina utile, e la sera del
talk non c'è tempo per scoprire perché il log è vuoto.

**Fonti:** [S-033](Sources.md#s-033), [S-035](Sources.md#s-035), [S-044](Sources.md#s-044), [S-045](Sources.md#s-045), [V-031](Sources.md#v-031), [V-032](Sources.md#v-032)

<a id="adr-0046"></a>
## ADR-0046 — Il replica set si presenta con i numeri che ha, e il confronto con l'istanza singola si misura

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto.** [ADR-0032](#adr-0032) ha dato all'istanza singola una forma precisa — quattro limiti
citabili invece di un aggettivo — e ha lasciato scritto un rimando: il confronto sulla **perdita di
dati** si sarebbe fatto in `feature/02`, «adesso c'è un replica set con cui farlo». La pagina
dell'istanza singola porta un numero che fa male: 100 scritture confermate al client e sparite dopo
un `SIGKILL` ([V-016](Sources.md#v-016)). Il numero gemello non esisteva.

Adesso esiste, ed è **zero** su 12 901 scritture confermate con `w: "majority"` mentre il primario
veniva ucciso ([V-033](Sources.md#v-033)). Con esso arrivano gli altri numeri che la pagina
aspettava: le tre scene di failover ([V-029](Sources.md#v-029), [V-030](Sources.md#v-030),
[V-031](Sources.md#v-031)), il ritardo di replica e il prezzo della maggioranza
([V-027](Sources.md#v-027)).

**Decisione.**

*La pagina risponde a «quanti guasti regge», e la risposta è una sottrazione.* Tre membri,
maggioranza due, **un** guasto tollerato in scrittura. Sta in cima, prima delle elezioni e prima del
file Compose, perché è la domanda che l'istanza singola lascia aperta e perché è l'unica risposta
che non si possa dare con un aggettivo.

*Le tre scene stanno in una tabella, con i loro numeri e i loro comandi.* `docker kill` ~10 s,
`shutdown` ~0,5 s, maggioranza persa ~9,3 s. Chi legge la pagina deve poterle rifare, e chi le rifà
deve trovare i numeri accanto al comando che li produce, non in fondo.

*Il confronto con l'istanza singola si misura, e si mostra anche la parte scomoda.* Zero perse
contro cento è la riga che si ricorda; da sola sarebbe pubblicità. Va con l'altro esito della stessa
prova: il documento `n=2698`, per cui il client ha ricevuto un **errore** e che nel database **c'è**
([V-033](Sources.md#v-033)). Lo scambio vero non è «niente si perde», è «la bugia cambia verso»: là
il client crede di avere dati che non ha, qui crede di non avere dati che ha. Il secondo si
sopravvive se le scritture si possono rifare, e questa condizione va detta.

*Write concern e read preference si trattano come una coppia, non come due sezioni.* Sono i due capi
dello stesso scambio: `w: "majority"` costa un millisecondo in più e compra la durabilità
([V-027](Sources.md#v-027)); leggere dai secondari distribuisce il carico e costa freschezza, con la
frase del manuale citata alla lettera — «All read preference modes except `primary` may return stale
data» ([S-058](Sources.md#s-058)). Separarle produce due elenchi corretti e nessuna decisione.

*Ogni numero porta la sua riserva addosso, sulla stessa riga.* Il millisecondo di `w: "majority"` è
un salto su un bridge locale, non fra due datacenter. I 9,3 secondi sono una forbice 8–10. I 10
secondi dell'elezione sono attesa, non elezione. Le riserve stanno accanto ai numeri e non in una
nota in fondo, perché la nota in fondo non arriva sulle slide.

**Conseguenze.** Nasce `docs/02-architetture/replica-set.md`. In `docs/README.md` la riga passa da
promessa a collegamento. La pagina dell'istanza singola riceve i rimandi nei tre punti in cui
prometteva un seguito — il failover che non c'è, `w: "majority"` che mente, la manutenzione che
vuole una finestra di fermo — e il rimando di [ADR-0032](#adr-0032) è saldato.

Resta dichiarato, nella sezione «cosa questa pagina non dice», ciò che non è stato misurato: la
stessa prova con `retryWrites=false`, `maxStalenessSeconds`, e qualunque confronto di prestazioni,
che ha senso solo sotto carico controllato e quindi non prima di `feature/04`.

**Alternative scartate:** argomentare il confronto invece di misurarlo — ci sarebbe voluta mezza
giornata in meno e la pagina avrebbe detto «i dati sono al sicuro», che è esattamente il tipo di
frase che questo repository non scrive; mostrare solo lo zero perse — un confronto che riporta
soltanto la buona notizia non è un confronto; elencare i cinque modi di read preference e fermarsi
lì — l'elenco è nel manuale, e ripeterlo senza il prezzo non aggiunge niente; rimandare tutto a
`feature/04`, dove ci sarà l'applicazione — il rimando di [ADR-0032](#adr-0032) è già stato spostato
una volta, e una decisione rimandata due volte è una decisione che non si prende.

**Fonti:** [S-035](Sources.md#s-035), [S-037](Sources.md#s-037), [S-044](Sources.md#s-044), [S-058](Sources.md#s-058), [V-016](Sources.md#v-016), [V-027](Sources.md#v-027), [V-029](Sources.md#v-029), [V-030](Sources.md#v-030), [V-031](Sources.md#v-031), [V-033](Sources.md#v-033)

---

<a id="adr-0047"></a>
## ADR-0047 — Il backup si documenta dopo averlo rotto, e il dump che fallisce resta sul disco

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto.** [ADR-0022](#adr-0022) ha registrato un paradosso e lo ha lasciato aperto: `--oplog`
funziona solo dove c'è un oplog, cioè su un replica set, quindi su un'istanza singola **non esiste
un dump coerente a un istante**. La fonte era già in casa da `feature/01` ([S-011](Sources.md#s-011))
e la pagina no, perché non c'era lo stack su cui provarla. Adesso c'è.

Una pagina di backup è il posto dove è più facile scrivere il falso senza accorgersene. «`--oplog`
rende il dump coerente» è vero e non dice niente: non dice **rispetto a quale istante**, non dice
quanto valga in documenti, non dice quando smette di funzionare. E la documentazione di `mongodump`,
che pure elenca sei combinazioni vietate, **non nomina** il modo in cui `--oplog` fallisce davvero:
l'oplog che rotola via sotto il dump ([V-036](Sources.md#v-036)).

**Decisione.**

*Il punto nel tempo si indica, non si evoca.* Il dump è durato 50 ms; il restore completo si ferma a
740 documenti mentre alla fine del comando ce n'erano 741 ([V-035](Sources.md#v-035)). Il punto di
ripristino è l'istante dell'**ultima voce di oplog catturata**, e cade dentro l'esecuzione del
comando, non alla sua ultima riga di log. La pagina scrive questo, con il numero, invece di
«coerente a un punto nel tempo».

*`--oplogReplay` si quantifica invece di raccomandarlo.* Stesso file, due restore: **733** documenti
senza, **740** con. Sette. Su un dump da cinquanta millisecondi sette documenti sono un aneddoto; la
pagina lo dice, e dice che su un dump da mezz'ora sono mezz'ora di scritture. Un'opzione
raccomandata senza un numero è cerimonia, e chi legge la salta.

*Il fallimento si mostra mentre fallisce, e si dichiara che è forzato.* Lo stack del lab ha una
finestra di oplog di **quindici ore** ([V-034](Sources.md#v-034)): riempirla non è una demo. Il
guasto è stato riprodotto su un'istanza usa-e-getta con oplog da 1 MB e checkpoint al secondo, e la
pagina riporta il testo esatto — `Failed: oplog overflow: mongodump was unable to capture all new
oplog entries during execution` — **insieme** all'ammissione che la scala è compressa: in produzione
il caso è un oplog normale e un dump lungo, non un oplog assurdo e un dump breve. Riprodurre il
meccanismo è onesto; far credere che siano le stesse grandezze non lo sarebbe.

*Il fallimento lascia 1,8 GB sul disco, e questa è la riga che va sulle slide.* `mongodump` si
ferma **dopo** aver scritto tutte le collezioni: sul disco resta un albero che assomiglia a un
backup, senza `oplog.bson` e senza `prelude.json`. L'unico segnale è il codice di uscita **1**. La
pagina ne ricava una regola operativa in due righe — si controlla l'uscita, si controlla che
`oplog.bson` esista — perché la regola è la sola parte che sopravvive alla lettura.

*Il limite dello strumento si cita dalla fonte che lo dichiara.* Non è `mongodump`: è la pagina dei
metodi di backup, che apre con «`mongodump` and `mongorestore` are tools for backing up and
restoring **small** MongoDB deployments» e mette in tabella RTO alto, RPO alto, nessun ripristino
continuo, coerenza «Not guaranteed» ([S-060](Sources.md#s-060)). La riserva della sezione «cosa
questa pagina non copre» non è un'opinione dell'autore: è una citazione.

*Dove fonte e misura non coincidono, si scrivono tutte e due.* La stessa tabella dichiara «impact on
source: High, requires write lock», e su questo stack le scritture non si sono fermate per i 50 ms
del dump ([V-035](Sources.md#v-035)). La fonte resta citata come dichiarazione dell'editore, la
misura resta accanto come osservazione, e la contraddizione resta visibile invece di essere risolta
scegliendo la versione più comoda.

*Il restore si verifica contando, con la disciplina di `smoke-02`.* Impronta di `lab.ordini`
identica prima e dopo, in entrambe le esecuzioni: `50000 124861860.70 150281`. Un backup che nessuno
ha mai ripristinato non è un backup, e un ripristino che nessuno ha mai contato non è una verifica.

*Il file di dump è un segreto.* `--oplog` impone il dump completo ([S-011](Sources.md#s-011)),
il dump completo contiene `admin/system.users.bson`, e il restore lo dice a voce alta —
`restoring users from …`. La pagina lo scrive accanto al comando, non in fondo, e rimanda alla
regola che questo repository già applica al keyfile ([ADR-0014](#adr-0014)).

**Conseguenze.** Nasce `docs/03-amministrazione/backup-restore.md`, la prima pagina della sezione
`03-amministrazione` scritta in questo branch; in `docs/README.md` la riga passa da promessa a
collegamento. [S-011](Sources.md#s-011), che dal `feature/01` era citata dal solo
[ADR-0022](#adr-0022), acquisisce il secondo ADR che la usa. Il paradosso di [ADR-0022](#adr-0022)
resta vero e adesso ha il suo rovescio scritto: dove l'oplog c'è, il dump a caldo coerente si fa, e
si è fatto.

Resta dichiarato ciò che non è stato provato: `--oplogLimit`, `--readPreference=secondary` per
scaricare da un secondario, il restore su uno stack **diverso** da quello di origine — che è il caso
vero di un ripristino — e il restore parziale **senza** `--oplogReplay`, che non dà nessun errore e
produce un ripristino incoerente in silenzio.

**Alternative scartate:** descrivere il fallimento invece di provocarlo — sarebbe costato un'ora in
meno e avrebbe prodotto la frase «attenzione alla finestra dell'oplog», che non ha mai fermato
nessuno; rimpicciolire l'oplog dello stack del lab per mostrarlo lì — `replSetResizeOplog` non
scende sotto ~990 MB e avrebbe comunque sporcato lo stack che serve alle altre demo; usare
`--oplogSize 1` e basta — provato, e non funziona: il taglio è vincolato al timestamp dell'ultimo
checkpoint, e senza `--syncdelay` la finestra resta di minuti ([V-036](Sources.md#v-036)); tacere la
riga «requires write lock» perché contraddetta dalla misura — la fonte va citata per quello che
dice, e il disaccordo con la misura è informazione, non imbarazzo; rimandare la pagina a un branch
di amministrazione — `--oplog` esiste solo qui, e una pagina di backup senza `--oplog` sarebbe la
pagina dello standalone, cioè [ADR-0022](#adr-0022) un'altra volta.

**Fonti:** [S-011](Sources.md#s-011), [S-059](Sources.md#s-059), [S-060](Sources.md#s-060), [V-034](Sources.md#v-034), [V-035](Sources.md#v-035), [V-036](Sources.md#v-036), [V-037](Sources.md#v-037)

---

<a id="adr-0048"></a>
## ADR-0048 — Il keyfile si giustifica dicendo a quali condizioni la sua fonte lo ammette

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto.** Il lab autentica i membri con un keyfile da [ADR-0005](#adr-0005), e la stessa fonte
che spiega come farlo scrive: «Use keyfiles only for testing and development environments because
of their limited manageability and cryptographic strength. For production environments, use X.509
certificates» ([S-005](Sources.md#s-005)). La riserva è registrata da agosto e non era ancora stata
scritta in una pagina rivolta a chi legge. Una pagina che insegna il keyfile senza riportarla
insegna male, e il modo in cui la si riporta decide se il lettore capisce o si spaventa.

C'è poi un debito nominale. [ADR-0026](#adr-0026) intesta a questa pagina, per nome, «la distinzione
fra utenti del cluster e utenti locali allo shard». Il branch che chiude quel debito è questo, e lo
shard non c'è: la distinzione va data nella forma che il replica set consente, senza fingere di
avere provato il caso sharded.

**Decisione.**

*La riserva si cita per intero, e si smonta.* «Test and development» non è un difetto del keyfile:
è una descrizione della sua economia. La pagina riporta la frase con le parole della fonte, poi dice
che cosa costerebbe l'alternativa in questo stack — una CA, un certificato per membro con `SAN` che
nomini ogni host, e una procedura di rotazione in sei passi e tre giri di riavvii
([S-063](Sources.md#s-063)). Il keyfile qui non è una scorciatoia: è la scelta giusta per un lab che
deve partire offline sul portatile di chi presenta. Dirlo con il numero dei passi accanto è più
onesto che dirlo con un aggettivo.

*Il controllo degli accessi arriva con il keyfile, e va detto perché è controintuitivo.* Nel comando
dei tre membri `--auth` non compare, eppure ogni comando vuole credenziali: misurato
([V-038](Sources.md#v-038)), e dichiarato da due fonti — «`--keyFile` implies `--auth`»
([S-002](Sources.md#s-002)), «enforces both Self-Managed Internal/Membership Authentication and
Role-Based Access Control» ([S-005](Sources.md#s-005)). È la stessa frase che vale per X.509
([S-061](Sources.md#s-061)): l'autenticazione interna, comunque la si faccia, si porta dietro
quella dei client. È anche la ragione per cui esiste la catena di [ADR-0040](#adr-0040), e la pagina
lo richiama invece di raccontarla di nuovo.

*Il debito di ADR-0026 si salda con la misura, non con l'analogia.* In un replica set un utente
locale a un nodo **non esiste**, e non per convenzione: `createUser` sul database `local` — l'unico
che non viene replicato — risponde `Cannot create users in the local database`; su un secondario
risponde `not primary`; e l'utente interno dei membri non è un documento in nessuna collezione
([V-038](Sources.md#v-038)). Tre righe di prova al posto di un paragrafo prudente. Il caso sharded,
dove gli utenti locali a uno shard esistono davvero perché ogni shard è un replica set con il suo
`admin`, resta **marcato come non eseguito** ed è dovuto a `feature/03`: la regola di
[ADR-0035](#adr-0035) e [ADR-0036](#adr-0036) vale anche quando la marcatura è scomoda.

*La migrazione a X.509 si esegue, per quel poco che si può eseguire.* Il piano chiedeva «le
differenze concrete». Descriverle dalla documentazione sarebbe bastato a riempire la sezione, e
avrebbe prodotto l'ennesima parafrasi. La sequenza `sendKeyFile` → `sendX509` → `x509` di
[S-062](Sources.md#s-062) è stata invece eseguita su un'istanza usa-e-getta con l'immagine pinnata,
e ha restituito due fatti che la fonte non scrive ([V-039](Sources.md#v-039)): l'ordine dei due
`setParameter` **non è indifferente** — `clusterAuthMode` non sale finché `tlsMode` non è almeno
`preferTLS`, perché il vincolo è sulle connessioni uscenti — e la scala è **a senso unico**, su
entrambi i parametri, con `Illegal state transition` a sbarrare il ritorno. Chi sbaglia tappa non
annulla il comando: riavvia il nodo.

*Il fatto più utile è il rifiuto che nessuno si aspetta.* `mongod --clusterAuthMode sendKeyFile`,
cioè il modo di transizione che continua a mandare il keyfile, **non parte** senza TLS:
`BadValue: need to enable TLS via the tlsMode flag`, uscita 1 ([V-039](Sources.md#v-039)). La
migrazione verso X.509 non comincia da X.509: comincia da TLS, e quindi dai client. La pagina lo
mette prima della sequenza, perché è la cosa che cambia la stima dei tempi.

*Il costo per i client si mostra con i suoi messaggi d'errore.* Dopo `requireTLS` un client in
chiaro viene chiuso, un client TLS senza certificato viene chiuso con `No SSL certificate provided
by peer`, e un client che si connette per indirizzo invece che per nome viene fermato **dal client
stesso** perché il `SAN` non lo elenca ([V-040](Sources.md#v-040)). Tre rifiuti diversi, nessuno dei
quali è il server che va male. È il preventivo che [S-062](Sources.md#s-062) riassume in una riga —
«applies to all connections; that is, with the clients as well as with the members of the cluster»
— reso in tre schermate.

*Quello che non si esegue si dichiara, e la fonte dichiara per prima.* [S-061](Sources.md#s-061)
scrive che «a full description of TLS/SSL, PKI … is beyond the scope of this document» e presuppone
«access to valid X.509 certificates». Questo repository fa lo stesso: non insegna a produrre
certificati, non ne distribuisce, e non pretende di aver provato un *rolling upgrade* — che per
definizione richiede un cluster misto, mentre la prova è girata su un nodo solo. La sezione lo
scrive.

**Conseguenze.** Nasce `docs/03-amministrazione/sicurezza-keyfile-x509.md`, seconda pagina della
sezione `03-amministrazione` di questo branch; in `docs/README.md` la riga passa da promessa a
collegamento. [S-005](Sources.md#s-005) acquisisce il quarto ADR che la cita, [S-002](Sources.md#s-002)
e [S-006](Sources.md#s-006) il terzo: sono le fonti di `feature/00` che questo branch ha finalmente
messo alla prova invece di limitarsi a citarle. Il debito nominale di [ADR-0026](#adr-0026) è
saldato per la parte replica set; la parte sharded resta aperta e marcata, con la sede già scritta.

**Alternative scartate:** scrivere la sezione X.509 dalla sola documentazione — sarebbe costata
un'ora in meno e non avrebbe prodotto né il rifiuto di `sendKeyFile` senza TLS né il vincolo
sull'ordine, che sono le due cose per cui la sezione vale la pena; mostrare X.509 **funzionante**
sullo stack del lab, con una CA e tre certificati generati all'avvio — è la strada tecnicamente più
ricca, e va scartata per tre motivi: allunga `make up-02` di una generazione di chiavi, introduce
certificati con una scadenza dentro un lab che deve funzionare anche fra un anno
([ADR-0016](#adr-0016)), e sposterebbe la demo dal replica set alla PKI, che non è l'argomento del
talk; tacere la riserva «test and development» per non indebolire il lab — è scritta nella fonte
che il repository cita da agosto, e nasconderla la renderebbe la prima domanda ostile in sala;
rimandare la distinzione sugli utenti a `feature/03`, dove lo shard esiste — [ADR-0026](#adr-0026)
la intesta a questa pagina per nome, e un debito si salda dove è scritto, marcando la parte che
manca.

**Fonti:** [S-002](Sources.md#s-002), [S-005](Sources.md#s-005), [S-006](Sources.md#s-006), [S-061](Sources.md#s-061), [S-062](Sources.md#s-062), [S-063](Sources.md#s-063), [V-038](Sources.md#v-038), [V-039](Sources.md#v-039), [V-040](Sources.md#v-040)
