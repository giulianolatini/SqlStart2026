"""Il rilevatore di log congelato di `failover-replicaset.sh`.

Serve perché il guasto che quel rilevatore intercetta è **silenzioso**: dopo un riavvio
del demone Docker i container tornano su da soli e mongod continua a scrivere, mentre
`docker logs` resta fermo all'istante in cui il demone è caduto (V-032). Senza il
controllo, la sezione «righe di log» della demo stampa il nulla e non dice perché.

Il guaio di un rilevatore così è che la sua condizione di scatto si presenta di rado:
può rompersi e nessuno se ne accorge fino alla sera in cui serve. Da qui questi casi,
costruiti sugli istanti veri misurati il 2026-09-01.

La funzione è in bash. Si estrae dallo script — non se ne tiene una copia, che
divergerebbe — e si esegue con `docker` sostituito da un finto che risponde con gli
istanti del caso in prova.
"""

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "failover-replicaset.sh"

# `docker inspect` risponde con l'istante di avvio, `docker logs --tail 1` con una riga
# di log finta ma della forma vera: JSON, con `t.$date`. Sono le sole due chiamate che
# `log_catturato_e_fresco` fa.
PREPARAZIONE = r"""
set -uo pipefail
eval "$(sed -n '/^log_catturato_e_fresco() {/,/^}/p' "$1")"
docker() {
  case "$1" in
    inspect) printf '%s\n' "${AVVIO}" ;;
    logs)    printf '{"t":{"$date":"%s"},"s":"I","c":"REPL","id":1,"msg":"finta"}\n' "${ULTIMA}" ;;
  esac
}
if log_catturato_e_fresco qualunque; then echo FRESCO; else echo VECCHIO; fi
"""

AVVIO_DI_STAMATTINA = "2026-09-01T08:05:55.098171001Z"


def freschezza(ultima: str, avvio: str) -> str:
    esito = subprocess.run(
        ["bash", "-c", PREPARAZIONE, "bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "ULTIMA": ultima, "AVVIO": avvio},
    )
    assert esito.returncode == 0, esito.stderr
    return esito.stdout.strip()


@pytest.mark.parametrize(
    "ultima, atteso, perche",
    [
        (
            "2026-08-31T19:19:50.378+00:00",
            "VECCHIO",
            "il caso vero: cattura ferma alla sera prima, container avviato stamattina",
        ),
        (
            "2026-09-01T08:22:32.630+00:00",
            "FRESCO",
            "la cattura è ripresa e le righe sono di questa esecuzione",
        ),
        (
            "2026-09-01T08:05:55.000+00:00",
            "VECCHIO",
            "stesso secondo dell'avvio: non si può dire di chi sia, e chiedere a mongod non costa",
        ),
        (
            "2026-09-01T08:05:54.999+00:00",
            "VECCHIO",
            "un millisecondo prima dell'avvio: non può essere di questa esecuzione",
        ),
    ],
)
def test_riconosce_un_log_catturato_che_non_e_di_questa_esecuzione(ultima, atteso, perche):
    assert freschezza(ultima, AVVIO_DI_STAMATTINA) == atteso, perche


def test_una_riga_non_json_vale_come_log_da_non_credere():
    """`docker logs` può finire con righe che non sono JSON. Il dubbio si risolve
    dalla parte innocua: si chiede a mongod, che risponde sempre bene."""
    esito = subprocess.run(
        [
            "bash",
            "-c",
            PREPARAZIONE.replace(
                r"""printf '{"t":{"$date":"%s"},"s":"I","c":"REPL","id":1,"msg":"finta"}\n' "${ULTIMA}" """,
                r"""printf 'non sono json\n' """,
            ),
            "bash",
            str(SCRIPT),
        ],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "ULTIMA": "", "AVVIO": AVVIO_DI_STAMATTINA},
    )
    assert esito.returncode == 0, esito.stderr
    assert esito.stdout.strip() == "VECCHIO"
