"""Il generatore deterministico: stesso seme, stesso dataset, in qualunque ordine.

La prova che vale più di tutte le altre è `test_il_documento_non_dipende_dall_ordine`.
Il seed JavaScript degli stack è deterministico perché è **sequenziale**: un solo flusso
di numeri, un documento dopo l'altro, e il documento numero mille dipende dai
novecentonovantanove di prima. Qui non si può, e non è una questione di gusto:
`WorkloadRunner` scrive da più thread e assegna gli indici a blocchi, quindi l'ordine in
cui i documenti vengono **chiesti** non è quello dei loro indici. Un generatore a flusso
darebbe dataset diversi a ogni corsa pur avendo lo stesso seme, cioè esattamente ciò che
il Passo 2 del Task 8 esiste per impedire.
"""

import random
import threading
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Mapping

import pytest

from mongolab.application.workload import Genera
from mongolab.domain.modelli import Documento
from mongolab.infrastructure.generatore import (
    CITTA,
    EPOCA,
    SEME_DEL_TALK,
    STATI,
    DataGenerator,
)

# --- Determinismo ---------------------------------------------------------------------


def test_lo_stesso_seme_produce_lo_stesso_documento() -> None:
    uno = DataGenerator(seme=7)
    altro = DataGenerator(seme=7)

    assert uno.documento(42) == altro.documento(42)


def test_semi_diversi_producono_documenti_diversi() -> None:
    """Altrimenti il seme sarebbe un parametro decorativo.

    Il confronto esclude `_id`, che è l'indice e per costruzione coincide: se restasse
    dentro, due generatori che ignorassero il seme in tutto il resto passerebbero lo
    stesso questa prova.
    """
    uno = dict(DataGenerator(seme=1).documento(42))
    altro = dict(DataGenerator(seme=2).documento(42))
    del uno["_id"], altro["_id"]

    assert uno != altro


def test_il_documento_non_dipende_dall_ordine_in_cui_e_stato_chiesto() -> None:
    """La ragione per cui questo generatore non è il seed JavaScript tradotto.

    Un generatore a flusso — stato interno che avanza a ogni chiamata, come
    `10-dati-demo.js` — passerebbe le due prove qui sopra e fallirebbe questa. E
    fallirebbe *in produzione* nel modo peggiore: `WorkloadRunner` con due scrittori
    chiede gli indici intrecciati, quindi il dataset uscirebbe diverso a ogni corsa senza
    che nessuno abbia cambiato il seme.
    """
    generatore = DataGenerator(seme=SEME_DEL_TALK)
    in_ordine = [generatore.documento(indice) for indice in range(200)]

    mescolati = list(range(200))
    random.Random(0).shuffle(mescolati)
    alla_rinfusa = {indice: generatore.documento(indice) for indice in mescolati}

    assert [alla_rinfusa[indice] for indice in range(200)] == in_ordine


def test_due_generatori_con_lo_stesso_seme_non_si_disturbano() -> None:
    """Intrecciare le chiamate di due generatori gemelli non cambia niente.

    È la stessa proprietà della prova precedente vista da fuori: se ci fosse uno stato
    interno condiviso o avanzante, alternare le due istanze lo farebbe emergere.
    """
    uno = DataGenerator(seme=SEME_DEL_TALK)
    altro = DataGenerator(seme=SEME_DEL_TALK)

    alternati = [(uno.documento(i), altro.documento(i)) for i in range(50)]

    assert all(sinistro == destro for sinistro, destro in alternati)


def test_il_generatore_regge_piu_thread() -> None:
    """`WorkloadRunner` lo chiamerà da più thread, quindi va provato da più thread.

    Non è la ripetizione della prova sull'ordine: quella esclude uno stato che *avanza*,
    questa esclude uno stato che si *corrompe*. Un generatore con un attributo scritto e
    riletto fra due istruzioni passa la prima e produce qui documenti che non
    corrispondono a nessun indice.
    """
    generatore = DataGenerator(seme=SEME_DEL_TALK)
    atteso = [generatore.documento(indice) for indice in range(400)]
    ottenuto: dict[int, Documento] = {}
    blocco = threading.Lock()

    def lavora(dal: int) -> None:
        for indice in range(dal, 400, 4):
            documento = generatore.documento(indice)
            with blocco:
                ottenuto[indice] = documento

    thread = [threading.Thread(target=lavora, args=(quale,)) for quale in range(4)]
    for uno in thread:
        uno.start()
    for uno in thread:
        uno.join()

    assert [ottenuto[indice] for indice in range(400)] == atteso


