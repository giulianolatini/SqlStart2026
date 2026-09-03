"""I due rapporti che non sono cronaca: la fotografia di `stats`, il consuntivo di `workload`.

`righe.py` trasforma **un** evento in **una** riga, e va bene per ciò che scorre. Ma
`mongolab stats` non emette eventi — è una fotografia — e la fine di una corsa non è un
evento ma un bilancio. Sono due testi con regole diverse: non scorrono, quindi possono
occupare più di una riga; stanno sullo stesso schermo, quindi il budget di sala vale
anche per loro, e infatti il taglio arriva da `righe.tronca`.

## Perché in `presentation/` e non nel composition root

La tentazione era scrivere queste stringhe dentro `cli.py`, dove vengono stampate. Il
§6.1 dice che il composition root **costruisce e inietta**, e formattare è un'altra cosa:
il giorno in cui il Task 18 vorrà lo stesso rapporto dentro una registrazione, o il Task
13 lo vorrà come prima fase di uno scenario, dovrebbe importarlo da `cli.py` — cioè
importare il punto d'ingresso, che è il verso sbagliato di ogni dipendenza.

## Perché `rapporto` prende la porta e non i quattro valori già letti

La forma più pura sarebbe `rapporto(topologia, stato, statistiche, distribuzione)`: pura
formattazione, nessuna dipendenza. Costerebbe però quattro chiamate a `ispettore.*`
scritte nel composition root, che è precisamente il lavoro che non deve stare lì, oppure
un quinto modulo in `application/` che non farebbe altro che leggere quattro valori e
metterli in una tupla.

La scelta è la terza: questo modulo riceve `ClusterInspector`, cioè **la porta**, non
l'adattatore. Non sa che esiste pymongo, si prova con `FakeInspector`, e la dipendenza
punta verso il dominio come tutte le altre. Il giorno in cui la fotografia servisse a due
consumatori con esigenze diverse, la lettura si sposterebbe in `application/` e questa
firma cambierebbe: è una riserva dichiarata, non un'architettura definitiva.

## Perché i valori mancanti si dichiarano

`serverStatus` attraverso un mongos non ha metà dei campi di un mongod — lo dice già
`inspector.py`, ed è il motivo per cui la porta restituisce il documento grezzo. Un
rapporto che scrivesse `connessioni 0` dove il campo non c'è direbbe una cosa falsa
proprio nello stack in cui la fotografia serve a spiegare che il router non è un mongod.
Dove il numero manca compare `IGNOTO`, che si legge come «non c'era» e non come «zero».
"""

from typing import Mapping, Sequence

from mongolab.application.workload import Latenze, Riepilogo
from mongolab.domain.modelli import ContoShard, DescrizioneServer, DescrizioneTopologia
from mongolab.domain.porte import ClusterInspector
from mongolab.presentation.righe import COLONNE_SALA, tronca

__all__ = [
    "GUTTER",
    "IGNOTO",
    "INDIRIZZO",
    "SEPARATORE",
    "rapporto",
    "riassunto",
]

IGNOTO = "—"
"""Il segno che sta dove un numero non c'era. Vedi la docstring del modulo."""

SEPARATORE = " · "
"""Fra due fatti sulla stessa riga.

Un punto mediano e non una virgola: le cifre italiane usano già la virgola come
separatore decimale, e «dati 12,3 MB, indici 2,1 MB» si legge male proprio nel punto in
cui la sala sta cercando i numeri.
"""

GUTTER = 12
"""Quanto spazio prende l'etichetta a sinistra, continuazioni comprese.

Le righe di continuazione sono rientrate della stessa misura: è ciò che fa leggere
l'elenco dei server come una cosa sola sotto `topologia`, invece che come quattro righe
senza padrone.
"""

INDIRIZZO = 22
"""Il minimo della colonna degli indirizzi: `localhost:27021` e i suoi fratelli.

Non è il massimo. Chi stampa la fotografia allarga la colonna quando serve — vedi
`_larghezza_indirizzi` — perché dentro la rete Compose gli indirizzi sono nomi di
servizio e questo numero non basta più.
"""


