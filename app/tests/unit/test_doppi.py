"""I doppi: che mantengano la promessa che i Task 5-18 daranno per buona.

Un doppio sbagliato non fa fallire le prove che lo usano — le fa **passare** per il motivo
sbagliato, ed è il modo più silenzioso che una suite abbia di mentire. Queste prove
esistono per quello, e per una ragione di ordine: qui la promessa di ogni doppio è scritta
una volta sola, invece di essere dedotta da come lo usano venti prove sparse.

L'altra metà della verifica non sta qui ma in `make app-check`. Le annotazioni esplicite —
`orologio: Clock = FakeClock(...)` — sono il punto in cui mypy controlla la conformità
**strutturale** alle porte: `isinstance` guarda i nomi e non le firme, e `test_dominio.py`
lo mostra scrivendo l'orologio che lo inganna.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
import threading

import pytest

from mongolab.domain.eventi import (
    Evento,
    LatencySampled,
    RetryAttempted,
    WriteFailed,
    WriteSucceeded,
)
from mongolab.domain.modelli import (
    ContoShard,
    DescrizioneServer,
    DescrizioneTopologia,
    Documento,
    Progress,
    RuoloServer,
    TipoTopologia,
)
from mongolab.domain.porte import (
    BackupTool,
    Clock,
    ClusterInspector,
    DocumentStore,
    EventSink,
)

from tests.contratto_archivio import ordini
from tests.doppi import (
    ArchivioCheNonLegge,
    ArchivioCheRompe,
    ArchivioLento,
    FakeBackup,
    FakeClock,
    FakeInspector,
    InMemoryStore,
    LetturaRifiutata,
    NonSupportato,
    OrologioCheScorre,
    RecordingSink,
    ScritturaRifiutata,
)

ISTANTE = datetime(2026, 9, 18, 9, 30, 0, tzinfo=UTC)


# --- FakeClock ------------------------------------------------------------------------


def test_l_orologio_finto_non_si_muove_da_solo() -> None:
    """Il tempo avanza per una chiamata, non perché il tempo vero è passato.

    È la proprietà da cui dipende ogni asserzione **esatta** su un istante: con
    l'orologio vero l'attesa diventa «circa 30 secondi», l'uguaglianza diventa una
    tolleranza, e la prova costa i 30 secondi che sta misurando.
    """
    orologio = FakeClock(ISTANTE)
    assert orologio.now() == ISTANTE
    assert orologio.now() == ISTANTE


def test_l_orologio_finto_avanza_quando_qualcuno_dorme() -> None:
    orologio = FakeClock(ISTANTE)
    orologio.sleep(30)
    assert orologio.now() == ISTANTE + timedelta(seconds=30)


def test_l_orologio_finto_ricorda_quanto_gli_e_stato_chiesto_di_dormire() -> None:
    """Le attese sono materiale per un'asserzione, non un effetto collaterale.

    La regola del Task 5 — ritenta, aspettando ogni volta un po' di più — è un
    comportamento che vive **tutto** in questa lista. Senza registrarla, l'unico modo di
    osservare il backoff sarebbe il tempo che la prova impiega davvero, cioè nessuno.
    """
    orologio = FakeClock(ISTANTE)
    orologio.sleep(0.1)
    orologio.sleep(0.2)
    orologio.sleep(0.4)
    assert orologio.attese == [0.1, 0.2, 0.4]


def test_l_orologio_finto_sa_avanzare_senza_che_nessuno_abbia_dormito() -> None:
    """Il tempo passa anche mentre si lavora, e la prova deve poterlo dire.

    `avanza` finge la durata di un'operazione — una scrittura che ci mette 12 ms — senza
    inventare una `sleep` che il codice sotto prova non ha mai chiamato. Se finisse in
    `attese`, l'asserzione sul backoff vedrebbe attese che nessuno ha chiesto: due
    significati diversi nella stessa lista sono il modo in cui un doppio comincia a
    mentire.
    """
    orologio = FakeClock(ISTANTE)
    orologio.avanza(0.012)
    assert orologio.now() == ISTANTE + timedelta(milliseconds=12)
    assert orologio.attese == []


def test_l_orologio_finto_passa_per_la_porta() -> None:
    orologio: Clock = FakeClock(ISTANTE)
    orologio.sleep(1)
    assert orologio.now() == ISTANTE + timedelta(seconds=1)


# --- RecordingSink --------------------------------------------------------------------


def test_il_raccoglitore_nasce_vuoto() -> None:
    assert RecordingSink().eventi == []


def test_il_raccoglitore_tiene_gli_eventi_nell_ordine_in_cui_sono_arrivati() -> None:
    """L'ordine **è** il contenuto della prova, non un dettaglio della lista.

    L'asserzione tipica dei Task 5 e 6 è su una sequenza — scrittura riuscita, scrittura
    fallita, ritentativo — perché è così che si racconta il failover: gli stessi tre
    eventi in ordine diverso sarebbero una cronaca diversa. Un raccoglitore che
    riordinasse, deduplicasse o tenesse solo l'ultimo per specie farebbe passare prove
    che descrivono un failover mai accaduto.
    """
    raccoglitore = RecordingSink()
    raccoglitore.emit(WriteSucceeded(istante=ISTANTE, documenti=10, durata_ms=1.0))
    raccoglitore.emit(
        WriteFailed(istante=ISTANTE, tipo_errore="NotPrimaryError", motivo="no primary")
    )
    raccoglitore.emit(
        RetryAttempted(istante=ISTANTE, tentativo=1, attesa_ms=50.0, motivo="rete")
    )

    assert [type(evento).__name__ for evento in raccoglitore.eventi] == [
        "WriteSucceeded",
        "WriteFailed",
        "RetryAttempted",
    ]


def test_il_raccoglitore_conserva_gli_eventi_e_non_una_loro_versione() -> None:
    """Ciò che si rilegge è ciò che è stato emesso, confrontabile per valore.

    Gli eventi sono congelati (`test_dominio.py`), quindi il raccoglitore può tenerne il
    riferimento senza copiarli: l'uguaglianza che si legge qui è quella che le prove dei
    Task 5 e 6 useranno per asserire su un evento intero invece che campo per campo.
    """
    evento = RetryAttempted(istante=ISTANTE, tentativo=2, attesa_ms=100.0, motivo="rete")
    raccoglitore = RecordingSink()
    raccoglitore.emit(evento)
    assert raccoglitore.eventi == [evento]


def test_il_raccoglitore_ricorda_da_quale_thread_e_stato_chiamato() -> None:
    """La promessa che rende asseribile la regola del §6.3.

    Non è una curiosità: «un solo thread tocca il sink» è un invariante di progetto
    (ADR-0019), e un invariante che nessuna prova può leggere è una frase. Qui il
    raccoglitore lo rende leggibile — `test_workload.py` ci asserisce sopra con più
    scrittori in corsa.
    """
    raccoglitore = RecordingSink()
    assert raccoglitore.chiamanti == set()

    raccoglitore.emit(LatencySampled(istante=ISTANTE, operazione="find", durata_ms=2.0))

    assert raccoglitore.chiamanti == {threading.get_ident()}


def test_il_raccoglitore_vede_i_thread_diversi_come_diversi() -> None:
    """Se non li distinguesse, la prova sul punto unico di sincronizzazione sarebbe vuota."""
    raccoglitore = RecordingSink()
    evento = LatencySampled(istante=ISTANTE, operazione="find", durata_ms=2.0)

    altro = threading.Thread(target=raccoglitore.emit, args=(evento,))
    altro.start()
    altro.join()
    raccoglitore.emit(evento)

    assert len(raccoglitore.chiamanti) == 2


def test_il_raccoglitore_passa_per_la_porta() -> None:
    raccoglitore = RecordingSink()
    sink: EventSink = raccoglitore
    evento: Evento = LatencySampled(istante=ISTANTE, operazione="find", durata_ms=2.0)
    sink.emit(evento)
    assert raccoglitore.eventi == [evento]


# --- InMemoryStore --------------------------------------------------------------------


# Le prove che valgono **anche** contro l'adattatore vero non stanno più qui: il Task 8 le
# ha spostate in `tests/contratto_archivio.py`, da dove le esegue la suite veloce
# (`test_contratto_archivio.py`) e quella di integrazione contro uno stack acceso. Erano
# già il contratto, scritte in un posto che ne conosceva una sola implementazione.
#
# Qui restano le prove che riguardano il **doppio in quanto doppio**: ciò che dichiara di
# non saper fare, e che l'originale invece fa. Metterle nel contratto vorrebbe dire
# chiedere alle due implementazioni di divergere, che è il contrario del suo mestiere.


def test_l_archivio_non_confronta_sottodocumenti() -> None:
    """Qui invece rifiuta, e la ragione viene dal manuale.

    Il confronto con un sottodocumento intero in MongoDB richiede «an *exact* match of the
    specified `<value>` document, **including the field order**», e il manuale aggiunge che
    «Queries that use comparisons on embedded documents can result in unpredictable
    behavior when used with a driver that does not use ordered data structures for
    expressing queries» (A-007). L'uguaglianza fra `dict` di Python l'ordine lo ignora: il
    doppio direbbe sì dove il cluster dice no. Fra imitare male e dichiarare di non saper
    fare, la seconda è l'unica che non produce prove verdi e sbagliate.
    """
    archivio = InMemoryStore()
    archivio.insert_many([{"_id": 1, "misura": {"h": 14, "w": 21}}])

    with pytest.raises(NonSupportato, match="sottodocumenti"):
        archivio.count({"misura": {"h": 14, "w": 21}})


def test_un_filtro_che_l_archivio_non_sa_applicare_solleva() -> None:
    """Il punto di tutta la faccenda: non sapere si dice, non si nasconde.

    Un doppio che ignorasse `$gt` restituirebbe *tutti* i documenti e la prova che lo usa
    diventerebbe verde — per il motivo sbagliato, e senza che nessuno abbia scritto una
    riga di codice difettoso. Il costo di sollevare è una riga da aggiungere il giorno in
    cui serve; il costo di tacere è una prova che non prova più niente e non lo dice.
    """
    archivio = InMemoryStore()
    archivio.insert_many(ordini())

    with pytest.raises(NonSupportato, match=r"\$gt"):
        archivio.count({"importo": {"$gt": 15}})


def test_uno_stadio_sconosciuto_solleva_invece_di_essere_saltato() -> None:
    """Saltare uno stadio è peggio che non conoscerlo: cambia il risultato in silenzio.

    `$group` non c'è perché nessuna prova l'ha ancora chiesto. Quando la prima lo chiederà
    arriverà qui insieme alla prova che lo verifica — che è la regola del piano: se una
    prova ha bisogno di una pipeline che il doppio non sa fare, la si aggiunge, non la si
    finge.
    """
    archivio = InMemoryStore()
    archivio.insert_many(ordini())

    with pytest.raises(NonSupportato, match=r"\$group"):
        archivio.aggregate([{"$group": {"_id": "$stato"}}])


def test_l_archivio_passa_per_la_porta() -> None:
    archivio = InMemoryStore()
    store: DocumentStore = archivio
    assert store.insert_many([{"_id": 1}]) == 1
    assert store.count({}) == 1
    assert store.find_page({}) == ({"_id": 1},)
    assert store.aggregate([{"$count": "quanti"}]) == ({"quanti": 1},)


# --- FakeInspector --------------------------------------------------------------------


def con_primario(indirizzo: str) -> DescrizioneTopologia:
    return DescrizioneTopologia(
        tipo=TipoTopologia.REPLICA_SET_CON_PRIMARIO,
        server=(
            DescrizioneServer(indirizzo=indirizzo, ruolo=RuoloServer.PRIMARIO),
            DescrizioneServer(indirizzo="mongo3:27017", ruolo=RuoloServer.SECONDARIO),
        ),
        nome_set="rs0",
    )


def senza_primario() -> DescrizioneTopologia:
    return DescrizioneTopologia(
        tipo=TipoTopologia.REPLICA_SET_SENZA_PRIMARIO,
        server=(
            DescrizioneServer(
                indirizzo="mongo1:27017", ruolo=RuoloServer.IRRAGGIUNGIBILE
            ),
            DescrizioneServer(indirizzo="mongo3:27017", ruolo=RuoloServer.SECONDARIO),
        ),
        nome_set="rs0",
    )


def test_l_ispettore_restituisce_le_topologie_preparate_in_ordine() -> None:
    prima, seconda = con_primario("mongo1:27017"), senza_primario()
    ispettore = FakeInspector([prima, seconda])

    assert ispettore.topology() == prima
    assert ispettore.topology() == seconda


def test_l_ispettore_resta_sull_ultima_invece_di_esaurirsi() -> None:
    """Chi guarda un cluster continua a guardarlo anche quando non cambia più.

    Il `TopologyWatcher` del Task 6 interroga in un ciclo, e quante volte lo faccia
    dipende dalla sua politica — cioè è proprio ciò che la prova sta verificando. Un
    doppio che a topologie finite sollevasse `IndexError` farebbe fallire la prova per il
    numero di giri invece che per il comportamento, e chi la legge cambierebbe il numero
    di topologie preparate finché il rosso sparisce: si sarebbe adattata la prova al
    doppio.
    """
    stabile = con_primario("mongo1:27017")
    ispettore = FakeInspector([stabile])

    assert [ispettore.topology() for _ in range(5)] == [stabile] * 5


def test_l_ispettore_conta_quante_volte_e_stato_interrogato() -> None:
    # Serve al Task 6: «smette di ritentare» si verifica anche mostrando che ha smesso di
    # guardare, e senza questo numero resterebbe osservabile solo di riflesso.
    ispettore = FakeInspector([con_primario("mongo1:27017")])
    for _ in range(3):
        ispettore.topology()
    assert ispettore.letture == 3


def test_l_ispettore_sa_raccontare_un_failover() -> None:
    """La scena del Blocco 2, preparata in tre descrizioni.

    Primario → nessun primario → primario **diverso**: è il caso che conta, ed è diverso
    da «il primario è tornato». Se il doppio non sapesse esprimere lo stato di mezzo — che
    non è né sano né rotto — la prova del Task 6 non potrebbe nemmeno essere scritta.
    """
    ispettore = FakeInspector(
        [con_primario("mongo1:27017"), senza_primario(), con_primario("mongo2:27017")]
    )

    prima, durante, dopo = (ispettore.topology() for _ in range(3))

    assert prima.ha_primario and prima.primario is not None
    assert not durante.ha_primario
    assert dopo.primario is not None
    assert dopo.primario.indirizzo != prima.primario.indirizzo


def test_un_ispettore_senza_topologie_e_un_errore_della_prova() -> None:
    # Non è un caso limite da gestire con eleganza: è una prova scritta male, e va detto
    # dove si costruisce e non dieci righe dopo, quando `topology()` restituirebbe chissà
    # che cosa.
    with pytest.raises(ValueError, match="almeno una topologia"):
        FakeInspector([])


def test_l_ispettore_restituisce_i_documenti_di_stato_preparati() -> None:
    distribuzione = (
        ContoShard(shard="shard1", documenti=20000, chunk=3),
        ContoShard(shard="shard2", documenti=100, chunk=3),
    )
    ispettore = FakeInspector(
        [con_primario("mongo1:27017")],
        server_status={"connections": {"current": 12}},
        db_stats={"dataSize": 4096},
        distribuzione=distribuzione,
    )

    assert ispettore.server_status() == {"connections": {"current": 12}}
    assert ispettore.db_stats() == {"dataSize": 4096}
    assert ispettore.shard_distribution() == distribuzione


def test_l_ispettore_non_inventa_una_distribuzione_di_shard() -> None:
    # La porta dice «vuota su ciò che non è uno sharded cluster», e il valore di partenza
    # del doppio è quello: un doppio che restituisse due shard finti farebbe passare la
    # scena del Blocco 3 contro un replica set.
    ispettore = FakeInspector([con_primario("mongo1:27017")])
    assert ispettore.shard_distribution() == ()
    assert ispettore.server_status() == {}


def test_l_ispettore_passa_per_la_porta() -> None:
    ispettore: ClusterInspector = FakeInspector([senza_primario()])
    assert not ispettore.topology().ha_primario


# --- FakeBackup -----------------------------------------------------------------------


def mezzo_dump() -> list[Progress]:
    return [
        Progress(fase="dump", completati=1, totali=3, messaggio="lab.ordini"),
        Progress(fase="dump", completati=2, totali=3, messaggio="lab.clienti"),
    ]


def test_il_backup_finto_produce_gli_avanzamenti_preparati() -> None:
    avanzamenti = mezzo_dump()
    backup = FakeBackup(avanzamenti)
    assert list(backup.dump(Path("/tmp/dump"))) == avanzamenti


def test_il_backup_finto_puo_fallire_a_meta() -> None:
    """Il caso che l'Atto III deve saper mostrare: rotto **dopo** aver fatto qualcosa.

    Un dump che fallisce alla prima riga si gestisce con un `try` attorno alla chiamata.
    Uno che fallisce a metà lascia dietro di sé avanzamento già mostrato a schermo e file
    già scritti, e la domanda diventa che cosa la TUI racconta di quello che era andato
    bene. La prova asserisce entrambe le cose insieme: che l'errore arriva, e che arriva
    **dopo** i due avanzamenti.
    """
    avanzamenti = mezzo_dump()
    backup = FakeBackup(avanzamenti, errore=RuntimeError("mongodump interrotto a metà"))

    visti: list[Progress] = []
    with pytest.raises(RuntimeError, match="a metà"):
        for avanzamento in backup.dump(Path("/tmp/dump")):
            visti.append(avanzamento)

    assert visti == avanzamenti


def test_il_backup_finto_registra_la_richiesta_anche_se_nessuno_la_scorre() -> None:
    """La trappola dei generatori, chiusa dove costa meno.

    Se `dump` fosse **esso stesso** una funzione generatrice, chiamarlo non eseguirebbe
    nulla: né la registrazione della destinazione, né — nell'adattatore vero del Task 9 —
    l'avvio di `mongodump`. Il corpo partirebbe al primo `next()`. La porta però dice
    «avvia il dump e produce l'avanzamento **mentre** procede», e un doppio che rimandasse
    l'avvio insegnerebbe al codice chiamante un ordine che l'adattatore vero non rispetta.
    Qui si registra subito e si produce dopo, ed è la prova che lo tiene fermo.
    """
    backup = FakeBackup(mezzo_dump())

    avanzamenti = backup.dump(Path("/tmp/dump"))

    assert backup.dump_chiesti == [Path("/tmp/dump")]
    assert len(list(avanzamenti)) == 2


def test_il_backup_finto_ricorda_che_cosa_gli_e_stato_chiesto_di_ripristinare() -> None:
    backup = FakeBackup([Progress(fase="restore", completati=1)])

    assert list(backup.restore(Path("/tmp/dump"), "lab_ripristinato")) == [
        Progress(fase="restore", completati=1)
    ]
    assert backup.restore_chiesti == [(Path("/tmp/dump"), "lab_ripristinato")]


def test_il_backup_finto_senza_avanzamenti_non_ne_inventa() -> None:
    assert list(FakeBackup().dump(Path("/tmp/dump"))) == []


def test_il_backup_finto_passa_per_la_porta() -> None:
    strumento: BackupTool = FakeBackup(mezzo_dump())
    assert [avanzamento.percentuale for avanzamento in strumento.dump(Path("/tmp/dump"))] == [
        pytest.approx(33.33, abs=0.01),
        pytest.approx(66.67, abs=0.01),
    ]


# --- ArchivioCheRompe -----------------------------------------------------------------


def test_l_archivio_che_rompe_rifiuta_le_scritture() -> None:
    archivio = ArchivioCheRompe(InMemoryStore())

    with pytest.raises(ScritturaRifiutata):
        archivio.insert_many([{"_id": 1}])


def test_l_archivio_che_rompe_smette_di_rompere_dopo_i_guasti_previsti() -> None:
    """È la forma che serve al Task 5: fallisce, si ritenta, la seconda volta passa."""
    archivio = ArchivioCheRompe(InMemoryStore(), guasti=2)

    for _ in range(2):
        with pytest.raises(ScritturaRifiutata):
            archivio.insert_many([{"_id": 1}])

    assert archivio.insert_many([{"_id": 1}]) == 1
    assert archivio.count({}) == 1


def test_l_archivio_che_rompe_conta_anche_le_scritture_fallite() -> None:
    archivio = ArchivioCheRompe(InMemoryStore(), guasti=1)

    with pytest.raises(ScritturaRifiutata):
        archivio.insert_many([{"_id": 1}])
    archivio.insert_many([{"_id": 2}])

    assert archivio.tentate == 2


def test_l_archivio_che_rompe_non_scrive_quando_fallisce() -> None:
    """Un guasto che scrivesse lo stesso renderebbe non falsificabile la misura del Blocco 2."""
    archivio = ArchivioCheRompe(InMemoryStore(), guasti=1)

    with pytest.raises(ScritturaRifiutata):
        archivio.insert_many([{"_id": 1}])

    assert archivio.count({}) == 0


def test_l_archivio_che_rompe_lascia_passare_le_letture() -> None:
    """Le letture funzionano **durante** il guasto: senza, non c'è scena da mostrare."""
    dentro = InMemoryStore()
    dentro.insert_many([{"_id": 1, "stato": "confermato"}])
    archivio = ArchivioCheRompe(dentro)

    assert archivio.count({"stato": "confermato"}) == 1
    assert archivio.find_page({}) == ({"_id": 1, "stato": "confermato"},)
    assert archivio.aggregate([{"$count": "quanti"}]) == ({"quanti": 1},)


