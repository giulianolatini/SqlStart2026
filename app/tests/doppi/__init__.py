"""I doppi delle sei porte, scritti prima degli adattatori veri.

**Prima, e non dopo, per una ragione sola.** I Task 5 e 6 fanno TDD contro questi
oggetti: sono ciò che sta dall'altra parte della porta mentre `WorkloadRunner` e
`TopologyWatcher` non esistono ancora. Scriverli dopo significherebbe modellarli
sull'implementazione che devono verificare — e un doppio disegnato guardando il codice
sotto prova concorda con lui per costruzione, cioè produce prove che non provano niente.

**Doppi, non finzioni.** Ognuno mantiene davvero la promessa della sua porta:
`InMemoryStore` conserva i documenti e filtra sul serio, `FakeClock` fa passare il tempo
per davvero. Dove non sa fare qualcosa — una pipeline di aggregazione che non conosce —
**solleva**, e non restituisce un risultato plausibile: un doppio che tace su ciò che non
sa fa passare la prova per il motivo sbagliato, che è il modo più silenzioso che una
suite abbia di mentire. La regola operativa è nel piano: se una prova ha bisogno di
qualcosa che il doppio non sa fare, glielo si insegna; non lo si finge.

**Perché in `tests/` e non in `src/`.** Non fanno parte di ciò che si distribuisce, e
soprattutto nessuno di loro importa il dominio per conformarsi: le porte sono `Protocol`,
la conformità è strutturale, ed è `mypy --strict` a verificarla nel punto in cui una
prova scrive `archivio: DocumentStore = InMemoryStore()`. La loro promessa è verificata
in `tests/unit/test_doppi.py`.
"""

from tests.doppi.archivio import (
    ArchivioCheNonLegge,
    ArchivioCheRompe,
    ArchivioLento,
    InMemoryStore,
    LetturaRifiutata,
    NonSupportato,
    ScritturaRifiutata,
)
from tests.doppi.backup import FakeBackup
from tests.doppi.ispettore import FakeInspector
from tests.doppi.orologio import FakeClock, OrologioCheScorre
from tests.doppi.raccoglitore import RecordingSink
from tests.doppi.regia import NodoSconosciuto, RegiaCheRifiuta, RegiaFinta

__all__ = [
    "ArchivioCheNonLegge",
    "ArchivioCheRompe",
    "ArchivioLento",
    "FakeBackup",
    "FakeClock",
    "FakeInspector",
    "InMemoryStore",
    "LetturaRifiutata",
    "NodoSconosciuto",
    "NonSupportato",
    "OrologioCheScorre",
    "RecordingSink",
    "RegiaCheRifiuta",
    "RegiaFinta",
    "ScritturaRifiutata",
]
