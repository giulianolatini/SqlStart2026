# Revisione della PR #stack-docker — foglio di triage

Prodotto da `.claude/skills/revisione-pr/scripts/revisione.sh`. I rilievi arrivano da due revisori esterni e **non sono ancora un giudizio**: lo diventano quando ogni scheda ha un verdetto motivato scritto sotto.

**7 rilievi** — Codex (codex): 4, Gemini Pro (agy): 3.

| ID | Gravità | Confidenza | Categoria | Titolo | Verdetto |
|---|---|---|---|---|---|
| C-2 | alta | alta | security | Le porte dei database sono pubblicate su tutte le interfacce dell'host | **respinto sugli stack · rischio aperto per il palco** |
| G-1 | alta | alta | security | Password di amministrazione passata in chiaro negli argomenti della riga di comando | **accolto · rinviato a un ADR** |
| C-3 | media | alta | altro | La guardia contro i membri di troppo può lasciar passare container ancora in avvio | **accolto** |
| C-4 | media | alta | altro | Gli init degli shard dichiarano presente l'amministratore senza verificarne le credenziali | **accolto ed esteso · rinviato** |
| G-2 | media | alta | congruita-commit | Ambiti mancanti e soggetti in maiuscolo nei messaggi di commit | **respinto sul merito · difetto nella skill** |
| G-3 | media | alta | congruita-commit | Rottura di compatibilità non dichiarata nella rimozione della variabile PULL_POLICY | **respinto** |
| C-1 | bassa | alta | congruita-commit | I messaggi dei commit omettono sistematicamente l'ambito obbligatorio | **respinto sul merito · difetto nella skill** |

## C-2 — Le porte dei database sono pubblicate su tutte le interfacce dell'host

*Sollevato da Codex (codex).*

- **Categoria:** security
- **Gravità:** alta
- **Confidenza:** alta
- **Dove:** docker/01-standalone/compose.yaml:55; sezioni ports degli stack 02 e 03

**Evidenza citata dal revisore:**

```
- "${PORTA_HOST:-27017}:27017"
```

**Perché sarebbe un problema:** La pubblicazione omette l'indirizzo di loopback e permette connessioni attraverso le interfacce esterne dell'host, salvo protezioni esterne non documentate nel dossier. Sullo standalone, deliberatamente privo di autenticazione, questo permette a chi raggiunge la porta di leggere, modificare o cancellare i dati; gli altri stack contraddicono il vincolo dichiarato di esposizione limitata alla macchina del relatore.

**Rimedio proposto:** Anteporre 127.0.0.1 a tutte le pubblicazioni destinate all'host, mantenendo la comunicazione fra container sulla rete Compose.

### Verdetto

**Respinto come difetto degli stack, accolto come rischio operativo aperto per il 18 settembre.**
La distinzione non è formale: cambia chi deve agire e quando.

**Il fatto, misurato.** Non mi sono fidato né del revisore né del file Compose, e ho provato:

```
$ docker port mongo-standalone
27017/tcp -> 0.0.0.0:27017
$ ipconfig getifaddr en0
192.168.178.61
$ docker run --rm --network host mongo:7.0.40 mongosh --quiet \
    --host 192.168.178.61 --port 27017 lab --eval 'db.ordini.countDocuments({})'
50000
```

Cinquantamila documenti letti **dall'indirizzo di rete locale della macchina, senza credenziali**.
`netstat` conferma `*.27017`, `*.27021` e `*.27117` in `LISTEN` su tutte le interfacce. Il
revisore ha ragione sul fatto, e il fatto è esattamente quanto grave sembra: chi legge può anche
scrivere e può anche fare `dropDatabase()`.

