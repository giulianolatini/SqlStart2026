"""La zavorra: portare un documento alla dimensione che `--doc-size` chiede.

Il tipo `Genera` di `application/workload.py` dice da sempre di essere «il gancio per
`--doc-size`: la dimensione del documento è una faccenda di chi genera, e tenerla fuori dal
generatore di carico evita che `WorkloadRunner` debba sapere che cos'è un kilobyte di
BSON». Questo modulo è ciò che si attacca al gancio: prende un `Genera` e ne restituisce
un altro, che produce gli stessi documenti con un campo in più.

Sta qui e non in `generatore.py` per una ragione precisa: quel modulo apre dichiarando di
non importare niente di terze parti, e la dimensione **esatta** di un documento si ottiene
solo codificandolo, cioè con `bson`. Aggiungerlo là avrebbe reso falsa la prima riga di
una docstring, che è il modo in cui una documentazione comincia a mentire.

## Perché misurata e non stimata

Sommare la lunghezza dei campi per prevedere quanto peserà il BSON si può fare, e si
sbaglia: ogni campo costa un byte di tipo, il nome con il suo terminatore, e gli interi
cambiano larghezza quando superano i trentadue bit — `_id` compreso, che in una corsa da
centomila documenti attraversa quel confine. Codificare e misurare costa un `bson.encode`
per documento e dà la risposta invece di una previsione. Il prezzo è dichiarato: a
cinquantamila documenti sono cinquantamila codifiche in più, che il Task 16 pagherà e
misurerà.

## Perché la zavorra non è una fila di `x`

`"x" * 2000` è la zavorra ovvia, e produrrebbe una misura falsa. WiredTiger comprime i
blocchi con snappy per impostazione predefinita, e duemila byte dello stesso carattere si
riducono a una manciata: una collezione di «documenti da 2 KB» occuperebbe una frazione
dello spazio, il working set starebbe tutto in cache, e la misura di throughput del Task
16 descriverebbe un carico che nessuno ha chiesto. La zavorra qui è base64 di un flusso
pseudocasuale — sei bit di entropia per carattere — deterministico in `(seme, indice)`
come tutto il resto del dataset.
"""

import base64
import hashlib
import re
from typing import Final

import bson

from mongolab.application.workload import Genera
from mongolab.domain.modelli import Documento
from mongolab.infrastructure.generatore import SEME_DEL_TALK

__all__ = [
    "CAMPO_ZAVORRA",
    "MASSIMO_BSON",
    "byte_di",
    "con_dimensione",
]

CAMPO_ZAVORRA: Final = "zavorra"
"""Il nome del campo che porta il riempimento.

Un nome italiano e leggibile invece di `_pad`: finisce in `db.ordini.findOne()` proiettato
sullo schermo durante il talk, e «zavorra» si spiega da solo mentre `_pad` fa alzare una
mano. Che sia corto conta anche per un'altra ragione: la sua lunghezza entra nel conto dei
byte, quindi un nome lungo abbassa la dimensione minima ottenibile.
"""

MASSIMO_BSON: Final = 16 * 1024 * 1024
"""Il limite di MongoDB per un singolo documento: 16 MB, cioè 16 777 216 byte.

Sedici *mebibyte*, non sedici milioni. È la ragione per cui `k` qui vale 1024: usare 1000
per l'opzione e 1024 per il limite metterebbe due unità diverse nella stessa frase.
"""

_FORMA: Final = re.compile(r"^(\d+)([kKmM]?)$")
_MOLTIPLICATORE: Final = {"": 1, "k": 1024, "m": 1024 * 1024}


def byte_di(testo: str) -> int:
    """Legge `512`, `2k`, `1m` e restituisce un numero di byte.

    Rifiuta tutto il resto mostrando le forme che accetta. Un messaggio che dicesse solo
    «valore non valido» costringerebbe a indovinare se il suffisso giusto sia `kb`, `KiB`
    o niente, e lo si indovinerebbe la sera del talk.
    """
    trovato = _FORMA.match(testo.strip())
    if trovato is None:
        raise ValueError(
            f"«{testo}» non è una dimensione. Si scrive un numero di byte, "
            f"eventualmente con `k` o `m`: 512, 2k, 1m."
        )
    quanti = int(trovato.group(1)) * _MOLTIPLICATORE[trovato.group(2).lower()]
    if quanti <= 0:
        raise ValueError(f"un documento di {quanti} byte non esiste: chiedine almeno uno.")
    if quanti > MASSIMO_BSON:
        raise ValueError(
            f"{quanti} byte superano il limite di MongoDB per un documento, che è "
            f"16 MB, cioè {MASSIMO_BSON} byte."
        )
    return quanti


def _riempimento(seme: int, indice: int, quanti: int) -> str:
    """`quanti` caratteri ASCII pseudocasuali, funzione pura di `(seme, indice)`.

    `shake_128` è una funzione di estrazione a lunghezza variabile: si chiede il numero di
    byte che serve e li dà, senza il giro di concatenare digest che servirebbe con una
    funzione a lunghezza fissa. Il base64 che segue porta i byte nell'ASCII, dove un
    carattere è un byte — che è la condizione perché tagliare a `quanti` caratteri dia
    `quanti` byte di BSON.
    """
    if quanti <= 0:
        return ""
    grezzi = hashlib.shake_128(f"{seme}:{indice}".encode("utf-8")).digest(
        (quanti * 3 + 3) // 4
    )
    return base64.b64encode(grezzi).decode("ascii")[:quanti]


def con_dimensione(genera: Genera, byte: int, *, seme: int = SEME_DEL_TALK) -> Genera:
    """Da un `Genera` a un `Genera` che produce documenti di esattamente `byte` byte.

    Restituisce una funzione e non una classe perché è esattamente ciò che
    `WorkloadRunner.esegui` accetta: `con_dimensione(DataGenerator().documento, 2048)` si
    passa dov'era `documento_progressivo`, e nessuno strato di mezzo cambia.
    """

    def vestito(indice: int) -> Documento:
        # Una copia, e non il documento ricevuto: `genera` potrebbe restituire un
        # dizionario che riusa, e scriverci dentro lo sporcherebbe per il chiamante dopo.
        # Annotato `dict` e non `Documento`: `Documento` è un `Mapping`, cioè di sola
        # lettura, e la riga che assegna la zavorra qui sotto non compilerebbe. La copia
        # torna `Documento` all'uscita, dove essere di sola lettura è di nuovo giusto.
        documento: dict[str, object] = {**genera(indice), CAMPO_ZAVORRA: ""}
        minimo = len(bson.encode(documento))
        if byte < minimo:
            raise ValueError(
                f"{byte} byte non bastano: il documento di indice {indice} ne misura "
                f"{minimo} già senza zavorra."
            )
        documento[CAMPO_ZAVORRA] = _riempimento(seme, indice, byte - minimo)
        return documento

    return vestito
