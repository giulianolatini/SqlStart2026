"""La resa che non rende niente, e che per servire deve non pesare.

Serve a due cose diverse che chiedono la stessa proprietà. Alle prove, come sink neutro
quando l'asserzione non riguarda ciò che si vede. E alle misure del Task 16, dove la
domanda è quanto costa il carico e non quanto costa raccontarlo: un sink che accumulasse
sposterebbe la misura di quello che accumula.
"""

from mongolab.domain.eventi import Evento

__all__ = ["NullSink"]


class NullSink:
    """Un `EventSink` che accetta e dimentica.

    `__slots__` vuoti non sono un vezzo: rendono **impossibile** attaccare un attributo a
    un'istanza, e quindi impossibile che un contatore aggiunto distrattamente un giorno
    trasformi il sink neutro delle misure in qualcosa che cresce con il carico. È
    l'unica promessa che questa classe fa, ed è l'unica che una prova può verificare
    senza cronometrare niente.
    """

    __slots__ = ()

    def emit(self, evento: Evento) -> None:
        return None
