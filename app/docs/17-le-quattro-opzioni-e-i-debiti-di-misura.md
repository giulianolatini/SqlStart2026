# 17. Le opzioni di misura, e i debiti che saldano

> Il principio in una riga: **chi non chiede non riceve.** Un'opzione lasciata a `None` non entra
> nel client, e la riga di base resta byte per byte quella di ieri. È la sola condizione perché due
> numeri misurati in due giorni diversi si possano ancora accostare.

Quattro pagine di `docs/02-architetture` avevano scritto per iscritto la stessa frase: quella
misura «ha senso solo sotto carico controllato, cioè con l'applicazione Python di `feature/04`, e
prima di allora sarebbe aria». Era una promessa con un debitore preciso. Questo capitolo è il
saldo: quattro opzioni nuove sulla riga di comando — cinque, con quella che il Task 18 ha
aggiunto in fondo — sette misure, e sette righe di «cosa questa
pagina non dice» che smettono di essere scoperti e diventano rimandi.

La riga che l'applicazione stampa quando una di quelle opzioni è accesa:

```
carico   standalone · 8 scrittori · 4 lettori · 2k
opzioni  journal=True
```

Quando non se ne chiede nessuna, quella riga **non compare affatto**. Non è economia di spazio: è
la stessa regola del codice, portata sullo schermo. Una corsa senza opzioni non ha niente da
dichiarare perché non ha cambiato niente.

Tre cose di questo capitolo sono arrivate perché la misura ha contraddetto chi la stava
progettando: il primo disegno della prova su `maxPoolSize` misurava due variabili insieme, il
prezzo di `j: true` era sbagliato del 9 % finché non si è tolto l'avvio dell'interprete, e il
controllo delle citazioni approvava un file in cui due citazioni erano sparite. Sono le tre sezioni
che valgono più delle altre.

---

## Le quattro regole di `opzioni_di_misura`

`opzioni_di_misura` sta in `bersagli.py`, accanto a `connetti`, e restituisce una mappa da passare
a `connetti(**extra)`. Il gancio `**extra` esisteva dal Task 5 e non aveva ancora un chiamante che
lo usasse per misurare: adesso ce l'ha.

```python
def opzioni_di_misura(
    *,
    journal: bool | None = None,
    retry_writes: bool | None = None,
    max_staleness_s: int | None = None,
    max_pool_size: int | None = None,
) -> dict[str, Any]:
```

