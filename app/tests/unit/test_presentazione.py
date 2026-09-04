"""La presentazione: tre rese dello stesso flusso, e nessuna che disegni in una prova.

Il piano lo dice in una riga, e conviene prenderla alla lettera: «le prove della
presentazione si fanno su `PlainSink` e `RecordingSink`, mai su `RichTui`: provare il
disegno significa provare Rich, che ha già le sue prove». Qui dentro nessuna prova
guarda che cosa Rich mette a schermo.

`RichTui` però compare, tre volte, e la ragione è venuta da un giro di rotture
deliberate: mutando `auto_refresh=True` e togliendo l'ultimo `aggiorna()` la suite
restava verde. Erano le uniche due mutazioni sopravvissute, e non erano disegno — erano
la promessa di ADR-0019 e la fine del ciclo. «Non provare il disegno» non vuol dire «non
provare niente di quel modulo»: vuol dire provare i thread e la coda, che si osservano
senza guardare un pixel.

Perché allora questo file è lungo? Perché il grosso di ciò che la presentazione fa non è
disegnare. È tradurre un evento in una riga, contare, ricordare l'ultima topologia, e
soprattutto **accettare eventi da un thread e cambiare stato in un altro**. Sono tutte
cose che vivono fuori da Rich, e che stanno fuori da `RichTui` apposta: se stessero
dentro, la regola del piano costringerebbe a non provarle, e la regola diventerebbe un
alibi. Un divieto di provare qualcosa si onora spostando altrove ciò che va provato, non
rinunciando a provarlo.
"""

import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

import pytest

from mongolab.domain.eventi import (
    BackupProgressed,
    Evento,
    FaseIniziata,
    LatencySampled,
    PrimaryWaitAbandoned,
    RetryAttempted,
    ServerStateChanged,
    TopologyChanged,
    WriteFailed,
    WriteSucceeded,
)
from mongolab.domain.modelli import (
    DescrizioneServer,
    DescrizioneTopologia,
    Progress,
    RuoloServer,
    TipoTopologia,
)
from mongolab.domain.porte import EventSink
from mongolab.presentation.null import NullSink
from mongolab.presentation.plain import PlainSink
from mongolab.presentation.righe import (
    ALTEZZA_INTESTAZIONE,
    COLONNE_SALA,
    ETICHETTA_IGNOTA,
    RIGHE_CRONACA,
    RIGHE_SALA,
    SERVER_MOSTRATI,
    TRONCAMENTO,
    server_da_mostrare,
    tronca,
    riga,
)
from mongolab.presentation.scena import Scena
from tests.aiutanti import SORGENTI, estranei, sottoclassi_di_evento
from tests.doppi import FakeClock, RecordingSink

if TYPE_CHECKING:  # a runtime Rich lo importa solo chi lo usa, dentro la funzione
    from mongolab.presentation.rich_tui import RichTui

ISTANTE = datetime(2026, 9, 18, 9, 30, 0, 123456, tzinfo=UTC)

CON_PRIMARIO = DescrizioneTopologia(
    tipo=TipoTopologia.REPLICA_SET_CON_PRIMARIO,
    server=(
        DescrizioneServer("mongo-rs-1:27017", RuoloServer.PRIMARIO, ritardo_ms=1.2),
        DescrizioneServer("mongo-rs-2:27017", RuoloServer.SECONDARIO, ritardo_ms=1.4),
    ),
    nome_set="rs0",
)
SENZA_PRIMARIO = DescrizioneTopologia(
    tipo=TipoTopologia.REPLICA_SET_SENZA_PRIMARIO,
    server=(
        DescrizioneServer("mongo-rs-1:27017", RuoloServer.IRRAGGIUNGIBILE),
        DescrizioneServer("mongo-rs-2:27017", RuoloServer.SECONDARIO, ritardo_ms=1.4),
    ),
    nome_set="rs0",
)


