# Le decisioni che vincolano `mongolab`

Questa pagina è una mappa, non una fonte. Le decisioni stanno tutte in
[`docs/Decision.md`](../../docs/Decision.md), con il loro contesto, le loro conseguenze e le
alternative scartate: qui c'è soltanto **quali di esse mordono sul codice dell'applicazione, dove si
vedono, e se sono già state applicate**.

Serve a due lettori. A chi legge il codice e trova una scelta che sembra arbitraria, per capire che
non lo è. A chi scriverà i task successivi, per sapere che cosa non può cambiare senza scrivere
prima un ADR nuovo.

**Come si legge la colonna «Stato»:**

- **applicata** — il vincolo è già visibile nel codice, e qualcosa lo verifica;
- **in attesa** — la decisione vale, ma il codice che la attua non è ancora stato scritto;
- **eredita** — il vincolo è stato risolto altrove (negli stack, negli strumenti) e l'applicazione
  ne riceve il risultato senza doverlo riaffermare.

---

## Come è fatta l'applicazione

<a id="adr-0006"></a>
### [ADR-0006](../../docs/Decision.md#adr-0006) — Applicazione in Python con `pymongo`

**Che cosa impone.** Il linguaggio è Python e il driver è PyMongo, con i listener di monitoraggio
registrati **per singolo client** — `MongoClient(event_listeners=[...])` — non globalmente.

**Perché.** `mongosh` mostrerebbe il risultato di un failover, non il suo svolgersi: non dà accesso
agli eventi di topologia. Il motivo non è di capacità del driver ma di ciò che si può proiettare in
sala.

