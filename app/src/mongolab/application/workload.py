"""Il generatore di carico: scrive, ritenta, misura.

`WorkloadRunner` non sa che esiste MongoDB. Parla con tre porte — `DocumentStore`,
`Clock`, `EventSink` — e questo non è purismo: è la ragione per cui l'intera politica dei
tentativi e l'intera aggregazione delle latenze sono provate in centesimi di secondo,
senza Docker, e sono provate **prima** che l'adattatore esista (Task 9).

**Che cosa produce.** Una corsa emette una cronaca di eventi e restituisce un
`Riepilogo`. Le due cose non sono ridondanti: la cronaca è ciò che la TUI mostra mentre
succede, il riepilogo è ciò che resta da leggere dopo — ed è il numero che finisce nelle
pagine di misura del repository.

**Perché i percentili e non la media.** La media di una latenza è il numero che nasconde
esattamente ciò che una demo di failover esiste per mostrare. Nove scritture da 1 ms e una
da 100 ms fanno una media di 10,9 ms: un valore che non è mai stato misurato e che non
descrive né il caso normale né quello brutto. La mediana dice il caso normale, il p95 dice
quanto è brutto il caso brutto, e in questa implementazione sono **entrambi valori
osservati** (vedi `percentile`).

**Concorrenza (§6.3).** I worker non toccano mai il sink: pubblicano su una
`queue.Queue` che il thread chiamante drena, e da lì escono le chiamate a `emit`. Il punto
di sincronizzazione è uno solo, ed è la stessa disciplina che ADR-0019 impone ai listener
di pymongo. Un `RecordingSink` in una prova conferma che i suoi chiamanti sono un thread
solo; nella demo lo stesso invariante protegge `Live` di Rich, che non è thread-safe.
"""

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
import math
import queue
from typing import Callable, Sequence

from mongolab.domain.eventi import (
    Evento,
    LatencySampled,
    RetryAttempted,
    WriteFailed,
    WriteSucceeded,
)
from mongolab.domain.modelli import Documento
from mongolab.domain.porte import Clock, DocumentStore, EventSink

__all__ = [
    "Genera",
    "Latenze",
    "PoliticaTentativi",
    "Riepilogo",
    "WorkloadRunner",
    "documento_progressivo",
    "percentile",
    "riassumi",
]

OPERAZIONE_SCRITTURA = "insert_many"
"""Il nome che finisce in `LatencySampled.operazione`.

È il nome del **metodo della porta**, non del comando MongoDB, e la differenza conta il
giorno in cui si campionerà anche la latenza delle letture: i due campioni vanno tenuti
separati, perché mescolare la latenza di una scrittura con quella di una `find` produce
un percentile che non descrive nessuna delle due.
"""

UN_MILLISECONDO = timedelta(milliseconds=1)

Genera = Callable[[int], Documento]
"""Da un indice progressivo a un documento.

È il gancio per `--doc-size`: la dimensione del documento è una faccenda di chi genera, e
tenerla fuori dal generatore di carico evita che `WorkloadRunner` debba sapere che cos'è
un kilobyte di BSON. L'indice è **globale** e distinto per ogni documento della corsa,
anche con più scrittori: è ciò che rende verificabile che nessun lavoro sia stato
duplicato o perso.
"""


def documento_progressivo(indice: int) -> Documento:
    """Il documento più piccolo che serva a qualcosa: solo il suo numero d'ordine."""
    return {"indice": indice}


