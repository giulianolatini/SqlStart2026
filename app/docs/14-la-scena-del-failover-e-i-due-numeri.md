# 14. La scena del failover, e i due numeri che la chiudono

> Il principio in una riga: **una scena che gira non è una scena che dice il vero.** Fra un
> failover mostrato e un failover finto non c'è differenza visibile — le fasi scorrono uguali,
> il carico riprende uguale — tranne in due numeri. Tutto il Task 13 è costruito perché quei
> due numeri non possano mentire.

Questo è l'Atto II del Blocco 2: cinque minuti, il primario che cade, l'elezione raccontata con
il timestamp al millisecondo, e in fondo **quanto è durata l'interruzione** e **quante scritture
si sono perse**. È la ragione per cui l'applicazione esiste: le altre scene si potrebbero fare
con `mongosh` e un po' di pazienza, questa no.

La misura contro lo stack vero è [M-043](Sources.md#m-043): **10 019 ms di interruzione, 0
scritture perse su 15 229 confermate**, con il primario passato da `mongo-rs-1:27017` a
`mongo-rs-3:27017`. Il Passo 5 del piano chiedeva di confrontarli con quelli che `feature/02`
aveva già misurato mesi prima, e di fermarsi se non avessero coinciso. Coincidono, e l'ultima
sezione di questo capitolo racconta perché la coincidenza vale più dei numeri.

---

## Il copione è un dato, non un metodo

`ScenarioFailover` riceve un `Copione`: quale nodo fermare, con quale modo, e quanti secondi
dura ciascuna delle tre fasi di carico. È un `dataclass` congelato, e sta lì invece di essere
sei parametri di `esegui` per una ragione che si vede solo dal palco: il copione è **ciò che si
prova la sera prima**, e deve poter essere stampato, confrontato, e passato identico alla
registrazione di riserva.

```python
@dataclass(frozen=True, slots=True)
class Copione:
    nodo: str
    modo: ModoGuasto = ModoGuasto.FERMA
    carico_s: float = DURATA_CARICO_S      # 10.0
    elezione_s: float = DURATA_ELEZIONE_S  # 25.0
    recupero_s: float = DURATA_RECUPERO_S  # 15.0
```

I cinquanta secondi di durata predefinita non sono un'ipotesi: l'elezione misurata sta fra 8 e
10 secondi ([V-031](../../docs/Sources.md#v-031)), e venticinque danno margine perché anche una
giornata storta stia dentro la fase, senza che la sala aspetti a vuoto. Le prove usano numeri
molto più piccoli, e la prova di integrazione gira con `--carico 3 --elezione 20 --recupero 5`.

## Una sola implementazione, due modi

Il Passo 1 del piano chiede due cose che sembrano due programmi: `--step` mette in pausa prima di
ogni fase e riparte con Invio — è la modalità da palco, quella in cui si parla sopra a ciò che
sta per succedere — e senza `--step` la stessa scena gira da sola, ed è così che si producono le
registrazioni di riserva del Task 18.

Sono un programma solo, e la differenza è **una funzione**:

```python
Attesa = Callable[[FaseIniziata], None]

def senza_attesa(fase: FaseIniziata) -> None:
    ...

def esegui(self, *, attesa: Attesa = senza_attesa) -> EsitoFailover:
```

Due implementazioni — una «interattiva» e una «da registrare» — divergerebbero entro il primo
ritocco, e il piano B racconterebbe una storia diversa da quella provata. È lo stesso ragionamento
che al Task 10 ha tenuto insieme le tre rese: **il valore sta nel fatto che sia la stessa cosa**,
non nel fatto che si somiglino.

La pausa riceve l'evento della fase e non una stringa. Sembra un dettaglio di tipo, e non lo è:
una pausa che annunciasse una fase diversa da quella scritta a schermo sarebbe un difetto
invisibile fino al momento peggiore.

## Il decimo evento: annunciare invece di stampare

Le fasi vanno dette. La strada corta era una `print` dentro lo scenario, e avrebbe rotto due cose:
[ADR-0007](../../docs/Decision.md#adr-0007), che tiene la resa fuori dal dominio, e la
verificabilità della scena — una prova che asserisce su `capsys` verifica l'impaginazione, non la
sequenza.

Il decimo evento di dominio è `FaseIniziata`, e [ADR-0094](../../docs/Decision.md#adr-0094) ne
registra la nascita. È di **specie diversa** dai nove che lo precedono, e vale la pena dirlo a
chi aggiungerà l'undicesimo: i nove raccontano un fatto osservato — una scrittura è riuscita, un
server ha cambiato ruolo — mentre questo racconta un'intenzione. È l'unico evento che
l'applicazione produce sapendo già che accadrà.

Lo stesso evento serve i tre sink **e** la pausa:

```python
def annuncia(fase: str, descrizione: str) -> None:
    evento = FaseIniziata(self._orologio.now(), fase, descrizione)
    self._sink.emit(evento)
    fasi.append(fase)
    attesa(evento)
```

Tre righe, e la conseguenza è che modalità automatica e modalità da palco mostrano davvero la
stessa scena. La quarta riga — `fasi.append` — è quella che permette alla prova di asserire sulla
sequenza: l'esito porta con sé l'elenco delle fasi che ha attraversato, nell'ordine.

## Il guasto entra da una porta, e la porta è nata da un'impossibilità

Il Task 13 ha scoperto eseguendo che **un processo solo non può fare questa scena.**

Da un lato, la cronaca dell'elezione — «il primario era `mongo-rs-1:27017`, adesso è
`mongo-rs-3:27017`» — esiste solo se il client fa scoperta, e la scoperta funziona solo da dentro
la rete Compose, dove i nomi dei servizi si risolvono. È tutto il capitolo
[13](13-il-container-sulla-rete-e-la-scoperta-che-si-vede.md): dall'host lo stesso replica set si
raggiunge con `directConnection=True` su `localhost:27021`, e lì di topologia non ce n'è. C'è di
peggio: l'indirizzo del primario, visto dall'host, **è** `localhost:27021`, che non è il nome di
nessun servizio che si possa fermare.

Dall'altro, il guasto è un `docker compose kill`, e vuole il socket del demone. Il container
dell'applicazione non ce l'ha, per una scelta del Task 12 che resta valida: montare
`/var/run/docker.sock` dentro un container mostrato in sala vuol dire mostrare, senza dirlo, il
modo più diretto di prendere la macchina che lo ospita.

La risposta è la sesta porta, `Regia`, con [ADR-0095](../../docs/Decision.md#adr-0095) alle
spalle. Quattro verbi:

```python
class Regia(Protocol):
    def ferma(self, nodo: str) -> None: ...
    def riavvia(self, nodo: str) -> None: ...
    def sospendi(self, nodo: str) -> None: ...
    def risveglia(self, nodo: str) -> None: ...
```

e due adattatori che la implementano in modi opposti.

### `RegiaCompose` esegue

Vive sull'host. Costruisce la riga dal frasario e la lancia con `subprocess.run`. Un'uscita
diversa da zero diventa `ComandoFallito` e **ferma la scena**, ed è la decisione più importante
di quella classe: un arresto fallito lascerebbe il primario in piedi, e i due numeri finali
sarebbero zero millisecondi di interruzione e zero scritture perse — cioè un failover perfetto.
La sala vedrebbe la slide sbagliata senza che nessuno abbia modo di accorgersene.

### `RegiaAnnunciata` annuncia

Vive nel container. Stampa la riga esatta e si blocca finché qualcuno non conferma. Non finge, e
non potrebbe: fingere produrrebbe esattamente i numeri di un failover riuscito senza il failover.

Le due funzioni che riceve sono separate perché fanno due cose diverse in due momenti diversi —
`annuncia` scrive, `conferma` **blocca** — e la radice di composizione decide con che cosa: un
`typer.echo` e un `input()` dal vivo, qualcos'altro dentro una prova.

Quale dei due adattatori si costruisce lo decide `punto_di_vista()`, cioè la stessa funzione che
già sceglie il bersaglio ([ADR-0090](../../docs/Decision.md#adr-0090)). Lo scenario non lo sa e
non deve saperlo.

### Il frasario, separato dall'esecuzione

`ComandiCompose` è un dato congelato, e sta a parte proprio perché `RegiaAnnunciata` deve poter
**comporre** una riga senza avere il diritto di eseguirla. Congelato perché è ciò che le due
regie condividono, e una condivisione mutabile fra chi annuncia e chi esegue sarebbe il modo più
silenzioso di far divergere le due.

Due dettagli del frasario sono stati pagati con un difetto ciascuno.

**I due `--env-file` non sono una comodità.** I `compose.yaml` di questo repository interpolano
con la forma `${VARIABILE:?messaggio}`, che è un errore e non un valore vuoto: `docker compose -f
docker/02-replicaset/compose.yaml ps` dalla radice risponde sette volte «required variable … is
missing a value» e non arriva nemmeno a guardare i container; con il solo `tools/images.env` ne
restano due, per `PASSWORD_AMMINISTRATORE`. La misura è [M-040](Sources.md#m-040). Viaggia il
**percorso**, mai il contenuto — è ciò che rende la riga annunciata innocua da mostrare a schermo
e da registrare, ed è [ADR-0054](../../docs/Decision.md#adr-0054).

**I percorsi sono relativi alla radice del repository**, e la prima versione li componeva con
`radice()`. Dentro il container la riga annunciata diceva allora
`/lab/docker/02-replicaset/compose.yaml`: un percorso che esiste dentro il container e sull'host
no. Una riga annunciata che non si può incollare è peggio di nessuna riga, perché sembra
funzionare. `RegiaCompose` ha quindi un `dove`, che è la directory da cui parte: chi esegue sa
dove sta la radice, chi annuncia lo dice a parole.

`-p` non serve, e non c'è: ogni `compose.yaml` dichiara il proprio `name:` al suo interno.

## `SIGKILL`, e il piano che aveva torto

Il Passo 2 del piano detta la sequenza del copione e nomina, alla lettera, `docker compose stop`
del primario. Eseguito, `stop` manda `SIGTERM`, e `mongod` che riceve `SIGTERM` **cede il ruolo
con ordine** prima di uscire: [V-029](../../docs/Sources.md#v-029) misura quella strada in 574,
480 e 486 millisecondi, senza elezione da raccontare. La stessa misura con `docker kill` dà
9 812, 10 619 e 10 943 ms — che sono i numeri che [V-031](../../docs/Sources.md#v-031) ha già
portato sulle slide come «forbice 8-10 s».

Il piano e le slide non possono avere ragione tutti e due, e le slide riportano una misura fatta.
[ADR-0097](../../docs/Decision.md#adr-0097) registra la correzione: `ferma` esegue `docker compose
kill -s SIGKILL`, e `ARRESTO_ORDINATO = ("stop",)` resta nel codice, documentato e configurabile.

Resta perché è il confronto che rende leggibile il numero grande — mezzo secondo contro dieci — e
perché la lezione è migliore della decisione: **«fermare un nodo» non è un'operazione sola**, e
quale delle due si sceglie decide se il pubblico vedrà un'elezione o non la vedrà affatto.
Nell'ordine dell'intuizione, poi, va nel verso sbagliato: «spegnere bene» è venti volte più
rapido di «staccare la spina», e il motivo è che il primario che si spegne bene *dice* di
andarsene.

## Il supplemento: irraggiungibile ma vivo

`--mode sospendi` è l'altra scena, quella che il pubblico non si aspetta. `docker compose pause`
congela i processi del container senza ucciderli: il nodo è vivo, la porta è aperta, e nessuno
risponde. Il client prende un **timeout** invece di un connection refused, ed è la differenza fra
un server morto e una rete partizionata.

Nel codice, i due modi sono due coppie di verbi scelte da una funzione di tre righe:

```python
def _verbi(modo: ModoGuasto) -> tuple[...]:
    if modo is ModoGuasto.SOSPENDI:
        return (Regia.sospendi, Regia.risveglia, "congelo (irraggiungibile ma vivo)")
    return (Regia.ferma, Regia.riavvia, "fermo")
```

Il terzo elemento è la frase con cui la fase si annuncia, e sta accanto ai due verbi apposta: una
scena che dicesse «fermo» mentre sospende sarebbe una scena che insegna la cosa sbagliata.

## Come si misura l'interruzione

La strada ovvia è un ciclo che chiede al cluster chi è il primario finché qualcuno risponde.
Quella strada misura però il proprio intervallo di sondaggio quanto misura l'elezione: con un
sondaggio ogni mezzo secondo, un'elezione di 10 019 ms e una di 10 400 danno lo stesso numero, e
il numero dipende da una costante che nessuno ha discusso.

Il ponte SDAM del Task 7 riceve intanto, dai listener di PyMongo, gli eventi che descrivono
esattamente ciò che serve. `CronometroInterruzione` li guarda passare e deduce:

```python
def considera(self, evento: Evento) -> None:
    if not isinstance(evento, TopologyChanged):
        return
    primario = evento.successiva.primario
    if primario is None:
        self._apri(evento)
        return
    self._ultimo_primario = primario.indirizzo
    self._chiudi(evento, primario.indirizzo)
```

[ADR-0096](../../docs/Decision.md#adr-0096) motiva la scelta, e la conseguenza importante è
**quale** numero ne esce: non il tempo in cui il replica set ha eletto, ma il tempo in cui il
driver è rimasto senza un posto dove scrivere. È quello che vive un'applicazione vera, ed è il
solo dei due che il pubblico possa mettere in relazione con le proprie latenze.

### La trappola: il cronometro si arma, non parte

Un client che si connette passa per «topologia sconosciuta» e «replica set senza primario»
**prima** di trovarne uno. Contare quel tratto aprirebbe l'interruzione all'istante della
connessione, e il numero di testa del Blocco 2 diventerebbe il tempo di avviamento del client
sommato all'elezione — cioè un numero più grande del vero, che nessuno avrebbe motivo di mettere
in dubbio.

Il cronometro si arma al primo primario visto: `_apri` non fa niente finché `_ultimo_primario` è
`None`. Prima di allora non c'è niente che si possa perdere.

È anche il motivo per cui la classe esiste invece di tre righe dentro lo scenario: una regola con
un caso limite merita un posto in cui il caso limite si provi da solo.

### Tutte le interruzioni, e quella che chiude la scena

`interruzioni` le restituisce tutte in ordine — una seconda interruzione durante la ripresa è un
fatto, e nasconderla sarebbe una scelta — mentre `prima` è quella che va in fondo al rapporto: il
guasto provocato dalla regia, non i suoi echi.

## I due numeri, e le due voci che non vanno sommate

La cronaca apre con i due numeri, e non è impaginazione:

```
failover interruzione 10019.0 ms · scritture perse 0
         da mongo-rs-1:27017 a mongo-rs-3:27017
scritture 15229 confermate · 15229 ritrovate · 0 non confermate
```

Chi guarda dalla decima fila legge la prima riga e le ultime due. Metterli in fondo, dopo tre
riepiloghi di carico, vuol dire farli scorrere via insieme alle latenze.

**Scritture perse** e **scritture non confermate** restano due voci distinte perché sono due
fenomeni opposti, e nessuno dei due è il negativo dell'altro: una scrittura non confermata è una
che il client non sa se sia andata, e potrebbe essere nella collezione; una scrittura persa è una
che il client sapeva andata e nella collezione non c'è. La seconda è quella che fa male, ed è la
sola che il talk promette di mostrare.

### Perché zero — e non è merito dell'applicazione

Le zero scritture perse hanno una spiegazione che vale la pena dire per intero, perché la frase
sbagliata è a portata di mano. Il `WriteConcern` del client è **vuoto**: `mongolab` non chiede
niente. Il valore effettivo, `w: majority`, arriva dal server come default *implicito*, e
`getDefaultRWConcern` lo dichiara con `defaultWriteConcernSource: 'implicit'`
([M-041](Sources.md#m-041), su MongoDB 7.0.40).

Quindi la frase da dire in sala non è «la mia applicazione usa `w: majority`», che sarebbe falsa,
ma **«nessuno qui ha chiesto niente, e il server ha scelto bene»**. Il che rende anche prevedibile
la variante: chi avesse eseguito `setDefaultRWConcern` con qualcosa di più debole vedrebbe questa
stessa scena produrre un altro numero. E il confronto con
[V-016](../../docs/Sources.md#v-016) — cento scritture perse con `w: 1` — resta valido proprio
perché lì il write concern era **esplicito**: quella misura scavalcava il default, questa lo
eredita.

## `--step` e `--sink rich` non stanno nello stesso terminale

La pausa legge da stdin, sul thread della scena. La resa `rich` tiene aperto un `Live` che
ridisegna su un thread suo ([ADR-0085](../../docs/Decision.md#adr-0085)). Le due cose vogliono lo
stesso terminale: il prompt «Invio per proseguire» finisce sotto il ridisegno successivo, e chi
tiene la tastiera dal palco non vede più che cosa sta aspettando.

È il genere di difetto che non fallisce nessuna prova e rovina esattamente un'occasione. La
combinazione è quindi rifiutata come errore di parametro, **prima** che la scena cominci: prima
della connessione, del carico e della collezione di lavoro. Il messaggio detta la riga giusta —
dal palco è `--step --sink plain`, che è la stessa con cui si girano le registrazioni di riserva.

Degradare in silenzio a `plain` sarebbe stato più gentile e peggiore: una scena che cambia da sola
la propria resa è una scena che dal vivo mostra qualcosa di diverso da quello che si è provato la
sera prima. [ADR-0098](../../docs/Decision.md#adr-0098) porta la riserva: è una biforcazione vera,
e se le prove generali mostrassero che `plain` non regge la proiezione va riaperta.

Il testo della pausa esce da `typer.echo` e non dal sink, benché la fase sia già un evento e il
sink la stia già rendendo. Sono due cose diverse: il sink racconta **alla sala** ciò che succede,
quella riga parla **a chi tiene la tastiera**. Confonderle vorrebbe dire mettere «premi Invio»
dentro una registrazione asciinema.

## Il ciclo di `watch` se n'è andato da `cli.py`

Fuori copione, ma nello stesso task: il ciclo che `watch` teneva dentro la radice di composizione
è diventato `sorveglia`, in `application/scenari.py`.

Non è riordino. Dentro `cli.py` quel ciclo era provabile solo eseguendo il comando, cioè aprendo
una connessione, e la sua regola più delicata — si aspetta `giri - 1` volte e non `giri` — non
aveva nessuna prova. Mezzo secondo speso dopo l'ultimo sguardo è mezzo secondo in cui la scena è
finita e lo schermo è fermo. Adesso è una funzione con un `ValueError` sui giri sotto uno e le sue
prove.

Il punto aperto che il registro segnava come «il ciclo di `watch` vive in `cli.py`» si chiude qui.

## Che cosa si è rotto la prima volta che si è eseguito davvero

Due cose, e nessuna delle due era visibile alle prove unitarie, che erano tutte verdi.

### Guardare non è aspettare

Alla prima esecuzione contro lo stack acceso, `demo failover` è uscito con:

```
Invalid value: nessun primario in vista su «rs»
```

contro un replica set sanissimo. La causa non era il cluster: `Inspector.topology()` legge la
descrizione che il driver **ha già** in mano, e nei primi millisecondi dopo `MongoClient(...)`
quella descrizione è ancora vuota, perché la scoperta comincia in quel momento e prosegue su
thread suoi. La docstring di `topology()` lo diceva da sempre — «è una lettura pura, non fa
scoperta e non blocca» — e nessuno l'aveva letta come un'avvertenza. La misura è
[M-042](Sources.md#m-042).

Gli altri comandi non ci inciampavano **per caso**: `stats` chiede `serverStatus`, che è un
comando vero e quindi aspetta la selezione; `watch` guarda la topologia proprio mentre cambia, che
è il suo mestiere. Solo `demo failover` guarda una volta sola, subito, e su quella risposta decide
chi fermare.

La correzione è un `ping`. Essendo un comando su `admin`, va sul primario per impostazione
predefinita — la docstring di `Database.command` lo dichiara e il codice di PyMongo 4.17.0 lo
attua, [A-017](Sources.md#a-017) — e quindi torna esattamente quando la domanda successiva ha una
risposta.

Il posto comodo dove metterla era `cli.py`, dove sta la chiamata. La guardia
`test_pymongo_si_importa_solo_nell_infrastruttura` lo vieta, e la sua docstring dice, da sempre,
che «`cli.py` è proprio il posto in cui la tentazione arriva». La guardia ha avuto ragione e non
è stata toccata: l'attesa vive in `infrastructure/bersagli.py`, accanto all'unico
`MongoClient(...)` del repository, e traduce il `ServerSelectionTimeoutError` in un
`SenzaPrimario` di quello strato; la riga di comando lo cattura e ne ricava la frase, che è cosa
sua. È [ADR-0099](../../docs/Decision.md#adr-0099), e il codice è finito meglio di dove voleva
andare.

`niente_da_fermare` **restituisce** l'eccezione di `typer` invece di sollevarla, così il messaggio
— la parte che finisce davanti al pubblico — si prova senza dover fabbricare un replica set
malato.

### La prova che passava per la ragione sbagliata

La seconda esecuzione ha fallito con «il nuovo primario è `mongo-rs-1:27017`, cioè il nodo che la
scena dice di aver ucciso». Il difetto era nella prova: cercava la prima riga `SERVER … →
primario` dell'output, e la prima è la **scoperta iniziale**, che nomina il primario di sempre.

Il pericolo non era il fallimento, era il caso opposto. Una prova che ricostruisce l'elezione
dalle righe di scoperta passerebbe anche se il guasto non fosse mai arrivato. L'asserzione si
appoggia adesso alla riga di continuazione che la cronaca stampa **solo** se qualcuno ha
davvero preso il posto di qualcun altro:

```
         da mongo-rs-1:27017 a mongo-rs-3:27017
```

cioè si verifica ciò che la sala legge.

## Le prove

### Con i doppi: l'asserzione è sulla sequenza

Il Passo 4 chiede che lo scenario si provi con `RecordingSink` e i doppi, asserendo sulla
**sequenza di eventi**. È la forma giusta perché una scena è un ordine: fermare il nodo *dopo*
aver misurato l'interruzione darebbe zero millisecondi — cioè un failover perfetto — e nessuna
asserzione sui conteggi se ne accorgerebbe.

`RegiaFinta` annota i verbi nell'ordine in cui li riceve, e la prima prova che la riguarda è
esattamente quella sull'ordine. Con `noti=frozenset({...})` rifiuta un nodo che non conosce, e
**non annota l'ordine rifiutato**: serve a provare la strada dell'errore — una `--node` scritta
male dal palco — senza uno stack acceso.

`RegiaCheRifiuta` solleva a ogni verbo e annota lo stesso, prima di sollevare. La distinzione che
permette è fra due fallimenti che di fuori si somigliano: la scena che ha *chiesto* di fermare il
nodo e non c'è riuscita, e la scena che non l'ha mai chiesto. La seconda è il difetto peggiore che
questa applicazione possa avere.

### Contro lo stack vero: una prova che fa da umano

`app/tests/integration/test_scenari.py` gira la scena **dentro** il container, sulla rete di
`02-replicaset`, e supplisce alla metà che manca. Un `Popen` legge lo stdout riga per riga; quando
una riga comincia con `docker compose `, la esegue **verbatim** sull'host con `shlex.split` dalla
radice del repository, poi scrive un `\n` sullo stdin del container.

Di passaggio, questo dimostra la cosa che nessun'altra prova può dimostrare: che la riga annunciata
è davvero incollabile. Se `RegiaAnnunciata` sbagliasse un `--env-file`, la prova fallirebbe.

Un `threading.Timer` fa da scadenza, perché un Invio che non arriva è un comando che non torna
mai; e `rimetti_in_piedi` chiude con `unpause` e `start` su tutto, come rete di sicurezza sotto la
ripresa che la scena fa già da sé.

La collezione di carico si porta via **da dentro il container**, e anche questo è un dettaglio
pagato: dopo un failover il client dell'host, che è `directConnection`, può ritrovarsi puntato a
un secondario, e il `drop` fallirebbe.

L'asserzione sui due numeri usa una banda larga — fra 5 000 e 15 000 ms — e non i 10 019 misurati.
Stringerla darebbe una prova che fallisce sul portatile di qualcun altro senza che niente sia
rotto. Ciò che la banda intercetta è l'errore di **categoria**: zero, cioè il guasto non è
arrivato; o sessanta secondi, cioè l'elezione non è avvenuta. Il numero preciso sta in
[M-043](Sources.md#m-043), che è il posto dei numeri precisi.

### Lo stato delle suite

```
uv run pytest tests/unit         → 523 passed
uv run mypy                      → Success: no issues found in 64 source files
uv run pytest tests/integration/test_scenari.py → 1 passed, ~34 s
```

## Il confronto che chiude il task

Il Passo 5 chiede di confrontare i numeri dell'applicazione con quelli che `feature/02` aveva già
misurato a mano, e aggiunge la regola giusta: **se dicono cose diverse, uno dei due è sbagliato, e
va capito quale prima di andare avanti.**

| | `feature/02`, a mano | `mongolab`, Task 13 |
|---|---|---|
| interruzione | 9 812 / 10 619 / 10 943 ms ([V-029](../../docs/Sources.md#v-029)) — «forbice 8-10 s» ([V-031](../../docs/Sources.md#v-031)) | **10 019 ms** |
| scritture perse | 0 su 12 901 confermate ([V-033](../../docs/Sources.md#v-033)) | **0** su 15 229 confermate |

Coincidono, e nessuno dei due va corretto. Vale la pena essere espliciti sul perché il confronto
contasse: le prove unitarie asseriscono sulla sequenza con i doppi, e una sequenza giusta può
benissimo accompagnare due numeri sbagliati — se il guasto non arrivasse, l'interruzione sarebbe
zero e la sequenza resterebbe identica. Una misura fatta settimane prima, per un'altra strada, da
un'altra persona che scriveva `docker kill` a mano, è il solo controllo che quei due numeri
abbiano un significato.

## Che cosa questo capitolo lascia aperto

- **La scena dal vivo richiede due terminali**, e va detto al PO prima delle prove generali: uno
  mostra la scena dentro la rete, l'altro esegue il guasto che la scena detta. Non è una
  scomodità aggirabile: è [ADR-0095](../../docs/Decision.md#adr-0095), e l'alternativa era il
  socket Docker nel container.
- **Il rifiuto di `--step` con `--sink rich`** è una rinuncia dichiarata, non una soluzione. Se in
  proiezione `plain` non reggesse, [ADR-0098](../../docs/Decision.md#adr-0098) va riaperto.
- **`--mode sospendi` non ha una prova di integrazione.** La sequenza è provata con i doppi, ma
  che `pause` produca davvero un timeout invece di un connection refused è affermato e non
  misurato. È il supplemento del Passo 3, e la misura manca.
- **Il numero dipende da questo replica set.** I 10 019 ms e la forbice di V-029 valgono per le
  impostazioni di elezione di questo lab; la frase in sala è «su questo lab», non «in MongoDB».
- **`mongodump` nell'immagine** resta la decisione del Task 14 ([M-039](Sources.md#m-039)).