def uno_per_specie() -> list[Evento]:
    """Un esemplare di ciascuno dei dieci eventi, in ordine alfabetico di classe.

    Costruiti a mano e non con una fabbrica generica: i campi hanno significati diversi,
    e una fabbrica che li riempisse con valori qualunque renderebbe illeggibili proprio
    le asserzioni sulle righe, che sono asserzioni su come quei valori si leggono.
    """
    return [
        BackupProgressed(ISTANTE, Progress("dump", 1200, 50000, "lab.ordini")),
        FaseIniziata(ISTANTE, "guasto", "fermo il primario"),
        LatencySampled(ISTANTE, "insert_many", 12.34),
        PrimaryWaitAbandoned(ISTANTE, 30000.0, 30000.0, "mongo-rs-1:27017"),
        RetryAttempted(ISTANTE, 2, 100.0, "AutoReconnect"),
        ServerStateChanged(
            ISTANTE, "mongo-rs-1:27017", RuoloServer.PRIMARIO, RuoloServer.IRRAGGIUNGIBILE
        ),
        TopologyChanged(ISTANTE, CON_PRIMARIO, SENZA_PRIMARIO),
        WriteFailed(ISTANTE, "AutoReconnect", "connection closed", 3),
        WriteSucceeded(ISTANTE, 3, 12.34),
    ]


# --- La riga: la resa comune a tutte e tre --------------------------------------------


def test_ogni_evento_del_dominio_sa_diventare_una_riga() -> None:
    """Dieci eventi, dieci rese dedicate: nessuno cade nel ripiego.

    La guardia è scritta al contrario di come verrebbe: non elenca le nove classi ma le
    **scopre**, e chiede che nessuna finisca sull'etichetta di ripiego. Un evento in più
    aggiunto senza una riga sua fa fallire questa prova invece di comparire a schermo
    come una scritta inutile nel mezzo del Blocco 2 — ed è successo davvero al Task 13.
    Funziona anche al contrario: al Task 15 un evento se n'è andato, e il numero qui è
    l'unico posto in cui bisognava accorgersene.
    """
    assert len(sottoclassi_di_evento()) == 9
    assert len(uno_per_specie()) == 9

    for evento in uno_per_specie():
        assert ETICHETTA_IGNOTA not in riga(evento), type(evento).__name__


def test_la_riga_si_apre_con_l_istante_al_millesimo() -> None:
    # I timestamp al millisecondo sono la promessa del §6.3: la cronaca dell'elezione
    # vale perché si legge quanto è durata, non perché elenca che cosa è successo.
    assert riga(WriteSucceeded(ISTANTE, 3, 12.34)).startswith("09:30:00.123 ")


def test_la_riga_e_una_riga_sola_anche_se_il_motivo_va_a_capo() -> None:
    """Un messaggio del driver su più righe non deve diventare più righe di cronaca.

    `PlainSink` scrive una riga per evento, e chi legge quel file — `grep`, una
    registrazione asciinema, un occhio — conta sugli a capo per separare i fatti. Un
    `motivo` con dentro un `\\n` romperebbe il conteggio senza rompere niente altro, che
    è il modo peggiore di rompersi.
    """
    prolisso = WriteFailed(ISTANTE, "OperationFailure", "prima riga\nseconda\n\tterza", 0)
    prodotta = riga(prolisso)

    assert "\n" not in prodotta
    assert "\t" not in prodotta
    assert "prima riga seconda terza" in prodotta


def test_la_riga_sta_nella_larghezza_di_sala_e_lo_dichiara() -> None:
    """Cento colonne, e un carattere che dice che si è tagliato.

    Il taglio non è pignoleria tipografica. Un `ServerSelectionTimeoutError` di pymongo
    porta con sé la descrizione dell'intera topologia: mandato a schermo intero occupa
    cinque righe, e durante un failover arriva centinaia di volte al secondo. La cronaca
    che dovrebbe raccontare l'elezione verrebbe sepolta dai messaggi degli errori che
    l'elezione provoca.
    """
    lunghissimo = WriteFailed(ISTANTE, "ServerSelectionTimeoutError", "x" * 500, 0)
    prodotta = riga(lunghissimo)

    assert len(prodotta) == COLONNE_SALA
    assert prodotta.endswith("…")


def test_chi_vuole_tutto_il_testo_lo_chiede_e_lo_ottiene() -> None:
    # Il taglio serve allo schermo; chi analizza un file vuole il messaggio intero, e la
    # differenza è un parametro invece che due funzioni che divergono.
    lunghissimo = WriteFailed(ISTANTE, "ServerSelectionTimeoutError", "x" * 500, 0)

    intera = riga(lunghissimo, larghezza=None)

    assert len(intera) > COLONNE_SALA
    # Il messaggio per intero, non «quasi tutto»: l'asserzione scritta come
    # `intera.endswith("x")` sarebbe passata anche con un taglio dopo il messaggio, e
    # infatti al primo giro ha fallito per il motivo opposto — la riga finisce con il
    # conteggio dei documenti, che viene dopo.
    assert "x" * 500 in intera
    assert intera.endswith("(0 documenti)")


