"""I due rapporti che non sono cronaca: la fotografia di `stats` e il consuntivo di `workload`.

La cronaca è un evento per riga, e la prova sta in `test_presentazione.py`. Questi due
sono l'altra cosa che l'applicazione stampa: uno stato, letto tutto insieme, e un
riassunto, letto alla fine. Hanno regole diverse dalla riga — non scorrono, quindi
possono permettersi più di una riga; ma stanno sullo stesso schermo, quindi il budget di
sala vale anche per loro.

Ciò che queste prove **non** verificano è l'estetica. Verificano che i numeri che il
rapporto dichiara di mostrare ci siano, che quelli che non ci sono si dichiarino assenti
invece di diventare zeri, e che nessuna riga sfori le cento colonne.
"""

from typing import Mapping, Sequence

from mongolab.application.workload import Latenze, Riepilogo
from mongolab.domain.modelli import (
    ContoShard,
    DescrizioneServer,
    DescrizioneTopologia,
    RuoloServer,
    TipoTopologia,
)
from mongolab.domain.porte import ClusterInspector
from mongolab.presentation.rapporto import IGNOTO, rapporto, riassunto
from mongolab.presentation.righe import COLONNE_SALA

from tests.doppi.ispettore import FakeInspector

PRIMARIO = DescrizioneServer(
    indirizzo="mongo-rs-1:27021", ruolo=RuoloServer.PRIMARIO, ritardo_ms=1.25
)
SECONDARIO = DescrizioneServer(
    indirizzo="mongo-rs-2:27022", ruolo=RuoloServer.SECONDARIO, ritardo_ms=1.5
)
CADUTO = DescrizioneServer(
    indirizzo="mongo-rs-3:27023",
    ruolo=RuoloServer.IRRAGGIUNGIBILE,
    errore="AutoReconnect: connection closed",
)

SET = DescrizioneTopologia(
    tipo=TipoTopologia.REPLICA_SET_CON_PRIMARIO,
    server=(PRIMARIO, SECONDARIO),
    nome_set="rs0",
)

STATO: Mapping[str, object] = {
    "process": "mongod",
    "version": "8.0.15",
    "uptime": 11_520.0,
    "connections": {"current": 7},
}

STATISTICHE: Mapping[str, object] = {
    "db": "lab",
    "objects": 50_000,
    "dataSize": 12_582_912,
    "indexSize": 2_097_152,
}


def ispettore(
    *,
    topologia: DescrizioneTopologia = SET,
    stato: Mapping[str, object] = STATO,
    statistiche: Mapping[str, object] = STATISTICHE,
    distribuzione: Sequence[ContoShard] = (),
) -> FakeInspector:
    """Un `FakeInspector` sul caso normale, con le sostituzioni che la prova chiede."""
    return FakeInspector([topologia], stato, statistiche, distribuzione)


# --- La fotografia di `stats` ----------------------------------------------------------


def test_il_rapporto_apre_con_il_titolo() -> None:
    testo = rapporto(ispettore(), titolo="rs (docker/02-replicaset)")

    assert testo.splitlines()[0] == "rs (docker/02-replicaset)"


def test_il_rapporto_nomina_la_forma_della_topologia_e_il_set() -> None:
    testo = rapporto(ispettore(), titolo="rs")

    assert TipoTopologia.REPLICA_SET_CON_PRIMARIO.value in testo
    assert "rs0" in testo


def test_il_rapporto_elenca_i_server_con_ruolo_e_ritardo() -> None:
    testo = rapporto(ispettore(), titolo="rs")

    assert "mongo-rs-1:27021" in testo
    assert RuoloServer.PRIMARIO.value in testo
    assert "1.2 ms" in testo
    assert "mongo-rs-2:27022" in testo
    assert RuoloServer.SECONDARIO.value in testo


