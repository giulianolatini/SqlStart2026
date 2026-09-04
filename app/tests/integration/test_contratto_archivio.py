"""Il contratto di `DocumentStore` eseguito contro `PymongoStore` e MongoDB vero.

L'altra metà della coppia: le stesse undici funzioni che `tests/unit/test_contratto_archivio.py`
esegue contro `InMemoryStore`. Se una passa di là e fallisce di qua, il doppio ha mentito —
ed è già successo alla prima esecuzione, con `$count` su una collezione vuota (M-017).

Sotto il contratto c'è la seconda metà del Passo 4, che il contratto da solo non può
coprire: **dove il doppio e l'originale non coincidono**. Ogni divergenza ha una prova che
asserisce entrambi i comportamenti nello stesso corpo, perché una divergenza scritta in un
commento è una divergenza che nessuno rilegge.
"""

from datetime import UTC, datetime
from typing import Any, Callable

import pytest
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import BulkWriteError

from mongolab.domain.porte import DocumentStore
from mongolab.infrastructure.store import PymongoStore

from tests.contratto_archivio import VERIFICHE, ordini
from tests.doppi.archivio import InMemoryStore, NonSupportato


@pytest.mark.parametrize("verifica", VERIFICHE, ids=lambda v: v.__name__)
def test_l_adattatore_rispetta_il_contratto(
    verifica: Callable[[DocumentStore], None], archivio: PymongoStore
) -> None:
    """Undici prove contro un MongoDB acceso, con gli stessi nomi della suite veloce.

    Gli `ids` coincidono con quelli dell'altra metà apposta: due esiti affiancati si
    leggono riga per riga, e la riga che diverge si vede senza contare.
    """
    porta: DocumentStore = archivio
    verifica(porta)


# --- Dove il doppio e l'originale non coincidono --------------------------------------
#
# Cinque punti. In ognuno il doppio fa una cosa e MongoDB ne fa un'altra, e in ognuno la
# prova asserisce **tutte e due**: senza il lato del doppio non si vedrebbe che è una
# divergenza, e senza il lato dell'originale non si saprebbe verso cosa.


def test_l_originale_conosce_gli_operatori_che_il_doppio_rifiuta(
    archivio: PymongoStore,
) -> None:
    """`$gt` esiste in MongoDB e non nel doppio, e va bene così.

    Il doppio solleva `NonSupportato` **apposta**: se ignorasse l'operatore
    restituirebbe tutti i documenti e la prova che lo usa diventerebbe verde per il motivo
    sbagliato. Il prezzo di quella scelta è che una prova con `$gt` non può stare nel
    contratto condiviso, e questa è la sede in cui il prezzo si dichiara.
    """
    archivio.insert_many(ordini())
    assert archivio.count({"importo": {"$gt": 15}}) == 2

    doppio = InMemoryStore()
    doppio.insert_many(ordini())
    with pytest.raises(NonSupportato, match=r"\$gt"):
        doppio.count({"importo": {"$gt": 15}})


def test_l_originale_confronta_i_sottodocumenti_e_l_ordine_dei_campi_conta(
    archivio: PymongoStore,
) -> None:
    """La divergenza più insidiosa delle cinque, perché il doppio aveva ragione a tacere.

    Il manuale dice che il confronto con un sottodocumento intero richiede «an *exact*
    match … **including the field order**» ([A-007](../../docs/Sources.md#a-007)). Qui si
    vede eseguito: lo stesso `dict` Python, scritto con le chiavi in ordine diverso, trova
    un documento in un caso e zero nell'altro — mentre per Python i due `dict` sono
    **uguali**. Il doppio, che confronta con `==`, direbbe sì tutte e due le volte: non
    imitando, non ha sbagliato.
    """
    archivio.insert_many([{"_id": 1, "misura": {"h": 14, "w": 21}}])

    assert archivio.count({"misura": {"h": 14, "w": 21}}) == 1
    assert archivio.count({"misura": {"w": 21, "h": 14}}) == 0
    assert {"h": 14, "w": 21} == {"w": 21, "h": 14}, "in Python i due filtri sono lo stesso"

    doppio = InMemoryStore()
    doppio.insert_many([{"_id": 1, "misura": {"h": 14, "w": 21}}])
    with pytest.raises(NonSupportato, match="sottodocumenti"):
        doppio.count({"misura": {"w": 21, "h": 14}})


