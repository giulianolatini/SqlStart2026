# Revisione della PR #app-sorgenti — foglio di triage

Prodotto da `.claude/skills/revisione-pr/scripts/revisione.sh`. I rilievi arrivano da due revisori esterni e **non sono ancora un giudizio**: lo diventano quando ogni scheda ha un verdetto motivato scritto sotto.

**12 rilievi** — Codex (codex): 10, Gemini Pro (agy): 2.

| ID | Gravità | Confidenza | Categoria | Titolo | Verdetto |
|---|---|---|---|---|---|
| C-3 | alta | media | security | La mappa dei parametri conserva la password in un percorso di errore della CLI | **accolto · riprodotto** |
| C-1 | media | alta | congruita-commit | Il commit descrive un cronometro delle scritture, ma il codice misura la topologia | **accolto sul fatto · nessuna azione** |
| C-10 | media | alta | altro | Il restore attribuisce all'oplog una differenza di conteggi non verificata | **accolto · riprodotto** |
| C-4 | media | alta | altro | Un errore del sink può lasciare i lettori in un ciclo infinito | **accolto · riprodotto anche da riga di comando** |
| C-5 | media | alta | altro | La fine di stderr disattiva il tetto prima della terminazione del processo | **accolto · riprodotto** |
| C-6 | media | alta | altro | Un errore durante l'invio della password lascia il processo senza gestione | **accolto · riprodotto** |
| C-7 | media | alta | altro | L'EOF viene trattato come conferma di un guasto mai eseguito | **accolto · riprodotto sullo stack** |
| C-8 | media | alta | altro | Le scritture senza conferma vengono contate come confermate | **accolto · riprodotto** |
| C-9 | media | alta | altro | Il confronto dello sharding considera uguali anche corse con fallimenti diversi | **accolto ed esteso · guardia morta** |
| G-2 | media | alta | security | Percorso del file temporaneo prevedibile e insicuro | **accolto in parte · rimedio respinto e riscritto** |
| C-2 | bassa | alta | congruita-commit | I soggetti dei commit omettono sistematicamente l'ambito obbligatorio | **respinto sul merito · difetto nella skill** |
| G-1 | bassa | alta | congruita-commit | Messaggi di commit privi dell'ambito obbligatorio | **respinto sul merito · difetto nella skill** |

## C-3 — La mappa dei parametri conserva la password in un percorso di errore della CLI

*Sollevato da Codex (codex).*

- **Categoria:** security
- **Gravità:** alta
- **Confidenza:** media
- **Dove:** app/src/mongolab/infrastructure/bersagli.py, connetti; app/src/mongolab/cli.py, costruzione di app

**Evidenza citata dal revisore:**

```
parametri["password"] = credenziali.password
+        parametri["authSource"] = "admin"
+    return MongoClient(vista.uri, **parametri)
```

**Perché sarebbe un problema:** Un errore di costruzione del client, per esempio da --max-pool-size negativo, lascia la password nel dizionario locale parametri della traccia. La CLI Typer non disabilita la visualizzazione dei locali nelle eccezioni formattate: repr=False su Credenziali non protegge il dizionario, e la configurazione effettiva di Typer non è verificabile dalle sole dipendenze aperte del dossier.

**Rimedio proposto:** Disabilitare esplicitamente i locali nei traceback della CLI e verificare un errore di configurazione con una credenziale sentinella, controllando stdout e stderr.

### Verdetto

**Accolto, e riprodotto.** Il revisore dichiarava confidenza «media» perché dalle sole dipendenze
aperte nel fascicolo non poteva verificare la configurazione di Typer. Verificata: aveva ragione,
e la falla è più stretta e più interessante di come l'ha descritta.

**Prima misura: oggi non esce.** Con una credenziale **sentinella** — la password vera non è mai
entrata in questa prova — e un errore di costruzione del client:

```
$ MONGOLAB_PUNTO_DI_VISTA=rete UTENTE_AMMINISTRATORE=admin \
  PASSWORD_AMMINISTRATORE=SENTINELLA-NON-E-UNA-PASSWORD-VERA \
  uv run mongolab workload --target rs --max-pool-size -1 --duration 1
…
ValueError: The value of maxPoolSize must be a non negative integer
sentinella in stdout: 0    sentinella in stderr: 0
```

Il motivo è che `typer` 0.27.2 ha `pretty_exceptions_show_locals = False` come predefinito. Il
nome `parametri` compare nello stderr quattro volte, ma sono **righe di sorgente** disegnate da
rich, non valori.

**Seconda misura: la protezione non è nostra, ed è recente.** `app/pyproject.toml:8` dichiara
`typer>=0.15`, senza tetto. Il predefinito di quella opzione è cambiato dentro l'intervallo
ammesso:

```
typer 0.15.1 show_locals = True      typer 0.19.0 show_locals = True
typer 0.16.0 show_locals = True      typer 0.21.0 show_locals = True
typer 0.17.0 show_locals = True      typer 0.24.0 show_locals = False
                                     typer 0.27.2 show_locals = False
```

Sette versioni provate, il ribaltamento fra 0.21 e 0.24. Sei delle versioni che il vincolo ammette
mostrano i locali.

**Terza misura: con una di quelle, la sentinella esce.** Stessa riga, stesso errore, con
`typer==0.21.0` — dentro il vincolo dichiarato:

```
sentinella in stderr: 5
│ │   parametri = {'tz_aware': True, …, 'username': 'admin', 'password': 'SENTINELLA-…'}
│ │ keyword_opts = {…, 'username': 'admin', 'password': 'SENTINELLA-…'}
│ │       kwargs = {…, 'username': 'admin', 'password': 'SENTINELLA-…'}
```

Cinque volte, in tre frame diversi, sul terminale. `repr=False` su `Credenziali` non protegge
nulla: quando il valore è già dentro un `dict` è un `str` come gli altri, e rich lo stampa. Il
revisore lo aveva detto esattamente così.

**Che cosa ci salva oggi, e perché non basta.** `app/uv.lock:287` fissa `typer` a 0.27.2, quindi
chi usa `uv run` o `uv sync` ha la versione sicura. Ma la garanzia sta nel lock e in un
predefinito altrui: chi installa risolvendo da capo, o con un vincolo diverso, ricade
nell'intervallo che perde la password. È esattamente la forma di rischio che ADR-0054 vuole
escludere — la credenziale non deve poter finire su un terminale — con la differenza che qui non
c'è una riga di comando da correggere, c'è un predefinito da non lasciare implicito.

