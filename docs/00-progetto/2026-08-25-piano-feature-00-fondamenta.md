# Piano di implementazione — `feature/00-fondamenta`

> **Per chi esegue il piano:** i passi usano caselle `- [ ]` da spuntare. Ogni task
> termina con un deliverable verificabile e un commit. Leggere anche la specifica
> collegata: questo piano attua decisioni prese lì, non le rimette in discussione.

**Obiettivo:** dotare il repository di igiene, impianto documentale verificabile e
strumenti di palco, e sondare il punto di massima incertezza del progetto — la catena di
inizializzazione dello sharded cluster — prima di aprire le altre branch.

**Architettura:** il branch non produce stack Docker né applicazione. Produce le
fondamenta su cui le quattro feature successive appoggiano: un `Sources.md` popolato da
verifiche su fonte primaria, un `Decision.md` con i diciassette ADR già presi, uno script
che rende quel legame **eseguibile** invece che dichiarato, e due script di palco
(`pull-images.sh`, `preflight.sh`) che rendono possibile il vincolo offline. Lo spike
sharded è codice usa-e-getta: nel repository entra solo il suo verbale.

**Stack tecnico:** Markdown, Bash (`set -euo pipefail`), Python 3.13+ con `pytest` per gli
strumenti di repository, GNU Make, Docker Compose v5.

**Specifica:** [`docs/00-progetto/2026-08-24-design.md`](2026-08-24-design.md) — approvata
dal Product Owner il 2026-08-25.

---

## Vincoli globali

Valgono per ogni task, senza doverli ripetere.

- **Lingua:** tutto il materiale prodotto è in **italiano**, compresi commenti nel codice,
  messaggi degli script e messaggi di commit.
- **Documentazione:** tutta sotto `docs/`. In radice esiste **solo** `README.md`.
- **Citazioni:** nessuna affermazione tecnica entra in `docs/` senza un riferimento
  `[S-NNN]`, `[V-NNN]` o `[C-NNN]` verso `Sources.md`. La verifica su fonte primaria
  **precede** la scrittura.
- **Offline:** nessun artefatto destinato al palco può richiedere rete. Gli script
  distinguono la fase di preparazione (rete ammessa) da quella di esecuzione (rete
  vietata).
- **MongoDB 8.0**, immagine `mongo:8.0` pinnata **per digest**.
- **Compose:** Specification corrente, **senza** chiave `version:` (obsoleta). Sintassi
  breve `mem_limit` / `cpus`.
- **Nomi:** nessun nome di strumento interno nei percorsi o nei contenuti pubblicati. Il
  repository è materiale didattico.
- **Commit:** stile convenzionale (`chore:`, `docs:`, `feat:`, `test:`), corpo in
  italiano, chiusi da `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- **Python:** SOLID e TDD Red → Green → Refactor. Funzioni pure separate dall'I/O;
  nessuna stampa fuori dal punto d'ingresso.
- **Bash:** `#!/usr/bin/env bash`, `set -euo pipefail`, nessun percorso assoluto della
  macchina del relatore, tutto relativo alla radice del repository.

---

## Mappa dei file

Cosa esiste alla fine del branch, e di chi è la responsabilità.

| File | Responsabilità |
|---|---|
| `.gitignore` | escludere artefatti di runtime, spike, filmati, virtualenv |
| `.editorconfig` | uniformare fine riga e indentazione |
| `LICENSE` | licenza del materiale didattico — **già presente (GPL-3.0), non toccare** |
| `README.md` | abstract del progetto e indice di primo livello |
| `Makefile` | unico punto d'ingresso; qui solo i target di fondamenta |
| `docs/README.md` | indice della documentazione |
| `docs/Sources.md` | fonti numerate, con collegamento inverso agli ADR |
| `docs/citazioni-riportare-slide.md` | sede unica delle citazioni letterali destinate alle slide |
| `docs/00-progetto/limiti-noti.md` | confini dichiarati: dove il lab semplifica e dove la documentazione non copre |
| `docs/Decision.md` | ADR-0001…ADR-0025 in ordine cronologico |
| `docs/registro-operativo-sviluppo.md` | diario cronologico di sessione |
| `docs/00-progetto/2026-08-25-spike-sharded.md` | verbale dello spike, con il Compose funzionante |
| `docs/06-sviluppo/gestione-risorse-compose.md` | `mem_limit`/`cpus`, cache WiredTiger, cgroup |
| `tools/pyproject.toml` | progetto Python isolato per gli strumenti di repository |
| `tools/check_citations.py` | verifica eseguibile del legame Decision ↔ Sources |
| `tools/tests/test_check_citations.py` | suite del precedente |
| `tools/images.env` | immagini pinnate per digest — generato e versionato |
| `tools/pull-images.sh` | scarica e pinna (con rete) · verifica presenza (offline) |
| `tools/preflight.sh` | controlli della mattina del talk |

Non appartiene a questo branch: `docker/`, `app/`, `.env.example`,
`tools/reset-demo.sh`, `tools/record-demo.sh`, `tools/seed-data.py`. Nascono con lo stack o
l'applicazione che devono servire. In particolare `.env.example`, che la §4 della specifica
colloca in radice, resta vuoto di contenuto reale finché non esiste uno stack: un file di
esempio senza variabili da esemplificare insegna solo a ignorarlo.

**Due divergenze dalla specifica, dichiarate qui invece che scoperte durante l'esecuzione:**

| Specifica | Piano | Ragione |
|---|---|---|
| `tools/check-citations.py` | `tools/check_citations.py` | un modulo con il trattino non è importabile in Python, e i test devono importarlo |
| `.env.example` in radice | rinviato a `feature/01` | non ha contenuto prima del primo stack |

---

## Task 1 — Igiene del repository

**File:**
- Crea: `.gitignore`, `.editorconfig`
- Lascia invariato: `LICENSE` (GPL-3.0, già nel repository)

**Interfacce:**
- Produce: la cartella ignorata `spike/`, usata dal Task 10; il pattern `*.mp4`, che attua
  ADR-0016.

