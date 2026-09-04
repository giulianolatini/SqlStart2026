# Le prove dell'applicazione: doppi, contratti, e un failover che non si aspetta

L'applicazione `mongolab` esiste per mostrare che cosa vede un client mentre il cluster sotto di lui
si rompe. È il soggetto più difficile da provare che ci sia: richiede un guasto, e un guasto vero
costa undici container, decine di secondi e un pezzo di fortuna.

Questa pagina racconta come si prova lo stesso una cosa così, e quanto costa la risposta. È scritta
per chi non aprirà i sorgenti; chi li apre trova in
[`app/docs/05-tipi-prove-e-guardie.md`](../../app/docs/05-tipi-prove-e-guardie.md),
[`02-porte-e-doppi.md`](../../app/docs/02-porte-e-doppi.md) e
[`09-adattatori-veri-e-contratto-condiviso.md`](../../app/docs/09-adattatori-veri-e-contratto-condiviso.md)
gli stessi fatti con i nomi, le firme e i file. La divisione fra le due sedi è una decisione
registrata ([ADR-0113](../Decision.md#adr-0113)), e la sua regola vale anche qui: **in questa pagina
non c'è nessuna riga di codice dell'applicazione**. La forma che l'applicazione ha — e che rende
possibile tutto ciò che segue — è raccontata nella [pagina sull'architettura](architettura-app.md).

---

<a id="1-due-suite-e-la-riga-che-le-tiene-separate"></a>
## 1. Due suite, e la riga che le tiene separate

Le prove di `mongolab` sono due insiemi che rispondono a due domande diverse:

| Suite | La domanda | Quante | Quanto dura | Serve Docker |
|---|---|---|---|---|
| unitaria | il comportamento è quello previsto? | 634 | **3,9 s** | no |
| di integrazione | funziona contro MongoDB vero? | 58 | ~110 s | **sì**, gli stack del repository |

La separazione non è una convenzione di cartelle: è una riga di configurazione che dichiara alla
suite veloce di raccogliere **solo** le prove unitarie. Senza quella riga, il giorno in cui è nata la
prima prova di integrazione la suite veloce avrebbe cominciato a pretendere Docker — senza che
nessuno l'avesse deciso, e senza che nessuno se ne accorgesse subito.

È così che le suite veloci muoiono: **per accumulo, non per scelta.** Nessuno decide mai che la
suite debba durare due minuti; ci si arriva una prova alla volta, e quando ci si arriva si smette di
eseguirla dopo ogni modifica, che è l'unico momento in cui serviva. L'integrazione qui si chiede per
nome, con un secondo comando.

### La misura, non la promessa

«La suite unitaria non ha bisogno di Docker» è un'affermazione facile da fare e difficile da
mantenere: basta un `import` di troppo, un adattatore costruito per comodità dentro una prova, e la
dipendenza rientra senza rumore. Il modo per saperlo è provarlo — eseguire la suite in un ambiente
in cui Docker **non esiste**, indicando al client un socket che non c'è.

L'esito: **634 prove passate in 3,86 secondi**, identiche alle 634 in 3,96 secondi dell'esecuzione
normale ([M-058](../../app/docs/Sources.md#m-058)). Non «non dovrebbe servire»: non serve, e c'è la
corsa che lo mostra.

Il rapporto fra i due numeri — quattro secondi contro quasi due minuti — è tutto il guadagno
dell'impianto descritto in questa pagina. Quattro secondi si pagano dopo ogni modifica; due minuti si
pagano quando ci si ricorda.

---

<a id="2-come-si-prova-un-failover-senza-aspettarlo"></a>
## 2. Come si prova un failover senza aspettarlo

Il progetto conteneva da mesi una regola scritta e mai realizzata: *dopo trenta secondi senza
primario, smetti di ritentare*. Era rimasta una frase per una ragione puramente pratica — **nessuno
mette in una suite veloce una prova che aspetta mezzo minuto**, e una regola che nessuna prova
esegue non è una regola: è un commento.

La via d'uscita non è un trucco di libreria. È una scelta di forma: **il tempo entra
nell'applicazione da una porta**, come il database. Il codice che misura un'interruzione non chiede
mai l'ora al sistema e non dorme mai da solo; domanda a un oggetto che gli è stato consegnato. In
produzione quell'oggetto è l'orologio vero. Nelle prove è un doppio che avanza **solo quando glielo
si dice**.

Il risultato è che la regola dei trenta secondi si verifica con la pazienza fissata a un secondo,
l'intervallo a un quarto, e il tempo che salta da un valore all'altro senza che passi niente:

```
sguardo 1 · t=0 ms      SANO      — il ricordo si stabilisce
sguardo 2 · t=250 ms    CADUTO    — l'interruzione si apre, inizio=250
sguardo 3 · t=500 ms    CADUTO    — durata attesa 250 ms
sguardo 4 · t=750 ms    CADUTO    — durata attesa 500 ms
sguardo 5 · t=1000 ms   CADUTO    — durata attesa 750 ms
sguardo 6 · t=1250 ms   CADUTO    — 1000 ms ≥ pazienza → resa
```

Sei letture, e la prova dura centesimi di secondo.

Ci sono due cose da guardare in questa tabella, e la seconda vale più della prima.

La prima è che **il valore atteso è esatto**, non una tolleranza. Nessun «circa 250 ms», nessun
margine per la lentezza della macchina, nessuna prova che diventa rossa il martedì. Il tempo è un
ingresso controllato, quindi la durata misurata è aritmetica.

La seconda è che si può fare la domanda al contrario. Con la pazienza fissata a **1001** ms gli
sguardi diventano **sette**: un millisecondo in più è un giro in più. Questa è la prova che la
regola smette quando deve **e non prima** — cioè che si sta verificando la soglia, e non
semplicemente che prima o poi il ciclo finisce. Con un'attesa vera quella distinzione non sarebbe
misurabile: la si dichiarerebbe e basta.

---

<a id="3-fake-contro-mock"></a>
## 3. Fake contro mock: la differenza si vede quando il codice cambia

I sostituti usati nelle prove di questo progetto non sono mock, e la distinzione è operativa, non
terminologica.

**Un mock registra le chiamate. Un doppio implementa il comportamento.** L'archivio finto conserva
davvero i documenti: quando gli si chiede di inserirne cinquanta li mette da parte, quando gli si
chiede di contarli li conta, quando gli si chiede una pagina la impagina. Non è configurato per
rispondere: risponde.

La differenza si vede in un momento preciso, ed è il momento in cui una suite serve — **quando il
codice sotto prova cambia**. Un mock configurato per rispondere a una chiamata continua a rispondere
anche quando il caso d'uso ha smesso di contare bene: verifica che la chiamata sia avvenuta, non che
il risultato sia giusto. Un doppio che conserva davvero i documenti fallisce, perché il conteggio
non torna.

Ce ne sono altre due, meno ovvie.

**I doppi sono stati scritti prima dei casi d'uso che devono verificare.** Scriverli dopo
significherebbe modellarli sull'implementazione esistente, che è il modo più efficace di ottenere
prove che confermano il codice invece di controllarlo.

**Il doppio deve parlare la stessa lingua dell'originale**, perché le stesse prove gireranno contro
entrambi (§5). È la ragione per cui, nel cuore dell'applicazione, un documento è una struttura del
linguaggio e non un tipo di pymongo: così le due implementazioni sono confrontabili, e una prova
scritta contro il doppio significa qualcosa anche contro il cluster.

### Dove non sa, solleva

Il doppio dell'archivio parla un dialetto piccolo e **dichiarato**: uguaglianza sui campi di primo
livello e tre stadi di aggregazione. Tutto il resto — un confronto d'ordine, un percorso puntato,
uno stadio che non conosce — solleva un errore che **nomina ciò che non sa fare** e dice che cosa
farne: insegnarglielo insieme alla prova che lo richiede.

L'alternativa non è sollevare di meno, è tacere. Un doppio che ignorasse un filtro che non capisce
restituirebbe tutti i documenti, e la prova che lo usa diventerebbe verde senza che nessuno abbia
scritto una riga di codice difettoso. **Un doppio che tace su ciò che non sa è più pericoloso di uno
che non c'è**, perché uno che non c'è lo si nota.

Anche questo rifiuto è verificato invece che sperato: rendendo permissivo il confronto del doppio —
la rottura che un doppio troppo accomodante produce davvero — diventano rosse sette prove, e due di
quelle sette falliscono proprio con «non ha sollevato»
([M-006](../../app/docs/Sources.md#m-006)).

---

<a id="4-tre-mestieri-di-un-doppio"></a>
## 4. Tre mestieri di un doppio

In `app/tests/doppi/` ci sono **dodici** classi per 833 righe, e non fanno tutte lo stesso lavoro.
Distinguerle è utile perché la terza famiglia è quella che di solito manca:

- **Quelli che sostituiscono.** L'archivio in memoria, l'ispettore della topologia, il backup finto,
  il pianificatore, il raccoglitore di eventi. Stanno al posto di un'infrastruttura e si comportano
  come lei.
- **Quelli che scorrono.** I due orologi: uno che avanza solo su comando — quello del §2 — e uno che
  scorre da sé a passo fisso, per il codice che misura durate senza governarle.
- **Quelli che rompono.** Un archivio che rifiuta le scritture, uno che rifiuta le letture, uno che è
  lento (e fa avanzare l'orologio *dentro* la chiamata, così che il costo del tempo si veda), una
  regia che nega i comandi.

L'ultima famiglia è il punto in cui l'impianto ripaga davvero. **Il guasto non è una condizione
eccezionale da simulare con un'eccezione lanciata a mano dentro una prova: è un'implementazione della
stessa porta** ([ADR-0095](../Decision.md#adr-0095)). Un archivio che rompe è un archivio a tutti gli
effetti, si costruisce come l'altro, e il codice sotto prova non sa di essere in una prova. Così la
cronaca degli errori, il conteggio dei tentativi e le latenze del caso peggiore si verificano a
freddo, senza spegnere niente.

Ogni doppio porta poi due cose sue. Una prova che ne verifica **la promessa** — che l'archivio
ritrovi ciò che ha accettato, che l'orologio distingua «ha dormito» da «il tempo è passato» — perché
un attrezzo di misura si tara prima di misurarci. E una riga, in una prova quasi vuota, che dichiara
il doppio come la porta che implementa: è lì che la conformità viene verificata davvero, dal
controllo dei tipi. Non basta che il doppio *sembri* conforme a chi esegue: a runtime, un oggetto con
la firma sbagliata **supera** il controllo di appartenenza al protocollo, ed è stato misurato
([M-004](../../app/docs/Sources.md#m-004)).

---

<a id="5-il-contratto-condiviso"></a>
## 5. Il doppio che mente, e il contratto che lo smaschera

Un doppio ben scritto ha un difetto che non ha niente a che vedere con la sua qualità: **è
convincente**. Ogni volta che una prova passa contro l'archivio finto, chi la legge conclude qualcosa
sull'applicazione davanti a MongoDB — e quella conclusione vale solo quanto la somiglianza fra i due.
Per settimane quella somiglianza non è stata scritta da nessuna parte, e non c'era modo di accorgersi
che stava calando.

La risposta è un file che **non è una prova**: contiene dodici verifiche, ciascuna delle quali prende
un archivio qualunque e fallisce se quell'archivio si comporta male. Poi due file, in due posti
diversi, le eseguono: quello della suite unitaria le passa al doppio, quello della suite di
integrazione all'adattatore vero, contro lo stack acceso.

Il valore sta tutto nel fatto che il **corpo** della verifica è scritto una volta sola. Se stesse
scritto due volte — anche identico, anche copiato — divergerebbe: qualcuno correggerebbe la copia del
doppio per farla passare, e la copia dell'originale resterebbe indietro senza che nessuno se ne
accorga. **Un contratto copiato non è un contratto.**

L'elenco delle dodici verifiche è poi scritto a mano invece di essere raccolto automaticamente, e non
è pigrizia al contrario: una verifica scritta male — nome fuori schema, dimenticata dopo un rinomino
— sparirebbe dall'elenco senza che niente diventi rosso. La copertura calerebbe in silenzio, che è
precisamente ciò contro cui quel file esiste.

Alla prima esecuzione il contratto ha trovato **due** bugiardi, e il secondo è quello che conta.

**Il primo era il doppio.** Su una pipeline di conteggio applicata a zero documenti rispondeva
«zero»; MongoDB non risponde niente, perché uno stadio che non riceve documenti non ne emette
([M-017](../../app/docs/Sources.md#m-017)). Il difetto era peggio di un errore, perché nessuna delle
due parti solleva: il codice che consuma il risultato legge un elemento che nel doppio c'è e contro
il cluster non c'è. Sarebbe comparso al **primo fotogramma della demo**, con la collezione ancora
vuota.

**Il secondo era l'originale**, cioè MongoDB, e nessuno lo avrebbe sospettato. Chiedere zero documenti
a una pagina, nel driver, non significa «nessun documento»: significa **nessun limite**
([A-011](../../app/docs/Sources.md#a-011)), e la traduzione ovvia avrebbe restituito la collezione
intera a chi ne aveva chiesti zero ([M-022](../../app/docs/Sources.md#m-022)). È un valore che nessuno
digita a mano: ci si arriva per sottrazione — quante righe restano nella finestra, quanti documenti
mancano alla fine. In scena si sarebbe visto come cinquantamila righe che scorrono dove ne erano state
chieste zero.

Il contratto ha però un confine, e dichiararlo fa parte del metodo: **vale solo dove le due
implementazioni devono coincidere.** Dove non devono, forzarle sarebbe peggio — o si mutila
l'originale, o si gonfia il doppio di capacità che nessuna prova richiede. Le differenze legittime
stanno perciò in cinque prove che vivono **solo** nel file di integrazione, e ciascuna dichiara la
propria: operatori che il doppio rifiuta, chiavi duplicate che l'originale respinge, e l'ordine dei
risultati, che il doppio garantisce e MongoDB senza ordinamento esplicito **non promette**.

---

<a id="6-ogni-guardia-e-stata-vista-fallire"></a>
## 6. Ogni guardia è stata vista fallire

C'è una disciplina che questo repository applica a tutti i controlli automatici, ed è la stessa cosa
del TDD guardata da un altro lato: **un controllo scritto quando non può fallire va rotto apposta,
subito.**

La ragione è che molte guardie nascono davanti al vuoto. La prova che vieta al cuore
dell'applicazione di importare il driver è stata scritta quando quel codice non importava ancora
niente: il suo primo verde non distingue «tutto a posto» da «non c'era niente da guardare», e la
differenza si scopre mesi dopo, quando serviva. Costa trenta secondi introdurre la violazione, vedere
il messaggio e toglierla — e quei trenta secondi verificano due cose: che il controllo scatti, e che
quando scatta dica **dove**.

La stessa guardia porta poi una difesa contro sé stessa: asserisce di aver esaminato almeno tanti
moduli quanti sono gli strati che sorveglia. Senza, il giorno in cui una cartella venisse rinominata
continuerebbe a passare **guardando il vuoto**.

Da questa pratica è uscito un risultato che non era previsto: **rompere una guardia apposta ha tre
esiti, non due.** Il controllo scatta, e va bene. Il controllo tace, e va corretto. Oppure **la
violazione non è costruibile**, perché il linguaggio la vieta prima — ed è capitato. Il terzo esito è
il più facile da leggere male, perché somiglia al primo: entrambi finiscono con la suite verde. La
differenza è che nel terzo caso l'asserzione è decorazione, controlla il compilatore, e chi la legge
crede che stia sorvegliando qualcosa che nessuno può violare. Va tolta — nominando l'esperimento che
l'ha dimostrata superflua, altrimenti il prossimo lettore la riaggiunge in buona fede.

Il rovescio della stessa medaglia è che **un limite noto si scrive come prova verde invece che come
commento**: un oggetto costruito male che *supera* il controllo, e l'asserzione che dice proprio
questo. Un commento invecchia in silenzio; quella prova diventerebbe rossa il giorno in cui il
linguaggio stringesse la regola.

---

<a id="7-dove-questo-impianto-non-arriva"></a>
## 7. Dove questo impianto non arriva

Tre limiti, misurati e non stimati.

**Il controllo dei tipi è l'unico posto in cui la conformità alle porte è verificata, e non verifica
tutto.** Scrivendo un doppio nella forma sintatticamente giusta ma semanticamente sbagliata — un
generatore dichiarato dove serviva una funzione che *restituisce* un generatore — il tipo annotato
resta identico e il controllo resta verde: a scoprirlo è **una** prova
([M-007](../../app/docs/Sources.md#m-007)). Insieme a [M-004](../../app/docs/Sources.md#m-004) è un
promemoria in due direzioni: niente qui è sorvegliato da un solo strumento, perché nessuno strumento
basta.

**Quattro secondi di suite unitaria non dicono niente sulla rete.** Tutto ciò che riguarda tempi di
scoperta, riconnessioni del driver e comportamento sotto un guasto vero sta nelle 58 prove di
integrazione e negli stack accesi. Il contratto condiviso riduce la distanza fra le due suite; non la
annulla, e non è stato costruito per farlo.

**Una prova di integrazione è intermittente.** Il repository ne ha una che verifica la presenza di un
primario da dentro la rete e che occasionalmente fallisce. È registrata come punto aperto invece che
disattivata: una prova intermittente spenta è un difetto che smette di farsi vedere.

---

## Cosa questa pagina non dice

- **Non contiene codice dell'applicazione né delle sue prove.** È la regola di
  [ADR-0113](../Decision.md#adr-0113): nomi di file, firme e corpi stanno in
  [`app/docs/`](../../app/docs/README.md), che cambia quando cambia il codice.
- **Non è un'introduzione al TDD.** Non definisce il ciclo, non discute scuole, non cita la
  letteratura. Racconta che cosa è costato e che cosa ha reso in **questo** progetto, che ha un
  soggetto insolito: un guasto.
- **Non elenca le prove né le guardie.** Quali violazioni siano state provate, e con quale esito, sta
  nella tabella di
  [`app/docs/05-tipi-prove-e-guardie.md`](../../app/docs/05-tipi-prove-e-guardie.md).
- **Non dice come si comportano le suite su una macchina diversa da questa.** I tempi qui riportati
  sono di un portatile solo, dichiarati con le loro riserve nella fonte, e la suite di integrazione
  richiede gli stack del repository accesi.
- **Non affronta la copertura.** Nessuna misura di copertura è stata presa in questo progetto, e
  nessuna delle affermazioni di questa pagina vi si appoggia.

---

**Decisioni correlate:** [ADR-0113](../Decision.md#adr-0113) (le pagine divulgative rimandano ad
`app/docs/` invece di riassumerlo), [ADR-0020](../Decision.md#adr-0020) (le prove di integrazione
usano gli stack del repository e non una libreria di container),
[ADR-0095](../Decision.md#adr-0095) (anche il guasto è una porta),
[ADR-0078](../Decision.md#adr-0078) (perché `feature/04` è cominciata quando è cominciata).

**Fonti:** [M-004](../../app/docs/Sources.md#m-004), [M-006](../../app/docs/Sources.md#m-006),
[M-007](../../app/docs/Sources.md#m-007), [M-017](../../app/docs/Sources.md#m-017),
[M-022](../../app/docs/Sources.md#m-022), [M-058](../../app/docs/Sources.md#m-058),
[A-011](../../app/docs/Sources.md#a-011)
