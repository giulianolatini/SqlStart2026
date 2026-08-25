"""Verifica il legame fra gli ADR di Decision.md e le voci di Sources.md."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

ADR_TITOLO = re.compile(r"^## (ADR-\d{4}) ", re.MULTILINE)
RIGA_FONTI = re.compile(r"^\*\*Fonti:\*\* (.+)$", re.MULTILINE)
RIFERIMENTO = re.compile(r"\[([SVC]-\d{3})\]")

FONTE_TITOLO = re.compile(r"^### ([SVC]-\d{3}) ", re.MULTILINE)
ANCORA = re.compile(r'<a id="([^"]+)"></a>')
RIGA_URL = re.compile(r"^- \*\*URL:\*\* (\S+)", re.MULTILINE)
RIGA_USATA_DA = re.compile(r"^- \*\*Usata da:\*\* (.+)$", re.MULTILINE)
ADR_RIFERITO = re.compile(r"ADR-\d{4}")


@dataclass(frozen=True)
class Fonte:
    identificatore: str
    url: str | None
    usata_da: frozenset[str] | set[str] = field(default_factory=set)
    ancora: str | None = None


def parse_decisions(testo: str) -> dict[str, set[str]]:
    """Associa a ogni ADR l'insieme delle fonti che cita."""
    risultato: dict[str, set[str]] = {}
    posizioni = [(m.group(1), m.start()) for m in ADR_TITOLO.finditer(testo)]
    for indice, (adr, inizio) in enumerate(posizioni):
        fine = posizioni[indice + 1][1] if indice + 1 < len(posizioni) else len(testo)
        blocco = testo[inizio:fine]
        riga = RIGA_FONTI.search(blocco)
        risultato[adr] = set(RIFERIMENTO.findall(riga.group(1))) if riga else set()
    return risultato


def parse_sources(testo: str) -> dict[str, Fonte]:
    """Associa a ogni identificatore di fonte i suoi metadati."""
    risultato: dict[str, Fonte] = {}
    posizioni = [(m.group(1), m.start()) for m in FONTE_TITOLO.finditer(testo)]
    for indice, (identificatore, inizio) in enumerate(posizioni):
        fine = posizioni[indice + 1][1] if indice + 1 < len(posizioni) else len(testo)
        blocco = testo[inizio:fine]
        # L'ancora precede il titolo: la si cerca nel testo che sta prima.
        ancore = ANCORA.findall(testo[:inizio])
        url = RIGA_URL.search(blocco)
        usata = RIGA_USATA_DA.search(blocco)
        risultato[identificatore] = Fonte(
            identificatore=identificatore,
            url=url.group(1) if url else None,
            usata_da=set(ADR_RIFERITO.findall(usata.group(1))) if usata else set(),
            ancora=ancore[-1] if ancore else None,
        )
    return risultato


def verifica(decisioni: dict[str, set[str]], fonti: dict[str, Fonte]) -> list[str]:
    """Restituisce l'elenco dei problemi. Lista vuota significa coerenza."""
    problemi: list[str] = []

    for adr, riferimenti in sorted(decisioni.items()):
        for riferimento in sorted(riferimenti):
            if riferimento not in fonti:
                problemi.append(
                    f"{adr} cita {riferimento}, che non esiste in Sources.md"
                )

    citata_da: dict[str, set[str]] = {}
    for adr, riferimenti in decisioni.items():
        for riferimento in riferimenti:
            citata_da.setdefault(riferimento, set()).add(adr)

    for identificatore, fonte in sorted(fonti.items()):
        effettivi = citata_da.get(identificatore, set())
        if not effettivi:
            problemi.append(f"{identificatore} è orfana: nessun ADR la cita")
            continue
        if fonte.usata_da != effettivi:
            mancanti = sorted(effettivi - set(fonte.usata_da))
            eccedenti = sorted(set(fonte.usata_da) - effettivi)
            problemi.append(
                f"{identificatore}: «Usata da» non corrisponde — "
                f"mancano {mancanti or '—'}, sono di troppo {eccedenti or '—'}"
            )
        atteso = identificatore.lower()
        if fonte.ancora != atteso:
            problemi.append(
                f"{identificatore}: ancora «{fonte.ancora}», attesa «{atteso}»"
            )

    return problemi


def main(argv: list[str] | None = None) -> int:
    import argparse
    import pathlib
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decision", type=pathlib.Path)
    parser.add_argument("sources", type=pathlib.Path)
    argomenti = parser.parse_args(argv)

    testi = []
    for percorso in (argomenti.decision, argomenti.sources):
        try:
            testi.append(percorso.read_text(encoding="utf-8"))
        except OSError as errore:
            # Chi clona il repository sbaglia il percorso prima di sbagliare
            # le citazioni: un traceback qui non aiuterebbe nessuno.
            print(f"Non riesco a leggere «{percorso}»: {errore.strerror}.", file=sys.stderr)
            print(
                "Attesi due argomenti, nell'ordine: docs/Decision.md e docs/Sources.md. "
                "I percorsi sono relativi alla radice del repository.",
                file=sys.stderr,
            )
            return 2

    problemi = verifica(parse_decisions(testi[0]), parse_sources(testi[1]))
    for problema in problemi:
        print(f"  ✗ {problema}", file=sys.stderr)
    if problemi:
        print(f"\n{len(problemi)} problemi di citazione.", file=sys.stderr)
        return 1
    print("Citazioni coerenti.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
