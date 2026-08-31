# Leggere i log di MongoDB

Durante il talk un nodo cadrà davanti a tutti, e l'unica prova che il cluster se ne è accorto
sarà il log proiettato su uno schermo. Non è il momento di imparare a leggerlo. Questa pagina
serve a saperlo già.

Comincia con una misura scomoda: in un'istanza che **non sta facendo assolutamente niente**, il
91,9 % delle righe di log parla di connessioni, e il 99,3 % di quelle nuove ogni minuto è il
controllo di salute che chiede «stai bene?» ([V-019](../Sources.md#v-019)). Un log così non si
legge scorrendolo. Si interroga.

> **Cosa è stato misurato e cosa no.** Le sezioni [1](#1-formato-e-componenti) e
> [2](#2-logrotate-e-perché-in-container-non-serve) sono state eseguite sullo stack
> `01-standalone` di questo repository, immagine `mongo:7.0.40`, e ogni numero che riportano
> viene da lì. La sezione [3](#3-cosa-cercare-durante-unelezione) è scritta **dal manuale e non
> dalla misura**: su un'istanza singola non esistono elezioni. Gli identificatori delle righe che
> compaiono davvero durante un'elezione saranno inseriti in `feature/02-stack-replicaset`, dopo
> averne vista una. Il debito è dichiarato in [ADR-0035](../Decision.md#adr-0035) e va saldato là.

---

<a id="1-formato-e-componenti"></a>
## 1. Formato e componenti

### 1.1 Una riga è un oggetto JSON, e i campi sono sempre quelli

Dalla 4.4 in poi MongoDB scrive il log in JSON, e lo fa ovunque: «All log output is in JSON
format including output sent to: Log file · Syslog · Stdout (standard out)»
([S-042](../Sources.md#s-042)). Ogni riga è un oggetto autonomo — non c'è un preambolo da saltare
né uno stato da ricostruire leggendo le righe precedenti — e l'ordine dei campi è fissato:

```javascript
{
  "t": <Datetime>,            // timestamp
  "s": <String>,              // severity
  "c": <String>,              // component
  "id": <Integer>,            // unique identifier
  "ctx": <String>,            // context
  "msg": <String>,            // message body
  "attr": <Object>            // additional attributes (optional)
  "tags": <Array of strings>  // tags (optional)
  "truncated": <Object>       // truncation info (if truncated)
  "size": <Object>            // original size of entry (if truncated)
}
```

Una riga vera, presa dal log dello stack di questo repository:

```json
{"t":{"$date":"2026-08-28T11:53:26.563+00:00"},"s":"W",  "c":"CONTROL",  "id":22120,   "ctx":"initandlisten","msg":"Access control is not enabled for the database. Read and write access to data and configuration is unrestricted","tags":["startupWarnings"]}
```

Vale la pena leggerla campo per campo, perché tutto quello che segue si appoggia a questi dieci
nomi.

| campo | in questa riga | a cosa serve davvero |
| --- | --- | --- |
| `t` | l'istante, con millisecondi e fuso | dentro il container il fuso è UTC, non quello del portatile: quando si correlano log e orologio della sala, la differenza si vede |
| `s` | `W` | la severità. Quattro valori si vedono sempre, cinque quasi mai — [§1.2](#12-le-severità-quattro-che-si-vedono-e-cinque-che-non-si-vedono) |
| `c` | `CONTROL` | il sottosistema che parla. È il primo filtro utile — [§1.3](#13-i-componenti-e-chi-occupa-il-log) |
| `id` | `22120` | **l'unico riferimento stabile della riga.** [S-042](../Sources.md#s-042) lo definisce «Unique identifier for the log statement» |
| `ctx` | `initandlisten` | il filo di esecuzione. Per le connessioni vale `connNNN` e permette di seguire una sessione dall'inizio alla fine; `listener` è il filo che accetta |
| `msg` | il testo | **è illustrazione, non chiave.** La fonte non promette da nessuna parte che resti identico fra versioni |
| `attr` | assente qui | i valori variabili. Tenerli fuori dal `msg` è ciò che rende il log aggregabile: mille righe con lo stesso `id` e `attr` diversi |
| `tags` | `["startupWarnings"]` | etichette. Questa è l'unica che il lab usa — [§1.4](#14-tre-modi-di-interrogare-il-log-e-uno-che-non-funziona) |
| `truncated`, `size` | assenti | compaiono solo quando la riga era troppo lunga ed è stata tagliata. Vederli significa che il contenuto originale **non c'è più** nel log |

**La regola operativa che ne discende**, ed è la ragione per cui in tutto questo repository le
righe si citano per numero: si cerca `"id":22943`, non `Connection accepted`. Il testo è utile a
capire, il numero a ritrovare. Una guida che insegnasse a cercare per testo invecchierebbe alla
prima riformulazione del messaggio, e invecchierebbe in silenzio: il lettore cerca, non trova, e
conclude che il server non ha fatto quella cosa ([ADR-0035](../Decision.md#adr-0035)).

### 1.2 Le severità: quattro che si vedono, e cinque che non si vedono

«Severity levels range from "Fatal" (most severe) to "Debug" (least severe)»
([S-042](../Sources.md#s-042)):

| `s` | nome | quando compare | nel log misurato |
| --- | --- | --- | ---: |
| `F` | Fatal | il server sta per morire | **0** |
| `E` | Error | un'operazione è fallita | **0** |
| `W` | Warning | qualcosa non va come dovrebbe, ma si continua | **30** |
| `I` | Informational | tutto il resto, a verbosità `0` | **9892** |
| `D1`–`D5` | Debug | solo alzando la verbosità sopra `0` | — |

Le proporzioni contano più dei valori assoluti: **lo 0,3 % del log** è ciò che un amministratore
vuole vedere. E le trenta `W` non sono trenta cose diverse — sono sei, ripetute a ogni avvio:

```console
$ docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml \
    logs --no-log-prefix mongo-standalone | grep '^{' \
  | jq -r 'select(.s=="W") | "\(.c) \(.id) \(.msg)"' | sort | uniq -c | sort -rn
  11 NETWORK 11621101 Overriding max connections to honor `capMemoryConsumptionForPreAuthBuffers` settings
   5 CONTROL 9068900 For customers running MongoDB 7.0, we suggest changing the contents of the following sysfsFile
   5 CONTROL 22120 Access control is not enabled for the database. Read and write access to data and configuration is unrestricted
   5 CONTROL 20720 Memory available to mongo process is less than total system memory
   2 STORAGE 22302 Recovering data from the last clean checkpoint.
   2 STORAGE 22271 Detected unclean shutdown - Lock file is not empty
```

Tre righe da leggere con attenzione, perché raccontano tre cose diverse.

- Il `5` accanto a `22120` e a `20720` non dice che il problema si è ripresentato cinque volte:
  dice che **`mongod` è partito cinque volte** dentro questo stesso container. `docker logs`
  conserva l'intera vita del container, riavvii compresi, e il `mongod` temporaneo che
  l'entrypoint accende per eseguire gli script di inizializzazione conta come uno
  ([V-019](../Sources.md#v-019)).
- `22271` — `Detected unclean shutdown - Lock file is not empty` — compare **due** volte, ed è la
  cicatrice degli esperimenti di [V-017](../Sources.md#v-017): due volte il processo è stato
  fermato senza chiudere. La riga che la segue, `22302`, è il recupero dall'ultimo checkpoint.
  Trovare questa coppia in un log di produzione significa che qualcuno, o qualcosa, ha spento
  male il database.
- `22120` — `Access control is not enabled for the database` — è il server che avvisa di essere
  aperto a chiunque. Il lab lo è di proposito ([ADR-0005](../Decision.md#adr-0005)), ma va notato
  che l'avviso **c'è**, a ogni singolo avvio, e in diecimila righe non lo legge nessuno. È il
  motivo per cui esiste [§1.4](#14-tre-modi-di-interrogare-il-log-e-uno-che-non-funziona).

Le altre tre sono figlie dell'ambiente e non di un errore: `9068900` chiede di disattivare le
*transparent huge pages* — e riguarda la VM Linux di Docker Desktop, non il Mac che la ospita —
mentre `20720` e `11621101` sono la conseguenza del tetto di memoria imposto al container
([ADR-0004](../Decision.md#adr-0004), [`06-sviluppo/gestione-risorse-compose.md`](../06-sviluppo/gestione-risorse-compose.md)):
il server si accorge di avere meno RAM della macchina e
ridimensiona il numero massimo di connessioni.

### 1.3 I componenti, e chi occupa il log

Il campo `c` dice quale sottosistema parla. I componenti hanno una **gerarchia**: `REPL` è il
genitore di `ELECTION`, `INITSYNC`, `REPL_HB` e `ROLLBACK`; `STORAGE` lo è di `JOURNAL` e
`RECOVERY` ([S-042](../Sources.md#s-042)). Se non si imposta la verbosità di un figlio, eredita
quella del genitore — utile quando si vuole alzare il dettaglio della sola replicazione senza
annegare nel resto.

Ecco come si spartiscono le 9922 righe misurate:

| componente | righe | quota | che cos'è |
| --- | ---: | ---: | --- |
| `NETWORK` | 7146 | 72,0 % | connessioni accettate, chiuse, metadati del client |
| `ACCESS` | 1971 | 19,9 % | autenticazione — qui, la sua assenza |
| `STORAGE` | 388 | 3,9 % | WiredTiger, avvio, recupero |
| `CONTROL` | 89 | 0,9 % | ciclo di vita del processo |
| `EXECUTOR` | 88 | 0,9 % | pool di thread |
| `WTCHKPT` | 61 | 0,6 % | i checkpoint periodici |

`NETWORK` e `ACCESS` insieme fanno **9117 righe, il 91,9 %**. Non perché lo stack sia trafficato:
perché **una connessione costa quattro righe** e qualcuno bussa in continuazione.

| ordine | `id` | componente | `msg` |
| --- | --- | --- | --- |
| 1 | `22943` | `NETWORK` | `Connection accepted` |
| 2 | `51800` | `NETWORK` | `client metadata` |
| 3 | `10483900` | `ACCESS` | `Connection not authenticating` |
| 4 | `22944` | `NETWORK` | `Connection ended` |

A cui si aggiunge `6788700` (`Received first command on ingress connection since session start or
auth handshake`) sulle connessioni su cui arriva davvero un comando.

Chi bussa è l'healthcheck del file Compose, che ogni dieci secondi lancia un `mongosh` per un
`ping` ([V-012](../Sources.md#v-012)). E qui c'è la sorpresa: **una sola invocazione di `mongosh`
apre cinque connessioni, non una.** Misurate: `connectionId` da 804 a 808 in novantanove
millisecondi, tutte chiuse insieme all'uscita del processo ([V-019](../Sources.md#v-019)).

L'aritmetica del log a riposo è quindi tutta qui:

```text
 6 healthcheck/minuto × 5 connessioni × 4 righe = 120 righe
 6 healthcheck/minuto × 3 primi comandi                =  18 righe
 1 checkpoint di WiredTiger                            =   1 riga
                                                        ───────────
                                                          139 righe/minuto
```

Misurate in sessanta secondi e un decimo: **139 righe, di cui 138 dall'healthcheck**. Un'istanza
MongoDB che non fa niente scrive più di centotrenta righe al minuto per dire che sta bene. È il
numero da tenere a mente quando si dimensiona la rotazione ([§2](#2-logrotate-e-perché-in-container-non-serve))
e quando si guarda il disco riempirsi ([trappola 10](../02-architetture/trappole-mongodb-in-docker.md#t-10)).

> **Conseguenza di scena.** Proiettare `logs -f` durante la demo mostra soprattutto l'healthcheck.
> Se il log va sullo schermo, va filtrato prima — e il filtro va provato prima.

### 1.4 Tre modi di interrogare il log, e uno che non funziona

**Primo: gli avvisi d'avvio, senza cercarli.** MongoDB etichetta le righe che vuole far notare
all'avvio con `tags: ["startupWarnings"]`, e le tiene a disposizione in memoria. Chiederle è
istantaneo e restituisce **tre righe invece di novemilanovecento**:

```console
$ docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml \
    exec -T mongo-standalone mongosh --quiet --eval \
    'const r = db.adminCommand({getLog: "startupWarnings"});
     print(r.totalLinesWritten);
     r.log.forEach(l => { const o = JSON.parse(l); print(o.s + " " + o.id + " " + o.msg); })'
3
I 22297 Using the XFS filesystem is strongly recommended with the WiredTiger storage engine. See http://dochub.mongodb.org/core/prodnotes-filesystem
W 22120 Access control is not enabled for the database. Read and write access to data and configuration is unrestricted
W 9068900 For customers running MongoDB 7.0, we suggest changing the contents of the following sysfsFile
```

`totalLinesWritten: 3`, e sono quelle dell'**avvio corrente** — non le quindici accumulate nel
file dalle cinque partenze. È il primo comando da dare su un server che non si conosce: in un
secondo si sa che è senza autenticazione, che il filesystem non è quello consigliato e che le
*huge pages* sono configurate male.

**Secondo: filtrare per severità.** Per sapere se è successo qualcosa, si tolgono le informative:

```console
$ docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml \
    logs --no-log-prefix mongo-standalone | grep -v '"s":"I"' | wc -l
      46
```

Quarantasei, non trenta. La differenza sono **sedici righe che non sono log**: nove di testo e
sette vuote ([§1.5](#15-le-nove-righe-che-non-sono-json)). Un filtro per severità non seleziona
le righe importanti — scarta quelle informative, e tutto ciò che non è una riga di log
sopravvive per esclusione. Se il conteggio deve essere esatto, si conta ciò che si vuole, non ciò
che non si vuole: `grep -c '"s":"W"'` dà `30`.

**Terzo: filtrare per `id`.** È il modo in cui si segue un evento specifico.

```console
$ docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml \
    logs --no-log-prefix mongo-standalone | grep -c '"id":22943'
```

Questo numero è diverso ogni volta che si esegue il comando, e cresce di trenta al minuto: è la
stessa cosa detta da un'altra angolazione. Con `jq` disponibile il filtro diventa leggibile —
`jq 'select(.id==22943)'` — ma `jq` non è nell'immagine e non è garantito sul portatile:
`grep '"id":NNNNN'` funziona ovunque, perché il campo `id` è sempre scritto senza spazi attorno
ai due punti.

**E quello che non funziona:** cercare il testo del messaggio. `grep 'Connection accepted'`
oggi trova le stesse righe di `grep '"id":22943'`, e continuerà a farlo finché a MongoDB non
verrà in mente di riformulare quella stringa. Nessuna fonte lo vieta e nessuna lo promette; il
campo dichiarato univoco è uno solo, ed è `id`.

Un dettaglio che si scopre solo provando: `docker compose logs` da questo repository **non
funziona senza `--env-file tools/images.env`**, perché nei file Compose l'immagine è una
variabile obbligatoria e senza il file l'interpolazione fallisce prima ancora di guardare i
container. Da qui la lunghezza dei comandi qui sopra; per l'uso quotidiano c'è
[`make logs-01`](../../Makefile), che segue il log dello stack in tempo reale.

### 1.5 Le nove righe che non sono JSON

[S-042](../Sources.md#s-042) dice che **tutto** l'output è JSON. Nel log di questo stack ci sono
nove righe che non lo sono, più sette righe vuote:

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

La fonte non è smentita: **nessuna di queste righe la scrive `mongod`.** Le prime tre e le ultime
due sono l'entrypoint dell'immagine, che avvia un server temporaneo per eseguire gli script di
inizializzazione e poi lo spegne; le quattro centrali sono lo script di questo repository
([ADR-0031](../Decision.md#adr-0031)). Il log di un container è lo `stdout` del container, non il
log del database: contiene il database e tutto ciò che gli sta attorno.

Queste nove righe hanno un uso pratico: sono la **ricevuta dell'inizializzazione**. La loro
assenza, in un container che pure risponde, è il sintomo della
[trappola 1](../02-architetture/trappole-mongodb-in-docker.md#t-01) — il volume non era vuoto e
gli script non sono stati eseguiti. Cercarle costa un comando:

```console
$ docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml \
    logs --no-log-prefix mongo-standalone | grep 'docker-entrypoint-initdb.d'
```

---

<a id="2-logrotate-e-perché-in-container-non-serve"></a>
## 2. `logRotate`, e perché in container non serve

### 2.1 Cosa dice il manuale

Il comando «allows you to rotate the MongoDB server log and/or audit log to prevent a single
logfile from consuming too much disk space», si emette sul database `admin`, e accetta `1` per
ruotare tutto, `"server"` o `"audit"` per scegliere ([S-043](../Sources.md#s-043)). Esiste anche
la via del segnale: «You may also rotate the logs by sending a `SIGUSR1` signal to the `mongod`
process.»

Le due modalità cambiano chi possiede il file. Con `systemLog.logRotate` a **`rename`** il server
rinomina il file esistente aggiungendovi un timestamp nella forma `<YYYY>-<mm>-<DD>T<HH>-<MM>-<SS>`
e ne apre uno nuovo. Con **`reopen`** il server chiude e riapre lo **stesso nome**, lasciando a
qualcun altro — tipicamente `logrotate(8)` di sistema — il compito di aver già spostato il file.
Sbagliare accoppiata è il modo classico di ritrovarsi con un log che scrive su un file cancellato.

E poi c'è la riga che conta, sotto *Limitations*: «Your `mongod` instance needs to be running with
the `--logpath [file]` option in order to use `logRotate`».

### 2.2 Cosa fa il server qui

Il limite è documentato. Non è **applicato**. Su questo stack, dove il log va su `stdout` e
`--logpath` non c'è, il comando risponde `ok: 1` e non ruota niente
([V-010](../Sources.md#v-010)):

```javascript
db.adminCommand({ logRotate: 1 })
// { ok: 1 }
```

Nessun errore, nessun avviso, nessun file. Chi lo mettesse in uno script di manutenzione
otterrebbe un'operazione che riesce sempre e non fa mai niente — la specie più difficile da
diagnosticare, perché il monitoraggio la vede verde. La voce completa è la
[trappola 9](../02-architetture/trappole-mongodb-in-docker.md#t-09).

### 2.3 La decisione: in container la rotazione è del runtime

Questo stack scrive i log su `stdout` di proposito ([ADR-0030](../Decision.md#adr-0030)): è la
convenzione dei container, è ciò che rende `docker compose logs` la fonte unica, ed è ciò che
permette a un raccoglitore esterno di leggere senza montare volumi. Il prezzo è che `logRotate`
diventa inerte, e la crescita del file la governa Docker con `logging.options`
(`max-size`, `max-file`), non MongoDB.

Con le 139 righe al minuto misurate in [§1.3](#13-i-componenti-e-chi-occupa-il-log), il conto si
fa a mente: un'istanza a riposo produce circa **duecentomila righe al giorno**, e nel lab il
tetto imposto al file di log tiene il disco sotto controllo per l'intera giornata di prove
([V-011](../Sources.md#v-011), [trappola 10](../02-architetture/trappole-mongodb-in-docker.md#t-10)).

Fuori dai container il discorso si ribalta: con un `mongod` installato sul sistema e un
`--logpath` vero, `logRotate` è lo strumento giusto e `SIGUSR1` la sua scorciatoia. Le procedure
per quel caso stanno in [`01-installazione/linux.md`](../01-installazione/linux.md).

---

<a id="3-cosa-cercare-durante-unelezione"></a>
## 3. Cosa cercare durante un'elezione

> **Sezione non verificata su questo branch.** Qui non esiste un replica set, e quindi non esiste
> un'elezione da guardare. Quanto segue viene da [S-044](../Sources.md#s-044) e da
> [S-042](../Sources.md#s-042): il **meccanismo** e i **componenti** sono documentati, gli `id`
> delle righe no — nessuna delle due fonti ne nomina uno. Verranno inseriti in
> `feature/02-stack-replicaset` dopo aver provocato un'elezione vera e averla letta. Finché
> questo riquadro è qui, la sezione è una mappa, non un resoconto
> ([ADR-0035](../Decision.md#adr-0035)).

### 3.1 Il meccanismo, e i tre numeri che lo governano

I membri di un replica set si controllano a vicenda in continuazione. Tre numeri, tutti da
[S-044](../Sources.md#s-044), spiegano tutto ciò che si vedrà scorrere:

| numero | cosa significa |
| --- | --- |
| **2 secondi** | «Replica set members send heartbeats (pings) to each other every two seconds» |
| **10 secondi** | «If a heartbeat does not return within 10 seconds, the other members mark the delinquent member as inaccessible» |
| **12 secondi** | «The median time before a cluster elects a new primary should not typically exceed 12 seconds, assuming default replica configuration settings» |

Tra il gesto che uccide il nodo e il primario nuovo passa quindi molto più tempo di quanto
sembri accettabile stando su un palco in silenzio: **una decina di secondi prima che qualcuno se
ne accorga**, e altri pochi per votare. Nel frattempo, e questa è la frase da tenere: «The
replica set cannot process write operations until the election completes successfully.» Le
letture possono continuare, se il client è configurato per accettare un secondario; le
scritture no.

Un'elezione non parte solo per un guasto. [S-044](../Sources.md#s-044) elenca anche l'aggiunta di
un nodo, `rs.initiate()`, `rs.reconfig()` e `rs.stepDown()`: il che significa che la
manutenzione ordinaria produce lo stesso tracciato nel log di un incidente, e che leggere una
riga di elezione non basta a sapere se c'è stato un problema.

### 3.2 Dove guardare: quattro componenti

Non c'è bisogno degli `id` per sapere **dove** guardare, perché la gerarchia dei componenti è
documentata ([S-042](../Sources.md#s-042)):

| componente | contiene | perché interessa |
| --- | --- | --- |
| `REPL_HB` | «messages related specifically to replica set heartbeats» | è qui che appare, per primo, il battito che non torna |
| `ELECTION` | «messages related specifically to replica set elections» | il voto: chi si candida, chi vota, chi vince |
| `REPL` | il genitore dei precedenti | cambi di stato dei membri: `PRIMARY`, `SECONDARY`, `ROLLBACK` |
| `ROLLBACK` | figlio di `REPL` | compare quando un ex primario deve buttare via scritture che nessun altro aveva — il caso che rende concreto `w: "majority"` |

Poiché sono padre e figli, si può alzare la verbosità della sola replicazione senza toccare il
resto: è la mossa da preparare **prima** della demo, non durante.

Attenzione a un falso amico misurato qui: sull'istanza singola di questo lab il componente `REPL`
compare **42 volte** pur non essendoci alcuna replica ([V-019](../Sources.md#v-019)). Sono le
inizializzazioni dei sottosistemi, che `mongod` costruisce comunque. Vedere righe `REPL` non
prova che il nodo stia replicando qualcosa.

### 3.3 Il debito, in chiaro

Manca la parte più utile: la sequenza reale di `id`, in ordine, dal battito perso al nuovo
primario, con i tempi misurati fra una riga e l'altra. Non è scritta qui perché non è stata
vista. In `feature/02` verrà provocata un'elezione vera — con il gesto giusto, non con
`docker kill`, che [ADR-0034](../Decision.md#adr-0034) ha dimostrato non essere un guasto — e
questa sezione si riempirà di numeri, come le prime due.

---

## Cosa questa pagina non dice

- **Non dice come si configura la destinazione dei log.** `systemLog.destination`, `syslog`,
  i formati alternativi: fuori perimetro, perché questo lab ha deciso `stdout` una volta per
  tutte ([ADR-0030](../Decision.md#adr-0030)).
- **Non dice come si alza la verbosità.** `setParameter`, `logComponentVerbosity` e i livelli
  `D1`–`D5` esistono e sono lo strumento giusto per una diagnosi difficile, ma nessuno di essi è
  stato usato qui: alzarla senza sapere cosa si cerca produce rumore che nasconde il segnale.
- **Non dice niente sull'audit log.** È una funzione di MongoDB Enterprise; `logRotate` la nomina
  (`"audit"`), il lab non ce l'ha.
- **Non contiene gli `id` di un'elezione.** Vedi il riquadro della
  [sezione 3](#3-cosa-cercare-durante-unelezione).
- **Non dice come si spediscono i log altrove.** Driver di logging di Docker diversi da quello
  predefinito, raccoglitori, indicizzazione: legittimi, e a distanza di sicurezza da un talk che
  deve funzionare senza rete.

---

**Decisioni correlate:** [ADR-0035](../Decision.md#adr-0035) (citare per `id`, e dichiarare cosa non è stato misurato), [ADR-0030](../Decision.md#adr-0030) (i log su `stdout` e il tetto alla loro crescita), [ADR-0005](../Decision.md#adr-0005) (il lab senza autenticazione, che il server segnala a ogni avvio), [ADR-0004](../Decision.md#adr-0004) (il tetto di memoria che genera due delle sei `W`), [ADR-0031](../Decision.md#adr-0031) (lo script di inizializzazione e le sue righe non-JSON), [ADR-0034](../Decision.md#adr-0034) (perché l'elezione non si provoca con `docker kill`).

**Fonti:** [S-042](../Sources.md#s-042), [S-043](../Sources.md#s-043), [S-044](../Sources.md#s-044), [V-010](../Sources.md#v-010), [V-011](../Sources.md#v-011), [V-012](../Sources.md#v-012), [V-017](../Sources.md#v-017), [V-019](../Sources.md#v-019)
