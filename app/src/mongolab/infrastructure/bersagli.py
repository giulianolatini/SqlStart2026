"""Dove stanno i tre stack, e come ci si arriva. La mappa `--target` → URI, in un posto solo.

Il §6.4 scrive `mongolab stats --target rs`: una parola sulla riga di comando, e dietro
quella parola una porta, una credenziale e una decisione su `directConnection`. Questo
modulo è l'unico posto del repository in cui quei tre fatti stanno scritti.

**Perché di produzione e non nelle prove.** Fino al Task 10 gli stessi numeri vivevano in
`tests/integration/ambiente.py`, che li aveva perché era l'unico codice che si collegasse
a qualcosa. Adesso c'è anche l'applicazione, e la scelta era fra copiarli — due copie che
divergono al primo cambio, e la seconda se ne accorge con un timeout di venti secondi che
parla d'altro — o spostarli qui e far derivare le prove. Il codice di produzione non può
importare quello di prova; il contrario sì. Quindi qui.

**La credenziale non entra nell'URI.** `Bersaglio.uri` è `mongodb://host:porta/` e basta.
Utente e password vanno a `MongoClient` come argomenti, dove pymongo non li lascia uscire
né in `repr(client)`, né in `ServerSelectionTimeoutError`, né in `OperationFailure`
([M-018](../../../docs/Sources.md#m-018)). Nell'URI ci finirebbero in tutti e tre.

**Lo stesso stack ha due indirizzi, e la differenza non è cosmetica.** Dall'host si passa
per una porta pubblicata — `localhost:27021` — e la scoperta dei membri va **spenta**: con
`replicaSet=rs0` da fuori della rete Compose pymongo riceve dalla configurazione del set i
nomi `mongo-rs-1:27017` e compagni, che l'host non risolve, e un replica set sanissimo si
legge `ReplicaSetNoPrimary` ([M-019](../../../docs/Sources.md#m-019)). Di qui
`diretto=True` sul `rs` dall'host, al prezzo che la *forma* della topologia si legge
`SINGOLA` mentre il *ruolo* è `RSPrimary`.

Dalla rete Compose la stessa scoperta funziona, perché lì quei nomi sono nomi veri: è il
punto di vista che il Task 12 aggiunge, ed è quello che il talk mostra
([ADR-0012](../../../docs/Decision.md#adr-0012)). Da lì il `rs` si dichiara con tre semi e
`directConnection=false`, e il solo stack 01 resta diretto — perché un mongod solo non
conosce nessun altro, e non c'è niente da scoprire.

Il punto di vista non si indovina: lo dice `MONGOLAB_PUNTO_DI_VISTA`, che il servizio
Compose dell'applicazione scrive `rete` e che sull'host nessuno scrive. Un valore che non
si capisce ferma l'applicazione invece di ripiegare, perché ripiegare vorrebbe dire venti
secondi di selezione fallita che parlano d'altro.

**Anche la credenziale cambia strada.** Dall'host si legge dal `.env` dello stack; dalla
rete quel file non esiste — nel container c'è `/app` e basta — e i valori arrivano
dall'ambiente, con gli stessi nomi (`UTENTE_AMMINISTRATORE`, `PASSWORD_AMMINISTRATORE`).
Una chiave sola, due trasporti.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Final, Mapping

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

__all__ = [
    "BERSAGLI",
    "COLLEZIONE",
    "DATABASE",
    "PREFISSO_CARICO",
    "VARIABILE_PUNTO_DI_VISTA",
    "Bersaglio",
    "BersaglioSconosciuto",
    "Credenziali",
    "PuntoDiVista",
    "PuntoDiVistaSconosciuto",
    "SenzaPrimario",
    "Vista",
    "attendi_il_primario",
    "bersaglio_di",
    "collezione_di_carico",
    "connetti",
    "credenziali_di",
    "opzioni_di_misura",
    "punto_di_vista",
    "radice",
]

PORTA_INTERNA: Final = 27017
"""La porta su cui ascolta ogni mongod e ogni mongos **dentro** la rete Compose.

