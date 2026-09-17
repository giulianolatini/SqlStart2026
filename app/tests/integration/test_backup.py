"""`SubprocessBackup` contro `mongodump` e `mongorestore` veri, sullo stack 02.

Le prove unitarie mettono al posto degli strumenti un programma Python che dice le righe
che gli si dettano. Servono, e non bastano: **le righe gliele ho dettate io**. Qui a
scriverle è `mongodump` 100.18.0, e le tre cose che un finto non può verificare vengono
tutte da questo file — che la password letta da `stdin` autentichi davvero, che
`--readPreference=secondary --oplog` sia una combinazione che lo strumento accetta, e che
il segreto non compaia nella tabella dei processi del container.

**Gli strumenti non sono sull'host.** `mongodump` non è installato sulla macchina di chi
presenta; è dentro l'immagine `mongo` pinnata, in `/usr/bin`
([V-035](../../../docs/00-progetto/verifiche.md)). Il comando è quindi
`docker exec -i mongo-rs-1 mongodump`, ed è precisamente ciò che l'adattatore accetta dal
costruttore invece di deciderlo: al Task 12, da dentro la rete Compose, quello stesso
adattatore riceverà `("mongodump",)` e non saprà mai che oggi c'era un `docker exec`.

**Il `-i` è obbligatorio.** Senza, `docker exec` non collega lo `stdin`, la password non
arriva e l'autenticazione fallisce con un messaggio che parla d'altro.

**Le durate.** Questo file carica centomila documenti e li ripristina, e costa qualche
secondo in più di tutto il resto della suite di integrazione messo insieme. È il prezzo
della prova sulla tabella dei processi: per guardare dentro `ps` mentre lo strumento gira
serve che lo strumento giri abbastanza a lungo da poterlo guardare, e un dump di
cinquantamila documenti dura cinquanta millesimi di secondo.
"""

import secrets
import subprocess
import threading
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

import pytest
from pymongo import MongoClient

from mongolab.domain.modelli import Progress
from mongolab.domain.porte import BackupTool
from mongolab.infrastructure.backup import (
    ComandoFallito,
    RestoreIncompleto,
    SubprocessBackup,
)
from mongolab.infrastructure.generatore import DataGenerator
from mongolab.infrastructure.store import PymongoStore

from tests.integration.ambiente import STACK, credenziali_di, nome_di_prova

CONTENITORE = "mongo-rs-1"
"""Il `container_name` del primo membro, fissato in `docker/02-replicaset/compose.yaml`."""

HOST_INTERNO = "rs0/mongo-rs-1:27017,mongo-rs-2:27017,mongo-rs-3:27017"
"""I nomi di servizio, che esistono nella rete Compose e non sull'host.

Non è un doppione di ciò che `ambiente.connetti` fa con `directConnection`: lì il client
gira **fuori** dalla rete e quei nomi non si risolvono; qui a risolverli è `mongodump`, che
gira **dentro** il container. Lo stesso indirizzo, letto da due posti diversi, è due cose
diverse — ed è la stessa asimmetria che il Task 12 chiuderà.
"""

QUANTI = 100_000
"""Quanti documenti carica il laboratorio di queste prove."""

DOCUMENTI_DEL_SEED = 50_000
"""Quanti ne mette il seed dello stack in `lab.ordini`.

Dichiarato in `docker/02-replicaset/init/20-dati-demo.js` come `const DOCUMENTI`. È
duplicato qui apposta: se il seed cambia, questa prova deve **accorgersene**, e un
valore letto dallo stesso posto da cui viene il dato non se ne accorgerebbe mai.
"""


@pytest.fixture(scope="module")
def laboratorio(
    stack02: MongoClient[dict[str, Any]],
) -> Iterator[tuple[str, PymongoStore]]:
    """Un database usa-e-getta con abbastanza documenti da rendere il restore osservabile."""
    nome = nome_di_prova("backup")
    stack02.drop_database(nome)
    archivio = PymongoStore(stack02[nome]["ordini"])
    generatore = DataGenerator()
    for primo in range(0, QUANTI, 20_000):
        archivio.insert_many(list(generatore.lotto(20_000, dal=primo)))
    try:
        yield nome, archivio
    finally:
        stack02.drop_database(nome)


