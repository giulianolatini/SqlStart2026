"""Il contratto di `DocumentStore` eseguito contro `InMemoryStore`.

Metà di una coppia: l'altra metà è `tests/integration/test_contratto_archivio.py`, che
esegue le **stesse** funzioni contro `PymongoStore` e uno stack acceso. Le verifiche non
stanno qui perché non appartengono a questo file più che a quello — stanno in
`tests/contratto_archivio.py`, che nessuno dei due possiede.

Il valore di questo file preso da solo è modesto, ed è giusto così: quello che prova è
che il doppio rispetti un contratto scritto altrove. Il valore sta nella coppia, cioè
nella differenza fra i due esiti.
"""

from typing import Callable

import pytest

from mongolab.domain.porte import DocumentStore

from tests.contratto_archivio import VERIFICHE
from tests.doppi.archivio import InMemoryStore


@pytest.mark.parametrize("verifica", VERIFICHE, ids=lambda v: v.__name__)
def test_il_doppio_rispetta_il_contratto(
    verifica: Callable[[DocumentStore], None],
) -> None:
    """Undici prove, una per verifica, con il nome della verifica nell'esito.

    `ids=` non è cosmesi: senza, pytest chiamerebbe i casi `verifica0`…`verifica10` e un
    rosso direbbe soltanto che «il numero sette» è fallito. Con i nomi, l'esito della
    suite veloce e quello della suite di integrazione si confrontano riga per riga.
    """
    archivio: DocumentStore = InMemoryStore()
    verifica(archivio)
