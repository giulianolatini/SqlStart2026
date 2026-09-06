"""`PymongoInspector` contro i tre stack veri.

È la prova che il Task 6 non poteva scrivere. `TopologyWatcher` ha visto finora solo
topologie costruite a mano da `FakeInspector`: sapeva confrontarle e sapeva tacere quando
non cambiavano, ma nessuno aveva mai verificato che una topologia **vera** entrasse in
quella forma. Qui entra, e viene da tre cluster diversi.

Le prove sono divise per stack perché costano tempo diverso. Quelle sul 01 girano in
pochi secondi; quelle sul 03 accendono uno sharded cluster, e chi sta lavorando
sull'adattatore può escluderle con `pytest tests/integration -m "not stack03"` sapendo a
che cosa sta rinunciando. I marcatori non sono scritti a mano su ogni prova: il conftest
li deduce dalle fixture che ciascuna chiede, così non possono restare indietro.
"""

from typing import Any

import pytest
from pymongo import MongoClient

from mongolab.domain.modelli import RuoloServer, TipoTopologia
from mongolab.domain.porte import ClusterInspector
from mongolab.infrastructure.bersagli import (
    BERSAGLI,
    COLLEZIONE,
    DATABASE,
    connetti,
)
from mongolab.infrastructure.generatore import DataGenerator
from mongolab.infrastructure.inspector import PymongoInspector
from mongolab.infrastructure.store import PymongoStore

from tests.integration.ambiente import PREFISSO_PROVE, collezione_usa_e_getta

# --- Lo stack 01: istanza singola ------------------------------------------------------


def test_l_ispettore_passa_per_la_porta(stack01: MongoClient[dict[str, Any]]) -> None:
    """La conformità strutturale, verificata dove mypy la verifica: in un'annotazione."""
    ispettore: ClusterInspector = PymongoInspector(stack01, "lab")
    assert ispettore.topology().server


def test_la_topologia_di_un_istanza_singola(stack01: MongoClient[dict[str, Any]]) -> None:
    """Un mongod da solo: una forma `SINGOLA`, un server, ruolo `STANDALONE`, nessun set.

    Il ponte SDAM del Task 7 sapeva tradurre le stringhe di pymongo nei tipi del dominio,
    e questa è la prima volta che le stringhe arrivano da un server invece che da una
    prova. `nome_set` è `None` perché non c'è nessun set: è il valore che distingue
    un'istanza singola da un membro visto da vicino, e il Task 12 lo userà.
    """
    topologia = PymongoInspector(stack01, "lab").topology()

    assert topologia.tipo is TipoTopologia.SINGOLA
    assert topologia.nome_set is None
    assert len(topologia.server) == 1
    assert topologia.server[0].ruolo is RuoloServer.STANDALONE
    assert topologia.server[0].indirizzo.endswith(":27017")


def test_lo_stato_del_server_arriva_grezzo(stack01: MongoClient[dict[str, Any]]) -> None:
    """`serverStatus` non viene interpretato, e i tre campi che si controllano dicono perché.

    `version` e `process` servono a sapere **con che cosa** si sta parlando, e `connections`
    è il primo grafico del Blocco 2. Nessuno dei tre viene estratto in un modello: la
    porta restituisce il documento intero apposta, così che la pagina del Task 17 possa
    dire quali campi guardare senza che il codice l'abbia già deciso.
    """
    stato = PymongoInspector(stack01, "lab").server_status()

    assert stato["process"] == "mongod"
    assert isinstance(stato["version"], str)
    assert isinstance(stato["connections"], dict)
    assert stato["ok"] == 1.0


