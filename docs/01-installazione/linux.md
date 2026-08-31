# Installare MongoDB su Linux (Ubuntu)

> **Riserva dichiarata.** Questa procedura **non è stata eseguita**. La macchina di sviluppo di
> questo progetto è un Mac con Docker Desktop: non esiste qui un Ubuntu su cui provare
> `apt-get install mongodb-org`. Ogni comando e ogni valore di questa pagina viene dalla
> documentazione ufficiale MongoDB per la versione 7.0 — [S-048](../Sources.md#s-048),
> [S-050](../Sources.md#s-050), [S-051](../Sources.md#s-051), [S-052](../Sources.md#s-052) — ed è
> citato accanto al punto in cui compare. Il primo a provarla davvero sarà chi legge
> ([ADR-0037](../Decision.md#adr-0037)).
>
> Fa eccezione la [sezione 6](#6-quello-che-cambia-dentro-un-container), che è misurata: riguarda
> il container del lab, e serve a mostrare **quanto** di questa pagina, dentro Docker, non si
> applica.

Nel resto del repository si parla di MongoDB dentro container. Questa pagina e la
[gemella per Windows](windows.md) sono le uniche due che parlano di MongoDB installato su un
sistema operativo, che è come sta il database nella maggior parte delle aziende.

---

<a id="1-prima-di-cominciare"></a>
## 1. Prima di cominciare

<a id="11-le-versioni-supportate"></a>
### 1.1 Le versioni supportate

MongoDB 7.0 Community Edition dichiara il supporto per Ubuntu **22.04 LTS «Jammy»** e **20.04 LTS
«Focal»**, solo a 64 bit ([S-048](../Sources.md#s-048)). Per sapere quale si ha davanti:

```bash
cat /etc/lsb-release
```

<a id="12-il-pacchetto-sbagliato-si-chiama-quasi-uguale"></a>
### 1.2 Il pacchetto sbagliato si chiama quasi uguale

È l'errore più comune, e la documentazione lo mette in evidenza
([S-048](../Sources.md#s-048)):

> «The `mongodb` package provided by Ubuntu is **not** maintained by MongoDB Inc. and conflicts
> with the official `mongodb-org` package. If you already installed the `mongodb` package on your
> Ubuntu system, you **must** first uninstall the `mongodb` package before proceeding with these
> instructions.»

Il pacchetto giusto si chiama **`mongodb-org`**. `mongodb` è quello di Ubuntu, è vecchio, e
impedisce l'installazione di quello ufficiale. Prima di partire vale la pena controllare:

```bash
dpkg -l | grep -i mongodb
```

<a id="2-installare"></a>
## 2. Installare

Quattro passi, tutti da [S-048](../Sources.md#s-048).

**1. Importare la chiave pubblica GPG.**

```bash
sudo apt-get install gnupg curl

curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
   sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg \
   --dearmor
```

**2. Creare il file di elenco per `apt`.** Su Ubuntu 22.04 (Jammy):

```bash
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
```

Il nome della distribuzione dentro l'URL (`jammy`) cambia con la versione di Ubuntu: su 20.04
diventa `focal`. È l'unica parte della riga che va adattata.

**3. Ricaricare l'elenco dei pacchetti.**

```bash
sudo apt-get update
```

**4. Installare.**

```bash
sudo apt-get install -y mongodb-org
```

> **Una nota sulla versione.** `apt-get install -y mongodb-org` installa l'ultima 7.0
> disponibile, e un `apt-get upgrade` la sposterà in avanti da solo. La documentazione prevede
> l'alternativa — «You can install either the latest stable version of MongoDB or a specific
> version of MongoDB» ([S-048](../Sources.md#s-048)) — ma la variante di pagina consultata qui
> riporta solo la prima forma, e questa pagina non inventa la seconda: chi ha bisogno di una
> versione esatta la cerchi nella scheda *Specific Release* del tutorial ufficiale. Il problema è
> lo stesso che in questo repository si risolve pinnando le immagini per digest
> ([ADR-0026](../Decision.md#adr-0026)): un tag non è un contratto.

<a id="3-che-cosa-e-comparso-sul-sistema"></a>
## 3. Che cosa è comparso sul sistema

| percorso | che cos'è |
| --- | --- |
| `/var/lib/mongodb` | la directory dei dati (`dbPath`), creata dall'installazione |
| `/var/log/mongodb` | la directory dei log, creata dall'installazione |
| `/etc/mongod.conf` | il file di configurazione, in formato YAML |
| utente `mongodb` | l'account con cui gira il processo |

Tutte e quattro le righe vengono da [S-048](../Sources.md#s-048), che aggiunge l'avvertenza che si
paga più cara: «By default, MongoDB runs using the `mongodb` user account. If you change the user
that runs the MongoDB process, you **must** also modify the permission to the data and log
directories to give this user access to these directories.» Cambiare l'utente e dimenticare i
permessi produce un servizio che non parte, con un errore che parla di disco e non di permessi.

Sul file di configurazione, una regola che sembra ovvia finché non morde: «if you change the
configuration file while the MongoDB instance is running, you must restart the instance for the
changes to take effect» ([S-048](../Sources.md#s-048)). Non c'è ricarica a caldo.

<a id="4-avviare-e-governare-il-servizio"></a>
## 4. Avviare e governare il servizio

Prima si stabilisce quale init system c'è, perché i comandi cambiano
([S-048](../Sources.md#s-048)):

```bash
ps --no-headers -o comm 1
```

`systemd` sulle versioni recenti, `init` su quelle vecchie. Con `systemd`:

| operazione | comando |
| --- | --- |
| avviare | `sudo systemctl start mongod` |
| controllare | `sudo systemctl status mongod` |
| avviare a ogni riavvio | `sudo systemctl enable mongod` |
| fermare | `sudo systemctl stop mongod` |
| riavviare | `sudo systemctl restart mongod` |

«You can follow the state of the process for errors or important messages by watching the output
in the `/var/log/mongodb/mongod.log` file» ([S-048](../Sources.md#s-048)). Quel file è scritto nel
formato JSON strutturato descritto in
[`03-amministrazione/log.md`](../03-amministrazione/log.md), e la differenza con il lab è
istruttiva: qui c'è un file da ruotare, e `logRotate` serve davvero — in container non serviva
([V-010](../Sources.md#v-010)).

Per collegarsi, `mongosh` sulla stessa macchina, senza opzioni.

<a id="5-la-messa-a-punto-che-nessuno-fa"></a>
## 5. La messa a punto che nessuno fa

Cinque argomenti che un `mongod` appena installato non ha, che nessuna pagina su Docker
insegnerà mai, e che si pagano in produzione. Tutti da [S-050](../Sources.md#s-050),
[S-051](../Sources.md#s-051) e [S-052](../Sources.md#s-052).

<a id="51-bindip-la-prima-riga-da-cambiare-e-la-piu-pericolosa"></a>
### 5.1 `bindIp`: la prima riga da cambiare, e la più pericolosa

Appena installato, `mongod` ascolta solo su `127.0.0.1` ([S-048](../Sources.md#s-048)):

> «By default, MongoDB launches with `bindIp` set to `127.0.0.1`, which binds to the localhost
> network interface. This means that the `mongod` can only accept connections from clients that
> are running on the same machine. Remote clients will not be able to connect to the `mongod`, and
> the `mongod` will not be able to initialize a replica set unless this value is set to a valid
> network interface which is accessible from the remote clients.»

Due conseguenze. La prima: nessun client remoto entra, e chi si aspetta il contrario perde
mezz'ora. La seconda, meno nota: **un replica set non si può nemmeno inizializzare** finché
`bindIp` resta su localhost.

E qui arriva l'avvertenza che va letta prima di cambiare quel valore — la stessa, parola per
parola, in entrambi i tutorial di installazione ([S-048](../Sources.md#s-048),
[S-049](../Sources.md#s-049)):

> «Before you bind your instance to a publicly-accessible IP address, you must secure your cluster
> from unauthorized access.»

Aprire `bindIp` senza aver prima abilitato l'autenticazione espone un database senza password su
una rete. Il lab di questo repository gira senza autenticazione **perché è isolato in una rete
Compose** ([ADR-0005](../Decision.md#adr-0005)); su un server la stessa scelta non è ammissibile.
[S-050](../Sources.md#s-050) lo dice come regola generale: «Always run MongoDB in a *trusted
environment*, with network rules that prevent access from *all* unknown computers, systems, and
networks», e in evidenza «By default, authorization is not enabled.»

<a id="52-ulimit-e-il-motivo-per-cui-si-contano-a-due-a-due"></a>
### 5.2 `ulimit`, e il motivo per cui i descrittori si contano a due a due

I sette valori raccomandati ([S-052](../Sources.md#s-052)):

| risorsa | opzione | valore |
| --- | --- | --- |
| file size | `-f` | `unlimited` |
| cpu time | `-t` | `unlimited` |
| virtual memory | `-v` | `unlimited` |
| locked-in-memory size | `-l` | `unlimited` |
| **open files** | `-n` | **`64000`** |
| memory size | `-m` | `unlimited` |
| **processes/threads** | `-u` | **`64000`** |

Il numero che conta è `-n`, e la ragione è una frase sola: «Incoming connections to a `mongod` or
`mongos` instance require **two** file descriptors» ([S-052](../Sources.md#s-052)). Il tetto da
reggere non è il numero delle connessioni: è il doppio. E se il valore resta sotto i 64000,
«MongoDB generates a startup warning» ([S-048](../Sources.md#s-048)) — l'avviso c'è, e finisce fra
le decine di migliaia di righe che nessuno legge.

**Sotto `systemd` non si usa `ulimit`.** Si scrivono le direttive nella sezione `[Service]` del
file di unità, in `/etc/systemd/system/<nome>.service` ([S-052](../Sources.md#s-052)):

```ini
[Service]
# (file size)
LimitFSIZE=infinity
# (cpu time)
LimitCPU=infinity
# (virtual memory size)
LimitAS=infinity
# (locked-in-memory size)
LimitMEMLOCK=infinity
# (open files)
LimitNOFILE=64000
# (processes/threads)
LimitNPROC=64000
```

Con un'avvertenza che evita un errore diffuso: «Each `systemd` limit directive sets both the
"hard" and "soft" limits to the value specified». Poi
`systemctl daemon-reload && systemctl restart mongod`, perché i limiti si applicano al processo
all'avvio: «Restart your `mongod` and `mongos` instances after changing the `ulimit` settings to
apply the changes.»

<a id="53-transparent-huge-pages"></a>
### 5.3 Transparent Huge Pages: perché un database le vuole spente

[S-051](../Sources.md#s-051) spiega prima che cosa sono e poi perché disturbano:

> «Transparent Huge Pages (THP) is a Linux memory management system that reduces the overhead of
> Translation Lookaside Buffer (TLB) lookups on machines with large amounts of memory by using
> larger memory pages.»
>
> «However, database workloads often perform poorly with THP enabled, because they tend to have
> sparse rather than contiguous memory access patterns. When running MongoDB on Linux, THP should
> be disabled for best performance.»

Il rimedio raccomandato non è un comando da dare a mano — sparirebbe al riavvio — ma un servizio
che gira **prima** di `mongod`. Il file, da salvare in
`/etc/systemd/system/disable-transparent-huge-pages.service`:

```ini
[Unit]
Description=Disable Transparent Hugepages (THP)
DefaultDependencies=no
After=sysinit.target local-fs.target
Before=mongod.service

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo never | tee /sys/kernel/mm/transparent_hugepage/enabled > /dev/null && echo never | tee /sys/kernel/mm/transparent_hugepage/defrag > /dev/null'

[Install]
WantedBy=basic.target
```

Poi `sudo systemctl daemon-reload` e `sudo systemctl enable disable-transparent-huge-pages`. La
riga che fa il lavoro è `Before=mongod.service`: THP va spento prima che il server allochi
memoria, non dopo.

Un'insidia sui percorsi ([S-051](../Sources.md#s-051)): «Some versions of Red Hat Enterprise Linux,
and potentially other Red Hat-based derivatives, use a different path for the THP `enabled` file:
`/sys/kernel/mm/redhat_transparent_hugepage/enabled`.» Su RHEL e CentOS con `tuned` o `ktune`
serve in più un profilo personalizzato, altrimenti il profilo attivo riaccende THP alle spalle del
servizio.

Quanto si guadagna spegnendole? La documentazione **non lo dice**, e questa pagina non lo inventa:
è una raccomandazione senza numero.

<a id="54-il-filesystem-e-lo-swap"></a>
### 5.4 Il filesystem, e lo swap

Sul filesystem [S-050](../Sources.md#s-050) è insolitamente netto:

> «When running MongoDB in production on Linux, you should use Linux kernel version 2.6.36 or
> later, with either the XFS or EXT4 filesystem. If possible, use XFS as it generally performs
> better with MongoDB.»
>
> «With the WiredTiger storage engine, using XFS is **strongly recommended** for data bearing
> nodes to avoid performance issues that may occur when using EXT4 with WiredTiger.»

È una decisione che si prende **prima** di installare: cambiare filesystem dopo significa
riformattare. Ed è la raccomandazione che il server ripete a ogni singolo avvio con l'`id` `22297`,
anche nel lab di questo repository ([V-021](../Sources.md#v-021)).

Sullo swap la posizione è più sfumata, e prevede due strategie, nessuna terza
([S-050](../Sources.md#s-050)):

> «MongoDB performs best where swapping can be avoided or kept to a minimum, as retrieving data
> from swap will always be slower than accessing data in RAM. However, if the system hosting
> MongoDB runs out of RAM, swapping can prevent the Linux OOM Killer from terminating the `mongod`
> process.»

Cioè: lo swap rallenta, ma è anche l'ultima cosa che si frappone fra il tuo database e l'OOM
Killer. Le due strategie ammesse sono assegnare swap e configurare il kernel perché lo usi solo
sotto forte pressione (`vm.swappiness` basso), oppure non assegnarne affatto e disabilitare del
tutto lo scambio. Quello che non si fa è lasciare il valore predefinito senza averci pensato.

Che cosa succede quando l'OOM Killer arriva davvero, e come appare nel log, è misurato in
[V-009](../Sources.md#v-009) e raccontato in
[`06-sviluppo/gestione-risorse-compose.md`](../06-sviluppo/gestione-risorse-compose.md).

<a id="55-numa"></a>
### 5.5 NUMA, se la macchina è grossa

Su hardware a più socket la memoria non è tutta ugualmente vicina a tutte le CPU, e MongoDB non
gradisce ([S-050](../Sources.md#s-050)):

> «Running MongoDB on a system with Non-Uniform Memory Access (NUMA) can cause a number of
> operational problems, including slow performance for periods of time and high system process
> usage.»

Il rimedio è una politica di *memory interleave*, cioè far comportare la macchina come se NUMA non
ci fosse. Su Linux:

```bash
sudo sysctl -w vm.zone_reclaim_mode=0
```

e l'avvio di `mongod` tramite `numactl`, che sotto `systemd` va configurato nel file di servizio.
Su Windows «memory interleaving must be enabled through the machine's BIOS»
([S-050](../Sources.md#s-050)).

La buona notizia è che non bisogna indovinare: «MongoDB checks NUMA settings on start up… If the
NUMA configuration may degrade performance, MongoDB prints a warning.» Come per THP e per il
filesystem, il server lo dice — basta leggere gli avvisi d'avvio, ed è il motivo per cui
[`03-amministrazione/log.md`](../03-amministrazione/log.md) insiste su
`getLog: "startupWarnings"`.

Su una macchina a un socket, come la maggior parte dei server virtuali, questa sezione non si
applica.

<a id="6-quello-che-cambia-dentro-un-container"></a>
## 6. Quello che cambia dentro un container

> **Questa sezione è misurata**, sullo stack `01-standalone` di questo repository
> ([V-021](../Sources.md#v-021)). Non verifica la procedura delle sezioni precedenti: mostra il
> **contrasto**, che è la cosa più utile che il lab possa dire su un'installazione che non ha
> eseguito.

L'immagine `mongo:7.0.40` è, letteralmente, l'installazione di questa pagina:

```console
$ cat /etc/os-release | head -2
PRETTY_NAME="Ubuntu 22.04.5 LTS"
NAME="Ubuntu"
$ cat /etc/apt/sources.list.d/mongodb-org.list
deb [ signed-by=/etc/apt/keyrings/mongodb.asc ] http://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse
```

Stesso Ubuntu Jammy, stesso repository ufficiale del passo 2. Quello che l'immagine ha tolto è
esattamente l'elenco delle cose che questa pagina insegna:

| in questa pagina | nel container del lab |
| --- | --- |
| `systemctl start mongod` | non esiste `systemd`: il processo 1 **è** `mongod` |
| `/etc/mongod.conf` | non esiste; le opzioni si passano sulla riga di comando |
| `/var/lib/mongodb`, `/var/log/mongodb` | `/data/db` e `stdout` ([ADR-0030](../Decision.md#adr-0030)) |
| utente `mongodb` | **conservato**: `ps -o user,pid,comm -p 1` risponde `mongodb 1 mongod` |
| `ulimit -n 64000` da configurare | già a **1 048 576**, fissato dal runtime |
| THP da spegnere | acceso, e **non spegnibile** da dentro il container |
| XFS raccomandato | `/data/db` è su **ext4** |

Le ultime tre righe si vedono negli avvisi d'avvio del lab:

```console
$ mongosh --quiet --eval 'db.adminCommand({getLog: "startupWarnings"}).log
    .forEach(r => { const o = JSON.parse(r); print(o.id + "  " + o.msg.substring(0, 78)) })'
22297   Using the XFS filesystem is strongly recommended with the WiredTiger storage
22120   Access control is not enabled for the database. Read and write access to dat
9068900 For customers running MongoDB 7.0, we suggest changing the contents of the f
```

Tre avvisi, e vanno letti diversamente: `22120` è una **scelta** di questo lab
([ADR-0005](../Decision.md#adr-0005)), mentre `22297` e `9068900` sono **proprietà del posto** —
il filesystem del volume e il kernel della macchina virtuale di Docker Desktop. Su un server
installato secondo questa pagina, quei due avvisi sono difetti da correggere; qui sono
caratteristiche dell'ambiente, e l'unica cosa da fare è saperlo.

Un dettaglio che sorprende: `docker compose exec` entra come `root`, ma il server gira come
`mongodb`, esattamente come dopo un `apt-get install mongodb-org`. La shell che si apre non ha i
privilegi del processo che si sta osservando.

<a id="7-disinstallare"></a>
## 7. Disinstallare

> **Avvertenza, da [S-048](../Sources.md#s-048):** «This process will *completely* remove MongoDB,
> its configuration, and *all* databases. This process is not reversible, so ensure that all of
> your configuration and data is backed up before proceeding.»

```bash
sudo service mongod stop
sudo apt-get purge "mongodb-org*"
sudo rm -r /var/log/mongodb
sudo rm -r /var/lib/mongodb
```

Il `purge` toglie i pacchetti e la configurazione; le due `rm` tolgono log e dati, che `apt` non
tocca. Chi salta le ultime due righe si ritrova un'installazione nuova che parte su un `dbPath`
pieno di dati vecchi.

---

## Cosa questa pagina non dice

- **Non è stata eseguita.** Vale la riserva in testa: la fonte è la documentazione ufficiale,
  non una prova.
- **Non copre le altre distribuzioni.** Red Hat, SUSE, Amazon Linux e Debian hanno tutorial
  propri, con repository e nomi di pacchetto diversi. Le sezioni [5.2](#52-ulimit-e-il-motivo-per-cui-si-contano-a-due-a-due),
  [5.3](#53-transparent-huge-pages) e [5.4](#54-il-filesystem-e-lo-swap) valgono comunque, con
  l'insidia del percorso THP su RHEL già segnalata.
- **Non copre l'autenticazione.** Abilitarla è il passo successivo obbligatorio prima di toccare
  `bindIp`, e in questo repository non c'è ([ADR-0005](../Decision.md#adr-0005)).
- **Non copre replica set e sharding installati sul sistema operativo.** L'architettura sta in
  [`02-architetture/`](../02-architetture/standalone.md); la messa in opera passa da qui più
  `rs.initiate()`, e i comandi sono in
  [`04-mongosh/guida-mongosh.md`](../04-mongosh/guida-mongosh.md#32-replica-set-non-eseguito-qui).
- **Non dice quanto si guadagna** spegnendo THP o scegliendo XFS. Nessuna delle fonti dà un
  numero, e questa pagina non ne inventa uno.

---

**Decisioni correlate:** [ADR-0037](../Decision.md#adr-0037) (pagine scritte da fonte e dichiarate
non eseguite), [ADR-0024](../Decision.md#adr-0024) (la gerarchia delle fonti),
[ADR-0005](../Decision.md#adr-0005) (il lab senza autenticazione),
[ADR-0030](../Decision.md#adr-0030) (i log su `stdout` in container),
[ADR-0026](../Decision.md#adr-0026) (perché un tag non è un contratto),
[ADR-0028](../Decision.md#adr-0028) (la versione 7.0 del lab).

**Fonti:** [S-005](../Sources.md#s-005), [S-048](../Sources.md#s-048), [S-049](../Sources.md#s-049), [S-050](../Sources.md#s-050), [S-051](../Sources.md#s-051), [S-052](../Sources.md#s-052), [V-009](../Sources.md#v-009), [V-010](../Sources.md#v-010), [V-021](../Sources.md#v-021)
