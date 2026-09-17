"""Le due regie: quella che comanda `docker compose`, e quella che annuncia e aspetta.

**Perché sono due, e non una con un'opzione.** Sono due perché il problema è strutturale,
non di gusto. La cronaca dell'elezione — quella con i timestamp al millisecondo, che è il
cuore del Blocco 2 — esiste solo se il driver riesce a **scoprire la topologia**, e la
scoperta funziona soltanto da dentro la rete Compose: dall'host i nomi che il replica set
si dà, `mongo-rs-1:27017` e compagni, non si risolvono
([M-019](../../../docs/Sources.md#m-019), e il rimedio è nel §7 del design: applicazione
dentro la rete Docker). Ma fermare un container richiede il socket del demone, che il
container dell'applicazione **non ha** — e il Task 9 ha deciso di non montarglielo.

Un solo processo non può fare tutte e due le cose. Quindi: `RegiaCompose` per chi gira
sull'host, `RegiaAnnunciata` per chi gira dentro la rete e chiede a un umano di dare il
comando in un'altra finestra. Lo scenario è lo stesso, e non sa quale delle due ha in
mano: è tutto il guadagno della porta `Regia`, e la ragione per cui è nata.

**Il frasario è separato dall'esecuzione** per la stessa ragione: `RegiaAnnunciata` deve
poter **stampare** la riga esatta che `RegiaCompose` eseguirebbe. Se ciascuna se la
costruisse per conto suo, la riga annunciata e la riga eseguita divergerebbero al primo
ritocco, e chi copia dallo schermo darebbe un comando diverso da quello provato.
"""

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Callable, Final, Mapping

from mongolab.infrastructure.backup import ComandoFallito

__all__ = [
    "ARRESTO_BRUSCO",
    "ARRESTO_ORDINATO",
    "ComandiCompose",
    "RegiaAnnunciata",
    "RegiaCompose",
    "SCADENZA_PREDEFINITA_S",
]


ARRESTO_BRUSCO: Final = ("kill", "-s", "SIGKILL")
"""Come si ferma il primario quando la scena deve mostrare un'elezione vera.

Il processo sparisce senza cedere il ruolo, il replica set deve accorgersene e votare, e
il nuovo primario arriva dopo 9 812, 10 619, 10 943 ms — i tre valori che
[V-029](../../../docs/Sources.md#v-029) ha misurato e che
[V-031](../../../docs/Sources.md#v-031) ha portato sulle slide come «forbice 8-10 s».
"""

ARRESTO_ORDINATO: Final = ("stop",)
"""L'altra strada, che è un'altra scena: `SIGTERM`, e `mongod` cede il ruolo prima di
uscire. V-029 la misura in 574, 480, 486 ms — venti volte più veloce, e senza elezione da
raccontare. Resta qui perché è il confronto che rende leggibile il numero grande.
"""

SCADENZA_PREDEFINITA_S: Final = 30.0
"""Quanto si aspetta `docker compose` prima di dichiararlo piantato.

Un comando che non torna è peggio di un comando che fallisce: la scena si ferma con lo
schermo pieno e nessuna spiegazione, in sala, davanti a tutti. Trenta secondi sono molto
più di quanto serva a `kill` e abbastanza per uno `start` su una macchina carica.
"""

_VERBI: Final[Mapping[str, tuple[str, ...]]] = {
    "riavvia": ("start",),
    "sospendi": ("pause",),
    "risveglia": ("unpause",),
}
"""I tre verbi che non dipendono da come si è scelto di arrestare. `ferma` manca apposta:
la sua riga arriva da `ComandiCompose.arresto`, che è configurabile."""


