"""Lo scheletro esiste, ed è la regola che tiene il dominio pulito.

Il vincolo che questo modulo verifica — `domain` e `application` non importano nulla di
terze parti — è la ragione per cui la suite unitaria gira in millisecondi senza Docker.
Scritto adesso, quando non può fallire, vale poco; scritto adesso, dal Task 5 in poi
varrà molto, perché il momento in cui la regola si rompe è quello in cui serve un
adattatore «solo per un attimo» e nessuno se ne accorge rileggendo il diff.
"""

import ast
import sys
from pathlib import Path

import mongolab

SORGENTI = Path(__file__).resolve().parents[2] / "src" / "mongolab"
STRATI_INTERNI = ("domain", "application")
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
    """I moduli importati che non sono né la libreria standard né il pacchetto."""
    ammessi = sys.stdlib_module_names | {PACCHETTO}
    return moduli_importati(sorgente) - ammessi


def test_il_pacchetto_e_importabile_e_dichiara_la_versione() -> None:
    assert mongolab.__version__ == "0.1.0"


def test_il_pacchetto_e_marcato_come_tipizzato() -> None:
    # Senza `py.typed` mypy tratta il pacchetto come non annotato quando lo importa
    # qualcun altro, e le porte smettono di essere verificabili proprio dal punto di
    # vista che le giustifica.
    assert (SORGENTI / "py.typed").is_file()


def test_i_cinque_pezzi_del_disegno_esistono() -> None:
    # §6.1 del design: quattro strati e il composition root. La prova esiste perché
    # tutte le altre danno per scontato dove stanno le cose.
    assert SORGENTI.is_dir()
    for strato in ("domain", "application", "infrastructure", "presentation"):
        assert (SORGENTI / strato / "__init__.py").is_file(), strato
    assert (SORGENTI / "cli.py").is_file()


def test_il_dominio_non_importa_nulla_di_terze_parti() -> None:
    esaminati = 0
    for strato in STRATI_INTERNI:
        for modulo in sorted((SORGENTI / strato).rglob("*.py")):
            esaminati += 1
            fuori = estranei(modulo.read_text(encoding="utf-8"))
            assert not fuori, f"{modulo.relative_to(SORGENTI)} importa {sorted(fuori)}"
    # Una guardia che non ha guardato niente passa, e passa in silenzio: è il modo in
    # cui un controllo sopravvive a una directory rinominata senza proteggere più
    # nulla. Il conteggio è la sola parte di questa prova che non può diventare vacua.
    assert esaminati >= len(STRATI_INTERNI)


def test_la_guardia_riconosce_una_violazione() -> None:
    # Il controllo di sopra passa anche se `estranei` fosse rotta e restituisse sempre
    # l'insieme vuoto. Qui le si dà da leggere ciò che deve bocciare.
    assert estranei("import pymongo") == {"pymongo"}
    assert estranei("from rich.live import Live") == {"rich"}
    assert estranei("import queue\nfrom dataclasses import dataclass") == set()
    assert estranei("from mongolab.domain import porte") == set()
    assert estranei("from .eventi import WriteSucceeded") == set()
