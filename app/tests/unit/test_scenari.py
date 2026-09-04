"""Lo scenario del failover: la sequenza delle fasi, e i due numeri che la chiudono.

**Le asserzioni sono sulla sequenza, non sui tempi**, ed è la richiesta esplicita del
Passo 4 del Task 13. Un'elezione vera dura fra otto e dieci secondi ([V-031]); una prova
che li aspettasse costerebbe dieci secondi a ogni salvataggio, e nessuno la eseguirebbe.
Qui la cronaca dell'elezione è **fornita** allo scenario — è ciò che `drena` restituisce —
e quello che si verifica è che lo scenario la legga giusta: le fasi nell'ordine, gli
ordini alla regia nell'ordine, e i due numeri calcolati da quella cronaca.

Gli istanti della cronaca finta non sono inventati: 9 812 ms è l'elezione misurata da
[V-029] contro lo stack 02 con `docker kill`. Se un giorno lo scenario sbagliasse
aritmetica, questa prova fallirebbe con un numero che qualcuno riconosce.
"""

from datetime import UTC, datetime, timedelta
from typing import Sequence

import pytest

from mongolab.application.scenari import (
    Attesa,
    Copione,
    CronometroInterruzione,
    EsitoFailover,
    ModoGuasto,
    ScenarioFailover,
    senza_attesa,
    sorveglia,
)
from mongolab.application.workload import WorkloadRunner
from mongolab.domain.eventi import Evento, FaseIniziata, TopologyChanged
from mongolab.domain.modelli import (
    DescrizioneServer,
    DescrizioneTopologia,
    Documento,
    RuoloServer,
    TipoTopologia,
)
from tests.doppi import (
    InMemoryStore,
    OrologioCheScorre,
    RecordingSink,
    RegiaCheRifiuta,
    RegiaFinta,
)

ISTANTE = datetime(2026, 9, 18, 9, 30, 0, tzinfo=UTC)

# L'elezione misurata da V-029, al millisecondo. Vedi il docstring del modulo.
ELEZIONE_MS = 9812.0

UNO = "mongo-rs-1:27017"
DUE = "mongo-rs-2:27017"


def _topologia(primario: str | None) -> DescrizioneTopologia:
    """Due membri, uno dei quali primario — oppure nessuno, ed è l'interruzione."""
    if primario is None:
        return DescrizioneTopologia(
            tipo=TipoTopologia.REPLICA_SET_SENZA_PRIMARIO,
            server=(
                DescrizioneServer(UNO, RuoloServer.IRRAGGIUNGIBILE),
                DescrizioneServer(DUE, RuoloServer.SECONDARIO),
            ),
            nome_set="rs0",
        )
    altro = DUE if primario == UNO else UNO
    return DescrizioneTopologia(
        tipo=TipoTopologia.REPLICA_SET_CON_PRIMARIO,
        server=(
            DescrizioneServer(primario, RuoloServer.PRIMARIO),
            DescrizioneServer(altro, RuoloServer.SECONDARIO),
        ),
        nome_set="rs0",
    )


CON_UNO = _topologia(UNO)
SENZA = _topologia(None)
CON_DUE = _topologia(DUE)

AVVIO = TopologyChanged(ISTANTE, _topologia(None), CON_UNO)
PERDITA = TopologyChanged(ISTANTE + timedelta(seconds=5), CON_UNO, SENZA)
ELEZIONE = TopologyChanged(
    ISTANTE + timedelta(seconds=5, milliseconds=ELEZIONE_MS), SENZA, CON_DUE
)


class PonteFinto:
    """La funzione `drena` dello scenario, con un copione che reagisce alla regia.

    Non un elenco a giri fissi: il numero di drenaggi dipende da quanto ci mette il
    carico, e una prova che ci contasse sopra misurerebbe la macchina. Qui l'avvio esce
    subito, e la perdita del primario con l'elezione escono al primo drenaggio **dopo**
    che la regia ha dato il suo ordine. È il copione del Blocco 2 ridotto a tre righe, e
    l'unica cosa che promette è l'ordine.

    Consegna tutto quello che è pronto, in una lista, perché è ciò che fa `SdamBridge`:
    un doppio che ne restituisse uno per volta metterebbe lo scenario alla prova di una
    coda che nella realtà non esiste, e lo lascerebbe scoperto su quella che esiste.
    """

    def __init__(self, regia: RegiaFinta) -> None:
        self._regia = regia
        self._consegnati: list[Evento] = []
        self.drenaggi = 0

    def drena(self) -> list[Evento]:
        self.drenaggi += 1
        rotto = bool(self._regia.ordini)
        pronti: list[Evento] = [
            evento
            for evento in (AVVIO, PERDITA, ELEZIONE)
            if evento not in self._consegnati and (evento is AVVIO or rotto)
        ]
        self._consegnati.extend(pronti)
        return pronti