**Il rimedio è quello proposto, in due righe.** Passare `pretty_exceptions_show_locals=False`
esplicito a `typer.Typer(...)` in `app/src/mongolab/cli.py:597`, e una prova che invochi la CLI
con una credenziale sentinella e verifichi che non compaia né in stdout né in stderr — la prova
che oggi non c'è: `grep -rl 'pretty_exceptions\|show_locals' app/tests/` non trova nulla. Una riga
trasforma un incidente evitato in una promessa mantenuta, e la prova la tiene ferma anche se
domani una dipendenza cambia idea di nuovo.

**Un difetto in più, trovato verificando questo.** `typer>=0.15` è un pavimento falso:
l'applicazione **non gira** su 0.15.1. Muore con codice 2 prima di arrivare a `connetti`:

```
Invalid value for '--sink': <Resa.RICH: 'rich'> is not one of 'rich', 'plain', 'null'.
```

Il valore predefinito di un `Enum` in un'opzione non era gestito così, in quella versione. Il
vincolo dichiarato mente sul minimo supportato. Da alzare — e la versione da mettere è comunque
una di quelle con `show_locals` già a `False`, il che chiude i due problemi con lo stesso numero.

## C-1 — Il commit descrive un cronometro delle scritture, ma il codice misura la topologia

*Sollevato da Codex (codex).*

- **Categoria:** congruita-commit
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** c7f81716

**Evidenza citata dal revisore:**

```
il cronometro si arma alla prima scrittura fallita e si ferma
alla prima riuscita dopo
```

**Perché sarebbe un problema:** CronometroInterruzione.considera ignora ogni evento diverso da TopologyChanged. Il numero risultante misura l'assenza di un primario nella topologia osservata, non l'interruzione effettivamente subita dalle scritture: il messaggio attribuisce alla misura un significato diverso.

**Rimedio proposto:** Correggere il messaggio indicando gli estremi SDAM effettivamente usati, oppure implementare e verificare la misura sulle scritture se quella è la decisione voluta.

### Verdetto

**Accolto sul fatto, senza azione — e il rilievo è più preciso di quanto la sua gravità «media»
suggerisca.** Il revisore ha letto bene il codice: `CronometroInterruzione.considera`
(`app/src/mongolab/application/scenari.py:238-247`) scarta tutto ciò che non è un
`TopologyChanged`, apre quando `evento.successiva.primario is None` e chiude quando un primario
ricompare. Nessuna scrittura entra nella misura. La frase del corpo di `c7f81716` — «il cronometro
si arma alla prima scrittura fallita e si ferma alla prima riuscita dopo» — descrive un meccanismo
che non è quello implementato, e la differenza non è nominale: con `serverSelectionTimeoutMS` a 20
000 una scrittura nella finestra senza primario **si blocca** invece di fallire, quindi «prima
scrittura fallita» potrebbe non accadere mai in una corsa che il cronometro misura benissimo.

Due cose però limitano il danno, e vanno dette perché cambiano il verdetto operativo.

**Lo stesso messaggio dice anche la cosa giusta**, due frasi prima: «L'interruzione si deduce
dagli eventi del ponte, non si misura sondando (ADR-0096)». Il corpo si contraddice nell'arco di
un paragrafo: non è una convinzione sbagliata, è una frase scritta male accanto a quella giusta.

**La documentazione è esatta, e mostra il codice.**
`app/docs/14-la-scena-del-failover-e-i-due-numeri.md:271-296` riporta `considera` per intero e poi
dice quale numero ne esce, senza ambiguità:

> non il tempo in cui il replica set ha eletto, ma il tempo in cui il driver è rimasto
> senza un posto dove scrivere

Cercata in tutto `docs/` e `app/docs/`, la formulazione sbagliata non compare da nessuna parte:
vive solo nel corpo di quel commit. Chi legge la pagina — cioè il pubblico, e chiunque riprenda il
repository dopo il 18 settembre — trova la descrizione corretta.

**Perché nessuna azione.** Il rimedio proposto ha due rami e nessuno dei due si può prendere.
Riscrivere il messaggio significa riscrivere cronologia già spinta su `origin/release/1.0`.
Implementare la misura sulle scritture sarebbe cambiare la misura, non correggere una frase — e la
misura attuale è quella che ADR-0096 ha scelto, con la motivazione scritta e i 10 019 ms di M-043
raccolti con essa.

Resta un promemoria, che vale più del rilievo: **la frase sbagliata è a un passo da quella
giusta.** «La misura è quella che l'applicazione ha davvero subito» è vero — ciò che
l'applicazione subisce è non avere dove scrivere — ed è proprio la sua verità ad aver reso
invisibile il pezzo falso che la precede. Da tenere presente se quel numero finisce su una slide:
la formulazione da usare è quella di `app/docs/14`, non quella del commit.

## C-10 — Il restore attribuisce all'oplog una differenza di conteggi non verificata

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** app/src/mongolab/presentation/rapporto.py, ripristino

**Evidenza citata dal revisore:**

```
f"{scena.differenza} scritti mentre il dump era in corso: "
+                "stanno nell'oplog, che il restore non riapplica"
```

**Perché sarebbe un problema:** La differenza viene calcolata leggendo l'origine al momento del restore, che è un comando separato: comprende anche eventuali scritture successive al dump. Il codice non esamina l'oplog né conserva i conteggi ai confini della copia, quindi presenta come verificata una causa che i due conteggi non dimostrano.

**Rimedio proposto:** Mostrare la differenza come dato osservato senza attribuirla interamente all'oplog; per dichiararne la causa, raccogliere e verificare le informazioni relative alla finestra del dump.

### Verdetto

**Accolto, e riprodotto contro lo stack vero.** Il revisore aveva ragione sul meccanismo e non
poteva sapere quanto fosse facile far mentire la frase.

**Il difetto, nel codice.** `ScenarioRestore.esegui`
(`app/src/mongolab/application/scenari.py:870-877`) prende i due conteggi **dopo** il restore, e
quello dell'origine è un `self._origine.count({})` letto in quel momento. `demo restore` è un
comando separato da `demo backup-live`: fra la fine del dump e quella lettura può passare
qualunque cosa, e tutto ciò che passa finisce dentro `differenza`. Poi
`app/src/mongolab/presentation/rapporto.py:277-283` gli attribuisce una causa che nessuno dei due
conteggi dimostra.

