# 12. La radice di composizione, e la prima volta che si esegue davvero

> Il principio in una riga: **un posto solo sa come si chiamano le cose** — e il corollario, pagato
> tre volte in un pomeriggio: finché quel posto non esiste, non hai mai eseguito niente.

Undici capitoli fa questa applicazione ha cominciato con quattro cartelle e una regola. Da allora
sono nate cinque porte, nove specie di evento, un generatore di carico, un osservatore della
topologia, un ponte SDAM, quattro adattatori veri e tre rese. Tutte queste cose hanno una proprietà
in comune, e fino a questo capitolo era anche il loro limite: **nessuna di loro sa chi sono le
altre.** `WorkloadRunner` riceve un `DocumentStore` e non sa che dietro c'è pymongo; `RichTui`
riceve un `Clock` e non sa che dietro c'è `time.monotonic`.

Un'applicazione fatta interamente di pezzi che non si conoscono non si avvia. Da qualche parte
qualcuno deve conoscerli tutti, costruirli e legarli. Quel posto ha un nome — **radice di
composizione**, *composition root* — e in `mongolab` è un file solo:
[`src/mongolab/cli.py`](../src/mongolab/cli.py).

Questo capitolo racconta com'è fatto, e poi racconta la parte che nessuno mette nei diagrammi: che
cosa è successo la prima volta che il programma è stato eseguito davvero, contro un MongoDB acceso,
con 425 prove verdi alle spalle.

---

## Che cos'è una radice di composizione

Il §6.1 del disegno la definisce in una riga: «`cli.py` è l'unico punto che conosce le classi
concrete». Detta così sembra una convenzione di stile. È invece una proprietà verificabile, e vale
la pena guardarla dal verso in cui si rompe.

Immaginate che `WorkloadRunner`, invece di ricevere un `DocumentStore`, si costruisse il suo:

```python
class WorkloadRunner:
    def __init__(self, ...):
        self._archivio = PymongoStore(MongoClient("mongodb://localhost:27017/")["lab"]["ordini"])
```

