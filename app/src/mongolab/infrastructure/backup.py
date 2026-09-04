"""`SubprocessBackup`: la porta `BackupTool` attaccata a `mongodump` e `mongorestore`.

Un adattatore verso un **processo**, non verso una libreria, e le differenze rispetto a
`PymongoStore` vengono tutte da lì: la credenziale attraversa un confine di sistema
operativo invece che una chiamata di funzione, l'avanzamento è testo da leggere invece che
un valore di ritorno, e il verdetto è un numero intero che lo strumento decide da solo.

## Riceve il comando, non decide come raggiungerlo

`comando_dump` e `comando_restore` arrivano dal costruttore, ed è la stessa scelta che in
`PymongoStore` fa arrivare una `Collection` già fatta: **questo oggetto non ha una politica
di esecuzione**. Dall'host, dove `mongodump` non è installato, il comando è
`("docker", "exec", "-i", "mongo-rs-1", "mongodump")`. Se la politica stesse qui,
l'applicazione containerizzata di
[ADR-0012](../../../../docs/Decision.md#adr-0012) si porterebbe dietro una dipendenza dal
socket Docker per fare una cosa — un dump — che dal suo container potrebbe fare da sé.

La prima stesura di queste righe prevedeva che «dall'interno della rete Compose al Task 12
sarà `("mongodump",)` e basta». Il Task 12 è passato e quella previsione **non è stata
onorata**: l'immagine dell'applicazione contiene l'interprete e `mongolab`, non gli
strumenti da riga di comando di MongoDB ([M-039](../../../../app/docs/Sources.md#m-039)).
Oggi non fa danno, perché nessun comando della CLI collega questa porta; la scelta fra
installarli e restare su `docker exec` è del Task 14, che è dove la scena del backup entra
in scaletta. Che l'oggetto riceva il comando invece di sceglierlo è ciò che permette di
decidere allora, e non adesso.

Il `-i` in quel prefisso non è decorativo: senza, `docker exec` non collega lo `stdin` del
client al processo dentro il container, e la password non arriva a destinazione.

## La password su `stdin`, non fra gli argomenti

Il piano del Task 9 chiedeva la lista di argomenti al posto della stringa di shell perché
«una stringa di shell la fa comparire nella tabella dei processi». La misura dice che la
lista **non basta**: con `-p <valore>` come elemento di `argv`, dentro il container
`ps -eo args` mostra il segreto per intero ([M-025](../../../../app/docs/Sources.md#m-025)).
La tabella dei processi legge `argv`, e a `argv` non importa da dove è arrivato.

Quello che funziona è omettere `-p`. Gli strumenti allora chiedono la password e la
**leggono da `stdin` anche quando `stdin` non è un terminale**: la si scrive, si chiude il
tubo, e il segreto non compare in nessun `argv` di nessun processo
([M-023](../../../../app/docs/Sources.md#m-023)). La lista resta comunque giusta, per la
ragione che il piano non nomina: senza shell non c'è nessuno a interpretare uno spazio, un
apice o un `$` dentro una password o dentro un percorso.

## Tutto quello che dicono lo dicono su `stderr`

Misurato: `stdout` resta **vuoto**, zero righe, per entrambi gli strumenti. Qui `stdout` va
a `DEVNULL` apposta — un tubo che nessuno svuota si riempie, e un processo che scrive in un
tubo pieno si ferma per sempre. Buttarlo via è l'unica scelta che non può bloccarsi, e non
si perde niente perché non ci passa niente.

## Il verdetto, e il caso in cui lo strumento non lo dà

Un'uscita diversa da zero diventa `ComandoFallito`, con il codice e il messaggio, e non un
iteratore che finisce in silenzio: è [ADR-0077](../../../../docs/Decision.md#adr-0077).

Ma `mongorestore` ha perso cinquantamila documenti ed è **uscito zero**, dicendolo solo in
una riga di sommario ([M-024](../../../../app/docs/Sources.md#m-024)). Il codice d'uscita,
lì, è l'avviso che nessuno legge. Quando quella riga conta dei falliti, questo adattatore
solleva `RestoreIncompleto` e mette il verdetto che lo strumento non ha messo
([ADR-0084](../../../../docs/Decision.md#adr-0084)).
"""

import re
import subprocess
from pathlib import Path
from typing import Iterator, Sequence

from mongolab.domain.modelli import Progress

__all__ = [
    "ComandoFallito",
    "RestoreIncompleto",
    "SubprocessBackup",
    "leggi_avanzamento",
]


