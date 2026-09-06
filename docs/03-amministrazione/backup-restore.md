# Backup e restore

Questa pagina esiste in questo branch e non prima per una ragione che non è organizzativa.
`mongodump --oplog` — l'opzione che rende il dump coerente rispetto a un istante — funziona solo
dove c'è un oplog, cioè su un replica set. Su un'istanza singola l'oplog non c'è, quindi il backup
a caldo coerente **non si può fare**: è il paradosso registrato in
[ADR-0022](../Decision.md#adr-0022), rimasto aperto finché non c'è stato uno stack su cui chiuderlo.

Ogni comando che segue è girato sullo stack `docker/02-replicaset` di questo repository. Ogni numero
porta accanto la verifica che lo ha prodotto. La forma della pagina è
[ADR-0047](../Decision.md#adr-0047).

Un avviso in apertura, perché è la cosa che si scopre tardi: **un `mongodump` che fallisce lascia
sul disco qualcosa che assomiglia a un backup.** Tutte le collezioni, gigabyte di BSON, e nessuna
garanzia. L'unico segnale è il codice di uscita.

---

## 1. L'oplog, e la sua finestra

Tutto quello che segue poggia su un pezzo solo: l'**oplog**, il registro delle operazioni che ogni
membro di un replica set tiene per farsi seguire dagli altri. È una collezione a dimensione fissa:
quando è piena, le voci più vecchie escono per far posto alle nuove. La quantità di storia che
contiene in un dato momento è la sua **finestra**, e non è una impostazione — è una conseguenza di
quanto si scrive.

Sullo stack di questo repository, misurata ([V-034](../Sources.md#v-034)):

```text
configuredLogSizeMB : 2032.35
usedMB              :  120.39
timeDiff            : 54339 s   →  15,09 ore
tFirst              : Mon Aug 31 2026 18:43:29 GMT+0000
tLast               : Tue Sep 01 2026 09:49:08 GMT+0000
```

Due gigabyte pieni al 6 %, quindici ore di storia. I 2 032 MB non li ha scelti nessuno: sono il 5 %
dello spazio libero al primo avvio, il valore predefinito dell'immagine.

Il comando per guardarla, da eseguire sul primario:

```javascript
rs.printReplicationInfo()
```

**La riga da leggere non è la dimensione, è `timeDiff`.** Quindici ore su questo stack vogliono dire
che quel giorno si è scritto pochissimo. La stessa configurazione sotto la scrittura di
[V-036](../Sources.md#v-036) — documenti da 100 KB, senza sosta — scende a **minuti**. Una finestra
si guarda sotto il carico vero, e si guarda periodicamente, perché cambia da sola quando cambia il
traffico.

---

## 2. Il dump a caldo, eseguito

Il comando, con l'autenticazione dello stack:

```bash
docker exec mongo-rs-1 mongodump \
  --host "rs0/mongo-rs-1:27017,mongo-rs-2:27017,mongo-rs-3:27017" \
  -u admin -p "${PASSWORD_AMMINISTRATORE}" --authenticationDatabase admin \
  --oplog --out /tmp/dump-02
```

La password non è scritta nel comando: si legge da `docker/02-replicaset/.env`, che sta fuori dal
repository per la stessa regola che tiene fuori il keyfile ([ADR-0014](../Decision.md#adr-0014)).
`mongodump` e `mongorestore` non sono stati installati a parte: sono in `/usr/bin` dentro l'immagine
pinnata, versione 100.18.0 ([V-035](../Sources.md#v-035)).

Il dump è girato **mentre un altro processo scriveva**, un documento alla volta, per trenta secondi.
Questo è il punto dell'esercizio: un backup che richiede di fermare le scritture non è un backup a
caldo.

```text
09:51:48.369  writing lab.movimenti to /tmp/dump-02/lab/movimenti.bson
09:51:48.369  writing lab.ordini    to /tmp/dump-02/lab/ordini.bson
09:51:48.419  dumped 12 oplog entries
```

**Cinquanta millisecondi**, 733 documenti in `lab.movimenti`, 50 000 in `lab.ordini`, e 12 voci di
oplog catturate. Nella cartella, oltre alle collezioni:

```text
/tmp/dump-02/oplog.bson      4 488 byte
/tmp/dump-02/prelude.json       51 byte
/tmp/dump-02/lab/ordini.bson       6 094 260 byte
/tmp/dump-02/lab/movimenti.bson       63 038 byte
/tmp/dump-02/admin/system.version.bson
```

### Il dump è un segreto

`--oplog` **impone** il dump completo: non lo si può combinare con `--db`, `--collection`,
`--dumpDbUsersAndRoles` o `--query` ([S-011](../Sources.md#s-011)). Un dump completo contiene il
database `admin`, e quindi le credenziali. Il restore lo dice a voce alta:

```text
restoring users from `/tmp/dump-02/admin/system.users.bson`
```

Il file di backup vale quanto il database, autenticazione compresa. Va trattato con la stessa cura
che questo repository riserva al keyfile ([ADR-0014](../Decision.md#adr-0014)): mai in un
repository, mai su un disco condiviso senza cifratura.

---

## 3. Quale punto nel tempo

«`--oplog` rende il dump coerente rispetto a un punto nel tempo» è vero e non basta. La domanda che
conta è **quale** punto.

Lo stesso dump è stato ripristinato due volte su una destinazione svuotata, la prima senza
`--oplogReplay` e la seconda con ([V-035](../Sources.md#v-035)):

| | senza `--oplogReplay` | con `--oplogReplay` |
|---|---:|---:|
| documenti ripristinati | 50 733 | 50 733 |
| falliti | 0 | 0 |
| impronta di `lab.ordini` | `50000 124861860.70 150281` | `50000 124861860.70 150281` |
| `lab.movimenti` | **733** | **740** |
| ultimo movimento | `n=733  t=09:51:48.370` | `n=740  t=09:51:48.388` |

La seconda esecuzione dichiara che cosa fa in più:

```text
replaying oplog
applied 12 oplog entries
```

**Sette documenti.** È quanto vale `--oplogReplay` su un dump durato cinquanta millisecondi: poco,
perché il dump è stato breve. Su un dump che dura mezz'ora vale mezz'ora di scritture, ed è la
differenza fra un ripristino coerente e uno che contiene una collezione com'era all'inizio e
un'altra com'era alla fine.

### Il punto cade dentro il comando

Il restore completo si ferma a **740**. Contando sull'orologio del client, alla fine del dump i
documenti erano **741**. La differenza è un documento, e spiega dove sta davvero il punto di
ripristino: **non è l'ultima riga di log del comando, è l'istante dell'ultima voce di oplog
catturata**, che cade dentro l'esecuzione. Quello che viene scritto fra la cattura dell'ultima voce
e il ritorno del comando è nel database e non è nel backup.

Riserva, sulla stessa riga: gli istanti nei documenti li scrive il **client**, non il server. Il
confine 740/741 è approssimato al millisecondo fra due orologi diversi, non dimostrato confrontando
i timestamp dell'oplog.

E per la stessa ragione, la promessa più ottimista della documentazione — «to ensure the data is
current and has all the writes that occurred during the dump operation»
([S-059](../Sources.md#s-059)) — va letta con l'accento su *during*. Non è «adesso»: è la fine del
dump, meno l'ultimo respiro.

---

## 4. Il restore, verificato

Un backup che nessuno ha mai ripristinato non è un backup. La perdita, simulata:

```javascript
db.getSiblingDB("lab").dropDatabase()
```

Il ripristino:

```bash
docker exec mongo-rs-1 mongorestore \
  --host "rs0/mongo-rs-1:27017,mongo-rs-2:27017,mongo-rs-3:27017" \
  -u admin -p "${PASSWORD_AMMINISTRATORE}" --authenticationDatabase admin \
  --oplogReplay /tmp/dump-02
```

E la verifica, che è la parte che si salta:

```javascript
db.getSiblingDB("lab").ordini.aggregate([
  { $group: { _id: null, n: { $sum: 1 }, tot: { $sum: "$importo" }, righe: { $sum: "$righe" } } }
])
```

`50000 124861860.70 150281`, identica a prima della perdita, in entrambe le esecuzioni. È la stessa
impronta che controlla `smoke-02`, e la stessa disciplina: contare i documenti e confrontare una
somma, non guardare se il comando ha stampato qualcosa di verde.

Da notare, perché non è stato dimostrato niente al riguardo: `no indexes to restore for collection
lab.ordini`. Il dataset di demo non ha indici oltre a `_id_`, quindi la ricostruzione degli indici
in fase di restore — che su un database vero è la parte lunga — qui **non si è vista**.

### `--oplogReplay` vuole tutto, e lo dice subito

`--oplogReplay` non convive con le opzioni che restringono l'ambito del restore: `--db`,
`--collection`, `--nsInclude`, `--nsExclude`, `--nsFrom`, `--nsTo`
([S-059](../Sources.md#s-059)). Provato ([V-037](../Sources.md#v-037)):

```text
$ mongorestore --oplogReplay --nsInclude 'lab.*' /tmp/dump-02
Failed: cannot use --oplogReplay with includes specified
0 document(s) restored successfully. 0 document(s) failed to restore.
uscita = 1
```

**Zero documenti toccati.** Il rifiuto arriva prima di scrivere, non a metà strada. La regola è
simmetrica e vale la pena tenerla in una riga sola: dump completo obbligatorio, restore completo
obbligatorio.

---

## 5. Quando fallisce, e che cosa lascia sul disco

La garanzia di `--oplog` regge finché l'oplog conserva le voci prodotte durante il dump. Se il dump
dura più della finestra, le voci di cui il dump ha bisogno sono già uscite, e la coerenza non è più
ricostruibile.

Sullo stack del lab questo guasto non si può mostrare: quindici ore di finestra contro un dump di
cinquanta millisecondi. È stato riprodotto su un'istanza usa-e-getta, con oplog da 1 MB e checkpoint
al secondo ([V-036](../Sources.md#v-036)). Con la finestra scesa a **un secondo** e un dump da
1,5 GB durato **3,4 secondi**:

```text
10:03:43.261  writing `lab.grandi` to /tmp/dump-mini/lab/grandi.bson
10:03:46.673  done dumping `lab.grandi` (15000 documents)
10:03:46.678  Failed: oplog overflow: mongodump was unable to capture all new oplog entries during execution
uscita = 1
```

### Il pezzo che si dimentica

Il comando è fallito **dopo** aver scritto tutte le collezioni:

```text
/tmp/dump-mini/lab/grandi.bson     1 536 555 000 byte
/tmp/dump-mini/lab/disturbo.bson     320 525 373 byte
/tmp/dump-mini/oplog.bson                  assente
/tmp/dump-mini/prelude.json                assente
```

Un dump riuscito ha `oplog.bson` e `prelude.json` in cima alla cartella. Questo ha 1,8 GB di BSON e
nessuno dei due: sul disco resta un oggetto che pesa come un backup, si apre come un backup, e non è
coerente rispetto a nessun istante. **L'unico segnale è il codice di uscita 1.**

Da cui la regola. Sta in quattro righe di script, e la prima è quella che rende lecite le altre:

```bash
DESTINAZIONE="$(mktemp -d)"   # cartella nuova: `rm -rf` è lecito solo su ciò che si è creato
mongodump --oplog --out "${DESTINAZIONE}" || { rm -rf "${DESTINAZIONE}"; exit 1; }
test -f "${DESTINAZIONE}/oplog.bson" || { rm -rf "${DESTINAZIONE}"; exit 1; }
mv "${DESTINAZIONE}" "${ARCHIVIO}/lab-$(date +%F)"   # si pubblica solo dopo il controllo
```

Le due righe di mezzo le ha insegnate il guasto qui sopra. La prima e l'ultima le ha insegnate una
revisione, ed è un errore che vale la pena vedere: `rm -rf` su una destinazione **scelta da chi
chiama** cancella anche ciò che il dump non ha creato. Provato — con una credenziale sbagliata
`mongodump` esce con 1 **prima di scrivere un solo file**, e la regola nella forma a due righe si
portava via il backup del giorno prima che stava nella stessa cartella
([V-095](../Sources.md#v-095)). Una cartella nata da `mktemp -d` non ha il problema per costruzione:
cancellarla ricorsivamente è lecito perché prima non c'era. E finché manca `oplog.bson` il dump non è
un backup, quindi non deve prendere il posto di quello buono: si sposta dopo il controllo, non prima.

### Perché rimpicciolire l'oplog non basta

Il primo tentativo, con `--oplogSize 1` e niente altro, **non ha fallito**: l'oplog è cresciuto fino
a 429 MB con una finestra di 131 secondi, e il dump è passato. Il motivo sta nel log del server:

```text
id 22402  OplogCapMaintainerThread-local.oplog.rs
"WiredTiger record store oplog truncation finished"
pinnedOplogTimestamp: 09:59:44   numRecords: 1835   dataSize: 188 494 870
```

Il taglio dell'oplog è vincolato da un **timestamp bloccato**: il motore di archiviazione non butta
via voci che servirebbero a ripartire dopo un crash, e quel confine è l'ultimo checkpoint. I
checkpoint, per impostazione predefinita, sono ogni sessanta secondi. Ne segue una cosa che vale la
pena sapere prima di provare a ridurre l'oplog per risparmiare spazio: **la finestra non scende
sotto l'intervallo di checkpoint**, per quanto piccolo sia l'oplog. Un oplog da 1 MB con checkpoint
al minuto tiene comunque un minuto di storia — e centinaia di megabyte.

Riserva, dichiarata dove si legge il numero: **la prova è forzata.** Nessuno mette in produzione un
oplog da 1 MB con un checkpoint al secondo. Il caso vero è l'opposto — un oplog normale e un dump
che dura ore. Qui i due termini sono stati compressi per farli stare in tre secondi: il meccanismo e
il messaggio d'errore sono quelli veri, la scala no.

---

<a id="6-sullo-sharded-cluster"></a>
## 6. Sullo sharded cluster: `--oplog` non si può, e il restore non ridistribuisce

Il divieto era già citato in fondo a questa pagina, con la promessa di provarlo. Provato, sullo
stack `03-sharded`, profilo `palco` ([V-065](../Sources.md#v-065)). Tutto quello che segue vale
**attraverso il `mongos`**, che è l'unico indirizzo a cui si parla a un cluster.

**Il divieto, e la sua faccia.** La documentazione dice «You can't run `mongodump` with `--oplog` on
a sharded cluster» ([S-011](../Sources.md#s-011)), e il comando lo conferma senza girarci intorno:

```console
$ mongodump --oplog --out /tmp/dump-03
Failed: can't use --oplog option when dumping from a mongos
```

**Ma l'accusa cambia se si sbaglia anche qualcos'altro,** e cambia in peggio:

```console
$ mongodump --oplog --db lab --out /tmp/dump-03
Failed: bad option: --oplog mode only supported on full dumps
```

È lo stesso comando, sullo stesso cluster, e non nomina più `mongos`. Chi lo legge toglie `--db`,
riprova, e **solo allora** scopre il divieto vero. Le due regole — `--oplog` vuole il dump completo
([§2](#2-il-dump-a-caldo-eseguito)), e `--oplog` non si dà a un router — sono verificate in
quest'ordine, quindi la prima nasconde la seconda.

**Che cosa si fa invece.** Non c'è un'opzione sostitutiva: quello che si perde è la garanzia, non il
comando. Il dump attraverso il router funziona, ed è coerente per singolo documento e per niente
altro:

```console
$ mongodump --db lab --out /tmp/dump-03
Warning: using a non-primary readPreference with a connection to mongos may produce
inconsistent duplicates or miss some documents.
writing lab.ordini to /tmp/dump-03/lab/ordini.bson
done dumping lab.ordini (20000 documents)
```

Due cose su quell'avviso. La prima è che compare **anche passando `--readPreference=primary`**: è
un consiglio su cui non si può agire dalla riga di comando. La seconda è che dice la verità sul
perché `--oplog` è vietato: un dump che attraversa un router legge da più repliche, e non esiste un
oplog solo in cui il «prima» e il «dopo» siano gli stessi per tutti gli shard.

La strada che la documentazione lascia aperta è **fermare il balancer**. «Never run a backup while
the balancer is active», e la verifica non è una sola domanda ma due:
`!sh.getBalancerState() && !sh.isBalancerRunning()` ([S-073](../Sources.md#s-073)). Serve perché una
migrazione in corso durante il dump può far comparire un documento due volte o mai — che è
esattamente ciò di cui l'avviso qui sopra parla. Attenzione all'effetto collaterale: dalla 7.0
`sh.stopBalancer()` spegne anche l'AutoMerger
([`sharded-cluster.md` §4.3](../02-architetture/sharded-cluster.md#43-il-balancer-le-sue-due-mansioni-e-quella-che-qui-non-esercita-mai)).

**Un singolo shard, invece, `--oplog` lo accetta.** Uno shard *è* un replica set, con il suo oplog:

```console
$ mongodump --oplog --out /tmp/dump-shard        # dato direttamente a shard1a
$ ls /tmp/dump-shard
admin  lab  oplog.bson  prelude.json
```

Esce `0`, `oplog.bson` c'è. È un backup coerente **di quello shard**, e tanti backup coerenti presi
uno per uno non fanno un backup coerente del cluster: ciascuno è fermo a un istante diverso, e una
transazione distribuita può stare di qua o di là. La documentazione dei metodi di backup lo dice
con una riga di tabella — sharded cluster: «High, requires extra steps»
([S-060](../Sources.md#s-060)) — e questa pagina non sa quali siano i passi in più.

**Il restore riporta i dati, non la distribuzione.** È la trappola vera, perché non dà nessun
errore. Ripristinando i ventimila documenti in un namespace nuovo, attraverso il router:

```
finished restoring lab.ordini_ripristinata (20000 documents, 0 failures)
index: _id_hashed
```

Ventimila documenti, zero errori, e persino l'**indice hashed** ricreato. Ma:

```
indici:                  _id_,_id_hashed
distribuita:             no
getShardDistribution():  [SHAPI-10001] Collection ordini_ripristinata is not sharded
```

La collezione originale sta 9 860 / 10 140 sui due shard; la ripristinata sta **tutta sul primary
shard** del database `lab`. C'è l'indice che serve a distribuirla e non è distribuita: `mongorestore`
ricrea gli indici e non chiama `shardCollection()`. Chi ripristina un cluster e guarda solo il
conteggio dei documenti trova tutto a posto, e ha appena trasformato uno sharded cluster in un
replica set con un indice inutile.

Il rimedio è dichiarare la distribuzione **prima** del restore — `sh.shardCollection()` sulla
collezione vuota, poi `mongorestore` — che è lo stesso ordine con cui lo stack si costruisce
([`sharded-cluster.md` §3](../02-architetture/sharded-cluster.md)). Questa pagina non l'ha provato:
è dichiarato fra le cose che non copre.

---

## 7. Provarlo in due minuti

Dallo stack già in piedi (`make up-02`), con la password letta da `docker/02-replicaset/.env`:

```bash
# 1. dump a caldo, mentre lo stack lavora, in una cartella che parte vuota
docker exec mongo-rs-1 rm -rf /tmp/dump-02
docker exec mongo-rs-1 mongodump \
  --host "rs0/mongo-rs-1:27017,mongo-rs-2:27017,mongo-rs-3:27017" \
  -u admin -p "${PASSWORD_AMMINISTRATORE}" --authenticationDatabase admin \
  --oplog --out /tmp/dump-02

# 2. la perdita — ma solo se il passo 1 ha prodotto un backup ripristinabile.
#    L'`&&` non è ornamentale: senza, un incolla tira dritto anche su un dump
#    fallito, cancella l'originale e lascia in mano il guasto del §5.
docker exec mongo-rs-1 test -f /tmp/dump-02/oplog.bson \
  && docker exec mongo-rs-1 mongosh --quiet --host rs0/localhost:27017 \
       -u admin -p "${PASSWORD_AMMINISTRATORE}" --authenticationDatabase admin \
       --eval 'db.getSiblingDB("lab").dropDatabase()'

# 3. il ripristino
docker exec mongo-rs-1 mongorestore \
  --host "rs0/mongo-rs-1:27017,mongo-rs-2:27017,mongo-rs-3:27017" \
  -u admin -p "${PASSWORD_AMMINISTRATORE}" --authenticationDatabase admin \
  --oplogReplay /tmp/dump-02

# 4. la verifica, che è il passo che conta
make smoke-02
```

Sui `-p "${PASSWORD_AMMINISTRATORE}"` di questi comandi: qui la password **si legge davvero** nella
tabella dei processi del container, perché `mongodump` e `mongorestore` non riscrivono il proprio
`argv` — misurato su tutti e due ([V-096](../Sources.md#v-096),
[M-025](../../app/docs/Sources.md#m-025)). `mongosh` invece lo riscrive e mostra `<credentials>`
([V-047](../Sources.md#v-047)): la stessa precauzione serve o non serve a seconda dello strumento, e
il modo di saperlo è provarlo. Su tutti e tre la password resta in chiaro **sull'host**, nell'`argv`
del client `docker`. Il [§8](#8-le-stesse-due-cose-come-scena-demo-backup-live-e-demo-restore) mostra
come fa l'applicazione, che `-p` non lo passa affatto.

Il passo 2 è l'unico con una guardia perché è l'unico irreversibile. Qui non costa niente —
`make reset-demo-02` rimette tutto — ma questa pagina la si copia altrove, e altrove il passo 2 senza
guardia è il modo in cui si perde un database avendo in mano una cartella che sembra un backup.
Misurato: dopo un `mongodump` fallito, `test -f /tmp/dump-02/oplog.bson` esce con 1
([V-095](../Sources.md#v-095)).

A fine prova, `make reset-demo-02` riporta lo stack allo stato di partenza e
`docker exec mongo-rs-1 rm -rf /tmp/dump-02` toglie il dump da dentro il container.

---

## 8. Le stesse due cose, come scena: `demo backup-live` e `demo restore`

Le sette sezioni sopra sono `feature/02`: comandi dati a mano, uno alla volta, per scoprire che cosa
succede. Questa sezione è `feature/04`, ed è l'altra metà — gli stessi due strumenti dentro
l'applicazione `mongolab`, perché in sala non c'è il tempo di incollare quattro righe e leggerne
quattro di risposta.

```bash
uv run --directory app mongolab demo backup-live --target rs
uv run --directory app mongolab demo restore --target rs --collection carico-…
```

La seconda riga non si scrive: la stampa la prima, già completa, nome della collezione compreso.

Tutte e due hanno un bersaglio — `make app-backup TARGET=rs` e `make app-restore TARGET=rs`
([ADR-0120](../Decision.md#adr-0120)) — e qui restano per esteso apposta: è la forma che la prima
riga stampa e che si incolla, e i due bersagli girano comunque solo dall'host.

### Che cosa mostra, e in che ordine

`demo backup-live` fa girare un carico di scrittura, ne misura il ritmo, poi lancia
`mongodump --readPreference=secondary --oplog` **senza fermare il carico** e misura il ritmo una
seconda volta, nella finestra esatta in cui il dump gira. Alla fine mette i due numeri sulla stessa
riga:

```text
ritmo       prima 595/s · durante 692/s · calo -16.2%
dump        /tmp/mongolab-backup · 3908 documenti in collezione
            dumped 72 oplog entries
carico      3629 scritture · 3629 confermate · p95 66.3 ms
sotto dump  279 scritture · 279 confermate · p95 68.7 ms
```

Il calo è una percentuale **con segno**, non un giudizio: qui è negativo, cioè il ritmo è salito, e
la ragione è che la finestra del dump è mezzo secondo — su mezzo secondo il rumore pesa più del
costo del dump. I numeri da leggere sono quelli assoluti che le stanno accanto: 279 scritture
durante il dump, tutte confermate, con un p95 di 68,7 ms contro i 66,3 di prima
([M-047](../../app/docs/Sources.md#m-047)). **Il servizio non si è fermato**, ed è la sola cosa che
questa metà della scena deve dimostrare.

`demo restore` rimette la copia **accanto** all'originale, in `lab_ripristinato`, e conta:

```text
restore     3908 all'origine · 3802 nella copia · differenza 106
            /tmp/mongolab-backup → lab_ripristinato
            106 scritti mentre il dump era in corso: stanno nell'oplog, che il
            restore non riapplica
```

Accanto e mai sopra, e il comando rifiuta `--into lab` dicendolo: i documenti che alla copia mancano
sono ancora nell'originale, quindi restaurarci sopra li lascerebbe dove sono, i conteggi
combacerebbero, e la differenza sparirebbe **proprio perché** il restore è riuscito. Quei 106 sono
la [§4](#4-il-restore-verificato) vista da un'altra angolazione: stanno nell'oplog che il dump ha
portato via — `dumped 72 oplog entries` — ma `--oplogReplay` non convive con la rinomina dei
namespace che serve a restaurare altrove. La §4 lo ha misurato nella forma con gli inclusi
(`cannot use --oplogReplay with includes specified`, [V-037](../Sources.md#v-037)); l'applicazione
lo ha incontrato in quella con le rinomine — `cannot use --oplogReplay with namespace renames
specified`, uscita 1 ([M-024](../../app/docs/Sources.md#m-024)) — e le due forme sono la stessa
regola ([S-059](../Sources.md#s-059)). Il prezzo di non aver fermato il servizio si legge lì, ed è
un numero, non un errore.

### La riga di comando è diversa da quella della [§7](#7-provarlo-in-due-minuti), e non per caso

Messi accanto, i due blocchi mostrano una differenza che vale il paragrafo. La §7 scrive
`-p "${PASSWORD_AMMINISTRATORE}"`; l'applicazione **non lo fa**, e la riga che stampa in scena è
questa:

```text
docker compose --env-file tools/images.env --env-file docker/02-replicaset/.env \
  -f docker/02-replicaset/compose.yaml exec -T mongo-rs-1 \
  mongodump --host rs0/mongo-rs-1:27017,mongo-rs-2:27017,mongo-rs-3:27017 \
  --out /tmp/mongolab-backup --username admin --authenticationDatabase admin \
  --readPreference=secondary --oplog
```

Nessuna password, e la riga si può proiettare. Il segreto entra dallo `stdin` del processo, perché
con `-p <valore>` in `argv` un `ps -eo args` dentro il container lo mostra a chiunque
([M-025](../../app/docs/Sources.md#m-025), [ADR-0054](../Decision.md#adr-0054)). Il comando lo sanno
costruire tutti e due; solo uno dei due si può registrare con asciinema.

L'altra differenza è `docker compose exec` al posto di `docker exec`: nomina il **servizio** invece
del container e porta con sé i due `--env-file` senza i quali lo stack non si compone
([M-040](../../app/docs/Sources.md#m-040)).

### Dove gira, e perché non dove gira il failover

Le due scene si lanciano **dall'host**, e da dentro la rete Compose si rifiutano. È l'inverso della
scena del failover, che la rete la pretende perché le serve la scoperta della topologia. La ragione
è misurata: `mongodump` non sta nell'immagine dell'applicazione — copiarcelo produce un container
che si ferma su `libgssapi_krb5.so.2` ([M-044](../../app/docs/Sources.md#m-044)) — e per andarlo a
prendere dentro un nodo serve il socket del demone Docker, che il container dell'applicazione non
ha. Il ragionamento per intero sta in [ADR-0100](../Decision.md#adr-0100).

Ne segue una cosa da sapere per la scaletta: dall'host si scrive solo sul nodo pubblicato, e dopo la
scena del failover quel nodo ci mette **quattro secondi** a riprendersi il primato
([M-048](../../app/docs/Sources.md#m-048)). Finché non l'ha fatto, `demo backup-live` si rifiuta di
partire invece di lanciare un carico che fallirebbe alla prima scrittura.

---

## Cosa questa pagina non copre

**`mongodump` non è lo strumento per un database grande, e non lo dice questa pagina: lo dice
MongoDB.** La pagina dei metodi di backup apre così: «`mongodump` and `mongorestore` are tools for
backing up and restoring **small** MongoDB deployments» ([S-060](../Sources.md#s-060)). La stessa
pagina mette la coppia in tabella con RTO **High**, RPO **High**, ripristino continuo a un punto nel
tempo **No**, coerenza **Not guaranteed**, backup di uno sharded cluster «High, requires extra
steps».

Due precisazioni sulla tabella, perché citarla senza sarebbe scorretto. La prima: «small» non è
quantificato da nessuna parte, quindi chi deve decidere se il proprio database è piccolo non trova
lì il numero per farlo. La seconda: la riga «impact on source: **High, requires write lock**» **non
corrisponde a ciò che si è osservato qui** — durante i cinquanta millisecondi del dump le scritture
sono proseguite, e i documenti scritti in quella finestra sono nel database
([V-035](../Sources.md#v-035)). La dichiarazione dell'editore resta citata; l'osservazione resta
accanto.

Non è stato provato, e la pagina non ne parla:

- **`--oplogLimit`**, che ferma la riproduzione dell'oplog a un timestamp scelto a mano. La
  documentazione lo accompagna con un avviso esplicito — «might cause corruption and inconsistencies
  in the restored data» ([S-059](../Sources.md#s-059)) — e provarlo bene richiede un caso d'uso che
  qui non c'è.
- **Il restore su uno stack diverso da quello di origine**, che è il caso vero di un ripristino. Qui
  sorgente e destinazione sono lo stesso processo, quindi il vincolo di versione dichiarato da
  [S-059](../Sources.md#s-059) — «the same major version or feature compatibility version» — non è
  stato messo alla prova.
- **Il restore parziale senza `--oplogReplay`**, che è il caso simmetrico di
  [V-037](../Sources.md#v-037) e il più insidioso: non dà nessun errore, e produce un ripristino
  incoerente in silenzio.
- **La ricostruzione degli indici**, perché il dataset di demo non ne ha.
- **Portare il dump fuori dal container** e conservarlo. Qui il dump vive in `/tmp` dentro
  `mongo-rs-1` e viene cancellato a fine prova: dove vada in una installazione vera, con quale
  rotazione e con quale cifratura, è una decisione che questo repository non prende.
- **Il restore preceduto da `shardCollection()`**, che è il rimedio alla trappola della
  [§6](#6-sullo-sharded-cluster): dichiarare la distribuzione sulla collezione vuota e poi
  ripristinare. Il ragionamento c'è, la misura no.
- **I «extra steps» del backup di uno sharded cluster**, che [S-060](../Sources.md#s-060) nomina in
  una casella di tabella e non elenca da nessuna parte. Questa pagina ha provato che cosa **non**
  funziona; che cosa faccia un backup coerente di un cluster intero resta fuori.
- **Il backup dei config server**, che contengono la mappa dei chunk. Il dump attraverso il router
  porta via anche `config`, ma che quella copia basti a ricostruire un cluster non è stato provato,
  e nessuna fonte letta lo afferma.

**Un punto in meno, chiuso da `feature/04`.** In questo elenco c'era anche
**`--readPreference=secondary`** ([S-011](../Sources.md#s-011)), con la nota «è probabilmente la
prima cosa da fare in produzione, e non è stata misurata». Adesso è misurato, e fa quello che dice.
Contando `serverStatus().opcounters.query` sui tre membri prima e dopo lo stesso dump: senza
l'opzione il primario prende **+15** letture e i due secondari +1 e +0; con l'opzione il primario ne
prende **+0**, e le quindici si spostano sui secondari, +7 e +8
([M-046](../../app/docs/Sources.md#m-046)). È l'opzione con cui la
[§8](#8-le-stesse-due-cose-come-scena-demo-backup-live-e-demo-restore) gira, ed è la ragione per cui
il carico sul primario non si accorge del dump.

---

**Decisioni correlate:** [ADR-0047](../Decision.md#adr-0047) (la forma di questa pagina),
[ADR-0022](../Decision.md#adr-0022) (il paradosso che questa pagina chiude),
[ADR-0014](../Decision.md#adr-0014) (i segreti fuori dal repository),
[ADR-0043](../Decision.md#adr-0043) (il dataset di demo e la sua impronta),
[ADR-0046](../Decision.md#adr-0046) (il replica set su cui tutto questo gira),
[ADR-0070](../Decision.md#adr-0070) (i debiti dello sharded, saldati eseguendo),
[ADR-0054](../Decision.md#adr-0054) (la password non passa da `argv`),
[ADR-0100](../Decision.md#adr-0100) (gli strumenti restano nei nodi, la scena si gira dall'host),
[ADR-0101](../Decision.md#adr-0101) (la finestra della seconda misura è quella del dump),
[ADR-0102](../Decision.md#adr-0102) (il restore scrive accanto all'originale, mai sopra).

**Fonti:** [S-011](../Sources.md#s-011), [S-059](../Sources.md#s-059),
[S-060](../Sources.md#s-060), [S-073](../Sources.md#s-073), [V-034](../Sources.md#v-034),
[V-035](../Sources.md#v-035), [V-036](../Sources.md#v-036), [V-037](../Sources.md#v-037),
[V-065](../Sources.md#v-065), [M-024](../../app/docs/Sources.md#m-024),
[M-025](../../app/docs/Sources.md#m-025),
[M-040](../../app/docs/Sources.md#m-040), [M-044](../../app/docs/Sources.md#m-044),
[M-045](../../app/docs/Sources.md#m-045), [M-046](../../app/docs/Sources.md#m-046),
[M-047](../../app/docs/Sources.md#m-047), [M-048](../../app/docs/Sources.md#m-048)
