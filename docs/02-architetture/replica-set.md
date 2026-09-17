# Replica set a tre membri

Tre processi `mongod`, tre dischi, un dato solo scritto tre volte. La pagina dell'[istanza
singola](standalone.md) si chiude con una domanda — quanto costa il tempo in cui non risponde
nessuno, e quanto costa il dato scritto negli ultimi cento millisecondi — e questa pagina è la
risposta: **cosa si ottiene** in più, e **a quale prezzo**.

Non un prezzo in astratto. Ogni numero di questa pagina è stato misurato su questo stack, su un
portatile, e porta accanto la verifica che lo ha prodotto e la riserva che lo qualifica. La
decisione di scriverla così è [ADR-0046](../Decision.md#adr-0046).

Un avviso in apertura, perché è la sorpresa più comune: **quasi tutto il tempo di un failover non è
il failover.** L'elezione dura sei millisecondi. I dieci secondi che si vedono sono l'attesa prima
di cominciarla, e sono una scelta di progetto.

---

## 1. Perché i membri sono tre

### 1.1 La sottrazione

È l'unica cosa di questa pagina che si dimostra senza accendere niente.

Un replica set decide per **maggioranza dei membri configurati**. La maggioranza di tre è due:
finché due membri si vedono, esiste un primario e si scrive. Perderne uno lascia due, cioè ancora
una maggioranza. Quindi **tre membri tollerano un guasto**.

Con due membri la maggioranza sarebbe ancora due — la metà più uno di due fa due — e perderne uno
lascerebbe uno solo, che non è una maggioranza. Un set a due membri tollera quindi **zero** guasti
in scrittura, pur costando il doppio di un'istanza singola. È il motivo per cui i membri sono tre, e
non ha niente a che vedere con le prestazioni né con il numero di copie dei dati.

La sottrazione si vede in funzione fermando **due** membri su tre. Il superstite resta vivo, sano,
raggiungibile, con tutti i dati, e dopo poco più di nove secondi si retrocede da solo a `SECONDARY`
([V-031](../Sources.md#v-031)). La riga di log con cui lo fa dice il perché meglio di qualunque
parafrasi:

```
id=21809  REPL  Can't see a majority of the set, relinquishing primary
```

Non «ho perso la connessione». *Non vedo una maggioranza, quindi cedo.* Da quell'istante le
scritture rispondono `NotWritablePrimary` e le letture continuano — su chi le sa chiedere, ed è il
§3.4.

### 1.2 Le priorità: chi comanda è prevedibile

I tre membri non sono pari. La configurazione assegna `priority: 2` al primo e `priority: 1` agli
altri due, e non è cosmetica: rende **prevedibile** chi sarà primario. In sala questo vale più di
quanto sembri, perché una demo in cui il primario è ogni volta un membro diverso costringe chi parla
a guardare lo schermo prima di dire una frase.

L'effetto si vede al rientro: dopo un failover, quando il membro a priorità 2 torna su, il set gli
restituisce il ruolo da solo. Non è una preferenza estetica del lab — è la stessa proprietà su cui
si appoggia `./tools/reset-demo.sh 02`, che dichiara lo stack pronto **solo** quando `mongo-rs-1` è
tornato primario ([V-031](../Sources.md#v-031)).

### 1.3 Il prezzo, in numeri

| Voce | Istanza singola | Replica set a tre membri |
|---|---:|---:|
| processi `mongod` | 1 | 3 |
| memoria del bilancio del lab | 1.024 MiB | **2.304 MiB** (768 × 3) |
| copie del dato | 1 | 3 |
| porte pubblicate | 27017 | 27021, 27022, 27023 |
| servizi nel file Compose | 1 | 5 (tre membri più due one-shot) |
| autenticazione | assente per scelta | **obbligatoria**: il keyfile la porta con sé |

L'ultima riga è quella che sorprende chi arriva dallo stack 01. Attivare `--keyFile` per far
riconoscere i membri fra loro attiva **anche** l'autenticazione dei client: non è una scelta di
sicurezza che si può rimandare, è un requisito di funzionamento, ed è la ragione per cui questo
stack ha una catena di inizializzazione mentre il precedente parte e basta
([ADR-0040](../Decision.md#adr-0040)).

---

## 2. Le elezioni, cronometrate

### 2.1 Le due morti di un primario non costano lo stesso

Il gesto con cui tutti simulano un guasto — `docker kill` — costa **venti volte** più di una
chiusura ordinata, e nel verso opposto all'intuizione:

| Come muore il primario | Tempo fino al nuovo primario | Il container |
|---|---:|---|
| `docker kill` (SIGKILL) | **9 812 / 10 619 / 10 943 ms** | resta `exited`, `RestartCount=0` |
| `db.shutdownServer()` | **574 / 480 / 486 ms** | torna su da sé, `RestartCount` avanza |

Tre esecuzioni per riga, [V-029](../Sources.md#v-029). La differenza sta in una parola: con lo
`shutdown` il primario **avvisa**. Comunica agli altri che se ne va, e l'elezione parte subito. Con
il `kill` non avvisa nessuno, e gli altri devono **accorgersene** — che è la cosa lenta.

Da qui discende anche il comportamento di `restart: unless-stopped`, che sorprende sempre: dopo un
`docker kill` il container **non** riparte, perché per il demone quella fermata l'ha voluta un
umano. Dopo uno `shutdown` interno sì. Il dettaglio è nella
[voce 6 delle trappole](trappole-mongodb-in-docker.md#t-06), e la decisione di dirlo invece di
fingere è [ADR-0034](../Decision.md#adr-0034).

### 2.2 L'elezione dura sei millisecondi

Il log di un'elezione vera, letto sul nodo **eletto** — non sull'osservatore, che registra il
proprio voto e nient'altro ([V-030](../Sources.md#v-030)):

```
19:01:47.369  id=21216    Member is now in state DOWN        ← 0,3 s dopo il colpo

     ... nove secondi, e diciannove «Heartbeat failed after max retries» ...

19:01:56.558  id=4615652  Starting an election, since we've seen no PRIMARY
                          in election timeout period
                          electionTimeoutPeriodMillis: 10000
19:01:56.564  id=21450    Election succeeded, assuming primary role
```

Fra la decisione di eleggere e il nuovo primario passano **sei millisecondi**. I dieci secondi non
sono l'elezione: sono l'attesa **prima** di cominciarla, e il set non è affatto lento ad accorgersi
— se ne accorge in tre decimi di secondo, con `Connection refused` scritto nell'attributo, e poi
*decide di non fare niente*. Un membro irraggiungibile per un istante non è un membro morto, e
indire un'elezione a ogni singhiozzo di rete costerebbe più di quello che salva.

Il manuale dà il meccanismo: i membri si scambiano battiti «every two seconds», e se un membro non
risponde entro dieci secondi gli altri lo marcano inaccessibile
([S-044](../Sources.md#s-044)). Nell'intervallo, testuale, «the replica set cannot process write
operations until the election completes successfully».

### 2.3 La maggioranza persa

La terza scena è quella del §1.1, cronometrata: si fermano **due** membri e si misura quanto ci
mette il superstite a retrocedersi.

```
9 364 · 9 136 · 9 331 · 9 334 · 9 327 · 9 316  ms      mediana 9 329 ms
```

Sei esecuzioni, [V-031](../Sources.md#v-031). Il cronometro gira **dentro** il primario, perché
nessun altro nodo può datare quella retrocessione: non ne resta nessuno.

**Perché nove e non dieci**, ed è la riserva da dire insieme al numero: `electionTimeoutMillis` vale
10 000 ms, ma si conta dall'**ultimo battito ricevuto**, non dal colpo. I battiti vanno ogni 2 000
ms, quindi il colpo cade in un punto qualunque di quella finestra e la misura vale fra **8 e 10
secondi**. Chi rifà la scena e legge 8,7 non ha uno stack diverso: ha colpito in un altro punto
della finestra.

Da lì nessuno rialza il superstite, **ed è il punto della scena**: non esiste nessuno che possa
eleggerlo. Si torna indietro riavviando i membri fermati, e il rientro costa altri 9–12 secondi.

### Le tre scene, con i comandi

| Scena | Comando | Quanto costa | Che cosa insegna |
|---|---|---:|---|
| Il primario ucciso | `make failover-02` | ~10 s | il set regge, e la lentezza è attesa deliberata |
| Il primario che saluta | `make failover-02-termina` | ~0,5 s | il gesto brutale è quello lento |
| La maggioranza persa | `make failover-02-maggioranza` | ~9,3 s | quanti guasti regge: **uno** |

Gli script rimisurano a ogni esecuzione e stampano i numeri che ottengono, non quelli scritti qui
([ADR-0044](../Decision.md#adr-0044), [ADR-0045](../Decision.md#adr-0045)). Se in sala una scena
dura il doppio, si vede sullo schermo invece di essere smentita da una slide. Dopo le scene,
`./tools/reset-demo.sh 02` rimette in piedi lo stack senza ricostruirlo.

---

## 3. Write concern e read preference, che sono una coppia

Si trovano quasi sempre in due capitoli diversi. Sono i due capi dello stesso scambio: da una parte
si decide **quante copie devono confermare prima che una scrittura sia mia**, dall'altra **quanto
vecchio può essere il dato che leggo**. Chi stringe da un lato paga dall'altro.

### 3.1 Qui `w: "majority"` vuol dire qualcosa

Sull'istanza singola `w: "majority"` **riesce** e non garantisce niente, perché la maggioranza di un
nodo è quel nodo: nessun errore, nessun avviso, nessuna riga di log
([V-015](../Sources.md#v-015)). È il limite silenzioso della pagina precedente, e su un replica set
smette di essere silenzioso perché smette di essere una bugia: la conferma arriva quando **due
membri su tre** hanno la scrittura.

Il prezzo, misurato a riposo su dieci giri per tre esecuzioni
([V-027](../Sources.md#v-027)):

| | mediana |
|---|---:|
| scrittura con `w: 1` | **1 ms** |
| scrittura con `w: "majority"` | **2 ms** |

**Un millisecondo in più**, e la riserva va detta sulla stessa riga: i tre membri girano sulla
stessa macchina, dentro la stessa rete Docker. Il costo della maggioranza è per definizione un giro
fino al secondo membro più veloce — qui vale un millisecondo, fra due datacenter varrebbe la latenza
fra i due datacenter, e sarebbe il termine dominante. Il numero **non descrive la produzione**: dice
che su questa configurazione la garanzia è quasi gratis, ed è il motivo per cui il dataset di demo
si carica così ([ADR-0043](../Decision.md#adr-0043)).

Da ignorare, invece, le medie: ogni esecuzione ha un valore fuori scala — 3, 9, 46 ms — ed è sempre
il **primo giro**. Non è ritardo di replica, è la prima connessione che si apre e si autentica.

### 3.2 Il ritardo di replica, e lo strumento che dà sempre ragione

Il ritardo mediano fra primario e secondario, a riposo, è **1 ms** ([V-027](../Sources.md#v-027)).

Il primo risultato della misura, però, è che **la misura ovvia non funziona**. `rs.status()` porta
`optimeDate` per ogni membro, e la differenza fra primario e secondari è il modo in cui il ritardo
si misura in tutti gli esempi che si trovano in rete. Su questo set risponde:

```
mongo-rs-2:27017  ritardo 0 ms
mongo-rs-3:27017  ritardo 0 ms
```

Sempre. `optimeDate` deriva dal timestamp dell'oplog, che ha **granularità di un secondo**: quello
zero non significa «nessun ritardo», significa «meno di un secondo, e più in là non vedo». Uno
strumento che dà sempre ragione non sta misurando. Il numero vero si ottiene scrivendo sul primario
con `w: 1` e interrogando un secondario in un ciclo finché il documento non compare.

### 3.3 I cinque modi, e che cosa costano

«Read preference describes how MongoDB clients route read operations to the members of a replica
set» ([S-058](../Sources.md#s-058)). I modi sono cinque:

| Modo | Che cosa fa (dal manuale 7.0) |
|---|---|
| `primary` | *predefinito.* «All operations read from the current replica set primary» |
| `primaryPreferred` | «operations read from the primary but if it is unavailable, operations read from secondary members» |
| `secondary` | «All operations read from the secondary members of the replica set» |
| `secondaryPreferred` | come sopra, ma se resta il solo primario legge da lui |
| `nearest` | «a random eligible replica set member, irrespective of whether that member is a primary or secondary», scelto per latenza |

Il prezzo sta in una frase sola, e conviene citarla alla lettera perché è più netta di qualunque
riassunto: «**All read preference modes except `primary` may return stale data** because secondaries
replicate operations from the primary in an asynchronous process. Ensure that your application can
tolerate stale data if you choose to use a non-`primary` mode»
([S-058](../Sources.md#s-058)).

Qui la coppia si chiude: *quanto* vecchio è il dato che si accetta leggendo da un secondario è il
ritardo di replica del §3.2 — su questo stack **un millisecondo**, altrove il numero che si misura
là. «Stale» non è un aggettivo morale: è una quantità, e va misurata prima di decidere se si può
tollerare.

Una seconda frase del manuale merita la stessa attenzione, perché smentisce un'aspettativa diffusa:
«Read preference does not affect the visibility of data. Clients can see the results of writes
before they are acknowledged or have propagated to a majority of replica set members». Leggere con
`primary` non protegge dal vedere scritture che potrebbero ancora sparire.

### 3.4 Senza primario: chi legge e chi no

Quando la maggioranza è persa (§2.3), il manuale è preciso su cosa succede a chi legge con il modo
predefinito: «If the primary is unavailable, read operations produce an error or throw an
exception» ([S-058](../Sources.md#s-058)). Misurato sul superstite retrocesso
([V-031](../Sources.md#v-031)):

| Richiesta | Come | Risposta |
|---|---|---|
| scrittura | qualunque | `NotWritablePrimary` (code **10107**) |
| lettura | `mongosh --host localhost`, connessione **diretta** | 50 000 documenti |
| lettura | URI con `replicaSet=rs0`, read preference predefinita | nessun server selezionabile |
| lettura | URI con `replicaSet=rs0`, `secondaryPreferred` | 50 000 documenti |

**La seconda riga è la trappola della verifica.** `mongosh` aggiunge `directConnection=true` da sé a
meno che la stringa non nomini un `replicaSet` ([S-045](../Sources.md#s-045)): con una connessione
diretta si parla a *quel* nodo e si legge, e chi prova la demo così conclude che il set funziona
ancora. L'applicazione, che usa l'URI del replica set, non trova nessun server a cui parlare.

---

## 4. Il confronto con l'istanza singola

[ADR-0032](../Decision.md#adr-0032) rimandava a questo branch il confronto sulla perdita di dati.
Eccolo, misurato dalle due parti con la stessa prova: uno scrittore che inserisce documenti uno alla
volta e stampa l'identificativo **dopo** la conferma del server, mentre a metà corsa il primario
viene ucciso senza chiusura pulita.

| | Istanza singola, `w: 1` ([V-016](../Sources.md#v-016)) | Replica set, `w: "majority"` ([V-033](../Sources.md#v-033)) |
|---|---:|---:|
| scritture confermate al client | 41 558 | 12 901 |
| **confermate e perdute** | **100** | **0** |
| errori visti dall'applicazione | — | **1** |
| pausa subita dall'applicazione | il servizio finisce | **10 155 ms**, poi riprende da sé |

Zero, e non «quasi tutte»: nella collezione ci sono 12 902 documenti e il massimo indice scritto è
12 902, quindi l'insieme è completo, senza buchi.

**E adesso la parte scomoda**, che sta qui perché un confronto che riporta soltanto la buona notizia
non è un confronto. L'unico errore visto dall'applicazione riguarda il documento `n=2698`:

```
ERR 2698 connection 1 to 172.18.0.3:27017 closed
```

Quel documento **nel database c'è**. Scritto, e mai confermato. È l'immagine speculare esatta della
perdita sull'istanza singola: là il client aveva in mano un `acknowledged: true` per dati che non
esistevano più, qui ha in mano un errore per dati che esistono. In tutti e due i casi ciò che il
client crede non coincide con ciò che il database ha — e la differenza è che **questo si
sopravvive**, a patto che la scrittura si possa rifare senza danno. Un'applicazione che reagisce
all'errore riscrivendo, e la cui riscrittura non è idempotente, qui si fa un duplicato.

Una precisazione onesta sul «un solo errore»: quasi tutta l'invisibilità del guasto è merito dei
**retryable write**, attivi per impostazione predefinita nel driver, che hanno tenuto appesa una
`insertOne` per dieci secondi invece di farla fallire. Senza di essi l'applicazione avrebbe visto
una raffica di errori e avrebbe dovuto decidere lei che fare. Quella prova non è stata fatta.

Il resto del confronto, per righe:

| | Istanza singola | Replica set a tre membri |
|---|---|---|
| failover | non esiste: `NoReplicationEnabled` | automatico, ~10 s (~0,5 s se ordinato) |
| `w: "majority"` | riesce e non garantisce niente | due membri su tre, +1 ms |
| oplog, change stream | assenti: `Location40573` | presenti |
| backup a caldo coerente | non possibile | possibile |
| manutenzione | vuole una finestra di fermo | a rotazione, servizio in piedi |
| letture distribuibili | no | sì, al prezzo del §3.3 |

La riga della manutenzione è quella che nella pratica decide più adozioni delle altre, e curiosamente
è quella di cui si parla meno: si discute di alta disponibilità pensando ai guasti, mentre la maggior
parte delle fermate è pianificata.

---

## 5. Il file Compose, riga per riga

Il file è [`docker/02-replicaset/compose.yaml`](../../docker/02-replicaset/compose.yaml). Sta in
poco più di quattrocento righe, di cui la maggioranza sono commenti: è materiale didattico, e va
letto dall'alto in basso.

### La catena di inizializzazione

Tre anelli, e si leggono nell'ordine in cui girano:

```
keyfile-init    genera il segreto condiviso e muore
     ↓          (service_completed_successfully)
mongo-rs-1/2/3  partono con --keyFile, rispondono, non sono ancora una replica
     ↓          (service_healthy)
rs-init         esegue rs.initiate(), attende il primario, crea l'amministratore,
                e come ultimo passo carica i dati di demo con w: "majority"
```

Il problema che questa catena risolve è circolare, e vale la pena enunciarlo perché è la ragione di
tutto il resto: con `--keyFile` attivo nessuno può inizializzare la replica prima che esista un
utente, e nessun utente può essere creato prima che la replica sia inizializzata. Tre strade sono
state montate e misurate prima di scegliere ([V-023](../Sources.md#v-023)); la scelta è
[ADR-0040](../Decision.md#adr-0040).

### Il keyfile, che non è nel repository

```yaml
  keyfile-init:
    image: ${MONGO_IMAGE:?assente — eseguire «make images-pull», ...}
    restart: "no"
    command: ["bash", "/init/01-keyfile.sh"]
    volumes:
      - keyfile:/keyfile
      - ./init/01-keyfile.sh:/init/01-keyfile.sh:ro
```

Volume **nominato**, non bind mount, ed è la decisione di [ADR-0014](../Decision.md#adr-0014): su
macOS un file montato dall'host non conserva i permessi che gli si danno, e `mongod` rifiuta di
partire con un keyfile che considera «too open». Generarlo dentro il volume è l'unico modo di
garantire il `400` ovunque. Il permesso sbagliato produce un errore che sembra tutt'altro: sta nella
[voce 3 delle trappole](trappole-mongodb-in-docker.md#t-03).

`restart: "no"` è obbligatorio su un one-shot. Con `unless-stopped` Compose rialzerebbe il servizio
ogni volta che esce — e un servizio che ha finito esce sempre — quindi
`service_completed_successfully` non scatterebbe mai per nessuno.

### Un membro

```yaml
  mongo-rs-1:
    hostname: mongo-rs-1
    mem_limit: ${MEMORIA_MEMBRO:-768m}
    cpus: ${CPU_MEMBRO:-0.75}
    command:
      - mongod
      - --replSet
      - ${NOME_REPLICA:-rs0}
      - --keyFile
      - /keyfile/mongo-keyfile
      - --bind_ip_all
      - --wiredTigerCacheSizeGB
      - "0.25"
```

Il **nome host** qui non è una buona abitudine come sullo stack 01: è un requisito. `rs.initiate()`
registra i membri con il nome con cui li si elenca, quel nome finisce *dentro* la configurazione
della replica, e da lì torna al driver quando scopre la topologia. Deve risolvere ovunque: nomi, mai
indirizzi ([ADR-0021](../Decision.md#adr-0021)).

`mongod` scritto per esteso non è pedanteria. L'entrypoint ufficiale lo antepone da sé quando il
primo argomento comincia per trattino, quindi le due forme avviano lo stesso processo — ma
`tools/check_stack.py` riconosce un `mongod` dal primo elemento del comando, e sulla forma
abbreviata la regola sulla cache **non scatta**. Misurato: un file senza cache dichiarata passava il
controllo come conforme ([V-026](../Sources.md#v-026)). Una regola che non può fallire non è una
regola.

`0.25` GiB di cache dentro `768m` di limite. La coppia va mossa **insieme**: chi abbassa
`MEMORIA_MEMBRO` sotto i 256 MiB configura una cache più grande della memoria che avrà, e `mongod`
lo accetta senza un avviso ([V-009](../Sources.md#v-009)). È il caso che `make stack-check`
intercetta. Il conto complessivo è in
[gestione delle risorse](../06-sviluppo/gestione-risorse-compose.md).

### L'healthcheck che deve diventare verde *prima* che la replica esista

```yaml
    healthcheck:
      test:
        - CMD
        - mongosh
        - --quiet
        - --eval
        - "const h = db.hello(); quit(h.isWritablePrimary || h.secondary || h.isreplicaset === true ? 0 : 1)"
      interval: 5s
      start_period: 20s
```

Tre termini, e il terzo è quello che fa funzionare la catena. Su un membro appena avviato con
`--replSet` e nessuna configurazione ricevuta, `hello()` risponde `isWritablePrimary: false`,
`secondary: false` e **`isreplicaset: true`**: solo il terzo è vero, ed è quello che apre la strada a
`rs.initiate()`. Un healthcheck con i primi due termini soltanto resta rosso per sempre, perché
`rs-init` aspetterebbe una condizione che solo lui può produrre.

`quit(0/1)` e non il valore stampato: `mongosh` esce 0 se lo script non solleva eccezioni, quindi un
`--eval` che si limita a stampare `false` risulterebbe sano lo stesso
([ADR-0036](../Decision.md#adr-0036), [V-020](../Sources.md#v-020)).

### La riga che rende possibile tutto il resto

```yaml
  rs-init:
    network_mode: "service:mongo-rs-1"
```

Questo container **non ha un'interfaccia di rete propria**: usa quella di `mongo-rs-1`. Quindi
`localhost`, qui dentro, è il `localhost` del `mongod`, e la connessione gode dell'**eccezione
localhost** — che permette `replSetInitiate` e il primo `createUser` su un nodo che pretende
autenticazione e non ha ancora nessun utente ([S-055](../Sources.md#s-055),
[V-023](../Sources.md#v-023)). È il momento in cui «localhost» si rivela una proprietà del namespace
di rete, non della macchina.

Due conseguenze da conoscere prima di provare a violarle: `rs-init` **non** è raggiungibile per nome
sulla rete Compose, e **non** può pubblicare porte.

### Come si avvia: due comandi, non uno

```console
$ docker compose --env-file tools/images.env \
                 --env-file docker/02-replicaset/.env \
                 -f docker/02-replicaset/compose.yaml up -d --wait
$ docker compose ... wait rs-init
```

Il primo comando esce **0 quattordici secondi prima** che il replica set esista: `--wait` attende che
i servizi siano «running|healthy», e `rs-init` — che non ha un healthcheck perché deve morire, non
vivere — è `running` nell'istante in cui comincia ([V-025](../Sources.md#v-025),
[S-057](../Sources.md#s-057)). Il verdetto vero è il codice di uscita del secondo comando, che blocca
finché il container si ferma. La decisione è [ADR-0041](../Decision.md#adr-0041); `make up-02` fa
tutti e due.

E i due `--env-file` non sono uno di troppo: la flag non **aggiunge** un file, prende il posto del
`.env` implicito. Passandone uno solo, il `.env` che sta accanto al file indicato con `-f` non viene
letto benché sia lì accanto ([S-056](../Sources.md#s-056)).

---

## 6. Provarlo in due minuti

Una premessa sola, e solo la prima volta: `docker/02-replicaset/.env` non è nel repository, perché
contiene la password dell'amministratore ([ADR-0040](../Decision.md#adr-0040)). Si crea con
`cp docker/02-replicaset/.env.example docker/02-replicaset/.env` e si riempie la riga
`PASSWORD_AMMINISTRATORE=`; è l'unica riga senza un valore predefinito. Saltandola, `make up-02` si
ferma dicendo esattamente questo, prima di toccare Docker.

```console
# Accendere: due comandi in uno, e il secondo è il verdetto vero
$ make up-02

# Chi comanda, e chi replica
$ docker exec mongo-rs-1 mongosh --quiet -u admin -p "$PASSWORD" \
    --authenticationDatabase admin --eval 'rs.status().members.map(m => m.name + " " + m.stateStr)'

# La prova completa dello stack: 42 controlli
$ make smoke-02

# Le tre scene, una alla volta, con reset-demo fra l'una e l'altra
$ make failover-02              # il primario ucciso        ~10 s
$ make failover-02-termina      # il primario che saluta    ~0,5 s
$ make failover-02-maggioranza  # la maggioranza persa      ~9,3 s
$ ./tools/reset-demo.sh 02

# Spegnere conservando i dati e il keyfile, oppure azzerare i soli dati
$ make down-02
$ make reset-02
```

Sul `-p "$PASSWORD"` di quella riga conviene essere precisi, perché il posto dove la password si
legge non è quello che sembra. Dentro il container **non** si legge: `mongosh` 2.10.0 riscrive il
proprio `argv`, e `ps` mostra `mongodb://<credentials>@…`. Si legge **sull'host**, nella riga di
comando del client `docker`, che nessuno oscura ([V-047](../Sources.md#v-047)). Su una macchina
condivisa è lì che si guarda, ed è la ragione per cui [ADR-0054](../Decision.md#adr-0054) chiede che
chi mostra il comando descriva l'esposizione vera invece di quella verosimile. Qui resta una password
di laboratorio, in un file fuori dal repository ([ADR-0040](../Decision.md#adr-0040)).

Lo smoke fa 42 controlli e ne dedica uno alla scena che conta: ferma un membro, verifica che il set
continui a scrivere con la maggioranza, e lo rimette a posto ([V-028](../Sources.md#v-028)).

Se una sezione «righe di log» stampasse il nulla, non è la scena che non è successa: dopo un riavvio
del demone Docker `docker logs` può restare fermo mentre il container è sano
([V-032](../Sources.md#v-032)). Gli script se ne accorgono e chiedono le righe a `mongod`, dicendo di
averlo fatto.

---

## Cosa questa pagina non dice

- ~~**Non misura le prestazioni sotto carico.** Tutti i numeri qui sono a riposo, con un solo
  scrittore. Il confronto fra le tre architetture ha senso sotto carico controllato, cioè con
  l'applicazione Python di `feature/04`, e prima di allora sarebbe aria.~~ **Saldato.**
  [V-079](../Sources.md#v-079): otto scrittori e quattro lettori per trenta secondi, lo stesso
  dataset deterministico sulle tre architetture. Il replica set scrive **6,2 volte più piano** dello
  standalone — è il prezzo della maggioranza, moltiplicato da tre container che si dividono lo
  stesso portatile ([ADR-0111](../Decision.md#adr-0111)). Sotto lo stesso carico *legge* invece con
  una mediana più bassa dello standalone, e non perché legga meglio: perché scrivendo cinque volte
  meno tiene i nodi molto meno occupati.
- ~~**Non prova la perdita con `retryWrites=false`.** È la misura naturale da aggiungere accanto a
  [V-033](../Sources.md#v-033): mostrerebbe che cosa vede un'applicazione senza la rete di sicurezza
  del driver.~~ **Saldato, e la risposta non è quella attesa:** [V-076](../Sources.md#v-076) — senza
  la rete di sicurezza del driver, durante un failover vero, il prezzo non è la perdita, è
  l'**incertezza**. La scrittura fallisce con un errore che non dice se il documento sia arrivato o
  no, e la decisione se ritentare torna a chi ha scritto l'applicazione.
- ~~**Non usa `maxStalenessSeconds`.** Il manuale lo indica come rimedio alla lettura di dati vecchi
  ([S-058](../Sources.md#s-058)); qui non è stato né usato né misurato.~~ **Saldato:**
  [V-077](../Sources.md#v-077) — adesso si usa, e in questo lab non può escludere nessuno. Il minimo
  ammesso è **90 secondi**, e i secondari di uno stack a riposo su un bridge locale restano ordini
  di grandezza sotto quella soglia: l'opzione è corretta e inerte insieme. Non viaggia mai da sola,
  perché con la preferenza `primary` è un errore in costruzione
  ([M-055](../../app/docs/Sources.md#m-055), [ADR-0109](../Decision.md#adr-0109)).
- **Non spiega perché un membro in pausa costi ventisette volte.** Con `mongo-rs-3` congelato la
  maggioranza si raggiunge ancora con due membri su tre, e il ritmo di scrittura crolla di un
  fattore ventisette ([V-078](../Sources.md#v-078)). Il rallentamento è misurato, la causa no: un
  membro **congelato** non è un membro **spento**, e separare l'effetto del flow control da quello
  dei timeout di heartbeat richiede una misura che qui non è stata fatta.
- **Non copre gli arbitri.** Un membro che vota e non porta dati è un modo di avere una maggioranza
  dispari a costo ridotto, con conseguenze che meritano più di un inciso. Lo stack non ne ha.
- **Non copre le letture nelle transazioni né il read concern.** `w: "majority"` e
  `readConcern: "majority"` sono cose diverse; qui compare solo il primo, più il secondo usato come
  strumento di verifica in [V-033](../Sources.md#v-033).
- **I numeri valgono per tre container sullo stesso portatile.** Il ritardo di replica e il costo
  della maggioranza sono dominati dalla rete, e qui la rete è un bridge locale. La forma dei
  fenomeni si trasferisce; le cifre no.
- **Non copre backup e restore su replica set.** Stanno in
  [`03-amministrazione`](../03-amministrazione/log.md) e nelle pagine che quel capitolo riceverà.

---

**Decisioni correlate:** [ADR-0046](../Decision.md#adr-0046) (la forma di questa pagina),
[ADR-0040](../Decision.md#adr-0040) (chi inizializza la replica),
[ADR-0041](../Decision.md#adr-0041) (quando lo stack si può dire pronto),
[ADR-0043](../Decision.md#adr-0043) (i dati di demo con la maggioranza),
[ADR-0044](../Decision.md#adr-0044) (le due scene di failover),
[ADR-0045](../Decision.md#adr-0045) (la terza scena),
[ADR-0014](../Decision.md#adr-0014) (il keyfile fuori dal repository),
[ADR-0021](../Decision.md#adr-0021) (nomi host, mai indirizzi),
[ADR-0032](../Decision.md#adr-0032) (i quattro limiti dell'istanza singola),
[ADR-0109](../Decision.md#adr-0109) (le opzioni di misura dalla riga di comando),
[ADR-0111](../Decision.md#adr-0111) (il confronto si pubblica in coppia con la riserva del ferro).

**Fonti:** [S-044](../Sources.md#s-044), [S-045](../Sources.md#s-045), [S-055](../Sources.md#s-055),
[S-056](../Sources.md#s-056), [S-057](../Sources.md#s-057), [S-058](../Sources.md#s-058),
[V-009](../Sources.md#v-009), [V-015](../Sources.md#v-015), [V-016](../Sources.md#v-016),
[V-020](../Sources.md#v-020), [V-023](../Sources.md#v-023), [V-025](../Sources.md#v-025),
[V-026](../Sources.md#v-026), [V-027](../Sources.md#v-027), [V-028](../Sources.md#v-028),
[V-029](../Sources.md#v-029), [V-030](../Sources.md#v-030), [V-031](../Sources.md#v-031),
[V-032](../Sources.md#v-032), [V-033](../Sources.md#v-033),
[V-076](../Sources.md#v-076), [V-077](../Sources.md#v-077), [V-078](../Sources.md#v-078),
[V-079](../Sources.md#v-079)
