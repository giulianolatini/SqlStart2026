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

**Due limiti, e mai tutti e due.** Una corsa finisce o perché ha fatto le scritture che le
sono state chieste (`scritture=N`) o perché è scaduto il tempo (`durata_s=T`). Il §6.4
scrive `--duration 120`, e il secondo limite esiste per quella riga: un failover si misura
per un intervallo, non per un conteggio, perché quante scritture ci stiano dentro è
**il risultato**, non il dato. Nessun valore predefinito: senza limiti la corsa non
finirebbe, e con tutti e due il primo che scade smentirebbe l'altro.

**I lettori (`--readers`).** Un carico di sole scritture non mostra ciò che un replica set
esiste per fare, e una latenza di lettura durante un failover è una misura diversa da
quella di scrittura. I lettori girano accanto agli scrittori, campionano su
`OPERAZIONE_LETTURA` — un campione **separato**, come `OPERAZIONE_SCRITTURA` prometteva
da prima che esistessero — e a fermarli è la scadenza, oppure la fine degli scrittori
quando il limite è un conteggio: un lettore non ha un lavoro da esaurire, quindi deve
esserci qualcuno che gli dice di smettere.

Una riserva dichiarata: una lettura fallita viene **contata e non raccontata**. Gli otto
eventi del dominio sono congelati e nessuno di loro descrive quel caso; inventarne un nono
per una statistica sarebbe stato scongelarli dalla parte sbagliata. Chi legge il riepilogo
vede `letture_fallite`; chi guarda la cronaca non vede niente.
"""

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
import queue
import threading
from typing import Callable, Iterator, Sequence

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
    "OPERAZIONE_LETTURA",
    "OPERAZIONE_SCRITTURA",
    "PAGINA",
    "PAGINE_LETTE",
    "Continua",
    "Genera",
    "Latenze",
    "Legge",
    "PoliticaTentativi",
    "Riepilogo",
    "WorkloadRunner",
    "documento_progressivo",
    "pagina_ciclica",
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

OPERAZIONE_LETTURA = "find_page"
"""Quel giorno è arrivato al Task 11, e questa costante è il modo in cui i due campioni
restano separati: il riepilogo li divide leggendo `LatencySampled.operazione`, e la
promessa scritta sopra si mantiene senza aggiungere un evento."""

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
    """Il documento più piccolo che serva a qualcosa: solo il suo numero d'ordine.

    **Non c'è `_id`, e l'assenza è la ragione per cui il Task 15 sta in piedi.** Senza
    quel campo lo genera il server, che produce un `ObjectId`; con esso lo genererebbe
    `DataGenerator`, che numera da zero e andrebbe a sbattere contro gli interi del seed
    al primo documento ([ADR-0088](../../../../docs/Decision.md#adr-0088)). È per questo
    che le scene di `demo` possono caricare `lab.ordini` — la collezione del seed, l'unica
    distribuita — senza un solo `E11000`, e che i loro documenti si riconoscono poi da
    `{_id: {$type: "objectId"}}` ([ADR-0106](../../../../docs/Decision.md#adr-0106)).
    """
    return {"indice": indice}


Legge = Callable[[DocumentStore, int], int]
"""Che cosa fa un lettore a ogni giro, e quanti documenti ha ottenuto.

Il gemello di `Genera`, dall'altro lato: riceve l'archivio e il numero d'ordine del giro,
e restituisce il conto dei documenti letti. È il gancio con cui il Task 16 misura *la sua*
interrogazione — un `aggregate`, una `find` con un filtro selettivo — senza che
`WorkloadRunner` sappia niente di query.
"""

Continua = Callable[[], bool]
"""Si va avanti? La domanda che il carico fa a qualcun altro, prima di ogni operazione.

`durata_s` sa quando finire perché glielo si è detto prima; questa condizione lo scopre
mentre la corsa va. Serve alla scena del backup a caldo, dove il carico deve coprire
**esattamente** la finestra del `mongodump`: una durata fissa la sceglierebbe a caso, e un
dump da mezzo secondo dentro un campione da venti finirebbe diluito in una media che non
mostra il crollo che la scena esiste per mostrare.

Non sostituisce il limite, lo restringe: `esegui` la accetta solo insieme a `scritture` o
a `durata_s`, perché una condizione che dipende da un processo esterno resta vera per
sempre se quel processo si pianta.

**La chiamano tutti i worker, ognuno dal proprio thread.** Chi la scrive deve reggerlo: un
`threading.Event` va bene, un contatore incrementato a mano no.
"""

PAGINA = 20
"""Quanti documenti legge un giro del lettore predefinito. È la pagina di `find_page`."""

PAGINE_LETTE = 50
"""Quante pagine diverse il lettore predefinito visita prima di ricominciare.

La finestra è **chiusa** apposta. `skip` in MongoDB scarta i documenti uno per uno prima
di restituire la pagina, quindi il costo cresce con il salto: un lettore che camminasse in
avanti per sempre, dopo qualche minuto, misurerebbe il costo dello `skip` invece di quello
della lettura, e il p95 del Task 16 salirebbe da solo senza che il cluster stia peggio.
Cinquanta pagine da venti sono mille documenti — abbastanza da non stare tutti nella cache
del piano, abbastanza pochi da rendere il salto trascurabile.
"""


def pagina_ciclica(archivio: DocumentStore, ordine: int) -> int:
    """Legge una pagina, girando dentro le prime `PAGINE_LETTE`. Restituisce quanti.

    Non filtra: `{}` è il carico di lettura più onesto per un confronto fra architetture,
    perché non dipende da quali indici esistano su quello stack. Il giorno in cui servisse
    misurare una query indicizzata, si passa un altro `Legge` — che è il motivo per cui
    questa funzione è un valore predefinito e non un metodo.
    """
    return len(archivio.find_page({}, salta=(ordine % PAGINE_LETTE) * PAGINA, quanti=PAGINA))


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
    """Le scritture **logiche**, cioè i tentativi riusciti più le rese definitive.

    Con il limite di conteggio è il numero chiesto, e si potrebbe copiare da lì; con quello
    di durata nessuno lo conosce in anticipo. Si ricava dagli eventi in tutti e due i casi
    — una scrittura che si arrende dopo tre tentativi ne conta **una** — perché due modi di
    calcolare lo stesso numero sono due numeri appena uno dei due sbaglia.
    """

    riuscite: int
    fallite: int
    ritentate: int
    documenti_confermati: int
    latenze: Latenze | None

    # I campi delle letture arrivano con un valore predefinito, e non è solo compatibilità:
    # una corsa di sole scritture non ha letture, e zero è la risposta giusta — mentre per
    # le *latenze* la risposta giusta resta `None`, per la ragione scritta qui sopra.
    letture: int = 0
    letture_riuscite: int = 0
    letture_fallite: int = 0
    documenti_letti: int = 0
    latenze_letture: Latenze | None = None


@dataclass(frozen=True, slots=True)
class _Lettura:
    """Il conto di una lettura, che viaggia sulla coda ma **non** finisce sul sink.

    `documenti` è quanti ne sono tornati, oppure `None` se la lettura è fallita. Esiste
    perché la coda porta due cose diverse — la cronaca e la contabilità — e distinguerle
    con un tipo invece che con una convenzione è ciò che rende impossibile emettere per
    sbaglio un conteggio come se fosse un evento del dominio.
    """

    documenti: int | None


@dataclass(frozen=True, slots=True)
class _Finito:
    """Il gettone con cui un worker dichiara di aver smesso. Nemmeno questo è un evento.

    Prende il posto del `None` che il Task 5 usava come sentinella, perché adesso il ciclo
    di drenaggio ha bisogno di sapere **chi** ha finito: quando finisce l'ultimo scrittore
    i lettori vanno fermati, e un `None` anonimo non lo direbbe.
    """

    lettore: bool


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
        lettori: int = 0,
    ) -> None:
        if scrittori < 0:
            raise ValueError(f"gli scrittori non sono negativi, ricevuti {scrittori}")
        if lettori < 0:
            raise ValueError(f"i lettori non sono negativi, ricevuti {lettori}")
        if scrittori + lettori < 1:
            # Zero scrittori non è più un errore da solo — `--writers 0 --readers 4` è il
            # carico con cui si misura una replica interrogata in sola lettura. L'errore è
            # zero worker: una corsa che non fa niente per tutto il tempo che le si dà.
            raise ValueError(
                "serve almeno un worker: zero scrittori e zero lettori sono una corsa "
                "che non farebbe niente."
            )
        self._archivio = archivio
        self._orologio = orologio
        self._sink = sink
        self._politica = politica
        self._scrittori = scrittori
        self._lettori = lettori

    def esegui(
        self,
        scritture: int | None = None,
        *,
        durata_s: float | None = None,
        finche: Continua | None = None,
        per_scrittura: int = 1,
        genera: Genera = documento_progressivo,
        legge: Legge = pagina_ciclica,
    ) -> Riepilogo:
        """Una corsa, limitata da un conteggio di scritture **oppure** da una durata.

        Il ciclo di drenaggio è il cuore del metodo, e la sua correttezza sta in un
        dettaglio: ogni worker, **qualunque cosa accada**, mette in coda un `_Finito` come
        ultimo gesto. Il chiamante conta i gettoni invece di interrogare i futuri o di
        attendere con un timeout, e così il ciclo termina anche se un worker muore per un
        errore che non riguarda le scritture. I timeout in un ciclo di consumo sono la
        via che porta a una prova che fallisce una volta su cento su una macchina carica.

        Lo stesso ciclo è anche ciò che ferma i lettori: quando l'ultimo gettone di
        scrittore è passato, alza `fine`. Farlo qui invece che in un contatore condiviso
        fra i worker toglie un lucchetto dal cammino caldo e mette la condizione di
        terminazione in un thread solo, che è già l'invariante del §6.3.

        `finche` si somma al limite invece di sostituirlo, e il verso conta: la condizione
        è il limite **vero** — la corsa finisce quando il dump finisce — e la durata resta
        la rete di sicurezza che fa terminare la scena anche se il dump non torna più.
        """
        if finche is not None and scritture is None and durata_s is None:
            raise ValueError(
                "`finché` restringe un limite, non ne fa le veci: una condizione che "
                "dipende da un processo esterno resta vera per sempre se quel processo "
                "si pianta. Va data insieme a `scritture` o a `durata_s`, che è il tetto."
            )
        if (scritture is None) == (durata_s is None):
            raise ValueError(
                "una corsa si limita in un modo solo: o `scritture`, quante ne fa, o "
                "`durata_s`, per quanto va avanti. Senza nessuno dei due non finirebbe; "
                "con tutti e due il primo che scade smentirebbe l'altro."
            )
        if scritture is not None and scritture < 0:
            raise ValueError(f"le scritture non sono negative, ricevute {scritture}")
        if durata_s is not None and durata_s <= 0:
            raise ValueError(
                f"una durata si misura in secondi positivi, ricevuti {durata_s}"
            )
        if scritture and self._scrittori == 0:
            raise ValueError(
                f"{scritture} scritture chieste a zero scrittori: nessuno le farebbe. "
                "Un carico di sole letture si limita con `durata_s`."
            )

        scadenza = (
            self._orologio.now() + timedelta(seconds=durata_s)
            if durata_s is not None
            else None
        )
        coda: queue.Queue[Evento | _Lettura | _Finito] = queue.Queue()
        fine = threading.Event()
        turni = self._turni(scritture)

        campioni: list[float] = []
        campioni_letture: list[float] = []
        riuscite = ritentate = confermati = cadute = 0
        letture_riuscite = letture_fallite = documenti_letti = 0

        with ThreadPoolExecutor(max_workers=max(1, len(turni) + self._lettori)) as pool:
            futuri: list[Future[None]] = [
                pool.submit(
                    self._turno,
                    coda,
                    primo,
                    passo,
                    quante,
                    scadenza,
                    finche,
                    per_scrittura,
                    genera,
                )
                for primo, passo, quante in turni
            ]
            futuri += [
                pool.submit(self._corsa_lettore, coda, scadenza, finche, fine, legge)
                for _ in range(self._lettori)
            ]
            scrittori_aperti = len(turni)
            if not scrittori_aperti:
                fine.set()
            aperti = len(futuri)
            while aperti:
                elemento = coda.get()
                if isinstance(elemento, _Finito):
                    aperti -= 1
                    if not elemento.lettore:
                        scrittori_aperti -= 1
                        if not scrittori_aperti:
                            fine.set()
                    continue
                if isinstance(elemento, _Lettura):
                    if elemento.documenti is None:
                        letture_fallite += 1
                    else:
                        letture_riuscite += 1
                        documenti_letti += elemento.documenti
                    continue
                self._sink.emit(elemento)
                if isinstance(elemento, WriteSucceeded):
                    riuscite += 1
                    confermati += elemento.documenti
                elif isinstance(elemento, LatencySampled):
                    if elemento.operazione == OPERAZIONE_LETTURA:
                        campioni_letture.append(elemento.durata_ms)
                    else:
                        campioni.append(elemento.durata_ms)
                elif isinstance(elemento, RetryAttempted):
                    ritentate += 1
                elif isinstance(elemento, WriteFailed):
                    cadute += 1
            # Un errore che non sia un fallimento di scrittura è un difetto, non un dato:
            # arriva al chiamante invece di finire in un conteggio.
            for futuro in futuri:
                futuro.result()

        # Ogni tentativo fallito emette un `WriteFailed`, e tutti tranne l'ultimo emettono
        # anche un `RetryAttempted`: la differenza fra i due conteggi è il numero di
        # scritture che si sono arrese, cioè di scritture **logiche** fallite. Tre
        # `WriteFailed` e due `RetryAttempted` sono una scrittura persa, non tre.
        fallite = cadute - ritentate

        return Riepilogo(
            scritture=riuscite + fallite,
            riuscite=riuscite,
            fallite=fallite,
            ritentate=ritentate,
            documenti_confermati=confermati,
            latenze=riassumi(campioni) if campioni else None,
            letture=letture_riuscite + letture_fallite,
            letture_riuscite=letture_riuscite,
            letture_fallite=letture_fallite,
            documenti_letti=documenti_letti,
            latenze_letture=riassumi(campioni_letture) if campioni_letture else None,
        )

    # --- Il lavoro di un worker -------------------------------------------------------

    def _turni(self, scritture: int | None) -> list[tuple[int, int, int | None]]:
        """Per ogni scrittore: da quale indice parte, di quanto avanza, e quante ne fa.

        I due limiti dividono il lavoro in due modi diversi, e devono. Con un conteggio si
        sa tutto prima, quindi si taglia in blocchi contigui — `_riparti` — e ogni worker
        conosce il proprio pezzo senza guardare l'orologio nemmeno una volta, che è ciò che
        tiene `FakeClock.attese` pulito nelle prove del backoff.

        Con una durata non si sa quante scritture ci staranno, e i blocchi non si possono
        calcolare. Gli indici si prendono a scacchiera — il k-esimo scrittore fa k, k+n,
        k+2n — e restano distinti senza che i worker si accordino su un contatore
        condiviso, che sarebbe un lucchetto proprio sul cammino più caldo del carico.
        """
        if scritture is None:
            return [(posto, self._scrittori, None) for posto in range(self._scrittori)]
        return [(primo, 1, quante) for primo, quante in self._riparti(scritture)]

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
        coda: "queue.Queue[Evento | _Lettura | _Finito]",
        primo: int,
        passo: int,
        quante: int | None,
        scadenza: datetime | None,
        finche: Continua | None,
        per_scrittura: int,
        genera: Genera,
    ) -> None:
        try:
            for scrittura in self._ordini(primo, passo, quante, scadenza, finche):
                documenti = [
                    genera(scrittura * per_scrittura + posto)
                    for posto in range(per_scrittura)
                ]
                self._scrivi(coda, documenti)
        finally:
            coda.put(_Finito(lettore=False))

    def _ordini(
        self,
        primo: int,
        passo: int,
        quante: int | None,
        scadenza: datetime | None,
        finche: Continua | None,
    ) -> Iterator[int]:
        """I numeri d'ordine che tocca a questo scrittore, finché ce ne sono o c'è tempo.

        L'orologio si guarda **prima** di ogni scrittura e non dopo: una corsa che
        cominciasse un inserimento a scadenza già passata lo porterebbe comunque a termine,
        e con un `insert_many` lento la durata misurata supererebbe quella chiesta senza
        che nessuno sappia di quanto.

        La condizione si guarda **prima dell'orologio**, perché è il limite vero: quando è
        lei a fermare la corsa, la scadenza non viene nemmeno letta, e nelle prove il
        `FakeClock` non conta un tempo che nessuno ha consumato.
        """
        ordine = primo
        prodotti = 0
        while quante is None or prodotti < quante:
            if finche is not None and not finche():
                return
            if scadenza is not None and self._orologio.now() >= scadenza:
                return
            yield ordine
            ordine += passo
            prodotti += 1

    # --- Il lavoro di un lettore ------------------------------------------------------

    def _corsa_lettore(
        self,
        coda: "queue.Queue[Evento | _Lettura | _Finito]",
        scadenza: datetime | None,
        finche: Continua | None,
        fine: threading.Event,
        legge: Legge,
    ) -> None:
        try:
            ordine = 0
            while self._si_legge_ancora(scadenza, finche, fine):
                self._leggi(coda, ordine, legge)
                ordine += 1
        finally:
            coda.put(_Finito(lettore=True))

    def _si_legge_ancora(
        self,
        scadenza: datetime | None,
        finche: Continua | None,
        fine: threading.Event,
    ) -> bool:
        """Le condizioni di terminazione di un lettore, e quali di esse si sommano.

        Con il limite di durata comanda la scadenza, e basta lei: gli scrittori finiscono
        nello stesso istante. Con quello di conteggio non c'è scadenza, e a fermare i
        lettori è `fine`, che il ciclo di drenaggio alza quando l'ultimo scrittore ha
        smesso — perché un lettore non ha un lavoro da esaurire e altrimenti girerebbe per
        sempre.

        Sommare **queste due** sarebbe un difetto sottile: con `--writers 0` non c'è
        nessuno scrittore da aspettare, `fine` è alzato dal primo istante, e una corsa di
        sole letture con una durata di due minuti durerebbe zero.

        `finche` invece si somma a entrambe, e deve: se fermasse i soli scrittori, i
        lettori resterebbero a girare fino al tetto, e la fase del dump durerebbe il minuto
        della rete di sicurezza invece del mezzo secondo del `mongodump`.
        """
        if finche is not None and not finche():
            return False
        if scadenza is not None:
            return self._orologio.now() < scadenza
        return not fine.is_set()

    def _leggi(
        self,
        coda: "queue.Queue[Evento | _Lettura | _Finito]",
        ordine: int,
        legge: Legge,
    ) -> None:
        """Una lettura. Nessun tentativo, e nessun evento se fallisce.

        **Perché non ritenta.** Gli scrittori ritentano perché una scrittura persa è un
        dato che si vuole recuperare; una lettura persa non lascia niente da recuperare, e
        ritentarla nasconderebbe proprio la finestra di indisponibilità che la scena esiste
        per mostrare. Il numero che interessa è quante letture non sono passate durante il
        failover, e lo si ottiene contandole al primo colpo.

        **Perché non emette.** Una lettura fallita è contabilità, non cronaca: gli otto
        eventi del dominio sono congelati e nessuno di loro la descrive. È una riserva
        dichiarata — chi guarda la TUI durante un failover vede le scritture cadere e non
        le letture — e il giorno in cui valesse il nono evento, si scongela con la prova in
        mano invece che di sfuggita.
        """
        prima = self._orologio.now()
        try:
            quanti = legge(self._archivio, ordine)
        except Exception:
            coda.put(_Lettura(documenti=None))
            return
        dopo = self._orologio.now()
        coda.put(_Lettura(documenti=quanti))
        coda.put(
            LatencySampled(
                istante=dopo,
                operazione=OPERAZIONE_LETTURA,
                durata_ms=(dopo - prima) / UN_MILLISECONDO,
            )
        )

    def _scrivi(
        self,
        coda: "queue.Queue[Evento | _Lettura | _Finito]",
        documenti: Sequence[Documento],
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
