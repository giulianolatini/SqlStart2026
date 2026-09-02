# Piano di implementazione — `feature/03-stack-sharded`

> **Per chi esegue il piano:** i passi usano caselle `- [ ]` da spuntare. Ogni task termina
> con un deliverable verificabile e un commit. Questo piano attua decisioni già prese
> altrove e non le rimette in discussione; dove se ne prende una nuova, è dichiarato nel
> task.

---

**Obiettivo:** produrre il terzo e ultimo stack Compose — lo sharded cluster a due profili —
la pagina che lo spiega, la scena di otto minuti del Blocco 3, e la chiusura dei debiti che
`feature/00`, `feature/01` e `feature/02` hanno intestato per iscritto a questo branch.

**Architettura:** questo branch non parte dalla pagina bianca, e la differenza è tutta qui.
Lo spike del 25 agosto ha **già montato la topologia completa e l'ha misurata**
([verbale](2026-08-25-spike-sharded.md)): undici container, la catena di inizializzazione
completa, `sh.status()` con due shard attivi, 20.000 documenti distribuiti al 50,7 % / 49,3 %
fra i due shard, e il failover di uno shard provato con 50.000 letture e una scrittura
riuscite a nodo giù. Il file Compose che ha funzionato è nel §8 del verbale, non nel
repository, e il verbale stesso dice perché: «da riportare in `docker/03-sharded/` quando la
feature sarà avviata». Questo branch è quel momento. Il compito di questo branch non è scoprire se
la topologia funziona — è **portarla dentro** con le regole del repository addosso: profili,
pinning per digest, healthcheck che aspettano un servizio operativo, un controllore che
sappia leggerla, e la documentazione che la spiega.

