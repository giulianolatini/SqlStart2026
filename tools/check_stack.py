"""Verifica che un file Compose del lab rispetti le decisioni prese negli ADR."""

from __future__ import annotations

import pathlib
import re

IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# Una riga `FROM`, con tutto ciò che la segue: le opzioni (`--platform=…`), il
# riferimento e l'eventuale `AS nome`. Si separano dopo, a pezzi, perché la
# forma è variabile e una sola espressione regolare che le coprisse tutte
# sarebbe illeggibile prima di essere sbagliata.
FROM_RIGA = re.compile(r"^\s*FROM\s+(?P<resto>.+?)\s*$", re.IGNORECASE | re.MULTILINE)

# `${NOME}` o `$NOME`: un `FROM` che non nomina un'immagine ma un argomento di
# costruzione, il cui valore vero sta in `build.args` del file Compose.
RIFERIMENTO_ARGOMENTO = re.compile(
    r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$|^\$([A-Za-z_][A-Za-z0-9_]*)$"
)

# `${NOME}`, `${NOME:-predefinito}`, `${NOME:?spiegazione}`.
VARIABILE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::([-?])([^}]*))?\}")

# Sessantaquattro cifre, non «da tre a sessantaquattro»: un digest SHA-256 più
# corto Docker lo rifiuta, e accettarlo qui vorrebbe dire approvare uno stack
# che non si avvia.
DIGEST = re.compile(r"\bsha256:[0-9a-f]{64}\b")

# `0.0.0.0` e `127.0.0.1` dicono su quali interfacce ascoltare, non dove trovare un
# altro nodo. La regola sui nomi host colpisce la topologia, non l'ascolto.
MASCHERE_DI_ASCOLTO = {"0.0.0.0", "127.0.0.1"}

# Suffissi accettati da Compose per le dimensioni di memoria, in MiB.
# La Specification elenca «2b, 1024kb, 2048k, 300m, 1gb»: le unità sono binarie.
SUFFISSI_MIB: dict[str, float] = {
    "b": 1 / (1024 * 1024),
    "k": 1 / 1024,
    "kb": 1 / 1024,
    "m": 1.0,
    "mb": 1.0,
    "g": 1024.0,
    "gb": 1024.0,
}


def risolvi(testo: str, ambiente: dict[str, str]) -> str:
    """Sostituisce le variabili di Compose come le sostituirebbe Compose.

    La forma `${NOME:?spiegazione}` esiste per far fallire l'avvio subito e con un
    messaggio invece di partire con un valore vuoto. Lo strumento fallisce nello
    stesso punto: sorvolare qui vorrebbe dire verificare un file diverso da quello
    che Docker leggerà.

    I due punti contano. In `${NOME:-x}` e `${NOME:?x}` una variabile **vuota**
    vale quanto una assente, e Compose prende l'alternativa; in `${NOME}` il
    vuoto è un valore e va restituito tale. Sono le sole tre forme modellate,
    perché sono le sole che i file Compose del lab usano.
    """

    def sostituisci(trovato: re.Match[str]) -> str:
        nome, operatore, argomento = trovato.groups()
        valore = ambiente.get(nome, "")
        if operatore is None or valore:
            return valore
        if operatore == "-":
            return argomento
        raise KeyError(f"{nome}: {argomento}")

    return VARIABILE.sub(sostituisci, testo)


def leggi_ambiente(percorso) -> dict[str, str]:
    """Legge un file `NOME=valore`, saltando commenti e righe vuote."""
    ambiente: dict[str, str] = {}
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        spogliata = riga.strip()
        if not spogliata or spogliata.startswith("#") or "=" not in spogliata:
            continue
        nome, _, valore = spogliata.partition("=")
        ambiente[nome.strip()] = valore.strip()
    return ambiente


def digest_noti_da(ambiente: dict[str, str]) -> set[str]:
    """I digest dichiarati in `tools/images.env`, cioè quelli che il lab scarica."""
    return {
        digest for valore in ambiente.values() for digest in DIGEST.findall(valore)
    }


def _risolvi_ovunque(nodo, ambiente: dict[str, str]):
    """Applica `risolvi` a ogni stringa dell'albero, lasciando intatto il resto."""
    if isinstance(nodo, str):
        return risolvi(nodo, ambiente)
    if isinstance(nodo, list):
        return [_risolvi_ovunque(voce, ambiente) for voce in nodo]
    if isinstance(nodo, dict):
        return {
            chiave: _risolvi_ovunque(valore, ambiente) for chiave, valore in nodo.items()
        }
    return nodo


# I due `VOLUME` dichiarati dall'immagine ufficiale di MongoDB. Sono i soli
# percorsi dove dimenticare un montaggio non dà un errore ma un volume anonimo,
# che è la differenza fra accorgersene subito e accorgersene al secondo avvio.
CARTELLE_DATI = ("/data/db", "/data/configdb")


def leggi_documento(percorso) -> dict:
    """Legge un file Compose senza toccarne le variabili.

    Serve alla regola sul `pull_policy`, che deve giudicare ciò che è scritto nel
    file e non ciò che ne esce dopo l'interpolazione: le due cose coincidono solo
    finché qualcuno non passa un ambiente diverso.
    """
    import yaml

    return yaml.safe_load(percorso.read_text(encoding="utf-8")) or {}


def carica(percorso, ambiente: dict[str, str]) -> dict:
    """Legge un file Compose e ne risolve le variabili.

    La sostituzione avviene **dopo** l'analisi YAML e non sul testo grezzo: un
    valore che contenesse due punti o virgolette cambierebbe la struttura del
    documento invece del proprio contenuto.
    """
    return _risolvi_ovunque(leggi_documento(percorso), ambiente)