def test_l_archivio_che_rompe_dice_perche() -> None:
    archivio = ArchivioCheRompe(InMemoryStore(), motivo="niente primario")

    with pytest.raises(ScritturaRifiutata, match="niente primario"):
        archivio.insert_many([{"_id": 1}])


def test_l_archivio_che_rompe_passa_per_la_porta() -> None:
    archivio: DocumentStore = ArchivioCheRompe(InMemoryStore(), guasti=0)
    assert archivio.insert_many([{"_id": 1}]) == 1


# --- ArchivioLento --------------------------------------------------------------------


def test_l_archivio_lento_fa_passare_il_tempo_dentro_la_chiamata() -> None:
    orologio = FakeClock(ISTANTE)
    archivio = ArchivioLento(InMemoryStore(), orologio, costo_ms=12.0)

    prima = orologio.now()
    archivio.insert_many([{"_id": 1}])

    assert (orologio.now() - prima) == timedelta(milliseconds=12)


def test_l_archivio_lento_non_finge_di_aver_dormito() -> None:
    """Il costo di una chiamata non è un'attesa chiesta: `attese` deve restare pulita.

    È la distinzione che rende asseribile il backoff. Se il tempo speso dentro
    `insert_many` finisse in `attese`, la prova sul raddoppio dell'attesa vedrebbe numeri
    che nessuno ha chiesto, e fallirebbe per un motivo che sembra un altro.
    """
    orologio = FakeClock(ISTANTE)
    archivio = ArchivioLento(InMemoryStore(), orologio, costo_ms=12.0)

    archivio.insert_many([{"_id": 1}])

    assert orologio.attese == []


