# Indice della documentazione

Materiale del talk **MongoDB: dalla singola istanza al cluster** — SqlStart 2026, Ancona,
venerdì 18 settembre 2026.

Questa cartella contiene la documentazione del progetto: il talk, gli stack, le decisioni, le
fonti e il registro operativo. Fuori da qui stanno due cose sole, ed entrambe per una ragione:
il [`README.md`](../README.md) di radice, che serve a chi arriva dal talk e vuole capire in
trenta secondi cosa ha davanti, e [`app/docs/`](../app/docs/README.md), che spiega
l'applicazione `mongolab` **accanto al suo codice**, perché sono pagine che si leggono con i
sorgenti aperti nella finestra di fianco. Quelle pagine citano queste e non le duplicano; il
controllo dei collegamenti percorre entrambe le cartelle.

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
| [`2026-09-01-piano-feature-03-stack-sharded.md`](00-progetto/2026-09-01-piano-feature-03-stack-sharded.md) | il piano della quarta feature: lo sharded cluster a due shard, la catena di inizializzazione in undici container, la shard key sbagliata da provare con i numeri e i debiti che lo spike aveva lasciato aperti | già nel repository |
| [`2026-09-02-piano-feature-04-app-python.md`](00-progetto/2026-09-02-piano-feature-04-app-python.md) | il piano della quinta feature: l'applicazione Python, il dominio provato senza Docker, le tre scene del Blocco 2 e i debiti di misura che quattro pagine le hanno intestato | già nel repository |
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
| [`02-architetture/sharded-cluster.md`](02-architetture/sharded-cluster.md) | sharded cluster a due shard: la decisione che non si disfa, i tre ruoli, la shard key sbagliata provata con i numeri, il balancer che fonde i chunk e non migra mai, la trappola dell'`insertMany` ordinato | già nel repository |
| [`02-architetture/trappole-mongodb-in-docker.md`](02-architetture/trappole-mongodb-in-docker.md) | i punti in cui MongoDB e Docker si fraintendono, una voce per sintomo: undici alla nascita, tredici da `02` (permessi del keyfile, scoperta della topologia), ventuno con `03` (il volume del config server, i chunk che si fondono da soli, l'eccezione localhost aperta shard per shard e come si chiude) | già nel repository |

## 03-amministrazione — le procedure

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| [`03-amministrazione/backup-restore.md`](03-amministrazione/backup-restore.md) | `mongodump`/`mongorestore`, il dump a caldo con `--oplog` e quale punto nel tempo garantisce, il restore contato, il fallimento per finestra di oplog mostrato mentre fallisce, e sullo sharded cluster il divieto di `--oplog` con le sue due facce e il restore che riporta i dati senza la distribuzione | già nel repository |
| [`03-amministrazione/sicurezza-keyfile-x509.md`](03-amministrazione/sicurezza-keyfile-x509.md) | autenticazione interna: perché `--keyFile` porta con sé il controllo degli accessi, perché MongoDB riserva il keyfile a test e sviluppo, la sequenza verso X.509 eseguita con i suoi rifiuti, dove vivono gli utenti di un replica set, e su uno sharded cluster l'eccezione localhost aperta su ogni shard che non ha utenti, con la procedura del manuale per l'amministratore per shard e le tre semplificazioni che questo lab si prende al suo posto | già nel repository |
| [`03-amministrazione/statistiche-monitoraggio.md`](03-amministrazione/statistiche-monitoraggio.md) | `serverStatus`, `dbStats`, metriche di replica, cosa guardare sotto carico; organizzata attorno a sei misure che smentiscono la lettura ingenua — le sezioni che al `mongos` mancano, le code che restano vuote sotto carico, il ritardo di replica che vale 10 000 ms su un insieme sano, e il router che dichiara un disco grande il doppio | già nel repository |
| [`03-amministrazione/log.md`](03-amministrazione/log.md) | il formato JSON campo per campo, le severità e i componenti misurati, `logRotate` in container, cosa cercare durante un'elezione: gli `id` delle tre cause, misurati su `02`, e le tre prime righe che distinguono un guasto da una manutenzione | già nel repository |

## 04-mongosh — la shell

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| [`04-mongosh/guida-mongosh.md`](04-mongosh/guida-mongosh.md) | connettersi da dentro il container e i tre parametri che `mongosh` sceglie da sé, comandi di uso quotidiano, comandi di amministrazione: quelli del replica set eseguiti su `02`, quelli dello sharded cluster eseguiti su `03` con le risposte che la marcatura nascondeva, script non interattivi e la tabella dei codici di uscita | già nel repository |

## 05-talk — il palco

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| [`05-talk/runbook-demo.md`](05-talk/runbook-demo.md) | documento unico del talk: preflight e stato atteso dei dati, copione minuto per minuto dei tre blocchi con i comandi esatti e l'output misurato che ci si aspetta, quando si passa alle registrazioni, tabella sintomo → azione; criteri di rinuncia di scena in appendice A e comandi di emergenza in appendice B ([ADR-0015](Decision.md#adr-0015)) | già nel repository |
| [`05-talk/registrazioni/`](05-talk/registrazioni/README.md) | indice dei filmati di riserva e delle registrazioni di terminale. Quattordici scene di terminale sono nel repository — quattro del replica set, cinque dell'applicazione `mongolab` sullo stesso stack, cinque dello sharded cluster; i filmati stanno sul canale YouTube del relatore, con copia locale obbligatoria ([ADR-0016](Decision.md#adr-0016), [ADR-0050](Decision.md#adr-0050)) | già nel repository |

## 06-sviluppo — come è fatto il lab

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| [`06-sviluppo/gestione-risorse-compose.md`](06-sviluppo/gestione-risorse-compose.md) | `mem_limit` e `cpus`, la cache WiredTiger nei container, come si dimostra che i limiti sono applicati; i due profili dello sharded cluster — a chi serve ciascuno, quanto costa, come si sceglie | già nel repository |
| [`06-sviluppo/worktree-e-branch-di-lavoro.md`](06-sviluppo/worktree-e-branch-di-lavoro.md) | come si apre un branch di feature con il suo worktree e come lo si chiude dopo la PR; l'ordine vincolante della rimozione, e come si esce se una sessione è rimasta agganciata a un worktree cancellato | già nel repository |
| [`06-sviluppo/architettura-app.md`](06-sviluppo/architettura-app.md) | stratificazione dell'applicazione, porte, modello a eventi, composition root; racconta a chi non apre i sorgenti quello che [`app/docs/`](../app/docs/README.md) spiega a chi li apre, e mostra che cosa quella forma ha reso: 634 prove in quattro secondi, con Docker irraggiungibile | già nel repository |
| [`06-sviluppo/tdd-e-doppi.md`](06-sviluppo/tdd-e-doppi.md) | separazione fra suite unitaria e di integrazione, fake contro mock, come si prova il failover senza aspettarlo; il contratto condiviso che ha smascherato due bugiardi, di cui uno era MongoDB. Rimanda a [`app/docs/05-tipi-prove-e-guardie.md`](../app/docs/05-tipi-prove-e-guardie.md) invece di ripeterlo | già nel repository |
| [`06-sviluppo/concetti-generali/`](06-sviluppo/concetti-generali/README.md) | il flusso di lavoro importato dal repository d'origine il 6 settembre 2026: da dove viene, quali delle dodici skill di `.claude/skills/` governano qui e quali no, e la regola che le tiene innocue — in conflitto con una scheda accettata di [`Decision.md`](Decision.md), vince la scheda | già nel repository |
| [`06-sviluppo/concetti-generali/introduzione-flusso-di-lavoro.md`](06-sviluppo/concetti-generali/introduzione-flusso-di-lavoro.md) | *Dall'idea al software funzionante*, v3.1, verbatim: commit atomici contro commit raggruppati, ADR e razionale, pull request, review, piano di lavoro, politiche di branching — sei temi con bibliografia annotata. **Testo di riferimento: descrive pratiche che questo repository in parte non segue** | già nel repository |
| [`06-sviluppo/concetti-generali/runbook-installazione-skill.md`](06-sviluppo/concetti-generali/runbook-installazione-skill.md) | come si installano e si collaudano le skill, installazione personale o di progetto; in coda «Il caso di SqlStart2026», che racconta l'installazione di qui e le 127 prove passate | già nel repository |
| [`06-sviluppo/concetti-generali/esempio-adr-0001.md`](06-sviluppo/concetti-generali/esempio-adr-0001.md) | l'ADR di riferimento prodotto dal collaudo delle skill, verbatim: serve a vedere che forma deve avere il risultato. Il percorso che nomina, `docs/adr/0001-<slug>.md`, è quello del repository d'origine — qui le schede stanno tutte in [`Decision.md`](Decision.md) | già nel repository |

## revisioni — le review esterne, arbitrate

I sei fascicoli della revisione generale di `release/1.0`, uno per perimetro. **72 rilievi**
sollevati da due revisori esterni indipendenti — Codex 45, Gemini Pro 27 — **50 accolti e 22
respinti**. Un rilievo qui non si chiude leggendo il codice: si chiude **eseguendo**, e il verdetto
riporta la misura che lo conferma o lo smentisce ([ADR-0135](Decision.md#adr-0135)).

Il dato che vale più dei rilievi: **14 dei 22 respinti non parlavano del repository, ma delle
istruzioni date ai revisori**. Undici sono lo stesso rilievo sull'«ambito obbligatorio» dei commit,
sollevato da tutti e due i revisori in tutti e sei i fascicoli — che due revisori indipendenti
concordino non aumenta la fondatezza di un rilievo, se leggono lo stesso prompt: l'accordo misura
la fonte comune. Le righe che li producevano sono state corrette **prima** della revisione
successiva.

| Pagina | Contenuto | Disponibile da |
|---|---|---|
| [`revisioni/2026-09-06-talk.md`](revisioni/2026-09-06-talk.md) | il runbook della demo e l'indice delle registrazioni: 17 rilievi, 12 accolti e 5 respinti | già nel repository |
| [`revisioni/2026-09-06-stack-docker.md`](revisioni/2026-09-06-stack-docker.md) | i tre stack Compose con i loro script di inizializzazione: 7 rilievi, 3 accolti e 4 respinti | già nel repository |
| [`revisioni/2026-09-06-documentazione-tecnica.md`](revisioni/2026-09-06-documentazione-tecnica.md) | installazione, architetture, amministrazione e `mongosh`: 9 rilievi, 7 accolti e 2 respinti | già nel repository |
| [`revisioni/2026-09-06-strumenti.md`](revisioni/2026-09-06-strumenti.md) | `tools/`, il `Makefile` e il `README.md` di radice: 18 rilievi, 12 accolti e 6 respinti — il fascicolo con i tre rilievi di gravità alta | già nel repository |
| [`revisioni/2026-09-06-app-sorgenti.md`](revisioni/2026-09-06-app-sorgenti.md) | i sorgenti di `mongolab`: 12 rilievi, 10 accolti e 2 respinti | già nel repository |
| [`revisioni/2026-09-06-app-prove.md`](revisioni/2026-09-06-app-prove.md) | le prove di `mongolab`: 9 rilievi, 6 accolti e 3 respinti — cinque prove erano verdi dentro il guasto che dichiaravano di sorvegliare | già nel repository |

## Dove sta il resto

| Cartella | Contenuto |
|---|---|
| `docker/` | i tre stack Compose: `01-standalone`, `02-replicaset`, `03-sharded` |
| `app/` | l'applicazione dimostrativa in Python, con la propria documentazione in [`app/docs/`](../app/docs/README.md): principi di funzionamento, registro di sviluppo, decisioni vincolanti e fonti proprie ([ADR-0081](Decision.md#adr-0081)) |
| `tools/` | strumenti di repository: preflight, pre-scaricamento delle immagini, e i tre controllori che tengono gli artefatti allineati alle decisioni — citazioni, file Compose, collegamenti ([ADR-0038](Decision.md#adr-0038)) |