def rapporto(
    ispettore: ClusterInspector,
    *,
    titolo: str,
    larghezza: int | None = COLONNE_SALA,
) -> str:
    """La fotografia dello stack: topologia, server, database, distribuzione.

    `titolo` arriva da fuori — è il composition root che sa quale `--target` è stato
    scritto e in quale directory sta lo stack — perché questo modulo non conosce la mappa
    dei bersagli e non deve: sta in `presentation/`, e `bersagli.py` sta
    nell'infrastruttura.
    """
    # **L'ordine di lettura non è quello di stampa, ed è deliberato.** `server_status`
    # esegue un comando, quindi obbliga il driver a una *selezione*, cioè a guardare;
    # `topology` invece riferisce ciò che il client crede in questo istante, senza
    # aspettare niente — ed è giusto così, perché è quella proprietà a rendere visibile
    # l'attimo in cui durante un'elezione il client non sa ancora. Su un client appena
    # costruito, però, quell'attimo è l'avvio: letta per prima, la topologia di uno
    # standalone sanissimo si legge `sconosciuta`. Misurato eseguendo, non dedotto.
    stato = ispettore.server_status()
    statistiche = ispettore.db_stats()
    distribuzione = ispettore.shard_distribution()
    vista = ispettore.topology()

    linee = [titolo]
    linee += _topologia(vista)
    linee += _server(stato)
    linee += _database(statistiche)
    linee += _shard(distribuzione)
    return "\n".join(tronca(linea, larghezza) for linea in linee)


def riassunto(corsa: Riepilogo, *, larghezza: int | None = COLONNE_SALA) -> str:
    """Che cosa resta da leggere quando il carico ha finito.

    La sezione delle letture compare **solo se ci sono state**: `--readers 0` è un caso
    normale, e quattro zeri sotto la voce «letture» si leggono come un guasto invece che
    come un'assenza.
    """
    linee = [
        _voce(
            "carico",
            f"{corsa.scritture} scritture",
            f"{corsa.riuscite} confermate",
            f"{corsa.fallite} fallite",
            f"{corsa.ritentate} ritentate",
            f"{corsa.documenti_confermati} documenti",
        )
    ]
    linee += _latenze("latenze", corsa.latenze)
    if corsa.letture:
        linee.append(
            _voce(
                "letture",
                f"{corsa.letture} letture",
                f"{corsa.letture_riuscite} riuscite",
                f"{corsa.letture_fallite} fallite",
                f"{corsa.documenti_letti} documenti",
            )
        )
        linee += _latenze("latenze", corsa.latenze_letture)
    return "\n".join(tronca(linea, larghezza) for linea in linee)


# --- Le voci del rapporto ---------------------------------------------------------------


def _voce(etichetta: str, *fatti: str) -> str:
    return f"{etichetta:<{GUTTER}}" + SEPARATORE.join(fatti)


def _sotto(*fatti: str) -> str:
    """Una riga di continuazione: nessuna etichetta, lo stesso rientro."""
    return " " * GUTTER + SEPARATORE.join(fatti)


def _topologia(vista: DescrizioneTopologia) -> list[str]:
    intestazione = [vista.tipo.value]
    if vista.nome_set is not None:
        intestazione.append(vista.nome_set)
    larghezza = _larghezza_indirizzi(vista.server)
    return [_voce("topologia", *intestazione)] + [
        _sotto(_riga_server(server, larghezza)) for server in vista.server
    ]


def _larghezza_indirizzi(server: Sequence[DescrizioneServer]) -> int:
    """Quanto spazio prende la colonna degli indirizzi: il più lungo, più uno.

    Una larghezza fissa a 22 è bastata finché gli indirizzi erano `localhost:27021`. Dal
    Task 12 l'applicazione guarda anche da dentro la rete Compose, dove sono nomi di
    servizio, e `mongo-standalone:27017` ne misura esattamente ventidue: la colonna si
    riempiva tutta e la riga stampava `mongo-standalone:27017standalone`, due parole
    diverse lette come una. Misurato eseguendo, la prima volta che il container ha parlato.

    Il massimo si calcola su tutti i server insieme e non riga per riga, perché una
    colonna che cambia larghezza a ogni riga non è una colonna. Il minimo resta 22, così
    la fotografia dall'host è la stessa di prima.
    """
    piu_lungo = max((len(uno.indirizzo) for uno in server), default=0)
    return max(INDIRIZZO, piu_lungo + 1)


def _riga_server(server: DescrizioneServer, larghezza: int = INDIRIZZO) -> str:
    ritardo = IGNOTO if server.ritardo_ms is None else f"{server.ritardo_ms:.1f} ms"
    riga = f"{server.indirizzo:<{larghezza}}{server.ruolo.value:<16}{ritardo:>10}"
    return riga if server.errore is None else f"{riga}  {server.errore}"


