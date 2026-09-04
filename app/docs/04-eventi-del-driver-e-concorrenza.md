# 4. Che cosa vede il client, e perché il listener deve tacere e uscire

> Il principio in una riga: **il driver ti parla sul suo thread, e ti aspetta.** Chi ascolta ha un
> solo dovere: depositare e ritornare.

> **Stato:** il codice che attua questo principio — `SdamBridge` — **esiste dal Task 7**, e
> [08-il-ponte-sdam-e-i-thread-del-driver.md](08-il-ponte-sdam-e-i-thread-del-driver.md) racconta
> com'è venuto. Quella pagina corregge anche un punto di questa: il driver non consegna tutti gli
> eventi sul thread che li ha generati ([M-014](Sources.md#m-014)). Resta vero, e più interessante,
> che il thread su cui il callback gira non è affar suo.

## La cosa che il talk vuole mostrare

La parte più difficile da raccontare di un failover non è quello che succede sul server. È quello
che vede **il client**.

Il server ha una storia lineare: un nodo cade, gli altri se ne accorgono, votano, uno diventa
primario. Il client ha una storia diversa e più interessante, perché per qualche secondo **la sua
idea del cluster è sbagliata**. Continua a mandare scritture a un indirizzo che non risponde più;
poi scopre che non risponde; poi non sa più chi sia il primario; poi lo riscopre. Fra il guasto e
l'elezione il cluster, agli occhi del client, non è rotto e non è sano: è in un terzo stato che
dura secondi e che il pubblico vede solo se qualcuno lo nomina.

Nel dominio di `mongolab` quel terzo stato ha un nome proprio,
`TipoTopologia.REPLICA_SET_SENZA_PRIMARIO`, ed è stato reso un valore di prima classe apposta. Un
enum che avesse solo «sano» e «rotto» avrebbe cancellato la scena.

## Perché PyMongo, e non `mongosh`

`mongosh` mostrerebbe il **risultato** del failover: prima c'era un primario, adesso ce n'è un
altro. Non mostrerebbe il suo svolgersi, perché non dà accesso agli eventi di topologia.

PyMongo sì. Espone cinque classi astratte di listener — `CommandListener`, `ServerListener`,
`ServerHeartbeatListener`, `TopologyListener`, `ConnectionPoolListener` — registrabili per singolo
client con `MongoClient(event_listeners=[...])` ([S-010](../../docs/Sources.md#s-010)). Tre eventi
bastano a cronometrare un failover:

- `ServerHeartbeatFailedEvent` — il momento esatto in cui il client si accorge della caduta;
- `ServerDescriptionChangedEvent` — «Published when server description changes»;
- `TopologyDescriptionChangedEvent` — «Published when the topology description changes».

È la ragione per cui il lab è scritto in Python
([ADR-0006](../../docs/Decision.md#adr-0006)): il failover diventa **cronaca in diretta** invece di
un'affermazione.

## La trappola, che sta nella stessa pagina

La documentazione di PyMongo dichiara anche una cosa che rovescia l'assunzione più naturale:

> «Events are delivered **synchronously**. Application threads **block** waiting for event handlers
> (e.g. `started()`) to return. Care must be taken to ensure that your event handlers are efficient
> enough to not adversely affect overall application performance.»
> — [S-010](../../docs/Sources.md#s-010)

Chi si aspettava che il driver consegnasse gli eventi su un thread suo, in modo asincrono, si
aspettava il contrario di quello che succede. Il codice del listener gira **dentro** il thread del
driver, e finché non ritorna, il driver aspetta.

La conseguenza per questo progetto è specifica e grave. Un listener che disegnasse una tabella Rich
non rallenterebbe soltanto l'interfaccia: **rallenterebbe il driver**, e falserebbe proprio le
misure di failover che la demo esiste per mostrare. Il numero mostrato in sala sarebbe il tempo di
disegno sommato al tempo di reazione, presentato come tempo di reazione.

C'è una seconda avvertenza sulla stessa pagina, utile a chi volesse registrare i comandi: «The
command documents published through this API are not copies.» Conservare il riferimento a un
documento che il driver riusa significa conservare qualcosa che cambierà sotto i piedi.

## La seconda lacuna, sull'altro lato

Rich offre un display che «will refresh 4 times a second» per impostazione predefinita, regolabile
con `refresh_per_second`, e permette di stampare sopra il display senza romperlo
([S-018](../../docs/Sources.md#s-018)).

Ma c'è un dettaglio che vale la pena conoscere, e che il repository ha registrato come **riserva
dichiarata** invece che risolvere con un'ipotesi: la documentazione di Rich **non contiene la parola
«thread»**, né nella pagina di `Live` né nel riferimento dell'API. Non esiste alcuna indicazione
documentata sull'aggiornamento di `Live` da più thread — né che sia sicuro, né che non lo sia.

Questa è una lacuna, non una risposta. E il progetto non ci si appoggia in nessuna delle due
direzioni.

## La decisione, che chiude entrambe con una mossa

Due lacune scoperte separatamente, una soluzione sola
([ADR-0019](../../docs/Decision.md#adr-0019)):

> Il listener costruisce un evento immutabile, lo deposita in una `queue.Queue` e **ritorna**. Il
> ciclo di disegno gira sul thread principale, svuota la coda a ogni giro e aggiorna `Live`.

```
  thread del driver                    coda                 thread principale
 ┌──────────────────┐          ┌────────────────┐        ┌──────────────────┐
 │ ServerHeartbeat  │          │                │        │  svuota la coda  │
 │  FailedEvent     │──emit──▶ │  queue.Queue   │ ──────▶│  aggiorna Live   │
 │ costruisci +     │          │  (eventi       │        │  (un solo thread │
 │ deposita, esci   │          │   congelati)   │        │   tocca Rich)    │
 └──────────────────┘          └────────────────┘        └──────────────────┘
   tempo speso qui:                                        tempo speso qui:
   un inserimento in coda                                  quanto serve
```

Che cosa risolve, punto per punto:

**Il driver non viene rallentato.** Il tempo trascorso dentro il listener è quello di un inserimento
in coda. Le misure restano oneste, perché il misuratore non pesa più della cosa misurata.

**La domanda non documentata su Rich non si pone.** Un solo thread tocca `Live`. Non serve una
risposta a una domanda che non ci si mette nella condizione di fare — ed è una mossa che vale la
pena riconoscere: di fronte a una lacuna nella documentazione, invece di indovinare, si cambia il
disegno finché la lacuna diventa irrilevante.

**La coda diventa il punto naturale dove intercettare gli eventi.** Volendo registrarli su file per
le registrazioni di riserva ([ADR-0050](../../docs/Decision.md#adr-0050)), il posto c'è già.

Le alternative scartate sono istruttive quanto la decisione. Disegnare direttamente nel listener
falsa le misure, ed è il difetto per cui la documentazione di PyMongo mette in guardia per primo.
Proteggere `Live` con un lock difenderebbe da un rischio che la documentazione non descrive, e
serializzerebbe comunque il driver dietro il disegno — cioè pagherebbe il prezzo del problema che
voleva evitare.

## Che cosa questo impone al codice, in concreto

La decisione si traduce in vincoli che attraversano tutto il progetto, e che è utile riconoscere
mentre si legge il codice.

**Gli eventi sono `frozen=True, slots=True`.** Non è gusto: se l'oggetto in coda fosse mutabile, la
coda tornerebbe a essere condivisione di stato fra thread e servirebbe il lock che ADR-0019 ha
deciso di non mettere. Il dettaglio, con le misure, sta in
[03-eventi-immutabili.md](03-eventi-immutabili.md).

**`EventSink.emit` non deve bloccare.** Sta scritto nella docstring della porta, perché è lì che lo
legge chi ne scrive un'implementazione. Un sink che ha bisogno di tempo — disegnare, scrivere su
disco — mette in coda e lascia che sia il proprio ciclo a spendere quel tempo.

**`refresh_per_second` si dichiara.** Il valore predefinito di Rich è documentato, ma un valore
predefinito che nessuno ha scelto è un valore che nessuno può difendere quando in sala qualcuno
chiede perché l'interfaccia si aggiorna così.

**L'istante arriva dal `Clock`, non da `time.time()`.** Se il tempo entra dalla porta, la cronaca
del failover si può riprodurre in una prova che dura un battito di ciglia.

## La coda, e perché è lei a tenere i lucchetti

ADR-0019 nomina `queue.Queue` senza spiegare perché quella e non una lista con un `Lock` intorno. La
ragione sta nella prima riga della documentazione del modulo: «It is especially useful in threaded
programming when information must be exchanged safely between multiple threads. The `Queue` class in
this module implements all the required locking semantics» ([A-010](Sources.md#a-010)).

Il punto non è che la coda sia più veloce: è che **il lucchetto sta dentro di lei**. Nel codice
dell'applicazione non compare nessun `Lock`, e quindi non c'è nessun ordine di acquisizione da
ricordare, nessun `finally` che rilascia, nessun percorso in cui un'eccezione lascia chiuso qualcosa.
Un lock scritto a mano intorno a una lista farebbe la stessa cosa e aprirebbe tutte quelle domande.

La stessa pagina aggiunge un avvertimento che qui vale come regola: «they are not designed to handle
reentrancy within a thread». Tradotto in questo disegno: **un `emit` non deve mai rimettere in coda**.
Il sink gira nel thread che drena, e un sink che ripubblicasse mentre viene drenato sarebbe
esattamente il caso che il modulo dichiara di non gestire.

### Lo stesso schema, un livello più in basso

Dal Task 5 la disciplina non è più solo sul confine col driver: `WorkloadRunner` la applica ai propri
scrittori. I worker del `ThreadPoolExecutor` non chiamano `EventSink.emit`, pubblicano in coda; il
thread chiamante drena e chiama `emit`. Il sink resta un oggetto a thread singolo per costruzione,
non per convenzione.

Con una differenza che il caso del driver non ha: qui la corsa **finisce**, e il ciclo di drenaggio
deve saperlo. Ogni worker mette in coda un `None` come ultimo gesto, dentro un `finally`, e il
chiamante conta le sentinelle. Spostando quel `put` fuori dal `finally`, la suite non fallisce: si
pianta ([M-010](Sources.md#m-010)). Il dettaglio sta in
[06-carico-tentativi-e-latenze.md](06-carico-tentativi-e-latenze.md).

La riserva è la stessa in entrambi i casi, ed è dichiarata: con `maxsize=0` la coda è illimitata, e
un produttore che corra più del consumatore la fa crescere in memoria finché non finisce. Alle scale
della demo — secondi, migliaia di eventi — non è un problema; la sede in cui si guarderà è il
Task 16.

## Che cosa non è ancora verificato

Questa sezione diceva, fino al Task 7, che tutto quanto sopra era **deciso e documentato** e non
ancora **misurato qui**. Metà di quel debito è stata pagata, e conviene essere precisi su quale.

**Misurato.** Da quale thread arriva ciascuna famiglia di eventi ([M-014](Sources.md#m-014)), in
che unità sono le durate — con un errore trovato nella documentazione di PyMongo
([M-012](Sources.md#m-012)) — che fine fa un'eccezione sollevata dentro un listener
([M-015](Sources.md#m-015)), e quanto costa davvero un callback che disobbedisce
([M-013](Sources.md#m-013)). Le sedi sono `Sources.md` e
[08](08-il-ponte-sdam-e-i-thread-del-driver.md), come promesso: nessuna riga di codice ha aggirato
niente in silenzio.

**Non ancora misurato.** Niente di tutto questo ha parlato con un cluster: i client delle prove
nascono con `connect=False`. Un battito che fallisce mentre il primario cade, e il
`ServerStateChanged` verso `PRIMARIO` che arriva su un altro nodo, nessuno li ha ancora visti
arrivare. La sede è il **Task 8**, contro gli stack veri.

**Il dubbio segnalato qui si è chiuso al Task 15, e non nel modo previsto.** `ChunkMigrated` era
l'unico dei nove eventi che potesse risultare **non osservabile dal client**: un client parla con
`mongos`, e la migrazione di un chunk è una faccenda fra shard e config server. Non è
l'osservabilità ad aver deciso. È che la migrazione **non accade**: la chiave hashed di
`lab.ordini` sparpaglia i documenti all'inserimento, i due shard restano a un chunk e a metà dei
documenti ciascuno, e in 1 153 giri di balancer `config.changelog` non ha una sola voce
`moveChunk` — due fusioni, zero migrazioni ([M-049](Sources.md#m-049)). L'evento è uscito dal
dominio ([ADR-0103](../../docs/Decision.md#adr-0103)) invece di restare il campo morto che questa
pagina si era impegnata a non lasciare.

---

**Da leggere dopo:** [05-tipi-prove-e-guardie.md](05-tipi-prove-e-guardie.md), che spiega come si
verifica tutto questo senza aspettare che accada, e
[08-il-ponte-sdam-e-i-thread-del-driver.md](08-il-ponte-sdam-e-i-thread-del-driver.md), che è
questa decisione diventata codice.

**Fonti:** [S-010](../../docs/Sources.md#s-010), [S-018](../../docs/Sources.md#s-018),
[A-010](Sources.md#a-010), [M-010](Sources.md#m-010), [M-012](Sources.md#m-012),
[M-013](Sources.md#m-013), [M-014](Sources.md#m-014), [M-015](Sources.md#m-015).
**Decisioni:** [ADR-0006](../../docs/Decision.md#adr-0006),
[ADR-0007](../../docs/Decision.md#adr-0007), [ADR-0019](../../docs/Decision.md#adr-0019),
[ADR-0050](../../docs/Decision.md#adr-0050).
