"""L'osservatore della topologia: la macchina a stati, e i due numeri del failover.

`TopologyWatcher` guarda il cluster attraverso `ClusterInspector`, confronta ciò che vede
con ciò che ricordava, e racconta la differenza emettendo eventi. Non sa che esiste
MongoDB, non sa che esiste pymongo, e non sa che esiste uno schermo: parla con tre porte,
e questo è ciò che permette di provare il failover in centesimi di secondo.

**Il caso che conta è un passaggio, non uno stato.** Primario → nessun primario →
primario **diverso**: sono tre fotogrammi, e nessuno dei tre da solo dice niente. È la
ragione per cui questo modulo tiene un ricordo (`vista`) invece di limitarsi a riferire
l'ultima lettura, ed è la ragione per cui `FakeInspector` riceve una *sequenza*.

**I due numeri stanno qui, non nella TUI.** La durata dell'interruzione e le scritture
perse sono ciò che giustifica l'esistenza di questa applicazione: sono l'unica cosa che
`mongosh` non sa mostrare. Calcolarli nel livello che disegna vorrebbe dire che non
esistono finché qualcuno non li guarda, e soprattutto che non sono provabili senza un
terminale. Stanno in `Bilancio`, che è un dato congelato come tutto il resto.

**Il tempo è una porta, e per questo la regola del §6.2 esiste davvero.** «Dopo 30 s
senza primario, smetti di ritentare» è rimasta una frase finché non c'è stato un `Clock`
da falsificare: nessuno mette in una suite veloce una prova che aspetta mezzo minuto, e
una prova che nessuno esegue non protegge niente. Con `FakeClock` la stessa regola si
verifica in millisecondi, e il valore atteso è **esatto** invece che una tolleranza.

**Il limite dichiarato: questo osservatore interroga, non ascolta.** La risoluzione della
misura è l'intervallo di campionamento — un'interruzione lunga 300 ms guardata ogni 250
può risultare di 250 o di 500, e l'errore è al massimo un intervallo. È accettabile per
la scena e non lo è per una misura: al Task 7 `SdamBridge` riceve gli stessi passaggi
dagli eventi SDAM del driver, cioè quando accadono, e la stessa `Interruzione` diventa
precisa. Le due strade convivono apposta — questa non ha bisogno di un driver per essere
provata, e resta la sola disponibile contro un `ClusterInspector` che non emette eventi.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Iterator

from mongolab.domain.eventi import (
    PrimaryWaitAbandoned,
    ServerStateChanged,
    TopologyChanged,
)
from mongolab.domain.modelli import DescrizioneTopologia, RuoloServer
from mongolab.domain.porte import Clock, ClusterInspector, EventSink

__all__ = [
    "Bilancio",
    "Interruzione",
    "TopologyWatcher",
]

UN_MILLISECONDO = timedelta(milliseconds=1)

INTERVALLO_PREDEFINITO_MS = 500.0
"""Due sguardi al secondo: abbastanza fitti perché la scena non salti, non di più.

Non è una misura, è una scelta di scena — e nel dubbio conviene ricordare che ogni
sguardo è un giro di rete verso il cluster. Chi vuole la precisione non abbassa questo
numero: usa il `SdamBridge` del Task 7, che non campiona affatto.
"""

PAZIENZA_PREDEFINITA_MS = 30_000.0
"""I 30 s del §6.2, scritti una volta sola e in millisecondi come tutto il resto.

