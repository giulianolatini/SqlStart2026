"""`PymongoInspector`: la porta `ClusterInspector` attaccata a un MongoDB vero.

Chiude il debito che il Task 6 aveva lasciato scritto: fin qui `TopologyWatcher` aveva
visto solo topologie costruite a mano da `FakeInspector`, e nessuno sapeva se una
topologia **vera** entrasse in quella forma. Adesso ci entra, e ci entra passando dal
ponte SDAM del Task 7 — `descrivi_topologia` è già scritta e già provata, e qui non se ne
riscrive una riga.

## Tre delle quattro risposte non costano un giro di rete, una sì

`topology()` legge la descrizione che il driver **tiene già aggiornata** per conto suo:
pymongo interroga i server ogni dieci secondi (il monitoraggio SDAM) e conserva l'ultima
risposta, quindi chiedergliela è leggere una struttura in memoria. È la ragione per cui il
Blocco 2 può disegnarla a ogni fotogramma senza aggiungere carico a un cluster che sta già
misurando la propria latenza — e anche la ragione per cui quella descrizione può essere
**vecchia di qualche secondo**, che è precisamente il fenomeno che il Blocco 2 mostra.

`server_status()`, `db_stats()` e `shard_distribution()` invece parlano col server. La
terza ne fa **fino a tre**, e la ragione sta nella sua docstring.

## Il database dal costruttore, la collezione dal metodo

Fino al Task 14 arrivavano tutti e due dal costruttore, e la ragione scritta qui era che un
ispettore capace di cambiare bersaglio a ogni chiamata renderebbe possibile una schermata
con le statistiche di un database e la distribuzione di un altro, cioè due numeri accanto
che non parlano della stessa cosa. Al Task 15 il confine si è spostato di un passo
([ADR-0104](../../../../docs/Decision.md#adr-0104)): il database resta qui, la collezione
passa al metodo. Non perché la ragione fosse sbagliata, ma perché la scena del Blocco 3
accosta **apposta** due collezioni dello stesso cluster — la distribuita e quella che non
lo è — e perché la risposta adesso porta con sé il nome di quella di cui parla. I due
numeri accanto si presentano da soli.
"""

from typing import Any, Mapping

from pymongo import MongoClient
from pymongo.errors import OperationFailure
from pymongo.read_preferences import ReadPreference

from mongolab.domain.modelli import (
    ContoCollezione,
    ContoShard,
    DescrizioneTopologia,
    Distribuzione,
    RuoloServer,
)
from mongolab.infrastructure.sdam import descrivi_topologia

__all__ = ["PymongoInspector"]


