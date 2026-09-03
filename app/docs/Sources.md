# Fonti dell'applicazione

Le fonti da cui viene ciò che `mongolab` fa, e il modo in cui lo fa.

## Perché questo registro è separato

Il repository ha già un registro di fonti, [`docs/Sources.md`](../../docs/Sources.md), ed è quello
canonico: raccoglie le fonti su **MongoDB** — il server, il protocollo, gli strumenti, le
immagini — ed è legato a [`docs/Decision.md`](../../docs/Decision.md) da un controllo automatico
che pretende che ogni fonte sia citata da almeno un ADR e che ogni ADR dichiari le proprie fonti
([ADR-0038](../../docs/Decision.md#adr-0038)).

Le fonti di questa pagina sono di un'altra natura: riguardano **il linguaggio e gli strumenti con
cui l'applicazione è scritta** — `dataclasses`, `typing.Protocol`, mypy, pytest. Nessun ADR le
cita, perché non decidono niente sull'architettura MongoDB del lab: decidono come si scrive il
codice che quell'architettura la mostra. Metterle nel registro canonico le renderebbe **orfane**, e
il controllo fallirebbe — a ragione, perché starebbero nel posto sbagliato. Questa pagina è la sede
che mancava, non un'eccezione alla regola.

**Le due sedi non si sovrappongono e non si copiano.** Quando una pagina di `app/docs/` ha bisogno
di una fonte canonica — la consegna sincrona degli eventi di PyMongo, il comportamento di `Live` di
Rich, le opzioni della stringa di connessione — la cita con il suo codice originale e un
collegamento a `docs/Sources.md`. Non se ne fa una copia qui: una fonte duplicata è una fonte che
prima o poi diverge, e a quel punto nessuna delle due è affidabile.

## Come si leggono i codici

| Prefisso | Che cos'è | Dove sta |
|---|---|---|
| `A-0NN` | una fonte esterna letta per scrivere l'applicazione | in questa pagina |
| `M-0NN` | una misura eseguita in questo repository, con comando e output | in questa pagina |
| `S-0NN` | una fonte ufficiale su MongoDB e dintorni | in [`docs/Sources.md`](../../docs/Sources.md) |
| `V-0NN` | una verifica empirica sul lab | in [`docs/Sources.md`](../../docs/Sources.md) |

Ogni voce `A-` porta **URL, editore, versione documentata, data di consultazione, che cosa afferma
davvero** e — quando c'è — la **riserva**: il punto in cui la pagina *non* dice quello che si
vorrebbe farle dire. La riserva non è una formalità. Più d'una, fra le dieci fonti qui sotto, tace
proprio sul punto per cui la si era aperta, e la cosa si scopre solo leggendole.

Ogni voce `M-` porta il **comando** e l'**output testuale**, così che chiunque possa rifarla. Le
misure valgono per l'ambiente descritto in [M-001](#m-001) e per nessun altro.

---

## Fonti esterne

<a id="a-001"></a>
### A-001 — Python: `typing` — `Protocol` e `runtime_checkable`

- **URL:** https://docs.python.org/3/library/typing.html#typing.runtime_checkable
- **Editore:** Python Software Foundation — documentazione ufficiale della libreria standard
- **Versione documentata:** Python 3.14.7 (il canale `/3/` segue l'ultima versione pubblicata)
- **Consultata:** 2026-09-02
- **Verdetto:** conferma, con una riserva sulla versione
- **Cosa afferma:** i `Protocol` servono al **sottotipaggio strutturale**, cioè al duck typing
  statico: «Such classes are primarily used with static type checkers that recognize structural
  subtyping (static duck-typing)», in contrapposizione al nominale di PEP 484, dove «a class `A` is
  allowed where a class `B` is expected if and only if `A` is a subclass of `B`». Un `Protocol` non
  decorato **non** si può usare a runtime: «Protocol classes without this decorator cannot be used
  as the second argument to `isinstance()` or `issubclass()`». Con il decoratore diventano
  «simple-minded runtime protocols that check only the presence of given attributes, ignoring their
  type signatures», e la nota esplicita è la frase che questo progetto cita più spesso:
  «`@runtime_checkable` will check only the presence of the required methods or attributes, **not
  their type signatures or types**». La pagina porta il proprio esempio di falso positivo:
  `ssl.SSLObject` supera un `issubclass()` contro `Callable` benché il suo `__init__` esista solo
  per sollevare `TypeError`. Due cambiamenti recenti da conoscere: dalla 3.12 il controllo
  `isinstance()` usa `inspect.getattr_static()` invece di `hasattr()`, e i membri di un protocollo
  runtime-checkable sono «frozen at runtime as soon as the class has been created». C'è infine un
  avviso di prestazioni: «An `isinstance()` check against a runtime-checkable protocol can be
  surprisingly slow compared to an `isinstance()` check against a non-protocol class.»
- **Riserve:** due. La prima è di versione: la pagina documenta la **3.14.7**, mentre il progetto
  gira su **3.13.15** ([M-001](#m-001)) con un tetto dichiarato `<3.14`. Le affermazioni citate qui
  non sono marcate come novità posteriori alla 3.12, quindi valgono anche sulla 3.13, ma è una
  deduzione dai marcatori di versione della pagina e non una frase della pagina. La seconda: **la
  pagina non dice niente** sul divieto di `issubclass()` contro protocolli con membri non-metodo.
  La restrizione esiste ed è in PEP 544, ma non è qui, e nessuna affermazione di questo repository
  ci si appoggia.
- **Usata da:** [02-porte-e-doppi.md](02-porte-e-doppi.md)

<a id="a-002"></a>
### A-002 — Python: `dataclasses`

- **URL:** https://docs.python.org/3/library/dataclasses.html
- **Editore:** Python Software Foundation — documentazione ufficiale della libreria standard
- **Versione documentata:** Python 3.14.7 (modulo introdotto nella 3.7)
- **Consultata:** 2026-09-02
- **Verdetto:** conferma parziale — la regola più importante per questo progetto **non c'è**
- **Cosa afferma:** l'immutabilità è dichiaratamente un'imitazione: «It is not possible to create
  truly immutable Python objects. However, by passing `frozen=True` to the `@dataclass` decorator
  you can emulate immutability. In that case, dataclasses will add `__setattr__()` and
  `__delattr__()` methods to the class. These methods will raise a `FrozenInstanceError` when
  invoked.» L'eccezione «is a subclass of `AttributeError`». C'è un costo dichiarato: «There is a
  tiny performance penalty when using `frozen=True`: `__init__()` cannot use simple assignment to
  initialize fields, and must use `object.__setattr__()`.» Su `slots`: «If true (the default is
  `False`), `__slots__` attribute will be generated and **new class will be returned instead of the
  original one**», il che contrasta con la regola generale del decoratore, «The decorator returns
  the same class that it is called on; no new class is created». Sull'ereditarietà dei campi: il
  decoratore «looks through all of the class's base classes in reverse MRO … and, for each
  dataclass that it finds, adds the fields from that base class to an ordered mapping of fields», e
  «Because the fields are in insertion order, derived classes override base classes» — è la ragione
  per cui in `mongolab` il campo `istante` della base resta sempre il primo parametro di ogni
  evento. Su `eq`: è vero per impostazione predefinita, «This method compares the class by
  comparing each field in order», e dalla 3.13 il confronto avviene campo per campo invece che
  costruendo tuple. Infine la combinazione che il progetto usa: «If _eq_ and _frozen_ are both
  true, by default `@dataclass` will generate a `__hash__()` method for you», quindi gli eventi
  congelati sono anche hashabili.
- **Riserve:** due lacune, entrambe rilevanti. La prima: **la pagina non enuncia la regola di
  ereditarietà fra dataclass congelate e non congelate.** La sezione «Inheritance» parla solo
  dell'ordine dei campi; l'unico `TypeError` legato a `frozen` che la pagina documenta è quello di
  una classe che definisce da sé `__setattr__`. Che CPython rifiuti una sottoclasse non congelata
  di una congelata è vero — è misurato in [M-002](#m-002) — ma **non risulta scritto qui**, e nel
  repository l'affermazione poggia sulla misura, non sulla pagina. La seconda: la pagina **non
  dice** che `slots=True` tolga il `__dict__` alle istanze; quel comportamento discende dalla
  semantica generale di `__slots__`, documentata altrove nel riferimento del modello dati. Anche
  qui l'affermazione del progetto poggia su una misura, [M-003](#m-003).
- **Usata da:** [03-eventi-immutabili.md](03-eventi-immutabili.md)

<a id="a-003"></a>
### A-003 — mypy: Protocols and structural subtyping

- **URL:** https://mypy.readthedocs.io/en/stable/protocols.html
- **Editore:** progetto mypy — documentazione su Read the Docs, canale `stable`
- **Versione documentata:** non numerata sulla pagina; nel progetto è installata mypy **2.3.1**
  ([M-001](#m-001))
- **Consultata:** 2026-09-02
- **Verdetto:** conferma — ed è la fonte che chiude il buco lasciato aperto da [A-001](#a-001)
- **Cosa afferma:** mypy sostiene entrambi i modelli. Il nominale è «strictly based on the class
  hierarchy»; lo strutturale è presentato come «the static equivalent of duck typing», con PEP 544
  come specifica di riferimento. La conformità **include le firme**, non i soli nomi: nell'esempio
  della pagina una classe soddisfa il protocollo perché «defines a compatible close method», senza
  ereditarlo e senza importarlo. Chi vuole un controllo esplicito ha due strade: ereditare il
  protocollo, il che «forces mypy to verify that your class implementation is actually compatible»,
  oppure assegnare a una variabile annotata con il tipo del protocollo — ed è la seconda che
  `mongolab` usa nelle prove. Sul controllo a runtime la pagina è netta, e la frase è quella che
  giustifica una prova verde apposta in `tests/unit/test_dominio.py`: «`isinstance()` with protocols
  is not completely safe at runtime. For example, **signatures of methods are not checked**.»
  Aggiunge che `issubclass()` guarda solo l'esistenza dei metodi, e ripete l'avviso di lentezza.
- **Riserve:** la pagina **non prende posizione** su dove vada dichiarato un protocollo rispetto a
  dove vivono le sue implementazioni. La scelta di questo progetto — le porte in `domain/`, gli
  adattatori in `infrastructure/`, i doppi in `tests/` — discende da
  [ADR-0007](../../docs/Decision.md#adr-0007) e dal disegno, non da questa fonte. La pagina la
  rende soltanto *possibile*, osservando che chi implementa non deve importare né ereditare nulla.
- **Usata da:** [02-porte-e-doppi.md](02-porte-e-doppi.md),
  [05-tipi-prove-e-guardie.md](05-tipi-prove-e-guardie.md)

<a id="a-004"></a>
### A-004 — pytest: Exit codes

- **URL:** https://docs.pytest.org/en/stable/reference/exit-codes.html
- **Editore:** progetto pytest — documentazione su Read the Docs, canale `stable`
- **Versione documentata:** non numerata sulla pagina; nel progetto è installata pytest **9.1.1**
  ([M-001](#m-001))
- **Consultata:** 2026-09-02
- **Verdetto:** conferma
- **Cosa afferma:** sette codici, ciascuno con un significato distinto. `0` «All tests collected
  passed successfully»; `1` «Tests collected run but tests failed»; `2` «Test execution interrupted
  by user»; `3` «Internal error happened while executing tests»; `4` «pytest command line usage
  error»; **`5` «No tests collected»**; `6` «Maximum number warnings exceeded». I codici sono API
  pubblica, rappresentati dall'enumerazione `pytest.ExitCode`, importabile con
  `from pytest import ExitCode`. Il `5` è il caso in cui la fase di raccolta non trova niente da
  eseguire: non è un fallimento, ed è distinto dall'`1`, che significa che le prove sono state
  eseguite e alcune sono fallite.
- **Riserve:** la pagina non dichiara la versione di pytest cui si riferisce, e il canale `stable`
  si sposta. Il significato del `5` è stato comunque **verificato qui** sulla versione installata:
  [M-005](#m-005).
- **Usata da:** [05-tipi-prove-e-guardie.md](05-tipi-prove-e-guardie.md)

<a id="a-005"></a>
### A-005 — Python: quando comincia a eseguire una funzione generatrice

- **URL:** https://docs.python.org/3/reference/expressions.html#yield-expressions
- **Editore:** Python Software Foundation — riferimento ufficiale del linguaggio
- **Versione documentata:** Python 3.14.7 (il canale `/3/` segue l'ultima versione pubblicata)
- **Consultata:** 2026-09-03
- **Verdetto:** conferma piena, ed è la frase su cui poggia la forma di `FakeBackup`
- **Cosa afferma:** chiamare una funzione generatrice **non esegue il suo corpo**. «When a generator
  function is called, it returns an iterator known as a generator. That generator then controls the
  execution of the generator function. **The execution starts when one of the generator's methods
  is called.** At that time, the execution proceeds to the first yield expression, where it is
  suspended again, returning the value of `yield_list` to the generator's caller». La sospensione
  conserva tutto: «all local state is retained, including the current bindings of local variables,
  the instruction pointer».
- **Conseguenza qui:** un `dump()` scritto come funzione generatrice non avvia niente finché
  qualcuno non scorre il risultato. Nell'adattatore vero del Task 9 vorrebbe dire che
  `mongodump` non parte alla chiamata; nel doppio vuol dire che la richiesta non viene registrata.
  La porta promette che qualcosa accade **alla chiamata**, quindi `FakeBackup.dump` registra subito
  e restituisce un generatore costruito a parte.
- **Riserve:** la pagina descrive il comportamento a **runtime** e non dice niente su come lo si
  distingua staticamente. È il punto che rende la cosa insidiosa, ed è misurato in
  [M-007](#m-007): una funzione generatrice e una funzione che restituisce un generatore hanno lo
  stesso tipo annotato, `Iterator[Progress]`, e `mypy --strict` non le distingue.
- **Usata da:** [02-porte-e-doppi.md](02-porte-e-doppi.md)

<a id="a-006"></a>
### A-006 — MongoDB: `{campo: null}` prende anche i documenti senza quel campo

- **URL:** https://www.mongodb.com/docs/manual/tutorial/query-for-null-fields/
- **Editore:** MongoDB, Inc. — Database Manual
- **Versione documentata:** 8.3 (canale «Current» del manuale)
- **Consultata:** 2026-09-03
- **Verdetto:** conferma — la semantica è dichiarata, non dedotta
- **Cosa afferma:** «The `{ metacritic : null }` query matches documents that contain the
  `metacritic` field with a `null` value **or** do not contain the `metacritic` field», e il
  risultato è descritto due volte perché non sia frainteso: «The query returns all documents in the
  `movies` collection where the `metacritic` field contains a `null` value or does not exist».
  Distinguere i due casi richiede altri operatori: `{ $type: 10 }` prende **solo** il `null`
  esplicito, `{ $exists: false }` **solo** il campo assente, `{ $ne: null }` i documenti dove il
  campo «exists **and** does not have a null value».
- **Conseguenza qui:** in `InMemoryStore._corrisponde`, per un valore atteso `None`, la condizione
  giusta è `documento.get(chiave) is not None` e non `chiave in documento`. Sono due righe
  ugualmente ovvie e una sola è quella di MongoDB: è il motivo per cui il doppio la implementa
  invece di rifiutarla, con la prova
  `test_l_archivio_cerca_i_campi_assenti_come_fa_mongodb` accanto.
- **Riserve:** tre. La prima è di versione: il lab gira su `mongo:7.0` (`tools/pull-images.sh`),
  la pagina documenta la 8.3; l'affermazione sui campi di primo livello non è marcata come novità di
  alcuna versione, ma è una deduzione dai marcatori della pagina. La seconda mostra che queste
  semantiche **si muovono**: la pagina dichiara che «Starting in MongoDB 9.0, the `{ "a.b": null }`
  query matches a document in any of these cases», elencando quattro casi per i percorsi puntati. È
  la conferma che il rifiuto dei percorsi puntati da parte del doppio non è pigrizia: imitarli
  vorrebbe dire scegliere una versione. La terza: sugli array la pagina avverte che «comparisons to
  `null` on array fields produce results you might not expect»; il doppio non conosce gli array e
  quel caso non si presenta.
- **Usata da:** [02-porte-e-doppi.md](02-porte-e-doppi.md)

<a id="a-007"></a>
### A-007 — MongoDB: l'uguaglianza su un sottodocumento richiede anche l'ordine dei campi

- **URL:** https://www.mongodb.com/docs/manual/tutorial/query-embedded-documents/
- **Editore:** MongoDB, Inc. — Database Manual
- **Versione documentata:** 8.3 (canale «Current» del manuale)
- **Consultata:** 2026-09-03
- **Verdetto:** conferma — e la pagina sconsiglia esplicitamente l'operazione
- **Cosa afferma:** «MongoDB does not recommend comparisons on embedded documents because the
  operations require an *exact* match of the specified `<value>` document, **including the field
  order**.» E poi il punto che riguarda chi scrive codice, non chi scrive query a mano: «Queries
  that use comparisons on embedded documents can result in **unpredictable behavior when used with
  a driver that does not use ordered data structures for expressing queries**.»
- **Conseguenza qui:** `InMemoryStore` **rifiuta** `{"campo": {...}}` senza operatori. Non perché
  sia difficile, ma perché l'uguaglianza fra `dict` di Python ignora l'ordine delle chiavi e quella
  di MongoDB no: le due risposte divergono sullo stesso dato, e un doppio che desse la risposta di
  Python farebbe passare una prova che contro il cluster fallirebbe. Il rifiuto nomina il campo e
  dice perché.
- **Riserve:** la pagina non dice **quale** driver usi strutture ordinate. PyMongo restituisce
  `dict`, e in CPython i `dict` conservano l'ordine di inserimento — ma conservare l'ordine non è
  confrontarlo, e `{"w": 21, "h": 14} == {"h": 14, "w": 21}` resta `True` in Python. La divergenza
  quindi c'è, e questa pagina la dichiara come rischio generale del driver senza misurarla per
  PyMongo. Nel repository nessuna affermazione si appoggia a più di così.
- **Usata da:** [02-porte-e-doppi.md](02-porte-e-doppi.md)

---

<a id="a-008"></a>
### A-008 — Python: `statistics.median` interpola, e la documentazione lo dice

- **URL:** https://docs.python.org/3/library/statistics.html#statistics.median
- **Editore:** Python Software Foundation — libreria standard
- **Versione documentata:** Python 3.14.7 (il canale `/3/` segue l'ultima versione pubblicata)
- **Consultata:** 2026-09-03
- **Verdetto:** conferma piena, e la pagina nomina da sé il compromesso che `mongolab` sceglie
- **Cosa afferma:** la mediana di un campione di lunghezza pari **non è un valore osservato**.
  «When the number of data points is even, the median is interpolated by taking the average of the
  two middle values», ed è per questo che `median([1, 3, 5, 7])` vale `4.0`, che nel campione non
  c'è. La stessa pagina descrive l'alternativa e la ragione per cui esiste: «Use the low median when
  your data are discrete and you prefer the median to be an actual data point rather than
  interpolated».
- **Conseguenza qui:** `mongolab` calcola la mediana come percentile per rango più vicino, che è la
  seconda forma — «an actual data point». La coincidenza con `statistics.median_low` non è supposta
  ma misurata, in [M-009](#m-009). Non si usa direttamente `median_low` perché la mediana qui non è
  un caso a parte: è il quantile 0,5 della stessa funzione che calcola p95 e p99, e due definizioni
  diverse nello stesso riquadro di riepilogo sarebbero una trappola per chi legge i numeri.
- **Riserve:** la pagina parla di dati **discreti** («when your data are discrete»), e le latenze in
  millisecondi sono continue. L'argomento della documentazione non copre quindi esattamente questo
  caso; la ragione per cui la scelta vale lo stesso è un'altra, ed è dichiarata nel codice: un
  numero che finisce su una slide deve poter essere ritrovato nel campione.
- **Usata da:** [06-carico-tentativi-e-latenze.md](06-carico-tentativi-e-latenze.md)

<a id="a-009"></a>
### A-009 — Python: `statistics.quantiles` interpola linearmente fra i due punti vicini

- **URL:** https://docs.python.org/3/library/statistics.html#statistics.quantiles
- **Editore:** Python Software Foundation — libreria standard
- **Versione documentata:** Python 3.14.7
- **Consultata:** 2026-09-03
- **Verdetto:** conferma piena — è la funzione che si sarebbe usata, e la pagina spiega perché non
  la si usa
- **Cosa afferma:** i tagli non cadono sui dati. «The cut points are linearly interpolated from the
  two nearest data points. For example, if a cut point falls one-third of the distance between two
  sample values, 100 and 112, the cut-point will evaluate to 104». La funzione ha inoltre **due**
  metodi, `'exclusive'` (predefinito) e `'inclusive'`, che danno risultati diversi sullo stesso
  campione: «The method for computing quantiles can be varied depending on whether the data includes
  or excludes the lowest and highest possible values from the population».
- **Conseguenza qui:** un p95 di 104 ms su un campione in cui nessuno ha misurato 104 ms è un numero
  costruito dalla formula. In una demo che esiste per mostrare misure vere è il tipo di numero da
  non avere sulla slide, e la divergenza fra i tre modi di dire «p95» è misurata in
  [M-009](#m-009): sullo stesso campione valgono 1,0 — 3,45 — 47,55.
- **Riserve:** nessuna sul contenuto. La riserva è sulla conclusione, e va detta: l'interpolazione
  **non è un difetto** di `quantiles`, è la definizione giusta quando si stima un quantile della
  popolazione da un campione. `mongolab` non stima una popolazione: riferisce le latenze che ha
  misurato, e per quello serve un valore osservato.
- **Usata da:** [06-carico-tentativi-e-latenze.md](06-carico-tentativi-e-latenze.md)

<a id="a-010"></a>
### A-010 — Python: `queue.Queue` è il punto di scambio fra thread, e si occupa dei lucchetti

- **URL:** https://docs.python.org/3/library/queue.html
- **Editore:** Python Software Foundation — libreria standard
- **Versione documentata:** Python 3.14.7
- **Consultata:** 2026-09-03
- **Verdetto:** conferma piena; è la fonte che rende `queue.Queue` una scelta e non un'abitudine
- **Cosa afferma:** «The queue module implements multi-producer, multi-consumer queues. It is
  especially useful in threaded programming when information must be exchanged safely between
  multiple threads. The `Queue` class in this module implements all the required locking semantics».
  Il modulo aggiunge come funziona dentro: «Internally, those three types of queues use locks to
  temporarily block competing threads; however, they are not designed to handle reentrancy within a
  thread».
- **Conseguenza qui:** i worker di `WorkloadRunner` non hanno bisogno di un lucchetto proprio, e
  soprattutto non ne hanno bisogno il sink e la TUI: la coda è l'unico punto in cui i thread si
  incontrano, e chi drena è uno solo (§6.3, ADR-0019). La riga sulla rientranza è la ragione per cui
  un `emit` non deve mai rimettere in coda: il sink sta nel thread che drena, e un ciclo lì sarebbe
  esattamente il caso che il modulo dichiara di non gestire.
- **Riserve:** la pagina non dice niente su quanto la coda possa crescere se il produttore corre più
  del consumatore. Con `maxsize=0` — quello che `mongolab` usa — la coda è illimitata, e sotto un
  carico che il drenaggio non regge cresce in memoria finché non finisce. Non è un problema alle
  scale della demo (secondi, migliaia di eventi) e lo diventerebbe in un carico lungo: la sede in
  cui si guarderà è il Task 16.
- **Usata da:** [06-carico-tentativi-e-latenze.md](06-carico-tentativi-e-latenze.md),
  [04-eventi-del-driver-e-concorrenza.md](04-eventi-del-driver-e-concorrenza.md)

---

## Misure fatte qui

<a id="m-001"></a>
### M-001 — L'ambiente in cui tutte le altre misure valgono

- **Data:** 2026-09-02
- **Comando:**
  ```
  uv run --directory app python -c "import sys; print(sys.version.split()[0])"
  uv run --directory app python -c "from importlib.metadata import version; print(version('pymongo'))"
  ```
  e altrettanto per `pytest`, `mypy`, `rich`, `typer`.
- **Output:**
  ```
  python: 3.13.15
  pymongo: 4.17.0
  pytest: 9.1.1
  mypy: 2.3.1
  rich: 15.0.0
  typer: 0.27.2
  ```
- **Che cosa dice:** l'interprete è la 3.13, non la 3.14 dell'host, perché `app/pyproject.toml`
  dichiara `requires-python = ">=3.13,<3.14"`. Il tetto è scritto e non lasciato alla fortuna della
  risoluzione: il design considera la 3.14 troppo recente per garantire il supporto di tutte le
  dipendenze di prova. Le versioni esatte stanno in `app/uv.lock`, che è versionato.
- **Riserve:** i numeri sono quelli risolti il 2026-09-02 su macOS con `uv`. Un `uv lock --upgrade`
  li sposterebbe, e a quel punto le misure che seguono andrebbero rifatte prima di essere citate.

<a id="m-002"></a>
### M-002 — Una sottoclasse mutabile di una dataclass congelata non è costruibile

- **Data:** 2026-09-02
- **Comando:**
  ```python
  @dataclass(frozen=True, slots=True)
  class Base:
      x: int

  @dataclass                      # senza frozen
  class Figlia(Base):
      y: int = 0
  ```
- **Output:**
  ```
  TypeError: cannot inherit non-frozen dataclass from a frozen one
  ```
- **Che cosa dice:** il congelamento della base si propaga come **regola del linguaggio**, non come
  buona abitudine. Nessuna sottoclasse di `Evento` può nascere mutabile, e la classe non arriva
  nemmeno a esistere: l'errore è al momento della creazione, non alla prima assegnazione. La
  conseguenza pratica è che una prova che asserisse `frozen` su ogni sottoclasse controllerebbe il
  compilatore, e non potrebbe mai fallire — è il ragionamento della **nota di metodo 144** del
  [registro operativo](../../docs/registro-operativo-sviluppo.md), ed è la ragione per cui quella
  asserzione è stata tolta.
- **Riserve:** il messaggio d'errore è quello di CPython 3.13.15 e non è documentato in
  [A-002](#a-002); un'altra implementazione o un'altra versione potrebbero formularlo
  diversamente, o — in teoria — non sollevarlo affatto. Il repository non si appoggia al **testo**
  del messaggio, solo al fatto che la classe non venga creata.

<a id="m-003"></a>
### M-003 — Che cosa compra `slots=True` su una dataclass già congelata

- **Data:** 2026-09-02
- **Comando:** su due sottoclassi congelate della stessa base — una con `slots=True`, una senza —
  si tentano tre scritture: assegnazione normale, `object.__setattr__`, scrittura diretta in
  `__dict__`.
- **Output:**
  ```
  --- SenzaSlot ---
    ha __dict__: True
    assegnazione normale: FrozenInstanceError: cannot assign to field 'z'
    object.__setattr__: RIESCE → o.z = 1
    scrittura in __dict__: RIESCE → o.z = 1
  --- ConSlot ---
    ha __dict__: False
    assegnazione normale: FrozenInstanceError: cannot assign to field 'z'
    object.__setattr__: AttributeError: 'ConSlot' object has no attribute 'z'
    scrittura in __dict__: AttributeError: 'ConSlot' object has no attribute '__dict__'
  ```
- **Che cosa dice:** `frozen=True` da solo ferma **l'assegnazione normale**, che è la via per cui
  passa il codice scritto in buona fede. Non ferma le due scorciatoie: `object.__setattr__` e la
  scrittura diretta nel `__dict__` riescono entrambe, ed è precisamente ciò che fa il costruttore
  generato ([A-002](#a-002): «`__init__()` … must use `object.__setattr__()`»). `slots=True`
  toglie il `__dict__`, e con esso tolgono terreno entrambe le scorciatoie: falliscono con
  `AttributeError`. La differenza fra i due decoratori, detta in una riga: **`frozen` protegge da
  una distrazione, `slots` protegge anche da chi conosce la scorciatoia.**
- **Riserve:** questa misura **corregge una frase** scritta nel registro operativo alla voce del
  Task 3, dove si legge che senza `slots` le istanze «tornano ad avere un `__dict__` in cui due
  thread possono scriversi di nascosto». Il `__dict__` c'è davvero, ma scriverci richiede di
  aggirare `__setattr__`: l'assegnazione normale resta bloccata. La sostanza dell'argomento regge —
  la superficie da cui si può scrivere esiste solo senza `slots` —, la formulazione era più larga
  del misurato. Il registro operativo è cronologico e non si riscrive: è la pratica costante del
  repository, la stessa per cui [ADR-0068](../../docs/Decision.md#adr-0068) «resta com'è, con la sua
  data» e una decisione successiva lo corregge. La correzione sta quindi qui, e la voce del
  2026-09-02 va letta insieme a questa riga.

<a id="m-004"></a>
### M-004 — `isinstance` contro un `Protocol` accetta una firma sbagliata

- **Data:** 2026-09-02
- **Comando:**
  ```python
  @runtime_checkable
  class Clock(Protocol):
      def now(self) -> datetime: ...
      def sleep(self, secondi: float) -> None: ...

  class FirmaSbagliata:
      def now(self) -> datetime: ...
      def sleep(self) -> None: ...      # manca `secondi`

  class Monco:
      def now(self) -> datetime: ...
  ```
- **Output:**
  ```
  firma sbagliata, isinstance: True
  metodo mancante, isinstance: False
  ```
- **Che cosa dice:** il controllo a runtime distingue **la presenza dei nomi** e nient'altro. Un
  oggetto cui manca un metodo viene respinto; un oggetto con tutti i nomi e una firma incompatibile
  passa, e passerebbe fino al primo `TypeError` in produzione. È la conferma sperimentale di quanto
  affermano [A-001](#a-001) e [A-003](#a-003), ed è la ragione per cui in questo progetto
  `mypy --strict` non è un accessorio: è **l'unico** punto in cui la conformità alle porte è
  verificata davvero.
- **Riserve:** nessuna. La misura riproduce ciò che entrambe le fonti dichiarano, sulla versione
  installata.

<a id="m-005"></a>
### M-005 — `pytest` su una directory di prove vuota esce 5

- **Data:** 2026-09-02
- **Comando:**
  ```
  uv run --directory app pytest -q tests/integration > /dev/null 2>&1; echo $?
  ```
- **Output:**
  ```
  5
  ```
- **Che cosa dice:** finché `tests/integration/` non contiene prove — arrivano al Task 8 del piano —
  il bersaglio `make app-test-integration` riceve un codice che non è né successo né errore.
  Lasciarlo passare come fallimento manderebbe a cercare Docker chi non ha ancora niente da
  eseguire; sopprimerlo con `|| true` insegnerebbe che il verde di quel bersaglio non vuol dire
  niente, e l'insegnamento sopravvivrebbe al Task 8. Il `Makefile` fa la terza cosa: intercetta
  **quel** codice e stampa la frase che spiega perché. È la **nota di metodo 143**.
- **Riserve:** il comportamento è quello di pytest 9.1.1 e coincide con [A-004](#a-004). Dal Task 8
  in poi questa misura smetterà di essere riproducibile, perché la directory non sarà più vuota: è
  attesa, ed è il segno che il debito è stato pagato.

<a id="m-006"></a>
### M-006 — Un archivio che accetta tutto fa fallire sette prove, non zero

- **Data:** 2026-09-03
- **Comando:** in `tests/doppi/archivio.py`, primo statement di `_corrisponde`:
  ```python
  def _corrisponde(self, documento, filtro) -> bool:
      return True          # rottura deliberata: il filtro non guarda più niente
  ```
  poi `make app-test`, poi ripristino.
- **Output:**
  ```
  FAILED test_l_archivio_non_tiene_il_documento_di_chi_lo_ha_chiamato - AssertionError: assert 1 == 0
  FAILED test_l_archivio_filtra_per_uguaglianza_invece_di_contare_tutto - AssertionError: assert 3 == 2
  FAILED test_l_archivio_cerca_i_campi_assenti_come_fa_mongodb - assert [1, 2, 3] == [1, 2]
  FAILED test_l_archivio_non_confronta_sottodocumenti - Failed: DID NOT RAISE NonSupportato
  FAILED test_l_archivio_impagina_quello_che_il_filtro_ha_scelto - assert [2, 3] == [3]
  FAILED test_un_filtro_che_l_archivio_non_sa_applicare_solleva - Failed: DID NOT RAISE NonSupportato
  FAILED test_l_aggregazione_esegue_gli_stadi_che_conosce - AssertionError: assert ({'quanti': 3},) == ({'quanti': 2},)
  7 failed, 47 passed in 0.08s
  ```
- **Che cosa dice:** la rottura è quella che un doppio permissivo produce davvero — «restituisco
  tutto» —, e le prove la vedono da sette lati. Due righe contano più delle altre cinque, e sono le
  `DID NOT RAISE`: dicono che il **rifiuto** è verificato quanto il comportamento. Senza quelle due,
  un `InMemoryStore` che ignorasse in silenzio un `$gt` sconosciuto resterebbe verde, e la prima
  prova scritta con quell'operatore passerebbe senza che nessuno abbia implementato niente. È il
  terzo esito della **nota di metodo 144**: la guardia esiste, e si è vista sparare.
- **Riserve:** la misura mostra che *quelle* prove reggono a *quella* rottura, e non che reggano a
  tutte. Cercandone una scoperta la si trova subito: togliendo da `_come_intero` il rifiuto dei
  booleani — `if not isinstance(argomento, int)`, senza l'`isinstance(argomento, bool)` — le prove
  restano **54 verdi**, perché nessuna chiede `{"$limit": True}`. Il rifiuto dei booleani è quindi
  oggi una precauzione non verificata: sopravvive alla revisione, non alla mutazione. Ci sarà una
  prova il giorno in cui qualcosa dipenderà da lui, secondo la stessa regola che tiene `$group`
  fuori dal dialetto.

<a id="m-007"></a>
### M-007 — `mypy --strict` non distingue una funzione generatrice da una che restituisce un generatore

- **Data:** 2026-09-03
- **Comando:** in `tests/doppi/backup.py`, `dump` scritta nella forma che verrebbe più naturale:
  ```python
  def dump(self, destinazione: Path) -> Iterator[Progress]:
      self.dump_chiesti.append(destinazione)
      yield from self._cronaca()        # invece di: return self._cronaca()
  ```
  poi `make app-test` e `make app-check`, poi ripristino.
- **Output:**
  ```
  FAILED tests/unit/test_doppi.py::test_il_backup_finto_registra_la_richiesta_anche_se_nessuno_la_scorre
         - AssertionError: assert [] == [PosixPath('/tmp/dump')]
  1 failed, 53 passed in 0.05s

  uv run --directory app mypy
  Success: no issues found in 23 source files
  ```
- **Che cosa dice:** due cose, e la seconda è la ragione per cui questa misura esiste. La prima: la
  differenza è **osservabile**, e una prova la osserva. Chiamare `dump()` senza scorrere il
  risultato lascia `dump_chiesti` vuoto, perché il corpo non è mai partito ([A-005](#a-005): «The
  execution starts when one of the generator's methods is called»). La seconda: **il sistema dei
  tipi tace.** Le due forme hanno lo stesso tipo annotato, `Iterator[Progress]`, e `mypy --strict`
  passa su entrambe. Un errore che cambia *quando* il lavoro comincia non è un errore di tipo, e
  qui la differenza sarà fra «`mongodump` è partito» e «`mongodump` partirà se qualcuno guarda».
  Sta insieme a [M-004](#m-004) come promemoria in due direzioni: `mypy` è l'unico a verificare la
  conformità alle porte, e non verifica tutto.
- **Riserve:** la misura vale per la forma `yield from` in una funzione annotata `Iterator[...]`.
  Un `-> Generator[...]` esplicito non cambierebbe niente, ma non è stato provato. Nessuna opzione
  di mypy è stata cercata per farlo distinguere: potrebbe esistere, e questa voce afferma solo che
  la configurazione `strict` del progetto non la applica.

---

<a id="m-008"></a>
### M-008 — Il rango di un percentile calcolato in virgola mobile non sbaglia mai, qui

- **Data:** 2026-09-03
- **Comando:** `percentile` calcola il rango come `math.ceil(quantile * len(campione))`, cioè con un
  prodotto in virgola mobile dentro un `ceil` — la combinazione in cui un errore di un ulp diventa
  un rango sbagliato di uno, e quindi un valore diverso. Il confronto è con l'aritmetica esatta di
  `fractions.Fraction`:
  ```python
  for q in (0.5, 0.9, 0.95, 0.99, 0.999):
      esatto_q = Fraction(q).limit_denominator(1000)
      for n in range(1, 200001):
          if math.ceil(q * n) != math.ceil(esatto_q * n):
              sbagli.append((q, n))
  ```
  eseguito con l'interprete del progetto: `uv run --directory app python rango.py`.
- **Output:**
  ```
  versione: 3.13.15 | GIL attivo: True
  ranghi divergenti su 5 quantili x 200000 campioni: 0
  ```
- **Che cosa dice:** per i quantili che `mongolab` usa e per campioni fino a duecentomila latenze,
  `ceil` in virgola mobile e il rango esatto coincidono sempre. La riga sul GIL è dello stesso
  comando e serve a un'altra prova: la suite concorrente si appoggia al fatto che `list.extend` di
  `InMemoryStore` non perda documenti sotto quattro scrittori, e su un interprete *free-threaded*
  quel presupposto andrebbe riverificato invece che ereditato.
- **Riserve:** è una verifica **esaustiva su un intervallo**, non una dimostrazione. Fuori
  dall'intervallo — quantili scritti come `0.9999`, campioni da milioni di elementi — non dice
  niente, e la forma giusta della difesa in quel caso sarebbe calcolare il rango in aritmetica
  intera invece di misurare che quella in virgola mobile tiene.

<a id="m-009"></a>
### M-009 — «p95» sullo stesso campione vale 1,0 oppure 3,45 oppure 47,55

- **Data:** 2026-09-03
- **Comando:** un campione costruito apposta con un gradino — 95 latenze da 1 ms, poi 50, 60, 70,
  80 e 900 ms — passato ai tre modi di calcolare il novantacinquesimo percentile, più la media.
  Nella stessa esecuzione, 20 000 campioni casuali per confrontare il quantile 0,5 per rango più
  vicino con `statistics.median_low`.
- **Output:**
  ```
  mediana per rango vs median_low: 0 divergenze su 20000 campioni
  campione: 95 valori a 1.0 piu 50, 60, 70, 80, 900 (n=100)
    rango piu vicino: 1.0
    quantiles inclusive[94]: 3.45
    quantiles exclusive[94]: 47.55
    media: 12.55
    osservato nel campione? mio=True incl=False
  Latenze(campioni=100, minimo_ms=1.0, mediana_ms=1.0, p95_ms=1.0, p99_ms=80.0, massimo_ms=900.0)
  ```
- **Che cosa dice:** due cose, e la seconda è scomoda. La prima è che la mediana per rango più
  vicino **è** `statistics.median_low`, su ventimila campioni casuali senza una divergenza: la
  scelta di `mongolab` coincide con una funzione della libreria standard, e la coincidenza è
  misurata invece che supposta. La seconda è che «p95» da solo non è un numero: sullo stesso
  campione i tre metodi danno 1,0, 3,45 e 47,55 — quarantasette volte l'uno dall'altro — e nessuno
  dei tre sbaglia, perché stanno rispondendo a tre domande diverse. Solo il primo, però,
  restituisce un valore che qualcuno ha misurato davvero (`mio=True`, `incl=False`).
- **Riserve:** la riserva riguarda la scelta di `mongolab`, e va scritta perché la misura la mostra.
  Con 95 valori su 100 identici, il p95 per rango cade **in cima al pianerottolo**: vale 1,0 e non
  racconta niente della coda, che pure c'è e arriva a 900 ms. In quel campione è il p99 a mostrarla
  — 80,0 — e il massimo a dirla tutta. Non è un difetto del metodo ma il suo confine: il percentile
  per rango risponde «il più piccolo valore osservato sotto il quale sta almeno il 95 % del
  campione», e su una distribuzione a gradino quella risposta sta sul gradino. È la ragione per cui
  il riepilogo di `mongolab` porta **sei** numeri e non uno.

<a id="m-010"></a>
### M-010 — Quattro rotture deliberate sul generatore di carico, e una che non fallisce

- **Data:** 2026-09-03
- **Comando:** quattro modifiche al solo `src/mongolab/application/workload.py`, una alla volta,
  ciascuna seguita da `make app-test` e dal ripristino da copia.
- **Output:**
  ```
  1. tolto il «return» che ferma i tentativi all'ultimo:
     FAILED test_la_politica_smette_dopo_i_tentativi_previsti_e_non_prima - assert 3 == 2
     FAILED test_l_ultimo_evento_di_una_resa_e_il_fallimento_non_il_tentativo - assert False
     FAILED test_l_attesa_raddoppia_a_ogni_tentativo - assert [50.0, 100.0, 200.0, 400.0] == [50.0, 100.0, 200.0]
     FAILED test_l_attesa_non_supera_il_tetto - assert [50.0, 120.0, 120.0, 120.0] == [50.0, 120.0, 120.0]
     FAILED test_il_tentativo_e_numerato_come_la_prova_che_sta_per_fare - assert [2, 3, 4] == [2, 3]
     5 failed, 100 passed in 0.11s

  2. i worker emettono sul sink invece che in coda:
     FAILED test_solo_il_thread_chiamante_tocca_il_sink - assert {6178680832} == {8352227712}
     (piu cinque prove sui conteggi, che vivono nel ciclo di drenaggio)
     6 failed, 99 passed in 0.11s

  3. mediana con statistics.median al posto del rango piu vicino:
     FAILED test_riassumi_su_un_campione_noto - Latenze(... mediana_ms=5.5 ...) != (... 5.0 ...)
     1 failed, 104 passed in 0.09s

  4. la sentinella spostata fuori dal «finally»:
     ...............  (la suite si ferma al 68 %)
     make: *** [app-test] Error 143      <- SIGTERM, dopo 45 s di «timeout»
  ```
- **Che cosa dice:** le prime tre rotture sono i due esiti noti della **nota 142** — la guardia
  scatta, e dice dove. La seconda merita una riga a sé: l'unica prova che vede la violazione *per
  quello che è* è quella sul thread, e lo dice mostrando due identificatori diversi. Le altre
  cinque falliscono per un effetto collaterale, perché i conteggi del riepilogo vivono nello stesso
  ciclo che drena la coda; se un giorno i conteggi si spostassero altrove, resterebbe **una sola**
  prova a difendere l'invariante del §6.3, ed è bene saperlo adesso.
- **Riserve:** la quarta rottura è l'esito nuovo, e non compare nella nota 144. Togliendo il
  `finally` che garantisce la sentinella, la prova sul generatore che solleva **non fallisce: si
  pianta**. Il worker muore prima di segnalare la fine del turno, il chiamante aspetta una
  sentinella che non arriverà, e la suite resta ferma finché qualcuno non la uccide da fuori.
  Nessun `FAILED`, nessun messaggio, nessun punto del codice indicato — e un blocco senza messaggio
  somiglia a un problema della macchina molto più che a un difetto. È la **nota di metodo 153**.

<a id="m-011"></a>
### M-011 — Ventuno rotture deliberate sull'osservatore della topologia, e due rapporti falsi

- **Data:** 2026-09-03
- **Comando:** ventun modifiche al solo `src/mongolab/application/topologia.py`, una alla volta,
  ciascuna seguita da `pytest -q` e dal ripristino da copia. Uno script guida il ciclo, con
  `PYTHONDONTWRITEBYTECODE=1` e la rimozione di ogni `__pycache__` **prima** di ogni corsa (il
  perché sta nelle riserve).
- **Output:**
  ```
  ROSSO   1. la prima occhiata emette                42 failed, 111 passed
  ROSSO   2. topologia identica emette lo stesso      2 failed, 151 passed
  ROSSO   3. il riepilogo prima dei dettagli          3 failed, 150 passed
  ROSSO   4. l'ordine non e' per indirizzo            1 failed, 152 passed  <- prova nuova
  ROSSO   5. chi sparisce diventa irraggiungibile     1 failed, 152 passed
  ROSSO   6. chi arriva viene da irraggiungibile      1 failed, 152 passed
  ROSSO   7. un'interruzione aperta dura zero         2 failed, 151 passed
  ROSSO   8. l'interruzione si apre al primo sguardo  1 failed, 152 passed
  ROSSO   9. lo stesso primario che torna e' failover 1 failed, 152 passed
  ROSSO  10. la pazienza scade un giro dopo           2 failed, 151 passed
  ROSSO  11. la resa chiude l'interruzione            1 failed, 152 passed
  ROSSO  12. dopo la resa si riprende a guardare      1 failed, 152 passed
  ROSSO  13. si attende anche dopo l'ultimo giro      1 failed, 152 passed
  ROSSO  14. le perdite possono essere negative       1 failed, 152 passed
  ROSSO  15. i conteggi negativi passano              1 failed, 152 passed
  ROSSO  16. zero giri e' un numero di giri           1 failed, 152 passed
  ROSSO  17. un intervallo di zero va bene            1 failed, 152 passed
  ROSSO  18. una pazienza di zero va bene             1 failed, 152 passed
  ROSSO  19. l'interruzione si richiude a ogni giro   2 failed, 151 passed  <- prova nuova
  ROSSO  20. il ricordo del primario non si azzera    2 failed, 151 passed  <- prova nuova
  ROSSO  21. segui torna il failover di prima         1 failed, 152 passed  <- prova nuova
  ```
- **Che cosa dice:** ventuno su ventuno, ciascuna catturata dalla prova che la nomina. Ma il
  risultato utile è **quello della prima corsa**, prima che le quattro prove nuove esistessero: le
  rotture 4, 19, 20 e 21 lasciavano la suite **verde su 148**. Quattro guardie scoperte su ventuno,
  cioè il terzo esito della nota 144 quasi una volta su cinque.

  La più istruttiva è la 4. Una prova sull'ordine per indirizzo dei `ServerStateChanged` esisteva
  già; togliendo `sorted` restava verde, perché in quella prova anche l'ordine di comparsa dei
  server era alfabetico. Osservava il risultato giusto per il motivo sbagliato. La prova nuova
  elenca i server **al contrario** nella prima descrizione.
- **Riserve — due volte l'arnese ha mentito prima del codice.**

  **Il codice d'uscita letto come un booleano.** Il primo rapporto diceva *ventuno su ventuno*, e
  non aveva eseguito una sola prova: era rimasta in riga di comando un'opzione inesistente, e
  `pytest` usciva con **4** — errore d'uso — per tutte e ventuno. Lo script trattava «diverso da
  zero» come «una prova ha fallito». Il repository conosceva già il codice 5, «nessuna prova
  raccolta» ([M-005](#m-005)); adesso conosce anche il 4. Solo l'**1** vuol dire che una prova ha
  fallito, e un arnese di mutazione deve pretenderlo.

  **Il bytecode riusato fra due rotture diverse.** Il secondo rapporto attribuiva a rotture diverse
  la stessa prova fallita, il che è impossibile. Python decide se ricompilare un modulo
  confrontando **la data di modifica in secondi e la dimensione in byte** del sorgente: le rotture 5
  e 6 sono la stessa sostituzione (`SCONOSCIUTO` → `IRRAGGIUNGIBILE`) in due punti diversi, quindi
  producono file **della stessa dimensione**, e vengono scritte a meno di un secondo l'una
  dall'altra. La corsa della 6 eseguiva il `.pyc` della 5. Lo stesso è capitato alla coppia 9/10,
  anch'essa di dimensione identica (`16033` byte contro `16032` dell'originale).

  In entrambi i casi il segnale d'allarme è stato lo stesso, e vale la pena tenerlo: **un rapporto
  troppo pulito.** Ventuno rotture su ventuno catturate era il risultato più desiderabile e il più
  improbabile; due mutazioni distinte catturate dalla stessa identica prova era un'impossibilità
  logica travestita da conferma.

---

## Fonti canoniche che l'applicazione usa senza copiarle

Queste stanno in [`docs/Sources.md`](../../docs/Sources.md) e sono citate da un ADR. Qui c'è solo
il puntatore e il motivo per cui riguardano `mongolab`.

| Codice | Che cosa afferma, in una riga | Dove pesa su `mongolab` |
|---|---|---|
| [S-010](../../docs/Sources.md#s-010) | i listener di PyMongo esistono, e «Events are delivered synchronously. Application threads block waiting for event handlers … to return» | [04-eventi-del-driver-e-concorrenza.md](04-eventi-del-driver-e-concorrenza.md) |
| [S-018](../../docs/Sources.md#s-018) | `Live` di Rich aggiorna quattro volte al secondo per impostazione predefinita, regolabile con `refresh_per_second` — e **non nomina mai i thread** | [04-eventi-del-driver-e-concorrenza.md](04-eventi-del-driver-e-concorrenza.md) |
| [S-007](../../docs/Sources.md#s-007) | con `directConnection=false` «the client attempts to discover all servers in the replica set» | [01-architettura-esagonale.md](01-architettura-esagonale.md) |
| [S-013](../../docs/Sources.md#s-013) | `testcontainers-python` non conosce i replica set | [05-tipi-prove-e-guardie.md](05-tipi-prove-e-guardie.md) |