def in_mib(valore: str | int) -> float | None:
    """Converte un `mem_limit` di Compose in MiB. `None` se non è interpretabile."""
    if isinstance(valore, int):
        return valore / (1024 * 1024)
    testo = str(valore).strip().lower()
    for suffisso in sorted(SUFFISSI_MIB, key=len, reverse=True):
        if testo.endswith(suffisso):
            numero = testo[: -len(suffisso)]
            try:
                return float(numero) * SUFFISSI_MIB[suffisso]
            except ValueError:
                return None
    try:
        return float(testo) / (1024 * 1024)
    except ValueError:
        return None


def cache_in_mib(comando: object) -> float | None:
    """Estrae `--wiredTigerCacheSizeGB` dal comando del servizio, in MiB.

    L'opzione è letta in **GiB**, non in GB decimali: `0.25` configura 268435456
    byte, cioè esattamente 256 MiB. La cifra `0.256` che compare nel manuale è un
    GB decimale scritto dove l'implementazione usa GiB, e non corrisponde a nulla
    (misurato in V-009).
    """
    if isinstance(comando, str):
        pezzi = comando.split()
    elif isinstance(comando, list):
        pezzi = [str(pezzo) for pezzo in comando]
    else:
        return None
    for indice, pezzo in enumerate(pezzi):
        if pezzo == "--wiredTigerCacheSizeGB" and indice + 1 < len(pezzi):
            try:
                return float(pezzi[indice + 1]) * 1024
            except ValueError:
                return None
        if pezzo.startswith("--wiredTigerCacheSizeGB="):
            try:
                return float(pezzo.split("=", 1)[1]) * 1024
            except ValueError:
                return None
    return None


def pezzi_del_comando(comando: object) -> list[str]:
    """Il comando del servizio come lista di parole, vuota se non ce n'è uno."""
    if isinstance(comando, str):
        return comando.split()
    if isinstance(comando, list):
        return [str(pezzo) for pezzo in comando]
    return []


def valore_opzione(comando: object, opzione: str) -> str | None:
    """Il valore di un'opzione del comando, nelle due forme che Compose ammette.

    `--opzione valore` e `--opzione=valore` sono la stessa cosa per il processo:
    riconoscerne una sola vorrebbe dire avere una regola che si aggira scrivendo
    la stessa riga in un altro modo.
    """
    pezzi = pezzi_del_comando(comando)
    for indice, pezzo in enumerate(pezzi):
        if pezzo == opzione and indice + 1 < len(pezzi):
            return pezzi[indice + 1]
        if pezzo.startswith(opzione + "="):
            return pezzo.split("=", 1)[1]
    return None


def avvia_mongod(comando: object) -> bool:
    """Vero se il servizio avvia un `mongod`.

    Il bersaglio della regola sulla cache sono i processi che hanno storage. Un
    `mongos` instrada e basta: pretendere una cache da lui sarebbe una regola che
    sbaglia bersaglio.

    Le forme riconosciute sono **due**, e la seconda è la ragione per cui questa
    funzione è stata riscritta. L'entrypoint dell'immagine ufficiale antepone
    `mongod` da sé quando il primo argomento comincia per trattino (S-022):

        if [ "${1:0:1}" = '-' ]; then set -- mongod "$@"; fi

    Per Docker `[mongod, --replSet, rs0]` e `[--replSet, rs0]` avviano lo stesso
    identico processo. Finché qui se ne riconosceva una sola, un file scritto
    nella forma abbreviata passava il controllo senza dichiarare la cache: la
    regola c'era e non poteva fallire, che è il modo peggiore in cui un controllo
    può essere sbagliato (misurato al Task 3 di feature/02).

    Il prezzo è un'assunzione dichiarata: che l'immagine sia quella ufficiale di
    MongoDB. In questo repository lo è dappertutto, e un falso positivo qui
    chiederebbe una cache a un servizio che non ne ha bisogno — rumoroso e
    innocuo, cioè il verso giusto in cui sbagliare.
    """
    pezzi = pezzi_del_comando(comando)
    if not pezzi:
        return False
    return pezzi[0].startswith("-") or pezzi[0].rsplit("/", 1)[-1] == "mongod"


def avvia_mongos(comando: object) -> bool:
    """Vero se il servizio avvia un `mongos`.

    Qui non serve la seconda forma che `avvia_mongod` deve riconoscere:
    l'entrypoint ufficiale antepone `mongod` quando il primo argomento comincia
    per trattino ([S-022]), e non antepone mai `mongos`. Un router va scritto per
    nome per forza, quindi guardare la prima parola del comando basta.

    È l'unica domanda che decide se lo stack è sharded, e quindi se le regole dei
    ruoli si accendono. Vale la pena vedere che cosa NON è: non è un elenco di
    nomi di servizio, non è il nome della cartella, non è un argomento passato
    dall'esterno. È una riga del file che si sta controllando.
    """
    pezzi = pezzi_del_comando(comando)
    return bool(pezzi) and pezzi[0].rsplit("/", 1)[-1] == "mongos"


def ha_opzione(comando: object, opzione: str) -> bool:
    """Vero se il comando porta l'opzione, che abbia un valore o non ne abbia.

    `valore_opzione` non risponde a questa domanda e non poteva: `--shardsvr` è
    un interruttore, e chiedergli il valore restituisce la parola dopo, cioè
    `--replSet`. Sono due funzioni perché sono due domande diverse, e confonderle
    darebbe una regola che approva `--shardsvr` scritto per ultimo e boccia lo
    stesso `--shardsvr` scritto per primo.
    """
    pezzi = pezzi_del_comando(comando)
    return any(
        pezzo == opzione or pezzo.startswith(opzione + "=") for pezzo in pezzi
    )


