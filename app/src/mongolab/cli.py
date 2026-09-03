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

## I tre comandi, e le opzioni che hanno davvero

Il §6.4 elenca sette righe di comando. Tre sono dirette e stanno qui; le quattro `demo`
arrivano al Task 13, che porta con sé `application/scenari.py`. Le opzioni sono quelle
del design, con i suoi stessi valori come predefiniti — `mongolab workload --target rs`
esegue esattamente la corsa che il §6.4 scrive per esteso, perché due righe di comando
che fanno cose diverse con lo stesso nome sono il modo più rapido di perdere il filo dal
palco.

**`--sink` c'è su `watch` e `workload` e non su `stats`**, ed è una scelta dichiarata:
`stats` è una fotografia e non emette nessun evento, quindi un `--sink` lì sarebbe
un'opzione accettata e inerte. Un'opzione inerte è una bugia che la riga di comando
racconta a chi la legge, e questo repository si è impegnato a non scriverne.

## Che cosa qui è provvisorio, e fino a quando

`watch` ha un ciclo suo — drena il ponte SDAM, aspetta, ricomincia — perché nessun
componente dell'applicazione possiede quel ritmo: il ponte raccoglie e basta, e chi
decide ogni quanto guardare in scena è chi ha in mano lo schermo. Quel ciclo è la prima
riga di `application/scenari.py`, e ci si sposta al Task 13: finché resta qui, è
orchestrazione dentro il composition root, cioè un po' più di quello che il §6.1 gli
assegna. È scritto perché si veda.

Sempre in `watch`, `TopologyWatcher` **non** c'è, e la sua assenza è deliberata: quando
c'era, ogni transizione finiva in cronaca due volte, perché lui e il ponte guardano la
stessa struttura da due lati. Il §6.3 assegna la cronaca al ponte; l'interruzione, che è
l'altra cosa che la sentinella sa fare, si misura accanto alle scritture perse — cioè
nello scenario di failover del Task 13.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
import math
import sys
from typing import Annotated, Callable, Final

import typer

from mongolab.application.topologia import INTERVALLO_PREDEFINITO_MS
from mongolab.application.workload import WorkloadRunner
from mongolab.domain.porte import Clock, EventSink
from mongolab.infrastructure.bersagli import (
    COLLEZIONE,
    DATABASE,
    Bersaglio,
    BersaglioSconosciuto,
    bersaglio_di,
    collezione_di_carico,
    connetti,
)
from mongolab.infrastructure.generatore import DataGenerator
from mongolab.infrastructure.inspector import PymongoInspector
from mongolab.infrastructure.orologio import SystemClock
from mongolab.infrastructure.sdam import SdamBridge
from mongolab.infrastructure.store import PymongoStore
from mongolab.infrastructure.zavorra import byte_di, con_dimensione
from mongolab.presentation.null import NullSink
from mongolab.presentation.plain import PlainSink
from mongolab.presentation.rapporto import rapporto, riassunto
from mongolab.presentation.rich_tui import RichTui

__all__ = [
    "DIMENSIONE_PREDEFINITA",
    "DURATA_WATCH_S",
    "DURATA_WORKLOAD_S",
    "LETTORI_PREDEFINITI",
    "SCRITTORI_PREDEFINITI",
    "Cablaggio",
    "Resa",
    "app",
    "cabla",
    "giri_di",
    "mentre_disegna",
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
        mentre_disegna(cablaggio.sink, lambda: _sorveglia(ponte, cablaggio, giri))
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


def _sorveglia(ponte: SdamBridge, cablaggio: Cablaggio, giri: int) -> None:
    """Il ciclo di `watch`: il ponte drenato, l'attesa. Al Task 13 si sposta in `scenari`.

    Il ciclo non interroga niente, e la mancanza è la correzione di un difetto: qui c'era
    anche un `TopologyWatcher`, e raccontava una seconda volta ciò che il ponte aveva già
    raccontato. Il driver osserva per conto suo, su un thread suo; questo giro serve solo
    a portare in scena ciò che ha già visto.

    Gli eventi del ponte — transizioni, latenze degli heartbeat — arrivano dai thread del
    monitor di pymongo e restano in coda finché qualcuno non li prende. Drenare a ogni
    giro, e non una volta sola alla fine, è ciò che fa vedere l'elezione **mentre**
    succede invece che tutta insieme quando è passata.

    L'attesa sta **fra** un drenaggio e l'altro, mai dopo l'ultimo: mezzo secondo di
    schermo fermo alla fine di ogni scena è la cosa che si nota di più in una demo.
    """
    for giro in range(giri):
        for evento in ponte.drena():
            cablaggio.sink.emit(evento)
        if giro < giri - 1:
            cablaggio.orologio.sleep(INTERVALLO_PREDEFINITO_MS / 1000.0)


if __name__ == "__main__":  # pragma: no cover
    app()
