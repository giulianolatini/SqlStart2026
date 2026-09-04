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

from mongolab.domain.eventi import (
    BackupProgressed,
    Evento,
    FaseIniziata,
    LatencySampled,
    PrimaryWaitAbandoned,
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
    Distribuzione,
    Documento,
    Piano,
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
    QueryPlanner,
    Regia,
)
from tests.aiutanti import sottoclassi_di_evento

ISTANTE = datetime(2026, 9, 18, 9, 30, 0, tzinfo=UTC)


# --- Gli eventi -----------------------------------------------------------------------


def test_gli_eventi_del_design_sono_nove_e_sono_quelli() -> None:
    """Otto dal §6.3, il nono da ADR-0082, il decimo da ADR-0094, meno uno: ADR-0103.

    `ChunkMigrated` è uscito al Task 15, e non perché fosse scomodo da emettere: in
    1153 giri di balancer questo cluster non ha migrato un chunk nemmeno una volta
    ([M-049](../../docs/Sources.md#m-049)). La sua stessa docstring aveva scritto la
    condizione — «una voce in `Sources.md` e un ADR, non un campo morto» — e questa
    prova è il posto in cui quella condizione si paga.

    Questa prova non elenca per pignoleria: elenca perché il costo di aggiungere un
    evento deve restare **visibile**. Un dominio che cresce in silenzio è un dominio in
    cui, fra tre task, nessuno sa più quali fatti l'applicazione sa raccontare.
    """
    attesi = {
        "BackupProgressed",
        "FaseIniziata",
        "LatencySampled",
        "PrimaryWaitAbandoned",
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
    ad avere un `__dict__`. L'assegnazione normale resta bloccata da `frozen`, ma
    `object.__setattr__` e la scrittura diretta nel `__dict__` passano — misurato in
    `app/docs/Sources.md`, M-003. Questa riga fallisce davvero, ed è stata vista fallire
    nominando la classe colpevole.
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


def test_i_nove_eventi_si_costruiscono() -> None:
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
        PrimaryWaitAbandoned(
            istante=ISTANTE,
            atteso_ms=30_000.0,
            pazienza_ms=30_000.0,
            ultimo_primario="mongo1:27017",
        ),
        FaseIniziata(istante=ISTANTE, fase="guasto", descrizione="spengo il primario"),
    ]
    assert len(costruiti) == 9
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


def test_una_distribuzione_distingue_i_tre_casi_che_la_tupla_confondeva() -> None:
    """Il punto aperto che la vecchia firma dichiarava, chiuso qui (ADR-0104).

    `shard_distribution()` restituiva una tupla, e la tupla vuota voleva dire due cose:
    «non è uno sharded cluster» e «è uno sharded cluster, ma questa collezione non è
    distribuita». La scena del Task 15 esiste per mostrare **esattamente la seconda**, e
    una scena non può poggiare su un valore ambiguo.
    """
    fuori = Distribuzione(collezione="lab.ordini", distribuita=False, primario=None, conti=())
    assert not fuori.in_un_cluster
    assert not fuori.distribuita
    assert fuori.documenti == 0

    intera = Distribuzione(
        collezione="lab.carico-20260918-093000",
        distribuita=False,
        primario="shard1rs",
        conti=(ContoShard(shard="shard1rs", documenti=300, chunk=0),),
    )
    assert intera.in_un_cluster
    assert not intera.distribuita
    assert intera.documenti == 300
    assert intera.chunk == 0

    sparsa = Distribuzione(
        collezione="lab.ordini",
        distribuita=True,
        primario="shard1rs",
        conti=(
            ContoShard(shard="shard1rs", documenti=9860, chunk=1),
            ContoShard(shard="shard2rs", documenti=10140, chunk=1),
        ),
    )
    assert sparsa.in_un_cluster
    assert sparsa.distribuita
    assert sparsa.documenti == 20000
    assert sparsa.chunk == 2


def test_la_quota_di_uno_shard_e_none_quando_non_c_e_niente_da_ripartire() -> None:
    """Zero documenti su zero documenti non è «lo zero per cento», è una domanda vuota."""
    vuota = Distribuzione(
        collezione="lab.ordini",
        distribuita=True,
        primario="shard1rs",
        conti=(ContoShard(shard="shard1rs", documenti=0, chunk=1),),
    )
    assert vuota.quota("shard1rs") is None
    assert vuota.quota("shard2rs") is None

    piena = Distribuzione(
        collezione="lab.ordini",
        distribuita=True,
        primario="shard1rs",
        conti=(
            ContoShard(shard="shard1rs", documenti=1, chunk=1),
            ContoShard(shard="shard2rs", documenti=3, chunk=1),
        ),
    )
    assert piena.quota("shard1rs") == pytest.approx(25.0)
    assert piena.quota("shard2rs") == pytest.approx(75.0)
    # Uno shard che non compare non ha «zero documenti»: non ha risposto affatto.
    assert piena.quota("shard3rs") is None