def nome_del_set(configdb: str | None) -> str | None:
    """Il nome del replica set dentro un `--configdb`, `None` se non c'è.

    Dalla 3.4 `mongos` accetta soltanto la forma `nomeSet/host:porta,…`. L'elenco
    nudo di host è la scrittura di prima, ed è quella che si trova copiando una
    guida vecchia: oggi il router non parte (misurato in V-057 e V-070).

    **Un nome vuoto è un nome assente.** `/cfg1:27017` la barra ce l'ha, ma prima
    non c'è niente. Restituire `""` non farebbe passare il file — il chiamante
    cercherebbe comunque quel nome fra i `--replSet` e non lo troverebbe — ma lo
    manderebbe sul messaggio sbagliato: quello del refuso, che dice «i processi
    partono tutti», mentre `mongos` con quell'argomento non parte affatto
    (V-070). Lo spazio conta come vuoto per la stessa ragione.
    """
    if not configdb or "/" not in configdb:
        return None
    return configdb.split("/", 1)[0].strip() or None


def montaggi(servizio: dict) -> list[tuple[str, str]]:
    """Le coppie (sorgente, destinazione) dei volumi dichiarati dal servizio."""
    coppie: list[tuple[str, str]] = []
    for voce in servizio.get("volumes") or ():
        if isinstance(voce, str):
            pezzi = voce.split(":")
            if len(pezzi) >= 2:
                coppie.append((pezzi[0], pezzi[1]))
        elif isinstance(voce, dict):
            sorgente, destinazione = voce.get("source"), voce.get("target")
            if sorgente and destinazione:
                coppie.append((str(sorgente), str(destinazione)))
    return coppie


def e_volume_nominato(sorgente: str) -> bool:
    """Vero per `keyfile:`, falso per `./keyfile:` e `/tmp/keyfile:`.

    È la stessa distinzione che fa Compose: una sorgente che comincia per punto,
    barra o tilde è un percorso dell'host, tutto il resto è un volume nominato.
    """
    return not sorgente.startswith((".", "/", "~")) and "/" not in sorgente


def e_restart_no(servizio: dict) -> bool:
    """Vero se il servizio dichiara `restart: "no"`.

    Le virgolette servono davvero: in YAML un `no` nudo è il booleano falso, non
    la stringa. Qui si accettano entrambi perché l'intenzione è la stessa, ma il
    messaggio d'errore continua a consigliare la forma con le virgolette, che è
    quella che Compose documenta.
    """
    valore = servizio.get("restart")
    return valore is False or str(valore).strip().lower() == "no"


def problemi_keyfile(nome: str, servizio: dict) -> list[str]:
    """Il keyfile deve arrivare da un volume nominato, non dall'host.

    ADR-0014 nasce da una misura: su macOS un bind mount non conserva i permessi
    del file, e `mongod` rifiuta un keyfile che altri possano leggere. Il sintomo
    è un membro che non parte; la causa è in un'altra riga di un altro file, e
    nessun messaggio collega le due cose.
    """
    percorso = valore_opzione(servizio.get("command"), "--keyFile")
    if percorso is None:
        return []

    for sorgente, destinazione in montaggi(servizio):
        copre = percorso == destinazione or percorso.startswith(
            destinazione.rstrip("/") + "/"
        )
        if not copre:
            continue
        if e_volume_nominato(sorgente):
            return []
        return [
            f"{nome}: il keyfile «{percorso}» arriva da «{sorgente}», che è un "
            "percorso dell'host. Un bind mount non conserva i permessi del file e "
            "mongod rifiuta un keyfile leggibile da altri: serve un volume "
            "nominato (ADR-0014)"
        ]

    return [
        f"{nome}: dichiara «--keyFile {percorso}» ma nessun volume monta quel "
        "percorso. Il processo parte e muore, e il file Compose sembra a posto "
        "perché la riga c'è (ADR-0014)"
    ]


def dbpath_effettivo(comando: object) -> str:
    """Il percorso in cui `mongod` scriverà davvero, dichiarato o no.

    Tre casi, e il secondo è quello che nessuno si aspetta. Se il comando porta
    `--dbpath`, vale quello. Altrimenti, se porta `--configsvr`, l'entrypoint
    dell'immagine ufficiale porta il predefinito a **/data/configdb** e non a
    /data/db. Righe 236-238 dell'entrypoint dentro l'immagine pinnata, lette
    con `docker run --rm --entrypoint cat` (V-060):

        # if running as config server, then the default dbpath is /data/configdb
        dbPath=/data/configdb

    Il ramo 8.0 dello stesso script dice la stessa cosa con altre parole
    ([S-022]). In tutti gli altri casi è /data/db, il predefinito di `mongod`.
    """
    dichiarato = valore_opzione(comando, "--dbpath")
    if dichiarato:
        return dichiarato
    if ha_opzione(comando, "--configsvr"):
        return "/data/configdb"
    return "/data/db"


