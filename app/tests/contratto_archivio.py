"""Il contratto di `DocumentStore`, scritto una volta e verificato su due implementazioni.

Il Passo 4 del Task 8 dice perché esiste: «un doppio che si comporta diversamente
dall'originale è un doppio che mente, e questo passo è il modo di accorgersene». Le
funzioni qui dentro girano contro `InMemoryStore` nella suite veloce
(`tests/unit/test_contratto_archivio.py`) e contro `PymongoStore` contro uno stack vero
(`tests/integration/test_contratto_archivio.py`). Un rosso da una parte sola è la notizia.

**Che cosa NON sta qui.** Il contratto è l'insieme dei comportamenti che le due
implementazioni devono avere **identici**, e non è tutto ciò che ciascuna sa fare. Dove
divergono — e divergono, in cinque punti misurati — le prove stanno nel file di
integrazione sotto il titolo «Dove il doppio e l'originale non coincidono», e ognuna
asserisce **entrambi** i comportamenti. Una divergenza che nessuna prova nomina è una
divergenza che qualcuno scoprirà in scena.

**Una condizione che il contratto si porta dietro.** `InMemoryStore` restituisce i
documenti nell'ordine in cui li ha ricevuti; MongoDB senza `sort` esplicito non promette
nessun ordine, e `PymongoStore` ordina per `_id` proprio per avere una pagina stabile. Le
due cose coincidono **solo se gli `_id` crescono nell'ordine di inserimento**, che è la
forma di tutti i dati di prova qui dentro e del dataset di demo (`_id` è l'indice). Non è
un dettaglio dell'ambiente: è un'ipotesi, ed è scritta perché chi aggiunge una verifica
con `_id` sparsi trovi il rosso spiegato invece che misterioso.

Le funzioni prendono un archivio **vuoto** e non restituiscono niente: chi le chiama
fornisce l'implementazione e si occupa di lasciarla pulita.
"""

from datetime import UTC, datetime
from typing import Callable, Final, Sequence

from mongolab.domain.modelli import Documento
from mongolab.domain.porte import DocumentStore

__all__ = ["VERIFICHE", "ordini"]


def ordini() -> list[Documento]:
    """Tre documenti che bastano a distinguere «filtra» da «restituisce tutto».

    Sono gli stessi del Task 4, spostati qui: erano già il contratto, scritti in un posto
    che ne conosceva una sola implementazione.
    """
    return [
        {"_id": 1, "stato": "confermato", "importo": 10},
        {"_id": 2, "stato": "annullato", "importo": 20},
        {"_id": 3, "stato": "confermato", "importo": 30},
    ]


def conferma_quanti_ne_ha_inseriti_e_li_conserva(archivio: DocumentStore) -> None:
    """Il conteggio di ritorno e ciò che resta dentro raccontano la stessa cosa.

    È la coppia di numeri su cui poggia la misura del Blocco 2 — confermate contro
    ritrovate — e un archivio che restituisse `len(documenti)` senza conservarli le
    farebbe coincidere sempre, cioè renderebbe le scritture perse impossibili da provare.
    """
    assert archivio.insert_many(ordini()) == 3
    assert archivio.count({}) == 3


def non_tiene_il_documento_di_chi_lo_ha_chiamato(archivio: DocumentStore) -> None:
    """Inserire è consegnare, non condividere.

    Il carico riusa lo stesso dizionario cambiandogli un campo a ogni giro, perché è così
    che si scrive un generatore di documenti. Se l'archivio ne tenesse il riferimento, i
    documenti «inseriti» cambierebbero dopo l'inserimento.

    Contro l'originale la prova ha un secondo bersaglio, che il doppio non ha: pymongo
    **scrive** `_id` dentro il dizionario che riceve, se non ce l'ha. `PymongoStore` copia
    prima di consegnare al driver, e senza quella copia questa asserzione fallirebbe sul
    campo aggiunto invece che sul campo cambiato.
    """
    documento: dict[str, object] = {"stato": "confermato"}
    archivio.insert_many([documento])

    documento["stato"] = "annullato"

    assert archivio.count({"stato": "confermato"}) == 1
    assert archivio.count({"stato": "annullato"}) == 0
    assert "_id" not in documento, "il driver ha scritto nel documento di chi ha chiamato"


