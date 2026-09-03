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

## Che cosa manca

I task dal 5 al 18 non sono ancora stati eseguiti. Le pagine dei principi dicono, dove descrivono il
futuro, che lo stanno facendo — in particolare
[04-eventi-del-driver-e-concorrenza.md](04-eventi-del-driver-e-concorrenza.md), che porta in testa un
avviso di stato.

I punti su cui questo registro tornerà, perché sono dichiarati aperti:

| Aperto | Dove è dichiarato | Quando si chiude |
|---|---|---|
| Uno store che **fallisce** le scritture: oggi nessun doppio sa rompersi | [registro, Task 4](#task-4--i-doppi-scritti-prima-del-codice-che-dovranno-verificare) | Task 5 |
| `$group` non è nel dialetto di `InMemoryStore` | il messaggio di `NonSupportato`, e [02](02-porte-e-doppi.md#dove-il-doppio-non-sa-solleva) | la prima prova che lo chiederà |
| Il rifiuto dei booleani in `_come_intero` non è coperto da nessuna prova | [M-006, riserve](Sources.md#m-006) | la prima prova che dipenderà da lui |
| `SdamBridge` e la coda: il comportamento di PyMongo va **osservato**, non solo letto | [04](04-eventi-del-driver-e-concorrenza.md#che-cosa-non-è-ancora-verificato) | Task 7 |
| `ChunkMigrated` potrebbe non essere osservabile da un client di `mongos` | [04](04-eventi-del-driver-e-concorrenza.md#che-cosa-non-è-ancora-verificato) | Task 7 |
| Come le prove di integrazione ricevono la credenziale senza violare ADR-0054 | [decisioni](decisioni-che-vincolano-app.md#adr-0054) | Task 8 |
| `refresh_per_second` dichiarato invece che ereditato | [04](04-eventi-del-driver-e-concorrenza.md) | Task 10 |
| L'immagine dell'applicazione fra quelle da avere in cache offline | [decisioni](decisioni-che-vincolano-app.md#adr-0009) | Task 12 |
| Il sink testuale per le registrazioni di riserva | [decisioni](decisioni-che-vincolano-app.md#adr-0050) | Task 18 |

---

**Torna a:** [README.md](README.md) per l'indice.

**Il registro completo del repository**, che copre anche le altre feature, è
[`docs/registro-operativo-sviluppo.md`](../../docs/registro-operativo-sviluppo.md). Le note di metodo
citate qui (137–152) stanno lì per esteso.
