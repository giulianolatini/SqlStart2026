"""Il generatore di carico: le scritture, i tentativi, le latenze.

Queste prove sono state scritte **prima** di `mongolab.application.workload`, e la loro
prima esecuzione è stata un `ModuleNotFoundError`. È la disciplina del piano, e qui ha un
effetto concreto: la firma di `WorkloadRunner` è stata decisa dalle asserzioni — cioè da
ciò che serve leggere dopo una corsa — invece che dall'implementazione che le doveva
soddisfare.

Tutto gira contro i doppi: nessuna prova di questo file sa che esiste MongoDB, e
l'intera suite dura centesimi di secondo. Il tempo lo decide `FakeClock`, quindi anche le
attese del backoff — decine di millisecondi che diventerebbero secondi sotto carico —
sono asserzioni su una lista, non pause vere.

**Che cosa non si asserisce, e apposta.** Con più scrittori l'ordine fra worker diversi
non è garantito da niente: pretenderlo qui produrrebbe una prova che passa quasi sempre,
cioè il tipo peggiore. Si asserisce invece ciò che il §6.3 promette davvero — che nessun
evento si perda, e che a toccare il sink sia **un solo thread**.
"""

from datetime import UTC, datetime
import threading

import pytest

from mongolab.application.workload import (
    Genera,
    Latenze,
    PoliticaTentativi,
    Riepilogo,
    WorkloadRunner,
    percentile,
    riassumi,
)
from mongolab.domain.eventi import (
    LatencySampled,
    RetryAttempted,
    WriteFailed,
    WriteSucceeded,
)
from mongolab.domain.modelli import Documento
from mongolab.domain.porte import Clock, DocumentStore, EventSink

from tests.aiutanti import specie
from tests.doppi import (
    ArchivioCheRompe,
    ArchivioLento,
    FakeClock,
    InMemoryStore,
    RecordingSink,
    ScritturaRifiutata,
)

ISTANTE = datetime(2026, 9, 18, 9, 30, 0, tzinfo=UTC)


# --- Le scritture che riescono --------------------------------------------------------


def test_n_scritture_producono_n_successi_e_altrettante_latenze() -> None:
    archivio = InMemoryStore()
    sink = RecordingSink()
    corridore = WorkloadRunner(archivio, FakeClock(ISTANTE), sink)

    corridore.esegui(scritture=5)

    assert len(specie(sink.eventi, WriteSucceeded)) == 5
    assert len(specie(sink.eventi, LatencySampled)) == 5
    assert archivio.count({}) == 5


def test_i_documenti_finiscono_davvero_nell_archivio() -> None:
    archivio = InMemoryStore()
    corridore = WorkloadRunner(archivio, FakeClock(ISTANTE), RecordingSink())

    riepilogo = corridore.esegui(scritture=2, per_scrittura=3)

    assert archivio.count({}) == 6
    assert riepilogo.documenti_confermati == 6


def test_ogni_evento_di_successo_dice_quanti_documenti_ha_confermato() -> None:
    sink = RecordingSink()
    corridore = WorkloadRunner(InMemoryStore(), FakeClock(ISTANTE), sink)

    corridore.esegui(scritture=2, per_scrittura=3)

    assert [evento.documenti for evento in specie(sink.eventi, WriteSucceeded)] == [3, 3]


def test_i_documenti_generati_sono_distinti() -> None:
    archivio = InMemoryStore()
    corridore = WorkloadRunner(archivio, FakeClock(ISTANTE), RecordingSink())

    corridore.esegui(scritture=4)

    indici = {documento["indice"] for documento in archivio.find_page({}, quanti=100)}
    assert indici == {0, 1, 2, 3}


def test_il_generatore_dei_documenti_si_puo_sostituire() -> None:
    archivio = InMemoryStore()
    corridore = WorkloadRunner(archivio, FakeClock(ISTANTE), RecordingSink())

    def carico(indice: int) -> Documento:
        return {"indice": indice, "riempimento": "x" * 16}

    corridore.esegui(scritture=2, genera=carico)

    assert archivio.count({"riempimento": "x" * 16}) == 2


# --- La latenza, misurata sull'orologio -----------------------------------------------


