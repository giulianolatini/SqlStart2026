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

---

<a id="adr-0049"></a>
## ADR-0049 — Un debito si chiude eseguendo, e il primo esito è che due righe erano sbagliate

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto.** Tre pagine scritte in `feature/00` e `feature/01` portano una riserva che nomina
questo branch come sede del saldo, e una di esse la scrive come clausola di non chiusura:
[ADR-0035](#adr-0035) stabilisce che «la sezione sull'elezione resta con un debito scritto in
chiaro» finché non si è vista un'elezione vera. [ADR-0036](#adr-0036), regola 6, marca
«**non eseguito su questo branch**» i comandi di amministrazione del replica set nella guida a
`mongosh`. [ADR-0033](#adr-0033) annuncia due trappole che `feature/02` dovrà aggiungere:
**permessi del keyfile** e **scoperta della topologia**.

C'è anche un debito più piccolo e più preciso, dichiarato nel
[registro](registro-operativo-sviluppo.md) alla chiusura del Task 2: il messaggio d'errore del
keyfile con permessi larghi era stato misurato ma non era mai entrato in
[`Sources.md`](Sources.md). Era «l'unico debito documentale aperto dai due task chiusi», e lo è
rimasto per dieci task.

Chiudere questi debiti si può in due modi. Il modo breve è togliere le marcature, perché adesso il
replica set c'è e i comandi «ovviamente funzionano». Il modo lungo è eseguirli e guardare
l'output.

**Decisione.**

*Si esegue, e si accetta il rischio che la pagina avesse torto.* È successo due volte. La §3.2
della guida a `mongosh` avvertiva che «un secondario non risponde alle letture finché non glielo si
dice»: misurato, risponde — nessun `setReadPref`, `readPreference` a `primary`, e 50 000 documenti
contati su `mongo-rs-2` ([V-042](Sources.md#v-042)). Peggio: la **stessa pagina** lo diceva già
giusto in §1.5, dove [S-045](Sources.md#s-045) spiega che una stringa con un solo membro parla con
quel membro «anche se è un secondario». La guida contraddiceva se stessa, e nessuna rilettura lo
aveva notato perché entrambe le frasi, da sole, suonano ragionevoli. La correzione tiene §1.5 e
riscrive §3.2, e la pagina dice **perché** era sbagliata invece di limitarsi a non esserlo più.

*La marcatura si toglie a misura, non a sezione.* Di §3.2 escono dalla marcatura i comandi
eseguiti; `rs.add()` e `rs.remove()` sono stati provati **solo nella forma che fallisce** — su un
secondario, dove sono innocui — perché aggiungere un quarto membro richiede un container che questo
stack non ha e togliere un membro vivo romperebbe le prove successive. Quelle due righe restano
marcate. La §3.3, sullo sharded cluster, resta marcata per intero ed è dovuta a `feature/03`. È la
stessa disciplina di [ADR-0048](#adr-0048): il debito si salda dove è scritto, marcando la parte
che manca.

*Gli `id` dell'elezione entrano nel log citati per numero e con il testo accanto.* La sequenza di
[V-030](Sources.md#v-030) — da `id: 21216` «Member is now in state DOWN» a `id: 21358` «Replica set
state transition» — sostituisce la §3.3 di `log.md`, che fino a ieri si intitolava «Il debito, in
chiaro». La regola 1 di [ADR-0035](#adr-0035) vuole il numero, perché è quello che non cambia fra
versioni; questa pagina aggiunge il testo accanto, perché un elenco di numeri non insegna a
nessuno che cosa stia succedendo. Il numero serve a ritrovare, il testo a capire, e servono
entrambi.

*Il debito più utile era quello che nessuno aveva dichiarato.* Prima di riempire la §3.3 di
`log.md` con gli `id`, si è controllata la frase che le stava sopra: [S-044](Sources.md#s-044)
elenca fra le cause di un'elezione anche `rs.stepDown()`, e la pagina ne aveva concluso che «la
manutenzione ordinaria produce lo stesso tracciato nel log di un incidente». Misurato: è falso, e
si vede alla **prima riga**. `4615652` dice «since we've seen no PRIMARY in election timeout
period» ed è un guasto; `4615661` dice «due to step up request» ed è una manutenzione; `4615660`
dice «for a priority takeover» ed è la configurazione che lavora ([V-044](Sources.md#v-044)). La
conclusione era ragionevole e sbagliata, e sarebbe rimasta in pagina se il Task si fosse limitato a
incollare gli `id` che gli erano stati chiesti.

*Le due trappole nuove portano il sintomo per titolo, e una delle due ha una soglia che nessuno si
aspetta.* Voce 12: `mongod` non parte e dice che il keyfile è «too open». Il registro aveva il
messaggio dal Task 2; qui si è chiesto anche **dove passa la soglia**, e la risposta è che non è
«leggibile da tutti» ma «un bit qualsiasi acceso fuori dal proprietario»: `640` viene rifiutato
come `644`, e `401` — che non concede lettura a nessuno — viene rifiutato lo stesso
([V-041](Sources.md#v-041)). Voce 13: il driver riceve dalla topologia i nomi di servizio Compose e
fallisce con `getaddrinfo ENOTFOUND` su un host che chi ha scritto la stringa non ha mai nominato
([V-043](Sources.md#v-043)).

*La voce 13 dice anche quale rimedio non funziona.* Elencare tutti e tre gli indirizzi pubblicati è
la mossa che viene in mente per prima, ed è quella che peggiora le cose: una seed list con più host
spegne `directConnection` — terza delle quattro eccezioni di [S-045](Sources.md#s-045) — quindi il
driver scopre il replica set e butta via proprio gli indirizzi buoni. Una pagina di trappole che
elenca solo i rimedi che funzionano lascia il lettore a scoprire da solo quello che non funziona,
che è il tempo che gli si voleva risparmiare.

*Quello che si misura per strada si tiene, anche se nessuno l'aveva chiesto.* `rs.stepDown()`
cronometrato dà 8, 101 e 87 millisecondi ([V-042](Sources.md#v-042)): è il terzo termine di
paragone accanto ai ~10 000 ms di `docker kill` e ai ~500 di `shutdownServer()`
([V-029](Sources.md#v-029)), e completa la scala che il Task 8 aveva lasciata a due punti. Il
`mongo-rs-1` a priorità 2 si riprende il posto undici secondi dopo, il che rende la scena
autopulente e insieme fragile: chi la spiega con calma se la vede annullare a metà spiegazione.

**Conseguenze.** `docs/03-amministrazione/log.md` perde due riquadri di riserva e la §3.3 cambia
titolo; `docs/04-mongosh/guida-mongosh.md` perde la marcatura della §3.2 e ne corregge il testo;
`docs/02-architetture/trappole-mongodb-in-docker.md` passa da undici a tredici voci e la sua
premessa smette di promettere le trappole del replica set al futuro. Il debito documentale del
Task 2 è chiuso: la misura del keyfile ha finalmente una voce in [`Sources.md`](Sources.md).
[S-045](Sources.md#s-045) acquisisce il terzo ADR che la cita, [V-029](Sources.md#v-029) e
[V-030](Sources.md#v-030) il terzo. [S-044](Sources.md#s-044) resta dov'era: la sua affermazione non è stata smentita, è stata smentita l'inferenza che questo repository ne aveva tratto.

Resta aperto quello che è marcato: `rs.add()`/`rs.remove()` nella forma che riesce, tutta la §3.3
sullo sharded cluster, e le trappole dei config server e del bilanciamento che
[ADR-0033](#adr-0033) intesta a `feature/03`.

**Alternative scartate:** togliere le marcature senza eseguire, perché adesso il replica set esiste
— avrebbe lasciato in pagina le due frasi sbagliate, e sono esattamente le due che un lettore
avrebbe copiato; eseguire e correggere **in silenzio**, riscrivendo la frase giusta senza dire che
c'era quella sbagliata — costa una riga in meno e toglie al lettore l'unica cosa che gli insegna a
diffidare, cioè che una guida può contraddirsi in due sezioni distanti quaranta righe; scrivere le
due trappole nuove dal registro, che il messaggio del keyfile ce l'aveva già — non sarebbe emersa
la soglia, che è la parte che non si indovina; riconfigurare il replica set con nomi risolvibili da
fuori per mostrare la terza via d'uscita della voce 13 — cambierebbe in modo permanente lo stack
del talk, e la via d'uscita si può descrivere senza prenderla.

**Fonti:** [S-045](Sources.md#s-045), [V-029](Sources.md#v-029), [V-030](Sources.md#v-030), [V-041](Sources.md#v-041), [V-042](Sources.md#v-042), [V-043](Sources.md#v-043), [V-044](Sources.md#v-044)

---

<a id="adr-0050"></a>
## ADR-0050 — Le registrazioni di riserva si producono con quello che c'è, e il formato è testo

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto.** [ADR-0016](#adr-0016) stabilisce che i filmati di riserva stanno sul canale YouTube
del relatore **con copia locale obbligatoria**, perché «la connettività in sala non è garantita, e
un piano B che richiede rete non è un piano B». `tools/preflight.sh` lo verifica: cerca file `.mp4`
in `${DEMO_VIDEOS_DIR:-~/SqlStart2026-registrazioni}`, oggi come avviso e dal 18 settembre 2026 come
errore bloccante.

Il Task 13 di `feature/02` chiede le prime registrazioni, e le chiede adesso perché la scena del
failover è la prima che valga la pena filmare: è la prima che possa fallire in modo interessante.

Qui però si incontrano due cose diverse che il piano nomina insieme. Un **filmato** mostra lo
schermo e porta la voce di chi parla: lo gira il relatore, e nessun altro può girarlo al posto suo.
Una **registrazione di terminale** è il tracciato di ciò che il terminale ha fatto, con i tempi: si
produce eseguendo. L'indice di [`docs/README.md`](README.md) le distingueva già — «indice dei
filmati di riserva **e delle registrazioni di terminale**» — senza che nessuna decisione dicesse
come si fanno le seconde.

**Decisione.**

*Le registrazioni di terminale si producono adesso; i filmati restano dovuti al relatore.* Quattro
scene sono registrate ed entrano nel repository: la prova completa dello stack, i due failover, la
maggioranza persa ([V-045](Sources.md#v-045)). I `.mp4` non sono stati prodotti e **non sono stati
sostituiti da un segnaposto**: `make preflight` continua ad avvisare, ed è giusto che avvisi, perché
il controllo verifica una cosa che davvero manca. Mettere un file `.mp4` finto in cartella per far
tacere il controllo trasformerebbe la mattina del talk in una brutta sorpresa, che è esattamente lo
scenario che quel controllo esiste per evitare.

*Il formato è asciinema v2, e lo strumento è nel repository.* Il formato è JSON su righe: si legge
con `cat`, si cerca con `grep`, si confronta con `diff`, e quattro scene pesano tredici kilobyte
contro le decine di megabyte dei filmati equivalenti — il che le mette dentro il repository invece
che accanto, senza le cautele di [S-021](Sources.md#s-021). Lo strumento è
[`tools/registra-terminale.py`](../tools/registra-terminale.py), centosettanta righe di libreria
standard, e non `asciinema` installato con un gestore di pacchetti: lo stesso ragionamento di
ADR-0016 applicato un livello più in basso. Una registrazione di riserva che per essere **prodotta**
o **vista** richiede di installare qualcosa non è una registrazione di riserva, e per questo lo
strumento sa anche riprodurre — `--riproduci`, che rispetta i tempi originali, perché in queste
scene i tempi *sono* il contenuto.

*Il comando gira dentro uno pseudo-terminale.* In una pipe i programmi smettono di colorare
l'output, e la scena registrata non sarebbe quella che il pubblico vede. Costa venti righe di
`pty`, e senza di esse le registrazioni mostrerebbero un terminale che non esiste.

*I tempi registrati non diventano la misura di riferimento.* Le quattro scene portano numeri veri —
8617 ms, 1039 ms, 8634 ms — ma sono **una** esecuzione ciascuna, girata di seguito su una macchina
che aveva appena fatto le altre. Le misure del branch restano quelle di [V-029](Sources.md#v-029) e
[V-031](Sources.md#v-031), con le loro mediane e i loro giri ripetuti. La registrazione mostra una
scena, non la certifica.

**Conseguenze.** Nasce `docs/05-talk/registrazioni/` con il proprio indice, quattro file `.cast` e
la procedura per rifarli. `tools/registra-terminale.py` entra nel repository. L'indice di
[`docs/README.md`](README.md) smette di promettere quella cartella a `feature/02` e la collega.
`make preflight` resta con un avviso, e il criterio 8 di completamento del branch — «almeno una
registrazione di riserva esiste in locale e `make preflight` non avvisa più» — è **soddisfatto a
metà e dichiarato tale**: le registrazioni esistono, l'avviso no. Chiuderlo tocca al relatore, e la
procedura per farlo è scritta nell'indice.

Una misura è caduta fuori dall'intervallo di [V-029](Sources.md#v-029) — 1039 ms contro un massimo
osservato di 574 — e non ha prodotto una correzione, perché conferma la riserva che V-029 aveva già
scritto: il singolo numero è instabile, il rapporto fra le due scene no.

**Alternative scartate:** girare un `.mp4` sintetico rendendo il tracciato in fotogrammi con
`ffmpeg` — è producibile e sarebbe passato il controllo di `preflight`, ma sarebbe un filmato che
nessun essere umano ha visto mentre accadeva, e chiuderebbe l'avviso senza chiudere il debito;
installare `asciinema` come dipendenza — un pacchetto in più fra la mattina del talk e il piano B, e
il formato lo si scrive in cinquanta righe; mettere le registrazioni fuori dal repository, accanto
ai filmati — tredici kilobyte di testo versionabile non hanno ragione di stare dove non si vedono
nei diff; rimandare tutto il Task 13 al relatore — l'indice, la procedura e le scene di terminale si
possono fare adesso, e farle adesso è ciò che rende il resto un gesto di venti minuti invece che una
serata.

**Fonti:** [S-021](Sources.md#s-021), [V-029](Sources.md#v-029), [V-045](Sources.md#v-045)

---

<a id="adr-0051"></a>
## ADR-0051 — Il primario del lab si sa in anticipo: priorità 2/1/1, e lo si dice al pubblico

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto:** i tre membri di `rs0` sono identici — stessa immagine, stessa configurazione, stessi
limiti di memoria e di CPU. Su un set così, chi diventa primario alla prima elezione lo decide
l'ordine con cui i nodi si vedono, che dipende da quanto ci mettono a partire: cambia da un avvio
all'altro e nessuno lo controlla. `10-rs-initiate.js` scrive invece `priority: 2` sul primo membro e
`1` sugli altri due, e la scelta va giustificata perché la simmetria sarebbe la cosa ovvia.

La ragione è di scena prima che tecnica. Le demo del talk nominano un container: `make failover-02`
uccide **il primario**, la pagina del replica set stampa porte e ruoli, lo smoke verifica chi
scrive. Se il primario cambiasse a ogni avvio, ogni comando andrebbe preceduto da «vediamo prima chi
è» — venti secondi buttati per ciascuna delle tre scene, davanti a un pubblico che non impara
niente da quell'attesa. Con la priorità, `mongo-rs-1` è primario e si può dire in anticipo, il che
rende anche la registrazione di riserva sovrapponibile alla demo dal vivo.

[S-065](Sources.md#s-065) documenta il meccanismo: la priorità «affect both the timing and the
outcome of elections for primary», i valori vanno da `0` a `1000`, il predefinito è `1`, e con `0`
un membro non si candida mai. Due sono quindi le forme possibili di questa decisione: alzare il
primo a 2, oppure azzerare gli altri due.

**Decisione:** priorità **2** su `mongo-rs-1`, **1** su `mongo-rs-2` e `mongo-rs-3`, scritte
nell'`rs.initiate()` e non modificate a caldo. Tre conseguenze si accettano insieme alla scelta:

1. **Il primario è prevedibile all'avvio**, e `docs/02-architetture/replica-set.md` può nominarlo.
2. **Il nodo fermato si riprende il ruolo quando torna.** Non è un effetto collaterale da subire: è
   una seconda elezione, misurata — undici secondi dopo uno `rs.stepDown(10)`
   ([V-042](Sources.md#v-042)) — e va **detta al pubblico**, perché una scena che si rimette a posto
   da sé mentre la si spiega sembra magia o sembra un errore, e non è né l'una né l'altra.
3. **Le altre due restano a 1 e non a 0.** Un membro a priorità 0 non può diventare primario mai: il
   set perderebbe la capacità di sopravvivere alla caduta di `mongo-rs-1`, che è precisamente la
   scena che il talk mostra.

Le priorità si scrivono all'inizializzazione e non si toccano dopo. S-065 avverte che cambiarle a
caldo «can force the current primary to step down» chiudendo tutte le connessioni aperte, per 10–20
secondi: sullo stack acceso durante una demo è un gesto da non fare.

**Conseguenze:** ogni misura del branch è stata presa su un set 2/1/1 e lo dichiara nel proprio
ambiente; chi la rifà su un set simmetrico può trovare tempi diversi nella scena del rientro, non in
quella della caduta. Il ritorno automatico del primario rende la scena del failover **autopulente**
— dopo un minuto lo stack è com'era — e per la stessa ragione fragile da spiegare con calma: se chi
parla si dilunga, la dimostrazione si annulla mentre la si commenta. È il motivo per cui
`tools/failover-replicaset.sh` cronometra invece di lasciar guardare
([ADR-0044](#adr-0044)).

Terza conseguenza, sulla scena della maggioranza persa: `reset-demo.sh 02` non si limita a rialzare
i container fermati, **aspetta che le priorità si siano riassestate** prima di dichiarare lo stack
pronto, altrimenti la prova successiva parte con un primario diverso da quello che dice di
aspettarsi ([V-031](Sources.md#v-031)).

**Alternative scartate:** priorità tutte a 1 (è il caso generale, ed è quello che un lettore
troverà in produzione — ma rende ogni demo condizionata a un'ispezione preliminare, e la scena del
rientro sparisce); priorità 0 sui due secondari (il primario sarebbe fisso davvero, e il set non
tollererebbe più la caduta che il talk mostra); priorità decrescenti 3/2/1 (renderebbe prevedibile
anche il **successore**, che è informazione utile una volta sola e costa una terza asimmetria da
spiegare); decidere il primario dopo l'avvio con un `rs.stepDown()` mirato (un comando in più nella
catena, che fa a caldo ciò che l'inizializzazione fa gratis).

**Fonti:** [S-065](Sources.md#s-065), [V-029](Sources.md#v-029), [V-031](Sources.md#v-031), [V-042](Sources.md#v-042)

---

<a id="adr-0052"></a>
## ADR-0052 — Una trappola già misurata si scrive nel branch che l'ha misurata

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto:** [ADR-0033](#adr-0033) stabilisce che la pagina delle trappole cresce **per aggiunta**
e che i branch successivi ne mettono in coda di nuove. Non dice **quando**, e la differenza è
emersa al Task 12. Il piano di `feature/02` prometteva due trappole — i permessi del keyfile e la
scoperta della topologia — e sono state scritte. I punti di ripresa dei Task 9 e 10, redatti dopo il
piano, avevano però accumulato un inventario più lungo: quattro fenomeni incontrati lungo la strada,
tutti già misurati, nessuno ancora in pagina.

- `--env-file` **sostituisce** il `.env` invece di aggiungersi ([V-025](Sources.md#v-025),
  [S-056](Sources.md#s-056));
- `up --wait` esce con successo mentre il replica set non esiste ancora
  ([V-025](Sources.md#v-025), [S-057](Sources.md#s-057));
- il `$` di un comando `sh -c` viene consumato da Compose e non arriva alla shell
  ([S-064](Sources.md#s-064), misurato al Task 14 in [V-046](Sources.md#v-046));
- `docker logs` si congela quando il demone Docker riparte, e tace invece di dare errore
  ([V-032](Sources.md#v-032)).

A questi il registro ne aggiungeva un quinto, di natura diversa: `ENOTFOUND` al posto di un errore
di selezione del server, perché un container fermo sparisce dal DNS della rete Compose
([V-031](Sources.md#v-031)). È un artefatto dei container, non di MongoDB, e la voce 13 della pagina
lo aveva già dato per scritto — vi si legge «fra le tre che danno `ENOTFOUND`» quando le voci
esistenti erano due.

Il Task 12 le ha lasciate aperte e ha scritto perché: la lista del piano è un contratto, quella dei
punti di ripresa è un inventario cresciuto misura dopo misura, e mescolarle di nascosto avrebbe
tolto la differenza. Il Product Owner ha deciso di chiuderle qui, in coda al Task 14, invece di
rimandarle a `feature/03`.

**Decisione:** una trappola **già misurata** si scrive nel branch che l'ha misurata, anche quando il
piano di quel branch non la nominava. Il criterio è la misura, non il piano: se esiste una voce in
[`Sources.md`](Sources.md) che documenta il fenomeno, la trappola è già scritta per tre quarti e
rimandarla costa più che farla.

`feature/02` porta quindi la pagina da 13 a **18 voci**, aggiungendo in coda — nell'ordine —
`--env-file`, `up --wait`, il dollaro di Compose, il congelamento di `docker logs` e il terzo
`ENOTFOUND`. La numerazione esistente non si tocca, come prescrive ADR-0033.

**Conseguenze:** il debito dichiarato nel registro al Task 12 è saldato dentro lo stesso branch, e
il punto di ripresa che lo nominava non sopravvive alla feature — che è la forma in cui un debito
dovrebbe finire. Tre delle cinque voci nuove non parlano di MongoDB affatto: sono trappole di
Compose e del runtime, e stanno in una pagina intitolata «MongoDB in Docker» perché è lì che le
incontra chi monta uno stack MongoDB. La pagina cambia leggermente natura, e la riga d'apertura lo
dice.

Il criterio ha un limite che conviene enunciare adesso, prima che qualcuno lo scopra applicandolo:
vale per le trappole **misurate**, non per quelle previste. Un fenomeno letto in una fonte e mai
riprodotto qui resta fuori, perché la pagina promette il sintomo così come si è visto e non come
dovrebbe presentarsi ([ADR-0024](#adr-0024)).

**Alternative scartate:** rimandare tutto a `feature/03`, che alla pagina deve comunque tornare (la
trascrizione sarebbe costata uguale, e nel frattempo la voce 13 avrebbe continuato a rimandare a una
voce inesistente); scrivere solo il terzo `ENOTFOUND`, cioè l'unica delle cinque che la pagina già
promettesse (chiuderebbe l'incoerenza e lascerebbe l'inventario aperto, che è il modo in cui le
liste di candidati muoiono); allargare invece il piano del Task 12 a posteriori (il piano non si
riscrive quando l'esecuzione devia — la deviazione si spiega nel registro, ed è quello che è stato
fatto).

**Fonti:** [S-056](Sources.md#s-056), [S-057](Sources.md#s-057), [S-064](Sources.md#s-064), [V-025](Sources.md#v-025), [V-031](Sources.md#v-031), [V-032](Sources.md#v-032), [V-046](Sources.md#v-046)


---

<a id="adr-0053"></a>
## ADR-0053 — Uno strumento che sbaglia lo dice con il codice della shell, e non scrive Python dentro una registrazione

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto:** `tools/registra-terminale.py` produce la riserva del talk
([ADR-0050](#adr-0050)): quattro registrazioni di terminale che si guardano il giorno in cui la
demo dal vivo non parte. Il programma fa `fork`, apre uno pseudo-terminale e chiama `os.execvpe`
nel figlio. Aveva un solo controllo preventivo — se il comando non esiste, esci 127 senza scrivere
niente — nato dalla prima regressione, quella in cui `argparse.REMAINDER` mangiava `--titolo`.

Una review esterna sulla PR #3 ha segnalato che `os.execvpe` non è protetta. Eseguendo il caso
([V-048](Sources.md#v-048)) il difetto si è rivelato più largo del rilievo: un file che **esiste**
ma non è eseguibile attraversa il controllo preventivo, `execvpe` fallisce quando lo pseudo-terminale
è già aperto, e il traceback di Python finisce **dentro il `.cast`**, percorsi assoluti della
macchina di chi registra compresi. Il file resta su disco e sembra una registrazione buona; il
programma esce con `1`.

La stessa misura ha mostrato che la shell questi due casi li distingue da sempre: `127` quando il
comando non c'è, `126` quando c'è e non si esegue — identico in `sh` e in `bash`, e `126` anche per
una directory.

**Decisione:** gli strumenti di questo repository riportano i due casi con i **codici della shell**,
127 per «non trovato» e 126 per «trovato e non eseguibile», e **nessun traceback di Python può
entrare in una registrazione**.

In concreto, in `registra-terminale.py`: il controllo preventivo verifica anche `os.access(…,
os.X_OK)` e restituisce 126 con un messaggio proprio; la `os.execvpe` nel figlio è racchiusa in un
`try`, e in caso di `OSError` il figlio scrive **una riga** con `os.write(2, …)` — non `print`, che
dopo `fork` ha un buffering su cui non si deve contare — ed esce con `os._exit(126)`.

Nella stessa correzione entrano altri due difetti trovati dalla stessa review e verificati
eseguendoli: `--velocita 0` sollevava `ZeroDivisionError` dentro `riproduci()`, cioè un traceback
al posto della riserva nel momento peggiore possibile, e ora è un errore di `argparse` (uscita 2);
e `--riproduci` veniva cercato in **tutta** la riga di comando, quindi un comando da registrare che
avesse per conto suo un'opzione con quel nome non si riusciva a registrare — `argparse` rispondeva
«unrecognized arguments», incolpando l'utente. La ricerca ora guarda solo la parte **prima** di
`--`. È l'immagine speculare della regressione originale: là erano le opzioni del programma a
colare nel comando, qui era un'opzione del comando a essere letta come propria, e la divisione su
`--` deve valere nei due versi.

**Conseguenze:** cinque casi nuovi in `tools/tests/test_registra_terminale.py`, che passa da 8 a
13. Uno dei cinque — `--riproduci` insieme a un comando dopo `--` si rifiuta invece di ignorarlo —
passava già prima della correzione: è lì per **conservare** un comportamento che la riscrittura
poteva far degradare in un silenzioso «ignoro quello che hai scritto», ed è il tipo di test che si
scrive solo mentre si tocca quel codice.

Il criterio dei due codici vale per tutti gli strumenti, non solo per questo: è una convenzione che
costa una riga e che chi legge un'uscita non nulla in un `make` conosce già. Non è stata estesa a
`smoke-replicaset.sh` e agli altri script di palco perché nessuno di loro esegue programmi
arbitrari scelti da chi digita — se lo faranno, la regola c'è.

**Alternative scartate:** lasciare la `execvpe` nuda e affidarsi al controllo preventivo (è la
situazione di partenza; un controllo preventivo non può coprire tutti i modi di fallire di `exec`,
e la directory lo dimostra — per il sistema è attraversabile, quindi `os.access` risponde di sì);
usare un solo codice, 127, per tutti gli errori di avvio (semplice, e cancella la distinzione che
serve a chi deve riparare: nome sbagliato e permesso mancante si aggiustano in due modi diversi);
cancellare il `.cast` quando il comando fallisce (sbagliato in generale — [ADR-0050](#adr-0050) e
il test già esistente vogliono che una demo *fallita* resti registrata: il problema non era il file,
era il traceback dentro); validare `--velocita` con un `type=` di `argparse` invece che con un
controllo esplicito (equivalente nell'effetto, meno leggibile nel messaggio d'errore).

**Fonti:** [V-048](Sources.md#v-048)


---

<a id="adr-0054"></a>
## ADR-0054 — La password del lab sta sulla riga di comando dell'host, e il commento lo dice

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto:** `tools/smoke-replicaset.sh` conteneva un commento che prometteva una cautela — «la
password passa per `-e` e non sulla riga di comando di mongosh: dentro il container resta comunque
leggibile in `ps`, ma è una password di lab… La riga esiste per non prendere l'abitudine, non per
illusione di segretezza» — e sotto, una chiamata che passava `--password "${PASSWORD}"` a `mongosh`
**e** un `-e SEGRETO="${PASSWORD}"` in più. Una review esterna sulla PR #3 ha notato che il testo e
il codice non dicono la stessa cosa.

La misura ([V-047](Sources.md#v-047)) ha ribaltato tutte e tre le affermazioni del commento.
`mongosh` 2.10.0 **riscrive il proprio `argv`**: nella tabella dei processi del container la
password in chiaro compare **zero** volte, e si legge `mongodb://<credentials>@127.0.0.1:27017/…`.
Dove resta in chiaro è **sull'host**, nella riga di comando del client `docker`, che nessuno
riscrive. E il `-e SEGRETO=` non solo non veniva letto da nessun comando — `grep` ne trovava la
sola definizione — ma metteva una **seconda** copia della password proprio su quella riga: il
gesto presentato come cautela peggiorava, di una misura contabile, la cosa che diceva di curare.

**Decisione:** la password del laboratorio passa a `mongosh` con `--password`, senza intermediari,
e il commento che l'accompagna descrive **l'esposizione vera**: sull'host, nell'`argv` del client
Docker. Il `-e SEGRETO=` è rimosso. Nessun codice di questo repository esiste per «dare l'esempio»
o «non prendere l'abitudine» senza fare nulla: o protegge qualcosa di misurabile, o non c'è.

Ciò che protegge davvero resta scritto, perché è quello che il pubblico deve portarsi via: è una
password di laboratorio, e il file che la porta sta fuori dal repository
([ADR-0014](#adr-0014)) — non un accorgimento sulla riga di comando.

**Conseguenze:** `smoke-replicaset.sh` si allinea a `failover-replicaset.sh` e `reset-demo.sh`, che
`--password` lo passavano già senza decorazioni; i 42 controlli dello smoke restano verdi contro lo
stack avviato. Sul palco la faccenda diventa dicibile in una frase, ed è più interessante di quella
che si sarebbe detta prima: lo strumento che maneggia il segreto si protegge, quello che lo lancia
no — e il secondo è quello che gira sulla macchina condivisa.

Il criterio generale che questa decisione fissa è più largo del caso: **un commento che promette
una protezione inesistente è un difetto di sicurezza, non di stile**. Chi legge smette di cercare,
ed è esattamente l'effetto che ha avuto qui per sette commit. Si corregge misurando, non
riscrivendo la frase a intuito — l'intuito, in questo caso, avrebbe scritto «tanto in `ps` si vede
lo stesso», che è falso nel container e vero sull'host, cioè sbagliato due volte.

**Alternative scartate:** far leggere davvero la variabile, con `sh -c 'mongosh --password
"$SEGRETO"'` (non nasconde niente: la shell la espande costruendo l'`argv` di `mongosh`, e la
password torna dove era — in più resta sulla riga di `docker`, che è quella che espone); togliere
la password dagli argomenti passando per un file dentro il container (`mongosh` 2.10.0 non offre
questa strada, e montare un file di segreti per un lab di sessanta minuti costa più di quanto
renda); lasciare il commento e togliere solo il codice morto (il commento era la parte dannosa:
quella che faceva smettere di guardare); toglierli entrambi senza scrivere niente al loro posto (la
riga senza spiegazione invita il prossimo lettore a «sistemarla» rimettendo un `-e`).

**Fonti:** [V-047](Sources.md#v-047)


---

<a id="adr-0055"></a>
## ADR-0055 — Il codice di uscita si conserva dove viene raccolto, e un rilievo che macOS nasconde si prova su Linux

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto:** chiuso il primo giro di review sulla PR #3 ([ADR-0053](#adr-0053),
[ADR-0054](#adr-0054)), ne è stato chiesto un secondo a un revisore diverso. Ha prodotto **un solo
rilievo**, sullo stesso file dei tre precedenti e in un punto che nessuno dei tre aveva guardato.

Il ciclo di cattura di `registra-terminale.py` ha due uscite. La prima è il pty che si chiude: si
esce dal ciclo e la `waitpid` finale raccoglie il comando e ne legge lo stato. La seconda serve al
caso in cui il comando finisce **senza** chiudere il pty, perché ha lasciato dietro di sé un
discendente che lo tiene aperto: lì un `os.waitpid(pid, os.WNOHANG)` accorgeva che era finito, e
buttava via lo stato in un `_`. Il processo però a quel punto era già raccolto: la `waitpid` finale
sollevava `ChildProcessError`, il ripiego `stato = 0` entrava in funzione, e lo strumento riportava
**successo** qualunque cosa fosse successo. Contraddice per intero la promessa scritta nel suo
docstring — «restituisce il codice di uscita del comando: una registrazione di una demo fallita è
ancora una registrazione, ma chi la produce deve saperlo subito» — e il test che quella promessa la
verifica esisteva già, senza accorgersi di niente.

Il rilievo arrivava con un caso di prova, e chi lo aveva scritto **non era riuscito a eseguirlo**.
Su questa macchina il caso non si riproduce: tre costruzioni diverse riportano tutte `7`
correttamente, in meno di un decimo di secondo ([V-049](Sources.md#v-049)). Non è fortuna, è BSD —
quando muore il processo di controllo, macOS **revoca** il terminale di controllo, e il pty si
chiude anche se un discendente ne tiene un descrittore. Il ramo difettoso, su macOS, non si
raggiunge.

Dentro un container Linux lo stesso comando riporta **0** invece di `7`, e ci mette 0,25 secondi —
il timeout di `select` più il giro non bloccante, cioè la firma esatta di quel ramo.

**Decisione:** lo stato del processo si conserva **dove viene raccolto**. Il ramo non bloccante
salva quello che `waitpid` gli restituisce in una variabile, e la `waitpid` finale si esegue solo
se quella variabile è ancora vuota. Il ripiego a `0` resta, ma da qui in avanti copre solo il caso
per cui esiste — un processo raccolto da qualcun altro — e non più il caso normale.

**Conseguenze:** un test in più, il quattordicesimo del file, scritto in modo da passare su macOS per
l'altra strada e da provare davvero il ramo corretto su Linux, dove prima della correzione
falliva. La suite passa 14 su 14 su tutte e due le piattaforme.

Il criterio generale, che vale oltre questo file: **un rilievo che non si riproduce sulla macchina
di sviluppo non è ancora smentito.** Si prova su Linux, in un container qualsiasi, prima di
respingerlo. Costa un `docker run` e una decina di righe, e qui era la differenza fra correggere un
difetto e archiviarlo come falso positivo con tre prove a sostegno — tutte e tre eseguite, tutte e
tre verdi, tutte e tre sulla piattaforma sbagliata. È il rovescio esatto del criterio del primo
giro: là eseguire bastava a smentire un rilievo inventato ([ADR-0053](#adr-0053)), qui eseguire
**sulla sola macchina di sviluppo** avrebbe confermato un difetto come inesistente. La regola
completa è quindi: si esegue, e quando l'esito dipende dal sistema operativo si esegue due volte.

Il laboratorio è distribuito a un pubblico che lo eseguirà su Linux e su WSL2 almeno quanto su
macOS ([ADR-0001](#adr-0001)); un difetto invisibile qui è visibile a loro, ed è l'unico tipo di
difetto che chi scrive non può trovare rileggendo.

**Alternative scartate:** togliere del tutto il ramo non bloccante e affidarsi alla chiusura del pty
(su macOS funzionerebbe, ed è esattamente il ragionamento che ha prodotto il difetto: su Linux il
ciclo resterebbe appeso finché il discendente non finisce, e il commento che quel ramo lo spiega
descrive un caso reale); chiamare `waitpid` con `WNOWAIT` per sbirciare lo stato senza raccogliere
il processo (funziona, ma lascia uno zombie fino alla `waitpid` finale e sposta la complessità
invece di toglierla); respingere il rilievo perché il caso di prova proposto non si riproduce
(sarebbe stato difendibile con tre esecuzioni a sostegno, ed è l'errore che questa decisione esiste
per non ripetere).

**Fonti:** [V-049](Sources.md#v-049)


---

<a id="adr-0056"></a>
## ADR-0056 — Prima di rimuovere un worktree si guarda dentro, e il file che conta vive nel checkout principale

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto:** il lavoro su questo repository si svolge in worktree separati, uno per branch, che
alla chiusura della PR vengono rimossi. La domanda «posso rimuoverlo?» ha una risposta ovvia e una
nascosta. Quella ovvia riguarda il lavoro versionato, e si verifica in due comandi: nessuna
modifica in sospeso, e la punta del ramo già dentro `develop`. Quella nascosta riguarda i file che
git ha ricevuto istruzione di non guardare.

In questo repository quella categoria non contiene solo cache. `docker/02-replicaset/.env` è
ignorato **per decisione** ([ADR-0014](#adr-0014) e la riga di `.gitignore` che ne discende):
contiene la password dell'amministratore del laboratorio, e non deve entrare nella cronologia. Il
prezzo di quella scelta, che fino a oggi non era stato scritto, è che quel file esiste in una copia
sola, dove è stato creato.

La misura ([V-050](Sources.md#v-050)) dice due cose. La prima: `git worktree remove` si rifiuta di
cancellare un worktree che contiene file non tracciati — `fatal: … contains modified or untracked
files` — ma cancella senza obiettare uno che contiene solo file ignorati, uscita `0` e nessun
messaggio. La rete di sicurezza c'è, e non copre questa categoria. La seconda: il controllo non si
può fare da fuori. Git non attraversa il confine di un altro repository, nemmeno con l'opzione che
esiste apposta per scendere nelle directory; da fuori il worktree è una riga sola.

**Decisione:** prima di ogni `git worktree remove`, si elencano i file ignorati **dall'interno del
worktree**, e si mette in salvo ciò che non si rigenera:

```
git -C <worktree> status --porcelain --ignored -uall \
  | grep -v -e '/\.venv/' -e '__pycache__' -e '\.pytest_cache'
```

Il filtro toglie ciò che si ricostruisce da solo e lascia in vista il resto. Quello che resta si
guarda a una a una: se una riga non si rigenera con un comando, si copia prima di rimuovere.

E, come conseguenza diretta: **la sede dei file `.env` del laboratorio è il checkout principale**,
non un worktree. Un worktree è per costruzione temporaneo; un file che vive solo lì è un file che
si perde a fine branch, e il momento in cui te ne accorgi è quello in cui uno stack non parte più.

**Conseguenze:** un comando in più nella chiusura di ogni branch, e l'abitudine di leggerne
l'uscita invece di scorrerla. In cambio, i worktree tornano a essere quello che devono essere —
usa e getta — perché la condizione che li rende tali è ora esplicita invece che sperata.

Alla chiusura di `feature/02` questa regola ha avuto la sua prima applicazione e ha trovato subito
il caso per cui esiste: il `.env` del replica set era nel worktree e **non** nel checkout
principale. Copiato prima della rimozione, lo stack 02 riparte senza reinizializzare
l'amministratore nei volumi; perso, si sarebbe fermato sull'errore esplicito di
`${PASSWORD_AMMINISTRATORE:?…}` — che è il comportamento voluto, ma a quel punto la password
andava scelta di nuovo e i volumi ricreati.

**Alternative scartate:** fidarsi di `git worktree remove`, che per i file non tracciati basta e
avanza (misurato: sugli ignorati non dice niente, ed è esattamente la categoria in cui cade il
`.env`); eseguire il controllo dal checkout principale, che è il posto naturale da cui si rimuove
un worktree (misurato: git si ferma al confine di repository e riporta la sola directory, quindi il
controllo non è impreciso, è cieco); togliere `.env` dal `.gitignore` così che git lo protegga come
file tracciato (metterebbe la password nella cronologia, che è precisamente ciò che
[ADR-0014](#adr-0014) vieta); usare `git clean -ndX` per l'elenco (funziona ed è più corto, ma
elenca solo gli ignorati e non i non tracciati, e vive a un solo carattere di distanza da
`-fdX`, che cancella — un comando di verifica non dovrebbe avere quella forma).

**Fonti:** [V-050](Sources.md#v-050)


---

<a id="adr-0057"></a>
## ADR-0057 — Lo sharded cluster comincia adesso, con i due giorni che `feature/02` ha restituito

**Data:** 2026-09-01 · **Stato:** Accettata — modifica il calendario del
[design](00-progetto/2026-08-24-design.md)

**Contesto:** il calendario del design assegna a `feature/02-stack-replicaset` il periodo dal 31
agosto al 3 settembre, poi `feature/04-app-python` dal 4 all'11 con la PR #4, e
`feature/03-stack-sharded` il 14 e il 15 con la PR #5. L'ordine non è casuale e il design lo
motiva: «`feature/04` precede `feature/03` perché è il pezzo più grande e meno comprimibile».

`feature/02` è stata unita il **1º settembre**, due giorni prima della sua scadenza. Il calendario
non prevede che cosa farne: prevede un ordine, non un modo di spendere l'anticipo. Il Product
Owner ha deciso di spenderlo aprendo `feature/03`.

La scelta ha due ragioni che il calendario non contraddice. La prima è di dimensione: allo sharded
sono assegnati due giorni, ed è quindi l'unico branch che entra per intero nella finestra
guadagnata. La seconda è di preparazione: lo spike del 25 agosto ha già montato la topologia
completa e l'ha misurata, e il file Compose che ha funzionato è dentro il verbale — è il branch che
parte più vicino all'arrivo, non quello che parte da zero.

**Decisione:** `feature/03-stack-sharded` si apre il 1º settembre e occupa il 2 e il 3, cioè i
giorni restituiti da `feature/02`. **`feature/04-app-python` conserva la sua data di inizio, il 4
settembre.** Se al 3 settembre lo sharded non è chiuso, non si sfora: si sospende scrivendo il
punto di ripresa, e il lavoro riprende nella sua finestra originale del 14–15 settembre. Il 14 e il
15 restano assegnati allo sharded finché non è chiuso; se si chiude prima, diventano margine prima
della `release/1.0` del 16.

**Conseguenze:** il ragionamento del design è preservato, perché ciò che protegge non è l'ordine in
sé ma la data di inizio di `feature/04` — il pezzo grande e incomprimibile mantiene la sua finestra
intera. Cambia soltanto che cosa succede nei due giorni che prima erano coda di `feature/02`.

Il calendario del design **non viene riscritto**: questo ADR lo modifica, come ogni altra decisione
di questo repository, per aggiunta e per rimando. Chi legge il design trova l'ordine originale e
la sua motivazione, che restano validi; chi legge qui trova che cosa è successo dopo e perché.

C'è un rischio, e conviene scriverlo invece di scoprirlo: aprire un branch «perché c'è tempo» è il
modo classico di trasformare due giorni di margine in due giorni di debito, se il branch non si
chiude. La clausola di sospensione sopra è la difesa, ed è vincolante: al 3 settembre si guarda
l'orologio, non lo stato d'animo.

**Alternative scartate:** rispettare l'ordine e restare fermi due giorni, che sarebbe stato
difendibile ma butta via il margine invece di investirlo; anticipare `feature/04` al 2 settembre,
che avrebbe usato l'anticipo sul pezzo grande — scartata perché l'applicazione ha bisogno di
giorni consecutivi e pieni, e due giorni intestati a un branch di due settimane non lo accorciano,
lo frammentano; iniziare lo sharded senza scrivere niente, lasciando che il ramo aperto raccontasse
da solo la deviazione dal calendario, che è la forma peggiore perché lascia in piedi due verità in
conflitto — un documento che dice una cosa e un repository che ne fa un'altra.

**Fonti:** nessuna (decisione organizzativa)


---

<a id="adr-0058"></a>
## ADR-0058 — La 8.0.30 non c'è: il lab resta su 7.0.40 e il controllo si ripete a data fissa

**Data:** 2026-09-01 · **Stato:** Accettata — attua [ADR-0028](#adr-0028)

**Contesto:** [ADR-0028](#adr-0028) adotta MongoDB 7.0.40 «con la 8.0.30 come traguardo», e la sua
clausola è condizionale: si ripinna **appena i binari escono**. Una clausola così non ha un
esecutore: «appena» non è una data, e nessuno è incaricato di guardare. Il punto di ripresa di
`feature/03` l'aveva quindi messa come primo passo del branch, prima di montare il terzo stack —
perché montarlo su una versione e ripinnarlo subito dopo significherebbe rigirare le
registrazioni.

La verifica è stata fatta ([V-051](Sources.md#v-051)): al 1º settembre 2026 la **8.0.30 non
esiste** in nessuno dei canali che ADR-0028 aveva nominato. Su Docker Hub il filtro per nome esatto
restituisce zero risultati e l'ultima patch della linea 8.0 resta la 8.0.29; nel feed ufficiale dei
download le versioni correnti sono 8.3.8, 8.2.12, 8.0.29, 7.0.40, 6.0.29, 5.0.34 e 4.4.31. Nel
frattempo la 7.0.40 è ancora la punta della propria linea: la versione del lab non sta invecchiando
mentre la si usa.

**Decisione:** il lab resta su **7.0.40** e `feature/03` monta lo sharded cluster su quella
versione, senza aspettare e senza deviare. La clausola condizionale di ADR-0028 resta in piedi, ma
smette di essere condizionale e basta: il controllo si ripete **a due date fisse** — il 3
settembre, alla chiusura di `feature/03`, e il **16 settembre**, il giorno della `release/1.0`, che
è l'ultimo momento utile per ripinnare e rigirare le registrazioni prima del talk. Il comando è
scritto e sta in [V-051](Sources.md#v-051): due `curl`, meno di un minuto.

**Conseguenze:** il terzo stack si scrive con `${MONGO_IMAGE}` come gli altri due, quindi un
eventuale ripinnamento resta il cambio di una variabile e la rigenerazione di `tools/images.env`
con `make images-pull` — è la ragione per cui [ADR-0008](#adr-0008) teneva la versione fuori dai
file Compose, e continua a pagare.

Va detto dal palco, e adesso c'è il numero per dirlo: il muro della 8.x su Docker Desktop non è una
stranezza di agosto che nel frattempo è stata chiusa. A ventisette giorni dalla scoperta, e con
l'immagine ufficiale aggiornata il giorno prima della verifica, la patch che lo risolve non è
uscita. Chiunque in sala provi oggi MongoDB 8 su Docker Desktop incontra lo stesso errore, e non ha
una versione a cui aggiornarsi.

**Alternative scartate:** montare lo sharded sulla 8.2.12 per avere un «8» sulle slide, già
scartata da ADR-0028 per due ragioni che non sono cambiate — non riceve più patch e si avvia solo
perché precede il controllo; aspettare la 8.0.30 spostando `feature/03` più avanti, che
subordinerebbe il calendario a una data che non esiste; lasciare la clausola come stava, cioè
«appena escono», che in ventisette giorni non ha prodotto una sola verifica e non ne avrebbe
prodotta nessuna nemmeno adesso senza un punto di ripresa che la nominasse.

**Fonti:** [V-051](Sources.md#v-051)

---

<a id="adr-0059"></a>
## ADR-0059 — Lo stack 03 si scrive per esteso, e il file dello spike si traduce invece di essere copiato

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto:** lo spike del 25 agosto ha lasciato un file Compose che funziona, e il verbale dice
di riportarlo in `docker/03-sharded/` quando la feature parte. Quel file usa gli ancoraggi YAML:
`x-mongo: &mongo`, `x-sonda: &sonda`, e undici `<<: *mongo`. È una scelta ragionevole per un file
di prova — undici servizi quasi identici, duecento righe risparmiate.

Gli altri due stack del repository non li usano. Lo stack 02 scrive i suoi tre membri per esteso e
lo dichiara nel commento: «la ripetizione è deliberata». La motivazione viene da
[ADR-0003](#adr-0003), che ha scartato `include` e i frammenti condivisi perché la
fattorizzazione è «comoda per chi mantiene, ostile a chi legge una volta sola». Ma ADR-0003 parla
di file diversi, non di ancoraggi dentro un file, e lo stack 03 non è lo stack 02: sono nove
`mongod` e due `mongos`, non tre membri. Copiare il criterio senza verificarlo sarebbe stato
comodo in un verso e nell'altro.

Il punto che decide non è il conteggio delle righe, è **cosa insegna il file sul proiettore**. Lo
stack 03 esiste per mostrare che tre ruoli sono distinti: `--configsvr`, `--shardsvr`, e un
`mongos` che non è un `mongod`. Un file in cui gli undici servizi ereditano dallo stesso ancoraggio
mette in evidenza ciò che hanno in comune e nasconde in una riga di override ciò che li distingue —
cioè esattamente il contenuto del Blocco 3.

**Decisione.**

1. **Nessun ancoraggio YAML e nessun `extends` in `docker/03-sharded/compose.yaml`.** Ogni
   servizio è scritto per esteso, come nei due stack precedenti.
2. **Si ripete il codice, non i commenti.** Il primo servizio di ogni ruolo — `cfg1`, poi
   `shard1a`, poi `mongos` — porta la spiegazione completa; gli altri della stessa famiglia
   aprono con una riga che rimanda a lui e commentano solo ciò che cambia. È già la forma dello
   stack 02, dove i membri 2 e 3 dicono «identico a quello del membro 1: vedi lì il perché».
3. **Il file dello spike si traduce, non si copia.** Oltre agli ancoraggi cambia la sonda: lo
   spike usava `db.adminCommand('ping').ok`, che risponde anche a un `mongod` che non è entrato in
   nessun replica set. Lo stack 03 adotta la disgiunzione a tre termini dello stack 02, e
   [V-052](Sources.md#v-052) ha misurato perché serve il terzo — su un config server non ancora
   inizializzato `isWritablePrimary` e `secondary` sono entrambi falsi, e una sonda a due termini
   resterebbe rossa per sempre.
4. **Il file dichiara in testa ciò che non contiene ancora.** Finché shard e `mongos` non ci sono,
   l'intestazione lo dice: chi apre il file a metà branch non deve scoprirlo avviandolo
   ([ADR-0037](#adr-0037)).

**Conseguenze:** il file sarà lungo — dell'ordine delle novecento righe a stack completo — ed è il
prezzo consapevole di un artefatto che è anche una slide. In cambio, ogni servizio si legge senza
risalire a un ancoraggio in cima, e le tre differenze di ruolo sono visibili nel punto in cui
capitano. La manutenzione peggiora: un cambiamento comune va ripetuto undici volte, e non c'è
niente che lo imponga automaticamente. È `tools/check_stack.py` a dover fare da rete — le regole
del Task 5 del piano esistono anche per questo.

**Alternative scartate:** copiare il file dello spike così com'è (veloce, e avrebbe portato dentro
la sonda debole insieme agli ancoraggi: due decisioni prese senza accorgersene); usare gli
ancoraggi solo per i blocchi davvero identici come `logging` (difendibile, ma introduce la domanda
«perché questo sì e quello no» in un file che deve rispondere a domande sullo sharding); generare
il file Compose da un modello (toglie di mezzo la ripetizione e mette al suo posto uno strumento in
più da spiegare, oltre a rendere il file non leggibile in un repository clonato senza eseguire
niente).

**Fonti:** [V-052](Sources.md#v-052)
---

<a id="adr-0060"></a>
## ADR-0060 — Quanti membri ha un set lo dice l'ambiente, e una guardia bilaterale controlla che sia vero

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto:** lo stack 03 ha tre componenti che sono replica set, e due profili che ne cambiano il
numero di membri: uno con `palco`, tre con `completo`. Qualcuno deve dire a `rs.initiate()` chi
sono i membri, e la via ovvia è che ogni componente abbia il suo servizio di inizializzazione con
un `depends_on` verso tutti i membri, `condition: service_healthy`. Così l'ordine di avvio lo
gestisce Compose e lo script non aspetta niente.

Quella via è chiusa. [V-053](Sources.md#v-053) l'ha misurata: un servizio **selezionato** non può
dichiarare `depends_on` verso un servizio **non selezionato**, e Compose rifiuta l'intero progetto
con `service "X" depends on undefined service "Y": invalid compose project`, uscita 1. La regola è
simmetrica — non conta chi ha il profilo — quindi non c'è nessuna combinazione di profili che salvi
un `cfg-init` che dipende da `cfg2`, perché nel profilo `palco` `cfg2` non esiste. La misura chiude
anche la riserva che [ADR-0010](#adr-0010) teneva aperta dal 24 agosto e quella di
[S-015](Sources.md#s-015) da cui era nata: il caso non documentato non è ambiguo, fallisce.

Restano tre strade. Sei servizi di inizializzazione invece di tre, uno per profilo, con i
`depends_on` giusti in ciascuno: raddoppia i servizi e mette due copie della stessa logica a
divergere. Nessun `depends_on` e nessuna attesa, lasciando che `rs.initiate()` fallisca e Compose
riprovi: rende l'avvio un'attesa cieca e i log illeggibili. Oppure il numero di membri arriva da
fuori, e lo script aspetta da sé.

**Decisione:**

1. **L'elenco dei membri arriva da una variabile d'ambiente**, per esteso e non come conteggio:
   `MEMBRI_CFG`, `MEMBRI_SHARD1`, `MEMBRI_SHARD2`, ciascuna un elenco di `nome-servizio:27017`
   separati da virgola. Per esteso perché è la stessa forma che finisce dentro `rs.initiate()`:
   un numero andrebbe tradotto in nomi da qualche parte, e quella traduzione sarebbe un secondo
   posto in cui la topologia è scritta.
2. **Ogni servizio di inizializzazione dipende da un solo membro**, quello presente in entrambi i
   profili — `cfg1`, `shard1a`, `shard2a` — con `condition: service_healthy`. Gli altri membri li
   aspetta lo script, interrogandoli per nome con `hello()` fino a trenta secondi. È più lavoro di
   un `depends_on`, ed è l'unico modo di ordinare l'avvio senza legare il servizio a un profilo.
3. **Una guardia bilaterale**, perché il numero di membri e il numero di container ora arrivano da
   due sorgenti diverse per lo stesso fatto, e possono divergere. Accanto a ogni elenco di membri
   viaggia un elenco di **candidati** — tutti i membri possibili di quel componente, fisso nel file
   Compose. Lo script rifiuta di procedere in tutte e due le direzioni:
   - un membro elencato che non risponde entro trenta secondi → uscita **4**;
   - un candidato **non** elencato che risponde → uscita **5**.

   La seconda è la ragione per cui la guardia esiste. Elencare un membro di troppo appende
   l'avvio, e un avvio appeso si nota; elencarne uno di meno non fallisce affatto: lo stack parte,
   sembra sano, e i due terzi dei container girano fuori dal set. In sala si scoprirebbe nel
   momento in cui la scena del failover non ha niente da mostrare. Vale qui la regola del
   repository per cui una condizione che non può fallire non è un controllo.
4. **Il verdetto di pronto si dà con il profilo addosso.** [ADR-0041](#adr-0041) già impone due
   comandi e non uno, perché `up --wait` considera a posto un one-shot appena parte;
   [V-054](Sources.md#v-054) lo riconferma sullo stack 03 in una forma peggiore — Compose stampa
   `Healthy` accanto a un container uscito **5**. La novità di questo stack è che
   `docker compose wait cfg-init` **senza** `--profile` risponde `no containers for project` e
   esce 1. I bersagli del Makefile devono quindi passare il profilo anche al comando che aspetta,
   e aspettare tutti e tre gli one-shot.

**Conseguenze:** chi lancia `docker compose` a mano deve tenere allineati `--profile` e le tre
variabili, e `.env.example` glielo dice con le righe del `completo` già scritte e commentate. Il
Makefile lo farà da sé nel Task 4. In cambio i servizi di inizializzazione restano tre e non sei,
e ogni disallineamento si presenta con un messaggio che nomina il container colpevole invece che
con uno stack silenziosamente sbagliato. Il costo vero è che `10-cfg-initiate.js` e
`11-shard-initiate.js` contengono un ciclo di attesa scritto a mano: quaranta righe che Compose
avrebbe fatto gratis se i profili lo avessero permesso, e che vanno mantenute.

Un effetto collaterale utile: siccome lo script interroga i membri per nome, il guasto si presenta
con il nome del membro e del componente. Un `addShard` che fallisce nel Task 3 dirà quale dei due
shard non aveva un primario, invece di lasciarlo dedurre.

**Alternative scartate:** sei servizi di inizializzazione, tre per profilo (nessuna attesa a mano,
ma due copie della stessa logica che divergeranno, e il numero di servizi del file Compose sale a
diciassette); un conteggio invece di un elenco, tipo `MEMBRI_CFG=3` (più corto da scrivere e
richiede di generare i nomi nello script, cioè di scrivere la topologia una seconda volta in
un'altra forma); nessuna guardia, affidandosi al Makefile che tiene allineate le variabili (regge
finché nessuno lancia Compose a mano, e il repository è materiale didattico: qualcuno lo lancerà a
mano, è anzi lo scopo); leggere il profilo attivo da dentro lo script (Compose non lo espone ai
container, e `COMPOSE_PROFILES` non arriva nell'ambiente del processo).

**Fonti:** [V-053](Sources.md#v-053), [V-054](Sources.md#v-054)

---

<a id="adr-0061"></a>
## ADR-0061 — La sonda di `mongos` chiede se è vivo, non se il cluster serve

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto:** con il Task 3 lo stack acquista i due `mongos` e il servizio one-shot `add-shard`,
che è il quinto e ultimo anello della catena di avvio. `add-shard` gira **dentro** `mongos`
(`network_mode: "service:mongos"`, come i tre init del Task 2 girano dentro il primo membro del
loro set) e quindi lo aspetta con `condition: service_healthy`.

Qui nasce la domanda. La tentazione, guardando gli altri healthcheck dello stack, è di rendere
onesta anche questa sonda: un `mongos` senza shard non serve a niente, quindi che `healthy`
significhi «il cluster ha i suoi shard». È un ragionamento che si morde la coda. `add-shard` è il
servizio che **registra** gli shard, aspetta `mongos` sano, e `mongos` non diventerebbe sano finché
`add-shard` non ha finito. Lo stack si bloccherebbe su se stesso, e — peggio — si bloccherebbe con
una diagnosi che punta al posto sbagliato: Compose direbbe che `mongos` non diventa sano, quando
il colpevole è il servizio che sta aspettando.

[V-055](Sources.md#v-055) ha misurato il terreno. Un `mongos` con zero shard è perfettamente vivo:
`hello()` risponde `ok=1` con `msg=isdbgrid`, `ping` passa, `listDatabases` elenca `admin` e
`config`, `sh.status()` stampa `shards []` con il balancer attivo. `hello()` passa **anche senza
credenziali**. Quello che non passa è la scrittura, con `ShardNotFound — No shards found`. E una
lettura risponde `[]` in silenzio, indistinguibile da un cluster sano con la collezione vuota.

Questa è la stessa forma già decisa da [ADR-0041](#adr-0041) per lo stack 02, dove `up --wait`
risponde 0 mentre gli init sono ancora in corsa e il verdetto vero è l'uscita del one-shot. Non è
un'invenzione nuova: è la regola vecchia applicata a un servizio nuovo.

**Decisione:**

1. **L'healthcheck di `mongos` è una sonda di vita, non di prontezza:**
   `quit(db.hello().ok === 1 ? 0 : 1)`. Non guarda `config.shards`, non conta gli shard, non prova
   a scrivere. Dice una cosa sola e la dice vera: il processo di routing risponde. Gira senza
   credenziali perché `hello()` non ne chiede, il che tiene la password fuori dal file Compose in
   un punto in più.

2. **Il verdetto «il cluster serve» è l'uscita di `add-shard`**, non lo stato di un container.
   Lo script controlla il risultato — `config.shards` alla fine ha almeno due righe — e non gli
   esiti dei singoli comandi, ed esce **7** se il cluster è incompleto. Chi vuole sapere se il
   cluster è pronto guarda quel codice, esattamente come nello stack 02 si guarda l'uscita di
   `rs-init`.

3. **Perciò l'avvio dello stack 03 resta in due comandi**, `up -d --wait` e poi
   `compose wait` sui one-shot, come ADR-0041 impone allo stack 02 e come
   [ADR-0060](#adr-0060) ha già stabilito debba avvenire **con il flag di profilo acceso**, che
   senza risponde `no containers for project` ed esce 1.

4. **`add-shard` dichiara tutte e tre le attese che gli servono**: `mongos` sano, e i due
   `shard{N}-init` completati con successo. La seconda parte non è ridondante: un `mongos` sano
   non implica che gli shard esistano, e `sh.addShard()` su un replica set senza primario eletto
   fallisce. Restano fuori i config server, che sono già coperti in transitiva — `mongos` non
   diventa sano senza `cfg-init`.

**Conseguenze:** fra `up --wait` che torna e `add-shard` che finisce esiste una finestra di qualche
secondo in cui lo stack è verde e le scritture falliscono con `ShardNotFound`. È esattamente la
finestra che ADR-0041 aveva già descritto per lo stack 02, ed è la ragione per cui il secondo
comando non è una raffinatezza. La pagina delle trappole del Task 9 deve raccoglierla insieme al
suo sintomo peggiore, che è la lettura muta: chi in quella finestra fa una `find` invece di una
`insert` riceve `[]` e conclude che il database è vuoto.

Il costo didattico è che l'healthcheck di `mongos` è il meno informativo dello stack, e uno
studente che lo legga da solo potrebbe crederlo pigro. Il commento accanto al servizio spiega
perché non può essere altro, e il ragionamento del deadlock è materiale per il Blocco 3.

**Alternative scartate:** una sonda che conta gli shard (il deadlock descritto sopra); una sonda
che prova una scrittura (stesso deadlock, più un documento scritto a ogni giro di healthcheck);
`add-shard` senza `depends_on` verso `mongos`, lasciandolo riprovare a collegarsi (rende l'avvio
un'attesa cieca, e i tre init del Task 2 avevano già scelto il contrario); un healthcheck di
prontezza su `mongos2` soltanto, dove il deadlock non ci sarebbe perché `add-shard` gira nel primo
(due sonde diverse per lo stesso ruolo, e `mongos2` non esiste nel profilo `palco`).

**Fonti:** [V-055](Sources.md#v-055)

---

<a id="adr-0062"></a>
## ADR-0062 — Lo stack 03 si avvia con un comando, e a farlo è un servizio che non fa niente

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto:** [ADR-0041](#adr-0041) ha deciso per lo stack 02 che l'avvio è di **due comandi**,
perché `docker compose up -d --wait` esce con successo prima che il replica set esista. Il
ragionamento è ancora valido e la misura pure: `--wait` è documentato come «Wait services be
running|healthy» ([S-057](Sources.md#s-057)), un one-shot che deve morire non ha healthcheck,
quindi la soglia che gli si applica è `running` ed è soddisfatta nell'istante in cui parte.

Il Passo 4 del Task 4 di `feature/03` chiedeva di verificare che su questo stack `up --wait`
esca 0 soltanto quando il cluster serve. Così com'è non è verificabile: è falso, e
[V-056](Sources.md#v-056) lo ha rimisurato qui — senza sentinella `up --wait` esce **0 dopo 18
secondi** con `add-shard` ancora in corsa e **zero shard registrati**, e esce **0** anche quando
la catena è rotta e non ci sarà mai nessuno shard. La domanda utile non è se la proprietà valga,
ma se si possa costruirla.

Si può. Un servizio che dipende da `add-shard` con `service_completed_successfully` non diventa
`running` finché `add-shard` non è uscito 0, e `--wait` aspetta che diventi `running`. Misurato
nei due versi: con la sentinella `up --wait` esce 0 a cluster fatto — nell'istante in cui torna,
`sh.status()` mostra due shard `state: 1` e una scrittura passa — oppure esce **1** con
`service "add-shard" didn't complete successfully: exit 6`.

Va detto che cosa questo **non** è. Non è dare un healthcheck a `add-shard`: ADR-0041 l'aveva
scartato con l'argomento giusto — un healthcheck descrive un container che resta vivo, un one-shot
deve morire — e quell'argomento regge. `add-shard` resta senza healthcheck e il suo verdetto resta
un codice di uscita. La sentinella usa `service_completed_successfully` per quello per cui è
documentato, cioè un vincolo di **ordine di avvio**, e sposta l'attesa su un servizio che vive
davvero.

**Decisione:**

1. **Lo stack 03 ha un servizio `up-03`** che dipende da `add-shard` con
   `service_completed_successfully`, non ha healthcheck, stampa una riga e dorme. Non ha healthcheck
   apposta: senza, la soglia di `--wait` per lui è `running`, che è esattamente la domanda giusta.

2. **L'avvio dello stack 03 è di UN comando**, `up -d --wait`, e il suo codice di uscita è il
   verdetto. È l'opposto della regola che ADR-0041 detta per lo stack 02, e i due stack restano
   diversi: quella regola non viene toccata.

3. **Il secondo comando qui non va dato**, e non è una preferenza. `docker compose wait add-shard`
   dopo un `up --wait` riuscito risponde `no containers for project` ed esce **1**, perché il
   container ha già finito e `wait` vuole qualcosa di vivo a cui attaccarsi. Un bersaglio del
   Makefile scritto per analogia con `up-02` fallirebbe sempre. Il Task 7 scrive **una** riga.

4. **`docker compose wait add-shard` resta lo strumento per la diagnosi**, non per il verdetto:
   `up --wait` esce 1 e non 6, quindi i codici distinti di `20-add-shard.js` sopravvivono solo nel
   testo del messaggio. Chi automatizza e vuole distinguere «addShard fallita» da «cluster
   incompleto» lancia `add-shard` da solo e ne legge l'uscita.

5. **La sonda severa si mette solo su un servizio da cui non dipende nessuno.** È la regola
   generale che tiene insieme questa decisione e [ADR-0061](#adr-0061): lì una sonda di prontezza
   su `mongos` era un cappio perché `add-shard` aspetta la salute di `mongos`; qui la sentinella
   può essere severa quanto si vuole perché nessuno la aspetta. Vale per gli stack che verranno.

**Conseguenze.** Lo stack acquista un container che non è MongoDB e che comparirà in `docker ps`
durante il talk. È un costo didattico reale, e si paga volentieri perché è anche una slide: il
container esiste perché `up --wait` mente, e spiegarlo insegna più di quanto costi. `up-03` è
scritto sull'immagine di `mongo` e non su `busybox` benché sia due ordini di grandezza più pesante:
il lab deve funzionare senza rete, e tutto lo stack gira su una immagine sola — la sentinella non è
un buon motivo per pinnarne una seconda. Il processo acceso è `sleep`.

Un debito verso lo stack 02, aperto qui perché è qui che si è visto: `up-02` esegue proprio i due
comandi, e funziona perché `up --wait` torna **prima** che `rs-init` finisca. La distanza fra le
due cose è di secondi e nessuna misura dice quanto sia stabile altrove; se un giorno `rs-init`
finisse per primo, `wait rs-init` risponderebbe `no containers` e il bersaglio fallirebbe senza che
niente sia rotto. Va verificato al Task 7, che è il task che tocca il Makefile.

**Alternative scartate:** lasciare due comandi anche qui (il secondo fallisce, misurato — non è
un'alternativa, è un guasto); dare un healthcheck a `add-shard` (piega la salute a descrivere una
cosa morta, e ADR-0041 l'ha già scartato); un healthcheck sulla sentinella che riverifichi il
cluster (non aggiunge niente, perché `add-shard` ha già verificato il risultato uscendo 7 se
incompleto, e ritarderebbe l'uscita di `up` del suo primo intervallo); `busybox` invece
dell'immagine di mongo (una seconda immagine da pinnare e scaricare, contro il vincolo del lab
offline); nessuna sentinella e la verifica affidata allo smoke del Task 7 (sposta il problema più
in là e lascia `up --wait` a mentire a chi lo lancia a mano, che è il caso d'uso del materiale
didattico).

**Fonti:** [V-056](Sources.md#v-056)

---

<a id="adr-0063"></a>
## ADR-0063 — Che cosa `check_stack.py` deve saper bocciare quando lo stack è sharded

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto.** [ADR-0042](#adr-0042) ha insegnato a `tools/check_stack.py` il mondo dello stack 02:
un replica set, un keyfile condiviso, una catena di dipendenze. Lo stack 03 aggiunge una cosa che i
primi due non avevano — **i ruoli**. Fino a qui ogni `mongod` era intercambiabile con ogni altro; da
qui un `mongod` è un config server oppure un membro di shard, e la differenza è una riga sola nel
comando. Accanto compare un terzo programma, `mongos`, che non è un `mongod` e che quasi tutte le
regole scritte finora devono avere il buon senso di non toccare.

Il piano elencava sei regole candidate. Tre erano **già in vigore e sono state verificate senza
scrivere codice**: nessun servizio usa un IP letterale, ogni servizio dichiara `mem_limit`, `cpus` e
`pull_policy: never`, ogni `mongod` dichiara una cache non superiore al proprio `mem_limit`. Valgono
sui ruoli nuovi perché non guardano il ruolo, e la prova che il caso del router fosse già previsto
esisteva da prima: un test dello stack 01 usa un comando `mongos` proprio per dire che a lui la
cache non si chiede.

Prima di scrivere le altre tre sono stati misurati i sintomi che dovrebbero prevenire, e la misura
ha dato la notizia contraria a quella attesa ([V-057](Sources.md#v-057)): **cinque sintomi su sei
non sono muti affatto**. Il server nomina l'opzione che manca, in inglese, con una frase cercabile —
«Cannot run addShard on a node started without --shardsvr», «Nodes being used for config servers
must be started with the --configsvr flag», «shardsvr is not allowed when configsvr is specified».
La giustificazione «senza questa regola l'errore è illeggibile» sarebbe stata comoda e falsa, e due
commenti del file Compose che la sostenevano sono stati corretti.

Il sesto sintomo però è muto sul serio, ed è quello del refuso: `cfgsr` per `cfgrs` dentro
`--configdb`. Tutti i processi partono, il router resta `unhealthy` per novantaquattro secondi
senza mai aprire la porta, e nel suo log **il nome giusto del replica set non compare nemmeno una
volta**. Quello che si legge è `HostUnreachable` su due host che nel profilo `palco` sono
irraggiungibili per costruzione, e `FailedToSatisfyReadPreference` sull'unico host che risponde. La
diagnosi indica la rete; la causa sono due lettere scambiate.

**Decisione.** Cinque regole nuove, e un criterio per decidere a chi si applicano.

*Il criterio, che è la parte che conta.* Lo strumento deve **dedurre il ruolo di un servizio
leggendo il file**, e la catena è tutta lì dentro: il `mongos` dichiara in `--configdb` il nome del
replica set dei config server; ogni `mongod` dichiara in `--replSet` a quale set appartiene; chi
appartiene a quel set è un config server, chiunque altro è uno shard. Nessuno dei tre passaggi
guarda il nome del servizio — rinominare `cfg1` in `secondo` non sposta un verdetto, e c'è un test
che lo esercita. È lo stesso criterio di ADR-0042 e per lo stesso motivo: un elenco di nomi da
tenere aggiornato a mano invecchia in silenzio, una guardia che legge il file no. Ed è per questo
che le regole tacciono sugli stack 01 e 02: quei file non hanno un `mongos`, non compaiono in
nessuna lista di eccezioni.

*Le cinque regole*, descritte dai messaggi che stampano, che restano la loro documentazione vera:

1. un `mongod` che sta nel replica set nominato da `--configdb` dichiara **`--configsvr`**;
2. un `mongod` che sta in un altro replica set è uno shard e dichiara **`--shardsvr`**;
3. nessun `mongod` dichiara tutti e due — non è un ruolo ambiguo, è un ruolo impossibile, e mongod
   non parte affatto;
4. un `mongos` dichiara `--configdb`, nella forma `nomeSet/host:porta`, e il set nominato deve
   essere dichiarato da qualche `mongod` di questo file;
5. un `mongos` non dichiara `--wiredTigerCacheSizeGB`, perché non ha uno storage engine.

Le regole 3 e 5 non erano nell'elenco del piano. La 3 è venuta dietro alla stessa domanda delle
prime due — per applicarle lo strumento deve decidere il ruolo, e «tutti e due» è la risposta che va
gestita prima delle altre — e la 5 protegge il ruolo nuovo dall'errore che il file didattico rende
più probabile di ogni altro: copiare il blocco di un `mongod` e cambiare solo la prima riga. La
regola 4 è la traduzione onesta di quella che il piano scriveva come «`--configdb` nomina il set
`cfgrs`»: scrivere `cfgrs` dentro lo strumento avrebbe legato un controllo generico al nome di un
solo stack, contro il principio che lo stack è un argomento, e avrebbe perso il caso che conta —
non il nome sbagliato in assoluto, ma il nome **incoerente con il resto del file**.

*La giustificazione, detta come la misura la sostiene.* Il guadagno di queste regole non è tradurre
un messaggio oscuro. È **spostare l'incontro con l'errore**: due secondi di `make stack-check` su un
file fermo, invece di un minuto e ventuno di avvio con dieci container accesi, e il pubblico che
guarda. La sola eccezione è la regola 4 nel caso del refuso, dove non c'è nessun messaggio da
anticipare e la regola è l'unica cosa che parla.

**Conseguenze.** `make stack-check` verifica ora **tre** file Compose, e `STACK_03` entra nel
`Makefile` con un Task di anticipo rispetto al piano, che lo collocava al Task 7. La suite degli
strumenti passa da 114 a 125 test. Le regole sono state provate sul file vero e non solo sui
campioni, come ADR-0042 aveva stabilito: sette copie dello stack 03, un difetto ciascuna, la copia
intatta verde e sei messaggi distinti, uno per copia.

Restano due limiti da non nascondere. Il primo è quello di sempre e vale integralmente: sei difetti
non sono tutti i difetti, e la conformità statica non ha mai sostituito l'avvio dello stack. Il
secondo è più stretto e riguarda la regola 4: lo strumento legge un file solo per volta, quindi «il
set è dichiarato da qualche `mongod` di questo file» è una verità che vale finché i tre stack del
lab restano in un file ciascuno. Il giorno in cui un `mongos` vivesse in un Compose separato dai suoi
config server, la regola darebbe un falso allarme — rumoroso e visibile, che è il verso giusto in
cui sbagliare, ma sarebbe da rivedere.

**Fonti:** [V-057](Sources.md#v-057)

---

<a id="adr-0064"></a>
## ADR-0064 — La shard key della demo è `{_id: "hashed"}`, e i ventimila documenti sono gli stessi nei due profili

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto.** La shard key è **il** contenuto del Blocco 3 del talk. Tutto il resto dello stack 03 —
i tre ruoli, la catena di avvio, il router davanti — è impalcatura per arrivare qui: è la sola
decisione di questa architettura che un partecipante porterà a casa e applicherà, e l'unica che, se
sbagliata, non si corregge senza rifare la collezione.

Il dataset da distribuire esiste già e non è in discussione: gli `ordini` generati dal seme
`20260918` che gli stack 01 e 02 usano da `feature/01`. Sono documenti con `_id` interi consecutivi
`0 … n-1`, cioè — non per caso, ma è una fortuna — **il caso peggiore possibile** per una chiave per
intervalli, e quindi l'esempio migliore possibile per spiegare perché serve l'hash.

Restavano da decidere tre cose: quale campo, con quale forma, e quanti documenti per profilo.

**Decisione.** Shard key `{_id: "hashed"}`; 20 000 documenti sia in `palco` sia in `completo`.

*Il campo.* `_id`, per tre ragioni in ordine di forza. È l'unico campo garantito presente e unico
in ogni documento, il che elimina in partenza la classe di problemi che il manuale chiama frequenza
e cardinalità. Tiene il dataset **identico** a quello degli altri due stack: questi 20 000 documenti
sono i primi 20 000 dei 50 000 di `feature/01`, campo per campo, e la demo può quindi mostrare la
stessa query su tre architetture senza che nessuno debba chiedersi se sono gli stessi dati. E, per
onestà, è la scelta che il manuale **non** avalla in generale: [S-067](Sources.md#s-067) insiste sul
verso opposto — la chiave si sceglie sul modo in cui si interroga la collezione — e nel materiale
questa è detta per quello che è, una comodità didattica.

L'alternativa scartata è `citta`, che sarebbe stata leggibile e sarebbe stata la peggiore
disponibile: dieci valori distinti, e «the cardinality of a shard key determines the maximum number
of chunks the balancer can create» (S-067). Dieci chunk al massimo per l'intero cluster, con la
conseguenza che il manuale mette per iscritto sul suo esempio a sette valori — «this constrains the
number of effective shards in the cluster to `7` as well».

*La forma: hashed e non per intervalli.* Con `{_id: 1}` la partizione sarebbe per intervalli, e in
ogni cluster esiste il chunk con estremo superiore `MaxKey`. Un `_id` che cresce sempre è sempre
maggiore di tutti quelli già scritti, quindi ogni inserimento cade lì: «the shard containing that
chunk becomes the bottleneck for write operations» (S-067). Con l'hash i valori contigui finiscono
sparsi, e la misura lo conferma — 49,3 % / 50,7 % ([V-058](Sources.md#v-058)).

Due precisazioni entrano nel materiale perché senza il racconto diventa una caricatura, e una
caricatura dal palco si smonta alla prima domanda. La prima: il chunk caldo **non resta fermo**.
«To optimize data distribution, the chunks that contain the global `maxKey` (or `minKey`) do not
stay on the same shard» (S-067) — il collo di bottiglia cambia nodo man mano che i chunk si
dividono. Non sparisce, perché in ogni istante le scritture vanno tutte in un posto solo e in più il
cluster paga le migrazioni; ma non è il nodo unico e immobile che le spiegazioni brevi descrivono.
La seconda: l'hash **non è una garanzia**. «A shard key that does not change monotonically does
not, on its own, guarantee even distribution of data across the sharded cluster» (S-067) — qui
funziona perché `_id` ha cardinalità massima e frequenza uniforme, non perché sia hashed.

*Il prezzo, che si dice invece di nasconderlo.* Si perde la località. Il manuale: «post-hash,
documents with "close" shard key values are unlikely to be on the same chunk or shard - the `mongos`
is more likely to perform Broadcast Operations to fulfill a given ranged query. `mongos` can target
queries with equality matches to a single shard» ([S-066](Sources.md#s-066)). Misurato sul lab: un
`{_id: 42}` interroga **uno** shard, un `{_id: {$gte: 100, $lt: 200}}` li interroga **tutti e due**
(V-058). Le due righe sono nello smoke apposta, perché è il baratto in forma eseguibile: si sceglie
fra distribuire le scritture e tenere vicine le letture contigue, e non si ottengono tutte e due.

*L'ordine: prima si distribuisce, poi si riempie.* Non è indifferente e non è una preferenza.
Distribuendo una collezione **vuota**, «the sharding operation creates empty chunks to cover the
entire range of the shard key values and performs an initial chunk distribution. By default, the
operation creates 2 chunks per shard and migrates across the cluster» (S-066): due per shard, due
shard, **quattro chunk** — il numero che lo spike §5 aveva misurato senza sapere che fosse un
valore predefinito documentato. Sull'ordine inverso il manuale è altrettanto chiaro: su una
collezione piena «the sharding operation creates an initial chunk to cover all of the shard key
values», uno solo, e poi tocca al balancer. Funzionerebbe, ma l'avvio del lab diventerebbe una gara
col balancer e la distribuzione al primo `sh.status()` sarebbe 100 % / 0 %.

*Ventimila in tutti e due i profili.* Il piano fissa 20 000 per `palco` e lo spike aveva usato
50 000 per `completo`. La scelta è di tenerne 20 000 anche lì: **i due profili differiscono nella
topologia, non nei dati**. Un dataset che cambia col profilo renderebbe i numeri mostrati dal palco
dipendenti da quale profilo sta girando, e la prima domanda del pubblico sarebbe sul numero
sbagliato. La misura conferma che non si perde niente: la distribuzione è identica nei due profili —
9860 e 10140 — perché dipende dall'hash delle chiavi e dai confini dei chunk, e i membri in più sono
copie dello stesso shard (V-058).

**Conseguenze.** `docker/03-sharded/init/30-dati-demo.js` porta il ragionamento accanto al comando
che lo applica: è il file più commentato dello stack, e deliberatamente — è la pagina del Blocco 3.
`lab.ordini` sullo stack 03 ha **due** indici e non uno, perché `shardCollection()` crea
`_id_hashed` senza che nessuno lo chieda; è l'unica differenza rispetto agli altri due stack, dove
la collezione ha il solo `_id_` per far vedere una query con e senza indice, e lo smoke la asserisce
per iscritto perché non passi per un residuo.

Restano due limiti dichiarati. Il primo: il 49,3 % / 50,7 % è una proprietà di questo dataset con
questo seme, non una legge — lo smoke fissa la soglia al 40 % per shard proprio per non confondere
una fluttuazione statistica con un guasto. Il secondo riguarda la versione: `_id_hashed` si può
togliere solo dalla 7.0.3 in poi (S-066), e il lab ci rientra per la 7.0.40 pinnata da
[ADR-0028](#adr-0028) — un vincolo che il giorno di un downgrade tornerebbe a mordere.

**Fonti:** [S-066](Sources.md#s-066) · [S-067](Sources.md#s-067) · [V-058](Sources.md#v-058)

---

<a id="adr-0065"></a>
## ADR-0065 — I dati entrano come sesto anello della catena, e la prova sa distinguere due shard da uno

**Data:** 2026-09-01 · **Stato:** Accettata

**Contesto.** Il Task 6 nominava due file: lo script che carica i dati e lo smoke. Scrivendoli è
emerso che i due si tengono per un vincolo che nessuno dei due nomina.

Il vincolo è questo: la sola asserzione che distingue uno sharded cluster funzionante da uno rotto è
la **distribuzione dei documenti**, e per misurarla i documenti devono esserci. Se il dataset
arrivasse da un comando separato, `make smoke-03` dopo `make up-03` fallirebbe — o peggio, andrebbe
verde saltando l'unico controllo che conta.

C'è poi una ragione che viene da fuori: negli stack 01 e 02 i dati ci sono appena l'avvio è finito.
Un terzo stack che pretende un comando in più è un comando in più da ricordare davanti al pubblico,
e [ADR-0062](#adr-0062) ha appena stabilito che lo stack 03 si avvia con **un** comando.

**Decisione.** Due decisioni legate.

*Il seed è il sesto anello della catena.* Il servizio one-shot `seed` entra nel file Compose dopo
`add-shard`, con `service_completed_successfully`, e la sentinella `up-03` sposta la propria
dipendenza da `add-shard` a `seed`. La catena diventa: `keyfile-init` → (`cfg-init`, `shard1-init`,
`shard2-init`) → `mongos` → `add-shard` → `seed` → `up-03`. Quello che cambia è **che cosa promette
`up --wait`**: prima «i due shard sono registrati», adesso «c'è anche il dataset» — che è la
promessa che gli altri due stack fanno già. Dopo `add-shard` e non prima, perché distribuire una
collezione vuota crea i chunk e li spalma sugli shard registrati **in quel momento**: fatto prima,
`shardCollection()` fallirebbe per mancanza di shard; fatto con uno solo, darebbe due chunk su un
nodo e un balancer da rincorrere. Il servizio è idempotente come tutti gli altri anelli — al secondo
`up` trova i documenti e non fa niente — e `make seed-03` resterà per **ricaricare**, con
`run --rm -e RICARICA=1`, non per caricare la prima volta.

Questo è uno scostamento dall'elenco dei file del Task 6, che nominava solo lo script e lo smoke, ed
è registrato come tale: il piano approvato non si tocca.

*Lo smoke asserisce la distribuzione, e la asserisce in due modi.* `tools/smoke-sharded.sh` segue
`smoke-replicaset.sh` nella forma — niente `set -e`, tutti i problemi in un giro solo, la password
letta da `.env` e mai passata con `-e` al client `docker` ([ADR-0054](#adr-0054)) — e il profilo si
sceglie con `PROFILO=palco|completo`, perché i controlli che contano i nodi hanno risposte diverse e
uno smoke che ne sapesse una sola mentirebbe sull'altro profilo.

Il criterio con cui i controlli sono stati scelti: **tutto quello che non riguarda la distribuzione
passerebbe identico su un cluster che ha messo i ventimila documenti su un solo shard.** Un cluster
così risponde, scrive, legge, e `sh.status()` gli mostra due shard. Quindi lo smoke verifica che
ciascuno dei due shard contenga documenti e che nessuno stia sotto il 40 %, e in più mette alla
prova il baratto della chiave: uguaglianza su `_id` → **uno** shard, intervallo sulla stessa chiave
→ **tutti**. Se un giorno la seconda tornasse `1`, vorrebbe dire che la chiave non è più hashed, e
sarebbe un guasto che nessun altro controllo vedrebbe.

**Conseguenze.** Lo stack 03 nel profilo `palco` sale a **11** servizi e in `completo` a **18**.
`up -d --wait` chiude a 0 in **23 secondi** su `palco` e in **36** su `completo`, dataset compreso
([V-058](Sources.md#v-058)). Lo smoke chiude a **62 controlli e 0 errori** su `palco`, **99 e 0** su
`completo`.

Due cose sono state imparate scrivendolo e sono finite nei commenti del file, perché sono
esattamente il genere di cosa che si riscopre a caro prezzo. La prima: **gli utenti di uno sharded
cluster vivono sui config server**, e la stessa coppia utente/password che funziona sul router dà
`Authentication failed` su uno shard interrogato in diretta. Non è un guasto, è la regola, e lo
smoke la asserisce come tale — se un giorno passasse, vorrebbe dire che qualcuno ha creato utenti
sugli shard e che da lì in poi ci sono due anagrafiche da tenere allineate. La conseguenza pratica è
che le misure interne dei nodi si leggono da `docker inspect` e dalla riga `cache_size=…` del log,
non da `hostInfo()`. La seconda: **`/data/db` risulta montato anche su `mongos`**, perché
l'immagine di MongoDB dichiara `VOLUME /data/db` e Docker crea un volume anonimo su ogni container.
Il controllo ovvio — «il router non monta `/data/db`» — è quindi falso su un cluster sano, ed è
stato l'unico rosso dell'intera prova. Il discriminante vero è il volume **nominato**.

Il limite da dichiarare: le costanti dello smoke sono numeri misurati su questo dataset e su questa
versione, e il conteggio dei controlli dipende dal profilo. Il giorno in cui cambia il seme del
generatore, l'impronta `20000 50083417.93 60278` va rimisurata — e lo smoke fallirà rumorosamente,
che è il verso giusto in cui sbagliare.

**Fonti:** [V-058](Sources.md#v-058)

---

<a id="adr-0066"></a>
## ADR-0066 — Lo stack 03 si spegne con tutti i profili, non con quello con cui è stato acceso

**Data:** 2026-09-02 · **Stato:** Accettata

**Contesto.** Il Task 7 dà allo stack 03 i suoi bersagli nel `Makefile`. La prima decisione è stata
come far entrare il profilo: `up-03-palco` e `up-03-completo`, cioè **due famiglie** di sei bersagli
l'una, oppure `PROFILO` come variabile e una famiglia sola. La variabile ha vinto per un motivo
semplice — con due famiglie basta sbagliare un suffisso una volta, `make up-03-completo` seguito da
`make down-03-palco`, per fermare metà cluster — e per un motivo che vale sul proiettore, cioè che
`make up-03 PROFILO=completo` mostra che il profilo è un parametro dello stesso stack e non un altro
stack.

Poi la scelta è stata provata, e la variabile da sola non bastava. [V-059](Sources.md#v-059) ha
misurato che `down` agisce **solo sui servizi dei profili attivi**: spegnere in `palco` uno stack
acceso in `completo` toglie undici container, ne lascia sette accesi, non riesce a rimuovere la rete
— «Resource is still in use» — ed esce **zero**. Nessun errore, nessun segnale. E `down` senza
`--profile` fa esattamente la stessa cosa, perché i servizi sempre attivi sono soltanto quelli che
non dichiarano nessun profilo ([S-068](Sources.md#s-068)).

Il difetto è dell'operazione, non della variabile: al momento di spegnere non si sa — e non si deve
dover ricordare — con quale profilo qualcun altro ha acceso.

**Decisione.** Il `Makefile` dello stack 03 usa **due** forme del comando Compose, e la seconda non è
una comodità.

`COMPOSE_03` porta `--profile $(PROFILO)` e serve ai comandi che **scelgono** che cosa esiste:
`up-03`, `seed-03`, e lo smoke, a cui il profilo arriva per ambiente. `COMPOSE_03_OGNI` porta
`--profile "*"` e serve ai comandi che agiscono su **tutto quello che c'è**: `down-03`, `reset-03`,
`logs-03`. Il jolly è la forma documentata per dire «tutti i profili» ([S-068](Sources.md#s-068)),
ed è preferito all'elenco `--profile palco --profile completo` per la stessa ragione per cui
[ADR-0042](#adr-0042) rifiuta le liste di eccezioni: un elenco scritto a mano invecchia in silenzio
al primo profilo nuovo, il jolly no.

`reset-03` cancella i nove volumi dei dati costruendoli con `addprefix` e **non** tocca `keyfile`,
per la stessa ragione dello stack 02: rigenerarlo significa un segreto nuovo.

**Conseguenze.** `make down-03` e `make reset-03` fanno la cosa giusta qualunque sia il profilo con
cui si è acceso, e `PROFILO` su quei tre bersagli diventa ininfluente — il che è il punto: non c'è
una combinazione sbagliata da indovinare. Misurato: `down-03` dopo un `palco` con un servizio del
`completo` aggiunto a mano rimuove tutti i container e la rete e lascia in piedi i cinque volumi
([V-059](Sources.md#v-059)).

Il prezzo è una riserva dichiarata. La pagina di Docker non dice da quale versione di Compose
`--profile "*"` esista, e qui è provato su **v5.5.0**: su una versione più vecchia va riverificato.
Il costo di sbagliarsi è basso e visibile — il jolly non riconosciuto darebbe un errore di
argomento, non uno spegnimento silenzioso a metà — che è il verso giusto in cui sbagliare.

Resta un debito, e vale per tutti e tre gli stack: **niente lega il `Makefile` ai profili dichiarati
nel file Compose.** Se domani nascesse un terzo profilo, il jolly lo prenderebbe da sé nello
spegnimento, ma nessun controllo direbbe che `up-03` non lo sa accendere. Il Task 9 lo valuta
insieme agli altri debiti segnati.

**Fonti:** [S-068](Sources.md#s-068) · [V-059](Sources.md#v-059)

---

<a id="adr-0067"></a>
## ADR-0067 — I config server dichiarano dove scrivono, e una guardia lega il volume al dbpath

**Data:** 2026-09-02 · **Stato:** Accettata

**Contesto.** Il Task 7 ha scoperto, provando i bersagli nuovi, che la sequenza più ordinaria dello
stack 03 non funzionava: `make up-03`, `make down-03`, `make up-03` falliva al secondo avvio con
`can't add shard 'shard2rs/shard2a:27017' because a local database 'lab' exists in another
shard1rs`.

La causa non è quella che il messaggio suggerisce. I config server **perdevano tutto a ogni
spegnimento** mentre gli shard conservavano i loro dati, quindi al riavvio il cluster non
riconosceva più i propri shard e provava a registrarli da capo su nodi che avevano già `lab`.
[V-060](Sources.md#v-060) l'ha contato: `dati-cfg1` e `dati-cfg2` contenevano **zero file**,
`dati-shard1a` ottantatré.

Il meccanismo sta in due fatti che si sommano, e nessuno dei due è un errore di per sé. Il primo:
l'entrypoint dell'immagine ufficiale, quando fra gli argomenti trova `--configsvr`, porta il dbpath
predefinito a `/data/configdb` invece che a `/data/db` — letto dentro l'immagine pinnata
([V-060](Sources.md#v-060)), e presente con altre parole anche nel ramo 8.0 dello stesso script
([S-022](Sources.md#s-022)). Il secondo:
l'immagine dichiara `VOLUME` su **entrambe** le cartelle, quindi Compose soddisfa quella non montata
con un volume **anonimo**, che `down` abbandona penzolante e che il `up` successivo rifà vuoto.
Insieme: i tre config server montavano `dati-cfgN` su `/data/db` — il posto giusto per ogni altro
mongod — e scrivevano altrove, in un contenitore che nessuno aveva chiesto e che nessuno conservava.

Il difetto è sopravvissuto quattro giorni perché era muto in tre modi. Il file Compose sembrava a
posto: la riga del volume c'era, con il nome giusto. Lo smoke era d'accordo, perché verificava che
ogni mongod **avesse** il proprio volume nominato e non che ci scrivesse dentro. E tutte le prove
dei Task 3-6 finivano con `down -v`, che cancella tutto: la perdita dei metadati è invisibile a chi
riparte sempre da zero.

**Decisione.** Tre cose, e la prima da sola non basterebbe.

*I tre config server dichiarano `--dbpath /data/db`.* Sono due righe per servizio nel file Compose,
accanto a `--port 27017`, che è là per la ragione gemella: `--configsvr` cambia più di un
predefinito, e nessuno di quei cambiamenti si vede leggendo il file. Fra le due riparazioni
possibili — dire a mongod dove scrivere, oppure montare il volume dove scriverebbe — si è scelta la
prima perché tiene i nove mongod dello stack uniformi: **il volume dei dati sta su `/data/db`**, una
regola sola per chi legge. L'altra resta legittima e la guardia la accetta.

*`check_stack.py` guadagna una regola statica.* Per ogni servizio che avvia un `mongod`, calcola il
dbpath che userà davvero — `--dbpath` se c'è, altrimenti `/data/configdb` se c'è `--configsvr`,
altrimenti `/data/db` — e boccia il file se un volume è montato su una cartella dei dati **diversa**
da quella. Le due cartelle sono scritte nel codice, e non è la lista di eccezioni che
[ADR-0042](#adr-0042) proibisce: quella elencava nomi di servizio, che cambiano a ogni stack nuovo;
queste due sono i `VOLUME` che l'immagine dichiara, leggibili con `docker image inspect`, e cambiano
solo se cambia l'immagine. La regola giudica un montaggio **sbagliato**, non uno mancante: un mongod
senza volumi dati non produce niente, perché lo stack 01 gira così per scelta
([ADR-0005](#adr-0005)).

*Lo smoke smette di accontentarsi.* Il controllo che aveva approvato lo stack rotto confronta adesso
la destinazione del volume nominato con il dbpath ricavato dal comando del container. Le due guardie
sono apposta ridondanti: quella statica giudica il file del repository, questa il processo che sta
girando, e solo la seconda vedrebbe un container avviato con un file diverso.

**Conseguenze.** Il ciclo che falliva adesso regge: `reset-03` 4 s, `up-03` 25 s con `dati-cfg1` a
**99 file**, `down-03` 7 s, `up-03` di nuovo **22 s** e a posto. Il ramo idempotente di `add-shard`,
scritto al Task 4, è stato **eseguito per la prima volta oggi** — prima di questa correzione non
poteva esserlo, perché i metadati non arrivavano mai al secondo giro: un pezzo di codice provato
solo dai test unitari lo era anche in produzione, senza che niente lo dicesse. `make smoke-03`
resta a 62 controlli e 0 errori, `make stack-check` a «Stack conformi: 3», la suite degli strumenti
a **131 passed** con sei test nuovi. Entrambe le guardie sono state provate rompendole
([V-060](Sources.md#v-060)).

Lo scostamento dal piano è dichiarato: il Task 7 nominava `Makefile`, `reset-demo.sh` e
`preflight.sh`, e questa correzione tocca `compose.yaml`, `check_stack.py` e `smoke-sharded.sh`, che
appartengono ai Task 3, 5 e 6. Non è stato rinviato al Task 9 perché non è un debito ma un guasto, e
perché il guasto colpisce la sequenza che al talk capita per prima: spegnere fra una parte e l'altra
e riaccendere.

Resta scoperto un caso, e va detto: chi ha già dei volumi `dati-cfgN` creati **prima** di questa
correzione se li ritrova vuoti e inutilizzabili, perché i metadati stavano nell'anonimo che intanto
è stato buttato. La via d'uscita è `make reset-03`, che è anche l'unica cosa sensata da fare con
metadati che non ci sono più. Nessuna migrazione: questo è un laboratorio, e i dati si rifanno in
venticinque secondi.

**Fonti:** [S-022](Sources.md#s-022) · [V-060](Sources.md#v-060)

---

<a id="adr-0068"></a>
## ADR-0068 — La pagina dello sharded cluster mostra la chiave sbagliata invece di descriverla

**Data:** 2026-09-02 · **Stato:** Accettata

**Contesto.** L'[indice](README.md) promette per nome
`docs/02-architetture/sharded-cluster.md` da `feature/00`, e il design le assegna il Blocco 3 del
talk: otto minuti, una slide, `sh.status()` già a schermo e il rimando al repository. Il materiale
esiste ed è sparso: il blocco `LA SHARD KEY` dentro `docker/03-sharded/init/30-dati-demo.js`, sette
ADR fra la [0058](#adr-0058) e la [0067](#adr-0067), sei verifiche empiriche dalla
[V-052](Sources.md#v-052) alla [V-060](Sources.md#v-060). La pagina lo raccoglie; non lo riscopre.

Ma due sezioni non si potevano scrivere con quello che c'era. Il **balancer** era un verbo senza
misure: il repository non sapeva se in questa demo lavorasse. E la **shard key sbagliata** era una
citazione — ottima, tripla, ma una citazione: il difetto che il Blocco 3 esiste per raccontare non
era mai stato visto accadere in questo laboratorio, e [ADR-0052](#adr-0052) ha stabilito che una
trappola scritta senza il sintomo è una previsione. [V-061](Sources.md#v-061) ha colmato tutti e
due i buchi, e ha trovato per strada una terza cosa che nessuno cercava.

**Decisione.**

*La pagina apre con l'irreversibilità, non con la topologia.* Il primo fatto non è che i componenti
sono tre: è che «once a collection has been sharded, MongoDB provides no method to unshard a sharded
collection» ([S-069](Sources.md#s-069)). Le altre due pagine di `02-architetture` descrivono scelte
che si disfano spegnendo un container; questa no. Chi legge deve saperlo prima di trovare la parte
interessante, perché è l'unica informazione che cambia il momento in cui si decide.

*«Quando non serve» si scrive, e si dichiara che il manuale non lo dice.* La sezione è necessaria —
è la domanda vera del pubblico — ma la fonte non la copre: la pagina d'ingresso del manuale non
contiene nessuna soglia, nessuna dimensione minima, nessuna sconsiglio circostanziato
([S-069](Sources.md#s-069), «cosa non afferma»). Quello che il manuale offre è il prezzo dichiarato,
«the trade-off is increased complexity in infrastructure and maintenance», e il resto è un giudizio
di chi scrive, tratto dai numeri dei tre stack di questo repository. Va detto in quei termini, non
attribuito a MongoDB.

*La chiave sbagliata si mostra con i numeri di una prova, non con un avvertimento.* Ventimila
documenti, chiave `{_id: 1}`, e **ventimila su uno dei due shard**; poi la stessa collezione con la
sola chiave cambiata, e 9860 contro 10140 ([V-061](Sources.md#v-061)). Il pezzo che vale la slide
non è però lo squilibrio: è che `sh.balancerCollectionStatus()` su quella collezione risponde
`balancerCompliant: true`. **Il cluster considera bilanciata una distribuzione cento a zero**, e ha
ragione, perché la differenza è sotto la soglia. L'errore non ha sintomo, e lo strumento che
dovrebbe accorgersene conferma che va tutto bene.

*Il balancer si racconta con la sua soglia, e con il fatto che qui non entra mai in scena.* Gira sul
primario dei config server e non su `mongos` ([S-070](Sources.md#s-070)), è acceso da solo, e si
muove solo quando la differenza fra due shard supera tre volte la dimensione di range configurata —
384 MB con i 128 predefiniti. Nella demo la differenza è di **34 KB**, e il registro del cluster
riporta **zero** migrazioni su sei eventi totali ([V-061](Sources.md#v-061)). I quattro chunk sono
opera di `shardCollection()` su collezione vuota, non del balancer. Dire «il balancer bilancia» a
proposito di questa demo sarebbe una didascalia falsa su una fotografia vera.

*La trappola dell'`insertMany` ordinato entra nella pagina, perché è quella che capita davvero.*
Con chiave hashed un lotto `ordered: true` — che è il **predefinito** — costa fra venti e trenta
volte un lotto `ordered: false`, mentre con chiave monotona le due forme costano uguale
([V-061](Sources.md#v-061), [S-071](Sources.md#s-071)). È il difetto più insidioso dei tre, perché
colpisce chi ha fatto la scelta **giusta**: distribuisci bene, non tocchi il codice di caricamento
che funzionava, e le scritture rallentano di un ordine di grandezza senza un errore. Il seed del lab
scrive `ordered: false` dal primo giorno, per allineamento con gli altri due stack; oggi si sa
perché era la riga giusta.

*Ogni numero porta la sua riserva addosso, sulla stessa riga.* Come in [ADR-0046](#adr-0046) per il
replica set: il 49,3 / 50,7 è questo dataset con questo seme; il fattore venticinque è due shard e
documenti da 121 byte; la soglia dei 384 MB non è mai stata superata, quindi è provato che sotto il
balancer sta fermo e non che sopra si muova. Le riserve stanno accanto ai numeri, non in fondo,
perché in fondo non arrivano sulle slide.

*Il file Compose non si ripete riga per riga.* La pagina del replica set lo fa e fa bene, perché lì
il file è il soggetto. Qui il file è commentato per esteso, i suoi sei anelli sono già raccontati in
[ADR-0062](#adr-0062) e [ADR-0065](#adr-0065), e ripeterli raddoppierebbe la pagina spostando
l'attenzione dalla decisione che conta. Restano nella pagina i due punti che si capiscono solo
guardando il file: la catena che rende onesto `up --wait`, e il difetto del dbpath dei config server
([ADR-0067](#adr-0067)), che è la storia migliore che questo branch abbia prodotto.

**Conseguenze.** Nasce `docs/02-architetture/sharded-cluster.md`. In `docs/README.md` la riga passa
da promessa a collegamento, e con essa si chiude l'ultima delle tre pagine di architettura previste
dal design. Entrano tre fonti nuove — [S-069](Sources.md#s-069), [S-070](Sources.md#s-070),
[S-071](Sources.md#s-071) — e una verifica, [V-061](Sources.md#v-061). Due frasi vanno in
`docs/citazioni-riportare-slide.md`, e sono le due che il Blocco 3 può reggere da solo se il tempo
stringe.

Resta dichiarato nella sezione «cosa questa pagina non dice» tutto ciò che non è stato misurato:
zone, resharding, chunk jumbo, il comportamento **oltre** la soglia del balancer, il confronto di
prestazioni fra le tre architetture — che ha senso solo sotto carico controllato, cioè con
l'applicazione di `feature/04` — e `analyzeShardKey`, che sarebbe lo strumento giusto in un caso
vero e che richiede query reali.

**Alternative scartate:** descrivere la chiave sbagliata citando le fonti e basta — ci sarebbero
volute due ore in meno e la pagina avrebbe detto «attenzione alle chiavi monotone», che è
esattamente il genere di frase che si dimentica uscendo dalla sala; mostrare lo squilibrio senza
`balancerCompliant: true` — sarebbe il difetto senza la parte che lo rende pericoloso, cioè il
silenzio; raccontare il balancer come se lavorasse, perché è quello che il pubblico si aspetta — è
una bugia comoda e questa è la pagina sbagliata dove dirla; rimandare la trappola dell'`ordered` a
`feature/04`, dove ci sarà un'applicazione che scrive — il numero c'è adesso, e un difetto che
colpisce chi ha scelto bene non si tiene in un cassetto per due settimane.

**Fonti:** [S-066](Sources.md#s-066) · [S-067](Sources.md#s-067) · [S-069](Sources.md#s-069) · [S-070](Sources.md#s-070) · [S-071](Sources.md#s-071) · [V-058](Sources.md#v-058) · [V-061](Sources.md#v-061)

---

<a id="adr-0069"></a>
## ADR-0069 — Il balancer entra in scena, e la pagina di ieri va corretta: la fusione non è una migrazione

**Data:** 2026-09-02 · **Stato:** Accettata · **Corregge:** [ADR-0068](#adr-0068)

**Contesto.** Il Task 9 chiude i debiti marcati eseguendoli, e [ADR-0049](#adr-0049) avverte che
l'esecuzione trova righe sbagliate: la prima volta che è stata applicata ne ha trovate due. Questa
volta la prima riga sbagliata è saltata fuori **prima** di arrivare al debito, riaccendendo lo stack.

`sh.status()` mostrava **due** chunk su `lab.ordini`. [V-061](Sources.md#v-061), poche ore prima, ne
aveva contati **quattro**, e su quel numero è costruita la sezione 4 di
`docs/02-architetture/sharded-cluster.md`. Nessuno aveva inserito, cancellato o spostato niente: fra
le due misure c'era solo un `make down-03` e un `make up-03`, che conservano i volumi.

[V-062](Sources.md#v-062) ha trovato la ragione nel registro del cluster: due eventi `merge`, alle
`12:34:16.530Z` e alle `12:34:31.450Z`, **3,8 secondi dopo l'avvio del config server** e sei secondi
prima che il router esistesse. Il campo `server` di tutti e due dice `cfg1:27017`. La spiegazione è
l'**AutoMerger**, che [S-070](Sources.md#s-070) non nomina e che [S-072](Sources.md#s-072) descrive:
«Starting in MongoDB 7.0, the balancer can automatically merge chunks that meet the mergeability
requirements», e «unless explicitly disabled, the AutoMerger **starts the first time the balancer is
enabled**».

**Decisione.**

*La frase «il balancer non entra mai in scena» è falsa e si corregge, non si sfuma.* Stava nella
pagina, in [ADR-0068](#adr-0068) e nella riga dell'indice, ed è smentita da un evento registrato con
data, ora e nodo. La pagina la sostituisce con quella vera, che è più interessante: **il balancer di
una 7.0 fa due mestieri, e nel lab ne esercita esattamente uno.** Non migra mai — la differenza fra i
due shard è 34 409 byte contro una soglia di 384 MB — e intanto fonde, perché la fusione non ha
soglia di squilibrio: ha condizioni di età.

*L'errore da nominare è l'identificazione, non il numero.* Quattro chunk erano quattro davvero, e due
sono due davvero: [V-062](Sources.md#v-062) mostra che il fenomeno ha due fasi e che le due misure
guardano fasi diverse. Lo sbaglio non è stato contare male, è stato **assumere che «balancer» e
«migrazione» fossero la stessa parola** — un'assunzione che il manuale non autorizza e che la pagina
del balancer, parlando quasi solo di migrazioni, incoraggia. È il tipo di errore che nessuna rilettura
avrebbe preso, perché il testo era coerente con sé stesso.

*La sezione 4 della pagina si riscrive attorno alla nuova sequenza, e ci guadagna.* Prima diceva: i
quattro chunk sono geometria di `shardCollection()`, e poi non succede più niente. Adesso dice che i
quattro chunk sono geometria, che restano quattro finché il cluster non viene riavviato, e che al
primo giro del balancer diventano due — perché due coppie contigue sullo stesso shard sono
«mergeable» e il confine fra i due shard non lo è. È una storia con un prima e un dopo, ed è più
facile da mostrare dal vivo di una fotografia ferma: **basta un `make down-03 && make up-03`.**

*Il numero dei chunk esce dalle frasi in cui era un dato di fatto.* Dove serviva «quattro», adesso
serve «quattro appena distribuita, due dopo il primo riavvio», e dove la cifra non aggiungeva niente
sparisce. Lo stesso vale per la riga dell'indice, che vendeva la pagina con «il balancer che non entra
mai in scena»: è la prima cosa che un lettore legge, e prometteva il falso.

*`sh.stopBalancer()` va raccontato per quello che fa davvero.* Dalla 7.0 spegne **anche**
l'AutoMerger ([S-073](Sources.md#s-073)), cioè in questo laboratorio spegne l'unica cosa che il
balancer stia facendo. Un comando il cui nome descrive metà del proprio effetto merita una riga sia
nella pagina dell'architettura sia nella guida a `mongosh`.

*[ADR-0068](#adr-0068) non si riscrive.* Resta com'è, con la sua data, e questa decisione lo corregge
per intero sul punto del balancer: la regola del repository è che una decisione si supera, non si
emenda ([ADR-0002](#adr-0002)). Lo stesso vale per [V-061](Sources.md#v-061), che registra ciò che è
stato misurato in quella finestra: ha ricevuto una **riserva aggiunta**, non una modifica dei numeri.

**Conseguenze.** Cambiano `docs/02-architetture/sharded-cluster.md` (sezione 4, l'apertura della 4.3,
la voce di «cosa questa pagina non dice» sul balancer), la riga 70 di `docs/README.md` e
`tools/smoke-sharded.sh`, che verificava un'uguaglianza a quattro e adesso verifica un pavimento —
almeno un chunk per shard, con quattro e due riconosciuti per nome. Entrano due
fonti — [S-072](Sources.md#s-072) e [S-073](Sources.md#s-073) — e due verifiche,
[V-062](Sources.md#v-062) e [V-063](Sources.md#v-063). [V-061](Sources.md#v-061) prende una riserva
in coda.

Il talk ci guadagna una scena che prima non c'era, e che costa un comando: distribuire, contare
quattro, spegnere, riaccendere, contare due. Se il tempo del Blocco 3 non la regge, è la prima da
tagliare — ma sta scritta ([feedback dal vivo a parte](00-progetto/2026-08-24-design.md)).

**Alternative scartate:** lasciare la frase e aggiungere una nota a piè di pagina — sarebbe stato un
modo di avere ragione senza correggersi, e la frase sbagliata è nel titolo di una sezione e nella
riga dell'indice, cioè nei due punti che si leggono per primi; dire «il balancer non migra mai» e
tacere la fusione — vero e reticente insieme, e taciuto proprio il pezzo che si può mostrare dal
vivo; rifare la misura sperando che i quattro chunk tornassero — sarebbe stato aspettare che il
laboratorio confermasse la pagina invece del contrario; attribuire la fusione al riavvio senza
provarlo — è la [riserva **b**](Sources.md#v-062) di V-062, e resta una riserva.

**Fonti:** [S-070](Sources.md#s-070) · [S-072](Sources.md#s-072) · [S-073](Sources.md#s-073) · [V-061](Sources.md#v-061) · [V-062](Sources.md#v-062) · [V-063](Sources.md#v-063)

---

<a id="adr-0070"></a>
## ADR-0070 — I debiti dello sharded, saldati eseguendo: quattro marcature tolte, e quello che togliendole si è visto

**Data:** 2026-09-02 · **Stato:** Accettata

> **Nota di allineamento, 2026-09-02.** Il resto di questo ADR regge intatto. Il solo punto superato
> è quello che lasciava l'eccezione localhost aperta sugli shard: il Product Owner ha scelto di
> creare l'amministratore per shard, e come lo si è fatto è in [ADR-0071](#adr-0071). Il corpo non
> viene toccato: si legge com'era, con questo rimando davanti.

**Contesto.** Il Task 9 del piano di `feature/03` non aggiunge funzioni: chiude i debiti che le
pagine si portano scritti addosso. La regola è [ADR-0049](#adr-0049) — un debito si chiude
**eseguendo** — e la prima volta che è stata applicata l'esecuzione ha rivelato due righe sbagliate.
È successo di nuovo, e prima ancora di arrivare ai debiti: la fusione dei chunk, che è
[ADR-0069](#adr-0069).

Le marcature da togliere erano quattro, ciascuna con un indirizzo: la §3.3 di
[`guida-mongosh.md`](04-mongosh/guida-mongosh.md), dichiarata **non eseguita** per intero; gli
utenti locali a uno shard in [`sicurezza-keyfile-x509.md`](03-amministrazione/sicurezza-keyfile-x509.md),
marcati «mai provato»; `--oplog` sullo sharded cluster in
[`backup-restore.md`](03-amministrazione/backup-restore.md), che [S-011](Sources.md#s-011) vieta e
che nessuno aveva visto vietare; le trappole dei config server e del bilanciamento, che
[ADR-0033](#adr-0033) intesta per nome a questo branch. Più la riga 55 del `README` alla radice, che
diceva `docker/03-sharded` «in lavorazione».

L'esecuzione ha trovato quattro cose che nessuna rilettura avrebbe trovato. La guida documentava
l'errore **sbagliato**: `sh.status()` su un nodo di shard non risponde
`MongoshInvalidInputError: This db does not have sharding enabled` — quello è lo standalone — ma un
avviso `[SHAPI-10003]` seguito da `MongoServerError: not authorized on config to execute command`
([V-063](Sources.md#v-063)). L'eccezione localhost si è rivelata aperta **su ogni shard**, e
raggiungibile da un container che ne condivida la rete senza mai leggere il keyfile
([V-064](Sources.md#v-064)). `mongodump --oplog` ha **due** messaggi di rifiuto, e quello che si
incontra per primo non nomina `mongos` ([V-065](Sources.md#v-065)). E il `mongorestore` che riporta
ventimila documenti senza un errore lascia la collezione **non distribuita**.

**Decisione.**

*Una marcatura si toglie mostrando la misura, mai perché il debito è invecchiato.* Ogni riga
«non eseguito» cancellata in questo task ha dietro una verifica numerata — [V-063](Sources.md#v-063),
[V-064](Sources.md#v-064), [V-065](Sources.md#v-065) — e ciò che le pagine dicono adesso è ciò che è
uscito dal terminale. Dove l'esecuzione ha smentito la pagina, la pagina cambia nel corpo del testo:
la §3.3 apre dichiarando che l'errore che documentava era di un'altra architettura, invece di
correggerlo in silenzio.

*L'eccezione localhost sugli shard resta aperta in questo laboratorio, e la pagina lo dice a voce
alta.* La documentazione prescrive un dovere — creato l'amministratore dal `mongos`, «you **must**
still prevent unauthorized access to the individual shards» ([S-074](Sources.md#s-074)) — e questo
stack non lo adempie. Le ragioni sono due, e sono di questo contesto, non generali: le porte
pubblicate sull'host **non** aprono l'eccezione, perché a `mongod` la connessione arriva dal gateway
di Docker, quindi la sola via è condividere la rete di un container, che richiede accesso al demone
Docker — e chi ce l'ha può già leggere il volume del keyfile, cioè ha di più; e i due rimedi
possibili costano l'inizializzazione dello stack, perché `enableLocalhostAuthBypass=0` sugli shard
impedisce a `rs.initiate()` di partire. **Questo punto è una scelta di laboratorio, reversibile, e
va rivista se il cluster esce di qui:** la strada corretta fuori dal lab — un amministratore sul
primario di ogni shard, oppure il parametro a `0` applicato *dopo* l'inizializzazione — è scritta
nella pagina e resta un debito aperto e indirizzato, non un fatto taciuto.

*Il divieto di `--oplog` si racconta con tutte e due le sue facce, in quest'ordine.* La pagina
mostra prima `can't use --oplog option when dumping from a mongos`, che è la regola, e poi
`bad option: --oplog mode only supported on full dumps`, che è ciò che si incontra davvero se si è
sbagliato anche `--db`. Tacere il secondo sarebbe stato più ordinato e meno utile: manda a togliere
`--db`, che non è il problema.

*Il restore che non ridistribuisce entra nelle pagine come trappola, non come nota.* Ventimila
documenti ripristinati, zero errori, l'indice `_id_hashed` ricreato, e la collezione su un solo
shard. È il caso peggiore per un lettore — nessun segnale — e per questo sta nel corpo della §6 di
`backup-restore.md` con il conteggio a fianco.

*Le trappole nuove si aggiungono in coda, e le diciotto esistenti non si toccano.* Numerazione
stabile, come vuole [ADR-0033](#adr-0033). Entrano le voci **19** (il config server che scrive in un
volume anonimo), **20** (i chunk che da quattro diventano due) e **21** (l'eccezione localhost shard
per shard). La 19 e la 20 sono i due nomi che ADR-0033 aveva scritto in anticipo; la 21 entra per
[ADR-0052](#adr-0052), che ammette una trappola già misurata anche quando il piano non la nominava.

*Il `README` dichiara lo stack nel repository, e non promette l'applicazione.* La riga 55 passa a
«nel repository» come le due sopra; la riga che dice l'applicazione Python «in lavorazione» resta
intatta, perché è vera fino a `feature/04` e cancellarla qui trasformerebbe il `README` in una
promessa.

*Quello che resta non eseguito resta dichiarato tale* ([ADR-0037](#adr-0037)). Sopravvivono, marcati:
`sh.disableBalancing()` e `sh.enableBalancing()` nella guida; i secondari degli shard, provati solo
sui primari; il restore preceduto da `sh.shardCollection()`, che è dedotto e non misurato; gli
«extra steps» che [S-060](Sources.md#s-060) attribuisce al backup di un cluster e non elenca; il
backup dei config server. Un debito saldato che ne lascia scoperti cinque nuovi non è un fallimento
del task: è il task che ha guardato più da vicino.

**Conseguenze.** Cambiano quattro pagine e il `README` alla radice:
`docs/04-mongosh/guida-mongosh.md` (§3.3 riscritta, l'apertura della §3),
`docs/03-amministrazione/sicurezza-keyfile-x509.md` (la nuova §4.1, e il debito diviso in due righe
più precise), `docs/03-amministrazione/backup-restore.md` (la nuova §6, con la vecchia §6
rinumerata a §7, e tre righe nuove fra ciò che non copre),
`docs/02-architetture/trappole-mongodb-in-docker.md` (voci 19-21, indice e chiusa),
`README.md` riga 55. Entrano una fonte — [S-074](Sources.md#s-074) — e tre verifiche,
[V-063](Sources.md#v-063), [V-064](Sources.md#v-064) e [V-065](Sources.md#v-065).
[S-006](Sources.md#s-006) chiude per misura la riserva aperta il 2026-08-25 sull'eccezione
localhost, e ne tiene aperta una bibliografica: che l'eccezione richieda il loopback è misurato qui,
e continua a non essere scritto in nessuna fonte primaria trovata.

Nessuna configurazione dello stack cambia: il Task 9 tocca documentazione, e l'unica riga di codice
che ha spostato è in [ADR-0069](#adr-0069). Il talk ci guadagna una scena — un container che diventa
amministratore di uno shard senza credenziali — e un avvertimento da dire a voce se il tempo lo
regge: il restore che sembra riuscito.

**Alternative scartate:** togliere le marcature dichiarando i debiti «superati dal branch» — è
esattamente il modo in cui un debito diventa una bugia, e [ADR-0049](#adr-0049) esiste per
impedirlo; creare l'amministratore per shard subito, senza discuterlo — sarebbe stata una modifica
alla sicurezza dello stack decisa da chi stava saldando un debito di documentazione, e la scelta
appartiene a chi risponde del laboratorio; scrivere solo il messaggio d'errore «giusto» di
`mongodump` — più pulito, e avrebbe lasciato il lettore a togliere `--db` per scoprire da solo il
resto; rimandare le trappole a un branch successivo perché lo sharded «ne prometterebbe di più» —
si sarebbe perso il momento in cui erano state misurate, che è la sola cosa che le rende scrivibili
([ADR-0052](#adr-0052)); rinumerare le trappole per raggrupparle per argomento — la numerazione è
un riferimento stabile citato da altre pagine, e riordinarla vale meno di quanto costa.

**Fonti:** [S-006](Sources.md#s-006) · [S-011](Sources.md#s-011) · [S-074](Sources.md#s-074) · [V-063](Sources.md#v-063) · [V-064](Sources.md#v-064) · [V-065](Sources.md#v-065)

---

<a id="adr-0071"></a>
## ADR-0071 — L'amministratore locale a ogni shard: l'obbligo del manuale, adempiuto, e le tre semplificazioni che restano di laboratorio

**Data:** 2026-09-02 · **Stato:** Accettata

**Contesto.** [ADR-0070](#adr-0070) ha lasciato una porta aperta e l'ha scritto: gli shard di questo
stack non hanno utenti, quindi l'eccezione localhost è aperta su ciascuno di essi per tutta la vita
del processo, e chiunque possa avviare un container nel loro *network namespace* diventa `root` di
uno shard senza presentare niente ([V-064](Sources.md#v-064)). La documentazione non lascia margini
su che cosa vada fatto — «you **must** still prevent unauthorized access to the individual shards»
([S-074](Sources.md#s-074)) — e ADR-0070 ha deciso di non decidere: la misura si pubblica, il rimedio
si propone, la scelta appartiene a chi risponde del laboratorio (nota di metodo 117). Il Product
Owner ha scelto, il 2026-09-02: si crea l'amministratore per shard, con l'eccezione localhost, per
questo laboratorio, e la documentazione deve dire ad alta voce che la forma automatica **non** va
riprodotta in produzione.

Prima di scrivere una riga è stata cercata la procedura canonica, ed è stata trovata: il tutorial di
autenticazione a keyfile su sharded cluster ([S-075](Sources.md#s-075)), passo 4 della creazione dei
replica set di shard, «Create the shard-local user administrator». La lettura ha spostato una
premessa che sembrava acquisita, e va detta subito perché cambia dove punta l'avvertenza.

**L'eccezione localhost non è la scorciatoia.** Il manuale crea quell'utente **usando proprio
l'eccezione localhost**, collegato al primario dello shard: «The localhost interface is only
available since no users have been created for the deployment. The localhost interface closes after
the creation of the first user.» È il solo modo di creare il primo utente su un nodo che pretende
autenticazione e non ha ancora nessuno da autenticare. Chi lo fa non devia dalla procedura: la
esegue. Le deviazioni di questo laboratorio sono altre tre, e sono quelle da segnalare.

**Decisione.**

*I due servizi `shard1-init` e `shard2-init` creano un amministratore locale sul primario del proprio
shard, subito dopo l'attesa dell'elezione e prima che `sh.addShard()` registri gli shard nel
cluster.* L'ordine è quello del manuale, e la ragione è scritta lì: «Executing them now ensures that
there are users available for each shard to perform shard-level maintenance»
([S-075](Sources.md#s-075)). Farlo dopo lascerebbe una finestra in cui lo shard è in piedi e non ha
utenti, che è esattamente la condizione che apre l'eccezione. L'attesa del primario, che c'era già
per `sh.addShard()`, adempie ora anche a «You must be connected to the primary to create users».

*Le tre semplificazioni sono dichiarate una per una, e nessuna delle tre va in produzione.* Sono
scritte in `docs/03-amministrazione/sicurezza-keyfile-x509.md` §4.2 accanto alla forma canonica, con
i comandi del manuale riportati per esteso. In breve: **una sola password** per l'amministratore del
cluster e per quelli dei due shard, dove il manuale vuole credenziali distinte; **letta da un file**
`.env` da uno script non presidiato, dove il manuale vuole `passwordPrompt()` e «random, long, and
complex»; **il ruolo `root`** invece del `userAdminAnyDatabase` del passo 4, e senza il secondo
utente `clusterAdmin` del passo 5.

*Il ruolo è `root`, e la ragione è misurata, non comoda.* [V-066](Sources.md#v-066) esito 5:
`userAdminAnyDatabase` non legge `lab.ordini`, ma si concede `root` da solo in un comando e subito
dopo la legge. Fra i due ruoli, su quel nodo, non c'è una barriera di privilegio — c'è un comando in
più. Con una password condivisa, scegliere il ruolo minimo avrebbe avuto l'aspetto della sicurezza
senza esserlo, e in cambio avrebbe reso impossibile la sola cosa per cui
[ADR-0026](#adr-0026) prevede questi utenti: «dove una demo debba ispezionare un singolo shard». La
scelta di `root` è dichiarata come deviazione, non presentata come buona pratica.

*Lo smoke test cambia invariante, e ne sorveglia una in più.* Il controllo che verificava che le
credenziali del cluster **non** aprissero uno shard ([V-058](Sources.md#v-058)) era vero e adesso è
falso per costruzione: al suo posto tre controlli. Che l'amministratore locale esista e sia locale —
un utente solo, e una fetta della collezione, non i ventimila documenti del cluster — e che
l'eccezione localhost sia chiusa **su tutti e due** gli shard, perché è una condizione di processo e
un nodo riavviato senza il suo init la riaprirebbe da solo. `make smoke-03` passa da 62 a 64
controlli.

*Quello che si guadagna e quello che si perde si scrivono insieme.* Si guadagna che l'attacco di
[V-064](Sources.md#v-064) non passa più: stesso container, stesso `127.0.0.1`, stesso comando, e la
risposta è `Unauthorized`. Si perde che le porte pubblicate degli shard — 27141 e 27151 nel profilo
`palco` — adesso **riconoscono una credenziale**, che è quella del cluster. Prima non c'era niente
da presentare loro. L'eccezione localhost non c'entra, quella via non l'ha mai aperta: cambia che
esiste un utente. Sul lab non sposta nulla, perché lo stack non va esposto fuori dalla macchina di
chi presenta ([ADR-0005](#adr-0005)); su una macchina esposta sarebbe la cosa da guardare per prima.

**Conseguenze.** Cambiano quattro file dello stack e quattro pagine.
`docker/03-sharded/init/11-shard-initiate.js` crea l'utente e porta in testa l'avvertenza;
`docker/03-sharded/compose.yaml` passa `UTENTE_AMMINISTRATORE` e `PASSWORD_AMMINISTRATORE` ai due
init, e il commento che diceva «Nessun `createUser` qui» dice adesso il contrario e perché;
`docker/03-sharded/.env.example` dichiara che la stessa password serve a quattro utenti;
`tools/smoke-sharded.sh` sostituisce un controllo con tre. In documentazione: la nuova §4.2 di
`sicurezza-keyfile-x509.md` con la procedura canonica per esteso, la trappola **21** di
`trappole-mongodb-in-docker.md` che cambia esito, e una fonte nuova
([S-075](Sources.md#s-075)) con la verifica che l'accompagna ([V-066](Sources.md#v-066)).

L'avvio non rallenta in modo percepibile: è un `createUser` per shard, in parallelo fra i due init.
Al secondo `up` i due init rispondono «già presente» e escono `0`, per il ramo `Unauthorized` — a
eccezione chiusa il nodo non arriva nemmeno a valutare se l'utente esista.

Resta aperto, e dichiarato: l'eccezione sui **secondari** di uno shard a tre membri, che il profilo
`palco` non ha; `enableLocalhostAuthBypass: 0` applicato **dopo** l'inizializzazione, che sarebbe il
secondo rimedio ammesso da [S-074](Sources.md#s-074) e che questo stack non prova; e lo stato
intermedio in cui uno solo dei due init fallisse.

**Alternative scartate:** lasciare l'eccezione aperta come decideva ADR-0070 — la scelta era del
Product Owner e il Product Owner ha scelto diversamente; `enableLocalhostAuthBypass: 0` sugli shard —
applicato prima dell'inizializzazione impedisce `rs.initiate()` e lo stack non parte
([V-064](Sources.md#v-064) riserva b), applicato dopo servirebbe un riavvio dentro la catena di
avvio, cioè un anello in più per ottenere quello che un `createUser` ottiene senza; usare
`userAdminAnyDatabase` come prescrive il passo 4 — è misurato che si concede `root` da solo, quindi
avrebbe l'aspetto della sicurezza e non la sostanza, e toglierebbe alla demo l'unica cosa che questi
utenti servono a fare; creare due utenti distinti come i passi 4 e 5 del manuale — con una sola
password nel `.env` sarebbero due nomi per la stessa chiave, cioè cerimonia; usare una password
diversa per gli shard — sarebbe più fedele al manuale e chiederebbe una seconda riga in `.env`, che
è il file che ADR-0056 racconta essere già stato perso una volta: il guadagno è simbolico finché la
prima password sta nello stesso file; creare l'utente **dopo** `sh.addShard()`, dove sarebbe stato
più comodo metterlo — lascia aperta la finestra che tutto questo ADR esiste per chiudere.

**Fonti:** [S-074](Sources.md#s-074) · [S-075](Sources.md#s-075) · [V-058](Sources.md#v-058) · [V-064](Sources.md#v-064) · [V-066](Sources.md#v-066)

---

<a id="adr-0072"></a>
## ADR-0072 — Le misure che una nostra decisione ha invalidato si riscrivono subito, e si dice quando la risposta nuova è più comoda e meno sincera

**Data:** 2026-09-02 · **Stato:** Accettata

**Contesto.** [ADR-0071](#adr-0071) ha dato un amministratore a ogni shard. Nello stesso giorno,
quattro punti di questo repository hanno cominciato a dire il falso: un commento in
`tools/reset-demo.sh`, uno in `docker/03-sharded/init/10-cfg-initiate.js`, due passaggi di
`docs/02-architetture/sharded-cluster.md` e un blocco `console` nella §3.3 di
`docs/04-mongosh/guida-mongosh.md`. Riportavano tutti una misura che era vera quando è stata presa,
e nessuno è stato invalidato da un aggiornamento di MongoDB: li ha invalidati una modifica nostra.

Rimisurarli ha portato a galla qualcosa che nessuno stava cercando ([V-067](Sources.md#v-067)). Il
cambiamento non ha scambiato un messaggio d'errore con un altro: ne ha tolto uno.
`sh.getBalancerState()` dato a uno shard rispondeva `Unauthorized: not authorized on config to
execute command …` — un errore che [V-063](Sources.md#v-063) aveva già giudicato reticente, «che non
nomina il problema vero», ma che almeno era un errore. Adesso risponde **`true`**. Le letture del
database `config` su uno shard riescono, tornano vuote, e il vuoto ha l'aspetto di una risposta.
Nello stesso movimento `sh.status()`, autenticato su uno shard, ha smesso di dire «non sei
autorizzato» e ha cominciato a dire `This db does not have sharding enabled`: cioè esattamente la
frase che la guida additava come sintomo di **un'altra** situazione. Il primo errore ne nascondeva un
secondo.

**Decisione.**

*Le pagine e i commenti che riportano una misura invalidata da una nostra decisione si riscrivono
sulla misura di oggi, dentro il lavoro che ha cambiato il comportamento.* Chi apre la guida alle
dieci di sera prima di una demo non deve datare quello che legge.

*La misura vecchia non si cancella: si data.* Va dove stanno le misure — nelle voci di `Sources.md`
che l'avevano registrata, con un «Seguito» che rimanda alla verifica nuova. [V-058](Sources.md#v-058)
e [V-063](Sources.md#v-063) restano leggibili come erano: è la regola di [ADR-0002](#adr-0002)
applicata alle verifiche invece che alle decisioni.

*Dove la risposta nuova è più pericolosa della vecchia, la pagina lo dice.* Un `true` al posto di un
errore non è un miglioramento raccontato male: è un segnale perso, e a perderlo siamo stati noi
chiudendo l'eccezione localhost. Una pagina che si limitasse ad aggiornare l'output sarebbe esatta e
lascerebbe il lettore peggio di prima.

**Conseguenze.** I quattro punti sono riscritti. La §3.3 della guida guadagna la regola che li tiene
insieme — le funzioni di `sh` che si risolvono in una lettura di `config` adesso rispondono il vuoto,
quelle che spediscono un comando falliscono ancora — perché è quella, e non l'elenco dei messaggi,
che sopravvive al prossimo cambiamento. Resta un obbligo pratico per le decisioni future: quando una
decisione cambia un comportamento misurato, il testo dei messaggi vecchi si cerca nel repository
prima di chiudere il commit. Qui la ricerca è stata fatta dopo, ed è per questo che i quattro punti
sono vissuti falsi per un commit.

Due categorie di documenti **non** rientrano in questa regola, e non per pigrizia. I verbali datati
di `docs/00-progetto/` — lo spike del 2026-08-25, il piano, il registro operativo — dicono che cosa
è stato misurato in un giorno, e riscriverli cancellerebbe proprio l'informazione che portano. Le
sezioni di pagina già marcate con la loro data lo stesso: la §4.1 di
`docs/03-amministrazione/sicurezza-keyfile-x509.md` apre con un riquadro che la dichiara anteriore
al 2026-09-02 e rimanda alla §4.2, ed è la forma corretta quando la misura vecchia **serve** a
spiegare perché la nuova esiste.

**Alternative scartate:** tenere le due letture affiancate nella pagina, «prima di ADR-0071» e
«dopo» — la guida diventerebbe un registro delle modifiche, e §3.3 è già una sezione che il lettore
percorre in cerca di un comando, non di una cronologia; annotare i punti con una nota senza toccare
il testo — chi legge in diagonale legge il testo, non la nota; aprire una trappola nuova in
`trappole-mongodb-in-docker.md` per il `true` del bilanciatore — la trappola 21 racconta già
l'eccezione localhost, e §3.3 è il posto dove quel comando si impara; lasciare i quattro punti come
erano e correggerli a fine feature, con il resto della documentazione — sono quattro affermazioni
false in un repository didattico, e il costo di rimandarle è che qualcuno le legga nel frattempo.

**Fonti:** [V-058](Sources.md#v-058) · [V-063](Sources.md#v-063) · [V-067](Sources.md#v-067)

---

<a id="adr-0073"></a>
## ADR-0073 — Una scena di riserva è l'uscita di un comando del repository, e misura invece di raccontare

**Data:** 2026-09-02 · **Stato:** Accettata

**Contesto.** Il Blocco 3 doveva avere la sua riserva registrata: l'avvio, `sh.status()`, la
distribuzione dei documenti e il guasto di un membro di shard. Per il Blocco 2 la cosa era già
risolta senza che nessuno l'avesse decisa: le scene erano `make failover-02` e le sue varianti,
cioè comandi che esistevano per la sala e che registrare è costato una riga. Per lo sharded no.
`sh.status()`, il conteggio shard per shard e la sequenza del guasto non erano comandi: erano
gesti, da battere dentro `docker exec` uno dopo l'altro.

Registrare una sequenza battuta a mano produce un artefatto che nessuno saprà rifare uguale. Il
`.cast` resta nel repository, il gesto no: chi lo rivede fra tre mesi non ha modo di sapere quali
`--eval` erano stati dati né in che ordine, e quando lo stack cambia niente segnala che la
registrazione è invecchiata. È lo stesso motivo per cui i controlli di questo repository eseguono
invece di dichiarare ([ADR-0038](#adr-0038)).

**Decisione.**

*Ogni scena di riserva è l'uscita di un comando che sta nel repository.* Nasce
`tools/demo-sharded.sh` con tre scene — `stato`, `distribuzione`, `guasto` — e tre bersagli nel
`Makefile`: `stato-03`, `distribuzione-03`, `guasto-03`. Il comando è per la sala **prima** che per
la registrazione: se in sala il cluster parte lo si esegue, se non parte si riproduce il `.cast`, e
le due strade mostrano le stesse parole. Una riserva che dice cose diverse dalla demo è una seconda
demo da mantenere.

*Una scena misura, non racconta.* Nessun numero è scritto nel copione: quanti membri ha ogni shard
lo chiede allo shard, i due `_id` da cercare li chiede ai due shard invece di indovinarli, i secondi
di ogni risposta li cronometra, e il nuovo primario dopo il guasto lo legge da un membro superstite
invece di affermare che c'è stata un'elezione. Il costo è qualche riga in più; il ritorno è che la
scena resta vera quando cambiano la chiave di sharding, il numero di membri o i tempi della
macchina — e che quando smette di essere vera lo dice da sola.

*Il bersaglio si chiama `guasto-03`, non `failover-03`.* Nel profilo `palco` ogni shard ha un
membro solo: un failover lì non può avvenire, e chiamarlo così prometterebbe al pubblico una scena
che non arriva. Il nome dice il gesto — si ferma un nodo — e lascia all'esito il compito di dire
che cosa succede, che nei due profili è il contrario.

*Una scena che rompe qualcosa lo rimette a posto, anche se la interrompono.* `guasto-03` riavvia il
nodo che ha fermato e installa una trappola su `INT` e `TERM` per riavviarlo anche se chi guarda
preme `Ctrl-C` a metà. Una demo che lascia il cluster peggio di come l'ha trovato non si può
provare due volte di seguito, che è esattamente quello che si fa prima di un talk.

**Conseguenze.** Il Task 10 esce dal perimetro che il piano gli aveva dato — `docs/05-talk/registrazioni/`
— e tocca `tools/` e il `Makefile`; la deviazione è scritta nel registro operativo, il piano
approvato non si modifica. Le cinque scene stanno in
[`docs/05-talk/registrazioni/`](05-talk/registrazioni/README.md) con le loro misure
([V-068](Sources.md#v-068)), e ognuna è stata riprodotta per intero prima di entrare nell'indice
([ADR-0055](#adr-0055)); per le cinque dello sharded il confronto è stato anche byte per byte.

Il debito «il `Makefile` non sa niente dei profili», aperto da [ADR-0049](#adr-0049) e ancora da
saldare, adesso riguarda tre bersagli in più: `stato-03`, `distribuzione-03` e `guasto-03` accettano
`PROFILO` e nessun controllo verifica che i valori ammessi siano quelli dei file Compose. Si chiude
nel task di chiusura del branch, eseguendo.

Resta un passaggio che nessun controllo può sorvegliare: la scena 9 richiede che in
`docker/03-sharded/.env` siano attive le righe `MEMBRI_*` a tre membri. Quel file non sta nel
repository ([ADR-0014](#adr-0014)), quindi chi rifà le registrazioni deve scambiarle a mano e
rimetterle a posto dopo — e se non lo fa, il profilo `palco` non riparte. Sta scritto nell'indice
delle registrazioni, che è il posto dove lo si legge nel momento in cui serve.

**Alternative scartate.** Battere le scene a mano dentro `docker exec` e registrarle — è quello che
questa decisione rifiuta, e sarebbe costato meno oggi e molto di più a ogni modifica dello stack.
Un unico bersaglio `demo-03` che esegue le tre scene di fila — in sala non si interrompe una scena
da settanta secondi per rispondere a una domanda, e le tre servono in momenti diversi del blocco.
Chiamare `failover-03` la scena del guasto perché nel profilo `completo` è davvero un failover — il
nome di un comando non può essere vero solo in una delle due configurazioni che il repository
dichiara di supportare.

**Fonti:** [V-045](Sources.md#v-045) · [V-068](Sources.md#v-068)

---

<a id="adr-0074"></a>
## ADR-0074 — Due file che devono dire la stessa cosa si legano con un test, e l'elenco valido lo tiene chi lo dichiara

**Data:** 2026-09-02 · **Stato:** Accettata

**Contesto.** Due debiti aperti da [ADR-0049](#adr-0049) e rinviati fin qui hanno la stessa forma, e
si è capito solo misurandoli.

Il primo: l'elenco `PORTE=(...)` di `tools/preflight.sh` è scritto a mano, e i file Compose
pubblicano le loro porte per conto proprio. Il secondo: `PROFILO` è una variabile del `Makefile` e i
profili sono dichiarati nel file Compose, e niente lega le due cose — segnato una prima volta da
[ADR-0066](#adr-0066), aggravato dal Task 10 che ha aggiunto tre bersagli con `PROFILO`
([ADR-0073](#adr-0073)).

Misurati oggi, **nessuno dei due era in errore** ([V-069](Sources.md#v-069)): quindici porte
pubblicate e quindici controllate, senza mancanti, senza eccedenti, in ordine. Il debito non era uno
sbaglio: era che la coincidenza reggeva **per attenzione**, e sette delle quindici porte esistono
solo nel profilo `completo`, cioè sono esattamente quelle che si dimenticano.

Il secondo debito ha invece una manifestazione precisa, e brutta. Compose accetta qualunque stringa
dopo `--profile` senza protestare: un profilo che non esiste non seleziona niente, quindi restano i
soli servizi che non dichiarano `profiles:` — qui uno, `keyfile-init`. `make up-03
PROFILO=inesistente` stampa cinque righe, muore con `container sh-keyfile-init exited (0)` e esce 2.
Accusa il one-shot del keyfile di essere uscito 0, cioè di aver fatto il suo mestiere, e la parola
«profilo» non compare da nessuna parte. Un refuso in `PROFILO=complteo` manda a leggere i log del
keyfile.

**Decisione.**

1. **Un guardiano `profilo-03` che chiede l'elenco al file Compose.** `docker compose … config
   --profiles` è la domanda giusta e ha una risposta pulita — `completo`, `palco`, uscita 0 — purché
   le si passino i due `--env-file`, senza i quali fallisce sull'interpolazione di `MONGO_IMAGE`. Il
   guardiano è un bersaglio `.PHONY` che rifiuta un profilo sconosciuto con una frase che lo nomina,
   elenca quelli veri e dice che cosa succederebbe senza il controllo.

2. **L'elenco dei profili validi non si scrive nel `Makefile`.** Scrivere `palco|completo` nella
   ricetta sarebbe stato il debito di prima con un nome nuovo: un terzo profilo nel file Compose
   resterebbe rifiutato, e il messaggio d'errore direbbe con sicurezza una cosa falsa. È la stessa
   ragione per cui `DATI_03` si costruisce con `addprefix` invece che con nove nomi a mano, e una
   prova la difende esplicitamente.

3. **Ogni bersaglio che usa `$(PROFILO)` dichiara il guardiano fra i prerequisiti** — oggi sono
   sette: `up-03`, `seed-03`, `smoke-03`, `reset-demo-03`, `stato-03`, `distribuzione-03`,
   `guasto-03`. I tre che non avevano nemmeno `$(AMBIENTE_03)` lo acquisiscono per transitività, ed
   è giusto: leggono comunque quel file.

4. **Le coerenze fra due file diventano una prova che legge i file veri.** Nasce
   `tools/tests/test_coerenza_repo.py`, che è il primo modulo della suite a non usare campioni
   costruiti: apre i tre `docker/*/compose.yaml`, `tools/preflight.sh` e il `Makefile` così come
   sono nel repository. Controlla i due versi delle porte, l'ordine e i doppioni, che nessun
   bersaglio con `$(PROFILO)` scordi il guardiano, e che il guardiano non nomini un profilo a mano.

5. **Le porte si leggono con un lettore YAML e non con `docker compose config`.** Quel comando
   pretende i `.env` che stanno fuori dal repository per scelta ([ADR-0014](#adr-0014)): un
   controllo che non gira su un clone appena fatto è un controllo che non gira. Il lettore risolve
   `${NOME:-valore}` con il valore predefinito, che è la porta della mappa del design.

**Conseguenze.** La suite passa da 131 a **139** prove. Le tre mutazioni provate a mano — togliere
27017 dall'elenco, togliere il guardiano a `guasto-03`, sostituire `$(PROFILO)` con `palco` nella
ricetta del guardiano — falliscono tutte e tre con il messaggio che dice quale file correggere:
una prova che non può fallire non vale niente, e queste sono state viste fallire.

Il costo è che `profilo-03` esegue un `docker compose config` prima di ogni `up-03`, `smoke-03`,
`stato-03` e degli altri quattro. Sono decimi di secondo su comandi che ne durano decine, e in
cambio un refuso si ferma **prima** di toccare il cluster: nella prova, i cinque container accesi in
`palco` non sono stati sfiorati dal tentativo con il profilo sbagliato.

Resta scoperto quello che nessuna prova statica può vedere: che le porte *dichiarate* siano quelle
che il design §5.2 voleva. La prova lega due file fra loro, non li lega alla specifica. Se qualcuno
spostasse una porta in un file Compose e aggiornasse `preflight.sh`, i controlli tacerebbero — ed è
il comportamento giusto, perché quella è una modifica legittima che va discussa altrove.

**Alternative scartate.** Generare `PORTE` dai file Compose a ogni esecuzione di `preflight.sh` —
`preflight` deve girare la mattina del talk sulla macchina più scarna possibile, e farlo dipendere
da un lettore YAML e da Python per sapere quali porte guardare è aggiungere modi di fallire proprio
lì. Una prova che confronta `preflight.sh` con la specifica invece che con i Compose — la specifica
è prosa, e un controllo che la interpreta è un controllo che discute. Un bersaglio `up-03-palco` e
uno `up-03-completo` invece della variabile — è la strada che [ADR-0066](#adr-0066) ha già scartata,
e rinunciarvi adesso significherebbe due famiglie di sette bersagli. Lasciare che sia lo smoke a
scoprire il profilo sbagliato — lo smoke gira dopo l'avvio, e l'avvio è la cosa che era fallita.

**Fonti:** [V-069](Sources.md#v-069)

---

<a id="adr-0075"></a>
## ADR-0075 — Il secondo comando di `up-02` resta, e la ragione per cui regge entra nel file

**Data:** 2026-09-02 · **Stato:** Accettata

**Contesto.** [ADR-0062](#adr-0062) ha chiuso lo stack 03 con **un** comando di avvio e ha aperto,
nello stesso paragrafo, un debito verso lo stack 02: «`up-02` esegue proprio i due comandi, e
funziona perché `up --wait` torna **prima** che `rs-init` finisca. La distanza fra le due cose è di
secondi e nessuna misura dice quanto sia stabile altrove; se un giorno `rs-init` finisse per primo,
`wait rs-init` risponderebbe `no containers` e il bersaglio fallirebbe senza che niente sia rotto.»

Il debito era indirizzato al Task 7 e non è stato saldato lì. Lo si salda qui, e la misura
([V-069](Sources.md#v-069)) risponde più di quanto fosse stato chiesto.

Il margine c'è: **21,59 / 22,16 / 21,90 s** su tre avvii a freddo, e a caldo `wait rs-init` blocca
ancora **3,97 / 3,87 / 3,94 s**. Ma il dato che cambia la decisione non è la sua ampiezza: è che il
margine **non è un caso fortunato**. `rs-init` è l'ultimo anello della catena e non ha healthcheck,
quindi la soglia che `--wait` gli applica è `running` ([S-057](Sources.md#s-057)) ed è soddisfatta
nell'istante in cui parte. `up --wait` torna dunque quando `rs-init` **comincia**, e la finestra a
disposizione del secondo comando coincide con l'intera durata del suo lavoro. Non si restringe con
una macchina più veloce: si restringe solo se `rs-init` smette di fare qualcosa.

Il fallimento temuto esiste e si riproduce — dato `wait rs-init` a cose finite, la risposta è `no
containers for project "sqlstart-02-replicaset"` con uscita 1, mentre il progetto ha cinque
container e `ps -a` li elenca tutti — ma per raggiungerlo bisogna dare il comando fuori dal
bersaglio. Dentro il bersaglio non capita, perché `up -d --wait` riavvia `rs-init` a ogni giro:
verificato lanciando `make up-02` due volte di fila.

**Decisione.**

1. **`up-02` resta di due comandi**, e la regola di [ADR-0041](#adr-0041) non viene toccata. Il
   debito si chiude come *verificato*, non come *corretto*: non c'era niente da correggere.

2. **Il motivo per cui regge entra nel `Makefile`, accanto alla riga.** Il pericolo vero non era il
   tempo: era che qualcuno leggesse due comandi dove ne bastava uno e ne togliesse uno per pulizia.
   Il commento adesso dice che la finestra è la durata del lavoro di `rs-init` e che chi svuota
   `rs-init` deve togliere anche quella riga — cioè lega la fragilità alla modifica che la
   scatenerebbe, invece di lasciarla a una data futura.

3. **Non si dà a `rs-init` una sentinella come quella dello stack 03.** Sarebbe la soluzione
   simmetrica e strutturalmente più solida, ed è stata considerata sul serio: un anello finale senza
   healthcheck da cui non dipende nessuno renderebbe `up-02` di un comando come `up-03`. Ma
   modificherebbe un file Compose di uno stack chiuso, verificato e già registrato, dentro il task
   di chiusura di un branch che riguarda un altro stack. Il guadagno è togliere una riga che
   funziona; il costo è rifare le verifiche dello stack 02.

4. **I due stack restano diversi, e la differenza si spiega.** Non è un'incoerenza da sanare: è che
   lo stack 02 ha un one-shot finale che *lavora* e lo stack 03 una sentinella che *non fa niente*
   apposta ([ADR-0062](#adr-0062)). Chi legge i due `Makefile` accanto trova adesso scritto, in
   entrambi, perché il numero di comandi è quello.

**Conseguenze.** Il debito di [ADR-0062](#adr-0062) è saldato. Resta scritto che una modifica a
`rs-init` che lo rendesse istantaneo romperebbe `up-02` con un messaggio che nomina l'intero
progetto per dire che non trova un container: il messaggio più fuorviante incontrato in questo
branch, insieme a quello del keyfile accusato di uscire 0 ([ADR-0074](#adr-0074)). Sono lo stesso
difetto visto da due parti — uno strumento che risponde alla domanda che gli è stata fatta invece
che a quella che gli si voleva fare.

La misura ha richiesto di avviare lo stack 02 in un worktree dove il suo `.env` non esiste, perché
è fuori dal repository ([ADR-0014](#adr-0014)). Il file è stato copiato dal checkout principale per
la durata della prova e rimosso subito dopo, con lo stack smontato e i volumi dei dati cancellati:
una misura su un altro stack non deve lasciare tracce nel branch che la prende.

**Alternative scartate.** Togliere `wait rs-init` e affidarsi al solo `up --wait` — è precisamente
ciò che [ADR-0041](#adr-0041) ha scartato misurando, e il replica set non esisterebbe ancora al
ritorno del comando. Sostituirlo con una lettura del codice di uscita via `docker inspect` — toglie
la dipendenza dal container vivo, ma introduce il nome `rs-init` scritto a mano in un secondo posto
e sostituisce un comando di Compose con uno del client Docker, contro la direzione presa dal resto
del `Makefile`. Ingoiare l'errore con `|| true` — trasformerebbe un `rs-init` fallito in un avvio
riuscito, che è il verso sbagliato in cui sbagliare. Rimandare ancora il debito a `feature/04` — il
calendario di [ADR-0057](#adr-0057) non lo consente, e un debito rinviato due volte è un debito che
nessuno salderà.

**Fonti:** [V-069](Sources.md#v-069)

---

<a id="adr-0076"></a>
## ADR-0076 — Un nome di replica set vuoto è un nome assente, e un messaggio che dice «nessuno protesta» deve averlo verificato

**Data:** 2026-09-02 · **Stato:** Accettata

**Contesto.** La PR #4 è stata data in lettura a un recensore esterno, come le tre precedenti.
Dei due rilievi, uno riguarda `tools/check_stack.py`: «`nome_del_set()` può restituire una stringa
vuota se `--configdb` inizia con `/`, e a quel punto il chiamante la tratta come un nome di
replica set valido».

Arbitrato eseguendo ([V-070](Sources.md#v-070)), il rilievo si spacca in due. **L'osservazione è
esatta**: `nome_del_set('/cfg1:27017')` restituiva `''`, e con uno spazio davanti restituiva lo
spazio. **La diagnosi è sbagliata**: il chiamante non la trattava affatto come valida — il file
veniva bocciato lo stesso, con due problemi, e `check_stack.py` usciva diverso da zero. Non
esisteva il falso negativo che il rilievo lascia immaginare.

Il difetto però c'era, ed era peggiore di quello segnalato. Il messaggio che usciva diceva «nomina
il replica set «»» — non nomina niente — e soprattutto «è l'unico caso in cui nessuno protesta: i
processi partono tutti». Misurato: `mongos --configdb /cfg1:27017` **non parte**, esce 2 e
risponde `BadValue: configdb supports only replica set connection string`. Lo strumento mandava a
cercare un refuso di due lettere dentro i `--replSet` del file, mentre il difetto era una barra di
troppo in bella vista. È esattamente la forma d'errore già registrata dalla **nota di metodo 129**
e da [ADR-0072](#adr-0072): un messaggio vero alla lettera che risponde alla domanda sbagliata.

La misura ha trovato un secondo scostamento che nessuno aveva cercato. Il messaggio del
`--configdb` senza nome di set cita `FailedToParse: invalid url`, che [V-057](Sources.md#v-057)
aveva misurato — sulla forma con la **virgola**. Su un host solo, che è precisamente ciò che la
prova del repository esercitava, `mongos` risponde `BadValue: configdb supports only replica set
connection string`. La fonte era accurata; il messaggio la generalizzava.

**Decisione.**

1. **`nome_del_set` normalizza, e un nome vuoto è un nome assente.** Restituisce `None` per
   `/cfg1:27017` come per `cfg1:27017`, e lo spazio conta come vuoto. Le due scritture sono lo
   stesso errore — «`--configdb` non nomina un replica set» — e devono ricevere lo stesso
   messaggio.

2. **Il messaggio porta entrambe le stringhe misurate**, con la condizione che le distingue: la
   virgola. Un messaggio di `check_stack.py` cita il sintomo che l'utente vedrà, e citarne uno solo
   quando ce ne sono due è una promessa che l'utente scopre falsa nel momento peggiore.

3. **Un rilievo esterno si accoglie per l'osservazione, non per la diagnosi.** Qui accogliere il
   verdetto («è trattata come valida») avrebbe portato a cercare un falso negativo inesistente;
   respingere il rilievo perché il verdetto è falso avrebbe lasciato in piedi un messaggio che
   afferma il contrario di ciò che accade. Le due parti si separano eseguendo, e solo eseguendo.

4. **Le due prove nuove sono state viste fallire prima di essere accettate** (nota di metodo 131).
   Con il difetto rimesso al suo posto, la prima riporta per intero il messaggio del refuso e la
   seconda `assert '' is None`: la suite passa da 139 a **141**.

**Conseguenze.** `make stack-check` boccia esattamente gli stessi file di prima — la copertura non
cambia, e chi misurasse questa modifica contando gli stack respinti non troverebbe differenza. A
cambiare è che il file bocciato adesso dice dov'è il difetto. Resta scritto che [V-057](Sources.md#v-057)
è accurata e che a essere troppo larga era la sua citazione: una fonte misurata su un caso non
autorizza a parlare di tutti i casi della stessa famiglia.

**Alternative scartate.** Lasciare com'era, visto che nessun file passava per sbaglio — sarebbe
coerente solo se il valore di `check_stack.py` fosse il codice d'uscita, mentre è il messaggio:
un controllo che boccia senza saper dire perché costringe a rifare a mano il lavoro che dovrebbe
risparmiare. Far restituire a `nome_del_set` la stringa vuota e distinguere nel chiamante — sposta
la normalizzazione nel punto in cui il valore si usa invece che in quello in cui si produce, e
obbliga ogni futuro chiamante a ricordarsene. Aggiungere un terzo messaggio dedicato al nome vuoto
— tre messaggi per un errore che l'utente vede sempre nello stesso modo, e la prova avrebbe dovuto
distinguere due casi che `mongos` non distingue.

**Fonti:** [V-070](Sources.md#v-070)


---

<a id="adr-0077"></a>
## ADR-0077 — Il verdetto è il codice d'uscita: tre punti in cui la catena diceva «pronto» e non lo era

**Data:** 2026-09-02 · **Stato:** Accettata

**Contesto.** Dopo il recensore della [ADR-0076](#adr-0076), la PR #4 è stata data a un secondo,
con un incarico esplicito: uno sguardo indipendente, non una conferma del primo. Ha lasciato tre
rilievi. Arbitrati eseguendo, **tutti e tre descrivono un caso raggiungibile**, e nessuno dei tre
era stato immaginato scrivendo il codice.

Hanno in comune più di quanto sembri leggendoli separati. La PR promette in testata che «`make
up-03` è **un** comando e il suo codice d'uscita è il verdetto». Ciascuno dei tre è un punto in cui
quel verdetto è verde su uno stack che non fa quello che la pagina accanto promette — e in due casi
su tre l'avviso in italiano c'era già, stampato, letto da nessuno, perché `up --wait` legge i codici
e non le frasi.

**Primo rilievo — il router senza keyfile.** La regola che pretende `--keyFile` in
`tools/check_stack.py` vive dentro `if stack_con_replica and avvia_mongod(...)`, e un `mongos` non è
un `mongod`. Verificato su un file vero — una copia di `docker/03-sharded/compose.yaml` con
cancellate le sole due righe del keyfile del router — `check_stack.py` rispondeva «Stack conformi:
1» e usciva **0** ([V-071](Sources.md#v-071)). Avviato, quello stack esce **1** con «container
sh-mongos is unhealthy», e il log del router ripete `Command find requires authentication`: la frase
che si legge quando la password è sbagliata, mentre la password è giusta e manca una riga.

**Secondo rilievo — il cambio di profilo su uno stack già acceso.** Gli anelli di inizializzazione
saltano il lavoro se trovano il replica set già formato, e non guardano **con quali membri**.
[ADR-0060](#adr-0060) aveva previsto due direzioni di disallineamento fra `MEMBRI_*` e `--profile`,
e le sorveglia entrambe. Questa è una terza, che non viene dall'ambiente ma dal disco: su uno stack
inizializzato in `palco`, con `MEMBRI_CFG` portato a tre nomi, tutti e tre i container rispondono
(la prima guardia è contenta), nessun candidato è fuori elenco (la seconda pure), e il ramo che
salta fa il resto. Misurato: la catena stampa «config server pronto», esce **0**, e
`rs.status().members.length` vale **1** mentre due config server sani girano fuori dalla replica
([V-072](Sources.md#v-072)). È il guasto che ADR-0060 chiamava «il pericoloso, perché non
fallisce», entrato da una porta che quella guardia non sorvegliava.

**Terzo rilievo — il seed accetta qualunque ventimila.** Il caricamento dei dati si salta se
`lab.ordini` ha già `DOCUMENTI` documenti. Il conteggio però non dice se sono **distribuiti**.
Misurato su una collezione rifatta a mano, piena e senza riga in `config.collections`: il seed
stampa «ATTENZIONE: lab.ordini non risulta distribuita» ed esce **0** lo stesso. Un laboratorio
sullo sharding la cui collezione non è partizionata, consegnato verde.

**Decisione.**

1. **Anche il router dichiara `--keyFile`, e la regola sta accanto a quella del `mongod`, non
   dentro.** `check_stack.py` guadagna un `if stack_con_replica and avvia_mongos(...)` parallelo al
   precedente. Non è un `elif` e non è una condizione allargata: sono due anelli diversi della
   stessa catena, con due messaggi diversi, perché chi legge il rilievo deve sapere quale dei due
   sta guardando. Il messaggio porta per intero la stringa che il router stamperebbe, così chi la
   trova nei log per un'altra strada ci arriva cercandola.

2. **Un anello che trova il set già formato confronta i membri, e se differiscono si ferma.** Nuovo
   codice d'uscita **6** (`USCITA_MEMBRI_DIVERSI`) in `10-cfg-initiate.js` e in
   `11-shard-initiate.js`, con il messaggio che elenca i membri configurati, quelli chiesti, e il
   modo di passare di profilo: `make reset-03`, poi `make up-03`. **Fermarsi e non riconfigurare**:
   `rs.reconfig()` su un set che ha già dati non è un'operazione da script di avvio, e un anello
   che la tentasse trasformerebbe un errore leggibile in un guasto a metà.

3. **Il seed non salta il caricamento se la collezione non è nel catalogo.** Nuovo codice **9**
   (`USCITA_NON_DISTRIBUITA`), con il messaggio che indica `make seed-03`. Non svuota da sé: una
   collezione piena è dati, e cancellarli non è una decisione che uno script di avvio possa
   prendere per conto di chi guarda.

4. **I documenti su un solo shard restano un avviso, e questa è una scelta.** Unire i chunk su uno
   shard è una **scena della demo** ([ADR-0069](#adr-0069)): un `make up-03` dato dopo quella scena
   non deve diventare rosso per averla eseguita. Si boccia l'assenza dal catalogo, che nessuna scena
   produce; non ogni stato diverso da quello che il seed avrebbe prodotto.

5. **Il cheat sheet dice la precondizione che la pagina delle registrazioni diceva già.**
   `docs/02-architetture/sharded-cluster.md` chiedeva di scommentare le tre righe `MEMBRI_*` e
   basta; `docs/05-talk/registrazioni/README.md` diceva anche `make reset-03`. Due pagine che
   descrivono la stessa manovra e ne dicono metà a testa: adesso il cheat sheet — che è dove va a
   guardare chi cambia profilo — le dice tutte e due.

6. **Le correzioni sono state viste in opera nei due versi** (nota di metodo 131). Le due prove
   nuove di `check_stack.py` sono state fatte fallire neutralizzando la regola; le tre correzioni
   agli script di init sono state provate riproducendo il guasto — uscite **6** e **9** con i
   membri e i conteggi nominati — e poi rifacendo i giri leciti: `up-03` in `palco` e in `completo`,
   da zero e ripetuto, **0** tutte e quattro le volte, e `smoke-03 PROFILO=completo` con «Superati:
   101 · Errori: 0».

**Conseguenze.** Tre stati che uscivano **0** adesso escono **1**, **6** e **9**, e nessuno di loro
è raggiungibile da un uso corretto: le prove sui giri leciti servono a dirlo, non a decorare. Il
prezzo è che chi cambia profilo su uno stack acceso adesso trova un errore dove prima trovava un
avvio riuscito e uno stack sbagliato — che è il baratto per cui la guardia esiste. Le cinque
registrazioni asciinema non sono toccate: mostrano giri leciti, e nei giri leciti niente cambia.

Resta scritto che [ADR-0060](#adr-0060) **regge**: le sue due guardie funzionano, e una di loro si è
fatta viva da sé durante una prova d'altro, fermando la catena con uscita 5. Il buco era accanto,
non dentro. Una guardia bilaterale su due sorgenti non copre una terza sorgente che nessuno aveva
contato — e la terza, qui, era lo stato sul disco.

**Alternative scartate.** **Riconfigurare invece di fermarsi** — l'anello potrebbe chiamare
`rs.reconfig()` e aggiungere i membri mancanti. Sarebbe comodo e sbagliato: la riconfigurazione di
un config server con dati dentro è un'operazione che si fa guardandola, non dentro un `depends_on`,
e il fallimento a metà lascerebbe un cluster in uno stato che nessun messaggio saprebbe descrivere.
**Fare del seed un errore anche per il singolo shard** — renderebbe rosso il `make up-03` che segue
la scena della fusione, cioè punirebbe l'uso previsto. **Allargare la condizione del `mongod`
invece di scrivere una regola nuova** — un `avvia_mongod(...) or avvia_mongos(...)` costa una riga
in meno e produce un solo messaggio per due guasti che si diagnosticano in modo diverso; il valore
di `check_stack.py` è il messaggio, non il codice d'uscita ([ADR-0076](#adr-0076)). **Lasciare i tre
rilievi alla revisione umana e fondere così com'è** — sono tre falsi verdi provati, e la promessa
in testata alla PR è proprio che il verde significhi qualcosa.

**Fonti:** [V-071](Sources.md#v-071), [V-072](Sources.md#v-072)


---

<a id="adr-0078"></a>
## ADR-0078 — `feature/04` comincia il 2 settembre, perché la condizione che ADR-0057 pretendeva è arrivata prima della data

**Data:** 2026-09-02 · **Stato:** Accettata — modifica la clausola di data di [ADR-0057](#adr-0057)

**Contesto:** [ADR-0057](#adr-0057) porta due frasi che vanno lette insieme, e la seconda è nelle
alternative scartate. La decisione dice «**`feature/04-app-python` conserva la sua data di inizio,
il 4 settembre**». Lo scarto dice perché: «anticipare `feature/04` al 2 settembre, che avrebbe usato
l'anticipo sul pezzo grande — scartata perché l'applicazione ha bisogno di **giorni consecutivi e
pieni**, e due giorni intestati a un branch di due settimane non lo accorciano, lo frammentano».

Il 2 settembre `feature/03-stack-sharded` è stata chiusa e unita in `develop` (merge `ca6f3d0`):
undici task su undici e due review esterne arbitrate, nel 1º e nel 2, non nel 2 e nel 3. La clausola
di sospensione di ADR-0057 non è stata azionata perché non è servita.

Questo cambia il fatto su cui poggiava lo scarto, e conviene essere precisi su come. Lo scenario
respinto era **due giorni intestati a `feature/04` mentre lo sharded era ancora aperto**: due giorni
che sarebbero stati interrotti e ripresi, cioè frammentazione travestita da anticipo. Lo scenario
che si presenta adesso è diverso in natura, non in grado — il 2, il 3 e tutti i successivi sono
liberi e contigui, quindi `feature/04` non riceve due giorni staccati ma una finestra continua che
passa da otto giorni a **dieci**. È esattamente la condizione — «giorni consecutivi e pieni» — la
cui assenza motivava lo scarto.

**Decisione:** `feature/04-app-python` si apre il **2 settembre 2026** e la sua finestra va dal 2
all'11 settembre. Il branch è stato creato lo stesso giorno dal Product Owner, con
`git worktree add -b feature/04-app-python .claude/worktrees/feature-04-app-python develop` e la
spinta su `origin`: questo ADR è la sede della decisione, non il suo annuncio.

Restano in piedi invariate le altre disposizioni di ADR-0057: il 14 e il 15 settembre sono margine
prima della `release/1.0` del 16, e la regola che un branch che sfora si sospende scrivendo il punto
di ripresa, invece di mangiare la finestra successiva, vale qui come valeva lì.

Il primo appuntamento di [ADR-0058](#adr-0058) — il controllo della 8.0.30 — è fissato «il 3
settembre, alla chiusura di `feature/03`». Le sue due coordinate si sono separate: l'evento è
successo il 2, la data dice il 3. **Vale l'evento**, e il controllo si esegue come primo passo di
questo branch. La ragione dell'appuntamento è che montare l'applicazione su una versione e
ripinnarla il giorno dopo costringe a rigirare le registrazioni, e quella ragione appartiene
all'inizio del branch, non a una casella di calendario. La seconda data, il 16 settembre, non è
toccata.

**Conseguenze:** la finestra di `feature/04` è di dieci giorni invece di otto, e la scadenza
dell'11 settembre **resta quella che era** — l'anticipo si spende in margine, non in ambizione. Il
calendario del design non viene riscritto: chi legge la §10 trova la finestra originale con la sua
motivazione, chi legge qui trova che cosa è successo dopo.

Va scritto anche ciò che questo ADR non compra. Dieci giorni invece di otto non rendono
`feature/04` più piccola, e il rischio che ADR-0057 nominava — un branch aperto «perché c'è tempo»
— non sparisce, cambia forma: qui prende quella di un piano che si allarga per riempire lo spazio
disponibile. La difesa resta la stessa di allora, cioè una data e un piano scritto prima di toccare
un file.

**Alternative scartate:** **aspettare il 4 e tenere fermi il 2 e il 3**, che rispetta la lettera di
ADR-0057 — scartata perché ne tradisce la ragione: quella clausola difendeva la **continuità** della
finestra dell'applicazione, e tenerla ferma due giorni la accorcia senza proteggere nulla.
**Aprire il branch e non scrivere niente**, lasciando che la data del primo commit raccontasse da
sé la deviazione — è la forma che ADR-0057 stesso boccia in coda alle proprie alternative, perché
lascia in piedi due verità in conflitto. **Spostare in avanti anche la scadenza dell'11**,
trasformando i due giorni in lavoro in più invece che in margine — scartata perché il 16 è la
`release/1.0` e il 18 è il talk: ciò che sta fra l'11 e il 16 è la riserva che assorbe gli
imprevisti di un branch che comincia da zero righe di codice, ed è la cosa che meno conviene
spendere in anticipo.

**Fonti:** nessuna (decisione organizzativa)


---

<a id="adr-0079"></a>
## ADR-0079 — Prima di rimuovere un worktree si sgancia chi ci sta dentro: una sessione viva è stato che git non vede

**Data:** 2026-09-02 · **Stato:** Accettata — estende [ADR-0056](#adr-0056)

**Contesto:** [ADR-0056](#adr-0056) ha scoperto che `git worktree remove` cancella in silenzio i
file ignorati, e ne ha ricavato una precondizione: prima di rimuovere, si guarda dentro. Il 2
settembre la stessa manovra ha rivelato una **seconda** categoria di cosa che vive dentro un
worktree e che git non conta — la sessione di lavoro che ci sta in piedi.

La sessione che aveva sviluppato `feature/03` era stata avviata dentro
`.claude/worktrees/feature-03-stack-sharded` ed era isolata lì da una guardia: ogni comando viene
confrontato con quel percorso e rifiutato se risolve altrove. È il meccanismo che impedisce a
sessioni parallele di pestarsi i piedi, ed è giusto che esista.

Quel percorso però è **stato della sessione**, registrato all'avvio. Non è un file, non è un ref,
non è un'informazione che git possieda: `git worktree remove` non può aggiornarlo e non ci prova.
Eseguito il comando dal checkout principale, con la sessione ancora viva, la directory è sparita e
la guardia ha continuato a pretenderla. Il risultato, misurato in [V-073](Sources.md#v-073): ogni
comando di shell rifiutato — anche quelli che non nominavano git e quelli che puntavano altrove,
perché nessuna directory di lavoro può risolvere dentro una directory che non esiste — e ogni
scrittura rifiutata con l'invito a modificare «la copia nel worktree» di un worktree che non c'è
più. La sessione poteva leggere e non toccare, per il resto del suo lavoro utile.

**Il comando che ha fatto il danno è il comando giusto.** `git worktree remove` è la forma
documentata per la pulizia, si rifiuta di girare se ci sono modifiche in sospeso, ed è uscito `0`.
Non era sbagliato: era **fuori ordine**. È la stessa forma di ADR-0056 — la rete di sicurezza
esiste e non copre questa categoria, perché una sessione viva non lascia tracce nel working tree e
da fuori il worktree è una directory pulita.

**Decisione:** alla chiusura di un branch, **la sessione si sgancia prima che la directory
sparisca**. L'ordine è vincolante quanto quello di ADR-0056:

1. la PR è unita in `develop` sul remoto;
2. **si sgancia la sessione** — `ExitWorktree` in modalità `keep`, oppure la si chiude, se era stata
   avviata da un terminale dentro il worktree;
3. si riallinea il checkout principale — `git fetch --prune`, poi `git merge --ff-only origin/develop`;
4. si guarda dentro il worktree e si salva ciò che è ignorato e non si rigenera ([ADR-0056](#adr-0056));
5. `git worktree remove`, `git branch -d`, `git worktree prune`;
6. si verifica con `git worktree list` e `git branch`.

I passi dal 3 in poi si eseguono **dal checkout principale**. La procedura per esteso — apertura,
chiusura, e la manovra di recupero se il blocco si presenta comunque — sta in
[`06-sviluppo/worktree-e-branch-di-lavoro.md`](06-sviluppo/worktree-e-branch-di-lavoro.md).

**Conseguenze:** un passo in più prima della rimozione, e uno stesso comando che adesso ha due
precondizioni scritte invece di una. Le due sono la stessa lezione applicata a categorie diverse —
ADR-0056 ai file che git ha ricevuto istruzione di non guardare, questo ai processi che git non ha
modo di vedere. La forma è quella di `umount` prima di staccare il disco, e la ragione è identica:
chi tiene aperto il riferimento non è chi cancella, e il secondo non ha modo di accorgersi del
primo.

Resta scritta anche la via d'uscita, perché una procedura che protegge da un errore serve poco a chi
l'errore l'ha già fatto: `ExitWorktree` con `action: "keep"` sgancia il pin **anche quando il
worktree agganciato non esiste più**, nonostante la sua documentazione dichiari di essere
un'operazione nulla fuori da una sessione aperta con `EnterWorktree`. Il rientro diretto invece non
funziona: `EnterWorktree` rifiuta se la directory corrente non è in un repository, e rifiuta anche
se il bersaglio è già la directory corrente. Si esce e poi si entra, in quest'ordine.

**Alternative scartate:** **rinunciare ai worktree e lavorare sempre nel checkout principale** —
toglie il problema e con lui la ragione per cui i worktree ci sono, cioè tenere `develop` fermo e
leggibile mentre un branch corre, e permettere a più sessioni di lavorare senza contendersi
l'albero. **Rimandare la rimozione a dopo la fine della sessione**, lasciando i worktree chiusi sul
disco fino all'apertura successiva — evita il blocco e accumula directory di cui nessuno ricorda
più a quale branch appartengano; la memoria di «questo si può togliere» dura meno del disordine.
**Affidarsi al rifiuto di `git worktree remove`** — non copre questo caso e non può: git guarda il
working tree, e una sessione viva non ci lascia niente da guardare. **Scrivere solo la manovra di
recupero e non la precondizione** — è la scelta che rende accettabile sbagliare, e questo
repository ha già l'abitudine contraria.

**Fonti:** [V-073](Sources.md#v-073)

---

<a id="adr-0080"></a>
## ADR-0080 — Speso il primo dei due appuntamenti: la 8.0.30 non c'è, resta il 16 settembre

**Data:** 2026-09-02 · **Stato:** Accettata — attua [ADR-0058](#adr-0058)

**Contesto:** [ADR-0058](#adr-0058) ha preso una clausola condizionale di [ADR-0028](#adr-0028) —
«si ripinna appena i binari della 8.0.30 escono» — e le ha dato due date, perché «appena» non ha un
esecutore. La prima era «il 3 settembre, alla chiusura di `feature/03`». Le due coordinate si sono
separate: la `03` ha chiuso il 2, e [ADR-0078](#adr-0078) ha stabilito che vale **l'evento**, perché
è l'evento a portare la ragione pratica — montare l'applicazione su una versione e ripinnarla il
giorno dopo significa rigirare le registrazioni. L'appuntamento è quindi caduto all'apertura di
`feature/04`, prima di scrivere una riga di codice.

Il controllo è stato fatto ([V-074](Sources.md#v-074)) e la risposta è la stessa del 1º settembre:
la **8.0.30 non è pubblicata**. Con tre differenze che valgono più della risposta. È stato
interrogato anche il **terzo canale** che ADR-0028 nominava e che V-051 aveva lasciato scoperto,
`mongodb/mongodb-community-server`: dà zero sulla 8.0.30 e **centosessantaquattro** tag sulla
8.0.29, fra cui ricostruzioni con marca temporale di **stamattina**. Non è un canale fermo che tace,
è un canale che oggi ha ripubblicato la versione precedente. È stata inoltre chiusa la riserva di
V-051 sul changelog: la correzione che aspettiamo,
[SERVER-125742](https://jira.mongodb.org/browse/SERVER-125742), è **ancora** attribuita alla 8.0.30
e non è slittata a una patch successiva ([S-028](Sources.md#s-028)). E la 7.0.40 resta la punta
della propria linea: la versione del lab non invecchia mentre la si usa.

**Decisione:** il lab resta su **7.0.40** e `feature/04` monta l'applicazione su quella versione. Il
primo dei due appuntamenti di ADR-0058 è **speso**, e ne resta uno solo: il **16 settembre**, giorno
della `release/1.0`, ultimo momento utile per ripinnare e rigirare le registrazioni prima del talk.
La procedura del controllo si estende da due canali a **tre** — Docker Hub `library/mongo`, il feed
ufficiale dei download, e `mongodb/mongodb-community-server` — perché ADR-0028 li nominava tutti e
tre e una verifica che ne copre due su tre lascia aperta proprio la domanda che dovrebbe chiudere.
Il comando è scritto per intero in [V-074](Sources.md#v-074).

**Conseguenze:** nessun file cambia. `${MONGO_IMAGE}` e i digest di `tools/images.env` restano dove
sono, le nove registrazioni asciinema restano valide, e i tre stack non si toccano. Cambia una cosa
sola, ed è la ragione per cui questa decisione è scritta invece che taciuta: chi arriva al 16
settembre sa che il primo controllo **è stato fatto** e che cosa ha trovato, invece di doverselo
chiedere. Una verifica negativa che non lascia una sede si fa due volte, e la seconda volta la si fa
di fretta.

Resta scritto anche il limite di ciò che si può concludere. Il changelog della 8.0.30 è pubblicato e
i binari no: è documentazione di una patch preparata, non un annuncio di rilascio, e non contiene
alcuna data. Non sappiamo quando esce, e il repository non ha modo di saperlo senza aprire un
contatto con MongoDB, che non è previsto. Il 16 settembre si guarda di nuovo; se la risposta è
ancora no, il talk si tiene su 7.0.40 e il muro della 8 su kernel 6.19 resta una cosa da
raccontare — chiunque in sala provi MongoDB 8 su Docker Desktop incontra lo stesso errore e non ha
una versione cui aggiornarsi, che è un fatto interessante di per sé.

**Alternative scartate:** **non scrivere niente**, perché ADR-0058 aveva già previsto questo esito e
il piano di `feature/04` diceva «se non c'è, non serve altro ADR» — ma un appuntamento onorato
cambia lo stato del progetto anche quando l'esito è il previsto, e `check_citations.py` lo dice a
suo modo rifiutando le fonti che nessuno cita: una misura senza una decisione che la usi non ha
sede. **Aggiungere V-074 alla riga «Fonti» di ADR-0058** invece di scrivere un ADR nuovo — costa una
riga sola, e riscrive un documento accettato per farlo parlare di un fatto successivo alla sua data;
qui gli ADR si superano per aggiunta, non si aggiornano. **Spostare anche la seconda data**, come
ADR-0078 ha fatto con la prima — non serve: il 16 settembre è il giorno della `release/1.0`, quindi
data ed evento coincidono per costruzione, ed è la coincidenza a mancare che aveva creato il
problema. **Ripinnare alla 8.2.12 per avere un «8» sulle slide** — già scartata da ADR-0028 per due
ragioni che non sono cambiate, e riscartata da ADR-0058 un giorno fa.

**Fonti:** [V-074](Sources.md#v-074), [S-028](Sources.md#s-028)

---

<a id="adr-0081"></a>
## ADR-0081 — La documentazione dell'applicazione sta accanto al codice, con un registro delle fonti proprio

**Data:** 2026-09-03 · **Stato:** Accettata

**Contesto:** scrivendo il dominio di `mongolab` sono emerse spiegazioni che non hanno una sede.
Perché `frozen=True` non basta e serve anche `slots=True`; perché `isinstance` contro un `Protocol`
guarda i nomi e non le firme; perché il listener di PyMongo deve depositare in coda e uscire. Sono
affermazioni verificate, alcune misurate su questo ambiente, e sono esattamente il materiale
didattico che il talk esiste per trasmettere. Finora vivevano in tre posti dove invecchiano male:
nelle docstring, dove le legge solo chi apre quel file; nel registro operativo, che è cronologico e
non si consulta per argomento; e in chat, che non è un posto.

Le sedi previste dal repository non le accolgono. `docs/06-sviluppo/` è divulgativa e ha un altro
lettore — chi ha visto il talk e non aprirà mai `app/src/`; le sue due pagine sull'applicazione sono
promesse al **Task 17**, cioè fra due settimane, e nascerebbero comunque senza il dettaglio che serve
a chi il codice lo apre. Il registro operativo è **append-only** per costruzione: ottimo per sapere
quando si è deciso qualcosa, inservibile per sapere che cosa vale adesso.

C'è un secondo ostacolo, ed è tecnico. Le fonti di queste spiegazioni sono documentazione di
linguaggio e di strumenti — `typing`, `dataclasses`, mypy, pytest — che **nessun ADR cita né deve
citare**: sono vincoli del linguaggio, non scelte del progetto. Messe in `docs/Sources.md`
diventerebbero tutte **orfane**, e `check_citations.py` boccerebbe la build. La regola non ha torto:
sta dicendo che quelle voci non appartengono a quel registro.

**Decisione:** la documentazione dell'applicazione sta in **`app/docs/`**, accanto al codice che
descrive, con un proprio `Sources.md` che usa prefissi distinti — **`A-0NN`** per le fonti esterne e
**`M-0NN`** per le misure eseguite in locale — così che non si confondano con gli `S-`/`V-`/`C-` del
registro canonico. Le voci canoniche si **puntano**, mai si copiano.

`docs/` resta la sede normativa: decisioni, fonti del progetto, registro operativo e materiale del
talk non si spostano e non si duplicano. Le pagine di `app/docs/` citano `docs/` e non viceversa,
tranne l'indice, che le annuncia. Le due pagine del Task 17 nasceranno **rimandando** qui invece di
ripetere.

Il controllo dei collegamenti si estende a `app/docs`: `make docs-check` esegue ora
`check_links.py docs app/docs README.md`. `check_citations.py` non cambia — continua a guardare
soltanto `docs/Decision.md` e `docs/Sources.md`, che è ciò che deve fare.

**Conseguenze:** ogni rimando da `app/docs/` a un ADR o a una fonte canonica è verificato con la sua
ancora, e un `#adr-0019` scritto male fallisce invece di portare in cima alla pagina. Al primo
passaggio del controllo, sulle nove pagine nuove, un solo collegamento è risultato rotto.

Il repository accetta un costo: la documentazione non è più tutta in un posto, e
`docs/README.md` ha dovuto correggere la propria affermazione — non era più vero che l'unico
Markdown fuori da `docs/` fosse il `README.md` di radice. In cambio, chi apre `app/` trova la
spiegazione dove sta il codice, e chi apre `docs/` continua a trovare tutto ciò che è normativo.

Il rischio dichiarato è la **divergenza**: due sedi che raccontano la stessa cosa finiscono per
raccontarla diversamente. La difesa scelta non è una regola scritta ma la disciplina del rimando —
`app/docs/` cita e non ricopia — più il controllo automatico che verifica che i rimandi restino
validi. È una difesa parziale: verifica che il collegamento porti da qualche parte, non che i due
testi concordino. Vale la pena saperlo.

**Alternative scartate:** **tutto in `docs/06-sviluppo/`** — sede giusta per il lettore sbagliato, e
disponibile solo dal Task 17, cioè dopo che il codice di cui parla è già scritto. **Solo docstring**
— non spiegano perché una scelta è stata fatta rispetto alle alternative, e chi cerca «come funziona
questa applicazione» non apre otto file. **Le fonti dell'applicazione in `docs/Sources.md`** —
sarebbero orfane e farebbero fallire `check_citations.py`; aggirare quel controllo per farcele stare
sarebbe l'esatto opposto di ciò che il repository fa quando una regola ostacola qualcosa di
legittimo, cioè aprire la sede che manca (nota di metodo 141). **Riusare i prefissi `S-`/`V-` anche
in `app/docs/Sources.md`** — due registri con la stessa numerazione producono `S-042` ambigui, e
l'ambiguità arriverebbe proprio quando qualcuno cita di fretta.

**Fonti:** nessuna (decisione organizzativa)

---

<a id="adr-0082"></a>
## ADR-0082 — Gli eventi del §6.3 diventano nove: il client può dire di aver smesso di aspettare

**Data:** 2026-09-03 · **Stato:** Accettata

**Contesto:** il §6.2 del design contiene una regola scritta come frase e mai implementata: «dopo
30 s senza primario, smetti di ritentare». È la regola per cui esiste la porta `Clock`, ed è citata
lì proprio come esempio di ciò che si prova in millisecondi invece che in decine di secondi. Il
Task 6 di `feature/04` la traduce in codice — `TopologyWatcher` osserva la topologia, e se non vede
un primario entro la pazienza configurata smette di guardare — e il piano chiede che lo dica
emettendo un evento.

Nessuno degli otto eventi del §6.3 può dirlo senza mentire. `WriteFailed` racconta una scrittura
rifiutata, e qui nessuno ha tentato di scrivere: metterlo in cronaca inventa un'operazione.
`RetryAttempted` annuncia un tentativo che sta per essere fatto, ed è l'esatto contrario di una resa
— al Task 5 il repository ha già stabilito, con una prova, che l'ultimo evento di una resa **non**
può essere un `RetryAttempted`, perché un tentativo annunciato e mai eseguito è una cronaca falsa.
`TopologyChanged` e `ServerStateChanged` riferiscono osservazioni, mentre la resa è una decisione di
chi osserva: non è cambiato niente nel cluster, è cambiato che il client ha smesso di chiedere.
Restano `LatencySampled`, `BackupProgressed` e `ChunkMigrated`, che non c'entrano.

Il vincolo che ha reso visibile il problema è una guardia: `test_gli_eventi_del_design_sono_otto_e_sono_quelli`
elenca le sottoclassi di `Evento` e le confronta con l'insieme del design. Un nono evento aggiunto
per comodità la fa fallire. È il meccanismo che ha funzionato come doveva — ha costretto a passare di
qui invece di lasciar crescere il dominio in silenzio.

**Decisione:** gli eventi del §6.3 diventano **nove**. Il nono è `PrimaryWaitAbandoned`, e porta
`atteso_ms`, `pazienza_ms` e `ultimo_primario`. Dice un fatto che nessun altro evento dice: **il
client ha smesso di aspettare un primario**, dopo aver atteso tanto, contro una pazienza che valeva
tanto, avendo visto per ultimo quel primario lì.

I due numeri viaggiano insieme e non è ridondanza: `atteso_ms` da solo non si legge. «Ho aspettato
30 000 ms» non dice se è tanto o poco finché non si sa che la pazienza era di 30 000 — e in una demo
dal vivo, dove la pazienza si abbassa apposta per non far attendere la sala, il rapporto fra i due è
esattamente ciò che il pubblico deve vedere. `ultimo_primario` è opzionale perché un client può
arrivare a primario già caduto, e in quel caso non ne ha mai visto uno.

La guardia si aggiorna insieme all'ADR, e resta una guardia: elenca **nove** nomi e li confronta con
le sottoclassi trovate. Il decimo evento aggiunto per comodità continuerà a farla fallire.

Il design **non si riscrive**: questo ADR lo emenda, come ADR-0078 ha emendato la clausola di data di
ADR-0057. Chi legge il §6.3 e conta otto nomi trova qui il nono e la ragione per cui è arrivato dopo.

**Alternative scartate:** **riusare `WriteFailed`** con `tipo_errore="ServerSelectionTimeoutError"` —
è la forma in cui la resa si manifesterebbe davvero in PyMongo, ma il `TopologyWatcher` non scrive, e
una scrittura fallita in cronaca dove nessuno ha scritto è il tipo di falso che il repository ha
appena finito di combattere nei doppi (nota di metodo 149). **Non emettere niente** e limitarsi al
valore di ritorno — il comportamento sarebbe provato lo stesso, perché «ha smesso» si verifica
mostrando che ha smesso di guardare, ma la resa sparirebbe dalla cronaca a schermo, che è il posto in
cui la demo esiste per mostrarla; e il piano chiede un evento. **Un evento generico**
`ClientGaveUp(operazione, motivo)` — coprirebbe anche le rese future, ma un evento che va bene per
tutto porta i suoi dati come testo libero, e i due numeri che rendono leggibile questa resa
tornerebbero a essere una stringa da leggere a occhio. **Un campo booleano su `TopologyChanged`** —
appiccicherebbe una decisione del client a un evento che riferisce il cluster, e renderebbe
`precedente`/`successiva` obbligatorie in un momento in cui non è cambiato niente.

**Fonti:** nessuna (decisione di disegno interna, che emenda il §6.3 di
[`docs/00-progetto/2026-08-24-design.md`](00-progetto/2026-08-24-design.md))

---

<a id="adr-0083"></a>
## ADR-0083 — I `.env` del laboratorio raggiungono un worktree per collegamento, non per copia

**Data:** 2026-09-03 · **Stato:** Accettata

**Contesto:** [ADR-0056](#adr-0056) stabilisce che la casa dei file `.env` del laboratorio è il
checkout principale, e che un worktree non ne ha una propria: sono ignorati dal versionamento,
quindi `worktree add` non li porta, e chi lavora in un worktree si trova gli stack che non partono.
Fin qui la conseguenza era sopportabile, perché nei worktree si scriveva codice e gli stack si
accendevano dal checkout principale.

Il Task 8 di `feature/04` rompe quella sopportabilità. Le prove di integrazione accendono gli stack
**da sole** — è il Passo 3, ed è [ADR-0020](#adr-0020) applicato: si usano i `make up-0X` di questo
repository, non un facsimile — e si eseguono dal worktree, che è il posto in cui il codice che
provano esiste. `make up-02` e `make up-03` leggono `PASSWORD_AMMINISTRATORE` da
`docker/0X-.../.env`. Dal worktree quel file non c'è, e la prova fallisce per un motivo che non ha
niente a che vedere con ciò che verifica.

Tre modi di uscirne, e due sono sbagliati in modo interessante. **Copiare** il file nel worktree
crea una seconda copia di un segreto: si rigenera la password nel checkout principale e il worktree
continua a usare la vecchia, con uno stack che non si autentica e nessun indizio sul perché.
**Leggere il file dal checkout principale** attraverso un percorso assoluto scritto nel codice delle
prove significherebbe mettere il percorso della macchina di chi sviluppa dentro un file versionato,
e costringerebbe `ambiente.py` a sapere che esiste un checkout principale — cioè a sapere del
versionamento, per collegarsi a MongoDB.

**Decisione:** un worktree che deve accendere gli stack crea un **collegamento simbolico** al `.env`
del checkout principale, nella stessa posizione relativa:

```
docker/02-replicaset/.env -> /percorso/del/checkout/principale/docker/02-replicaset/.env
docker/03-sharded/.env    -> /percorso/del/checkout/principale/docker/03-sharded/.env
```

Il collegamento si crea a mano quando serve, non da uno script: sono due comandi, e uno script che
li facesse dovrebbe indovinare quale sia il checkout principale.

Tre proprietà rendono questa la scelta giusta e non un ripiego. Il file **resta uno**: chi rigenera
la password la rigenera per tutti, e non esiste una seconda copia che invecchia. Il versionamento
non lo vede — `docker/*/.env` è gia ignorato da [ADR-0014](#adr-0014), e la regola vale per il
collegamento come per il file, verificato guardando lo stato del repository dopo averli creati. E
`make up-02` eseguito dal worktree funziona senza sapere niente di tutto questo, perché Compose apre
un percorso e il sistema operativo lo segue.

Il prezzo, dichiarato: il collegamento **penzola** se il checkout principale si sposta o si
rinomina, e il messaggio che ne esce parla di un file che non c'è mentre il file c'è, altrove.
È lo stesso genere di errore contro cui ADR-0056 già mette in guardia, e la difesa è la stessa:
prima di rimuovere un worktree si elencano da dentro i file ignorati e si guarda che cosa non si
rigenera. Un collegamento simbolico si rigenera; ciò a cui punta, no.

Questo ADR **estende** ADR-0056, non lo contraddice: la casa dei `.env` resta il checkout
principale, e il worktree non ne ha una propria — ha una porta che dà su quella.

**Alternative scartate:** **copiare il file** — due copie di un segreto che divergono in silenzio.
**Un percorso assoluto nel codice delle prove** — la macchina di chi sviluppa dentro un file
versionato. **Passare la password con `-e` a `docker`** — vietato da [ADR-0054](#adr-0054), e in
ogni caso non risolverebbe: `make up-0X` non è un `exec`, è un `compose up` che legge il `.env` da
sé. **Un `.env` con una password diversa nel worktree** — funzionerebbe, e vorrebbe dire provare
contro uno stack configurato diversamente da quello che il pubblico eseguirà, cioè il contrario di
ADR-0020.

**Fonti:** nessuna (decisione operativa interna, che estende [ADR-0056](#adr-0056) e serve
[ADR-0020](#adr-0020))

---

<a id="adr-0084"></a>
## ADR-0084 — Un restore che perde documenti non è un restore riuscito, anche se `mongorestore` esce zero

**Data:** 2026-09-03 · **Stato:** Accettata

**Contesto:** [ADR-0077](#adr-0077) dice che «un avviso che non cambia il codice d'uscita è un
avviso che nessuno legge», e lo dice guardando gli script del laboratorio: se un controllo scopre
qualcosa e poi esce zero, la catena a valle prosegue come se nulla fosse. Il Task 9 di `feature/04`
ha incontrato la stessa frase dal lato opposto — non uno script che scrive noi, ma uno strumento
ufficiale che **ha** l'informazione, la stampa, e esce zero lo stesso.

La misura è in [M-024](../app/docs/Sources.md#m-024). Un `mongorestore` su una destinazione già
popolata riporta:

```
400000 document(s) restored successfully. 50000 document(s) failed to restore.
```

e il codice d'uscita è **0**. Non è un caso limite costruito per l'occasione: è quello che succede
ogni volta che un restore ricade su documenti il cui `_id` esiste già, cioè il secondo giro di
qualunque restore sulla stessa destinazione. Chi chiama controllando soltanto il codice d'uscita —
che è il modo in cui si controlla un processo esterno — riceve «riuscito» per un'operazione che ha
perso un documento su nove.

Sul palco questo è precisamente il difetto peggiore. L'Atto III del Blocco 2 mostra un backup che
gira mentre il cluster lavora, e la tesi è che il dump non disturbi. Una tesi del genere si regge
sul fatto che il dump e il restore **siano andati a buon fine**: un ripristino che ha perso un
nono dei documenti senza dirlo trasformerebbe la dimostrazione in un'affermazione falsa fatta con
sicurezza.

**Decisione:** l'adattatore `SubprocessBackup` legge la riga di sommario e, quando i falliti sono
più di zero, solleva `RestoreIncompleto` con i due conteggi — restaurati e persi. Mette cioè il
verdetto che lo strumento non ha messo.

Tre precisazioni su che cosa questo *non* è. **Non sostituisce il codice d'uscita:** un'uscita
diversa da zero resta `ComandoFallito` e ha la precedenza, perché lì lo strumento il verdetto lo ha
dato e va riportato con il suo codice e il suo messaggio. **Non annulla niente:** i documenti già
entrati restano dentro, l'eccezione racconta l'accaduto e non lo disfa — chi la riceve deve
decidere che cosa fare della destinazione, e la scelta non è dell'adattatore. **Non è una politica
sul numero di documenti attesi:** l'adattatore non sa quanti dovevano essere, sa solo che lo
strumento ne ha dichiarati alcuni persi, e su quello si basa.

La responsabilità sta nell'adattatore e non in chi lo chiama per la ragione che rende una porta una
porta: la riga di sommario è testo di `mongorestore`, e chi chiama parla con `BackupTool`, non con
`mongorestore`. Spostare il controllo di sopra vorrebbe dire che ogni chiamante rifà lo stesso
riconoscimento della stessa riga, e che il primo che si dimentica di farlo riapre il buco.

Il prezzo, dichiarato: **la riga di sommario è un formato di testo, non un'interfaccia**. Se una
versione futura la riscrive, la guardia non diventa sbagliata — diventa **muta**, che è peggio,
perché torna il silenzio di prima senza che nessuno lo veda. La difesa è una prova di integrazione
che esegue un secondo restore sulla stessa destinazione e pretende `RestoreIncompleto` con
`restaurati == 0` e `falliti == 100000`: il giorno in cui il formato cambia, quella prova diventa
rossa. È la stessa forma di difesa già usata per l'ispettore che dipende da `config`
([A-013](../app/docs/Sources.md#a-013)).

**Alternative scartate:** **registrare un avviso e proseguire** — è esattamente lo sbaglio che
ADR-0077 descrive, con l'aggravante che qui l'avviso esiste già ed è lo strumento a scriverlo.
**Contare i documenti a posteriori** — richiede di sapere quanti dovevano essere, cioè di mettere
nell'adattatore una conoscenza del dominio che non gli appartiene; e sulla destinazione di una
demo il conteggio atteso è proprio la cosa che si vuole verificare, non un dato da assumere.
**`--stopOnError` sulla riga di comando dello strumento** — non è stata misurata, e in ogni caso
risponde a un'altra domanda: cambia ciò che lo strumento **fa**, interrompendolo a metà, invece di
cambiare ciò che l'applicazione **dice** di quello che è successo; un restore fermato a metà è un
esito peggiore da spiegare dal palco di un restore completato e dichiarato incompleto.
**Considerare fallito qualunque restore con almeno un fallimento solo nelle prove, e non in
produzione** — le prove verificherebbero un comportamento che l'applicazione non ha.

Questo ADR **estende** ADR-0077: la regola era «un avviso che non cambia il codice d'uscita è un
avviso che nessuno legge», e vale per gli avvisi che scriviamo noi. L'aggiunta è che, quando lo
strumento di qualcun altro commette lo stesso errore, l'adattatore che lo incapsula è il posto in
cui si ripara.

**Fonti:** nessuna in [`Sources.md`](Sources.md) (decisione di disegno interna, che estende
[ADR-0077](#adr-0077)); le misure che la giustificano sono
[M-024](../app/docs/Sources.md#m-024) e [M-023](../app/docs/Sources.md#m-023) nel registro
dell'applicazione

---

<a id="adr-0085"></a>
## ADR-0085 — La promessa di un solo thread si mantiene spegnendo `auto_refresh`, e il ritmo si sposta nel ciclo

**Data:** 2026-09-03 · **Stato:** Accettata

**Contesto:** [ADR-0019](#adr-0019) ha deciso che gli eventi del driver non toccano lo schermo:
l'ascoltatore di PyMongo costruisce un fatto congelato, lo mette in coda e ritorna, perché la
consegna è sincrona e blocca il thread del driver ([S-010](Sources.md#s-010)). La conseguenza
scritta nell'ADR era «il ciclo di disegno gira sul thread principale», e la ragione dichiarata per
non fare altrimenti era una lacuna: la documentazione di `Live` di Rich non nomina mai i thread
([S-018](Sources.md#s-018)). Di fronte a una lacuna il progetto ha cambiato disegno invece di
indovinare.

Scrivendo il Task 10 la lacuna è stata guardata da vicino, ed è peggio di una lacuna. Con le
impostazioni predefinite `Live.start()` avvia un `_RefreshThread` **demone** che chiama `refresh()`
per conto suo quattro volte al secondo ([M-027](../app/docs/Sources.md#m-027)). La docstring del
parametro `auto_refresh` dice «Enable auto refresh» e non dice chi lo attui
([A-015](../app/docs/Sources.md#a-015)): la frase è al passivo, e un lettore ragionevole può
concludere che il ridisegno avvenga dentro le chiamate che fa lui. Non avviene.

Il codice non sarebbe stato scorretto — dentro `Live` c'è un `RLock`, e i due thread non si
sarebbero pestati i piedi. Sarebbe stato però **corretto per una ragione che il progetto non
conosceva**, appoggiata a un attributo privato di una libreria, in un ADR che diceva testualmente
di non volersi appoggiare a niente del genere. Una promessa mantenuta per caso non è mantenuta: è
una promessa che nessuno sta controllando.

**Decisione:** `RichTui` costruisce `Live` con `auto_refresh=False` e chiama `refresh()` dal proprio
ciclo. Questo rende vera, e non solo dichiarata, la frase di ADR-0019.

Il prezzo è misurato e va detto per intero: con `auto_refresh=False` il parametro
`refresh_per_second` diventa **inerte**. Mille aggiornamenti al secondo per mezzo secondo scrivono
sette byte, cioè niente ([M-027](../app/docs/Sources.md#m-027)). Il Task 10 chiedeva di passarlo
«esplicitamente, con il valore scritto accanto alla ragione per cui è quello»: passarlo sarebbe
stato scrivere una ragione accanto a un numero che nessuno legge, cioè la forma dell'esplicitezza
senza la sostanza. Il numero vive quindi nel **periodo del ciclo** — `RITMO_PREDEFINITO = 10.0`, e
`self._periodo = 1.0 / ritmo` — che è il posto in cui agisce davvero, e resta regolabile dal
composition root come chiedeva l'intento del passo.

Dieci al secondo, e non altro, per due misure che guardano da lati opposti. Verso il basso il ritmo
è il ritardo massimo fra un fatto e la sua comparsa: cento millisecondi a dieci, duecentocinquanta
ai quattro predefiniti di Rich, e in una scena in cui i tempi sono il contenuto quel quarto di
secondo si vede. Verso l'alto un disegno costa 0,76 ms nel caso peggiore — tre server e cronaca
piena — cioè lo 0,8% di un core a dieci giri al secondo
([M-028](../app/docs/Sources.md#m-028)). Il costo non è il vincolo; il ritardo sì.

La promessa non resta affidata alla riga di codice che la mantiene. Una prova conta i thread vivi
mentre il display è acceso e pretende che non ne sia nato nessuno. Conta i thread invece di
nominare `_RefreshThread` apposta: se Rich rinominasse la classe privata la prova continuerebbe a
valere, se ne cambiasse il **comportamento** fallirebbe. È l'ordine giusto fra le due cose.

**Alternative scartate.** **Lasciare `auto_refresh=True` e fidarsi del lucchetto interno** — è la
scelta che funziona oggi e che rende ADR-0019 una frase non verificabile; il giorno in cui Rich
cambiasse il lucchetto, il difetto comparirebbe in sala e non nelle prove. **Passare comunque
`refresh_per_second` per rispettare la lettera del passo** — decorazione: un parametro inerte
accanto a un commento che ne spiega il valore è peggio dell'assenza, perché chi legge crede di aver
capito da dove viene il ritmo. **Tenere il ciclo di disegno su un thread suo** — è la simmetrica
dell'errore che ADR-0019 aveva evitato, e riporterebbe due thread su `Live` per scelta invece che
per distrazione.

Questo ADR **non modifica** ADR-0019: ne mantiene la decisione e ne corregge il presupposto. La
regola sottostante è la stessa che il progetto applica altrove, e vale la pena enunciarla: quando
una decisione si giustifica con il silenzio di una documentazione, quel silenzio va misurato prima
di trattarlo come una garanzia.

**Fonti:** [S-018](Sources.md#s-018) e [S-010](Sources.md#s-010); nel registro dell'applicazione
[A-015](../app/docs/Sources.md#a-015), [M-027](../app/docs/Sources.md#m-027) e
[M-028](../app/docs/Sources.md#m-028)

---

<a id="adr-0086"></a>
## ADR-0086 — L'orologio si ancora al muro una volta sola, e da lì in poi conta con il monotono

**Data:** 2026-09-03 · **Stato:** Accettata

**Contesto:** la porta `Clock` ([ADR-0007](#adr-0007)) ha due metodi, `now()` e `sleep()`, e fino
al Task 10 esisteva solo come doppio: `FakeClock` nelle prove, in produzione nessuno. Il Task 11
la doveva riempire, e l'implementazione ovvia è una riga: `datetime.now().astimezone()`.

Quella riga è sbagliata, e leggendola non si vede perché. `Clock` serve a due cose che sembrano
una sola. Serve a **datare** — `WriteSucceeded.istante` finisce in cronaca al millesimo — e serve
a **misurare**: `WorkloadRunner._scrivi` sottrae due `now()` e chiama il risultato latenza,
`TopologyWatcher` sottrae due `now()` e decide se la pazienza è finita. Datare vuole l'ora vera;
misurare vuole che il tempo non torni indietro. L'orologio da parete di questa macchina dichiara
`monotonic=False`, cioè per contratto non promette la seconda
([M-030](../app/docs/Sources.md#m-030)).

Un salto all'indietro non produce un errore. Produce una latenza negativa che entra nei percentili
e una pazienza che non scade: numeri plausibili, proiettati in sala. È la stessa forma di guasto
di [ADR-0084](#adr-0084) — un'uscita che non si lamenta e non è vera.

**Decisione:** `SystemClock` legge l'orologio da parete **una volta sola**, alla costruzione, e da
lì in poi restituisce quell'ancora più il tempo trascorso secondo `time.monotonic()`. Gli istanti
sono ore vere — si leggono accanto all'orologio in fondo alla sala — e le loro differenze sono
durate vere, perché vengono tutte dallo stesso contatore che non torna indietro.

L'ancora è nel **fuso locale**, non in UTC: `presentation/righe.py` stampa `%H:%M:%S.mmm` senza
data né nome di zona, e a Ancona due ore di scarto dall'orologio della sala sarebbero la prima
domanda del pubblico. I due orologi entrano come argomenti con valore predefinito (`muro=`,
`monotono=`) perché la riga che distingue questa classe da `datetime.now` è verificabile solo
facendo saltare il muro sotto di lei.

**Alternative scartate.**

- *`datetime.now()` a ogni chiamata.* Una riga, e corretta quasi sempre. Ma la volta che sbaglia
  produce numeri invece che eccezioni, e la scena in cui sbaglia — la macchina che si risincronizza
  durante un failover — è quella per cui il talk esiste.
- *Due porte: un orologio da muro e un cronometro.* Onesta, perché separa i due usi invece di
  riconciliarli. Costa una quinta porta, un secondo doppio in ogni prova, e a ogni chiamata una
  domanda in più per chi scrive: «questo istante lo devo datare o misurare?». Il §6.2 nomina un
  `SystemClock` solo, e per un'applicazione di questa dimensione il conto non torna.
- *Controllare il segno a ogni sottrazione.* Sposta la difesa nei punti d'uso — due oggi, N domani
  — e trasforma un'anomalia in un caso da gestire dentro codice che parla d'altro. Nasconde invece
  di prevenire.
- *`time.monotonic()` puro, con le date ricostruite in presentazione.* La cronaca perderebbe l'ora
  vera, che è ciò che rende una registrazione confrontabile con i log dei container.

**Riserve.** L'ancora non viene mai ricorretta: dopo un'ora di processo l'istante riportato
differisce dal muro di quanto i due orologi divergono, che su un portatile è dell'ordine dei
millisecondi. Per una scena di minuti è invisibile; per un demone che gira per giorni sarebbe la
scelta sbagliata, e questo non è un demone. La riserva vera è la **sospensione**:
`mach_absolute_time()` non conta il tempo in cui la macchina dorme, quindi un coperchio chiuso a
metà scena lascerebbe la cronaca indietro rispetto al muro. Non è stato misurato e non lo si
difende: chi presenta non chiude il coperchio.

**Fonti:** nessuna nuova in [`Sources.md`](Sources.md) — è una decisione di disegno interna; la
misura che la giustifica è [M-030](../app/docs/Sources.md#m-030) nel registro dell'applicazione

---

<a id="adr-0087"></a>
## ADR-0087 — La mappa fra `--target` e stack sta nel codice di produzione, e il nome sbagliato muore prima della connessione

**Data:** 2026-09-03 · **Stato:** Accettata

**Contesto:** il §6.4 del disegno scrive `mongolab stats --target rs`. Dietro quella parola stanno
tre fatti: una porta pubblicata sull'host, un `.env` da cui leggere la credenziale, e una decisione
su `directConnection`. Fino al Task 10 vivevano in `tests/integration/ambiente.py`, che li aveva
perché era l'unico codice del repository a collegarsi a qualcosa. Con l'applicazione i candidati a
possederli diventano due, e due copie divergono al primo cambio: la seconda se ne accorge con un
`ServerSelectionTimeoutError` di venti secondi che parla d'altro.

**Decisione:** `infrastructure/bersagli.py` è l'unico posto in cui quella mappa è scritta, e le
prove d'integrazione la importano da lì — il codice di produzione non può importare quello di
prova, il contrario sì.

Il nome è validato **al parse**: `bersaglio_di` solleva `BersaglioSconosciuto`, la CLI lo traduce
in `typer.BadParameter`, e il processo esce con **2** senza aver aperto nessuna connessione
([M-034](../app/docs/Sources.md#m-034)). Il messaggio elenca i tre nomi che esistono, perché chi
sbaglia `--target` sta quasi sempre scrivendo il nome della directory (`02-replicaset`) o quello
del set (`rs0`). Il 2 è anche il codice con cui il `Makefile` rifiuta un `TARGET` mancante: `make
app-stats` senza argomenti e `mongolab stats --target xyz` sono lo stesso errore per chi legge un
CI, e meritano lo stesso numero.

`Bersaglio` è una dataclass congelata di `infrastructure/`, non un `Enum` del dominio: i numeri di
porta di docker-compose sono un fatto d'ambiente, e [ADR-0007](#adr-0007) tiene `domain/` senza
dipendenze e senza conoscenza di dove giri.

**Alternative scartate.**

- *Leggere la mappa dalle variabili d'ambiente.* Il laboratorio deve funzionare offline e senza
  preparazione: se `--target rs` richiedesse un `export`, la prima cosa visibile in sala sarebbe un
  errore di configurazione. La credenziale, che invece non può stare nel repository
  ([ADR-0014](#adr-0014)), continua a venire dal `.env`.
- *Un valore predefinito per `--target`.* Comodo, e capace di mandare a uno stack un comando
  lanciato per un altro. Un carico spedito al bersaglio sbagliato non fallisce: riesce, altrove.
- *Costruire l'URI dentro ogni comando.* Tre copie di tre righe, e la porta di `sharded` cambiata
  in due punti su tre.
- *Validare al momento della connessione.* Il messaggio sarebbe arrivato dopo il timeout di
  selezione, mescolato a un errore di rete che non c'entra niente.

**Riserve.** La mappa contiene le porte **predefinite**: i file Compose le scrivono
`${PORTA_...:-27021}`, quindi un operatore che le spostasse con una variabile d'ambiente non
verrebbe seguito. Nessuno lo fa oggi e `tools/preflight.sh` riserva gli intervalli, ma è una riga
aperta dichiarata. `diretto=True` sul `rs` è il punto di vista dell'**host**
([M-019](../app/docs/Sources.md#m-019)) e ha una scadenza: al Task 12 l'applicazione gira dentro la
rete Compose e la scoperta funziona ([ADR-0012](#adr-0012)).

**Fonti:** nella parte canonica nessuna nuova; nel registro dell'applicazione
[M-034](../app/docs/Sources.md#m-034), [M-019](../app/docs/Sources.md#m-019) e
[M-018](../app/docs/Sources.md#m-018)

---

<a id="adr-0088"></a>
## ADR-0088 — Il carico ha una collezione sua, nuova a ogni corsa

**Data:** 2026-09-03 · **Stato:** Accettata

**Contesto:** la prima esecuzione vera di `mongolab workload` contro lo stack 01 acceso ha stampato
`38 scritture · 0 confermate · 38 fallite`, ed è uscita con zero. Ogni inserimento tornava
`E11000 duplicate key error collection: lab.ordini index: _id_ dup key: { _id: 0 }`
([M-032](../app/docs/Sources.md#m-032)): `DataGenerator` numera i documenti da zero — è ciò che
rende il dataset una funzione pura di `(seme, indice)` — e il seed occupa già gli `_id` da 0 a
49 999.

A sbagliare era il cablaggio, non il disegno. Che il carico dovesse scrivere altrove era già
scritto in due posti: `infrastructure/generatore.py` («le due popolazioni non si incontrano mai
nella stessa collezione, perché il carico scrive nella propria») e `tools/reset-demo.sh`
(`const superstiti = ["ordini"]`, cioè in `lab` ogni altra collezione è residuo e viene tolta). Il
posto c'era; la radice di composizione ci ha mandato il carico in `ordini`.

Nessuna prova unitaria poteva trovarlo, e nessuna doveva: il fatto vive nel punto in cui un
generatore che numera da zero incontra una collezione già numerata, cioè in nessuno dei due. La
cosa che pesa di più non è l'errore, è la sua **forma** — uscita zero, cronaca che scorre, 4 833
letture riuscite su 4 833. Dal fondo della sala è una demo che funziona.

**Decisione:** `workload` scrive in `lab.carico-<AAAAMMGG-hhmmss>`, costruito da
`collezione_di_carico()` accanto alla mappa dei bersagli, e **dice dove scrive** prima di
cominciare: un benchmark che non nomina la propria collezione è un benchmark che non si può
rileggere. La pulizia resta a `reset-demo`, che spazza tutto ciò che non è `ordini`.

Una collezione per corsa, e non una fissa: gli `_id` ripartono da zero a ogni esecuzione, quindi la
seconda corsa sulla stessa collezione fallirebbe come falliva contro `ordini`. In sala il carico si
lancia più di una volta. Il timestamp nel nome è nel fuso locale, per la stessa ragione per cui lo
è la cronaca ([ADR-0086](#adr-0086)): chi cerca la propria collezione fra tre avanzi guarda
l'orologio della sala.

**Alternative scartate.**

- *Far partire il generatore dopo la fine del seed.* Accoppia il generatore a un numero che vive in
  tre `init/*.js`, e non risolve comunque la seconda corsa.
- *Lasciare l'`_id` a MongoDB.* Toglie la riproducibilità del dataset, che è il motivo per cui
  `DataGenerator` esiste, e mescola due popolazioni in una collezione: il «prima e dopo» che il
  Task 16 misura diventa illeggibile.
- *Una collezione fissa `carico`, cancellata all'avvio.* Una `drop` implicita dentro un comando di
  carico è un atto distruttivo nascosto in un posto in cui nessuno lo cerca.
- *Un'opzione `--collection`.* Una manopola in più da ricordare la sera del talk, per una decisione
  che ha una sola risposta giusta.

**Riserve.** Sullo stack 03 la collezione del carico **non è distribuita**:
`docker/03-sharded/init/30-dati-demo.js` distribuisce `lab.ordini` su `{_id: "hashed"}`, e una
collezione creata al volo resta intera sullo shard primario del database. Il confronto fra
architetture del Task 16 dovrà quindi o distribuire la collezione appena creata, o dichiarare che
sta misurando un solo shard. Non è stato misurato, ed è la prima cosa che quel task deve decidere.

**Fonti:** nessuna in [`Sources.md`](Sources.md) — la misura che la giustifica è
[M-032](../app/docs/Sources.md#m-032) nel registro dell'applicazione

---

<a id="adr-0089"></a>
## ADR-0089 — Su uno stesso fatto, un narratore solo: in `watch` è il ponte SDAM

**Data:** 2026-09-03 · **Stato:** Accettata

**Contesto:** `mongolab watch` contro lo stack 01 stampava ogni transizione **due volte**, a mezzo
secondo di distanza. PyMongo non c'entra: un client con un ascoltatore nudo la emette una volta
sola ([M-033](../app/docs/Sources.md#m-033)). A raddoppiarla era il cablaggio del comando, che
aveva due narratori sullo stesso fatto — `SdamBridge`, che traduce i callback del driver (spinto),
e `TopologyWatcher`, che rilegge la stessa `TopologyDescription` ogni mezzo secondo (tirato). Il
ritardo di un giro fra i due rendeva la ripetizione difficile da riconoscere come tale: sembrava
che fosse successo due volte.

Un failover raccontato due volte non è rumore. Chi guarda **conta** le transizioni per capire che
cosa è successo, e leggerne il doppio è leggere un'altra storia.

**Decisione:** in `watch` resta il ponte, e `TopologyWatcher` non viene costruito. Lo prescrive il
§6.3, che assegna al ponte «la cronaca a schermo del failover con timestamp al millisecondo»; sono
anche gli istanti migliori, perché segnano **quando il driver ha saputo**, non quando qualcuno è
passato a chiedere. La sentinella conserva l'altra cosa che sa fare — misurare la durata
dell'**interruzione** — e quella misura vale accanto alle scritture perse, cioè nello scenario di
failover del Task 13.

La regola generale, che vale oltre questo comando: **su uno stesso fatto, un narratore solo.** Se
due componenti osservano la stessa struttura, uno spinto e uno tirato, la ripetizione non è un
rischio: è una certezza.

**Alternative scartate.**

- *Deduplicare nel sink.* Cura il sintomo e introduce un guasto peggiore. Due transizioni identiche
  e ravvicinate sono anche la firma di un membro che *flappa*, cioè esattamente ciò che una demo di
  failover deve mostrare; un filtro non sa distinguere i due casi, e sceglierebbe di nascondere
  quello vero.
- *Tenere la sentinella e togliere il ponte.* Si perderebbero i millisecondi veri, sostituiti
  dall'istante in cui il ciclo è passato a guardare — mezzo secondo di incertezza su una scena che
  dura pochi secondi.
- *Tenerli entrambi, con parole diverse.* Due narratori su un fatto restano due narratori. Cambiare
  il vocabolario rende il doppione più difficile da riconoscere, non meno presente.

**Riserve.** Resta in cronaca una riga vera ma non utile: `TOPOLOGIA singola → singola`, che il
ponte emette perché la *descrizione* della topologia è cambiata — dentro c'è il server che ha
cambiato ruolo — mentre la forma no. È un punto aperto della presentazione, non del cablaggio, e si
chiude decidendo che cosa quella riga debba dire, non aggiungendo un secondo osservatore. Il ciclo
di `watch` vive per ora in `cli.py`, che è un po' più di quanto il §6.1 assegni a una radice di
composizione: si sposta in `application/scenari.py` al Task 13.

**Fonti:** [S-010](Sources.md#s-010), per la consegna sincrona degli eventi che è il motivo per cui
il ponte esiste ([ADR-0019](#adr-0019)); nel registro dell'applicazione
[M-033](../app/docs/Sources.md#m-033)

---

<a id="adr-0090"></a>
## ADR-0090 — Lo stesso stack ha due indirizzi, e l'applicazione dichiara da dove sta guardando

**Data:** 2026-09-03 · **Stato:** Accettata

**Contesto:** fino al Task 11 un bersaglio aveva un indirizzo solo — `localhost:27021` per il
replica set — e una risposta sola alla domanda su `directConnection`. Il Task 12 mette
l'applicazione dentro la rete Compose, e da lì quell'indirizzo non esiste: si chiama
`mongo-rs-1:27017`, e sono tre. Non è lo stesso stack visto peggio, sono due punti di
osservazione con proprietà diverse, e la differenza è precisamente ciò che
[ADR-0012](#adr-0012) dice essere la scena del talk.

I tre fatti che cambiano insieme sono i semi, `directConnection` e il nome del set. Non sono
tre campi indipendenti: `directConnection=True` con più di un seme solleva `ConfigurationError`
**alla costruzione** del client, cioè prima di qualunque rete. Tenerli separati avrebbe
permesso di scrivere una combinazione che non può esistere.

**Decisione:** una `Vista` — semi, `diretto`, `replica` — e ogni `Bersaglio` ne ha due,
`da_host` e `da_rete`. Quale delle due valga lo dice la variabile d'ambiente
`MONGOLAB_PUNTO_DI_VISTA`, che i tre file Compose impostano a `rete` nel servizio `app` e che
sull'host resta assente, cioè `host`. Un valore che non sia nessuno dei due non viene
interpretato con indulgenza: solleva `PuntoDiVistaSconosciuto` e nel messaggio elenca quali
sono.

Una variabile d'ambiente e non un'opzione della riga di comando, perché il punto di vista è una
proprietà di **dove il processo gira** e non una scelta di chi lo lancia. Chi esegue `mongolab
stats --target rs` non deve saperlo, e soprattutto non deve poterlo sbagliare in sala: la
risposta la dà l'ambiente, che è l'unica cosa che quel fatto lo sa davvero.

**Alternative scartate.**

- *Dedurlo, provando a risolvere `mongo-rs-1`.* Una risoluzione DNS che fallisce prende secondi
  e può fallire per altri dieci motivi. Dedurre una cosa che si può dichiarare significa
  scambiare un fatto certo con un indizio.
- *Un secondo bersaglio, `rs-rete`, accanto a `rs`.* Raddoppia la mappa e sposta l'errore su chi
  scrive `--target`: sarebbe possibile chiedere `rs-rete` dall'host e aspettare venti secondi
  per un `ServerSelectionTimeout` che parla d'altro.
- *Tre campi paralleli invece di una `Vista`.* È la forma che permette di scrivere l'impossibile
  — un seme in più su una vista diretta — e di scoprirlo solo quando il client si costruisce.

**Riserve.** Le prove d'integrazione girano sull'host e **dichiarano** il punto di vista invece
di leggerlo, perché una sessione che avesse esportato `MONGOLAB_PUNTO_DI_VISTA=rete` — cosa che
capita provando i comandi di questo task — le farebbe fallire venti secondi per volta parlando
d'altro. È una precauzione contro l'ambiente, non contro il codice.

**Fonti:** [A-016](../app/docs/Sources.md#a-016) per ciò che la specifica SDAM prescrive,
[M-036](../app/docs/Sources.md#m-036) per la scoperta misurata, [M-019](../app/docs/Sources.md#m-019) per il
motivo per cui dall'host non funziona

---

<a id="adr-0091"></a>
## ADR-0091 — Il servizio `app` sta dentro i tre stack, sotto un profilo, e non in un quarto file

**Data:** 2026-09-03 · **Stato:** Accettata

**Contesto:** perché il client scopra i membri per nome di servizio deve stare **sulla rete di
quello stack**, e in Compose una rete appartiene a un progetto. Le forme possibili erano tre: un
quarto file Compose che si attacca alle reti altrui come esterne, un `docker run --network` a
mano, o un servizio dentro ciascuno dei tre file.

**Decisione:** un servizio `app` in ognuno dei tre `compose.yaml`, sotto il profilo `strumenti`,
così che `docker compose up` non lo tiri su mai e `docker compose run --rm app` lo accenda per
il tempo di un comando. Non dichiara `container_name` — di container ne convivono quanti se ne
lanciano — e non dichiara `depends_on`, perché non serve al *ciclo di vita* dello stack: chi lo
esegue lo esegue quando lo stack c'è già.

La ripetizione fra i tre file è reale ed è accettata: è la stessa scelta che il repository fa da
[ADR-0013](#adr-0013) per i tre stack, dove ogni file si legge da solo perché è materiale
didattico prima che infrastruttura. Il prezzo — tre blocchi che possono divergere — si paga con
un controllo invece che con un'astrazione: `tools/tests/test_coerenza_repo.py` verifica che i
tre dichiarino la stessa immagine, che il tag sia la versione di `app/pyproject.toml`, e che
tutti e tre impostino `MONGOLAB_PUNTO_DI_VISTA: rete`.

Il sorgente arriva per **bind mount** (`../../app/src:/app/src:ro`) e l'ambiente virtuale vive
in `/opt/mongolab`, fuori da `/app`: se stesse in `/app/.venv`, montare il sorgente dell'host
sopra `/app` lo coprirebbe — o peggio ci metterebbe sopra il `.venv` di macOS, che dentro Linux
non è eseguibile. È il §6.5 del design: una modifica al codice non deve richiedere una
ricostruzione.

**Alternative scartate.**

- *Un quarto file Compose con le reti dichiarate `external`.* Il nome di una rete esterna
  contiene il nome del progetto, che dipende dalla cartella da cui si esegue: funziona finché
  nessuno rinomina una directory, e rompe con un messaggio che parla di reti e non di cartelle.
- *`docker run --network sqlstart-02-replicaset_default`.* Rimette a mano ciò che Compose sa
  fare, e mette in sala una riga che nessuno può leggere al volo.
- *Nessun profilo, e il servizio spento con `scale: 0`.* Comparirebbe comunque in `up`, `ps` e
  nei log, cioè in tutti i posti in cui il pubblico guarda per capire di quanti pezzi è fatto uno
  stack.

**Riserve.** `docker compose run` **non** ha un flag `--no-build` ([M-035](../app/docs/Sources.md#m-035)):
la garanzia che nessuna costruzione parta a sorpresa la danno `pull_policy: never`
([ADR-0039](#adr-0039)) e il controllo di `tools/preflight.sh`, che sono due presidi più forti
di un flag da ricordare. Il bind mount serve allo **sviluppo**: la sera del talk il sorgente
dell'immagine e quello dell'host coincidono, e se non coincidessero vincerebbe l'host — il che
è desiderabile mentre si lavora e sarebbe una sorpresa in sala. Chi registra i filmati di
riserva ricostruisca prima.

**Fonti:** [M-035](../app/docs/Sources.md#m-035), [M-036](../app/docs/Sources.md#m-036)

---

<a id="adr-0092"></a>
## ADR-0092 — Il `Makefile` sceglie **da dove** si esegue, e il predefinito è la rete

**Data:** 2026-09-03 · **Stato:** Accettata

**Contesto:** dopo il Task 12 lo stesso comando ha due modi di girare, e servono entrambi:
dentro la rete è ciò che il talk mostra, sull'host è ciò che serve mentre si sviluppa — nessun
container da ricostruire, il debugger attaccato, il ciclo corto.

**Decisione:** una variabile `DOVE`, con `rete` come predefinito, che sceglie fra `docker
compose run --rm app` e `uv run --directory app mongolab`. Il predefinito è `rete` perché il
comportamento giusto in sala deve essere quello che si ottiene senza ricordarsi niente. Un
valore diverso da `rete` o `host` viene rifiutato con un messaggio che dice che cosa sono i due,
non solo che il terzo non esiste.

La mappa `COMPOSE_DI_<nome>` traduce il bersaglio nel file Compose. È la **quarta** scrittura
della stessa lista di stack, dopo `BERSAGLI`, i file Compose e il guardiano `CHIEDI_TARGET`, e
una lista scritta quattro volte diverge: tre prove in `tools/tests/test_coerenza_repo.py` la
tengono ferma, e la più importante non controlla i nomi ma le **destinazioni**, perché
`COMPOSE_DI_rs = $(COMPOSE_03_BASE)` è una riga valida che accende un container e si collega
allo stack sbagliato senza dire niente a nessuno.

**Alternative scartate.**

- *`DOVE=host` come predefinito, e `rete` da chiedere.* Metterebbe il modo sbagliato per il
  talk a portata di dimenticanza, e il modo sbagliato qui non fallisce: stampa `topologia
  singola` su un replica set sanissimo, che è una risposta plausibile e falsa.
- *Due famiglie di target, `app-stats` e `app-stats-host`.* Sei target invece di tre, e ogni
  opzione nuova ne aggiunge due.
- *Far scegliere all'applicazione, provando prima la rete e poi l'host.* Un fallback silenzioso
  su una demo che serve proprio a mostrare la differenza fra i due casi.

**Riserve.** `make app-image` costruisce sempre attraverso lo stack 01, perché il servizio è
identico nei tre e costruirlo tre volte produrrebbe tre volte la stessa immagine. Se un giorno
i tre divergessero, quella riga diventerebbe falsa in silenzio — ed è esattamente ciò che la
prova sull'immagine unica impedisce.

**Fonti:** [M-035](../app/docs/Sources.md#m-035)

---

<a id="adr-0093"></a>
## ADR-0093 — Un servizio che si costruisce si giudica sulle righe `FROM` del suo Dockerfile

**Data:** 2026-09-03 · **Stato:** Accettata

**Contesto:** `tools/check_stack.py` pretende, da [ADR-0009](#adr-0009) e
[ADR-0018](#adr-0018), che ogni servizio dichiari un'immagine pinnata per digest e nota a
`tools/images.env`. Il servizio `app` non può obbedire: la sua immagine non viene da un
registro, la costruisce `make app-image` sulla macchina di chi presenta. Il Passo 5 del Task 12
dice che, se una regola esistente vieta qualcosa di nuovo, **la regola ha ragione finché non si
dimostra il contrario**.

La dimostrazione ha richiesto di correggere anche la premessa da cui era partita. La prima
stesura argomentava che un'immagine costruita in locale «non ha un digest». È falso: con
l'archivio immagini di containerd, che è quello attivo su questa Docker Desktop, l'`Id` di
un'immagine *è* il digest del suo manifesto, e `docker image inspect mongolab@sha256:…` la
trova ([M-037](../app/docs/Sources.md#m-037)).

**Decisione:** un servizio che dichiara `build:` è esente dalla regola sull'immagine e soggetto
a una regola equivalente un livello più in basso: le righe `FROM` del suo Dockerfile devono
essere pinnate per digest, e per un digest che `tools/images.env` conosce. `check_stack.py`
risolve il `Dockerfile` a partire da `build.context`, segue i `${ARG}` attraverso `build.args`,
salta gli stadi intermedi e i flag, e protesta se una base è mobile, sconosciuta o non
risolvibile.

Lo scopo della regola originale non si sposta di un millimetro: **nessun bit arriva dalla rete
senza che qualcuno l'abbia fissato.** Per un servizio che si scarica quei bit sono la sua
immagine; per uno che si costruisce sono le sue basi — e sono le uniche che vadano davvero in
rete.

Il digest dell'immagine costruita resta fuori da `images.env` non perché non esista, ma perché
nessun registro l'ha mai servito e cambia a ogni ricostruzione: metterlo là darebbe a
`pull-images.sh --verify` una cosa da cercare in rete che in rete non c'è, e il preflight
fallirebbe la mattina del talk accusando la cache di un difetto che non ha. Ciò che il preflight
controlla è la sola cosa controllabile e la sola che serva: che l'immagine ci sia, con `make
app-image` come rimedio.

**Alternative scartate.**

- *Esentare il servizio e basta.* Lascerebbe le basi libere di essere `python:3.13-slim`, cioè
  un tag mobile, e la prima costruzione senza rete fallirebbe — o peggio riuscirebbe con un
  contenuto diverso da quello provato.
- *Scrivere il digest dell'immagine costruita in `images.env`.* Un digest che nessuno può
  scaricare, che cambia a ogni `make app-image`, e che trasformerebbe `--verify` in un
  controllo che fallisce a caso.
- *Scrivere le basi direttamente nel Dockerfile, pinnate.* Toglie il pin dal posto in cui
  `pull-images.sh` lo aggiorna, e crea due elenchi di immagini da tenere allineati a mano.

**Riserve.** [M-037](../app/docs/Sources.md#m-037) è misurata con l'archivio containerd. Con il
vecchio archivio a grafo `RepoDigests` resta vuoto finché l'immagine non è spinta, e la premessa
sbagliata sarebbe stata vera per caso: la decisione non cambia, la sua motivazione sì. Il
controllo legge il Dockerfile con una regex e non con un parser: gli basta per i `FROM` che
questo repository scrive, e non pretende di capire ogni Dockerfile del mondo.

**Fonti:** [M-037](../app/docs/Sources.md#m-037), [ADR-0009](#adr-0009), [ADR-0018](#adr-0018),
[ADR-0039](#adr-0039)

---

<a id="adr-0094"></a>
## ADR-0094 — `FaseIniziata`, il decimo evento: uno scenario che annuncia invece di stampare

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** la scena del failover è una sequenza di fasi — carico, guasto, elezione, ripresa,
recupero, bilancio — e ciascuna va annunciata: in sala perché il pubblico sappia che cosa sta
guardando, e con `--step` perché la pausa da palco deve dire **che cosa** sta per succedere
prima di aspettare l'Invio. La strada breve era una `print` dentro lo scenario. La strada breve
avrebbe però messo la resa dentro il dominio, che [ADR-0007](#adr-0007) vieta, e avrebbe reso
la scena non verificabile: una prova che asserisce su `capsys` verifica l'impaginazione, non
la sequenza.

**Decisione:** lo scenario emette un decimo evento di dominio, `FaseIniziata`, con il nome
della fase e la sua descrizione, e non stampa niente. I nove eventi precedenti sono di specie
diversa — raccontano un fatto **osservato** (una scrittura è riuscita, un server è cambiato di
ruolo); questo racconta un'**intenzione**, ed è l'unico evento che l'applicazione produce
sapendo già che accadrà. La distinzione è dichiarata nel modulo, perché chi aggiunge l'undicesimo
sappia in quale delle due famiglie sta entrando.

La pausa di `--step` è una funzione che riceve `FaseIniziata` e torna quando può proseguire:
`senza_attesa` non fa niente, `_invio` scrive e legge da stdin. È lo stesso evento a servire i
tre sink e la pausa, che è la ragione per cui la modalità automatica e quella da palco mostrano
davvero la stessa scena e non due scene che si somigliano.

**Conseguenze:** le prove unitarie della scena asseriscono sulla sequenza di eventi che esce da
`RecordingSink`, fasi comprese, senza mai guardare un carattere di output. La pausa si prova
passando una funzione che annota invece di leggere, e non serve simulare una tastiera. Le
registrazioni di riserva del Task 18 mostrano la stessa successione di fasi della scena dal
vivo, per costruzione.

**Alternative scartate.**

- *Una `print` nello scenario.* Rompe ADR-0007 e rende la sequenza inosservabile.
- *Passare i nomi delle fasi alla riga di comando e lasciare che li stampi lei.* La riga di
  comando dovrebbe allora conoscere l'ordine delle fasi, cioè il copione — che è la sola cosa
  che lo scenario possiede davvero.
- *Riusare `MisuraPresa` con un campo `fase`.* Un evento che significa due cose diverse a
  seconda di un campo è un evento che ogni sink deve disambiguare, tre volte.

**Fonti:** [ADR-0007](#adr-0007), [ADR-0082](#adr-0082),
[M-043](../app/docs/Sources.md#m-043)

---

<a id="adr-0095"></a>
## ADR-0095 — `Regia`, la sesta porta: chi fa accadere il guasto non sta dove lo scenario guarda

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** la scena centrale del talk ha bisogno di due cose insieme, e il Task 13 ha scoperto
eseguendo che **un processo solo non può averle entrambe**.

La cronaca dell'elezione — «il primario era `mongo-rs-1:27017`, adesso è `mongo-rs-3:27017`» —
esiste solo se il client fa scoperta, e la scoperta funziona solo da dentro la rete Compose,
dove i nomi dei servizi si risolvono ([M-036](../app/docs/Sources.md#m-036),
[A-016](../app/docs/Sources.md#a-016)). Dall'host lo stesso replica set si raggiunge con
`directConnection=True` su `localhost:27021`: nessuna scoperta, nessuna cronaca, e per giunta
l'indirizzo del primario è un `localhost:27021` che non è il nome di nessun servizio da fermare.

Il guasto, però, è un `docker compose kill`, e richiede il socket del demone. Il container
dell'applicazione **non ce l'ha**, per una scelta del Task 12 che resta valida: montare
`/var/run/docker.sock` dentro un container mostrato in sala vuol dire mostrare, senza dirlo, il
modo più diretto di prendere la macchina che lo ospita.

**Decisione:** una sesta porta, `Regia`, con quattro verbi — `ferma`, `riavvia`, `sospendi`,
`risveglia` — e due adattatori che la implementano in modi opposti:

- `RegiaCompose` **esegue**. Vive sull'host, costruisce la riga di `docker compose` dal frasario
  e la lancia con `subprocess.run` dalla radice del repository.
- `RegiaAnnunciata` **annuncia**. Vive nel container, stampa la riga esatta — quella che si
  incolla in un altro terminale, con entrambi i `--env-file` che
  [M-040](../app/docs/Sources.md#m-040) ha dimostrato obbligatori — e si blocca finché un umano
  non preme Invio.

Quale dei due si costruisce lo decide `punto_di_vista()`, cioè la stessa funzione che già
sceglie il bersaglio; lo scenario non lo sa e non deve saperlo. Il frasario è un dato separato
dall'esecuzione **proprio perché** `RegiaAnnunciata` deve poter comporre una riga senza averne
il diritto di eseguirla.

**Conseguenze:** la scena dal vivo richiede due terminali, e questo va detto al PO prima delle
prove generali: uno mostra la scena, l'altro esegue il guasto che la scena detta. In cambio, la
riga da incollare non si inventa a mano sotto pressione e non può essere sbagliata. La prova di
integrazione automatizza esattamente questo: un processo legge lo stdout del container, esegue
verbatim la riga annunciata e rimanda un Invio — il che, di passaggio, dimostra che la riga
annunciata è davvero incollabile ([M-043](../app/docs/Sources.md#m-043)).

**Alternative scartate.**

- *Montare il socket Docker nel container.* Rifiutata al Task 12 e rifiutata di nuovo qui. Il
  motivo non è cambiato, e in sala peserebbe di più: sarebbe proiettato.
- *Girare tutta la scena dall'host.* Funziona per il guasto e perde la cronaca, cioè la metà
  che vale i cinque minuti dell'Atto II.
- *Un secondo processo «agente» che riceve gli ordini dal container su una socket.* Sposta il
  problema di un livello e aggiunge un componente da spiegare in sala; il valore didattico del
  vincolo — *questo container non può toccare il demone* — sparirebbe dentro l'infrastruttura
  che lo aggira.

**Riserve.** `RegiaAnnunciata` legge da stdin, quindi la scena dal container non gira senza un
terminale interattivo o un processo che ne faccia le veci; la prova di integrazione fa la
seconda cosa, e la sua scadenza è un `threading.Timer` perché un Invio che non arriva è un
comando che non torna mai.

**Fonti:** [M-036](../app/docs/Sources.md#m-036), [A-016](../app/docs/Sources.md#a-016),
[M-040](../app/docs/Sources.md#m-040), [M-043](../app/docs/Sources.md#m-043),
[ADR-0054](#adr-0054), [ADR-0090](#adr-0090), [ADR-0092](#adr-0092)

---

<a id="adr-0096"></a>
## ADR-0096 — L'interruzione si deduce dagli eventi del ponte, non si misura sondando

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** «quanto è durata l'interruzione» è uno dei due numeri che chiudono la scena, e la
strada ovvia per ottenerlo è un ciclo che chiede al cluster chi è il primario finché qualcuno
risponde. Quella strada misura però il proprio intervallo di sondaggio quanto misura
l'elezione: con un sondaggio ogni 500 ms, un'elezione di 10 019 ms e una di 10 400 danno lo
stesso numero, e il numero dipende da una costante che nessuno ha discusso.

Il ponte SDAM del Task 7 riceve intanto, dai listener di PyMongo, gli eventi che descrivono
esattamente ciò che serve: il momento in cui il primario smette di essere tale e il momento in
cui la topologia ne ha uno nuovo. Sono i tempi del driver, non i nostri.

**Decisione:** lo scenario non sonda. Drena la coda del ponte e ricava l'interruzione dalla
distanza fra i due eventi di cambio ruolo che il driver ha già osservato. La conseguenza
importante è che il numero è quello che **il client ha vissuto**, cioè lo stesso che vive
un'applicazione vera: non il tempo in cui il replica set ha eletto, ma il tempo in cui il driver
è rimasto senza un posto dove scrivere. È anche il solo dei due che il pubblico possa mettere in
relazione con le proprie latenze.

Il carico continua per tutta la durata, e la sua interruzione è la controprova: le fasi
mostrano 2 057 scritture prima, 9 006 durante e 4 166 dopo, con p95 che restano attorno ai 51-56
ms. Un numero dedotto e un numero osservato che raccontano lo stesso fatto.

**Conseguenze:** nessun intervallo di sondaggio da giustificare, nessun thread in più, e una
scena che continua a funzionare se il driver cambia le sue soglie — cambierà il numero, non il
modo di ottenerlo. Le prove unitarie possono fabbricare la sequenza di eventi e verificare
l'aritmetica senza un cluster.

**Alternative scartate.**

- *Sondare `hello` in un ciclo.* Misura anche sé stessa, e ogni scelta dell'intervallo è
  arbitraria.
- *Leggere `replSetGetStatus` e usare il timestamp dell'elezione dichiarato dal server.* È un
  numero diverso e più preciso, e risponde a un'altra domanda: quanto ci ha messo **il set**, non
  quanto è rimasto fermo **il client**. Vale la pena nominarlo in sala, non sostituirlo.
- *Cronometrare a mano dal primo errore di scrittura alla prima riuscita.* Dipende dalla
  frequenza delle scritture, che è un parametro della scena, non del failover.

**Riserve.** Il numero dedotto vale quanto vale la puntualità con cui i listener sono chiamati;
[S-010](Sources.md#s-010) dice che gli eventi sono consegnati in modo sincrono e che il thread
che li consegna aspetta il gestore, il che è la ragione per cui il gestore accoda e basta —
[ADR-0019](#adr-0019). Il confronto con la misura indipendente di `feature/02` è la verifica
che la deduzione non stia mentendo: 10 019 ms contro i 9 812-10 943 di
[V-029](Sources.md#v-029) ([M-043](../app/docs/Sources.md#m-043)).

**Fonti:** [S-010](Sources.md#s-010), [V-029](Sources.md#v-029), [V-031](Sources.md#v-031),
[M-043](../app/docs/Sources.md#m-043), [ADR-0019](#adr-0019), [ADR-0089](#adr-0089)

---

<a id="adr-0097"></a>
## ADR-0097 — Il guasto predefinito è `SIGKILL`, e non lo `stop` che il piano scriveva

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** il Passo 2 del Task 13 detta la sequenza del copione e nomina, alla lettera,
`docker compose stop` del primario. Eseguito, `stop` manda `SIGTERM`, e `mongod` che riceve
`SIGTERM` **cede il ruolo con ordine** prima di uscire: [V-029](Sources.md#v-029) misura quella
strada in 574, 480 e 486 ms, senza elezione da raccontare. La stessa misura, con `docker kill`,
dà 9 812, 10 619 e 10 943 ms — che sono i numeri che [V-031](Sources.md#v-031) ha già portato
sulle slide come «forbice 8-10 s».

Il piano e le slide non possono avere ragione tutti e due.

**Decisione:** il verbo `ferma` della regia esegue `docker compose kill -s SIGKILL`, che diventa
il guasto predefinito della scena. `ARRESTO_ORDINATO = ("stop",)` resta nel codice, documentato
e configurabile, perché è il confronto che rende leggibile il numero grande: mezzo secondo
contro dieci, e nel verso opposto all'intuizione di chi si aspetta che «spegnere bene» sia più
lento.

Le slide hanno ragione, il piano ha una svista, e la svista è istruttiva quanto la correzione:
**«fermare un nodo» non è un'operazione sola**, e quale delle due si sceglie decide se il
pubblico vedrà un'elezione o non la vedrà affatto.

**Conseguenze:** la scena riproduce i numeri già misurati, il che è la premessa perché il
confronto del Passo 5 abbia senso. Chi voglia mostrare l'altra scena può, ed è una riga di
configurazione, non una modifica.

**Alternative scartate.**

- *Obbedire alla lettera del piano.* Produrrebbe una scena in cui il primario cambia in mezzo
  secondo e nessuno capisce perché il talk ne parlasse tanto, con due slide che dicono un numero
  diverso da quello proiettato sotto.
- *Togliere `stop` dal codice.* Perderebbe il confronto, che è il pezzo di didattica migliore
  dei due.
- *Cambiare le slide.* Le slide riportano una misura fatta, non un'opinione.

**Riserve.** Va portata al PO come correzione dichiarata del piano, non applicata in silenzio:
il piano è un documento del progetto e la sua lettera contava. Da segnalare anche che i tre
valori di V-029 e i 10 019 ms di [M-043](../app/docs/Sources.md#m-043) dipendono dalle
impostazioni di elezione di questo replica set; su un set configurato diversamente la forbice si
sposta, e la frase da dire in sala è «su questo lab», non «in MongoDB».

**Fonti:** [V-029](Sources.md#v-029), [V-031](Sources.md#v-031),
[M-043](../app/docs/Sources.md#m-043)

---

<a id="adr-0098"></a>
## ADR-0098 — `--step` e `--sink rich` si rifiutano a vicenda, e il rifiuto arriva prima della scena

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** `--step` mette in pausa prima di ogni fase e riparte con un Invio: legge da stdin,
sul thread della scena. La resa `rich` tiene aperto un `Live` che ridisegna quattro volte al
secondo su un thread suo ([ADR-0085](#adr-0085), [M-027](../app/docs/Sources.md#m-027)). Le due
cose vogliono lo stesso terminale: il prompt «Invio per proseguire» finisce sotto il ridisegno
successivo, e chi tiene la tastiera dal palco non vede più che cosa sta aspettando. È il genere
di difetto che non fallisce nessuna prova e rovina esattamente un'occasione.

**Decisione:** la combinazione è rifiutata come errore di parametro, prima che la scena
cominci — prima della connessione, del carico e della collezione di lavoro. Il messaggio dice
perché, e detta la riga giusta: dal palco è `--step --sink plain`, che è **la stessa** con cui si
girano le registrazioni di riserva.

Rifiutare invece di degradare in silenzio a `plain` è deliberato: una scena che cambia da sola
la propria resa è una scena che dal vivo mostra qualcosa di diverso da quello che si è provato
la sera prima.

**Conseguenze:** la modalità da palco è `plain`, punto — il che semplifica anche le prove
generali, perché la registrazione asciinema e la scena dal vivo usano la stessa riga. La resa
`rich` resta quella dei comandi che nessuno interrompe, `watch` in testa.

**Alternative scartate.**

- *Sospendere il `Live` durante la pausa.* Tecnicamente possibile e appeso a un dettaglio
  privato di Rich, che [M-027](../app/docs/Sources.md#m-027) ha già mostrato essere `_RefreshThread`:
  appoggiarcisi sarebbe un errore anche se fosse documentato.
- *Degradare a `plain` con un avviso.* L'avviso scorre via e la scena non è quella provata.
- *Leggere la pausa da un altro descrittore.* Risolve il conflitto e ne crea uno peggiore: dal
  palco bisognerebbe ricordarsi dove premere Invio.

**Riserve.** Da portare al PO: è una biforcazione vera fra ciò che si vorrebbe (la scena bella
**e** la pausa) e ciò che si può, e la risposta scelta rinuncia alla prima. Se le prove generali
mostrassero che la resa `plain` non regge la proiezione, la decisione va riaperta — con la
sospensione del `Live` come prima candidata, e con il costo dichiarato.

**Fonti:** [M-027](../app/docs/Sources.md#m-027), [S-018](Sources.md#s-018),
[ADR-0085](#adr-0085)

---

<a id="adr-0099"></a>
## ADR-0099 — L'attesa del primario vive nell'infrastruttura, perché la riga di comando resti senza PyMongo

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** alla prima esecuzione vera, `demo failover` è uscito con «nessun primario in vista
su «rs»» contro un replica set sanissimo ([M-042](../app/docs/Sources.md#m-042)). La causa non
era il cluster: `Inspector.topology()` legge la descrizione che il driver **ha già** in mano, e
nei primi millisecondi dopo `MongoClient(...)` quella descrizione è ancora vuota, perché la
scoperta comincia in quel momento e prosegue su thread suoi. **Guardare non è aspettare.**

La correzione è un `ping`, che essendo un comando su `admin` va sul primario per impostazione
predefinita ([A-017](../app/docs/Sources.md#a-017)) e quindi torna esattamente quando la domanda
successiva ha una risposta. La tentazione era metterlo in `cli.py`, dove sta la chiamata. La
guardia `test_pymongo_si_importa_solo_nell_infrastruttura` lo vieta — e la sua docstring dice, da
sempre, che «`cli.py` è proprio il posto in cui la tentazione arriva».

**Decisione:** la guardia ha ragione, e non si tocca. L'attesa vive in
`infrastructure/bersagli.py`, accanto all'unico `MongoClient(...)` del repository, e traduce il
`ServerSelectionTimeoutError` di PyMongo in un `SenzaPrimario` di questo strato. La riga di
comando cattura `SenzaPrimario` e ne ricava la frase, che è cosa sua: `niente_da_fermare`
**restituisce** l'eccezione di `typer` invece di sollevarla, così il messaggio — la parte che
finisce davanti al pubblico — si prova senza dover fabbricare un replica set malato.

L'attesa massima non è un parametro: è il `serverSelectionTimeoutMS` che `connetti` già fissa.
Prenderlo di nuovo qui vorrebbe dire poter dichiarare un'attesa diversa da quella che si aspetta
davvero.

**Conseguenze:** il codice è finito meglio di dove voleva andare — un fatto
dell'infrastruttura da una parte, la frase per la sala dall'altra, ciascuno provato per conto
suo. Il difetto vale anche come lezione sui limiti dei doppi: 518 prove unitarie verdi non lo
vedevano, perché i doppi rispondono subito e un cluster vero no.

**Alternative scartate.**

- *Rilassare la guardia per `cli.py`.* Una guardia che cede la prima volta che dà fastidio non
  è una guardia, ed è la sola cosa che tenga `MongoClient(...)` in un punto solo del repository.
- *Un ciclo che rilegge `topology()` finché non compare un primario.* Reimplementa la selezione
  del server che il driver già fa, con un intervallo arbitrario in più.
- *Aggiungere l'attesa dentro `connetti`.* Farebbe pagare a `stats`, `watch` e `workload`
  un'attesa che non hanno chiesto, e a `watch` in particolare toglierebbe proprio la scena che
  deve mostrare: la topologia mentre si forma.

**Fonti:** [A-017](../app/docs/Sources.md#a-017), [M-042](../app/docs/Sources.md#m-042),
[ADR-0007](#adr-0007), [ADR-0090](#adr-0090)

---

<a id="adr-0100"></a>
## ADR-0100 — Gli strumenti di backup restano nei nodi, e l'Atto III si gira dall'host

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** la scena del backup a caldo ha bisogno di eseguire `mongodump` e `mongorestore`.
La strada che sembrava ovvia — metterli nell'immagine dell'applicazione, così che `mongolab`
li chiami come chiama qualunque altro sottoprocesso — è stata provata e non funziona. Copiare i
due binari dall'immagine `mongo` pinnata dentro `python:3.13-slim` produce un container che si
ferma su `libgssapi_krb5.so.2: cannot open shared object file`
([M-044](../app/docs/Sources.md#m-044)): gli strumenti sono compilati contro le librerie Kerberos
di Debian, che nell'immagine slim non ci sono. La via d'uscita apparente — `apt-get install
mongodb-database-tools` — aggiungerebbe all'immagine un pacchetto che nessun `FROM` dichiara, e
`check_stack.py` verifica proprio che ogni base sia pinnata ([ADR-0093](#adr-0093)); in più
richiederebbe rete al `build`, che il laboratorio offline non ha.

Ci sono già tre copie di quegli strumenti, e sono nei nodi: l'immagine `mongo` li contiene.
Raggiungerli vuol dire `docker compose exec`, e chi lo esegue deve avere il socket del demone
Docker. Il container dell'applicazione non ce l'ha, perché il Task 9 ha deciso di non montarglielo.
L'host sì.

**Decisione:** `mongodump` e `mongorestore` girano **dentro un nodo dello stack**, raggiunti con
la stessa `ComandiCompose` che la regia del failover usa per fermare un container; `demo
backup-live` e `demo restore` girano **dall'host**, e da dentro la rete si rifiutano dicendo
perché. È l'inverso esatto di `demo failover`, che vuole la scoperta della topologia e quindi la
rete Compose ([M-019](../app/docs/Sources.md#m-019)).

Tre conseguenze sono parte della decisione:

- **L'indirizzo che gli strumenti ricevono è quello di rete**, non quello dell'host: il processo
  gira dentro un container, dove `mongo-rs-1` si risolve e `localhost` è sé stesso. Lo costruisce
  `host_interno_di`, nella forma `rs0/uno,due,tre`.
- **Le due scene accettano solo un bersaglio che si presenti come replica set.** `--oplog` vuole
  un oplog, e uno standalone non ne ha ([ADR-0022](#adr-0022)); attraverso un `mongos` il dump
  attraversa gli shard uno per uno, senza un istante comune, e non è la fotografia che la scena
  promette. Il rifiuto guarda la proprietà — `Vista.replica is not None` — e non il nome del
  bersaglio.
- **Il nodo predefinito è il primo dello stack, non il primario.** Il dump atterra nel filesystem
  del container in cui gira, e `demo restore` deve ritrovarlo lì qualche minuto dopo: un
  predefinito che seguisse il primario cambierebbe nodo dopo l'elezione dell'Atto II, e la copia
  finirebbe in un container mentre il restore la cercherebbe in un altro.

**Conseguenze:** l'immagine dell'applicazione resta quella che è — un `FROM` pinnato e niente
`apt` — e il Task 9 non va riaperto. Il prezzo è un'asimmetria che chi presenta deve conoscere: i
due Atti consecutivi del Blocco 2 si lanciano da due posti diversi, e la riga
`make ... DOVE=host` non è intercambiabile con quella di dentro. È dichiarata nella docstring del
gruppo `demo`, nei due rifiuti, e in `docs/03-amministrazione/backup-restore.md`.

Ce n'è una seconda, più sottile: dall'host il client arriva su `localhost:27021` con
`directConnection`, quindi scrive **solo** su `mongo-rs-1`. Se l'Atto II è appena passato, quel
nodo è rientrato da poco e non ha ancora ripreso il ruolo — `priority: 2` glielo restituisce, ma
non istantaneamente ([M-048](../app/docs/Sources.md#m-048) misura 4,0 s). Perciò `demo
backup-live` verifica di avere un primario **in vista** prima di far partire il carico, e non si
accontenta del `ping`: in connessione diretta un `ping` riesce anche su un secondario, e il guasto
comparirebbe alla prima scrittura, con la scena già cominciata.

**Alternative scartate.**

- *Gli strumenti nell'immagine dell'applicazione.* Misurata e fallita ([M-044](../app/docs/Sources.md#m-044)).
- *`apt-get install mongodb-database-tools` nel `Dockerfile`.* Rompe la verifica dei `FROM`
  pinnati di [ADR-0093](#adr-0093) e vuole rete al `build`.
- *Montare il socket Docker nel container dell'applicazione.* Ribalterebbe una decisione del Task
  9 per una scena sola, e darebbe al container dell'applicazione il potere di fermare l'host.
- *`docker exec` invece di `docker compose exec`.* Nominerebbe il container invece del servizio e
  perderebbe i due `--env-file` obbligatori ([M-040](../app/docs/Sources.md#m-040)), cioè la sola
  cosa che fa arrivare la credenziale senza passarla in `argv` ([ADR-0054](#adr-0054)).
- *Un volume condiviso per il dump, così che l'applicazione lo veda.* Il container
  dell'applicazione è `--rm` e senza volumi scrivibili, e aggiungerne uno per far vedere un file
  che nessuno legge dall'applicazione è complessità senza destinatario: fra `backup-live` e
  `restore` il dump deve sopravvivere, e nel filesystem del nodo sopravvive già.

**Fonti:** [M-019](../app/docs/Sources.md#m-019), [M-040](../app/docs/Sources.md#m-040),
[M-044](../app/docs/Sources.md#m-044), [M-045](../app/docs/Sources.md#m-045),
[M-048](../app/docs/Sources.md#m-048), [ADR-0022](#adr-0022), [ADR-0054](#adr-0054),
[ADR-0093](#adr-0093), [ADR-0095](#adr-0095)

---

<a id="adr-0101"></a>
## ADR-0101 — La finestra della seconda misura è quella del dump, e non una durata scelta prima

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** l'Atto III mette due ritmi accanto: il carico da solo, e lo stesso carico mentre
`mongodump` copia. Il secondo va misurato **esattamente** nella finestra in cui il dump gira, e
quella finestra non si sa prima: [M-045](../app/docs/Sources.md#m-045) misura 476 ms su un `lab`
da poche migliaia di documenti, ma dipende dalla macchina e dal dataset.

Con una durata fissa il conto si sfalsa in tutti e due i versi. Se la finestra è più lunga del
dump, i secondi dopo la fine entrano nella media e diluiscono l'effetto: un crollo totale di mezzo
secondo dentro un campione da venti comparirebbe come un calo del due per cento. Se è più corta, si
misura un pezzo di dump e si dichiara un numero che vale per un'altra durata. In tutti e due i casi
la scena mostra un numero che non è quello che dice di mostrare — cioè fa la cosa che il §6.3 del
design rimprovera ai benchmark altrui.

**Decisione:** `WorkloadRunner.esegui` accetta `finche: Continua | None`, una condizione che i
worker interrogano prima di ogni operazione; la scena del backup la lega alla vita del processo
`mongodump`, e il carico finisce quando finisce il dump.

**`finche` restringe un limite, non ne fa le veci.** Passarla senza `scritture` né `durata_s` alza
`ValueError`: una condizione che dipende da un processo esterno resta vera per sempre se quel
processo si pianta, e una scena che non termina in sala è peggio di una scena che termina male. Il
tetto resta, come rete di sicurezza, ed è esposto come `--tetto`.

*Per una stagione quel tetto è arrivato al solo `WorkloadRunner`, e la rete di sicurezza teneva la
metà leggera: il carico mollava, la scena no. [ADR-0118](#adr-0118) lo fa arrivare fino alla porta,
che è l'unico posto da cui si può onorare.*

**Conseguenze:** i due numeri della prima riga sono confrontabili, e la percentuale che li separa
significa qualcosa. Il prezzo è che la seconda finestra può essere breve — mezzo secondo — e quindi
rumorosa: la scena lo dichiara mostrando anche le due conte assolute, così chi guarda vede su
quante scritture il numero è stato calcolato. Il rapporto non conclude al posto del pubblico: scrive
il calo con il segno e si ferma lì, e un calo negativo — il ritmo che sale — è un risultato
possibile e non un errore di calcolo.

**Alternative scartate.**

- *Una durata fissa per la seconda fase.* È il difetto descritto sopra.
- *Fermare il carico dall'esterno con un `Event` gestito dalla riga di comando.* Metterebbe in
  `cli.py` la conoscenza di quando il dump finisce, che è dello scenario; e la condizione la
  chiamano tutti i worker dai loro thread, quindi va documentata come tale — cosa che il tipo
  `Continua` fa nel posto giusto.
- *Misurare il ritmo campionandolo a intervalli e ritagliando la finestra dopo.* Aggiunge un
  campionatore, un intervallo arbitrario, e l'errore di quantizzazione proprio dove la finestra è
  più corta.

**Fonti:** [M-045](../app/docs/Sources.md#m-045), [M-047](../app/docs/Sources.md#m-047),
[ADR-0019](#adr-0019), [ADR-0100](#adr-0100)

---

<a id="adr-0102"></a>
## ADR-0102 — Il restore scrive accanto all'originale, mai sopra, e la scena precedente detta la riga successiva

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** ciò che l'Atto III deve far vedere è che una copia presa **a caldo** non contiene i
documenti scritti mentre veniva presa. Quel divario è il prezzo di non aver fermato il servizio, ed
è l'unico numero della scena che il pubblico deve portarsi via.

Restaurare sopra il database di origine lo cancella. I documenti mancanti nella copia sono ancora
lì, nell'originale; `mongorestore` non toglie ciò che trova, quindi i conteggi combacerebbero — e
combacerebbero **proprio perché** il restore è riuscito. La scena si distruggerebbe da sé, in
silenzio, e sembrerebbe un successo.

Il divario non si può nemmeno colmare: `mongodump --oplog` porta via l'oplog della finestra, ma
`--oplogReplay` è incompatibile con la rinomina dei namespace che serve a restaurare altrove
([ADR-0084](#adr-0084)). O si restaura sopra riapplicando l'oplog, o si restaura accanto e si
guarda la differenza. La seconda è la scena.

**Decisione:** `demo restore` scrive in un database diverso — predefinito `lab_ripristinato` — e
rifiuta `--into lab` nominando la ragione. Il rifiuto guarda il nome del database di partenza, non
una lista di nomi vietati.

Le due scene sono due comandi consecutivi sul palco, e il secondo consuma ciò che il primo ha
lasciato nel nodo. Perciò: il percorso del dump ha un predefinito fisso (`/tmp/mongolab-backup`,
non uno con la data), il database di destinazione ne ha un altro, e `demo backup-live` **stampa
già scritta** la riga di `demo restore` che gli va dietro, con dentro il nome della collezione di
carico — che porta l'orario nel nome e non si indovina. Ricopiarlo a mano davanti alla sala è il
modo più prevedibile di sbagliare un comando.

**Conseguenze:** dopo la scena restano un database in più e una collezione di carico in più, che
`make reset-02` porta via. Il rapporto scrive la differenza e ne dice la provenienza in una riga —
«scritti mentre il dump era in corso: stanno nell'oplog, che il restore non riapplica» — perché un
numero senza la sua causa accanto viene letto come un guasto.

Misurato sullo stack vero: 3 908 documenti all'origine, 3 802 nella copia, **106** di differenza
([M-047](../app/docs/Sources.md#m-047)).

**Alternative scartate.**

- *Restaurare sopra `lab`.* Descritto sopra: cancella la prova.
- *Un percorso di dump con la data, per non sovrascrivere il precedente.* Renderebbe obbligatorio
  ricopiarlo fra i due comandi, che è precisamente ciò che la riga suggerita evita. Chi ne vuole
  due li nomina con `--out`.
- *Un comando solo che faccia dump e restore di fila.* Toglierebbe la pausa in cui chi presenta
  spiega che cosa sta per succedere, e nasconderebbe che sono due strumenti diversi con due
  invocazioni diverse — che è metà di quello che la sezione sta insegnando.

**Fonti:** [M-047](../app/docs/Sources.md#m-047), [ADR-0084](#adr-0084), [ADR-0100](#adr-0100)

---

<a id="adr-0103"></a>
## ADR-0103 — `ChunkMigrated` esce dal dominio: un evento che questo laboratorio non produce

**Data:** 2026-09-04 · **Stato:** Accettata · **Corregge:** il §6.3 di
[`2026-08-24-design.md`](00-progetto/2026-08-24-design.md)

**Contesto:** il §6.3 del design elencava otto eventi, e l'ottavo era `ChunkMigrated` —
`collezione`, `da_shard`, `a_shard`, `chunk`. Al Task 3 è stato scritto insieme agli altri sette,
congelato e slottato come loro, con una docstring che dichiarava già la propria condizione di
esistenza: se durante la scena dello sharding fosse risultato non osservabile dal client, sarebbe
diventato «una voce in `Sources.md` e un ADR, non un campo morto nel codice». Il Passo 2 del Task
15 chiedeva di trovargli finalmente chi lo emette.

Non c'è nessuno. [ADR-0069](#adr-0069) aveva già stabilito che il balancer di una 7.0 fa due
mestieri e che qui ne esercita uno solo — l'AutoMerger fonde, e non migra. Il Task 15 l'ha
**misurato** invece di ricordarlo: `balancerStatus` risponde `mode: full` e 1 153 giri, e
`config.changelog`, che conserva le voci dall'`addShard` del giorno dell'inizializzazione, non ne
ha **una sola** di tipo `moveChunk`. Due `merge`, zero migrazioni
([M-049](../app/docs/Sources.md#m-049)).

La ragione sta nel disegno dello stack e non in un guasto: `lab.ordini` è distribuita su
`{_id: "hashed"}`, e una chiave hashed sparpaglia i documenti fra gli shard **all'inserimento**. I
due shard restano a un chunk ciascuno e a metà dei documenti ciascuno; non c'è nessuno sbilancio da
correggere, e il balancer migra solo quando qualcuno si è sbilanciato. Che non succeda non è un
limite del lab: è precisamente ciò che il Blocco 3 vuole far vedere.

**Decisione:** `ChunkMigrated` esce da `domain/eventi.py`. Al suo posto resta un commento che dice
che stava lì, quando è uscito e con quale misura — un buco nominato costa meno di un buco muto,
perché il prossimo che cerca l'evento nel design lo trova invece di ricostruirlo. La guardia
`test_gli_eventi_del_design_sono_nove_e_sono_quelli` scende da dieci nomi a nove, ed è il punto in
cui la decisione si paga: rimetterlo significa cambiare quell'elenco, cioè accorgersene.

**Conseguenze:** il dominio ha nove eventi — otto dal §6.3 meno uno, più
[`PrimaryWaitAbandoned`](#adr-0082) e [`FaseIniziata`](#adr-0094). La scena dello sharding mostra i
chunk **fermi**, e lo dichiara: `bilancio · sbilancio 0 punti · chunk 0 in più` è una riga che
afferma qualcosa, e afferma il vero. Le tre pagine che tenevano l'evento fra i dubbi aperti —
`03-eventi-immutabili.md`, `04-eventi-del-driver-e-concorrenza.md`,
`08-il-ponte-sdam-e-i-thread-del-driver.md` — lo chiudono citando questo ADR. Il design del 24
agosto resta com'è scritto: è un documento datato, e la divergenza è registrata qui.

**Alternative scartate.**

- *Tenerlo, non emesso.* È esattamente il campo morto che la sua docstring vietava. Un dominio in
  cui un evento non ha emittente insegna a chi legge che l'elenco degli eventi è una lista di
  intenzioni e non di fatti, e a quel punto non ne garantisce più nessuno.
- *Emetterlo leggendo `config.changelog` in polling.* Un componente in più, un permesso in più su
  `config`, un thread in più — per una coda che resta vuota. E se una migrazione avvenisse davvero,
  arriverebbe con un ritardo che la cronaca non saprebbe dichiarare, cioè con un istante sbagliato
  addosso in un dominio il cui unico campo comune è l'istante.
- *Provocare una migrazione a scena aperta*, spegnendo uno shard o distribuendo su una chiave
  crescente perché si sbilanci. Sono decine di secondi di attesa dentro un blocco che ne ha dieci,
  e cambierebbero lo stack per far accadere una cosa che l'architettura del lab non fa. Il Blocco 3
  dimostra dove finiscono i documenti, non che il balancer esista.

**Fonti:** [M-049](../app/docs/Sources.md#m-049), [ADR-0069](#adr-0069), [ADR-0082](#adr-0082),
[ADR-0094](#adr-0094)

---

<a id="adr-0104"></a>
## ADR-0104 — La distribuzione per shard diventa una risposta strutturata, e la collezione un parametro

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** fino al Task 14 `ClusterInspector.shard_distribution()` restituiva una
`tuple[ContoShard, ...]` e leggeva la collezione dal costruttore dell'ispettore. Entrambe le scelte
avevano una ragione, ed entrambe smettono di reggere davanti al Blocco 3.

**La tupla vuota diceva due cose opposte.** «Non è uno sharded cluster» e «è uno sharded cluster,
ma questa collezione non è distribuita» arrivavano allo scenario con lo stesso valore. Il Blocco 3
esiste per mostrare **precisamente il secondo caso accanto al terzo** — la collezione di carico che
sta tutta su uno shard, e `lab.ordini` che sta su due — e una scena non può poggiare su un valore
che confonde i due fatti che deve contrapporre.

**La collezione dal costruttore** era una scelta difensiva, e la sua ragione è scritta in
`inspector.py`: un ispettore capace di cambiare bersaglio a ogni chiamata rende possibile una
schermata con due numeri accanto che non parlano della stessa cosa. Il Blocco 3 accosta due
collezioni **apposta**, e la difesa impediva la scena invece di un errore.

Le tre fonti che rispondono sono state interrogate invece che dedotte
([M-050](../app/docs/Sources.md#m-050)): `$shardedDataDistribution` distingue «distribuita e vuota»
— una riga con tutti gli shard a zero — da «non distribuita», che non produce **nessuna** riga;
`config.collections` per una collezione non distribuita non ha proprio la voce; `config.databases`
nomina lo shard primario del database, e `$collStats` conferma che è lì che stanno i documenti.

**Decisione:** la porta restituisce `Distribuzione(collezione, distribuita, primario, conti)` e
prende la collezione come parametro. Il tipo distingue i tre stati con due campi, e la tabella che
li elenca sta nella sua docstring:

| `primario` | `distribuita` | che cosa significa                                |
| ---------- | ------------- | ------------------------------------------------- |
| `None`     | `False`       | non è uno sharded cluster: non c'è niente da dire |
| uno shard  | `False`       | è un cluster, ma la collezione sta **intera** lì  |
| uno shard  | `True`        | è un cluster, e il catalogo la conosce            |

Il rischio dei due numeri che non parlano della stessa cosa non è stato risolto vietando la
domanda, ma facendo sì che la risposta **si presenti**: `Distribuzione` porta con sé il nome della
collezione di cui parla, e la presentazione lo stampa. La difesa è passata dal costruttore al dato.

**Conseguenze:** `documenti`, `chunk` e `quota()` diventano proprietà del tipo invece di calcoli
sparsi in chi chiama, e `chunk == 0` è la risposta **giusta** per una collezione non distribuita,
non un dato mancante. La quarta combinazione — `primario None` e `distribuita True` — non è
rappresentabile in un cluster reale, e il tipo non la vieta: sarebbe una guardia contro un errore
di chi costruisce l'oggetto, non contro un fatto del mondo, in un dominio che di validazione non ne
ha da nessun'altra parte.

**Alternative scartate.**

- *Un `bool` in più accanto alla tupla.* Due valori di ritorno che vanno tenuti coerenti da chi
  chiama sono la premessa della prossima schermata sbagliata.
- *Sollevare un'eccezione quando non è uno sharded cluster.* «Non sei in un cluster» è una risposta
  legittima a una domanda legittima — è ciò che la scena dice allo stack 01 e allo stack 02 — e
  farne un'eccezione obbligherebbe a un `try` intorno a una riga di rapporto.
- *Un secondo ispettore per la seconda collezione.* Due client, due topologie, due fotografie prese
  in due istanti: esattamente il disallineamento da cui il costruttore voleva difendere.

**Fonti:** [M-050](../app/docs/Sources.md#m-050), [ADR-0064](#adr-0064), [ADR-0088](#adr-0088)

---

<a id="adr-0105"></a>
## ADR-0105 — `QueryPlanner`, la settima porta: il piano si legge, e non lo si esegue

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** il Passo 3 del Task 15 chiede due righe sullo schermo: una query mirata e una
scatter-gather, con accanto ciò che il router ha deciso di farne. È una domanda che nessuna delle
sei porte sa fare. `DocumentStore` scrive e legge documenti; `ClusterInspector` guarda il cluster,
non una query.

La tentazione era aggiungere `explain` a `DocumentStore`, che è già l'oggetto che ha la collezione
in mano. Sarebbe una promessa che la maggioranza delle sue implementazioni non mantiene: i doppi in
memoria non hanno un piano da restituire, e un metodo che quasi tutti implementano sollevando
`NotImplementedError` è una porta larga travestita da porta stretta.

La forma di `explain()` è stata misurata sui tre stack ([M-051](../app/docs/Sources.md#m-051)): lo
stadio sta sempre in `queryPlanner.winningPlan.stage`; la chiave `shards` compare **solo**
attraverso un router, e fuori da un cluster il piano non nomina nessuno shard; l'ordine in cui il
server elenca gli shard non è quello del nome — `['shard2rs', 'shard1rs']` — quindi due schermate a
minuti di distanza potrebbero elencarli in ordine diverso senza che sia cambiato niente.

**Decisione:** una settima porta, `QueryPlanner`, con un metodo solo, `explain(filtro) -> Piano`.
`Piano` porta `stadio`, `shard` e il filtro, e `mirata` è una proprietà che si ricava da un campo
che si vede.

Lo stadio viaggia **verbatim** fino allo schermo: `SINGLE_SHARD` e `SHARD_MERGE` sono le parole che
chi guarda ritroverà in `explain()` la prima volta che proverà da solo, e tradurle in un booleano
significherebbe tenere aggiornato un dizionario al posto del server — il giorno in cui comparisse
una terza parola, un campo di testo la mostra e un booleano la nasconde. Gli shard si consegnano
**ordinati**, perché il server non li ordina e una scena che cambia ordine da sola insegna a
diffidarne.

Una porta si disegna guardando **chi la chiama**, non chi la implementa. Qui la chiama un solo
scenario, e la soddisfa un solo adattatore: `PymongoStore`, che la collezione ce l'ha già, adesso
passa per due porte invece che per una. Che un adattatore ne soddisfi due non è un'eccezione da
giustificare — è ciò che si ottiene quando le porte sono `Protocol` strutturali e nessuno le
eredita.

**Conseguenze:** le porte diventano sette, e `app/docs/02-porte-e-doppi.md` lo registra. Fuori da un
cluster `Piano.shard` è vuoto — sullo stack 01 e sullo stack 02 lo stadio è `IDHACK` e la chiave
`shards` non c'è proprio — e la presentazione lo dice invece di stampare uno zero: «nessuno shard:
qui non c'è un router». Il comando comunque rifiuta i due stack non sharded prima di arrivarci
([ADR-0107](#adr-0107)).

**Alternative scartate.**

- *`explain` dentro `DocumentStore`.* Vedi sopra: allarga una porta che tutti implementano per un
  bisogno che ha un chiamante solo.
- *`explain` dentro `ClusterInspector`.* Quella porta risponde su cluster, database e collezione;
  una query non è nessuna delle tre, e il suo adattatore non ha in mano la collezione su cui
  eseguirla.
- *Restituire il dizionario grezzo di `explain()`.* Farebbe entrare la forma di una risposta di
  PyMongo dentro lo scenario, cioè dentro il dominio, che è precisamente ciò contro cui l'esagono
  esiste — e la guardia che tiene `pymongo` fuori da tutto ciò che non è `infrastructure/` non se
  ne accorgerebbe, perché un `dict` non si importa.
- *Un booleano `mirata` come tipo di ritorno.* Butta via la parola per cui la scena esiste.

**Fonti:** [M-051](../app/docs/Sources.md#m-051), [ADR-0095](#adr-0095)

---

<a id="adr-0106"></a>
## ADR-0106 — Il Blocco 3 carica `lab.ordini`, e l'accoppiamento temuto non si paga

**Data:** 2026-09-04 · **Stato:** Accettata · **Chiude la riserva di:** [ADR-0088](#adr-0088)

**Contesto:** ADR-0088 si era chiuso con una riserva che nominava questo task: sullo stack 03 la
collezione del carico **non è distribuita**, perché `docker/03-sharded/init/30-dati-demo.js`
distribuisce `lab.ordini` e una collezione creata al volo resta intera sullo shard primario. Il
confronto fra architetture avrebbe dovuto o distribuire la collezione appena creata, o dichiarare
che stava misurando un solo shard.

Il Blocco 3 fa una terza cosa, ed è la scena: carica **entrambe**. La collezione nuova, non
distribuita, è il metro; `lab.ordini`, distribuita, è la misura. Le due colonne accanto sono
l'intero contenuto didattico del blocco, e per averle serve scrivere in `lab.ordini`.

Fra le alternative che ADR-0088 aveva scartato c'era «far partire il generatore dopo la fine del
seed», rifiutata perché accoppia il generatore a un numero che vive in tre `init/*.js`. Scrivere in
`lab.ordini` sembrava riaprire quell'accoppiamento, ed è stato accettato in quanto tale — poi
misurato, e non si paga.

`lab.ordini` sullo stack 03 contiene **34 415** documenti: 20 000 con `_id` intero, che sono il
seed, e 14 415 con `_id` `ObjectId` e un campo `indice`, che sono le corse dell'applicazione. Non
si sono mai scontrati, e non possono: le scene di `demo` scrivono con `documento_progressivo`, che
**non tocca `_id`** e lascia che sia il server a generarlo. L'unico che numera gli `_id` è
`DataGenerator.documento`, cioè `mongolab workload`, che ha la sua collezione per corsa e la
conserva.

**Decisione:** `demo sharding` scrive in `lab.ordini` — il valore predefinito di `--collection`,
non un nome scritto nel codice — e in una collezione `carico-<AAAAMMGG-hhmmss>` creata dalla stessa
`collezione_di_carico()` delle altre scene. Annuncia entrambe con la formula condivisa
`carico in lab.<nome>`, che è la riga da cui chi presenta — e la prova d'integrazione — ricava che
cosa togliere dopo.

La pulizia resta a `reset-demo` come vuole ADR-0088, e adesso ha un criterio che prima non le
serviva: i documenti dell'applicazione dentro `lab.ordini` si riconoscono da
`{_id: {$type: "objectId"}}`, e il seed no. La collezione del seed non si cancella, si sfoltisce.

**Conseguenze:** dopo la scena `lab.ordini` ha qualche migliaio di documenti in più, ripartiti fra
gli shard come tutti gli altri, e la riga `arrivati` dello schermo dice esattamente quanti ne sono
arrivati su ciascuno **in questa corsa** — che è il numero della scena, mentre il totale per shard è
il contesto. Ripetere la scena in sala è sicuro: nessun `_id` duplicato, nessuna `drop` implicita.
Chi vuole lasciare `lab.ordini` intatta ha `--collection` e paga il prezzo di caricare una
collezione che nessuno ha distribuito, cioè di non vedere niente.

**Alternative scartate.**

- *Distribuire al volo la collezione di carico.* Un comando `shardCollection` dentro una scena è un
  atto sul catalogo del cluster nascosto in un comando che dice di generare carico, e lascerebbe
  dietro di sé collezioni distribuite che `reset-demo` deve poi togliere dal `config` oltre che dai
  dati. In più toglierebbe il metro: senza la collezione **non** distribuita non c'è confronto.
- *Una collezione fissa distribuita una volta per tutte nel seed.* È `lab.ordini`. Farne una seconda
  identica accanto significa aggiungere un file al `docker/03-sharded/init/` per non toccare una
  collezione che si può toccare.
- *Non scrivere affatto e leggere solo la distribuzione a riposo.* È ciò che `feature/03` sapeva già
  fare, ed è il motivo per cui la sua pagina dichiarava scoperto «il comportamento sotto carico».

**Fonti:** [ADR-0088](#adr-0088), [ADR-0064](#adr-0064), [M-050](../app/docs/Sources.md#m-050)

---

<a id="adr-0107"></a>
## ADR-0107 — Il limite del Blocco 3 è un conteggio, e il blocco si gira solo sullo sharded cluster

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** la prima esecuzione vera della scena, quando il limite era ancora una durata come
nelle altre tre, ha stampato in fondo:

```
carico      4288 senza chiave · 4415 con chiave · non è lo stesso carico
```

Sei secondi per corsa, gli stessi otto scrittori, pochi secondi di distanza — e due conteggi
diversi ([M-052](../app/docs/Sources.md#m-052)). Il tre per cento non è molto, e non è il punto: il
punto è che la scena si chiama «lo stesso carico due volte», e con due conteggi diversi la
differenza fra le colonne non è più attribuibile alla sola chiave di shard. La riga di garanzia
funzionava — ha detto il vero — e ciò che denunciava era un difetto di disegno, non un caso.

Nessuna prova unitaria poteva vederlo: i doppi fanno esattamente il numero di scritture che il
copione chiede. Il fatto vive nel punto in cui un limite di tempo incontra due throughput diversi,
cioè in nessuno dei due.

**Decisione:** `demo sharding` è l'unica delle quattro scene senza `--carico`. Il suo limite è
`--scritture`, predefinito 5 000, e le due corse diventano uguali **per costruzione** — non per
fortuna. La riga che dichiara i due conteggi resta a schermo comunque: una garanzia che nessuno
controlla è una speranza.

Cinquemila per corsa costano circa sette secondi sullo stack 03, cioè quattordici in tutto, contro i
dieci delle altre scene. Lo sforo è deliberato ed è stato accettato dal PO: è il prezzo della
seconda colonna, e senza la seconda colonna la prima non dimostra niente.

Nella stessa decisione sta il rifiuto degli altri due stack. Su un mongod solo non ci sono shard fra
cui ripartire niente, e `explain()` non nomina nessuno shard perché non c'è nessun router che
riparta la domanda; su un replica set ci sono tre nodi con gli **stessi** dati, non tre shard con
dati diversi. Le due righe per cui il Blocco 3 esiste resterebbero mute. Il comando si ferma prima
di connettersi e dice **quale** delle due cose manca, con parole diverse per i due casi: un
messaggio unico costringerebbe chi lo legge a capire da sé quale metà lo riguarda.

**Conseguenze:** `--carico` non esiste in questa scena, ed è una difformità che va spiegata a voce
una volta sola. `WorkloadRunner.esegui` rifiuta per disegno i due limiti insieme, quindi non c'è una
rete di sicurezza temporale: con un `--scritture` molto grande e un cluster lento la scena dura
finché dura. È accettabile perché il predefinito è misurato e chi lo alza sa che cosa sta chiedendo.

**Alternative scartate.**

- *Tenere la durata e dichiarare la differenza.* È ciò che il codice faceva, ed è ciò che ha
  prodotto la riga «non è lo stesso carico» in mezzo alla scena che dimostra il contrario.
- *Durata uguale e poi troncare al minore dei due conteggi.* Butterebbe via documenti già scritti
  per far tornare un numero: una scena che aggiusta i propri dati dopo averli prodotti.
- *Un conteggio con una durata massima di sicurezza.* Richiederebbe di riaprire il rifiuto dei due
  limiti insieme in `WorkloadRunner`, che è una decisione presa altrove e per altre ragioni, in
  cambio di una protezione da uno scenario che nel lab non si verifica.
- *Girare il blocco anche sugli altri stack, mostrando le righe vuote.* «Qui non c'è niente da
  vedere» è un'informazione, ma dieci secondi di carico per arrivarci sono dieci secondi spesi male
  in un talk di sessanta minuti.

**Fonti:** [M-052](../app/docs/Sources.md#m-052), [ADR-0098](#adr-0098), [ADR-0101](#adr-0101)

---

<a id="adr-0108"></a>
## ADR-0108 — A client freddo si guarda prima di rispondere: un `ping` `NEAREST`, e solo la prima volta

**Data:** 2026-09-04 · **Stato:** Accettata · **Ricorrenza di:** [ADR-0099](#adr-0099)

**Contesto:** la prima esecuzione vera di `demo sharding` contro uno stack 03 sano ha stampato per
la collezione distribuita `sbilancio —` e `chunk —`, e per la fotografia iniziale
`distribuita=False, primario=None, conti=()` — su una `lab.ordini` che le righe subito sotto
mostravano ripartita su due shard ([M-053](../app/docs/Sources.md#m-053)).

`PymongoInspector._e_sharded()` decideva guardando la descrizione della topologia **come il client
la conosce**. Un client appena costruito non conosce niente: PyMongo scopre i server alla **prima
operazione**, non alla costruzione. Fino a lì ogni seme è `SCONOSCIUTO`, che nel dominio significa
esattamente «assenza di un'osservazione» e non «osservato assente» — e concludere «non c'è nessun
router» da lì è leggere il proprio non aver guardato.

Nessuna prova d'integrazione lo vedeva, e la ragione è istruttiva: la fixture di sessione chiama
`spazza(client)` prima di consegnarlo, quindi la scoperta era già avvenuta **per effetto
collaterale** della pulizia. Ogni prova partiva da un client caldo; solo la sala partiva da uno
freddo.

È la seconda volta. [M-042](../app/docs/Sources.md#m-042) è lo stesso inciampo un task prima, in
`demo failover`, e la sua nota diceva già che gli altri comandi non ci cascavano «per caso»:
`stats` chiede `serverStatus`, che aspetta la selezione del server. Il caso ha smesso di reggere
alla prima scena che legge la topologia **prima** di fare qualunque altra cosa.

**Decisione:** `_scopri()` costringe il client a guardare — un `ping` su `admin` — e lo fa **solo se
nessun ruolo è ancora noto**. Appena uno lo è, il monitoraggio in background tiene aggiornata la
descrizione da sé, e la riga non costa più niente per il resto della corsa.

Il `ping` porta `read_preference=ReadPreference.NEAREST`, e non è un dettaglio: per
[A-017](../app/docs/Sources.md#a-017) un comando su `admin` va sul primario per impostazione
predefinita e **non torna finché un primario non c'è**. Su un mongos non esiste; su un replica set
in mezzo a un'elezione nemmeno. Con la preferenza predefinita questa riga avrebbe piantato `stats`
proprio durante l'Atto II, cioè avrebbe scambiato un difetto di schermata con un blocco in scena.

**Conseguenze:** `shard_distribution` costa un giro di rete in più su uno stack non sharded, dove
prima non ne costava nessuno. È il prezzo di una risposta che distingue «ho guardato e non c'è» da
«non ho guardato», e su tre stack accesi è un millisecondo. La prova che lo copre apre il **proprio**
client apposta, invece di riusare la fixture: è l'unico modo di provare una condizione che la
fixture cancella.

**Alternative scartate.**

- *Attendere il primario, come fa `attendi_il_primario` per il failover.* È la correzione di
  [ADR-0099](#adr-0099), ed è giusta lì: quella scena il primario lo vuole davvero. Qui no — e su un
  mongos aspetterebbe qualcosa che non esiste.
- *Chiamare `_scopri()` nel costruttore dell'ispettore.* Farebbe un giro di rete a ogni costruzione,
  anche quando nessuno chiede la distribuzione, e trasformerebbe un costruttore in un'operazione di
  I/O che può fallire — proprio in un oggetto che si costruisce nella radice di composizione, dove
  un'eccezione non ha ancora un rapporto in cui finire.
- *Documentare che la prima fotografia può mentire.* Una nota che chiede a chi presenta di ignorare
  una riga sbagliata sul proiettore.

**Fonti:** [M-053](../app/docs/Sources.md#m-053), [M-042](../app/docs/Sources.md#m-042),
[A-017](../app/docs/Sources.md#a-017), [ADR-0099](#adr-0099)

---

<a id="adr-0109"></a>
## ADR-0109 — Le opzioni di misura entrano dalla riga di comando, e chi non chiede non riceve

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** il Task 16 doveva saldare quattro debiti che quattro pagine avevano intestato
all'applicazione Python: `j: true` sullo standalone, `retryWrites=false` e `maxStalenessSeconds` sul
replica set, la saturazione di `maxPoolSize`. Il piano li descrive come lavoro di documentazione — i
suoi file sono `Sources.md`, `Decision.md` e le tre pagine di `02-architetture`.

Nessuna delle quattro misure era però producibile con `mongolab` così com'era. `connetti` accettava
`**extra`, quindi le opzioni si potevano passare da Python, ma non dalla riga di comando: ogni
misura sarebbe stata uno script buttato via alla fine della sessione, e la voce `V-` che la cita
avrebbe puntato a un comando che nessuno può rieseguire. Un repository che pretende che ogni numero
porti il proprio comando non può registrare numeri prodotti da comandi che non esistono più.

C'era anche un problema di confrontabilità. `workload` accettava solo `--duration`, e due corse a
pari durata contro due architetture diverse fanno **quantità di lavoro diverse**: è la lezione di
[ADR-0107](#adr-0107), dove il limite del Blocco 3 è diventato un conteggio proprio perché due corse
a tempo non si confrontano.

**Decisione:** quattro opzioni di misura su `workload`, una su `demo failover`, e un limite
alternativo a `--duration`.

- `--journal/--no-journal`, `--retry-writes/--no-retry-writes`, `--max-staleness N`,
  `--max-pool-size N` su `mongolab workload`.
- `--retry-writes/--no-retry-writes` anche su `mongolab demo failover`, che è la scena in cui quella
  differenza si vede.
- `--writes N` su `workload`, mutuamente esclusivo con `--duration`: quando si confrontano
  architetture, il limite è il lavoro fatto, non il tempo passato.

Le quattro opzioni passano per una funzione sola, `opzioni_di_misura`, che sta in
`infrastructure/bersagli.py` e restituisce una `dict[str, Any]` con i nomi dell'**URI** —
`journal`, `retryWrites`, `readPreference`, `maxStalenessSeconds`, `maxPoolSize`. La CLI non importa
niente di pymongo: le sue opzioni sono `bool | None`, `int | None`, e la guardia del repository che
tiene `pymongo` sotto `infrastructure/` resta intatta.

Quattro regole dentro quella funzione, e sono la decisione vera:

1. **Chi non chiede non riceve.** Un argomento lasciato a `None` non compare nella mappa. Il client
   di partenza è byte per byte quello di sempre, quindi ogni misura senza opzioni resta confrontabile
   con tutte le misure precedenti.
2. **La staleness non viaggia mai da sola.** `maxStalenessSeconds` senza una preferenza di lettura è
   un `ConfigurationError` in costruzione; la funzione aggiunge sempre `readPreference`.
3. **`secondary` e non `secondaryPreferred`.** Un ripiego sul primario nasconderebbe una selezione
   fallita facendola sembrare riuscita — e il punto di quella misura è vedere quando la selezione
   fallisce ([V-077](Sources.md#v-077)).
4. **I nomi sono quelli dell'URI, non quelli di Python.** Chi legge la riga annunciata sullo schermo
   deve poterla incollare in una stringa di connessione.

Ed è annunciata: `riga_delle_opzioni` compone `opzioni journal=True · retryWrites=False` a partire
**dalla stessa mappa** che va a `connetti`, non dai parametri da cui è stata costruita. Se un giorno
la mappa e l'annuncio divergessero, sarebbe perché la mappa è cambiata — e allora l'annuncio deve
cambiare con lei. Mappa vuota, riga assente: un annuncio che dice «nessuna opzione» sarebbe rumore
su una registrazione.

**Conseguenze:** le sette misure del Task 16 ([V-075](Sources.md#v-075) … [V-081](Sources.md#v-081))
citano tutte un comando `make app-workload` che chiunque può rieseguire. Il gancio che il Task 5
aveva lasciato in `WorkloadRunner` — «`scrittori` è il parametro che il Task 16 farà salire sopra
`maxPoolSize`» — si chiude, e con l'altra manopola la prova è diventata anche più pulita: si tiene
fermo il numero di scrittori e si stringe il pool ([V-080](Sources.md#v-080)).

La superficie della CLI cresce di sei opzioni, che è il costo. È contenuto dal fatto che siano tutte
opzioni di **misura**: nessuna cambia che cosa la scena racconta, tutte cambiano solo come il client
è configurato mentre la racconta.

`**extra` resta su `connetti` e non diventa un parametro tipato: gli altri usi non sono spariti —
`connect=False` nelle prove unitarie, `event_listeners` per il ponte SDAM.

**Alternative scartate.**

- *Script di prova, buttati a fine sessione.* È ciò che il repository chiama esplicitamente aria: la
  voce `V-` citerebbe un comando irripetibile, e la misura non sarebbe verificabile da nessuno.
- *Una variabile d'ambiente per ogni opzione.* Non comparirebbe nella riga di comando che finisce
  nella voce `V-`, quindi due corse con configurazioni diverse sarebbero indistinguibili nella
  documentazione — che è esattamente il difetto da evitare.
- *Un'unica opzione `--client-opt chiave=valore` ripetibile.* Più corta da scrivere e senza tipi:
  `--client-opt maxstaleness=90` passerebbe la validazione della CLI e fallirebbe in pymongo, dove
  l'errore non sa più da quale opzione venga.
- *Lasciare `--duration` come unico limite.* Rende impossibile il Passo 3 del piano: tre architetture
  a pari tempo fanno lavori diversi, ed è la stessa ragione per cui ADR-0107 ha scelto un conteggio.

**Fonti:** [V-075](Sources.md#v-075), [V-076](Sources.md#v-076), [V-077](Sources.md#v-077),
[V-079](Sources.md#v-079), [V-080](Sources.md#v-080),
[M-054](../app/docs/Sources.md#m-054), [M-055](../app/docs/Sources.md#m-055),
[ADR-0107](#adr-0107), [ADR-0088](#adr-0088)

---

<a id="adr-0110"></a>
## ADR-0110 — `analyzeShardKey` resta fuori da `mongolab`: risponde una volta, e l'applicazione emette flussi

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** il Passo 4 del Task 16 chiede di saldare `analyzeShardKey`, scoperto dichiarato di
[`sharded-cluster.md`](02-architetture/sharded-cluster.md). La domanda che si apre subito è dove
metterlo: un sottocomando di `mongolab`, come `demo sharding`, o un comando amministrativo citato
nella pagina?

`mongolab` è costruita intorno a una cosa sola: un flusso di eventi di dominio che tre rese
disegnano in modi diversi ([ADR-0091](#adr-0091)). Ogni comando esistente produce eventi mentre
qualcosa accade nel tempo — scritture che riescono e falliscono, un primario che cambia, un dump che
avanza. `analyzeShardKey` non ha niente di tutto questo: si dà una volta, legge una collezione ferma,
e risponde con un documento.

**Decisione:** `analyzeShardKey` non entra in `mongolab`. La misura si esegue come comando
amministrativo attraverso il `mongos`, e la pagina la cita così — con il comando per intero, come
ogni altra misura del repository.

**Conseguenze:** [V-081](Sources.md#v-081) cita un `docker compose run --entrypoint python` invece di
un sottocomando di `mongolab`. È una riga più lunga, e l'onestà di questa decisione sta nel dire che
è il costo: chi vuole rifare la misura scrive più caratteri.

In cambio, nessuna porta nuova, nessun evento nuovo, e la guardia che tiene gli eventi di dominio a
nove ([ADR-0103](#adr-0103)) non deve discutere se un verdetto sia un evento. La conseguenza
didattica è la migliore delle due: durante il talk il confine si può nominare a voce — «questo non è
un comando dell'applicazione, è un comando di amministrazione, e la differenza è che non c'è niente
da guardare mentre accade».

**Alternative scartate.**

- *`mongolab shard-key --analyze`.* Costringerebbe a inventare un evento per un verdetto che non ha
  durata, o a bucare la resa facendo stampare qualcosa che non passa dal flusso — cioè a rompere
  proprio la proprietà che rende l'applicazione un esempio.
- *Una porta `ShardKeyAnalyzer` accanto a `QueryPlanner`.* Sette porte hanno una ragione ciascuna
  scritta nel design; un'ottava per un comando che si dà una volta sola sarebbe una porta per un
  caso, non per un ruolo.
- *Metterlo dentro `demo sharding`.* Quella scena confronta due corse di carico; un verdetto sulla
  chiave lì dentro sarebbe una schermata che risponde a una domanda che nessuno ha fatto in quel
  momento.

**Fonti:** [V-081](Sources.md#v-081), [S-067](Sources.md#s-067), [ADR-0091](#adr-0091),
[ADR-0103](#adr-0103), [ADR-0064](#adr-0064)

---

<a id="adr-0111"></a>
## ADR-0111 — Il confronto fra architetture si pubblica in coppia, e la riserva del ferro viaggia con ogni numero

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** il Passo 3 del Task 16 ha prodotto il confronto che tutte e tre le pagine di
`02-architetture` si erano intestate. Ha prodotto anche una scoperta che rende la pubblicazione una
decisione invece di una trascrizione: **nel lab così com'è, il numero dello standalone non misura lo
standalone**. Il container dell'applicazione ha `cpus: 1.0`, e a quel ritmo l'interprete Python
satura la propria CPU prima che il server saturi la sua. Con quattro CPU al client lo standalone
guadagna il 40 %; il replica set il 3 % e lo sharded il 9 %, cioè rumore
([V-079](Sources.md#v-079)).

Ci sono quindi due numeri veri e diversi per la stessa riga, e la domanda è quale va sulla slide.

Il numero del lab predefinito è quello che chiunque riproduce con un `make`, ed è quindi l'unico
onesto verso chi rifà la prova a casa. Il numero a quattro CPU è quello che confronta le
architetture invece dei limiti di Compose, ed è l'unico onesto verso la domanda che il confronto
pone.

**Decisione:** si pubblicano **entrambi**, sempre insieme, e il rapporto citabile è quello del
controllo. Ogni numero porta la propria riserva **sulla stessa riga**, e non in una nota in fondo:
la disciplina del repository su questo è esplicita, e un lab su un portatile non è un datacenter.

La riserva che viaggia con ogni numero del confronto è duplice e va scritta tutta e due le volte:

1. **Le tre architetture non hanno lo stesso ferro**, per costruzione — 1,0 CPU al `mongod` singolo,
   0,75 a ogni membro del replica set, 0,5 a ogni shard dietro un router da 0,5. Il budget è stato
   distribuito perché il portatile potesse tenere accesi tutti e tre gli stack insieme, che è la
   ragione per cui il lab esiste. Una parte della distanza è la scelta di Compose, non
   l'architettura, e non è separabile senza cambiare il lab.
2. **La semantica dell'ack non è la stessa.** Lo standalone conferma con `w: 1` senza giornale, il
   replica set con `w: "majority"` e giornale sulla maggioranza, lo shard con `w: "majority"` su un
   membro solo — perché in questo cluster **ogni shard ha un membro solo**. Chi confronta i tre
   numeri senza dirlo sta misurando la durabilità e chiamandola velocità.
3. **Un dettaglio di stato sposta il numero di un ordine di grandezza.** Con un membro del replica
   set in pausa la maggioranza si raggiunge ancora, e la resa crolla di un fattore ventisette
   ([V-078](Sources.md#v-078)). Il rapporto pubblicato vale per tre stack **sani e a riposo**: non
   è una proprietà dell'architettura, è una fotografia con le sue condizioni scritte accanto. La
   riserva viaggia con il numero anche per questo — la stessa architettura, in un altro stato, dà
   un altro numero, e chi cita 6,2× senza dire «a riposo» sta citando una coincidenza.

**Conseguenze:** le tre pagine di `02-architetture` ricevono lo stesso rimando a
[V-079](Sources.md#v-079) invece di tre tabelle divergenti, e la tabella sta in un posto solo. Chi
prepara la slide ha due numeri da far stare dove ce ne stava uno; è il prezzo, ed è preferibile a una
slide che dice 4,7× quando il numero vero è 6,2×.

Lo stack 01 guadagna un debito che questa decisione non salda: il limite di CPU del suo `mongod` non
è parametrizzato — è scritto `cpus: 1.0` a mano, mentre gli stack 02 e 03 hanno `CPU_MEMBRO`,
`CPU_SHARD`, `CPU_MONGOS`. Finché resta così non si può sapere a quale ritmo lo standalone
saturerebbe davvero, e [V-079](Sources.md#v-079) lo dichiara fra le riserve.

**Alternative scartate.**

- *Pubblicare solo il numero del lab predefinito.* È riproducibile e sbagliato: darebbe 4,7× fra
  standalone e replica set quando il rapporto vero è 6,2×, e la differenza non è un dettaglio.
- *Pubblicare solo il numero del controllo.* Nessuno lo riprodurrebbe con un `make`, e il repository
  smetterebbe di poter dire «ogni numero porta il suo comando».
- *Pareggiare il ferro fra i tre stack e rimisurare.* Cambierebbe i tre stack che il talk descrive,
  per far tornare una tabella. Le architetture sono il soggetto, il confronto è un capitolo.
- *Mettere la riserva in una nota in fondo alla pagina.* Una nota in fondo non arriva sulla slide,
  e il numero sì.

**Fonti:** [V-078](Sources.md#v-078), [V-079](Sources.md#v-079),
[ADR-0031](#adr-0031), [ADR-0032](#adr-0032),
[ADR-0046](#adr-0046), [ADR-0068](#adr-0068), [ADR-0072](#adr-0072)


---

<a id="adr-0112"></a>

## ADR-0112 — La pagina sul monitoraggio mostra sei numeri che smentiscono la lettura ingenua, e dichiara inutilizzabile la metrica di ritardo invece di esibirla

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** `docs/README.md` intesta a `feature/04` una pagina
`03-amministrazione/statistiche-monitoraggio.md` descritta così: «`serverStatus`, `dbStats`,
metriche di replica, cosa guardare sotto carico». La forma ovvia di quella pagina è un elenco
commentato dei campi di `serverStatus`. È anche la forma inutile: quell'elenco esiste già, è il
manuale, ed è più completo di qualunque cosa questo repository possa scrivere
([ADR-0024](#adr-0024) separa da tempo il materiale divulgativo dalla documentazione normativa).

La campagna di misura fatta per questa pagina ha però prodotto **sei risultati che il manuale non
dice e che contraddicono ciascuno una lettura corrente**:

1. `serverStatus` non risponde la stessa cosa su tre nodi — 45, 52 e 36 sezioni — e al router ne
   mancano venti, fra cui `wiredTiger`, `globalLock`, `locks` e `repl`, senza che nessun errore lo
   segnali ([V-082](Sources.md#v-082)).
2. Sotto un carico che satura il client, il server non mette in coda **niente**, e la latenza che
   dichiara — 67 µs — è quaranta volte più piccola di quella che il client misura
   ([V-083](Sources.md#v-083)). Lo stesso campo sul primario di un replica set vale 18 390 µs: non è
   la stessa metrica più grande, è una metrica che **cambia significato** con l'architettura.
3. Il pool dei ticket di scrittura non è la costante 128 che circola: nella 7.0 lo dimensiona un
   controllore e in questi container sta fra 7 e 12, muovendosi da solo ([V-083](Sources.md#v-083)).
4. Il ritardo di replica letto come lo legge `rs.printSecondaryReplicationInfo()` è **quantizzato al
   secondo**, vale **10 000 ms su un insieme sano a riposo** e diventa **negativo** se lo si chiede
   al secondario ([V-084](Sources.md#v-084)) — mentre il ritardo vero di questo lab, misurato
   diversamente, è ≈ 1,6 ms ([V-027](Sources.md#v-027)).
5. Un router conta le operazioni del client alla singola unità, ma somma i filesystem degli shard e
   dichiara un disco grande il doppio di quello che esiste; e non dice che uno dei due shard, per
   tutta la corsa, non ha visto **nessuna** operazione ([V-086](Sources.md#v-086)).

6. `dataSize` non è spazio su disco, e il rapporto con `storageSize` è una proprietà **dei
   dati**, non del motore: 3,06× sulla collezione di dati veri, **0,97×** su quella di carico, la
   cui zavorra pseudocasuale non si comprime ([V-087](Sources.md#v-087)).

A questi si aggiunge il raddoppio di `apply.ops` dovuto alle scritture ripetibili
([V-085](Sources.md#v-085)): una metrica di replica che vale il doppio del carico vero per una
ragione che sta nel driver, non nel database.

**Decisione:** la pagina si organizza **attorno alla domanda «cosa guardare, e cosa non credere»**,
non attorno alla struttura di `serverStatus`. Ogni sezione parte da una metrica che si guarderebbe
per istinto, mostra il numero misurato, e dice perché quel numero non risponde alla domanda che si
credeva di aver posto. Il campo di riferimento resta il manuale, e la pagina ci rimanda.

Tre conseguenze operative della decisione, esplicite perché sono ciò che la distingue da un elenco:

- **Il ritardo di replica non si mostra dal vivo, e la pagina dice perché.** Non è una rinuncia
  didattica: è il risultato. La metrica che tutti citano, su questo lab, produce il valore più
  allarmante nello stato migliore. Al suo posto la pagina indica `opcountersRepl.insert` sul
  secondario, che nella misura coincide **esattamente** con le scritture confermate al client
  (9 139 = 9 139), e `metrics.repl.buffer`, che è la coda vera.
- **Ogni metrica viene dichiarata insieme al nodo su cui va letta.** Le tre architetture del lab
  hanno tre insiemi di sezioni diversi, e una ricetta senza il nodo è una ricetta rotta.
- **I numeri della pagina sono quelli del Task 16 e di questa campagna, con le loro riserve
  accanto**, secondo [ADR-0111](#adr-0111). Nessun numero di questa pagina è preso dal manuale.

**Conseguenze:** la pagina è più corta di un elenco di campi e più difficile da scrivere, perché
ogni sezione deve avere una misura sotto. Chi cerca «cosa vuol dire `wiredTiger.cache.bytes read
into cache`» non lo trova qui, e la pagina glielo dice in «Cosa questa pagina non dice» invece di
lasciarglielo scoprire. Nasce inoltre un debito che questa decisione non salda: la conclusione che i
18 390 µs del primario contengano l'attesa della maggioranza è coerente ma **non isolata** — la
prova che la chiuderebbe è la stessa corsa con `w: 1` sul replica set, ed è dichiarata fra le
riserve di [V-083](Sources.md#v-083).

*Debito saldato lo stesso giorno da [ADR-0114](#adr-0114) e [V-088](Sources.md#v-088).* La corsa con
`w: 1` è stata eseguita e l'interpretazione regge — 18 913 µs contro 644 — ma con una correzione che
tocca proprio questa pagina: fra il predefinito e `w: 1` non cambia solo il numero di conferme,
cambia anche il giornale, e il giornale costa più della maggioranza. La sesta sezione della pagina è
stata riscritta di conseguenza: dire «l'attesa della maggioranza» e fermarsi lì sarebbe stata la
spiegazione giusta a metà.

**Alternative scartate.**

- *L'elenco commentato dei campi di `serverStatus`.* Duplica il manuale, invecchia a ogni versione
  minore, e nessuna delle cinque scoperte ci starebbe dentro: sono tutte relazioni fra un numero e
  un'aspettativa, non definizioni di campi.
- *Mostrare comunque il ritardo di replica, con una nota.* La nota non arriva sulla slide e il
  numero sì ([ADR-0111](#adr-0111)). Mostrare 10 000 ms di ritardo su un insieme sano davanti a un
  pubblico significa insegnare un allarme falso.
- *Rimandare la pagina finché la prova con `w: 1` non chiude il punto sui 18 ms.* Le altre quattro
  scoperte sono complete e la pagina è dovuta a questo branch. Un debito dichiarato in una riserva
  costa meno di una pagina che non esiste.
- *Mettere le misure in `app/docs/` perché le ha prodotte l'applicazione.* Sono misure **sul
  server**, prese con `mongosh`, di cui l'applicazione è solo il generatore di carico. Chi le cerca
  le cerca in `03-amministrazione`.

**Fonti:** [V-027](Sources.md#v-027), [V-079](Sources.md#v-079), [V-082](Sources.md#v-082),
[V-083](Sources.md#v-083), [V-084](Sources.md#v-084), [V-085](Sources.md#v-085),
[V-086](Sources.md#v-086), [V-087](Sources.md#v-087),
[ADR-0024](#adr-0024), [ADR-0111](#adr-0111)

---

<a id="adr-0113"></a>

## ADR-0113 — Le pagine divulgative sull'applicazione rimandano ad `app/docs/` invece di riassumerlo, e si distinguono per il lettore, non per l'argomento

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** il Task 17 crea `docs/06-sviluppo/architettura-app.md` e
`docs/06-sviluppo/tdd-e-doppi.md`. Gli stessi argomenti — stratificazione, porte, eventi, radice di
composizione, doppi di prova, separazione fra suite — hanno già diciassette capitoli in
[`app/docs/`](../app/docs/README.md), scritti dai Task 1-16 mentre il codice nasceva. Senza una
regola, due esiti sono garantiti: o le pagine nuove riassumono quelle vecchie, e allora divergono
alla prima modifica del codice, oppure le ripetono, e allora il repository ha due verità sullo
stesso soggetto. [ADR-0024](#adr-0024) distingue già il materiale divulgativo da quello normativo,
ma non dice che cosa fare quando i due parlano dello stesso codice.

**Decisione:** la distinzione non è per argomento ma **per lettore**, e la si dichiara in testa a
ciascuna delle due pagine.

- `app/docs/` scrive per **chi apre i sorgenti**: nomi di classi, firme, file, prove. È la
  documentazione normativa dell'applicazione, e quando il codice cambia cambia lei.
- `docs/06-sviluppo/` scrive per **chi non li aprirà mai** — il pubblico del talk, chi valuta se
  adottare l'impianto, chi legge il repository da fuori. Racconta **che cosa si guadagna** e **come
  lo si è misurato**, e per ogni dettaglio realizzativo rimanda al capitolo di `app/docs/` che lo
  possiede.

La regola operativa che ne discende: **nelle due pagine nuove non compare nessun blocco di codice
dell'applicazione**. Un nome di classe sì, quando serve a puntare; il corpo no. Un numero
misurato sì, sempre con la sua fonte. Se scrivendo viene voglia di copiare dieci righe da
`app/docs/`, quelle dieci righe stanno già dove devono e va messo un collegamento.

**Conseguenze:** le due pagine restano corte e invecchiano piano — un rinomino di classe non le
tocca. In cambio non si possono leggere da sole per capire *come* è fatta una cosa: sono una porta,
e chi vuole i dettagli fa un salto in più. È il prezzo giusto, perché il lettore per cui sono
scritte quel salto non lo farebbe comunque. `app/docs/README.md` smette di promettere le due pagine
al futuro e le collega; il legame diventa reciproco, e un collegamento rotto lo trova
`make docs-check`.

**Alternative scartate.**

- *Una pagina sola in `docs/` che riassume tutto `app/docs/`.* È la forma che diverge più in fretta,
  perché riassumere è ricopiare con meno controlli.
- *Nessuna pagina in `docs/`, solo il rimando a `app/docs/`.* Il piano le pretende, e con ragione:
  chi legge `docs/` non sa che `app/docs/` esiste, e soprattutto `app/docs/` risponde a «com'è
  fatto», non a «perché conviene». La seconda domanda è quella del talk.
- *Spostare i capitoli di `app/docs/` sotto `docs/06-sviluppo/`.* Allontanerebbe la documentazione
  dal codice che descrive, che è esattamente ciò che la fa marcire.

**Fonti:** nessuna (decisione organizzativa), [ADR-0024](#adr-0024), [ADR-0078](#adr-0078)

---

<a id="adr-0114"></a>

## ADR-0114 — La quinta opzione di misura: `--write-concern`, e un debito che era vero solo sulla riga di comando

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** il Task 17 si è chiuso registrando un debito fra i punti aperti del registro
dell'applicazione: «il carico non sa chiedere un write concern diverso dal predefinito, quindi la
corsa con `w: 1` che isolerebbe i 18 390 µs del primario non è eseguibile». La riserva di
[V-083](Sources.md#v-083) e le conseguenze di [ADR-0112](#adr-0112) dicevano la stessa cosa in
forma più prudente: l'interpretazione è coerente ma **non isolata**, e la prova che la chiuderebbe
è la stessa corsa con `w: 1`.

Il Product Owner ha obiettato al debito, non alla riserva: `w` è un parametro della stringa di
connessione, nella sezione dopo il `?`. La verifica sul manuale gli dà ragione
([S-076](Sources.md#s-076)): le opzioni di write concern nell'URI sono tre — `w`, `journal`,
`wtimeoutMS` — e `w` accetta un numero, `majority`, o un tag set.

**Il debito era vero per metà, ed è la metà che conta meno.** `opzioni_di_misura` parla i nomi
dell'URI dal Task 16 — è scritto nella sua docstring — e `connetti(**extra)` inoltra a pymongo
qualunque opzione le si dia, dal Task 5. Il meccanismo per portare `w: 1` fino al client c'era da
tredici task; mancava **la parola per chiederla** dalla riga di comando. Scrivere «non è eseguibile»
al posto di «non è chiedibile» ha trasformato una parola mancante in un impedimento, e ha tenuto
aperta per un task una riserva che costava tre righe di codice e due minuti di misura.

La verifica ha anche cambiato il disegno della misura. [S-077](Sources.md#s-077) dice che con `j`
non specificato `w: "majority"` equivale a `j: true` — via `writeConcernMajorityJournalDefault`, che
è `true` di suo — mentre `w: <numero>` equivale a `j: false`. Cioè scendere da `majority` a `1`
spegne **due** cose: l'attesa dei secondari e la sincronizzazione del giornale. Un confronto a due
corse avrebbe attribuito alla maggioranza un costo che è in gran parte del giornale.

**Decisione:** `mongolab workload` riceve una quinta opzione di misura, `--write-concern`, che vale
un numero o `majority` e va in `opzioni_di_misura` come `w`, prima di `journal` — l'ordine dell'URI,
non quello alfabetico, perché le due opzioni si condizionano. Il valore arriva come testo e diventa
intero se è tutto cifre, così la mappa annunciata a schermo è identica a quella che il client userà.

Con la parola disponibile, la riserva di [V-083](Sources.md#v-083) si chiude con **tre** corse e non
due ([V-088](Sources.md#v-088)): il predefinito, `w: 1` con il giornale acceso, e `w: 1` nudo.

Tre conseguenze, ed è per queste che la decisione esiste:

- **La riserva si chiude, e l'interpretazione era giusta.** `opLatencies.writes` sul primario passa
  da 18 913 µs a **644 µs** con `w: 1`, un fattore 29. Quello che il primario contava e lo
  standalone no era davvero l'attesa della conferma.
- **Ma la maggioranza è la metà piccola del conto.** A giornale costante la maggioranza costa
  1,38× di resa; a conferme costanti il giornale costa 2,24×. La pagina sul monitoraggio non può
  più dire «l'attesa della maggioranza» e fermarsi lì: **la cosa cara che il predefinito fa senza
  dirlo è la sincronizzazione su disco.**
- **Restano 644 µs contro i 67 dello standalone**, cioè quasi dieci volte, senza nessuno da
  aspettare. È il costo di essere un primario, e prima di questa misura era confuso dentro il
  fattore 274.

**Alternative scartate.**

- *Lasciare il debito aperto e chiuderlo dopo la PR.* Sarebbe stato registrato come limite di
  progetto un limite di vocabolario, e la pagina sul monitoraggio avrebbe portato al talk una
  spiegazione a metà — quella che attribuisce alla maggioranza il costo del giornale.
- *Un'opzione `--w` con il nome dell'URI.* Coerente con la regola «i nomi sono quelli dell'URI», che
  però vale per la **mappa**, non per la riga di comando: `--w 1` accanto a `--writers 8` e
  `--writes 100` è un prefisso ambiguo che Typer risolve senza chiedere. La mappa continua a dire
  `w`; la riga di comando dice per esteso.
- *Un intero invece di una stringa.* Escluderebbe `majority`, cioè proprio il valore che serve per
  chiedere esplicitamente il predefinito e distinguere una corsa dichiarata da una implicita.
- *Due corse invece di tre.* Avrebbe prodotto il numero giusto con la spiegazione sbagliata, e non
  ci sarebbe stato modo di accorgersene guardando i risultati.

**Fonti:** [S-076](Sources.md#s-076), [S-077](Sources.md#s-077), [V-083](Sources.md#v-083),
[V-088](Sources.md#v-088)

<a id="adr-0115"></a>

## ADR-0115 — Chi registra fa da seconda finestra: `--regia PREFISSO`

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** la scena centrale del Blocco 2 — il primario che cade sotto carico — gira
l'applicazione **dentro** la rete Compose, che è l'unico posto da cui si veda la cronaca
dell'elezione: dall'host il client è `directConnection` su una porta pubblicata, non ha topologia da
osservare e la scena perde esattamente ciò che deve mostrare. Ma dentro la rete l'applicazione non
ha il socket del demone, quindi non può uccidere il container: annuncia il comando e si ferma su un
`input()` finché qualcuno non l'ha eseguito altrove. Dal palco quel qualcuno è una persona con un
secondo terminale aperto; la prova di integrazione ha già un ponte che fa la stessa cosa.
`tools/registra-terminale.py` invece non scriveva **mai** sul lato padrone dello pseudo-terminale:
una registrazione di quella scena si sarebbe piantata per sempre sul `input()`.

Il Task 18 chiede che le registrazioni si producano «con lo stesso codice della scena dal vivo»
([ADR-0098](#adr-0098)): la modalità da palco cambia una funzione di attesa, non il flusso. Rinunciare
alla scena, o girarla dall'host perdendo la cronaca, sarebbero state due riserve che non
sostituiscono la scena che devono sostituire.

**Decisione:** lo strumento di registrazione impara a fare da seconda finestra. Con `--regia
PREFISSO`, ogni **riga intera** che il comando registrato stampa e che comincia con quel prefisso —
a meno degli spazi ai due lati — viene eseguita da chi registra, e subito dopo un `\n` va sul lato padrone dello pseudo-terminale:
prima il comando, poi la conferma. L'ordine è l'unico possibile — invertirlo produrrebbe una scena
che riparte prima che il guasto sia avvenuto, cioè un failover raccontato senza failover.

Quattro vincoli che fanno parte della decisione:

- **Il prefisso è un argomento obbligatorio dell'opzione, non un predefinito.** Un `--regia` senza
  valore eseguirebbe ciò che un comando registrato decide di stampare, e la riga di comando che ha
  prodotto la registrazione non direbbe che cosa. Così invece la ricetta dichiara che cosa lo
  strumento è autorizzato a eseguire, e chi rilegge lo legge lì.
- **L'uscita del comando eseguito non entra nel `.cast`.** Si cattura e si riassume su `stderr`
  (`regia: … · uscita 0`): nel tracciato va ciò che il pubblico vedrebbe nella finestra di sinistra,
  e chi registra deve comunque sapere se il comando è riuscito. *Questa decisione dava per scontato
  che chi registra `stderr` lo legga: [ADR-0117](#adr-0117) toglie quel presupposto.*
- **La regia guarda le righe, non i blocchi.** Lo pseudo-terminale consegna quando gli pare, e un
  comando annunciato spezzato a metà fra due letture non comincerebbe con il prefisso. Il residuo
  non terminato resta in sospeso fino alla lettura successiva.
- **Il confronto ignora gli spazi ai due lati della riga, ed è una scelta e non una svista.** Chi
  annuncia un comando lo rientra per staccarlo dal testo che lo introduce: `mongolab` stampa
  «▸ da un'altra finestra…» e poi il comando con due spazi davanti. Un confronto ancorato alla
  colonna zero non troverebbe mai la riga vera, e la scena resterebbe appesa all'`input()` per
  sempre — non fallirebbe, si pianterebbe. A sinistra del prefisso possono esserci **spazi, non
  parole**: una riga che il prefisso ce l'ha *dentro* — un log, un messaggio d'errore che riporta
  ciò che ha provato a fare — non viene eseguita.

Su `--riproduci` l'opzione è un errore dichiarato e non un'opzione ignorata: una riproduzione non ha
una seconda finestra, e un'opzione che non fa niente in silenzio è peggio di un rifiuto.

**Conseguenze:** la scena 12 esiste, dura 53 secondi ed è una copia della scena dal vivo invece di
una ricostruzione ([V-089](Sources.md#v-089)). In cambio lo strumento di registrazione **esegue
comandi**, che prima non faceva, e la superficie di ciò che può eseguire è tutta nel prefisso
scritto sulla riga.

Il conto è arrivato subito. `make` fa l'eco della ricetta prima di eseguirla, e l'eco comincia con
`docker compose ` esattamente come il comando annunciato: la prima corsa ha rilanciato la scena
dentro se stessa. Si registra con `make -s`, e la trappola è scritta nella ricetta dell'indice
perché è invisibile finché non succede. È il costo di riconoscere un comando dal **prefisso** invece
che da un canale separato, e si paga una volta.

**Alternative scartate.**

- *Registrare la scena dall'host.* Nessuna riga di cronaca dell'elezione: il client è
  `directConnection`, non fa scoperta e non ha transizioni da annunciare. Si sarebbe registrata una
  scena diversa con lo stesso nome.
- *Un `--sblocca` che manda l'Invio dopo N secondi.* Non esegue il guasto: qualcuno dovrebbe
  comunque darlo da fuori, con il rischio che l'Invio arrivi prima. Una scena che riparte prima del
  guasto è indistinguibile, nel `.cast`, da un failover istantaneo.
- *Uno script esterno che pilota tutto e la registrazione come sottoprodotto.* È la soluzione usata
  per la scena 11, dove va bene perché `watch` non annuncia niente e i tempi sono liberi. Per la 12
  vorrebbe dire indovinare quando l'applicazione ha annunciato: la sincronizzazione esiste già, ed è
  la riga stampata.
- *Un canale separato — un file, un FIFO, una variabile d'ambiente — invece del prefisso sul testo.*
  Più solido e meno fedele: cambierebbe ciò che l'applicazione fa quando è registrata, che è
  precisamente la proprietà che [ADR-0098](#adr-0098) protegge.

**Fonti:** [V-089](Sources.md#v-089), [ADR-0050](#adr-0050), [ADR-0055](#adr-0055),
[ADR-0098](#adr-0098)

<a id="adr-0116"></a>

## ADR-0116 — Le registrazioni dell'applicazione pesano quanto il carico che mostrano, e restano intere

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** le nove registrazioni degli stack stanno in trentun kilobyte. Le due
dell'applicazione sotto carico ne pesano **sei megabyte**, cioè il 99,9 % della cartella
([V-089](Sources.md#v-089)). Non è un difetto: `PlainSink` scrive una riga per evento e non taglia
niente — è ciò che lo rende adatto a una riserva, perché ciò che il pubblico vede dal vivo è
esattamente quel flusso — e una scena che conferma trentaduemila scritture produce
sessantaquattromila righe. Le vie d'uscita erano tutte disponibili: accorciare il copione, ridurre
gli scrittori, campionare gli eventi, tenere i file fuori da git.

**Decisione:** le due scene restano intere, con il copione predefinito, dentro il repository. Il
peso si dichiara nell'indice con la tabella che lo spiega, e non si compra riducendo la scena.

Una riserva serve quando la demo dal vivo non parte. Se la registrazione di riserva dura la metà
della scena che sostituisce, o mostra un carico che non è quello del talk, il momento in cui se ne
scopre la differenza è davanti a cento persone — che è precisamente il momento in cui la riserva
doveva servire. Il criterio è lo stesso di [ADR-0055](#adr-0055) e per la stessa ragione: una
registrazione vale se, riprodotta, mostra quello che deve mostrare.

Nel pacchetto di git i sei megabyte diventano ~640 K, perché sono righe quasi identiche: il costo
reale sta fra i due numeri, ed è più vicino al piccolo.

**Conseguenze:** `git clone` del repository trasporta ~640 K in più, una volta. Chi apre le due
scene con `--riproduci` le vede scorrere per cinquantatré e undici secondi, che è il punto. Il
confronto automatico su file di quella lunghezza ha fatto emergere il difetto della regola di
normalizzazione dei ritorni a capo, che sulle dodici scene corte non si vedeva: le registrazioni
grandi hanno pagato una parte del loro peso trovando un errore nella pagina che le descrive.

Resta scoperta la resa `rich`: nessuna delle cinque la registra, e `app/docs/11-tre-rese-e-un-solo-thread-che-disegna.md` prometteva il contrario. La promessa era sbagliata,
non la scelta — un pannello che si ridisegna dieci volte al secondo produce un `.cast` illeggibile
e pesantissimo insieme, e `plain` porta lo stesso **contenuto**. Chi vuole vedere la resa la fa
girare; in sala la vedrà chi guarda il filmato.

**Alternative scartate.**

- *Un copione più corto per le registrazioni.* Riserva più leggera e scena diversa: si scoprirebbe
  dal vivo, nell'unico momento in cui la riserva serve.
- *Meno scrittori, o `--duration` ridotta.* Cambia i numeri che la scena porta — 31 952 scritture
  confermate, 0 perse — e quei numeri sono la scena.
- *Campionare gli eventi nel sink, o troncare la registrazione.* `PlainSink` scrive ciò che il
  pubblico vede; un sink che taglia solo quando registra rompe la proprietà di
  [ADR-0098](#adr-0098) e fa della riserva una ricostruzione.
- *Tenere i `.cast` pesanti fuori da git, accanto agli `.mp4`.* Gli `.mp4` stanno fuori perché sono
  binari grandi e opachi ([ADR-0016](#adr-0016)); un `.cast` è testo versionabile e diffabile, e
  fuori dal repository non sarebbe più disponibile offline con un `clone`, che è la ragione per cui
  la cartella esiste.
- *Comprimerli in `.cast.gz`.* Nove decimi del peso in meno e la riproduzione non funziona più
  direttamente: `--riproduci` vorrebbe una decompressione preventiva, cioè un passo in più proprio
  nel momento in cui la riserva serve.

**Fonti:** [V-089](Sources.md#v-089), [ADR-0016](#adr-0016), [ADR-0050](#adr-0050),
[ADR-0055](#adr-0055), [ADR-0098](#adr-0098)

<a id="adr-0117"></a>

## ADR-0117 — Se il comando di regia fallisce, la registrazione si ferma invece di confermare

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** [ADR-0115](#adr-0115) ha insegnato allo strumento di registrazione a fare da seconda
finestra: esegue la riga annunciata e poi manda un Invio a chi la aspettava. Nella prima stesura
l'Invio partiva **sempre**, e l'esito del comando finiva solo in una riga di `stderr` che chi
registra è libero di non leggere.

La review di `codex` sulla PR #5 ha rilevato il punto, e la misura lo conferma: con un comando
annunciato che esce con **7**, la scena riparte, il `.cast` contiene una scena in cui il primario
non è mai caduto, e lo strumento esce **0**. È esattamente il guasto che l'adattatore
dell'applicazione evita alzando `ComandoFallito`, e il docstring di `RegiaCompose` aveva già scritto
perché è grave: «un `stop` fallito lascerebbe il primario in piedi, e i due numeri finali sarebbero
zero millisecondi di interruzione e zero scritture perse — cioè un failover perfetto. La sala
vedrebbe la slide sbagliata senza che nessuno abbia modo di accorgersene.» Quando si registra,
`seconda_finestra` sta **al posto** di quella regia; il ragionamento non aveva attraversato il
confine fra l'applicazione e gli strumenti.

Dal vivo il difetto sarebbe stato meno grave: una persona con il secondo terminale aperto vede il
comando fallire, e la scena non riparte perché non è lei a premere Invio. In una registrazione non
resta traccia di niente, e la riserva del talk mostrerebbe un failover che non è avvenuto.

**Decisione:** la conferma è condizionata alla riuscita, e la registrazione si ferma. Tre cose
insieme, perché nessuna delle tre da sola basta:

- **L'Invio parte solo se il comando annunciato è uscito con zero.** È l'invariante di
  `RegiaCompose`, scritta dove serve la seconda volta.
- **La scena viene abbattuta**, con un `SIGTERM` al gruppo di processi — il comando registrato ha
  fatto `setsid()` ed è capogruppo. Non c'è una terza possibilità: la scena non può ripartire,
  perché aspetta la conferma di un guasto che non è avvenuto, e non può nemmeno restare dov'è,
  perché resterebbe appesa all'`input()` finché qualcuno non se ne accorge. Fra un errore e
  un'attesa, il modo peggiore di fallire è l'attesa.
- **Lo strumento esce con 125.** 126 e 127 sono già presi, e parlano del **comando registrato**: 125
  è quello che `env` e `timeout` usano per «ha fallito lo strumento, non ciò che gli era stato
  chiesto di fare». Chi registra dentro un `make` se ne accorge senza leggere niente.

Quando il comando fallisce si stampa anche il **contenuto** della sua uscita, non solo il codice:
senza, chi registra sa che è andata male e non perché.

**Conseguenze:** il `.cast` parziale resta sul disco e non viene cancellato. È la scelta giusta:
mostra fin dove la scena è arrivata, e la sua interruzione è la prova di ciò che è successo — un
file che sparisce non spiega niente. Chi registra rilancia dopo aver capito perché il comando è
fallito.

Il prezzo è che una registrazione ora può essere **interrotta a metà da chi la registra**, cosa che
prima non poteva succedere. È esattamente ciò che si voleva: una registrazione mutila è un problema
visibile, una registrazione completa e falsa non lo è.

**Alternative scartate.**

- *Lasciare com'era e fidarsi di `stderr`.* È lo stato che il rilievo ha trovato. Una riga di
  diagnostica in mezzo all'output di `make`, accanto a un comando uscito con 0, è precisamente ciò
  che non si legge.
- *Non mandare l'Invio e lasciare la scena dov'è.* Il `.cast` non racconterebbe più una bugia, ma lo
  strumento resterebbe appeso senza dire niente. Lo stesso modo di fallire che
  [ADR-0115](#adr-0115) evita con lo `strip()`, e per la stessa ragione: piantarsi non è fallire.
- *Ritentare il comando.* Lo strumento non sa se la riga annunciata è idempotente, e non può
  saperlo: esegue ciò che l'applicazione stampa. Un secondo tentativo che riesce nasconderebbe per
  di più il fatto che il primo non era riuscito, cioè l'informazione che serve.
- *Restituire il codice di uscita del comando annunciato.* Porta più informazione e la porta
  ambigua: chi legge non distingue un 7 della regia da un 7 della scena, e un 126 della regia
  sembrerebbe un comando registrato non eseguibile.
- *Cancellare il `.cast` parziale.* È ciò che fanno i due controlli preventivi (127 e 126), ma là il
  file non è ancora stato aperto e non contiene niente. Qui contiene la scena fino al punto in cui
  si è fermata, che è l'unica cosa che spiega dove guardare.

**Fonti:** [ADR-0115](#adr-0115), [ADR-0055](#adr-0055), [ADR-0098](#adr-0098)

<a id="adr-0118"></a>

## ADR-0118 — Il tetto del dump viaggia fino alla porta, e chi lo supera abbatte il processo

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** [ADR-0101](#adr-0101) ha legato la fine del carico alla fine del `mongodump` e ha
tenuto `--tetto` come rete di sicurezza, scrivendo perché: «una scena che non termina in sala è
peggio di una scena che termina male». La pagina
[15](../app/docs/15-il-backup-a-caldo-e-la-finestra-che-si-misura.md) lo ripete con altre parole —
«`durata_s` resta la rete di sicurezza che fa **terminare la scena** anche se il dump non torna
più» — e nomina il caso da evitare: «uno schermo fermo davanti a duecento persone».

La review di `codex` sulla PR #5 ha rilevato che il codice non lo faceva. `ScenarioBackup._con_dump`
passava `tetto_s` al solo `WorkloadRunner` e poi restava, sul thread principale, dentro
`for avanzamento in self._strumento.dump(...)`. **Misurato:** con un iteratore che non torna mai e
`tetto_s = 0,05 s`, dopo **15 secondi** — trecento volte il tetto — `esegui()` non era ancora
tornata. Il carico mollava, la scena restava ferma a leggere uno `stderr` che non diceva più niente.
La documentazione prometteva più di ciò che il codice faceva.

La correzione ovvia non funziona, ed è la misura che ha deciso la forma di questa decisione. Un
thread di guardia che allo scadere chiuda l'iteratore trova un generatore **in esecuzione**, non
sospeso: il thread principale sta *dentro* il frame, fermo sulla lettura di un tubo. `close()` da lì
alza `ValueError: generator already executing`, il dump resta vivo e il ciclo resta dov'è
([M-059](../app/docs/Sources.md#m-059)). Nella stessa sonda, il thread principale è uscito solo
quando il guardiano ha **ucciso il processo** — e ne è uscito con un `ComandoFallito`, cioè per una
strada che la scena già conosce.

Chi chiama la porta tiene un iteratore. Chi la implementa tiene il processo. Solo il secondo può
onorare un tetto.

**Decisione:** `BackupTool.dump` prende `tetto_s: float | None = None`, parola chiave, e
`ScenarioBackup` gli passa lo stesso numero che dà al carico. `SubprocessBackup` lo fa rispettare
con un `threading.Timer` che abbatte il figlio; allo scadere sale `DumpTroppoLungo`, che porta
l'eseguibile e il tetto.

Tre dettagli che il rimedio richiede e che nessuno dei tre è ovvio:

- **Un'eccezione propria, non un `ComandoFallito` con codice `-9`.** Dal palco «mongodump è uscito
  con codice -9» è il rumore del rimedio; «mongodump ha superato il tetto di 300 secondi ed è stato
  fermato» è la notizia. Il numero sta anche in un attributo, perché la resa possa dirlo a modo suo.
- **Il guardiano guarda `poll()` prima di segnare.** Il cronometro può scadere nell'attimo fra la
  fine del figlio e la lettura del suo codice d'uscita — un dump riuscito mentre chi guarda è lento
  a scorrere — e segnare «scaduto» lì vorrebbe dire dichiarare fallita in sala la scena che era
  appena riuscita. Un processo già uscito non ha superato nessun tetto.
- **Un solo numero per due destinatari.** Il tetto va al carico come limite della corsa e allo
  strumento come scadenza del processo. Due campi separati sarebbero un ordine da ricordare per
  sempre — quale scade prima, e che cosa succede in mezzo — per una scelta che nessuno vuole fare.

**Conseguenze:** con lo stesso dump piantato e un tetto di 2 secondi, la scena esce dopo **2,05 s**
in una corsa e **2,07 s** nell'altra, dicendo che è stato il tetto
([M-059](../app/docs/Sources.md#m-059)). La promessa scritta in ADR-0101 e nella pagina 15 è
diventata vera.

Il limite dichiarato in `SubprocessBackup` resta e vale anche qui: quando il comando è
`docker exec ...`, ciò che muore è il **client** `docker`, e lo strumento dentro il container tira
dritto. Il tetto libera la scena, non il cluster; è il compromesso che [ADR-0012](#adr-0012)
comporta, ed è scritto dove qualcuno lo leggerà.

Il cronometro parte quando qualcuno comincia a scorrere l'iteratore e non alla chiamata di `dump`.
Nella scena i due istanti coincidono — il `for` è la riga dopo — ma la differenza esiste ed è
dichiarata: `dump` avvia il processo subito, il corpo del generatore parte al primo `next`.

`restore` **non** ha preso il parametro. La simmetria delle due firme è una proprietà voluta della
porta, e romperla è un debito: ma un tetto sul restore vorrebbe dire un `--tetto` su
`demo restore`, cioè superficie di riga di comando che nessuno ha chiesto, e la scena del restore
non ha un carico accanto da fermare. Sta nella tabella dei punti aperti del
[registro di sviluppo dell'applicazione](../app/docs/registro-sviluppo-app.md#che-cosa-manca).

**Alternative scartate.**

- *Un thread di guardia che chiude l'iteratore.* È la correzione che viene in mente per prima, ed è
  quella che la sonda ha escluso: `ValueError: generator already executing`.
- *Il tetto nel costruttore di `SubprocessBackup` invece che sulla porta.* Non cambia nessuna firma,
  e mette lo stesso numero in due posti — la radice di composizione e il copione della scena. Il
  giorno in cui divergono nessuno se ne accorge, perché nessuna prova può accorgersene.
- *Rifare `_avanzamento` attorno a `select` con un timeout sulla lettura.* Sposta il limite dal
  dump alla **singola riga**: un `mongodump` che scrive un avanzamento ogni tre secondi per un'ora
  non lo supererebbe mai, ed è esattamente il caso da fermare.
- *Non correggere il codice e correggere i due documenti.* È l'opzione più economica, e la scarta
  la frase stessa di ADR-0101: se una scena che non termina è peggio di una che termina male,
  togliere la promessa è togliere la cosa sbagliata.

**Fonti:** [M-059](../app/docs/Sources.md#m-059), [M-045](../app/docs/Sources.md#m-045),
[ADR-0101](#adr-0101), [ADR-0077](#adr-0077), [ADR-0012](#adr-0012)

<a id="adr-0119"></a>

## ADR-0119 — Ciò che la scena rompe, la scena lo ripara in un `finally`

**Data:** 2026-09-04 · **Stato:** Accettata

**Contesto:** in `ScenarioFailover.esegui`, `rompe(...)` e `ripara(...)` erano due righe consecutive
con in mezzo la fase più lunga della scena. Qualunque cosa sollevasse là dentro — il carico, la
resa, un Ctrl-C dato al prompt di `--step` — saltava la ripresa. La review di `codex` sulla PR #5 lo
ha rilevato e la misura lo conferma: con un carico che solleva alla seconda fase, la regia riceve
`[('ferma', 'mongo-rs-1')]` e basta, per tutti e due i modi del guasto. Il `finally` di `cli.py`
chiude il client e non tocca lo stack.

Nel modo `sospendi` lo stato in cui il laboratorio resta è peggiore che nel modo `ferma`. Un
container spento si vede: `docker compose ps` lo elenca `exited`. Un container **in pausa** è vivo,
tiene la sua memoria e non risponde a nessuno; è lo stato più facile da dimenticare e il più
difficile da diagnosticare la volta dopo, quando il replica set non elegge e non si capisce perché.

L'obiezione che ha tenuto aperta la decisione per un giorno: dentro la rete Compose la regia è
`RegiaAnnunciata`, che *annuncia* il comando e si ferma su un `input()`. Un `finally` che ripara
farebbe una domanda **proprio mentre qualcuno sta interrompendo la scena**. Guardando i quattro casi
uno per uno, l'obiezione si è ridotta a uno solo:

- dall'host, con `RegiaCompose`, la riparazione è immediata e silenziosa;
- sotto il registratore, la seconda finestra esegue la riparazione e conferma — funziona, ed è ciò
  che si vuole ([ADR-0115](#adr-0115), [ADR-0117](#adr-0117));
- dal palco, dopo un Ctrl-C, compare il comando e una domanda. Non è un blocco: è la domanda a cui
  chi conduce dovrebbe comunque rispondere, e un secondo Ctrl-C ne esce;
- con `stdin` che non è un terminale, `input()` alza `EOFError` **subito**. Da dentro un `finally`,
  durante la risalita, quell'eccezione **prende il posto** di quella che stava passando: chi guarda
  leggerebbe «EOF when reading a line» invece del motivo per cui la scena si è fermata.

Solo il quarto è un guaio, e costa otto righe.

**Decisione:** il `try` si apre **dopo** `rompe` e si chiude su un `finally` che chiama `ripara`.
L'eccezione risale: un `finally` che la mangiasse per «non disturbare» chiuderebbe la scena con i
numeri di un failover che nessuno ha guardato fino in fondo. E `_gia_fatto`, la conferma della regia
annunciata, assorbe l'`EOFError`: dove non c'è nessuno a cui fare la domanda, l'unica risposta
sensata è proseguire.

Due dettagli di posizione, che sono la decisione vera:

- **Il `try` si apre dopo `rompe`, non prima.** Il `finally` deve coprire ciò che è stato rotto, non
  ciò che non si è riusciti a rompere. Se `ferma` solleva — la regia senza socket del demone,
  [ADR-0095](#adr-0095) — il nodo non è mai caduto, e una ripresa chiesta lì sopra sarebbe un
  comando dato al buio: con la regia annunciata, una riga sullo schermo che dice a qualcuno di
  riavviare qualcosa che nessuno ha spento.
- **L'annuncio della ripresa resta dentro il `try`,** e `ripara` da solo nel `finally`. Sul percorso
  normale non cambia niente: annuncio, pausa di `--step`, riparazione. Su quello interrotto la
  riparazione avviene senza una **seconda** pausa, e non in silenzio — la regia che ha bisogno di un
  umano è quella che il comando lo scrive da sé. Una domanda sola, non due.

**Conseguenze:** una scena interrotta lascia il laboratorio nello stato in cui l'ha trovato, e
`tools/reset-demo.sh 02` torna a essere ciò che era: il rimedio per quando qualcosa è andato storto
*davvero*, non il passaggio obbligato dopo ogni Ctrl-C.

Il prezzo è che lo strumento fa una cosa di sua iniziativa nel momento in cui chi conduce ha appena
chiesto di smettere. È accettato consapevolmente: la riparazione è idempotente — `riavvia` e
`risveglia` su un nodo sano non fanno danno — ed è l'unica azione che il `finally` compie.

**Alternative scartate.**

- *Un `finally` che annuncia lo stato e la riga di ripristino, senza agire.* Difendibile, e costa la
  metà. Lascia però il container **in pausa** nel modo in cui dimenticarlo è più facile, e sposta su
  chi conduce un gesto che lo strumento sa fare e che nel novanta per cento dei casi è silenzioso.
- *La riparazione al confine di `cli.py`, nel `finally` che chiude il client.* Là non si sa che cosa
  la scena ha rotto né in che modo: servirebbe far uscire quello stato dallo scenario, cioè
  aggiungere un canale per non aggiungere un `try`.
- *Lasciare com'è e documentare `reset-demo.sh`.* Chiede a chi conduce di ricordarsene subito dopo
  che qualcosa è andato storto in pubblico, che è il momento in cui ci si ricorda peggio.
- *Assorbire anche l'`EOFError` di `_invio`, la pausa di `--step`.* Quella pausa non gira mai dentro
  un `finally`, e un `--step` chiesto senza terminale è un uso sbagliato che è giusto veda un
  errore.

**Fonti:** [ADR-0095](#adr-0095), [ADR-0115](#adr-0115), [ADR-0117](#adr-0117)

---

<a id="adr-0120"></a>

## ADR-0120 — Quattro scene, quattro bersagli, e una prova che nessuna resti scoperta

**Data:** 2026-09-06 · **Stato:** Accettata

**Contesto:** il `Makefile` copriva una scena su quattro. `demo failover` aveva `app-demo`; `demo
backup-live`, `demo restore` e `demo sharding` si scrivevano per esteso, `uv run --directory app
mongolab demo …`. Non era una svista: il `README` dichiarava l'asimmetria — «i comandi di uso più
frequente hanno un bersaglio nel `Makefile`» — e [ADR-0036](#adr-0036) aveva scartato l'idea di
avvolgere *ogni* comando in un bersaglio, con una ragione che regge ancora: chi guarda le slide deve
imparare `mongosh`, non questo repository. Il costo si è visto scrivendo il runbook, non
ragionandoci: il copione diventa bilingue e cambia registro **a metà dell'Atto III**, cioè nel punto
in cui chi conduce ha le mani più occupate. La domanda l'ha posta il Product Owner con gli stack
accesi davanti, ed è la ragione per cui la risposta è cambiata.

La ragione di [ADR-0036](#adr-0036) non morde qui, ed è il punto che distingue i due casi: là i
comandi avvolti sarebbero stati comandi **MongoDB**, e nasconderli dietro `make` avrebbe insegnato
il repository al posto del database. `mongolab demo sharding` è già un comando di questo repository:
avvolgerlo non nasconde niente che valga la pena imparare.

**Decisione.** Quattro punti.

- **Ogni sottocomando di `mongolab demo` ha un bersaglio.** `app-demo` per il failover — invariato,
  perché lo nominano le registrazioni, il runbook e tre pagine di `docs/`, e rinominarlo costerebbe
  più di quanto renda — più `app-backup`, `app-restore`, `app-sharding`.
- **La copertura è provata, non ricordata.**
  `test_ogni_scena_dell_applicazione_ha_un_bersaglio_nel_makefile` legge i decoratori
  `@demo.command` con `ast` e le ricette del `Makefile`, e confronta i due insiemi. Una scena nuova
  senza bersaglio fa fallire `make tools-test`. È lo stesso rimedio di [ADR-0049](#adr-0049) per le
  porte di `preflight`: non «era giusto quel giorno», ma «non è più sbagliabile in silenzio».
- **Le due scene dell'Atto III non offrono `DOVE`.** `mongodump` non è nell'immagine
  dell'applicazione ([M-044](../app/docs/Sources.md#m-044)) e quel container non ha il socket del
  demone Docker: girano dall'host e basta. I bersagli ci vanno da sé — non c'è niente da ricordare —
  ma se `DOVE` è scritto a mano diverso da `host`, `CHIEDI_SOLO_HOST` si ferma invece di eseguire
  altrove. Il guardiano guarda `$(origin DOVE)` e non solo il valore, perché deve distinguere il
  predefinito del file dalla richiesta esplicita di chi digita.
- **L'esempio che il guardiano suggerisce segue il bersaglio.** `ESEMPIO_TARGET` vale `rs` ovunque e
  `sharded` su `app-sharding`: prima, un `make app-sharding` senza `TARGET` consigliava
  `TARGET=rs`, che supera il guardiano del `Makefile` per andare a sbattere contro il rifiuto della
  CLI due secondi dopo. Un suggerimento che non funziona costa più del silenzio.

**Conseguenze.** Tre scene su quattro del copione si dicono in `make`, e le quattro stanno vicine in
`make help` con l'atto che le nomina. La quarta resta per esteso, e la ragione va scritta perché è
l'eccezione che sembra una dimenticanza: la riga del `restore` la **stampa** `demo backup-live`,
già completa del nome della collezione di carico, che ha la data dentro e cambia a ogni corsa
(`_prossimo_passo`). Tradurla in `ARGS` chiederebbe di ricopiare a mano davanti alla sala esattamente
la stringa che quel codice esiste per non far ricopiare. `app-restore` c'è lo stesso, e serve a chi
userà il repository dopo il talk, quando la collezione la sceglie chi comanda. Il ramo host di `ESEGUI` diventa `DALL_HOST`, perché ora ha
due usi e la stessa riga scritta due volte è la prima a divergere. `make help` guadagna in coda la
legenda di `TARGET`, `DOVE`, `ARGS`, `PROFILO` e `NOMI`: erano spiegate solo nei commenti del
`Makefile` e nelle pagine di `app/docs/`, cioè in nessun posto che chi arriva dopo il talk apra per
primo.

Il prezzo è un `Makefile` più lungo di una trentina di righe e quattro nomi in più da conoscere. È
accettato: sono quattro nomi che `make help` elenca, contro tre righe di sessanta caratteri da
ricopiare a memoria.

**Alternative scartate.**

- *Un bersaglio solo, `app-demo SCENA=failover|backup-live|restore|sharding`.* Più corto da
  scrivere e peggiore da leggere: le tre scene hanno vincoli **diversi** — due vogliono l'host, una
  vuole lo sharded — e un bersaglio unico o li ignora tutti o li controlla con un `case` dentro un
  `case`. `make help` mostrerebbe una riga sola dove servono quattro.
- *Rinominare `app-demo` in `app-failover`, con `app-demo` come alias.* Più simmetrico nell'elenco,
  e due nomi per la stessa cosa sono esattamente la frizione che questa ADR toglie. Le quattordici
  registrazioni non si rigirano per un nome.
- *Cablare `--target rs` nei due bersagli dell'Atto III.* Risparmia due parole e spegne una
  proprietà: la CLI controlla che il bersaglio **sia** un replica set, non che si chiami `rs`
  (`_solo_da_un_replica_set`), e il giorno in cui il repository ne avesse un secondo la riga giusta
  funzionerebbe da sé.
- *Forzare `DOVE=host` con `override` nei due bersagli dell'Atto III.* Funziona sempre e mente una
  volta: chi ha scritto `DOVE=rete` vedrebbe girare qualcos'altro senza che nessuno glielo dica.
- *Lasciare com'era e spiegarlo nel runbook.* È ciò che il runbook faceva, in due righe di prosa.
  Una spiegazione nel documento che si legge sotto pressione è un lavoro rimandato al momento
  peggiore (nota di metodo 243).

**Fonti:** [ADR-0012](#adr-0012), [ADR-0036](#adr-0036), [ADR-0049](#adr-0049), [ADR-0092](#adr-0092), [M-019](../app/docs/Sources.md#m-019), [M-044](../app/docs/Sources.md#m-044)

---

<a id="adr-0121"></a>

## ADR-0121 — La fotografia dice di che cosa è fatta, e poi quanto fa in tutto

**Data:** 2026-09-06 · **Stato:** Accettata

**Contesto:** `mongolab stats` stampava una riga sola per i documenti, `database lab · 50 000
documenti`, e quella riga è una **somma**. Su uno stack pulito coincide con `ordini` e nessuno se ne
accorge; appena l'Atto III è girato una volta, in `lab` resta una collezione `carico-AAAAMMGG-hhmmss`
da qualche migliaio di documenti e il totale sale. Il costo si è visto scrivendo il runbook: la
§1.4 diceva «`ordini`, 50 000, si verifica con `make app-stats`», e il comando rispondeva **62 602**.
Chi controlla lo stato atteso la sera prima del talk legge un guasto dove non c'è.

Il caso limite l'ha dato lo stack 01, che porta i residui delle registrazioni del 4 settembre: la
riga diceva **1 505 885**. Cinquantamila c'erano, e non c'era modo di saperlo dallo schermo
([V-090](Sources.md#v-090)).

**Decisione.** Tre punti.

1. **`stats` stampa una riga per collezione, e poi il totale del database.** La riga `collezioni`
   elenca ogni collezione con i suoi documenti, in ordine di nome; la riga `database` resta dov'era
   e dice la stessa cosa di prima. Il modello è `ContoCollezione`, la porta è `collection_counts()`,
   il rendering è `_collezioni` e riusa il gutter di `_topologia`.

2. **Il dettaglio viene prima della somma.** Un totale stampato sopra i suoi addendi si legge come
   il primo di essi, ed è precisamente l'errore di lettura da cui questa decisione viene. Sotto, la
   riga `database` chiude il conto.

3. **Il conteggio è esatto: `countDocuments`, non la stima dei metadati.** È lo stesso numero che
   verificano `demo restore` e gli smoke, e una fotografia che dicesse 49 998 dove la scena dice
   50 000 manderebbe a cercare un guasto nel posto sbagliato. Costa una scansione dell'indice `_id`,
   che su un laboratorio da cinquantamila documenti non si sente.

Le **viste** non si contano: `listCollections` le elenca insieme alle collezioni, e una vista non ha
documenti propri — comparirebbe con il conteggio della sorgente, cioè come un raddoppio. Il filtro è
`{"type": "collection"}`. `system.views`, invece, **si conta**: è la collezione vera in cui il
database tiene le definizioni, `dbStats` la somma, ed escluderla per far pulizia sullo schermo
romperebbe l'unica proprietà che rende la fotografia verificabile — che gli addendi facciano il
totale. L'attesa opposta era scritta in una prova, ed è la prova che l'ha smentita.

**Conseguenze.** La riga `collezioni` è lunga quanto le collezioni che ci sono: su uno stack pulito
è una riga, sullo stack 01 di oggi sono trentotto. È il prezzo di dire la verità su uno stack
sporco, e chi guarda capisce al primo sguardo *perché* il totale è quello.

La proprietà «gli addendi fanno il totale» vale su dati appena scritti e **non è garantita**: il
totale viene da `dbStats`, che somma contatori conservati per collezione, e quei contatori possono
restare indietro. Misurato lo stesso giorno sullo stack 01: somma 1 528 002, `dbStats.objects`
1 505 885, e lo scarto sta tutto in due collezioni che dichiarano **zero** mentre ne contengono
7 847 e 14 270. `validate()` risponde `valid: true` senza avvisi e intanto rimette il contatore a
posto. È la ragione per cui il conteggio è esatto e non stimato, ed è scritta nel runbook come
regola di lettura: **se le due righe litigano, ha ragione quella sopra**.

Attraverso un `mongos` le due righe possono divergere legittimamente: `dbStats` somma i metadati
degli shard, orfani compresi, mentre `countDocuments` conta i documenti **posseduti**. È la stessa
distinzione fra `numOwnedDocuments` e `numOrphanedDocs` che `shard_distribution` già tiene separate
([ADR-0106](#adr-0106)), e farla sparire vorrebbe dire cancellare l'unico posto in cui una
migrazione non ripulita si vede.

**Alternative scartate.**

- *Lasciare la riga sola e spiegarlo nel runbook.* È ciò che il runbook faceva, in due righe di
  prosa. Una spiegazione nel documento che si legge sotto pressione è un lavoro rimandato al momento
  peggiore (nota di metodo 243), e la prosa non dice mai *quale* collezione ha portato il totale a
  62 602.
- *Stampare solo la collezione che interessa, `ordini`.* Risolve la §1.4 e nasconde il resto: il
  milione e mezzo dello stack 01 resterebbe invisibile, e con esso il fatto che l'Atto III non è mai
  stato ripulito. La fotografia serve a far vedere lo stato, non a confermare un'attesa.
- *Contare con `estimated_document_count`.* Un istante invece di una scansione, e un numero che può
  essere **zero su una collezione piena** — misurato, due volte, lo stesso giorno
  ([V-090](Sources.md#v-090)).
- *Escludere `system.views` per pulizia.* Toglie una riga dallo schermo e rompe la somma. Una
  fotografia in cui gli addendi non fanno il totale non si può controllare a mente, ed era l'unica
  cosa che questa decisione prometteva.
- *Restituire una mappa nome → documenti invece di una tupla ordinata.* L'ordine è parte del
  risultato, perché è l'ordine in cui si legge; affidarlo all'ordine di inserimento di un `dict`
  vorrebbe dire affidarlo a `listCollections`, che non lo garantisce.

**Fonti:** [ADR-0092](#adr-0092), [ADR-0106](#adr-0106), [V-090](Sources.md#v-090)

---

<a id="adr-0122"></a>
## ADR-0122 — Lo stato della demo non sta solo nei database, e `reset-demo` toglie anche quello

**Data:** 2026-09-06 · **Stato:** Accettata

**Contesto:** [ADR-0088](#adr-0088) ha dato la pulizia a `reset-demo`, e le ha dato un criterio
scritto dentro un database: «spazza tutto ciò che non è `ordini`». Il criterio ha retto finché la
demo ha lasciato in giro soltanto collezioni. Poi il 6 settembre, alla prima ripresa della scena
14, `mongorestore` ha rimesso in piedi **sei** collezioni invece di una: `demo backup-live` scrive
in `/tmp/mongolab-backup` **dentro `mongo-rs-1`**, e `mongodump --out` non svuota la destinazione —
ci aggiunge. Una prova generale ripetuta cinque volte lascia cinque dump, e il restore li ripristina
tutti, elencati una riga per collezione davanti alla sala.

Quella cartella era l'unico pezzo di stato della demo che non stava né in un database né in un
volume: sta nel livello scrivibile del container ([V-091](Sources.md#v-091)). Per questo non la
toglieva nessuno — non perché qualcuno avesse deciso di lasciarla, ma perché nessuna delle regole
scritte la nominava.

**Decisione.** Due punti.

1. **`reset-demo.sh 02` svuota anche `/tmp/mongolab-backup` in `mongo-rs-1`.** Il criterio di
   ADR-0088 si legge in avanti: `reset-demo` riporta lo stack allo stato da cui la scena comincia, e
   quello stato comprende tutto ciò che una corsa lascia dietro, non solo ciò che finisce in un
   database. Solo sullo stack 02, per la stessa ragione per cui solo lì si toglie
   `lab_ripristinato`: `demo backup-live` pretende un primario e `demo restore` rifiuta un bersaglio
   che non sia un replica set ([ADR-0102](#adr-0102)), quindi sugli stack 01 e 03 quella cartella non
   può esistere e una riga che la cercasse direbbe sempre «niente».

2. **Il verdetto guarda prima di togliere.** `rm -rf` esce zero tanto se la cartella c'era quanto se
   non c'era: è lo stesso difetto di `dropDatabase()`, che risponde `dropped` anche per un database
   mai esistito, con un altro comando. Il conteggio si fa con un `ls` **prima** del `rm`, e conta i
   `.bson` sotto `lab` — cioè le collezioni che il restore avrebbe rimesso in piedi, non i file del
   dump: `admin/` e `oplog.bson` ci sono ma il restore li esclude con `--nsInclude lab.*`.

**Conseguenze.** Chi conduce non deve più ricordarsi un comando a mano fra una prova generale e
l'altra, che è la forma di debito che ADR-0088 aveva già rifiutato una volta. Il numero che lo
script dice non è una conferma, è un'informazione: «dump rimossi: 2 collezioni» racconta quante
corse sono passate di lì senza che nessuno pulisse.

La cartella non sopravvive a `down` (V-091), e questo va detto perché cambia il rimedio lento: chi
vuole ripartire da zero sulla copia non ha bisogno di `make reset-02`, che cancella i volumi. Ma il
rimedio lento adesso serve ancora meno, perché il rimedio veloce fa la stessa cosa.

**Alternative scartate.**

- *Lasciarlo al runbook, con il comando a mano.* È ciò che c'era, scritto in §1.4 il 6 settembre
  mattina. Un passo che si legge sotto pressione è un passo che si salta, e infatti la prima ripresa
  della scena 14 l'ha saltato: il difetto è stato scoperto dalla registrazione, non dalla lettura.
- *Far svuotare la destinazione a `demo backup-live` prima di copiare.* Sposta la pulizia dentro la
  scena che si proietta, e un comando che cancella prima di scrivere è un comando che, lanciato per
  sbaglio, toglie l'unica copia esistente. `mongodump --out` non lo fa, e ha ragione a non farlo.
- *Togliere solo i dump vecchi e tenere l'ultimo.* Chiede allo script di indovinare che cosa serva
  alla scena successiva. `reset-demo` riporta allo stato di **partenza**, e alla partenza la copia
  non c'è: è la scena a costruirla, in dieci secondi.
- *Montare `/tmp` su un volume nominato, per poterlo cancellare con `down -v`.* Renderebbe
  permanente ciò che deve essere effimero, e `down -v` qui è già vietato perché cancellerebbe il
  volume del keyfile ([ADR-0014](#adr-0014)).
- *Fidarsi del codice di uscita di `rm -rf`.* Misurato lo stesso giorno sul comando gemello: un
  esito che vale in tutti e due i casi non è un verdetto, è una frase che sembra una risposta.

**Fonti:** [ADR-0088](#adr-0088), [ADR-0102](#adr-0102), [V-091](Sources.md#v-091)

<a id="adr-0123"></a>
## ADR-0123 — Le skill importate si versionano col repository, entrano verbatim, e perdono contro una scheda

**Data:** 2026-09-06 · **Stato:** Accettata

**Contesto:** il 6 settembre il Product Owner ha chiesto di riprendere dal repository d'origine,
ramo `step/azure-policy/allineamento-e-fase-1`, il contenuto di `.claude/skills` e di
`Docs/Concetti-Generali`, e di incorporarlo nella release in corso.

I tre documenti non pongono problemi: sono testi, si leggono, si citano. Le dodici skill sì. Una
skill non è documentazione: **si accende da sola**, durante una sessione, quando il modello giudica
che il caso sia suo, e da quel momento indirizza il lavoro. È materiale operativo che entra in un
repository senza che nessuno lo abbia invocato, e che arriva da un progetto che ha preso decisioni
proprie — alcune diverse dalle nostre, prese per ragioni che qui non valgono.

Copiate e basta, non funzionavano. Misurato sul pacchetto verbatim ([V-092](Sources.md#v-092)):
delle dodici descrizioni, **nove** nominano il repository d'origine come condizione e qui non si
sarebbero accese mai; **due** lo nominano per negazione — «use when the repository is NOT the
origin one» — e quelle qui si accendono sempre; **una** è generica e scrive gli ADR in
`docs/adr/`, che qui non esiste. Undici su dodici erano quindi o mute o fuori bersaglio.

E fra le due che si accendono c'è `git-flow`, il cui file `references/comandi.md` elenca
`git flow feature finish`: il comando che in questo repository è vietato da quando, sulla PR #1,
chiuse un ramo saltando la revisione. Il modello dei rami di qui ha la forma di Git Flow e
differisce solo nella chiusura — è la somiglianza a rendere efficace la trappola.

**Decisione.** Cinque punti.

1. **Installazione di progetto, non personale.** Le skill stanno in `.claude/skills/` e si versionano
   con il repository. Sono convenzioni di questo progetto, e il loro senso è viaggiare con esso: chi
   clona ha il metodo insieme al codice, e una modifica al metodo si rivede in una PR come qualsiasi
   altra. `.gitignore` continua a escludere solo ciò che è della macchina — `settings.local.json`,
   `.headroom_*`, `worktrees/` — e in più `.revisioni/`, che è materiale di lavorazione della
   revisione esterna: nel repository entra soltanto il foglio archiviato.

2. **Verbatim prima, adattamento dopo, in due commit distinti.** Il pacchetto entra byte per byte
   come sta a monte ([`65385ec`](https://github.com/giulianolatini/SqlStart2026/commit/65385ec)),
   verificato con `diff -r` contro il clone; l'adattamento è il commit successivo
   ([`25b5df6`](https://github.com/giulianolatini/SqlStart2026/commit/25b5df6)). Così ciò che
   abbiamo cambiato **è un diff**, leggibile e discutibile, invece di un'affermazione. È la stessa
   sequenza che il repository d'origine usò per sé.

3. **L'adattamento tocca la `description` e un blocco in testa. I corpi restano intatti.** La
   `description` perché è la superficie che decide se una skill si accende, ed è l'unica parte che
   non si può correggere da fuori. Il blocco `[!IMPORTANT]` perché una skill dev'essere in grado di
   dire, nel momento in cui viene letta, se qui governa, non governa, o è testo di riferimento.
   Nient'altro: dieci righe per file, 108 in tutto. Il resto si lascia stare **apposta**, perché
   queste sono copie e un miglioramento fatto a monte andrà riportato a mano — con i corpi intatti
   quel riporto resta un diff, con i corpi riscritti diventa una fusione.

4. **In conflitto fra una skill e una scheda accettata di questo file, vince la scheda.** La regola
   sta nel blocco in testa a **tutte e dodici**, non solo nella pagina di provenienza: serve dove
   viene letta. Una skill è un testo persuasivo che si presenta al momento giusto; senza una regola
   di precedenza scritta, prima o poi riscrive una decisione presa, e nessuno se ne accorge.

5. **Cinque governano, sette no, e ciascuna lo dice di sé.** Governano `decision-md`, `sources-md`,
   `registro-di-sviluppo`, `revisione-pr` e `adr-brainstorm` (quest'ultima fino alla fase 3: la
   scrittura passa a `decision-md`). Non governano `changelog-di-chiusura`, `project-memory`,
   `worktree-di-step`, `modello-dei-rami`, `workflow-conventions`; `git-flow` e `github-flow`
   restano testi di riferimento, **e i loro comandi non si eseguono qui**. Il quadro completo, con le
   divergenze di forma di quelle che governano, sta in
   [`docs/06-sviluppo/concetti-generali/README.md`](06-sviluppo/concetti-generali/README.md).

**Conseguenze.** Cinque skill diventano operative subito, e portano dentro pratiche che qui erano
consuetudine non scritta. Sette sono inerti per costruzione: continuano a occupare 272 KB nel
repository, ed è un costo accettato in cambio della possibilità di riprenderle senza ripetere
l'import.

Le tre suite che le skill si portano dietro entrano nel repository e girano senza rete: 127 prove,
tutte passate dopo l'adattamento. Non sono nel `make check` — provano gli script della skill, non il
lab — ma esistono e si lanciano a mano.

L'import ha scoperto un vuoto che non colma: **questo repository non ha una scheda che fissi il
proprio modello dei rami, la strategia di merge o lo standard dei messaggi di commit.** La pratica
c'è, è coerente ed è descritta in
[`worktree-e-branch-di-lavoro.md`](06-sviluppo/worktree-e-branch-di-lavoro.md), ma non è mai stata
registrata come decisione — e finora nessuno l'aveva notato, perché nessuno l'aveva contraddetta.
L'hanno resa visibile proprio le skill che quelle decisioni le pretendono.

**Alternative scartate.**

- *Installazione personale, in `~/.claude/skills/`.* È l'altra strada che il runbook documenta, e
  costa meno: nessun file nel repository, nessun peso nel diff. Ma il metodo resterebbe sulla
  macchina di una persona, invisibile a chi clona e non rivedibile in una PR. Un repository che
  registra ogni decisione in una scheda non può tenere fuori dal controllo di versione le regole con
  cui quelle schede si scrivono.
- *Importare solo le cinque che governano.* Toglie 272 KB e ogni ambiguità. Ma le sette scartate
  sono scartate **oggi**: `changelog-di-chiusura` servirà il giorno in cui questo repository avrà un
  `CHANGELOG.md`, e `github-flow` è il testo con cui si confronta il modello quando si discute di
  cambiarlo. Scartare significa doverle ricercare, e la ricerca ricomincia da capo — mentre tenerle
  con un verdetto scritto in testa costa una tabella.
- *Riscrivere le skill invece di adattarle.* Produce testi che parlano di questo repository e di
  nessun altro, più chiari da leggere. E rompe il legame con l'origine: da quel momento non esiste
  più un `diff` da fare contro monte, e ogni miglioramento fatto là va riscoperto leggendo.
- *Adattare tutto in un commit solo, senza il passaggio verbatim.* Un commit più corto, e la perdita
  dell'unica cosa che rende verificabile l'import: senza la base identica, «i corpi sono intatti» è
  una promessa e non un fatto controllabile.
- *Mettere la regola di precedenza solo nella pagina di provenienza.* Una pagina che si potrebbe non
  aprire. Le skill si presentano da sole, spesso in mezzo a un lavoro: la regola deve stare dove
  arriva l'interruzione.
- *Lasciare `git-flow` com'era, trattandolo come documentazione.* È ciò che sarebbe successo senza
  guardare le descrizioni. Una skill che si accende da sola e offre il comando vietato non è
  materiale di riferimento: è una trappola, e la sua forma somigliantissima al modello di qui la
  rende più pericolosa, non meno.

**Fonti:** [V-092](Sources.md#v-092), [ADR-0052](#adr-0052)
