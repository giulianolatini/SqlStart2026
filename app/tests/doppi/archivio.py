"""Gli archivi di prova: quello che conserva davvero, quello che rompe, quello che rallenta.

Tre `DocumentStore`, e due dei tre avvolgono il primo invece di rifarlo. La composizione
non è eleganza fine a se stessa: è la dimostrazione che le porte `Protocol` reggono, e
costa meno di un doppio che finge di essere tutte e tre le cose a comando.
"""

from typing import Mapping, Sequence

from mongolab.domain.modelli import Documento
from mongolab.domain.porte import DocumentStore

from tests.doppi.orologio import FakeClock

__all__ = [
    "ArchivioCheRompe",
    "ArchivioLento",
    "InMemoryStore",
    "NonSupportato",
    "ScritturaRifiutata",
]


class NonSupportato(NotImplementedError):
    """Il doppio non sa fare ciò che gli è stato chiesto, e invece di arrangiarsi lo dice.

    Ogni volta che questa eccezione arriva in faccia a qualcuno, la risposta giusta è la
    stessa: insegnare al doppio l'operatore o lo stadio che manca, **insieme alla prova
    che lo verifica**. Non c'è mai una seconda risposta buona, e in particolare non lo è
    riscrivere la prova per chiedere qualcosa di più semplice: sarebbe provare ciò che il
    doppio sa fare invece di ciò che il codice deve fare.
    """