def test_le_righe_dicono_il_fatto_e_non_il_nome_della_classe() -> None:
    """Le rese che il pubblico legge, scritte una volta e verificate qui.

    Sono asserzioni su testo, e il testo cambierà: è il prezzo, ed è accettabile perché
    ciò che proteggono non è la formattazione ma il **contenuto** — che il numero dei
    documenti ci sia, che il passaggio di stato mostri entrambi gli estremi, che una
    percentuale non compaia quando il totale non si conosce.
    """
    assert "3 documenti" in riga(WriteSucceeded(ISTANTE, 3, 12.34))
    assert "12.3 ms" in riga(WriteSucceeded(ISTANTE, 3, 12.34))

    fallita = riga(WriteFailed(ISTANTE, "AutoReconnect", "connection closed", 3))
    assert "AutoReconnect" in fallita and "connection closed" in fallita

    ritento = riga(RetryAttempted(ISTANTE, 2, 100.0, "AutoReconnect"))
    assert "2" in ritento and "100" in ritento

    passaggio = riga(
        ServerStateChanged(
            ISTANTE, "mongo-rs-1:27017", RuoloServer.PRIMARIO, RuoloServer.IRRAGGIUNGIBILE
        )
    )
    assert "primario" in passaggio and "irraggiungibile" in passaggio
    assert "→" in passaggio

    cambio = riga(TopologyChanged(ISTANTE, CON_PRIMARIO, SENZA_PRIMARIO))
    assert "replica set con primario" in cambio
    assert "replica set senza primario" in cambio

    resa = riga(PrimaryWaitAbandoned(ISTANTE, 30000.0, 30000.0, "mongo-rs-1:27017"))
    assert "mongo-rs-1:27017" in resa

    # `fase` è il nome su cui asseriscono le prove dello scenario; in sala si legge la
    # `descrizione`. La riga porta la seconda, perché la prima è vocabolario interno.
    fase = riga(FaseIniziata(ISTANTE, "guasto", "fermo il primario"))
    assert "fermo il primario" in fase


def test_l_avanzamento_senza_totale_non_inventa_una_percentuale() -> None:
    """`Progress.totali` è opzionale, e la riga rispetta il silenzio.

    `mongodump` annuncia il totale di una collezione e non quello del dump intero. Una
    barra che mostrasse comunque una percentuale mostrerebbe un numero inventato, che in
    sala è peggio di nessun numero.
    """
    noto = riga(BackupProgressed(ISTANTE, Progress("dump", 1200, 50000, "lab.ordini")))
    ignoto = riga(BackupProgressed(ISTANTE, Progress("dump", 1200, None, "lab.ordini")))

    assert "2.4%" in noto
    assert "%" not in ignoto
    assert "1200" in ignoto


# --- La scena: accetta da un thread, cambia stato in un altro -------------------------


def test_emit_deposita_e_ritorna_senza_toccare_lo_stato() -> None:
    """Il patto di ADR-0019, verificato dove si può ancora verificare.

    `emit` può essere chiamata dal thread del driver. Se cambiasse lo stato che il ciclo
    di disegno sta leggendo, la coda tornerebbe a essere stato condiviso e servirebbe il
    lock che ADR-0019 ha deciso di non mettere. Qui si chiede la sola cosa che rende
    superfluo quel lock: dopo `emit`, e prima di `assorbi`, **non è cambiato niente**.
    """
    scena = Scena()

    for evento in uno_per_specie():
        scena.emit(evento)

    assert scena.in_coda == 9
    assert scena.cronaca == ()
    assert scena.conteggi.scritture == 0
    assert scena.topologia is None
    assert scena.avanzamento is None


def test_assorbi_svuota_la_coda_e_dice_quanti() -> None:
    scena = Scena()
    for evento in uno_per_specie():
        scena.emit(evento)

    assorbiti = scena.assorbi()

    assert assorbiti == 9
    assert scena.in_coda == 0
    assert len(scena.cronaca) == min(9, RIGHE_CRONACA)


