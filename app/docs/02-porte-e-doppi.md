# 2. Le porte: `Protocol` strutturali, e doppi che non sono finzioni

> Il principio in una riga: **un oggetto soddisfa una porta perché ha i metodi giusti, non perché
> l'ha ereditata.** E chi verifica che li abbia davvero è mypy, non `isinstance`.

## Le sette porte

Il dominio dichiara sette interfacce. Sono i soli punti in cui `mongolab` tocca il mondo.

| Porta | Metodi | A che cosa serve |
|---|---|---|
| `DocumentStore` | `insert_many`, `find_page`, `count`, `aggregate` | leggere e scrivere documenti |
| `ClusterInspector` | `topology`, `server_status`, `db_stats`, `shard_distribution` | guardare com'è fatto il cluster e come sta |
| `QueryPlanner` | `explain` | come il router ha deciso di eseguire una query |
| `BackupTool` | `dump`, `restore` | dump e restore come operazioni lunghe che raccontano come procedono |
| `Regia` | `ferma`, `riavvia`, `sospendi`, `risveglia` | far accadere il guasto, che non è cosa da applicazione |
| `EventSink` | `emit` | dove finiscono gli eventi |
| `Clock` | `now`, `sleep` | il tempo, come dipendenza invece che come fatto |

Stanno in `app/src/mongolab/domain/porte.py`, e sono `typing.Protocol`.

