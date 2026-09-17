# I filmati di riserva — che cosa mostra ognuno, e come intitolarlo

Quattordici filmati muti, da mettere dentro le slide. Sono di due tagli:

- **sei montaggi** (`01`…`06`), che sono le scene del talk: uno o più `.cast` uno dietro l'altro,
  pensati per stare su una slide da soli;
- **otto scene singole** (`scena-02`…`scena-09`), utili se una slide deve mostrare **un pezzo solo**
  di un montaggio, o se dal vivo serve accorciare.

Tutti sono **senza audio**, per costruzione: dentro una presentazione una voce registrata litiga
con quella di chi parla. Tredici su quattordici sono fabbricati dalle registrazioni di terminale
con `make filmati` e si rifanno da capo in meno di un minuto; il quarto è girato dal vivo.

> **Due coppie sono lo stesso file, byte per byte.** `01-failover-docker-kill-muto.mp4` è identico
> a `scena-02-failover-docker-kill-muto.mp4`, e `03-maggioranza-persa-muto.mp4` è identico a
> `scena-04-maggioranza-persa-muto.mp4` — quei due montaggi contengono una scena sola. Non metterli
> su due slide diverse pensando che mostrino cose diverse.

---

## In breve

| file | durata | titolo proposto |
|---|---:|---|
| `01-failover-docker-kill-muto.mp4` | 19,2 s | **Il primario muore senza preavviso** |
| `02-failover-i-due-gesti-muto.mp4` | 46,3 s | **Due modi di spegnere un primario, e uno costa otto volte l'altro** |
| `03-maggioranza-persa-muto.mp4` | 17,6 s | **Il superstite è vivo, è sano, e non scrive più** |
| `04-avvio-offline-muto.mp4` | 50,6 s | **Un comando, e il replica set c'è** |
| `05-guasto-shard-nei-due-profili-muto.mp4` | 56,4 s | **Lo stesso guasto, due architetture: quindici secondi contro zero** |
| `06-blocco-3-per-intero-muto.mp4` | 39,3 s | **Uno sharded cluster dentro un portatile** |
| `scena-02-failover-docker-kill-muto.mp4` | 19,2 s | *(identico al filmato 01)* |
| `scena-03-failover-terminazione-pulita-muto.mp4` | 27,1 s | **Il primario si dimette: 1039 millisecondi** |
| `scena-04-maggioranza-persa-muto.mp4` | 17,6 s | *(identico al filmato 03)* |
| `scena-05-avvio-sharded-muto.mp4` | 24,9 s | **Un comando, e c'è un cluster** |
| `scena-06-stato-sharded-muto.mp4` | 8,5 s | **Che cosa mi sta dicendo `sh.status()`** |
| `scena-07-distribuzione-sharded-muto.mp4` | 6,0 s | **9860 + 10140 = 20000** |
| `scena-08-guasto-shard-palco-muto.mp4` | 42,1 s | **Metà cluster risponde, l'altra metà aspetta** |
| `scena-09-failover-membro-shard-muto.mp4` | 14,3 s | **Lo shard elegge, e il router se ne accorge da solo** |

---

## I sei montaggi

### `01-failover-docker-kill-muto.mp4` · 19,2 s

**Titolo:** Il primario muore senza preavviso
**Alternative:** «8617 millisecondi» · «`docker kill` sul primario» · «Quanto dura un failover?»

Si termina il primario con `docker kill`: nessun preavviso, nessuna cessione del ruolo. I due
membri rimasti se ne accorgono solo quando scade il timeout, e ne eleggono uno nuovo.

**Il numero da mostrare:** elezione in **8617 ms**. Il container risulta `exited`, con
`RestartCount=0` ed `ExitCode=137` — cioè è stato ucciso, non è uscito da sé.

**Che cosa dire sopra:** che otto secondi e mezzo non sono un difetto di MongoDB, sono il tempo che
serve a *stabilire* che qualcuno è morto quando non l'ha detto a nessuno.

---

### `02-failover-i-due-gesti-muto.mp4` · 46,3 s

**Titolo:** Due modi di spegnere un primario, e uno costa otto volte l'altro
**Alternative:** «Brutale o educato: 8617 ms contro 1039 ms» · «Il contrario di quello che ti
aspetti» · «Non tutti i failover sono uguali»

Le due scene una dietro l'altra: prima `docker kill`, poi lo stesso primario che esce da sé con
`shutdownServer()`. È il montaggio più importante del Blocco 2 — **il punto non è nessuna delle due
scene, è il confronto.**

**I numeri da mostrare:** **8617 ms** contro **1039 ms**. Nel primo caso `ExitCode=137`, nel secondo
`ExitCode=0` e il container è ancora `running`.