class ComandoFallito(RuntimeError):
    """Il processo esterno è uscito diverso da zero.

    Porta il codice e il messaggio separati oltre che nel testo: chi cattura può decidere
    guardando il numero, che è l'unica parte stabile fra due versioni degli strumenti.

    **Non contiene la riga di comando.** Sarebbe comoda in un traceback e sarebbe uno
    sbaglio: qui la password non passa da `argv`, ma nulla impedirebbe a un domani
    distratto di rimettercela, e un'eccezione che stampa `argv` la porterebbe dritta in una
    slide.
    """

    def __init__(self, eseguibile: str, codice: int, messaggio: str) -> None:
        coda = f": {messaggio}" if messaggio else ""
        super().__init__(f"{eseguibile} è uscito con codice {codice}{coda}")
        self.eseguibile = eseguibile
        self.codice = codice
        self.messaggio = messaggio


class RestoreIncompleto(RuntimeError):
    """Il restore è uscito zero e ha detto, di sfuggita, di aver perso dei documenti."""

    def __init__(self, eseguibile: str, restaurati: int, falliti: int) -> None:
        super().__init__(
            f"{eseguibile} è uscito con codice 0 dopo aver ripristinato {restaurati} "
            f"documenti e averne persi {falliti}: il conteggio è il verdetto, non l'uscita"
        )
        self.eseguibile = eseguibile
        self.restaurati = restaurati
        self.falliti = falliti


_ORARIO = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+[+-]\d{4}\t")
"""Il prefisso `2026-09-03T12:08:29.809+0000\\t` che apre quasi ogni riga.

*Quasi*: `Enter password for mongo user:` arriva senza, perché non è un messaggio di log ma
il prompt scritto sul terminale che non c'è.
"""

_MISURA = r"(\d+(?:\.\d+)?)((?:[KMGT]i?)?B)?"
"""Un numero della barra: `1863086` per `mongodump`, `46.5MB` per `mongorestore`."""

_MOLTIPLICATORE = {
    None: 1,
    "B": 1,
    "KB": 1024,
    "MB": 1024**2,
    "GB": 1024**3,
    "TB": 1024**4,
}
"""Base **1024**, misurata e non dedotta dal nome dell'unità.

Un `.bson` di 48 760 014 byte è stato annunciato come `46.5MB`: in base 1000 farebbe
46 500 000 (scarto 4,6%), in base 1024 fa 48 758 784 (scarto 0,003%, che è il prezzo
dell'arrotondamento a una cifra decimale). Vedi [M-026](../../../../app/docs/Sources.md#m-026).
"""

_BARRA = re.compile(rf"^\[[#.]*\]\s+(\S+)\s+{_MISURA}/{_MISURA}\s+\([\d.]+%\)$")
_APERTURA = re.compile(r"^writing `([^`]+)` to `")
_OPLOG_APERTURA = re.compile(r"^writing captured oplog to")
_CHIUSURA = re.compile(r"^done dumping `([^`]+)` \((\d+) documents?\)$")
_OPLOG_CHIUSURA = re.compile(r"^dumped (\d+) oplog entr(?:y|ies)$")
_RESTORE_CHIUSURA = re.compile(
    r"^finished restoring `([^`]+)` \((\d+) documents?, (\d+) failures?\)$"
)
_SOMMARIO = re.compile(
    r"^(\d+) document\(s\) restored successfully\. (\d+) document\(s\) failed to restore\.$"
)
_FALLIMENTO = re.compile(r"^Failed: (.*)$")


def _senza_orario(riga: str) -> str:
    """Toglie il timestamp e i rientri: `\\t\\tdumped 1 oplog entry` ha due tabulazioni."""
    return _ORARIO.sub("", riga).strip()


def _quantita(numero: str, unita: str | None) -> int:
    return round(float(numero) * _MOLTIPLICATORE[unita])


