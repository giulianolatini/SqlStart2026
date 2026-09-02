# 2. Le porte: `Protocol` strutturali, e doppi che non sono finzioni

> Il principio in una riga: **un oggetto soddisfa una porta perché ha i metodi giusti, non perché
> l'ha ereditata.** E chi verifica che li abbia davvero è mypy, non `isinstance`.

## Le cinque porte

Il dominio dichiara cinque interfacce. Sono i soli punti in cui `mongolab` tocca il mondo.

| Porta | Metodi | A che cosa serve |
|---|---|---|
| `DocumentStore` | `insert_many`, `find_page`, `count`, `aggregate` | leggere e scrivere documenti |
| `ClusterInspector` | `topology`, `server_status`, `db_stats`, `shard_distribution` | guardare com'è fatto il cluster e come sta |
| `BackupTool` | `dump`, `restore` | dump e restore come operazioni lunghe che raccontano come procedono |
| `EventSink` | `emit` | dove finiscono gli eventi |
| `Clock` | `now`, `sleep` | il tempo, come dipendenza invece che come fatto |

Stanno in `app/src/mongolab/domain/porte.py`, e sono `typing.Protocol`.

## Perché `Protocol` e non una classe base astratta

Con una `ABC` il verso della dipendenza si ribalta proprio dove non deve. Un doppio scritto in
`tests/` dovrebbe fare `class InMemoryStore(DocumentStore)`, cioè **importare il dominio per
conformarsi a lui**. Funziona, ma il legame è nominale: la conformità dipende dalla parentela
dichiarata.

