"""Come le prove di integrazione raggiungono gli stack di questo repository.

[ADR-0020](../../../docs/Decision.md#adr-0020) è la regola che governa questo file: non si
usa `testcontainers` e non si costruisce un facsimile. Le prove girano contro gli stessi
`docker/0X-*/compose.yaml` che il pubblico avvierà, avviati con gli stessi `make up-0X`.
Un adattatore provato contro un MongoDB diverso da quello della serata è un adattatore
provato contro qualcos'altro.

## Che cosa questo modulo **non** decide più

Fino al Task 10 qui dentro stavano le porte dei tre stack, i loro `.env` e la scelta di
`directConnection`. Dal Task 11 quei fatti sono in `mongolab.infrastructure.bersagli`,
perché adesso ha bisogno di conoscerli anche l'applicazione — e due copie della stessa
mappa sono due mappe diverse dal primo cambio in poi. Il verso della dipendenza è l'unico
possibile: le prove importano la produzione, mai il contrario. Qui resta ciò che è
davvero solo delle prove — quale `make up-0X` accende cosa, e come si smontano i dati.

## Due cose che questo modulo decide ancora, e perché

**Lo stack si accende solo se non risponde.** Un `make up-0X` a ogni sessione sarebbe
idempotente e costerebbe qualche secondo di `docker compose` anche quando tutto è già in
piedi; un `ping` con due secondi di pazienza costa qualche millisecondo e dice la stessa
cosa. Se il `ping` non passa, allora sì: `make up-0X`, e poi si riprova con la pazienza
lunga che serve a uno sharded cluster che parte da zero.

**Lo stack non si spegne alla fine.** Passo 5 chiede che una prova smonti ciò che ha
acceso, e qui *ciò che ha acceso* sono i **dati**, non i container. Spegnere uno stack che
l'operatore aveva già su sarebbe un effetto che la prova non ha causato: si ritroverebbe
la macchina in uno stato diverso da come l'aveva lasciata, per aver eseguito dei test. I
dati invece si portano via tutti, e il modo è un database intero usa-e-getta.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Final, Iterator, Mapping
from uuid import uuid4
import subprocess

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from mongolab.infrastructure.bersagli import (
    BERSAGLI,
    Bersaglio,
    Credenziali,
    radice,
)
from mongolab.infrastructure.bersagli import connetti as _connetti
from mongolab.infrastructure.bersagli import credenziali_di as _credenziali_di

__all__ = [
    "PREFISSO_PROVE",
    "STACK",
    "Credenziali",
    "Stack",
    "collezione_usa_e_getta",
    "connetti",
    "credenziali_di",
    "radice",
    "sveglia",
]

PREFISSO_PROVE: Final = "mongolab_prove_"
"""Il prefisso di ogni database che queste prove creano.

Esiste perché la pulizia sia **riconoscibile**: se una prova viene interrotta a metà — un
Ctrl-C, un kill, un timeout di CI — il suo database resta sullo stack, e senza un prefisso
convenuto nessuno saprebbe distinguerlo da `lab`. Con il prefisso, la sessione successiva
lo trova e lo toglie, e nessuno tocca mai un database che non abbia questo nome.
"""


@dataclass(frozen=True)
class Stack:
    """Uno dei tre stack, come lo vedono le prove: un bersaglio più il modo di accenderlo.

    `quale` porta tutto ciò che serve per **collegarsi**, e lo porta dalla mappa di
    produzione. Qui si aggiunge la sola cosa che l'applicazione non ha ragione di sapere:
    con quale target del Makefile si tira su. Le quattro proprietà che seguono sono
    inoltri, e non campi copiati, perché un campo copiato è una copia.
    """

    quale: Bersaglio
    bersaglio: str
    """Il target del Makefile che lo accende: `up-01`, `up-02`, `up-03`."""

    @property
    def nome(self) -> str:
        """Il nome della directory sotto `docker/`, che è anche quello nei log."""
        return self.quale.stack

    @property
    def porta(self) -> int:
        """La porta pubblicata sull'host, non quella interna al container."""
        return self.quale.porta

    @property
    def diretto(self) -> bool:
        return self.quale.diretto

    @property
    def ambiente(self) -> str | None:
        return self.quale.ambiente


STACK: Final[Mapping[str, Stack]] = {
    "01": Stack(quale=BERSAGLI["standalone"], bersaglio="up-01"),
    "02": Stack(quale=BERSAGLI["rs"], bersaglio="up-02"),
    "03": Stack(quale=BERSAGLI["sharded"], bersaglio="up-03"),
}
"""I tre stack, chiavati con il numero che le fixture usano nei marcatori.

Le chiavi restano `01`/`02`/`03` e non i nomi di `--target`: i marcatori si chiamano
`stack01`, `stack02`, `stack03` da prima che i bersagli esistessero, e rinominarli
cambierebbe la riga `-m "not stack03"` che sta scritta in tre pagine di documentazione
per risparmiare un'indirezione a chi legge questo file.
"""


