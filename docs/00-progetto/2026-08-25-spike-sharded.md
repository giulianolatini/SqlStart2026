# Spike dello sharded cluster — 2026-08-25

Uno spike è un esperimento con una domanda e una scadenza, non un pezzo di prodotto. Questo
aveva una domanda sola: **lo sharded cluster in Docker Compose, con autenticazione interna a
keyfile, funziona come il design lo ha immaginato?** Lo sharded cluster è il punto di massima
incertezza del progetto, e il momento per scoprirlo è adesso — non il 14 settembre.

Il codice dello spike è stato cancellato al termine, come previsto. Quello che resta è questo
verbale: il file Compose che ha funzionato, i numeri misurati, e i punti in cui il design si
era sbagliato.

**Esito in una riga:** la topologia funziona ed entra nella VM con largo margine; ma nessuna
versione di MongoDB 8 attualmente pubblicata si avvia sul kernel della VM di Docker Desktop, e
questo è un problema che riguarda il progetto intero, non solo lo sharded cluster.

---

## Ambiente

| Voce | Valore |
|---|---|
| Docker Engine / client | 29.7.2 |
| Docker Compose | v5.4.0 |
| Kernel della VM | `7.0.12-linuxkit` |
| Sistema della VM | Docker Desktop, `aarch64` |
| Memoria assegnata alla VM | 11.946 MiB (11,67 GiB), 8 CPU |
| Host | macOS arm64, 16 GiB |

---

## 1. Il blocco: MongoDB 8 non parte su questo kernel

Al primo avvio il config server è uscito immediatamente con codice 1:

```json
{"s":"F","c":"CONTROL","id":12257600,"ctx":"main","msg":"MongoDB cannot start: Linux
kernel versions 6.19 and newer has a known incompatibility with this version of MongoDB.
See https://jira.mongodb.org/browse/SERVER-121912 for more information."}
```

Non è un problema di configurazione: il controllo scatta in `main`, prima ancora che mongod
legga i parametri. Lo si ottiene identico con `mongod --version`, che è il modo più economico
per verificarlo.

### Cosa è stato provato

| Prova | Esito |
|---|---|
| `mongo:8.0` (= 8.0.29, ultima patch pubblicata della 8.0) | rifiuta di partire |
| `mongo:8.0.29` esplicita | rifiuta di partire |
| `mongo:8.3` (= 8.3.8, stabile corrente) | rifiuta di partire |
| `mongo:8.2` (= 8.2.12) | **parte** |
| `mongo:7.0` (= 7.0.40) | **parte** |
| `GLIBC_TUNABLES=glibc.pthread.rseq=0` su 8.0 | rifiuta lo stesso |
| `--setParameter tcmallocEnablePerCPUCaches=false` su 8.0 | rifiuta lo stesso |
| `mongo:8.0.30` (la patch che contiene la correzione) | **non esiste**: né su Docker Hub, né su `mongodb/mongodb-community-server`, né in `downloads.mongodb.org/current.json` |

Nessuna variabile d'ambiente e nessun parametro di avvio aggira il controllo. Cercando nel
binario compaiono i simboli `isKernelVersionSafeForTCMallocPerCPUCache` e
`validateRseqKernelCompat`, ma nessun interruttore che li disattivi.

### Perché succede

