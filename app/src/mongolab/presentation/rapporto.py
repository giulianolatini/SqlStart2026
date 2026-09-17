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

import json
from typing import Mapping, Sequence

from mongolab.application.scenari import (
    EsitoBackup,
    EsitoFailover,
    EsitoRestore,
    EsitoSharding,
    Ritmo,
)
from mongolab.application.topologia import Interruzione
from mongolab.application.workload import Latenze, Riepilogo
from mongolab.domain.modelli import (
    ContoCollezione,
    ContoShard,
    DescrizioneServer,
    DescrizioneTopologia,
    Distribuzione,
    Documento,
    Piano,
    Progress,
)
from mongolab.domain.porte import ClusterInspector
from mongolab.presentation.righe import COLONNE_SALA, tronca

__all__ = [
    "GUTTER",
    "IGNOTO",
    "INDIRIZZO",
    "SEPARATORE",
    "copia",
    "cronaca",
    "rapporto",
    "riassunto",
    "ripristino",
    "spartizione",
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
    collezione: str,
    larghezza: int | None = COLONNE_SALA,
) -> str:
    """La fotografia dello stack: topologia, server, database, distribuzione.

    `titolo` arriva da fuori — è il composition root che sa quale `--target` è stato
    scritto e in quale directory sta lo stack — perché questo modulo non conosce la mappa
    dei bersagli e non deve: sta in `presentation/`, e `bersagli.py` sta
    nell'infrastruttura.

    `collezione` arriva da fuori per la stessa ragione, e da ADR-0104: delle quattro
    domande dell'ispettore la distribuzione è l'unica che è **per collezione**, e il nome
    `ordini` sta in `bersagli.py`, cioè dall'altra parte del confine.
    """
    # **L'ordine di lettura non è quello di stampa, ed è deliberato.** `server_status`
    # esegue un comando, quindi obbliga il driver a una *selezione*, cioè a guardare;
    # `topology` invece riferisce ciò che il client crede in questo istante, senza
    # aspettare niente — ed è giusto così, perché è quella proprietà a rendere visibile
    # l'attimo in cui durante un'elezione il client non sa ancora. Su un client appena
    # costruito, però, quell'attimo è l'avvio: letta per prima, la topologia di uno
    # standalone sanissimo si legge `sconosciuta`. Misurato eseguendo, non dedotto.
    stato = ispettore.server_status()
    conti = ispettore.collection_counts()
    statistiche = ispettore.db_stats()
    distribuzione = ispettore.shard_distribution(collezione)
    vista = ispettore.topology()

    linee = [titolo]
    linee += _topologia(vista)
    linee += _server(stato)
    # Il dettaglio **prima** della somma: la riga del database è un totale, e un
    # totale stampato sopra i suoi addendi si legge come il primo di essi. È
    # precisamente l'errore di lettura da cui questa riga viene (ADR-0121).
    linee += _collezioni(conti)
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


def cronaca(scena: EsitoFailover, *, larghezza: int | None = COLONNE_SALA) -> str:
    """Come è finita la scena del failover: i due numeri, e quel tanto che li spiega.

    **I due numeri stanno sulla prima riga**, e non è impaginazione. Il §6.3 li chiama
    per nome — «durata dell'interruzione» e «scritture perse» — come le due cose che
    giustificano l'esistenza di questa applicazione, e chi guarda dalla decima fila legge
    la prima riga e le ultime due. Metterli in fondo, dopo tre riepiloghi di carico, vuol
    dire farli scorrere via insieme alle latenze.

    Le scritture perse e quelle non confermate restano **due voci distinte**, perché sono
    due fenomeni opposti e nessuno dei due è il negativo dell'altro: il perché sta nella
    docstring di `Bilancio`, e questa funzione si limita a non ricomporlo in un numero
    solo con il segno.
    """
    bilancio = scena.bilancio
    linee = [
        _voce(
            "failover",
            f"interruzione {_millisecondi(scena.durata_interruzione_ms)}",
            f"scritture perse {bilancio.scritture_perse}",
        )
    ]
    linee += _avvicendamento(bilancio.interruzione)
    linee.append(
        _voce(
            "scritture",
            f"{bilancio.confermate} confermate",
            f"{bilancio.ritrovate} ritrovate",
            f"{bilancio.scritture_non_confermate} non confermate",
        )
    )
    linee += _fase("prima", scena.prima)
    linee += _fase("durante", scena.durante)
    linee += _fase("dopo", scena.dopo)
    if scena.fasi:
        linee.append(_voce("fasi", *scena.fasi))
    return "\n".join(tronca(linea, larghezza) for linea in linee)

