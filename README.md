# MongoDB: dalla singola istanza al cluster

Un laboratorio riproducibile che porta MongoDB dalla singola istanza al replica set allo
sharded cluster, tre stack Docker Compose sulla stessa macchina, più un'applicazione
Python che ne mostra il comportamento sotto guasto e sotto carico. È il materiale del talk
omonimo a **SqlStart 2026**, e resta consultabile per conto proprio da chi al talk non era.

Serve a chi amministra o sviluppa su MongoDB e vuole vedere, non sentir raccontare, cosa
cambia fra le tre architetture: chi risponde quando un nodo cade, cosa costa un backup a
caldo, come si comporta la latenza quando le connessioni concorrenti crescono.

## Il talk

**SqlStart 2026** — Ancona, venerdì 18 settembre 2026. Sessanta minuti, di cui circa metà
di dimostrazioni dal vivo.

Il repository è più esteso di quanto entri in un'ora, per scelta: i criteri di rinuncia
valgono per l'esecuzione dal palco, non per il materiale scritto. Chi c'era e vuole
approfondire trova qui proprio le parti che dal vivo sono state saltate.

## Cosa contiene

| Cartella | Contenuto |
|---|---|
| [`docs/`](docs/README.md) | tutta la documentazione: architetture, installazione, amministrazione, `mongosh`, decisioni e fonti |
| `docker/` | i tre stack Compose, uno per architettura |
| `app/` | l'applicazione dimostrativa in Python |
| `tools/` | strumenti di repository: preflight, pre-scaricamento delle immagini, verifica delle citazioni |

Due file meritano una menzione a parte, perché sono il modo in cui questo materiale prova
quello che afferma:

- [`docs/Sources.md`](docs/Sources.md) — ogni fonte consultata con URL, versione
  documentata, data, un verdetto su cosa la pagina afferma davvero e le **riserve**, cioè
  il punto in cui smette di coprirci. Nessuna affermazione tecnica entra nella
  documentazione senza un riferimento qui.
- [`docs/Decision.md`](docs/Decision.md) — le decisioni architetturali in ordine
  cronologico, con contesto, conseguenze e alternative scartate. Le decisioni superate
  restano, con il rimando a quella che le sostituisce.

Il legame fra le due è verificato da un controllo automatico che fallisce se un ADR cita
una fonte inesistente o se una fonte non è citata da nessuno.

## Stato di avanzamento

Il repository è in costruzione fino a metà settembre 2026. Questo è quello che c'è oggi:

| Stack | Stato | Branch |
|---|---|---|
| `docker/01-standalone` | in lavorazione | `feature/01-stack-standalone` |
| `docker/02-replicaset` | in lavorazione | `feature/02-stack-replicaset` |
| `docker/03-sharded` | in lavorazione | `feature/03-stack-sharded` |

Anche l'applicazione Python in `app/` è in lavorazione, su `feature/04-app-python`. In
questo momento sono pronti solo l'impianto documentale e gli strumenti di repository: le
sezioni della documentazione non ancora scritte sono elencate
nell'[indice](docs/README.md) con la feature che le produrrà.

## Requisiti

- **Docker Desktop** o un runtime equivalente che fornisca `docker compose`. Gli stack sono
  stati sviluppati con Docker 29.7.2 e Compose v5.4.0.
- **RAM.** Lo standalone e il replica set stanno comodi in 4 GiB assegnati al runtime. Lo
  sharded cluster completo no: è stato sviluppato su una VM Docker da 7,65 GiB, ricavata da
  un host con 16 GiB [V-002](docs/Sources.md#v-002), e per questo lo stack sharded ha due
  profili di dimensione diversa.
- **`make`** per i comandi di uso quotidiano, e **[`uv`](https://docs.astral.sh/uv/)** per
  eseguire gli strumenti Python senza installare nulla a mano.

## Avvio rapido

Gli stack Compose non sono ancora nel repository: appena ci saranno, i comandi per
avviarli compariranno qui. Per ora quello che si può eseguire su un clone appena fatto è
l'impianto documentale.

```bash
git clone https://github.com/giulianolatini/SqlStart2026.git
cd SqlStart2026

# Verifica che ogni ADR citi fonti esistenti e che nessuna fonte sia orfana.
uv run --project tools python tools/check_citations.py docs/Decision.md docs/Sources.md

# Esegue la suite degli strumenti di repository.
uv run --directory tools pytest -q
```

Il primo dei due comandi scarica le dipendenze di sviluppo alla prima esecuzione, quindi
vuole rete una volta sola.

## Licenza

[GPL-3.0](LICENSE). Il materiale è pensato per essere riusato: se lo porti in aula o in
azienda, la licenza chiede solo che resti libero.