- [ ] **Passo 1: scrivere `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Strumenti locali di sviluppo (non fanno parte del materiale didattico)
.tokensave/
.rtk/
.serena/
.claude/worktrees/

# Spike: codice usa-e-getta, nel repository entra solo il verbale
spike/

# Registrazioni: gli MP4 stanno su YouTube e in locale, mai in git (ADR-0016)
*.mp4
*.mov
docs/05-talk/registrazioni/locale/

# Ambiente
.env
!.env.example
!tools/images.env

# Sistema
.DS_Store
```

- [ ] **Passo 2: scrivere `.editorconfig`**

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 2

[*.py]
indent_size = 4

[*.md]
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
```

- [ ] **Passo 3: lasciare `LICENSE` com'è**

Il file **esiste già**: GPL-3.0, scelta alla creazione del repository. Non va toccato.
La licenza è una prerogativa del titolare del copyright, non una scelta di questo piano.

La domanda era stata posta al Product Owner: il materiale è pensato per essere **copiato**
dal pubblico nei propri progetti, e la GPL-3.0 è copyleft — chi riusa i file Compose o
l'applicazione in un lavoro proprio eredita l'obbligo di rilasciare con la stessa licenza.
**Risposta del 2026-08-25: resta GPL-3.0.** Il `README.md` (Task 6) lo dichiara
esplicitamente. Questione chiusa.

- [ ] **Passo 4: verificare che l'esclusione funzioni**

Creare `spike/prova.yml`, eseguire `git status --porcelain` e verificare che **non**
compaia. Poi rimuovere la cartella.

- [ ] **Passo 5: commit**

Messaggio: `chore: igiene del repository — gitignore ed editorconfig`

---

## Task 2 — `docs/Sources.md`: verifica delle fonti primarie

Questo task **consulta davvero** le fonti. È il debito dichiarato in §8.1 della specifica:
finora le decisioni poggiano su conoscenza pregressa, e la conoscenza pregressa non regge
a una domanda dal pubblico.

**File:**
- Crea: `docs/Sources.md`

**Interfacce:**
- Produce: gli identificatori `S-001`…`S-021` e `V-001`…`V-002`, e il formato di voce che
  `tools/check_citations.py` (Task 3) analizza e che il Task 4 cita dagli ADR.

- [ ] **Passo 1: consultare le fonti una per una e annotare cosa dicono davvero**

Per ciascuna: aprire l'URL, individuare il passaggio pertinente, annotare data di
consultazione e versione documentata. Se una fonte **non conferma** l'assunzione della
specifica, non riscrivere la fonte: annotare la divergenza e portarla al Product Owner
prima di procedere.

| ID | URL | Cosa deve confermare |
|---|---|---|
| S-001 | `https://www.mongodb.com/docs/manual/core/wiredtiger/` | formula della cache predefinita e lettura del limite cgroup |
| S-002 | `https://www.mongodb.com/docs/manual/reference/program/mongod/` | opzione `--wiredTigerCacheSizeGB`, valori ammessi |
| S-003 | `https://docs.docker.com/reference/compose-file/services/` | `mem_limit`, `cpus`, `healthcheck`, `depends_on` |
| S-004 | `https://docs.docker.com/reference/compose-file/deploy/` | `deploy.resources.limits` e il suo ambito di applicazione |
| S-005 | `https://www.mongodb.com/docs/manual/tutorial/deploy-replica-set-with-keyfile-access-control/` | permessi richiesti al keyfile, autenticazione interna obbligatoria |
| S-006 | `https://www.mongodb.com/docs/manual/core/localhost-exception/` | perimetro esatto dell'eccezione localhost |
| S-007 | `https://www.mongodb.com/docs/manual/reference/connection-string/` | `directConnection`, scoperta della topologia |
| S-008 | `https://www.mongodb.com/docs/manual/core/sharded-cluster-components/` | componenti obbligatorie, config server come replica set |
| S-009 | `https://hub.docker.com/_/mongo` | variabili `MONGO_INITDB_*`, fase temporanea dell'entrypoint |
| S-010 | `https://pymongo.readthedocs.io/en/stable/api/pymongo/monitoring.html` | listener SDAM disponibili e loro eventi |
| S-011 | `https://www.mongodb.com/docs/database-tools/mongodump/` | `--oplog`, `--readPreference`, consistenza del dump |
| S-012 | `https://docs.docker.com/reference/compose-file/services/#depends_on` | `service_healthy`, `service_completed_successfully` |
| S-013 | `https://testcontainers-python.readthedocs.io/` | supporto MongoDB, classe `DockerCompose` |
| S-014 | `https://www.mongodb.com/it-it/resources/products/fundamentals/mongodb-cluster-setup` | fonte indicata dal Product Owner |
| S-015 | `https://docs.docker.com/compose/how-tos/profiles/` | semantica dei profili, servizi senza profilo |
| S-016 | `https://docs.docker.com/reference/compose-file/` | Compose Specification, obsolescenza di `version:` |
| S-017 | `https://docs.docker.com/compose/how-tos/project-name/` | isolamento fra progetti Compose |
| S-018 | `https://rich.readthedocs.io/en/stable/live.html` | vincoli di `Live` su refresh e thread |
| S-019 | `https://docs.docker.com/reference/cli/docker/compose/up/` | quando `up` esegue un pull implicito |
| S-020 | `https://www.mongodb.com/docs/manual/tutorial/change-hostnames-in-a-replica-set/` | i nomi host sono memorizzati nella configurazione |
| S-021 | `https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github` | costo dei binari in git |

- [ ] **Passo 2: scrivere intestazione e legenda di `docs/Sources.md`**

```markdown
# Fonti

Registro delle fonti consultate. Ogni affermazione tecnica in `docs/` cita almeno una voce
di questo file; ogni voce di questo file è citata da almeno un ADR di
[`Decision.md`](Decision.md). Il vincolo è verificato da `tools/check_citations.py`.

| Prefisso | Tipo |
|---|---|
| `S-NNN` | fonte ufficiale — URL, editore, versione documentata, data di consultazione |
| `V-NNN` | verifica empirica su questo lab — comando eseguito, output osservato, data |
| `C-NNN` | fonte comunitaria — indizio, mai unica base di una decisione |

---

## Fonti ufficiali
```

