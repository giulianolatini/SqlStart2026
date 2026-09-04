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


def test_un_file_che_esiste_ma_non_si_esegue_non_finisce_in_un_traceback(tmp_path):
    """Il pre-controllo guardava se il file *esiste*, non se si può eseguire: il
    traceback di `execvpe` veniva scritto **dentro** la registrazione, con i percorsi
    assoluti della macchina di chi registra, e l'uscita era 1 invece che 126."""
    finto = tmp_path / "non-eseguibile.sh"
    finto.write_text("#!/bin/sh\necho ciao\n", encoding="utf-8")
    finto.chmod(0o644)
    destinazione = tmp_path / "prova.cast"

    esito = esegui(str(destinazione), "--", str(finto))

    assert esito.returncode == 126
    assert "non eseguibile" in esito.stderr
    assert "Traceback" not in esito.stderr
    assert not destinazione.exists()


def test_se_l_esecuzione_fallisce_lo_stesso_la_registrazione_non_contiene_un_traceback(tmp_path):
    """Un controllo preventivo non copre tutti i modi di fallire di `execvpe`: una
    directory è eseguibile per il sistema e non lo è per `exec`. Il figlio deve dirlo
    in una riga, non riversare Python nello pseudo-terminale che si sta registrando."""
    destinazione = tmp_path / "prova.cast"

    esito = esegui(str(destinazione), "--", str(tmp_path))

    assert esito.returncode == 126
    assert "Traceback" not in esito.stderr
    if destinazione.exists():
        assert "Traceback" not in intestazione_e_testo(destinazione)[1]


def test_una_velocita_nulla_si_rifiuta_invece_di_dividere_per_zero(tmp_path):
    """La riproduzione è la riserva del talk: un `ZeroDivisionError` lì è l'errore
    peggiore nel momento peggiore. Si rifiuta l'argomento, non si divide."""
    destinazione = tmp_path / "prova.cast"
    esegui(str(destinazione), "--", "echo", "ciao")

    esito = esegui(str(destinazione), "--riproduci", "--velocita", "0")

    assert esito.returncode == 2
    assert "ZeroDivisionError" not in esito.stderr
    assert "velocita" in esito.stderr


def test_riproduci_dopo_il_doppio_trattino_appartiene_al_comando_registrato(tmp_path):
    """L'immagine speculare della regressione del primo test: là erano le opzioni di
    questo programma a finire nel comando, qui è un'opzione del comando a essere letta
    come propria. `--` divide in due, e la divisione vale in tutte e due i versi."""
    destinazione = tmp_path / "prova.cast"

    esito = esegui(str(destinazione), "--", "echo", "--riproduci")

    assert esito.returncode == 0
    assert destinazione.exists()
    assert "--riproduci" in intestazione_e_testo(destinazione)[1]


def test_riproduci_con_un_comando_da_registrare_si_ferma_invece_di_ignorarlo(tmp_path):
    """Chiedere insieme le due cose è un errore di chi digita, e va detto: prima
    `argparse` lo segnalava per caso, come «unrecognized arguments»."""
    destinazione = tmp_path / "prova.cast"
    esegui(str(destinazione), "--", "echo", "ciao")

    esito = esegui(str(destinazione), "--riproduci", "--", "echo", "ciao")

    assert esito.returncode == 2
    assert "riproduci" in esito.stderr