def filtra_per_uguaglianza_invece_di_contare_tutto(archivio: DocumentStore) -> None:
    archivio.insert_many(ordini())

    assert archivio.count({"stato": "confermato"}) == 2
    assert archivio.count({"stato": "annullato"}) == 1
    assert archivio.count({"stato": "in dubbio"}) == 0
    # Due condizioni si sommano, e un campo che il documento non ha non corrisponde.
    assert archivio.count({"stato": "confermato", "importo": 30}) == 1
    assert archivio.count({"spedito": True}) == 0


def cerca_i_campi_assenti_come_fa_mongodb(archivio: DocumentStore) -> None:
    """`{"campo": None}` corrisponde a chi ha `null` **e** a chi il campo non ce l'ha.

    È la verifica per cui questo file esiste. Il manuale è esplicito — «matches documents
    that contain the `metacritic` field with a `null` value **or** do not contain the
    `metacritic` field» ([A-006](../docs/Sources.md#a-006)) — e al Task 4 il doppio è stato
    scritto apposta per imitarla, con la fonte in mano. Ma «l'abbiamo letta bene» resta
    una scommessa finché la stessa asserzione non passa anche sul cluster: qui la
    scommessa si chiude.
    """
    archivio.insert_many(
        [
            {"_id": 1, "annullato_il": None},
            {"_id": 2},
            {"_id": 3, "annullato_il": "2026-09-03"},
        ]
    )

    trovati = archivio.find_page({"annullato_il": None})

    assert [documento["_id"] for documento in trovati] == [1, 2]


def impagina_saltando_e_limitando(archivio: DocumentStore) -> None:
    archivio.insert_many(ordini())

    prima = archivio.find_page({}, salta=0, quanti=2)
    seconda = archivio.find_page({}, salta=2, quanti=2)

    assert [documento["_id"] for documento in prima] == [1, 2]
    assert [documento["_id"] for documento in seconda] == [3]
    # La pagina è una tupla perché lo dice la porta: chi la riceve non deve poterla
    # allungare credendo di aver caricato di più.
    assert isinstance(prima, tuple)


def impagina_quello_che_il_filtro_ha_scelto(archivio: DocumentStore) -> None:
    """Filtro e pagina si compongono, e nell'ordine giusto.

    Un archivio che impaginasse prima e filtrasse poi restituirebbe pagine più corte del
    dovuto e, con `salta`, salterebbe documenti che il filtro avrebbe tenuto: un errore
    che non si vede finché tutte le prove chiedono la prima pagina di tutto.
    """
    archivio.insert_many(ordini())

    pagina = archivio.find_page({"stato": "confermato"}, salta=1, quanti=10)

    assert [documento["_id"] for documento in pagina] == [3]


def una_pagina_di_zero_documenti_e_vuota(archivio: DocumentStore) -> None:
    """Chiedere zero documenti ne restituisce zero. Sembra ovvio, e non lo è.

    `quanti=0` arriva da un calcolo — quante righe restano nella finestra del terminale,
    quanti ne mancano alla fine dell'elenco — e il caso limite di un calcolo è il valore
    che nessuno digita a mano. Nel doppio `scelti[salta:salta+0]` fa la cosa giusta da
    sola. Nel driver **no**: `limit(0)` in MongoDB vuol dire *nessun limite*, quindi la
    traduzione ovvia restituirebbe la collezione intera proprio dove il chiamante ne
    chiedeva zero. Delle due implementazioni ugualmente ovvie, qui una è pericolosa.
    """
    archivio.insert_many(ordini())

    assert archivio.find_page({}, quanti=0) == ()
    assert archivio.find_page({}, salta=1, quanti=0) == ()
    # E non è che «zero» sia diventato un modo per non leggere niente mai: la riga dopo
    # deve tornare a leggere, altrimenti la guardia avrebbe rotto il caso normale.
    assert len(archivio.find_page({}, quanti=2)) == 2


def restituisce_documenti_nuovi_a_ogni_lettura(archivio: DocumentStore) -> None:
    """Leggere non dà accesso a ciò che sta dentro.

    Il commento che il Task 4 aveva scritto su questa prova era una previsione: «pymongo
    costruisce un dizionario nuovo a ogni documento che decodifica». Adesso non è più una
    previsione.
    """
    archivio.insert_many(ordini())

    prima = archivio.find_page({})
    seconda = archivio.find_page({})

    assert prima == seconda
    assert prima[0] is not seconda[0]


