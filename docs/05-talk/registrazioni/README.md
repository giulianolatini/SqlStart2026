# Registrazioni di riserva

Questa cartella è il piano B del talk. Serve quando la demo dal vivo non parte, quando la sala non
ha rete, quando un container decide di fare il difficile davanti a cento persone — e serve che
funzioni **senza rete e senza installare niente** ([ADR-0016](../../Decision.md#adr-0016),
[ADR-0050](../../Decision.md#adr-0050)).

Le registrazioni sono di due specie, e non sono intercambiabili.

| | che cos'è | dove sta | chi la produce |
|---|---|---|---|
| **Filmato** (`.mp4`) | lo schermo e la voce di chi parla | canale YouTube del relatore, **più** copia locale in `~/SqlStart2026-registrazioni` | il relatore |
| **Registrazione di terminale** (`.cast`) | il tracciato di ciò che il terminale ha fatto, con i tempi | qui, dentro il repository | si produce eseguendo |

Un filmato mostra una persona che spiega; una registrazione di terminale mostra una macchina che
lavora. In sala servono tutt'e due, per motivi diversi: il filmato copre il caso «la demo non
parte», la registrazione di terminale copre il caso «la demo parte ma stiamo finendo il tempo».

---

<a id="registrazioni-di-terminale"></a>
## Le registrazioni di terminale, che ci sono

Quattordici scene: quattro del Blocco 2 — il replica set — cinque dell'applicazione `mongolab`
sullo stesso stack, e cinque del Blocco 3, lo sharded cluster. Nessuna è montata: ognuna è **una**
esecuzione intera, con i tempi che ha avuto.

Dodici stanno in trentasei kilobyte. Le altre due sono l'applicazione sotto carico e pesano sei
megabyte: il perché è scritto più sotto, e non è un difetto da correggere.

### Blocco 2 — il replica set

Misurate sullo stack `docker/02-replicaset`, con i tre membri sani prima di ciascuna
([V-045](../../Sources.md#v-045)).

| # | File | Che cosa mostra | Durata | Il numero che porta | Momento |
|---:|---|---|---:|---|---|
| 1 | [`01-smoke-replica-set.cast`](01-smoke-replica-set.cast) | la prova completa dello stack: keyfile, autenticazione, replica, log | 16,9 s | `Superati: 42 · Errori: 0` | apertura del blocco sul replica set — «funziona, e lo dimostro» |
| 2 | [`02-failover-docker-kill.cast`](02-failover-docker-kill.cast) | `docker kill` sul primario: nessun preavviso, il timeout scade | 17,2 s | elezione in **8617 ms**; `exited`, `RestartCount=0`, `ExitCode=137` | la scena principale del blocco |
| 3 | [`03-failover-terminazione-pulita.cast`](03-failover-terminazione-pulita.cast) | il primario esce da sé con `shutdownServer()`: cede il ruolo e lo dice | 25,1 s | elezione in **1039 ms**; `running`, `RestartCount=1`, `ExitCode=0` | subito dopo la 2, come confronto |
| 4 | [`04-maggioranza-persa.cast`](04-maggioranza-persa.cast) | due membri su tre giù: il superstite è vivo, sano, e smette di scrivere | 15,6 s | `SECONDARY` dopo **8634 ms** | la risposta a «e a quanti guasti regge?» |

Le scene 2 e 3 vanno **una dopo l'altra**, perché il punto non è nessuna delle due: è che il gesto
brutale costa dieci secondi e quello educato uno, cioè il contrario di quello che il pubblico si
aspetta ([ADR-0034](../../Decision.md#adr-0034), [ADR-0044](../../Decision.md#adr-0044)).

### Blocco 2 — l'applicazione `mongolab`

Cinque scene girate alla fine di `feature/04`, sullo stesso stack `docker/02-replicaset` e con i
tre membri riportati sani prima di ciascuna. I numeri dei file proseguono la serie perché sono
state prodotte dopo; nella scaletta stanno **dentro** il Blocco 2, subito dopo le quattro di sopra
([V-089](../../Sources.md#v-089)).

Tutte e cinque sono girate con `--sink plain` e **senza** `--step`, cioè con lo stesso codice che
gira dal vivo: la modalità da palco cambia una funzione di attesa, non la scena
([ADR-0098](../../Decision.md#adr-0098)). È la proprietà che rende queste registrazioni una copia
e non una ricostruzione.

| # | File | Che cosa mostra | Durata | Il numero che porta | Momento |
|---:|---|---|---:|---|---|
| 10 | [`10-app-fotografia-dello-stack.cast`](10-app-fotografia-dello-stack.cast) | `mongolab stats`: topologia, versione, **dettaglio per collezione**, totale del database e distribuzione | 2,3 s | `mongod 7.0.40` · tre membri e un primario · `ordini` con **50 000** documenti, e `lab` con lo stesso totale perché lo stack è pulito | apertura dell'Atto I — «che cosa c'è, prima che lo rompa» |
| 11 | [`11-app-cronaca-dell-elezione.cast`](11-app-cronaca-dell-elezione.cast) | `mongolab watch`: l'elezione **senza carico intorno**, una riga per transizione | 42,5 s | primario perso a `26.047`, `mongo-rs-2` eletto a `36.082`: **10 035 ms** | l'Atto I quando la domanda è «e il driver come fa a saperlo?» |
| 12 | [`12-app-failover-e-i-due-numeri.cast`](12-app-failover-e-i-due-numeri.cast) | la scena centrale: carico attivo, `SIGKILL` sul primario, l'elezione, il bilancio | 53,3 s | interruzione **10 019 ms** · **0 scritture perse** · 31 952 confermate contro 31 955 ritrovate | l'Atto II, ed è la ragione per cui l'applicazione esiste |
| 13 | [`13-app-backup-a-caldo.cast`](13-app-backup-a-caldo.cast) | `mongodump --readPreference=secondary --oplog` mentre il carico continua a scrivere | 11,3 s | ritmo **506/s** prima, **516/s** durante: **calo −1,9 %**, cioè il ritmo è salito | l'Atto III — «si fa a caldo, e questo è quanto costa» |
| 14 | [`14-app-restore-e-i-due-conteggi.cast`](14-app-restore-e-i-due-conteggi.cast) | la copia rientra in `lab_ripristinato`, e i due conteggi **non** coincidono | 3,7 s | 5 386 all'origine · 5 295 nella copia · **differenza 91** | subito dopo la 13: la finestra che il dump non copre |

Le scene 13 e 14 vanno **una dopo l'altra** e in quest'ordine, perché la 14 conta ciò che la 13 ha
copiato: i 146 documenti di differenza sono quelli scritti *mentre* il dump era in corso, e stanno
nell'oplog che `mongorestore` senza `--oplogReplay` non riapplica. Il numero della 13 — un calo
dell'1,3 % — e il numero della 14 sono lo stesso fatto visto dai due lati: il backup a caldo costa
pochissimo in ritmo e lascia una finestra, e la finestra è ciò che si paga.

**Nella 12 le elezioni sono due, e la seconda non è nel copione.** La prima è quella che la scena
provoca; la seconda avviene da sé a `40:45`, quando `mongo-rs-1` rientra e si riprende il ruolo —
otto secondi dopo essere tornato secondario. Si legge dagli `ERRORE NotPrimaryError` seguiti da
`RITENTO tentativo 2 dopo 50 ms`: sono i tentativi automatici del driver che assorbono
l'avvicendamento, e sono la ragione per cui le scritture perse restano zero anche lì. Non era
previsto, non è stato tolto, ed è la parte della registrazione che risponde meglio alla domanda
«ma allora a che serve `retryWrites`?».

Da leggere accanto: la fase `durante` dichiara **13 786 scritture, tutte confermate**, con un p95
di 49,5 ms — *più basso* di quello della fase precedente. Non è un miglioramento: quella fase dura
venticinque secondi, i primi dieci non ne contengono nemmeno una, e i quindici che restano girano
contro un primario appena eletto e scarico. È il tipo di numero che una registrazione mostra e una
tabella nasconde.

#### Quanto pesano, e perché

| | scene | byte |
|---|---:|---:|
| gli stack (1–9) | 9 | 31 K |
| l'applicazione (10, 11, 14) | 3 | 4,8 K |
| l'applicazione sotto carico (12, 13) | 2 | **6,3 M** |

Due scene su quattordici fanno il 99,9 % della cartella, e non è un difetto della registrazione: è
il carico. `PlainSink` scrive **una riga per evento** e non taglia niente — è ciò che lo rende
adatto a una riserva, perché ciò che il pubblico vede dal vivo è esattamente questo — e una scena
che confeziona trentaduemila scritture produce sessantaquattromila righe. Nel pacchetto di git
scendono a ~640 K, perché sono righe quasi identiche.

La scorciatoia sarebbe accorciare il copione. Non è stata presa, ed è
[ADR-0116](../../Decision.md#adr-0116): una riserva che dura la metà della scena che sostituisce
non è la riserva di quella scena.

### Blocco 3 — lo sharded cluster

Misurate sullo stack `docker/03-sharded` ([V-068](../../Sources.md#v-068)). Le prime quattro nel
profilo `palco` — un membro per shard, quello che entra in un portatile; l'ultima nel profilo
`completo`, tre membri per insieme ([ADR-0010](../../Decision.md#adr-0010)).

| # | File | Che cosa mostra | Durata | Il numero che porta | Momento |
|---:|---|---|---:|---|---|
| 5 | [`05-avvio-sharded.cast`](05-avvio-sharded.cast) | undici servizi che si accendono nell'ordine giusto: keyfile, config server, i due shard, il router, `addShard`, i dati | 22,9 s | la catena finisce con `Container sh-up-03 Healthy` | apertura del blocco — «un comando, e c'è un cluster» |
| 6 | [`06-stato-sharded.cast`](06-stato-sharded.cast) | `sh.status()` per intero, e sotto le quattro righe che contano davvero | 6,5 s | 2 shard · `lab.ordini` in **4 chunk**, due per shard · balancer abilitato · 1 router | subito dopo l'avvio: «che cosa mi sta dicendo tutto questo?» |
| 7 | [`07-distribuzione-sharded.cast`](07-distribuzione-sharded.cast) | gli stessi documenti contati dal router e poi shard per shard | 4,0 s | **9860 + 10140 = 20000**, cioè 49,3 % e 50,7 % | il cuore del blocco: partizionata, non copiata |
| 8 | [`08-guasto-shard-palco.cast`](08-guasto-shard-palco.cast) | si ferma l'unico membro di uno shard: metà cluster risponde, l'altra metà aspetta | 40,1 s | lettura sullo shard vivo in **1 s**; `FailedToSatisfyReadPreference` dopo **15 s** e **16 s**; ritorno in **3 s** | la risposta a «e se ne cade uno?» |
| 9 | [`09-failover-membro-shard.cast`](09-failover-membro-shard.cast) | lo stesso guasto con tre membri per shard: lo shard elegge, e il router se ne accorge da solo | 12,3 s | totale ancora **20000**, in **0 s**; primario da `shard1a` a `shard1b`; ritorno in **2 s** | subito dopo la 8, come confronto |

Le scene 8 e 9 sono **lo stesso comando** — `make guasto-03` — eseguito in due profili diversi, e
vanno una dopo l'altra per la stessa ragione per cui vanno insieme la 2 e la 3: il punto non è
nessuna delle due, è la differenza fra le due. Con un membro per shard il router aspetta quindici
secondi e poi dichiara che per `shard1rs` non trova un primario; con tre membri lo stesso guasto
quasi non si vede, perché dentro lo shard l'elezione è già avvenuta. La ridondanza sta **dentro**
ogni shard, e fra shard non c'è: nessun altro nodo tiene una copia di ciò che teneva quello caduto.

La scena 8 mostra anche il limite del profilo `palco`, e lo mostra senza bisogno di dirlo: un membro
per shard sta in un portatile e non regge un guasto. Dal palco è più onesto farlo vedere che
nasconderlo — e la 9 esiste per aggiungere che la differenza è di configurazione, non di prodotto.

### Come si riproducono

Senza installare niente, con i tempi originali:

```bash
python3 tools/registra-terminale.py --riproduci \
  docs/05-talk/registrazioni/02-failover-docker-kill.cast
```

I tempi si rispettano di proposito: un failover che scorre tutto insieme non racconta niente,
perché la scena *è* l'attesa. Vale doppio per la scena 8, dove i quindici secondi prima
dell'errore **sono** la risposta alla domanda. Per le prove c'è `--velocita 10`, che in sala non si
usa.

Chi ha `asciinema` installato può usare quello — il formato è il suo, versione 2 — ma non serve, ed
è deliberato: un piano B che richiede un `brew install` non è un piano B.

Una precisazione da conoscere prima di provarci in sala: la riproduzione ha bisogno di un terminale
vero. Dentro una pipe o in un editor le sequenze di colore diventano caratteri e lo schermo si
sporca.

### Come si rifanno

#### Il replica set

Prima di ogni scena i tre membri devono essere sani, altrimenti si registra un'altra cosa:

```bash
./tools/reset-demo.sh 02          # e si aspetta che dica «riportato allo stato di partenza»

python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/02-failover-docker-kill.cast \
  --titolo "feature/02 — Failover: docker kill sul primario (~10 s)" \
  -- make failover-02
```

Poi di nuovo `reset-demo.sh 02` prima della successiva. Le quattro scene sono state girate in questo
ordine — smoke, `docker kill`, terminazione pulita, maggioranza persa — con un ripristino fra
ciascuna.

#### Lo sharded cluster

L'avvio si registra da fermo, e con il renderer testuale di Compose:

```bash
make reset-03                     # ferma lo stack e cancella i dati: l'avvio deve creare i volumi

COMPOSE_PROGRESS=plain python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/05-avvio-sharded.cast \
  --titolo "feature/03 — Lo sharded cluster si accende con un comando (profilo palco)" \
  -- make up-03
```

`COMPOSE_PROGRESS=plain` non è un dettaglio estetico. Il renderer predefinito ridisegna una tabella
animata decine di volte al secondo: lo stesso `up`, sullo stesso stack e nello stesso stato, pesa
**134 861 byte in 205 eventi** con l'animazione e **3 050 byte in 28 eventi** senza — quarantaquattro
volte meno, e per giunta leggibile, perché in `plain` ogni container scrive la propria riga e
l'ordine della catena si vede scorrere ([V-068](../../Sources.md#v-068)).

Le tre scene successive si registrano a cluster acceso, una dopo l'altra e senza ripristini in
mezzo: non toccano i dati, e `make guasto-03` rimette in piedi da sé il nodo che ha fermato.

```bash
python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/06-stato-sharded.cast \
  --titolo "feature/03 — sh.status(): il cluster come si presenta" \
  -- make stato-03

python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/07-distribuzione-sharded.cast \
  --titolo "feature/03 — Dove stanno davvero i ventimila documenti" \
  -- make distribuzione-03

python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/08-guasto-shard-palco.cast \
  --titolo "feature/03 — Cade uno shard: metà cluster risponde, l'altra aspetta (profilo palco)" \
  -- make guasto-03
```

La nona chiede il profilo `completo`, che non è solo una variabile: in `docker/03-sharded/.env` vanno
scambiate le tre righe `MEMBRI_*`, commentando quelle a un membro e togliendo il commento a quelle a
tre. Poi `make reset-03`, `PROFILO=completo make up-03`, e infine:

```bash
python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/09-failover-membro-shard.cast \
  --titolo "feature/03 — Cade il primario di uno shard, e lo shard elegge (profilo completo)" \
  -- make guasto-03 PROFILO=completo
```

Finito, il `.env` va rimesso com'era. Quel file non sta nel repository, non c'è controllo che se ne
accorga, e chi lo lascia a tre membri si ritrova il profilo `palco` che non parte più.

#### L'applicazione

Le cinque scene di `mongolab` girano contro lo stesso stack `docker/02-replicaset`, con
`./tools/reset-demo.sh 02` prima di ciascuna. Due particolari le distinguono dalle altre, e sono
tutt'e due trappole.

**`make -s`, non `make`.** `make` fa l'eco della ricetta prima di eseguirla, e l'eco comincia
esattamente come il comando che l'applicazione annuncia: `docker compose …`. Con la regia accesa —
qui sotto — quell'eco viene **eseguita**, e la scena riparte da capo dentro se stessa. `-s` toglie
l'eco, e la registrazione perde una riga che al pubblico non serviva.

```bash
./tools/reset-demo.sh 02

python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/10-app-fotografia-dello-stack.cast \
  --titolo "feature/04 — mongolab stats: la fotografia del replica set (Blocco 2, Atto I)" \
  -- make app-stats TARGET=rs
```

**La seconda finestra.** La scena 12 gira l'applicazione *dentro* la rete Compose, dove vede la
topologia ma non ha il socket del demone: annuncia il comando che uccide il primario e si ferma su
un `input()` finché qualcuno non l'ha dato altrove. Dal palco quel qualcuno è una persona con un
secondo terminale aperto; per registrare dev'essere lo strumento stesso, ed è `--regia`
([ADR-0115](../../Decision.md#adr-0115)):

```bash
python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/12-app-failover-e-i-due-numeri.cast \
  --titolo "feature/04 — mongolab demo failover: il primario cade sotto carico (Blocco 2, Atto II)" \
  --regia "docker compose " \
  -- make -s app-demo TARGET=rs ARGS="--sink plain"
```

Il prefisso è un argomento e non un predefinito nascosto: la riga di comando dichiara che cosa lo
strumento è autorizzato a eseguire, e chi rilegge la ricetta lo legge lì. Il confronto ignora gli
spazi ai due lati: l'applicazione annuncia il comando **rientrato di due spazi**, per staccarlo dal
testo che lo introduce, e un prefisso ancorato alla colonna zero non lo troverebbe mai. A sinistra
possono esserci spazi, non parole. L'esito del comando finisce
su `stderr` di chi registra — `regia: … · uscita 0` — e **non** nel `.cast`, dove va solo ciò che il
pubblico vedrebbe nella finestra di sinistra.

**Se il comando di regia fallisce, la registrazione si ferma lì**
([ADR-0117](../../Decision.md#adr-0117)): niente Invio, la scena viene abbattuta e lo strumento esce
con **125**, stampando su `stderr` il codice e l'uscita del comando. Il `.cast` parziale resta sul
disco, e la sua interruzione è la prova di ciò che è successo. Il motivo è che la scena aspetta la
conferma di un guasto: un Invio mandato dopo un `docker compose stop` fallito produrrebbe una
registrazione in cui il primario non cade mai, con zero millisecondi di interruzione e zero
scritture perse — un failover perfetto, e nessuno che riguarda il `.cast` può accorgersene. Quando
capita: si legge perché il comando è fallito, si rimette a posto lo stack con
`./tools/reset-demo.sh 02`, e si rilancia.

La scena 11 ha lo stesso bisogno e non passa dalla regia: `watch` non annuncia niente, sta solo a
guardare. Lì il guasto si dà da fuori, con uno script che aspetta dieci secondi, ferma `mongo-rs-1`,
ne aspetta venti e lo riavvia, mentre la registrazione è già partita.

Le scene 13 e 14 girano **dall'host** e in quest'ordine, perché la 14 conta ciò che la 13 ha
copiato. Il nome della collezione che la 13 stampa va copiato nel `--collection` della 14: lo genera
il carico, e cambia a ogni corsa.

```bash
uv run --directory app mongolab demo backup-live --target rs --sink plain

uv run --directory app mongolab demo restore --target rs --sink plain \
  --from /tmp/mongolab-backup --collection carico-20260904-184403
```

#### E poi si riproduce, prima di dichiararla buona

Una registrazione non è buona perché il comando è finito bene: è buona se, **riprodotta**, mostra
quello che deve mostrare. Ognuna delle quattordici è stata riaperta con `--riproduci` per intero
prima di entrare in questa pagina ([ADR-0055](../../Decision.md#adr-0055)). È lì che si scopre quello che
durante l'esecuzione non si vede — una scena che *afferma* un'elezione invece di mostrarla, un
titolo che dice un profilo e un contenuto che ne dice un altro.

Il controllo è stato anche automatico, e alla fine di `feature/04` su tutte e quattordici: la
riproduzione è stata eseguita dentro uno pseudo-terminale e il testo raccolto confrontato **byte per
byte** con l'originale. Tutte e quattordici coincidono, e in tutte il titolo compare
([V-089](../../Sources.md#v-089)).

**Una correzione a quello che questa pagina diceva prima.** La regola scritta qui — «lo
pseudo-terminale traduce ogni `\n` in `\r\n`, quindi un `\r\n` registrato torna indietro come
`\r\r\n` e va normalizzato» — è vera e insufficiente. Sulle due registrazioni lunghe compaiono anche
`\r\r\r\n`: il ritorno a capo si accumula quando la stessa riga ripassa per la traduzione. Con la
regola vecchia il confronto falliva **a 66 354 byte**, dopo che due terzi del file avevano coinciso
— cioè nel modo in cui fallirebbe una registrazione davvero rotta. La regola buona è comprimere
`\r+\n` in `\n` da **tutt'e due** le parti, l'originale compreso, e poi confrontare.

**I numeri di una registrazione non sono la misura.** Ogni scena è **una** esecuzione, girata di
seguito alle altre. Le misure del branch stanno in [V-029](../../Sources.md#v-029) e
[V-031](../../Sources.md#v-031), che hanno tre giri per scena e le mediane. La scena 3 qui sopra ne
è la prova: 1039 ms, contro i 574, 480 e 486 di V-029 — stesso strumento, stesso metodo, il doppio
del tempo, perché la macchina aveva appena fatto altre tre scene. Il singolo numero balla, il
rapporto fra le due scene no. Vale identico per i quindici secondi della scena 8: quello che regge
non è il numero, è che da una parte si aspetta e dall'altra no.

---

<a id="filmati"></a>
## I filmati

I filmati servono — i primi quattro del Blocco 2, gli ultimi due del Blocco 3, in ordine di
importanza dentro ciascun blocco:

| # | Che cosa filmare | Corrisponde a | Come si ottiene | Perché serve |
|---:|---|---|---|---|
| 1 | il failover con `docker kill` | scena 2 | `make filmati` | è la scena del talk. Se salta questa, salta il blocco |
| 2 | le due varianti a confronto, `kill` e terminazione | scene 2 e 3 | `make filmati` | il confronto è il punto, non le due scene separate |
| 3 | la maggioranza persa | scena 4 | `make filmati` | risponde alla domanda che il pubblico fa sempre |
| 4 | `make up-02` da zero, con la rete disattivata | — | `make filmato`, dal vivo | dimostra che il lab è offline davvero, e apre il talk |
| 5 | il guasto di uno shard nei due profili | scene 8 e 9 | `make filmati` | è la scena del Blocco 3, e dal vivo costa due stack e uno scambio di `.env` |
| 6 | il Blocco 3 per intero: avvio, `sh.status()`, distribuzione | scene 5, 6 e 7 | `make filmati` | se il cluster non parte in sala non c'è modo di raccontarlo a voce |

Cinque su sei escono dalle registrazioni di terminale già archiviate. Il quarto no, e il motivo è
istruttivo: **la sua prova sta fuori dal terminale.** Un `.cast` contiene quello che il terminale
ha scritto, non l'icona del Wi-Fi spenta nella barra dei menu — e quella icona *è* la
dimostrazione. Va girato dal vivo.

### Due strade, e non sono intercambiabili

C'è più di un modo di ottenere un `.mp4`, e sceglierlo male costa un pomeriggio o una bugia.

**`make filmati` fabbrica il filmato dalla registrazione.** Le scene sono già state eseguite
davvero; [`agg`](#agg) le ridisegna fotogramma per fotogramma rispettando gli intervalli originali,
e `ffmpeg` ne fa un `.mp4`. Dura secondi, non tocca nessuno stack, e il filmato che ne esce mostra
**la stessa esecuzione** che il `.cast` conserva — non una sua imitazione rifatta a memoria.

**`make filmato` registra lo schermo.** Serve quando la scena vive fuori dal terminale: una
finestra di Compass, un grafico che si muove, la barra dei menu, la voce di chi parla.

Detto in breve: se la scena sta tutta dentro il terminale ed esiste già come `.cast`, si fabbrica;
altrimenti si gira.

### Il comando che fabbrica

```bash
make filmati                                        # tutti: cinque montaggi e otto scene singole
make filmati NOME=03-maggioranza-persa-muto         # uno solo
make filmati-elenco                                 # che cosa uscirebbe, senza produrlo
```

Lo strumento è
[`tools/filmati-da-registrazioni.sh`](../../../tools/filmati-da-registrazioni.sh). I file escono in
`~/SqlStart2026-registrazioni`, la stessa cartella che `make preflight` conta. Escono **muti**, e
non è una rinuncia: un `.cast` non ha voce da restituire, e il muto è esattamente quello che va
dentro le slide (vedi sotto).

Oltre ai cinque montaggi produce le otto scene singole, con il prefisso `scena-`, per chi in slide
le vuole separate invece che di fila.

#### Che cosa dichiara, e perché conta invece di fidarsi

A ogni filmato lo strumento affianca la somma delle scene che lo compongono, e se le due non
coincidono entro mezzo secondo **si ferma con un errore**:

```
  ✓ 05-guasto-shard-nei-due-profili-muto.mp4      56.4 s (attesi 56.4) · 7447730 byte
```

Non è zelo. Un filmato più corto della scena che sostituisce *sembra riuscito* — si apre, scorre,
si vede — e mente sull'unica cosa per cui esiste. È successo due volte mentre lo strumento veniva
scritto, per due cause diverse e nessuna delle due visibile a occhio ([V-107](../../Sources.md#v-107)):

* il limite di inattività di `agg` vale **cinque secondi** se non glielo si dice, e comprime a
  cinque ogni pausa più lunga: la scena 8, che dura 40,1 s, ne usciva 21,3;
* i `.mp4` nati da una GIF hanno fotogrammi a durata variabile, e il montaggio che li incolla senza
  ricodificare scarta i secondi che non sa incastrare: il filmato 05 usciva 47,1 s invece di 52,5.

Tutt'e due contraddicono lo stesso principio, che vale qui quanto vale per le registrazioni: i
tempi si rispettano di proposito, perché la scena **è** l'attesa. Una riserva che dura la metà
della scena che sostituisce non è la riserva di quella scena ([ADR-0116](../../Decision.md#adr-0116)).

<a id="agg"></a>
#### `agg`, la seconda installazione

```bash
brew install agg
```

[`agg`](../../Sources.md#s-080) — *asciinema gif generator* — disegna un `.cast` in una GIF animata.
È un solo eseguibile, senza dipendenze di esecuzione.

Insieme a `ffmpeg` sono **le due sole installazioni che questo repository chiede**, e vanno lette
per quello che sono: servono a *fabbricare* le riserve, non a usarle. Per eseguire il lab non
servono; per riprodurre una registrazione in sala nemmeno — quello resta
`python3 tools/registra-terminale.py --riproduci`, che non chiede niente, ed è deliberato: un piano
B che richiede un `brew install` non è un piano B.

### Il comando che registra

Lo strumento è [`tools/registra-schermo.sh`](../../../tools/registra-schermo.sh), e la riga da
imparare è una sola:

```bash
make filmato NOME=02-failover-docker-kill-muto AUDIO=no   # la passata muta
make filmato NOME=02-failover-docker-kill                 # la passata parlata
```

Il file esce come `<NOME>.mp4` in `~/SqlStart2026-registrazioni` — la stessa cartella che
`make preflight` conta, e che si sposta con `DEMO_VIDEOS_DIR`. Senza `DURATA` si registra finché
non si preme **`q`** nella finestra del terminale; con `DURATA=120` si ferma da sé dopo due minuti,
che è comodo quando le mani servono altrove. Alla fine lo strumento rilegge il file e dichiara che
cosa contiene davvero: dimensioni, secondi, byte e **quante tracce audio**. Se si è chiesta la voce
e la traccia non c'è, esce con errore invece di dire «fatto».

Due nomi e non uno, nell'esempio qui sopra, perché **una registrazione non si sovrascrive**: lo
strumento rifiuta un nome già occupato, e la passata muta va conservata comunque (vedi sotto).

> **La prima volta chiede due permessi, e uno riavvia il terminale.** macOS domanda
> «Registrazione schermo» e «Microfono» alla prima corsa; concedere il secondo **fa ripartire
> l'applicazione del terminale**, misurato su iTerm. È un costo da pagare una volta sola, e si paga
> **adesso**: la sera prima del talk è il momento sbagliato per incontrare una finestra di dialogo.
> Serve anche `ffmpeg` (`brew install ffmpeg`): è una delle due installazioni che questo repository
> chiede, insieme ad [`agg`](#agg), e nessuna delle due serve per eseguire il lab.

### Le due passate, e perché la muta si tiene

Si gira **prima il muto**, e lo si guarda. Una elezione dura i secondi che dura, non quelli che ci
si ricorda: vedere la scena prima di commentarla è ciò che permette di raccontarla: si sa dove
stanno le pause, che cosa compare mentre si parla, e quando conviene tacere. Poi si rigira la stessa
scena parlandoci sopra.

Il muto non è uno scarto della lavorazione: **è il filmato da mettere dentro la presentazione**,
dove una voce registrata che si sovrappone a quella di chi parla dal vivo è un difetto e non un di
più. Le due passate producono due file che servono a due cose diverse — quello parlato va su
YouTube, quello muto va nelle slide — ed è il motivo per cui `AUDIO=no` esiste come opzione e non
come ripiego.

### Procedura, quando si gira

1. `./tools/reset-demo.sh 02` — o `03`, secondo il blocco — e si aspetta l'impronta del dataset.
2. Un terminale a 100×30, come le registrazioni di terminale, così le due specie di riserva
   mostrano la stessa cosa.
3. `make filmato NOME=<scena>-muto AUDIO=no`, si esegue la scena, si preme `q`. Si riguarda.
4. `make filmato NOME=<scena>`, si rifà la stessa scena parlandoci sopra, si preme `q`.
5. Il file parlato va sul canale YouTube del relatore **e** resta in `~/SqlStart2026-registrazioni`,
   con lo stesso nome della scena corrispondente e l'estensione `.mp4`.
6. `make preflight`: l'avviso sui filmati diventa `filmati locali disponibili: N`.
7. Il collegamento a YouTube torna in questa pagina, nella colonna che oggi non c'è.

Le tre righe di rumore che `ffmpeg` stampa a ogni corsa — `NSKVONotifying_AVCaptureScreenInput`,
`Configuration of video device failed` e `not enough frames to estimate rate` — sono attese e non
sono guasti: la ragione di ognuna sta nei commenti dello strumento, misurata in
[V-106](../../Sources.md#v-106).

---

## Cosa questa cartella non dice

- **Non contiene la scaletta.** Il documento unico del talk — copione, tempi, piani di ripiego,
  criteri di rinuncia — è `05-talk/runbook-demo.md`, dovuto a `release/1.0`
  ([ADR-0015](../../Decision.md#adr-0015)). Qui c'è solo il materiale di riserva.
- **Non contiene le scene dello standalone.** Il Blocco 1 non ne ha nessuna: `feature/01` è passata
  senza registrarne, e se ne servisse una si gira con lo stesso strumento e finisce qui. Le
  quattordici che ci sono vengono da `feature/02`, da `feature/03` e da `feature/04`.
- **Non contiene una registrazione della schermata `rich`.** Le cinque dell'applicazione sono tutte
  `--sink plain`, perché una riserva deve mostrare ciò che il pubblico vedrebbe, e ciò che il
  pubblico vede dal vivo è il pannello. Il pannello si ridisegna dieci volte al secondo e in un
  `.cast` diventa illeggibile e pesantissimo insieme; `plain` è il **contenuto** delle stesse righe
  ([ADR-0116](../../Decision.md#adr-0116)). Chi vuole vedere la resa `rich` la fa girare: nemmeno i
  filmati fabbricati da qui la contengono, perché nascono dagli stessi `.cast`.
- **Non contiene i filmati.** Un `.mp4` per scena pesa quanto tutte le registrazioni messe insieme,
  e si rifà in pochi secondi con `make filmati`: il repository conserva il `.cast`, che è la fonte,
  e lascia fuori ciò che dalla fonte si rigenera. I file vivono in `~/SqlStart2026-registrazioni`
  ([ADR-0016](../../Decision.md#adr-0016)).
- **La passata parlata non è fabbricabile.** `make filmati` restituisce l'esecuzione, non la voce:
  il commento per YouTube si registra con `make filmato`, sulla scena già vista.
- **Le registrazioni non sostituiscono i filmati, e i due branch lo chiedono in modo diverso.** Il
  criterio 8 di `feature/02` chiedeva entrambe le specie — «almeno una registrazione di riserva
  esiste in locale e `make preflight` non avvisa più»: soddisfatto per intero dal 17 settembre 2026,
  quando i filmati sono stati fabbricati dalle registrazioni. Il criterio 8 di `feature/03` chiede
  che la riserva del Blocco 3 sia «registrata e **riprodotta**», e quello era già soddisfatto.

---

**Decisioni correlate:** [ADR-0016](../../Decision.md#adr-0016) (i filmati e la copia locale
obbligatoria), [ADR-0050](../../Decision.md#adr-0050) (il formato delle registrazioni di terminale,
e perché lo strumento sta nel repository), [ADR-0055](../../Decision.md#adr-0055) (una registrazione
si riproduce prima di dichiararla buona), [ADR-0034](../../Decision.md#adr-0034) (`docker kill` non
è un guasto), [ADR-0044](../../Decision.md#adr-0044) (i due bersagli del failover),
[ADR-0045](../../Decision.md#adr-0045) (la maggioranza persa),
[ADR-0010](../../Decision.md#adr-0010) (i due profili dello sharded cluster),
[ADR-0073](../../Decision.md#adr-0073) (una scena di riserva è l'uscita di un comando del
repository), [ADR-0015](../../Decision.md#adr-0015) (il documento unico del talk),
[ADR-0115](../../Decision.md#adr-0115) (chi registra fa da seconda finestra),
[ADR-0116](../../Decision.md#adr-0116) (le registrazioni dell'applicazione pesano quanto il carico
che mostrano).

**Fonti:** [V-029](../../Sources.md#v-029), [V-031](../../Sources.md#v-031),
[V-045](../../Sources.md#v-045), [V-068](../../Sources.md#v-068), [V-089](../../Sources.md#v-089)