def test_l_archivio_lento_conserva_davvero_i_documenti() -> None:
    archivio = ArchivioLento(InMemoryStore(), FakeClock(ISTANTE), costo_ms=1.0)

    assert archivio.insert_many([{"_id": 1}, {"_id": 2}]) == 2
    assert archivio.count({}) == 2


def test_l_archivio_lento_costa_anche_sulle_letture() -> None:
    orologio = FakeClock(ISTANTE)
    archivio = ArchivioLento(InMemoryStore(), orologio, costo_ms=5.0)

    prima = orologio.now()
    archivio.count({})

    assert (orologio.now() - prima) == timedelta(milliseconds=5)


def test_i_due_archivi_si_compongono() -> None:
    """Guasto **e** lento insieme, senza che nessuno dei due sappia dell'altro.

    È la dimostrazione che le porte `Protocol` reggono: `ArchivioLento` annota `dentro`
    con `DocumentStore`, quindi accetta qualunque archivio — compreso uno che rompe.
    """
    orologio = FakeClock(ISTANTE)
    archivio = ArchivioLento(
        ArchivioCheRompe(InMemoryStore(), guasti=1), orologio, costo_ms=3.0
    )

    with pytest.raises(ScritturaRifiutata):
        archivio.insert_many([{"_id": 1}])
    archivio.insert_many([{"_id": 1}])

    assert orologio.now() - ISTANTE == timedelta(milliseconds=6)
    assert archivio.count({}) == 1