def copia(scena: EsitoBackup, *, larghezza: int | None = COLONNE_SALA) -> str:
    """Come è andato il backup a caldo: il ritmo di prima accanto al ritmo di durante.

    **I due ritmi stanno sulla prima riga**, per la stessa ragione per cui i due numeri
    del failover stanno sulla prima riga di `cronaca`: la tesi dell'Atto III è che il dump
    non faccia crollare il throughput, e una tesi che si verifica confrontando due numeri
    va letta con i due numeri vicini. Separati da tre righe, la sottrazione toccherebbe
    alla sala mentre la scena è già passata.

    **Il calo è una percentuale con segno, non un giudizio.** Questa funzione non scrive
    «il dump non ha impatto»: scrive di quanto è calato, e chi guarda decide se è poco.
    Una riga che concludesse al posto del pubblico sarebbe la stessa cosa che il §6.3
    rimprovera ai benchmark altrui.

    L'ultima riga di `mongodump` compare per intero perché è la conferma che lo strumento
    dà di sé — «done dumping lab.carico (4460 documents)» — e riportarla è la differenza
    fra dire che il dump è andato bene e mostrarlo.
    """
    linee = [
        _voce(
            "ritmo",
            f"prima {_al_secondo(scena.prima)}",
            f"durante {_al_secondo(scena.durante)}",
            f"calo {_percentuale(scena.calo_percentuale)}",
        ),
        _voce(
            "dump",
            str(scena.destinazione),
            f"{scena.documenti} documenti in collezione",
        ),
    ]
    linee += _ultimo_avanzamento(scena.avanzamenti)
    linee += _fase("carico", scena.prima.riepilogo)
    linee += _fase("sotto dump", scena.durante.riepilogo)
    if scena.fasi:
        linee.append(_voce("fasi", *scena.fasi))
    return "\n".join(tronca(linea, larghezza) for linea in linee)


def ripristino(scena: EsitoRestore, *, larghezza: int | None = COLONNE_SALA) -> str:
    """I due conteggi del restore, e la differenza detta per quello che è.

    **La differenza non si chiama «perse».** Le scritture perse sono la voce del Blocco 2,
    e sono un'altra cosa: là il client aveva ricevuto una conferma e il documento non
    c'era più. Qui i documenti ci sono ancora, tutti, nel database di partenza: mancano
    **nella copia**, perché sono stati scritti mentre la copia veniva presa. Usare la
    stessa parola per i due fenomeni sarebbe l'errore più costoso che questo rapporto
    possa fare, perché arriverebbe nel momento in cui la sala sta imparando la differenza.
    """
    linee = [
        _voce(
            "restore",
            f"{scena.documenti_origine} all'origine",
            f"{scena.documenti_destinazione} nella copia",
            f"differenza {scena.differenza}",
        ),
        _sotto(f"{scena.sorgente} → {scena.destinazione}"),
    ]
    if not scena.combaciano:
        linee.append(
            _sotto(
                f"{scena.differenza} scritti mentre il dump era in corso: "
                "stanno nell'oplog, che il restore non riapplica"
            )
        )
    linee += _ultimo_avanzamento(scena.avanzamenti)
    if scena.fasi:
        linee.append(_voce("fasi", *scena.fasi))
    return "\n".join(tronca(linea, larghezza) for linea in linee)


