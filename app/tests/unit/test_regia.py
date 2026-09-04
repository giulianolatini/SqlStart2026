"""Le due regie: quella che comanda e quella che annuncia.

**Il comando non si esegue davvero, ma il processo sì.** Come per `SubprocessBackup` al
Task 9, l'eseguibile arriva dal costruttore e nella prova è un programmino Python che
scrive su un diario quello che gli è stato passato. Si verifica quindi la stessa cosa che
gira in produzione — argomenti, codice d'uscita, `stderr` — senza che serva Docker e senza
che nessun container venga fermato per errore mentre la suite gira.
"""

import ast
from pathlib import Path
import sys
import pytest

from mongolab.infrastructure.backup import ComandoFallito
from mongolab.infrastructure.regia import (
    ARRESTO_BRUSCO,
    ComandiCompose,
    RegiaAnnunciata,
    RegiaCompose,
)

COMPOSE = Path("/lab/docker/02-replicaset/compose.yaml")

SORGENTE = """\
import sys

with open({diario!r}, "a", encoding="utf-8") as diario:
    diario.write(repr(sys.argv[1:]) + "\\n")
sys.stderr.write({messaggio!r})
sys.exit({codice})
"""


def finto(
    dove: Path, *, codice: int = 0, messaggio: str = ""
) -> tuple[tuple[str, ...], Path]:
    """Un programma che si comporta come `docker compose`, e il diario di ciò che riceve."""
    diario = dove / "diario.txt"
    sorgente = dove / "finto.py"
    sorgente.write_text(
        SORGENTE.format(diario=str(diario), messaggio=messaggio, codice=codice)
    )
    return (sys.executable, str(sorgente)), diario


def righe_di(diario: Path) -> list[list[str]]:
    if not diario.exists():
        return []
    return [list(ast.literal_eval(riga)) for riga in diario.read_text().splitlines()]


# --- Il frasario ------------------------------------------------------------------------


def test_i_quattro_verbi_diventano_quattro_righe_di_compose() -> None:
    comandi = ComandiCompose(file_compose=COMPOSE)

    assert comandi.per("ferma", "mongo-rs-1") == (
        "docker",
        "compose",
        "-f",
        str(COMPOSE),
        "kill",
        "-s",
        "SIGKILL",
        "mongo-rs-1",
    )
    assert comandi.per("riavvia", "mongo-rs-1")[-2:] == ("start", "mongo-rs-1")
    assert comandi.per("sospendi", "mongo-rs-1")[-2:] == ("pause", "mongo-rs-1")
    assert comandi.per("risveglia", "mongo-rs-1")[-2:] == ("unpause", "mongo-rs-1")


def test_l_arresto_predefinito_e_brusco_ed_e_una_scelta_misurata() -> None:
    """`kill -s SIGKILL` e non `stop`, e la differenza vale un ordine di grandezza.

    `docker compose stop` manda `SIGTERM`, e `mongod` lo tratta come uno spegnimento
    ordinato: cede il ruolo **prima** di uscire, e il nuovo primario arriva in mezzo
    secondo — è la strada che [V-029] ha misurato in 574, 480 e 486 ms. Con `SIGKILL` il
    processo sparisce senza cedere niente, e il replica set deve accorgersene e votare:
    9 812, 10 619, 10 943 ms, cioè la forbice 8-10 s che [V-031] ha messo sulle slide e
    che il Blocco 2 esiste per mostrare.

    Sono due scene diverse, e questa prova fissa quale delle due è quella predefinita:
    quella di cui esistono i numeri già misurati (ADR-0097).
    """
    assert ARRESTO_BRUSCO == ("kill", "-s", "SIGKILL")
    assert ComandiCompose(file_compose=COMPOSE).arresto == ARRESTO_BRUSCO

    ordinato = ComandiCompose(file_compose=COMPOSE, arresto=("stop",))
    assert ordinato.per("ferma", "mongo-rs-1")[-2:] == ("stop", "mongo-rs-1")


def test_il_progetto_entra_nella_riga_solo_se_c_e() -> None:
    """Serve quando il compose gira da una cartella diversa da quella del file.

    Senza `-p`, Compose deduce il nome del progetto dalla directory in cui si trova, e
    l'applicazione lanciata dalla radice del repository comanderebbe container di un
    progetto che non esiste — fallendo con «no such service», che è il messaggio meno
    utile possibile per dire «sei nella cartella sbagliata».
    """
    senza = ComandiCompose(file_compose=COMPOSE).per("ferma", "mongo-rs-1")
    assert "-p" not in senza

    con = ComandiCompose(file_compose=COMPOSE, progetto="02-replicaset").per(
        "ferma", "mongo-rs-1"
    )
    assert con[:6] == ("docker", "compose", "-p", "02-replicaset", "-f", str(COMPOSE))


