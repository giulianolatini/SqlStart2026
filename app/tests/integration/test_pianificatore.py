"""`PymongoStore.explain` contro un cluster vero: mirata contro scatter-gather.

È il Passo 3 del Blocco 3, dal lato del client. La pagina dello sharded lo dimostra già
dalla shell; qui la stessa cosa passa da una porta, perché è quella che la scena userà.

**Perché una collezione usa-e-getta e non `lab.ordini`.** Il piano non dipende da quanti
documenti ci sono ma dalla chiave, e una prova che si appoggia al seed racconta quale
profilo è stato avviato invece del comportamento del codice. La chiave qui è la stessa del
repository — `{_id: "hashed"}`, come in `docker/03-sharded/init/30-dati-demo.js` — perché
è quella la chiave di cui il talk parla.
"""

from contextlib import contextmanager
from typing import Any, Iterator

import pytest
from pymongo import MongoClient
from pymongo.errors import OperationFailure

from mongolab.domain.porte import QueryPlanner
from mongolab.infrastructure.generatore import DataGenerator
from mongolab.infrastructure.store import PymongoStore

from tests.integration.ambiente import collezione_usa_e_getta

DOCUMENTI = 200


def test_il_pianificatore_passa_per_la_porta(
    stack03: MongoClient[dict[str, Any]],
) -> None:
    """La conformità strutturale, verificata dove mypy la verifica: in un'annotazione.

    E la riga dice anche l'altra metà di ADR-0105: `PymongoStore` soddisfa **due** porte,
    e non ha dovuto ereditarne nessuna per farlo.
    """
    with _sparsa(stack03) as archivio:
        pianificatore: QueryPlanner = archivio
        assert pianificatore.explain({}).stadio


def test_una_query_sulla_chiave_di_shard_va_a_un_solo_shard(
    stack03: MongoClient[dict[str, Any]],
) -> None:
    """`{_id: 42}` con chiave hashed: il router sa dove sta, e chiede solo lì.

    È la metà buona della dimostrazione, e da sola non dimostra niente: qualunque query su
    un cluster a uno shard risulterebbe mirata. Vale accanto alla prova che segue.
    """
    with _sparsa(stack03) as archivio:
        piano = archivio.explain({"_id": 42})

    assert piano.stadio == "SINGLE_SHARD"
    assert piano.mirata
    assert len(piano.shard) == 1


def test_una_query_su_un_campo_qualunque_interroga_tutti_gli_shard(
    stack03: MongoClient[dict[str, Any]],
) -> None:
    """`{citta: "Ancona"}`: nessuno sa dove stiano, quindi si chiede a tutti."""
    with _sparsa(stack03) as archivio:
        piano = archivio.explain({"citta": "Ancona"})

    assert piano.stadio == "SHARD_MERGE"
    assert not piano.mirata
    assert len(piano.shard) == 2


def test_un_intervallo_sulla_chiave_hashed_e_comunque_scatter_gather(
    stack03: MongoClient[dict[str, Any]],
) -> None:
    """La sorpresa della scena, e il prezzo dichiarato della chiave hashed.

    Stesso campo della chiave di shard, e il router **non** riesce a indirizzarla: l'hash
    di 100 e l'hash di 101 non sono vicini, quindi «gli `_id` fra 100 e 200» non è un
    intervallo di nessuno shard. Lo dice già `30-dati-demo.js`, che sceglie la chiave
    sapendolo; qui si vede che il router si comporta come annunciato.
    """
    with _sparsa(stack03) as archivio:
        piano = archivio.explain({"_id": {"$gte": 100, "$lt": 200}})

    assert piano.stadio == "SHARD_MERGE"
    assert not piano.mirata


def test_il_piano_riporta_il_filtro_che_gli_e_stato_dato(
    stack03: MongoClient[dict[str, Any]],
) -> None:
    # Il piano viaggia da solo fino allo schermo, e senza il filtro dentro la scena
    # stamperebbe il piano di una query accanto al testo di un'altra.
    with _sparsa(stack03) as archivio:
        piano = archivio.explain({"_id": 42})

    assert piano.filtro == {"_id": 42}


def test_gli_shard_del_piano_escono_ordinati(
    stack03: MongoClient[dict[str, Any]],
) -> None:
    """L'ordine che il server dà **non** è stabile, e la scena confronta due schermate.

    Misurato prima di scriverlo: lo stesso mongos, a due filtri diversi, ha risposto una
    volta `['shard2rs', 'shard1rs']` e una volta `['shard1rs', 'shard2rs']`. Due righe che
    si scambiano di posto in scena sembrano un cambiamento che non c'è stato.
    """
    with _sparsa(stack03) as archivio:
        piano = archivio.explain({"citta": "Ancona"})

    assert list(piano.shard) == sorted(piano.shard)


def test_su_un_database_che_non_esiste_il_piano_non_si_inventa(
    stack03: MongoClient[dict[str, Any]],
) -> None:
    """Misurato al primo giro verde, e non era quello che ci si aspettava.

    Dal mongos, `explain` di un namespace il cui **database** non esiste solleva
    `NamespaceNotFound` invece di rispondere con un piano vuoto: il router non ha nessuno
    a cui girare la domanda. Su un mongod la stessa query risponderebbe `EOF`.

    La prova sta qui per due ragioni. La prima è che il comportamento è del driver e del
    server, non di questo codice, e una caratterizzazione che nessuno ha scritto è una
    sorpresa che aspetta la scena. La seconda è che dice dove sta il confine: la scena del
    Blocco 3 scrive **prima** e interroga **dopo**, e finché resta in quest'ordine il caso
    non la tocca.
    """
    with collezione_usa_e_getta(stack03) as collezione:
        with pytest.raises(OperationFailure):
            PymongoStore(collezione).explain({})


@contextmanager
def _sparsa(cliente: MongoClient[dict[str, Any]]) -> Iterator[PymongoStore]:
    """Una collezione distribuita con la chiave del repository, piena e usa-e-getta."""
    with collezione_usa_e_getta(cliente) as collezione:
        nome = f"{collezione.database.name}.{collezione.name}"
        cliente.admin.command("enableSharding", collezione.database.name)
        cliente.admin.command("shardCollection", nome, key={"_id": "hashed"})
        archivio = PymongoStore(collezione)
        archivio.insert_many(list(DataGenerator().lotto(DOCUMENTI)))
        yield archivio
