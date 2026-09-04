# La documentazione di `mongolab`

Questa cartella spiega **come è fatta l'applicazione del lab e perché**. Sta accanto al codice, non
in `docs/`, perché parla di scelte che si capiscono avendo i sorgenti sotto gli occhi: un file che si
apre nella finestra accanto a quello che descrive.

`mongolab` è l'applicazione console che, durante il talk, mostra dall'interno che cosa succede a un
client MongoDB mentre il cluster sotto di lui cambia forma. È il pezzo che trasforma un failover da
affermazione in **cronaca in diretta**.

## Le pagine, nell'ordine in cui conviene leggerle

| # | Pagina | Risponde a |
|---|---|---|
| 1 | [01-architettura-esagonale.md](01-architettura-esagonale.md) | perché quattro cartelle invece di un file solo |
| 2 | [02-porte-e-doppi.md](02-porte-e-doppi.md) | che cos'è una porta, e perché non è una classe astratta |
| 3 | [03-eventi-immutabili.md](03-eventi-immutabili.md) | perché un evento è congelato, e perché `frozen` da solo non basta |
| 4 | [04-eventi-del-driver-e-concorrenza.md](04-eventi-del-driver-e-concorrenza.md) | che cosa vede il client durante un failover, e perché il listener deve tacere e uscire |
| 5 | [05-tipi-prove-e-guardie.md](05-tipi-prove-e-guardie.md) | chi controlla che tutto questo resti vero |
| 6 | [06-carico-tentativi-e-latenze.md](06-carico-tentativi-e-latenze.md) | perché i percentili e non la media, e perché i worker non toccano il sink |
| 7 | [07-topologia-failover-e-i-due-numeri.md](07-topologia-failover-e-i-due-numeri.md) | come si riconosce un failover, e dove si calcolano durata dell'interruzione e scritture perse |
| 8 | [08-il-ponte-sdam-e-i-thread-del-driver.md](08-il-ponte-sdam-e-i-thread-del-driver.md) | chi chiama i listener, da quale thread, e quanto costa scrivere una riga di troppo dentro un callback |
| 9 | [09-adattatori-veri-e-contratto-condiviso.md](09-adattatori-veri-e-contratto-condiviso.md) | che cosa si rompe quando i doppi incontrano MongoDB vero, e il contratto che li tiene onesti |
| 10 | [10-processi-esterni-e-il-verdetto-che-manca.md](10-processi-esterni-e-il-verdetto-che-manca.md) | che cosa cambia quando l'adattatore lancia un processo invece di chiamare una libreria, e dove mettere la password |
| 11 | [11-tre-rese-e-un-solo-thread-che-disegna.md](11-tre-rese-e-un-solo-thread-che-disegna.md) | tre modi di guardare lo stesso flusso di eventi, il budget di sala, e una promessa architetturale che si è scoperta falsa mentre la si manteneva |
| 12 | [12-la-radice-di-composizione-e-la-prima-esecuzione-vera.md](12-la-radice-di-composizione-e-la-prima-esecuzione-vera.md) | chi conosce le classi concrete, e che cosa si scopre la prima volta che si esegue davvero contro un MongoDB acceso |
| 13 | [13-il-container-sulla-rete-e-la-scoperta-che-si-vede.md](13-il-container-sulla-rete-e-la-scoperta-che-si-vede.md) | perché lo stesso stack ha due indirizzi, e come si dimostra che un client non parla con l'indirizzo che gli hai dato |
| 14 | [14-la-scena-del-failover-e-i-due-numeri.md](14-la-scena-del-failover-e-i-due-numeri.md) | la sesta porta nata da un'impossibilità, il decimo evento, e i due numeri che dicono se il failover è avvenuto davvero |
| 15 | [15-il-backup-a-caldo-e-la-finestra-che-si-misura.md](15-il-backup-a-caldo-e-la-finestra-che-si-misura.md) | perché la finestra di una misura non si sceglie a tavolino, dove girano gli strumenti che nell'immagine non ci sono, e perché il restore scrive accanto e mai sopra |
| 16 | [16-la-chiave-di-shard-e-lo-stesso-carico-due-volte.md](16-la-chiave-di-shard-e-lo-stesso-carico-due-volte.md) | perché una sola colonna non dimostra niente, l'evento del design che nessuno emette, e la settima porta che legge un piano senza eseguirlo |

