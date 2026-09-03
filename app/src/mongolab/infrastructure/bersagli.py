"""Dove stanno i tre stack, e come ci si arriva. La mappa `--target` → URI, in un posto solo.

Il §6.4 scrive `mongolab stats --target rs`: una parola sulla riga di comando, e dietro
quella parola una porta, una credenziale e una decisione su `directConnection`. Questo
modulo è l'unico posto del repository in cui quei tre fatti stanno scritti.

**Perché di produzione e non nelle prove.** Fino al Task 10 gli stessi numeri vivevano in
`tests/integration/ambiente.py`, che li aveva perché era l'unico codice che si collegasse
a qualcosa. Adesso c'è anche l'applicazione, e la scelta era fra copiarli — due copie che
divergono al primo cambio, e la seconda se ne accorge con un timeout di venti secondi che
parla d'altro — o spostarli qui e far derivare le prove. Il codice di produzione non può
importare quello di prova; il contrario sì. Quindi qui.

**La credenziale non entra nell'URI.** `Bersaglio.uri` è `mongodb://host:porta/` e basta.
Utente e password vanno a `MongoClient` come argomenti, dove pymongo non li lascia uscire
né in `repr(client)`, né in `ServerSelectionTimeoutError`, né in `OperationFailure`
([M-018](../../../docs/Sources.md#m-018)). Nell'URI ci finirebbero in tutti e tre.

**`directConnection` dipende da dove si guarda, e questo è il punto di vista dell'host.**
Con `replicaSet=rs0` da fuori della rete Compose, pymongo scopre i membri dalla
configurazione del set — `mongo-rs-1:27017` e compagni, nomi che l'host non risolve — e un
replica set sanissimo si legge `ReplicaSetNoPrimary`
([M-019](../../../docs/Sources.md#m-019)). Di qui `diretto=True` sul `rs`, al prezzo che la
*forma* della topologia si legge `SINGOLA` mentre il *ruolo* è `RSPrimary`. È una riserva
dichiarata e ha una scadenza: al Task 12 l'applicazione gira **dentro** la rete Compose e
la scoperta funziona ([ADR-0012](../../../docs/Decision.md#adr-0012)). Quel task cambierà
questa mappa, ed è il motivo per cui il valore sta in un campo e non in una costante
sparsa dentro `connetti`.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Final, Mapping

from pymongo import MongoClient

__all__ = [
    "BERSAGLI",
    "COLLEZIONE",
    "DATABASE",
    "PREFISSO_CARICO",
    "Bersaglio",
    "BersaglioSconosciuto",
    "Credenziali",
    "bersaglio_di",
    "collezione_di_carico",
    "connetti",
    "credenziali_di",
    "radice",
]

HOST: Final = "localhost"
"""Da dove guarda questa mappa. Al Task 12 sarà il nome di servizio Compose."""

DATABASE: Final = "lab"
COLLEZIONE: Final = "ordini"
"""`lab.ordini` è ciò che i tre `init/*-dati-demo.js` seminano: la stessa collezione su
tutti e tre gli stack, perché il confronto fra architetture del Task 16 abbia senso."""

PREFISSO_CARICO: Final = "carico-"
"""Da cosa comincia il nome della collezione in cui `workload` scrive.

Il carico **non** scrive in `ordini`, e non è una preferenza estetica: `DataGenerator`
numera i documenti da zero e il seed occupa già gli `_id` da 0 a 49 999, quindi ogni
scrittura tornerebbe indietro con un `E11000 duplicate key`. Misurato eseguendo, non
dedotto — la prima corsa contro lo stack 01 acceso ha risposto «38 scritture, 0
confermate», tutte per quel motivo.

Che dovesse andare altrove era già dichiarato: `generatore.py` scrive che «le due
popolazioni non si incontrano mai nella stessa collezione, perché il carico scrive nella
propria», e `tools/reset-demo.sh` tiene `const superstiti = ["ordini"]` — cioè in `lab`
ogni altra collezione è residuo, e viene tolta. Il posto c'era; a sbagliare era il
cablaggio.
"""


def collezione_di_carico(istante: datetime) -> str:
    """Il nome della collezione per **questa** corsa: `carico-20260918-103000`.

    Il nome cambia a ogni corsa perché altrimenti funzionerebbe una volta sola. Gli `_id`
    ripartono da zero a ogni esecuzione — è ciò che rende il dataset una funzione pura di
    `(seme, indice)`, vedi `generatore.py` — quindi una seconda corsa sulla stessa
    collezione ritroverebbe i propri documenti e fallirebbe come falliva contro `ordini`.
    In sala il carico si lancia più di una volta.

    L'istante si legge **così com'è**, senza convertirlo a UTC: chi cerca la propria
    collezione fra tre avanzi guarda l'orologio della sala, e `SystemClock` gliene dà uno
    che parla del fuso locale. Gli avanzi non si accumulano oltre la giornata — è
    `reset-demo` a spazzarli, tutti insieme.
    """
    return f"{PREFISSO_CARICO}{istante:%Y%m%d-%H%M%S}"


ATTESA_SELEZIONE_MS: Final = 20_000
"""Quanto pymongo aspetta un server prima di arrendersi.

