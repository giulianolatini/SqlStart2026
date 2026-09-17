# Piano di implementazione — `feature/01-stack-standalone`

> **Per chi esegue il piano:** i passi usano caselle `- [ ]` da spuntare. Ogni task
> termina con un deliverable verificabile e un commit. Leggere anche la specifica
> collegata: questo piano attua decisioni prese lì, non le rimette in discussione.

> **Nota di allineamento, 2026-08-31.** Dove questo piano dice
> `pull_policy: ${PULL_POLICY:-missing}` e `PULL_POLICY=never`, leggere **`pull_policy: never`
> scritto fisso nel file Compose**, senza variabile. Il cambio nasce da una review esterna della
> PR #2, che ha fatto emergere un conflitto fra [ADR-0018](../Decision.md#adr-0018) e
> [ADR-0027](../Decision.md#adr-0027), entrambe Accettata: lo scioglie
> [ADR-0039](../Decision.md#adr-0039), che supera la prima. Il criterio di completamento 2 — «`make
> up-01` funziona con la rete disattivata» — non cambia di merito: cambia il modo in cui la
> garanzia è scritta. Il testo qui sotto **non** è stato riscritto.

---

**Obiettivo:** produrre il primo dei tre stack Compose — l'istanza singola — e la
documentazione che lo accompagna, insieme allo strumento che rende **eseguibili** sul file
Compose le decisioni prese in `feature/00`, invece di lasciarle affidate alla memoria di chi
scrive il secondo e il terzo stack.

**Architettura:** lo stack è deliberatamente il più semplice dei tre e il meno interessante da
guardare. Il suo valore non è tecnico, è narrativo: apre il talk mostrando cosa si ottiene con
un solo `mongod` e — soprattutto — cosa **non** si ottiene, che è la domanda a cui rispondono
i due stack successivi. Per questo gira senza autenticazione ed è presentato come esempio
negativo ([ADR-0005](../Decision.md#adr-0005)).

Attorno al file Compose nascono due cose che sopravvivranno al branch. La prima è
`tools/check_stack.py`: le decisioni di `feature/00` sulle risorse, sul `pull_policy`, sui
nomi host e sui tag delle immagini valgono per tutti e tre gli stack, e un ADR che nessuno
verifica è una buona intenzione. Lo strumento controlla il file, non il cluster: gira offline,
in millisecondi, e diventa una porta che `feature/02` e `feature/03` devono attraversare. La
seconda è `docs/02-architetture/trappole-mongodb-in-docker.md`, che raccoglie i punti in cui
MongoDB e Docker si fraintendono — pagina condivisa, aperta qui e ampliata dai due branch
successivi.

**Stack tecnico:** Compose Specification (senza chiave `version:`), MongoDB **7.0.40**
dall'immagine ufficiale pinnata per digest, Bash (`set -euo pipefail`), Python 3.13+ con
`pytest` per gli strumenti di repository, GNU Make, Markdown.

**Specifica:** [`docs/00-progetto/2026-08-24-design.md`](2026-08-24-design.md) §5.1
(bilancio delle risorse), §5.2 (mappa delle porte), §5.3 (stack 01), approvata dal Product
Owner il 2026-08-25. L'elenco delle pagine dovute da questo branch è nell'indice
[`docs/README.md`](../README.md), colonna «Branch».

---

## Vincoli globali

Valgono per ogni task, senza doverli ripetere.

- **Lingua:** tutto il materiale prodotto è in **italiano**, compresi commenti nel codice,
  messaggi degli script e messaggi di commit.
- **Documentazione:** tutta sotto `docs/`. In radice esiste **solo** `README.md`.
- **Citazioni:** nessuna affermazione tecnica entra in `docs/` senza un riferimento
  `[S-NNN]`, `[V-NNN]` o `[C-NNN]` verso [`Sources.md`](../Sources.md). La verifica su fonte
  primaria **precede** la scrittura. `make docs-check` deve uscire `0` a ogni commit.
- **Offline:** nessun artefatto destinato al palco può richiedere rete. Ogni servizio dichiara
  `pull_policy: ${PULL_POLICY:-missing}` ([ADR-0018](../Decision.md#adr-0018)); nessuna
  immagine usa il tag `latest`, in nessuna circostanza.
- **MongoDB 7.0.40**, immagine ufficiale pinnata **per digest** tramite
  [`tools/images.env`](../../tools/images.env) ([ADR-0028](../Decision.md#adr-0028), che
  supera [ADR-0008](../Decision.md#adr-0008)). Il digest non si scrive a mano nei file
  Compose: si legge dalla variabile.
- **Compose:** Specification corrente, **senza** chiave `version:`. Sintassi breve
  `mem_limit` / `cpus` nei file, `deploy.resources` solo nella documentazione
  ([ADR-0013](../Decision.md#adr-0013)).
- **Risorse:** ogni servizio dichiara `mem_limit` e `cpus`; ogni `mongod` dichiara
  `--wiredTigerCacheSizeGB` esplicito e **non superiore** al proprio `mem_limit`
  ([ADR-0004](../Decision.md#adr-0004)). Per questo stack: `1024m`, `0.25`, `1.0`.
- **Nomi host:** mai indirizzi IP, né nei file né nella documentazione
  ([ADR-0021](../Decision.md#adr-0021)).
- **Ordine di avvio:** `depends_on` con `condition: service_healthy`, mai `sleep`
  ([ADR-0023](../Decision.md#adr-0023)).
- **Indipendenza degli stack:** progetto Compose, rete e volumi propri, nessun `include` né
  profilo condiviso con gli altri due ([ADR-0003](../Decision.md#adr-0003)).
- **Nomi:** nessun nome di strumento interno nei percorsi o nei contenuti pubblicati. Il
  repository è materiale didattico.
- **Commit:** stile convenzionale (`chore:`, `docs:`, `feat:`, `test:`, `fix:`), corpo in
  italiano, chiusi da `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- **Python:** SOLID e TDD Red → Green → Refactor. Funzioni pure separate dall'I/O; nessuna
  stampa fuori dal punto d'ingresso.
- **Bash:** `#!/usr/bin/env bash`, `set -euo pipefail`, nessun percorso assoluto della
  macchina del relatore, tutto relativo alla radice del repository.

---

## Mappa dei file

| Percorso | Responsabilità | Task |
|---|---|---|
| `docker/01-standalone/compose.yaml` | l'unico artefatto che il pubblico copierà: un `mongod`, leggibile dall'alto in basso | 2-5 |
| `docker/01-standalone/.env.example` | i parametri che chi clona può cambiare, con i valori del lab come predefiniti | 2 |
| `docker/01-standalone/conf/mongod.conf` | configurazione in YAML, se il Task 4 decide che serve | 4 |
| `docker/01-standalone/init/01-utenti.js` | **assente per scelta**: lo standalone gira aperto. La cartella esiste con il solo seed dei dati | 5 |
| `docker/01-standalone/init/10-dati-demo.js` | dataset deterministico, stesso contenuto a ogni avvio | 5 |
| `tools/check_stack.py` | funzioni pure che leggono un documento Compose e restituiscono i problemi; CLI in coda | 1 |
| `tools/tests/test_check_stack.py` | la suite che guida `check_stack.py` in TDD | 1 |
| `tools/smoke-standalone.sh` | verifica dal vivo che lo stack avviato risponda e rispetti ciò che dichiara | 6 |
| `Makefile` | target `up-01`, `down-01`, `logs-01`, `smoke-01`, `stack-check` | 6 |
| `docs/02-architetture/standalone.md` | quando basta un'istanza singola e cosa non garantisce | 7 |
| `docs/02-architetture/trappole-mongodb-in-docker.md` | pagina condivisa, aperta qui | 8 |
| `docs/03-amministrazione/log.md` | formato dei log, livelli, rotazione | 9 |
| `docs/04-mongosh/guida-mongosh.md` | connessione, comandi quotidiani, script non interattivi | 10 |
| `docs/01-installazione/linux.md` · `windows.md` | istanza singola **fuori** da Docker | 11 |
| `docs/Decision.md` · `docs/Sources.md` | gli ADR nuovi e le fonti che li giustificano | 12 |
| `docs/registro-operativo-sviluppo.md` | il diario, compresi i fallimenti | 13 |

Due assenze deliberate, per non farle scoprire a metà strada. **Non** nasce qui
`tools/reset-demo.sh`: lo stato da riportare a noto è interessante quando c'è un replica set
da rompere, e nascerebbe qui per essere riscritto in `feature/02`. **Non** nasce qui
`docs/05-talk/runbook-demo.md`: [ADR-0015](../Decision.md#adr-0015) lo vuole documento unico
e autonomo, e un runbook scritto su un terzo delle demo è un runbook da riscrivere.

---

## Task 1 — `tools/check_stack.py`: le decisioni di `feature/00` diventano eseguibili

**File:**
- Creare: `tools/check_stack.py`
- Creare: `tools/tests/test_check_stack.py`
- Modificare: `tools/pyproject.toml` (dipendenza `pyyaml`)

**Interfacce:**
- Produce: `carica(percorso: Path) -> dict`, `verifica(documento: dict, digest_noti: set[str]) -> list[str]`, `main(argv: Sequence[str]) -> int`. I task 2-5 sono verdi quando `verifica` non ha più niente da dire sul file dello stack.

Questo task viene **prima** del file Compose, non dopo. Il motivo è quello di sempre in TDD,
ma qui c'è una ragione in più: le otto regole qui sotto sono già state decise in
`feature/00`, e scriverle come test le costringe a essere precise. Una regola che non si sa
scrivere come asserzione non era una decisione, era un'intenzione.

Le regole, ciascuna con l'ADR che la impone:

| # | Regola | Origine |
|---|---|---|
| 1 | nessuna chiave `version:` al livello superiore | Compose Specification, obsoleta |
| 2 | ogni servizio ha `image:`, e l'immagine risolve a un digest presente in `tools/images.env` | [ADR-0009](../Decision.md#adr-0009), [ADR-0028](../Decision.md#adr-0028) |
| 3 | nessuna immagine usa il tag `latest`, neppure implicito | [ADR-0018](../Decision.md#adr-0018) |
| 4 | ogni servizio dichiara `pull_policy` | [ADR-0018](../Decision.md#adr-0018) |
| 5 | ogni servizio dichiara `mem_limit` **e** `cpus` | [ADR-0004](../Decision.md#adr-0004), [ADR-0013](../Decision.md#adr-0013) |
| 6 | ogni servizio che avvia `mongod` dichiara `--wiredTigerCacheSizeGB`, e il valore in MiB **non supera** il proprio `mem_limit` | [ADR-0004](../Decision.md#adr-0004), [V-009](../Sources.md#v-009) |
| 7 | nessun indirizzo IPv4 letterale in `command`, `environment` o `extra_hosts` | [ADR-0021](../Decision.md#adr-0021) |
| 8 | ogni `depends_on` in forma lunga usa `condition:`, e il servizio atteso ha un `healthcheck` | [ADR-0023](../Decision.md#adr-0023) |

La regola 6 è quella che giustifica lo strumento da sola. La misura di `feature/00` ha
trovato che **una cache maggiore del `mem_limit` viene accettata senza un solo avviso** che
metta in relazione le due cifre [V-009](../Sources.md#v-009): il controllo di coerenza non
esiste nel prodotto, e il file Compose è l'unico posto dove può esistere. Lo strumento fa
esattamente il controllo che MongoDB non fa.

- [ ] **Passo 1 — Il test che fallisce sulla regola 6**

```python
def test_cache_maggiore_del_limite_di_memoria_e_un_problema() -> None:
    documento = {
        "services": {
            "mongo": {
                "image": "mongo@sha256:aaa",
                "pull_policy": "missing",
                "mem_limit": "512m",
                "cpus": 1.0,
                "command": ["mongod", "--wiredTigerCacheSizeGB", "1.0"],
            }
        }
    }
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("wiredTigerCacheSizeGB" in p and "mem_limit" in p for p in problemi)
```

- [ ] **Passo 2 — Eseguire e vedere il rosso**

Comando: `uv run --directory tools pytest -q -k cache_maggiore`
Atteso: `NameError` / `ImportError` — `verifica` non esiste.

- [ ] **Passo 3 — L'implementazione minima della sola regola 6**

Nessuna delle altre sette regole entra adesso. `mem_limit` va convertito: `1024m` sono
1024 MiB, `1g` sono 1024 MiB, e `--wiredTigerCacheSizeGB 0.25` sono 256 MiB, perché
l'opzione è letta in **GiB** e non in GB decimali [V-009](../Sources.md#v-009). Questa
conversione è la parte del codice che merita un commento, perché è la parte in cui il manuale
è ambiguo e la misura no.

- [ ] **Passo 4 — Verde su quel test, rosso su nessun altro**

Comando: `uv run --directory tools pytest -q`

- [ ] **Passo 5 — Ripetere il ciclo per le regole 1-5, 7, 8**

Un test per regola, più un test per il caso conforme che non deve produrre niente. Ogni
messaggio di problema nomina il servizio, dice cosa manca e **perché** è richiesto, con la
sigla dell'ADR: chi lo legge deve poter risalire alla decisione senza chiedere. Nessun
messaggio generico del tipo «configurazione non valida».

- [ ] **Passo 6 — Il caso negativo che conta**

Un documento conforme in tutto **tranne** la regola in esame, uno per regola. Il modo in cui
`feature/00` ha scoperto il difetto di `parse_decisions` è stato mutilare un file conforme e
guardare se il controllo se ne accorgeva: qui il metodo si applica dall'inizio invece che
dopo una review.

- [ ] **Passo 7 — CLI e commit**

`main(argv)` accetta uno o più percorsi, stampa i problemi su `stderr`, esce `1` se ce ne
sono, `0` altrimenti, e con un messaggio leggibile se un file non si trova — stesso
comportamento di `check_citations.py`, perché due strumenti dello stesso repository che
falliscono in due modi diversi sono due strumenti da ricordare invece che uno.

```bash
git add tools/check_stack.py tools/tests/test_check_stack.py tools/pyproject.toml
git commit -m "feat: check_stack.py — gli ADR sulle risorse diventano verificabili"
```

---

## Task 2 — Il servizio `mongod`: immagine pinnata, porta, volume

**File:**
- Creare: `docker/01-standalone/compose.yaml`
- Creare: `docker/01-standalone/.env.example`

**Interfacce:**
- Consuma: `tools/images.env` (variabile `MONGO_IMAGE`), `tools/check_stack.py` dal Task 1.
- Produce: il progetto Compose `sqlstart-01-standalone` con il servizio `mongo-standalone` sulla porta host `27017`.

- [ ] **Passo 1 — Il file minimo**

```yaml
name: sqlstart-01-standalone

services:
  mongo-standalone:
    image: ${MONGO_IMAGE:?variabile assente: eseguire `make images-pull` oppure passare tools/images.env}
    container_name: mongo-standalone
    hostname: mongo-standalone
    pull_policy: ${PULL_POLICY:-missing}
    restart: unless-stopped
    ports:
      - "${PORTA_HOST:-27017}:27017"
    volumes:
      - dati:/data/db

volumes:
  dati:
```

Tre scelte da non lasciare implicite. Il `name:` esplicito realizza l'indipendenza voluta da
[ADR-0003](../Decision.md#adr-0003): progetto, rete e volumi restano separati dagli altri due
stack anche se qualcuno li avvia tutti insieme. La sintassi `${MONGO_IMAGE:?messaggio}` fa
fallire Compose **subito e dicendo cosa manca**, invece di avviare un container con
un'immagine vuota. Il volume è **nominato** e non un bind mount: su macOS un bind mount di
`/data/db` paga il filesystem condiviso a ogni scrittura, e la demo sulle prestazioni
misurerebbe VirtioFS invece di WiredTiger.

- [ ] **Passo 2 — `.env.example` con i valori del lab**

Commentato riga per riga: chi clona deve capire cosa può cambiare senza rompere le demo.

- [ ] **Passo 3 — `docker compose config -q` e `check_stack.py`**

Comando: `docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml config -q`
Atteso: uscita `0` e nessun output.
Poi: `uv run --project tools python tools/check_stack.py docker/01-standalone/compose.yaml`
Atteso: **rosso** sulle regole 5 e 6 — `mem_limit`, `cpus` e la cache non ci sono ancora. È il
risultato giusto: lo strumento del Task 1 sta facendo il suo lavoro.

- [ ] **Passo 4 — Commit**

---

## Task 3 — Limiti di risorsa e cache WiredTiger leggibile

**File:**
- Modificare: `docker/01-standalone/compose.yaml`

- [ ] **Passo 1 — Le tre righe, con il calcolo accanto**

```yaml
    mem_limit: 1024m
    cpus: 1.0
    command:
      - mongod
      # 0.25 GiB = 256 MiB di cache dentro 1024 MiB di limite. Il valore è dichiarato
      # a mano non perché mongod non sappia leggere il cgroup — lo legge, misurato in
      # V-009 — ma perché questo file è materiale didattico e il calcolo deve vedersi.
      - --wiredTigerCacheSizeGB
      - "0.25"
```

- [ ] **Passo 2 — `check_stack.py` passa dal rosso al verde**

Comando: `uv run --project tools python tools/check_stack.py docker/01-standalone/compose.yaml`
Atteso: uscita `0`.

- [ ] **Passo 3 — La verifica dal vivo, che è diversa dalla verifica statica**

Avviare lo stack e confrontare ciò che il file dichiara con ciò che il processo ha fatto:

```
db.serverStatus().wiredTiger.cache["maximum bytes configured"]   → atteso 268435456
db.hostInfo().system.memLimitMB                                   → atteso 1024
```

Se i due numeri non tornano, **non** correggere il file: aprire una verifica empirica in
`Sources.md` e capire perché, come è stato fatto per V-009. Un numero che non torna è
materiale per il talk.

- [ ] **Passo 4 — Commit**

---

## Task 4 — Healthcheck, e la questione del doppio canale di log

**File:**
- Modificare: `docker/01-standalone/compose.yaml`
- Eventuale: `docker/01-standalone/conf/mongod.conf`
- Modificare: `docs/Decision.md`, `docs/Sources.md`

**Questo task comincia con una misura, non con del codice.** Il design §5.3 prevede un
«doppio canale di log deliberato: stdout (per `docker compose logs`) **e** file `--logpath`».
L'assunto va verificato prima di costruirci sopra, perché il riferimento di `mongod` descrive
`--logpath` come una **redirezione**, non come una duplicazione: se è così, attivarlo spegne
`docker compose logs`, e con esso il modo più naturale di mostrare i log dal palco.

- [ ] **Passo 1 — Misurare**

Avviare due container, uno con `--logpath` e uno senza, e guardare `docker logs` in entrambi
i casi. Registrare l'esito come verifica empirica `V-0NN` in `Sources.md`, con il comando
eseguito e l'output osservato, qualunque sia il risultato.

- [ ] **Passo 2 — Decidere in base a ciò che si è misurato**

Se `--logpath` silenzia stdout, le vie sono tre e vanno pesate per **quanto costano al
pubblico**, non per eleganza: (a) solo stdout, e la rotazione si dimostra su un secondo
avvio dedicato; (b) `--logpath` più un sidecar che fa `tail -F` sul file e lo rimanda a
stdout, che funziona ma aggiunge un container al primo stack, quello che deve essere il più
semplice; (c) `--logpath` e basta, mostrando i log con `docker compose exec`. Scrivere un ADR
con la scelta e le due scartate, qualunque sia. Se invece i due canali convivono, l'ADR non
serve e la misura resta comunque in `Sources.md`: ha smentito un dubbio, che è un risultato.

- [ ] **Passo 3 — Healthcheck**

```yaml
    healthcheck:
      test: ["CMD", "mongosh", "--quiet", "--eval", "db.adminCommand('ping').ok"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s
```

`start_period` non è decorativo: senza, i primi tentativi falliti contano come guasti e il
container risulta `unhealthy` mentre sta semplicemente ancora partendo. Verificare che
`mongosh` esista **dentro** l'immagine 7.0.40 — sull'host non c'è
([`limiti-noti.md`](limiti-noti.md)) e non è detto che ci sia nell'immagine.

- [ ] **Passo 4 — Verificare che `healthy` arrivi, e in quanto tempo**

Comando: `docker compose ... ps --format 'table {{.Name}}\t{{.Status}}'`
Il tempo osservato entra nella documentazione del Task 7: chi guarda dal palco deve sapere
quanti secondi di silenzio sono normali.

- [ ] **Passo 5 — Commit**

---

## Task 5 — Dati di esempio deterministici

**File:**
- Creare: `docker/01-standalone/init/10-dati-demo.js`

Lo stesso dataset servirà ai tre stack e all'applicazione: nasce qui, in una forma che i
branch successivi possano riusare senza copiarlo.

- [ ] **Passo 1 — Requisito: deterministico**

Stesso contenuto a ogni avvio, `_id` compresi. Niente `new Date()` senza argomento, niente
`Math.random()` senza seme. Un dataset che cambia rende impossibile confrontare la demo dal
vivo con la registrazione di riserva, ed è esattamente il confronto che si fa quando la demo
va storta.

- [ ] **Passo 2 — Requisito: abbastanza grande da mostrare qualcosa**

Deve rendere visibile la differenza fra query con indice e senza — è il materiale della demo
sulle prestazioni — restando abbastanza piccolo da caricarsi in pochi secondi. Misurare il
tempo di caricamento e scriverlo nel Task 7.

- [ ] **Passo 3 — Verificare che l'entrypoint lo esegua davvero**

L'immagine ufficiale esegue `/docker-entrypoint-initdb.d/*.js` **solo se `/data/db` è
vuota**. Su un volume già popolato non succede niente, in silenzio. Provarlo: avviare, fare
`down` senza `-v`, riavviare e controllare se lo script è stato rieseguito. Il risultato va
in `trappole-mongodb-in-docker.md` (Task 8) — è una delle trappole che la pagina esiste per
raccogliere.

- [ ] **Passo 4 — Commit**

---

## Task 6 — I target del `Makefile` e la verifica dal vivo

**File:**
- Modificare: `Makefile`
- Creare: `tools/smoke-standalone.sh`

- [ ] **Passo 1 — I target**

`up-01`, `down-01`, `logs-01`, `smoke-01`, e `stack-check` che passa tutti i file Compose
esistenti a `check_stack.py`. I nomi seguono la nota già scritta in testa al `Makefile`: le
feature successive aggiungono i propri senza toccare quelli esistenti. `down-01` **non**
cancella il volume; per quello un target esplicito e nominato, perché un `down -v`
involontario alla vigilia del talk è un dataset da ricostruire.

- [ ] **Passo 2 — `tools/smoke-standalone.sh`**

Verifica dal vivo ciò che `check_stack.py` verifica sulla carta: il container è `healthy`, la
porta risponde, la cache configurata è quella dichiarata, il `mem_limit` visto da dentro è
quello scritto nel file, il dataset è caricato, e — questo è il punto narrativo — una
connessione **senza credenziali** riesce. L'ultimo controllo non è un difetto da correggere:
è l'esempio negativo di [ADR-0005](../Decision.md#adr-0005) reso eseguibile, e lo script deve
dirlo in chiaro invece di limitarsi a un `✓`.

- [ ] **Passo 3 — `make help` elenca i target nuovi**

Verificare che le descrizioni compaiano: la regola `awk` è quella di
[ADR-0029](../Decision.md#adr-0029), e un target senza `## ` a fine riga sparisce
dall'elenco senza che nessuno se ne accorga.

- [ ] **Passo 4 — Commit**

---

## Task 7 — `docs/02-architetture/standalone.md`

**File:**
- Creare: `docs/02-architetture/standalone.md`
- Modificare: `docs/README.md` (la riga passa da promessa a collegamento)

La pagina risponde a due domande e in quest'ordine: **quando basta** un'istanza singola, e
**cosa non garantisce**. La seconda è quella che apre il talk, perché è la ragione per cui
esistono gli altri due stack.

- [ ] **Passo 1 — Cosa non garantisce, con le fonti**

Nessuna ridondanza; nessun failover; `w: 1` è tutto ciò che si può chiedere, e cosa questo
significhi quando il processo muore fra l'acknowledgement e il flush su disco; nessun
oplog, quindi nessun change stream e nessun backup a caldo coerente
([ADR-0022](../Decision.md#adr-0022)); manutenzione che richiede finestra di fermo. Ogni
affermazione con la sua fonte primaria: `make docs-check` non lascia scelta.

- [ ] **Passo 2 — Quando basta davvero**

Contrappeso onesto: sviluppo, test, CI, dataset ricostruibili. Dire che un'istanza singola non
va mai bene sarebbe falso, e il pubblico se ne accorge.

- [ ] **Passo 3 — Il file Compose commentato**

Riga per riga, con i numeri misurati nei Task 3 e 4 al posto delle stime.

- [ ] **Passo 4 — Commit**

---

## Task 8 — `docs/02-architetture/trappole-mongodb-in-docker.md`

**File:**
- Creare: `docs/02-architetture/trappole-mongodb-in-docker.md`
- Modificare: `docs/README.md`

Pagina condivisa: nasce qui e viene ampliata da `feature/02` e `feature/03`. Struttura una
trappola per sezione — **sintomo**, causa, rimedio, fonte — così che i branch successivi
aggiungano sezioni senza riscrivere quelle esistenti.

Le trappole già note, due delle quali sono debito dichiarato di `feature/00`:

- [ ] **Passo 1 — Volume già popolato, script d'inizializzazione ignorato in silenzio**

Misurata nel Task 5.

- [ ] **Passo 2 — Il kernel della VM e le versioni di MongoDB** *(debito di `feature/00`)*

Nessuna MongoDB 8 pubblicata si avvia sul kernel della VM di Docker Desktop; il sintomo che
si vede è un container che esce senza un messaggio comprensibile.
[ADR-0028](../Decision.md#adr-0028) ha la storia, la pagina deve avere il **sintomo** —
perché è dal sintomo che si parte quando capita a qualcun altro.

- [ ] **Passo 3 — `MONGO_INITDB_ROOT_*` su un config server** *(debito di `feature/00`)*

L'entrypoint rimuove `--replSet` dal mongod temporaneo **solo se entrambe** le variabili root
sono presenti ([ADR-0005](../Decision.md#adr-0005)): su un config server questo produce un
avvio che sembra riuscito e un cluster che non si forma.

- [ ] **Passo 4 — Nomi host: `localhost` dentro il container non è `localhost` sull'host**

La trappola che [ADR-0021](../Decision.md#adr-0021) previene. Si vede già sullo standalone,
con la stringa di connessione.

- [ ] **Passo 5 — Commit**

---

## Task 9 — `docs/03-amministrazione/log.md`

**File:**
- Creare: `docs/03-amministrazione/log.md`
- Modificare: `docs/README.md`

- [ ] **Passo 1 — Formato e componenti**

Il log strutturato in JSON dalla 4.4 in poi: campi, `severity`, `component`. Cosa si legge
davvero e cosa si salta.

- [ ] **Passo 2 — `logRotate` e la decisione del Task 4**

`db.adminCommand({logRotate: 1})` e cosa succede se non c'è un `--logpath` su cui ruotare.

- [ ] **Passo 3 — Cosa cercare durante un'elezione**

Le righe che si illumineranno in `feature/02`, quando un nodo cade dal vivo. Questa sezione
si scrive qui e si **verifica** là.

- [ ] **Passo 4 — Commit**

---

## Task 10 — `docs/04-mongosh/guida-mongosh.md`

**File:**
- Creare: `docs/04-mongosh/guida-mongosh.md`
- Modificare: `docs/README.md`

- [ ] **Passo 1 — Connessione**

Stringhe di connessione da host e da dentro la rete Compose, e perché sono diverse. `mongosh`
sull'host **non c'è** ([`limiti-noti.md`](limiti-noti.md)): ogni comando della guida deve
essere eseguibile via `docker compose exec`, e la guida deve dirlo in apertura invece di
lasciarlo scoprire al primo errore.

- [ ] **Passo 2 — Comandi di uso quotidiano**

- [ ] **Passo 3 — Comandi di amministrazione**

Replica set e sharded cluster: la sezione si scrive completa qui, perché la guida è unica, e
si **verifica** nei branch che avviano quelle topologie. Marcare le parti non ancora
eseguite: una guida che afferma cose non provate è peggio di una guida incompleta.

- [ ] **Passo 4 — Script non interattivi**

`--eval`, `--file`, `--quiet`, codici di uscita. È la forma che usano `smoke-standalone.sh` e
gli healthcheck: la guida documenta ciò che il repository già fa.

- [ ] **Passo 5 — Commit**

---

## Task 11 — `docs/01-installazione/linux.md` e `windows.md`

**File:**
- Creare: `docs/01-installazione/linux.md`, `docs/01-installazione/windows.md`
- Modificare: `docs/README.md`

Le uniche due pagine del branch che **non** parlano di Docker: installazione di un'istanza
singola sul sistema operativo, che è ciò che farà in azienda buona parte del pubblico.

- [ ] **Passo 1 — Linux: repository ufficiale, servizio, percorsi**

Repository e chiave GPG, `systemd`, percorsi di dati e configurazione, `mongod.conf`,
`ulimit`, la raccomandazione su `THP`. Ogni affermazione da fonte primaria.

- [ ] **Passo 2 — Windows: installer, servizio, differenze**

Comprese le differenze che contano per la sicurezza: sui permessi del keyfile la
documentazione dichiara che su Windows **non vengono controllati affatto**
([ADR-0005](../Decision.md#adr-0005)).

- [ ] **Passo 3 — Riserva dichiarata in testa a entrambe**

Queste procedure **non** sono state eseguite sulla macchina di sviluppo, che è macOS con
Docker. Provengono da documentazione ufficiale e vanno marcate come tali: la
[gerarchia delle fonti](../Decision.md#adr-0024) distingue ciò che è stato verificato da ciò
che è stato letto, e mescolarle qui sarebbe il primo posto in cui il repository mentirebbe.

- [ ] **Passo 4 — Commit**

---

## Task 12 — ADR e fonti del branch

**File:**
- Modificare: `docs/Decision.md`, `docs/Sources.md`

- [ ] **Passo 1 — Gli ADR nuovi**

Quelli prevedibili adesso: la decisione sul canale dei log (Task 4), e la scelta di dotarsi di
una verifica eseguibile sui file Compose (Task 1) — che è una decisione sull'artefatto, non
un dettaglio implementativo, e appartiene alla stessa famiglia di
[ADR-0029](../Decision.md#adr-0029). Altri nasceranno strada facendo: si scrivono quando la
decisione si prende, non alla fine.

- [ ] **Passo 2 — Le fonti**

Ogni pagina dei Task 7-11 porta le proprie. Le verifiche empiriche del branch — cache
configurata, `memLimitMB`, tempo di `healthy`, comportamento dell'entrypoint su volume
popolato — entrano come `V-0NN` con comando e output.

- [ ] **Passo 3 — `make docs-check` e `make stack-check`**

Entrambi `0`.

- [ ] **Passo 4 — Commit**

---

## Task 13 — Chiusura del branch

- [ ] **Passo 1 — La verifica completa**

`make tools-test`, `make docs-check`, `make stack-check`, `make images-verify`,
`make preflight`, `make up-01 && make smoke-01 && make down-01`. Tutti `0`.

- [ ] **Passo 2 — La prova che conta: la rete staccata**

Con il Wi-Fi spento e `PULL_POLICY=never`: `make up-01` deve **funzionare**. È il vincolo per
cui esiste [ADR-0009](../Decision.md#adr-0009), e la sola verifica che riproduce le condizioni
del 18 settembre.

- [ ] **Passo 3 — Il registro operativo**

La voce del branch, **compresi i fallimenti**. La sezione «Fallito» non è facoltativa: nella
voce di `feature/00` è la parte che ha reso possibile trovare due difetti reali.

- [ ] **Passo 4 — Le citazioni per le slide**

Le frasi emerse scrivendo, in [`citazioni-riportare-slide.md`](../citazioni-riportare-slide.md).
Si raccolgono adesso, non a fine progetto.

- [ ] **Passo 5 — PR #2**

Base **`develop`**, non `main`: il 2026-08-28 `develop` ha ricevuto l'intero
`feature/00-fondamenta` e questo branch parte da lì. Corpo che racconta cosa c'è, cosa manca e
come si verifica, con la tabella dei criteri di completamento.

---

## Criterio di completamento

Il branch è finito quando:

1. `make stack-check` esce `0` e le otto regole del Task 1 hanno ciascuna il proprio test.
2. `make up-01` funziona **con la rete disattivata** e `PULL_POLICY=never`.
3. `make smoke-01` verifica dal vivo ciò che il file dichiara, e dice a voce alta che
   l'istanza accetta connessioni senza credenziali.
4. Le sei pagine assegnate a `feature/01` nell'indice [`docs/README.md`](../README.md)
   esistono, e la colonna «Branch» diventa un collegamento.
5. `make docs-check` esce `0`: nessuna fonte orfana, nessun ADR senza fonti.
6. Chi clona il repository avvia lo stack seguendo il solo `README.md`.

Se il calendario stringe, i task rinviabili in ordine di rinuncia sono **11** (installazione
su Linux e Windows: interessa il pubblico, non la demo), poi **10** (la guida `mongosh` può
nascere in `feature/02`, dove i comandi di amministrazione si possono finalmente eseguire).
**Non** sono rinviabili il Task 1 — è la porta che i due stack successivi devono attraversare,
e nasce adesso o non nasce — né il Task 8, perché le due trappole che porta sono già debito di
`feature/00` e un debito rinviato due volte è un debito perso.

---

## Nota di calendario

Il piano di progetto assegna a questo branch due giorni, giovedì 27 e venerdì 28 agosto, ed è
un dimensionamento fatto quando il branch sembrava «un `mongod` in Compose». I tredici task
qui sopra non ci stanno in due giorni: sei pagine di documentazione, uno strumento nuovo in
TDD e una misura da fare sui log sono, a occhio, tre o quattro giornate. Il ritardo va
dichiarato adesso e assorbito dove costa meno — la scala di rinuncia del criterio di
completamento serve a questo — invece di scoprirlo lunedì. La decisione su cosa tagliare è
del Product Owner.
