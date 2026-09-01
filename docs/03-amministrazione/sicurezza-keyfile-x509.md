# Autenticazione interna: keyfile e X.509

Tre `mongod` sulla stessa rete non sono un replica set: sono tre processi che si scambiano dati
perché nessuno glielo impedisce. L'autenticazione interna è ciò che li rende un insieme chiuso —
ogni membro dimostra agli altri di essere un membro, e chi non lo dimostra viene ignorato. MongoDB
la fa in due modi: un **keyfile**, cioè un segreto condiviso, oppure dei **certificati X.509**.

Questo repository usa il keyfile. La stessa pagina di documentazione che spiega come farlo dice, in
un riquadro, di non usarlo in produzione. Le due cose non sono in contraddizione, ma una pagina che
riportasse solo la prima insegnerebbe male: qui ci sono tutte e due, con la citazione per intero e
il preventivo dell'alternativa accanto.

Un avviso in apertura, perché è la cosa che sorprende chi legge il file Compose: **nel comando dei
tre membri l'opzione `--auth` non compare**, e ciononostante ogni comando pretende credenziali.
L'autenticazione interna se le porta dietro, in tutti e due i modi.

La forma di questa pagina è [ADR-0048](../Decision.md#adr-0048). Quello che è stato eseguito è
eseguito sullo stack `docker/02-replicaset` o su istanze usa-e-getta con la stessa immagine
pinnata, e porta accanto la verifica che lo ha prodotto; quello che non è stato eseguito è
**marcato come non eseguito**, secondo la regola di [ADR-0035](../Decision.md#adr-0035) e
[ADR-0036](../Decision.md#adr-0036).

---

## 1. Che cosa fa il keyfile, e che cosa si porta dietro

Un keyfile è un file di testo con dentro una stringa. Tutti i membri ne hanno una copia identica, e
la usano per autenticarsi a vicenda. La documentazione fissa tre requisiti
([S-005](../Sources.md#s-005)):

> «A key's length must be between 6 and 1024 characters and may only contain characters in the
> base64 set. All members of the replica set must share at least one common key.»

> «On UNIX systems, the keyfile must not have group or world permissions. On Windows systems,
> keyfile permissions are not checked.»

> «Ensure that the user running the `mongod` instances is the owner of the file and can access the
> keyfile.»

La ricetta ufficiale è una riga:

```bash
openssl rand -base64 756 > <path-to-keyfile>
```

Nel lab la esegue un servizio one-shot, `keyfile-init`, che scrive dentro un volume nominato e non
in un bind mount — la ragione è in [ADR-0014](../Decision.md#adr-0014): i permessi dei file montati
da macOS non si governano con `chmod`, e il keyfile **non deve entrare nel repository** in nessun
caso. Dentro il container il risultato è questo ([V-038](../Sources.md#v-038)):

```text
/keyfile/mongo-keyfile   400   mongodb:mongodb   1024 byte
                         16 righe, 1008 caratteri base64 senza gli a capo
processo mongod:         uid=999(mongodb) gid=999(mongodb)
```

Vale la pena fermarsi su quel `1024`, perché è esattamente il massimo dichiarato dalla fonte per la
lunghezza di una chiave. Tolti i sedici a capo che `openssl` inserisce ogni 64 caratteri, i
caratteri base64 sono 1008. **Quale dei due numeri MongoDB confronti con il limite non è scritto da
nessuna parte**, e questa misura non lo distingue: la ricetta ufficiale produce un file che va bene
con entrambe le letture, il che è probabilmente il motivo per cui è quella ricetta.

Una precisazione onesta sui permessi: l'esempio ufficiale usa **solo** `chmod 400`. Dire «400 o 600»
è una deduzione corretta, non una citazione — e la frase «altrimenti `mongod` rifiuta di avviarsi»
**non è scritta** nella fonte, che pone il requisito senza descrivere che cosa succeda a violarlo.
Che cosa succeda davvero lo si vede in
[`../02-architetture/trappole-mongodb-in-docker.md`](../02-architetture/trappole-mongodb-in-docker.md),
dove il messaggio è riportato per intero.

### `--keyFile` porta con sé il controllo degli accessi

Questo è il punto controintuitivo, ed è meglio scoprirlo qui che davanti a un pubblico. Il comando
dei tre membri è questo, per intero:

```text
["mongod","--replSet","rs0","--keyFile","/keyfile/mongo-keyfile",
 "--bind_ip_all","--wiredTigerCacheSizeGB","0.25"]
```

`--auth` non c'è. Eppure, aprendo una sessione **senza credenziali** dentro `mongo-rs-1`, sullo
stesso loopback a cui l'eccezione localhost si applicherebbe ([V-038](../Sources.md#v-038)):

```text
hello()                            -> OK: setName=rs0 primary=mongo-rs-1:27017
admin.system.users.countDocuments  -> Unauthorized: Command aggregate requires authentication
replSetGetStatus                   -> Unauthorized: Command replSetGetStatus requires authentication
lab.ordini.countDocuments          -> Unauthorized: Command aggregate requires authentication
createUser                         -> Unauthorized: Command createUser requires authentication
```

Una cosa sola passa: `hello()`. È il comando con cui un driver scopre la topologia, e resta aperto
perché altrimenti nessun client saprebbe nemmeno a chi chiedere di autenticarsi.

Le due fonti lo dichiarano, ciascuna a modo suo: «`--keyFile` implies `--auth`»
([S-002](../Sources.md#s-002)) e, più esplicitamente, l'esecuzione con `--keyFile` «enforces both
Self-Managed Internal/Membership Authentication and Role-Based Access Control»
([S-005](../Sources.md#s-005)). Per X.509 la frase è la stessa: «Enabling internal authentication
also enables Role-Based Access Control in Self-Managed Deployments. Clients must authenticate as a
user in order to connect and perform operations in the deployment»
([S-061](../Sources.md#s-061)).

Da qui discende un problema che sembra un paradosso: prima che un utente esista nessuno può
inizializzare la replica, e senza replica inizializzata non si può creare un utente. Se ne esce con
l'**eccezione localhost**, che concede molto meno di quanto il nome suggerisca — nella prova sopra,
su un nodo con un utente già creato, perfino `createUser` risponde `Unauthorized`. Come il lab ne
esca in pratica è scritto in [ADR-0040](../Decision.md#adr-0040), e non si ripete qui.

---

## 2. Perché MongoDB lo riserva a test e sviluppo

La frase è questa, per intero ([S-005](../Sources.md#s-005)):

> «Use keyfiles only for testing and development environments because of their limited
> manageability and cryptographic strength. For production environments, use X.509 certificates.»

Va letta per quello che dice, che non è «il keyfile è rotto». Dice due cose distinte. La prima è
sulla **forza crittografica**: un segreto condiviso, per quanto lungo, resta un segreto condiviso —
chi lo ottiene diventa un membro. La seconda, e in pratica la più pesante, è sulla
**gestibilità**: una chiave sola per tutti i membri significa che l'unità minima di rotazione è
l'intero cluster, e che il file va distribuito, protetto e sostituito ovunque insieme.

X.509 risolve entrambe, e presenta il conto. Il conto è la parte che le pagine introduttive
saltano, quindi eccolo con i numeri della documentazione:

- **Una CA sola.** «A single Certificate Authority (CA) must issue all X.509 certificates for the
  members of a sharded cluster or a replica set» ([S-061](../Sources.md#s-061)). Va gestita, e va
  gestita per anni.
- **Un certificato per membro**, con vincoli precisi sul soggetto: valore non vuoto per almeno uno
  fra `O`, `OU`, `DC`, e «MongoDB verifies that entries match exactly across all member
  certificates».
- **Ogni host va nominato.** «At least one of the Subject Alternative Name (`SAN`) entries must
  match the server hostname used by other cluster members.» Aggiungere un membro significa emettere
  un certificato.
- **Una rotazione in sei passi e tre giri di riavvii** ([S-063](../Sources.md#s-063)), descritta
  al §3.5.
- **TLS obbligatorio**, con tutto ciò che comporta per i client: §3.4.

Per un lab che deve partire offline sul portatile di chi presenta, questo è il costo sbagliato. Il
keyfile qui non è una scorciatoia: è la scelta giusta, e la riserva della fonte descrive un
ambiente diverso da questo. La gradazione fra i tre stack del repository è decisa in
[ADR-0005](../Decision.md#adr-0005).

---

## 3. Come si passa a X.509

Quello che segue è in parte eseguito e in parte no, e la differenza è marcata riga per riga.

### 3.1 Che cosa cambia nei parametri del server

| | keyfile | X.509 |
|---|---|---|
| autenticazione interna | `--keyFile <percorso>` | `--clusterAuthMode x509` |
| TLS | non richiesto | **obbligatorio** — `--tlsMode requireTLS` |
| identità del membro | il file condiviso | `--tlsClusterFile <pem>` |
| identità verso i client | nessuna | `--tlsCertificateKeyFile <pem>` |
| verifica dei pari | la chiave coincide | `--tlsCAFile <pem>`, e i `DN` coincidono |
| controllo accessi client | attivato di conseguenza | attivato di conseguenza |

La riga d'avvio completa, dalla fonte ([S-061](../Sources.md#s-061)):

```bash
mongod --replSet <name> --tlsMode requireTLS --clusterAuthMode x509 \
       --tlsClusterFile <path to membership certificate and key PEM file> \
       --tlsCertificateKeyFile <path to TLS/SSL certificate and key file> \
       --tlsCAFile <path to root CA file> \
       --bind_ip localhost,<hostname(s)|ip address(es)>
```

Con un obbligo esplicito: «To use X.509 authentication, `--tlsCAFile` or `net.tls.CAFile` must be
specified unless you are using `--tlsCertificateSelector`». E una regola sull'uniformità: «Outside
of rolling upgrade procedures, every component of a replica set or sharded cluster should use the
same `--clusterAuthMode` setting».

Nota terminologica, per chi incontra esempi vecchi: le opzioni `ssl` sono deprecate ma **non
diverse**. «The `tls` settings/options provide *identical* functionality as the `ssl` options since
MongoDB has always supported TLS 1.0 and later» ([S-061](../Sources.md#s-061)).

### 3.2 Che cosa devono contenere i certificati

Oltre al soggetto e al `SAN` già visti, la fonte pone vincoli sugli usi estesi della chiave:
`tlsCertificateKeyFile` deve includere `serverAuth`, `tlsClusterFile` deve includere `clientAuth`, e
se il secondo è omesso il primo deve includerli entrambi. Con una scappatoia dichiarata: «If
`tlsCertificateKeyFile` or `tlsClusterFile` point to certificates that omit these extensions, no
restrictions apply».

Due avvertenze che valgono anche per chi non arriverà mai a X.509. «MongoDB disables support for TLS
1.0 encryption on systems where TLS 1.1+ is available.» E, sull'opzione che tutti provano quando i
certificati non funzionano: «If you specify `--tlsAllowInvalidCertificates` … an invalid certificate
is sufficient only to establish a TLS connection but it is *insufficient* for authentication» — cioè
disattivarla non fa passare l'autenticazione interna, la fa fallire più tardi.

La fonte dichiara il proprio limite, e questa pagina lo eredita:

> «A full description of TLS/SSL, PKI (Public Key Infrastructure) certificates, in particular X.509
> certificates, and Certificate Authority is beyond the scope of this document. This tutorial
> assumes prior knowledge of TLS/SSL as well as access to valid X.509 certificates.»

Come si producono quei certificati, quindi, **non è materia di questa pagina** né di questo
repository.

### 3.3 La sequenza, eseguita

La migrazione è una procedura **a caldo** ([S-062](../Sources.md#s-062)): si cambia un nodo alla
volta, e nel mezzo il cluster resta misto — alcuni membri mandano il keyfile, altri il certificato,
e tutti accettano entrambi. I modi di `clusterAuthMode` sono quattro, e i due centrali esistono solo
per questo:

| modo | manda | accetta |
|---|---|---|
| `keyFile` | keyfile | keyfile |
| `sendKeyFile` | keyfile | keyfile **o** X.509 |
| `sendX509` | X.509 | keyfile **o** X.509 |
| `x509` | X.509 | X.509 |

**Prima cosa da sapere, e non è nella documentazione.** Il modo di transizione non è gratis:
`mongod --clusterAuthMode sendKeyFile` **non parte** se il TLS non è configurato. Quattro avvii, con
l'immagine pinnata, tutti con uscita `1` ([V-039](../Sources.md#v-039)):

```text
--clusterAuthMode x509         BadValue: need to enable TLS via the tlsMode flag
--clusterAuthMode sendX509     BadValue: need to enable TLS via the tlsMode flag
--clusterAuthMode sendKeyFile  BadValue: need to enable TLS via the tlsMode flag
--clusterAuthMode keyFile      Location5579201: Unable to acquire security key[s]
```

Detto altrimenti: **la migrazione verso X.509 non comincia da X.509, comincia da TLS.** Il primo
riavvio di ogni nodo introduce i certificati e `allowTLS`; X.509 arriva dopo. È la cosa che cambia
la stima dei tempi, perché il TLS tocca i client (§3.4) e i client non sono governati da chi
amministra il database.

La procedura per un cluster che usa il keyfile e **non** usa TLS — il caso di questo stack — ha
quattro passi ([S-062](../Sources.md#s-062)). Il primo è un riavvio per nodo, con
`net.tls.mode: allowTLS`, `net.tls.certificateKeyFile`, `net.tls.clusterFile`, `net.tls.CAFile` e
`security.clusterAuthMode: sendKeyFile`. Il keyfile **resta al suo posto**. Il secondo e il terzo
sono `setParameter`, a caldo, su ogni nodo. Il quarto è riscrivere il file di configurazione perché
il nuovo stato sopravviva al prossimo riavvio.

Eseguita su un'istanza usa-e-getta configurata come prescrive il primo passo, la sequenza è questa
([V-039](../Sources.md#v-039)):

```text
partenza: [sendKeyFile / allowTLS]
  tlsMode=preferTLS            [sendKeyFile / allowTLS]   ->  accettato
  clusterAuthMode=sendX509     [sendKeyFile / preferTLS]  ->  accettato
  tlsMode=requireTLS           [sendX509 / preferTLS]     ->  accettato
  clusterAuthMode=x509         [sendX509 / requireTLS]    ->  accettato
arrivo:   [x509 / requireTLS]     il nodo scrive: true     stato: PRIMARY
```

Nessun riavvio fra una riga e l'altra, e il nodo è rimasto primario e scrivibile per tutta la
sequenza.

**Seconda cosa che la documentazione non scrive: l'ordine non è indifferente.** Nello stesso passo,
la fonte presenta i due `setParameter` uno sotto l'altro senza dire che il primo abiliti il secondo.
Invertendoli:

```text
clusterAuthMode=x509      [sendKeyFile / allowTLS] -> BadValue: Illegal state transition for
                                                      clusterAuthMode, need to enable SSL for
                                                      outgoing connections
```

Il vincolo è sulle connessioni **uscenti**: con `allowTLS` il nodo accetta TLS ma non lo usa per
chiamare gli altri, e mandare un certificato su un canale in chiaro non ha senso. `preferTLS` è il
primo modo in cui le uscenti sono cifrate, ed è per questo che viene prima.

**Terza cosa: la scala è a senso unico.** Su entrambi i parametri:

```text
clusterAuthMode  x509 -> sendX509   Location5579202: Illegal state transition
                                    for clusterAuthMode from 'x509' to 'sendX509'
clusterAuthMode  x509 -> keyFile    Location5579202: (idem)
tlsMode  requireTLS -> preferTLS    BadValue: Illegal state transition for tlsMode
```

Chi sbaglia tappa non annulla il comando: riavvia il nodo con la configurazione di prima. E il
ritorno al keyfile, dopo, non è un ripensamento — è una rimessa in piedi.

> **Non eseguito.** La sequenza è girata su un replica set di **un solo membro**, dove
> l'autenticazione interna non ha nessuno con cui parlare. Quello che non è stato provato è proprio
> ciò che rende la procedura un *rolling upgrade*: un cluster misto in cui un nodo a `sendX509` e
> uno a `sendKeyFile` continuano a riconoscersi. Il certificato usato è autofirmato e privo di
> estensioni di uso della chiave, quindi i requisiti `serverAuth`/`clientAuth` e la regola dell'unica
> CA non sono stati messi alla prova. Le riserve per intero sono in
> [V-039](../Sources.md#v-039).

### 3.4 Che cosa succede ai client

Il quarto passo della procedura porta un avviso in grassetto, ed è il più costoso della pagina
([S-062](../Sources.md#s-062)):

> «This TLS/SSL connection requirement applies to all connections; that is, with the clients as well
> as with the members of the cluster.»

Tradotto: passare a `requireTLS` non è una modifica al database, è una modifica a tutto ciò che si
collega al database. Tre modi di sbagliare, misurati su un'istanza con `requireTLS` e un certificato
con `subjectAltName = DNS:x509-san, DNS:localhost` ([V-040](../Sources.md#v-040)):

```text
127.0.0.1  tls=true   -> Hostname/IP does not match certificate's altnames:
                         IP: 127.0.0.1 is not in the cert's list:      (rifiuto del CLIENT)
localhost  senza tls  -> connessione chiusa; lato server SSLHandshakeFailed
                         «The server is configured to only allow SSL connections»
x509-san   tls=true   -> connessione chiusa; lato server id 23255
                         «No SSL certificate provided by peer; connection rejected»
```

Nessuno dei tre è il server che va male. Il primo è il **client** che verifica il nome: il
certificato elenca `DNS:localhost` e nessun indirizzo, quindi connettersi per IP non passa — è la
regola del `SAN` del §3.2, vista dal lato di chi si collega. Il secondo è un client in chiaro contro
un server che non parla più in chiaro. Il terzo è il server che, avendo un `--tlsCAFile`, pretende
un certificato **anche dal client**.

> **Non eseguito.** Nessun certificato client è stato generato: sopra ci sono i tre modi di
> sbagliare, non il caso che funziona. L'autenticazione **dei client** via X.509 — cosa diversa
> dall'autenticazione interna fra membri — non è trattata.

### 3.5 La rotazione, che è il costo vero

Un certificato scade. Quando arriva il momento di sostituirlo con uno che ha un `DN` diverso, i nodi
smettono di riconoscersi, perché il riconoscimento è proprio un confronto fra `DN`
([S-063](../Sources.md#s-063)):

> «When a server node receives a connection request, it compares the Distinguished Name (DN)
> attributes in the `subject` field of the presented certificates to the subject DN attributes of
> its own certificates. The certificates match if their subjects contain the same values for the
> Organization (`O`), Organizational Unit (`OU`), and Domain Component (`DC`) attributes.»

La via d'uscita è un parametro-ponte, `tlsX509ClusterAuthDNOverride`, che fa accettare a un nodo
anche i pari con l'altro `DN`. La procedura completa è di **sei passi** e comporta **tre giri di
riavvii** dell'intero cluster: si mette l'override sul `DN` nuovo ovunque e si riavvia; si
sostituiscono i certificati mettendo l'override sul `DN` **vecchio** e si riavvia; si toglie
l'override e si riavvia una terza volta. Ogni passo ripete lo stesso avviso — «This configuration
will not be taken into consideration until you restart each member» — e ogni giro è un rolling
restart fatto come si deve: `db.shutdownServer()` su ogni secondario, attesa che torni `SECONDARY`
verificata con `rs.status()`, e `rs.stepDown()` sul primario prima di fermarlo.

Sul fermo macchina la fonte è netta: «In a rolling update, member certificates are updated one at a
time, and your deployment does not incur any downtime.»

Questa procedura è il termine di paragone onesto con il keyfile, ed è la ragione per cui il §2 parla
di gestibilità prima che di crittografia. Tre giri di riavvii, da programmare prima della scadenza,
per ogni cluster, per sempre.

> **Non eseguito.** La rotazione è riportata dalla fonte e non è stata provata. Da segnalare anche
> un silenzio della fonte: la pagina non dice niente su **come accorgersi** che i certificati stanno
> per scadere, né su che cosa succeda a un cluster i cui certificati scadono mentre è in esercizio.
> La presenta come una scelta organizzativa — «such as if an organization changes its name» — non
> come una manutenzione periodica obbligata, che è invece quello che è.

---

## 4. Utenti del cluster e utenti locali a un nodo

Questa sezione esiste perché [ADR-0026](../Decision.md#adr-0026) la intesta a questa pagina per
nome. La domanda: quando si crea un utente su un membro di un replica set, dove finisce?

**Su tutti.** Gli utenti sono documenti in `admin.system.users`, e `admin` è un database replicato
come gli altri. Creando `lettore-demo` sul primario, i due secondari lo vedono
([V-038](../Sources.md#v-038)):

```text
mongo-rs-1 (primario)   utenti=2   admin.admin   admin.lettore-demo
mongo-rs-2 (secondario) utenti=2   admin.admin   admin.lettore-demo
mongo-rs-3 (secondario) utenti=2   admin.admin   admin.lettore-demo
```

Da cui tre conseguenze pratiche, tutte misurate.

**Un utente si crea una volta sola, e sul primario.** Un secondario risponde come risponde a
qualsiasi scrittura:

```text
createUser su un secondario -> NotWritablePrimary: not primary
```

**Un utente locale a un nodo non esiste**, e non per convenzione. L'unico database che non viene
replicato è `local`, e MongoDB rifiuta di metterci utenti:

```text
createUser sul database local -> BadValue: Cannot create users in the local database
```

Il rifiuto è netto e vale la pena leggerlo per quello che è: il posto dove un utente «solo di questo
nodo» potrebbe vivere è precisamente l'unico posto che gli è vietato. In un replica set, ogni utente
è un oggetto del cluster.

**L'utente interno dei membri non è un documento.** Cercando `__system` in `admin.system.users`, su
tutti e tre i membri, il conteggio è zero. L'identità con cui i membri parlano fra loro **non sta
nel database**: sta nel keyfile — o, con X.509, nel certificato. È il motivo per cui perdere il
keyfile non è come perdere una password: non c'è un documento da riscrivere, c'è un file da
ridistribuire ovunque.

> **Non eseguito.** Il caso dello **sharded cluster** è diverso, e qui non c'è. Là ogni shard è un
> replica set con il proprio `admin`, quindi gli utenti locali a uno shard esistono davvero — sono
> quelli che [ADR-0026](../Decision.md#adr-0026) prevede «dove una demo debba ispezionare un singolo
> shard». E l'eccezione localhost si comporta diversamente: «In a sharded cluster, the localhost
> exception applies to each shard individually as well as to the cluster as a whole»
> ([S-006](../Sources.md#s-006)). Niente di tutto questo è stato provato su questo branch: è materia
> di `feature/03`.

---

## 5. Provarlo in due minuti

Sullo stack già avviato con `make up-02`, da dentro un membro:

```bash
# 1. --auth non c'è nel comando
docker inspect mongo-rs-1 --format '{{json .Config.Cmd}}'

# 2. il keyfile, e i suoi permessi
docker exec mongo-rs-1 stat -c '%n %a %U:%G %s byte' /keyfile/mongo-keyfile

# 3. senza credenziali: hello() passa, il resto no
docker exec mongo-rs-1 mongosh --quiet \
  "mongodb://localhost:27017/?directConnection=true" \
  --eval 'print(db.hello().setName); db.getSiblingDB("admin").system.users.countDocuments({})'

# 4. l'utente interno non è un documento (serve autenticarsi)
docker exec mongo-rs-1 mongosh --quiet \
  "mongodb://admin:$PASSWORD_AMMINISTRATORE@localhost:27017/?directConnection=true&authSource=admin" \
  --eval 'print(db.getSiblingDB("admin").system.users.countDocuments({user: "__system"}))'
```

Il quarto comando stampa `0`. Il terzo stampa `rs0` e poi `Unauthorized`, che è il risultato giusto:
il replica set dice il proprio nome a chiunque e nient'altro a nessuno.

La password sta in `docker/02-replicaset/.env`, che è ignorato da git e non entra nel repository
([ADR-0014](../Decision.md#adr-0014)).

---

## Cosa questa pagina non copre

- **Come si producono i certificati X.509.** La fonte stessa lo esclude dal proprio ambito
  ([S-061](../Sources.md#s-061)), e questo repository fa lo stesso. Qui ci sono i requisiti che i
  certificati devono soddisfare, non le istruzioni per emetterli.
- **X.509 funzionante sullo stack del lab.** È stata una scelta, non una dimenticanza: allungherebbe
  `make up-02` con una generazione di chiavi, metterebbe dentro un lab che deve funzionare anche fra
  un anno dei certificati con una scadenza, e sposterebbe la demo dal replica set alla PKI. La
  motivazione per esteso è in [ADR-0048](../Decision.md#adr-0048).
- **Il rolling upgrade vero**, su un cluster misto. Provato su un nodo solo: §3.3.
- **La rotazione dei certificati.** Riportata dalla fonte, non eseguita: §3.5.
- **L'autenticazione dei client via X.509**, che è cosa diversa dall'autenticazione interna fra
  membri.
- **La rotazione del keyfile.** La documentazione consultata non la descrive, e questa pagina non la
  inventa.
- **Gli utenti locali a uno shard**, e l'eccezione localhost su uno sharded cluster: `feature/03`.
- **I ruoli e i privilegi.** Il lab crea un solo utente, con `root`, perché è un lab. Che cosa sia
  ragionevole in un'installazione vera — ruoli separati per applicazione, backup e diagnostica — è
  una decisione che questo repository non prende.

---

**Decisioni correlate:** [ADR-0048](../Decision.md#adr-0048) (la forma di questa pagina),
[ADR-0005](../Decision.md#adr-0005) (la sicurezza graduata sui tre stack),
[ADR-0014](../Decision.md#adr-0014) (il keyfile in un volume nominato, e fuori dal repository),
[ADR-0026](../Decision.md#adr-0026) (la catena di inizializzazione, e il debito che il §4 salda),
[ADR-0040](../Decision.md#adr-0040) (chi crea l'utente amministratore, e come si esce dal paradosso).

**Fonti:** [S-002](../Sources.md#s-002), [S-005](../Sources.md#s-005), [S-006](../Sources.md#s-006),
[S-061](../Sources.md#s-061), [S-062](../Sources.md#s-062), [S-063](../Sources.md#s-063),
[V-038](../Sources.md#v-038), [V-039](../Sources.md#v-039), [V-040](../Sources.md#v-040)
