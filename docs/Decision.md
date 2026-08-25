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

**Fonti:** [S-001](Sources.md#s-001), [S-002](Sources.md#s-002), [S-003](Sources.md#s-003), [S-026](Sources.md#s-026)

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

**Data:** 2026-08-24 · **Stato:** Accettata

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

**Fonti:** [S-003](Sources.md#s-003), [S-004](Sources.md#s-004)

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

**Data:** 2026-08-25 · **Stato:** Accettata

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

**Fonti:** [S-001](Sources.md#s-001), [V-002](Sources.md#v-002), [V-004](Sources.md#v-004)
