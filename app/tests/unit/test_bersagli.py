"""La mappa fra il nome che si scrive dopo `--target` e lo stack che risponde.

Il Passo 2 del Task 11 chiede una cosa sola di questa mappa: che stia **in un posto solo**.
Il posto è `infrastructure/bersagli.py`, ed è di produzione — non `tests/integration/
ambiente.py`, che fino al Task 10 teneva gli stessi tre numeri e che da qui in poi li
riceve. Una porta scritta in due file è una porta che al primo cambio ne vale due diverse,
e il modo in cui se ne accorge qualcuno è una prova d'integrazione che fallisce con un
messaggio che parla d'altro.

Le prove qui dentro guardano tre cose: che i nomi siano quelli del §6.4, che i numeri
coincidano con quelli che i `compose.yaml` pubblicano davvero, e che la credenziale non
finisca mai nell'URI.
"""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
import re

import pytest

from mongolab.infrastructure.bersagli import (
    BERSAGLI,
    COLLEZIONE,
    PREFISSO_CARICO,
    BersaglioSconosciuto,
    Credenziali,
    bersaglio_di,
    collezione_di_carico,
    credenziali_di,
    radice,
)

COMPOSE = {
    "standalone": "docker/01-standalone/compose.yaml",
    "rs": "docker/02-replicaset/compose.yaml",
    "sharded": "docker/03-sharded/compose.yaml",
}


def test_i_tre_nomi_sono_quelli_del_design() -> None:
    # §6.4 scrive `--target rs` e `--target sharded`; per lo standalone non dà un nome,
    # e `standalone` è quello che il repository usa già ovunque per lo stack 01.
    assert sorted(BERSAGLI) == ["rs", "sharded", "standalone"]


def test_ogni_bersaglio_conosce_il_proprio_nome() -> None:
    # La chiave della mappa e il campo `nome` devono coincidere: un messaggio d'errore che
    # nomina un bersaglio diverso da quello chiesto è peggio di nessun messaggio.
    for chiave, bersaglio in BERSAGLI.items():
        assert bersaglio.nome == chiave


def test_bersaglio_di_restituisce_quello_chiesto() -> None:
    assert bersaglio_di("rs") is BERSAGLI["rs"]


def test_un_target_sconosciuto_elenca_quelli_veri() -> None:
    # Il Passo 4 chiede che un `--target` sbagliato fallisca «con un messaggio». Un
    # messaggio che dice solo «sconosciuto» costringe a cercare i nomi nel sorgente.
    with pytest.raises(BersaglioSconosciuto) as caduta:
        bersaglio_di("replicaset")
    detto = str(caduta.value)
    assert "replicaset" in detto
    for nome in BERSAGLI:
        assert nome in detto


def test_un_target_sconosciuto_e_un_valueerror() -> None:
    # Chi cattura `ValueError` intorno alla lettura degli argomenti prende anche questo,
    # senza dover conoscere il tipo del progetto.
    assert issubclass(BersaglioSconosciuto, ValueError)


@pytest.mark.parametrize("nome", sorted(COMPOSE))
def test_la_porta_e_quella_che_il_compose_pubblica(nome: str) -> None:
    # La guardia contro la deriva: se qualcuno cambia la porta pubblicata in un
    # `compose.yaml`, questa prova diventa rossa prima che lo faccia un timeout di
    # selezione del server, che avrebbe impiegato venti secondi per dire un'altra cosa.
    testo = (radice() / COMPOSE[nome]).read_text(encoding="utf-8")
    porte = set(re.findall(r"\$\{PORTA_\w+:-(\d+)\}:27017", testo))
    assert str(BERSAGLI[nome].porta) in porte, f"{nome}: pubblicate {sorted(porte)}"


def test_solo_lo_standalone_non_ha_credenziali() -> None:
    assert BERSAGLI["standalone"].ambiente is None
    assert BERSAGLI["rs"].ambiente == "docker/02-replicaset/.env"
    assert BERSAGLI["sharded"].ambiente == "docker/03-sharded/.env"