**La riproduzione.** Stack 02 acceso, `demo backup-live --target rs --carico 3`:

```
carico      1450 scritture · 1450 confermate
sotto dump   320 scritture ·  320 confermate
prossimo: mongolab demo restore … --collection carico-20260906-145510
```

Poi **sette** documenti scritti nella collezione d'origine, con `mongosh`, **a dump già finito** —
quindi non nell'oplog del dump, che a quel punto era chiuso da un pezzo. Poi il restore, senza
toccare altro:

```
restore     1777 all'origine · 1680 nella copia · differenza 97
            97 scritti mentre il dump era in corso: stanno nell'oplog, che il restore non riapplica
```

Novantasette, di cui **sette scritti dopo**. La frase è falsa per sette documenti su novantasette,
e lo schermo non lascia modo di accorgersene.

**C'è un secondo errore nella stessa riga, e il revisore non lo nomina.** I numeri dicono che
durante il dump sono state confermate **320** scritture e che alla copia ne mancano **90** (1770 −
1680): il dump ne ha catturate 230 mentre giravano. «*N* scritti mentre il dump era in corso»
invita a leggere *N* come «quanto è costata la finestra del dump», e non lo è né come sottoinsieme
né come totale. Vale anche per la registrazione buona: 275 scritture confermate sotto dump,
differenza 91.

Lo stesso passo, con le stesse parole, sta in `docs/05-talk/runbook-demo.md:473-475` — «I
documenti di differenza sono quelli scritti *mentre* il dump era in corso» — quindi la correzione
è in due posti, non in uno.

**Che cosa resta vero.** Che il restore non riapplichi l'oplog è misurato e motivato:
`--oplogReplay` è incompatibile con la rinomina dei namespace (M-024). E nel copione così com'è
scritto — collezione con la data e l'ora nel nome, `backup-live` che spegne il carico nel
`finally` subito dopo il dump (`scenari.py:729-730`), restore attaccato subito dopo — nessuno
scrive nell'intervallo, e il numero sullo schermo è onesto. **Il difetto non è che il numero sia
sbagliato dal palco: è che il programma afferma una causa che non ha modo di conoscere**, e la
afferma con la stessa faccia sia quando è vera sia quando non lo è.

**Rimedio, nella forma del revisore e con una riga in meno di ambizione.** Dire ciò che si osserva
— «97 documenti che la copia non ha: il dump è stato preso a caldo, e il restore non riapplica
l'oplog» — invece di dichiarare quando sono stati scritti. Chi volesse tenere l'attribuzione deve
prendere i conteggi ai due bordi del dump, e quei numeri `ScenarioBackup` ce li ha già
(`Riepilogo.scritture` della fase `dump`): sono in un comando diverso, ed è questa la ragione per
cui oggi mancano.

Non è un blocco per il 18 settembre: dal palco il numero esce giusto. È una frase da correggere
prima che qualcuno la citi.

*Nota di igiene:* la collezione di prova creata qui è stata tolta; in `lab` è rimasta la sola
`ordini`.

## C-4 — Un errore del sink può lasciare i lettori in un ciclo infinito

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** app/src/mongolab/application/workload.py, WorkloadRunner.esegui

**Evidenza citata dal revisore:**

```
self._sink.emit(elemento)
```

**Perché sarebbe un problema:** Con un limite a conteggio e lettori attivi, fine viene impostato consumando le sentinelle degli scrittori. Se emit solleva, per esempio perché si chiude la pipe di PlainSink, il drenaggio termina e il context manager del pool aspetta lettori che continuano ad attendere fine: il comando non restituisce più il controllo.

**Rimedio proposto:** Impostare un segnale di arresto in un finally che copra il drenaggio e farlo rispettare da tutti i worker prima di attendere la chiusura del pool. Verificare il caso con lettori attivi e sink che solleva.

### Verdetto

**Accolto, e riprodotto due volte — la seconda con una riga di comando che si può battere in
scena.** Il revisore ha ricostruito il meccanismo esattamente, e la docstring del repository lo
conferma parola per parola prima ancora della prova.

**Il meccanismo, scritto in casa.** `workload.py:643-646`: con il limite di conteggio «non c'è
scadenza, e a fermare i lettori è `fine`, che il ciclo di drenaggio alza quando l'ultimo scrittore
ha smesso — perché un lettore non ha un lavoro da esaurire e **altrimenti girerebbe per sempre**».
Quel «altrimenti» è tutto il rilievo: `fine.set()` sta dentro il ciclo di drenaggio
(`workload.py:479-480`), e `self._sink.emit(elemento)` sta nello stesso ciclo, tre righe più sotto
(`:489`), **senza protezione**. Se `emit` alza, il drenaggio muore prima di aver alzato `fine`; i
lettori non hanno nessun'altra condizione di uscita; e l'eccezione, uscendo dal `with`, finisce in
`ThreadPoolExecutor.__exit__`, che fa `shutdown(wait=True)` e li aspetta. Aspetta per sempre.

**Prima prova, in laboratorio.** Stessa corsa, un sink che alza `BrokenPipeError` dopo tre eventi,
una volta senza lettori e una con due:

```
lettori=0: BrokenPipeError: pipe chiusa (finta)
lettori=2: ANCORA VIVA dopo 6.0 s -> non torna piu'

thread ancora vivi alla fine: 3
```

Senza lettori l'errore esce e il comando muore, che è il comportamento giusto. Con i lettori non
esce niente: `esegui` non ritorna, e i thread restano.

**Seconda prova, dalla riga di comando, contro lo stack 02 acceso.** Il sink che si chiude non è
un'ipotesi di laboratorio: è `--sink plain` in una pipe che l'altro capo chiude.

```
$ mongolab workload --target rs --writes 20000 --readers 0 --sink plain | head -3
--readers 0: tornato, exit=0

$ mongolab workload --target rs --writes 20000 --readers 4 --sink plain | head -3
--readers 4: NON TORNA entro 45 s
```

Quarantacinque secondi e ancora lì; l'ho dovuto uccidere con `pkill`. `| head`, `| less` chiuso
con `q`, un `Ctrl-C` sul processo a valle: tutte e tre chiudono la pipe, e tutte e tre bastano.

