"""Gli scenari: il copione del Blocco 2, scritto una volta e girato in due modi.

**Una sola implementazione, due modi.** `demo failover --step` mette in pausa prima di
ogni fase e riparte con Invio; senza `--step` la stessa identica scena gira da sola, ed è
così che si producono le registrazioni di riserva. La differenza fra il palco e il piano B
è una funzione passata a `esegui`, `Attesa`, che nel modo automatico non fa niente. Due
implementazioni — una «interattiva» e una «da registrare» — divergerebbero entro il primo
ritocco, e il piano B racconterebbe una storia diversa da quella provata.

**Perché lo scenario sta qui e non in `cli.py`.** Il §6.1 tiene fuori dall'applicazione
tutto ciò che è tecnologia, e la radice di composizione è l'unico posto che conosce le
classi concrete. Un copione scritto dentro un comando Typer sarebbe provabile solo
accendendo Docker: la sequenza di eventi che il Passo 4 del Task 13 chiede di verificare
richiederebbe un'elezione vera, cioè [V-031](../../../../docs/Sources.md#v-031) secondi a
ogni salvataggio. Qui la stessa sequenza si verifica in millisecondi.

**Il guasto entra da una porta.** Fermare un container è tecnologia, e lo scenario non
deve saperlo: riceve una `Regia` e le dice `ferma`. Il perché va oltre la pulizia formale
ed è scritto in `porte.py`: gli adattatori sono **due**, e sono diversi per una ragione
strutturale. Dall'host il guasto si provoca con un comando; dentro la rete Docker — dove
l'applicazione deve stare perché la scoperta della topologia funzioni
([M-019](../../../docs/Sources.md#m-019)) — il container non ha il socket del demone e non
può fermare nessuno. Lì la regia **annuncia** l'ordine e aspetta che un umano lo esegua.

**L'interruzione si deduce dagli eventi, non dai sondaggi.** `TopologyWatcher` guarda ogni
500 ms, e con lui la durata dell'interruzione — che è metà del titolo del Blocco 2 —
avrebbe una granularità di mezzo secondo. Gli eventi del ponte portano l'istante in cui il
**driver** ha saputo, al millisecondo, ed è la ragione per cui `CronometroInterruzione`
legge la stessa cronaca che finisce a schermo invece di aprire una seconda finestra sul
cluster (ADR-0096, e prima ancora ADR-0089, che di narratori ne aveva tolto uno).
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from pathlib import Path
import threading
from typing import Callable, Final

from mongolab.application.topologia import (
    INTERVALLO_PREDEFINITO_MS,
    Bilancio,
    Interruzione,
)
from mongolab.application.workload import (
    Continua,
    Genera,
    Riepilogo,
    WorkloadRunner,
    documento_progressivo,
)
from mongolab.domain.eventi import (
    BackupProgressed,
    Evento,
    FaseIniziata,
    TopologyChanged,
)
from mongolab.domain.modelli import Distribuzione, Documento, Piano, Progress
from mongolab.domain.porte import (
    BackupTool,
    Clock,
    ClusterInspector,
    DocumentStore,
    EventSink,
    QueryPlanner,
    Regia,
)

__all__ = [
    "Attesa",
    "Copione",
    "CopioneBackup",
    "CopioneRestore",
    "CopioneSharding",
    "CronometroInterruzione",
    "Drena",
    "EsitoBackup",
    "EsitoFailover",
    "EsitoRestore",
    "EsitoSharding",
    "ModoGuasto",
    "Ritmo",
    "ScenarioBackup",
    "ScenarioFailover",
    "ScenarioRestore",
    "ScenarioSharding",
    "senza_attesa",
    "sorveglia",
]


Drena = Callable[[], list[Evento]]
"""Come lo scenario prende gli eventi del driver, senza sapere da dove vengono.

Un alias di funzione e non una settima porta, per la stessa ragione per cui `Genera` e
`Legge` sono alias: la forma è **una funzione senza argomenti**, e un `Protocol` con un
metodo solo aggiungerebbe un nome da importare senza aggiungere un vincolo. Chi passa
`SdamBridge.drena` soddisfa il tipo, e `application` continua a non conoscere pymongo.
"""

Attesa = Callable[[FaseIniziata], None]
"""La pausa fra una fase e l'altra. È `--step`, ridotto alla sua essenza.

Riceve l'evento che annuncia la fase, e non una stringa: è la stessa cosa che la sala
legge a schermo un istante prima. Una pausa che annunciasse una fase diversa da quella
scritta sarebbe un inciampo dal vivo, e così è impossibile per costruzione.
"""


def senza_attesa(fase: FaseIniziata) -> None:
    """Il modo automatico: nessuna pausa. È il predefinito, e produce le registrazioni."""
    return None


class ModoGuasto(Enum):
    """Come si rompe il primario. Due modi, e la differenza è il Passo 3 del copione.

    `FERMA` spegne il processo: chi prova a connettersi riceve un rifiuto immediato, e il
    driver lo scopre in un battito. `SOSPENDI` congela il processo e lascia la porta TCP
    aperta: nessuno rifiuta niente, e il client scopre il guasto solo quando scade un
    timeout. Server morto e rete partizionata sono due guasti diversi, e il secondo è la
    parte che il pubblico non si aspetta.
    """

    FERMA = "ferma"
    SOSPENDI = "sospendi"


DURATA_CARICO_S: Final = 10.0
"""Quanto dura la prima fase, quella con il cluster sano. Serve a far vedere il ritmo
normale: senza un prima, il dopo non si legge."""

DURATA_ELEZIONE_S: Final = 25.0
"""Quanto si resta a guardare dopo il guasto. Più della forbice 8-10 s misurata da V-031,
perché la scena deve mostrare anche il **ritorno** del ritmo, non solo la sua caduta."""

DURATA_RECUPERO_S: Final = 15.0
"""Quanto si resta a guardare dopo il riavvio, mentre il nodo rientra nel replica set."""

TETTO_DUMP_S: Final = 300.0
"""Il tetto della fase del dump, e si spera che non serva mai.

