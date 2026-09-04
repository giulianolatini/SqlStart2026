"""I dieci eventi del §6.3. Immutabili, e con l'istante come campo esplicito.

Il design ne elencava **otto**. Il nono, `PrimaryWaitAbandoned`, è arrivato al Task 6 di
`feature/04` con ADR-0082: la regola «dopo tanto senza primario, smetti di ritentare»
esisteva come frase dal §6.2, e nessuno degli otto sapeva raccontarne l'esito senza
mentire. Il decimo, `FaseIniziata`, è arrivato al Task 13 con ADR-0094, ed è di specie
diversa: non racconta un fatto del cluster ma un fatto **dello scenario**. Il §6.3 non si
riscrive: gli ADR lo emendano, e la guardia in `test_dominio.py` conta dieci.

**Immutabili non per eleganza.** Un evento nasce dentro un callback di pymongo, che gira
sul thread del driver, e viene letto dal ciclo di disegno, che gira sul thread
principale (ADR-0019). Un oggetto congelato rende la coda un punto di **consegna**: chi
riceve non può cambiare ciò che il mittente ha detto, e chi ha inviato non può cambiarlo
sotto gli occhi di chi legge. Con un oggetto mutabile la coda tornerebbe a essere
condivisione di stato, e servirebbe un lock proprio nel punto in cui ADR-0019 vieta di
metterne uno.

**L'istante è un campo, non una chiamata.** Nessun evento legge l'orologio dentro di sé:
lo riceve da chi lo costruisce, che a sua volta lo prende dal `Clock`. È la condizione
che rende riproducibile la cronaca del failover in una prova — con `FakeClock` il valore
atteso è **esatto**, e l'asserzione non degrada in una tolleranza. È anche la condizione
perché l'istante sia quello in cui il fatto è **accaduto** e non quello in cui qualcuno
si è ricordato di registrarlo: fra i due, sotto carico, passa proprio la latenza che si
sta misurando.
"""

from dataclasses import dataclass
from datetime import datetime

from mongolab.domain.modelli import (
    DescrizioneTopologia,
    Progress,
    RuoloServer,
)

__all__ = [
    "BackupProgressed",
    "ChunkMigrated",
    "Evento",
    "FaseIniziata",
    "LatencySampled",
    "PrimaryWaitAbandoned",
    "RetryAttempted",
    "ServerStateChanged",
    "TopologyChanged",
    "WriteFailed",
    "WriteSucceeded",
]


@dataclass(frozen=True, slots=True)
class Evento:
    """Ciò che ogni evento ha: il momento in cui è accaduto.

    La base esiste per dare a `EventSink.emit` un tipo solo da accettare. Non porta
    comportamento: un evento è un fatto, e i fatti non sanno rendersi a schermo — quello
    è mestiere di `presentation`, ed è la ragione per cui il nucleo non conosce Rich
    (ADR-0007).
    """

    istante: datetime


@dataclass(frozen=True, slots=True)
class WriteSucceeded(Evento):
    """Scritture confermate dal server.

    `documenti` è un conteggio e non un elenco di chiavi: le scritture perse si misurano
    confrontando il totale confermato con quello ritrovato dopo, che è il metodo con cui
    `feature/02` ha già prodotto il numero del failover (V-033). Portare le chiavi
    costerebbe memoria proporzionale al carico dentro oggetti che attraversano una coda.
    """

    documenti: int
    durata_ms: float


@dataclass(frozen=True, slots=True)
class WriteFailed(Evento):
    """Una scrittura rifiutata o non conclusa.

    `tipo_errore` è il nome della classe di errore del driver, tenuto come **testo**: il
    dominio non importa pymongo, e per la scena serve distinguere un rifiuto da un
    timeout, non ricostruire la gerarchia delle eccezioni.
    """

    tipo_errore: str
    motivo: str
    documenti: int = 0


@dataclass(frozen=True, slots=True)
class RetryAttempted(Evento):
    """Un nuovo tentativo dopo un fallimento."""

    tentativo: int
    attesa_ms: float
    motivo: str


