"""L'applicazione dentro la rete Compose, che è il solo posto da cui la scoperta funziona.

Questo modulo esiste per rendere ripetibile la dimostrazione che
[ADR-0012](../../../docs/Decision.md#adr-0012) chiedeva e non aveva. La decisione diceva
che dall'host il replica set si vede male — un `ReplicaSetNoPrimary` su un set sanissimo,
perché i nomi che il set rimanda sono nomi di servizi Compose e l'host non li risolve
(M-019) — e portava con sé una riserva dichiarata: *la documentazione non afferma che il
driver usi gli host memorizzati nella configurazione del set; se lo si vuole affermare, va
mostrato*. Il Task 12 lo mostra, e queste prove sono il modo di non doverlo rimostrare a
mano ogni volta.

## Perché passano da `docker compose run` e non da un client Python

La domanda a cui rispondono non è «pymongo scopre i membri?» ma «l'applicazione di questo
repository, avviata come la avvierà chi guarda, scopre i membri?». Sono due domande
diverse: la prima si prova con un client, la seconda solo eseguendo il servizio `app` che
i tre file Compose dichiarano, con il suo `MONGOLAB_PUNTO_DI_VISTA=rete`, la sua rete e le
sue credenziali. Una prova che costruisse un `MongoClient` dall'host non potrebbe nemmeno
risolvere `mongo-rs-1`.

## Perché saltano invece di costruire l'immagine

`make app-image` vuole la rete la prima volta. Una suite di prove che si mette a scaricare
`python:3.13-slim` è una suite che, la sera prima del talk e senza rete, non finisce. Chi
deve accorgersi che l'immagine manca è `tools/preflight.sh`, che infatti blocca e dice
quale comando eseguire; qui il salto porta la stessa frase.
"""

import re
from typing import Any

import pytest
from pymongo import MongoClient

from tests.integration.ambiente import (
    IMMAGINE,
    STACK,
    immagine_in_cache,
    nel_container,
)

servono_immagine = pytest.mark.skipif(
    not immagine_in_cache(),
    reason=f"l'immagine {IMMAGINE} non è costruita: «make app-image» (richiede rete)",
)

# `mongo-rs-1:27017      primario` — l'indirizzo, spazi, il ruolo. La colonna è larga
# quanto l'indirizzo più lungo (vedi `presentation/rapporto.py`), quindi il numero di
# spazi non si può fissare: fissarlo renderebbe questa prova un controllo di
# formattazione travestito da controllo di topologia.
RIGA_SERVER = re.compile(r"^\s+(?P<indirizzo>[a-z0-9.-]+:\d+)\s+(?P<ruolo>\S+)\s")


def server_visti(rapporto: str) -> dict[str, str]:
    """`{indirizzo: ruolo}` dalle righe della topologia, così come le legge il pubblico.

    Si legge il **testo stampato** e non un oggetto interno, perché ciò che deve essere
    vero è quello che comparirà sullo schermo in sala. Un rapporto giusto costruito da una
    topologia giusta e stampato male è, dal fondo della sala, un rapporto sbagliato.
    """
    return {
        trovato.group("indirizzo"): trovato.group("ruolo")
        for riga in rapporto.splitlines()
        if (trovato := RIGA_SERVER.match(riga))
    }


@servono_immagine
def test_lo_standalone_si_vede_per_nome_di_servizio(stack01: MongoClient[Any]) -> None:
    """Passo 3: qui `directConnection` resta acceso, e va bene così.

    Un mongod solo non conosce nessun altro: non c'è niente da scoprire, e la differenza
    con gli altri due stack è voluta. Ciò che cambia rispetto all'host è solo il nome —
    `mongo-standalone` invece di `localhost` — ed è la prova che il container è davvero
    attaccato alla rete dello stack e non sta parlando con sé stesso.
    """
    uscita = nel_container(STACK["01"], "stats", "--target", "standalone")

    assert "topologia" in uscita
    visti = server_visti(uscita)
    assert visti == {"mongo-standalone:27017": "standalone"}, uscita


