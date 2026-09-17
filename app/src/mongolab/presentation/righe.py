"""La riga: la resa che le tre implementazioni hanno in comune.

Un evento diventa **una** riga di testo, e la stessa riga finisce sullo schermo di Rich,
nel file di `PlainSink` e dentro una registrazione asciinema. Non è economia di codice: è
la condizione perché le registrazioni di riserva mostrino ciò che il pubblico avrebbe
visto dal vivo. Due formattazioni diverse per la stessa scena vorrebbero dire che il
piano B racconta un'altra storia.

**Il budget di sala non è deciso qui, è ereditato.** `tools/registra-terminale.py` fissa
100x30 per le registrazioni, con la ragione scritta accanto: «una registrazione di
riserva va proiettata, e 100x30 sta su uno schermo da sala senza che il testo vada a capo
dove non deve». Il Task 18 girerà le registrazioni con `--sink plain` dentro quello
strumento, quindi una schermata più alta di trenta righe si vedrebbe tagliata proprio nel
piano B. Il testo grande in sala lo fa il terminale, non l'applicazione; ciò che
l'applicazione può decidere è **quanto poco spazio occupare**, ed è questo.
"""

from datetime import datetime

from mongolab.domain.eventi import (
    BackupProgressed,
    Evento,
    FaseIniziata,
    LatencySampled,
    PrimaryWaitAbandoned,
    RetryAttempted,
    ServerStateChanged,
    TopologyChanged,
    WriteFailed,
    WriteSucceeded,
)
from mongolab.domain.modelli import DescrizioneTopologia

__all__ = [
    "ALTEZZA_INTESTAZIONE",
    "COLONNE_SALA",
    "ETICHETTA_IGNOTA",
    "LARGHEZZA_ETICHETTA",
    "RIGHE_CRONACA",
    "RIGHE_SALA",
    "SERVER_MOSTRATI",
    "TRONCAMENTO",
    "riga",
    "server_da_mostrare",
    "tronca",
]

COLONNE_SALA = 100
RIGHE_SALA = 30
"""Le dimensioni della registrazione di riserva, e quindi della schermata.

Non si scelgono due volte: sono le stesse costanti di `tools/registra-terminale.py`, dove
sono state decise da `feature/02` per la proiezione in sala. Ripeterle qui invece di
importarle è deliberato — `app/` non dipende da `tools/`, e sono numeri di sala, non di
codice — ma il valore è lo stesso, e una prova lo controlla.
"""

SERVER_MOSTRATI = 3
"""Quanti server stanno nell'intestazione.

Tre perché tre sono quanti ne vede un client, misurati sui tre stack accesi
([M-029](../../../../app/docs/Sources.md#m-029)): il replica set scoperto ne mostra tre,
un client di un `mongos` ne mostra **uno** — il `mongos`. La topologia di uno sharded
cluster, dal punto di vista del driver, non contiene i membri degli shard: quelli si
contano con `$shardedDataDistribution`, che produce `ContoShard` e non
`DescrizioneServer`.

Il numero è misurato perché la prima stesura ne riservava otto, con una giustificazione
plausibile e falsa — «due shard da due membri, tre config server, un mongos» — che
contava i **container** dello stack 03 invece di ciò che il driver vede. Cinque righe di
intestazione che nessuno avrebbe mai riempito, sottratte alla cronaca per sempre.
"""

ALTEZZA_INTESTAZIONE = 4 + SERVER_MOSTRATI
"""Il bordo alto, i server, il separatore, la riga dei conteggi, il bordo basso."""

RIGHE_CRONACA = 21
"""Le righe di cronaca visibili. Sette di intestazione più ventuno fanno ventotto: due
righe restano al prompt e al cursore, che in una registrazione si vedono.
"""

LARGHEZZA_ETICHETTA = 9
"""Quanto è larga la colonna centrale. Nove è `SCRITTURA`, ed è la più lunga."""

TRONCAMENTO = "…"
ETICHETTA_IGNOTA = "IGNOTO"
"""Il ripiego per un evento che nessuno ha insegnato a scriversi.

Esiste perché in sala lo spettacolo non si ferma: un decimo evento aggiunto un giorno e
dimenticato qui produce una riga brutta, non un'eccezione dentro il ciclo di disegno.
Che poi è esattamente il motivo per cui `test_presentazione.py` pretende che **nessuno**
dei nove ci finisca: il ripiego protegge la sala, la prova protegge il codice.
"""


def riga(evento: Evento, *, larghezza: int | None = COLONNE_SALA) -> str:
    """L'evento come una riga sola, tagliata alla larghezza di sala.

    `larghezza=None` restituisce il testo intero, ed è ciò che serve a chi reindirizza su
    file per analizzare dopo. Il valore predefinito taglia, e taglia per una ragione
    misurata sul campo: un `ServerSelectionTimeoutError` di pymongo porta con sé la
    descrizione dell'intera topologia, e durante un failover ne arrivano a centinaia al
    secondo. Non tagliare significa seppellire la cronaca dell'elezione sotto i messaggi
    degli errori che l'elezione provoca.
    """
    etichetta, dettaglio = _etichetta_e_dettaglio(evento)
    return tronca(
        f"{_istante(evento.istante)}  "
        f"{etichetta:<{LARGHEZZA_ETICHETTA}}  "
        f"{_appiattisci(dettaglio)}",
        larghezza,
    )


