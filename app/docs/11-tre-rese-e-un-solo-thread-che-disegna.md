# 11. Tre rese dello stesso flusso, e un solo thread che disegna

> Il principio in una riga: **se una resa ha bisogno di un dato che le altre non ricevono, il
> difetto è nell'evento, non nel sink** — e il corollario, scoperto per strada: una promessa
> architetturale mantenuta per caso non è mantenuta.

Fino al [capitolo 10](10-processi-esterni-e-il-verdetto-che-manca.md) l'applicazione ha prodotto
fatti. Otto specie di evento congelate al Task 2 e una nona aggiunta al Task 7, un generatore
di carico che le emette, un osservatore della topologia, un ponte SDAM, due adattatori veri. Nessuno di questi ha mai deciso
come un fatto si guarda: la porta `EventSink` ha un metodo solo, `emit`, e chi la implementa può
fare quello che vuole.

Questo capitolo scrive tre implementazioni. `RichTui` disegna una schermata che si aggiorna,
`PlainSink` scrive righe di testo, `NullSink` non fa niente. Sono tre risposte diverse alla stessa
domanda, e la parte interessante non è nessuna delle tre: è il vincolo che le tiene insieme, e una
promessa scritta in un ADR che si è scoperta falsa mentre la si manteneva.

---

## Perché tre, e perché non due o quattro

Ogni resa esiste per un momento preciso del 18 settembre.

**`RichTui` è la sala.** Il pubblico guarda uno schermo mentre un primario cade, e deve vedere il
cluster ricomporsi in tempo reale. È l'unica delle tre che il pubblico vedrà, se tutto va bene.