def problemi_persistenza(nome: str, servizio: dict) -> list[str]:
    """Un volume dei dati va montato dove il processo scrive, non dove sembra.

    La regola nasce da un difetto misurato, non da un timore. I config server
    dello stack 03 montavano `dati-cfgN` su /data/db — il posto giusto per
    qualunque altro mongod — mentre con `--configsvr` scrivevano in
    /data/configdb. Lì l'immagine dichiara `VOLUME`, quindi Compose ce ne
    metteva uno ANONIMO: `down` lo lasciava penzolante e il `up` successivo ne
    fabbricava un altro vuoto. Risultato, i metadati del cluster sparivano a
    ogni spegnimento mentre gli shard conservavano i loro dati, e il giro dopo
    `sh.addShard()` rifiutava il secondo shard con «a local database 'lab'
    exists in another shard1rs». Il volume nominato conteneva zero file, quello
    di uno shard ottantatré (V-060, ADR-0067).

    Le due cartelle sono scritte qui, e non è la lista di eccezioni che [ADR-0042]
    proibisce: quella elencava NOMI DI SERVIZIO, che cambiano a ogni stack nuovo.
    Queste due sono i `VOLUME` che l'immagine ufficiale dichiara — si leggono con
    `docker image inspect --format '{{json .Config.Volumes}}'` — e sono l'elenco
    esatto dei posti dove un montaggio mancato diventa un volume anonimo invece
    di un errore. Cambiano solo se cambia l'immagine.

    La regola giudica un montaggio SBAGLIATO, non un montaggio mancante: un
    mongod senza volumi dati non produce niente, perché lo stack 01 gira così
    per scelta e perché «questo servizio non conserva niente» è una decisione
    legittima che un file può prendere.
    """
    comando = servizio.get("command")
    if not avvia_mongod(comando):
        return []

    percorso = dbpath_effettivo(comando).rstrip("/")
    problemi: list[str] = []
    for sorgente, destinazione in montaggi(servizio):
        destinazione = destinazione.rstrip("/")
        if destinazione not in CARTELLE_DATI:
            continue
        if destinazione != percorso:
            problemi.append(
                f"{nome}: monta «{sorgente}» su «{destinazione}» ma scriverà in "
                f"«{percorso}». Là l'immagine dichiara un VOLUME, che Compose "
                "soddisfa con un volume ANONIMO: «down» lo abbandona e i dati "
                "spariscono a ogni spegnimento, senza un errore (ADR-0067)"
            )
        elif not e_volume_nominato(sorgente):
            problemi.append(
                f"{nome}: il dbpath «{percorso}» arriva da «{sorgente}», che è "
                "un percorso dell'host. I dati del lab finiscono nell'albero di "
                "lavoro e su macOS ereditano i permessi che mongod rifiuta: "
                "serve un volume nominato (ADR-0014)"
            )
    return problemi


def problemi_di_ruolo(
    nome: str,
    servizio: dict,
    sharded: bool,
    set_di_configurazione: set[str],
    set_dichiarati: set[str],
) -> list[str]:
    """Le regole dei tre ruoli di uno sharded cluster.

    Il problema vero non è controllare che due opzioni ci siano: è **decidere
    che ruolo ha un servizio**, e deciderlo senza chiederlo a un elenco di nomi.
    La catena che lo permette sta tutta dentro il file. Il `mongos` dichiara in
    `--configdb` il nome del replica set dei config server; ogni `mongod`
    dichiara in `--replSet` a quale set appartiene; chi appartiene a quel set è
    un config server, e chiunque altro è uno shard. Nessuno dei tre passaggi
    guarda il nome del servizio, ed è la ragione per cui rinominare `cfg1` in
    `secondo` non sposta un verdetto.

    Le regole tacciono sugli stack 01 e 02 perché quei file non hanno un
    `mongos`, non perché compaiano in una lista di eccezioni. È lo stesso criterio
    di [ADR-0042] e per lo stesso motivo: una lista di eccezioni invecchia in
    silenzio, una guardia che legge il file no.

    Nessuno dei sintomi che queste regole prevengono è muto — il server nomina
    ogni volta l'opzione che manca, e la scoperta ha corretto un commento che
    diceva il contrario. Il guadagno non è tradurre un messaggio oscuro, è
    incontrarlo con `make stack-check` in due secondi invece che al minuto e
    ventuno di un avvio, davanti al pubblico. L'unica eccezione è il refuso nel
    nome del set, che non produce nessun messaggio: lì la regola è l'unica cosa
    che parla.
    """
    comando = servizio.get("command")
    problemi: list[str] = []

    if avvia_mongod(comando):
        configsvr = ha_opzione(comando, "--configsvr")
        shardsvr = ha_opzione(comando, "--shardsvr")
        insieme = valore_opzione(comando, "--replSet")

        if configsvr and shardsvr:
            # Prima delle altre due, e al posto loro: con entrambe le opzioni il
            # ruolo non è ambiguo, è impossibile, e aggiungere «manca --shardsvr»
            # a «ci sono tutti e due» sarebbe rumore sopra la diagnosi giusta.
            problemi.append(
                f"{nome}: dichiara «--configsvr» e «--shardsvr» nello stesso "
                "comando. mongod non parte affatto — «BadValue: shardsvr is not "
                "allowed when configsvr is specified» — e un file che fonde i due "
                "ruoli insegna il contrario di quello per cui lo stack 03 è stato "
                "scritto (ADR-0063, V-057)"
            )
        elif sharded and insieme in set_di_configurazione and not configsvr:
            problemi.append(
                f"{nome}: sta nel replica set «{insieme}», che «--configdb» "
                "indica come quello dei config server, ma non dichiara "
                "«--configsvr». rs.initiate() lo rifiuta — «Nodes being used for "
                "config servers must be started with the --configsvr flag» — e la "
                "catena si ferma al primo anello (ADR-0063, V-057)"
            )
        elif (
            sharded
            and insieme is not None
            and insieme not in set_di_configurazione
            and not shardsvr
        ):
            problemi.append(
                f"{nome}: sta nel replica set «{insieme}», che non è quello "
                "nominato da «--configdb», quindi è uno shard, e un membro di "
                "shard dichiara «--shardsvr». Senza, parte tutto e a rifiutarlo è "
                "l'ultimo anello: «Cannot run addShard on a node started without "
                "--shardsvr» (ADR-0063, V-057)"
            )

    if avvia_mongos(comando):
        configdb = valore_opzione(comando, "--configdb")
        if configdb is None:
            problemi.append(
                f"{nome}: avvia un mongos senza «--configdb». Il router non ha "
                "una mappa del cluster da leggere e si ferma sulla riga di "
                "comando: «BadValue: error: no args for --configdb» (ADR-0063, "
                "V-057)"
            )
        elif nome_del_set(configdb) is None:
            problemi.append(
                f"{nome}: «--configdb {configdb}» non nomina un replica set. "
                "Dalla 3.4 mongos accetta soltanto la forma "
                "«nomeSet/host:porta,…» e rifiuta il resto sulla riga di "
                "comando, con due messaggi diversi: «FailedToParse: invalid "
                "url» su un elenco di host separati da virgola, «BadValue: "
                "configdb supports only replica set connection string» su un "
                "host solo o su un nome di set vuoto (ADR-0063, V-057, V-070)"
            )
        elif nome_del_set(configdb) not in set_dichiarati:
            problemi.append(
                f"{nome}: «--configdb» nomina il replica set "
                f"«{nome_del_set(configdb)}», che nessun mongod di questo file "
                "dichiara con «--replSet». È il caso del refuso, ed è l'unico in "
                "cui nessuno protesta: i processi partono tutti, e mongos resta a "
                "cercare un set che non esiste (ADR-0063)"
            )

        if cache_in_mib(comando) is not None:
            problemi.append(
                f"{nome}: avvia un mongos con «--wiredTigerCacheSizeGB». Il router "
                "non ha uno storage engine e l'opzione per lui non esiste: «Error "
                "parsing command line: unrecognised option», e il container esce "
                "subito. È l'errore che nasce copiando il blocco di un mongod e "
                "cambiando la prima riga (ADR-0063, V-057)"
            )

    return problemi


