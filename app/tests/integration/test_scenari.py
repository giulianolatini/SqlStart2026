"""Le scene del Blocco 2 contro lo stack vero: l'Atto II, e l'Atto III che gli va dietro.

Le prove unitarie del Task 13 asseriscono sulla **sequenza** — sei fasi, in quell'ordine,
con i doppi al posto di tutto — e ci mettono millisecondi. Questo modulo fa l'altra metà
del Passo 4: che la stessa sequenza esca da un replica set vero, con un'elezione vera in
mezzo. Costa una quarantina di secondi e non può costare meno, perché quaranta secondi è
quanto dura la scena in sala.

## Perché la prova esegue i comandi che l'applicazione annuncia

Dentro la rete Compose l'applicazione **vede** la topologia — e solo da lì la vede, che è
tutto il senso di [M-019](../../../app/docs/Sources.md#m-019) — ma non ha il socket del
demone Docker e non può fermare nessuno. Sull'host è esattamente il contrario. Un processo
solo non può fare tutte e due le cose, e la porta `Regia` esiste per questo: nel container
l'adattatore è `RegiaAnnunciata`, che **stampa** la riga da eseguire e aspetta.

In sala quella riga la esegue una persona con una seconda finestra aperta. Qui la esegue
questa prova, che legge lo stdout del container e risponde sul suo stdin. Non è una
scorciatoia: è la stessa disposizione, con la persona sostituita. E ha un effetto
collaterale che vale da solo la prova — la riga annunciata viene eseguita **verbatim**, e
se non fosse incollabile così com'è la prova fallirebbe qui invece che sul proiettore.

## Che cosa questo modulo non prova

Non prova la modalità `--step`: la pausa legge da `stdin`, e una prova che le rispondesse
verificherebbe di saper scrivere un a capo. La differenza fra `--step` e senza è una sola
funzione di attesa, e a coprirla sono le prove unitarie.

Non prova `--mode sospendi`. La congelata è un'altra scena, con un'altra durata e un'altra
attesa, e raddoppierebbe il minuto che questo modulo costa per verificare una variante che
il frasario di `ComandiCompose` già copre riga per riga.

## L'Atto III sta qui sotto, e gira dall'altro lato

Le due scene del backup a caldo non si avviano con `scena_nel_container`: si avviano
**dall'host**, con il `mongolab` che sta nel venv delle prove. Non è una comodità, è la
sola disposizione che funziona — `mongodump` non è nell'immagine dell'applicazione
([M-044](../../docs/Sources.md#m-044)) e il container dell'applicazione non ha il socket
del demone Docker, quindi il `docker compose exec` che va a prenderlo nel nodo può partire
solo da fuori. È l'inverso esatto dell'Atto II, ed è per questo che le due metà del modulo
si somigliano poco.

Girarle dall'host ha un effetto che vale la prova: `pytest` parte da `app/`, mentre i
percorsi dei `compose.yaml` che il frasario costruisce sono **relativi alla radice**.
Togliendo il `dove` che `strumento_di` passa a `SubprocessBackup`, questa prova diventa
rossa in quattro secondi con `open .../app/docker/02-replicaset/compose.yaml: no such file
or directory` — verificato rompendolo apposta. Senza di lei il guasto comparirebbe sul
portatile di chi presenta, e solo perché avesse lanciato il comando dalla cartella
sbagliata.
"""

import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

import pytest
from pymongo import MongoClient

from mongolab.cli import comandi_di
from mongolab.infrastructure.bersagli import BERSAGLI, DATABASE, radice
from tests.integration.ambiente import (
    IMMAGINE,
    PREFISSO_PROVE,
    STACK,
    Scena,
    immagine_in_cache,
    nel_container,
    rimetti_in_piedi,
    scena_nel_container,
)

servono_immagine = pytest.mark.skipif(
    not immagine_in_cache(),
    reason=f"l'immagine {IMMAGINE} non è costruita: «make app-image» (richiede rete)",
)

FASI_DEL_COPIONE = ("carico", "guasto", "elezione", "ripresa", "recupero", "bilancio")
"""L'Atto II, in ordine. È la sequenza su cui il Passo 4 chiede di asserire."""