def test_la_latenza_e_il_tempo_passato_sull_orologio() -> None:
    orologio = FakeClock(ISTANTE)
    archivio = ArchivioLento(InMemoryStore(), orologio, costo_ms=12.0)
    sink = RecordingSink()

    WorkloadRunner(archivio, orologio, sink).esegui(scritture=2)

    successi = specie(sink.eventi, WriteSucceeded)
    campioni = specie(sink.eventi, LatencySampled)
    assert [evento.durata_ms for evento in successi] == [12.0, 12.0]
    assert [evento.durata_ms for evento in campioni] == [12.0, 12.0]


def test_il_campione_di_latenza_nomina_l_operazione() -> None:
    sink = RecordingSink()
    WorkloadRunner(InMemoryStore(), FakeClock(ISTANTE), sink).esegui(scritture=1)

    (campione,) = specie(sink.eventi, LatencySampled)
    assert campione.operazione == "insert_many"


def test_gli_eventi_portano_l_istante_dell_orologio() -> None:
    orologio = FakeClock(ISTANTE)
    sink = RecordingSink()

    WorkloadRunner(InMemoryStore(), orologio, sink).esegui(scritture=1)

    assert {evento.istante for evento in sink.eventi} == {ISTANTE}


# --- I fallimenti e i tentativi -------------------------------------------------------


def test_uno_store_che_solleva_produce_un_fallimento_seguito_da_un_tentativo() -> None:
    archivio = ArchivioCheRompe(InMemoryStore(), guasti=1)
    sink = RecordingSink()

    WorkloadRunner(archivio, FakeClock(ISTANTE), sink).esegui(scritture=1)

    assert [type(evento) for evento in sink.eventi] == [
        WriteFailed,
        RetryAttempted,
        WriteSucceeded,
        LatencySampled,
    ]


def test_il_fallimento_nomina_il_tipo_di_errore_e_il_motivo() -> None:
    archivio = ArchivioCheRompe(InMemoryStore(), guasti=1, motivo="niente primario")
    sink = RecordingSink()

    WorkloadRunner(archivio, FakeClock(ISTANTE), sink).esegui(scritture=1, per_scrittura=4)

    (fallimento,) = specie(sink.eventi, WriteFailed)
    assert fallimento.tipo_errore == ScritturaRifiutata.__name__
    assert fallimento.motivo == "niente primario"
    assert fallimento.documenti == 4


def test_la_politica_smette_dopo_i_tentativi_previsti_e_non_prima() -> None:
    archivio = ArchivioCheRompe(InMemoryStore())
    sink = RecordingSink()
    politica = PoliticaTentativi(tentativi_massimi=3)

    riepilogo = WorkloadRunner(
        archivio, FakeClock(ISTANTE), sink, politica=politica
    ).esegui(scritture=1)

    assert len(specie(sink.eventi, WriteFailed)) == 3
    assert len(specie(sink.eventi, RetryAttempted)) == 2
    assert riepilogo.fallite == 1
    assert riepilogo.riuscite == 0


def test_l_ultimo_evento_di_una_resa_e_il_fallimento_non_il_tentativo() -> None:
    archivio = ArchivioCheRompe(InMemoryStore())
    sink = RecordingSink()

    WorkloadRunner(archivio, FakeClock(ISTANTE), sink).esegui(scritture=1)

    assert isinstance(sink.eventi[-1], WriteFailed)


def test_l_attesa_raddoppia_a_ogni_tentativo() -> None:
    orologio = FakeClock(ISTANTE)
    sink = RecordingSink()
    politica = PoliticaTentativi(
        tentativi_massimi=4, attesa_iniziale_ms=50.0, fattore=2.0
    )

    WorkloadRunner(
        ArchivioCheRompe(InMemoryStore()), orologio, sink, politica=politica
    ).esegui(scritture=1)

    tentativi = specie(sink.eventi, RetryAttempted)
    assert [evento.attesa_ms for evento in tentativi] == [50.0, 100.0, 200.0]
    assert orologio.attese == [0.05, 0.1, 0.2]


def test_l_attesa_non_supera_il_tetto() -> None:
    orologio = FakeClock(ISTANTE)
    politica = PoliticaTentativi(
        tentativi_massimi=4, attesa_iniziale_ms=50.0, fattore=10.0, attesa_massima_ms=120.0
    )
    sink = RecordingSink()

    WorkloadRunner(
        ArchivioCheRompe(InMemoryStore()), orologio, sink, politica=politica
    ).esegui(scritture=1)

    tentativi = specie(sink.eventi, RetryAttempted)
    assert [evento.attesa_ms for evento in tentativi] == [50.0, 120.0, 120.0]


