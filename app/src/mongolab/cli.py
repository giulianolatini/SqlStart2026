"""Il composition root: l'unico punto che conosce le classi concrete.

Tutto il resto di questa applicazione riceve **porte** — `DocumentStore`,
`ClusterInspector`, `BackupTool`, `EventSink`, `Clock` — e non ha modo di sapere chi le
implementa. Qui invece si sa, e si sa apposta: questo file costruisce `PymongoStore`,
`PymongoInspector`, `SdamBridge`, `SystemClock`, `RichTui`, e li inietta. È il §6.1 del
design preso alla lettera, ed è anche il motivo per cui una prova può sostituire
qualunque pezzo senza toccare una riga di `application/`.

La regola ha una guardia eseguibile in `tests/unit/test_scheletro.py`: `pymongo` si
importa **solo** sotto `infrastructure/`. Vale anche per questo file, che pure è il
punto in cui i client vengono creati — li crea chiamando `bersagli.connetti`, che è
l'unico posto del repository in cui `MongoClient(...)` compare davvero. Se un `import
pymongo` spuntasse qui, l'applicazione funzionerebbe lo stesso: è un difetto comunque, e
la guardia lo dice.

## Le opzioni, e i loro predefiniti

Le opzioni sono quelle del design, con i suoi stessi valori come predefiniti —
`mongolab workload --target rs` esegue esattamente la corsa che il §6.4 scrive per
esteso, perché due righe di comando che fanno cose diverse con lo stesso nome sono il
modo più rapido di perdere il filo dal palco.

**`--sink` c'è su `watch` e `workload` e non su `stats`**, ed è una scelta dichiarata:
`stats` è una fotografia e non emette nessun evento, quindi un `--sink` lì sarebbe
un'opzione accettata e inerte. Un'opzione inerte è una bugia che la riga di comando
racconta a chi la legge, e questo repository si è impegnato a non scriverne.

## Che cosa qui non c'è più, e dove è andato

`watch` aveva un ciclo suo — drena il ponte SDAM, aspetta, ricomincia — ed era
orchestrazione dentro la radice di composizione, cioè un po' più di quanto il §6.1 le
assegni. Al Task 13 è diventato `scenari.sorveglia`, dove la regola delle attese — fra
uno sguardo e l'altro, mai dopo l'ultimo — ha finalmente delle prove: qui dentro era
verificabile solo eseguendo il comando, cioè aprendo una connessione.

Sempre in `watch`, `TopologyWatcher` **non** c'è, e la sua assenza è deliberata: quando
c'era, ogni transizione finiva in cronaca due volte, perché lui e il ponte guardano la
stessa struttura da due lati. Il §6.3 assegna la cronaca al ponte; l'interruzione, che è
l'altra cosa che la sentinella sa fare, si misura accanto alle scritture perse — ed è
`CronometroInterruzione`, dentro la scena del failover.

## I quattro comandi, e le opzioni che hanno davvero

Il §6.4 elenca sette righe di comando. Tre sono dirette; le quattro `demo` sono un
gruppo, e la prima scena — `demo failover` — è di questo file dal Task 13. Le altre tre
arrivano ai Task 14 e 15.

Quella scena porta con sé l'unico pezzo di cablaggio che non riguarda MongoDB: **chi
provoca il guasto**. Arriva dalla porta `Regia` e ha due adattatori, e a sceglierne uno è
lo stesso `MONGOLAB_PUNTO_DI_VISTA` che sceglie come si raggiunge lo stack. Non è una
coincidenza: dall'host il socket del demone Docker c'è e la scoperta della topologia no,
dalla rete è l'opposto, e un processo solo non può fare tutte e due le cose.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
import sys
from typing import Annotated, Callable, Final

import typer

from mongolab.application.scenari import (
    DURATA_CARICO_S,
    DURATA_ELEZIONE_S,
    DURATA_RECUPERO_S,
    Attesa,
    Copione,
    ModoGuasto,
    ScenarioFailover,
    senza_attesa,
    sorveglia,
)
from mongolab.application.topologia import INTERVALLO_PREDEFINITO_MS
from mongolab.application.workload import WorkloadRunner
from mongolab.domain.eventi import FaseIniziata
from mongolab.domain.modelli import DescrizioneTopologia
from mongolab.domain.porte import Clock, EventSink, Regia
from mongolab.infrastructure.bersagli import (
    ATTESA_SELEZIONE_MS,
    COLLEZIONE,
    DATABASE,
    Bersaglio,
    BersaglioSconosciuto,
    PuntoDiVista,
    SenzaPrimario,
    attendi_il_primario,
    bersaglio_di,
    collezione_di_carico,
    connetti,
    punto_di_vista,
    radice,
)
from mongolab.infrastructure.generatore import DataGenerator
from mongolab.infrastructure.inspector import PymongoInspector
from mongolab.infrastructure.orologio import SystemClock
from mongolab.infrastructure.sdam import SdamBridge
from mongolab.infrastructure.store import PymongoStore
from mongolab.infrastructure.zavorra import byte_di, con_dimensione
from mongolab.presentation.null import NullSink
from mongolab.presentation.plain import PlainSink
from mongolab.infrastructure.regia import (
    ComandiCompose,
    RegiaAnnunciata,
    RegiaCompose,
)
from mongolab.presentation.rapporto import cronaca, rapporto, riassunto
from mongolab.presentation.rich_tui import RichTui

__all__ = [
    "DIMENSIONE_PREDEFINITA",
    "DURATA_WATCH_S",
    "DURATA_WORKLOAD_S",
    "IMMAGINI",
    "niente_da_fermare",
    "LETTORI_PREDEFINITI",
    "SCRITTORI_PREDEFINITI",
    "Cablaggio",
    "Resa",
    "app",
    "cabla",
    "comandi_di",
    "demo",
    "giri_di",
    "mentre_disegna",
    "nodo_di",
    "regia_di",
    "servizi_di",
    "sink_di",
]

SCRITTORI_PREDEFINITI: Final = 8
LETTORI_PREDEFINITI: Final = 4
DIMENSIONE_PREDEFINITA: Final = "2k"
DURATA_WORKLOAD_S: Final = 120.0
"""I quattro valori della riga del §6.4, che qui diventano i predefiniti.

