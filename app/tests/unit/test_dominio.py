"""Il dominio: che gli eventi siano davvero congelati, e le porte davvero strutturali.

Le due proprietà che questo modulo verifica sono quelle su cui poggia tutto il resto del
branch, e sono entrambe invisibili leggendo il codice: un `@dataclass(frozen=True)` senza
prova è una promessa, e un `Protocol` senza prova è un commento. Qui si guardano
funzionare.
"""

import dataclasses
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import Sequence

import pytest

from mongolab.domain import eventi as modulo_eventi
from mongolab.domain.eventi import (
    BackupProgressed,
    ChunkMigrated,
    Evento,
    LatencySampled,
    RetryAttempted,
    ServerStateChanged,
    TopologyChanged,
    WriteFailed,
    WriteSucceeded,
)
from mongolab.domain.modelli import (
    ContoShard,
    DescrizioneServer,
    DescrizioneTopologia,
    Documento,
    Progress,
    RuoloServer,
    TipoTopologia,
)
from mongolab.domain.porte import (
    BackupTool,
    Clock,
    ClusterInspector,
    DocumentStore,
    EventSink,
)

ISTANTE = datetime(2026, 9, 18, 9, 30, 0, tzinfo=UTC)


# --- Gli eventi -----------------------------------------------------------------------


def sottoclassi_di_evento() -> list[type[Evento]]:
    """Gli eventi dichiarati nel modulo, scoperti invece che elencati.

    Elencarli a mano qui vorrebbe dire che una nona classe aggiunta al Task 6 sfugge a
    ogni regola di questo file, e sfugge in silenzio: le prove continuerebbero a passare
    parlando delle otto che già conoscevano.
    """
    return [
        valore
        for valore in vars(modulo_eventi).values()
        if isinstance(valore, type)
        and issubclass(valore, Evento)
        and valore is not Evento
    ]


def test_gli_eventi_del_design_sono_otto_e_sono_quelli() -> None:
    attesi = {
        "BackupProgressed",
        "ChunkMigrated",
        "LatencySampled",
        "RetryAttempted",
        "ServerStateChanged",
        "TopologyChanged",
        "WriteFailed",
        "WriteSucceeded",
    }
    assert {classe.__name__ for classe in sottoclassi_di_evento()} == attesi


def test_la_base_e_congelata_slottata_e_porta_l_istante() -> None:
    """La radice: è da qui che le proprietà degli otto discendono.

    Sta separata dal controllo sulle sottoclassi perché è l'unico punto in cui `frozen` e
    l'ordine dei campi si possono ancora perdere. Sotto, il linguaggio li garantisce.
    """
    campi = dataclasses.fields(Evento)
    assert [campo.name for campo in campi] == ["istante"]
    # `__dataclass_params__` esiste a runtime su ogni dataclass ma non compare negli
    # stub: il plugin di mypy modella i campi, non i parametri del decoratore.
    parametri = Evento.__dataclass_params__  # type: ignore[attr-defined]
    assert parametri.frozen
    assert "__slots__" in vars(Evento)


def test_ogni_evento_ha_i_propri_slot() -> None:
    """L'unica delle tre proprietà che una sottoclasse può ancora perdere.

    Le altre due sono garantite dal linguaggio, e la prova è stata fatta rompendole
    apposta: `@dataclass` senza `frozen` su una sottoclasse di `Evento` non arriva
    nemmeno a esistere — «cannot inherit non-frozen dataclass from a frozen one» —, e i
    campi della base precedono sempre quelli di chi eredita, quindi `istante` resta
    primo per costruzione. Asserirle qui sarebbe controllare il compilatore.

    `slots=True` no: si dimentica in silenzio, la classe nasce, e le sue istanze tornano
    ad avere un `__dict__` in cui due thread possono scriversi di nascosto. Questa riga
    fallisce davvero, ed è stata vista fallire nominando la classe colpevole.
    """
    for classe in sottoclassi_di_evento():
        assert "__slots__" in vars(classe), classe.__name__


