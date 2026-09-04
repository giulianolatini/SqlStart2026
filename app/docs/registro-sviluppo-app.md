# Registro di sviluppo di `mongolab`

Questa è la cronaca di come l'applicazione viene costruita: che cosa è stato fatto, in che ordine, e
soprattutto **che cosa è stato scoperto strada facendo** — comprese le volte in cui la scoperta ha
contraddetto il piano.

Non sostituisce il [registro operativo](../../docs/registro-operativo-sviluppo.md) del repository,
che è cronologico e copre tutte le feature. Qui c'è solo `app/`, raccontato per **task** invece che
per giornata, con il filo del ragionamento invece che dei commit.

**Come si legge.** Ogni voce ha la stessa forma: che cosa chiedeva il task, che cosa è stato scritto,
che cosa è andato diversamente dal previsto, che cosa resta aperto. La sezione *«Diversamente dal
previsto»* è la parte interessante — se manca, il task è filato liscio, ed è raro.

Il piano di riferimento è
[`2026-09-02-piano-feature-04-app-python.md`](../../docs/00-progetto/2026-09-02-piano-feature-04-app-python.md):
diciotto task, finestra 2–11 settembre 2026.

**Come si scrive.** Questo registro è **append-only**: le voci non si riscrivono. Se una voce
successiva scopre che una precedente era imprecisa, la correzione va nella voce nuova o in una
riserva di [`Sources.md`](Sources.md) — mai cancellando quel che c'era. È la stessa disciplina del
registro del repository, e serve a poter rileggere non solo che cosa si è deciso, ma **con quali
informazioni** lo si è deciso.

---

## Prima del codice: che cosa era già stato deciso

`app/` non è partita da un foglio bianco. Al momento del primo commit esistevano già, nate mesi
prima insieme al design del talk:

