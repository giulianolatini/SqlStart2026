"""Il ponte fra i listener SDAM di pymongo e gli eventi del dominio.

**Ogni callback fa tre cose: costruisce un evento congelato, lo deposita in coda,
ritorna.** Non è uno stile: è il vincolo dell'[ADR-0019](../../../../docs/Decision.md#adr-0019),
e la ragione la scrive la documentazione di pymongo — «Events are delivered
synchronously. Application threads block waiting for event handlers … to return».

Quella frase, misurata su pymongo 4.17, vale **per due dei quattro** ascoltatori, e per
i due in cui pesa di più. `publish_server_heartbeat_*` lo chiama il monitor dritto per
dritto (`synchronous/monitor.py`, righe 271, 306, 334): il thread che si ferma dentro
`AscoltatoreHeartbeat` è quello che deve accorgersi che il primario è caduto, e un
listener lento allunga il failover che il talk sta cronometrando **mentre** lo
cronometra. I comandi arrivano allo stesso modo, dal thread che ha appena scritto.

Gli altri due — server e topologia — passano da `self._events.put(...)` e li consegna un
thread di nome `pymongo_events_thread` (`synchronous/topology.py`, riga 201). Il driver,
per metà dei suoi listener, fa esattamente quello che l'ADR-0019 ha scelto di fare per
tutti e quattro: una `queue.Queue` e qualcuno che la svuota. Non è un motivo per
rilassare la regola, per due ragioni misurate. La prima è che quel thread è uno solo, e
un listener che ci si siede dentro tiene ferma la cronaca di **tutti** i server. La
seconda è che il thread cambia: alla chiusura del client, `Topology.close()` svuota
quella coda sul thread di chi ha chiamato `close()`, e lo stesso metodo che un istante
prima girava su `pymongo_events_thread` si trova a girare sul `MainThread`.

**Corollario, e vale come regola:** un callback SDAM non può fare ipotesi su chi lo
chiama. Qui non ne fa nessuna, perché non tocca niente che non sia la coda.

**Quattro classi, non una.** `ServerListener` e `TopologyListener` dichiarano metodi con
lo stesso nome — `opened`, `closed`, `description_changed` — e pymongo smista con
`isinstance`: un oggetto che ereditasse da tutte e due finirebbe in due elenchi e si
vedrebbe arrivare due specie di evento sullo stesso metodo. Il §6.3 del design chiedeva
quattro classi; la firma delle classi base dice che non ce n'erano altre.

**Il ponte non ricorda niente.** Che cosa sia cambiato glielo dice il driver, con
`previous_description` e `new_description`, e non c'è un solo campo che due callback
concorrenti possano contendersi. L'unico stato condiviso è la `queue.Queue`, che è già
sincronizzata: è per questo che qui non compare nessun lucchetto, e la
[ADR-0019](../../../../docs/Decision.md#adr-0019) aveva scartato proprio l'alternativa
di metterne uno intorno al `Live` di Rich.

**Che cosa il ponte legge del driver, lo dicono dei `Protocol`.** Non è astrazione per
gusto: i callback sono tipizzati con questi `Protocol` invece che con le classi di
pymongo, e così la mappatura si prova costruendo a mano quattro campi in croce, senza un
`mongod` e senza un driver vivo. Il controllo che la classe vera abbia davvero quella
forma non si perde — anzi, diventa più stretto: sovrascrivere un callback con un
parametro **più largo** obbliga `mypy --strict` a verificare che
`ServerDescriptionChangedEvent` soddisfi `CambioServerDelDriver`. Il giorno in cui
pymongo rinominasse un attributo, a fallire sarebbe `make app-check`, non la
dimostrazione.
"""

import queue
from collections.abc import Collection, Mapping
from typing import Final, Protocol

from pymongo import monitoring

from mongolab.domain.eventi import (
    Evento,
    LatencySampled,
    ServerStateChanged,
    TopologyChanged,
)
from mongolab.domain.modelli import (
    DescrizioneServer,
    DescrizioneTopologia,
    RuoloServer,
    TipoTopologia,
)
from mongolab.domain.porte import Clock

