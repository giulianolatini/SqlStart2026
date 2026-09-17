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

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping, Sequence

from mongolab.application.scenari import EsitoFailover
from mongolab.application.scenari import (
    EsitoBackup,
    EsitoRestore,
    EsitoSharding,
    Ritmo,
)
from mongolab.application.topologia import Bilancio, Interruzione
from mongolab.application.workload import Latenze, Riepilogo
from mongolab.domain.modelli import (
    ContoCollezione,
    ContoShard,
    DescrizioneServer,
    DescrizioneTopologia,
    Distribuzione,
    Piano,
    Progress,
    RuoloServer,
    TipoTopologia,
)
from mongolab.domain.porte import ClusterInspector
from mongolab.presentation.rapporto import (
    IGNOTO,
    copia,
    cronaca,
    rapporto,
    riassunto,
    ripristino,
    spartizione,
)
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


COLLEZIONI = (ContoCollezione(nome="ordini", documenti=50_000),)


def ispettore(
    *,
    topologia: DescrizioneTopologia = SET,
    stato: Mapping[str, object] = STATO,
    statistiche: Mapping[str, object] = STATISTICHE,
    distribuzione: Distribuzione | None = None,
    collezioni: Sequence[ContoCollezione] = COLLEZIONI,
) -> FakeInspector:
    """Un `FakeInspector` sul caso normale, con le sostituzioni che la prova chiede."""
    distribuzioni = (
        {} if distribuzione is None else {distribuzione.collezione: [distribuzione]}
    )
    return FakeInspector(
        [topologia], stato, statistiche, distribuzioni, collezioni=collezioni
    )


def sparsa(*conti: ContoShard, collezione: str = "ordini") -> Distribuzione:
    """Una collezione distribuita su questi shard, con il primo come primario."""
    return Distribuzione(
        collezione=collezione,
        distribuita=True,
        primario=conti[0].shard,
        conti=conti,
    )


# --- La fotografia di `stats` ----------------------------------------------------------


def test_il_rapporto_apre_con_il_titolo() -> None:
    testo = rapporto(ispettore(), collezione="ordini", titolo="rs (docker/02-replicaset)")

    assert testo.splitlines()[0] == "rs (docker/02-replicaset)"


def test_il_rapporto_nomina_la_forma_della_topologia_e_il_set() -> None:
    testo = rapporto(ispettore(), collezione="ordini", titolo="rs")

    assert TipoTopologia.REPLICA_SET_CON_PRIMARIO.value in testo
    assert "rs0" in testo


def test_il_rapporto_elenca_i_server_con_ruolo_e_ritardo() -> None:
    testo = rapporto(ispettore(), collezione="ordini", titolo="rs")

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

    testo = rapporto(ispettore(topologia=topologia), collezione="ordini", titolo="rs")
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

    testo = rapporto(ispettore(topologia=topologia), collezione="ordini", titolo="standalone")
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

    testo = rapporto(ispettore(topologia=topologia), collezione="ordini", titolo="misto")
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

    testo = rapporto(ispettore(topologia=topologia), collezione="ordini", titolo="rs")

    assert "AutoReconnect" in testo


def test_il_rapporto_legge_server_status() -> None:
    testo = rapporto(ispettore(), collezione="ordini", titolo="rs")

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
        ispettore(stato={"process": "mongos", "version": "8.0.15"}), collezione="ordini", titolo="sharded"
    )

    assert "mongos" in testo
    assert f"attivo da {IGNOTO}" in testo
    assert f"connessioni {IGNOTO}" in testo


def test_il_rapporto_legge_db_stats() -> None:
    testo = rapporto(ispettore(), collezione="ordini", titolo="rs")

    assert "lab" in testo
    assert "50000 documenti" in testo
    assert "dati 12.0 MB" in testo
    assert "indici 2.0 MB" in testo