def test_assorbi_su_una_coda_vuota_ritorna_zero_e_non_aspetta() -> None:
    # Un `assorbi` che bloccasse trasformerebbe il ciclo di disegno in un'attesa, ed è
    # il verso di dipendenza che ADR-0019 ha invertito. La prova non misura il tempo:
    # se bloccasse, la suite non finirebbe, che è un fallimento più chiaro di un timeout.
    assert Scena().assorbi() == 0


def test_la_cronaca_tiene_le_ultime_righe_e_butta_le_prime() -> None:
    """Una scena è alta trenta righe, e la cronaca non può crescere all'infinito.

    Il taglio è dal fondo perché la scena è **il presente**: durante un failover conta
    l'ultima decina di secondi, non i primi. Chi vuole tutto usa `PlainSink`, che non
    taglia niente ed è fatto apposta per essere riletto dopo.
    """
    scena = Scena(righe_cronaca=3)
    for indice in range(10):
        scena.emit(WriteSucceeded(ISTANTE, indice, 1.0))
    scena.assorbi()

    assert len(scena.cronaca) == 3
    assert "7 documenti" in scena.cronaca[0]
    assert "9 documenti" in scena.cronaca[-1]


def test_la_scena_conta_quello_che_la_sala_guarda() -> None:
    scena = Scena()
    scena.emit(WriteSucceeded(ISTANTE, 3, 10.0))
    scena.emit(WriteSucceeded(ISTANTE, 2, 20.0))
    scena.emit(WriteFailed(ISTANTE, "AutoReconnect", "chiusa", 0))
    scena.emit(RetryAttempted(ISTANTE, 1, 50.0, "AutoReconnect"))
    scena.emit(LatencySampled(ISTANTE, "insert_many", 12.5))
    scena.assorbi()

    assert scena.conteggi.scritture == 2
    assert scena.conteggi.documenti == 5
    assert scena.conteggi.fallimenti == 1
    assert scena.conteggi.ritentativi == 1
    assert scena.conteggi.campioni == 1
    assert scena.conteggi.ultima_latenza_ms == 12.5


def test_la_scena_ricorda_l_ultima_topologia_e_l_ultimo_avanzamento() -> None:
    scena = Scena()
    scena.emit(TopologyChanged(ISTANTE, CON_PRIMARIO, SENZA_PRIMARIO))
    scena.emit(BackupProgressed(ISTANTE, Progress("dump", 10, 100)))
    scena.emit(BackupProgressed(ISTANTE, Progress("dump", 90, 100)))
    scena.assorbi()

    assert scena.topologia == SENZA_PRIMARIO
    assert scena.avanzamento == Progress("dump", 90, 100)


def test_un_altro_thread_emette_e_il_thread_che_assorbe_vede_tutto() -> None:
    """Il caso vero: il produttore non è chi disegna.

    Duecento eventi da due thread, e nessuno perso. Non è una prova sulla `queue.Queue`,
    che ha le sue: è la prova che questa scena la usa nel modo in cui la si può usare
    senza lock, cioè che lo stato lo tocca **solo** chi assorbe.
    """
    scena = Scena(righe_cronaca=1000)

    def produci(primo: int) -> None:
        for indice in range(primo, primo + 100):
            scena.emit(WriteSucceeded(ISTANTE, indice, 1.0))

    thread = [threading.Thread(target=produci, args=(base,)) for base in (0, 100)]
    for uno in thread:
        uno.start()
    for uno in thread:
        uno.join()

    # Finché nessuno assorbe, la scena è com'era: lo stato non l'ha toccato nessuno.
    assert scena.conteggi.scritture == 0

    assert scena.assorbi() == 200
    assert scena.conteggi.scritture == 200
    assert scena.conteggi.documenti == sum(range(200))


# --- I tre sink ------------------------------------------------------------------------


def test_il_sink_di_testo_scrive_una_riga_per_evento(tmp_path: Path) -> None:
    percorso = tmp_path / "cronaca.txt"
    with percorso.open("w", encoding="utf-8") as flusso:
        sink = PlainSink(flusso)
        for evento in uno_per_specie():
            sink.emit(evento)

    righe_scritte = percorso.read_text(encoding="utf-8").splitlines()

    assert len(righe_scritte) == 9
    assert righe_scritte[-1] == riga(WriteSucceeded(ISTANTE, 3, 12.34))


