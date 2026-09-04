# 7. La topologia, il failover, e i due numeri

> Il principio in una riga: **un'applicazione client può misurare quello che ha visto, non quello che
> è successo — e la differenza fra le due cose va scritta, non arrotondata.**

`TopologyWatcher` sta in `app/src/mongolab/application/topologia.py` ed è il pezzo che giustifica
l'esistenza dell'intera applicazione. Guarda il cluster attraverso `ClusterInspector`, confronta ciò
che vede con ciò che ricordava, racconta la differenza emettendo eventi, e da quel racconto ricava
**i due numeri che `mongosh` non sa dare**: quanto è durata l'interruzione, e quante scritture sono
andate perse.

Questa pagina spiega le scelte che non erano ovvie. Sono più di quante sembri: quasi ogni riga di
questo modulo decide che cosa il talk potrà affermare dal palco.

## Il caso che conta è un passaggio, non uno stato

Un cluster «senza primario» non è una notizia. La notizia è la sequenza:

| fotogramma | topologia | che cosa vede il client |
|---|---|---|
| 1 | `REPLICA_SET_CON_PRIMARIO` | `mongo-1` è il primario |
| 2 | `REPLICA_SET_SENZA_PRIMARIO` | `mongo-1` è irraggiungibile, nessuno comanda |
| 3 | `REPLICA_SET_CON_PRIMARIO` | `mongo-2` è il primario |

Nessuno dei tre, da solo, dice niente di interessante. È il **passaggio** fra loro a essere la scena
del Blocco 2, e per questo `TopologyWatcher` tiene un ricordo — la proprietà `vista` — invece di
limitarsi a riferire l'ultima lettura. È anche la ragione per cui `FakeInspector`, scritto al Task 4,
riceve una *sequenza* di topologie e non una sola: quel doppio è stato disegnato leggendo questo
task, mesi prima che il codice esistesse.

Il terzo fotogramma non è il primo. `mongo-2` non è `mongo-1`, e chiamare «ripristino» entrambe le
cose fa perdere l'unica scena che il pubblico è venuto a vedere. `Interruzione.e_un_failover`
distingue le due: vero solo se il primario di dopo è un **altro**. Un nodo che si riavvia in fretta
produce un'interruzione senza elezione, ed è una storia diversa.

## La prima occhiata non è un cambiamento

Il primo sguardo non emette niente. Un `TopologyChanged` in cima alla cronaca direbbe che il client
ha cambiato idea rispetto a un'idea che non aveva.

Sembra una sottigliezza e non lo è, per una ragione che riguarda chi guarda: **la prima riga di una
cronaca è dove si decide quanto fidarsi di tutte le altre.** Un fatto falso lì costa più di un fatto
falso in mezzo, perché non viene corretto — viene usato come metro.

## Un server che sparisce non è un server irraggiungibile

Quando un indirizzo compare in una descrizione e non nella successiva, l'evento
`ServerStateChanged` lo porta a `SCONOSCIUTO`, non a `IRRAGGIUNGIBILE`.

La distinzione non è un cavillo:

- **`IRRAGGIUNGIBILE` è un'osservazione.** Il client ha provato a parlare con quel server e non ci è
  riuscito. C'è un tentativo dietro, e spesso c'è anche un errore da mostrare.
- **`SCONOSCIUTO` è l'assenza di un'osservazione.** Il server non compare più nella descrizione, e
  di lui non si sa più niente.

Scrivere la prima al posto della seconda mette in cronaca un tentativo che nessuno ha fatto. È lo
stesso principio per cui i doppi sollevano invece di far finta ([02](02-porte-e-doppi.md)): il
codice non inventa un esito che non ha.

Simmetricamente, un indirizzo che compare per la prima volta arriva **da** `SCONOSCIUTO`.

## L'ordine degli eventi, e perché è per indirizzo

Dentro un giro escono prima i `ServerStateChanged`, poi il `TopologyChanged`: la forma dell'insieme
è la conseguenza, e si legge dopo la causa.

