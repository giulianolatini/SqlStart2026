"""Il ponte SDAM, provato senza un driver vivo e senza un server.

Queste prove sono state scritte **prima** di `mongolab.infrastructure.sdam`, e la cosa
più importante che dicono non è un'asserzione: è che si possono scrivere. Il contratto
da fissare al Task 7 è la **mappatura** — da ciò che pymongo passa a un callback a ciò
che il dominio conosce — e una mappatura si prova costruendo a mano gli oggetti che il
driver passerebbe. Serve un `mongod` solo per la prova del Passo 4, che infatti non ne
usa uno: `MongoClient(connect=False)` non parla con nessuno.

**Gli oggetti finti del driver stanno qui, non in `tests/doppi/`.** La cartella dei
doppi ha un significato preciso — lì dentro c'è ciò che sta *al posto* di una porta, e
un doppio implementa comportamento, o solleva. Questi non implementano niente: sono
schede, quattro campi in croce, senza una riga di logica che possa sbagliare. Un
`_ServerDelDriver` non «fa finta» di essere un `ServerDescription`: **ha la forma** che
`sdam.py` dichiara di leggere, ed è `mypy --strict` a verificare che la classe vera di
pymongo abbia la stessa forma, nel punto in cui i callback la sovrascrivono.

**Il tempo compare in tre prove sole.** Il vincolo dell'[ADR-0019](../../../docs/Decision.md#adr-0019)
— costruisci, deposita, ritorna — è per sua natura una cosa che si misura, ma la prova
che vale davvero è quella deterministica: `test_i_callback_non_hanno_bisogno_di_nessuno_che_svuoti`
non guarda l'orologio e fallirebbe comunque se qualcuno mettesse un consumatore dentro
il callback. La prova cronometrata sta accanto, si tara da sola sulla macchina che la
esegue, e serve a distinguere «deposita» da «formatta».
"""

import queue
import threading
import time
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from pymongo import MongoClient
from pymongo.server_type import SERVER_TYPE
from pymongo.topology_description import TOPOLOGY_TYPE

from mongolab.domain.eventi import (
    Evento,
    LatencySampled,
    ServerStateChanged,
    TopologyChanged,
)
from mongolab.domain.modelli import DescrizioneServer, RuoloServer, TipoTopologia
from mongolab.domain.porte import Clock
from mongolab.infrastructure.sdam import (
    COMANDI_OSSERVATI,
    FORME,
    OPERAZIONE_BATTITO,
    RUOLI,
    AscoltatoreSdam,
    SdamBridge,
    descrivi_server,
    descrivi_topologia,
)

from tests.aiutanti import specie
from tests.doppi import FakeClock

ISTANTE = datetime(2026, 9, 18, 9, 30, 0, tzinfo=UTC)

# Quante volte si ripete un callback nelle due prove cronometrate. Abbastanza da coprire
# il rumore di `perf_counter`, poco abbastanza da non pesare sulla suite.
GIRI = 2000

# Quante volte il callback può costare più di un `put_nowait` nudo. Il numero è stato
# misurato prima di essere scritto (M-013): il callback vero costa 1,3 µs contro 0,45 µs,
# cioè **2,9 volte**, stabile su cinque ripetizioni. La soglia sta a dieci, più del
# triplo, perché a far fallire questa prova non dev'essere una macchina carica.
#
# Che cosa prende, e che cosa no. Aggiungere al callback una frase formattata porta il
# rapporto a 5: **non** lo prende, ed è giusto dirlo invece di far finta. Disegnare una
# tabella di Rich lo porta a 884 — 383 µs a callback — e quello lo prende con tre ordini
# di grandezza di margine. È la rottura che conta, perché è quella che l'ADR-0019 ha
# scartato per nome: a 800 comandi al secondo sarebbero 0,31 secondi di CPU per ogni
# secondo di orologio, rubati ai thread che stanno scrivendo.
SOGLIA_COSTO = 10.0


# --------------------------------------------------------------------------------------
# Gli oggetti che il driver passerebbe, costruiti a mano.
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _ServerDelDriver:
    """La forma di `pymongo.server_description.ServerDescription`, per quel che si legge."""

    address: tuple[str, int | None]
    server_type_name: str
    round_trip_time: float | None = None
    error: Exception | None = None