@dataclass(frozen=True, slots=True)
class ComandiCompose:
    """Il frasario: quale riga di `docker compose` corrisponde a ciascun verbo.

    Congelato perché è ciò che le due regie **condividono**, e una condivisione mutabile
    fra chi annuncia e chi esegue sarebbe il modo più silenzioso di far divergere le due.

    `nodo` è il nome del servizio Compose così com'è scritto nel `compose.yaml` —
    `mongo-rs-1` — e non il nome del container, che Compose costruisce da sé aggiungendo
    il progetto e un ordinale. Chi comanda i servizi non deve sapere come Compose li
    battezza.
    """

    file_compose: Path
    comando: tuple[str, ...] = ("docker", "compose")
    ambiente: tuple[Path, ...] = ()
    """I `--env-file`, nell'ordine in cui il Makefile li passa. Senza, non si parte.

    Non è una comodità: i `compose.yaml` di questo repository interpolano con la forma
    `${MONGO_IMAGE:?...}`, che è un **errore** e non un valore vuoto. `docker compose -f
    docker/02-replicaset/compose.yaml ps` dalla radice risponde sette volte «required
    variable ... is missing a value» e non arriva nemmeno a guardare i container; con il
    solo `tools/images.env` ne restano due, per `PASSWORD_AMMINISTRATORE`.

    Viaggia il **percorso**, mai il contenuto: è ciò che rende la riga di
    `RegiaAnnunciata` innocua da mostrare a schermo e da registrare (ADR-0054).
    """
    progetto: str | None = None
    arresto: tuple[str, ...] = ARRESTO_BRUSCO

    def _preambolo(self) -> tuple[str, ...]:
        """Tutto ciò che viene prima del sottocomando, e che ogni riga ha uguale.

        Le opzioni globali del client stanno qui in un posto solo perché il giorno in cui
        se ne aggiunge una — un terzo `--env-file`, un `--profile` — deve comparire tanto
        in `per` quanto in `dentro`, senza che nessuno debba ricordarsene.
        """
        ambiente = tuple(
            pezzo for file in self.ambiente for pezzo in ("--env-file", str(file))
        )
        progetto = ("-p", self.progetto) if self.progetto is not None else ()
        return (*self.comando, *ambiente, *progetto, "-f", str(self.file_compose))

    def per(self, verbo: str, nodo: str) -> tuple[str, ...]:
        """La riga completa per un verbo. `KeyError` su un verbo che non esiste."""
        coda = self.arresto if verbo == "ferma" else _VERBI[verbo]
        return (*self._preambolo(), *coda, nodo)

    def dentro(self, nodo: str, *comando: str) -> tuple[str, ...]:
        """La riga che esegue un comando **dentro** un nodo del cluster.

        Serve perché `mongodump` e `mongorestore` non stanno nell'immagine
        dell'applicazione e non ci staranno: copiare i due binari da `MONGO_IMAGE` dentro
        `python:3.13-slim` produce un container che si ferma su
        `libgssapi_krb5.so.2: cannot open shared object file`
        ([M-044](../../../docs/Sources.md#m-044)). Stanno già in ogni nodo del replica set,
        e questa è la riga per andarci.

        `-T` invece di `-i`: nessun terminale allocato — Compose ne aprirebbe uno che in
        una scena non interattiva non serve — ma lo stdin resta collegato, che è dove passa
        la password senza comparire in `argv` (M-025, ADR-0054).

        Il nodo è un **servizio** Compose, non un container: chi comanda non deve sapere
        con quale ordinale Compose l'ha battezzato, ed è la stessa promessa di `per`.
        """
        if not comando:
            raise ValueError(
                f"entrare in {nodo} senza dire che cosa farci non è un comando: "
                "`exec -T` da solo aprirebbe l'entrypoint del container e resterebbe lì."
            )
        return (*self._preambolo(), "exec", "-T", nodo, *comando)

    def riga(self, verbo: str, nodo: str) -> str:
        """La stessa riga, da leggere e da copiare. È ciò che `RegiaAnnunciata` stampa."""
        return " ".join(self.per(verbo, nodo))