CARICO_S, ELEZIONE_S, RECUPERO_S = "3", "20", "5"
"""Le tre durate, accorciate rispetto ai predefiniti del §6.4 (10, 25, 15).

L'unica che non si può accorciare è l'elezione: V-029 la misura fra 9 812 e 10 943 ms, e
una fase più corta chiuderebbe la scena mentre il replica set sta ancora votando. Venti
secondi lasciano il doppio del margine sul valore peggiore misurato. Le altre due esistono
per avere scritture prima e dopo, e tre secondi di otto scrittori ne fanno a sufficienza.
"""

# `failover     interruzione 9812 ms · scritture perse 0` — la prima riga della cronaca,
# che è anche la sola che il pubblico deve ricordare.
DUE_NUMERI = re.compile(
    r"^failover\s+interruzione (?P<interruzione>\S+) ms\s+·\s+"
    r"scritture perse (?P<perse>\d+)\s*$"
)
FASI = re.compile(r"^fasi\s+(?P<elenco>.+?)\s*$")
DESTINAZIONE = re.compile(r"carico in lab\.(?P<collezione>carico-\S+)")
# `             da mongo-rs-1:27017 a mongo-rs-2:27017` — la riga di continuazione che la
# cronaca stampa solo se qualcuno ha davvero preso il posto di qualcun altro.
AVVICENDAMENTO = re.compile(r"^\s+da (?P<prima>\S+:\d+) a (?P<dopo>\S+:\d+)\s*$")


def _riga(uscita: str, quale: re.Pattern[str]) -> re.Match[str]:
    """La prima riga che corrisponde, o un fallimento che mostra tutto ciò che è uscito.

    Il testo intero nel messaggio e non solo l'asserzione: quando questa prova fallisce, il
    replica set è già tornato a posto e la scena non si ripete gratis. Quello che è uscito
    è l'unico documento di che cosa è successo.

    Prende il testo e non la `Scena` perché l'Atto III, girando dall'host, non ha una
    regia da annunciare e quindi non ha una `Scena`: ciò che le due metà del modulo hanno
    davvero in comune è che leggono righe.
    """
    for riga in uscita.splitlines():
        trovata = quale.search(riga)
        if trovata is not None:
            return trovata
    raise AssertionError(f"nessuna riga per {quale.pattern!r}.\n{uscita}")


def _porta_via(collezione: str) -> None:
    """Toglie la collezione di carico che la scena ha creato, da dentro la rete.

    Da dentro e non dall'host perché dopo il failover il primario può essere un altro
    nodo, e il client dell'host arriva su `localhost:27021` con `directConnection`: se
    `mongo-rs-1` è rientrato come secondario, una `drop` da lì fallisce. Nella rete la
    scoperta funziona e il primario si trova da sé — è la stessa asimmetria per cui esiste
    `RegiaAnnunciata`, vista dal lato dei dati.

    Si collega con `connetti` della produzione, non con un URI scritto qui: un URI scritto
    a mano in una prova è il posto in cui la credenziale prima o poi compare.
    """
    nel_container(
        STACK["02"],
        "-c",
        "from mongolab.infrastructure.bersagli import BERSAGLI, DATABASE, connetti\n"
        "cliente = connetti(BERSAGLI['rs'])\n"
        f"cliente[DATABASE].drop_collection({collezione!r})\n"
        "cliente.close()\n",
        entrypoint="python",
    )


