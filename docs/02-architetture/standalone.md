# Istanza singola

Un solo processo `mongod`, un solo disco, un solo punto di guasto. È la forma con cui quasi tutti
incontrano MongoDB la prima volta, ed è la ragione per cui il talk dura sessanta minuti invece di
dieci.

Questa pagina risponde a due domande, in quest'ordine: **cosa non garantisce** un'istanza singola, e
**quando basta davvero**. La prima apre il talk. La seconda è quella che rende credibile la prima,
perché dire che un'istanza singola non va mai bene sarebbe falso, e il pubblico se ne accorge.

**Ogni limite di questa pagina si può riprodurre in venti secondi**, su un portatile, davanti a
chiunque. I comandi sono quelli, con le uscite che hanno prodotto qui il 2026-08-28 su
`mongo` 7.0.40 ([V-015](../Sources.md#v-015), [V-016](../Sources.md#v-016)). La decisione di
scrivere la pagina così — quattro limiti citabili invece di un aggettivo — è
[ADR-0032](../Decision.md#adr-0032).

---

## 1. Cosa non garantisce

Quattro limiti. Tre si fanno sentire, uno no, ed è quello che vale il biglietto.

### 1.1 Nessuna ridondanza, nessun failover

Non c'è nulla da eleggere, perché non c'è nessuno da eleggere. Il processo che muore è il servizio
che finisce, e chiederlo al nodo produce una risposta senza ambiguità:

```console
$ docker compose exec -T mongo-standalone mongosh --quiet --eval 'rs.status()'
MongoServerError[NoReplicationEnabled]: not running with --replSet
```

Codice 76, `NoReplicationEnabled` [V-015](../Sources.md#v-015). Questa è una buona notizia nel senso
stretto del termine: il server dice di no, dice perché, e lo dice al primo tentativo. Dei quattro
limiti è il più innocuo, proprio perché è il più rumoroso.

Vale la pena dire cosa **non** significa. Non significa che il dato sia in pericolo appena il
processo si ferma: il dato è sul disco, e alla ripartenza torna. Significa che fra la fermata e la
ripartenza non risponde nessuno, e che quel tempo lo decide chi se ne accorge — non
l'infrastruttura.

Con `restart: unless-stopped` nel file Compose il container riparte da solo in molti casi, ma non
in tutti, e i casi scoperti non sono quelli che si immaginano: vedi
[la voce 6 delle trappole](trappole-mongodb-in-docker.md#t-06).

Il seguito è misurato. Su un replica set a tre membri lo stesso colpo costa **~10 secondi** fino al
nuovo primario, e **mezzo secondo** se il primario saluta invece di essere ucciso: le tre scene,
cronometrate, stanno in [«Le elezioni, cronometrate»](replica-set.md#2-le-elezioni-cronometrate).

### 1.2 `w: 1` è tutto ciò che si può chiedere — e `w: "majority"` è la stessa cosa travestita

Qui la pagina rallenta, perché è il punto in cui il repository ha trovato qualcosa che il manuale
non dice.

**Cosa dice il manuale.** Su un'istanza singola, «a standalone `mongod` acknowledges a write
operation after applying the write in memory **or** after writing to the on-disk journal»
[S-035](../Sources.md#s-035). Quale delle due lo decide una tabella, e la riga che riguarda il caso
predefinito — `w: 1`, `j` non specificato — dice **In memory**.

Tradotto: quando l'applicazione riceve `acknowledged: true`, il dato è in memoria. Il disco arriva
dopo. Quanto dopo lo dice [S-036](../Sources.md#s-036): il journal viene sincronizzato «At every 100
milliseconds», e nel frattempo, testuale, «updates can be lost following a hard shutdown of
`mongod`».

**Cosa succede se si chiede di più.** Niente, perché non si può:

```console
$ mongosh --quiet --eval 'db.ordini.insertOne({x: 1}, {writeConcern: {w: 2}})'
MongoServerError[BadValue]: cannot use 'w' > 1 when a host is not replicated
```

**E qui arriva il limite silenzioso.** La stessa scrittura con `w: "majority"` — la write concern
che qualunque guida consiglia per i dati che contano — **riesce**:

```console
$ mongosh --quiet --eval 'db.ordini.insertOne({x: 1}, {writeConcern: {w: "majority"}})'
{ acknowledged: true, insertedId: ... }
```

Nessun errore. Nessun avviso. Nessuna riga di log. La maggioranza di un nodo è quel nodo
[V-015](../Sources.md#v-015).

Questo è lo scenario da raccontare, perché è quello che capita davvero: un'applicazione scritta per
un replica set, con `w: "majority"` diligentemente scritto su ogni operazione importante, viene
puntata su un'istanza singola — in sviluppo, in un ambiente di collaudo, in una migrazione andata a
metà — e **continua a funzionare**. Il codice crede di avere una garanzia che non ha. Non c'è niente
che glielo dica, e il giorno in cui si scopre non è un giorno tranquillo.

Su un replica set la stessa istruzione smette di essere una bugia — la conferma arriva quando due
membri su tre hanno la scrittura — e il prezzo, misurato, è **un millisecondo**:
[«Qui `w: "majority"` vuol dire qualcosa»](replica-set.md#31-qui-w-majority-vuol-dire-qualcosa).

#### La finestra, misurata

Le due frasi del manuale descrivono una finestra. Aprirla richiede un `SIGKILL` e cinque minuti
[V-016](../Sources.md#v-016): uno scrittore inserisce documenti uno alla volta con la write concern
predefinita e stampa ogni `_id` **dopo** la conferma del server; a metà corsa il container viene
ucciso senza chiusura pulita.

| Grandezza | Valore |
|---|---:|
| ultimo `_id` confermato al client | 41.558 |
| documenti sopravvissuti al riavvio | 41.458 |
| **documenti confermati e perduti** | **100** |

Cento scritture per cui l'applicazione aveva in mano un `acknowledged: true` non esistono più.

Tre precisazioni, tutte necessarie:

- **Non è un difetto di MongoDB.** È il comportamento documentato, con il numero che gli
  corrisponde su questa macchina. Chi vuole la durabilità la chiede — `j: true` — e la paga in
  latenza.
- **Cento non è una costante.** È quanti inserimenti stavano nella finestra *a quel ritmo, su quel
  disco*. Con scritture in lotto il numero cambia. Quello che non cambia è che la finestra esista.
- **La misura è a senso unico.** L'uscita dello scrittore passa per una pipe, che può bufferizzare:
  il conteggio degli ack può essere in difetto, mai in eccesso. Cento è quindi un **minimo**.

E una cosa che nella stessa prova **non** è andata persa: il dataset di demo. Cinquantamila ordini,
impronta invariata dopo il kill e il recovery [V-016](../Sources.md#v-016). Erano in un checkpoint
da tempo; a cadere è solo ciò che stava nella finestra. La differenza fra i due esiti, sulla stessa
macchina e nello stesso istante, è la lezione dell'intero paragrafo.

Il numero gemello, quello che [ADR-0032](../Decision.md#adr-0032) rimandava a `feature/02`, adesso
esiste: la stessa prova su un replica set, con `w: "majority"` e il primario ucciso, perde **zero**
scritture su 12 901 confermate — al prezzo di una pausa di dieci secondi e di un errore per un
documento che nel database **c'è** ([V-033](../Sources.md#v-033)). Il confronto per righe è in
[«Il confronto con l'istanza singola»](replica-set.md#4-il-confronto-con-listanza-singola).

### 1.3 Nessun oplog: niente change stream, niente backup a caldo coerente

L'oplog è «a special capped collection that keeps a rolling record of all operations that modify the
data stored in your databases», e «all **replica set members** contain a copy of the oplog, in the
`local.oplog.rs` collection» [S-037](../Sources.md#s-037). Su un'istanza singola non c'è, e si vede:

```console
$ mongosh --quiet --eval 'print(db.getSiblingDB("local").getCollectionNames())'
startup_log
```

Una sola collezione [V-015](../Sources.md#v-015). Da qui discendono due mancanze che si notano in
momenti diversi.

**I change stream non esistono.** «Change streams are available for replica sets and sharded
clusters» [S-038](../Sources.md#s-038), e chi ci prova comunque riceve:

```console
$ mongosh --quiet --eval 'db.ordini.watch()'
MongoServerError[Location40573]: The $changeStream stage is only supported on replica sets
```

Anche questo è un limite rumoroso, e si scopre in sviluppo.

**Il backup a caldo coerente non si ottiene.** Questo si scopre più tardi, che è il problema.
`mongodump` funziona benissimo su un'istanza singola; quello che non funziona è `--oplog`, cioè
l'opzione che rende il dump un'istantanea coerente rispetto alle scritture in corso
[S-011](../Sources.md#s-011):

```console
$ mongodump --oplog --out=/tmp/dump
Failed: error getting oplog start: error getting recent oplog entry: mongo: no documents in result
```

Il messaggio descrive il sintomo e nasconde la causa [V-015](../Sources.md#v-015). «No documents in
result» manda a cercare un documento mancante; il problema è che manca la collezione, e manca perché
manca il replica set.

Senza `--oplog` un dump preso mentre l'applicazione scrive **non è un'istantanea**: le collezioni
vengono lette una dopo l'altra, e fra la prima e l'ultima il mondo è cambiato. Le conseguenze e la
procedura completa sono in [ADR-0022](../Decision.md#adr-0022) e nella pagina di
`feature/02-stack-replicaset` su backup e restore.

### 1.4 La manutenzione vuole una finestra di fermo

L'ultimo limite non ha un messaggio d'errore perché non è un errore: è aritmetica. Aggiornare la
versione di MongoDB, cambiare un parametro che richiede riavvio, spostare i dati su un altro disco,
ridimensionare la cache — ognuna di queste operazioni ferma il processo, e fermare l'unico processo
significa fermare il servizio.

Su un replica set le stesse operazioni si fanno **a rotazione**, un membro alla volta, con il
servizio sempre in piedi. È la differenza pratica che più spesso decide l'adozione, e curiosamente è
quella di cui si parla meno: si discute di alta disponibilità pensando ai guasti, mentre la maggior
parte delle fermate è pianificata.

Quanto costa quel «sempre in piedi» — in memoria, in porte e in complessità di avvio — è la prima
sezione di [replica set a tre membri](replica-set.md#1-perché-i-membri-sono-tre).

---

## 2. Quando basta davvero

Se la sezione precedente fosse tutta la verità, nessuno userebbe un'istanza singola, e invece la
usano tutti — compreso questo repository, in tre dei suoi quattro stack di lavoro. Ecco i casi in
cui è la scelta giusta, non un compromesso.

**Sviluppo sulla macchina di chi scrive il codice.** Un `mongod` in un container, dati ricostruibili
con un comando, nessuna elezione da attendere all'avvio. Il tempo che si risparmia a ogni
riavvio è tempo vero, e la ridondanza non serve a nessuno su un portatile.

**Integrazione continua.** Un'istanza per esecuzione, distrutta alla fine. Il dato dura quanto la
pipeline. Un replica set qui costerebbe tempo di avvio a ogni corsa in cambio di una garanzia che a
nessuno interessa.

**Collaudo e dimostrazioni.** Ambienti che si ricreano a comando, con dataset generati. È il caso di
questo lab: lo stack 01 esiste per essere acceso, guardato, spento e dimenticato.

**Dati ricostruibili.** Cache, indici derivati, risultati di elaborazioni che si possono rifare
dalla sorgente. Se la perdita del dato costa un ricalcolo e non una telefonata, la ridondanza è un
costo senza contropartita.

**Ambienti con un vincolo di risorse duro.** Tre nodi costano tre volte la memoria. Su un dispositivo
periferico, in un laboratorio, dentro un budget, un nodo che funziona batte tre nodi che non stanno
in piedi. Il conto è in [gestione delle risorse](../06-sviluppo/gestione-risorse-compose.md).

La domanda onesta da farsi non è «standalone o replica set», ma: **quanto costa il tempo in cui non
risponde nessuno, e quanto costa il dato scritto negli ultimi cento millisecondi.** Se entrambe le
risposte sono «poco», un'istanza singola è la scelta giusta e le altre due architetture sono
complessità che non serve.

Se invece una delle due risposte è «molto», la pagina successiva è
[replica set a tre membri](replica-set.md): tre processi, un guasto tollerato, e ogni numero
misurato su questo stack.

---

## 3. Il file Compose, riga per riga

Il file è [`docker/01-standalone/compose.yaml`](../../docker/01-standalone/compose.yaml). Sta in
sessanta righe, di cui metà sono commenti. Qui si spiega perché ogni pezzo è com'è, con i numeri
misurati e non stimati.

### Il nome del progetto e l'immagine

```yaml
name: sqlstart-01-standalone

services:
  mongo-standalone:
    image: ${MONGO_IMAGE:?assente — eseguire «make images-pull», oppure passare --env-file tools/images.env}
```

Il nome esplicito del progetto evita che Compose lo deduca dal nome della cartella
([ADR-0003](../Decision.md#adr-0003)), così i tre stack convivono senza pestarsi i piedi.

L'immagine arriva per **digest**, non per tag, da `tools/images.env` generato da `make images-pull`
([ADR-0028](../Decision.md#adr-0028)). La forma `${VAR:?messaggio}` fa fallire Compose subito e
dicendo cosa manca, invece di avviare un container con un'immagine vuota. La versione è 7.0.40 e non
una 8.x, per una ragione che è costata uno spike intero: è scritta nello stesso ADR.

### Nome host e politica di pull

```yaml
    container_name: mongo-standalone
    hostname: mongo-standalone
    pull_policy: never
    restart: unless-stopped
```

Il nome host esplicito qui non serve a nessuno — c'è un nodo solo — e c'è lo stesso, perché la buona
abitudine si prende sullo stack dove non costa niente. Sugli altri due gli indirizzi IP sono un
guasto in attesa ([ADR-0021](../Decision.md#adr-0021)).

`pull_policy: never` significa che l'immagine non viene **mai** scaricata: se non è nella cache
locale l'avvio fallisce subito, e in sala è esattamente ciò che si vuole — un errore in un decimo di
secondo invece di un minuto di attesa di rete davanti al pubblico
([V-022](../Sources.md#v-022)). Il valore è scritto fisso e non arriva da una variabile: una
variabile si dimentica di passare, un file no, e questo file va proiettato
([ADR-0039](../Decision.md#adr-0039), che supera [ADR-0018](../Decision.md#adr-0018)). Il prezzo è
`make images-pull` una volta, a casa, con la rete.

### Memoria e CPU

```yaml
    mem_limit: 1024m
    cpus: 1.0
```

Senza `mem_limit` la cache di WiredTiger si dimensiona sulla memoria della **VM** e un solo `mongod`
ne rivendica 5.461 MiB [V-009](../Sources.md#v-009). Non è un problema qui, con un nodo; lo diventa
sugli stack 02 e 03, dove la somma sfonda la macchina. La regola vale per tutti e tre e sta in
[gestione delle risorse](../06-sviluppo/gestione-risorse-compose.md); la decisione è
[ADR-0004](../Decision.md#adr-0004).

### Il comando, e ciò che non contiene

```yaml
    command:
      - mongod
      - --wiredTigerCacheSizeGB
      - "0.25"
```

`0.25` sono GiB, non GB: **268.435.456 byte esatti**, cioè 256 MiB dentro un limite di 1.024
[V-012](../Sources.md#v-012). Il valore è dichiarato a mano non perché `mongod` non sappia leggere il
proprio cgroup — lo legge, ed è misurato — ma perché questo file è materiale didattico e il calcolo
deve vedersi. Da sapere: **nessuno controlla che la cache stia sotto il `mem_limit`.** Un container
da 512 MiB con una cache da 4 GiB parte senza un avviso e si condanna alla prima scrittura seria.

Ciò che nel comando **non** c'è conta quanto ciò che c'è. Non c'è `--logpath`, e non è una
dimenticanza: l'aiuto del binario dice «Log file to send write to **instead of** stdout», ed è una
redirezione, non una duplicazione. Con `--logpath` attivo il file ha 65 righe e `docker logs` ne ha
zero [V-010](../Sources.md#v-010). Attivarlo spegnerebbe `docker compose logs`, che è il modo più
naturale di mostrare i log dal palco. La decisione è [ADR-0030](../Decision.md#adr-0030), la pagina
completa è [i log](../03-amministrazione/log.md).

E non c'è `--auth`, che è il punto successivo.

### La porta

```yaml
    ports:
      - "${PORTA_HOST:-27017}:27017"
```

27017 come da mappa del design. Gli stack 02 e 03 usano intervalli diversi apposta: i tre progetti
devono poter convivere.

Qui va detta una cosa che riguarda la sicurezza. L'entrypoint ufficiale aggiunge `--bind_ip_all` al
comando, sempre, senza che il nostro file lo chieda: `/proc/1/cmdline` dice
`mongod --wiredTigerCacheSizeGB 0.25 --bind_ip_all` [V-012](../Sources.md#v-012),
[S-034](../Sources.md#s-034). Dentro la rete Docker va benissimo. Insieme all'assenza di
autenticazione significa però che **l'unica barriera è la porta pubblicata sull'host**, e su una rete
condivisa quella barriera non c'è. Vedi [§4](#4-questo-stack-gira-senza-autenticazione-di-proposito).

### I volumi

```yaml
    volumes:
      - dati:/data/db
      - ./init:/docker-entrypoint-initdb.d:ro
```

Volume **nominato**, non bind mount: su macOS un bind mount di `/data/db` paga il filesystem
condiviso a ogni scrittura, e la demo sulle prestazioni finirebbe per misurare VirtioFS invece di
WiredTiger.

Il secondo montaggio ha una trappola dentro, ed è quella che morde più spesso in sviluppo:
**l'entrypoint esegue gli script di `/docker-entrypoint-initdb.d` solo se il volume non è già
inizializzato, e quando decide di saltarli non stampa niente.** Non un avviso, non una riga
[V-014](../Sources.md#v-014). Il criterio non è nemmeno «la cartella è vuota»: è la presenza di uno
fra quattro percorsi noti [S-034](../Sources.md#s-034). Dettagli e rimedio in
[la voce 1 delle trappole](trappole-mongodb-in-docker.md#t-01);
la seconda strada per caricare i dati è `make seed-01` ([ADR-0031](../Decision.md#adr-0031)).

### La rotazione dei log

```yaml
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

Se i log stanno su stdout, ruotarli non è più affare di `mongod`: è affare del runtime. Il driver
`json-file` **non ruota niente** per impostazione predefinita — `max-size` vale `-1 (unlimited)` e
`max-file` vale `1` [V-011](../Sources.md#v-011), [S-033](../Sources.md#s-033). Con la demo sulle
prestazioni, che apre e chiude connessioni a raffica, un file senza limiti cresce finché c'è disco.
Dieci MiB per tre file: trenta MiB al massimo.

Quanto scrive davvero? A riposo, con il solo healthcheck a lavorare: circa **142 righe al minuto**,
cioè circa 3 MiB per la durata del talk, con zero carico [V-011](../Sources.md#v-011).

### L'healthcheck

```yaml
    healthcheck:
      test: ["CMD", "mongosh", "--quiet", "--eval", "db.adminCommand('ping').ok"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s
```

`mongosh` è dentro l'immagine (2.10.0) e un `ping` è l'unica prova onesta che il nodo serva: una
porta in ascolto non vuol dire pronta a rispondere. Costa circa 300 ms a esecuzione, ogni dieci
secondi, dentro una CPU [V-012](../Sources.md#v-012) — ed è il produttore dominante di righe di log
quando non succede nient'altro.

`start_period` esiste perché senza di lui i primi tentativi falliti contano come guasti e il
container risulta `unhealthy` mentre sta semplicemente ancora partendo. Al primo avvio, con il
caricamento dei 50.000 ordini, il nodo diventa `healthy` in **5,46 secondi**
[V-012](../Sources.md#v-012): venti secondi di franchigia sono abbondanti e non costano niente.

---

## 4. Questo stack gira senza autenticazione, di proposito

Non è una svista da correggere in una pull request. È l'esempio negativo di
[ADR-0005](../Decision.md#adr-0005), e sta scritto in testa al file Compose perché chi lo copia se lo
porti dietro.

Le ragioni per cui il lab lo fa:

- **Il talk deve mostrare l'architettura, non la gestione delle credenziali.** Ogni `mongosh` con
  `-u`/`-p` sulle slide è rumore che allontana dall'argomento.
- **Il primo stack deve partire e basta.** L'autenticazione arriva in `feature/02`, dove serve
  davvero: su un replica set il keyfile non è una scelta di sicurezza, è un requisito di
  funzionamento.
- **Un esempio negativo dichiarato insegna più di un esempio corretto muto.** Chi vede scritto
  «questo file gira senza autenticazione, ed ecco perché è accettabile solo qui» ricorda la
  distinzione. Chi trova solo `--auth` copia `--auth` senza sapere cosa fa.

Cosa questo significa in pratica, misurato: `mongod` ascolta su tutte le interfacce del container
perché l'entrypoint aggiunge `--bind_ip_all` [V-012](../Sources.md#v-012), e la porta 27017 è
pubblicata sull'host. **Chiunque possa raggiungere quella porta è amministratore.** Su un portatile
dietro un router domestico è irrilevante; su una rete d'ufficio, di conferenza o di coworking non lo
è.

Se questo file finisce fuori dal lab, i due interventi minimi sono: pubblicare la porta solo sul
loopback (`"127.0.0.1:27017:27017"`) e aggiungere `MONGO_INITDB_ROOT_USERNAME` /
`MONGO_INITDB_ROOT_PASSWORD` più `--auth`. Il secondo intervento ha una trappola sua sugli stack con
`--replSet`, ed è documentata fra
[la voce 3 delle trappole](trappole-mongodb-in-docker.md#t-03).

---

## 5. Provarlo in venti secondi

```console
# Accendere, e attendere che sia sano davvero (non solo avviato)
$ make up-01

# I quattro limiti, uno per riga
$ docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml \
    exec -T mongo-standalone mongosh lab --quiet --eval '
      print("local: " + db.getSiblingDB("local").getCollectionNames());
      try { db.ordini.watch() } catch (e) { print("watch: " + e.codeName) }
      try { rs.status() }      catch (e) { print("rs:    " + e.codeName) }
      try { db.ordini.insertOne({x:1}, {writeConcern:{w:2}}) } catch (e) { print("w=2:   " + e.codeName) }
      print("majority: " + db.ordini.insertOne({x:1}, {writeConcern:{w:"majority"}}).acknowledged);
      db.ordini.deleteMany({x: 1});'

# La prova completa dello stack: dodici controlli
$ make smoke-01

# Spegnere conservando i dati, oppure ripartire da zero
$ make down-01
$ make reset-01
```

L'uscita attesa del blocco centrale:

```
local: startup_log
watch: Location40573
rs:    NoReplicationEnabled
w=2:   BadValue
majority: true
{ acknowledged: true, deletedCount: 1 }
```

Le prime quattro righe sono i limiti che si fanno sentire. La quinta è quello che non si fa sentire,
e sulla slide sta da sola. L'ultima è il valore dell'ultima istruzione, che `mongosh` stampa sempre:
`deletedCount: 1` e non `2`, perché l'inserimento con `w: 2` non è mai avvenuto — mentre quello con
`w: "majority"` sì.

---

## Cosa questa pagina non dice

- **Non confronta le prestazioni con le altre architetture.** Il confronto ha senso sotto carico
  controllato, cioè con l'applicazione Python di `feature/04`, e prima di allora sarebbe aria.
- **Non misura la perdita con `j: true`.** Secondo [S-035](../Sources.md#s-035) dovrebbe azzerarsi,
  al prezzo della latenza. È la misura naturale da aggiungere e non è stata fatta
  [V-016](../Sources.md#v-016).
- **Non copre l'autenticazione.** Lo stack la esclude per scelta; la trattazione seria è in
  `feature/02`, dove il keyfile diventa obbligatorio.
- **Non copre l'installazione fuori da Docker.** Sta in
  [`01-installazione/linux.md`](../01-installazione/linux.md) e
  [`01-installazione/windows.md`](../01-installazione/windows.md), con la riserva che quelle
  procedure non sono state eseguite qui.
- **I codici d'errore valgono per MongoDB 7.0.40.** I numeri (`40573`, `76`, `2`) sono la parte
  stabile; i testi dei messaggi cambiano con più facilità, e quelli di `mongodump` hanno una
  numerazione di versione tutta loro [S-011](../Sources.md#s-011).

---

**Decisioni correlate:** [ADR-0032](../Decision.md#adr-0032) (i quattro limiti citabili),
[ADR-0046](../Decision.md#adr-0046) (il seguito: il replica set con i suoi numeri),
[ADR-0005](../Decision.md#adr-0005) (lo stack senza autenticazione come esempio negativo),
[ADR-0030](../Decision.md#adr-0030) (i log su stdout),
[ADR-0031](../Decision.md#adr-0031) (il dataset deterministico),
[ADR-0022](../Decision.md#adr-0022) (backup a caldo e oplog),
[ADR-0028](../Decision.md#adr-0028) (perché la 7.0).

**Fonti:** [S-011](../Sources.md#s-011), [S-033](../Sources.md#s-033), [S-034](../Sources.md#s-034),
[S-035](../Sources.md#s-035), [S-036](../Sources.md#s-036), [S-037](../Sources.md#s-037),
[S-038](../Sources.md#s-038), [V-009](../Sources.md#v-009), [V-010](../Sources.md#v-010),
[V-011](../Sources.md#v-011), [V-012](../Sources.md#v-012), [V-014](../Sources.md#v-014),
[V-015](../Sources.md#v-015), [V-016](../Sources.md#v-016),
[V-033](../Sources.md#v-033)