# --- La forma del documento -----------------------------------------------------------


def test_il_documento_ha_i_campi_del_dataset_degli_stack() -> None:
    """Gli stessi sette campi di `10-dati-demo.js`, né uno di più né uno di meno.

    Non è simmetria per bellezza: le interrogazioni della demo — `{citta: "Ancona"}`,
    l'indice su `stato`, la chiave di shard su `_id` — devono valere sui documenti che
    l'applicazione scrive *e* su quelli che il seed ha caricato. Un campo in meno qui
    farebbe passare una query in scena e non l'altra.
    """
    documento = DataGenerator().documento(0)

    assert sorted(documento) == [
        "_id",
        "citta",
        "cliente",
        "data",
        "importo",
        "righe",
        "stato",
    ]


def test_l_id_e_l_indice_che_e_stato_chiesto() -> None:
    """Il legame che rende verificabile «nessun documento perso né duplicato».

    `WorkloadRunner` assegna a ogni documento un indice globale distinto; se `_id` non ne
    fosse la copia, contare i documenti scritti non direbbe più quali mancano.
    """
    generatore = DataGenerator()

    assert generatore.documento(0)["_id"] == 0
    assert generatore.documento(49_999)["_id"] == 49_999


def test_i_valori_stanno_negli_intervalli_dichiarati() -> None:
    for indice in range(0, 5000, 7):
        documento = DataGenerator().documento(indice)

        cliente = documento["cliente"]
        assert isinstance(cliente, str)
        assert cliente.startswith("cliente-") and len(cliente) == len("cliente-0000")

        assert documento["citta"] in CITTA
        assert documento["stato"] in STATI

        importo = documento["importo"]
        assert isinstance(importo, float)
        assert 0.0 <= importo < 5000.0
        # Due decimali esatti: è un importo, e `round` a due deve lasciarlo com'è.
        assert round(importo, 2) == importo

        righe = documento["righe"]
        assert isinstance(righe, int)
        assert 1 <= righe <= 5


def test_la_data_e_consapevole_del_fuso_e_sta_nella_finestra() -> None:
    """UTC dichiarato, non «ora locale che sembra UTC».

    BSON conserva un istante, non un fuso: un `datetime` ingenuo verrebbe interpretato
    come UTC dal driver e riletto come UTC, e sulla macchina di chi presenta — due ore
    avanti d'estate — le date della cronaca scivolerebbero di due ore senza che nulla
    fallisca.
    """
    finestra = timedelta(days=240)

    for indice in range(0, 2000, 13):
        data = DataGenerator().documento(indice)["data"]
        assert isinstance(data, datetime)
        assert data.tzinfo is UTC
        assert EPOCA <= data < EPOCA + finestra
        # Mezzanotte esatta: la data è epoca più un numero intero di giorni.
        assert (data - EPOCA) % timedelta(days=1) == timedelta(0)


# --- La qualità dei numeri, che è la lezione di V-013 ---------------------------------


def test_le_dieci_citta_escono_tutte_e_in_proporzioni_confrontabili() -> None:
    """La prova che il generatore sbagliato del seed JavaScript non avrebbe superato.

    La prima stesura di `10-dati-demo.js` usava un congruenziale lineare e sceglieva la
    città con `seme % 10`: i bit bassi di un LCG hanno periodo cortissimo, e il risultato
    misurato in V-013 furono cinque città con diecimila ordini e cinque con qualche
    decina. Il difetto non fa fallire niente — il dataset esiste, le query rispondono — e
    si vede solo guardando le proporzioni. Quindi si guardano.

    La forbice è larga apposta: ±25 % attorno alla quota attesa non è una misura di
    uniformità, è la soglia sotto la quale sta un difetto **strutturale**. Il caso di
    V-013 sarebbe finito a -99 %.
    """
    generatore = DataGenerator(seme=SEME_DEL_TALK)
    conti = Counter(str(generatore.documento(i)["citta"]) for i in range(10_000))

    assert set(conti) == set(CITTA)
    attesa = 10_000 / len(CITTA)
    for citta, quante in conti.items():
        assert 0.75 * attesa <= quante <= 1.25 * attesa, f"{citta}: {quante}"