**Che cosa dire sopra:** che il gesto brutale costa otto volte quello educato, perché nel secondo
caso il primario *dice* che se ne va e l'elezione parte subito invece di aspettare un timeout. Se
hai una sola slide per il Blocco 2, è questa.

---

### `03-maggioranza-persa-muto.mp4` · 17,6 s

**Titolo:** Il superstite è vivo, è sano, e non scrive più
**Alternative:** «E a quanti guasti regge?» · «Due su tre» · «Perché tre e non due»

Cadono due membri su tre. Il terzo risponde, è raggiungibile, i suoi dati ci sono tutti — e diventa
`SECONDARY`: smette di accettare scritture.

**Il numero da mostrare:** passa a `SECONDARY` dopo **8634 ms**.

**Che cosa dire sopra:** che è la risposta alla domanda che il pubblico fa sempre. Un replica set a
tre membri regge **un** guasto, non due, e il motivo non è la disponibilità dei dati: è che senza
maggioranza nessuno può garantire di essere l'unico primario. Meglio smettere di scrivere che
scrivere in due.

---

### `04-avvio-offline-muto.mp4` · 50,6 s

**Titolo:** Un comando, e il replica set c'è
**Alternative:** «Il lab parte senza rete» · «`make up-02`» · «Da zero a tre membri sani»

Da stack spento e dati cancellati: `make up-02` accende i tre membri e li mette in replica set,
`make smoke-02` passa tutti i controlli.

**Il numero da mostrare:** `Superati: 42 · Errori: 0`, e la riga finale «Lo stack 02 fa quello che
il file Compose promette».

> **Questo filmato non mostra che la rete è spenta.** L'icona del Wi-Fi barrata c'era nella ripresa
> a schermo intero, ma quel fotogramma conteneva anche materiale non pubblicabile, e il filmato è
> ritagliato sulla finestra del terminale. **È la frase che devi dire tu**, mentre scorre: che
> quando questa registrazione è stata fatta il Wi-Fi era spento e il cavo staccato, e che tutte le
> immagini erano già nella cache locale. Se vuoi che la slide lo affermi anche senza di te,
> aggiungici una riga di testo.

Ha anche un **aspetto diverso** dagli altri tredici: quelli mostrano solo il testo, questo mostra
la finestra del terminale con le sue decorazioni. Nasce da una ripresa dello schermo, non da una
registrazione di terminale — è l'unico, ed è l'unico che poteva esserlo.

---

### `05-guasto-shard-nei-due-profili-muto.mp4` · 56,4 s

**Titolo:** Lo stesso guasto, due architetture: quindici secondi contro zero
**Alternative:** «E se ne cade uno?» · «Un membro per shard, o tre» · «Quanto vale la ridondanza,
in secondi»

Le due scene una dietro l'altra. Prima il profilo `palco`, un membro per shard: si ferma l'unico
membro, e metà cluster continua a rispondere mentre l'altra metà aspetta. Poi il profilo
`completo`, tre membri per shard: lo stesso guasto, e il router non se ne accorge nemmeno.

**I numeri da mostrare:** nel primo caso, lettura sullo shard vivo in **1 s**,
`FailedToSatisfyReadPreference` dopo **15 s** e **16 s**, ritorno in **3 s**. Nel secondo, totale
ancora **20000** documenti in **0 s**, primario passato da `shard1a` a `shard1b`, ritorno in **2 s**.

**Che cosa dire sopra:** che la differenza fra le due colonne è esattamente ciò che si compra
mettendo tre membri per shard invece di uno — e che il profilo `palco` non è un lab fatto male, è
un lab che ci sta in un portatile e che mostra il guasto *meglio*, perché lo rende visibile.

---

### `06-blocco-3-per-intero-muto.mp4` · 39,3 s

**Titolo:** Uno sharded cluster dentro un portatile
**Alternative:** «Undici servizi, quattro chunk, ventimila documenti» · «Accensione, stato,
distribuzione» · «Che cos'è uno shard, visto da terminale»

Le tre scene del Blocco 3 in fila: l'avvio, `sh.status()`, la distribuzione dei documenti.

**I numeri da mostrare:** undici servizi che si accendono nell'ordine giusto fino a
`Container sh-up-03 Healthy`; poi 2 shard, `lab.ordini` in **4 chunk** due per shard, balancer
abilitato, 1 router; poi **9860 + 10140 = 20000**.

**Che cosa dire sopra:** che è il filmato da tenere pronto se il cluster non parte in sala — questo
è il blocco che a voce non si racconta, perché il punto è vedere undici cose accendersi in ordine.

---

## Le otto scene singole

Da usare quando una slide deve mostrare **un pezzo solo**.

### `scena-03-failover-terminazione-pulita-muto.mp4` · 27,1 s

