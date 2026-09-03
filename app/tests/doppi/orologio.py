"""L'orologio che avanza solo quando glielo si chiede."""

from datetime import datetime, timedelta

__all__ = ["FakeClock"]


class FakeClock:
    """Un `Clock` in cui il tempo è una variabile, non una lettura.

    È il doppio che rende provabili le regole scritte in decine di secondi — «dopo 30 s
    senza primario, smetti di ritentare» — in una prova che dura un battito di ciglia.
    Senza, quella regola resterebbe una frase del design: nessuno mette in una suite
    veloce una prova che aspetta mezzo minuto, e una prova che nessuno esegue non
    protegge niente.

    Le due maniere di far passare il tempo sono tenute distinte apposta. `sleep` è ciò
    che il codice sotto prova **chiede**, e finisce in `attese`, che è dove si legge il
    backoff. `avanza` è ciò che accade **mentre** il codice lavora — una scrittura che ci
    mette 12 ms — e non lascia traccia lì: mescolarle vorrebbe dire che l'asserzione sul
    backoff vede attese che nessuno ha chiesto.

    Non eredita `Clock` e non lo importa: la conformità è strutturale, e il verso della
    dipendenza resta quello giusto anche nei doppi (`porte.py` spiega perché). A
    verificarla è `mypy --strict`, nel punto in cui una prova annota `orologio: Clock`.
    """

    def __init__(self, istante: datetime) -> None:
        self._istante = istante
        self.attese: list[float] = []
        """Le attese chieste, in ordine. È l'asserzione tipica sulle politiche di ritentativo."""

    def now(self) -> datetime:
        return self._istante

    def sleep(self, secondi: float) -> None:
        self.attese.append(secondi)
        self.avanza(secondi)

    def avanza(self, secondi: float) -> None:
        """Sposta l'orologio senza che nessuno abbia dormito."""
        self._istante += timedelta(seconds=secondi)
