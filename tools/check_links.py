"""Verifica i collegamenti relativi e le ancore fra le pagine Markdown di docs/.

Un rimando rotto non rompe niente: la pagina si apre lo stesso, il collegamento
porta in cima al documento invece che al punto giusto, e nessuno se ne accorge
finché non è il pubblico a cliccarlo. È il tipo di errore che si moltiplica in
silenzio ogni volta che una sezione viene rinominata, ed è per questo che vale
la pena farlo controllare a una macchina.
"""

from __future__ import annotations

import pathlib
import re
from collections.abc import Iterable

ANCORA_ESPLICITA = re.compile(r'<a id="([^"]+)"></a>')
INTESTAZIONE = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)
# Un blocco recintato da ``` non è prosa: quello che c'è dentro non è né
# un'intestazione né un collegamento, anche quando ne ha la forma.
RECINTO = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
APICI = re.compile(r"`+[^`\n]*`+")
COLLEGAMENTO = re.compile(r"\]\(([^)\s]+)\)")
SCHEMA = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def _prosa(testo: str) -> str:
    return RECINTO.sub("", testo)


def _senza_codice(testo: str) -> str:
    """Prosa senza blocchi recintati e senza codice in linea.

    Serve per i collegamenti, non per i titoli: una pagina che spiega la
    sintassi scrive `[testo](url)` fra apici inversi, e quello è un esempio.
    Un titolo invece contiene spesso un nome di comando fra apici, e lì gli
    apici vanno tolti conservando la parola — se ne occupa `slug()`.
    """
    return APICI.sub("", _prosa(testo))


def slug(titolo: str) -> str:
    """Riproduce l'ancora che GitHub assegna a un'intestazione Markdown.

    Serve perché i rimandi interni si scrivono nella forma naturale
    `#1-prima-di-cominciare`, senza che nessuno abbia dichiarato quell'ancora:
    è GitHub a generarla dal testo del titolo. Senza questa regola il controllo
    segnalerebbe come rotti proprio i collegamenti scritti bene.
    """
    t = re.sub(r"^#{1,6}\s+", "", titolo.strip())
    t = ANCORA_ESPLICITA.sub("", t)                   # ancora dichiarata in linea
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)    # [testo](url) -> testo
    t = re.sub(r"[`*_~]", "", t)                      # enfasi e codice
    t = t.lower()
    # Via la punteggiatura, ma non le lettere: GitHub non traslittera, e
    # «perché» resta «perché».
    t = re.sub(r"[^\w\s-]", "", t, flags=re.UNICODE)
    # «Spaces are replaced by hyphens. Any other whitespace or punctuation
    # characters are removed» (S-053). Uno spazio, un trattino: nessuno li
    # accorpa, e in «S-001 — WiredTiger» il trattino lungo se ne va lasciando
    # due spazi, che diventano due trattini.
    t = re.sub(r"[^\S ]", "", t)
    return t.replace(" ", "-")


def ancore(testo: str) -> set[str]:
    """I punti di atterraggio di una pagina: quelli dichiarati e quelli generati."""
    prosa = _prosa(testo)
    esplicite = set(ANCORA_ESPLICITA.findall(_senza_codice(testo)))
    generate = {slug(riga) for riga in INTESTAZIONE.findall(prosa)}
    return (esplicite | generate) - {""}


def collegamenti(testo: str) -> list[tuple[str, str]]:
    """I collegamenti relativi, come coppie (percorso, ancora).

    Percorso vuoto significa «questa stessa pagina», ancora vuota significa
    «nessuna ancora». Gli indirizzi con uno schema — `https:`, `mailto:` — non
    sono affare di questo controllo: verificarli richiederebbe la rete, e il
    repository deve restare verificabile senza.
    """
    trovati: list[tuple[str, str]] = []
    for bersaglio in COLLEGAMENTO.findall(_senza_codice(testo)):
        if SCHEMA.match(bersaglio):
            continue
        percorso, _, ancora = bersaglio.partition("#")
        trovati.append((percorso, ancora))
    return trovati


def pagine(percorsi: Iterable[pathlib.Path]) -> list[pathlib.Path]:
    """Espande cartelle e file in un elenco ordinato di pagine, senza ripetizioni.

    Le ripetizioni contano: `docs` e `README.md` non si sovrappongono, ma
    passare due volte lo stesso albero farebbe contare due volte ogni problema,
    e un numero gonfiato è peggio di nessun numero.
    """
    trovate: dict[pathlib.Path, pathlib.Path] = {}
    for percorso in percorsi:
        candidate = sorted(percorso.rglob("*.md")) if percorso.is_dir() else [percorso]
        for pagina in candidate:
            trovate.setdefault(pagina.resolve(), pagina)
    return list(trovate.values())


def verifica(percorsi: Iterable[pathlib.Path]) -> list[str]:
    """Restituisce l'elenco dei problemi. Lista vuota significa coerenza."""
    problemi: list[str] = []
    conosciute: dict[pathlib.Path, set[str]] = {}

    def ancore_di(percorso: pathlib.Path) -> set[str]:
        if percorso not in conosciute:
            conosciute[percorso] = ancore(percorso.read_text(encoding="utf-8"))
        return conosciute[percorso]

    for pagina in pagine(percorsi):
        testo = pagina.read_text(encoding="utf-8")
        conosciute[pagina.resolve()] = ancore(testo)
        etichetta = pagina
        for percorso, ancora in collegamenti(testo):
            bersaglio = pagina if percorso == "" else (pagina.parent / percorso)
            scritto = f"{percorso}#{ancora}" if ancora else percorso
            if not bersaglio.is_file():
                problemi.append(f"{etichetta} → {scritto}: il file non esiste")
                continue
            if not ancora:
                continue
            # Un bersaglio che non sia Markdown non ha ancore da offrire, e
            # pretenderle sarebbe un falso allarme.
            if bersaglio.suffix != ".md":
                continue
            if ancora not in ancore_di(bersaglio.resolve()):
                problemi.append(
                    f"{etichetta} → {scritto}: l'ancora non esiste nel file di destinazione"
                )

    return problemi


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("percorsi", type=pathlib.Path, nargs="+")
    argomenti = parser.parse_args(argv)

    for percorso in argomenti.percorsi:
        if not percorso.exists():
            print(f"Non esiste: «{percorso}».", file=sys.stderr)
            print(
                "Attesi uno o più percorsi da esaminare — cartelle o singoli file "
                "Markdown, di norma `docs` e `README.md`. I percorsi sono relativi "
                "alla radice del repository.",
                file=sys.stderr,
            )
            return 2

    problemi = verifica(argomenti.percorsi)
    for problema in problemi:
        print(f"  ✗ {problema}", file=sys.stderr)
    if problemi:
        print(f"\n{len(problemi)} collegamenti rotti.", file=sys.stderr)
        return 1
    print("Collegamenti coerenti.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
