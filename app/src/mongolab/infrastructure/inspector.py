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
terza fa **due** chiamate, e la ragione sta nella sua docstring.

## Nomi legati alla costruzione, non passati ai metodi

La porta dichiara `db_stats()` e `shard_distribution()` senza argomenti, quindi database e
collezione arrivano dal costruttore. Non è una limitazione subita: un ispettore che
cambiasse bersaglio a ogni chiamata renderebbe possibile una schermata che mostra le
statistiche di un database e la distribuzione di un altro, con due numeri accanto che non
parlano della stessa cosa.
"""

from typing import Any, Mapping

from pymongo import MongoClient
from pymongo.errors import OperationFailure

from mongolab.domain.modelli import ContoShard, DescrizioneTopologia, RuoloServer
from mongolab.infrastructure.sdam import descrivi_topologia

__all__ = ["PymongoInspector"]


class PymongoInspector:
    """Un `ClusterInspector` che guarda un cluster vero attraverso un `MongoClient`.

    Come `PymongoStore`, non decide la connessione: la riceve. Al Task 12 chi la costruisce
    saprà di ADR-0012 e userà i nomi di servizio della rete Compose; qui non se ne sa
    niente, ed è la ragione per cui le prove di integrazione possono collegarsi dall'host
    con `directConnection` senza che questo file lo sappia.
    """

    __slots__ = ("_client", "_database", "_collezione")

    def __init__(
        self, client: MongoClient[dict[str, Any]], database: str, collezione: str
    ) -> None:
        self._client = client
        self._database = database
        self._collezione = collezione

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

    def shard_distribution(self) -> tuple[ContoShard, ...]:
        """Quanti documenti e quanti chunk per shard. Vuota su ciò che non è sharded.

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

        Due riserve che vengono dalla stessa pagina. Lo stadio è «New in version 6.0.3»:
        su un cluster più vecchio solleverebbe, e questo file non ha un ripiego. E «After
        an unclean shutdown of a `mongod` using the Wired Tiger storage engine, size and
        count statistics reported by `$shardedDataDistribution` may be inaccurate» — cioè
        dopo un `docker kill` della scena del guasto i numeri possono essere sbagliati, che
        è esattamente il momento in cui la scena li mostra.

        **Come si decide che non è sharded.** Guardando la topologia, non catturando
        un'eccezione. Su un mongod `$shardedDataDistribution` solleva davvero — codice
        6789101, «can only be run on mongoS», misurato al Task 8 — ma dedurre una topologia
        da un errore è fragile: il giorno in cui quel codice cambia, o in cui l'utente non
        ha i permessi per `admin`, «non è sharded» diventerebbe la risposta a una domanda
        diversa. Il driver la topologia la sa già.

        **La tupla vuota ha due significati diversi**, e la porta ne dichiara uno solo. Il
        primo è «non è uno sharded cluster». Il secondo è «è uno sharded cluster, ma questa
        collezione non è distribuita»: i documenti stanno tutti sullo shard primario e il
        catalogo non ha niente da dire su di loro. Distinguere i due casi richiederebbe un
        tipo di ritorno diverso; per la scena che questa applicazione mostra la distinzione
        non serve, e fingere di averla fatta con una tupla sarebbe peggio che dichiararlo.
        """
        if not self._e_sharded():
            return ()
        chunk = self._chunk_per_shard()
        righe = self._client["admin"].aggregate(
            [
                {"$shardedDataDistribution": {}},
                {"$match": {"ns": f"{self._database}.{self._collezione}"}},
            ]
        )
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
        return tuple(sorted(conti, key=lambda conto: conto.shard))

    # --- Il mestiere ------------------------------------------------------------------

    def _e_sharded(self) -> bool:
        """C'è un router fra i server che il client conosce?

        Il ruolo e non la forma della topologia. `TipoTopologia.SHARDED` sarebbe la
        risposta ovvia e ha un buco: un client costruito con `directConnection=True` verso
        un mongos legge la forma `SINGOLA` — conosce un server solo, quindi non ha nulla da
        chiamare cluster — mentre il *ruolo* di quel server resta `ROUTER`, perché glielo
        dice `hello` con `msg: "isdbgrid"`. Chiedere il ruolo funziona in tutti e due i
        casi.
        """
        return any(
            server.ruolo is RuoloServer.ROUTER
            for server in self.topology().server
        )

    def _chunk_per_shard(self) -> dict[str, int]:
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
            collezione = self._client["config"]["collections"].find_one(
                {"_id": f"{self._database}.{self._collezione}"}
            )
        except OperationFailure:
            # Un utente senza lettura su `config` non è un errore da propagare: la
            # distribuzione resta leggibile per i documenti, e i chunk escono a zero. La
            # riserva è dichiarata qui perché uno zero silenzioso è ciò che questa
            # applicazione teme di più.
            return {}
        if collezione is None or "uuid" not in collezione:
            return {}
        raggruppati = self._client["config"]["chunks"].aggregate(
            [
                {"$match": {"uuid": collezione["uuid"]}},
                {"$group": {"_id": "$shard", "quanti": {"$sum": 1}}},
            ]
        )
        return {str(riga["_id"]): int(riga["quanti"]) for riga in raggruppati}