**Titolo:** Il primario si dimette: 1039 millisecondi
**Alternative:** «Uscire educatamente» · «`shutdownServer()`»

Il primario esce da sé: cede il ruolo e lo comunica. Elezione in **1039 ms**, container ancora
`running`, `RestartCount=1`, `ExitCode=0`. È la metà «educata» del filmato 02 — usala da sola solo
se la slide precedente ha già mostrato il `docker kill`, altrimenti il numero non dice niente.

---

### `scena-05-avvio-sharded-muto.mp4` · 24,9 s

**Titolo:** Un comando, e c'è un cluster
**Alternative:** «Undici servizi nell'ordine giusto» · «keyfile, config server, shard, router»

L'accensione per intero: keyfile, config server, i due shard, il router, `addShard`, i dati. La
catena finisce con `Container sh-up-03 Healthy`. Buona come apertura del Blocco 3.

---

### `scena-06-stato-sharded-muto.mp4` · 8,5 s

**Titolo:** Che cosa mi sta dicendo `sh.status()`
**Alternative:** «Due shard, quattro chunk, un router» · «Leggere lo stato senza spaventarsi»

`sh.status()` per intero — che è tanto testo — e sotto le quattro righe che contano davvero: 2
shard, `lab.ordini` in **4 chunk** due per shard, balancer abilitato, 1 router. Otto secondi e
mezzo: la più corta, sta bene accanto a un elenco puntato.

---

### `scena-07-distribuzione-sharded-muto.mp4` · 6,0 s

**Titolo:** 9860 + 10140 = 20000
**Alternative:** «Partizionata, non copiata» · «Lo stesso conteggio, da tre punti di vista»

Gli stessi documenti contati prima dal router e poi shard per shard: **49,3 %** e **50,7 %**. È il
cuore del blocco, e sei secondi: **la differenza fra sharding e replica sta tutta in questa
addizione.** Se devi tagliare tutto il resto del Blocco 3, tieni questa.

---

### `scena-08-guasto-shard-palco-muto.mp4` · 42,1 s

**Titolo:** Metà cluster risponde, l'altra metà aspetta
**Alternative:** «E se ne cade uno?» · «Quindici secondi di attesa, poi l'errore»

Si ferma l'unico membro di uno shard, nel profilo `palco`. Lettura sullo shard vivo in **1 s**;
`FailedToSatisfyReadPreference` dopo **15 s** e **16 s**; ritorno in **3 s**.

**Attenzione a non accorciarla.** I quindici secondi di attesa prima dell'errore non sono una pausa
morta: **sono la risposta.** Un client che aspetta un quarto di minuto e poi fallisce è un
comportamento diverso da un client che fallisce subito, ed è la cosa che chi gestisce un cluster
deve sapere riconoscere. Se la slide ti sembra lenta, è perché il sistema *è* lento in quel caso.

---

### `scena-09-failover-membro-shard-muto.mp4` · 14,3 s

**Titolo:** Lo shard elegge, e il router se ne accorge da solo
**Alternative:** «Lo stesso guasto, con tre membri» · «Zero secondi»

Lo stesso guasto della scena 8, ma nel profilo `completo`: tre membri per shard. Il totale è ancora
**20000** documenti, letti in **0 s**; il primario passa da `shard1a` a `shard1b`; il ritorno costa
**2 s**. Va **dopo** la scena 8, sempre: da sola non si capisce che cosa abbia di notevole.

---

## Come rifarli

```bash
make filmati            # tutti e tredici i fabbricati, da capo
make filmati NOME=05-guasto-shard-nei-due-profili-muto   # uno solo
make filmati-elenco     # che cosa produrrebbe, senza produrlo
```

Il quattordicesimo — `04-avvio-offline-muto.mp4` — non si rifà così: si rigira con
`make filmato NOME=04-avvio-offline-muto AUDIO=no`, e prima si prepara lo schermo (vedi
[«Lo schermo intero è anche quello che non vuoi pubblicare»](README.md#schermo-intero)).

---

**Dove stanno i file.** I `.mp4` non sono in questo repository e non ci entrano: pesano quanto
tutto il resto e si rifanno dalla fonte, che è il `.cast` ([ADR-0141](../../Decision.md#adr-0141)).
Vivono in `~/SqlStart2026-registrazioni`, dove `make preflight` li conta. Questa pagina sta invece
nel repository, perché i titoli e le descrizioni non si rigenerano da niente.

**Decisioni correlate:** [ADR-0140](../../Decision.md#adr-0140) (la passata muta è quella che va
dentro le slide), [ADR-0141](../../Decision.md#adr-0141) (i filmati si fabbricano dalle
registrazioni), [ADR-0142](../../Decision.md#adr-0142) (perché il filmato 4 ha un aspetto diverso e
non mostra la rete spenta).
