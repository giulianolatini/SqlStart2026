from check_citations import Fonte, parse_decisions, parse_sources, verifica


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


def test_segnala_una_fonte_citata_ma_inesistente():
    problemi = verifica({"ADR-0001": {"S-999"}}, {})
    assert any("S-999" in p and "ADR-0001" in p for p in problemi)


def test_segnala_una_fonte_orfana():
    fonti = {"S-001": Fonte("S-001", "https://esempio", set(), "s-001")}
    problemi = verifica({}, fonti)
    assert any("S-001" in p and "orfana" in p for p in problemi)


def test_segnala_un_collegamento_inverso_incompleto():
    fonti = {"S-001": Fonte("S-001", "https://esempio", {"ADR-0001"}, "s-001")}
    problemi = verifica({"ADR-0001": {"S-001"}, "ADR-0002": {"S-001"}}, fonti)
    assert any("ADR-0002" in p and "Usata da" in p for p in problemi)


def test_segnala_unancora_non_corrispondente():
    fonti = {"S-001": Fonte("S-001", "https://esempio", {"ADR-0001"}, "s-002")}
    problemi = verifica({"ADR-0001": {"S-001"}}, fonti)
    assert any("ancora" in p for p in problemi)


def test_nessun_problema_su_un_insieme_coerente():
    fonti = {"S-001": Fonte("S-001", "https://esempio", {"ADR-0001"}, "s-001")}
    assert verifica({"ADR-0001": {"S-001"}}, fonti) == []
