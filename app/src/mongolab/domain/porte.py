"""Le sei porte: le cinque del §6.2, più `Regia` (ADR-0095).

**Strutturali, non nominali.** Un doppio soddisfa una porta perché ha i metodi giusti,
senza ereditarla e senza registrarsi da nessuna parte. Il vantaggio non è risparmiare una
riga di `class X(Porta)`: è che il verso della dipendenza resta quello giusto anche nei
test. `InMemoryStore` vive in `tests/` e non ha bisogno di importare il dominio per
conformarsi — è il dominio a descrivere la forma, e chiunque l'abbia va bene.

Il prezzo è che la conformità non si vede a occhio, e a runtime un doppio con una firma
sbagliata si scopre solo quando una prova fallisce per un motivo che sembra un altro. Per
questo `mypy --strict` non è negoziabile in questo progetto: è l'unico posto in cui quella
conformità è verificata, e senza di lui `Protocol` sarebbe documentazione.

Le porte sono `@runtime_checkable` per permettere a una prova di mostrare che un oggetto
incompleto **non** passa. Attenzione al limite, che vale la pena conoscere: `isinstance`
contro un `Protocol` guarda i **nomi** dei metodi, non le firme. Un doppio con
`insert_many(self)` senza argomenti supera `isinstance` e viene bocciato da mypy. Il
controllo statico è il vero guardiano; quello a runtime serve a scrivere la prova che lo
racconta.
"""

from datetime import datetime
from pathlib import Path
from typing import Iterator, Mapping, Protocol, Sequence, runtime_checkable

from mongolab.domain.eventi import Evento
from mongolab.domain.modelli import (
    ContoShard,
    DescrizioneTopologia,
    Documento,
    Progress,
)

__all__ = [
    "BackupTool",
    "Clock",
    "ClusterInspector",
    "DocumentStore",
    "EventSink",
    "Regia",
]


@runtime_checkable
class DocumentStore(Protocol):
    """Leggere e scrivere documenti, senza sapere che c'è MongoDB dall'altra parte."""

    def insert_many(self, documenti: Sequence[Documento]) -> int:
        """Inserisce i documenti e restituisce quanti ne ha confermati il server.

        Il valore di ritorno è un conteggio e non un elenco di identificatori perché è
        quello che serve al numero della scena: confermate contro ritrovate. Un
        inserimento parziale si distingue da uno completo confrontando con la lunghezza
        di `documenti`, e chi chiama sa entrambe.
        """
        ...

    def find_page(
        self, filtro: Documento, salta: int = 0, quanti: int = 20
    ) -> tuple[Documento, ...]:
        """Una pagina di risultati. Tupla, perché il chiamante non deve poterla alterare."""
        ...

    def count(self, filtro: Documento) -> int: ...

    def aggregate(self, pipeline: Sequence[Documento]) -> tuple[Documento, ...]: ...


@runtime_checkable
class ClusterInspector(Protocol):
    """Guardare com'è fatto il cluster e come sta."""

    def topology(self) -> DescrizioneTopologia:
        """La topologia **come la vede il client**, non come la dichiara il cluster.

        È la differenza che il Blocco 2 mostra: durante un'elezione le due cose divergono
        per qualche secondo, e l'unica che spiega perché una scrittura fallisce è questa.
        """
        ...

    def server_status(self) -> Mapping[str, object]:
        """Il documento grezzo di `serverStatus`, non interpretato.

        Restituirlo così invece che in un modello nostro è una scelta: la pagina
        `statistiche-monitoraggio.md` del Task 17 spiega **quali campi guardare**, e un
        modello che ne seleziona cinque deciderebbe la risposta al posto del lettore.
        """
        ...

    def db_stats(self) -> Mapping[str, object]: ...

    def shard_distribution(self) -> tuple[ContoShard, ...]:
        """Dove stanno davvero i documenti. Vuota su ciò che non è uno sharded cluster."""
        ...


