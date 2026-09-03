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
from mongolab.infrastructure.generatore import DataGenerator
from mongolab.infrastructure.inspector import PymongoInspector
from mongolab.infrastructure.store import PymongoStore

from tests.integration.ambiente import PREFISSO_PROVE, collezione_usa_e_getta

# --- Lo stack 01: istanza singola ------------------------------------------------------


def test_l_ispettore_passa_per_la_porta(stack01: MongoClient[dict[str, Any]]) -> None:
    """La conformità strutturale, verificata dove mypy la verifica: in un'annotazione."""
    ispettore: ClusterInspector = PymongoInspector(stack01, "lab", "ordini")
    assert ispettore.topology().server


def test_la_topologia_di_un_istanza_singola(stack01: MongoClient[dict[str, Any]]) -> None:
    """Un mongod da solo: una forma `SINGOLA`, un server, ruolo `STANDALONE`, nessun set.

    Il ponte SDAM del Task 7 sapeva tradurre le stringhe di pymongo nei tipi del dominio,
    e questa è la prima volta che le stringhe arrivano da un server invece che da una
    prova. `nome_set` è `None` perché non c'è nessun set: è il valore che distingue
    un'istanza singola da un membro visto da vicino, e il Task 12 lo userà.
    """
    topologia = PymongoInspector(stack01, "lab", "ordini").topology()

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
    stato = PymongoInspector(stack01, "lab", "ordini").server_status()

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
    ispettore = PymongoInspector(stack01, "lab", "ordini")
    statistiche = ispettore.db_stats()

    assert statistiche["db"] == "lab"
    assert isinstance(statistiche["dataSize"], (int, float))
    assert int(statistiche["objects"]) > 0  # type: ignore[call-overload]

    vuoto = PymongoInspector(stack01, f"{PREFISSO_PROVE}mai_creato", "ordini").db_stats()
    assert vuoto["db"] == f"{PREFISSO_PROVE}mai_creato"
    assert vuoto["objects"] == 0


def test_su_un_istanza_singola_non_c_e_distribuzione_per_shard(
    stack01: MongoClient[dict[str, Any]],
) -> None:
    """Tupla vuota, e **non** un'eccezione: lo dice la porta.

    La strada facile sarebbe eseguire `$shardedDataDistribution` e catturare l'errore. Su
    un mongod solleva davvero — codice 6789101, «can only be run on mongoS», misurato —
    ma catturare un errore per dedurne una topologia è una deduzione fragile: il giorno in
    cui il codice cambia o l'utente non ha i permessi, «non è sharded» diventa la risposta
    a una domanda diversa. L'ispettore lo chiede alla topologia, che il driver conosce già.
    """
    assert PymongoInspector(stack01, "lab", "ordini").shard_distribution() == ()


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
    topologia = PymongoInspector(stack02, "lab", "ordini").topology()

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
    stato = PymongoInspector(stack02, "lab", "ordini").server_status()
    repl = stato["repl"]

    assert isinstance(repl, dict)
    assert repl["setName"] == "rs0"
    assert repl["isWritablePrimary"] is True


def test_un_replica_set_non_ha_distribuzione_per_shard(
    stack02: MongoClient[dict[str, Any]],
) -> None:
    assert PymongoInspector(stack02, "lab", "ordini").shard_distribution() == ()


# --- Lo stack 03: sharded cluster -----------------------------------------------------


def test_il_mongos_si_presenta_come_router(stack03: MongoClient[dict[str, Any]]) -> None:
    """Un mongos non è un mongod, e il dominio ha un ruolo apposta.

    Qui, a differenza del 02, il client **non** usa `directConnection`: un mongos è già il
    punto d'ingresso, quindi la scoperta non porta altrove e la topologia si legge per
    quello che è.
    """
    topologia = PymongoInspector(stack03, "lab", "ordini").topology()

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
    stato = PymongoInspector(stack03, "lab", "ordini").server_status()

    assert stato["process"] == "mongos"
    assert "wiredTiger" not in stato


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
            stack03, collezione.database.name, collezione.name
        ).shard_distribution()

    assert len(distribuzione) == 2, "il cluster del repository ha due shard"
    assert sum(conto.documenti for conto in distribuzione) == quanti
    assert all(conto.chunk >= 1 for conto in distribuzione)
    assert [conto.shard for conto in distribuzione] == sorted(
        conto.shard for conto in distribuzione
    ), "l'ordine è stabile perché la scena confronta due schermate a distanza di minuti"


def test_una_collezione_non_distribuita_dentro_un_cluster_sharded(
    stack03: MongoClient[dict[str, Any]],
) -> None:
    """Il caso che sembra un difetto e non lo è: sharded il cluster, non la collezione.

    Finché nessuno ha eseguito `shardCollection`, i documenti stanno tutti sullo shard
    primario del database e `$shardedDataDistribution` non ha niente da dire su quella
    collezione. La tupla esce vuota, ed è la risposta giusta: **non c'è** una
    distribuzione, che è diverso da «la distribuzione è tutta da una parte».

    È anche la domanda più frequente di chi vede uno sharded cluster per la prima volta —
    «l'ho acceso, perché non distribuisce?» — e vale la pena che il codice abbia una
    risposta invece di un conteggio che sembra sbagliato.
    """
    with collezione_usa_e_getta(stack03) as collezione:
        PymongoStore(collezione).insert_many(list(DataGenerator().lotto(100)))
        ispettore = PymongoInspector(stack03, collezione.database.name, collezione.name)

        assert ispettore.shard_distribution() == ()
        assert int(ispettore.db_stats()["objects"]) == 100  # type: ignore[call-overload]


@pytest.mark.parametrize("nome", ["lab", "config"])
def test_le_statistiche_attraverso_il_mongos_sommano_gli_shard(
    stack03: MongoClient[dict[str, Any]], nome: str
) -> None:
    """`dbStats` da un mongos aggrega, e lo dichiara con un campo che altrove non c'è.

    `raw` contiene una voce per shard: è la differenza fra leggere le statistiche di un
    cluster e leggere quelle di un server, e chi la ignora crede di guardare una macchina
    mentre ne sta guardando due sommate.
    """
    statistiche = PymongoInspector(stack03, nome, "ordini").db_stats()

    assert statistiche["db"] == nome
    assert isinstance(statistiche["raw"], dict)