def test_il_diretto_e_falso_solo_per_lo_sharded() -> None:
    # Dall'host il replica set va raggiunto con `directConnection=True`, o la scoperta
    # trova nomi di servizio Compose che l'host non risolve e la topologia si legge
    # `ReplicaSetNoPrimary` su un set sanissimo (M-019). Il mongos invece **è** il punto
    # d'ingresso: scoprire a partire da lui non porta il client da nessun'altra parte.
    assert BERSAGLI["standalone"].diretto is True
    assert BERSAGLI["rs"].diretto is True
    assert BERSAGLI["sharded"].diretto is False


@pytest.mark.parametrize("nome", sorted(COMPOSE))
def test_l_uri_non_contiene_credenziali(nome: str) -> None:
    # M-018: la credenziale si passa come argomento a `MongoClient`, mai nell'URI, perché
    # nell'URI entrerebbe in `repr(client)`, nei messaggi d'errore e in ogni log che
    # stampi la stringa di connessione. Qui si verifica che l'URI non abbia nemmeno la
    # forma che lo permetterebbe.
    uri = BERSAGLI[nome].uri
    assert uri.startswith("mongodb://")
    assert "@" not in uri
    assert ":" in uri.removeprefix("mongodb://")


def test_l_uri_porta_l_host_e_la_porta() -> None:
    assert BERSAGLI["rs"].uri == "mongodb://localhost:27021/"


def test_la_radice_e_quella_che_contiene_il_makefile() -> None:
    assert (radice() / "Makefile").is_file()
    assert (radice() / "docker").is_dir()


def test_lo_standalone_non_ha_credenziali_da_leggere() -> None:
    assert credenziali_di(BERSAGLI["standalone"]) is None


def test_la_credenziale_si_legge_dal_file_dello_stack(tmp_path: Path) -> None:
    ambiente = tmp_path / "docker" / "02-replicaset"
    ambiente.mkdir(parents=True)
    (ambiente / ".env").write_text(
        "# un commento\nUTENTE_AMMINISTRATORE=capo\nPASSWORD_AMMINISTRATORE=non-un-segreto-vero\n",
        encoding="utf-8",
    )
    lette = credenziali_di(BERSAGLI["rs"], base=tmp_path)
    assert lette == Credenziali(utente="capo", password="non-un-segreto-vero")


def test_l_utente_ha_un_valore_predefinito(tmp_path: Path) -> None:
    ambiente = tmp_path / "docker" / "02-replicaset"
    ambiente.mkdir(parents=True)
    (ambiente / ".env").write_text("PASSWORD_AMMINISTRATORE=x\n", encoding="utf-8")
    lette = credenziali_di(BERSAGLI["rs"], base=tmp_path)
    assert lette is not None and lette.utente == "admin"


def test_un_env_mancante_dice_quale_e_come_si_ottiene(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError) as caduta:
        credenziali_di(BERSAGLI["rs"], base=tmp_path)
    detto = str(caduta.value)
    assert "docker/02-replicaset/.env" in detto
    assert "ADR-0083" in detto


def test_un_env_senza_password_lo_dice_senza_stamparne_il_contenuto(tmp_path: Path) -> None:
    ambiente = tmp_path / "docker" / "02-replicaset"
    ambiente.mkdir(parents=True)
    (ambiente / ".env").write_text("ALTRO=qualcosa\n", encoding="utf-8")
    with pytest.raises(RuntimeError) as caduta:
        credenziali_di(BERSAGLI["rs"], base=tmp_path)
    detto = str(caduta.value)
    assert "PASSWORD_AMMINISTRATORE" in detto
    assert "qualcosa" not in detto