A fermare il carico dev'essere il `mongodump` che finisce, non un cronometro: è tutta la
ragione per cui `WorkloadRunner.esegui` ha imparato `finche` al Task 14. Ma `finche` non
garantisce la terminazione — se il dump si pianta resta vero per sempre — e `esegui` per
questo esige comunque un limite. Cinque minuti: molto più dei 476 ms misurati contro lo
stack 02 con la collezione della demo ([M-045](../../../docs/Sources.md#m-045)), e
abbastanza poco da non lasciare il carico a scrivere per un'ora se qualcosa si blocca."""


@dataclass(frozen=True, slots=True)
class Copione:
    """I parametri della scena, in un oggetto solo perché si leggono insieme.

    Congelato come tutto ciò che attraversa i livelli: un copione che qualcuno potesse
    ritoccare a metà scena renderebbe la registrazione di riserva non riproducibile, che
    è precisamente ciò che una registrazione di riserva deve essere.

    `scritture` è l'alternativa alla durata, ed esiste per lo stesso motivo per cui esiste
    in `WorkloadRunner.esegui`: con un conteggio la corsa è **riproducibile**, con una
    durata è realistica. Dal palco si usa la durata; le prove usano il conteggio, e per
    questo non si piantano quando la macchina è lenta.
    """

    nodo: str
    modo: ModoGuasto = ModoGuasto.FERMA
    scritture: int | None = None
    carico_s: float = DURATA_CARICO_S
    elezione_s: float = DURATA_ELEZIONE_S
    recupero_s: float = DURATA_RECUPERO_S
    intervallo_ms: float = INTERVALLO_PREDEFINITO_MS


@dataclass(frozen=True, slots=True)
class EsitoFailover:
    """Che cosa resta da leggere dopo la scena.

    I tre riepiloghi restano **distinti** e non si sommano. Sommarli vorrebbe dire mediare
    i percentili di tre corse, che è un'operazione che non ha risposta giusta: un p95
    calcolato su tre insiemi di latenze incollati non è il p95 di niente. Distinti, invece,
    raccontano da soli la scena — il ritmo prima, il crollo durante, il ritorno dopo — che
    è esattamente ciò che la slide vuole mostrare.
    """

    fasi: tuple[str, ...]
    prima: Riepilogo
    durante: Riepilogo
    dopo: Riepilogo
    bilancio: Bilancio
    interruzioni: tuple[Interruzione, ...]

    @property
    def confermate(self) -> int:
        return self.bilancio.confermate

    @property
    def ritrovate(self) -> int:
        return self.bilancio.ritrovate

    @property
    def scritture_perse(self) -> int:
        return self.bilancio.scritture_perse

    @property
    def durata_interruzione_ms(self) -> float | None:
        """Il primo dei due numeri. `None` se il primario non è mai stato perso."""
        return self.bilancio.durata_interruzione_ms


class CronometroInterruzione:
    """L'interruzione dedotta dalla cronaca del driver, evento per evento.

    Legge solo i `TopologyChanged` perché è l'unico evento che porta **entrambi** gli
    estremi del passaggio, e perché è quello che il §6.3 assegna alla cronaca del failover.

    La trappola, e il motivo per cui questa classe esiste invece di tre righe dentro lo
    scenario: un client che si connette passa per «sconosciuta» e «replica set senza
    primario» prima di trovarne uno. Contare quel tratto aprirebbe l'interruzione
    all'istante della connessione, e il numero di testa del Blocco 2 diventerebbe il tempo
    di avviamento del client sommato all'elezione. Il cronometro si **arma** al primo
    primario visto: prima di allora non c'è niente che si possa perdere.
    """

    __slots__ = ("_interruzioni", "_ultimo_primario")

    def __init__(self) -> None:
        self._interruzioni: list[Interruzione] = []
        self._ultimo_primario: str | None = None

    def considera(self, evento: Evento) -> None:
        """Aggiorna la misura con un evento. Ignora tutto ciò che non è una topologia."""
        if not isinstance(evento, TopologyChanged):
            return
        primario = evento.successiva.primario
        if primario is None:
            self._apri(evento)
            return
        self._ultimo_primario = primario.indirizzo
        self._chiudi(evento, primario.indirizzo)

    def _apri(self, evento: TopologyChanged) -> None:
        if self._ultimo_primario is None:
            return
        if self._interruzioni and not self._interruzioni[-1].chiusa:
            return
        self._interruzioni.append(
            Interruzione(inizio=evento.istante, primario_prima=self._ultimo_primario)
        )

    def _chiudi(self, evento: TopologyChanged, indirizzo: str) -> None:
        if not self._interruzioni or self._interruzioni[-1].chiusa:
            return
        self._interruzioni[-1] = replace(
            self._interruzioni[-1], fine=evento.istante, primario_dopo=indirizzo
        )

    @property
    def interruzioni(self) -> tuple[Interruzione, ...]:
        """Tutte, in ordine. Una seconda interruzione durante la ripresa è un fatto."""
        return tuple(self._interruzioni)

    @property
    def prima(self) -> Interruzione | None:
        """Quella che chiude la scena: il guasto provocato dalla regia, non i suoi echi."""
        return self._interruzioni[0] if self._interruzioni else None


def sorveglia(
    drena: Drena,
    sink: EventSink,
    orologio: Clock,
    *,
    giri: int,
    intervallo_ms: float = INTERVALLO_PREDEFINITO_MS,
) -> None:
    """Guarda per `giri` volte: drena il ponte verso il sink, e fra uno e l'altro aspetta.

    È il ciclo che `watch` teneva dentro `cli.py` fino al Task 13. Spostarlo qui non è
    riordino: dentro la radice di composizione era provabile solo eseguendo il comando,
    cioè aprendo una connessione, e la regola delle attese — `giri - 1` e non `giri` —
    non aveva nessuna prova. Mezzo secondo speso dopo l'ultimo sguardo è mezzo secondo in
    cui la scena è finita e lo schermo è fermo.
    """
    if giri < 1:
        raise ValueError(f"i giri sono almeno uno, ricevuti {giri}")
    for giro in range(giri):
        for evento in drena():
            sink.emit(evento)
        if giro < giri - 1:
            orologio.sleep(intervallo_ms / 1000.0)


class ScenarioFailover:
    """L'Atto II del Blocco 2: carico, guasto, elezione, ripresa, recupero, bilancio.

    Sei fasi, e ciascuna si annuncia con un `FaseIniziata` **prima** di cominciare. Le
    prove asseriscono su quella sequenza, il palco la legge a schermo, e `--step` si ferma
    lì: un solo elenco di titoli serve a tre scopi, e nessuno dei tre può divergere dagli
    altri.

    L'ordine non è decorativo. Fermare il nodo dopo aver misurato darebbe zero millisecondi
    di interruzione e zero scritture perse — la cronaca di un failover che non è avvenuto,
    indistinguibile da un failover perfetto — e nessuno se ne accorgerebbe guardando lo
    schermo. È la ragione per cui `test_scenari.py` asserisce sugli ordini dati alla regia
    e non solo sui numeri che ne escono.

    L'archivio arriva **oltre** al generatore di carico, e sembra una ripetizione: il
    secondo è costruito sul primo. Non lo è, perché servono a due cose diverse in due
    momenti diversi. Il generatore scrive; l'archivio viene interrogato alla fine, a carico
    spento, per il conteggio di ciò che è **sopravvissuto**. Ricavarlo dal generatore
    vorrebbe dire aggiungere a `WorkloadRunner` un metodo che serve a un chiamante solo.
    """

    __slots__ = (
        "_archivio",
        "_copione",
        "_corsa",
        "_cronometro",
        "_drena",
        "_genera",
        "_orologio",
        "_regia",
        "_scarto",
        "_sink",
    )

    def __init__(
        self,
        archivio: DocumentStore,
        corsa: WorkloadRunner,
        regia: Regia,
        orologio: Clock,
        sink: EventSink,
        drena: Drena,
        *,
        copione: Copione,
        genera: Genera = documento_progressivo,
    ) -> None:
        self._archivio = archivio
        self._corsa = corsa
        self._regia = regia
        self._orologio = orologio
        self._sink = sink
        self._drena = drena
        self._copione = copione
        self._genera = genera
        self._cronometro = CronometroInterruzione()
        self._scarto = 0

    def esegui(self, *, attesa: Attesa = senza_attesa) -> EsitoFailover:
        """Gira la scena intera e restituisce i suoi numeri.

        `attesa` è l'unica differenza fra il palco e la registrazione di riserva.
        """
        copione = self._copione
        fasi: list[str] = []

        def annuncia(fase: str, descrizione: str) -> None:
            evento = FaseIniziata(self._orologio.now(), fase, descrizione)
            self._sink.emit(evento)
            fasi.append(fase)
            attesa(evento)

        rompe, ripara, verso = _verbi(copione.modo)

        annuncia("carico", "il carico gira contro il replica set sano")
        prima = self._con_carico(copione.carico_s)

        annuncia("guasto", f"{verso} {copione.nodo}")
        rompe(self._regia, copione.nodo)

        annuncia("elezione", "il carico continua mentre il replica set elegge")
        durante = self._con_carico(copione.elezione_s)

        annuncia("ripresa", f"rimetto in servizio {copione.nodo}")
        ripara(self._regia, copione.nodo)

        annuncia("recupero", "il carico continua mentre il nodo rientra")
        dopo = self._con_carico(copione.recupero_s)

        annuncia("bilancio", "confermate contro ritrovate")
        confermate = (
            prima.documenti_confermati
            + durante.documenti_confermati
            + dopo.documenti_confermati
        )
        bilancio = Bilancio(
            interruzione=self._cronometro.prima,
            confermate=confermate,
            ritrovate=self._archivio.count({}),
        )
        return EsitoFailover(
            fasi=tuple(fasi),
            prima=prima,
            durante=durante,
            dopo=dopo,
            bilancio=bilancio,
            interruzioni=self._cronometro.interruzioni,
        )

    def _con_carico(self, durata_s: float) -> Riepilogo:
        """Una fase con il carico acceso, drenando il ponte mentre gira.

        Il carico va su un thread e il drenaggio resta qui, ed è la stessa forma di
        `cli.mentre_disegna` per la stessa ragione: se drenasse il thread del carico, la
        cronaca dell'elezione arriverebbe a schermo **dopo** la fine della fase, cioè
        quando la scena è già passata. Il ciclo si ferma quando il carico si ferma, e non
        dopo un numero di giri calcolato: con un limite a conteggio nessuno sa quanto
        durerà, e un ciclo che finisse prima lascerebbe eventi in coda.
        """
        with ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="mongolab-carico"
        ) as pool:
            futuro = pool.submit(self._una_corsa, durata_s)
            while not futuro.done():
                self._raccogli()
                self._orologio.sleep(self._copione.intervallo_ms / 1000.0)
            # L'ultimo drenaggio è dopo la fine del carico apposta: gli eventi arrivati
            # nell'ultimo giro sono quelli che raccontano la fine della fase.
            self._raccogli()
            riepilogo = futuro.result()
        self._scarto += riepilogo.scritture
        return riepilogo

    def _una_corsa(self, durata_s: float) -> Riepilogo:
        """La corsa di una fase, con gli indici che riprendono da dove la precedente ha
        smesso.

        Lo scarto esiste perché le tre fasi sono tre chiamate a `esegui`, e ciascuna
        riparte da zero. Senza, la collezione finirebbe con tre serie di `indice`
        sovrapposte: il conteggio dei perduti resterebbe giusto — è una sottrazione fra
        conteggi — ma chiunque aprisse la collezione dopo la demo per **vedere** quali
        documenti mancano troverebbe tre documenti con lo stesso numero.
        """
        genera = self._genera
        scarto = self._scarto
        spostato: Genera = lambda indice: genera(indice + scarto)  # noqa: E731
        if self._copione.scritture is not None:
            return self._corsa.esegui(self._copione.scritture, genera=spostato)
        return self._corsa.esegui(durata_s=durata_s, genera=spostato)

    def _raccogli(self) -> None:
        """Un giro di drenaggio: al sink perché si veda, al cronometro perché si misuri."""
        for evento in self._drena():
            self._sink.emit(evento)
            self._cronometro.considera(evento)


def _verbi(
    modo: ModoGuasto,
) -> tuple[Callable[[Regia, str], None], Callable[[Regia, str], None], str]:
    """Quale coppia di verbi usa la scena, e come si annuncia la fase del guasto."""
    if modo is ModoGuasto.SOSPENDI:
        return (
            lambda regia, nodo: regia.sospendi(nodo),
            lambda regia, nodo: regia.risveglia(nodo),
            "congelo (irraggiungibile ma vivo)",
        )
    return (
        lambda regia, nodo: regia.ferma(nodo),
        lambda regia, nodo: regia.riavvia(nodo),
        "fermo",
    )


# --- L'Atto III: il backup a caldo ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Ritmo:
    """Un riepilogo e la finestra in cui è stato raccolto. Insieme fanno un throughput.

    `Riepilogo` da solo non basta: conta le scritture ma non sa in quanto tempo, e il
    numero che l'Atto III deve mostrare è **al secondo**. Tenerli separati e accostarli qui
    evita di aggiungere a `Riepilogo` una durata che le corse a conteggio non hanno.

    La finestra è misurata con l'orologio della scena, non chiesta al copione: il tetto
    dice quanto **al massimo**, e usarlo come denominatore darebbe un throughput diviso per
    cinque minuti quando il dump ne è durato mezzo secondo.
    """

    riepilogo: Riepilogo
    durata_s: float

    @property
    def documenti_al_secondo(self) -> float | None:
        """Il numero che va sulla slide. `None` se la finestra è nulla o negativa."""
        if self.durata_s <= 0:
            return None
        return self.riepilogo.documenti_confermati / self.durata_s

    @property
    def scritture_al_secondo(self) -> float | None:
        """L'altro verso dello stesso dato: operazioni invece di documenti.

        Con `--per-write 1` i due numeri coincidono; con un `insert_many` da cento
        documenti divergono di cento, e chi confronta con un benchmark altrui deve sapere
        quale dei due sta guardando.
        """
        if self.durata_s <= 0:
            return None
        return self.riepilogo.scritture / self.durata_s


@dataclass(frozen=True, slots=True)
class CopioneBackup:
    """I parametri dell'Atto III. Due durate e una destinazione.

    Manca `scritture`, che il copione del failover ha: qui non servirebbe a niente e
    confonderebbe. Delle due fasi, una sola potrebbe limitarsi a conteggio — quella del
    dump deve finire **quando finisce il dump**, e un conteggio la farebbe smettere prima o
    dopo. Un parametro che vale per metà scena è un parametro che qualcuno userà per
    l'altra metà.
    """

    destinazione: Path
    carico_s: float = DURATA_CARICO_S
    tetto_s: float = TETTO_DUMP_S
    intervallo_ms: float = INTERVALLO_PREDEFINITO_MS


@dataclass(frozen=True, slots=True)
class EsitoBackup:
    """I due ritmi accostati, che sono la tesi dell'Atto III messa alla prova.

    «Il dump non fa crollare il throughput» è una promessa del copione, e il Passo 1 del
    Task 14 chiede che si veda invece di affermarla. Si vede così: il ritmo di prima, il
    ritmo di durante, e il loro rapporto.
    """

    fasi: tuple[str, ...]
    prima: Ritmo
    durante: Ritmo
    destinazione: Path
    avanzamenti: tuple[Progress, ...]
    documenti: int

    @property
    def tenuta(self) -> float | None:
        """Quanto del ritmo di prima resta durante il dump. Uno è nessun calo.

        `None` quando il ritmo di prima è zero o sconosciuto: un rapporto con lo zero al
        denominatore non è «calo infinito», è un dato che non c'è.
        """
        prima = self.prima.documenti_al_secondo
        durante = self.durante.documenti_al_secondo
        if prima is None or durante is None or prima <= 0:
            return None
        return durante / prima

    @property
    def calo_percentuale(self) -> float | None:
        """La stessa cosa detta come la dice la slide. Negativo se il ritmo è salito."""
        tenuta = self.tenuta
        return None if tenuta is None else (1.0 - tenuta) * 100.0


class ScenarioBackup:
    """`demo backup-live`: carico, dump a carico acceso, bilancio.

    **Perché il carico e il dump devono coprire la stessa finestra.** Il numero che la
    scena mostra è una media, e una media si può diluire fino a nascondere qualsiasi cosa.
    Contro lo stack 02 il `mongodump` della collezione della demo dura 476 ms (M-045): se
    la fase durasse i venti secondi scelti a tavolino, il dump occuperebbe il due per cento
    del campione, e un crollo totale del throughput durante quel due per cento comparirebbe
    come un calo del due per cento. La promessa del copione risulterebbe verificata da una
    misura incapace di smentirla. Per questo il carico si ferma **quando si ferma il dump**,
    e non un istante dopo.

    **Chi fa che cosa, e su quale thread.** Il carico va sul pool, come in
    `ScenarioFailover`; il dump resta sul thread chiamante, che lo consuma avanzamento per
    avanzamento e fra uno e l'altro drena il ponte. Sono due e non tre perché il dump *è*
    un iteratore: consumarlo è già un ciclo, e metterlo su un thread suo vorrebbe dire
    aggiungere una coda per riportare qui gli avanzamenti che il thread chiamante ha già
    sotto mano.

    **`mongodump` non gira dentro l'applicazione.** Non è una scelta di questo modulo — lo
    scenario riceve un `BackupTool` e non sa dove esegua — ma è la ragione per cui la porta
    esiste in questa forma: i binari non stanno nell'immagine dell'applicazione e non ci
    staranno (M-044, ADR-0100), quindi il comando che li esegue entra nel nodo, e la riga
    per entrarci la costruisce `ComandiCompose.dentro`.
    """

    __slots__ = (
        "_archivio",
        "_copione",
        "_corsa",
        "_drena",
        "_genera",
        "_orologio",
        "_scarto",
        "_sink",
        "_strumento",
    )

    def __init__(
        self,
        archivio: DocumentStore,
        corsa: WorkloadRunner,
        strumento: BackupTool,
        orologio: Clock,
        sink: EventSink,
        drena: Drena,
        *,
        copione: CopioneBackup,
        genera: Genera = documento_progressivo,
    ) -> None:
        self._archivio = archivio
        self._corsa = corsa
        self._strumento = strumento
        self._orologio = orologio
        self._sink = sink
        self._drena = drena
        self._copione = copione
        self._genera = genera
        self._scarto = 0

    def esegui(self, *, attesa: Attesa = senza_attesa) -> EsitoBackup:
        """Gira la scena e restituisce i due ritmi. `attesa` è `--step`, come sempre."""
        copione = self._copione
        fasi: list[str] = []

        def annuncia(fase: str, descrizione: str) -> None:
            evento = FaseIniziata(self._orologio.now(), fase, descrizione)
            self._sink.emit(evento)
            fasi.append(fase)
            attesa(evento)

        annuncia("carico", "il carico gira, e nessuno sta copiando niente")
        prima = self._con_carico()

        annuncia("dump", f"copia a caldo verso {copione.destinazione}, a carico acceso")
        durante, avanzamenti = self._con_dump()

        annuncia("bilancio", "il ritmo di prima accanto al ritmo di durante")
        return EsitoBackup(
            fasi=tuple(fasi),
            prima=prima,
            durante=durante,
            destinazione=copione.destinazione,
            avanzamenti=avanzamenti,
            documenti=self._archivio.count({}),
        )

    def _con_carico(self) -> Ritmo:
        """La fase sana: il carico da solo, per il tempo scritto nel copione."""
        inizio = self._orologio.now()
        with ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="mongolab-carico"
        ) as pool:
            futuro = pool.submit(self._una_corsa, self._copione.carico_s, None)
            while not futuro.done():
                self._raccogli()
                self._orologio.sleep(self._copione.intervallo_ms / 1000.0)
            self._raccogli()
            riepilogo = futuro.result()
        return self._chiudi(riepilogo, inizio)

    def _con_dump(self) -> tuple[Ritmo, tuple[Progress, ...]]:
        """La fase interessante: il dump sul thread di qui, il carico sul pool.

        Lo spegnimento sta in un `finally` e non dopo il ciclo, ed è la riga che tiene in
        piedi il caso brutto: se il dump solleva — un `mongodump` che esce con uno, cioè
        `ComandoFallito` — il carico deve fermarsi **prima** che l'eccezione risalga. Senza,
        l'uscita dal `with` aspetterebbe il pool, il pool aspetterebbe il tetto, e l'errore
        arriverebbe a chi l'ha causato cinque minuti dopo il fatto: in sala, uno schermo
        fermo senza spiegazione.
        """
        finito = threading.Event()
        avanzamenti: list[Progress] = []
        inizio = self._orologio.now()
        with ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="mongolab-carico"
        ) as pool:
            futuro = pool.submit(self._una_corsa, self._copione.tetto_s, finito)
            try:
                for avanzamento in self._strumento.dump(self._copione.destinazione):
                    avanzamenti.append(avanzamento)
                    self._sink.emit(BackupProgressed(self._orologio.now(), avanzamento))
                    self._raccogli()
            finally:
                finito.set()
            self._raccogli()
            riepilogo = futuro.result()
        return self._chiudi(riepilogo, inizio), tuple(avanzamenti)

    def _chiudi(self, riepilogo: Riepilogo, inizio: datetime) -> Ritmo:
        """Aggiorna lo scarto degli indici e misura la finestra appena passata."""
        self._scarto += riepilogo.scritture
        return Ritmo(riepilogo, (self._orologio.now() - inizio).total_seconds())

    def _una_corsa(self, durata_s: float, finito: threading.Event | None) -> Riepilogo:
        """La corsa di una fase, con gli indici che riprendono da dove l'altra ha smesso.

        Lo scarto è lo stesso accorgimento di `ScenarioFailover`, e per la stessa ragione:
        due fasi sono due chiamate a `esegui`, ciascuna riparte da zero, e senza scarto la
        collezione finirebbe con due serie di `indice` sovrapposte.
        """
        genera = self._genera
        scarto = self._scarto
        spostato: Genera = lambda indice: genera(indice + scarto)  # noqa: E731
        finche: Continua | None = None
        if finito is not None:
            fermata = finito
            finche = lambda: not fermata.is_set()  # noqa: E731
        return self._corsa.esegui(durata_s=durata_s, finche=finche, genera=spostato)

    def _raccogli(self) -> None:
        """Un giro di drenaggio verso il sink. Qui non c'è nessun cronometro da nutrire:
        la topologia non cambia durante un dump, e se cambiasse sarebbe una notizia che va
        vista a schermo, non misurata."""
        for evento in self._drena():
            self._sink.emit(evento)