@servono_immagine
def test_la_scena_del_failover_esce_dallo_stack_vero(
    stack02: MongoClient[dict[str, Any]],
) -> None:
    """Sei fasi, due comandi annunciati ed eseguiti, un'elezione, e i due numeri.

    Una prova sola e non sei, perché la scena si gira una volta: spezzarla in sei
    asserzioni indipendenti vorrebbe dire girarla sei volte, cioè quattro minuti di stack
    vero per verificare cose che un'unica esecuzione mostra tutte insieme.

    `stack02` serve a garantire che il replica set sia acceso prima di cominciare. Il
    client che restituisce non si usa: da qui dentro non si osserva niente, perché ciò che
    dev'essere vero è quello che l'applicazione **stampa**.
    """
    try:
        scena = scena_nel_container(
            STACK["02"],
            "demo",
            "failover",
            "--target",
            "rs",
            "--sink",
            "plain",
            "--carico",
            CARICO_S,
            "--elezione",
            ELEZIONE_S,
            "--recupero",
            RECUPERO_S,
        )
    finally:
        rimetti_in_piedi(STACK["02"])

    fasi = tuple(_riga(scena.uscita, FASI).group("elenco").split(" · "))
    assert fasi == FASI_DEL_COPIONE

    caduto, rientrato = (riga.split()[-1] for riga in scena.comandi)
    assert scena.comandi[0].endswith(f"kill -s SIGKILL {caduto}")
    assert scena.comandi[1].endswith(f"start {rientrato}")
    assert caduto == rientrato, "il nodo rimesso in servizio non è quello ucciso"

    # L'avvicendamento si legge dal **resoconto della scena** e non ricostruendolo dalle
    # righe `SERVER … → primario`: di quelle la prima è la scoperta iniziale, che nomina
    # il primario di sempre, e una prova che la scambiasse per l'elezione passerebbe anche
    # se il guasto non fosse mai arrivato. Qui si verifica ciò che la sala legge.
    avvicendamento = _riga(scena.uscita, AVVICENDAMENTO)
    prima, dopo = avvicendamento.group("prima"), avvicendamento.group("dopo")
    assert prima.startswith(f"{caduto}:"), (
        f"la cronaca dice che il primario era {prima}, ma la scena ha ucciso {caduto}"
    )
    assert dopo != prima, "nessuno ha preso il posto del primario ucciso"

    numeri = _riga(scena.uscita, DUE_NUMERI)
    interruzione = float(numeri.group("interruzione"))
    perse = int(numeri.group("perse"))
    _porta_via(_riga(scena.uscita, DESTINAZIONE).group("collezione"))

    # La banda è larga apposta. Stretta sulla forbice 8-10 s di V-031 questa prova
    # diventerebbe rossa su un portatile carico senza che niente sia rotto; larga così
    # coglie ancora l'unica cosa che deve cogliere, che è l'errore di **categoria**: mezzo
    # secondo vorrebbe dire che il nodo ha ceduto il ruolo con grazia invece di sparire
    # (V-029 misura 574, 480, 486 ms con `stop`), e trenta secondi che qualcosa non ha
    # funzionato affatto. Il confronto stretto con V-031 si fa a mano, leggendo il numero.
    assert 5_000.0 <= interruzione <= 15_000.0, (
        f"interruzione di {interruzione:.0f} ms, fuori da ogni ordine di grandezza "
        f"atteso: V-031 misura la forbice 8-10 s con SIGKILL e V-029 misura 480-574 ms "
        f"con l'arresto ordinato.\n{scena.uscita}"
    )
    assert perse == 0, (
        f"{perse} scritture perse. V-033 ne misura zero su 12 901 con `w: majority`, che "
        f"è il valore predefinito del server dalla 5.0: se qui ne mancano, o la scena "
        f"scrive con un'altra write concern o V-033 va rimisurata.\n{scena.uscita}"
    )


# --- L'Atto III: il backup a caldo e la copia rimessa altrove ---------------------------

MONGOLAB: Final = Path(sys.executable).parent / "mongolab"
"""Il comando installato accanto all'interprete che sta girando queste prove.

Non `uv run`: dentro `pytest` l'ambiente è già quello giusto, e un `uv run` annidato
ricontrollerebbe il lock e potrebbe scaricare. La prova deve girare anche senza rete, che
è la condizione del laboratorio in sala.
"""

NODO: Final = "mongo-rs-1"
"""Dove `mongodump` gira, e dove il dump resta ad aspettare `demo restore`.

Fisso e non «il primario»: il file atterra nel filesystem di **quel** container, e le due
scene sono due comandi separati. Un nodo scelto due volte è un nodo che dopo un'elezione
può essere due nodi diversi, e il restore cercherebbe la copia dove non è.
"""

CARICO_ATTO_III_S: Final = "3"
"""Tre secondi invece dei dieci del §6.4: servono scritture prima del dump, non venti."""

# `ritmo       prima 595/s · durante 692/s · calo -16.2%`
RITMO = re.compile(
    r"^ritmo\s+prima (?P<prima>[\d.]+)/s\s+·\s+durante (?P<durante>[\d.]+)/s"
)
# `prossimo: mongolab demo restore --target rs --from /tmp/... --collection carico-...`
PROSSIMO = re.compile(r"^prossimo: .*--collection (?P<collezione>\S+)\s*$")
# `restore     3908 all'origine · 3802 nella copia · differenza 106`
CONTEGGI = re.compile(
    r"^restore\s+(?P<origine>\d+) all'origine\s+·\s+(?P<copia>\d+) nella copia"
    r"\s+·\s+differenza (?P<differenza>-?\d+)\s*$"
)