@dataclass(frozen=True, slots=True)
class LatencySampled(Evento):
    """Una misura di durata di una singola operazione.

    Separata da `WriteSucceeded` perché si campiona anche ciò che non scrive — le letture
    dell'Atto III, e gli heartbeat — e perché l'aggregazione in percentili vuole un flusso
    di campioni, non un sottoprodotto di un altro evento.
    """

    operazione: str
    durata_ms: float


@dataclass(frozen=True, slots=True)
class TopologyChanged(Evento):
    """Il client ha cambiato idea sulla forma del cluster.

    Porta **entrambe** le descrizioni: senza la precedente, chi legge la cronaca vede
    dove si è arrivati e non da dove, e la frase «il primario non c'è più» diventa
    indistinguibile da «il primario non c'era».
    """

    precedente: DescrizioneTopologia
    successiva: DescrizioneTopologia


@dataclass(frozen=True, slots=True)
class ServerStateChanged(Evento):
    """Un singolo server ha cambiato ruolo agli occhi del client."""

    indirizzo: str
    precedente: RuoloServer
    successivo: RuoloServer


@dataclass(frozen=True, slots=True)
class BackupProgressed(Evento):
    """Il dump o il restore sono andati avanti."""

    avanzamento: Progress


@dataclass(frozen=True, slots=True)
class ChunkMigrated(Evento):
    """Il balancer ha spostato un chunk da uno shard a un altro.

    È l'unico evento degli otto che al Task 15 potrebbe risultare **non osservabile dal
    client**: un client parla con `mongos`, e la migrazione è una faccenda fra shard e
    config server. Se si scoprisse che non lo è, la conseguenza è una voce in
    `Sources.md` e un ADR — non un campo morto lasciato qui per non toccare il design.
    """

    collezione: str
    da_shard: str
    a_shard: str
    chunk: str


@dataclass(frozen=True, slots=True)
class PrimaryWaitAbandoned(Evento):
    """Il client ha smesso di aspettare un primario (ADR-0082).

    Non è un fallimento del cluster: è una **decisione di chi osserva**. Il cluster può
    benissimo eleggere un primario un istante dopo; questo evento dice che nessuno starà
    più a guardare.

    I due numeri viaggiano insieme perché `atteso_ms` da solo non si legge: «ho aspettato
    30 000 ms» non dice se è tanto finché non si sa che la pazienza valeva 30 000. Nella
    demo la pazienza si abbassa apposta, per non far attendere la sala, ed è il rapporto
    fra i due a restare vero.

    `ultimo_primario` è opzionale perché un client può connettersi a primario **già**
    caduto, e in quel caso non ne ha mai visto uno da nominare.
    """

    atteso_ms: float
    pazienza_ms: float
    ultimo_primario: str | None


@dataclass(frozen=True, slots=True)
class FaseIniziata(Evento):
    """Lo scenario annuncia la fase che sta per cominciare (ADR-0094).

    È l'unico dei dieci che non riporta qualcosa **accaduto al cluster**: riporta una
    decisione del copione. La distinzione conta, perché spiega perché questo evento può
    essere emesso prima che accada alcunché — è il titolo di un capitolo, non il capitolo.

    Esiste perché il Passo 4 del Task 13 chiede di asserire sulla **sequenza**: senza un
    evento che nomini le fasi, una prova dello scenario dovrebbe riconoscerle indovinando
    dai fatti che le compongono, e cambierebbe colore ogni volta che cambia una latenza.
    Con questo evento la sequenza del copione è leggibile in una lista di stringhe.

    Serve anche dal palco: è ciò che `--step` mostra prima di fermarsi ad aspettare Invio,
    ed è la ragione per cui `descrizione` è una frase e non un identificatore. `fase` è
    quella su cui asseriscono le prove; `descrizione` è quella che legge la sala.
    """

    fase: str
    descrizione: str