**Perché conta il 18 settembre.** Non perché la riga del copione contenga una pipe — non la
contiene — ma per la forma del guasto. Un comando che *muore* davanti al pubblico si riavvia in
tre secondi; un comando che **non torna** costringe a un `Ctrl-C` che non funziona (il segnale
arriva al main, che è dentro `shutdown`), poi a cercare un'altra finestra, poi a spiegare. È il
caso peggiore sul palco, ed è quello in cui `--readers` — che è un gancio che esiste apposta per
mostrare le letture durante un failover — trasforma un errore in un blocco.

**Rimedio: quello proposto, ed è piccolo.** `fine.set()` in un `finally` che copra tutto il ciclo
di drenaggio, così i lettori escono comunque e il `with` può chiudersi; l'eccezione del sink poi
risale normale. Vale la pena aggiungere anche la prova che qui non c'è: una corsa con lettori e un
sink che alza, con un tetto di tempo, perché una prova che dimostra un blocco deve poter fallire
in un tempo finito.

*Nota di igiene:* le collezioni `carico-*` create dalle due corse sono state tolte; in `lab` resta
la sola `ordini`, e nessun processo `mongolab` è rimasto vivo.

## C-5 — La fine di stderr disattiva il tetto prima della terminazione del processo

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** app/src/mongolab/infrastructure/backup.py, SubprocessBackup._avanzamento

**Evidenza citata dal revisore:**

```
if guardia is not None:
+                guardia.cancel()
+            processo.stderr.close()
+
+        codice = processo.wait()
```

**Perché sarebbe un problema:** Un processo può chiudere stderr e restare vivo. In quel caso il timer viene cancellato e wait blocca senza scadenza, quindi --tetto non garantisce la terminazione della scena; inoltre quel wait è fuori dall'except che abbatte il figlio su interruzione.

**Rimedio proposto:** Mantenere attiva la guardia e la gestione delle eccezioni fino al completamento di wait, cancellando il timer soltanto dopo aver raccolto il processo.

### Verdetto

**Accolto, e riprodotto contro il codice di produzione.** Il revisore ha letto la sequenza giusta:
`app/src/mongolab/infrastructure/backup.py:475-480` cancella la guardia e chiude `stderr` nel
`finally`, e solo **dopo** chiama `processo.wait()`. Quel `wait()` sta fuori dal `try`, quindi
fuori dalla guardia e fuori dall'`except BaseException` che abbatte il figlio.

**La prova.** Un finto `mongodump` che scrive una riga su `stderr`, chiude il descrittore con
`os.close(2)` e poi dorme otto secondi. Nessun doppio: `SubprocessBackup.dump` vero, con
`tetto_s=2.0`.

```
$ uv run python prova-c5.py
nessuna eccezione
avanzamenti letti: 0
tempo trascorso con tetto_s=2.0: 8.0 s
```

Otto secondi con un tetto di due. E la prima corsa, con il finto che dormiva 120 secondi, è stata
uccisa dal *mio* `timeout 60` — non dal tetto, che non è mai scattato.

**Il meccanismo è peggiore di «il timer viene cancellato».** L'EOF su `stderr` arriva subito,
quindi il `finally` cancella la guardia a t≈0, cioè **due secondi prima** che avrebbe dovuto
suonare. Poi `wait()` blocca per tutta la vita residua del figlio. La durata della scena non è
governata dal tetto: è governata dal processo che il tetto doveva limitare. E `dump` esce **senza
eccezione**, con `scaduto` mai impostato: chi guarda vede una scena lenta, non una scena scaduta.

**Perché conta qui.** `--tetto` non è un dettaglio di robustezza: è la rete che ADR-0118 mette
sotto l'Atto III perché un `mongodump` che non torna è «l'altro modo di rovinare l'Atto III e
l'unico che non si vede arrivare» — parole della docstring di `_con_dump`. Il tetto copre il caso
in cui il figlio tace **e** resta attaccato a `stderr`. Non copre il caso in cui il figlio chiude
`stderr` e resta vivo, che è la stessa disgrazia con un descrittore in meno.

**Quanto è probabile con `mongodump`.** Poco: gli strumenti del database parlano su `stderr` fino
alla fine. Ma il comando reale non è `mongodump`, è `docker compose -f … exec -T … mongodump …`, e
in quella catena chi tiene `stderr` è il client `docker` — la docstring di `_avanzamento` già
riconosce che il client e lo strumento dentro il container si possono separare. È lo stesso punto
cieco, guardato da un'altra parte.

**Rimedio: quello proposto.** Tenere viva la guardia e l'`except` fino a dopo `wait()`, e
cancellare il timer solo quando il processo è stato raccolto. In pratica il `wait()` finale va
dentro il `try`, e la cancellazione della guardia dopo di lui. La prova che lo tiene fermo è
quella qui sopra, con il finto `mongodump` sordo: oggi passa in 8 s, dopo la correzione deve
chiudersi in ~2 s con `DumpTroppoLungo`.

Non blocca il 18 settembre — è un caso che non si è mai visto in nove corse — ma è una rete di
sicurezza che oggi ha un buco della forma esatta del guasto che deve prendere.

## C-6 — Un errore durante l'invio della password lascia il processo senza gestione

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** app/src/mongolab/infrastructure/backup.py, SubprocessBackup._avvia

**Evidenza citata dal revisore:**

```
processo.stdin.write(self._password + "\n")
+            processo.stdin.flush()
+        processo.stdin.close()
```

**Perché sarebbe un problema:** Se il comando chiude stdin prima dell'invio, write, flush o close possono sollevare BrokenPipeError. _avanzamento non viene allora restituito e il suo cleanup non interviene: mancano la raccolta del processo e la chiusura garantita dei descrittori già aperti.

**Rimedio proposto:** Proteggere tutta l'inizializzazione successiva a Popen con un cleanup che chiuda i flussi, termini il processo se ancora vivo e ne attenda l'uscita prima di rilanciare.

### Verdetto

**Accolto, e riprodotto — con il caso brutto che il revisore ipotizzava e che si verifica
davvero.**

`_avvia` (`backup.py:409-422`) fa `Popen`, poi `write`, `flush`, `close` sullo `stdin`. Nessuno
dei tre è protetto, e il processo appena creato non è ancora in mano a nessuno: `_avanzamento`,
con il suo `except BaseException` che abbatte il figlio, riceve il `Popen` come **argomento** —
quindi non esiste ancora quando `_avvia` solleva.

