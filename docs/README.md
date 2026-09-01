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
inesistente o se una fonte non è citata da nessun ADR. Accanto gira
`tools/check_links.py`, che riapre ogni collegamento relativo di queste pagine e verifica
che il file esista e che l'ancora ci sia davvero — comprese quelle che nessuno ha
dichiarato, perché le genera GitHub dal titolo. I due controlli stanno in `make docs-check`,
e la ragione per cui esistono è [ADR-0038](Decision.md#adr-0038).

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
| [`2026-08-28-piano-feature-01-stack-standalone.md`](00-progetto/2026-08-28-piano-feature-01-stack-standalone.md) | il piano della seconda feature: lo stack a istanza singola, la verifica eseguibile sui file Compose e le sei pagine di documentazione dovute | già nel repository |
| [`2026-08-31-piano-feature-02-stack-replicaset.md`](00-progetto/2026-08-31-piano-feature-02-stack-replicaset.md) | il piano della terza feature: il replica set a tre membri, la catena di inizializzazione sotto keyfile, la demo di failover e i quattro debiti che i due branch precedenti gli hanno intestato | già nel repository |
| [`2026-08-25-spike-sharded.md`](00-progetto/2026-08-25-spike-sharded.md) | il verbale dello spike: il file Compose che ha funzionato, la memoria misurata sugli undici container, i tre punti in cui il design si era sbagliato, e la versione di MongoDB che su Docker Desktop non parte | già nel repository |
| [`limiti-noti.md`](00-progetto/limiti-noti.md) | i confini dichiarati: dove il lab semplifica, dove la documentazione ufficiale non copre, quali affermazioni diffuse non risultano scritte | già nel repository |

## 01-installazione — istanza singola, fuori da Docker

Il lab gira in container, ma la domanda «e su una macchina vera?» arriva sempre. Queste due
pagine rispondono con le procedure ufficiali, e portano entrambe una riserva in testa: non
sono state eseguite qui, perché qui non c'è né un Ubuntu né un Windows
([ADR-0037](Decision.md#adr-0037)).

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| [`01-installazione/linux.md`](01-installazione/linux.md) | installazione su Ubuntu dal repository ufficiale, che cosa compare sul sistema, il servizio `systemd`, e la messa a punto che nessuno fa — `bindIp`, `ulimit`, THP, filesystem, swap, NUMA; in coda il contrasto misurato con il container del lab, che è la stessa installazione senza `systemd` | già nel repository |
| [`01-installazione/windows.md`](01-installazione/windows.md) | installazione con il `.msi`, il servizio di Windows, la shell che va installata a parte, e le differenze che contano — WSL non supportato, `ulimit` e THP che non esistono, i permessi del keyfile che su Windows non vengono controllati | già nel repository |

## 02-architetture — le tre modalità

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| [`02-architetture/standalone.md`](02-architetture/standalone.md) | istanza singola: i quattro limiti con la fonte che li sostiene, quando basta davvero, il file Compose riga per riga | già nel repository |
| [`02-architetture/replica-set.md`](02-architetture/replica-set.md) | replica set a tre membri: perché tre e non due, le elezioni cronometrate nelle tre scene, write concern e read preference come coppia, il confronto con l'istanza singola, il file Compose riga per riga | già nel repository |
| `02-architetture/sharded-cluster.md` | mongos, config server, shard key, bilanciamento; i due profili dello stack | `feature/03-stack-sharded` |
| [`02-architetture/trappole-mongodb-in-docker.md`](02-architetture/trappole-mongodb-in-docker.md) | i punti in cui MongoDB e Docker si fraintendono, una voce per sintomo: undici alla nascita, tredici da `02` (permessi del keyfile, scoperta della topologia), ampliata ancora da `03` | già nel repository |

## 03-amministrazione — le procedure

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| [`03-amministrazione/backup-restore.md`](03-amministrazione/backup-restore.md) | `mongodump`/`mongorestore`, il dump a caldo con `--oplog` e quale punto nel tempo garantisce, il restore contato, e il fallimento per finestra di oplog mostrato mentre fallisce | già nel repository |
| [`03-amministrazione/sicurezza-keyfile-x509.md`](03-amministrazione/sicurezza-keyfile-x509.md) | autenticazione interna: perché `--keyFile` porta con sé il controllo degli accessi, perché MongoDB riserva il keyfile a test e sviluppo, la sequenza verso X.509 eseguita con i suoi rifiuti, e dove vivono gli utenti di un replica set | già nel repository |
| `03-amministrazione/statistiche-monitoraggio.md` | `serverStatus`, `dbStats`, metriche di replica, cosa guardare sotto carico | `feature/04-app-python` |
| [`03-amministrazione/log.md`](03-amministrazione/log.md) | il formato JSON campo per campo, le severità e i componenti misurati, `logRotate` in container, cosa cercare durante un'elezione: gli `id` delle tre cause, misurati su `02`, e le tre prime righe che distinguono un guasto da una manutenzione | già nel repository |

## 04-mongosh — la shell

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| [`04-mongosh/guida-mongosh.md`](04-mongosh/guida-mongosh.md) | connettersi da dentro il container e i tre parametri che `mongosh` sceglie da sé, comandi di uso quotidiano, comandi di amministrazione: quelli del replica set eseguiti su `02`, quelli dello sharded cluster ancora solo scritti (dovuti a `03`), script non interattivi e la tabella dei codici di uscita | già nel repository |

## 05-talk — il palco

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| `05-talk/runbook-demo.md` | documento unico del talk: scaletta, comandi, tempi, piani di ripiego, criteri di rinuncia in appendice ([ADR-0015](Decision.md#adr-0015)) | `release/1.0` |
| [`05-talk/registrazioni/`](05-talk/registrazioni/README.md) | indice dei filmati di riserva e delle registrazioni di terminale. Quattro scene di terminale sono nel repository; i filmati stanno sul canale YouTube del relatore, con copia locale obbligatoria ([ADR-0016](Decision.md#adr-0016), [ADR-0050](Decision.md#adr-0050)) | già nel repository |

## 06-sviluppo — come è fatto il lab

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| [`06-sviluppo/gestione-risorse-compose.md`](06-sviluppo/gestione-risorse-compose.md) | `mem_limit` e `cpus`, la cache WiredTiger nei container, come si dimostra che i limiti sono applicati; i due profili dello sharded cluster — a chi serve ciascuno, quanto costa, come si sceglie | già nel repository |
| `06-sviluppo/architettura-app.md` | stratificazione dell'applicazione, porte, modello a eventi, composition root | `feature/04-app-python` |
| `06-sviluppo/tdd-e-doppi.md` | separazione fra suite unitaria e di integrazione, fake contro mock, come si prova il failover senza aspettarlo | `feature/04-app-python` |

## Dove sta il resto

| Cartella | Contenuto |
|---|---|
| `docker/` | i tre stack Compose: `01-standalone`, `02-replicaset`, `03-sharded` |
| `app/` | l'applicazione dimostrativa in Python |
| `tools/` | strumenti di repository: preflight, pre-scaricamento delle immagini, e i tre controllori che tengono gli artefatti allineati alle decisioni — citazioni, file Compose, collegamenti ([ADR-0038](Decision.md#adr-0038)) |
