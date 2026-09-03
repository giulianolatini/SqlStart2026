# 9. Gli adattatori veri, e il contratto che li tiene onesti

> Il principio in una riga: **un doppio che si comporta diversamente dall'originale è un doppio
> che mente, e l'unico modo di accorgersene è far girare le stesse prove sui due.**

Fino al Task 7 questa applicazione non aveva mai parlato con un MongoDB. Aveva le porte
([capitolo 1](01-architettura-esagonale.md)), i doppi che le implementano
([capitolo 2](02-porte-e-doppi.md)), gli eventi ([capitolo 3](03-eventi-immutabili.md)), il
generatore di carico ([capitolo 6](06-carico-tentativi-e-latenze.md)), l'osservatore della topologia
([capitolo 7](07-topologia-failover-e-i-due-numeri.md)) e il ponte che traduce gli eventi del driver
([capitolo 8](08-il-ponte-sdam-e-i-thread-del-driver.md)). Tutto provato, tutto verde, e tutto
contro qualcosa che avevamo scritto noi.

Questo capitolo racconta il Task 8, in cui l'applicazione ha incontrato il cluster. La notizia non è
che funziona: è **che cosa si è rotto**, e quanto era invisibile prima.

---

## Il debito che il Task 4 aveva contratto senza dirlo

`InMemoryStore` è una lista di dizionari con quattro metodi sopra. Filtra per uguaglianza, salta,
limita, conta, e sa eseguire una manciata di stadi di aggregazione. È stato scritto in mezz'ora,
funziona, e settanta prove ci girano contro in meno di un secondo.

Il problema di un doppio così non è che sia semplice. È che **è convincente**. Ogni volta che una
prova passa contro `InMemoryStore`, chi la legge conclude qualcosa sul comportamento
dell'applicazione contro MongoDB — e quella conclusione è valida solo nella misura in cui il doppio
somiglia all'originale. Nessuno aveva mai misurato quella somiglianza. Non c'era un posto in cui
fosse scritta, e non c'era un modo di accorgersi che era calata.

Il Passo 4 del Task 8 chiede esattamente questo, e vale la pena leggerlo per intero perché è il
cuore del capitolo:

> Gli stessi test che il Task 4 ha scritto contro `InMemoryStore` girano contro `PymongoStore` dove
> il contratto è identico. Un doppio che si comporta diversamente dall'originale è un doppio che
> mente, e questo passo è il modo di accorgersene.

---

## Il contratto: un file che non è una prova

`app/tests/contratto_archivio.py` non contiene nessuna funzione che pytest raccoglierebbe. Non
inizia per `test_`, non sta in `tests/unit` né in `tests/integration`, e importarlo da solo non
esegue niente. Contiene **dodici funzioni che prendono un `DocumentStore` e sollevano
`AssertionError` se quel `DocumentStore` si comporta male**, più la tupla `VERIFICHE` che le elenca.

```python
def impagina_saltando_e_limitando(archivio: DocumentStore) -> None:
    archivio.insert_many(ordini())
    prima = archivio.find_page({}, salta=0, quanti=2)
    seconda = archivio.find_page({}, salta=2, quanti=2)
    assert len(prima) == 2
    assert len(seconda) == 1
    assert [d["cliente"] for d in prima] + [d["cliente"] for d in seconda] == [
        "ada", "grace", "ada",
    ]
```

Poi due file, in due posti diversi, la eseguono:

```python
# tests/unit/test_contratto_archivio.py — veloce, nessun Docker
@pytest.mark.parametrize("verifica", VERIFICHE, ids=lambda v: v.__name__)
def test_il_doppio_rispetta_il_contratto(verifica) -> None:
    archivio: DocumentStore = InMemoryStore()
    verifica(archivio)

# tests/integration/test_contratto_archivio.py — stack 01 acceso
@pytest.mark.parametrize("verifica", VERIFICHE, ids=lambda v: v.__name__)
def test_l_adattatore_rispetta_il_contratto(verifica, archivio: PymongoStore) -> None:
    verifica(archivio)
```

Il valore sta tutto nel fatto che il **corpo** della verifica è scritto una volta sola. Se stesse
scritto due volte — anche identico, anche copiato con il copia-e-incolla — divergerebbe: qualcuno
correggerebbe la copia del doppio per farla passare, e la copia dell'originale resterebbe indietro
senza che nessuno se ne accorga. Un contratto copiato non è un contratto.