def spartizione(scena: EsitoSharding, *, larghezza: int | None = COLONNE_SALA) -> str:
    """Il Blocco 3 in otto righe: le due colonne, i chunk fermi, i due piani.

    **Le due colonne stanno una sopra l'altra e non una accanto all'altra.** Affiancarle
    davvero vorrebbe dire due incolonnamenti su cento caratteri, cioè cinquanta per parte,
    cioè i nomi degli shard troncati proprio dove si legge la differenza. In verticale
    ciascuna riga è intera, e il confronto è fra la prima riga e la seconda — che è
    esattamente la distanza che l'occhio percorre senza aiuto.

    **La riga degli arrivi non è un di più: è la riga che rende vera la precedente.** I
    totali di `lab.ordini` contengono i ventimila documenti del seed, e duemila arrivati
    non si confrontano con ventiduemila presenti. Vedi `EsitoSharding.arrivi`, dove sta la
    misura che ha fatto aggiungere questa riga.

    **Il carico si dichiara.** L'ultima riga dice quante scritture ha fatto ciascuna
    corsa, e se le due non combaciano lo scrive. Due colonne accostate danno per scontato
    che il carico sia lo stesso; quando non lo è, la differenza fra le colonne non è più
    la chiave di shard ed è la riga più importante dello schermo.

    **Questa funzione non conclude.** Non scrive «lo sharding funziona»: scrive lo
    sbilancio, i chunk e i due stadi, e chi guarda decide. È la stessa regola di `copia`,
    e la ragione è la stessa per cui il §6.3 rimprovera i benchmark che concludono al
    posto di chi legge.
    """
    linee = _shard(scena.intera, "non sharded")
    linee += _shard(scena.dopo, "sharded")
    linee += _arrivi(scena.arrivi)
    linee.append(
        _voce(
            "bilancio",
            f"sbilancio {_punti(scena.sbilancio)}",
            f"chunk {_chunk_in_piu(scena.chunk_in_piu)}",
        )
    )
    linee.append(_voce("mirata", *_piano(scena.mirata)))
    linee.append(_voce("su tutti", *_piano(scena.sparpagliata)))
    linee.append(_voce("carico", *_carico(scena)))
    if scena.fasi:
        linee.append(_voce("fasi", *scena.fasi))
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


def _collezioni(conti: Sequence[ContoCollezione]) -> list[str]:
    """Una riga per collezione, e una riga che dichiara il vuoto quando non ce ne sono.

    La regola del vuoto è quella di `_shard`, e per la stessa ragione: su uno stack appena
    acceso, prima che il seed sia passato, la domanda «e le collezioni?» è legittima, e una
    voce assente si legge come una dimenticanza del programma invece che come una risposta
    del database.

    Le righe di continuazione usano `_sotto` come fa `_topologia`: l'etichetta si scrive
    una volta e le voci si incolonnano sotto, perché sei collezioni con sei etichette
    uguali a sinistra sono sei volte la stessa parola e una volta sola l'informazione.
    """
    if not conti:
        return [_voce("collezioni", "nessuna")]
    righe = [
        (_voce("collezioni", conto.nome, f"{conto.documenti} documenti"))
        if indice == 0
        else _sotto(conto.nome, f"{conto.documenti} documenti")
        for indice, conto in enumerate(conti)
    ]
    return righe


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