class _TopologiaDelDriver:
    """La forma di `pymongo.topology_description.TopologyDescription`.

    Non è un `dataclass` perché l'elenco dei server è variadico e `server_descriptions`
    è un metodo, non un campo: la classe vera lo espone così, e la forma che si prova
    deve essere quella vera.
    """

    def __init__(
        self,
        topology_type_name: str,
        *server: _ServerDelDriver,
        replica_set_name: str | None = None,
    ) -> None:
        self.topology_type_name = topology_type_name
        self.replica_set_name = replica_set_name
        self._server = server

    def server_descriptions(self) -> Mapping[tuple[str, int | None], _ServerDelDriver]:
        return {descrizione.address: descrizione for descrizione in self._server}


@dataclass(frozen=True)
class _CambioServer:
    previous_description: _ServerDelDriver
    new_description: _ServerDelDriver


@dataclass(frozen=True)
class _CambioTopologia:
    previous_description: _TopologiaDelDriver
    new_description: _TopologiaDelDriver


@dataclass(frozen=True)
class _Battito:
    duration: float
    awaited: bool = False


@dataclass(frozen=True)
class _Comando:
    command_name: str
    duration_micros: int


def _srv(
    nome: str,
    tipo: str,
    ritardo: float | None = None,
    errore: Exception | None = None,
) -> _ServerDelDriver:
    """Un server del driver, all'indirizzo `nome:27017`."""
    return _ServerDelDriver((nome, 27017), tipo, ritardo, errore)


def _ponte() -> SdamBridge:
    orologio: Clock = FakeClock(ISTANTE)
    return SdamBridge(orologio)


# --------------------------------------------------------------------------------------
# La mappatura dei ruoli: il contratto del Passo 3.
# --------------------------------------------------------------------------------------


def test_ogni_tipo_di_server_di_pymongo_ha_un_ruolo() -> None:
    """La guardia di totalità: se il driver impara un tipo nuovo, questa prova cade.

    Nel codice la traduzione ha un valore di ripiego, perché un'eccezione dentro un
    callback pymongo se la ingoia (`_handle_exception` la stampa su `stderr` e prosegue)
    e sotto un `Live` di Rich quella stampa non la vede nessuno. Questa prova esiste
    perché il ripiego non si usi mai davvero: un ripiego che si usa è una bugia sullo
    schermo, e questa guardia la trasforma in una suite rossa il giorno
    dell'aggiornamento del driver.
    """
    assert set(RUOLI) == set(SERVER_TYPE._fields)


def test_ogni_tipo_di_topologia_di_pymongo_ha_una_forma() -> None:
    """Come sopra, per la forma del cluster."""
    assert set(FORME) == set(TOPOLOGY_TYPE._fields)


def test_i_ruoli_che_la_scena_nomina() -> None:
    """I cinque ruoli che compaiono a schermo, e da quale tipo di pymongo vengono."""
    assert RUOLI["RSPrimary"] is RuoloServer.PRIMARIO
    assert RUOLI["RSSecondary"] is RuoloServer.SECONDARIO
    assert RUOLI["RSArbiter"] is RuoloServer.ARBITRO
    assert RUOLI["Standalone"] is RuoloServer.STANDALONE
    assert RUOLI["Mongos"] is RuoloServer.ROUTER


def test_i_ruoli_che_la_scena_non_nomina_sono_altro() -> None:
    """`RSOther`, `RSGhost`, `LoadBalancer`: riconosciuti dal client, estranei al talk.

    Il caso vero è `RSOther`, e capita **proprio durante la dimostrazione**: un membro
    che riparte è in `RECOVERING` o in `STARTUP2` per qualche secondo, e il driver lo
    chiama così. Mandarlo su `SCONOSCIUTO` scriverebbe «non so» su un server di cui il
    client sa benissimo che cosa sia, e lo farebbe nell'unico minuto in cui la sala sta
    guardando quella riga.
    """
    assert RUOLI["RSOther"] is RuoloServer.ALTRO
    assert RUOLI["RSGhost"] is RuoloServer.ALTRO
    assert RUOLI["LoadBalancer"] is RuoloServer.ALTRO