Dal vivo si abbassa dalla riga di comando: mezzo minuto di sala in silenzio è lungo, e
l'evento che annuncia la resa porta entrambi i numeri proprio perché il rapporto fra
attesa e pazienza resti leggibile anche quando la pazienza non è quella del design.
"""


@dataclass(frozen=True, slots=True)
class Interruzione:
    """Il tempo in cui il client non ha visto nessun primario.

    Congelata come gli eventi, e per la stessa ragione: finisce dentro un riepilogo che
    attraversa i livelli, e chi la riceve non deve poterla correggere. Un'interruzione non
    si modifica, si sostituisce — chiuderla produce un oggetto nuovo.

    «Il client non ha visto» e non «il cluster non aveva»: sono due cose diverse, e la
    prima è l'unica che un'applicazione client possa onestamente misurare. Il cluster può
    aver eletto il primario un istante prima che qualcuno se ne accorgesse.
    """

    inizio: datetime
    primario_prima: str | None = None
    fine: datetime | None = None
    primario_dopo: str | None = None

    @property
    def chiusa(self) -> bool:
        return self.fine is not None

    @property
    def durata_ms(self) -> float | None:
        """La durata, oppure `None` finché l'interruzione è aperta.

        `None` e non zero. Uno zero direbbe «è durata niente» dove la verità è «non è
        ancora finita», ed è la peggiore risposta mancante perché ha la faccia di una
        misura: passa i controlli, entra nelle medie, e finisce su una slide.
        """
        if self.fine is None:
            return None
        return (self.fine - self.inizio) / UN_MILLISECONDO

    @property
    def e_un_failover(self) -> bool:
        """Vero solo se il primario di dopo è un **altro**.

        Un nodo che si riavvia in fretta produce un'interruzione senza elezione, e sulle
        slide è una scena diversa: «il primario è tornato» non è «ne è stato eletto un
        altro», e il Blocco 2 esiste per mostrare la seconda.
        """
        return (
            self.primario_prima is not None
            and self.primario_dopo is not None
            and self.primario_prima != self.primario_dopo
        )


@dataclass(frozen=True, slots=True)
class Bilancio:
    """I due numeri del failover, più quello che serve a leggerli.

    Le perdite sono **due**, non una con il segno. Confermate meno ritrovate sono
    scritture che il client credeva salve e non ci sono: è il numero che il talk esiste
    per mostrare. Ritrovate meno confermate sono scritture applicate dal server la cui
    conferma si è persa per strada mentre il primario cadeva: un fenomeno opposto, che
    con un solo campo firmato apparirebbe come «meno diciassette perse» — aritmetica
    sensata e cronaca sbagliata.
    """

    interruzione: Interruzione | None
    confermate: int
    ritrovate: int

    @property
    def scritture_perse(self) -> int:
        return max(0, self.confermate - self.ritrovate)

    @property
    def scritture_non_confermate(self) -> int:
        return max(0, self.ritrovate - self.confermate)

    @property
    def durata_interruzione_ms(self) -> float | None:
        """`None` quando non c'è stata interruzione, o quando è ancora aperta."""
        if self.interruzione is None:
            return None
        return self.interruzione.durata_ms


