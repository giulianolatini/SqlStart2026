"""Il registratore di schermo, che produce i filmati da caricare e da allegare.

È il gemello di `test_registra_terminale.py`, e nasce dalla stessa paura: ciò che
questo strumento produce si guarda **quando il filmato serve**, cioè troppo tardi per
rigirarlo. Un `.mp4` senza traccia audio, girato credendo di parlarci sopra, sembra
riuscito fino al momento in cui lo si apre davanti a qualcuno.

Nessuna prova qui gira un filmato. Registrare vuol dire aprire lo schermo e il
microfono, cioè chiedere a macOS due permessi che una suite non deve pretendere, e
aspettare secondi veri: una suite che accende un dispositivo è una suite che non si
esegue. Si esercitano invece i **rifiuti** — che stanno tutti prima di ffmpeg — e le
coerenze fra file che nessuno dei due può controllare da solo, nello spirito di
`test_coerenza_repo.py`.

La coerenza che conta più delle altre è quella sulla cartella: `preflight.sh` conta i
`.mp4` in una cartella, questo strumento ce li scrive, e i due la calcolano ognuno per
conto suo. Il giorno in cui una delle due righe cambia, il preflight dichiarerebbe zero
filmati con la cartella piena — un allarme che si impara a ignorare, che è il modo in
cui un controllo smette di controllare.
"""

import os
import pathlib
import shutil
import subprocess

import pytest

RADICE = pathlib.Path(__file__).resolve().parents[2]
STRUMENTO = RADICE / "tools/registra-schermo.sh"
PREFLIGHT = RADICE / "tools/preflight.sh"
MAKEFILE = RADICE / "Makefile"
PAGINA_REGISTRAZIONI = RADICE / "docs/05-talk/registrazioni/README.md"

# La cartella predefinita, scritta qui una terza volta di proposito: se la prova la
# leggesse dallo strumento, verificherebbe che lo strumento è d'accordo con sé stesso.
CARTELLA_PREDEFINITA = "${HOME}/SqlStart2026-registrazioni"

senza_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="ffmpeg non è installato: questo caso arriva dopo il controllo dei prerequisiti",
)


def esegui(*argomenti: str, **ambiente: str) -> subprocess.CompletedProcess:
    """Esegue lo strumento con un ambiente controllato.

    `DEMO_VIDEOS_DIR` è sempre imposto dalle prove: senza, un caso che sbagliasse
    scriverebbe nella cartella vera delle registrazioni del talk.
    """
    return subprocess.run(
        [str(STRUMENTO), *argomenti],
        capture_output=True,
        text=True,
        env={**os.environ, **ambiente},
    )


def test_lo_strumento_e_eseguibile():
    assert STRUMENTO.exists(), "manca tools/registra-schermo.sh"
    assert os.access(STRUMENTO, os.X_OK), (
        "lo strumento non ha il bit di esecuzione: la riga scritta nella documentazione "
        "è «./tools/registra-schermo.sh», e senza quel bit non funziona"
    )


# --- I rifiuti, che stanno tutti prima di ffmpeg -------------------------------------


def test_senza_nome_si_ferma_e_spiega_come_si_chiama(tmp_path):
    esito = esegui(DEMO_VIDEOS_DIR=str(tmp_path))
    assert esito.returncode == 2
    assert "manca il nome della scena" in esito.stderr
    # Il messaggio deve contenere l'uso: un errore che dice solo «manca» costringe a
    # cercare altrove quello che serve subito.
    assert "uso:" in esito.stderr


def test_un_nome_con_la_barra_e_un_percorso_e_viene_rifiutato(tmp_path):
    esito = esegui("scene/failover", DEMO_VIDEOS_DIR=str(tmp_path))
    assert esito.returncode == 2
    assert "DEMO_VIDEOS_DIR" in esito.stderr, (
        "rifiutare il percorso senza dire dove si sceglie la cartella lascia "
        "l'operatore senza la via d'uscita"
    )
    assert not list(tmp_path.iterdir()), "non deve aver scritto niente"


def test_una_durata_che_non_e_un_numero_di_secondi_viene_rifiutata(tmp_path):
    esito = esegui("prova", "venti", DEMO_VIDEOS_DIR=str(tmp_path))
    assert esito.returncode == 2
    assert "secondi interi" in esito.stderr


def test_un_audio_che_non_e_si_ne_no_viene_rifiutato(tmp_path):
    esito = esegui("prova", DEMO_VIDEOS_DIR=str(tmp_path), AUDIO="forse")
    assert esito.returncode == 2
    # Il messaggio elenca i due valori: sono due, e nominarli costa una riga.
    assert "si" in esito.stderr and "no" in esito.stderr


