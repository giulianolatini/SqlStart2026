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
from typing import Any

import pytest
from pymongo import MongoClient

from mongolab.infrastructure.bersagli import (
    SenzaPrimario,
    attendi_il_primario,
    BERSAGLI,
    COLLEZIONE,
    PREFISSO_CARICO,
    VARIABILE_PUNTO_DI_VISTA,
    BersaglioSconosciuto,
    Credenziali,
    PuntoDiVista,
    PuntoDiVistaSconosciuto,
    Vista,
    bersaglio_di,
    collezione_di_carico,
    connetti,
    credenziali_di,
    punto_di_vista,
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


def test_dall_host_il_diretto_e_falso_solo_per_lo_sharded() -> None:
    # Dall'host il replica set va raggiunto con `directConnection=True`, o la scoperta
    # trova nomi di servizio Compose che l'host non risolve e la topologia si legge
    # `ReplicaSetNoPrimary` su un set sanissimo (M-019). Il mongos invece **è** il punto
    # d'ingresso: scoprire a partire da lui non porta il client da nessun'altra parte.
    assert BERSAGLI["standalone"].vista(PuntoDiVista.HOST).diretto is True
    assert BERSAGLI["rs"].vista(PuntoDiVista.HOST).diretto is True
    assert BERSAGLI["sharded"].vista(PuntoDiVista.HOST).diretto is False


@pytest.mark.parametrize("nome", sorted(COMPOSE))
@pytest.mark.parametrize("punto", list(PuntoDiVista))
def test_l_uri_non_contiene_credenziali(nome: str, punto: PuntoDiVista) -> None:
    # M-018: la credenziale si passa come argomento a `MongoClient`, mai nell'URI, perché
    # nell'URI entrerebbe in `repr(client)`, nei messaggi d'errore e in ogni log che
    # stampi la stringa di connessione. Qui si verifica che l'URI non abbia nemmeno la
    # forma che lo permetterebbe — da tutti e due i punti di vista, perché il secondo è
    # quello che gira dentro un container dove la password arriva dall'ambiente.
    uri = BERSAGLI[nome].vista(punto).uri
    assert uri.startswith("mongodb://")
    assert "@" not in uri
    assert ":" in uri.removeprefix("mongodb://")


def test_l_uri_dell_host_porta_localhost_e_la_porta_pubblicata() -> None:
    assert BERSAGLI["rs"].vista(PuntoDiVista.HOST).uri == "mongodb://localhost:27021/"


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


# --- Da dove si guarda -----------------------------------------------------------------
#
# Il Task 12 mette l'applicazione dentro la rete Compose, e da lì gli stessi tre stack
# hanno un altro indirizzo: non `localhost:27021` ma `mongo-rs-1:27017`, non una porta
# pubblicata ma un nome di servizio. Cambia anche `directConnection`, e cambia dove sta la
# password. Sono tre fatti che dipendono dallo stesso unico dato — da dove si guarda — e
# per questo stanno in un tipo solo, `Vista`, invece che in tre variabili che possono
# smettere di essere d'accordo.


def test_i_punti_di_vista_sono_due() -> None:
    # Due e non tre: «dentro un altro container sulla stessa rete» e «dentro il container
    # dell'applicazione» sono lo stesso punto di vista, e un terzo nome li farebbe sembrare
    # diversi.
    assert sorted(punto.value for punto in PuntoDiVista) == ["host", "rete"]


def test_senza_variabile_si_guarda_dall_host() -> None:
    # Il predefinito è l'host perché è da lì che si sviluppa: `uv run mongolab stats` sul
    # portatile deve funzionare senza dichiarare niente.
    assert punto_di_vista({}) is PuntoDiVista.HOST


def test_una_variabile_vuota_vale_come_assente() -> None:
    """Compose passa la stringa vuota quando la variabile di partenza non è definita.

    `MONGOLAB_PUNTO_DI_VISTA: ${QUALCOSA}` con `QUALCOSA` non definita non toglie la
    variabile: la mette a `""`. Trattarla come un valore sbagliato farebbe fallire
    l'applicazione per una riga di configurazione che voleva dire «niente».
    """
    assert punto_di_vista({VARIABILE_PUNTO_DI_VISTA: ""}) is PuntoDiVista.HOST


def test_dalla_rete_lo_dice_la_variabile() -> None:
    assert punto_di_vista({VARIABILE_PUNTO_DI_VISTA: "rete"}) is PuntoDiVista.RETE


def test_il_valore_si_legge_senza_badare_a_spazi_e_maiuscole() -> None:
    assert punto_di_vista({VARIABILE_PUNTO_DI_VISTA: " Rete\n"}) is PuntoDiVista.RETE


def test_un_punto_di_vista_sconosciuto_non_diventa_il_predefinito() -> None:
    """Un valore che non si capisce **ferma** l'applicazione, e non ripiega sull'host.

    Ripiegare in silenzio sarebbe la cosa peggiore che possa fare: da dentro un container,
    `localhost:27021` non è un errore immediato, è un `ServerSelectionTimeoutError` dopo
    venti secondi che parla di una porta chiusa. Il messaggio nomina la variabile e i due
    valori veri, perché chi ha scritto `container` invece di `rete` deve leggerlo lì.
    """
    with pytest.raises(PuntoDiVistaSconosciuto) as caduta:
        punto_di_vista({VARIABILE_PUNTO_DI_VISTA: "container"})
    detto = str(caduta.value)
    assert "container" in detto
    assert VARIABILE_PUNTO_DI_VISTA in detto
    for valore in ("host", "rete"):
        assert valore in detto


def test_un_punto_di_vista_sconosciuto_e_un_valueerror() -> None:
    assert issubclass(PuntoDiVistaSconosciuto, ValueError)


def test_senza_argomenti_il_punto_di_vista_e_quello_del_processo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VARIABILE_PUNTO_DI_VISTA, "rete")

    assert punto_di_vista() is PuntoDiVista.RETE