`mongolab workload --target rs` e la riga lunga del design sono lo stesso comando. È una
proprietà che vale la pena tenere: il Task 16 misurerà quella corsa, una slide la
mostrerà, e chi la digita dal palco scriverà la forma corta.
"""

DURATA_WATCH_S: Final = 120.0
"""Per quanto `watch` sta a guardare, se non gli si dice altro.

Il §6.4 scrive `mongolab watch --target rs` e basta, senza durata: un allargamento, e
dichiarato. La ragione è che `TopologyWatcher.segui` **pretende** un numero di giri e
rifiuta il ciclo infinito, con una motivazione che vale anche fuori dalle prove — un
ciclo che aspetta un fatto che non arriva non fallisce, si pianta. Servendo un numero,
tanto vale che arrivi da qualcosa che si legge: due minuti, gli stessi di `workload`,
che è quanto dura la scena del failover con tutto il suo contorno.
"""


IMMAGINI: Final = Path("tools/images.env")
"""Il file che fissa le immagini, relativo alla radice del repository.

`docker compose` di questo repository non parte senza: i `compose.yaml` interpolano con
la forma `${MONGO_IMAGE:?...}`, che davanti a una variabile assente è un errore e non un
valore vuoto. È lo stesso file che le variabili `COMPOSE_0X` del Makefile passano, ed è
la ragione per cui una riga annunciata dall'applicazione si può incollare in un terminale
e funziona identica.
"""

class Resa(str, Enum):
    """Come esce ciò che la corsa racconta. È il gancio del Task 18.

    Tre valori e non un booleano `--no-tui`: le registrazioni di riserva si producono
    con `--sink plain` dentro `tools/registra-terminale.py`, e le misure del Task 16 con
    `--sink null`, dove il costo del disegno non deve entrare nei numeri. Tre casi
    diversi, tre nomi.

    Eredita da `str` perché è così che Typer sa mostrarli come scelte nell'aiuto e
    rifiutare il quarto nome senza che nessuno scriva la validazione.
    """

    RICH = "rich"
    PLAIN = "plain"
    NULL = "null"


@dataclass(frozen=True, slots=True)
class Cablaggio:
    """Che cosa una corsa ha in mano prima di partire: il bersaglio, l'orologio, il sink.

    Esiste perché il cablaggio sia **osservabile**. Le stesse tre righe scritte dentro
    ciascun comando funzionerebbero identiche, e per verificarle servirebbe eseguire il
    comando, cioè aprire una connessione: la prova del composition root diventerebbe una
    prova d'integrazione, e le prove d'integrazione non si eseguono a ogni salvataggio.
    Qui invece `cabla("rs", Resa.PLAIN)` risponde offline.
    """

    bersaglio: Bersaglio
    orologio: Clock
    sink: EventSink


def sink_di(resa: Resa, orologio: Clock) -> EventSink:
    """L'unico posto che traduce `--sink` in una classe.

    `if resa is ...` in tre punti diversi del file sarebbe la stessa cosa scritta tre
    volte, e la terza divergerebbe: è il difetto che il Passo 3 del piano chiama
    «condizione sparsa».
    """
    if resa is Resa.RICH:
        return RichTui(orologio)
    if resa is Resa.PLAIN:
        return PlainSink(sys.stdout)
    return NullSink()


def cabla(target: str, resa: Resa) -> Cablaggio:
    """Risolve il bersaglio, costruisce l'orologio, sceglie il sink. Non apre niente.

    Che non apra niente è la proprietà che rende provabile il resto: il `MongoClient`
    nasce nel corpo del comando, dentro un `try`/`finally` che lo chiude, perché una
    connessione aperta e mai chiusa lascia il thread del monitor a battere anche dopo che
    la scena è finita.
    """
    bersaglio = bersaglio_di(target)
    orologio = SystemClock()
    return Cablaggio(bersaglio=bersaglio, orologio=orologio, sink=sink_di(resa, orologio))


def mentre_disegna[T](sink: EventSink, lavoro: Callable[[], T]) -> T:
    """Esegue il lavoro, e se il sink è la TUI lo fa disegnare dal thread che chiama.

    È ADR-0019 nella sua forma eseguibile: **un solo thread tocca il `Live` di Rich**, e
    quel thread è questo. Il lavoro va su un thread del pool ed emette nella coda di
    `Scena`, che è fatta per essere riempita da chiunque; il ciclo di disegno resta qui e
    la drena.

    Con gli altri due sink non c'è niente da disegnare e non serve nessun thread: il
    lavoro gira dove è stato chiamato. Un pool creato comunque «per uniformità»
    aggiungerebbe un thread a una misura di throughput che dovrebbe misurare MongoDB.

    `futuro.result()` alla fine non è per il valore soltanto: è ciò che fa **risollevare**
    un'eccezione del lavoro. Senza, una corsa caduta chiuderebbe la TUI in silenzio, con
    l'errore sepolto dentro un `Future` che nessuno interroga.
    """
    if not isinstance(sink, RichTui):
        return lavoro()
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="mongolab-lavoro") as pool:
        futuro = pool.submit(lavoro)
        sink.esegui(lambda: not futuro.done())
        return futuro.result()


def giri_di(durata_s: float, *, intervallo_ms: float = INTERVALLO_PREDEFINITO_MS) -> int:
    """Quante volte guardare, per stare a guardare `durata_s` secondi.

    Arrotonda per eccesso e non scende mai sotto uno: `--duration 0.1` deve dare uno
    sguardo, non zero. Zero finirebbe in `segui(0)`, che solleva — un comando che si
    rifiuta di guardare invece di guardare una volta.
    """
    if durata_s <= 0:
        raise ValueError(f"la durata è un tempo positivo, ricevuti {durata_s} secondi")
    return max(1, math.ceil(durata_s * 1000.0 / intervallo_ms))


# --- Che cosa serve alla scena del failover, e da dove viene -----------------------------


def servizi_di(bersaglio: Bersaglio) -> tuple[str, ...]:
    """I nomi dei servizi Compose dello stack, presi dalla vista di rete.

    Ci sono già, e stanno nei semi con cui il client cerca i nodi da dentro la rete: sono
    i nomi che il `compose.yaml` dà ai servizi, che è esattamente ciò che `docker compose
    kill` vuole sentirsi dire. Una seconda mappa «stack → servizi» accanto a `BERSAGLI`
    sarebbe la stessa informazione scritta due volte, e la seconda divergerebbe al primo
    nodo aggiunto.
    """
    return tuple(nome for nome, _ in bersaglio.da_rete.semi)


def comandi_di(bersaglio: Bersaglio) -> ComandiCompose:
    """Il frasario di `docker compose` per quello stack, con i suoi env-file.

    Il `.env` dello stack entra solo se lo stack autentica: `Bersaglio.ambiente` è `None`
    per il 01, e un `--env-file` verso un file che non esiste fermerebbe `docker compose`
    prima ancora che guardi i container, per una credenziale di cui non c'è bisogno.

    Nessun `-p`: i `compose.yaml` di questo repository dichiarano `name:` al loro interno
    (`sqlstart-02-replicaset`), quindi il progetto arriva dal file e non dalla directory
    da cui si lancia il comando. Passarlo anche qui vorrebbe dire tenere allineati due
    posti che dicono la stessa cosa.

    **I percorsi sono relativi alla radice**, ed è la correzione di un difetto vero: la
    prima versione li componeva con `radice()`, e dentro il container la riga annunciata
    diceva `/lab/docker/02-replicaset/compose.yaml` — un percorso che sull'host, dove
    quella riga va incollata, non esiste. Relativi, la riga è la stessa in tutti e due i
    posti; chi la esegue parte dalla radice, chi la annuncia lo dice.
    """
    ambiente = [IMMAGINI]
    if bersaglio.ambiente is not None:
        ambiente.append(Path(bersaglio.ambiente))
    return ComandiCompose(
        file_compose=Path("docker") / bersaglio.stack / "compose.yaml",
        ambiente=tuple(ambiente),
    )


def regia_di(bersaglio: Bersaglio, punto: PuntoDiVista) -> Regia:
    """Chi provoca il guasto: chi comanda dall'host, chi annuncia dalla rete.

    È lo stesso punto di vista che sceglie la vista del client, e non è un caso: sono le
    due metà di un problema che nessun processo solo può tenere insieme. Dall'host il
    socket del demone c'è e la scoperta della topologia no; dalla rete è l'opposto, e il
    container dell'applicazione non ha il socket perché il Task 9 ha deciso di non
    montarglielo. Sceglierli nello stesso posto è ciò che impedisce alle due decisioni di
    finire in disaccordo — un'applicazione che annuncia il comando e poi lo esegue anche
    lei fermerebbe il nodo due volte.

    """
    comandi = comandi_di(bersaglio)
    if punto is PuntoDiVista.HOST:
        return RegiaCompose(comandi, dove=radice())
    return RegiaAnnunciata(comandi, annuncia=_da_un_altra_finestra, conferma=_gia_fatto)


def _da_un_altra_finestra(riga: str) -> None:
    typer.echo(f"\n▸ da un'altra finestra, nella radice del repository:\n\n  {riga}\n")


def _gia_fatto(riga: str) -> None:
    """Blocca finché qualcuno non conferma di aver dato il comando.

    `input()` e non `typer.confirm`: la domanda non è «sei sicuro», è «l'hai fatto». Un
    «no» non avrebbe una strada alternativa da prendere — la scena senza guasto non è una
    scena più corta, è un failover perfetto raccontato senza failover — e una domanda a
    cui una sola risposta è utile si fa con un Invio.
    """
    input("   Invio quando è stato eseguito ")


def niente_da_fermare(bersaglio: Bersaglio) -> typer.BadParameter:
    """L'errore di quando il primario non si è fatto vedere entro l'attesa di selezione.

    Restituisce l'eccezione invece di sollevarla, e non è un vezzo: così il messaggio —
    che è la parte che finisce davanti al pubblico — si prova senza dover mettere in piedi
    un replica set malato.

    Sta qui e non accanto ad `attendi_il_primario` perché `typer` è di questo strato:
    l'infrastruttura solleva `SenzaPrimario`, che è un fatto, e la riga di comando decide
    come dirlo a chi sta guardando.
    """
    return typer.BadParameter(
        f"nessun primario su «{bersaglio.nome}» entro "
        f"{ATTESA_SELEZIONE_MS / 1000:.0f} s di attesa di selezione. Senza primario non "
        "c'è un nodo da fermare, e quindi non c'è nemmeno un failover da mostrare: lo "
        f"stack va acceso e sano prima della scena (`make up-{bersaglio.stack[:2]}`).",
        param_hint="--target",
    )


def nodo_di(vista: DescrizioneTopologia, bersaglio: Bersaglio) -> str:
    """Quale servizio fermare, dedotto dal primario che il driver sta vedendo.

    Il primario cambia a ogni prova, e una riga di comando che lo nomina a mano è una
    riga che dal palco si digita sbagliata: `mongo-rs-1` fermato quando il primario era
    `mongo-rs-3` toglie un secondario e non produce nessuna elezione — cioè cinque minuti
    di Atto II in cui non succede niente.

    L'indirizzo si riduce alla parte prima dei due punti e deve essere un servizio dello
    stack. Dall'host non lo è: il bersaglio `rs` si raggiunge con `directConnection` su
    una porta pubblicata, il primario si chiama `localhost`, e `docker compose kill
    localhost` fallirebbe con «no such service» dopo che il carico è già partito. È la
    faccia visibile di M-019, e qui si dichiara prima invece di scoprirla dopo.
    """
    primario = vista.primario
    if primario is None:
        raise typer.BadParameter(
            f"nessun primario in vista su «{bersaglio.nome}»: non c'è un nodo da fermare, "
            "e senza primario non c'è nemmeno un failover da mostrare."
        )
    nome = primario.indirizzo.rsplit(":", 1)[0]
    servizi = servizi_di(bersaglio)
    if nome not in servizi:
        raise typer.BadParameter(
            f"il primario si presenta come «{primario.indirizzo}», che non è un servizio "
            f"di docker/{bersaglio.stack}. I servizi sono: {', '.join(servizi)}. "
            "Da fuori la rete Docker i nomi del replica set non si risolvono: la scena si "
            "gira da dentro (`make app-demo`), oppure si nomina il servizio con --node."
        )
    return nome

# --- Le opzioni, e i loro controlli ------------------------------------------------------


def _controlla_bersaglio(nome: str) -> str:
    """Traduce `BersaglioSconosciuto` in un errore d'uso, prima che il comando parta.

    Un `callback` di Typer e non un `try` nel corpo: così il controllo avviene mentre si
    leggono gli argomenti, il codice d'uscita è il 2 che ogni strumento a riga di comando
    usa per «hai scritto male», e soprattutto non si è ancora aperta nessuna connessione.

    Il nome torna com'è invece di diventare un `Bersaglio`: Typer deduce il tipo del
    parametro dall'annotazione, e un tipo del progetto lì dentro non saprebbe convertirlo.
    La seconda risoluzione nel corpo è una lettura da un dizionario, ed è il prezzo per
    non avere una seconda mappa da tenere allineata alla prima — che è ciò che il Passo 2
    del piano chiede.
    """
    try:
        bersaglio_di(nome)
    except BersaglioSconosciuto as errore:
        raise typer.BadParameter(str(errore)) from errore
    return nome


def _controlla_dimensione(testo: str) -> str:
    """Come sopra, per `--doc-size`: `byte_di` sa già dire perché `2gb` non si scrive."""
    try:
        byte_di(testo)
    except ValueError as errore:
        raise typer.BadParameter(str(errore)) from errore
    return testo


Bersaglio_ = Annotated[
    str,
    typer.Option(
        "--target",
        help="Quale stack: standalone, rs, sharded.",
        callback=_controlla_bersaglio,
    ),
]
"""`--target` è obbligatorio ovunque, e non ha un valore predefinito.