@servono_immagine
def test_dentro_la_rete_il_replica_set_ha_un_primario(stack02: MongoClient[Any]) -> None:
    """La dimostrazione che ADR-0012 chiedeva, nella forma in cui il talk la mostrerà.

    Dall'host lo stesso comando stampa `topologia singola` e un indirizzo solo, perché
    `directConnection` spegne la scoperta per non incappare in M-019. Da qui dentro
    stampa tre membri e dice quale comanda.
    """
    uscita = nel_container(STACK["02"], "stats", "--target", "rs")

    assert "replica set con primario" in uscita, uscita
    assert "rs0" in uscita, uscita

    visti = server_visti(uscita)
    assert set(visti) == {
        "mongo-rs-1:27017",
        "mongo-rs-2:27017",
        "mongo-rs-3:27017",
    }, uscita
    ruoli = sorted(visti.values())
    assert ruoli == ["primario", "secondario", "secondario"], uscita


@servono_immagine
def test_un_seme_solo_basta_a_trovare_tutti_e_tre(stack02: MongoClient[Any]) -> None:
    """La riserva dichiarata di ADR-0012, chiusa: quei due indirizzi il client non li aveva.

    Le prove qui sopra passano tre semi, ed è ciò che fa la configurazione di produzione;
    ma un client che riceve tre indirizzi e ne conosce tre non ha dimostrato niente —
    potrebbe non aver mai letto la configurazione del set. Questa prova gliene passa
    **uno**, e sceglie un secondario: se alla fine ne conosce tre e sa chi è il primario,
    gli altri due glieli ha detti il set.

    Sostituisce l'entrypoint invece di usare `mongolab`, perché il numero di semi è una
    scelta della mappa dei bersagli e non un'opzione della riga di comando — e deve
    restare tale: un `--seed` esposto all'utente sarebbe un modo di sbagliare in demo.
    La credenziale non passa dalla riga di comando; il codice la legge dall'ambiente che
    Compose ha già messo nel container.
    """
    programma = (
        "import os;"
        "from pymongo import MongoClient;"
        "c=MongoClient('mongodb://mongo-rs-2:27017/',replicaSet='rs0',"
        "username=os.environ['UTENTE_AMMINISTRATORE'],"
        "password=os.environ['PASSWORD_AMMINISTRATORE'],"
        "serverSelectionTimeoutMS=20000);"
        "c.admin.command('hello');"
        "d=c.topology_description;"
        "print(d.topology_type_name);"
        "print(' '.join(sorted(f'{h}:{p}' for h,p in d.server_descriptions())));"
        "c.close()"
    )
    uscita = nel_container(
        STACK["02"], "-c", programma, entrypoint="python"
    ).splitlines()

    assert uscita[0] == "ReplicaSetWithPrimary", uscita
    assert uscita[1].split() == [
        "mongo-rs-1:27017",
        "mongo-rs-2:27017",
        "mongo-rs-3:27017",
    ], uscita


@servono_immagine
def test_lo_sharded_si_vede_attraverso_il_router(stack03: MongoClient[Any]) -> None:
    """Su questo stack la scoperta c'è, ma trova router e non membri.

    `directConnection` è spento come sul 02, e per la stessa ragione — un mongos è un
    punto d'ingresso, non un'istanza da interrogare direttamente — ma ciò che il client
    scopre attraverso di lui sono gli shard, non i server: la topologia si legge
    `sharded`, e i conteggi per shard arrivano dal config server.
    """
    uscita = nel_container(STACK["03"], "stats", "--target", "sharded")

    # `in uscita` non basterebbe: la parola «sharded» compare già nel titolo, che è il
    # nome del bersaglio, e la prova passerebbe anche con la topologia sconosciuta.
    topologia = next(r for r in uscita.splitlines() if r.startswith("topologia"))
    assert topologia.split() == ["topologia", "sharded"], uscita
    visti = server_visti(uscita)
    assert visti == {"mongos:27017": "router"}, uscita