def _dall_host(*argomenti: str) -> tuple[int, str]:
    """Avvia `mongolab` come lo avvia chi presenta: restituisce l'esito **e** ciò che ha
    scritto, anche quando è andata male.

    Senza `cwd`: la directory di partenza è quella di `pytest`, cioè `app/`, che **non** è
    la radice del repository. È voluto — è la sola cosa che mette alla prova il `dove` che
    `strumento_di` passa a `SubprocessBackup`.

    Non solleva. Sembra il contrario di quello che una prova dovrebbe fare, ed è successo
    per averlo fatto: una versione precedente sollevava, e il chiamante perdeva il nome
    della collezione di carico — che la scena annuncia **prima** di scrivere — insieme
    all'eccezione. Il risultato era che ogni scena fallita lasciava una collezione nel
    replica set, cioè proprio nel caso in cui la pulizia serve di più. Il codice torna al
    chiamante, che lo verifica dopo essersi segnato ciò che c'è da togliere.
    """
    esito = subprocess.run(
        [str(MONGOLAB), *argomenti],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    return esito.returncode, esito.stdout + esito.stderr


RIPRESA_DEL_RUOLO_S: Final = 60.0
"""Quanto si concede a `mongo-rs-1` per riprendersi il primato dopo l'Atto II.

Non è un ritardo di comodo: è la stessa attesa che chi presenta fa in sala, e ha una
ragione nel `compose`. Il primo membro ha `priority: 2` in
`docker/02-replicaset/init/10-rs-initiate.js` **apposta** perché il ruolo torni prevedibile
dopo un guasto; il ritorno però non è istantaneo, e finché non è avvenuto `demo
backup-live` si rifiuta di partire — correttamente, perché dall'host si scrive solo sul
nodo pubblicato. Misurato: eseguendo i due Atti di fila senza attesa, la scena esce con
codice 2 e il messaggio del guardiano.
"""


def _aspetta_che_torni_primario(
    cliente: MongoClient[dict[str, Any]], secondi: float = RIPRESA_DEL_RUOLO_S
) -> float:
    """Aspetta che il nodo pubblicato sull'host sia di nuovo il primario. Torna i secondi.

    Serve perché questo modulo gira i due Atti nell'ordine in cui vanno in scena, e l'Atto
    II lascia `mongo-rs-1` secondario per qualche secondo. Senza questa attesa la prova
    dell'Atto III fallirebbe a intermittenza — e fallirebbe **giustamente**, con il rifiuto
    del guardiano, il che è il modo peggiore di fallire: un rosso che accusa il codice
    quando il difetto è nel momento in cui lo si è chiamato.

    Con `hello` e non con l'ispettore della produzione: da qui la connessione è diretta, e
    ciò che interessa è la sola cosa che decide se il carico può scrivere, cioè se **questo**
    nodo accetta scritture. `isWritablePrimary` è la risposta a quella domanda e a nessuna
    altra.
    """
    partenza = time.monotonic()
    while (trascorsi := time.monotonic() - partenza) < secondi:
        if cliente.admin.command("hello").get("isWritablePrimary", False):
            return trascorsi
        time.sleep(1.0)
    raise AssertionError(
        f"dopo {secondi:.0f} s il nodo pubblicato non è tornato primario. Con "
        "`priority: 2` dovrebbe riprendersi il ruolo da sé: se non succede, il replica "
        "set è rimasto in uno stato che `make reset-02` risolve e questa prova no."
    )


def _togli_il_dump(dove: str) -> None:
    """Porta via la directory del dump da dentro il nodo, con lo stesso frasario della scena.

    Con `ComandiCompose.dentro` e non con un `docker exec` scritto qui: la riga che pulisce
    e la riga che ha creato devono venire dallo stesso posto, altrimenti il giorno in cui
    lo stack cambia nome la prova smette di pulire e nessuno se ne accorge — i dump
    resterebbero nel container fino al `make down`.
    """
    subprocess.run(
        [*comandi_di(BERSAGLI["rs"]).dentro(NODO, "rm"), "-rf", dove],
        cwd=radice(),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_l_atto_iii_esce_dallo_stack_vero(
    stack02: MongoClient[dict[str, Any]],
) -> None:
    """Il dump a caldo sotto carico, poi la copia rimessa accanto, e i conteggi si toccano.

    **Una prova sola per due comandi**, perché sul palco sono due comandi consecutivi e il
    secondo consuma ciò che il primo ha lasciato nel nodo. Spezzarla vorrebbe dire o girare
    il dump due volte, o fabbricare a mano una directory che finge di essere un dump: nel
    primo caso si paga il doppio, nel secondo non si prova più il pezzo che conta, cioè che
    le due scene si passino qualcosa di vero.

    **Comincia aspettando.** Se l'Atto II è appena passato, `mongo-rs-1` è rientrato da
    poco e il ruolo di primario non è ancora suo: da qui si scrive solo su quel nodo, e la
    scena si rifiuterebbe di partire. È la stessa attesa che fa chi presenta, e metterla
    qui è dichiarare che l'ordine delle due scene ha un costo in secondi.

    **Ciò che si verifica è la differenza, non un numero.** Quanti documenti entrino
    durante il dump dipende dalla macchina, e un'asserzione su una cifra sarebbe rossa
    altrove senza che niente sia rotto. Quello che deve valere sempre è il **verso**: la
    copia non può contenere più di quanti ce n'erano, e il divario è esattamente ciò che è
    stato scritto mentre `mongodump` leggeva — cioè il prezzo di non aver fermato il
    servizio, che è la cosa che l'Atto III esiste per far vedere.
    """
    _aspetta_che_torni_primario(stack02)
    dump = f"/tmp/{PREFISSO_PROVE}{uuid4().hex[:12]}"
    ripristinato = f"{PREFISSO_PROVE}{uuid4().hex[:12]}"
    collezione: str | None = None
    try:
        codice, backup = _dall_host(
            "demo", "backup-live",
            "--target", "rs",
            "--sink", "plain",
            "--carico", CARICO_ATTO_III_S,
            "--out", dump,
            "--node", NODO,
        )
        # Il nome della collezione **prima** di verificare il codice di uscita: la scena lo
        # annuncia sulla prima riga, prima ancora di scrivere il primo documento, e una
        # scena morta a metà è esattamente quella che lascia i residui.
        annuncio = DESTINAZIONE.search(backup)
        collezione = annuncio.group("collezione") if annuncio is not None else None
        assert codice == 0, f"`demo backup-live` è uscito con {codice}.\n{backup}"
        assert collezione is not None, f"la scena non ha annunciato dove scrive.\n{backup}"

        # La riga che chi presenta incolla deve nominare la collezione che il carico ha
        # davvero riempito: se le due divergessero, il comando suggerito girerebbe a vuoto
        # su un nome che non esiste, e lo farebbe davanti alla sala.
        assert _riga(backup, PROSSIMO).group("collezione") == collezione

        ritmo = _riga(backup, RITMO)
        prima, durante = float(ritmo.group("prima")), float(ritmo.group("durante"))
        assert prima > 0.0, f"nessuna scrittura prima del dump.\n{backup}"
        # Il carico **non si ferma** quando `mongodump` parte: è tutta la tesi dell'Atto
        # III, e uno zero qui vorrebbe dire che il dump ha bloccato il database — cioè che
        # la promessa del copione è falsa. Di quanto cali lo decide chi guarda; che il
        # servizio resti in piedi lo decide questa riga.
        assert durante > 0.0, (
            f"zero scritture durante il dump: il servizio si è fermato, e il backup a "
            f"caldo non sarebbe più a caldo.\n{backup}"
        )

        codice, ripristino = _dall_host(
            "demo", "restore",
            "--target", "rs",
            "--sink", "plain",
            "--from", dump,
            "--into", ripristinato,
            "--collection", collezione,
            "--node", NODO,
        )
        assert codice == 0, f"`demo restore` è uscito con {codice}.\n{ripristino}"
    finally:
        _togli_il_dump(dump)
        stack02.drop_database(ripristinato)
        if collezione is not None:
            stack02[DATABASE].drop_collection(collezione)

    conteggi = _riga(ripristino, CONTEGGI)
    origine = int(conteggi.group("origine"))
    copia = int(conteggi.group("copia"))
    differenza = int(conteggi.group("differenza"))

    assert copia > 0, f"la copia è vuota: il restore non ha portato niente.\n{ripristino}"
    assert copia <= origine, (
        f"nella copia ci sono {copia} documenti e all'origine {origine}: una copia più "
        f"grande dell'originale vuol dire che il restore ha scritto due volte.\n{ripristino}"
    )
    assert differenza == origine - copia