def test_l_uri_di_una_vista_elenca_tutti_i_semi() -> None:
    # I semi separati da virgola sono la forma con cui si dichiara più di un punto di
    # partenza: il client li interroga tutti e tiene quelli che rispondono.
    vista = Vista(semi=(("a", 1), ("b", 2)), diretto=False, replica="rs0")

    assert vista.uri == "mongodb://a:1,b:2/"


@pytest.mark.parametrize("nome", sorted(COMPOSE))
def test_dall_host_c_e_un_solo_seme_ed_e_localhost(nome: str) -> None:
    # Dall'host il seme è uno perché la porta pubblicata è una: lo stack 02 ne pubblica
    # tre, ma con `directConnection=True` pymongo **rifiuta** più di un seme, e senza
    # `diretto` la scoperta ripartirebbe dai nomi di servizio (M-019).
    vista = BERSAGLI[nome].vista(PuntoDiVista.HOST)

    assert vista.semi == (("localhost", BERSAGLI[nome].porta),)


@pytest.mark.parametrize("nome", sorted(COMPOSE))
def test_dalla_rete_ogni_seme_e_un_servizio_dichiarato_nel_compose(nome: str) -> None:
    """La guardia contro il nome inventato: ogni host della vista di rete esiste davvero.

    Un nome di servizio sbagliato non dà un errore di configurazione: dà una risoluzione
    DNS fallita dentro il monitor di pymongo, che la ritenta in silenzio fino alla
    scadenza della selezione. Venti secondi per scoprire un refuso. Qui il refuso si legge
    subito, e si legge sull'unica fonte che conta, cioè il `compose.yaml` dello stack.
    """
    testo = (radice() / COMPOSE[nome]).read_text(encoding="utf-8")
    servizi = set(re.findall(r"^  ([a-z0-9-]+):$", testo, flags=re.MULTILINE))

    for host, porta in BERSAGLI[nome].vista(PuntoDiVista.RETE).semi:
        assert host in servizi, f"{nome}: «{host}» non è un servizio di {COMPOSE[nome]}"
        # Dentro la rete la porta è sempre 27017: le porte diverse dei `compose.yaml`
        # sono mappature verso l'host, e dentro non esistono.
        assert porta == 27017


