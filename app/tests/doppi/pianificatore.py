"""Il pianificatore che risponde con i piani che la prova ha deciso."""

from typing import Sequence

from mongolab.domain.modelli import Documento, Piano

__all__ = ["FakePlanner"]


class FakePlanner:
    """Un `QueryPlanner` che non ha un router dietro, e non finge di averlo.

    **Una sequenza, non un valore**, come le topologie di `FakeInspector` e per la stessa
    ragione: ciò che il Blocco 3 mostra non è un piano ma il **contrasto** fra due, mirata
    contro scatter-gather. Un doppio a risposta unica proverebbe che il codice chiede, non
    che accosta due risposte diverse.

    **Il filtro torna indietro com'è arrivato.** Il doppio decide lo stadio e gli shard —
    cioè le due cose che solo un router saprebbe — e ricopia la domanda nel piano, come
    farebbe un router vero. Un doppio che restituisse anche un filtro preparato lascerebbe
    passare una scena che stampa il piano di una query accanto al testo di un'altra.

    **Finiti i piani resta sull'ultimo**, di nuovo come `FakeInspector`: un doppio che si
    esaurisse farebbe fallire la prova per il numero di domande invece che per il
    comportamento, e chi la legge aggiusterebbe il numero finché il rosso sparisce.
    """

    def __init__(self, piani: Sequence[tuple[str, Sequence[str]]] = ()) -> None:
        if not piani:
            raise ValueError(
                "un FakePlanner vuole almeno un piano: senza, non c'è niente da "
                "restituire e l'errore si vedrebbe lontano da dove è stato commesso."
            )
        self._piani = tuple((stadio, tuple(shard)) for stadio, shard in piani)
        self.chiesti: list[Documento] = []
        """I filtri arrivati, nell'ordine. È un'asserzione, non un contatore di servizio:
        «la scena contrappone due query» si verifica anche mostrando quali ha chiesto."""

    def explain(self, filtro: Documento) -> Piano:
        stadio, shard = self._piani[min(len(self.chiesti), len(self._piani) - 1)]
        self.chiesti.append(dict(filtro))
        return Piano(filtro=dict(filtro), stadio=stadio, shard=shard)