def test_un_server_senza_ritardo_non_ne_inventa_uno() -> None:
    """Uno zero direbbe «risponde all'istante» di un server che non ha ancora risposto.

    È la stessa regola che `descrivi_server` applica in `sdam.py`: dove il ritardo manca,
    manca — e il rapporto lo scrive.
    """
    muto = DescrizioneServer(indirizzo="mongo-rs-9:27029", ruolo=RuoloServer.SCONOSCIUTO)
    topologia = DescrizioneTopologia(
        tipo=TipoTopologia.REPLICA_SET_SENZA_PRIMARIO, server=(muto,), nome_set="rs0"
    )

    testo = rapporto(ispettore(topologia=topologia), titolo="rs")
    riga_del_server = next(
        linea for linea in testo.splitlines() if "mongo-rs-9:27029" in linea
    )

    assert "0.0 ms" not in riga_del_server
    assert IGNOTO in riga_del_server


def test_un_indirizzo_lungo_non_si_incolla_al_ruolo() -> None:
    """Misurato al Task 12, la prima volta che l'applicazione ha guardato da dentro.

    Dall'host gli indirizzi sono `localhost:27021`, quindici caratteri. Dalla rete Compose
    sono nomi di servizio, e `mongo-standalone:27017` ne fa **ventidue** — esattamente la
    larghezza della colonna. Il risultato stampato è stato
    `mongo-standalone:27017standalone`, due parole diverse lette come una.
    """
    lungo = DescrizioneServer(
        indirizzo="mongo-standalone:27017",
        ruolo=RuoloServer.STANDALONE,
        ritardo_ms=0.7,
    )
    topologia = DescrizioneTopologia(tipo=TipoTopologia.SINGOLA, server=(lungo,))

    testo = rapporto(ispettore(topologia=topologia), titolo="standalone")
    riga = next(
        linea for linea in testo.splitlines() if "mongo-standalone:27017" in linea
    )

    assert "mongo-standalone:27017standalone" not in riga
    assert "mongo-standalone:27017 " in riga


def test_le_colonne_dei_server_restano_allineate() -> None:
    # La colonna si allarga per il più lungo, non per ciascuno: tre righe con indirizzi
    # di lunghezza diversa devono cominciare il ruolo alla stessa colonna, o la
    # fotografia si legge peggio di un elenco.
    # I due ruoli sono scelti perché nessuna delle due parole compare dentro l'indirizzo
    # della propria riga: una prova che cercasse «standalone» dentro
    # «mongo-standalone:27017» misurerebbe l'indirizzo invece della colonna.
    corto = DescrizioneServer(
        indirizzo="mongos:27017", ruolo=RuoloServer.ROUTER, ritardo_ms=0.4
    )
    lungo = DescrizioneServer(
        indirizzo="mongo-config-server:27017",
        ruolo=RuoloServer.PRIMARIO,
        ritardo_ms=0.7,
    )
    topologia = DescrizioneTopologia(tipo=TipoTopologia.SINGOLA, server=(corto, lungo))

    testo = rapporto(ispettore(topologia=topologia), titolo="misto")
    righe = [linea for linea in testo.splitlines() if ":27017" in linea]

    assert righe[0].index(RuoloServer.ROUTER.value) == righe[1].index(
        RuoloServer.PRIMARIO.value
    )


def test_un_server_irraggiungibile_mostra_perche() -> None:
    topologia = DescrizioneTopologia(
        tipo=TipoTopologia.REPLICA_SET_SENZA_PRIMARIO,
        server=(SECONDARIO, CADUTO),
        nome_set="rs0",
    )

    testo = rapporto(ispettore(topologia=topologia), titolo="rs")

    assert "AutoReconnect" in testo


def test_il_rapporto_legge_server_status() -> None:
    testo = rapporto(ispettore(), titolo="rs")

    assert "mongod" in testo
    assert "8.0.15" in testo
    assert "attivo da 3 h 12 m" in testo
    assert "connessioni 7" in testo


