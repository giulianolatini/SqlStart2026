"""Il generatore deterministico del dataset di demo.

Sta in `infrastructure/` benché non importi niente di terze parti, e il motivo non è la
dipendenza: è che **la forma del documento è un dettaglio del mondo esterno**. I sette
campi qui sotto sono quelli di `docker/01-standalone/init/10-dati-demo.js`, cioè di un
file che non è codice Python e che comanda su questo. Se un giorno il seed cambia una
città, cambia questo file e non il dominio.

Fa una cosa sola, e la fa in modo che due corse diverse producano lo stesso risultato:
**lo stesso seme dà lo stesso dataset**. Serve a due scene. La prima è la prova generale,
che deve scoprire gli stessi numeri della serata; la seconda è il confronto fra due misure
prese in momenti diversi, che con dataset diversi non significherebbe niente.

## Perché non è il seed JavaScript tradotto

`10-dati-demo.js` è deterministico ed è già scritto: la tentazione di ricopiarlo riga per
riga è forte, e produrrebbe per giunta lo stesso identico dataset. Non si può, per una
ragione che non ha niente a che vedere con il linguaggio.

Quel generatore è **sequenziale**: un solo stato che avanza a ogni numero estratto, quindi
il documento numero mille dipende dai novecentonovantanove chiesti prima. Va benissimo per
uno script che riempie una collezione dall'inizio alla fine, e non va per
`WorkloadRunner`, che scrive **da più thread** e distribuisce gli indici a blocchi
(`_turni`). L'ordine in cui i documenti vengono chiesti non è l'ordine dei loro indici, e
non è nemmeno lo stesso a ogni corsa: un generatore a flusso darebbe dataset diversi pur
avendo lo stesso seme. Il determinismo si perderebbe **proprio nella scena in cui serve**,
e senza che nulla fallisse.

Qui il documento di indice `n` è una funzione pura di `(seme, n)`. Non c'è stato che
avanzi, quindi non c'è ordine che conti e non c'è niente da bloccare fra thread. Il prezzo
è che il dataset **non coincide** con quello del seed: stessa forma, stessi valori
possibili, contenuti diversi.

## Le due popolazioni si incontrano, e non si scontrano

Fino al Task 14 qui c'era scritto che «le due popolazioni non si incontrano mai nella stessa
collezione, perché il carico scrive nella propria». Dal Task 15 non è più vero: la scena
dello sharding carica **apposta** `lab.ordini`, che è la collezione del seed, perché è
l'unica distribuita e senza quella non c'è niente da mostrare
([ADR-0106](../../../../docs/Decision.md#adr-0106)).

Quello che regge è un'invariante più stretta, e riguarda solo l'`_id`. **`documento` numera
gli `_id` da zero**, ed è ciò che rende il dataset una funzione pura di `(seme, indice)`:
quel metodo lo chiama solo `mongolab workload`, che ha la propria collezione per corsa
([ADR-0088](../../../../docs/Decision.md#adr-0088)). Le scene di `demo` scrivono invece con
`documento_progressivo`, che l'`_id` **non lo tocca** e lascia che sia il server a generare
un `ObjectId`. Un intero e un `ObjectId` non collidono mai, e infatti in `lab.ordini` sullo
stack 03 le due popolazioni convivono senza un solo `E11000`.

Il che dà anche il modo di distinguerle dopo: `{_id: {$type: "objectId"}}` seleziona ciò che
ha scritto l'applicazione, e `tools/reset-demo.sh` lo conta prima che il seed ricostruisca
la collezione.

## Perché xorshift e non `random`

`random.Random(seme)` sarebbe deterministico e più corto. Due ragioni per non usarlo. La
prima: il Mersenne Twister è uno stato di 624 parole, e seminarlo a ogni documento costa
molto più che estrarne un numero — con cinquantamila documenti la spesa si vede nella
misura di latenza, che è la misura per cui il carico esiste. La seconda: la sequenza di
`random` è garantita stabile fra versioni di Python per gli interi, ma è una promessa di
CPython, non un algoritmo scritto qui. Trentadue bit di xorshift stanno in cinque righe e
si rileggono fra un anno.
"""

