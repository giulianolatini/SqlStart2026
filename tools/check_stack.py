"""Verifica che un file Compose del lab rispetti le decisioni prese negli ADR."""

from __future__ import annotations

import re

IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

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


def avvia_mongod(comando: object) -> bool:
    """Vero se il servizio avvia un `mongod`.

    Il bersaglio della regola sulla cache sono i processi che hanno storage. Un
    `mongos` instrada e basta: pretendere una cache da lui sarebbe una regola che
    sbaglia bersaglio.
    """
    if isinstance(comando, str):
        pezzi = comando.split()
    elif isinstance(comando, list):
        pezzi = [str(pezzo) for pezzo in comando]
    else:
        return False
    return bool(pezzi) and pezzi[0].rsplit("/", 1)[-1] == "mongod"


def verifica(
    documento: dict, digest_noti: set[str], grezzo: dict | None = None
) -> list[str]:
    """Restituisce l'elenco dei problemi. Lista vuota significa conformità.

    `documento` è il file dopo l'interpolazione, `grezzo` prima. Quasi tutte le
    regole guardano il primo, perché giudicano lo stack che si avvia. Quella sul
    `pull_policy` guarda il secondo, perché giudica ciò che il file promette a
    chi lo apre. Se `grezzo` manca si assume che i due coincidano.
    """
    problemi: list[str] = []
    servizi_grezzi = (grezzo or documento).get("services", {})

    if "version" in documento:
        problemi.append(
            "la chiave «version» al livello superiore è obsoleta nella Compose "
            "Specification: va tolta, non aggiornata"
        )

    for nome, servizio in sorted(documento.get("services", {}).items()):
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
            problemi.append(
                f"{nome}: l'immagine «{immagine}» non è pinnata per digest. Un tag può "
                "cambiare contenuto sotto lo stesso nome; il digest no (ADR-0009, "
                "ADR-0028)"
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
        if condizione == "service_healthy" and "healthcheck" not in servizi.get(
            atteso, {}
        ):
            problemi.append(
                f"{nome} attende «{atteso}» in stato service_healthy, ma «{atteso}» "
                "non ha un «healthcheck»: la condizione non diventerà mai vera "
                "(ADR-0023)"
            )
    return problemi


def main(argv: list[str] | None = None) -> int:
    import argparse
    import pathlib
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ambiente",
        type=pathlib.Path,
        default=pathlib.Path("tools/images.env"),
        help="il file che dichiara le immagini pinnate (default: tools/images.env)",
    )
    parser.add_argument("compose", type=pathlib.Path, nargs="+")
    argomenti = parser.parse_args(argv)

    try:
        ambiente = leggi_ambiente(argomenti.ambiente)
    except OSError as errore:
        print(
            f"Non riesco a leggere «{argomenti.ambiente}»: {errore.strerror}. "
            "Il file si genera con `make images-pull`.",
            file=sys.stderr,
        )
        return 2

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

        problemi = verifica(documento, digest, grezzo)
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