Venti secondi e non i trenta predefiniti: durante un failover la selezione **deve**
scadere prima che la pazienza di `TopologyWatcher` finisca, altrimenti la cronaca mostra
un silenzio invece di mostrare i tentativi, ed è proprio quella la scena.
"""


class BersaglioSconosciuto(ValueError):
    """Il nome dopo `--target` non è uno dei tre.

    Sottoclasse di `ValueError` perché chi legge gli argomenti cattura già quello: la CLI
    non deve conoscere un tipo del progetto per tradurre l'errore in un codice d'uscita.
    """


@dataclass(frozen=True)
class Credenziali:
    """Utente e password, con la password fuori dal `repr`.

    `field(repr=False)` non è offuscamento e non protegge da chi legge il codice: protegge
    dalla **stampa accidentale**, che è il modo in cui i segreti escono davvero. Un oggetto
    del genere può comparire in un `assert` fallito, in un traceback, in un `print` di
    disperazione — e in nessuno di quei casi mostra il segreto.
    """

    utente: str
    password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class Bersaglio:
    """Uno stack, come lo raggiunge chi scrive `--target <nome>`."""

    nome: str
    """La parola sulla riga di comando: `standalone`, `rs`, `sharded`."""

    stack: str
    """La directory sotto `docker/`, che è anche il nome che si legge nei log."""

    porta: int
    """La porta che il `compose.yaml` pubblica sull'host, nella sua forma predefinita.

    Predefinita e non assoluta: i file Compose la scrivono `${PORTA_...:-27021}`, quindi
    un operatore può spostarla con una variabile d'ambiente e questa mappa non lo saprebbe.
    Non è un problema oggi — nessuno lo fa, e `tools/preflight.sh` riserva gli intervalli
    predefiniti — ed è una riga aperta dichiarata. La guardia contro la deriva è una prova
    che rilegge il `compose.yaml` e confronta.
    """

    diretto: bool
    """`directConnection`. Vedi la docstring del modulo: dipende dal punto di vista."""

    ambiente: str | None = None
    """Il `.env` da cui leggere la credenziale, relativo alla radice. `None`: nessuna
    autenticazione, che è il caso del solo stack 01."""

    @property
    def uri(self) -> str:
        """`mongodb://host:porta/`. Senza credenziali, e non è una dimenticanza."""
        return f"mongodb://{HOST}:{self.porta}/"


BERSAGLI: Final[Mapping[str, Bersaglio]] = {
    "standalone": Bersaglio(
        nome="standalone", stack="01-standalone", porta=27017, diretto=True
    ),
    "rs": Bersaglio(
        nome="rs",
        stack="02-replicaset",
        porta=27021,
        diretto=True,
        ambiente="docker/02-replicaset/.env",
    ),
    "sharded": Bersaglio(
        nome="sharded",
        stack="03-sharded",
        porta=27117,
        diretto=False,
        ambiente="docker/03-sharded/.env",
    ),
}
"""I tre nomi che `--target` accetta.