Durante il talk si passa da uno stack all'altro tre volte. Un predefinito silenzioso
vorrebbe dire collegarsi a quello sbagliato senza accorgersene, davanti alla sala, e
scoprirlo da una topologia che non torna.
"""

Resa_ = Annotated[
    Resa, typer.Option("--sink", help="Dove va la cronaca: rich, plain, null.")
]

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Tre architetture MongoDB, viste da un client.",
)


# --- I tre comandi diretti del §6.4 -------------------------------------------------------


@app.command()
def stats(target: Bersaglio_) -> None:
    """Una fotografia dello stack: topologia, server, database, distribuzione."""
    bersaglio = bersaglio_di(target)
    cliente = connetti(bersaglio)
    try:
        ispettore = PymongoInspector(cliente, DATABASE, COLLEZIONE)
        typer.echo(
            rapporto(ispettore, titolo=f"{bersaglio.nome} (docker/{bersaglio.stack})")
        )
    finally:
        cliente.close()


@app.command()
def watch(
    target: Bersaglio_,
    sink: Resa_ = Resa.RICH,
    duration: Annotated[
        float, typer.Option("--duration", help="Per quanti secondi stare a guardare.")
    ] = DURATA_WATCH_S,
) -> None:
    """Guarda la topologia cambiare, e racconta ogni cambiamento.

    **Il narratore è uno solo, ed è il ponte.** La prima versione di questo comando ne
    aveva due — il ponte, che traduce i callback del driver, e `TopologyWatcher`, che
    interroga la descrizione ogni mezzo secondo — e contro lo stack 01 stampava ogni
    transizione due volte, a mezzo secondo di distanza. Vedono la stessa struttura, uno
    spinto e uno tirato: era garantito che si ripetessero.

    A scegliere è il §6.3 del design, che assegna al ponte «la cronaca a schermo del
    failover con timestamp al millisecondo». Sono anche gli istanti migliori: segnano
    quando il driver ha saputo, non quando qualcuno è passato a chiedere.

    `TopologyWatcher` non è sparito dal progetto: misura l'**interruzione**, e quella
    misura vale accanto alle scritture perse — cioè nello scenario di failover del Task
    13. Qui, dove non si scrive niente, avrebbe soltanto raccontato una seconda volta.
    """
    cablaggio = cabla(target, sink)
    ponte = SdamBridge(cablaggio.orologio)
    cliente = connetti(cablaggio.bersaglio, event_listeners=ponte.ascoltatori)
    try:
        giri = giri_di(duration)
        mentre_disegna(
            cablaggio.sink,
            lambda: sorveglia(
                ponte.drena, cablaggio.sink, cablaggio.orologio, giri=giri
            ),
        )
    finally:
        cliente.close()


@app.command()
def workload(
    target: Bersaglio_,
    writers: Annotated[
        int, typer.Option("--writers", help="Quanti thread scrivono.")
    ] = SCRITTORI_PREDEFINITI,
    readers: Annotated[
        int, typer.Option("--readers", help="Quanti thread leggono.")
    ] = LETTORI_PREDEFINITI,
    doc_size: Annotated[
        str,
        typer.Option(
            "--doc-size",
            help="Dimensione di un documento: 512, 2k, 1m.",
            callback=_controlla_dimensione,
        ),
    ] = DIMENSIONE_PREDEFINITA,
    duration: Annotated[
        float, typer.Option("--duration", help="Per quanti secondi far girare il carico.")
    ] = DURATA_WORKLOAD_S,
    sink: Resa_ = Resa.RICH,
) -> None:
    """Manda carico contro lo stack, e alla fine dice come è andata."""
    cablaggio = cabla(target, sink)
    genera = con_dimensione(DataGenerator().documento, byte_di(doc_size))
    # **Non `COLLEZIONE`**: il carico ha la propria, e il nome cambia a ogni corsa. Il
    # perché sta in `bersagli.collezione_di_carico`, ed è un E11000 misurato, non una
    # precauzione. Che la scelta si faccia qui e non dentro `WorkloadRunner` è la regola
    # del §6.1: dove i documenti atterrano è una decisione di cablaggio, e l'applicazione
    # riceve una porta senza sapere quale collezione ci sia dietro.
    destinazione = collezione_di_carico(cablaggio.orologio.now())
    typer.echo(f"carico in {DATABASE}.{destinazione}")
    cliente = connetti(cablaggio.bersaglio)
    try:
        corsa = WorkloadRunner(
            PymongoStore(cliente[DATABASE][destinazione]),
            cablaggio.orologio,
            cablaggio.sink,
            scrittori=writers,
            lettori=readers,
        )
        esito = mentre_disegna(
            cablaggio.sink, lambda: corsa.esegui(durata_s=duration, genera=genera)
        )
    finally:
        cliente.close()
    typer.echo(riassunto(esito))


# --- La scena centrale del talk: `demo failover` ------------------------------------------

demo = typer.Typer(
    no_args_is_help=True, help="Le scene del Blocco 2, una per sottocomando."
)
app.add_typer(demo, name="demo")
"""Le quattro righe `demo` del §6.4 sono un gruppo, non quattro comandi con un prefisso.