Sempre 27017, su tutti e tre gli stack: le porte diverse che si leggono nei `compose.yaml`
— 27021, 27117 — sono mappature verso l'host, e dentro la rete non esistono. È il motivo
per cui i tre stack, visti da dentro, si somigliano molto più di quanto sembri da fuori.
"""

DATABASE: Final = "lab"
COLLEZIONE: Final = "ordini"
"""`lab.ordini` è ciò che i tre `init/*-dati-demo.js` seminano: la stessa collezione su
tutti e tre gli stack, perché il confronto fra architetture del Task 16 abbia senso."""

PREFISSO_CARICO: Final = "carico-"
"""Da cosa comincia il nome della collezione in cui `workload` scrive.

Il carico **non** scrive in `ordini`, e non è una preferenza estetica: `DataGenerator`
numera i documenti da zero e il seed occupa già gli `_id` da 0 a 49 999, quindi ogni
scrittura tornerebbe indietro con un `E11000 duplicate key`. Misurato eseguendo, non
dedotto — la prima corsa contro lo stack 01 acceso ha risposto «38 scritture, 0
confermate», tutte per quel motivo.

Che dovesse andare altrove era già dichiarato: `generatore.py` scriveva che «le due
popolazioni non si incontrano mai nella stessa collezione, perché il carico scrive nella
propria», e `tools/reset-demo.sh` tiene `const superstiti = ["ordini"]` — cioè in `lab`
ogni altra collezione è residuo, e viene tolta. Il posto c'era; a sbagliare era il
cablaggio.