def test_il_sink_di_testo_svuota_il_buffer_a_ogni_evento(tmp_path: Path) -> None:
    """Senza `flush`, una registrazione mostra il nulla e poi tutto insieme.

    Python bufferizza a blocchi quando la destinazione non è un terminale, ed è
    esattamente il caso di `--sink plain > file` e di una pipe. La cronaca di un
    failover arriverebbe a failover concluso: i tempi, che in queste scene *sono* il
    contenuto, andrebbero persi senza che nessun byte vada perso.
    """
    percorso = tmp_path / "cronaca.txt"
    with percorso.open("w", encoding="utf-8") as flusso:
        PlainSink(flusso).emit(WriteSucceeded(ISTANTE, 3, 12.34))

        # Ancora dentro il `with`: il file non è stato chiuso, e quindi nessuno ha
        # svuotato il buffer al posto del sink.
        assert percorso.read_text(encoding="utf-8").strip() != ""


def test_il_sink_di_testo_puo_non_tagliare(tmp_path: Path) -> None:
    percorso = tmp_path / "cronaca.txt"
    lunghissimo = WriteFailed(ISTANTE, "ServerSelectionTimeoutError", "x" * 500, 0)

    with percorso.open("w", encoding="utf-8") as flusso:
        PlainSink(flusso, larghezza=None).emit(lunghissimo)

    assert len(percorso.read_text(encoding="utf-8").rstrip("\n")) > COLONNE_SALA


def test_il_sink_che_non_fa_niente_non_tiene_niente() -> None:
    """`NullSink` serve alle misure del Task 16, e serve solo se non pesa.

    L'asserzione non è sul tempo — misurare che «è veloce» in una prova unitaria produce
    la prova che fallisce una volta su cento su una macchina carica. È strutturale: un
    oggetto con `__slots__` vuoti **non può** accumulare, e nessuna aggiunta distratta di
    un contatore passerebbe da qui in silenzio.
    """
    sink = NullSink()

    for evento in uno_per_specie():
        sink.emit(evento)

    assert not hasattr(sink, "__dict__")
    # E non può nemmeno prenderselo: `__slots__` vuoti chiudono la porta a un contatore
    # aggiunto domani, che è la sola cosa che potrebbe far crescere questo oggetto.
    with pytest.raises(AttributeError):
        sink.contati = 1  # type: ignore[attr-defined]


def test_i_tre_sink_sono_tre_rese_dello_stesso_flusso(tmp_path: Path) -> None:
    """La regola del Passo 3, resa eseguibile.

    Lo stesso flusso attraversa le tre implementazioni: la resa di testo produce una riga
    per evento, quella che ricorda ne ricorda uno per evento, quella che non fa niente
    non lascia traccia. Se un giorno una delle tre avesse bisogno di un dato che le altre
    non ricevono, il difetto sarebbe nell'evento — e si vedrebbe qui, perché il conto
    smetterebbe di tornare.
    """
    percorso = tmp_path / "cronaca.txt"
    raccoglitore = RecordingSink()
    niente = NullSink()

    with percorso.open("w", encoding="utf-8") as flusso:
        testo = PlainSink(flusso)
        for evento in uno_per_specie():
            testo.emit(evento)
            raccoglitore.emit(evento)
            niente.emit(evento)

    righe_scritte = percorso.read_text(encoding="utf-8").splitlines()

    assert len(righe_scritte) == len(raccoglitore.eventi) == 9
    assert righe_scritte == [riga(evento) for evento in raccoglitore.eventi]


def test_i_quattro_sink_soddisfano_la_porta() -> None:
    # L'annotazione è metà della prova: è lì che `mypy --strict` verifica la conformità
    # strutturale, perché `isinstance` contro un Protocol guarda i nomi e non le firme.
    sinks: list[EventSink] = [NullSink(), RecordingSink(), Scena()]

    for sink in sinks:
        assert isinstance(sink, EventSink)


def test_anche_il_sink_di_testo_soddisfa_la_porta(tmp_path: Path) -> None:
    with (tmp_path / "c.txt").open("w", encoding="utf-8") as flusso:
        aperto: TextIO = flusso
        sink: EventSink = PlainSink(aperto)
        assert isinstance(sink, EventSink)