**Prima prova: l'eccezione esce.** Finto strumento che chiude `stdin` con `os.close(0)` ed esce
subito con codice 3; password abbastanza grande da superare il buffer della pipe:

```
sollevato BrokenPipeError: [Errno 32] Broken pipe
processi finti rimasti: 0
```

**Seconda prova, quella che conta: il figlio resta acceso.** Stesso finto, ma invece di uscire
dorme trenta secondi — cioè uno strumento che non legge la credenziale e tira dritto:

```
sollevato BrokenPipeError: [Errno 32] Broken pipe
processi finti rimasti: 1 (ne avevo 0 prima)
```

Un processo orfano, che nessuno raccoglierà. Nel caso vero non è un finto che dorme: è un
`mongodump` — o il client `docker` che lo contiene — lasciato a girare contro il cluster mentre la
scena è già finita in errore. È esattamente il guasto che l'`except BaseException` di
`_avanzamento` esiste per impedire, e che qui accade **prima** che quell'`except` esista.

**Un dettaglio che aggrava.** L'eccezione è `BrokenPipeError`, non un errore del dominio: risale
lungo tutto lo scenario e arriva alla CLI come traceback. Il che la mette in rapporto diretto con
C-3: se un giorno i locali tornassero visibili, quel traceback conterrebbe il frame di `_avvia`,
dove `self._password` è a portata di `repr`. Due rilievi che da soli sono medi, insieme sono la
credenziale sullo schermo.

**Rimedio: quello proposto.** Un `try/except BaseException` intorno a tutto ciò che segue `Popen`,
che chiuda i flussi, uccida il figlio se è ancora vivo, lo attenda, e poi rilanci. Le due prove
qui sopra lo tengono fermo: la seconda deve arrivare a «processi finti rimasti: 0».

Da fare insieme a C-5 — è lo stesso file, la stessa domanda («chi garantisce che il figlio
muoia?») posta ai due estremi opposti della stessa funzione.

## C-7 — L'EOF viene trattato come conferma di un guasto mai eseguito

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** app/src/mongolab/cli.py, _gia_fatto

**Evidenza citata dal revisore:**

```
except EOFError:
+        typer.echo("   (nessuno da chiedere: proseguo)")
```

**Perché sarebbe un problema:** La funzione è usata da RegiaAnnunciata anche per fermare o sospendere il nodo, non soltanto nel finally di riparazione. Con stdin chiuso la scena prosegue senza conferma e senza eseguire alcun comando, producendo un bilancio di failover non provocato.

**Rimedio proposto:** Trattare l'EOF durante la richiesta del guasto come interruzione della scena. Gestire separatamente l'eventuale EOF della riparazione, preservando l'errore originale senza dichiarare effettuato il recupero.

### Verdetto

**Accolto, e riprodotto contro lo stack acceso.** Il revisore ha ragione, e la prova è che la
scena produce il bilancio di un failover che non è mai avvenuto — che è, parola per parola, ciò
che il repository si era ripromesso di non fare mai.

**La riproduzione.** Dentro la rete Compose, con `stdin` che non è un terminale: cioè il caso che
la docstring di `_gia_fatto` nomina per prima fra quelli in cui l'EOF va assorbito («un `docker
compose run` senza `-t`», `cli.py:485`).

```
$ docker compose ... run --rm -T app demo failover --target rs --carico 1 --elezione 3 --recupero 1

scena del failover su mongo-rs-1 · carico in lab.carico-20260906-131943

▸ da un'altra finestra, nella radice del repository:

  docker compose ... kill -s SIGKILL mongo-rs-1

   Invio quando è stato eseguito    (nessuno da chiedere: proseguo)

▸ da un'altra finestra, nella radice del repository:

  docker compose ... start mongo-rs-1

   Invio quando è stato eseguito    (nessuno da chiedere: proseguo)

