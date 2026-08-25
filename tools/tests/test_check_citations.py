from check_citations import parse_decisions


def test_estrae_un_adr_con_le_sue_fonti():
    testo = """
## ADR-0004 — Limiti di risorsa espliciti
**Data:** 2026-08-24 · **Stato:** Accettata
**Fonti:** [S-001](Sources.md#s-001), [S-003](Sources.md#s-003)
"""
    assert parse_decisions(testo) == {"ADR-0004": {"S-001", "S-003"}}


def test_riconosce_un_adr_senza_fonti_dichiarato_organizzativo():
    testo = """
## ADR-0015 — Runbook come documento unico
**Fonti:** nessuna (decisione organizzativa)
"""
    assert parse_decisions(testo) == {"ADR-0015": set()}