def test_un_server_status_di_mongos_non_fa_esplodere_il_rapporto() -> None:
    """Attraverso un mongos metà dei campi non ci sono, e `inspector.py` lo dichiara.

    Un rapporto che pretendesse `connections.current` andrebbe in `KeyError` proprio
    sullo stack 03, cioè nell'unico caso in cui la fotografia serve a spiegare che il
    router non è un mongod.

    Le due voci si nominano una per una, e non con un `IGNOTO in testo`: quella forma
    passa finché **una qualunque** delle due manca, e una mutazione che trasformasse il
    solo `uptime` assente in `attivo da 0 s` le sopravvivrebbe — cioè sopravvivrebbe
    scrivendo che il mongos è appena partito. Provata rompendo, è successo davvero.
    """
    testo = rapporto(
        ispettore(stato={"process": "mongos", "version": "8.0.15"}), titolo="sharded"
    )

    assert "mongos" in testo
    assert f"attivo da {IGNOTO}" in testo
    assert f"connessioni {IGNOTO}" in testo


def test_il_rapporto_legge_db_stats() -> None:
    testo = rapporto(ispettore(), titolo="rs")

    assert "lab" in testo
    assert "50000 documenti" in testo
    assert "dati 12.0 MB" in testo
    assert "indici 2.0 MB" in testo


def test_senza_shard_il_rapporto_lo_dice() -> None:
    # Una riga assente si legge come una dimenticanza; una riga che dichiara il vuoto si
    # legge come una risposta. Su un replica set la domanda «e gli shard?» è legittima.
    testo = rapporto(ispettore(), titolo="rs")

    assert "shard" in testo


def test_con_gli_shard_il_rapporto_li_elenca() -> None:
    distribuzione = (
        ContoShard(shard="shard01", documenti=30_000, chunk=12),
        ContoShard(shard="shard02", documenti=20_000, chunk=11),
    )

    testo = rapporto(ispettore(distribuzione=distribuzione), titolo="sharded")

    assert "shard01" in testo
    assert "30000 documenti" in testo
    assert "12 chunk" in testo
    assert "shard02" in testo
    assert "11 chunk" in testo


def test_il_rapporto_guarda_la_topologia_una_volta_sola() -> None:
    # Due letture darebbero due fotografie diverse durante un'elezione, e il rapporto
    # racconterebbe uno stato che non è mai esistito.
    doppio = ispettore()

    rapporto(doppio, titolo="rs")

    assert doppio.letture == 1


def test_il_rapporto_sta_nel_budget_di_sala() -> None:
    distribuzione = tuple(
        ContoShard(shard=f"shard{numero:02d}", documenti=10_000, chunk=7)
        for numero in range(1, 4)
    )
    topologia = DescrizioneTopologia(
        tipo=TipoTopologia.SHARDED, server=(PRIMARIO, SECONDARIO, CADUTO)
    )

    testo = rapporto(
        ispettore(topologia=topologia, distribuzione=distribuzione),
        titolo="sharded (docker/03-sharded)",
    )

    for linea in testo.splitlines():
        assert len(linea) <= COLONNE_SALA, linea


# --- Il consuntivo di `workload` -------------------------------------------------------

CORSA = Riepilogo(
    scritture=3200,
    riuscite=3198,
    fallite=2,
    ritentate=5,
    documenti_confermati=3198,
    latenze=Latenze(
        campioni=3198,
        minimo_ms=0.4,
        mediana_ms=1.2,
        p95_ms=4.8,
        p99_ms=12.0,
        massimo_ms=30.1,
    ),
)


def test_il_riassunto_conta_le_scritture() -> None:
    testo = riassunto(CORSA)

    assert "3200 scritture" in testo
    assert "3198 confermate" in testo
    assert "2 fallite" in testo
    assert "5 ritentate" in testo


def test_il_riassunto_da_i_percentili() -> None:
    testo = riassunto(CORSA)

    assert "1.2" in testo
    assert "4.8" in testo
    assert "12.0" in testo


