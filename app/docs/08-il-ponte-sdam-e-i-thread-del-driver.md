# 8. Il ponte SDAM: chi consegna gli eventi, e da quale thread

> Il principio in una riga: **un listener lento non rallenta la grafica, rallenta il driver — e
> allunga proprio il failover che si sta cronometrando.**

`SdamBridge` sta in `app/src/mongolab/infrastructure/sdam.py` ed è il punto in cui l'applicazione
smette di *interrogare* il cluster e comincia ad *ascoltarlo*. Il `TopologyWatcher` del Task 6 guarda
ogni mezzo secondo e riferisce quello che ha visto; questi quattro listener ricevono il cambiamento
**quando accade**, perché è il driver a chiamarli.

Il prezzo di quel salto è una regola stretta, ed è la ragione per cui questa pagina esiste.

## Costruire, depositare, ritornare — e nient'altro

[ADR-0019](../../docs/Decision.md#adr-0019) dice che ogni callback fa tre cose: costruisce un evento
congelato, lo mette in una `queue.Queue`, ritorna. La regola sembra igiene e non lo è. Viene da una
riga della documentazione di PyMongo ([S-010](../../docs/Sources.md#s-010)):

> «Events are delivered synchronously. Application threads block waiting for event handlers (e.g.
> `started()`) to return.»

Il thread che aspetta è il **monitor del driver**, quello che manda i battiti e aggiorna la topologia.
Se il callback disegna una tabella, il monitor resta fermo mentre la tabella si disegna, e il momento
in cui il client si accorge che il primario è caduto arriva più tardi. Il numero che finisce sulla
slide — «l'interruzione è durata *tot*» — diventa più grande di quanto sia stata davvero, **per
colpa dello strumento che la misura**. Non è una degradazione: è una falsificazione.

Tutto il resto di questa pagina discende da lì.

## Quattro classi, e non è una preferenza di stile

Il ponte contiene quattro oggetti — `AscoltatoreServer`, `AscoltatoreTopologia`,
`AscoltatoreHeartbeat`, `AscoltatoreComandi` — che condividono una coda sola. Un lettore ragionevole
si chiede perché non una classe che le implementa tutte e quattro: sarebbe meno codice, e la coda
sarebbe naturalmente unica.

Non si può, e il motivo è nei nomi. `ServerListener` e `TopologyListener` dichiarano **gli stessi
tre metodi**: `opened`, `closed`, `description_changed`. Il driver decide a chi consegnare con
`isinstance`, non guardando quali metodi l'oggetto abbia. Una classe che eredita da entrambi
verrebbe iscritta a due elenchi, e il suo unico `description_changed` riceverebbe sia cambi di
server sia cambi di topologia — due oggetti diversi, sulla stessa firma. Distinguerli dentro il
metodo si potrebbe fare, ed è esattamente il genere di cosa che ADR-0019 vieta: un `isinstance` in
più nel percorso caldo, per risparmiare una classe.

Quattro classi separate sono la forma in cui la distinzione la fa il driver, gratis.

## Il contratto da fissare è la mappatura, non il driver

I callback non sono tipizzati con le classi di PyMongo ma con sei `Protocol` scritti qui:
`DescrizioneServerDelDriver`, `DescrizioneTopologiaDelDriver`, `CambioServerDelDriver`,
`CambioTopologiaDelDriver`, `BattitoRiuscitoDelDriver`, `ComandoRiuscitoDelDriver`. Ciascuno dichiara
**soltanto** gli attributi che questo codice legge, tutti in sola lettura.

Serve a due cose, e la seconda non era prevista.

La prima: le prove costruiscono a mano gli oggetti che il driver passerebbe, e la traduzione si
verifica **senza PyMongo vivo**. Nessun cluster, nessun mock del driver, nessuna attesa. Quaranta
prove girano in meno di un secondo perché non c'è niente da aspettare.

La seconda: un metodo che accetta un tipo **più largo** di quello dichiarato dalla classe base
soddisfa comunque l'ereditarietà, e mypy lo verifica. Siccome `AscoltatoreServer` eredita davvero da
`monitoring.ServerListener`, `mypy --strict` deve dimostrare che
`ServerDescriptionChangedEvent` — la classe vera — soddisfa `CambioServerDelDriver`. Il controllo di
compatibilità con il driver arriva senza che nessuno lo scriva, e arriva **a ogni `make app-check`**,
non alla prima esecuzione contro un cluster.

## Il tipo che ha corretto il codice: `mongo-1:None`

La prima stesura dei `Protocol` dichiarava `address: tuple[str, int]`, che è quello che uno si
aspetta da un indirizzo. `mypy --strict` ha rifiutato:

```
error: Argument 1 has incompatible type "tuple[str, int | None]"; expected "tuple[str, int]"
```

In PyMongo la porta è opzionale, perché un indirizzo può arrivare senza. Se il controllo non avesse
protestato, `indirizzo_di` avrebbe scritto `mongo-1:None` in una riga della cronaca, e nessuna prova
scritta a mano se ne sarebbe accorta — perché chi scrive il doppio mette sempre la porta. Da lì la
riga:

```python
return host if porta is None else f"{host}:{porta}"
```

È l'esempio più netto, in questa applicazione, di che cosa comprano i tipi: non hanno impedito un
crash, hanno impedito una **stringa sbagliata a schermo durante il talk**.

## Tre numeri, tre unità, e una documentazione che sbaglia

Il ponte legge tre durate, e nessuna delle tre è nella stessa unità delle altre
([M-012](Sources.md#m-012)):

| Da dove | Attributo | Unità vera | Che cosa dice la documentazione |
|---|---|---|---|
| descrizione di un server | `round_trip_time` | secondi | niente |
| battito riuscito | `duration` | **secondi** | «The duration of this heartbeat in **microseconds**» |
| comando riuscito | `duration_micros` | microsecondi | microsecondi |

La riga di mezzo è un errore della documentazione di PyMongo 4.17, verificato nel suo sorgente: il
valore passato all'evento è `round_trip_time`, che viene da `_monotonic_duration`, che restituisce
`time.monotonic() - start` — secondi. Se `mongolab` avesse creduto alla docstring, un battito di
2 ms sarebbe finito nella cronaca come 0,000002 ms, e il riepilogo delle latenze avrebbe mostrato
zeri. La **nota 155** — uno zero inventato è la peggiore risposta mancante — sarebbe scattata per
colpa di una riga di documentazione.

Il codice converte tutto in millisecondi, che è l'unità del dominio: `* 1000.0` per i secondi,
`/ 1000.0` per i microsecondi. Tre rotture deliberate ([M-016](Sources.md#m-016), numeri 8, 19 e 22)
verificano che nessuna delle tre conversioni si possa togliere o invertire senza che una prova lo
dica.

## Il battito che dura trenta secondi e non è lento

`AscoltatoreHeartbeat.succeeded` comincia con due righe che sembrano una svista:

```python
if evento.awaited:
    return
```

Da MongoDB 4.4 il monitoraggio usa lo *streaming hello*: il client apre una richiesta e il server
**non risponde finché non ha qualcosa da dire**, fino a un tetto di dieci secondi. La durata di quel
battito misura l'attesa, non la rete. Metterla fra i campioni di latenza vorrebbe dire riempire il
riepilogo di numeri a quattro cifre che non descrivono nessun ritardo: il p95 diventerebbe il tetto
dello streaming, e il grafico direbbe che il cluster è lentissimo mentre è perfettamente sano.

I battiti non in attesa restano, e sono la misura buona: quelli sì sono un giro di rete.

## I cinque silenzi

Otto callback dei dodici implementati non fanno niente. Si raggruppano in cinque silenzi,
perché cinque sono le ragioni:

| Callback | Perché tace |
|---|---|
| `ServerListener.opened` / `closed` | è il ciclo di vita degli **oggetti del driver**, non dei nodi |
| `TopologyListener.opened` / `closed` | è l'accensione e lo spegnimento del client, non un fatto del cluster |
| `ServerHeartbeatListener.started` | non è un fatto, è l'intenzione di verificarne uno |
| `ServerHeartbeatListener.failed` | vedi sotto |
| `CommandListener.started` / `failed` | l'inizio non è una durata; il fallimento arriva già da `WorkloadRunner` |

Il silenzio meno ovvio è `heartbeat.failed`, perché [ADR-0006](../../docs/Decision.md#adr-0006) lo
chiama per nome — «il momento esatto in cui il client si accorge della caduta» — e sembra quindi
l'evento più prezioso di tutti.

Tace lo stesso, per tre ragioni che vanno insieme. Non c'è un evento di dominio che lo porti senza
mentire: gli otto del §6.3 più `PrimaryWaitAbandoned` non ne hanno uno, e il precedente di
[ADR-0082](../../docs/Decision.md#adr-0082) dice che si aggiunge un evento invece di piegarne uno
esistente. Il fatto **arriva comunque**, un istante dopo, come `ServerStateChanged` verso
`IRRAGGIUNGIBILE`: il battito fallito è la causa, il cambio di ruolo è la notizia. E i battiti
falliscono a raffica durante un'interruzione — uno per nodo caduto a ogni giro di monitoraggio —
mentre il cambio di ruolo si emette **una volta**.

Se un giorno servisse l'istante esatto, la risposta non sarà scomodare `LatencySampled`: sarà un
decimo evento e un ADR.

## `ALTRO`, e il momento in cui non si può scrivere «non so»

Questo task ha aggiunto un valore a `RuoloServer`, ed è l'unica modifica al dominio che il Task 7 ha
richiesto. Il driver conosce tipi di server che il talk non nomina — `RSOther`, `RSGhost`,
`LoadBalancer` — e la prima stesura li mandava tutti su `SCONOSCIUTO`.

È una traduzione sbagliata, e il caso in cui si vede è proprio quello della demo. Un membro del
replica set che sta ripartendo passa qualche secondo in `RECOVERING` o `STARTUP2`, e il driver lo
chiama `RSOther`. Sono i secondi in cui la sala sta guardando quella riga. Scrivere «sconosciuto»
direbbe *il client non ha capito*, mentre il client ha capito benissimo.

I tre stati dell'assenza sono ora tre cose distinte, e la distinzione è nel docstring
dell'enumerazione: `SCONOSCIUTO` è **l'assenza di un'osservazione**, `IRRAGGIUNGIBILE` è
**un'osservazione** (il client ha provato e non è riuscito), `ALTRO` è **il contrario di entrambi** —
il client sa che cosa ha davanti, ed è qualcosa che questa scena non nomina.

Nessun ADR: `RuoloServer` non è enumerato nel design, a differenza dei nove eventi. Se lo fosse
stato, questa riga sarebbe costata una decisione come è costata al nono evento.

## Chi consegna gli eventi, e da quale thread

La documentazione dice «synchronously» e lascia credere che ogni callback arrivi sul thread che ha
generato il fatto. Misurato, in PyMongo 4.17, il quadro è più articolato
([M-014](Sources.md#m-014)):

| Famiglia | Thread che chiama il callback |
|---|---|
| server (`ServerListener`) | `pymongo_events_thread` |
| topologia (`TopologyListener`) | `pymongo_events_thread` |
| battiti (`ServerHeartbeatListener`) | il thread del monitor di quel server |
| comandi (`CommandListener`) | il thread applicativo che ha eseguito il comando |
| topologia, **durante `close()`** | il thread che chiama `close()` — `MainThread` nella misura |

Metà degli eventi passa quindi da una **coda interna del driver**, drenata da un thread suo: i due
`publish_*` di `_process_change` non chiamano i listener, fanno `self._events.put(...)`. Il driver
applica a sé stesso, per i suoi listener più rumorosi, esattamente lo schema che
[ADR-0019](../../docs/Decision.md#adr-0019) impone all'applicazione — un'informazione che vale come
conferma indipendente della decisione, e che nessuna pagina di documentazione dice.

Non cambia però la regola, per due motivi. Quel thread è **uno solo**: un callback lento lì mette in
coda tutti gli altri eventi di topologia, compreso quello che segnala il primario nuovo. E gli altri
due terzi arrivano davvero sul thread che stava lavorando. La conclusione pratica resta: **il thread
che chiama un callback non è stabile e non è affar suo**. Il ponte non tiene stato, non ha lucchetti,
e non ne ha bisogno — la coda tiene i suoi ([A-010](Sources.md#a-010)).

## Un listener che solleva, non lo sa nessuno

Se un callback alza un'eccezione, PyMongo la cattura e la stampa su `stderr`, poi tira dritto
([M-015](Sources.md#m-015)). Il codice che ha costruito il `MongoClient` non se ne accorge, il
driver continua a funzionare, e le uniche tracce sono sette righe di traceback.

Durante il talk quelle sette righe non esistono: la TUI di Rich ([ADR-0050](../../docs/Decision.md#adr-0050))
occupa il terminale, e un `traceback` che arriva sotto un `Live` viene sovrascritto al primo
aggiornamento. Un ponte rotto si presenterebbe come **una cronaca che non si aggiorna**, senza
messaggi, davanti a una sala.

È la seconda ragione, indipendente dalla velocità, per cui questi callback fanno tre cose sole: meno
codice gira lì dentro, meno cose possono sollevare senza che nessuno lo veda. La difesa vera arriva
al Task 11, dove il composition root può controllare che la cronaca stia procedendo; questa pagina
si limita a dichiarare il buco, come vuole il patto di lettura.

## Quanto costa disobbedire, e perché la soglia è dieci

La prova `test_il_callback_ritorna_nel_tempo_di_un_inserimento_in_coda` confronta duemila giri del
callback vero con duemila `put_nowait`, e chiede che il rapporto stia sotto **10**. La soglia non è
scelta a occhio: viene da tre misure ([M-013](Sources.md#m-013)).

| Che cosa fa il callback | Costo per giro | Rapporto | La prova se ne accorge? |
|---|---|---|---|
| costruisce, deposita, ritorna | ~1,3 µs | ~2,9 | — (è il caso buono) |
| più una frase formattata | ~2,4 µs | ~5,5 | **no** |
| più una tabella di Rich | ~386 µs | ~883 | sì, di tre ordini di grandezza |

Vale la pena dire ad alta voce che cosa la prova **non** prende: una `f-string` dentro il callback
resta sotto la soglia. È una scelta consapevole. Una soglia a 4 renderebbe la prova instabile su una
macchina carica, e il fallimento sarebbe indistinguibile dal rumore; una soglia a 10 non fallisce mai
per caso e prende comunque l'errore che conta. Perché la differenza fra i due errori è enorme: a
ottocento comandi al secondo, 386 µs per evento sono **0,31 secondi di CPU per ogni secondo di
orologio**, sottratti al thread del driver. Una frase formattata costa un microsecondo.

Il divieto della formattazione costosa resta scritto nel codice e in ADR-0019; la prova difende il
confine oltre il quale il vincolo diventa un danno misurabile. Le due cose non coincidono, e fingere
che coincidano sarebbe una prova che dice più di quello che sa.

## Per client, non globalmente

PyMongo permette di registrare i listener in due modi: `monitoring.register()`, che vale per tutto il
processo, e `MongoClient(event_listeners=[...])`, che vale per un client solo.
[ADR-0006](../../docs/Decision.md#adr-0006) sceglie il secondo, e il Task 7 lo prova costruendo due
client nella stessa esecuzione: quello con il ponte riceve i quattro ascoltatori, l'altro ne ha zero,
e la cronaca contiene solo i fatti del primo.

Serve, e non è un'ipotesi: al Task 13 la scena del failover userà un client per il carico e uno per
l'osservazione, e la registrazione globale li mescolerebbe in un'unica cronaca senza modo di
separarli.

## La rottura che non era una rottura

Ventotto modifiche deliberate al solo `sdam.py`, una alla volta ([M-016](Sources.md#m-016)).
Ventisette hanno fatto fallire almeno una prova. Una è rimasta verde, e la spiegazione non è quella
che ci si aspetta.

La modifica numero 15 legge l'indirizzo del server dalla descrizione **di prima** invece che da
quella **di dopo**. Nessuna prova protesta — e non perché ne manchi una. Il driver pubblica quel
cambio in un punto solo di tutto il suo codice, e la descrizione vecchia la trova indicizzando per
l'indirizzo di quella nuova:

```python
sd_old = td_old._server_descriptions[server_description.address]
```

I due lati portano quindi **sempre** lo stesso indirizzo, per costruzione. Non sono due letture di
cui una giusta: sono la stessa lettura scritta in due modi.

La cura non è inventare una prova. Una prova che costruisca a mano un cambio con due indirizzi
diversi passerebbe da rossa a verde, e sembrerebbe una guardia — ma difenderebbe un caso che il
driver non può produrre. Si aggiungerebbe copertura senza aggiungere verità. La cura è **verificare
l'invariante alla fonte e scriverlo**, che è quello che il docstring del metodo adesso fa, con il
riferimento al file e alla riga.

È la **nota di metodo 161**: le tre uscite della nota 144 e la quarta della nota 153 danno per
scontato che una modifica cambi il comportamento. Qui il file è cambiato e il comportamento no,
perché le due scritture sono uguali sotto un invariante della dipendenza. Prima di concludere che
manca una guardia, va escluso che manchi la differenza.

## Che cosa non è ancora verificato

Questa pagina chiude metà della promessa che [04](04-eventi-del-driver-e-concorrenza.md) aveva
lasciato aperta, e va detto quale metà.

**Chiuso:** il comportamento di PyMongo non è più solo letto. I thread di consegna, le unità delle
durate, il destino di un'eccezione nel listener e il costo di un callback disonesto sono stati
misurati qui, su questa versione, con l'output riportato in `Sources.md`.

**Aperto:** niente di tutto questo ha ancora parlato con un cluster. I client delle prove nascono con
`connect=False`, e i due eventi che contano davvero per il talk — un battito che fallisce mentre il
primario cade, un `ServerStateChanged` verso `PRIMARIO` su un altro nodo — nessuno li ha visti
arrivare. La sede è il **Task 8**, contro gli stack veri.

**Chiuso al Task 15:** `ChunkMigrated`. Il ponte non lo emetteva, e nessuno dei quattro listener
SDAM era il posto in cui potesse nascere — ma la ragione per cui non nasce non sta nel ponte. Sta
nel cluster: in 1 153 giri il balancer di questo lab non ha migrato un chunk nemmeno una volta,
perché con una chiave hashed non c'è niente da ribilanciare ([M-049](Sources.md#m-049)). L'evento
è uscito dal dominio ([ADR-0103](../../docs/Decision.md#adr-0103)), che è precisamente ciò che
questa pagina aveva promesso sarebbe successo.

---

**Da leggere prima:** [04-eventi-del-driver-e-concorrenza.md](04-eventi-del-driver-e-concorrenza.md),
che spiega la decisione di cui questa pagina è l'esecuzione.

**Fonti:** [S-010](../../docs/Sources.md#s-010), [A-010](Sources.md#a-010),
[M-012](Sources.md#m-012), [M-013](Sources.md#m-013), [M-014](Sources.md#m-014),
[M-015](Sources.md#m-015), [M-016](Sources.md#m-016).
**Decisioni:** [ADR-0006](../../docs/Decision.md#adr-0006),
[ADR-0007](../../docs/Decision.md#adr-0007), [ADR-0019](../../docs/Decision.md#adr-0019),
[ADR-0050](../../docs/Decision.md#adr-0050), [ADR-0082](../../docs/Decision.md#adr-0082).