class InMemoryStore:
    """Un `DocumentStore` che tiene i documenti in una lista e li interroga sul serio.

    **Conserva, non finge.** `insert_many` non restituisce `len(documenti)` per finta:
    li mette da parte, e `count` li ritrova. È la condizione perché la misura del Blocco 2
    — scritture confermate contro scritture ritrovate — sia provabile su un doppio, perché
    un archivio che confermasse senza conservare farebbe coincidere i due numeri sempre, e
    la scena delle scritture perse diventerebbe non falsificabile.

    **Parla un dialetto piccolo, e lo dichiara.** Del linguaggio di interrogazione conosce
    l'uguaglianza su campi di primo livello; della pipeline conosce `$match`, `$limit` e
    `$count`. Tutto il resto solleva `NonSupportato` **nominando ciò che non sa fare**.
    L'alternativa — ignorare in silenzio un `$gt` che non capisce — restituirebbe tutti i
    documenti e renderebbe verde la prova che lo usa: verde per il motivo sbagliato, senza
    che nessuno abbia scritto una riga di codice difettoso. Un doppio che tace su ciò che
    non sa è più pericoloso di uno che non c'è.

    **Tre casi in cui l'ovvio diverge da MongoDB**, e le risposte sono diverse perché
    diverse sono le domande:

    - `{"campo": None}` lo **sa fare**, e apposta. In MongoDB corrisponde sia ai documenti
      con `null` sia a quelli **senza quel campo**: qui `documento.get(chiave)` indovina
      quella semantica e `chiave in documento` la sbaglia. Fra due implementazioni
      ugualmente ovvie ce n'è una giusta, quindi si sceglie con la fonte in mano — il
      manuale, in `Sources.md` A-006 — e con la prova accanto;
    - `{"campo": {...}}` senza operatori, cioè il confronto con un sottodocumento intero,
      lo **rifiuta**. MongoDB lo risolve «including the field order» e l'uguaglianza fra
      `dict` di Python l'ordine lo ignora: nessuna implementazione ovvia è quella giusta,
      e imitare male è peggio che dichiarare di non saper fare (A-007);
    - `$count` su **zero** documenti in ingresso non emette niente, e non emette lo zero.
      È la divergenza che il doppio aveva davvero, scoperta al Task 8 dal contratto
      condiviso e corretta con la misura in mano (M-017). Val la pena di rileggerla come
      un caso della [nota 155](../../../docs/registro-operativo-sviluppo.md): lì il
      difetto era una risposta mancante scambiata per uno zero, qui è uno zero inventato
      dove la risposta manca. Lo stesso errore, dai due lati.

    **Una divergenza che resta, e va conosciuta**: i documenti tornano nell'ordine in cui
    sono stati inseriti, mentre MongoDB senza `sort` esplicito non promette **nessun**
    ordine. Una prova che si appoggia a quest'ordine passa qui e può fallire al Task 8
    contro lo stack vero. Quando l'ordine è parte di ciò che si sta provando va chiesto,
    non ereditato dal doppio.

    Non eredita `DocumentStore` e non lo importa: la conformità è strutturale, e a
    verificarla è `mypy --strict` dove una prova annota `store: DocumentStore`.
    """

    def __init__(self) -> None:
        self._documenti: list[dict[str, object]] = []

    def insert_many(self, documenti: Sequence[Documento]) -> int:
        # La copia è ciò che rende l'inserimento una consegna invece che una condivisione:
        # il generatore di carico del Task 5 riuserà lo stesso dizionario a ogni giro, e
        # l'adattatore vero serializza in BSON al momento della chiamata.
        self._documenti.extend(dict(documento) for documento in documenti)
        return len(documenti)

    def find_page(
        self, filtro: Documento, salta: int = 0, quanti: int = 20
    ) -> tuple[Documento, ...]:
        scelti = self._scelti(filtro)
        return tuple(dict(documento) for documento in scelti[salta : salta + quanti])

    def count(self, filtro: Documento) -> int:
        return len(self._scelti(filtro))

    def aggregate(self, pipeline: Sequence[Documento]) -> tuple[Documento, ...]:
        risultato = [dict(documento) for documento in self._documenti]
        for stadio in pipeline:
            risultato = self._applica(stadio, risultato)
        return tuple(risultato)

    # --- Il dialetto conosciuto -------------------------------------------------------

    def _scelti(self, filtro: Documento) -> list[dict[str, object]]:
        return [
            documento
            for documento in self._documenti
            if self._corrisponde(documento, filtro)
        ]

    def _corrisponde(self, documento: Mapping[str, object], filtro: Documento) -> bool:
        for chiave, atteso in filtro.items():
            self._rifiuta_cio_che_non_sa(chiave, atteso)
            if atteso is None:
                # `{campo: null}` corrisponde al `null` esplicito **e** al campo assente:
                # è la semantica del manuale, non un effetto collaterale di `get`.
                if documento.get(chiave) is not None:
                    return False
            elif chiave not in documento or documento[chiave] != atteso:
                return False
        return True

    @staticmethod
    def _rifiuta_cio_che_non_sa(chiave: str, atteso: object) -> None:
        if chiave.startswith("$"):
            raise NonSupportato(
                f"InMemoryStore non conosce l'operatore di filtro {chiave}: "
                "insegnaglielo insieme alla prova che lo verifica."
            )
        if "." in chiave:
            raise NonSupportato(
                f"InMemoryStore non sa scendere in un percorso annidato ({chiave!r}): "
                "insegnaglielo insieme alla prova che lo verifica."
            )
        if isinstance(atteso, Mapping):
            operatori = sorted(
                nome
                for nome in atteso
                if isinstance(nome, str) and nome.startswith("$")
            )
            if operatori:
                raise NonSupportato(
                    f"InMemoryStore non conosce l'operatore {operatori[0]} "
                    f"(campo {chiave!r}): insegnaglielo insieme alla prova che lo verifica."
                )
            raise NonSupportato(
                f"InMemoryStore non confronta sottodocumenti (campo {chiave!r}): MongoDB "
                "lo fa rispettando l'ordine delle chiavi, i dict di Python no, e qui i due "
                "darebbero risposte diverse sullo stesso dato."
            )

    def _applica(
        self, stadio: Documento, documenti: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        if len(stadio) != 1:
            raise NonSupportato(
                f"uno stadio dichiara un operatore solo, questo ne dichiara {len(stadio)}: "
                f"{sorted(stadio)}."
            )
        [(nome, argomento)] = stadio.items()
        match nome:
            case "$match":
                filtro = self._come_documento(nome, argomento)
                return [
                    documento
                    for documento in documenti
                    if self._corrisponde(documento, filtro)
                ]
            case "$limit":
                return documenti[: self._come_intero(nome, argomento)]
            case "$count":
                nome_campo = self._come_testo(nome, argomento)
                # Su zero documenti in ingresso, MongoDB non emette **niente**: né `$count`
                # né `$group {_id: null}` producono la riga con lo zero che SQL darebbe.
                # Misurato contro lo stack 01 al Task 8 ([M-017](../../docs/Sources.md#m-017)),
                # perché fin lì il doppio restituiva `[{campo: 0}]` e il contratto
                # condiviso l'ha smentito alla prima esecuzione. La differenza non è
                # accademica: chi legge `risultato[0]["quanti"]` passa nella suite veloce
                # e solleva `IndexError` contro il cluster.
                if not documenti:
                    return []
                return [{nome_campo: len(documenti)}]
        raise NonSupportato(
            f"InMemoryStore non conosce lo stadio {nome}: insegnaglielo insieme alla prova "
            "che lo verifica. Conosce $match, $limit e $count."
        )

    @staticmethod
    def _come_documento(stadio: str, argomento: object) -> Documento:
        if not isinstance(argomento, Mapping):
            raise NonSupportato(f"{stadio} vuole un documento, ha ricevuto {argomento!r}.")
        return argomento

    @staticmethod
    def _come_intero(stadio: str, argomento: object) -> int:
        if not isinstance(argomento, int) or isinstance(argomento, bool):
            raise NonSupportato(f"{stadio} vuole un intero, ha ricevuto {argomento!r}.")
        return argomento

    @staticmethod
    def _come_testo(stadio: str, argomento: object) -> str:
        if not isinstance(argomento, str):
            raise NonSupportato(f"{stadio} vuole il nome di un campo, ha ricevuto {argomento!r}.")
        return argomento


class ScritturaRifiutata(RuntimeError):
    """L'errore che `ArchivioCheRompe` solleva al posto del driver.

    Non imita `pymongo.errors.AutoReconnect` e non ne eredita, apposta: il codice sotto
    prova non deve riconoscere *quel* tipo — se lo facesse, il dominio saprebbe che
    esiste MongoDB. Ciò che deve fare è trattare qualunque eccezione come un fallimento
    di scrittura, e questo tipo esiste per verificare proprio quella genericità.
    """


class ArchivioCheRompe:
    """Un `DocumentStore` che rifiuta le scritture, e per il resto delega.

    Il Task 4 ha lasciato aperto un debito preciso: nessun doppio sapeva rompersi, e la
    politica dei tentativi non è provabile contro un archivio che riesce sempre. La
    regola è che la capacità arriva **insieme** alla prova che ne ha bisogno — mai
    semplificando la prova — ed è quello che succede qui.

    **Avvolge invece di sostituire.** Non reimplementa la memoria: tiene dentro di sé un
    altro `DocumentStore` vero e gli passa tutto ciò che non deve fallire. Le letture
    quindi funzionano davvero anche durante il guasto, che è la condizione per la misura
    del Blocco 2 — confermate contro ritrovate — e per una scena in cui il carico continua
    mentre le scritture non passano.

    **`dentro` è annotato con la porta, non con `InMemoryStore`.** È una scelta che si
    paga da sola: mypy verifica al punto di costruzione che l'archivio avvolto rispetti
    `DocumentStore`, e i doppi si compongono — `ArchivioLento(ArchivioCheRompe(...))` è un
    archivio lento **e** guasto senza che nessuno dei due sappia dell'altro.

    `guasti` è quante scritture fallire prima di lasciar passare le altre; `None`, il
    valore predefinito, vuol dire **sempre**, che è il caso della resa definitiva. Il
    conteggio non è protetto da un lucchetto: questo doppio è pensato per le prove a un
    solo scrittore, dove la sequenza dei guasti è parte di ciò che si asserisce.
    """

    def __init__(
        self,
        dentro: DocumentStore,
        guasti: int | None = None,
        motivo: str = "il server ha rifiutato la scrittura",
    ) -> None:
        self._dentro = dentro
        self._rimasti = guasti
        self._motivo = motivo
        self.tentate = 0
        """Quante scritture sono state chiese in tutto, riuscite o no."""

    def insert_many(self, documenti: Sequence[Documento]) -> int:
        self.tentate += 1
        if self._rimasti is None:
            raise ScritturaRifiutata(self._motivo)
        if self._rimasti > 0:
            self._rimasti -= 1
            raise ScritturaRifiutata(self._motivo)
        return self._dentro.insert_many(documenti)

    def find_page(
        self, filtro: Documento, salta: int = 0, quanti: int = 20
    ) -> tuple[Documento, ...]:
        return self._dentro.find_page(filtro, salta, quanti)

    def count(self, filtro: Documento) -> int:
        return self._dentro.count(filtro)

    def aggregate(self, pipeline: Sequence[Documento]) -> tuple[Documento, ...]:
        return self._dentro.aggregate(pipeline)


class ArchivioLento:
    """Un `DocumentStore` che fa **costare tempo** ogni operazione, e per il resto delega.

    Senza di lui la latenza non è provabile. `FakeClock` non avanza da solo — è la sua
    virtù — quindi contro `InMemoryStore` ogni scrittura dura zero millisecondi, e una
    prova che asserisse `durata_ms == 0.0` verificherebbe l'immobilità dell'orologio
    invece della misura. Qui il tempo passa **dentro** la chiamata, che è dove passa
    anche nella realtà, e l'asserzione diventa un numero scelto: `costo_ms=12.0`.

    Prende `FakeClock` e non `Clock`, e la differenza è sostanziale: `avanza` non è nella
    porta e non deve esserci. Il codice di produzione può solo **chiedere** di dormire; a
    far passare il tempo mentre lavora è il mondo, e in una prova il mondo è questo
    doppio. Tenerli distinti è ciò che permette a `FakeClock.attese` di contenere solo il
    backoff.

    Un limite da conoscere: `timedelta` arrotonda al microsecondo, quindi un costo sotto
    il millesimo di millisecondo sparisce. Per le latenze di rete che questa applicazione
    misura non è un problema; per un'ipotetica prova su microsecondi lo sarebbe.
    """

    def __init__(self, dentro: DocumentStore, orologio: FakeClock, costo_ms: float) -> None:
        self._dentro = dentro
        self._orologio = orologio
        self._costo_ms = costo_ms

    def insert_many(self, documenti: Sequence[Documento]) -> int:
        self._costa()
        return self._dentro.insert_many(documenti)

    def find_page(
        self, filtro: Documento, salta: int = 0, quanti: int = 20
    ) -> tuple[Documento, ...]:
        self._costa()
        return self._dentro.find_page(filtro, salta, quanti)

    def count(self, filtro: Documento) -> int:
        self._costa()
        return self._dentro.count(filtro)

    def aggregate(self, pipeline: Sequence[Documento]) -> tuple[Documento, ...]:
        self._costa()
        return self._dentro.aggregate(pipeline)

    def _costa(self) -> None:
        self._orologio.avanza(self._costo_ms / 1000)