def test_un_evento_non_si_puo_modificare() -> None:
    evento = WriteSucceeded(istante=ISTANTE, documenti=100, durata_ms=12.5)
    with pytest.raises(FrozenInstanceError):
        evento.documenti = 0  # type: ignore[misc]
    assert evento.documenti == 100


def test_un_evento_non_accetta_attributi_nuovi() -> None:
    # `slots=True`: senza, un `frozen` congela i campi dichiarati e lascia comunque
    # aggiungere il proprio. Un evento che attraversa una coda e cresce per strada è il
    # modo in cui due thread tornano a condividere stato senza che nessuno lo scriva.
    evento = LatencySampled(istante=ISTANTE, operazione="insert", durata_ms=3.0)
    assert not hasattr(evento, "__dict__")
    with pytest.raises(AttributeError):
        evento.annotazione = "di passaggio"  # type: ignore[attr-defined]


def test_un_evento_e_confrontabile_per_valore() -> None:
    # Serve alle prove dei Task 5 e 6, che asseriscono su **sequenze** di eventi: senza
    # uguaglianza per valore l'asserzione dovrebbe smontare ogni oggetto campo per campo.
    primo = RetryAttempted(istante=ISTANTE, tentativo=1, attesa_ms=50.0, motivo="rete")
    secondo = RetryAttempted(istante=ISTANTE, tentativo=1, attesa_ms=50.0, motivo="rete")
    assert primo == secondo


def test_gli_otto_eventi_si_costruiscono() -> None:
    # Una prova noiosa che serve a una cosa sola: se una firma cambia, se ne accorge qui
    # e non dentro il primo caso d'uso che la usa.
    topologia = DescrizioneTopologia(tipo=TipoTopologia.SCONOSCIUTA, server=())
    costruiti: list[Evento] = [
        WriteSucceeded(istante=ISTANTE, documenti=10, durata_ms=1.0),
        WriteFailed(istante=ISTANTE, tipo_errore="NotPrimaryError", motivo="no primary"),
        RetryAttempted(istante=ISTANTE, tentativo=2, attesa_ms=100.0, motivo="rete"),
        LatencySampled(istante=ISTANTE, operazione="find", durata_ms=2.0),
        TopologyChanged(istante=ISTANTE, precedente=topologia, successiva=topologia),
        ServerStateChanged(
            istante=ISTANTE,
            indirizzo="mongo1:27017",
            precedente=RuoloServer.PRIMARIO,
            successivo=RuoloServer.IRRAGGIUNGIBILE,
        ),
        BackupProgressed(istante=ISTANTE, avanzamento=Progress(fase="dump", completati=1)),
        ChunkMigrated(
            istante=ISTANTE,
            collezione="lab.ordini",
            da_shard="shard1",
            a_shard="shard2",
            chunk="[MinKey, 100)",
        ),
    ]
    assert len(costruiti) == 8
    assert all(evento.istante == ISTANTE for evento in costruiti)


# --- I modelli ------------------------------------------------------------------------


def test_la_topologia_trova_il_primario_e_sa_dire_che_non_c_e() -> None:
    primario = DescrizioneServer(indirizzo="mongo1:27017", ruolo=RuoloServer.PRIMARIO)
    secondario = DescrizioneServer(indirizzo="mongo2:27017", ruolo=RuoloServer.SECONDARIO)

    con = DescrizioneTopologia(
        tipo=TipoTopologia.REPLICA_SET_CON_PRIMARIO, server=(primario, secondario)
    )
    assert con.ha_primario
    assert con.primario == primario

    # Lo stato che dura pochi secondi ed è tutta la scena del Blocco 2.
    senza = DescrizioneTopologia(
        tipo=TipoTopologia.REPLICA_SET_SENZA_PRIMARIO, server=(secondario,)
    )
    assert not senza.ha_primario
    assert senza.primario is None


def test_l_avanzamento_non_inventa_una_percentuale_che_non_ha() -> None:
    assert Progress(fase="dump", completati=25, totali=100).percentuale == 25.0
    # Nessun totale: la risposta onesta è «non lo so», non uno zero che a schermo
    # sembrerebbe una barra ferma.
    assert Progress(fase="dump", completati=25).percentuale is None
    assert Progress(fase="dump", completati=0, totali=0).percentuale is None


