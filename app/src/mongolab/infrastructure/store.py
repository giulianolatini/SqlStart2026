"""`PymongoStore`: la porta `DocumentStore` attaccata a un MongoDB vero.

Quattro metodi, e nessuno di essi è una riga sola per caso. Ognuno traduce una promessa
del dominio in una chiamata al driver, e in tre casi su quattro la traduzione ovvia
sarebbe **diversa** da quella giusta: le ragioni stanno nelle docstring dei metodi, e
ognuna ha una prova in `tests/integration/test_contratto_archivio.py` che la verifica
contro uno stack acceso.

## Riceve una collezione, non una stringa di connessione

Il costruttore prende una `Collection` già fatta. Sembra un dettaglio e decide una cosa
grossa: **questo oggetto non ha una politica di connessione**. Chi lo costruisce sceglie
l'indirizzo, l'autenticazione, il `directConnection`, il `readPreference` — e al Task 12
quella scelta sarà [ADR-0012](../../../../docs/Decision.md#adr-0012), cioè il nome di
servizio dentro la rete Compose. Se la politica stesse qui, provare l'adattatore
significherebbe provare anche la politica, e cambiarla vorrebbe dire riaprire questo file.

## L'unica cosa del client su cui però ha voce

`tz_aware`. Il costruttore rifiuta una collezione che arriva da un client senza, e non è
zelo: è l'unico difetto di configurazione che **non fallisce**. Le date tornano indietro
ingenue, il confronto fra due ingenue riesce, e lo sbaglio si vede in una data storta
sullo schermo, in scena. Una guardia si giustifica quando l'alternativa è un errore
silenzioso, ed è esattamente questo il caso.
"""

from typing import Any, Sequence

from pymongo import ASCENDING
from pymongo.collection import Collection

from mongolab.domain.modelli import Documento

__all__ = ["PymongoStore"]