def test_il_rapporto_elenca_le_collezioni_con_i_loro_documenti() -> None:
    """Il difetto che questa prova toglie e' costato una lettura sbagliata dello stato
    atteso: `dbStats` risponde per **database**, e la riga «50000 documenti» diventa
    62 602 appena una corsa dell'Atto III lascia in giro una collezione di carico. Chi
    controllava leggeva un guasto dove non c'era. Il dettaglio per collezione toglie la
    domanda: si legge quale numero appartiene a chi.
    """
    testo = rapporto(
        ispettore(
            collezioni=(
                ContoCollezione(nome="carico-20260906-153012", documenti=5_886),
                ContoCollezione(nome="ordini", documenti=50_000),
            )
        ),
        collezione="ordini",
        titolo="rs",
    )

    assert "carico-20260906-153012" in testo
    assert "5886 documenti" in testo
    assert "ordini" in testo
    assert "50000 documenti" in testo


def test_il_totale_del_database_sta_dopo_il_dettaglio_delle_collezioni() -> None:
    """L'ordine e' il messaggio: prima di che cosa e' fatto, poi quanto fa in tutto.

    Non e' impaginazione. La riga del database e' una **somma**, e una somma stampata
    sopra i suoi addendi si legge come se fosse il primo di essi — che e' precisamente
    l'errore di lettura da cui questa scena viene.
    """
    testo = rapporto(ispettore(), collezione="ordini", titolo="rs")
    righe = testo.splitlines()

    prima_collezione = next(i for i, r in enumerate(righe) if r.startswith("collezioni"))
    totale = next(i for i, r in enumerate(righe) if r.startswith("database"))

    assert prima_collezione < totale


def test_un_database_senza_collezioni_dichiara_il_vuoto() -> None:
    # La stessa regola di `_shard`: una riga assente si legge come una dimenticanza, una
    # riga che dichiara il vuoto si legge come una risposta. Su uno stack appena acceso
    # prima del seed la domanda «e le collezioni?» e' legittima.
    testo = rapporto(ispettore(collezioni=()), collezione="ordini", titolo="rs")

    assert "nessuna" in testo


def test_senza_shard_il_rapporto_lo_dice() -> None:
    # Una riga assente si legge come una dimenticanza; una riga che dichiara il vuoto si
    # legge come una risposta. Su un replica set la domanda «e gli shard?» è legittima.
    testo = rapporto(ispettore(), collezione="ordini", titolo="rs")

    assert "questo non è uno sharded cluster" in testo


def test_con_gli_shard_il_rapporto_li_elenca_con_la_loro_quota() -> None:
    distribuzione = sparsa(
        ContoShard(shard="shard01", documenti=30_000, chunk=12),
        ContoShard(shard="shard02", documenti=20_000, chunk=11),
    )

    testo = rapporto(
        ispettore(distribuzione=distribuzione), collezione="ordini", titolo="sharded"
    )

    assert "shard01" in testo
    assert "30000 documenti" in testo
    assert "12 chunk" in testo
    assert "shard02" in testo
    assert "11 chunk" in testo
    # La percentuale accanto al conteggio: due numeri grezzi si confrontano a mente, e
    # dalla decima fila nessuno lo fa. È il numero che il Blocco 3 esiste per mostrare.
    assert "60%" in testo
    assert "40%" in testo


def test_una_collezione_non_distribuita_non_si_legge_come_un_replica_set() -> None:
    """Il punto aperto che ADR-0104 chiude, visto dallo schermo.

    Fino al Task 14 questi due casi producevano la stessa riga — «nessuno: questo non è
    uno sharded cluster» — perché arrivavano qui come la stessa tupla vuota. Uno dei due
    è la scena del Blocco 3: un cluster c'è, e la collezione sta tutta su uno shard solo.
    """
    intera = Distribuzione(
        collezione="carico-20260918-093000",
        distribuita=False,
        primario="shard1rs",
        conti=(ContoShard(shard="shard1rs", documenti=2_000, chunk=0),),
    )

    testo = rapporto(
        ispettore(distribuzione=intera),
        collezione="carico-20260918-093000",
        titolo="sharded",
    )

    assert "non è distribuita" in testo
    assert "shard1rs" in testo
    assert "2000 documenti" in testo
    assert "questo non è uno sharded cluster" not in testo


