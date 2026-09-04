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
gruppo, e tre di quelle scene — `failover`, `backup-live`, `restore` — sono di questo file
dai Task 13 e 14. `sharding` arriva al Task 15.

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
from typing import Annotated, Any, Callable, Final, Mapping

import typer

from mongolab.application.scenari import (
    DURATA_CARICO_S,
    DURATA_ELEZIONE_S,
    DURATA_RECUPERO_S,
    TETTO_DUMP_S,
    Attesa,
    Copione,
    CopioneBackup,
    CopioneRestore,
    CopioneSharding,
    ModoGuasto,
    ScenarioBackup,
    ScenarioFailover,
    ScenarioRestore,
    ScenarioSharding,
    senza_attesa,
    sorveglia,
)
from mongolab.application.topologia import INTERVALLO_PREDEFINITO_MS
from mongolab.application.workload import WorkloadRunner
from mongolab.domain.eventi import FaseIniziata
from mongolab.domain.modelli import DescrizioneTopologia, Documento
from mongolab.domain.porte import Clock, EventSink, Regia
from mongolab.infrastructure.bersagli import (
    ATTESA_SELEZIONE_MS,
    COLLEZIONE,
    DATABASE,
    VARIABILE_PUNTO_DI_VISTA,
    Bersaglio,
    BersaglioSconosciuto,
    Credenziali,
    PuntoDiVista,
    SenzaPrimario,
    attendi_il_primario,
    bersaglio_di,
    collezione_di_carico,
    connetti,
    credenziali_di,
    opzioni_di_misura,
    punto_di_vista,
    radice,
)
from mongolab.infrastructure.backup import SubprocessBackup
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
from mongolab.presentation.rapporto import (
    copia,
    cronaca,
    rapporto,
    riassunto,
    ripristino,
    spartizione,
)
from mongolab.presentation.rich_tui import RichTui