**`PlainSink` è il piano B, e il dopo.** Le registrazioni asciinema del Task 18 si girano con
`--sink plain` dentro `tools/registra-terminale.py` ([ADR-0050](../../docs/Decision.md#adr-0050)):
se la rete della sala non collabora, la registrazione va in proiezione al posto della dimostrazione
dal vivo. Serve anche a chi reindirizza su file per rileggere i tempi con calma dopo.

**`NullSink` è la misura.** Al Task 16 la domanda sarà quanto costa il carico, non quanto costa
raccontarlo. Un sink che accumulasse sposterebbe la misura di quello che accumula.

Quattro sarebbero troppe e due troppo poche per una ragione sola: sono i tre momenti in cui il
progetto ha davvero bisogno di guardare gli stessi eventi con occhi diversi. Il quarto sink esiste
già ed è `RecordingSink`, il doppio del Task 4, che vive nelle prove e non in produzione.

---

## Il vincolo che li tiene insieme, e come si rompe

Il Passo 3 del piano lo scrive così: «sono tre rese dello stesso flusso di eventi: se una ha
bisogno di un dato che le altre non ricevono, il difetto è nell'evento, non nel sink».

È una frase che sembra ovvia e non lo è. Il modo naturale di scrivere una TUI è chiedere al codice
che la chiama qualcosa in più — un titolo, un contesto, un totale — perché la TUI ha spazio e il
testo no. Ogni volta che quel «qualcosa in più» passa da un canale che non sia l'evento, le tre
rese smettono di essere tre rese: diventano tre applicazioni, e due di loro raccontano una scena
più povera senza che nessuno l'abbia deciso.

La prova che tiene in piedi la frase è `test_i_tre_sink_sono_tre_rese_dello_stesso_flusso`: manda la
stessa sequenza a `PlainSink`, a `RecordingSink` e a una `Scena`, e pretende che le righe prodotte
coincidano. Non confronta pixel: confronta il **contenuto**, che è la cosa che deve essere la
stessa.

La rottura tipica, quando arriva, non si presenta come una violazione della regola. Si presenta
come un parametro in più nel costruttore di un sink.

---

## Cento per trenta, e perché non lo decide questo capitolo

Il Passo 2 chiede testo grande e leggibile dall'ultima fila, e dice che è «un requisito di sala,
non di gusto». La parte interessante è la seconda metà: «va deciso adesso perché condiziona quante
righe stanno in una schermata».

Il testo grande in sala lo fa il terminale, non l'applicazione. Nessuna riga di Python può
ingrandire un carattere sul proiettore. Ciò che l'applicazione può decidere è **quanto poco spazio
occupare**, ed è una decisione che qualcun altro aveva già preso in questo repository:

```python
# tools/registra-terminale.py
COLONNE = 100
RIGHE = 30
```

con la ragione scritta accanto — «una registrazione di riserva va proiettata, e 100x30 sta su uno
schermo da sala senza che il testo vada a capo dove non deve». I file `.cast` già registrati lo
confermano nella loro intestazione: `"width": 100, "height": 30`.

Quindi il budget non si inventa qui, si eredita. E siccome il Task 18 girerà le registrazioni con
`--sink plain` **dentro** quello strumento, una schermata più alta di trenta righe non si vedrebbe
intera proprio nel piano B — cioè nel momento in cui non c'è modo di rimediare.

L'aritmetica sta in `presentation/righe.py`, e sta lì perché la usano tutti e tre:

| Costante | Valore | Perché |
|---|---|---|
| `COLONNE_SALA` | 100 | ereditata da `tools/registra-terminale.py` |
| `RIGHE_SALA` | 30 | idem |
| `SERVER_MOSTRATI` | 3 | misurato ([M-029](Sources.md#m-029)): tanti ne vede un client |
| `ALTEZZA_INTESTAZIONE` | 7 | `4 + SERVER_MOSTRATI`: bordi, titolo, riga dei conteggi, separatore |
| `RIGHE_CRONACA` | 21 | quel che resta: `7 + 21 = 28`, e due righe restano al prompt |
| `LARGHEZZA_ETICHETTA` | 9 | `SCRITTURA`, la più lunga delle nove |

`test_la_schermata_sta_nelle_trenta_righe_della_registrazione` verifica i conti. È una prova su
delle costanti, il che sembra inutile finché non si prova a immaginare come si rompe: qualcuno
aggiunge una riga all'intestazione perché ci sta, e la cronaca perde una riga senza che nessuno se
ne accorga fino alla proiezione.

### Otto righe riservate a server che non esistono

La prima stesura di quella tabella diceva `SERVER_MOSTRATI = 8`, con questa giustificazione:
«due shard da due membri, tre config server, un `mongos`».

Sono due errori in una frase, e il secondo è quello che vale la pena raccontare.

Il primo è di conteggio: gli shard dello stack 03 hanno **tre** membri ciascuno, e i container
`mongo` del suo `compose.yaml` sono undici, non otto. Basta contarli.

Il secondo è un errore di modello. Quella frase conta i **container**, e l'intestazione della TUI
non mostra container: mostra la `TopologyDescription` che il driver espone. E la topologia che un
client vede attraverso un `mongos` **non contiene i membri degli shard**. Un client di un `mongos`
vede il `mongos`. La misura, sui tre stack accesi ([M-029](Sources.md#m-029)):

```
stack 01: tipo=singola  server=1     localhost:27017   standalone
stack 02: tipo=singola  server=1     localhost:27021   primario
stack 03: tipo=sharded  server=1     localhost:27117   router
```

e, sullo stack 02 lasciando che il driver scopra il set, tre — `mongo-rs-1`, `mongo-rs-2`,
`mongo-rs-3`. Tre è il caso peggiore.

I documenti per shard esistono, e si contano: ma passano da `$shardedDataDistribution`
([A-012](Sources.md#a-012)) e producono `ContoShard`, che è un modello diverso e non finisce in
quell'elenco. La frase sbagliata aveva unito due cose che il dominio tiene separate apposta.

Il costo dell'errore era di cinque righe. `ALTEZZA_INTESTAZIONE = 4 + SERVER_MOSTRATI`, e la
cronaca prende quel che avanza su trenta: otto invece di tre significava cinque righe di cronaca
perse per sempre, per fare spazio a server che non sarebbero mai comparsi. Corretto il numero, la
cronaca passa da sedici a **ventuno** righe.

### E se un giorno i server fossero cinque

Un replica set a cinque membri è legittimo, e non è nel lab solo perché il lab ha tre nodi. Il
pannello ha altezza fissa — se crescesse, la cronaca si accorcerebbe proprio quando il cluster si
scompone — quindi qualcosa andrebbe tagliato.

Tagliare in silenzio, qui, sarebbe la cosa peggiore possibile: chi guarda conta i server per
capire se il cluster è integro, e un elenco troncato senza dirlo si legge come **un cluster più
piccolo di quello che è**. Non è un difetto estetico: è un'informazione falsa data con sicurezza,
proiettata su uno schermo, mentre si sta spiegando come si legge lo stato di un cluster.

`server_da_mostrare` quindi mostra i primi due e scrive `… e altri 3` al posto del terzo. Sta in
`righe.py` e non dentro `RichTui` per la ragione di tutto questo capitolo: è una decisione, e le
decisioni si provano.

---

## Una riga per evento, e il taglio che dichiara di aver tagliato

`riga(evento)` traduce un fatto in una stringa. Il formato è fisso: istante al millesimo, etichetta
allineata, dettaglio.

```
09:30:00.123  SCRITTURA  1000 documenti in 12.3 ms
09:30:01.004  ERRORE     NotPrimaryError: not master (0 documenti)
09:30:01.108  RITENTO    tentativo 1 fra 100.0 ms — not master
09:30:03.550  TOPOLOGIA  ReplicaSetWithPrimary «rs0» — 3 server
```

Tre scelte meritano di essere raccontate.

**I millesimi ci sono perché la scena è fatta di tempi.** Un failover dura pochi secondi; una
cronaca al secondo intero mostrerebbe quattro righe con lo stesso orario e nessuna informazione su
cosa è successo prima di cosa. `_istante` costruisce il millesimo a mano —
`strftime("%H:%M:%S.")` più `microsecond // 1000` — invece di usare `%f`, che darebbe sei cifre.

**Il testo va appiattito prima di essere scritto.** Il campo `motivo` di un `WriteFailed` arriva da
PyMongo e può contenere ritorni a capo: una riga che va a capo da sola scardina sia la cronaca a
ventuno righe sia il conteggio delle righe della registrazione. `_appiattisci` fa
`" ".join(testo.split())`, che è la forma più corta per «collassa qualunque spazio bianco, tab e a
capo compresi».

**Il taglio si dichiara.** Quando la riga supera le cento colonne viene tagliata e chiusa con `…`,
e il risultato è lungo **esattamente** cento. La versione sbagliata di questa riga è
`intera[:larghezza] + TRONCAMENTO`, che produce centouno colonne e manda a capo proprio la riga che
si stava cercando di non mandare a capo. Chi vuole tutto il testo passa `larghezza=None`, ed è
quello che fa chi analizza un file dopo.

Una larghezza zero o negativa solleva `ValueError`. Il ripiego silenzioso, qui, sarebbe una riga
vuota per ogni evento: una cronaca che scorre senza dire niente, e nessuno che sappia perché.

### L'evento che nessuno ha previsto

`_etichetta_e_dettaglio` è un `match` sulle nove specie con un `case _:` finale che restituisce
`("IGNOTO", type(evento).__name__)`. È un ripiego, e i ripieghi silenziosi sono quello che questo
progetto evita — ma qui il silenzio è impossibile: la parola `IGNOTO` compare sullo schermo, in
sala, accanto al nome della classe che nessuno ha gestito.

La guardia vera è una prova. `test_ogni_evento_del_dominio_sa_diventare_una_riga` costruisce
un'istanza di ogni sottoclasse di `Evento` e pretende che nessuna produca `IGNOTO`; e comincia con
`assert len(sottoclassi_di_evento()) == 9`, così che aggiungere una decima specie faccia fallire la
prova invece di far comparire una riga sbiadita durante il talk.

---

## La scoperta: Rich apre un thread, e la documentazione non lo dice

[ADR-0019](../../docs/Decision.md#adr-0019) è una delle decisioni più antiche del progetto. Nasce
da [S-010](../../docs/Sources.md#s-010) — i listener di PyMongo sono consegnati in modo sincrono e
bloccano il thread del driver — e conclude che un ascoltatore deve costruire un fatto congelato,
metterlo in coda e ritornare. La frase che chiude l'ADR è:

> il ciclo di disegno gira sul thread principale — **un solo thread tocca `Live`**

e la ragione dichiarata per non fare altrimenti era una lacuna: la documentazione di `Live` non
nomina mai i thread ([S-018](../../docs/Sources.md#s-018)). Di fronte a una lacuna, il progetto ha
cambiato disegno invece di indovinare. È la scelta giusta, ed è stata presa per il motivo giusto.

Scrivendo questo capitolo la lacuna è stata guardata da vicino. Dentro `rich/live.py`:

```python
class _RefreshThread(Thread):
    """A thread that calls refresh() at regular intervals."""

    def __init__(self, live: "Live", refresh_per_second: float) -> None:
        self.live = live
        self.refresh_per_second = refresh_per_second
        super().__init__(daemon=True)

    def run(self) -> None:
        while not self.done.wait(1 / self.refresh_per_second):
            with self.live._lock:
                if not self.done.is_set():
                    self.live.refresh()
```

e in `Live.start()`, alla fine: `if self.auto_refresh: self._refresh_thread = _RefreshThread(...)`.

La misura ([M-027](Sources.md#m-027)) conta i thread vivi mentre il display è acceso:

```
predefinito:        [('Thread-1', '_RefreshThread', True)]
auto_refresh=False: []
```

Quindi ADR-0019 **non sarebbe stata mantenuta** dal codice che credeva di mantenerla. Due thread
toccavano `Live`: il nostro e quello di Rich.

Vale la pena essere precisi su che tipo di difetto è. Non è un difetto di correttezza: dentro
`Live` c'è un `RLock`, i due thread si sarebbero serializzati, e nessuna schermata sarebbe uscita
storta. È un difetto di **fondamento**. Il codice sarebbe stato corretto per una ragione che il
progetto non conosceva, appoggiata a un attributo privato di una libreria — cioè esattamente la
condizione da cui ADR-0019 diceva testualmente di volersi tenere alla larga. Una promessa mantenuta
per caso non è mantenuta: è una promessa che nessuno sta controllando.

La riga che la mantiene davvero è una:

```python
with Live(self._disegna(), console=self._console, auto_refresh=False, vertical_overflow="crop"):
```

La decisione, con le alternative scartate, è [ADR-0085](../../docs/Decision.md#adr-0085).

### Come si è arrivati a guardare

Vale la pena raccontarlo perché il metodo si riusa. La prima sonda ha contato i thread **dopo**
`live.stop()` e ne ha trovati zero — un risultato vero, che confermava la tesi sbagliata. Il thread
c'era stato per tutta la durata del display ed era già morto quando lo si è cercato. La domanda «ci
sono thread in più?» va posta nel momento in cui la risposta conta, non dopo.

---

## Il prezzo: un parametro che nessuno legge più

Il Passo 1 chiedeva che `refresh_per_second` fosse «passato esplicitamente, con il valore scritto
accanto alla ragione per cui è quello». Prima di scrivere una ragione accanto a un numero conviene
accertarsi che il numero faccia qualcosa. Non lo fa:

```
auto_refresh=False, refresh_per_second=1000, 0.5 s di attesa: 7 byte scritti
```

Sette byte in mezzo secondo con mille aggiornamenti al secondo richiesti, cioè niente. Spento
`auto_refresh`, `refresh_per_second` diventa inerte: nessuno lo legge più. Anche `update()` senza
`refresh=True` non disegna.

Passarlo comunque sarebbe stato decoro: la forma dell'esplicitezza senza la sostanza, e — peggio —
un commento che spiega da dove viene un ritmo che in realtà viene da un'altra parte. Il numero vive
quindi nel periodo del ciclo:

```python
RITMO_PREDEFINITO = 10.0
...
self._periodo = 1.0 / ritmo
```

**Questa è una deviazione dalla lettera del piano**, presa per onorarne l'intento, ed è dichiarata
qui perché il piano resta la sede in cui è scritto il contrario.

### Perché dieci

Due misure che guardano da lati opposti.

Verso il basso, il ritmo è il **ritardo massimo** fra un fatto e la sua comparsa. Dieci al secondo
sono cento millisecondi; i quattro predefiniti di Rich sarebbero duecentocinquanta, e in una scena
in cui i tempi sono il contenuto quel quarto di secondo si vede.

Verso l'alto, il costo. Ogni giro ridisegna la schermata intera, e chi disegna è lo stesso processo
che sta misurando il failover. Un disegno costa **0,76 ms** nel caso peggiore — tre server e
cronaca piena — su cinquecento giri e tre esecuzioni ([M-028](Sources.md#m-028)):

| Giri al secondo | Costo | Ritardo massimo |
|---|---|---|
| 4 (predefinito di Rich) | 0,3% di un core | 250 ms |
| **10** | **0,8%** | **100 ms** |
| 20 | 1,6% | 50 ms |
| 60 | 4,7% | 17 ms |

Il costo non è il vincolo: il ritardo sì. Dieci sta dove entrambi i lati restano piccoli senza che
nessuno dei due debba essere difeso.

### Un segnaposto che era già stato scritto

La docstring che giustifica `RITMO_PREDEFINITO` è stata scritta **prima** della misura, e diceva
«0,86 ms misurati», con una citazione a una fonte che non esisteva ancora. Il numero era plausibile
e sbagliato del 35%.

Vale la pena lasciarlo agli atti, perché è il modo in cui un repository con una regola sulle fonti
la viola: non scrivendo un numero senza fonte, ma scrivendo un numero **con** una fonte che si ha
intenzione di produrre dopo. Un numero assente si nota. Un numero inventato accanto a un codice
`M-0NN` ben formato non si nota affatto.

---

## Il divieto del Passo 4, letto due volte

Il Passo 4 dice: «Le prove della presentazione si fanno su `PlainSink` e `RecordingSink`, mai su
`RichTui`: provare il disegno significa provare Rich, che ha già le sue prove».

La regola è giusta. Il modo sbagliato di rispettarla è lasciare dentro `RichTui` della logica e poi
non provarla, con il divieto come alibi. Un divieto di provare qualcosa si onora **spostando
altrove ciò che va provato**, non rinunciando a provarlo.

Da qui la divisione della presentazione in cinque moduli, due dei quali non erano nell'elenco del
piano:

| Modulo | Che cosa fa | Conosce Rich |
|---|---|---|
| `righe.py` | un evento → una riga; il budget di sala | no |
| `scena.py` | la coda, i conteggi, la cronaca, l'ultima topologia | no |
| `plain.py` | scrive le righe su un flusso | no |
| `null.py` | niente | no |
| `rich_tui.py` | un ciclo di cinque righe e un disegno | **sì, ed è l'unico** |

`scena.py` è la metà di `RichTui` che non sa disegnare, ed è la parte che vale la pena provare:
`emit` deposita in una `queue.Queue` e ritorna senza toccare lo stato — perché chi chiama può
essere un thread qualunque — e `assorbi` svuota la coda dentro lo stato, senza mai bloccare. Un
`assorbi` che aspettasse rimetterebbe il disegno alla mercé del driver, cioè invertirebbe di nuovo
la dipendenza che ADR-0019 aveva raddrizzato.

La regola che tiene in piedi tutto il resto è una prova che legge i sorgenti:

```python
assert trovati == {"rich_tui.py": {"rich"}}
```

Se Rich entrasse in `plain.py` o in `scena.py`, due cose cadrebbero insieme: le prove qui sopra
proverebbero Rich senza dirlo, e `--sink plain` — quello con cui si girano le registrazioni e si
misura al Task 16 — si porterebbe dietro la TUI che dichiara di non usare.

### Il giro di rotture, e le due che sono sopravvissute

Come agli altri task, il codice è stato rotto un pezzo per volta per vedere se le prove
protestavano. Undici mutazioni: la riga che non tronca mai, quella che tronca una colonna oltre, i
millesimi persi, la cronaca senza tetto, la topologia sbagliata, il `flush` tolto, gli `__slots__`
tolti. Nove scoperte.

Due sopravvissute, e stavano tutte e due in `rich_tui.py`:

1. `auto_refresh=True` — cioè la riga che mantiene ADR-0019, rimessa com'era prima della scoperta;
2. l'ultimo `aggiorna()` dopo il ciclo, tolto.

Il fatto che sopravvivessero era la conseguenza diretta del Passo 4 letto in modo largo. Ma nessuna
delle due è disegno. La prima è **quanti thread esistono**; la seconda è **se la coda è vuota
quando il ciclo finisce**. Si osservano entrambe senza guardare un pixel:

```python
prima = set(threading.enumerate())
with tui.acceso():
    durante = set(threading.enumerate())
assert durante - prima == set()
```

e, per la seconda, `tui.esegui(finche)` con un `finche` che emette un evento proprio quando decide
di restituire `False`, poi `assert tui.in_coda == 0`. L'ultimo `aggiorna()` fuori dal ciclo non è
pignoleria: in ogni scenario l'evento finale — il primario ritrovato, il restore concluso — è
proprio quello che il pubblico deve leggere.

Con le due prove aggiunte, **undici mutazioni su undici** vengono scoperte.

La lezione è sul modo di leggere un divieto. «Non provare il disegno» non vuol dire «non provare
niente di quel modulo»: le uniche due righe di `rich_tui.py` che il resto del progetto **cita** —
una in un ADR, una in ogni scenario — erano anche le uniche senza guardia.

---

## Le tre rese, una per volta

### `PlainSink`: il `flush` non è prudenza, è il contenuto

```python
def emit(self, evento: Evento) -> None:
    self._flusso.write(riga(evento, larghezza=self._larghezza) + "\n")
    self._flusso.flush()
```

Python bufferizza a blocchi quando la destinazione non è un terminale — cioè in
`--sink plain > file` e in ogni tubo. Senza svuotare, la cronaca di un failover comparirebbe tutta
insieme a failover concluso: non si perderebbe un byte, si perderebbero i **tempi**, che in queste
scene sono la cosa che si sta mostrando.

La prova apre il file una seconda volta **dentro** il `with` e legge: se il buffer non fosse
svuotato, il secondo lettore non vedrebbe niente.

La larghezza predefinita è quella di sala e non `None`, e la ragione è la stessa di prima: la
registrazione di riserva deve mostrare quello che il pubblico avrebbe visto. Una registrazione più
informativa dello schermo dal vivo racconterebbe un'altra scena.

### `NullSink`: la promessa è che non cresca

```python
class NullSink:
    __slots__ = ()

    def emit(self, evento: Evento) -> None:
        return None
```

Gli `__slots__` vuoti rendono **impossibile** attaccare un attributo a un'istanza, e quindi
impossibile che un contatore aggiunto distrattamente un giorno trasformi il sink neutro delle
misure in qualcosa che cresce con il carico. È l'unica promessa che questa classe fa, ed è l'unica
che una prova può verificare senza cronometrare niente:

```python
with pytest.raises(AttributeError):
    sink.contati = 1  # type: ignore[attr-defined]
```

Questa prova è nata da un errore di mypy. La versione precedente era
`assert sink.emit(evento) is None`, che mypy rifiuta — leggere il valore di una chiamata dichiarata
`-> None` è un errore, e giustamente. La prova sostitutiva è più forte di quella che sostituiva.

### `RichTui`: il pannello che non si accorcia quando serve

L'intestazione ha altezza **fissa**, non elastica. Se il pannello crescesse con il numero di
server, la cronaca si accorcerebbe da sola nel momento peggiore — quando il cluster si scompone e
le righe da leggere sono tante. `vertical_overflow="crop"` completa la difesa: senza, una schermata
più alta del terminale scorrerebbe, e una TUI che scorre in sala non è più una TUI.

Il numero degli eventi in coda si mostra **solo se non è zero**. È il numero che dice che il
disegno è rimasto indietro; a zero occuperebbe spazio per dire che va tutto bene.

---

## Una nota sulle prove che si sono spostate

Tre funzioni hanno cambiato casa e sono finite in `tests/aiutanti.py`: `moduli_importati`,
`estranei` e `sottoclassi_di_evento`. Erano definite dentro `test_scheletro.py` e
`test_dominio.py`, dove servivano a una guardia sola; adesso servono a due, e una funzione che
serve a due guardie duplicata in due file diventa due funzioni diverse alla prima modifica.

Il costo è che tre file di prova sono stati toccati fuori dall'elenco del piano. È dichiarato qui
per lo stesso motivo per cui è dichiarata la deviazione su `refresh_per_second`.

---

## Che cosa questo capitolo lascia aperto

**`PlainSink` non gestisce `BrokenPipeError`.** `mongolab --sink plain | head -20` chiude il tubo
dopo venti righe e la ventunesima solleva. Non è gestito perché la gestione giusta non è ovvia —
uscire in silenzio? con quale codice? — e perché è la stessa classe di problema del
`BrokenPipeError` lasciato aperto al [capitolo 10](10-processi-esterni-e-il-verdetto-che-manca.md).
Vale la pena deciderli insieme.

**`SystemClock` non esiste ancora.** `RichTui` riceve un `Clock` dalla porta e nelle prove riceve
`FakeClock`; l'implementazione vera arriva al Task 11 con il composition root. Finché non c'è, la
TUI non è avviabile davvero.

**Nessuna prova guarda che cosa Rich disegna,** ed è voluto. Il primo sguardo vero sulla schermata
sarà una registrazione asciinema del Task 18, ed è lì che si scoprirà se sette righe di
intestazione siano troppe o poche.

**Il costo del disegno è misurato su `StringIO`.** Un terminale vero aggiunge il costo di scrivere
sul tty, che non è stato misurato. Se al Task 18 la registrazione risultasse a scatti, è il primo
posto in cui guardare.

**`_RefreshThread` è privato.** Se una versione futura di Rich lo rinominasse, la guardia
continuerebbe a valere perché conta i thread invece di nominare la classe; se ne cambiasse il
comportamento, fallirebbe. È l'ordine giusto fra le due cose, ma vale la pena saperlo prima di
aggiornare la libreria alla vigilia del talk.

---

**Torna a:** [README.md](README.md) per l'indice ·
[capitolo 4](04-eventi-del-driver-e-concorrenza.md) per la decisione sui thread che questo capitolo
ha dovuto correggere · [capitolo 10](10-processi-esterni-e-il-verdetto-che-manca.md) per
l'adattatore che attraversa un confine di sistema operativo.
