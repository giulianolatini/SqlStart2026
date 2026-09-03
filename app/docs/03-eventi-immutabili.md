# 3. Gli eventi: congelati, slottati, e con l'istante addosso

> Il principio in una riga: **un evento è un fatto, e un fatto non cambia.** Il che, in Python,
> richiede due decoratori e non uno.

## I nove eventi

Sono i fatti che `mongolab` sa raccontare. Stanno in `app/src/mongolab/domain/eventi.py`, tutti
`@dataclass(frozen=True, slots=True)`, tutti figli di una base `Evento` che porta un solo campo.

| Evento | Campi propri | La scena in cui compare |
|---|---|---|
| `WriteSucceeded` | `documenti`, `durata_ms` | il carico che scorre |
| `WriteFailed` | `tipo_errore`, `motivo`, `documenti` | il primario che non c'è più |
| `RetryAttempted` | `tentativo`, `attesa_ms`, `motivo` | il driver che riprova mentre si elegge |
| `LatencySampled` | `operazione`, `durata_ms` | la latenza durante il dump |
| `TopologyChanged` | `precedente`, `successiva` | la forma del cluster che cambia |
| `ServerStateChanged` | `indirizzo`, `precedente`, `successivo` | il singolo membro che cade o risale |
| `BackupProgressed` | `avanzamento` | il dump che procede |
| `ChunkMigrated` | `collezione`, `da_shard`, `a_shard`, `chunk` | il balancer che sposta |
| `PrimaryWaitAbandoned` | `atteso_ms`, `pazienza_ms`, `ultimo_primario` | il client che smette di aspettare |

