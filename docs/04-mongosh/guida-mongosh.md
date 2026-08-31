# Usare `mongosh`

Su questo portatile `mongosh` **non c'è**:

```console
$ which mongosh
mongosh not found
```

E non serve che ci sia. La shell vive dentro l'immagine, insieme al server e agli strumenti di
backup, nella versione **2.10.0** che accompagna `mongo:7.0.40`:

```console
$ docker exec mongo-standalone sh -c 'command -v mongosh; command -v mongod; command -v mongodump'
/usr/bin/mongosh
/usr/bin/mongod
/usr/bin/mongodump
```

Tutta questa pagina discende da quel fatto ([V-020](../Sources.md#v-020),
[ADR-0036](../Decision.md#adr-0036)). Le guide ufficiali presuppongono `mongosh` installato
accanto al database, e scrivono `mongosh` da solo; qui ogni comando entra nel container. È una
riga più lunga e una versione in meno da tenere allineata.

> **Se `mongosh` ce l'hai sull'host.** La traduzione è meccanica: dove qui si legge
> `docker compose … exec -T mongo-standalone mongosh <argomenti>`, tu scrivi
> `mongosh --host localhost --port 27017 <argomenti>`, e leggi
> [§1.4](#14-localhost-non-e-un-posto) prima di fidarti della parola «localhost». Nel resto della
> pagina questa variante non viene più ripetuta.

---

<a id="1-connettersi"></a>
## 1. Connettersi

<a id="11-la-forma-canonica-del-lab"></a>
### 1.1 La forma canonica del lab

```bash
docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml \
  exec -T mongo-standalone mongosh --quiet --eval "db.adminCommand('ping').ok"
```

Sei pezzi, e nessuno è decorativo.

| pezzo | perché c'è |
| --- | --- |
| `--env-file tools/images.env` | il file Compose pretende `MONGO_IMAGE` e senza questo fallisce **prima** di contattare Docker: `required variable MONGO_IMAGE is missing a value` ([ADR-0026](../Decision.md#adr-0026)) |
| `-f docker/01-standalone/compose.yaml` | il repository ha tre stack; nessuno è «quello predefinito» |
| `exec` | il container è già acceso: `exec` entra, `run` ne creerebbe un secondo |
| `-T` | non alloca un terminale. Non è obbligatorio, ma è esplicito e non costa niente — [§4.5](#45-t-e-it-il-colpevole-non-e-quello-che-si-crede) spiega chi è il vero colpevole degli script che si piantano |
| `mongo-standalone` | il **servizio** dichiarato nel file Compose. Non `mongodb`, non `mongo` |
| `--quiet` | niente preamboli, solo il risultato — [§4.2](#42-quiet-e-gia-acceso-quando-non-ce-un-umano) |

La stessa riga, in forma interattiva, è quella da tenere aperta in una seconda finestra durante
il talk: si toglie `-T`, si toglie `--eval`, e si ottiene un prompt.

```bash
docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml \
  exec mongo-standalone mongosh
```

<a id="12-tre-parametri-che-nessuno-ha-scritto"></a>
### 1.2 Tre parametri che nessuno ha scritto

[S-045](../Sources.md#s-045) dice che «To connect to a MongoDB deployment running on **localhost**
with **default port** 27017, run `mongosh` without any options». Vero, e incompleto: invocato
senza argomenti `mongosh` non usa la stringa vuota, ne costruisce una. Chiedendogli dove sia
andato, risponde:

```text
mongodb://127.0.0.1:27017/?directConnection=true&serverSelectionTimeoutMS=2000&appName=mongosh+2.10.0
```

- `directConnection=true` — parla con **quel nodo**, non con la topologia a cui il nodo
  appartiene. Da `feature/02` in poi è la differenza fra leggere il primario e leggere un
  secondario che risponde qualunque cosa gli si chieda.
- `appName=mongosh 2.10.0` — comparirà nei log del server e in `currentOp`. Utile: distingue le
  tue query da quelle dell'applicazione.
- `serverSelectionTimeoutMS=2000` — **due secondi**, ed è il valore che merita attenzione.

> **La trappola dei due secondi.** [S-044](../Sources.md#s-044) descrive un'elezione che dura fino
> a dodici secondi: «The median time before a cluster elects a new primary should not typically
> exceed 12 seconds». Un `mongosh` invocato senza pensarci contro un replica set che sta
> rieleggendo si arrende **dieci secondi prima** che il cluster abbia finito, e l'errore che
> stampa somiglia a quello di un cluster morto. Nessuna delle pagine consultate nomina questo
> valore predefinito: è stato letto interrogando la shell ([V-020](../Sources.md#v-020)).
>
> Il rimedio è scriverlo, e scriverlo nella **stringa di connessione** — non esiste l'opzione
> `--serverSelectionTimeoutMS` sulla riga di comando, e chi ci prova ottiene
> `MongoshUnimplementedError … unrecognized option`:
>
> ```bash
> mongosh "mongodb://localhost:27017/?serverSelectionTimeoutMS=20000" --quiet --eval "…"
> ```

<a id="13-il-database-predefinito-e-test"></a>
### 1.3 Il database predefinito è `test`

«If unspecified by the connection string, the default database is the `test` database»
([S-045](../Sources.md#s-045)). Misurato:

```console
$ mongosh --quiet --eval "db.getName()"
test
$ mongosh --quiet "mongodb://localhost:27017/lab" --eval "db.getName()"
lab
```

Il dato di questo lab sta in `lab`, e `test` è vuoto. Uno script che dimentica il database
interroga una collezione che non esiste, ottiene zero, e **non fallisce**: si veda
[§4.4](#44-i-codici-di-uscita). Le due forme che evitano l'equivoco sono la stringa di connessione
con il percorso, come sopra, oppure il nome del database come primo argomento posizionale
(`mongosh lab --quiet --eval …`, che è la forma usata da `tools/smoke-standalone.sh`).

Dentro la shell, `use lab` cambia il database, e lo stato sopravvive fra un `--eval` e l'altro:

```console
$ mongosh --quiet --eval "use lab" --eval "db.getName()"
lab
```

<a id="14-localhost-non-e-un-posto"></a>
### 1.4 «localhost» non è un posto

È un punto di vista, e cambia significato tre volte nello stesso stack
([V-018](../Sources.md#v-018)):

| da dove si parla | come si chiama il database |
| --- | --- |
| dentro il container `mongo-standalone` | `localhost`, `127.0.0.1` |
| da un altro container sulla rete Compose | `mongo-standalone` (il nome del servizio) |
| dall'host, grazie alla porta pubblicata | `localhost:27017` |

Sono tre nomi per la stessa istanza, e sbagliarli dà due errori diversi: chi usa il nome del
servizio dall'host ottiene `getaddrinfo ENOTFOUND` — il nome non esiste; chi usa `localhost` da un
altro container ottiene `connect ECONNREFUSED` — il nome esiste, ed è sé stesso. La distinzione
vale la pena di impararla: il primo errore dice «hai sbagliato nome», il secondo dice «hai
sbagliato macchina».

<a id="15-directconnection-e-le-sue-quattro-eccezioni"></a>
### 1.5 `directConnection`, e le sue quattro eccezioni

Da `feature/02` in poi il modo in cui si scrive la stringa decide se si sta parlando con **un
nodo** o con **un replica set**. [S-045](../Sources.md#s-045): «When you specify individual
replica set members in the connection string, `mongosh` automatically adds the
`directConnection=true` parameter, unless at least one of the following is true»:

1. la stringa contiene il parametro `replicaSet`;
2. la stringa usa il formato `mongodb+srv://`;
3. la stringa contiene una seed list con più host;
4. la stringa contiene già `directConnection`.

In pratica: `mongodb://nodo1:27017/` parla con **quel nodo**, anche se è un secondario;
`mongodb://nodo1:27017,nodo2:27017,nodo3:27017/?replicaSet=rs0` parla con **il replica set**, e le
scritture arrivano al primario ovunque esso sia. La prima forma è quella che serve per ispezionare
un nodo caduto; la seconda è quella che serve per lavorare.

Una nota per chi copia esempi da Atlas: «When you use the `+srv` connection string modifier,
MongoDB automatically sets the `--tls` option to `true`» ([S-045](../Sources.md#s-045)). Contro
questo lab, che TLS non ce l'ha ([ADR-0005](../Decision.md#adr-0005)), una stringa `+srv` non
funzionerebbe mai.

---

<a id="2-comandi-di-uso-quotidiano"></a>
## 2. Comandi di uso quotidiano

Tutti eseguiti sullo stack `01-standalone` di questo repository il 2026-08-28. Gli output sono
copiati, non ricostruiti.

<a id="21-orientarsi"></a>
### 2.1 Orientarsi: che cosa c'è qui dentro

```console
$ mongosh --quiet --eval 'show dbs'
admin    40.00 KiB
config  184.00 KiB
lab       2.36 MiB
local    72.00 KiB
```

Tre dei quattro non li ha creati nessuno: `admin` tiene utenti e ruoli, `config` è di servizio
(diventerà interessante nello sharded cluster), `local` contiene l'oplog e non viene replicato.
`lab` è il nostro.

```console
$ mongosh --quiet "mongodb://localhost:27017/lab" --eval 'show collections'
ordini
```

```console
$ mongosh --quiet "mongodb://localhost:27017/lab" --eval 'db.stats(1024*1024)'
{
  db: 'lab',
  collections: Long('1'),
  views: Long('0'),
  objects: Long('50000'),
  avgObjSize: 121.8852,
  dataSize: 5.811939239501953,
  storageSize: 1.84765625,
  indexes: Long('1'),
  indexSize: 0.51171875,
  totalSize: 2.359375,
  scaleFactor: Long('1048576'),
  fsUsedSize: 17924.90625,
  fsTotalSize: 59767.81640625,
  ok: 1
}
```

L'argomento di `db.stats()` è il divisore: `1024*1024` restituisce mebibyte. Il numero da
guardare è il rapporto fra `dataSize` (5,81 MiB, i documenti come li vede l'utente) e
`storageSize` (1,85 MiB, quanto occupano su disco): WiredTiger comprime, e in questo dataset
comprime di **oltre tre volte**. È il motivo per cui stimare lo spazio contando i documenti dà
sempre un numero troppo grande.

<a id="22-interrogare"></a>
### 2.2 Interrogare, e contare

```console
$ mongosh --quiet "mongodb://localhost:27017/lab" --eval 'db.ordini.findOne()'
{
  _id: 0,
  cliente: 'cliente-1279',
  citta: 'Torino',
  stato: 'in lavorazione',
  importo: 4121.44,
  righe: 3,
  data: ISODate('2026-05-24T00:00:00.000Z')
}
```

Due modi di contare, che non sono lo stesso modo:

```console
$ mongosh --quiet "mongodb://localhost:27017/lab" \
    --eval 'print(db.ordini.countDocuments({}) + " / " + db.ordini.estimatedDocumentCount())'
50000 / 50000
```

- `countDocuments({})` **conta davvero**: esegue un'aggregazione, accetta un filtro, ed è esatto
  anche mentre qualcuno scrive.
- `estimatedDocumentCount()` legge i metadati della collezione: è immediato su collezioni enormi,
  non accetta filtri, e dopo un arresto non pulito può essere sbagliato.

Qui coincidono perché il dataset è fermo. Su un cluster sotto carico non coincidono, e la
differenza fra i due numeri è precisamente ciò che si sta pagando per la velocità.

<a id="23-capire-perche-e-lento"></a>
### 2.3 Capire perché è lento: `explain`

```console
$ mongosh --quiet "mongodb://localhost:27017/lab" --eval '
    const e = db.ordini.find({importo: {$gt: 4990}}).explain("executionStats").executionStats;
    print(JSON.stringify({n: e.nReturned, esaminati: e.totalDocsExamined,
                          chiavi: e.totalKeysExamined, ms: e.executionTimeMillis}))'
{"n":107,"esaminati":50000,"chiavi":0,"ms":16}
```

Centosette documenti restituiti, **cinquantamila esaminati**, zero chiavi di indice lette. Il
rapporto fra `totalDocsExamined` e `nReturned` è la diagnosi: 467 a 1 significa scansione
completa. Le chiavi a zero dicono perché — l'unico indice della collezione è quello su `_id`:

```console
$ mongosh --quiet "mongodb://localhost:27017/lab" --eval 'db.ordini.getIndexes()'
[ { v: 2, key: { _id: 1 }, name: '_id_' } ]
```

Su cinquantamila documenti sedici millisecondi non li nota nessuno, ed è esattamente il punto: la
lentezza non si misura col cronometro, si legge in `explain`. Il dataset di demo è tenuto senza
indici aggiuntivi apposta ([ADR-0031](../Decision.md#adr-0031)), perché una scansione completa che
si vede è più istruttiva di una query veloce che non spiega niente.

<a id="24-sapere-con-chi-si-sta-parlando"></a>
### 2.4 Sapere con chi si sta parlando

`db.hello()` è il comando che risponde alla domanda «che cosa sei?», e le sue risposte utili sono
tre campi:

```console
$ mongosh --quiet --eval '
    const h = db.hello();
    print(JSON.stringify({isWritablePrimary: h.isWritablePrimary, msg: h.msg,
                          setName: h.setName, maxBsonObjectSize: h.maxBsonObjectSize}))'
{"isWritablePrimary":true,"maxBsonObjectSize":16777216}
```

`setName` e `msg` **non compaiono**: `JSON.stringify` omette i campi indefiniti, e la loro assenza
è essa stessa l'informazione.

| campo | qui | su un membro di replica set | su un `mongos` |
| --- | --- | --- | --- |
| `isWritablePrimary` | `true` | `true` sul primario, `false` sui secondari | `true` |
| `setName` | assente | il nome del set | assente |
| `msg` | assente | assente | `isdbgrid` |

Tre righe di tabella e si sa sempre dove si è finiti. `maxBsonObjectSize` è il limite di 16 MiB
per documento, che vale ovunque.

<a id="25-lo-stato-del-server"></a>
### 2.5 Lo stato del server, in pillole

`db.serverStatus()` restituisce un documento enorme. Si usa estraendo:

```console
$ mongosh --quiet --eval '
    const s = db.serverStatus();
    print(JSON.stringify({versione: s.version, uptimeSecondi: s.uptime,
                          connessioni: s.connections.current, host: s.host}))'
{"versione":"7.0.40","uptimeSecondi":3471,"connessioni":5,"host":"mongo-standalone"}
```

Cinque connessioni su un'istanza che non serve nessuna applicazione. Non è un errore: è il
controllo di salute di Compose, che ne apre cinque a ogni giro e scrive 139 righe di log al minuto
per dire che va tutto bene ([V-019](../Sources.md#v-019), e
[`03-amministrazione/log.md`](../03-amministrazione/log.md)). Sapere quanto vale il «rumore di
fondo» è la premessa per accorgersi quando il numero sale davvero.

Altri due campi che si guardano spesso: `connections.available` (13102 qui) dice quanto margine
resta prima del rifiuto, e `connections.totalCreated` — 2118 in poco meno di un'ora di vita —
dice quante ne sono state aperte in tutto, cioè se qualcuno le sta riciclando o buttando via.

Le operazioni in corso, senza le inattive:

```console
$ mongosh --quiet --eval '
    print(db.getSiblingDB("admin").aggregate([{$currentOp: {}}]).toArray().length + " operazioni")'
3 operazioni
```

<a id="26-tre-numeri-di-memoria"></a>
### 2.6 Tre numeri di memoria, tre verità diverse

Questa è la misura che sorprende di più:

```console
$ mongosh --quiet --eval '
    const w = db.serverStatus().wiredTiger.cache;
    print("cache max bytes: " + w["maximum bytes configured"])'
cache max bytes: 268435456

$ docker inspect mongo-standalone --format '{{.HostConfig.Memory}}'
1073741824

$ mongosh --quiet --eval 'print(JSON.stringify(db.hostInfo().system.memSizeMB))'
{"high":0,"low":11946,"unsigned":false}
```

| numero | valore | che cos'è davvero |
| --- | ---: | --- |
| cache WiredTiger configurata | 256 MiB | il tetto che abbiamo scritto noi: `--wiredTigerCacheSizeGB 0.25` |
| limite del container | 1024 MiB | `mem_limit` nel file Compose ([ADR-0004](../Decision.md#adr-0004)) |
| `hostInfo().system.memSizeMB` | 11 946 MiB | la memoria della **macchina virtuale Linux** di Docker Desktop |

Il terzo numero non è una misura del container: `hostInfo` legge `/proc/meminfo`, che dentro un
container mostra la memoria dell'host. Un dimensionamento fatto su quel numero pianifica per
dodici gigabyte una cache che ne ha duecentocinquantasei mebibyte. La riga di comando con cui il
server è partito lo dice senza ambiguità:

```console
$ mongosh --quiet --eval 'print(JSON.stringify(db.adminCommand({getCmdLineOpts: 1}).argv))'
["mongod","--wiredTigerCacheSizeGB","0.25","--bind_ip_all"]
```

Il perché di quei due valori, e perché la cache non si lascia calcolare al server, sta in
[`06-sviluppo/gestione-risorse-compose.md`](../06-sviluppo/gestione-risorse-compose.md) e in
[V-009](../Sources.md#v-009).

<a id="27-chiedere-alla-shell"></a>
### 2.7 Chiedere alla shell, invece di cercare su internet

`mongosh --quiet --eval 'help'` stampa una tabella a due colonne larga più di cento caratteri —
qui sotto ci sta solo la prima. Sono le diciannove voci dell'aiuto di primo livello, nell'ordine
in cui escono:

```text
log   use   show   exit   quit   Mongo   connect   it   version   load
enableTelemetry   disableTelemetry   passwordPrompt   sleep   print   printjson
convertShardKeyToHashed   cls   isInteractive
```

Chiude con `For more information on usage: https://mongodb.com/docs/manual/reference/method`.
Le tre da ricordare sono `show log <name>`, che stampa il log della connessione corrente;
`load`, di cui parla [§4.3](#43-file-e-i-percorsi-assoluti); e `it`, che continua a scorrere
l'ultimo risultato quando la shell ha mostrato solo i primi venti documenti.

Ogni oggetto ha il suo: `db.help()`, `db.ordini.help()`, `rs.help()`, `sh.help()`. E il server sa
elencare quello che sa fare:

```console
$ mongosh --quiet --eval 'print(Object.keys(db.adminCommand({listCommands: 1}).commands).length)'
264
```

Duecentosessantaquattro comandi in un `mongod` 7.0.40 senza repliche e senza sharding. Con
`db.adminCommand({listCommands: 1}).commands` in mano si scopre se una funzione esiste **in questa
versione** senza aprire il browser — utile in sala, dove la rete non è garantita.

---

<a id="3-comandi-di-amministrazione"></a>
## 3. Comandi di amministrazione

> **Che cosa di questa sezione è stato eseguito.** [§3.1](#31-quello-che-gira-anche-qui) è stata
> eseguita sullo stack `01-standalone`. [§3.2](#32-replica-set-non-eseguito-qui) e
> [§3.3](#33-sharded-cluster-non-eseguito-qui) **no**: qui non esistono né un replica set né uno
> sharded cluster, e gli unici output riportati sono i due errori che quei comandi restituiscono
> su un'istanza singola — quelli sì, misurati. La verifica del resto è dovuta a
> `feature/02-stack-replicaset` e `feature/03-stack-sharded`
> ([ADR-0036](../Decision.md#adr-0036), stessa regola di [ADR-0035](../Decision.md#adr-0035)).
> La sezione si scrive completa adesso perché la guida è una sola; si marca perché una guida che
> afferma cose non provate è peggio di una guida incompleta ([ADR-0024](../Decision.md#adr-0024)).

<a id="31-quello-che-gira-anche-qui"></a>
### 3.1 Quello che gira anche su un'istanza singola

**Il profiler.** Registra le operazioni lente in `system.profile`, una collezione capped dentro il
database osservato.

```console
$ mongosh --quiet "mongodb://localhost:27017/lab" --eval 'print(JSON.stringify(db.getProfilingStatus()))'
{"was":0,"slowms":100,"sampleRate":1,"ok":1}
```

`was: 0` significa spento — è il valore predefinito. I tre livelli sono `0` (spento), `1` (solo le
operazioni oltre `slowms`), `2` (tutte). Si accende con
`db.setProfilingLevel(1, { slowms: 50 })` e si spegne con `db.setProfilingLevel(0)`. Attenzione a
due cose: il livello `2` su un sistema carico scrive moltissimo, e il profiler **è per database**,
non per istanza.

**Le operazioni in corso, e come fermarle.** `db.currentOp()` elenca; `db.killOp(<opid>)` termina.
Su un'istanza in salute la lista è corta ([§2.5](#25-lo-stato-del-server)); durante la demo di
carico sarà il modo per far vedere che cosa sta succedendo davvero.

**Il log dalla shell.** `db.adminCommand({getLog: "global"})` restituisce il buffer in memoria,
non il file:

```console
$ mongosh --quiet --eval 'print(db.adminCommand({getLog: "global"}).totalLinesWritten + " righe")'
9839 righe
```

Il buffer è limitato e viene svuotato dai riavvii. La variante che conta il giorno del talk è
`getLog: "startupWarnings"`, e la rotazione dei log in container è un argomento con una risposta
non ovvia: entrambe stanno in
[`03-amministrazione/log.md`](../03-amministrazione/log.md#2-logrotate-e-perché-in-container-non-serve).

**Le statistiche di una collezione.**

```console
$ mongosh --quiet "mongodb://localhost:27017/lab" --eval '
    const s = db.ordini.stats();
    print(JSON.stringify({count: s.count, size: s.size, storageSize: s.storageSize, nindexes: s.nindexes}))'
{"count":50000,"size":6094260,"storageSize":1937408,"nindexes":1}
```

<a id="32-replica-set-non-eseguito-qui"></a>
### 3.2 Replica set — **non eseguito su questo branch**

Quello che succede se ci si prova qui, misurato:

```console
$ mongosh --quiet --eval 'try { rs.status() } catch (e) { print(e.codeName + ": " + e.message) }'
NoReplicationEnabled: not running with --replSet
```

L'errore è preciso e vale la pena riconoscerlo: non dice «comando sconosciuto», dice che
*questo* processo non è stato avviato per replicare. I comandi che serviranno in `feature/02`:

| comando | a che cosa serve |
| --- | --- |
| `rs.initiate(<config>)` | crea il replica set. Si esegue **una volta sola**, su **un solo** nodo |
| `rs.status()` | stato di ogni membro: `stateStr`, ritardo di replica, ultimo battito |
| `rs.conf()` | la configurazione corrente, con priorità e voti |
| `rs.add("nodo:27017")` / `rs.remove(…)` | aggiunge o toglie un membro |
| `rs.reconfig(<config>)` | cambia la configurazione: si legge con `rs.conf()`, si modifica, si riscrive |
| `rs.stepDown(<secondi>)` | il primario si dimette e provoca un'elezione — è il modo **pulito** di mostrare un failover |
| `rs.printSecondaryReplicationInfo()` | il ritardo dei secondari, in forma leggibile |
| `db.getMongo().setReadPref("secondaryPreferred")` | manda le letture ai secondari |

Due avvertenze che si possono già dare, perché vengono dalle fonti e non dalla prova:

- **Un secondario non risponde alle letture finché non glielo si dice.** Con
  `directConnection=true` ([§1.5](#15-directconnection-e-le-sue-quattro-eccezioni)) si finisce su
  un nodo che rifiuta le query fino a `db.getMongo().setReadPref(…)`.
- **Durante l'elezione non si scrive.** [S-044](../Sources.md#s-044): «The replica set cannot
  process write operations until the election completes successfully». Con i due secondi di
  [§1.2](#12-tre-parametri-che-nessuno-ha-scritto) e i dodici dell'elezione, una `mongosh`
  distratta dichiara morto un cluster che sta solo cambiando primario.

Perché il failover del talk si provoca con `rs.stepDown()` o con `docker stop`, e non con
`docker kill`, sta in [ADR-0034](../Decision.md#adr-0034).

<a id="33-sharded-cluster-non-eseguito-qui"></a>
### 3.3 Sharded cluster — **non eseguito su questo branch**

Anche qui l'errore misurato è istruttivo:

```console
$ mongosh --quiet --eval 'sh.status()'
Warning: MongoshWarning: [SHAPI-10003] You are not connected to a mongos. This command may not work as expected.
MongoshInvalidInputError: [SHAPI-10003] This db does not have sharding enabled. Be sure you are connecting to a mongos from the shell and not to a mongod.
```

«Be sure you are connecting to a mongos from the shell and not to a mongod»: è l'errore che si
prende chiunque apra la shell sulla porta di uno shard invece che su quella del router. Il
riconoscimento rapido è quello di [§2.4](#24-sapere-con-chi-si-sta-parlando) — `db.hello().msg`
vale `isdbgrid` solo su un `mongos`.

I comandi che serviranno in `feature/03`:

| comando | a che cosa serve |
| --- | --- |
| `sh.status()` | shard, database, collezioni distribuite, stato del bilanciatore |
| `sh.enableSharding("lab")` | abilita lo sharding su un database |
| `sh.shardCollection("lab.ordini", { <chiave> })` | distribuisce una collezione; la scelta della chiave è la decisione irreversibile |
| `sh.addShard("rs-shard-1/nodo:27017")` | aggiunge uno shard al cluster |
| `sh.getBalancerState()` / `sh.startBalancer()` / `sh.stopBalancer()` | il bilanciatore, che sposta i chunk |
| `db.collection.getShardDistribution()` | quanto è distribuita davvero una collezione |

L'architettura di questi componenti — router, config server, shard — sta in
[`02-architetture/standalone.md`](../02-architetture/standalone.md) e nelle pagine che
`feature/02` e `feature/03` aggiungeranno; qui interessa solo che i comandi si danno **al
`mongos`**, e che dare `sh.status()` a un `mongod` produce esattamente l'errore qui sopra.

---

<a id="4-script-non-interattivi"></a>
## 4. Script non interattivi

È la forma che usa questo repository: gli healthcheck, `make seed-01`,
`tools/smoke-standalone.sh`. Tutto questo capitolo è misurato in
[V-020](../Sources.md#v-020).

<a id="41-eval-e-la-regola-dellultimo"></a>
### 4.1 `--eval`, e la regola dell'ultimo

Si può ripetere: «You can use a single `--eval` argument or multiple `--eval` arguments together»
([S-046](../Sources.md#s-046)). Ma la stampa segue una regola che sorprende: «If you use multiple
`--eval` statements, `mongosh` only prints the results of the last `--eval`». Misurato:

| comando | stampa |
| --- | --- |
| `--eval "1 + 1" --eval "2 + 2"` | `4` |
| `--eval "print('uno')" --eval "print('due')" --eval "3 + 3"` | `uno`, `due`, `6` |
| `--eval "use lab" --eval "db.getName()"` | `lab` |

Due conseguenze pratiche. La prima: se vuoi vedere i risultati intermedi devi chiedere `print()`,
altrimenti ottieni **silenzio, non un errore**. La seconda: lo stato attraversa i frammenti — il
`use lab` del primo `--eval` vale ancora nel secondo.

<a id="42-quiet-e-gia-acceso-quando-non-ce-un-umano"></a>
### 4.2 `--quiet` è già acceso, quando non c'è un umano

«For non-interactive shell sessions, MongoDB enables `--quiet` by default»
([S-046](../Sources.md#s-046)), e `--no-quiet` serve a **ri**accendere il preambolo, non a
spegnerlo. Misurato:

| invocazione | prima riga stampata |
| --- | --- |
| `mongosh --eval "1 + 1"` | `2` |
| `mongosh --quiet --eval "1 + 1"` | `2` |
| `mongosh --no-quiet --eval "1 + 1"` | `Current Mongosh Log ID: …` (sei righe di intestazione) |

`--quiet` si scrive lo stesso, e la ragione è in [ADR-0036](../Decision.md#adr-0036): la fonte non
definisce che cosa sia una sessione «non interattiva», e la stessa riga di comando in questo lab
finisce ora dentro uno script, ora incollata in un terminale. Scriverlo rende l'output
indipendente da quella distinzione.

Due opzioni che rendono uno script ripetibile su macchine altrui: `--norc` («Prevents the shell
from sourcing and evaluating `~/.mongoshrc.js` on startup») e `--nodb`, che avvia la shell senza
collegarsi a niente. E se l'output deve essere letto da un programma, `--json` produce Extended
JSON: «`mongosh` supports both `--json=canonical` and `--json=relaxed` modes».

<a id="43-file-e-i-percorsi-assoluti"></a>
### 4.3 `--file`, e i percorsi assoluti

Per i file c'è un modo solo, e la fonte lo mette in grassetto: «To pass filenames always use
`--file` or `-f`» ([S-047](../Sources.md#s-047)). L'opzione si ripete, e i file girano in ordine.

`load()` invece non cerca da nessuna parte: «There is no search path for the `load()` method. If
the target script is not in the current working directory or the full specified path, the MongoDB
Shell cannot access the file». Dentro un container questa frase ha un peso particolare, perché la
directory di lavoro non è quella da cui hai digitato il comando. Misurato, con lo script in
`/tmp/controllo.js` e la directory di lavoro in `/etc`:

```console
$ mongosh --quiet --eval 'load("controllo.js")'
Error: ENOENT: no such file or directory, open '/etc/controllo.js'
    rc = 1
$ mongosh --quiet --eval 'load("/tmp/controllo.js")'
ordini: 50000
    rc = 0
```

**Niente script per pipe.** `mongosh` legge lo standard input come una sessione interattiva e ci
stampa sopra i suoi prompt:

```console
$ echo 'print("dallo standard input: " + …)' | docker compose exec -T mongo-standalone mongosh --quiet
test> dallo standard input: 50000

test>
```

Il risultato c'è, annegato fra due `test>`. E `--file -` non è la scorciatoia che sembra:
`mongosh` cerca un file chiamato `-` e fallisce con `ENOENT: … open '/-'`. Gli unici due modi
puliti restano `--eval` e `--file <percorso assoluto>`; per portare un file dentro il container
c'è `docker cp`, oppure — meglio — un montaggio dichiarato nel file Compose.

<a id="44-i-codici-di-uscita"></a>
### 4.4 I codici di uscita

Nessuna pagina della documentazione di `mongosh` contiene questa tabella
([S-046](../Sources.md#s-046), [S-047](../Sources.md#s-047)). È stata misurata su quindici casi
([V-020](../Sources.md#v-020)):

| situazione | codice |
| --- | ---: |
| espressione valutata senza errori | **0** |
| `countDocuments` che non trova nulla (restituisce `0`) | **0** |
| `throw new Error("rotto")` non catturato | **1** |
| `TypeError` — metodo che non esiste | **1** |
| `ReferenceError` — identificatore non definito | **1** |
| `MongoServerError` — `no such command` | **1** |
| `MongoServerError` — `E11000 duplicate key error` | **1** |
| `MongoNetworkError` — `getaddrinfo ENOTFOUND` | **1** |
| `MongoNetworkError` — `connect ECONNREFUSED` | **1** |
| `--file` su un percorso che non esiste | **1** |
| `exit(3)` | **3** |
| `quit(7)` | **7** |
| `exit(300)` | **44** |
| `exit(-1)` | **255** |

Tre conclusioni, e sono tutte scomode.

1. **Ogni errore vale `1`.** Dal codice di uscita non si distingue «il server ha risposto di no»
   da «il server non l'ho trovato». Chi deve distinguere legge `stderr`, oppure cattura
   l'eccezione e sceglie un codice suo.
2. **Il silenzio vale `0`.** Una ricerca che non trova niente termina con successo. Uno script di
   verifica che si limiti a interrogare, e che giudichi dal codice di uscita, **dichiara sano un
   database vuoto**. È la stessa trappola di `logRotate` che risponde `ok: 1` senza ruotare
   niente ([V-010](../Sources.md#v-010)): l'operazione riesce, il fatto non avviene.
3. **Il codice scelto non è sempre il codice consegnato.** `exit(300)` arriva al chiamante come 44
   (300 modulo 256) ed `exit(-1)` come 255. Restare fra 1 e 125 evita anche la sovrapposizione con
   i codici che le shell si riservano.

Il rimedio è quello raccomandato dalla fonte: «As a best practice, wrap code in a `try - catch`,
calling the `exit` method in the `catch` block. Likewise, to check the results of a query or any
command, you can add an `if - else` statement and call the `exit` method if the results are not
what is expected» ([S-047](../Sources.md#s-047)). In pratica:

```javascript
// controllo.js — si esegue con: mongosh --quiet --file /tmp/controllo.js
try {
  const lab = db.getSiblingDB("lab");
  const n = lab.ordini.countDocuments();
  if (n !== 50000) {
    print(`atteso 50000, trovato ${n}`);
    exit(4);           // 4 = il dato non è quello che ci aspettavamo
  }
  print(`ordini: ${n}`);
} catch (e) {
  print(`errore: ${e.message}`);
  exit(5);             // 5 = non siamo riusciti nemmeno a chiedere
}
```

Quattro e cinque non hanno alcun significato convenzionale: significano quello che dice il
commento accanto. È il punto — il significato lo dà chi scrive, non `mongosh`.

<a id="45-t-e-it-il-colpevole-non-e-quello-che-si-crede"></a>
### 4.5 `-T` e `-it`: il colpevole non è quello che si crede

Circola la convinzione che gli script si piantino perché manca `-T`. Misurato:

| comando | stdin | esito |
| --- | --- | --- |
| `docker compose exec mongo-standalone mongosh …` | `/dev/null` | `2`, codice 0 |
| `docker compose exec mongo-standalone mongosh …` | **chiuso** | `2`, codice 0 |
| `docker compose exec -T mongo-standalone mongosh …` | chiuso | `2`, codice 0 |
| `docker exec -it mongo-standalone mongosh …` | `/dev/null` | **fallisce**, codice 1 |

L'ultima riga stampa `cannot attach stdin to a TTY-enabled container because stdin is not a
terminal`. Non è l'assenza di `-T` a rompere gli script: è la **presenza di `-it`**, l'abitudine
copiata da mille esempi interattivi. `docker compose exec` da solo si arrangia; `-T` resta la
scelta giusta perché è esplicito, ma sapere chi è il colpevole vero fa risparmiare mezz'ora la
prima volta che una pipeline si blocca.

<a id="46-come-lo-fa-questo-repository"></a>
### 4.6 Come lo fa questo repository

`tools/smoke-standalone.sh` è la sezione precedente messa in pratica. La sua funzione di
interrogazione:

```bash
interroga() {
  compose exec -T "${SERVIZIO}" mongosh lab --quiet --eval "$1" 2>/dev/null | tail -1 | tr -d '\r'
}
```

`-T` esplicito; il database come argomento posizionale, così nessuna query finisce su `test`;
`--quiet` scritto anche se implicito; `tail -1` perché conta l'ultima riga; `tr -d '\r'` perché
un ritorno a capo invisibile fa fallire un confronto di stringhe e non si vede nel messaggio
d'errore.

E soprattutto: lo script **non guarda il codice di uscita**, confronta i valori.

```bash
DOCUMENTI_ATTESI=50000
IMPORTO_ATTESO="124861860.70"
RIGHE_ATTESE=150281
```

Tre numeri attesi, misurati una volta ([V-013](../Sources.md#v-013)) e confrontati a ogni giro. È
l'unica forma di verifica che sopravvive alla regola del §4.4: se il database fosse vuoto,
`mongosh` uscirebbe con zero e lo script direbbe ugualmente di no.

---

## Cosa questa pagina non dice

- **Non parla di autenticazione.** In questo lab non c'è
  ([ADR-0005](../Decision.md#adr-0005)), quindi nessun `--username`, `--authenticationDatabase`,
  `db.createUser()`. È la lacuna più grande e la più deliberata: farla vedere richiederebbe metà
  del talk, e mostrarla male sarebbe peggio che non mostrarla.
- **Non è un manuale del linguaggio.** L'aggregation framework, gli operatori di query, gli indici
  composti: c'è la documentazione ufficiale, e non è quello che il pubblico viene a vedere.
- **Non copre gli strumenti di backup.** `mongodump`, `mongorestore` e `mongoexport` stanno nella
  stessa immagine ma non sono `mongosh`: sono materia di `feature/04`, insieme al backup a caldo.
- **Non copre il driver Python.** L'applicazione della demo non userà `mongosh`: userà `pymongo`,
  con altre regole e altri valori predefiniti — a partire, presumibilmente, da un
  `serverSelectionTimeoutMS` diverso da due secondi.
- **Non ha eseguito `rs.*` né `sh.*`.** Vale la riserva dichiarata all'inizio della
  [sezione 3](#3-comandi-di-amministrazione).

---

**Decisioni correlate:** [ADR-0036](../Decision.md#adr-0036) (`mongosh` dentro il container, e la
diffidenza verso il codice di uscita), [ADR-0035](../Decision.md#adr-0035) (dichiarare che cosa
non è stato misurato), [ADR-0024](../Decision.md#adr-0024) (la gerarchia delle fonti),
[ADR-0031](../Decision.md#adr-0031) (il dataset deterministico e la sua impronta),
[ADR-0004](../Decision.md#adr-0004) (i limiti di memoria che spiegano i tre numeri di §2.6),
[ADR-0005](../Decision.md#adr-0005) (il lab senza autenticazione),
[ADR-0026](../Decision.md#adr-0026) (le immagini pinnate e `--env-file`),
[ADR-0034](../Decision.md#adr-0034) (come si provoca un failover).

**Fonti:** [S-044](../Sources.md#s-044), [S-045](../Sources.md#s-045), [S-046](../Sources.md#s-046), [S-047](../Sources.md#s-047), [V-009](../Sources.md#v-009), [V-010](../Sources.md#v-010), [V-013](../Sources.md#v-013), [V-018](../Sources.md#v-018), [V-019](../Sources.md#v-019), [V-020](../Sources.md#v-020)