def test_i_cinque_stati_escono_tutti_e_in_proporzioni_confrontabili() -> None:
    generatore = DataGenerator(seme=SEME_DEL_TALK)
    conti = Counter(str(generatore.documento(i)["stato"]) for i in range(10_000))

    assert set(conti) == set(STATI)
    attesa = 10_000 / len(STATI)
    for stato, quante in conti.items():
        assert 0.75 * attesa <= quante <= 1.25 * attesa, f"{stato}: {quante}"


def test_documenti_vicini_non_si_somigliano() -> None:
    """Indici consecutivi devono dare documenti scorrelati.

    È il rischio proprio di questo disegno, che il seed sequenziale non ha: siccome lo
    stato di partenza si ricava dall'indice, due indici vicini partono da stati vicini. Un
    mescolamento debole si vede qui — cento documenti di fila con la stessa città — e non
    si vedrebbe nella prova sulle proporzioni, che guarda diecimila documenti insieme.
    """
    generatore = DataGenerator(seme=SEME_DEL_TALK)
    citta = [str(generatore.documento(indice)["citta"]) for indice in range(100)]

    assert len(set(citta)) == len(CITTA)
    ripetizioni = sum(1 for prima, dopo in zip(citta, citta[1:]) if prima == dopo)
    # Con dieci città indipendenti la ripetizione attesa su 99 coppie è ~9,9.
    assert ripetizioni <= 25, f"{ripetizioni} ripetizioni consecutive su 99"


# --- Il lotto, e la porta -------------------------------------------------------------


def test_il_lotto_produce_gli_indici_richiesti_in_ordine() -> None:
    generatore = DataGenerator(seme=SEME_DEL_TALK)

    lotto = list(generatore.lotto(quanti=5, dal=100))

    assert [documento["_id"] for documento in lotto] == [100, 101, 102, 103, 104]
    assert lotto == [generatore.documento(indice) for indice in range(100, 105)]


def test_il_lotto_e_pigro() -> None:
    """Un iteratore, non una lista: cinquantamila documenti non stanno tutti in memoria.

    Il carico del Blocco 2 ne scrive a decine di migliaia, e materializzarli prima di
    cominciare sposterebbe il tempo dal cluster al generatore — falsando proprio la
    misura di latenza per cui il carico esiste.
    """
    lotto = DataGenerator().lotto(quanti=1_000_000_000)

    assert next(iter(lotto))["_id"] == 0


def test_un_lotto_negativo_protesta_subito_e_non_al_primo_giro() -> None:
    """Senza `list()` attorno, e la differenza è tutto il punto della prova.

    Se `lotto` fosse una funzione generatore, il `ValueError` non partirebbe alla
    chiamata: partirebbe al primo `next()`, cioè dentro il ciclo di scrittura, a thread
    già avviati e con l'errore che sembra arrivare dal carico invece che da chi l'ha
    configurato. La versione con `list()` attorno passa in entrambi i casi, quindi non
    prova niente — è la nota 159, una guardia si dimostra solo con il caso in cui la sua
    assenza si vedrebbe.
    """
    with pytest.raises(ValueError, match="quanti"):
        DataGenerator().lotto(quanti=-1)


def test_il_documento_e_una_funzione_Genera() -> None:
    """Il metodo si passa a `WorkloadRunner` così com'è, senza adattatori in mezzo.

    A verificarlo davvero è `mypy --strict` su questa annotazione; qui runtime si
    controlla soltanto che sia chiamabile con un indice e restituisca un documento.
    """
    genera: Genera = DataGenerator(seme=SEME_DEL_TALK).documento

    documento = genera(3)

    assert isinstance(documento, Mapping)
    assert documento["_id"] == 3


def test_il_documento_e_congelato_per_chi_lo_riceve() -> None:
    """Ogni chiamata restituisce un documento nuovo.

    `InMemoryStore` copia in ingresso apposta, ma `PymongoStore` no — è pymongo a
    serializzare al momento della chiamata. Se il generatore riusasse lo stesso
    dizionario, i documenti già accodati cambierebbero sotto i piedi di chi li sta
    scrivendo.
    """
    generatore = DataGenerator()

    assert generatore.documento(1) is not generatore.documento(1)