__all__ = [
    "COMANDI_OSSERVATI",
    "FORME",
    "OPERAZIONE_BATTITO",
    "RUOLI",
    "AscoltatoreComandi",
    "AscoltatoreHeartbeat",
    "AscoltatoreSdam",
    "AscoltatoreServer",
    "AscoltatoreTopologia",
    "SdamBridge",
    "descrivi_server",
    "descrivi_topologia",
    "indirizzo_di",
    "ruolo_di",
]


# --------------------------------------------------------------------------------------
# La forma di ciò che il driver passa. Solo quel che si legge, niente di più.
# --------------------------------------------------------------------------------------


class DescrizioneServerDelDriver(Protocol):
    """Quattro attributi di `pymongo.server_description.ServerDescription`.

    `address` è `tuple[str, int | None]` e non `tuple[str, int]`: la porta di pymongo
    può mancare. Non è una precauzione, è una bocciatura di `mypy --strict` presa
    scrivendo questo file, e senza di essa un indirizzo sarebbe finito a schermo come
    `mongo-1:None`.
    """

    @property
    def address(self) -> tuple[str, int | None]: ...
    @property
    def server_type_name(self) -> str: ...
    @property
    def round_trip_time(self) -> float | None: ...
    @property
    def error(self) -> Exception | None: ...


class DescrizioneTopologiaDelDriver(Protocol):
    """La forma di `pymongo.topology_description.TopologyDescription`.

    `server_descriptions` restituisce un `Mapping` e non un `dict` perché `dict` è
    invariante nel tipo dei valori: dichiarato `dict`, questo `Protocol` non sarebbe
    soddisfatto dalla classe vera, che restituisce `dict[..., ServerDescription]`.
    """

    @property
    def topology_type_name(self) -> str: ...
    @property
    def replica_set_name(self) -> str | None: ...
    def server_descriptions(
        self,
    ) -> Mapping[tuple[str, int | None], DescrizioneServerDelDriver]: ...


class CambioServerDelDriver(Protocol):
    """La forma di `pymongo.monitoring.ServerDescriptionChangedEvent`."""

    @property
    def previous_description(self) -> DescrizioneServerDelDriver: ...
    @property
    def new_description(self) -> DescrizioneServerDelDriver: ...


class CambioTopologiaDelDriver(Protocol):
    """La forma di `pymongo.monitoring.TopologyDescriptionChangedEvent`."""

    @property
    def previous_description(self) -> DescrizioneTopologiaDelDriver: ...
    @property
    def new_description(self) -> DescrizioneTopologiaDelDriver: ...


class BattitoRiuscitoDelDriver(Protocol):
    """La forma di `pymongo.monitoring.ServerHeartbeatSucceededEvent`.

    `duration` è in **secondi**, malgrado la docstring del driver dica «in
    microseconds»: il monitor ci passa `max(0.0, time.monotonic() - inizio)`. Il
    conflitto fra documentazione e codice è registrato in `app/docs/Sources.md` (M-012).
    """

    @property
    def awaited(self) -> bool: ...
    @property
    def duration(self) -> float: ...


class ComandoRiuscitoDelDriver(Protocol):
    """La forma di `pymongo.monitoring.CommandSucceededEvent`.

    Qui `duration_micros` è davvero in microsecondi: il driver lo calcola con
    `_to_micros(timedelta)`. Due campi che si chiamano quasi allo stesso modo e hanno
    unità diverse, nella stessa libreria.
    """

    @property
    def command_name(self) -> str: ...
    @property
    def duration_micros(self) -> int: ...


# --------------------------------------------------------------------------------------
# La mappatura.
# --------------------------------------------------------------------------------------