from datetime import UTC, datetime, timedelta
from typing import Final, Iterator, Sequence

from mongolab.domain.modelli import Documento

__all__ = [
    "CITTA",
    "EPOCA",
    "SEME_DEL_TALK",
    "STATI",
    "DataGenerator",
]

SEME_DEL_TALK: Final = 20260918
"""Lo stesso seme di `10-dati-demo.js`: la data del talk, 18 settembre 2026.

Lo stesso numero non produce lo stesso dataset, perché l'algoritmo che lo consuma è
diverso (vedi la docstring del modulo). Resta lo stesso numero perché è quello che
qualcuno cercherà, e trovarne due diversi farebbe pensare a una svista invece che a una
scelta.
"""

CITTA: Final[Sequence[str]] = (
    "Ancona",
    "Bologna",
    "Cagliari",
    "Firenze",
    "Genova",
    "Milano",
    "Napoli",
    "Palermo",
    "Roma",
    "Torino",
)
"""Le dieci città del seed, nello stesso ordine.

Ancona è la prima perché è la città del talk, e perché è quella che compare nelle query
mostrate dal vivo: `{citta: "Ancona"}` deve trovare qualcosa sia sui documenti del seed
sia su quelli che l'applicazione scrive.
"""

STATI: Final[Sequence[str]] = (
    "ricevuto",
    "in lavorazione",
    "spedito",
    "consegnato",
    "annullato",
)

EPOCA: Final = datetime(2026, 1, 1, tzinfo=UTC)
"""Primo gennaio 2026, UTC. Mai `datetime.now()`.

Consapevole del fuso, e non per pedanteria: BSON conserva un istante, e un `datetime`
ingenuo viene scritto come UTC e riletto come UTC. Sulla macchina di chi presenta, due ore
avanti in estate, le date scritte «alla locale» tornerebbero indietro di due ore senza che
niente fallisca.
"""

GIORNI: Final = 240
"""L'ampiezza della finestra: da gennaio a fine agosto 2026, come nel seed."""

CLIENTI: Final = 2000
IMPORTO_MASSIMO_CENTESIMI: Final = 500_000
RIGHE_MASSIME: Final = 5

_MASCHERA: Final = 0xFFFFFFFF
_RAPPORTO_AUREO: Final = 0x9E3779B1
"""La costante di Weyl: il reciproco della sezione aurea su 32 bit, dispari.

Moltiplicare l'indice per un intero dispari grande e sparso è un modo standard di
trasformare `0, 1, 2, …` in punti lontani fra loro. Da sola non basta — è una biiezione
lineare, e resta lineare — per questo il risultato passa dal mescolatore qui sotto.
"""


def _mescola(valore: int) -> int:
    """`fmix32` di MurmurHash3: porta i bit alti a influenzare i bassi.

    Serve a un difetto che questo disegno ha e quello sequenziale no. Siccome lo stato di
    partenza si ricava dall'indice, due indici vicini partono da stati vicini; e xorshift,
    che è lineare, da stati vicini produce primi valori correlati. Senza questo passaggio
    cento documenti di fila finiscono nella stessa città — un difetto che non fa fallire
    niente e si vede solo guardando, che è la lezione di [V-013](../../../docs/Sources.md).
    """
    valore ^= valore >> 16
    valore = (valore * 0x85EBCA6B) & _MASCHERA
    valore ^= valore >> 13
    valore = (valore * 0xC2B2AE35) & _MASCHERA
    valore ^= valore >> 16
    return valore