def test_un_server_sconosciuto_con_un_errore_e_irraggiungibile() -> None:
    """`Unknown` **più** un errore: il client ha provato e non è riuscito."""
    descrizione = descrivi_server(_srv("mongo-2", "Unknown", errore=OSError("rifiutata")))

    assert descrizione.ruolo is RuoloServer.IRRAGGIUNGIBILE


def test_un_server_sconosciuto_senza_errore_resta_sconosciuto() -> None:
    """`Unknown` senza errore: il client non ha ancora provato.

    È la stessa distinzione del Task 6, dall'altro capo del ponte: `IRRAGGIUNGIBILE` è
    un'osservazione, `SCONOSCIUTO` è l'assenza di un'osservazione. Il driver le tiene
    nello stesso tipo, e le distingue con un campo; qui diventano due parole diverse.
    """
    descrizione = descrivi_server(_srv("mongo-2", "Unknown"))

    assert descrizione.ruolo is RuoloServer.SCONOSCIUTO


def test_un_tipo_che_pymongo_non_aveva_non_fa_esplodere_il_callback() -> None:
    """Il ripiego, provato nell'unico modo in cui si può: inventando un tipo.

    Non si arriva qui finché `test_ogni_tipo_di_server_di_pymongo_ha_un_ruolo` è verde.
    Ma il costo di sbagliarsi non è simmetrico: un ripiego mancante diventa un
    `KeyError` dentro un thread del driver, e pymongo lo ingoia.
    """
    descrizione = descrivi_server(_srv("mongo-1", "Quantum"))

    assert descrizione.ruolo is RuoloServer.SCONOSCIUTO


def test_il_ritardo_e_in_millisecondi() -> None:
    """`round_trip_time` di pymongo è in **secondi**; il dominio parla in millisecondi."""
    descrizione = descrivi_server(_srv("mongo-1", "RSPrimary", ritardo=0.0123))

    assert descrizione.ritardo_ms == pytest.approx(12.3)


def test_un_ritardo_che_non_c_e_resta_assente() -> None:
    """Nessun campione, nessun numero: `None`, non zero (nota di metodo 155).

    Uno zero qui direbbe «questo server risponde istantaneamente» a proposito di un
    server che non ha ancora risposto affatto.
    """
    descrizione = descrivi_server(_srv("mongo-1", "RSPrimary"))

    assert descrizione.ritardo_ms is None


def test_l_errore_porta_il_nome_della_classe_e_il_messaggio() -> None:
    """Il *perché* del driver e il *che cosa* del sistema operativo, in una riga sola."""
    descrizione = descrivi_server(_srv("mongo-2", "Unknown", errore=OSError("rifiutata")))

    assert descrizione.errore == "OSError: rifiutata"


def test_un_server_senza_errore_non_ne_inventa_uno() -> None:
    descrizione = descrivi_server(_srv("mongo-1", "RSPrimary"))

    assert descrizione.errore is None


def test_un_indirizzo_senza_porta_non_diventa_una_porta_finta() -> None:
    """Il tipo `_Address` di pymongo è `tuple[str, int | None]`: la porta può mancare.

    Lo si è scoperto da `mypy --strict`, che ha bocciato il Protocol scritto con
    `tuple[str, int]`. Scrivere `f"{host}:{port}"` senza guardare avrebbe messo
    `mongo-1:None` a schermo.
    """
    descrizione = descrivi_server(_ServerDelDriver(("mongo-1", None), "Standalone"))

    assert descrizione.indirizzo == "mongo-1"


def test_le_forme_del_cluster() -> None:
    assert FORME["Single"] is TipoTopologia.SINGOLA
    assert FORME["ReplicaSetWithPrimary"] is TipoTopologia.REPLICA_SET_CON_PRIMARIO
    assert FORME["ReplicaSetNoPrimary"] is TipoTopologia.REPLICA_SET_SENZA_PRIMARIO
    assert FORME["Sharded"] is TipoTopologia.SHARDED
    assert FORME["Unknown"] is TipoTopologia.SCONOSCIUTA


def test_la_topologia_porta_il_nome_del_set() -> None:
    topologia = descrivi_topologia(
        _TopologiaDelDriver(
            "ReplicaSetWithPrimary",
            _srv("mongo-1", "RSPrimary"),
            replica_set_name="rs0",
        )
    )

    assert topologia.tipo is TipoTopologia.REPLICA_SET_CON_PRIMARIO
    assert topologia.nome_set == "rs0"