def test_l_originale_esegue_group_che_il_doppio_non_conosce(archivio: PymongoStore) -> None:
    """`$group` arriverà nel doppio il giorno in cui una prova unitaria ne avrà bisogno."""
    archivio.insert_many(ordini())

    raggruppati = archivio.aggregate(
        [
            {"$group": {"_id": "$stato", "quanti": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
    )

    assert [(riga["_id"], riga["quanti"]) for riga in raggruppati] == [
        ("annullato", 1),
        ("confermato", 2),
    ]

    doppio = InMemoryStore()
    with pytest.raises(NonSupportato, match=r"\$group"):
        doppio.aggregate([{"$group": {"_id": "$stato"}}])


def test_l_originale_rifiuta_un_id_duplicato_e_il_doppio_lo_accetta(
    archivio: PymongoStore,
) -> None:
    """Il doppio è una lista, e una lista accetta due volte lo stesso `_id`.

    MongoDB no: solleva, e il tipo è `BulkWriteError` perché l'inserimento è massivo. La
    divergenza conta per il Task 13: dopo un fallimento **parziale**, riprovare lo stesso
    blocco produce duplicati sui documenti che erano già passati, e il ritentativo cieco
    perde i pochi che mancavano davvero. È una riserva del carico, non di questo file, e
    sta scritta qui perché è qui che si vede.
    """
    with pytest.raises(BulkWriteError):
        archivio.insert_many([{"_id": 1, "a": 1}, {"_id": 1, "a": 2}])

    doppio = InMemoryStore()
    assert doppio.insert_many([{"_id": 1, "a": 1}, {"_id": 1, "a": 2}]) == 2
    assert doppio.count({}) == 2


def test_l_originale_non_promette_l_ordine_che_il_doppio_garantisce(
    collezione: Collection[dict[str, Any]],
) -> None:
    """Il doppio restituisce in ordine d'inserimento; MongoDB non promette niente.

    `PymongoStore` compra la stabilità con un `sort` esplicito su `_id`, perché una pagina
    che cambia fra una chiamata e l'altra non è una pagina — con `skip` e `limit` si
    finirebbe per vedere due volte lo stesso documento e mai un altro. Il costo è che
    l'ordine è quello degli `_id`, non quello degli inserimenti, e qui i due si separano
    apposta: si inserisce 3, 1, 2 e si rilegge 1, 2, 3.

    Sotto, la stessa collezione letta **senza** ordinamento. Non si asserisce che l'ordine
    sia diverso — su una collezione così piccola WiredTiger la restituisce quasi sempre
    per `_id` e l'asserzione sarebbe capricciosa — si asserisce che ci siano tutti e tre.
    L'ordine è ciò che non si può affermare, e dirlo è il contenuto della prova.
    """
    archivio = PymongoStore(collezione)
    archivio.insert_many([{"_id": 3, "n": "terzo"}, {"_id": 1, "n": "primo"}, {"_id": 2, "n": "secondo"}])

    assert [documento["_id"] for documento in archivio.find_page({})] == [1, 2, 3]

    grezzi = [documento["_id"] for documento in collezione.find({})]
    assert sorted(grezzi) == [1, 2, 3]

    doppio = InMemoryStore()
    doppio.insert_many([{"_id": 3, "n": "terzo"}, {"_id": 1, "n": "primo"}, {"_id": 2, "n": "secondo"}])
    assert [documento["_id"] for documento in doppio.find_page({})] == [3, 1, 2]


# --- Ciò che solo l'adattatore vero può sbagliare -------------------------------------


def test_un_client_senza_tz_aware_viene_rifiutato_alla_costruzione(
    stack01: MongoClient[dict[str, Any]],
) -> None:
    """La guardia che rende impossibile la data sbagliata, e la prova che senza si passa.

    Senza `tz_aware=True` pymongo riconsegna i `datetime` **ingenui**, e nessuno solleva:
    il confronto fra due ingenui riesce e sbaglia di quante ore vale il fuso. È un difetto
    che passa tutte le prove e si vede solo in una data storta sullo schermo.

    La prova non si accontenta di vedere la `ValueError`: costruisce prima il caso in cui
    la guardia **mancherebbe** — la stessa collezione, l'andata e ritorno di un istante —
    e mostra che il valore torna diverso. Senza questa metà si verificherebbe che una
    guardia c'è, non che serve ([nota 159](../../../docs/registro-operativo-sviluppo.md)).
    """
    ingenuo: MongoClient[dict[str, Any]] = MongoClient(
        stack01.address and f"mongodb://{stack01.address[0]}:{stack01.address[1]}/",
        directConnection=True,
        tz_aware=False,
    )
    try:
        collezione = ingenuo["mongolab_prove_tz"]["ordini"]
        istante = datetime(2026, 9, 18, 9, 30, tzinfo=UTC)
        collezione.insert_one({"_id": 1, "quando": istante})
        [riletto] = list(collezione.find({}))
        assert riletto["quando"].tzinfo is None, "il difetto che la guardia previene"
        assert riletto["quando"] != istante

        with pytest.raises(ValueError, match="tz_aware"):
            PymongoStore(collezione)
    finally:
        ingenuo.drop_database("mongolab_prove_tz")
        ingenuo.close()


def test_l_adattatore_non_scrive_l_id_nel_documento_di_chi_lo_ha_chiamato(
    archivio: PymongoStore,
) -> None:
    """Il motivo per cui `insert_many` copia, che il doppio non ha.

    `pymongo` genera l'`_id` mancante **dentro** il dizionario ricevuto, non in una copia:
    è documentato ed è comodo per chi vuole recuperarlo. Per il carico è un guaio, perché
    il generatore riusa i propri dizionari e al secondo giro si troverebbe un `_id` già
    dentro — inserendo due volte lo stesso, cioè un `BulkWriteError` al posto di una
    scrittura.

    Sotto, la stessa chiamata fatta al driver **senza** l'adattatore: è il caso in cui la
    copia manca, ed è ciò che rende questa prova la prova di una guardia e non di un
    comportamento qualunque.
    """
    documento: dict[str, object] = {"stato": "confermato"}
    archivio.insert_many([documento])
    assert "_id" not in documento

    diretto: dict[str, object] = {"stato": "confermato"}
    archivio.collezione.insert_many([diretto])
    assert "_id" in diretto, "senza la copia, il driver scrive nel dizionario del chiamante"
