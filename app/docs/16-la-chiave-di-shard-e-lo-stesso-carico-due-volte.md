# 16. La chiave di shard, e lo stesso carico due volte

> Il principio in una riga: **una sola colonna non dimostra niente.** Che i documenti si dividano
> fra due shard è un'affermazione finché non c'è accanto, con lo stesso carico e nello stesso
> istante, una collezione che nessuno ha distribuito e che se li prende tutti.

Questo è il Blocco 3, ed è la parte che `feature/03` aveva potuto mostrare solo **a riposo**: la
pagina dello sharded cluster dichiarava scoperto «il comportamento oltre la soglia del balancer»
proprio perché serviva carico controllato. Adesso il carico c'è, ed è controllato al punto che le
due corse scrivono lo stesso numero esatto di documenti.

La schermata, misurata contro lo stack 03 vero:

```
non sharded carico-20260904-140333 non è distribuita · 5000 documenti su shard1rs
sharded     shard1rs          17047 documenti (50%) · 1 chunk
            shard2rs          17368 documenti (50%) · 1 chunk
arrivati    shard1rs 2507 (50%) · shard2rs 2493 (50%)
bilancio    sbilancio 0 punti · chunk 0 in più
mirata      {"_id": 4242} · SINGLE_SHARD · 1 shard
su tutti    {"citta": "Ancona"} · SHARD_MERGE · 2 shard
carico      5000 scritture su ognuna
fasi        riposo · non-distribuita · distribuita · piani · bilancio
```

Tre cose di questo capitolo sono arrivate perché il codice, eseguito, ha contraddetto il piano: un
evento del design è **uscito**, un limite di tempo è diventato un conteggio, e un metodo che
sembrava corretto negava un cluster acceso. Sono le tre sezioni più lunghe.

---

## L'evento che non ha trovato nessuno che lo emetta

Il Passo 2 del piano diceva: «l'evento `ChunkMigrated` trova finalmente chi lo emette. Se durante
la scrittura risulta che non è osservabile dal client, va detto: un evento dichiarato nel design e
non producibile è una voce in `Sources.md` e un ADR, non un campo morto nel codice».

Non è l'osservabilità ad aver deciso. È il fatto.

