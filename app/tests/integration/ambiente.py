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
from importlib.metadata import version
from dataclasses import dataclass
from typing import Any, Final, Iterator, Mapping
from uuid import uuid4
import os
import shlex
import subprocess
import threading

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from mongolab.infrastructure.bersagli import (
    BERSAGLI,
    Bersaglio,
    Credenziali,
    PuntoDiVista,
    radice,
)
from mongolab.infrastructure.bersagli import connetti as _connetti
from mongolab.infrastructure.bersagli import credenziali_di as _credenziali_di

__all__ = [
    "IMMAGINE",
    "PREFISSO_PROVE",
    "SESSIONE",
    "STACK",
    "Credenziali",
    "Scena",
    "Stack",
    "collezione_usa_e_getta",
    "comando_nel_container",
    "connetti",
    "credenziali_di",
    "immagine_in_cache",
    "nel_container",
    "nome_di_prova",
    "radice",
    "rimetti_in_piedi",
    "scena_nel_container",
    "sessione_viva",
    "sveglia",
]

PREFISSO_PROVE: Final = "mongolab_prove_"
"""Il prefisso di ogni database che queste prove creano.

Esiste perché la pulizia sia **riconoscibile**: se una prova viene interrotta a metà — un
Ctrl-C, un kill, un timeout di CI — il suo database resta sullo stack, e senza un prefisso
convenuto nessuno saprebbe distinguerlo da `lab`. Con il prefisso, la sessione successiva
lo trova e lo toglie, e nessuno tocca mai un database che non abbia questo nome.

Il prefisso da solo non basta, e il perché è misurato in
[M-063](../../docs/Sources.md#m-063): è **comune a tutte le sessioni**, quindi la spazzata
di chi parte adesso arrivava anche sui database di chi sta ancora lavorando. Il nome porta
per questo anche la sessione — vedi `SESSIONE` e `nome_di_prova`.
"""

SESSIONE: Final = str(os.getpid())
"""Chi ha creato un database di prova, scritto dentro il nome del database.

Il `pid` del processo `pytest`, e non un `uuid`, per una ragione sola: deve essere
**interrogabile**. Un identificatore casuale distingue le sessioni ma non dice se quella
che l'ha scritto esiste ancora, e la spazzata ha bisogno esattamente di quella risposta —
altrimenti può solo scegliere fra cancellare tutto (e portarsi via il lavoro di chi sta
girando) e non cancellare niente (e lasciare che gli orfani si accumulino). Un `pid` la
risposta ce l'ha, in una chiamata di sistema e senza registri da tenere.

**Il limite, dichiarato.** Vale finché le sessioni girano sulla stessa macchina degli
stack, che è il caso di questo laboratorio: gli stack sono Compose locale. Due macchine
diverse contro lo stesso MongoDB si scambierebbero `pid`, e l'errore possibile sarebbe in
tutte e due le direzioni. Con `pytest-xdist` invece funziona senza aggiunte, perché ogni
worker è un processo con il suo `pid`.
"""


def nome_di_prova(etichetta: str = "") -> str:
    """Il nome di un database di prova: prefisso, sessione, e ciò che la prova ci mette.

    Senza `etichetta` la coda è casuale, perché due prove della stessa sessione non si
    contino i documenti a vicenda. Con `etichetta`, il nome è stabile dentro la sessione e
    diverso fra sessioni — è ciò che serve alle fixture di modulo, che quel database lo
    vogliono ritrovare.
    """
    return f"{PREFISSO_PROVE}{SESSIONE}_{etichetta or uuid4().hex[:12]}"


def _sessione_di(nome: str) -> str | None:
    """La sessione firmata nel nome, oppure `None` se quel nome non ne porta una."""
    testa, _, coda = nome.removeprefix(PREFISSO_PROVE).partition("_")
    return testa if coda and testa.isdigit() else None


