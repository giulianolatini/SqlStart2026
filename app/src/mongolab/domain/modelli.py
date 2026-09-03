"""I dati che le porte si scambiano. Congelati, e senza dipendenze.

Nessun import di terze parti, per la regola del §6.1 verificata da
`tests/unit/test_scheletro.py`. In particolare **niente pymongo**: un documento qui è
una `Mapping[str, object]`, non un `SON` né un `RawBSONDocument`, e la traduzione da
quei tipi avviene in `infrastructure`. È ciò che permette a `InMemoryStore` di essere un
doppio onesto invece di una finzione: parla la stessa lingua dell'adattatore vero.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

__all__ = [
    "ContoShard",
    "DescrizioneServer",
    "DescrizioneTopologia",
    "Documento",
    "Progress",
    "RuoloServer",
    "TipoTopologia",
]

type Documento = Mapping[str, object]
"""Un documento come lo vede il dominio: chiavi di testo, valori che non interpreta.

`object` e non `Any`: `Any` spegne il controllo dei tipi in ogni punto che tocca, e un
valore che arriva da BSON è appunto qualcosa di cui non sappiamo niente — dirlo con
`object` costringe chi lo usa a restringerlo esplicitamente, che è la verità.
"""


class RuoloServer(Enum):
    """Il ruolo di un server come lo vede il client, non come lo dichiara il server.

    È una distinzione che il talk mostra: il client conosce la topologia perché la
    **scopre**, e per un istante durante un'elezione la sua idea è diversa da quella del
    cluster. Questi valori sono ciò che il client crede in un dato momento.

    I primi tre stati dell'assenza vanno letti insieme, perché sono tre cose diverse.
    `SCONOSCIUTO` è **l'assenza di un'osservazione**: il client non ha ancora guardato,
    o ha guardato e non ha capito. `IRRAGGIUNGIBILE` è **un'osservazione**: il client ha
    provato, e non è riuscito. `ALTRO` è il contrario di tutti e due: il client sa
    benissimo che cosa ha davanti, ed è qualcosa che questa scena non nomina.
    """

    SCONOSCIUTO = "sconosciuto"
    STANDALONE = "standalone"
    PRIMARIO = "primario"
    SECONDARIO = "secondario"
    ARBITRO = "arbitro"
    ROUTER = "router"
    IRRAGGIUNGIBILE = "irraggiungibile"
    ALTRO = "altro"
    """Riconosciuto dal client, estraneo al talk.

    Il caso che capita davvero è un membro del replica set che sta ripartendo: per
    qualche secondo è in `RECOVERING` o in `STARTUP2`, e il driver lo chiama `RSOther`.
    Sono i secondi della dimostrazione del failover, cioè l'unico momento in cui la sala
    sta guardando quella riga. Mandarlo su `SCONOSCIUTO` scriverebbe «non so» proprio lì.
    """


class TipoTopologia(Enum):
    """La forma dell'insieme, che non è la somma dei ruoli.

    `REPLICA_SET_SENZA_PRIMARIO` esiste come stato di prima classe perché è **la** scena
    del Blocco 2: fra il guasto e l'elezione il cluster non è rotto e non è sano, è in un
    terzo stato che dura secondi e che il pubblico vede solo se qualcuno lo nomina.
    """

    SCONOSCIUTA = "sconosciuta"
    SINGOLA = "singola"
    REPLICA_SET_CON_PRIMARIO = "replica set con primario"
    REPLICA_SET_SENZA_PRIMARIO = "replica set senza primario"
    SHARDED = "sharded"


@dataclass(frozen=True, slots=True)
class DescrizioneServer:
    """Un server come il client lo vede adesso."""

    indirizzo: str
    ruolo: RuoloServer
    ritardo_ms: float | None = None
    errore: str | None = None


@dataclass(frozen=True, slots=True)
class DescrizioneTopologia:
    """La topologia come il client la vede adesso.

    `server` è una tupla e non una lista: questa descrizione viaggia dentro un evento,
    da un thread all'altro, e una lista renderebbe congelato il riferimento e non il
    contenuto — il `frozen=True` del dataclass non protegge ciò che i campi contengono.
    """

    tipo: TipoTopologia
    server: tuple[DescrizioneServer, ...]
    nome_set: str | None = None

    @property
    def primario(self) -> DescrizioneServer | None:
        """Il primario, se il client ne vede uno."""
        for server in self.server:
            if server.ruolo is RuoloServer.PRIMARIO:
                return server
        return None

    @property
    def ha_primario(self) -> bool:
        return self.primario is not None


@dataclass(frozen=True, slots=True)
class ContoShard:
    """Quanti documenti e quanti chunk stanno su uno shard.

    I due numeri non si deducono l'uno dall'altro, ed è tutto il punto della scena: un
    cluster può avere i chunk divisi a metà e i documenti tutti da una parte, ed è
    esattamente ciò che succede con la chiave sbagliata.
    """

    shard: str
    documenti: int
    chunk: int


@dataclass(frozen=True, slots=True)
class Progress:
    """L'avanzamento di un'operazione lunga, mentre procede.

    `totali` è opzionale perché a volte non si sa: `mongodump` annuncia il totale di una
    collezione ma non quello del dump intero, e inventare un denominatore per avere una
    percentuale a schermo significa mostrare una barra che mente.
    """

    fase: str
    completati: int
    totali: int | None = None
    messaggio: str = ""

    @property
    def percentuale(self) -> float | None:
        """La frazione completata, o `None` quando il totale non si conosce."""
        if self.totali is None or self.totali <= 0:
            return None
        return 100.0 * self.completati / self.totali
