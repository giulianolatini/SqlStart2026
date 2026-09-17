"""L'orologio vero, cioè l'implementazione di `Clock` che il §6.2 chiama `SystemClock`.

Fino al Task 10 l'orologio esisteva solo come porta e come doppio: `FakeClock` nelle
prove, e in produzione nessuno. Questo modulo chiude quella riga aperta, e nel farlo
scopre che l'implementazione ovvia — `datetime.now()` e `time.sleep()` — è sbagliata per
questa applicazione.

## Perché non `datetime.now()` a ogni chiamata

La porta `Clock` è usata in due modi che sembrano uno solo. Serve a **datare** un evento
(`WriteSucceeded.istante`, che finisce nella cronaca al millesimo) e serve a **misurare**
una durata: `WorkloadRunner._scrivi` sottrae due `now()` e chiama il risultato latenza,
`TopologyWatcher` sottrae due `now()` e decide se i trenta secondi di pazienza sono
finiti. Le due letture di un `datetime` sono la stessa chiamata; le due proprietà che
richiedono, no.

`datetime.now()` legge l'orologio da parete. Su questo interprete
`time.get_clock_info("time")` lo dichiara `implementation='clock_gettime(CLOCK_REALTIME)',
monotonic=False, adjustable=True` ([M-030](../../../docs/Sources.md#m-030)):
*aggiustabile* vuol dire che è previsto che salti, all'indietro compreso, quando NTP
corregge una deriva o quando la macchina si risveglia. `time.monotonic()`, sulla stessa
macchina, è `mach_absolute_time()` con `monotonic=True, adjustable=False`.

Un salto all'indietro durante una demo di failover non produce un errore: produce una
latenza negativa che entra nei percentili e una pazienza che non scade. Nessuno dei due
punti controlla il segno, e non devono — è l'orologio che deve essere un orologio.

## La scelta: un'ancora e un contatore

`SystemClock` legge il muro **una volta sola**, alla costruzione, e da lì in poi somma a
quell'ancora il tempo trascorso secondo il contatore monotono. Gli istanti che restituisce
sono ore vere — si leggono accanto all'orologio della sala — e le loro differenze sono
durate vere, perché vengono tutte dallo stesso contatore che non torna indietro.

Il prezzo è una deriva: dopo un'ora di processo l'istante riportato differisce dal muro
di quanto i due orologi divergono fra loro, che su un portatile è dell'ordine dei
millisecondi, e non viene mai ricorretto. Per una scena che dura minuti è invisibile; per
un demone che gira per giorni sarebbe la scelta sbagliata, e questo non è un demone.

La riserva vera è un'altra ed è dichiarata: se la macchina viene **sospesa** a metà scena,
il contatore monotono di macOS (`mach_absolute_time`) non conta il tempo di sospensione, e
al risveglio la cronaca risulterebbe indietro rispetto al muro di quanto è durato il
sonno. Non è stato misurato, e non lo si difende: chi presenta non chiude il coperchio.

## L'ora locale, e non UTC

`presentation/righe.py` stampa `%H:%M:%S.mmm` **senza convertire il fuso**, perché una
cronaca che dura minuti non ha spazio per una data né per un nome di zona. Se `now()`
restituisse UTC, la schermata proiettata a Ancona mostrerebbe un'ora di due diversa da
quella dell'orologio in fondo alla sala — e in una scena in cui i tempi sono il contenuto,
la prima domanda del pubblico sarebbe su quella differenza. `datetime.now().astimezone()`
dà un istante consapevole del fuso, nel fuso di chi presenta.
"""

from datetime import datetime, timedelta
import time
from typing import Callable, Final

__all__ = ["SystemClock", "muro_locale"]

UN_SECONDO: Final = timedelta(seconds=1)


def muro_locale() -> datetime:
    """L'ora del sistema, consapevole del fuso locale.

    `datetime.now()` da solo restituisce un istante **ingenuo**, e `datetime.now(UTC)` uno
    consapevole ma nel fuso sbagliato per una schermata. `astimezone()` senza argomenti
    attacca all'istante il fuso configurato sulla macchina, che è quello della sala.
    """
    return datetime.now().astimezone()


class SystemClock:
    """`Clock` vero: ancorato al muro alla costruzione, avanzato dal contatore monotono.

    I due parametri esistono per le prove e non per la produzione, ed è deliberato che si
    chiamino come le due cose che sostituiscono: senza un modo di far saltare il muro, la
    riga che rende questa classe diversa da `datetime.now` resterebbe senza guardia — che
    è precisamente l'errore che il Task 10 ha pagato due volte.
    """

    __slots__ = ("_ancora", "_monotono", "_zero")

    def __init__(
        self,
        *,
        muro: Callable[[], datetime] = muro_locale,
        monotono: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ancora = muro()
        self._monotono = monotono
        self._zero = monotono()

    def now(self) -> datetime:
        return self._ancora + (self._monotono() - self._zero) * UN_SECONDO

    def sleep(self, secondi: float) -> None:
        """Aspetta, e rifiuta un'attesa negativa dicendo quale.

        `time.sleep(-1)` solleva già `ValueError`, ma con un messaggio che parla del tipo
        e non del numero. Qui il numero arriva sempre da un calcolo — `attesa_ms / 1000`
        di una politica di tentativi — e il valore sbagliato è l'unica informazione utile.
        """
        if secondi < 0:
            raise ValueError(f"non si aspetta un tempo negativo: {secondi}")
        time.sleep(secondi)
