# 15. Il backup a caldo, e la finestra che misura se stessa

> Il principio in una riga: **una media si può diluire fino a nascondere qualsiasi cosa.** Se la
> finestra di misura è più larga dell'evento da misurare, il numero che esce è vero e non dice
> niente. Tutto l'Atto III è costruito perché la seconda finestra sia esattamente lunga quanto il
> dump.

Questo è l'Atto III del Blocco 2: quattro minuti, `mongodump` che gira **mentre il carico
scrive**, e in fondo due ritmi accostati. Poi il restore della copia accanto all'originale, e la
differenza fra i due conteggi — che non è un errore, è il prezzo di non aver fermato il servizio.

La misura contro lo stack vero è [M-047](Sources.md#m-047): **prima 595/s, durante 692/s**, 279
scritture nella finestra del dump, tutte confermate, e nella copia **3 802 documenti su 3 908**.
Il capitolo racconta perché quei numeri hanno la forma che hanno, e le tre volte in cui la strada
più corta era sbagliata.

---

## L'impossibilità che detta la forma

Il Task 9 aveva già lasciato scritto che nell'immagine dell'applicazione `mongodump` non c'è
([M-039](Sources.md#m-039)), e la pagina precedente aveva chiuso elencando «`mongodump`
nell'immagine» fra le decisioni del Task 14. La decisione è stata presa provando.

Un `Dockerfile` a due stadi che copia i due binari dall'immagine `mongo` pinnata dentro quella
`python` pinnata **si costruisce senza un avviso**. Poi il container si ferma alla prima
esecuzione:

```text
mongodump: error while loading shared libraries: libgssapi_krb5.so.2:
cannot open shared object file: No such file or directory
```

Uscita **127** ([M-044](Sources.md#m-044)). I due strumenti non sono binari statici: sono compilati
contro le librerie Kerberos del sistema su cui l'immagine `mongo` è costruita, e `python:3.13-slim`
è slim proprio perché non le ha. Il guasto non arriva al `build` — che sarebbe il momento buono —
ma alla prima esecuzione, cioè il peggiore.

Le altre tre strade sono state scartate senza provarle, e vale la pena dire perché, perché ognuna
avrebbe disfatto una decisione già presa:

| strada | perché no |
|---|---|
| `apt-get install mongodb-database-tools` | aggiunge all'immagine un pacchetto che nessun `FROM` dichiara, e `check_stack.py` verifica esattamente questo ([ADR-0093](../../docs/Decision.md#adr-0093)); richiede rete al `build`, che il lab offline non ha |
| socket Docker nel container | rovescia la decisione che ha fatto nascere la sesta porta: chi fa accadere le cose nei container non è l'applicazione ([ADR-0095](../../docs/Decision.md#adr-0095)) |
| volume condiviso host↔nodo | non risolve niente: il dump sopravvive nel filesystem del nodo fra i due comandi, che è tutto ciò che serve |

Resta quella giusta, e ha una simmetria che la rende difendibile: **gli strumenti stanno dove sono
già**. Il comando entra nel nodo con `docker compose exec`, e la riga la costruisce
`ComandiCompose.dentro`, che esisteva dal Task 12 per la regia del failover. È
[ADR-0100](../../docs/Decision.md#adr-0100).

## Un indirizzo che il client non userebbe mai

Da qui nasce la cosa meno intuitiva di tutto il capitolo. L'applicazione gira **sull'host** e parla
con `localhost:27021`; `mongodump` gira **dentro `mongo-rs-1`** e da lì `localhost:27021` non
esiste. Le due metà della stessa scena hanno due indirizzi diversi per lo stesso cluster, e la
radice di composizione deve saperli tutti e due.

```python
def host_interno_di(bersaglio: Bersaglio) -> str:
    vista = bersaglio.da_rete
    elenco = ",".join(f"{nome}:{porta}" for nome, porta in vista.semi)
    return f"{vista.replica}/{elenco}" if vista.replica is not None else elenco
```

Il risultato è `rs0/mongo-rs-1:27017,mongo-rs-2:27017,mongo-rs-3:27017`, ed è il `--host` di
`mongodump`. Il `Bersaglio` aveva già le due viste dal Task 13, per una ragione diversa — un
container che parla con la rete e un processo dell'host che parla con le porte pubblicate — e qui
servono **contemporaneamente**, nello stesso comando, per la prima volta.

Il nome del set davanti alla lista non è ornamentale: senza, `--oplog` non è accettato. Con,
funziona, e la misura che lo dice è [M-045](Sources.md#m-045) — exit 0, `dumped 72 oplog entries`,
**476 / 446 / 404 ms** in tre esecuzioni.

Della stessa famiglia è una cosa da non fraintendere leggendo il rapporto: `/tmp/mongolab-backup` è
un percorso **nel filesystem di `mongo-rs-1`**, non dell'host. Chi va a cercarlo sul portatile non
lo trova, e non è un guasto.

### Il nodo predefinito è il primo, non il primario

```python
def _nodo_degli_strumenti(bersaglio: Bersaglio, detto: str | None) -> str:
    nodo = detto if detto is not None else servizi_di(bersaglio)[0]
    _controlla_nodo(nodo, bersaglio)
    return nodo
```

Un predefinito che seguisse il primario sembrerebbe più intelligente ed è la trappola: il dump
atterra nel filesystem del nodo in cui gira, e `demo restore` deve ritrovarlo lì qualche minuto
dopo. Dopo l'Atto II il primario è cambiato — la copia starebbe in un container e il restore la
cercherebbe in un altro, con un messaggio di errore che non nomina la vera causa.

## La finestra della seconda misura è quella del dump

Ecco il cuore, ed è aritmetica, non architettura. Il `mongodump` della collezione della demo dura
**476 ms**. Se la fase «durante» durasse i venti secondi che uno sceglierebbe a tavolino, il dump
occuperebbe il due per cento del campione, e **un crollo totale del throughput per tutta la durata
del dump comparirebbe come un calo del due per cento**. La promessa del copione — «il dump non fa
crollare il throughput» — risulterebbe verificata da una misura incapace di smentirla.

Quindi la fase deve finire quando finisce il dump. `WorkloadRunner.esegui` ha imparato un parametro
nuovo:

```python
def esegui(
    self,
    scritture: int | None = None,
    *,
    durata_s: float | None = None,
    finche: Continua | None = None,
    ...
) -> Riepilogo:
```

`finche` **si somma** al limite invece di sostituirlo, e il verso conta: la condizione è il limite
vero — la corsa finisce quando il dump finisce — e `durata_s` resta la rete di sicurezza che fa
terminare la scena anche se il dump non torna più. Il metodo rifiuta di ricevere `finche` da sola:

```python
if finche is not None and scritture is None and durata_s is None:
    raise ValueError(
        "`finché` restringe un limite, non ne fa le veci: una condizione che "
        "dipende da un processo esterno resta vera per sempre se quel processo "
        "si pianta. Va data insieme a `scritture` o a `durata_s`, che è il tetto."
    )
```

Un'eccezione e non un valore predefinito silenzioso, perché il caso che rovina la scena è
esattamente quello: `mongodump` che si pianta, la condizione che resta vera, e uno schermo fermo
davanti a duecento persone. La decisione è [ADR-0101](../../docs/Decision.md#adr-0101); il tetto
predefinito è `TETTO_DUMP_S` e si sposta con `--tetto`.

Il copione dell'Atto III, di conseguenza, **non ha** il parametro `scritture` che il copione del
failover ha:

```python
@dataclass(frozen=True, slots=True)
class CopioneBackup:
    destinazione: Path
    carico_s: float = DURATA_CARICO_S
    tetto_s: float = TETTO_DUMP_S
    intervallo_ms: float = INTERVALLO_PREDEFINITO_MS
```

Delle due fasi una sola potrebbe limitarsi a conteggio, e un parametro che vale per metà scena è un
parametro che qualcuno userà per l'altra metà.

### Chi sta su quale thread, e perché due e non tre

Il carico va sul pool, come in `ScenarioFailover`. Il dump resta sul **thread chiamante**, che lo
consuma avanzamento per avanzamento e fra uno e l'altro drena il ponte SDAM. Sono due e non tre
perché il dump *è* un iteratore: consumarlo è già un ciclo, e metterlo su un thread suo vorrebbe
dire aggiungere una coda per riportare qui gli avanzamenti che il thread chiamante ha già in mano.

Una riga sola tiene in piedi il caso brutto:

```python
try:
    for avanzamento in self._strumento.dump(self._copione.destinazione):
        ...
finally:
    finito.set()
```

Lo spegnimento sta nel `finally` e non dopo il ciclo. Se il dump solleva — un `mongodump` che esce
con uno, cioè `ComandoFallito` — il carico deve fermarsi **prima** che l'eccezione risalga. Senza,
l'uscita dal `with` aspetterebbe il pool, il pool aspetterebbe il tetto, e l'errore arriverebbe a
chi l'ha causato cinque minuti dopo il fatto.

## Il calo ha il segno, e il segno è il punto

La prima riga del rapporto contro lo stack vero è questa:

```text
ritmo       prima 595/s · durante 692/s · calo -16.2%
```

Un calo **negativo**: il ritmo è salito. Non è un errore di calcolo, ed è la ragione per cui
`_percentuale` scrive il segno invece di concludere. La finestra del dump è mezzo secondo, e su
mezzo secondo il rumore pesa più del costo del dump.

Sarebbe stato facile scrivere «il dump non ha impatto» e avere ragione quel giorno. La docstring di
`copia` dice perché no:

> **Il calo è una percentuale con segno, non un giudizio.** Questa funzione non scrive «il dump non
> ha impatto»: scrive di quanto è calato, e chi guarda decide se è poco. Una riga che concludesse al
> posto del pubblico sarebbe la stessa cosa che il §6.3 rimprovera ai benchmark altrui.

I numeri da leggere sono quelli assoluti che le stanno accanto — 3 629 scritture prima, 279 durante,
zero rifiutate, p95 da 66,3 a 68,7 ms. La percentuale cambia a ogni giro, e su una slide non ci va.

C'è anche una ragione **misurata** per cui il primario non se ne accorge, e non è fortuna. Contando
`serverStatus().opcounters.query` sui tre membri prima e dopo lo stesso dump: senza
`--readPreference` il primario prende **+15** letture; con `--readPreference=secondary` ne prende
**+0**, e le quindici si spostano sui due secondari, +7 e +8 ([M-046](Sources.md#m-046)). La misura
chiude un punto che `docs/03-amministrazione/backup-restore.md` si era lasciato aperto dai tempi di
`feature/02`, dove era annotato come «probabilmente la prima cosa da fare in produzione, e non è
stata misurata».

## Due guardie nuove, e un'asimmetria voluta

`demo failover` gira **dentro la rete** e dall'host si rifiuta. `demo backup-live` e `demo restore`
fanno l'esatto contrario. Sono due comandi della stessa applicazione, nella stessa scaletta, con
requisiti opposti, e il motivo per ciascuno è diverso: il failover ha bisogno che il driver veda la
topologia intera, il backup ha bisogno del client Docker che nel container non c'è.

Non nasconderlo è una scelta. Il messaggio di rifiuto nomina la variabile e detta la riga giusta:

```python
def _solo_dall_host(scena: str) -> None:
    ...
    param_hint=VARIABILE_PUNTO_DI_VISTA
```

La seconda guardia rifiuta gli altri due stack, e lo fa **sulla proprietà** e non sul nome:

```python
def _solo_da_un_replica_set(bersaglio: Bersaglio) -> None:
    if bersaglio.da_rete.replica is not None:
        return
    if bersaglio.da_rete.diretto:
        raise typer.BadParameter(...)   # un mongod solo: nessun oplog
    raise typer.BadParameter(...)       # un mongos: nessun istante comune
```

`bersaglio.nome != "rs"` avrebbe funzionato oggi e sarebbe stato sbagliato domani: il giorno in cui
il repository avesse un secondo replica set, questa riga funziona da sé. E le due forme di rifiuto
sono due lezioni diverse, non una sola — su uno standalone l'oplog **non c'è**
([ADR-0022](../../docs/Decision.md#adr-0022)); attraverso un `mongos` c'è, ma un dump preso da lì
attraversa gli shard uno per uno **senza un istante comune**, che è un'altra cosa e va detta con
altre parole.

### Un `ping` che riesce e non basta

Dall'host si arriva a un nodo solo, con `directConnection`. Il driver non sceglie: parla con quello
pubblicato. Se dopo l'Atto II quel nodo è ancora un secondario, `attendi_il_primario` — che fa
`admin.command("ping")` — **riesce lo stesso**, perché la lettura è ammessa. Il guasto comparirebbe
alla prima scrittura, con il carico già partito e la collezione a metà.

Quindi c'è un controllo esplicito in più, dopo il `ping` e prima del carico:

```python
if not ispettore.topology().ha_primario:
    raise _serve_il_primario(target)
```

Il rimedio quasi sempre è **aspettare**: `mongo-rs-1` ha `priority: 2` e si riprende il ruolo da sé.
Quanto ci mette è [M-048](Sources.md#m-048): **4,0 secondi**. È un dato di scaletta, non di codice —
fra l'Atto II e l'Atto III il presentatore ha quattro secondi da riempire, e ora lo sa.

## Il restore scrive accanto, e mai sopra

```text
restore     3908 all'origine · 3802 nella copia · differenza 106
            /tmp/mongolab-backup → lab_ripristinato
            106 scritti mentre il dump era in corso: stanno nell'oplog, che il
            restore non riapplica
```

La destinazione predefinita è `lab_ripristinato`, e `--into lab` viene rifiutato. La ragione è più
sottile del riflesso «non sovrascrivere i dati»: i 106 documenti che alla copia mancano **sono
ancora nell'originale**. Un restore sopra `lab` li lascerebbe dove sono, i conteggi
combacerebbero, e la differenza sparirebbe *proprio perché* il restore è riuscito. La scena
mostrerebbe zero e insegnerebbe il contrario di quello che deve insegnare. È
[ADR-0102](../../docs/Decision.md#adr-0102).

Restaurare accanto costa la coda dell'oplog, ed è un costo dichiarato: `--oplogReplay` non convive
con la rinomina dei namespace — `cannot use --oplogReplay with namespace renames specified`, uscita
1 ([M-024](Sources.md#m-024)) — e la rinomina serve proprio a scrivere altrove. Il dump ha portato
via l'oplog (`dumped 72 oplog entries`), ma il restore non lo riapplica. Dei 279 documenti scritti
nella finestra del dump, 173 sono entrati nella copia e 106 no: la fotografia è stata scattata
mentre la scena si muoveva.

`EsitoRestore` chiama quel numero **differenza** e non «perse», e la docstring spiega perché la
parola conta:

> Le scritture perse sono la voce del Blocco 2, e sono un'altra cosa: là il client aveva ricevuto
> una conferma e il documento non c'era più. Qui i documenti ci sono ancora, tutti, nel database di
> partenza: mancano **nella copia**.

Usare la stessa parola per i due fenomeni sarebbe l'errore più costoso possibile, perché arriverebbe
nel momento in cui la sala sta imparando la differenza.

### La riga successiva la detta la scena precedente

La collezione di carico ha la data nel nome — `carico-20260904-115619` — e non si indovina.
Ricopiarla a mano davanti alla sala è il modo più prevedibile di sbagliare un comando, quindi
`demo backup-live` stampa come ultima riga quella da incollare:

```text
prossimo: mongolab demo restore --target rs --from /tmp/mongolab-backup --collection carico-20260904-115619
```

Costa sei righe di codice e toglie dalla scaletta l'unico punto in cui serviva copiare a mano.

## Le prove, e le due lezioni che hanno insegnato

### La prova d'integrazione è stata vista rossa

`test_l_atto_iii_esce_dallo_stack_vero` lancia le due scene **come un umano**: `mongolab` da riga di
comando, dall'host, e legge il testo che esce. Una prova del genere passa alla prima esecuzione e
lascia il dubbio di non provare niente. Quindi è stata rotta apposta: `dove=None` in `strumento_di`,
cioè il comando `docker compose` eseguito dalla directory sbagliata.

```text
open /Users/.../app/docker/02-replicaset/compose.yaml: no such file or directory
```

Rossa, con il messaggio giusto. Poi ripristinata. Il messaggio è riportato **verbatim** nella
docstring della prova, perché sapere come si presenta il guasto vale quanto sapere che la prova lo
prende.

### La pulizia deve sopravvivere al fallimento

La prima stesura del helper faceva così:

```python
def _dall_host(*argomenti: str) -> str:
    esito = subprocess.run(...)
    esito.check_returncode()   # ← qui
    return esito.stdout
```

Sembra corretto, e lascia spazzatura. Il nome della collezione di carico lo annuncia la scena, sulla
sua prima riga di output: se il helper solleva prima di restituire il testo, il chiamante non ha mai
saputo che collezione pulire — e la scena l'aveva già creata e riempita. **Il fallimento è
esattamente il caso in cui la pulizia serve di più.**

La versione buona restituisce `tuple[int, str]` e non solleva mai; il chiamante estrae il nome
della collezione dall'output, e **solo dopo** asserisce sul codice di uscita.

### Lo stato delle suite

```text
pytest -q                    582 passed
mypy                         Success: no issues found in 64 source files
pytest tests/integration     49 passed in 85.39s
make docs-check              Citazioni coerenti · Collegamenti coerenti
```

Fra le integrazioni, `test_container.py::test_dentro_la_rete_il_replica_set_ha_un_primario` è
fallita **una volta** durante il lavoro, con `mongo-rs-3 sconosciuto` e `mongod attivo da 1 m 14 s`.
Rieseguita da sola: quattro passate. Rieseguita l'intera suite da uno stack assestato: 49 passate.
Era la scia dei failover fatti a mano poco prima — la scoperta SDAM incompleta in un container
appena avviato — e non un difetto del Task 14. Vale la pena averlo scritto: una prova che fallisce
una volta e poi passa è una prova da spiegare, non da rieseguire finché non tace.

## Che cosa questo capitolo lascia aperto

- **Le due scene girano solo dall'host e solo su `rs`.** È l'inverso di `demo failover`, e in sala
  significa cambiare terminale fra l'Atto II e l'Atto III. Va nella scaletta, non scoperto la sera
  prima.
- **Fra Atto II e Atto III ci sono quattro secondi** in cui il primario torna al suo posto
  ([M-048](Sources.md#m-048)). Sono misurati dopo una scena che comprende già cinque secondi di
  recupero: a freddo il tempo è presumibilmente più lungo, e la prova concede sessanta secondi
  proprio per questo.
- **`--readPreference=secondary` è misurato una volta sola**, e la distribuzione fra i due secondari
  (7 e 8) non la governa niente di dichiarato: è la selezione del driver degli strumenti, e su
  un'altra macchina può cadere diversamente.
- **Il dump non esce dal nodo.** `/tmp/mongolab-backup` vive dentro `mongo-rs-1` e sparisce con lui.
  Dove vada una copia vera, con quale rotazione e quale cifratura, questo repository non lo decide —
  ed è la stessa lacuna che dichiara la pagina dei backup.
- **Non c'è una prova che il dump fallito si comporti bene in scena.** Il `finally` che ferma il
  carico è provato con i doppi; che davanti a un `mongodump` che esce con uno lo schermo dica la
  cosa giusta entro un secondo è ragionato e non misurato.

---

**Decisioni correlate:** [ADR-0100](../../docs/Decision.md#adr-0100) (gli strumenti restano nei
nodi, e l'Atto III si gira dall'host), [ADR-0101](../../docs/Decision.md#adr-0101) (la finestra
della seconda misura è quella del dump), [ADR-0102](../../docs/Decision.md#adr-0102) (il restore
scrive accanto all'originale, mai sopra),
[ADR-0084](../../docs/Decision.md#adr-0084) (un restore che perde documenti non è riuscito),
[ADR-0054](../../docs/Decision.md#adr-0054) (la password non passa da `argv`),
[ADR-0093](../../docs/Decision.md#adr-0093) (le immagini pinnate, che chiudono una delle strade),
[ADR-0095](../../docs/Decision.md#adr-0095) (la sesta porta: chi fa accadere il guasto non sta
dove lo scenario guarda, e non è l'applicazione),
[ADR-0022](../../docs/Decision.md#adr-0022) (il paradosso del backup a caldo su un mongod solo).

**Fonti:** [M-019](Sources.md#m-019), [M-024](Sources.md#m-024), [M-025](Sources.md#m-025),
[M-039](Sources.md#m-039), [M-040](Sources.md#m-040), [M-044](Sources.md#m-044),
[M-045](Sources.md#m-045), [M-046](Sources.md#m-046), [M-047](Sources.md#m-047),
[M-048](Sources.md#m-048), e la pagina canonica
[`docs/03-amministrazione/backup-restore.md`](../../docs/03-amministrazione/backup-restore.md), di
cui questo capitolo è la metà applicativa.