def test_gli_env_file_precedono_il_file_compose_e_senza_di_loro_non_si_parte() -> None:
    """Senza `--env-file` Compose **non** parla dei container: si ferma a leggere il file.

    Non è una precauzione, è una misura. `docker compose -f
    docker/02-replicaset/compose.yaml ps` dalla radice del repository risponde sette
    volte «required variable MONGO_IMAGE is missing a value», e con il solo
    `tools/images.env` risponde ancora due volte per `PASSWORD_AMMINISTRATORE`: i
    `compose.yaml` di questo repository usano la forma `${VAR:?messaggio}`, che è un
    errore e non un valore vuoto. Servono tutti e due, e servono **prima** del
    sottocomando, perché sono opzioni globali del client.

    Quello che viaggia è il **percorso** del file, mai il suo contenuto: è la stessa cosa
    che fanno le variabili `COMPOSE_0X` del Makefile, ed è ciò che tiene la riga
    annunciata da `RegiaAnnunciata` innocua da leggere a schermo e da registrare.
    """
    comandi = ComandiCompose(
        file_compose=COMPOSE,
        ambiente=(Path("/lab/tools/images.env"), Path("/lab/docker/02-replicaset/.env")),
    )

    riga = comandi.per("ferma", "mongo-rs-1")

    assert riga[:6] == (
        "docker",
        "compose",
        "--env-file",
        "/lab/tools/images.env",
        "--env-file",
        "/lab/docker/02-replicaset/.env",
    )
    assert riga.index("--env-file") < riga.index("-f")


def test_un_verbo_che_non_esiste_si_ferma_qui() -> None:
    with pytest.raises(KeyError):
        ComandiCompose(file_compose=COMPOSE).per("distruggi", "mongo-rs-1")


# --- La regia che comanda -----------------------------------------------------------------


def test_la_regia_esegue_il_comando_del_frasario(tmp_path: Path) -> None:
    comando, diario = finto(tmp_path)
    regia = RegiaCompose(
        ComandiCompose(file_compose=COMPOSE, comando=comando), scadenza_s=10.0
    )

    regia.ferma("mongo-rs-1")
    regia.riavvia("mongo-rs-1")

    ricevuti = righe_di(diario)
    assert ricevuti[0][-4:] == ["kill", "-s", "SIGKILL", "mongo-rs-1"]
    assert ricevuti[1][-2:] == ["start", "mongo-rs-1"]


def test_i_due_verbi_della_partizione_arrivano_a_compose(tmp_path: Path) -> None:
    comando, diario = finto(tmp_path)
    regia = RegiaCompose(ComandiCompose(file_compose=COMPOSE, comando=comando))

    regia.sospendi("mongo-rs-2")
    regia.risveglia("mongo-rs-2")

    assert [riga[-2:] for riga in righe_di(diario)] == [
        ["pause", "mongo-rs-2"],
        ["unpause", "mongo-rs-2"],
    ]


def test_un_uscita_diversa_da_zero_diventa_un_errore_con_dentro_il_motivo(
    tmp_path: Path,
) -> None:
    """Senza questa riga la scena proseguirebbe su un primario ancora in piedi.

    È il caso peggiore fra tutti quelli che questo adattatore può incontrare, perché non
    somiglia a un guasto: i numeri finali sarebbero zero millisecondi di interruzione e
    zero scritture perse, cioè un failover perfetto. La sala vedrebbe la slide sbagliata
    e nessuno avrebbe modo di saperlo.
    """
    comando, _ = finto(tmp_path, codice=1, messaggio="no such service: mongo-rs-9\n")
    regia = RegiaCompose(ComandiCompose(file_compose=COMPOSE, comando=comando))

    with pytest.raises(ComandoFallito) as errore:
        regia.ferma("mongo-rs-9")

    assert "no such service" in str(errore.value)
    assert "1" in str(errore.value)