class ArchivioCheDimentica(InMemoryStore):
    """Conferma tutto e ne conserva solo una parte: è `w: 1` durante un'elezione.

    Il guasto che questo doppio riproduce è quello che il Blocco 2 esiste per mostrare, e
    che [V-016] ha misurato in cento scritture perdute: il primario conferma, cade prima
    di aver replicato, e il nuovo primario non ha mai visto quei documenti. Il client li
    ha contati come riusciti — perché lo erano, per la promessa che aveva chiesto — e
    dopo il failover non li ritrova.
    """

    def __init__(self, *, tiene_una_ogni: int = 2) -> None:
        super().__init__()
        self._tiene_una_ogni = tiene_una_ogni
        self._visti = 0
        self.confermati = 0

    def insert_many(self, documenti: Sequence[Documento]) -> int:
        tenuti: list[Documento] = []
        for documento in documenti:
            self._visti += 1
            if self._visti % self._tiene_una_ogni == 0:
                tenuti.append(documento)
        if tenuti:
            super().insert_many(tenuti)
        self.confermati += len(documenti)
        return len(documenti)


def _scenario(
    *,
    archivio: InMemoryStore | None = None,
    regia: RegiaFinta | None = None,
    copione: Copione | None = None,
) -> tuple[ScenarioFailover, RecordingSink, RegiaFinta, InMemoryStore]:
    """Il cablaggio della prova, in un posto solo perché sei prove lo ripetono."""
    deposito = archivio if archivio is not None else InMemoryStore()
    comando = regia if regia is not None else RegiaFinta()
    orologio = OrologioCheScorre(ISTANTE)
    sink = RecordingSink()
    ponte = PonteFinto(comando)
    corsa = WorkloadRunner(deposito, orologio, sink)
    scenario = ScenarioFailover(
        deposito,
        corsa,
        comando,
        orologio,
        sink,
        ponte.drena,
        copione=copione if copione is not None else Copione(nodo="mongo-1", scritture=6),
    )
    return scenario, sink, comando, deposito


def _fasi(sink: RecordingSink) -> list[str]:
    return [e.fase for e in sink.eventi if isinstance(e, FaseIniziata)]


# --- Il cronometro: l'interruzione dedotta dagli eventi, non dai sondaggi ---------------


def test_il_cronometro_misura_dall_evento_e_non_dal_campionamento() -> None:
    """I 9 812 ms escono esatti, perché escono dagli istanti che il driver ha segnato.

    `TopologyWatcher` guarda ogni 500 ms, e con lui questa misura avrebbe una
    granularità di mezzo secondo su un numero che finisce su una slide. Gli eventi del
    ponte portano l'istante in cui il **driver** ha saputo, ed è la ragione per cui
    l'interruzione si deduce da loro (ADR-0096).
    """
    cronometro = CronometroInterruzione()
    for evento in (AVVIO, PERDITA, ELEZIONE):
        cronometro.considera(evento)

    interruzione = cronometro.prima
    assert interruzione is not None
    assert interruzione.durata_ms == ELEZIONE_MS
    assert interruzione.primario_prima == UNO
    assert interruzione.primario_dopo == DUE
    assert interruzione.e_un_failover


def test_il_cronometro_non_conta_l_attesa_del_primo_primario() -> None:
    """All'avvio il client non ha ancora visto nessun primario, e non è un'interruzione.

    È la trappola vera di questa misura. Un client che si connette passa per
    `sconosciuta` e `replica set senza primario` prima di trovarne uno: contare quel
    tratto vorrebbe dire aprire l'interruzione all'istante della connessione e chiuderla
    al primo primario, e il numero di testa del Blocco 2 diventerebbe il tempo di
    avviamento del client sommato all'elezione.
    """
    cronometro = CronometroInterruzione()
    cronometro.considera(TopologyChanged(ISTANTE, _topologia(None), _topologia(None)))
    assert cronometro.prima is None

    cronometro.considera(AVVIO)
    assert cronometro.prima is None


