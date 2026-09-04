"""Lo strumento di backup che avanza — e, se la prova lo chiede, si rompe a metà."""

from pathlib import Path
from typing import Iterator, Sequence

from mongolab.domain.modelli import Progress

__all__ = ["FakeBackup"]


class FakeBackup:
    """Un `BackupTool` la cui cronaca di avanzamento la decide la prova.

    **Il caso che serve davvero è quello che fallisce a metà.** Un dump che si rompe alla
    prima riga si gestisce con un `try` attorno alla chiamata; uno che si rompe dopo due
    collezioni lascia avanzamento già mostrato a schermo e file già scritti, e la domanda
    interessante — che cosa la TUI racconta di ciò che era andato bene — esiste solo in
    quel caso. Si prepara con `errore`, che viene sollevato **dopo** aver prodotto tutti
    gli avanzamenti dati.

    **`dump` non è una funzione generatrice, ed è deliberato.** Se lo fosse, chiamarla non
    eseguirebbe niente: il corpo partirebbe al primo `next()`, e con lui la registrazione
    della richiesta — nell'adattatore vero del Task 9, l'avvio di `mongodump`. La porta
    dice «avvia il dump e produce l'avanzamento **mentre** procede», cioè promette che
    qualcosa accade alla chiamata. Qui la richiesta si registra subito e gli avanzamenti
    arrivano scorrendo, che è la stessa forma che l'adattatore vero dovrà avere.

    **Una sola sequenza per `dump` e `restore`**, e i contenuti li decide chi costruisce
    il doppio: una prova che ha bisogno di due cronache diverse costruisce due doppi. Ogni
    chiamata riparte dall'inizio della sequenza, perché due dump di seguito sono due dump
    e non uno spezzato in due.
    """

    def __init__(
        self,
        avanzamenti: Sequence[Progress] = (),
        errore: Exception | None = None,
    ) -> None:
        self._avanzamenti = tuple(avanzamenti)
        self._errore = errore
        self.dump_chiesti: list[Path] = []
        """Le destinazioni per cui è stato chiesto un dump, in ordine."""
        self.tetti_chiesti: list[float | None] = []
        """I tetti chiesti, in ordine e in parallelo a `dump_chiesti`.

        **Registrato e non onorato**, ed è deliberato. Il tetto è una promessa sul
        processo: un doppio che lo facesse scadere dovrebbe fingere un cronometro e un
        figlio da abbattere, cioè rifare in finto la parte che è tutta la difficoltà
        dell'adattatore vero — e una prova che passasse contro quella finzione non direbbe
        niente di `mongodump`. Che il tetto **arrivi** è quanto le scene possono verificare
        di qua dalla porta; che valga è misurato in `test_backup.py`, con un processo vero
        che non finisce.
        """
        self.restore_chiesti: list[tuple[Path, str]] = []
        """Le coppie origine e database di destinazione per cui è stato chiesto un restore."""

    def dump(
        self, destinazione: Path, *, tetto_s: float | None = None
    ) -> Iterator[Progress]:
        self.dump_chiesti.append(destinazione)
        self.tetti_chiesti.append(tetto_s)
        return self._cronaca()

    def restore(self, origine: Path, destinazione_db: str) -> Iterator[Progress]:
        self.restore_chiesti.append((origine, destinazione_db))
        return self._cronaca()

    def _cronaca(self) -> Iterator[Progress]:
        yield from self._avanzamenti
        if self._errore is not None:
            raise self._errore