@runtime_checkable
class BackupTool(Protocol):
    """Dump e restore come operazioni lunghe che raccontano come procedono."""

    def dump(self, destinazione: Path) -> Iterator[Progress]:
        """Avvia il dump e produce l'avanzamento **mentre** procede.

        Un iteratore e non una lista: l'Atto III mostra il throughput che non crolla
        durante il dump, e una lista sarebbe disponibile solo a dump finito, cioè quando
        la scena è già passata.
        """
        ...

    def restore(self, origine: Path, destinazione_db: str) -> Iterator[Progress]:
        """Come `dump`, e per la stessa ragione.

        Il design nomina solo il tipo di ritorno di `dump`; qui `restore` ha la stessa
        forma perché il copione mostra anche il restore mentre avviene, e due firme
        diverse per due operazioni simmetriche costringerebbero `presentation` a due
        strade dove ne basta una.
        """
        ...


@runtime_checkable
class EventSink(Protocol):
    """Dove finiscono gli eventi. Rich, testo semplice, o niente."""

    def emit(self, evento: Evento) -> None:
        """Accetta l'evento e ritorna.

        Chi chiama può essere un callback di pymongo, quindi questo metodo non deve
        bloccare (ADR-0019). Un sink che ha bisogno di tempo — disegnare, scrivere su
        disco — mette in coda e lascia che sia il proprio ciclo a spendere quel tempo.
        """
        ...


@runtime_checkable
class Clock(Protocol):
    """L'orologio, come porta.

    Esiste per provare in millisecondi comportamenti definiti in decine di secondi: la
    regola «dopo 30 s senza primario smetti di ritentare» ha una prova che dura un
    battito di ciglia, e senza questa porta resterebbe una frase nel design.
    """

    def now(self) -> datetime:
        """L'istante attuale. Le implementazioni vere lo restituiscono con fuso orario.

        Un istante senza fuso è ambiguo appena esce dal processo che l'ha creato, e
        questi istanti finiscono in una registrazione asciinema che qualcuno leggerà a
        giorni di distanza.
        """
        ...

    def sleep(self, secondi: float) -> None: ...


@runtime_checkable
class Regia(Protocol):
    """Chi fa accadere il guasto, senza che lo scenario sappia come (ADR-0095).

    I quattro verbi sono due coppie, e la differenza fra le coppie **è** il Blocco 2.
    `ferma`/`riavvia` spengono il processo: chi prova a connettersi riceve un rifiuto
    immediato. `sospendi`/`risveglia` lasciano il processo vivo e lo congelano: nessuno
    rifiuta niente, la porta TCP resta aperta, e il client scopre il guasto solo quando
    scade un timeout. Server morto e rete partizionata sono due guasti diversi, e un
    dominio che li chiamasse allo stesso modo non potrebbe raccontarne la differenza.

    Nessun metodo nomina Docker, e non è pulizia formale: gli adattatori sono due, e sono
    diversi per una ragione strutturale. Dall'host il guasto si provoca con un comando;
    dentro la rete Docker — dove l'applicazione deve stare perché la scoperta della
    topologia funzioni (M-019) — il container non ha il socket del demone e **non può**
    fermare un altro container. Lì la regia annuncia l'ordine e aspetta che un umano lo
    esegua. Lo scenario è lo stesso in entrambi i casi: è l'unica cosa che permette a
    `demo failover` di girare sia dal palco sia dentro una registrazione.

    `nodo` è il nome logico del membro — `mongo-1`, non `02-replicaset-mongo-1-1`. La
    traduzione in ciò che Docker vuole sentirsi dire appartiene all'adattatore.
    """

    def ferma(self, nodo: str) -> None:
        """Spegne il nodo. Al ritorno il processo non c'è più: connessione rifiutata."""
        ...

    def riavvia(self, nodo: str) -> None:
        """Rimette in piedi un nodo fermato. Non attende che sia di nuovo nel replica set.

        L'attesa non sta qui perché chi sa dire «è tornato» è l'osservatore della
        topologia, non chi ha dato l'ordine. Metterla qui costringerebbe ogni adattatore
        ad avere un client MongoDB, e la porta si trascinerebbe dietro il driver.
        """
        ...

    def sospendi(self, nodo: str) -> None:
        """Congela il nodo lasciandolo vivo: irraggiungibile, ma non morto."""
        ...

    def risveglia(self, nodo: str) -> None:
        """Scongela un nodo sospeso. Il processo riprende da dov'era, senza riavvio."""
        ...
