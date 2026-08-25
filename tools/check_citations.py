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