failover    interruzione — · scritture perse 0
scritture   3350 confermate · 3350 ritrovate · 0 non confermate
prima       508 scritture · 508 confermate · p95 64.0 ms
durante     2241 scritture · 2241 confermate · p95 58.5 ms
dopo        601 scritture · 601 confermate · p95 63.5 ms
fasi        carico · guasto · elezione · ripresa · recupero · bilancio
```

E subito dopo, sullo stesso nodo:

```
$ docker ps --filter name=mongo-rs-1
mongo-rs-1 · Up 3 hours (healthy)
```

Tre ore in piedi. Nessun `SIGKILL`, nessun riavvio, nessuna elezione. Eppure il bilancio elenca
«guasto · elezione · ripresa» fra le fasi, dichiara `scritture perse 0` e mostra una colonna
«durante» con 2241 scritture — 2241 scritture *durante* niente.

**Perché è più grave di come l'ha scritto il revisore: il repository aveva già dato un nome a
questo esito.** `RegiaAnnunciata`, la classe che chiama `_gia_fatto`, si apre così
(`regia.py:213-216`): «Dentro la rete Compose l'applicazione vede la topologia… ma non ha il
socket del demone e non può fermare nessuno. **Fingere sarebbe la bugia peggiore possibile, perché
produce esattamente i numeri di un failover riuscito senza il failover.**» La classe è stata
disegnata per non poter fingere; l'assorbimento dell'EOF le restituisce quella possibilità dal
fondo, e l'uscita qui sopra è letteralmente «i numeri di un failover riuscito senza il failover».

**E il revisore ha ragione anche sulla portata.** `conferma` non è la conferma della riparazione:
è la conferma di tutti e quattro i verbi. `_chiedi` è uno solo (`regia.py:249-252`), e ci passano
`ferma`, `riavvia`, `sospendi`, `risveglia` (`:237-247`). L'assorbimento nato per il `finally`
della ripresa vale per il guasto che apre la scena.

**Ma la ragione di ADR-0119 resta buona, e va conservata.** L'EOF durante la ripresa va assorbito
davvero: quella conferma può arrivare mentre un'eccezione sta risalendo, e un'eccezione sollevata
dentro un `finally` prende il posto di quella che passava — chi guarda leggerebbe «EOF when
reading a line» al posto del motivo vero. Il difetto non è l'assorbimento, è che sia **uno solo
per due domande diverse**.

**Rimedio: quello proposto, e cioè separare i due casi.** Due funzioni di conferma, non una. Per
il guasto — `ferma` e `sospendi` — l'EOF è la fine della scena: nessuno da chiedere vuol dire
nessuno che possa provocare il guasto, e proseguire è produrre un numero falso; l'uscita giusta è
un `typer.BadParameter` che dica «questa scena ha bisogno di un terminale, oppure di
`MONGOLAB_PUNTO_DI_VISTA=host`». Per la ripresa — `riavvia` e `risveglia` — l'EOF resta assorbito
com'è oggi, con l'avvertenza che il nodo è rimasto giù, e senza mai coprire l'eccezione che stava
risalendo.

Vale la pena anche che il bilancio si rifiuti di dire «guasto · elezione · ripresa» quando
l'ispettore non ha visto cambiare il primario: la scena saprebbe accorgersene da sola.

**Blocca il 18 settembre?** No, perché in scena il comando si dà da un terminale vero e la domanda
trova qualcuno. Ma tocca due cose che al 18 settembre servono: la registrazione `.cast` non
interattiva, che produrrebbe un bilancio falso senza che nessuno se ne accorga, e le prove di
integrazione, che è esattamente il posto in cui una scena finta passa per verde.

*Nota di igiene:* le due collezioni `carico-*` create dalle corse sono state tolte; in `lab` resta
la sola `ordini`, e `mongo-rs-1` non è mai stato fermato.

## C-8 — Le scritture senza conferma vengono contate come confermate

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** app/src/mongolab/infrastructure/store.py, PymongoStore.insert_many

**Evidenza citata dal revisore:**

```
return len(self.collezione.insert_many(copie).inserted_ids)
```

**Perché sarebbe un problema:** La CLI accetta --write-concern 0 e lo inoltra come w=0. inserted_ids conta gli identificatori dei documenti inviati anche senza acknowledgment del server: WorkloadRunner emette quindi WriteSucceeded e stampa conferme che non ha ricevuto.

**Rimedio proposto:** Rifiutare w=0 per le misure che richiedono conferme, oppure rappresentare esplicitamente le scritture non confermate controllando acknowledged.

### Verdetto

**Accolto, e riprodotto due volte.** Il revisore ha ragione su tutta la catena, e la prova sta in
una riga di output che dice una cosa impossibile.

**Prima prova: la CLI accetta `w=0` e poi dichiara le conferme.**

```
$ uv run mongolab workload --target rs --write-concern 0 --duration 3 --sink plain
carico      25786 scritture · 25786 confermate · 0 fallite · 0 ritentate · 25786 documenti
latenze     p50 0.1 ms · p95 2.3 ms · p99 8.3 ms · max 1473.6 ms · 25786 campioni
```

«25 786 confermate» con `w=0`. Con `w=0` il server **non manda nessuna conferma**: non c'è niente
da contare. Il `p50 0.1 ms` è la firma del fatto — un round-trip verso un replica set non costa un
decimo di millisecondo — ed è la stessa riga che dovrebbe far sospettare chi legge, se sapesse
cosa guardare.

**Seconda prova: da dove viene il numero.** Con il codice di questo repository, sullo stack
acceso:

```
acknowledged = False
len(inserted_ids) = 5  <- e' questo che l'app conta
```

`PymongoStore.insert_many` (`app/src/mongolab/infrastructure/store.py:68`) restituisce
`len(...inserted_ids)`, cioè quanti `_id` il **client** ha generato prima di spedire. Il risultato
porta `acknowledged=False` accanto, e nessuno lo guarda. Da lì il numero diventa
`WriteSucceeded(documenti=confermati)` (`workload.py:744`) e finisce sullo schermo come
«confermate».

**La docstring dichiara proprio ciò che non fa.** `store.py:69`: «Inserisce e restituisce quanti
il server ha confermato». Con `w=0` non è una imprecisione, è il contrario del vero.

**Perché è più grave di «media».** Non per il caso d'uso — nessuno userà `w=0` dal palco — ma per
il mestiere del programma. `mongolab` esiste per **misurare** il prezzo delle garanzie:
`--journal` contro `--no-journal`, `--write-concern majority` contro `1`, ognuna «vale come mezza
misura» (ADR-0109, ADR-0114). Uno strumento che confronta garanzie e poi conta come confermato ciò
che non lo è mente esattamente sull'asse che pretende di misurare. E la confusione è già stata
evitata altrove: il bilancio del failover tiene «confermate» e «non confermate» come **due voci
distinte** (`rapporto.py:190,207-209`), perché — dice il commento — sono cose diverse. È la stessa
distinzione, che nel carico non arriva.

**Rimedio: il primo dei due proposti, che qui è anche il più economico.** Rifiutare
`--write-concern 0` con un `typer.BadParameter` che dica il perché — «con w=0 non c'è nessuna
conferma da contare, e questo strumento misura conferme» — sulla falsariga del rifiuto già
esistente fra `--writes` e `--duration`. Chi vuole davvero vedere quanto costa la conferma la
toglie dal confronto, non dal conteggio.

Se un giorno servisse mostrare `w=0` come termine di paragone in scena, allora serve il secondo
rimedio: leggere `acknowledged` e riportare le scritture come «spedite, non confermate», con la
latenza dichiarata per quello che è — il tempo di consegna al socket.

Non è un blocco per il 18 settembre: la riga del copione non contiene `--write-concern 0`.

*Nota di igiene:* le collezioni di carico create da questa prova sono state tolte; in `lab` resta
la sola `ordini`.

## C-9 — Il confronto dello sharding considera uguali anche corse con fallimenti diversi

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** app/src/mongolab/application/scenari.py, EsitoSharding.confrontabile

**Evidenza citata dal revisore:**

```
return self.carico_intera.scritture == self.carico_sparsa.scritture
```

**Perché sarebbe un problema:** Riepilogo.scritture comprende sia successi sia rese definitive. Con il limite a conteggio le due corse risultano quindi confrontabili anche se una inserisce tutti i documenti e l'altra fallisce, e il rapporto nasconde la differenza dietro «scritture su ognuna».

**Rimedio proposto:** Confrontare i documenti confermati e mostrare i fallimenti delle due corse nel bilancio, dichiarando non confrontabile un carico effettivamente diverso.

### Verdetto

**Accolto ed esteso, e riprodotto.** Il revisore ha ragione sul fatto; la prova mostra che la
conseguenza è più grande di come l'ha scritta.

**Il fatto.** `Riepilogo.scritture` è dichiarato per quello che è — «le scritture **logiche**,
cioè i tentativi riusciti più le rese definitive» (`workload.py:236-243`) — e `confrontabile`
confronta proprio quello (`scenari.py:930-940`). Due corse identiche nel numero e opposte
nell'esito passano per confrontabili.

```
corsa pulita  scritture=20 riuscite=20 fallite=0 confermati=20
corsa sporca  scritture=20 riuscite=15 fallite=5 confermati=15