def leggi_avanzamento(riga: str) -> Progress | None:
    """Una riga di `stderr` diventa un `Progress`, oppure `None` se non è avanzamento.

    `fase` porta **su che cosa lo strumento sta lavorando** — il namespace `db.collezione`,
    o `oplog` — e non il nome dell'operazione. Chi consuma ha appena chiamato `dump` o
    `restore` e quindi sa già quale delle due è; quello che non saprebbe, senza questo
    campo, è a quale collezione appartiene la barra che sta guardando, che è l'unica cosa
    di cui ha bisogno per non disegnarne due sovrapposte.

    Resta una scomodità dichiarata: `Progress` non ha un campo per l'unità di misura, e
    `completati` conta **documenti** durante un dump e **byte** durante un restore. Chi
    chiama sa quale ha chiesto, quindi l'ambiguità non arriva mai a schermo; ma una
    funzione che ricevesse un `Progress` senza sapere da dove viene non potrebbe scrivergli
    accanto l'unità giusta.

    Ciò che non è avanzamento resta `None` di proposito, e la riga che conta di più è
    `Enter password for mongo user:`. Diventasse un `Progress`, la TUI mostrerebbe in scena
    una richiesta di password a cui nessuno può rispondere.
    """
    testo = _senza_orario(riga)
    if not testo:
        return None

    barra = _BARRA.match(testo)
    if barra is not None:
        fase, fatti, unita_fatti, totali, unita_totali = barra.groups()
        return Progress(
            fase=fase,
            completati=_quantita(fatti, unita_fatti),
            totali=_quantita(totali, unita_totali),
            messaggio=testo,
        )

    if _OPLOG_APERTURA.match(testo) is not None:
        return Progress(fase="oplog", completati=0, totali=None, messaggio=testo)

    apertura = _APERTURA.match(testo)
    if apertura is not None:
        return Progress(
            fase=apertura.group(1), completati=0, totali=None, messaggio=testo
        )

    chiusura = _CHIUSURA.match(testo) or _RESTORE_CHIUSURA.match(testo)
    if chiusura is not None:
        quanti = int(chiusura.group(2))
        return Progress(
            fase=chiusura.group(1), completati=quanti, totali=quanti, messaggio=testo
        )

    oplog = _OPLOG_CHIUSURA.match(testo)
    if oplog is not None:
        quante = int(oplog.group(1))
        return Progress(
            fase="oplog", completati=quante, totali=quante, messaggio=testo
        )

    return None