@dataclass(frozen=True, slots=True)
class PoliticaTentativi:
    """Quante volte ritentare, e quanto aspettare fra un tentativo e l'altro.

    Attesa esponenziale con un tetto, e **senza jitter**. Il jitter è la scelta giusta
    quando molti client ritentano insieme contro lo stesso server, perché ne sfasa le
    ondate; qui sarebbe un danno per due ragioni. La prima è che renderebbe le prove
    non deterministiche proprio dove servono esatte. La seconda è che questa politica non
    è la difesa vera del client: quella è `retryWrites` del driver, e il §6.4 la mostra
    accesa e spenta. Questa esiste per **raccontare** i tentativi, cioè per rendere
    visibile in scena ciò che il driver di solito fa in silenzio.

    Le attese sono in millisecondi, come gli eventi che le riportano: è l'unico modo
    perché `attesa_ms=50.0` nel test, nell'evento e nella politica siano lo stesso 50,
    senza conversioni che introducono cifre in coda.
    """

    tentativi_massimi: int = 3
    """Tentativi in tutto, non ritentativi: 3 vuol dire una scrittura e due repliche."""

    attesa_iniziale_ms: float = 50.0
    fattore: float = 2.0
    attesa_massima_ms: float = 1000.0

    def attesa_ms(self, tentativo: int) -> float:
        """L'attesa **prima** del tentativo numero `tentativo`, che parte da 2.

        Il primo tentativo non aspetta, quindi la funzione non è definita per 1: il
        secondo tentativo aspetta l'attesa iniziale, il terzo il doppio, e così via fino
        al tetto.
        """
        if tentativo < 2:
            raise ValueError(f"il primo tentativo non attende, ricevuto {tentativo}")
        cresciuta = self.attesa_iniziale_ms * self.fattore ** (tentativo - 2)
        return min(cresciuta, self.attesa_massima_ms)


@dataclass(frozen=True, slots=True)
class Latenze:
    """Il campione di latenze, ridotto a sei numeri che si possono leggere a voce."""

    campioni: int
    minimo_ms: float
    mediana_ms: float
    p95_ms: float
    p99_ms: float
    massimo_ms: float


@dataclass(frozen=True, slots=True)
class Riepilogo:
    """Che cosa resta da leggere dopo una corsa.

    `latenze` è `None` — e non un oggetto pieno di zeri — quando nessuna scrittura è
    riuscita. Un p95 di zero millisecondi su una corsa in cui tutto è fallito è il numero
    più fuorviante che questa applicazione potrebbe stampare: direbbe «velocissimo» dove
    la verità è «mai arrivato». È la stessa regola dei doppi, applicata alle statistiche:
    dove non c'è una risposta giusta, si dichiara di non averla.
    """

    scritture: int
    riuscite: int
    fallite: int
    ritentate: int
    documenti_confermati: int
    latenze: Latenze | None


def percentile(campioni: Sequence[float], quantile: float) -> float:
    """Il percentile per **rango più vicino**: sempre un valore che è stato misurato.

    Con `n` campioni ordinati, il quantile `q` è il valore in posizione `ceil(q · n)`.
    Niente interpolazione fra i due valori adiacenti — che è ciò che fa
    `statistics.median` per i campioni di lunghezza pari, e che qui si evita apposta: un
    p95 di 37,5 ms su un campione in cui nessuno ha mai misurato 37,5 ms è un numero
    inventato dalla formula, e in una demo che esiste per mostrare misure vere non lo si
    vuole sulla slide. Il prezzo è che la mediana di `[10, 20]` è 10 e non 15; il
    guadagno è che ogni numero riportato si può ritrovare nel campione.

    Il rango si calcola in virgola mobile, e `ceil` amplificherebbe un errore di un ulp
    in un rango sbagliato di uno. Sull'interprete del progetto non succede: verificato
    contro l'aritmetica esatta di `Fraction` per i quantili 0,5 / 0,9 / 0,95 / 0,99 /
    0,999 su campioni da 1 a 200 000 elementi, zero divergenze — è M-008 in `Sources.md`.
    """
    if not campioni:
        raise ValueError(
            "il percentile di un campione vuoto non esiste, e non è zero: "
            "chi chiama deve distinguere «nessuna misura» da «misura bassa»."
        )
    if not 0.0 < quantile <= 1.0:
        raise ValueError(
            f"il quantile sta fra 0 escluso e 1 compreso, ricevuto {quantile!r}"
        )
    ordinati = sorted(campioni)
    rango = max(1, math.ceil(quantile * len(ordinati)))
    return ordinati[rango - 1]