il corpo di `confrontabile` su queste due corse:
  carico_intera.scritture == carico_sparsa.scritture -> True
  documenti_confermati uguali?                       -> False
```

Sono due corse vere di `WorkloadRunner`, non un doppio del confronto: cambia solo l'archivio
sotto, che nella seconda fa cadere le prime cinque scritture fino alla resa. Il numero che la
guardia guarda è lo stesso; quello che conta è diverso di cinque.

**L'estensione, ed è la parte che il revisore non ha visto: la guardia non può scattare mai.**
`demo sharding` passa **sempre** un limite di conteggio — `cli.py:1134-1137`, `--scritture` con
default `SCRITTURE_SHARDING`, e `scenari.py:1123-1124` lo gira a `corsa.esegui(copione.scritture)`
senza `finche`. Con un limite di conteggio il numero è determinato: `_ordini` produce esattamente
`quante` ordini, perché la scadenza è `None` (conteggio e durata si escludono a vicenda,
`workload.py:418`) e `finche` non arriva — è la sola scena del failover a usarlo
(`scenari.py:750-754`). E ogni `_scrivi` contribuisce esattamente 1 a `riuscite + fallite`: o esce
con un `WriteSucceeded`, o si arrende dopo l'ultimo tentativo (`workload.py:712-758`), e `fallite
= cadute - ritentate` conta le rese, non i tentativi (`workload.py:507-514`). Quindi `scritture ==
N` per costruzione, in tutte e due le corse, sempre.

Il che vuol dire che nella scena spedita `confrontabile` è **sempre vero**, e le tre righe che
dicono «non è lo stesso carico» (`rapporto.py:547-551`) sono codice che nessuno vedrà mai
eseguire. Non è una guardia troppo larga: è una guardia morta.

**E la prova che dovrebbe accorgersene fa il contrario.** `test_scenari.py:990-999` copre il ramo
falso con `_esito_sharding(scritte_intera=5, scritte_sparsa=3)`: due numeri diversi messi a mano
in un doppio, cioè uno stato che la scena vera non sa produrre. La prova è verde, il ramo è
coperto, e la copertura non dice niente — è esattamente il caso di
[ADR-0124](../Decision.md#adr-0124), «un doppio più ubbidiente dell'originale non prova niente»,
qui nella variante speculare: un doppio *meno vincolato* dell'originale, che raggiunge stati che
il codice reale esclude.

**Rimedio: quello proposto, che è anche a portata di mano.** `Riepilogo` porta già
`documenti_confermati`; la guardia diventa un confronto fra quelli, e il bilancio mostra `fallite`
delle due corse invece di tacerle. La prova va rifatta partendo da una corsa vera con un archivio
che cade, come quella qui sopra, non da un `_esito_sharding` con due numeri scelti.

**Non è un blocco per il 18 settembre**, e va detto perché non lo è: sul palco lo sharding gira
contro uno stack sano, le rese non ci sono, e i due numeri combaciano davvero. Il difetto è che
combaciano *comunque* — se qualcosa andasse storto in scena, il rapporto direbbe «stesso carico»
proprio nel momento in cui non lo è.

## G-2 — Percorso del file temporaneo prevedibile e insicuro

*Sollevato da Gemini Pro (agy).*

- **Categoria:** security
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** app/src/mongolab/cli.py

**Evidenza citata dal revisore:**

```
DESTINAZIONE_DUMP: Final = Path("/tmp/mongolab-backup")
```

**Perché sarebbe un problema:** L'utilizzo di un percorso fisso e prevedibile sotto `/tmp` per i backup espone al rischio di attacchi (es. symlink attack o pre-creazione), compromettendo potenzialmente i dati o l'esecuzione dello strumento.

**Rimedio proposto:** Utilizzare funzioni sicure come `tempfile.TemporaryDirectory` per generare dinamicamente un percorso univoco e con permessi restrittivi.

### Verdetto

**Accolto in parte sul meccanismo, respinto il rimedio, e con un'osservazione che il revisore non
poteva vedere.** Il rilievo è scritto come se `/tmp/mongolab-backup` stesse sull'host. Non ci sta.

**Dove sta davvero quel percorso.** `DESTINAZIONE_DUMP` non viene mai aperto dal processo Python:
diventa l'argomento `--out` di un `mongodump` che gira **dentro il nodo**, per la via
`comandi.dentro(nodo, "mongodump")` → `docker compose exec` (`regia.py:120-132`,
`cli.py:438-447`). La docstring lo dice in prima riga — «Dove il dump atterra, **dentro il nodo**
in cui `mongodump` gira» (`cli.py:187`) — e la misura lo conferma: sull'host il percorso non
esiste, dentro il container sì.

```
$ ls -ld /tmp/mongolab-backup                       # host
ls: /tmp/mongolab-backup: No such file or directory

$ docker exec mongo-rs-1 ls -la /tmp                # container
drwxrwxrwt 1 root    root    4096 Sep  6 12:55 .
srwx------ 1 mongodb mongodb    0 Sep  6 10:30 mongodb-27017.sock
drwxr-xr-x 4 root    root    4096 Sep  6 12:55 mongolab-backup
```

**Perciò il rimedio proposto non si può applicare: romperebbe la funzione.** `tempfile.Temporary
Directory()` crea una cartella **sull'host** e ne restituisce il percorso; quel percorso finirebbe
in `--out` di un comando che gira **altrove**, dove non esiste. Verificato:

```
$ mkdir -p /Users/.../tmp/finto-out-g2               # host
$ docker exec mongo-rs-1 ls -ld /Users/.../tmp/finto-out-g2
/bin/ls: cannot access '...': No such file or directory
```

`tempfile` è lo strumento giusto per un percorso locale. Questo non lo è.

**La metà che invece regge, ed è giusto scriverla.** Il meccanismo che il revisore descrive esiste
davvero, spostato dentro il container: `/tmp` è `drwxrwxrwt`, e il dump lo scrive **root** (la
cartella risulta `root root`, perché `docker compose exec` entra come root). Un processo non-root
può quindi piantare un collegamento e farci scrivere root attraverso. Riprodotto, con un nome di
prova:

```
$ docker exec -u 999 mongo-rs-1 ln -sfn /data/db /tmp/prova-g2-link
lrwxrwxrwx 1 mongodb mongodb 8 Sep  6 13:22 /tmp/prova-g2-link -> /data/db

