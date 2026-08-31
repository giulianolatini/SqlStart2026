from check_citations import (
    ADR_TITOLO,
    FONTE_TITOLO,
    Fonte,
    main,
    parse_decisions,
    parse_sources,
    ripetuti,
    verifica,
)


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


def test_segnala_un_percorso_inesistente_senza_traceback(tmp_path, capsys):
    codice = main([str(tmp_path / "assente.md"), str(tmp_path / "nemmeno.md")])
    catturato = capsys.readouterr()
    assert codice == 2
    assert "assente.md" in catturato.err
    assert "Traceback" not in catturato.err


def test_distingue_un_adr_a_cui_manca_la_riga_delle_fonti():
    # Non è la stessa cosa di «nessuna (decisione organizzativa)»: quella è una
    # scelta dichiarata, questa è una svista. Il controllo deve vedere solo la seconda.
    testo = """
## ADR-0099 — Una decisione a cui è caduta la riga delle fonti
**Data:** 2026-08-28 · **Stato:** Accettata
"""
    assert parse_decisions(testo) == {"ADR-0099": None}


def test_segnala_un_adr_a_cui_manca_la_riga_delle_fonti():
    problemi = verifica({"ADR-0099": None}, {})
    assert any("ADR-0099" in p and "Fonti" in p for p in problemi)


def test_una_fonte_e_immutabile_e_utilizzabile_come_chiave():
    fonte = Fonte("S-001", "https://esempio", {"ADR-0001"}, "s-001")
    assert isinstance(fonte.usata_da, frozenset)
    assert hash(fonte) == hash(Fonte("S-001", "https://esempio", {"ADR-0001"}, "s-001"))


def test_ripetuti_trova_un_identificatore_dichiarato_due_volte():
    # Il caso reale: un numero riusato per sbaglio in una PR che ne aggiunge
    # tre in fondo al file. Nessuna fonte resta orfana, nessun collegamento
    # inverso salta, e il controllo tace su un ADR che non esiste più.
    testo = "## ADR-0001 — La prima\n\n## ADR-0001 — La seconda\n\n## ADR-0002 — Un'altra\n"
    assert ripetuti(ADR_TITOLO, testo) == ["ADR-0001"]


def test_ripetuti_tace_su_identificatori_distinti():
    testo = "### S-001 — Una\n\n### S-002 — Due\n"
    assert ripetuti(FONTE_TITOLO, testo) == []


def scrivi_coppia(cartella, decisione, fonti):
    (cartella / "Decision.md").write_text(decisione, encoding="utf-8")
    (cartella / "Sources.md").write_text(fonti, encoding="utf-8")
    return [str(cartella / "Decision.md"), str(cartella / "Sources.md")]


def test_main_segnala_un_adr_dichiarato_due_volte(tmp_path, capsys):
    argomenti = scrivi_coppia(
        tmp_path,
        '<a id="adr-0001"></a>\n## ADR-0001 — La prima\n\n'
        "**Fonti:** [S-001](Sources.md#s-001)\n\n"
        '<a id="adr-0001"></a>\n## ADR-0001 — La seconda, con lo stesso numero\n\n'
        "**Fonti:** [S-001](Sources.md#s-001)\n",
        '<a id="s-001"></a>\n### S-001 — La fonte\n\n'
        "- **URL:** https://esempio.it/1\n- **Usata da:** ADR-0001\n",
    )
    codice = main(argomenti)
    assert codice == 1
    assert "ADR-0001" in capsys.readouterr().err


def test_main_segnala_una_fonte_dichiarata_due_volte(tmp_path, capsys):
    argomenti = scrivi_coppia(
        tmp_path,
        '<a id="adr-0001"></a>\n## ADR-0001 — Una decisione\n\n'
        "**Fonti:** [S-001](Sources.md#s-001)\n",
        '<a id="s-001"></a>\n### S-001 — La fonte giusta\n\n'
        "- **URL:** https://esempio.it/giusta\n- **Usata da:** ADR-0001\n\n"
        '<a id="s-001"></a>\n### S-001 — Una fonte diversa con lo stesso numero\n\n'
        "- **URL:** https://esempio.it/sbagliata\n- **Usata da:** ADR-0001\n",
    )
    codice = main(argomenti)
    assert codice == 1
    assert "S-001" in capsys.readouterr().err