La causa è l'allocatore TCMalloc, che nella sua cache per-CPU usa `rseq` (*restartable
sequences*) in un modo che viola l'ABI del kernel; dal 6.19 in poi il kernel lo fa saltare.
MongoDB ha reagito in due tempi: prima sostituendo il crash con un'uscita pulita e un
messaggio comprensibile — è il controllo che vediamo — poi restringendo il controllo ai soli
kernel dai quali il problema si manifesta davvero [S-027](../Sources.md#s-027).

Questa cronologia spiega la tabella qui sopra, che altrimenti sembra assurda:

- **8.2.12 parte** non perché sia sana, ma perché è *precedente* all'introduzione del
  controllo. Sta girando sul percorso difettoso. È la stessa famiglia per cui è segnalato un
  ciclo di crash con SIGSEGV sul kernel 6.19.
- **8.3.8 rifiuta** perché è *successiva* al controllo ma precedente alla correzione.
- **8.0.30 funzionerebbe**, perché contiene il ticket che restringe il controllo ai kernel
  dal 7.0.14 in su — e il nostro è il 7.0.12. Ma la 8.0.30 compare solo nel changelog: i
  binari non sono pubblicati [S-027](../Sources.md#s-027).
- **7.0.40 parte** perché la 7.0 usa una versione precedente di TCMalloc: il difetto
  riguarda la 8.0 e successive.

### Perché non basta scegliere «quella che parte»

La tentazione è usare la 8.2.12, che parte ed è una MongoDB 8. È la scelta peggiore delle tre.
Con la 8.2 MongoDB ha cambiato schema di rilascio: esistono *Major Releases*, ogni due anni e
con cinque anni di ciclo di vita, e *Minor Releases*. Delle seconde la documentazione dice due
cose, e la seconda è decisiva [S-027](../Sources.md#s-027):

> «They are as stable as major releases and suitable for production workloads.»

> «After a new minor release becomes available, MongoDB does not continue patching the
> previous minor release.»

Uscita la 8.3, la 8.2 non riceve più patch. Non è un ramo su cui appoggiare un lab che deve
restare consultabile dopo il talk — e infatti fra i tag correnti dell'immagine ufficiale la
8.2 non compare più: ci sono 8.3.8, 8.0.29 e 7.0.40, e basta.

### Cosa resta aperto

Questa è una **decisione, non un dettaglio tecnico**: cambia [ADR-0008](../Decision.md#adr-0008),
che fissa MongoDB 8.0 pinnata per digest, e con essa `tools/images.env` e ogni stack futuro.
Le opzioni sono in fondo a questo verbale, § *Decisione da prendere*.

Vale la pena notare che **non è un problema solo nostro**: chiunque, in sala, avvii oggi
MongoDB 8 su Docker Desktop incontra lo stesso muro. È materiale da
`02-architetture/trappole-mongodb-in-docker.md`, ed è il genere di trappola che vale più di
una slide teorica.

---

## 2. `MONGO_INITDB_ROOT_*` non funziona su un config server

Il design prevedeva di creare l'utente amministratore passando `MONGO_INITDB_ROOT_USERNAME` e
`MONGO_INITDB_ROOT_PASSWORD` al config server. Il container esce subito:

```
BadValue: Cannot start a configsvr as a standalone server. Please use the option
--replSet to start the node as a replica set.
```

Il motivo sta nell'entrypoint dell'immagine ufficiale [S-022](../Sources.md#s-022): per creare
l'utente, avvia un mongod temporaneo, e per farlo **toglie `--replSet`** dalla riga di comando
— ma solo se entrambe le variabili sono presenti. Non toglie però `--configsvr`, e un config
server senza replica set si rifiuta di partire. Le due cose sono incompatibili per costruzione.

**Come si fa invece:** si avvia il nodo *senza* variabili di root, si esegue `rs.initiate()` e
poi si crea l'utente, entrambi sotto l'eccezione localhost.

---

## 3. `rs.initiate()` va scritto con i nomi dei servizi Compose

`rs.initiate()` senza argomenti usa l'hostname del container, che è l'ID generato da Docker.
Il replica set si inizializza, sembra funzionare, e poi mongos non riesce a raggiungerlo,
perché quell'hostname non è risolvibile dagli altri container. I membri vanno elencati per
nome di servizio:

```javascript
rs.initiate({ _id: "cfgrs", configsvr: true, members: [
  { _id: 0, host: "cfg1:27017" },
  { _id: 1, host: "cfg2:27017" },
  { _id: 2, host: "cfg3:27017" }
]})
```

---

## 4. L'eccezione localhost concede meno di quanto sembri

Con `--keyFile` l'autorizzazione è attiva. Finché non esiste alcun utente vale l'eccezione
localhost — ma **consente soltanto di creare il primo utente o ruolo**, non di eseguire
comandi qualsiasi. Un `db.adminCommand({hostInfo: 1})` su un nodo senza utenti risponde:

```
MongoServerError: not authorized on admin to execute command { hostInfo: 1, ... }
```

`rs.initiate()` passa perché su un replica set non ancora inizializzato è ammesso a parte.

C'è un secondo strato, e sorprende. Gli utenti creati sul config server sono gli utenti *del
cluster*: valgono su mongos, non per una connessione diretta a uno shard. Per ispezionare uno
shard da vicino — ed è quello che fa una demo di amministrazione — serve un utente **locale a
quello shard**, creato sul nodo prima o dopo `sh.addShard()`. Con le credenziali del cluster
la connessione diretta risponde `Authentication failed`.

---

## 5. La topologia funziona

Catena di inizializzazione completa, nell'ordine, per il profilo `completo`:

1. `keyfile-init` genera il keyfile con `openssl rand -base64 756`, lo assegna a `999:999` e
   lo porta a `chmod 400` [S-023](../Sources.md#s-023).
2. I nove `mongod` partono con `--keyFile` e diventano `healthy`.
3. `rs.initiate()` con host espliciti su `cfg1`, `shard1a`, `shard2a`.
4. `db.createUser()` per `root` sul config server, sotto eccezione localhost.
5. I due `mongos` partono e diventano `healthy`.
6. `sh.addShard()` per entrambi gli shard, autenticato come `root`.

Risultato, dopo aver distribuito una collezione con shard key `{_id: "hashed"}`:

| Prova | Esito |
|---|---|
| `sh.status()` | due shard `state: 1`, balancer attivo |
| 20.000 documenti (profilo `palco`) | 4 chunk, 50,7 % / 49,3 % fra i due shard |
| 50.000 documenti (profilo `completo`) | distribuiti su entrambi gli shard |

### Failover

Fermato il primario di `shard1rs` con `docker stop`:

```
prima:  shard1a=PRIMARY   shard1b=SECONDARY  shard1c=SECONDARY
dopo:   shard1a=(not reachable/healthy)  shard1b=PRIMARY  shard1c=SECONDARY
```

Con il nodo giù, attraverso mongos: **50.000 letture e una scrittura riuscite**. Riavviato il
container, `shard1a` è rientrato come `SECONDARY` senza intervento. È la demo del talk, provata
in anticipo.

---

## 6. I due profili, misurati

`profiles` si comporta esattamente come serve:

```
docker compose --profile palco    config --services  ->  5  (keyfile-init + 4)
docker compose --profile completo config --services  -> 12  (keyfile-init + 11)
docker compose                    config --services  ->  1  (solo keyfile-init)
```

Il servizio condiviso porta due profili — `profiles: ["palco", "completo"]` — e i nodi in più
solo `completo`. `keyfile-init` resta **senza profilo**, ed è deliberato: la dipendenza va
allora da un servizio con profilo verso uno senza, che è l'unica direzione su cui la
documentazione di Compose si sbilancia. La riserva dichiarata in
[ADR-0010](../Decision.md#adr-0010) resta quindi aggirata anziché sciolta — ma aggirata per
costruzione, non per fortuna.

### Memoria: la riserva di ADR-0025 è sciolta

Undici container in esecuzione, cluster popolato:

| Componente | Limite | Uso reale |
|---|---|---|
| `cfg1` / `cfg2` / `cfg3` | 512 MiB ciascuno | 153 / 138 / 136 MiB |
| `shard1a` / `shard1b` / `shard1c` | 640 MiB ciascuno | 121 / 122 / 283 MiB |
| `shard2a` / `shard2b` / `shard2c` | 640 MiB ciascuno | 123 / 121 / 117 MiB |
| `mongos` / `mongos2` | 384 MiB ciascuno | 21 / 21 MiB |
| **Totale** | **6.144 MiB (6,0 GiB)** | **1.356 MiB (1,32 GiB)** |

Nella VM, a cluster acceso: 2.705 MiB usati, 9.021 MiB disponibili degli 11.946 totali.

Gli undici container ci stanno, e con margine largo. Va però letto per quello che è:
`mem_limit` è un **tetto, non una prenotazione**. Docker non mette da parte 6 GiB; ne servono
1,32 a riposo. I 12 GiB di [ADR-0025](../Decision.md#adr-0025) restano la scelta giusta perché
coprono il caso in cui i container si avvicinino ai loro tetti sotto carico — che è
esattamente ciò che l'applicazione del talk andrà a provocare.

---

## 7. Due domande aperte, chiuse per strada

### La cache WiredTiger nei container

`Sources.md` registrava una contraddizione fra [S-001](../Sources.md#s-001) e
[S-026](../Sources.md#s-026) sul rilevamento dei limiti di memoria nei container. La misura la
scioglie: **non si contraddicono, descrivono due campi diversi.**

```
hostInfo.system.memSizeMB  = 11946   <- la memoria della VM
hostInfo.system.memLimitMB = 640     <- il mem_limit del container
```

E il limite del container è quello che guida la cache, come ADR-0004 assumeva senza averlo
misurato. Due mongod senza `--wiredTigerCacheSizeGB`, solo con limiti diversi:

| `mem_limit` | Cache WiredTiger scelta da sola |
|---|---|
| 640 MiB | 256 MiB — il pavimento |
| 4.096 MiB | 1.536 MiB = 0,5 × (4.096 − 1.024) |

La formula `max(0,5 × (RAM − 1 GiB), pavimento)` si applica alla memoria del **container**. Da
notare per la pagina sulle risorse: il pavimento reale misurato è 268.435.456 byte, cioè 256
MiB esatti; la documentazione lo scrive «0.256 GB», che è la stessa cosa detta male.

### `compose up` e la rete

[ADR-0009](../Decision.md#adr-0009) lasciava aperto se `docker compose up` contatti il registro
quando l'immagine è pinnata per digest ed è già in cache. La domanda si è rivelata mal posta:
invece di dimostrare che Compose non esce, conviene **impedirglielo**, con `pull_policy: never`.

| Caso | Esito | Tempo |
|---|---|---|
| digest presente in cache | container avviato | 0,674 s |
| digest inesistente | `No such image`, uscita in errore | **0,110 s** |

Il decimo di secondo è la prova: non c'è stato alcun tentativo di rete. Ed è il fallimento
giusto — immediato e leggibile — invece di un timeout di trenta secondi in sala.

---

## 8. Il file Compose che ha funzionato

Da riportare in `docker/03-sharded/` quando la feature sarà avviata. Le `mem_limit` sono
quelle di §5.1 del design; `pull_policy: never` è l'aggiunta di §7.

```yaml
name: sqlstart-sharded

x-mongo: &mongo
  image: ${MONGO_IMAGE}
  pull_policy: never
  restart: "no"
  cpus: 0.5

x-sonda: &sonda
  test: ["CMD", "mongosh", "--quiet", "--eval", "db.adminCommand('ping').ok"]
  interval: 3s
  timeout: 5s
  retries: 30
  start_period: 5s

x-attesa-keyfile: &attesa-keyfile
  keyfile-init:
    condition: service_completed_successfully

x-cfg: &cfg
  <<: *mongo
  mem_limit: 512m
  command: >
    mongod --configsvr --replSet cfgrs --port 27017 --bind_ip_all
           --keyFile /keyfile/mongo-keyfile --wiredTigerCacheSizeGB 0.25
  healthcheck: *sonda
  depends_on: *attesa-keyfile

x-shard1: &shard1
  <<: *mongo
  mem_limit: 640m
  command: >
    mongod --shardsvr --replSet shard1rs --port 27017 --bind_ip_all
           --keyFile /keyfile/mongo-keyfile --wiredTigerCacheSizeGB 0.25
  healthcheck: *sonda
  depends_on: *attesa-keyfile

x-shard2: &shard2
  <<: *mongo
  mem_limit: 640m
  command: >
    mongod --shardsvr --replSet shard2rs --port 27017 --bind_ip_all
           --keyFile /keyfile/mongo-keyfile --wiredTigerCacheSizeGB 0.25
  healthcheck: *sonda
  depends_on: *attesa-keyfile

x-mongos: &mongos
  <<: *mongo
  mem_limit: 384m
  command: >
    mongos --configdb cfgrs/cfg1:27017,cfg2:27017,cfg3:27017 --port 27017
           --bind_ip_all --keyFile /keyfile/mongo-keyfile
  healthcheck: *sonda
  volumes:
    - keyfile:/keyfile:ro

services:
  # Senza profilo: serve a entrambi. La dipendenza va da un servizio con profilo
  # verso uno senza, che è l'unica direzione documentata da Compose.
  keyfile-init:
    image: ${MONGO_IMAGE}
    pull_policy: never
    restart: "no"
    user: root
    volumes:
      - keyfile:/keyfile
    command:
      - bash
      - -c
      - |
        set -e
        if [ ! -s /keyfile/mongo-keyfile ]; then
          openssl rand -base64 756 > /keyfile/mongo-keyfile
        fi
        chown 999:999 /keyfile/mongo-keyfile
        chmod 400 /keyfile/mongo-keyfile
        ls -ln /keyfile/mongo-keyfile

  cfg1:
    <<: *cfg
    profiles: ["palco", "completo"]
    volumes: [keyfile:/keyfile:ro, cfg1-data:/data/db]
    ports: ["27131:27017"]

  cfg2:
    <<: *cfg
    profiles: ["completo"]
    volumes: [keyfile:/keyfile:ro, cfg2-data:/data/db]
    ports: ["27132:27017"]

  cfg3:
    <<: *cfg
    profiles: ["completo"]
    volumes: [keyfile:/keyfile:ro, cfg3-data:/data/db]
    ports: ["27133:27017"]

  shard1a:
    <<: *shard1
    profiles: ["palco", "completo"]
    volumes: [keyfile:/keyfile:ro, shard1a-data:/data/db]
    ports: ["27141:27017"]

  shard1b:
    <<: *shard1
    profiles: ["completo"]
    volumes: [keyfile:/keyfile:ro, shard1b-data:/data/db]
    ports: ["27142:27017"]

  shard1c:
    <<: *shard1
    profiles: ["completo"]
    volumes: [keyfile:/keyfile:ro, shard1c-data:/data/db]
    ports: ["27143:27017"]

  shard2a:
    <<: *shard2
    profiles: ["palco", "completo"]
    volumes: [keyfile:/keyfile:ro, shard2a-data:/data/db]
    ports: ["27151:27017"]

  shard2b:
    <<: *shard2
    profiles: ["completo"]
    volumes: [keyfile:/keyfile:ro, shard2b-data:/data/db]
    ports: ["27152:27017"]

  shard2c:
    <<: *shard2
    profiles: ["completo"]
    volumes: [keyfile:/keyfile:ro, shard2c-data:/data/db]
    ports: ["27153:27017"]

  mongos:
    <<: *mongos
    profiles: ["palco", "completo"]
    ports: ["27117:27017"]

  mongos2:
    <<: *mongos
    profiles: ["completo"]
    ports: ["27118:27017"]

volumes:
  keyfile:
  cfg1-data:
  cfg2-data:
  cfg3-data:
  shard1a-data:
  shard1b-data:
  shard1c-data:
  shard2a-data:
  shard2b-data:
  shard2c-data:
```

Nel profilo `palco` il `--configdb` elenca `cfg2` e `cfg3`, che non esistono. Non è un
problema: mongos li usa come semi, scopre la configurazione reale da `cfg1` e ignora i semi
irraggiungibili. È stato verificato: con il solo `cfg1` acceso, mongos diventa `healthy` e il
cluster serve.

---

## 9. Decisione da prendere

La topologia è validata. Resta la versione, e la sceglie il relatore perché supera una
decisione già accettata.

| Opzione | Pro | Contro |
|---|---|---|
| **A. 7.0.40** | è l'unica versione pubblicata che parte oggi su questo kernel; Major Release, ciclo di vita quinquennale; il difetto non la riguarda | una major indietro rispetto a quanto ci si aspetta da un talk del 2026 |
| **B. 8.2.12** | è una MongoDB 8 e parte | non riceve più patch, non è più fra i tag ufficiali, e parte solo perché precede il controllo: sta girando sul percorso difettoso |
| **C. aspettare la 8.0.30** | conserva [ADR-0008](../Decision.md#adr-0008) intatta | i binari non esistono; mancano ventiquattro giorni al talk e non c'è una data |
| **D. cambiare runtime o kernel** | terrebbe la 8.0 | chi clona il repository dovrebbe replicare una versione precisa di Docker Desktop: un lab che chiede questo non è riproducibile |

**Raccomandazione: A, con C come traguardo.** Si sviluppa su 7.0.40 adesso, e si ripinna alla
8.0.30 appena esce. Costa poco perché la versione è una variabile sola: `${MONGO_IMAGE}` negli
stack, `tools/images.env` rigenerato da `make images-pull`. Se la 8.0.30 arriva prima del 18
settembre si ripinna e si rigirano i filmati; se non arriva, il lab funziona lo stesso.

Qualunque sia la scelta, un obbligo resta: **il preflight deve provare ad avviare l'immagine
pinnata**, non limitarsi a verificare che sia in cache. Questo guasto sarebbe passato indenne
attraverso ogni controllo esistente fino al momento del `compose up` sul palco.

---

**Fonti:** [S-022](../Sources.md#s-022), [S-023](../Sources.md#s-023),
[S-027](../Sources.md#s-027), [V-006](../Sources.md#v-006), [V-007](../Sources.md#v-007)