def test_senza_latenze_il_riassunto_non_ne_stampa() -> None:
    """`latenze=None` vuol dire «nessuna scrittura è riuscita», non «zero millisecondi».

    Stampare un p95 di zero su una corsa in cui non è passato niente è il numero più
    fuorviante che questa applicazione potrebbe mettere su uno schermo, e la docstring di
    `Riepilogo` lo dice già. Qui si verifica che il rapporto la rispetti.
    """
    caduta = Riepilogo(
        scritture=10,
        riuscite=0,
        fallite=10,
        ritentate=0,
        documenti_confermati=0,
        latenze=None,
    )

    testo = riassunto(caduta)

    assert "p95" not in testo
    assert "0.0 ms" not in testo


def test_senza_lettori_il_riassunto_non_parla_di_letture() -> None:
    testo = riassunto(CORSA)

    assert "letture" not in testo


def test_con_i_lettori_il_riassunto_ha_la_sua_riga() -> None:
    con_letture = Riepilogo(
        scritture=3200,
        riuscite=3198,
        fallite=2,
        ritentate=5,
        documenti_confermati=3198,
        latenze=CORSA.latenze,
        letture=1500,
        letture_riuscite=1498,
        letture_fallite=2,
        documenti_letti=29_960,
        latenze_letture=Latenze(
            campioni=1498,
            minimo_ms=0.2,
            mediana_ms=0.9,
            p95_ms=3.3,
            p99_ms=7.7,
            massimo_ms=15.0,
        ),
    )

    testo = riassunto(con_letture)

    assert "letture" in testo
    assert "1500 letture" in testo
    assert "29960 documenti" in testo
    assert "3.3" in testo


def test_il_riassunto_sta_nel_budget_di_sala() -> None:
    for linea in riassunto(CORSA).splitlines():
        assert len(linea) <= COLONNE_SALA, linea

# --- In che ordine il rapporto interroga --------------------------------------------


class IspettoreCheRicorda:
    """Un `ClusterInspector` che annota in che ordine gli è stato chiesto qualcosa.

    Sta qui e non in `tests/doppi/` perché serve a una prova sola, e a una prova che non
    parla del cluster ma del **rapporto**: nessun'altra parte del progetto ha motivo di
    sapere in che sequenza si interroga un ispettore.
    """

    def __init__(self) -> None:
        self.chiamate: list[str] = []

    def topology(self) -> DescrizioneTopologia:
        self.chiamate.append("topology")
        return SET

    def server_status(self) -> Mapping[str, object]:
        self.chiamate.append("server_status")
        return STATO

    def db_stats(self) -> Mapping[str, object]:
        self.chiamate.append("db_stats")
        return STATISTICHE

    def shard_distribution(self) -> tuple[ContoShard, ...]:
        self.chiamate.append("shard_distribution")
        return ()


def test_il_rapporto_guarda_la_topologia_per_ultima() -> None:
    """L'ordine di lettura è l'opposto dell'ordine di stampa, e non è un caso.

    `topology()` riferisce ciò che il client crede **adesso**, senza aspettare: è la
    proprietà che rende visibile l'attimo in cui, durante un'elezione, il client non sa
    ancora. Su un client appena costruito però quell'attimo è l'avvio, e chiedergli la
    topologia per prima significa fotografare uno standalone sanissimo come
    `sconosciuta`. È successo davvero, eseguendo `mongolab stats --target standalone`
    contro lo stack 01. `server_status()` esegue un comando, quindi costringe il driver
    a una selezione: letto per primo, garantisce che il client abbia guardato.
    """
    doppio: ClusterInspector = IspettoreCheRicorda()

    rapporto(doppio, titolo="rs")

    assert isinstance(doppio, IspettoreCheRicorda)
    assert doppio.chiamate[0] == "server_status"
    assert doppio.chiamate[-1] == "topology"
