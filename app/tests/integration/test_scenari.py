"""La scena del failover contro lo stack vero, con la prova che fa da umano.

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
"""

import re
from typing import Any

import pytest
from pymongo import MongoClient

from tests.integration.ambiente import (
    IMMAGINE,
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


def _riga(scena: Scena, quale: re.Pattern[str]) -> re.Match[str]:
    """La prima riga che corrisponde, o un fallimento che mostra tutto ciò che è uscito.

    Il testo intero nel messaggio e non solo l'asserzione: quando questa prova fallisce, il
    replica set è già tornato a posto e la scena non si ripete gratis. Quello che è uscito
    è l'unico documento di che cosa è successo.
    """
    for riga in scena.righe:
        trovata = quale.search(riga)
        if trovata is not None:
            return trovata
    raise AssertionError(f"nessuna riga per {quale.pattern!r}.\n{scena.uscita}")


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

    fasi = tuple(_riga(scena, FASI).group("elenco").split(" · "))
    assert fasi == FASI_DEL_COPIONE

    caduto, rientrato = (riga.split()[-1] for riga in scena.comandi)
    assert scena.comandi[0].endswith(f"kill -s SIGKILL {caduto}")
    assert scena.comandi[1].endswith(f"start {rientrato}")
    assert caduto == rientrato, "il nodo rimesso in servizio non è quello ucciso"

    # L'avvicendamento si legge dal **resoconto della scena** e non ricostruendolo dalle
    # righe `SERVER … → primario`: di quelle la prima è la scoperta iniziale, che nomina
    # il primario di sempre, e una prova che la scambiasse per l'elezione passerebbe anche
    # se il guasto non fosse mai arrivato. Qui si verifica ciò che la sala legge.
    avvicendamento = _riga(scena, AVVICENDAMENTO)
    prima, dopo = avvicendamento.group("prima"), avvicendamento.group("dopo")
    assert prima.startswith(f"{caduto}:"), (
        f"la cronaca dice che il primario era {prima}, ma la scena ha ucciso {caduto}"
    )
    assert dopo != prima, "nessuno ha preso il posto del primario ucciso"

    numeri = _riga(scena, DUE_NUMERI)
    interruzione = float(numeri.group("interruzione"))
    perse = int(numeri.group("perse"))
    _porta_via(_riga(scena, DESTINAZIONE).group("collezione"))

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