class RegiaCompose:
    """Una `Regia` che esegue `docker compose`. Vive sull'host, dove il socket c'è.

    Non eredita dalla porta e non la importa: la conformità è strutturale, e a verificarla
    è `mypy --strict` — come per `PymongoStore`, `SubprocessBackup` e i doppi.

    `dove` è la directory da cui il comando parte, e serve perché il frasario porta
    percorsi **relativi alla radice del repository**: `docker/02-replicaset/compose.yaml`
    e non `/Users/.../docker/02-replicaset/compose.yaml`. Relativi perché la stessa riga
    deve poter essere **annunciata** da `RegiaAnnunciata` e incollata a mano — e i
    percorsi assoluti che l'applicazione vede da dentro il container non esistono
    sull'host. Chi esegue sa dove sta la radice; chi annuncia lo dice a parole.

    Un'uscita diversa da zero diventa `ComandoFallito` e **ferma la scena**. È la
    decisione più importante di questa classe: un `stop` fallito lascerebbe il primario in
    piedi, e i due numeri finali sarebbero zero millisecondi di interruzione e zero
    scritture perse — cioè un failover perfetto. La sala vedrebbe la slide sbagliata senza
    che nessuno abbia modo di accorgersene.
    """

    __slots__ = ("_comandi", "_dove", "_scadenza_s")

    def __init__(
        self,
        comandi: ComandiCompose,
        *,
        dove: Path | None = None,
        scadenza_s: float = SCADENZA_PREDEFINITA_S,
    ) -> None:
        self._comandi = comandi
        self._dove = dove
        self._scadenza_s = scadenza_s

    def ferma(self, nodo: str) -> None:
        self._esegui("ferma", nodo)

    def riavvia(self, nodo: str) -> None:
        self._esegui("riavvia", nodo)

    def sospendi(self, nodo: str) -> None:
        self._esegui("sospendi", nodo)

    def risveglia(self, nodo: str) -> None:
        self._esegui("risveglia", nodo)

    def _esegui(self, verbo: str, nodo: str) -> None:
        argomenti = self._comandi.per(verbo, nodo)
        esito = subprocess.run(
            argomenti,
            cwd=self._dove,
            capture_output=True,
            text=True,
            timeout=self._scadenza_s,
            check=False,
        )
        if esito.returncode != 0:
            raise ComandoFallito(
                argomenti[0], esito.returncode, esito.stderr.strip() or esito.stdout.strip()
            )


class RegiaAnnunciata:
    """Una `Regia` che non comanda: dice quale comando dare, e aspetta che sia stato dato.

    È la regia del container. Dentro la rete Compose l'applicazione vede la topologia — ed
    è l'unico posto da cui la vede — ma non ha il socket del demone e non può fermare
    nessuno. Fingere sarebbe la bugia peggiore possibile, perché produce esattamente i
    numeri di un failover riuscito senza il failover.

    Le due funzioni sono separate perché fanno due cose diverse in due momenti diversi:
    `annuncia` scrive, `conferma` **blocca**. La radice di composizione decide con che
    cosa: un `typer.echo` e un `input()` dal vivo, un logger e un `lambda` che ritorna
    subito quando la scena gira dentro una prova di integrazione.
    """

    __slots__ = ("_annuncia", "_comandi", "_conferma")

    def __init__(
        self,
        comandi: ComandiCompose,
        *,
        annuncia: Callable[[str], None],
        conferma: Callable[[str], None],
    ) -> None:
        self._comandi = comandi
        self._annuncia = annuncia
        self._conferma = conferma

    def ferma(self, nodo: str) -> None:
        self._chiedi("ferma", nodo)

    def riavvia(self, nodo: str) -> None:
        self._chiedi("riavvia", nodo)

    def sospendi(self, nodo: str) -> None:
        self._chiedi("sospendi", nodo)

    def risveglia(self, nodo: str) -> None:
        self._chiedi("risveglia", nodo)

    def _chiedi(self, verbo: str, nodo: str) -> None:
        riga = self._comandi.riga(verbo, nodo)
        self._annuncia(riga)
        self._conferma(riga)
