# Piano di implementazione — `feature/02-stack-replicaset`

> **Per chi esegue il piano:** i passi usano caselle `- [ ]` da spuntare. Ogni task
> termina con un deliverable verificabile e un commit. Leggere anche la specifica
> collegata: questo piano attua decisioni prese lì, non le rimette in discussione — con
> l'unica eccezione dichiarata nel Task 1, che ne scioglie una rimasta ambigua.

---

**Obiettivo:** produrre il secondo dei tre stack Compose — il replica set a tre membri con
autenticazione interna — le tre pagine che lo spiegano, e la demo di failover che è il
centro del talk. Lungo la strada si saldano i quattro debiti che `feature/00` e `feature/01`
hanno intestato per iscritto a questo branch.

**Architettura:** è qui che il talk gira. Lo stack 01 serviva a mostrare cosa **non** si
ottiene con un `mongod` solo; questo stack risponde, e la risposta si vede dal vivo: si
ferma un nodo, il cluster elegge un primario, le scritture riprendono. Tre `mongod` con
`--replSet rs0 --keyFile`, legati da una catena di inizializzazione a tre anelli che
risolve un problema dell'uovo e della gallina — con `--keyFile` l'autenticazione è
obbligatoria, ma prima che esista un utente nessuno può inizializzare la replica.

