"""Il produttore di filmati, che fabbrica i `.mp4` di riserva dalle registrazioni.

È il terzo strumento della famiglia, e va letto accanto agli altri due:
`registra-terminale.py` conserva quello che il terminale ha fatto, `registra-schermo.sh`
conserva quello che il pubblico avrebbe visto, e questo **trasforma il primo nel
secondo** senza riaccendere niente. Le scene sono già state eseguite davvero: rigirarle
costerebbe due stack, uno scambio di `.env` e un pomeriggio, e produrrebbe comunque una
esecuzione diversa da quella misurata.

La paura da cui nascono queste prove è precisa, e non è che lo strumento fallisca: è che
**riesca male**. Un filmato che esce più corto della scena che sostituisce sembra
riuscito — si apre, si vede, scorre — e mente sull'unica cosa per cui esiste. È già
successo due volte mentre lo strumento veniva scritto, per due cause diverse:

* `agg` comprime a cinque secondi ogni attesa più lunga, se non glielo si vieta: la
  scena 8, che dura 40,1 s, ne usciva 21,3 (V-107);
* i `.mp4` nati da una GIF hanno fotogrammi a durata variabile, e il montaggio che li
  incolla senza ricodificare butta via i secondi che non sa incastrare: il filmato 05
  usciva 47,1 s invece di 52,5 (V-107).

Nessuna delle due si vede leggendo il codice, e tutt'e due si vedono contando. Per
questo lo strumento confronta ogni filmato con la somma delle scene che lo compongono e
si **ferma** se non torna, e per questo le prove qui sotto sorvegliano i due flag che
tengono in piedi quel conto: chi li togliesse per fare prima romperebbe i filmati senza
rompere nessuna prova.

Nessuna prova qui produce un filmato. Rendere tredici file vuol dire minuti di CPU e
decine di megabyte, che una suite non deve spendere a ogni corsa: si esercitano il
catalogo, i rifiuti e le coerenze fra file che nessuno dei due può controllare da solo,
nello spirito di `test_coerenza_repo.py`.
"""

import json
import pathlib
import subprocess

import pytest

RADICE = pathlib.Path(__file__).resolve().parents[2]
STRUMENTO = RADICE / "tools/filmati-da-registrazioni.sh"
PREFLIGHT = RADICE / "tools/preflight.sh"
MAKEFILE = RADICE / "Makefile"
SCENE = RADICE / "docs/05-talk/registrazioni"
PAGINA_REGISTRAZIONI = SCENE / "README.md"

# La cartella predefinita, riscritta qui di proposito invece di leggerla dallo
# strumento: una prova che la ricavasse dal codice verificherebbe che il codice è
# d'accordo con sé stesso. È la stessa che conta `preflight.sh`, ed è il motivo per cui
# quel controllo passa da «nessun filmato» a «filmati locali disponibili: N».
CARTELLA_PREDEFINITA = "${HOME}/SqlStart2026-registrazioni"

# La registrazione più lunga dell'archivio dura 53,3 s. Il limite di inattività deve
# stare comodamente sopra: sotto, `agg` accorcia le attese, e le attese sono la scena.
CASTO_PIU_LUNGO = 60


def esegui(*argomenti: str, **ambiente: str) -> subprocess.CompletedProcess:
    """Chiama lo strumento dalla radice del repository, come lo chiama il Makefile."""
    import os

    return subprocess.run(
        [str(STRUMENTO), *argomenti],
        cwd=RADICE,
        capture_output=True,
        text=True,
        env={**os.environ, **ambiente},
    )


def catalogo() -> dict[str, list[str]]:
    """Il catalogo dichiarato dallo strumento: filmato → scene che lo compongono."""
    esito = esegui("--elenco")
    assert esito.returncode == 0, esito.stderr
    voci: dict[str, list[str]] = {}
    for riga in esito.stdout.splitlines():
        if ":" not in riga:
            continue
        nome, scene = riga.split(":", 1)
        voci[nome.strip()] = scene.split()
    return voci


def durata_cast(nome: str) -> float:
    """L'istante dell'ultimo evento di una registrazione, che è la sua durata."""
    ultima = (SCENE / f"{nome}.cast").read_text().splitlines()[-1]
    return float(json.loads(ultima)[0])


def test_lo_strumento_esiste_ed_e_eseguibile():
    assert STRUMENTO.exists(), "manca tools/filmati-da-registrazioni.sh"
    assert STRUMENTO.stat().st_mode & 0o111, "lo strumento non ha il bit di esecuzione"


def test_l_elenco_non_produce_niente_e_dichiara_il_catalogo():
    """`--elenco` serve a sapere che cosa uscirebbe senza aspettare che esca."""
    voci = catalogo()
    assert len(voci) >= 5, f"catalogo troppo corto: {sorted(voci)}"
    assert "01-failover-docker-kill-muto" in voci, "manca la scena del talk"


def test_ogni_filmato_del_catalogo_nasce_da_registrazioni_che_esistono():
    """Il catalogo nomina scene: se una non c'è, il guasto va scoperto adesso."""
    for filmato, scene in catalogo().items():
        assert scene, f"{filmato} non nomina nessuna scena"
        for scena in scene:
            assert (SCENE / f"{scena}.cast").exists(), (
                f"{filmato} nomina {scena}, che non è fra le registrazioni"
            )


