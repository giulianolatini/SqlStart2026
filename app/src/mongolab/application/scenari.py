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
from enum import Enum
from typing import Callable, Final

from mongolab.application.topologia import (
    INTERVALLO_PREDEFINITO_MS,
    Bilancio,
    Interruzione,
)
from mongolab.application.workload import (
    Genera,
    Riepilogo,
    WorkloadRunner,
    documento_progressivo,
)
from mongolab.domain.eventi import Evento, FaseIniziata, TopologyChanged
from mongolab.domain.porte import Clock, DocumentStore, EventSink, Regia

__all__ = [
    "Attesa",
    "Copione",
    "CronometroInterruzione",
    "Drena",
    "EsitoFailover",
    "ModoGuasto",
    "ScenarioFailover",
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