class _Estrattore:
    """Uno xorshift32 privato, che vive quanto un documento e poi sparisce.

    Non è una classe pubblica e non è riusabile fra documenti apposta: la sua unica
    ragione di esistere è tenere lo stato per le sei estrazioni di **un** documento. Quello
    che il chiamante vede è `DataGenerator.documento`, che di stato non ne ha.
    """

    __slots__ = ("_stato",)

    def __init__(self, seme: int, indice: int) -> None:
        stato = _mescola((seme + indice * _RAPPORTO_AUREO) & _MASCHERA)
        # Lo zero è il punto fisso di xorshift: da lì non si esce più, e ogni documento
        # che ci capitasse sarebbe identico agli altri. Capita a un indice su quattro
        # miliardi, cioè mai — e «mai» in una demo vuol dire una volta, davanti a tutti.
        self._stato = stato or _RAPPORTO_AUREO

    def prossimo(self, limite: int) -> int:
        """Un intero in `[0, limite)`.

        Le tre righe sono lo xorshift32 di Marsaglia con la terna (13, 17, 5), la stessa
        che usa il seed. Il resto della divisione introduce una distorsione verso i valori
        bassi, che con limiti fino a 2000 su 2³² vale meno di un milionesimo: dichiarata,
        e irrilevante per scegliere una città.
        """
        stato = self._stato
        stato ^= (stato << 13) & _MASCHERA
        stato ^= stato >> 17
        stato ^= (stato << 5) & _MASCHERA
        self._stato = stato
        return stato % limite


class DataGenerator:
    """Documenti della forma del dataset di demo, indicizzati invece che in fila.

    `documento(n)` è una funzione pura: nessuno stato interno, quindi nessun blocco fra
    thread e nessuna dipendenza dall'ordine delle chiamate. Le prove che lo verificano
    sono in `tests/unit/test_generatore.py`, e la più importante è quella che mescola gli
    indici prima di chiederli.
    """

    __slots__ = ("_seme",)

    def __init__(self, seme: int = SEME_DEL_TALK) -> None:
        self._seme = seme & _MASCHERA

    def documento(self, indice: int) -> Documento:
        """Il documento di indice `indice`. Si passa a `WorkloadRunner` come `Genera`.

        L'ordine delle sei estrazioni è quello dei campi nel seed, e non si cambia senza
        cambiare il dataset: sono estrazioni dallo stesso flusso, quindi scambiare due
        righe qui è scambiare due valori in tutti i documenti.
        """
        estrai = _Estrattore(self._seme, indice)
        return {
            "_id": indice,
            "cliente": f"cliente-{estrai.prossimo(CLIENTI):04d}",
            "citta": CITTA[estrai.prossimo(len(CITTA))],
            "stato": STATI[estrai.prossimo(len(STATI))],
            "importo": estrai.prossimo(IMPORTO_MASSIMO_CENTESIMI) / 100,
            "righe": 1 + estrai.prossimo(RIGHE_MASSIME),
            "data": EPOCA + timedelta(days=estrai.prossimo(GIORNI)),
        }

    def lotto(self, quanti: int, dal: int = 0) -> Iterator[Documento]:
        """`quanti` documenti a partire da `dal`, uno alla volta.

        Un iteratore e non una lista: cinquantamila documenti materializzati prima di
        cominciare sposterebbero il tempo dal cluster al generatore, e il carico esiste
        per misurare il primo.

        **Non è una funzione generatore**, ed è deliberato. Scritta con `yield` dentro,
        questa stessa funzione controllerebbe `quanti` solo al primo `next()`: l'errore di
        chi l'ha configurata male arriverebbe a thread già avviati, dal punto sbagliato e
        con la traccia sbagliata. Validare all'ingresso e restituire l'iteratore costa una
        riga in più e sposta il rosso dove sta il torto.
        """
        if quanti < 0:
            raise ValueError(f"quanti documenti non può essere negativo: {quanti}")
        return (self.documento(indice) for indice in range(dal, dal + quanti))