def test_le_statistiche_del_database_contano_la_collezione_che_c_e(
    stack01: MongoClient[dict[str, Any]],
) -> None:
    """`dbStats` guarda il database che l'ispettore ha ricevuto, non `admin`.

    Con un database inventato risponde lo stesso — MongoDB non solleva su un database che
    non esiste — e risponde **zero**. Le due asserzioni insieme dicono che il nome viene
    davvero usato: senza la seconda, un ispettore che interrogasse sempre lo stesso
    database passerebbe la prima.
    """
    ispettore = PymongoInspector(stack01, "lab")
    statistiche = ispettore.db_stats()

    assert statistiche["db"] == "lab"
    assert isinstance(statistiche["dataSize"], (int, float))
    assert int(statistiche["objects"]) > 0  # type: ignore[call-overload]

    vuoto = PymongoInspector(stack01, f"{PREFISSO_PROVE}mai_creato").db_stats()
    assert vuoto["db"] == f"{PREFISSO_PROVE}mai_creato"
    assert vuoto["objects"] == 0


def test_le_collezioni_si_contano_una_per_una_e_in_ordine_di_nome(
    stack01: MongoClient[dict[str, Any]],
) -> None:
    """Il dettaglio che `dbStats` non da': quale numero appartiene a quale collezione.

    Due collezioni con conteggi **diversi**, e diversi anche dal totale: un ispettore che
    restituisse due volte lo stesso numero, o il totale del database per entrambe,
    passerebbe una prova costruita con due collezioni uguali.

    L'ordine e' asserito perche' e' parte del contratto della porta: questa fotografia
    esiste per essere confrontata a colpo d'occhio con lo stato atteso del runbook, e un
    elenco che si riordina da solo a ogni corsa non si confronta.
    """
    with collezione_usa_e_getta(stack01) as ordini:
        database = ordini.database
        ordini.insert_many([{"n": n} for n in range(7)])
        database["carico-20260906-153012"].insert_many([{"n": n} for n in range(3)])

        conti = PymongoInspector(stack01, database.name).collection_counts()

    assert [conto.nome for conto in conti] == ["carico-20260906-153012", "ordini"]
    assert [conto.documenti for conto in conti] == [3, 7]


def test_la_somma_delle_collezioni_torna_con_il_totale_del_database(
    stack01: MongoClient[dict[str, Any]],
) -> None:
    """La proprieta' per cui la fotografia si chiama verificabile.

    Fuori da uno sharded cluster i due numeri devono coincidere, e chi guarda lo schermo
    deve poterlo controllare a mente. Attraverso un mongos possono divergere — `dbStats`
    somma i metadati degli shard, orfani compresi — ed e' il motivo per cui questa prova
    sta sullo stack 01 e non sul 03: li' la disuguaglianza sarebbe un'informazione, non un
    guasto, e una prova non deve promettere un'uguaglianza che il dominio non garantisce.
    """
    with collezione_usa_e_getta(stack01) as ordini:
        database = ordini.database
        ordini.insert_many([{"n": n} for n in range(11)])
        database["carico"].insert_many([{"n": n} for n in range(5)])

        ispettore = PymongoInspector(stack01, database.name)
        conti = ispettore.collection_counts()
        totale = int(ispettore.db_stats()["objects"])  # type: ignore[call-overload]

    assert sum(conto.documenti for conto in conti) == totale == 16


def test_una_vista_non_si_conta_come_collezione(
    stack01: MongoClient[dict[str, Any]],
) -> None:
    """Una vista non ha documenti propri: contarla raddoppierebbe quelli della sorgente.

    `listCollections` le elenca insieme alle collezioni, e senza il filtro sul tipo
    `ordini_visti` comparirebbe con i quattro documenti di `ordini` — cioe' la somma
    direbbe otto dove i documenti sono quattro.

    **`system.views` invece si conta, ed e' giusto cosi'.** Non e' la vista: e' la
    collezione vera in cui il database *scrive la definizione* della vista, un documento
    per vista, e `dbStats` la somma insieme alle altre. Escluderla per farla sparire dallo
    schermo romperebbe la sola proprieta' per cui questo dettaglio esiste — che i pezzi
    tornino con il totale. Misurato scrivendo questa prova: l'attesa iniziale era che
    creare una vista non lasciasse altro, e non e' vero.
    """
    with collezione_usa_e_getta(stack01) as ordini:
        database = ordini.database
        ordini.insert_many([{"n": n} for n in range(4)])
        database.create_collection("ordini_visti", viewOn="ordini", pipeline=[])

        ispettore = PymongoInspector(stack01, database.name)
        conti = ispettore.collection_counts()
        totale = int(ispettore.db_stats()["objects"])  # type: ignore[call-overload]

    nomi = [conto.nome for conto in conti]
    assert "ordini_visti" not in nomi, "una vista non e' una collezione da contare"
    assert nomi == ["ordini", "system.views"]
    assert sum(conto.documenti for conto in conti) == totale


