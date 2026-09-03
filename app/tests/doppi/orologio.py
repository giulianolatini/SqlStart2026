"""L'orologio che avanza solo quando glielo si chiede."""

from datetime import datetime, timedelta
import threading

__all__ = ["FakeClock", "OrologioCheScorre"]


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


class OrologioCheScorre:
    """Un `Clock` che avanza da solo, di un passo fisso a ogni lettura dell'ora.

    Esiste per una cosa sola che `FakeClock` non sa fare: provare un ciclo che si ferma
    **quando il tempo è scaduto**. Con un orologio immobile quel ciclo non finisce, e la
    prova non fallisce — si pianta, che è il modo peggiore in cui una suite può rompersi.

    Il passo è per lettura e non per secondo di CPU, e questo è il punto: il numero di
    giri che il codice sotto prova riesce a fare prima della scadenza diventa
    **deterministico**, perché è la scadenza divisa per il passo. Una prova che dicesse
    «in due secondi veri fa più di dieci giri» misurerebbe la macchina.

    `attese` c'è come in `FakeClock`, e per la stessa ragione: `sleep` è ciò che il codice
    chiede, e va potuto leggere separatamente dallo scorrere del tempo.
    """

    def __init__(self, istante: datetime, passo_s: float = 0.001) -> None:
        self._istante = istante
        self._passo = timedelta(seconds=passo_s)
        self._serratura = threading.Lock()
        self.attese: list[float] = []
        self.letture = 0
        """Quante volte è stata chiesta l'ora. È il conto dei giri, visto da qui."""

    def now(self) -> datetime:
        # Il lucchetto non è prudenza generica: questo doppio viene letto da tutti i
        # worker insieme, e senza di lui il numero di giri prima della scadenza
        # dipenderebbe da come si intrecciano i thread. Con lui, «quanti giri stanno in
        # una durata» è una divisione, e la prova può asserirla.
        with self._serratura:
            self.letture += 1
            adesso = self._istante
            self._istante += self._passo
            return adesso

    def sleep(self, secondi: float) -> None:
        with self._serratura:
            self.attese.append(secondi)
            self._istante += timedelta(seconds=secondi)