def tronca(testo: str, larghezza: int | None = COLONNE_SALA) -> str:
    """Il testo tagliato alla larghezza di sala, con i puntini che dichiarano il taglio.

    Estratto da `riga` al Task 11, quando il secondo consumatore è arrivato: il rapporto
    di `stats` sta sullo stesso schermo e ha lo stesso budget, e una seconda copia di
    queste quattro righe sarebbe stata una copia destinata a divergere — con il risultato
    che due parti della stessa schermata avrebbero tagliato a due larghezze diverse.
    """
    if larghezza is not None and larghezza <= 0:
        raise ValueError(f"la larghezza è un numero di colonne, ricevuto {larghezza}")
    if larghezza is None or len(testo) <= larghezza:
        return testo
    return testo[: larghezza - len(TRONCAMENTO)] + TRONCAMENTO


def _istante(momento: datetime) -> str:
    """L'ora al millesimo, senza la data.

    Al millesimo perché è la promessa del §6.3: la cronaca dell'elezione vale se si legge
    **quanto** è durata. Senza la data perché una scena dura minuti e la data occuperebbe
    dieci colonne per ripetere un'informazione che il nome del file già porta.
    """
    return momento.strftime("%H:%M:%S.") + f"{momento.microsecond // 1000:03d}"


def _appiattisci(testo: str) -> str:
    """Tutto su una riga, con gli spazi normalizzati.

    Un messaggio del driver può andare a capo, e chi legge il file di `PlainSink` conta
    sugli a capo per separare i fatti: una riga per evento. Un `\\n` dentro un `motivo`
    romperebbe quel conteggio senza rompere nient'altro, che è il modo peggiore di
    rompersi.
    """
    return " ".join(testo.split())


def _etichetta_e_dettaglio(evento: Evento) -> tuple[str, str]:
    """L'etichetta in colonna e ciò che la segue, per ciascuna delle dieci specie."""
    match evento:
        case WriteSucceeded():
            return (
                "SCRITTURA",
                f"{evento.documenti} documenti confermati in {evento.durata_ms:.1f} ms",
            )
        case WriteFailed():
            return (
                "ERRORE",
                f"{evento.tipo_errore}: {evento.motivo} ({evento.documenti} documenti)",
            )
        case RetryAttempted():
            return (
                "RITENTO",
                f"tentativo {evento.tentativo} dopo {evento.attesa_ms:.0f} ms:"
                f" {evento.motivo}",
            )
        case LatencySampled():
            return "LATENZA", f"{evento.operazione} {evento.durata_ms:.1f} ms"
        case TopologyChanged():
            return (
                "TOPOLOGIA",
                f"{evento.precedente.tipo.value} → {evento.successiva.tipo.value}",
            )
        case ServerStateChanged():
            return (
                "SERVER",
                f"{evento.indirizzo} {evento.precedente.value} → {evento.successivo.value}",
            )
        case BackupProgressed():
            return "BACKUP", _avanzamento(evento)
        case FaseIniziata():
            return "FASE", evento.descrizione
        case PrimaryWaitAbandoned():
            ultimo = evento.ultimo_primario or "nessuno visto"
            return (
                "RESA",
                f"{evento.atteso_ms:.0f} ms senza primario"
                f" (pazienza {evento.pazienza_ms:.0f} ms), ultimo {ultimo}",
            )
        case _:
            return ETICHETTA_IGNOTA, type(evento).__name__


def _avanzamento(evento: BackupProgressed) -> str:
    """L'avanzamento, e il silenzio quando il totale non si conosce.

    `Progress.totali` è opzionale perché `mongodump` annuncia il totale di una collezione
    e non quello del dump intero. Una percentuale mostrata comunque sarebbe un numero
    inventato, e in sala un numero inventato è peggio di nessun numero.
    """
    passo = evento.avanzamento
    percentuale = passo.percentuale
    if percentuale is None:
        testo = f"{passo.fase} {passo.completati}"
    else:
        testo = f"{passo.fase} {passo.completati}/{passo.totali} ({percentuale:.1f}%)"
    return f"{testo} — {passo.messaggio}" if passo.messaggio else testo


def server_da_mostrare(
    topologia: DescrizioneTopologia,
) -> tuple[tuple[str, str, str], ...]:
    """Le righe della tabella dei server: indirizzo, ruolo, ritardo — al più `SERVER_MOSTRATI`.

    Sta qui e non dentro `RichTui` per la ragione di sempre: è una decisione, e le
    decisioni si provano. Quella che prende è cosa fare quando i server sono più delle
    righe disponibili, e la risposta è **dirlo**. Il pannello ha altezza fissa apposta —
    se crescesse, la cronaca si accorcerebbe proprio quando il cluster si scompone — e
    quindi qualcosa va tagliato; ma chi guarda conta i server per capire se il cluster è
    integro, e un elenco troncato in silenzio si legge come un cluster più piccolo di
    quello che è.
    """
    server = topologia.server
    if len(server) <= SERVER_MOSTRATI:
        mostrati, nascosti = server, 0
    else:
        mostrati = server[: SERVER_MOSTRATI - 1]
        nascosti = len(server) - len(mostrati)

    righe = tuple(
        (
            uno.indirizzo,
            uno.ruolo.value,
            "—" if uno.ritardo_ms is None else f"{uno.ritardo_ms:.1f} ms",
        )
        for uno in mostrati
    )
    if nascosti:
        righe += ((f"… e altri {nascosti}", "", ""),)
    return righe