Quella catena non nasce qui: è la stessa dello sharded cluster, meno gli shard, e
[ADR-0026](../Decision.md#adr-0026) scrive che «le due feature condividono il meccanismo e
vanno scritte per condividerlo». Ciò che si costruisce adesso `feature/03` lo riuserà con
un anello in più, quindi va scritto pensando a un lettore che non è ancora arrivato.

La seconda cosa che sopravvive al branch è l'onestà della demo. `docker kill` non simula un
guasto ([ADR-0034](../Decision.md#adr-0034)): la scena va costruita sapendolo, con la frase
giusta accanto al comando, perché è il momento esatto in cui un ascoltatore attento chiede
«ma allora non riparte da solo?».

**Stack tecnico:** Compose Specification (senza chiave `version:`), MongoDB **7.0.40**
dall'immagine ufficiale pinnata per digest, `mongosh`, Bash (`set -euo pipefail`), Python
3.13+ con `pytest` per gli strumenti di repository, GNU Make, Markdown.

**Specifica:** [`docs/00-progetto/2026-08-24-design.md`](2026-08-24-design.md) §5.1
(bilancio delle risorse), §5.2 (mappa delle porte), §5.4 (stack 02), §5.6 (trappole).
L'elenco delle pagine dovute da questo branch è nell'indice
[`docs/README.md`](../README.md), colonna «Branch».

---

## Vincoli globali

Valgono per ogni task, senza doverli ripetere.

- **Lingua:** tutto il materiale prodotto è in **italiano**, compresi commenti nel codice,
  messaggi degli script e messaggi di commit.
- **Documentazione:** tutta sotto `docs/`. In radice esiste **solo** `README.md`.
- **Citazioni:** nessuna affermazione tecnica entra in `docs/` senza un riferimento
  `[S-NNN]`, `[V-NNN]` o `[C-NNN]` verso [`Sources.md`](../Sources.md). La verifica su
  fonte primaria **precede** la scrittura. `make docs-check` deve uscire `0` a ogni commit.
- **Offline:** nessun artefatto destinato al palco può richiedere rete. Ogni servizio
  dichiara `pull_policy: never` **scritto fisso nel file**, mai da variabile
  ([ADR-0039](../Decision.md#adr-0039), che supera [ADR-0018](../Decision.md#adr-0018));
  nessuna immagine usa il tag `latest`, in nessuna circostanza.
- **MongoDB 7.0.40**, immagine ufficiale pinnata **per digest** tramite
  [`tools/images.env`](../../tools/images.env) ([ADR-0028](../Decision.md#adr-0028)). Il
  digest non si scrive a mano nei file Compose: si legge dalla variabile.
- **Compose:** Specification corrente, **senza** chiave `version:`. Sintassi breve
  `mem_limit` / `cpus` nei file, `deploy.resources` solo nella documentazione
  ([ADR-0013](../Decision.md#adr-0013)).
- **Risorse:** ogni servizio dichiara `mem_limit` e `cpus`; ogni `mongod` dichiara
  `--wiredTigerCacheSizeGB` esplicito e **non superiore** al proprio `mem_limit`
  ([ADR-0004](../Decision.md#adr-0004)). Per questo stack, da §5.1 del design: **768m**,
  **0,25 GB** di cache, **0.75** CPU per membro — 2,25 GiB in tutto.
- **Porte host,** da §5.2 del design: `27021`, `27022`, `27023`. Sono già riservate in
  [`tools/preflight.sh`](../../tools/preflight.sh): il controllo di occupazione le conosce
  da prima che questo stack esistesse.
- **Nomi host:** mai indirizzi IP, né nei file né nella documentazione
  ([ADR-0021](../Decision.md#adr-0021)). Qui il vincolo è più stretto del solito: i membri
  di un replica set si registrano nella configurazione con il nome con cui sono stati
  elencati, e quel nome deve risolvere **anche dal client**.
- **Ordine di avvio:** `depends_on` con `condition:`, mai `sleep`
  ([ADR-0023](../Decision.md#adr-0023)).
- **Indipendenza degli stack:** progetto Compose, rete e volumi propri, nessun `include` né
  profilo condiviso con gli altri due ([ADR-0003](../Decision.md#adr-0003)). Lo stack 01
  deve poter restare acceso mentre questo gira.
- **Il keyfile non entra nel repository,** in nessuna forma e in nessun momento
  ([ADR-0014](../Decision.md#adr-0014)).
- **Nomi:** nessun nome di strumento interno nei percorsi o nei contenuti pubblicati. Il
  repository è materiale didattico.
- **Commit:** stile convenzionale (`chore:`, `docs:`, `feat:`, `test:`, `fix:`), corpo in
  italiano che spiega il perché e non il cosa.

---

## Mappa dei file

| Percorso | Responsabilità | Task |
|---|---|---|
| `docker/02-replicaset/compose.yaml` | l'artefatto centrale del talk: tre `mongod` e la catena che li mette in replica | 2-5 |
| `docker/02-replicaset/.env.example` | i parametri che chi clona può cambiare, con i valori del lab come predefiniti | 3 |
| `docker/02-replicaset/init/01-keyfile.sh` | genera il keyfile nel volume nominato, con permessi e proprietario giusti | 2 |
| `docker/02-replicaset/init/10-rs-initiate.js` | `rs.initiate()` con i tre membri e le priorità | 4 |
| `docker/02-replicaset/init/20-dati-demo.js` | dataset deterministico, scritto con `w: "majority"` | 7 |
| `tools/check_stack.py` | le regole nuove che il replica set porta con sé | 6 |
| `tools/tests/test_check_stack.py` | la suite che le guida in TDD | 6 |
| `tools/smoke-replicaset.sh` | verifica dal vivo che il set sia formato, autenticato e scrivibile | 7 |
| `tools/reset-demo.sh` | riporta uno stack allo stato iniziale fra una prova e l'altra — debito di `feature/01` | 8 |
| `Makefile` | target `up-02`, `down-02`, `reset-02`, `logs-02`, `seed-02`, `smoke-02`, `failover-02` | 7-8 |
| `docs/02-architetture/replica-set.md` | topologia, elezioni, read preference, write concern, ritardo di replica | 9 |
| `docs/03-amministrazione/backup-restore.md` | `mongodump`/`mongorestore`, `--oplog` e i suoi limiti, restore verificato | 10 |
| `docs/03-amministrazione/sicurezza-keyfile-x509.md` | perché il lab usa il keyfile, perché MongoDB lo riserva a test e sviluppo, come si passa a X.509 | 11 |
| `docs/02-architetture/trappole-mongodb-in-docker.md` | due trappole nuove: permessi del keyfile, scoperta della topologia | 12 |
| `docs/03-amministrazione/log.md` | i numeri `id` delle righe di elezione, finalmente osservati | 12 |
| `docs/04-mongosh/guida-mongosh.md` | le sezioni marcate «non eseguite qui» diventano eseguite | 12 |
| `docs/05-talk/registrazioni/README.md` | indice dei filmati di riserva e delle registrazioni di terminale | 13 |
| `docs/Decision.md`, `docs/Sources.md` | gli ADR e le fonti del branch | 1, 14 |
| `docs/registro-operativo-sviluppo.md` | il diario, con le note di metodo | 14 |

---

## Task 1 — Chi crea l'utente root: sciogliere l'ambiguità fra il design e ADR-0026

**File:**
- Modificare: `docs/Decision.md`, `docs/Sources.md`

Questo task esiste perché la specifica **non è univoca**, e accorgersene adesso costa
un'ora, accorgersene al Task 4 costa una giornata.

Il design §5.4 descrive la catena così: `mongo-rs-1` parte con
`MONGO_INITDB_ROOT_USERNAME/PASSWORD`, l'entrypoint ufficiale crea l'utente root nella sua
fase temporanea, e `rs-init` si connette **autenticato come root** per eseguire
`rs.initiate()`. Motivo dichiarato: «l'eccezione localhost non copre un container sidecar».

[ADR-0026](../Decision.md#adr-0026), scritta dopo, sullo spike dello sharded cluster, dice
il contrario: i `mongod` partono con `--keyFile` e **senza** variabili di root, e l'utente
amministratore si crea «sotto eccezione localhost». È l'ADR più recente ed è nata da
un'esecuzione vera, il che di norma la fa vincere — ma parla di un config server, e non è
detto che il caso si trasferisca identico.

Le due strade non sono equivalenti, e la differenza è visibile al pubblico: la prima mette
una password in `.env.example`, la seconda no.

- [ ] **Passo 1 — Provare la strada di ADR-0026**

Tre `mongod` con `--keyFile`, senza variabili di root, e `rs.initiate()` eseguito con
`docker compose exec` **sul membro 1**, non da un sidecar. Domanda a cui rispondere con una
esecuzione, non con un ragionamento: l'eccezione localhost è attiva su un `mongod` avviato
con `--keyFile` quando la replica non è ancora inizializzata, e copre una connessione che
arriva da `mongosh` avviato **dentro lo stesso container**?

Registrare l'esito con il comando esatto e l'output, incluso il caso in cui fallisca.

- [ ] **Passo 2 — Provare la strada del design §5.4**

`MONGO_INITDB_ROOT_*` sul solo membro 1, `rs-init` come servizio separato che si connette
autenticato. Verificare le due cose che il design dà per scontate: che l'entrypoint crei
davvero l'utente **prima** che la replica esista, e che i membri 2 e 3, partiti vuoti,
ricevano l'utente in sincronizzazione iniziale.

- [ ] **Passo 3 — La fonte primaria sull'eccezione localhost**

Prima di decidere, leggere cosa la documentazione MongoDB dichiara sull'eccezione localhost:
a quali condizioni è attiva, quando si disattiva, e se il suo ambito è l'interfaccia di rete
o il processo. Nuova voce in [`Sources.md`](../Sources.md) — e se ciò che si misura
contraddice ciò che è scritto, si riportano **entrambe**, come è già stato fatto per
`logRotate` in [ADR-0035](../Decision.md#adr-0035).

- [ ] **Passo 4 — L'ADR che scioglie il nodo**

Un ADR nuovo che registra la scelta e il perché, con la misura accanto. Se vince la strada
del design, l'ADR **non** supera ADR-0026: ne circoscrive l'ambito al config server,
spiegando cosa cambia in un replica set semplice. Se vince ADR-0026, l'ADR dichiara superata
la §5.4 del design e il documento storico riceve una **nota di allineamento in testa**, non
una riscrittura.

La scelta è del Product Owner: il task si ferma qui e la si chiede, portando le due misure.

- [ ] **Passo 5 — `make docs-check` e commit**

---

## Task 2 — `keyfile-init`: il primo anello

**File:**
- Creare: `docker/02-replicaset/compose.yaml` (primo abbozzo), `docker/02-replicaset/init/01-keyfile.sh`

**Interfacce:**
- Consuma: [`tools/images.env`](../../tools/images.env) (variabile `MONGO_IMAGE`).
- Produce: il volume nominato `keyfile` contenente `/keyfile/mongo-keyfile`, `chmod 400`,
  proprietario `999:999`, montato in sola lettura dai tre `mongod`.

- [ ] **Passo 1 — Il servizio one-shot**

```yaml
name: sqlstart-02-replicaset

services:
  keyfile-init:
    image: ${MONGO_IMAGE:?variabile assente: eseguire `make images-pull` oppure passare tools/images.env}
    container_name: rs-keyfile-init
    pull_policy: never
    restart: "no"
    command: ["bash", "/init/01-keyfile.sh"]
    volumes:
      - keyfile:/keyfile
      - ./init/01-keyfile.sh:/init/01-keyfile.sh:ro

volumes:
  keyfile:
```

Tre scelte da non lasciare implicite. Il servizio usa **la stessa immagine** dei `mongod`,
non un'immagine di utilità: una in meno da scaricare, e il vincolo offline ringrazia. Il
`restart: "no"` è obbligatorio su un one-shot — con `unless-stopped` Compose lo rialzerebbe
in continuazione e la catena non completerebbe mai. Il keyfile vive in un **volume
nominato** e non in un bind mount, che è la decisione di [ADR-0014](../Decision.md#adr-0014):
su macOS i bind mount non conservano i permessi, e `mongod` rifiuta di partire con un
keyfile che considera «too open».

- [ ] **Passo 2 — Lo script, idempotente**

```bash
#!/usr/bin/env bash
set -euo pipefail

DESTINAZIONE=/keyfile/mongo-keyfile

if [[ -s "${DESTINAZIONE}" ]]; then
  echo "keyfile già presente: non lo rigenero"
else
  openssl rand -base64 756 > "${DESTINAZIONE}"
  echo "keyfile generato"
fi

chmod 400 "${DESTINAZIONE}"
chown 999:999 "${DESTINAZIONE}"
```

L'idempotenza non è eleganza: al secondo `make up-02` il volume esiste già, e rigenerare il
keyfile significherebbe che i membri non si riconoscono più fra loro. Il `999:999` è
l'utente `mongodb` dell'immagine ufficiale ([S-023](../Sources.md#s-023)); il `chmod` e il
`chown` stanno **fuori** dal ramo condizionale perché un volume ripristinato da un backup
potrebbe avere il contenuto giusto e i permessi sbagliati.

- [ ] **Passo 3 — Verificare permessi e proprietario dal vivo**

Comando: `docker compose --env-file tools/images.env -f docker/02-replicaset/compose.yaml run --rm keyfile-init`
poi ispezionare il volume con `ls -ln` da un container che lo monta.
Atteso: `-r-------- 1 999 999` e una dimensione di 1024 caratteri.

Verificare anche il caso storto, perché è quello che si incontra: montare di proposito un
keyfile con `chmod 644` e osservare **il messaggio d'errore esatto** di `mongod`. Serve al
Task 12: una trappola senza il suo sintomo testuale non è ritrovabile da chi la cerca.

- [ ] **Passo 4 — Commit**

---

## Task 3 — I tre `mongod`: `--replSet`, `--keyFile`, risorse, porte

**File:**
- Modificare: `docker/02-replicaset/compose.yaml`
- Creare: `docker/02-replicaset/.env.example`

**Interfacce:**
- Consuma: il volume `keyfile` dal Task 2.
- Produce: i servizi `mongo-rs-1`, `mongo-rs-2`, `mongo-rs-3` sulle porte host `27021`,
  `27022`, `27023`, ciascuno con volume dati proprio.

- [ ] **Passo 1 — Un membro, scritto per essere copiato tre volte**

```yaml
  mongo-rs-1:
    image: ${MONGO_IMAGE:?variabile assente: eseguire `make images-pull` oppure passare tools/images.env}
    container_name: mongo-rs-1
    hostname: mongo-rs-1
    pull_policy: never
    restart: unless-stopped
    command:
      - --replSet
      - ${NOME_REPLICA:-rs0}
      - --keyFile
      - /keyfile/mongo-keyfile
      - --bind_ip_all
      - --wiredTigerCacheSizeGB
      - "0.25"
    mem_limit: ${MEMORIA_MEMBRO:-768m}
    cpus: ${CPU_MEMBRO:-0.75}
    ports:
      - "${PORTA_MEMBRO_1:-27021}:27017"
    volumes:
      - keyfile:/keyfile:ro
      - dati-1:/data/db
    depends_on:
      keyfile-init:
        condition: service_completed_successfully
```

Quattro punti che il Task 9 dovrà spiegare al pubblico. Il keyfile è montato **in sola
lettura**: un membro non ha ragione di riscriverlo, e il montaggio lo impedisce invece di
fidarsi. Ogni membro ha il **proprio** volume dati — condividerne uno significherebbe tre
processi sullo stesso `/data/db`, che è il modo più rapido di corrompere un database. La
cache WiredTiger è dichiarata a `0,25 GB` contro un `mem_limit` di `768m`, come impone
[ADR-0004](../Decision.md#adr-0004): senza, ogni `mongod` dimensionerebbe la cache sulla
memoria della VM Docker e i tre membri insieme la esaurirebbero. Il `--bind_ip_all` serve
perché dentro un container l'interfaccia utile non è `localhost`, ed è anche la ragione per
cui questo stack **non** va esposto fuori dalla macchina di chi presenta.

- [ ] **Passo 2 — Gli altri due membri**

Identici, con `mongo-rs-2` / `mongo-rs-3`, `dati-2` / `dati-3`, porte `27022` / `27023`.
Ripetizione deliberata: nessun ancoraggio YAML e nessun `extends`. Il file è materiale
didattico e va letto dall'alto in basso da chi non conosce né il progetto né gli ancoraggi
YAML — la stessa ragione per cui [ADR-0003](../Decision.md#adr-0003) tiene i tre stack
separati anche a costo di duplicare.

- [ ] **Passo 3 — `.env.example` commentato riga per riga**

I parametri che chi clona può cambiare senza rompere le demo: nome della replica, porte,
memoria, CPU. **Nessuna** variabile per `pull_policy`, che è fissa nel file per
[ADR-0039](../Decision.md#adr-0039). Se il Task 1 ha scelto la strada del design, qui
compaiono anche le credenziali di root, con scritto in chiaro che sono credenziali da lab e
perché è accettabile che lo siano.

- [ ] **Passo 4 — `config -q` e `check_stack.py` sul file incompleto**

Comando: `docker compose --env-file tools/images.env -f docker/02-replicaset/compose.yaml config -q`
Atteso: uscita `0`.
Poi: `uv run --project tools python tools/check_stack.py --ambiente tools/images.env docker/02-replicaset/compose.yaml`
Atteso: **verde sulle regole esistenti**. Le regole del replica set non esistono ancora: è
il Task 6 a scriverle, ed è giusto che questo passo non le veda fallire.

- [ ] **Passo 5 — Commit**

---

## Task 4 — `rs-init`: `rs.initiate()` e le priorità

**File:**
- Modificare: `docker/02-replicaset/compose.yaml`
- Creare: `docker/02-replicaset/init/10-rs-initiate.js`

**Interfacce:**
- Consuma: i tre `mongod` sani (healthcheck del Task 5).
- Produce: un replica set `rs0` formato, con primario prevedibile e utente amministratore
  utilizzabile.

- [ ] **Passo 1 — Lo script di inizializzazione**

```javascript
rs.initiate({
  _id: "rs0",
  members: [
    { _id: 0, host: "mongo-rs-1:27017", priority: 2 },
    { _id: 1, host: "mongo-rs-2:27017", priority: 1 },
    { _id: 2, host: "mongo-rs-3:27017", priority: 1 },
  ],
});
```

I membri si elencano con il **nome di servizio Compose e la porta interna `27017`**, mai con
la porta host e mai con un indirizzo ([ADR-0021](../Decision.md#adr-0021)). Il motivo è più
sottile del solito vincolo: quei nomi finiscono **dentro** la configurazione della replica,
e sono i nomi che il driver riceverà quando scoprirà la topologia. Un client fuori dalla
rete Compose li riceve e non li risolve — è la seconda trappola del Task 12, e nasce qui.

La `priority: 2` sul primo membro non è cosmetica: rende **prevedibile** chi sarà primario
all'avvio, il che per una demo cronometrata vale più della simmetria. Va detto al pubblico,
perché ha un effetto visibile nella scena di failover — quando il nodo fermato torna, si
riprende il ruolo. Il Task 9 lo spiega, il Task 8 lo prova.

- [ ] **Passo 2 — Il servizio, e l'attesa che non è un `sleep`**

`rs-init` dipende dai tre membri con `condition: service_healthy` e da `keyfile-init` con
`condition: service_completed_successfully`. Nessun `sleep`, in nessuna forma
([ADR-0023](../Decision.md#adr-0023)).

Lo script si passa con `--file` e **percorso assoluto**, mai per pipe: dentro un container
la directory di lavoro non è quella da cui si è digitato il comando, `load()` non ha
percorso di ricerca, e `mongosh` tratta lo standard input come una sessione interattiva
stampandoci sopra i prompt ([ADR-0036](../Decision.md#adr-0036),
[S-047](../Sources.md#s-047)).

- [ ] **Passo 3 — Idempotenza, che qui è una questione di scena**

Un secondo `make up-02` non deve fallire. Lo script verifica se la replica è già
inizializzata e in quel caso esce `0` dicendolo. Il codice di uscita resta fra 1 e 125
([ADR-0036](../Decision.md#adr-0036)): `exit(300)` arriva al chiamante come 44 ed `exit(-1)`
come 255.

- [ ] **Passo 4 — Misurare quanto ci mette**

Cronometrare da `make up-02` al primo `PRIMARY`, tre volte, a freddo e a caldo. Il numero
serve al runbook e al Task 13: una scena da trenta secondi e una da tre minuti si raccontano
in modi diversi, e il tempo va saputo **prima** di essere sul palco. Nuova voce di verifica
in [`Sources.md`](../Sources.md).

- [ ] **Passo 5 — Commit**

---

## Task 5 — Healthcheck: un membro operativo, non un processo vivo

**File:**
- Modificare: `docker/02-replicaset/compose.yaml`

- [ ] **Passo 1 — La condizione giusta**

L'healthcheck valuta `hello().isWritablePrimary || hello().secondary`, come prescrive §5.4
del design. La differenza con un `ping` è tutta qui: `ping` risponde a un processo avviato,
questa condizione risponde a un **membro operativo**, e `depends_on` finalmente attende la
cosa giusta.

- [ ] **Passo 2 — La verifica che non si può saltare**

`hello` deve rispondere **senza credenziali** su un `mongod` avviato con `--keyFile`,
altrimenti l'healthcheck andrebbe autenticato e ci si troverebbe a mettere una password
dentro il file Compose per sapere se un nodo è vivo. La documentazione MongoDB elenca i
comandi ammessi prima dell'autenticazione: leggerla, citarla, e **provare** il comando su un
nodo con autenticazione attiva. Nuova voce in [`Sources.md`](../Sources.md).

- [ ] **Passo 3 — L'uovo e la gallina, di nuovo**

Prima di `rs.initiate()` nessun membro è primario né secondario, quindi l'healthcheck è
rosso per costruzione, e `rs-init` che attende `service_healthy` non partirebbe mai. Il
`start_period` non basta a risolverlo: **allunga** la tolleranza, non cambia la condizione.

Le due uscite possibili, da scegliere misurando e non ragionando: un healthcheck che
accetta anche lo stato «membro non ancora configurato» finché la replica non esiste, oppure
`rs-init` che dipende dai membri con `condition: service_started` e attende da sé la
disponibilità con un ciclo di tentativi interno. La seconda sposta l'attesa dentro uno
script che possiamo leggere; la prima la lascia in Compose, dove è più dichiarativa ma più
difficile da spiegare a voce. Registrare la scelta nel Task 14.

- [ ] **Passo 4 — `make up-02` completo, dal nulla**

Comando: `docker compose ... down -v` seguito da `up -d --wait`.
Atteso: quattro servizi, tre `Healthy`, `rs-keyfile-init` e `rs-init` completati con `0`.

- [ ] **Passo 5 — Commit**

---

## Task 6 — `check_stack.py` impara il replica set

**File:**
- Modificare: `tools/check_stack.py`
- Test: `tools/tests/test_check_stack.py`

Lo strumento nato in `feature/01` è «una porta che `feature/02` e `feature/03` devono
attraversare». Attraversarla non basta: questo branch porta decisioni nuove, e una decisione
che nessuno verifica è una buona intenzione. **TDD stretto — il test rosso prima, sempre.**

- [ ] **Passo 1 — Scrivere i test delle quattro regole nuove**

1. **Il keyfile sta in un volume nominato.** Un servizio che monta il keyfile da un percorso
   dell'host è un errore: [ADR-0014](../Decision.md#adr-0014) esiste perché su macOS quel
   montaggio non conserva i permessi. La regola distingue `keyfile:/keyfile` da
   `./keyfile:/keyfile`.
2. **Ogni `mongod` di questo stack dichiara `--replSet` e `--keyFile`.** Un membro senza
   `--keyFile` parte lo stesso e resta fuori dalla replica, silenziosamente.
3. **I servizi one-shot dichiarano `restart: "no"`.** Con `unless-stopped` la catena non
   completa mai, e il sintomo — uno stack che non finisce di partire — non somiglia alla
   causa.
4. **Ogni dipendenza da un one-shot usa `service_completed_successfully`,** ogni dipendenza
   da un `mongod` usa `service_healthy`. Scambiarle è l'errore che rende la catena non
   deterministica: funziona sulla macchina veloce e fallisce in sala.

- [ ] **Passo 2 — Vederli fallire**

Comando: `uv run --directory tools pytest -q`
Atteso: quattro rossi. Un controllo che non si è visto fallire non è un controllo — è la
lezione registrata nel registro alla chiusura di `feature/01`.

- [ ] **Passo 3 — Implementare, minimo**

Funzioni pure che ricevono il documento e restituiscono l'elenco dei problemi, nella forma
già in uso. Attenzione alla distinzione introdotta da
[ADR-0039](../Decision.md#adr-0039): esiste un documento **grezzo** e uno **interpolato**, e
le regole che giudicano ciò che il file promette guardano il primo.

- [ ] **Passo 4 — Verdi, e il file vero passa**

Comando: `make tools-test` poi `make stack-check`
Atteso: tutti verdi, `Stack conformi: 2.`

- [ ] **Passo 5 — Estendere `stack-check` al file nuovo**

Nel `Makefile`, il target passa ora entrambi i file Compose. Verificare che lo stack 01
**non** sia stato rotto dalle regole nuove: le regole 2 e 4 non devono scattare su uno stack
che non ha né replica né catena.

- [ ] **Passo 6 — Commit**

---

## Task 7 — I target del `Makefile`, i dati di demo e `smoke-02`

**File:**
- Modificare: `Makefile`
- Creare: `docker/02-replicaset/init/20-dati-demo.js`, `tools/smoke-replicaset.sh`

- [ ] **Passo 1 — I target, con gli stessi nomi dello stack 01**

`up-02`, `down-02`, `reset-02`, `logs-02`, `seed-02`, `smoke-02`. Stessa forma dei target
`-01`, perché chi ha imparato i primi non deve reimparare i secondi, e sul palco la memoria
muscolare conta. `reset-02` cancella i volumi dei dati — e **non** quello del keyfile, che
rigenerarlo significherebbe far ripartire la fiducia fra i membri da zero senza motivo.

- [ ] **Passo 2 — Il dataset, scritto con `w: "majority"`**

Deterministico e identico a ogni avvio, come per lo stack 01. Qui però il write concern è
parte della lezione: si scrive con `w: "majority"` **e lo si dice**, perché è la prima
differenza tangibile rispetto allo stack 01, dove `w: 1` era tutto ciò che si poteva
chiedere ([ADR-0022](../Decision.md#adr-0022)).

- [ ] **Passo 3 — `smoke-replicaset.sh`: contare, non lanciare**

Lo script **verifica**, non esegue e basta ([ADR-0036](../Decision.md#adr-0036)). Almeno:
il set ha tre membri; c'è esattamente un primario; i due secondari sono in stato `SECONDARY`;
una scrittura con `w: "majority"` torna e si rilegge da un secondario con
`readPreference: secondary`; il conteggio dei documenti e l'impronta corrispondono a quelli
attesi; una connessione **senza credenziali** viene rifiutata — che è il contrario di quanto
`smoke-01` deve dire ad alta voce sullo stack 01, ed è il punto.

- [ ] **Passo 4 — Misurare il ritardo di replica a riposo**

Con lo stack fermo sotto carico nullo, quanto vale il ritardo fra primario e secondari? Il
numero serve alla pagina del Task 9, che senza di esso parlerebbe di «ritardo di replica»
senza mai mostrarne uno. Nuova voce di verifica in [`Sources.md`](../Sources.md).

- [ ] **Passo 5 — Commit**

---

## Task 8 — La demo di failover, costruita sapendo che `docker kill` non è un guasto

**File:**
- Creare: `tools/reset-demo.sh`
- Modificare: `Makefile` (target `failover-02`)

È la scena centrale del talk. [ADR-0034](../Decision.md#adr-0034) la vincola, e il vincolo
è narrativo prima che tecnico.

- [ ] **Passo 1 — Le due scene, distinte**

1. **«Fermo un nodo»** — `docker kill` sul primario. È immediato, riproducibile, ed è quello
   che il pubblico si aspetta. La frase che lo accompagna è «sto spegnendo un nodo», **non**
   «sto simulando un crash»: il container resta fermo, e `restart: unless-stopped` non lo
   rialza. Questo è il punto in cui un ascoltatore attento chiede «ma allora non riparte da
   solo?», e la risposta onesta è più interessante della domanda.
2. **«Il processo muore da sé»** — il nodo si termina con il comando `shutdown`, che è la via
   misurata in cui la politica di riavvio interviene davvero, e il container torna su.

- [ ] **Passo 2 — Cronometrare l'elezione**

Dal `docker kill` al nuovo `PRIMARY`: tre misure, con il comando esatto. Il numero va nel
runbook e nella pagina del Task 9. Serve anche a decidere se la scena regge dal vivo o se va
registrata come riserva.

- [ ] **Passo 3 — Catturare le righe di log dell'elezione**

Con lo stack fermo e i log sotto mano, questo è il momento in cui si salda il debito di
[ADR-0035](../Decision.md#adr-0035): i numeri `id` delle righe di elezione, mai visti su uno
standalone. Salvare l'estratto integrale — il Task 12 lo userà.

- [ ] **Passo 4 — `reset-demo.sh`, debito di `feature/01`**

Riporta uno stack allo stato iniziale fra una prova e l'altra, senza ricostruirlo da zero: è
ciò che serve quando si ripete la stessa demo tre volte in prova generale. Prende lo stack
come argomento, così `feature/03` lo eredita senza riscriverlo.

- [ ] **Passo 5 — La frase per le slide**

«Il gesto con cui tutti simulano un guasto non simula un guasto» va in
[`citazioni-riportare-slide.md`](../citazioni-riportare-slide.md), dove
[ADR-0034](../Decision.md#adr-0034) la manda.

- [ ] **Passo 6 — Commit**

---

## Task 9 — `docs/02-architetture/replica-set.md`

**File:**
- Creare: `docs/02-architetture/replica-set.md`
- Modificare: `docs/README.md` (la riga passa da promessa a collegamento),
  `docs/02-architetture/standalone.md` (il confronto ora è possibile)

La pagina risponde alla domanda che lo stack 01 lascia aperta: **cosa si ottiene** in più, e
a quale prezzo. Indice dovuto dall'indice: topologia, elezioni, read preference, write
concern, ritardo di replica.

- [ ] **Passo 1 — Topologia ed elezioni, con i numeri misurati**

Tre membri, perché il quorum di maggioranza su due non esiste; le priorità e il loro effetto
visibile; il tempo d'elezione misurato al Task 8, non stimato.

- [ ] **Passo 2 — Write concern e read preference, come coppia**

`w: "majority"` e cosa garantisce davvero; `readPreference: secondary` e il prezzo che si
paga — dati che possono essere vecchi di quanto misurato al Task 7. È qui che il ritardo di
replica smette di essere un concetto e diventa un numero.

- [ ] **Passo 3 — Il confronto con l'istanza singola**

[ADR-0032](../Decision.md#adr-0032) rimanda esplicitamente a questo branch il confronto sulla
perdita di dati: adesso c'è un replica set con cui farlo. La pagina dello standalone riceve
il collegamento in entrambe le direzioni.

- [ ] **Passo 4 — Il file Compose commentato**

Riga per riga, con i numeri dei Task 3, 4 e 7 al posto delle stime.

- [ ] **Passo 5 — `make docs-check` e commit**

---

## Task 10 — `docs/03-amministrazione/backup-restore.md`

**File:**
- Creare: `docs/03-amministrazione/backup-restore.md`
- Modificare: `docs/README.md`

La pagina esiste in questo branch e non prima perché `mongodump --oplog` **richiede** un
replica set: su uno standalone non c'è oplog, quindi non c'è backup a caldo coerente
([ADR-0022](../Decision.md#adr-0022)).

- [ ] **Passo 1 — `mongodump` e `mongorestore`, eseguiti**

Comandi completi, con autenticazione, eseguiti sullo stack di questo branch. Niente comandi
riportati da altrove: se sono nella pagina, sono girati.

- [ ] **Passo 2 — `--oplog`: cosa garantisce e cosa no**

La garanzia è di coerenza rispetto a un punto nel tempo **per la durata del dump**, e non è
un backup continuo. I limiti dichiarati dalla fonte primaria vanno riportati per esteso,
compresa la finestra dell'oplog: un restore che pretende un oplog più vecchio della finestra
fallisce, e va mostrato **mentre fallisce**.

- [ ] **Passo 3 — Il restore verificato**

Un backup che nessuno ha mai ripristinato non è un backup. Il restore si esegue su uno stack
pulito e si verifica contando i documenti e confrontando un'impronta, la stessa disciplina di
`smoke-02`.

- [ ] **Passo 4 — Quello che questa pagina non copre**

`mongodump` non è lo strumento per un database grande, e la pagina lo dice invece di lasciarlo
scoprire. La riserva è dichiarata, con la fonte.

- [ ] **Passo 5 — `make docs-check` e commit**

---

## Task 11 — `docs/03-amministrazione/sicurezza-keyfile-x509.md`

**File:**
- Creare: `docs/03-amministrazione/sicurezza-keyfile-x509.md`
- Modificare: `docs/README.md`

- [ ] **Passo 1 — Perché il lab usa il keyfile**

Semplice, offline, riproducibile, e sufficiente a mostrare che l'autenticazione interna
esiste. `--keyFile` implica `--auth` ([ADR-0005](../Decision.md#adr-0005)): il keyfile porta
con sé il controllo degli accessi, e questo va detto perché è controintuitivo.

- [ ] **Passo 2 — Perché MongoDB lo riserva a test e sviluppo**

È la riserva già dichiarata in [ADR-0005](../Decision.md#adr-0005), e va riportata con le
parole della fonte, non parafrasata. Una pagina che insegna a usare il keyfile senza dire a
quali condizioni la documentazione lo ammette insegna male.

- [ ] **Passo 3 — Come si passa a X.509**

Le differenze concrete: cosa cambia nei parametri del server, cosa comporta in termini di
certificati e di rotazione, e cosa succede a un cluster esistente durante la migrazione. Se
qualcosa non è stato eseguito su questo branch, è **marcato come non eseguito** — la regola
di [ADR-0035](../Decision.md#adr-0035) e [ADR-0036](../Decision.md#adr-0036).

- [ ] **Passo 4 — Utenti del cluster e utenti locali a un nodo**

Distinzione che [ADR-0026](../Decision.md#adr-0026) intesta esplicitamente a questa pagina.

- [ ] **Passo 5 — `make docs-check` e commit**

---

## Task 12 — I debiti di `feature/00` e `feature/01` che si saldano qui

**File:**
- Modificare: `docs/02-architetture/trappole-mongodb-in-docker.md`,
  `docs/03-amministrazione/log.md`, `docs/04-mongosh/guida-mongosh.md`

Quattro debiti scritti in chiaro negli ADR. Nessuno è facoltativo: uno di essi ha una
clausola esplicita di non chiusura.

- [ ] **Passo 1 — I numeri `id` delle righe di elezione**

[ADR-0035](../Decision.md#adr-0035): «la sezione sull'elezione resta con un debito scritto in
chiaro, e `feature/02` non può chiudersi senza saldarlo». Le righe catturate al Task 8
entrano in `log.md` citate per `id`, con il testo accanto — la prima serve a ritrovare, la
seconda a capire.

- [ ] **Passo 2 — Le sezioni di `mongosh` marcate «non eseguite qui»**

[ADR-0036](../Decision.md#adr-0036): i comandi di amministrazione di un replica set stanno
nella guida ma sono marcati come non eseguiti. Adesso si eseguono, si correggono se l'output
smentisce il testo, e la marcatura si toglie **solo** per ciò che è stato davvero eseguito.
Quello che riguarda lo sharded cluster resta marcato: è dovuto a `feature/03`.

- [ ] **Passo 3 — Le due trappole nuove**

[ADR-0033](../Decision.md#adr-0033) le nomina: **permessi del keyfile** e **scoperta della
topologia**. Contratto della pagina: il **sintomo per titolo**, perché chi cerca ha in mano
il sintomo, non la causa.

- «`mongod` non parte e dice che il keyfile è "too open"» — con il messaggio esatto
  osservato al Task 2 e il rimedio del volume nominato.
- «Mi connetto al replica set e il driver prova a raggiungere un host che non esiste» — il
  driver riceve dalla topologia i nomi di servizio Compose, che fuori da quella rete non
  risolvono. Sintomo, causa, e le due vie d'uscita.

- [ ] **Passo 4 — `make docs-check` e commit**

---

## Task 13 — `docs/05-talk/registrazioni/` e le prime registrazioni

**File:**
- Creare: `docs/05-talk/registrazioni/README.md`
- Modificare: `docs/README.md`

Il piano di progetto affianca a questo branch le **prime registrazioni**, e non è un caso:
la demo di failover è la prima che valga la pena filmare, perché è la prima che possa
fallire in modo interessante.

- [ ] **Passo 1 — L'indice**

Una riga per filmato: cosa mostra, quanto dura, a quale momento del copione corrisponde, e
il collegamento. I filmati stanno sul canale del relatore, con **copia locale obbligatoria**
([ADR-0016](../Decision.md#adr-0016)): la connettività in sala non è garantita, e un piano B
che richiede rete non è un piano B.

- [ ] **Passo 2 — Registrare failover ed elezione**

La scena del Task 8, nelle due varianti. Girata dopo che i tempi sono stati misurati, così la
registrazione mostra la scena vera e non una prova.

- [ ] **Passo 3 — Verificare con `preflight`**

[`tools/preflight.sh`](../../tools/preflight.sh) controlla già la cartella dei filmati e il
suo contenuto: oggi è un avviso, il **18 settembre diventa errore bloccante**. Con i primi
filmati in cartella il controllo passa da avviso a verde, ed è la prima volta che accade.

Comando: `make preflight`
Atteso: l'avviso sui filmati sparisce.

- [ ] **Passo 4 — Commit**

---

## Task 14 — ADR, fonti e chiusura del branch

**File:**
- Modificare: `docs/Decision.md`, `docs/Sources.md`,
  `docs/registro-operativo-sviluppo.md`, `docs/citazioni-riportare-slide.md`

- [ ] **Passo 1 — Gli ADR del branch**

Oltre a quello del Task 1: la scelta sull'healthcheck del Task 5, le priorità dei membri del
Task 4, e qualunque decisione presa lungo la strada che un lettore futuro troverebbe
arbitraria. Un ADR **si supera, non si riscrive**.

- [ ] **Passo 2 — Le fonti**

Ogni voce nuova con la sua `- **Usata da:**` allineata. `make docs-check` non lascia scelta:
nessuna fonte orfana, nessun ADR senza fonti.

- [ ] **Passo 3 — Il registro operativo**

La voce del branch con le note di metodo. Quelle che nascono da un errore valgono più delle
altre.

- [ ] **Passo 4 — Il consuntivo, contato all'ultimo commit**

Nota di metodo 37 del registro: quando un numero descrive il branch e vive dentro il branch,
si calcola includendo il commit che lo introduce. È già stato sbagliato due volte.

- [ ] **Passo 5 — `make preflight`, `make docs-check`, `make stack-check`, `make tools-test`**

Tutti e quattro verdi, con gli stack **fermi** e poi con lo stack 02 avviato.

- [ ] **Passo 6 — PR #3 verso `develop`**

La PR si apre e si fa revisionare. **Non** si chiude con `git flow feature finish`: è
successo con `feature/00-fondamenta`, i commit sono finiti su `develop` senza passare da una
revisione, e la PR #1 è stata chiusa senza merge perché non aveva più niente da unire.

---

## Criterio di completamento

Il branch è finito quando:

1. `make up-02` porta da zero a un replica set con un primario e due secondari, **con la
   rete disattivata**, senza interventi manuali e senza `sleep`.
2. `make smoke-02` verifica dal vivo ciò che il file dichiara, e dice a voce alta che senza
   credenziali non si entra.
3. La demo di failover è eseguibile, cronometrata, e accompagnata dalla frase giusta
   ([ADR-0034](../Decision.md#adr-0034)).
4. `make stack-check` esce `0` su **entrambi** gli stack, e ogni regola nuova ha il proprio
   test.
5. Le quattro voci assegnate a `feature/02` nell'indice [`docs/README.md`](../README.md)
   esistono, e la colonna «Branch» diventa un collegamento.
6. I quattro debiti del Task 12 sono saldati, o esplicitamente rinviati con il motivo scritto
   — con l'eccezione di [ADR-0035](../Decision.md#adr-0035), che **non ammette** rinvio.
7. `make docs-check` esce `0`.
8. Almeno una registrazione di riserva esiste in locale e `make preflight` non avvisa più.

Se il calendario stringe, i task rinviabili in ordine di rinuncia sono **11**
(keyfile e X.509: interessa il pubblico, non la demo — ma la riserva di
[ADR-0005](../Decision.md#adr-0005) va comunque scritta da qualche parte), poi **10**
(backup e restore, che `feature/04` toccherà di nuovo dal lato applicativo). **Non** sono
rinviabili il Task 1, perché tutto il resto ne dipende; il Task 6, perché è la porta che
`feature/03` deve attraversare e nasce adesso o non nasce; il Task 8, che è la scena del
talk; e il Passo 1 del Task 12, che ha una clausola di non chiusura in un ADR.

---

## Nota di calendario

Il piano di progetto assegna a questo branch quattro giorni — da lunedì 31 agosto a giovedì
3 settembre — **più** le prime registrazioni. Rispetto a `feature/01`, che ne aveva due
nominali e ne è costati di più, il dimensionamento è più onesto: quattro giorni per
quattordici task restano stretti, ma la differenza è che tre delle quattro pagine hanno
l'indice già scritto nell'indice generale e non vanno progettate da zero.

Il rischio vero non è la documentazione: è il Task 1. Se le due strade dell'inizializzazione
si rivelassero entrambe percorribili con costi simili, la scelta è del Product Owner e va
fatta **il primo giorno**, perché i Task da 2 a 5 non possono iniziare prima. Se invece
nessuna delle due funzionasse come descritto, siamo davanti a una scoperta che vale un ADR e
probabilmente una giornata.

Il secondo rischio è di scena e non di codice. Le registrazioni vanno fatte quando la demo è
stabile, non quando il branch è finito: se scivolano oltre giovedì, scivolano dentro
`feature/04`, dove non c'è posto. Meglio girarle imperfette mercoledì che perfette mai.