- [ ] **Passo 3: scrivere una voce per fonte, nel formato esatto**

L'ancora HTML esplicita è obbligatoria: l'ancora che GitHub genera da un titolo contenente
un trattino lungo non è prevedibile, e i collegamenti da `Decision.md` devono funzionare.

```markdown
<a id="s-001"></a>
### S-001 — MongoDB Manual: WiredTiger Storage Engine

- **URL:** https://www.mongodb.com/docs/manual/core/wiredtiger/
- **Editore:** MongoDB, Inc.
- **Versione documentata:** MongoDB 8.0
- **Consultata:** 2026-08-25
- **Cosa afferma:** [una o due righe in italiano, con la citazione pertinente]
- **Usata da:** ADR-0004
```

- [ ] **Passo 4: scrivere le due verifiche empiriche già in nostro possesso**

```markdown
<a id="v-001"></a>
### V-001 — Apple `container` non espone un subcomando `compose`

- **Comando:** `container --help` · `container compose --help`
- **Ambiente:** macOS 26.6.2, Apple `container` 1.2.2
- **Esito:** nessun subcomando `compose`; il secondo comando termina con errore.
- **Data:** 2026-08-24
- **Usata da:** ADR-0002

<a id="v-002"></a>
### V-002 — Inventario dell'ambiente di sviluppo e di palco

- **Comandi:** `docker version` · `docker info` · `sysctl hw.memsize`
- **Esito:** host macOS 26.6.2 arm64, 8 CPU, 16 GiB; VM Docker 7,65 GiB e 8 CPU;
  Docker 29.7.2 con Compose v5.4.0, contesto `desktop-linux`.
- **Data:** 2026-08-24
- **Usata da:** ADR-0008, ADR-0009, ADR-0010
```

- [ ] **Passo 5: commit**

Messaggio: `docs: registro delle fonti verificate su documentazione primaria`

---

## Task 3 — `tools/check_citations.py` in TDD

Il legame Decision ↔ Sources è una promessa fatta al pubblico. Una promessa non verificata
decade in silenzio: entro settembre `Sources.md` avrà voci orfane e `Decision.md`
riferimenti morti. Questo script trasforma la promessa in un controllo che fallisce.

**File:**
- Crea: `tools/pyproject.toml`, `tools/check_citations.py`, `tools/tests/test_check_citations.py`

**Interfacce:**
- Consuma: il formato di voce definito nel Task 2.
- Produce: `python check_citations.py <decision.md> <sources.md>` con uscita `0` se tutto
  è coerente, `1` altrimenti, e un elenco di problemi su stderr. Il target `make
  docs-check` del Task 7 lo invoca.

**Regole verificate** (decise ora, così i test le fissano):

1. Ogni riferimento citato da un ADR esiste come voce in `Sources.md`.
2. Ogni voce di `Sources.md` è citata da almeno un ADR — nessuna fonte orfana.
3. Il collegamento inverso `Usata da:` di ogni fonte elenca **esattamente** gli ADR che la
   citano: né più né meno.
4. Gli ADR privi di fonte sono ammessi **solo** se dichiarano `**Fonti:** nessuna
   (decisione organizzativa)`. Il silenzio non è ammesso: la dimenticanza e la scelta
   devono essere distinguibili.
5. Ogni ancora `<a id="s-001"></a>` corrisponde all'identificatore del titolo che segue.

- [ ] **Passo 1: creare il progetto Python degli strumenti**

`tools/pyproject.toml`:

```toml
[project]
name = "sqlstart2026-tools"
version = "0.1.0"
description = "Strumenti di repository per il lab MongoDB di SqlStart 2026"
requires-python = ">=3.13"
dependencies = []

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Passo 2: scrivere il primo test — analisi degli ADR**

`tools/tests/test_check_citations.py`:

```python
from check_citations import parse_decisions


def test_estrae_un_adr_con_le_sue_fonti():
    testo = """
## ADR-0004 — Limiti di risorsa espliciti
**Data:** 2026-08-24 · **Stato:** Accettata
**Fonti:** [S-001](../Sources.md#s-001), [S-003](../Sources.md#s-003)
"""
    assert parse_decisions(testo) == {"ADR-0004": {"S-001", "S-003"}}


def test_riconosce_un_adr_senza_fonti_dichiarato_organizzativo():
    testo = """
## ADR-0015 — Runbook come documento unico
**Fonti:** nessuna (decisione organizzativa)
"""
    assert parse_decisions(testo) == {"ADR-0015": set()}
```

- [ ] **Passo 3: eseguire e verificare il fallimento**

Comando: `uv run --project tools pytest -v`
Atteso: FAIL con `ModuleNotFoundError: No module named 'check_citations'`.

- [ ] **Passo 4: implementazione minima di `parse_decisions`**

`tools/check_citations.py`:

```python
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
```

- [ ] **Passo 5: eseguire e verificare il passaggio**

Comando: `uv run --project tools pytest -v` — Atteso: 2 PASS.

- [ ] **Passo 6: commit**

Messaggio: `test: analisi degli ADR in check_citations`

- [ ] **Passo 7: test dell'analisi delle fonti**

```python
from check_citations import Fonte, parse_sources


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
```

- [ ] **Passo 8: eseguire e verificare il fallimento** — Atteso: `ImportError` su `Fonte`.

- [ ] **Passo 9: implementare `Fonte` e `parse_sources`**

```python
from dataclasses import dataclass, field

FONTE_TITOLO = re.compile(r"^### ([SVC]-\d{3}) ", re.MULTILINE)
ANCORA = re.compile(r'<a id="([^"]+)"></a>')
RIGA_URL = re.compile(r"^- \*\*URL:\*\* (\S+)$", re.MULTILINE)
RIGA_USATA_DA = re.compile(r"^- \*\*Usata da:\*\* (.+)$", re.MULTILINE)
ADR_RIFERITO = re.compile(r"ADR-\d{4}")


@dataclass(frozen=True)
class Fonte:
    identificatore: str
    url: str | None
    usata_da: frozenset[str] | set[str] = field(default_factory=set)
    ancora: str | None = None