def basi_del_dockerfile(testo: str) -> list[str]:
    """Le immagini da cui una costruzione parte davvero: un `FROM`, meno gli stadi.

    `FROM base AS uv` dichiara uno stadio; `FROM uv` più sotto non scarica niente,
    riusa quello. Contarlo fra le immagini darebbe un falso positivo su ogni
    costruzione a più stadi — che è la forma con cui `app/Dockerfile` prende il
    binario di uv senza installarlo con pip.
    """
    basi: list[str] = []
    stadi: set[str] = set()
    for trovato in FROM_RIGA.finditer(testo):
        # Le opzioni della riga (`--platform`, `--chmod`) non sono l'immagine.
        pezzi = [
            pezzo for pezzo in trovato.group("resto").split() if not pezzo.startswith("--")
        ]
        if not pezzi:
            continue
        if len(pezzi) >= 3 and pezzi[1].lower() == "as":
            stadi.add(pezzi[2].lower())
        if pezzi[0].lower() in stadi:
            continue
        basi.append(pezzi[0])
    return basi


def argomenti_di_costruzione(build: object) -> dict[str, str]:
    """`build.args`, nelle due forme che la Specification ammette: mappa o elenco."""
    if not isinstance(build, dict):
        return {}
    argomenti = build.get("args")
    if isinstance(argomenti, dict):
        return {str(k): str(v) for k, v in argomenti.items() if v is not None}
    if isinstance(argomenti, list):
        letti: dict[str, str] = {}
        for voce in argomenti:
            nome, _, valore = str(voce).partition("=")
            letti[nome.strip()] = valore.strip()
        return letti
    return {}


def problemi_costruzione(
    nome: str, servizio: dict, digest_noti: set[str], percorso: object | None
) -> list[str]:
    """La regola del digest, spostata dove ha senso per un servizio che si costruisce.

    La prima stesura di questa docstring diceva che un'immagine costruita in
    locale «non ha un digest». È falso, e a smentirlo è bastato guardare
    ([M-037](../app/docs/Sources.md#m-037)): con l'archivio immagini di
    containerd — quello che Docker Desktop usa qui — anche un'immagine mai
    pubblicata ha il suo digest di manifesto, e `docker image inspect
    mongolab@sha256:…` la trova.

    Il punto vero è un altro, e regge lo stesso: quel digest **nessun registro
    l'ha mai servito**, quindi non è verificabile da fuori, e cambia a ogni
    ricostruzione. Scriverlo in `tools/images.env` darebbe a `pull-images.sh
    --verify` una cosa da cercare in rete che in rete non c'è, e la mattina del
    talk il preflight fallirebbe accusando la cache di un difetto che non ha.

    Lo scopo della regola però resta: nessun bit arriva dalla rete senza che
    qualcuno l'abbia fissato. Per un servizio che si costruisce quei bit sono le
    sue **basi**, cioè le righe `FROM` del suo Dockerfile — e quelle devono essere
    pinnate per digest, e per un digest che `tools/images.env` conosce, altrimenti
    `pull-images.sh` non le porta in cache e la costruzione cerca la rete (ADR-0009).
    """
    build = servizio.get("build")
    if percorso is None:
        return [
            f"{nome}: dichiara «build» ma il controllo non sa da dove risolverne il "
            "contesto. Le basi del Dockerfile non sono state guardate: passare il "
            "percorso del file Compose"
        ]
    if isinstance(build, str):
        contesto, dockerfile = build, "Dockerfile"
    elif isinstance(build, dict):
        contesto = str(build.get("context", "."))
        dockerfile = str(build.get("dockerfile", "Dockerfile"))
    else:
        return [f"{nome}: «build» non è né un percorso né una mappa"]

    # Il contesto è relativo alla cartella del file Compose, non alla radice del
    # repository né alla cartella da cui si esegue il controllo.
    quale = pathlib.Path(str(percorso)).parent / contesto / dockerfile
    try:
        testo = quale.read_text(encoding="utf-8")
    except OSError as errore:
        return [
            f"{nome}: non riesco a leggere «{quale}» ({errore.strerror}). Il contesto "
            "di «build» si risolve dalla cartella del file Compose"
        ]

    argomenti = argomenti_di_costruzione(build)
    problemi: list[str] = []
    for base in basi_del_dockerfile(testo):
        trovato = RIFERIMENTO_ARGOMENTO.match(base)
        if trovato:
            chiave = trovato.group(1) or trovato.group(2)
            if chiave not in argomenti:
                problemi.append(
                    f"{nome}: «{dockerfile}» parte da «{base}», ma «build.args» non "
                    f"dichiara {chiave}: la base resterebbe quella predefinita del "
                    "Dockerfile, o nessuna"
                )
                continue
            riferimento = argomenti[chiave]
        else:
            riferimento = base

        if "@sha256:" not in riferimento:
            problemi.append(
                f"{nome}: la base «{riferimento}» di {dockerfile} non è pinnata per "
                "digest. Un tag può cambiare contenuto sotto lo stesso nome, anche "
                "quando sta in un Dockerfile invece che in un compose (ADR-0009)"
            )
        elif riferimento.split("@", 1)[1] not in digest_noti:
            digest = riferimento.split("@", 1)[1]
            problemi.append(
                f"{nome}: la base «{riferimento}» di {dockerfile} ha il digest "
                f"«{digest}», che non compare in tools/images.env: pull-images.sh non "
                "lo scarica e la costruzione cercherebbe la rete (ADR-0009)"
            )
    return problemi