I nomi delle verifiche appaiono negli identificativi di pytest, quindi un fallimento si legge senza
aprire il file:

```
FAILED tests/integration/test_contratto_archivio.py::
       test_l_adattatore_rispetta_il_contratto[una_pagina_di_zero_documenti_e_vuota]
```

### L'elenco è scritto a mano, e non è pigrizia al contrario

`VERIFICHE` è una tupla di dodici nomi, non il risultato di un `dir()` filtrato per prefisso. La
raccolta automatica sembra più comoda e ha un difetto che si paga una volta sola: una verifica
scritta male — nome fuori schema, importata da un altro modulo, dimenticata dopo un `rename` —
sparisce dall'elenco senza che niente diventi rosso. La copertura cala in silenzio, e il silenzio è
precisamente ciò contro cui esiste questo file. Dodici righe da tenere aggiornate sono il prezzo di
sapere quante sono.

---

## Il primo bugiardo, trovato in ventisei secondi

La prima esecuzione del contratto contro `InMemoryStore` — prima ancora che `PymongoStore`
esistesse — ha dato `1 failed, 10 passed`. La verifica che è caduta:

```python
def un_conteggio_su_niente_e_zero_non_un_errore(archivio: DocumentStore) -> None:
    assert archivio.aggregate([{"$count": "quanti"}]) == ()
```

Il doppio rispondeva `({"quanti": 0},)`. Ed era stato scritto così senza malizia: `len(documenti)`
di una lista vuota fa zero, e la riga sembrava giusta a chiunque l'avesse letta.