# --- Il budget di sala, e la regola sull'unico modulo che conosce Rich ----------------


def test_la_schermata_sta_nelle_trenta_righe_della_registrazione() -> None:
    """Cento per trenta non è una scelta di questo task: è già nel repository.

    `tools/registra-terminale.py` fissa 100x30 per le registrazioni di riserva, con la
    ragione scritta accanto — «sta su uno schermo da sala senza che il testo vada a capo
    dove non deve». Il Task 18 produrrà le registrazioni con `--sink plain` **dentro**
    quello strumento: una schermata più alta di trenta righe non si vedrebbe intera
    proprio nel piano B.
    """
    assert (COLONNE_SALA, RIGHE_SALA) == (100, 30)
    assert ALTEZZA_INTESTAZIONE == 4 + SERVER_MOSTRATI
    assert ALTEZZA_INTESTAZIONE + RIGHE_CRONACA <= RIGHE_SALA


def test_dentro_la_presentazione_rich_lo_importa_un_modulo_solo() -> None:
    """La regola che tiene in piedi tutto il resto di questo file.

    Se Rich entrasse in `plain.py` o in `scena.py`, due cose cadrebbero insieme: le prove
    qui sopra proverebbero Rich senza dirlo, e `--sink plain` — quello con cui si girano
    le registrazioni e si misura al Task 16 — si porterebbe dietro la TUI che dichiara di
    non usare.
    """
    trovati: dict[str, set[str]] = {}
    for modulo in sorted((SORGENTI / "presentation").rglob("*.py")):
        fuori = estranei(modulo.read_text(encoding="utf-8"))
        if fuori:
            trovati[modulo.name] = fuori

    assert trovati == {"rich_tui.py": {"rich"}}


def test_il_modulo_della_tui_si_importa() -> None:
    """L'unica prova che tocca `RichTui`, e non disegna niente.

    Il piano vieta di provare il disegno, non di accertarsi che il modulo esista: un
    `ImportError` in `presentation/rich_tui.py` è un difetto che si scopre all'avvio, e
    l'avvio, il 18 settembre, è in sala.
    """
    from mongolab.presentation.rich_tui import RichTui

    assert callable(RichTui.emit)


@pytest.mark.parametrize("larghezza", [0, -1])
def test_una_larghezza_impossibile_e_un_errore_non_una_riga_vuota(larghezza: int) -> None:
    # Il ripiego silenzioso qui sarebbe una riga vuota per ogni evento: una cronaca che
    # scorre senza dire niente, e nessuno che sappia perché.
    with pytest.raises(ValueError):
        riga(WriteSucceeded(ISTANTE, 3, 12.34), larghezza=larghezza)


# --- Le due prove che il giro di rotture ha reclamato ---------------------------------
#
# Le mutazioni del Task 10 sono state scoperte tutte tranne due, ed erano tutte e due in
# `rich_tui.py`: `auto_refresh=True` e il `aggiorna()` finale tolto. Il Passo 4 vieta di
# provare **il disegno**; queste due righe non disegnano niente — sono la promessa di
# ADR-0019 e la fine del ciclo. Un divieto letto come «di RichTui non si prova nulla»
# avrebbe lasciato senza guardia proprio le due righe che il resto del progetto cita.


def _tui_muta() -> "RichTui":
    """Una TUI che scrive in memoria: serve a non sporcare il terminale, non a leggere."""
    import io

    from rich.console import Console

    from mongolab.presentation.rich_tui import RichTui

    console = Console(
        file=io.StringIO(), force_terminal=True, width=COLONNE_SALA, height=RIGHE_SALA
    )
    return RichTui(FakeClock(ISTANTE), console=console)


def test_mentre_la_tui_e_accesa_non_nasce_nessun_altro_thread() -> None:
    """La promessa di ADR-0019, verificata invece che dichiarata.

    Rich, con le impostazioni predefinite, avvia un `_RefreshThread` demone che chiama
    `refresh()` per conto suo ([M-027]): la promessa «un solo thread tocca `Live`»
    sarebbe falsa senza `auto_refresh=False`. Questa prova non guarda cosa Rich disegna
    — guarda **quanti thread** ci sono, che è l'unica cosa che ADR-0019 promette.
    """
    tui = _tui_muta()
    prima = set(threading.enumerate())

    with tui.acceso():
        durante = set(threading.enumerate())

    assert durante - prima == set(), f"Live ha avviato {durante - prima}"