@pytest.fixture(scope="module")
def strumento(laboratorio: tuple[str, PymongoStore]) -> SubprocessBackup:
    """L'adattatore configurato come lo sarà in scena, `--oplog` compreso."""
    nome, _ = laboratorio
    credenziali = credenziali_di(STACK["02"])
    assert credenziali is not None, "lo stack 02 ha un .env: vedi ambiente.credenziali_di"
    return SubprocessBackup(
        host=HOST_INTERNO,
        comando_dump=("docker", "exec", "-i", CONTENITORE, "mongodump"),
        comando_restore=("docker", "exec", "-i", CONTENITORE, "mongorestore"),
        utente=credenziali.utente,
        password=credenziali.password,
        database=nome,
        opzioni_dump=("--readPreference=secondary", "--oplog"),
    )


@pytest.fixture(scope="module")
def sentinelle(stack02: MongoClient[dict[str, Any]]) -> Iterator[str]:
    """Due tracce **fuori** dal laboratorio, messe prima del dump: una collezione e un utente.

    Servono a `test_il_restore_isolato_non_tocca_il_database_del_laboratorio`, e la ragione
    per cui non basta contare è misurata in [M-064](../../docs/Sources.md#m-064): togliendo
    `--nsInclude`, `mongorestore` riscrive `lab` sopra sé stessa e **inserisce**, non
    aggiorna, quindi ogni `_id` collide e il conteggio resta identico al seed. Un conteggio
    che non cambia nel guasto che sorveglia non è una sorveglianza
    ([ADR-0135](../../../docs/Decision.md#adr-0135)).

    Una traccia che cambia di **valore** avrebbe lo stesso difetto: il documento esiste già,
    la sua chiave collide, il restore lo lascia com'è. Ciò che si vede è solo ciò che al
    momento del dump c'era e al momento del restore **non c'è più**: allora la chiave è
    libera, l'inserimento riesce, e la traccia riappare. Le due tracce coprono le due metà
    della promessa — `lab`, e gli utenti di `admin`, che `mongodump` porta via insieme al
    resto perché `--oplog` non ammette `--db`.

    La password dell'utente è casuale, non viene restituita e non attraversa nessuna riga di
    comando: `createUser` viaggia sulla connessione, come vuole
    [ADR-0054](../../../docs/Decision.md#adr-0054).
    """
    traccia = nome_di_prova("sentinella")
    stack02["lab"][traccia].insert_one({"_id": traccia})
    stack02["admin"].command("createUser", traccia, pwd=secrets.token_urlsafe(24), roles=[])
    try:
        yield traccia
    finally:
        _togli_sentinelle(stack02, traccia)


@pytest.fixture(scope="module")
def dump(
    strumento: SubprocessBackup,
    laboratorio: tuple[str, PymongoStore],
    sentinelle: str,
) -> Iterator[tuple[Path, list[Progress]]]:
    """Un dump vero, fatto una volta sola, e la cronaca che ha prodotto.

    La destinazione è un percorso **dentro il container**: l'adattatore lo passa allo
    strumento e non lo tocca, e chi lo pulisce è questa fixture con un `rm -rf` dalla
    stessa parte del confine.
    """
    nome, _ = laboratorio
    destinazione = Path("/tmp") / nome
    _dentro("rm", "-rf", str(destinazione))
    avanzamenti = list(strumento.dump(destinazione))
    try:
        yield destinazione, avanzamenti
    finally:
        _dentro("rm", "-rf", str(destinazione))


@pytest.fixture(scope="module")
def sentinelle_tolte(
    stack02: MongoClient[dict[str, Any]],
    dump: tuple[Path, list[Progress]],
    sentinelle: str,
) -> str:
    """Toglie le tracce **fra** il dump e il restore. È l'ordine a renderle visibili.

    Chiedere `dump` non serve al valore restituito: serve a fissare il momento. Se le tracce
    sparissero prima del dump non finirebbero nell'archivio e nessun restore potrebbe
    riportarle; se sparissero dopo il restore, il restore le troverebbe già lì e non
    lascerebbe segno. La finestra è una sola, e una fixture di modulo interposta fra le due
    è il modo di dichiararla al posto di sperarla.
    """
    _togli_sentinelle(stack02, sentinelle)
    return sentinelle