**Perché il rilievo non è però un difetto degli stack.** La scelta è deliberata, dichiarata e
documentata da prima di questa release: è l'esempio negativo di
[ADR-0005](../Decision.md#adr-0005), scritto in testa al file Compose, e
`docs/02-architetture/standalone.md:403-407` lo descrive meglio di quanto lo descriva il revisore
— «**Chiunque possa raggiungere quella porta è amministratore.** Su un portatile dietro un router
domestico è irrilevante; su una rete d'ufficio, **di conferenza** o di coworking non lo è.» Il
rimedio che il revisore propone, `127.0.0.1:` davanti alle pubblicazioni, sta già scritto sia lì
(riga 409) sia nella trappola [T-10](../02-architetture/trappole-mongodb-in-docker.md), riga 386.
Applicarlo agli stack cancellerebbe l'esempio negativo, cioè uno dei contenuti didattici del talk.

**Quello che invece manca davvero, e che il revisore ha trovato senza cercarlo.** Il documento che
nomina le reti di conferenza è la pagina dell'architettura standalone. Il documento che si usa
**il 18 settembre, alla Fiera di Ancona, sulla Wi-Fi della conferenza** è il runbook — e il
runbook non dice niente in proposito: `grep -in 'rete|wi-fi'` su `runbook-demo.md` dà nove righe,
tutte sul fatto che il lab non ha bisogno della rete per *funzionare*, nessuna sul fatto che la
rete può arrivare a lui. Per la durata del talk ci sarà una sala piena di gente, molta della quale
sa che cos'è la porta 27017, sulla stessa rete di tre `mongod` di cui uno senza autenticazione.

Azione, e la scelta fra le due è del PO perché tocca la scena:

1. **La via minima:** una riga nella §1.2 del runbook — Wi-Fi spenta durante le demo, o firewall
dell'host acceso — e una nota che dica perché. Costa zero e non tocca niente. 2. **La via
dichiarativa:** un `docker/01-standalone/compose.palco.yaml` che sovrascrive la sola riga `ports`
con `127.0.0.1:`, da usare in sala. L'esempio negativo resta nel file principale, dove insegna; il
palco gira sul loopback.

Preferisco la 1, perché la 2 introduce un secondo modo di accendere lo stack a dodici giorni dal
talk, e ciò che si accende in sala deve essere ciò che è stato provato.

## G-1 — Password di amministrazione passata in chiaro negli argomenti della riga di comando

*Sollevato da Gemini Pro (agy).*

- **Categoria:** security
- **Gravità:** alta
- **Confidenza:** alta
- **Dove:** docker/03-sharded/compose.yaml

**Evidenza citata dal revisore:**

```
- ${PASSWORD_AMMINISTRATORE:?assente — copiare docker/03-sharded/.env.example in .env e riempire la password}
```

**Perché sarebbe un problema:** Docker Compose interpola la variabile d'ambiente direttamente nell'array command per i servizi add-shard e seed. Passando la password come argomento, essa resta esposta in chiaro e permanentemente visibile ispezionando i container con docker inspect, contraddicendo la regola di sicurezza motivata poco prima nel commento all'healthcheck di mongos.

**Rimedio proposto:** Rimuovere la password dall'array command e farla leggere internamente agli script js dalle variabili d'ambiente (già iniettate tramite environment), oppure passare il comando tramite sh -c e usare $$PASSWORD_AMMINISTRATORE per posticipare l'espansione a runtime.

### Verdetto

**Accolto sul fatto, respinto sulla diagnosi**, e con una conseguenza che il revisore non ha
visto: il rimedio che sottintende non basterebbe.

**Il fatto è vero, verificato senza stampare niente.** `docker/03-sharded/compose.yaml:1149` e
`:1224` interpolano `${PASSWORD_AMMINISTRATORE}` dentro l'array `command` di `add-shard` e `seed`.
Ispezionato il container reale, con i valori oscurati in uscita:

```
$ docker inspect sh-add-shard --format '{{json .Config.Cmd}}' | <redattore>
["mongosh","--quiet","--host","loca…","-u","admin","-p","pass…","--au…","--file","/init…"]
```

La credenziale è nella configurazione del container, in chiaro, e ci resta finché il container
esiste.

**Dove la diagnosi sbaglia.** Il revisore dice che questo «contraddice la regola di sicurezza
motivata poco prima nel commento all'healthcheck di `mongos`». Non la contraddice: quella regola,
che è [ADR-0054](../Decision.md#adr-0054), vieta di passare la password con `-e` al **client
`docker`**, perché lì finirebbe nella riga di comando *dell'host*, dove `ps` la mostra a qualunque
processo dell'utente e dove nessuno la riscrive. Qui siamo in un posto diverso: il file Compose,
letto da Compose, che la mette nella config del container. È un'esposizione reale ma di natura
diversa, e ADR-0054 non se n'era mai occupata.

**La conseguenza che rende il rimedio ovvio insufficiente.** Togliere la password dal `command`
non basta, perché è esposta **anche** nell'ambiente dello stesso container:

```
$ docker inspect sh-add-shard --format '{{json .Config.Env}}' | <solo i nomi>
"UTENTE_AMMINISTRATORE=   "PASSWORD_AMMINISTRATORE=   "PATH=   …
```

`compose.yaml:1139` la passa già come variabile d'ambiente al medesimo servizio. Chi può fare
`docker inspect` sul `command` può farlo sull'`Env`: sono lo stesso comando. Quindi «spostarla
nell'ambiente» sarebbe un rimedio che non rimedia — e sarebbe esattamente il genere di correzione
che sembra un esito.

**Che cosa protegge davvero, e resta vero.** Lo dice già `tools/smoke-sharded.sh:154-158`: che sia
una password di laboratorio e che il file che la porta stia fuori dal repository. Il modello di
minaccia di `docker inspect` è «qualcuno ha già accesso al demone Docker di questa macchina», cioè
qualcuno che può anche montare i volumi e leggere i dati direttamente.

**Verdetto operativo: accolto e rinviato, non da chiudere prima del 18 settembre.** Il rilievo
merita una decisione scritta — un ADR che estenda ADR-0054 dicendo dove la credenziale può stare e
dove no, e che dichiari `Config.Cmd` e `Config.Env` dei container di init come esposizione
accettata e perché. Riscrivere adesso i due servizi di init, che sono quelli che costruiscono il
cluster, a dodici giorni dal talk, per un'esposizione locale a una password di laboratorio,
sarebbe il baratto sbagliato.

## C-3 — La guardia contro i membri di troppo può lasciar passare container ancora in avvio

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** docker/03-sharded/init/10-cfg-initiate.js:117; docker/03-sharded/init/11-shard-initiate.js, ciclo sui CANDIDATI

**Evidenza citata dal revisore:**

```
if (!MEMBRI.includes(candidato) && risponde(candidato)) {
```

**Perché sarebbe un problema:** Con profilo completo ed elenchi del palco, il ciclo precedente attende soltanto il primo membro, mentre ogni candidato escluso viene interrogato una sola volta. Se gli altri container non accettano ancora connessioni, la guardia passa e inizializza set a un membro; successivamente gli altri possono diventare healthy senza entrare nella replica, lasciando verde proprio il caso che la guardia promette di impedire.

**Rimedio proposto:** Verificare la coerenza fra profilo ed elenchi prima dell'avvio oppure fornire agli init un elenco autorevole dei servizi selezionati, senza dedurne l'assenza da una singola connessione fallita. Riprodurre il caso ritardando l'avvio dei membri esclusi.

### Verdetto

**Accolto**, e il rimedio esiste già — è lo stesso di [G-5 del fascicolo
`talk`](2026-09-06-talk.md), trovato da un revisore diverso su un altro fascicolo.

**Che il meccanismo sia quello che il revisore descrive è certo dal codice.**
`docker/03-sharded/init/10-cfg-initiate.js:61-69`: `risponde(host)` apre una connessione, chiede
`hello()` e su qualunque eccezione torna `false`. **Un tentativo solo, nessuna attesa.** Un
container che non ha ancora aperto la porta è indistinguibile da un container che non c'è.

Il ciclo di attesa che precede (righe 90-111) aspetta solo i membri di `MEMBRI_*`. Con il profilo
`completo` e `MEMBRI_CFG` lasciato al valore del palco, aspetta **cfg1** e basta; poi interroga
cfg2 e cfg3 una volta ciascuno. E `compose.yaml:835-837` mostra che `cfg-init` ha una sola
condizione d'ingresso, `cfg1: service_healthy`: cfg2 e cfg3 partono insieme a cfg1 ma nessuno
aspetta loro.

**Quanto sia raggiungibile la finestra è l'unica cosa che non ho misurato, e dico perché.**
Diventare *healthy* costa a cfg1 più che rispondere a `hello()`, quindi partendo insieme cfg2 e
cfg3 di solito rispondono già quando la guardia li interroga. La finestra si apre solo se lo
scarto d'avvio è grande — undici servizi su un portatile carico, che è la macchina del talk.
Riprodurla richiederebbe `make reset-03` con avvii ritardati, e `reset-03` cancellerebbe lo stato
dello stack 03 su cui poggia [V-090](../Sources.md#v-090). Non l'ho fatto: il prezzo della prova è
più alto di quello che la prova aggiungerebbe, perché la conclusione non cambia.

**Non cambia perché la correzione giusta rende la guardia superflua.** Il primo dei due rimedi
proposti — «verificare la coerenza fra profilo ed elenchi prima dell'avvio» — è realizzabile oggi:
ho verificato sotto G-5 che una variabile d'ambiente **vince** sull'`--env-file` in Compose,
quindi il `Makefile` può derivare `MEMBRI_CFG`, `MEMBRI_SHARD1` e `MEMBRI_SHARD2` da `PROFILO` e
passarle lui. Il disallineamento che la guardia intercetta a valle diventa impossibile a monte, e
le due sorgenti dello stesso fatto — la variabile e `--profile` — tornano a essere una sola.

La guardia resta dov'è: continua a proteggere chi lancia `docker compose` a mano, che è il caso
per cui era stata scritta. Semplicemente smette di essere l'unica difesa.

## C-4 — Gli init degli shard dichiarano presente l'amministratore senza verificarne le credenziali

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** docker/03-sharded/init/11-shard-initiate.js, catch della createUser

**Evidenza citata dal revisore:**

```
const gia = errore.codeName === "Unauthorized" || errore.codeName === "Location51003";
```

**Perché sarebbe un problema:** Unauthorized dimostra che la richiesta anonima è vietata, non che esista l'amministratore richiesto con la password prevista. Se uno shard conserva utenti diversi o una password precedente, l'init esce comunque con successo e le operazioni successive attraverso mongos possono riuscire usando le credenziali del cluster e il keyfile, mentre l'accesso diretto allo shard fallirà durante la demo.

**Rimedio proposto:** Dopo la creazione o il recupero dell'errore, autenticarsi direttamente sullo shard con le credenziali richieste e verificare l'utente e i privilegi necessari; uscire con errore se la verifica fallisce.

### Verdetto

**Accolto, ed esteso.** Il rilievo ha ragione sulla logica, cita un file solo su due, e sbaglia
bersaglio sulle conseguenze: il caso pericoloso non è quello che descrive.

**La logica, riprodotta.** Il `catch` prende per «utente già presente» due `codeName`,
`Unauthorized` e `Location51003`, o il messaggio «already exists». Eseguito sul cluster acceso:

```
$ docker exec sh-shard1a mongosh --quiet --host localhost --eval \
    'try { db.getSiblingDB("admin").createUser({user:"admin", pwd:"una-password-qualunque",
                                                roles:[{role:"root",db:"admin"}]}); print("creato"); }
     catch (e) { print("codeName=" + e.codeName + " | " + e.message); }'
codeName=Unauthorized | Command createUser requires authentication
```

Il messaggio del server lo dice per esteso: *requires authentication*. `Unauthorized` arriva
**prima** che il server guardi il contenuto della richiesta, quindi non è affatto una prova che
l'utente esista, e tanto meno che esista con quella password. È una prova che l'eccezione
localhost è chiusa. Il ramo non distingue «c'è ed è quello giusto» da «c'è, ma con un'altra
credenziale».

**Il rilievo cita un file su due.** Lo stesso identico `catch` sta anche in
`docker/03-sharded/init/10-cfg-initiate.js:256-264`, per l'amministratore del config server, con
il commento che ne rivendica la scelta (`:243-247`: «Un one-shot che fallisce al secondo avvio è
un `make up-03` che fallisce davanti al pubblico»). Il revisore ha guardato solo
`11-shard-initiate.js`.

**Lo stato reale, verificato.** Su tutti e due gli shard, con la credenziale passata da stdin al
prompt di `mongosh` così che non compaia in nessuna riga di comando (ADR-0054):

```
sh-shard1a -> {"authenticatedUsers":[{"user":"admin","db":"admin"}],
               "authenticatedUserRoles":[{"role":"root","db":"admin"}]}
sh-shard2a -> (identico)
```

**Dove il rilievo sbaglia, e dove ha ragione più di quanto sappia.** La rete di sicurezza a valle
esiste, ma copre solo metà del problema, e la metà scoperta è proprio quella degli shard:

- **L'amministratore del config server è coperto.** `add-shard` si autentica davvero
  — `compose.yaml:1146-1151` passa `-u ${UTENTE_AMMINISTRATORE} -p ${PASSWORD_AMMINISTRATORE}` — e `up-03` diventa `running`
solo dopo che `add-shard` è uscito 0 (`:1306-1309`, ADR-0062). Una credenziale disallineata sul
config server fa fallire `make up-03`, rumorosamente, prima del palco.
- **L'amministratore locale degli shard non è coperto da niente.** `mongos` si autentica verso il
config server, non verso gli shard; nessun servizio dello stack usa mai l'utente locale di uno
shard. Una password rimasta indietro lì dentro resta invisibile a tutto `up --wait`.

Va anche detto che la sonda che avrei creduto d'aiuto non lo è: l'healthcheck di `mongos` è
`quit(db.hello().ok === 1 ? 0 : 1)` senza credenziali (`compose.yaml:1027-1033`), e il file lo
dichiara misurato (`:1022-1026`, «`hello()` passa senza credenziali anche su un `mongos` con
`--keyFile` e utenti già creati»). Non intercetterebbe nulla, per costruzione e per scelta.

**Perché il rimedio non entra prima del 18 settembre.** Chi incontrerebbe il guasto non è la
scena. In `docs/05-talk/` non c'è nessun accesso diretto a uno shard: la distribuzione si mostra
da `mongos`. L'utente locale compare invece in `docs/04-mongosh/guida-mongosh.md:608` e in
`docs/03-amministrazione/sicurezza-keyfile-x509.md:418`, cioè nel materiale che si legge dopo, con
calma, e dove un errore costa un'ora e non una scena.

Accolto come debito, nella forma che il revisore propone e su **tutti e due** i file: dopo il
`catch`, autenticarsi con le credenziali attese e uscire in errore se non funzionano — così il
messaggio «non lo ricreo» diventa un'affermazione misurata invece che una deduzione da un codice
d'errore che parla d'altro. Da fare insieme alla riscrittura degli init chiesta da G-1.

## G-2 — Ambiti mancanti e soggetti in maiuscolo nei messaggi di commit

*Sollevato da Gemini Pro (agy).*

- **Categoria:** congruita-commit
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** Tutti i commit (es. 76defde5, a6deb1f7)

**Evidenza citata dal revisore:**

```
feat: lo stack 01 — un mongod solo, con le risorse dichiarate\nfeat: Task 2 — keyfile-init, il primo anello della catena
```

**Perché sarebbe un problema:** Il repository usa Conventional Commits e le direttive impongono di indicare un ambito (uguale alla cartella toccata) e il soggetto in minuscolo. Nei commit proposti l'ambito è sistematicamente omesso (es. manca 01-standalone) e diversi soggetti iniziano in maiuscolo.

**Rimedio proposto:** Eseguire un rebase interattivo riscrivendo i messaggi per includere l'ambito corretto e convertire in minuscolo l'iniziale del soggetto (es. feat(01-standalone): lo stack 01...).

### Verdetto

**Respinto sul merito — e il difetto è nella skill, non nel repository.** Il rilievo fa due
affermazioni, e tutte e due sono false contro questo repository. La prima perché la regola non è
di qui; la seconda perché la regola di qui c'è, ed è rispettata senza eccezioni.

**L'ambito.** Misurato su `main..HEAD`:

```
$ git log --format='%s' main..HEAD | wc -l              → 156
$ git log --format='%s' main..HEAD | grep -cE '^[a-z]+\([^)]+\):'  → 0
```

Zero su centocinquantasei. Non è una dimenticanza sparsa: è che questo repository non ha mai usato
l'ambito. La direttiva che il revisore cita arriva da
`.claude/skills/revisione-pr/prompt/revisione.md:12-13`, importata ieri dal repository d'origine
insieme alla skill, e descrive le convenzioni di *quel* repository. Il revisore ha fatto
esattamente quello che gli avevamo chiesto: il difetto è nostro, e vale anche per C-1 qui sotto e
per G-1/C-1 del fascicolo `talk`. Quattro rilievi da una riga di prompt sbagliata.

**Il soggetto in maiuscolo.** Qui il revisore non ha nemmeno la scusa del prompt: la regola c'è
davvero, e il repository la rispetta. Trentatré soggetti su 156 iniziano in maiuscolo, e **tutti e
trentatré** iniziano con un identificatore:

```
ADR-0025 — 12 GiB alla VM Docker per il profilo completo
V-093 e ADR-0124 — due difetti che solo l'uso reale poteva mostrare
Task 8 — le due morti di un primario, e il log che dice perché costano diverso
README di radice — abstract, requisiti, indice
Makefile come punto d'ingresso unico
Merge pull request #4 from giulianolatini/feature/03-stack-sharded
```

`ADR-nnnn`, `V-nnn`, `Task N`, `README`, `Makefile`, `Merge`. Nessuna parola italiana comune
maiuscola, zero eccezioni su 156 commit. La convenzione è «soggetto minuscolo, salvo gli
identificatori», ed è seguita con una regolarità che il revisore ha scambiato per una violazione
perché non aveva modo di sapere quale fosse la regola.

**Il rimedio è comunque impraticabile.** Un rebase interattivo riscriverebbe cronologia già spinta
su `origin/release/1.0`, e la riscrittura della cronologia pubblicata qui non si fa.

**Il residuo, che è la parte utile.** Il rilievo è respinto ma non è sterile: se un revisore
esterno non riesce a dedurre la convenzione in centocinquantasei esempi coerenti, la convenzione
va scritta. Il repository non ha né `CLAUDE.md` né `CONTRIBUTING.md`, cioè non ha la sede. Aprirla
— e correggere `prompt/revisione.md` prima della prossima revisione — è l'azione che questo
rilievo produce.

## G-3 — Rottura di compatibilità non dichiarata nella rimozione della variabile PULL_POLICY

*Sollevato da Gemini Pro (agy).*

- **Categoria:** congruita-commit
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** 80379b47

**Evidenza citata dal revisore:**

```
PULL_POLICY sparisce da .env.example, che al suo posto spiega perché non c'è più
```

**Perché sarebbe un problema:** La rimozione di un parametro d'ambiente preesistente e supportato costituisce una rottura di compatibilità. Il commit tuttavia non dichiara tale rottura, omettendo sia il suffisso ! nel tipo sia la sezione BREAKING CHANGE: nel corpo, come prescritto dalle regole del repository.

**Rimedio proposto:** Modificare il messaggio del commit per dichiarare la rottura di compatibilità, aggiungendo il punto esclamativo (feat!:) o un blocco BREAKING CHANGE: descrittivo nel corpo.

### Verdetto

**Respinto — non c'è compatibilità da rompere, e la rottura è comunque annunciata.**

Il rilievo poggia su un presupposto che non regge alla misura: che `PULL_POLICY` fosse un
parametro «preesistente e supportato», cioè che esista qualcuno legato al contratto vecchio.

```
$ git tag --list | wc -l      → 0
```

Nessun tag, nessun rilascio, mai. `release/1.0` è la prima versione che uscirà: fino al 18
settembre non esiste un utente con un `.env` da migrare. Il suffisso `!` e il piede `BREAKING
CHANGE:` servono a chi aggiorna: qui non c'è nessuno che aggiorna.

Coerentemente, in tutta la cronologia — non solo in questo ramo — nessun commit usa `!` nel tipo e
nessun corpo contiene `BREAKING CHANGE`. Non è una svista ripetuta 156 volte: è che la convenzione
citata dal revisore arriva da `.claude/skills/revisione-pr/prompt/revisione.md`, importata dal
repository d'origine, come per G-2 e C-1.

**E soprattutto: la rottura è già annunciata, meglio di come la chiede il rilievo.** Il commit
`80379b47` ci dedica un paragrafo del corpo («un parametro tolto lascia un buco, e il buco va
spiegato dove qualcuno andrebbe a cercarlo»), ma la cosa che conta sta in
`docker/01-standalone/.env.example:12-14`, cioè nel file che apre chi si trova senza la variabile:

```
# PULL_POLICY non esiste più: `pull_policy: never` è scritto fisso nel file
# Compose e non si sovrascrive da qui (ADR-0039). Se l'avvio fallisce dicendo che
# l'immagine manca, la risposta è `make images-pull`, una volta, con la rete.
```

Dice che è sparita, perché, con quale decisione, e cosa fare al suo posto. Un piede `BREAKING
CHANGE:` in un messaggio di commit direbbe meno, a meno persone, in un posto dove nessuno lo
cercherebbe. Il rimedio proposto sposterebbe l'avviso dal luogo giusto a quello rituale — e
richiederebbe per giunta di riscrivere cronologia già spinta.

Respinto in pieno. Il residuo è lo stesso di G-2: la convenzione di questo repository va scritta,
perché in sua assenza il revisore ne applica un'altra.

## C-1 — I messaggi dei commit omettono sistematicamente l'ambito obbligatorio

*Sollevato da Codex (codex).*

- **Categoria:** congruita-commit
- **Gravità:** bassa
- **Confidenza:** alta
- **Dove:** 76defde5 e tutti gli altri commit dell'intervallo

**Evidenza citata dal revisore:**

```
feat: lo stack 01 — un mongod solo, con le risorse dichiarate
```

**Perché sarebbe un problema:** Tutti i venti soggetti usano tipo e soggetto senza l'ambito richiesto dalla convenzione del repository. Inoltre diversi iniziano con «Task», anziché con un soggetto italiano minuscolo.

**Rimedio proposto:** Riscrivere i soggetti con l'ambito della cartella di progetto interessata e il soggetto italiano minuscolo, verificando i percorsi effettivi di ciascun commit.

### Verdetto

**Respinto sul merito — difetto nella skill.** È lo stesso rilievo di G-2, sollevato dall'altro
revisore a partire dalla stessa riga di prompt sbagliata, e vale la stessa misura: zero commit su
156 portano un ambito, e la direttiva viene da
`.claude/skills/revisione-pr/prompt/revisione.md:12-13`, importata dal repository d'origine.

Una nota in più, perché C-1 aggiunge un dettaglio che G-2 non ha: il revisore contesta i soggetti
che «iniziano con «Task», anziché con un soggetto italiano minuscolo». `Task N` non è una parola
inglese lasciata lì per pigrizia: è il numero del task nel piano di implementazione, cioè
l'identificatore che lega il commit alla riga del piano che lo ha prodotto. Sta nella stessa
classe di `ADR-0039`, `V-093` e `README`. Toglierlo per far cominciare la frase in minuscolo
perderebbe l'unico aggancio fra la cronologia e i piani in `docs/superpowers/plans/`.

**Che due revisori indipendenti sollevino lo stesso rilievo non ne aumenta la fondatezza**:
conferma solo che leggono lo stesso prompt. È un dato utile sulla revisione, non sul repository —
e va tenuto a mente quando l'accordo fra i due sembra una controprova.

Il residuo è quello di G-2: scrivere la convenzione, e correggere il prompt.