__all__ = [
    "DATABASE_RIPRISTINO",
    "DESTINAZIONE_DUMP",
    "DIMENSIONE_PREDEFINITA",
    "DURATA_WATCH_S",
    "DURATA_WORKLOAD_S",
    "IMMAGINI",
    "OPZIONI_DUMP",
    "niente_da_fermare",
    "LETTORI_PREDEFINITI",
    "MIRATO",
    "SCRITTURE_SHARDING",
    "SPARPAGLIATO",
    "SCRITTORI_PREDEFINITI",
    "Cablaggio",
    "Resa",
    "app",
    "cabla",
    "comandi_di",
    "demo",
    "giri_di",
    "host_interno_di",
    "mentre_disegna",
    "nodo_di",
    "regia_di",
    "riga_delle_opzioni",
    "servizi_di",
    "sink_di",
    "strumento_di",
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


DESTINAZIONE_DUMP: Final = Path("/tmp/mongolab-backup")
"""Dove il dump atterra, **dentro il nodo** in cui `mongodump` gira.

Un percorso fisso e non uno con la data: `demo backup-live` e `demo restore` sono due
comandi consecutivi, e un percorso da ricopiare fra l'uno e l'altro è un percorso da
sbagliare davanti alla sala. Chi ne vuole due li nomina con `--out`.

`/tmp` e non `/data`: dentro l'immagine di MongoDB `/data/db` è il volume e il resto di
`/data` appartiene a root, mentre `/tmp` è scrivibile da chiunque — e il dump deve
sopravvivere solo fra i due comandi, non fra due ricostruzioni dello stack.
"""

DATABASE_RIPRISTINO: Final = f"{DATABASE}_ripristinato"
"""Dove il restore scrive, e non è mai `lab`.

Ciò che manca nella copia sono i documenti scritti **durante** il dump, e quelli stanno
nell'originale: restaurare lì sopra li lascerebbe dove sono, il conteggio combacerebbe, e
la differenza che l'Atto III esiste per mostrare sparirebbe proprio perché il restore è
riuscito.
"""

SCRITTURE_SHARDING: Final = 5000
"""Quante scritture fa ciascuna delle due corse del Blocco 3.

Un conteggio e non una durata, per la ragione scritta in `sharding`. Cinquemila perché
sullo stack 03 sono circa sette secondi per corsa — misurati 4288 scritture in sei
secondi ([M-052](../../../app/docs/Sources.md#m-052)) — cioè quattordici secondi in tutto,
un po' più dei dieci che costano le altre scene. Lo sforo è deliberato: è il prezzo della
seconda colonna, e senza la seconda colonna la prima non dimostra niente.
"""

MIRATO: Final[Documento] = {"_id": 4242}
"""La domanda che il router sa indirizzare, e il numero non è a caso.

La chiave dello stack 03 è `{_id: "hashed"}`: su una **uguaglianza** di `_id` il router
calcola l'hash, sa in quale intervallo cade e interroga un solo shard. Su qualunque altro
campo non può, e li interroga tutti — che è precisamente l'altra riga della schermata.

`4242` sta dentro i ventimila del seed, quindi il documento esiste davvero: un piano su un
filtro che non trova niente sarebbe identico, ma chi guarda non ha modo di saperlo e la
domanda «e se non c'era?» si porta via la scena.
"""

SPARPAGLIATO: Final[Documento] = {"citta": "Ancona"}
"""La domanda che nessun router sa indirizzare, e nemmeno questa è a caso.

`citta` è un campo del seed dello stack 03 — dieci città, Ancona è la prima — quindi il
filtro è uno che si scriverebbe davvero. E non è la chiave di shard né un suo prefisso:
il router non ha modo di sapere dove stiano quei documenti, li chiede a tutti gli shard e
poi ricuce. È lo scatter-gather del §6.3, mostrato invece che raccontato.

Ancona perché il talk si tiene lì. Non cambia niente al piano, e in sala si nota.
"""

OPZIONI_DUMP: Final = ("--readPreference=secondary", "--oplog")
"""Le due opzioni che fanno la scena, e stanno qui perché la politica è della radice.

`--readPreference=secondary` è la promessa da verificare — il dump legge dai secondari e
il primario non se ne accorge — e `--oplog` è ciò che rende la copia coerente a un
istante. Misurate insieme: senza la prima, `opcounters.query` del primario sale di dieci
e quello dei secondari di uno; con la prima, il primario sale di **zero** e i due
secondari di sei e quattro ([M-046](../../docs/Sources.md#m-046)).
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


def host_interno_di(bersaglio: Bersaglio) -> str:
    """L'indirizzo che `mongodump` usa, e non è quello che usa `mongolab`.

    È [M-019](../../docs/Sources.md#m-019) vista dal lato degli strumenti. L'applicazione
    gira sull'host, dove i nomi di servizio non si risolvono e si arriva a `localhost` con
    la scoperta spenta; il processo che l'applicazione avvia gira **dentro un nodo**, dove
    quei nomi esistono. Passargli la vista dell'host lo manderebbe a bussare a un
    `localhost` che dentro il container è sé stesso.

    La forma `rs0/uno,due,tre` è quella che gli strumenti di MongoDB chiamano *seed list*:
    davanti il nome del set, che è la stessa dichiarazione di aspettativa di `Vista.replica`.
    Dove il set non c'è resta il solo elenco, perché `rs0/` davanti a un mongod solo è una
    dichiarazione falsa e lo strumento la crede.
    """
    vista = bersaglio.da_rete
    elenco = ",".join(f"{nome}:{porta}" for nome, porta in vista.semi)
    return f"{vista.replica}/{elenco}" if vista.replica is not None else elenco


def strumento_di(
    bersaglio: Bersaglio, nodo: str, credenziali: Credenziali | None
) -> SubprocessBackup:
    """`mongodump` e `mongorestore`, eseguiti dentro un nodo dello stack.

    **Gli strumenti non stanno nell'immagine dell'applicazione**, e la ragione è misurata:
    copiarci dentro i due binari dall'immagine `mongo` pinnata produce un container che si
    ferma su `libgssapi_krb5.so.2: cannot open shared object file`
    ([M-044](../../docs/Sources.md#m-044)). Stanno già in ogni nodo, e la riga per andarci
    la costruisce `ComandiCompose.dentro` ([ADR-0100](../../../docs/Decision.md#adr-0100)).

    `dove=radice()` non è un dettaglio: il frasario tiene i percorsi dei `compose.yaml`
    **relativi alla radice** perché la riga si possa incollare in un terminale, e chi
    lancia `mongolab` non parte per forza di lì.

    La credenziale arriva già risolta invece di essere letta qui, e serve alle prove: il
    `.env` dello stack è fuori dal repository ([ADR-0014](../../../docs/Decision.md#adr-0014)),
    e una prova unitaria che dipendesse da un file che non c'è sarebbe rossa su ogni
    macchina appena clonata.
    """
    comandi = comandi_di(bersaglio)
    return SubprocessBackup(
        host=host_interno_di(bersaglio),
        comando_dump=comandi.dentro(nodo, "mongodump"),
        comando_restore=comandi.dentro(nodo, "mongorestore"),
        utente=credenziali.utente if credenziali is not None else None,
        password=credenziali.password if credenziali is not None else None,
        database=DATABASE,
        opzioni_dump=OPZIONI_DUMP,
        dove=radice(),
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

    **L'`EOFError` si assorbe, e la ragione è dove questa funzione può essere chiamata.**
    Da [ADR-0119](../../../docs/Decision.md#adr-0119) la ripresa del failover sta in un
    `finally`, quindi la conferma può arrivare mentre un'eccezione sta risalendo — e
    un'eccezione sollevata dentro un `finally` prende il posto di quella che passava. Con
    `stdin` che non è un terminale — una prova di integrazione, una pipe, un
    `docker compose run` senza `-t` — `input()` alza `EOFError` all'istante, e chi guarda
    leggerebbe «EOF when reading a line» invece del motivo per cui la scena si è fermata.
    Dove non c'è nessuno a cui fare la domanda, l'unica risposta sensata è proseguire.
    """
    try:
        input("   Invio quando è stato eseguito ")
    except EOFError:
        typer.echo("   (nessuno da chiedere: proseguo)")


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
        ispettore = PymongoInspector(cliente, DATABASE)
        typer.echo(
            rapporto(
                ispettore,
                collezione=COLLEZIONE,
                titolo=f"{bersaglio.nome} (docker/{bersaglio.stack})",
            )
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


def riga_delle_opzioni(opzioni: Mapping[str, Any]) -> str:
    """La riga che annuncia com'è configurato il client, o niente se è quello di sempre.

    Riceve **la stessa mappa** che va a `connetti`, e non i parametri da cui è stata
    costruita. Due funzioni che descrivono la stessa configurazione — una che la fa, una
    che la racconta — divergono alla prima opzione aggiunta a una sola delle due, e il
    modo in cui ci si accorge è una registrazione che dichiara una misura diversa da
    quella eseguita. Qui la parafrasi non esiste: si stampa il dizionario.

    Vuoto vuol dire vuoto. Una corsa senza opzioni di misura non annuncia «predefinito»,
    perché la riga in più a schermo darebbe l'impressione che il Task 16 abbia toccato
    anche la corsa di base, e il §6.4 la vuole identica a com'era.
    """
    if not opzioni:
        return ""
    return "opzioni " + " · ".join(f"{nome}={valore}" for nome, valore in opzioni.items())


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
        float | None,
        typer.Option(
            "--duration",
            help="Secondi di carico. Predefinito 120, se non si dà --writes.",
        ),
    ] = None,
    writes: Annotated[
        int | None,
        typer.Option(
            "--writes",
            help="Quante scritture fare, invece di quanti secondi durare.",
        ),
    ] = None,
    write_concern: Annotated[
        str | None,
        typer.Option(
            "--write-concern",
            help="Quante conferme aspettare: un numero, oppure majority.",
        ),
    ] = None,
    journal: Annotated[
        bool | None,
        typer.Option(
            "--journal/--no-journal",
            help="Chiede j: true, cioè la conferma dopo il giornale.",
        ),
    ] = None,
    retry_writes: Annotated[
        bool | None,
        typer.Option(
            "--retry-writes/--no-retry-writes",
            help="La rete di sicurezza del driver: accesa o spenta.",
        ),
    ] = None,
    max_staleness: Annotated[
        int | None,
        typer.Option(
            "--max-staleness",
            help="Secondi di ritardo tollerati; implica la lettura da un secondario.",
        ),
    ] = None,
    max_pool_size: Annotated[
        int | None,
        typer.Option("--max-pool-size", help="Quante connessioni può tenere aperte."),
    ] = None,
    sink: Resa_ = Resa.RICH,
) -> None:
    """Manda carico contro lo stack, e alla fine dice come è andata.

    **Due limiti, e mai tutti e due** (ADR-0107, esteso qui dal Task 16). `--duration` è
    la riga del §6.4 e resta il predefinito; `--writes` è quello che serve a confrontare
    architetture diverse, perché a durata uguale due stack con throughput diverso non
    hanno fatto lo stesso lavoro — è la stessa scoperta che al Task 15 ha riscritto
    `demo sharding`, applicata al confronto fra le tre architetture.

    **Le quattro opzioni di misura** (ADR-0109) saldano altrettanti debiti scritti nelle
    pagine delle architetture, e ognuna vale come mezza misura: `--journal` contro
    `--no-journal`, `--retry-writes` contro `--no-retry-writes`. Chi ne cita una sola in
    una voce di `Sources.md` sta riportando la buona notizia senza il suo prezzo.

    **`--write-concern` è la quinta, e arriva dal Task 18** (ADR-0114). Serve a isolare
    che cosa il primario di un replica set stia contando quando dichiara 18 390 µs di
    `opLatencies.writes` contro i 67 µs dello standalone: la stessa corsa con `w: 1`
    risponde, e senza questa parola non era chiedibile dalla riga di comando. Vale un
    numero o `majority`, come nell'URI.
    """
    if writes is not None and duration is not None:
        # Il rifiuto sta qui e non in `WorkloadRunner.esegui`, che pure ha già la regola:
        # là scatterebbe dopo che il client è aperto e la collezione annunciata, cioè dopo
        # aver fatto credere che la corsa fosse partita.
        raise typer.BadParameter(
            "una corsa si limita in un modo solo: --writes, quante scritture fare, "
            "oppure --duration, per quanti secondi andare avanti. Con tutti e due il "
            "primo che scade smentirebbe l'altro."
        )
    cablaggio = cabla(target, sink)
    genera = con_dimensione(DataGenerator().documento, byte_di(doc_size))
    misura = opzioni_di_misura(
        write_concern=write_concern,
        journal=journal,
        retry_writes=retry_writes,
        max_staleness_s=max_staleness,
        max_pool_size=max_pool_size,
    )
    # **Non `COLLEZIONE`**: il carico ha la propria, e il nome cambia a ogni corsa. Il
    # perché sta in `bersagli.collezione_di_carico`, ed è un E11000 misurato, non una
    # precauzione. Che la scelta si faccia qui e non dentro `WorkloadRunner` è la regola
    # del §6.1: dove i documenti atterrano è una decisione di cablaggio, e l'applicazione
    # riceve una porta senza sapere quale collezione ci sia dietro.
    destinazione = collezione_di_carico(cablaggio.orologio.now())
    typer.echo(f"carico in {DATABASE}.{destinazione}")
    annuncio = riga_delle_opzioni(misura)
    if annuncio:
        typer.echo(annuncio)
    cliente = connetti(cablaggio.bersaglio, **misura)
    try:
        corsa = WorkloadRunner(
            PymongoStore(cliente[DATABASE][destinazione]),
            cablaggio.orologio,
            cablaggio.sink,
            scrittori=writers,
            lettori=readers,
        )
        limite = (
            {"scritture": writes}
            if writes is not None
            else {"durata_s": duration if duration is not None else DURATA_WORKLOAD_S}
        )
        esito = mentre_disegna(
            cablaggio.sink, lambda: corsa.esegui(genera=genera, **limite)
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

`failover`, `backup-live` e `restore` sono i tre Atti del Blocco 2; `sharding` arriva al
Task 15. Un gruppo dichiarato al Task 13 ha già mantenuto la sua promessa: le due scene di
oggi sono due funzioni in più, e nessuno ha dovuto ritoccare il modo in cui i comandi si
chiamano dopo che una slide li aveva già scritti.

**Le prime due scene girano in due posti opposti, ed è dichiarato.** `failover` vuole la
scoperta della topologia e quindi la rete Compose; `backup-live` e `restore` vogliono
entrare in un nodo con `docker compose exec` e quindi l'host. Non è una svista da
uniformare: è la stessa asimmetria che ha fatto nascere la porta `Regia`, e i due comandi
la dicono rifiutandosi dal lato sbagliato invece di fallire a metà scena.
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
    retry_writes: Annotated[
        bool | None,
        typer.Option(
            "--retry-writes/--no-retry-writes",
            help="La rete di sicurezza del driver durante l'elezione: accesa o spenta.",
        ),
    ] = None,
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

    **`--no-retry-writes` è la terza** (ADR-0109), e non ha bisogno di codice suo: è la
    stessa scena con la rete di sicurezza del driver spenta, ed esiste perché
    `replica-set.md` aveva intestato qui la misura di che cosa vede un'applicazione senza
    di essa. Vale come mezza misura: il numero che conta è la differenza con la corsa
    identica in cui i tentativi sono accesi.
    """
    _niente_step_con_la_tui(step, sink)
    cablaggio = cabla(target, sink)
    ponte = SdamBridge(cablaggio.orologio)
    misura = opzioni_di_misura(retry_writes=retry_writes)
    annuncio = riga_delle_opzioni(misura)
    if annuncio:
        typer.echo(annuncio)
    cliente = connetti(
        cablaggio.bersaglio, event_listeners=ponte.ascoltatori, **misura
    )
    try:
        try:
            attendi_il_primario(cliente)
        except SenzaPrimario as senza:
            raise niente_da_fermare(cablaggio.bersaglio) from senza
        ispettore = PymongoInspector(cliente, DATABASE)
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


# --- L'Atto III: il backup a caldo, e la copia rimessa altrove --------------------------


@demo.command(name="backup-live")
def backup_live(
    target: Bersaglio_,
    out: Annotated[
        Path, typer.Option("--out", help="Dove il dump atterra, dentro il nodo.")
    ] = DESTINAZIONE_DUMP,
    node: Annotated[
        str | None,
        typer.Option("--node", help="In quale nodo eseguire mongodump."),
    ] = None,
    carico: Annotated[
        float, typer.Option("--carico", help="Secondi di carico prima del dump.")
    ] = DURATA_CARICO_S,
    tetto: Annotated[
        float,
        typer.Option(
            "--tetto", help="Secondi oltre i quali il dump si abbatte e la scena finisce."
        ),
    ] = TETTO_DUMP_S,
    step: Annotated[
        bool,
        typer.Option(
            "--step", help="Pausa prima di ogni fase, si riparte con Invio: da palco."
        ),
    ] = False,
    sink: Resa_ = Resa.RICH,
) -> None:
    """Il carico gira, il dump parte, e i due ritmi si guardano. È l'Atto III.

    **La tesi è che il throughput non crolli**, e una tesi si mostra invece di
    affermarla: la scena misura il carico da solo, poi lo stesso carico mentre
    `mongodump --readPreference=secondary --oplog` copia, e mette i due numeri accanto.
    Il calo che esce è quello che è — questa riga di comando non ha un valore soglia
    oltre il quale si lamenta, perché a decidere se è poco è chi guarda.

    **La finestra della seconda misura è quella del dump, non una durata scelta prima.**
    Il carico si ferma quando il dump finisce: con una durata fissa un dump da mezzo
    secondo dentro un campione da venti verrebbe diluito, e un crollo totale comparirebbe
    come un calo del due per cento. `--tetto` resta come rete di sicurezza, per il dump
    che si pianta: allo scadere il `mongodump` viene abbattuto, il carico si ferma con lui
    e la scena finisce dicendo che è stato il tetto. Una scena che non termina in sala è
    peggio di una scena che termina male.

    **Si gira dall'host**, ed è l'inverso del failover. Là serve la scoperta della
    topologia, che funziona solo da dentro la rete Compose (M-019); qui serve entrare in
    un nodo con `docker compose exec`, e il socket del demone Docker c'è solo da fuori.
    """
    _niente_step_con_la_tui(step, sink)
    cablaggio = cabla(target, sink)
    _solo_da_un_replica_set(cablaggio.bersaglio)
    _solo_dall_host("backup-live")
    nodo = _nodo_degli_strumenti(cablaggio.bersaglio, node)
    strumento = strumento_di(
        cablaggio.bersaglio, nodo, credenziali_di(cablaggio.bersaglio)
    )
    ponte = SdamBridge(cablaggio.orologio)
    cliente = connetti(cablaggio.bersaglio, event_listeners=ponte.ascoltatori)
    try:
        try:
            attendi_il_primario(cliente)
        except SenzaPrimario as senza:
            raise _serve_il_primario(cablaggio.bersaglio) from senza
        ispettore = PymongoInspector(cliente, DATABASE)
        if not ispettore.topology().ha_primario:
            raise _serve_il_primario(cablaggio.bersaglio)
        destinazione = collezione_di_carico(cablaggio.orologio.now())
        typer.echo(f"backup a caldo da {nodo} · carico in {DATABASE}.{destinazione}")
        # La riga si mostra perché si **può** mostrare: il segreto non ci passa, viaggia
        # su stdin (ADR-0054). Ed è la riga che il Blocco 2 sta spiegando, quindi vederla
        # per intero vale più di qualunque slide che la riassuma.
        typer.echo(f"  {' '.join(strumento.argomenti_dump(out))}")
        archivio = PymongoStore(cliente[DATABASE][destinazione])
        # `--readers 0` come nel failover, per una ragione diversa: il dump legge dai
        # secondari, e delle letture nostre sugli stessi secondari mescolerebbero due
        # effetti in un numero solo.
        corsa = WorkloadRunner(
            archivio,
            cablaggio.orologio,
            cablaggio.sink,
            scrittori=SCRITTORI_PREDEFINITI,
            lettori=0,
        )
        scena = ScenarioBackup(
            archivio,
            corsa,
            strumento,
            cablaggio.orologio,
            cablaggio.sink,
            ponte.drena,
            copione=CopioneBackup(destinazione=out, carico_s=carico, tetto_s=tetto),
        )
        attesa: Attesa = _invio if step else senza_attesa
        esito = mentre_disegna(cablaggio.sink, lambda: scena.esegui(attesa=attesa))
    finally:
        cliente.close()
    typer.echo(copia(esito))
    typer.echo(_prossimo_passo(target, out, destinazione))


@demo.command()
def restore(
    target: Bersaglio_,
    da: Annotated[
        Path, typer.Option("--from", help="La directory del dump, dentro il nodo.")
    ] = DESTINAZIONE_DUMP,
    into: Annotated[
        str, typer.Option("--into", help="Il database in cui la copia rientra.")
    ] = DATABASE_RIPRISTINO,
    collection: Annotated[
        str, typer.Option("--collection", help="Quale collezione contare, dai due lati.")
    ] = COLLEZIONE,
    node: Annotated[
        str | None,
        typer.Option("--node", help="In quale nodo eseguire mongorestore."),
    ] = None,
    step: Annotated[
        bool,
        typer.Option(
            "--step", help="Pausa prima di ogni fase, si riparte con Invio: da palco."
        ),
    ] = False,
    sink: Resa_ = Resa.RICH,
) -> None:
    """La copia rientra accanto all'originale, e i due conteggi si guardano.

    **Accanto e non sopra.** Il restore scrive in un database diverso perché ciò che
    manca nella copia — i documenti scritti mentre il dump era in corso — sta
    nell'originale, e sovrascriverlo cancellerebbe la prova di ciò che la scena vuole
    mostrare.

    **La differenza non è un guasto.** `mongodump --oplog` porta via anche l'oplog della
    finestra, ma `--oplogReplay` è incompatibile con la rinomina dei namespace che serve
    a restaurare altrove (ADR-0084): il prezzo di non aver fermato il servizio si legge
    lì, ed è un numero, non un errore.

    I predefiniti sono quelli che `demo backup-live` lascia sul terminale: senza opzioni,
    questo comando raccoglie ciò che la scena precedente ha prodotto.
    """
    _niente_step_con_la_tui(step, sink)
    cablaggio = cabla(target, sink)
    _solo_da_un_replica_set(cablaggio.bersaglio)
    _solo_dall_host("restore")
    if into == DATABASE:
        raise typer.BadParameter(
            f"«{into}» è il database di partenza. Ciò che manca nella copia sono i "
            "documenti scritti mentre il dump era in corso, e quelli stanno lì: "
            "restaurarci sopra li lascerebbe al loro posto, i conteggi combacerebbero, e "
            "la differenza che questa scena esiste per mostrare sparirebbe proprio "
            f"perché il restore è riuscito. Il predefinito è «{DATABASE_RIPRISTINO}».",
            param_hint="--into",
        )
    nodo = _nodo_degli_strumenti(cablaggio.bersaglio, node)
    strumento = strumento_di(
        cablaggio.bersaglio, nodo, credenziali_di(cablaggio.bersaglio)
    )
    cliente = connetti(cablaggio.bersaglio)
    try:
        typer.echo(
            f"restore da {da} in {nodo} · "
            f"{DATABASE}.{collection} → {into}.{collection}"
        )
        typer.echo(f"  {' '.join(strumento.argomenti_restore(da, into))}")
        scena = ScenarioRestore(
            PymongoStore(cliente[DATABASE][collection]),
            PymongoStore(cliente[into][collection]),
            strumento,
            cablaggio.orologio,
            cablaggio.sink,
            copione=CopioneRestore(sorgente=da, database=into),
        )
        attesa: Attesa = _invio if step else senza_attesa
        esito = mentre_disegna(cablaggio.sink, lambda: scena.esegui(attesa=attesa))
    finally:
        cliente.close()
    typer.echo(ripristino(esito))


# --- Il Blocco 3: lo stesso carico due volte, e i chunk che si muovono ------------------


@demo.command()
def sharding(
    target: Bersaglio_,
    collection: Annotated[
        str,
        typer.Option("--collection", help="La collezione distribuita da caricare."),
    ] = COLLEZIONE,
    scritture: Annotated[
        int,
        typer.Option("--scritture", help="Quante scritture, per ciascuna delle due corse."),
    ] = SCRITTURE_SHARDING,
    step: Annotated[
        bool,
        typer.Option(
            "--step", help="Pausa prima di ogni fase, si riparte con Invio: da palco."
        ),
    ] = False,
    sink: Resa_ = Resa.RICH,
) -> None:
    """Lo stesso carico due volte, e la chiave di shard è l'unica differenza. È il Blocco 3.

    **Due corse e non una.** Il primo carico va in una collezione nuova, che nessuno ha
    distribuito: finisce tutto su un solo shard, ed è la riga che dà un metro al resto. Il
    secondo va in `lab.ordini`, che è distribuita su `{_id: "hashed"}`, e si ripartisce.
    Le due colonne accostate dicono che cosa fa la chiave di shard — e una sola colonna
    non lo direbbe, perché mancherebbe il termine di paragone.

    **Il limite è un conteggio e non una durata**, ed è l'unica scena in cui lo sia. Le
    altre tre usano i secondi perché là il carico è lo sfondo; qui è la misura, e due
    corse cronometrate uguali producono conteggi diversi — 4288 contro 4415 sullo stack 03
    ([M-052](../../../app/docs/Sources.md#m-052)), cioè la scena chiamata «lo stesso carico
    due volte» dichiarava di non esserlo. Con un conteggio sono uguali per costruzione, e
    la sola differenza rimasta fra le colonne è la chiave di shard. Lo schermo lo verifica
    lo stesso, perché una garanzia che nessuno controlla è una speranza.

    **Niente si cancella alla fine.** Le due collezioni restano dove sono: il carico è la
    prova, e una prova che si autodistrugge non è ispezionabile dopo. La pulizia è di
    `tools/reset-demo.sh` ([ADR-0088](../../../docs/Decision.md#adr-0088)).
    """
    _niente_step_con_la_tui(step, sink)
    cablaggio = cabla(target, sink)
    _solo_da_uno_sharded_cluster(cablaggio.bersaglio)
    cliente = connetti(cablaggio.bersaglio)
    try:
        intera = collezione_di_carico(cablaggio.orologio.now())
        # «carico in lab.…» è la formula delle altre due scene, e non è una convenzione
        # estetica: è la riga da cui chi presenta — e la prova d'integrazione — ricava il
        # nome della collezione da togliere dopo. Riscriverla diversamente qui vorrebbe
        # dire un residuo in più ogni volta che la scena muore a metà.
        typer.echo(
            f"scena dello sharding · carico in {DATABASE}.{intera} (non distribuita) "
            f"e in {DATABASE}.{collection} (distribuita)"
        )
        archivio_intera = PymongoStore(cliente[DATABASE][intera])
        archivio_sparsa = PymongoStore(cliente[DATABASE][collection])
        # `--readers 0` per la ragione delle altre due scene: qui si contano i documenti
        # **arrivati** su ciascuno shard, e delle letture non ne fanno arrivare nessuno.
        scena = ScenarioSharding(
            PymongoInspector(cliente, DATABASE),
            # Il pianificatore è lo store della collezione distribuita, e non è un caso:
            # `explain()` si chiede alla collezione di cui si vuole il piano, e le due
            # domande del copione riguardano quella.
            archivio_sparsa,
            _corsa(archivio_intera, cablaggio),
            _corsa(archivio_sparsa, cablaggio),
            cablaggio.orologio,
            cablaggio.sink,
            copione=CopioneSharding(
                intera=intera,
                sparsa=collection,
                mirato=MIRATO,
                sparpagliato=SPARPAGLIATO,
                scritture=scritture,
            ),
        )
        attesa: Attesa = _invio if step else senza_attesa
        esito = mentre_disegna(cablaggio.sink, lambda: scena.esegui(attesa=attesa))
    finally:
        cliente.close()
    typer.echo(spartizione(esito))


def _corsa(archivio: PymongoStore, cablaggio: Cablaggio) -> WorkloadRunner:
    """Le due corse del Blocco 3 nascono uguali, e questa riga è la garanzia che lo siano.

    Scritte due volte disteso sarebbero due righe che possono divergere con una svista, e
    la svista renderebbe le due colonne non confrontabili senza che niente lo segnali.
    """
    return WorkloadRunner(
        archivio,
        cablaggio.orologio,
        cablaggio.sink,
        scrittori=SCRITTORI_PREDEFINITI,
        lettori=0,
    )


def _solo_da_uno_sharded_cluster(bersaglio: Bersaglio) -> None:
    """Il Blocco 3 si gira sullo stack 03, e gli altri due si rifiutano dicendo perché.

    Come `_solo_da_un_replica_set`, il controllo è sulla **proprietà** e non sul nome: si
    passa da un router — quindi la scoperta è spenta — e quel router non appartiene a
    nessun replica set. È la firma che in `bersagli.py` ha soltanto lo stack sharded.
    """
    if not bersaglio.da_rete.diretto and bersaglio.da_rete.replica is None:
        return
    if bersaglio.da_rete.diretto:
        raise typer.BadParameter(
            f"«{bersaglio.nome}» è un mongod solo: non ha shard fra cui ripartire niente, "
            "e `explain()` da lì non nomina nessuno shard perché non c'è nessun router "
            "che riparta la domanda. La scena dei chunk è quella dello sharded cluster: "
            "--target sharded.",
            param_hint="--target",
        )
    raise typer.BadParameter(
        f"«{bersaglio.nome}» è un replica set: tre nodi con gli **stessi** dati, non tre "
        "shard con dati diversi. Non c'è nessun router a cui chiedere un piano, e le due "
        "righe per cui il Blocco 3 esiste — la query mirata e quella su tutti — "
        "resterebbero mute. La scena dei chunk vuole lo sharded cluster: --target sharded.",
        param_hint="--target",
    )


def _niente_step_con_la_tui(step: bool, sink: Resa) -> None:
    """Il rifiuto che vale per ogni scena con `--step`, scritto una volta sola.

    Sta qui e non dentro i comandi perché la terza copia sarebbe quella che diverge: è la
    stessa ragione per cui `sink_di` esiste invece di tre `if` sparsi.
    """
    if step and sink is Resa.RICH:
        raise typer.BadParameter(
            "--step e --sink rich vogliono lo stesso terminale: la pausa legge da stdin "
            "mentre il Live di Rich ridisegna, e il prompt finirebbe sotto il ridisegno. "
            "Dal palco la riga è `--step --sink plain`, la stessa con cui si girano le "
            "registrazioni di riserva.",
            param_hint="--step",
        )


def _solo_da_un_replica_set(bersaglio: Bersaglio) -> None:
    """L'Atto III si gira sullo stack 02, e gli altri due si rifiutano dicendo perché.

    Non un controllo sul nome — `bersaglio.nome != "rs"` — ma sulla **proprietà** che
    serve: che quel bersaglio si presenti come un replica set. Il giorno in cui il
    repository ne avesse un secondo, la riga giusta funzionerebbe da sé.
    """
    if bersaglio.da_rete.replica is not None:
        return
    if bersaglio.da_rete.diretto:
        raise typer.BadParameter(
            f"«{bersaglio.nome}» è un mongod solo, e un mongod solo non ha un oplog: "
            "`mongodump --oplog` non ha niente da copiare e la copia non è coerente a "
            "nessun istante (ADR-0022). Il backup a caldo è la scena del replica set: "
            "--target rs.",
            param_hint="--target",
        )
    raise typer.BadParameter(
        f"«{bersaglio.nome}» si raggiunge da un mongos, che non è membro di nessun "
        "replica set e non ha un oplog da consegnare. Un dump preso da lì attraversa gli "
        "shard uno per uno, senza un istante comune: non è la fotografia che questa "
        "scena promette. Il backup a caldo si gira sul replica set: --target rs.",
        param_hint="--target",
    )


def _solo_dall_host(scena: str) -> None:
    """Le due scene dell'Atto III non girano da dentro la rete, ed è l'inverso del failover.

    Là serve la scoperta della topologia, che si accende solo da dentro (M-019); qui serve
    `docker compose exec`, e il socket del demone Docker sta solo fuori — nel container
    dell'applicazione non c'è, perché il Task 9 ha deciso di non montarglielo. Un comando
    che accettasse tutti e due i posti sarebbe un comando che in uno dei due mente.
    """
    if punto_di_vista() is PuntoDiVista.HOST:
        return
    raise typer.BadParameter(
        f"«demo {scena}» si gira dall'host e non da dentro la rete Compose: mongodump "
        "non è nell'immagine dell'applicazione (M-044) e questo container non ha il "
        "socket del demone Docker, quindi non può entrare in un nodo per trovarcelo. "
        "Dalla radice del repository: `uv run --directory app mongolab demo "
        f"{scena} --target rs`.",
        param_hint=VARIABILE_PUNTO_DI_VISTA,
    )


def _nodo_degli_strumenti(bersaglio: Bersaglio, detto: str | None) -> str:
    """In quale nodo entrare a cercare `mongodump`. Predefinito: il primo dello stack.

    Il primo e non il primario, e non è indifferente: il dump atterra nel filesystem del
    nodo in cui gira, e `demo restore` deve ritrovarlo lì qualche minuto dopo. Un
    predefinito che seguisse il primario cambierebbe nodo dopo un'elezione — cioè dopo
    l'Atto II — e la copia si troverebbe in un container e il restore la cercherebbe in
    un altro.
    """
    nodo = detto if detto is not None else servizi_di(bersaglio)[0]
    _controlla_nodo(nodo, bersaglio)
    return nodo


def _serve_il_primario(bersaglio: Bersaglio) -> typer.BadParameter:
    """Dall'host si arriva a un nodo solo, e il carico ha bisogno che sia quello giusto.

    Con `directConnection` il driver non sceglie: parla con il nodo pubblicato e basta.
    Se quel nodo è un secondario un `ping` riesce lo stesso — la lettura è ammessa — e il
    guasto comparirebbe soltanto alla prima scrittura, con il carico già partito e una
    collezione a metà. Meglio dirlo adesso.

    Il rimedio quasi sempre è aspettare: `mongo-rs-1` ha `priority: 2` e si riprende il
    ruolo da sé quando rientra, che è esattamente ciò che succede al termine dell'Atto II.
    """
    return typer.BadParameter(
        f"su «{bersaglio.nome}» il nodo pubblicato su localhost:{bersaglio.porta} non è "
        "il primario. Dall'host la scoperta è spenta (M-019): il carico scriverebbe su "
        "un secondario, dove ogni scrittura fallisce. Il primo membro ha priority 2 e "
        "riprende il ruolo da sé qualche secondo dopo essere rientrato — è ciò che "
        f"succede a fine Atto II — oppure si riparte pulito con `make reset-"
        f"{bersaglio.stack[:2]}`.",
        param_hint="--target",
    )


def _prossimo_passo(target: str, dove: Path, collezione: str) -> str:
    """La riga da dare dopo, già scritta. Dal palco è la differenza fra due comandi e uno.

    La collezione di carico ha la data nel nome e non si indovina; ricopiarla a mano
    davanti alla sala è il modo più prevedibile di sbagliare un comando. Qui esce già
    completa, e chi presenta la incolla.
    """
    return (
        f"prossimo: mongolab demo restore --target {target} "
        f"--from {dove} --collection {collezione}"
    )


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