@pytest.fixture
def destinazione(stack02: MongoClient[dict[str, Any]]) -> Iterator[str]:
    """Un database di destinazione **nuovo** per ogni restore, e la ragione è misurata.

    `mongorestore` inserisce, non aggiorna: ripristinare due volte sopra la stessa
    destinazione fa collidere ogni `_id` e non salva un solo documento. Riusare il nome fra
    due prove non le renderebbe indipendenti — renderebbe la seconda un caso di
    fallimento travestito da caso normale.
    """
    nome = nome_di_prova(f"ripristino_{uuid4().hex[:8]}")
    try:
        yield nome
    finally:
        stack02.drop_database(nome)


@pytest.fixture(scope="module")
def restore_fatto(
    strumento: SubprocessBackup,
    dump: tuple[Path, list[Progress]],
    sentinelle_tolte: str,
    stack02: MongoClient[dict[str, Any]],
) -> Iterator[tuple[str, list[Progress]]]:
    """Un restore pulito, fatto una volta sola: due prove ne guardano due proprietà diverse.

    Costa qualche secondo, e farlo una volta per prova ne costerebbe il doppio senza
    aggiungere niente — ciò che le due prove verificano è del risultato, e il risultato è
    lo stesso.
    """
    nome = nome_di_prova("ripristino_condiviso")
    stack02.drop_database(nome)
    origine, _ = dump
    avanzamenti = list(strumento.restore(origine, nome))
    try:
        yield nome, avanzamenti
    finally:
        stack02.drop_database(nome)


def _utente_c_e(client: MongoClient[dict[str, Any]], nome: str) -> bool:
    """C'è un utente con questo nome in `admin`?

    `usersInfo` risponde con una lista vuota se non c'è, mentre `dropUser` su un utente
    assente è un errore: chiedere prima è ciò che rende ripetibile la rimozione.
    """
    risposta: dict[str, Any] = client["admin"].command("usersInfo", nome)
    return bool(risposta["users"])


def _togli_sentinelle(client: MongoClient[dict[str, Any]], traccia: str) -> None:
    """Toglie le due tracce, e si può chiamare due volte.

    La chiama `sentinelle_tolte` quando è il momento, e la richiama la fixture `sentinelle`
    a fine modulo: la seconda volta non deve trovare niente da fare, perché una prova che
    fallisce non deve anche lasciare in giro un utente.
    """
    client["lab"].drop_collection(traccia)
    if _utente_c_e(client, traccia):
        client["admin"].command("dropUser", traccia)


def _dentro(*argomenti: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "exec", CONTENITORE, *argomenti],
        capture_output=True,
        text=True,
        check=False,
    )


class Spia(threading.Thread):
    """Guarda la tabella dei processi del container finché non le si dice di smettere.

    **Non stampa mai quello che vede**, e nemmeno lo restituisce: espone due booleani. Una
    prova che fallisce mostra i valori che ha confrontato, e qui uno di quei valori sarebbe
    la riga di comando che si sta cercando di dimostrare pulita — cioè, il giorno in cui
    non lo fosse, il segreto finirebbe nel rapporto della prova che l'ha scoperto.
    """

    def __init__(self, atteso: str, segreto: str) -> None:
        super().__init__(daemon=True)
        self._atteso = atteso
        self._segreto = segreto
        self._basta = threading.Event()
        self.visto_lo_strumento = False
        self.visto_il_segreto = False
        self.campioni = 0

    def run(self) -> None:
        while not self._basta.is_set():
            tabella = _dentro("ps", "-eo", "args").stdout
            self.campioni += 1
            if self._atteso in tabella:
                self.visto_lo_strumento = True
            if self._segreto in tabella:
                self.visto_il_segreto = True

    def smetti(self) -> None:
        self._basta.set()
        self.join(timeout=30)


# --- Il dump ------------------------------------------------------------------------


def test_il_dump_racconta_la_collezione_mentre_la_scrive(
    dump: tuple[Path, list[Progress]], laboratorio: tuple[str, PymongoStore]
) -> None:
    nome, _ = laboratorio
    _, avanzamenti = dump

    nostri = [a for a in avanzamenti if a.fase == f"{nome}.ordini"]

    assert nostri, f"nessun avanzamento per {nome}.ordini fra {len(avanzamenti)} righe"
    assert nostri[0].completati == 0
    assert nostri[0].totali is None
    assert nostri[-1].completati == QUANTI