def verifica(
    documento: dict,
    digest_noti: set[str],
    grezzo: dict | None = None,
    percorso: object | None = None,
) -> list[str]:
    """Restituisce l'elenco dei problemi. Lista vuota significa conformità.

    `documento` è il file dopo l'interpolazione, `grezzo` prima. Quasi tutte le
    regole guardano il primo, perché giudicano lo stack che si avvia. Quella sul
    `pull_policy` guarda il secondo, perché giudica ciò che il file promette a
    chi lo apre. Se `grezzo` manca si assume che i due coincidano.
    """
    problemi: list[str] = []
    servizi_grezzi = (grezzo or documento).get("services", {})

    # Due regole valgono per l'INTERO file e non per il singolo servizio: uno
    # stack che dichiara un replica set pretende `--replSet` e `--keyFile` da
    # ogni mongod, e uno stack che non lo dichiara non deve pretendere niente.
    # È la guardia che tiene verde lo stack 01, che gira senza autenticazione
    # per scelta didattica (ADR-0005): la regola si accende leggendo il file,
    # non consultando un elenco di nomi che qualcuno dovrebbe tenere aggiornato.
    stack_con_replica = any(
        valore_opzione(servizio.get("command"), "--replSet")
        for servizio in documento.get("services", {}).values()
    )

    # Il terzo ruolo, e la domanda che accende le regole del Task 5: c'è un
    # `mongos` in questo file? Se c'è, lo stack instrada, e allora ogni mongod ha
    # un ruolo da dichiarare. Se non c'è — stack 01 e stack 02 — non si pretende
    # niente, e nessuno dei due compare in una lista di eccezioni.
    servizi_tutti = documento.get("services", {}).values()
    router = [
        servizio
        for servizio in servizi_tutti
        if avvia_mongos(servizio.get("command"))
    ]
    # Chi sono i config server lo dice il `mongos`, nominando il loro replica set
    # in `--configdb`. Non lo dice il nome del servizio, che è una convenzione, né
    # una lista in questo file, che invecchierebbe.
    set_di_configurazione = {
        nome_del_set(valore_opzione(servizio.get("command"), "--configdb"))
        for servizio in router
    } - {None}
    set_dichiarati = {
        valore_opzione(servizio.get("command"), "--replSet")
        for servizio in servizi_tutti
    } - {None}

    if "version" in documento:
        problemi.append(
            "la chiave «version» al livello superiore è obsoleta nella Compose "
            "Specification: va tolta, non aggiornata"
        )

    for nome, servizio in sorted(documento.get("services", {}).items()):
        # Un servizio che si costruisce non può avere un digest di registro, e la
        # regola si sposta sulle basi del suo Dockerfile invece di sparire.
        costruisce = "build" in servizio
        if costruisce:
            problemi += problemi_costruzione(nome, servizio, digest_noti, percorso)

        immagine = str(servizio.get("image", ""))
        if not immagine:
            problemi.append(f"{nome}: manca «image»")
        elif "@sha256:" not in immagine:
            if immagine.endswith(":latest") or ":" not in immagine.rsplit("/", 1)[-1]:
                problemi.append(
                    f"{nome}: usa il tag «latest», esplicito o implicito. «The latest "
                    "tag is always pulled even when the missing pull policy is used»: "
                    "il vincolo offline salterebbe senza preavviso (ADR-0018)"
                )
            if not costruisce:
                problemi.append(
                    f"{nome}: l'immagine «{immagine}» non è pinnata per digest. Un tag "
                    "può cambiare contenuto sotto lo stesso nome; il digest no "
                    "(ADR-0009, ADR-0028)"
                )
        else:
            digest = immagine.split("@", 1)[1]
            if digest not in digest_noti:
                problemi.append(
                    f"{nome}: il digest «{digest}» non compare in tools/images.env, "
                    "quindi pull-images.sh non lo scarica e la cache locale non lo "
                    "avrà il giorno del talk (ADR-0009)"
                )

        politica = servizio.get("pull_policy")
        scritta = servizi_grezzi.get(nome, {}).get("pull_policy")
        if politica is None:
            problemi.append(
                f"{nome}: manca «pull_policy: never». Senza, Compose scarica ciò "
                "che manca, e in sala non c'è rete da cui scaricare (ADR-0039)"
            )
        elif politica != "never":
            problemi.append(
                f"{nome}: «pull_policy: {politica}». L'unico valore ammesso è "
                "«never», che è anche l'unico con una frase documentale esplicita "
                "sul non contattare il registro (ADR-0039)"
            )
        elif isinstance(scritta, str) and VARIABILE.search(scritta):
            problemi.append(
                f"{nome}: «pull_policy: {scritta}» vale «never» solo grazie "
                "all'ambiente passato adesso. Una variabile si dimentica, un file "
                "no: la garanzia va scritta nell'artefatto (ADR-0039)"
            )

        for chiave in ("mem_limit", "cpus"):
            if chiave not in servizio:
                problemi.append(
                    f"{nome}: manca «{chiave}». Senza limiti espliciti N mongod "
                    "rivendicano ciascuno metà VM e l'OOM killer si presenta davanti "
                    "al pubblico (ADR-0004, sintassi breve per ADR-0013)"
                )

        limite = in_mib(servizio.get("mem_limit", ""))
        cache = cache_in_mib(servizio.get("command"))
        if cache is None and avvia_mongod(servizio.get("command")):
            problemi.append(
                f"{nome}: avvia mongod senza «--wiredTigerCacheSizeGB». Il valore va "
                "dichiarato a mano perché il file Compose è materiale didattico e il "
                "calcolo deve vedersi (ADR-0004)"
            )
        if cache is not None and limite is not None and cache > limite:
            problemi.append(
                f"{nome}: --wiredTigerCacheSizeGB configura {cache:.0f} MiB di cache "
                f"dentro un mem_limit di {limite:.0f} MiB. Nessuno lo controlla al "
                "posto nostro: mongod accetta il valore senza un avviso che colleghi "
                "le due cifre (ADR-0004, V-009)"
            )

        if stack_con_replica and avvia_mongod(servizio.get("command")):
            if not valore_opzione(servizio.get("command"), "--replSet"):
                problemi.append(
                    f"{nome}: avvia un mongod senza «--replSet» in uno stack che "
                    "dichiara un replica set. Resta un'istanza a sé, e nessuno lo "
                    "dice (ADR-0021)"
                )
            if not valore_opzione(servizio.get("command"), "--keyFile"):
                problemi.append(
                    f"{nome}: avvia un membro di replica set senza «--keyFile». "
                    "Parte lo stesso e resta fuori dalla replica: gli altri lo "
                    "rifiutano all'handshake, e nei log sembra un problema di rete "
                    "(ADR-0014)"
                )

        # Il router ha bisogno dello stesso segreto, e la regola qui sopra non lo
        # copre: `mongos` non è un `mongod`, e per due anelli della stessa catena
        # servivano due domande. Senza `--keyFile` il router parte, non diventa mai
        # sano e ripete `Error loading global settings from config server` con
        # dentro `Unauthorized: Command find requires authentication` — che manda a
        # cercare una password sbagliata mentre manca il keyfile (V-071).
        if stack_con_replica and avvia_mongos(servizio.get("command")):
            if not valore_opzione(servizio.get("command"), "--keyFile"):
                problemi.append(
                    f"{nome}: avvia un mongos senza «--keyFile». Il router non ha "
                    "il segreto con cui il resto del cluster si autentica: parte, "
                    "resta unhealthy e ripete «Error loading clusterID :: caused "
                    "by :: Command find requires authentication», che sembra una "
                    "credenziale sbagliata e invece è una riga mancante "
                    "(ADR-0014, V-071)"
                )

        problemi.extend(problemi_keyfile(nome, servizio))
        problemi.extend(problemi_persistenza(nome, servizio))

        problemi.extend(
            problemi_di_ruolo(
                nome,
                servizio,
                bool(router),
                set_di_configurazione,
                set_dichiarati,
            )
        )

        for indirizzo in indirizzi_letterali(servizio):
            problemi.append(
                f"{nome}: «{indirizzo}» è un indirizzo IP scritto a mano. La "
                "configurazione di un replica set memorizza i nomi con cui i membri "
                "si chiamano fra loro e li rimanda al client: servono nomi "
                "risolvibili ovunque (ADR-0021)"
            )

        problemi.extend(problemi_ordine_avvio(nome, servizio, documento))

    return problemi