def riassumi(campioni: Sequence[float]) -> Latenze:
    """I sei numeri, calcolati su una copia ordinata del campione.

    Ordina una volta e passa la sequenza già ordinata a `percentile`, che la riordina
    invano tre volte: è un `sorted` su una lista ordinata, cioè lineare, e non vale
    complicare la firma con un parametro «fidati, è ordinata» che un chiamante distratto
    userebbe a sproposito.
    """
    if not campioni:
        raise ValueError("non si riassume un campione vuoto: non ci sono latenze.")
    ordinati = sorted(campioni)
    return Latenze(
        campioni=len(ordinati),
        minimo_ms=ordinati[0],
        mediana_ms=percentile(ordinati, 0.5),
        p95_ms=percentile(ordinati, 0.95),
        p99_ms=percentile(ordinati, 0.99),
        massimo_ms=ordinati[-1],
    )


class WorkloadRunner:
    """Genera il carico di scritture, ritenta ciò che fallisce, racconta tutto.

    `scrittori` è il gancio del §6.3: è il numero di thread che scrivono insieme, ed è
    **il parametro che il Task 16 farà salire sopra `maxPoolSize`** per mostrare la
    saturazione del connection pool di pymongo. Qui la saturazione non si misura e non si
    può: contro `InMemoryStore` non c'è nessun pool da saturare, e una prova che
    pretendesse di mostrarla misurerebbe il doppio. Il piano lo dichiara materiale
    didattico e ne fissa la sede; questa riga è il gancio, non la misura.
    """

    def __init__(
        self,
        archivio: DocumentStore,
        orologio: Clock,
        sink: EventSink,
        *,
        politica: PoliticaTentativi = PoliticaTentativi(),
        scrittori: int = 1,
    ) -> None:
        if scrittori < 1:
            raise ValueError(f"serve almeno uno scrittore, ricevuto {scrittori}")
        self._archivio = archivio
        self._orologio = orologio
        self._sink = sink
        self._politica = politica
        self._scrittori = scrittori

    def esegui(
        self,
        scritture: int,
        *,
        per_scrittura: int = 1,
        genera: Genera = documento_progressivo,
    ) -> Riepilogo:
        """Esegue `scritture` inserimenti da `per_scrittura` documenti ciascuno.

        Il ciclo di drenaggio è il cuore del metodo, e la sua correttezza sta in un
        dettaglio: ogni worker, **qualunque cosa accada**, mette in coda un `None` come
        ultimo gesto. Il chiamante conta i `None` invece di interrogare i futuri o di
        attendere con un timeout, e così il ciclo termina anche se un worker muore per un
        errore che non riguarda le scritture. I timeout in un ciclo di consumo sono la
        via che porta a una prova che fallisce una volta su cento su una macchina carica.
        """
        if scritture < 0:
            raise ValueError(f"le scritture non sono negative, ricevute {scritture}")

        coda: queue.Queue[Evento | None] = queue.Queue()
        turni = self._riparti(scritture)
        campioni: list[float] = []
        riuscite = ritentate = confermati = 0

        with ThreadPoolExecutor(max_workers=max(1, len(turni))) as pool:
            futuri: list[Future[None]] = [
                pool.submit(self._turno, coda, primo, quante, per_scrittura, genera)
                for primo, quante in turni
            ]
            aperti = len(futuri)
            while aperti:
                elemento = coda.get()
                if elemento is None:
                    aperti -= 1
                    continue
                self._sink.emit(elemento)
                if isinstance(elemento, WriteSucceeded):
                    riuscite += 1
                    confermati += elemento.documenti
                elif isinstance(elemento, LatencySampled):
                    campioni.append(elemento.durata_ms)
                elif isinstance(elemento, RetryAttempted):
                    ritentate += 1
            # Un errore che non sia un fallimento di scrittura è un difetto, non un dato:
            # arriva al chiamante invece di finire in un conteggio.
            for futuro in futuri:
                futuro.result()

        return Riepilogo(
            scritture=scritture,
            riuscite=riuscite,
            fallite=scritture - riuscite,
            ritentate=ritentate,
            documenti_confermati=confermati,
            latenze=riassumi(campioni) if campioni else None,
        )

    # --- Il lavoro di un worker -------------------------------------------------------

    def _riparti(self, scritture: int) -> list[tuple[int, int]]:
        """Divide le scritture fra gli scrittori: (primo indice, quante) per ciascuno.

        Le scritture in avanzo vanno ai primi worker, uno a testa. Chiedere più scrittori
        che scritture non è un errore e non produce turni vuoti: il pool si dimensiona sul
        lavoro che c'è.
        """
        quanti = min(self._scrittori, scritture)
        if quanti < 1:
            return []
        base, resto = divmod(scritture, quanti)
        turni: list[tuple[int, int]] = []
        primo = 0
        for posto in range(quanti):
            quante = base + (1 if posto < resto else 0)
            turni.append((primo, quante))
            primo += quante
        return turni

    def _turno(
        self,
        coda: "queue.Queue[Evento | None]",
        primo: int,
        quante: int,
        per_scrittura: int,
        genera: Genera,
    ) -> None:
        try:
            for scrittura in range(primo, primo + quante):
                documenti = [
                    genera(scrittura * per_scrittura + posto)
                    for posto in range(per_scrittura)
                ]
                self._scrivi(coda, documenti)
        finally:
            coda.put(None)

    def _scrivi(
        self, coda: "queue.Queue[Evento | None]", documenti: Sequence[Documento]
    ) -> None:
        """Una scrittura e i suoi tentativi. Emette in coda, mai sul sink.

        Cattura `Exception` e non un tipo del driver: il dominio non sa che esiste
        pymongo, e per quanto riguarda questo strato **qualunque** errore di
        `insert_many` è un fallimento di scrittura da riportare e ritentare. Il tipo
        preciso non si perde, diventa il testo di `tipo_errore` — che è quanto serve
        perché la cronaca dica «AutoReconnect» durante un failover senza che nessuno qui
        dentro conosca quella classe.
        """
        for tentativo in range(1, self._politica.tentativi_massimi + 1):
            prima = self._orologio.now()
            try:
                confermati = self._archivio.insert_many(documenti)
            except Exception as errore:
                istante = self._orologio.now()
                motivo = str(errore)
                coda.put(
                    WriteFailed(
                        istante=istante,
                        tipo_errore=type(errore).__name__,
                        motivo=motivo,
                        documenti=len(documenti),
                    )
                )
                if tentativo == self._politica.tentativi_massimi:
                    return
                attesa_ms = self._politica.attesa_ms(tentativo + 1)
                coda.put(
                    RetryAttempted(
                        istante=istante,
                        tentativo=tentativo + 1,
                        attesa_ms=attesa_ms,
                        motivo=motivo,
                    )
                )
                self._orologio.sleep(attesa_ms / 1000)
                continue

            dopo = self._orologio.now()
            durata_ms = (dopo - prima) / UN_MILLISECONDO
            coda.put(
                WriteSucceeded(istante=dopo, documenti=confermati, durata_ms=durata_ms)
            )
            # Solo le scritture riuscite entrano nel campione. La durata di un fallimento
            # misura quanto ci ha messo il driver ad arrendersi, non quanto costa la
            # scrittura: mescolarle sposterebbe i percentili in un modo che nessuno
            # saprebbe più interpretare, e li sposterebbe **verso il basso** proprio nel
            # momento in cui il cluster sta peggio.
            coda.put(
                LatencySampled(
                    istante=dopo,
                    operazione=OPERAZIONE_SCRITTURA,
                    durata_ms=durata_ms,
                )
            )
            return