Si leggono in ordine, ma nessuna dipende dalle altre per essere comprensibile. Chi arriva da una
domanda precisa può entrare dal punto giusto.

## Le altre tre

- **[registro-sviluppo-app.md](registro-sviluppo-app.md)** — la cronaca di come l'applicazione è
  stata costruita, task per task, comprese le volte in cui la scoperta ha contraddetto il piano.
  È la pagina da leggere per capire **il processo**, non il risultato.
- **[decisioni-che-vincolano-app.md](decisioni-che-vincolano-app.md)** — la mappa delle decisioni
  architetturali del repository che mordono su questo codice: che cosa impongono, dove si vedono,
  se sono già applicate.
- **[Sources.md](Sources.md)** — le fonti esterne consultate (`A-0NN`) e le misure fatte in locale
  (`M-0NN`), con verdetto e riserve.

## Il patto di lettura

Queste pagine seguono le regole del repository, e vale la pena conoscerle prima di fidarsi di una
riga:

**Ogni affermazione tecnica porta la sua fonte.** `A-0NN` e `M-0NN` rimandano a
[Sources.md](Sources.md); `S-0NN`, `V-0NN` e `C-0NN` al registro canonico
[`docs/Sources.md`](../../docs/Sources.md); `ADR-0NNN` a
[`docs/Decision.md`](../../docs/Decision.md).

**Ciò che è stato misurato qui è distinto da ciò che è stato letto altrove.** Una voce `M-` è un
esperimento eseguito su questo ambiente, con il suo output riportato. Una voce `A-` è una pagina di
documentazione ufficiale, con la data in cui è stata consultata. **Dove le due non concordano, la
riserva è scritta**, e la misura non zittisce la fonte né viceversa.

**Le lacune sono dichiarate, non riempite.** Quando la documentazione di uno strumento tace su
qualcosa che serviva sapere, la pagina lo dice invece di indovinare. Il caso più notevole è la
documentazione di Rich, che non nomina mai i thread: il progetto non se n'è appoggiato in nessuna
delle due direzioni, e ha cambiato il disegno finché la domanda è diventata irrilevante.

**Dove una pagina descrive il futuro, lo dichiara in testa.** Il codice arriva in diciotto task, e
alcune di queste pagine descrivono principi già decisi il cui codice non è ancora scritto. Chi legge
deve poterlo sapere senza andare a controllare.

## Rapporto con `docs/`

Il repository ha una documentazione canonica in [`docs/`](../../docs/README.md), che copre il talk, gli stack
Compose, le decisioni, le fonti e il registro operativo. **Quella resta la sede normativa.** Queste
pagine non la contraddicono e non la duplicano: dove serve una decisione o una fonte del repository,
la **citano** invece di ricopiarla, perché un contenuto duplicato è un contenuto che prima o poi
diverge.

Le pagine divulgative promesse dal piano — `docs/06-sviluppo/architettura-app.md` e
`docs/06-sviluppo/tdd-e-doppi.md`, al Task 17 — nasceranno **rimandando qui**, non ripetendo. Il loro
mestiere è diverso: raccontano l'applicazione a chi ha visto il talk e non aprirà mai `app/src/`.
Queste pagine parlano a chi il codice lo apre.

Perché due `Sources.md` e non uno solo è spiegato nell'intestazione di [Sources.md](Sources.md): in
breve, il controllo automatico delle citazioni del repository considera **orfana** una fonte che
nessun ADR cita, e le fonti di linguaggio e strumenti non sono citate da nessun ADR né devono
esserlo. Aprire la sede che mancava era la risposta giusta; aggirare il controllo no.

## Verificare che questa documentazione sia sana

```sh
make docs-check     # collegamenti e ancore, anche di queste pagine
make app-test       # le prove unitarie citate qui
make app-check      # mypy --strict
```

Il controllo dei collegamenti percorre anche `app/docs`: ogni rimando a un ADR o a una fonte del
registro canonico viene verificato, ancora compresa. Un `#adr-0019` scritto male è un errore che
fallisce, non un rimando che porta in cima alla pagina.