def _shard(distribuzione: Distribuzione, etichetta: str = "shard") -> list[str]:
    """Tre casi, tre righe diverse. Fino al Task 14 i primi due erano la stessa.

    Il caso di mezzo — c'è un cluster, la collezione non è distribuita — è la prima metà
    della scena del Blocco 3, e prima di ADR-0104 arrivava qui indistinguibile dal caso di
    chi un cluster non ce l'ha: entrambi una tupla vuota, entrambi «questo non è uno
    sharded cluster». Cioè lo schermo negava un cluster che era acceso.

    **L'etichetta è un parametro** perché `spartizione` usa questa stessa funzione **due**
    volte, sulle due collezioni che accosta, e due righe intitolate «shard» una sopra
    l'altra non direbbero quale sia quale. I tre casi restano scritti in un posto solo: è
    la logica, non il titolo, che non va duplicata.
    """
    if not distribuzione.in_un_cluster:
        # Dichiarare il vuoto invece di omettere la voce: su un replica set la domanda
        # «e gli shard?» è legittima, e una riga assente si legge come una dimenticanza.
        return [_voce(etichetta, "nessuno: questo non è uno sharded cluster")]
    if not distribuzione.distribuita:
        return [
            _voce(
                etichetta,
                f"{distribuzione.collezione} non è distribuita",
                f"{distribuzione.documenti} documenti su {distribuzione.primario}",
            )
        ]
    if not distribuzione.conti:
        # Distribuita e senza un solo shard che risponde: non è «zero documenti», è una
        # risposta che manca, e inventare una riga di zeri la farebbe sembrare un dato.
        return [_voce(etichetta, f"{distribuzione.collezione} è distribuita", IGNOTO)]
    prima, *altri = distribuzione.conti
    return [_voce(etichetta, _riga_shard(distribuzione, prima))] + [
        _sotto(_riga_shard(distribuzione, conto)) for conto in altri
    ]


def _riga_shard(distribuzione: Distribuzione, conto: ContoShard) -> str:
    """Documenti, quota e chunk. La quota perché due conteggi grezzi si confrontano a
    mente, e dalla decima fila nessuno lo fa."""
    quota = distribuzione.quota(conto.shard)
    percentuale = IGNOTO if quota is None else f"{quota:.0f}%"
    return (
        f"{conto.shard:<18}{conto.documenti} documenti ({percentuale})"
        f"{SEPARATORE}{conto.chunk} chunk"
    )


def _piano(piano: Piano) -> list[str]:
    """Il filtro, lo stadio verbatim, e quanti shard ha coinvolto.

    Lo stadio non si traduce: `SINGLE_SHARD` e `SHARD_MERGE` sono le parole che chi guarda
    ritroverà nel proprio `explain()`, e sostituirle con «mirata» e «a tutti» renderebbe
    la schermata più chiara e la shell irriconoscibile. Le due etichette italiane stanno a
    sinistra, dove sono un titolo; la parola del server sta a destra, dove è un dato.
    """
    quanti = len(piano.shard)
    return [
        _filtro(piano.filtro),
        piano.stadio,
        f"{quanti} shard" if quanti else "nessuno shard: qui non c'è un router",
    ]


def _filtro(filtro: Documento) -> str:
    """Il filtro come lo si digiterebbe, non come lo stampa Python.

    Virgolette doppie: chi guarda riscriverà quella riga in `mongosh`, e il `repr` di un
    dict — apostrofi compresi — non è ciò che mongosh accetta. Il ripiego su `str` c'è per
    i filtri che JSON non sa scrivere, un `ObjectId` per esempio: meglio una riga con gli
    apostrofi che una schermata che solleva mentre la sala guarda.
    """
    try:
        return json.dumps(filtro, ensure_ascii=False, separators=(", ", ": "))
    except TypeError:
        return str(filtro)


def _arrivi(arrivi: Sequence[tuple[str, int]]) -> list[str]:
    """Dove è finito il carico, shard per shard, con la sua quota.

    Nessuna riga se gli arrivi non ci sono: là non c'è una collezione distribuita di cui
    dire dove sia finito qualcosa, e le due righe sopra lo hanno già detto.
    """
    totale = sum(quanti for _, quanti in arrivi)
    if not arrivi or totale <= 0:
        return []
    return [
        _voce(
            "arrivati",
            *(
                f"{shard} {quanti} ({100.0 * quanti / totale:.0f}%)"
                for shard, quanti in arrivi
            ),
        )
    ]


def _punti(sbilancio: float | None) -> str:
    """Punti percentuali, e il trattino dove la distanza non esiste. Vedi `sbilancio`.

    Il singolare è scritto a mano perché «1 punti» è la svista che si nota dalla prima
    fila, e questa schermata sta su un proiettore per un minuto intero.
    """
    if sbilancio is None:
        return IGNOTO
    quanti = round(sbilancio)
    return f"{quanti} punto" if quanti == 1 else f"{quanti} punti"