RUOLI: Final[Mapping[str, RuoloServer]] = {
    "Unknown": RuoloServer.SCONOSCIUTO,
    "Standalone": RuoloServer.STANDALONE,
    "Mongos": RuoloServer.ROUTER,
    "RSPrimary": RuoloServer.PRIMARIO,
    "RSSecondary": RuoloServer.SECONDARIO,
    "RSArbiter": RuoloServer.ARBITRO,
    "RSOther": RuoloServer.ALTRO,
    "RSGhost": RuoloServer.ALTRO,
    "LoadBalancer": RuoloServer.ALTRO,
}
"""Dai nomi di `pymongo.server_type.SERVER_TYPE` ai ruoli del dominio.

Le chiavi sono **tutti** i nomi che il driver conosce oggi, e una prova lo verifica
confrontando questo dizionario con `SERVER_TYPE._fields`. `Unknown` compare qui con il
valore che ha quando non c'è un errore; con un errore diventa `IRRAGGIUNGIBILE`, e
quella è l'unica riga della traduzione che dipende da un secondo campo.
"""

FORME: Final[Mapping[str, TipoTopologia]] = {
    "Unknown": TipoTopologia.SCONOSCIUTA,
    "Single": TipoTopologia.SINGOLA,
    "ReplicaSetNoPrimary": TipoTopologia.REPLICA_SET_SENZA_PRIMARIO,
    "ReplicaSetWithPrimary": TipoTopologia.REPLICA_SET_CON_PRIMARIO,
    "Sharded": TipoTopologia.SHARDED,
    "LoadBalanced": TipoTopologia.SINGOLA,
}
"""Dai nomi di `pymongo.topology_description.TOPOLOGY_TYPE` alle forme del dominio.

`LoadBalanced` non capita in questo laboratorio: nessuno dei tre stack usa un load
balancer, e per arrivarci servirebbe `loadBalanced=true` nella stringa di connessione.
La riserva è che, se un giorno ci si arrivasse, il cluster verrebbe chiamato «singola» —
che dal punto di vista del client è quasi vero, perché parla con un indirizzo solo — e
la guardia sui nomi non se ne accorgerebbe, perché il nome c'è.
"""

COMANDI_OSSERVATI: Final[frozenset[str]] = frozenset(
    {
        "aggregate",
        "count",
        "delete",
        "distinct",
        "find",
        "findAndModify",
        "getMore",
        "insert",
        "update",
    }
)
"""I comandi la cui durata diventa un campione di latenza.

L'elenco è chiuso apposta. Sotto carico il driver parla molto — `hello` ogni due
secondi per server, `ping`, `endSessions` alla chiusura di ogni sessione — e a 800
scritture al secondo un ascoltatore che prendesse tutto riempirebbe la coda di campioni
che nessuno ha chiesto, spostando verso il basso proprio i percentili dell'Atto II.

Chi legge `LatencySampled` deve sapere che qui dentro finisce **anche** ciò che
`WorkloadRunner` misura dalla porta, ma sotto un altro nome: `insert_many` è il tempo
visto da chi chiama, `insert` è il tempo del comando sul filo. Sono due misure diverse
della stessa scrittura, e la differenza fra le due è il costo del driver. Tenerle
separate per nome è ciò che impedisce di mescolarle in un percentile solo.
"""

OPERAZIONE_BATTITO: Final = "heartbeat"
"""Il nome sotto cui finiscono le latenze degli heartbeat.

`LatencySampled` dice già nella sua docstring che si campiona anche ciò che non scrive,
«e gli heartbeat»: questo è il nome con cui arrivano.
"""


def indirizzo_di(address: tuple[str, int | None]) -> str:
    """`("mongo-1", 27017)` diventa `"mongo-1:27017"`; senza porta, solo l'host."""
    host, porta = address
    return host if porta is None else f"{host}:{porta}"