def test_ogni_filmato_del_catalogo_esce_muto():
    """Il filmato che va dentro le slide non ha voce: è il muto di ADR-0140."""
    for filmato in catalogo():
        assert filmato.endswith("-muto"), (
            f"{filmato} non dichiara nel nome di essere la passata muta"
        )


def test_le_attese_non_si_comprimono():
    """Il flag che, tolto, accorcerebbe le scene senza rompere nient'altro.

    `agg --idle-time-limit` vale 5 secondi se non lo si dice, e comprime a cinque ogni
    pausa più lunga. Su queste scene la pausa non è tempo morto: nella 8 i quindici
    secondi prima dell'errore *sono* la risposta alla domanda.
    """
    testo = STRUMENTO.read_text()
    assert "--idle-time-limit" in testo, (
        "senza --idle-time-limit agg accorcia le attese, e le attese sono la scena"
    )
    valore = testo.split("--idle-time-limit", 1)[1].split()[0]
    assert int(valore) > CASTO_PIU_LUNGO, (
        f"--idle-time-limit {valore} è sotto la registrazione più lunga: le attese si perdono"
    )


def test_il_passo_dei_fotogrammi_e_costante():
    """L'altro flag che, tolto, accorcerebbe i filmati montati da più scene.

    Una GIF ha fotogrammi a durata variabile; il `.mp4` che ne nasce eredita timestamp
    fuori ordine, e il montaggio che incolla senza ricodificare scarta ciò che non sa
    incastrare. Il passo costante toglie la causa invece di inseguire l'effetto.
    """
    testo = STRUMENTO.read_text()
    assert "-fps_mode cfr" in testo, (
        "senza passo costante il montaggio perde secondi, e il filmato mente sulla durata"
    )


def test_il_filmato_si_confronta_con_le_scene_che_lo_compongono():
    """Non basta produrre: bisogna dichiarare che quello che è uscito è quello giusto."""
    testo = STRUMENTO.read_text()
    assert "attesi" in testo, "lo strumento non dichiara la durata attesa"


def test_un_nome_sconosciuto_si_rifiuta_invece_di_tacere():
    esito = esegui("filmato-che-non-esiste")
    assert esito.returncode != 0
    assert "filmato-che-non-esiste" in esito.stdout + esito.stderr


def test_senza_agg_lo_dice_e_non_prova_a_girare():
    """Il prerequisito nuovo si annuncia da sé, con il comando per rimediare."""
    esito = esegui("01-failover-docker-kill-muto", AGG="agg-che-non-esiste")
    assert esito.returncode != 0
    messaggio = esito.stdout + esito.stderr
    assert "agg" in messaggio
    assert "brew install agg" in messaggio, (
        "l'errore non dice come rimediare: chi lo legge deve poter risolvere leggendo"
    )


def test_la_cartella_e_la_stessa_che_conta_il_preflight():
    """La coerenza che, rotta, farebbe dire «nessun filmato» a cartella piena."""
    assert CARTELLA_PREDEFINITA in STRUMENTO.read_text()
    assert CARTELLA_PREDEFINITA in PREFLIGHT.read_text()
    assert "DEMO_VIDEOS_DIR" in STRUMENTO.read_text()


def test_il_makefile_espone_il_bersaglio():
    testo = MAKEFILE.read_text()
    assert "filmati-da-registrazioni" in testo
    assert "filmati:" in testo, "manca il bersaglio `filmati` in Makefile"


def test_la_pagina_delle_registrazioni_dichiara_la_dipendenza_nuova():
    """`agg` è la seconda installazione che il repository chiede: va scritto dove si cerca."""
    testo = PAGINA_REGISTRAZIONI.read_text()
    assert "brew install agg" in testo
    assert "make filmati" in testo


def test_la_pagina_non_promette_piu_una_sola_installazione():
    """La frase che era vera fino a `agg`, e che dopo `agg` sarebbe una bugia."""
    testo = PAGINA_REGISTRAZIONI.read_text()
    assert "l'unica installazione che questo repository chiede" not in testo


@pytest.mark.parametrize(
    "filmato,scene",
    [
        ("02-failover-i-due-gesti-muto", 2),
        ("05-guasto-shard-nei-due-profili-muto", 2),
        ("06-blocco-3-per-intero-muto", 3),
    ],
)
def test_i_montaggi_uniscono_piu_scene(filmato: str, scene: int):
    """I tre filmati il cui senso è il confronto, non la scena singola."""
    voci = catalogo()
    assert filmato in voci, f"manca {filmato}"
    assert len(voci[filmato]) == scene


def test_le_scene_lunghe_restano_lunghe():
    """Il conto che le prove possono fare senza produrre: quanto deve durare ognuno.

    Non misura un file — non ne esiste uno, in una suite — ma fissa l'ordine di
    grandezza che lo strumento dovrà dichiarare. Se un giorno il catalogo si riordinasse,
    questa prova direbbe che il filmato 05 non dura più quanto le sue due scene.
    """
    voci = catalogo()
    atteso = sum(durata_cast(scena) for scena in voci["05-guasto-shard-nei-due-profili-muto"])
    assert atteso > 50, f"il guasto shard nei due profili dovrebbe superare i 50 s, non {atteso:.1f}"
