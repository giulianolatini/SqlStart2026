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

Quattro scene, tredici kilobyte in tutto, misurate sullo stack `docker/02-replicaset` con i tre
membri sani prima di ciascuna ([V-045](../../Sources.md#v-045)).

| # | File | Che cosa mostra | Durata | Il numero che porta | Momento |
|---:|---|---|---:|---|---|
| 1 | [`01-smoke-replica-set.cast`](01-smoke-replica-set.cast) | la prova completa dello stack: keyfile, autenticazione, replica, log | 16,9 s | `Superati: 42 · Errori: 0` | apertura del blocco sul replica set — «funziona, e lo dimostro» |
| 2 | [`02-failover-docker-kill.cast`](02-failover-docker-kill.cast) | `docker kill` sul primario: nessun preavviso, il timeout scade | 17,2 s | elezione in **8617 ms**; `exited`, `RestartCount=0`, `ExitCode=137` | la scena principale del blocco |
| 3 | [`03-failover-terminazione-pulita.cast`](03-failover-terminazione-pulita.cast) | il primario esce da sé con `shutdownServer()`: cede il ruolo e lo dice | 25,1 s | elezione in **1039 ms**; `running`, `RestartCount=1`, `ExitCode=0` | subito dopo la 2, come confronto |
| 4 | [`04-maggioranza-persa.cast`](04-maggioranza-persa.cast) | due membri su tre giù: il superstite è vivo, sano, e smette di scrivere | 15,6 s | `SECONDARY` dopo **8634 ms** | la risposta a «e a quanti guasti regge?» |

Le scene 2 e 3 vanno **una dopo l'altra**, perché il punto non è nessuna delle due: è che il gesto
brutale costa dieci secondi e quello educato uno, cioè il contrario di quello che il pubblico si
aspetta ([ADR-0034](../../Decision.md#adr-0034), [ADR-0044](../../Decision.md#adr-0044)).

### Come si riproducono

Senza installare niente, con i tempi originali:

```bash
python3 tools/registra-terminale.py --riproduci \
  docs/05-talk/registrazioni/02-failover-docker-kill.cast
```

I tempi si rispettano di proposito: un failover che scorre tutto insieme non racconta niente,
perché la scena *è* l'attesa. Per le prove c'è `--velocita 10`, che in sala non si usa.

Chi ha `asciinema` installato può usare quello — il formato è il suo, versione 2 — ma non serve, ed
è deliberato: un piano B che richiede un `brew install` non è un piano B.

Una precisazione da conoscere prima di provarci in sala: la riproduzione ha bisogno di un terminale
vero. Dentro una pipe o in un editor le sequenze di colore diventano caratteri e lo schermo si
sporca.

### Come si rifanno

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

**I numeri di una registrazione non sono la misura.** Ogni scena è **una** esecuzione, girata di
seguito alle altre. Le misure del branch stanno in [V-029](../../Sources.md#v-029) e
[V-031](../../Sources.md#v-031), che hanno tre giri per scena e le mediane. La scena 3 qui sopra ne
è la prova: 1039 ms, contro i 574, 480 e 486 di V-029 — stesso strumento, stesso metodo, il doppio
del tempo, perché la macchina aveva appena fatto altre tre scene. Il singolo numero balla, il
rapporto fra le due scene no.

---

<a id="filmati"></a>
## I filmati, che ancora non ci sono

**`make preflight` avvisa, ed è giusto così.** Il controllo cerca file `.mp4` in
`~/SqlStart2026-registrazioni` (impostabile con `DEMO_VIDEOS_DIR`), e quella cartella è vuota. Non
ci è stato messo un file finto per far tacere l'avviso: il controllo verifica una cosa che manca
davvero, e dal **18 settembre 2026** diventa un errore bloccante. Zittirlo adesso significherebbe
scoprire il buco la mattina del talk, che è precisamente lo scenario per cui il controllo esiste.

I quattro filmati da girare, in ordine di importanza:

| # | Che cosa filmare | Corrisponde a | Durata attesa | Perché serve |
|---:|---|---|---:|---|
| 1 | il failover con `docker kill`, dal vivo e con la voce | scena 2 qui sopra | ~2 min | è la scena del talk. Se salta questa, salta il blocco |
| 2 | le due varianti a confronto, `kill` e terminazione | scene 2 e 3 | ~3 min | il confronto è il punto, non le due scene separate |
| 3 | la maggioranza persa | scena 4 | ~2 min | risponde alla domanda che il pubblico fa sempre |
| 4 | `make up-02` da zero, con la rete disattivata | — | ~4 min | dimostra che il lab è offline davvero, e apre il talk |

Procedura, quando si gira:

1. `./tools/reset-demo.sh 02`, e si aspetta l'impronta del dataset.
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
- **Non contiene le scene degli altri stack.** Lo standalone e lo sharded cluster hanno le proprie,
  e arrivano con i rispettivi branch. Le quattro qui sono di `feature/02`.
- **Le registrazioni non sostituiscono i filmati.** Sono due coperture diverse e il criterio 8 di
  completamento del branch chiede entrambe: oggi è soddisfatto a metà, e la metà mancante è scritta
  qui sopra invece che nascosta.

---

**Decisioni correlate:** [ADR-0016](../../Decision.md#adr-0016) (i filmati e la copia locale
obbligatoria), [ADR-0050](../../Decision.md#adr-0050) (il formato delle registrazioni di terminale,
e perché lo strumento sta nel repository), [ADR-0034](../../Decision.md#adr-0034) (`docker kill` non
è un guasto), [ADR-0044](../../Decision.md#adr-0044) (i due bersagli del failover),
[ADR-0045](../../Decision.md#adr-0045) (la maggioranza persa),
[ADR-0015](../../Decision.md#adr-0015) (il documento unico del talk).

**Fonti:** [V-029](../../Sources.md#v-029), [V-031](../../Sources.md#v-031),
[V-045](../../Sources.md#v-045)