Quattro argomenti, quattro `None`, e quattro regole che [ADR-0109](../../docs/Decision.md#adr-0109)
fissa.

**Uno: chi non chiede non riceve.** Un argomento a `None` non compare nella mappa. Sembra ovvio, e
non lo è: la tentazione è scrivere `journal=False` come predefinito, «tanto è quello che fa già
pymongo». Ma un valore scritto è un valore **dichiarato**, e un giorno il predefinito del driver
cambia mentre il nostro resta fermo — o viceversa. La riga di base dev'essere l'assenza, non una
copia dell'assenza.

**Due: la staleness non viaggia mai da sola.** `maxStalenessSeconds` con la preferenza predefinita
è un `ConfigurationError` alla **costruzione** del client: `primary` non può avere un limite di
vecchiaia, perché il primario per definizione non è in ritardo. Quindi la funzione aggiunge sempre
`readPreference` insieme, e non offre nessun modo di separarli. Un'API che permette di costruire lo
stato illegale e poi lo rifiuta è un'API che ha spostato il problema sull'utente.

**Tre: `secondary`, non `secondaryPreferred`.** La differenza conta esattamente quando la misura
conta. `secondaryPreferred` ricade sul primario se nessun secondario passa il filtro, e la ricaduta
è **silenziosa**: la lettura riesce, il numero esce, e non c'è niente che dica che il vincolo che
si stava misurando non è stato applicato. Con `secondary` la stessa situazione dà un errore di
selezione, che è la risposta giusta a una domanda sulla staleness.

**Quattro: i nomi sono quelli dell'URI.** Le chiavi della mappa sono `journal`, `retryWrites`,
`readPreference`, `maxStalenessSeconds`, `maxPoolSize` — non `giornale` o `dimensione_pool`. Il
resto di questa applicazione parla italiano; qui no, e per una ragione: la riga stampata a schermo
si incolla dentro un URI o dentro `MONGO_URI` senza traduzione. Chi legge `opzioni retryWrites=False`
sullo schermo sa già che cosa scrivere nella stringa di connessione.

### L'ordine della mappa non è alfabetico

Le chiavi si inseriscono in un ordine fisso — journal, retryWrites, readPreference,
maxStalenessSeconds, maxPoolSize — e `riga_delle_opzioni` le stampa in quell'ordine. In Python un
`dict` conserva l'ordine di inserimento dalla 3.7, quindi la riga è **deterministica** senza doverla
ordinare: due corse con le stesse opzioni producono la stessa riga carattere per carattere. È la
proprietà che rende diffabili due registrazioni `.cast`, e costa zero.

---

## Il prezzo di `j: true`, e la metà che di solito non si racconta

[V-016](../../docs/Sources.md#v-016) aveva misurato **cento scritture confermate e sparite** dopo un
`SIGKILL` allo standalone, e aveva chiuso con una riserva onesta: `j: true` dovrebbe azzerare la
perdita, «al prezzo della velocità». Due affermazioni. La tentazione, misurandole, è pubblicare
solo la prima.

Le due metà, entrambe, sono in [V-075](../../docs/Sources.md#v-075):

| | scritture al secondo | perse dopo il `SIGKILL` |
|---|---|---|
| `--no-journal` | ≈ 4 900 | **2** |
| `--journal` | ≈ 3 330 | **0** |

La perdita si azzera davvero. Il prezzo è **−32 %** sul carico a conteggio fisso, e **−45 %** sul
carico a scadenza con un solo scrittore — due cifre diverse perché le due prove spendono il tempo
in modo diverso, e pubblicarle tutte e due dice più di quanto direbbe la loro media.

Questa misura toglie anche una riserva a V-016. Là gli ack si contavano leggendo un file su cui
`mongosh` stampava, e una pipe può bufferizzare: il conteggio poteva essere **minore** del vero,
quindi la perdita misurata era un minimo. Qui gli ack li conta il processo che li riceve —
`Riepilogo.documenti_confermati` è la somma dei `WriteSucceeded`, cioè delle risposte già arrivate
al chiamante — e quella riserva cade. Il numero è la perdita, non il suo minimo.

### Il 23 % che era sbagliato

Il primo calcolo dava −23 %, e veniva dal rapporto fra le durate a orologio: 1,70 s contro 2,20 s.
È sbagliato, perché dentro quei tempi c'è l'avvio dell'interprete — importare pymongo, costruire il
cablaggio, aprire il client — che non ha niente a che vedere con il giornale.

Il costo fisso si misura con la corsa più corta che l'applicazione sappia fare, `--writes 1
--writers 1`, e vale 0,67–0,78 s. Toglierlo cambia il rapporto da −23 % a −32 %, cioè di un nono
del totale, e lo cambia **in modo asimmetrico**: un addendo costante uguale sui due lati comprime
sempre le differenze verso lo zero. La regola generale sta in
[M-057](Sources.md#m-057), e la sua conseguenza è che il confronto fra le tre architetture non usa
il tempo a orologio: usa `--duration`, e conta le scritture fatte. Con la durata fissata
dall'orologio interno l'avvio esce dal numero da sé.

---

## Il confronto fra le tre architetture, e il numero che non era del server

Il debito più grosso — quello che tutte e tre le pagine di architettura avevano intestato qui — è
il confronto di prestazioni. Stesso carico, stesso dataset deterministico, stessa riga:

```
--writers 8 --readers 4 --doc-size 2k --duration 30 --sink null
```

Tre corse per architettura, da **dentro** la rete Compose: dall'host il replica set si raggiunge in
`directConnection` su una porta sola, e confrontare un nodo con un cluster non sarebbe un confronto
([M-019](Sources.md#m-019)).

| | scritture/s | p50 | p95 | p99 |
|---|---|---|---|---|
| standalone | 1 656 – 1 712 | 2,8 | 12,3 – 13,9 | ≈ 40,6 |
| sharded | 419 – 428 | 5,5 | ≈ 84 | ≈ 95 |
| replica set | 359 – 366 | 9,0 | ≈ 75 | ≈ 88 |

Zero scritture fallite, zero ritentate, ovunque.

E qui la misura ha corretto chi la stava facendo. Il container dell'applicazione ha `cpus: 1.0`, e
**una CPU non basta** a saturare uno standalone: rialzando solo il client a `CPU_APP=4.0` lo
standalone sale a 2 334 scritture/s, **+40 %**, mentre replica set e cluster si muovono del 3 % e
del 9 %, cioè restano fermi. Il numero del lab predefinito non misurava il server, misurava
l'interprete Python.

La firma del fenomeno è la coda, non la mediana: il p50 resta identico a 2,8 ms e il p99 passa da
40,6 a 11,0. **Una mediana intatta con una coda quattro volte più lunga è contesa dal lato di chi
chiede, non lentezza dal lato di chi risponde** — la maggior parte delle operazioni trova la strada
libera, e quelle che aspettano aspettano il proprio processo, non il server. Il dettaglio sta in
[M-056](Sources.md#m-056).

Il controllo che rende leggibile tutto questo è che le altre due architetture **non** si siano
mosse. Se fossero salite tutte e tre del 40 %, il sospetto sarebbe stato la macchina, e non ci
sarebbe stato modo di distinguere.

### Perché si pubblicano due numeri e non uno

[ADR-0111](../../docs/Decision.md#adr-0111) decide che il confronto esce **in coppia**: la riga del
lab predefinito, che chiunque riproduce con un `make`, e la riga del controllo, che dice quanto la
prima fosse limitata dal client. I rapporti citabili sono quelli del controllo — 6,2× fra standalone
e replica set, 5,0× fra standalone e cluster, 1,23× fra cluster e replica set — e la riserva viaggia
**sulla stessa riga del numero**, non in una nota in fondo: una nota in fondo non arriva sulla
slide, il numero sì.

Il 1,23× a favore del cluster sharded merita la sua riga, perché è il numero che si presta di più a
essere citato male. In questo lab **ogni shard ha un solo membro**: la maggioranza si raggiunge da
sé, quindi il cluster paga il salto in più di `mongos` senza pagare la replica. Non è un merito
dello sharding; è la conseguenza di una topologia da portatile.

C'è anche un numero che nessuno aveva chiesto e che vale più di quelli chiesti: sotto lo stesso
carico il replica set **legge** con una mediana più bassa dello standalone, 2,0 ms contro 3,4. Non
perché legga meglio — perché scrivendo cinque volte meno tiene i nodi molto meno occupati. È il
promemoria che in una misura di sistema nessuna colonna è indipendente dalle altre.

---

## `maxPoolSize`: la resa non è la variabile

Il design chiamava la saturazione del pool «materiale didattico», e il Task 5 l'aveva lasciata in
sospeso: `--writers` era il gancio, non la misura. Adesso c'è anche `--max-pool-size`, e con
trentadue scrittori fermi e il solo pool che varia ([V-080](../../docs/Sources.md#v-080)):

| `maxPoolSize` | scritture/s | p50 | p95 | p99 | **massimo** |
|---|---|---|---|---|---|
| 2 | 3 613 | 0,5 | 0,8 | 1,5 | **20 004,7** |
| 4 | 3 284 | 1,0 | 2,5 | 4,0 | **20 009,6** |
| 8 | 3 090 | 2,1 | 5,6 | 8,8 | **20 002,8** |
| 16 | 3 113 | 4,3 | 11,6 | 17,2 | **19 997,4** |
| 31 | 3 526 | 7,4 | 19,9 | 28,7 | **19 973,1** |
| 32 | 3 470 | 7,7 | 21,1 | 32,7 | 101,7 |
| 33 | 3 479 | 7,7 | 21,0 | 32,2 | 137,4 |
| 100 (predefinito) | 3 476 | 7,6 | 21,4 | 35,2 | 117,6 |

Tre letture, e nessuna è quella che ci si aspetta.

**La resa non è la variabile.** Da due connessioni a cento la resa oscilla fra 3 090 e 3 613, senza
una direzione. Chi si aspettava un crollo stringendo il pool ha in mente un collo di bottiglia che
qui non c'è: il server è servito lo stesso, solo da meno canali più occupati.

**I percentili *migliorano* stringendo il pool.** Con due connessioni il p50 è 0,5 ms, con cento è
7,6. Non è un paradosso: la coda si è spostata: da dentro il server, dove ottanta richieste
concorrenti si contendono le risorse, a fuori, nella `waitQueue` del driver. Le operazioni che
partono trovano un server sgombro, e chi aspetta non è misurato mentre aspetta.

**Il massimo è una funzione a gradino, e il gradino è a `pool = scrittori`.** Da 31 a 32 il massimo
passa da 20 000 ms a 102. Venti secondi sono la durata della corsa: c'è un thread che ha aspettato
dall'inizio alla fine e non ha mai scritto. Con `waitQueueTimeoutMS` non impostato il driver non si
arrende mai, quindi non c'è nessun errore, nessuna scrittura fallita, nessun ritentativo — solo una
colonna, la meno rispettabile statisticamente di tutte, che dice che qualcosa è rotto.

Il motivo per cui p50, p95 e p99 restano ciechi è istruttivo: **il thread affamato contribuisce
pochi campioni proprio perché è affamato.** Se aspetta non scrive, e se non scrive non compare. I
percentili pesano le operazioni, non i thread, quindi il thread che soffre di più è il meno
rappresentato nella statistica che dovrebbe descriverlo. È anche la risposta alla domanda che il
docstring di `Latenze` lasciava aperta — perché accanto ai percentili stia anche il massimo
([M-054](Sources.md#m-054)).

### Il primo disegno misurava due cose insieme

La prima versione di questa prova teneva il pool fermo a 4 e faceva salire gli scrittori: 8, 16, 24,
32. La resa **scendeva** — 4 118, 3 372, 2 632, 2 446 — e la lettura naturale era «ecco la
saturazione del pool».

Era falsa. Una resa che *scende* aggiungendo scrittori non è un pool saturo: un pool saturo tiene la
resa e allunga le attese, perché il server continua a essere servito allo stesso ritmo da quelle
quattro connessioni. Una resa che scende vuol dire che si sta perdendo lavoro da qualche parte, e in
un client con una CPU quella parte è la contesa fra thread Python.

Il disegno sbagliato muoveva **due** variabili insieme: la pressione sul pool e la contesa sulla
CPU del client. Il disegno buono ne muove una sola — scrittori fermi a 32, `CPU_APP=4.0`, e solo il
pool che cambia. La lezione è registrata dentro V-080 invece di essere cancellata: un disegno
scartato è un risultato, e chi lo rifarà lo rifarà meglio sapendo perché.

---

## `analyzeShardKey` risponde una volta, e questa applicazione emette flussi

`analyzeShardKey` era uno scoperto dichiarato di `sharded-cluster.md`, con una motivazione che la
misura ha smentito: «richiede un campione di query reali che una demo con dati generati non ha». Il
campione si fabbrica — `configureQueryAnalyzer` più il carico di `mongolab` — e le distribuzioni
compaiono: 576 letture campionate, il 77,6 % mirate e il 22,4 % a tutti gli shard, contro un mix
generato 75/25 ([V-081](../../docs/Sources.md#v-081)).

Il comando ha due condizioni che **non dichiara**, e sono la parte utile:

- Una chiave candidata **senza indice** non dà errore: risponde `ok: 1` e omette
  `keyCharacteristics`. Un `ok: 1` che tace è la forma peggiore di risposta, perché chi la legge in
  uno script non ha niente su cui ramificare.
- Le distribuzioni richiedono l'analizzatore acceso **prima** del traffico, e con due ritardi da
  rispettare: il mongos rilegge la configurazione dei campionatori ogni 10 s, e lo scrittore dei
  campioni gira ogni 90 s. Un tentativo che manda traffico subito dopo l'accensione raccoglie zero
  campioni e sembra un fallimento del comando.

Ci sono anche due rifiuti che insegnano più di un successo: `{stato: 1}` è respinta perché «può fare
solo **6** chunk», `{citta: 1}` undici. Una chiave a bassa cardinalità non è lenta — è
**inutilizzabile**, e il server lo dice prima di provarci.

Nonostante tutto questo, `analyzeShardKey` **resta fuori da `mongolab`**
([ADR-0110](../../docs/Decision.md#adr-0110)). Non per difficoltà: perché non è la stessa forma. Le
sette porte di questa applicazione servono cose che *durano* — un carico che scorre, una topologia
che cambia, un backup che avanza — e ognuna emette un flusso di eventi che una scena consuma.
`analyzeShardKey` risponde una volta sola, e per una risposta sola `mongosh` è lo strumento giusto:
metterla dietro una porta significherebbe inventare un evento per un fatto che non ha durata.

---

## Il controllo che approvava un file rotto

Con le sette voci `V-` scritte e i tre ADR appesi, `make docs-check` ha bocciato: V-079 e V-080
dichiaravano di essere usate da ADR-0109, e il controllo diceva che nessuno le citava. Erano citate.

`check_citations.py` leggeva la riga delle fonti così:

```python
RIGA_FONTI = re.compile(r"^\*\*Fonti:\*\* (.+)$", re.MULTILINE)
```

`.` non attraversa il newline, e `$` con `MULTILINE` è la fine della **riga fisica**. Un ADR con sei
fonti non ci sta in cento colonne, va a capo, e tutto ciò che sta sotto la prima riga spariva —
**in silenzio**, che è il modo peggiore in cui un controllo possa sbagliare: il file risultava
coerente proprio mentre aveva perso un pezzo. È lo stesso errore che la funzione `ripetuti` dello
stesso file esiste per impedire, e stava tre righe più in su.

La correzione allunga il blocco fino alla prima riga vuota, alla prima etichetta in grassetto o al
primo separatore, con due prove nuove: una che il blocco raccolga le righe di continuazione, una che
non inghiotta l'ADR successivo. Su centoundici ADR il buco ne toccava esattamente uno — quello
appena scritto — e per centodieci l'abitudine di tenere le fonti sulla prima riga aveva funzionato
per caso.

**Un controllo che nessuno controlla è una firma in bianco.** Vale la pena scriverlo qui perché è il
genere di difetto che si scopre solo quando un file legittimo viene bocciato: se avesse continuato a
promuovere file rotti, nessuno se ne sarebbe accorto.

---

## Le prove

Il codice nuovo di questo capitolo è piccolo — una funzione e quattro opzioni — e le due suite che
lo coprono, `test_bersagli.py` e `test_cli.py`, contano centoquarantanove prove.

### `opzioni_di_misura`: il vuoto ha un nome

La prova che conta di più non guarda un valore, guarda un'assenza:

```python
def test_senza_argomenti_la_mappa_e_vuota():
    assert opzioni_di_misura() == {}
```

Sembra una prova banale, ed è quella che protegge tutte le misure del repository: se un giorno
qualcuno mettesse un predefinito «tanto è uguale a quello di pymongo», questa prova diventerebbe
rossa e chiederebbe conto della riga di base.

Accanto, la prova che la staleness non esce mai sola, e quella che asserisce sulla forma sul filo
invece che sull'enumerazione:

```python
assert cliente.read_preference.document == {
    "mode": "secondary",
    "maxStalenessSeconds": 90,
}
```

La prima stesura asseriva `read_preference.mode == 1` con il commento `# secondary` accanto, e
falliva: `secondary` vale **2**. La correzione non è stata cambiare l'1 in 2 — è stata smettere di
asserire su un'enumerazione che va saputa a memoria, e asserire sul documento, che si legge
([M-055](Sources.md#m-055)).

### `--writes` e `--duration` si escludono

`workload` accetta un conteggio o una scadenza, mai tutti e due, e la prova guarda il messaggio
d'errore oltre al codice di uscita: un `Exit code 2` senza una riga che dica **quale** delle due
scegliere non aiuta nessuno alle nove di sera in sala.

### Lo stato delle suite

| suite | comando | esito |
|---|---|---|
| unità | `make app-test` | 634 passate |
| tipi | `make app-check` | 66 file, nessun errore |
| integrazione | `make app-test-integration` | 58 passate, 1 min 51 s — con un fallimento intermittente su tre esecuzioni, registrato fra i punti aperti |
| strumenti | `make tools-test` | 168 passate |
| documentazione | `make docs-check` | citazioni e collegamenti coerenti |

---

## La quinta opzione, e un debito che era vero solo sulla riga di comando

Il Task 16 aveva chiuso con quattro opzioni; questa sezione ne aggiunge una, ed è stata scritta due
task dopo per una ragione che vale più dell'opzione.

Il Task 17 aveva registrato fra i punti aperti che «il carico non sa chiedere un write concern
diverso dal predefinito, quindi la corsa con `w: 1` che isolerebbe i 18 390 µs del primario non è
eseguibile». Il Product Owner ha obiettato al **quindi**: `w` è un parametro della stringa di
connessione, nella sezione dopo il `?`. Il manuale gli dà ragione
([S-076](../../docs/Sources.md#s-076)): le opzioni di write concern nell'URI sono `w`, `journal` e
`wtimeoutMS`, e `w` accetta un numero, `majority`, o un tag set.

**Il debito era vero per metà.** La mappa di questo capitolo parla i nomi dell'URI — è la quarta
regola, e l'aveva scritto la docstring — e `connetti(**extra)` inoltra a pymongo qualunque opzione
le si dia, dal Task 5. Il meccanismo per portare `w: 1` fino al client c'era da tredici task.
Mancava la parola per chiederla:

```python
def opzioni_di_misura(
    *,
    write_concern: str | None = None,
    journal: bool | None = None,
    ...
```

Tre dettagli, ciascuno con la sua ragione ([ADR-0114](../../docs/Decision.md#adr-0114)):

- **Testo e non intero**, perché `majority` è un valore legittimo quanto `1`. Diventa intero se è
  tutto cifre, così la mappa annunciata a schermo è identica a quella che il client userà: pymongo
  converte comunque, ma allora la riga stampata direbbe una cosa e il `write_concern` del client
  un'altra.
- **`w` prima di `journal` nella mappa**, che è l'ordine dell'URI e non quello alfabetico. Le due
  opzioni si condizionano — con `journal: true` e un `w` minore di 1 prevale il giornale — e chi
  rilegge una registrazione deve trovarle accostate.
- **`--write-concern` per esteso sulla riga di comando**, non `--w`. La regola «i nomi sono quelli
  dell'URI» vale per la mappa; accanto a `--writers` e `--writes`, un `--w` sarebbe un prefisso
  ambiguo che Typer risolve senza chiedere.

### Che cosa ha trovato la misura che l'opzione ha reso possibile

La riserva di [V-083](../../docs/Sources.md#v-083) si chiude, e la lettura era giusta: con `w: 1` il
cronometro del server passa da 18 913 µs a **644**, un fattore 29.

Ma il manuale ha cambiato il disegno della prova prima che partisse
([S-077](../../docs/Sources.md#s-077)): con `j` non specificato, `w: "majority"` **equivale a
`j: true`**, mentre `w: <numero>` equivale a `j: false`. Scendere da `majority` a `1` spegne due
cose insieme. Quindi tre corse e non due ([V-088](../../docs/Sources.md#v-088)):

| corsa | `opLatencies.writes` | inserimenti/s | p50 client |
|---|---|---|---|
| `w: majority` (predefinito) | 18 913 µs | 351 | 9,8 ms |
| `w: 1` + `--journal` | 11 547 µs | 486 | 7,5 ms |
| `w: 1` | 644 µs | 1 087 | 3,4 ms |

A giornale costante la maggioranza costa **1,38×** di resa; a conferme costanti il giornale costa
**2,24×**. **La cosa cara che il predefinito fa senza dirlo è il disco, non la rete.** Un confronto
a due corse avrebbe dato il numero giusto con la spiegazione sbagliata, e non ci sarebbe stato modo
di accorgersene guardando i risultati.

### Le prove

Cinque, tutte unitarie, tutte viste fallire prima:

```python
assert opzioni_di_misura(write_concern="1") == {"w": 1}
assert opzioni_di_misura(write_concern="majority") == {"w": "majority"}
assert list(opzioni_di_misura(write_concern="1", journal=True)) == ["w", "journal"]
```

più quella che costruisce il client e guarda il `write_concern` che ne esce — un nome sbagliato di
una lettera produce una mappa perfetta e un client identico a prima — e le due sulla riga di
comando: che `--write-concern` compaia in `--help`, e che la riga annunciata dica `opzioni w=1`.

---

## Che cosa questo capitolo lascia aperto

- **Perché un membro in pausa costi ventisette volte.** Con `mongo-rs-3` congelato il replica set
  scrive un ventisettesimo, e la maggioranza si raggiunge ancora con due membri su tre
  ([V-078](../../docs/Sources.md#v-078)). Il rallentamento è misurato, la causa no: un membro
  **congelato** non è un membro **spento**, e separare l'effetto del flow control da quello dei
  timeout di heartbeat richiede una misura che non è stata fatta.
- **Il `mongod` dello stack 01 ha `cpus: 1.0` scritto a mano**, mentre 02 e 03 hanno `CPU_MEMBRO`,
  `CPU_SHARD`, `CPU_MONGOS`. Finché resta così, `CPU_APP` alza solo il client, e il 2 334
  scritture/s dello standalone è a sua volta un limite inferiore: non si sa a quale ritmo saturerebbe
  davvero.
- **`waitQueueTimeoutMS` non è esposto.** Con il predefinito «nessun limite» la fame di pool si
  manifesta come attesa; con un timeout diventerebbe un'eccezione, cioè una scrittura fallita in un
  posto completamente diverso del riepilogo. È mezza misura mancante, e la metà che manca è quella
  che un'applicazione vera configurerebbe.
- **Il rapporto fra CPU del client e resa non è mappato.** Sono state provate una CPU e quattro, non
  le due in mezzo, e non c'è ragione di credere che la relazione sia lineare.
- **`config.sampledQueries` interrogata da `mongos` è rimasta a zero** per tutti i 150 secondi in cui
  `analyzeShardKey` riportava 576 campioni. Non è il termometro giusto, e quale sia non è stato
  trovato.

---

**Decisioni correlate:** [ADR-0109](../../docs/Decision.md#adr-0109) (le quattro opzioni, e chi non
chiede non riceve), [ADR-0110](../../docs/Decision.md#adr-0110) (`analyzeShardKey` resta fuori),
[ADR-0111](../../docs/Decision.md#adr-0111) (il confronto si pubblica in coppia),
[ADR-0107](../../docs/Decision.md#adr-0107) (il carico scrive nella sua collezione),
[ADR-0088](../../docs/Decision.md#adr-0088) (il dataset deterministico e il seme),
[ADR-0072](../../docs/Decision.md#adr-0072) (le misure che una decisione invalida si riscrivono
subito), [ADR-0114](../../docs/Decision.md#adr-0114) (la quinta opzione, e il debito che era vero
solo sulla riga di comando).

**Fonti:** [M-054](Sources.md#m-054), [M-055](Sources.md#m-055), [M-056](Sources.md#m-056),
[M-057](Sources.md#m-057), [M-019](Sources.md#m-019),
[V-016](../../docs/Sources.md#v-016), [V-075](../../docs/Sources.md#v-075),
[V-076](../../docs/Sources.md#v-076), [V-077](../../docs/Sources.md#v-077),
[V-078](../../docs/Sources.md#v-078), [V-079](../../docs/Sources.md#v-079),
[V-080](../../docs/Sources.md#v-080), [V-081](../../docs/Sources.md#v-081),
[V-083](../../docs/Sources.md#v-083), [V-088](../../docs/Sources.md#v-088),
[S-035](../../docs/Sources.md#s-035), [S-067](../../docs/Sources.md#s-067),
[S-076](../../docs/Sources.md#s-076), [S-077](../../docs/Sources.md#s-077)