# --- L'Atto III, seconda metà: il restore e i due conteggi ------------------------------


@dataclass(frozen=True, slots=True)
class CopioneRestore:
    """Da dove si restaura e dove si scrive. Il secondo non è mai il primo.

    `database` è un database **di destinazione**, diverso da quello di partenza, e la
    ragione è che la scena si deve poter rifare: un restore sopra l'originale
    sovrascriverebbe proprio i documenti la cui assenza nella copia è ciò che l'Atto III
    mostra, e il secondo giro racconterebbe una storia diversa dal primo.
    """

    sorgente: Path
    database: str


@dataclass(frozen=True, slots=True)
class EsitoRestore:
    """I due conteggi accostati, e la loro differenza.

    **La differenza non è un errore, ed è il punto della scena.** Il dump è stato preso a
    caldo: `mongodump --oplog` porta via anche l'oplog della finestra, ma restaurare su un
    database diverso richiede di rinominare i namespace, e `--oplogReplay` con la rinomina
    è incompatibile (M-024 e la docstring di `SubprocessBackup.restore`). Ciò che manca
    è esattamente quanto è stato scritto **durante** il dump, ed è il prezzo di non aver
    fermato il servizio. Mostrarlo è metà della lezione; chiamarlo fallimento sarebbe
    l'altra metà, sbagliata.
    """

    fasi: tuple[str, ...]
    sorgente: Path
    destinazione: str
    documenti_origine: int
    documenti_destinazione: int
    avanzamenti: tuple[Progress, ...]

    @property
    def differenza(self) -> int:
        """Quanti documenti l'originale ha in più. Negativo sarebbe una notizia grossa."""
        return self.documenti_origine - self.documenti_destinazione

    @property
    def combaciano(self) -> bool:
        return self.differenza == 0