def test_su_un_istanza_singola_non_c_e_distribuzione_per_shard(
    stack01: MongoClient[dict[str, Any]],
) -> None:
    """Una `Distribuzione` che dice di no, e **non** un'eccezione: lo dice la porta.

    La strada facile sarebbe eseguire `$shardedDataDistribution` e catturare l'errore. Su
    un mongod solleva davvero — codice 6789101, «can only be run on mongoS», misurato —
    ma catturare un errore per dedurne una topologia è una deduzione fragile: il giorno in
    cui il codice cambia o l'utente non ha i permessi, «non è sharded» diventa la risposta
    a una domanda diversa. L'ispettore lo chiede alla topologia, che il driver conosce già.
    """
    fuori = PymongoInspector(stack01, "lab").shard_distribution("ordini")

    assert fuori.collezione == "ordini"
    assert not fuori.in_un_cluster
    assert not fuori.distribuita
    assert fuori.conti == ()


# --- Lo stack 02: replica set ---------------------------------------------------------


def test_il_membro_di_un_replica_set_si_dichiara_primario(
    stack02: MongoClient[dict[str, Any]],
) -> None:
    """Il ruolo è giusto, la forma no, e la ragione è dichiarata.

    Dall'host il client non può usare `replicaSet=rs0`: i membri sono registrati con i
    nomi di servizio Compose (ADR-0021), che dall'host non risolvono. Con
    `directConnection=True` il server si presenta per quello che è — `RSPrimary` → ruolo
    `PRIMARIO` — mentre la **forma** della topologia si legge `SINGOLA`, perché il client
    di membri ne conosce uno solo.

    La riserva è che `REPLICA_SET_CON_PRIMARIO` qui non si può verificare, e la si
    verificherà al Task 12 quando l'applicazione girerà dentro la rete Compose (ADR-0012).
    La prova asserisce quello che si può asserire adesso, **e** l'anomalia, così che il
    giorno in cui la forma diventerà giusta questa riga diventi rossa e chieda di essere
    riscritta invece di restare a raccontare una cosa vecchia.
    """
    topologia = PymongoInspector(stack02, "lab").topology()

    assert len(topologia.server) == 1
    assert topologia.server[0].ruolo is RuoloServer.PRIMARIO
    assert topologia.tipo is TipoTopologia.SINGOLA, (
        "se questa è diventata REPLICA_SET_CON_PRIMARIO, la prova va dall'interno della "
        "rete Compose: riscrivila, è la promessa del Task 12"
    )


def test_lo_stato_di_un_membro_dichiara_il_set(
    stack02: MongoClient[dict[str, Any]],
) -> None:
    """`serverStatus.repl` c'è su un membro e non su un'istanza singola.

    È il campo che rende `serverStatus` interessante per il Blocco 2: `repl.setName` e
    `repl.isWritablePrimary` sono ciò che si guarda durante un'elezione, e sono anche la
    dimostrazione che restituire il documento grezzo era la scelta giusta — un modello
    scritto contro lo stack 01 non avrebbe avuto un posto dove metterli.
    """
    stato = PymongoInspector(stack02, "lab").server_status()
    repl = stato["repl"]

    assert isinstance(repl, dict)
    assert repl["setName"] == "rs0"
    assert repl["isWritablePrimary"] is True


def test_un_replica_set_non_ha_distribuzione_per_shard(
    stack02: MongoClient[dict[str, Any]],
) -> None:
    fuori = PymongoInspector(stack02, "lab").shard_distribution("ordini")

    assert not fuori.in_un_cluster
    assert fuori.primario is None


# --- Lo stack 03: sharded cluster -----------------------------------------------------