class TopologyWatcher:
    """Guarda la topologia, ricorda che cosa aveva visto, racconta la differenza."""

    def __init__(
        self,
        ispettore: ClusterInspector,
        orologio: Clock,
        sink: EventSink,
        *,
        intervallo_ms: float = INTERVALLO_PREDEFINITO_MS,
        pazienza_ms: float = PAZIENZA_PREDEFINITA_MS,
    ) -> None:
        if intervallo_ms <= 0:
            raise ValueError(
                f"l'intervallo fra due sguardi è positivo, ricevuto {intervallo_ms}"
            )
        if pazienza_ms <= 0:
            raise ValueError(f"la pazienza è positiva, ricevuta {pazienza_ms}")
        self._ispettore = ispettore
        self._orologio = orologio
        self._sink = sink
        self._intervallo_ms = intervallo_ms
        self._pazienza_ms = pazienza_ms

        self._vista: DescrizioneTopologia | None = None
        self._interruzione: Interruzione | None = None
        self._senza_primario_da: datetime | None = None
        self._ultimo_primario: str | None = None
        self._pazienza_esaurita = False

    @property
    def vista(self) -> DescrizioneTopologia | None:
        """L'ultima topologia vista, o `None` prima del primo sguardo."""
        return self._vista

    @property
    def interruzione(self) -> Interruzione | None:
        """L'interruzione in corso, o l'ultima chiusa, o `None` se non ce ne sono state."""
        return self._interruzione

    @property
    def pazienza_esaurita(self) -> bool:
        return self._pazienza_esaurita

    def guarda(self) -> DescrizioneTopologia:
        """Uno sguardo: interroga, confronta con il ricordo, emette, aggiorna il ricordo.

        Il primo sguardo non emette niente. Un `TopologyChanged` in cima alla cronaca
        direbbe che il client ha cambiato idea rispetto a un'idea che non aveva — un fatto
        falso, e proprio nel punto in cui chi legge decide quanto fidarsi del resto.
        """
        nuova = self._ispettore.topology()
        adesso = self._orologio.now()
        precedente = self._vista

        if precedente is not None and nuova != precedente:
            self._racconta(precedente, nuova, adesso)
        self._vista = nuova
        self._segna_il_primario(precedente, nuova, adesso)
        return nuova

    def segui(self, giri: int) -> Interruzione | None:
        """Guarda fino a `giri` volte, e restituisce l'interruzione se si chiude.

        `giri` è obbligatorio, e non è una scortesia verso chi chiama: un ciclo senza
        limite che aspetta un fatto che non arriva non fallisce, si **pianta**, e una
        suite piantata è peggio di una suite rossa perché non dice niente. Il limite si
        mette generoso e a fermare il ciclo è il fatto — la chiusura dell'interruzione,
        oppure la resa.

        L'attesa sta **fra** uno sguardo e l'altro, mai dopo l'ultimo: in una demo dal
        vivo sarebbe un quarto di secondo di schermo fermo alla fine di ogni scena.
        """
        if giri < 1:
            raise ValueError(f"il numero di giri è almeno 1, ricevuto {giri}")
        if self._pazienza_esaurita:
            return None

        aperta_all_inizio = self._interruzione
        for giro in range(giri):
            self.guarda()
            corrente = self._interruzione
            if (
                corrente is not None
                and corrente.chiusa
                and corrente is not aperta_all_inizio
            ):
                return corrente
            if self._arrenditi_se_e_ora():
                return None
            if giro < giri - 1:
                self._orologio.sleep(self._intervallo_ms / 1000.0)
        return None

    def bilancio(self, *, confermate: int, ritrovate: int) -> Bilancio:
        """Il riepilogo del failover: i due conteggi, e l'interruzione che li spiega.

        I conteggi arrivano da fuori — chi ha scritto sa quante ne ha confermate, chi ha
        riletto sa quante ne ha ritrovate — perché questo osservatore guarda la topologia
        e non i documenti. Tenerli insieme qui è ciò che rende «17 scritture perse in
        4,2 s senza primario» una frase sola invece di due numeri da accostare a mano.
        """
        if confermate < 0 or ritrovate < 0:
            raise ValueError(
                "i conteggi non sono negativi, ricevuti "
                f"confermate={confermate} e ritrovate={ritrovate}"
            )
        return Bilancio(
            interruzione=self._interruzione,
            confermate=confermate,
            ritrovate=ritrovate,
        )

    # --- Il racconto ---------------------------------------------------------------

    def _racconta(
        self,
        precedente: DescrizioneTopologia,
        nuova: DescrizioneTopologia,
        adesso: datetime,
    ) -> None:
        """Prima i server, poi la forma: la forma è la conseguenza, e si legge dopo."""
        for indirizzo, prima, dopo in self._ruoli_cambiati(precedente, nuova):
            self._sink.emit(
                ServerStateChanged(
                    istante=adesso,
                    indirizzo=indirizzo,
                    precedente=prima,
                    successivo=dopo,
                )
            )
        self._sink.emit(
            TopologyChanged(istante=adesso, precedente=precedente, successiva=nuova)
        )

    @staticmethod
    def _ruoli_cambiati(
        precedente: DescrizioneTopologia, nuova: DescrizioneTopologia
    ) -> Iterator[tuple[str, RuoloServer, RuoloServer]]:
        """Solo i server che hanno cambiato ruolo, in ordine di indirizzo.

        L'ordine è per indirizzo e non quello delle descrizioni, perché quello non è
        garantito: due letture del driver possono elencare gli stessi server in ordine
        diverso, e una cronaca che ne dipendesse sarebbe riproducibile *quasi sempre*.

        Un indirizzo che compare per la prima volta viene da `SCONOSCIUTO`, e uno che
        sparisce ci torna. Non da `IRRAGGIUNGIBILE`: quella è un'osservazione — il client
        ha provato e non ci è riuscito — mentre sparire dalla descrizione è l'assenza di
        un'osservazione. Scriverne una al posto dell'altra mette in cronaca un tentativo
        che nessuno ha fatto.
        """
        prima = {server.indirizzo: server.ruolo for server in precedente.server}
        dopo = {server.indirizzo: server.ruolo for server in nuova.server}
        for indirizzo in sorted(prima | dopo):
            vecchio = prima.get(indirizzo, RuoloServer.SCONOSCIUTO)
            corrente = dopo.get(indirizzo, RuoloServer.SCONOSCIUTO)
            if vecchio is not corrente:
                yield indirizzo, vecchio, corrente

    # --- L'interruzione ------------------------------------------------------------

    def _segna_il_primario(
        self,
        precedente: DescrizioneTopologia | None,
        nuova: DescrizioneTopologia,
        adesso: datetime,
    ) -> None:
        """Apre, chiude, o lascia com'è.

        L'interruzione si apre solo passando **da** un primario a nessun primario. Un
        client che si connette a primario già caduto non sa da quando manca, e aprirla al
        primo sguardo produrrebbe una durata più corta del vero — tanto più corta quanto
        più tardi si è guardato, cioè un numero che sbaglia verso il rassicurante. Meglio
        nessuna misura di una misura ottimista.

        Il momento in cui il primario è sparito si segna comunque, in
        `_senza_primario_da`: serve alla pazienza, che deve poter finire anche in una
        corsa cominciata a cluster già senza guida. In quel caso la resa dirà di non aver
        mai visto un primario da nominare, ed è la ragione per cui `ultimo_primario` è
        opzionale (ADR-0082).
        """
        primario = nuova.primario
        if primario is not None:
            aperta = self._interruzione
            if aperta is not None and not aperta.chiusa:
                self._interruzione = replace(
                    aperta, fine=adesso, primario_dopo=primario.indirizzo
                )
            self._senza_primario_da = None
            self._ultimo_primario = primario.indirizzo
            return

        if self._senza_primario_da is not None:
            return
        self._senza_primario_da = adesso
        if precedente is not None and precedente.ha_primario:
            self._interruzione = Interruzione(
                inizio=adesso, primario_prima=self._ultimo_primario
            )

    def _arrenditi_se_e_ora(self) -> bool:
        """Se la pazienza è finita, lo dice e smette. Altrove non tocca niente.

        La resa **non chiude l'interruzione**: aver smesso di aspettare non vuol dire che
        sia finita, e una durata scritta qui misurerebbe la pazienza di chi guarda invece
        del guasto. Non è nemmeno un giro andato male, è uno stato: riprendere richiede
        un `TopologyWatcher` nuovo, cioè una decisione di chi chiama.
        """
        senza_primario_da = self._senza_primario_da
        if senza_primario_da is None:
            return False

        adesso = self._orologio.now()
        atteso_ms = (adesso - senza_primario_da) / UN_MILLISECONDO
        if atteso_ms < self._pazienza_ms:
            return False

        self._pazienza_esaurita = True
        self._sink.emit(
            PrimaryWaitAbandoned(
                istante=adesso,
                atteso_ms=atteso_ms,
                pazienza_ms=self._pazienza_ms,
                ultimo_primario=self._ultimo_primario,
            )
        )
        return True