def test_un_piano_e_mirato_quando_il_router_interroga_un_solo_shard() -> None:
    """`SINGLE_SHARD` contro `SHARD_MERGE`, che è il Passo 3 del Task 15 in due parole."""
    mirata = Piano(filtro={"_id": 42}, stadio="SINGLE_SHARD", shard=("shard2rs",))
    assert mirata.mirata

    ovunque = Piano(filtro={"citta": "Ancona"}, stadio="SHARD_MERGE", shard=("shard1rs", "shard2rs"))
    assert not ovunque.mirata

    # Il caso che la sala non si aspetta: stesso campo della chiave, ma per intervallo.
    intervallo = Piano(
        filtro={"_id": {"$gte": 100, "$lt": 200}},
        stadio="SHARD_MERGE",
        shard=("shard1rs", "shard2rs"),
    )
    assert not intervallo.mirata


def test_un_piano_senza_shard_non_e_mirato() -> None:
    """Nessuno shard non è «uno shard». Un `explain` fuori da un cluster non risponde qui."""
    assert not Piano(filtro={}, stadio="COLLSCAN", shard=()).mirata


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


class PianificatoreDiProva:
    """Il minimo che soddisfi `QueryPlanner`: un metodo, e nessun documento in casa."""

    def explain(self, filtro: Documento) -> Piano:
        return Piano(filtro=filtro, stadio="SINGLE_SHARD", shard=("shard1rs",))


class RaccoglitoreDiProva:
    def __init__(self) -> None:
        self.ricevuti: list[Evento] = []

    def emit(self, evento: Evento) -> None:
        self.ricevuti.append(evento)


class RegiaDiProva:
    """Annota gli ordini. Nessun metodo nomina Docker: la porta non sa chi li esegue."""

    def __init__(self) -> None:
        self.ordini: list[tuple[str, str]] = []

    def ferma(self, nodo: str) -> None:
        self.ordini.append(("ferma", nodo))

    def riavvia(self, nodo: str) -> None:
        self.ordini.append(("riavvia", nodo))

    def sospendi(self, nodo: str) -> None:
        self.ordini.append(("sospendi", nodo))

    def risveglia(self, nodo: str) -> None:
        self.ordini.append(("risveglia", nodo))


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

    annotata = RegiaDiProva()
    regia: Regia = annotata
    regia.ferma("mongo-1")
    regia.sospendi("mongo-2")
    assert annotata.ordini == [("ferma", "mongo-1"), ("sospendi", "mongo-2")]


def test_il_pianificatore_e_una_porta_a_se_non_un_quinto_metodo_dell_archivio() -> None:
    """`explain` sta su una porta sua, e la ragione è nei doppi (ADR-0105).

    Metterlo su `DocumentStore` avrebbe obbligato **quattro** doppi a rispondere: uno che
    esiste per rompersi, uno che esiste per essere lento, uno che esiste per non leggere.
    Nessuno dei tre ha un router da interrogare, quindi tutti e tre avrebbero risposto
    sollevando — cioè la porta avrebbe dichiarato una promessa che tre implementazioni su
    cinque non mantengono. Una porta esiste per un chiamante, non per un oggetto.
    """
    pianificatore: QueryPlanner = PianificatoreDiProva()
    piano = pianificatore.explain({"_id": 42})

    assert piano.filtro == {"_id": 42}
    assert piano.mirata

    assert isinstance(PianificatoreDiProva(), QueryPlanner)
    # E l'archivio non lo è: i suoi quattro metodi non ne fanno un pianificatore.
    assert not isinstance(ArchivioDiProva(), QueryPlanner)


def test_le_porte_si_riconoscono_anche_a_runtime() -> None:
    assert isinstance(OrologioDiProva(), Clock)
    assert isinstance(ArchivioDiProva(), DocumentStore)
    assert isinstance(RaccoglitoreDiProva(), EventSink)
    assert isinstance(RegiaDiProva(), Regia)
    # Le altre due esistono e sono controllabili allo stesso modo: qui basta nominarle
    # perché un `Protocol` non `runtime_checkable` solleverebbe `TypeError`.
    assert not isinstance(OrologioDiProva(), ClusterInspector)
    assert not isinstance(OrologioDiProva(), BackupTool)


def test_una_regia_che_ferma_ma_non_sospende_non_e_una_regia() -> None:
    """I quattro verbi sono quattro perché la scena ne mostra due coppie.

    Fermare e riavviare sono il nodo morto: la connessione viene rifiutata subito.
    Sospendere e risvegliare sono il nodo irraggiungibile ma vivo: nessuno rifiuta
    niente, e il client aspetta il timeout. Una regia che sa solo la prima coppia
    saprebbe raccontare mezzo Blocco 2, ed è il muro che questa riga alza.
    """

    class RegiaCheSoloFerma:
        def ferma(self, nodo: str) -> None: ...

        def riavvia(self, nodo: str) -> None: ...

    assert not isinstance(RegiaCheSoloFerma(), Regia)


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