def parse_sources(testo: str) -> dict[str, Fonte]:
    """Associa a ogni identificatore di fonte i suoi metadati."""
    risultato: dict[str, Fonte] = {}
    posizioni = [(m.group(1), m.start()) for m in FONTE_TITOLO.finditer(testo)]
    for indice, (identificatore, inizio) in enumerate(posizioni):
        fine = posizioni[indice + 1][1] if indice + 1 < len(posizioni) else len(testo)
        blocco = testo[inizio:fine]
        # L'ancora precede il titolo: la si cerca nel testo che sta prima.
        precedente = testo[:inizio]
        ancore = ANCORA.findall(precedente)
        url = RIGA_URL.search(blocco)
        usata = RIGA_USATA_DA.search(blocco)
        risultato[identificatore] = Fonte(
            identificatore=identificatore,
            url=url.group(1) if url else None,
            usata_da=set(ADR_RIFERITO.findall(usata.group(1))) if usata else set(),
            ancora=ancore[-1] if ancore else None,
        )
    return risultato
```

- [ ] **Passo 10: eseguire, verificare il passaggio, commit**

Messaggio: `test: analisi delle fonti in check_citations`

- [ ] **Passo 11: test del confronto incrociato — una regola per test**

```python
from check_citations import Fonte, verifica


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
```

- [ ] **Passo 12: eseguire e verificare il fallimento** — Atteso: `ImportError` su `verifica`.

- [ ] **Passo 13: implementare `verifica`**

Funzione pura: riceve i due dizionari, restituisce una lista di stringhe. Nessun I/O,
nessuna stampa — è ciò che la rende testabile in millisecondi.

```python
def verifica(
    decisioni: dict[str, set[str]], fonti: dict[str, Fonte]
) -> list[str]:
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
```

- [ ] **Passo 14: eseguire, verificare 5 PASS, commit**

Messaggio: `feat: confronto incrociato fra ADR e fonti`

- [ ] **Passo 15: punto d'ingresso da riga di comando**

```python
def main(argv: list[str] | None = None) -> int:
    import argparse
    import pathlib
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decision", type=pathlib.Path)
    parser.add_argument("sources", type=pathlib.Path)
    argomenti = parser.parse_args(argv)

    problemi = verifica(
        parse_decisions(argomenti.decision.read_text(encoding="utf-8")),
        parse_sources(argomenti.sources.read_text(encoding="utf-8")),
    )
    for problema in problemi:
        print(f"  ✗ {problema}", file=sys.stderr)
    if problemi:
        print(f"\n{len(problemi)} problemi di citazione.", file=sys.stderr)
        return 1
    print("Citazioni coerenti.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Nota: `--check-urls` **non** viene implementato. Richiederebbe rete e finirebbe per
fallire proprio la mattina del talk, quando la rete non c'è. La raggiungibilità degli URL
si controlla a mano quando si aggiunge una fonte.

- [ ] **Passo 16: verifica manuale sui file reali**

Comando: `uv run --project tools python tools/check_citations.py docs/Decision.md docs/Sources.md`
Atteso in questo momento: fallisce, perché `Decision.md` non esiste ancora. È il test rosso
del Task 4.

- [ ] **Passo 17: commit**

Messaggio: `feat: interfaccia a riga di comando di check_citations`

---

## Task 4 — `docs/Decision.md`: gli ADR

**File:**
- Crea: `docs/Decision.md`

**Interfacce:**
- Consuma: gli identificatori di `Sources.md` (Task 2) e le regole di
  `check_citations.py` (Task 3).
- Produce: gli ADR-0001…ADR-0024. Il Task 10 aggiunge ADR-0025.

### Esito del Task 2: cosa cambia rispetto ai diciassette ADR iniziali

La verifica delle fonti ha modificato il contenuto di questo task. Il Product Owner ha
approvato quanto segue il **2026-08-25**; il campo `Usata da` di ogni voce di
`Sources.md` è già allineato a questa lista, e `check_citations.py` fallirà se il Task 4
se ne discosta.

**Decisioni riformulate nella motivazione, non nel merito:**

| ADR | Cosa cambia |
|---|---|
| ADR-0004 | la cache si imposta a mano non perché mongod legga il cgroup, ma perché la documentazione dice che *potrebbe non leggerlo* e prescrive di impostarla. Il valore passa da `0.25` a un valore ≥ `0.256 GB`, fissato dalla verifica empirica del Task 10 |
| ADR-0009 | la garanzia offline non poggia sul digest ma su `pull_policy`: il digest stabilisce *quale* immagine, non *se* si va in rete |
| ADR-0013 | cadono entrambe le gambe della motivazione originale — che `deploy` sia ignorato fuori da Swarm non è documentato, e la sintassi breve non è un'alternativa a `deploy` ma deve restarvi coerente. La decisione resta; la nuova motivazione è leggibilità, portabilità verso Podman ed efficacia dimostrata con `docker inspect` |

**Decisione revocata:**

| ADR | Stato |
|---|---|
| ADR-0011 | **Superata da ADR-0020.** `MongoDbContainer` avvia solo istanze standalone; la classe `DockerCompose` non è documentata |

**Nuove decisioni da registrare:**

| ADR | Decisione | Fonti |
|---|---|---|
| ADR-0018 | `pull_policy: ${PULL_POLICY:-missing}` nei file Compose, `PULL_POLICY=never` sul profilo di palco | S-003, S-019 |
| ADR-0019 | i listener del driver depositano un evento in una `queue.Queue` e ritornano subito; il ciclo di disegno legge dalla coda sul thread principale | S-010, S-018 |
| ADR-0020 | niente `testcontainers`: i test di integrazione girano contro gli stack Compose del repository | S-013 |
| ADR-0021 | nomi host risolvibili ovunque, mai indirizzi IP: dalla 5.0 i nodi con solo IP non superano la validazione all'avvio | S-020 |
| ADR-0022 | il backup a caldo si dimostra sul replica set, mai sullo sharded cluster | S-011 |
| ADR-0023 | l'ordine di avvio si esprime con le condizioni di `depends_on` e gli healthcheck, mai con attese a tempo | S-012 |
| ADR-0024 | gerarchia delle fonti: il materiale divulgativo di un produttore non è documentazione normativa | S-014 |

**Senza fonte, per scelta dichiarata:** ADR-0015 e ADR-0017 sono decisioni organizzative e
devono riportare `**Fonti:** nessuna (decisione organizzativa)` — la regola 4 di
`check_citations.py` non ammette il silenzio.

- [ ] **Passo 1: intestazione**

```markdown
# Registro delle decisioni architetturali

Le decisioni sono in ordine cronologico e non vengono riscritte: una decisione superata
resta, con lo stato aggiornato e il rimando a quella che la sostituisce. Ogni ADR cita le
fonti di [`Sources.md`](Sources.md) che lo sostengono; il legame è verificato da
`tools/check_citations.py`.
```

- [ ] **Passo 2: scrivere gli ADR nel formato esatto**

Una sezione per ADR, nell'ordine numerico. Contenuto e motivazioni si travasano dalla §3
della specifica, espansi nei cinque campi. Esempio completo, da usare come modello:

```markdown
## ADR-0004 — Limiti di memoria e CPU espliciti per ogni servizio

**Data:** 2026-08-24 · **Stato:** Accettata

**Contesto:** dalla versione 5.0 mongod dimensiona la cache WiredTiger leggendo il limite
del proprio cgroup, non la memoria della macchina fisica. In un container senza limite il
cgroup coincide con la VM Docker: ogni mongod calcola la propria cache su 7,65 GiB. Tre
membri di un replica set arrivano così a rivendicare più memoria di quanta ne esista.

**Decisione:** ogni servizio dichiara `mem_limit` e `cpus`, e ogni mongod riceve
`--wiredTigerCacheSizeGB` esplicito, dimensionato sotto il proprio `mem_limit`.

**Conseguenze:** gli stack sono prevedibili e coesistono nella stessa VM. Il file Compose
diventa esso stesso materiale didattico: mostra il calcolo invece di nasconderlo. In più,
`cpus` diventa uno strumento narrativo — si può strozzare deliberatamente un secondario
per mostrarne il ritardo di replica.

**Alternative scartate:** lasciare i valori predefiniti (l'OOM killer arriva sul palco);
alzare la memoria della VM (non risolve, e il pubblico può avere meno RAM).

**Fonti:** [S-001](../Sources.md#s-001), [S-002](../Sources.md#s-002), [S-003](../Sources.md#s-003)
```

- [ ] **Passo 3: gli ADR senza fonte tecnica dichiarano l'assenza in modo esplicito**

ADR-0015 e ADR-0017 sono decisioni organizzative. Riga fonti:
`**Fonti:** nessuna (decisione organizzativa)`.

- [ ] **Passo 4: allineare i collegamenti inversi in `Sources.md`**

Aggiornare la riga `Usata da:` di ogni fonte con l'elenco esatto degli ADR che la citano.

- [ ] **Passo 5: eseguire il verificatore**

Comando: `uv run --project tools python tools/check_citations.py docs/Decision.md docs/Sources.md`
Atteso: `Citazioni coerenti.` e uscita `0`. Se segnala fonti orfane, la scelta è netta: o
la fonte serve a un ADR e va citata, o non serve e va tolta.

- [ ] **Passo 6: commit**

Messaggio: `docs: registro delle decisioni architetturali ADR-0001..ADR-0017`

---

## Task 5 — Indice della documentazione e registro operativo

**File:**
- Crea: `docs/README.md`, `docs/registro-operativo-sviluppo.md`

**Interfacce:**
- Produce: la struttura di indice a cui `README.md` di radice (Task 6) rimanda, e il
  formato di voce del registro che ogni sessione successiva riusa.

- [ ] **Passo 1: `docs/README.md`**

Indice per sezioni, con una riga di descrizione per ciascuna. Le pagine non ancora scritte
compaiono con la feature che le produrrà — un indice che promette senza datare invecchia
male:

```markdown
| Pagina | Contenuto | Disponibile da |
|---|---|---|
| `02-architetture/replica-set.md` | topologia, elezioni, read preference | `feature/02` |
```

- [ ] **Passo 2: `docs/registro-operativo-sviluppo.md`**

```markdown
# Registro operativo di sviluppo

Diario cronologico: cosa è stato fatto, cosa è fallito, cosa se ne è imparato. Una voce per
sessione, la più recente in fondo. Distinto da [`Decision.md`](Decision.md), che registra
le sole decisioni.

---

## 2026-08-24 — Brainstorming e design

**Fatto:** rilevazione dell'ambiente; esclusione di Apple `container` (V-001); design delle
tre architetture, dell'applicazione e dell'impianto documentale in
[`00-progetto/2026-08-24-design.md`](00-progetto/2026-08-24-design.md); diciassette ADR.

**Fallito:** il primo tentativo di usare Rancher Desktop come runtime — il binario `docker`
risolveva a Rancher mentre il contesto puntava al socket di Docker Desktop. Sostituito con
Docker Desktop; i residui in `~/.rd` restano un controllo del preflight.

**Imparato:** la VM Docker dispone di 7,65 GiB dei 16 dell'host. È il vincolo che ha
generato i due profili dello sharded cluster (ADR-0010).

---

## 2026-08-25 — Approvazione e fondamenta

**Fatto:** approvazione della specifica; ADR-0016 (filmati su YouTube con copia locale) e
ADR-0017 (il repository resta esaustivo, i tagli sono solo di scena); avvio di
`feature/00-fondamenta`.
```

- [ ] **Passo 3: commit**

Messaggio: `docs: indice della documentazione e registro operativo`

---

## Task 6 — `README.md` di radice

**File:**
- Crea: `README.md`

**Interfacce:**
- Consuma: `docs/README.md` (Task 5).
- Produce: la promessa di avvio che il Task 7 deve mantenere. Non promettere target che il
  `Makefile` non ha ancora: il primo comando che fallisce su una macchina appena clonata
  costa più di una pagina intera non scritta.

- [ ] **Passo 1: scrivere le sezioni**

Abstract (tre righe: cos'è, per chi, cosa ci si fa) · Contesto del talk · Cosa contiene il
repository · Requisiti (Docker Desktop o equivalente, RAM consigliata, `make`) · Avvio
rapido, con i **soli** comandi già funzionanti · Indice verso `docs/` · Licenza.

- [ ] **Passo 2: dichiarare lo stato di avanzamento**

Una tabella `Stack | Stato | Branch` con le tre architetture, in questo momento tutte «in
lavorazione». Chi clona a fine agosto deve capire in trenta secondi cosa funziona.

- [ ] **Passo 3: verificare ogni comando citato**

Eseguire uno per uno i comandi che compaiono nell'avvio rapido. Se uno non funziona
ancora, toglierlo.

- [ ] **Passo 4: commit**

Messaggio: `docs: README di radice — abstract, requisiti, indice`

---

## Task 7 — `Makefile`

**File:**
- Crea: `Makefile`

**Interfacce:**
- Consuma: `tools/check_citations.py` (Task 3), `tools/pull-images.sh` e
  `tools/preflight.sh` (Task 8 e 9).
- Produce: i target `help`, `docs-check`, `tools-test`, `images-pull`, `images-verify`,
  `preflight`. Le feature successive aggiungono i propri target `up-*` / `down-*` senza
  toccare questi.

- [ ] **Passo 1: scheletro con `help` come target predefinito**

```makefile
.DEFAULT_GOAL := help
.PHONY: help docs-check tools-test images-pull images-verify preflight

help: ## Elenca i target disponibili
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
```

- [ ] **Passo 2: target di fondamenta**

```makefile
tools-test: ## Esegue la suite degli strumenti di repository
	uv run --project tools pytest -q

docs-check: ## Verifica il legame fra ADR e fonti
	uv run --project tools python tools/check_citations.py docs/Decision.md docs/Sources.md

images-pull: ## Scarica le immagini e le pinna per digest (richiede rete)
	./tools/pull-images.sh --pull

images-verify: ## Verifica che le immagini pinnate siano presenti in locale (offline)
	./tools/pull-images.sh --verify

preflight: ## Controlli della mattina del talk
	./tools/preflight.sh
```

- [ ] **Passo 3: verificare**

`make` senza argomenti mostra l'elenco; `make tools-test` e `make docs-check` passano.

- [ ] **Passo 4: commit**

Messaggio: `chore: Makefile come punto d'ingresso unico`

---

## Task 8 — `tools/pull-images.sh` e le immagini pinnate

Il vincolo offline (ADR-0009) è credibile solo se qualcosa impedisce a Compose di tentare
un pull. Un tag come `mongo:8.0` è un puntatore mobile: se l'immagine locale manca o il tag
si sposta, `docker compose up` va in rete [S-019]. Un digest no.

**File:**
- Crea: `tools/pull-images.sh`, `tools/images.env`

**Interfacce:**
- Produce: `tools/images.env` con righe `NOME=immagine@sha256:…`, sorgente unica per gli
  stack delle feature 01-03, che vi si agganciano con
  `image: ${MONGO_IMAGE}`.

- [ ] **Passo 1: elenco delle immagini in testa allo script**

```bash
#!/usr/bin/env bash
# Scarica le immagini del lab e le pinna per digest, oppure verifica che siano
# già presenti in locale. Il talk gira senza rete: il digest è ciò che lo garantisce.
set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FILE_IMMAGINI="${RADICE}/tools/images.env"

# NOME_VARIABILE=riferimento:tag
declare -a IMMAGINI=(
  "MONGO_IMAGE=mongo:8.0"
)
```

`mongo:8.0` porta con sé `mongosh` e i Database Tools: una sola immagine copre mongod,
la CLI e `mongodump`. Se una feature successiva ne richiederà un'altra, si aggiunge qui.

- [ ] **Passo 2: modalità `--pull`**

Per ogni immagine: `docker pull` (con `--platform linux/arm64` solo se richiesto
esplicitamente), poi lettura del digest:

```bash
digest="$(docker image inspect --format '{{index .RepoDigests 0}}' "$riferimento")"
```

Scrivere `NOME=<digest>` in `tools/images.env`, preceduto da un'intestazione che riporta
data e comando di rigenerazione. Il file è **versionato**: è il lasciapassare offline.

- [ ] **Passo 3: modalità `--verify`**

Legge `tools/images.env`, e per ciascuna riga esegue
`docker image inspect "$riferimento" >/dev/null 2>&1`. **Nessun accesso alla rete.**
Uscita `1` se anche una sola manca, con il comando esatto da eseguire per rimediare —
quando serve, serve subito.

- [ ] **Passo 4: eseguire `--pull` per davvero e versionare il risultato**

Comando: `make images-pull`
Atteso: `tools/images.env` contiene il digest di `mongo:8.0`.
Annotare l'esito come nuova fonte `V-003` in `Sources.md` (immagine, digest, data,
piattaforma) e citarla in ADR-0008 e ADR-0009, aggiornandone la riga `Fonti`. Poi
`make docs-check`.

- [ ] **Passo 5: provare il fallimento**

Verificare che `--verify` fallisca su un digest inesistente: modificare temporaneamente
una cifra del digest in una copia del file, eseguire, ripristinare. Uno script di sicurezza
mai visto fallire non è uno script di sicurezza.

- [ ] **Passo 6: commit**

Messaggio: `feat: pull-images.sh — immagini pinnate per digest per il lab offline`

---

## Task 9 — `tools/preflight.sh`

Lo strato 3 del piano B (§9.3 della specifica). Un solo comando, la mattina del talk,
prima di aprire le slide.

**File:**
- Crea: `tools/preflight.sh`

**Interfacce:**
- Consuma: `tools/images.env` e `tools/pull-images.sh --verify` (Task 8).
- Produce: uscita `0` se tutto è a posto, `1` in presenza di errori bloccanti. Gli avvisi
  non bloccano. Le feature 01-03 aggiungono i propri controlli `healthy`.

- [ ] **Passo 1: impianto — due categorie di esito**

```bash
#!/usr/bin/env bash
# Controlli della mattina del talk. Errori bloccanti -> uscita 1. Avvisi -> uscita 0.
set -uo pipefail   # niente -e: i controlli devono girare tutti e riferire insieme

ERRORI=0
ok()      { printf '  \033[32m✓\033[0m %s\n' "$1"; }
avviso()  { printf '  \033[33m!\033[0m %s\n' "$1"; }
errore()  { printf '  \033[31m✗\033[0m %s\n' "$1"; ERRORI=$((ERRORI + 1)); }
```

L'assenza di `-e` è deliberata: un preflight che si ferma al primo problema costringe a
tre giri. Deve dire tutto quello che non va, subito.

- [ ] **Passo 2: controllo del daemon e del contesto**

`docker info` risponde (bloccante) · contesto attivo riportato per informazione.

- [ ] **Passo 3: controllo del PATH — i residui di Rancher Desktop**

```bash
percorso_docker="$(command -v docker || true)"
case "$percorso_docker" in
  *"/.rd/"*) errore "docker risolve a Rancher Desktop: $percorso_docker" ;;
  "")        errore "docker non è nel PATH" ;;
  *)         ok "docker: $percorso_docker" ;;
esac
[ -d "$HOME/.rd" ] && avviso "residui di Rancher Desktop in ~/.rd: valuta la rimozione"
```

Questo controllo esiste perché il problema si è già verificato il 2026-08-24 e si è
manifestato come un errore di socket incomprensibile.

- [ ] **Passo 4: controllo della memoria della VM**

Lettura da `docker info --format '{{.MemTotal}}'`. Sotto 6 GiB: errore. Fra 6 e 8 GiB:
avviso con la raccomandazione di portare la VM a 10-12 GiB. Non bloccante, perché il
pubblico può avere meno RAM e il lab deve restare loro utilizzabile.

- [ ] **Passo 5: controllo delle porte libere**

Elenco da §5.2 della specifica: `27017`, `27021-27023`, `27117-27118`, `27131-27133`,
`27141-27143`, `27151-27153`. Con `lsof -nP -iTCP:"$porta" -sTCP:LISTEN`. Una porta
occupata **da un container del lab** non è un errore: distinguere confrontando con
`docker ps --format '{{.Ports}}'`.

- [ ] **Passo 6: controllo delle immagini**

Richiama `tools/pull-images.sh --verify`. Bloccante: senza immagini non c'è demo, e in
sala non si scarica.

- [ ] **Passo 7: controllo dei filmati locali (ADR-0016)**

```bash
CARTELLA_FILMATI="${DEMO_VIDEOS_DIR:-$HOME/SqlStart2026-registrazioni}"
```

Se manca o non contiene alcun `.mp4`: **avviso** oggi, da promuovere a **errore** nel
preflight del 18 settembre, quando i filmati devono esistere. Annotarlo nel runbook.

- [ ] **Passo 8: riepilogo finale ed esito**

Numero di controlli superati, avvisi ed errori. Uscita `1` se `ERRORI > 0`.

- [ ] **Passo 9: eseguire su questa macchina**

Comando: `make preflight`
Registrare l'output come `V-004` in `Sources.md`, citata da ADR-0009. Poi `make docs-check`.

- [ ] **Passo 10: commit**

Messaggio: `feat: preflight.sh — controlli della mattina del talk`

---

## Task 10 — Spike dello sharded cluster

Il punto di massima incertezza del progetto: il Product Owner ha poca esperienza di
sharded cluster e la catena di init sotto keyfile ha tre anelli invece di due. Va sondato
adesso. Se non funziona come previsto, `feature/03` va ripensata mentre c'è tempo, non il
14 settembre.

Il codice è **usa-e-getta** e vive in `spike/`, che è ignorata da git. Nel repository entra
il verbale.

**File:**
- Crea (ignorato): `spike/03-sharded/docker-compose.yml`, `spike/03-sharded/init/*`
- Crea (versionato): `docs/00-progetto/2026-08-25-spike-sharded.md`
- Modifica: `docs/Decision.md` (ADR-0025), `docs/Sources.md` (V-005),
  `docs/registro-operativo-sviluppo.md`

**Interfacce:**
- Consuma: `MONGO_IMAGE` da `tools/images.env` (Task 8).
- Produce: il Compose funzionante come blocco di codice dentro il verbale. `feature/03` lo
  promuove a file invece di ripartire da zero.

- [ ] **Passo 1: la topologia minima del profilo `palco`**

Un config server (replica set `cfgrs`, 1 membro), due shard (`shard1rs`, `shard2rs`, 1
membro ciascuno), un `mongos`. Quattro container. Limiti da §5.1: `512m` / `640m` / `384m`,
`cpus: 0.5`, cache WiredTiger `0.25`.

- [ ] **Passo 2: la catena di init, un anello alla volta**

Verificare **in quest'ordine**, senza saltare avanti: ogni anello che si aggiunge a una
base non funzionante costa il doppio da diagnosticare.

1. `keyfile-init` genera il keyfile nel volume nominato; `chmod 400`, `chown 999:999`.
2. Il config server parte con `--configsvr --replSet cfgrs --keyFile`, con
   `MONGO_INITDB_ROOT_USERNAME/PASSWORD` sul primo membro.
3. `cfg-init` esegue `rs.initiate()` autenticato come root.
4. Gli shard partono con `--shardsvr --replSet shard1rs --keyFile`; ciascuno esegue il
   proprio `rs.initiate()`.
5. `mongos` parte con `--configdb cfgrs/…` e `--keyFile`.
6. `sh-init` esegue `sh.addShard()` per ciascuno shard e abilita lo sharding sul database
   di demo.

- [ ] **Passo 3: la domanda a cui lo spike deve rispondere**

Annotare **letteralmente** l'esito di ciascuna, con l'output osservato:

| Domanda | Perché conta |
|---|---|
| Gli shard hanno bisogno del proprio utente root, o basta il keyfile per l'autenticazione interna? | determina quanti anelli di init servono davvero |
| `sh.addShard()` funziona autenticato come root del config server? | se no, serve un utente su ogni shard |
| `mongos` accetta un config server a **un solo membro**? | è il presupposto del profilo `palco` (ADR-0010) |
| Quanta memoria consuma davvero il profilo `palco` a regime? | confronto con la stima di 2,2 GiB in §5.1 |
| Quanto impiega lo stack a diventare completamente `healthy`? | se supera i 90 s, sul palco va avviato prima |

- [ ] **Passo 4: misurare, non stimare**

```bash
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}'
```

E cronometrare l'avvio da `up -d` all'ultimo `healthy`.

- [ ] **Passo 5: scrivere il verbale `docs/00-progetto/2026-08-25-spike-sharded.md`**

Struttura: obiettivo · topologia provata · **il Compose che funziona**, per intero ·
tabella domanda → risposta osservata · misure di memoria e tempo · sorprese ·
raccomandazioni per `feature/03`.

Se qualcosa non ha funzionato, il verbale lo dice. Uno spike che riporta solo successi non
ha sondato niente.

- [ ] **Passo 6: ADR-0025 con l'esito**

Titolo secondo il risultato, per esempio *«Catena di inizializzazione dello sharded cluster
sotto keyfile»*. Stato Accettata. Fonti: la nuova verifica `V-005` più `S-005` e `S-008`.
Se lo spike **contraddice** la specifica, ADR-0025 lo dichiara e segnala quale ADR
precedente ne risulta superato: è a questo che serve un registro cronologico.

- [ ] **Passo 7: aggiornare `Sources.md` e il registro operativo, poi verificare**

Comando: `make docs-check` — Atteso: uscita `0`.

- [ ] **Passo 8: rimuovere lo spike dal disco**

`rm -rf spike/`. Il Compose vive nel verbale. Codice non eseguito che resta in giro viene
poi copiato da qualcuno.

- [ ] **Passo 9: commit**

Messaggio: `docs: verbale dello spike sharded cluster e ADR-0025`

---

## Task 11 — `docs/06-sviluppo/gestione-risorse-compose.md`

La pagina didattica che ADR-0004 e ADR-0013 rendono necessaria. Non appartiene a un singolo
stack: li governa tutti, e va scritta prima che ne esista uno.

**File:**
- Crea: `docs/06-sviluppo/gestione-risorse-compose.md`
- Modifica: `docs/README.md` (indice)

**Interfacce:**
- Consuma: S-001, S-002, S-003, S-004 (Task 2).
- Produce: la pagina a cui le feature 01-03 rimandano invece di rispiegare i limiti in ogni
  README di stack.

- [ ] **Passo 1: sezione «Perché senza limiti va male»**

La formula della cache predefinita e la lettura del cgroup [S-001]. Il conto esplicito: tre
mongod senza limiti in una VM da 7,65 GiB. Cosa si vede quando succede — non «va in OOM»,
ma il messaggio preciso nel log e l'exit code 137.

- [ ] **Passo 2: sezione «Come si dimensiona»**

Il rapporto fra `mem_limit`, `--wiredTigerCacheSizeGB` e la memoria che mongod usa **fuori**
dalla cache (connessioni, ordinamenti, aggregazioni). La tabella di §5.1 con il
ragionamento che l'ha prodotta, non solo i numeri.

- [ ] **Passo 3: sezione «`mem_limit` contro `deploy.resources`»**

Le due forme, la storia ereditata da Swarm, quale vale dove [S-003] [S-004], e il
disclaimer per chi migra verso Podman — attuazione della richiesta esplicita del Product
Owner del 2026-08-24. Entrambe le forme mostrate affiancate.

- [ ] **Passo 4: sezione «`cpus` come strumento narrativo»**

Limitare la CPU non serve solo a proteggere la postazione: strozzare deliberatamente un
secondario mostra il ritardo di replica in modo osservabile. Come si fa e cosa si vede.

- [ ] **Passo 5: verificare le citazioni**

Ogni affermazione tecnica della pagina porta un riferimento. Rileggere cercando le frasi
senza citazione: sono quelle che vengono dalla memoria del modello, ed è esattamente ciò
che il Product Owner ha chiesto di non far entrare in `docs/`.

- [ ] **Passo 6: aggiornare l'indice, poi `make docs-check`**

- [ ] **Passo 7: commit**

Messaggio: `docs: gestione delle risorse in Compose — memoria, CPU, cache WiredTiger`

---

## Task 12 — Chiusura del branch

**File:**
- Modifica: `docs/registro-operativo-sviluppo.md`

- [ ] **Passo 1: verifica completa su albero pulito**

Eseguire nell'ordine: `make tools-test` · `make docs-check` · `make images-verify` ·
`make preflight`. I primi tre devono uscire `0`. Riportare l'esito del quarto così com'è.

- [ ] **Passo 2: prova del clone pulito**

Clonare il branch in una cartella temporanea, seguire **solo** il `README.md`, e verificare
che i comandi dell'avvio rapido funzionino. È il criterio di successo «un lettore riproduce
il lab dalla sola documentazione» applicato a ciò che esiste finora.

- [ ] **Passo 3: voce di chiusura nel registro**

Cosa è stato fatto, cosa è fallito, cosa se ne è imparato — con l'esito dello spike in
evidenza, che è l'informazione che cambia i piani.

- [ ] **Passo 4: commit e push**

Messaggio: `docs: chiusura di feature/00-fondamenta nel registro operativo`

- [ ] **Passo 5: aprire la PR**

Titolo: `feature/00-fondamenta — igiene, impianto documentale, strumenti di palco`
Corpo: cosa contiene, cosa **non** contiene e perché, esito dello spike, e i comandi che il
revisore può eseguire per verificare. Segnalare in evidenza qualsiasi divergenza fra fonti
consultate e specifica.

---

## Criterio di completamento

Il branch è finito quando:

1. `make docs-check` esce `0` e non esistono fonti orfane né riferimenti morti.
2. `make tools-test` esce `0`.
3. `make images-verify` esce `0` **con la rete disattivata**.
4. `make preflight` gira e riporta un esito comprensibile a chi non lo ha scritto.
5. Lo spike sharded ha una risposta scritta per ciascuna delle cinque domande del Task 10,
   e ADR-0025 registra l'esito.
6. Un clone pulito è utilizzabile seguendo il solo `README.md`.

Se il calendario stringe, l'unico task rinviabile è il **Task 11**: la pagina sulle risorse
può nascere in `feature/01` insieme al primo stack che la esemplifica. Tutti gli altri sono
presupposti delle branch successive. Il Task 10 in particolare **non è rinviabile**: è la
ragione per cui questo branch esiste adesso.
