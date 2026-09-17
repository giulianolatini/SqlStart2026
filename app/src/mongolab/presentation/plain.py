"""La resa di testo: una riga per evento, e il buffer svuotato ogni volta.

È il sink delle registrazioni asciinema e di chi reindirizza su file. Non tiene stato,
non ricorda niente, non taglia la cronaca: quello che passa, scrive.

**Il `flush` non è prudenza, è il contenuto.** Python bufferizza a blocchi quando la
destinazione non è un terminale — cioè in `--sink plain > file` e in ogni pipe. Senza
svuotare, la cronaca di un failover comparirebbe tutta insieme a failover concluso: non
si perderebbe un byte, si perderebbero i **tempi**, che in queste scene sono la cosa che
si sta mostrando.
"""

from typing import TextIO

from mongolab.domain.eventi import Evento
from mongolab.presentation.righe import COLONNE_SALA, riga

__all__ = ["PlainSink"]


class PlainSink:
    """Un `EventSink` che scrive una riga di testo per evento.

    `larghezza=None` scrive il messaggio intero, ed è ciò che serve a chi analizzerà il
    file dopo. Il valore predefinito è la larghezza di sala, perché la registrazione di
    riserva deve mostrare **quello che il pubblico avrebbe visto**: una registrazione più
    informativa dello schermo dal vivo racconterebbe un'altra scena.

    Scrive senza mettersi in coda, e quindi fa I/O nel thread di chi chiama. Va bene
    perché nessun ascoltatore di pymongo chiama direttamente un sink — i produttori
    depositano in una coda e il consumatore chiama `emit` dal proprio thread
    ([ADR-0019](../../../../docs/Decision.md#adr-0019)) — e va detto, perché il giorno in
    cui qualcuno passasse questo oggetto a un listener la regola cadrebbe qui.
    """

    def __init__(self, flusso: TextIO, *, larghezza: int | None = COLONNE_SALA) -> None:
        self._flusso = flusso
        self._larghezza = larghezza

    def emit(self, evento: Evento) -> None:
        self._flusso.write(riga(evento, larghezza=self._larghezza) + "\n")
        self._flusso.flush()