`rs` e `sharded` vengono dal §6.4 alla lettera. Per lo standalone il design non dà un
nome, e `standalone` è quello che il repository usa già dappertutto — nella directory,
nel target del Makefile, nel titolo della pagina di architettura. Un quarto sinonimo
sarebbe stato una cosa in più da ricordare la sera del talk.
"""


def bersaglio_di(nome: str) -> Bersaglio:
    """Il bersaglio di quel nome, o un errore che elenca quelli che esistono.

    L'elenco nel messaggio non è cortesia: chi sbaglia `--target` sta quasi sempre
    scrivendo il nome della *directory* (`02-replicaset`) o quello del *set* (`rs0`), e
    senza i tre nomi veri sotto gli occhi va a cercarli nel sorgente.
    """
    try:
        return BERSAGLI[nome]
    except KeyError:
        disponibili = ", ".join(sorted(BERSAGLI))
        raise BersaglioSconosciuto(
            f"«{nome}» non è uno stack di questo repository. I bersagli sono: {disponibili}."
        ) from None


def radice() -> Path:
    """La radice del repository, cercando all'insù il `Makefile`.

    Non una costante calcolata da `__file__` con quattro `.parent`: questo albero vive
    anche dentro `.claude/worktrees/`, e un conteggio di livelli sbagliato darebbe una
    directory che esiste, in cui non c'è niente di ciò che si cerca.
    """
    for cartella in [Path(__file__).resolve(), *Path(__file__).resolve().parents]:
        if (cartella / "Makefile").is_file():
            return cartella
    raise RuntimeError(
        f"nessun Makefile risalendo da {__file__}: `mongolab` non sa dove sta il "
        "repository, e senza repository non sa dove sono i suoi stack."
    )


def credenziali_di(bersaglio: Bersaglio, base: Path | None = None) -> Credenziali | None:
    """Legge utente e password dal `.env` dello stack, o `None` se non ne ha uno.

    Il `.env` non è nel repository ([ADR-0014](../../../docs/Decision.md#adr-0014)) e la
    sua casa è il checkout principale ([ADR-0056](../../../docs/Decision.md#adr-0056)); da
    un worktree ci si arriva con un collegamento, mai con una copia
    ([ADR-0083](../../../docs/Decision.md#adr-0083)). Qui non si sa niente di tutto
    questo: si legge un percorso, e se manca si dice quale comando lo rimedia.

    `base` esiste per le prove, che non possono dipendere da un file fuori dal
    repository: senza, ogni clone appena fatto avrebbe due prove rosse per una ragione
    che non riguarda il codice.
    """
    if bersaglio.ambiente is None:
        return None
    percorso = (base if base is not None else radice()) / bersaglio.ambiente
    if not percorso.is_file():
        raise RuntimeError(
            f"manca {bersaglio.ambiente}: copia il .env.example accanto e riempilo, "
            f"oppure — se sei in un worktree — collegalo al checkout principale (ADR-0083)."
        )
    valori: dict[str, str] = {}
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if riga and not riga.startswith("#") and "=" in riga:
            chiave, _, valore = riga.partition("=")
            valori[chiave.strip()] = valore.strip()
    password = valori.get("PASSWORD_AMMINISTRATORE")
    if not password:
        # Il messaggio nomina la chiave che manca e **non** stampa il file: un `.env` letto
        # male e riversato in un errore è il modo più stupido di perdere un segreto.
        raise RuntimeError(
            f"{bersaglio.ambiente} non definisce PASSWORD_AMMINISTRATORE. "
            "Il valore non viene stampato qui e non deve comparire in nessun log."
        )
    return Credenziali(
        utente=valori.get("UTENTE_AMMINISTRATORE", "admin"), password=password
    )


def connetti(
    bersaglio: Bersaglio,
    *,
    attesa_ms: int = ATTESA_SELEZIONE_MS,
    base: Path | None = None,
    **extra: Any,
) -> MongoClient[dict[str, Any]]:
    """Il `MongoClient` verso quello stack. È l'unico posto che lo costruisce.

    **`tz_aware=True`.** L'impostazione predefinita di pymongo è `False`, e con quella un
    `datetime` scritto consapevole del fuso torna indietro **ingenuo**. Nessuno solleva: il
    confronto fra due ingenui passa, e sbaglia di quante ore vale il fuso di chi presenta.
    Il dataset di demo ha un campo `data`, quindi il caso non è ipotetico
    ([M-018](../../../docs/Sources.md#m-018)) — e `PymongoStore` rifiuta di costruirsi
    senza, il che rende questa riga difficile da perdere per sbaglio.

    `extra` esiste per il Task 16, che dovrà accendere e spegnere `retryWrites` e
    `maxPoolSize` sulla stessa mappa senza scriverne una seconda.
    """
    credenziali = credenziali_di(bersaglio, base=base)
    parametri: dict[str, Any] = {
        "tz_aware": True,
        "serverSelectionTimeoutMS": attesa_ms,
        "directConnection": bersaglio.diretto,
        **extra,
    }
    if credenziali is not None:
        parametri["username"] = credenziali.utente
        parametri["password"] = credenziali.password
        parametri["authSource"] = "admin"
    return MongoClient(bersaglio.uri, **parametri)
