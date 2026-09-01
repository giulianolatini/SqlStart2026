"""Il registratore di terminale, che produce la riserva del talk.

Serve perché ciò che questo strumento produce si guarda **il giorno in cui la demo
non parte** (ADR-0050): se scrive male, lo si scopre nel momento peggiore possibile.
Un `.cast` rotto non se ne accorge nessuno finché non lo si riproduce davanti a
qualcuno.

Il primo caso è la regressione di un errore vero. La prima registrazione è morta con
`comando non trovato: --titolo`, perché `argparse.REMAINDER`, dopo il primo argomento
posizionale, raccoglie anche le opzioni del programma. La divisione su `--` adesso si
fa a mano, e questo test è ciò che impedisce di tornare alla scorciatoia.

Si esercita la riga di comando e non le funzioni: è la riga di comando che sta scritta
nella pagina delle registrazioni, ed è quella che il relatore digiterà.
"""

import json
import subprocess
import sys
from pathlib import Path

STRUMENTO = Path(__file__).resolve().parents[1] / "registra-terminale.py"


def esegui(*argomenti: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(STRUMENTO), *argomenti], capture_output=True, text=True
    )


def intestazione_e_testo(registrazione: Path) -> tuple[dict, str]:
    """L'intestazione della registrazione, e tutto ciò che il terminale ha stampato."""
    righe = registrazione.read_text(encoding="utf-8").splitlines()
    eventi = [json.loads(riga) for riga in righe[1:]]
    return json.loads(righe[0]), "".join(testo for _, tipo, testo in eventi if tipo == "o")


def test_il_titolo_non_finisce_nel_comando_da_registrare(tmp_path):
    """La regressione: `--titolo` sta prima di `--`, quindi è del programma."""
    destinazione = tmp_path / "prova.cast"
    esito = esegui(str(destinazione), "--titolo", "Una scena", "--", "echo", "ciao")

    assert esito.returncode == 0, esito.stderr
    intestazione, testo = intestazione_e_testo(destinazione)
    assert intestazione["title"] == "Una scena"
    assert "ciao" in testo


def test_l_intestazione_e_un_asciinema_v2(tmp_path):
    """Il formato è di asciinema perché chi ce l'ha deve poter usare quello."""
    destinazione = tmp_path / "prova.cast"
    esito = esegui(str(destinazione), "--righe", "10", "--colonne", "40", "--", "echo", "x")

    assert esito.returncode == 0, esito.stderr
    intestazione, _ = intestazione_e_testo(destinazione)
    assert intestazione["version"] == 2
    assert (intestazione["height"], intestazione["width"]) == (10, 40)
    assert isinstance(intestazione["timestamp"], int)


def test_il_comando_vede_le_dimensioni_dichiarate_e_non_quelle_di_chi_registra(tmp_path):
    """Se il pty non venisse dimensionato, la scena andrebbe a capo dove capita."""
    destinazione = tmp_path / "prova.cast"
    esito = esegui(str(destinazione), "--righe", "10", "--colonne", "40", "--", "stty", "size")

    assert esito.returncode == 0, esito.stderr
    _, testo = intestazione_e_testo(destinazione)
    assert "10 40" in testo


def test_i_tempi_crescono_e_partono_da_dopo_l_avvio(tmp_path):
    """I tempi *sono* il contenuto di queste scene: un failover senza attesa non
    racconta niente. Devono essere monotòni, altrimenti la riproduzione va a scatti."""
    destinazione = tmp_path / "prova.cast"
    esito = esegui(str(destinazione), "--", "sh", "-c", "echo uno; sleep 0.3; echo due")

    assert esito.returncode == 0, esito.stderr
    righe = destinazione.read_text(encoding="utf-8").splitlines()[1:]
    istanti = [json.loads(riga)[0] for riga in righe]
    assert istanti == sorted(istanti)
    assert istanti[0] >= 0
    assert istanti[-1] >= 0.3


def test_riproduce_quello_che_ha_registrato(tmp_path):
    """Senza asciinema installato: una riserva che va installata non è una riserva."""
    destinazione = tmp_path / "prova.cast"
    assert esegui(str(destinazione), "--titolo", "T", "--", "echo", "ciao").returncode == 0

    riproduzione = esegui("--riproduci", str(destinazione), "--velocita", "100")
    assert riproduzione.returncode == 0, riproduzione.stderr
    assert "ciao" in riproduzione.stdout
    # Il titolo va su stderr, così una riproduzione dentro una pipe resta pulita.
    assert "T" in riproduzione.stderr


def test_riporta_il_codice_di_uscita_del_comando(tmp_path):
    """Una demo fallita resta registrata, ma chi la gira deve saperlo subito."""
    destinazione = tmp_path / "prova.cast"
    esito = esegui(str(destinazione), "--", "sh", "-c", "echo rotta; exit 3")

    assert esito.returncode == 3
    assert destinazione.exists()
    assert "rotta" in intestazione_e_testo(destinazione)[1]


def test_un_comando_che_non_esiste_non_lascia_una_registrazione(tmp_path):
    """L'errore che aveva sepolto quello vero: proseguire e leggere il file mai
    scritto sostituiva il messaggio utile con un `FileNotFoundError`."""
    destinazione = tmp_path / "prova.cast"
    esito = esegui(str(destinazione), "--", "comando-che-non-esiste-davvero")

    assert esito.returncode == 127
    assert "comando non trovato" in esito.stderr
    assert "FileNotFoundError" not in esito.stderr
    assert not destinazione.exists()


def test_senza_il_doppio_trattino_si_ferma_invece_di_indovinare(tmp_path):
    destinazione = tmp_path / "prova.cast"
    esito = esegui(str(destinazione), "--titolo", "T")

    assert esito.returncode == 2
    assert "manca il comando da registrare" in esito.stderr
    assert not destinazione.exists()
