"""Il cablaggio, e soltanto quello.

Queste prove non verificano che il carico scriva, che la sentinella veda un failover o
che una riga sia formattata bene: sono cose già provate, ciascuna contro il proprio
modulo, con doppi che non hanno bisogno di un database. Qui si verifica l'unica cosa che
nessun'altra prova può verificare, perché nessun altro modulo la sa — **che i pezzi
giusti finiscano attaccati ai posti giusti**: che `--sink plain` costruisca un
`PlainSink`, che `--target` sbagliato si fermi prima di aprire una connessione, che il
thread che disegna sia quello che ha chiamato.

**Nessuna di queste prove si collega a MongoDB**, ed è una proprietà voluta e non una
comodità: il composition root è il posto in cui la scelta dell'adattatore si fa, non il
posto in cui l'adattatore lavora. Se per provare il cablaggio servisse uno stack acceso,
vorrebbe dire che nel cablaggio è finito del lavoro, e sarebbe quello il difetto.
"""

import re
import threading
from io import StringIO
from typing import Sequence

import pytest
from rich.console import Console
from typer.testing import CliRunner

from mongolab.application.topologia import INTERVALLO_PREDEFINITO_MS
import typer

from mongolab.cli import (
    DATABASE_RIPRISTINO,
    DESTINAZIONE_DUMP,
    LETTORI_PREDEFINITI,
    OPZIONI_DUMP,
    SCRITTORI_PREDEFINITI,
    Resa,
    app,
    cabla,
    comandi_di,
    giri_di,
    host_interno_di,
    mentre_disegna,
    nodo_di,
    regia_di,
    riga_delle_opzioni,
    servizi_di,
    sink_di,
    strumento_di,
    niente_da_fermare,
)
from mongolab.domain.eventi import Evento, ServerStateChanged
from mongolab.domain.modelli import (
    DescrizioneServer,
    DescrizioneTopologia,
    Documento,
    RuoloServer,
    TipoTopologia,
)
from mongolab.domain.porte import Clock
from mongolab.infrastructure.bersagli import (
    BERSAGLI,
    COLLEZIONE,
    DATABASE,
    PREFISSO_CARICO,
    VARIABILE_PUNTO_DI_VISTA,
    BersaglioSconosciuto,
    Credenziali,
    PuntoDiVista,
)
from mongolab.infrastructure.bersagli import opzioni_di_misura
from mongolab.infrastructure.regia import RegiaAnnunciata, RegiaCompose
from mongolab.presentation.null import NullSink
from mongolab.presentation.plain import PlainSink
from mongolab.presentation.rich_tui import RichTui

from tests.doppi.orologio import FakeClock

from datetime import UTC, datetime

ISTANTE = datetime(2026, 9, 18, 10, 0, 0, tzinfo=UTC)

COMANDI = ("stats", "watch", "workload")
"""I tre comandi diretti del §6.4. `demo` arriva al Task 13 e qui non c'è."""

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def pulito(testo: str) -> str:
    """L'output di Typer senza colori e senza la cornice, su una riga sola.

    Serve perché gli errori di Typer passano da Rich, che li incornicia e li manda a
    capo dove finisce il riquadro: una frase di ottanta caratteri arriva spezzata in
    due, e un `in` su quella frase fallirebbe per un motivo che non riguarda il codice.
    Togliere il colore, togliere il bordo e ricucire gli spazi rende l'asserzione una
    domanda sul messaggio invece che sulla larghezza del terminale.
    """
    return " ".join(_ANSI.sub("", testo).replace("│", " ").split())


def esegui(*argomenti: str) -> tuple[int, str]:
    """Invoca la CLI e restituisce codice d'uscita e output ripulito."""
    esito = CliRunner().invoke(app, list(argomenti))
    return esito.exit_code, pulito(esito.output)


# --- I tre comandi diretti del §6.4 ----------------------------------------------------


def test_i_tre_comandi_diretti_esistono() -> None:
    codice, testo = esegui("--help")

    assert codice == 0
    for comando in COMANDI:
        assert comando in testo, comando


def test_ogni_comando_vuole_un_bersaglio() -> None:
    # `--target` senza valore predefinito è deliberato: durante il talk si passa da uno
    # stack all'altro, e un predefinito silenzioso vorrebbe dire collegarsi a quello
    # sbagliato senza accorgersene, davanti alla sala.
    for comando in COMANDI:
        codice, testo = esegui(comando)
        assert codice != 0, comando
        assert "target" in testo, comando


def test_un_bersaglio_sconosciuto_si_ferma_prima_di_collegarsi() -> None:
    for comando in COMANDI:
        codice, testo = esegui(comando, "--target", "rs0")
        assert codice != 0, comando
        assert "rs0" in testo, comando
        for nome in BERSAGLI:
            assert nome in testo, (comando, nome)


def test_workload_ha_le_quattro_opzioni_della_riga_del_design() -> None:
    codice, testo = esegui("workload", "--help")

    assert codice == 0
    for opzione in ("--writers", "--readers", "--doc-size", "--duration"):
        assert opzione in testo, opzione


def test_i_predefiniti_di_workload_sono_la_riga_del_design() -> None:
    """`mongolab workload --target rs` da solo fa la corsa che il §6.4 scrive per esteso.

    Non è una comodità: la riga del design è quella che il Task 16 misurerà, ed è quella
    che finisce su una slide. Se i predefiniti dicessero altro, ci sarebbero due corse
    diverse con lo stesso nome.
    """
    codice, testo = esegui("workload", "--help")

    assert codice == 0
    assert SCRITTORI_PREDEFINITI == 8
    assert LETTORI_PREDEFINITI == 4
    for predefinito in ("8", "4", "2k", "120"):
        assert predefinito in testo, predefinito