def credenziali_di(stack: Stack) -> Credenziali | None:
    """Le credenziali dello stack, lette dal `.env` che il bersaglio dichiara."""
    return _credenziali_di(stack.quale)


def connetti(stack: Stack, attesa_ms: int = 20_000) -> MongoClient[dict[str, Any]]:
    """Un client verso lo stack, dall'host.

    Le tre scelte misurate al Task 8 — `tz_aware=True`, la credenziale come argomenti e
    non nell'URI, `directConnection` secondo il punto di vista — stanno adesso in
    `mongolab.infrastructure.bersagli.connetti`, che è ciò che usa anche l'applicazione.
    Provarle qui contro una copia locale sarebbe stato provare l'altra implementazione.
    """
    return _connetti(stack.quale, attesa_ms=attesa_ms)


def risponde(stack: Stack, attesa_ms: int) -> bool:
    """Un `ping`, e nessuna eccezione lasciata uscire.

    Restituisce un booleano invece di sollevare perché chi chiama deve poter distinguere
    «non c'è» da «è rotto», e a questo livello non c'è modo di distinguerli: uno stack
    spento e uno stack malato falliscono la stessa chiamata. La differenza la fa `sveglia`,
    che dopo un `make up-0X` riprova — e se fallisce ancora, allora è rotto davvero.
    """
    try:
        client = connetti(stack, attesa_ms=attesa_ms)
    except RuntimeError:
        raise
    try:
        client.admin.command("ping")
        return True
    except PyMongoError:
        return False
    finally:
        client.close()


def sveglia(stack: Stack) -> None:
    """Si assicura che lo stack risponda, accendendolo con il suo `make up-0X` se serve.

    Il `make` non è ricostruito qui e non è imitato: è **quello del repository**, con i
    suoi `--wait`, i suoi healthcheck e i suoi container di inizializzazione. Rifarne una
    versione python-side vorrebbe dire provare l'adattatore contro un avvio diverso da
    quello che il pubblico userà, che è esattamente ciò che ADR-0020 vieta.

    Dieci minuti di timeout perché lo `03` deve tirare su due shard, tre config server, un
    mongos, generare un keyfile e caricare il seed. Sulla macchina della prova generale ci
    mette molto meno; il numero serve a non lasciare una CI appesa per sempre.
    """
    if risponde(stack, attesa_ms=2_000):
        return
    esito = subprocess.run(
        ["make", stack.bersaglio],
        cwd=radice(),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if esito.returncode != 0:
        # Le ultime venti righe e non tutte: `docker compose` ne produce centinaia, e la
        # ragione del fallimento è sempre in fondo.
        coda = "\n".join((esito.stdout + esito.stderr).splitlines()[-20:])
        raise RuntimeError(
            f"`make {stack.bersaglio}` è uscito con {esito.returncode}.\n{coda}"
        )
    if not risponde(stack, attesa_ms=20_000):
        raise RuntimeError(
            f"`make {stack.bersaglio}` è riuscito ma localhost:{stack.porta} non risponde. "
            f"Se sei dentro un container o su una macchina remota, la porta non è pubblicata lì."
        )


def spazza(client: MongoClient[dict[str, Any]]) -> int:
    """Toglie i database rimasti da una sessione interrotta. Restituisce quanti.

    Tocca **solo** ciò che comincia per `PREFISSO_PROVE`, e questa è l'unica garanzia che
    conta: uno strumento di pulizia che si sbaglia sul filtro cancella il lavoro di
    qualcun altro, e lo fa in silenzio perché è il suo mestiere cancellare.
    """
    tolti = 0
    for nome in client.list_database_names():
        if nome.startswith(PREFISSO_PROVE):
            client.drop_database(nome)
            tolti += 1
    return tolti


@contextmanager
def collezione_usa_e_getta(
    client: MongoClient[dict[str, Any]], collezione: str = "ordini"
) -> Iterator[Collection[dict[str, Any]]]:
    """Un database tutto per una prova, e alla fine non c'è più.

    Un **database** e non una collezione: `drop_database` è una chiamata sola e porta via
    anche gli indici, le collezioni che la prova avesse creato per conto suo e i residui
    di `$out`. Una collezione lasciata indietro non fa fallire subito — fa fallire la
    prova dopo, con un conteggio che non torna e un motivo che sembra un altro.

    Il nome è casuale perché le prove possano girare in parallelo sullo stesso stack senza
    accordarsi, e perché due esecuzioni sovrapposte non si contino i documenti a vicenda.
    """
    nome = f"{PREFISSO_PROVE}{uuid4().hex[:12]}"
    try:
        yield client[nome][collezione]
    finally:
        client.drop_database(nome)