def test_il_dump_con_oplog_produce_anche_la_fase_oplog(
    dump: tuple[Path, list[Progress]],
) -> None:
    """`--oplog` è ciò che rende il dump coerente a un istante, e si vede nella cronaca."""
    _, avanzamenti = dump

    assert any(a.fase == "oplog" for a in avanzamenti)


def test_il_dump_scrive_davvero_i_file_dentro_il_container(
    dump: tuple[Path, list[Progress]], laboratorio: tuple[str, PymongoStore]
) -> None:
    """Perché una cronaca convincente e nessun file è esattamente il modo di sbagliarsi."""
    destinazione, _ = dump
    nome, _ = laboratorio

    elenco = _dentro("ls", str(destinazione / nome))

    assert elenco.returncode == 0
    assert "ordini.bson" in elenco.stdout
    assert _dentro("test", "-f", str(destinazione / "oplog.bson")).returncode == 0


def test_la_credenziale_letta_da_stdin_autentica_davvero(
    dump: tuple[Path, list[Progress]],
) -> None:
    """La prova che giustifica tutto il progetto dell'adattatore.

    Nessun `-p` fra gli argomenti: se `mongodump` non leggesse la password da uno `stdin`
    che non è un terminale, questo dump sarebbe fallito con `AuthenticationFailed` e la
    fixture avrebbe sollevato prima di arrivare qui. Che ci sia una cronaca è il verdetto.
    """
    _, avanzamenti = dump

    assert len(avanzamenti) > 1


def test_una_password_sbagliata_esce_diversa_da_zero_e_lo_dice(tmp_path: Path) -> None:
    """[ADR-0077](../../../docs/Decision.md#adr-0077) contro lo strumento vero."""
    sbagliato = SubprocessBackup(
        host=HOST_INTERNO,
        comando_dump=("docker", "exec", "-i", CONTENITORE, "mongodump"),
        utente="admin",
        password="questa-non-e-la-password-di-nessuno",
    )

    with pytest.raises(ComandoFallito) as caduta:
        list(sbagliato.dump(Path("/tmp/mongolab_prove_mai_scritto")))

    assert caduta.value.codice != 0
    assert "Authentication failed" in caduta.value.messaggio


# --- Il segreto ------------------------------------------------------------------------


def test_la_password_non_compare_nella_tabella_dei_processi_del_container(
    strumento: SubprocessBackup,
    dump: tuple[Path, list[Progress]],
    destinazione: str,
) -> None:
    """La misura che ha corretto il Passo 2 del piano, verificata mentre succede.

    Il piano diceva che la lista di argomenti tiene il segreto fuori dalla tabella dei
    processi. Non è vero: con `-p <valore>` in `argv`, dentro questo stesso container
    `ps -eo args` lo mostra per intero ([M-025](../../docs/Sources.md#m-025)). Quello che
    lo tiene fuori è ometterlo del tutto e passarlo da `stdin`, ed è questa prova a dirlo —
    guardando `ps` **mentre** lo strumento sta girando, non dopo.

    `visto_lo_strumento` non è una comodità: senza, una prova che avesse sbagliato momento e
    non avesse guardato niente passerebbe lo stesso, e sarebbe la peggiore specie di prova
    verde.
    """
    origine, _ = dump
    credenziali = credenziali_di(STACK["02"])
    assert credenziali is not None
    spia = Spia(atteso="mongorestore", segreto=credenziali.password)

    spia.start()
    try:
        for _ in strumento.restore(origine, destinazione):
            pass
    finally:
        spia.smetti()

    assert spia.visto_lo_strumento, (
        f"{spia.campioni} sguardi alla tabella dei processi e mai un mongorestore: "
        "il restore è finito prima che la spia potesse guardare, e questa prova non ha "
        "verificato niente"
    )
    assert not spia.visto_il_segreto


# --- Il restore ------------------------------------------------------------------------


def test_il_restore_rimette_gli_stessi_documenti_in_un_altro_database(
    restore_fatto: tuple[str, list[Progress]],
    laboratorio: tuple[str, PymongoStore],
    stack02: MongoClient[dict[str, Any]],
) -> None:
    """Il Passo 5: il verdetto è il conteggio sulla destinazione, non il codice d'uscita."""
    nome, avanzamenti = restore_fatto
    _, archivio = laboratorio

    assert avanzamenti, "un restore senza nemmeno una riga di cronaca"
    assert stack02[nome]["ordini"].count_documents({}) == QUANTI
    assert archivio.collezione.count_documents({}) == QUANTI