def test_una_dimensione_impossibile_si_ferma_alla_riga_di_comando() -> None:
    # `2gb` non è una forma che `byte_di` accetta, e il punto della prova è **dove** lo
    # si scopre: alla lettura degli argomenti, non dopo aver aperto una connessione e
    # aver acceso una TUI.
    codice, testo = esegui("workload", "--target", "rs", "--doc-size", "2gb")

    assert codice != 0
    assert "2gb" in testo
    assert "2k" in testo


def test_una_resa_inesistente_si_ferma_alla_riga_di_comando() -> None:
    codice, testo = esegui("workload", "--target", "rs", "--sink", "asciinema")

    assert codice != 0
    assert "asciinema" in testo


# --- La resa: `--sink` è un'opzione, non una condizione sparsa -------------------------


def test_sink_plain_produce_un_plain_sink() -> None:
    assert isinstance(sink_di(Resa.PLAIN, FakeClock(ISTANTE)), PlainSink)


def test_sink_rich_produce_la_tui() -> None:
    assert isinstance(sink_di(Resa.RICH, FakeClock(ISTANTE)), RichTui)


def test_sink_null_produce_il_sink_muto() -> None:
    assert isinstance(sink_di(Resa.NULL, FakeClock(ISTANTE)), NullSink)


def test_ogni_resa_ha_il_suo_sink() -> None:
    """La guardia contro il quarto valore aggiunto senza il suo ramo.

    Le tre prove qui sopra restano vere anche se domani `Resa` cresce di un membro che
    `sink_di` non conosce: passerebbero tutte, e il difetto si vedrebbe la prima volta
    che qualcuno scrive `--sink` con il nome nuovo. Questa lo vede subito.
    """
    assert len(Resa) == 3
    for resa in Resa:
        assert sink_di(resa, FakeClock(ISTANTE)) is not None, resa


def test_la_resa_predefinita_e_rich() -> None:
    for comando in ("watch", "workload"):
        codice, testo = esegui(comando, "--help")
        assert codice == 0, comando
        assert "--sink" in testo, comando
        assert "rich" in testo, comando


def test_stats_non_offre_una_resa() -> None:
    """`stats` è una fotografia, e una fotografia non emette eventi.

    Dargli `--sink` sarebbe un'opzione accettata e inerte — esattamente la bugia che
    questo repository si è impegnato a non scrivere. Chi vuole la cronaca usa `watch`.
    """
    codice, testo = esegui("stats", "--help")

    assert codice == 0
    assert "--sink" not in testo


# --- Il cablaggio: che cosa una corsa ha in mano prima di partire ----------------------


def test_il_cablaggio_risolve_il_bersaglio() -> None:
    cablaggio = cabla("rs", Resa.NULL)

    assert cablaggio.bersaglio.nome == "rs"
    assert cablaggio.bersaglio.stack == "02-replicaset"


def test_il_cablaggio_da_un_orologio_consapevole_del_fuso() -> None:
    # Il fuso non è un dettaglio: `righe.py` stampa l'ora senza convertirla, e un istante
    # ingenuo qui diventerebbe una cronaca fuori orario proiettata in sala.
    cablaggio = cabla("standalone", Resa.NULL)

    assert cablaggio.orologio.now().tzinfo is not None


def test_il_cablaggio_sceglie_il_sink_che_gli_e_stato_chiesto() -> None:
    assert isinstance(cabla("rs", Resa.PLAIN).sink, PlainSink)
    assert isinstance(cabla("rs", Resa.NULL).sink, NullSink)


def test_il_cablaggio_rifiuta_un_bersaglio_sconosciuto() -> None:
    with pytest.raises(BersaglioSconosciuto, match="rs0"):
        cabla("rs0", Resa.NULL)


def test_il_cablaggio_non_apre_niente() -> None:
    """Su tutti e tre i bersagli, senza rete, senza Docker e senza `.env`.

    È la prova che il composition root **sceglie** e basta. Se un giorno `cabla`
    aprisse un `MongoClient` o leggesse una credenziale, questa prova diventerebbe rossa
    su una macchina appena clonata — che è esattamente quando serve.
    """
    for nome in BERSAGLI:
        cablaggio = cabla(nome, Resa.NULL)
        assert cablaggio.bersaglio.nome == nome


# --- Chi disegna: un thread solo tocca la TUI ------------------------------------------


def test_senza_tui_il_lavoro_gira_nel_thread_chiamante() -> None:
    visti: list[str] = []

    def lavoro() -> str:
        visti.append(threading.current_thread().name)
        return "fatto"

    assert mentre_disegna(NullSink(), lavoro) == "fatto"
    assert visti == [threading.current_thread().name]


def test_con_la_tui_il_lavoro_va_altrove_e_il_disegno_resta_qui() -> None:
    """ADR-0019 detto in una prova: chi ha chiamato disegna, il lavoro sta da un'altra parte.

    Le due asserzioni vanno lette insieme. Che il lavoro giri su un thread diverso è
    metà del fatto; l'altra metà è che qualcosa sia stato **disegnato** dal thread che
    ha chiamato, e la console che scrive su un `StringIO` è il modo di vederlo senza
    guardare un pixel.
    """
    foglio = StringIO()
    tui = RichTui(
        FakeClock(ISTANTE), console=Console(file=foglio, width=100), ritmo=1000.0
    )
    visti: list[str] = []

    def lavoro() -> int:
        visti.append(threading.current_thread().name)
        return 7

    assert mentre_disegna(tui, lavoro) == 7
    assert visti and visti[0] != threading.current_thread().name
    assert foglio.getvalue() != ""


def test_un_errore_del_lavoro_non_resta_sepolto() -> None:
    # Un `Future` che solleva e non viene mai interrogato è un errore che sparisce: la
    # scena finirebbe in silenzio, con la TUI che si chiude e nessuno che sa perché.
    foglio = StringIO()
    tui = RichTui(
        FakeClock(ISTANTE), console=Console(file=foglio, width=100), ritmo=1000.0
    )

    def lavoro() -> None:
        raise RuntimeError("il carico è caduto")

    with pytest.raises(RuntimeError, match="il carico è caduto"):
        mentre_disegna(tui, lavoro)


