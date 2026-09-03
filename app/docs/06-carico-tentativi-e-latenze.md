# 6. Il carico, i tentativi, le latenze

> Il principio in una riga: **ogni numero che finisce su una slide deve poter essere ritrovato nel
> campione da cui viene.**

`WorkloadRunner` è il primo caso d'uso vero dell'applicazione: genera scritture, ritenta quelle che
falliscono, misura quanto ci mettono, e racconta tutto emettendo eventi. Sta in
`app/src/mongolab/application/workload.py`, e non sa che esiste MongoDB — parla con tre porte,
`DocumentStore`, `Clock`, `EventSink`, e con nient'altro.

Questa pagina spiega le tre scelte che non sono ovvie: perché i percentili e non la media, perché la
politica dei tentativi esiste anche se il driver ne ha già una, e perché i worker non toccano mai il
sink.

## Che cosa produce una corsa

Due cose, e non sono ridondanti.

La **cronaca** è la sequenza di eventi che escono dal sink mentre la corsa procede: `WriteSucceeded`,
`LatencySampled`, `WriteFailed`, `RetryAttempted`. È quello che la TUI disegna in diretta, ed è
quello su cui asseriscono le prove — perché la sequenza è il comportamento osservabile, mentre la
resa a schermo è il pezzo più volatile del progetto.

Il **riepilogo** è ciò che resta da leggere dopo: quante scritture, quante riuscite, quante fallite,
quante ritentate, quanti documenti confermati, e le latenze ridotte a sei numeri.

```python
Riepilogo(scritture=40, riuscite=40, fallite=0, ritentate=0,
          documenti_confermati=40,
          latenze=Latenze(campioni=40, minimo_ms=..., mediana_ms=...,
                          p95_ms=..., p99_ms=..., massimo_ms=...))
```

`latenze` è `None` — e non un oggetto pieno di zeri — quando nessuna scrittura è riuscita. Un p95 di
zero millisecondi su una corsa in cui tutto è fallito direbbe «velocissimo» dove la verità è «mai
arrivato», ed è il numero più fuorviante che questa applicazione potrebbe stampare. È la regola dei
doppi applicata alle statistiche: **dove non c'è una risposta giusta, si dichiara di non averla**.

## Perché i percentili, e non la media

La media di una latenza è il numero che nasconde esattamente ciò che una demo di failover esiste per
mostrare. Nove scritture da 1 ms e una da 100 ms fanno una media di 10,9 ms: un valore che non è mai
stato misurato, e che non descrive né il caso normale né quello brutto.

La mediana dice il caso normale. Il p95 e il p99 dicono quanto è brutto il caso brutto. Il massimo
dice quanto è stata brutta la volta peggiore, che durante un failover è **il** numero.

## «p95» da solo non è un numero

Qui comincia la parte che non è ovvia, e che il progetto ha misurato invece di assumere.

