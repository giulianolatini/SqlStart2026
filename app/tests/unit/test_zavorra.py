"""`--doc-size 2k`: documenti di una dimensione chiesta, misurata e non stimata.

Il tipo `Genera` di `application/workload.py` dichiara da sempre di essere «il gancio per
`--doc-size`», e fino al Task 10 non c'era niente attaccato a quel gancio. Questo modulo è
la cosa attaccata: prende un `Genera` qualunque e ne restituisce uno che produce documenti
della dimensione richiesta.

Due decisioni si provano qui. La prima è che la dimensione è **esatta e misurata**: il
documento viene codificato in BSON e la zavorra tagliata sul risultato, invece di
stimarne la lunghezza sommando i campi. La seconda è che la zavorra non è una fila di
`x`: WiredTiger comprime, e mille documenti di duemila `x` non occupano due megabyte.
"""

import bson
import pytest

from mongolab.infrastructure.generatore import SEME_DEL_TALK, DataGenerator
from mongolab.infrastructure.zavorra import (
    CAMPO_ZAVORRA,
    MASSIMO_BSON,
    byte_di,
    con_dimensione,
)


def test_un_numero_nudo_sono_byte() -> None:
    assert byte_di("512") == 512


def test_il_suffisso_k_e_millequarantotto() -> None:
    # 1024 e non 1000: è la convenzione che MongoDB usa per il proprio limite di 16 MB,
    # che vale 16 777 216 byte. Due unità diverse nello stesso discorso sarebbero peggio
    # di quella scomoda.
    assert byte_di("2k") == 2048
    assert byte_di("2K") == 2048


def test_il_suffisso_m_e_un_mebibyte() -> None:
    assert byte_di("1m") == 1024 * 1024


def test_il_limite_di_bson_e_quello_di_mongodb() -> None:
    assert MASSIMO_BSON == 16 * 1024 * 1024


def test_una_dimensione_oltre_il_limite_lo_nomina() -> None:
    with pytest.raises(ValueError) as caduta:
        byte_di("17m")
    detto = str(caduta.value)
    assert "16" in detto
    assert str(MASSIMO_BSON) in detto


def test_una_dimensione_nulla_e_rifiutata() -> None:
    with pytest.raises(ValueError):
        byte_di("0")


def test_una_dimensione_negativa_e_rifiutata() -> None:
    with pytest.raises(ValueError):
        byte_di("-1")


def test_una_forma_che_non_si_capisce_mostra_quelle_che_si_capiscono() -> None:
    with pytest.raises(ValueError) as caduta:
        byte_di("due kappa")
    detto = str(caduta.value)
    assert "due kappa" in detto
    # Il messaggio deve portare degli esempi, non solo il rifiuto.
    assert "2k" in detto


@pytest.mark.parametrize("byte", [256, 512, 1024, 2048, 4096, 65_536])
def test_il_documento_misura_esattamente_quanto_chiesto(byte: int) -> None:
    genera = con_dimensione(DataGenerator().documento, byte)
    for indice in (0, 1, 7, 999, 123_456):
        assert len(bson.encode(genera(indice))) == byte, indice


def test_vale_anche_per_il_documento_piu_piccolo_del_dominio() -> None:
    # `documento_progressivo` ha un campo solo. La zavorra deve funzionare su qualunque
    # `Genera`, non solo su quello del dataset di demo.
    from mongolab.application.workload import documento_progressivo

    genera = con_dimensione(documento_progressivo, 300)
    assert len(bson.encode(genera(42))) == 300


def test_una_dimensione_piu_piccola_del_documento_dice_i_due_numeri() -> None:
    genera = con_dimensione(DataGenerator().documento, 10)
    with pytest.raises(ValueError) as caduta:
        genera(0)
    detto = str(caduta.value)
    assert "10" in detto
    # E anche quanto misura il documento nudo, che è l'informazione che serve per
    # correggere l'opzione senza doverla indovinare per tentativi.
    minimo = len(bson.encode(DataGenerator().documento(0))) + len(CAMPO_ZAVORRA) + 7
    assert str(minimo) in detto or any(str(n) in detto for n in range(minimo - 2, minimo + 3))


def test_lo_stesso_seme_e_lo_stesso_indice_danno_lo_stesso_documento() -> None:
    primo = con_dimensione(DataGenerator().documento, 1024, seme=SEME_DEL_TALK)
    secondo = con_dimensione(DataGenerator().documento, 1024, seme=SEME_DEL_TALK)
    assert primo(17) == secondo(17)


def test_semi_diversi_danno_zavorre_diverse() -> None:
    primo = con_dimensione(DataGenerator().documento, 1024, seme=1)
    secondo = con_dimensione(DataGenerator().documento, 1024, seme=2)
    assert primo(17)[CAMPO_ZAVORRA] != secondo(17)[CAMPO_ZAVORRA]


def test_indici_diversi_danno_zavorre_diverse() -> None:
    genera = con_dimensione(DataGenerator().documento, 1024)
    assert genera(1)[CAMPO_ZAVORRA] != genera(2)[CAMPO_ZAVORRA]


def test_la_zavorra_non_e_un_carattere_ripetuto() -> None:
    # È la prova che vale il costo del generatore pseudocasuale. Duemila byte di `x` si
    # comprimono a niente, e una misura di throughput fatta su documenti che il motore
    # riduce a un ventesimo misura qualcos'altro.
    zavorra = con_dimensione(DataGenerator().documento, 2048)(0)[CAMPO_ZAVORRA]
    assert isinstance(zavorra, str)
    assert len(set(zavorra)) > 16


def test_la_zavorra_e_ascii_perche_un_byte_e_un_carattere() -> None:
    # Se la zavorra contenesse caratteri multibyte, tagliarla a `n` caratteri non darebbe
    # `n` byte e la dimensione non sarebbe più esatta.
    zavorra = con_dimensione(DataGenerator().documento, 4096)(3)[CAMPO_ZAVORRA]
    assert isinstance(zavorra, str)
    assert zavorra.isascii()


def test_i_campi_dell_originale_restano() -> None:
    nudo = DataGenerator().documento(5)
    vestito = con_dimensione(DataGenerator().documento, 1024)(5)
    for chiave, valore in nudo.items():
        assert vestito[chiave] == valore
    assert set(vestito) == set(nudo) | {CAMPO_ZAVORRA}


def test_il_generatore_originale_non_viene_alterato() -> None:
    # `con_dimensione` non deve scrivere dentro il documento che riceve e restituirlo:
    # un `Genera` che riusasse un dizionario si ritroverebbe la zavorra addosso.
    generatore = DataGenerator()
    con_dimensione(generatore.documento, 1024)(9)
    assert CAMPO_ZAVORRA not in generatore.documento(9)