def test_dalla_rete_solo_lo_standalone_va_diretto() -> None:
    """Il Passo 3 del Task 12, e la ragione per cui la differenza è voluta.

    Sullo stack 01 non c'è niente da scoprire — un mongod solo, che non conosce nessun
    altro — quindi `directConnection=true` non toglie nulla e dice la verità. Sugli altri
    due la scoperta **è** la cosa da mostrare: il client parte dai semi, chiede `hello`,
    riceve l'elenco dei membri dalla configurazione del set e va a parlare col primario.
    Metterci `diretto` significherebbe spegnere la scena.
    """
    assert BERSAGLI["standalone"].vista(PuntoDiVista.RETE).diretto is True
    assert BERSAGLI["rs"].vista(PuntoDiVista.RETE).diretto is False
    assert BERSAGLI["sharded"].vista(PuntoDiVista.RETE).diretto is False


@pytest.mark.parametrize("nome", sorted(COMPOSE))
@pytest.mark.parametrize("punto", list(PuntoDiVista))
def test_una_vista_diretta_ha_un_seme_solo(nome: str, punto: PuntoDiVista) -> None:
    # Non è un gusto: `MongoClient(directConnection=True)` con più di un seme solleva
    # `ConfigurationError` alla costruzione. Una mappa che lo violasse romperebbe ogni
    # comando, e questa prova lo dice prima.
    vista = BERSAGLI[nome].vista(punto)

    if vista.diretto:
        assert len(vista.semi) == 1


def test_dalla_rete_il_replica_set_parte_da_tutti_e_tre_i_membri() -> None:
    """Tre semi e non uno, perché uno solo funziona finché quel membro è acceso.

    La scoperta funziona anche a partire da un membro qualunque — è ciò che il Passo 2 va
    a misurare — ma un'applicazione che dichiara un seme solo non parte se proprio quello
    è giù, e in sala il membro giù è una scena prevista, non un incidente.
    """
    semi = BERSAGLI["rs"].vista(PuntoDiVista.RETE).semi

    assert semi == (
        ("mongo-rs-1", 27017),
        ("mongo-rs-2", 27017),
        ("mongo-rs-3", 27017),
    )


def test_dalla_rete_il_nome_del_set_e_quello_che_il_compose_avvia() -> None:
    # `replicaSet=rs0` è una dichiarazione di aspettativa: se il set trovato si chiama
    # diversamente, pymongo non lo usa. Quindi il nome deve essere lo stesso che i tre
    # `--replSet` del compose scrivono, e questa prova rilegge il compose invece di
    # fidarsi.
    testo = (radice() / COMPOSE["rs"]).read_text(encoding="utf-8")
    nomi = set(re.findall(r"\$\{NOME_REPLICA:-(\w+)\}", testo))

    assert BERSAGLI["rs"].vista(PuntoDiVista.RETE).replica in nomi


def test_solo_il_replica_set_dichiara_un_nome_di_set() -> None:
    # Un `replicaSet=` verso un mongos è un errore di categoria: il mongos non è un
    # membro di nessun set, e il client che glielo chiedesse non lo userebbe.
    for nome in ("standalone", "sharded"):
        for punto in PuntoDiVista:
            assert BERSAGLI[nome].vista(punto).replica is None


# --- La credenziale, dai due lati ------------------------------------------------------


def test_dalla_rete_la_credenziale_arriva_dall_ambiente() -> None:
    lette = credenziali_di(
        BERSAGLI["rs"],
        punto=PuntoDiVista.RETE,
        variabili={
            "UTENTE_AMMINISTRATORE": "capo",
            "PASSWORD_AMMINISTRATORE": "non-un-segreto-vero",
        },
    )

    assert lette == Credenziali(utente="capo", password="non-un-segreto-vero")


def test_dalla_rete_non_si_cerca_nessun_file(tmp_path: Path) -> None:
    """Dentro il container il repository non c'è: c'è `/app`, e basta.

    Il `.env` sta nel checkout dell'host e non viene montato — è un segreto, e ADR-0014
    lo tiene fuori dal repository. Se questo ramo provasse comunque a leggerlo, `radice()`
    risalirebbe fino a `/` senza trovare un `Makefile` e l'errore parlerebbe di un
    repository mancante invece che di una variabile mancante.
    """
    lette = credenziali_di(
        BERSAGLI["sharded"],
        base=tmp_path,
        punto=PuntoDiVista.RETE,
        variabili={"PASSWORD_AMMINISTRATORE": "non-un-segreto-vero"},
    )

    assert lette is not None
    assert lette.utente == "admin"