Esistono almeno tre modi di calcolare il novantacinquesimo percentile di un campione, e sullo stesso
campione danno risultati diversi. Il campione della misura [M-009](Sources.md#m-009) è costruito
apposta con un gradino — 95 latenze da 1 ms, poi 50, 60, 70, 80 e 900 ms:

| Metodo | p95 | È un valore osservato? |
|---|---|---|
| rango più vicino (quello di `mongolab`) | **1,0** | sì |
| `statistics.quantiles(..., method='inclusive')[94]` | 3,45 | no |
| `statistics.quantiles(..., method='exclusive')[94]` | 47,55 | no |
| *(la media, per confronto)* | 12,55 | no |

Quarantasette volte l'uno dall'altro, e **nessuno dei tre sbaglia**: stanno rispondendo a tre
domande diverse. Le due forme di `quantiles` stimano un quantile della **popolazione** a partire da
un campione, e per farlo interpolano — la documentazione lo dice esplicitamente: «The cut points are
linearly interpolated from the two nearest data points. For example, if a cut point falls one-third
of the distance between two sample values, 100 and 112, the cut-point will evaluate to 104»
([A-009](Sources.md#a-009)).

`mongolab` non stima una popolazione: riferisce le latenze che ha misurato. Per quello serve un
valore che sia stato osservato, e il metodo giusto è il **rango più vicino**: con `n` campioni
ordinati, il quantile `q` è il valore in posizione `ceil(q · n)`.

```python
ordinati = sorted(campioni)
rango = max(1, math.ceil(quantile * len(ordinati)))
return ordinati[rango - 1]
```

## La mediana è lo stesso percentile

Per coerenza, anche la mediana passa da lì: è il quantile 0,5. La conseguenza è che la mediana di
`[10, 20]` vale **10** e non 15, che sorprende chi si aspetta `statistics.median`.

Non è un'invenzione locale. La documentazione di Python descrive entrambe le forme e dice a che cosa
serve la seconda: «When the number of data points is even, the median is interpolated by taking the
average of the two middle values», e poco sotto «Use the low median when your data are discrete and
you prefer the median to be an actual data point rather than interpolated»
([A-008](Sources.md#a-008)). Il quantile 0,5 per rango più vicino **è** `statistics.median_low`, e
non per somiglianza: verificato su ventimila campioni casuali, zero divergenze
([M-009](Sources.md#m-009)).

Perché allora non chiamare direttamente `median_low`? Perché la mediana qui non è un caso a parte: è
un quantile fra gli altri, e due definizioni diverse dentro lo stesso riquadro di riepilogo sarebbero
una trappola per chi legge i numeri.

## Il confine del metodo, dichiarato

Il rango più vicino ha un confine, e la misura lo mostra: nel campione della tabella il p95 vale
**1,0**, cioè non racconta niente della coda — che pure c'è, e arriva a 900 ms.

Non è un difetto, è la definizione: «il più piccolo valore osservato sotto il quale sta almeno il
95 % del campione». Con 95 valori su 100 identici, quella risposta sta in cima al pianerottolo. Nello
stesso campione è il p99 a mostrare la coda (80,0) e il massimo a dirla tutta (900,0).

È la ragione per cui il riepilogo porta **sei** numeri e non uno. Un singolo indicatore di latenza,
qualunque sia, è un modo di non guardare.

## Un dettaglio di aritmetica, verificato invece che sperato

`ceil` applicato a un prodotto in virgola mobile è la combinazione in cui un errore di un ulp diventa
un rango sbagliato di uno, e quindi un valore diverso. Poteva restare un dubbio; è diventata una
misura: per i quantili 0,5 / 0,9 / 0,95 / 0,99 / 0,999 e per campioni da 1 a 200 000 elementi, il
rango in virgola mobile e quello calcolato con l'aritmetica esatta di `Fraction` coincidono sempre
([M-008](Sources.md#m-008)).

La riserva è scritta lì: è una verifica esaustiva **su un intervallo**, non una dimostrazione. Fuori
da quell'intervallo la difesa giusta non sarebbe misurare di nuovo, ma calcolare il rango in
aritmetica intera.

## I tentativi: perché una politica nostra se il driver ne ha una

PyMongo ritenta già le scritture idempotenti da sé, con `retryWrites`. La politica di
`WorkloadRunner` non la sostituisce: esiste per **raccontare** i tentativi, cioè per rendere visibile
in scena ciò che il driver di solito fa in silenzio. Il §6.4 del design mostra `retryWrites` acceso e
spento, e la differenza si vede solo se qualcuno la narra.

```python
PoliticaTentativi(tentativi_massimi=3, attesa_iniziale_ms=50.0,
                  fattore=2.0, attesa_massima_ms=1000.0)
```

`tentativi_massimi=3` vuol dire **una scrittura e due repliche**, non tre repliche: è il tipo di
ambiguità che si paga con un fuori-di-uno, e per questo il campo si chiama così e la prova lo fissa.

L'attesa cresce per raddoppio fino a un tetto, e **senza jitter**. Il jitter è la scelta giusta
quando molti client ritentano insieme contro lo stesso server, perché ne sfasa le ondate; qui
renderebbe le prove non deterministiche proprio dove servono esatte, e la difesa vera contro le
ondate resta quella del driver.

### La sequenza, e dove smette

```
WriteFailed  →  RetryAttempted  →  WriteFailed  →  RetryAttempted  →  WriteFailed
      tentativo 1                        tentativo 2                     tentativo 3
```

L'ultimo evento di una resa è un `WriteFailed`, **non** un `RetryAttempted`: un ritentativo annunciato
e mai eseguito sarebbe una cronaca falsa. La prova che lo fissa si chiama
`test_l_ultimo_evento_di_una_resa_e_il_fallimento_non_il_tentativo`, e non è pedanteria: togliendo il
`return` che ferma il ciclo, cinque prove falliscono insieme ([M-010](Sources.md#m-010)).

`RetryAttempted.tentativo` numera **la prova che sta per essere fatta** — il primo ritentativo porta
`tentativo=2`. Si legge bene in una TUI («tentativo 2 fra 100 ms») ed è l'unica numerazione in cui il
numero e l'attesa che lo accompagna parlano dello stesso evento futuro.

### Che cosa si cattura, e che cosa no

Il blocco cattura `Exception`, non un tipo del driver. Il dominio non sa che esiste PyMongo, e per
questo strato **qualunque** errore di `insert_many` è un fallimento di scrittura da riportare e
ritentare. Il tipo preciso non si perde: diventa il testo di `tipo_errore`, che è quanto serve perché
la cronaca dica «AutoReconnect» durante un failover senza che nessuno qui dentro conosca quella
classe.

### Le latenze dei fallimenti non entrano nel campione

Un `WriteFailed` non produce `LatencySampled`. La durata di un fallimento misura quanto ci ha messo
il driver ad arrendersi, non quanto costa una scrittura: mescolarle sposterebbe i percentili in un
modo che nessuno saprebbe più interpretare — e li sposterebbe **verso il basso** proprio nel momento
in cui il cluster sta peggio, perché un rifiuto immediato è velocissimo.

## La concorrenza: un solo punto di sincronizzazione

Il §6.3 del design lo dice in una riga: i worker non toccano la TUI, pubblicano su una `queue.Queue`
che il ciclo di `Live` drena. `WorkloadRunner` applica la stessa disciplina un livello più in basso:
**i worker non toccano il sink**.

```
worker 1 ─┐
worker 2 ─┼──►  queue.Queue  ──►  thread chiamante  ──►  sink.emit(...)
worker 3 ─┘
```

La coda è lo strumento giusto perché si occupa dei lucchetti al posto nostro: «It is especially
useful in threaded programming when information must be exchanged safely between multiple threads.
The `Queue` class in this module implements all the required locking semantics»
([A-010](Sources.md#a-010)). Nessun `Lock` nel codice dell'applicazione, e nessuno nel sink.

L'invariante è verificabile perché `RecordingSink` ricorda **da quale thread** è stato chiamato:

```python
def test_solo_il_thread_chiamante_tocca_il_sink() -> None:
    ...
    assert sink.chiamanti == {threading.get_ident()}
```

Facendo emettere i worker direttamente, quella prova fallisce mostrando due identificatori diversi
([M-010](Sources.md#m-010)).

### La sentinella, e perché sta in un `finally`

Il ciclo di drenaggio deve sapere quando fermarsi. Non lo chiede ai futuri e non usa un timeout: ogni
worker, **qualunque cosa accada**, mette in coda un `None` come ultimo gesto, e il chiamante conta i
`None`.

```python
finally:
    coda.put(None)
```

I timeout dentro un ciclo di consumo sono la via che porta a una prova che fallisce una volta su
cento su una macchina carica. Il `finally`, invece, è ciò che rende il ciclo terminante anche quando
un worker muore per un motivo che non c'entra con le scritture — e allora l'errore arriva al
chiamante attraverso `future.result()`, invece di essere inghiottito.

**Che cosa succede senza.** Spostando il `put` fuori dal `finally`, la suite non fallisce: **si
pianta**. Il worker muore prima di segnalare la fine del turno, il chiamante aspetta una sentinella
che non arriverà, e la corsa resta ferma finché qualcuno non la uccide da fuori. Nessun `FAILED`,
nessun messaggio, nessun punto del codice indicato ([M-010](Sources.md#m-010)). È l'esito che la
[nota di metodo 153](../../docs/registro-operativo-sviluppo.md) ha aggiunto ai tre della 144.

### Che cosa le prove non asseriscono

L'ordine fra worker diversi. Non è garantito da niente, e pretenderlo produrrebbe una prova che passa
quasi sempre — il tipo peggiore. Le prove asseriscono ciò che il §6.3 promette davvero: che nessun
evento si perda, che il lavoro non si duplichi (gli indici generati sono esattamente `0..N-1`), e che
a chiamare `emit` sia un thread solo.

## Il gancio per `maxPoolSize`, e la misura che non c'è

`scrittori` è il numero di thread che scrivono insieme. È **il parametro che il Task 16 farà salire
sopra `maxPoolSize`** per mostrare la saturazione del connection pool di PyMongo, che il design
dichiara materiale didattico.

Qui la saturazione non si misura e non si può: contro `InMemoryStore` non c'è nessun pool da saturare,
e una prova che pretendesse di mostrarla misurerebbe il doppio invece del driver. Questa riga è il
gancio, non la misura — e la distinzione è scritta perché il prossimo lettore non la cerchi dove non
c'è.

## Che cosa hanno insegnato i doppi, qui

Il Task 4 aveva lasciato un debito dichiarato: **nessun doppio sapeva rompersi**, e una politica di
tentativi non è provabile contro un archivio che riesce sempre. La regola del repository è che la
capacità si aggiunge insieme alla prova che ne ha bisogno — mai semplificando la prova — ed è quello
che è successo.

Sono nati due archivi, e nessuno dei due riscrive `InMemoryStore`: lo **avvolgono**.

- **`ArchivioCheRompe`** rifiuta le scritture e lascia passare le letture. Le letture devono
  funzionare durante il guasto, altrimenti non c'è la scena — «confermate contro ritrovate» è
  proprio il numero del Blocco 2.
- **`ArchivioLento`** fa costare tempo a ogni chiamata, facendo avanzare `FakeClock` **dentro**
  l'operazione. Senza, ogni scrittura durerebbe zero millisecondi e la prova sulla latenza
  verificherebbe l'immobilità dell'orologio invece della misura.

Il secondo prende `FakeClock` e non `Clock`, ed è deliberato: `avanza` non sta nella porta e non deve
starci. Il codice di produzione può solo **chiedere** di dormire; a far passare il tempo mentre lavora
è il mondo, e in una prova il mondo è quel doppio. È la stessa distinzione che tiene pulita
`FakeClock.attese`, dove si legge il backoff e nient'altro.

Entrambi annotano l'archivio avvolto con la **porta**, non con `InMemoryStore`. Costa una riga e
compra due cose: mypy verifica al punto di costruzione che l'archivio avvolto rispetti
`DocumentStore`, e i doppi si compongono — `ArchivioLento(ArchivioCheRompe(...))` è un archivio lento
**e** guasto senza che nessuno dei due sappia dell'altro.

## Un tipo perso in un aiutante di prova

Un ultimo dettaglio, perché è il genere di cosa che si scopre solo eseguendo. Le prove filtrano gli
eventi per specie con un aiutante:

```python
def _specie[E: Evento](eventi: list[Evento], tipo: type[E]) -> list[E]:
```

Nella prima stesura il tipo di ritorno era `list[Evento]`, e `make app-check` ha bocciato **dieci**
asserzioni in un colpo: `"Evento" has no attribute "durata_ms"`. A runtime sarebbero passate tutte.

La lezione sta nel verso: un aiutante di prova che perde il tipo spegne il controllo proprio dove le
asserzioni sono più specifiche, e lo spegne in silenzio. Il filtro sa quale specie ha cercato — con
un parametro di tipo, glielo si fa dire.

---

**Torna a:** [README.md](README.md) per l'indice, oppure
[05-tipi-prove-e-guardie.md](05-tipi-prove-e-guardie.md) per chi controlla che tutto questo resti
vero.

**Fonti:** [A-008](Sources.md#a-008), [A-009](Sources.md#a-009), [A-010](Sources.md#a-010),
[M-008](Sources.md#m-008), [M-009](Sources.md#m-009), [M-010](Sources.md#m-010).
**Decisioni:** [ADR-0007](../../docs/Decision.md#adr-0007),
[ADR-0019](../../docs/Decision.md#adr-0019).
