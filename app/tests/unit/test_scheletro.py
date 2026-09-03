"""Lo scheletro esiste, ed è la regola che tiene il dominio pulito.

Il vincolo che questo modulo verifica — `domain` e `application` non importano nulla di
terze parti — è la ragione per cui la suite unitaria gira in millisecondi senza Docker.
Scritto adesso, quando non può fallire, vale poco; scritto adesso, dal Task 5 in poi
varrà molto, perché il momento in cui la regola si rompe è quello in cui serve un
adattatore «solo per un attimo» e nessuno se ne accorge rileggendo il diff.
"""

import mongolab

from tests.aiutanti import SORGENTI, estranei, moduli_importati

STRATI_INTERNI = ("domain", "application")


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


def test_pymongo_si_importa_solo_nell_infrastruttura() -> None:
    """Il Passo 1 del Task 11, come guardia: il driver sta dietro l'adattatore.

    La regola di `test_il_dominio_non_importa_nulla_di_terze_parti` è più severa ma più
    stretta: vale su due strati soltanto. Questa vale su tutti, `cli.py` compreso — e
    `cli.py` è proprio il posto in cui la tentazione arriva, perché è lui che costruisce
    i client. Li costruisce chiamando `bersagli.connetti`, che è l'unico punto del
    repository in cui `MongoClient(...)` compare davvero.

    `bson` è nella stessa lista e non è pignoleria: `bson` è il pacchetto che pymongo
    installa insieme a sé, quindi importarlo altrove sarebbe la stessa dipendenza entrata
    da una porta di servizio.
    """
    driver = {"pymongo", "bson"}
    fuori_posto: list[str] = []
    esaminati = 0
    for modulo in sorted(SORGENTI.rglob("*.py")):
        if modulo.parent.name == "infrastructure":
            continue
        esaminati += 1
        if moduli_importati(modulo.read_text(encoding="utf-8")) & driver:
            fuori_posto.append(str(modulo.relative_to(SORGENTI)))

    assert not fuori_posto, fuori_posto
    assert esaminati >= 4, "la guardia non ha guardato niente"


def test_l_infrastruttura_il_driver_lo_importa_davvero() -> None:
    # Il controllo di sopra passerebbe anche in un repository da cui pymongo è sparito,
    # e passerebbe in silenzio. Questa è la sua controprova.
    importati: set[str] = set()
    for modulo in sorted((SORGENTI / "infrastructure").rglob("*.py")):
        importati |= moduli_importati(modulo.read_text(encoding="utf-8"))

    assert "pymongo" in importati