def test_il_rapporto_guarda_la_topologia_una_volta_sola() -> None:
    # Due letture darebbero due fotografie diverse durante un'elezione, e il rapporto
    # racconterebbe uno stato che non è mai esistito.
    doppio = ispettore()

    rapporto(doppio, collezione="ordini", titolo="rs")

    assert doppio.letture == 1


def test_il_rapporto_sta_nel_budget_di_sala() -> None:
    distribuzione = sparsa(
        *(
            ContoShard(shard=f"shard{numero:02d}", documenti=10_000, chunk=7)
            for numero in range(1, 4)
        )
    )
    topologia = DescrizioneTopologia(
        tipo=TipoTopologia.SHARDED, server=(PRIMARIO, SECONDARIO, CADUTO)
    )

    testo = rapporto(
        ispettore(topologia=topologia, distribuzione=distribuzione),
        collezione="ordini", titolo="sharded (docker/03-sharded)",
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

    def collection_counts(self) -> tuple[ContoCollezione, ...]:
        self.chiamate.append("collection_counts")
        return COLLEZIONI

    def shard_distribution(self, collezione: str) -> Distribuzione:
        self.chiamate.append("shard_distribution")
        return Distribuzione(
            collezione=collezione, distribuita=False, primario=None, conti=()
        )


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

    rapporto(doppio, collezione="ordini", titolo="rs")

    assert isinstance(doppio, IspettoreCheRicorda)
    assert doppio.chiamate[0] == "server_status"
    assert doppio.chiamate[-1] == "topology"


# --- La cronaca del failover: i due numeri che chiudono la scena -----------------------
#
# Sono i due numeri per cui l'applicazione esiste — il §6.3 li chiama per nome, «durata
# dell'interruzione» e «scritture perse» — e questa sezione verifica l'unica cosa che li
# riguarda a questo livello: che si **leggano**. Che siano giusti lo provano
# `test_topologia.py` e `test_scenari.py`; che finiscano su una riga che si legge dalla
# decima fila lo può provare solo chi la scrive.

INTERROTTA = Interruzione(
    inizio=datetime(2026, 9, 18, 10, 30, 0, tzinfo=UTC),
    primario_prima="mongo-rs-1:27017",
    fine=datetime(2026, 9, 18, 10, 30, 9, 812_000, tzinfo=UTC),
    primario_dopo="mongo-rs-2:27017",
)

SCENA = EsitoFailover(
    fasi=("carico", "guasto", "elezione", "ripresa", "recupero", "bilancio"),
    prima=CORSA,
    durante=CORSA,
    dopo=CORSA,
    bilancio=Bilancio(interruzione=INTERROTTA, confermate=12_901, ritrovate=12_901),
    interruzioni=(INTERROTTA,),
)


def test_la_cronaca_apre_con_i_due_numeri() -> None:
    """Prima riga, e nient'altro prima: sono la conclusione, non un dettaglio.

    Un consuntivo che li mettesse in fondo li farebbe scorrere via insieme alle latenze,
    e chi guarda dalla sala legge la prima riga e le ultime due.
    """
    prima = cronaca(SCENA).splitlines()[0]

    assert "9812" in prima.replace(" ", "").replace(" ", "")
    assert "perse 0" in prima


def test_la_cronaca_dice_chi_ha_preso_il_posto_di_chi() -> None:
    testo = cronaca(SCENA)

    assert "mongo-rs-1:27017" in testo
    assert "mongo-rs-2:27017" in testo


def test_un_primario_che_torna_non_e_un_avvicendamento() -> None:
    """Stesso nodo prima e dopo: c'è stata un'interruzione, non un'elezione.

    `Interruzione.e_un_failover` fa già questa distinzione, e la cronaca la rispetta:
    scrivere «da mongo-rs-1 a mongo-rs-1» sarebbe una riga che si legge come un errore
    di stampa proprio nel momento in cui va letta con attenzione.
    """
    tornato = replace(INTERROTTA, primario_dopo="mongo-rs-1:27017")
    scena = replace(
        SCENA,
        bilancio=Bilancio(interruzione=tornato, confermate=10, ritrovate=10),
        interruzioni=(tornato,),
    )

    assert " a mongo-rs-1:27017" not in cronaca(scena)


def test_senza_interruzione_il_numero_e_il_segno_del_mancante() -> None:
    """Non zero: zero direbbe «non è durata niente» dove la verità è «non è successo».

    È la stessa scelta di `Interruzione.durata_ms`, portata fino allo schermo. Uno zero
    in quella casella passerebbe per una misura — e sarebbe la misura di un failover
    perfetto, cioè esattamente ciò che si vede quando il guasto non è avvenuto.
    """
    scena = replace(
        SCENA,
        bilancio=Bilancio(interruzione=None, confermate=10, ritrovate=10),
        interruzioni=(),
    )

    assert IGNOTO in cronaca(scena).splitlines()[0]


def test_la_cronaca_conta_le_scritture_dei_due_versi() -> None:
    """Perse e non confermate sono due voci, perché sono due fenomeni.

    Confermate meno ritrovate sono scritture che il client credeva salve; ritrovate meno
    confermate sono scritture applicate la cui conferma si è persa mentre il primario
    cadeva. Un solo campo firmato scriverebbe «-17 perse», che è aritmetica giusta e
    cronaca sbagliata.
    """
    scena = replace(
        SCENA, bilancio=Bilancio(interruzione=INTERROTTA, confermate=100, ritrovate=83)
    )

    testo = cronaca(scena)

    assert "perse 17" in testo
    assert "100 confermate" in testo
    assert "83 ritrovate" in testo


def test_la_cronaca_elenca_le_fasi_nell_ordine_in_cui_sono_andate() -> None:
    testo = cronaca(SCENA)

    posizioni = [testo.index(fase) for fase in SCENA.fasi if fase != "bilancio"]
    assert posizioni == sorted(posizioni)


def test_la_cronaca_sta_nel_budget_di_sala() -> None:
    for linea in cronaca(SCENA).splitlines():
        assert len(linea) <= COLONNE_SALA, linea


# --- L'Atto III: il ritmo del dump, e i due conteggi del restore ------------------------

DESTINAZIONE = Path("/lab/backup/2026-09-18")

SANO = Ritmo(replace(CORSA, scritture=4000, riuscite=4000, fallite=0, documenti_confermati=4000), durata_s=4.0)
"""Mille documenti al secondo con il cluster tranquillo."""

SOTTO_DUMP = Ritmo(replace(CORSA, scritture=460, riuscite=460, fallite=0, documenti_confermati=460), durata_s=0.5)
"""Novecentoventi al secondo durante il dump: un otto per cento in meno, che è la forma
del numero che il copione promette — un calo che si vede e non un crollo."""

COPIA = EsitoBackup(
    fasi=("carico", "dump", "bilancio"),
    prima=SANO,
    durante=SOTTO_DUMP,
    destinazione=DESTINAZIONE,
    avanzamenti=(
        Progress("dump", 0, None, "writing lab.carico"),
        Progress("dump", 4460, 4460, "done dumping lab.carico (4460 documents)"),
    ),
    documenti=4460,
)


def test_la_copia_apre_con_i_due_ritmi_accostati() -> None:
    """La tesi dell'Atto III sta sulla prima riga, come i due numeri del failover.

    «Il dump non fa crollare il throughput» si verifica leggendo due numeri vicini. Se il
    secondo stesse tre righe sotto il primo, la sala dovrebbe fare la sottrazione da sé
    mentre la scena è già passata.
    """
    prima = copia(COPIA).splitlines()[0]

    assert "1000" in prima
    assert "920" in prima


def test_la_copia_dice_di_quanto_e_calato_il_ritmo() -> None:
    testo = copia(COPIA)

    assert "8" in testo
    assert "%" in testo


def test_senza_un_ritmo_prima_la_copia_non_inventa_una_percentuale() -> None:
    """Un `-inf%` sulla slide sarebbe peggio di nessun numero: `IGNOTO` si legge come
    «non c'era»."""
    vuoto = replace(
        COPIA, prima=Ritmo(replace(CORSA, scritture=0, riuscite=0, fallite=0, documenti_confermati=0), 1.0)
    )

    assert IGNOTO in copia(vuoto)


def test_la_copia_dice_dove_e_finito_il_dump() -> None:
    """Il percorso serve per il `demo restore` che viene dopo: senza, chi guida la demo
    deve ricordarselo."""
    assert str(DESTINAZIONE) in copia(COPIA)


def test_la_copia_riporta_l_ultima_riga_del_dump() -> None:
    """`done dumping lab.carico (4460 documents)` è la conferma che `mongodump` dà di sé.
    Riportarla è la differenza fra dire che il dump è andato bene e mostrarlo."""
    assert "done dumping" in copia(COPIA)


def test_la_copia_sta_nel_budget_di_sala() -> None:
    for linea in copia(COPIA).splitlines():
        assert len(linea) <= COLONNE_SALA, linea


RIPRISTINO = EsitoRestore(
    fasi=("restore", "verifica"),
    sorgente=DESTINAZIONE,
    destinazione="lab_restore",
    documenti_origine=4460,
    documenti_destinazione=4402,
    avanzamenti=(Progress("restore", 4402, 4402, "4402 document(s) restored"),),
)


def test_il_ripristino_apre_con_i_due_conteggi() -> None:
    prima = ripristino(RIPRISTINO).splitlines()[0]

    assert "4460" in prima
    assert "4402" in prima


def test_il_ripristino_dice_la_differenza_e_non_la_chiama_errore() -> None:
    """Cinquantotto documenti mancanti sono il prezzo del backup a caldo, non un guasto.

    Sono quelli scritti **durante** la finestra del dump: stanno nell'oplog che questo
    restore non riapplica, perché `--oplogReplay` è incompatibile con la rinomina dei
    namespace che serve a restaurare altrove. Una riga che li chiamasse «persi» direbbe
    una cosa falsa nel momento in cui la sala sta imparando la cosa vera.
    """
    testo = ripristino(RIPRISTINO)

    assert "58" in testo
    assert "perse" not in testo
    assert "perduti" not in testo


def test_un_ripristino_che_combacia_lo_dice() -> None:
    intero = replace(RIPRISTINO, documenti_destinazione=4460)

    assert "0" in ripristino(intero).splitlines()[0]


def test_il_ripristino_nomina_i_due_database() -> None:
    assert "lab_restore" in ripristino(RIPRISTINO)
    assert str(DESTINAZIONE) in ripristino(RIPRISTINO)


def test_il_ripristino_sta_nel_budget_di_sala() -> None:
    for linea in ripristino(RIPRISTINO).splitlines():
        assert len(linea) <= COLONNE_SALA, linea


# --- Il Blocco 3: le due colonne, i chunk fermi e i due piani ---------------------------

NON_DISTRIBUITA = Distribuzione(
    collezione="carico-20260918-093000",
    distribuita=False,
    primario="shard1rs",
    conti=(ContoShard(shard="shard1rs", documenti=2_000, chunk=0),),
)

A_RIPOSO = Distribuzione(
    collezione="ordini",
    distribuita=True,
    primario="shard1rs",
    conti=(
        ContoShard(shard="shard1rs", documenti=10_000, chunk=2),
        ContoShard(shard="shard2rs", documenti=10_000, chunk=2),
    ),
)

DOPO_IL_CARICO = Distribuzione(
    collezione="ordini",
    distribuita=True,
    primario="shard1rs",
    conti=(
        ContoShard(shard="shard1rs", documenti=11_200, chunk=2),
        ContoShard(shard="shard2rs", documenti=10_800, chunk=2),
    ),
)
"""Milleduecento arrivi contro ottocento: sessanta a quaranta, venti punti di sbilancio.

Sui **totali** gli stessi numeri darebbero due punti, ed è la ragione per cui lo sbilancio
non si misura lì: i ventimila del seed diluiscono qualunque squilibrio del carico."""


def _spartizione(
    *,
    dopo: Distribuzione = DOPO_IL_CARICO,
    scritte_intera: int = 2_000,
    scritte_sparsa: int = 2_000,
) -> EsitoSharding:
    return EsitoSharding(
        fasi=("riposo", "non-distribuita", "distribuita", "piani", "bilancio"),
        intera=NON_DISTRIBUITA,
        prima=A_RIPOSO,
        dopo=dopo,
        carico_intera=replace(CORSA, scritture=scritte_intera),
        carico_sparsa=replace(CORSA, scritture=scritte_sparsa),
        mirata=Piano(filtro={"_id": 4242}, stadio="SINGLE_SHARD", shard=("shard1rs",)),
        sparpagliata=Piano(
            filtro={"citta": "Ancona"},
            stadio="SHARD_MERGE",
            shard=("shard1rs", "shard2rs"),
        ),
    )


def test_la_spartizione_accosta_le_due_collezioni_con_i_conteggi_per_shard() -> None:
    """Le due colonne sono la scena: senza l'altra, una sola non dimostra niente."""
    testo = spartizione(_spartizione())

    assert "carico-20260918-093000" in testo
    assert "non è distribuita" in testo
    assert "2000 documenti su shard1rs" in testo
    assert "11200 documenti" in testo
    assert "10800 documenti" in testo
    # E la riga che rende le due colonne confrontabili: duemila scritti da una parte,
    # duemila dall'altra, e qui si vede dove sono finiti.
    assert "shard1rs 1200" in testo
    assert "shard2rs 800" in testo


def test_la_spartizione_dice_lo_sbilancio_in_punti_percentuali() -> None:
    testo = spartizione(_spartizione())

    assert "sbilancio" in testo
    assert "20 punti" in testo
    # Un punto solo si scrive al singolare: è una schermata italiana, e «1 punti» è la
    # svista che si nota dalla prima fila.
    assert "1 punto" in spartizione(_spartizione(dopo=_di_un_punto()))


def _di_un_punto() -> Distribuzione:
    """Milledieci arrivi contro novecentonovanta: 50,5 contro 49,5, cioè un punto."""
    return Distribuzione(
        collezione="ordini",
        distribuita=True,
        primario="shard1rs",
        conti=(
            ContoShard(shard="shard1rs", documenti=11_010, chunk=2),
            ContoShard(shard="shard2rs", documenti=10_990, chunk=2),
        ),
    )


def test_i_chunk_fermi_si_scrivono_invece_di_lasciare_la_riga_fuori() -> None:
    """Zero è il risultato, e va **mostrato**.

    Il balancer del 7.0 in questo laboratorio non migra mai (M-049, ADR-0069). Una riga
    assente si leggerebbe come una funzione mancante; una riga che dice zero è la lezione.
    """
    testo = spartizione(_spartizione())

    assert "chunk" in testo
    assert "0 in più" in testo


def test_la_spartizione_contrappone_i_due_piani_con_gli_shard_interrogati() -> None:
    testo = spartizione(_spartizione())

    assert "SINGLE_SHARD" in testo
    assert "SHARD_MERGE" in testo
    assert "1 shard" in testo
    assert "2 shard" in testo
    # Le virgolette sono doppie: chi guarda riscriverà quel filtro in mongosh, e il
    # `repr` di un dict Python non è ciò che mongosh accetta.
    assert '{"_id": 4242}' in testo
    assert '{"citta": "Ancona"}' in testo


def test_se_i_due_carichi_non_combaciano_la_schermata_lo_scrive() -> None:
    """Due colonne affiancate danno per scontato che il carico sia lo stesso.

    Se non lo è, la differenza fra le colonne non è più la chiave di shard: è il carico.
    Tacerlo sarebbe il modo più elegante di mentire in sala.
    """
    testo = spartizione(_spartizione(scritte_intera=2_000, scritte_sparsa=1_400))

    assert "2000" in testo and "1400" in testo
    assert "non è lo stesso carico" in testo


def test_quando_i_carichi_combaciano_la_schermata_non_avvisa_di_niente() -> None:
    assert "non è lo stesso carico" not in spartizione(_spartizione())


def test_la_spartizione_sta_nel_budget_di_sala() -> None:
    for linea in spartizione(_spartizione()).splitlines():
        assert len(linea) <= COLONNE_SALA, linea
