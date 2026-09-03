"""Le fixture della suite di integrazione: uno stack acceso, un archivio, e nessun residuo.

Girano contro **gli stack di questo repository** avviati con i `make up-0X` che già
esistono — non contro un facsimile e non con `testcontainers`
([ADR-0020](../../../docs/Decision.md#adr-0020), che supera ADR-0011). Il §7 del design
dice ancora il contrario e va letto insieme a quell'ADR.

**Perché le fixture di stack sono tre e non una parametrizzata.** Una fixture unica con
`params=["01", "02", "03"]` farebbe girare ogni prova su tutti e tre, e accenderebbe tre
stack per verificare cose che uno solo basta a verificare: il contratto di `DocumentStore`
non cambia fra un'istanza singola e uno sharded cluster, e provarlo tre volte costa minuti
senza aggiungere una sola informazione. Gli stack che una prova chiede sono quelli di cui
ha davvero bisogno — la distribuzione per shard il 03, la topologia con primario il 02 —
e le altre restano sul 01, che si accende in pochi secondi.

**Perché ogni fixture è a livello di sessione.** Accendere è la parte cara; il database
usa-e-getta è la parte che deve essere per prova. Le due cose hanno vite diverse e qui
hanno scope diversi.
"""

from typing import Any, Iterator

import pytest
from pymongo import MongoClient
from pymongo.collection import Collection

from mongolab.infrastructure.store import PymongoStore

from tests.integration.ambiente import (
    STACK,
    Stack,
    collezione_usa_e_getta,
    connetti,
    spazza,
    sveglia,
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Marca ogni prova con gli stack che chiede, **deducendoli dalle fixture**.

    I marcatori esistono perché `-m "not stack03"` possa saltare lo sharded cluster quando
    si sta lavorando sull'adattatore e non sulla distribuzione. Metterli a mano
    funzionerebbe fino al primo che se ne dimentica: la prova chiederebbe `stack03`,
    accenderebbe il cluster, e `-m "not stack03"` non la escluderebbe — cioè il comando
    farebbe esattamente il contrario di quello che dice. Dedotti dalla lista delle fixture
    non possono divergere, perché la fixture è la stessa cosa che li rende necessari.
    """
    for prova in items:
        for chiave in STACK:
            if f"stack{chiave}" in getattr(prova, "fixturenames", ()):
                prova.add_marker(f"stack{chiave}")


def _acceso(chiave: str) -> Iterator[MongoClient[dict[str, Any]]]:
    """Accende lo stack se serve, spazza i residui, e restituisce un client per la sessione.

    La spazzata all'inizio e non alla fine, ed è deliberato: alla fine tocca alle singole
    prove, che tolgono il proprio database appena finiscono. Quella all'inizio raccoglie
    ciò che una sessione **interrotta** ha lasciato — un Ctrl-C non esegue nessun teardown,
    e senza questo passaggio i database orfani si accumulerebbero per settimane.
    """
    stack: Stack = STACK[chiave]
    sveglia(stack)
    client = connetti(stack)
    spazza(client)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture(scope="session")
def stack01() -> Iterator[MongoClient[dict[str, Any]]]:
    """L'istanza singola: nessuna autenticazione, `directConnection`, pochi secondi d'avvio."""
    yield from _acceso("01")


@pytest.fixture(scope="session")
def stack02() -> Iterator[MongoClient[dict[str, Any]]]:
    """Il replica set, visto dall'host — con la riserva sulla topologia scritta in `connetti`."""
    yield from _acceso("02")


@pytest.fixture(scope="session")
def stack03() -> Iterator[MongoClient[dict[str, Any]]]:
    """Lo sharded cluster, attraverso il mongos. L'unico su cui `shard_distribution` risponde."""
    yield from _acceso("03")


@pytest.fixture
def collezione(
    stack01: MongoClient[dict[str, Any]],
) -> Iterator[Collection[dict[str, Any]]]:
    """Una collezione vuota, in un database che sparisce quando la prova finisce."""
    with collezione_usa_e_getta(stack01) as coll:
        yield coll


@pytest.fixture
def archivio(collezione: Collection[dict[str, Any]]) -> PymongoStore:
    """`PymongoStore` su una collezione vuota dello stack 01.

    È la fixture del contratto: la stessa forma che la suite veloce ottiene costruendo
    `InMemoryStore()`, e con la stessa promessa — l'archivio arriva **vuoto**.
    """
    return PymongoStore(collezione)
