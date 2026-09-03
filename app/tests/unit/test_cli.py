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
from mongolab.cli import (
    LETTORI_PREDEFINITI,
    SCRITTORI_PREDEFINITI,
    Resa,
    app,
    cabla,
    giri_di,
    mentre_disegna,
    sink_di,
)
from mongolab.domain.eventi import Evento, ServerStateChanged
from mongolab.domain.modelli import Documento, RuoloServer
from mongolab.domain.porte import Clock
from mongolab.infrastructure.bersagli import (
    BERSAGLI,
    COLLEZIONE,
    PREFISSO_CARICO,
    BersaglioSconosciuto,
)
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
