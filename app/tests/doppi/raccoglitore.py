"""Il sink che non disegna niente e ricorda tutto."""

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

    def emit(self, evento: Evento) -> None:
        self.eventi.append(evento)
