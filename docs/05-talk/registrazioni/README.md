# Registrazioni di riserva

Questa cartella è il piano B del talk. Serve quando la demo dal vivo non parte, quando la sala non
ha rete, quando un container decide di fare il difficile davanti a cento persone — e serve che
funzioni **senza rete e senza installare niente** ([ADR-0016](../../Decision.md#adr-0016),
[ADR-0050](../../Decision.md#adr-0050)).

Le registrazioni sono di due specie, e non sono intercambiabili.

| | che cos'è | dove sta | chi la produce |
|---|---|---|---|
| **Filmato** (`.mp4`) | lo schermo e la voce di chi parla | canale YouTube del relatore, **più** copia locale in `~/SqlStart2026-registrazioni` | il relatore |
| **Registrazione di terminale** (`.cast`) | il tracciato di ciò che il terminale ha fatto, con i tempi | qui, dentro il repository | si produce eseguendo |

Un filmato mostra una persona che spiega; una registrazione di terminale mostra una macchina che
lavora. In sala servono tutt'e due, per motivi diversi: il filmato copre il caso «la demo non
parte», la registrazione di terminale copre il caso «la demo parte ma stiamo finendo il tempo».

---

<a id="registrazioni-di-terminale"></a>
## Le registrazioni di terminale, che ci sono

Nove scene, trentun kilobyte in tutto: quattro del Blocco 2 — il replica set — e cinque del
Blocco 3, lo sharded cluster. Nessuna è montata: ognuna è **una** esecuzione intera, con i tempi
che ha avuto.

### Blocco 2 — il replica set

Misurate sullo stack `docker/02-replicaset`, con i tre membri sani prima di ciascuna
([V-045](../../Sources.md#v-045)).

| # | File | Che cosa mostra | Durata | Il numero che porta | Momento |
|---:|---|---|---:|---|---|
| 1 | [`01-smoke-replica-set.cast`](01-smoke-replica-set.cast) | la prova completa dello stack: keyfile, autenticazione, replica, log | 16,9 s | `Superati: 42 · Errori: 0` | apertura del blocco sul replica set — «funziona, e lo dimostro» |
| 2 | [`02-failover-docker-kill.cast`](02-failover-docker-kill.cast) | `docker kill` sul primario: nessun preavviso, il timeout scade | 17,2 s | elezione in **8617 ms**; `exited`, `RestartCount=0`, `ExitCode=137` | la scena principale del blocco |
| 3 | [`03-failover-terminazione-pulita.cast`](03-failover-terminazione-pulita.cast) | il primario esce da sé con `shutdownServer()`: cede il ruolo e lo dice | 25,1 s | elezione in **1039 ms**; `running`, `RestartCount=1`, `ExitCode=0` | subito dopo la 2, come confronto |
| 4 | [`04-maggioranza-persa.cast`](04-maggioranza-persa.cast) | due membri su tre giù: il superstite è vivo, sano, e smette di scrivere | 15,6 s | `SECONDARY` dopo **8634 ms** | la risposta a «e a quanti guasti regge?» |

Le scene 2 e 3 vanno **una dopo l'altra**, perché il punto non è nessuna delle due: è che il gesto
brutale costa dieci secondi e quello educato uno, cioè il contrario di quello che il pubblico si
aspetta ([ADR-0034](../../Decision.md#adr-0034), [ADR-0044](../../Decision.md#adr-0044)).

### Blocco 3 — lo sharded cluster

Misurate sullo stack `docker/03-sharded` ([V-068](../../Sources.md#v-068)). Le prime quattro nel
profilo `palco` — un membro per shard, quello che entra in un portatile; l'ultima nel profilo
`completo`, tre membri per insieme ([ADR-0010](../../Decision.md#adr-0010)).

| # | File | Che cosa mostra | Durata | Il numero che porta | Momento |
|---:|---|---|---:|---|---|
| 5 | [`05-avvio-sharded.cast`](05-avvio-sharded.cast) | undici servizi che si accendono nell'ordine giusto: keyfile, config server, i due shard, il router, `addShard`, i dati | 22,9 s | la catena finisce con `Container sh-up-03 Healthy` | apertura del blocco — «un comando, e c'è un cluster» |
| 6 | [`06-stato-sharded.cast`](06-stato-sharded.cast) | `sh.status()` per intero, e sotto le quattro righe che contano davvero | 6,5 s | 2 shard · `lab.ordini` in **4 chunk**, due per shard · balancer abilitato · 1 router | subito dopo l'avvio: «che cosa mi sta dicendo tutto questo?» |
| 7 | [`07-distribuzione-sharded.cast`](07-distribuzione-sharded.cast) | gli stessi documenti contati dal router e poi shard per shard | 4,0 s | **9860 + 10140 = 20000**, cioè 49,3 % e 50,7 % | il cuore del blocco: partizionata, non copiata |
| 8 | [`08-guasto-shard-palco.cast`](08-guasto-shard-palco.cast) | si ferma l'unico membro di uno shard: metà cluster risponde, l'altra metà aspetta | 40,1 s | lettura sullo shard vivo in **1 s**; `FailedToSatisfyReadPreference` dopo **15 s** e **16 s**; ritorno in **3 s** | la risposta a «e se ne cade uno?» |
| 9 | [`09-failover-membro-shard.cast`](09-failover-membro-shard.cast) | lo stesso guasto con tre membri per shard: lo shard elegge, e il router se ne accorge da solo | 12,3 s | totale ancora **20000**, in **0 s**; primario da `shard1a` a `shard1b`; ritorno in **2 s** | subito dopo la 8, come confronto |

Le scene 8 e 9 sono **lo stesso comando** — `make guasto-03` — eseguito in due profili diversi, e
vanno una dopo l'altra per la stessa ragione per cui vanno insieme la 2 e la 3: il punto non è
nessuna delle due, è la differenza fra le due. Con un membro per shard il router aspetta quindici
secondi e poi dichiara che per `shard1rs` non trova un primario; con tre membri lo stesso guasto
quasi non si vede, perché dentro lo shard l'elezione è già avvenuta. La ridondanza sta **dentro**
ogni shard, e fra shard non c'è: nessun altro nodo tiene una copia di ciò che teneva quello caduto.

La scena 8 mostra anche il limite del profilo `palco`, e lo mostra senza bisogno di dirlo: un membro
per shard sta in un portatile e non regge un guasto. Dal palco è più onesto farlo vedere che
nasconderlo — e la 9 esiste per aggiungere che la differenza è di configurazione, non di prodotto.

### Come si riproducono

Senza installare niente, con i tempi originali:

```bash
python3 tools/registra-terminale.py --riproduci \
  docs/05-talk/registrazioni/02-failover-docker-kill.cast
```

I tempi si rispettano di proposito: un failover che scorre tutto insieme non racconta niente,
perché la scena *è* l'attesa. Vale doppio per la scena 8, dove i quindici secondi prima
dell'errore **sono** la risposta alla domanda. Per le prove c'è `--velocita 10`, che in sala non si
usa.

Chi ha `asciinema` installato può usare quello — il formato è il suo, versione 2 — ma non serve, ed
è deliberato: un piano B che richiede un `brew install` non è un piano B.

Una precisazione da conoscere prima di provarci in sala: la riproduzione ha bisogno di un terminale
vero. Dentro una pipe o in un editor le sequenze di colore diventano caratteri e lo schermo si
sporca.

### Come si rifanno

#### Il replica set

Prima di ogni scena i tre membri devono essere sani, altrimenti si registra un'altra cosa:

```bash
./tools/reset-demo.sh 02          # e si aspetta che dica «riportato allo stato di partenza»

python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/02-failover-docker-kill.cast \
  --titolo "feature/02 — Failover: docker kill sul primario (~10 s)" \
  -- make failover-02
```

Poi di nuovo `reset-demo.sh 02` prima della successiva. Le quattro scene sono state girate in questo
ordine — smoke, `docker kill`, terminazione pulita, maggioranza persa — con un ripristino fra
ciascuna.

#### Lo sharded cluster

L'avvio si registra da fermo, e con il renderer testuale di Compose:

```bash
make reset-03                     # ferma lo stack e cancella i dati: l'avvio deve creare i volumi

COMPOSE_PROGRESS=plain python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/05-avvio-sharded.cast \
  --titolo "feature/03 — Lo sharded cluster si accende con un comando (profilo palco)" \
  -- make up-03
```

`COMPOSE_PROGRESS=plain` non è un dettaglio estetico. Il renderer predefinito ridisegna una tabella
animata decine di volte al secondo: lo stesso `up`, sullo stesso stack e nello stesso stato, pesa
**134 861 byte in 205 eventi** con l'animazione e **3 050 byte in 28 eventi** senza — quarantaquattro
volte meno, e per giunta leggibile, perché in `plain` ogni container scrive la propria riga e
l'ordine della catena si vede scorrere ([V-068](../../Sources.md#v-068)).

Le tre scene successive si registrano a cluster acceso, una dopo l'altra e senza ripristini in
mezzo: non toccano i dati, e `make guasto-03` rimette in piedi da sé il nodo che ha fermato.

```bash
python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/06-stato-sharded.cast \
  --titolo "feature/03 — sh.status(): il cluster come si presenta" \
  -- make stato-03

python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/07-distribuzione-sharded.cast \
  --titolo "feature/03 — Dove stanno davvero i ventimila documenti" \
  -- make distribuzione-03

python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/08-guasto-shard-palco.cast \
  --titolo "feature/03 — Cade uno shard: metà cluster risponde, l'altra aspetta (profilo palco)" \
  -- make guasto-03
```

La nona chiede il profilo `completo`, che non è solo una variabile: in `docker/03-sharded/.env` vanno
scambiate le tre righe `MEMBRI_*`, commentando quelle a un membro e togliendo il commento a quelle a
tre. Poi `make reset-03`, `PROFILO=completo make up-03`, e infine:

```bash
python3 tools/registra-terminale.py \
  docs/05-talk/registrazioni/09-failover-membro-shard.cast \
  --titolo "feature/03 — Cade il primario di uno shard, e lo shard elegge (profilo completo)" \
  -- make guasto-03 PROFILO=completo
```

Finito, il `.env` va rimesso com'era. Quel file non sta nel repository, non c'è controllo che se ne
accorga, e chi lo lascia a tre membri si ritrova il profilo `palco` che non parte più.

#### E poi si riproduce, prima di dichiararla buona

Una registrazione non è buona perché il comando è finito bene: è buona se, **riprodotta**, mostra
quello che deve mostrare. Ognuna delle nove è stata riaperta con `--riproduci` per intero prima di
entrare in questa pagina ([ADR-0055](../../Decision.md#adr-0055)). È lì che si scopre quello che
durante l'esecuzione non si vede — una scena che *afferma* un'elezione invece di mostrarla, un
titolo che dice un profilo e un contenuto che ne dice un altro.

Per le cinque dello sharded il controllo è stato anche automatico: la riproduzione è stata eseguita
dentro uno pseudo-terminale e il testo raccolto confrontato **byte per byte** con l'originale. Tutte
e cinque coincidono. Un dettaglio da sapere se lo si rifà: lo pseudo-terminale traduce ogni `\n` in
`\r\n`, quindi un `\r\n` registrato torna indietro come `\r\r\n` e va normalizzato prima di
confrontare — altrimenti il confronto fallisce su una differenza che non esiste.

**I numeri di una registrazione non sono la misura.** Ogni scena è **una** esecuzione, girata di
seguito alle altre. Le misure del branch stanno in [V-029](../../Sources.md#v-029) e
[V-031](../../Sources.md#v-031), che hanno tre giri per scena e le mediane. La scena 3 qui sopra ne
è la prova: 1039 ms, contro i 574, 480 e 486 di V-029 — stesso strumento, stesso metodo, il doppio
del tempo, perché la macchina aveva appena fatto altre tre scene. Il singolo numero balla, il
rapporto fra le due scene no. Vale identico per i quindici secondi della scena 8: quello che regge
non è il numero, è che da una parte si aspetta e dall'altra no.

---

<a id="filmati"></a>
## I filmati, che ancora non ci sono

**`make preflight` avvisa, ed è giusto così.** Il controllo cerca file `.mp4` in
`~/SqlStart2026-registrazioni` (impostabile con `DEMO_VIDEOS_DIR`), e quella cartella è vuota. Non
ci è stato messo un file finto per far tacere l'avviso: il controllo verifica una cosa che manca
davvero, e dal **18 settembre 2026** diventa un errore bloccante. Zittirlo adesso significherebbe
scoprire il buco la mattina del talk, che è precisamente lo scenario per cui il controllo esiste.

I filmati da girare — i primi quattro del Blocco 2, gli ultimi due del Blocco 3, in ordine di
importanza dentro ciascun blocco:

| # | Che cosa filmare | Corrisponde a | Durata attesa | Perché serve |
|---:|---|---|---:|---|
| 1 | il failover con `docker kill`, dal vivo e con la voce | scena 2 | ~2 min | è la scena del talk. Se salta questa, salta il blocco |
| 2 | le due varianti a confronto, `kill` e terminazione | scene 2 e 3 | ~3 min | il confronto è il punto, non le due scene separate |
| 3 | la maggioranza persa | scena 4 | ~2 min | risponde alla domanda che il pubblico fa sempre |
| 4 | `make up-02` da zero, con la rete disattivata | — | ~4 min | dimostra che il lab è offline davvero, e apre il talk |
| 5 | il guasto di uno shard nei due profili | scene 8 e 9 | ~3 min | è la scena del Blocco 3, e dal vivo costa due stack e uno scambio di `.env` |
| 6 | il Blocco 3 per intero: avvio, `sh.status()`, distribuzione | scene 5, 6 e 7 | ~4 min | se il cluster non parte in sala non c'è modo di raccontarlo a voce |

Procedura, quando si gira:

1. `./tools/reset-demo.sh 02` — o `03`, secondo il blocco — e si aspetta l'impronta del dataset.
2. Si registra lo schermo — un terminale a 100×30, come le registrazioni di terminale, così le due
   specie di riserva mostrano la stessa cosa.
3. Il file va sul canale YouTube del relatore **e** in `~/SqlStart2026-registrazioni`, con lo stesso
   nome della scena corrispondente e l'estensione `.mp4`.
4. `make preflight`: l'avviso sui filmati diventa `filmati locali disponibili: N`.
5. Il collegamento a YouTube torna in questa pagina, nella colonna che oggi non c'è.

---

## Cosa questa cartella non dice

- **Non contiene la scaletta.** Il documento unico del talk — copione, tempi, piani di ripiego,
  criteri di rinuncia — è `05-talk/runbook-demo.md`, dovuto a `release/1.0`
  ([ADR-0015](../../Decision.md#adr-0015)). Qui c'è solo il materiale di riserva.
- **Non contiene le scene dello standalone.** Il Blocco 1 non ne ha nessuna: `feature/01` è passata
  senza registrarne, e se ne servisse una si gira con lo stesso strumento e finisce qui. Le nove che
  ci sono vengono da `feature/02` e da `feature/03`.
- **Le registrazioni non sostituiscono i filmati, e i due branch lo chiedono in modo diverso.** Il
  criterio 8 di `feature/02` chiedeva entrambe le specie — «almeno una registrazione di riserva
  esiste in locale e `make preflight` non avvisa più» — ed è soddisfatto a metà, con la metà
  mancante scritta qui sopra invece che nascosta. Il criterio 8 di `feature/03` chiede che la
  riserva del Blocco 3 sia «registrata e **riprodotta**», e quello è soddisfatto per intero.

---

**Decisioni correlate:** [ADR-0016](../../Decision.md#adr-0016) (i filmati e la copia locale
obbligatoria), [ADR-0050](../../Decision.md#adr-0050) (il formato delle registrazioni di terminale,
e perché lo strumento sta nel repository), [ADR-0055](../../Decision.md#adr-0055) (una registrazione
si riproduce prima di dichiararla buona), [ADR-0034](../../Decision.md#adr-0034) (`docker kill` non
è un guasto), [ADR-0044](../../Decision.md#adr-0044) (i due bersagli del failover),
[ADR-0045](../../Decision.md#adr-0045) (la maggioranza persa),
[ADR-0010](../../Decision.md#adr-0010) (i due profili dello sharded cluster),
[ADR-0073](../../Decision.md#adr-0073) (una scena di riserva è l'uscita di un comando del
repository), [ADR-0015](../../Decision.md#adr-0015) (il documento unico del talk).

**Fonti:** [V-029](../../Sources.md#v-029), [V-031](../../Sources.md#v-031),
[V-045](../../Sources.md#v-045), [V-068](../../Sources.md#v-068)