def test_il_codice_di_uscita_sopravvive_a_un_figlio_che_tiene_aperto_il_pty(tmp_path):
    """Il ciclo di cattura ha due uscite: il pty che si chiude, e il comando che finisce
    **senza** chiuderlo perché ha lasciato dietro di sé un discendente. La seconda
    raccoglieva il processo e ne buttava via lo stato, e la `waitpid` finale — che non
    trovava più nessuno — ripiegava su 0: una demo fallita veniva riportata riuscita.

    Il caso non si vede su macOS, dove il kernel revoca il terminale di controllo appena
    il leader di sessione muore e il pty si chiude comunque. Si vede su Linux, dove il
    discendente lo tiene aperto: là questo test falliva riportando 0 al posto di 7."""
    lascia_un_discendente = (
        "import os, sys, time\n"
        "if os.fork() == 0:\n"
        "    os.setsid()\n"  # fuori dalla sessione del terminale: niente SIGHUP
        "    time.sleep(2)\n"  # e intanto tiene aperto il lato schiavo che ha ereditato
        "    os._exit(0)\n"
        "sys.exit(7)\n"
    )
    destinazione = tmp_path / "prova.cast"

    esito = esegui(str(destinazione), "--", sys.executable, "-c", lascia_un_discendente)

    assert esito.returncode == 7


# --- La regia: chi fa da seconda finestra -----------------------------------------------
#
# `mongolab demo failover`, girando dentro la rete Compose, vede la topologia ma non ha il
# socket del demone: annuncia il comando che ferma il primario e aspetta un Invio da chi lo
# ha eseguito altrove. Dal palco quel qualcuno è una persona; per registrare la scena deve
# essere questo strumento, o la registrazione non esisterebbe.


def copione(percorso: Path, riga_annunciata: str) -> Path:
    """Un finto comando che annuncia una riga e poi aspetta che qualcuno confermi."""
    sorgente = percorso / "scena.py"
    sorgente.write_text(
        "import sys\n"
        f"print({riga_annunciata!r}, flush=True)\n"
        "input('   Invio quando è stato eseguito ')\n"
        "print('ripartito', flush=True)\n",
        encoding="utf-8",
    )
    return sorgente


def test_la_regia_esegue_la_riga_annunciata_e_poi_manda_l_invio(tmp_path):
    """Le due metà del ponte: il comando gira davvero, e la scena riparte."""
    fatto = tmp_path / "fatto"
    scena = copione(tmp_path, f"touch {fatto}")
    destinazione = tmp_path / "prova.cast"

    esito = esegui(
        str(destinazione), "--regia", "touch ", "--", sys.executable, str(scena)
    )

    assert esito.returncode == 0, esito.stderr
    assert fatto.exists(), "la regia non ha eseguito la riga annunciata"
    _, testo = intestazione_e_testo(destinazione)
    assert "ripartito" in testo, "la scena non ha ricevuto l'Invio"


def test_senza_regia_la_riga_annunciata_resta_una_riga(tmp_path):
    """La regia è esplicita: senza, questo strumento registra e basta."""
    fatto = tmp_path / "fatto"
    scena = tmp_path / "scena.py"
    scena.write_text(f"print('touch {fatto}')\n", encoding="utf-8")
    destinazione = tmp_path / "prova.cast"

    esito = esegui(str(destinazione), "--", sys.executable, str(scena))

    assert esito.returncode == 0, esito.stderr
    assert not fatto.exists(), "senza --regia nessuna riga si esegue"


def test_la_regia_esegue_solo_le_righe_che_cominciano_con_il_prefisso(tmp_path):
    """Il prefisso è la guardia: una riga qualsiasi dell'uscita non è un comando."""
    fatto = tmp_path / "fatto"
    scena = tmp_path / "scena.py"
    scena.write_text(f"print('non è un comando: touch {fatto}')\n", encoding="utf-8")
    destinazione = tmp_path / "prova.cast"

    esito = esegui(str(destinazione), "--regia", "touch ", "--", sys.executable, str(scena))

    assert esito.returncode == 0, esito.stderr
    assert not fatto.exists(), "il prefisso vale dall'inizio della riga, non ovunque"