def test_i_server_arrivano_in_ordine_di_indirizzo() -> None:
    """`server_descriptions()` è un dizionario, e un dizionario ha l'ordine di chi l'ha riempito.

    Senza questo riordino, due `DescrizioneTopologia` con gli stessi server potrebbero
    risultare diverse solo perché il driver li ha elencati in un altro ordine, e il
    confronto che tiene silenzioso il ponte emetterebbe un cambiamento che non c'è.
    """
    topologia = descrivi_topologia(
        _TopologiaDelDriver(
            "ReplicaSetWithPrimary",
            _srv("mongo-3", "RSSecondary"),
            _srv("mongo-1", "RSPrimary"),
            _srv("mongo-2", "RSSecondary"),
        )
    )

    assert [server.indirizzo for server in topologia.server] == [
        "mongo-1:27017",
        "mongo-2:27017",
        "mongo-3:27017",
    ]


# --------------------------------------------------------------------------------------
# Che cosa depositano i callback.
# --------------------------------------------------------------------------------------


def test_un_server_che_cambia_ruolo_deposita_un_evento() -> None:
    ponte = _ponte()

    ponte.ascoltatore_server.description_changed(
        _CambioServer(_srv("mongo-1", "RSSecondary"), _srv("mongo-1", "RSPrimary"))
    )

    (evento,) = specie(ponte.drena(), ServerStateChanged)
    assert evento.indirizzo == "mongo-1:27017"
    assert evento.precedente is RuoloServer.SECONDARIO
    assert evento.successivo is RuoloServer.PRIMARIO


def test_un_server_che_non_cambia_ruolo_non_deposita_niente() -> None:
    """pymongo pubblica anche per cambiamenti che il dominio non rappresenta.

    Un `topologyVersion` che avanza, un `setVersion` che cambia: fatti veri, che qui non
    diventano una riga di cronaca, perché la cronaca racconta i ruoli.
    """
    ponte = _ponte()

    ponte.ascoltatore_server.description_changed(
        _CambioServer(
            _srv("mongo-1", "RSPrimary", ritardo=0.001),
            _srv("mongo-1", "RSPrimary", ritardo=0.002),
        )
    )

    assert ponte.drena() == []


def test_il_cambio_di_forma_deposita_entrambe_le_descrizioni() -> None:
    ponte = _ponte()
    prima = _TopologiaDelDriver(
        "ReplicaSetWithPrimary",
        _srv("mongo-1", "RSPrimary"),
        replica_set_name="rs0",
    )
    dopo = _TopologiaDelDriver(
        "ReplicaSetNoPrimary",
        _srv("mongo-1", "Unknown", errore=OSError("rifiutata")),
        replica_set_name="rs0",
    )

    ponte.ascoltatore_topologia.description_changed(_CambioTopologia(prima, dopo))

    (evento,) = specie(ponte.drena(), TopologyChanged)
    assert evento.precedente.tipo is TipoTopologia.REPLICA_SET_CON_PRIMARIO
    assert evento.successiva.tipo is TipoTopologia.REPLICA_SET_SENZA_PRIMARIO
    assert evento.successiva.server[0].ruolo is RuoloServer.IRRAGGIUNGIBILE


def test_una_topologia_tradotta_uguale_non_deposita_niente() -> None:
    ponte = _ponte()
    topologia = _TopologiaDelDriver("Sharded", _srv("router-1", "Mongos"))

    ponte.ascoltatore_topologia.description_changed(_CambioTopologia(topologia, topologia))

    assert ponte.drena() == []


def test_il_battito_riuscito_e_un_campione_di_latenza() -> None:
    """`duration` di un heartbeat è in **secondi**, malgrado quel che dice la docstring.

    La docstring di `ServerHeartbeatSucceededEvent.duration` dice «in microseconds»; il
    monitor passa lì dentro `max(0.0, time.monotonic() - inizio)`, che è in secondi. Il
    conflitto è registrato in `app/docs/Sources.md` (M-012); questa prova fissa il verso
    che si è misurato, non quello che si è letto.
    """
    ponte = _ponte()

    ponte.ascoltatore_battiti.succeeded(_Battito(duration=0.0072))

    (evento,) = specie(ponte.drena(), LatencySampled)
    assert evento.operazione == OPERAZIONE_BATTITO
    assert evento.durata_ms == pytest.approx(7.2)