class ScenarioRestore:
    """`demo restore`: restaura la copia altrove e accosta i due conteggi.

    **Due archivi e non uno.** Il conteggio di partenza e quello di arrivo vengono da due
    database diversi, quindi da due `DocumentStore` diversi: la porta è per collezione, e
    un solo adattatore non può contare in due database. Costruirli è faccenda della radice
    di composizione, che è l'unica a sapere che dietro c'è un `MongoClient` solo.

    **Nessun `drena`, a differenza delle altre due scene.** Durante un restore la topologia
    non ha niente da raccontare, e un parametro aggiunto per simmetria è un parametro che
    qualcuno dovrà passare a vuoto. Se un giorno servisse — un restore che innesca
    un'elezione perché satura il primario — sarebbe una notizia che merita il suo ADR, non
    un argomento già lì per caso.
    """

    __slots__ = (
        "_copione",
        "_destinazione",
        "_orologio",
        "_origine",
        "_sink",
        "_strumento",
    )

    def __init__(
        self,
        origine: DocumentStore,
        destinazione: DocumentStore,
        strumento: BackupTool,
        orologio: Clock,
        sink: EventSink,
        *,
        copione: CopioneRestore,
    ) -> None:
        self._origine = origine
        self._destinazione = destinazione
        self._strumento = strumento
        self._orologio = orologio
        self._sink = sink
        self._copione = copione

    def esegui(self, *, attesa: Attesa = senza_attesa) -> EsitoRestore:
        """Restaura, poi conta. Le due fasi si annunciano come nelle altre scene."""
        copione = self._copione
        fasi: list[str] = []

        def annuncia(fase: str, descrizione: str) -> None:
            evento = FaseIniziata(self._orologio.now(), fase, descrizione)
            self._sink.emit(evento)
            fasi.append(fase)
            attesa(evento)

        annuncia("restore", f"da {copione.sorgente} verso il database {copione.database}")
        avanzamenti: list[Progress] = []
        for avanzamento in self._strumento.restore(copione.sorgente, copione.database):
            avanzamenti.append(avanzamento)
            self._sink.emit(BackupProgressed(self._orologio.now(), avanzamento))

        annuncia("verifica", "quanti ce n'erano, quanti ne sono tornati")
        return EsitoRestore(
            fasi=tuple(fasi),
            sorgente=copione.sorgente,
            destinazione=copione.database,
            documenti_origine=self._origine.count({}),
            documenti_destinazione=self._destinazione.count({}),
            avanzamenti=tuple(avanzamenti),
        )


