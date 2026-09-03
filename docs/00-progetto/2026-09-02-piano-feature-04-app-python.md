# Piano di implementazione — `feature/04-app-python`

> **Per chi esegue il piano:** i passi usano caselle `- [ ]` da spuntare. Ogni task termina con un
> deliverable verificabile e un commit. Questo piano attua decisioni già prese altrove e non le
> rimette in discussione; dove se ne prende una nuova, il task lo dichiara.

---

**Obiettivo:** produrre `mongolab`, l'applicazione Python che rende visibile dal palco ciò che vede
un client — e che nessun `mongosh` può mostrare: la scoperta della topologia, la cronaca di un
failover al millisecondo, e i due numeri che giustificano l'esistenza dell'applicazione, **durata
dell'interruzione** e **scritture perse**. Con l'applicazione si saldano anche i debiti di misura
che quattro pagine hanno intestato per iscritto a questo branch, e si scrivono le tre pagine che
`docs/README.md` promette qui.

**Architettura:** questo branch parte da un disegno già deciso e da **zero righe di codice**. È
l'opposto di `feature/03`, che aveva lo spike a fare da mappa: qui la mappa è il §6 del design, e
quattro ADR ne fissano i punti che non si rinegoziano — [ADR-0006](../Decision.md#adr-0006)
(pymongo, con i listener di monitoraggio registrati per client),
[ADR-0007](../Decision.md#adr-0007) (il nucleo non conosce Rich, emette verso un `EventSink`),
[ADR-0019](../Decision.md#adr-0019) (il listener deposita in coda e ritorna subito) e
[ADR-0012](../Decision.md#adr-0012) (l'applicazione gira in container sulla rete degli stack).

Le dipendenze puntano solo verso l'interno: `domain/` e `application/` non importano alcuna libreria
di terze parti, ed è la ragione per cui la suite unitaria gira in millisecondi senza Docker. Gli
adattatori veri stanno in `infrastructure/`, e la loro prova è di integrazione contro **gli stack di
questo repository** — non contro un facsimile, perché [ADR-0020](../Decision.md#adr-0020) ha già
scartato `testcontainers` misurando.

**Il rischio numero uno del design è già chiuso, e va detto qui perché il design non lo sa.** Il §7
elenca come rischio 1 il supporto di `testcontainers-python` ai replica set, e scrive «la verifica è
il primo passo di `feature/04`; l'esito è un ADR in ogni caso». Quell'ADR esiste dal **25 agosto**:
è [ADR-0020](../Decision.md#adr-0020), che supera [ADR-0011](../Decision.md#adr-0011). Il primo
passo di questo branch **non** è quella verifica. Per la stessa ragione è superata la riga del §7
che vuole le fixture con «un Compose minimale proprio, non quello di `docker/`»: ADR-0020 dice il
contrario, ed è del giorno dopo.

**Stack tecnico:** Python **3.13** (`python:3.13-slim` nel container; l'host ha la 3.14.7, che il
design dichiara troppo recente per garantire il supporto di tutte le dipendenze di test), `uv` per
le dipendenze, `pymongo`, `Typer` per la CLI, `Rich` per la TUI, `pytest`, `mypy --strict`. Fuori
dall'applicazione: Compose Specification, MongoDB 7.0.40 pinnata per digest, GNU Make, Markdown.

**Specifica:** [`2026-08-24-design.md`](2026-08-24-design.md) §4 (posto di `app/` nell'albero), §6
per intero (stratificazione, porte, modello a eventi, CLI, runtime), §7 (strategia di test, **letto
insieme ad ADR-0020**), §9.1 (che cosa l'applicazione deve fare in sala, Blocco 2 e Blocco 3).

**Finestra:** dal 2 all'11 settembre 2026, per [ADR-0078](../Decision.md#adr-0078). La scadenza
dell'11 non si muove: i due giorni guadagnati chiudendo `feature/03` in anticipo sono margine, non
ambizione.

---

## Vincoli globali

Valgono per ogni task e non si ripetono dentro i task.

- **Le dipendenze puntano verso l'interno.** `domain/` e `application/` non importano nulla di terze
  parti — né `pymongo`, né `rich`, né `typer`. Una violazione è un difetto anche se i test passano,
  ed è ciò che rende la suite unitaria istantanea.
- **`mypy --strict` è verde a ogni commit.** Le porte sono `typing.Protocol`: la conformità di un
  doppio è strutturale, e la verifica è statica.
- **Doppi, non mock.** `InMemoryStore` conserva davvero i documenti. Un mock che verifica «è stato
  chiamato `insert_many`» prova l'implementazione e si rompe al primo refactor, cioè nella fase in
  cui il TDD dovrebbe proteggere.
- **Il listener deposita e ritorna** ([ADR-0019](../Decision.md#adr-0019)). Nessuna I/O, nessun
  disegno, nessun lock dentro un callback di pymongo: gli eventi sono consegnati in modo sincrono e
  bloccano il thread del driver, quindi un listener lento **falsa proprio la misura che la demo
  esiste per mostrare**.
- **Un solo thread tocca `Live`.** Il ciclo di disegno gira sul thread principale e drena la coda.
  La documentazione di Rich non dice nulla sulla sicurezza di `Live` rispetto ai thread, in nessuna
  delle due direzioni: il progetto non si mette nella condizione di doverlo sapere.
- **`refresh_per_second` è dichiarato esplicitamente**, non lasciato al valore predefinito
  ([ADR-0007](../Decision.md#adr-0007)).
- **L'applicazione si collega per nome di servizio, dalla rete dello stack**
  ([ADR-0012](../Decision.md#adr-0012)). `directConnection=true` **solo** nella demo dello
  standalone, dove non c'è nulla da scoprire.
- **Niente `testcontainers`** ([ADR-0020](../Decision.md#adr-0020)). I test di integrazione avviano
  gli stack del repository con i `make up-0X` che già esistono. Restano separati dagli unitari, con
  un target `make` distinto, perché la suite veloce resti veloce.
- **Niente CI** ([ADR-0038](../Decision.md#adr-0038)): i controlli si eseguono in locale con `make`.
- **La password non entra mai nel repository**, e non si passa con `-e` al client `docker`
  ([ADR-0054](../Decision.md#adr-0054)): si legge dal `.env` e si passa al comando dentro il
  container. Vale identico per l'URI di connessione dell'applicazione.
- **Ogni affermazione tecnica in `docs/` cita almeno una voce di `Sources.md`.** Una fonte che
  nessun ADR cita è orfana e fa fallire `make docs-check`.
- **Le intestazioni nuove `V-` e `ADR-` vogliono l'ancora esplicita** (`<a id="v-0NN"></a>`,
  `<a id="adr-0NNN"></a>`) sulla riga sopra, altrimenti `make docs-check` fallisce.
- **Il design non si riscrive e gli ADR non si correggono:** si supera per aggiunta e per rimando.
  Il registro è cronologico; le deviazioni dal piano si dichiarano lì, non modificando il piano.
- **Numeri liberi all'apertura:** ADR-**0080**, V-**074**, S-**076**, nota di metodo **140**. La
  suite del repository è a **143** prove.
- **Lingua:** prosa e commit in italiano, stile convenzionale con il corpo che spiega il perché,
  chiusi da `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

## Task 1 — L'appuntamento di ADR-0058: la 8.0.30 esiste?

**File:** `docs/Sources.md`; eventualmente `tools/images.env`, `docker/*/.env.example`,
`docs/Decision.md`.

[ADR-0058](../Decision.md#adr-0058) ha trasformato la clausola condizionale di
[ADR-0028](../Decision.md#adr-0028) in **due date fisse**. La prima diceva «il 3 settembre, alla
chiusura di `feature/03`»; le due coordinate si sono separate, e
[ADR-0078](../Decision.md#adr-0078) ha stabilito che vale l'evento. L'appuntamento cade quindi qui,
e va onorato **prima** di scrivere codice: montare l'applicazione su una versione e ripinnarla il
giorno dopo significa rigirare le registrazioni.

- [x] **Passo 1.** Eseguire i due `curl` scritti in [V-051](../Sources.md#v-051): il filtro per
      **nome esatto** su Docker Hub e il feed ufficiale dei download. Non leggere un elenco paginato
      cercando un elemento — è la trappola della nota di metodo 91: si chiede per nome e si guarda
      il **conteggio**, perché uno `0` non dipende da dove cade il taglio della pagina.
- [x] **Passo 2.** Registrare l'esito come **V-074** in ogni caso, con l'ancora
      `<a id="v-074"></a>`. Un controllo che non lascia traccia è un controllo che il 16 settembre
      qualcuno rifarà da capo senza sapere che era già stato fatto.
- [x] **Passo 3.** Se la 8.0.30 **non** c'è: si resta su 7.0.40 e non serve altro ADR — ADR-0058
      prevede questo esito, e la sua seconda data resta in piedi. Se **c'è**: fermarsi e chiedere al
      Product Owner. Ripinnare a sedici giorni dal talk tocca le cinque registrazioni della `03` e
      le tre della `02`, e non è una decisione da task.
- [x] **Passo 4.** `make docs-check`, poi commit: `docs: l'appuntamento di ADR-0058, onorato`.

---

## Task 2 — Lo scheletro di `app/`, e la prima prova che gira

**File:** creare `app/pyproject.toml`, `app/src/mongolab/__init__.py`,
`app/src/mongolab/py.typed`, i cinque pacchetti del §6.1, `app/tests/conftest.py`,
`app/tests/unit/test_scheletro.py`; modificare `Makefile`, `.gitignore`.

Il posto di `app/` nell'albero lo fissa il §4 e non si discute qui. Questo task produce un progetto
che **non fa niente** e lo fa in modo verificabile: è ciò che rende falsificabile tutto il resto.

- [x] **Passo 1.** `app/pyproject.toml` sul modello di `tools/pyproject.toml`, che è già nel
      repository e detta lo stile: `requires-python = ">=3.13"`, dipendenze dichiarate,
      `[dependency-groups] dev` per `pytest` e `mypy`. Il layout è `src/`, quindi **non** serve il
      `pythonpath = ["."]` che `tools/` ha dovuto mettere: annotarlo nel commento, perché la
      differenza è voluta e chi copia il file si chiederà perché.
- [x] **Passo 2.** I cinque pacchetti del §6.1 — `domain/`, `application/`, `infrastructure/`,
      `presentation/`, e `cli.py` in radice — ciascuno con il suo `__init__.py`. Il file `py.typed`
      accanto, altrimenti `mypy` non guarda dentro il pacchetto quando lo importa qualcun altro.
- [x] **Passo 3.** `strict = true` per `mypy`, nella sezione di `pyproject.toml`.
- [x] **Passo 4.** Tre target nel `Makefile`, con la forma degli esistenti e la riga `##` per
      `make help`: `app-test` (suite unitaria), `app-check` (`mypy --strict`),
      `app-test-integration` (che per ora non ha nulla da eseguire, e lo dice). Il `Makefile` è il
      punto d'ingresso unico: un comando che non c'è lì, per questo repository, non esiste.
- [x] **Passo 5.** La prima prova unitaria, che è anche la guardia architetturale: percorrere i
      sorgenti di `domain/` e `application/` e fallire se compare un `import` che non sia della
      libreria standard o del pacchetto stesso. Scritta adesso, quando non può fallire, vale poco;
      scritta adesso, al Task 5 varrà molto. È la stessa idea di `tools/check_stack.py`: una regola
      che vive in una prova, non in una convenzione.
- [x] **Passo 6.** `make app-test` e `make app-check` verdi, `make tools-test` ancora a 143. Commit:
      `feat: lo scheletro dell'applicazione, e la regola che tiene il dominio pulito`.

---

## Task 3 — Il dominio: eventi immutabili e porte come `Protocol`

**File:** creare `app/src/mongolab/domain/eventi.py`, `domain/porte.py`, `domain/modelli.py`,
`app/tests/unit/test_dominio.py`.

- [x] **Passo 1.** Gli otto eventi del §6.3 come `@dataclass(frozen=True, slots=True)`:
      `WriteSucceeded`, `WriteFailed`, `RetryAttempted`, `LatencySampled`, `TopologyChanged`,
      `ServerStateChanged`, `BackupProgressed`, `ChunkMigrated`. Immutabili non per eleganza:
      l'evento nasce dentro un callback di pymongo e viene letto dal thread principale, e un oggetto
      congelato è ciò che rende la coda un punto di **consegna** e non una condivisione di stato.
- [x] **Passo 2.** Ogni evento porta il proprio istante come campo esplicito, preso dal `Clock` e
      **non** da `time.time()` chiamato dentro. È la condizione che rende riproducibile la cronaca
      del failover in una prova: senza, i timestamp li decide l'orologio della macchina e
      l'asserzione diventa una tolleranza.
- [x] **Passo 3.** Le cinque porte del §6.2 come `typing.Protocol`, con le firme esatte della
      tabella: `DocumentStore` (`insert_many`, `find_page`, `count`, `aggregate`),
      `ClusterInspector` (`topology`, `server_status`, `db_stats`, `shard_distribution`),
      `BackupTool` (`dump` che ritorna `Iterator[Progress]`, `restore`), `EventSink` (`emit`),
      `Clock` (`now`, `sleep`).
- [x] **Passo 4.** I modelli che le porte si scambiano — `Progress`, la descrizione di topologia, lo
      stato di un server — anch'essi congelati e senza dipendenze.
- [x] **Passo 5.** Prove: che gli eventi siano davvero immutabili (un'assegnazione solleva), e che
      un oggetto qualunque con i metodi giusti soddisfi la porta senza ereditarietà — è la proprietà
      per cui i `Protocol` sono stati scelti, e va vista funzionare almeno una volta.
- [x] **Passo 6.** `make app-test`, `make app-check`. Commit:
      `feat: il dominio — otto eventi congelati e cinque porte strutturali`.

---

## Task 4 — I doppi, scritti prima degli adattatori veri

**File:** creare `app/tests/doppi/` con `InMemoryStore`, `FakeInspector`, `FakeBackup`, `FakeClock`,
`RecordingSink`; `app/tests/unit/test_doppi.py`.

I doppi vengono prima perché sono ciò contro cui i Task 5-6 fanno TDD. Scriverli dopo
significherebbe modellarli sull'implementazione che devono verificare, che è il modo di ottenere
prove che non provano niente.

- [x] **Passo 1.** `InMemoryStore` **conserva davvero** i documenti: `insert_many` li mette in una
      lista, `count` la conta, `find_page` la impagina, `aggregate` esegue il sottoinsieme di
      pipeline che serve. Se una prova ha bisogno di una pipeline che il doppio non sa fare, la si
      aggiunge — non la si finge.
- [x] **Passo 2.** `FakeClock`, con `now` che avanza solo quando `sleep` viene chiamato. È il pezzo
      che permette di provare in millisecondi un comportamento definito in decine di secondi —
      «dopo 30 s senza primario, smetti di ritentare» — e senza di esso quella regola resterebbe non
      provata per tutto il branch.
- [x] **Passo 3.** `FakeInspector` che restituisce topologie preparate, compresa quella senza
      primario; `FakeBackup` il cui `dump` produce una sequenza di `Progress` decisa dalla prova,
      compreso il caso che fallisce a metà.
- [x] **Passo 4.** `RecordingSink`, che accumula gli eventi in una lista. È il doppio più importante
      del branch: l'asserzione tipica di questa suite è sulla **sequenza di eventi**, cioè sul
      comportamento osservabile, non sulla resa a schermo.
- [x] **Passo 5.** Una prova per doppio, che ne verifichi la promessa. Un doppio sbagliato non fa
      fallire le prove che lo usano: le fa passare per il motivo sbagliato.
- [x] **Passo 6.** `make app-test`, `make app-check`. Commit:
      `test: i doppi, scritti prima del codice che dovranno verificare`.

---

## Task 5 — `WorkloadRunner`: il carico, i tentativi, le latenze (TDD)

**File:** creare `app/src/mongolab/application/workload.py`, `app/tests/unit/test_workload.py`.

- [x] **Passo 1.** Scrivere **prima** le prove, contro `InMemoryStore` + `FakeClock` +
      `RecordingSink`: N scritture producono N `WriteSucceeded` e altrettanti `LatencySampled`; uno
      store che solleva produce `WriteFailed` seguito da `RetryAttempted`; la politica di retry
      smette quando deve e **non** prima. Eseguirle e vederle fallire.
- [x] **Passo 2.** Implementare il minimo che le fa passare. `WorkloadRunner` non sa che esiste
      MongoDB: parla con `DocumentStore`, `Clock` ed `EventSink`, e basta.
- [x] **Passo 3.** L'aggregazione delle latenze: mediana e percentili sul campione, non media. Le
      prove fissano il comportamento su campioni piccoli e noti, dove il valore atteso si calcola a
      mano — perché è lì che gli errori di un percentile si vedono.
- [x] **Passo 4.** La concorrenza con `ThreadPoolExecutor` (§6.3): i worker **non** toccano il sink
      direttamente, pubblicano su una `queue.Queue`. Provare che con più worker la sequenza di
      eventi resta completa e che nessun evento si perde; l'ordine fra worker diversi non è
      garantito, e la prova non deve pretenderlo.
- [x] **Passo 5.** La saturazione di `maxPoolSize` è **materiale didattico** dichiarato dal design:
      lasciare il gancio, cioè il parametro configurabile, e annotare che la misura arriva al Task
      16 e non qui.
- [x] **Passo 6.** `make app-test`, `make app-check`. Commit:
      `feat: il generatore di carico, con i tentativi e le latenze provati sui doppi`.

---

## Task 6 — `TopologyWatcher`: la macchina a stati, provata senza aspettare

**File:** creare `app/src/mongolab/application/topologia.py`, `app/tests/unit/test_topologia.py`.

- [x] **Passo 1.** Prove prima: una sequenza di descrizioni di topologia in ingresso produce una
      sequenza attesa di `ServerStateChanged` e `TopologyChanged`. Il caso che conta è primario →
      nessun primario → primario **diverso**, cioè il failover, e va provato con `FakeClock` in
      millisecondi.
- [x] **Passo 2.** I due numeri che giustificano l'applicazione — **durata dell'interruzione** e
      **scritture perse** — si calcolano qui, non nella TUI. La durata è fra l'ultimo istante con
      primario e il primo istante con primario nuovo; le scritture perse sono quelle confermate al
      client e assenti dopo. Provare entrambi contro `FakeClock`, dove il valore atteso è esatto e
      non una tolleranza.
- [x] **Passo 3.** Un `TopologyWatcher` che non vede un primario per la durata configurata smette di
      ritentare, ed emette l'evento che lo dice. È la regola che finora esisteva solo come frase nel
      design: adesso ha una prova, e la prova gira in millisecondi.
- [x] **Passo 4.** `make app-test`, `make app-check`. Commit:
      `feat: la macchina a stati della topologia, e i due numeri del failover`.

---

## Task 7 — `SdamBridge`: i listener che depositano e ritornano

**File:** creare `app/src/mongolab/infrastructure/sdam.py`, `app/tests/unit/test_sdam.py`.

Qui il repository incontra la conseguenza che [ADR-0006](../Decision.md#adr-0006) chiama «non
piccola» e che [ADR-0019](../Decision.md#adr-0019) risolve. La regola sta nei vincoli globali;
questo task la rende codice e prova.

- [x] **Passo 1.** Le quattro classi di listener del §6.3 — `ServerListener`, `TopologyListener`,
      `ServerHeartbeatListener`, `CommandListener` — implementate in modo che **ogni callback faccia
      tre cose**: costruire un evento congelato, metterlo in coda, ritornare. Niente altro, e in
      particolare nessuna formattazione di stringhe costosa.
- [x] **Passo 2.** Una prova che il callback ritorni entro il tempo di un inserimento in coda. Non è
      una prova di prestazioni travestita: è la verifica del vincolo che rende oneste tutte le
      misure del Task 6, perché un listener lento rallenta il driver e allunga proprio il failover
      che si sta cronometrando.
- [x] **Passo 3.** La traduzione da evento pymongo a evento di dominio si prova **senza** pymongo
      vivo, costruendo a mano gli oggetti che il driver passerebbe. Il contratto da fissare è la
      mappatura, non il driver.
- [x] **Passo 4.** Il `MongoClient` riceve i listener **per singolo client**
      (`MongoClient(event_listeners=[...])`), non globalmente: è la forma scelta da
      [ADR-0006](../Decision.md#adr-0006), e permette a due client nella stessa esecuzione di avere
      cronache separate.
- [x] **Passo 5.** `make app-test`, `make app-check`. Commit:
      `feat: il ponte SDAM — il listener costruisce, deposita e ritorna`.

---

## Task 8 — Gli adattatori veri, contro uno stack vero

**File:** creare `app/src/mongolab/infrastructure/store.py`, `infrastructure/inspector.py`,
`infrastructure/generatore.py`, `app/tests/integration/`; modificare `Makefile`.

Prima esecuzione con Docker acceso. [ADR-0020](../Decision.md#adr-0020) è la regola: si usano gli
stack del repository, non un facsimile, così i test verificano l'artefatto che il pubblico eseguirà
davvero.

- [x] **Passo 1.** `PymongoStore` che implementa `DocumentStore`, e `PymongoInspector` che
      implementa `ClusterInspector` leggendo `serverStatus`, `dbStats` e — sullo sharded — la
      distribuzione per shard. Nessuno dei due conosce il sink: emettono ritornando dati.
- [x] **Passo 2.** `DataGenerator` deterministico: lo stesso seme produce lo stesso dataset. È la
      condizione perché una misura di oggi e una di giovedì siano confrontabili, e perché la prova
      generale non scopra numeri diversi da quelli provati.
- [x] **Passo 3.** I test di integrazione avviano lo stack con i `make up-0X` esistenti e ci girano
      contro. Il target `app-test-integration` diventa vero, resta **separato** dagli unitari, e la
      sua descrizione dice che richiede Docker: la suite veloce deve restare veloce, altrimenti
      smette di essere eseguita.
- [x] **Passo 4.** Gli stessi test che il Task 4 ha scritto contro `InMemoryStore` girano contro
      `PymongoStore` dove il contratto è identico. Un doppio che si comporta diversamente
      dall'originale è un doppio che mente, e questo passo è il modo di accorgersene.
- [x] **Passo 5.** Ogni test di integrazione smonta ciò che ha acceso e non lascia dati: una misura
      che sporca lo stack fa fallire la prova dopo, per un motivo che sembra un altro.
- [x] **Passo 6.** Commit: `feat: gli adattatori pymongo, provati contro gli stack del repository`.

---

## Task 9 — `SubprocessBackup`: `mongodump` che racconta come procede

**File:** creare `app/src/mongolab/infrastructure/backup.py`, `app/tests/unit/test_backup.py`, prove
in `app/tests/integration/`.

- [x] **Passo 1.** `dump` ritorna un `Iterator[Progress]`: l'avanzamento si consuma man mano, non si
      aspetta la fine. È ciò che permette all'Atto III del Blocco 2 di mostrare il throughput che
      **non** crolla mentre il dump gira.
- [x] **Passo 2.** Il processo esterno si lancia con gli argomenti in **lista**, mai con una stringa
      di shell: la password dell'amministratore è uno degli argomenti, e una stringa di shell la fa
      comparire nella tabella dei processi di chiunque guardi.
- [x] **Passo 3.** Un `mongodump` che esce diverso da zero è un errore che si propaga con il suo
      codice e il suo messaggio, non un iteratore che finisce in silenzio. È la lezione di
      [ADR-0077](../Decision.md#adr-0077): un avviso che non cambia il codice d'uscita è un avviso
      che nessuno legge.
- [x] **Passo 4.** Prove unitarie contro `FakeBackup` per la logica di consumo e per il fallimento a
      metà; prove di integrazione contro `mongodump` vero, con `--readPreference=secondary --oplog`
      sullo stack 02, che è esattamente la forma che il Blocco 2 Atto III mostra.
- [x] **Passo 5.** `restore` e verifica dei conteggi su database di destinazione, come da copione.
      Commit: `feat: dump e restore come processi, con l'avanzamento che si consuma`.

---

## Task 10 — `RichTui`: un solo thread disegna

**File:** creare `app/src/mongolab/presentation/rich_tui.py`, `presentation/plain.py`,
`presentation/null.py`, `app/tests/unit/test_presentazione.py`.

- [x] **Passo 1.** `RichTui` implementa `EventSink`. Il ciclo `Live` gira sul **thread principale**,
      drena la coda a ogni giro e aggiorna. `refresh_per_second` è passato esplicitamente, con il
      valore scritto accanto alla ragione per cui è quello.
      *Eseguito con una deviazione dichiarata: con `auto_refresh=False`, che è ciò che rende
      vero «un solo thread», `refresh_per_second` è **inerte** e non viene passato a `Live`; il
      numero vive nel periodo del ciclo. [ADR-0085](../Decision.md#adr-0085),
      [M-027](../../app/docs/Sources.md#m-027).*
- [x] **Passo 2.** Testo grande e leggibile dall'ultima fila: è un requisito di sala, non di gusto,
      e va deciso adesso perché condiziona quante righe stanno in una schermata.
- [x] **Passo 3.** `PlainSink` (righe di testo, per le registrazioni asciinema e per chi reindirizza
      su file) e `NullSink` (niente, per le prove e per le misure del Task 16). Sono tre rese dello
      stesso flusso di eventi: se una ha bisogno di un dato che le altre non ricevono, il difetto è
      nell'evento, non nel sink.
- [x] **Passo 4.** Le prove della presentazione si fanno su `PlainSink` e `RecordingSink`, mai su
      `RichTui`: provare il disegno significa provare Rich, che ha già le sue prove.
- [x] **Passo 5.** `make app-test`, `make app-check`. Commit:
      `feat: tre rese dello stesso flusso di eventi, e un solo thread che disegna`.

---

## Task 11 — La CLI Typer: il composition root

**File:** creare `app/src/mongolab/cli.py`, `app/tests/unit/test_cli.py`; modificare `Makefile`.

*Eseguito con un allargamento dichiarato. Oltre ai file dell'elenco sono nati `infrastructure/orologio.py` — la porta `Clock` non aveva un'implementazione di produzione, e quella ovvia è sbagliata ([ADR-0086](../Decision.md#adr-0086)) — `infrastructure/bersagli.py` per la mappa del Passo 2 ([ADR-0087](../Decision.md#adr-0087)), `infrastructure/zavorra.py` per `--doc-size`, `presentation/rapporto.py` per l'uscita di `stats`, e le prove che li accompagnano; `application/workload.py` ha ricevuto `lettori` e `durata_s`, `app/pyproject.toml` la voce `[project.scripts]`, e il `Makefile` tre target `app-stats`/`app-watch`/`app-workload`. Le quattro opzioni di `workload` sono state implementate tutte, e non solo nominate, perché il Task 16 misurerà quella riga di comando.*

- [x] **Passo 1.** `cli.py` è **l'unico punto che conosce le classi concrete** (§6.1). Costruisce
      gli adattatori e li inietta; tutto il resto riceve porte. Se un `import` di `pymongo` compare
      altrove che in `infrastructure/`, è un difetto anche se funziona.
- [x] **Passo 2.** I tre comandi diretti del §6.4: `mongolab stats --target rs`,
      `mongolab watch --target rs`, e
      `mongolab workload --target rs --writers 8 --readers 4 --doc-size 2k --duration 120`. Il
      `--target` sceglie lo stack, e la mappa fra nome e URI sta in un posto solo.
      *Eseguito. Due dei tre comandi erano sbagliati alla prima esecuzione contro un MongoDB vero, e le prove unitarie non potevano vederlo: `workload` scriveva nella collezione seminata e falliva ogni inserimento con `E11000` uscendo con zero ([ADR-0088](../Decision.md#adr-0088), [M-032](../../app/docs/Sources.md#m-032)); `watch` raccontava ogni transizione due volte perché aveva due narratori sullo stesso fatto ([ADR-0089](../Decision.md#adr-0089), [M-033](../../app/docs/Sources.md#m-033)). `stats` leggeva la topologia per prima e diceva `sconosciuto` di un server sano ([M-031](../../app/docs/Sources.md#m-031)).*
- [x] **Passo 3.** La scelta del sink è un'opzione, non una condizione sparsa: `--sink rich`
      (predefinito), `plain`, `null`. È il gancio con cui il Task 18 produce le registrazioni senza
      toccare il codice.
- [x] **Passo 4.** Le prove della CLI verificano il **cablaggio** — che `--sink plain` produca un
      `PlainSink`, che un `--target` sbagliato fallisca con un messaggio e un codice d'uscita diverso
      da zero — non il comportamento dei componenti, già provato altrove.
      *Eseguito. Il codice d'uscita è **2**, quello di `typer.BadParameter`, e il messaggio va ripulito prima di poterlo asserire: Rich lo incornicia e lo manda a capo dove finisce il riquadro, quindi un'asserzione ingenua dipenderebbe dalla larghezza del terminale di chi esegue le prove ([M-034](../../app/docs/Sources.md#m-034)).*
- [x] **Passo 5.** `make app-test`, `make app-check`. Commit:
      `feat: la CLI Typer, unico punto che conosce le classi concrete`.

---

## Task 12 — L'applicazione in container, sulla rete degli stack

**File:** creare `app/Dockerfile` e il servizio Compose; modificare `Makefile`, `tools/images.env`,
`tools/preflight.sh`, `tools/pull-images.sh`.

[ADR-0012](../Decision.md#adr-0012) è la ragione per cui questo task esiste e non è
un'ottimizzazione: con `directConnection=false`, che è il valore predefinito, il client scopre tutti
i membri e parla con il primario — e quella scoperta è ciò che il talk mostra, ed è la prima cosa
che si rompe se l'applicazione gira sull'host e il cluster dentro Docker.

- [ ] **Passo 1.** `Dockerfile` su `python:3.13-slim`, dipendenze con `uv`, sorgente in
      **bind-mount** durante lo sviluppo (§6.5), così che una modifica non richieda una
      ricostruzione.
- [ ] **Passo 2.** Il servizio si attacca alla rete Compose dello stack e si collega **per nome di
      servizio**. Verificare che la scoperta funzioni davvero: la riserva dichiarata di ADR-0012
      dice che la documentazione non afferma che il driver usi gli host memorizzati nella
      configurazione del set, e che se serve affermarlo va **mostrato in demo**. Questo è il task
      che lo mostra, e l'esito è una voce in `Sources.md`.
- [ ] **Passo 3.** `directConnection=true` **solo** per lo stack 01, dove non c'è nulla da scoprire,
      con il commento che dice perché la differenza è voluta.
- [ ] **Passo 4.** L'immagine dell'applicazione entra nell'elenco di quelle da avere in cache prima
      del talk ([ADR-0009](../Decision.md#adr-0009)): `images.env`, `pull-images.sh` e il controllo
      di `preflight.sh`. Un'immagine che si scarica la mattina del talk è un'immagine che non c'è.
- [ ] **Passo 5.** `make stack-check` verde — se `check_stack.py` ha una regola che il servizio nuovo
      viola, la regola ha ragione finché non si dimostra il contrario.
- [ ] **Passo 6.** Commit: `feat: l'applicazione in container, sulla rete dove la scoperta funziona`.

---

## Task 13 — `demo failover --step`: la scena centrale del talk

**File:** creare `app/src/mongolab/application/scenari.py` e la sottocomanda `demo`; prove in
`app/tests/unit/` e `app/tests/integration/`.

È l'Atto II del Blocco 2, cinque minuti, ed è la ragione per cui l'applicazione esiste.

- [ ] **Passo 1.** `--step` mette in pausa prima di ogni fase e riparte con Invio: è modalità da
      palco. Senza `--step` lo stesso scenario gira da solo — ed è **così** che si producono le
      registrazioni di riserva, che per costruzione mostrano esattamente ciò che si farà dal vivo.
      Una sola implementazione, due modi.
- [ ] **Passo 2.** La sequenza del copione: carico attivo, `docker compose stop` del primario,
      cronaca dell'elezione con timestamp al millisecondo, **durata dell'interruzione e scritture
      perse**, riavvio e recupero.
- [ ] **Passo 3.** Il supplemento previsto dal copione: `docker compose pause` per il nodo
      *irraggiungibile ma vivo* — timeout invece di connection refused, cioè la differenza fra
      server morto e rete partizionata. È la parte che il pubblico non si aspetta, e vale i trenta
      secondi che costa.
- [ ] **Passo 4.** Lo scenario si prova con `RecordingSink` e i doppi: l'asserzione è sulla
      **sequenza di eventi**, verificabile senza aspettare dieci secondi di elezione. Poi una prova
      di integrazione che la stessa sequenza esca da uno stack vero.
- [ ] **Passo 5.** Confrontare i numeri con quelli che `feature/02` ha già misurato —
      [V-031](../Sources.md#v-031) (la forbice 8-10 s) e [V-033](../Sources.md#v-033) (12 901
      confermate, 0 perdute). Se l'applicazione dice qualcosa di diverso, **uno dei due è sbagliato**
      e va capito quale prima di andare avanti.
- [ ] **Passo 6.** Commit: `feat: la scena del failover, con i due numeri che la chiudono`.

---

## Task 14 — `demo backup-live` e `demo restore`

**File:** modificare `app/src/mongolab/application/scenari.py`; prove di integrazione; modificare
`docs/03-amministrazione/backup-restore.md`, `docs/04-mongosh/guida-mongosh.md`.

Atto III del Blocco 2, quattro minuti.

- [ ] **Passo 1.** `mongodump --readPreference=secondary --oplog` **sotto carico**, con il
      throughput mostrato accanto: la promessa del copione è che non crolli, e va vista, non
      affermata.
- [ ] **Passo 2.** `restore` su database di destinazione e verifica dei conteggi a schermo.
- [ ] **Passo 3.** Saldare il rimando: `docs/04-mongosh/guida-mongosh.md` dichiara che
      `mongodump`/`mongorestore` «sono materia di `feature/04`, insieme al backup a caldo». La
      pagina dei backup riceve la parte applicativa, e il rimando diventa un collegamento.
- [ ] **Passo 4.** Commit: `feat: il backup a caldo come scena, e il rimando di mongosh saldato`.

---

## Task 15 — `demo sharding`: il Blocco 3 sotto carico

**File:** modificare `app/src/mongolab/application/scenari.py`; prove di integrazione contro lo
stack 03.

- [ ] **Passo 1.** Distribuzione dei chunk **sotto carico** e balancer al lavoro: è la parte che
      `feature/03` ha potuto mostrare solo a riposo, e la pagina dello sharded dichiara scoperto «il
      comportamento oltre la soglia del balancer» proprio perché serviva carico controllato.
- [ ] **Passo 2.** L'evento `ChunkMigrated` trova finalmente chi lo emette. Se durante la scrittura
      risulta che non è osservabile dal client, va detto: un evento dichiarato nel design e non
      producibile è una voce in `Sources.md` e un ADR, non un campo morto nel codice.
- [ ] **Passo 3.** `explain()` che contrappone query mirata e scatter-gather, come da copione. La
      pagina dello sharded ha già il materiale; qui si aggiunge il lato client.
- [ ] **Passo 4.** Commit: `feat: la scena dello sharding, con i chunk che si muovono sotto carico`.

---

## Task 16 — I debiti di misura, saldati sotto carico controllato

**File:** `docs/Sources.md`, `docs/Decision.md`, `docs/02-architetture/standalone.md`,
`replica-set.md`, `sharded-cluster.md`.

Quattro pagine hanno scritto per iscritto che una misura «ha senso solo sotto carico controllato,
cioè con l'applicazione Python di `feature/04`, e prima di allora sarebbe aria». Adesso
l'applicazione c'è. Questo task va eseguito **prima** delle pagine nuove del Task 17: una pagina
scritta su misure che non esistono ancora è esattamente l'aria che quelle righe promettevano di
evitare.

- [ ] **Passo 1.** `j: true` contro lo standalone, la controprova di [V-016](../Sources.md#v-016) —
      100 scritture confermate e sparite. La riserva dice che `j: true` dovrebbe azzerare la perdita
      **al prezzo della velocità**: misurare entrambi i lati, perché un confronto che riporta solo
      la buona notizia non è un confronto.
- [ ] **Passo 2.** `retryWrites=false` e `maxStalenessSeconds` sul replica set, i due scoperti
      dichiarati in «cosa questa pagina non dice» di `replica-set.md`.
- [ ] **Passo 3.** Il **confronto di prestazioni fra le tre architetture**, sotto lo stesso carico e
      lo stesso dataset deterministico. È il debito che tutte e tre le pagine hanno intestato qui.
      Ogni numero porta la sua riserva sulla stessa riga, come vuole la disciplina del repository:
      un lab su un portatile non è un datacenter, e va scritto accanto al numero, non in una nota in
      fondo.
- [ ] **Passo 4.** La saturazione di `maxPoolSize`, che il design chiama «materiale didattico» e il
      Task 5 ha lasciato in sospeso. E `analyzeShardKey`, scoperto dichiarato di
      `sharded-cluster.md`.
- [ ] **Passo 5.** Ogni misura è una voce `V-` con esiti e riserve; le sezioni «cosa questa pagina
      non dice» perdono le righe saldate e **guadagnano il collegamento**. Le righe non si
      cancellano in silenzio: diventano rimandi.
- [ ] **Passo 6.** `make docs-check`. Commit: `docs: i debiti di misura, saldati sotto carico`.

---

## Task 17 — Le tre pagine che `docs/README.md` promette qui

**File:** creare `docs/06-sviluppo/architettura-app.md`, `docs/06-sviluppo/tdd-e-doppi.md`,
`docs/03-amministrazione/statistiche-monitoraggio.md`; modificare `docs/README.md`, `README.md`,
`docs/citazioni-riportare-slide.md`.

`docs/README.md` intesta tre pagine a questo branch: finché non esistono, quelle righe sono promesse
invece che collegamenti.

- [ ] **Passo 1.** `architettura-app.md`: stratificazione, porte, modello a eventi, composition
      root. La pagina spiega **perché** le dipendenze puntano verso l'interno mostrando che cosa si
      guadagna — la suite unitaria che gira senza Docker — non citando un principio.
- [ ] **Passo 2.** `tdd-e-doppi.md`: separazione fra suite unitaria e di integrazione, fake contro
      mock, e «come si prova il failover senza aspettarlo», che è la domanda a cui `FakeClock`
      risponde. Il materiale l'hanno prodotto i Task 4-6: qui si scrive, non si inventa.
- [ ] **Passo 3.** `statistiche-monitoraggio.md`: `serverStatus`, `dbStats`, metriche di replica,
      **cosa guardare sotto carico**. Le misure sono quelle del Task 16.
- [ ] **Passo 4.** Nel `README.md` di radice, la riga che dichiara l'applicazione non ancora
      esistente smette di essere vera e va aggiornata. È l'ultimo punto in cui il repository dice di
      sé una cosa che non è più così.
- [ ] **Passo 5.** Le frasi che meritano una slide vanno in `docs/citazioni-riportare-slide.md`
      **adesso**, non a fine progetto.
- [ ] **Passo 6.** `make docs-check`. Commit: `docs: le tre pagine dovute a feature/04`.

---

## Task 18 — Le registrazioni del Blocco 2, e la chiusura

**File:** `docs/05-talk/registrazioni/` e il suo `README.md`; `docs/registro-operativo-sviluppo.md`.

- [ ] **Passo 1.** Le registrazioni si producono con `--sink plain` e senza `--step`, cioè con lo
      stesso codice della scena dal vivo: è la proprietà che il Task 13 ha costruito apposta, e che
      rende la registrazione una copia fedele invece di una ricostruzione.
- [ ] **Passo 2.** Il formato è `asciicast` ([ADR-0050](../Decision.md#adr-0050)): leggero,
      versionabile, testo copiabile. Gli `.mp4` **non** entrano in git e restano compito del
      relatore — l'avviso di `preflight` diventa bloccante dal 18 settembre.
- [ ] **Passo 3.** Indice delle registrazioni aggiornato con che cosa mostra ciascuna, come è stata
      prodotta e quando si usa.
- [ ] **Passo 4.** I controlli, tutti: `make preflight`, `make docs-check`, `make stack-check`,
      `make tools-test`, `make app-test`, `make app-check`. Il conteggio delle prove va scritto nel
      registro.
- [ ] **Passo 5.** Voce di chiusura nel registro con le note di metodo prodotte dal branch e la riga
      di stato — decisioni, verifiche, note, prove.
- [ ] **Passo 6.** PR verso `develop`. **Mai `git flow feature finish`**: salta la revisione, ed è
      già successo con la PR #1. La fusione la fa il Product Owner. A PR unita, la chiusura del
      worktree segue l'ordine di [ADR-0079](../Decision.md#adr-0079) — **si sgancia la sessione
      prima di rimuovere la directory** — e i `.env` si salvano prima
      ([ADR-0056](../Decision.md#adr-0056)).

---

## Che cosa questo piano non copre

- **Gli `.mp4`.** Solo il relatore può girarli, e non dipendono da questo branch.
- **I cinque debiti di documentazione sui backup dei config server** aperti da
  [ADR-0071](../Decision.md#adr-0071): appartengono allo sharded, non all'applicazione.
- **Il runbook del talk** (`docs/05-talk/runbook-demo.md`, §9 del design): è documento unico e
  autonomo, e si scrive quando tutte le scene esistono, cioè dopo questo branch.
- **La `release/1.0`** del 16 settembre, con la seconda data del controllo di
  [ADR-0058](../Decision.md#adr-0058).