def test_il_battito_in_attesa_non_e_un_campione() -> None:
    """Il campione di latenza che vale dieci secondi e non è un problema di rete.

    Con lo *streaming hello* (MongoDB ≥ 4.4) il server tiene aperta la richiesta finché
    non ha qualcosa da dire, fino a `heartbeatFrequencyMS`. La `duration` di quel battito
    misura l'attesa concordata, non il giro di rete: farla entrare nello stesso flusso da
    cui l'Atto II legge i percentili vorrebbe dire mostrare un p99 di dieci secondi e
    chiamarlo latenza.
    """
    ponte = _ponte()

    ponte.ascoltatore_battiti.succeeded(_Battito(duration=9.98, awaited=True))

    assert ponte.drena() == []


def test_il_comando_osservato_e_un_campione_di_latenza() -> None:
    """`duration_micros` di un comando, invece, è davvero in microsecondi."""
    ponte = _ponte()

    ponte.ascoltatore_comandi.succeeded(_Comando("insert", duration_micros=4321))

    (evento,) = specie(ponte.drena(), LatencySampled)
    assert evento.operazione == "insert"
    assert evento.durata_ms == pytest.approx(4.321)


def test_i_comandi_di_servizio_non_entrano_nella_cronaca() -> None:
    """Sotto carico il driver parla molto, e quasi tutto quel che dice non è latenza.

    `hello` è il battito, `ping` è il controllo, `endSessions` è la pulizia: tre comandi
    che a 800 scritture al secondo riempirebbero la coda di campioni che nessuno ha
    chiesto e che sposterebbero i percentili verso il basso.
    """
    ponte = _ponte()

    for nome in ("hello", "ping", "endSessions", "isMaster"):
        ponte.ascoltatore_comandi.succeeded(_Comando(nome, duration_micros=100))

    assert ponte.drena() == []


def test_l_insieme_dei_comandi_da_osservare_si_puo_scegliere() -> None:
    """Il valore di partenza è un nome, non un letterale sparso nel codice."""
    orologio: Clock = FakeClock(ISTANTE)
    ponte = SdamBridge(orologio, comandi=frozenset({"ping"}))

    ponte.ascoltatore_comandi.succeeded(_Comando("ping", duration_micros=100))
    ponte.ascoltatore_comandi.succeeded(_Comando("insert", duration_micros=100))

    (evento,) = specie(ponte.drena(), LatencySampled)
    assert evento.operazione == "ping"
    assert "insert" in COMANDI_OSSERVATI


def test_gli_eventi_portano_l_istante_dell_orologio() -> None:
    """L'ora viene dalla porta `Clock`, non da `datetime.now()` sepolto nel callback."""
    ponte = _ponte()

    ponte.ascoltatore_battiti.succeeded(_Battito(duration=0.001))
    ponte.ascoltatore_comandi.succeeded(_Comando("find", duration_micros=100))
    ponte.ascoltatore_server.description_changed(
        _CambioServer(_srv("mongo-1", "Unknown"), _srv("mongo-1", "RSPrimary"))
    )

    eventi = ponte.drena()
    assert len(eventi) == 3
    assert all(evento.istante == ISTANTE for evento in eventi)


def test_il_ponte_deposita_solo_eventi_del_dominio() -> None:
    """Nessuna specie di comodo: ciò che esce dalla coda sta in `domain/eventi.py`."""
    ponte = _ponte()

    ponte.ascoltatore_battiti.succeeded(_Battito(duration=0.001))
    ponte.ascoltatore_server.description_changed(
        _CambioServer(_srv("mongo-1", "Unknown"), _srv("mongo-1", "RSPrimary"))
    )

    eventi = ponte.drena()
    assert eventi
    assert all(isinstance(evento, Evento) for evento in eventi)


# --------------------------------------------------------------------------------------
# I silenzi voluti. Ognuno con la sua ragione, e ognuno con la sua prova.
# --------------------------------------------------------------------------------------


