# L'architettura dell'applicazione del lab

Dentro questo repository, accanto ai tre stack Docker, c'è un'applicazione Python: `mongolab`. È
lei che genera il carico, che guida le scene del talk, e che mostra dal vivo che cosa **vede un
client** mentre il cluster sotto di lui cambia forma.

Questa pagina è per chi non aprirà i sorgenti. Racconta che forma ha, perché quella forma, e —
soprattutto — **che cosa si è guadagnato** ad averla scelta, con il numero che lo dimostra. Chi
invece i sorgenti li apre ha una sede migliore: i diciassette capitoli di
[`app/docs/`](../../app/docs/README.md), scritti mentre il codice nasceva, con i nomi delle classi,
le firme e le prove. La divisione fra le due sedi è una decisione registrata
([ADR-0113](../Decision.md#adr-0113)) e vale la pena dirla subito: **qui non c'è nessuna riga di
codice dell'applicazione.** Dove servirebbe, c'è un collegamento al capitolo che la possiede.

---

<a id="1-il-problema-che-la-forma-risolve"></a>
## 1. Il problema che la forma risolve

L'applicazione ha un vincolo che si contraddice da solo.

Da un lato, il suo valore didattico sta tutto nel **contatto con MongoDB vero**. Un facsimile del
driver non dimostrerebbe niente: la cosa da mostrare è precisamente come si comporta pymongo
davanti a un primario che sparisce ([ADR-0020](../Decision.md#adr-0020)).

Dall'altro, se ogni pezzo di codice tocca il driver, allora ogni prova ha bisogno di un cluster
acceso. E una suite che pretende undici container per dire se un percentile è calcolato bene **non
verrà eseguita**. Non per pigrizia: perché costa novanta secondi ogni volta, e a quel prezzo si
smette di eseguirla dopo ogni modifica, che è l'unico momento in cui servirebbe.

La forma dell'applicazione è la risposta a questa tensione. Non è un ornamento architetturale, e
non è stata scelta perché un libro la raccomanda: è ciò che permette alle due esigenze di
coesistere invece di sceglierne una.

---

<a id="2-quattro-strati-e-una-regola"></a>
## 2. Quattro strati e una regola sola

```
   presentation      come si vede            Rich, Typer, le tre rese
        │
        ▼
   application       che cosa fa             i casi d'uso: carico, scene, topologia
        │
        ▼
     domain          che cos'è               modelli, eventi, e le PORTE
        ▲
        │
   infrastructure    con che cosa            pymongo, mongodump, i processi esterni
```

Tutte le frecce puntano verso `domain`. Quella che conta è **l'ultima**: `infrastructure` — dove
vive pymongo — dipende da `domain`, e non il contrario.

Detto senza il nome del principio: è il **dominio** a dichiarare di che cosa ha bisogno, sotto forma
di interfacce che chiama *porte*; e sono gli adattatori, al bordo, a farsi in modo da soddisfarle.
Il nucleo dell'applicazione non sa che MongoDB esiste. Lo sa un adattatore, che sta fuori, e che si
può staccare.

Le proporzioni, in righe di codice, dicono dove sta il peso:

| strato | righe | che cosa contiene |
|---|---|---|
| `domain` | 693 | modelli, eventi, sette porte. **Nessuna dipendenza esterna** |
| `application` | 2 219 | i tre casi d'uso: il carico, le scene, la topologia |
| `infrastructure` | 2 795 | pymongo, `mongodump`/`mongorestore`, l'orologio, la regia dei guasti |
| `presentation` | 1 371 | tre modi di rendere lo stesso flusso di eventi |
| `cli.py` | 1 358 | la radice di composizione: l'unico file che conosce i nomi concreti |

Il dominio è la parte **più piccola**, ed è quella da cui dipendono tutte le altre. Non è un caso:
contiene le decisioni, non il lavoro.

La forma è spiegata per esteso, con il codice, in
[`app/docs/01-architettura-esagonale.md`](../../app/docs/01-architettura-esagonale.md).

---

<a id="3-che-cosa-si-guadagna-634-prove-in-quattro-secondi"></a>
## 3. Che cosa si guadagna: 634 prove in quattro secondi

Qui sta il motivo per cui questa pagina esiste. Le architetture pulite si difendono di solito
citando un principio; questa si difende con un cronometro.

```
$ make app-test
634 passed in 3.96s
```

Seicentotrentaquattro prove, meno di quattro secondi, **senza accendere niente**. Non è un modo di
dire: la stessa suite è stata rieseguita con il client Docker puntato su un socket che non esiste,

```
$ DOCKER_HOST=unix:///percorso/che/non/esiste.sock make app-test
634 passed in 3.86s
```

e il risultato è identico, sia nel conteggio sia nel tempo
([M-058](../../app/docs/Sources.md#m-058)). Se una sola prova avesse avuto bisogno di un demone
Docker, sarebbe fallita in quel momento. Nessuna ce l'ha.

Il numero da tenere non è il 3,9. È il **rapporto** con l'altra suite: quella d'integrazione, che
gli stack li accende sul serio, ci mette circa **110 secondi** — quasi trenta volte tanto. È quella
differenza a rendere praticabile eseguire le prove dopo ogni modifica invece che prima del commit.

E la differenza è esattamente ciò che l'inversione delle dipendenze compra. Gli adattatori veri
stanno tutti dietro una porta; al loro posto, nella suite unitaria, sta un doppio che vive in
memoria. Nessun container da avviare, nessun `mongod` da aspettare, nessun cluster da rimettere in
piedi quando una prova lo rompe apposta.

> **Il ritorno di un'architettura si misura in secondi, non in aggettivi.** «Testabile» è
> un'affermazione che non si può verificare; «634 prove in 3,9 secondi contro 110» è un fatto che
> chiunque può rifare con due comandi.

Vale la pena guardare anche l'altro lato del conto: le prove unitarie sono **9 836 righe** contro
le 8 436 dei sorgenti. C'è più codice di prova che codice. È il prezzo, ed è stato pagato
volentieri, perché è quello che ha permesso di rompere l'applicazione deliberatamente decine di
volte senza paura.

---

<a id="4-le-sette-porte"></a>
## 4. Le sette porte

Una porta è una domanda che il dominio pone al mondo esterno, scritta come interfaccia. Sono sette,
e ciascuna esiste perché **qualcosa andava provato senza il mondo vero**:

| porta | la domanda che pone | l'adattatore vero | il doppio |
|---|---|---|---|
| `DocumentStore` | «scrivi questo documento, leggi questi» | pymongo | un archivio in memoria, più tre varianti che rompono, rallentano o rifiutano |
| `ClusterInspector` | «com'è fatto il cluster adesso?» | comandi di amministrazione | un ispettore che risponde quello che serve alla prova |
| `QueryPlanner` | «come eseguiresti questa query?» | `explain` | un pianificatore che restituisce un piano preparato |
| `BackupTool` | «fai il dump, fai il restore» | `mongodump`/`mongorestore` come processi | un doppio che finge l'avanzamento |
| `EventSink` | «è successo questo» | le tre rese | un raccoglitore che conserva tutto per l'asserzione |
| `Clock` | «che ora è, aspetta un po'» | l'orologio di sistema | un orologio che si sposta a comando |
| `Regia` | «fai cadere quel nodo» | il client Docker | una regia finta, e una che rifiuta |

L'ultima riga è la più istruttiva, e non è ovvia: **anche il guasto è una porta.** Chi fa cadere il
nodo non sta dove lo scenario guarda, e questa separazione è ciò che permette di provare la scena
del failover senza uccidere niente ([ADR-0095](../Decision.md#adr-0095)).

Le porte, con le firme e i doppi che le soddisfano, stanno in
[`app/docs/02-porte-e-doppi.md`](../../app/docs/02-porte-e-doppi.md).

---

<a id="5-il-modello-a-eventi"></a>
## 5. Il modello a eventi: nove fatti, tre modi di guardarli

L'applicazione non stampa. **Emette fatti.**

Ogni cosa che succede — una scrittura riuscita, una fallita, un tentativo ripetuto, un campione di
latenza, un cambio di topologia, un nodo che cambia stato, un backup che avanza, un'attesa
abbandonata, una fase che comincia — è un oggetto immutabile, con i suoi campi, che viene consegnato
a un `EventSink`. Sono **nove**.

Da questa scelta discendono tre cose che altrimenti sarebbero costate lavoro:

1. **Le prove asseriscono sui fatti, non sull'output.** Un doppio raccoglie gli eventi e la prova
   verifica che ci sia stato un `RetryAttempted` seguito da un `WriteSucceeded` — cosa impossibile
   da fare in modo pulito su una stringa stampata.
2. **La stessa esecuzione si può rendere in tre modi diversi** senza toccare il codice che la
   esegue: una resa muta per le misure, una a righe per i log e i filmati, una cruscotto per il
   palco. Tre rese, un solo flusso di eventi — e **un solo thread che disegna**, perché il driver
   ne usa altri e disegnare da più thread rompe il terminale
   ([`app/docs/11`](../../app/docs/11-tre-rese-e-un-solo-thread-che-disegna.md)).
3. **Gli eventi del driver entrano dalla stessa porta.** Pymongo ha un suo sistema di notifiche
   sulla topologia, e il ponte che lo collega al modello a eventi dell'applicazione è il punto in
   cui il talk può mostrare **la scoperta che avviene**, invece di raccontarla
   ([`app/docs/08`](../../app/docs/08-il-ponte-sdam-e-i-thread-del-driver.md)).

C'è anche un evento che è stato **tolto**: `ChunkMigrated`. Il laboratorio non lo produce mai, e un
evento che nessuno emette è una promessa al lettore del codice che il codice non mantiene
([ADR-0103](../Decision.md#adr-0103)). Vale la pena registrarlo qui perché è il tipo di decisione
che di solito non si prende: togliere è più difficile che lasciare.

Il dettaglio sta in
[`app/docs/03-eventi-immutabili.md`](../../app/docs/03-eventi-immutabili.md) e
[`app/docs/04-eventi-del-driver-e-concorrenza.md`](../../app/docs/04-eventi-del-driver-e-concorrenza.md).

---

<a id="6-la-radice-di-composizione"></a>
## 6. La radice di composizione: un file solo sa i nomi veri

Se il dominio dichiara porte e gli adattatori le soddisfano, resta una domanda: **chi decide quale
adattatore usare?**

La risposta è un punto solo, e in questa applicazione è la riga di comando. `cli.py` è l'unico file
che nomina le classi concrete: legge le opzioni, costruisce l'adattatore giusto, lo consegna al caso
d'uso e si toglie di mezzo. Tutto il resto del programma vede solo porte.

Questo ha una conseguenza che si vede a occhio nudo, ed è il modo più rapido di verificare che
l'impianto tenga: **se si cerca `pymongo` nei sorgenti, lo si trova solo in `infrastructure` e nella
riga di comando.** Nel dominio e nei casi d'uso non compare. Non è una convenzione da rispettare a
memoria: è verificato da `mypy --strict` su tutti i file e da una prova che guarda gli import.

Il prezzo è dichiarato, perché esiste: quel file è il più grande dell'applicazione (1 358 righe).
La complessità del cablaggio non sparisce scegliendo questa forma — **si concentra**, e concentrata
si può leggere tutta insieme. Il capitolo che la descrive è
[`app/docs/12`](../../app/docs/12-la-radice-di-composizione-e-la-prima-esecuzione-vera.md).

---

<a id="7-dove-questa-forma-e-costata"></a>
## 7. Dove questa forma è costata

Una pagina che elenca solo i vantaggi non è una pagina tecnica. Tre punti in cui la forma ha
presentato il conto:

- **Il ponte con gli eventi del driver.** Pymongo notifica i cambi di topologia dai **suoi** thread,
  che non sono quelli dell'applicazione. Portare quelle notifiche dentro un modello a eventi
  ordinato, senza rompere il terminale e senza perdere l'ordine, è il pezzo più delicato del
  progetto, e ha richiesto un capitolo tutto suo
  ([`app/docs/08`](../../app/docs/08-il-ponte-sdam-e-i-thread-del-driver.md)). Le porte non hanno
  reso il problema più facile: lo hanno reso **isolabile**.
- **I processi esterni non hanno una porta comoda.** `mongodump` e `mongorestore` sono programmi, non
  librerie: l'avanzamento arriva su un flusso di testo che va consumato mentre scorre. La porta
  `BackupTool` esiste, ma dietro c'è un adattatore che fa un lavoro che nessuna interfaccia rende
  elegante ([`app/docs/10`](../../app/docs/10-processi-esterni-e-il-verdetto-che-manca.md)).
- **Un doppio può mentire.** Un archivio in memoria che si comporta meglio del vero rende verdi
  prove che sul cluster fallirebbero. La difesa adottata — un contratto unico eseguito **sia** sul
  doppio **sia** sull'adattatore vero — è raccontata nella
  [pagina sulle prove](tdd-e-doppi.md) e in
  [`app/docs/09`](../../app/docs/09-adattatori-veri-e-contratto-condiviso.md). È la contromisura
  senza la quale tutto il guadagno della sezione 3 sarebbe illusorio.

---

## Cosa questa pagina non dice

- **Non contiene codice dell'applicazione.** È la regola che
  [ADR-0113](../Decision.md#adr-0113) si è data: firme, classi e file stanno in
  [`app/docs/`](../../app/docs/README.md), che è la loro sede normativa e cambia quando cambia il
  codice.
- **Non è una guida all'architettura esagonale in generale.** Non discute varianti, non confronta
  con altre forme, non cita la letteratura. Descrive **una** applicazione e mostra che cosa le è
  costata e che cosa le ha reso.
- **Non dice se questa forma convenga a un'applicazione qualunque.** Qui conviene per una ragione
  precisa e insolita: il soggetto del programma **è** il comportamento del driver davanti a un
  cluster che si rompe, quindi il confine fra dominio e infrastruttura è anche il confine fra ciò
  che si può provare a freddo e ciò che richiede undici container. In un gestionale quel confine
  cade altrove.
- **Non dice quanto costa mantenerla.** Il progetto ha diciotto giorni di vita e un solo autore. La
  domanda vera su un'architettura — come invecchia con più mani e due anni — questo repository non
  può rispondervi, e non finge di poterlo fare.
- **Non elenca i comandi dell'applicazione.** Per quelli c'è `mongolab --help` e i capitoli 12-17
  di [`app/docs/`](../../app/docs/README.md); il documento unico del talk — scaletta, comandi,
  tempi, piani di ripiego — è previsto come `05-talk/runbook-demo.md` e a oggi non esiste
  ([ADR-0015](../Decision.md#adr-0015)).

---

**Decisioni correlate:** [ADR-0113](../Decision.md#adr-0113) (le pagine divulgative rimandano ad
`app/docs/` invece di riassumerlo), [ADR-0020](../Decision.md#adr-0020) (l'applicazione tocca
MongoDB vero, non un facsimile), [ADR-0095](../Decision.md#adr-0095) (anche il guasto è una porta),
[ADR-0103](../Decision.md#adr-0103) (l'evento che il laboratorio non produce esce dal dominio),
[ADR-0078](../Decision.md#adr-0078) (perché `feature/04` è cominciata quando è cominciata).

**Fonti:** [M-058](../../app/docs/Sources.md#m-058)
