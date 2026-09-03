"""L'archivio che conserva davvero i documenti, e dice quando non sa fare qualcosa."""

from typing import Mapping, Sequence

from mongolab.domain.modelli import Documento

__all__ = ["InMemoryStore", "NonSupportato"]


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

    **Due casi in cui l'ovvio diverge da MongoDB**, e le due risposte sono diverse perché
    diverse sono le domande:

    - `{"campo": None}` lo **sa fare**, e apposta. In MongoDB corrisponde sia ai documenti
      con `null` sia a quelli **senza quel campo**: qui `documento.get(chiave)` indovina
      quella semantica e `chiave in documento` la sbaglia. Fra due implementazioni
      ugualmente ovvie ce n'è una giusta, quindi si sceglie con la fonte in mano — il
      manuale, in `Sources.md` A-006 — e con la prova accanto;
    - `{"campo": {...}}` senza operatori, cioè il confronto con un sottodocumento intero,
      lo **rifiuta**. MongoDB lo risolve «including the field order» e l'uguaglianza fra
      `dict` di Python l'ordine lo ignora: nessuna implementazione ovvia è quella giusta,
      e imitare male è peggio che dichiarare di non saper fare (A-007).

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
                return [{self._come_testo(nome, argomento): len(documenti)}]
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