def test_l_archivio_lento_passa_per_la_porta() -> None:
    archivio: DocumentStore = ArchivioLento(
        InMemoryStore(), FakeClock(ISTANTE), costo_ms=1.0
    )
    assert archivio.insert_many([{"_id": 1}]) == 1


# --- ArchivioCheNonLegge --------------------------------------------------------------
#
# Il gemello di `ArchivioCheRompe`, arrivato al Task 11 con la prova che ne aveva bisogno:
# senza un archivio che rifiuta le letture non si può verificare che `WorkloadRunner`
# **conti** una lettura fallita invece di lasciar cadere l'intera corsa.


def test_l_archivio_che_non_legge_rifiuta_le_letture() -> None:
    archivio = ArchivioCheNonLegge(InMemoryStore())

    with pytest.raises(LetturaRifiutata):
        archivio.find_page({})


def test_l_archivio_che_non_legge_smette_dopo_i_guasti_previsti() -> None:
    dentro = InMemoryStore()
    dentro.insert_many([{"_id": 1}])
    archivio = ArchivioCheNonLegge(dentro, guasti=2)

    for _ in range(2):
        with pytest.raises(LetturaRifiutata):
            archivio.find_page({})
    assert archivio.find_page({}) == ({"_id": 1},)


def test_l_archivio_che_non_legge_conta_anche_le_letture_fallite() -> None:
    archivio = ArchivioCheNonLegge(InMemoryStore(), guasti=1)

    with pytest.raises(LetturaRifiutata):
        archivio.find_page({})
    archivio.find_page({})

    assert archivio.tentate == 2