@pytest.mark.parametrize("valore", ["si", "sì", "no"])
def test_i_valori_leciti_di_audio_non_vengono_rifiutati(valore, tmp_path):
    """Il rifiuto di AUDIO non deve scattare sui valori buoni.

    Non si arriva a registrare: manca il nome, quindi lo strumento si ferma prima. Ciò
    che si verifica è che si fermi per QUELLA ragione e non per l'audio.
    """
    esito = esegui(DEMO_VIDEOS_DIR=str(tmp_path), AUDIO=valore)
    assert esito.returncode == 2
    assert "manca il nome della scena" in esito.stderr
    # Non basta cercare «AUDIO»: il testo d'uso lo nomina comunque, spiegando la
    # passata muta. Ciò che non deve comparire è il rifiuto.
    assert "non esiste" not in esito.stderr


@senza_ffmpeg
def test_non_sovrascrive_una_registrazione_che_esiste_gia(tmp_path):
    """Il caso che protegge il lavoro già fatto.

    Rigirare una scena col nome di una girata bene è un errore di distrazione da cui
    non si torna indietro: il file di prima non c'è più, e a volte non è ripetibile.
    """
    (tmp_path / "gia-girata.mp4").write_bytes(b"non sono un filmato, ma occupo il nome")
    esito = esegui("gia-girata", "1", DEMO_VIDEOS_DIR=str(tmp_path))
    assert esito.returncode == 2
    assert "esiste già" in esito.stderr
    assert (tmp_path / "gia-girata.mp4").read_bytes().startswith(b"non sono"), (
        "il file di prima deve essere intatto"
    )


@senza_ffmpeg
def test_il_suffisso_mp4_nel_nome_non_produce_un_doppio_suffisso(tmp_path):
    """`nome.mp4` e `nome` sono la stessa scena.

    Si verifica attraverso il rifiuto di sovrascrittura, che nomina il file di
    destinazione: chiedere «gia-girata.mp4» deve puntare a `gia-girata.mp4` e non a
    `gia-girata.mp4.mp4`.
    """
    (tmp_path / "gia-girata.mp4").write_bytes(b"occupo il nome")
    esito = esegui("gia-girata.mp4", DEMO_VIDEOS_DIR=str(tmp_path))
    assert esito.returncode == 2
    assert "gia-girata.mp4.mp4" not in esito.stderr


# --- Le coerenze fra file --------------------------------------------------------------


def test_la_cartella_dei_filmati_e_la_stessa_che_conta_il_preflight():
    """Chi scrive i filmati e chi li conta devono guardare nello stesso posto."""
    scrive = STRUMENTO.read_text(encoding="utf-8")
    conta = PREFLIGHT.read_text(encoding="utf-8")
    for sorgente, nome in ((scrive, "registra-schermo.sh"), (conta, "preflight.sh")):
        assert "DEMO_VIDEOS_DIR" in sorgente, f"{nome} non legge DEMO_VIDEOS_DIR"
        assert CARTELLA_PREDEFINITA in sorgente, (
            f"{nome} non usa più {CARTELLA_PREDEFINITA} come cartella predefinita: "
            "se cambia da una parte sola, il preflight conterà i filmati dove non sono"
        )


def test_il_makefile_offre_il_bersaglio_e_chiama_questo_strumento():
    """La riga che la documentazione insegna è `make filmato`, non lo script nudo."""
    makefile = MAKEFILE.read_text(encoding="utf-8")
    assert "\nfilmato:" in makefile, "manca il bersaglio `filmato`"
    assert "## " in makefile.split("\nfilmato:")[1].split("\n")[0], (
        "il bersaglio `filmato` non ha la riga di aiuto `##`, quindi `make help` non lo elenca"
    )
    assert "./tools/registra-schermo.sh" in makefile
    assert "filmato" in makefile.split(".PHONY:")[1].split("\n\n")[0], (
        "`filmato` non è in .PHONY: un file con quel nome nella radice lo zittirebbe"
    )


def test_la_pagina_delle_registrazioni_dice_il_comando_per_girare_un_filmato():
    """Il buco che questa tornata chiude.

    La procedura dei filmati diceva «si registra lo schermo» senza dire con che cosa.
    Una procedura che non si può eseguire leggendola è una procedura da riscrivere, e
    questa prova è ciò che impedisce di tornare a quella forma.
    """
    pagina = PAGINA_REGISTRAZIONI.read_text(encoding="utf-8")
    assert "make filmato" in pagina, "la pagina non nomina il comando"
    assert "AUDIO=no" in pagina, "la pagina non documenta la passata muta"