def sessione_viva(sessione: str) -> bool:
    """Il processo che ha firmato quel nome esiste ancora su questa macchina?

    `os.kill(pid, 0)` non manda niente: chiede al kernel se avrebbe qualcuno a cui
    mandarlo. `PermissionError` è un **sì** — il processo c'è e non è nostro.
    """
    try:
        os.kill(int(sessione), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


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
        """`directConnection` **dall'host**, che è da dove girano queste prove.

        Dal Task 12 lo stesso stack ha due indirizzi e due risposte a questa domanda: da
        dentro la rete Compose il replica set si raggiunge con la scoperta accesa. Le
        prove d'integrazione stanno fuori — `pytest` gira sul portatile, non in un
        container — quindi qui la vista è sempre quella dell'host.
        """
        return self.quale.vista(PuntoDiVista.HOST).diretto

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

    Il punto di vista si dichiara invece di lasciarlo leggere all'ambiente: se una sessione
    avesse esportato `MONGOLAB_PUNTO_DI_VISTA=rete` — cosa che capita provando i comandi
    del Task 12 — l'intera suite si metterebbe a cercare `mongo-rs-1`, che dall'host non
    esiste, e fallirebbe venti secondi per volta parlando d'altro.
    """
    return _connetti(stack.quale, attesa_ms=attesa_ms, punto=PuntoDiVista.HOST)


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


# --- L'applicazione dentro la rete (Task 12) -------------------------------------------

IMMAGINE: Final = f"mongolab:{version('mongolab')}"
"""Il tag che i file Compose chiedono, ricavato dalla versione del pacchetto installato.

Non è riscritto a mano: `tools/tests/test_coerenza_repo.py` verifica che i tre file
Compose scrivano esattamente `mongolab:` più la versione di `app/pyproject.toml`, quindi
leggere la versione qui e leggere il tag là danno la stessa stringa — con la differenza
che questa non invecchia.
"""


def immagine_in_cache() -> bool:
    """Se l'immagine dell'applicazione è già costruita su questa macchina.

    Le prove che eseguono nel container la chiedono e **saltano** se non c'è, invece di
    costruirla: `make app-image` vuole la rete la prima volta, e una suite di prove che si
    mette a scaricare Python è una suite che in sala non finisce. Chi deve accorgersene
    prima del talk è `tools/preflight.sh`, che infatti blocca.
    """
    esito = subprocess.run(
        ["docker", "image", "inspect", IMMAGINE],
        capture_output=True,
        text=True,
        check=False,
    )
    return esito.returncode == 0


def _compose(stack: Stack) -> list[str]:
    """`docker compose` con i suoi due `--env-file` e il file dello stack, e nulla altro.

    I due `--env-file` sono obbligatori tutti e due, e non è una comodità: i `compose.yaml`
    di questo repository interpolano con la forma `${MONGO_IMAGE:?...}`, che è un **errore**
    e non un valore vuoto. Senza nessuno dei due, `docker compose -f
    docker/02-replicaset/compose.yaml ps` risponde sette volte «required variable ... is
    missing a value»; con il solo `tools/images.env` ne restano due, per
    `PASSWORD_AMMINISTRATORE`.

    Nessun `-p`: il nome del progetto sta dentro i file (`name: sqlstart-02-replicaset`).
    """
    comando = ["docker", "compose", "--env-file", "tools/images.env"]
    if stack.ambiente is not None:
        comando += ["--env-file", stack.ambiente]
    return comando + ["-f", f"docker/{stack.nome}/compose.yaml"]


def comando_nel_container(
    stack: Stack,
    *argomenti: str,
    entrypoint: str | None = None,
    senza_tty: bool = False,
) -> list[str]:
    """La riga che avvia il servizio `app` di uno stack, come lista di argomenti.

    Separata da chi la esegue perché due prove la eseguono in due modi: `nel_container`
    aspetta la fine e legge tutto insieme, `scena_nel_container` legge riga per riga
    mentre la scena gira e risponde. La riga è la stessa, e deve restare la stessa.

    `senza_tty` aggiunge `-T`. Serve a chi parla con il processo attraverso delle pipe: con
    uno pseudo-terminale in mezzo Compose riscriverebbe i fine riga e l'eco, e chi legge si
    troverebbe il proprio Invio nel testo che sta analizzando.
    """
    comando = _compose(stack) + ["run", "--rm"]
    if senza_tty:
        comando.append("-T")
    if entrypoint is not None:
        comando += ["--entrypoint", entrypoint]
    return comando + ["app", *argomenti]


def nel_container(stack: Stack, *argomenti: str, entrypoint: str | None = None) -> str:
    """Esegue qualcosa nel servizio `app` dello stack, e restituisce ciò che ha scritto.

    Il comando si compone dai campi del bersaglio — la cartella dello stack e il suo
    `.env` — e non da una tabella scritta qui: sarebbe la quarta copia della stessa mappa,
    dopo `BERSAGLI`, il `Makefile` e i file Compose, e la prima a divergere.

    La credenziale non compare mai sulla riga di comando. Arriva al container perché
    `--env-file` la dà a **Compose**, che la interpola nel blocco `environment:` del
    servizio; il client `docker` non la vede passare come argomento, che è ciò che
    [ADR-0054](../../../docs/Decision.md#adr-0054) vieta.
    """
    esito = subprocess.run(
        comando_nel_container(stack, *argomenti, entrypoint=entrypoint),
        cwd=radice(),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if esito.returncode != 0:
        coda = "\n".join((esito.stdout + esito.stderr).splitlines()[-20:])
        raise RuntimeError(
            f"`docker compose run app` su {stack.nome} è uscito con "
            f"{esito.returncode}.\n{coda}"
        )
    return esito.stdout


@dataclass(frozen=True)
class Scena:
    """Che cosa resta di una scena girata nel container: ciò che ha scritto e ciò che ha
    chiesto di fare.

    I comandi sono tenuti a parte perché sono metà di quello che c'è da verificare. Una
    scena che stampa la cronaca giusta senza aver chiesto di uccidere nessuno non è una
    scena riuscita: è una simulazione, ed è esattamente la bugia che
    `RegiaAnnunciata` esiste per non dire.
    """

    uscita: str
    comandi: tuple[str, ...]

    @property
    def righe(self) -> list[str]:
        """Le righe stampate, senza i fine riga. È come le legge chi guarda."""
        return self.uscita.splitlines()


PROMPT_DI_REGIA: Final = "docker compose "
"""Da che cosa si riconosce una riga annunciata da `RegiaAnnunciata`.

Si riconosce dal contenuto e non da un marcatore, perché quella riga esiste per essere
**copiata**: qualunque cosa la rendesse riconoscibile e non incollabile — un prefisso, una
sigla, delle virgolette — la renderebbe inutile allo scopo per cui viene stampata.
"""


def _sull_host(riga: str) -> None:
    """Esegue verbatim, dalla radice del repository, la riga che la scena ha annunciato.

    `shlex.split` e nessuna shell. Nessuna shell perché la riga arriva da un altro
    processo, e passarla a una shell vorrebbe dire che un `$` capitato in un nome di
    servizio diventa una sostituzione. Verbatim perché è proprio questo che la prova
    verifica: se la riga annunciata non fosse eseguibile così com'è, stamparla non
    servirebbe a niente, e chi la copiasse dal proiettore se ne accorgerebbe in sala.
    """
    esito = subprocess.run(
        shlex.split(riga),
        cwd=radice(),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if esito.returncode != 0:
        coda = "\n".join((esito.stdout + esito.stderr).splitlines()[-10:])
        raise RuntimeError(
            f"il comando annunciato dalla scena è fallito con {esito.returncode}:\n"
            f"{riga}\n{coda}"
        )


def scena_nel_container(
    stack: Stack, *argomenti: str, scadenza_s: float = 300.0
) -> Scena:
    """Gira una scena nel container e **fa da umano**: esegue i comandi che annuncia.

    È l'unica disposizione che produce una cronaca dell'elezione vera. Dentro la rete
    Compose l'applicazione vede la topologia — e solo da lì la vede (M-019) — ma non ha il
    socket del demone e non può fermare nessuno; sull'host è il contrario. Questa funzione
    è il ponte fra le due metà, e in sala quel ponte è una persona con una seconda
    finestra aperta.

    Legge riga per riga e non alla fine: la conferma va data **mentre** la scena aspetta,
    e una `communicate()` aspetterebbe una fine che non arriva. Il figlio ha
    `PYTHONUNBUFFERED=1` dal proprio Dockerfile, quindi le righe arrivano quando vengono
    scritte e non a blocchi.

    La scadenza è un `Timer` che uccide, e non un `timeout=` su una lettura: una
    `readline` bloccata non scade, e una prova che resta appesa è peggio di una che
    fallisce, perché non lo dice a nessuno.
    """
    processo = subprocess.Popen(
        comando_nel_container(stack, *argomenti, senza_tty=True),
        cwd=radice(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    righe: list[str] = []
    comandi: list[str] = []
    with processo:
        allarme = threading.Timer(scadenza_s, processo.kill)
        allarme.start()
        try:
            canale, uscita = processo.stdin, processo.stdout
            assert canale is not None and uscita is not None  # sono `PIPE`, per mypy
            for riga in iter(uscita.readline, ""):
                righe.append(riga)
                annunciato = riga.strip()
                if not annunciato.startswith(PROMPT_DI_REGIA):
                    continue
                comandi.append(annunciato)
                _sull_host(annunciato)
                canale.write("\n")
                canale.flush()
            codice = processo.wait()
        finally:
            allarme.cancel()
            processo.kill()
    testo = "".join(righe)
    if codice != 0:
        perche = " (uccisa dalla scadenza)" if codice < 0 else ""
        raise RuntimeError(
            f"la scena su {stack.nome} è uscita con {codice}{perche}.\n{testo}"
        )
    return Scena(uscita=testo, comandi=tuple(comandi))


def rimetti_in_piedi(stack: Stack) -> None:
    """Riavvia e risveglia tutto ciò che una scena può aver lasciato fermo o congelato.

    Serve solo quando una prova **fallisce**: una scena che arriva in fondo rimette il
    nodo in servizio da sé, perché è una fase del copione. Ma se la prova muore a metà —
    una scadenza, un'asserzione, un Ctrl-C — il primario resta ucciso, e la prova
    successiva troverebbe un replica set a due membri senza avere modo di capire perché.

    Non contraddice la regola per cui le prove non spengono gli stack: qui non si spegne
    niente, si rimette in piedi ciò che questa prova ha buttato giù.

    `unpause` tollera l'errore perché non è idempotente — risvegliare un servizio che non
    dorme è un fallimento, e sarebbe il fallimento del caso normale.
    """
    for coda, scadenza in ((["unpause"], 60), (["start"], 120)):
        subprocess.run(
            _compose(stack) + coda,
            cwd=radice(),
            capture_output=True,
            text=True,
            timeout=scadenza,
            check=False,
        )


def spazza(client: MongoClient[dict[str, Any]]) -> int:
    """Toglie i database rimasti da una sessione **finita**. Restituisce quanti.

    Tocca solo ciò che comincia per `PREFISSO_PROVE`, e questa è la prima garanzia: uno
    strumento di pulizia che si sbaglia sul filtro cancella il lavoro di qualcun altro, e
    lo fa in silenzio perché è il suo mestiere cancellare.

    La seconda garanzia è arrivata dopo, da un rilievo della review misurato eseguendolo
    ([M-063](../../docs/Sources.md#m-063), [ADR-0136](../../../docs/Decision.md#adr-0136)).
    Il prefisso è comune a tutte le sessioni, e ogni sessione spazza appena parte: una
    seconda esecuzione sullo stesso stack cancellava i database usa-e-getta della prima
    **mentre li stava usando**, e la prima se ne accorgeva come di un conteggio che non
    torna. Il nome porta ora la sessione che l'ha creato, e qui si risparmia ciò che
    appartiene a una sessione ancora viva.

    I nomi che non portano una sessione — quelli scritti prima di questa regola — sono
    orfani per definizione e se ne vanno.

    **La propria sessione si risparmia come le altre**, e la prima stesura di questo
    rimedio faceva il contrario. L'argomento era che alla prima spazzata i propri database
    non esistono ancora, quindi uno firmato con il proprio `pid` non può che venire da un
    `pid` riciclato. L'argomento è vero e non serve: vale per un'assunzione sull'ordine in
    cui le fixture vengono create, che nessuno verifica e che il giorno in cui cambiasse
    non farebbe rumore. La prova scritta per fissare il rimedio l'ha bocciato subito. Un
    residuo da `pid` riciclato costa una corsa in più prima di sparire — se la prossima
    sessione ha un numero diverso, e ce l'ha quasi sempre — mentre l'assunzione costava un
    modo silenzioso di cancellare del lavoro vivo. L'invariante ora si dice in una riga:
    **`spazza` non tocca niente che appartenga a una sessione viva.**
    """
    tolti = 0
    for nome in client.list_database_names():
        if not nome.startswith(PREFISSO_PROVE):
            continue
        sessione = _sessione_di(nome)
        if sessione is not None and sessione_viva(sessione):
            continue
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
    accordarsi, e porta la sessione perché due esecuzioni sovrapposte non si contino i
    documenti a vicenda **e non si spazzino a vicenda** — la seconda metà della promessa
    mancava, ed è `nome_di_prova` a mantenerla.
    """
    nome = nome_di_prova()
    try:
        yield client[nome][collezione]
    finally:
        client.drop_database(nome)