class SubprocessBackup:
    """Un `BackupTool` che lancia `mongodump` e `mongorestore` e ne legge l'avanzamento.

    Non eredita dalla porta e non la importa: la conformità è strutturale e a verificarla è
    `mypy --strict`, come per `PymongoStore` e per i doppi.
    """

    __slots__ = (
        "_comando_dump",
        "_comando_restore",
        "_database",
        "_database_autenticazione",
        "_dove",
        "_host",
        "_opzioni_dump",
        "_opzioni_restore",
        "_password",
        "_utente",
    )

    def __init__(
        self,
        host: str,
        *,
        comando_dump: Sequence[str] = ("mongodump",),
        comando_restore: Sequence[str] = ("mongorestore",),
        utente: str | None = None,
        password: str | None = None,
        database_autenticazione: str = "admin",
        database: str = "lab",
        opzioni_dump: Sequence[str] = (),
        opzioni_restore: Sequence[str] = (),
        dove: Path | None = None,
    ) -> None:
        """`database` è quello su cui il laboratorio lavora, e serve al `restore`.

        La porta dà a `restore` la directory di origine e il nome della destinazione, non
        quello dell'origine — che però è dentro il container e non si può guardare da qui.
        Arriva quindi dal costruttore, dove sta accanto all'host di cui è il database.

        `dove` è la directory da cui il comando parte, ed è lo stesso parametro che
        `RegiaCompose` ha per la stessa ragione: quando il comando è `docker compose -f
        docker/02-replicaset/compose.yaml exec ...`, quel percorso è **relativo alla radice
        del repository**, e chi lancia `mongolab` non parte per forza di lì. `None` — il
        predefinito — vuol dire la directory di chi chiama, che è la cosa giusta quando il
        comando è `mongodump` e basta.
        """
        self._host = host
        self._comando_dump = tuple(comando_dump)
        self._comando_restore = tuple(comando_restore)
        self._utente = utente
        self._password = password
        self._database_autenticazione = database_autenticazione
        self._database = database
        self._opzioni_dump = tuple(opzioni_dump)
        self._opzioni_restore = tuple(opzioni_restore)
        self._dove = dove

    def argomenti_dump(self, destinazione: Path) -> tuple[str, ...]:
        """La riga esatta del dump, e si può stampare.

        Si può perché la password non ci passa: viaggia su `stdin`
        ([ADR-0054](../../../../docs/Decision.md#adr-0054),
        [M-025](../../../../app/docs/Sources.md#m-025)), e ciò che resta qui è
        `mongodump --host rs0/... --readPreference=secondary --oplog` — cioè esattamente
        la riga che il Blocco 2 sta spiegando mentre la scena gira.

        È la **stessa** tupla che `dump` esegue, non una sua ricostruzione: due
        costruzioni distinte vorrebbero dire poter mostrare una riga ed eseguirne
        un'altra, e una demo che si fa verificare su un comando diverso da quello che ha
        dato non dimostra niente.
        """
        return (
            *self._comando_dump,
            "--host",
            self._host,
            "--out",
            str(destinazione),
            *self._autenticazione(),
            *self._opzioni_dump,
        )

    def dump(self, destinazione: Path) -> Iterator[Progress]:
        """Avvia `mongodump` **adesso** e restituisce l'avanzamento da scorrere."""
        argomenti = self.argomenti_dump(destinazione)
        return self._avanzamento(self._avvia(argomenti), self._comando_dump[-1])

    def restore(self, origine: Path, destinazione_db: str) -> Iterator[Progress]:
        """Ripristina in un database **diverso**, e per farlo servono tre opzioni.

        `--nsFrom/--nsTo` rinominano ciò che corrispondono e **lasciano passare tutto il
        resto**: un restore dell'intera directory con solo quelle due ha rimesso a posto
        anche `lab` sopra sé stessa — cinquantamila chiavi duplicate — e ha toccato gli
        utenti in `admin/system.users.bson`
        ([M-024](../../../../app/docs/Sources.md#m-024)). `--nsInclude` è la terza, quella
        che filtra, e senza di lei le altre due sono una trappola.

        Manca `--oplogReplay`, e non per dimenticanza: `cannot use --oplogReplay with
        namespace renames specified`, uscita 1. Un dump preso con `--oplog` si può
        ripristinare **coerente al suo istante** solo sopra il proprio nome; ripristinarlo
        accanto, per confrontare i conteggi senza perdere l'originale, costa la coda
        dell'oplog. È il compromesso che il copione sceglie, e va detto in scena.
        """
        argomenti = self.argomenti_restore(origine, destinazione_db)
        return self._avanzamento(self._avvia(argomenti), self._comando_restore[-1])

    def argomenti_restore(self, origine: Path, destinazione_db: str) -> tuple[str, ...]:
        """La riga esatta del restore, come sopra e per le stesse ragioni."""
        return (
            *self._comando_restore,
            "--host",
            self._host,
            *self._autenticazione(),
            "--nsInclude",
            f"{self._database}.*",
            "--nsFrom",
            f"{self._database}.*",
            "--nsTo",
            f"{destinazione_db}.*",
            *self._opzioni_restore,
            str(origine),
        )

    def _autenticazione(self) -> tuple[str, ...]:
        """Utente e database di autenticazione, e **mai** la password."""
        if self._utente is None:
            return ()
        return (
            "--username",
            self._utente,
            "--authenticationDatabase",
            self._database_autenticazione,
        )

    def _avvia(self, argomenti: Sequence[str]) -> "subprocess.Popen[str]":
        """Lancia il processo e gli passa la password, se c'è, chiudendo poi lo `stdin`.

        La chiusura non è una cortesia: gli strumenti leggono la password fino alla fine
        del flusso, e uno `stdin` lasciato aperto li terrebbe in attesa di una riga che non
        arriva mai. Senza credenziale si chiude subito e basta — lo stack 01 non ha
        autenticazione, e uno strumento che aspettasse una password lì si pianterebbe.
        """
        processo = subprocess.Popen(
            list(argomenti),
            cwd=self._dove,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert processo.stdin is not None
        if self._password is not None:
            processo.stdin.write(self._password + "\n")
            processo.stdin.flush()
        processo.stdin.close()
        return processo

    def _avanzamento(
        self, processo: "subprocess.Popen[str]", eseguibile: str
    ) -> Iterator[Progress]:
        """Legge `stderr` riga per riga, produce ciò che è avanzamento, e poi giudica.

        **Chiudere l'iteratore ferma il processo.** Se l'avanzamento si consuma man mano
        allora esiste un consumatore che può smettere — una schermata chiusa, un Ctrl-C — e
        senza questo `except` resterebbe un `mongodump` a girare contro il cluster senza
        più nessuno che lo guardi. Il limite: quando il comando è `docker exec ...`, ciò che
        muore qui è il client `docker`, e lo strumento dentro il container tira dritto.
        """
        assert processo.stderr is not None
        motivo = ""
        sommario: tuple[int, int] | None = None
        try:
            for riga in processo.stderr:
                testo = _senza_orario(riga.rstrip("\n"))
                fallimento = _FALLIMENTO.match(testo)
                if fallimento is not None:
                    motivo = fallimento.group(1)
                conti = _SOMMARIO.match(testo)
                if conti is not None:
                    sommario = (int(conti.group(1)), int(conti.group(2)))
                avanzamento = leggi_avanzamento(testo)
                if avanzamento is not None:
                    yield avanzamento
        except GeneratorExit:
            processo.kill()
            processo.wait()
            raise
        finally:
            processo.stderr.close()

        codice = processo.wait()
        if codice != 0:
            raise ComandoFallito(eseguibile, codice, motivo)
        if sommario is not None and sommario[1] > 0:
            raise RestoreIncompleto(eseguibile, sommario[0], sommario[1])