I `ServerStateChanged` sono ordinati **per indirizzo**, non nell'ordine in cui i server compaiono
nelle descrizioni. Quell'ordine arriva da due letture diverse del driver e niente lo garantisce: una
cronaca che vi si appoggiasse sarebbe riproducibile *quasi sempre*, che nelle prove è il modo
educato di dire «rossa una volta ogni tanto, su una macchina carica, senza motivo apparente».

C'è un seguito istruttivo, ed è raccontato più sotto: la prima prova scritta per quest'ordine **non
lo verificava affatto**.

## I due numeri, e perché stanno qui e non nella TUI

`bilancio(confermate=…, ritrovate=…)` restituisce un `Bilancio` congelato, con dentro
l'interruzione e i conteggi. Calcolarli nel livello che disegna avrebbe voluto dire due cose,
entrambe brutte: che non esistono finché qualcuno non li guarda, e che non sono provabili senza un
terminale.

### Le perdite sono due, non una con il segno

| campo | che cosa dice |
|---|---|
| `scritture_perse` | confermate al client e **non** ritrovate dopo |
| `scritture_non_confermate` | ritrovate dopo e **mai** confermate al client |

Il secondo fenomeno è l'altro esito del failover, e non ha un nome sulle slide benché ne meriterebbe
uno: il server applica la scrittura, la conferma parte, il primario cade prima che arrivi. Il client
non sa di aver scritto, e ha scritto.

Con un solo campo firmato, questo apparirebbe come «meno diciassette scritture perse»: aritmetica
sensata e cronaca sbagliata. Due campi, entrambi non negativi.

### La durata è `None` finché l'interruzione è aperta

`Interruzione.durata_ms` non restituisce zero. Uno zero direbbe «è durata niente» dove la verità è
«non è ancora finita», ed è la peggiore risposta mancante perché **ha la faccia di una misura**:
passa i controlli, entra nelle medie, e finisce su una slide. È la stessa regola per cui il
riepilogo del carico porta `latenze=None` quando nessuna scrittura è riuscita
([06](06-carico-tentativi-e-latenze.md)).

### Un'interruzione che non si è vista cominciare non si misura

Se il primo sguardo trova il cluster **già** senza primario, nessuna interruzione viene aperta.

La tentazione è aprirla lì: si otterrebbe comunque un numero. Ma quel numero sarebbe un limite
inferiore, e tanto più corto quanto più tardi si è cominciato a guardare — cioè **un numero che
sbaglia verso il rassicurante**. Il talk esiste per dire che il failover costa; misurarlo con uno
strumento che tende a sottostimarlo sarebbe un modo raffinato di darsi ragione.

Meglio nessuna misura di una misura ottimista. L'attesa del primario, però, viene contata lo stesso:
serve alla pazienza, che deve poter finire anche in una corsa cominciata a cluster già senza guida.
In quel caso la resa dirà di non aver mai visto un primario da nominare.

### Un'interruzione chiusa non si allunga

L'errore speculare esiste, ed è più insidioso. Se ogni sguardo successivo rispostasse la fine
dell'interruzione, la durata crescerebbe finché qualcuno guarda: **un numero che sbaglia verso lo
spettacolare.** È più difficile da notare del primo, per la ragione più semplice del mondo — la
slide ne guadagna.

## La pazienza: la regola del §6.2, che finalmente esiste

Il design conteneva una frase mai implementata: «dopo 30 s senza primario, smetti di ritentare». Era
rimasta una frase per un motivo pratico: nessuno mette in una suite veloce una prova che aspetta
mezzo minuto, e **una prova che nessuno esegue non protegge niente.**

Con la porta `Clock` la stessa regola si verifica in millisecondi. Nelle prove la pazienza vale un
secondo, l'intervallo un quarto, il tempo lo decide `FakeClock`, e la suite intera dura centesimi.
Il conto è a mano e il valore atteso è **esatto**, non una tolleranza:

```
sguardo 1 · t=0 ms      SANO      — il ricordo si stabilisce
sguardo 2 · t=250 ms    CADUTO    — l'interruzione si apre, inizio=250
sguardo 3 · t=500 ms    CADUTO    — atteso 250 ms
sguardo 4 · t=750 ms    CADUTO    — atteso 500 ms
sguardo 5 · t=1000 ms   CADUTO    — atteso 750 ms
sguardo 6 · t=1250 ms   CADUTO    — atteso 1000 ms ≥ pazienza → resa
```