Dal Task 15 quella frase è più stretta, e questa costante non ne è toccata: le scene di
`demo` scrivono anche in `ordini`, ma con `documento_progressivo`, che l'`_id` non lo tocca
([ADR-0106](../../../../docs/Decision.md#adr-0106)). A numerare gli `_id` resta solo
`workload`, ed è solo `workload` ad avere bisogno di una collezione tutta sua.
"""


def collezione_di_carico(istante: datetime) -> str:
    """Il nome della collezione per **questa** corsa: `carico-20260918-103000`.

    Il nome cambia a ogni corsa perché altrimenti funzionerebbe una volta sola. Gli `_id`
    ripartono da zero a ogni esecuzione — è ciò che rende il dataset una funzione pura di
    `(seme, indice)`, vedi `generatore.py` — quindi una seconda corsa sulla stessa
    collezione ritroverebbe i propri documenti e fallirebbe come falliva contro `ordini`.
    In sala il carico si lancia più di una volta.

    L'istante si legge **così com'è**, senza convertirlo a UTC: chi cerca la propria
    collezione fra tre avanzi guarda l'orologio della sala, e `SystemClock` gliene dà uno
    che parla del fuso locale. Gli avanzi non si accumulano oltre la giornata — è
    `reset-demo` a spazzarli, tutti insieme.
    """
    return f"{PREFISSO_CARICO}{istante:%Y%m%d-%H%M%S}"


ATTESA_SELEZIONE_MS: Final = 20_000
"""Quanto pymongo aspetta un server prima di arrendersi.

Venti secondi e non i trenta predefiniti: durante un failover la selezione **deve**
scadere prima che la pazienza di `TopologyWatcher` finisca, altrimenti la cronaca mostra
un silenzio invece di mostrare i tentativi, ed è proprio quella la scena.
"""


class BersaglioSconosciuto(ValueError):
    """Il nome dopo `--target` non è uno dei tre.

    Sottoclasse di `ValueError` perché chi legge gli argomenti cattura già quello: la CLI
    non deve conoscere un tipo del progetto per tradurre l'errore in un codice d'uscita.
    """


class PuntoDiVistaSconosciuto(ValueError):
    """`MONGOLAB_PUNTO_DI_VISTA` dice qualcosa che non è né `host` né `rete`."""


class PuntoDiVista(Enum):
    """Da dove si guarda lo stack: da fuori la rete Compose, o da dentro.

    Due valori e non tre. «Da un altro container sulla stessa rete» e «dal container
    dell'applicazione» sono lo stesso punto di vista — stessi nomi, stessa porta interna,
    stessa scoperta — e dargli due nomi farebbe credere che ci sia una differenza.
    """

    HOST = "host"
    RETE = "rete"


VARIABILE_PUNTO_DI_VISTA: Final = "MONGOLAB_PUNTO_DI_VISTA"
"""La variabile d'ambiente che sceglie il punto di vista.

Una variabile e non un'opzione della riga di comando: chi lancia `mongolab stats --target
rs` scrive la stessa riga in tutti e due i casi, e ciò che cambia è **dove** la scrive. Il
servizio Compose la dichiara una volta; sull'host non la dichiara nessuno.
"""


def punto_di_vista(variabili: Mapping[str, str] | None = None) -> PuntoDiVista:
    """Legge il punto di vista dall'ambiente. Predefinito: l'host.

    L'host è il predefinito perché è da lì che si sviluppa: `uv run mongolab stats` sul
    portatile deve funzionare senza dichiarare niente.

    La stringa vuota vale come assente, e non è indulgenza: Compose, davanti a
    `MONGOLAB_PUNTO_DI_VISTA: ${QUALCOSA}` con `QUALCOSA` non definita, non toglie la
    variabile — la mette a `""`. Un valore *sbagliato*, invece, ferma tutto: da dentro un
    container `localhost:27021` non è un errore immediato, è un timeout di venti secondi
    che parla di una porta chiusa invece che di un refuso.
    """
    ambiente = variabili if variabili is not None else os.environ
    detto = ambiente.get(VARIABILE_PUNTO_DI_VISTA, "").strip().lower()
    if not detto:
        return PuntoDiVista.HOST
    try:
        return PuntoDiVista(detto)
    except ValueError:
        validi = ", ".join(punto.value for punto in PuntoDiVista)
        raise PuntoDiVistaSconosciuto(
            f"{VARIABILE_PUNTO_DI_VISTA}=«{detto}» non è un punto di vista di questo "
            f"repository. I valori sono: {validi}."
        ) from None


@dataclass(frozen=True, slots=True)
class Vista:
    """Come si raggiunge uno stack da un punto di vista: i semi, il diretto, il set.

    Tre fatti in un tipo solo perché dipendono tutti dallo stesso dato — da dove si
    guarda — e tenerli separati vorrebbe dire poterli cambiare uno per volta, cioè poterli
    mettere in disaccordo. `directConnection=True` con più di un seme, per dire, non è una
    configurazione discutibile: è un `ConfigurationError` alla costruzione del client.
    """

    semi: tuple[tuple[str, int], ...]
    """Da dove il client parte. Più di uno solo dove la scoperta è accesa."""

    diretto: bool
    """`directConnection`: se `True`, il client parla con quel server e non scopre nulla."""

    replica: str | None = None
    """`replicaSet`, dove ha senso dichiararlo.

    È una dichiarazione di aspettativa: se il set che risponde si chiama diversamente,
    pymongo non lo usa. Verso un mongos sarebbe un errore di categoria — il mongos non è
    membro di nessun set — e infatti lì resta `None`.
    """

    @property
    def uri(self) -> str:
        """`mongodb://host:porta[,host:porta...]/`. Senza credenziali, e non è una svista."""
        elenco = ",".join(f"{host}:{porta}" for host, porta in self.semi)
        return f"mongodb://{elenco}/"


@dataclass(frozen=True)
class Credenziali:
    """Utente e password, con la password fuori dal `repr`.

    `field(repr=False)` non è offuscamento e non protegge da chi legge il codice: protegge
    dalla **stampa accidentale**, che è il modo in cui i segreti escono davvero. Un oggetto
    del genere può comparire in un `assert` fallito, in un traceback, in un `print` di
    disperazione — e in nessuno di quei casi mostra il segreto.
    """

    utente: str
    password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class Bersaglio:
    """Uno stack, come lo raggiunge chi scrive `--target <nome>`."""

    nome: str
    """La parola sulla riga di comando: `standalone`, `rs`, `sharded`."""

    stack: str
    """La directory sotto `docker/`, che è anche il nome che si legge nei log."""

    da_host: Vista
    """Come lo si raggiunge da fuori la rete Compose: porta pubblicata, scoperta spenta."""

    da_rete: Vista
    """Come lo si raggiunge da dentro: nomi di servizio, porta interna, scoperta accesa."""

    ambiente: str | None = None
    """Il `.env` da cui leggere la credenziale, relativo alla radice. `None`: nessuna
    autenticazione, che è il caso del solo stack 01.

    Il percorso serve solo dall'host. Dalla rete la stessa credenziale arriva
    dall'ambiente, e questo campo resta il modo di dire «questo stack autentica».
    """

    def vista(self, punto: PuntoDiVista) -> Vista:
        """La vista giusta per quel punto di vista."""
        return self.da_host if punto is PuntoDiVista.HOST else self.da_rete

    @property
    def porta(self) -> int:
        """La porta che il `compose.yaml` pubblica sull'host, nella sua forma predefinita.

        Predefinita e non assoluta: i file Compose la scrivono `${PORTA_...:-27021}`,
        quindi un operatore può spostarla con una variabile d'ambiente e questa mappa non
        lo saprebbe. Non è un problema oggi — nessuno lo fa, e `tools/preflight.sh`
        riserva gli intervalli predefiniti — ed è una riga aperta dichiarata. La guardia
        contro la deriva è una prova che rilegge il `compose.yaml` e confronta.

        Deriva dalla vista dell'host invece di essere un campo, perché due posti in cui
        scrivere lo stesso numero sono due numeri.
        """
        return self.da_host.semi[0][1]


BERSAGLI: Final[Mapping[str, Bersaglio]] = {
    "standalone": Bersaglio(
        nome="standalone",
        stack="01-standalone",
        da_host=Vista(semi=(("localhost", 27017),), diretto=True),
        # Diretto anche da dentro, ed è il Passo 3 del Task 12: qui non c'è niente da
        # scoprire. Un mongod solo non conosce nessun altro, quindi `directConnection`
        # non toglie una scena — dice la verità sulla topologia.
        da_rete=Vista(semi=(("mongo-standalone", PORTA_INTERNA),), diretto=True),
    ),
    "rs": Bersaglio(
        nome="rs",
        stack="02-replicaset",
        da_host=Vista(semi=(("localhost", 27021),), diretto=True),
        # Tre semi, scoperta accesa, nome del set dichiarato: è la configurazione che
        # un'applicazione vera scrive, ed è quella che il talk mostra. Tre e non uno
        # perché con un seme solo l'avvio dipende da quale membro è acceso, e in sala il
        # membro giù è una scena prevista.
        da_rete=Vista(
            semi=(
                ("mongo-rs-1", PORTA_INTERNA),
                ("mongo-rs-2", PORTA_INTERNA),
                ("mongo-rs-3", PORTA_INTERNA),
            ),
            diretto=False,
            replica="rs0",
        ),
        ambiente="docker/02-replicaset/.env",
    ),
    "sharded": Bersaglio(
        nome="sharded",
        stack="03-sharded",
        da_host=Vista(semi=(("localhost", 27117),), diretto=False),
        # Un seme solo, e non è una dimenticanza: `mongos2` esiste nel solo profilo
        # `completo`, e dichiararlo sempre vorrebbe dire dichiarare un nome che di norma
        # non risolve. Il secondo router entra in scena quando c'è, non prima.
        da_rete=Vista(semi=(("mongos", PORTA_INTERNA),), diretto=False),
        ambiente="docker/03-sharded/.env",
    ),
}
"""I tre nomi che `--target` accetta, con i due indirizzi di ciascuno.

`rs` e `sharded` vengono dal §6.4 alla lettera. Per lo standalone il design non dà un
nome, e `standalone` è quello che il repository usa già dappertutto — nella directory,
nel target del Makefile, nel titolo della pagina di architettura. Un quarto sinonimo
sarebbe stato una cosa in più da ricordare la sera del talk.
"""


def bersaglio_di(nome: str) -> Bersaglio:
    """Il bersaglio di quel nome, o un errore che elenca quelli che esistono.

    L'elenco nel messaggio non è cortesia: chi sbaglia `--target` sta quasi sempre
    scrivendo il nome della *directory* (`02-replicaset`) o quello del *set* (`rs0`), e
    senza i tre nomi veri sotto gli occhi va a cercarli nel sorgente.
    """
    try:
        return BERSAGLI[nome]
    except KeyError:
        disponibili = ", ".join(sorted(BERSAGLI))
        raise BersaglioSconosciuto(
            f"«{nome}» non è uno stack di questo repository. I bersagli sono: {disponibili}."
        ) from None


def radice() -> Path:
    """La radice del repository, cercando all'insù il `Makefile`.

    Non una costante calcolata da `__file__` con quattro `.parent`: questo albero vive
    anche dentro `.claude/worktrees/`, e un conteggio di livelli sbagliato darebbe una
    directory che esiste, in cui non c'è niente di ciò che si cerca.
    """
    for cartella in [Path(__file__).resolve(), *Path(__file__).resolve().parents]:
        if (cartella / "Makefile").is_file():
            return cartella
    raise RuntimeError(
        f"nessun Makefile risalendo da {__file__}: `mongolab` non sa dove sta il "
        "repository, e senza repository non sa dove sono i suoi stack."
    )


CHIAVE_UTENTE: Final = "UTENTE_AMMINISTRATORE"
CHIAVE_PASSWORD: Final = "PASSWORD_AMMINISTRATORE"
"""I due nomi con cui la credenziale viaggia, tanto nel `.env` quanto nell'ambiente.

Gli stessi nomi da tutti e due i lati apposta: il `compose.yaml` dell'applicazione li
inoltra così come li trova, senza tradurli, e chi legge il servizio riconosce le stesse
parole che sta guardando nel `.env` accanto.
"""


def credenziali_di(
    bersaglio: Bersaglio,
    base: Path | None = None,
    *,
    punto: PuntoDiVista | None = None,
    variabili: Mapping[str, str] | None = None,
) -> Credenziali | None:
    """Utente e password dello stack, o `None` se quello stack non autentica.

    Da dove arrivano dipende dal punto di vista. **Dall'host** si leggono dal `.env` dello
    stack, che non è nel repository ([ADR-0014](../../../docs/Decision.md#adr-0014)) e la
    cui casa è il checkout principale
    ([ADR-0056](../../../docs/Decision.md#adr-0056)); da un worktree ci si arriva con un
    collegamento, mai con una copia ([ADR-0083](../../../docs/Decision.md#adr-0083)). Qui
    non si sa niente di tutto questo: si legge un percorso, e se manca si dice quale
    comando lo rimedia.

    **Dalla rete** quel file non esiste: nel container c'è `/app`, e cercare comunque il
    `.env` farebbe risalire `radice()` fino a `/` per poi lamentare un repository
    mancante, che è la cosa sbagliata da dire a chi ha dimenticato una variabile. I valori
    arrivano dall'ambiente, con gli stessi due nomi, perché è il `compose.yaml` a
    passarli — leggendoli dallo stesso `.env`, dal lato in cui esiste.

    `base` e `variabili` esistono per le prove, che non possono dipendere da un file fuori
    dal repository né dall'ambiente di chi le esegue.
    """
    if bersaglio.ambiente is None:
        return None
    if (punto if punto is not None else punto_di_vista()) is PuntoDiVista.RETE:
        return _dall_ambiente(variabili if variabili is not None else os.environ)
    percorso = (base if base is not None else radice()) / bersaglio.ambiente
    if not percorso.is_file():
        raise RuntimeError(
            f"manca {bersaglio.ambiente}: copia il .env.example accanto e riempilo, "
            f"oppure — se sei in un worktree — collegalo al checkout principale (ADR-0083)."
        )
    valori: dict[str, str] = {}
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if riga and not riga.startswith("#") and "=" in riga:
            chiave, _, valore = riga.partition("=")
            valori[chiave.strip()] = valore.strip()
    password = valori.get(CHIAVE_PASSWORD)
    if not password:
        # Il messaggio nomina la chiave che manca e **non** stampa il file: un `.env` letto
        # male e riversato in un errore è il modo più stupido di perdere un segreto.
        raise RuntimeError(
            f"{bersaglio.ambiente} non definisce {CHIAVE_PASSWORD}. "
            "Il valore non viene stampato qui e non deve comparire in nessun log."
        )
    return Credenziali(utente=valori.get(CHIAVE_UTENTE, "admin"), password=password)


def _dall_ambiente(variabili: Mapping[str, str]) -> Credenziali:
    """La credenziale come la riceve un container: due variabili, nessun file."""
    password = variabili.get(CHIAVE_PASSWORD)
    if not password:
        # Come per il `.env`: si nomina la chiave che manca, non si riversa nell'errore
        # l'ambiente che è stato letto — che qui conterrebbe anche tutto il resto.
        raise RuntimeError(
            f"{CHIAVE_PASSWORD} non è definita nell'ambiente. Dentro la rete Compose la "
            "credenziale arriva di lì e non dal .env, che nel container non c'è: "
            "controlla il servizio `app` del compose.yaml. Il valore non viene stampato "
            "qui e non deve comparire in nessun log."
        )
    return Credenziali(utente=variabili.get(CHIAVE_UTENTE, "admin"), password=password)


class SenzaPrimario(RuntimeError):
    """Nessun primario si è fatto vedere entro l'attesa di selezione del client.

    Un'eccezione di questo strato e non un `ServerSelectionTimeoutError` che passa: chi la
    riceve è la riga di comando, e deve poterla trasformare in una frase senza importare
    pymongo — glielo vieta `test_pymongo_si_importa_solo_nell_infrastruttura`, ed è la
    stessa regola per cui `MongoClient(...)` compare in un punto solo del repository.
    """


def attendi_il_primario(cliente: MongoClient[dict[str, Any]]) -> None:
    """Un `ping`, per aspettare che ci sia un primario prima di chiedere chi è.

    **Guardare non è aspettare**, e la differenza è costata un difetto vero al Task 13.
    `Inspector.topology()` legge la descrizione che il driver ha già in mano: è una
    lettura pura, non fa scoperta e non blocca. Subito dopo `connetti` quella descrizione
    è ancora vuota, perché la scoperta di pymongo comincia in quel momento e prosegue su
    thread suoi. Contro un replica set sanissimo, `demo failover` usciva con «nessun
    primario in vista» qualche decina di millisecondi prima che il primario comparisse.

    Gli altri comandi non se ne accorgevano, e per caso: `stats` chiede `serverStatus`,
    che è un comando vero e quindi aspetta la selezione; `watch` guarda la topologia
    mentre cambia, che è precisamente il suo mestiere.

    Il `ping` va **sul primario** — è la preferenza di lettura predefinita dei comandi su
    `admin` — quindi torna quando la selezione è riuscita, cioè esattamente quando la
    domanda che segue ha una risposta. L'attesa massima non è un parametro di questa
    funzione: è il `serverSelectionTimeoutMS` del client, che `connetti` fissa a
    `ATTESA_SELEZIONE_MS`. Prenderla anche qui vorrebbe dire poter dichiarare un'attesa
    diversa da quella che si aspetta davvero.
    """
    try:
        cliente.admin.command("ping")
    except ServerSelectionTimeoutError as scaduta:
        raise SenzaPrimario(str(scaduta)) from scaduta


def opzioni_di_misura(
    *,
    journal: bool | None = None,
    retry_writes: bool | None = None,
    max_staleness_s: int | None = None,
    max_pool_size: int | None = None,
) -> dict[str, Any]:
    """Le opzioni del client che il Task 16 accende e spegne per misurare (ADR-0109).

    Quattro pagine di architettura avevano scritto per iscritto che certe misure «hanno
    senso solo sotto carico controllato, cioè con l'applicazione Python di `feature/04`».
    Questa è la mappa che le rende possibili: `j: true` contro lo standalone,
    `retryWrites=false` e `maxStalenessSeconds` sul replica set, `maxPoolSize` stretto
    sotto il numero degli scrittori. Va a `connetti(**extra)`, che dal Task 5 aveva già
    il gancio e ne aveva già scritto il perché.

    **Chi non chiede non riceve.** Un argomento lasciato a `None` non compare nella mappa,
    e il client resta byte per byte quello di prima. Non è avarizia: è la condizione
    perché il confronto fra le tre architetture misuri le architetture. Se qui comparisse
    un valore «tanto è uguale al predefinito», la riga di base non sarebbe più quella del
    §6.4, e i numeri di due giorni diversi smetterebbero di essere accostabili.

    **La staleness non viaggia mai da sola.** `maxStalenessSeconds` con la preferenza
    predefinita è un `ConfigurationError` alla costruzione del client — «Read preference
    primary cannot be combined with maxStalenessSeconds» — e ha ragione il driver: un
    limite alla vecchiaia di ciò che si legge non dice niente su un membro che per
    definizione è aggiornato. Chiedere la staleness **è** chiedere di leggere da un
    secondario, quindi le due opzioni escono insieme da qui invece di dover essere
    ricordate insieme da chi scrive il comando.

    La preferenza è `secondary` e non `secondaryPreferred` apposta: con il ripiego sul
    primario una selezione fallita per staleness diventerebbe una lettura riuscita, cioè
    la misura si nasconderebbe da sola.

    **I nomi sono quelli dell'URI**, non quelli di Python — `retryWrites`, non
    `retry_writes`. pymongo accetta le opzioni della stringa di connessione come argomenti
    con lo stesso nome, e tenerli così vuol dire che la riga stampata a schermo si può
    incollare in un URI e in una `MONGO_URI` senza tradurla.
    """
    opzioni: dict[str, Any] = {}
    if journal is not None:
        opzioni["journal"] = journal
    if retry_writes is not None:
        opzioni["retryWrites"] = retry_writes
    if max_staleness_s is not None:
        opzioni["readPreference"] = "secondary"
        opzioni["maxStalenessSeconds"] = max_staleness_s
    if max_pool_size is not None:
        opzioni["maxPoolSize"] = max_pool_size
    return opzioni


def connetti(
    bersaglio: Bersaglio,
    *,
    attesa_ms: int = ATTESA_SELEZIONE_MS,
    base: Path | None = None,
    punto: PuntoDiVista | None = None,
    variabili: Mapping[str, str] | None = None,
    **extra: Any,
) -> MongoClient[dict[str, Any]]:
    """Il `MongoClient` verso quello stack. È l'unico posto che lo costruisce.

    **Il punto di vista decide tre cose**: l'indirizzo, la scoperta e la provenienza della
    credenziale. Non si passa quasi mai: sull'host il predefinito è giusto, e dentro il
    container lo dice `MONGOLAB_PUNTO_DI_VISTA`. L'argomento esiste perché le prove
    possano chiedere l'uno e l'altro senza toccare l'ambiente del processo.

    **`tz_aware=True`.** L'impostazione predefinita di pymongo è `False`, e con quella un
    `datetime` scritto consapevole del fuso torna indietro **ingenuo**. Nessuno solleva: il
    confronto fra due ingenui passa, e sbaglia di quante ore vale il fuso di chi presenta.
    Il dataset di demo ha un campo `data`, quindi il caso non è ipotetico
    ([M-018](../../../docs/Sources.md#m-018)) — e `PymongoStore` rifiuta di costruirsi
    senza, il che rende questa riga difficile da perdere per sbaglio.

    `extra` esisteva per il Task 16, che doveva accendere e spegnere `retryWrites` e
    `maxPoolSize` sulla stessa mappa senza scriverne una seconda. Quella mappa adesso c'è
    e si chiama `opzioni_di_misura`: la costruisce lei, la stampa la riga di comando, e
    la riceve questa funzione senza sapere che cosa contenga. È rimasto `**extra` e non è
    diventato un parametro tipato perché gli altri usi non sono spariti — `connect=False`
    nelle prove unitarie, `event_listeners` per il ponte SDAM — e ognuno di quelli è un
    argomento di pymongo che questo strato ha il permesso di conoscere.
    """
    dove = punto if punto is not None else punto_di_vista(variabili)
    vista = bersaglio.vista(dove)
    credenziali = credenziali_di(bersaglio, base=base, punto=dove, variabili=variabili)
    parametri: dict[str, Any] = {
        "tz_aware": True,
        "serverSelectionTimeoutMS": attesa_ms,
        "directConnection": vista.diretto,
        **extra,
    }
    if vista.replica is not None:
        # Il nome del set come argomento e non nell'URI, per la stessa ragione per cui ci
        # sta la credenziale: l'URI si costruisce in un posto solo, e quel posto non deve
        # sapere che cosa ci va dentro oltre agli indirizzi.
        parametri["replicaSet"] = vista.replica
    if credenziali is not None:
        parametri["username"] = credenziali.utente
        parametri["password"] = credenziali.password
        parametri["authSource"] = "admin"
    return MongoClient(vista.uri, **parametri)