def test_l_apertura_e_la_chiusura_di_un_server_non_dicono_niente() -> None:
    """Il ciclo di vita degli oggetti del driver non è il ciclo di vita del cluster.

    Un server che scompare dalla configurazione arriva comunque, come cambio di
    topologia; un `ServerClosedEvent` in più direbbe la stessa cosa due volte.
    """
    ponte = _ponte()

    ponte.ascoltatore_server.opened(object())
    ponte.ascoltatore_server.closed(object())

    assert ponte.drena() == []


def test_l_apertura_e_la_chiusura_della_topologia_non_dicono_niente() -> None:
    """Sono l'accensione e lo spegnimento del client, non fatti del cluster."""
    ponte = _ponte()

    ponte.ascoltatore_topologia.opened(object())
    ponte.ascoltatore_topologia.closed(object())

    assert ponte.drena() == []


def test_il_battito_iniziato_non_dice_niente() -> None:
    """Un battito che parte non è un fatto: il fatto è come finisce."""
    ponte = _ponte()

    ponte.ascoltatore_battiti.started(object())

    assert ponte.drena() == []


def test_il_battito_fallito_non_dice_niente() -> None:
    """Il silenzio meno ovvio di tutti, e quello con la ragione più lunga.

    L'[ADR-0006](../../../docs/Decision.md#adr-0006) chiama questo evento «il momento
    esatto in cui il client si accorge della caduta», e la tentazione è emetterlo. Non
    lo si fa per tre ragioni. Lo stesso fatto arriva pochi microsecondi dopo come cambio
    di descrizione, con il ruolo `IRRAGGIUNGIBILE` e con il testo dell'errore dentro la
    `DescrizioneTopologia`, quindi non si perde niente. Non esiste un evento di dominio
    che gli somigli: `WriteFailed` mentirebbe, perché nessuna scrittura è fallita, ed è
    esattamente la bugia che l'[ADR-0082](../../../docs/Decision.md#adr-0082) ha rifiutato
    quando ha preferito inventare `PrimaryWaitAbandoned`. E mentre un nodo resta giù i
    battiti continuano a fallire ogni due secondi: la cronaca si riempirebbe di righe
    identiche, mentre il cambio di descrizione, che `pymongo` pubblica solo quando la
    descrizione è **diversa**, ne produce una sola.
    """
    ponte = _ponte()

    ponte.ascoltatore_battiti.failed(object())

    assert ponte.drena() == []


def test_il_comando_iniziato_e_quello_fallito_non_dicono_niente() -> None:
    """Un comando fallito ha una durata, e quella durata non è latenza.

    Chi racconta le scritture fallite è già `WorkloadRunner`, con l'eccezione vera del
    driver in mano (`WriteFailed`). Qui si guarda la stessa scrittura dal lato del filo,
    dove non si sa se qualcuno la ritenterà: farne un campione vorrebbe dire mettere nel
    flusso da cui si calcolano i percentili il tempo di un tentativo andato a vuoto.
    """
    ponte = _ponte()

    ponte.ascoltatore_comandi.started(object())
    ponte.ascoltatore_comandi.failed(object())

    assert ponte.drena() == []


# --------------------------------------------------------------------------------------
# Costruisci, deposita, ritorna: il vincolo dell'ADR-0019.
# --------------------------------------------------------------------------------------


def test_i_callback_non_hanno_bisogno_di_nessuno_che_svuoti() -> None:
    """La prova che vale, e non guarda l'orologio.

    Se un giorno qualcuno mettesse dentro il callback il consumo dell'evento — un
    `sink.emit`, un ridisegno, una scrittura su file — questa prova non fallirebbe per
    lentezza: fallirebbe perché non c'è nessun consumatore, e il callback lo pretende.
    Il ponte non riceve un `EventSink` nel costruttore, e questa prova è la ragione.
    """
    ponte = _ponte()
    cambio = _CambioServer(_srv("mongo-1", "RSSecondary"), _srv("mongo-1", "RSPrimary"))
    altro = _CambioServer(_srv("mongo-1", "RSPrimary"), _srv("mongo-1", "RSSecondary"))

    for giro in range(1000):
        ponte.ascoltatore_server.description_changed(cambio if giro % 2 == 0 else altro)

    assert ponte.in_coda == 1000
    assert len(ponte.drena()) == 1000