def ruolo_di(descrizione: DescrizioneServerDelDriver) -> RuoloServer:
    """Il ruolo del dominio, con la distinzione che il driver non fa.

    `Unknown` è una parola sola per due situazioni diverse, e il driver le distingue con
    un campo: senza errore il client non ha ancora guardato, con un errore ha guardato e
    non c'era nessuno. La prima è `SCONOSCIUTO`, la seconda è `IRRAGGIUNGIBILE`.

    Il valore di ripiego per un nome mai visto non è pigrizia. Un `KeyError` sollevato
    qui verrebbe **ingoiato** da pymongo: `_handle_exception` stampa la traccia su
    `stderr` e prosegue, e sotto un `Live` di Rich quella stampa non la vede nessuno. Il
    ripiego tiene in piedi il thread del monitor; a garantire che non si usi mai è la
    prova che confronta le chiavi di `RUOLI` con quelle di `SERVER_TYPE`.
    """
    ruolo = RUOLI.get(descrizione.server_type_name, RuoloServer.SCONOSCIUTO)
    if ruolo is RuoloServer.SCONOSCIUTO and descrizione.error is not None:
        return RuoloServer.IRRAGGIUNGIBILE
    return ruolo


def descrivi_server(descrizione: DescrizioneServerDelDriver) -> DescrizioneServer:
    """Un `ServerDescription` di pymongo diventa un `DescrizioneServer` del dominio.

    Il ritardo passa da secondi a millisecondi, e se non c'è **resta assente**: uno zero
    direbbe «questo server risponde istantaneamente» a proposito di un server che non ha
    ancora risposto affatto.
    """
    errore = descrizione.error
    ritardo = descrizione.round_trip_time
    return DescrizioneServer(
        indirizzo=indirizzo_di(descrizione.address),
        ruolo=ruolo_di(descrizione),
        ritardo_ms=None if ritardo is None else ritardo * 1000.0,
        errore=None if errore is None else f"{type(errore).__name__}: {errore}",
    )


def descrivi_topologia(
    descrizione: DescrizioneTopologiaDelDriver,
) -> DescrizioneTopologia:
    """Un `TopologyDescription` di pymongo diventa un `DescrizioneTopologia` del dominio.

    I server escono **ordinati per indirizzo**. `server_descriptions()` è un dizionario,
    e l'ordine di un dizionario è quello di chi l'ha riempito: senza il riordino, due
    topologie identiche potrebbero risultare diverse solo per come il driver le ha
    elencate, e il confronto che tiene silenzioso questo ponte emetterebbe un
    cambiamento che non c'è. È la stessa regola del `TopologyWatcher` del Task 6.
    """
    return DescrizioneTopologia(
        tipo=FORME.get(descrizione.topology_type_name, TipoTopologia.SCONOSCIUTA),
        server=tuple(
            sorted(
                (
                    descrivi_server(server)
                    for server in descrizione.server_descriptions().values()
                ),
                key=lambda server: server.indirizzo,
            )
        ),
        nome_set=descrizione.replica_set_name,
    )


# --------------------------------------------------------------------------------------
# I quattro ascoltatori.
# --------------------------------------------------------------------------------------


class _Ascoltatore:
    """Quello che i quattro hanno in comune: dove depositare, e che ora è.

    I callback che tacciono hanno il parametro annotato `object`, e il tipo è il
    commento: questo callback non legge niente dell'evento. Il giorno in cui ne leggesse
    qualcosa, il tipo dovrebbe dire che cosa.
    """

    def __init__(self, coda: "queue.Queue[Evento]", orologio: Clock) -> None:
        self._coda = coda
        self._orologio = orologio