Sei letture. Con `pazienza_ms=1001` diventano sette: un millisecondo di pazienza in più è un giro in
più, ed è la prova che la regola smette quando deve **e non prima**.

### La resa non chiude l'interruzione

Aver smesso di aspettare non vuol dire che sia finita. Se la resa scrivesse una fine,
`durata_ms` misurerebbe la pazienza di chi guarda invece del guasto — un numero che dice più
dell'osservatore che del cluster.

E non è un giro andato male, è uno **stato**: dopo la resa, chiamare `segui` di nuovo non riapre gli
occhi. Riprendere richiede un `TopologyWatcher` nuovo, cioè una decisione esplicita di chi chiama.

## Il nono evento, e perché è costato un ADR

Il piano chiedeva che la resa fosse **detta**, non solo eseguita. Nessuno degli otto eventi del §6.3
sapeva dirlo senza mentire: `WriteFailed` parla di una scrittura che qui nessuno ha tentato,
`RetryAttempted` annuncia un tentativo che non ci sarà, `TopologyChanged` riferisce il cluster mentre
la resa è una decisione di chi osserva.

La strada era una sola: aggiungere l'evento e pagarne il prezzo procedurale.
[ADR-0082](../../docs/Decision.md#adr-0082) porta gli eventi a nove con `PrimaryWaitAbandoned`, che
dichiara `atteso_ms`, `pazienza_ms` e `ultimo_primario`.

**I due numeri viaggiano insieme e non è ridondanza.** «Ho aspettato 30 000 ms» non si legge finché
non si sa che la pazienza valeva 30 000 — e dal vivo la pazienza si abbassa apposta, per non tenere
la sala ferma mezzo minuto. È il rapporto fra i due a restare vero quando il valore assoluto cambia.

`ultimo_primario` è opzionale perché un client può connettersi a primario già caduto, e in quel caso
non ne ha mai visto uno da nominare.

**La cosa da notare è come ci si è arrivati.** La guardia
`test_gli_eventi_del_design_sono_nove_e_sono_quelli` elenca le sottoclassi di `Evento` e le confronta
con l'insieme del design. Finché i nomi erano otto, il nono è arrivato e l'ha fatta fallire — che è
il motivo per cui questa sezione esiste. Ha funzionato esattamente come doveva: ha reso il costo
**visibile**, e ha costretto la decisione a passare per la sede giusta invece di lasciar crescere il
dominio in silenzio. Adesso i nomi sono nove, e il decimo troverà lo stesso muro.

## `segui` vuole un limite di giri, e non è una scortesia

```python
watcher.segui(giri=100)
```

Il parametro è obbligatorio. Un ciclo senza limite, in attesa di un fatto che non arriva, non
fallisce: si **pianta**. Il Task 5 ha imparato che una suite piantata è peggio di una suite rossa,
perché non dice niente e somiglia a un guasto della macchina (nota di metodo 153,
[M-010](Sources.md#m-010)).

Il limite si mette generoso, e a fermare il ciclo è il fatto: la chiusura dell'interruzione, oppure
la resa. Il numero di letture effettive è quindi **un'asserzione**, non un dettaglio — «sei letture
su cento giri concessi» dice che ha smesso perché ha deciso, non perché è finito.

L'attesa sta **fra** uno sguardo e l'altro, mai dopo l'ultimo. Tre sguardi, due attese: l'attesa dopo
l'ultimo non serve a nessuno, e in scena sarebbe un quarto di secondo di schermo fermo alla fine di
ogni blocco.

## Il limite di questo osservatore, dichiarato

**Questo `TopologyWatcher` interroga; non ascolta.** La risoluzione della misura è l'intervallo di
campionamento: un'interruzione lunga 300 ms, guardata ogni 250, può risultare di 250 o di 500.
L'errore è al più un intervallo, e non si riduce se non guardando più spesso — cioè facendo più giri di
rete verso il cluster.

Va bene per la scena, non va bene per una misura. Al **Task 7** `SdamBridge` riceverà gli stessi
passaggi dagli eventi SDAM del driver, cioè **quando accadono**, e la stessa `Interruzione` diventerà
precisa. Le due strade convivono apposta: questa non ha bisogno di un driver per essere provata, e
resta la sola disponibile contro un `ClusterInspector` che non emette eventi.

Il numero che finirà sulle slide verrà da lì. Il numero che si vede scorrere durante la demo viene
da qui.

## Che cosa hanno insegnato le rotture, questa volta

Ventuno rotture deliberate, una alla volta, con ripristino da copia
([M-011](Sources.md#m-011)). Diciassette hanno fatto scattare una guardia. **Quattro sono passate in
silenzio**, e le quattro prove che le coprono sono nate lì.

La più istruttiva è l'ordinamento. Esisteva già una prova che asseriva l'ordine per indirizzo di due
`ServerStateChanged`; togliendo `sorted` dal codice, restava **verde**. Il motivo è banale una volta
visto: anche l'ordine di comparsa dei server, in quella prova, era alfabetico. La prova osservava il
risultato giusto per il motivo sbagliato.

> Una guardia si prova solo con un caso in cui, se non ci fosse, si vedrebbe.

La prova nuova elenca i server **al contrario** nella prima descrizione, e adesso la rottura si vede.

## Quando è l'arnese a mentire

Le rotture di questo task hanno prodotto due rapporti falsi prima di produrne uno vero, ed è
materiale che vale più delle rotture stesse.

**Il primo rapporto diceva ventuno su ventuno.** Il risultato più rassicurante possibile, e
completamente falso: lo script leggeva il codice d'uscita di `pytest` come un booleano, e `pytest`
stava uscendo con **4** — errore d'uso, un'opzione inesistente rimasta in riga di comando — per tutte
e ventuno. Zero prove eseguite, ventuno «catturate». Il repository conosceva già il codice 5 («nessuna
prova raccolta», [M-005](Sources.md#m-005)); adesso conosce anche il 4, e la regola generale: **un
codice d'uscita non è un booleano.** Solo l'1 vuol dire «una prova ha fallito».

**Il secondo rapporto attribuiva la rottura sbagliata.** Due mutazioni diverse risultavano catturate
dalla stessa prova, il che è impossibile se davvero sono diverse. La causa è la cache dei bytecode:
Python decide se ricompilare confrontando **la data di modifica in secondi e la dimensione in byte**
del sorgente. Le rotture 5 e 6 producevano file di dimensione identica — la stessa sostituzione,
`SCONOSCIUTO` → `IRRAGGIUNGIBILE`, in due punti — e venivano scritte nello stesso secondo. La seconda
corsa eseguiva il `.pyc` della prima.

Con `PYTHONDONTWRITEBYTECODE=1` e la cache rimossa fra una rottura e l'altra, ogni mutazione inciampa
nella prova che la nomina. Il segnale d'allarme, in entrambi i casi, era lo stesso: **un rapporto
troppo pulito.**

## Che cosa le prove non asseriscono

- **Non c'è ancora nessun `ClusterInspector` vero.** Tutto qui è provato contro `FakeInspector`, che
  restituisce descrizioni preparate. Che le descrizioni somiglino a quelle che PyMongo produrrà
  davvero è una promessa del Task 9, non un fatto verificato.
- **Il `TopologyWatcher` non è provato sotto concorrenza.** È pensato per essere guidato da un solo
  thread — quello che chiama `segui` — e nessuna prova lo dice. Quando al Task 10 la TUI entrerà in
  scena, l'invariante andrà scritto e difeso come è stato fatto per il generatore di carico.
- **Nessuna misura di quanto costa un giro** verso un cluster vero. L'intervallo predefinito di 500 ms
  è una scelta di scena, non un numero misurato.

---

**Torna a:** [README.md](README.md) per l'indice, oppure
[06-carico-tentativi-e-latenze.md](06-carico-tentativi-e-latenze.md) per l'altro caso d'uso.

**Fonti:** [M-005](Sources.md#m-005), [M-010](Sources.md#m-010), [M-011](Sources.md#m-011).
**Decisioni:** [ADR-0007](../../docs/Decision.md#adr-0007),
[ADR-0019](../../docs/Decision.md#adr-0019), [ADR-0082](../../docs/Decision.md#adr-0082).