def test_la_regia_soddisfa_la_porta(tmp_path: Path) -> None:
    from mongolab.domain.porte import Regia

    comando, _ = finto(tmp_path)
    regia: Regia = RegiaCompose(ComandiCompose(file_compose=COMPOSE, comando=comando))
    assert isinstance(regia, Regia)


# --- La regia che annuncia ------------------------------------------------------------


def test_la_regia_annunciata_scrive_il_comando_e_aspetta() -> None:
    """Dentro la rete Docker un client **non può** fermare un container, e lo dice.

    L'applicazione sta dentro la rete perché è l'unico posto da cui la scoperta della
    topologia funziona ([M-019]); da lì non ha il socket del demone, e nessuna riga di
    codice glielo può dare senza montarlo — che il Task 9 ha deciso di non fare. Questa
    regia non finge: stampa la riga esatta da incollare in un'altra finestra e si ferma
    finché qualcuno non conferma di averla eseguita.
    """
    detto: list[str] = []
    confermati: list[str] = []
    regia = RegiaAnnunciata(
        ComandiCompose(file_compose=COMPOSE),
        annuncia=detto.append,
        conferma=confermati.append,
    )

    regia.ferma("mongo-rs-1")

    assert len(detto) == 1
    assert "docker compose" in detto[0]
    assert "kill -s SIGKILL mongo-rs-1" in detto[0]
    assert confermati == [detto[0]]


def test_la_regia_annunciata_annuncia_prima_di_chiedere_conferma() -> None:
    """L'ordine conta: chiedere «fatto?» prima di aver detto che cosa è una domanda muta."""
    fatti: list[str] = []
    regia = RegiaAnnunciata(
        ComandiCompose(file_compose=COMPOSE),
        annuncia=lambda riga: fatti.append("annuncio"),
        conferma=lambda riga: fatti.append("conferma"),
    )

    regia.sospendi("mongo-rs-2")

    assert fatti == ["annuncio", "conferma"]


def test_la_regia_annunciata_copre_tutti_e_quattro_i_verbi() -> None:
    detto: list[str] = []
    regia = RegiaAnnunciata(
        ComandiCompose(file_compose=COMPOSE),
        annuncia=detto.append,
        conferma=lambda riga: None,
    )

    regia.ferma("mongo-rs-1")
    regia.riavvia("mongo-rs-1")
    regia.sospendi("mongo-rs-2")
    regia.risveglia("mongo-rs-2")

    verbi = [riga.rsplit(" ", 2)[-2] for riga in detto]
    assert verbi == ["SIGKILL", "start", "pause", "unpause"]


def test_la_regia_annunciata_soddisfa_la_porta() -> None:
    from mongolab.domain.porte import Regia

    regia: Regia = RegiaAnnunciata(
        ComandiCompose(file_compose=COMPOSE),
        annuncia=lambda riga: None,
        conferma=lambda riga: None,
    )
    assert isinstance(regia, Regia)


def test_il_frasario_nomina_il_file_della_credenziale_e_mai_il_suo_valore() -> None:
    """ADR-0054 vieta il **valore**, non il file. La differenza è tutta la guardia.

    `--env-file docker/02-replicaset/.env` passa un percorso: chi legge la riga a schermo
    vede dove sta il segreto, non il segreto. `-e PASSWORD_AMMINISTRATORE=...` passerebbe
    il valore, e finirebbe nella tabella dei processi — visibile a `ps` da qualunque
    utente della macchina — e dentro le registrazioni asciinema del Task 18, che sono
    testo e vanno in git.

    La guardia è scritta sul frasario **completo**, quello con gli env-file dentro,
    perché è quello che gira davvero: provarla sulla forma predefinita, che di env-file
    non ne ha nessuno, sarebbe una guardia che sorveglia un caso che non si usa.
    """
    comandi = ComandiCompose(
        file_compose=COMPOSE,
        ambiente=(Path("/lab/tools/images.env"), Path("/lab/docker/02-replicaset/.env")),
    )
    tutte: list[str] = []
    for verbo in ("ferma", "riavvia", "sospendi", "risveglia"):
        tutte.extend(comandi.per(verbo, "mongo-rs-1"))

    assert not any(pezzo == "-e" or pezzo.startswith("-e") for pezzo in tutte)
    assert not any(pezzo.startswith("--env") and pezzo != "--env-file" for pezzo in tutte)
    assert not any("=" in pezzo for pezzo in tutte)
    assert not any("PASSWORD" in pezzo.upper() for pezzo in tutte)
