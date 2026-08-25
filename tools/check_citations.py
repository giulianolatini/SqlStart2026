"""Verifica il legame fra gli ADR di Decision.md e le voci di Sources.md."""

from __future__ import annotations

import re

ADR_TITOLO = re.compile(r"^## (ADR-\d{4}) ", re.MULTILINE)
RIGA_FONTI = re.compile(r"^\*\*Fonti:\*\* (.+)$", re.MULTILINE)
RIFERIMENTO = re.compile(r"\[([SVC]-\d{3})\]")


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