La catena di inizializzazione è la stessa di `feature/02` **con un anello in più**.
[ADR-0026](../Decision.md#adr-0026) lo aveva scritto in anticipo — «le due feature
condividono il meccanismo e vanno scritte per condividerlo» — e
[ADR-0040](../Decision.md#adr-0040) ha già scelto la forma, il namespace di rete condiviso,
dopo aver montato e misurato tutte e tre le alternative ([V-023](../Sources.md#v-023)).
**Quel confronto non si rifà.** La domanda di questo branch è più piccola: se la stessa forma
regge con `mongos` davanti e `sh.addShard()` in coda.

**Stack tecnico:** Compose Specification (senza chiave `version:`), MongoDB **7.0.40**
dall'immagine ufficiale pinnata per digest, `mongosh`, Bash (`set -euo pipefail`), Python
3.13+ con `pytest` per gli strumenti di repository, GNU Make, Markdown.

**Specifica:** [`docs/00-progetto/2026-08-24-design.md`](2026-08-24-design.md) §5.1 (bilancio
delle risorse), §5.2 (mappa delle porte), §5.5 (stack 03), §7 (Blocco 3 del talk). Il verbale
dello spike è la seconda specifica, e per la topologia è quella che comanda.

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
  `pull_policy: never` **scritto fisso nel file**, mai da variabile
  ([ADR-0039](../Decision.md#adr-0039)); nessuna immagine usa il tag `latest`.
- **MongoDB 7.0.40**, immagine ufficiale pinnata **per digest** tramite
  [`tools/images.env`](../../tools/images.env). La verifica del 1º settembre
  ([V-051](../Sources.md#v-051)) ha stabilito che la 8.0.30 non esiste:
  [ADR-0058](../Decision.md#adr-0058) fissa la 7.0.40 per questo branch e sposta il prossimo
  controllo al 16 settembre. Il digest non si scrive a mano nei file Compose.
- **Compose:** Specification corrente, **senza** chiave `version:`. Sintassi breve
  `mem_limit` / `cpus` nei file ([ADR-0013](../Decision.md#adr-0013)).
- **Risorse,** da §5.1 del design: config server **512m**, ogni membro di shard **640m**,
  ogni `mongos` **384m**; `--wiredTigerCacheSizeGB 0.25` esplicito su ogni `mongod`, **0.5**
  CPU. Totale `palco` ~2,2 GiB su 4 container, `completo` ~6,0 GiB su 11
  ([ADR-0004](../Decision.md#adr-0004)).
- **Porte host,** da §5.2 del design: `mongos` **27117** (e **27118** nel profilo
  `completo`), config server **27131**–**27133**, shard 1 **27141**–**27143**, shard 2
  **27151**–**27153**. Vanno aggiunte all'elenco che `tools/preflight.sh` controlla.
- **Nomi host:** mai indirizzi IP ([ADR-0021](../Decision.md#adr-0021)). Qui il vincolo morde
  due volte: i membri si registrano con il nome con cui sono elencati, e `sh.addShard()`
  registra nel config server una stringa che i client useranno.
- **Ordine di avvio:** `depends_on` con `condition:`, mai `sleep`
  ([ADR-0023](../Decision.md#adr-0023)).
- **Indipendenza degli stack:** progetto Compose, rete e volumi propri, nessun `include` né
  profilo condiviso con gli altri due ([ADR-0003](../Decision.md#adr-0003)).
- **Il keyfile non entra nel repository,** in nessuna forma e in nessun momento
  ([ADR-0014](../Decision.md#adr-0014)). Il `.env` con la password **vive nel checkout
  principale**, non in un worktree ([ADR-0056](../Decision.md#adr-0056)).
- **Lo stack è un argomento, non un ramo nel codice.** `reset-demo.sh 03` deve funzionare
  aggiungendo un caso al dispatch esistente, non riscrivendo lo strumento; lo stesso vale per
  i bersagli del `Makefile`.
- **Ciò che non si esegue si dichiara non eseguito**
  ([ADR-0037](../Decision.md#adr-0037)), anche quando la marcatura è scomoda; e **un debito si
  chiude eseguendo**, non riscrivendolo meglio ([ADR-0049](../Decision.md#adr-0049)).
- **Le trappole si aggiungono, non si riscrivono** ([ADR-0033](../Decision.md#adr-0033)), e
  una trappola misurata si scrive nel branch che l'ha misurata
  ([ADR-0052](../Decision.md#adr-0052)).
- **Commit:** stile convenzionale, corpo in italiano che spiega il perché e non il cosa.

---

## Mappa dei file

| Percorso | Responsabilità | Task |
|---|---|---|
| `docker/03-sharded/compose.yaml` | l'artefatto: config server, due shard, `mongos`, e la catena a cinque anelli | 1-4 |
| `docker/03-sharded/.env.example` | i parametri modificabili, con i valori del lab come predefiniti | 1 |
| `docker/03-sharded/init/01-keyfile.sh` | il keyfile nel volume nominato — ripreso da `02-replicaset` | 1 |
| `docker/03-sharded/init/10-cfg-initiate.js` | `rs.initiate()` del config server e creazione dell'amministratore | 2 |
| `docker/03-sharded/init/11-shard-initiate.js` | `rs.initiate()` dei due replica set di shard | 2 |
| `docker/03-sharded/init/20-add-shard.js` | `sh.addShard()` per entrambi, autenticato | 3 |
| `docker/03-sharded/init/30-dati-demo.js` | shard key, `sh.shardCollection()`, dataset deterministico | 6 |
| `tools/check_stack.py` | le regole nuove dello sharded | 5 |
| `tools/tests/test_check_stack.py` | la suite che le guida in TDD | 5 |
| `tools/smoke-sharded.sh` | prova dal vivo: shard attivi, balancer, scrittura instradata | 6 |
| `tools/reset-demo.sh` | il caso `03`, aggiunto al dispatch | 7 |
| `tools/preflight.sh` | le sette porte nuove nell'elenco dei controlli | 7 |
| `Makefile` | `up-03`, `down-03`, `reset-03`, `logs-03`, `seed-03`, `smoke-03`, `demo-03` | 7 |
| `docs/02-architetture/sharded-cluster.md` | la pagina promessa dall'indice: shard key, chunk, balancer, `mongos` | 8 |
| `docs/04-mongosh/guida-mongosh.md` | la §3.3, marcata «non eseguita», diventa eseguita | 9 |
| `docs/03-amministrazione/sicurezza-keyfile-x509.md` | gli utenti locali a uno shard e l'eccezione localhost per shard | 9 |
| `docs/03-amministrazione/backup-restore.md` | `--oplog` vietato sullo sharded, e che cosa si fa invece | 9 |
| `docs/02-architetture/trappole-mongodb-in-docker.md` | le trappole dei config server e del bilanciamento | 9 |
| `README.md` (radice) | la riga che dichiara `docker/03-sharded` «in lavorazione» | 9 |
| `docs/05-talk/registrazioni/` | la riserva del Blocco 3 | 10 |
| `docs/Decision.md`, `docs/Sources.md` | ADR e fonti del branch | 11 |
| `docs/registro-operativo-sviluppo.md` | il diario, con le note di metodo | 11 |

---

## Task 1 — Lo scheletro: `keyfile-init`, il config server, i profili

**File:** creare `docker/03-sharded/compose.yaml`, `docker/03-sharded/.env.example`,
`docker/03-sharded/init/01-keyfile.sh`.

**Interfacce prodotte:** il progetto Compose `sqlstart-03-sharded` — la forma
`sqlstart-NN-<nome>` degli altri due stack — la rete e i volumi propri, il
volume nominato del keyfile, e i nomi di servizio `cfg1`, `cfg2`, `cfg3` che i task 2 e 3
useranno testualmente.

- [ ] **Passo 1.** Copiare `docker/02-replicaset/init/01-keyfile.sh` in `03-sharded/init/` e
      leggerlo riga per riga prima di adattarlo. Non è codice nuovo: genera il keyfile con
      `openssl rand -base64 756`, lo assegna a `999:999` e lo porta a `chmod 400`
      ([S-023](../Sources.md#s-023)). Cambia solo il nome del volume.
- [ ] **Passo 2.** Scrivere lo scheletro di `compose.yaml` con `keyfile-init` **senza
      profilo** e i tre config server con `--configsvr --replSet cfgrs --keyFile`. `cfg1`
      porta `profiles: ["palco", "completo"]`; `cfg2` e `cfg3` solo `["completo"]`. La
      direzione della dipendenza — da un servizio con profilo verso uno senza — è l'unica su
      cui la documentazione di Compose si sbilancia ([S-015](../Sources.md#s-015)), ed è il
      motivo per cui `keyfile-init` resta fuori dai profili. Rileggere la riserva di
      [ADR-0010](../Decision.md#adr-0010) prima di toccare questa parte: resta aggirata per
      costruzione, non per fortuna.
- [ ] **Passo 3.** Porte `27131`–`27133`, `mem_limit: 512m`, `cpus: 0.5`,
      `--wiredTigerCacheSizeGB 0.25`, `pull_policy: never` scritto fisso, immagine da
      `${MONGO_IMAGE}`.
- [ ] **Passo 4.** Scrivere `.env.example` sul modello di `02-replicaset`, con
      `PASSWORD_AMMINISTRATORE=` **vuota** e il commento che spiega perché: la forma
      `${PASSWORD_AMMINISTRATORE:?…}` nel file Compose fa fallire l'avvio con un messaggio
      invece di partire con una password vuota.
- [ ] **Passo 5.** Verificare i profili contando i servizi, che è la misura dello spike §6:

```
docker compose --profile palco    config --services   # atteso: 2 (keyfile-init + cfg1)
docker compose --profile completo config --services   # atteso: 4
docker compose                    config --services   # atteso: 1
```

- [ ] **Passo 6.** Commit: `feat: lo scheletro dello stack 03, e il keyfile senza profilo`.

---

## Task 2 — I due shard e l'inizializzazione dei tre replica set

**File:** modificare `docker/03-sharded/compose.yaml`; creare
`init/10-cfg-initiate.js` e `init/11-shard-initiate.js`.

**Interfacce consumate:** i nomi `cfg1`–`cfg3` dal Task 1.
**Interfacce prodotte:** i nomi `shard1a`–`shard1c`, `shard2a`–`shard2c`, e i tre set
`cfgrs`, `shard1rs`, `shard2rs` che il Task 3 nomina in `sh.addShard()`.

- [ ] **Passo 1.** Aggiungere i sei `mongod` di shard con `--shardsvr --replSet shard1rs`
      (rispettivamente `shard2rs`) `--keyFile`. `shard1a` e `shard2a` portano entrambi i
      profili, gli altri quattro solo `completo`. Porte `27141`–`27143` e `27151`–`27153`,
      `mem_limit: 640m`.
- [ ] **Passo 2.** Scrivere `10-cfg-initiate.js`: `rs.initiate()` sul config server con host
      **espliciti** — i nomi dei servizi Compose, mai gli IP. Lo spike §3 lo ha già
      dimostrato necessario, e non va riscoperto.
- [ ] **Passo 3.** Nello stesso script, creare l'amministratore con `db.createUser()` sotto
      eccezione localhost. Qui vale la scoperta dello spike §2, che è già
      [ADR-0026](../Decision.md#adr-0026): **`MONGO_INITDB_ROOT_*` non funziona su un config
      server.** Non provarci di nuovo.
- [ ] **Passo 4.** Scrivere `11-shard-initiate.js` per i due set di shard. Il numero di
      membri dipende dal profilo: lo script deve leggerlo da una variabile d'ambiente, non
      dedurlo, perché nel profilo `palco` i membri sono uno per shard e `rs.initiate()` con
      tre host su un solo container avviato lascia il set senza maggioranza.
- [ ] **Passo 5.** Verificare a mano, con il profilo `palco` e poi con `completo`, che i tre
      set si formino: `rs.status().ok === 1` su ciascuno.
- [ ] **Passo 6.** Commit: `feat: i due shard, e i tre rs.initiate() che il profilo governa`.

---

## Task 3 — `mongos` e l'anello in più: `sh.addShard()`

**File:** modificare `compose.yaml`; creare `init/20-add-shard.js`.

**Interfacce consumate:** i tre nomi di replica set dal Task 2.
**Interfacce prodotte:** il servizio `mongos` sulla porta `27117`, che è il punto d'ingresso
di ogni client — smoke, dati di demo, applicazione di `feature/04`.

- [ ] **Passo 1.** Aggiungere `mongos` con
      `--configdb cfgrs/cfg1:27017,cfg2:27017,cfg3:27017` e `--keyFile`. La stringa elenca tutti
      e tre i config server **anche nel profilo `palco`**, dove `cfg2` e `cfg3` non esistono:
      `mongos` li tratta da semi, scopre la configurazione reale da `cfg1` e ignora quelli
      irraggiungibili. Non è una speranza, è la misura del §8 dello spike — con il solo `cfg1`
      acceso `mongos` diventa `healthy` e il cluster serve. **Non parametrizzare la stringa per
      profilo:** aggiungerebbe un ramo per risolvere un problema che non c'è.
- [ ] **Passo 2.** Aggiungere `mongos2` sulla porta `27118`, solo profilo `completo`. Serve a
      mostrare che i router sono più d'uno e senza stato, che è mezza slide del Blocco 3.
- [ ] **Passo 3.** Scrivere `20-add-shard.js`: `sh.addShard("shard1rs/shard1a:27017,…")` per
      entrambi, **autenticato** come amministratore. La stringa contiene i nomi dei servizi,
      e finisce nel config server: un IP qui diventerebbe un IP nella configurazione del
      cluster, non solo nel file.
- [ ] **Passo 4.** Verificare che `sh.status()` mostri due shard con `state: 1` e il balancer
      attivo — è la misura dello spike §5, e va rifatta perché adesso gira dentro il
      repository e non in una directory di prova.
- [ ] **Passo 5.** Commit: `feat: mongos davanti, e i due shard che entrano nel cluster`.

---

## Task 4 — Healthcheck e la catena che dichiara «pronto»

**File:** modificare `compose.yaml`.

- [ ] **Passo 1.** Healthcheck sui `mongod`: `hello().isWritablePrimary || hello().secondary`
      — un membro **operativo**, non un processo vivo. È la stessa forma dello stack 02 e la
      ragione è la stessa. Attenzione: lo spike usava `db.adminCommand('ping').ok`, che risponde
      anche a un `mongod` che non è ancora entrato nel set. Il passaggio alla sonda più severa è
      **voluto**, e va scritto nel commento del file perché chi confronta i due documenti non lo
      prenda per una svista.
- [ ] **Passo 2.** Healthcheck su `mongos`: non è un membro di replica set e la condizione di
      cui sopra non si applica. Provare `sh.status()` o un `db.adminCommand({ping: 1})`
      autenticato, e **scegliere misurando**: la domanda è se il router accetti connessioni
      prima che gli shard siano registrati. Se sì, l'healthcheck deve verificare la
      registrazione, altrimenti `up-03` dichiarerà pronto un cluster senza shard. L'esito è
      una voce in `Sources.md` in ogni caso.
- [ ] **Passo 3.** Aggiungere il servizio finale `up-03` che dipende dal completamento della
      catena e chiude l'avvio, come `up-02` nello stack 02.
- [ ] **Passo 4.** Verificare che `docker compose --profile palco up --wait` esca `0`
      **soltanto** quando `sh.status()` è già utile. La trappola numero 15 della pagina delle
      trappole dice che `up --wait` esce mentre la topologia non c'è ancora: questo è il task
      che la deve rendere inoffensiva qui.
- [ ] **Passo 5.** Commit: `feat: la catena dichiara pronto quando il cluster lo è davvero`.

---

## Task 5 — `check_stack.py` impara lo sharded (TDD)

**File:** modificare `tools/tests/test_check_stack.py`, poi `tools/check_stack.py`.

- [ ] **Passo 1.** Scrivere i test **prima**, uno per regola. Le regole candidate, tutte
      ricavate dai vincoli globali e non inventate qui: ogni `mongod` di shard dichiara
      `--shardsvr`; ogni config server dichiara `--configsvr`; la stringa `--configdb` di
      `mongos` nomina il set `cfgrs`; nessun servizio usa un IP; ogni servizio ha
      `mem_limit`, `cpus` e `pull_policy: never`; ogni `mongod` ha
      `--wiredTigerCacheSizeGB` non superiore al proprio `mem_limit`.
- [ ] **Passo 2.** Eseguirli e vederli **fallire** per la ragione giusta — non per un errore
      di importazione.
- [ ] **Passo 3.** Implementare le regole. Attenzione al principio del Task 0 di ogni branch:
      lo stack è un argomento. Se una regola vale per tutti e tre gli stack, va dove stanno
      le altre regole comuni, non in un ramo `if stack == "03"`.
- [ ] **Passo 4.** `make tools-test` verde, `make stack-check` con **tre** stack conformi.
- [ ] **Passo 5.** Commit: `test: le regole dello sharded, scritte prima del codice che le fa`.

---

## Task 6 — Dati di demo con la shard key, e `smoke-03`

**File:** creare `docker/03-sharded/init/30-dati-demo.js` e `tools/smoke-sharded.sh`.

- [ ] **Passo 1.** `sh.shardCollection()` con shard key `{_id: "hashed"}`, che è quella dello
      spike §5 e ha prodotto una distribuzione 50,7 % / 49,3 %. La scelta della shard key è
      **il** contenuto del Blocco 3: va scritta nel file con il commento che spiega perché
      hashed distribuisce e perché una chiave monotona no.
- [ ] **Passo 2.** Dataset deterministico: 20.000 documenti nel profilo `palco`. Lo spike ha
      misurato 4 chunk; se il numero cambia, è un'informazione, non un errore da nascondere.
- [ ] **Passo 3.** Scrivere `tools/smoke-sharded.sh` sul modello di `smoke-replicaset.sh`.
      Rileggere quel file prima: la lezione di [ADR-0054](../Decision.md#adr-0054) è che la
      password non va passata con `-e` al client `docker`, perché ne lascia una copia in più
      nella riga di comando dell'host.
- [ ] **Passo 4.** Le asserzioni dello smoke: due shard `state: 1`; balancer attivo; una
      scrittura con `w: "majority"` che va a buon fine; una lettura che torna il documento;
      la distribuzione dei documenti su **entrambi** gli shard, che è l'unica che distingue
      uno sharded cluster funzionante da uno che ha tutti i dati su un solo shard.
- [ ] **Passo 5.** Eseguire lo smoke con il profilo `palco` e con `completo`.
- [ ] **Passo 6.** Commit: `feat: i dati distribuiti, e uno smoke che sa distinguere due shard da uno`.

---

## Task 7 — Il `Makefile`, `reset-demo.sh 03`, le porte in `preflight`

**File:** modificare `Makefile`, `tools/reset-demo.sh`, `tools/preflight.sh`.

- [ ] **Passo 1.** I bersagli, con gli stessi nomi e la stessa forma degli altri due stack:
      `up-03`, `down-03`, `reset-03`, `logs-03`, `seed-03`, `smoke-03`. Il profilo si sceglie
      con una variabile, `PROFILO=palco` come predefinito.
- [ ] **Passo 2.** Aggiungere il caso `03` a `reset-demo.sh`. Il file dichiara nel proprio
      commento di testa che «feature/03 aggiunge il suo»: la verifica è che il diff sia
      **un ramo in più**, non una riscrittura. Se serve riscrivere, la riscrittura va
      motivata in un ADR.
- [ ] **Passo 3.** Aggiungere le sette porte nuove all'elenco di `preflight.sh`. Le porte
      degli stack 01 e 02 erano già lì prima che gli stack esistessero: qui si chiude
      l'ultimo pezzo di quella previsione.
- [ ] **Passo 4.** `make preflight` con gli stack fermi e con lo stack 03 avviato, due volte,
      stesso esito.
- [ ] **Passo 5.** Commit: `feat: i bersagli dello stack 03, e un caso in più invece di una riscrittura`.

---

## Task 8 — `docs/02-architetture/sharded-cluster.md`

**File:** creare la pagina che l'[indice](../README.md) promette per nome a questo branch.

- [ ] **Passo 1.** Struttura, sul modello di `replica-set.md`: che problema risolve lo
      sharding e quando **non** serve; la topologia dei tre ruoli; la shard key e perché è la
      decisione irreversibile; chunk e balancer; `mongos` come router senza stato; che cosa
      cambia per il client.
- [ ] **Passo 2.** La sezione che vale il Blocco 3: **la shard key sbagliata**. Una chiave
      monotona concentra le scritture su un chunk solo, e il balancer insegue senza mai
      raggiungere. Va scritta con la fonte, non a memoria.
- [ ] **Passo 3.** I numeri della pagina vengono dalle misure di questo branch o dallo spike,
      con il riferimento accanto. Nessun numero senza fonte.
- [ ] **Passo 4.** `make docs-check` verde.
- [ ] **Passo 5.** Commit: `docs: la pagina dello sharded cluster, e la chiave che non si cambia`.

---

## Task 9 — I debiti marcati, che si chiudono qui

Sono già scritti in pagina come debito: nessuna lista da ricostruire, ogni riga ha un
indirizzo. La regola che governa il task è [ADR-0049](../Decision.md#adr-0049) — un debito si
chiude **eseguendo**, e la prima volta che è stato applicato l'esecuzione ha rivelato due righe
sbagliate. Aspettarsi lo stesso qui è la posizione ragionevole.

- [ ] **Passo 1.** [`guida-mongosh.md`](../04-mongosh/guida-mongosh.md) §3.3, *Sharded
      cluster*, marcata per intero come non eseguita: eseguirla e togliere la marcatura,
      comando per comando. Ciò che resta non eseguito resta dichiarato tale
      ([ADR-0037](../Decision.md#adr-0037)). Nel farlo vale
      [ADR-0036](../Decision.md#adr-0036): in automazione il codice di uscita di `mongosh` non è
      una prova, l'esito va letto dall'output.
- [ ] **Passo 2.** [`sicurezza-keyfile-x509.md`](../03-amministrazione/sicurezza-keyfile-x509.md):
      gli **utenti locali a uno shard**, che qui esistono davvero perché ogni shard è un
      replica set con il proprio `admin`, e l'eccezione localhost che «applies to each shard
      individually as well as to the cluster as a whole» ([S-006](../Sources.md#s-006)).
      Marcato e mai provato: provarlo.
- [ ] **Passo 3.** [`backup-restore.md`](../03-amministrazione/backup-restore.md): `--oplog`
      che la documentazione **vieta** sullo sharded cluster ([S-011](../Sources.md#s-011)).
      Scrivere che cosa si fa invece, e provarlo.
- [ ] **Passo 4.** [`trappole-mongodb-in-docker.md`](../02-architetture/trappole-mongodb-in-docker.md):
      le trappole dei **config server** e del **bilanciamento**, che
      [ADR-0033](../Decision.md#adr-0033) intesta per nome a questo branch. Si aggiungono in
      coda; le diciotto esistenti non si toccano.
- [ ] **Passo 5.** `README.md` alla radice, riga 55: la tabella dichiara `docker/03-sharded`
      «in lavorazione». Va aggiornata. **Non** toccare la riga 57, che dice la stessa cosa
      dell'applicazione Python: quella è vera fino a `feature/04` e cancellarla qui
      trasformerebbe il `README` in una promessa.
- [ ] **Passo 6.** Commit: `docs: i debiti dello sharded, saldati eseguendo`.

---

## Task 10 — La riserva del Blocco 3

**File:** `docs/05-talk/registrazioni/`.

- [ ] **Passo 1.** Registrare con `tools/registra-terminale.py` almeno: l'avvio dello stack
      nel profilo `palco`, `sh.status()`, la distribuzione dei documenti, e il failover di un
      membro di shard.
- [ ] **Passo 2.** Riprodurre **ogni** registrazione per intero con `--riproduci` prima di
      dichiararla buona. È la regola che ha prodotto lo strumento, e la seconda review della
      PR #3 ha dimostrato che il codice di uscita di quello strumento è affidabile solo dopo
      [ADR-0055](../Decision.md#adr-0055).
- [ ] **Passo 3.** Aggiornare l'indice `registrazioni/README.md`.
- [ ] **Passo 4.** I filmati `.mp4` li gira **solo il relatore**
      ([ADR-0050](../Decision.md#adr-0050)): l'avviso di `preflight` resta acceso e nessun
      file finto viene creato per spegnerlo.
- [ ] **Passo 5.** Commit: `docs: la riserva del Blocco 3, riprodotta prima di dichiararla buona`.

---

## Task 11 — ADR, fonti e chiusura del branch

- [ ] **Passo 1.** Scrivere gli ADR delle decisioni prese lungo la strada. Almeno una è
      certa: l'esito del Passo 2 del Task 4, l'healthcheck di `mongos`.
- [ ] **Passo 2.** Ogni misura presa in questo branch diventa una voce in `Sources.md`, con
      comandi, ambiente, esito e **riserve**. Ogni voce dev'essere citata da un ADR:
      `check_citations.py` lo verifica.
- [ ] **Passo 3.** Scrivere la voce di registro con le note di metodo, e il consuntivo del
      branch. Il conteggio dei commit **include il commit che lo introduce**
      ([nota 37](../registro-operativo-sviluppo.md)), che è stato sbagliato tre volte prima
      che la regola esistesse.
- [ ] **Passo 4.** Le frasi da slide emerse lungo il branch vanno in
      [`citazioni-riportare-slide.md`](../citazioni-riportare-slide.md) **adesso**, non a fine
      progetto.
- [ ] **Passo 5.** I quattro controlli, eseguiti due volte — stack fermi e stack 03 avviato:
      `make preflight`, `make docs-check`, `make stack-check`, `make tools-test`.
- [ ] **Passo 6.** Aprire la PR #5 verso `develop`. **Non** chiudere con
      `git flow feature finish`: la feature si chiude unendo la PR su GitHub, ed è già
      successo una volta di sbagliare.
- [ ] **Passo 7.** Commit: `docs: ADR, fonti e chiusura di feature/03`.

---

## Criterio di completamento

Il branch è chiuso quando, e solo quando:

1. `docker compose --profile palco up --wait` esce `0` e `sh.status()` mostra due shard
   attivi **senza attese aggiunte a mano**.
2. Lo stesso vale per il profilo `completo`, con undici container.
3. `make smoke-03` verde su tutti e due i profili.
4. `make stack-check` riporta **tre** stack conformi.
5. `make tools-test`, `make docs-check` e `make preflight` verdi, eseguiti due volte.
6. `docs/02-architetture/sharded-cluster.md` esiste, e l'indice non promette più niente che
   non ci sia.
7. Nel `README.md` di radice `docker/03-sharded` non è più «in lavorazione», e l'unica
   dichiarazione di quel tipo rimasta è quella dell'applicazione Python.
8. La riserva del Blocco 3 è registrata e **riprodotta**.
9. Ogni sezione marcata «non eseguita» che questo branch poteva eseguire è stata eseguita, e
   quelle che restano marcate hanno il motivo scritto accanto.

---

## Nota di calendario

Questo branch si apre il **1º settembre** e ha due giorni: il 2 e il 3, che sono quelli
restituiti da `feature/02`, chiusa in anticipo. La regola che lo governa è in
[ADR-0057](../Decision.md#adr-0057) e ha una clausola vincolante: **`feature/04-app-python`
comincia il 4 settembre e non si sposta**. Se al 3 settembre lo sharded non è chiuso, non si
sfora: si sospende scrivendo il punto di ripresa, e il lavoro riprende nella finestra
originale del 14–15 settembre.

Il rischio è dichiarato invece che scoperto: aprire un branch perché c'è tempo è il modo
classico di trasformare due giorni di margine in due giorni di debito. La difesa è la data,
non la buona volontà.

Se si arriva stretti, l'ordine in cui si rinuncia è questo, dal primo sacrificabile
all'ultimo: il profilo `completo` (il `palco` basta per il talk), il Task 10, il Task 9
Passo 3. Non sono sacrificabili il Task 8 — l'indice promette quella pagina per nome — né il
criterio di completamento numero 4, perché uno stack che il controllore non sa leggere è uno
stack che invecchia da solo.