# --- Il Blocco 3: lo stesso carico due volte, e i chunk che non si muovono ---------------


@dataclass(frozen=True, slots=True)
class CopioneSharding:
    """Le due collezioni, le due query, e quanto carico.

    **Due nomi di collezione e nessun `DocumentStore` in più.** I due archivi arrivano
    dentro i due `WorkloadRunner`, che è dove servono per scrivere; qui i nomi servono per
    **chiedere di loro** all'ispettore, che dopo ADR-0104 risponde per collezione. Sono la
    stessa collezione detta a due porte diverse, e tenerne il nome qui è ciò che impedisce
    a una scena di scrivere in una e fotografare l'altra.

    **I due filtri stanno nel copione e non nel codice della scena.** Quale query sia
    mirata dipende dalla chiave di shard, cioè da come è fatto lo stack, cioè da qualcosa
    che `application` non sa e non deve sapere. Scritti qui, cambiano con lo stack senza
    toccare la scena; scritti dentro `esegui`, sarebbero una costante vera per un solo
    `docker-compose.yml`.

    Non hanno un valore predefinito, e la mancanza è voluta: un filtro «ragionevole»
    scelto qui verrebbe usato contro uno stack con un'altra chiave, e la scena mostrerebbe
    due scatter-gather affermando che il primo è mirato.
    """

    intera: str
    sparsa: str
    mirato: Documento
    sparpagliato: Documento
    scritture: int | None = None
    carico_s: float = DURATA_CARICO_S