def test_l_archivio_che_non_legge_lascia_passare_le_scritture() -> None:
    """Il verso opposto di `ArchivioCheRompe`: qui a funzionare sono le scritture.

    Serve così: un carico che continua a scrivere mentre le letture non passano è la
    scena di un secondario che è caduto sotto un primario sano.
    """
    dentro = InMemoryStore()
    archivio = ArchivioCheNonLegge(dentro)

    assert archivio.insert_many([{"_id": 1}, {"_id": 2}]) == 2
    assert archivio.count({}) == 2
    assert dentro.count({}) == 2


def test_l_archivio_che_non_legge_dice_perche() -> None:
    archivio = ArchivioCheNonLegge(InMemoryStore(), motivo="il secondario non risponde")

    with pytest.raises(LetturaRifiutata, match="il secondario non risponde"):
        archivio.find_page({})


def test_le_due_rotture_si_compongono() -> None:
    """`ArchivioCheNonLegge(ArchivioCheRompe(...))`: un archivio in cui non passa niente.

    È la ragione per cui sono due classi e non un parametro in più su una sola: nessuno
    dei due sa dell'altro, e mypy verifica la composizione al punto di costruzione perché
    `dentro` è annotato con la porta.
    """
    archivio: DocumentStore = ArchivioCheNonLegge(ArchivioCheRompe(InMemoryStore()))

    with pytest.raises(ScritturaRifiutata):
        archivio.insert_many([{"_id": 1}])
    with pytest.raises(LetturaRifiutata):
        archivio.find_page({})