- il linguaggio e il driver ([ADR-0006](../../docs/Decision.md#adr-0006));
- l'idea che il nucleo non conosca l'interfaccia ([ADR-0007](../../docs/Decision.md#adr-0007));
- la regola di concorrenza per i listener ([ADR-0019](../../docs/Decision.md#adr-0019));
- il rifiuto di `testcontainers` ([ADR-0020](../../docs/Decision.md#adr-0020));
- l'obbligo di funzionare offline ([ADR-0009](../../docs/Decision.md#adr-0009)).

Sono tutte in [decisioni-che-vincolano-app.md](decisioni-che-vincolano-app.md), con l'indicazione di
dove si vedono nel codice. Vale la pena notare che **le due più tecniche — ADR-0019 e ADR-0020 —
sono nate leggendo la documentazione, non scrivendo codice.** Il progetto ha scoperto la consegna
sincrona degli eventi di PyMongo e il limite di `MongoDbContainer` prima di avere una riga da
correggere. È il tipo di lettura che si fa malvolentieri, e che qui ha risparmiato due riscritture.

### Una premessa che il branch ha dovuto correggere

Il documento di design assegnava a questa feature, come **primo passo**, la verifica del supporto di
`testcontainers-python` ai replica set. Quel passo non è stato eseguito, perché la risposta esisteva
già da otto giorni: ADR-0020 aveva superato ADR-0011 il 25 agosto.

La lezione è registrata come nota di metodo 138 e vale la pena riportarla qui, perché riguarda
chiunque erediti un piano: **un documento superato è più pericoloso dove assegna lavoro che dove
afferma un fatto.** Un'affermazione sbagliata dà fastidio quando qualcuno la controlla; un compito
sbagliato si autoconserva, perché resta nella lista, sembra da fare, e chi lo esegue non ha motivo
di sospettare — ha appena letto il documento che glielo assegna.

---

## Task 1 — L'appuntamento con la 8.0.30

**Che cosa chiedeva.** Non codice: una data. Il repository aveva un appuntamento fissato per
verificare se MongoDB 8.0.30 fosse uscita, prima di montarci sopra l'applicazione.

**Esito.** La 8.0.30 **non è pubblicata**. Il lab resta su 7.0.40. La documentazione della patch
esiste, i binari no, e nessuna pagina consultata contiene una data prevista.

**Diversamente dal previsto — due volte.**

La prima: interrogare un registro di immagini e ottenere `count: 0` sembra una risposta, e non lo è.
`0` è indistinguibile dal risultato di un filtro sbagliato, di un endpoint deprecato o di un
repository abbandonato — quattro cause diverse, una sola risposta, ed è la risposta che si sperava.
La difesa è **una seconda interrogazione di controllo che deve dare un numero diverso da zero**:
chiedere la 8.0.29 e vedersi rispondere 164 tag, alcuni ricostruiti quella mattina, trasforma
un'assenza dichiarata in un'assenza misurata. Nota di metodo 140.

La seconda: il piano diceva che questo esito non richiedeva un ADR. Il controllo automatico delle
citazioni ha rifiutato — una fonte che nessun ADR cita è orfana — e **aveva ragione il controllo**.
La decisione da registrare non era sulla versione, che non cambia, ma sul **calendario**: due
appuntamenti diventati uno. Nota di metodo 141.

**Perché sta in un registro dell'applicazione.** Perché la versione di MongoDB su cui `mongolab`
gira è un vincolo dell'applicazione quanto degli stack, e perché la disciplina — misurare l'assenza
invece di dichiararla — riguarda ogni volta che il codice chiederà «c'è?» a qualcosa di remoto.

---

## Task 2 — Uno scheletro che non fa niente, in modo verificabile

**Che cosa chiedeva.** La struttura di `app/`: `pyproject.toml`, il pacchetto `mongolab` con i
quattro strati, la suite divisa fra unitaria e integrazione, i bersagli `make`.

**Che cosa è stato scritto.** Cinque prove, `mypy --strict` verde su 12 file, l'ambiente su Python
**3.13.15** con `requires-python = ">=3.13,<3.14"`. Il tetto è deliberato: l'host ha la 3.14.7, che
il design considera troppo recente per garantire il supporto di tutte le dipendenze di test. Meglio
scriverlo che affidarlo alla fortuna della risoluzione.

**La prova che conta è una guardia.** `test_scheletro.py` percorre i sorgenti di `domain/` e
`application/` con il modulo `ast` e boccia ogni import che non sia libreria standard o il pacchetto
stesso. È il vincolo che rende la suite unitaria istantanea, ed è codice invece che buona
intenzione. Il dettaglio sta in
[05-tipi-prove-e-guardie.md](05-tipi-prove-e-guardie.md#la-guardia-architetturale).

**Ed è stata rotta apposta.** Aggiunto `import pymongo` a `domain/__init__.py`, la prova è fallita
dicendo `domain/__init__.py importa ['pymongo']`, e la violazione è stata tolta. È la nota di metodo
142, e da qui in poi è la regola della casa: **un controllo scritto quando non può fallire va rotto
apposta, subito.** Una guardia architetturale nasce per definizione davanti a un albero vuoto; il
suo primo verde non distingue «tutto a posto» da «non c'era niente da guardare».

**Tre trappole schivate scrivendo.**

1. **Copiare `tools/pyproject.toml`** avrebbe portato con sé `pythonpath = ["."]`, che lì serve e
   qui disferebbe il layout `src/`. Gli import continuerebbero a funzionare — dall'albero dei
   sorgenti invece che dal pacchetto installato. Cioè le prove smetterebbero di verificare ciò che
   si distribuisce, senza dirlo.
2. **`testpaths = ["tests"]`** avrebbe trascinato l'integrazione dentro la suite veloce dal Task 8
   in poi, senza che nessuno l'avesse deciso. È `tests/unit`, e l'integrazione si chiede per nome.
3. **`mypy` rifiuta due `conftest.py` omonimi.** La soluzione è quella che suggerisce lui:
   `__init__.py` nelle directory di prova.

**Una quarta trappola è stata lasciata dov'era**, e vale la pena dire perché: il bersaglio
`failover-02-maggioranza` è lungo 23 caratteri e sballa l'incolonnamento di `make help`, che ne
prevede 16. Toccarlo avrebbe cambiato la resa di tutti i bersagli dentro un commit che parla d'altro.

**Il codice d'uscita 5.** `tests/integration/` è vuota fino al Task 8, e pytest su una directory
vuota esce **5**. Non è un errore e non è un successo. Il `Makefile` lo **traduce** invece di
sopprimerlo — nota di metodo 143, e il ragionamento completo è in
[05-tipi-prove-e-guardie.md](05-tipi-prove-e-guardie.md#il-codice-duscita-5-tradotto-invece-che-nascosto).

---

## Task 3 — Il dominio: otto eventi, cinque porte

**Che cosa chiedeva.** I modelli, gli otto eventi del design e le cinque porte, senza alcuna
implementazione: solo i tipi che tutto il resto userà.

**Che cosa è stato scritto.** `domain/modelli.py`, `domain/eventi.py`, `domain/porte.py` e
**19 prove** unitarie (erano 5). Il contenuto è spiegato in
[03-eventi-immutabili.md](03-eventi-immutabili.md) e [02-porte-e-doppi.md](02-porte-e-doppi.md); qui
c'è il processo.

**L'ordine è stato: prima le prove.** Non per ortodossia, ma perché scrivere l'asserzione prima
costringe a decidere che cosa si sta affermando. La prova
`test_gli_eventi_del_design_sono_otto_e_sono_quelli` è stata scritta prima che gli otto eventi
esistessero, e ha determinato i loro nomi.

**Diversamente dal previsto — il terzo esito.**

Applicando la disciplina della nota 142 ho aggiunto un nono evento mutabile per vedere fallire la
guardia sugli eventi congelati. **Non è fallita: la classe non è arrivata a esistere.**

```
TypeError: cannot inherit non-frozen dataclass from a frozen one
```

Il congelamento della base si propaga come regola del linguaggio. L'asserzione su `frozen` nelle
sottoclassi non poteva fallire — era un controllo sul compilatore travestito da prova.

Questo ha aggiunto qualcosa che la nota 142 non prevedeva: rompere una guardia apposta ha **tre**
esiti, non due. Il controllo scatta e va bene; il controllo tace e va corretto; oppure **la
violazione non è costruibile**. Il terzo è il più insidioso perché somiglia al primo — entrambi
finiscono in verde. È la nota di metodo 144, e la conseguenza pratica è che l'asserzione va tolta
**nominando l'esperimento** che l'ha dimostrata superflua, altrimenti il prossimo lettore la
riaggiunge in buona fede.

La guardia è stata quindi riscritta in due: una sulla base, dove `frozen`, l'ordine dei campi e
`slots` si possono ancora perdere; una sulle sottoclassi, che asserisce soltanto `slots` — l'unica
cosa che si dimentica in silenzio.

**Diversamente dal previsto — un buco scritto come prova verde.**

`isinstance` contro un `Protocol` `runtime_checkable` guarda i **nomi** dei metodi, non le firme: un
doppio con la firma sbagliata passa il controllo. Il primo istinto era scriverlo in un commento. Un
commento invecchia senza dirlo.

È diventato una **prova che passa**: un oggetto con la firma sbagliata che *supera* `isinstance`, e
l'asserzione che dice esattamente questo. Costa una prova verde in più, e in cambio dà due cose —
documentazione che il lettore incontra dove serve, e una sentinella che fallirebbe il giorno in cui
il comportamento di Python cambiasse. Nota di metodo 145.

**Una prova scritta e subito cancellata.** Ne avevo scritta una che asseriva
`all(tipo is not None for tipo in ...)` sui tipi nominati dalle porte. Non poteva fallire: se un
tipo non esistesse, il modulo non si importerebbe e la prova non verrebbe eseguita. È esattamente
ciò che la nota 142 vieta, ed è finita nel cestino prima di essere eseguita una volta.

**Una misura che ha corretto una mia frase.** Avevo scritto che senza `slots` gli eventi «tornano ad
avere un `__dict__` in cui due thread possono scriversi di nascosto». Misurato
([M-003](Sources.md#m-003)): il `__dict__` c'è, ma l'assegnazione normale resta bloccata da
`frozen`; passano solo `object.__setattr__` e la scrittura diretta nel `__dict__`. La formulazione
corretta è **«`frozen` protegge da una distrazione, `slots` protegge anche da chi conosce la
scorciatoia»**, e la correzione vive in M-003 e in
[03-eventi-immutabili.md](03-eventi-immutabili.md#che-cosa-compra-slots-misurato).

**Un errore di mypy che vale la pena conoscere.** `Evento.__dataclass_params__` esiste a runtime ma
mypy non lo vede: il suo plugin per le dataclass modella i **campi**, non i parametri del decoratore.
Serve un `# type: ignore[attr-defined]`, e vale la pena commentarlo, perché sembra una svista.

---

## Fuori dai task — Questa documentazione

**Da dove viene.** Su richiesta del PO, dopo il Task 3: molto di ciò che era stato spiegato in chat
mentre si scriveva il dominio era materiale didattico — proprio il tipo di spiegazione che serve a
raccontare un'applicazione che parla con MongoDB — e stava andando perduto.

**Che cosa è stato costruito.** Cinque pagine di principi, questo registro, una mappa delle decisioni
vincolanti e un registro delle fonti proprio dell'applicazione. L'indice è in [README.md](README.md).

**Diversamente dal previsto — due Sources.md.**

L'istinto era mettere le fonti nel registro canonico `docs/Sources.md`. Verificando come funziona
`check_citations.py` è emerso che non si poteva: quel controllo considera **orfana** — e boccia —
ogni fonte che nessun ADR citi. Le fonti dell'applicazione sono documentazione di linguaggio e di
strumenti, e nessun ADR le cita né deve citarle: sarebbero state tutte orfane.

La soluzione non è stata aggirare il controllo ma **aprire la sede che mancava**: un registro
separato, con prefissi diversi (`A-` per le fonti esterne, `M-` per le misure) proprio perché non si
confondano con gli `S-`/`V-`/`C-` canonici. Le voci canoniche vengono **puntate, mai copiate**:
una fonte duplicata è una fonte che prima o poi diverge.

È lo stesso schema della nota 141 — quando un controllo automatico ostacola qualcosa di legittimo,
la risposta giusta è quasi sempre che manca una sede, non che la regola è di troppo.

**Diversamente dal previsto — una citazione falsa, presa in tempo.**

Scrivendo `Sources.md` avevo attribuito ad ADR-0024 la regola «il registro operativo non si
riscrive». Andando a verificare, ADR-0024 dice tutt'altro (parla della gerarchia delle fonti), e
**nessun ADR** enuncia quella regola: è una pratica costante del repository, non una decisione
scritta. La citazione è stata sostituita con un rinvio alla pratica e al precedente di ADR-0068.

Vale la pena registrarlo perché è l'errore più facile da commettere scrivendo documentazione
densamente citata: **una citazione plausibile è più pericolosa di una mancante**, perché nessuno la
va a controllare.

---

## Task 4 — I doppi, scritti prima del codice che dovranno verificare

**Che cosa chiedeva.** Un doppio per porta, in `tests/doppi/`, e una prova per doppio.

**Che cosa è stato scritto.** Sei file — `archivio.py`, `ispettore.py`, `backup.py`, `orologio.py`,
`raccoglitore.py` e l'`__init__.py` che li raccoglie — più `tests/unit/test_doppi.py`. Le prove
passano da **19 a 54**. Che cosa fanno i doppi e perché stanno in `tests/` è in
[02-porte-e-doppi.md](02-porte-e-doppi.md#i-doppi-non-sono-mock); qui c'è il processo.

**Prima i doppi, e non è un dettaglio d'ordine.** I Task 5 e 6 faranno TDD contro questi oggetti.
Scriverli dopo avrebbe voluto dire modellarli sul codice che devono verificare — e un doppio che
concorda con l'implementazione per costruzione produce prove che non provano niente. Per la stessa
ragione ho letto i Task 5 e 6 **prima** di disegnarli: è da lì che viene la scelta di dare a
`FakeInspector` una *sequenza* di topologie invece di una sola, perché ciò che il Task 6 deve
provare non è uno stato ma un passaggio.

**Diversamente dal previsto — avevo rifiutato ciò che andava implementato.**

`InMemoryStore` all'inizio rifiutava `{"campo": None}`. La motivazione, scritta nella docstring, era
che `dict.get` arriva alla semantica di MongoDB **per caso**, e per caso è il modo peggiore di
essere giusti. Poi ho aperto il manuale: quella semantica è dichiarata — `{campo: null}` prende sia
il `null` esplicito sia i documenti senza quel campo ([A-006](Sources.md#a-006)). Una regola
dichiarata si implementa deliberatamente, con la citazione accanto e la prova che la fissa;
rifiutarla era la scelta più debole, non la più prudente.

Il rifiuto è rimasto dove è giusto: sul confronto con un sottodocumento intero, che MongoDB risolve
«including the field order» ([A-007](Sources.md#a-007)) mentre l'uguaglianza fra `dict` di Python
l'ordine lo ignora. Il criterio che distingue i due casi — se esista un'implementazione giusta da
scrivere — è la **nota di metodo 150**.

**Tre rotture deliberate, e ognuna ha detto una cosa diversa.**

| Rottura | Esito | Che cosa ha insegnato |
|---|---|---|
| `_corrisponde` restituisce sempre `True` | 7 prove rosse, due con `DID NOT RAISE` | il rifiuto è verificato quanto il comportamento ([M-006](Sources.md#m-006)) |
| `dump` scritta come funzione generatrice | 1 prova rossa, **mypy verde** | un errore di *quando* non è un errore di tipo ([M-007](Sources.md#m-007)) |
| `_come_intero` accetta i booleani | **54 verdi** | una guardia mai provata sopravvive alla revisione, non alla mutazione |

La terza non era in programma: è nata da una riserva che avevo scritto a tavolino su M-006 —
«un `$limit` che tagliasse dalla coda passerebbe» — e che è risultata **falsa** appena sono andato a
guardare la prova. Cercando una lacuna vera l'ho trovata al secondo tentativo. È la **nota 152**:
anche una riserva è un'affermazione.

**Che cosa i doppi non sanno fare, dichiarato per nome.** `$group` non c'è, un `topology()` che
solleva non c'è, uno store che fallisce le scritture non c'è. Non sono dimenticanze: nessuna prova
li ha ancora chiesti, e il messaggio di `NonSupportato` lo dice a chi li incontra. Lo store che
fallisce arriverà al Task 5, insieme alla prova che ne ha bisogno.

---

## Task 5 — Il generatore di carico, i tentativi, le latenze

**Che cosa chiedeva.** `WorkloadRunner` in TDD contro i doppi: N scritture producono N
`WriteSucceeded` e altrettanti `LatencySampled`; uno store che solleva produce `WriteFailed` seguito
da `RetryAttempted`; la politica smette quando deve e **non** prima. Poi le latenze aggregate per
percentili, la concorrenza del §6.3, e il gancio per `maxPoolSize` lasciato senza misurarlo.

**Che cosa è stato scritto.** `application/workload.py` — la prima classe di caso d'uso del
progetto — e `tests/unit/test_workload.py`. Insieme sono nati i due doppi che mancavano,
`ArchivioCheRompe` e `ArchivioLento`, e `RecordingSink` ha imparato a ricordare **da quale thread**
è stato chiamato. Le prove passano da **54 a 106**, `mypy --strict` verde su 25 file. Le scelte —
percentili, tentativi, coda — sono spiegate in
[06-carico-tentativi-e-latenze.md](06-carico-tentativi-e-latenze.md); qui c'è il processo.

**Il rosso c'era, ma non dove me lo aspettavo.** Le prove scritte per prime fallivano tutte con un
`ModuleNotFoundError`: il modulo non esisteva. È un rosso vero ma povero — dice «manca tutto», non
«questa guardia serve». Alla prima esecuzione dopo l'implementazione la suite è passata intera, e a
quel punto la domanda onesta non è «è verde?» ma «quali di queste prove avrebbero visto un errore?».
La risposta si compra solo rompendo, ed è la **nota 142** applicata alla lettera: cinque rotture
deliberate, una alla volta, con ripristino da copia ([M-010](Sources.md#m-010)).

**La quinta rottura ha trovato una guardia scoperta.** Togliendo da `PoliticaTentativi.attesa_ms` il
rifiuto del primo tentativo — quello che non attende, perché non ha niente da ritentare — la suite è
rimasta **verde su 105**. Nessuna prova la interrogava. È il terzo esito della **nota 144** nella sua
forma più utile: la rottura non ha confermato una difesa, ne ha rivelato l'assenza. La prova
`test_l_attesa_del_primo_tentativo_non_esiste` è nata lì, e da allora sono 106.

**Diversamente dal previsto — una rottura che non fallisce, si pianta.**

La quarta rottura sposta fuori dal `finally` la sentinella con cui ogni worker dichiara di aver
finito. Mi aspettavo un rosso; ho ottenuto un blocco. Il worker muore prima di segnalare, il
chiamante aspetta un `None` che non arriverà, e la suite resta ferma al 68 % finché il `timeout` non
la uccide: `Error 143`. Nessun `FAILED`, nessun messaggio, nessun punto del codice indicato.

Ai tre esiti della nota 144 se ne aggiunge un quarto, ed è il peggiore da leggere, perché **somiglia
a un problema della macchina molto più che a un difetto del codice** — la reazione naturale davanti
a una suite che non torna è pensare a Docker, alla rete, al portatile. È la **nota di metodo 153**.

**Diversamente dal previsto — «p95» non era un numero.**

Avevo scritto `percentile` come una cosa ovvia. Poi ho misurato: sullo stesso campione, con un
gradino di latenze, il novantacinquesimo percentile vale **1,0** per rango più vicino, **3,45** con
`statistics.quantiles(method='inclusive')`, **47,55** con `'exclusive'`
([M-009](Sources.md#m-009)). Quarantasette volte l'uno dall'altro, e nessuno dei tre sbaglia:
rispondono a tre domande diverse.

La scelta — rango più vicino, perché ogni numero riferito deve essere stato osservato — non è
cambiata. È cambiato il suo statuto: da abitudine a decisione documentata, con la sua fonte
([A-009](Sources.md#a-009)) e con la sua riserva scritta, che è scomoda: su quel campione il p95 per
rango cade in cima al pianerottolo e non racconta la coda. È la ragione per cui il riepilogo porta
sei numeri e non uno. **Nota 154.**

**Lo zero che sembra una misura.** La prima stesura del riepilogo restituiva latenze a zero quando
non c'era nessun campione. Un p95 di zero millisecondi su una corsa in cui tutto è fallito legge
«velocissimo» dove la verità è «mai arrivato»: è la peggiore risposta mancante, perché non ha la
faccia di una risposta mancante. Ora è `latenze=None`, e `riassumi` su un campione vuoto solleva
invece di inventare. **Nota 155**, ed è la regola dei doppi applicata alle statistiche.

**Un aiutante di prova che spegneva il controllo.** Il filtro `_specie(eventi, WriteSucceeded)`
tornava `list[Evento]`, e `mypy --strict` ha bocciato **dieci** asserzioni in un colpo:
`"Evento" has no attribute "durata_ms"`. A runtime sarebbero passate tutte. La correzione è un
parametro di tipo (`def _specie[E: Evento](...) -> list[E]`), ma la lezione sta nel verso: un
aiutante di prova che perde il tipo lo perde **dove le asserzioni sono più specifiche**, cioè dove
il controllo serviva di più, e lo perde in silenzio. **Nota 156.**

**Che cosa resta aperto.** La saturazione di `maxPoolSize` non è misurata e qui non può esserlo:
contro `InMemoryStore` non c'è nessun pool da saturare. `scrittori` è il gancio, e la misura è del
Task 16, dove la coda illimitata va guardata per la stessa ragione
([A-010, riserve](Sources.md#a-010)).
E c'è un avvertimento che vale la pena portarsi dietro: oggi la violazione del §6.3 è vista *per
quello che è* da **una sola** prova, quella sul thread; le altre cinque che falliscono insieme a lei
lo fanno per effetto collaterale, perché i conteggi vivono nel ciclo di drenaggio. Se i conteggi si
spostassero, resterebbe quella sola a difendere l'invariante.

---

## Task 6 — L'osservatore della topologia, e i due numeri del failover

**Che cosa chiedeva.** Un `TopologyWatcher` che, viste in ingresso alcune descrizioni di topologia,
produca la sequenza attesa di `ServerStateChanged` e `TopologyChanged`; il caso che conta è primario
→ nessun primario → primario **diverso**, provato con `FakeClock` in millisecondi. Poi i due numeri
che giustificano l'applicazione — durata dell'interruzione e scritture perse — calcolati **qui** e
non nella TUI, con valori attesi esatti e non tolleranze. Infine la regola del §6.2, «dopo 30 s senza
primario smetti di ritentare», che finora esisteva solo come frase nel design.

**Che cosa è stato scritto.** `application/topologia.py` e `tests/unit/test_topologia.py`:
`TopologyWatcher`, e due valori congelati che portano i numeri, `Interruzione` e `Bilancio`. Le prove
passano da **106 a 153**, `mypy --strict` verde su 28 file. Le scelte sono spiegate in
[07-topologia-failover-e-i-due-numeri.md](07-topologia-failover-e-i-due-numeri.md); qui c'è il
processo.

**Diversamente dal previsto — il nono evento, e una guardia che ha fatto il suo mestiere.**

Il Passo 3 chiedeva che la resa fosse **detta con un evento**. Nessuno degli otto del §6.3 sapeva
dirlo senza mentire, e aggiungerne uno faceva fallire
`test_gli_eventi_del_design_sono_otto_e_sono_quelli` — la guardia scritta al Task 3 proprio perché il
dominio non crescesse in silenzio. Ha funzionato come doveva: ha reso il costo visibile e ha
costretto a passare per un ADR. [ADR-0082](../../docs/Decision.md#adr-0082) porta gli eventi a
**nove** con `PrimaryWaitAbandoned`, e la guardia — rinominata — adesso ne conta nove.

Il che rende imprecisi, da oggi, il titolo e il corpo della voce del **Task 3** qui sopra, che
parlano di otto eventi. Restano come sono: erano esatti con le informazioni di allora, e questa è la
correzione prescritta dalla disciplina append-only.

**Diversamente dal previsto — due volte l'arnese ha mentito prima del codice.**

Ventun rotture deliberate sull'osservatore ([M-011](Sources.md#m-011)), e i primi due rapporti erano
falsi entrambi.

Il primo diceva *ventuno su ventuno catturate* senza aver eseguito una sola prova: era rimasta in
riga di comando un'opzione inesistente, `pytest` usciva con **4** — errore d'uso — e lo script
leggeva «diverso da zero» come «una prova ha fallito». Il repository conosceva già il codice 5,
«nessuna prova raccolta» ([M-005](Sources.md#m-005)); adesso conosce anche il 4. **Nota 157.**

Il secondo attribuiva a due rotture diverse la stessa prova fallita, che è un'impossibilità logica.
Python decide se ricompilare un modulo guardando **data di modifica in secondi e dimensione in byte**
del sorgente: due mutazioni della stessa lunghezza, scritte nello stesso secondo, condividono il
`.pyc`. Le rotture 5 e 6 producevano entrambe 16 036 byte, la 9 e la 10 entrambe 16 033.
**Nota 158.**

In tutti e due i casi il segnale d'allarme è stato lo stesso: **un rapporto troppo pulito**. Vale la
pena tenerlo, perché è l'unico che si accende quando lo strumento di verifica è quello rotto.

**Quattro guardie scoperte su ventuno, e una prova che guardava il risultato giusto.**

Al netto degli arnesi, la prima corsa onesta ha dato diciassette rosse e **quattro mute**. La più
istruttiva è la 4: togliendo `sorted` dall'elenco dei server, la prova che asserisce l'ordine per
indirizzo restava verde, perché in quella prova anche l'ordine di comparsa era già alfabetico.
Osservava il risultato giusto per il motivo sbagliato. La prova nuova elenca i server **al
contrario** nella descrizione di partenza. **Nota 159:** una guardia si prova solo con un caso in
cui, se non ci fosse, si vedrebbe.

**Un numero può sbagliare verso lo spettacolare.** La nota 155 diceva che uno zero inventato è la
peggiore risposta mancante, perché sembra una misura. Qui la stessa domanda ha avuto due risposte
opposte, e vanno tenute insieme. Un'interruzione già in corso al primo sguardo **non si misura**:
`durata_ms` resta `None`, perché il valore che si potrebbe scrivere sarebbe un minimo, e sbaglierebbe
verso il rassicurante. Un'interruzione chiusa **non si riapre** allo sguardo dopo: spostarne la fine
la allungherebbe a ogni giro, e sbaglierebbe verso lo spettacolare. Il secondo errore è più difficile
da notare, perché la slide ci guadagna. **Nota 160.**

**Che cosa resta aperto.** Questo osservatore **interroga**, non ascolta: la risoluzione della misura
è l'intervallo di campionamento, e l'errore sulla durata è al più un intervallo. Il valore
predefinito, 500 ms, non è misurato — è scelto. La misura vera arriva al Task 7, con `SdamBridge` e i
callback di PyMongo, che riferiscono il cambiamento quando accade. Nessun `ClusterInspector` reale
esiste ancora, e per il `TopologyWatcher` non c'è l'invariante di thread che il Task 5 ha dato al
generatore di carico: oggi lo si usa da un thread solo, ma nessuna prova lo dice.

## Task 7 — Il ponte SDAM: quattro ascoltatori, una coda

**Data:** 2026-09-03 · **Commit:** `feat: il ponte SDAM — il listener costruisce, deposita e ritorna`

Il primo modulo di `infrastructure/` che importa PyMongo davvero, e il primo punto in cui
l'applicazione smette di interrogare il cluster e comincia ad ascoltarlo. Il racconto per esteso è
in [08-il-ponte-sdam-e-i-thread-del-driver.md](08-il-ponte-sdam-e-i-thread-del-driver.md); qui c'è
quello che il piano non prevedeva.

**Quattro classi non sono una scelta di stile.** Il piano diceva «le quattro classi di listener del
§6.3», e la tentazione di farne una sola che le implementa tutte è forte: la coda sarebbe
naturalmente unica. Non si può. `ServerListener` e `TopologyListener` dichiarano gli stessi tre
metodi — `opened`, `closed`, `description_changed` — e il driver smista per `isinstance`. Una classe
che eredita da entrambi finirebbe in due elenchi, e il suo unico `description_changed` riceverebbe
due tipi di evento diversi sulla stessa firma. La separazione la fa il driver, gratis.

**I `Protocol` hanno pagato due volte, e la seconda non era prevista.** La prima è quella per cui
sono stati scritti: le prove costruiscono a mano gli oggetti che il driver passerebbe, e la
traduzione si verifica senza PyMongo vivo — quaranta prove in meno di un secondo. La seconda è che
`mypy --strict`, dovendo dimostrare che i metodi accettano un tipo **più largo** di quello della
classe base ereditata, verifica che le classi vere di PyMongo soddisfino i nostri `Protocol`. Il
controllo di compatibilità col driver arriva a ogni `make app-check`, senza che nessuno lo scriva.

Ed è servito subito. La prima stesura dichiarava `address: tuple[str, int]`; mypy ha rifiutato,
perché in PyMongo la porta è opzionale. Senza quel rifiuto, `indirizzo_di` avrebbe scritto
`mongo-1:None` in una riga della cronaca, e nessun doppio scritto a mano se ne sarebbe accorto —
perché chi scrive il doppio la porta ce la mette sempre. Non un crash evitato: **una stringa
sbagliata a schermo durante il talk**.

**La documentazione di PyMongo sbaglia un'unità, e sarebbe costata una tabella di zeri.** La
docstring di `ServerHeartbeatSucceededEvent.duration` dice «in microseconds»; il valore che ci
arriva è una differenza di `time.monotonic()`, cioè **secondi** ([M-012](Sources.md#m-012)).
`CommandSucceededEvent.duration_micros`, invece, è davvero in microsecondi. Credere alla docstring
avrebbe prodotto battiti nell'ordine di 10⁻⁶ ms, che nel riepilogo dei percentili sarebbero comparsi
come zeri: la **nota 155** fatta scattare da una riga di documentazione altrui. È il caso che il
patto di lettura di `app/docs` prevede — dove la misura e la fonte non concordano, la riserva si
scrive — e stavolta è capitato sul serio.

**Un valore nuovo nel dominio, e la ragione per cui non è un ADR.** `RuoloServer.ALTRO`. Il driver
conosce `RSOther`, `RSGhost`, `LoadBalancer`, e mandarli tutti su `SCONOSCIUTO` è una traduzione
sbagliata proprio nel momento della demo: un membro che riparte sta qualche secondo in `RECOVERING`,
il driver lo chiama `RSOther`, e la sala sta guardando quella riga. «Sconosciuto» direbbe *il client
non ha capito*, mentre il client ha capito benissimo. I tre stati dell'assenza sono ora tre cose
distinte: `SCONOSCIUTO` è l'assenza di un'osservazione, `IRRAGGIUNGIBILE` è un'osservazione, `ALTRO`
è il contrario di entrambi. Nessun ADR perché `RuoloServer` non è enumerato nel design, a differenza
dei nove eventi — se lo fosse stato, questa riga sarebbe costata una decisione come è costata a
`PrimaryWaitAbandoned`.

**Il driver fa quello che ADR-0019 impone a noi.** Misurando da quale thread arrivano i callback si
scopre che server e topologia **non** vengono consegnati dal codice che scopre il cambiamento: quel
codice fa `self._events.put(...)`, e un thread di nome `pymongo_events_thread` drena e chiama i
listener ([M-014](Sources.md#m-014)). Battiti e comandi invece arrivano davvero sul thread del
monitor e su quello applicativo. Metà dei listener di PyMongo passano quindi dalla stessa forma —
coda più drenatore — che ADR-0019 impone all'applicazione, e nessuna pagina di documentazione lo
dice. La regola non cambia: quel thread è uno solo, e un callback lento lì accoda anche l'evento che
annuncia il primario nuovo.

**La soglia della prova cronometrata è stata misurata prima di essere scritta.** Il callback onesto
costa 1,3 µs contro 0,45 µs di un `put_nowait` nudo: 2,9 volte, stabile su cinque ripetizioni. Una
tabella di Rich dentro il callback porta il rapporto a 883, cioè 386 µs — a ottocento comandi al
secondo sono 0,31 secondi di CPU per ogni secondo di orologio, rubati al thread del driver. La
soglia sta a **10** ([M-013](Sources.md#m-013)). Va detto che non prende una `f-string`, che pure il
codice vieta: a 5,5 resterebbe sotto. È una rinuncia dichiarata, perché una soglia a 4 fallirebbe su
una macchina carica, e una prova che fallisce a caso prima o poi viene disattivata.

**Ventotto rotture, ventisette rosse, e una che non era una rottura.** Nessuna prova nuova è stata
necessaria: il contrario di [M-011](Sources.md#m-011), dove quattro guardie su ventuno mancavano. La
differenza è che qui le prove sono state scritte contro un contratto già **misurato**, non contro
un'idea del comportamento.

La quindicesima resta verde, e la prima ipotesi — manca una guardia — è sbagliata. Il driver
pubblica quel cambio in un punto solo, e ricava la descrizione vecchia indicizzando per l'indirizzo
di quella nuova: i due lati portano sempre lo stesso indirizzo, per costruzione. Non sono due
letture di cui una giusta, sono la stessa lettura scritta in due modi. Inventare una prova con due
indirizzi diversi aggiungerebbe copertura senza aggiungere verità, perché difenderebbe un caso che
il driver non può produrre; la cura è verificare l'invariante alla fonte e scriverlo dove il codice
lo usa. **Nota 161:** prima di concludere che manca una guardia, va escluso che manchi la differenza.

**La nota 153 è arrivata al primo colpo.** La rottura «`drena` guarda ma non svuota», nella sua prima
forma, era un ciclo infinito: la batteria si è piantata dopo sette minuti senza dire niente. Da lì
un limite di 90 secondi per corsa e un esito `APPESO` che ha un nome suo. Le protezioni delle note
157–159 erano già nello script fin dall'inizio, ed è la prima volta che una batteria di rotture
parte con gli arnesi già a posto.

**Che cosa resta aperto.** Nessuna di queste misure ha parlato con un cluster: i client delle prove
nascono con `connect=False`, e i due eventi che contano per il talk — un battito che fallisce mentre
il primario cade, un `ServerStateChanged` verso `PRIMARIO` su un altro nodo — nessuno li ha visti
arrivare. È il Task 8. Resta aperto anche il buco dichiarato in [M-015](Sources.md#m-015): PyMongo
ingoia le eccezioni dei listener stampandole su `stderr`, e sotto un `Live` di Rich quelle righe non
si vedono. Un ponte rotto si presenterebbe come una cronaca che smette di aggiornarsi. La sede in
cui si può chiudere è il Task 11.

---

---

## Task 8 — Gli adattatori veri, e il contratto che li tiene onesti

**Data:** 2026-09-03 · **Commit:** `feat: gli adattatori pymongo, provati contro gli stack del repository`

Il primo task in cui l'applicazione parla con un MongoDB. `PymongoStore`, `PymongoInspector`, il
`DataGenerator` deterministico, e una seconda suite che accende gli stack di questo repository e ci
gira contro. Il racconto per esteso è in
[09-adattatori-veri-e-contratto-condiviso.md](09-adattatori-veri-e-contratto-condiviso.md); qui c'è
quello che il piano non prevedeva.

**Il contratto ha trovato il primo bugiardo prima che l'adattatore esistesse.** Il Passo 4 chiedeva
di far girare le prove del Task 4 anche contro l'originale, e l'ordine naturale sarebbe stato:
scrivo l'adattatore, poi condivido le prove. È stato fatto al contrario — prima il file condiviso,
eseguito **solo** contro `InMemoryStore` — e la prima esecuzione ha dato `1 failed, 10 passed`. Il
doppio rispondeva `[{"quanti": 0}]` a un `$count` su zero documenti, e MongoDB non risponde niente
([M-017](Sources.md#m-017)). Un difetto che esisteva da quattro task, invisibile perché nessuna
prova aveva mai chiesto quel caso, e trovato da un file che non conteneva ancora una riga di
integrazione. **Estrarre il contratto è già una prova**, indipendentemente da dove poi lo si esegue.

**Il secondo bugiardo era l'originale, e la fonte inverte l'ovvio.** `find_page(quanti=0)`
restituisce la lista vuota sul doppio e la collezione intera contro MongoDB, perché «A `limit()`
value of 0 (i.e. `.limit(0)`) is equivalent to setting no limit» ([A-011](Sources.md#a-011)). La
guardia è stata scritta dopo aver visto la prova fallire ([M-022](Sources.md#m-022)), che è la
**nota 159** applicata al caso più facile: quando esiste già una seconda implementazione che si
comporta bene, il caso in cui la guardia manca non va costruito, c'è.

**`ordered=False` è stata la prima scelta di prestazioni rifiutata da una misura.** Ogni guida al
caricamento massivo la consiglia, e stava per essere adottata per abitudine. Misurata su ventimila
documenti per configurazione in tre giri alternati, la differenza non c'è: mediane fra 2,48 e
2,70 ms da entrambe le parti, e al terzo giro l'ordinato è più veloce ([M-021](Sources.md#m-021)).
Resta il predefinito, e la **nota 162** ha funzionato su qualcosa che nessuno avrebbe pensato di
verificare perché «si sa».

**Due trappole della connessione che nessuna documentazione dichiara.** La prima: `replicaSet=rs0`
dall'host contro lo stack 02 sano dà `ReplicaSetNoPrimary` dopo 4,2 secondi, con tutti e tre i
membri irrisolvibili — perché il set si annuncia con i nomi di servizio Compose
([M-019](Sources.md#m-019)). È indistinguibile da un primario caduto davvero, cioè dalla diagnosi
che il Blocco 2 esiste per mostrare. La seconda: `tz_aware` è predefinito a `False`, e il difetto
che ne segue non fallisce — le date tornano ingenue, il confronto riesce lo stesso, e lo sbaglio si
vede come un orario storto sullo schermo. È l'unica cosa del client su cui `PymongoStore` si
permette di avere voce, e la guardia sta nel costruttore.

**La credenziale è stata cercata invece che dedotta.** Il punto aperto diceva «come le prove di
integrazione ricevono la credenziale senza violare ADR-0054». Passata come argomento, non compare né
nel messaggio di `ServerSelectionTimeoutError`, né in quello di `OperationFailure`, né nel `repr` del
client ([M-018](Sources.md#m-018)). Il posto scoperto non era PyMongo: era il `dataclass` delle
prove, il cui `repr` sarebbe finito in ogni traceback — da lì `field(repr=False)`.

**Una regola del repository ostacolava una cosa legittima, e la sede mancava.** Le prove accendono
gli stack, `make up-02` legge il `.env`, e [ADR-0056](../../docs/Decision.md#adr-0056) dice che quei
file vivono nel checkout principale. Copiarli avrebbe creato un segreto che invecchia in silenzio.
Invece di aggirare la regola si è aperta la sede: [ADR-0083](../../docs/Decision.md#adr-0083), il
collegamento simbolico — il file resta uno, il versionamento non lo vede.

**Il manuale non diceva quello che stavo per fargli dire.** La prima stesura di `_chunk_per_shard`
spiegava che «dalla 5.0 `config.chunks` non contiene più il campo `ns`». La pagina del manuale non
lo afferma da nessuna parte e non nomina la 5.0 a questo proposito: prescrive l'unione per `uuid`
([A-013](Sources.md#a-013)) e basta. La docstring è stata riscritta separando le due cose — il Tip
è del manuale, l'assenza di `ns` è una misura sul 7.0.40 di questo repository
([M-020](Sources.md#m-020)). La differenza fra le due formulazioni è la differenza fra una riserva
onesta e una leggenda tramandata.

**Il commento sul `pyproject.toml` prometteva più di quanto `--strict-markers` mantenga.** Diceva
che protegge dagli errori di battitura nei marcatori. Verificato: `@pytest.mark.stack3` in un
decoratore è intercettato, ma `pytest -m stack3` sulla riga di comando deseleziona trentatré prove
ed esce zero, senza una parola. Il commento adesso dice entrambe le cose, compreso il buco che
resta.

**Numeri.** 214 prove unitarie in 0,79 s, 33 di integrazione in 1,46 s su tre stack accesi,
`mypy --strict` verde su 39 file. Da stack spento a diciannove prove verdi in 8,1 secondi, perché
`sveglia()` esegue `make up-01` da sé — che è [ADR-0020](../../docs/Decision.md#adr-0020) applicato:
si prova l'artefatto che il pubblico eseguirà, non un facsimile.

## Task 9 — Un processo esterno, e il verdetto che manca

**Deciso:** `SubprocessBackup` attacca la porta `BackupTool` a `mongodump` e `mongorestore`. È il
primo adattatore che non parla con una libreria ma con un **processo**, e le quattro differenze
vengono tutte da lì: la credenziale attraversa un confine di sistema operativo, l'avanzamento è
testo da riconoscere, l'errore è un intero, e il processo sopravvive a chi lo ha lanciato. Il
capitolo è [10](10-processi-esterni-e-il-verdetto-che-manca.md).

**Il piano aveva ragione sulla regola e torto sul motivo.** Il Passo 2 chiedeva la lista di
argomenti al posto della stringa di shell «perché una stringa di shell fa comparire la password
nella tabella dei processi». Con `-p <valore>` come elemento della lista — nessuna shell coinvolta —
`ps -eo args` dentro il container lo mostra per intero, sedici campioni su sedici
([M-025](Sources.md#m-025)). La tabella dei processi legge `argv`, e ad `argv` non importa da dove
è arrivato. Quello che funziona è omettere `-p`: gli strumenti chiedono la password e la leggono
dallo `stdin` anche quando lo `stdin` non è un terminale ([M-023](Sources.md#m-023)). La lista resta
la scelta giusta per la ragione che il piano non nomina — senza shell nessuno interpreta uno spazio,
un apice o un `$` dentro una password o dentro un percorso.

**Il comando arriva dal costruttore.** `("docker", "exec", "-i", "mongo-rs-1", "mongodump")` dalle
prove sull'host, `("mongodump",)` dal container al Task 12. Se la politica di esecuzione stesse
nell'adattatore, l'applicazione containerizzata di
[ADR-0012](../../docs/Decision.md#adr-0012) si porterebbe dietro una dipendenza dal socket Docker
per fare una cosa che dal suo container sa già fare da sé. È la stessa scelta che fa arrivare a
`PymongoStore` una `Collection` già fatta.

**`mongorestore` ha perso cinquantamila documenti ed è uscito zero.** Un restore ripetuto sulla
stessa destinazione ricade su `_id` che esistono già, dichiara `0 document(s) restored successfully.
50000 document(s) failed to restore.` e restituisce **0** al sistema operativo
([M-024](Sources.md#m-024)). Chi controlla il processo nel modo in cui si controlla un processo
riceve «riuscito». Da qui [ADR-0084](../../docs/Decision.md#adr-0084), che estende
[ADR-0077](../../docs/Decision.md#adr-0077): la regola valeva per gli avvisi che scriviamo noi,
l'aggiunta è che quando lo strumento di qualcun altro commette lo stesso errore, l'adattatore che
lo incapsula è il posto in cui si ripara. L'adattatore solleva `RestoreIncompleto` con i due
conteggi.

**La guardia non è stata progettata: è stata scoperta dal codice che la contiene.** Le prime due
prove di integrazione sul restore davano per idempotente un restore ripetuto — c'era scritto nella
docstring di una di loro, come premessa ovvia. Eseguite, `RestoreIncompleto` è stata sollevata, e
l'assunzione della prova era la parte sbagliata. Le prove sono state riscritte su destinazioni
fresche e il caso è diventato una prova sua.

**`dump` non è una funzione generatrice, e la porta lo pretendeva dal Task 4.** Con un `yield`
dentro, chiamare `dump` non eseguirebbe niente e `mongodump` partirebbe al primo `next()`: lo stesso
codice sarebbe corretto o sbagliato con la stessa forma, e l'errore arriverebbe dentro il ciclo che
disegna la schermata invece che dove il dump è stato chiesto. `dump` è una funzione normale che
*ritorna* l'iteratore di un'altra, e la prova pretende `FileNotFoundError` senza iterare niente.

**Le prove unitarie lanciano processi veri.** Nessun `Mock` di `subprocess`: metà di ciò che
l'adattatore garantisce riguarda il confine col sistema operativo, cioè esattamente la parte che un
mock sostituirebbe con la propria opinione. Al posto di `mongodump` c'è un programma Python di sei
righe che scrive pid e argomenti in un diario, e le righe che stampa su `stderr` sono **le righe
misurate**. Il pid nel diario è ciò che permette alla prova sulla chiusura di chiedere al sistema
operativo se il processo è morto, invece di chiedere a un mock se ha ricevuto una chiamata.

**Sei mutazioni, e la sesta non la vedeva nessuno.** L'adattatore è stato rotto una volta alla volta
— password in `argv`, sommario ridotto ad avviso, `dump` resa generatrice, `kill` tolto, codice
d'uscita ignorato, base 1024 cambiata in 1000. Le prime cinque sono diventate rosse subito; la base
è rimasta verde, perché l'unica prova sulle barre usava il formato senza unità di `mongodump`. Da lì
due prove nuove sulle barre del restore, una delle quali giudica contro la dimensione vera del file
letta con `stat` ([M-026](Sources.md#m-026)) invece che contro un `1024**2` riscritto nella prova.

**Numeri.** 243 prove unitarie in circa un secondo, 43 di integrazione, `mypy --strict` verde su 42
file. La suite di integrazione è passata da 1,46 s a **28–40 s** — due esecuzioni consecutive hanno
dato 39,6 s e 28,4 s, e la variabilità è quella di due strumenti che leggono e scrivono su disco
dentro un container: dieci di quelle prove eseguono `mongodump` e
`mongorestore` veri su centomila documenti, ed è il prezzo di
[ADR-0020](../../docs/Decision.md#adr-0020) applicato a uno strumento lento.

---

## Task 10 — Tre rese dello stesso flusso, e una promessa che era falsa

**Fatto il 3 settembre 2026.** Il capitolo che ne esce è
[11-tre-rese-e-un-solo-thread-che-disegna.md](11-tre-rese-e-un-solo-thread-che-disegna.md).

Il piano chiedeva tre file — `rich_tui.py`, `plain.py`, `null.py` — e ne sono usciti cinque. I due
in più, `righe.py` e `scena.py`, esistono per una ragione sola: il Passo 4 vieta di provare
`RichTui`, e un divieto di provare qualcosa si onora spostando altrove ciò che va provato, non
rinunciando a provarlo. Tutto ciò che nella presentazione è una **decisione** — la riga di un
evento, il budget di sala, la coda, i conteggi, la cronaca, che cosa fare quando i server sono
troppi — sta nei due moduli che non conoscono Rich e hanno le loro prove. `rich_tui.py` resta un
ciclo di cinque righe e un disegno.

### La scoperta che ha cambiato un ADR

[ADR-0019](../../docs/Decision.md#adr-0019) prometteva «un solo thread tocca `Live`», e la
prometteva perché la documentazione di Rich non nomina mai i thread
([S-018](../../docs/Sources.md#s-018)): di fronte a una lacuna il progetto aveva cambiato disegno
invece di indovinare. Guardando dentro `rich/live.py` si è scoperto che la lacuna nascondeva una
risposta, e la risposta era «due»: con le impostazioni predefinite `Live.start()` avvia un
`_RefreshThread` demone che chiama `refresh()` per conto suo ([M-027](Sources.md#m-027)).

Non sarebbe stato scorretto — dentro `Live` c'è un `RLock` — ma sarebbe stato corretto per una
ragione che il progetto non conosceva. Da lì `auto_refresh=False`, e
[ADR-0085](../../docs/Decision.md#adr-0085), che mantiene la decisione di ADR-0019 e ne corregge il
presupposto. È la **nota di metodo 173**: un silenzio ha due letture, «non succede» e «non
è documentato», e la seconda è quasi sempre quella giusta. Il prezzo, misurato: `refresh_per_second` diventa inerte, e quindi non si passa a
`Live`; il numero vive nel periodo del ciclo, dove agisce davvero. È una deviazione dalla lettera
del Passo 1, presa per onorarne l'intento.

**La prima sonda ha risposto di no alla domanda giusta.** Contava i thread *dopo* `live.stop()`, e
ne trovava zero — vero, e inutile, perché è `stop()` a chiudere il thread che si cercava. La
domanda «esiste un thread in più?» va posta nel momento in cui la risposta conta: **nota 176**.

### Due numeri sbagliati, scoperti in due modi diversi

Il primo era un **segnaposto**. La docstring che giustifica `RITMO_PREDEFINITO = 10.0` è stata
scritta prima della misura, e diceva «0,86 ms misurati» con una citazione a una fonte che non
esisteva ancora. È il modo in cui un repository con una regola sulle fonti la viola: non scrivendo
un numero senza fonte, ma scrivendo un numero **con** una fonte che si ha intenzione di produrre
dopo. Un numero assente si nota; un numero inventato accanto a un `M-0NN` ben formato no —
**nota 174**, e la regola pratica è che la citazione si scrive dopo la fonte, mai prima.

Il secondo era un **errore di modello**, ed è più interessante. `SERVER_MOSTRATI = 8` era
giustificato con «due shard da due membri, tre config server, un `mongos`»: una frase che conta i
container dello stack 03 — sbagliando anche quelli, perché gli shard hanno tre membri — mentre
l'intestazione della TUI mostra la `TopologyDescription` che il driver espone. Un client di un
`mongos` vede il `mongos`. Misurato sui tre stack accesi, il caso peggiore è **tre**
([M-029](Sources.md#m-029)), e le cinque righe di troppo le pagava la cronaca, che passa da sedici
a ventuno. È la **nota 175**: un numero nudo invita a chiedere da dove viene, un numero con una
derivazione plausibile scritta accanto chiude la domanda.

Corretto il layout, la misura del costo di disegno è stata rifatta: 0,76 ms invece di 1,33
([M-028](Sources.md#m-028)). La prima correzione ha aggiustato il numero, la seconda la cosa
misurata.

Il numero resta però quello del lab, e fuori dal lab un replica set a cinque membri esiste. Per
questo `server_da_mostrare` non taglia in silenzio ma scrive «… e altri 3»: **nota 178** — un
elenco troncato senza dirlo non è una schermata incompleta, è una schermata che afferma il falso,
perché si legge come un cluster più piccolo di quello che è.

### Il giro di rotture, e che cosa ha insegnato sul divieto

Undici mutazioni. Nove scoperte subito; due sopravvissute, tutte e due in `rich_tui.py`:
`auto_refresh=True`, cioè la riga che tiene in piedi ADR-0019, e l'ultimo `aggiorna()` dopo il
ciclo, cioè l'evento che chiude la scena.

Sopravvivevano perché il Passo 4 era stato letto come «di `RichTui` non si prova nulla». Ma nessuna
delle due è disegno: la prima è *quanti thread esistono*, la seconda è *se la coda è vuota quando
il ciclo finisce*, e si osservano entrambe senza guardare un pixel — **nota 177**, un divieto
di provare si onora spostando ciò che va provato. Con le due prove aggiunte,
undici su undici. Le uniche due righe di quel modulo che il resto del progetto **cita** — una in un
ADR, una in ogni scenario — erano anche le uniche senza guardia.

### Numeri

| | Prima | Dopo |
|---|---|---|
| Prove unitarie | 243 | **280** |
| Prove di integrazione | 43 (28–40 s) | 43 (29,6 s) — invariate |
| File controllati da mypy | 42 | **48** |
| Prove degli strumenti | 143 | 143 — invariate |

Tre file di prova sono stati toccati fuori dall'elenco del piano — `tests/aiutanti.py`,
`test_dominio.py`, `test_scheletro.py` — per spostare `moduli_importati`, `estranei` e
`sottoclassi_di_evento` in una sede condivisa: adesso servono a due guardie, e una funzione
duplicata in due file diventa due funzioni diverse alla prima modifica.

---

## Task 11 — La radice di composizione, e tre difetti che solo l'esecuzione poteva mostrare

**Fatto il 3 settembre 2026.** Il capitolo che ne esce è
[12-la-radice-di-composizione-e-la-prima-esecuzione-vera.md](12-la-radice-di-composizione-e-la-prima-esecuzione-vera.md).

`cli.py` è l'unico punto dell'applicazione che conosce le classi concrete: costruisce
`PymongoStore`, `PymongoInspector`, `SdamBridge`, `SystemClock` e le tre rese, e le inietta in
componenti che continuano a vedere soltanto porte. Con lui arrivano i tre comandi diretti del §6.4
— `stats`, `watch`, `workload` — la mappa fra `--target` e stack in un posto solo, e `--sink` come
opzione invece che come condizione sparsa in tre punti.

I file scritti sono più di quelli che il piano elenca, e l'allargamento è dichiarato:
`infrastructure/orologio.py` (la porta `Clock` non aveva un'implementazione di produzione),
`infrastructure/bersagli.py` (la mappa), `infrastructure/zavorra.py` (`--doc-size`),
`presentation/rapporto.py` (l'uscita di `stats`), `--readers` e `--duration` in
`application/workload.py`, `[project.scripts]` in `app/pyproject.toml`, tre target nel `Makefile`.
Le quattro opzioni di `workload` sono state implementate tutte perché il Task 16 misurerà **quella**
riga di comando del §6.4, e una riga misurata che non si può digitare non serve a niente.

### Poi si è eseguito davvero, e due comandi su tre erano sbagliati

Con 425 prove unitarie verdi, 43 d'integrazione e `mypy --strict` senza rilievi, lo stack 01 è stato
acceso e i tre comandi lanciati per la prima volta contro un MongoDB vero. Nessuno dei difetti
trovati era una svista: tutti vivevano nella **giuntura** fra componenti che, presi uno per uno,
erano corretti e provati.

**`workload` scriveva nella collezione seminata.** `38 scritture · 0 confermate · 38 fallite`, e
uscita zero. Ogni inserimento tornava
`E11000 duplicate key error collection: lab.ordini index: _id_ dup key: { _id: 0 }`
([M-032](Sources.md#m-032)): `DataGenerator` numera da zero, il seed occupa gli `_id` da 0 a 49 999.
La forma del guasto conta più del guasto — la cronaca scorreva, 4 833 letture su 4 833 riuscivano, e
dal fondo della sala era una demo che funziona. `InMemoryStore` accetta gli `_id` che gli si danno e
non ha un seed, quindi nessuna prova unitaria poteva vederlo, e nessuna doveva. Che il carico
dovesse scrivere altrove era già scritto in `generatore.py` e in `tools/reset-demo.sh`: a sbagliare
era il cablaggio. Correzione: una collezione per corsa, `lab.carico-<AAAAMMGG-hhmmss>`, e il comando
che dice dove scrive prima di cominciare ([ADR-0088](../../docs/Decision.md#adr-0088)). Rifatta la
corsa: **8 245 scritture, 8 245 confermate, 0 fallite.**

**`watch` raccontava ogni transizione due volte.** Il driver è stato messo alla prova nudo prima di
accusarlo, e la emette **una volta sola** ([M-033](Sources.md#m-033)). Il doppione era nostro:
`SdamBridge` e `TopologyWatcher` guardano la stessa struttura, uno spinto e uno tirato. Correzione:
in `watch` resta il ponte, come prescrive il §6.3; la sentinella conserva la misura
dell'**interruzione** per lo scenario di failover del Task 13
([ADR-0089](../../docs/Decision.md#adr-0089)). Deduplicare nel sink era la scorciatoia, ed è stata
scartata: due transizioni identiche e ravvicinate sono anche la firma di un membro che *flappa*,
cioè la cosa che una demo di failover deve mostrare.

**`stats` diceva `sconosciuto` di un server sano.** `client.topology_description` riferisce ciò che
il client crede *in questo istante*, e su un client appena costruito il primo battito non è ancora
tornato ([M-031](Sources.md#m-031)). Correzione nell'ordine di lettura di `rapporto()`:
`server_status()` per primo, perché esegue un comando e costringe il driver a guardare; `topology()`
per ultimo. L'ordine di lettura è l'opposto di quello di stampa, e siccome è il genere di dettaglio
che un riordino per leggibilità cancella, c'è una prova che conta l'ordine delle chiamate —
validata con una mutazione deliberata.

### L'orologio, che era una porta senza casa

`Clock` esisteva come porta e come `FakeClock`; in produzione nessuno. L'implementazione ovvia —
`datetime.now().astimezone()` — è sbagliata per l'uso che questa applicazione ne fa, perché la porta
serve a **datare** e a **misurare**, e l'orologio da parete dichiara `monotonic=False`
([M-030](Sources.md#m-030)). Un salto all'indietro non solleva: produce una latenza negativa che
entra nei percentili. `SystemClock` legge il muro una volta sola e da lì somma il contatore
monotono, nel fuso locale e non in UTC ([ADR-0086](../../docs/Decision.md#adr-0086)).

### Numeri

| | Prima | Dopo |
|---|---|---|
| Prove unitarie | 280 | **425** |
| Prove di integrazione | 43 (29,6 s) | 43 (28,0 s) — invariate |
| File controllati da mypy | 48 | **57** |
| Prove degli strumenti | 143 | 143 — invariate |
| ADR del repository | 85 | **89** |
| Misure nel registro dell'app | 29 | **34** |

Le prove della CLI verificano il **cablaggio** e non il comportamento dei componenti, già provato
altrove: che `--sink plain` produca un `PlainSink`, che un `--target` sbagliato esca con 2, che il
carico chieda una collezione che comincia per `carico-`, che il cliente venga chiuso. Girano offline
in millisecondi, perché `cabla()` non apre niente.

---

## Task 12 — L'applicazione in container, e la riserva di ADR-0012 chiusa due volte

**Fatto il 3 settembre 2026.** Il capitolo che ne esce è
[13-il-container-sulla-rete-e-la-scoperta-che-si-vede.md](13-il-container-sulla-rete-e-la-scoperta-che-si-vede.md).

Fino a ieri `mongolab` guardava gli stack da fuori, attraverso una porta pubblicata, e da fuori la
cosa che il talk deve mostrare **non si vede**: un replica set con tre membri sani si legge
`ReplicaSetNoPrimary`, e per farlo funzionare bisogna spegnere la scoperta. Da oggi c'è
un'immagine, un servizio `app` in ognuno dei tre `compose.yaml` e una variabile d'ambiente che dice
da che parte si sta.

Il perimetro è quello del piano: `Dockerfile` su `python:3.13-slim`, sorgente in bind mount,
`directConnection=true` solo per lo stack 01, l'immagine nel controllo del preflight,
`make stack-check` verde. Quello che il piano **non** poteva prevedere è che il Passo 2 — «verificare
che la scoperta funzioni davvero» — si sarebbe chiuso in due modi indipendenti invece che in uno.

### La riserva di ADR-0012, chiusa leggendo e chiusa misurando

[ADR-0012](../../docs/Decision.md#adr-0012) aveva dichiarato che la documentazione di PyMongo non
afferma che il driver usi gli host memorizzati nella configurazione del set, e che per affermarlo
bisognava mostrarlo in demo. Entrambe le cose sono successe.

**Leggendo:** la frase esiste, ma non nel manuale di PyMongo — sta nella specifica *Server Discovery
And Monitoring* di `mongodb/specifications` ([A-016](Sources.md#a-016)), che tutti i driver
ufficiali implementano, ed è normativa: «While no known primary, client MUST **add** servers
non-primaries' host lists, but MUST NOT remove». La stessa specifica definisce la *seed list* come
«server addresses provided client in initial configuration», cioè da dove si parte e non dove si
arriva. La riserva era corretta e cercava la risposta un livello sotto a dove stava.

**Misurando:** un seme solo, e non il primario. Con i tre semi della configurazione di produzione la
dimostrazione sarebbe stata circolare; con `mongo-rs-2:27017` da solo, il client ha trovato tre
membri e ha scritto su `mongo-rs-1`, un nome che nessuno gli aveva dato
([M-036](Sources.md#m-036)). La prova che la rende ripetibile è
`test_un_seme_solo_basta_a_trovare_tutti_e_tre`, e usa `--entrypoint python` per non toccare la
configurazione vera.

### Quattro decisioni, e una che ha dovuto correggere sé stessa

[ADR-0090](../../docs/Decision.md#adr-0090) dà a ogni bersaglio due `Vista` — semi,
`directConnection`, nome del set — e lascia scegliere all'ambiente con
`MONGOLAB_PUNTO_DI_VISTA`. Un tipo solo e non tre campi, perché `directConnection=True` con più di
un seme è un `ConfigurationError` alla costruzione: tre campi permettono di scriverlo.

[ADR-0091](../../docs/Decision.md#adr-0091) mette il servizio dentro i tre stack sotto il profilo
`strumenti`, invece che in un quarto file che si attacchi alle reti altrui come esterne — il cui
nome dipende dalla cartella da cui si esegue.

[ADR-0092](../../docs/Decision.md#adr-0092) dà al `Makefile` la variabile `DOVE`, predefinita a
`rete`, perché il modo sbagliato qui **non fallisce**: stampa `topologia singola` su un replica set
sanissimo. Un predefinito che sbaglia in silenzio è una trappola.

[ADR-0093](../../docs/Decision.md#adr-0093) è quella che ha dovuto correggersi. La regola —
un servizio che dichiara `build:` si giudica sulle righe `FROM` del suo Dockerfile — è rimasta;
la sua motivazione no. Era argomentata su «un'immagine costruita in locale non ha un digest», che
suona ovvio ed è falso: con l'archivio immagini di containerd l'`Id` **è** il digest del manifesto
anche per un'immagine mai pubblicata ([M-037](Sources.md#m-037)). Il punto vero regge lo stesso —
quel digest nessun registro l'ha mai servito e cambia a ogni ricostruzione — ma la premessa
sbagliata era già scritta in cinque posti quando la misura l'ha smentita. Con il vecchio archivio a
grafo sarebbe stata perfino vera, per caso.

### Che cosa si è rotto, e che cosa non si è chiuso

Un difetto, e di un genere che nessuna prova unitaria poteva vedere: `mongo-standalone:27017` è
lungo **esattamente** ventidue caratteri, quanto la colonna con cui `_riga_server` impaginava gli
indirizzi, e l'indirizzo finiva incollato al ruolo ([M-038](Sources.md#m-038)). Era latente da tre
capitoli con ventuno prove verdi: a scoprirlo è stato un dato nuovo, non una svista. La larghezza
adesso si calcola sul più lungo della fotografia, con ventidue come minimo.

Una previsione, invece, non è stata onorata, e conviene dirlo prima di segnarla chiusa. Il registro
elencava fra i punti aperti che dal container non ci sarebbe più stato nessun `docker exec` in mezzo
al dump. L'immagine però contiene l'interprete e `mongolab`, non gli strumenti da riga di comando di
MongoDB ([M-039](Sources.md#m-039)): `mongodump` lì dentro non c'è. Oggi non fa danno — nessun
comando della CLI collega la porta `BackupTool` — e la scelta fra installarli e restare su
`docker exec` è del Task 14.

Un dettaglio di metodo che vale per tutte le guardie nuove: **le cinque prove aggiunte a
`tools/tests/test_coerenza_repo.py` passavano alla prima esecuzione**, perché sorvegliano una
configurazione già giusta. Ognuna è stata mutata — si perturba il file, si verifica che la guardia
scatti con un messaggio leggibile, si ripristina — e la prima delle cinque, così, ha trovato un
difetto in sé stessa: traducevo in Python il `sed` del preflight con `[^ ]*`, che in Python
attraversa gli a capo mentre `sed` lavora una riga per volta.

### Numeri

| | Prima | Dopo |
|---|---|---|
| Prove unitarie | 425 | **462** |
| Prove di integrazione | 43 (28,0 s) | **47** (41,2 s) |
| File controllati da mypy | 57 | **58** |
| Prove degli strumenti | 143 | **166** |
| ADR del repository | 89 | **93** |
| Fonti esterne nel registro dell'app | 15 | **16** |
| Misure nel registro dell'app | 34 | **39** |

`make stack-check` dice «Stack conformi: 3.» e `tools/preflight.sh` chiude con «Superati: 9 ·
Avvisi: 1 · Errori: 0 · Pronto.», dove il nono superato è l'immagine dell'applicazione in cache.

## Task 13 — La scena centrale, e la sesta porta nata da un'impossibilità

**Fatto il 4 settembre 2026.** Il capitolo che ne esce è
[14-la-scena-del-failover-e-i-due-numeri.md](14-la-scena-del-failover-e-i-due-numeri.md).

È l'Atto II del Blocco 2, cinque minuti, e la ragione per cui questa applicazione esiste. Il
piano lo scriveva in sei passi e li ha ottenuti tutti; quello che non poteva prevedere è che il
Passo 2 avrebbe smentito il Passo 2, e che la scena, eseguita per la prima volta, si sarebbe
rivelata **impossibile per un processo solo**.

### L'impossibilità, e la porta che ne è uscita

La cronaca dell'elezione esiste solo se il client fa scoperta, e la scoperta funziona solo da
dentro la rete Compose — è tutto il Task 12. Il guasto è un `docker compose kill`, e vuole il
socket del demone, che il container dell'applicazione **non ha** per una scelta deliberata del
Task 12. Dall'host, per giunta, il primario si chiama `localhost:27021`: un indirizzo che non è
il nome di nessun servizio che si possa fermare.

Da qui la sesta porta, `Regia`, con due adattatori che la implementano in modi opposti
([ADR-0095](../../docs/Decision.md#adr-0095)): `RegiaCompose` **esegue** e vive sull'host,
`RegiaAnnunciata` **annuncia** la riga esatta e si blocca finché un umano non l'ha eseguita. Il
frasario è un dato separato dall'esecuzione proprio perché chi annuncia deve poter comporre una
riga senza avere il diritto di lanciarla.

La conseguenza va portata al PO prima delle prove generali: **la scena dal vivo richiede due
terminali.** In cambio, la riga da incollare non si inventa a mano sotto pressione.

### Il piano diceva `stop`, e le slide dicevano un altro numero

Il Passo 2 nomina alla lettera `docker compose stop`. Eseguito, `stop` manda `SIGTERM`, e `mongod`
cede il ruolo con ordine: [V-029](../../docs/Sources.md#v-029) misura quella strada in 574, 480 e
486 ms, **senza elezione da raccontare**. Con `docker kill` sono 9 812, 10 619 e 10 943 ms, che
sono i numeri già sulle slide.

Le slide riportano una misura fatta, il piano ha una svista, e
[ADR-0097](../../docs/Decision.md#adr-0097) la corregge: il guasto predefinito è `kill -s
SIGKILL`. `ARRESTO_ORDINATO = ("stop",)` resta documentato e configurabile, perché il confronto è
il pezzo di didattica migliore dei due — «spegnere bene» è venti volte più rapido di «staccare la
spina», e va contro l'intuizione di tutti.

### Due difetti trovati eseguendo, e nessuno dei due visibile alle prove unitarie

**Guardare non è aspettare.** Contro un replica set sanissimo, `demo failover` usciva con «nessun
primario in vista su «rs»». `Inspector.topology()` legge la descrizione che il driver **ha già**,
e subito dopo `connetti` quella descrizione è vuota: la scoperta comincia in quel momento
([M-042](Sources.md#m-042)). Gli altri comandi non ci inciampavano per caso — `stats` chiede
`serverStatus`, che aspetta la selezione, e `watch` guarda la topologia proprio mentre cambia.

La correzione è un `ping`, che essendo un comando su `admin` va sul primario per impostazione
predefinita ([A-017](Sources.md#a-017)) e quindi **aspetta**. Il posto comodo era `cli.py`, e
`test_pymongo_si_importa_solo_nell_infrastruttura` lo vieta: la guardia non è stata toccata, e il
codice è finito meglio di dove voleva andare — `SenzaPrimario` è un fatto dell'infrastruttura,
`niente_da_fermare` è la frase che la riga di comando ne ricava
([ADR-0099](../../docs/Decision.md#adr-0099)).

**Una prova che passava per la ragione sbagliata.** La seconda esecuzione ha fallito dicendo che
il nuovo primario era il nodo appena ucciso: la prova cercava la prima riga `SERVER … →
primario`, che è la **scoperta iniziale**. Il pericolo non era il fallimento ma il suo contrario:
una prova così passerebbe anche se il guasto non fosse mai arrivato. L'asserzione si appoggia
adesso alla riga di continuazione `da … a …`, che la cronaca stampa solo se qualcuno ha davvero
preso il posto di qualcun altro.

### La prova che fa da umano

`tests/integration/test_scenari.py` gira la scena dentro il container e supplisce alla metà che
manca: legge lo stdout, esegue **verbatim** sull'host la riga `docker compose` che la scena
annuncia, e rimanda un Invio. Di passaggio dimostra la sola cosa che nessun'altra prova può
dimostrare — che la riga annunciata è davvero incollabile. Fissare la forma di quella riga ha
richiesto [M-040](Sources.md#m-040): i due `--env-file` sono obbligatori, `-p` non serve, e la
prima versione componeva percorsi assoluti che dentro il container esistevano e sull'host no.

### Il confronto del Passo 5, che è la vera chiusura del task

| | `feature/02`, a mano | `mongolab`, Task 13 |
|---|---|---|
| interruzione | 9 812 / 10 619 / 10 943 ms ([V-029](../../docs/Sources.md#v-029)) | **10 019 ms** |
| scritture perse | 0 su 12 901 ([V-033](../../docs/Sources.md#v-033)) | **0** su 15 229 |

Coincidono ([M-043](Sources.md#m-043)), e nessuno dei due va corretto. Il confronto contava
perché le prove con i doppi asseriscono sulla **sequenza**, e una sequenza giusta può
accompagnare due numeri sbagliati: se il guasto non arrivasse, l'interruzione sarebbe zero e la
sequenza resterebbe identica.

Lo zero, poi, ha una spiegazione che cambia la frase da dire in sala. Il `WriteConcern` del client
è **vuoto**: `mongolab` non chiede niente, e `w: majority` arriva dal server come default
*implicito* ([M-041](Sources.md#m-041)). Non «la mia applicazione usa `w: majority`», che sarebbe
falso, ma «nessuno qui ha chiesto niente, e il server ha scelto bene».

### Fuori copione: il ciclo di `watch` ha lasciato `cli.py`

È diventato `sorveglia`, in `application/scenari.py`. Non è riordino: dentro la radice di
composizione era provabile solo aprendo una connessione, e la sua regola più delicata — si aspetta
`giri - 1` volte e non `giri` — non aveva nessuna prova. Il punto aperto del Task 12 si chiude
qui.

### Numeri

| | Prima | Dopo |
|---|---|---|
| Prove unitarie | 462 | **523** |
| Prove di integrazione | 47 | **48** |
| File controllati da mypy | 58 | **64** |
| Prove degli strumenti | 166 | 166 |
| ADR del repository | 93 | **99** |
| Fonti esterne nel registro dell'app | 16 | **17** |
| Misure nel registro dell'app | 39 | **43** |
| Porte del dominio | 5 | **6** |
| Eventi del dominio | 9 | **10** |

## Task 14 — Il backup a caldo, e una finestra che non si poteva scegliere a tavolino

**Fatto il 4 settembre 2026.** Il capitolo che ne esce è
[15-il-backup-a-caldo-e-la-finestra-che-si-misura.md](15-il-backup-a-caldo-e-la-finestra-che-si-misura.md).

È l'Atto III del Blocco 2, quattro minuti: `mongodump --readPreference=secondary --oplog` **sotto
carico**, con i due ritmi accostati, e poi il restore con i conteggi a schermo. Il piano lo scriveva
in quattro passi e li ha ottenuti tutti. Quello che non poteva prevedere è che il Passo 1 avrebbe
dovuto cominciare **da dove il comando gira**, e che la risposta non era quella che il Task 9 aveva
lasciato in sospeso.

### La strada corta si costruisce e non parte

Il debito era scritto dal Task 9: nell'immagine dell'applicazione `mongodump` non c'è
([M-039](Sources.md#m-039)), e la scelta fra installarlo e restare su `docker exec` era rimandata a
qui. La scelta è stata fatta **provando**, e la prova è durata cinque minuti.

Un `Dockerfile` a due stadi che copia i due binari dall'immagine `mongo` pinnata dentro quella
`python` pinnata si costruisce **senza un avviso**, e poi esce con **127**:
`libgssapi_krb5.so.2: cannot open shared object file` ([M-044](Sources.md#m-044)). I due strumenti
non sono statici; `python:3.13-slim` è slim proprio perché non ha le librerie Kerberos contro cui
sono compilati. Il guasto non arriva al `build`, che sarebbe il momento buono: arriva alla prima
esecuzione, cioè il peggiore possibile — in sala.

Le altre tre strade sono state scartate senza provarle, ognuna perché avrebbe disfatto una decisione
già presa: `apt-get install mongodb-database-tools` aggiunge un pacchetto che nessun `FROM` dichiara
e vuole rete al `build` ([ADR-0093](../../docs/Decision.md#adr-0093)); il socket Docker nel container
rovescia la decisione da cui è nata la sesta porta ([ADR-0095](../../docs/Decision.md#adr-0095)); il
volume condiviso non serve, perché il dump sopravvive nel filesystem del nodo fra i due comandi.
Resta quella giusta, ed è [ADR-0100](../../docs/Decision.md#adr-0100): **gli strumenti stanno dove
sono già**, e la riga per entrarci la costruisce `ComandiCompose.dentro`, che esisteva dal Task 12.

Ne segue la cosa meno intuitiva del task: le due metà della stessa scena hanno **due indirizzi
diversi** per lo stesso cluster. L'applicazione parla con `localhost:27021`; `mongodump`, che gira
dentro `mongo-rs-1`, ha bisogno di `rs0/mongo-rs-1:27017,…`. È `host_interno_di`, e le due viste del
`Bersaglio` — nate al Task 13 per un'altra ragione — servono qui **contemporaneamente**, nello
stesso comando, per la prima volta.

### La finestra non si sceglie: la detta il dump

Il `mongodump` della collezione della demo dura **476 ms** ([M-045](Sources.md#m-045)). Se la fase
«durante» durasse i venti secondi che uno sceglierebbe a tavolino, il dump occuperebbe il due per
cento del campione: **un crollo totale del throughput per tutta la durata del dump comparirebbe come
un calo del due per cento**, e la promessa del copione risulterebbe verificata da una misura
incapace di smentirla.

Da qui `finche: Continua | None` in `WorkloadRunner.esegui`, che **si somma** al limite invece di
sostituirlo: la condizione è il limite vero, `durata_s` è la rete di sicurezza. E da qui il rifiuto
di riceverlo da solo, con un `ValueError` invece di un predefinito silenzioso — una condizione che
dipende da un processo esterno resta vera per sempre se quel processo si pianta, ed è esattamente il
caso che rovinerebbe la scena. È [ADR-0101](../../docs/Decision.md#adr-0101).

### Il calo esce negativo, e resta negativo

Contro lo stack vero: `ritmo prima 595/s · durante 692/s · calo -16.2%`
([M-047](Sources.md#m-047)). Un calo negativo, cioè un ritmo salito, perché la finestra è mezzo
secondo e su mezzo secondo il rumore pesa più del dump. Sarebbe stato facile scrivere «il dump non
ha impatto» e avere ragione quel giorno; il rapporto scrive la percentuale **con il segno** e lascia
concludere alla sala. I numeri che contano sono quelli assoluti accanto: 279 scritture durante il
dump, tutte confermate, p95 da 66,3 a 68,7 ms.

C'è anche una ragione misurata per cui il primario non se ne accorge. Senza `--readPreference` il
primario prende **+15** letture; con `--readPreference=secondary` ne prende **+0**, e le quindici
vanno sui due secondari ([M-046](Sources.md#m-046)). La misura **chiude un punto aperto di
`feature/02`**: `docs/03-amministrazione/backup-restore.md` elencava quell'opzione fra le cose «non
misurate», e adesso la pagina ha la sua §8 applicativa e il punto dichiarato chiuso.

### Due guardie, e l'asimmetria da mettere in scaletta

`demo failover` gira dentro la rete e dall'host si rifiuta. `demo backup-live` e `demo restore` fanno
l'esatto contrario, e non è un'incoerenza: il failover ha bisogno che il driver veda la topologia, il
backup ha bisogno del client Docker che nel container non c'è. La seconda guardia rifiuta gli altri
due stack **sulla proprietà** e non sul nome — `bersaglio.da_rete.replica is not None` — con due
messaggi diversi, perché su un mongod solo l'oplog non c'è e attraverso un `mongos` c'è ma senza un
istante comune.

E c'è un terzo controllo, che sembra ridondante e non lo è: `attendi_il_primario` fa `ping`, e con
`directConnection` un `ping` **riesce anche su un secondario**. Dopo l'Atto II il nodo pubblicato è
ancora secondario per qualche secondo, e senza il controllo esplicito su `topology().ha_primario` il
guasto comparirebbe alla prima scrittura, con il carico partito e la collezione a metà. Quanti
secondi, adesso si sa: **4,0** ([M-048](Sources.md#m-048)).

### Il restore accanto, e perché non è solo prudenza

`--into lab` è rifiutato, e la ragione è più sottile del riflesso «non sovrascrivere». I 106
documenti che alla copia mancano **sono ancora nell'originale**: un restore sopra `lab` li
lascerebbe dove sono, i conteggi combacerebbero, e la differenza sparirebbe *proprio perché* il
restore è riuscito. La scena mostrerebbe zero e insegnerebbe il contrario di quello che deve
insegnare. È [ADR-0102](../../docs/Decision.md#adr-0102), che nello stesso passaggio decide anche
che la riga successiva la stampa la scena precedente: la collezione di carico ha la data nel nome, e
ricopiarla a mano davanti alla sala è il modo più prevedibile di sbagliare un comando.

### Due lezioni dalle prove, e nessuna delle due sul codice di produzione

**Una prova nuova che passa alla prima non ha ancora provato niente.** La prova d'integrazione è
stata rotta apposta — `dove=None` in `strumento_di` — per vederla rossa con il messaggio giusto:
`open …/app/docker/02-replicaset/compose.yaml: no such file or directory`. Quel messaggio è
riportato verbatim nella docstring della prova, perché sapere come si presenta il guasto vale quanto
sapere che la prova lo prende.

**La pulizia deve sopravvivere al fallimento.** La prima stesura di `_dall_host` chiamava
`check_returncode()` prima di restituire l'output, e lasciava spazzatura: il nome della collezione di
carico lo annuncia la scena sulla sua prima riga, quindi se il helper solleva, il chiamante non ha
mai saputo che cosa pulire — e la collezione era già stata creata e riempita. Il fallimento è
esattamente il caso in cui la pulizia serve di più. La versione buona restituisce `tuple[int, str]`,
non solleva mai, e il codice di uscita si asserisce **dopo** aver letto il nome.

Fuori dai due, una terza cosa vale la riga. `test_container.py::test_dentro_la_rete_il_replica_set_ha_un_primario`
è fallita **una volta**, con `mongo-rs-3 sconosciuto` e `mongod attivo da 1 m 14 s`. Da sola: verde.
L'intera suite da uno stack assestato: verde. Era la scia dei failover fatti a mano poco prima — la
scoperta SDAM incompleta in un container appena avviato — e non un difetto di questo task. Una prova
che fallisce una volta e poi passa è una prova da **spiegare**, non da rieseguire finché non tace.

### Numeri

| | Prima | Dopo |
|---|---|---|
| Prove unitarie | 523 | **582** |
| Prove di integrazione | 48 | **49** |
| File controllati da mypy | 64 | 64 |
| Prove degli strumenti | 166 | 166 |
| ADR del repository | 99 | **102** |
| Fonti esterne nel registro dell'app | 17 | 17 |
| Misure nel registro dell'app | 43 | **48** |
| Porte del dominio | 6 | 6 |
| Eventi del dominio | 10 | 10 |

---

## Che cosa manca

I task dal 13 al 18 non sono ancora stati eseguiti. Le pagine dei principi dicono, dove descrivono il
futuro, che lo stanno facendo. L'avviso di stato in testa a
[04-eventi-del-driver-e-concorrenza.md](04-eventi-del-driver-e-concorrenza.md) è stato riscritto al
Task 7, perché quella pagina descriveva un codice che adesso esiste.

I punti su cui questo registro tornerà, perché sono dichiarati aperti:

| Aperto | Dove è dichiarato | Quando si chiude |
|---|---|---|
| ~~Uno store che **fallisce** le scritture: oggi nessun doppio sa rompersi~~ | [registro, Task 4](#task-4--i-doppi-scritti-prima-del-codice-che-dovranno-verificare) | **chiuso** al Task 5 |
| La saturazione di `maxPoolSize`: `scrittori` è il gancio, non la misura | [06](06-carico-tentativi-e-latenze.md#il-gancio-per-maxpoolsize-e-la-misura-che-non-cè) | Task 16 |
| La coda è illimitata: sotto un carico lungo cresce in memoria | [A-010, riserve](Sources.md#a-010) | Task 16 |
| L'invariante del §6.3 è difeso *per quello che è* da una sola prova | [registro, Task 5](#task-5--il-generatore-di-carico-i-tentativi-le-latenze) | se i conteggi lasciassero il ciclo di drenaggio |
| `$group` non è nel dialetto di `InMemoryStore` | il messaggio di `NonSupportato`, e [02](02-porte-e-doppi.md#dove-il-doppio-non-sa-solleva) | la prima prova che lo chiederà |
| Il rifiuto dei booleani in `_come_intero` non è coperto da nessuna prova | [M-006, riserve](Sources.md#m-006) | la prima prova che dipenderà da lui |
| ~~`SdamBridge` e la coda: il comportamento di PyMongo va **osservato**, non solo letto~~ | [08](08-il-ponte-sdam-e-i-thread-del-driver.md) | **chiuso** al Task 7, per la parte che non richiede un cluster |
| ~~Nessun `ClusterInspector` reale: il `TopologyWatcher` ha visto solo topologie finte~~ | [registro, Task 6](#task-6--losservatore-della-topologia-e-i-due-numeri-del-failover) | **chiuso** al Task 8: quattordici prove di integrazione guardano tre topologie vere |
| ~~L'osservatore interroga invece di ascoltare: la risoluzione è l'intervallo~~ | [08](08-il-ponte-sdam-e-i-thread-del-driver.md) | **chiuso** al Task 7: il ponte riceve i cambiamenti quando accadono |
| ~~L'intervallo predefinito di 500 ms è scelto, non misurato~~ | [07](07-topologia-failover-e-i-due-numeri.md#il-limite-di-questo-osservatore-dichiarato) | **decaduto** al Task 13: l'interruzione non si sonda più, si **deduce** dagli eventi del ponte ([ADR-0096](../../docs/Decision.md#adr-0096)), quindi la risoluzione della misura non dipende più da nessun intervallo. I 500 ms restano il ritmo con cui la scena drena la coda verso lo schermo, che è un'altra cosa |
| Il `TopologyWatcher` non ha un invariante di thread: oggi non lo usa nessuno | [registro, Task 6](#task-6--losservatore-della-topologia-e-i-due-numeri-del-failover) | **Task 13 non l'ha rimesso in servizio, e la scadenza cade**: `ScenarioFailover` deduce l'interruzione dal ponte ([ADR-0096](../../docs/Decision.md#adr-0096)), non da una sentinella che interroga. Il `TopologyWatcher` resta codice provato che nessun comando costruisce: la domanda vera, da porre al Task 18, non è più «che invariante di thread ha» ma «serve ancora» |
| `ChunkMigrated` potrebbe non essere osservabile da un client di `mongos` | [08](08-il-ponte-sdam-e-i-thread-del-driver.md#che-cosa-non-è-ancora-verificato) | Task 15 |
| Un'eccezione dentro un listener finisce su `stderr`, e sotto un `Live` non si vede | [M-015](Sources.md#m-015) | **ancora aperto dopo il Task 13, e più esposto**: `demo failover` senza `--step` usa `--sink rich` per default, e ci mette dentro un failover vero, cioè il momento in cui gli ascoltatori lavorano di più. La difesa resta la stessa — gli ascoltatori sono **totali** — e non è che l'errore si veda. Task 18, con la registrazione che è il controllo |
| La soglia della prova cronometrata non prende una `f-string` nel callback | [M-013, riserve](Sources.md#m-013) | dichiarata, non si chiude |
| Le unità delle durate sono lette nel sorgente di PyMongo, non viste su un battito vero | [M-012, riserve](Sources.md#m-012) | il primo battito su un cluster in movimento: il Task 8 ha collegato l'ispettore, non il ponte |
| ~~Come le prove di integrazione ricevono la credenziale senza violare ADR-0054~~ | [decisioni](decisioni-che-vincolano-app.md#adr-0054) | **chiuso** al Task 8: [M-018](Sources.md#m-018) e [ADR-0083](../../docs/Decision.md#adr-0083) |
| ~~`refresh_per_second` dichiarato invece che ereditato~~ | [04](04-eventi-del-driver-e-concorrenza.md) | **chiuso** al Task 10, al contrario: [M-027](Sources.md#m-027) mostra che con `auto_refresh=False` il parametro è **inerte**, e il ritmo vive nel periodo del ciclo ([ADR-0085](../../docs/Decision.md#adr-0085)) |
| ~~L'immagine dell'applicazione fra quelle da avere in cache offline~~ | [decisioni](decisioni-che-vincolano-app.md#adr-0009) | **chiuso** al Task 12: le due basi sono pinnate in `tools/images.env` e `tools/preflight.sh` verifica che `mongolab:0.1.0` sia in cache ([ADR-0093](../../docs/Decision.md#adr-0093)) |
| Il contratto condiviso copre **dodici** comportamenti: la fedeltà del doppio oltre quelli non è misurata | [09](09-adattatori-veri-e-contratto-condiviso.md#che-cosa-questo-capitolo-ha-chiuso-e-che-cosa-no) | non si chiude: si riduce, una verifica alla volta |
| ~~`REPLICA_SET_CON_PRIMARIO` non è verificabile dall'host: `directConnection` legge la forma `SINGOLA`~~ | [M-019, riserve](Sources.md#m-019) | **chiuso** al Task 12: dalla rete Compose la forma si legge `replicaset` con un primario, e c'è una prova d'integrazione che la guarda ([M-036](Sources.md#m-036)) |
| Dopo un arresto sporco, `$shardedDataDistribution` può riportare conteggi imprecisi | [A-012, riserve](Sources.md#a-012) | dichiarata: il Blocco 3 fa un `docker kill`, e va detto dal palco |
| L'ispettore dipende da `config`, che il manuale dichiara interno | [A-013, riserve](Sources.md#a-013) | dichiarata: la difesa è la prova sullo stack 03, che diventa rossa se il formato cambia |
| `ordered=False` è stato misurato solo su istanza singola in loopback | [M-021, riserve](Sources.md#m-021) | se il Blocco 3 mostrerà scritture lente |
| Il sink testuale per le registrazioni di riserva | [decisioni](decisioni-che-vincolano-app.md#adr-0050) | il sink **c'è** dal Task 10 ([`PlainSink`](11-tre-rese-e-un-solo-thread-che-disegna.md#plainsink-il-flush-non-è-prudenza-è-il-contenuto)); resta collegarlo a `tools/registra-terminale.py`, al Task 18 |
| Uccidere il client `docker exec` non uccide `mongodump` dentro il container | [10](10-processi-esterni-e-il-verdetto-che-manca.md#literatore-abbandonato-e-un-limite-che-va-detto) | **la scelta è stata fatta al Task 14, il limite resta**: gli strumenti restano nei nodi e si raggiungono con `docker compose exec`, perché copiarli nell'immagine produce un container che non parte ([M-044](Sources.md#m-044), [ADR-0100](../../docs/Decision.md#adr-0100)). Adesso la porta `BackupTool` è collegata a due comandi veri, quindi il limite è **esposto**: un Ctrl-C durante `demo backup-live` lascia `mongodump` a girare dentro il nodo. Task 18, con la registrazione che è il controllo |
| `Progress.completati` non porta l'unità: documenti per il dump, byte per il restore | [10](10-processi-esterni-e-il-verdetto-che-manca.md#un-inconveniente-dichiarato-completati-non-porta-con-sé-lunità) | Task 10 è passato senza chiederlo: la TUI stampa la percentuale, non il numero. Torna al Task 18 se una registrazione mostrerà il conteggio |
| Il formato del testo di `mongodump`/`mongorestore` è quello della 100.18.0 | [M-024, riserve](Sources.md#m-024) | dichiarata: la difesa è la suite di integrazione, che diventa rossa se il formato cambia |
| Un `BrokenPipeError` scrivendo la password a un processo già morto non è gestito | [M-023, riserve](Sources.md#m-023) | la prima volta che si riprodurrà: gestire un caso mai visto è codice che nessuna prova copre |
| `--nsFrom`/`--nsTo` senza `--nsInclude` è stato osservato una volta e non ripetuto | [M-024, riserve](Sources.md#m-024) | dichiarata: ripeterlo significa far passare `mongorestore` sugli utenti dell'amministratore |
| `PlainSink` non gestisce `BrokenPipeError`: chi reindirizza su `head` vede una traccia invece di una fine | [11](11-tre-rese-e-un-solo-thread-che-disegna.md#che-cosa-questo-capitolo-lascia-aperto) | la prima volta che succederà dentro una registrazione |
| ~~Non esiste ancora un `Orologio` di sistema: `RichTui` lo riceve, e in produzione nessuno glielo dà~~ | [11](11-tre-rese-e-un-solo-thread-che-disegna.md#che-cosa-questo-capitolo-lascia-aperto) | **chiuso** al Task 11: `SystemClock` è ancorato al muro una volta sola e avanzato dal contatore monotono ([ADR-0086](../../docs/Decision.md#adr-0086), [M-030](Sources.md#m-030)) |
| Nessuna prova guarda che cosa Rich disegna davvero: il Passo 4 lo vieta | [11](11-tre-rese-e-un-solo-thread-che-disegna.md#il-divieto-del-passo-4-letto-due-volte) | Task 18: la registrazione `.cast` **è** il controllo, e la guarda una persona |
| Il costo di un disegno è misurato su `StringIO`, non su un terminale vero | [M-028, riserve](Sources.md#m-028) | Task 18, se la registrazione risultasse a scatti |
| `_RefreshThread` è privato di Rich e può cambiare senza avviso | [A-015, riserve](Sources.md#a-015) | dichiarata: la difesa è la prova che conta i thread, che si accorgerebbe del cambiamento |
| Sullo stack 03 `lab.carico-*` **non è distribuita**: `init/30-dati-demo.js` distribuisce solo `lab.ordini` su `{_id: "hashed"}` | [ADR-0088, riserve](../../docs/Decision.md#adr-0088) | Task 16, ed è la prima cosa che quel task deve decidere: o distribuire la collezione, o dichiarare che misura un solo shard |
| `TOPOLOGIA singola → singola` è vera e non utile: cambia la *descrizione*, non la forma | [12](12-la-radice-di-composizione-e-la-prima-esecuzione-vera.md#che-cosa-questo-capitolo-lascia-aperto) | decidendo che cosa quella riga debba dire, non aggiungendo un osservatore |
| ~~Il ciclo di `watch` vive in `cli.py`: orchestrazione dentro la radice di composizione~~ | [12](12-la-radice-di-composizione-e-la-prima-esecuzione-vera.md#che-cosa-questo-capitolo-lascia-aperto) | **chiuso** al Task 13: è `sorveglia` in `application/scenari.py`, e la regola delle attese — `giri - 1` e non `giri` — adesso ha le sue prove |
| Le letture fallite si contano ma non emettono nessun evento: nel consuntivo ci sono, in cronaca no | [12](12-la-radice-di-composizione-e-la-prima-esecuzione-vera.md#che-cosa-questo-capitolo-lascia-aperto) | **il Task 13 non l'ha chiesto, e per scelta**: la scena del failover gira con `--readers 0`, perché durante l'elezione le letture su un secondario continuano a riuscire e mescolate alle scritture renderebbero illeggibile l'unica cosa che quella scena misura. Torna al Task 16, dove le letture sono il contenuto |
| `rapporto()` riceve la porta invece dei valori già letti, quindi l'ordine delle interrogazioni è affar suo | [12](12-la-radice-di-composizione-e-la-prima-esecuzione-vera.md#terzo-la-fotografia-diceva-sconosciuto-di-un-server-sano) | dichiarata: chi volesse comporre un rapporto da dati raccolti altrove oggi non può |
| La mappa dei bersagli contiene le porte **predefinite**, e i Compose le scrivono `${PORTA_...:-27021}` | [ADR-0087, riserve](../../docs/Decision.md#adr-0087) | dichiarata: la difesa sarebbe una prova che rilegge il `compose.yaml` e confronta |
| La scoperta è misurata su un set **con** il primario: il ramo `updateRSWithoutPrimary` non è stato visto | [M-036, riserve](Sources.md#m-036) | **chiuso a metà** al Task 13: [M-043](Sources.md#m-043) attraversa lo stato senza primario e ne esce con un primario diverso, quindi il ramo viene percorso; ciò che resta non visto è la parte che dà il nome al ramo — un server **aggiunto** mentre non c'è primario — perché i tre membri erano già tutti noti. Servirebbe un membro aggiunto al set durante l'elezione, che non è una scena del talk |
| Il bind mount del sorgente fa vincere l'host sull'immagine: in sala sarebbe una sorpresa | [13](13-il-container-sulla-rete-e-la-scoperta-che-si-vede.md#che-cosa-questo-capitolo-lascia-aperto) | Task 18: chi registra i filmati di riserva ricostruisce prima |
| `make app-image` costruisce sempre attraverso lo stack 01, dando per scontato che i tre servizi `app` siano identici | [ADR-0092, riserve](../../docs/Decision.md#adr-0092) | dichiarata: la difesa è la prova che verifica che i tre stack dichiarino la stessa immagine |
| `check_stack.py` legge le righe `FROM` con una regex, non con un parser di Dockerfile | [ADR-0093, riserve](../../docs/Decision.md#adr-0093) | dichiarata: basta per i Dockerfile che questo repository scrive |
| `M-037` è misurata con l'archivio immagini di containerd: con il vecchio archivio a grafo il comportamento è un altro | [M-037, riserve](Sources.md#m-037) | dichiarata: la decisione non cambia, la sua motivazione sì |
| Le prove d'integrazione **dichiarano** il punto di vista invece di leggerlo dall'ambiente | [ADR-0090, riserve](../../docs/Decision.md#adr-0090) | dichiarata: è una precauzione contro una `MONGOLAB_PUNTO_DI_VISTA` esportata a mano, non contro il codice |
| La scena dal vivo richiede **due terminali**: uno mostra, l'altro esegue il guasto annunciato | [14](14-la-scena-del-failover-e-i-due-numeri.md#il-guasto-entra-da-una-porta-e-la-porta-è-nata-da-unimpossibilità) | non si chiude, si prova: è [ADR-0095](../../docs/Decision.md#adr-0095), e l'alternativa era il socket Docker nel container. Da portare al PO prima delle prove generali |
| `--step` con `--sink rich` è **rifiutato**: dal palco la resa è `plain` | [ADR-0098, riserve](../../docs/Decision.md#adr-0098) | Task 18: se in proiezione `plain` non reggesse, la decisione va riaperta, con la sospensione del `Live` come prima candidata |
| Le due scene dell'Atto III girano **solo dall'host** e **solo su `rs`**: è l'inverso di `demo failover` | [15](15-il-backup-a-caldo-e-la-finestra-che-si-misura.md#due-guardie-nuove-e-unasimmetria-voluta) | non si chiude, si mette in scaletta: fra Atto II e Atto III si cambia terminale, ed è [ADR-0100](../../docs/Decision.md#adr-0100). Da portare al PO con la stessa urgenza dei due terminali del failover |
| Fra l'Atto II e l'Atto III il primario ci mette **quattro secondi** a tornare al suo posto | [M-048](Sources.md#m-048) | dichiarata: sono misurati **dopo** una scena che comprende già cinque secondi di recupero, quindi a freddo il tempo è presumibilmente più lungo. La prova concede sessanta secondi proprio per questo |
| `--readPreference=secondary` è misurato una volta sola, e la ripartizione fra i due secondari non la governa niente di dichiarato | [M-046, riserve](Sources.md#m-046) | dichiarata: è la selezione del driver degli strumenti, e su un'altra macchina può cadere diversamente. La conclusione — il primario passa da +15 a +0 — non dipende da quella ripartizione |
| Che davanti a un `mongodump` che esce con uno lo schermo dica la cosa giusta entro un secondo è **ragionato, non misurato** | [15](15-il-backup-a-caldo-e-la-finestra-che-si-misura.md#chi-sta-su-quale-thread-e-perché-due-e-non-tre) | il `finally` che ferma il carico è provato con i doppi; il comportamento in scena no. Task 18, insieme alle altre prove di come si presenta un guasto |
| Il dump non esce dal nodo: `/tmp/mongolab-backup` vive dentro `mongo-rs-1` e sparisce con lui | [15](15-il-backup-a-caldo-e-la-finestra-che-si-misura.md#che-cosa-questo-capitolo-lascia-aperto) | non si chiude qui: dove vada una copia vera, con quale rotazione e quale cifratura, è la stessa lacuna che dichiara [la pagina canonica](../../docs/03-amministrazione/backup-restore.md) |
| `--mode sospendi` non ha una prova di integrazione: che `pause` dia un **timeout** invece di un connection refused è affermato, non misurato | [14](14-la-scena-del-failover-e-i-due-numeri.md#il-supplemento-irraggiungibile-ma-vivo) | il Passo 3 del Task 13 ha prodotto il codice e non la misura. Prima delle prove generali, perché è la scena che il pubblico non si aspetta |
| I 10 019 ms dipendono dalle impostazioni di elezione **di questo lab** | [M-043, riserve](Sources.md#m-043) | dichiarata: la frase in sala è «su questo lab», non «in MongoDB» |
| «Zero scritture perse» dipende da un default **del server**, non da una scelta dell'applicazione | [M-041](Sources.md#m-041) | dichiarata: un `setDefaultRWConcern` più debole cambierebbe il numero, ed è una cosa da dire, non un difetto da correggere |
| La prova di integrazione della scena assicura una banda larga (5-15 s), non il numero | [14](14-la-scena-del-failover-e-i-due-numeri.md#contro-lo-stack-vero-una-prova-che-fa-da-umano) | dichiarata: la banda intercetta l'errore di categoria, il numero preciso sta in [M-043](Sources.md#m-043) |

---

**Torna a:** [README.md](README.md) per l'indice.

**Il registro completo del repository**, che copre anche le altre feature, è
[`docs/registro-operativo-sviluppo.md`](../../docs/registro-operativo-sviluppo.md). Le note di metodo
citate qui (137–185) stanno lì per esteso.