def test_il_tentativo_e_numerato_come_la_prova_che_sta_per_fare() -> None:
    sink = RecordingSink()

    WorkloadRunner(
        ArchivioCheRompe(InMemoryStore()), FakeClock(ISTANTE), sink
    ).esegui(scritture=1)

    assert [evento.tentativo for evento in specie(sink.eventi, RetryAttempted)] == [2, 3]


def test_l_attesa_del_primo_tentativo_non_esiste() -> None:
    """La guardia c'è perché un `attesa_ms(1)` sarebbe una domanda malposta.

    Questa prova è nata da una rottura deliberata: tolta la guardia, la suite restava
    verde: nessuno chiedeva mai l'attesa del primo tentativo, e una guardia che nessuna
    prova può veder scattare è indistinguibile da un commento (nota di metodo 144).
    """
    with pytest.raises(ValueError, match="il primo tentativo non attende"):
        PoliticaTentativi().attesa_ms(1)


def test_una_scrittura_che_riesce_al_primo_colpo_non_chiede_attese() -> None:
    orologio = FakeClock(ISTANTE)
    sink = RecordingSink()

    WorkloadRunner(InMemoryStore(), orologio, sink).esegui(scritture=3)

    assert orologio.attese == []
    assert specie(sink.eventi, RetryAttempted) == []


def test_una_scrittura_fallita_non_entra_nel_campione_delle_latenze() -> None:
    sink = RecordingSink()

    riepilogo = WorkloadRunner(
        ArchivioCheRompe(InMemoryStore()), FakeClock(ISTANTE), sink
    ).esegui(scritture=1)

    assert specie(sink.eventi, LatencySampled) == []
    assert riepilogo.latenze is None


def test_il_riepilogo_conta_le_scritture_i_successi_e_i_tentativi() -> None:
    archivio = ArchivioCheRompe(InMemoryStore(), guasti=2)

    riepilogo = WorkloadRunner(archivio, FakeClock(ISTANTE), RecordingSink()).esegui(
        scritture=3
    )

    assert riepilogo.scritture == 3
    assert riepilogo.riuscite == 3
    assert riepilogo.fallite == 0
    assert riepilogo.ritentate == 2


def test_un_errore_del_generatore_non_viene_inghiottito() -> None:
    def genera_male(indice: int) -> Documento:
        raise ValueError("il generatore è rotto")

    corridore = WorkloadRunner(InMemoryStore(), FakeClock(ISTANTE), RecordingSink())

    with pytest.raises(ValueError, match="il generatore è rotto"):
        corridore.esegui(scritture=2, genera=genera_male)


# --- I percentili, calcolati a mano ---------------------------------------------------


def test_il_percentile_e_sempre_un_valore_osservato() -> None:
    campione = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

    assert percentile(campione, 0.5) == 5.0
    assert percentile(campione, 0.9) == 9.0
    assert percentile(campione, 0.95) == 10.0
    assert percentile(campione, 1.0) == 10.0


def test_il_percentile_non_interpola_fra_due_valori() -> None:
    assert percentile([10.0, 20.0], 0.5) == 10.0


def test_l_ordine_del_campione_non_conta() -> None:
    assert percentile([9.0, 1.0, 5.0], 0.5) == 5.0


def test_la_mediana_non_e_la_media() -> None:
    campione = [1.0] * 9 + [100.0]

    assert riassumi(campione).mediana_ms == 1.0
    assert sum(campione) / len(campione) == 10.9


def test_il_percentile_alto_vede_l_estremo_che_la_media_nasconde() -> None:
    campione = [1.0] * 9 + [100.0]

    assert riassumi(campione).p95_ms == 100.0


def test_il_percentile_di_un_campione_vuoto_non_e_zero() -> None:
    with pytest.raises(ValueError, match="campione vuoto"):
        percentile([], 0.5)


def test_il_percentile_vuole_un_quantile_fra_zero_e_uno() -> None:
    with pytest.raises(ValueError, match="quantile"):
        percentile([1.0], 1.5)


