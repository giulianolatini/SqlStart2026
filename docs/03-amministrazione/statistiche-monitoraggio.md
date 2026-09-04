# Statistiche e monitoraggio

Questa pagina non è l'elenco dei campi di `serverStatus`. Quell'elenco esiste, è il manuale, ed è
più completo di qualunque cosa si possa riscrivere qui. Questa pagina risponde a un'altra domanda,
che il manuale non pone: **quale numero guardare, e quale numero non credere.**

Le sei sezioni che seguono nascono ciascuna da una misura in cui la lettura istintiva di una
metrica risultava sbagliata. Non sbagliata di poco: sbagliata di segno, o di un fattore quaranta, o
allarmante proprio quando tutto funziona. Sono i casi che valgono la pena di essere scritti, perché
sono quelli in cui chi guarda un cruscotto conclude il contrario di quello che sta succedendo.

> **Cosa è stato misurato, e su quale stack.** Tutti i numeri di questa pagina vengono da corse
> eseguite il 4 settembre 2026 sui tre stack del lab accesi insieme, MongoDB 7.0.40, con il
> generatore di carico dell'applicazione `mongolab` ([`app/docs/`](../../app/docs/README.md)). Le
> misure stanno in [V-082](../Sources.md#v-082) … [V-087](../Sources.md#v-087) e in
> [V-079](../Sources.md#v-079); la decisione su come questa pagina è organizzata è
> [ADR-0112](../Decision.md#adr-0112). Su un ambiente diverso i valori assoluti vanno rifatti, non
> ricopiati: quello che si trasferisce sono i **rapporti** e le **relazioni fra metriche**.

---

<a id="1-serverstatus-non-e-una-domanda-sola"></a>
## 1. `serverStatus` non è una domanda sola

### 1.1 Tre nodi, tre risposte diverse

Lo stesso comando, sui tre stack del lab, non restituisce lo stesso documento
([V-082](../Sources.md#v-082)):

| nodo | sezioni di primo livello | dimensione della risposta |
|---|---|---|
| `mongo-standalone` | **45** | 73 614 byte |
| `mongo-rs-1` (primario) | **52** | 75 865 byte |
| `sh-mongos` (router) | **36** | **26 445 byte** |

Le sezioni comuni a tutti e tre sono **28**. Fra standalone e replica set la differenza è
rassicurante: le 45 dello standalone ci sono tutte, e se ne aggiungono sette — `repl`,
`oplogTruncation`, `readPreferenceCounters`, `defaultRWConcern`, `queryAnalyzers`, `$clusterTime`,
`operationTime`. Passare dallo stack 01 al 02 non toglie niente a chi guardava.

Passare al router sì.

### 1.2 Al `mongos` mancano venti sezioni, e non lo dice

Rispetto al primario, il router non ha:

```
batchedDeletes        catalogStats            electionMetrics      featureCompatibilityVersion
flowControl           globalLock              indexBuilds          indexStats
locks                 opcountersRepl          oplogTruncation      profiler
readConcernCounters   readPreferenceCounters  repl                 shardSplits
storageEngine         tenantMigrations        twoPhaseCommitCoordinator
wiredTiger
```

e in cambio ne ha quattro sue: `health`, `hedgingMetrics`, `sharding`, `shardingStatistics`.

Guardate l'elenco delle venti con l'occhio di chi scrive uno script di monitoraggio. `wiredTiger`
per la cache e i ticket. `globalLock` per le code. `locks` per la contesa. `repl` e
`opcountersRepl` per la replica. **Sono esattamente le sezioni su cui si appoggia qualunque ricetta
scritta per un `mongod`**, ed è per questo che il caso merita una sezione invece di una nota.

Il modo in cui questo fallisce è il peggiore possibile: `serverStatus` risponde `ok: 1`. Non c'è
errore, non c'è avviso, non c'è codice di ritorno diverso. Le chiavi semplicemente non ci sono, e
lo script se ne accorge tre righe dopo, sotto forma di `undefined`, oppure — se somma — sotto forma
di uno zero perfettamente plausibile. Un cruscotto che mostra «ticket disponibili: 0» su un router
non sta segnalando una saturazione: sta leggendo una sezione che non esiste.

La lezione generale, che vale oltre MongoDB: **una metrica va sempre dichiarata insieme al nodo su
cui si legge.** «Guarda `wiredTiger.cache`» non è un'istruzione completa; «guarda
`wiredTiger.cache` su ogni `mongod`, e sui `mongos` non cercarla» lo è.

> La risposta del router pesa 26 445 byte contro i 73 614 dello standalone: poco più di un terzo.
> Non è solo il numero di sezioni, è la loro profondità. Ciò che manca è la descrizione di un
> motore di archiviazione che il router non ha, perché **un `mongos` non archivia niente**.

---

<a id="2-cosa-guardare-sotto-carico"></a>
## 2. Cosa guardare sotto carico

Il carico di riferimento di questa sezione è lo stesso di
[V-079](../Sources.md#v-079): 30 secondi, otto scrittori e quattro lettori, documenti da 2 KB.

```
make app-workload TARGET=standalone \
  ARGS="--duration 30 --doc-size 2k --writers 8 --readers 4 --sink null"
```

Mentre gira, `serverStatus` viene campionato una volta al secondo per 45 secondi da una sessione
`mongosh` aperta prima e chiusa dopo. Un dettaglio di metodo che vale la pena rubare: **il
campionatore sta dentro una sola sessione.** Un `docker exec` per campione costerebbe mezzo secondo
di orologio a giro e falserebbe la cadenza che si sta cercando di misurare.

### 2.1 Le code: la prima cosa che si guarda, e qui non si è mai formata

| metrica | corsa A | corsa B |
|---|---|---|
| inserimenti/s medi | 1 408 | **1 689** |
| `globalLock.currentQueue.writers` | **0** in tutti i campioni | **0** in tutti i campioni |
| `globalLock.currentQueue.readers` | **0** in tutti i campioni | **0** in tutti i campioni |
| `wiredTiger.concurrentTransactions.write.queueLength` | **0** in tutti i campioni | **0** in tutti i campioni |
| `totalTimeQueuedMicros`, accumulato sui 45 s | **0 µs** | **9 840 µs** |

Nella corsa B il server ha accumulato **9,8 millisecondi** di attesa per un ticket. In totale.
Distribuiti su 50 664 scritture fanno 0,19 microsecondi a scrittura. Nella corsa A, zero
([V-083](../Sources.md#v-083)).

Le tre metriche che si guardano per prime quando qualcuno dice «il database è lento» dicono
all'unisono che il collo di bottiglia **non era nel database**. È la conferma, dal lato del server,
di quello che [V-079](../Sources.md#v-079) aveva concluso dal lato del client: in quel lab il
numero era del client, che satura la propria CPU prima che il server saturi la sua.

Vale la pena fermarsi su come questa conclusione è stata raggiunta, perché è il metodo, non il
numero. `queueLength` campionato al secondo **non può** escludere una coda che si forma e si
smaltisce fra due campioni. `totalTimeQueuedMicros` sì, perché è cumulativo: qualunque attesa,
anche di un microsecondo, ci finisce dentro e non ne esce. **Quando una metrica istantanea e una
cumulativa dicono la stessa cosa, quella che sta parlando è la cumulativa.**

### 2.2 La latenza che il server dichiara non è quella che l'utente aspetta

Sulla stessa corsa:

- `opLatencies.writes`, lato server: **67 µs** di media.
- p50 misurato dal client: **2,8 ms** ([V-079](../Sources.md#v-079)).

Un fattore quaranta. I due numeri non sono in disaccordo, e nessuno dei due è sbagliato: misurano
**tratti diversi dello stesso percorso**. `opLatencies` conta il tempo passato dentro il comando;
il client conta anche la serializzazione BSON, il socket, l'attraversamento della rete Compose e il
ritorno.

Detto in modo utile: **guardare solo `opLatencies` su uno standalone significa non vedere il 97 %
del tempo che l'utente aspetta.**

E qui arriva la parte che rende la sezione necessaria. La stessa metrica, sul primario di un
replica set sotto lo stesso carico, vale **18 390 µs** — un fattore 274 rispetto ai 67 µs dello
standalone, mentre il rapporto di resa fra le due architetture è 6,2×. La differenza non è che il
replica set sia 274 volte più lento: è che sul primario **la durata del comando comprende l'attesa
della conferma di maggioranza**, che sullo standalone non esiste. Sul replica set il numero del
server e quello del client sono dello stesso ordine (p50 9,0 ms); sullo standalone no.

> **`opLatencies.writes` non è una metrica che diventa più grande quando l'architettura cambia. È
> una metrica che cambia significato.** Sullo standalone misura il lavoro locale; sul primario
> misura il lavoro locale più l'attesa della rete. Confrontare i due valori fra architetture è un
> confronto fra due grandezze diverse con lo stesso nome.
>
> Questa lettura è coerente con i numeri ma **non è stata isolata**: la prova che la chiuderebbe è
> la stessa corsa con `w: 1` sul replica set, ed è dichiarata fra le riserve di
> [V-083](../Sources.md#v-083).

### 2.3 I ticket di scrittura non sono 128, e non stanno fermi

Il numero 128 circola come se fosse una costante di WiredTiger. Misurato, dentro i container di
questo lab ([V-083](../Sources.md#v-083)):

```
standalone, corsa A:   totalTickets  12 → 11
standalone, corsa B:   totalTickets   9 →  8
primario del rs:       totalTickets   8 →  7
```

Nella 7.0 il pool è governato da un controllore che lo dimensiona da solo in base a quello che
osserva, e in questi container si è assestato **fra 7 e 12**, muovendosi durante la corsa. Non c'è
niente di rotto: è il comportamento previsto di un pool adattivo su un `mongod` con una CPU e un
gigabyte.

La conseguenza pratica è un allarme da non scrivere. «Avvisa se `available` scende sotto N» mette a
confronto una misura viva con una costante che non vale più, e produrrà falsi positivi ogni volta
che il controllore restringe il pool — cioè, tipicamente, quando il server sta lavorando bene. Il
numero che risponde alla domanda «qualcuno sta aspettando?» è **`queueLength`**, ed è zero anche
mentre il pool si restringe.

### 2.4 Il resto del quadro, per completezza

| metrica | corsa A | corsa B |
|---|---|---|
| cache WiredTiger | 191 → 207 MiB | 188 → 206 MiB |
| dirty massimo | 9,2 MiB | 8,9 MiB |
| `mem.resident` | 462–463 MB | 461–462 MB |
| connessioni create nei 45 s | 35 | 36 |

Su un `mem_limit` di 1024 MB, la cache si assesta poco sopra i 200 MiB e il residente non si muove.
Il dirty non supera i 9 MiB: la scrittura su disco tiene il passo senza accumulo. Nessuno di questi
numeri è drammatico, ed è proprio questo il punto — **il quadro completo di un server che non è il
collo di bottiglia**, da tenere accanto per riconoscerlo quando lo si vede.

---

<a id="3-le-metriche-di-replica"></a>
## 3. Le metriche di replica, e quella da non mostrare

### 3.1 Il ritardo di replica, letto nel modo standard, è inutilizzabile qui

Questa è la sezione per cui la pagina è stata organizzata come è organizzata. Il ritardo di replica
è la metrica più citata di un replica set, e su questo lab **non si può mostrare**.

Il calcolo standard — quello che fa `rs.printSecondaryReplicationInfo()` — è la differenza fra
l'`optimeDate` del primario e quella di ciascun membro. Campionata al secondo per 45 secondi su un
insieme sano, durante e attorno al carico, dà questa serie, in millisecondi
([V-084](../Sources.md#v-084)):

```
0, 10000, 10000, 0, 0, 0, 0, 1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000,
1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000, 1000,
2000, 1000, 0, 1000, 0, 0, 0, 0, 0, 0, 0, 0, 0
```

Tre cose, in una riga di numeri.

**Primo: non esistono valori intermedi.** Solo 0, 1000, 2000. Non è un caso e non è
arrotondamento del campionatore: `optimeDate` ha granularità di **un secondo**, quindi la
differenza fra due di esse è per costruzione un multiplo di mille millisecondi. Il ritardo vero di
questo lab, misurato con un metodo diretto, è **≈ 1,6 ms** ([V-027](../Sources.md#v-027)): un
valore che questa metrica **non è in grado di rappresentare**. Chi la guarda non vede 1,6 ms
arrotondati male — vede zero, oppure mille.

**Secondo: i due campioni da 10 000 ms sono a riposo.** Prima che il carico partisse, su un insieme
perfettamente sano, con i secondari allineati. Senza scritture l'optime del primario non avanza: il
primario ha scritto dieci secondi fa, il secondario ha applicato tutto, e la sottrazione dice
«dieci secondi indietro». **Il valore più allarmante di tutta la serie è quello dello stato
migliore.**

**Terzo: sotto carico oscilla fra 1 000 e 2 000 con la regolarità di un metronomo.** Perché la
vista che il primario ha degli altri membri non è diretta: arriva dagli heartbeat, che sono ogni
2 000 ms ([V-031](../Sources.md#v-031)). Si sta guardando un dato vecchio fino a due secondi,
arrotondato al secondo.

### 3.2 Dal secondario lo stesso conto è negativo

Ventidue campioni su 45, letti da `mongo-rs-2`, danno **−1 000 ms**; uno dà **−10 000 ms**.

Un ritardo negativo non è un errore da segnalare. È la prova che i due termini della sottrazione
**non sono contemporanei**: il secondario conosce il proprio optime adesso e quello del primario
dall'ultimo heartbeat, quindi quando applica in fretta il suo optime è più recente di quello che
crede sia del primario.

Chi scrive un allarme su questa metrica deve quindi decidere **da quale nodo la legge** — e
scoprire che la risposta cambia segno a seconda della scelta è il modo più diretto di capire che la
metrica non misura quello che sembra.

### 3.3 Che cosa guardare invece

Sul secondario, durante i 30 secondi di carico ([V-084](../Sources.md#v-084)):

| metrica | valore | che cosa risponde |
|---|---|---|
| `opcountersRepl.insert` | **+9 139** | **identico** agli inserimenti confermati al client |
| `metrics.repl.buffer.count`, massimo | **3** | quanto arretrato ha accumulato: nessuno |
| `metrics.repl.buffer.sizeBytes`, massimo | 7 023 | sette kilobyte |
| `metrics.repl.apply.batches.num` | +6 501 | ≈ 217 lotti al secondo |
| `metrics.repl.apply.ops` | +18 280 | 2,8 operazioni per lotto |

La prima riga è la risposta alla domanda che si voleva porre. `opcountersRepl.insert` sul secondario
coincide **esattamente** con il numero di scritture che il client si è visto confermare: 9 139 =
9 139. Non dipende da nessun orologio, non dipende dagli heartbeat, non ha granularità. Se questo
numero segue quello del primario, il secondario sta applicando tutto.

La seconda e la terza rispondono a «e ce la sta facendo?». `metrics.repl.buffer` è la coda vera del
percorso di replica: le operazioni ricevute e non ancora applicate. Non ha mai contenuto più di
**tre** operazioni, per un totale di sette kilobyte. Il secondario non era in ritardo di niente — e
nessuna metrica temporale sapeva dirlo.

> **Una cautela sul primario.** `metrics.repl.apply.batches.num` sul primario ha delta **zero** in
> tutti i campioni, pur avendo un valore cumulativo non nullo: l'eredità di quando quel nodo era
> secondario. Il valore assoluto **non dice il ruolo**; solo il delta lo dice. Su un cruscotto che
> mostra il totale, un primario e un secondario si somigliano.

### 3.4 Perché `apply.ops` vale il doppio: le scritture ripetibili

Nella tabella qui sopra c'è un numero che non torna: 18 280 operazioni applicate per 9 139
inserimenti. Esattamente il doppio.

La spiegazione non stava nel database. Tre prove in scala decrescente hanno ristretto il campo — un
`insertMany` controllato da 100 documenti non riproduce il raddoppio, una corsa concorrente da 800
sì — fino a una coppia decisiva, a parità di tutto il resto ([V-085](../Sources.md#v-085)):

| corsa | `apply.ops` | `opcountersRepl.insert` | `opcountersRepl.update` |
|---|---|---|---|
| `--no-retry-writes` | **+802** | +800 | **+0** |
| `--retry-writes` | **+1 603** | +800 | **+800** |

Ogni scrittura ripetibile scrive un record di sessione in `config.transactions`, e **quel record si
replica come un `update`**. Ottocento inserimenti diventano milleseicento operazioni sul secondario.

È il prezzo, in lavoro replicato, di una garanzia che il driver attiva **per impostazione
predefinita** — la stessa garanzia che [V-076](../Sources.md#v-076) ha misurato spegnendola durante
un failover vero, e che si è rivelata la ragione per cui un guasto risultava quasi invisibile.

Per chi guarda un cruscotto: **`apply.ops` non è il numero di documenti che stanno arrivando al
secondario.** Leggerlo così porta a credere che il carico sia il doppio di quello che è. Il numero
che risponde alla domanda vera resta `opcountersRepl.insert`.

---

<a id="4-il-router-cosa-sa-dire-e-cosa-inventa"></a>
## 4. Il router: cosa sa dire, e cosa inventa

### 4.1 I contatori del router sono quelli del client, alla singola operazione

Stessa corsa di carico, contro `sh-mongos`, con `opcounters` letti prima e dopo
([V-086](../Sources.md#v-086)):

| | delta sul router | il client dichiara |
|---|---|---|
| `opcounters.insert` | **+12 541** | **12 541 scritture** |
| `opcounters.query` | **+13 003** | **13 003 letture** |

Coincidenza esatta su entrambe le righe. Il router è il posto giusto per rispondere a «quante
operazioni sono state chieste al cluster», ed è l'**unico** posto in cui quel numero è quello del
client.

### 4.2 Ma non dice che metà del cluster sta a guardare

Gli stessi contatori, sui due shard:

| | insert | query | connessioni |
|---|---|---|---|
| `shard1a` | **+12 546** | **+13 017** | 16 → 28 |
| `shard2a` | **+0** | **+0** | 14 → 14 |

Zero. Non «poco»: **nessuna operazione**, per tutta la corsa.

È la conferma quantitativa di una riserva che [V-079](../Sources.md#v-079) dichiarava a parole: la
collezione di carico non è partizionata, quindi vive intera sul primary shard. Ma vale la pena
dirla nella forma generale, perché è l'equivoco più comune davanti a un cluster:

> **Un cluster sharded non distribuisce il carico. Distribuisce le collezioni partizionate.** Se il
> database non è partizionato — o se lo è ma la collezione che state scrivendo non lo è — metà del
> ferro sta a guardare, e il router non ve lo dirà: i suoi contatori sono perfetti. Lo si scopre
> solo chiedendo shard per shard.

Questo è anche il motivo per cui la pagina sullo [sharded cluster](../02-architetture/sharded-cluster.md)
insiste sulla distinzione fra abilitare lo sharding su un database e partizionare una collezione.
Qui c'è il numero che la rende concreta.

### 4.3 `dbStats` sul router somma cose che non si sommano

Chiesto a `sh-mongos` sul database `lab`, e ai due shard:

```
router:   fsTotalSize 125 342 195 712     fsUsedSize 63 012 814 848
shard1a:  fsTotalSize  62 671 097 856     fsUsedSize 31 506 227 200
```

125 342 195 712 = **2 × 62 671 097 856**, esattamente. Ma i due shard sono due container sulla
stessa macchina e vedono lo **stesso** `/dev/vda1` da 62 671 097 856 byte. Il router dichiara un
disco che non esiste, grande il doppio del vero.

Le righe che si sommano legittimamente — `objects`, `dataSize`, `storageSize`, `indexSize` — sono
corrette. Quelle che descrivono **il ferro** non lo sono, perché sommare presuppone che gli shard
stiano su macchine diverse. In un cluster di produzione lo sono; in un lab su un portatile, e in
qualunque cluster con più shard sullo stesso host, quel numero è finzione.

Detto in generale: **un'aggregazione è corretta solo se l'operazione che la produce ha senso sul
dato aggregato.** Sommare documenti ha senso. Sommare la capacità di un filesystem condiviso no. Il
router non ha modo di distinguere i due casi, quindi somma tutto.

---

<a id="5-le-dimensioni-datasize-non-e-spazio-su-disco"></a>
## 5. Le dimensioni: `dataSize` non è spazio su disco

### 5.1 Il rapporto di compressione è una proprietà dei dati

Due collezioni dello stesso database, sullo stesso motore, con la stessa compressione predefinita
([V-087](../Sources.md#v-087)):

| collezione | documenti | `avgObjSize` | `size` | `storageSize` | rapporto |
|---|---|---|---|---|---|
| `lab.ordini` | 50 000 | 121 B | 6 094 260 | 1 990 656 | **3,06×** |
| `lab.carico-…` | 49 690 | 2 048 B | 101 765 120 | 105 021 440 | **0,97×** |

Sulla prima, `snappy` restituisce tre volte lo spazio. Sulla seconda **non restituisce niente**, e
l'archiviazione è del 3 % più grande dei dati.

La ragione sta nel generatore, non nel motore. La zavorra dei documenti di carico è base64 di uno
`shake_128` — byte pseudocasuali — e **i byte casuali non si comprimono**. Il 3 % in più è il costo
delle strutture di WiredTiger su un contenuto che non le ripaga.

Perché questo conta per chi monitora: **`dataSize` sommato su un database misto non dice quanto
disco serve, e `storageSize` da solo non dice quanto si sta risparmiando.** Il rapporto va misurato
sulla collezione con `collStats`, non stimato sul database con `dbStats`. Due database con lo
stesso `dataSize` possono occupare tre volte l'uno dell'altro.

### 5.2 Due dettagli che fanno perdere tempo

**`freeStorageSize` non c'è, se non lo si chiede.** `db.stats()` restituisce quattordici chiavi
sullo standalone, e quella non è fra loro: va chiesta con `db.stats({freeStorage: 1})`. Chi la cerca
senza chiederla trova `undefined`, che in uno script diventa facilmente uno zero.

**`dbStats` somma tutto quello che c'è, comprese le cose dimenticate.** Al momento della misura il
database `lab` dello standalone aveva **38 collezioni, 37 delle quali di carico**: ogni corsa di
`workload` ne crea una nuova, chiamata con l'istante di partenza, e nessuno le cancella. Sono 1,5
milioni di documenti e ~3 GB di `dataSize` che non interessano più a nessuno, e che `dbStats` conta
diligentemente.

Su un lab si sistema con un `drop`. Su un sistema vero, il fatto che nessuno guardi `collections` è
il modo tipico in cui un disco si riempie senza spiegazione.

---

<a id="6-una-ricetta-minima"></a>
## 6. Una ricetta minima

Se di questa pagina va tenuta una cosa sola, è questa tabella: la metrica per ogni domanda, con il
nodo su cui va letta.

| domanda | metrica | dove |
|---|---|---|
| Il server è in coda? | `wiredTiger.concurrentTransactions.write.queueLength` e `globalLock.currentQueue` | ogni `mongod` — **non** sul `mongos` |
| Ha aspettato, anche brevemente? | `wiredTiger.concurrentTransactions.write.totalTimeQueuedMicros` (delta) | ogni `mongod` |
| Quanto ci mette il server? | `opLatencies.writes` (delta di `latency`/`ops`) | ogni `mongod`, sapendo che sul primario include l'attesa della maggioranza |
| Quanto aspetta l'utente? | il client, non il server | l'applicazione |
| Il secondario sta applicando tutto? | `opcountersRepl.insert` (delta) | ogni secondario |
| Il secondario ha arretrato? | `metrics.repl.buffer.count` | ogni secondario |
| Quante operazioni ha chiesto il client? | `opcounters` (delta) | il `mongos` |
| Il carico è distribuito? | `opcounters` (delta) | **shard per shard**, mai il `mongos` |
| Quanto occupa una collezione? | `collStats`: `size` **e** `storageSize` | ogni `mongod` |

E tre numeri da non guardare: il ritardo di replica calcolato dagli `optimeDate` (§3.1),
`available` dei ticket contro una soglia fissa (§2.3), `fsTotalSize` su un `mongos` (§4.3).

---

## Cosa questa pagina non dice

- **Non è il riferimento dei campi di `serverStatus`.** Quello è il manuale, ed è la scelta
  registrata da [ADR-0112](../Decision.md#adr-0112). Chi cerca il significato di un campo che qui
  non compare lo trova là, aggiornato alla sua versione.
- **Non dice se i 18 390 µs del primario siano davvero l'attesa della maggioranza.** La lettura è
  coerente con i numeri, non isolata. La prova che chiuderebbe il punto è la stessa corsa con
  `w: 1` sul replica set, ed è un debito dichiarato in [V-083](../Sources.md#v-083).
- **Non copre `top`, `collStats` in dettaglio, `currentOp`, `$indexStats`, né il profiler.** Sono
  strumenti di diagnosi puntuale, e questa pagina risponde a «cosa guardare mentre gira», non a
  «come si indaga una query lenta» — per cui c'è
  [`04-mongosh/guida-mongosh.md`](../04-mongosh/guida-mongosh.md).
- **Non prova nessuno strumento di monitoraggio esterno.** Né Ops Manager, né Cloud Manager, né
  Prometheus con il suo esportatore. Sono la risposta giusta in produzione e richiedono componenti
  che questo lab, che deve funzionare senza rete, non ha
  ([ADR-0031](../Decision.md#adr-0031)).
- **Non dice quale sia una soglia di allarme ragionevole.** Le soglie dipendono dal sistema, e
  questa pagina ne ha appena mostrate due che sarebbero sbagliate ovunque. Ricavarle da un lab su un
  portatile sarebbe l'errore che la pagina insegna a evitare.
- **Non misura la cache sotto pressione.** Nelle corse la cache si assesta a ~200 MiB su un limite
  di 1 024 MB e il dirty non supera i 9 MiB: non si è mai vista una eviction sotto stress, che è
  proprio la condizione in cui `wiredTiger.cache` diventa interessante.
- **Non ripete le misure di resa fra architetture.** Stanno in [V-079](../Sources.md#v-079) e nelle
  tre pagine di `02-architetture/` — [standalone](../02-architetture/standalone.md),
  [replica set](../02-architetture/replica-set.md),
  [sharded cluster](../02-architetture/sharded-cluster.md) — con la riserva del ferro che
  [ADR-0111](../Decision.md#adr-0111) impone di far viaggiare con ogni numero.

---

**Decisioni correlate:** [ADR-0112](../Decision.md#adr-0112) (questa pagina mostra le metriche che
smentiscono la lettura ingenua, e dichiara inutilizzabile il ritardo di replica),
[ADR-0111](../Decision.md#adr-0111) (la riserva viaggia con il numero),
[ADR-0024](../Decision.md#adr-0024) (il materiale divulgativo non è documentazione normativa),
[ADR-0031](../Decision.md#adr-0031) (il lab funziona senza rete),
[ADR-0046](../Decision.md#adr-0046) (il costo della maggioranza, misurato).

**Fonti:** [V-027](../Sources.md#v-027), [V-031](../Sources.md#v-031),
[V-076](../Sources.md#v-076), [V-079](../Sources.md#v-079), [V-082](../Sources.md#v-082),
[V-083](../Sources.md#v-083), [V-084](../Sources.md#v-084), [V-085](../Sources.md#v-085),
[V-086](../Sources.md#v-086), [V-087](../Sources.md#v-087)