def test_la_password_non_esce_dal_repr() -> None:
    # In una prova fallita l'oggetto finisce nel traceback, e il traceback finisce in una
    # `.cast` o in un log. `field(repr=False)` non protegge dal dolo: protegge dallo
    # sbaglio, che è il modo in cui i segreti escono davvero.
    mostrato = repr(Credenziali(utente="capo", password="non-un-segreto-vero"))
    assert "capo" in mostrato
    assert "non-un-segreto-vero" not in mostrato


# --- Dove atterra il carico ------------------------------------------------------------
#
# Misurato, non dedotto: `mongolab workload --target standalone` contro lo stack 01 acceso
# ha risposto `E11000 duplicate key error collection: lab.ordini index: _id_ dup key:
# { _id: 0 }` per **ogni** scrittura, e il consuntivo diceva `38 scritture · 0 confermate`.
# `DataGenerator` numera i documenti da zero, il seed occupa già `_id` da 0 a 49 999, e il
# carico stava scrivendo nella collezione seminata.
#
# Che non dovesse farlo era già scritto in `generatore.py`: «le due popolazioni non si
# incontrano mai nella stessa collezione, perché il carico scrive nella propria». Ed era
# già previsto altrove — `tools/reset-demo.sh` dichiara `const superstiti = ["ordini"]` e
# lascia cadere ogni altra collezione di `lab`. Il posto per i documenti del carico
# esisteva; a sbagliare era il cablaggio.


def test_la_collezione_del_carico_non_e_quella_seminata() -> None:
    quando = datetime(2026, 9, 18, 10, 30, 0, tzinfo=UTC)

    assert collezione_di_carico(quando) != COLLEZIONE


def test_la_collezione_del_carico_dice_quando_e_nata() -> None:
    # Chi apre `mongosh` dopo la corsa deve poter riconoscere la propria fra le altre, e
    # l'istante è l'unica cosa che distingue due corse identiche.
    quando = datetime(2026, 9, 18, 10, 30, 0, tzinfo=UTC)

    assert collezione_di_carico(quando) == "carico-20260918-103000"


def test_due_corse_non_si_pestano_i_piedi() -> None:
    """Il nome cambia a ogni corsa, e non è un vezzo: è ciò che rende ripetibile il carico.

    Con un nome fisso la seconda esecuzione ritroverebbe gli `_id` della prima e
    fallirebbe con lo stesso E11000 — cioè funzionerebbe una volta sola, e in sala si
    esegue più di una volta. Gli avanzi non restano: `reset-demo` li spazza tutti insieme,
    perché in `lab` sopravvive solo `ordini`.
    """
    prima = collezione_di_carico(datetime(2026, 9, 18, 10, 30, 0, tzinfo=UTC))
    poi = collezione_di_carico(datetime(2026, 9, 18, 10, 30, 1, tzinfo=UTC))

    assert prima != poi


def test_il_nome_del_carico_si_riconosce_dal_prefisso() -> None:
    # `reset-demo` non ha bisogno del prefisso — toglie tutto ciò che non è `ordini` — ma
    # chi guarda `show collections` sì: tre nomi che cominciano allo stesso modo si
    # leggono come tre corse, non come tre collezioni scollegate.
    quando = datetime(2026, 9, 18, 10, 30, 0, tzinfo=UTC)

    assert collezione_di_carico(quando).startswith(PREFISSO_CARICO)


def test_l_istante_del_carico_si_legge_nel_suo_fuso() -> None:
    """Un nome è un'etichetta per un umano, e l'umano guarda l'orologio della sala.

    `SystemClock` restituisce istanti consapevoli del fuso locale; convertirli a UTC per
    il nome darebbe una collezione «delle 8:30» a una corsa fatta alle 10:30, e chi cerca
    la propria fra tre avanzi cercherebbe l'ora sbagliata.
    """
    roma = timezone(timedelta(hours=2))
    quando = datetime(2026, 9, 18, 10, 30, 0, tzinfo=roma)

    assert collezione_di_carico(quando) == "carico-20260918-103000"