def _chunk_in_piu(quanti: int | None) -> str:
    """Zero si scrive. È la lezione del Passo 1, e una riga assente sembrerebbe un buco."""
    return IGNOTO if quanti is None else f"{quanti} in più"


def _carico(scena: EsitoSharding) -> list[str]:
    """Una riga sola se le due corse combaciano, tre se no. Vedi `EsitoSharding`."""
    if scena.confrontabile:
        return [f"{scena.carico_intera.scritture} scritture su ognuna"]
    return [
        f"{scena.carico_intera.scritture} senza chiave",
        f"{scena.carico_sparsa.scritture} con chiave",
        "non è lo stesso carico",
    ]


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


def _avvicendamento(interruzione: Interruzione | None) -> list[str]:
    """Chi ha preso il posto di chi, e solo se qualcuno l'ha preso davvero.

    `e_un_failover` è falso quando lo stesso nodo torna primario: c'è stata
    un'interruzione, non un'elezione, e scrivere «da mongo-rs-1 a mongo-rs-1» sarebbe una
    riga che si legge come un refuso proprio nel momento in cui va letta con attenzione.
    """
    if interruzione is None or not interruzione.e_un_failover:
        return []
    return [_sotto(f"da {interruzione.primario_prima} a {interruzione.primario_dopo}")]


def _fase(etichetta: str, corsa: Riepilogo) -> list[str]:
    """Il carico di una fase in una riga sola: qui interessa il confronto fra le tre.

    Non `riassunto`, che di righe ne fa fino a quattro: tre riassunti interi sarebbero
    dodici righe fra i due numeri e le fasi, e la domanda a cui questa parte risponde —
    *quanto è calato il carico durante l'elezione* — si legge meglio da tre righe
    allineate che da dodici complete.
    """
    if not corsa.scritture:
        return []
    voci = [f"{corsa.scritture} scritture", f"{corsa.riuscite} confermate"]
    if corsa.fallite:
        voci.append(f"{corsa.fallite} fallite")
    if corsa.latenze is not None:
        voci.append(f"p95 {corsa.latenze.p95_ms:.1f} ms")
    return [_voce(etichetta, *voci)]

def _ultimo_avanzamento(avanzamenti: Sequence[Progress]) -> list[str]:
    """L'ultima riga che lo strumento ha detto di sé, se ne ha detta almeno una.

    Solo l'ultima: le altre sono già scorse a schermo come eventi mentre l'operazione
    andava, e ristamparle tutte nel consuntivo raddoppierebbe una cronaca invece di
    riassumerla.
    """
    if not avanzamenti:
        return []
    messaggio = avanzamenti[-1].messaggio.strip()
    return [_sotto(messaggio)] if messaggio else []


def _al_secondo(ritmo: Ritmo) -> str:
    """Un throughput in documenti al secondo, o il segno del mancante."""
    quanti = ritmo.documenti_al_secondo
    return IGNOTO if quanti is None else f"{quanti:.0f}/s"


def _percentuale(quanta: float | None) -> str:
    """Un calo in punti percentuali. `IGNOTO` quando non c'era niente da confrontare.

    Non `0%`: uno zero in quella casella si leggerebbe come «il dump non ha avuto nessun
    impatto», che è precisamente la conclusione che il rapporto non deve suggerire quando
    il dato manca.
    """
    return IGNOTO if quanta is None else f"{quanta:.1f}%"


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


def _millisecondi(quanti: float | None) -> str:
    """Una durata in millisecondi, o il segno del mancante.

    `IGNOTO` e non `0 ms`, ed è la stessa scelta di `Interruzione.durata_ms` portata fino
    allo schermo: uno zero in quella casella passerebbe per una misura, e sarebbe la
    misura di un failover perfetto — cioè esattamente ciò che si vede quando il guasto
    non è avvenuto affatto.
    """
    return IGNOTO if quanti is None else f"{quanti:.0f} ms"


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
