"""Le prove di `tests.integration.ambiente`: la spazzata, e chi risparmia.

Il modulo che le prove usano per raggiungere gli stack non aveva prove proprie, e la cosa
si è vista: `spazza` cancellava i database usa-e-getta di una sessione ancora viva, e
nessuno lo prendeva ([M-063](../../docs/Sources.md#m-063),
[ADR-0136](../../../docs/Decision.md#adr-0136)). Uno strumento che cancella è esattamente
quello che va provato per primo, perché quando sbaglia lo fa in silenzio.

Le due prove pure — riconoscere la sessione dentro un nome, e chiedere al kernel se un
processo esiste — non hanno bisogno di uno stack. La terza sì: la promessa da verificare è
su `drop_database`, e un doppio di MongoDB verificherebbe il doppio.
"""

import os
import subprocess
import sys
from typing import Any

import pytest
from pymongo import MongoClient

from tests.integration.ambiente import (
    PREFISSO_PROVE,
    SESSIONE,
    _sessione_di,
    collezione_usa_e_getta,
    nome_di_prova,
    sessione_viva,
    spazza,
)


# --- Il nome porta la sessione, e la sessione si sa interrogare ---------------------------


def test_il_nome_di_prova_porta_prefisso_sessione_e_coda() -> None:
    casuale = nome_di_prova()
    etichettato = nome_di_prova("backup")

    assert casuale.startswith(f"{PREFISSO_PROVE}{SESSIONE}_")
    assert etichettato == f"{PREFISSO_PROVE}{SESSIONE}_backup"
    assert casuale != nome_di_prova(), "due nomi casuali di seguito non devono coincidere"
    assert _sessione_di(casuale) == SESSIONE
    assert _sessione_di(etichettato) == SESSIONE


def test_un_nome_senza_sessione_non_ne_dichiara_una() -> None:
    # I nomi scritti prima di questa regola, e quelli di chi la aggirasse a mano. Non
    # portano una sessione, quindi sono orfani per definizione: `spazza` li prende.
    assert _sessione_di(f"{PREFISSO_PROVE}backup") is None
    assert _sessione_di(f"{PREFISSO_PROVE}abc123_qualcosa") is None
    assert _sessione_di(f"{PREFISSO_PROVE}12345") is None, "manca la coda"


def test_una_sessione_e_viva_se_il_suo_processo_esiste() -> None:
    assert sessione_viva(SESSIONE), "questo processo, che sta girando adesso"
    assert sessione_viva("1"), "init esiste sempre, e non è nostro: PermissionError è un sì"

    morto = subprocess.Popen([sys.executable, "-c", ""])
    morto.wait()
    assert not sessione_viva(str(morto.pid))


# --- La spazzata, contro uno stack vero ----------------------------------------------------


@pytest.mark.stack01
def test_la_spazzata_risparmia_i_database_di_una_sessione_viva(
    stack01: MongoClient[dict[str, Any]],
) -> None:
    """Il rilievo C-5 della review, fissato: la seconda sessione non porta via la prima.

    Le due sessioni si fabbricano scrivendo i nomi a mano, perché è il **nome** che porta
    l'informazione: uno firmato da un processo vivo — questo — e uno firmato da un processo
    che è appena morto.
    """
    morto = subprocess.Popen([sys.executable, "-c", ""])
    morto.wait()

    orfano = f"{PREFISSO_PROVE}{morto.pid}_{'o' * 8}"
    senza_firma = f"{PREFISSO_PROVE}vecchio_formato"
    stack01[orfano]["c"].insert_one({"x": 1})
    stack01[senza_firma]["c"].insert_one({"x": 1})

    with collezione_usa_e_getta(stack01) as mio:
        mio.insert_many([{"i": n} for n in range(5)])
        vivo = mio.database.name

        spazza(stack01)

        rimasti = set(stack01.list_database_names())
        assert vivo in rimasti, "la spazzata ha portato via il lavoro di una sessione viva"
        assert mio.count_documents({}) == 5
        assert orfano not in rimasti, "un orfano di sessione morta deve andarsene"
        assert senza_firma not in rimasti, "un nome senza sessione è un orfano"


@pytest.mark.stack01
def test_la_spazzata_risparmia_anche_i_residui_del_proprio_pid(
    stack01: MongoClient[dict[str, Any]],
) -> None:
    """Firmato con il **nostro** numero: potrebbe venire da un `pid` riciclato, e resta.

    È la prova che ha bocciato la prima stesura del rimedio, che invece li toglieva. Il
    ragionamento di allora — «alla prima spazzata i miei database non esistono ancora,
    quindi questo viene da un morto» — è vero e poggia su un ordine di creazione delle
    fixture che nessuno verifica. Il residuo lo prende la sessione dopo, che ha un numero
    diverso; l'assunzione invece non aveva scadenza.
    """
    riciclato = f"{PREFISSO_PROVE}{os.getpid()}_residuo_di_un_altro"
    stack01[riciclato]["c"].insert_one({"x": 1})
    try:
        spazza(stack01)

        assert riciclato in set(stack01.list_database_names())
    finally:
        stack01.drop_database(riciclato)
