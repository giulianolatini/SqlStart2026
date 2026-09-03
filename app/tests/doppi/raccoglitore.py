"""Il sink che non disegna niente e ricorda tutto — nemmeno chi lo ha chiamato."""

import threading

from mongolab.domain.eventi import Evento

__all__ = ["RecordingSink"]


class RecordingSink:
    """Un `EventSink` che accumula gli eventi in una lista, in ordine di arrivo.

    È il doppio più importante del branch, e la ragione è nel verso in cui si legge: le
    prove dei Task 5 e 6 asseriscono sulla **sequenza di eventi**, cioè sul comportamento
    osservabile, e non su ciò che compare a schermo. Un `WorkloadRunner` provato guardando
    la resa di Rich sarebbe provato attraverso il pezzo più volatile del progetto; provato
    attraverso questa lista, resta provato anche quando la TUI cambia — che è tutto il
    guadagno dell'architettura esagonale (ADR-0007), reso concreto in venti righe.

    Ordine e nient'altro: non riordina, non deduplica, non tiene solo l'ultimo per specie.
    Gli stessi eventi in ordine diverso sono una cronaca diversa del failover.

    Tenere il riferimento all'evento invece di copiarlo è lecito perché gli eventi sono
    congelati e slottati: nessuno può cambiarli dopo l'emissione, che è esattamente la
    proprietà per cui la coda del Task 7 è un punto di consegna e non uno stato condiviso
    (ADR-0019).
    """

    def __init__(self) -> None:
        self.eventi: list[Evento] = []
        self.chiamanti: set[int] = set()
        """Gli identificatori dei thread che hanno chiamato `emit`.

        Il §6.3 non promette qualcosa sugli eventi ma su **chi li consegna**: un solo
        punto di sincronizzazione, un solo thread che tocca il sink. È una promessa
        asseribile solo se il sink ricorda da dove è stato chiamato, e senza queste due
        righe la regola resterebbe una frase del design — di quelle che restano vere
        finché qualcuno non emette da un worker e nessuno se ne accorge.
        """

    def emit(self, evento: Evento) -> None:
        self.chiamanti.add(threading.get_ident())
        self.eventi.append(evento)