def esegue_gli_stadi_di_aggregazione_del_dialetto_comune(archivio: DocumentStore) -> None:
    """`$match`, `$limit`, `$count`: i tre che il doppio conosce, e che qui devono coincidere.

    Il doppio ne conosce solo tre e l'originale li conosce tutti: quello che si verifica
    qui è l'intersezione, che è precisamente ciò che il talk può permettersi di provare
    contro un archivio in memoria.
    """
    archivio.insert_many(ordini())

    assert archivio.aggregate(
        [{"$match": {"stato": "confermato"}}, {"$count": "quanti"}]
    ) == ({"quanti": 2},)
    assert [
        documento["_id"] for documento in archivio.aggregate([{"$limit": 2}])
    ] == [1, 2]


def un_conteggio_su_niente_e_zero_non_un_errore(archivio: DocumentStore) -> None:
    """L'archivio vuoto risponde, non protesta.

    La cronaca interroga il cluster prima che il carico cominci: se questo caso sollevasse,
    il primo fotogramma della scena sarebbe una traccia di stack.
    """
    assert archivio.count({}) == 0
    assert archivio.find_page({}) == ()
    assert archivio.aggregate([{"$count": "quanti"}]) == ()


def inserire_niente_non_e_un_errore(archivio: DocumentStore) -> None:
    """Zero documenti, zero confermati, nessuna eccezione.

    Contro l'originale non è gratis: `pymongo` solleva `InvalidOperation` su una lista
    vuota, quindi `PymongoStore` deve prevedere il caso. Il carico ci arriva davvero, il
    giorno in cui l'ultimo turno di un thread è vuoto perché i documenti non si dividono
    esattamente per il numero di scrittori.
    """
    assert archivio.insert_many([]) == 0
    assert archivio.count({}) == 0


def i_tipi_tornano_indietro_come_sono_andati(archivio: DocumentStore) -> None:
    """Il giro d'andata e ritorno dei tipi che il dataset di demo usa davvero.

    Il `datetime` è quello che conta, ed è l'unico che può tornare **diverso** senza che
    nessuno sollevi: BSON conserva un istante in millisecondi, e un client costruito senza
    `tz_aware=True` lo riconsegna **ingenuo**. Un confronto fra un `datetime` consapevole
    del fuso e uno ingenuo in Python solleva `TypeError`; un confronto fra due ingenui
    passa e sbaglia di due ore. `PymongoStore` esiste anche per garantire che questo caso
    non capiti mai a chi sta sopra.
    """
    istante = datetime(2026, 9, 18, 9, 30, tzinfo=UTC)
    originale: Documento = {
        "_id": 1,
        "testo": "Ancona",
        "intero": 42,
        "decimale": 1234.56,
        "vero": True,
        "niente": None,
        "elenco": [1, 2, 3],
        "quando": istante,
    }

    archivio.insert_many([originale])
    [riletto] = archivio.find_page({})

    assert riletto["testo"] == "Ancona"
    assert riletto["intero"] == 42
    assert riletto["decimale"] == 1234.56
    assert riletto["vero"] is True
    assert riletto["niente"] is None
    assert riletto["elenco"] == [1, 2, 3]

    quando = riletto["quando"]
    assert isinstance(quando, datetime)
    assert quando.tzinfo is not None, "il datetime è tornato ingenuo: manca tz_aware=True"
    assert quando == istante


VERIFICHE: Final[Sequence[Callable[[DocumentStore], None]]] = (
    conferma_quanti_ne_ha_inseriti_e_li_conserva,
    non_tiene_il_documento_di_chi_lo_ha_chiamato,
    filtra_per_uguaglianza_invece_di_contare_tutto,
    cerca_i_campi_assenti_come_fa_mongodb,
    impagina_saltando_e_limitando,
    impagina_quello_che_il_filtro_ha_scelto,
    una_pagina_di_zero_documenti_e_vuota,
    restituisce_documenti_nuovi_a_ogni_lettura,
    esegue_gli_stadi_di_aggregazione_del_dialetto_comune,
    un_conteggio_su_niente_e_zero_non_un_errore,
    inserire_niente_non_e_un_errore,
    i_tipi_tornano_indietro_come_sono_andati,
)
"""L'elenco è esplicito, non raccolto per prefisso con `dir()`.

Una raccolta automatica sembra più comoda e ha un difetto che si paga una volta sola: una
verifica scritta male — nome fuori schema, importata da un altro modulo — sparisce
dall'elenco senza che niente diventi rosso, e la copertura cala in silenzio. Dodici righe
da tenere aggiornate sono il prezzo di sapere quante sono.
"""