def test_il_restore_isolato_non_tocca_il_database_del_laboratorio(
    restore_fatto: tuple[str, list[Progress]],
    sentinelle_tolte: str,
    stack02: MongoClient[dict[str, Any]],
) -> None:
    """`--nsFrom/--nsTo` da soli rinominano e lasciano passare il resto.

    Il dump è di **tutto** — `--oplog` non ammette `--db` — quindi dentro quella directory
    c'è anche `lab`, che è il database della demo, e ci sono gli utenti di `admin`. Senza
    `--nsInclude`, un restore per confrontare i conteggi riscriverebbe `lab` sopra sé
    stessa: misurato, cinquantamila chiavi duplicate e un `restoring users from`
    ([M-024](../../docs/Sources.md#m-024)). Questa prova esiste perché quella terza opzione
    non sparisca in un riordino.

    **Il conteggio del seed non lo dimostra**, ed è il rilievo C-6 della review, misurato in
    [M-064](../../docs/Sources.md#m-064). Proprio M-024 dice perché: quel restore inserisce
    e non aggiorna, quindi cinquantamila chiavi duplicate lo lasciano **esattamente** a
    cinquantamila documenti, e con uscita 0. L'asserzione era verde nel guasto che
    sorvegliava. Ciò che la rende falsificabile sono le sentinelle: una collezione di `lab` e
    un utente di `admin` che al momento del dump c'erano e al momento del restore non ci sono
    più. Se il restore tocca quelle due parti, la chiave è libera e la traccia riappare.

    Il conteggio resta, e adesso è un secondo controllo invece che l'unico: dice che il
    restore non ha nemmeno **aggiunto** documenti a `lab`.
    """
    nome, _ = restore_fatto
    traccia = sentinelle_tolte

    assert stack02[nome]["ordini"].count_documents({}) == QUANTI
    assert stack02["lab"]["ordini"].count_documents({}) == DOCUMENTI_DEL_SEED
    assert traccia not in stack02["lab"].list_collection_names(), (
        "il restore ha rimesso in `lab` una collezione tolta dopo il dump: sta riscrivendo "
        "il database della demo"
    )
    assert not _utente_c_e(stack02, traccia), (
        "il restore ha ricreato un utente di `admin` tolto dopo il dump: sta riscrivendo gli "
        "utenti dello stack"
    )


def test_un_secondo_restore_sulla_stessa_destinazione_perde_tutto_ed_esce_zero(
    strumento: SubprocessBackup,
    dump: tuple[Path, list[Progress]],
    restore_fatto: tuple[str, list[Progress]],
) -> None:
    """[ADR-0084](../../../docs/Decision.md#adr-0084) contro lo strumento vero.

    `mongorestore` **inserisce**: sopra una destinazione già piena ogni `_id` collide, e
    centomila documenti su centomila falliscono. Lo dice — una riga `continuing through
    error` per ciascuno, e un sommario in fondo — e poi **esce zero**. Un chiamante che
    guardasse solo il codice d'uscita concluderebbe che il ripristino è andato bene.

    Questa non è una prova costruita per illustrare l'ADR: è il caso in cui sono
    inciampato scrivendo le due prove qui sopra, che davano per idempotente un restore che
    non lo è. L'adattatore ha sollevato, e la mia assunzione era la parte sbagliata.
    """
    origine, _ = dump
    gia_piena, _ = restore_fatto

    with pytest.raises(RestoreIncompleto) as caduta:
        list(strumento.restore(origine, gia_piena))

    assert caduta.value.restaurati == 0
    assert caduta.value.falliti == QUANTI


def test_la_porta_e_soddisfatta_dall_adattatore_vero(
    strumento: SubprocessBackup,
) -> None:
    """`mypy --strict` lo verifica sulle firme; questa riga lo mostra a runtime.

    Con il limite noto: `isinstance` contro un `Protocol` guarda i nomi dei metodi, non le
    firme. Vale come promemoria, non come garanzia — la garanzia è l'annotazione.
    """
    strutturale: BackupTool = strumento

    assert isinstance(strutturale, BackupTool)