@dataclass(frozen=True, slots=True)
class EsitoSharding:
    """Le tre fotografie, i due carichi e i due piani. Tutto ciò che la scena mostra.

    `prima` e `dopo` sono la **stessa** collezione a due istanti, `intera` è l'altra: tre
    oggetti e non due, perché la scena del Blocco 3 fa due confronti diversi con lo stesso
    materiale — distribuita contro non distribuita, e distribuita prima contro dopo.
    """

    fasi: tuple[str, ...]
    intera: Distribuzione
    prima: Distribuzione
    dopo: Distribuzione
    carico_intera: Riepilogo
    carico_sparsa: Riepilogo
    mirata: Piano
    sparpagliata: Piano

    @property
    def confrontabile(self) -> bool:
        """Le due corse hanno scritto lo stesso numero di documenti?

        La decisione del PO è «lo stesso carico due volte», e due colonne affiancate lo
        danno per scontato. Se una delle due corse ha scritto meno — un archivio che
        rifiuta, un tentativo esaurito — la differenza fra le colonne non è più la chiave
        di shard, è il carico. Un booleano, e non un'eccezione: la scena continua, e chi
        disegna la schermata decide che cosa scriverci accanto.
        """
        return self.carico_intera.scritture == self.carico_sparsa.scritture

    @property
    def arrivi(self) -> tuple[tuple[str, int], ...]:
        """Quanti documenti sono arrivati su ciascuno shard **durante** il carico.

        La differenza fra la fotografia di dopo e quella di prima, ed è il numero che rende
        confrontabili le due colonne della scena. La collezione non distribuita nasce con
        il carico, quindi il suo totale **è** il carico; `lab.ordini` invece contiene già i
        ventimila documenti del seed, e accostare duemila a ventiduemila non confronta
        niente.

        Non è una raffinatezza: misurata su questi totali, una corsa finita per l'ottanta
        per cento su un solo shard risultava sbilanciata di **tre centesimi di punto**,
        cioè la schermata avrebbe dichiarato un equilibrio perfetto mentre il carico era
        tutto da una parte. Il seed diluisce qualunque squilibrio, e una misura che non può
        smentire la tesi non la sta verificando.

        Vuota se una delle due fotografie non è distribuita: la differenza fra i conteggi
        di una collezione sharded e quelli di una che non lo è non è un arrivo.
        """
        if not (self.prima.distribuita and self.dopo.distribuita):
            return ()
        prima = {conto.shard: conto.documenti for conto in self.prima.conti}
        return tuple(
            (conto.shard, conto.documenti - prima.get(conto.shard, 0))
            for conto in self.dopo.conti
        )

    @property
    def sbilancio(self) -> float | None:
        """Quanti punti percentuali separano lo shard più servito dal meno servito.

        Sugli **arrivi**, per la ragione scritta lì sopra. Zero è l'equilibrio. Punti e non
        un rapporto: «venti punti di distanza» si capisce senza spiegazioni, mentre «uno
        virgola cinque» chiede di ricordare che cosa sta sopra e che cosa sotto — e in sala
        nessuno lo ricorda.

        `None` in due casi, e nessuno dei due è uno zero. Meno di due shard, perché una
        distanza vuole due estremi. E **nessun arrivo**, che non è «distribuiti alla
        perfezione» ma «niente da ripartire»: è ciò che si vede se il carico fallisce del
        tutto, cioè precisamente il momento in cui uno zero stampato mentirebbe con la
        faccia del successo. Stessa regola di `Riepilogo.latenze`, che è `None` e non una
        fila di zeri.
        """
        arrivi = self.arrivi
        totale = sum(quanti for _, quanti in arrivi)
        if len(arrivi) < 2 or totale <= 0:
            return None
        quote = [100.0 * quanti / totale for _, quanti in arrivi]
        return max(quote) - min(quote)

    @property
    def chunk_in_piu(self) -> int | None:
        """Quanti chunk sono comparsi durante il carico. La risposta attesa è zero.

        Ed è la lezione, non un difetto: il balancer del 7.0 in questo laboratorio non
        migra mai — 1153 giri e nessuna migrazione ([M-049](../../../docs/Sources.md#m-049),
        ADR-0069) — e con una chiave hashed i chunk sono già distribuiti prima che arrivi
        la prima scrittura. Uno zero **mostrato** dice che la distribuzione era già decisa;
        uno zero taciuto sembrerebbe una funzione che manca.

        `None` se una delle due fotografie non è distribuita: la differenza fra i chunk di
        una collezione sharded e quelli di una che non lo è non è un numero, è un confronto
        fra due cose diverse.
        """
        if not (self.prima.distribuita and self.dopo.distribuita):
            return None
        return self.dopo.chunk - self.prima.chunk


