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

## Che cosa manca

I task dall'8 al 18 non sono ancora stati eseguiti. Le pagine dei principi dicono, dove descrivono il
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
| Nessun `ClusterInspector` reale: il `TopologyWatcher` ha visto solo topologie finte | [registro, Task 6](#task-6--losservatore-della-topologia-e-i-due-numeri-del-failover) | Task 8 |
| ~~L'osservatore interroga invece di ascoltare: la risoluzione è l'intervallo~~ | [08](08-il-ponte-sdam-e-i-thread-del-driver.md) | **chiuso** al Task 7: il ponte riceve i cambiamenti quando accadono |
| L'intervallo predefinito di 500 ms è scelto, non misurato | [07](07-topologia-failover-e-i-due-numeri.md#il-limite-di-questo-osservatore-dichiarato) | Task 8 |
| Il `TopologyWatcher` non ha un invariante di thread: oggi lo usa un thread solo | [registro, Task 6](#task-6--losservatore-della-topologia-e-i-due-numeri-del-failover) | Task 10, con la TUI |
| `ChunkMigrated` potrebbe non essere osservabile da un client di `mongos` | [08](08-il-ponte-sdam-e-i-thread-del-driver.md#che-cosa-non-è-ancora-verificato) | Task 15 |
| Un'eccezione dentro un listener finisce su `stderr`, e sotto un `Live` non si vede | [M-015](Sources.md#m-015) | Task 11 |
| La soglia della prova cronometrata non prende una `f-string` nel callback | [M-013, riserve](Sources.md#m-013) | dichiarata, non si chiude |
| Le unità delle durate sono lette nel sorgente di PyMongo, non viste su un battito vero | [M-012, riserve](Sources.md#m-012) | Task 8 |
| Come le prove di integrazione ricevono la credenziale senza violare ADR-0054 | [decisioni](decisioni-che-vincolano-app.md#adr-0054) | Task 8 |
| `refresh_per_second` dichiarato invece che ereditato | [04](04-eventi-del-driver-e-concorrenza.md) | Task 10 |
| L'immagine dell'applicazione fra quelle da avere in cache offline | [decisioni](decisioni-che-vincolano-app.md#adr-0009) | Task 12 |
| Il sink testuale per le registrazioni di riserva | [decisioni](decisioni-che-vincolano-app.md#adr-0050) | Task 18 |

---

**Torna a:** [README.md](README.md) per l'indice.

**Il registro completo del repository**, che copre anche le altre feature, è
[`docs/registro-operativo-sviluppo.md`](../../docs/registro-operativo-sviluppo.md). Le note di metodo
citate qui (137–161) stanno lì per esteso.