def test_il_mongos_si_presenta_come_router(stack03: MongoClient[dict[str, Any]]) -> None:
    """Un mongos non è un mongod, e il dominio ha un ruolo apposta.

    Qui, a differenza del 02, il client **non** usa `directConnection`: un mongos è già il
    punto d'ingresso, quindi la scoperta non porta altrove e la topologia si legge per
    quello che è.
    """
    topologia = PymongoInspector(stack03, "lab").topology()

    assert topologia.tipo is TipoTopologia.SHARDED
    assert [server.ruolo for server in topologia.server] == [RuoloServer.ROUTER]


def test_lo_stato_di_un_mongos_dice_di_essere_un_mongos(
    stack03: MongoClient[dict[str, Any]],
) -> None:
    """`process` vale `mongos`, e chi legge `serverStatus` deve aspettarselo.

    Metà dei campi di un `serverStatus` di mongod qui non ci sono — non c'è
    `wiredTiger`, non c'è `repl` — perché un router non ha un motore di
    memorizzazione e non replica niente. Una pagina di monitoraggio che li desse per
    scontati mostrerebbe dei buchi proprio sullo stack più complicato.
    """
    stato = PymongoInspector(stack03, "lab").server_status()

    assert stato["process"] == "mongos"
    assert "wiredTiger" not in stato


def test_la_prima_domanda_a_un_client_appena_aperto_non_nega_il_cluster() -> None:
    """Il difetto che nessuna prova vedeva, perché tutte partivano da un client già caldo.

    `_e_sharded()` legge la topologia **come il client la conosce**, e un client appena
    costruito non conosce ancora niente: PyMongo scopre i server alla prima operazione, non
    alla costruzione. La domanda diventava allora «fra i server che conosco c'è un router?»
    posta a un client che non conosce nessun server, e la risposta era no — cioè
    `shard_distribution` dichiarava non distribuita una collezione distribuita, e `primario`
    `None` su un cluster acceso.

    Le fixture di sessione lo nascondevano tutte: `_acceso` chiama `spazza(client)` prima
    di consegnarlo, e quella spazzata scalda la topologia. Il difetto è comparso alla prima
    corsa vera di `demo sharding`, dove la fase «riposo» legge per prima ed è l'unica che
    parte fredda — schermata con `sbilancio —` e `chunk —` su un cluster perfettamente
    distribuito ([M-053](../../docs/Sources.md#m-053)).

    Questa prova apre il proprio client apposta e non usa `stack03`: il client della
    fixture è caldo per costruzione, e su un client caldo il difetto non si riproduce.
    """
    cliente: MongoClient[dict[str, Any]] = connetti(BERSAGLI["sharded"])
    try:
        # Prima operazione in assoluto su questo client. Nessun ping, nessuna scrittura.
        distribuzione = PymongoInspector(cliente, DATABASE).shard_distribution(COLLEZIONE)
    finally:
        cliente.close()

    assert distribuzione.in_un_cluster, "il cluster è acceso, e il client lo deve scoprire"
    assert distribuzione.distribuita, "lab.ordini è distribuita dal seed dello stack 03"
    assert len(distribuzione.conti) == 2


