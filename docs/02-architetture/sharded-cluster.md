# Sharded cluster: due shard, un router, e una decisione che non si disfa

Undici container per gli stessi ventimila documenti che l'[istanza singola](standalone.md) tiene in
uno. La pagina del [replica set](replica-set.md) risponde alla domanda «quanto costa il tempo in cui
non risponde nessuno»; questa risponde a una domanda diversa, che si pone molto più tardi e a molte
meno persone: **che cosa si fa quando i dati, o le scritture, non stanno più su una macchina sola.**

Un avviso in apertura, perché è l'unica informazione di questa pagina che cambia il momento in cui
si decide, e non il modo. Distribuire una collezione **non è reversibile**: «Once a collection has
been sharded, MongoDB provides no method to unshard a sharded collection»
([S-069](../Sources.md#s-069)). Si può ridistribuire con una chiave diversa — il *resharding*, dalla
5.0 — ma non si può tornare a una collezione normale. Le altre due architetture di questo
repository si disfano spegnendo un container; questa no.

E il vero soggetto della pagina non è la topologia, che si disegna in trenta secondi. È la **shard
key**: la sola scelta di questo capitolo che, sbagliata, produce un cluster che funziona, non dà
errori, e non fa il suo lavoro. La sezione [3](#3-la-shard-key-che-è-la-decisione-che-non-si-cambia)
è quella per cui esistono le altre.

Come per il replica set, ogni numero qui è stato misurato su questo stack, su un portatile, e porta
accanto la verifica che lo ha prodotto e la riserva che lo qualifica ([ADR-0068](../Decision.md#adr-0068)).

---

## 1. Che problema risolve, e quando non serve

### 1.1 Scalare in alto, o scalare di lato

Il manuale pone il problema in termini di capacità, non di guasti: «Database systems with large data
sets or high throughput applications can challenge the capacity of a single server. For example,
high query rates can exhaust the CPU capacity of the server. Working set sizes larger than the
system's RAM stress the I/O capacity of disk drives» ([S-069](../Sources.md#s-069)).

Le risposte possibili sono due, e la seconda non è gratis:

| | Che cosa si fa | Il limite |
|---|---|---|
| **Verticale** | CPU più veloce, più RAM, più disco sulla stessa macchina | «Available technology and cloud provider hardware configurations impose a practical maximum» |
| **Orizzontale** | Si divide il dataset e il carico su più macchine, se ne aggiungono | «**The trade-off is increased complexity in infrastructure and maintenance**» |

Quell'ultima riga è la frase che questo laboratorio mette in pratica meglio di qualunque
spiegazione: **un** container per l'istanza singola, **tre** per il replica set, **undici** per lo
sharded cluster nel profilo ridotto e **diciotto** in quello completo. Gli stessi dati, lo stesso
generatore, lo stesso seme.

### 1.2 Che cosa si guadagna, in tre voci

Il manuale ne elenca tre, e la terza è quella che sorprende chi arriva dal replica set
([S-069](../Sources.md#s-069)):

1. **Letture e scritture.** «MongoDB distributes the read and write workload across the shards in
   the sharded cluster, allowing each shard to process a subset of cluster operations.» Un replica
   set non fa questo: le scritture vanno tutte al primario, sempre.
2. **Capacità.** «As the data set grows, additional shards increase the storage capacity of the
   cluster.» È il motivo per cui si sharda quando non ci si sta più.
3. **Disponibilità, ma parziale.** «Even if one or more shard replica sets become completely
   unavailable, the sharded cluster can continue to perform partial reads and writes. That is, while
   data on the unavailable shard(s) cannot be accessed, reads or writes directed at the available
   shards can still succeed.»

La terza va letta con attenzione, perché è diversa da quello che dà un replica set. Un replica set
perde un membro e continua a rispondere **su tutti i dati**. Uno sharded cluster perde uno shard e
continua a rispondere **su una parte dei dati**: passano le query che toccano solo gli shard sani,
falliscono quelle che toccano lo shard perduto. Non in silenzio — l'errore arriva, e nomina il
replica set che manca — ma nemmeno subito: sedici secondi ([V-097](../Sources.md#v-097)). La
disponibilità non è più una proprietà del cluster, è una proprietà della singola query.

### 1.3 Quando non serve — e qui il manuale non aiuta

Questa è la domanda che il pubblico fa davvero, ed è onesto dire subito che **la fonte non la
copre**. La pagina d'ingresso del manuale ha una sezione intitolata «Considerations Before
Sharding», e chi la apre aspettandosi una soglia non la trova: non c'è una dimensione minima, non
c'è un numero di documenti, non c'è nessuna frase del tipo «non distribuire se…»
([S-069](../Sources.md#s-069), «cosa non afferma»). Quello che c'è sono tre avvertimenti:

> «Sharded cluster infrastructure requirements and complexity require careful planning, execution,
> and maintenance.»
>
> «Once a collection has been sharded, MongoDB provides no method to unshard a sharded collection.»
>
> «While you can reshard your collection later, carefully consider your shard key choice to avoid
> scalability and performance issues.»

Il resto è giudizio di chi scrive, e va preso per tale — non attribuito a MongoDB. Il giudizio,
tratto dai numeri dei tre stack di questo repository, è questo: **lo sharding risponde a un problema
di capacità, non di disponibilità e non di prestazioni in generale.** Se il working set sta nella
RAM di una macchina, un replica set dà già l'alta disponibilità, la lettura distribuita sui
secondari e la durabilità, senza aggiungere otto processi, un registro di metadati che può perdersi
([§7.2](#72-il-volume-cera-aveva-il-nome-giusto-ed-era-vuoto)) e una decisione che non si annulla.

Un numero per capire quanto sia sovradimensionato il laboratorio rispetto al problema che simula:
la collezione distribuita della demo pesa **2 437 499 byte** in tutto — due megabyte e mezzo —
spalmati su due shard che sarebbero pronti a reggerne centinaia di volte tanto
([V-061](../Sources.md#v-061)). Il lab non è sharded perché serva: è sharded perché è l'unico modo
di **far vedere** un cluster sharded su un portatile.

---

## 2. I tre ruoli, e perché nessuno è opzionale

### 2.1 I componenti, e i loro vincoli

«A MongoDB sharded cluster consists of the following components» ([S-069](../Sources.md#s-069)) —
tre, ciascuno con un vincolo scritto nella stessa riga che lo definisce:

| Ruolo | Che cosa fa, testuale | Vincolo |
|---|---|---|
| **shard** | «Each shard contains a subset of the sharded data» | «**Each shard must be deployed as a replica set**» |
| **`mongos`** | «acts as a query router, providing an interface between client applications and the sharded cluster» | nessuno stato da conservare |
| **config server** | «store metadata and configuration settings for the cluster» | «**must be deployed as a replica set (CSRS)**» |

E la granularità, che è la riga più dimenticata di tutte: «MongoDB shards data at the **collection**
level». Non si distribuisce un database, si distribuisce una collezione alla volta — e le altre
restano dove sono ([§6.3](#63-le-collezioni-non-distribuite-e-lo-shard-primario)).

Nel laboratorio i tre ruoli diventano questo:

| | Profilo `palco` | Profilo `completo` | Porta sull'host |
|---|---|---|---|
| Config server | `cfg1` | `cfg1` `cfg2` `cfg3` | 27131 · 27132 · 27133 |
| Shard 1 (`shard1rs`) | `shard1a` | `shard1a` `shard1b` `shard1c` | 27141 · 27142 · 27143 |
| Shard 2 (`shard2rs`) | `shard2a` | `shard2a` `shard2b` `shard2c` | 27151 · 27152 · 27153 |
| Router | `mongos` | `mongos` `mongos2` | 27117 · 27118 |
| **Container in tutto** | **11** | **18** | |

I numeri contano anche i servizi che vivono un istante e muoiono: `keyfile-init`, i tre `*-init` che
inizializzano i replica set, `add-shard` che registra gli shard, `seed` che carica i dati e la
sentinella `up-03`. Sono sei anelli di una catena che rende vero `up --wait`
([§7.1](#71-la-catena-dei-sei-anelli-e-la-sentinella)).

I due profili non cambiano la topologia logica: sono sempre due shard e un insieme di config server.
Cambiano quanti membri ha ciascun insieme. Un replica set a **un** membro è legittimo e documentato
([S-024](../Sources.md#s-024)), e serve a far entrare undici processi MongoDB in un portatile.

### 2.2 I config server sono il cluster

Il nome inganna: sembrano un dettaglio di configurazione, e invece **sono** il cluster. Contengono
l'elenco degli shard, la mappa dei chunk, gli utenti, e il registro delle operazioni di
bilanciamento. Tolti loro, i nove processi che conservano i dati restano nove replica set
indipendenti che non sanno di far parte di niente.

Che sia letteralmente così lo ha dimostrato un guasto, e non un ragionamento: quando i config server
di questo stack perdevano i propri dati a ogni spegnimento, il secondo avvio trovava «shard già
registrati: **nessuno**» su un cluster che al giro prima ne aveva due — mentre sugli shard i dati
c'erano tutti ([V-060](../Sources.md#v-060)). La storia è in
[§7.2](#72-il-volume-cera-aveva-il-nome-giusto-ed-era-vuoto), e vale la pena leggerla perché è il
modo più rapido di capire dove viva davvero lo stato di un cluster sharded.

Il manuale mette sui config server tre vincoli che tolgono le scorciatoie tipiche di chi vuole
risparmiare risorse ([S-025](../Sources.md#s-025)): «Must zero arbiters. / Must no delayed members.
/ Must build indexes». E uno che sembra pedanteria finché non morde: «The config server replica set
must not same name any shard replica sets» — nel lab `cfgrs`, `shard1rs`, `shard2rs`.

Una conseguenza pratica che si scopre solo provando: **gli utenti del cluster vivono qui.** Le
credenziali che entrano dal router funzionano su `cfg1`, e fino al 2026-09-02 in diretta su
`shard1a` fallivano con `Authentication failed` ([V-058](../Sources.md#v-058)). Sembrava un limite
scomodo ed era una fortuna: rendeva difficile per costruzione la cosa che il manuale vieta —
«Clients should *never* connect to a single shard to perform read or write operations»
([S-069](../Sources.md#s-069)).

Quella fortuna è finita, e va detto qui perché è una nostra scelta. Da
[ADR-0071](../Decision.md#adr-0071) ogni shard ha un amministratore locale, con lo stesso nome e
la stessa password del cluster: la porta si apre, e apre su un'anagrafe diversa
([V-067](../Sources.md#v-067)). Chi sbaglia indirizzo adesso **entra** — e legge 9 860 documenti
su 20 000 credendo di avere la collezione. La ragione per cui non si fa non è cambiata; è
cambiato che a impedirlo non c'è più un errore, ma la disciplina di chi opera.

### 2.3 `mongos`, il router che non ha niente da perdere

È l'unico servizio dello stack **senza volume**. Non conserva dati, non conserva metadati: legge la
mappa dai config server e instrada. La prova è brutale e sta in una riga di misura: fermato
`sh-mongos` con `docker stop`, la stessa scrittura data a `mongos2` passa e vede i due shard; niente
è andato perso, perché non c'era niente da perdere ([V-055](../Sources.md#v-055)). La morte di un
router è un dettaglio operativo, non un incidente — ed è la ragione per cui il profilo `completo` ne
tiene due e il `palco` uno solo.

Due cose che il router **non** fa, e che gli vengono attribuite spesso:

- **Non bilancia.** «The balancer runs on the primary of the config server replica set (CSRS)»
  ([S-070](../Sources.md#s-070)). A spostare i dati è il container che sembra non fare niente.
- **Non sa se il cluster serve a qualcosa.** Un `mongos` a cui non è stato registrato nessuno shard
  è `healthy` per Docker, risponde `ok=1 msg=isdbgrid` a `hello()`, elenca i database, e a una
  `find()` su una collezione inesistente risponde `[]` — indistinguibile da un cluster sano con la
  collezione vuota. Solo la **scrittura** distingue, con `ShardNotFound: No shards found`
  ([V-055](../Sources.md#v-055)). Un cluster senza shard non è rotto in modo visibile: è rotto in
  modo che si nota alla prima scrittura, e a una demo dal vivo la prima scrittura arriva dopo che si
  è già detto al pubblico che il cluster è pronto.

Il secondo punto ha deciso la forma dell'healthcheck: la sonda di `mongos` chiede se è **vivo**, non
se il cluster **serve**, perché il servizio che registra gli shard gira dentro `mongos` e lo aspetta
sano — una sonda più esigente bloccherebbe lo stack su se stesso
([ADR-0061](../Decision.md#adr-0061)).

### 2.4 Che cosa distingue davvero i tre ruoli

Dal di fuori i nove `mongod` e i due `mongos` sono lo stesso eseguibile con argomenti diversi, e i
modi di sbagliare il ruolo sono più di quanti sembri. Ne sono stati provati sei; cinque danno un
segnale, uno no ([V-057](../Sources.md#v-057)). Il controllo che sembrava ovvio — «il router non ha
un volume dati» — è **falso** come lo si scrive di solito: `docker inspect` mostra `/data/db`
montato anche su `mongos`, perché l'immagine dichiara `VOLUME /data/db` nel proprio Dockerfile e
Docker crea un volume **anonimo** su ogni container che ne nasce. Il discriminante vero è il volume
**nominato** ([V-058](../Sources.md#v-058)). La stessa proprietà dell'immagine, un anno di distanza
concettuale da qui, è la causa del guasto di [§7.2](#72-il-volume-cera-aveva-il-nome-giusto-ed-era-vuoto).

---

## 3. La shard key, che è la decisione che non si cambia

### 3.1 Si partiziona sull'hash del valore, non sul valore

La chiave della demo è `{_id: "hashed"}`. Non è la chiave giusta in assoluto — non esiste — è quella
giusta per questo dataset e per quello che la demo deve mostrare
([ADR-0064](../Decision.md#adr-0064)).

Gli `_id` di questi ventimila documenti sono gli interi 0, 1, 2, … 19 999: valori contigui, che
crescono di uno alla volta. I loro **hash** no: sono sparsi su tutto l'intervallo a 64 bit, e due
documenti consecutivi finiscono con altissima probabilità in chunk diversi, quindi su shard diversi.
Il manuale parte proprio dal problema che questo risolve: «Hashed keys are ideal for shard keys with
fields that change monotonically like ObjectId values or timestamps»
([S-066](../Sources.md#s-066)).

Misurato: **9860 documenti su `shard1rs`, 10140 su `shard2rs`** — 49,3 % contro 50,7 %
([V-058](../Sources.md#v-058)). Gli stessi due numeri escono su un altro database, con documenti di
forma diversa, purché la chiave e gli `_id` siano quelli ([V-061](../Sources.md#v-061)): la
ripartizione dipende dall'hash e dai confini dei chunk, non dal contenuto.

### 3.2 La chiave sbagliata, provata

Questa è la sezione per cui esiste il Blocco 3, e fino al 2 settembre 2026 questo repository la
citava senza averla mai vista accadere. Adesso è misurata.

Stessa collezione, stessa forma di documento, stessi `_id` interi crescenti. Cambia **solo** la
chiave: `{_id: 1}` invece di `{_id: "hashed"}`, cioè partizione per intervalli invece che per hash.

```
Alla distribuzione, su collezione VUOTA:
   chunk: 1        shard1rs   MinKey -> MaxKey

Dopo ventimila inserimenti:
   shard1rs: 20000 documenti
   shard2rs:  —  (non compare nella distribuzione)
   chunk: ancora 1
   migrazioni: 0
```

Il perché è geometrico, non statistico. In ogni cluster esiste un chunk il cui estremo superiore è
`MaxKey`, cioè «più grande di qualunque valore». Un `_id` che cresce sempre è sempre più grande di
tutti quelli già scritti, quindi **ogni** inserimento cade in quel chunk, che sta su **uno** shard:

> «If the shard key value is always increasing, all new inserts are routed to the chunk with
> `maxKey` as the upper bound. […] The shard containing that chunk becomes the bottleneck for write
> operations.» — [S-067](../Sources.md#s-067)

Lo stesso fatto, detto altrove in modo più brutale, come un tetto invece che come uno squilibrio:

> «If your shard key increases monotonically during an insert, then all inserted data goes to the
> last chunk in the collection, which will always end up on a single shard. **Therefore, the insert
> capacity of the cluster will never exceed the insert capacity of that single shard.**» —
> [S-071](../Sources.md#s-071)

**E adesso il pezzo che vale la slide.** Su quella collezione — ventimila documenti su uno shard e
zero sull'altro — `sh.balancerCollectionStatus()` risponde:

```
balancerCompliant: true
```

Il cluster considera **bilanciata** una distribuzione cento a zero. E ha ragione: la differenza fra
i due shard è 1,2 MB, la soglia perché il balancer si muova è 384 MB
([§4.3](#43-il-balancer-le-sue-due-mansioni-e-quella-che-qui-non-esercita-mai)). Non è un guasto
del balancer, è la sua specifica.

Quindi: l'errore non ha sintomo. Il cluster funziona, le scritture riescono, `sh.status()` mostra
due shard, e lo strumento che dovrebbe accorgersene conferma che va tutto bene. Quello che non si
vede è che **uno dei due shard non sta facendo niente**, e che la capacità di scrittura dell'intero
cluster è quella di una macchina sola — con in più il costo di tutte le altre.

**Una precisazione che il manuale fa e che va riportata**, altrimenti il difetto diventa una
caricatura: MongoDB il chunk caldo non lo lascia fermo dov'è. «To optimize data distribution, the
chunks that contain the global `maxKey` (or `minKey`) do not stay on the same shard. When a chunk is
split, the new chunk with the `maxKey` (or `minKey`) chunk is located on a different shard»
([S-067](../Sources.md#s-067)). Il collo di bottiglia **cambia nodo**; non sparisce. In ogni istante
gli inserimenti vanno tutti in un posto solo, e il cluster paga in più le migrazioni che servono a
spostare quel posto.

*Riserva sui numeri qui sopra:* lo shard che riceve tutto è lo **shard primario del database**, e
non è sempre lo stesso — in una ripetizione era `shard1rs`, in un'altra `shard2rs`. Quello che è
costante è che sia **uno solo** ([V-061](../Sources.md#v-061)).

### 3.3 Il prezzo dell'hash: le letture per intervallo

Non esiste una chiave che dia tutto. L'hash distribuisce le scritture e in cambio **perde la
località**: documenti con `_id` vicini stanno apposta lontani.

> «Post-hash, documents with "close" shard key values are unlikely to be on the same chunk or
> shard - the `mongos` is more likely to perform Broadcast Operations to fulfill a given ranged
> query. `mongos` can target queries with equality matches to a single shard.» —
> [S-066](../Sources.md#s-066)

Misurato con tre `explain()` attraverso il router, contando gli shard interrogati
([V-058](../Sources.md#v-058)):

| Query | Shard interrogati |
|---|---|
| `db.ordini.find({_id: 42})` | **1** — `shard2rs` |
| `db.ordini.find({_id: {$gte: 100, $lt: 200}})` | **2** — broadcast |
| `db.ordini.find({citta: "Ancona"})` | **2** — broadcast |

La seconda riga è il prezzo, ed è controintuitiva: è un intervallo **sulla chiave stessa**, e
nonostante questo va a tutti gli shard. La terza è il caso normale di un campo qualunque e serve da
controprova, perché senza si potrebbe credere che il broadcast dipenda dall'intervallo e non
dall'hash.

In una frase: **si sceglie fra distribuire le scritture e tenere vicine le letture contigue.** Non
si ottengono tutte e due.

### 3.4 La cardinalità è un tetto, non una preferenza

> «The cardinality of a shard key determines the maximum number of chunks the balancer can create.»
> — [S-067](../Sources.md#s-067)

È il conto da rifare su qualunque campo candidato, e nel dataset della demo squalifica subito quello
che sarebbe il più leggibile. Il campo `citta` ha **dieci** valori distinti: dieci chunk al massimo
per l'intero cluster, e quindi al massimo dieci shard utili. Il manuale fa lo stesso conto su un
campo `continent` da sette valori — «this constrains the number of effective shards in the cluster
to `7` as well - adding more than seven shards would not provide any benefit» — e con dieci al posto
di sette la conclusione non cambia.

Una chiave leggibile e sbagliata è più pericolosa di una chiave illeggibile e giusta, perché supera
la revisione del codice.

### 3.5 E l'hash non è una garanzia

> «A shard key that does not change monotonically does not, on its own, guarantee even distribution
> of data across the sharded cluster. **The cardinality and frequency of the shard key also
> contribute to the distribution of the data.**» — [S-067](../Sources.md#s-067)

Nella demo distribuisce perché gli `_id` sono ventimila valori distinti, uno per documento:
cardinalità massima e frequenza uniforme, cioè le due condizioni che la frase mette accanto. Su un
campo con dieci valori l'hash non salverebbe niente — distribuirebbe dieci gruppi invece di dieci
intervalli, e i gruppi resterebbero dieci.

### 3.6 Perché `_id`, che non è la risposta giusta in generale

Perché è l'unico campo garantito presente e unico in ogni documento, e perché così il dataset resta
identico a quello degli altri due stack — che è la condizione per poter confrontare le tre
architetture in `feature/04`. È una scelta di laboratorio, e il manuale non l'avalla: insiste sul
verso opposto, cioè che la chiave si scelga sul **modo in cui si interroga** la collezione. Detto
per quello che è ([ADR-0064](../Decision.md#adr-0064)).

---

## 4. Chunk e balancer

### 4.1 I quattro chunk non emergono: sono geometria — e non restano quattro

Distribuire una collezione **vuota** con una chiave hashed fa una cosa che distribuire una collezione
piena non fa: MongoDB crea i chunk in anticipo e li spalma sugli shard prima che esista un documento.
«By default, the operation creates 2 chunks per shard and migrates across the cluster»
([S-066](../Sources.md#s-066)). Due chunk per shard, due shard: **quattro**. Non è un numero
emergente, è un valore predefinito documentato — e infatti è lo stesso numero che lo spike aveva
misurato senza sapere che fosse un predefinito.

I confini, letti da `config.chunks` e riportati in decimale ([V-061](../Sources.md#v-061)):

```
shard2rs   MinKey                       ->  -4 611 686 018 427 387 902     (-2^62 + 2)
shard2rs   -4 611 686 018 427 387 902   ->                            0
shard1rs                             0  ->   4 611 686 018 427 387 902     (+2^62 - 2)
shard1rs    4 611 686 018 427 387 902   ->  MaxKey
```

È lo spazio dei valori hash — un intero con segno a 64 bit — tagliato in **quattro parti uguali**,
due per shard. La distribuzione 49,3 / 50,7 non è il risultato di un bilanciamento: è il risultato
di venti­mila hash che cadono in quattro caselle decise prima.

**Ma quattro è un numero con una scadenza.** Spegnere lo stack e riaccenderlo sugli stessi volumi —
`make down-03 && make up-03`, nessun dato toccato — e i chunk diventano **due**:

```
shard2rs   MinKey  ->  0
shard1rs        0  ->  MaxKey
```

Non è un guasto e non è una migrazione: è la seconda cosa che il balancer sa fare, ed è raccontata
in [§4.3](#43-il-balancer-le-sue-due-mansioni-e-quella-che-qui-non-esercita-mai). Notare quale
confine è sopravvissuto: i due interni sono spariti, **lo zero — quello fra i due shard — no.**

### 4.2 Prima si distribuisce, poi si riempie

L'ordine non è indifferente, ed è il motivo per cui nel lab `sh.shardCollection()` viene **prima**
dell'inserimento. Distribuendo una collezione già piena, «the sharding operation creates an initial
chunk to cover all of the shard key values», e poi «the balancer moves ranges of the initial chunk
when it needs to balance data» ([S-066](../Sources.md#s-066)): un chunk solo, e si aspetta il
balancer. La stessa raccomandazione, dal lato delle scritture di massa: «If your sharded collection
is empty and you are not using hashed sharding for the first key of your shard key, then your
collection has only one initial chunk, which resides on a single shard»
([S-071](../Sources.md#s-071)).

Quel «one initial chunk» è esattamente ciò che è stato contato distribuendo una collezione vuota con
`{_id: 1}` in [§3.2](#32-la-chiave-sbagliata-provata).

### 4.3 Il balancer, le sue due mansioni, e quella che qui non esercita mai

Prima di tutto una distinzione che quasi tutte le spiegazioni saltano, questa pagina compresa fino
al giorno dopo averla scritta: **«balancer» e «migrazione» non sono la stessa parola.** Dalla 7.0 il
balancer fa due mestieri — sposta dati fra shard, e **fonde** chunk contigui che stanno già sullo
stesso shard. Il primo ha una soglia di squilibrio; il secondo no. In questo laboratorio il primo non
scatta mai e il secondo sì, quattro secondi dopo l'accensione.

Poi tre fatti, nell'ordine in cui vengono dimenticati.

**Dove gira.** «The balancer runs on the primary of the config server replica set (CSRS)»
([S-070](../Sources.md#s-070)). Non su `mongos`, che è dove quasi tutti lo collocano.

**Se è acceso.** «By default, the balancer process is always enabled.» Lo si vede già su un cluster
senza nemmeno uno shard: `sh.status()` riporta `Currently enabled: yes`
([V-055](../Sources.md#v-055)).

**Quando si muove.** Solo oltre una soglia, e la soglia è grossa:

> «A collection is considered balanced if the difference in data between shards (for that
> collection) is less than three times the configured range size for the collection. For the default
> range size of `128MB`, two shards must have a data size difference for a given collection of at
> least `384MB` for a migration to occur.» — [S-070](../Sources.md#s-070)

Nella demo, i numeri veri ([V-061](../Sources.md#v-061)):

```
lab.ordini      dataSize     2 437 499 byte   (avgObjSize 121)
   shard1rs                  1 201 545 byte
   shard2rs                  1 235 954 byte
   differenza                   34 409 byte

soglia perché il balancer intervenga   384 MB  =  402 653 184 byte
rapporto                                circa   1 a 11 700

config.changelog: 6 eventi in tutto — 2 addShard, 2 shardCollection, 2 setClusterParameter
migrazioni (moveChunk | moveRange): 0
```

**Il balancer, in questa demo, non sposta un solo documento.** È acceso, guarda, e la differenza è
undicimila volte sotto la soglia. Raccontare la demo dicendo «e qui il balancer ridistribuisce»
resta una didascalia falsa su una fotografia vera.

**Quello che invece fa, e si vede.** Al riavvio i quattro chunk diventano due
([§4.1](#41-i-quattro-chunk-non-emergono-sono-geometria--e-non-restano-quattro)), e il registro del
cluster dice chi, quando e da dove:

```
12:34:16.530Z   merge   lab.ordini   server cfg1:27017   owningShard shard1rs   numChunks 2
12:34:31.450Z   merge   lab.ordini   server cfg1:27017   owningShard shard2rs   numChunks 2

container dei dati avviati alle 12:34:12.735Z   →  la prima fusione dopo 3,8 secondi
router avviato alle          12:34:22.418Z      →  sei secondi DOPO la prima fusione
```

Quel `server: cfg1:27017` è la conferma migliore che questa pagina abbia della riga di
[S-070](../Sources.md#s-070) sul primario dei config server: non una citazione, un campo scritto dal
cluster. E la fusione è avvenuta prima che il router esistesse, il che chiude la questione su chi
bilanci.

Si chiama **AutoMerger**, è nuova nella 7.0, e il manuale la descrive senza giri di parole: «When
the AutoMerger runs, it squashes together all sequences of mergeable chunks for each shard of each
collection» ([S-072](../Sources.md#s-072)). *Mergeable* vuol dire contigui, **dello stesso shard**,
non jumbo, e con la storia abbastanza vecchia da poter essere buttata. Ecco perché lo zero
sopravvive: separa due shard diversi, e non è fondibile per definizione.

Perché al primo giro non era successo niente e al riavvio sì: «unless explicitly disabled, the
AutoMerger **starts the first time the balancer is enabled** and pauses for the next
`autoMergerIntervalSecs`» ([S-072](../Sources.md#s-072)). Alla prima accensione i chunk avevano nove
secondi di vita ed erano troppo freschi; l'intervallo successivo non è mai scaduto perché lo stack è
stato spento prima; al riavvio il balancer è stato abilitato «per la prima volta» un'altra volta, e
stavolta i chunk avevano quasi due ore ([V-062](../Sources.md#v-062)).

Un effetto collaterale che il nome non lascia intuire: **`sh.stopBalancer()` spegne anche
l'AutoMerger.** «Starting in MongoDB 7.0, stopping the balancer also disables the AutoMerger for the
sharded cluster», e simmetricamente per `sh.startBalancer()` ([S-073](../Sources.md#s-073)). Su
questo laboratorio vuol dire che l'unico comando che sembra innocuo — fermare un balancer che tanto
non migra — è quello che ferma l'unica cosa che il balancer sta facendo.

Che cosa costerebbe, se si muovesse: «Range migrations carry some overhead in terms of bandwidth and
workload», e il momento più caro è nominato con precisione — «MongoDB briefly pauses all application
reads and writes to the collection being migrated to on the source shard before updating the config
servers with the range location» ([S-070](../Sources.md#s-070)). Con due shard, una migrazione alla
volta: «for a sharded cluster with *n* shards, MongoDB can perform at most *n/2* (rounded down)
simultaneous migrations».

*Riserva:* la soglia dei 384 MB non è mai stata **superata** in nessuna misura di questo repository.
È provato che sotto la soglia il balancer sta fermo; non è provato che sopra si muova, né quanto ci
metta — il manuale non dà nessuna frequenza di sondaggio ([S-070](../Sources.md#s-070), «cosa non
afferma»).

---

## 5. La trappola che colpisce chi ha scelto bene

C'è un modo di perdere quasi tutto il vantaggio di una shard key corretta senza toccare la shard
key. È il predefinito di `insertMany`.

> «Bulk write operations execute either serially (*ordered*) or in any order (*unordered*).
> **By default, operations are ordered and stop on the first error.** Unordered operations continue
> despite errors and may execute in parallel, making them typically faster for sharded collections.»
> — [S-071](../Sources.md#s-071)

Il manuale dice *typically faster* e non dà nessun numero. Il numero, su questo stack, è questo —
quattro casi, due giri, stessi ventimila documenti ([V-061](../Sources.md#v-061)):

| Chiave | `ordered` | Giro 1 | Giro 2 |
|---|---|---|---|
| hashed | `true` *(predefinito)* | **11 328 ms** | **9 393 ms** |
| hashed | `false` | 336 ms | 408 ms |
| ranged (monotona) | `true` | 340 ms | 192 ms |
| ranged (monotona) | `false` | 248 ms | 1 947 ms |

Il costo **non è la chiave hashed**: è la chiave hashed *insieme* al lotto ordinato. Con
`ordered: false` le due chiavi costano uguale. Il meccanismo sta in una parola del manuale:
«`mongos` attempts to send the writes to multiple shards **simultaneously**»
([S-071](../Sources.md#s-071)) — cosa che con un lotto ordinato non può fare, perché mantenere
l'ordine fra shard diversi vuol dire aspettare. E con una chiave hashed lo shard di destinazione
cambia quasi a ogni documento.

Perché è la trappola peggiore delle tre di questa pagina: **colpisce chi ha fatto la scelta giusta.**
Si distribuisce bene, non si tocca il codice di caricamento che funzionava sul replica set, e le
scritture rallentano di un ordine di grandezza senza un errore, senza un avviso, e senza che
`sh.status()` mostri niente di strano.

Il seed di questo laboratorio scrive `ordered: false` dal primo giorno, per allineamento con gli
altri due stack (`docker/03-sharded/init/30-dati-demo.js`, riga 296). Oggi si sa **perché** era la
riga giusta.

*Riserve:* il valore `1 947 ms` dell'ultima riga è fuori scala rispetto agli altri tre valori ranged,
tutti fra 192 e 340 ms — è rumore della macchina, ed è riportato invece che tolto perché toglierlo
sarebbe scegliere i dati. Tutti i tempi sono esecuzioni singole su un portatile con Docker Desktop,
non medie. Il fattore vale per **due** shard e documenti da 121 byte medi.

---

## 6. Che cosa cambia per il client

### 6.1 Si entra dal router, e solo dal router

> «You must connect to a mongos router to interact with any collection in the sharded cluster. This
> includes sharded *and* unsharded collections. **Clients should *never* connect to a single shard
> to perform read or write operations.**» — [S-069](../Sources.md#s-069)

Nel lab la regola **non** è più resa difficile da violare, e vale la pena sapere perché. Gli utenti
del cluster stanno sui config server, e fino a [ADR-0071](../Decision.md#adr-0071) le loro
credenziali in diretta su `shard1a` rispondevano `Authentication failed`
([V-058](../Sources.md#v-058)): chi sbagliava indirizzo non entrava. Adesso ogni shard ha un
amministratore locale con le stesse credenziali, quindi entra, e non ottiene un errore ma **metà**
dei documenti — 9 860 su 20 000 ([V-067](../Sources.md#v-067)). Il chiavistello era l'effetto
collaterale di uno shard senza utenti, cioè di una configurazione che il manuale vieta
([V-064](../Sources.md#v-064)): toglierlo era giusto, e lascia scoperto ciò che solo questa regola
copriva.

La stringa di connessione, per il resto, è quella di sempre: «You can connect to a `mongos` the same
way you connect to a `mongod`».

### 6.2 Mirata o in broadcast, e lo decide la query

È la tabella di [§3.3](#33-il-prezzo-dellhash-le-letture-per-intervallo), e in esercizio si riassume
in una regola: una query che porta la shard key con un'uguaglianza va a **uno** shard; tutto il resto
va a **tutti**. Il manuale avverte del costo con parole sue: se le query non includono la chiave o
il prefisso di una chiave composta, «`mongos` performs a broadcast operation, querying *all* shards
in the sharded cluster. These scatter/gather queries can be long running operations»
([S-069](../Sources.md#s-069)).

Detto al contrario, ed è il modo utile di dirlo: **la shard key non si sceglie per distribuire i
dati, si sceglie per non fare broadcast.** La distribuzione è la parte facile.

### 6.3 Le collezioni non distribuite, e lo shard primario

Distribuire è un'operazione per collezione, quindi in un database convivono i due mondi:

> «A database can have a mixture of sharded and unsharded collections. Sharded collections are
> partitioned and distributed across the shards in the cluster. **Unsharded collections are stored
> on a primary shard. Each database has its own primary shard.**» — [S-069](../Sources.md#s-069)

Misurato: una collezione creata al volo attraverso il router, scritta con `w: "majority"` e riletta,
**non** risulta distribuita e vive intera su `shard2rs`, che è lo shard primario del database `lab`
([V-058](../Sources.md#v-058)). Non è un errore: è la definizione. Ma spiega un'esperienza comune —
«ho uno sharded cluster e i dati stanno tutti su un nodo» — che nella maggior parte dei casi
significa che nessuno ha mai chiamato `shardCollection()`.

### 6.4 La disponibilità è parziale, e lo è per query

Ripresa da [§1.2](#12-che-cosa-si-guadagna-in-tre-voci) perché qui è il client a sentirne l'effetto:
perso uno shard, il cluster «can continue to perform partial reads and writes»
([S-069](../Sources.md#s-069)). La fonte si ferma lì; il resto è misurato fermando un membro con
`make guasto-03` ([V-097](../Sources.md#v-097)). La query che tocca solo lo shard sano risponde in
**1 s**. Quella che tocca lo shard perduto e il conteggio totale falliscono tutte e due, con lo
stesso errore:

```text
FailedToSatisfyReadPreference: Could not find host matching read preference
{ mode: "primary" } for set shard1rs
```

Il client non riceve un risultato mutilato: riceve un errore, che nomina lo shard mancante. Lo riceve
dopo **16 s**, ed è la parte che sorprende — sono il tempo che il router impiega a smettere di
sperare in un primario che non c'è. Un'applicazione che chiama in sincrono se li prende tutti.

Un caso resta ragionato e non provato: una query in broadcast i cui documenti stiano **tutti** sullo
shard vivo. Deve fallire per costruzione — il router la manda a tutti proprio perché non sa dove
siano i documenti — ma questa pagina non l'ha eseguita, e la differenza fra «deve» e «l'ho visto»
qui si dichiara.

Il replica set ha una disponibilità del cluster; lo sharded cluster ha una disponibilità **della
singola query**, e un'applicazione va scritta sapendolo.

---

## 7. Il file Compose, i due punti che non si indovinano

Il file è commentato per esteso e non viene ripetuto qui riga per riga
([ADR-0068](../Decision.md#adr-0068)). Restano due cose che si capiscono solo guardandolo.

### 7.1 La catena dei sei anelli, e la sentinella

Undici container, e uno solo comando: `make up-03`. Perché `up --wait` sia **onesto** — cioè torni
quando il cluster serve e non quando i processi sono accesi — la catena è dichiarata per intero:

```
keyfile-init  →  cfg-init · shard1-init · shard2-init  →  mongos  →  add-shard  →  seed  →  up-03
```

L'ultimo anello, `up-03`, è un servizio che non fa niente: esiste solo per dipendere da tutti gli
altri e dare a `--wait` qualcosa da aspettare ([ADR-0062](../Decision.md#adr-0062),
[V-056](../Sources.md#v-056)). Quando `make up-03` torna, i due shard sono registrati e `lab.ordini`
è distribuita e piena. È una differenza reale rispetto allo stack 02, che di comandi ne vuole due.

### 7.2 Il volume c'era, aveva il nome giusto, ed era vuoto

Il guasto migliore che questo branch abbia prodotto, e vale come lezione su dove viva lo stato.

Accendere, spegnere **senza** cancellare i volumi, riaccendere: il secondo avvio falliva. Il
messaggio d'errore accusava la persona sbagliata — parlava di un database `lab` di troppo su uno
shard — mentre la riga che spiegava tutto stava due righe sopra: «shard già registrati: **nessuno**»,
su un cluster che al giro prima ne aveva due.

Contato ([V-060](../Sources.md#v-060)):

```
dati-cfg1       0 file
dati-cfg2       0 file
dati-shard1a   83 file
dati-shard2a   76 file
```

I config server avevano il loro volume nominato, montato su `/data/db` come tutti gli altri nodi, e
dentro non c'era niente. Due fatti si sommavano, e nessuno dei due è un errore: l'entrypoint
dell'immagine, quando fra gli argomenti trova `--configsvr`, porta il dbpath predefinito a
`/data/configdb`; e l'immagine dichiara `VOLUME` su **entrambe** le cartelle dei dati, quindi Compose
soddisfa quella non montata con un volume **anonimo**, che `down` abbandona e che il `up` successivo
rifà vuoto.

La riparazione è una riga — `--dbpath /data/db` dichiarato sui tre config server — più due guardie
che avrebbero dovuto prenderlo prima: una regola statica in `tools/check_stack.py` che confronta il
dbpath vero con la destinazione del volume, e il controllo dello smoke, che si accontentava
dell'**esistenza** del volume nominato invece di chiedere se il processo ci scrivesse dentro
([ADR-0067](../Decision.md#adr-0067)).

---

## 8. Provarlo in due minuti

```bash
# Prima volta soltanto: il file con la password, che non sta nel repository
cp docker/03-sharded/.env.example docker/03-sharded/.env   # poi riempire PASSWORD_AMMINISTRATORE

# Accendere: UN comando, e quando torna il cluster è pieno e distribuito
make up-03                       # ~25 s, undici container

# La prova completa dello stack: 62 controlli
make smoke-03

# Chi sono gli shard, e com'è messa la collezione
docker exec -it sh-mongos mongosh -u admin --authenticationDatabase admin
#   sh.status()
#   db.getSiblingDB("admin").aggregate([{$shardedDataDistribution: {}}])
#   db.getSiblingDB("lab").ordini.getShardDistribution()
#   sh.balancerCollectionStatus("lab.ordini")

# Il baratto della chiave, in tre explain: uno shard, poi tutti, poi tutti
#   db.ordini.find({_id: 42}).explain().queryPlanner.winningPlan.shards.length
#   db.ordini.find({_id: {$gte: 100, $lt: 200}}).explain().queryPlanner.winningPlan.shards.length

# Tre membri per insieme invece di uno (18 container). Sono DUE cose, non una:
# scommentare le tre righe MEMBRI_* nel file .env, e azzerare lo stack prima di
# riavviarlo. Gli init non riconfigurano un replica set che esiste già: su uno
# stack acceso in «palco» il cambio di profilo lascerebbe i set com'erano e i
# container nuovi fuori dalla replica. Dalla correzione di ADR-0077 non è più
# silenzioso — l'anello esce 6 e nomina i membri — ma il modo di farlo resta
# questo.
make reset-03
make up-03 PROFILO=completo

# Rimettere i dati come all'inizio dopo aver giocato
make reset-demo-03

# Spegnere conservando i dati, oppure azzerare tutto
make down-03
make reset-03
```

---

## Cosa questa pagina non dice

- **Non mostra una migrazione.** La soglia è 384 MB e la demo ne muove 2,4: è provato che sotto la
  soglia il balancer non sposta niente, non che sopra si muova ([V-061](../Sources.md#v-061)).
  Vederlo richiederebbe un dataset di scala diversa da quella di un portatile. La **fusione** invece
  si vede, ed è l'altra metà del mestiere ([§4.3](#43-il-balancer-le-sue-due-mansioni-e-quella-che-qui-non-esercita-mai)).
- **Non misura ogni quanto l'AutoMerger torni a girare.** Che esista un intervallo è del manuale;
  quanto valga su questo deployment non è stato letto, perché il cluster non espone il parametro
  ([V-062](../Sources.md#v-062), riserva *a*). Ed è osservato dopo un riavvio, che rende il riavvio
  sufficiente e non dimostra che fosse necessario.
- **Non copre le zone.** Sono il modo di legare intervalli di shard key a shard specifici, tipico
  dei cluster su più data center. Lo stack non ne ha.
- **Non copre il resharding.** È la via d'uscita da una shard key sbagliata dalla 5.0, ed è
  nominata in [§1](#1-che-problema-risolve-e-quando-non-serve) solo per non far credere che la
  scelta sia eterna. Non è stata provata.
- ~~**Non usa `analyzeShardKey`.** Introdotto nella 7.0, sarebbe lo strumento giusto per scegliere
  una chiave in un caso vero, e richiede un campione di query reali che una demo con dati generati
  non ha ([S-067](../Sources.md#s-067)).~~ **Saldato:** [V-081](../Sources.md#v-081) — il comando è
  stato eseguito su `lab.ordini`, e dà il verdetto sulla chiave in uso più due rifiuti istruttivi
  (`{stato: 1}` «può fare solo **6** chunk», `{citta: 1}` undici). Il campione di query reali si
  fabbrica: `configureQueryAnalyzer` più il carico dell'applicazione, e le distribuzioni compaiono.
  Le due condizioni che il comando non dichiara sono che una chiave candidata **senza indice**
  riceve un `ok: 1` **privo** di `keyCharacteristics` invece di un errore, e che l'analizzatore va
  acceso **prima** del traffico, con due ritardi da rispettare. Resta fuori da `mongolab`, perché
  risponde una volta sola e l'applicazione emette flussi
  ([ADR-0110](../Decision.md#adr-0110)).
- ~~**Non misura le prestazioni sotto carico.** Tutti i numeri qui sono a riposo, con un solo
  scrittore. Il confronto fra le tre architetture ha senso sotto carico controllato, cioè con
  l'applicazione Python di `feature/04`, e prima di allora sarebbe aria.~~ **Saldato.**
  [V-079](../Sources.md#v-079): il cluster scrive **5,0 volte più piano** dello standalone, e 1,23
  volte più veloce del replica set. Il secondo numero non è un merito dello sharding: in questo lab
  ogni shard ha **un solo membro**, quindi la maggioranza si raggiunge da sé, e il cluster paga il
  salto in più di `mongos` senza pagare la replica. La riserva sul ferro vale qui più che altrove —
  undici container sullo stesso portatile, e mezza CPU a shard
  ([ADR-0111](../Decision.md#adr-0111)).
- **Non prova la perdita di uno shard.** La disponibilità parziale di
  [§6.4](#64-la-disponibilità-è-parziale-e-lo-è-per-query) è citata dal manuale, non misurata qui.
- **Non copre i chunk jumbo né il `chunkSize` diverso dal predefinito.** Il lab lascia i 128 MB e li
  legge invece di supporli.
- **Non copre le transazioni distribuite** né il comportamento dei change stream su più shard.
- **I numeri valgono per undici container sullo stesso portatile.** La forma dei fenomeni si
  trasferisce; le cifre no. In particolare il fattore venticinque di
  [§5](#5-la-trappola-che-colpisce-chi-ha-scelto-bene) dipende dal numero di shard, e con più shard
  può solo peggiorare.

---

**Decisioni correlate:** [ADR-0068](../Decision.md#adr-0068) (la forma di questa pagina),
[ADR-0064](../Decision.md#adr-0064) (la shard key della demo),
[ADR-0065](../Decision.md#adr-0065) (i dati come sesto anello della catena),
[ADR-0062](../Decision.md#adr-0062) (un comando solo, e la sentinella),
[ADR-0061](../Decision.md#adr-0061) (che cosa chiede la sonda di `mongos`),
[ADR-0069](../Decision.md#adr-0069) (la correzione sul balancer, e l'AutoMerger),
[ADR-0067](../Decision.md#adr-0067) (dove scrivono i config server),
[ADR-0066](../Decision.md#adr-0066) (con quale profilo si spegne),
[ADR-0060](../Decision.md#adr-0060) (quanti membri ha un insieme),
[ADR-0063](../Decision.md#adr-0063) (che cosa la guardia statica deve bocciare),
[ADR-0014](../Decision.md#adr-0014) (il keyfile fuori dal repository),
[ADR-0021](../Decision.md#adr-0021) (nomi host, mai indirizzi),
[ADR-0071](../Decision.md#adr-0071) (l'amministratore per shard, che apre la porta di §2.2),
[ADR-0072](../Decision.md#adr-0072) (le misure che una decisione invalida si riscrivono subito),
[ADR-0110](../Decision.md#adr-0110) (perché `analyzeShardKey` resta fuori dall'applicazione),
[ADR-0111](../Decision.md#adr-0111) (il confronto si pubblica in coppia con la riserva del ferro).

**Fonti:** [S-008](../Sources.md#s-008), [S-024](../Sources.md#s-024), [S-025](../Sources.md#s-025),
[S-066](../Sources.md#s-066), [S-067](../Sources.md#s-067), [S-069](../Sources.md#s-069),
[S-070](../Sources.md#s-070), [S-071](../Sources.md#s-071), [S-072](../Sources.md#s-072),
[S-073](../Sources.md#s-073), [V-052](../Sources.md#v-052),
[V-054](../Sources.md#v-054), [V-055](../Sources.md#v-055), [V-056](../Sources.md#v-056),
[V-057](../Sources.md#v-057), [V-058](../Sources.md#v-058), [V-060](../Sources.md#v-060),
[V-061](../Sources.md#v-061), [V-062](../Sources.md#v-062), [V-063](../Sources.md#v-063),
[V-064](../Sources.md#v-064), [V-067](../Sources.md#v-067),
[V-079](../Sources.md#v-079), [V-081](../Sources.md#v-081)
