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

<a id="a-011"></a>
### A-011 — MongoDB: `limit(0)` non vuol dire «nessun documento», vuol dire «nessun limite»

- **URL:** https://www.mongodb.com/docs/manual/reference/method/cursor.limit/
- **Editore:** MongoDB, Inc. — Database Manual 8.3
- **Consultata:** 2026-09-03
- **Verdetto:** conferma piena, e conferma un'inversione: la lettura ovvia del valore è quella sbagliata
- **Cosa afferma:** «A `limit()` value of 0 (i.e. `.limit(0)`) is equivalent to setting no limit». La
  pagina aggiunge due cose che valgono per `find_page`: un limite **negativo** «closes the cursor
  after returning a single batch of results», quindi non è semplicemente «zero documenti»; e
  l'ordine di concatenazione non conta, perché «the server always applies skip before limit».
- **Conseguenza qui:** `PymongoStore.find_page` intercetta `quanti <= 0` **prima** di chiamare il
  driver e restituisce la tupla vuota. Senza quella riga, chi chiede zero documenti riceve la
  collezione intera — e a `quanti=0` non ci si arriva digitandolo, ci si arriva per sottrazione
  (quante righe restano nella finestra, quanti mancano alla fine dell'elenco), cioè nel caso limite
  di un calcolo, che è precisamente quello che nessuno prova a mano. La verifica corrispondente sta
  nel contratto condiviso, dove passa contro `InMemoryStore` e falliva contro MongoDB: vedi
  [M-022](#m-022).
- **Usata da:** [09-adattatori-veri-e-contratto-condiviso.md](09-adattatori-veri-e-contratto-condiviso.md)

<a id="a-012"></a>
### A-012 — MongoDB: `$shardedDataDistribution`, l'unico conteggio per shard che non interroga gli shard

- **URL:** https://www.mongodb.com/docs/manual/reference/operator/aggregation/shardedDataDistribution/
- **Editore:** MongoDB, Inc. — Database Manual
- **Versione documentata:** stadio «New in version 6.0.3»
- **Consultata:** 2026-09-03
- **Verdetto:** conferma piena, con **due riserve che la pagina stessa dichiara**
- **Cosa afferma:** «Returns information on the distribution of data in sharded collections». Dove si
  esegue: «This aggregation stage is only available on `mongos`» e «This aggregation stage must be run
  on the `admin` database. The user must have the `shardedDataDistribution` privilege action». I due
  campi che contano: `numOwnedDocuments` è il «Number of documents owned by the shard»,
  `numOrphanedDocs` il «Number of orphaned documents in the shard».
  Le due riserve: «Starting in MongoDB 8.0, `$shardedDataDistribution` only returns output for a
  collection's primary shard if the primary shard has chunks or orphaned documents»; e «After an
  unclean shutdown of a `mongod` using the Wired Tiger storage engine, size and count statistics
  reported by `$shardedDataDistribution` may be inaccurate».
- **Conseguenza qui:** `PymongoInspector.shard_distribution` somma `numOwnedDocuments` e **non** gli
  orfani, perché contarli farebbe superare al totale il numero di documenti che esistono e il conto
  non tornerebbe con `count()`. La seconda riserva pesa sulla scena del guasto: il Blocco 3 spegne
  uno shard con un `docker kill`, che è per definizione un arresto sporco, e la pagina dice che
  proprio dopo quello i conteggi possono essere imprecisi. Va detto dal palco invece di essere
  scoperto.
- **Usata da:** [09-adattatori-veri-e-contratto-condiviso.md](09-adattatori-veri-e-contratto-condiviso.md)

<a id="a-013"></a>
### A-013 — MongoDB: i chunk di una collezione si trovano per `uuid`, e il manuale lo prescrive

- **URL:** https://www.mongodb.com/docs/manual/reference/config-database/
- **Editore:** MongoDB, Inc. — Database Manual
- **Consultata:** 2026-09-03
- **Verdetto:** conferma **parziale**, e la parte che manca è quella che si sarebbe voluta citare
- **Cosa afferma:** «The `config.chunks` collection stores a document for each chunk in the cluster»,
  e il documento d'esempio ha `_id`, `uuid`, `min`, `max`, `shard`, `lastmod`, `history` — nessun
  `ns`. Il modo di interrogarla è prescritto: «To find the chunks in a collection, retrieve the
  collection's `uuid` identifier from the `config.collections` collection. Then, use the `uuid` to
  retrieve the document with the same `uuid` from the `config.chunks` collection». La pagina premette
  che «The config database is internal. Applications and administrators should not modify or depend
  on its content during normal operation».
- **Conseguenza qui:** `_chunk_per_shard` fa esattamente i due passaggi del Tip. La parte che **non**
  si può citare è la sparizione del campo `ns`: la pagina non la afferma da nessuna parte e non
  nomina la 5.0 a questo proposito, quindi il codice non lo dice — lo dice la misura
  [M-020](#m-020), che è una constatazione sul 7.0.40 di questo repository e non una regola di
  versione. L'avvertimento sull'uso di `config` è invece una riserva vera: questo ispettore legge un
  database interno, e lo fa perché non esiste altro modo di contare i chunk. Se un giorno il formato
  cambia, la prova di integrazione sul 03 diventa rossa — che è la ragione per cui esiste.
- **Usata da:** [09-adattatori-veri-e-contratto-condiviso.md](09-adattatori-veri-e-contratto-condiviso.md)

<a id="a-014"></a>
### A-014 — PyMongo: `insert_one` scrive l'`_id` dentro il documento che riceve

- **URL:** https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html
- **Editore:** MongoDB, Inc. — documentazione di PyMongo (stable)
- **Consultata:** 2026-09-03
- **Verdetto:** conferma **parziale**, e la parte mancante è stata misurata invece che letta
- **Cosa afferma:** di `insert_one`, che il documento «Must be a mutable mapping type. If the document
  does not have an `_id` field one will be added automatically». Di `ordered` in `insert_many`: «If
  `True` (the default) documents will be inserted on the server serially, in the order provided» e in
  caso di errore «all remaining inserts are aborted»; con `False` i documenti vanno «in arbitrary
  order, possibly in parallel, and all document inserts will be attempted».
- **Conseguenza qui:** la frase sul `mutable mapping` è la ragione formale per cui `PymongoStore`
  copia: la porta dichiara `Mapping`, il driver vuole qualcosa di mutabile. La conseguenza che la
  pagina **non** enuncia per `insert_many` — che l'`_id` finisca nel dizionario **del chiamante** —
  è quella che pesa davvero sul generatore di carico, e non essendo scritta è stata provata: la
  verifica `test_l_adattatore_non_scrive_l_id_nel_documento_di_chi_lo_ha_chiamato` chiama prima
  l'adattatore, poi il driver nudo, e mostra la differenza. Su `ordered` la pagina descrive due
  comportamenti senza promettere prestazioni: il confronto è [M-021](#m-021).
- **Usata da:** [09-adattatori-veri-e-contratto-condiviso.md](09-adattatori-veri-e-contratto-condiviso.md)

---

<a id="a-015"></a>
### A-015 — Rich: `auto_refresh` è documentato, il thread che lo attua no

- **URL:** https://rich.readthedocs.io/en/stable/reference/live.html — letta però sul pacchetto
  installato, `rich` **15.0.0**, in `app/.venv/lib/python3.13/site-packages/rich/live.py`, perché
  la pagina pubblicata è generata da quelle stesse docstring e il repository deve poter essere
  verificato senza rete.
- **Editore:** Will McGugan e i contributori di Rich
- **Consultata:** 2026-09-03
- **Verdetto:** conferma **parziale** — il parametro c'è, il meccanismo non è detto
- **Cosa afferma:** di `Live`, che `auto_refresh` è «Enable auto refresh. If disabled, you will
  need to call `refresh()` or `update()` with refresh flag. Defaults to True», e che
  `refresh_per_second` è il «Number of times per second to refresh the live display. Defaults to
  4». Nessuna delle due righe dice **chi** aggiorna: la frase è scritta al passivo, e un lettore
  che non apra il modulo può concludere che il ridisegno avvenga dentro le chiamate che fa lui.
- **Conseguenza qui:** è la stessa lacuna già dichiarata da [S-018](../../docs/Sources.md#s-018),
  vista adesso da un metro più vicino — e la lacuna non è cosmetica, perché
  [ADR-0019](../../docs/Decision.md#adr-0019) aveva promesso «un solo thread tocca `Live`» proprio
  appoggiandosi al silenzio della documentazione. Il thread esiste, e si chiama `_RefreshThread`:
  la misura è [M-027](#m-027), la decisione che ne discende è
  [ADR-0085](../../docs/Decision.md#adr-0085). Il nome con la sottolineatura davanti è l'unica cosa
  che Rich dice sul suo conto, ed è la cosa giusta da dire: è privato, e appoggiarcisi sarebbe
  stato un errore anche se fosse stato documentato.
- **Usata da:** [11-tre-rese-e-un-solo-thread-che-disegna.md](11-tre-rese-e-un-solo-thread-che-disegna.md)

---

<a id="a-016"></a>
### A-016 — MongoDB: la specifica SDAM dice che il client aggiunge i server che il set gli nomina

- **URL:** https://raw.githubusercontent.com/mongodb/specifications/master/source/server-discovery-and-monitoring/server-discovery-and-monitoring.md
  — il sorgente e non la pagina resa, perché la resa su GitHub tronca i blocchi lunghi e le
  frasi che qui contano stanno dentro uno pseudocodice.
- **Editore:** MongoDB, Inc. — repository `mongodb/specifications`, documento *Server Discovery
  And Monitoring*, senza numero di versione né data: l'unico metadato in testa è `Status:
  Accepted`.
- **Consultata:** 2026-09-03
- **Verdetto:** **conferma** — e conferma proprio ciò che [ADR-0012](../../docs/Decision.md#adr-0012)
  aveva dichiarato di non poter affermare
- **Cosa afferma:** che nella sottoroutine `updateRSWithoutPrimary` il client cicla «for each
  address in description's "hosts", "passives", and "arbiters"» e, per ogni indirizzo che non
  conosce ancora, aggiunge una `ServerDescription` di tipo `Unknown` e comincia a sorvegliarlo;
  e che, nella motivazione, «While there is no known primary, the client MUST **add** servers
  from non-primaries' host lists, but it MUST NOT remove» server dalla `TopologyDescription`.
  La rimozione invece spetta al solo primario: è `updateRSFromPrimary` a togliere gli host che
  la sua lista non nomina. La *seed list* è definita per contrasto: «Server addresses provided
  to the client in its initial configuration, for example from the connection string» — cioè
  ciò da cui si parte, non ciò con cui si finisce.
- **Conseguenza qui:** ADR-0012 portava una riserva dichiarata — *la documentazione non afferma
  che il driver usi gli host memorizzati nella configurazione del set, e se lo si vuole
  affermare va mostrato in demo*. La riserva era giusta sul manuale di PyMongo, che davvero non
  lo dice, e sbagliata sul perimetro: la frase esiste, sta nella specifica *cross-driver* che
  PyMongo implementa, ed è normativa (`MUST`). Che poi PyMongo la implementi davvero resta una
  cosa diversa dall'affermarla, ed è misurata in [M-036](#m-036): un seme solo, e tre membri
  trovati. La distinzione vale per il talk più di entrambe le metà — una promessa sta nella
  specifica, non nel manuale dello strumento, e chi legge solo il secondo non la trova.
- **Usata da:** [13-il-container-sulla-rete-e-la-scoperta-che-si-vede.md](13-il-container-sulla-rete-e-la-scoperta-che-si-vede.md)

<a id="a-017"></a>
### A-017 — PyMongo: un comando su `admin` va sul primario, e per questo `ping` è un'attesa

- **URL:** https://pymongo.readthedocs.io/en/stable/api/pymongo/database.html — letta però sul
  pacchetto installato, `pymongo` **4.17.0**, in
  `app/.venv/lib/python3.13/site-packages/pymongo/synchronous/database.py`, perché ciò che qui
  conta non è la frase della pagina ma la riga che la attua, e la riga si può citare per numero.
- **Editore:** MongoDB, Inc. — documentazione e sorgente di PyMongo
- **Consultata:** 2026-09-04
- **Verdetto:** **conferma**, e la conferma è doppia — la docstring lo dichiara, il codice lo fa
- **Cosa afferma:** di `Database.command`, che il parametro `read_preference`, se la sessione non
  è in una transazione, «defaults to :attr:`~pymongo.read_preferences.ReadPreference.PRIMARY`»
  (righe 880-885). Cinquanta righe più sotto, il codice che lo attua:
  ```python
  if read_preference is None:
      read_preference = (session and session._txn_read_preference()) or ReadPreference.PRIMARY
  ```
  (righe 932-933).
- **Conseguenza qui:** è la ragione per cui `attendi_il_primario` è una riga sola e non un ciclo
  di sondaggi. Un comando che deve andare sul primario **non torna finché un primario non c'è**:
  la selezione del server è l'attesa, e il suo limite è il `serverSelectionTimeoutMS` che
  `connetti` fissa. `cliente.admin.command("ping")` non è quindi una verifica di raggiungibilità
  — quella la darebbe una preferenza `NEAREST` — ma la stessa domanda che la scena farà un
  istante dopo, fatta in anticipo per aspettarne la risposta. Il difetto che ha reso necessaria
  la riga è [M-042](#m-042).
- **Usata da:** [14-la-scena-del-failover-e-i-due-numeri.md](14-la-scena-del-failover-e-i-due-numeri.md)

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

<a id="m-012"></a>
### M-012 — La documentazione dice microsecondi, il codice passa secondi

- **Data:** 2026-09-03
- **Comando:** lettura del sorgente di PyMongo 4.17.0 installato nel `.venv` del progetto, ai tre
  punti che decidono l'unità di misura di `ServerHeartbeatSucceededEvent.duration`.
- **Output:**
  ```
  monitoring.py:1361            @property
  monitoring.py:1362            def duration(self) -> float:
  monitoring.py:1363                """The duration of this heartbeat in microseconds."""

  synchronous/monitor.py:326    response, round_trip_time = self._check_with_socket(conn)
  synchronous/monitor.py:334    self._listeners.publish_server_heartbeat_succeeded(
  synchronous/monitor.py:335        address, round_trip_time, response, response.awaitable

  synchronous/monitor.py:357    start = time.monotonic()
  synchronous/monitor.py:372    duration = _monotonic_duration(start)
  synchronous/monitor.py:57     def _monotonic_duration(start: float) -> float:
  synchronous/monitor.py:63         return max(0.0, time.monotonic() - start)
  ```
- **Che cosa dice:** la docstring di `duration` afferma «in microseconds», e il valore che arriva
  lì è `round_trip_time`, cioè il ritorno di `_monotonic_duration`, cioè una **differenza di
  `time.monotonic()`**: secondi. Sono tre passaggi, tutti nello stesso file tranne l'ultimo, e la
  conclusione non ammette letture alternative. La docstring sbaglia.

  Il confronto con l'altro evento chiude il quadro. `CommandSucceededEvent` riceve un
  `datetime.timedelta` (`monitoring.py:672`) e lo converte a `monitoring.py:466` con
  `int(dur.total_seconds() * 10e5)`: `duration_micros` è **davvero** in microsecondi. Le due
  famiglie di eventi usano quindi unità diverse, e solo una delle due è documentata correttamente.
- **Conseguenza qui:** `AscoltatoreHeartbeat.succeeded` moltiplica per 1000, `AscoltatoreComandi.succeeded`
  divide per 1000, e le due conversioni hanno ciascuna la sua prova. Credere alla docstring avrebbe
  prodotto latenze di battito nell'ordine di 10⁻⁶ ms: nel riepilogo dei percentili sarebbero
  comparse come **zeri**, che la nota di metodo 155 chiama la peggiore risposta mancante possibile.
  Un errore di documentazione sarebbe diventato una tabella di zeri sulla slide.
- **Riserve:** la conclusione è tratta dal sorgente, non da un battito osservato: nessun cluster ha
  ancora prodotto un `ServerHeartbeatSucceededEvent` in questo repository. La verifica contro un
  valore vero — un battito su rete locale deve stare fra 0,2 e 5 ms, non fra 200 e 5000 — arriva al
  Task 8. Se il numero misurato smentisse questa lettura, la voce va corretta, non difesa.
- **Usata da:** [08-il-ponte-sdam-e-i-thread-del-driver.md](08-il-ponte-sdam-e-i-thread-del-driver.md),
  `src/mongolab/infrastructure/sdam.py`, `tests/unit/test_sdam.py`

<a id="m-013"></a>
### M-013 — Quanto costa un callback che non si limita a depositare

- **Data:** 2026-09-03
- **Comando:** due sonde, duemila giri ciascuna. La prima confronta il callback vero di
  `AscoltatoreServer.description_changed` con un `put_nowait` nudo, ripetuta cinque volte; la
  seconda misura tre modi di scrivere lo stesso callback, dal più sobrio al più costoso.
- **Output:**
  ```
  1: put_nowait  0.440 us/giro | callback  1.344 us/giro | rapporto   3.06
  2: put_nowait  0.453 us/giro | callback  1.282 us/giro | rapporto   2.83
  3: put_nowait  0.480 us/giro | callback  1.334 us/giro | rapporto   2.78
  4: put_nowait  0.479 us/giro | callback  1.268 us/giro | rapporto   2.65
  5: put_nowait  0.451 us/giro | callback  1.260 us/giro | rapporto   2.79

  callback onesto      :     1.473 us/giro | rapporto      3.37
  + una frase formattata:     2.397 us/giro | rapporto      5.48
  + una tabella di Rich :   385.942 us/giro | rapporto    882.70
  ```
- **Che cosa dice:** il callback che rispetta [ADR-0019](../../docs/Decision.md#adr-0019) costa
  **meno di tre volte** un inserimento in coda nudo, e la misura è stabile su cinque ripetizioni
  (2,65–3,06). Aggiungere una `f-string` porta il rapporto a 5,5, cioè **un microsecondo in più**.
  Disegnare una tabella di Rich lo porta a 883, cioè 386 µs: tre ordini di grandezza.

  La distanza fra i due errori è il punto. A ottocento comandi al secondo — una scala plausibile per
  la demo — 386 µs per evento sono **0,31 secondi di CPU per ogni secondo di orologio**, sottratti
  al thread che il driver stava usando per accorgersi del failover. Il microsecondo della frase
  formattata, alla stessa scala, è 0,0008 secondi.
- **Conseguenza qui:** la soglia della prova `test_il_callback_costa_quanto_un_inserimento_in_coda`
  è **10**, scritta dopo la misura e non prima. Il valore lascia più del triplo di margine sul caso
  buono, così una macchina carica non fa fallire la suite, e prende comunque l'errore che ADR-0019
  ha scartato per nome con ottantotto volte di margine.
- **Riserve:** la soglia **non** prende la frase formattata, che pure il codice vieta. È una rinuncia
  consapevole: una soglia a 4 renderebbe il fallimento indistinguibile dal rumore di una macchina
  occupata, e una prova che fallisce a caso viene disattivata da qualcuno, prima o poi. Il divieto
  della formattazione nel callback resta affidato al codice e alla decisione, non a questa prova.
  Va detto anche che i numeri vengono da una macchina scarica (l'ambiente di [M-001](#m-001)): il
  rapporto è più robusto del valore assoluto, ed è per questo che la prova misura un rapporto.
- **Usata da:** [08-il-ponte-sdam-e-i-thread-del-driver.md](08-il-ponte-sdam-e-i-thread-del-driver.md),
  `tests/unit/test_sdam.py`

<a id="m-014"></a>
### M-014 — Gli eventi non arrivano tutti dallo stesso thread, e il driver usa la coda anche lui

- **Data:** 2026-09-03
- **Comando:** un listener che registra `threading.current_thread().name` a ogni callback, su un
  `MongoClient` costruito con `connect=False` verso un replica set che non esiste, seguito dai tre
  punti del sorgente che spiegano il risultato.
- **Output:**
  ```
  il thread che costruisce e chiude: MainThread
  --- dopo la costruzione ---
    TopologyOpenedEvent                <- pymongo_events_thread
    TopologyDescriptionChangedEvent    <- pymongo_events_thread
    ServerOpeningEvent                 <- pymongo_events_thread
    ServerOpeningEvent                 <- pymongo_events_thread
  --- i thread vivi mentre il client e' aperto ---
    MainThread
    pymongo_events_thread
  --- durante close() ---
    TopologyDescriptionChangedEvent    <- MainThread
    TopologyClosedEvent                <- MainThread

  synchronous/topology.py:514   self._events.put(
  synchronous/topology.py:516       self._listeners.publish_server_description_changed,
  synchronous/topology.py:201   "pymongo_events_thread"        (il PeriodicExecutor che la drena)
  synchronous/monitor.py:271    self._listeners.publish_server_heartbeat_failed(...)
  synchronous/monitor.py:306    self._listeners.publish_server_heartbeat_started(...)
  synchronous/monitor.py:334    self._listeners.publish_server_heartbeat_succeeded(...)
  ```
- **Che cosa dice:** «Events are delivered synchronously» ([S-010](../../docs/Sources.md#s-010)) è
  vero, ma non vuol dire *sullo stesso thread che ha generato il fatto*. Le due famiglie più
  rumorose — server e topologia — non vengono consegnate dal codice che scopre il cambiamento: quel
  codice fa `self._events.put(...)`, e un thread dedicato di nome `pymongo_events_thread` drena la
  coda e chiama i listener. Battiti e comandi invece arrivano davvero sul thread del monitor e su
  quello applicativo, perché lì il `publish_*` è chiamato direttamente.

  **Il driver applica a sé stesso lo schema che ADR-0019 impone all'applicazione.** Metà dei suoi
  listener passano da una coda drenata da un thread solo, che è esattamente la forma scelta qui.
  Nessuna pagina di documentazione lo dice, e vale come conferma indipendente della decisione.

  Un dettaglio secondario ma utile: `connect=False` non impedisce la pubblicazione di un
  `TopologyDescriptionChangedEvent` alla costruzione, e durante `close()` gli stessi callback
  girano sul thread **chiamante**, non più su quello degli eventi.
- **Conseguenza qui:** nessuna, ed è il punto. Il ponte non tiene stato e non ha lucchetti: che il
  callback arrivi da uno di quattro thread diversi non cambia una riga, perché la coda tiene i suoi
  lucchetti ([A-010](#a-010)). La regola resta valida anche per gli eventi che passano dalla coda
  del driver: quel thread è **uno solo**, e un callback lento lì accoda tutti gli altri cambi di
  topologia, compreso quello che annuncia il primario nuovo.
- **Riserve:** la misura è stata fatta senza cluster, quindi il thread dei battiti e quello dei
  comandi sono dedotti dal sorgente e non osservati. Il nome `pymongo_events_thread` è un dettaglio
  interno di PyMongo 4.17, non un'interfaccia pubblica: nessun codice di `mongolab` lo nomina, e
  questa voce lo cita solo come prova di dove il callback sia stato eseguito.
- **Usata da:** [08-il-ponte-sdam-e-i-thread-del-driver.md](08-il-ponte-sdam-e-i-thread-del-driver.md)

<a id="m-015"></a>
### M-015 — Un'eccezione dentro un listener non arriva a nessuno

- **Data:** 2026-09-03
- **Comando:** un `TopologyListener` il cui `opened` solleva `RuntimeError`, registrato su un
  `MongoClient` con `connect=False`, con `stderr` catturato.
- **Output:**
  ```
  il codice che costruisce il client e' arrivato fin qui: nessuna eccezione propagata
  su stderr sono finite 7 righe:
    | Traceback (most recent call last):
    |   File ".../site-packages/pymongo/monitoring.py", line 1752, in publish_topology_opened
    |     subscriber.opened(event)
    |     ~~~~~~~~~~~~~~~~~^^^^^^^
    |   File ".../probe/eccezione.py", line 12, in opened
    |     raise RuntimeError("il listener e' rotto, e nessuno lo sa")
    | RuntimeError: il listener e' rotto, e nessuno lo sa
  ```
- **Che cosa dice:** PyMongo avvolge ogni chiamata a un listener in un `try/except Exception` e
  passa il controllo a `_handle_exception`, che stampa il traceback su `stderr` e ritorna. Il
  driver continua, il codice chiamante non vede niente, e il listener rotto **resta registrato**:
  solleverà di nuovo al prossimo evento, altre sette righe, all'infinito.
- **Conseguenza qui:** è la seconda ragione, indipendente dalla velocità, per cui questi callback
  fanno tre cose sole. Meno codice gira dentro un listener, meno cose possono sollevare senza che
  nessuno se ne accorga. E l'accorgersene, durante il talk, è impossibile: la TUI di Rich
  ([ADR-0050](../../docs/Decision.md#adr-0050)) tiene il terminale, e un traceback che arriva sotto
  un `Live` viene sovrascritto al primo aggiornamento. Un ponte rotto si presenterebbe come una
  cronaca che smette di aggiornarsi, senza messaggi, davanti a una sala.
- **Riserve:** il buco è **dichiarato, non chiuso**. Nessun meccanismo di `mongolab` oggi si accorge
  che un listener sta sollevando. La sede in cui si può chiudere è il Task 11, dove il composition
  root vede sia il ponte sia la TUI e può controllare che la cronaca stia procedendo; questa voce
  esiste perché al Task 11 la domanda non venga dimenticata.
- **Usata da:** [08-il-ponte-sdam-e-i-thread-del-driver.md](08-il-ponte-sdam-e-i-thread-del-driver.md)

<a id="m-016"></a>
### M-016 — Ventotto rotture deliberate sul ponte SDAM, e una che non era una rottura

- **Data:** 2026-09-03
- **Comando:** ventotto modifiche al solo `src/mongolab/infrastructure/sdam.py`, una alla volta,
  ciascuna seguita da `pytest -q tests/unit` e dal ripristino da copia. Lo script porta le tre
  protezioni che le note 157–159 hanno imposto dopo [M-011](#m-011): esito letto dal **codice di
  uscita mappato per nome**, `PYTHONDONTWRITEBYTECODE=1` con i `__pycache__` rimossi prima di ogni
  corsa, e la verifica che ogni sostituzione cambi davvero il file. Ne ha aggiunta una quarta, e il
  perché sta nelle riserve: un **limite di 90 secondi** per corsa.
- **Output:**
  ```
  BASE   VERDE  193 passed
   1. un errore non fa irraggiungibile              ROSSO   2 failed, 191 passed
   2. il ripiego e' irraggiungibile                 ROSSO   1 failed, 192 passed
   3. nessun ripiego, solo la chiave                ROSSO   1 failed, 192 passed
   4. RSOther diventa sconosciuto                   ROSSO   1 failed, 192 passed
   5. un tipo di server non mappato                 ROSSO   2 failed, 191 passed
   6. una forma di topologia non mappata            ROSSO   1 failed, 192 passed
   7. il ritardo assente diventa zero               ROSSO   1 failed, 192 passed
   8. il ritardo resta in secondi                   ROSSO   1 failed, 192 passed
   9. l'errore perde il nome della classe           ROSSO   1 failed, 192 passed
  10. la porta assente diventa None a schermo       ROSSO   1 failed, 192 passed
  11. i server non si riordinano                    ROSSO   2 failed, 191 passed
  12. il nome del set si perde                      ROSSO   1 failed, 192 passed
  13. un ruolo immutato emette lo stesso            ROSSO   1 failed, 192 passed
  14. un ruolo cambiato non emette                  ROSSO   5 failed, 188 passed
  15. l'indirizzo viene da prima                    VERDE  193 passed        <- non e' una rottura
  16. prima e dopo si scambiano                     ROSSO   1 failed, 192 passed
  17. una topologia identica emette                 ROSSO   3 failed, 190 passed
  18. il battito in attesa e' un campione           ROSSO   1 failed, 192 passed
  19. il battito resta in secondi                   ROSSO   1 failed, 192 passed
  20. il battito ha un altro nome                   ROSSO   1 failed, 192 passed
  21. tutti i comandi passano                       ROSSO   2 failed, 191 passed
  22. i microsecondi diventano millisecondi al contrario  ROSSO 2 failed, 191 passed
  23. il battito fallito parla                      ROSSO   1 failed, 192 passed
  24. l'apertura di un server parla                 ROSSO   1 failed, 192 passed
  25. drena guarda ma non svuota                    ROSSO   1 failed, 192 passed
  26. gli ascoltatori sono tre                      ROSSO   1 failed, 192 passed
  27. ogni ascoltatore ha la sua coda               ROSSO   4 failed, 189 passed
  28. il callback disegna una tabella               ROSSO   1 failed, 192 passed
  FINE   VERDE  193 passed
  ```
- **Che cosa dice:** ventisette su ventotto catturate, **senza prove nuove aggiunte dopo**. È il
  contrario di [M-011](#m-011), dove quattro guardie su ventuno mancavano: la differenza è che qui
  le prove sono state scritte contro un contratto già misurato (le unità di [M-012](#m-012), il
  costo di [M-013](#m-013)) invece che contro un'idea del comportamento.

  La rottura 28 merita una riga a sé, perché è quella che l'ADR-0019 ha scartato per nome: mettere
  una tabella di Rich dentro il callback fa fallire la prova cronometrata, e la fa fallire con tre
  ordini di grandezza di margine. Il vincolo non è un principio, è una cosa che si vede.
- **Riserve — la quindicesima rottura non era una rottura, e serve una nota nuova.**

  Scambiando `new_description.address` con `previous_description.address` la suite resta verde. La
  prima ipotesi — manca una guardia, come nella 4 di M-011 — è **sbagliata**. Il driver pubblica
  quel cambio in un punto solo di tutto il suo codice (`synchronous/topology.py:516`), e la
  descrizione vecchia la ricava indicizzando per l'indirizzo di quella nuova
  (`synchronous/topology.py:495`, `sd_old = td_old._server_descriptions[server_description.address]`).
  I due lati portano **sempre** lo stesso indirizzo, per costruzione: non sono due letture di cui
  una giusta, sono la stessa lettura scritta in due modi.

  La cura non è una prova. Una prova che costruisse a mano un cambio con due indirizzi diversi
  passerebbe da rossa a verde e sembrerebbe una guardia, ma difenderebbe un caso che il driver non
  può produrre: copertura senza verità. La cura è verificare l'invariante alla fonte e scriverlo
  dove il codice lo usa, che è quello che il docstring di `description_changed` adesso fa.

  **Nota di metodo 161:** le tre uscite della nota 144 e la quarta della 153 danno per scontato che
  una modifica cambi il comportamento. Prima di concludere che manca una guardia, va escluso che
  manchi la **differenza**.

  **La quarta protezione, e perché è servita.** La rottura 25 nella sua prima forma — «`drena`
  guarda ma non svuota», scritta come *riprendi dalla coda e rimettici dentro quello che prendi* —
  è un ciclo infinito. La batteria si è piantata dopo sette minuti senza dire niente: è la nota 153,
  arrivata al primo colpo su questo file. Da lì il limite di 90 secondi per corsa, con un esito
  `APPESO` che ha un nome suo e non si confonde con un fallimento. La rottura è stata poi riscritta
  in una forma che termina (`return list(self._coda.queue)`) e catturata.
- **Usata da:** [08-il-ponte-sdam-e-i-thread-del-driver.md](08-il-ponte-sdam-e-i-thread-del-driver.md),
  [registro-sviluppo-app.md](registro-sviluppo-app.md)

---

<a id="m-017"></a>
### M-017 — `$count` su zero documenti non risponde zero: non risponde

- **Data:** 2026-09-03
- **Comando:** un `MongoClient` verso lo stack 01, una collezione appena creata e poi una con due
  documenti e un filtro che non prende niente.
- **Output:**
  ```
  collezione inesistente:
    $count            -> []
    $match+$count     -> []
    $group _id:null   -> []
    count_documents   -> 0
  con due documenti, ma filtro che non prende niente:
    $match+$count     -> []
    $count            -> [{'quanti': 2}]
  ```
- **Che cosa dimostra:** uno stadio di aggregazione che non riceve documenti non ne emette. Non è una
  particolarità di `$count`: anche `$group` con `_id: null`, che in SQL corrisponderebbe a un
  `COUNT(*)` su zero righe e darebbe zero, qui tace. L'unico che risponde zero è `count_documents`,
  che non è una pipeline.
- **Perché è stata fatta:** perché il contratto condiviso del Task 8 ha smentito il doppio alla prima
  esecuzione. `InMemoryStore` restituiva `[{"quanti": 0}]`, ed è stato scritto così senza malizia:
  `len(documenti)` di una lista vuota fa zero, e la riga sembrava giusta. La misura ha detto chi
  aveva ragione, e il doppio è stato corretto.
- **Riserve:** la differenza è pericolosa proprio perché nessuno solleva da nessuna delle due parti.
  Chi legge `risultato[0]["quanti"]` passa nella suite veloce e prende `IndexError` contro il
  cluster — nella scena in cui la collezione è vuota, cioè al primo fotogramma. Vale la pena leggerla
  accanto alla **nota 155**: lì il difetto era una risposta mancante scambiata per uno zero, qui è
  uno zero inventato dove la risposta manca. Lo stesso errore, dai due lati.
- **Usata da:** [09-adattatori-veri-e-contratto-condiviso.md](09-adattatori-veri-e-contratto-condiviso.md),
  [registro-sviluppo-app.md](registro-sviluppo-app.md)

<a id="m-018"></a>
### M-018 — La credenziale passata come argomento non compare in nessuno dei tre posti in cui la si cercava

- **Data:** 2026-09-03
- **Comando:** una sonda che si collega allo stack 02 con `username=`/`password=`, poi con una
  password sbagliata, e in tutti i casi cerca la stringa del segreto dentro il messaggio d'errore e
  dentro `repr(client)`. La sonda non stampa mai il valore vero.
- **Output:**
  ```
  === 02 replica set, dall'host, replicaSet=rs0 — la trappola ===
  la password compare nel messaggio? False
  === password sbagliata: il messaggio la contiene? ===
  tipo: OperationFailure
  la password compare nel messaggio? False
  messaggio: Authentication failed., full error: {'ok': 0.0, 'errmsg': 'Authentication failed.',
             'code': 18, 'codeName': 'AuthenticationFailed', ...}
  === e nel repr del client? ===
  la password compare nel repr? False
  repr (primi 300): MongoClient(host=['localhost:27021'], document_class=dict, tz_aware=False,
                                connect=True, authsource='admin', directconnection=True)
  ```
- **Che cosa dimostra:** passata come argomento — non dentro l'URI — la password non esce da PyMongo
  né in un `ServerSelectionTimeoutError`, né in un `OperationFailure`, né nel `repr` del client. Il
  `repr` mostra `authsource` e `directconnection` e non mostra `password`. La misura dice anche
  un'altra cosa, che si legge nella riga stessa: `tz_aware=False` è l'impostazione **predefinita**.
- **Perché è stata fatta:** era un punto aperto dichiarato — «come le prove di integrazione ricevono
  la credenziale senza violare ADR-0054». La risposta è che la ricevono come argomento, e che il
  punto scoperto non era PyMongo ma il codice delle prove: da lì `Credenziali` con `field(repr=False)`.
- **Riserve:** vale per la versione di PyMongo installata qui (4.17) e per questi tre percorsi. Non è
  una promessa dell'API e non è scritta in nessuna pagina: se un giorno un messaggio d'errore
  includesse la stringa di connessione completa, questa misura non lo intercetterebbe. E resta il buco
  dichiarato in `Credenziali`: `credenziali.password` stampato a mano si vede, perché non può essere
  altrimenti.
- **Usata da:** [09-adattatori-veri-e-contratto-condiviso.md](09-adattatori-veri-e-contratto-condiviso.md)

<a id="m-019"></a>
### M-019 — Un replica set sano, visto dall'host, si legge `ReplicaSetNoPrimary`

- **Data:** 2026-09-03
- **Comando:** `MongoClient("mongodb://localhost:27021/", replicaSet="rs0", …)` dall'host, contro lo
  stack 02 avviato e sano, con `serverSelectionTimeoutMS=4000`.
- **Output:**
  ```
  FALLITA dopo 4.2s
  tipo: ServerSelectionTimeoutError
  mongo-rs-2:27017: [Errno 8] nodename nor servname provided, or not known …,
  mongo-rs-1:27017: [Errno 8] nodename nor servname provided, or not known …,
  mongo-rs-3:27017: [Errno 8] nodename nor servname provided, or not known …,
  Timeout: 4.0s, Topology Description: <TopologyDescription topology_type: ReplicaSetNoPrimary, …>
  topology_type_name: ReplicaSetNoPrimary
    server: ('mongo-rs-2', 27017) Unknown errore: AutoReconnect
    server: ('mongo-rs-1', 27017) Unknown errore: AutoReconnect
    server: ('mongo-rs-3', 27017) Unknown errore: AutoReconnect
  ```
  Con `directConnection=True` sulla stessa porta, invece:
  ```
  topology_type_name: Single
  replica_set_name: None
    server: ('localhost', 27021) RSPrimary 0.0017071250003937166
  hello.setName: rs0
  hello.hosts: ['mongo-rs-1:27017', 'mongo-rs-2:27017', 'mongo-rs-3:27017']
  hello.me: mongo-rs-1:27017
  conta lab.ordini: 50000
  ```
- **Che cosa dimostra:** è ADR-0012 e ADR-0021 visti dal lato che fa male. Il client si collega alla
  porta pubblicata, chiede la configurazione del set, e la configurazione gli risponde con i nomi di
  servizio Compose — che dentro la rete esistono e sull'host no. Tutti e tre i membri falliscono la
  risoluzione DNS, e la topologia che ne risulta è **indistinguibile da un replica set che ha perso il
  primario**: stesso nome, stessi tre server sconosciuti, stesso errore di selezione. Quattro secondi
  e due decimi per scoprirlo.
- **Perché è stata fatta:** per decidere come le prove di integrazione del Task 8 si collegano al 02.
  La risposta è `directConnection=True`, e la conseguenza è una riserva: il **ruolo** si legge giusto
  (`RSPrimary` → `PRIMARIO`), la **forma** no (`Single` → `SINGOLA`). `REPLICA_SET_CON_PRIMARIO` non è
  verificabile dall'host, e lo sarà al Task 12 dall'interno della rete.
- **Riserve:** la misura è fatta su macOS con Docker Desktop, dove la rete Compose non è raggiungibile
  dall'host. Su Linux con `network_mode: host`, o con voci in `/etc/hosts`, i nomi risolverebbero e il
  fenomeno non si presenterebbe — il che lo rende **peggiore**, non migliore: chi prova su una
  macchina e non sull'altra vede due comportamenti diversi senza aver cambiato una riga.
- **Usata da:** [09-adattatori-veri-e-contratto-condiviso.md](09-adattatori-veri-e-contratto-condiviso.md)

<a id="m-020"></a>
### M-020 — Su 7.0.40 nessun chunk ha il campo `ns`, e cercarlo restituisce zero senza protestare

- **Data:** 2026-09-03
- **Comando:** attraverso il mongos dello stack 03, un documento qualunque di `config.chunks` e tre
  conteggi.
- **Output:**
  ```
  versione mongos: 7.0.40
  un chunk qualunque, campi: ['_id', 'history', 'lastmod', 'max', 'min', 'onCurrentShardSince',
                              'shard', 'uuid']
  quanti chunk hanno il campo ns? 0
  chunk totali: 5
  query per ns='lab.ordini': 0
  ```
  E l'unione fatta nei due modi, sulla stessa collezione:
  ```
  join su uuid: [{'_id': 'shard1rs', 'chunk': 2}, {'_id': 'shard2rs', 'chunk': 2}]
  join su _id:  []
  ```
- **Che cosa dimostra:** l'unione va fatta su `uuid`, come prescrive [A-013](#a-013), e ogni altra
  chiave dà la lista vuota. Il punto non è che sia vuota: è che è vuota **in silenzio**. Nessuna
  eccezione, nessun avvertimento, un numero plausibile — zero chunk — al posto di quattro.
- **Perché è stata fatta:** perché la scena del Blocco 3 poggia sul fatto che chunk e documenti non si
  deducono l'uno dall'altro, e un ispettore che riportasse zero chunk direbbe «i dati non sono
  distribuiti» esattamente nel momento in cui lo sono.
- **Riserve:** è una constatazione su 7.0.40, non una regola di versione: il manuale non afferma da
  nessuna parte che `ns` sia stato tolto, e la pagina di `config` avverte che «The config database is
  internal. Applications and administrators should not modify or depend on its content during normal
  operation». Questo ispettore ci dipende, perché non c'è altro modo di contare i chunk. La difesa è
  la prova di integrazione sullo stack 03, che diventa rossa il giorno in cui il formato cambia.
- **Usata da:** [09-adattatori-veri-e-contratto-condiviso.md](09-adattatori-veri-e-contratto-condiviso.md)

<a id="m-021"></a>
### M-021 — `ordered=False` non fa guadagnare niente su questo carico

- **Data:** 2026-09-03
- **Comando:** stack 01, lotti da 500 documenti del `DataGenerator`, 40 lotti per configurazione
  (ventimila documenti), tre giri alternando `ordered=True` e `ordered=False`, ogni corsa su un
  database proprio poi cancellato.
- **Output:**
  ```
  giro 0  ordered=True   totale   123.1 ms  mediana lotto   2.63 ms  p95   4.70 ms   162426 doc/s
  giro 0  ordered=False  totale   115.9 ms  mediana lotto   2.70 ms  p95   3.59 ms   172497 doc/s
  giro 1  ordered=True   totale   134.0 ms  mediana lotto   2.69 ms  p95  11.27 ms   149307 doc/s
  giro 1  ordered=False  totale   113.7 ms  mediana lotto   2.54 ms  p95   3.81 ms   175855 doc/s
  giro 2  ordered=True   totale   115.1 ms  mediana lotto   2.48 ms  p95   6.18 ms   173779 doc/s
  giro 2  ordered=False  totale   118.0 ms  mediana lotto   2.55 ms  p95   7.56 ms   169500 doc/s
  ```
- **Che cosa dimostra:** le mediane per lotto stanno fra 2,48 e 2,70 ms in **entrambe** le
  configurazioni, e i totali si sovrappongono — al giro 2 l'ordinato è perfino più veloce del non
  ordinato. Su questo carico la scelta non si vede. Il p95 è più mosso in tutti e due i sensi, e con
  tre giri non basta a dire niente.
- **Perché è stata fatta:** `ordered=False` è la scelta abituale per il caricamento massivo, e stava
  per essere adottata per abitudine. La regola del repository è che una scelta di prestazioni si
  misura prima di scriverla (**nota 162**): misurata, non c'era niente da guadagnare, e
  `ordered=True` — il predefinito — ha in cambio un errore più semplice da leggere.
- **Riserve:** è un'istanza singola su loopback, senza rete, senza `w: majority` e senza contesa. Le
  tre condizioni in cui il confronto può ribaltarsi sono tutte fuori da questa misura: una rete vera
  con latenza, un replica set che aspetta la maggioranza, e soprattutto uno **sharded cluster**, dove
  un lotto si spezza fra shard e `ordered=True` costringe a rispettarne la sequenza. Se il Blocco 3
  mostrerà scritture lente, questa è la prima riga da rimisurare.
- **Usata da:** [09-adattatori-veri-e-contratto-condiviso.md](09-adattatori-veri-e-contratto-condiviso.md)

<a id="m-022"></a>
### M-022 — La stessa verifica, verde sul doppio e rossa contro MongoDB

- **Data:** 2026-09-03
- **Comando:** `una_pagina_di_zero_documenti_e_vuota`, aggiunta al contratto condiviso ed eseguita
  dalle due parti prima di scrivere la guardia in `find_page`.
- **Output:**
  ```
  ### DOPPIO ###
  2 passed, 10 deselected in 0.02s
  ### ORIGINALE ###
  >       assert archivio.find_page({}, quanti=0) == ()
  E       AssertionError
  FAILED tests/integration/test_contratto_archivio.py::
         test_l_adattatore_rispetta_il_contratto[una_pagina_di_zero_documenti_e_vuota]
  ```
- **Che cosa dimostra:** è il Passo 4 del Task 8 che funziona, colto nell'atto. La stessa funzione,
  lo stesso corpo, due implementazioni della stessa porta: una passa e l'altra no, e la differenza è
  che `limit(0)` per MongoDB significa «nessun limite» ([A-011](#a-011)) mentre per una lista Python
  `[salta:salta+0]` significa «niente». Senza la coppia, il difetto sarebbe stato scoperto in scena,
  su una schermata che mostra cinquantamila righe dove ne erano state chieste zero.
- **Perché è stata fatta:** per scrivere la guardia dopo averla vista servire, non prima. È la
  **nota 159** applicata all'unico caso in cui è facile applicarla: quando esiste già una seconda
  implementazione che si comporta bene, il caso in cui la guardia manca non va costruito — c'è.
- **Riserve:** la coppia non è simmetrica. Una verifica che passa da entrambe le parti non dimostra
  che il doppio sia fedele: dimostra che lo è **su quel caso**. Il contratto ha dodici funzioni, e
  il numero di comportamenti di MongoDB è molto più grande di dodici.
- **Usata da:** [09-adattatori-veri-e-contratto-condiviso.md](09-adattatori-veri-e-contratto-condiviso.md)

---

<a id="m-023"></a>
### M-023 — La password letta da uno `stdin` che non è un terminale

- **Data:** 2026-09-03
- **Comando:** `mongodump` 100.18.0 dentro `mongo-rs-1`, **senza** `-p`, con il segreto scritto sul
  tubo e il tubo chiuso subito dopo:
  ```sh
  docker exec -i mongo-rs-1 mongodump \
      --host rs0/mongo-rs-1:27017,mongo-rs-2:27017,mongo-rs-3:27017 \
      --username admin --authenticationDatabase admin \
      --readPreference=secondary --oplog --out /tmp/probe9
  # sullo stdin: la password, un a capo, e la chiusura
  ```
- **Output:** codice d'uscita **0**, `stdout` **vuoto**, e su `stderr`:
  ```
  2026-09-03T12:41:52.688+0000	reading password from standard input
  Enter password for mongo user:
  2026-09-03T12:41:52.707+0000	writing `lab.ordini` to `/tmp/probe9/lab/ordini.bson`
  2026-09-03T12:41:52.754+0000	done dumping `lab.ordini` (50000 documents)
  2026-09-03T12:41:52.756+0000	writing captured oplog to ``
  2026-09-03T12:41:52.756+0000		dumped 1 oplog entry
  ```
- **Che cosa dimostra:** tre cose che l'adattatore usa tutte. Che lo strumento **chiede** la
  password quando `-p` manca e la **legge dal tubo** anche se il tubo non è un terminale, il che
  rende praticabile tenerla fuori da `argv` ([M-025](#m-025)). Che il `-i` di `docker exec` è
  obbligatorio: senza, lo `stdin` del client non è collegato al processo dentro il container e la
  password non arriva. E che la riga del prompt, `Enter password for mongo user:`, esce **senza il
  prefisso dell'orario** che tutte le altre righe hanno — è la ragione per cui il riconoscitore
  dell'adattatore, che quel prefisso lo pretende, la scarta senza doverla nominare.
- **Perché è stata fatta:** perché il Passo 2 del Task 9 prescriveva la lista di argomenti al posto
  della stringa di shell «perché la stringa fa comparire la password nella tabella dei processi», e
  bisognava sapere se esistesse un posto dove metterla che non fosse `argv`. Esiste.
- **Riserve:** il testo del prompt non è un'interfaccia, e la misura vale per la **100.18.0**. Una
  versione che smettesse di leggere da uno `stdin` non interattivo non romperebbe una prova unitaria
  — le romperebbe tutte quelle di integrazione, che è dove il buco si vedrebbe. Non è stato
  verificato che cosa succeda se il processo muore **prima** che la password sia scritta: sarebbe un
  `BrokenPipeError`, e non è mai stato riprodotto.
- **Usata da:** [10-processi-esterni-e-il-verdetto-che-manca.md](10-processi-esterni-e-il-verdetto-che-manca.md)

---

<a id="m-024"></a>
### M-024 — `mongorestore` perde cinquantamila documenti ed esce **zero**

- **Data:** 2026-09-03
- **Comando:** lo stesso restore, due volte di fila sulla **stessa** destinazione. Il primo la
  riempie, il secondo ricade su `_id` che esistono già:
  ```sh
  docker exec -i mongo-rs-1 mongorestore \
      --host rs0/mongo-rs-1:27017,mongo-rs-2:27017,mongo-rs-3:27017 \
      --username admin --authenticationDatabase admin \
      --nsInclude 'lab.*' --nsFrom 'lab.*' --nsTo 'mongolab_prove_m9.*' /tmp/probe9
  ```
- **Output:** il primo giro, codice **0**:
  ```
  2026-09-03T12:41:55.254+0000	finished restoring `mongolab_prove_m9.ordini` (50000 documents, 0 failures)
  2026-09-03T12:41:55.254+0000	50000 document(s) restored successfully. 0 document(s) failed to restore.
  ```
  il secondo giro, cinquantamila righe come questa —
  ```
  2026-09-03T12:41:55.771+0000	continuing through error: E11000 duplicate key error collection: mongolab_prove_m9.ordini index: _id_ dup key: { _id: 0 }
  ```
  — e poi, **codice d'uscita 0**:
  ```
  2026-09-03T12:42:04.982+0000	finished restoring `mongolab_prove_m9.ordini` (0 documents, 50000 failures)
  2026-09-03T12:42:04.982+0000	0 document(s) restored successfully. 50000 document(s) failed to restore.
  ```
- **Che cosa dimostra:** che il codice d'uscita di `mongorestore` **non** è il verdetto
  sull'operazione. Lo strumento sa di aver perso tutto, lo scrive, e poi dichiara successo al
  sistema operativo. Chi controlla il processo nel modo in cui si controlla un processo — guardando
  l'intero che restituisce — riceve «riuscito». È il motivo di
  [ADR-0084](../../docs/Decision.md#adr-0084): l'adattatore legge la riga di sommario e solleva
  `RestoreIncompleto`, mettendo il verdetto che lo strumento non ha messo.

  La stessa esecuzione chiude altre due domande. `--nsInclude` è ciò che **filtra**: il dump
  conteneva `admin.system.users` e `admin.system.version`, e il restore con `--nsInclude 'lab.*'`
  non li nomina, toccando la sola `ordini`. E `--oplogReplay` non convive con la riscrittura dei
  nomi, in nessuna delle due forme — con gli inclusi:
  ```
  2026-09-03T12:42:05.073+0000	Failed: cannot use --oplogReplay with includes specified
  ```
  con le sole rinomine:
  ```
  2026-09-03T12:43:34.236+0000	Failed: cannot use --oplogReplay with namespace renames specified
  ```
  entrambe con **codice 1**, cioè entrambe dette nel modo giusto: qui il verdetto c'è.
- **Perché è stata fatta:** per scrivere `restore` sapendo che cosa lo strumento garantisce.
  L'ordine dei fatti è stato l'inverso di quello raccontato qui: la prima stesura delle prove di
  integrazione dava per **idempotente** un restore ripetuto, l'adattatore ha sollevato
  `RestoreIncompleto`, e la parte sbagliata era l'assunzione nella docstring della prova.
- **Riserve:** la riga di sommario è **testo**, non un'interfaccia. Se una versione la riscrive, la
  guardia dell'adattatore non diventa sbagliata: diventa **muta**, che è peggio, e la difesa è la
  prova di integrazione che pretende `RestoreIncompleto` sul secondo giro. Il caso complementare —
  `--nsFrom`/`--nsTo` **senza** `--nsInclude`, che nella prima sonda aveva riscritto anche `lab` e
  toccato `admin/system.users.bson` — è stato osservato una volta e **non ripetuto** qui, perché
  ripeterlo significa far passare `mongorestore` sugli utenti dell'amministratore dello stack.
- **Usata da:** [10-processi-esterni-e-il-verdetto-che-manca.md](10-processi-esterni-e-il-verdetto-che-manca.md)

---

<a id="m-025"></a>
### M-025 — `-p` fra gli argomenti si legge nella tabella dei processi del container

- **Data:** 2026-09-03
- **Comando:** un `mongorestore` lanciato **apposta** nel modo sbagliato, con `-p <segreto>` come
  elemento di `argv`, mentre da un secondo `exec` un campionamento ogni 50 ms guarda:
  ```sh
  docker exec mongo-rs-1 ps -eo args
  ```
- **Output:** 16 campioni su 16 contengono il processo, con una sola riga distinta. **Il segreto è
  stato sostituito dallo script prima di stampare** — la sonda non lo scrive mai, e ciò che asserisce
  è il valore booleano sulla riga grezza, `il segreto compare nella riga: True`:
  ```
  il segreto compare nella riga: True
  mongorestore --host rs0/mongo-rs-1:27017,mongo-rs-2:27017,mongo-rs-3:27017 --username admin
  --authenticationDatabase admin -p <PASSWORD> --nsInclude lab.* --nsFrom lab.* --nsTo
  mongolab_prove_m9.* /tmp/probe9
  ```
- **Che cosa dimostra:** che **la lista di argomenti non basta**. Il Passo 2 del piano del Task 9
  chiede la lista al posto della stringa di shell perché «una stringa di shell la fa comparire nella
  tabella dei processi di chiunque guardi»; la misura dice che a comparire nella tabella dei processi
  è `argv`, e ad `argv` non importa da dove è arrivato — lista o stringa, il risultato è lo stesso.
  Chiunque abbia un `exec` su quel container, per i secondi in cui il dump gira, legge la password
  dell'amministratore. La lista resta comunque la scelta giusta, per la ragione che il piano non
  nomina: senza shell non c'è nessuno a interpretare uno spazio, un apice o un `$` dentro una
  password o dentro un percorso. Ma la cosa che protegge il segreto è **omettere `-p`** e scriverlo
  sullo `stdin` ([M-023](#m-023)).
- **Perché è stata fatta:** perché la motivazione scritta nel piano era plausibile e incompleta, ed
  è il genere di frase che nessuno rimette in discussione perché sta accanto alla regola giusta.
- **Riserve:** la finestra è breve — il segreto è visibile solo mentre il processo vive — e questo
  la rende più insidiosa, non meno: un campionamento a 50 ms l'ha presa 16 volte su 16, e un
  osservatore paziente non ha bisogno di essere fortunato. Non è stato verificato se `mongodump`
  riscriva `argv` dopo l'avvio, come fanno alcuni strumenti: sulla 100.18.0 evidentemente no, e
  contarci sarebbe comunque appoggiarsi a un comportamento non documentato.
- **Usata da:** [10-processi-esterni-e-il-verdetto-che-manca.md](10-processi-esterni-e-il-verdetto-che-manca.md)

---

<a id="m-026"></a>
### M-026 — La barra di `mongorestore` conta byte, e li conta in base 1024

- **Data:** 2026-09-03
- **Comando:** la dimensione vera del file, letta dentro il container sullo stesso `.bson` che quel
  restore stava leggendo, messa accanto alla barra che lo annunciava:
  ```sh
  docker exec mongo-rs-1 stat -c '%s %n' /tmp/probe9/lab/ordini.bson
  ```
- **Output:**
  ```
  6094260 /tmp/probe9/lab/ordini.bson
  2026-09-03T12:42:04.982+0000	[########################]  mongolab_prove_m9.ordini  5.81MB/5.81MB  (100.0%)
  ```
  e, sulla collezione da 400 000 documenti della prima sonda, `48760014` byte annunciati come
  `46.5MB`.
- **Che cosa dimostra:** che `MB` qui vale 1024², non 1000². `6094260 / 1024² = 5,8129` — che
  arrotondato è il `5,81` stampato; in base 1000 farebbe `6,09`, e la barra direbbe un altro numero.
  Sul file grande la distanza è ancora più netta: `46,5 × 1024² = 48 758 784`, lontano dai
  `48 760 014` veri dello **0,003%**, mentre `46,5 × 1000² = 46 500 000` sbaglia del **4,6%**. La
  seconda cosa che dimostra è che le barre dei due strumenti contano **unità diverse**: quella di
  `mongodump` conta documenti (`1863086/2000000`), quella di `mongorestore` conta byte.
- **Perché è stata fatta:** perché senza un metro esterno la prova sulla conversione sarebbe stata
  un `1024**2` scritto nella prova confrontato con un `1024**2` scritto nel codice, cioè la verifica
  che due copie della stessa scelta coincidono. La misura è la sola cosa che rende quell'asserzione
  un'asserzione. Era anche l'unica mutazione, delle sei provate sull'adattatore, che nessuna prova
  vedeva.
- **Riserve:** l'arrotondamento a due cifre lascia margine — su `5,81` la base 1000 e la base 1024
  distano abbastanza da non confondersi, ma su file di certe dimensioni potrebbero. Il file grande
  è la misura che decide, e sta qui per quello. Resta dichiarato che `Progress.completati` non porta
  con sé l'unità: per un dump sono documenti, per un restore byte, e chi legge deve saperlo dal
  contesto.
- **Usata da:** [10-processi-esterni-e-il-verdetto-che-manca.md](10-processi-esterni-e-il-verdetto-che-manca.md)

---

<a id="m-027"></a>
### M-027 — `Live` di Rich avvia un thread demone, e `refresh_per_second` smette di contare quando lo si spegne

- **Data:** 2026-09-03
- **Comando:** contare i thread vivi **mentre** il display è acceso — la prima sonda li ha contati
  dopo `stop()` e ne ha trovati zero, che è vero e inutile:
  ```python
  prima = set(threading.enumerate())
  with Live("x", console=console) as live:          # e poi: auto_refresh=False
      nuovi = set(threading.enumerate()) - prima
      print([(t.name, type(t).__name__, t.daemon) for t in nuovi])
      print(nuovi == {live._refresh_thread})
  ```
  e, per il secondo pezzo, `Live(..., auto_refresh=False, refresh_per_second=1000)` lasciato mezzo
  secondo senza chiamare niente, misurando i byte scritti sulla console.
- **Output:**
  ```
  predefinito:      [('Thread-1', '_RefreshThread', True)]   identico a live._refresh_thread: True
  auto_refresh=False: []
  auto_refresh=False, refresh_per_second=1000, 0.5 s di attesa: 7 byte scritti
  ```
- **Che cosa dimostra:** due cose, e la seconda è la sorpresa. La prima: con le impostazioni
  predefinite `Live.start()` avvia un `_RefreshThread` demone che gira per conto suo — il sorgente
  lo mostra chiamare `self.live.refresh()` dentro `with self.live._lock:`. Quindi
  [ADR-0019](../../docs/Decision.md#adr-0019), che prometteva «un solo thread tocca `Live`», **non
  sarebbe stata mantenuta** dal codice che credeva di mantenerla. Non è insicuro: il lucchetto c'è.
  È però esattamente la condizione da cui ADR-0019 voleva stare alla larga — una correttezza che
  poggia su un dettaglio privato e non documentato ([A-015](#a-015),
  [S-018](../../docs/Sources.md#s-018)). La seconda: spento `auto_refresh`, `refresh_per_second`
  non ha più nessun effetto. Mille al secondo per mezzo secondo scrivono sette byte, cioè niente:
  nessuno legge più quel numero. Anche `update()` senza `refresh=True` non disegna.
- **Perché è stata fatta:** perché il Passo 1 del Task 10 chiedeva di passare `refresh_per_second`
  «esplicitamente, con il valore scritto accanto alla ragione», e prima di scrivere una ragione
  accanto a un numero conviene accertarsi che il numero faccia qualcosa. Non lo faceva.
- **Riserve:** vale per `rich` 15.0.0. `_RefreshThread` è privato e può cambiare o sparire in una
  versione qualunque: è la ragione per cui la guardia in
  `test_mentre_la_tui_e_accesa_non_nasce_nessun_altro_thread` conta i thread invece di nominare la
  classe — se Rich cambiasse il nome la prova continuerebbe a valere, se cambiasse il
  **comportamento** fallirebbe, che è l'ordine giusto. Non è stato verificato se un terminale vero
  (qui la console scriveva su `StringIO` con `force_terminal=True`) cambi il conteggio dei byte;
  cambierebbe il numero, non il fatto che sia sostanzialmente zero.
- **Usata da:** [11-tre-rese-e-un-solo-thread-che-disegna.md](11-tre-rese-e-un-solo-thread-che-disegna.md)

---

<a id="m-028"></a>
### M-028 — Un disegno della schermata costa 0,76 ms nel caso peggiore

- **Data:** 2026-09-03
- **Comando:** cinquecento giri di `RichTui.aggiorna()` sulla scena più cara che il progetto
  produce — tre server, cioè il replica set scoperto ([M-029](#m-029)), e la cronaca piena a
  ventuno righe — con il primo giro scartato perché paga la costruzione dei renderable:
  ```python
  console = Console(file=io.StringIO(), force_terminal=True, width=100, height=30)
  tui = RichTui(OrologioFermo(), console=console)
  tui.emit(TopologyChanged(ISTANTE, TRE, TRE))
  for i in range(RIGHE_CRONACA):
      tui.emit(WriteSucceeded(ISTANTE, i, 12.345))
  with tui.acceso():
      tui.aggiorna()
      for giro in range(500):
          tui.emit(LatencySampled(ISTANTE, "insert_many", 12.0 + giro % 7))
          prima = time.perf_counter()
          tui.aggiorna()
          misure.append((time.perf_counter() - prima) * 1000.0)
  ```
- **Output:** tre esecuzioni di seguito, su Apple M1 Pro, Python 3.13.15, `rich` 15.0.0:
  ```
  giri=500  mediana_ms=0.778  minimo_ms=0.732  massimo_ms=9.078  p95_ms=1.032
  giri=500  mediana_ms=0.764  minimo_ms=0.734  massimo_ms=1.409  p95_ms=0.837
  giri=500  mediana_ms=0.742  minimo_ms=0.729  massimo_ms=0.969  p95_ms=0.827
  ```
  Sulla schermata sbagliata di prima — otto server e sedici righe — le stesse tre esecuzioni
  davano `1.327`, `1.323` e `1.331` ms: un pannello più alto costa quasi il doppio, il che è
  coerente e non sorprendente.
- **Che cosa dimostra:** che il ritmo di disegno non è un vincolo economico. A 0,76 ms per giro,
  dieci giri al secondo costano lo **0,8% di un core**; anche a sessanta si resta sotto il 5%. Il
  costo quindi non decide `RITMO_PREDEFINITO = 10.0` — lo decide l'altro lato, il ritardo massimo
  fra un fatto e la sua comparsa, che a dieci al secondo è di cento millisecondi e ai quattro
  predefiniti di Rich sarebbe di duecentocinquanta. In una scena in cui i tempi **sono** il
  contenuto, quel quarto di secondo si vede.
- **Perché è stata fatta:** perché la docstring che giustifica il numero era già scritta con dentro
  un costo di «0,86 ms misurati» che nessuno aveva misurato. Il segnaposto era plausibile, e la
  prima misura vera — sulla schermata di allora — lo smentiva del 35%. Poi si è scoperto che anche
  la schermata era sbagliata ([M-029](#m-029)) e la misura è stata rifatta. Vale la pena che
  entrambi i giri restino scritti: la prima correzione ha aggiustato il numero, la seconda ha
  aggiustato la cosa misurata.
- **Riserve:** la mediana è stabile su tre esecuzioni, il massimo no — 9,1, 1,4 e 1,0 ms, cioè il
  rumore del sistema operativo su un portatile, non del codice. È la ragione per cui la cifra
  riportata è la mediana e non la media. La misura scrive su `StringIO`: un terminale vero aggiunge
  il costo di `write` sul tty, che non è stato misurato e che al Task 18 varrà la pena guardare se
  la registrazione risultasse a scatti. La larghezza è quella di sala: una console più larga
  costerebbe di più.
- **Usata da:** [11-tre-rese-e-un-solo-thread-che-disegna.md](11-tre-rese-e-un-solo-thread-che-disegna.md)

---

<a id="m-029"></a>
### M-029 — Un client vede tre server nel replica set e uno soltanto attraverso un `mongos`

- **Data:** 2026-09-03
- **Comando:** chiedere al driver, sui tre stack accesi, quanti server contiene la sua
  `TopologyDescription` — cioè esattamente la lista che finisce nell'intestazione della TUI:
  ```python
  topologia = descrivi_topologia(cliente.topology_description)
  print(f"stack {codice}: tipo={topologia.tipo.value} server={len(topologia.server)}")
  ```
  eseguito prima come lo fanno le prove d'integrazione (`directConnection=True` su 01 e 02, un
  `mongos` su 03) e poi, sullo stack 02, lasciando che il driver **scopra** il set.
- **Output:**
  ```
  stack 01: tipo=singola  server=1     localhost:27017   standalone
  stack 02: tipo=singola  server=1     localhost:27021   primario
  stack 03: tipo=sharded  server=1     localhost:27117   router
  ```
  e, sullo stack 02 con la scoperta attiva, la topologia scoperta contiene tre server —
  `mongo-rs-1:27017`, `mongo-rs-2:27017`, `mongo-rs-3:27017` — che dall'host non sono
  raggiungibili per nome, come già dichiarato in `tests/integration/ambiente.py` e come risolve
  [ADR-0012](../../docs/Decision.md#adr-0012) portando l'applicazione dentro la rete Compose.
- **Che cosa dimostra:** che il caso peggiore per l'intestazione della TUI è **tre**, e non otto.
  La prima stesura di `presentation/righe.py` riservava otto righe con questa giustificazione:
  «due shard da due membri, tre config server, un `mongos`». Sono due errori in una frase. Il
  primo è di conteggio — gli shard dello stack 03 hanno tre membri ciascuno, non due, e i
  container `mongo` dello stack sono undici. Il secondo è più interessante e riguarda il modello:
  **la topologia che il driver espone attraverso un `mongos` non contiene i membri degli shard**.
  Un client di un `mongos` vede il `mongos`. I documenti per shard si contano con
  `$shardedDataDistribution` ([A-012](#a-012)), che produce `ContoShard` — un modello diverso, che
  non passa da `DescrizioneServer` e non finisce in quell'elenco.
- **Perché è stata fatta:** perché `SERVER_MOSTRATI` non è un numero di comodo: entra in
  `ALTEZZA_INTESTAZIONE = 4 + SERVER_MOSTRATI`, e ogni riga riservata all'intestazione è una riga
  tolta alla cronaca in una schermata alta trenta. Otto invece di tre significava cinque righe di
  cronaca perse per sempre, per fare spazio a server che non sarebbero mai comparsi.
- **Riserve:** vale per gli stack di questo repository. Un replica set a cinque membri
  esisterebbe legittimamente altrove, ed è la ragione per cui `server_da_mostrare` non taglia in
  silenzio ma scrive «… e altri N»: il numero è misurato sul lab, la funzione regge anche fuori.
  Sullo stack 03 il `compose.yaml` definisce due `mongos`: un client che li seminasse entrambi ne
  vedrebbe due, e resterebbe sotto il tre. Non è stato verificato che cosa esponga la topologia di
  un client collegato **direttamente** a un config server, perché nessuna scena del talk lo fa.
- **Usata da:** [11-tre-rese-e-un-solo-thread-che-disegna.md](11-tre-rese-e-un-solo-thread-che-disegna.md)

---

<a id="m-030"></a>
### M-030 — L'orologio da parete è dichiarato *aggiustabile*, quello monotono no

- **Data:** 2026-09-03
- **Comando:** chiedere all'interprete che cosa siano davvero i due orologi che `Clock`
  userebbe:

  ```python
  import platform, sys, time
  print(platform.platform())
  print(sys.version.split()[0])
  for nome in ("time", "monotonic", "perf_counter"):
      print(nome, time.get_clock_info(nome))
  ```

- **Output:**

  ```
  macOS-26.6.2-arm64-arm-64bit-Mach-O
  3.13.15
  time       namespace(implementation='clock_gettime(CLOCK_REALTIME)', monotonic=False,
                       adjustable=True,  resolution=1.0000000000000002e-06)
  monotonic  namespace(implementation='mach_absolute_time()',          monotonic=True,
                       adjustable=False, resolution=4.166666666666666e-08)
  perf_counter namespace(implementation='mach_absolute_time()',        monotonic=True,
                       adjustable=False, resolution=4.166666666666666e-08)
  ```

- **Che cosa dimostra:** che l'implementazione ovvia della porta `Clock` — `datetime.now()`
  a ogni chiamata — è sbagliata per l'uso che questa applicazione ne fa. La porta serve a
  due cose: **datare** un evento e **misurare** una durata sottraendo due istanti. La
  prima vuole l'ora vera, la seconda vuole che il tempo non torni indietro. Il flag
  che decide è `monotonic`, e sull'orologio da parete vale **False**: Python dichiara,
  per contratto, che quell'orologio non promette di andare avanti.
- **Perché è stata fatta:** perché `WorkloadRunner._scrivi` sottrae due `now()` e chiama
  il risultato *latenza*, e `TopologyWatcher` sottrae due `now()` e decide se la pazienza
  è finita. Nessuno dei due controlla il segno, e non deve: un percentile calcolato su una
  latenza negativa non fallisce, mente. La misura ha portato a `SystemClock`, che legge il
  muro una volta sola e da lì in poi somma il contatore monotono
  ([ADR-0086](../../docs/Decision.md#adr-0086)).
- **Riserve:** i numeri sono di **questa** macchina — macOS 26.6.2 su arm64, CPython
  3.13.15. L'altro flag, `adjustable=True`, dice la stessa cosa dal verso di chi
  corregge — la documentazione di CPython lo definisce come «l'orologio può essere
  cambiato automaticamente (per esempio da un demone NTP) o manualmente
  dall'amministratore» — ma quella definizione è **letta nella documentazione della
  libreria standard, non in questo registro**, e l'argomento non ci si appoggia: basta
  `monotonic=False`, che è misurato qui sopra.

  Su Linux `time.monotonic()` è `clock_gettime(CLOCK_MONOTONIC)`, che si ferma
  durante la sospensione come `mach_absolute_time()`; la riserva della sospensione, scritta
  in `infrastructure/orologio.py`, resta identica e resta non misurata. Il valore di
  `resolution` non è stato usato per nessuna decisione: le misure di questo progetto sono
  al millisecondo, cioè tre ordini di grandezza sopra la risoluzione peggiore delle tre.

<a id="m-031"></a>
### M-031 — Il client di PyMongo è pigro: la topologia letta per prima dice `sconosciuta` anche su uno standalone sano

- **Data:** 2026-09-03
- **Comando:** eseguire il comando appena scritto contro lo stack 01 acceso — non una
  sonda, il programma:

  ```sh
  make app-stats TARGET=standalone
  ```

  e poi, per isolare il fatto, chiedere sei volte di seguito all'ispettore che cosa vede,
  mezzo secondo l'una dall'altra, senza eseguire nessun comando in mezzo.
- **Output:** la prima esecuzione, con `rapporto()` che leggeva la topologia per prima:

  ```
  standalone (docker/01-standalone)
  topologia   singola
              localhost:27017       sconosciuto              —
  server      mongod 7.0.40 · attivo da 7 h 20 m · connessioni 3
  database    lab · 50000 documenti · dati 5.8 MB · indici 524.0 kB
  ```

  e i sei sguardi consecutivi:

  ```
  0 singola | [('localhost:27017', 'sconosciuto')]
  1 singola | [('localhost:27017', 'standalone')]
  2 singola | [('localhost:27017', 'standalone')]
  ...
  ```

- **Che cosa dimostra:** che `client.topology_description` riferisce ciò che il client
  **crede in questo istante**, e su un client appena costruito quella credenza è
  «non lo so ancora»: il primo battito non è ancora tornato. Non è un difetto del driver,
  è la proprietà che rende visibile l'attimo in cui, durante un'elezione, il client non sa
  — cioè esattamente la scena per cui `watch` esiste. Diventa un difetto solo se la si
  legge per prima e si stampa il risultato come una fotografia.
- **Perché è stata fatta:** perché la fotografia diceva `sconosciuto` di un server sano, e
  la prima riga di `mongolab stats` è ciò con cui la sala decide quanto fidarsi di tutte
  le altre. La correzione è nell'ordine di lettura di `rapporto()`: `server_status()` per
  primo, perché **esegue un comando** e quindi obbliga il driver a una selezione, cioè a
  guardare; `topology()` per ultimo. L'ordine di lettura non è quello di stampa, ed è
  protetto da una prova che conta l'ordine delle chiamate.
- **Riserve:** il rimedio vale perché `rapporto()` esegue comunque un comando. Un comando
  che non ne eseguisse nessuno — una fotografia della sola topologia — resterebbe esposto,
  e la risposta giusta lì non è leggere due volte ma dichiarare `sconosciuta`, che è la
  verità. Il numero di battiti che servono non è stato misurato: si è misurato che al
  secondo sguardo, mezzo secondo dopo, il ruolo c'è.

<a id="m-032"></a>
### M-032 — Il carico contro la collezione seminata: `E11000` su ogni scrittura, e il consuntivo non se ne accorge

- **Data:** 2026-09-03
- **Comando:** la riga del §6.4, accorciata, contro lo stack 01 acceso:

  ```sh
  make app-workload TARGET=standalone \
      ARGS="--sink plain --duration 3 --writers 2 --readers 1 --doc-size 1k"
  ```

- **Output:**

  ```
  47:46.007  ERRORE     BulkWriteError: batch op errors occurred, full error: {'writeErrors': [{'i…
  carico      38 scritture · 0 confermate · 38 fallite · 76 ritentate · 0 documenti
  letture     4833 letture · 4833 riuscite · 0 fallite · 96660 documenti
  ```

  e l'errore per intero, ottenuto rifacendo l'inserimento fuori dal carico:

  ```
  E11000 duplicate key error collection: lab.ordini index: _id_ dup key: { _id: 0 }
  ```

- **Che cosa dimostra:** due cose, e la seconda vale più della prima. La prima è il
  difetto: `DataGenerator` numera i documenti da zero, il seed occupa già gli `_id` da 0 a
  49 999, e la radice di composizione aveva mandato il carico in `lab.ordini`. La seconda
  è che **il programma non si è fermato**: uscita zero, cronaca che scorre, un consuntivo
  con numeri dall'aria plausibile. Le letture riuscivano — 4 833 su 4 833 — e riempivano
  lo schermo mentre le scritture fallivano tutte. Dal fondo della sala quella è una demo
  che funziona.
- **Perché è stata fatta:** perché era il primo comando eseguito per intero dopo averlo
  scritto, e le prove unitarie non potevano trovarlo: sono verdi, e devono esserlo. Il
  fatto vive nel punto in cui un generatore che numera da zero incontra una collezione già
  numerata, cioè in nessuno dei due. Che il carico dovesse scrivere altrove era già
  scritto in due posti — `infrastructure/generatore.py` («le due popolazioni non si
  incontrano mai nella stessa collezione, perché il carico scrive nella propria») e
  `tools/reset-demo.sh` (`const superstiti = ["ordini"]`, tutto il resto cade). A
  sbagliare era il cablaggio, non il disegno ([ADR-0088](../../docs/Decision.md#adr-0088)).
- **Riserve:** la misura è dello stack 01. Sullo stack 03 la collezione del carico **non è
  sharded** — `lab.ordini` lo è, per `{_id: "hashed"}`, ma una collezione nuova no — quindi
  le scritture finirebbero tutte sullo shard primario del database. Non è stato misurato, e
  pesa sul confronto fra architetture del Task 16: è un punto aperto, non una cosa risolta.

<a id="m-033"></a>
### M-033 — PyMongo emette la transizione una volta sola; a raddoppiarla erano due narratori

- **Data:** 2026-09-03
- **Comando:** prima il programma contro lo stack 01 acceso:

  ```sh
  make app-watch TARGET=standalone ARGS="--sink plain --duration 3"
  ```

  poi, per capire di chi fosse il doppione, gli eventi crudi del driver — un `MongoClient`
  con un ascoltatore che stampa e nessun altro in mezzo — e infine il cablaggio esatto di
  `watch`, con l'origine di ogni evento dichiarata.
- **Output:** il programma, con la stessa transizione due volte a mezzo secondo:

  ```
  20:58:05.293  TOPOLOGIA  sconosciuta → singola
  20:58:05.798  SERVER     localhost:27017 sconosciuto → standalone
  20:58:06.303  SERVER     localhost:27017 sconosciuto → standalone
  ```

  PyMongo nudo, per sei sguardi di mezzo secondo:

  ```
  TOPOLOG Unknown -> Unknown
  SERVER  Unknown -> Standalone rtt 0.0012988750022486784
  TOPOLOG Unknown -> Single
  (poi più niente per cinque giri)
  ```

  il cablaggio di `watch`, con l'origine:

  ```
  --- giro 1
  [sentinella] ServerStateChanged ... SCONOSCIUTO -> STANDALONE
  --- giro 2
  [ponte] ServerStateChanged
  ```

- **Che cosa dimostra:** che il driver si comporta correttamente — la transizione la emette
  **una volta sola** — e che il doppione era nostro. `watch` aveva due narratori sullo
  stesso fatto: `SdamBridge`, che traduce i callback del driver, e `TopologyWatcher`, che
  interroga la stessa struttura ogni mezzo secondo. Uno spinto e uno tirato, sulla stessa
  fonte: era garantito che si ripetessero, e il ritardo di un giro fra i due rendeva la
  ripetizione difficile da riconoscere come tale.
- **Perché è stata fatta:** perché il doppione compariva nella scena centrale del talk. Un
  failover raccontato due volte non è rumore: chi guarda conta le transizioni per capire
  che cosa è successo, e leggerne il doppio è leggere un'altra storia. La correzione è nel
  cablaggio, non nei componenti: in `watch` resta il ponte, che è il narratore che il §6.3
  del design nomina, e `TopologyWatcher` torna a fare l'unica cosa che il ponte non sa fare
  — misurare l'interruzione — nello scenario in cui quella misura serve
  ([ADR-0089](../../docs/Decision.md#adr-0089)).
- **Riserve:** resta in cronaca una riga che non è falsa ma non è utile — `TOPOLOGIA
  singola → singola`, che il ponte emette perché la *descrizione* della topologia è
  cambiata (dentro c'è il server che ha cambiato ruolo) benché la forma no. È un punto
  aperto della presentazione, non del cablaggio, ed è dichiarato come tale.

<a id="m-034"></a>
### M-034 — Un parametro rifiutato da Typer esce con 2, e Rich lo incornicia

- **Data:** 2026-09-03
- **Comando:** invocare i comandi con un `--target` che non esiste, sotto `CliRunner`, e
  guardare il codice d'uscita e il testo esatto — prima a ottanta colonne, poi a duecento.
- **Output:** codice d'uscita **2**; il messaggio compare in `result.output`, incorniciato
  da Rich in un riquadro con caratteri `│` e sequenze ANSI di colore, e **mandato a capo
  dove finisce il riquadro**: a ottanta colonne una frase di ottanta caratteri arriva
  spezzata in due righe.
- **Che cosa dimostra:** che un'asserzione `"il bersaglio non esiste" in result.output`
  fallisce per un motivo che non riguarda il codice — la larghezza del terminale di chi
  esegue le prove. Ripulire l'uscita (togliere l'ANSI, togliere il bordo, ricucire gli
  spazi) rende l'asserzione una domanda sul messaggio; verificato che la frase intera si
  ricompone identica sia a `COLUMNS=80` sia a `COLUMNS=200`.
- **Perché è stata fatta:** perché il Passo 4 del Task 11 chiede che un `--target` sbagliato
  «fallisca con un messaggio e un codice d'uscita diverso da zero», e per provarlo bisogna
  sapere quale codice e quale messaggio. Il 2 è poi diventato anche il codice con cui il
  `Makefile` rifiuta un `TARGET` mancante: sbagliare la riga di `make` e sbagliare la riga
  di `mongolab` sono lo stesso errore per chi legge un CI, e meritano lo stesso numero.
- **Riserve:** misurato con typer 0.27.2, che **incorpora** click al proprio interno — in
  questo ambiente `import click` solleva `ModuleNotFoundError`, e nessuna prova può
  appoggiarsi a quel nome. Il riquadro è una scelta di resa di Typer, non un contratto: se
  una versione futura smettesse di incorniciare, la ripulitura resterebbe innocua e le
  prove continuerebbero a valere.

<a id="m-035"></a>
### M-035 — `docker compose run` non ha `--no-build`, e la garanzia che serve sta altrove

- **Data:** 2026-09-03
- **Comando:**
  ```
  docker compose version
  docker compose run --help | grep -iE '^\s+--(build|no-build|pull|quiet)'
  ```
- **Output:** `Docker Compose version v5.5.0`; i soli flag di quella famiglia sono `--build`
  («Build image before starting container»), `--pull` («Pull image before running»),
  `--quiet-build` e `--quiet-pull`. Un `--no-build` non esiste, e passarlo fa uscire
  `unknown flag: --no-build`.
- **Che cosa dimostra:** che la simmetria che uno si aspetta — c'è `--build`, quindi ci sarà
  `--no-build` — non c'è. La scoperta è arrivata nel modo peggiore possibile, cioè eseguendo
  `make app-stats` la prima volta e vedendolo fallire su un flag che avevo scritto per
  prudenza.
- **Perché è stata fatta:** perché il Passo 1 del Task 12 vuole che una modifica al sorgente
  non richieda una ricostruzione, e la lettura sbagliata di quel requisito è «allora vieta di
  costruire». La lettura giusta è che nessuno *debba* costruire, e a questo provvedono il bind
  mount del sorgente e il fatto che l'immagine ci sia già.
- **Riserve:** la garanzia «nessuna costruzione a sorpresa la sera del talk» non è persa, è
  spostata in due posti che la danno meglio di un flag sulla riga di comando: `pull_policy:
  never` scritto nel file ([ADR-0039](../../docs/Decision.md#adr-0039)), che vale per chiunque
  esegua quel servizio e non solo per chi si ricorda il flag, e il controllo di
  `tools/preflight.sh`, che la mattina dice se l'immagine c'è e con quale comando costruirla.
  Misurato su Compose v5.5.0: una versione futura potrebbe aggiungere il flag, e il giorno in
  cui lo facesse resterebbe comunque il flag più debole dei due presidi.

<a id="m-036"></a>
### M-036 — Un seme solo, e per giunta un secondario: il client ne trova tre e parla col primario

- **Data:** 2026-09-03
- **Comando:** dentro la rete Compose dello stack 02, con l'entrypoint sostituito, un client
  costruito su **un** indirizzo — `mongo-rs-2:27017`, che è un secondario — con
  `replicaSet='rs0'`; poi un `hello`, e la lettura di `topology_description`.
  ```
  docker compose --env-file tools/images.env --env-file docker/02-replicaset/.env \
    -f docker/02-replicaset/compose.yaml run --rm --entrypoint python app /sonda.py
  ```
- **Output:**
  ```
  seme passato        : mongo-rs-2:27017
  tipo di topologia   : ReplicaSetWithPrimary
  nome del set        : rs0
  server conosciuti   : 3
    mongo-rs-1:27017    RSPrimary
    mongo-rs-2:27017    RSSecondary
    mongo-rs-3:27017    RSSecondary
  primario scelto     : mongo-rs-1:27017
  host dalla config   : ['mongo-rs-1:27017', 'mongo-rs-2:27017', 'mongo-rs-3:27017']
  ```
- **Che cosa dimostra:** che PyMongo **4.17.0** fa ciò che la specifica SDAM prescrive
  ([A-016](#a-016)): i due indirizzi che il client non aveva li ha saputi dalla risposta di
  `hello`, e ha finito per parlare con un server — `mongo-rs-1` — che nessuno gli aveva mai
  nominato. È la differenza fra *avere tre semi e trovarne tre*, che non prova niente, e
  *averne uno e trovarne tre*, che prova la scoperta.
- **Perché è stata fatta:** perché il Passo 2 del Task 12 chiede di verificare che la scoperta
  funzioni davvero, e la configurazione di produzione passa tre semi — con i quali la
  dimostrazione sarebbe stata circolare. La riserva dichiarata di ADR-0012 chiedeva
  esattamente questo, ed è la ragione per cui il task esiste.
- **Riserve:** la misura vale per un set con il primario disponibile. La stessa specifica
  distingue il caso senza primario, in cui il client aggiunge ma non toglie, e quel caso qui
  non è stato misurato — lo sarà al Task 13, che è dove il failover si mette in scena. La
  prova che rende la misura ripetibile è
  `app/tests/integration/test_container.py::test_un_seme_solo_basta_a_trovare_tutti_e_tre`, e
  usa un programma inline invece del file montato: la sonda di questa misura era un file in
  una cartella temporanea, che non sarebbe sopravvissuto alla sessione.

<a id="m-037"></a>
### M-037 — Un'immagine costruita in locale un digest ce l'ha; quello che non ha è un registro che lo serva

- **Data:** 2026-09-03
- **Comando:**
  ```
  docker image inspect mongolab:0.1.0 --format 'Id={{.Id}} RepoDigests={{.RepoDigests}}'
  docker image inspect mongo:7.0 --format 'Id={{.Id}}'
  docker info --format '{{.Driver}}'
  docker image inspect mongolab@sha256:6a8638…
  ```
- **Output:** per `mongolab:0.1.0`, `Id` e `RepoDigests` portano **lo stesso** sha256
  (`6a8638238ac3…`); per `mongo:7.0`, `Id` è `b6421fd6d1c5…`, cioè esattamente il digest che
  `tools/images.env` pinna. Il driver è `overlayfs` con `driver-type:
  io.containerd.snapshotter.v1`. E `docker image inspect mongolab@sha256:6a8638…` **risolve**,
  restituendo `[mongolab:0.1.0]`.
- **Che cosa dimostra:** che con l'archivio immagini di containerd — quello attivo su questa
  Docker Desktop — l'`Id` di un'immagine *è* il digest del suo manifesto, per le immagini
  scaricate come per quelle costruite in casa. La frase «un'immagine costruita in locale non ha
  un digest», che era scritta nella prima stesura di `problemi_costruzione` in
  `tools/check_stack.py`, è **falsa**, e questa misura l'ha smentita.
- **Perché è stata fatta:** per scrivere onestamente la motivazione di
  [ADR-0093](../../docs/Decision.md#adr-0093), che era stata argomentata su una premessa mai
  verificata. La conclusione della decisione non cambia — un servizio che dichiara `build:` si
  giudica sulle righe `FROM` del suo Dockerfile — ma la ragione sì: non «il digest non esiste»,
  bensì «quel digest nessun registro l'ha mai servito, cambia a ogni ricostruzione, e metterlo
  in `images.env` darebbe a `pull-images.sh --verify` una cosa da cercare in rete che in rete
  non c'è».
- **Riserve:** misurato con l'archivio containerd. Con il vecchio archivio a grafo il
  comportamento è quello che la premessa dava per scontato — `RepoDigests` vuoto finché
  l'immagine non è spinta — e allora la premessa sarebbe stata vera per caso. È un buon
  esempio di quanto valga eseguire: la stessa riga di ragionamento dava la risposta giusta e la
  spiegazione sbagliata, e solo la seconda si sarebbe portata dietro l'errore.

<a id="m-038"></a>
### M-038 — Ventidue colonne bastavano per `localhost`, non per un nome di servizio

- **Data:** 2026-09-03
- **Comando:** `make app-stats TARGET=standalone`, cioè la prima esecuzione dell'applicazione
  da dentro la rete Compose.
- **Output:**
  ```
  topologia   singola
              mongo-standalone:27017standalone          0.7 ms
  ```
- **Che cosa dimostra:** che `_riga_server` impaginava l'indirizzo con `f"{indirizzo:<22}"`, e
  che `mongo-standalone:27017` è lungo **esattamente** ventidue caratteri: la colonna si riempie
  tutta, il riempimento è di zero spazi, e due parole distinte finiscono incollate in una che
  non esiste. Dall'host non era mai successo perché `localhost:27021` ne misura quindici.
- **Perché è stata fatta:** non è stata *fatta*, è **capitata** — ed è il motivo per cui vale la
  pena scriverla. Il Task 12 non parlava di impaginazione; il difetto era in un modulo provato,
  con ventuno prove verdi, e nessuna lo vedeva perché tutte usavano indirizzi corti. È bastato
  cambiare il punto da cui si guarda perché comparisse.
- **Riserve:** la correzione calcola la larghezza sul più lungo degli indirizzi di *quella*
  fotografia, con ventidue come minimo, così che la vista dall'host resti identica a prima. Le
  due prove che la sorvegliano scelgono ruoli le cui parole non compaiono negli indirizzi: il
  primo tentativo cercava `standalone` dentro una riga che conteneva `mongo-standalone:27017`,
  e passava per la ragione sbagliata.

<a id="m-039"></a>
### M-039 — Nell'immagine dell'applicazione `mongodump` non c'è, e una previsione del Task 9 resta da onorare

- **Data:** 2026-09-03
- **Comando:**
  ```
  docker run --rm --entrypoint python mongolab:0.1.0 \
    -c "import shutil; print(shutil.which('mongodump') or 'ASSENTE')"
  ```
- **Output:** `ASSENTE`
- **Che cosa dimostra:** che l'immagine costruita al Task 12 contiene l'interprete, `mongolab` e le
  sue tre dipendenze, e **non** contiene gli strumenti da riga di comando di MongoDB. La docstring
  di `infrastructure/backup.py`, scritta al Task 9, prevedeva che «dall'interno della rete Compose
  al Task 12 [il comando] sarà `("mongodump",)` e basta»: oggi quella riga solleverebbe un
  `FileNotFoundError`.
- **Perché è stata fatta:** perché il registro elencava fra i punti aperti «uccidere il client
  `docker exec` non uccide `mongodump` dentro il container», con «Task 12» come scadenza e la
  motivazione che dal container non ci sarebbe più stato nessun `docker exec` in mezzo. Prima di
  segnare chiuso un punto aperto conviene guardare se lo è, e non lo è.
- **Riserve:** il punto non è urgente e non è un difetto del Task 12, che non doveva installare
  niente: **nessun comando della CLI usa oggi la porta `BackupTool`**, quindi il caso non si
  presenta. Si presenta al Task 14, che è dove `demo backup-live` collega quella porta, e lì la
  scelta è fra installare gli strumenti nell'immagine — con una terza base da pinnare in
  `tools/images.env` e un'immagine più pesante da tenere in cache — e continuare a passare per
  `docker exec` dall'host, rinunciando a eseguire quella scena dal container. La decisione è di
  quel task; qui si registra solo che la previsione non è stata onorata.

<a id="m-040"></a>
### M-040 — I due `--env-file` non sono un vezzo del Makefile: senza, `docker compose` non parte

- **Data:** 2026-09-04
- **Comando:**
  ```
  docker compose -f docker/02-replicaset/compose.yaml ps
  docker compose --env-file tools/images.env -f docker/02-replicaset/compose.yaml ps
  ```
  entrambi dalla radice del repository.
- **Output:** il primo esce con `1` e sette errori `required variable … is missing a value`; il
  secondo esce con `1` e due, tutti e due `required variable PASSWORD_AMMINISTRATORE is missing
  a value`. Con entrambi i file — `tools/images.env` e `docker/02-replicaset/.env` — il comando
  riesce.
- **Che cosa dimostra:** che l'interpolazione dei `compose.yaml` usa la forma
  `${VARIABILE:?messaggio}`, che è un errore e non un valore vuoto, e che le variabili vengono da
  **due** file distinti: i digest delle immagini da `tools/images.env`, che sta in git, e la
  credenziale da `docker/<stack>/.env`, che non ci sta e non ci starà mai. Dimostra anche che
  `-p` non serve: ogni `compose.yaml` dichiara il proprio `name:` al suo interno, e la riga
  annunciata dalla scena è già completa senza.
- **Perché è stata fatta:** perché la prova di integrazione del Task 13 esegue **verbatim** la
  riga che l'applicazione annuncia, e prima di poterla eseguire bisognava sapere che cosa quella
  riga deve contenere per funzionare da sola. La misura ha fissato la forma di `_compose()` in
  `app/tests/integration/ambiente.py` e, per la stessa ragione, quella del frasario di
  `ComandiCompose`.
- **Riserve:** i due errori del secondo comando sono due e non uno perché la variabile compare in
  due servizi; il numero dipende dallo stack e non va letto come una costante. La misura è su
  `02-replicaset`; `03-sharded` ha più servizi e quindi più errori, ma la conclusione — che
  servono entrambi i file — è la stessa.

<a id="m-041"></a>
### M-041 — «Zero scritture perse» è vero, e non è merito dell'applicazione: è il server a imporre `majority`

- **Data:** 2026-09-04
- **Comando:**
  ```
  docker compose --env-file tools/images.env --env-file docker/02-replicaset/.env \
    -f docker/02-replicaset/compose.yaml run --rm -T --entrypoint python app -c \
    "from mongolab.infrastructure.bersagli import BERSAGLI, connetti
     c = connetti(BERSAGLI['rs'])
     print(c.admin.command('getDefaultRWConcern'))
     print(repr(c.write_concern))
     print(c.admin.command('buildInfo')['version'])"
  ```
- **Output:**
  ```
  defaultWriteConcern: {'w': 'majority', 'wtimeout': 0}
  defaultWriteConcernSource: 'implicit'
  WriteConcern()
  7.0.40
  ```
- **Che cosa dimostra:** che il `WriteConcern` del client è **vuoto** — l'applicazione non chiede
  niente — e che il valore effettivo, `w: majority`, arriva dal server come *default implicito*.
  Da MongoDB 5.0 il write concern predefinito è `majority` quando il numero di membri portatori
  di dati lo consente; `defaultWriteConcernSource: 'implicit'` dice esattamente che nessuno
  l'ha impostato a livello di cluster, e che quindi **cambierebbe** se qualcuno eseguisse
  `setDefaultRWConcern`.
- **Perché è stata fatta:** perché il Passo 5 del Task 13 chiede di confrontare i numeri della
  scena con quelli che `feature/02` aveva già misurato, e il numero da spiegare era «0 scritture
  perse». Prima di dire *perché* zero bisognava sapere **chi** chiede `majority`. La risposta
  cambia la frase da dire in sala: non «la mia applicazione usa `w: majority`», che sarebbe
  falso, ma «nessuno qui ha chiesto niente, e il server ha scelto bene».
- **Riserve:** il confronto con [V-016](../../docs/Sources.md#v-016) — cento scritture perse con
  `w: 1` — resta valido proprio perché lì il write concern era **esplicito**: quella misura
  scavalcava il default, questa lo eredita. La misura vale per questo replica set su questa
  versione; su un cluster con un default esplicito diverso la scena mostrerebbe un altro numero,
  ed è una cosa da dire, non un difetto da correggere.

<a id="m-042"></a>
### M-042 — Subito dopo `connetti` la topologia è vuota, e la scena moriva prima di cominciare

- **Data:** 2026-09-04
- **Comando:** la prima esecuzione di `app/tests/integration/test_scenari.py` contro lo stack
  `02-replicaset` acceso e sano.
- **Output:**
  ```
  Usage: mongolab demo failover [OPTIONS]
  Try 'mongolab demo failover --help' for help.
  ╭─ Error ───────────────────────────────────────────────────────────────────╮
  │ Invalid value: nessun primario in vista su «rs»                           │
  ╰───────────────────────────────────────────────────────────────────────────╯
  ```
- **Che cosa dimostra:** che `Inspector.topology()` legge la descrizione che il driver **ha già**
  in mano, e che quella descrizione, nei primi millisecondi dopo `MongoClient(...)`, è ancora
  vuota: la scoperta di PyMongo comincia in quel momento e prosegue su thread suoi. Non è un
  difetto del replica set, che era sanissimo, ed è precisamente ciò che la docstring di
  `topology()` dichiarava da sempre — è una lettura pura, non fa scoperta e non blocca. La
  correzione è un `ping`, che va sul primario ([A-017](#a-017)) e quindi **aspetta**.
- **Perché è stata fatta:** non è stata fatta, è **capitata** alla prima esecuzione vera della
  scena, e vale la pena scriverla per un motivo preciso: le prove unitarie, tutte verdi, non
  la vedevano, perché i doppi rispondono subito. Gli altri comandi non ci inciampavano per caso —
  `stats` chiede `serverStatus`, che è un comando vero e quindi aspetta la selezione; `watch`
  guarda la topologia proprio mentre cambia, che è il suo mestiere. Solo `demo failover` guarda
  una volta sola, subito, e su quella risposta decide chi fermare.
- **Riserve:** la correzione vive in `infrastructure/bersagli.py` e non in `cli.py`, dove sarebbe
  stata più comoda, perché `test_pymongo_si_importa_solo_nell_infrastruttura` lo vieta: la
  guardia ha avuto ragione, e il risultato è migliore — `SenzaPrimario` è un fatto
  dell'infrastruttura, `niente_da_fermare` è la frase che la riga di comando ne ricava. Vedi
  [ADR-0099](../../docs/Decision.md#adr-0099).

<a id="m-043"></a>
### M-043 — La scena del failover contro lo stack vero: 10 019 ms, 0 scritture perse, e i numeri di `feature/02` tengono

- **Data:** 2026-09-04
- **Comando:**
  ```
  uv run --directory app pytest tests/integration/test_scenari.py
  ```
  che gira `mongolab demo failover --target rs --sink plain --carico 3 --elezione 20
  --recupero 5` **dentro** il container, sulla rete di `02-replicaset`, ed esegue sull'host le
  righe `docker compose` che la scena annuncia.
- **Output:**
  ```
  fasi     prima 2057 scritture p95 55.7 ms · durante 9006 p95 51.4 ms · dopo 4166 p95 50.8 ms
  cronaca  primario perduto
           da mongo-rs-1:27017 a mongo-rs-3:27017
  failover interruzione 10019.0 ms · scritture perse 0
  ```
  su **15 229** scritture confermate e 15 229 ritrovate.
- **Che cosa dimostra:** che l'applicazione misura la stessa cosa che `feature/02` aveva misurato
  a mano, e la misura uguale. I 10 019 ms cadono dentro la forbice di
  [V-029](../../docs/Sources.md#v-029) — 9 812, 10 619 e 10 943 ms su tre `docker kill` — e
  quindi dentro gli «8-10 s» di [V-031](../../docs/Sources.md#v-031); le zero scritture perse
  ripetono [V-033](../../docs/Sources.md#v-033), che ne aveva confermate 12 901 e perdute
  nessuna. Il Passo 5 del Task 13 chiedeva di fermarsi se i due non avessero coinciso:
  coincidono, e nessuno dei due va corretto.
- **Perché è stata fatta:** perché una scena che gira non è una scena che dice il vero. Le prove
  unitarie asseriscono sulla **sequenza** degli eventi con i doppi, e una sequenza giusta può
  benissimo accompagnare due numeri sbagliati: se il guasto non arrivasse, l'interruzione
  sarebbe zero e la sequenza resterebbe identica. Confrontare con una misura fatta settimane
  prima, per un'altra strada, è il solo controllo che quei due numeri abbiano un significato.
- **Riserve:** la prova asserisce su una banda larga — fra 5 000 e 15 000 ms — e non sui 10 019,
  perché a stringerla si otterrebbe una prova che fallisce sul portatile di qualcun altro senza
  che niente sia rotto. Ciò che la banda intercetta è l'errore di **categoria**: zero (il guasto
  non è arrivato) o sessanta secondi (l'elezione non è avvenuta). Il numero preciso è questa
  misura, e sta qui. La scena è girata dal container e il guasto è stato eseguito sull'host da
  un processo che faceva da umano: dall'host solo non si può, perché lì la connessione è
  `directConnection` e non c'è scoperta — [ADR-0095](../../docs/Decision.md#adr-0095).

## Fonti canoniche che l'applicazione usa senza copiarle

Queste stanno in [`docs/Sources.md`](../../docs/Sources.md) e sono citate da un ADR. Qui c'è solo
il puntatore e il motivo per cui riguardano `mongolab`.

| Codice | Che cosa afferma, in una riga | Dove pesa su `mongolab` |
|---|---|---|
| [S-010](../../docs/Sources.md#s-010) | i listener di PyMongo esistono, e «Events are delivered synchronously. Application threads block waiting for event handlers … to return» | [04-eventi-del-driver-e-concorrenza.md](04-eventi-del-driver-e-concorrenza.md) |
| [S-018](../../docs/Sources.md#s-018) | `Live` di Rich aggiorna quattro volte al secondo per impostazione predefinita, regolabile con `refresh_per_second` — e **non nomina mai i thread** | [04-eventi-del-driver-e-concorrenza.md](04-eventi-del-driver-e-concorrenza.md) |
| [S-007](../../docs/Sources.md#s-007) | con `directConnection=false` «the client attempts to discover all servers in the replica set» | [01-architettura-esagonale.md](01-architettura-esagonale.md) |
| [S-013](../../docs/Sources.md#s-013) | `testcontainers-python` non conosce i replica set | [05-tipi-prove-e-guardie.md](05-tipi-prove-e-guardie.md) |

<a id="m-044"></a>
### M-044 — Gli strumenti di backup copiati nell'immagine dell'applicazione non partono: manca `libgssapi_krb5.so.2`

- **Data:** 2026-09-04
- **Comando:** un `Dockerfile` a due stadi che prende i due binari dall'immagine `mongo` pinnata
  e li mette in quella `python` pinnata, entrambe da `tools/images.env`:
  ```dockerfile
  FROM ${MONGO_IMAGE} AS strumenti
  FROM ${PYTHON_IMAGE}
  COPY --from=strumenti /usr/bin/mongodump /usr/bin/mongorestore /usr/bin/
  ```
  poi `docker run --rm --entrypoint mongodump <immagine> --version`.
- **Output:** la costruzione **riesce** (exit 0). L'esecuzione esce con **127**:
  ```
  mongodump: error while loading shared libraries: libgssapi_krb5.so.2:
  cannot open shared object file: No such file or directory
  ```
- **Che cosa dimostra:** che i due strumenti non sono binari statici. Sono compilati contro le
  librerie Kerberos del sistema su cui l'immagine `mongo` è costruita, e `python:3.13-slim` —
  che è slim proprio perché non le ha — non le fornisce. La copia riesce e il container si
  costruisce: il guasto arriva alla prima esecuzione, cioè nel momento peggiore.
- **Perché è stata fatta:** perché l'Atto III deve eseguire `mongodump`, e metterlo nell'immagine
  dell'applicazione era la strada che sembrava più corta. Provarla è costato cinque minuti;
  scoprirlo in sala sarebbe costato la scena. Il risultato è [ADR-0100](../../docs/Decision.md#adr-0100):
  gli strumenti restano nei nodi, dove ci sono già e dove funzionano.
- **Riserve:** la via d'uscita esiste ed è `apt-get install mongodb-database-tools`, ma aggiunge
  all'immagine un pacchetto che nessun `FROM` dichiara — e `check_stack.py` verifica proprio che
  ogni base sia pinnata ([ADR-0093](../../docs/Decision.md#adr-0093)) — oltre a richiedere rete
  al `build`, che il laboratorio offline non ha. Non è stata provata perché sarebbe stata scartata
  comunque.

<a id="m-045"></a>
### M-045 — `mongodump --readPreference=secondary --oplog` dentro un nodo, con la password su stdin: riesce in mezzo secondo

- **Data:** 2026-09-04
- **Comando:** la riga che `SubprocessBackup` costruisce ed esegue, mostrata dalla scena stessa:
  ```
  docker compose --env-file tools/images.env --env-file docker/02-replicaset/.env \
    -f docker/02-replicaset/compose.yaml exec -T mongo-rs-1 \
    mongodump --host rs0/mongo-rs-1:27017,mongo-rs-2:27017,mongo-rs-3:27017 \
    --out /tmp/mongolab-backup --username admin --authenticationDatabase admin \
    --readPreference=secondary --oplog
  ```
  La password **non c'è**: viaggia su `stdin`, come [ADR-0054](../../docs/Decision.md#adr-0054)
  prescrive e come [M-025](#m-025) ha reso obbligatorio.
- **Output:** exit 0, venti righe di avanzamento, e come ultima `dumped 72 oplog entries`. Durata
  del processo misurata dal lato Python: **476, 446 e 404 ms** in tre esecuzioni su `lab` con
  circa 54 000 documenti.
- **Che cosa dimostra:** tre cose insieme. Che l'autenticazione su stdin funziona anche
  attraverso `docker compose exec -T` — cioè che il metodo di M-025 regge un livello di
  annidamento in più; che `--oplog` è accettato quando l'indirizzo è una *seed list* con il nome
  del set davanti; e che la riga è **mostrabile**, perché ciò che resta in `argv` non contiene
  segreti. La scena la stampa per intero, ed è la riga che il Blocco 2 sta spiegando.
- **Perché è stata fatta:** perché `demo backup-live` doveva sapere se il comando che avrebbe
  costruito era eseguibile prima che ci fosse una scena attorno.
- **Riserve:** mezzo secondo è la durata su un `lab` di dimostrazione, e non dice niente su un
  database vero — la pagina dei backup cita [S-060](../../docs/Sources.md#s-060), che quella coppia
  di strumenti la raccomanda per «small deployments». Qui il numero serve solo a sapere quanto dura
  la finestra che la scena misura, che è il motivo per cui quella finestra non poteva essere fissa
  ([ADR-0101](../../docs/Decision.md#adr-0101)).

<a id="m-046"></a>
### M-046 — `--readPreference=secondary` sposta davvero le letture: il primario passa da +15 a +0

- **Data:** 2026-09-04
- **Comando:** `serverStatus().opcounters.query` letto sui tre membri — `localhost:27021/2/3` con
  `directConnection` — prima e dopo lo stesso dump, una volta senza `--readPreference` e una volta
  con `--readPreference=secondary`. Un secondo di attesa fra il dump e la seconda lettura, perché
  il conteggio è aggiornato dal nodo e non dal client.
- **Output:**
  ```
  senza --readPreference (446 ms)      con --readPreference=secondary (404 ms)
    mongo-rs-1   39 →  54   (+15)        mongo-rs-1   54 →  54   (+0)
    mongo-rs-2  293 → 294   (+1)         mongo-rs-2  294 → 301   (+7)
    mongo-rs-3  270 → 270   (+0)         mongo-rs-3  270 → 278   (+8)
  ```
- **Che cosa dimostra:** che l'opzione fa quello che dice, e che la promessa dell'Atto III non è
  retorica. Senza, tutte le letture del dump cadono sul primario — che è il nodo che sta anche
  ricevendo il carico. Con, il primario ne prende **zero**: le quindici si spostano sui due
  secondari, distribuite fra i due perché la *seed list* li nomina entrambi e il driver degli
  strumenti sceglie. Questa misura chiude il punto aperto che
  `docs/03-amministrazione/backup-restore.md` si era lasciato in fondo — «è probabilmente la prima
  cosa da fare in produzione, e non è stata misurata».
- **Perché è stata fatta:** perché la scena mette in fila due ritmi e dichiara che il dump non fa
  crollare il throughput. Se le letture del dump colpissero il primario, quella dichiarazione
  dipenderebbe dal caso; sapendo che non lo colpiscono, si sa **perché** non crolla, che è
  un'altra cosa da sapere che non crolla.
- **Riserve:** il `+1` su `mongo-rs-2` nella prima colonna non è del dump — è il traffico di
  fondo del replica set, o la lettura di questa stessa sonda. Il rapporto fra 15 e 0 è così netto
  che un'unità di rumore non cambia la conclusione, ma è la ragione per cui la misura si legge come
  ordine di grandezza e non come conteggio esatto. La distribuzione fra i due secondari (7 e 8) non
  è governata da niente che sia stato dichiarato qui: è la selezione del driver, e su un'altra
  macchina può cadere diversamente.

<a id="m-047"></a>
### M-047 — L'Atto III per intero: il carico non si ferma, e nella copia mancano 106 documenti su 3 908

- **Data:** 2026-09-04
- **Comando:** le due scene di fila, dall'host, sullo stack 02:
  ```
  uv run --directory app mongolab demo backup-live --target rs --sink plain --carico 6
  uv run --directory app mongolab demo restore --target rs --sink plain \
    --from /tmp/mongolab-backup --collection carico-20260904-115619
  ```
  La seconda riga è quella che la prima ha stampato: `demo backup-live` la scrive già completa,
  compreso il nome della collezione di carico.
- **Output:**
  ```
  ritmo       prima 595/s · durante 692/s · calo -16.2%
  dump        /tmp/mongolab-backup · 3908 documenti in collezione
              dumped 72 oplog entries
  carico      3629 scritture · 3629 confermate · p95 66.3 ms
  sotto dump  279 scritture · 279 confermate · p95 68.7 ms

  restore     3908 all'origine · 3802 nella copia · differenza 106
              /tmp/mongolab-backup → lab_ripristinato
              106 scritti mentre il dump era in corso: stanno nell'oplog, che il
              restore non riapplica
  ```
- **Che cosa dimostra:** che le due promesse dell'Atto III reggono, e che sono due promesse
  diverse. La prima è che **il servizio non si ferma**: durante il dump sono passate 279 scritture,
  tutte confermate, con un p95 di 68,7 ms contro i 66,3 di prima. La seconda è che **la copia
  a caldo è incompleta, e di quanto si vede**: dei 3 908 documenti presenti alla fine, nella copia
  ce ne sono 3 802 — mancano i 106 arrivati dopo che `mongodump` era già passato su quella
  collezione. Dei 279 scritti nella finestra del dump, 173 sono entrati nella copia e 106 no: la
  fotografia è stata scattata mentre la scena si muoveva.
- **Perché è stata fatta:** perché il Passo 1 del Task 14 chiede che il throughput «non crolli, e
  va visto, non affermato», e il Passo 2 che la verifica dei conteggi stia a schermo.
- **Riserve:** il `calo -16.2%` è un calo **negativo**, cioè il ritmo è salito. Non è un errore di
  calcolo ed è la ragione per cui il rapporto scrive la percentuale con il segno invece di
  concludere: la finestra del dump è mezzo secondo, e su mezzo secondo il rumore vale più del
  costo del dump. Il numero da guardare non è la percentuale, sono le due conte assolute che le
  stanno accanto — 3 629 scritture prima, 279 durante, zero rifiutate. Questa esecuzione è una
  sola: la percentuale cambia a ogni giro e non va messa su una slide.

<a id="m-048"></a>
### M-048 — Dopo l'Atto II, `mongo-rs-1` si riprende il primato in 4,0 secondi, e finché non l'ha fatto l'Atto III si rifiuta

- **Data:** 2026-09-04
- **Comando:** i due Atti di fila, che è l'ordine in cui vanno in scena:
  ```
  uv run --directory app pytest tests/integration/test_scenari.py
  ```
  Al termine della scena del failover, `hello().isWritablePrimary` interrogato ogni secondo sul
  nodo pubblicato all'host.
- **Output:** **4,0 s**. Senza attendere, `demo backup-live` esce con **codice 2** e il messaggio
  del suo guardiano: «il nodo pubblicato su localhost:27021 non è il primario».
- **Che cosa dimostra:** che il `priority: 2` di `docker/02-replicaset/init/10-rs-initiate.js`
  mantiene la promessa per cui è stato messo — il ruolo torna al primo membro da sé, senza che
  nessuno intervenga — ma non la mantiene istantaneamente. Sono quattro secondi di scaletta fra
  l'Atto II e l'Atto III, e chi presenta li deve avere.
- **Perché è stata fatta:** perché eseguendo i due Atti di fila la prova d'integrazione è
  diventata rossa, **e aveva ragione**: il guardiano ha rifiutato una scena che sarebbe fallita
  alla prima scrittura. Il difetto non era nel codice, era nel momento in cui lo si chiamava. La
  misura serve a dire quanto dura quel momento.
- **Riserve:** quattro secondi sono ciò che si è misurato dopo una scena che comprende già una
  fase di `recupero` di cinque secondi; a freddo, subito dopo il rientro del nodo, il tempo è
  presumibilmente più lungo. La prova concede sessanta secondi e non quattro, perché un'attesa
  tarata sulla misura migliore è un'attesa che fallisce sulla macchina di qualcun altro.

<a id="m-049"></a>
### M-049 — Il balancer del 7.0 in questo lab fonde e non migra: 1 153 giri, 2 fusioni, zero migrazioni

- **Data:** 2026-09-04
- **Comando:** contro `docker/03-sharded` acceso, dal client di `mongolab`:
  ```python
  admin.command("balancerStatus")
  # e, in config.changelog, il conteggio per campo `what`
  ```
- **Output:**
  ```
  balancerStatus: { mode: 'full', inBalancerRound: false, numBalancerRounds: 1153, term: 2 }
  config.changelog per `what`:
    addShard 2 · setClusterParameter.start 1 · setClusterParameter.end 1
    shardCollection.start 33 · shardCollection.end 33
    dropDatabase.start 50 · dropDatabase 50
    merge 2 · dropCollection.start 2 · dropCollection 2
  ```
- **Che cosa dimostra:** che il balancer **è acceso e gira** — mille centocinquantatré giri, e
  `mode: full` — e che in tutta la vita di questo cluster non ha spostato un chunk nemmeno una
  volta: nel registro dei cambiamenti non c'è una sola voce `moveChunk`, `migrate` o
  `moveRange`. Le due voci `merge` sono le stesse che [ADR-0069](../../docs/Decision.md#adr-0069)
  aveva già datate al secondo, ed è l'AutoMerger. Il balancer di una 7.0 fa due mestieri, e qui
  ne esercita esattamente uno.
- **Perché è stata fatta:** perché il Task 15 doveva emettere `ChunkMigrated`, e prima di
  scrivere l'emittente valeva la pena chiedersi se ci fosse mai qualcosa da emettere. Non c'è: un
  evento che descrive un fatto che questo laboratorio non produce sarebbe un campo che sul
  proiettore resta vuoto per sempre, e la scelta è stata toglierlo
  ([ADR-0103](../../docs/Decision.md#adr-0103)) invece di lasciarlo lì a somigliare a un difetto.
- **Riserve:** il conteggio dei giri cresce da sé finché il cluster è acceso, quindi «1 153» è la
  fotografia di questo istante e non un valore da mettere su una slide. Il numero che conta è
  l'altro, ed è zero. Il changelog del config server ha una finestra di ritenzione: se questo
  cluster girasse per settimane, una migrazione vecchia potrebbe esserne uscita — qui non è il
  caso, perché le voci `addShard` del giorno dell'inizializzazione ci sono ancora.

<a id="m-050"></a>
### M-050 — Le tre fonti della distribuzione per shard rispondono a domande diverse, e nessuna da sola basta

- **Data:** 2026-09-04
- **Comando:** su un database usa-e-getta dello stack 03, tre casi in fila.
- **Output:**
  ```
  ### 1. collezione DISTRIBUITA ma VUOTA
    $shardedDataDistribution: {"ns": "…​.vuota", "shards": [
      {"shardName": "shard2rs", "numOrphanedDocs": 0, "numOwnedDocuments": 0, …},
      {"shardName": "shard1rs", "numOrphanedDocs": 0, "numOwnedDocuments": 0, …}]}

  ### 2. collezione NON distribuita, con 50 documenti
    $shardedDataDistribution: []
    config.collections   : None
    config.databases     : {'_id': '…', 'primary': 'shard2rs', 'partitioned': False, …}
    $collStats           : [('shard2rs', 50)]
  ```
- **Che cosa dimostra:** tre cose che insieme decidono la forma di `Distribuzione`.
  **(a)** `$shardedDataDistribution` distingue «distribuita e vuota» da «non distribuita»: nel
  primo caso restituisce una riga con tutti gli shard a zero, nel secondo **nessuna riga**. È
  quindi una risposta sul catalogo e non sui dati, ed è la sola che sappia dirlo.
  **(b)** Per una collezione non distribuita `config.collections` non ha proprio la voce — è
  `None`, non una riga con un campo assente — quindi non è di lì che si ricava lo shard che
  tiene i documenti.
  **(c)** `config.databases` lo dice: `primary: 'shard2rs'`. E `$collStats` conferma che è
  proprio quello lo shard che ha i cinquanta documenti. Le due fonti concordano, e questo
  autorizza `shard_distribution` a fidarsi della prima, che costa una lettura sola.
- **Perché è stata fatta:** perché fino al Task 14 la risposta per la collezione non distribuita
  era una tupla vuota — **la stessa** che dà un replica set — e lo schermo del Blocco 3 negava un
  cluster che era acceso. Distinguere i tre casi richiede di sapere quale fonte risponde a quale
  domanda, e le fonti sono state interrogate invece che dedotte
  ([ADR-0104](../../docs/Decision.md#adr-0104)).
- **Riserve:** `$shardedDataDistribution` esiste dalla 6.0.3, e questo lab è fissato alla 7.0.40
  ([ADR-0058](../../docs/Decision.md#adr-0058)): su un cluster più vecchio il metodo non
  risponderebbe. `numOwnedDocuments` esclude gli orfani, che dopo uno spegnimento sporco possono
  esserci: sono documenti presenti sul disco di uno shard che non li possiede più, e questa misura
  li lascia fuori — è la scelta giusta per la scena, ed è una scelta. `config.databases` chiede il
  permesso di leggere `config`: senza, `primario` resta `None` e la riga a schermo perde il nome
  dello shard senza perdere il resto.

<a id="m-051"></a>
### M-051 — `explain()` dal mongos: lo stadio sta in `winningPlan.stage`, gli shard ci sono solo lì, e il loro ordine non è stabile

- **Data:** 2026-09-04
- **Comando:** lo stesso `find(...).explain()` sui tre stack, letto in `queryPlanner.winningPlan`.
- **Output:**
  ```
  mongos, {_id: 42}      stage='SINGLE_SHARD'  shards=['shard2rs']              chiavi=['shards', 'stage']
  mongos, {indice: 42}   stage='SHARD_MERGE'   shards=['shard2rs', 'shard1rs']  chiavi=['shards', 'stage']
  replica set, {_id: 3}  stage='IDHACK'                                         chiavi=['stage']
  standalone,  {_id: 3}  stage='IDHACK'                                         chiavi=['stage']
  ```
- **Che cosa dimostra:** **(a)** lo stadio si legge sempre in `winningPlan.stage`, su tutti e tre
  gli stack, senza dover scendere in un `queryPlan` annidato. **(b)** La chiave `shards` compare
  **solo** attraverso un router: fuori da un cluster il piano non nomina nessuno shard, e la
  tupla vuota che l'adattatore restituisce lì è un fatto e non un ripiego. **(c)** L'ordine con
  cui il server elenca gli shard **non è quello del nome** — `shard2rs` viene prima di `shard1rs`
  — quindi due schermate a distanza di minuti potrebbero elencarli in ordine diverso senza che sia
  cambiato niente. È per questo che `PymongoStore.explain` li ordina prima di consegnarli.
- **Perché è stata fatta:** perché la porta `QueryPlanner`
  ([ADR-0105](../../docs/Decision.md#adr-0105)) restituisce un `Piano` con tre campi, e ciascuno
  dei tre andava preso da un posto che si sapesse indicare. Dedurre la forma di `explain()` dalla
  documentazione avrebbe prodotto un adattatore che funziona finché il piano è semplice.
- **Riserve:** `IDHACK` compare perché il filtro è su `_id`; con un altro filtro sarebbe
  `COLLSCAN` o `IXSCAN`. Lo stadio si consegna **verbatim** proprio per questo: tradurlo vorrebbe
  dire un dizionario da tenere aggiornato al posto del server. Su un `find` con `sort` o `limit`
  il piano vincente può avere altri stadi sopra, e `winningPlan.stage` allora nomina il più
  esterno — che per la scena del Blocco 3 è ciò che si vuole, ma non è vero in generale.

<a id="m-052"></a>
### M-052 — A durata uguale le due corse del Blocco 3 non fanno lo stesso carico: 4 288 contro 4 415

- **Data:** 2026-09-04
- **Comando:** la prima esecuzione vera della scena, quando il limite era ancora una durata:
  ```
  uv run --directory app mongolab demo sharding --target sharded --carico 6 --sink plain
  ```
- **Output:** l'ultima riga della schermata:
  ```
  carico      4288 senza chiave · 4415 con chiave · non è lo stesso carico
  ```
- **Che cosa dimostra:** che due corse cronometrate uguali, con gli stessi otto scrittori e a
  pochi secondi di distanza, producono conteggi diversi — qui il tre per cento — perché il
  throughput di una collezione distribuita su due shard e quello di una collezione che sta tutta
  su un nodo non sono lo stesso numero. La differenza è piccola, e non è il punto: il punto è che
  **c'è**, e che la scena si chiama «lo stesso carico due volte». Con due conteggi diversi la
  differenza fra le colonne non è più attribuibile alla sola chiave di shard.
- **Perché è stata fatta:** non è stata fatta, è **capitata** alla prima corsa contro lo stack
  vero. Le prove unitarie non la vedevano perché i doppi fanno esattamente il numero di scritture
  che il copione chiede. La conseguenza è che `demo sharding` è l'unica delle quattro scene senza
  `--carico`: il suo limite è `--scritture`, che rende le due corse uguali per costruzione. La
  riga che dichiara i due conteggi resta a schermo comunque — una garanzia che nessuno controlla
  è una speranza.
- **Riserve:** il verso della differenza non è stabile e non va raccontato: in questa esecuzione
  la collezione distribuita ha ricevuto **più** scritture, ma la finestra è di sei secondi e su
  sei secondi il rumore vale quanto l'effetto. Che lo sharding aumenti il throughput di scrittura
  è una tesi diversa da quella del Blocco 3, e questa misura non la sostiene.

<a id="m-053"></a>
### M-053 — A client freddo la topologia è tutta `SCONOSCIUTO`, e la prima fotografia negava un cluster acceso

- **Data:** 2026-09-04
- **Comando:** la prima esecuzione vera della scena, contro lo stack 03 sano e distribuito:
  ```
  uv run --directory app mongolab demo sharding --target sharded --sink null
  ```
- **Output:**
  ```
  non sharded carico-20260904-140017 non è distribuita · 5000 documenti su shard1rs
  sharded     shard1rs          14540 documenti (49%) · 1 chunk
              shard2rs          14875 documenti (51%) · 1 chunk
  bilancio    sbilancio — · chunk —
  ```
  Le righe `arrivati` e i due numeri del bilancio mancavano, perché la fotografia di **prima**
  diceva `distribuita=False, primario=None, conti=()` su una `lab.ordini` distribuita su due shard.
- **Che cosa dimostra:** che `_e_sharded()` leggeva la descrizione della topologia **come il
  client la conosce**, e che un client appena costruito non conosce ancora niente: PyMongo scopre
  i server alla prima operazione. Ogni seme è allora `SCONOSCIUTO`, che nel dominio significa
  esattamente «assenza di un'osservazione» — e concludere «non c'è nessun router» da lì è leggere
  il proprio non aver guardato. La correzione è un `ping` con preferenza `NEAREST`, e solo da
  freddo: appena un ruolo è noto il monitoraggio in background tiene aggiornata la descrizione.
- **Perché è stata fatta:** è **capitata**, ed è la seconda volta — [M-042](#m-042) è lo stesso
  inciampo un Task prima, in `demo failover`. Quella volta la nota diceva che gli altri comandi
  non ci cascavano «per caso»: `stats` chiede `serverStatus`, che aspetta la selezione. Il caso
  ha smesso di reggere alla prima scena che legge la topologia **prima** di fare qualunque altra
  cosa. Nessuna prova d'integrazione la vedeva, perché la fixture di sessione consegna un client
  già caldo: la scoperta avveniva per effetto collaterale di `spazza(client)`. La prova nuova
  apre il proprio client apposta.
- **Riserve:** `NEAREST` e non il primario, per la ragione di [A-017](#a-017): un comando su
  `admin` va sul primario per impostazione predefinita e **non torna finché un primario non c'è**
  — che su un mongos non esiste, e su un replica set in mezzo a un'elezione nemmeno. Con la
  preferenza sbagliata questa riga avrebbe piantato `stats` proprio durante l'Atto II. Il `ping`
  costa un giro di rete su un metodo che altrimenti, su uno stack non sharded, non ne faceva
  nessuno: è il prezzo di una risposta che distingue «ho guardato e non c'è» da «non ho guardato».

<a id="m-054"></a>
### M-054 — L'attesa di una connessione è dentro la latenza misurata, e il thread che soffre è quello meno rappresentato

- **Data:** 2026-09-04
- **Comando:** le otto corse di [V-080](../../docs/Sources.md#v-080) — trentadue scrittori fermi e
  solo `maxPoolSize` che cambia — più la lettura del punto in cui parte l'orologio:
  ```
  CPU_APP=4.0 make app-workload TARGET=standalone \
    ARGS="--writers 32 --readers 0 --doc-size 2k --duration 20 --sink null --max-pool-size 31"
  ```
- **Output:**
  ```
  --max-pool-size 31   p50 7.4 ms · p95 19.9 ms · p99 28.7 ms · max 19973.1 ms
  --max-pool-size 32   p50 7.7 ms · p95 21.1 ms · p99 32.7 ms · max   101.7 ms
  --max-pool-size 33   p50 7.7 ms · p95 21.0 ms · p99 32.2 ms · max   137.4 ms
  ```
- **Che cosa dimostra:** due cose sul modo in cui questa applicazione misura, e valgono per
  chiunque legga i suoi numeri.

  **La prima.** In `_scrivi` l'orologio si guarda **prima** di `insert_many` e non dentro
  (`workload.py:706`), quindi la latenza registrata comprende tutto ciò che pymongo fa per
  quell'operazione — compresa l'attesa di una connessione libera dal pool. Non è un caso
  fortunato: se il campione partisse dopo l'acquisizione della connessione, la fame di pool
  sarebbe **invisibile** in questi numeri, e la riga a 31 connessioni sarebbe indistinguibile da
  quella a 33.

  **La seconda, e non è ovvia.** Con `maxPoolSize` a uno in meno del numero di scrittori, p50, p95
  e p99 sono indistinguibili dal caso sano; solo il massimo dice che un thread ha aspettato venti
  secondi. Il motivo è che **il thread affamato contribuisce pochi campioni proprio perché è
  affamato**: se aspetta non scrive, e se non scrive non compare. I percentili pesano le
  operazioni, non i thread, quindi il thread che soffre di più è quello meno rappresentato nella
  statistica che dovrebbe descriverlo.
- **Perché è stata fatta:** il docstring di `Latenze` argomenta perché il riassunto stampa i
  percentili e non la media — la media è il numero che nasconde. Mancava l'altra metà: perché
  accanto ai tre percentili stia anche il **massimo**, che è la cifra meno rispettabile
  statisticamente di tutte. Questa misura è la risposta: in tutta la tabella di
  [V-080](../../docs/Sources.md#v-080) il massimo è l'unica colonna che distingue una
  configurazione sana da una che affama un thread per l'intera corsa.
- **Riserve:** il massimo di ~20 000 ms coincide con la durata della corsa, quindi è un **limite
  inferiore**: non si sa quanto avrebbe aspettato quel thread se la corsa fosse durata di più.
  L'attesa non produce errori perché `waitQueueTimeoutMS` non è impostato e il predefinito di
  pymongo è «nessun limite»: con un timeout configurato il fenomeno cambierebbe forma — da attesa
  illimitata a eccezioni — e diventerebbe visibile in un posto completamente diverso. Il
  ragionamento sul peso dei campioni è dedotto dalla forma dei numeri, non misurato per thread:
  l'applicazione non tiene un campione separato per scrittore, e per confermarlo servirebbe.

<a id="m-055"></a>
### M-055 — `maxStalenessSeconds` in pymongo: non viaggia mai da sola, e il `repr` del client non è la fonte

- **Data:** 2026-09-04
- **Comando:** costruzione diretta di un client con le opzioni che
  [ADR-0109](../../docs/Decision.md#adr-0109) compone, e interrogazione della preferenza effettiva:
  ```
  cliente = connetti(BERSAGLI["rs"], **opzioni_di_misura(max_staleness_s=90))
  cliente.read_preference.document
  ```
- **Output:**
  ```
  read_preference           Secondary(tag_sets=None, max_staleness=90, hedge=None)
  read_preference.document  {'mode': 'secondary', 'maxStalenessSeconds': 90}
  read_preference.mode      2
  ```
- **Che cosa dimostra:** tre trappole, tutte incontrate scrivendo `opzioni_di_misura` e la prova che
  la copre.

  **Uno.** `maxStalenessSeconds` da sola, con la preferenza predefinita, è un errore in
  **costruzione**: `primary` più una staleness massima è una `ConfigurationError`, perché il
  primario non ha ritardo per definizione e il vincolo non avrebbe significato. Per questo
  `opzioni_di_misura` aggiunge sempre `readPreference` insieme alla staleness, e non offre
  all'utente il modo di separarle.

  **Due.** Il modo `secondary` vale **2** e non 1 — l'enumerazione è
  0 `primary`, 1 `primaryPreferred`, 2 `secondary`, 3 `secondaryPreferred`, 4 `nearest`. La prima
  stesura della prova asseriva `mode == 1` con il commento `# secondary` accanto, e falliva con
  `assert 2 == 1`. La correzione non è stata cambiare l'1 in 2: è stato asserire sulla forma sul
  filo, `read_preference.document`, che si legge senza sapere a memoria un'enumerazione.

  **Tre.** Il `repr` del `MongoClient` mostra `maxstalenessseconds=90000`, che a colpo d'occhio
  sembra un errore di unità di misura di tre ordini di grandezza. Non lo è: quel `repr` sta
  riecheggiando l'argomento grezzo in una forma sua, mentre la preferenza effettiva è
  `Secondary(max_staleness=90)`. **Il `repr` non è la fonte**; `read_preference.document` sì.
- **Perché è stata fatta:** il terzo punto è costato un'indagine, perché un fattore mille in una
  misura di tempo è esattamente il tipo di difetto che invalida una voce `V-`. Vale la pena
  registrarlo: chi rivedrà questo codice vedrà lo stesso `repr` e si porrà la stessa domanda.
- **Riserve:** i tre comportamenti sono di pymongo 4.x come impacchettato in questa applicazione, e
  il `repr` in particolare è la parte meno stabile di una libreria — è testo di comodo, e può
  cambiare in una patch senza che nessuno lo consideri una rottura. La validazione `primary` +
  staleness avviene lato client: non è stato chiesto al server come reagirebbe se la coppia gli
  arrivasse comunque.

<a id="m-056"></a>
### M-056 — Il container dell'applicazione ha una CPU, e satura la misura prima del server

- **Data:** 2026-09-04
- **Comando:** la stessa riga di carico, due volte, con l'unica differenza del limite dato al
  container che esegue l'applicazione:
  ```
  make app-workload TARGET=standalone ARGS="--writers 8 --readers 4 --doc-size 2k --duration 30 --sink null"
  CPU_APP=4.0 MEMORIA_APP=1024m make app-workload TARGET=standalone ARGS="…la stessa riga…"
  ```
- **Output:**
  ```
  cpus 1.0 (predefinito)  49 690–51 361 scritture · p50 2.8 · p95 12.3–13.9 · p99 ≈40.6 · 21 808–23 087 letture
  cpus 4.0                70 013        scritture · p50 2.8 · p95  7.4       · p99  11.0 · 31 065        letture
  ```
  Le stesse due corse contro `rs` e `sharded` danno +3 % e +9 %, cioè rumore.
- **Che cosa dimostra:** che il servizio `app` dei tre file Compose porta `cpus: ${CPU_APP:-1.0}`, e
  che **una CPU non basta** a saturare uno standalone: l'interprete Python arriva al proprio
  tetto prima. Il numero misurato nel lab predefinito era del 40 % più basso del vero, e non
  c'era niente nel riassunto che lo dicesse — nessuna scrittura fallita, nessun ritentativo,
  latenze plausibili.

  La firma che lo tradisce è la coda, non la mediana: il p50 è identico (2,8 ms) e il p99 passa da
  40,6 a 11,0. Una mediana intatta con una coda quattro volte più lunga è **contesa dal lato di
  chi chiede**, non lentezza dal lato di chi risponde.

  Il controllo che rende leggibile il numero è che le altre due architetture **non** si muovano:
  se tutte e tre fossero salite del 40 % il sospetto sarebbe stato la macchina, non il client.
- **Perché è stata fatta:** è stata **provocata** da un'altra misura. Il primo disegno della prova
  su `maxPoolSize` teneva il pool fermo e faceva salire gli scrittori, e la resa **scendeva**
  — 4 118 → 3 372 → 2 632 → 2 446 scritture/s. Una resa che scende quando si aggiungono scrittori
  non è saturazione di pool, è contesa per una risorsa del chiamante; da lì al `cpus: 1.0` nel
  file Compose il passo è stato corto. Il disegno buono tiene fermi gli scrittori e stringe il
  pool ([V-080](../../docs/Sources.md#v-080)), e il limite di CPU è diventato una variabile da
  controllare invece di un rumore di fondo.
- **Riserve:** una corsa per riga nel controllo. `CPU_APP` alza solo il **client**: il `mongod`
  dello stack 01 ha `cpus: 1.0` scritto a mano e non parametrizzato, quindi non si sa a quale
  ritmo saturerebbe davvero, e la riga a quattro CPU è a sua volta un limite inferiore. Il rapporto
  fra CPU del client e resa non è lineare e non è stato mappato: sono state provate una CPU e
  quattro, non le due in mezzo.

<a id="m-057"></a>
### M-057 — L'avvio dell'interprete è dentro il tempo a orologio, e va misurato a parte prima di dividere

- **Data:** 2026-09-04
- **Comando:** il costo fisso, isolato con la corsa più corta che l'applicazione sa fare, e poi
  sottratto dalle corse vere:
  ```
  make app-workload TARGET=standalone ARGS="--writes 1 --writers 1 --readers 0 --sink null"
  ```
- **Output:**
  ```
  avvio (una scrittura, uno scrittore)   0.78 s · 0.68 s · 0.67 s
  5 000 scritture --no-journal           1.79 s · 1.70 s · 1.68 s   → netto ≈ 1.02 s → ≈ 4 900/s
  5 000 scritture --journal              2.19 s · 2.22 s · 2.19 s   → netto ≈ 1.50 s → ≈ 3 330/s
  ```
- **Che cosa dimostra:** che su corse dell'ordine dei due secondi l'avvio dell'interprete pesa il
  **40 %** del tempo a orologio, e che dividere le scritture per la durata senza sottrarlo produce
  un numero sbagliato — e sbagliato **in modo asimmetrico**, perché comprime le differenze: sui
  tempi lordi il giornale costerebbe il 23 %, sui netti ne costa il 32.

  Il costo fisso si isola con `--writes 1 --writers 1`, che è la corsa più corta possibile:
  quel tempo è tutto ciò che l'applicazione fa prima e dopo il lavoro — avviare Python, importare
  pymongo, costruire il cablaggio, aprire il client, chiudere e riassumere.

  È anche la ragione per cui il confronto fra le tre architetture
  ([V-079](../../docs/Sources.md#v-079)) **non** usa il tempo a orologio: usa `--duration` fisso e
  confronta le scritture fatte. Con la durata fissata dall'orologio interno, l'avvio esce dal
  numero da sé.
- **Perché è stata fatta:** perché il primo calcolo del prezzo di `j: true` l'aveva dimenticato, e
  dava −23 %. La cifra pubblicata in [V-075](../../docs/Sources.md#v-075) è −32 %, ed è quella al
  netto.
- **Riserve:** tre corse per misurare il costo fisso, che varia di 0,11 s fra la più veloce e la
  più lenta — su un netto di un secondo è un 10 % di incertezza che si trasferisce interamente al
  ritmo calcolato. I ritmi «≈ 4 900/s» e «≈ 3 330/s» vanno letti con quella tolleranza: il
  rapporto fra i due è più solido delle due cifre. Il costo fisso è misurato con `DOVE=host`; da
  dentro la rete Compose ci sarebbe in più la creazione del container, che è molto più grande e
  altrettanto fissa, e non è stata misurata.


<a id="m-058"></a>

### M-058 — Le 634 prove unitarie passano in 3,9 s con il socket di Docker che non esiste

- **Data:** 2026-09-04
- **Comando:** la suite unitaria eseguita due volte, la seconda con il client Docker puntato su un
  socket inesistente:

```
make app-test
DOCKER_HOST=unix:///percorso/che/non/esiste.sock make app-test
```

- **Output:**

```
634 passed in 3.96s          4,24 real   2,18 user   0,34 sys
634 passed in 3.86s          4,14 real   2,10 user   0,33 sys
```

- **Che cosa dimostra:** che l'affermazione «la suite unitaria non ha bisogno di Docker» è una
  misura e non un proposito. Con `DOCKER_HOST` che punta a un socket che non esiste, qualunque prova
  che provasse a parlare con un demone fallirebbe subito: **nessuna lo fa**, e il conteggio è
  identico. I due tempi sono indistinguibili — 3,96 s contro 3,86 s — il che dice anche che nessuna
  prova sta pagando un tempo di attesa nascosto verso un servizio esterno.

  Il numero interessante non è il 3,9 ma il rapporto con l'altra suite: l'integrazione, che gli
  stack li accende davvero, ci mette **circa 110 secondi**, cioè quasi trenta volte tanto. È quella
  differenza a rendere praticabile eseguire le unitarie dopo ogni modifica, ed è il ritorno concreto
  delle dipendenze che puntano verso l'interno: gli adattatori veri stanno tutti dietro una porta, e
  al loro posto la suite mette un doppio.

  La separazione non è un'abitudine, è configurata: `testpaths = ["tests/unit"]` in
  `app/pyproject.toml` fa sì che un `pytest` nudo — quello che si digita distrattamente — non
  raccolga l'integrazione, che va chiesta per nome con `make app-test-integration`.
- **Riserve:** una coppia di corse su una macchina sola, a stack accesi (che è il caso peggiore per
  questa prova: se una dipendenza da Docker ci fosse, con i container in piedi avrebbe potuto
  passare inosservata proprio nella corsa senza `DOCKER_HOST`). La prova esclude il **demone**
  Docker, non ogni forma di rete: un test che si collegasse a un `mongod` già in ascolto su
  `localhost` non verrebbe intercettato da questa misura. Che non ce ne siano si appoggia alla
  configurazione di `testpaths` e alla revisione dei marcatori `stack01`/`stack02`/`stack03`, non a
  un esperimento. I 110 s dell'integrazione sono un valore osservato più volte durante i Task 8-16,
  non una misura ripetuta apposta qui.

<a id="m-059"></a>

### M-059 — Il tetto che non fermava la scena: 15 s contro 0,05, e `close()` che non si può chiamare

- **Data:** 2026-09-04
- **Comando:** due sonde in sequenza, tutte e due contro un finto `mongodump` che stampa una riga
  di avanzamento su `stderr` e poi dorme dieci minuti. La prima prova a chiudere l'iteratore da un
  thread di guardia mentre il ciclo principale sta leggendo; la seconda esegue `ScenarioBackup`
  intero con `tetto_s = 2,0`:


```unknown
uv run --directory app python sonda_close2.py
uv run --directory app python sonda_tetto_scena.py
```


- **Output:**


```unknown
primo avanzamento: Progress(fase='lab.ordini', completati=0, totali=None, messaggio='writing `lab.ordini` to `dump/lab/ordini.bson`')
GUARDIANO: close() ha alzato ValueError: generator already executing
GUARDIANO: dump ancora vivo tre secondi dopo il tetto: True
GUARDIANO: il thread principale è ancora dentro il ciclo
PRINCIPALE: uscito con ComandoFallito

uscita dopo 2.07 s
DumpTroppoLungo: …/sonda-tetto/finto_dump.py ha superato il tetto di 2 secondi ed è stato fermato
```


- **Che cosa dimostra:** tre cose, e la seconda è quella che ha deciso la forma della correzione.

  **Il difetto era reale e grande.** Prima della correzione, con lo stesso finto dump e
  `tetto_s = 0,05 s`, `ScenarioBackup.esegui()` non era ancora tornata dopo **15 secondi**: trecento
  volte il tetto. Il numero passava al solo `WorkloadRunner`, che smetteva di scrivere; il thread
  principale restava dentro `for avanzamento in self._strumento.dump(...)`, fermo su una lettura
  bloccante. Il carico mollava, la scena no. La differenza fra le due metà non si vede leggendo il
  codice, perché le due chiamate sono a due righe di distanza.

  **Il rimedio che viene in mente per primo non esiste.** Un thread di guardia che allo scadere
  chiuda l'iteratore trova un generatore **in esecuzione**, non sospeso — il consumatore è dentro il
  frame, fermo sul tubo — e `close()` alza `ValueError: generator already executing`. Il dump resta
  vivo (`ancora vivo tre secondi dopo il tetto: True`) e il ciclo resta dov'è. Nella stessa corsa il
  thread principale è uscito **solo** quando il guardiano ha ucciso il processo, e ne è uscito con
  un `ComandoFallito`: la prova che l'unica leva che libera un consumatore bloccato è il figlio, non
  il generatore. È il motivo per cui il tetto sta sulla porta e non nella scena.

  **Col tetto sulla porta la promessa diventa vera.** Stessa sonda, tetto di 2 secondi: la scena
  esce dopo **2,07 s** — 2,05 s in una prima corsa — nominando il tetto invece del segnale. Lo
  scarto di due centesimi è il tempo fra la sveglia del `Timer` e il `wait()` sul figlio abbattuto.
- **Riserve:** il finto dump è un `python` che dorme, non un `mongodump`: dimostra il comportamento
  del **consumatore** davanti a un processo che non finisce, non che `mongodump` si pianti in quel
  modo. Il caso vero da cui nasce il tetto — un `mongodump` che smette di scrivere ma non esce — non
  è stato riprodotto contro MongoDB, e non è chiaro come lo si farebbe senza rompere il server.

  I 15 secondi della prima misura sono un limite osservato, non una durata: la sonda è stata
  interrotta a mano, la scena avrebbe continuato. Il valore utile è il rapporto con il tetto (300×),
  non il numero.

  Il limite dichiarato in `SubprocessBackup` vale anche qui e la sonda non lo tocca: quando il
  comando è `docker exec ...`, il `kill` uccide il **client** `docker` e lo strumento dentro il
  container tira dritto. Il tetto libera la scena, non il cluster.