def _server(stato: Mapping[str, object]) -> list[str]:
    processo = _testo(stato, "process")
    versione = _testo(stato, "version")
    attivo = _numero(stato, "uptime")
    connessioni = _intero(stato, "connections", "current")
    return [
        _voce(
            "server",
            f"{processo} {versione}",
            f"attivo da {IGNOTO if attivo is None else _durata(attivo)}",
            f"connessioni {IGNOTO if connessioni is None else connessioni}",
        )
    ]


def _database(statistiche: Mapping[str, object]) -> list[str]:
    documenti = _intero(statistiche, "objects")
    dati = _intero(statistiche, "dataSize")
    indici = _intero(statistiche, "indexSize")
    return [
        _voce(
            "database",
            _testo(statistiche, "db"),
            f"{IGNOTO if documenti is None else documenti} documenti",
            f"dati {IGNOTO if dati is None else _byte(dati)}",
            f"indici {IGNOTO if indici is None else _byte(indici)}",
        )
    ]


def _shard(distribuzione: Sequence[ContoShard]) -> list[str]:
    if not distribuzione:
        # Dichiarare il vuoto invece di omettere la voce: su un replica set la domanda
        # «e gli shard?» è legittima, e una riga assente si legge come una dimenticanza.
        return [_voce("shard", "nessuno: questo non è uno sharded cluster")]
    prima, *altri = distribuzione
    return [_voce("shard", _riga_shard(prima))] + [
        _sotto(_riga_shard(conto)) for conto in altri
    ]


def _riga_shard(conto: ContoShard) -> str:
    return f"{conto.shard:<18}{conto.documenti} documenti{SEPARATORE}{conto.chunk} chunk"


def _latenze(etichetta: str, latenze: Latenze | None) -> list[str]:
    if latenze is None:
        return []
    return [
        _voce(
            etichetta,
            f"p50 {latenze.mediana_ms:.1f} ms",
            f"p95 {latenze.p95_ms:.1f} ms",
            f"p99 {latenze.p99_ms:.1f} ms",
            f"max {latenze.massimo_ms:.1f} ms",
            f"{latenze.campioni} campioni",
        )
    ]


# --- I formati ---------------------------------------------------------------------------


def _testo(mappa: Mapping[str, object], chiave: str) -> str:
    valore = mappa.get(chiave)
    return IGNOTO if valore is None else str(valore)


def _numero(mappa: Mapping[str, object], *strada: str) -> float | None:
    """Il numero in fondo a un percorso di chiavi, o `None` se il percorso non c'è.

    `strada` è variadica per un caso solo, ma è quello che conta: `connections.current`
    sta annidato, e un `mappa["connections"]["current"]` esploderebbe con `TypeError` —
    non `KeyError` — quando `connections` manca del tutto, cioè attraverso un mongos.

    `bool` esce per primo perché in Python è un intero, e un campo che vale `True`
    diventerebbe il numero 1 invece di dichiararsi non numerico.
    """
    corrente: object = mappa
    for chiave in strada:
        if not isinstance(corrente, Mapping):
            return None
        corrente = corrente.get(chiave)
    if isinstance(corrente, bool) or not isinstance(corrente, (int, float)):
        return None
    return float(corrente)


def _intero(mappa: Mapping[str, object], *strada: str) -> int | None:
    valore = _numero(mappa, *strada)
    return None if valore is None else int(valore)


def _byte(quanti: int) -> str:
    """Byte in una misura che si legge a voce, con 1024 per gradino.

    Mille e ventiquattro e non mille, per la stessa ragione di `zavorra.py`: il limite di
    MongoDB è 16 *mebibyte*, e usare due unità diverse nella stessa applicazione
    metterebbe due numeri incoerenti sulla stessa slide.
    """
    for unita, soglia in (("GB", 1024**3), ("MB", 1024**2), ("kB", 1024)):
        if quanti >= soglia:
            return f"{quanti / soglia:.1f} {unita}"
    return f"{quanti} B"


def _durata(secondi: float) -> str:
    """`11520.0` diventa `3 h 12 m`. Un uptime in secondi non si legge dalla decima fila."""
    interi = int(secondi)
    ore, resto = divmod(interi, 3600)
    minuti, rimasti = divmod(resto, 60)
    if ore:
        return f"{ore} h {minuti} m"
    if minuti:
        return f"{minuti} m {rimasti} s"
    return f"{rimasti} s"
