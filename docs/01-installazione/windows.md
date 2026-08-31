# Installare MongoDB su Windows

> **Riserva dichiarata.** Questa procedura **non è stata eseguita**. In questo progetto non esiste
> una macchina Windows: la macchina di sviluppo è un Mac con Docker Desktop. Ogni passo, ogni
> percorso e ogni nome di file di questa pagina viene dalla documentazione ufficiale MongoDB per la
> versione 7.0 — [S-049](../Sources.md#s-049), [S-050](../Sources.md#s-050) — e da
> [S-005](../Sources.md#s-005) per la parte sul keyfile, ed è citato accanto al punto in cui
> compare. Il primo a provarla davvero sarà chi legge ([ADR-0037](../Decision.md#adr-0037)).
>
> A differenza della [gemella per Linux](linux.md), qui non c'è nemmeno una sezione misurata: il
> container del lab è Ubuntu, e non ha niente da dire su Windows.

---

<a id="1-prima-di-cominciare"></a>
## 1. Prima di cominciare

<a id="11-le-versioni-supportate-e-una-esclusione-netta"></a>
### 1.1 Le versioni supportate, e un'esclusione netta

MongoDB 7.0 Community Edition supporta Windows Server 2022, Windows Server 2019 e Windows 11, solo
a 64 bit su architettura x86_64 ([S-049](../Sources.md#s-049)). Poi c'è una frase che vale la pena
leggere due volte:

> «MongoDB is not supported on Windows Subsystem for Linux (WSL). To run MongoDB on Linux, use a
> supported Linux system.»

Non è un'avvertenza sulle prestazioni: è un'esclusione dal supporto. Chi vuole il MongoDB Linux su
una macchina Windows ha due strade sostenute — una macchina virtuale vera, oppure un container —
e WSL non è nessuna delle due.

Sulla virtualizzazione, un'insidia specifica ([S-049](../Sources.md#s-049)): Oracle offre un
supporto sperimentale per VirtualBox su host Windows dove gira Hyper-V, ma Microsoft non supporta
VirtualBox su Hyper-V. «Disable Hyper-V if you want to install MongoDB on Windows using
VirtualBox.»

<a id="12-la-shell-non-e-inclusa"></a>
### 1.2 La shell non è inclusa

È la differenza più concreta con Linux, e la documentazione la ripete due volte perché evidentemente
in due non bastano ([S-049](../Sources.md#s-049)):

> «The MongoDB Shell (`mongosh`) is not installed with MongoDB Server. You need to follow the
> `mongosh` installation instructions to download and install `mongosh` separately.»
>
> «The `.msi` installer does not include `mongosh`.»

Su Ubuntu il pacchetto `mongodb-org` si tira dietro `mongodb-mongosh`; su Windows no. Installato il
server, il computer non ha ancora un modo per parlarci. La shell si scarica e si installa a parte, e
conviene farlo **subito dopo**, non «quando servirà».

<a id="2-installare"></a>
## 2. Installare, con la procedura guidata

Il `.msi` installa i binari **e** un file di configurazione predefinito, che finisce nella directory
di installazione come `bin\mongod.cfg` ([S-049](../Sources.md#s-049)).

**1. Scaricare l'installer.** Dal [MongoDB Download Center](https://www.mongodb.com/try/download/community):
scegliere la versione, `Windows` come piattaforma, `msi` come pacchetto.

**2. Lanciarlo.** Doppio clic sul file `.msi`, di norma nella cartella `Downloads`.

**3. Seguire la procedura guidata.** Due schermate contano davvero.

*Choose Setup Type* — `Complete` installa MongoDB e gli strumenti nelle posizioni predefinite;
`Custom` permette di scegliere quali eseguibili installare e dove.

*Service Configuration* — è qui che si decide se MongoDB sarà un **servizio di Windows**. Se sì:

| campo | che cosa significa |
| --- | --- |
| account | il servizio gira come `Network Service` oppure come un utente locale o di dominio |
| *Service Name* | il nome del servizio, predefinito `MongoDB`; deve essere unico sulla macchina |
| *Data Directory* | corrisponde a `--dbpath` |
| *Log Directory* | corrisponde a `--logpath` |

Sulle ultime due, un dettaglio che risparmia un errore di permessi: «If the directory does not
exist, the installer will create the directory and sets the directory access to the service user»
([S-049](../Sources.md#s-049)). Lasciare che sia l'installer a crearle è la strada sicura; crearle
prima a mano, e dimenticare i permessi, è la strada che porta a un servizio che non parte.

Per un utente locale esistente si indica un punto (`.`) come *Account Domain*, più nome e password;
per un utente di dominio, dominio, nome e password.

**4. Installare `mongosh` a parte.** Vedi [§1.2](#12-la-shell-non-e-inclusa). Durante
l'installazione della shell, «be sure to add the path to your `mongosh.exe` binary to your `PATH`
environment variable» ([S-049](../Sources.md#s-049)). Poi si apre un **nuovo** interprete dei
comandi — quello già aperto non vede la variabile aggiornata — e si scrive `mongosh.exe`.

<a id="3-governare-il-servizio"></a>
## 3. Governare il servizio

Se MongoDB è stato installato come servizio, parte da solo: «The MongoDB service starts upon
successful installation» ([S-049](../Sources.md#s-049)).

Avvio, arresto e riavvio passano dalla console dei Servizi: si individua il servizio `MongoDB`, si
fa clic destro, `Start` o `Stop`.

Per cambiare la configurazione la sequenza è obbligata: **prima si ferma il servizio**, poi si
modifica `<install directory>\bin\mongod.cfg`, poi si riavvia. Vale la stessa regola di Linux — la
configurazione si legge all'avvio, non c'è ricarica a caldo.

Il file `mongod.cfg` usa lo stesso formato YAML di `/etc/mongod.conf`: cambia il percorso, non la
sintassi. È l'unica cosa che si può portare da un sistema all'altro senza tradurla.

<a id="4-senza-servizio-dalla-riga-di-comando"></a>
## 4. Senza servizio, dalla riga di comando

Si può anche non installare il servizio e lanciare `mongod.exe` a mano
([S-049](../Sources.md#s-049)). Con un'avvertenza in evidenza: «You must open the command
interpreter as an Administrator.»

**1. Creare la directory dei dati.** Il percorso predefinito è `\data\db` sull'unità da cui si
avvia MongoDB:

```bat
cd C:\
md "\data\db"
```

**2. Avviare il server.**

```bat
"C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe" --dbpath="c:\data\db"
```

Se tutto va bene, l'interprete dei comandi mostra:

```text
[initandlisten] waiting for connections
```

È la stessa riga che nel lab di questo repository compare nel log JSON con il proprio `id`, e che
segna il momento in cui il server è pronto ([`03-amministrazione/log.md`](../03-amministrazione/log.md)).

**3. Il firewall.** «Depending on the Windows Defender Firewall settings on your Windows host,
Windows may display a Security Alert dialog box about blocking "some features" of
`C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe` from communicating on networks»
([S-049](../Sources.md#s-049)). La scelta di quale rete autorizzare non è una formalità: autorizzare
la rete pubblica significa esporre il database, e va letta la [sezione 5](#5-la-messa-a-punto-che-su-windows-e-diversa)
prima di cliccare.

<a id="5-la-messa-a-punto-che-su-windows-e-diversa"></a>
## 5. La messa a punto, che su Windows è diversa

Il confronto con la pagina Linux è più interessante dell'elenco:

| argomento | Linux | Windows |
| --- | --- | --- |
| `ulimit` | sette valori da configurare, `-n` a 64000 ([S-052](../Sources.md#s-052)) | **non esiste** |
| Transparent Huge Pages | da disabilitare con un servizio dedicato ([S-051](../Sources.md#s-051)) | **non esiste**: è un meccanismo del kernel Linux |
| NUMA | `vm.zone_reclaim_mode=0` più `numactl` | «memory interleaving must be enabled through the machine's BIOS» ([S-050](../Sources.md#s-050)) |
| filesystem | XFS «strongly recommended» ([S-050](../Sources.md#s-050)) | la raccomandazione non si applica: è formulata per XFS ed EXT4 |
| `bindIp` | `127.0.0.1` all'avvio | identico, e con la stessa avvertenza |
| permessi del keyfile | controllati | **non controllati** ([S-005](../Sources.md#s-005)) |

Due righe di questa tabella meritano il proprio paragrafo.

<a id="51-bindip-e-la-stessa-avvertenza"></a>
### 5.1 `bindIp`, e la stessa avvertenza

Anche su Windows il server nasce chiuso ([S-049](../Sources.md#s-049)): `bindIp` vale `127.0.0.1`,
`mongod.exe` accetta connessioni solo dalla stessa macchina, e non può inizializzare un replica set
finché quel valore non punta a un'interfaccia raggiungibile. Il valore si cambia in
`bin\mongod.cfg` oppure con `--bind_ip` sulla riga di comando.

L'avvertenza è quella della pagina Linux, parola per parola:

> «Before you bind your instance to a publicly-accessible IP address, you must secure your cluster
> from unauthorized access.»

Con il Windows Defender Firewall di mezzo ([§4](#4-senza-servizio-dalla-riga-di-comando)) è facile
credere che il firewall basti. Non basta: il firewall decide chi arriva alla porta, l'autenticazione
decide chi entra nel database. Sono due controlli diversi, e MongoDB parte senza il secondo —
«By default, authorization is not enabled» ([S-050](../Sources.md#s-050)).

<a id="52-il-keyfile-e-il-controllo-che-su-windows-non-ce"></a>
### 5.2 Il keyfile, e il controllo che su Windows non c'è

È la differenza che conta di più fra i due sistemi, e non compare in nessuna pagina di
installazione: sta nel tutorial sull'autenticazione fra membri di un replica set
([S-005](../Sources.md#s-005)).

> «On UNIX systems, the keyfile must not have group or world permissions. On Windows systems,
> keyfile permissions are not checked.»

Su Linux, un keyfile con i permessi sbagliati impedisce l'avvio: il server rifiuta di partire, e
l'errore è chiaro. Su Windows quel controllo **non viene fatto affatto**. Un keyfile leggibile da
chiunque su una macchina Windows non produce nessun errore, nessun avviso, nessuna riga di log — e
chi legge quel file può autenticarsi come membro del replica set.

La conseguenza pratica è che su Windows la protezione del keyfile è interamente a carico
dell'amministratore, tramite le ACL di NTFS, e nessuno gli dirà mai che se n'è dimenticato. Una
procedura di installazione portata da Linux a Windows perde questa rete di sicurezza senza
segnalarlo.

Per completezza, [S-005](../Sources.md#s-005) ricorda anche il perimetro d'uso: «Use keyfiles only
for testing and development environments» — in produzione la raccomandazione è X.509. Il tema è di
`feature/02`, dove il replica set esisterà davvero.

<a id="6-aggiornare-e-disinstallare"></a>
## 6. Aggiornare

Una regola che sorprende chi arriva da `apt` ([S-049](../Sources.md#s-049)):

> «If you installed MongoDB with the Windows installer (`.msi`), the `.msi` automatically upgrades
> within its release series (e.g. 7.2.1 to 7.2.2). Upgrading a full release series (e.g. 6.0 to
> 7.0) requires a new installation.»

Cioè: dentro la stessa riga di versione un `.msi` più recente si installa sopra quello che c'è già,
senza disinstallare prima; il salto di riga di versione vuole «a new installation». Attenzione a cosa
la frase *non* dice: descrive come si comporta l'installatore quando lo si esegue, non che Windows
vada a cercarlo. Il `.msi` nuovo lo scarica una persona, ogni volta.

È qui la differenza con Ubuntu, dove il repository configurato è quello di una riga di versione e
`apt-get upgrade` sposta avanti da solo l'ultima disponibile dentro quella riga
([pagina Linux](linux.md#2-installare)). Su Windows nessun automatismo tiene il conto al posto tuo,
ed è un motivo in più per sapere quale riga di versione sta girando prima di programmare un
aggiornamento.

---

## Cosa questa pagina non dice

- **Non è stata eseguita**, e non c'è nemmeno una misura di contrasto come nella
  [pagina Linux](linux.md#6-quello-che-cambia-dentro-un-container). È la pagina più teorica del
  repository, e lo dichiara.
- **Non copre l'installazione di `mongosh`**, che ha una procedura propria: qui si dice solo che
  serve e che va fatta a parte.
- **Non copre MongoDB Compass**, che l'installer propone di installare. È un'interfaccia grafica
  utile e fuori tema per un talk che mostra la riga di comando.
- **Non copre l'autenticazione.** Vale quanto detto per Linux: è il passo obbligatorio prima di
  toccare `bindIp`, e in questo repository non c'è ([ADR-0005](../Decision.md#adr-0005)).
- **Non copre l'esecuzione su Windows tramite Docker Desktop**, che è un'altra cosa ancora: in quel
  caso il MongoDB che gira è quello Linux dell'immagine, e valgono le pagine di
  [`02-architetture/`](../02-architetture/standalone.md).

---

**Decisioni correlate:** [ADR-0037](../Decision.md#adr-0037) (pagine scritte da fonte e dichiarate
non eseguite), [ADR-0024](../Decision.md#adr-0024) (la gerarchia delle fonti),
[ADR-0005](../Decision.md#adr-0005) (il lab senza autenticazione, e il keyfile),
[ADR-0028](../Decision.md#adr-0028) (la versione 7.0 del lab).

**Fonti:** [S-005](../Sources.md#s-005), [S-049](../Sources.md#s-049), [S-050](../Sources.md#s-050), [S-051](../Sources.md#s-051), [S-052](../Sources.md#s-052)