Tutto funzionerebbe. La differenza non si vede finché non si prova a fare una delle tre cose per
cui il codice esiste: **provarlo** (ogni prova avrebbe bisogno di un MongoDB acceso),
**riconfigurarlo** (l'indirizzo è dentro una classe che parla d'altro) e **cambiarlo** (sostituire
l'archivio vuol dire modificare chi lo usa). L'iniezione delle dipendenze non è una tecnica: è la
decisione di rimandare quella conoscenza in **un posto solo**, e la radice di composizione è quel
posto.

Il prezzo lo paga la radice: è l'unico file dell'applicazione che ha il diritto di essere brutto,
nel senso preciso che importa tanto e non astrae niente. Le sue prime venti righe di `import`
nominano quattro adattatori d'infrastruttura, tre rese, due componenti applicativi e due porte. È
una lista della spesa, ed è giusto che lo sia.

### La guardia che rende la regola più di un'intenzione

Il capitolo 5 ha descritto la guardia `ast` in
[`tests/unit/test_scheletro.py`](../tests/unit/test_scheletro.py): `domain/` e `application/` non
importano nessuna libreria di terze parti, e `pymongo` compare **solo** sotto `infrastructure/`.

Quella guardia vale anche per `cli.py`, che pure è il punto in cui i client nascono. Non è una
contraddizione: `cli.py` chiama `bersagli.connetti(...)`, e `bersagli.py` è l'unico posto del
repository in cui `MongoClient(...)` compare davvero. Se domani un `import pymongo` spuntasse nella
radice, l'applicazione funzionerebbe esattamente come oggi — e sarebbe un difetto lo stesso, perché
la seconda riga sarebbe più facile della prima e la decima non la noterebbe nessuno.

> Se un `import` di `pymongo` compare altrove che in `infrastructure/`, è un difetto anche se
> funziona.
>
> — il Passo 1 del Task 11, che è la frase con cui questa guardia è stata chiesta

---

## Tre comandi, e le opzioni che hanno davvero

Il §6.4 elenca sette righe di comando. Tre sono **dirette** — mostrano un fatto e basta — e sono
quelle di questo capitolo:

```sh
mongolab stats    --target rs
mongolab watch    --target rs
mongolab workload --target rs --writers 8 --readers 4 --doc-size 2k --duration 120
```

Le altre quattro sono `demo` di scenario e arrivano al Task 13, insieme ad
`application/scenari.py`.

La riga di `workload` merita una nota. I quattro valori che scrive — 8, 4, `2k`, 120 — sono
diventati i **predefiniti** delle rispettive opzioni, e la conseguenza è che
`mongolab workload --target rs` e la riga lunga del design sono **lo stesso comando**. Non è
un'economia di battitura: il Task 16 misurerà quella corsa, una slide mostrerà quei numeri, e chi
la digita dal palco scriverà la forma corta. Due righe di comando che fanno cose diverse con lo
stesso nome sono il modo più rapido di perdere il filo davanti a cento persone.

### Perché `--sink` non c'è su `stats`

`watch` e `workload` hanno `--sink`; `stats` no. È una scelta dichiarata, non una dimenticanza.

`stats` è una fotografia: interroga, compone un testo, lo stampa, esce. Non emette **nessun**
evento, quindi non ha un `EventSink` da scegliere. Un `--sink` lì sarebbe un'opzione accettata,
documentata nell'aiuto, e inerte — cioè una bugia che la riga di comando racconta a chi la legge.
Il repository si è impegnato a non scriverne, e il posto in cui l'impegno si mantiene o si perde è
esattamente questo: le opzioni che non servono si aggiungono «per uniformità».

### `--target` non ha un valore predefinito, e non lo avrà

```python
Bersaglio_ = Annotated[
    str,
    typer.Option(
        "--target",
        help="Quale stack: standalone, rs, sharded.",
        callback=_controlla_bersaglio,
    ),
]
```

Nessun `= "rs"`. Durante il talk si passa da uno stack all'altro tre volte, e un predefinito
silenzioso vorrebbe dire collegarsi a quello sbagliato **senza accorgersene**, per poi scoprirlo da
una topologia che non torna mentre la sala guarda.

La stessa severità è nel `Makefile`, che rifiuta un `TARGET` mancante invece di indovinarlo:

```make
CHIEDI_TARGET = @[ -n "$(TARGET)" ] || { echo "manca TARGET: make $@ TARGET=rs (standalone, rs, sharded)" >&2; exit 2; }
```

Il **2** non è casuale: è il codice con cui Typer esce quando un parametro è sbagliato
([M-034](Sources.md#m-034)). Sbagliare la riga di `make` e sbagliare la riga di `mongolab` sono lo
stesso errore per chi legge l'uscita di un CI, e meritano lo stesso numero.

---

## La mappa in un posto solo

Dietro la parola `rs` stanno tre fatti: una porta pubblicata sull'host, un `.env` da cui leggere la
credenziale, e una decisione su `directConnection`. Fino al Task 10 vivevano in
`tests/integration/ambiente.py`, che li aveva perché era l'unico codice del repository a collegarsi
a qualcosa. Con l'applicazione i candidati diventano due — e due copie divergono al primo cambio,
con la seconda che se ne accorge dopo venti secondi di timeout di selezione, in un messaggio che
parla d'altro.

La regola che scioglie il dubbio è meccanica: **il codice di produzione non può importare quello di
prova, il contrario sì.** Quindi la mappa sta in `infrastructure/bersagli.py`, e le prove
d'integrazione la importano da lì ([ADR-0087](../../docs/Decision.md#adr-0087)).

```python
BERSAGLI: Final[Mapping[str, Bersaglio]] = {
    "standalone": Bersaglio(nome="standalone", stack="01-standalone", porta=27017, diretto=True),
    "rs":         Bersaglio(nome="rs", stack="02-replicaset", porta=27021, diretto=True,
                            ambiente="docker/02-replicaset/.env"),
    "sharded":    Bersaglio(nome="sharded", stack="03-sharded", porta=27117, diretto=False,
                            ambiente="docker/03-sharded/.env"),
}
```

Tre cose in questa tabella hanno una storia più lunga di quanto sembri.

**La credenziale non entra nell'URI.** `Bersaglio.uri` è `mongodb://host:porta/` e basta; utente e
password vanno a `MongoClient` come argomenti, dove pymongo non li lascia uscire né in
`repr(client)`, né in un `ServerSelectionTimeoutError`, né in un `OperationFailure`
([M-018](Sources.md#m-018)). Dentro l'URI ci finirebbero in tutti e tre.

**`diretto=True` sul replica set è il punto di vista dell'host.** Con `replicaSet=rs0` da fuori
della rete Compose, pymongo scopre i membri dalla configurazione del set — `mongo-rs-1:27017` e
compagni, nomi che l'host non risolve — e un replica set perfettamente sano si legge
`ReplicaSetNoPrimary` ([M-019](Sources.md#m-019)). La riserva è dichiarata e ha una scadenza: al
Task 12 l'applicazione gira **dentro** la rete Compose, e la scoperta funziona
([ADR-0012](../../docs/Decision.md#adr-0012)).

**Le porte sono quelle predefinite.** I file Compose le scrivono `${PORTA_...:-27021}`: un
operatore che le spostasse con una variabile d'ambiente non verrebbe seguito da questa mappa.
Nessuno lo fa, `tools/preflight.sh` riserva gli intervalli, ed è una riga aperta scritta come tale.

### Il nome sbagliato muore prima della connessione

```python
def _controlla_bersaglio(nome: str) -> str:
    try:
        bersaglio_di(nome)
    except BersaglioSconosciuto as errore:
        raise typer.BadParameter(str(errore)) from errore
    return nome
```

Un `callback` di Typer e non un `try` nel corpo del comando. La differenza è di tre cose:
il controllo avviene mentre si leggono gli argomenti, il codice d'uscita è il **2** convenzionale
per «hai scritto male», e soprattutto **non si è ancora aperta nessuna connessione**. Un nome
sbagliato validato nel corpo produrrebbe lo stesso errore venti secondi più tardi, dopo un tentativo
di collegarsi a niente.

Il messaggio elenca i tre nomi che esistono, e non è cortesia:

```
«02-replicaset» non è uno stack di questo repository. I bersagli sono: rs, sharded, standalone.
```

Chi sbaglia `--target` sta quasi sempre scrivendo il nome della *directory* (`02-replicaset`) o
quello del *set* (`rs0`). Senza i tre nomi veri sotto gli occhi, va a cercarli nel sorgente.

---

## Il sink è un'opzione, non una condizione sparsa

```python
def sink_di(resa: Resa, orologio: Clock) -> EventSink:
    if resa is Resa.RICH:
        return RichTui(orologio)
    if resa is Resa.PLAIN:
        return PlainSink(sys.stdout)
    return NullSink()
```

Quattro righe, in una funzione, chiamate da un posto. La forma alternativa — `if sink == "plain":`
dentro `watch`, e di nuovo dentro `workload`, e domani dentro i quattro comandi `demo` — è la stessa
cosa scritta sei volte, e la sesta diverge. Il Passo 3 del piano ha un nome per quel difetto:
**condizione sparsa**.

`Resa` è un `str, Enum` con tre valori e non un booleano `--no-tui`, perché i casi sono davvero tre:
la sala (`rich`), le registrazioni asciinema di riserva del Task 18 (`plain`, dentro
`tools/registra-terminale.py`, [ADR-0050](../../docs/Decision.md#adr-0050)) e le misure del Task 16
(`null`, dove il costo del disegno non deve entrare nei numeri). Eredita da `str` perché è così che
Typer sa mostrare le tre scelte nell'aiuto e rifiutare la quarta senza che nessuno scriva la
validazione.

Questo è il gancio con cui il Task 18 produrrà le registrazioni **senza toccare il codice**: cambia
una parola sulla riga di comando, non un file.

### `Cablaggio`: rendere osservabile ciò che altrimenti va provato eseguendo

```python
@dataclass(frozen=True, slots=True)
class Cablaggio:
    bersaglio: Bersaglio
    orologio: Clock
    sink: EventSink

def cabla(target: str, resa: Resa) -> Cablaggio:
    bersaglio = bersaglio_di(target)
    orologio = SystemClock()
    return Cablaggio(bersaglio=bersaglio, orologio=orologio, sink=sink_di(resa, orologio))
```

Queste tre righe scritte dentro ciascun comando funzionerebbero identiche. La differenza è che per
verificarle bisognerebbe **eseguire il comando**, cioè aprire una connessione: la prova della radice
di composizione diventerebbe una prova d'integrazione, e le prove d'integrazione non si eseguono a
ogni salvataggio. Con `Cablaggio`, invece, `cabla("rs", Resa.PLAIN)` risponde offline, in
microsecondi.

E che `cabla` **non apra niente** è la proprietà su cui poggia tutto il resto: il `MongoClient`
nasce nel corpo del comando, dentro un `try`/`finally` che lo chiude. Una connessione aperta e mai
chiusa lascia il thread del monitor a battere anche dopo che la scena è finita — su uno schermo
proiettato, un cursore che non torna.

---

## Che cosa provano le prove della CLI

Il Passo 4 del piano è netto:

> Le prove della CLI verificano il **cablaggio** — che `--sink plain` produca un `PlainSink`, che un
> `--target` sbagliato fallisca con un messaggio e un codice d'uscita diverso da zero — non il
> comportamento dei componenti, già provato altrove.

È una distinzione che vale la pena rendere concreta. `PlainSink` scrive una riga per evento: lo
prova `tests/unit/test_plain.py`, ed è giusto lì. Che `--sink plain` **scelga** `PlainSink` non lo
prova nessuno di quei file, perché nessuno di quei file sa che esiste una riga di comando. È
l'unica cosa che le prove della CLI hanno da dire, e la dicono trentuno volte.

Un esempio della forma:

```python
def test_il_carico_sceglie_una_collezione_sua(monkeypatch) -> None:
    cliente = carico_finto(monkeypatch)
    codice, _ = esegui("workload", "--target", "standalone", "--sink", "null", "--duration", "0.01")
    assert codice == 0
    assert cliente.database.chieste[0].startswith(PREFISSO_CARICO)
```

Non c'è MongoDB, non c'è rete, non ci sono thread da aspettare: c'è un doppio che **annota che cosa
gli è stato chiesto**, e un'asserzione su quella lista. La prova dura millisecondi e fallisce per un
motivo solo — che il cablaggio sia cambiato.

### La sorpresa di Typer, e la funzione `pulito()`

Provare un messaggio d'errore di Typer sembra banale finché non lo si fa. `typer.BadParameter` esce
con **2**, e il messaggio Rich lo incornicia in un riquadro con caratteri `│` e sequenze ANSI di
colore, **mandandolo a capo dove finisce il riquadro**. A ottanta colonne una frase di ottanta
caratteri arriva spezzata in due righe ([M-034](Sources.md#m-034)).

Un'asserzione ingenua — `"non è uno stack" in result.output` — fallirebbe quindi per un motivo che
non riguarda il codice: la larghezza del terminale di chi esegue le prove. Il rimedio è un helper
di tre righe che toglie l'ANSI, toglie il bordo e ricuce gli spazi, e che è stato verificato dando
lo stesso risultato a `COLUMNS=80` e a `COLUMNS=200`. Ripulire l'uscita rende l'asserzione una
domanda sul **messaggio** invece che sull'impaginazione.

Una nota che si paga in fretta: typer 0.27.2 **incorpora** click al proprio interno, e in questo
ambiente `import click` solleva `ModuleNotFoundError`. Nessuna prova può appoggiarsi a quel nome.

---

## E poi si è eseguito davvero

Fin qui la parte che si progetta. Quello che segue è la parte che si scopre.

Quando la radice di composizione è stata finita, la batteria era verde: 425 prove unitarie, 43
d'integrazione, `mypy --strict` su 57 file senza un rilievo. Poi lo stack 01 è stato acceso, e i
tre comandi eseguiti per la prima volta contro un MongoDB vero. **Due su tre erano sbagliati**, e un
terzo aveva un difetto minore.

Nessuno dei tre era una svista di battitura. Tutti e tre vivevano nello stesso posto: la giuntura
fra componenti che, presi uno per uno, erano corretti.

### Primo: il carico scriveva nella collezione seminata

```
47:46.007  ERRORE     BulkWriteError: batch op errors occurred, full error: {'writeErrors': [...
carico      38 scritture · 0 confermate · 38 fallite · 76 ritentate · 0 documenti
letture     4833 letture · 4833 riuscite · 0 fallite · 96660 documenti
```

L'errore per intero, ripescato fuori dal carico:

```
E11000 duplicate key error collection: lab.ordini index: _id_ dup key: { _id: 0 }
```

`DataGenerator` numera i documenti da zero — è ciò che rende il dataset una funzione pura di
`(seme, indice)`, vedi il capitolo 6 — e il seed occupa già gli `_id` da 0 a 49 999. La radice di
composizione aveva mandato il carico in `lab.ordini`. Ogni singola scrittura tornava indietro.

Guardate però la **forma** del guasto, che è la parte istruttiva. Il processo non si è fermato: è
uscito con zero. La cronaca scorreva. Le letture riuscivano — 4 833 su 4 833 — e riempivano lo
schermo di attività. Dal fondo della sala quella è una demo che funziona; solo leggendo la riga
`carico` si scopre che di scritture confermate non ce n'è nemmeno una.

Le prove unitarie non potevano trovarlo, **e non dovevano**: `InMemoryStore` accetta gli `_id` che
gli si danno, e non ha un seed. Il fatto vive nel punto in cui un generatore che numera da zero
incontra una collezione già numerata — cioè in nessuno dei due componenti, e in nessuna delle loro
prove.

A sbagliare era il cablaggio, non il disegno: che il carico dovesse scrivere altrove era già
scritto in due posti, `infrastructure/generatore.py` («le due popolazioni non si incontrano mai
nella stessa collezione, perché il carico scrive nella propria») e `tools/reset-demo.sh`, che tiene
`const superstiti = ["ordini"]` e considera residuo tutto il resto. Il posto c'era; ci si è mandato
il carico ([ADR-0088](../../docs/Decision.md#adr-0088), [M-032](Sources.md#m-032)).

La correzione è un nome per corsa:

```python
def collezione_di_carico(istante: datetime) -> str:
    """Il nome della collezione per **questa** corsa: `carico-20260918-103000`."""
    return f"{PREFISSO_CARICO}{istante:%Y%m%d-%H%M%S}"
```

Per corsa e non fisso, perché gli `_id` ripartono da zero **ogni volta**: una seconda esecuzione
sulla stessa collezione fallirebbe come falliva contro `ordini`, e in sala il carico si lancia più
di una volta. Il comando dice anche dove scrive, prima di cominciare — un benchmark che non nomina
la propria collezione è un benchmark che non si può rileggere.

Dopo la correzione, la stessa riga di comando: **8 245 scritture, 8 245 confermate, 0 fallite.**

### Secondo: il failover raccontato due volte

`mongolab watch` contro lo stack 01 stampava ogni transizione **due volte**, a mezzo secondo di
distanza:

```
20:58:05.293  TOPOLOGIA  sconosciuta → singola
20:58:05.798  SERVER     localhost:27017 sconosciuto → standalone
20:58:06.303  SERVER     localhost:27017 sconosciuto → standalone
```

La prima ipotesi — pymongo emette l'evento due volte, forse una per monitor — è stata verificata
invece che creduta: un `MongoClient` con un ascoltatore nudo che stampa, e nient'altro in mezzo. Il
driver la emette **una volta sola** ([M-033](Sources.md#m-033)).

Il doppione era nostro. `watch` aveva due narratori sullo stesso fatto: `SdamBridge`, che traduce i
callback del driver (**spinto**), e `TopologyWatcher`, che rilegge la stessa `TopologyDescription`
ogni mezzo secondo (**tirato**). Due osservatori sulla stessa struttura, uno per verso: era
garantito che si ripetessero. Il ritardo di un giro fra i due rendeva la ripetizione difficile da
riconoscere come tale — sembrava che fosse successo due volte.

E questo è il punto che vale oltre il difetto. Un failover raccontato due volte non è rumore: chi
guarda **conta** le transizioni per capire che cosa è successo, e leggerne il doppio è leggere
un'altra storia. La scena centrale del talk avrebbe mentito.

La correzione è una riga in meno nel cablaggio: in `watch` resta il ponte, e la sentinella non viene
costruita. Lo prescrive il §6.3, che assegna al ponte «la cronaca a schermo del failover con
timestamp al millisecondo» — che sono anche gli istanti migliori, perché segnano *quando il driver
ha saputo*, non quando qualcuno è passato a chiedere. `TopologyWatcher` conserva l'altra cosa che sa
fare, misurare la durata dell'**interruzione**, e quella misura vale accanto alle scritture perse:
nello scenario di failover del Task 13 ([ADR-0089](../../docs/Decision.md#adr-0089)).

Vale la pena scartare esplicitamente la scorciatoia, perché è quella che viene in mente per prima:
**deduplicare nel sink**. Curerebbe il sintomo e introdurrebbe un guasto peggiore. Due transizioni
identiche e ravvicinate sono anche la firma di un membro che *flappa* — cioè esattamente ciò che una
demo di failover deve mostrare — e un filtro non sa distinguere i due casi. Sceglierebbe di
nascondere quello vero.

> Su uno stesso fatto, un narratore solo. Se due componenti osservano la stessa struttura, uno
> spinto e uno tirato, la ripetizione non è un rischio: è una certezza.

### Terzo: la fotografia diceva `sconosciuto` di un server sano

```
standalone (docker/01-standalone)
topologia   singola
            localhost:27017       sconosciuto              —
server      mongod 7.0.40 · attivo da 7 h 20 m · connessioni 3
database    lab · 50000 documenti · dati 5.8 MB · indici 524.0 kB
```

Il server è vivo — le tre righe sotto lo dimostrano — e la prima riga dice che il suo ruolo è
ignoto.

`client.topology_description` riferisce ciò che il client **crede in questo istante**, e su un
client appena costruito quella credenza è «non lo so ancora»: il primo battito non è ancora tornato
([M-031](Sources.md#m-031)). Non è un difetto del driver. È esattamente la proprietà che rende
visibile l'attimo in cui, durante un'elezione, il client non sa — cioè la scena per cui `watch`
esiste. Diventa un difetto solo se la si legge per prima e si stampa il risultato come una
fotografia.

La correzione sta nell'**ordine di lettura** di `rapporto()`: `server_status()` per primo, perché
esegue un comando e quindi obbliga il driver a una selezione, cioè a guardare; `topology()` per
ultimo. L'ordine di lettura è l'opposto dell'ordine di stampa, e non è un caso — il che lo rende
esattamente il tipo di dettaglio che il prossimo refactoring cancella per errore. Perciò c'è una
prova che conta l'ordine delle chiamate:

```python
def test_il_rapporto_guarda_la_topologia_per_ultima() -> None:
    doppio: ClusterInspector = IspettoreCheRicorda()
    rapporto(doppio, titolo="rs")
    assert doppio.chiamate[0] == "server_status"
    assert doppio.chiamate[-1] == "topology"
```

Validata con una mutazione deliberata: rimettendo `topology()` per prima, diventa rossa.

---

## L'orologio, che era una porta senza casa

Il Task 11 ha chiuso anche una riga rimasta aperta dal capitolo 2: `Clock` esisteva come porta e
come doppio, `FakeClock` nelle prove, e in produzione nessuno. La radice di composizione doveva
iniettare qualcosa, e l'implementazione ovvia è una riga: `datetime.now().astimezone()`.

Quella riga è sbagliata, e leggendola non si vede perché. `Clock` serve a due cose che sembrano una
sola: **datare** un evento — `WriteSucceeded.istante` finisce in cronaca al millesimo — e
**misurare** una durata, perché `WorkloadRunner._scrivi` sottrae due `now()` e chiama il risultato
latenza. Datare vuole l'ora vera; misurare vuole che il tempo non torni indietro. L'orologio da
parete dichiara `monotonic=False`, cioè per contratto non promette la seconda
([M-030](Sources.md#m-030)).

Un salto all'indietro non solleva niente. Produce una **latenza negativa** che entra nei percentili
e una pazienza che non scade: numeri plausibili, proiettati in sala. È la stessa forma di guasto
dell'`E11000` di poco fa, ed è la forma che questo progetto ha imparato a temere più delle
eccezioni.

`SystemClock` legge il muro **una volta sola**, alla costruzione, e da lì in poi somma a
quell'ancora il tempo trascorso secondo `time.monotonic()`:

```python
def now(self) -> datetime:
    return self._ancora + (self._monotono() - self._zero) * UN_SECONDO
```

Gli istanti sono ore vere — si leggono accanto all'orologio in fondo alla sala — e le loro
differenze sono durate vere, perché vengono tutte dallo stesso contatore che non torna indietro.
L'ancora è nel **fuso locale** e non in UTC: la cronaca stampa `%H:%M:%S.mmm` senza nome di zona, e
a Ancona due ore di scarto dall'orologio della sala sarebbero la prima domanda del pubblico
([ADR-0086](../../docs/Decision.md#adr-0086)).

Il prezzo è dichiarato: l'ancora non viene mai ricorretta, quindi dopo un'ora di processo l'istante
riportato deriva di quanto i due orologi divergono — millisecondi, su un portatile. Per una scena di
minuti è invisibile; per un demone sarebbe la scelta sbagliata, e questo non è un demone. La riserva
vera è la sospensione, che `mach_absolute_time()` non conta: chi presenta non chiude il coperchio.

---

## Che cosa questo capitolo lascia aperto

- **Il ciclo di `watch` vive in `cli.py`.** È orchestrazione dentro una radice di composizione, cioè
  un po' più di quanto il §6.1 le assegni. Si sposta in `application/scenari.py` al Task 13, ed è
  scritto nella docstring perché si veda invece di sedimentare.
- **`lab.carico-*` non è distribuita, sullo stack 03.** `init/30-dati-demo.js` distribuisce solo
  `lab.ordini` su `{_id: "hashed"}`; una collezione creata al volo resta intera sullo shard primario
  del database. Il confronto fra architetture del Task 16 dovrà o distribuirla, o dichiarare che sta
  misurando un solo shard. È la prima cosa che quel task deve decidere.
- **`TOPOLOGIA singola → singola`** compare in cronaca ed è vera senza essere utile: il ponte la
  emette perché la *descrizione* della topologia è cambiata — dentro c'è il server che ha cambiato
  ruolo — mentre la forma no. Si chiude decidendo che cosa quella riga debba dire.
- **Il `--target rs` di oggi è `directConnection=true`,** cioè il punto di vista dell'host. Al Task
  12 l'applicazione entra nella rete Compose e questa mappa cambia.
- **`rapporto()` riceve la porta invece dei valori già letti,** ed è il motivo per cui l'ordine
  delle interrogazioni è affar suo. Funziona, ed è un accoppiamento in più di quanto servirebbe: chi
  volesse comporre un rapporto da dati raccolti altrove oggi non può.
- **Le letture fallite si contano ma non emettono nessun evento.** Nel consuntivo compaiono; in
  cronaca no. Per una demo in cui le letture continuano durante un failover, potrebbero doverci
  comparire.

---

**Fonti e decisioni citate:** [ADR-0086](../../docs/Decision.md#adr-0086),
[ADR-0087](../../docs/Decision.md#adr-0087), [ADR-0088](../../docs/Decision.md#adr-0088),
[ADR-0089](../../docs/Decision.md#adr-0089); nel registro di questa applicazione
[M-018](Sources.md#m-018), [M-019](Sources.md#m-019), [M-030](Sources.md#m-030),
[M-031](Sources.md#m-031), [M-032](Sources.md#m-032), [M-033](Sources.md#m-033) e
[M-034](Sources.md#m-034).