class PymongoStore:
    """Un `DocumentStore` che parla con MongoDB.

    Non eredita dalla porta e non la importa: la conformità è strutturale e a verificarla
    è `mypy --strict`, dove le prove annotano `archivio: DocumentStore`. È la stessa regola
    dei doppi, e vale qui per la stessa ragione — se l'ereditarietà fosse necessaria, il
    dominio dovrebbe essere importabile da chi lo implementa, e non lo è.
    """

    __slots__ = ("collezione",)

    def __init__(self, collezione: Collection[dict[str, Any]]) -> None:
        if not collezione.codec_options.tz_aware:
            raise ValueError(
                "la collezione arriva da un client senza tz_aware=True: i datetime "
                "tornerebbero indietro ingenui, il confronto con quelli scritti "
                "riuscirebbe lo stesso, e sbaglierebbe di quante ore vale il fuso. "
                "Costruisci il client con MongoClient(..., tz_aware=True)."
            )
        self.collezione = collezione
        """Pubblica apposta: le prove che devono mostrare la differenza fra l'adattatore e
        il driver nudo hanno bisogno di arrivarci, e nasconderla dietro un `_` per poi
        leggerla da fuori sarebbe fingere un incapsulamento che non c'è."""

    def insert_many(self, documenti: Sequence[Documento]) -> int:
        """Inserisce e restituisce quanti il server ha confermato.

        **Copia ogni documento**, e non per prudenza generica: `pymongo` scrive l'`_id`
        che genera **dentro** il dizionario ricevuto (la pagina lo dice di `insert_one` —
        il documento «Must be a mutable mapping type. If the document does not have an `_id`
        field one will be added automatically» — e non lo dice di `insert_many`, dove pure
        succede: [A-014](../../../../app/docs/Sources.md#a-014)). Il generatore di carico riusa i
        propri dizionari, quindi senza la copia al secondo giro si troverebbe un `_id` già
        dentro e inserirebbe due volte lo stesso — un `BulkWriteError` al posto di una
        scrittura. La copia serve comunque, perché la porta dichiara `Mapping` e il driver
        vuole un mapping mutabile; averla per due ragioni indipendenti la rende difficile
        da togliere per sbaglio.

        **Zero documenti non è un errore**, benché per `pymongo` lo sia
        (`InvalidOperation`). Il carico ci arriva davvero il giorno in cui l'ultimo turno
        di un thread è vuoto perché i documenti non si dividono per il numero di scrittori.

        **Non ingoia il `BulkWriteError`.** Il numero che esce di qui finisce in
        `WriteSucceeded.documenti`, che è metà della misura «confermate contro ritrovate»:
        restituire il parziale dopo un fallimento vorrebbe dire dichiarare un successo che
        non c'è stato. Chi chiama decide, e al Task 13 deciderà con una politica di
        tentativi — che dovrà sapere che riprovare un blocco a metà produce duplicati.

        **`ordered` resta quello predefinito, cioè `True`, ed è una misura non una
        pigrizia.** `ordered=False` è la scelta abituale per il caricamento massivo, perché
        lascia al server la libertà di non fermarsi al primo errore. Misurato al Task 8 su
        questo carico — lotti da 500, ventimila documenti per configurazione, tre giri
        alternati sullo stack 01 — le mediane per lotto stanno fra 2,48 e 2,70 ms **in
        entrambe le configurazioni**, e i totali si sovrappongono
        ([M-021](../../../../app/docs/Sources.md#m-021)). Non c'è niente da guadagnare, e
        `ordered=True` ha in cambio un errore più semplice da leggere.

        Che cosa la misura **non** dice: è un'istanza singola su loopback, senza rete e
        senza `w: majority`. Su un replica set attraverso una rete vera, e soprattutto su
        uno sharded cluster dove un lotto si spezza fra shard e `ordered=True` costringe a
        rispettarne la sequenza, il confronto può cambiare del tutto. Se un giorno il
        Blocco 3 mostrerà scritture lente, questa è la prima riga da rimisurare.
        """
        copie = [dict(documento) for documento in documenti]
        if not copie:
            return 0
        return len(self.collezione.insert_many(copie).inserted_ids)

    def find_page(
        self, filtro: Documento, salta: int = 0, quanti: int = 20
    ) -> tuple[Documento, ...]:
        """Una pagina, **ordinata per `_id`**.

        L'ordinamento non è un abbellimento. `skip` e `limit` senza `sort` chiedono al
        server pagine di un insieme che non ha ordine definito: due chiamate consecutive
        possono restituire lo stesso documento due volte e un altro mai, e nessuna delle
        due sbaglia. Una pagina che non è stabile non è una pagina.

        Su `_id` perché è l'unico campo che c'è sempre, ha sempre un indice e non richiede
        di conoscere lo schema. Il prezzo, dichiarato: l'ordine è quello degli `_id`, che
        coincide con quello d'inserimento solo se gli `_id` crescono — vero per il dataset
        di demo, dove `_id` **è** l'indice, e non vero in generale.

        **`quanti <= 0` restituisce niente, e va intercettato prima del driver.** Per
        MongoDB `limit(0)` significa *nessun limite* — «A `limit()` value of 0 (i.e.
        `.limit(0)`) is equivalent to setting no limit»
        ([A-011](../../../../app/docs/Sources.md#a-011)) — quindi la traduzione ovvia
        restituirebbe la collezione intera a chi ne ha chiesti zero. Il valore non lo digita
        nessuno, ci si arriva per sottrazione — quante righe restano nella finestra, quanti
        mancano alla fine dell'elenco — e il caso limite di un calcolo è precisamente quello
        che nessuno prova a mano. La guardia è stata scritta **dopo** averla vista servire:
        la stessa verifica del contratto passa sul doppio e fallisce qui
        ([M-022](../../../../app/docs/Sources.md#m-022)).
        """
        if quanti <= 0:
            return ()
        pagina = (
            self.collezione.find(dict(filtro))
            .sort("_id", ASCENDING)
            .skip(salta)
            .limit(quanti)
        )
        return tuple(pagina)

    def count(self, filtro: Documento) -> int:
        """`count_documents`, che conta davvero.

        Non `estimated_document_count`, che legge i metadati della collezione: è molto più
        veloce e su uno sharded cluster può contare anche i documenti **orfani**, cioè
        quelli rimasti su uno shard dopo una migrazione. Il Blocco 2 confronta le scritture
        confermate con quelle ritrovate, e una stima che sbaglia di qualche unità
        trasformerebbe quel confronto in rumore.
        """
        return self.collezione.count_documents(dict(filtro))

    def aggregate(self, pipeline: Sequence[Documento]) -> tuple[Documento, ...]:
        """Esegue la pipeline e raccoglie tutto.

        La porta restituisce una tupla, quindi il cursore si consuma qui. È una scelta che
        va conosciuta: una `$match` senza indice su cinquantamila documenti materializza
        cinquantamila dizionari in memoria. Per le pipeline di questa applicazione —
        conteggi e raggruppamenti, che escono in poche righe — non è un problema; per una
        che restituisse l'intera collezione lo sarebbe, e la risposta giusta sarebbe
        cambiare la porta, non nascondere il cursore dietro un generatore che la firma non
        dichiara.
        """
        return tuple(self.collezione.aggregate([dict(stadio) for stadio in pipeline]))