def test_il_cronometro_lascia_aperta_l_interruzione_che_non_si_chiude() -> None:
    """Nessun primario ritrovato: durata `None`, non zero. La regola di `Interruzione`."""
    cronometro = CronometroInterruzione()
    cronometro.considera(AVVIO)
    cronometro.considera(PERDITA)

    interruzione = cronometro.prima
    assert interruzione is not None
    assert not interruzione.chiusa
    assert interruzione.durata_ms is None


def test_il_cronometro_tiene_la_prima_interruzione_e_ricorda_le_altre() -> None:
    """Un nodo che rientra può far ballare la topologia una seconda volta.

    Il numero della scena è il **primo** guasto, quello provocato dalla regia; le altre
    non si buttano, perché una seconda interruzione durante la ripresa è un fatto che chi
    guarda la registrazione ha il diritto di ritrovare.
    """
    dopo = ISTANTE + timedelta(seconds=40)
    cronometro = CronometroInterruzione()
    for evento in (
        AVVIO,
        PERDITA,
        ELEZIONE,
        TopologyChanged(dopo, CON_DUE, SENZA),
        TopologyChanged(dopo + timedelta(milliseconds=300), SENZA, CON_DUE),
    ):
        cronometro.considera(evento)

    assert len(cronometro.interruzioni) == 2
    prima = cronometro.prima
    assert prima is not None
    assert prima.durata_ms == ELEZIONE_MS
    assert cronometro.interruzioni[1].durata_ms == 300.0


# --- La scena: sei fasi, nell'ordine ----------------------------------------------------


def test_la_scena_annuncia_le_sue_sei_fasi_nell_ordine_del_copione() -> None:
    """L'asserzione del Passo 4: la sequenza, leggibile in una lista di stringhe."""
    scenario, sink, _, _ = _scenario()

    scenario.esegui()

    assert _fasi(sink) == [
        "carico",
        "guasto",
        "elezione",
        "ripresa",
        "recupero",
        "bilancio",
    ]


def test_la_scena_ferma_il_nodo_e_poi_lo_riavvia_in_quest_ordine() -> None:
    """Fermare dopo aver misurato darebbe zero millisecondi, e nessuno se ne accorgerebbe."""
    scenario, _, regia, _ = _scenario()

    scenario.esegui()

    assert regia.ordini == [("ferma", "mongo-1"), ("riavvia", "mongo-1")]


def test_col_modo_sospendi_la_scena_congela_il_nodo_invece_di_spegnerlo() -> None:
    """Il supplemento del Passo 3: irraggiungibile ma vivo, cioè timeout e non rifiuto."""
    scenario, _, regia, _ = _scenario(
        copione=Copione(nodo="mongo-1", modo=ModoGuasto.SOSPENDI, scritture=6)
    )

    scenario.esegui()

    assert regia.ordini == [("sospendi", "mongo-1"), ("risveglia", "mongo-1")]


def test_la_scena_chiude_con_i_due_numeri() -> None:
    """Durata dell'interruzione e scritture perse: è ciò per cui il Blocco 2 esiste."""
    scenario, _, _, _ = _scenario()

    esito = scenario.esegui()

    assert isinstance(esito, EsitoFailover)
    assert esito.durata_interruzione_ms == ELEZIONE_MS
    assert esito.confermate > 0
    # `InMemoryStore` conserva tutto ciò che conferma: è il `w: majority` di V-033.
    assert esito.ritrovate == esito.confermate
    assert esito.scritture_perse == 0


def test_con_un_archivio_che_dimentica_le_scritture_perse_si_vedono() -> None:
    """La prova che il numero non è sempre zero per costruzione.

    Senza di lei «zero scritture perse» sarebbe un valore che lo scenario non saprebbe
    calcolare diversamente, e la slide di V-033 poggerebbe su un'aritmetica mai vista
    sbagliare.
    """
    scenario, _, _, deposito = _scenario(archivio=ArchivioCheDimentica())

    esito = scenario.esegui()

    assert esito.confermate > esito.ritrovate
    assert esito.scritture_perse == esito.confermate - esito.ritrovate