**Cinque erano quelle del disegno; due sono arrivate perché una scena non stava in piedi senza.**
`Regia` è nata al Task 13 da un'impossibilità — chi fa cadere un nodo non può essere il processo che
sta guardando il nodo cadere ([ADR-0095](../../docs/Decision.md#adr-0095)), e la pagina che la
racconta è [14](14-la-scena-del-failover-e-i-due-numeri.md). `QueryPlanner` è nata al Task 15
([ADR-0105](../../docs/Decision.md#adr-0105)) perché la scena dello sharding deve mostrare che cosa
il router ha **deciso** di fare di una query, e nessuna delle sei sapeva chiederlo:
`DocumentStore` scrive e legge documenti, `ClusterInspector` guarda il cluster e non una query.

Aggiungere `explain` a `DocumentStore` sarebbe stato più corto e sbagliato: una porta che tutti
implementano si sarebbe allargata per un bisogno che ha un chiamante solo, e i doppi in memoria
avrebbero dovuto promettere un piano che non hanno. Una porta si disegna guardando **chi la
chiama**. Che poi un solo adattatore — `PymongoStore` — ne soddisfi due non è un'eccezione da
giustificare: è ciò che si ottiene quando le porte sono strutturali e nessuno le eredita.

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

Le sette porte sono decorate con `@runtime_checkable`. Serve a una cosa sola: permettere a una
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

I cinque doppi sono arrivati al Task 4 del
[piano](../../docs/00-progetto/2026-09-02-piano-feature-04-app-python.md) e stanno in
`app/tests/doppi/`, uno per file: `InMemoryStore` (`archivio.py`), `FakeInspector`
(`ispettore.py`), `FakeBackup` (`backup.py`), `FakeClock` (`orologio.py`), `RecordingSink`
(`raccoglitore.py`). La regola che li governa era dichiarata prima che esistessero, perché è il
punto in cui una suite di prove smette di provare qualcosa.

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

### Dove il doppio non sa, solleva

`InMemoryStore` parla un dialetto piccolo e dichiarato: uguaglianza su campi di primo livello,
`$match`, `$limit`, `$count`. Tutto il resto — un `$gt`, un percorso puntato, uno stadio
sconosciuto — solleva `NonSupportato` **nominando ciò che non sa fare** e dicendo che cosa
farne: insegnarglielo insieme alla prova che lo verifica.

L'alternativa non è sollevare *meno*: è tacere. Un doppio che ignorasse un `$gt` che non capisce
restituirebbe tutti i documenti, e la prova che lo usa diventerebbe verde senza che nessuno abbia
scritto una riga di codice difettoso. **Un doppio che tace su ciò che non sa è più pericoloso di
uno che non c'è**, perché uno che non c'è lo si nota.

Che il rifiuto sia verificato quanto il comportamento si vede rompendo il doppio apposta. Con un
`_corrisponde` che restituisce sempre `True` — la rottura che un doppio permissivo produce davvero
— falliscono sette prove, e due di quelle sette falliscono con `DID NOT RAISE NonSupportato`:
[M-006](Sources.md#m-006). La stessa misura mostra il limite del metodo, perché una rottura
scoperta si trova al secondo tentativo, ed è annotata lì.

Per la stessa ragione `$group` **non** c'è. Nessuna prova l'ha ancora chiesto; il giorno in cui una
lo chiederà, arriverà lo stadio insieme a lei. Il messaggio d'errore lo dice per nome, così chi lo
incontra non deve indovinare se sia una dimenticanza o una scelta.

### Due divergenze da MongoDB, e due risposte diverse

Imitare un database significa scegliere, e in due punti la scelta ovvia in Python non è quella di
MongoDB. Le due risposte del doppio sono opposte, e il criterio che le distingue è se
un'implementazione giusta esista:

- **`{"campo": None}` lo sa fare.** Nel manuale, «The `{ metacritic : null }` query matches
  documents that contain the `metacritic` field with a `null` value **or** do not contain the
  `metacritic` field» ([A-006](Sources.md#a-006)). In Python `documento.get(chiave) is not None`
  indovina quella semantica e `chiave not in documento` la sbaglia: due righe ugualmente ovvie, di
  cui una è quella giusta. Si sceglie con la fonte in mano e con la prova accanto.
- **`{"campo": {...}}` senza operatori lo rifiuta.** MongoDB richiede «an *exact* match of the
  specified `<value>` document, **including the field order**», e avverte del rischio di
  «unpredictable behavior when used with a driver that does not use ordered data structures»
  ([A-007](Sources.md#a-007)). L'uguaglianza fra `dict` di Python l'ordine lo ignora: qui nessuna
  implementazione ovvia è quella giusta, e imitare male è peggio che dichiarare di non saper fare.

Ne resta una terza, che non si può né imitare né rifiutare: i documenti tornano nell'ordine di
inserimento, mentre MongoDB senza `sort` esplicito non promette **nessun** ordine. È scritta nella
docstring del doppio perché una prova che vi si appoggiasse passerebbe qui e potrebbe fallire al
Task 8 contro lo stack vero.

### Un doppio può sbagliare anche il *quando*

`FakeBackup.dump` registra la richiesta e **restituisce** un generatore costruito a parte, invece di
essere una funzione generatrice. È una riga che sembra uno stilismo e non lo è: «The execution
starts when one of the generator's methods is called» ([A-005](Sources.md#a-005)), quindi con
`yield from` nel corpo la chiamata non eseguirebbe niente — né la registrazione qui, né l'avvio di
`mongodump` nell'adattatore vero del Task 9. La porta promette che il dump *parte*, non che
partirebbe se qualcuno guardasse.

La parte che vale la pena ricordare è chi se ne accorge. Scritto nella forma sbagliata, il doppio
fa fallire **una** prova — quella che chiama `dump()` senza scorrerlo e controlla che la richiesta
sia stata registrata — mentre `mypy --strict` resta verde: le due forme hanno lo stesso tipo
annotato, `Iterator[Progress]` ([M-007](Sources.md#m-007)). Insieme a [M-004](Sources.md#m-004) fa
un promemoria in due direzioni: mypy è l'**unico** posto in cui la conformità alle porte è
verificata, e non verifica tutto.

### Ogni doppio porta la sua prova

`tests/unit/test_doppi.py` verifica la promessa di ciascuno, non la sua implementazione: che
`InMemoryStore` ritrovi ciò che ha accettato, che `FakeClock` distingua «ha dormito» da «il tempo è
passato», che `FakeInspector` resti sull'ultima topologia invece di esaurirsi, che `RecordingSink`
conservi gli eventi in ordine. Provare i doppi non è girare a vuoto: sono ciò su cui poggeranno le
prove dei Task 5 e 6, e un attrezzo di misura si tara prima di misurarci.

Ogni doppio ha poi una prova a sé, `…_passa_per_la_porta`, il cui corpo è quasi vuoto perché tutto
il lavoro lo fa una riga che sembra ridondante e non lo è:

```python
archivio: DocumentStore = InMemoryStore()
```

L'annotazione è il punto in cui la conformità strutturale viene verificata davvero, da
`mypy --strict` ([A-003](Sources.md#a-003)). Nessun doppio eredita la sua porta e nessuno la
importa per conformarsi; senza quella riga, un doppio potrebbe allontanarsi dalla porta senza che
niente lo dica — e [M-004](Sources.md#m-004) mostra che `isinstance` non lo direbbe.

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
