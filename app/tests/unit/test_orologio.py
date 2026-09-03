"""L'orologio di sistema: consapevole del fuso, e che non torna indietro.

`SystemClock` è due righe di codice e tre decisioni, e le decisioni sono la ragione per
cui questo file esiste. La porta `Clock` è usata in due modi diversi che sembrano uno
solo: per **datare** un evento e per **misurare** una durata. `WorkloadRunner._scrivi`
sottrae due `now()` e chiama il risultato latenza; `TopologyWatcher` sottrae due `now()`
e decide se la pazienza è finita. Un orologio che salta all'indietro produce una latenza
negativa che entra in un percentile e una pazienza che non scade mai — in silenzio,
perché nessuno dei due controlla il segno.
"""

from datetime import UTC, datetime, timedelta
import time

from mongolab.domain.porte import Clock
from mongolab.infrastructure.orologio import SystemClock


class MuroCheSalta:
    """Un orologio da parete che torna indietro di un'ora alla seconda lettura.

    È il salto che fa un NTP quando corregge una deriva grossa, o un portatile che si
    risveglia. Non è ipotetico: `time.get_clock_info("time")` su questo interprete
    dichiara `adjustable=True`, cioè che è previsto che accada.
    """

    def __init__(self, inizio: datetime) -> None:
        self._inizio = inizio
        self.letture = 0

    def __call__(self) -> datetime:
        self.letture += 1
        return self._inizio - timedelta(hours=1) * (self.letture - 1)


class MonotonoFinto:
    """Un contatore monotono che avanza di dieci millisecondi a ogni lettura."""

    def __init__(self) -> None:
        self.secondi = 0.0

    def __call__(self) -> float:
        adesso = self.secondi
        self.secondi += 0.010
        return adesso


def test_soddisfa_la_porta_orologio() -> None:
    assert isinstance(SystemClock(), Clock)


def test_now_ha_il_fuso_orario() -> None:
    # Un istante ingenuo è ambiguo appena esce dal processo, e questi istanti finiscono
    # in una registrazione che qualcuno leggerà a giorni di distanza.
    adesso = SystemClock().now()
    assert adesso.tzinfo is not None
    assert adesso.utcoffset() is not None


def test_now_e_l_ora_locale_e_non_utc() -> None:
    # La cronaca stampa `%H:%M:%S` senza convertire il fuso: in UTC la schermata
    # proiettata mostrerebbe un'ora diversa da quella dell'orologio in sala.
    atteso = datetime.now().astimezone().utcoffset()
    assert SystemClock().now().utcoffset() == atteso


def test_now_e_ancorato_al_muro_al_momento_della_costruzione() -> None:
    prima = datetime.now(UTC)
    orologio = SystemClock()
    dopo = datetime.now(UTC)
    # Ancorato, non slegato: l'istante restituito è un'ora vera, non un tempo dall'avvio.
    assert prima <= orologio.now() <= dopo + timedelta(seconds=1)


def test_now_avanza_del_tempo_monotono_non_di_quello_del_muro() -> None:
    monotono = MonotonoFinto()
    orologio = SystemClock(muro=MuroCheSalta(datetime(2026, 9, 18, 10, 0, tzinfo=UTC)), monotono=monotono)
    primo = orologio.now()
    secondo = orologio.now()
    assert secondo - primo == timedelta(milliseconds=10)


def test_now_non_torna_indietro_quando_il_muro_torna_indietro() -> None:
    # È la prova che giustifica la classe. Un orologio che leggesse il muro a ogni
    # chiamata restituirebbe qui un istante di un'ora **prima** del precedente, e la
    # differenza fra i due — che questa applicazione chiama «latenza» — sarebbe
    # -3 600 000 ms, un numero che finisce dentro un p95 senza che nessuno se ne accorga.
    muro = MuroCheSalta(datetime(2026, 9, 18, 10, 0, tzinfo=UTC))
    orologio = SystemClock(muro=muro, monotono=MonotonoFinto())
    istanti = [orologio.now() for _ in range(5)]
    assert istanti == sorted(istanti)
    assert all(dopo > prima for prima, dopo in zip(istanti, istanti[1:]))
    # Il muro è stato letto una volta sola: all'ancoraggio.
    assert muro.letture == 1


def test_sleep_aspetta_davvero() -> None:
    orologio = SystemClock()
    prima = time.monotonic()
    orologio.sleep(0.005)
    assert time.monotonic() - prima >= 0.005


def test_sleep_rifiuta_un_attesa_negativa() -> None:
    # `time.sleep` di un valore negativo solleva `ValueError` per conto suo, ma con un
    # messaggio che non dice chi l'ha chiesto. Qui la richiesta arriva sempre da un
    # calcolo — `attesa_ms / 1000` di una politica di tentativi — e il numero sbagliato
    # è più utile del tipo sbagliato.
    try:
        SystemClock().sleep(-1.0)
    except ValueError as errore:
        assert "-1.0" in str(errore)
    else:  # pragma: no cover - il ramo esiste per fallire se l'eccezione non arriva
        raise AssertionError("un'attesa negativa deve essere rifiutata")