Prima di scrivere l'emittente valeva la pena chiedersi se ci fosse mai qualcosa da emettere, e la
risposta è stata misurata invece che ricordata ([M-049](Sources.md#m-049)). `balancerStatus` dice
`mode: "full"` e **1 153 giri**: il balancer è acceso e lavora. `config.changelog`, che conserva le
voci dall'`addShard` del giorno dell'inizializzazione, ha due `merge` e **zero** migrazioni — non
una sola voce `moveChunk`, `moveRange` o `migrate`.

Il perché sta nel disegno dello stack, non in un guasto. `lab.ordini` è distribuita su
`{_id: "hashed"}` ([ADR-0064](../../docs/Decision.md#adr-0064)), e una chiave hashed sparpaglia i
documenti **all'inserimento**: i due shard restano a un chunk ciascuno e a metà dei documenti
ciascuno, e non c'è nessuno sbilancio da correggere. Il balancer migra quando qualcuno si è
sbilanciato; qui non succede mai. [ADR-0069](../../docs/Decision.md#adr-0069) l'aveva già scritto
un task prima — il balancer di una 7.0 fa due mestieri, e in questo lab esercita solo il secondo,
l'AutoMerger che fonde.

Quindi `ChunkMigrated` è uscito da `domain/eventi.py`
([ADR-0103](../../docs/Decision.md#adr-0103)). Al suo posto c'è un commento che dice che stava lì,
quando è uscito e con quale misura: un buco nominato costa meno di un buco muto, perché il prossimo
che cerca l'evento nel design lo trova invece di ricostruirlo.

La guardia scende da dieci nomi a nove, ed è quello il punto in cui la decisione si paga:

```python
def test_gli_eventi_del_design_sono_nove_e_sono_quelli() -> None:
    """Otto dal §6.3, il nono da ADR-0082, il decimo da ADR-0094, meno uno: ADR-0103."""
```

Rimettere l'evento significa cambiare quell'elenco, cioè accorgersene.

### Che cosa mostra la scena al posto dell'evento

La riga `bilancio sbilancio 0 punti · chunk 0 in più`. Non è un campo vuoto: è un'affermazione, e
afferma il vero. Uno zero **mostrato** dice che la distribuzione era già decisa prima che arrivasse
la prima scrittura; uno zero taciuto sembrerebbe una funzione che manca.

E `chunk_in_piu` è `None` — non zero — quando una delle due fotografie non è distribuita, perché la
differenza fra i chunk di una collezione sharded e quelli di una che non lo è non è un numero, è un
confronto fra due cose diverse.

---

## Lo stesso carico due volte, e la volta in cui non lo è stato

La decisione del PO era «lo stesso carico due volte, con i conteggi per shard accostati», accettando
uno sforo di scaletta. La prima esecuzione vera, quando il limite era ancora una durata come nelle
altre tre scene, ha stampato in fondo:

```
carico      4288 senza chiave · 4415 con chiave · non è lo stesso carico
```

Sei secondi per corsa, gli stessi otto scrittori, pochi secondi di distanza — e due conteggi diversi
([M-052](Sources.md#m-052)). Il tre per cento non è molto, e non è il punto: la scena si chiama «lo
stesso carico due volte», e con due conteggi diversi la differenza fra le colonne non è più
attribuibile alla sola chiave di shard.

**La riga di garanzia ha funzionato.** Ha detto il vero, e ciò che denunciava era un difetto di
disegno. Nessuna prova unitaria poteva vederlo: i doppi fanno esattamente il numero di scritture che
il copione chiede, quindi `confrontabile` è sempre stato verde. Il fatto vive nel punto in cui un
limite di tempo incontra due throughput diversi, cioè in nessuno dei due.

Da lì `demo sharding` è l'unica delle quattro scene **senza** `--carico`
([ADR-0107](../../docs/Decision.md#adr-0107)). Il suo limite è `--scritture`, predefinito 5 000, e
le due corse diventano uguali per costruzione invece che per fortuna. La riga resta comunque a
schermo: una garanzia che nessuno controlla è una speranza.

```python
@property
def confrontabile(self) -> bool:
    """Le due corse hanno scritto lo stesso numero di documenti?"""
    return self.carico_intera.scritture == self.carico_sparsa.scritture
```

Un booleano e non un'eccezione: la scena continua, e chi disegna la schermata decide che cosa
scriverci accanto. Se una delle due corse scrivesse meno — un archivio che rifiuta, un tentativo
esaurito — il pubblico deve vedere il numero e la sua smentita, non un traceback.

### Il verso della differenza non si racconta

In quella misura la collezione distribuita ha ricevuto **più** scritture. È una tentazione, e va
lasciata perdere: la finestra era di sei secondi, e su sei secondi il rumore vale quanto l'effetto.
Che lo sharding aumenti il throughput di scrittura è una tesi diversa da quella del Blocco 3, e
questa misura non la sostiene.

### Perché quattordici secondi invece di dieci

Cinquemila scritture costano circa sette secondi per corsa, cioè quattordici in tutto, contro i
dieci che costano le altre scene. Lo sforo è deliberato ed è stato accettato dal PO: **è il prezzo
della seconda colonna, e senza la seconda colonna la prima non dimostra niente.**

`WorkloadRunner.esegui` rifiuta per disegno i due limiti insieme, quindi non c'è una rete di
sicurezza temporale: con un `--scritture` molto grande e un cluster lento la scena dura finché dura.
È accettabile perché il predefinito è misurato, e chi lo alza sa che cosa sta chiedendo.

---

## La prima fotografia negava un cluster acceso

Terza cosa scoperta eseguendo, e la più grave delle tre. La stessa esecuzione ha stampato, su uno
stack 03 sano e distribuito:

```
sharded     shard1rs          14540 documenti (49%) · 1 chunk
            shard2rs          14875 documenti (51%) · 1 chunk
bilancio    sbilancio — · chunk —
```

Le righe con i trattini, e le righe `arrivati` mancanti. La fotografia di **prima** diceva
`distribuita=False, primario=None, conti=()` su una `lab.ordini` che le righe subito sotto
mostravano ripartita su due shard ([M-053](Sources.md#m-053)).

`PymongoInspector._e_sharded()` decideva guardando la descrizione della topologia **come il client
la conosce**. Un client appena costruito non conosce niente: **PyMongo scopre i server alla prima
operazione, non alla costruzione.** Fino a lì ogni seme è `SCONOSCIUTO`, che nel dominio significa
esattamente «assenza di un'osservazione» e non «osservato assente» — e concludere «non c'è nessun
router» da lì è leggere il proprio non aver guardato.

La correzione è una riga, e la riga ha due dettagli che non sono decorativi:

```python
def _scopri(self) -> None:
    if any(
        server.ruolo is not RuoloServer.SCONOSCIUTO
        for server in self.topology().server
    ):
        return
    self._client.admin.command("ping", read_preference=ReadPreference.NEAREST)
```

**Solo da freddo.** Appena un ruolo è noto, il monitoraggio in background di PyMongo tiene
aggiornata la descrizione da sé, e la riga non costa più niente per il resto della corsa.

**`NEAREST` e non il primario.** Per [A-017](Sources.md#a-017) un comando su `admin` va sul primario
per impostazione predefinita e **non torna finché un primario non c'è**. Su un mongos non esiste; su
un replica set in mezzo a un'elezione nemmeno. Con la preferenza predefinita questa riga avrebbe
piantato `stats` proprio durante l'Atto II, cioè avrebbe scambiato un difetto di schermata con un
blocco in scena ([ADR-0108](../../docs/Decision.md#adr-0108)).

### È la seconda volta, e la prima volta era scritta

[M-042](Sources.md#m-042) è lo stesso inciampo un task prima, in `demo failover`, risolto lì con
`attendi_il_primario` ([ADR-0099](../../docs/Decision.md#adr-0099)). La sua nota diceva già che gli
altri comandi non ci cascavano «per caso»: `stats` chiede `serverStatus`, che aspetta la selezione
del server. Il caso ha smesso di reggere alla prima scena che legge la topologia **prima** di fare
qualunque altra cosa.

### Perché nessuna prova d'integrazione lo vedeva

Questa è la parte che vale il capitolo. La fixture di sessione chiama `spazza(client)` prima di
consegnare il client, quindi la scoperta era già avvenuta per **effetto collaterale della pulizia**.
Ogni prova partiva da un client caldo; solo la sala partiva da uno freddo.

Una fixture che prepara l'ambiente prepara anche ciò che nessuno ha chiesto, e ciò che nessuno ha
chiesto non viene provato. La prova nuova apre quindi il **proprio** client:

```python
def test_la_prima_domanda_a_un_client_appena_aperto_non_nega_il_cluster() -> None:
    cliente: MongoClient[dict[str, Any]] = connetti(BERSAGLI["sharded"])
    try:
        distribuzione = PymongoInspector(cliente, DATABASE).shard_distribution(COLLEZIONE)
    finally:
        cliente.close()
    assert distribuzione.in_un_cluster, "il cluster è acceso, e il client lo deve scoprire"
    assert distribuzione.distribuita, "lab.ordini è distribuita dal seed dello stack 03"
    assert len(distribuzione.conti) == 2
```

---

## Il tipo che separa tre casi che erano due

Fino al Task 14 `shard_distribution()` restituiva una tupla, e la tupla vuota diceva **due cose
opposte**: «non è uno sharded cluster» e «è uno sharded cluster, ma questa collezione non è
distribuita». La pagina [09](09-adattatori-veri-e-contratto-condiviso.md) lo dichiarava, e
concludeva che «per la scena che questa applicazione mostra la distinzione non serve».

Il Blocco 3 è la scena in cui serve. Mette le due colonne una accanto all'altra, ed è tutto il suo
contenuto.

Il tipo di ritorno è diventato `Distribuzione(collezione, distribuita, primario, conti)`
([ADR-0104](../../docs/Decision.md#adr-0104)), e due campi bastano a separare i tre stati:

| `primario` | `distribuita` | che cosa significa                                |
| ---------- | ------------- | ------------------------------------------------- |
| `None`     | `False`       | non è uno sharded cluster: non c'è niente da dire |
| uno shard  | `False`       | è un cluster, ma la collezione sta **intera** lì  |
| uno shard  | `True`        | è un cluster, e il catalogo la conosce            |

Che cosa distingua il secondo caso dal terzo è stato **misurato, non dedotto**
([M-050](Sources.md#m-050)): su una collezione distribuita e **vuota** `$shardedDataDistribution`
produce comunque la sua riga, con i due shard a zero documenti; su una non distribuita e piena di
cinquanta documenti non ne produce nessuna. Un criterio basato sui documenti avrebbe sbagliato il
primo caso; uno basato su `config.collections` — che per una collezione non distribuita non ha
proprio la voce — avrebbe confuso «non distribuita» con «non ho i permessi per saperlo».

La quarta combinazione, `primario None` e `distribuita True`, non è rappresentabile in un cluster
reale, e il tipo **non la vieta**: sarebbe una guardia contro un errore di chi costruisce l'oggetto,
non contro un fatto del mondo, in un dominio che di validazione non ne ha da nessun'altra parte.

### La collezione passa dal costruttore al metodo

L'altra metà della stessa decisione. Fino al Task 14 la collezione arrivava dal costruttore
dell'ispettore, e la ragione scritta in `inspector.py` era buona: un ispettore capace di cambiare
bersaglio a ogni chiamata rende possibile una schermata con due numeri accanto che non parlano della
stessa cosa.

Il Blocco 3 accosta due collezioni **apposta**. La difesa impediva la scena invece di un errore.

Il rischio non è stato risolto rimettendo il divieto altrove, ma facendo sì che la risposta **si
presenti**: `Distribuzione` porta con sé il nome della collezione di cui parla, e la presentazione
lo stampa. La difesa è passata dal costruttore al dato — che è il posto in cui non ostacola nessuno
e continua a proteggere.

---

## `QueryPlanner`, la settima porta

Il Passo 3 chiede due righe: una query mirata e una scatter-gather, con accanto ciò che il router ha
deciso di farne. Nessuna delle sei porte sa fare quella domanda. `DocumentStore` scrive e legge
documenti; `ClusterInspector` guarda il cluster, non una query.

La strada corta era aggiungere `explain` a `DocumentStore`, che è già l'oggetto con la collezione in
mano. Sarebbe una promessa che la maggioranza delle sue implementazioni non mantiene: i doppi in
memoria non hanno un piano da restituire, e un metodo che quasi tutti implementano sollevando
`NotImplementedError` è una porta larga travestita da porta stretta.

Da qui la settima ([ADR-0105](../../docs/Decision.md#adr-0105)), con un metodo solo:

```python
@runtime_checkable
class QueryPlanner(Protocol):
    def explain(self, filtro: Documento) -> Piano: ...
```

Una porta si disegna guardando **chi la chiama**, non chi la implementa. Qui la chiama un solo
scenario e la soddisfa un solo adattatore: `PymongoStore`, che adesso passa per due porte invece che
per una. Che un adattatore ne soddisfi due non è un'eccezione da giustificare — è ciò che si ottiene
quando le porte sono `Protocol` strutturali e nessuno le eredita
([02](02-porte-e-doppi.md)).

### Tre cose lette da `winningPlan`, tutte e tre misurate

[M-051](Sources.md#m-051), sui tre stack:

```
mongos, {_id: 42}      stage='SINGLE_SHARD'  shards=['shard2rs']              chiavi=['shards', 'stage']
mongos, {indice: 42}   stage='SHARD_MERGE'   shards=['shard2rs', 'shard1rs']  chiavi=['shards', 'stage']
replica set, {_id: 3}  stage='IDHACK'                                         chiavi=['stage']
standalone,  {_id: 3}  stage='IDHACK'                                         chiavi=['stage']
```

**Lo stadio** sta sempre in `winningPlan.stage`, senza dover scendere in un `queryPlan` annidato, e
viaggia fino allo schermo **verbatim**: `SINGLE_SHARD` e `SHARD_MERGE` sono le parole che chi guarda
ritroverà in `explain()` la prima volta che proverà da solo. Tradurle in un booleano significherebbe
tenere aggiornato un dizionario al posto del server — il giorno in cui comparisse una terza parola,
un campo di testo la mostra e un booleano la nasconde. Il booleano lo ricava `Piano.mirata`, e da un
campo che si vede.

**Gli shard** compaiono solo attraverso un router. Fuori da un cluster la chiave `shards` non c'è
proprio, quindi la tupla vuota è un fatto e non un ripiego, e la presentazione lo dice: «nessuno
shard: qui non c'è un router».

**Il loro ordine** non è quello del nome — il server risponde `['shard2rs', 'shard1rs']` — quindi
due schermate a minuti di distanza potrebbero elencarli in ordine diverso senza che sia cambiato
niente. L'adattatore li ordina prima di consegnarli: una scena che cambia ordine da sola insegna a
diffidarne.

### I due filtri stanno nel copione, non nella scena

```python
MIRATO: Final[Documento] = {"_id": 4242}
SPARPAGLIATO: Final[Documento] = {"citta": "Ancona"}
```

Quale query sia mirata dipende dalla chiave di shard, cioè da come è fatto lo stack, cioè da
qualcosa che `application` non sa e non deve sapere. Scritti nel copione cambiano con lo stack senza
toccare la scena; scritti dentro `esegui`, sarebbero una costante vera per un solo
`docker-compose.yml`. E non hanno un valore predefinito: un filtro «ragionevole» scelto a tavolino
verrebbe usato contro uno stack con un'altra chiave, e la scena mostrerebbe due scatter-gather
affermando che il primo è mirato.

`4242` sta dentro i ventimila documenti del seed dello stack 03, e `Ancona` è la prima delle città
del generatore — oltre a essere la città del talk. Il secondo filtro non è la chiave di shard né un
suo prefisso, ed è precisamente una query che qualcuno scriverebbe davvero.

---

## `lab.ordini` si carica, e l'accoppiamento temuto non si paga

[ADR-0088](../../docs/Decision.md#adr-0088) si era chiuso con una riserva che nominava questo task:
la collezione del carico non è distribuita, quindi il confronto fra architetture avrebbe dovuto o
distribuirla al volo, o dichiarare di misurare un solo shard.

Il Blocco 3 fa una terza cosa, ed è la scena: carica **entrambe**. La collezione nuova, non
distribuita, è il metro; `lab.ordini`, distribuita, è la misura.

Il PO ha accettato di riaprire l'accoppiamento col numero del seme che ADR-0088 aveva scartato.
Misurato, non si paga. `lab.ordini` sullo stack 03 contiene 34 415 documenti: 20 000 con `_id`
intero, che sono il seed, e 14 415 con `_id` `ObjectId` e un campo `indice`, che sono le corse
dell'applicazione. Non si sono mai scontrati, **e non possono**: le scene di `demo` scrivono con
`documento_progressivo`, che l'`_id` non lo tocca e lascia che sia il server a generarlo. L'unico
che numera gli `_id` è `DataGenerator.documento`, cioè `mongolab workload`, che ha la propria
collezione per corsa e la conserva ([ADR-0106](../../docs/Decision.md#adr-0106)).

Il che dà anche il criterio per la pulizia: `{_id: {$type: "objectId"}}` seleziona ciò che ha
scritto l'applicazione. `tools/reset-demo.sh` lo conta prima che il seed ricostruisca la collezione,
perché un residuo silenzioso è un residuo che qualcuno prima o poi attribuirà al seed.

### Perché gli arrivi e non i totali

```
sharded     shard1rs          17047 documenti (50%) · 1 chunk
arrivati    shard1rs 2507 (50%) · shard2rs 2493 (50%)
```

Due righe che dicono cose diverse, e la seconda è quella della scena. `lab.ordini` contiene già i
ventimila del seed, e accostare duemila a ventiduemila non confronta niente.

Non è una raffinatezza. Misurato sui totali, una corsa finita per l'ottanta per cento su un solo
shard risultava sbilanciata di **tre centesimi di punto**: la schermata avrebbe dichiarato un
equilibrio perfetto mentre il carico era tutto da una parte. Il seed diluisce qualunque squilibrio,
e una misura che non può smentire la tesi non la sta verificando.

Per la stessa ragione `sbilancio` è `None` — e non zero — quando non c'è nessun arrivo: «niente da
ripartire» non è «distribuiti alla perfezione», ed è precisamente ciò che si vede se il carico
fallisce del tutto, cioè il momento in cui uno zero stampato mentirebbe con la faccia del successo.

---

## Il rifiuto degli altri due stack

`demo sharding` si ferma prima di connettersi se il bersaglio non è lo sharded cluster, e dice
**quale** delle due cose manca:

- su un mongod solo — «non ha shard fra cui ripartire niente, e `explain()` da lì non nomina nessuno
  shard perché non c'è nessun router che riparta la domanda»;
- su un replica set — «tre nodi con gli **stessi** dati, non tre shard con dati diversi. Non c'è
  nessun router a cui chiedere un piano».

Due messaggi e non uno: un messaggio unico costringerebbe chi lo legge a capire da sé quale metà lo
riguarda. È la stessa forma del rifiuto di [ADR-0098](../../docs/Decision.md#adr-0098) — arriva
prima della scena, non durante.

La prova che lo copre ha insegnato qualcosa sul modo di scrivere le asserzioni. Nella fase rossa
`test_su_un_replica_set_non_c_e_nessun_router_a_cui_chiedere` **passava**, perché il messaggio di
Typer per un comando inesistente — «No such command 'sharding'» — contiene la sottostringa `shard`.
Un'asserzione su `"shard"` è verde per il motivo sbagliato; le asserzioni sono quindi su
`"sharded cluster"`, `"--target sharded"` e `"router"`, e il commento accanto dice perché.

---

## Le prove

### La prova d'integrazione asserisce sui versi, non sui numeri

Quanti documenti finiscano su ciascuno shard lo decide una funzione hash, e pretendere una cifra
esatta renderebbe la prova capricciosa su un'altra macchina. Quello che il disegno garantisce è che
la collezione non distribuita finisca **tutta** su un solo shard e che quella distribuita ne veda
due, che è precisamente la tesi del Blocco 3:

```python
sola = _riga(uscita, NON_SHARDED)
assert int(sola.group("documenti")) == int(SCRITTURE_BLOCCO_3)

arrivi = QUANTI_ARRIVATI.findall(_riga(uscita, ARRIVATI).group("elenco"))
assert len(arrivi) == 2
assert sum(int(quanti) for _, quanti in arrivi) == int(SCRITTURE_BLOCCO_3)
assert all(int(quanti) > 0 for _, quanti in arrivi)
```

La riga del carico si verifica, e non è pedanteria: è l'invariante che ha fatto sostituire
`--carico` con `--scritture`, e qui c'è la riga che la tiene.

**`chunk 0 in più` non è un'asserzione di questa prova.** Che il balancer non migri è un fatto del
cluster e non del codice, e asserirlo qui vorrebbe dire una prova rossa il giorno in cui MongoDB
cambia politica, senza che niente si sia rotto.

### La pulizia distingue le due collezioni

```python
finally:
    if collezione is not None:
        stack03[DATABASE].drop_collection(collezione)
    stack03[DATABASE][COLLEZIONE].delete_many({"_id": {"$type": "objectId"}})
```

La collezione di carico si toglie intera; da `lab.ordini` si tolgono solo i documenti
dell'applicazione. Il nome della prima non si indovina — porta l'orario — e si ricava dalla riga che
la scena annuncia, che è la stessa formula `carico in lab.<nome>` delle altre due scene. Non è una
convenzione estetica: è la riga da cui chi presenta, e la prova, sanno che cosa togliere dopo.

### Lo stato delle suite

| Suite | Comando | Esito |
| --- | --- | --- |
| unitarie | `make app-test` | 619 verdi |
| tipi | `make app-check` | `Success: no issues found in 66 source files` |
| integrazione | `make app-test-integration` | verdi sui tre stack accesi |
| strumenti | `make tools-test` | verdi |

---

## Che cosa questo capitolo lascia aperto

**Il balancer non è stato visto migrare, e non lo sarà su questo stack.** La scena mostra i chunk
fermi e ne dà la ragione, che è didatticamente onesta ma non è una dimostrazione del balancer al
lavoro. Chi volesse vederlo migrare deve distribuire su una chiave crescente e aspettare: non è il
Blocco 3, ed è una scena che questo lab non ha.

**Il conteggio dei giri cresce da sé.** «1 153» è la fotografia di un istante e non un numero da
slide. Quello da slide è l'altro, ed è zero.

**`$shardedDataDistribution` dopo un arresto sporco può mentire.** Il manuale lo dichiara — «After
an unclean shutdown of a `mongod` using the Wired Tiger storage engine, size and count statistics
reported by `$shardedDataDistribution` may be inaccurate» — e la scena del guasto fa esattamente un
`docker kill`. Va detto dal palco invece di essere scoperto.

**Senza permessi su `config` il primario resta ignoto**, e una `Distribuzione` senza primario si
legge come «non è uno sharded cluster». È la stessa degradazione che c'era prima di ADR-0104,
ristretta a un caso che questo laboratorio non incontra, e preferita a un quarto stato che
esisterebbe solo per descrivere un permesso che manca.

---

**Da leggere prima:** [09-adattatori-veri-e-contratto-condiviso.md](09-adattatori-veri-e-contratto-condiviso.md),
di cui questo capitolo corregge due sezioni, e
[03-eventi-immutabili.md](03-eventi-immutabili.md), da cui un evento è uscito.

**Decisioni correlate:** [ADR-0103](../../docs/Decision.md#adr-0103) (`ChunkMigrated` esce dal
dominio), [ADR-0104](../../docs/Decision.md#adr-0104) (la distribuzione diventa una risposta
strutturata), [ADR-0105](../../docs/Decision.md#adr-0105) (`QueryPlanner`, la settima porta),
[ADR-0106](../../docs/Decision.md#adr-0106) (il Blocco 3 carica `lab.ordini`),
[ADR-0107](../../docs/Decision.md#adr-0107) (il limite è un conteggio, e il blocco vuole lo sharded
cluster), [ADR-0108](../../docs/Decision.md#adr-0108) (un `ping` `NEAREST` prima della prima
fotografia), [ADR-0069](../../docs/Decision.md#adr-0069) (il balancer fonde e non migra),
[ADR-0064](../../docs/Decision.md#adr-0064) (la chiave hashed e i ventimila documenti),
[ADR-0088](../../docs/Decision.md#adr-0088) (il carico ha una collezione sua).

**Fonti:** [M-049](Sources.md#m-049), [M-050](Sources.md#m-050), [M-051](Sources.md#m-051),
[M-052](Sources.md#m-052), [M-053](Sources.md#m-053), [M-042](Sources.md#m-042),
[A-012](Sources.md#a-012), [A-013](Sources.md#a-013), [A-017](Sources.md#a-017), e la pagina
canonica [`docs/02-architetture/sharded-cluster.md`](../../docs/02-architetture/sharded-cluster.md),
di cui questo capitolo è la metà applicativa.
