# Trappole di MongoDB in Docker

Questa pagina raccoglie i punti in cui MongoDB e Docker si fraintendono. Hanno tutti la stessa
firma: **non producono un messaggio d'errore che nomini la causa.** Qualcosa non c'è, o non
riparte, o non risponde, e il log tace o parla d'altro.

Per questo ogni voce **comincia dal sintomo**, che è l'unica cosa che si ha in mano quando
capita, e ha sempre le stesse quattro righe: *sintomo*, *causa*, *rimedio*, *fonte*. Il contratto
della pagina è [ADR-0033](../Decision.md#adr-0033); le voci si aggiungono in coda e non si
riscrivono, così la numerazione resta un riferimento stabile.

La pagina nasce con `feature/01` e cresce: `feature/02` ha aggiunto le due trappole del replica
set — i **permessi del keyfile**, voce [12](#t-12), e la **scoperta della topologia**, voce
[13](#t-13) — e `feature/03` aggiungerà quelle dello sharded cluster.

**Indice dei sintomi**

| # | Quello che si vede |
|---:|---|
| [1](#t-01) | il dataset non c'è, e nel log non c'è traccia degli script di inizializzazione |
| [2](#t-02) | il container esce subito dopo l'avvio e il log non dice perché |
| [3](#t-03) | il config server parte «bene» e il cluster non si forma mai |
| [4](#t-04) | «connection refused» verso un nodo che è acceso e sano |
| [5](#t-05) | «getaddrinfo ENOTFOUND» su un nome che nel file Compose c'è |
| [6](#t-06) | ho ucciso il container e `restart: unless-stopped` non l'ha rialzato |
| [7](#t-07) | `kill -9 1` dentro il container esce con successo e non succede niente |
| [8](#t-08) | `docker compose logs` non mostra niente, ma il server sta lavorando |
| [9](#t-09) | `logRotate` risponde `{ok: 1}` e non ruota niente |
| [10](#t-10) | il disco si riempie durante la demo |
| [11](#t-11) | chiunque raggiunga la porta è amministratore |
| [12](#t-12) | `mongod` non parte e dice che il keyfile è «too open» |
| [13](#t-13) | il driver prova a raggiungere un host che io non ho mai scritto |

---

<a id="t-01"></a>
## 1. Il dataset non c'è, e nel log non c'è traccia degli script di inizializzazione

**Sintomo.** Si monta una cartella su `/docker-entrypoint-initdb.d`, si avvia lo stack, il
container diventa `healthy` — e le collezioni sono vuote. In `docker compose logs` non c'è
nessuna riga che nomini gli script: né un errore, né un avviso, né una menzione. Sembra che il
montaggio non sia stato fatto.

**Causa.** L'entrypoint ufficiale esegue quegli script **solo alla prima inizializzazione del
volume**, e quando decide di saltarli non lo dice. Il criterio non è nemmeno «la cartella dei
dati è vuota»: l'entrypoint cerca la presenza di uno fra quattro percorsi noti, e se ne trova
uno considera il database già inizializzato. Un volume nominato sopravvive a `docker compose
down`, quindi al secondo avvio in poi l'inizializzazione non riparte più — anche se nel
frattempo gli script sono cambiati.

**Rimedio.** Distinguere i due casi:

- *voglio davvero ricaricare da zero*: eliminare il volume, non solo il container. Nel lab è
  `make reset-01`, che è un target separato apposta — un `docker compose down -v` involontario
  alla vigilia del talk è un dataset da ricostruire.
- *voglio caricare dati su un volume che deve restare*: gli script di init non servono. Serve
  una strada esplicita, che nel lab è `make seed-01` ([ADR-0031](../Decision.md#adr-0031)).

In entrambi i casi, non fidarsi del silenzio: verificare il conteggio dei documenti, che è
l'unica prova che il caricamento sia avvenuto.

**Fonte.** [V-014](../Sources.md#v-014) (misurata: nessuna riga di log allo skip),
[S-034](../Sources.md#s-034) (l'entrypoint `7.0`, i quattro percorsi),
[ADR-0031](../Decision.md#adr-0031).

---

<a id="t-02"></a>
## 2. Il container esce subito dopo l'avvio e il log non dice perché

**Sintomo.** `docker compose up -d` riesce, e pochi secondi dopo il container è `exited`. Il log
si ferma a metà dell'avvio, senza una riga di errore che spieghi cosa manchi. Rilanciarlo dà lo
stesso risultato, sempre nello stesso punto.

**Causa.** L'immagine richiede al kernel qualcosa che quel kernel non offre. Nel caso incontrato
qui: **nessuna versione pubblicata di MongoDB 8.x si avvia sul kernel della VM di Docker
Desktop** su questa macchina. Il processo non arriva a un punto in cui abbia un logger
configurato, quindi non c'è nessuno che possa scrivere il messaggio utile.

Il tranello secondario è che il sintomo assomiglia a mille altre cose — un volume con permessi
sbagliati, un comando malformato, la memoria insufficiente — e si perde tempo a escluderle.

**Rimedio.** Prima di tutto separare «l'immagine non parte» da «la mia configurazione non va»:
avviare l'immagine nuda, senza volumi, senza comando, senza limiti. Se esce anche così, la
configurazione è innocente. Poi provare la versione precedente: se quella parte, il problema è
la coppia kernel/versione e non il file Compose.

Nel lab la conclusione è scritta e pinnata: si esegue MongoDB 7.0.40, per digest
([ADR-0028](../Decision.md#adr-0028)). La versione non è una preferenza, è un vincolo misurato.

**Fonte.** [V-007](../Sources.md#v-007) (quali versioni si avviano su quel kernel),
[ADR-0028](../Decision.md#adr-0028).

---

<a id="t-03"></a>
## 3. Il config server parte «bene» e il cluster non si forma mai

**Sintomo.** Si aggiungono `MONGO_INITDB_ROOT_USERNAME` e `MONGO_INITDB_ROOT_PASSWORD` a un
servizio che ha `--replSet` — tipicamente un config server o un membro di replica set — per
crearsi l'utente amministrativo al primo avvio. Il container parte, il log sembra normale, e poi
l'inizializzazione del cluster non arriva mai a compimento.

**Causa.** L'entrypoint, prima di eseguire gli script di inizializzazione, avvia un `mongod`
**temporaneo** e ne ripulisce la riga di comando. Le rimozioni non seguono però tutte la stessa
regola:

- `--auth` e `--keyFile` vengono tolti **sempre**;
- `--replSet` viene tolto **solo se sono presenti entrambe** le variabili root.

Chi ne imposta una sola ottiene un `mongod` temporaneo che è ancora membro di un replica set non
inizializzato, e quel processo non si comporta come l'entrypoint si aspetta. C'è poi un secondo
inciampo, indipendente: il `dbPath` predefinito di un config server è `/data/configdb`, non
`/data/db`, quindi il volume montato nel posto abituale non è quello che il processo usa.

**Rimedio.** Sul lab la scelta è a monte: lo stack 01 gira senza autenticazione per progetto
([ADR-0005](../Decision.md#adr-0005)), e sugli stack 02 e 03 le credenziali si creano dopo
l'inizializzazione del replica set, non durante l'avvio del container. Se si vogliono comunque
usare le variabili root, impostarle **entrambe** — mai una sola — e montare il volume del config
server su `/data/configdb`.

**Fonte.** [V-006](../Sources.md#v-006) (lo spike dello sharded cluster, dove è emerso),
[S-034](../Sources.md#s-034) e [S-022](../Sources.md#s-022) (gli entrypoint `7.0` e `8.0`),
[ADR-0005](../Decision.md#adr-0005).

---

<a id="t-04"></a>
## 4. «Connection refused» verso un nodo che è acceso e sano

**Sintomo.** Un container si collega a un altro con `mongodb://localhost:27017` e riceve
`MongoNetworkError: connect ECONNREFUSED 127.0.0.1:27017`. Il nodo di destinazione, controllato
a mano, è `running` e `healthy`. La stessa stringa di connessione funzionava benissimo dal
portatile.

**Causa.** `localhost` non è un posto: è un punto di vista. Dentro un container significa *quel*
container, e quasi mai è quello che ospita il database. La stringa funzionava dal portatile
perché lì `localhost:27017` è la porta **pubblicata** da `ports:`, che è un percorso
completamente diverso.

Il dettaglio da cui riconoscere il caso è il testo dell'errore: `ECONNREFUSED` significa che il
nome **ha risolto** e che qualcuno ha risposto «qui non c'è niente su questa porta». Il nome era
valido, la macchina era sbagliata.

**Rimedio.** Fra container si usa il **nome del servizio**, che il DNS interno di Docker risolve
per tutti quelli attaccati alla stessa rete. Nel lab i servizi hanno anche `hostname:` esplicito
sul nome del servizio, così le due strade coincidono
([ADR-0021](../Decision.md#adr-0021)). Dall'host si usa `localhost` più la porta pubblicata, che
è l'unica cosa che l'host sa raggiungere.

Sul replica set questa trappola smette di essere un fastidio e diventa un guasto: i membri
annunciano ai client gli indirizzi con cui sono stati configurati, quindi un `rs.initiate()`
fatto con `localhost` produce un cluster che dice a tutti di connettersi a se stessi
([S-020](../Sources.md#s-020)).

**Fonte.** [V-018](../Sources.md#v-018) (gli otto tentativi da quattro posizioni),
[ADR-0021](../Decision.md#adr-0021), [S-020](../Sources.md#s-020).

---

<a id="t-05"></a>
## 5. «getaddrinfo ENOTFOUND» su un nome che nel file Compose c'è

**Sintomo.** Si usa il nome del servizio, come da manuale, e la risposta è
`MongoNetworkError: getaddrinfo ENOTFOUND mongo-standalone`. Il nome è scritto giusto, il
servizio è in piedi, il file Compose è quello.

**Causa.** È l'errore gemello del precedente, e dice una cosa diversa: il nome **non ha risolto
affatto**. Il DNS interno di Docker risponde solo a chi è attaccato a quella rete. Chi chiede da
fuori — un container avviato senza `--network`, un processo sull'host, uno stack Compose diverso
— non riceve nessuna risposta, perché per lui quel nome non esiste.

Sull'host il fenomeno ha una causa in più: la risoluzione dei nomi lì non dipende da Docker ma
dal sistema operativo, che di quei nomi non sa niente.

**Rimedio.** Decidere da dove ci si connette, e usare la strada che corrisponde:

| Da dove | Cosa usare |
|---|---|
| stesso stack Compose | nome del servizio |
| stack Compose diverso | attaccare i due stack a una rete comune, dichiarandola |
| host | `localhost` + porta pubblicata da `ports:` |
| container avviato a mano | `docker run --network <rete_dello_stack> …` |

Il modo più rapido per distinguere i due errori: `ECONNREFUSED` è la voce 4 di questa pagina — il
nome ha risolto verso il posto sbagliato. `ENOTFOUND` è questa — il nome non ha risolto.

**Fonte.** [V-018](../Sources.md#v-018), [ADR-0021](../Decision.md#adr-0021).

---

<a id="t-06"></a>
## 6. Ho ucciso il container e `restart: unless-stopped` non l'ha rialzato

**Sintomo.** Il file Compose dichiara `restart: unless-stopped`. Si simula un guasto con
`docker kill`, e il container resta `exited` per sempre. `docker inspect` mostra
`ExitCode=137`, `OOMKilled=false` e — la riga che sorprende — `RestartCount=0`: il demone non ha
nemmeno **provato**.

**Causa.** Per Docker un `docker kill` non è un guasto: è una fermata chiesta da un umano. E dopo
una fermata la politica di riavvio smette di applicarsi, «until the Docker daemon restarts or
the container is manually restarted» ([S-039](../Sources.md#s-039)).

La documentazione lo copre con una parentesi — il container «is stopped (manually or otherwise)»
— e la pagina di `docker kill` non contiene mai la parola «restart»
([S-040](../Sources.md#s-040)). Non c'è modo, leggendo, di prevederlo.

La prova che la politica sia sana è il caso simmetrico: se `mongod` termina **da sé**, lo stesso
container riparte da solo in pochi secondi, con `RestartCount=1`.

**Rimedio.** Nessuno, perché non è un difetto da riparare: è una definizione da conoscere.

- Per rialzare il container dopo un `docker kill`: `docker start`, oppure `docker compose up -d`.
- Per **dimostrare** che la politica di riavvio funziona, non usare `docker kill`: far terminare
  il processo da sé, che è la via misurata in cui il demone interviene.
- Nelle demo, dire quello che si sta facendo. `docker kill` simula uno spegnimento, non un
  crash. Il lab lo dichiara invece di fingere ([ADR-0034](../Decision.md#adr-0034)).

**Fonte.** [V-017](../Sources.md#v-017) (le tre prove affiancate),
[S-039](../Sources.md#s-039), [S-040](../Sources.md#s-040),
[ADR-0034](../Decision.md#adr-0034).

---

<a id="t-07"></a>
## 7. `kill -9 1` dentro il container esce con successo e non succede niente

**Sintomo.** Per far morire il processo «dall'interno» si esegue `docker exec <container> kill -9
1`. Il comando ritorna **zero**, senza stdout e senza stderr. Il container però è ancora
`running` e `healthy`, e `RestartCount` non si muove.

**Causa.** Non è Docker, è il kernel Linux. Il processo con PID 1 in un namespace è l'«init» di
quel namespace, e riceve dagli altri membri **solo** i segnali per cui ha installato un gestore —
«even to privileged processes», precisa il manuale. `SIGKILL` per definizione non è gestibile,
quindi viene scartato. Il `kill` riesce (i controlli di permesso passano) e non produce alcun
effetto ([S-041](../Sources.md#s-041)).

Dal namespace **antenato** la regola si rovescia: `SIGKILL` e `SIGSTOP` «are forcibly delivered
when sent from an ancestor PID namespace». Il demone Docker sta lì, ed è il motivo per cui
`docker kill` arriva a destinazione mentre `kill -9 1` no.

**Rimedio.** Per fermare il container si usano gli strumenti del runtime — `docker stop`,
`docker kill` — che agiscono dal namespace giusto. Se serve terminare un processo *dentro* il
container, deve essere un processo che non sia PID 1. Se serve far morire il servizio
«naturalmente», si chiede al servizio di spegnersi: su MongoDB è il comando `shutdown`, ed è
anche l'unica via che fa scattare la politica di riavvio (voce [6](#t-06)).

**Fonte.** [V-017](../Sources.md#v-017) (misurato: `rc=0`, nessun effetto),
[S-041](../Sources.md#s-041) (`pid_namespaces(7)`).

---

<a id="t-08"></a>
## 8. `docker compose logs` non mostra niente, ma il server sta lavorando

**Sintomo.** Il database risponde, le query funzionano, l'healthcheck è verde — e
`docker compose logs` è **vuoto**. Sembra un problema del driver di log, o dei permessi, o della
configurazione di Compose.

**Causa.** Nel comando c'è `--logpath` (o `systemLog.path` nel file di configurazione). L'aiuto
del binario lo dice con una parola che è facile leggere di sfuggita: «Log file to send write to
**instead of** stdout». È una **redirezione**, non una duplicazione: attivarla non aggiunge un
file, toglie lo stdout. E il canale che Docker raccoglie è esattamente quello.

Misurato: con `--logpath` attivo il file contiene 65 righe e `docker logs` ne contiene zero
([V-010](../Sources.md#v-010)).

**Rimedio.** In container, **non** impostare `--logpath`: lasciare che `mongod` scriva su stdout,
che è la convenzione dei container e l'unica strada per cui `docker compose logs`, i driver di
log e gli aggregatori funzionino. Se un file serve davvero — per un archivio, per un obbligo —
va prodotto dal runtime a valle, non spegnendo lo stdout a monte.

La conseguenza da non dimenticare: se il log sta su stdout, **ruotarlo non è più affare di
`mongod`**. Vedi la voce [10](#t-10).

**Fonte.** [V-010](../Sources.md#v-010), [S-032](../Sources.md#s-032),
[ADR-0030](../Decision.md#adr-0030).

---

<a id="t-09"></a>
## 9. `logRotate` risponde `{ok: 1}` e non ruota niente

**Sintomo.** Si esegue `db.adminCommand({logRotate: 1})` per ruotare i log. La risposta è
`{ "ok": 1 }`. Nel log compare pure la conferma, `"msg":"Log rotation initiated"`. Sul
filesystem non è cambiato assolutamente niente.

**Causa.** Il comando ruota il **file** di log. Se il log va su stdout non c'è nessun file da
ruotare, e il comando non ha modo di dirlo: riporta comunque `ok: 1`. L'unico indizio è dentro la
riga di log stessa, dove `"logType"` vale `null`.

Il limite **è documentato**, e questo rende la trappola più insidiosa, non meno: sotto
*Limitations* il manuale scrive che «Your `mongod` instance needs to be running with the
`--logpath [file]` option in order to use `logRotate`» ([S-043](../Sources.md#s-043)). Dichiara
il prerequisito e non lo fa rispettare. Chi ha letto la pagina sa che serve un `--logpath`; chi
guarda la risposta del server legge `ok: 1` e conclude il contrario.

Il confronto rende la cosa netta ([V-010](../Sources.md#v-010)):

| Destinazione del log | Risposta | Nel log | Effetto sul filesystem |
|---|---|---|---|
| stdout | `{"ok":1}` | `"msg":"Log rotation initiated"`, `"logType":null` | **nessuno** |
| file | `{"ok":1}` | idem | `mongod.log` rinominato, nuovo `mongod.log` creato |

**Rimedio.** Non chiedere a `mongod` una rotazione che non gli compete. In container la rotazione
la fa il driver di log del runtime, e va configurata lì (voce [10](#t-10)). Se si sta scrivendo uno
script di manutenzione, non trattare `ok: 1` come prova che qualcosa sia successo: controllare il
filesystem.

**Fonte.** [S-043](../Sources.md#s-043), [V-010](../Sources.md#v-010), [ADR-0030](../Decision.md#adr-0030), [ADR-0035](../Decision.md#adr-0035).

---

<a id="t-10"></a>
## 10. Il disco si riempie durante la demo

**Sintomo.** Dopo qualche ora di lavoro intenso — o dopo una demo che apre e chiude connessioni a
raffica — lo spazio libero è sparito. Il colpevole è un unico file JSON enorme sotto la directory
del container.

**Causa.** Il driver di log `json-file`, che è quello predefinito, **non ruota niente** se non
glielo si chiede: `max-size` vale `-1 (unlimited)` e `max-file` vale `1`
([S-033](../Sources.md#s-033), misurato in [V-011](../Sources.md#v-011)). In nessun punto della
documentazione c'è una frase che avverta del disco: lo si ricava da un valore predefinito in una
cella di tabella e dal verbo «enable» in una didascalia.

La combinazione con la voce [8](#t-08) è ciò che rende la trappola frequente: si sposta il log su
stdout perché è la cosa giusta da fare, e così facendo si toglie a `mongod` la rotazione senza
darla a nessun altro.

**Rimedio.** Dichiarare i due limiti, che funzionano solo in coppia:

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

Trenta MiB al massimo. Per dare un ordine di grandezza: lo stack 01 **a riposo**, con il solo
healthcheck a lavorare, scrive circa 142 righe al minuto, cioè circa 3 MiB in un'ora di talk
([V-011](../Sources.md#v-011)).

**Fonte.** [V-011](../Sources.md#v-011), [S-033](../Sources.md#s-033),
[ADR-0030](../Decision.md#adr-0030).

---

<a id="t-11"></a>
## 11. Chiunque raggiunga la porta è amministratore

**Sintomo.** Nessun sintomo. È il punto.

**Causa.** Due decisioni indipendenti si sommano. La prima è di chi scrive il file: senza
`--auth` e senza credenziali, `mongod` non chiede niente a nessuno. La seconda non è di nessuno:
l'entrypoint ufficiale aggiunge `--bind_ip_all` alla riga di comando **da solo**, anche se il
file Compose non lo chiede. Misurato: `/proc/1/cmdline` riporta
`mongod --wiredTigerCacheSizeGB 0.25 --bind_ip_all` su uno stack che quell'opzione non l'ha mai
scritta ([V-012](../Sources.md#v-012), [S-034](../Sources.md#s-034)).

Dentro la rete Docker è il comportamento voluto — è così che i container si parlano. L'unica
barriera che resta è quindi la porta pubblicata sull'host, e su una rete condivisa quella
barriera non c'è.

**Rimedio.** Nel lab la scelta è deliberata e dichiarata: lo stack 01 è l'esempio negativo di
[ADR-0005](../Decision.md#adr-0005), e sta scritto in testa al file Compose. Fuori dal lab, i due
interventi minimi sono:

- pubblicare la porta solo sul loopback: `"127.0.0.1:27017:27017"` invece di `"27017:27017"`;
- attivare l'autenticazione — con l'avvertenza della voce [3](#t-03) se il servizio ha `--replSet`.

Il punto da portarsi via: `--bind_ip_all` **non è nel vostro file**, quindi non lo troverete
rileggendolo. Per sapere con cosa sta girando davvero un `mongod` in container si guarda
`/proc/1/cmdline`, non il `compose.yaml`.

**Fonte.** [V-012](../Sources.md#v-012), [S-034](../Sources.md#s-034),
[ADR-0005](../Decision.md#adr-0005).

---

<a id="t-12"></a>
## 12. `mongod` non parte e dice che il keyfile è «too open»

**Sintomo.** Il container esce subito, con codice **1**. Nel log ci sono due righe, e solo la
prima dice qualcosa di utile:

```json
{"s":"I","c":"ACCESS","id":20254,"ctx":"main","msg":"Read security file failed",
 "attr":{"error":{"code":30,"codeName":"InvalidPath",
                  "errmsg":"permissions on /keyfile/mongo-keyfile are too open"}}}
{"s":"F","c":"CONTROL","id":20575,"ctx":"main","msg":"Error creating service context",
 "attr":{"error":"Location5579201: Unable to acquire security key[s]"}}
```

La riga fatale — quella con `"s":"F"` — **non nomina né il file né i permessi**. Chi guarda solo
l'ultima riga, che è quello che si fa quando un container muore, legge «Unable to acquire security
key[s]» e va a cercare un problema di contenuto o di percorso. La riga che spiega è la penultima,
ed è di livello informativo.

**Causa.** MongoDB pretende che il keyfile sia leggibile **solo** dal proprietario, e il
proprietario dev'essere l'utente con cui gira `mongod`. La soglia non è dove la si immagina.
Misurato provando sei permessi diversi su sei container usa-e-getta
([V-041](../Sources.md#v-041)):

| permessi | ottale | esito |
| --- | ---: | --- |
| `-r--------` | `400` | parte |
| `-rw-------` | `600` | parte |
| `-rw-r-----` | `640` | **rifiutato** |
| `-rw-r--r--` | `644` | **rifiutato** |
| `-r--r--r--` | `444` | **rifiutato** |
| `-r-------x` | `401` | **rifiutato** |

L'ultima riga è quella che smentisce l'intuizione: `401` non concede la lettura a nessuno, né al
gruppo né agli altri, eppure viene rifiutato. La regola non è «non dev'essere leggibile da tutti»,
è **«non dev'esserci nessun bit acceso fuori dal proprietario»** — nemmeno un bit di esecuzione che
su un file di testo non significa niente.

Fuori dai permessi c'è la seconda metà della causa, che dà lo stesso messaggio: il file può avere
`400` e appartenere all'utente sbagliato. Nell'immagine ufficiale `mongod` gira come `mongodb`,
uid **999** ([S-023](../Sources.md#s-023)); un keyfile con `400` e proprietario `root` è
irraggiungibile, e il log dice «too open» anche in quel caso.

In Docker la trappola scatta soprattutto con il **bind mount**: un file preso dall'host arriva nel
container con i permessi e gli identificatori numerici che aveva fuori, che su macOS e su Windows
non sono quelli che si sono scritti. Un `chmod 400` dato sull'host può non essere quello che il
container vede.

**Rimedio.** Non montare il keyfile dall'host: **generarlo dentro un volume nominato**, dove i
permessi sono quelli che ci si scrive. È quello che fa questo repository
([ADR-0014](../Decision.md#adr-0014)): un servizio one-shot `keyfile-init` scrive il file nel
volume `keyfile`, e i tre membri lo montano in sola lettura.

```bash
openssl rand -base64 756 > /keyfile/mongo-keyfile
chmod 400 /keyfile/mongo-keyfile
chown 999:999 /keyfile/mongo-keyfile     # l'utente `mongodb` dell'immagine ufficiale
```

Due dettagli che valgono la loro riga. Il `chmod` e il `chown` stanno **fuori** dal ramo che
genera: un volume ripristinato da un backup ha il contenuto giusto e può avere i permessi
sbagliati, e in quel caso il ramo di generazione non passa mai. E la verifica si fa da dentro, con
`ls -ln`, che stampa gli identificatori numerici invece dei nomi — perché il nome `mongodb` esiste
nel container e sull'host quasi certamente no.

La documentazione ufficiale usa `chmod 400` e basta ([S-005](../Sources.md#s-005)); «400 o 600» è
una deduzione, corretta, che questa misura conferma.

**Fonte.** [V-041](../Sources.md#v-041), [S-005](../Sources.md#s-005),
[S-023](../Sources.md#s-023), [ADR-0014](../Decision.md#adr-0014),
[ADR-0049](../Decision.md#adr-0049).

---

<a id="t-13"></a>
## 13. Il driver prova a raggiungere un host che io non ho mai scritto

**Sintomo.** Ci si connette a un replica set dall'host, nominando una porta pubblicata che
risponde, e il driver fallisce nominando **un altro** nodo:

```console
$ mongosh "mongodb://admin:<password>@host.docker.internal:27021/?replicaSet=rs0"
MongoNetworkError: getaddrinfo ENOTFOUND mongo-rs-2
```

`mongo-rs-2` non compare nella stringa. Rieseguendo, il nome cambia: tre tentativi identici hanno
dato `mongo-rs-1`, `mongo-rs-2`, `mongo-rs-1` — e **non è mai** quello che si è scritto
([V-043](../Sources.md#v-043)).

**Causa.** È lo stesso messaggio della voce [5](#t-05) e una trappola diversa, perché lì il nome
che non risolve l'aveva scritto l'utente e qui no. L'indirizzo della stringa serve solo a bussare;
subito dopo il driver chiede al nodo com'è fatto il set, e riceve `hosts` così:

```
["mongo-rs-1:27017", "mongo-rs-2:27017", "mongo-rs-3:27017"]
```

Sono i nomi di servizio Compose, cioè quelli con cui i membri si conoscono **fra loro**. Il driver
li adotta, butta via l'indirizzo con cui era entrato, e da lì in poi tenta su nomi che fuori dalla
rete Docker non esistono. Il nome che compare nell'errore è semplicemente quello su cui è caduto
per primo, e cambia da un tentativo all'altro perché l'ordine non è garantito.

**Rimedio.** Due strade, e vanno scelte sapendo che cosa costano.

*Da fuori: rinunciare al set.* Con `directConnection=true` il driver non fa la scoperta e resta
sull'indirizzo scritto. Funziona, misurato: 50 000 documenti letti da `host.docker.internal:27021`.

```console
$ mongosh "mongodb://admin:<password>@host.docker.internal:27021/?directConnection=true"
… servito da mongo-rs-1:27017
```

Il prezzo è che non è più un client di replica set: niente scoperta del primario, niente failover
automatico. Se quel nodo diventa secondario, le scritture cominciano a fallire con
`NotWritablePrimary` e nessuno le devia. Per un'ispezione va benissimo; per un'applicazione, no.

*Da dentro: entrare nella rete.* Chi gira dentro `sqlstart-02-replicaset_default` risolve quei
nomi, e la connessione al set funziona come da manuale:

```bash
docker run --rm --network sqlstart-02-replicaset_default mongo:7.0.40 \
  mongosh "mongodb://admin:<password>@mongo-rs-1:27017/?replicaSet=rs0" --quiet --eval '…'
```

È la strada giusta per l'applicazione del talk, ed è il motivo per cui il client sta in un
container invece che sull'host.

*C'è una terza strada, e qui non è stata presa:* riconfigurare il set con `rs.reconfig()` perché
pubblichi nomi risolvibili da fuori — `host.docker.internal:27021` e compagni. Funziona e cambia
il set **in modo permanente**, quindi si fa su un lab dedicato, non su uno stack che deve reggere
una demo.

**Quello che invece non funziona, ed è la prima cosa che viene in mente:** elencare tutti e tre gli
indirizzi pubblicati.

```console
$ mongosh "mongodb://…@host.docker.internal:27021,host.docker.internal:27022,host.docker.internal:27023/"
MongoNetworkError: getaddrinfo ENOTFOUND mongo-rs-2
```

Stesso errore, e per una ragione precisa: una seed list con **più di un host** è la terza delle
quattro eccezioni che spengono `directConnection` ([S-045](../Sources.md#s-045)). Più indirizzi
buoni si scrivono, più si convince il driver a scoprire la topologia — e a buttarli via tutti e
tre.

Il modo rapido di riconoscere questa voce fra le tre che danno `ENOTFOUND`: se il nome
nell'errore è uno che **non hai scritto tu**, è questa.

**Fonte.** [V-043](../Sources.md#v-043), [S-045](../Sources.md#s-045),
[ADR-0049](../Decision.md#adr-0049).

---

## Cosa questa pagina non dice

- **Non è un elenco completo.** È l'elenco di ciò che è stato incontrato *e misurato* qui. Le
  due del replica set sono arrivate con `feature/02`; quelle dello sharded cluster — config server,
  bilanciamento — arrivano con `feature/03`.
- **Non copre le trappole di MongoDB fuori da Docker.** Quelle di un'installazione su sistema
  operativo — `ulimit`, transparent huge pages, filesystem — stanno nelle pagine di
  [installazione](../01-installazione/linux.md), con la riserva che le dichiara non eseguite.
- **I numeri valgono per questa macchina.** Docker Engine 29.7.2 su Docker Desktop per macOS,
  `mongo` 7.0.40. I comportamenti sono stabili; i testi dei messaggi lo sono molto meno.
- **Non è una guida alla sicurezza.** La voce 11 dice cosa succede e come chiudere le due falle
  più larghe, non come mettere in sicurezza un'installazione vera.

---

**Decisioni correlate:** [ADR-0033](../Decision.md#adr-0033) (il contratto di questa pagina),
[ADR-0034](../Decision.md#adr-0034) (`docker kill` non è un guasto),
[ADR-0005](../Decision.md#adr-0005), [ADR-0021](../Decision.md#adr-0021),
[ADR-0028](../Decision.md#adr-0028), [ADR-0030](../Decision.md#adr-0030),
[ADR-0031](../Decision.md#adr-0031), [ADR-0014](../Decision.md#adr-0014) (il keyfile nasce in
un volume e non entra nel repository),
[ADR-0049](../Decision.md#adr-0049) (le due voci del replica set).

**Fonti:** [S-020](../Sources.md#s-020), [S-022](../Sources.md#s-022),
[S-032](../Sources.md#s-032), [S-033](../Sources.md#s-033), [S-034](../Sources.md#s-034),
[S-039](../Sources.md#s-039), [S-040](../Sources.md#s-040), [S-041](../Sources.md#s-041),
[V-006](../Sources.md#v-006), [V-007](../Sources.md#v-007), [V-010](../Sources.md#v-010),
[V-011](../Sources.md#v-011), [V-012](../Sources.md#v-012), [V-014](../Sources.md#v-014),
[S-005](../Sources.md#s-005), [S-023](../Sources.md#s-023), [S-045](../Sources.md#s-045),
[V-017](../Sources.md#v-017), [V-018](../Sources.md#v-018), [V-041](../Sources.md#v-041),
[V-043](../Sources.md#v-043)