La regola del repository è che a decidere chi ha ragione non è il ragionamento, è la misura. Una
sonda contro lo stack 01 ([M-017](Sources.md#m-017)):

```
collezione inesistente:
  $count            -> []
  $match+$count     -> []
  $group _id:null   -> []
  count_documents   -> 0
con due documenti, ma filtro che non prende niente:
  $match+$count     -> []
```

**Uno stadio di aggregazione che non riceve documenti non ne emette.** Non è una particolarità di
`$count`: anche `$group` con `_id: null`, che in SQL corrisponderebbe a un `COUNT(*)` su zero righe
e darebbe zero, qui tace. L'unico che risponde zero è `count_documents`, che non è una pipeline.

Il doppio è stato corretto, non il contratto:

```python
case "$count":
    nome_campo = self._come_testo(nome, argomento)
    # Su zero documenti in ingresso, MongoDB non emette **niente**: né `$count`
    # né `$group {_id: null}` producono la riga con lo zero che SQL darebbe.
    if not documenti:
        return []
    return [{nome_campo: len(documenti)}]
```

### Perché questo difetto era peggio di un errore

Nessuna delle due parti solleva. Il doppio risponde una lista di un elemento, MongoDB risponde una
lista vuota, e il codice che le consuma è lo stesso:

```python
quanti = risultato[0]["quanti"]     # doppio: 0.  MongoDB: IndexError.
```

La suite veloce passa. Il difetto compare contro il cluster, nel momento in cui la collezione è
vuota — cioè al **primo fotogramma della demo**, prima che il generatore abbia scritto qualcosa.

Vale la pena leggerlo accanto alla **nota di metodo 155** del registro operativo, che dice che il
peggior valore mancante è lo zero, perché è indistinguibile da una misura riuscita. Qui il fenomeno
è lo stesso visto dall'altro lato: lì una risposta mancante veniva scambiata per uno zero, qui uno
zero veniva **inventato** dove la risposta manca. Le due facce dello stesso errore.

---

## Il secondo bugiardo era l'originale

La verifica successiva è nata da un sospetto e non da un fallimento:

```python
def una_pagina_di_zero_documenti_e_vuota(archivio: DocumentStore) -> None:
    archivio.insert_many(ordini())
    assert archivio.find_page({}, quanti=0) == ()
    assert archivio.find_page({}, salta=1, quanti=0) == ()
    assert len(archivio.find_page({}, quanti=2)) == 2
```

Sul doppio passa: `documenti[salta:salta + 0]` è la lista vuota, come chiunque si aspetta. Contro
MongoDB ([M-022](Sources.md#m-022)):

```
### DOPPIO ###
2 passed, 10 deselected in 0.02s
### ORIGINALE ###
>       assert archivio.find_page({}, quanti=0) == ()
E       AssertionError
```

Il manuale lo dice in una riga sola, e la riga inverte l'ovvio: «A `limit()` value of 0 (i.e.
`.limit(0)`) is equivalent to setting no limit» ([A-011](Sources.md#a-011)). **Zero non significa
nessun documento: significa nessun limite.** La traduzione ovvia di `find_page` avrebbe restituito
la collezione intera a chi ne aveva chiesti zero.

E `quanti=0` non lo digita nessuno. Ci si arriva per sottrazione: quante righe restano nella
finestra, quanti documenti mancano alla fine dell'elenco, quanti ne ha chiesti l'utente meno quanti
ne abbiamo già. È il caso limite di un calcolo, cioè precisamente quello che nessuno prova a mano —
e in scena si sarebbe visto come cinquantamila righe che scorrono dove ne erano state chieste zero.

La guardia è quindi stata scritta **dopo** aver visto la prova fallire, che è la **nota di
metodo 159** applicata al caso più facile: quando esiste già una seconda implementazione che si
comporta bene, il caso in cui la guardia manca non va costruito — c'è già.

```python
if quanti <= 0:
    return ()
```

La stessa pagina del manuale spiega anche perché la guardia dice `<= 0` e non `== 0`: un limite
**negativo** «closes the cursor after returning a single batch of results», che non è «nessun
documento» ma «un lotto e poi basta» — un terzo comportamento, altrettanto lontano da quello che la
porta promette.

---

## Le cinque divergenze che il contratto non può contenere

Un contratto condiviso funziona solo dove le due implementazioni **devono** coincidere. Dove non
devono, forzarle sarebbe peggio: o si mutila l'originale, o si gonfia il doppio di comportamenti che
nessuna prova richiede — e la regola ferrea dei doppi di questo repository
([capitolo 2](02-porte-e-doppi.md)) dice che una capacità si aggiunge **insieme** alla prova che la
chiede.

Le divergenze stanno quindi in cinque prove che vivono solo nel file di integrazione, e ciascuna
dichiara la propria:

| Prova | Il doppio | L'originale |
|---|---|---|
| `test_l_originale_conosce_gli_operatori_che_il_doppio_rifiuta` | `$gt` → `NonSupportato` | filtra |
| `test_l_originale_confronta_i_sottodocumenti_e_l_ordine_dei_campi_conta` | `NonSupportato` | confronta, **e l'ordine delle chiavi conta** |
| `test_l_originale_esegue_group_che_il_doppio_non_conosce` | `$group` → `NonSupportato` | raggruppa |
| `test_l_originale_rifiuta_un_id_duplicato_e_il_doppio_lo_accetta` | accetta | `BulkWriteError` |
| `test_l_originale_non_promette_l_ordine_che_il_doppio_garantisce` | ordine d'inserimento | ordine solo se `sort` |

La seconda merita una riga in più, perché è una trappola vera di MongoDB e non una differenza fra
implementazioni: `{"spedizione": {"citta": "Ancona", "cap": "60121"}}` e
`{"spedizione": {"cap": "60121", "citta": "Ancona"}}` sono **due filtri diversi**. Un confronto fra
sottodocumenti è un confronto fra documenti BSON serializzati, e la serializzazione conserva
l'ordine dei campi. Il doppio non sa farlo e solleva; l'originale lo fa e dà zero risultati, che è
la risposta giusta a una domanda che chi scrive non sapeva di aver posto.

L'ultima è quella che giustifica una riga di `PymongoStore` che sembrerebbe superflua:

```python
pagina = self.collezione.find(dict(filtro)).sort("_id", ASCENDING).skip(salta).limit(quanti)
```

Senza `sort`, `skip` e `limit` chiedono al server pagine di un insieme che **non ha un ordine
definito**: due chiamate consecutive possono restituire lo stesso documento due volte e un altro
mai, e nessuna delle due sbaglia. Una pagina che non è stabile non è una pagina. Si ordina per
`_id` perché è l'unico campo che c'è sempre, ha sempre un indice e non richiede di conoscere lo
schema — con il prezzo dichiarato che l'ordine è quello degli `_id`, che coincide con quello
d'inserimento solo se gli `_id` crescono. Per il dataset di questa demo è vero, perché `_id` **è**
l'indice del documento; in generale no.

---

## L'`_id` che il driver scrive nel tuo dizionario

`PymongoStore.insert_many` comincia con una riga che sembra prudenza generica:

```python
copie = [dict(documento) for documento in documenti]
```

Non lo è. PyMongo scrive l'`_id` che genera **dentro il dizionario che gli hai passato**. La
documentazione lo afferma di `insert_one` — il documento «Must be a mutable mapping type. If the
document does not have an `_id` field one will be added automatically»
([A-014](Sources.md#a-014)) — e non lo afferma di `insert_many`, dove pure succede.

Il generatore di carico riusa i propri dizionari fra un giro e l'altro. Senza la copia, al secondo
giro si troverebbe un `_id` già dentro e tenterebbe di inserire due volte la stessa chiave: un
`BulkWriteError` al posto di una scrittura, in mezzo alla demo, per una riga che nessuno ha
scritto.

Siccome la documentazione non lo dichiara per il metodo che usiamo, il fatto è provato invece che
citato — `test_l_adattatore_non_scrive_l_id_nel_documento_di_chi_lo_ha_chiamato` chiama prima
l'adattatore e poi il driver nudo sullo stesso dizionario, e mostra la differenza. La copia serve
comunque per un secondo motivo indipendente: la porta dichiara `Mapping`, il driver vuole un mapping
mutabile. Avere due ragioni la rende difficile da togliere per sbaglio.

---

## `ordered=False`: la scelta abituale, misurata prima di adottarla

Ogni guida al caricamento massivo consiglia `ordered=False`. Stava per essere adottato per
abitudine, e la **nota di metodo 162** dice che una soglia — o una scelta di prestazioni — si misura
prima di scriverla. Stack 01, lotti da 500, ventimila documenti per configurazione, tre giri
alternati ([M-021](Sources.md#m-021)):

```
giro 0  ordered=True   totale 123.1 ms  mediana lotto 2.63 ms  162426 doc/s
giro 0  ordered=False  totale 115.9 ms  mediana lotto 2.70 ms  172497 doc/s
giro 1  ordered=True   totale 134.0 ms  mediana lotto 2.69 ms  149307 doc/s
giro 1  ordered=False  totale 113.7 ms  mediana lotto 2.54 ms  175855 doc/s
giro 2  ordered=True   totale 115.1 ms  mediana lotto 2.48 ms  173779 doc/s
giro 2  ordered=False  totale 118.0 ms  mediana lotto 2.55 ms  169500 doc/s
```

Le mediane per lotto stanno fra 2,48 e 2,70 ms **in entrambe le configurazioni**, e al giro 2
l'ordinato è perfino più veloce. Non c'era niente da guadagnare, quindi resta il predefinito
`ordered=True`, che in cambio dà un errore più semplice da leggere.

Quello che la misura **non** copre è scritto accanto ai numeri, ed è la parte che conta di più: è
un'istanza singola su loopback, senza rete, senza `w: majority` e senza contesa. Le tre condizioni
in cui il confronto può ribaltarsi sono tutte fuori — una rete con latenza vera, un replica set che
aspetta la maggioranza, e soprattutto uno **sharded cluster**, dove un lotto si spezza fra shard e
`ordered=True` costringe a rispettarne la sequenza. Se il Blocco 3 mostrerà scritture lente, questa
è la prima riga da rimisurare.

---

## L'unica cosa del client su cui l'adattatore ha voce

`PymongoStore` riceve una `Collection` già fatta e non decide niente della connessione: indirizzo,
autenticazione, `directConnection`, `readPreference` sono di chi lo costruisce, e al Task 12 quella
scelta sarà [ADR-0012](../../docs/Decision.md#adr-0012). Se la politica stesse qui, provare
l'adattatore vorrebbe dire provare anche la politica.

Con una sola eccezione, e il costruttore la fa valere:

```python
if not collezione.codec_options.tz_aware:
    raise ValueError(
        "la collezione arriva da un client senza tz_aware=True: i datetime "
        "tornerebbero indietro ingenui, il confronto con quelli scritti "
        "riuscirebbe lo stesso, e sbaglierebbe di quante ore vale il fuso. ..."
    )
```

Una guardia si giustifica quando l'alternativa è un errore **silenzioso**, e questo è il caso
manuale: `tz_aware` è predefinito a `False` — si vede nel `repr` del client misurato in
[M-018](Sources.md#m-018) — le date tornano indietro ingenue, il confronto fra due ingenue riesce
senza protestare, e lo sbaglio si manifesta come un orario storto sullo schermo, in scena, sbagliato
di quante ore vale il fuso. Nessuna eccezione, nessun avvertimento, solo un numero plausibile.

---

## L'ispettore: tre risposte gratis, una che costa

`PymongoInspector` implementa `ClusterInspector` e chiude un debito che il Task 6 aveva scritto nero
su bianco: fin lì `TopologyWatcher` aveva visto solo topologie costruite a mano da `FakeInspector`,
e nessuno sapeva se una topologia **vera** entrasse in quella forma. Ora ci entra, e ci entra
passando dal ponte SDAM del [capitolo 8](08-il-ponte-sdam-e-i-thread-del-driver.md) senza
riscriverne una riga:

```python
def topology(self) -> DescrizioneTopologia:
    return descrivi_topologia(self._client.topology_description)
```

Quella riga non fa un giro di rete. Il driver **tiene già aggiornata** la descrizione per conto suo
— interroga i server con il monitoraggio SDAM e conserva l'ultima risposta — quindi chiedergliela è
leggere una struttura in memoria. È la ragione per cui il Blocco 2 può ridisegnarla a ogni
fotogramma senza aggiungere carico a un cluster di cui sta misurando la latenza, ed è anche la
ragione per cui quella descrizione può essere **vecchia di qualche secondo**: che è precisamente il
fenomeno che il Blocco 2 esiste per mostrare.

`server_status()` e `db_stats()` invece parlano col server, e restituiscono il documento **grezzo**.
È una scelta, non una pigrizia: attraverso un mongos `serverStatus` risponde con `process: "mongos"`
e senza metà dei campi, perché un router non ha un motore di memorizzazione; e `dbStats` risponde
**aggregato** sugli shard, con un campo `raw` che altrove non c'è. Normalizzare i tre casi in un
unico modello darebbe l'impressione che siano lo stesso caso, e guardare un `dataSize` senza sapere
che è una somma è credere di guardare una macchina mentre se ne guardano due.

### `shard_distribution`, ovvero due numeri che stanno in due posti

È il metodo che costa, e costa **due** chiamate. Il motivo è tutta la scena del Blocco 3: **chunk e
documenti non si deducono l'uno dall'altro.** Con una chiave di sharding sbagliata si vedono i chunk
divisi a metà e i documenti tutti da una parte, ed è esattamente ciò che il pubblico deve vedere
succedere.

I documenti per shard li sa `$shardedDataDistribution`, che è l'unico modo di averli **senza
interrogare gli shard uno per uno** ([A-012](Sources.md#a-012)). Lo stadio si esegue solo su
`mongos` e solo sul database `admin`, e l'ispettore somma `numOwnedDocuments` e **non**
`numOrphanedDocs`: gli orfani sono i documenti rimasti su uno shard dopo una migrazione non ancora
ripulita, e sommarli farebbe superare al totale il numero di documenti che esistono — con il conto
che non torna con `count()` per un motivo che sembrerebbe un errore del codice.

I chunk li sa il catalogo, e il modo di interrogarlo è prescritto dal manuale: «To find the chunks
in a collection, retrieve the collection's `uuid` identifier from the `config.collections`
collection. Then, use the `uuid` to retrieve the document with the same `uuid` from the
`config.chunks` collection» ([A-013](Sources.md#a-013)).

Qui c'è la trappola peggiore del capitolo. Sul 7.0.40 di questo repository, un chunk ha questi campi
([M-020](Sources.md#m-020)):

```
['_id', 'history', 'lastmod', 'max', 'min', 'onCurrentShardSince', 'shard', 'uuid']
quanti chunk hanno il campo ns? 0    (su 5 chunk totali)
query per ns='lab.ordini':        0
join su uuid: [{'_id': 'shard1rs', 'chunk': 2}, {'_id': 'shard2rs', 'chunk': 2}]
join su _id:  []
```

Non c'è nessun `ns`, e cercarlo **non solleva**: restituisce zero. Zero chunk su uno shard che ne
ha due, cioè la conclusione «i dati non sono distribuiti» detta esattamente nel momento in cui lo
sono. Il manuale, va detto, **non** afferma da nessuna parte che `ns` sia stato tolto e non nomina
la 5.0 a questo proposito: quindi il codice non lo scrive come regola di versione, lo scrive come
misura su questo ambiente. La differenza fra le due formulazioni è tutta la differenza fra una
riserva onesta e una leggenda tramandata.

Lo stesso ispettore dichiara due riserve che vengono dalla pagina del manuale. Lo stadio è «New in
version 6.0.3», e su un cluster più vecchio solleverebbe senza che questo file abbia un ripiego. E:
«After an unclean shutdown of a `mongod` using the Wired Tiger storage engine, size and count
statistics reported by `$shardedDataDistribution` may be inaccurate» — cioè dopo un `docker kill`,
che è per definizione un arresto sporco, i numeri possono essere imprecisi. Il Blocco 3 fa
esattamente un `docker kill`. **Va detto dal palco invece di essere scoperto**, ed è la ragione per
cui sta scritto qui.

### Come si decide che non è sharded: guardando, non inciampando

```python
def _e_sharded(self) -> bool:
    return any(server.ruolo is RuoloServer.ROUTER for server in self.topology().server)
```

Su un mongod `$shardedDataDistribution` solleva davvero: codice 6789101, «The
$shardedDataDistribution stage can only be run on mongoS», misurato. Sarebbe stato facile catturare
l'eccezione e dedurne la topologia — ed è fragile: il giorno in cui quel codice cambia, o in cui
l'utente non ha i permessi su `admin`, «non è sharded» diventa la risposta a una domanda diversa. Il
driver la topologia la sa già; basta chiedergliela.

E si chiede il **ruolo**, non la forma. `TipoTopologia.SHARDED` sarebbe la risposta ovvia e ha un
buco: un client costruito con `directConnection=True` verso un mongos legge la forma `SINGOLA` —
conosce un server solo, quindi non ha nulla da chiamare cluster — mentre il ruolo di quel server
resta `ROUTER`, perché glielo dice `hello` con `msg: "isdbgrid"`. Siccome è precisamente così che le
prove di integrazione si collegano (vedi sotto), la differenza non è teorica: è la differenza fra
sei prove verdi e sei prove che non provano niente.

### La tupla vuota che ha due significati

`shard_distribution()` restituisce `()` sia quando non è uno sharded cluster, sia quando lo è ma
**questa collezione non è distribuita** — i documenti stanno tutti sullo shard primario e il
catalogo non ha niente da dire su di loro. Distinguere i due casi richiederebbe un tipo di ritorno
diverso. Per la scena che questa applicazione mostra la distinzione non serve, e la porta lo
dichiara invece di fingere di averla fatta: entrambi i casi hanno la loro prova di integrazione,
`test_su_un_istanza_singola_non_c_e_distribuzione_per_shard` e
`test_una_collezione_non_distribuita_dentro_un_cluster_sharded`.

---

## La macchina delle prove: accendere, sporcare, ripulire

[ADR-0020](../../docs/Decision.md#adr-0020) è la regola che governa tutto il Passo 3: **niente
testcontainers, si usano gli stack di questo repository.** Non è avversione a una libreria: è che i
test devono verificare l'artefatto che il pubblico eseguirà davvero. Un container di prova
configurato altrove sarebbe verde mentre lo stack del lab è rotto.

`app/tests/integration/ambiente.py` fa tre cose e nient'altro.

**Accende.** `sveglia(stack)` prova un ping da 2 000 ms; se fallisce esegue `make up-0X` con un
timeout di dieci minuti e ripinga con 20 000 ms. Se anche quello fallisce, solleva riportando le
ultime venti righe dell'uscita di `make` — perché un errore di Compose letto a tre righe non dice
niente. Provato spegnendo davvero lo stack:

```
$ make down-01 && pytest tests/integration -k "stack01 or contratto"
19 passed in 8.13s
```

Otto secondi da stack spento a diciannove prove verdi, senza che nessuno abbia digitato `make up-01`.

**Non spegne.** Alla fine gli stack restano su, ed è deliberato: fermare uno stack che l'operatore
aveva già acceso sarebbe un effetto che le prove non hanno causato, e chi sta preparando la demo si
troverebbe la scena smontata da una suite di test.

**Ripulisce i dati, non l'infrastruttura.** Ogni prova riceve un database usa-e-getta:

```python
@contextmanager
def collezione_usa_e_getta(client, collezione="ordini"):
    nome = f"{PREFISSO_PROVE}{uuid4().hex[:12]}"
    try:
        yield client[nome][collezione]
    finally:
        client.drop_database(nome)
```

È il Passo 5, e la sua ragione sta nel modo in cui questo genere di difetto si presenta: una misura
che sporca lo stack fa fallire la prova **dopo**, per un motivo che sembra un altro. Il prefisso
`mongolab_prove_` serve alla rete di sicurezza `spazza()`, che all'apertura della sessione cancella
i residui di una corsa interrotta — e cancella **solo** quelli, perché `lab` è il database della
demo e nessuna prova ha il diritto di toccarlo.

### Un marcatore per stack, applicato da solo

I tre stack costano tempi molto diversi. Chi sta lavorando sull'adattatore vuole poter dire «solo
l'istanza singola», e chi prepara il Blocco 3 vuole il contrario:

```python
def pytest_collection_modifyitems(items):
    for prova in items:
        for chiave in STACK:
            if f"stack{chiave}" in getattr(prova, "fixturenames", ()):
                prova.add_marker(f"stack{chiave}")
```

I marcatori si applicano **da sé**, guardando quale fixture la prova ha chiesto. Un decoratore
scritto a mano si dimentica, e una prova che chiede `stack03` senza il marcatore accenderebbe un
cluster sharded dentro una selezione che credeva di averlo escluso.

I tre marcatori sono dichiarati in `pyproject.toml` insieme a `--strict-markers`, che trasforma un
marcatore non dichiarato da avvertimento in errore di raccolta. Misurato che cosa copre e che cosa
no: `@pytest.mark.stack3` scritto in un decoratore ferma pytest con «'stack3' not found in `markers`
configuration option»; ma `pytest -m stack3` sulla riga di comando **deseleziona tutto ed esce
zero** — trentatré prove saltate, nessuna protesta. Non c'è un'opzione che lo impedisca, e l'unica
difesa è che il numero di prove raccolte si legge sempre. Sta scritto nel `pyproject.toml` per non
essere scoperto il giorno in cui una suite «verde» non aveva eseguito niente.

E la suite veloce resta veloce, perché `testpaths = ["tests/unit"]`: un `pytest` nudo — quello che
si digita distrattamente — non accende niente.

```
make app-test              →  214 passed in 0.79s     (nessun Docker)
make app-test-integration  →   33 passed in 1.46s     (tre stack accesi)
```

---

## Due trappole della connessione, misurate perché non erano scritte

### `replicaSet=rs0` dall'host: quattro secondi per una diagnosi sbagliata

La forma canonica per collegarsi a un replica set è passare il nome del set. Fatto dall'host contro
lo stack 02 **sano** ([M-019](Sources.md#m-019)):

```
FALLITA dopo 4.2s — ServerSelectionTimeoutError
mongo-rs-1:27017: [Errno 8] nodename nor servname provided, or not known
mongo-rs-2:27017: [Errno 8] nodename nor servname provided, or not known
mongo-rs-3:27017: [Errno 8] nodename nor servname provided, or not known
topology_type_name: ReplicaSetNoPrimary
```

È [ADR-0012](../../docs/Decision.md#adr-0012) e [ADR-0021](../../docs/Decision.md#adr-0021) visti
dal lato che fa male. Il client si collega alla porta pubblicata, chiede la configurazione del set, e
la configurazione gli risponde con i **nomi di servizio Compose** — che dentro la rete esistono e
sull'host no. Tutti e tre i membri falliscono la risoluzione DNS.

Il punto non è che fallisca: è **come** si legge il fallimento. `ReplicaSetNoPrimary`, tre server
sconosciuti, errore di selezione: è indistinguibile da un replica set che ha davvero perso il
primario. Nel Blocco 2, dove si fa cadere un primario apposta, sarebbe la diagnosi giusta al momento
sbagliato.

Con `directConnection=True`, sulla stessa porta:

```
topology_type_name: Single
  server: ('localhost', 27021) RSPrimary 0.0017s
hello.setName: rs0
hello.hosts: ['mongo-rs-1:27017', 'mongo-rs-2:27017', 'mongo-rs-3:27017']
conta lab.ordini: 50000
```

Quindi le prove usano `directConnection`, **con la riserva scritta**: il *ruolo* si legge giusto
(`RSPrimary` → `PRIMARIO`), la *forma* no (`Single` → `SINGOLA`). `REPLICA_SET_CON_PRIMARIO` non è
verificabile dall'host, e lo sarà al Task 12 dall'interno della rete Compose. Una riserva così va
detta anche perché il fenomeno è **peggiore su un'altra macchina**: su Linux con `network_mode:
host`, o con voci in `/etc/hosts`, i nomi risolverebbero e la trappola non scatterebbe — due
comportamenti diversi senza aver cambiato una riga.

### La credenziale che non esce

[ADR-0054](../../docs/Decision.md#adr-0054) vieta di passare la password con `-e` al client
`docker`. Le prove non usano `docker`, usano PyMongo — quindi la domanda era un'altra: passata come
argomento, quella password esce da qualche parte? Cercata nei tre posti in cui sarebbe finita
([M-018](Sources.md#m-018)):

```
la password compare nel messaggio di ServerSelectionTimeoutError? False
la password compare nel messaggio di OperationFailure?           False   ("Authentication failed.")
la password compare nel repr del client?                         False
repr: MongoClient(host=['localhost:27021'], document_class=dict, tz_aware=False,
                  connect=True, authsource='admin', directconnection=True)
```

Il `repr` mostra `authsource` e `directconnection`, e non mostra `password`. Il posto scoperto non
era PyMongo: era il codice delle prove, che la avrebbe messa in un `dataclass` il cui `repr` finisce
in ogni traceback. Da lì:

```python
@dataclass(frozen=True)
class Credenziali:
    utente: str
    password: str = field(repr=False)
```

Con il buco residuo dichiarato: `credenziali.password` stampato a mano si vede, perché non può
essere altrimenti.

### E il `.env` che nel worktree non c'era

Le prove accendono gli stack, `make up-02` e `make up-03` leggono `PASSWORD_AMMINISTRATORE` da
`docker/0X-.../.env`, e [ADR-0056](../../docs/Decision.md#adr-0056) dice che quei file vivono nel
checkout principale e non in un worktree. Il Task 8 è il primo che ne ha avuto bisogno da dentro un
worktree.

Copiare il file avrebbe creato una seconda copia di un segreto che invecchia in silenzio; scrivere
un percorso assoluto nel codice delle prove avrebbe messo la macchina di chi sviluppa dentro un file
versionato. [ADR-0083](../../docs/Decision.md#adr-0083) apre la sede che mancava e sceglie il
collegamento simbolico: il file resta uno, il versionamento non lo vede, e `make up-02` funziona
senza sapere niente di tutto questo.

---

## Il generatore deterministico, e perché non è un dettaglio

Il Passo 2 chiede un `DataGenerator` in cui lo stesso seme produce lo stesso dataset. La ragione sta
scritta nel piano: **è la condizione perché una misura di oggi e una di giovedì siano
confrontabili**, e perché la prova generale non scopra numeri diversi da quelli provati.

`DataGenerator.documento(indice)` è una funzione pura del seme e dell'indice — nessuno stato interno,
nessun `random` globale, nessuna dipendenza dall'ordine di chiamata. Chiedere il documento 4 000 dà
lo stesso risultato che si arrivi da un lotto di cinquemila o da una chiamata isolata, e due
processi paralleli che si dividono gli indici producono insieme esattamente il dataset che ne
avrebbe prodotto uno solo.

Il seme predefinito è `20260918`, cioè la data del talk.

---

## Che cosa questo capitolo ha chiuso, e che cosa no

**Chiuso.** «Nessun `ClusterInspector` reale: il `TopologyWatcher` ha visto solo topologie finte» —
adesso quattordici prove di integrazione guardano tre topologie vere, e la traduzione del ponte SDAM
regge su tutte e tre. «Come le prove di integrazione ricevono la credenziale senza violare
ADR-0054» — misurato, e la risposta è ADR-0083 più `field(repr=False)`.

**Non chiuso, e non per dimenticanza.** L'intervallo predefinito di 500 ms del `TopologyWatcher`
resta *scelto* e non *misurato*: per misurarlo serve un failover cronometrato, cioè il Blocco 2 in
funzione, che arriva più avanti. E le unità delle durate del driver sono ancora lette nel sorgente
di PyMongo invece che viste su un battito vero: il Task 8 ha collegato l'ispettore, non ha ancora
acceso il ponte SDAM contro un cluster in movimento.

**Il limite del contratto, dichiarato.** Dodici verifiche che passano da entrambe le parti non
dimostrano che il doppio sia fedele: dimostrano che lo è su quei dodici casi. Il numero di
comportamenti di MongoDB è molto più grande di dodici, e ogni volta che una prova unitaria conclude
qualcosa che il contratto non copre, sta usando una somiglianza che nessuno ha verificato. La
differenza rispetto a prima non è che il rischio sia sparito: è che adesso ha un posto in cui si
misura, e un numero.
