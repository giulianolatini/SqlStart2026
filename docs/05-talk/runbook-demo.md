# Runbook del talk — SqlStart 2026

**Ancona, venerdì 18 settembre 2026 · 60 minuti · 27 di demo, 2 di margine.**

Questo è **l'unico documento che serve sul palco**. Si stampa, si tiene aperto sul secondo
schermo, e non rimanda a nient'altro: tutto ciò che serve mentre si parla è qui dentro, anche
quando è scritto meglio altrove ([ADR-0015](../Decision.md#adr-0015)). La duplicazione è
deliberata e costa un file da tenere aggiornato; l'alternativa è saltare fra quattro documenti
davanti a cento persone, che è il modo affidabile di perdere l'informazione giusta.

**Come si legge sotto pressione.** Le §1 e §2 si leggono in ordine e si eseguono. La §3 e la §4
si consultano a salto, quando qualcosa non va. L'**Appendice A** si apre solo se si è in ritardo,
e dice cosa tagliare **in quale ordine** — la decisione è già presa, non si prende sul palco.
L'**Appendice B** è per quando serve rimettere in piedi qualcosa.

**Sui numeri di questo documento.** Ogni «output atteso» è un numero **misurato**, non stimato, e
viene dalla registrazione o dalla verifica citata accanto. Sul palco varieranno: sono un metro per
capire se la scena sta andando come deve, non una promessa. Uno scarto del 20 % non è un problema;
un ordine di grandezza sì, e allora si guarda la §4.

---

## Indice

- [§1 — Prima del talk](#prima-del-talk)
- [§2 — Copione minuto per minuto](#copione)
- [§3 — Piano delle registrazioni](#registrazioni)
- [§4 — Guasti previsti e reazione](#guasti)
- [Appendice A — Criteri di rinuncia di scena](#appendice-a)
- [Appendice B — Comandi di emergenza e ripristino completo](#appendice-b)

---

<a id="prima-del-talk"></a>

## §1 — Prima del talk

<a id="la-sera-prima"></a>

### 1.1 La sera prima

Quattro cose, e nessuna si può fare la mattina.

| # | Cosa | Comando | Perché la sera |
|---:|---|---|---|
| 1 | Le immagini sono in cache | `make images-verify` | Se ne manca una servono rete e tempo: la mattina c'è poco dell'una e niente dell'altra |
| 2 | L'immagine dell'applicazione esiste | `docker image inspect mongolab:0.1.0` | `pull_policy: never`: se manca, Compose non la scarica ([ADR-0039](../Decision.md#adr-0039)), e costruirla la prima volta vuole rete |
| 3 | I filmati MP4 sono sul disco | `ls -la ~/SqlStart2026-registrazioni` | YouTube è distribuzione, non piano B ([ADR-0016](../Decision.md#adr-0016)) |
| 4 | Le tre suite sono verdi | `make app-test` · `make tools-test` · `make docs-check` | Un rosso scoperto la mattina è un'ora persa |

Se il punto 2 dice che manca: `make app-image`, che vuole rete la prima volta e poi mai più.

<a id="la-mattina"></a>

### 1.2 La mattina, con la sala vuota — T–60 minuti

```bash
make preflight
```

Controlla, in quest'ordine e senza fermarsi al primo problema: che `docker` risponda e quale
contesto sia attivo; che il binario nel `PATH` sia quello del contesto — il 24 agosto `docker`
risolveva a Rancher Desktop mentre il contesto puntava a Docker Desktop, e l'errore che ne usciva
non era leggibile; la memoria e le CPU assegnate alla VM; la versione del kernel; che ogni
immagine pinnata sia in cache; che l'immagine dell'applicazione ci sia; che i filmati di riserva
siano sul disco; che le porte del lab siano libere.

**Errori → uscita 1, e si rimedia. Avvisi → uscita 0, e si prosegue.** Il preflight non si ferma
al primo problema di proposito: deve dire tutto quello che non va mentre c'è ancora tempo.

Se manca l'immagine dell'applicazione lo dice, e dice `make app-image`.

<a id="accensione"></a>

### 1.3 Accensione degli stack — T–25 minuti

I tre stack si accendono **tutti e tre** e restano accesi per tutto il talk. Il bilancio delle
risorse è dimensionato perché ci stiano insieme.

```bash
make up-01     # standalone      — porta 27017
make up-02     # replica set     — porte 27021 27022 27023
make up-03     # sharded, profilo palco — mongos su 27117
```

Ognuno dei tre termina da sé quando lo stack è **sano**: `up -d --wait` non torna prima. Se torna
con successo e la replica non esiste, è la trappola
[15](../02-architetture/trappole-mongodb-in-docker.md#t-15) — `--wait` guarda l'`healthcheck` del
container, non lo stato del replica set.

Lo stack 03 parte nel profilo `palco`, un membro per shard: è quello che entra in un portatile
([ADR-0010](../Decision.md#adr-0010)). Il profilo `completo` si usa solo per la scena 9 delle
registrazioni, e in sala non si accende.

Poi, uno per stack, la prova end-to-end:

```bash
make smoke-01
make smoke-02      # atteso: Superati: 42 · Errori: 0
make smoke-03
```

<a id="stato-atteso"></a>

### 1.4 Stato atteso dei dati

Questo è il metro. Se un numero non torna, la demo comincia da uno stato che il copione non
prevede, e si rimedia **adesso** con `./tools/reset-demo.sh <stack>`.

| Stack | Database | Collezione | Documenti attesi | Come si verifica |
|---|---|---|---:|---|
| 01 standalone | `lab` | `ordini` | **50 000** | `make app-stats TARGET=standalone` |
| 02 replica set | `lab` | `ordini` | **50 000** | `make app-stats TARGET=rs` |
| 03 sharded | `lab` | `ordini` | **20 000** | `make stato-03` |

Sullo stack 02 `mongolab stats` deve mostrare **tre membri e un primario**, e il primario deve
essere quello con priorità 2 — `mongo-rs-1`. La scena del failover comincia da lì; se comincia da
un primario diverso, il copione regge lo stesso ma la frase «il nodo con priorità più alta» non
descrive più quello che si vede.

Sullo stack 03: **2 shard**, `lab.ordini` in **4 chunk** (due per shard), **balancer abilitato**,
**1 router**.

<a id="terminali"></a>

### 1.5 Disposizione dei terminali

**Tre finestre, e la ragione di ciascuna.** È l'unica parte della preparazione che il pubblico
vede, quindi si sistema prima.

| Finestra | Dove punta | Serve a |
|---|---|---|
| **A** — la scena | radice del repository | Ci gira l'applicazione. È quella proiettata |
| **B** — la regia | radice del repository | Ci si danno i comandi `docker` che l'applicazione **annuncia** ma non può dare |
| **C** — la riserva | radice del repository | Riproduzione delle registrazioni, `reset-demo.sh`, tutto ciò che non deve interrompere A |

**Perché la B esiste.** Nell'Atto II l'applicazione gira **dentro la rete Compose**, perché la
cronaca dell'elezione esiste solo da lì ([M-019](../../app/docs/Sources.md#m-019)); e da dentro la
rete non ha il socket del demone Docker, quindi non può fermare un container. Allora non finge: lo
**annuncia** e aspetta.

```
▸ da un'altra finestra, nella radice del repository:

  docker compose --env-file tools/images.env --env-file docker/02-replicaset/.env \
    -f docker/02-replicaset/compose.yaml stop mongo-rs-1

   Invio quando è stato eseguito
```

Si copia la riga nella **B**, la si esegue, si torna in **A** e si preme Invio. La riga è già
completa: non si compone niente sul palco.

**Font grande in tutte e tre.** La cronaca dell'Atto II è fatta di righe con timestamp al
millisecondo, e un millisecondo illeggibile non è un dato.

---

<a id="copione"></a>

## §2 — Copione minuto per minuto

I minuti sono **dall'inizio delle demo**, non dall'inizio del talk: dove cade T+0 dentro i 60
minuti dipende da quanto durano le slide di apertura, e si decide alla prova generale del 17.

| Da | A | Durata | Blocco |
|---:|---:|---:|---|
| T+0 | T+4 | 4 min | [Blocco 1 — standalone](#blocco-1) |
| T+4 | T+8 | 4 min | [Blocco 2, Atto I — che cosa c'è](#atto-i) |
| T+8 | T+13 | 5 min | [Blocco 2, Atto II — il failover cronometrato](#atto-ii) |
| T+13 | T+17 | 4 min | [Blocco 2, Atto III — il backup a caldo](#atto-iii) |
| T+17 | T+25 | 8 min | [Blocco 3 — sharded](#blocco-3) |
| T+25 | T+27 | 2 min | **Buffer** — è parte del piano, non un avanzo |

**Il buffer si spende, non si risparmia.** Se a T+17 si è in pari, il Blocco 3 ha 8 minuti e il
buffer resta per le domande. Se si è oltre T+18, si apre l'[Appendice A](#appendice-a) **prima** di
cominciare il Blocco 3, non a metà.

---

<a id="blocco-1"></a>

### Blocco 1 — standalone · 4 minuti

**Che cosa deve restare al pubblico:** un `mongod` solo è una cosa semplice e comprensibile, e ha
esattamente un limite che conta.

**1. La cache, cioè dove vive davvero un database.** Finestra A:

```bash
docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml \
  exec mongo-standalone mongosh lab
```

```javascript
db.serverStatus().wiredTiger.cache["maximum bytes configured"]
```

> **Atteso:** un numero di byte coerente con `mem_limit` del servizio — la metà della memoria
> meno un giga, con un minimo di 256 MiB. Da leggere ad alta voce in gigabyte, non in byte.

Da dire mentre si vede: `wiredTiger.cache` esiste su ogni `mongod` e **su un `mongos` non c'è**.
Serve nel Blocco 3, quando qualcuno la cercherà sul router.

**2. Quanto pesa quello che c'è.**

```javascript
db.stats()
```

> **Atteso:** `lab` con **50 000** documenti in `ordini`.

**3. Carico breve.** Si esce da `mongosh` e:

```bash
make app-workload TARGET=standalone ARGS="--duration 20"
```

**4. Il dump, e il suo limite.**

```bash
docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml \
  exec mongo-standalone mongodump --db lab --out /tmp/dump-standalone
```

Lo stack 01 non ha autenticazione, ed è deliberato: il talk mostra l'architettura, non la gestione
delle credenziali. Dal Blocco 2 in poi c'è il keyfile, e con lui il controllo degli accessi.

> **Frase di chiusura del blocco.** «Questo dump è partito mentre qualcuno scriveva. Su un nodo
> solo, per averlo davvero coerente, dovrei bloccare le scritture con `fsyncLock` o fermarle del
> tutto. Fra due minuti vedremo l'architettura in cui questo problema non si pone — e vedremo
> quanto costa.»

---

<a id="atto-i"></a>

### Blocco 2, Atto I — che cosa c'è, prima che lo rompa · 4 minuti

**1. La fotografia.** Finestra A:

```bash
make app-stats TARGET=rs
```

> **Atteso** (riferimento: registrazione [10](registrazioni/README.md#registrazioni-di-terminale),
> 1,5 s): `mongod 7.0.40`; **tre membri e un primario**; `lab` con **50 000** documenti. Otto
> righe, e ci stanno tutte sullo schermo.

Da dire: la versione è **7.0.40** e non 8, e il perché è una cosa interessante — su kernel 6.19,
cioè quello che Docker Desktop monta oggi, MongoDB 8 non parte. Chiunque in sala ci provi incontra
lo stesso muro, e non ha una versione a cui aggiornarsi.

**2. Chi comanda, e chi vota.**

```javascript
rs.status()
rs.conf()
```

Le righe che contano: `stateStr`, `priority`, `votes`. `mongo-rs-1` ha priorità **2**, gli altri
due **1**: è per questo che il ruolo torna da lui quando rientra, e nell'Atto II si vedrà.

**3. Il driver che se ne accorge da solo.**

```bash
make app-watch TARGET=rs ARGS="--duration 60"
```

Una riga per transizione, con il timestamp al millisecondo. Non è un `poll`: è il driver che
racconta quando **ha saputo**, non quando qualcuno è passato a chiedere.

> **Se questo si vuole mostrare senza aspettare un guasto vero**, la registrazione
> [11](registrazioni/README.md#registrazioni-di-terminale) ha un'elezione intera senza carico
> intorno: primario perso a `26.047`, `mongo-rs-2` eletto a `36.082`, cioè **10 035 ms**.

> **Frase di chiusura dell'atto.** «Il driver conosce la topologia e la aggiorna da sé. Adesso
> gliela cambio sotto.»

---

<a id="atto-ii"></a>

### Blocco 2, Atto II — il failover cronometrato · 5 minuti

**Questa è la scena che non si taglia mai.** È la ragione per cui l'applicazione esiste, ed è la
cosa che una platea che viene da SQL non ha mai visto: non «il cluster è resiliente», ma **quanti
millisecondi** e **quante scritture**.

Finestra A:

```bash
make app-demo TARGET=rs ARGS="--step --sink plain"
```

`--sink plain` non è gusto: `--step` e il pannello `Live` di Rich vogliono lo stesso terminale, e
la riga di comando lo **rifiuta** invece di lasciar premere Invio alla cieca. `--step` mette una
pausa prima di ogni fase, e si riparte con Invio.

Le fasi, in ordine, e cosa dire su ciascuna:

| Fase | Durata | Che cosa si vede | Che cosa si dice |
|---|---:|---|---|
| `carico` | 10 s | scritture confermate che salgono, p95 | «Sto scrivendo. Tutto normale.» |
| `guasto` | — | l'applicazione **annuncia** il comando e aspetta | Si passa alla finestra **B**, si esegue, si torna in **A**, Invio |
| `elezione` | 25 s | `ERRORE NotPrimaryError`, poi `RITENTO tentativo 2 dopo 50 ms`, poi il nuovo primario | «Il driver sta riprovando da solo. Questo è `retryWrites`.» |
| `ripresa` | — | annuncio del comando di riavvio | Di nuovo dalla **B** |
| `recupero` | 15 s | il ritmo torna, e il ruolo torna a `mongo-rs-1` | «Priorità 2: se lo riprende.» |
| bilancio | — | **i due numeri** | Sotto |

> **Atteso** (riferimento: registrazione [12](registrazioni/README.md#registrazioni-di-terminale),
> 53,3 s): interruzione **10 019 ms** · **0 scritture perse** · 31 952 confermate contro 31 955
> ritrovate.

**Le tre in più non sono un errore di conteggio ed è meglio dirlo prima che lo chieda qualcuno.**
L'applicazione le chiama **scritture non confermate**: sono arrivate al database, e il loro `ack`
non è mai tornato al chiamante perché il primario è caduto in mezzo. È il verso *sicuro* dello
scarto — l'altro verso, le **scritture perse**, è quello che resta a **zero**.

Se qualcuno chiede a che serva `retryWrites`, la risposta è misurata e sta in una riga: con i
tentativi del driver spenti la perdita resta zero lo stesso — `w: "majority"` fa il suo mestiere —
ma le non confermate diventano **8** in una corsa e **1** nell'altra, e un'applicazione che
riprovasse quelle scritture a mano, senza una chiave di idempotenza, le duplicherebbe
([V-076](../Sources.md#v-076)).

**Il supplemento, se il tempo c'è** (~1,5 min, ed è il taglio n. 2):

```bash
make app-demo TARGET=rs ARGS="--step --sink plain --mode sospendi"
```

Con `--mode sospendi` il container non muore: resta **vivo, con la sua memoria, e non risponde a
nessuno**. Il client non riceve «connection refused» ma un **timeout**, cioè la differenza fra un
server morto e una rete partizionata. E `docker compose ps` dice «Up» esattamente come per un
container sano: un guasto che non lascia tracce nel posto in cui si guarda.

> **Frase di chiusura dell'atto.** «Dieci secondi di interruzione, zero scritture perse. Il numero
> di sinistra si può migliorare con la configurazione; quello di destra è la ragione per cui si
> usa un replica set.»

**Prima dell'Atto III:** si cambia terminale. L'Atto III gira **dall'host**, non dentro la rete.

---

<a id="atto-iii"></a>

### Blocco 2, Atto III — il backup a caldo e la finestra che si paga · 4 minuti

`demo backup-live` e `demo restore` girano **solo dall'host** e accettano **solo** `--target rs`:
il dump lo esegue un processo dentro un nodo, e chi lo comanda deve avere il socket del demone.
Se si sbaglia, la riga di comando lo dice e non parte.

**1. Il dump mentre si scrive.** Finestra A:

```bash
uv run --directory app mongolab demo backup-live --target rs --step --sink plain
```

Il dump è `mongodump --readPreference=secondary --oplog`: legge da un **secondario**, così il
primario continua a servire le scritture, e `--oplog` cattura le operazioni avvenute *durante* il
dump, che è ciò che lo rende coerente rispetto a un istante.

> **Atteso** (riferimento: registrazione [13](registrazioni/README.md#registrazioni-di-terminale),
> 11,4 s): ritmo **546/s** prima, **539/s** durante — **calo dell'1,3 %**.

C'è un tetto: `--tetto`, predefinito **300 secondi**. Oltre quello il dump viene abbattuto e la
scena finisce con un errore che dice «ha superato il tetto», non «`mongodump` è uscito con
codice -9». Sul palco non si tocca; esiste perché un dump che non torna non può tenere ferma la
scena ([ADR-0118](../Decision.md#adr-0118)).

**2. I due conteggi, che non coincidono.**

```bash
uv run --directory app mongolab demo restore --target rs --step --sink plain
```

> **Atteso** (riferimento: registrazione [14](registrazioni/README.md#registrazioni-di-terminale),
> 3,2 s): **5 886** all'origine · **5 740** nella copia · **differenza 146**.

**Le due scene vanno in quest'ordine e attaccate**, perché la seconda conta ciò che la prima ha
copiato. I documenti di differenza sono quelli scritti *mentre* il dump era in corso: stanno
nell'oplog, e `mongorestore` senza `--oplogReplay` non li riapplica.

> **Frase di chiusura dell'atto, e del blocco.** «Il backup a caldo costa l'uno per cento di
> ritmo e lascia una finestra. Il numero di prima e il numero di adesso sono lo stesso fatto visto
> dai due lati — e la finestra è ciò che si paga. Su un nodo solo, come nel Blocco 1, non avrei
> avuto nemmeno la scelta.»

---

<a id="blocco-3"></a>

### Blocco 3 — sharded cluster · 8 minuti

**Il cluster è già acceso** dalla §1.3: non si mostra l'avvio, si mostra il risultato. Chi vuole
vedere gli undici servizi accendersi nell'ordine giusto ha la registrazione
[5](registrazioni/README.md#registrazioni-di-terminale), 22,9 s.

**1. Come si presenta.** Finestra A:

```bash
make stato-03
```

> **Atteso** (riferimento: registrazione [6](registrazioni/README.md#registrazioni-di-terminale),
> 6,5 s): **2 shard** · `lab.ordini` in **4 chunk**, due per shard · **balancer abilitato** ·
> **1 router**.

`sh.status()` per intero è molto testo. Sotto ci sono le quattro righe che contano, e sono quelle
che si leggono ad alta voce.

**2. Partizionata, non copiata.** È il cuore del blocco.

```bash
make distribuzione-03
```

> **Atteso** (riferimento: registrazione [7](registrazioni/README.md#registrazioni-di-terminale),
> 4,0 s): **9 860 + 10 140 = 20 000**, cioè **49,3 %** e **50,7 %**.

Da dire: gli stessi documenti, contati prima dal router e poi shard per shard. La somma torna, e
nessuno dei due ha una copia dell'altro. **Questa è la differenza fra sharding e replica**, ed è
la cosa che una platea SQL confonde più spesso.

**3. La chiave di shard, cioè che cosa cambia se la si sceglie male.**

```bash
uv run --directory app mongolab demo sharding --target sharded --step --sink plain
```

Non è `make app-demo`: quel target è la scena del **failover**, e `demo sharding` non ha un target
suo nel Makefile.

Lo stesso carico due volte: la prima corsa in una collezione **nuova, non distribuita** — finisce
tutta su un solo shard; la seconda in `lab.ordini`, distribuita su `{_id: "hashed"}` — si
ripartisce. Il limite è un **conteggio** di scritture e non una durata, perché a durata uguale due
corse fanno lavoro diverso e la scena chiamata «lo stesso carico due volte» non lo sarebbe.

**4. Query mirata contro scatter-gather** (se restano almeno 2 minuti). Da `mongosh` sul router:

```javascript
db.ordini.find({_id: 42}).explain().queryPlanner.winningPlan.shards.length
db.ordini.find({_id: {$gte: 100, $lt: 200}}).explain().queryPlanner.winningPlan.shards.length
db.ordini.find({citta: "Ancona"}).explain().queryPlanner.winningPlan.shards.length
```

> **Atteso:** **1** shard alla prima — la chiave c'è tutta. **2** alla seconda: la chiave è
> `hashed`, e un intervallo su una chiave hashed non è un intervallo su nulla. **2** alla terza:
> `citta` non è la chiave, e il router non ha modo di sapere dove guardare.

> **Frase di chiusura del blocco, e delle demo.** «Tre query, e solo la prima sa dove andare. Con
> due shard il broadcast costa il doppio; con venti costa venti volte. Ed è per questo che la
> domanda giusta non è "come faccio a fare sharding" — è **quando lo sharding non serve**. Se i
> vostri dati stanno in un replica set, ci state benissimo: avete visto quanto regge, e quanto
> costa il backup. Lo sharding si prende quando non c'è alternativa, e si paga in una chiave che
> non si cambia più.»

---

<a id="registrazioni"></a>

## §3 — Piano delle registrazioni

<a id="le-due-specie"></a>

### 3.1 Due specie, e non sono intercambiabili

| | che cos'è | dove sta | copre il caso |
|---|---|---|---|
| **Filmato** (`.mp4`) | lo schermo e la voce di chi parla | `~/SqlStart2026-registrazioni` sul disco, **più** il canale YouTube del relatore | «la demo non parte» |
| **Registrazione di terminale** (`.cast`) | il tracciato di ciò che il terminale ha fatto, con i tempi | `docs/05-talk/registrazioni/` | «la demo parte ma stiamo finendo il tempo» |

**YouTube è distribuzione, non piano B.** La connettività in sala non è garantita: un filmato
raggiungibile solo in rete non è un filmato di riserva. La copia locale la verifica il preflight.

<a id="che-cosa-esiste"></a>

### 3.2 Che cosa esiste, e quale numero porta

Quattordici scene, nessuna montata: ognuna è **una** esecuzione intera, con i tempi che ha avuto.
Le cinque dell'applicazione sono girate con lo **stesso codice** che gira dal vivo — `--sink plain`
e senza `--step`, perché la modalità da palco cambia una funzione di attesa, non la scena. È la
proprietà che le rende una copia e non una ricostruzione.

| # | File | Sostituisce | Durata | Il numero che porta |
|---:|---|---|---:|---|
| 1 | `01-smoke-replica-set.cast` | apertura del Blocco 2 | 16,9 s | `Superati: 42 · Errori: 0` |
| 2 | `02-failover-docker-kill.cast` | Atto II, versione brutale | 17,2 s | elezione in **8 617 ms**; `ExitCode=137` |
| 3 | `03-failover-terminazione-pulita.cast` | subito dopo la 2 | 25,1 s | elezione in **1 039 ms**; `ExitCode=0` |
| 4 | `04-maggioranza-persa.cast` | «e a quanti guasti regge?» | 15,6 s | `SECONDARY` dopo **8 634 ms** |
| 5 | `05-avvio-sharded.cast` | apertura del Blocco 3 | 22,9 s | `Container sh-up-03 Healthy` |
| 6 | `06-stato-sharded.cast` | Blocco 3, punto 1 | 6,5 s | 2 shard · 4 chunk · balancer on · 1 router |
| 7 | `07-distribuzione-sharded.cast` | Blocco 3, punto 2 | 4,0 s | **9 860 + 10 140 = 20 000** |
| 8 | `08-guasto-shard-palco.cast` | «e se ne cade uno?» | 40,1 s | `FailedToSatisfyReadPreference` dopo **15 s** |
| 9 | `09-failover-membro-shard.cast` | subito dopo la 8 | 12,3 s | totale ancora **20 000**, in **0 s** |
| 10 | `10-app-fotografia-dello-stack.cast` | **Atto I, punto 1** | 1,5 s | `mongod 7.0.40` · tre membri · 50 000 documenti |
| 11 | `11-app-cronaca-dell-elezione.cast` | **Atto I, punto 3** | 42,5 s | elezione in **10 035 ms**, senza carico |
| 12 | `12-app-failover-e-i-due-numeri.cast` | **Atto II per intero** | 53,3 s | **10 019 ms** · **0 scritture perse** |
| 13 | `13-app-backup-a-caldo.cast` | **Atto III, punto 1** | 11,4 s | 546/s → 539/s: **calo 1,3 %** |
| 14 | `14-app-restore-e-i-due-conteggi.cast` | **Atto III, punto 2** | 3,2 s | 5 886 · 5 740 · **differenza 146** |

**Le coppie che vanno insieme, e in quest'ordine:** 2 e 3 (il gesto brutale costa dieci secondi,
quello educato uno — il contrario di quello che il pubblico si aspetta); 8 e 9 (lo stesso comando
in due profili: la ridondanza sta *dentro* ogni shard); 13 e 14 (la seconda conta ciò che la prima
ha copiato).

<a id="come-si-riproducono"></a>

### 3.3 Come si riproducono — finestra C

Senza installare niente, con i tempi originali:

```bash
python3 tools/registra-terminale.py --riproduci \
  docs/05-talk/registrazioni/12-app-failover-e-i-due-numeri.cast
```

**I tempi si rispettano di proposito.** Un failover che scorre tutto insieme non racconta niente,
perché la scena *è* l'attesa. Vale doppio per la 8, dove i quindici secondi prima dell'errore
**sono** la risposta alla domanda. `--velocita 10` esiste per le prove e in sala non si usa.

Serve un **terminale vero**: dentro una pipe o in un editor le sequenze di colore diventano
caratteri e lo schermo si sporca.

<a id="quando-si-usano"></a>

### 3.4 Quando si usano — regola, non discrezione

| Situazione | Cosa si fa |
|---|---|
| La scena non parte entro **30 secondi** dal comando | Registrazione della scena, senza commentare il guasto |
| La scena parte e si pianta a metà | Si lascia lo schermo com'è, si dice cosa doveva succedere, si passa alla registrazione |
| Si è oltre T+18 all'inizio del Blocco 3 | [Appendice A](#appendice-a), non registrazioni |
| Docker è morto del tutto | Filmati MP4 dalla cartella locale, e si continua a parlare |

**La regola esiste perché la decisione non si prende sul palco.** Trenta secondi sono lunghi
davanti a cento persone e brevi per un container: il numero è scelto perché non lo si debba
scegliere lì.

---

<a id="guasti"></a>

## §4 — Guasti previsti e reazione

Tutti i rimedi valgono **dalla finestra C**, senza toccare la A.

| Sintomo | Che cos'è | Azione |
|---|---|---|
| `make app-stats` dice 0 documenti | il seed non è passato, o la demo precedente ha lasciato la collezione a metà | `./tools/reset-demo.sh 02` — riavvia i container fermati, aspetta un primario, ricarica il dataset |
| Il primario è `mongo-rs-2` o `-3` | una demo precedente non è rientrata | `./tools/reset-demo.sh 02`: aspetta che torni quello con priorità 2 |
| «Connection refused» verso un nodo acceso e sano | trappola [4](../02-architetture/trappole-mongodb-in-docker.md#t-04) — si sta bussando alla porta dell'host invece che al nome interno | Comando dalla finestra giusta: dentro la rete si usa `mongo-rs-1:27017`, dall'host `localhost:27021` |
| Il container ucciso non si rialza | trappola [6](../02-architetture/trappole-mongodb-in-docker.md#t-06) — `restart: unless-stopped` non rialza chi è stato fermato a mano | `docker compose ... start mongo-rs-1`, che è la riga che l'applicazione annuncia |
| Compose dice che la password manca | trappola [14](../02-architetture/trappole-mongodb-in-docker.md#t-14) — il `.env` accanto al file Compose non è quello che Compose legge | Serve `--env-file docker/02-replicaset/.env`, che i target del Makefile hanno già |
| `up --wait` è uscito bene e il replica set non c'è | trappola [15](../02-architetture/trappole-mongodb-in-docker.md#t-15) | `make smoke-02`: se fallisce, `make reset-02` e poi `make up-02` |
| I chunk sono 2 invece di 4 | trappola [20](../02-architetture/trappole-mongodb-in-docker.md#t-20) — il balancer li ha uniti | Non si rimedia sul palco: si mostra `make distribuzione-03`, che conta i documenti e non i chunk |
| Il cluster chiede la password e gli shard no | trappola [21](../02-architetture/trappole-mongodb-in-docker.md#t-21) — l'eccezione localhost su uno shard senza utenti | È previsto e si racconta: è una delle tre semplificazioni dichiarate del lab |
| Il router aspetta 15 s e poi dà `FailedToSatisfyReadPreference` | profilo `palco`, un membro per shard: non c'è nessuna elezione da fare | È il comportamento corretto, e la registrazione 9 mostra lo stesso guasto con tre membri |
| L'applicazione non parte: immagine assente | `pull_policy: never` e l'immagine non c'è | `make app-image` — vuole rete. In sala: si usa `DOVE=host`, che non ha bisogno dell'immagine |
| Rich si comporta male con `--step` | sono incompatibili, e la riga di comando lo rifiuta | `--sink plain`, che è già nel copione |
| Il disco si riempie | trappola [10](../02-architetture/trappole-mongodb-in-docker.md#t-10) | `docker system df`, e in emergenza `rm -rf /tmp/dump-*` dentro i nodi |

**Una cosa che non è un guasto.** Nella registrazione 12 le elezioni sono **due**: la seconda
avviene da sé quando `mongo-rs-1` rientra e si riprende il ruolo, otto secondi dopo essere tornato
secondario. Se succede dal vivo, non è un problema: è la migliore risposta possibile alla domanda
«ma allora a che serve `retryWrites`?».

---

<a id="appendice-a"></a>

## Appendice A — Criteri di rinuncia di scena

**Nel repository non si taglia nulla** ([ADR-0017](../Decision.md#adr-0017)). La documentazione
resta esaustiva su tutto, compreso ciò che dal vivo non si mostrerà: chi è interessato lo avvia a
casa con un comando. Questi tagli valgono **solo per l'esecuzione dal vivo**.

**L'ordine è deciso a mente fredda il 25 agosto 2026, e sul palco si applica senza discutere.** La
ragione per cui esiste in agosto e non il 15 settembre: sotto pressione si taglia ciò che è
difficile, non ciò che vale poco.

| # | Taglio | Recupera | Cosa resta comunque al pubblico |
|---:|---|---:|---|
| 1 | **Blocco 3 per intero.** Una slide, la `sh.status()` già a schermo, e il rimando al repository | ~8 min | `docker/03-sharded/`, la pagina dell'architettura sharded, il filmato su YouTube |
| 2 | Il supplemento `--mode sospendi` nell'Atto II (nodo irraggiungibile ma vivo) | ~1,5 min | descritto in `trappole-mongodb-in-docker.md` |
| 3 | `mongodump` nel Blocco 1 — restano `wiredTiger.cache` e `db.stats()` | ~1 min | la pagina `backup-restore.md` |
| 4 | Atto III — backup a caldo **mostrato sul filmato** invece che eseguito | ~3 min | il filmato è già pronto e mostra la stessa scena |

**Il mezzo taglio, se il ritardo è modesto:** del Blocco 3 si tengono `sh.status()` e la
contrapposizione query mirata / scatter-gather; cadono la distribuzione dei chunk e il balancer al
lavoro. Recupera **~4 minuti**.

**Non si taglia mai:**

- **L'Atto II del Blocco 2** — il failover cronometrato, con durata dell'interruzione e scritture
  perse. È la ragione per cui esiste l'applicazione, ed è la cosa che una platea che viene da SQL
  non ha mai visto.
- Fuori scena: **preflight, reset e registrazioni di riserva**. Non li vede nessuno e sono ciò che
  permette di ricominciare.

---

<a id="appendice-b"></a>

## Appendice B — Comandi di emergenza e ripristino completo

**In ordine di violenza.** Si sale di un gradino solo se quello sotto non è bastato.

<a id="b1"></a>

### B.1 — Rimettere a posto una scena, senza ricostruire nulla (~10 s)

```bash
./tools/reset-demo.sh 02
```

Riavvia i container fermati a mano; aspetta che i tre membri siano sani e che il primario sia
tornato quello con priorità 2; porta via le collezioni che la demo ha lasciato in giro; ricarica il
dataset. **Non è `make reset-02`**: quello cancella i volumi e costa mezzo minuto.

Vale per tutti e tre: `./tools/reset-demo.sh 01`, `... 02`, `... 03`.

<a id="b2"></a>

### B.2 — Ricostruire uno stack da zero, conservando il keyfile (~30–60 s)

```bash
make reset-02      # ferma e CANCELLA i volumi dei dati
make up-02         # ricostruisce e aspetta che la replica esista
make smoke-02      # atteso: Superati: 42 · Errori: 0
```

Il keyfile **non** viene cancellato: sta in un volume suo, e ricrearlo vorrebbe dire rifare
l'autenticazione interna di tutti i membri.

<a id="b3"></a>

### B.3 — Spegnere tutto e riaccendere

```bash
make down-01 && make down-02 && make down-03
make up-01 && make up-02 && make up-03
```

**`down` e non `docker kill`.** `down` manda `SIGTERM` e il primario cede il ruolo prima di
uscire: lo spegnimento costa mezzo secondo invece di dieci, e la riaccensione trova un insieme che
sa già dov'era. Nessuno dei tre `down` porta `-v`: i volumi restano, i dati anche.

<a id="b4"></a>

### B.4 — Quando Docker stesso non risponde

1. `docker context show` — è quello giusto?
2. `which docker` — il binario è quello del contesto? (Il 24 agosto non lo era, e l'errore era
   illeggibile.)
3. Riavvio di Docker Desktop, e si perdono **due minuti**: si passa alle registrazioni e si
   riavvia in sottofondo.
4. Se non torna: **filmati MP4** da `~/SqlStart2026-registrazioni`, e il talk continua. È
   esattamente il caso per cui esistono.

<a id="b5"></a>

### B.5 — Le tre righe che valgono più di tutte le altre

```bash
make preflight                                          # cosa non va, tutto insieme
./tools/reset-demo.sh 02                                # rimetti la scena com'era
python3 tools/registra-terminale.py --riproduci docs/05-talk/registrazioni/12-app-failover-e-i-due-numeri.cast
```

La prima prima di cominciare, la seconda fra una prova e l'altra, la terza quando la prima e la
seconda non sono bastate.

---

## Il debito di questo documento

Il runbook è scritto il **6 settembre 2026**, dieci giorni prima della data prevista per la
`release/1.0`, e prima della prova generale cronometrata del 17. Due cose restano da chiudere, e
sono scritte qui perché chi legge sappia che cosa non è ancora stato verificato:

- **I tempi della §2 sono quelli del design, non quelli misurati.** La ripartizione 4 / 13 / 8 / 2
  viene dal §9.1 della specifica ed è coerente con le durate delle registrazioni, ma nessuno l'ha
  ancora cronometrata **parlando sopra**. È esattamente ciò che la prova generale del 17 deve
  produrre, e i numeri di questa tabella vanno riscritti con quelli veri.
- **L'appuntamento di ADR-0058 sulla 8.0.30 è ancora aperto**, e la sua data è il **16 settembre**,
  non oggi: è l'ultimo momento utile per ripinnare e rigirare le registrazioni prima del talk. Il
  primo dei due controlli è stato speso ed è andato a vuoto. Aprire la release in anticipo **non**
  sposta il secondo: la procedura, sui tre canali, è in [V-074](../Sources.md#v-074).