def test_la_scena_passa_al_sink_tutto_quello_che_il_ponte_le_consegna() -> None:
    """Lo scenario non trattiene niente: la cronaca del driver arriva intera alla sala."""
    scenario, sink, _, _ = _scenario()

    scenario.esegui()

    cambi = [e for e in sink.eventi if isinstance(e, TopologyChanged)]
    assert cambi == [AVVIO, PERDITA, ELEZIONE]


def test_a_ogni_fase_l_attesa_riceve_l_evento_che_la_annuncia() -> None:
    """È `--step`: sei pause, ciascuna con davanti il titolo di ciò che sta per accadere.

    L'attesa riceve l'evento e non una stringa perché è la stessa cosa che vede la sala:
    una pausa che annunciasse una fase diversa da quella scritta a schermo sarebbe un
    inciampo dal vivo, e qui è impossibile per costruzione.
    """
    viste: list[FaseIniziata] = []
    scenario, sink, _, _ = _scenario()

    scenario.esegui(attesa=viste.append)

    assert [e.fase for e in viste] == _fasi(sink)
    assert all(e.descrizione for e in viste)


def test_senza_attesa_non_fa_niente_ed_e_il_modo_senza_step() -> None:
    """Una sola implementazione, due modi: il modo automatico è questa funzione vuota.

    Provare una funzione vuota sembra eccessivo finché non si guarda che cosa protegge:
    è il **predefinito** di `esegui`, cioè ciò che gira quando si registra il piano B. Il
    giorno in cui qualcuno ci mettesse dentro una stampa di comodo, la registrazione
    mostrerebbe una riga che dal vivo non c'è.
    """
    attesa: Attesa = senza_attesa
    attesa(FaseIniziata(ISTANTE, "guasto", "fermo il primario"))


def test_se_la_regia_non_puo_fermare_niente_la_scena_si_ferma_subito() -> None:
    """Non si prosegue fingendo: un failover mai avvenuto ha gli stessi numeri di uno
    perfetto, e sarebbe la bugia peggiore che questa applicazione possa raccontare.
    """
    orologio = OrologioCheScorre(ISTANTE)
    sink = RecordingSink()
    deposito = InMemoryStore()
    regia = RegiaCheRifiuta()
    scenario = ScenarioFailover(
        deposito,
        WorkloadRunner(deposito, orologio, sink),
        regia,
        orologio,
        sink,
        lambda: [],
        copione=Copione(nodo="mongo-1", scritture=6),
    )

    with pytest.raises(RuntimeError):
        scenario.esegui()

    assert _fasi(sink) == ["carico", "guasto"]


# --- Il ciclo di `watch`, che al Task 13 esce da `cli.py` -------------------------------


def test_sorveglia_drena_a_ogni_giro_e_aspetta_fra_uno_e_l_altro() -> None:
    """Il ciclo che `watch` usava dentro `cli.py`, adesso provabile senza Typer.

    Le attese sono `giri - 1` e non `giri`: dopo l'ultimo sguardo non c'è niente da
    aspettare, e mezzo secondo speso lì è mezzo secondo in cui la scena è già finita e lo
    schermo è fermo.
    """
    orologio = OrologioCheScorre(ISTANTE)
    sink = RecordingSink()
    consegne: list[list[Evento]] = [[AVVIO], [], [PERDITA]]

    def drena() -> list[Evento]:
        return consegne.pop(0) if consegne else []

    sorveglia(drena, sink, orologio, giri=3, intervallo_ms=500.0)

    assert sink.eventi == [AVVIO, PERDITA]
    assert orologio.attese == [0.5, 0.5]


def test_sorveglia_con_un_giro_solo_non_aspetta_affatto() -> None:
    orologio = OrologioCheScorre(ISTANTE)
    sink = RecordingSink()

    uno: list[Evento] = [AVVIO]
    sorveglia(lambda: uno, sink, orologio, giri=1, intervallo_ms=500.0)

    assert sink.eventi == [AVVIO]
    assert orologio.attese == []


def test_sorveglia_rifiuta_zero_giri() -> None:
    """Zero sguardi è un comando che si rifiuta di guardare: meglio dirlo che piantarsi."""
    orologio = OrologioCheScorre(ISTANTE)
    with pytest.raises(ValueError, match="giri"):
        sorveglia(lambda: [], RecordingSink(), orologio, giri=0, intervallo_ms=500.0)