def test_drena_svuota_la_coda_una_volta_sola() -> None:
    ponte = _ponte()
    ponte.ascoltatore_battiti.succeeded(_Battito(duration=0.001))

    assert len(ponte.drena()) == 1
    assert ponte.drena() == []
    assert ponte.in_coda == 0


def test_gli_eventi_escono_nell_ordine_in_cui_sono_entrati() -> None:
    """Una coda, non un insieme: la cronaca è una successione."""
    ponte = _ponte()

    for millisecondi in (1, 2, 3):
        ponte.ascoltatore_comandi.succeeded(
            _Comando("insert", duration_micros=millisecondi * 1000)
        )

    durate = [evento.durata_ms for evento in specie(ponte.drena(), LatencySampled)]
    assert durate == [1.0, 2.0, 3.0]


def test_il_callback_costa_quanto_un_inserimento_in_coda() -> None:
    """La misura, tarata sulla macchina che la esegue.

    Non è una prova di prestazioni travestita. È la verifica del vincolo che rende
    oneste tutte le misure del Task 6: i callback SDAM li chiama il driver in modo
    **sincrono**, e un listener lento rallenta il monitor, cioè allunga proprio il
    failover che si sta cronometrando. Il riferimento si misura nello stesso giro,
    così una macchina lenta rallenta tutti e due i termini e il rapporto regge.
    """
    ponte = _ponte()
    cambio = _CambioServer(_srv("mongo-1", "RSSecondary"), _srv("mongo-1", "RSPrimary"))
    altro = _CambioServer(_srv("mongo-1", "RSPrimary"), _srv("mongo-1", "RSSecondary"))

    magazzino: queue.Queue[object] = queue.Queue()
    pronto = object()
    inizio = time.perf_counter()
    for _ in range(GIRI):
        magazzino.put_nowait(pronto)
    riferimento = time.perf_counter() - inizio

    inizio = time.perf_counter()
    for giro in range(GIRI):
        ponte.ascoltatore_server.description_changed(cambio if giro % 2 == 0 else altro)
    misurato = time.perf_counter() - inizio

    assert misurato < riferimento * SOGLIA_COSTO


def test_i_callback_da_piu_thread_non_perdono_eventi() -> None:
    """Un callback SDAM non sa chi lo chiama, e qui non gli serve saperlo.

    Non è una precauzione teorica: misurando pymongo 4.17 si vede lo **stesso metodo**
    girare su due thread diversi. `description_changed` arriva da `pymongo_events_thread`
    mentre il client vive, e dal `MainThread` quando qualcuno chiama `close()`, perché
    `Topology.close()` svuota la coda degli eventi sul thread di chi chiude. Gli
    heartbeat, invece, arrivano dritti dal thread del monitor.

    Il ponte regge senza lucchetti perché **non ricorda niente**: quel che è cambiato
    glielo dice il driver, con `previous_description` e `new_description`. L'unico stato
    condiviso è la coda, che è già sincronizzata.
    """
    ponte = _ponte()
    cambio = _CambioServer(_srv("mongo-1", "RSSecondary"), _srv("mongo-1", "RSPrimary"))

    def duecento_volte() -> None:
        for _ in range(200):
            ponte.ascoltatore_server.description_changed(cambio)

    thread = [threading.Thread(target=duecento_volte) for _ in range(8)]

    for uno in thread:
        uno.start()
    for uno in thread:
        uno.join()

    assert len(ponte.drena()) == 8 * 200


# --------------------------------------------------------------------------------------
# Per singolo client, non globalmente: il Passo 4.
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Registrazione:
    """Che cosa si è visto costruendo due client: uno con gli ascoltatori, uno senza."""

    ascoltatori: tuple[AscoltatoreSdam, ...]
    registrati: Sequence[object]
    altrui: Sequence[object]
    cronaca: list[Evento]


