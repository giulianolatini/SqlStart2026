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
from pathlib import Path
from typing import Sequence

import pytest

from mongolab.application.scenari import (
    Attesa,
    Copione,
    CopioneBackup,
    CopioneRestore,
    CopioneSharding,
    CronometroInterruzione,
    EsitoBackup,
    EsitoFailover,
    EsitoRestore,
    EsitoSharding,
    ModoGuasto,
    Ritmo,
    ScenarioBackup,
    ScenarioFailover,
    ScenarioRestore,
    ScenarioSharding,
    senza_attesa,
    sorveglia,
)
from mongolab.application.workload import Riepilogo, WorkloadRunner
from mongolab.domain.eventi import (
    BackupProgressed,
    Evento,
    FaseIniziata,
    TopologyChanged,
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
from tests.doppi import (
    FakeBackup,
    FakeInspector,
    FakePlanner,
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


# --- L'Atto III: il backup a caldo, con il ritmo accanto --------------------------------

DESTINAZIONE = Path("/lab/backup/2026-09-18")

AVANZAMENTI = (
    Progress("dump", 0, None, "writing lab.carico to /lab/backup"),
    Progress("dump", 5000, 20000, "lab.carico  5000/20000  (25.0%)"),
    Progress("dump", 20000, 20000, "done dumping lab.carico (20000 documents)"),
)
"""Tre righe come quelle vere: la prima senza denominatore, perché `mongodump` annuncia
la collezione prima di sapere quanto è grande. È il caso che tiene onesta
`Progress.percentuale`, ed è la ragione per cui `totali` è opzionale."""


TETTO_LARGHISSIMO = 3600.0
"""Un'ora di tetto, che nelle prove non si raggiunge mai — ed è il punto.

Con `OrologioCheScorre(passo_s=0.001)` un'ora di scadenza sono tre milioni e mezzo di
scritture: se `finche` non arrivasse ai worker, queste prove non fallirebbero con
un'asserzione, resterebbero appese. Il conteggio piccolo che asseriscono è la prova che il
dump — e non il tetto — ha fermato il carico."""


def _scena_backup(
    strumento: FakeBackup,
    *,
    archivio: InMemoryStore | None = None,
    sink: RecordingSink | None = None,
    copione: CopioneBackup | None = None,
) -> tuple[ScenarioBackup, InMemoryStore, RecordingSink]:
    """Lo scenario con tutti i doppi al loro posto. Il ponte è vuoto: qui non c'è
    topologia da raccontare, e un `PonteFinto` aggiungerebbe eventi che nessuna di queste
    prove guarda."""
    archivio = archivio if archivio is not None else InMemoryStore()
    sink = sink if sink is not None else RecordingSink()
    orologio = OrologioCheScorre(ISTANTE, passo_s=0.001)
    scenario = ScenarioBackup(
        archivio,
        WorkloadRunner(archivio, orologio, sink),
        strumento,
        orologio,
        sink,
        lambda: [],
        copione=copione
        if copione is not None
        else CopioneBackup(
            destinazione=DESTINAZIONE, carico_s=0.02, tetto_s=TETTO_LARGHISSIMO
        ),
    )
    return scenario, archivio, sink


def test_la_scena_del_backup_ha_tre_fasi_nell_ordine() -> None:
    """Carico, dump, bilancio — e il carico **prima** del dump, non insieme.

    Senza la prima fase il numero della seconda non dice niente: «duemila scritture al
    secondo durante il dump» è un dato solo se accanto c'è quante ne faceva prima. È la
    stessa ragione per cui `ScenarioFailover` ha una fase «carico» che sembra non servire
    a niente.
    """
    scenario, _, sink = _scena_backup(FakeBackup(AVANZAMENTI))

    esito = scenario.esegui()

    assert esito.fasi == ("carico", "dump", "bilancio")
    annunci = [evento for evento in sink.eventi if isinstance(evento, FaseIniziata)]
    assert [evento.fase for evento in annunci] == ["carico", "dump", "bilancio"]


def test_il_dump_va_dove_dice_il_copione_e_una_volta_sola() -> None:
    strumento = FakeBackup(AVANZAMENTI)
    scenario, _, _ = _scena_backup(strumento)

    esito = scenario.esegui()

    assert strumento.dump_chiesti == [DESTINAZIONE]
    assert esito.destinazione == DESTINAZIONE


def test_ogni_avanzamento_del_dump_arriva_a_schermo_mentre_procede() -> None:
    """Gli avanzamenti diventano eventi, e l'ultimo evento del dump precede il bilancio.

    Che siano eventi e non un valore di ritorno è tutta la differenza fra mostrare il dump
    e raccontarlo dopo: la porta promette «l'avanzamento **mentre** procede», e questa è
    la prova che lo scenario non lo accumula per consegnarlo alla fine.
    """
    scenario, _, sink = _scena_backup(FakeBackup(AVANZAMENTI))

    esito = scenario.esegui()

    passati = [e for e in sink.eventi if isinstance(e, BackupProgressed)]
    assert [e.avanzamento for e in passati] == list(AVANZAMENTI)
    assert esito.avanzamenti == AVANZAMENTI
    ultimo_dump = max(i for i, e in enumerate(sink.eventi) if isinstance(e, BackupProgressed))
    bilancio = next(
        i
        for i, e in enumerate(sink.eventi)
        if isinstance(e, FaseIniziata) and e.fase == "bilancio"
    )
    assert ultimo_dump < bilancio


def test_il_carico_della_seconda_fase_finisce_quando_finisce_il_dump() -> None:
    """Il motivo per cui `finche` esiste, verificato dove serve.

    Il tetto è un'ora: se a fermare il carico fosse lui, questa prova non tornerebbe. È
    anche la ragione per cui la finestra del dump si misura invece di sceglierla — mezzo
    secondo di `mongodump` dentro venti secondi di carico produce una media che il crollo
    non lo mostra nemmeno se c'è.
    """
    scenario, _, _ = _scena_backup(FakeBackup(AVANZAMENTI))

    esito = scenario.esegui()

    assert esito.durante.riepilogo.scritture < 1000


def test_un_dump_che_si_rompe_non_lascia_il_carico_a_girare() -> None:
    """L'errore risale, e il carico si ferma **prima** che risalga.

    Senza lo spegnimento nel `finally`, l'errore del dump uscirebbe dal ciclo e il pool
    aspetterebbe il carico fino al tetto: un'eccezione consegnata un'ora dopo il fatto. In
    sala sarebbe uno schermo fermo senza spiegazione; qui sarebbe una prova appesa.
    """
    rotto = FakeBackup(AVANZAMENTI[:2], errore=RuntimeError("mongodump: exit 1"))
    scenario, _, sink = _scena_backup(rotto)

    with pytest.raises(RuntimeError, match="exit 1"):
        scenario.esegui()

    passati = [e for e in sink.eventi if isinstance(e, BackupProgressed)]
    assert len(passati) == 2


def test_il_bilancio_conta_i_documenti_sopravvissuti_al_dump() -> None:
    archivio = InMemoryStore()
    archivio.insert_many([{"indice": posto} for posto in range(7)])
    scenario, _, _ = _scena_backup(FakeBackup(AVANZAMENTI), archivio=archivio)

    esito = scenario.esegui()

    assert esito.documenti == archivio.count({})
    assert esito.documenti >= 7


def test_anche_la_scena_del_backup_si_ferma_a_ogni_fase_con_step() -> None:
    fermate: list[str] = []
    attesa: Attesa = lambda evento: fermate.append(evento.fase)  # noqa: E731
    scenario, _, _ = _scena_backup(FakeBackup(AVANZAMENTI))

    scenario.esegui(attesa=attesa)

    assert fermate == ["carico", "dump", "bilancio"]


# --- Il ritmo: un riepilogo diventa un throughput solo se si sa la finestra -------------


def _riepilogo(documenti: int) -> Riepilogo:
    return Riepilogo(
        scritture=documenti,
        riuscite=documenti,
        fallite=0,
        ritentate=0,
        documenti_confermati=documenti,
        latenze=None,
    )


def test_il_ritmo_divide_i_documenti_per_la_finestra() -> None:
    assert Ritmo(_riepilogo(2000), durata_s=2.0).documenti_al_secondo == 1000.0


def test_una_finestra_nulla_non_produce_un_throughput_infinito() -> None:
    """Zero secondi di finestra è un dump che è finito prima di cominciare — su una
    macchina veloce con un database vuoto succede. Dividere per zero darebbe una slide con
    `inf` sopra."""
    assert Ritmo(_riepilogo(10), durata_s=0.0).documenti_al_secondo is None


def test_la_tenuta_e_il_rapporto_fra_i_due_ritmi() -> None:
    """Il numero che la promessa del copione mette alla prova: il dump non fa crollare il
    ritmo. Uno significa nessun calo, zero virgola nove un dieci per cento."""
    esito = _esito_backup(prima=1000.0, durante=900.0)

    assert esito.tenuta == pytest.approx(0.9)
    assert esito.calo_percentuale == pytest.approx(10.0)


def test_senza_un_ritmo_prima_non_c_e_niente_da_confrontare() -> None:
    esito = _esito_backup(prima=0.0, durante=900.0)

    assert esito.tenuta is None
    assert esito.calo_percentuale is None


def _esito_backup(*, prima: float, durante: float) -> EsitoBackup:
    return EsitoBackup(
        fasi=("carico", "dump", "bilancio"),
        prima=Ritmo(_riepilogo(int(prima)), durata_s=1.0),
        durante=Ritmo(_riepilogo(int(durante)), durata_s=1.0),
        destinazione=DESTINAZIONE,
        avanzamenti=AVANZAMENTI,
        documenti=int(prima) + int(durante),
    )


# --- L'Atto III, seconda metà: il restore e i due conteggi ------------------------------

SORGENTE = Path("/lab/backup/2026-09-18")


def _scena_restore(
    strumento: FakeBackup,
    *,
    origine: InMemoryStore,
    destinazione: InMemoryStore,
    sink: RecordingSink | None = None,
) -> tuple[ScenarioRestore, RecordingSink]:
    sink = sink if sink is not None else RecordingSink()
    scenario = ScenarioRestore(
        origine,
        destinazione,
        strumento,
        OrologioCheScorre(ISTANTE, passo_s=0.001),
        sink,
        copione=CopioneRestore(sorgente=SORGENTE, database="lab_restore"),
    )
    return scenario, sink


def _archivio_con(quanti: int) -> InMemoryStore:
    archivio = InMemoryStore()
    if quanti:
        archivio.insert_many([{"indice": posto} for posto in range(quanti)])
    return archivio


def test_la_scena_del_restore_ha_due_fasi_nell_ordine() -> None:
    scenario, sink = _scena_restore(
        FakeBackup(AVANZAMENTI),
        origine=_archivio_con(10),
        destinazione=_archivio_con(10),
    )

    esito = scenario.esegui()

    assert esito.fasi == ("restore", "verifica")
    annunci = [e.fase for e in sink.eventi if isinstance(e, FaseIniziata)]
    assert annunci == ["restore", "verifica"]


def test_il_restore_riceve_la_sorgente_e_il_database_di_destinazione() -> None:
    """Su un database **diverso**, e non è un dettaglio di prudenza: un restore sopra
    l'originale cancellerebbe la sola copia della differenza che la scena vuole mostrare —
    e in sala non ci sarebbe modo di rifare la demo."""
    strumento = FakeBackup(AVANZAMENTI)
    scenario, _ = _scena_restore(
        strumento, origine=_archivio_con(10), destinazione=_archivio_con(0)
    )

    esito = scenario.esegui()

    assert strumento.restore_chiesti == [(SORGENTE, "lab_restore")]
    assert esito.sorgente == SORGENTE
    assert esito.destinazione == "lab_restore"


def test_ogni_avanzamento_del_restore_arriva_a_schermo() -> None:
    scenario, sink = _scena_restore(
        FakeBackup(AVANZAMENTI),
        origine=_archivio_con(3),
        destinazione=_archivio_con(3),
    )

    esito = scenario.esegui()

    passati = [e.avanzamento for e in sink.eventi if isinstance(e, BackupProgressed)]
    assert passati == list(AVANZAMENTI)
    assert esito.avanzamenti == AVANZAMENTI


def test_i_due_conteggi_si_accostano_e_la_differenza_e_un_numero() -> None:
    """Il dump è a caldo, quindi i due conteggi **possono** non combaciare, e lo scenario
    non lo tratta come un errore.

    `mongodump --oplog` porta via anche l'oplog della finestra, ma
    `SubprocessBackup.restore` non lo riapplica: `--oplogReplay` è incompatibile con la
    rinomina di namespace che serve a restaurare su un database diverso. Ciò che manca è
    esattamente quello che è stato scritto **durante** il dump, e mostrarlo è metà della
    lezione dell'Atto III. Dichiararlo un fallimento sarebbe l'altra metà, sbagliata.
    """
    scenario, _ = _scena_restore(
        FakeBackup(AVANZAMENTI),
        origine=_archivio_con(10),
        destinazione=_archivio_con(7),
    )

    esito = scenario.esegui()

    assert esito.documenti_origine == 10
    assert esito.documenti_destinazione == 7
    assert esito.differenza == 3
    assert not esito.combaciano


def test_un_restore_che_ritrova_tutto_combacia() -> None:
    scenario, _ = _scena_restore(
        FakeBackup(AVANZAMENTI),
        origine=_archivio_con(10),
        destinazione=_archivio_con(10),
    )

    esito = scenario.esegui()

    assert esito.differenza == 0
    assert esito.combaciano


def test_anche_la_scena_del_restore_si_ferma_a_ogni_fase_con_step() -> None:
    fermate: list[str] = []
    attesa: Attesa = lambda evento: fermate.append(evento.fase)  # noqa: E731
    scenario, _ = _scena_restore(
        FakeBackup(AVANZAMENTI),
        origine=_archivio_con(1),
        destinazione=_archivio_con(1),
    )

    scenario.esegui(attesa=attesa)

    assert fermate == ["restore", "verifica"]


# --- Il Blocco 3: lo stesso carico due volte, e i chunk che non si muovono ---------------

INTERA = "carico-20260918-093000"
"""La collezione che nessuno ha distribuito: il nome porta l'istante, come da ADR-0088."""

SPARSA = "ordini"
"""La collezione del seed, distribuita su chiave hashed da `30-dati-demo.js`."""

MIRATO: Documento = {"_id": 4242}
SPARPAGLIATO: Documento = {"citta": "Ancona"}

SCRITTURE = 10
"""Un conteggio e non una durata, per la ragione scritta in `Copione`: le prove usano il
conteggio e per questo non si piantano quando la macchina è lenta."""


def _distribuzione(
    collezione: str,
    *coppie: tuple[str, int, int],
    distribuita: bool = True,
) -> Distribuzione:
    return Distribuzione(
        collezione=collezione,
        distribuita=distribuita,
        primario=coppie[0][0],
        conti=tuple(
            ContoShard(shard=shard, documenti=documenti, chunk=chunk)
            for shard, documenti, chunk in coppie
        ),
    )


A_RIPOSO = _distribuzione(SPARSA, ("shard1rs", 10_000, 2), ("shard2rs", 10_000, 2))

DOPO_IL_CARICO = _distribuzione(SPARSA, ("shard1rs", 10_008, 2), ("shard2rs", 10_002, 2))
"""Otto arrivi da una parte e due dall'altra: ottanta contro venti, sessanta punti di
sbilancio, e nessuna di queste cifre va ricalcolata a mente leggendo l'asserzione.

Notare quanto sono **piccoli** gli arrivi accanto ai ventimila che c'erano già: è
esattamente la ragione per cui lo sbilancio non si misura sui totali. Sui totali questi
stessi numeri darebbero zero punti, cioè «perfettamente bilanciato», mentre il carico è
finito per l'ottanta per cento da una parte sola."""

PARI = _distribuzione(SPARSA, ("shard1rs", 10_005, 2), ("shard2rs", 10_005, 2))
"""Cinque e cinque: l'equilibrio vero, che sui totali è indistinguibile dal precedente."""

TUTTA_SU_UNO = _distribuzione(
    INTERA, ("shard1rs", SCRITTURE, 0), distribuita=False
)


def _scena_sharding(
    *,
    distribuzioni: dict[str, list[Distribuzione]] | None = None,
    piani: Sequence[tuple[str, Sequence[str]]] = (
        ("SINGLE_SHARD", ("shard1rs",)),
        ("SHARD_MERGE", ("shard1rs", "shard2rs")),
    ),
    copione: CopioneSharding | None = None,
) -> tuple[ScenarioSharding, FakeInspector, FakePlanner, RecordingSink]:
    """La scena con i doppi al loro posto: due archivi, un ispettore, un pianificatore."""
    sink = RecordingSink()
    orologio = OrologioCheScorre(ISTANTE, passo_s=0.001)
    ispettore = FakeInspector(
        [_topologia(UNO)],
        distribuzioni=distribuzioni
        if distribuzioni is not None
        else {SPARSA: [A_RIPOSO, DOPO_IL_CARICO], INTERA: [TUTTA_SU_UNO]},
    )
    pianificatore = FakePlanner(piani)
    scenario = ScenarioSharding(
        ispettore,
        pianificatore,
        WorkloadRunner(InMemoryStore(), orologio, sink),
        WorkloadRunner(InMemoryStore(), orologio, sink),
        orologio,
        sink,
        copione=copione
        if copione is not None
        else CopioneSharding(
            intera=INTERA,
            sparsa=SPARSA,
            mirato=MIRATO,
            sparpagliato=SPARPAGLIATO,
            scritture=SCRITTURE,
        ),
    )
    return scenario, ispettore, pianificatore, sink


def test_la_scena_dello_sharding_ha_cinque_fasi_nell_ordine() -> None:
    """Riposo, i due carichi, i piani, il bilancio.

    La prima fase sembra non servire a niente, come la fase «carico» del failover, e per
    la stessa ragione non lo è: senza la fotografia di prima, quella di dopo è un elenco
    di numeri di cui nessuno sa dire se siano cambiati.
    """
    scenario, _, _, sink = _scena_sharding()

    esito = scenario.esegui()

    assert esito.fasi == (
        "riposo",
        "non-distribuita",
        "distribuita",
        "piani",
        "bilancio",
    )
    annunci = [evento for evento in sink.eventi if isinstance(evento, FaseIniziata)]
    assert [evento.fase for evento in annunci] == list(esito.fasi)


def test_lo_stesso_carico_gira_due_volte_e_l_esito_dice_che_e_lo_stesso() -> None:
    """La decisione del PO, messa alla prova: due corse, e il confronto vale solo se sono
    identiche.

    Nessuno scarto fra le due, a differenza delle fasi del failover e del backup: lì le
    fasi si susseguono nella **stessa** collezione e gli indici si sovrapporrebbero, qui le
    collezioni sono due e ripartire da zero è ciò che rende le due corse letteralmente lo
    stesso carico.
    """
    scenario, _, _, _ = _scena_sharding()

    esito = scenario.esegui()

    assert esito.carico_intera.scritture == SCRITTURE
    assert esito.carico_sparsa.scritture == SCRITTURE
    assert esito.confrontabile


def test_due_corse_di_lunghezza_diversa_non_si_accostano_e_l_esito_lo_dice() -> None:
    """Un archivio che rifiuta metà delle scritture rende il confronto una bugia.

    Non solleva e non nasconde: l'esito porta un booleano, e chi disegna la schermata
    decide che cosa scriverci accanto. Accostare due colonne senza dire che vengono da due
    carichi diversi sarebbe il modo più elegante di mentire in sala.
    """
    esito = _esito_sharding(scritte_intera=5, scritte_sparsa=3)

    assert not esito.confrontabile


def test_la_collezione_non_distribuita_finisce_tutta_su_un_solo_shard() -> None:
    """La prima metà della scena, ed è la domanda che il pubblico fa sempre.

    «L'ho acceso, perché non distribuisce?» — perché nessuno ha eseguito
    `shardCollection`. La quota dello shard primario è cento, e non è un difetto.
    """
    scenario, _, _, _ = _scena_sharding()

    esito = scenario.esegui()

    assert not esito.intera.distribuita
    assert esito.intera.in_un_cluster, "il cluster c'è: è la metà che ADR-0104 ha aggiunto"
    assert esito.intera.quota("shard1rs") == 100.0


def test_lo_sbilancio_e_la_distanza_fra_lo_shard_piu_pieno_e_il_piu_vuoto() -> None:
    """Un numero solo, perché in sala due colonne di conteggi non si confrontano a mente.

    Punti percentuali e non un rapporto: «venti punti di distanza» si capisce senza
    spiegazioni, «uno virgola cinque» chiede di sapere che cosa sta sopra e che cosa sotto.
    """
    scenario, _, _, _ = _scena_sharding()

    esito = scenario.esegui()

    assert esito.sbilancio == 60.0
    assert _esito_sharding(dopo=PARI).sbilancio == 0.0


def test_gli_arrivi_dicono_dove_e_finito_il_carico_e_non_dove_stava_il_seed() -> None:
    """Il numero che rende le due colonne confrontabili, e che per poco non c'era.

    La colonna «non sharded» mostra duemila documenti su uno shard: sono **tutti** quelli
    scritti, perché quella collezione è nata con il carico. La colonna «sharded» mostra i
    totali di `lab.ordini`, che contengono i ventimila del seed: accostare duemila a
    ventiduemila non confronta niente. Gli arrivi sono la differenza fra la fotografia di
    dopo e quella di prima, cioè l'unica parte comparabile.
    """
    scenario, _, _, _ = _scena_sharding()

    esito = scenario.esegui()

    assert esito.arrivi == (("shard1rs", 8), ("shard2rs", 2))
    assert sum(quanti for _, quanti in esito.arrivi) == SCRITTURE


def test_senza_arrivi_lo_sbilancio_e_ignoto_e_non_un_equilibrio_perfetto() -> None:
    """Zero documenti arrivati non è «distribuiti alla perfezione»: è niente da misurare.

    Il caso non è teorico — è ciò che si vede se il carico fallisce del tutto — ed è
    precisamente quello in cui uno zero stampato mentirebbe con la faccia del successo.
    """
    assert _esito_sharding(dopo=A_RIPOSO).sbilancio is None


def test_su_una_collezione_non_distribuita_lo_sbilancio_e_ignoto_e_non_cento() -> None:
    """Zero shard e uno shard solo non hanno uno sbilancio: non c'è una seconda colonna.

    `None` e non `100.0`: cento direbbe «massimamente sbilanciata», che è una descrizione
    di una distribuzione che non esiste. È la stessa regola dei doppi applicata alle
    statistiche — un numero inventato è peggio di un dato che manca.
    """
    assert _esito_sharding(dopo=TUTTA_SU_UNO).sbilancio is None


def test_la_collezione_distribuita_si_guarda_due_volte_prima_e_dopo() -> None:
    scenario, ispettore, _, _ = _scena_sharding()

    esito = scenario.esegui()

    assert ispettore.distribuzioni_chieste == [SPARSA, INTERA, SPARSA]
    assert esito.prima.documenti == 20_000
    assert esito.dopo.documenti == 20_010


def test_i_chunk_che_non_si_sono_mossi_si_contano_invece_di_tacere() -> None:
    """Il Passo 1 del Task 15, e la risposta misurata è zero.

    Il balancer del 7.0 in questo laboratorio non migra mai — 1153 giri e nessuna migrazione
    ([M-049](../../docs/Sources.md#m-049), ADR-0069) — e con una chiave hashed i
    chunk sono già distribuiti prima che arrivi la prima scrittura. Uno zero **mostrato** è
    la lezione della scena; uno zero taciuto sembrerebbe una funzione che non c'è.
    """
    scenario, _, _, _ = _scena_sharding()

    esito = scenario.esegui()

    assert esito.chunk_in_piu == 0


def test_senza_una_delle_due_fotografie_distribuite_i_chunk_in_piu_sono_ignoti() -> None:
    assert _esito_sharding(dopo=TUTTA_SU_UNO).chunk_in_piu is None


def test_i_due_piani_arrivano_dal_pianificatore_nell_ordine_del_copione() -> None:
    """Mirata prima, scatter-gather dopo — e il contrasto è tutto il Passo 3.

    L'ordine non è estetico: la scena mostra prima che si **può** interrogare un solo
    shard, poi che cosa costa non poterlo fare. Invertito, la seconda schermata sembra un
    miglioramento invece di un prezzo.
    """
    scenario, _, pianificatore, _ = _scena_sharding()

    esito = scenario.esegui()

    assert pianificatore.chiesti == [MIRATO, SPARPAGLIATO]
    assert esito.mirata.stadio == "SINGLE_SHARD"
    assert esito.mirata.mirata
    assert esito.sparpagliata.stadio == "SHARD_MERGE"
    assert not esito.sparpagliata.mirata


def test_col_passo_la_pausa_arriva_prima_di_ogni_fase() -> None:
    """`--step`, la stessa funzione delle altre due scene e la stessa prova."""
    scenario, _, _, _ = _scena_sharding()
    viste: list[str] = []
    attesa: Attesa = lambda fase: viste.append(fase.fase)  # noqa: E731

    esito = scenario.esegui(attesa=attesa)

    assert viste == list(esito.fasi)


def _esito_sharding(
    *,
    dopo: Distribuzione = DOPO_IL_CARICO,
    scritte_intera: int = SCRITTURE,
    scritte_sparsa: int = SCRITTURE,
) -> EsitoSharding:
    """Un esito montato a mano, per le proprietà che non hanno bisogno di una corsa."""
    return EsitoSharding(
        fasi=("riposo", "non-distribuita", "distribuita", "piani", "bilancio"),
        intera=TUTTA_SU_UNO,
        prima=A_RIPOSO,
        dopo=dopo,
        carico_intera=_riepilogo(scritte_intera),
        carico_sparsa=_riepilogo(scritte_sparsa),
        mirata=Piano(filtro=MIRATO, stadio="SINGLE_SHARD", shard=("shard1rs",)),
        sparpagliata=Piano(
            filtro=SPARPAGLIATO, stadio="SHARD_MERGE", shard=("shard1rs", "shard2rs")
        ),
    )
