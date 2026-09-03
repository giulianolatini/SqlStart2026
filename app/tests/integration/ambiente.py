"""Come le prove di integrazione raggiungono gli stack di questo repository.

[ADR-0020](../../../docs/Decision.md#adr-0020) è la regola che governa questo file: non si
usa `testcontainers` e non si costruisce un facsimile. Le prove girano contro gli stessi
`docker/0X-*/compose.yaml` che il pubblico avvierà, avviati con gli stessi `make up-0X`.
Un adattatore provato contro un MongoDB diverso da quello della serata è un adattatore
provato contro qualcos'altro.

## Tre cose che questo modulo decide, e perché

**La credenziale non si stampa.** `Credenziali` tiene la password in un campo con
`repr=False`: `repr()` di un'istanza mostra l'utente e non il segreto. Serve perché in una
prova fallita l'oggetto finisce nel traceback, e il traceback finisce in una `.cast` o in
un log di CI. Misurato al Task 8: pymongo dal canto suo non la lascia uscire né in
`ServerSelectionTimeoutError`, né in `OperationFailure`, né in `repr(MongoClient)`
([M-018](../../docs/Sources.md#m-018)) — questo campo copre l'unico punto che restava
scoperto, cioè noi.

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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Iterator, Mapping
from uuid import uuid4
import subprocess

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

__all__ = [
    "PREFISSO_PROVE",
    "STACK",
    "Credenziali",
    "Stack",
    "collezione_usa_e_getta",
    "connetti",
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
class Credenziali:
    """Utente e password, con la password fuori dal `repr`.

    `field(repr=False)` non è offuscamento e non protegge da chi legge il codice: protegge
    dalla **stampa accidentale**, che è il modo in cui i segreti escono davvero. Un oggetto
    del genere può comparire in un `assert` fallito, in un `-vv`, in un `print` di
    disperazione alle undici di sera, e in nessuno di quei casi mostra il segreto.

    Resta un buco dichiarato: `credenziali.password` stampato a mano si vede. Non è
    chiudibile e non vale la pena di fingere il contrario — quello che si può fare è
    rendere difficile lo sbaglio, non impossibile il dolo.
    """

    utente: str
    password: str = field(repr=False)


@dataclass(frozen=True)
class Stack:
    """Uno dei tre stack del repository, come lo vedono le prove **dall'host**.

    `porta` è la porta pubblicata sull'host, non quella interna al container: dall'host
    ci si arriva su `localhost:porta`, dall'interno della rete Compose per nome di
    servizio. La seconda strada è quella dell'applicazione vera e arriva al Task 12
    ([ADR-0012](../../../docs/Decision.md#adr-0012)); qui siamo fuori dalla rete e la
    differenza ha una conseguenza misurata, scritta in `connetti`.
    """

    nome: str
    """Il nome della directory sotto `docker/`, che è anche quello che si legge nei log."""

    bersaglio: str
    """Il target del Makefile che lo accende: `up-01`, `up-02`, `up-03`."""

    porta: int
    diretto: bool
    """Se il client deve usare `directConnection=True`. Vedi `connetti`."""

    ambiente: str | None = None
    """Il file `.env` da cui leggere la credenziale, relativo alla radice. `None`: nessuna
    autenticazione, che è il caso dello stack 01."""


STACK: Final[Mapping[str, Stack]] = {
    "01": Stack(nome="01-standalone", bersaglio="up-01", porta=27017, diretto=True),
    "02": Stack(
        nome="02-replicaset",
        bersaglio="up-02",
        porta=27021,
        diretto=True,
        ambiente="docker/02-replicaset/.env",
    ),
    "03": Stack(
        nome="03-sharded",
        bersaglio="up-03",
        porta=27117,
        diretto=False,
        ambiente="docker/03-sharded/.env",
    ),
}
"""I tre stack, con le porte che i loro `compose.yaml` pubblicano.

Lo `03` è l'unico con `diretto=False`, e non è un'eccezione: è il caso normale. Un mongos
**è** il punto d'ingresso, quindi scoprire la topologia a partire da lui non porta il
client da nessun'altra parte, e la scoperta è precisamente ciò che si vuole misurare
quando l'ispettore chiede la distribuzione per shard.
"""


def radice() -> Path:
    """La radice del repository, cercando all'insù il `Makefile`.

    Non una costante calcolata da `__file__` con tre `.parent`: questo albero vive anche
    dentro `.claude/worktrees/`, e un conteggio di livelli sbagliato darebbe una directory
    che esiste, in cui `make` fallisce con un messaggio che non spiega niente.
    """
    for cartella in [Path(__file__).resolve(), *Path(__file__).resolve().parents]:
        if (cartella / "Makefile").is_file():
            return cartella
    raise RuntimeError(
        f"nessun Makefile risalendo da {__file__}: le prove di integrazione non sanno "
        "dove sta il repository."
    )


def credenziali_di(stack: Stack) -> Credenziali | None:
    """Legge utente e password dal `.env` dello stack, o `None` se non ne ha uno.

    Il `.env` non è nel repository ([ADR-0014](../../../docs/Decision.md#adr-0014)) e la
    sua casa è il checkout principale ([ADR-0056](../../../docs/Decision.md#adr-0056)); da
    un worktree ci si arriva con un collegamento, mai con una copia
    ([ADR-0083](../../../docs/Decision.md#adr-0083)). Qui non si sa niente di tutto questo:
    si legge un percorso, e se manca si dice quale comando lo crea.
    """
    if stack.ambiente is None:
        return None
    percorso = radice() / stack.ambiente
    if not percorso.is_file():
        raise RuntimeError(
            f"manca {stack.ambiente}: copia il .env.example accanto e riempilo, oppure "
            f"— se sei in un worktree — collegalo al checkout principale (ADR-0083)."
        )
    valori: dict[str, str] = {}
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if riga and not riga.startswith("#") and "=" in riga:
            chiave, _, valore = riga.partition("=")
            valori[chiave.strip()] = valore.strip()
    password = valori.get("PASSWORD_AMMINISTRATORE")
    if not password:
        raise RuntimeError(
            f"{stack.ambiente} non definisce PASSWORD_AMMINISTRATORE. "
            "Il valore non viene stampato qui e non deve comparire in nessun log."
        )
    return Credenziali(utente=valori.get("UTENTE_AMMINISTRATORE", "admin"), password=password)


def connetti(stack: Stack, attesa_ms: int = 20_000) -> MongoClient[dict[str, Any]]:
    """Un client verso lo stack, dall'host.

    Tre scelte, tutte misurate al Task 8.

    **`tz_aware=True`.** L'impostazione predefinita di pymongo è `False`, e con quella un
    `datetime` scritto consapevole del fuso torna indietro **ingenuo**. Nessuno solleva:
    il confronto fra due ingenui passa, e sbaglia di quante ore vale il fuso di chi
    presenta. Il dataset di demo ha un campo `data`, quindi il caso non è ipotetico
    (M-018).

    **La credenziale come argomenti, non nell'URI.** `username=`/`password=` invece di
    `mongodb://utente:segreto@host`: nell'URI il segreto entrerebbe in `repr(client)`, nei
    messaggi di errore e in qualunque log che stampi la stringa di connessione. Passata
    così è stata cercata e non trovata in nessuno dei tre (M-018).

    **`directConnection=True` sul 02, e la ragione è una trappola.** Con `replicaSet=rs0`
    da un host, pymongo scopre i membri **dalla configurazione del set**, che li nomina
    `mongo-rs-1:27017` e compagni ([ADR-0021](../../../docs/Decision.md#adr-0021)): nomi
    che esistono nella rete Compose e non sulla macchina di chi lancia le prove. Tutti e
    tre falliscono la risoluzione DNS, la selezione scade dopo quattro secondi, e la
    topologia si legge `ReplicaSetNoPrimary` — cioè **un replica set sanissimo, visto da
    fuori, è indistinguibile da uno che ha perso il primario** (M-019). Con
    `directConnection=True` la stessa istanza risponde in millisecondi e si presenta come
    `RSPrimary`: il *ruolo* è giusto, la *forma* si legge `SINGOLA`. È una riserva
    dichiarata, non un difetto nascosto, e la scoperta vera arriva al Task 12 quando
    l'applicazione girerà **dentro** la rete Compose.
    """
    credenziali = credenziali_di(stack)
    parametri: dict[str, Any] = {
        "tz_aware": True,
        "serverSelectionTimeoutMS": attesa_ms,
        "directConnection": stack.diretto,
    }
    if credenziali is not None:
        parametri["username"] = credenziali.utente
        parametri["password"] = credenziali.password
        parametri["authSource"] = "admin"
    return MongoClient(f"mongodb://localhost:{stack.porta}/", **parametri)


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