class ScenarioSharding:
    """`demo sharding`: lo stesso carico due volte, e la chiave che fa la differenza.

    **Perché due volte.** Mostrare una collezione distribuita che si riempie in modo
    uniforme non dimostra niente da solo: chi guarda non ha visto l'alternativa, e «i
    documenti si sono divisi» resta un'affermazione. Accanto, lo stesso identico carico su
    una collezione che nessuno ha distribuito finisce tutto su uno shard, e la differenza
    fra le due colonne ha una causa sola — `shardCollection` — perché tutto il resto è
    uguale per costruzione. È la decisione del PO per il Blocco 3, e costa il tempo di una
    seconda corsa.

    **Identico vuol dire identico.** Le due corse partono entrambe dall'indice zero, senza
    lo scarto che `ScenarioFailover` e `ScenarioBackup` portano fra le loro fasi. Là le
    fasi si susseguono nella **stessa** collezione e senza scarto gli `indice` si
    sovrapporrebbero; qui le collezioni sono due, e ripartire da zero è precisamente ciò
    che rende i due carichi lo stesso carico.

    **Nessuno cancella niente.** Il carico distribuito va in `lab.ordini`, cioè nella
    collezione del seed, ed è ancora la decisione del PO. Non c'è un `delete` in questa
    classe e non ci sarà: la pulizia è di `tools/reset-demo.sh`, come stabilito da
    ADR-0088, e un quinto metodo su `DocumentStore` che esiste solo per la scena sarebbe
    una porta allargata per una comodità.

    **Nessun `drena`**, per la stessa ragione di `ScenarioRestore`: qui la topologia non
    ha niente da raccontare, e un parametro aggiunto per simmetria è un parametro che
    qualcuno dovrà passare a vuoto.

    **Il carico non gira su un pool.** Nelle altre due scene un thread serviva perché
    qualcos'altro doveva succedere insieme — l'elezione, il dump. Qui le fasi sono in
    fila: si scrive, poi si guarda. Un thread aggiungerebbe una sincronizzazione per
    ottenere ciò che una chiamata dopo l'altra ottiene da sola.
    """

    __slots__ = (
        "_copione",
        "_corsa_intera",
        "_corsa_sparsa",
        "_genera",
        "_ispettore",
        "_orologio",
        "_pianificatore",
        "_sink",
    )

    def __init__(
        self,
        ispettore: ClusterInspector,
        pianificatore: QueryPlanner,
        corsa_intera: WorkloadRunner,
        corsa_sparsa: WorkloadRunner,
        orologio: Clock,
        sink: EventSink,
        *,
        copione: CopioneSharding,
        genera: Genera = documento_progressivo,
    ) -> None:
        self._ispettore = ispettore
        self._pianificatore = pianificatore
        self._corsa_intera = corsa_intera
        self._corsa_sparsa = corsa_sparsa
        self._orologio = orologio
        self._sink = sink
        self._copione = copione
        self._genera = genera

    def esegui(self, *, attesa: Attesa = senza_attesa) -> EsitoSharding:
        """Gira la scena. `attesa` è `--step`, come nelle altre due."""
        copione = self._copione
        fasi: list[str] = []

        def annuncia(fase: str, descrizione: str) -> None:
            evento = FaseIniziata(self._orologio.now(), fase, descrizione)
            self._sink.emit(evento)
            fasi.append(fase)
            attesa(evento)

        annuncia("riposo", f"com'è distribuita {copione.sparsa} prima che qualcuno scriva")
        prima = self._ispettore.shard_distribution(copione.sparsa)

        annuncia(
            "non-distribuita",
            f"il carico su {copione.intera}, che nessuno ha distribuito",
        )
        carico_intera = self._una_corsa(self._corsa_intera)
        intera = self._ispettore.shard_distribution(copione.intera)

        annuncia(
            "distribuita",
            f"lo stesso carico su {copione.sparsa}, che ha una chiave di shard",
        )
        carico_sparsa = self._una_corsa(self._corsa_sparsa)
        dopo = self._ispettore.shard_distribution(copione.sparsa)

        annuncia("piani", "la stessa domanda a un solo shard e poi a tutti")
        mirata = self._pianificatore.explain(copione.mirato)
        sparpagliata = self._pianificatore.explain(copione.sparpagliato)

        annuncia("bilancio", "le due colonne accostate, e i chunk che non si sono mossi")
        return EsitoSharding(
            fasi=tuple(fasi),
            intera=intera,
            prima=prima,
            dopo=dopo,
            carico_intera=carico_intera,
            carico_sparsa=carico_sparsa,
            mirata=mirata,
            sparpagliata=sparpagliata,
        )

    def _una_corsa(self, corsa: WorkloadRunner) -> Riepilogo:
        """Una delle due corse. Conteggio **oppure** durata, come in `WorkloadRunner`."""
        copione = self._copione
        if copione.scritture is not None:
            return corsa.esegui(copione.scritture, genera=self._genera)
        return corsa.esegui(durata_s=copione.carico_s, genera=self._genera)