def indirizzi_letterali(servizio: dict) -> list[str]:
    """Gli IPv4 scritti a mano nel servizio, escluse le maschere di ascolto."""
    testo: list[str] = []
    comando = servizio.get("command")
    if isinstance(comando, list):
        testo.extend(str(pezzo) for pezzo in comando)
    elif isinstance(comando, str):
        testo.append(comando)
    ambiente = servizio.get("environment")
    if isinstance(ambiente, dict):
        testo.extend(str(valore) for valore in ambiente.values())
    elif isinstance(ambiente, list):
        testo.extend(str(voce) for voce in ambiente)
    aggiunte = servizio.get("extra_hosts")
    if isinstance(aggiunte, list):
        testo.extend(str(voce) for voce in aggiunte)
    elif isinstance(aggiunte, dict):
        testo.extend(str(valore) for valore in aggiunte.values())

    trovati: list[str] = []
    for pezzo in testo:
        for indirizzo in IPV4.findall(pezzo):
            if indirizzo not in MASCHERE_DI_ASCOLTO and indirizzo not in trovati:
                trovati.append(indirizzo)
    return trovati


def problemi_ordine_avvio(nome: str, servizio: dict, documento: dict) -> list[str]:
    """Controlla che `depends_on` esprima una condizione e non un semplice ordine."""
    dipendenze = servizio.get("depends_on")
    if not dipendenze:
        return []

    if isinstance(dipendenze, list):
        return [
            f"{nome}: «depends_on» in forma breve verso {sorted(dipendenze)} attende "
            "che il container esista, non che il servizio sia pronto. Serve la forma "
            "lunga con «condition» (ADR-0023)"
        ]

    problemi: list[str] = []
    servizi = documento.get("services", {})
    for atteso, opzioni in sorted(dipendenze.items()):
        condizione = (opzioni or {}).get("condition")
        if not condizione:
            problemi.append(
                f"{nome}: «depends_on: {atteso}» non dichiara «condition» (ADR-0023)"
            )
            continue
        bersaglio = servizi.get(atteso, {})

        if condizione == "service_healthy" and "healthcheck" not in bersaglio:
            problemi.append(
                f"{nome} attende «{atteso}» in stato service_healthy, ma «{atteso}» "
                "non ha un «healthcheck»: la condizione non diventerà mai vera "
                "(ADR-0023)"
            )

        if condizione == "service_completed_successfully" and not e_restart_no(
            bersaglio
        ):
            problemi.append(
                f"{atteso}: «{nome}» lo attende come completato, ma «{atteso}» non "
                'dichiara «restart: "no"». Compose lo rialza appena esce, la '
                "condizione non diventa mai vera, e lo stack resta fermo a metà "
                "senza dire perché (ADR-0023)"
            )

        if condizione == "service_started":
            if avvia_mongod(bersaglio.get("command")):
                problemi.append(
                    f"{nome} attende «{atteso}» con «service_started», ma «{atteso}» "
                    "avvia un mongod: la condizione scatta quando il container esiste, "
                    "non quando il server risponde. Serve «service_healthy» — misurato "
                    "al Task 1 di feature/02, ECONNREFUSED al primo colpo (ADR-0023)"
                )
            elif e_restart_no(bersaglio):
                problemi.append(
                    f"{nome} attende «{atteso}» con «service_started», ma «{atteso}» "
                    'è un one-shot (dichiara «restart: "no"»): attenderne l\'avvio '
                    "invece della fine rende la catena non deterministica — riesce "
                    "sulla macchina veloce e fallisce in sala. Serve "
                    "«service_completed_successfully» (ADR-0023)"
                )

    return problemi