$ docker exec mongo-rs-1 touch /tmp/prova-g2-link/prova-g2-scritto-da-root
-rw-r--r-- 1 root root 0 Sep  6 13:22 /data/db/prova-g2-scritto-da-root
```

**Ma chi sarebbe l'attaccante.** Dentro quel container gira **un solo** processo non-root:
`mongod`, PID 1, uid 999. Per piantare il collegamento bisogna già eseguire codice come `mongod` —
cioè possedere già per intero il dataset che il dump conterrebbe. Il guadagno è «scrivere file
come root dentro un container effimero, su una rete Compose privata, su un portatile, offline, per
la durata di una demo». Non è niente, ma non è «gravità media»: è un rafforzamento in profondità,
non una falla sfruttabile da chi non ha già vinto.

**L'osservazione che il revisore non poteva fare, ed è la più utile.** La docstring sceglie `/tmp`
perché «`/tmp` è scrivibile da chiunque» (`cli.py:193-195`). La misura dice che quella ragione
**non è quella operativa**: il dump lo scrive root, e root scrive dove vuole. Il vincolo vero da
rispettare è l'altro che la docstring difende, ed è buono: un percorso **fisso**, perché `demo
backup-live` e `demo restore` sono due comandi consecutivi e «un percorso da ricopiare fra l'uno e
l'altro è un percorso da sbagliare davanti alla sala».

**Rimedio, riscritto perché sia applicabile.** Tenere il percorso fisso e toglierlo dalla cartella
scrivibile-da-tutti: una costante come `/var/lib/mongolab-backup`, che dentro l'immagine di
MongoDB appartiene a root e che solo root può creare. È una riga di costante, non cambia niente
per chi guarda, conserva la proprietà che serve al palco, e chiude la finestra di pre-creazione.
La ragione scritta nella docstring va aggiornata insieme al valore, perché oggi motiva una scelta
con un fatto che non è quello vero.

Non è un blocco per il 18 settembre, e la priorità è bassa.

*Nota di igiene:* il collegamento di prova e il file scritto attraverso sono stati tolti; `/tmp`
del container è tornato com'era, e in `/data/db` non è rimasto niente.

## C-2 — I soggetti dei commit omettono sistematicamente l'ambito obbligatorio

*Sollevato da Codex (codex).* Probabilmente lo stesso rilievo di G-1.

- **Categoria:** congruita-commit
- **Gravità:** bassa
- **Confidenza:** alta
- **Dove:** 17fe481b e gli altri 18 commit del dossier

**Evidenza citata dal revisore:**

```
feat: lo scheletro dell'applicazione, e la regola che tiene il dominio pulito
```

**Perché sarebbe un problema:** Tutti i soggetti usano tipo: soggetto senza ambito, mentre la convenzione dichiarata richiede tipo(ambito): soggetto. Per i sorgenti revisionati la cartella di progetto è app.

**Rimedio proposto:** Aggiungere l'ambito ai messaggi; separare le modifiche a progetti diversi quando necessario per assegnare un ambito coerente.

### Verdetto

**Respinto sul merito · il difetto è nella skill.** È il quinto membro della stessa famiglia:
[G-1](#g-1--messaggi-di-commit-privi-dellambito-obbligatorio) qui sotto, e G-2 e C-1 del fascicolo
`stack-docker`, e G-1 e C-1 del fascicolo `talk`. Il verdetto disteso sta lì e non lo ripeto: la
regola dell'ambito obbligatorio **non è di questo repository**, ma di quello da cui la skill di
revisione è stata importata, ed è finita nel prompt che abbiamo dato ai due recensori
(`.claude/skills/revisione-pr/prompt/revisione.md:12-13`).

La misura vale identica anche per i diciannove commit di questo fascicolo: zero soggetti con
ambito, su 156 in tutto `main..HEAD`. Non è una dimenticanza, è una convenzione diversa, mai
dichiarata da nessuna parte — ed è quest'ultima la cosa da correggere.

**Azione, che è nostra e non del codice:** correggere la riga del prompt, e scrivere la
convenzione di questo repository in una sede che oggi non esiste (non c'è né `CLAUDE.md` né
`CONTRIBUTING.md`). I messaggi già scritti restano come sono: riscrivere 156 soggetti per una
regola presa in prestito sarebbe il rimedio sbagliato al problema sbagliato.

## G-1 — Messaggi di commit privi dell'ambito obbligatorio

*Sollevato da Gemini Pro (agy).* Probabilmente lo stesso rilievo di C-2.

- **Categoria:** congruita-commit
- **Gravità:** bassa
- **Confidenza:** alta
- **Dove:** 17fe481b

**Evidenza citata dal revisore:**

```
feat: lo scheletro dell'applicazione, e la regola che tiene il dominio pulito
```

**Perché sarebbe un problema:** Le regole del repository richiedono che ogni commit indichi l'ambito corrispondente alla cartella di progetto toccata, ma tutti i messaggi forniti ne sono privi.

**Rimedio proposto:** Riscrivere i messaggi di commit inserendo l'ambito (es. `feat(app): ...`) per conformarsi alle regole sui Conventional Commits.

### Verdetto

**Respinto sul merito · il difetto è nella skill.** Stesso rilievo di
[C-2](#c-2--i-soggetti-dei-commit-omettono-sistematicamente-lambito-obbligatorio), sollevato
dall'altro recensore, e stesso verdetto: l'ambito obbligatorio è una regola del repository da cui
la skill di revisione è stata importata, non di questo, e ci è arrivata attraverso il prompt
(`.claude/skills/revisione-pr/prompt/revisione.md:12-13`).

Che due modelli indipendenti abbiano sollevato la stessa cosa non è una conferma del rilievo: è la
conferma che il prompt diceva a tutti e due la stessa cosa sbagliata. Vale la pena notarlo, perché
è il modo in cui una revisione esterna può sembrare concorde e non esserlo — concordano
sull'input, non sull'evidenza.