class PymongoInspector:
    """Un `ClusterInspector` che guarda un cluster vero attraverso un `MongoClient`.

    Come `PymongoStore`, non decide la connessione: la riceve. Al Task 12 chi la costruisce
    saprà di ADR-0012 e userà i nomi di servizio della rete Compose; qui non se ne sa
    niente, ed è la ragione per cui le prove di integrazione possono collegarsi dall'host
    con `directConnection` senza che questo file lo sappia.
    """

    __slots__ = ("_client", "_database")

    def __init__(
        self, client: MongoClient[dict[str, Any]], database: str
    ) -> None:
        self._client = client
        self._database = database

    def topology(self) -> DescrizioneTopologia:
        """La topologia come la vede il client, tradotta dal ponte del Task 7.

        Una riga, e le due cose che quella riga garantisce sono state scritte altrove: i
        server escono ordinati per indirizzo — così che due letture identiche risultino
        identiche — e le stringhe del driver diventano i tipi del dominio passando da
        `RUOLI` e `FORME`, dove una forma sconosciuta diventa `SCONOSCIUTA` invece di
        sollevare.
        """
        return descrivi_topologia(self._client.topology_description)

    def server_status(self) -> Mapping[str, object]:
        """`serverStatus` così com'è, dal server a cui il client sta parlando.

        **Da quale server**, esattamente? Da quello che la selezione sceglie in questo
        istante: su un'istanza singola non c'è dubbio, su un replica set è il primario, e
        su uno sharded cluster è il mongos — che risponde con `process: "mongos"` e senza
        metà dei campi, perché un router non ha un motore di memorizzazione. Chi legge
        questo documento deve saperlo, ed è il motivo per cui la porta lo restituisce
        grezzo invece di normalizzarlo in un modello che darebbe l'impressione che i tre
        casi siano lo stesso caso.
        """
        return self._client.admin.command("serverStatus")

    def db_stats(self) -> Mapping[str, object]:
        """`dbStats` del database ricevuto alla costruzione.

        Attraverso un mongos la risposta è **aggregata** sugli shard, e lo dichiara con un
        campo `raw` che altrove non c'è: una voce per shard. Guardare `dataSize` senza
        sapere che è una somma è credere di guardare una macchina mentre se ne guardano
        due.
        """
        return self._client[self._database].command("dbStats")

    def collection_counts(self) -> tuple[ContoCollezione, ...]:
        """Un `countDocuments` per collezione, in ordine di nome.

        **`count_documents` e non `estimated_document_count`.** La stima legge i metadati
        della collezione e torna in un istante; il conteggio esatto le scandisce l'indice
        `_id`. Su un laboratorio da cinquantamila documenti la differenza non si sente, e
        in cambio il numero e' lo **stesso** che verificano `demo restore` e gli smoke:
        una fotografia che dicesse 49 998 dove la scena dice 50 000 farebbe cercare un
        guasto nel posto sbagliato.

        **E i metadati sbagliano davvero, su questo laboratorio.** Misurato sullo stack 01
        il 6 settembre: 38 collezioni in `lab`, `countDocuments` somma 1 528 002 e
        `dbStats.objects` ne dichiara 1 505 885. Lo scarto — 22 117 — sta tutto in **due**
        collezioni che nei metadati risultano a **zero** mentre contengono 7 847 e 14 270
        documenti. `validate()` su una delle due risponde `valid: true` senza un avviso e
        intanto rimette il contatore a 7 847: la collezione non era corrotta, era stantio
        il numero. Questo e' il motivo per cui la riga `collezioni` conta e non stima
        ([V-090](../../../../docs/Sources.md#v-090)).

        **Attraverso un mongos i due numeri possono divergere da `dbStats`**, ed e'
        corretto che divergano: `dbStats` somma i metadati degli shard, orfani compresi,
        mentre `countDocuments` conta i documenti **posseduti**. E' la stessa distinzione
        di `numOwnedDocuments` in `shard_distribution`, e nasconderla facendo tornare i
        conti vorrebbe dire cancellare l'unico posto in cui una migrazione non ripulita si
        vede.

        Le viste non si contano: `listCollections` le elenca insieme alle collezioni, e
        una vista non ha documenti propri — comparirebbe con il conteggio della sorgente,
        cioe' come un raddoppio.
        """
        database = self._client[self._database]
        nomi = database.list_collection_names(filter={"type": "collection"})
        return tuple(
            ContoCollezione(nome=nome, documenti=database[nome].count_documents({}))
            for nome in sorted(nomi)
        )

    def shard_distribution(self, collezione: str) -> Distribuzione:
        """Quanti documenti e quanti chunk per shard, e i tre casi tenuti distinti.

        **Due fonti, perché i due numeri stanno in due posti**, ed è esattamente il punto
        della scena del Blocco 3: chunk e documenti non si deducono l'uno dall'altro, e con
        la chiave sbagliata si vedono i chunk divisi a metà e i documenti tutti da una
        parte. I chunk li conosce il catalogo — `config.chunks`, unito a `config.collections`
        per `uuid`; i documenti li conosce `$shardedDataDistribution`, che è l'unico modo di
        avere il conteggio **per shard** senza interrogare gli shard uno per uno.

        `numOwnedDocuments` e non `numOrphanedDocs`: il manuale li definisce «Number of
        documents owned by the shard» e «Number of orphaned documents in the shard»
        ([A-012](../../../../app/docs/Sources.md#a-012)). Gli orfani sono i documenti rimasti
        su uno shard dopo una migrazione non ancora ripulita: sommarli gonfierebbe il totale
        oltre i documenti che esistono, e il conto non tornerebbe con `count()` per un motivo
        che sembrerebbe un errore del codice.

        **Come si decide che non è sharded.** Guardando la topologia, non catturando
        un'eccezione. Su un mongod `$shardedDataDistribution` solleva davvero — codice
        6789101, «can only be run on mongoS», misurato al Task 8 — ma dedurre una topologia
        da un errore è fragile: il giorno in cui quel codice cambia, o in cui l'utente non
        ha i permessi per `admin`, «non è sharded» diventerebbe la risposta a una domanda
        diversa. Il driver la topologia la sa già.

        **Come si decide che la collezione è distribuita**, che fino al Task 14 non si
        decideva affatto: la tupla vuota diceva «non è uno sharded cluster» e anche «è uno
        sharded cluster, ma questa collezione no», cioè il codice negava un cluster che era
        acceso ([ADR-0104](../../../../docs/Decision.md#adr-0104)). Lo decide la presenza di
        una riga di `$shardedDataDistribution`, e la scelta è misurata, non dedotta: su una
        collezione distribuita e **vuota** quella riga c'è lo stesso, con i due shard a zero
        documenti; su una non distribuita e piena di cinquanta documenti non c'è
        ([M-050](../../../../app/docs/Sources.md#m-050)). Un criterio basato sui documenti
        avrebbe sbagliato il primo caso, e uno basato su `config.collections` avrebbe
        confuso «non distribuita» con «non ho i permessi per saperlo».

        **La collezione non distribuita sta tutta sullo shard primario del database**, e
        qui il conteggio è esatto — `count_documents`, non una stima di metadati — perché
        la scena lo accosta alle scritture confermate dal carico e un paio di unità di
        scarto sembrerebbero documenti persi. Che sia davvero il primario non è dedotto:
        `$collStats` su quella collezione nomina lo stesso shard che `config.databases`
        chiama `primary` (M-050).

        Due riserve che vengono dalla stessa pagina. Lo stadio è «New in version 6.0.3»:
        su un cluster più vecchio solleverebbe, e questo file non ha un ripiego. E «After
        an unclean shutdown of a `mongod` using the Wired Tiger storage engine, size and
        count statistics reported by `$shardedDataDistribution` may be inaccurate» — cioè
        dopo un `docker kill` della scena del guasto i numeri possono essere sbagliati, che
        è esattamente il momento in cui la scena li mostra.

        Una terza riserva, che nasce qui: **senza lettura su `config` il primario resta
        ignoto**, e una `Distribuzione` senza primario si legge come «non è uno sharded
        cluster». È la stessa degradazione che c'era prima di ADR-0104, ristretta a un caso
        che questo laboratorio non incontra — i tre stack si collegano da amministratore —
        e preferita a un quarto stato che esisterebbe solo per descrivere un permesso che
        manca.
        """
        if not self._e_sharded():
            return Distribuzione(
                collezione=collezione, distribuita=False, primario=None, conti=()
            )
        primario = self._shard_primario()
        righe = tuple(
            self._client["admin"].aggregate(
                [
                    {"$shardedDataDistribution": {}},
                    {"$match": {"ns": f"{self._database}.{collezione}"}},
                ]
            )
        )
        if not righe:
            return Distribuzione(
                collezione=collezione,
                distribuita=False,
                primario=primario,
                conti=()
                if primario is None
                else (
                    ContoShard(
                        shard=primario,
                        documenti=self._quanti(collezione),
                        # Zero, e non «ignoto»: una collezione non distribuita non ha
                        # chunk, perché i chunk sono il modo in cui il catalogo racconta
                        # una divisione che qui non è mai avvenuta.
                        chunk=0,
                    ),
                ),
            )
        chunk = self._chunk_per_shard(collezione)
        conti: list[ContoShard] = []
        for riga in righe:
            for shard in riga.get("shards", []):
                nome = str(shard["shardName"])
                conti.append(
                    ContoShard(
                        shard=nome,
                        documenti=int(shard.get("numOwnedDocuments", 0)),
                        chunk=chunk.get(nome, 0),
                    )
                )
        # Ordinati per nome, come i server di `topology()` e per la stessa ragione: la
        # scena confronta due schermate a distanza di minuti, e due righe che si scambiano
        # di posto sembrano un cambiamento che non c'è stato.
        return Distribuzione(
            collezione=collezione,
            distribuita=True,
            primario=primario,
            conti=tuple(sorted(conti, key=lambda conto: conto.shard)),
        )

    # --- Il mestiere ------------------------------------------------------------------

    def _e_sharded(self) -> bool:
        """C'è un router fra i server che il client conosce?

        Il ruolo e non la forma della topologia. `TipoTopologia.SHARDED` sarebbe la
        risposta ovvia e ha un buco: un client costruito con `directConnection=True` verso
        un mongos legge la forma `SINGOLA` — conosce un server solo, quindi non ha nulla da
        chiamare cluster — mentre il *ruolo* di quel server resta `ROUTER`, perché glielo
        dice `hello` con `msg: "isdbgrid"`. Chiedere il ruolo funziona in tutti e due i
        casi.

        La riga di `_scopri` sopra è il resto della risposta, e non è un dettaglio: senza,
        la domanda diventa «fra i server che conosco c'è un router?» posta a un client che
        non conosce ancora nessun server.
        """
        self._scopri()
        return any(
            server.ruolo is RuoloServer.ROUTER for server in self.topology().server
        )

    def _scopri(self) -> None:
        """Costringe il client a guardare, se non ha ancora guardato.

        PyMongo scopre la topologia alla **prima operazione**, non alla costruzione: fino
        a lì ogni seme è `SCONOSCIUTO`, che nel dominio è esattamente «assenza di
        un'osservazione» e non «osservato assente». Leggere quella descrizione e concludere
        qualcosa sul cluster è leggere il proprio non aver guardato.

        Costava una schermata: la prima fase di `demo sharding` legge a client freddo, e
        dichiarava non distribuita una `lab.ordini` distribuita su due shard, con `primario`
        `None` e la riga del bilancio a trattini ([M-053](../../../../app/docs/Sources.md#m-053)).
        Nessuna prova d'integrazione lo vedeva, perché la fixture di sessione consegna un
        client già caldo: la scoperta era avvenuta per effetto collaterale di qualcos'altro.

        **`nearest` e non il primario.** Qui serve sapere *che cosa* si ha davanti, non
        parlare con chi comanda: un mongos non è primario di niente, e un replica set in
        mezzo a un'elezione non ne ha uno — chiedere il primario pianterebbe `stats`
        proprio durante la scena dell'Atto II, che è quando la si guarda di più.

        Un solo `ping`, e solo da freddo: appena un ruolo è noto la descrizione la tiene
        aggiornata da sé, con il monitoraggio in background.
        """
        if any(
            server.ruolo is not RuoloServer.SCONOSCIUTO
            for server in self.topology().server
        ):
            return
        self._client.admin.command("ping", read_preference=ReadPreference.NEAREST)

    def _shard_primario(self) -> str | None:
        """Quale shard tiene le collezioni non distribuite di questo database.

        `config.databases`, campo `primary`. `None` se il database non c'è ancora — su un
        cluster un database esiste quando ci si scrive dentro — o se l'utente non può
        leggere `config`, che è la riserva dichiarata in `shard_distribution`.
        """
        try:
            riga = self._client["config"]["databases"].find_one({"_id": self._database})
        except OperationFailure:
            return None
        if riga is None or "primary" not in riga:
            return None
        return str(riga["primary"])

    def _quanti(self, collezione: str) -> int:
        """Il conteggio esatto della collezione. Serve solo al caso non distribuito."""
        return self._client[self._database][collezione].count_documents({})

    def _chunk_per_shard(self, collezione: str) -> dict[str, int]:
        """Quanti chunk della collezione stanno su ciascuno shard, dal catalogo.

        L'unione è su `uuid` e non sul namespace, e lo prescrive il manuale: «To find the
        chunks in a collection, retrieve the collection's `uuid` identifier from the
        `config.collections` collection. Then, use the `uuid` to retrieve the document with
        the same `uuid` from the `config.chunks` collection»
        ([A-013](../../../../app/docs/Sources.md#a-013)).

        Il manuale **non** dice che `ns` sia stato tolto, e infatti non lo si scrive qui:
        lo si è misurato. Sul 7.0.40 di questo repository nessuno dei chunk ha quel campo, e
        `{"ns": "lab.ordini"}` restituisce zero **senza sollevare**
        ([M-020](../../../../app/docs/Sources.md#m-020)). È il difetto peggiore possibile in
        questa scena: zero chunk su uno shard che ne ha, cioè la conclusione «i dati non
        sono distribuiti» detta esattamente dove lo sono.
        """
        try:
            catalogo = self._client["config"]["collections"].find_one(
                {"_id": f"{self._database}.{collezione}"}
            )
        except OperationFailure:
            # Un utente senza lettura su `config` non è un errore da propagare: la
            # distribuzione resta leggibile per i documenti, e i chunk escono a zero. La
            # riserva è dichiarata qui perché uno zero silenzioso è ciò che questa
            # applicazione teme di più.
            return {}
        if catalogo is None or "uuid" not in catalogo:
            return {}
        raggruppati = self._client["config"]["chunks"].aggregate(
            [
                {"$match": {"uuid": catalogo["uuid"]}},
                {"$group": {"_id": "$shard", "quanti": {"$sum": 1}}},
            ]
        )
        return {str(riga["_id"]): int(riga["quanti"]) for riga in raggruppati}
