"""La regia finta: annota gli ordini, e non ferma niente."""

__all__ = ["RegiaFinta", "RegiaCheRifiuta", "NodoSconosciuto"]


class NodoSconosciuto(RuntimeError):
    """Il nodo che la regia non sa raggiungere. Serve a provare la strada dell'errore."""


class RegiaFinta:
    """Una `Regia` che ricorda che cosa le è stato chiesto, e nell'ordine.

    L'ordine è tutto il valore del doppio. Lo scenario del failover è una sequenza —
    carico, guasto, elezione, ripresa — e sbagliarne l'ordine produce una scena che gira
    lo stesso e racconta un'altra cosa: fermare il nodo *dopo* aver misurato
    l'interruzione darebbe zero millisecondi e nessuno se ne accorgerebbe.

    Non simula gli effetti del guasto, e la scelta è deliberata: chi racconta la topologia
    è il ponte, e nella prova il ponte è la funzione `drena` che lo scenario riceve. Una
    regia che si mettesse a fabbricare `TopologyChanged` sarebbe un secondo narratore,
    cioè esattamente il difetto che ADR-0089 ha tolto da `watch`.
    """

    def __init__(self, *, noti: frozenset[str] | None = None) -> None:
        self.ordini: list[tuple[str, str]] = []
        self._noti = noti

    def _annota(self, verbo: str, nodo: str) -> None:
        if self._noti is not None and nodo not in self._noti:
            raise NodoSconosciuto(nodo)
        self.ordini.append((verbo, nodo))

    def ferma(self, nodo: str) -> None:
        self._annota("ferma", nodo)

    def riavvia(self, nodo: str) -> None:
        self._annota("riavvia", nodo)

    def sospendi(self, nodo: str) -> None:
        self._annota("sospendi", nodo)

    def risveglia(self, nodo: str) -> None:
        self._annota("risveglia", nodo)


class RegiaCheRifiuta:
    """Una `Regia` che solleva a ogni ordine, per provare che cosa fa la scena quando
    il guasto **non** si può provocare.

    È il caso del container senza socket del demone, ridotto alla sua essenza: la scena
    non deve proseguire fingendo che il primario sia caduto, perché i due numeri che ne
    uscirebbero sarebbero un'interruzione di zero millisecondi e zero scritture perse —
    la cronaca di un failover che non è avvenuto, indistinguibile da un failover perfetto.
    """

    def __init__(self, motivo: str = "questa regia non comanda niente") -> None:
        self.motivo = motivo
        self.ordini: list[tuple[str, str]] = []

    def _rifiuta(self, verbo: str, nodo: str) -> None:
        self.ordini.append((verbo, nodo))
        raise NodoSconosciuto(f"{self.motivo}: {verbo} {nodo}")

    def ferma(self, nodo: str) -> None:
        self._rifiuta("ferma", nodo)

    def riavvia(self, nodo: str) -> None:
        self._rifiuta("riavvia", nodo)

    def sospendi(self, nodo: str) -> None:
        self._rifiuta("sospendi", nodo)

    def risveglia(self, nodo: str) -> None:
        self._rifiuta("risveglia", nodo)
