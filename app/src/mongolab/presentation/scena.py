"""Che cosa mostra una schermata, senza sapere come si disegna.

`Scena` è la metà di `RichTui` che non conosce Rich: accetta eventi da qualunque thread,
li tiene in coda, e quando qualcuno la fa **assorbire** aggiorna lo stato che lo schermo
legge. Fuori da qui restano il disegno e il ciclo, che sono venti righe.

**Perché la divisione sta esattamente in questo punto.** Il piano vieta di provare
`RichTui`, e ha ragione: provare il disegno significa provare Rich. Ma il grosso di ciò
che la presentazione fa non è disegnare — è accettare eventi da un thread e cambiare
stato in un altro, che è la parte in cui si sbaglia. Un divieto di provare qualcosa si
onora spostando altrove ciò che va provato, non rinunciando a provarlo.

**Il patto di [ADR-0019](../../../../docs/Decision.md#adr-0019), qui dentro.** `emit`
mette in coda e ritorna: non tocca lo stato, non disegna, non prende lucchetti. Tutto il
resto succede in `assorbi`, che gira sul thread che disegna. È la ragione per cui in
questo modulo non compare nessun `Lock`: l'unico stato condiviso è la `queue.Queue`, che
i lucchetti li ha già dentro.
"""

import queue
from collections import deque
from dataclasses import dataclass, replace

from mongolab.domain.eventi import (
    BackupProgressed,
    Evento,
    LatencySampled,
    RetryAttempted,
    TopologyChanged,
    WriteFailed,
    WriteSucceeded,
)
from mongolab.domain.modelli import DescrizioneTopologia, Progress
from mongolab.presentation.righe import COLONNE_SALA, RIGHE_CRONACA, riga

__all__ = ["Conteggi", "Scena"]


@dataclass(frozen=True, slots=True)
class Conteggi:
    """I numeri che stanno nell'intestazione.

    Congelato come tutto il resto, e sostituito invece che modificato: chi legge
    `scena.conteggi` mentre `assorbi` lavora ottiene una fotografia coerente e non un
    oggetto a metà. Non è una difesa contro un secondo thread — nessun secondo thread
    legge — ma contro l'errore di scriverne uno domani.

    **Non ci sono i due numeri del failover.** Durata dell'interruzione e scritture perse
    si calcolano in `application/topologia.py`, e restano lì: un numero calcolato dal
    livello che disegna non esiste finché qualcuno non lo guarda, e soprattutto non è
    provabile senza un terminale.
    """

    scritture: int = 0
    documenti: int = 0
    fallimenti: int = 0
    ritentativi: int = 0
    campioni: int = 0
    ultima_latenza_ms: float | None = None


class Scena:
    """Lo stato che una schermata mostra, ricostruito dal solo flusso di eventi.

    Soddisfa `EventSink` per tipizzazione strutturale, e la cosa è voluta: chi vuole i
    conteggi senza lo schermo — una prova, una misura del Task 16 — usa questa e basta.
    """

    def __init__(
        self,
        *,
        righe_cronaca: int = RIGHE_CRONACA,
        larghezza: int | None = COLONNE_SALA,
    ) -> None:
        self._coda: queue.Queue[Evento] = queue.Queue()
        self._cronaca: deque[str] = deque(maxlen=righe_cronaca)
        self._conteggi = Conteggi()
        self._topologia: DescrizioneTopologia | None = None
        self._avanzamento: Progress | None = None
        self._assorbiti = 0
        self._larghezza = larghezza

    # --- Il lato di chi produce: da qualunque thread -----------------------------------

    def emit(self, evento: Evento) -> None:
        """Mette in coda e ritorna. Non tocca niente di ciò che lo schermo legge."""
        self._coda.put(evento)

    # --- Il lato di chi disegna: un thread solo ----------------------------------------

    def assorbi(self) -> int:
        """Svuota la coda dentro lo stato, e dice quanti eventi ha assorbito.

        Non aspetta: su una coda vuota ritorna zero. Un `assorbi` che bloccasse
        trasformerebbe il ciclo di disegno in un'attesa, cioè rimetterebbe il disegno
        alla mercé del driver — il verso di dipendenza che ADR-0019 ha invertito. Chi
        chiama decide il ritmo, e lo decide dormendo fra un giro e l'altro.
        """
        quanti = 0
        while True:
            try:
                evento = self._coda.get_nowait()
            except queue.Empty:
                break
            self._applica(evento)
            quanti += 1
        self._assorbiti += quanti
        return quanti

    @property
    def in_coda(self) -> int:
        """Quanti eventi aspettano. È il numero che dice se il disegno sta al passo."""
        return self._coda.qsize()

    @property
    def assorbiti(self) -> int:
        """Quanti ne sono passati in tutto, da quando la scena è aperta."""
        return self._assorbiti

    @property
    def cronaca(self) -> tuple[str, ...]:
        """Le ultime righe, dalla più vecchia alla più recente.

        Tagliate dal fondo perché una scena è **il presente**: durante un failover conta
        l'ultima decina di secondi, non i primi. Chi vuole tutto usa `PlainSink`, che non
        butta niente ed è fatto apposta per essere riletto dopo.
        """
        return tuple(self._cronaca)

    @property
    def conteggi(self) -> Conteggi:
        return self._conteggi

    @property
    def topologia(self) -> DescrizioneTopologia | None:
        """L'ultima topologia vista, o `None` se nessun evento l'ha ancora detta."""
        return self._topologia

    @property
    def avanzamento(self) -> Progress | None:
        return self._avanzamento

    # --- La riduzione -------------------------------------------------------------------

    def _applica(self, evento: Evento) -> None:
        self._cronaca.append(riga(evento, larghezza=self._larghezza))
        match evento:
            case WriteSucceeded():
                self._conteggi = replace(
                    self._conteggi,
                    scritture=self._conteggi.scritture + 1,
                    documenti=self._conteggi.documenti + evento.documenti,
                )
            case WriteFailed():
                self._conteggi = replace(
                    self._conteggi, fallimenti=self._conteggi.fallimenti + 1
                )
            case RetryAttempted():
                self._conteggi = replace(
                    self._conteggi, ritentativi=self._conteggi.ritentativi + 1
                )
            case LatencySampled():
                self._conteggi = replace(
                    self._conteggi,
                    campioni=self._conteggi.campioni + 1,
                    ultima_latenza_ms=evento.durata_ms,
                )
            case TopologyChanged():
                self._topologia = evento.successiva
            case BackupProgressed():
                self._avanzamento = evento.avanzamento
            case _:
                # `ServerStateChanged`, `ChunkMigrated`, `PrimaryWaitAbandoned`: la riga
                # di cronaca è tutta la loro resa, e non c'è nessun contatore da toccare.
                # Il passaggio di ruolo di un server arriva già dentro la topologia.
                pass