Con un `Protocol` la conformità è **strutturale**. La documentazione di Python la chiama duck
typing statico: le classi che li usano «are primarily used with static type checkers that recognize
structural subtyping (static duck-typing)», in contrapposizione al modello nominale di PEP 484,
dove «a class `A` is allowed where a class `B` is expected **if and only if** `A` is a subclass of
`B`» ([A-001](Sources.md#a-001)). Mypy dice la stessa cosa dal proprio lato: nel suo esempio una
classe soddisfa il protocollo perché «defines a compatible close method», senza ereditarlo e senza
importarlo ([A-003](Sources.md#a-003)).

In pratica: è il dominio a descrivere la forma, e chiunque l'abbia va bene. Un doppio non ha
bisogno di sapere che il dominio esiste. Un adattatore neppure — anche se in questo progetto
l'adattatore vero il dominio lo importa comunque, perché ne usa i modelli.

Questo non è un risparmio di una riga. È la ragione per cui il diagramma di
[01-architettura-esagonale.md](01-architettura-esagonale.md) resta vero anche dentro la suite di
prove, che è il posto in cui le architetture di solito cedono per prime.

## Il prezzo, e chi lo paga

La conformità strutturale ha un difetto evidente: **non si vede**. Guardando una classe non si
capisce a quale porta risponde, e un doppio con una firma sbagliata non protesta al momento in cui
lo si scrive.

Per questo, in questo progetto, `mypy --strict` non è un accessorio: è **l'unico posto** in cui la
conformità è verificata. Senza di lui, `Protocol` sarebbe documentazione.

Il modo in cui `mongolab` chiede a mypy di controllare è quello che la documentazione di mypy
descrive come alternativa all'ereditarietà: **assegnare a una variabile annotata**.

```python
orologio: Clock = OrologioDiProva()      # ← qui mypy verifica le firme
```

Se `OrologioDiProva` sbagliasse un parametro, `make app-check` fallirebbe su quella riga. La prova
`test_un_oggetto_qualunque_soddisfa_la_porta_senza_ereditarla` esiste anche per questo: la sua
asserzione a runtime verifica il comportamento, ma la riga che conta è l'annotazione.

## `runtime_checkable`, e il buco che ha

Le cinque porte sono decorate con `@runtime_checkable`. Serve a una cosa sola: permettere a una
prova di mostrare che a un oggetto incompleto **la porta si chiude**.

```python
class OrologioMonco:
    def now(self) -> datetime: ...

assert not isinstance(OrologioMonco(), Clock)     # ✓ respinto
```

Ma il decoratore fa molto meno di quanto sembri, ed è scritto in entrambe le fonti. Python:
«`@runtime_checkable` will check only the presence of the required methods or attributes, **not
their type signatures or types**» ([A-001](Sources.md#a-001)). Mypy, ancora più diretto:
«`isinstance()` with protocols is not completely safe at runtime. For example, **signatures of
methods are not checked**» ([A-003](Sources.md#a-003)).

Misurato qui, sulla versione installata ([M-004](Sources.md#m-004)):

```
firma sbagliata, isinstance: True      ← passa, e non dovrebbe
metodo mancante, isinstance: False     ← respinto, correttamente
```

Un orologio con `sleep(self)` — senza il parametro `secondi` — supera il controllo a runtime e
fallirebbe al primo uso.

**Nel repository questo limite è scritto come prova che passa, non come commento.** In
`test_dominio.py` c'è una prova che costruisce l'oggetto con la firma sbagliata e asserisce che
`isinstance` lo accetti. È verde, ed è verde apposta: documenta il buco dove il lettore lo incontra,
e sarebbe la prima a fallire il giorno in cui Python stringesse la regola. Un commento, al posto
suo, invecchierebbe in silenzio. È la nota di metodo 145 del
[registro operativo](../../docs/registro-operativo-sviluppo.md).

## I doppi non sono mock

Al Task 4 del [piano](../../docs/00-progetto/2026-09-02-piano-feature-04-app-python.md) arrivano
cinque doppi: `InMemoryStore`, `FakeInspector`, `FakeBackup`, `FakeClock`, `RecordingSink`. La
regola che li governa è dichiarata prima che esistano, perché è il punto in cui una suite di prove
smette di provare qualcosa.

**Un doppio implementa il comportamento; un mock registra le chiamate.** `InMemoryStore` conserva
davvero i documenti: `insert_many` li mette in una lista, `count` la conta, `find_page` la impagina.
Se una prova ha bisogno di una pipeline di aggregazione che il doppio non sa eseguire, la si
**aggiunge** — non la si finge restituendo il risultato atteso.

La differenza si vede quando il codice sotto prova cambia. Un mock configurato per rispondere a
`insert_many(documenti)` continua a rispondere anche se il caso d'uso ha smesso di contare bene:
verifica che una chiamata sia avvenuta, non che il risultato sia giusto. Un doppio che conserva
davvero i documenti fallisce, perché il conteggio non torna.

C'è una seconda ragione, specifica di questo progetto: i doppi vengono scritti **prima** dei casi
d'uso che devono verificare. Scriverli dopo significherebbe modellarli sull'implementazione, che è
il modo più efficace di ottenere prove che non provano niente.

E una terza, che riguarda l'onestà del confronto: `mongolab` ha anche prove di integrazione contro
gli stack veri. Perché quel confronto abbia senso, il doppio deve parlare **la stessa lingua**
dell'adattatore — stessi tipi, stessi valori di ritorno. È la ragione per cui un documento, nel
dominio, è una `Mapping[str, object]` e non un tipo di pymongo: così le due implementazioni della
stessa porta sono confrontabili, e una prova scritta contro il doppio ha senso anche contro il
cluster.

## Una nota sui tipi: `object`, non `Any`

Nel dominio un documento è dichiarato così:

```python
type Documento = Mapping[str, object]
```

`object` e non `Any`, deliberatamente. `Any` spegne il controllo dei tipi in ogni punto che tocca:
un valore `Any` si può passare ovunque, chiamare, indicizzare, e mypy non dice niente. Un valore che
arriva da BSON è invece precisamente qualcosa di cui non sappiamo niente, e dirlo con `object`
costringe chi lo usa a **restringerlo esplicitamente** prima di farci qualcosa. Costa qualche riga
in più agli adattatori, e in cambio impedisce che l'ignoranza sul contenuto di un documento si
propaghi silenziosamente in tutto il resto del codice.

`Mapping` e non `dict` per la stessa famiglia di ragioni: è una vista in sola lettura, e chi riceve
un documento dal dominio non deve poterlo modificare in luogo.

---

**Da leggere dopo:** [03-eventi-immutabili.md](03-eventi-immutabili.md), che applica la stessa
diffidenza — verso ciò che sembra protetto e non lo è — agli oggetti che attraversano le porte.

**Fonti:** [A-001](Sources.md#a-001), [A-003](Sources.md#a-003), [M-004](Sources.md#m-004).
**Decisioni:** [ADR-0007](../../docs/Decision.md#adr-0007).