@pytest.fixture(scope="module")
def registrazione() -> Iterator[_Registrazione]:
    """Due client, costruiti una volta sola per tutto il modulo.

    È l'unica preparazione cara di questa suite, e conviene sapere perché. Chiudere un
    client su cui sono registrati degli ascoltatori costa fra i due e i cinque decimi di
    secondo: `Topology.close()` ferma `pymongo_events_thread` e poi lo **aspetta**, e
    quel thread dorme a intervalli di `MIN_HEARTBEAT_INTERVAL`, mezzo secondo. Pagarlo
    tre volte porterebbe una suite da otto centesimi a un secondo e mezzo. Le tre prove
    qui sotto guardano fatti diversi della stessa preparazione, e lo pagano una volta.

    `connect=False` tiene tutto offline. Non tiene tutto zitto, però, ed è la scoperta
    che rende questa preparazione utile: il client pubblica un cambio di topologia già
    mentre lo si costruisce, e lo pubblica su un thread suo. L'attesa che segue è lì per
    quello: senza, la prova leggerebbe una coda ancora vuota una volta su tante.
    """
    ponte = _ponte()
    con: MongoClient[dict[str, object]] = MongoClient(
        "mongodb://mongo-1:27017,mongo-2:27017/?replicaSet=rs0",
        connect=False,
        event_listeners=list(ponte.ascoltatori),
    )
    senza: MongoClient[dict[str, object]] = MongoClient(
        "mongodb://mongo-9:27017/", connect=False
    )
    scadenza = time.monotonic() + 2.0
    while ponte.in_coda < 1 and time.monotonic() < scadenza:
        time.sleep(0.001)
    try:
        yield _Registrazione(
            ascoltatori=ponte.ascoltatori,
            registrati=list(con.options.event_listeners),
            altrui=list(senza.options.event_listeners),
            cronaca=ponte.drena(),
        )
    finally:
        con.close()
        senza.close()


def test_i_quattro_ascoltatori_finiscono_sul_client(
    registrazione: _Registrazione,
) -> None:
    """`MongoClient(event_listeners=[...])`, la forma scelta dall'ADR-0006.

    Il quattro non è decorativo. Se un giorno `ascoltatori` ne dimenticasse uno, tutte
    le prove sulla mappatura resterebbero verdi — chiamano i callback a mano, e a un
    callback non importa se qualcuno lo ha registrato.
    """
    assert len(registrazione.ascoltatori) == 4
    for ascoltatore in registrazione.ascoltatori:
        assert ascoltatore in registrazione.registrati


def test_un_altro_client_nella_stessa_esecuzione_non_li_vede(
    registrazione: _Registrazione,
) -> None:
    """Due client, due cronache separate: il motivo per cui non si registra globalmente.

    `monitoring.register()` metterebbe questi ascoltatori su **ogni** client del
    processo, compreso quello che l'Atto III usa per leggere: la cronaca del failover si
    riempirebbe dei battiti di un cluster che non c'entra.
    """
    for ascoltatore in registrazione.ascoltatori:
        assert ascoltatore not in registrazione.altrui


def test_la_cronaca_e_quella_di_un_client_solo(registrazione: _Registrazione) -> None:
    """La prova che non guarda dentro il client, ma dentro la coda.

    Un client con `connect=False` non parla con nessuno, e **pubblica lo stesso** un
    cambio di topologia mentre lo si costruisce: da «sconosciuta e vuota» a «replica set
    senza primario», con i due semi elencati come `SCONOSCIUTO`. Sono i seed della
    stringa di connessione, non una scoperta — ed è la dimostrazione più pulita che
    `SCONOSCIUTO` significhi «non ho ancora guardato».

    Nella stessa esecuzione è nato un secondo client, su `mongo-9`, e di quello nella
    cronaca non c'è traccia. È esattamente ciò che una registrazione globale avrebbe
    reso impossibile.
    """
    (cambio,) = specie(registrazione.cronaca, TopologyChanged)

    assert cambio.successiva.tipo is TipoTopologia.REPLICA_SET_SENZA_PRIMARIO
    assert [server.indirizzo for server in cambio.successiva.server] == [
        "mongo-1:27017",
        "mongo-2:27017",
    ]
    assert all(
        server.ruolo is RuoloServer.SCONOSCIUTO for server in cambio.successiva.server
    )


def test_una_descrizione_tradotta_e_un_oggetto_del_dominio() -> None:
    """Dall'altra parte del ponte non passa niente di pymongo."""
    topologia = descrivi_topologia(
        _TopologiaDelDriver("Single", _srv("mongo-1", "Standalone", ritardo=0.0005))
    )

    assert all(isinstance(server, DescrizioneServer) for server in topologia.server)