class AscoltatoreServer(_Ascoltatore, monitoring.ServerListener):
    """Il ruolo di un singolo server, quando cambia."""

    def opened(self, evento: object) -> None:
        """Silenzio. Il ciclo di vita degli oggetti del driver non è quello del cluster."""

    def closed(self, evento: object) -> None:
        """Silenzio. Un server che sparisce arriva comunque, come cambio di topologia."""

    def description_changed(self, evento: CambioServerDelDriver) -> None:
        """L'indirizzo è quello del «dopo», ed è la stessa cosa che quello del «prima».

        Non è una scelta fra due possibilità: è la stessa scrittura per due strade. Il
        driver pubblica questo evento in un punto solo (`synchronous/topology.py:516`), e
        la descrizione vecchia la trova indicizzando per l'indirizzo di quella nuova
        (`_process_change`, riga 495). I due lati portano quindi sempre lo stesso
        indirizzo, per costruzione. È scritto qui perché una rottura deliberata l'ha
        chiesto: scambiando `new_` con `previous_` la suite resta verde, e la spiegazione
        non è una guardia che manca — è che non c'è niente da guardare.
        """
        precedente = ruolo_di(evento.previous_description)
        successivo = ruolo_di(evento.new_description)
        if precedente is successivo:
            return
        self._coda.put_nowait(
            ServerStateChanged(
                istante=self._orologio.now(),
                indirizzo=indirizzo_di(evento.new_description.address),
                precedente=precedente,
                successivo=successivo,
            )
        )


class AscoltatoreTopologia(_Ascoltatore, monitoring.TopologyListener):
    """La forma del cluster, quando cambia."""

    def opened(self, evento: object) -> None:
        """Silenzio. È l'accensione del client, non un fatto del cluster."""

    def closed(self, evento: object) -> None:
        """Silenzio. È lo spegnimento del client, non un fatto del cluster."""

    def description_changed(self, evento: CambioTopologiaDelDriver) -> None:
        precedente = descrivi_topologia(evento.previous_description)
        successiva = descrivi_topologia(evento.new_description)
        if precedente == successiva:
            return
        self._coda.put_nowait(
            TopologyChanged(
                istante=self._orologio.now(),
                precedente=precedente,
                successiva=successiva,
            )
        )


class AscoltatoreHeartbeat(_Ascoltatore, monitoring.ServerHeartbeatListener):
    """Il giro di rete verso ogni server, ogni due secondi."""

    def started(self, evento: object) -> None:
        """Silenzio. Un battito che parte non è un fatto: il fatto è come finisce."""

    def succeeded(self, evento: BattitoRiuscitoDelDriver) -> None:
        """Un campione di latenza — tranne quando il battito era in attesa.

        Con lo *streaming hello* (MongoDB ≥ 4.4) il server tiene aperta la richiesta
        finché non ha qualcosa da dire, fino a `heartbeatFrequencyMS`. La `duration` di
        quel battito misura un'attesa concordata, non un giro di rete: farla entrare nel
        flusso da cui l'Atto II calcola i percentili vorrebbe dire mostrare un p99 di
        dieci secondi e chiamarlo latenza.
        """
        if evento.awaited:
            return
        self._coda.put_nowait(
            LatencySampled(
                istante=self._orologio.now(),
                operazione=OPERAZIONE_BATTITO,
                durata_ms=evento.duration * 1000.0,
            )
        )

    def failed(self, evento: object) -> None:
        """Silenzio, ed è il silenzio meno ovvio dei cinque.

        L'[ADR-0006](../../../../docs/Decision.md#adr-0006) chiama questo evento «il
        momento esatto in cui il client si accorge della caduta», e la tentazione di
        emetterlo è forte. Tre ragioni per non farlo. Lo stesso fatto arriva pochi
        microsecondi dopo come cambio di descrizione, con il ruolo `IRRAGGIUNGIBILE` e
        con il testo dell'errore dentro la `DescrizioneTopologia`: non si perde niente.
        Non esiste un evento di dominio che gli somigli, e `WriteFailed` mentirebbe,
        perché nessuna scrittura è fallita — è la bugia che l'ADR-0082 ha rifiutato
        quando ha preferito inventare `PrimaryWaitAbandoned`. E mentre un nodo resta giù
        i battiti continuano a fallire ogni due secondi, mentre il cambio di descrizione
        pymongo lo pubblica solo quando la descrizione è **diversa**: una riga sola
        invece di una cascata di righe identiche.
        """