def test_la_distribuzione_per_shard_conta_documenti_e_chunk(
    stack03: MongoClient[dict[str, Any]],
) -> None:
    """La scena del Blocco 3, misurata su una collezione che questa prova crea e distrugge.

    Non usa `lab.ordini` del seed apposta: quel conteggio dipende da quale profilo è stato
    avviato, e una prova che si appoggia a dati che non ha creato racconta lo stato della
    macchina invece del comportamento del codice. Qui si accende lo sharding su un database
    usa-e-getta, si distribuisce la collezione con la stessa chiave del repository —
    `{_id: "hashed"}`, come in `docker/03-sharded/init/30-dati-demo.js` — e si scrivono
    duemila documenti del generatore.

    Le asserzioni sono tre, e nessuna delle tre è un numero esatto: **la somma** dei
    documenti deve fare duemila, **entrambi** gli shard devono comparire, e ognuno deve
    avere almeno un chunk. Un'uguaglianza esatta per shard sarebbe una prova capricciosa —
    dipenderebbe dal bilanciatore, che si muove quando vuole — e la nota 162 vale anche
    qui: si asserisce ciò che il disegno garantisce, non ciò che è capitato la prima volta.
    """
    quanti = 2_000
    with collezione_usa_e_getta(stack03) as collezione:
        nome_completo = f"{collezione.database.name}.{collezione.name}"
        stack03.admin.command("enableSharding", collezione.database.name)
        stack03.admin.command("shardCollection", nome_completo, key={"_id": "hashed"})
        PymongoStore(collezione).insert_many(list(DataGenerator().lotto(quanti)))

        distribuzione = PymongoInspector(
            stack03, collezione.database.name
        ).shard_distribution(collezione.name)

    assert distribuzione.collezione == collezione.name
    assert distribuzione.in_un_cluster
    assert distribuzione.distribuita
    assert len(distribuzione.conti) == 2, "il cluster del repository ha due shard"
    assert distribuzione.documenti == quanti
    assert all(conto.chunk >= 1 for conto in distribuzione.conti)
    assert [conto.shard for conto in distribuzione.conti] == sorted(
        conto.shard for conto in distribuzione.conti
    ), "l'ordine è stabile perché la scena confronta due schermate a distanza di minuti"
    # La quota è il numero che il Blocco 3 mostra, e con una chiave hashed sta vicino a
    # metà. «Vicino» e non «uguale»: asserire 50.0 esatto sarebbe una prova capricciosa.
    for conto in distribuzione.conti:
        quota = distribuzione.quota(conto.shard)
        assert quota is not None and 25.0 < quota < 75.0


def test_una_collezione_non_distribuita_dentro_un_cluster_sharded(
    stack03: MongoClient[dict[str, Any]],
) -> None:
    """Il caso che sembra un difetto e non lo è: sharded il cluster, non la collezione.

    Finché nessuno ha eseguito `shardCollection`, i documenti stanno tutti sullo shard
    primario del database e `$shardedDataDistribution` non ha niente da dire su quella
    collezione. Fino al Task 14 la risposta era la tupla vuota, cioè **la stessa** che dà
    un replica set: il codice negava un cluster che era acceso. Da ADR-0104 la risposta
    dice tutte e tre le cose — il cluster c'è, la collezione non è distribuita, e i
    documenti stanno tutti su questo shard qui, che ha un nome.

    È anche la domanda più frequente di chi vede uno sharded cluster per la prima volta —
    «l'ho acceso, perché non distribuisce?» — ed è la prima metà della scena del Blocco 3.
    """
    quanti = 100
    with collezione_usa_e_getta(stack03) as collezione:
        PymongoStore(collezione).insert_many(list(DataGenerator().lotto(quanti)))
        ispettore = PymongoInspector(stack03, collezione.database.name)
        intera = ispettore.shard_distribution(collezione.name)

        assert intera.collezione == collezione.name
        assert intera.in_un_cluster, "il cluster c'è, ed è la metà che mancava"
        assert not intera.distribuita
        assert intera.primario is not None
        assert intera.documenti == quanti
        assert intera.chunk == 0, "una collezione non distribuita non ha chunk suoi"
        assert intera.quota(intera.primario) == 100.0
        assert int(ispettore.db_stats()["objects"]) == quanti  # type: ignore[call-overload]


@pytest.mark.parametrize("nome", ["lab", "config"])
def test_le_statistiche_attraverso_il_mongos_sommano_gli_shard(
    stack03: MongoClient[dict[str, Any]], nome: str
) -> None:
    """`dbStats` da un mongos aggrega, e lo dichiara con un campo che altrove non c'è.

    `raw` contiene una voce per shard: è la differenza fra leggere le statistiche di un
    cluster e leggere quelle di un server, e chi la ignora crede di guardare una macchina
    mentre ne sta guardando due sommate.
    """
    statistiche = PymongoInspector(stack03, nome).db_stats()

    assert statistiche["db"] == nome
    assert isinstance(statistiche["raw"], dict)