def test_dalla_rete_una_password_mancante_nomina_la_variabile() -> None:
    with pytest.raises(RuntimeError) as caduta:
        credenziali_di(
            BERSAGLI["rs"],
            punto=PuntoDiVista.RETE,
            variabili={"ALTRO": "qualcosa"},
        )
    detto = str(caduta.value)
    assert "PASSWORD_AMMINISTRATORE" in detto
    # Come per il `.env`: si nomina la chiave che manca, non si riversa nell'errore
    # l'ambiente che è stato letto.
    assert "qualcosa" not in detto


def test_dalla_rete_lo_standalone_resta_senza_credenziali() -> None:
    assert (
        credenziali_di(BERSAGLI["standalone"], punto=PuntoDiVista.RETE, variabili={})
        is None
    )


# --- Il client, dai due lati -----------------------------------------------------------
#
# `connect=False` passa per `extra` e arriva a `MongoClient`: il client si costruisce
# senza aprire un socket e senza avviare i monitor, così queste restano prove unitarie che
# non hanno bisogno di nessuno stack acceso. Ciò che si guarda dopo — i semi, il diretto,
# il nome del set — è già deciso alla costruzione.


def test_dalla_rete_il_client_parte_dai_nomi_di_servizio() -> None:
    cliente = connetti(
        BERSAGLI["rs"],
        punto=PuntoDiVista.RETE,
        variabili={"PASSWORD_AMMINISTRATORE": "non-un-segreto-vero"},
        connect=False,
    )
    try:
        assert sorted(cliente.topology_description.server_descriptions()) == [
            ("mongo-rs-1", 27017),
            ("mongo-rs-2", 27017),
            ("mongo-rs-3", 27017),
        ]
        assert cliente.options.direct_connection is False
        assert cliente.options.replica_set_name == "rs0"
    finally:
        cliente.close()


def test_dall_host_il_client_resta_su_localhost() -> None:
    cliente = connetti(BERSAGLI["standalone"], punto=PuntoDiVista.HOST, connect=False)
    try:
        assert sorted(cliente.topology_description.server_descriptions()) == [
            ("localhost", 27017)
        ]
        assert cliente.options.direct_connection is True
        assert cliente.options.replica_set_name is None
    finally:
        cliente.close()


def test_senza_punto_di_vista_il_client_lo_legge_dall_ambiente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # È così che funziona dentro il container: nessuno passa `punto=`, la variabile è
    # scritta nel servizio Compose, e l'applicazione si comporta di conseguenza.
    monkeypatch.setenv(VARIABILE_PUNTO_DI_VISTA, "rete")
    monkeypatch.setenv("PASSWORD_AMMINISTRATORE", "non-un-segreto-vero")

    cliente = connetti(BERSAGLI["sharded"], connect=False)
    try:
        assert sorted(cliente.topology_description.server_descriptions()) == [
            ("mongos", 27017)
        ]
    finally:
        cliente.close()


def test_l_attesa_del_primario_finisce_e_lo_dice_nel_linguaggio_di_questo_strato() -> None:
    """Se il primario non arriva, esce `SenzaPrimario` e non l'eccezione di pymongo.

    Un `MongoClient` vero contro una porta chiusa, e non un doppio: ciò che si verifica è
    come **pymongo** fallisce, e un doppio verificherebbe come lo immagina chi scrive la
    prova. La porta 1 su loopback rifiuta subito, quindi la prova costa i cinquanta
    millisecondi di attesa che le si danno e non tocca la rete.

    Il caso opposto — il `ping` che riesce, e che è il motivo per cui questa funzione
    esiste — non si prova senza un server: lo prova `tests/integration/test_scenari.py`
    contro il replica set acceso, dove senza questa attesa la scena non parte.
    """
    cliente: MongoClient[dict[str, Any]] = MongoClient(
        "mongodb://127.0.0.1:1/", serverSelectionTimeoutMS=50, connectTimeoutMS=50
    )
    try:
        with pytest.raises(SenzaPrimario):
            attendi_il_primario(cliente)
    finally:
        cliente.close()