def test_l_archivio_che_non_legge_passa_per_la_porta() -> None:
    archivio: DocumentStore = ArchivioCheNonLegge(InMemoryStore(), guasti=0)
    assert archivio.find_page({}) == ()


# --- OrologioCheScorre ----------------------------------------------------------------
#
# `FakeClock` non si muove da solo, ed è la sua virtù: è ciò che rende `attese` una lista
# di numeri scelti. Ma una corsa limitata da una durata, contro un orologio immobile, non
# finirebbe mai. Questo doppio è la risposta minima — il tempo avanza di un passo fisso a
# ogni lettura — e la conseguenza è che «quanti giri stanno in una durata» smette di
# dipendere dalla macchina e diventa una divisione.


def test_l_orologio_che_scorre_avanza_a_ogni_lettura() -> None:
    orologio = OrologioCheScorre(ISTANTE, passo_s=0.010)

    assert orologio.now() == ISTANTE
    assert orologio.now() == ISTANTE + timedelta(milliseconds=10)
    assert orologio.now() == ISTANTE + timedelta(milliseconds=20)


def test_l_orologio_che_scorre_conta_le_letture() -> None:
    orologio = OrologioCheScorre(ISTANTE)

    for _ in range(7):
        orologio.now()

    assert orologio.letture == 7