# --- I giri di `watch`: una durata diventa un numero di sguardi ------------------------


def test_i_giri_vengono_dalla_durata() -> None:
    assert giri_di(10.0, intervallo_ms=500.0) == 20
    assert giri_di(60.0, intervallo_ms=INTERVALLO_PREDEFINITO_MS) == 120


def test_una_durata_piu_corta_dell_intervallo_vale_un_giro() -> None:
    # Meglio uno sguardo di zero: `segui(0)` solleverebbe, e `watch --duration 0.1`
    # sarebbe un comando che si rifiuta di guardare invece di guardare una volta.
    assert giri_di(0.1, intervallo_ms=500.0) == 1


def test_i_giri_si_arrotondano_per_eccesso() -> None:
    assert giri_di(1.2, intervallo_ms=500.0) == 3


def test_una_durata_non_positiva_e_rifiutata() -> None:
    with pytest.raises(ValueError, match="durata"):
        giri_di(0.0)


# --- Dove il carico atterra ------------------------------------------------------------
#
# Questa sezione esiste per un difetto vero, trovato eseguendo. `mongolab workload
# --target standalone` contro lo stack 01 acceso ha risposto `38 scritture · 0
# confermate`: ogni inserimento tornava indietro con `E11000 duplicate key error
# collection: lab.ordini index: _id_ dup key: { _id: 0 }`. Il generatore numera i
# documenti da zero, il seed occupa già quegli `_id`, e il cablaggio aveva mandato il
# carico nella collezione seminata.
#
# La prova che segue non tocca un database: mette al posto di `connetti` un cliente che
# annota quali collezioni gli vengono chieste. È esattamente la domanda del Passo 4 —
# *che cosa è stato attaccato a che cosa* — e non la domanda «il carico scrive bene»,
# che ha già le sue prove in `test_workload.py`.


class CollezioneFinta:
    """Quel tanto di collezione che serve al cablaggio: un nome."""

    def __init__(self, nome: str) -> None:
        self.name = nome


class DatabaseFinto:
    def __init__(self) -> None:
        self.chieste: list[str] = []

    def __getitem__(self, nome: str) -> CollezioneFinta:
        self.chieste.append(nome)
        return CollezioneFinta(nome)


class ClienteFinto:
    def __init__(self) -> None:
        self.database = DatabaseFinto()
        self.chiuso = False

    def __getitem__(self, nome: str) -> DatabaseFinto:
        return self.database

    def close(self) -> None:
        self.chiuso = True


class ArchivioSpia:
    """Prende il posto di `PymongoStore` e non parla con nessuno.

    Sostituire l'adattatore invece del driver tiene la prova sulla domanda giusta: qui
    interessa **quale** collezione è stata scelta, non che cosa `pymongo` ne farebbe.
    """

    def __init__(self, collezione: CollezioneFinta) -> None:
        self.collezione = collezione

    def insert_many(self, documenti: Sequence[Documento]) -> int:
        return len(documenti)


def carico_finto(monkeypatch: pytest.MonkeyPatch) -> ClienteFinto:
    cliente = ClienteFinto()
    monkeypatch.setattr("mongolab.cli.connetti", lambda bersaglio: cliente)
    monkeypatch.setattr("mongolab.cli.PymongoStore", ArchivioSpia)
    return cliente


def test_il_carico_non_scrive_nella_collezione_seminata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = carico_finto(monkeypatch)

    codice, _ = esegui(
        "workload",
        "--target",
        "standalone",
        "--sink",
        "null",
        "--writers",
        "1",
        "--readers",
        "0",
        "--duration",
        "0.01",
    )

    assert codice == 0
    (chiesta,) = cliente.database.chieste
    assert chiesta != COLLEZIONE