def test_i_modelli_sono_congelati_come_gli_eventi() -> None:
    conto = ContoShard(shard="shard1", documenti=20000, chunk=3)
    with pytest.raises(FrozenInstanceError):
        conto.documenti = 0  # type: ignore[misc]


# --- Le porte -------------------------------------------------------------------------
#
# I doppi veri arrivano al Task 4. Quelli qui sotto sono minimi apposta: servono a
# mostrare la proprietà dei `Protocol`, non a essere usati da qualcuno.


class OrologioDiProva:
    """Non eredita `Clock`, e non lo importa nemmeno. Ha i metodi giusti, e basta."""

    def __init__(self) -> None:
        self.adesso = ISTANTE

    def now(self) -> datetime:
        return self.adesso

    def sleep(self, secondi: float) -> None:
        self.adesso += timedelta(seconds=secondi)


class ArchivioDiProva:
    def __init__(self) -> None:
        self.documenti: list[Documento] = []

    def insert_many(self, documenti: Sequence[Documento]) -> int:
        self.documenti.extend(documenti)
        return len(documenti)

    def find_page(
        self, filtro: Documento, salta: int = 0, quanti: int = 20
    ) -> tuple[Documento, ...]:
        return tuple(self.documenti[salta : salta + quanti])

    def count(self, filtro: Documento) -> int:
        return len(self.documenti)

    def aggregate(self, pipeline: Sequence[Documento]) -> tuple[Documento, ...]:
        return ()


class RaccoglitoreDiProva:
    def __init__(self) -> None:
        self.ricevuti: list[Evento] = []

    def emit(self, evento: Evento) -> None:
        self.ricevuti.append(evento)


def test_un_oggetto_qualunque_soddisfa_la_porta_senza_ereditarla() -> None:
    # L'annotazione è la prova vera, e la fa mypy: se `OrologioDiProva` sbagliasse una
    # firma, `make app-check` fallirebbe su questa riga. A runtime resta la conferma che
    # l'oggetto funziona davvero attraverso la porta.
    orologio: Clock = OrologioDiProva()
    partenza = orologio.now()
    orologio.sleep(30)
    assert orologio.now() - partenza == timedelta(seconds=30)

    archivio: DocumentStore = ArchivioDiProva()
    assert archivio.insert_many([{"_id": 1}, {"_id": 2}]) == 2
    assert archivio.count({}) == 2

    raccoglitore: EventSink = RaccoglitoreDiProva()
    raccoglitore.emit(LatencySampled(istante=ISTANTE, operazione="find", durata_ms=1.0))


def test_le_porte_si_riconoscono_anche_a_runtime() -> None:
    assert isinstance(OrologioDiProva(), Clock)
    assert isinstance(ArchivioDiProva(), DocumentStore)
    assert isinstance(RaccoglitoreDiProva(), EventSink)
    # Le altre due esistono e sono controllabili allo stesso modo: qui basta nominarle
    # perché un `Protocol` non `runtime_checkable` solleverebbe `TypeError`.
    assert not isinstance(OrologioDiProva(), ClusterInspector)
    assert not isinstance(OrologioDiProva(), BackupTool)


def test_a_chi_manca_un_metodo_la_porta_si_chiude() -> None:
    class OrologioMonco:
        def now(self) -> datetime:
            return ISTANTE

    assert not isinstance(OrologioMonco(), Clock)


def test_il_controllo_a_runtime_guarda_i_nomi_e_non_le_firme() -> None:
    # Il limite, scritto come prova invece che come commento, perché è il punto in cui
    # qualcuno potrebbe credere che `isinstance` basti. Non basta: questo orologio ha i
    # due nomi giusti e una firma sbagliata, passa il controllo a runtime, e sarebbe
    # bocciato da mypy nel momento in cui lo si annotasse `Clock`. Il guardiano vero è
    # `make app-check`; questa riga dice perché.
    class OrologioConFirmaSbagliata:
        def now(self) -> datetime:
            return ISTANTE

        def sleep(self) -> None:  # manca `secondi`
            return None

    assert isinstance(OrologioConFirmaSbagliata(), Clock)
