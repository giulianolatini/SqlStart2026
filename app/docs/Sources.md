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
vorrebbe farle dire. La riserva non è una formalità. Due delle quattro fonti qui sotto tacciono
proprio sul punto per cui erano state aperte, e la cosa si scopre solo leggendole.

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