def test_riassumi_su_un_campione_noto() -> None:
    campione = [4.0, 1.0, 3.0, 2.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

    latenze = riassumi(campione)

    assert latenze == Latenze(
        campioni=10,
        minimo_ms=1.0,
        mediana_ms=5.0,
        p95_ms=10.0,
        p99_ms=10.0,
        massimo_ms=10.0,
    )


def test_riassumi_su_un_campione_solo() -> None:
    latenze = riassumi([7.0])

    assert latenze == Latenze(
        campioni=1,
        minimo_ms=7.0,
        mediana_ms=7.0,
        p95_ms=7.0,
        p99_ms=7.0,
        massimo_ms=7.0,
    )


def test_il_riepilogo_riassume_le_latenze_misurate() -> None:
    orologio = FakeClock(ISTANTE)
    archivio = ArchivioLento(InMemoryStore(), orologio, costo_ms=3.0)

    riepilogo = WorkloadRunner(archivio, orologio, RecordingSink()).esegui(scritture=4)

    assert riepilogo.latenze == Latenze(
        campioni=4,
        minimo_ms=3.0,
        mediana_ms=3.0,
        p95_ms=3.0,
        p99_ms=3.0,
        massimo_ms=3.0,
    )


# --- La concorrenza -------------------------------------------------------------------


def test_con_piu_scrittori_nessun_evento_si_perde() -> None:
    archivio = InMemoryStore()
    sink = RecordingSink()

    riepilogo = WorkloadRunner(
        archivio, FakeClock(ISTANTE), sink, scrittori=4
    ).esegui(scritture=40)

    assert len(specie(sink.eventi, WriteSucceeded)) == 40
    assert len(specie(sink.eventi, LatencySampled)) == 40
    assert riepilogo.riuscite == 40
    assert archivio.count({}) == 40


def test_con_piu_scrittori_il_lavoro_non_si_duplica() -> None:
    archivio = InMemoryStore()

    WorkloadRunner(archivio, FakeClock(ISTANTE), RecordingSink(), scrittori=4).esegui(
        scritture=40
    )

    indici = {documento["indice"] for documento in archivio.find_page({}, quanti=100)}
    assert indici == set(range(40))


def test_le_scritture_si_ripartiscono_anche_quando_non_sono_divisibili() -> None:
    archivio = InMemoryStore()

    WorkloadRunner(archivio, FakeClock(ISTANTE), RecordingSink(), scrittori=3).esegui(
        scritture=7
    )

    assert archivio.count({}) == 7


def test_solo_il_thread_chiamante_tocca_il_sink() -> None:
    sink = RecordingSink()

    WorkloadRunner(InMemoryStore(), FakeClock(ISTANTE), sink, scrittori=4).esegui(
        scritture=40
    )

    assert sink.chiamanti == {threading.get_ident()}


def test_piu_scrittori_del_lavoro_non_producono_scritture_in_piu() -> None:
    archivio = InMemoryStore()
    sink = RecordingSink()

    WorkloadRunner(archivio, FakeClock(ISTANTE), sink, scrittori=8).esegui(scritture=3)

    assert archivio.count({}) == 3
    assert len(specie(sink.eventi, WriteSucceeded)) == 3


# --- Le porte ------------------------------------------------------------------------


def test_il_generatore_di_carico_parla_solo_attraverso_le_porte() -> None:
    """Le annotazioni sono la prova: è `mypy --strict` a eseguirla davvero.

    A runtime questa prova verifica poco — che una corsa minima non sollevi. Il suo
    valore sta nelle tre righe annotate: se `WorkloadRunner` chiedesse un giorno qualcosa
    che le porte non promettono, `make app-check` fallirebbe qui.
    """
    archivio: DocumentStore = InMemoryStore()
    orologio: Clock = FakeClock(ISTANTE)
    sink: EventSink = RecordingSink()

    riepilogo: Riepilogo = WorkloadRunner(archivio, orologio, sink).esegui(scritture=1)

    assert riepilogo.riuscite == 1


def test_il_generatore_e_una_funzione_dall_indice_al_documento() -> None:
    def carico(indice: int) -> Documento:
        return {"indice": indice}

    genera: Genera = carico
    archivio = InMemoryStore()

    WorkloadRunner(archivio, FakeClock(ISTANTE), RecordingSink()).esegui(
        scritture=1, genera=genera
    )

    assert archivio.count({"indice": 0}) == 1