def test_l_ultimo_evento_si_vede_anche_se_arriva_a_ciclo_finito() -> None:
    """Il fatto che chiude la scena arriva sempre dopo l'ultimo giro.

    In ogni scenario l'evento finale — il primario ritrovato, il restore concluso — è
    proprio quello che il pubblico deve leggere. Se il ciclo uscisse senza un ultimo
    assorbimento, quell'evento resterebbe in coda e la sala vedrebbe la penultima riga.
    """
    tui = _tui_muta()
    giri: list[int] = []

    def finche() -> bool:
        giri.append(len(giri))
        if len(giri) > 1:
            # Arriva quando il ciclo ha già deciso di finire: il caso da coprire.
            tui.emit(WriteSucceeded(ISTANTE, 7, 1.0))
            return False
        return True

    tui.esegui(finche)

    assert tui.in_coda == 0


# --- Quanti server stanno nell'intestazione, e l'omissione dichiarata -----------------


def _topologia_con(quanti: int) -> DescrizioneTopologia:
    return DescrizioneTopologia(
        tipo=TipoTopologia.REPLICA_SET_CON_PRIMARIO,
        server=tuple(
            DescrizioneServer(f"mongo-rs-{n}:27017", RuoloServer.SECONDARIO, ritardo_ms=1.0)
            for n in range(quanti)
        ),
        nome_set="rs0",
    )


def test_il_caso_peggiore_misurato_ci_sta_tutto() -> None:
    """Tre server, che è quanti ne vede un client del replica set ([M-029]).

    Il numero è misurato e non stimato: la prima versione di questo modulo ne riservava
    otto, con una giustificazione — «due shard da due membri, tre config, un mongos» —
    che descriveva i **container** dello stack 03 e non ciò che il driver vede. Un client
    di un mongos vede il mongos. Le cinque righe di troppo le pagava la cronaca.
    """
    assert SERVER_MOSTRATI == 3
    assert len(server_da_mostrare(_topologia_con(3))) == 3


def test_i_server_in_piu_non_spariscono_in_silenzio() -> None:
    """Se un giorno il set avesse cinque membri, la schermata deve **dirlo**.

    Il pannello ha altezza fissa apposta, e quindi qualcosa va tagliato. Tagliare senza
    dirlo però sarebbe la cosa peggiore possibile in questa scena: chi guarda conta i
    server per capire se il cluster è integro, e un elenco troncato in silenzio si legge
    come un cluster più piccolo di quello che è.
    """
    righe_tabella = server_da_mostrare(_topologia_con(5))

    assert len(righe_tabella) == SERVER_MOSTRATI
    assert righe_tabella[-1][0] == "… e altri 3"
    assert [r[0] for r in righe_tabella[:-1]] == ["mongo-rs-0:27017", "mongo-rs-1:27017"]


@pytest.mark.parametrize("quanti", [0, 1, 2, 3, 4, 8, 40])
def test_la_tabella_dei_server_non_sfonda_mai_il_pannello(quanti: int) -> None:
    assert len(server_da_mostrare(_topologia_con(quanti))) <= SERVER_MOSTRATI


# --- Il taglio, estratto al Task 11 perché i consumatori sono diventati due ------------


def test_il_taglio_lascia_stare_ciò_che_ci_sta() -> None:
    assert tronca("corto", 100) == "corto"


def test_il_taglio_dichiara_di_aver_tagliato() -> None:
    tagliato = tronca("x" * 200, 100)

    assert len(tagliato) == 100
    assert tagliato.endswith(TRONCAMENTO)


def test_senza_larghezza_non_si_taglia() -> None:
    # È ciò che serve a chi reindirizza su file per analizzare dopo: là le colonne di
    # sala non contano, e un troncamento sarebbe una perdita di dati.
    lungo = "x" * 500

    assert tronca(lungo, None) == lungo


def test_una_larghezza_non_positiva_e_rifiutata() -> None:
    with pytest.raises(ValueError, match="colonne"):
        tronca("qualunque", 0)
