# Gestione delle risorse in Compose

Questa pagina governa tutti e tre gli stack del lab e non appartiene a nessuno. Dice quanta
memoria e quanta CPU riceve ogni servizio, perché quei numeri e non altri, e — soprattutto —
come si **dimostra** che i limiti sono davvero applicati invece di limitarsi a dichiararlo.

È scritta prima che gli stack esistano, di proposito: i limiti non sono una rifinitura da
aggiungere quando qualcosa va in crisi, sono ciò che decide se undici container convivono su
un portatile o se l'OOM killer si presenta davanti al pubblico.

**Ogni numero di questa pagina è misurato.** Le misure stanno in
[V-006](../Sources.md#v-006) e [V-009](../Sources.md#v-009), sull'ambiente descritto lì:
Docker 29.7.2, Compose v5.4.0, VM `linuxkit` con 11.946 MiB e 8 CPU, MongoDB 7.0.40. Su un
ambiente diverso vanno rifatte, non ricopiate.

---

## 1. Perché senza limiti va male

### Il conto

La cache interna di WiredTiger, se nessuno le dice quanto essere grande, prende «the larger of
either: 50% of (RAM - 1GB), or 0.256 GB» [S-001](../Sources.md#s-001). La domanda che decide
tutto è quale sia la `RAM` di quella formula dentro un container. La risposta, misurata su sei
configurazioni [V-009](../Sources.md#v-009), è: **la memoria che il container può usare**, non
quella della macchina.

Il che va benissimo — finché un limite c'è. Senza limite, la memoria del container *è* quella
della VM, e allora:

```
VM Docker:                    11.946 MiB
cache scelta da un mongod:     5.461 MiB     ← 0,5 × (11.946 − 1.024)
tre mongod di un replica set: 16.383 MiB     ← il 137 % della VM
```

Non è una stima: `5461` è il valore letto da `db.serverStatus()` in un container senza
`mem_limit` [V-009](../Sources.md#v-009). Tre membri di un replica set rivendicano un terzo di
memoria in più di quanta ne esista, e lo fanno **senza dire niente a nessuno**: la cache non si
alloca tutta all'avvio, si riempie sotto carico. Il lab parte, la demo comincia, e la crisi
arriva nel momento esatto in cui si inizia a scrivere dati — cioè durante la dimostrazione.

Con i limiti del lab lo stesso replica set occupa 768 MiB per membro e ogni cache si ferma a
256 MiB.

### Cosa si vede quando succede

Questa è la parte che vale la pena provare prima, perché la risposta è controintuitiva: **nel
log non si vede niente.**

Un processo che supera il proprio `mem_limit` viene ucciso con `SIGKILL`. Non c'è gestione
dell'errore, non c'è messaggio d'addio, non c'è stack trace. Misurato
[V-009](../Sources.md#v-009): `docker logs` sul container ucciso restituisce **zero righe**.

L'unico posto dove il fatto è registrato è lo stato del container:

```console
$ docker inspect <container> --format 'OOMKilled={{.State.OOMKilled}} ExitCode={{.State.ExitCode}} Error="{{.State.Error}}"'
OOMKilled=true ExitCode=137 Error=""
```

Tre cose da sapere a memoria:

- **`137` è `128 + 9`**, cioè «terminato dal segnale 9». È la firma dell'OOM killer.
- **`Error` è vuoto.** Chi cerca lì una spiegazione non la trova, e conclude che il container
  «si è chiuso da solo».
- **`OOMKilled` è l'unico campo affidabile.** Il codice 137 da solo non basta: lo produce anche
  un `docker kill`.

Se una demo muore così sul palco, il comando da avere nelle dita è quello lì sopra, non
`docker logs`.

### L'avviso che mongod dà, e quello che non dà

Quando un limite c'è, mongod lo vede e lo scrive nel log. Misurato
[V-009](../Sources.md#v-009), avviso `id: 20720`:

```json
{"s":"W","c":"CONTROL","id":20720,"ctx":"initandlisten",
 "msg":"Memory available to mongo process is less than total system memory",
 "attr":{"availableMemSizeMB":640,"systemMemSizeMB":11946}}
```

Nel container **senza** limite quell'avviso ha zero occorrenze. È quindi una prova diretta e
proiettabile: se compare, mongod ha letto il `mem_limit`; se non compare, non c'è limite da
leggere.

Ma attenzione a cosa quell'avviso **non** dice. Un container da 512 MiB con
`--wiredTigerCacheSizeGB 4` parte senza errori e configura 4.096 MiB di cache
[V-009](../Sources.md#v-009). Nessun messaggio mette in relazione le due cifre. Il nodo sembra
sano, risponde al `ping`, supera l'healthcheck — e si condanna alla prima scrittura seria.
**Il controllo di coerenza fra cache e `mem_limit` non esiste: lo fa chi scrive il file
Compose, o non lo fa nessuno.**

---

## 2. Come si dimensiona

### I tre consumatori di memoria

Un mongod non è la sua cache. La memoria si divide grosso modo in tre:

1. **La cache interna di WiredTiger.** È l'unica delle tre che si dichiara con un numero, ed è
   la ragione per cui esiste questa pagina.
2. **Il resto di mongod** — connessioni, ordinamenti, aggregazioni, buffer di rete. Cresce con
   la concorrenza, cioè con esattamente ciò che l'applicazione del talk andrà a variare.
3. **La cache del filesystem**, che sta fuori dal processo ma dentro il limite del container.

La formula predefinita lascia metà della memoria meno un GiB alle prime due voci. È una
divisione sensata su un server dedicato; in un container piccolo il termine `− 1 GiB` la rende
brutalmente conservativa, ed è esattamente il comportamento che serve al lab.

### La formula, misurata su sei punti

Nessun `--wiredTigerCacheSizeGB`, solo `mem_limit` variabile [V-009](../Sources.md#v-009):

| `mem_limit` | `hostInfo.system.memLimitMB` | Cache scelta | Come si spiega |
|---|---|---|---|
| 640 MiB | 640 | **256 MiB** | `0,5 × (640 − 1.024)` è negativo → pavimento |
| 768 MiB | 768 | **256 MiB** | idem |
| 1.024 MiB | 1024 | **256 MiB** | `0,5 × 0` = 0 → pavimento |
| 2.048 MiB | 2048 | **512 MiB** | `0,5 × (2.048 − 1.024)` |
| 4.096 MiB | 4096 | **1.536 MiB** | `0,5 × (4.096 − 1.024)` |
| *nessuno* | 11946 | **5.461 MiB** | `0,5 × (11.946 − 1.024)` |

Due letture da portare via.

**Il campo che conta è `memLimitMB`, non `memSizeMB`.** Il secondo riporta sempre 11946, cioè
la VM, in tutte e sei le righe. Il manuale MongoDB su questo si contraddice fra due pagine
correnti — [S-001](../Sources.md#s-001) avverte che WiredTiger «may not account for the memory
limits of the specific container in certain cases», [S-026](../Sources.md#s-026) afferma che
«This memory limit, rather than the total system memory, is used as the maximum RAM available
to calculate WiredTiger internal cache». La contraddizione è **apparente**: parlano di campi
diversi, e la misura scioglie il dubbio in favore di [S-026](../Sources.md#s-026). Sul palco si
mostra `db.adminCommand({hostInfo: 1})` e i due campi si vedono affiancati, invece di scegliere
una pagina e sperare che nessuno controlli.

**Il pavimento è 256 MiB, non «0.256 GB».** Sono due numeri diversi: 0,256 GB decimali fanno
244 MiB. Il manuale scrive GB, l'implementazione usa GiB. Se in slide finisce «0.256 GB», la
cifra non corrisponde a ciò che il lab mostra a schermo.

### Il valore esplicito, e il minimo vero

Il lab dichiara comunque la cache a mano, con `--wiredTigerCacheSizeGB 0.25` per ogni mongod
([ADR-0004](../Decision.md#adr-0004)). Non perché il rilevamento automatico non funzioni — le
sei misure dicono che funziona — ma perché **il file Compose è materiale didattico**: un numero
scritto si può leggere, discutere e cambiare in proiezione; un numero calcolato di nascosto no.

Sul valore c'è una precisazione che vale il tempo di leggerla, perché il progetto ci si era
sbagliato sopra. Il riferimento di `mongod` dichiara «Values can range from **0.256GB** to
10000GB» [S-002](../Sources.md#s-002), e da lì era nato il timore che `0.25` fosse sotto il
minimo. Il binario dice altro [V-009](../Sources.md#v-009):

```console
$ docker run --rm mongo:7.0 mongod --dbpath /data/db --wiredTigerCacheSizeGB 0.1
{"s":"F","c":"CONTROL","id":20574,"ctx":"main","msg":"Error during global initialization",
 "attr":{"error":{"code":2,"codeName":"BadValue",
 "errmsg":"storage.wiredTiger.engineConfig.cacheSizeGB must be greater than or equal to 0.25"}}}
```

Il minimo imposto è **`0.25`**, alla lettera. E `0.25` configura `268435456` byte, cioè
esattamente 256 MiB: lo stesso identico valore del pavimento automatico. Il valore `0.256`,
quello scritto nel manuale, ne produce 262 — un numero che non corrisponde a niente.

### La tabella del lab

| Stack | Servizi | `mem_limit` | Cache WT | `cpus` | Totale dichiarato |
|---|---|---|---|---|---|
| 01 standalone | 1 mongod | `1024m` | `0.25` | `1.0` | 1,0 GiB |
| 02 replica set | 3 mongod | `768m` | `0.25` | `0.75` | 2,25 GiB |
| 03 sharded `palco` | 1 cfg + 2 shard + 1 mongos | `512m` / `640m` / `384m` | `0.25` | `0.5` | 2,2 GiB |
| 03 sharded `completo` | 3 cfg + 6 shard + 2 mongos | idem | `0.25` | `0.5` | 6,0 GiB |
| app | 1 container Python | `512m` | — | `1.0` | 0,5 GiB |

Il ragionamento dietro i numeri, che conta più dei numeri:

- **`0.25` ovunque** non è pigrizia. Alle taglie del lab la formula automatica finisce sul
  pavimento in ogni caso da 1.024 MiB in giù, quindi dichiarare `0.25` **non cambia il
  comportamento**: lo rende leggibile. È una scelta didattica, e va detta come tale.
- **I mongos non hanno cache** perché non hanno storage: instradano. `384m` copre il processo e
  i buffer di connessione, e la misura dà loro ragione — 21 MiB reali in esercizio
  [V-006](../Sources.md#v-006).
- **Gli shard hanno più memoria dei config server** (`640m` contro `512m`) perché ci finiscono i
  dati. I config server tengono metadati, che sono piccoli.
- **`cpus` scende quando i servizi salgono.** Non per equità: per lasciare fiato a macOS, alle
  slide e alla registrazione dello schermo, che girano sulla stessa macchina.

### Il tetto non è una prenotazione

La riga più importante di tutta la pagina, e quella che si dimentica per prima.

Undici container del profilo `completo`, tutti avviati, hanno occupato **1.356 MiB reali contro
6.144 MiB di `mem_limit` dichiarati** [V-006](../Sources.md#v-006). Docker non pre-alloca
niente: `mem_limit` dice *fin dove* un container può arrivare, non quanto si prende subito.

Il che ha due conseguenze opposte, ed entrambe vanno dette.

*In positivo:* si possono dichiarare somme che eccedono la memoria della VM senza che succeda
nulla di male, finché i container non ci arrivano davvero.

*In negativo:* **il fatto che tutto giri a riposo non dimostra niente sul comportamento sotto
carico**, ed è precisamente sotto carico che il talk mostra qualcosa. I 12 GiB assegnati alla
VM ([ADR-0025](../Decision.md#adr-0025)) servono al caso peggiore, non a quello osservato.

---

## 3. `mem_limit` contro `deploy.resources`

### Le due forme, affiancate

Compose accetta due modi di dire la stessa cosa. Sintassi breve:

```yaml
services:
  mongo1:
    image: ${MONGO_IMAGE}
    mem_limit: 640m
    cpus: 0.5
```

Deploy Specification:

```yaml
services:
  mongo1:
    image: ${MONGO_IMAGE}
    deploy:
      resources:
        limits:
          memory: 640m
          cpus: "0.5"
```

Le unità ammesse dalla forma breve sono `b`, `k`/`kb`, `m`/`mb`, `g`/`gb`
[S-003](../Sources.md#s-003). `cpus` è «a fractional number», e «`0.000` means no limit».

### La storia, e perché quasi tutti la raccontano sbagliata

La convinzione diffusa è che `deploy` sia roba da Swarm e venga ignorato da `docker compose
up`. Aveva una base: la frase esisteva davvero, nel riferimento del formato v3. Quel
riferimento oggi non c'è più — «The legacy versions of the Compose file reference has moved to
the V1 branch of the Compose repository. They are no longer being actively maintained»
[S-004](../Sources.md#s-004).

Nella documentazione attuale la situazione è più scomoda di così. Nel corpo della pagina della
Deploy Specification i termini «Swarm», «ignored», «not supported» e «docker compose up» hanno
**zero occorrenze** [S-004](../Sources.md#s-004). Non è che la risposta sia cambiata: è che la
domanda non ha più una risposta scritta.

E c'è un dettaglio che ribalta la narrazione corrente. La documentazione **non** presenta le due
forme come alternative fra cui scegliere: ne impone la coerenza. «When set, `mem_limit` must be
consistent with the `limits.memory` attribute in the Deploy Specification»
[S-003](../Sources.md#s-003). Chi dice «usa `mem_limit` *invece di* `deploy`» sta citando una
fonte che non esiste.

### La misura

Dove la documentazione tace, si misura. Tre servizi nello stesso file, stessa immagine, stesso
comando, diversi solo per come dichiarano i limiti [V-009](../Sources.md#v-009):

| Servizio | Dichiarazione | `HostConfig.Memory` | `HostConfig.NanoCpus` |
|---|---|---|---|
| `breve` | `mem_limit` + `cpus` | `671088640` | `500000000` |
| `deploy_solo` | `deploy.resources.limits` | `671088640` | `500000000` |
| `nessun_limite` | niente | `0` | `0` |

**Identici byte per byte.** Su Compose v5.4.0, `deploy.resources.limits` è applicato da `docker
compose up` esattamente come la forma breve. `671088640` è `640 × 1024²`, cioè `640m` letto in
MiB; `500000000` nanoCPU è mezza CPU.

Il comando che lo mostra, da tenere nel runbook:

```console
$ docker inspect <container> --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}}'
671088640 500000000
```

### Cosa usa il lab, e perché

Il lab usa la **sintassi breve** ([ADR-0013](../Decision.md#adr-0013)), per una ragione sola e
onesta: due righe invece di sei, su un proiettore, davanti a gente seduta in fondo alla sala.

Va detto chiaramente che questo **non** è un giudizio di merito. L'argomento «l'altra non
funziona» è caduto con la misura qui sopra. Chi preferisce `deploy.resources` non perde niente,
e se dichiara entrambe le forme deve tenerle coerenti — non per stile, perché lo chiede la
documentazione.

### Se si migra verso Podman

Nota richiesta esplicitamente dal Product Owner il 2026-08-24, e va letta per quello che è: **un
avvertimento, non una verifica.** Il lab non è mai stato eseguito su Podman, e nessuna delle
fonti di questo repository parla di Podman.

Il punto di attenzione è che l'equivalenza fra le due sintassi misurata qui sopra vale per
**Compose v5.4.0**, non per il formato Compose in astratto. È un comportamento di quella
implementazione. Chi porta questi file su `podman compose` o `podman-compose` deve rifare la
misura, non fidarsi di questa pagina:

```console
$ podman inspect <container> --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}}'
```

Se i campi tornano a zero, i limiti non sono stati applicati e la cache di WiredTiger si
dimensionerà sulla memoria dell'intera macchina — cioè si torna al conto della sezione 1. La
verifica costa una riga; ometterla costa una demo.

---

## 4. `cpus` come strumento narrativo

Limitare la CPU protegge la postazione, ma è la ragione meno interessante. Quella buona è che
`cpus` rende **osservabile** qualcosa che altrimenti si può solo raccontare.

### Prima, che strozzi davvero

Un ciclo occupato, tempo di CPU contro tempo di parete [V-009](../Sources.md#v-009):

| Configurazione | Tempo di parete | Tempo di CPU | Rapporto |
|---|---|---|---|
| senza limite | 3,947 s | 3,946 s | **1,00** |
| `--cpus 0.5` | 3,069 s | 1,541 s | **0,502** |

Il rapporto misurato è `0,502` contro un limite dichiarato di `0,5`. Non è un tetto teorico:
è un tetto.

### Poi, che serva a raccontare

Un secondario deliberatamente strozzato — `cpus: 0.1` mentre gli altri membri ne hanno `0.75` —
fatica ad applicare l'oplog quanto il primario lo produce. Il ritardo di replica smette di
essere un concetto e diventa un numero che cresce a schermo, in `rs.printSecondaryReplicationInfo()`
o nel campo `optimeDate` di `rs.status()`.

È una demo che si costruisce cambiando **una cifra** in un file Compose, senza software di
carico e senza attese artificiali. La procedura operativa completa appartiene allo stack del
replica set, non a questa pagina; qui serve sapere che il meccanismo è quello e che il limite
è misurato.

Due avvertenze per non mentire dal palco:

- **Il rapporto `0,502` vale per una CPU occupata in un ciclo.** Un carico MongoDB reale aspetta
  anche su I/O, e lì il rapporto dipende da altro [V-009](../Sources.md#v-009).
- **`cpus` non nasconde i core.** Un container con `cpus: 0.5` continua a vedere
  `hostInfo.system.numCores = 8` [V-009](../Sources.md#v-009). Il limite è una quota di tempo,
  non una maschera sull'hardware: mongod dimensiona i suoi pool di thread sui core che vede, non
  sulla quota che riceve. È la ragione per cui non si scende sotto `0.5` senza motivo.

---

## 5. I due profili dello sharded cluster

Lo stack sharded è uno solo e porta due profili ([ADR-0010](../Decision.md#adr-0010)). Questa
sezione è un obbligo formale di [ADR-0025](../Decision.md#adr-0025), che chiede di dire in modo
esplicito **a chi serve ciascun profilo, quanto costa e con quale comando si sceglie**. Nell'ordine.

### A chi serve

| Profilo | Destinatario | Perché |
|---|---|---|
| `palco` | **chi presenta**, dal vivo | Un membro per componente. Mostra l'architettura completa — config server, due shard, router — nel budget di memoria di una macchina che sta anche proiettando e registrando lo schermo. |
| `completo` | **chi studia**, dopo aver clonato il repository | Tre membri per componente: la forma canonica. È l'unico dei due su cui il failover di uno shard sia dimostrabile, perché con un membro solo non c'è nessuno da eleggere. |

La divisione non è fra «versione buona» e «versione ridotta». Sono due destinatari diversi con
due esigenze diverse, e il repository serve entrambi ([ADR-0017](../Decision.md#adr-0017)).

Il profilo `palco` non è un ripiego improvvisato: il replica set a un membro è autorizzato dalla
documentazione MongoDB, che lo dice due volte — una per i config server e una per gli shard —
con la stessa frase, «For testing purposes, you can create a single-member replica set»
[S-024](../Sources.md#s-024). Vale la pena sapere dove sta scritto, perché **non** è sulla
pagina dei componenti, dove istintivamente si andrebbe a cercarla.

### Quanto costa

| | `palco` | `completo` |
|---|---|---|
| Servizi avviati | **5** | **12** |
| Container MongoDB | 4 | 11 |
| `mem_limit` totale dichiarato | ~2,2 GiB | **6,0 GiB** |
| Occupazione reale misurata | — | **1,32 GiB** [V-006](../Sources.md#v-006) |
| VM Docker necessaria | 8 GiB bastano | **12 GiB** ([ADR-0025](../Decision.md#adr-0025)) |
| Failover dimostrabile | no | **sì**, misurato |

I conteggi dei servizi sono misurati, non stimati [V-006](../Sources.md#v-006). Il dodicesimo
servizio di `completo` e il quinto di `palco` sono lo stesso: `keyfile-init`, che non porta
`profiles` e quindi è **sempre** attivo — «Services without a `profiles` attribute are always
enabled» [S-015](../Sources.md#s-015).

Sulla distanza fra 6,0 GiB dichiarati e 1,32 GiB reali vale quanto detto in §2: è un tetto, non
una prenotazione, e il cluster misurato era a riposo.

### Con quale comando si sceglie

```console
# Il profilo di palco — quello che va in scena
$ docker compose --profile palco up -d --wait

# Il profilo completo — tre membri per componente
$ docker compose --profile completo up -d --wait

# Cosa parte, prima di farlo partire davvero
$ docker compose --profile palco config --services
$ docker compose --profile completo config --services

# Fermare, ricordandosi il profilo: senza, Compose non sa cosa fermare
$ docker compose --profile completo down -v
```

Tre cose che si imparano sbagliandole:

- **`--profile` va ripetuto su ogni comando**, `down` compreso. Un `docker compose down` senza
  profilo lascia in piedi i container profilati.
- **`config --services` è il modo di controllare prima.** Elenca cosa verrebbe avviato senza
  avviare niente: 5 con `palco`, 12 con `completo`, 1 senza profilo
  [V-006](../Sources.md#v-006). Quel `1` è `keyfile-init`, ed è la prova che la regola di
  [S-015](../Sources.md#s-015) è attiva.
- **`--wait` non è un vezzo.** Senza, Compose torna appena i container sono *partiti*, non
  quando sono *sani*; la forma breve di `depends_on` «does not wait for dependency services to
  be "healthy"» [S-012](../Sources.md#s-012).

I due profili non vanno mai avviati insieme: userebbero le stesse porte
([ADR-0010](../Decision.md#adr-0010)) e la somma dei limiti supererebbe la VM.

---

## 6. La lista dei controlli

Da eseguire dopo ogni modifica ai limiti, e prima di ogni prova generale.

```console
# 1. I limiti sono arrivati al container?
$ docker inspect <container> --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}}'
#    Zero significa «nessun limite», non «limite predefinito».

# 2. mongod li ha visti?
$ docker exec <container> mongosh --quiet --eval \
    'const h = db.adminCommand({hostInfo: 1}); print(h.system.memSizeMB, h.system.memLimitMB)'
#    Se i due numeri coincidono, il limite non c'è.

# 3. Che cache ne è uscita?
$ docker exec <container> mongosh --quiet --eval \
    'print(db.serverStatus().wiredTiger.cache["maximum bytes configured"] / 1048576 + " MiB")'
#    Deve stare largamente sotto il mem_limit. Nessuno lo controlla al posto nostro.

# 4. Quanto stanno consumando davvero?
$ docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}'
#    La colonna MEM USAGE / LIMIT è la più leggibile su un proiettore.

# 5. Qualcuno è stato ucciso?
$ docker inspect <container> --format '{{.State.OOMKilled}} {{.State.ExitCode}}'
#    true 137 — e nel log non ci sarà niente.
```

---

## Cosa questa pagina non dice

- **Non copre Podman.** Vedi la nota in §3: è un avvertimento con la procedura di verifica, non
  una verifica.
- **Non copre il comportamento sotto carico.** Tutte le misure di occupazione reale
  ([V-006](../Sources.md#v-006)) vengono da un cluster a riposo salvo cinquantamila inserimenti.
  L'applicazione del talk fa esattamente il contrario, e i numeri saliranno verso i tetti.
- **Non copre l'OOM di un mongod reale.** Il codice 137 è stato riprodotto con un allocatore
  artificiale [V-009](../Sources.md#v-009). Che un mongod ucciso si presenti allo stesso modo è
  plausibile, non misurato.
- **Vale per MongoDB 7.0.40 e Compose v5.4.0.** Il minimo della cache, il pavimento e
  l'equivalenza fra le due sintassi sono proprietà di quelle versioni. Sulla versione del lab e
  sul perché non sia una 8.x, vedi [ADR-0028](../Decision.md#adr-0028).

---

**Decisioni correlate:** [ADR-0004](../Decision.md#adr-0004) (limiti espliciti),
[ADR-0010](../Decision.md#adr-0010) (i due profili),
[ADR-0013](../Decision.md#adr-0013) (sintassi breve nei file),
[ADR-0025](../Decision.md#adr-0025) (dodici GiB alla VM).

**Fonti:** [S-001](../Sources.md#s-001), [S-002](../Sources.md#s-002),
[S-003](../Sources.md#s-003), [S-004](../Sources.md#s-004), [S-012](../Sources.md#s-012),
[S-015](../Sources.md#s-015), [S-024](../Sources.md#s-024), [S-026](../Sources.md#s-026),
[V-006](../Sources.md#v-006), [V-009](../Sources.md#v-009)