def test_l_orologio_che_scorre_registra_le_attese_come_il_gemello() -> None:
    # La stessa promessa di `FakeClock`: il backoff resta una lista di numeri, non pause
    # vere. Qui in più l'attesa fa **anche** avanzare il tempo, perché una prova a durata
    # deve poter scadere dormendo.
    orologio = OrologioCheScorre(ISTANTE, passo_s=0.0)

    orologio.sleep(0.05)
    orologio.sleep(0.1)

    assert orologio.attese == [0.05, 0.1]
    assert orologio.now() == ISTANTE + timedelta(milliseconds=150)


def test_l_orologio_che_scorre_non_torna_mai_indietro_sotto_piu_thread() -> None:
    """Il lucchetto è ciò che rende il doppio usabile in una prova a più worker.

    Senza, due thread possono leggere lo stesso istante — e una prova che divide una
    durata per un passo si ritroverebbe più giri di quanti ne siano stati concessi, una
    volta ogni tanto. Che è il tipo di prova peggiore.
    """
    orologio = OrologioCheScorre(ISTANTE, passo_s=0.001)
    letti: list[datetime] = []
    serratura = threading.Lock()

    def legge_cento() -> None:
        for _ in range(100):
            adesso = orologio.now()
            with serratura:
                letti.append(adesso)

    thread = [threading.Thread(target=legge_cento) for _ in range(4)]
    for uno in thread:
        uno.start()
    for uno in thread:
        uno.join()

    assert len(set(letti)) == 400
    assert orologio.letture == 400


def test_l_orologio_che_scorre_passa_per_la_porta() -> None:
    orologio: Clock = OrologioCheScorre(ISTANTE)
    assert orologio.now().tzinfo is not None
