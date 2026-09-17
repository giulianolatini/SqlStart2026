"""Gli aiutanti delle prove. Non sono doppi: non implementano nessuna porta.

Stanno in un modulo a parte perché `tests/doppi/` ha un significato preciso — lì dentro
c'è ciò che sta *al posto* di un pezzo del mondo — e un filtro sulla lista degli eventi
non sta al posto di niente.
"""

import ast
import sys
from pathlib import Path

from mongolab.domain import eventi as modulo_eventi
from mongolab.domain.eventi import Evento

__all__ = [
    "PACCHETTO",
    "SORGENTI",
    "estranei",
    "moduli_importati",
    "sottoclassi_di_evento",
    "specie",
]

SORGENTI = Path(__file__).resolve().parents[1] / "src" / "mongolab"
PACCHETTO = "mongolab"


def moduli_importati(sorgente: str) -> set[str]:
    """I nomi di primo livello importati da un sorgente.

    Gli import relativi non compaiono: `from .eventi import X` ha `level > 0` e per
    costruzione resta dentro il pacchetto, quindi non è una dipendenza verso l'esterno.
    """
    trovati: set[str] = set()
    for nodo in ast.walk(ast.parse(sorgente)):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                trovati.add(alias.name.split(".")[0])
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level == 0 and nodo.module is not None:
                trovati.add(nodo.module.split(".")[0])
    return trovati


def estranei(sorgente: str) -> set[str]:
    """I moduli importati che non sono né la libreria standard né il pacchetto.

    Nato al Task 2 per una regola sola — `domain` e `application` non toccano niente di
    terze parti — serve dal Task 10 anche a una seconda: dentro `presentation`, Rich lo
    importa **un modulo solo**. Le due guardie chiedono la stessa cosa a strati diversi,
    e conviene che la chiedano con lo stesso arnese.
    """
    ammessi = sys.stdlib_module_names | {PACCHETTO}
    return moduli_importati(sorgente) - ammessi


def sottoclassi_di_evento() -> list[type[Evento]]:
    """Gli eventi dichiarati nel modulo, scoperti invece che elencati.

    Elencarli a mano vorrebbe dire che una decima classe aggiunta domani sfugge a ogni
    regola che li riguarda, e sfugge in silenzio: le prove continuerebbero a passare
    parlando delle nove che già conoscevano.

    La nona è arrivata davvero, al Task 6, ed è andata come doveva: la guardia di
    `test_dominio.py` ha fallito, e per farla tornare verde è servito un ADR (l'0082)
    invece di una riga in più in un insieme.

    Sta qui e non più in `test_dominio.py` da quando le guardie che ne hanno bisogno sono
    due: dal Task 10 anche la presentazione pretende che **ogni** evento sappia diventare
    una riga, e una copia della scoperta in due file sarebbe una copia che invecchia.
    """
    return [
        valore
        for valore in vars(modulo_eventi).values()
        if isinstance(valore, type) and issubclass(valore, Evento) and valore is not Evento
    ]


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
