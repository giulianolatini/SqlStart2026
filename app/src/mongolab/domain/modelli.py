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
    "ContoCollezione",
    "ContoShard",
    "DescrizioneServer",
    "DescrizioneTopologia",
    "Distribuzione",
    "Documento",
    "Piano",
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
class ContoCollezione:
    """Quanti documenti stanno in una collezione, con il suo nome accanto.

    Esiste perche' `dbStats` risponde per **database**, e per il database `lab` quella
    risposta e' una somma: `ordini` piu' tutte le collezioni di carico che le corse
    dell'Atto III lasciano indietro. Chi controllava lo stato atteso del runbook leggeva
    62 602 dove il documento diceva 50 000 e concludeva che lo stack era rotto, mentre era
    soltanto gia' stato usato. Un totale non risponde alla domanda «quanti ordini ci
    sono»: il dettaglio si', e la somma resta stampata sotto per chi vuole verificarla.

    Il conteggio e' **esatto**, non stimato: `countDocuments` e non i metadati della
    collezione. Costa una scansione, e su cinquantamila documenti in un laboratorio e' un
    prezzo che non si sente; in cambio il numero e' lo stesso che le scene del talk
    verificano, e due numeri diversi per la stessa cosa sullo stesso schermo sono peggio
    di un numero lento.
    """

    nome: str
    documenti: int


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


@dataclass(frozen=True, slots=True)
class Distribuzione:
    """Dove stanno i documenti di **una** collezione, e se qualcuno l'ha distribuita.

    Sostituisce la `tuple[ContoShard, ...]` che `ClusterInspector.shard_distribution()`
    restituiva fino al Task 14, e nasce per chiudere il punto aperto che quella firma
    dichiarava da sé: **la tupla vuota voleva dire due cose diverse.** «Non è uno sharded
    cluster» e «è uno sharded cluster, ma questa collezione non è distribuita» sono lo
    stesso valore e fatti opposti, e la scena del Blocco 3 esiste per mostrare
    precisamente il secondo ([ADR-0104](../../../../docs/Decision.md#adr-0104)).

    I tre stati si leggono da due campi, e nessuna combinazione è ambigua:

    | `primario` | `distribuita` | che cosa significa                                  |
    | ---------- | ------------- | --------------------------------------------------- |
    | `None`     | `False`       | non è uno sharded cluster: non c'è niente da dire     |
    | uno shard  | `False`       | è un cluster, ma la collezione sta **intera** lì      |
    | uno shard  | `True`        | è un cluster, e il catalogo la conosce                |

    La quarta combinazione — `primario is None` e `distribuita` — non è rappresentabile
    in un cluster reale, e questo tipo **non la vieta**: sarebbe una guardia che difende
    da un errore di chi costruisce l'oggetto, non da un fatto del mondo, e costerebbe una
    riga di validazione in un dominio che di validazione non ne ha da nessun'altra parte.
    """

    collezione: str
    distribuita: bool
    primario: str | None
    conti: tuple[ContoShard, ...]

    @property
    def in_un_cluster(self) -> bool:
        """C'è uno shard primario, quindi la domanda ha senso. Non dice che sia distribuita."""
        return self.primario is not None

    @property
    def documenti(self) -> int:
        """Quanti documenti in tutto, sommando gli shard che hanno risposto."""
        return sum(conto.documenti for conto in self.conti)

    @property
    def chunk(self) -> int:
        """Quanti chunk in tutto. **Zero è la risposta giusta** per una non distribuita."""
        return sum(conto.chunk for conto in self.conti)

    def quota(self, shard: str) -> float | None:
        """La percentuale di documenti su `shard`, o `None` se la domanda è vuota.

        Due casi restituiscono `None`, e sono diversi fra loro. Il primo: la collezione
        non ha documenti, e «zero su zero» non è lo zero per cento. Il secondo: quello
        shard non compare nella risposta — e uno shard che non ha risposto non ha «zero
        documenti», semplicemente non si sa. Dire zero in entrambi i casi metterebbe a
        schermo un numero fabbricato accanto a numeri misurati.
        """
        totale = self.documenti
        if totale <= 0:
            return None
        for conto in self.conti:
            if conto.shard == shard:
                return 100.0 * conto.documenti / totale
        return None


@dataclass(frozen=True, slots=True)
class Piano:
    """Come il router ha deciso di eseguire una query: su uno shard o su tutti.

    È il lato client del Passo 3 del Blocco 3. `stadio` è la parola che `mongos` mette in
    `queryPlanner.winningPlan.stage` — `SINGLE_SHARD` o `SHARD_MERGE` sulla 7.0.40 — e si
    porta dietro **verbatim** invece di tradurla in un booleano soltanto: il giorno in cui
    comparisse una terza parola, un campo di testo la mostra e un booleano la nasconde.

    *Riserva.* `mirata` guarda **quanti** shard sono stati interrogati, non che cosa il
    router abbia pensato. Su un cluster a uno shard solo ogni query risulterebbe mirata, e
    sarebbe vero senza essere interessante.
    """

    filtro: Documento
    stadio: str
    shard: tuple[str, ...]

    @property
    def mirata(self) -> bool:
        """Un solo shard interrogato. Nessuno shard **non** è mirato: è una risposta vuota."""
        return len(self.shard) == 1