`failover` è di questo Task; `backup-live`, `restore` e `sharding` arrivano ai Task 14 e
15. Un gruppo dichiarato adesso vuol dire che `mongolab demo --help` elenca ciò che
esiste, e che aggiungere una scena è aggiungere una funzione — non ritoccare il modo in
cui i comandi si chiamano dopo che una slide li ha già scritti.
"""


@demo.command()
def failover(
    target: Bersaglio_,
    step: Annotated[
        bool,
        typer.Option(
            "--step", help="Pausa prima di ogni fase, si riparte con Invio: da palco."
        ),
    ] = False,
    node: Annotated[
        str | None,
        typer.Option("--node", help="Quale servizio fermare. Predefinito: il primario."),
    ] = None,
    mode: Annotated[
        ModoGuasto,
        typer.Option("--mode", help="Il guasto: ferma (morto) o sospendi (irraggiungibile)."),
    ] = ModoGuasto.FERMA,
    carico: Annotated[
        float, typer.Option("--carico", help="Secondi di carico prima del guasto.")
    ] = DURATA_CARICO_S,
    elezione: Annotated[
        float, typer.Option("--elezione", help="Secondi di attesa con il nodo giù.")
    ] = DURATA_ELEZIONE_S,
    recupero: Annotated[
        float, typer.Option("--recupero", help="Secondi di carico dopo il rientro.")
    ] = DURATA_RECUPERO_S,
    sink: Resa_ = Resa.RICH,
) -> None:
    """Carico attivo, il primario cade, l'elezione, i due numeri. È l'Atto II.

    **Una sola implementazione, due modi.** Con `--step` la scena si ferma prima di ogni
    fase e riparte con un Invio: è la modalità da palco, quella in cui si parla sopra a
    ciò che sta per succedere. Senza, la stessa scena gira da sola — ed è così che si
    producono le registrazioni di riserva del Task 18, che per costruzione mostrano
    esattamente ciò che si farà dal vivo invece di somigliargli.

    **`--mode sospendi` è l'altra scena**, quella che il pubblico non si aspetta: il nodo
    resta vivo ma irraggiungibile, e il client prende un timeout invece di un connection
    refused. È la differenza fra un server morto e una rete partizionata, e vale i trenta
    secondi che costa.
    """
    if step and sink is Resa.RICH:
        raise typer.BadParameter(
            "--step e --sink rich vogliono lo stesso terminale: la pausa legge da stdin "
            "mentre il Live di Rich ridisegna, e il prompt finirebbe sotto il ridisegno. "
            "Dal palco la riga è `--step --sink plain`, la stessa con cui si girano le "
            "registrazioni di riserva.",
            param_hint="--step",
        )
    cablaggio = cabla(target, sink)
    ponte = SdamBridge(cablaggio.orologio)
    cliente = connetti(cablaggio.bersaglio, event_listeners=ponte.ascoltatori)
    try:
        try:
            attendi_il_primario(cliente)
        except SenzaPrimario as senza:
            raise niente_da_fermare(cablaggio.bersaglio) from senza
        ispettore = PymongoInspector(cliente, DATABASE, COLLEZIONE)
        nodo = (
            node
            if node is not None
            else nodo_di(ispettore.topology(), cablaggio.bersaglio)
        )
        _controlla_nodo(nodo, cablaggio.bersaglio)
        destinazione = collezione_di_carico(cablaggio.orologio.now())
        typer.echo(f"scena del failover su {nodo} · carico in {DATABASE}.{destinazione}")
        archivio = PymongoStore(cliente[DATABASE][destinazione])
        # `--readers 0`: durante l'elezione le letture su un secondario continuano a
        # riuscire, e mescolate alle scritture renderebbero illeggibile l'unica cosa che
        # questa scena misura. Le letture hanno il loro comando, ed è `workload`.
        corsa = WorkloadRunner(
            archivio, cablaggio.orologio, cablaggio.sink, scrittori=SCRITTORI_PREDEFINITI, lettori=0
        )
        scena = ScenarioFailover(
            archivio,
            corsa,
            regia_di(cablaggio.bersaglio, punto_di_vista()),
            cablaggio.orologio,
            cablaggio.sink,
            ponte.drena,
            copione=Copione(
                nodo=nodo,
                modo=mode,
                carico_s=carico,
                elezione_s=elezione,
                recupero_s=recupero,
            ),
        )
        attesa: Attesa = _invio if step else senza_attesa
        esito = mentre_disegna(cablaggio.sink, lambda: scena.esegui(attesa=attesa))
    finally:
        cliente.close()
    typer.echo(cronaca(esito))


def _controlla_nodo(nodo: str, bersaglio: Bersaglio) -> None:
    """`--node` scritto a mano, verificato contro i servizi dello stack.

    Prima del carico e non dopo: un nome sbagliato scoperto dentro la fase del guasto
    lascerebbe una collezione di carico piena a metà e una scena da rifare, e in sala la
    scena da rifare è il costo peggiore che ci sia.
    """
    servizi = servizi_di(bersaglio)
    if nodo not in servizi:
        raise typer.BadParameter(
            f"«{nodo}» non è un servizio di docker/{bersaglio.stack}. "
            f"I servizi sono: {', '.join(servizi)}.",
            param_hint="--node",
        )


def _invio(fase: FaseIniziata) -> None:
    """La pausa di `--step`: si scrive che cosa sta per succedere, e si aspetta un Invio.

    Il testo esce da `typer.echo` e non dal sink, benché la fase sia già un evento e il
    sink lo stia già rendendo. Sono due cose diverse: il sink racconta **alla sala** ciò
    che succede, questa riga parla **a chi tiene la tastiera** e gli dice che tocca a lui.
    Confonderle vorrebbe dire mettere «premi Invio» dentro una registrazione asciinema.
    """
    typer.echo(f"\n▸ {fase.descrizione}")
    input("   Invio per proseguire ")

if __name__ == "__main__":  # pragma: no cover
    app()