class AscoltatoreComandi(_Ascoltatore, monitoring.CommandListener):
    """La durata dei comandi sul filo, per i soli comandi che si è chiesto di guardare."""

    def __init__(
        self,
        coda: "queue.Queue[Evento]",
        orologio: Clock,
        comandi: Collection[str],
    ) -> None:
        super().__init__(coda, orologio)
        self._comandi = comandi

    def started(self, evento: object) -> None:
        """Silenzio. La durata la sa solo chi la vede finire."""

    def succeeded(self, evento: ComandoRiuscitoDelDriver) -> None:
        nome = evento.command_name
        if nome not in self._comandi:
            return
        self._coda.put_nowait(
            LatencySampled(
                istante=self._orologio.now(),
                operazione=nome,
                durata_ms=evento.duration_micros / 1000.0,
            )
        )

    def failed(self, evento: object) -> None:
        """Silenzio. Un comando fallito ha una durata, e quella durata non è latenza.

        Le scritture fallite le racconta già `WorkloadRunner`, con l'eccezione vera del
        driver in mano. Qui si guarda la stessa scrittura dal lato del filo, dove non si
        sa ancora se qualcuno la ritenterà: farne un campione vorrebbe dire mettere il
        tempo di un tentativo andato a vuoto nel flusso da cui si calcolano i percentili.
        """


type AscoltatoreSdam = (
    AscoltatoreServer | AscoltatoreTopologia | AscoltatoreHeartbeat | AscoltatoreComandi
)
"""Uno dei quattro. Serve solo a dare un tipo alla tupla che va nel `MongoClient`."""


class SdamBridge:
    """I quattro ascoltatori, la coda che condividono, e il modo di svuotarla.

    Si registra **per singolo client** — `MongoClient(event_listeners=ponte.ascoltatori)`
    — e mai con `monitoring.register()`, che li metterebbe su ogni client del processo.
    È la forma scelta dall'[ADR-0006](../../../../docs/Decision.md#adr-0006), e la
    ragione è pratica: due client nella stessa esecuzione devono poter avere cronache
    separate, altrimenti la cronaca del failover si riempirebbe dei battiti del cluster
    che l'Atto III sta leggendo per conto suo.

    Chi consuma chiama `drena()` dal **proprio** thread, e da lì in poi può fare quel che
    vuole con gli eventi: disegnarli, contarli, tenerli. Il patto dell'ADR-0019 finisce
    dove finisce la coda.
    """

    def __init__(
        self,
        orologio: Clock,
        *,
        comandi: Collection[str] = COMANDI_OSSERVATI,
    ) -> None:
        self._coda: queue.Queue[Evento] = queue.Queue()
        self.ascoltatore_server = AscoltatoreServer(self._coda, orologio)
        self.ascoltatore_topologia = AscoltatoreTopologia(self._coda, orologio)
        self.ascoltatore_battiti = AscoltatoreHeartbeat(self._coda, orologio)
        self.ascoltatore_comandi = AscoltatoreComandi(self._coda, orologio, comandi)

    @property
    def ascoltatori(self) -> tuple[AscoltatoreSdam, ...]:
        """I quattro, nell'ordine in cui il §6.3 li elenca. Da passare al `MongoClient`."""
        return (
            self.ascoltatore_server,
            self.ascoltatore_topologia,
            self.ascoltatore_battiti,
            self.ascoltatore_comandi,
        )

    @property
    def in_coda(self) -> int:
        """Quanti eventi aspettano. È il numero che dice se il consumatore sta al passo."""
        return self._coda.qsize()

    def drena(self) -> list[Evento]:
        """Tutto quello che c'è, nell'ordine in cui è arrivato, e la coda resta vuota.

        Non aspetta: se non c'è niente restituisce una lista vuota. Un `drena()` che
        bloccasse trasformerebbe il ciclo di chi disegna in un'attesa, ed è esattamente
        il verso della dipendenza che l'ADR-0019 ha invertito.
        """
        raccolti: list[Evento] = []
        while True:
            try:
                raccolti.append(self._coda.get_nowait())
            except queue.Empty:
                return raccolti