def test_il_carico_sceglie_una_collezione_sua(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = carico_finto(monkeypatch)

    esegui(
        "workload",
        "--target",
        "standalone",
        "--sink",
        "null",
        "--writers",
        "1",
        "--readers",
        "0",
        "--duration",
        "0.01",
    )

    (chiesta,) = cliente.database.chieste
    assert chiesta.startswith(PREFISSO_CARICO)


def test_il_carico_dice_dove_ha_scritto(monkeypatch: pytest.MonkeyPatch) -> None:
    # Una collezione con un nome diverso a ogni corsa è inutile se il nome resta segreto:
    # chi apre `mongosh` dopo la scena deve sapere quale delle tre guardare.
    cliente = carico_finto(monkeypatch)

    _, uscita = esegui(
        "workload",
        "--target",
        "standalone",
        "--sink",
        "null",
        "--writers",
        "1",
        "--readers",
        "0",
        "--duration",
        "0.01",
    )

    (chiesta,) = cliente.database.chieste
    assert chiesta in pulito(uscita)


def test_il_carico_chiude_il_cliente(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = carico_finto(monkeypatch)

    esegui(
        "workload",
        "--target",
        "standalone",
        "--sink",
        "null",
        "--writers",
        "1",
        "--readers",
        "0",
        "--duration",
        "0.01",
    )

    assert cliente.chiuso


# --- Un solo narratore -------------------------------------------------------------------
#
# Anche questa sezione viene da un difetto trovato eseguendo. `mongolab watch --target
# standalone --sink plain` contro lo stack 01 ha stampato **due volte** la stessa
# transizione, a mezzo secondo di distanza:
#
#     20:58:05.798  SERVER  localhost:27017 sconosciuto → standalone
#     20:58:06.303  SERVER  localhost:27017 sconosciuto → standalone
#
# Sondato con pymongo nudo, il driver la emette una volta sola: il doppione era nostro. Il
# cablaggio aveva messo **due narratori sullo stesso fatto** — `SdamBridge`, che traduce i
# callback del driver, e `TopologyWatcher`, che interroga la descrizione ogni mezzo
# secondo. Vedono la stessa cosa perché guardano la stessa struttura, uno spinto e uno
# tirato, e la raccontano tutti e due.
#
# A dire quale dei due tenere è il §6.3 del design: il ponte «traduce ogni callback in un
# evento di dominio. Il risultato è la cronaca a schermo del failover con timestamp al
# millisecondo». La cronaca è del ponte, e i suoi istanti sono migliori — segnano quando
# il driver ha saputo, non quando qualcuno è passato a chiedere.
#
# `TopologyWatcher` non sparisce dal progetto: misura l'**interruzione**, e quella misura
# ha senso accanto alle scritture perse, cioè nello scenario di failover del Task 13. In
# `watch`, dove non si scrive niente, avrebbe raccontato soltanto — due volte.

TRANSIZIONE = ServerStateChanged(
    istante=ISTANTE,
    indirizzo="mongo-rs-1:27021",
    precedente=RuoloServer.SECONDARIO,
    successivo=RuoloServer.PRIMARIO,
)


class PonteFinto:
    """Un `SdamBridge` che consegna un fatto solo, e una volta sola."""

    def __init__(self, orologio: Clock) -> None:
        self.ascoltatori: list[object] = []
        self._in_attesa = [TRANSIZIONE]

    def drena(self) -> tuple[Evento, ...]:
        svuotato = tuple(self._in_attesa)
        self._in_attesa = []
        return svuotato


def test_una_transizione_si_racconta_una_volta_sola(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Due narratori sullo stesso fatto lo raddoppiano, e la scena del failover è quella.

    La prova conta le occorrenze e non ne cerca una: `in` sarebbe passato anche con il
    doppione, cioè proprio nel caso che ha reso necessaria questa sezione.
    """
    cliente = ClienteFinto()
    monkeypatch.setattr("mongolab.cli.connetti", lambda bersaglio, **resto: cliente)
    monkeypatch.setattr("mongolab.cli.SdamBridge", PonteFinto)

    codice, uscita = esegui(
        "watch", "--target", "standalone", "--sink", "plain", "--duration", "0.01"
    )

    assert codice == 0
    assert uscita.count("sconosciuto") == 0
    assert uscita.count("mongo-rs-1:27021") == 1


def test_watch_chiude_il_cliente(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = ClienteFinto()
    monkeypatch.setattr("mongolab.cli.connetti", lambda bersaglio, **resto: cliente)
    monkeypatch.setattr("mongolab.cli.SdamBridge", PonteFinto)

    esegui("watch", "--target", "standalone", "--sink", "plain", "--duration", "0.01")

    assert cliente.chiuso


# --- La scena del failover: `demo failover` --------------------------------------------
#
# La scena vera ha bisogno di uno stack acceso, di dieci secondi di elezione e di un
# container fermato per davvero: sta in `tests/integration/`. Qui c'è la stessa domanda
# di tutto il resto del file — **che cosa è stato attaccato a che cosa** — declinata sui
# pezzi che questa scena aggiunge: il frasario di Compose, la regia che dipende da dove
# si guarda, e il nodo da fermare.


def test_demo_e_un_gruppo_e_la_prima_scena_e_il_failover() -> None:
    codice, testo = esegui("--help")
    assert codice == 0
    assert "demo" in testo

    codice, testo = esegui("demo", "--help")
    assert codice == 0
    assert "failover" in testo


def test_demo_failover_ha_le_opzioni_del_copione() -> None:
    codice, testo = esegui("demo", "failover", "--help")

    assert codice == 0
    for opzione in ("--target", "--step", "--node", "--mode", "--sink"):
        assert opzione in testo, opzione


def test_demo_failover_vuole_un_bersaglio() -> None:
    codice, testo = esegui("demo", "failover")

    assert codice != 0
    assert "target" in testo


def test_demo_failover_rifiuta_un_bersaglio_sconosciuto() -> None:
    codice, testo = esegui("demo", "failover", "--target", "rs0")

    assert codice != 0
    assert "rs0" in testo
    for nome in BERSAGLI:
        assert nome in testo, nome


def test_i_due_guasti_sono_quelli_del_copione() -> None:
    """Il nodo morto e il nodo irraggiungibile ma vivo, e non ce n'è un terzo.

    Sono due scene diverse e il copione le vuole entrambe: `kill` dà connection refused,
    `pause` dà un timeout. La differenza fra un server caduto e una rete partizionata è
    la parte che il pubblico non si aspetta, e vale i trenta secondi che costa.
    """
    codice, testo = esegui("demo", "failover", "--help")

    assert codice == 0
    assert "ferma" in testo
    assert "sospendi" in testo


def test_un_guasto_che_non_esiste_si_ferma_alla_riga_di_comando() -> None:
    codice, testo = esegui(
        "demo", "failover", "--target", "rs", "--mode", "incendia"
    )

    assert codice != 0
    assert "incendia" in testo


def test_step_e_la_tui_non_possono_avere_lo_stesso_terminale() -> None:
    """Due cose vogliono lo schermo, e ADR-0019 dice che lo tocca un thread solo.

    La pausa di `--step` legge da `stdin` sul thread che esegue la scena; il `Live` di
    Rich ridisegna dal thread che ha chiamato. Il prompt finirebbe sotto il ridisegno —
    invisibile — e chi sta sul palco premerebbe Invio alla cieca davanti alla sala.

    Il rifiuto arriva **alla lettura degli argomenti**, prima che si apra una connessione
    e prima che parta il carico: è la differenza fra scoprirlo digitando il comando e
    scoprirlo con la scena già in corso. Dal palco la riga giusta è `--step --sink
    plain`, che è anche quella con cui si girano le registrazioni di riserva.
    """
    codice, testo = esegui("demo", "failover", "--target", "rs", "--step")

    assert codice != 0
    assert "plain" in testo


def test_senza_step_la_tui_resta_la_resa_predefinita() -> None:
    codice, testo = esegui("demo", "failover", "--help")

    assert codice == 0
    assert "rich" in testo


# --- Il frasario di Compose, il nodo, la regia -----------------------------------------


def test_i_servizi_di_uno_stack_sono_i_nomi_della_vista_di_rete() -> None:
    """I nomi dei servizi ci sono già, e stanno nei semi con cui il client li cerca.

    Una seconda mappa «stack → servizi» accanto a `BERSAGLI` sarebbe la stessa
    informazione scritta due volte, e la seconda divergerebbe al primo nodo aggiunto.
    """
    assert servizi_di(BERSAGLI["rs"]) == ("mongo-rs-1", "mongo-rs-2", "mongo-rs-3")
    assert servizi_di(BERSAGLI["standalone"]) == ("mongo-standalone",)


def test_il_frasario_punta_al_compose_dello_stack_con_i_suoi_env_file() -> None:
    """Il file dello stack, `tools/images.env`, e il `.env` di chi autentica.

    L'ordine e la presenza non sono estetica: senza i due env-file `docker compose` non
    arriva a guardare i container, perché i `compose.yaml` interpolano con `${VAR:?...}`
    e una variabile mancante è un errore. Sono gli stessi che le variabili `COMPOSE_0X`
    del Makefile passano, ed è voluto: la riga che l'applicazione esegue e quella che si
    digita a mano devono essere la stessa riga.
    """
    riga = comandi_di(BERSAGLI["rs"]).riga("ferma", "mongo-rs-1")

    assert "docker/02-replicaset/compose.yaml" in riga
    assert "tools/images.env" in riga
    assert "docker/02-replicaset/.env" in riga
    assert riga.endswith("mongo-rs-1")


def test_lo_stack_che_non_autentica_non_ha_un_env_file_da_passare() -> None:
    # `Bersaglio.ambiente` è `None` per il 01, e vuol dire «questo stack non autentica».
    # Un `--env-file` verso un file che non esiste fermerebbe `docker compose` prima di
    # arrivare al container, e per una credenziale di cui non c'è bisogno.
    assert len(comandi_di(BERSAGLI["standalone"]).ambiente) == 1
    assert len(comandi_di(BERSAGLI["rs"]).ambiente) == 2


def test_dall_host_la_regia_comanda_e_dalla_rete_annuncia() -> None:
    """Le due metà del problema che nessun processo solo può tenere insieme.

    Dall'host il socket del demone c'è e la scoperta della topologia no ([M-019]); dalla
    rete è l'opposto. Il punto di vista che sceglie la vista del client sceglie anche la
    regia, e sceglierlo in un posto solo è ciò che impedisce alle due scelte di finire in
    disaccordo — un'applicazione che annuncia il comando e poi lo esegue anche lei
    fermerebbe il nodo due volte.
    """
    assert isinstance(regia_di(BERSAGLI["rs"], PuntoDiVista.HOST), RegiaCompose)
    assert isinstance(regia_di(BERSAGLI["rs"], PuntoDiVista.RETE), RegiaAnnunciata)


def _vista(indirizzo: str | None) -> DescrizioneTopologia:
    server = (
        ()
        if indirizzo is None
        else (DescrizioneServer(indirizzo=indirizzo, ruolo=RuoloServer.PRIMARIO),)
    )
    return DescrizioneTopologia(
        tipo=TipoTopologia.REPLICA_SET_CON_PRIMARIO, server=server, nome_set="rs0"
    )


def test_il_nodo_predefinito_e_il_primario_che_il_driver_vede() -> None:
    """`--node` si può omettere, e l'omissione è la scelta giusta quasi sempre.

    Il primario cambia a ogni prova, e una riga di comando che lo nomina a mano è una
    riga che dal palco si digita sbagliata: `mongo-rs-1` fermato quando il primario era
    `mongo-rs-3` produce un secondario in meno e nessuna elezione — cioè cinque minuti
    di Atto II in cui non succede niente.
    """
    assert nodo_di(_vista("mongo-rs-2:27017"), BERSAGLI["rs"]) == "mongo-rs-2"


def test_senza_primario_non_c_e_niente_da_fermare() -> None:
    with pytest.raises(typer.BadParameter, match="primario"):
        nodo_di(_vista(None), BERSAGLI["rs"])


def test_un_indirizzo_che_non_e_un_servizio_dello_stack_lo_dice() -> None:
    """`localhost:27021` è ciò che il driver vede dall'host, e non si può fermare.

    Dall'host il bersaglio `rs` si raggiunge con `directConnection` su una porta
    pubblicata: il primario si chiama `localhost`, che non è un servizio del
    `compose.yaml` e non è un nome che `docker compose kill` sappia usare. È la faccia
    visibile di [M-019], e l'errore lo dice invece di far fallire Compose con «no such
    service» dopo che il carico è già partito.
    """
    with pytest.raises(typer.BadParameter) as errore:
        nodo_di(_vista("localhost:27021"), BERSAGLI["rs"])

    for servizio in servizi_di(BERSAGLI["rs"]):
        assert servizio in str(errore.value), servizio


def test_un_nodo_scritto_a_mano_che_non_esiste_si_ferma_prima_del_carico() -> None:
    codice, testo = esegui(
        "demo", "failover", "--target", "rs", "--node", "mongo-rs-9", "--sink", "null"
    )

    assert codice != 0
    assert "mongo-rs-9" in testo
    assert "mongo-rs-1" in testo


def test_senza_primario_l_errore_nomina_il_bersaglio_e_il_comando_che_rimedia() -> None:
    """Il messaggio è la parte che finisce davanti al pubblico, e si prova da sola.

    `niente_da_fermare` restituisce l'eccezione invece di sollevarla proprio per questo:
    verificare che cosa dice non richiede un replica set senza primario, che è una cosa
    che si fabbrica in trenta secondi di `docker compose` e che nessuno rifabbricherebbe
    a ogni suite.

    Che l'attesa **avvenga** lo prova `test_bersagli`; che serva, la prova di integrazione
    del Task 13, dove senza di essa la scena non partiva affatto.
    """
    detto = str(niente_da_fermare(BERSAGLI["rs"]))

    assert "rs" in detto
    assert "make up-02" in detto, "l'errore deve dire come si rimedia"


# --- L'Atto III: `demo backup-live` e `demo restore` ------------------------------------
#
# Le due scene girano **dall'host** e non da dentro la rete, ed è l'inverso del failover.
# La ragione è una sola e si ripete in tutte le prove che seguono: `mongodump` non sta
# nell'immagine dell'applicazione (M-044) e il container dell'applicazione non ha il
# socket del demone Docker, quindi il comando che entra nel nodo può partire solo da fuori.

FINTA = Credenziali(utente="admin", password="non-e-un-segreto-e-non-lo-sara-mai")
"""Una credenziale che non è di nessuno: queste prove la cercano dentro la riga."""


def test_le_due_scene_dell_atto_iii_sono_nel_gruppo_demo() -> None:
    codice, testo = esegui("demo", "--help")

    assert codice == 0
    assert "backup-live" in testo
    assert "restore" in testo


def test_backup_live_ha_le_opzioni_della_scena() -> None:
    codice, testo = esegui("demo", "backup-live", "--help")

    assert codice == 0
    for opzione in ("--target", "--out", "--node", "--carico", "--step", "--sink"):
        assert opzione in testo, opzione


def test_restore_ha_le_opzioni_della_scena() -> None:
    codice, testo = esegui("demo", "restore", "--help")

    assert codice == 0
    for opzione in ("--target", "--from", "--into", "--collection", "--sink"):
        assert opzione in testo, opzione


def test_il_backup_a_caldo_vuole_un_replica_set() -> None:
    """`--oplog` non è un'opzione che uno standalone accetta, ed è tutta la scena.

    Il dump a caldo è coerente **a un istante** perché porta via anche l'oplog della
    finestra in cui è stato preso ([ADR-0022](../../../docs/Decision.md#adr-0022)). Senza
    un replica set quell'oplog non esiste, e lo strumento esce con un errore dopo che il
    carico è già partito: il rifiuto arriva prima, alla lettura degli argomenti.
    """
    codice, testo = esegui("demo", "backup-live", "--target", "standalone")

    assert codice != 0
    assert "oplog" in testo
    assert "rs" in testo


def test_attraverso_un_mongos_il_dump_non_e_una_fotografia_coerente() -> None:
    """Lo stack 03 si raggiunge da un router, e un router non è membro di nessun set.

    `mongodump` verso un `mongos` legge shard per shard, senza un istante comune: la
    copia che ne esce non è la fotografia che l'Atto III promette. È una scena diversa e
    non è questa, e dirlo qui costa una riga.
    """
    codice, testo = esegui("demo", "backup-live", "--target", "sharded")

    assert codice != 0
    assert "shard" in testo


def test_anche_il_restore_vuole_un_replica_set() -> None:
    """Restaura una copia che solo il replica set può aver prodotto: stesso rifiuto."""
    codice, testo = esegui("demo", "restore", "--target", "standalone")

    assert codice != 0
    assert "oplog" in testo


def test_dalla_rete_il_backup_a_caldo_si_rifiuta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dentro il container non c'è né lo strumento né il socket per raggiungerlo.

    È l'inverso esatto del failover, e per lo stesso motivo: la scena del guasto ha
    bisogno della **scoperta**, che funziona solo da dentro (M-019); questa ha bisogno di
    `docker compose exec`, che funziona solo da fuori. Un'unica riga di comando che
    andasse bene in tutti e due i posti sarebbe una riga che in uno dei due mente.
    """
    monkeypatch.setenv(VARIABILE_PUNTO_DI_VISTA, "rete")

    codice, testo = esegui("demo", "backup-live", "--target", "rs")

    assert codice != 0
    assert "host" in testo


def test_dalla_rete_anche_il_restore_si_rifiuta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VARIABILE_PUNTO_DI_VISTA, "rete")

    codice, testo = esegui("demo", "restore", "--target", "rs")

    assert codice != 0
    assert "host" in testo


def test_step_e_la_tui_non_convivono_nemmeno_nel_backup() -> None:
    """Lo stesso rifiuto del failover, e dalla stessa funzione: la pausa e il `Live` di
    Rich vogliono lo stesso terminale, e ADR-0019 dice che lo tocca un thread solo."""
    codice, testo = esegui("demo", "backup-live", "--target", "rs", "--step")

    assert codice != 0
    assert "plain" in testo


def test_non_si_restaura_sopra_il_database_di_partenza() -> None:
    """Sarebbe la scena che si distrugge da sé.

    Ciò che manca nella copia sono i documenti scritti durante il dump, e stanno
    nell'originale: restaurare lì sopra li lascerebbe dove sono e il conteggio
    combacerebbe per il motivo sbagliato — la differenza che l'Atto III mostra sparirebbe
    proprio perché il restore è andato a buon fine.
    """
    codice, testo = esegui("demo", "restore", "--target", "rs", "--into", DATABASE)

    assert codice != 0
    assert DATABASE in testo


def test_i_due_predefiniti_tengono_insieme_le_due_scene() -> None:
    """`demo restore` senza opzioni raccoglie ciò che `demo backup-live` ha lasciato.

    Dal palco sono due comandi consecutivi, e un percorso da ricopiare fra l'uno e
    l'altro è un percorso da sbagliare davanti alla sala.
    """
    codice, testo = esegui("demo", "restore", "--help")

    assert codice == 0
    assert str(DESTINAZIONE_DUMP) in testo
    assert DATABASE_RIPRISTINO in testo
    assert DATABASE_RIPRISTINO != DATABASE


# --- Il Blocco 3: `demo sharding` -------------------------------------------------------
#
# La scena gira **da tutti e due i posti**, e non è una dimenticanza: qui non c'è nessuno
# strumento esterno da avviare in un nodo, si parla con il router e basta. Dall'host il
# router è `localhost:27117`, da dentro la rete è `mongos:27017`, e in entrambi i casi la
# scoperta resta spenta perché un `mongos` non si scopre — lo si interroga.


def test_la_scena_dello_sharding_e_nel_gruppo_demo() -> None:
    codice, testo = esegui("demo", "--help")

    assert codice == 0
    assert "sharding" in testo


def test_sharding_ha_le_opzioni_della_scena() -> None:
    codice, testo = esegui("demo", "sharding", "--help")

    assert codice == 0
    for opzione in ("--target", "--collection", "--scritture", "--step", "--sink"):
        assert opzione in testo, opzione


def test_il_carico_del_blocco_3_si_conta_e_non_si_cronometra() -> None:
    """L'unica scena senza `--carico`, e la ragione è una misura.

    Le altre tre si limitano con i secondi, e va bene: là il carico è lo sfondo su cui
    succede qualcos'altro. Qui il carico **è** la misura, e le due corse vanno accostate:
    con una durata uguale ne escono due conteggi diversi, perché il throughput delle due
    collezioni non è lo stesso. Misurato sullo stack 03 con sei secondi per parte:
    **4288 scritture sulla non distribuita, 4415 sulla distribuita**
    ([M-052](../../docs/Sources.md#m-052)) — cioè la schermata dichiarava «non è lo stesso
    carico» proprio nella scena che il copione intitola «lo stesso carico due volte».

    Con un conteggio le due corse sono uguali per costruzione, e la differenza fra le
    colonne resta quella che la scena vuole mostrare: la chiave di shard.
    """
    codice, testo = esegui("demo", "sharding", "--help")

    assert codice == 0
    assert "--carico" not in testo


def test_la_scena_dello_sharding_vuole_uno_sharded_cluster() -> None:
    """Su un mongod solo non c'è niente da ripartire, e il rifiuto lo dice così.

    Non «comando non valido»: la riga spiega che cosa manca — gli shard — e quale
    bersaglio ce li ha. È la stessa forma di `_solo_da_un_replica_set`, ed è la forma che
    serve dal palco, dove un errore si legge a voce alta senza poterlo interpretare.
    """
    codice, testo = esegui("demo", "sharding", "--target", "standalone")

    assert codice != 0
    # Non `"shard"`: quella parola è dentro il nome del comando, e un'asserzione così
    # passerebbe anche contro «No such command 'sharding'» — cioè contro un comando che
    # non esiste. La prova deve poter fallire, se no non sta provando niente.
    assert "sharded cluster" in testo
    assert "--target sharded" in testo


def test_su_un_replica_set_non_c_e_nessun_router_a_cui_chiedere() -> None:
    """Tre nodi con gli stessi dati non sono tre shard, e la differenza è tutta la scena.

    `explain()` su un replica set risponde `COLLSCAN` o `IXSCAN` e non nomina nessuno
    shard, perché non c'è nessun router che riparta la domanda: la schermata del Blocco 3
    resterebbe muta proprio nelle due righe per cui esiste.
    """
    codice, testo = esegui("demo", "sharding", "--target", "rs")

    assert codice != 0
    assert "router" in testo
    assert "--target sharded" in testo


def test_step_e_la_tui_non_convivono_nemmeno_nello_sharding() -> None:
    """Stesso rifiuto delle altre scene, e dalla stessa funzione: ADR-0019."""
    codice, testo = esegui("demo", "sharding", "--target", "sharded", "--step")

    assert codice != 0
    assert "plain" in testo


# --- Chi esegue gli strumenti, e con quale indirizzo ------------------------------------


def test_l_indirizzo_interno_e_quello_che_lo_strumento_risolve() -> None:
    """`mongodump` gira **dentro** la rete Compose anche quando `mongolab` gira fuori.

    È la stessa asimmetria di [M-019](../../docs/Sources.md#m-019) vista dal lato degli
    strumenti: l'applicazione, dall'host, raggiunge lo stack su `localhost` con la
    scoperta spenta; il processo che lei avvia sta dentro un nodo, dove quei nomi
    esistono e la scoperta funziona. Passargli la vista dell'host lo farebbe fallire con
    un `connection refused` verso sé stesso.
    """
    assert host_interno_di(BERSAGLI["rs"]) == (
        "rs0/mongo-rs-1:27017,mongo-rs-2:27017,mongo-rs-3:27017"
    )


def test_senza_un_replica_set_l_indirizzo_non_ne_dichiara_uno() -> None:
    """`rs0/` davanti a un mongod solo è una dichiarazione falsa, e lo strumento la crede."""
    assert host_interno_di(BERSAGLI["standalone"]) == "mongo-standalone:27017"


def test_gli_strumenti_entrano_nel_nodo_con_il_frasario_dello_stack() -> None:
    """La riga del dump è `docker compose ... exec -T mongo-rs-1 mongodump ...`.

    Non `docker exec`: passare da Compose vuol dire riusare gli `--env-file` obbligatori
    dello stack e nominare il **servizio** invece del container, che è la stessa promessa
    che `ComandiCompose.per` fa alla regia del failover.
    """
    strumento = strumento_di(BERSAGLI["rs"], "mongo-rs-1", FINTA)

    riga = strumento.argomenti_dump(DESTINAZIONE_DUMP)

    preambolo = comandi_di(BERSAGLI["rs"]).dentro("mongo-rs-1", "mongodump")
    assert riga[: len(preambolo)] == preambolo


def test_la_riga_del_dump_porta_le_opzioni_del_copione() -> None:
    """`--readPreference=secondary --oplog`: la coppia che il Blocco 2 sta spiegando."""
    strumento = strumento_di(BERSAGLI["rs"], "mongo-rs-1", FINTA)

    riga = strumento.argomenti_dump(DESTINAZIONE_DUMP)

    for opzione in OPZIONI_DUMP:
        assert opzione in riga, opzione
    assert riga[riga.index("--host") + 1] == host_interno_di(BERSAGLI["rs"])
    assert riga[riga.index("--out") + 1] == str(DESTINAZIONE_DUMP)


def test_la_riga_che_la_scena_mostra_non_porta_il_segreto() -> None:
    """La scena stampa la riga del dump, e può farlo solo perché il segreto non ci passa.

    È [ADR-0054](../../../docs/Decision.md#adr-0054) al punto in cui serve davvero: la
    riga finisce su un proiettore e dentro una registrazione asciinema del Task 18.
    """
    strumento = strumento_di(BERSAGLI["rs"], "mongo-rs-1", FINTA)

    riga = " ".join(strumento.argomenti_dump(DESTINAZIONE_DUMP))
    ripristino = " ".join(strumento.argomenti_restore(DESTINAZIONE_DUMP, "lab_x"))

    assert FINTA.password not in riga
    assert FINTA.password not in ripristino
    assert "--env-file" in riga, "il frasario passa il percorso del .env, mai il valore"


def test_senza_autenticazione_la_riga_non_chiede_un_utente() -> None:
    """Lo stack 01 non autentica, e uno strumento che aspettasse una password lì si pianta."""
    strumento = strumento_di(BERSAGLI["standalone"], "mongo-standalone", None)

    riga = strumento.argomenti_dump(DESTINAZIONE_DUMP)

    assert "--username" not in riga


def test_il_restore_rinomina_verso_il_database_che_gli_si_chiede() -> None:
    strumento = strumento_di(BERSAGLI["rs"], "mongo-rs-1", FINTA)

    riga = strumento.argomenti_restore(DESTINAZIONE_DUMP, DATABASE_RIPRISTINO)

    assert riga[riga.index("--nsTo") + 1] == f"{DATABASE_RIPRISTINO}.*"
    assert riga[riga.index("--nsInclude") + 1] == f"{DATABASE}.*"


# --- Le opzioni di misura del Task 16 --------------------------------------------------
#
# Quattro debiti di misura scritti nelle pagine delle architetture, e quattro opzioni per
# saldarli (ADR-0109). La ragione per cui stanno qui e non in uno script di sonda è che
# una voce `V-` deve poter citare **il comando che la riproduce**: uno script scritto per
# l'occasione muore con la sessione, e la misura diventa una cifra di cui fidarsi.


def test_workload_ha_le_opzioni_di_misura_del_task_16() -> None:
    codice, testo = esegui("workload", "--help")

    assert codice == 0
    for opzione in (
        "--writes",
        "--journal",
        "--retry-writes",
        "--max-staleness",
        "--max-pool-size",
    ):
        assert opzione in testo, opzione


def test_le_tre_opzioni_a_due_facce_hanno_anche_la_faccia_negativa() -> None:
    """`--no-journal` esiste, e non è simmetria per bellezza.

    Il Passo 1 del Task 16 è un **confronto**: `j: true` contro il predefinito. Poterlo
    scrivere per esteso da tutte e due le parti — `--no-journal` e `--journal` — vuol dire
    che le due righe di comando della misura differiscono per una parola e non per
    l'assenza di una parola, e chi rilegge la voce `V-` non deve ricostruire che cosa
    fosse sottinteso nella prima.
    """
    codice, testo = esegui("workload", "--help")

    assert codice == 0
    assert "--no-journal" in testo
    assert "--no-retry-writes" in testo


def test_i_due_limiti_di_workload_non_si_danno_insieme() -> None:
    """`--writes` e `--duration` insieme si fermano **prima** di aprire una connessione.

    `WorkloadRunner.esegui` già rifiuta i due limiti insieme, ma lo fa dopo che il client
    è stato costruito e la collezione di carico annunciata. È la stessa regola di
    `--doc-size 2gb`: un argomento impossibile si scopre alla lettura degli argomenti.
    """
    codice, testo = esegui(
        "workload", "--target", "rs", "--writes", "100", "--duration", "30"
    )

    assert codice != 0
    assert "--writes" in testo
    assert "--duration" in testo


def test_senza_limiti_espliciti_workload_resta_la_riga_del_design() -> None:
    """I 120 secondi del §6.4 restano il predefinito anche ora che `--writes` esiste.

    Il predefinito è dovuto sparire dalla firma — con due limiti alternativi, un valore
    predefinito su uno dei due li renderebbe sempre entrambi presenti — ma non è dovuto
    sparire dal comportamento né dall'aiuto. Se `--help` smettesse di dire 120, la riga
    del design e la riga eseguita comincerebbero a divergere in silenzio.
    """
    codice, testo = esegui("workload", "--help")

    assert codice == 0
    assert "120" in testo


def test_senza_opzioni_di_misura_non_si_annuncia_niente() -> None:
    assert riga_delle_opzioni({}) == ""


def test_la_riga_annunciata_e_la_stessa_mappa_che_va_al_client() -> None:
    """A schermo va la mappa, non una sua parafrasi.

    Due funzioni che descrivono la stessa configurazione — una che la costruisce, una che
    la racconta — divergono alla prima opzione aggiunta a una sola delle due, e il modo in
    cui lo si scopre è un `.cast` che dichiara una misura diversa da quella eseguita.
    """
    misura = opzioni_di_misura(journal=True, retry_writes=False, max_pool_size=4)

    assert (
        riga_delle_opzioni(misura)
        == "opzioni journal=True · retryWrites=False · maxPoolSize=4"
    )


def test_demo_failover_puo_spegnere_i_tentativi_del_driver() -> None:
    """La perdita con `retryWrites=false` si misura dove c'è un failover.

    `replica-set.md` intesta la misura accanto a V-033, che è la scena del failover: senza
    un primario che cade, i tentativi del driver non hanno niente da riprendere e la
    misura direbbe zero contro zero.
    """
    codice, testo = esegui("demo", "failover", "--help")

    assert codice == 0
    assert "--retry-writes" in testo
    assert "--no-retry-writes" in testo
