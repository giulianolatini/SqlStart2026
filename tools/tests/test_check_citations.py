from check_citations import Fonte, parse_decisions, parse_sources


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


def test_estrae_una_fonte_con_il_collegamento_inverso():
    testo = """
<a id="s-001"></a>
### S-001 — WiredTiger Storage Engine

- **URL:** https://www.mongodb.com/docs/manual/core/wiredtiger/
- **Usata da:** ADR-0004, ADR-0008
"""
    assert parse_sources(testo) == {
        "S-001": Fonte(
            identificatore="S-001",
            url="https://www.mongodb.com/docs/manual/core/wiredtiger/",
            usata_da={"ADR-0004", "ADR-0008"},
            ancora="s-001",
        )
    }