**Dove si vede.** `app/pyproject.toml` dichiara `pymongo>=4.10`; l'ambiente risolve la 4.17.0
([M-001](Sources.md#m-001)). I listener arrivano al Task 7.

**Stato:** applicata per la dipendenza, **in attesa** per i listener.

<a id="adr-0007"></a>
### [ADR-0007](../../docs/Decision.md#adr-0007) — Nucleo disaccoppiato da un `EventSink`

**Che cosa impone.** Il nucleo dell'applicazione **non conosce Rich**. Emette eventi verso
un'interfaccia `EventSink`; l'interfaccia Rich è un adattatore che la implementa. La frequenza di
aggiornamento si dichiara esplicitamente, non si lascia al valore predefinito.

**Perché.** L'output va letto dall'ultima fila di una sala, quindi serve più di righe di log; e va
provato, quindi il nucleo non può dipendere dal disegno. Lo stesso punto di estensione serve a
produrre un sink che scrive testo, utile alle registrazioni di riserva.

**Dove si vede.** La porta `EventSink` in `domain/porte.py`, con una sola firma: `emit(evento) ->
None`. La guardia architetturale di `tests/unit/test_scheletro.py` verifica che `domain/` e
`application/` non importino nulla di terze parti — quindi neanche Rich. Il vincolo su
`refresh_per_second` arriva al Task 10.

**Stato:** **applicata** per il disaccoppiamento, **in attesa** per la frequenza.

<a id="adr-0019"></a>
### [ADR-0019](../../docs/Decision.md#adr-0019) — I listener depositano in coda e ritornano subito

**Che cosa impone.** Il listener costruisce un evento **immutabile**, lo deposita in una
`queue.Queue` e ritorna. Il ciclo di disegno gira sul thread principale, svuota la coda a ogni giro
e aggiorna `Live`. **Un solo thread tocca Rich.**

**Perché.** Due lacune con una soluzione sola. PyMongo consegna gli eventi in modo sincrono e blocca
il thread chiamante: un listener che disegna rallenta il driver e falsa le misure che la demo esiste
per mostrare. La documentazione di Rich non nomina mai i thread: non c'è risposta documentata sulla
sicurezza di `Live`, in nessuna delle due direzioni. Un solo thread rende la domanda inutile.

**Dove si vede.** Tutti gli eventi sono `@dataclass(frozen=True, slots=True)` in
`domain/eventi.py`, e la ragione è scritta nella docstring del modulo. La docstring di
`EventSink.emit` dice che il metodo non deve bloccare. Le prove
`test_un_evento_non_si_puo_modificare` e `test_ogni_evento_ha_i_propri_slot` lo verificano. La coda
è arrivata al Task 7 con `SdamBridge`, il ciclo al Task 10 con `Scena` e `RichTui`.

**È il vincolo più facile da dimenticare del progetto**, perché non si vede finché non fa danno: il
codice funziona lo stesso, e a sbagliare sono soltanto i numeri.

**E infatti è stato dimenticato, dal codice che credeva di applicarlo.** Il Task 10 ha scoperto che
`Live`, con le impostazioni predefinite, avvia un `_RefreshThread` demone che chiama `refresh()`
per conto suo ([M-027](Sources.md#m-027)): i thread che toccavano Rich sarebbero stati due. La
lacuna della documentazione che aveva motivato questo ADR nascondeva, oltre alla risposta, anche il
fatto che la domanda avesse già una risposta sbagliata. Si applica con `auto_refresh=False`, e da
lì [ADR-0085](../../docs/Decision.md#adr-0085), che ne è il seguito: la decisione resta, il
presupposto è corretto, e una prova conta i thread invece di fidarsi.

**Stato:** **applicata** — immutabilità dal Task 2, coda dal Task 7, ciclo e thread unico dal
Task 10.

<a id="adr-0085"></a>
### [ADR-0085](../../docs/Decision.md#adr-0085) — `auto_refresh=False`, e il ritmo nel ciclo

**Che cosa impone.** `RichTui` costruisce `Live` con `auto_refresh=False` e chiama `refresh()` dal
proprio ciclo. `refresh_per_second` **non** si passa a `Live`, perché in quella configurazione è
inerte; il numero vive nel periodo del ciclo, `RITMO_PREDEFINITO = 10.0`.

**Perché.** Perché è la sola riga che rende vero [ADR-0019](#adr-0019) invece che sperato. Con le
impostazioni predefinite `Live.start()` avvia un `_RefreshThread` demone: i thread che toccano Rich
sarebbero due, e la correttezza dipenderebbe da un `RLock` privato che nessuno ha promesso
([M-027](Sources.md#m-027), [A-015](Sources.md#a-015)).

**Dove si vede.** `presentation/rich_tui.py`, il `with Live(...)` dentro `acceso()`. La guardia è
`test_mentre_la_tui_e_accesa_non_nasce_nessun_altro_thread`, che conta i thread vivi mentre il
display è acceso — conta invece di nominare la classe privata, così che a fallire sia un
cambiamento di comportamento e non un cambiamento di nome.

**Vale anche per chi verrà dopo.** Un `Live` costruito altrove nel progetto, un giorno, senza
`auto_refresh=False`, non farebbe fallire nessuna prova esistente: la guardia è su `RichTui`. È il
motivo per cui questa pagina lo scrive.

**Stato:** **applicata** dal Task 10.

<a id="adr-0012"></a>
### [ADR-0012](../../docs/Decision.md#adr-0012) — Applicazione containerizzata sulla rete degli stack

**Che cosa impone.** L'applicazione gira in un container collegato alla rete Compose dello stack e
si connette **con i nomi dei servizi**. `directConnection=true` si usa **solo** nella demo dello
standalone, dove non c'è nulla da scoprire.

**Perché.** Con `directConnection=false`, che è il valore predefinito, «the client attempts to
discover all servers in the replica set» ([S-007](../../docs/Sources.md#s-007)). Quella scoperta è
ciò che il talk vuole mostrare, ed è la prima cosa che si rompe se l'applicazione gira sull'host e
il cluster dentro Docker.

**Dove si vede.** In [`app/Dockerfile`](../Dockerfile), nel servizio `app` di ciascuno dei tre
`compose.yaml` ([ADR-0091](../../docs/Decision.md#adr-0091)) e nella mappa dei bersagli, che dal
Task 12 tiene **due** indirizzi per stack e lascia scegliere all'ambiente
([ADR-0090](../../docs/Decision.md#adr-0090)). `directConnection=true` resta al solo stack 01, dove
non c'è nulla da scoprire.

**Riserva ereditata, e chiusa.** L'ADR dichiarava un limite della propria fonte: la pagina dice che
il driver «attempts to discover all servers», ma non dice che usi i nomi host memorizzati nella
configurazione del replica set. La frase esiste, in un'altra fonte — la specifica SDAM, che è
normativa e vale per tutti i driver ([A-016](Sources.md#a-016)) — ed è stata anche misurata: un
seme solo, tre membri trovati, e una scrittura su un server mai nominato al client
([M-036](Sources.md#m-036)). Resta fuori il caso senza primario, che si vede al Task 13.

**Stato:** **applicata** dal Task 12.

---

## Come si verifica

<a id="adr-0020"></a>
### [ADR-0020](../../docs/Decision.md#adr-0020) — Niente `testcontainers`

**Che cosa impone.** Nessuna dipendenza da `testcontainers`. Le prove di integrazione avviano gli
stack Compose **del repository** e ci girano contro. Restano separate dalle unitarie, con un
bersaglio `make` distinto.

**Perché.** `MongoDbContainer` avvia uno standalone e non conosce i replica set
([S-013](../../docs/Sources.md#s-013)); `DockerCompose` della stessa libreria esiste nel codice ma
non nella documentazione pubblicata. Soprattutto: le prove così verificano **l'artefatto che il
pubblico eseguirà davvero**, non un facsimile.

**Dove si vede.** `app/pyproject.toml` non ha `testcontainers` fra le dipendenze di sviluppo.
`testpaths = ["tests/unit"]` tiene l'integrazione fuori dalla suite veloce; `make
app-test-integration` la chiede per nome.

**Nota storica.** Questa decisione **sostituisce ADR-0011**, che prescriveva l'opposto. Il documento
di design non è stato riscritto e su questo punto è superato: il suo «rischio 1» è chiuso da qui.

**Stato:** **applicata**.

<a id="adr-0038"></a>
### [ADR-0038](../../docs/Decision.md#adr-0038) — Le decisioni che una macchina può controllare le controlla una macchina

**Che cosa impone.** Quando una regola è verificabile automaticamente, si scrive il controllo invece
di scrivere la raccomandazione.

**Perché.** Una convenzione non applicata è una convenzione che il primo pomeriggio di fretta
cancella, e nessuno se ne accorge finché non serve.

**Dove si vede.** È la decisione più densamente presente in `app/`. La guardia architetturale sugli
import di terze parti; `mypy --strict` su `src` **e** `tests`; il controllo riflessivo che scopre le
sottoclassi di `Evento` invece di elencarle; il controllo che verifica di non aver esaminato il
vuoto. E, fuori da `app/`, `check_citations.py` e `check_links.py`, che da questa feature guardano
anche queste pagine.

**Stato:** **applicata**.

<a id="adr-0053"></a>
### [ADR-0053](../../docs/Decision.md#adr-0053) — Uno strumento che sbaglia lo dice con il codice della shell

**Che cosa impone.** Un errore si comunica con il codice d'uscita, non solo con un messaggio; e il
messaggio non sostituisce il codice.

**Dove si vede.** Il bersaglio `app-test-integration` intercetta il codice **5** di pytest — «No
tests collected» ([A-004](Sources.md#a-004), misurato in [M-005](Sources.md#m-005)) — e lo traduce
in una frase, invece di sopprimerlo con `|| true` o di lasciarlo passare come fallimento. Le altre
uscite passano intatte.

**Stato:** **applicata**.

---

## Che cosa il repository esige comunque

<a id="adr-0009"></a>
### [ADR-0009](../../docs/Decision.md#adr-0009) — Funzionamento completamente offline obbligatorio

**Che cosa impone.** Il lab deve funzionare senza rete. Niente si scarica al momento della demo.

**Conseguenze per `app/`.** Le dipendenze sono bloccate in `app/uv.lock`, che è **versionato**. Non
c'è integrazione continua: i controlli sono comandi `make` che chiunque esegue in locale. Dal Task 12
l'immagine dell'applicazione entra nell'elenco delle cose da avere prima del talk, e ci entra in due
modi diversi: le sue **basi** sono pinnate per digest in `tools/images.env` come tutte le altre,
perché sono l'unica parte della costruzione che venga dalla rete; l'immagine **costruita** no,
perché il suo digest nessun registro l'ha mai servito e cambia a ogni ricostruzione, e quindi
`tools/preflight.sh` ne verifica la presenza invece del digest
([ADR-0093](../../docs/Decision.md#adr-0093), [M-037](Sources.md#m-037)).

**Stato:** **applicata**, per le dipendenze e per l'immagine.

<a id="adr-0050"></a>
### [ADR-0050](../../docs/Decision.md#adr-0050) — Le registrazioni di riserva si producono con quello che c'è, e il formato è testo

**Conseguenze per `app/`.** L'interfaccia Rich non è l'unica resa possibile: serve un sink che
produca testo. È la seconda implementazione di `EventSink`, e la ragione per cui quella porta ha un
solo metodo. La coda di ADR-0019 è il punto naturale in cui intercettare gli eventi per registrarli.

**Stato:** **in attesa** (Task 18).

<a id="adr-0017"></a>
### [ADR-0017](../../docs/Decision.md#adr-0017) — Il repository resta esaustivo, i tagli valgono solo dal vivo

**Conseguenze per `app/`.** Queste pagine esistono per questo. Ciò che dal palco non entra in
sessanta minuti resta scritto, e chi ha assistito al talk trova qui proprio le parti saltate.

**Stato:** **applicata**.

---

## Vincoli di sicurezza che `app/` non può violare

Non riguardano il codice dell'applicazione oggi, ma lo riguarderanno appena toccherà uno stack
autenticato. Vale la pena conoscerli prima.

<a id="adr-0014"></a>
### [ADR-0014](../../docs/Decision.md#adr-0014) — Keyfile generato in un volume nominato, non in bind mount

Il keyfile **non entra nel repository**, in nessuna forma. Nessuna prova, nessuno script e nessuna
pagina lo riproduce.

**Stato:** **eredita** — risolto negli stack.

<a id="adr-0054"></a>
### [ADR-0054](../../docs/Decision.md#adr-0054) — La password del lab sta sulla riga di comando dell'host, e il commento lo dice

La password **non si passa con `-e` al client `docker`**: gli script la leggono da `.env` e la
passano con `--password` a `mongosh` dentro `docker exec`. I file `.env` degli stack sono
gitignorati e non vanno mai committati, e il valore va oscurato ovunque finisse in `docs/`, in chat
o in una registrazione.

**Conseguenze per `app/`.** Quando le prove di integrazione toccheranno lo stack 02 o 03, la
credenziale dovrà seguire la stessa disciplina. Il modo esatto è ancora da decidere, ed è **un debito
esplicito del Task 8**, non una svista.

**Stato:** **in attesa** — e da progettare, non da copiare.

---

## Decisioni che il codice di `app/` **non** eredita

Vale la pena dire anche che cosa non vincola, per non cercare corrispondenze che non ci sono.

| Decisione | Perché non riguarda `app/` |
|---|---|
| [ADR-0001](../../docs/Decision.md#adr-0001), [ADR-0003](../../docs/Decision.md#adr-0003) | riguardano la forma degli stack Compose, non il codice che ci si collega |
| [ADR-0004](../../docs/Decision.md#adr-0004), [ADR-0025](../../docs/Decision.md#adr-0025) | limiti di memoria e CPU dei container MongoDB |
| [ADR-0008](../../docs/Decision.md#adr-0008), [ADR-0028](../../docs/Decision.md#adr-0028) | la versione di MongoDB e il suo pinning per digest: `app/` parla con quello che trova |
| [ADR-0037](../../docs/Decision.md#adr-0037) | le pagine di installazione sul sistema operativo |

---

**Fonti citate in questa pagina:** [S-007](../../docs/Sources.md#s-007),
[S-013](../../docs/Sources.md#s-013), [A-004](Sources.md#a-004), [M-001](Sources.md#m-001),
[M-005](Sources.md#m-005).