Otto vengono dal §6.3 del design. Il nono è arrivato dopo, al Task 6, e non per comodità: la
regola del §6.2 «dopo 30 s senza primario, smetti di ritentare» non aveva un evento che sapesse
dirla senza mentire, e aggiungerne uno è costato un ADR ([ADR-0082](../../docs/Decision.md#adr-0082)).
Come ci sia riuscita una guardia a imporlo sta in
[07-topologia-failover-e-i-due-numeri.md](07-topologia-failover-e-i-due-numeri.md).

## Perché immutabili: la coda è una consegna

Un evento nasce dentro un callback di pymongo, che gira sul thread del driver, e viene letto dal
ciclo di disegno, che gira sul thread principale. Fra i due c'è una `queue.Queue`
([ADR-0019](../../docs/Decision.md#adr-0019), spiegato in
[04-eventi-del-driver-e-concorrenza.md](04-eventi-del-driver-e-concorrenza.md)).

Un oggetto congelato trasforma quella coda in un punto di **consegna**: chi riceve non può cambiare
ciò che il mittente ha detto, e chi ha inviato non può cambiarlo sotto gli occhi di chi legge. Con
un oggetto mutabile la coda tornerebbe a essere **condivisione di stato fra thread**, e servirebbe
un lock — proprio nel punto in cui ADR-0019 ha deciso di non metterne uno.

Non è un ragionamento astratto sulla purezza: è la differenza fra una cronaca del failover di cui ci
si può fidare e una in cui un campo potrebbe essere cambiato dopo che qualcuno l'ha letto.

## Che cosa fa `frozen`, e che cosa non fa

La documentazione di Python è onesta fin dalla prima riga: «It is not possible to create truly
immutable Python objects. However, by passing `frozen=True` to the `@dataclass` decorator you can
**emulate** immutability. In that case, dataclasses will add `__setattr__()` and `__delattr__()`
methods to the class. These methods will raise a `FrozenInstanceError` when invoked»
([A-002](Sources.md#a-002)).

«Emulate» è la parola chiave. `frozen` intercetta l'assegnazione normale — quella per cui passa il
codice scritto in buona fede — e non tocca il resto. La prova che lo dimostra è nella stessa pagina,
dove si legge che il costruttore generato «cannot use simple assignment to initialize fields, and
must use `object.__setattr__()`»: se il costruttore può aggirare il congelamento, può farlo
chiunque.

## Che cosa compra `slots`, misurato

Ho misurato le tre vie di scrittura su due sottoclassi congelate della stessa base — una con
`slots=True`, una senza ([M-003](Sources.md#m-003)):

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

**La riga da portare via: `frozen` protegge da una distrazione, `slots` protegge anche da chi
conosce la scorciatoia.** Senza `slots` l'istanza conserva un `__dict__`, e da lì passano sia
`object.__setattr__` sia la scrittura diretta. Con `slots` il `__dict__` non c'è, e con esso
spariscono entrambe le vie.

Per un evento che attraversa una coda fra due thread la differenza non è teorica: la superficie su
cui si può aggiungere un campo per strada esiste solo senza `slots`. Un evento che cresce durante il
viaggio è il modo in cui due thread tornano a condividere stato senza che nessuno l'abbia deciso.

Vale una precisazione: `slots=True` fa una cosa insolita per un decoratore. Restituisce **una classe
nuova** invece dell'originale — «`__slots__` attribute will be generated and new class will be
returned instead of the original one» ([A-002](Sources.md#a-002)) — in contrasto con la regola
generale «The decorator returns the same class that it is called on; no new class is created». Chi
conserva riferimenti alla classe prima della decorazione conserva la classe sbagliata.

## L'istante è un campo, non una chiamata

Nessun evento legge l'orologio dentro di sé. Lo riceve da chi lo costruisce, che a sua volta lo
prende dalla porta `Clock`.

```python
@dataclass(frozen=True, slots=True)
class Evento:
    istante: datetime
```

Due ragioni, entrambe pratiche.

**La prova diventa esatta invece che tollerante.** Con un `FakeClock` che avanza solo quando
qualcuno chiama `sleep`, il valore atteso di ogni istante è noto: l'asserzione confronta due
`datetime` uguali, non due valori vicini entro una soglia. Una prova che tollera è una prova che un
giorno passerà per il motivo sbagliato.

**L'istante è quello in cui il fatto è accaduto, non quello in cui qualcuno se n'è ricordato.**
Sotto carico, fra il momento in cui il driver segnala un heartbeat fallito e il momento in cui il
ciclo di disegno lo elabora, passa esattamente la latenza che la demo esiste per misurare. Se
l'evento leggesse l'orologio quando viene reso a schermo, misurerebbe se stesso.

Il costo è visibile nelle firme: `istante` è il primo parametro di ogni evento, perché i campi della
base precedono quelli di chi eredita — «Because the fields are in insertion order, derived classes
override base classes» ([A-002](Sources.md#a-002)).

## La base esiste per una ragione sola

`Evento` non porta comportamento. Non sa rendersi a schermo, non sa serializzarsi, non sa nulla di
Rich: quello è mestiere di `presentation`, ed è il punto di
[ADR-0007](../../docs/Decision.md#adr-0007).

Esiste per dare a `EventSink.emit` **un tipo solo da accettare**. Senza una base, la porta dovrebbe
dichiarare un'unione di otto tipi, e ogni evento nuovo obbligherebbe a toccare la porta — cioè il
dominio — per un motivo che con il dominio non c'entra.

## Uguaglianza per valore, e hashabilità in omaggio

`eq` è vero per impostazione predefinita: la dataclass genera un `__eq__` che «compares the class by
comparing each field in order» ([A-002](Sources.md#a-002)). Serve alle prove dei Task 5 e 6, che
asseriscono su **sequenze** di eventi: senza uguaglianza per valore ogni asserzione dovrebbe smontare
l'oggetto campo per campo.

Un effetto collaterale utile: «If _eq_ and _frozen_ are both true, by default `@dataclass` will
generate a `__hash__()` method for you». Gli eventi sono quindi hashabili, e si possono mettere in un
insieme o usare come chiave — cosa che un oggetto mutabile non permetterebbe, e giustamente.

## Come si controlla che la regola valga per tutti e otto

Qui c'è la parte che ha insegnato qualcosa.

La prova che sorveglia gli eventi li **scopre** invece di elencarli: percorre il modulo, raccoglie
le sottoclassi di `Evento`, e applica le regole a tutte. Elencarli a mano vorrebbe dire che un nono
evento aggiunto fra sei mesi sfugge a ogni controllo, e ci sfugge in silenzio.

Scritta la prova, l'ho rotta apposta — la disciplina della nota di metodo 142 — aggiungendo un
evento mutabile in più (allora sarebbe stato il nono; oggi il decimo). **E non è fallita: la classe non è arrivata a esistere.**

```
TypeError: cannot inherit non-frozen dataclass from a frozen one
```

([M-002](Sources.md#m-002).) Il congelamento della base si propaga come regola del linguaggio.
Un'asserzione su `frozen` nelle sottoclassi non poteva fallire, e per la stessa ragione non poteva
fallire quella sull'ordine dei campi: sarebbero state controlli sul compilatore travestiti da prove.

Restava viva solo `slots`, che si dimentica in silenzio: un evento in più `frozen=True` senza
`slots=True` nasce senza protestare. Quella variante ha fatto fallire due prove nominando la classe
colpevole.

La guardia è stata quindi riscritta in due:

- una **sulla base**, l'unico punto in cui `frozen`, l'ordine dei campi e `slots` si possono ancora
  perdere — e togliendo `slots=True` a `Evento` fallisce davvero, perché anche le sottoclassi
  slottate ereditano un `__dict__` dalla base;
- una **sulle sottoclassi**, che asserisce soltanto ciò che può ancora andare storto.

È la nota di metodo 144 del [registro operativo](../../docs/registro-operativo-sviluppo.md): rompere
una guardia apposta ha tre esiti, non due, e il terzo — *la violazione non è costruibile* — somiglia
al primo perché finisce anch'esso in verde.

Una nota sulla fonte: **la regola misurata in M-002 non è documentata in
[A-002](Sources.md#a-002).** La sezione «Inheritance» della pagina parla solo dell'ordine dei campi.
Che CPython rifiuti una sottoclasse non congelata di una congelata è vero e riproducibile, ma nel
repository poggia sulla misura e non sulla pagina — ed è scritto così apposta.

---

**Da leggere dopo:** [04-eventi-del-driver-e-concorrenza.md](04-eventi-del-driver-e-concorrenza.md),
che spiega da dove arrivano questi eventi e perché la coda esiste.

**Fonti:** [A-002](Sources.md#a-002), [M-002](Sources.md#m-002), [M-003](Sources.md#m-003).
**Decisioni:** [ADR-0007](../../docs/Decision.md#adr-0007),
[ADR-0019](../../docs/Decision.md#adr-0019).
