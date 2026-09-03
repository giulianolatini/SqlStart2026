"""Gli aiutanti delle prove. Non sono doppi: non implementano nessuna porta.

Stanno in un modulo a parte perché `tests/doppi/` ha un significato preciso — lì dentro
c'è ciò che sta *al posto* di un pezzo del mondo — e un filtro sulla lista degli eventi
non sta al posto di niente.
"""

from mongolab.domain.eventi import Evento

__all__ = ["specie"]


def specie[E: Evento](eventi: list[Evento], tipo: type[E]) -> list[E]:
    """Gli eventi di una sola specie, **con il loro tipo**.

    Il parametro di tipo non è ornamento. Scritto `-> list[Evento]`, questo filtro
    restituirebbe la classe base, e ogni asserzione su un campo specifico —
    `.durata_ms`, `.tentativo`, `.successivo` — verrebbe bocciata da `mypy --strict`
    con `"Evento" has no attribute ...`. È successo davvero, dieci volte in un colpo, al
    Task 5: la nota di metodo 156 è nata lì.

    Il verso della lezione è quello che conta: un aiutante che perde il tipo lo perde
    **dove le asserzioni sono più specifiche**, cioè dove il controllo serviva di più.
    Il filtro sa quale specie ha cercato; con un parametro di tipo, glielo si fa dire.
    """
    return [evento for evento in eventi if isinstance(evento, tipo)]