def test_la_regia_riconosce_la_riga_annunciata_anche_se_rientrata(tmp_path):
    """Il caso vero: `mongolab` non annuncia a colonna zero, rientra di due spazi.

    `_da_un_altra_finestra` stampa «▸ da un'altra finestra…» e poi il comando con due
    spazi davanti, perché a schermo va staccato dal testo che lo introduce. Un confronto
    che pretendesse il prefisso a colonna zero non troverebbe mai niente, e la scena
    resterebbe appesa all'`input()` **per sempre**: non fallirebbe, si pianterebbe. Questa
    prova esiste perché quel rientro è portante e non si vede leggendo la condizione.
    """
    fatto = tmp_path / "fatto"
    scena = copione(tmp_path, f"  touch {fatto}")
    destinazione = tmp_path / "prova.cast"

    esito = esegui(str(destinazione), "--regia", "touch ", "--", sys.executable, str(scena))

    assert esito.returncode == 0, esito.stderr
    assert fatto.exists(), "una riga rientrata è la riga che l'applicazione annuncia davvero"
    _, testo = intestazione_e_testo(destinazione)
    assert "ripartito" in testo, "la scena non ha ricevuto l'Invio"


def test_la_regia_non_esegue_una_riga_che_il_prefisso_ce_l_ha_dentro(tmp_path):
    """Tollerare il rientro non vuol dire cercare il prefisso ovunque.

    Fra «spazi a sinistra» e «testo a sinistra» c'è la differenza fra una riga annunciata
    e una riga che *parla* di un comando — un log, una citazione, un messaggio d'errore che
    riporta ciò che ha provato a fare. La prima si esegue, la seconda no.
    """
    fatto = tmp_path / "fatto"
    scena = tmp_path / "scena.py"
    scena.write_text(f"print('  # poi: touch {fatto}')\n", encoding="utf-8")
    destinazione = tmp_path / "prova.cast"

    esito = esegui(str(destinazione), "--regia", "touch ", "--", sys.executable, str(scena))

    assert esito.returncode == 0, esito.stderr
    assert not fatto.exists(), "a sinistra del prefisso possono esserci spazi, non parole"


def test_la_regia_non_conferma_un_comando_fallito(tmp_path):
    """L'invariante che `RegiaCompose` protegge, dall'altra parte del confine.

    Il docstring di quella classe dice perché un comando di guasto fallito e ignorato è
    grave: «un `stop` fallito lascerebbe il primario in piedi, e i due numeri finali
    sarebbero zero millisecondi di interruzione e zero scritture perse — cioè un failover
    perfetto. La sala vedrebbe la slide sbagliata senza che nessuno abbia modo di
    accorgersene.» Quando si registra, questa funzione **sta al posto** di quella regia:
    se manda l'Invio comunque, il `.cast` racconta un guasto mai avvenuto, e nessuno
    guardando la registrazione può accorgersene.

    Rilievo della review di `codex` sulla PR #5, 4 settembre 2026.
    """
    guasto = tmp_path / "ferma-il-primario"
    guasto.write_text("#!/bin/sh\nexit 7\n", encoding="utf-8")
    guasto.chmod(0o755)
    scena = copione(tmp_path, f"  {guasto} mongo-rs-1")
    destinazione = tmp_path / "prova.cast"

    esito = esegui(
        str(destinazione), "--regia", str(guasto), "--", sys.executable, str(scena)
    )

    assert esito.returncode == 125, "una regia fallita non è una registrazione riuscita"
    assert "uscita 7" in esito.stderr
    assert "non riparte" in esito.stderr
    _, testo = intestazione_e_testo(destinazione)
    assert "ripartito" not in testo, "la scena è ripartita senza che il guasto sia avvenuto"


def test_la_regia_su_una_riproduzione_si_ferma_invece_di_non_fare_niente(tmp_path):
    """Una registrazione già girata non ha una seconda finestra da azionare."""
    destinazione = tmp_path / "prova.cast"
    esegui(str(destinazione), "--", "echo", "x")

    esito = esegui(str(destinazione), "--riproduci", "--regia", "touch ")

    assert esito.returncode != 0
    assert "seconda finestra" in esito.stderr
