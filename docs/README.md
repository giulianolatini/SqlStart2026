# Indice della documentazione

Materiale del talk **MongoDB: dalla singola istanza al cluster** — SqlStart 2026, Ancona,
venerdì 18 settembre 2026.

Questa cartella contiene tutta la documentazione del progetto. L'unico file Markdown fuori
da qui è il [`README.md`](../README.md) di radice, che serve a chi arriva dal talk e vuole
capire in trenta secondi cosa ha davanti.

## Come si legge

Il repository è più esteso di quanto entri in sessanta minuti, e lo è per scelta: i criteri
di rinuncia valgono per l'esecuzione dal vivo, non per il materiale scritto
([ADR-0017](Decision.md#adr-0017)). Chi ha assistito al talk e vuole approfondire troverà
qui proprio le parti che dal palco sono state saltate.

**Ogni affermazione tecnica cita una fonte.** Il vincolo non è decorativo: `Sources.md`
registra per ciascuna voce URL, editore, versione documentata, data di consultazione, un
verdetto su cosa la pagina afferma davvero e le **riserve**, cioè il punto in cui la fonte
smette di coprirci. La gerarchia con cui le fonti si pesano è
[ADR-0024](Decision.md#adr-0024). Il legame fra decisioni e fonti è verificato da un
controllo automatico, `tools/check_citations.py`, che fallisce se un ADR cita una fonte
inesistente o se una fonte non è citata da nessun ADR.

Le pagine non ancora scritte compaiono comunque in questo indice, con la feature che le
produrrà. Un indice che promette senza datare invecchia male.

## Registri trasversali

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| [`Decision.md`](Decision.md) | le decisioni architetturali in ordine cronologico, con contesto, conseguenze e alternative scartate | già nel repository |
| [`Sources.md`](Sources.md) | le fonti consultate, con verdetto e riserve per ciascuna | già nel repository |
| [`registro-operativo-sviluppo.md`](registro-operativo-sviluppo.md) | il diario: cosa è stato fatto, cosa è fallito, cosa se ne è imparato | già nel repository |
| [`citazioni-riportare-slide.md`](citazioni-riportare-slide.md) | le citazioni letterali che meritano una slide, raccolte man mano | già nel repository |

## 00-progetto — come è stato progettato

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| [`2026-08-24-design.md`](00-progetto/2026-08-24-design.md) | il documento di design: vincoli, architetture, applicazione, impianto documentale, piano di lavoro | già nel repository |
| [`2026-08-25-piano-feature-00-fondamenta.md`](00-progetto/2026-08-25-piano-feature-00-fondamenta.md) | il piano di implementazione della prima feature, passo per passo | già nel repository |
| [`limiti-noti.md`](00-progetto/limiti-noti.md) | i confini dichiarati: dove il lab semplifica, dove la documentazione ufficiale non copre, quali affermazioni diffuse non risultano scritte | già nel repository |

## 01-installazione — istanza singola, fuori da Docker

Il lab gira in container, ma la domanda «e su una macchina vera?» arriva sempre. Queste due
pagine rispondono con le procedure ufficiali.

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| `01-installazione/linux.md` | installazione di un'istanza singola su Linux, servizio, percorsi, configurazione iniziale | `feature/01-stack-standalone` |
| `01-installazione/windows.md` | installazione di un'istanza singola su Windows, servizio, differenze rispetto a Linux | `feature/01-stack-standalone` |

## 02-architetture — le tre modalità

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| `02-architetture/standalone.md` | istanza singola: quando basta, cosa non garantisce | `feature/01-stack-standalone` |
| `02-architetture/replica-set.md` | topologia, elezioni, read preference, write concern, ritardo di replica | `feature/02-stack-replicaset` |
| `02-architetture/sharded-cluster.md` | mongos, config server, shard key, bilanciamento; i due profili dello stack | `feature/03-stack-sharded` |
| `02-architetture/trappole-mongodb-in-docker.md` | i punti in cui MongoDB e Docker si fraintendono: nomi host, scoperta della topologia, permessi del keyfile, volumi già popolati | `feature/01-stack-standalone`, ampliata da `02` e `03` |

## 03-amministrazione — le procedure

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| `03-amministrazione/backup-restore.md` | `mongodump`/`mongorestore`, backup a caldo con `--oplog` e i suoi limiti, restore verificato | `feature/02-stack-replicaset` |
| `03-amministrazione/sicurezza-keyfile-x509.md` | autenticazione interna: perché il lab usa il keyfile, perché MongoDB lo riserva a test e sviluppo, e come si passa a X.509 in produzione | `feature/02-stack-replicaset` |
| `03-amministrazione/statistiche-monitoraggio.md` | `serverStatus`, `dbStats`, metriche di replica, cosa guardare sotto carico | `feature/04-app-python` |
| `03-amministrazione/log.md` | formato dei log, livelli, cosa cercare durante un'elezione | `feature/01-stack-standalone` |

## 04-mongosh — la shell

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| `04-mongosh/guida-mongosh.md` | connessione, comandi di uso quotidiano, comandi di amministrazione del replica set e dello sharded cluster, script non interattivi | `feature/01-stack-standalone` |

## 05-talk — il palco

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| `05-talk/runbook-demo.md` | documento unico del talk: scaletta, comandi, tempi, piani di ripiego, criteri di rinuncia in appendice ([ADR-0015](Decision.md#adr-0015)) | `release/1.0` |
| `05-talk/registrazioni/` | indice dei filmati di riserva e delle registrazioni di terminale. I filmati stanno sul canale YouTube del relatore, con copia locale obbligatoria ([ADR-0016](Decision.md#adr-0016)) | `feature/02-stack-replicaset` |

## 06-sviluppo — come è fatto il lab

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| `06-sviluppo/gestione-risorse-compose.md` | `mem_limit` e `cpus`, la cache WiredTiger nei container, come si dimostra che i limiti sono applicati; i due profili dello sharded cluster — a chi serve ciascuno, quanto costa, come si sceglie | `feature/00-fondamenta` |
| `06-sviluppo/architettura-app.md` | stratificazione dell'applicazione, porte, modello a eventi, composition root | `feature/04-app-python` |
| `06-sviluppo/tdd-e-doppi.md` | separazione fra suite unitaria e di integrazione, fake contro mock, come si prova il failover senza aspettarlo | `feature/04-app-python` |

## Dove sta il resto

| Cartella | Contenuto |
|---|---|
| `docker/` | i tre stack Compose: `01-standalone`, `02-replicaset`, `03-sharded` |
| `app/` | l'applicazione dimostrativa in Python |
| `tools/` | strumenti di repository: preflight, pre-scaricamento delle immagini, verifica delle citazioni |