def main(argv: list[str] | None = None) -> int:
    import argparse
    import pathlib
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    # `--ambiente` è ripetibile perché lo è `--env-file` di Compose, e per lo
    # stesso motivo: lo stack 02 si avvia con due file (ADR-0041). Uno strumento
    # che ne accettasse uno solo controllerebbe un documento diverso da quello
    # che verrà avviato. L'ordine è quello di Compose — «Later files can override
    # variables from earlier files» (S-056).
    parser.add_argument(
        "--ambiente",
        type=pathlib.Path,
        action="append",
        metavar="FILE",
        help="un file «NOME=valore», ripetibile; gli ultimi vincono sui primi "
        "(default: tools/images.env)",
    )
    # `--variabile` serve ai file che dichiarano `${NOME:?…}` quando il `.env`
    # vero non è nel repository — il caso della password dello stack 02, che è
    # ignorata da git apposta. Il valore passato qui non avvia niente: esiste
    # solo perché il documento si possa interpolare e quindi controllare.
    parser.add_argument(
        "--variabile",
        action="append",
        default=[],
        metavar="NOME=valore",
        help="una variabile singola, che vince su tutti i file",
    )
    parser.add_argument("compose", type=pathlib.Path, nargs="+")
    argomenti = parser.parse_args(argv)

    ambiente: dict[str, str] = {}
    for sorgente in argomenti.ambiente or [pathlib.Path("tools/images.env")]:
        try:
            ambiente.update(leggi_ambiente(sorgente))
        except OSError as errore:
            print(
                f"Non riesco a leggere «{sorgente}»: {errore.strerror}. "
                "Il file si genera con `make images-pull`.",
                file=sys.stderr,
            )
            return 2

    for dichiarazione in argomenti.variabile:
        nome, uguale, valore = dichiarazione.partition("=")
        if not uguale or not nome.strip():
            print(
                f"«{dichiarazione}» non è nella forma NOME=valore.",
                file=sys.stderr,
            )
            return 2
        ambiente[nome.strip()] = valore.strip()

    digest = digest_noti_da(ambiente)
    totale = 0
    for percorso in argomenti.compose:
        try:
            grezzo = leggi_documento(percorso)
            documento = _risolvi_ovunque(grezzo, ambiente)
        except OSError as errore:
            # Chi esegue lo strumento sbaglia il percorso prima di sbagliare lo
            # stack: un traceback qui non aiuterebbe nessuno.
            print(
                f"Non riesco a leggere «{percorso}»: {errore.strerror}. "
                "I percorsi sono relativi alla radice del repository.",
                file=sys.stderr,
            )
            return 2
        except KeyError as errore:
            print(f"«{percorso}»: variabile obbligatoria assente — {errore.args[0]}", file=sys.stderr)
            return 2

        problemi = verifica(documento, digest, grezzo, percorso=percorso)
        for problema in problemi:
            print(f"  ✗ {percorso}: {problema}", file=sys.stderr)
        totale += len(problemi)

    if totale:
        print(f"\n{totale} problemi negli stack.", file=sys.stderr)
        return 1
    quanti = len(argomenti.compose)
    print(f"Stack conformi: {quanti}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
