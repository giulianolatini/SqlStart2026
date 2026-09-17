# 13. Il container sulla rete, e la scoperta che si vede

> Il principio in una riga: **un client MongoDB non parla con l'indirizzo che gli hai dato, parla
> con quelli che il cluster gli nomina** — e finché stai fuori dalla rete in cui quei nomi
> esistono, non puoi né vederlo né mostrarlo.

Questa applicazione è nata per far vedere una cosa sola: che cosa succede *dentro* un client mentre
il cluster sotto di lui cambia forma. Per dodici capitoli l'ha fatto da fuori — dal portatile,
attraverso una porta pubblicata — e da fuori quella cosa **non si vede**. Un replica set con tre
membri sani, interrogato dall'host, si legge `ReplicaSetNoPrimary`
([M-019](Sources.md#m-019)); per farlo funzionare bisogna spegnere la scoperta con
`directConnection=true`, e allora la topologia si legge `SINGOLA` mentre il ruolo del server è
`RSPrimary`. Due bugie contemporanee, entrambe innocue, entrambe fatali per una demo che di
topologie parla.

[ADR-0012](../../docs/Decision.md#adr-0012) l'aveva scritto due mesi prima che ci fosse del codice,
e aveva chiuso con una riserva dichiarata: la documentazione di PyMongo **non afferma** che il
driver, dopo essersi collegato, usi gli host memorizzati nella configurazione del set invece di
quello che gli hai passato; se si vuole affermarlo, va mostrato in demo. Questo capitolo è il posto
in cui quella riserva si chiude, in due modi indipendenti: leggendo una specifica che quella frase
la contiene per intero, e misurandola.

E il modo in cui si chiude è anche il motivo per cui l'applicazione, da questo task in poi, ha un
Dockerfile.

---

## Il problema, in due indirizzi

Lo stesso replica set ha due nomi a seconda di dove sta chi guarda:

| | dall'host | dalla rete Compose |
|---|---|---|
| indirizzo | `localhost:27021` | `mongo-rs-1:27017`, `mongo-rs-2:27017`, `mongo-rs-3:27017` |
| `directConnection` | `true`, obbligatoriamente | `false` |
| `replicaSet` | non dichiarabile | `rs0` |
| topologia letta | `singola` | `replicaset` con primario |
| che cosa mostra | un server | **la scoperta** |

La colonna di sinistra non è una versione peggiore della destra: è un'altra cosa. La porta 27021
esiste solo sull'host, i nomi `mongo-rs-*` esistono solo dentro la rete, e nessuno dei due lati
vede gli indirizzi dell'altro. Il talk ha bisogno della colonna di destra; lo sviluppo quotidiano
ha bisogno di quella di sinistra, perché sull'host non c'è niente da ricostruire e il debugger si
attacca.

Da qui tutto il resto: un'immagine, un servizio in ogni stack, una variabile che dice da che parte
si sta, e un `Makefile` che sceglie.

---

## Che cosa dice la specifica, e dove *non* lo dice

La riserva di ADR-0012 diceva che la documentazione di PyMongo non afferma la cosa. È ancora vero.
Ciò che si è scoperto è che **la afferma un'altra fonte**, e in termini normativi: la specifica
*Server Discovery And Monitoring* del repository `mongodb/specifications`
([A-016](Sources.md#a-016)), quella che tutti i driver ufficiali implementano.

Nella sottoroutine `updateRSWithoutPrimary` il client cicla «for address in description's "hosts",
"passives", "arbiters"» e, per ogni indirizzo che ancora non conosce, aggiunge una
`ServerDescription` di tipo `Unknown` e comincia a sorvegliarlo. E nella motivazione, in maiuscolo
come si usa lì:

> While no known primary, client MUST **add** servers non-primaries' host lists, but MUST NOT
> remove.

La *seed list* la stessa specifica la definisce per contrasto: «Server addresses provided client in
initial configuration, example connection string» — cioè **ciò da cui si parte, non ciò con cui si
finisce**.

C'è una lezione di metodo in questa differenza, e vale più del fatto tecnico. La riserva era
corretta: il manuale di PyMongo davvero non lo dice. Ma un driver MongoDB non implementa il proprio
manuale, implementa una specifica scritta una volta per tutti i linguaggi, e quella specifica sta
in un repository pubblico che nessuno pensa di aprire perché non ha l'aria della documentazione. La
risposta era a un livello sopra a quello in cui la si cercava.

Per la sala, la frase da tenere è questa: **la stringa di connessione non è un indirizzo, è un
punto di partenza.**

Un dettaglio operativo, perché è costato una fetch in più: la fonte citata è il file *sorgente* su
`raw.githubusercontent.com`, non la pagina resa. La resa di GitHub tronca i blocchi lunghi, e le
frasi che qui contano stanno dentro uno pseudocodice.

---

## La prova che chiude la riserva

Una specifica dice che cosa un driver *deve* fare. Che PyMongo 4.17.0 lo faccia davvero è un'altra
affermazione, e va misurata ([M-036](Sources.md#m-036)).

La misura ha una sola difficoltà, ed è di disegno sperimentale. La configurazione di produzione
passa **tre** semi al replica set, e con tre semi trovare tre membri non dimostra niente: potrebbe
averli semplicemente usati tutti. La prova doveva partire da **un** seme, e non dal primario:

```
seme passato       : mongo-rs-2:27017
tipo di topologia  : ReplicaSetWithPrimary
nome del set       : rs0
server conosciuti  : 3
  mongo-rs-1:27017    RSPrimary
  mongo-rs-2:27017    RSSecondary
  mongo-rs-3:27017    RSSecondary
primario scelto    : mongo-rs-1:27017
host dalla config  : ['mongo-rs-1:27017', 'mongo-rs-2:27017', 'mongo-rs-3:27017']
```

Il client ha finito per scrivere su un server — `mongo-rs-1` — il cui nome **nessuno gli aveva mai
dato**. L'ha saputo dalla risposta di `hello` di un secondario, come la specifica prescrive.

La prova è ripetibile e vive in
[`tests/integration/test_container.py::test_un_seme_solo_basta_a_trovare_tutti_e_tre`](../tests/integration/test_container.py):
un programma di tre righe passato al container con `--entrypoint python`, così che la
configurazione di produzione resti quella vera e l'esperimento resti un esperimento.

**Riserva onesta:** questa misura vale per un set *con* il primario disponibile. La specifica
distingue il caso senza primario — dove il client aggiunge ma non toglie — e quel caso qui non è
stato misurato. Lo sarà al Task 13, che è dove il failover si mette in scena.

---

## Due punti di vista, un tipo solo

La mappa dei bersagli in
[`infrastructure/bersagli.py`](../src/mongolab/infrastructure/bersagli.py) fino al Task 11 aveva un
indirizzo per stack. Adesso ne ha due, e la forma in cui li tiene è una decisione
([ADR-0090](../../docs/Decision.md#adr-0090)).

I fatti che cambiano insieme sono tre — i semi, `directConnection`, il nome del set — e stanno in
un tipo unico:

```python
@dataclass(frozen=True, slots=True)
class Vista:
    semi: tuple[tuple[str, int], ...]
    diretto: bool
    replica: str | None = None
```

Non tre campi paralleli su `Bersaglio`, e la ragione non è estetica: `directConnection=True` con
più di un seme **non è una configurazione discutibile**, è un `ConfigurationError` sollevato alla
costruzione del client, prima che esista una connessione. Tre campi separati permettono di
scriverla; un tipo che si costruisce intero rende la combinazione impossibile un errore che si
vede leggendo, invece che un errore che si scopre eseguendo.

`Bersaglio` ne tiene due, `da_host` e `da_rete`, e un metodo che sceglie:

```python
def vista(self, punto: PuntoDiVista) -> Vista:
    return self.da_host if punto is PuntoDiVista.HOST else self.da_rete
```

### Perché una variabile d'ambiente e non un'opzione

Chi sceglie il punto di vista? Non chi scrive la riga di comando. La riga è la stessa nei due casi
— `mongolab stats --target rs` — e ciò che cambia è **dove** viene eseguita. Il punto di vista è
una proprietà del processo, non dell'invocazione, e il posto in cui una proprietà del processo si
dichiara è l'ambiente:

```yaml
environment:
  MONGOLAB_PUNTO_DI_VISTA: rete
```

Tre righe, una per file Compose, e nessuno deve ricordarsene mai più. Sull'host la variabile non la
scrive nessuno, e l'assenza vale `host`, che è il predefinito giusto per chi sviluppa.

L'alternativa scartata più tentante era **dedurlo**: provare a risolvere `mongo-rs-1` e vedere se
funziona. Sarebbe stato elegante e sbagliato. Una risoluzione DNS che fallisce costa secondi e può
fallire per dieci motivi che non c'entrano; dedurre una cosa che si può dichiarare significa
scambiare un fatto certo con un indizio.

### La stringa vuota vale come assente, un valore sbagliato no

```python
detto = ambiente.get(VARIABILE_PUNTO_DI_VISTA, "").strip().lower()
if not detto:
    return PuntoDiVista.HOST
try:
    return PuntoDiVista(detto)
except ValueError:
    raise PuntoDiVistaSconosciuto(...)
```

Due comportamenti diversi per due casi che sembrano lo stesso, e la differenza è misurata sul
comportamento di Compose: davanti a `MONGOLAB_PUNTO_DI_VISTA: ${QUALCOSA}` con `QUALCOSA` non
definita, Compose **non toglie** la variabile — la mette a stringa vuota. Trattare il vuoto come un
errore vorrebbe dire far fallire un container per un'interpolazione a vuoto.

Un valore *sbagliato* invece ferma tutto, e non ripiega. Ripiegare vorrebbe dire che dentro un
container l'applicazione prova `localhost:27021`, che lì non è un errore immediato: è un timeout di
venti secondi che parla di una porta chiusa invece che di un refuso. Il messaggio elenca i due
valori validi, perché chi ha sbagliato sta quasi sempre scrivendo una parola vicina.

### `directConnection=true` anche dalla rete, ma su un solo stack

È il Passo 3 del Task 12, e la sua motivazione è più corta della sua riga di codice:

```python
"standalone": Bersaglio(
    ...
    da_rete=Vista(semi=(("mongo-standalone", PORTA_INTERNA),), diretto=True),
),
```

Su un mongod solo non c'è niente da scoprire. `directConnection=true` lì non toglie una scena: dice
la verità sulla topologia, e la fotografia legge `singola` perché singola lo è davvero.

Gli altri due stanno dall'altra parte, ma per ragioni diverse. Il replica set dichiara **tre** semi
perché con un seme solo l'avvio dipenderebbe da quale membro è acceso — e in sala il membro giù è
una scena prevista, non un imprevisto. Lo sharded ne dichiara **uno**, `mongos:27017`, perché il
secondo router esiste nel solo profilo `completo`: dichiarare sempre `mongos2` vorrebbe dire
dichiarare un nome che di norma non risolve. Verso un mongos `replicaSet` resta `None`, che non è
una dimenticanza: un router non è membro di nessun set, e dichiararglielo sarebbe un errore di
categoria.

Una nota di dettaglio che sorprende chi guarda i tre `compose.yaml`: **dentro la rete la porta è
27017 su tutti e tre**. Le porte diverse che si leggono nei file — 27021, 27117 — sono mappature
verso l'host e dentro non esistono. Visti da dentro, i tre stack si somigliano molto più di quanto
sembri da fuori, e la differenza che resta è esattamente quella architetturale.

---

## L'immagine

Il [`Dockerfile`](../Dockerfile) è corto e quasi tutto commento. Le decisioni che contiene sono
cinque, e nessuna è ovvia.

### Le basi arrivano da fuori, pinnate

```dockerfile
ARG PYTHON_IMAGE
ARG UV_IMAGE

FROM ${UV_IMAGE} AS uv
FROM ${PYTHON_IMAGE}
```

Scrivere `FROM python:3.13-slim` avrebbe funzionato, e sarebbe stata la stessa promessa che i file
Compose fanno con `image:` — senza il digest. Un tag mobile è un contenuto che domani è un altro
contenuto, e questo repository ha un vincolo che rende la cosa non negoziabile: deve costruire e
girare **senza rete** ([ADR-0009](../../docs/Decision.md#adr-0009)). I valori arrivano da
`tools/images.env` attraverso `build.args`, e `make app-image` li passa senza che nessuno li
scriva a mano.

Il primo stadio esiste per copiare un file solo, `/uv`. Installare uv con pip dentro l'immagine
finale avrebbe voluto dire una risoluzione di dipendenze in più, fatta in rete, per ottenere lo
strumento che serve a non farne.

### La riga che non c'è

In cima al Dockerfile **non** c'è `# syntax=docker/dockerfile:1`, e la sua assenza è una decisione.
Quella riga fa scaricare al demone l'immagine del frontend BuildKit da un registro: una dipendenza
di rete in più, non pinnata, in un repository il cui vincolo principale è quello appena detto. La
sintassi predefinita basta per tutto ciò che serve qui.

### L'ambiente virtuale fuori da `/app`

```dockerfile
ENV UV_PROJECT_ENVIRONMENT=/opt/mongolab
```

È la riga che rende possibile il bind mount, ed è il tipo di dettaglio che si scopre rompendolo. Il
Passo 1 vuole che una modifica al sorgente non richieda una ricostruzione (§6.5 del design), quindi
il sorgente dell'host si monta su `/app/src`. Se l'ambiente virtuale stesse in `/app/.venv`,
montare `/app` lo coprirebbe — o peggio, ci metterebbe sopra il `.venv` di macOS, che dentro Linux
non è eseguibile. Spostandolo in `/opt/mongolab` i due mondi non si toccano.

Il progetto è installato in modo **modificabile**, che è il comportamento predefinito di `uv sync`
per la radice del progetto: il collegamento punta a `/app/src`, cioè esattamente al percorso su cui
il mount arriva. Modificare un file e rieseguire il comando basta.

### Due `COPY`, `--frozen`, `--no-dev`

```dockerfile
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev
```

Due `COPY` e non uno, perché il manifesto cambia di rado e il sorgente a ogni modifica: con un
`COPY . .` ogni riga toccata in `cli.py` invaliderebbe il livello che installa pymongo, typer e
rich — cioè l'unico che va in rete.

`--frozen` è ciò che rende la costruzione ripetibile: uv usa `uv.lock` così com'è e **fallisce** se
il lock non corrisponde a `pyproject.toml`, invece di risolvere di nuovo e installare in silenzio
qualcosa di diverso da ciò che le prove hanno visto. `--no-dev` lascia fuori pytest e mypy: in
questa immagine non si prova niente, le due suite girano sull'host dove hanno il repository intero
e il socket Docker con cui accendono gli stack veri.

`PYTHONDONTWRITEBYTECODE=1` non è igiene generica. Il sorgente arriva da un bind mount dell'host, e
senza quella riga il container ci scriverebbe dentro i propri `__pycache__`: file di un'altra
architettura, di proprietà di un altro utente, in mezzo al codice di chi sviluppa. La stessa
variabile ha già una storia qui — al Task 6 due mutazioni della stessa dimensione scritte nello
stesso secondo hanno condiviso il `.pyc`, e una prova ha mentito ([M-011](Sources.md#m-011)).

`PYTHONUNBUFFERED=1` riguarda invece la demo: quando l'uscita non è un terminale — `make app-watch
| tee`, o una registrazione — Python bufferizza a blocchi, e la cronaca di un failover comparirebbe
a scatti da 8 KiB. Il fatto da mostrare è *quando* le cose succedono; un buffer lo distrugge.

### `ENTRYPOINT` e non `CMD`

```dockerfile
ENTRYPOINT ["mongolab"]
CMD ["--help"]
```

L'immagine **è** l'applicazione: `docker compose run --rm app stats --target rs` passa le tre parole
finali come argomenti. Con `CMD` al posto di `ENTRYPOINT`, la stessa riga avrebbe cercato un
eseguibile di nome «stats».

---

## Il servizio, dentro i tre stack

Perché il client scopra i membri per nome di servizio deve stare **sulla rete di quello stack**, e
in Compose una rete appartiene a un progetto. Il servizio `app` è quindi scritto in ognuno dei tre
`compose.yaml` ([ADR-0091](../../docs/Decision.md#adr-0091)), identico nei tre.

La ripetizione è reale ed è accettata: è la stessa scelta che il repository fa dal principio per i
tre stack, dove ogni file si legge da solo perché è materiale didattico prima che infrastruttura.
Il prezzo — tre blocchi che possono divergere — si paga con un controllo invece che con
un'astrazione, e il controllo sta in `tools/tests/test_coerenza_repo.py`.

Tre assenze meritano più attenzione delle presenze.

**Niente `container_name`,** ed è l'unico servizio del repository a non averlo. `run` crea un
container nuovo a ogni invocazione: con un nome fisso, due comandi lanciati insieme — la cronaca in
una finestra e il carico in un'altra, che è precisamente la scena del Blocco 2 — collidono.

**Niente `depends_on`.** Sarebbe comodo e sarebbe sbagliato: `run` avvia da sé le dipendenze
dichiarate, quindi `make app-stats` **accenderebbe** lo stack invece di dire che è spento. Che lo
stack sia in piedi lo si chiede a `make up-01`; se non lo è, la risposta giusta è un errore di
connessione.

**Un profilo,** `strumenti`, che tiene il servizio fuori da `docker compose up`. Senza, `up -d
--wait` avvierebbe anche l'applicazione, che eseguirebbe `--help` e uscirebbe subito — e `--wait`
resterebbe ad aspettare la salute di un container già finito. `docker compose run` attiva da sé il
profilo del servizio che nomina, quindi non c'è niente da ricordare.

### La credenziale, che non passa dalla riga di comando

Dall'host la credenziale si legge dal `.env` dello stack, che non sta nel repository
([ADR-0014](../../docs/Decision.md#adr-0014)). Dentro il container quel file non esiste: c'è `/app`
e basta, e cercarlo comunque farebbe risalire `radice()` fino a `/` per poi lamentare un repository
mancante — che è la cosa sbagliata da dire a chi ha dimenticato una variabile. Dalla rete i valori
arrivano dall'ambiente, con gli stessi due nomi.

Il passaggio rispetta [ADR-0054](../../docs/Decision.md#adr-0054): la password **non compare mai su
una riga di comando**. Non viene passata con `-e` al client `docker`; è `--env-file` a darla a
Compose, che la interpola dentro `environment:`. Una chiave sola, due trasporti, e in nessuno dei
due il valore passa per `ps`.

---

## La regola del digest, spostata di un livello

`tools/check_stack.py` pretende che ogni servizio dichiari un'immagine pinnata per digest e nota a
`tools/images.env`. Il servizio `app` non può obbedire: la sua immagine non viene da un registro.

Qui il repository ha una regola su come si trattano le regole — se una vieta qualcosa di legittimo,
si apre la sede che manca invece di aggirarla — e la sede aperta è
[ADR-0093](../../docs/Decision.md#adr-0093): **un servizio che dichiara `build:` si giudica sulle
righe `FROM` del suo Dockerfile.** Il controllo risolve il Dockerfile a partire da `build.context`,
segue i `${ARG}` attraverso `build.args`, salta gli stadi intermedi, e protesta se una base è
mobile, sconosciuta o non risolvibile.

Lo scopo originale non si sposta di un millimetro: nessun bit arriva dalla rete senza che qualcuno
l'abbia fissato. Per un servizio che si scarica, quei bit sono la sua immagine; per uno che si
costruisce, sono le sue basi — e sono le uniche che vadano davvero in rete.

### La motivazione era sbagliata, e la decisione no

Vale la pena raccontare questo pezzo per intero, perché è il tipo di errore che sopravvive alle
revisioni.

La prima stesura di questa regola era argomentata così: *un'immagine costruita in locale non ha un
digest, quindi non può essere pinnata*. Suona ovvio. È falso, e a smentirlo è bastato guardare
([M-037](Sources.md#m-037)): con l'archivio immagini di containerd — quello attivo su questa Docker
Desktop — l'`Id` di un'immagine **è** il digest del suo manifesto, tanto per le immagini scaricate
quanto per quelle costruite in casa, e `docker image inspect mongolab@sha256:…` la trova.

Il punto vero è un altro, e regge lo stesso: quel digest **nessun registro l'ha mai servito**,
quindi non è verificabile da fuori, e cambia a ogni ricostruzione. Metterlo in `images.env` darebbe
a `pull-images.sh --verify` una cosa da cercare in rete che in rete non c'è, e la mattina del talk
il preflight fallirebbe accusando la cache di un difetto che non ha.

La stessa riga di ragionamento dava la risposta giusta e la spiegazione sbagliata, e solo la
seconda si sarebbe portata dietro l'errore — nella docstring del controllo, nei commenti dei tre
`compose.yaml`, e in una slide. Con il vecchio archivio a grafo, per giunta, la premessa sarebbe
stata **vera per caso**: `RepoDigests` resta vuoto finché l'immagine non è spinta. Un buon
promemoria del fatto che una premessa plausibile e mai verificata è esattamente ciò che una misura
serve a cogliere.

`make stack-check` dopo tutto questo dice **«Stack conformi: 3.»**

---

## Il preflight, e le due immagini nuove in `images.env`

Il Passo 4 chiede che l'immagine dell'applicazione entri fra quelle da avere prima del talk. Entra
in due modi diversi, ed è la distinzione che conta.

Le **basi** entrano in `tools/images.env` come le altre — `PYTHON_IMAGE` e `UV_IMAGE`, pinnate per
digest — perché sono l'unica parte della costruzione che venga dalla rete. Per aggiungerle senza
riscaricare tutto il resto, `pull-images.sh` ha imparato a ricevere dei nomi:

```sh
make images-pull NOMI="PYTHON_IMAGE UV_IMAGE"
```

Senza nomi le riscarica tutte, che è ciò che serve quando si cambia versione di MongoDB, e ciò che
**non** si vuole quando si aggiunge un'immagine: `mongo:7.0` è un tag mobile, e il lab resta sulla
7.0.40 per decisione. (Dettaglio di implementazione con una storia: niente array associativi, perché
su macOS `/bin/bash` è ancora la 3.2 e `declare -A` non esiste — lo script morirebbe alla prima
riga invece che al primo uso.)

L'**immagine costruita** invece non entra in `images.env`, per il motivo appena detto, ed entra
nel preflight come presenza da verificare:

```
✓ l'immagine dell'applicazione è in cache — mongolab:0.1.0
```

Il controllo non scrive il tag a mano: lo estrae dal `compose.yaml` dello stack 01 con un `sed`, e
se non trova nessun servizio con un'immagine `mongolab:` protesta. Se il demone non risponde, dice
che la verifica **non è stata possibile** invece di dire che l'immagine manca — perché le due cose
si rimediano in modo diverso. Se manca davvero, il rimedio è nel messaggio: `make app-image`,
finché c'è rete.

---

## Il `Makefile`: da dove si esegue

Dal Task 12 lo stesso comando ha due modi di girare, e la variabile che sceglie si chiama `DOVE`
([ADR-0092](../../docs/Decision.md#adr-0092)):

```make
DOVE ?= rete
DALL_HOST = uv run --directory app mongolab
ESEGUI = $(if $(filter host,$(DOVE)),$(DALL_HOST),$(COMPOSE_DI_$(TARGET)) run --rm app)
```

```sh
make app-stats TARGET=rs             # dentro la rete: tre membri, un primario
make app-stats TARGET=rs DOVE=host   # sul portatile: un server, topologia «singola»
```

Il predefinito è `rete` perché il comportamento giusto in sala dev'essere quello che si ottiene
senza ricordarsi niente — e perché il modo sbagliato, qui, non fallisce: stampa `topologia singola`
su un replica set sanissimo, che è una risposta plausibile e falsa. Un predefinito che sbaglia
rumorosamente è un fastidio; uno che sbaglia in silenzio è una trappola.

Un valore diverso da `rete` o `host` viene respinto con un messaggio che dice **che cosa sono i
due**, non solo che il terzo non esiste. Stessa cosa per `TARGET`, che dal Task 12 viene controllato
anche qui e non solo dalla CLI: in container il bersaglio sceglie il *file Compose* prima che
l'applicazione parta, e un nome sconosciuto darebbe una riga di comando monca invece di un errore
comprensibile. L'uscita è 2, la stessa con cui Typer respinge un parametro sbagliato.

Due bersagli il `DOVE` non ce l'hanno, e il ramo host è diventato `DALL_HOST` per loro: `app-backup`
e `app-restore` girano solo sull'host — `mongodump` non è nell'immagine ([M-044](Sources.md#m-044))
e questo container non ha il socket del demone Docker — quindi ci vanno da sé, e rifiutano un
`DOVE` scritto a mano diverso da `host` invece di eseguire altrove ([ADR-0120](../../docs/Decision.md#adr-0120)).

### Il flag che non esiste

`ESEGUI` non contiene `--no-build`, e non è una dimenticanza: **`docker compose run` non ha quel
flag.** Compose v5.5.0 espone `--build`, `--pull`, `--quiet-build` e `--quiet-pull`; un `--no-build`
esce con `unknown flag` ([M-035](Sources.md#m-035)). La simmetria che uno si aspetta non c'è, e la
scoperta è arrivata nel modo peggiore possibile: eseguendo `make app-stats` la prima volta e
vedendolo fallire su un flag scritto per prudenza.

La garanzia che quel flag doveva dare — nessuna costruzione a sorpresa la sera del talk — non è
persa, è spostata in due posti che la danno meglio: `pull_policy: never` scritto nel file
([ADR-0039](../../docs/Decision.md#adr-0039)), che vale per chiunque esegua quel servizio e non solo
per chi si ricorda un flag, e il controllo del preflight. La lettura giusta del requisito, del
resto, non era «vietare di costruire»: era che **nessuno debba** costruire.

### Una lista scritta quattro volte

I tre stack, dopo questo task, sono elencati in quattro posti: `BERSAGLI` nel codice di produzione,
i tre file Compose, il guardiano `CHIEDI_TARGET`, e la mappa `COMPOSE_DI_*`. Una lista scritta
quattro volte diverge, e tre prove in `tools/tests/test_coerenza_repo.py` la tengono ferma.

La più importante non controlla i nomi ma le **destinazioni**:

```python
def test_ogni_voce_della_mappa_punta_al_file_dello_stack_giusto() -> None:
```

Perché `COMPOSE_DI_rs = $(COMPOSE_03_BASE)` è una riga sintatticamente ineccepibile che accende un
container e lo collega allo stack sbagliato, senza dire niente a nessuno. Un controllo sui nomi
sarebbe passato.

Una nota su come quella prova legge il `Makefile`: `BERSAGLI` viene letto con `ast`, non importato.
Il pacchetto `tools/` non dipende da `mongolab` e non deve cominciare adesso; leggere il modulo come
sorgente costa cinque righe e non aggiunge una dipendenza fra due progetti che il repository tiene
apposta separati.

---

## Che cosa si è rotto la prima volta che si è eseguito davvero

Il capitolo 12 raccontava tre difetti trovati alla prima esecuzione contro un MongoDB acceso.
Questo ne ha uno solo, ed è di un genere che nessuna prova unitaria avrebbe potuto trovare, perché
il dato che lo scatena non esisteva prima ([M-038](Sources.md#m-038)):

```
topologia  singola
  mongo-standalone:27017standalone            0.7 ms
```

`_riga_server` impaginava l'indirizzo con `f"{indirizzo:<22}"`, e `mongo-standalone:27017` è lungo
**esattamente** ventidue caratteri. La colonna si riempie tutta, il riempimento è di zero spazi, e
due parole distinte finiscono incollate in una parola che non esiste. Dall'host non era mai
successo: `localhost:27021` ne occupa quindici, e ne restavano sette.

La correzione non è alzare il numero, che sposterebbe il problema al primo nome più lungo. La
larghezza si calcola una volta per rapporto:

```python
def _larghezza_indirizzi(server: Sequence[DescrizioneServer]) -> int:
    piu_lungo = max((len(uno.indirizzo) for uno in server), default=0)
    return max(INDIRIZZO, piu_lungo + 1)
```

`INDIRIZZO = 22` resta come **minimo**, non come massimo: la vista dall'host non cambia di una
colonna, e quella dalla rete si allarga quanto serve. Il `+ 1` è lo spazio che garantisce che due
parole restino due parole.

C'è una cosa che vale la pena notare su questo difetto: era latente da tre capitoli, tutte le prove
erano verdi, e a scoprirlo è stato un dato **nuovo** — nomi di servizio invece di `localhost`.
Nessuna prova sbagliata, nessuna svista di revisione: semplicemente, quel valore non era mai
passato di lì.

---

## Le prove

Quattro nuove prove d'integrazione in
[`tests/integration/test_container.py`](../tests/integration/test_container.py), una per stack più
quella della scoperta:

| Prova | Che cosa fissa |
|---|---|
| `test_lo_standalone_si_vede_per_nome_di_servizio` | `mongo-standalone:27017` → `standalone` |
| `test_dentro_la_rete_il_replica_set_ha_un_primario` | tre membri, ruoli `primario, secondario, secondario` |
| `test_un_seme_solo_basta_a_trovare_tutti_e_tre` | la scoperta: un seme, tre membri, `ReplicaSetWithPrimary` |
| `test_lo_sharded_si_vede_attraverso_il_router` | topologia `sharded`, `mongos:27017` → `router` |

Passano per `docker compose run` invece di costruire un client in-process, perché ciò che provano è
proprio **che il container veda la rete**: un client costruito dentro pytest, sull'host, non
proverebbe niente di ciò che qui interessa. E **saltano** invece di costruire, se l'immagine non c'è
in cache: una suite che costruisce un'immagine è una suite che un giorno lo fa senza rete, o mentre
qualcuno sta presentando.

Una trappola in cui la quarta prova è caduta prima di essere corretta: la prima stesura asseriva
`"sharded" in uscita`, che è **banalmente vero** — il titolo del rapporto è `sharded
(docker/03-sharded)`. Sarebbe passata con qualunque topologia. Adesso la prova prende la riga
`topologia` e ne confronta le parole.

### Le guardie vanno mutate

Le cinque prove nuove in `tools/tests/test_coerenza_repo.py` hanno una proprietà scomoda: passano
alla prima esecuzione, perché la configurazione che sorvegliano è già giusta. Una prova che non è
mai stata vista fallire non è una prova, è un'affermazione.

Ognuna è stata quindi **mutata**: si perturba il file sorvegliato, si verifica che la guardia
scatti con un messaggio leggibile, si ripristina l'albero e si riverifica il verde. La prima delle
cinque, così facendo, ha trovato un difetto in sé stessa: traducevo in Python il `sed` del
preflight e avevo scritto `[^ ]*`, che in Python attraversa gli a capo mentre `sed` lavora una riga
per volta. L'asserzione falliva con `'mongolab:0.1.0\n\n' == 'mongolab:0.1.0'`. La versione giusta è
`[^ \n]*`, ed è ciò che `sed` fa davvero.

### Lo stato delle suite

```
make app-test              462 passed
make app-check             mypy --strict: nessun problema su 58 sorgenti
make app-test-integration   47 passed in 41.19s
make tools-test            166 passed
make stack-check           Stack conformi: 3.
```

---

## Che cosa questo capitolo lascia aperto

- **Il caso senza primario non è misurato.** La specifica distingue `updateRSWithoutPrimary` da
  `updateRSFromPrimary` — il primo aggiunge e non toglie, il secondo può togliere — e
  [M-036](Sources.md#m-036) ha visto solo un set con il primario disponibile. Il Task 13, che mette
  in scena il failover, è il posto in cui l'altro ramo si vede.
- **Il bind mount serve allo sviluppo, non alla sala.** La sera del talk il sorgente dell'immagine e
  quello dell'host coincidono; se non coincidessero, vincerebbe l'host. È desiderabile mentre si
  lavora e sarebbe una sorpresa in sala. Chi registra i filmati di riserva ricostruisca prima.
- **`make app-image` costruisce sempre attraverso lo stack 01,** perché il servizio è identico nei
  tre. Se un giorno divergessero, quella riga diventerebbe falsa in silenzio — ed è esattamente ciò
  che la prova sull'immagine unica esiste per impedire.
- **Il controllo legge il Dockerfile con una regex, non con un parser.** Basta per i `FROM` che
  questo repository scrive, e non pretende di capire ogni Dockerfile del mondo.
- **Le prove d'integrazione dichiarano il punto di vista invece di leggerlo.** È una precauzione
  contro l'ambiente e non contro il codice: una sessione che avesse esportato
  `MONGOLAB_PUNTO_DI_VISTA=rete` — cosa che capita provando i comandi di questo task — le farebbe
  fallire venti secondi per volta parlando d'altro.

---

**Fonti e decisioni citate:** [ADR-0009](../../docs/Decision.md#adr-0009),
[ADR-0012](../../docs/Decision.md#adr-0012), [ADR-0014](../../docs/Decision.md#adr-0014),
[ADR-0039](../../docs/Decision.md#adr-0039), [ADR-0054](../../docs/Decision.md#adr-0054),
[ADR-0090](../../docs/Decision.md#adr-0090), [ADR-0091](../../docs/Decision.md#adr-0091),
[ADR-0092](../../docs/Decision.md#adr-0092), [ADR-0093](../../docs/Decision.md#adr-0093); nel
registro di questa applicazione [A-016](Sources.md#a-016), [M-011](Sources.md#m-011),
[M-019](Sources.md#m-019), [M-035](Sources.md#m-035), [M-036](Sources.md#m-036),
[M-037](Sources.md#m-037) e [M-038](Sources.md#m-038).
