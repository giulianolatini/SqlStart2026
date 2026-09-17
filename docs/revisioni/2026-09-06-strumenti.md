# Revisione della PR #strumenti — foglio di triage

Prodotto da `.claude/skills/revisione-pr/scripts/revisione.sh`. I rilievi arrivano da due revisori esterni e **non sono ancora un giudizio**: lo diventano quando ogni scheda ha un verdetto motivato scritto sotto.

**18 rilievi** — Codex (codex): 10, Gemini Pro (agy): 8.

| ID | Gravità | Confidenza | Categoria | Titolo | Verdetto |
|---|---|---|---|---|---|
| C-3 | alta | alta | security | Lo smoke può lasciare sugli shard un amministratore con password pubblica | accolto |
| C-4 | alta | alta | altro | I reset possono cancellare i volumi di un progetto diverso da quello fermato | accolto |
| G-2 | alta | alta | security | Possibile shell injection tramite interpolazione di stringhe nel Makefile | accolto |
| C-10 | media | alta | altro | Gli errori di avvio della regia saltano la terminazione controllata della scena | accolto |
| C-2 | media | alta | congruita-commit | Diversi commit classificati docs o test introducono comportamento operativo | accolto in parte |
| C-5 | media | alta | altro | reset-01 esegue il comando vietato dal perimetro di revisione | respinto |
| C-6 | media | alta | altro | Il preflight tenta un download proprio quando manca l'immagine | accolto |
| C-7 | media | alta | altro | reset-demo dichiara riuscite pulizie e verifiche dei dati che possono essere fallite | accolto |
| C-8 | media | alta | altro | La distribuzione del reset è approvata anche con uno shard vuoto | accolto |
| C-9 | media | alta | altro | Il preflight considera del laboratorio qualsiasi container che occupi una porta | accolto |
| G-3 | media | alta | security | Variabile d'ambiente non quotata soggetta a word splitting | accolto |
| G-4 | media | alta | security | Credenziale di prova inserita in chiaro nel codice versionato | respinto |
| G-5 | media | alta | congruita-commit | Downgrade di versione MongoDB mascherato da commit documentale | accolto in parte |
| G-7 | media | alta | congruita-commit | Rottura di compatibilità operativa non dichiarata sull'isolamento credenziali | respinto |
| G-8 | media | media | security | Uso di percorso temporaneo statico e altamente prevedibile | respinto |
| C-1 | bassa | alta | congruita-commit | I commit omettono sistematicamente l'ambito richiesto | respinto |
| G-1 | bassa | alta | congruita-commit | I messaggi di commit omettono sistematicamente l'ambito obbligatorio | respinto |
| G-6 | bassa | alta | congruita-commit | Modifica di feature e correzione di difetto slegato accorpati nello stesso commit | accolto, non riscritto |

## C-3 — Lo smoke può lasciare sugli shard un amministratore con password pubblica

*Sollevato da Codex (codex).*

- **Categoria:** security
- **Gravità:** alta
- **Confidenza:** alta
- **Dove:** tools/smoke-sharded.sh, blocchi eccezione ed eccezione2

**Evidenza citata dal revisore:**

```
try { db.getSiblingDB("admin").createUser({user: "smoke-non-deve-esistere", pwd: "x", roles: [{role: "root", db: "admin"}]}); print("CREATO"); }
```

**Perché sarebbe un problema:** Se il difetto cercato è presente, la prova crea davvero un utente root con password nota e si limita a segnalare l'errore. Non esiste una pulizia successiva: il controllo trasforma la condizione vulnerabile in una credenziale persistente e pubblica.

**Rimedio proposto:** Preferire una verifica non persistente oppure usare una credenziale temporanea casuale e garantire la rimozione dell'utente anche sui percorsi di errore, verificandone l'assenza.

### Verdetto

**Accolto, con la causa corretta.** Il rilievo è giusto: se l'eccezione localhost fosse aperta,
la sonda creava davvero un `root` e non lo toglieva. La causa proposta — «il `dropUser` potrebbe
fallire» — è invece sbagliata, e la differenza cambia il rimedio. Misurato su container usa-e-getta
con `--auth` e zero utenti: `dropUser` **riesce**. A fallire era la verifica, con `Unauthorized`,
perché togliendo l'utente con cui ci si è autenticati si perdono nello stesso istante i privilegi
per guardare se è andato via.

Corretto in `tools/smoke-sharded.sh`: password casuale invece che `x`, rimozione autenticandosi con
quella, e verifica da una **connessione nuova** — la prova che una credenziale non c'è più è che non
apre più. I due blocchi gemelli diventano una funzione sola. Provata sui due casi per cui esiste:
porta aperta su container usa-e-getta (`TOLTO`, e la credenziale non apre più), porta chiusa su
`sh-shard1a` (`Unauthorized`, niente creato).

Dalla misura è uscito un fatto che nessuno dei due revisori aveva previsto e che cambia il consiglio
operativo: **l'eccezione localhost è un fermo di processo**. Si chiude alla creazione del primo
utente e resta chiusa per la vita di quel `mongod` anche se poi gli utenti vengono tolti tutti; si
riapre al riavvio. Un residuo va quindi tolto **prima** del riavvio del nodo.

Schede: [V-102](../Sources.md#v-102), [ADR-0133](../Decision.md#adr-0133).

## C-4 — I reset possono cancellare i volumi di un progetto diverso da quello fermato

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** alta
- **Confidenza:** alta
- **Dove:** Makefile, target reset-02 e reset-03

**Evidenza citata dal revisore:**

```
PROGETTO_02 := sqlstart-02-replicaset
DATI_02 := $(PROGETTO_02)_dati-1 $(PROGETTO_02)_dati-2 $(PROGETTO_02)_dati-3
```

**Perché sarebbe un problema:** Compose può selezionare un progetto tramite COMPOSE_PROJECT_NAME, mentre i nomi passati a docker volume rm restano fissi. Con un progetto alternativo attivo e i volumi del progetto canonico inutilizzati, il reset ferma il primo e cancella i dati del secondo.

**Rimedio proposto:** Vincolare esplicitamente il progetto Compose e ricavare i volumi dal medesimo progetto, verificando le etichette di appartenenza prima della cancellazione.

### Verdetto

**Accolto.** Misurato: `COMPOSE_PROJECT_NAME` nell'ambiente di chi lancia `make` passa davanti al
`name:` dei file Compose. Con la variabile impostata, `config` risolve il nome dell'ambiente e `ps`
elenca **niente** mentre i tre membri dello stack 02 sono accesi; un `down` lì dentro sarebbe un
nulla di fatto che esce 0. Il danno che il rilievo descrive è reale e ha la forma esatta che dice:
`reset-02` cancella i volumi per nome letterale, costruito da `PROGETTO_02`, dopo un `down` che non
ha smontato niente.

Corretto: ogni invocazione di `docker compose` nel Makefile porta `-p`, che ha la precedenza
sull'ambiente. Verificato nello stesso ambiente ostile: `config` risolve `sqlstart-02-replicaset` e
`ps` elenca i tre membri.

Schede: [V-098](../Sources.md#v-098), [ADR-0129](../Decision.md#adr-0129).

## G-2 — Possibile shell injection tramite interpolazione di stringhe nel Makefile

*Sollevato da Gemini Pro (agy).*

- **Categoria:** security
- **Gravità:** alta
- **Confidenza:** alta
- **Dove:** Makefile

**Evidenza citata dal revisore:**

```
@$(COMPOSE_03_BASE) config --profiles | grep -qx '$(PROFILO)' || { \
```

**Perché sarebbe un problema:** La variabile proveniente dall'input dell'utente viene interpolata in un comando shell direttamente tra apici singoli. Un utente può fornire un valore contenente un apice singolo (es. `palco'; comando; '`) per evadere il controllo ed eseguire comandi shell arbitrari sul sistema.

**Rimedio proposto:** Passare il valore in modo sicuro tramite l'ambiente o quotare correttamente, ad esempio esportandola prima ed eseguendo `grep -qx "$$PROFILO"`.

### Verdetto

**Accolto, e il difetto era doppio.** L'interpolazione del valore nel testo della shell c'era, ed è
stata tolta: il valore arriva alla guardia per **ambiente**, e il confronto è
`grep -qxF -- "$PROFILO"`. Verificato: `PROFILO="palco'; echo IRRUZIONE; #"` esce dalla guardia come
dato, finisce intero nel messaggio d'errore, e `IRRUZIONE` non compare da nessuna parte.

Sulla stessa riga c'era un secondo difetto che nessuno dei due revisori ha visto, e che la misura ha
trovato: `grep -qx` tratta ciò che riceve come **espressione regolare**. Isolato dal contesto,
`grep -qx -- 'palco[ ]*'` su `completo palco strumenti` risponde **0** — valido — mentre `grep -qxF`
risponde **1**. Una guardia che accetta `palco[ ]*` accetta una famiglia infinita di stringhe che
poi arrivano a Compose come nomi letterali, dove non corrispondono a niente. `-F` chiude anche
questo.

Le tre parti del rimedio fanno tre cose diverse e servono tutte: l'ambiente toglie il valore dalla
sintassi, `-F` gli toglie il significato di regex, `--` gli toglie la possibilità di sembrare
un'opzione.

Schede: [V-099](../Sources.md#v-099), [ADR-0130](../Decision.md#adr-0130).

## C-10 — Gli errori di avvio della regia saltano la terminazione controllata della scena

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** tools/registra-terminale.py, seconda_finestra

**Evidenza citata dal revisore:**

```
esito = subprocess.run(shlex.split(riga), capture_output=True, text=True)
```

**Perché sarebbe un problema:** Un eseguibile annunciato assente o non eseguibile solleva OSError anziché restituire un codice; una riga con virgolette incomplete solleva ValueError. Entrambi i casi saltano ferma_la_scena e il ritorno 125, lasciando la pulizia del processo e dello pseudo-terminale fuori dal percorso garantito.

**Rimedio proposto:** Gestire gli errori di parsing e avvio come fallimenti della regia e racchiudere il ciclo di registrazione in una pulizia garantita che termini e raccolga il figlio.

### Verdetto

**Accolto, e il danno era più grave di come è descritto.** Il rilievo parla di terminazione
controllata saltata. Misurato contro la copia pre-rimedio: le conseguenze sono **tre**, e la terza è
la peggiore. Uscita **1** invece di 125; un `Traceback` intero sullo schermo; e sul disco un `.cast`
di **192 byte** che contiene la riga di regia e nessun marcatore — un file con l'estensione giusta e
l'intestazione giusta, che chi lo trova più tardi non distingue da una registrazione riuscita se non
aprendolo.

Corretto: `ValueError` da `shlex.split` e `OSError` da `subprocess.run` diventano `REGIA_FALLITA`,
con il nome del guasto e senza traceback. 125 non è forma: è il solo codice che distingue «è fallita
la regia» da «è fallito il comando registrato», e la prima si ripara nel copione, la seconda no. Due
prove nuove, viste rosse contro `HEAD` prima di essere verdi: la suite di `tools` passa da 181 a
183.

Una non-modifica è deliberata: il `.cast` continua a essere scritto. L'uscita 125 e la riga di
riepilogo raccontano già che quel file non è una registrazione riuscita, e il file è la sola prova
di che cosa la regia abbia provato a fare. L'ambiguità si toglie dicendola, non cancellando la
prova.

Schede: [V-103](../Sources.md#v-103), [ADR-0132](../Decision.md#adr-0132).

## C-2 — Diversi commit classificati docs o test introducono comportamento operativo

*Sollevato da Codex (codex).*

- **Categoria:** congruita-commit
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** aac3106d, 1b92a796, eb3c54a1, bd0a0913

**Evidenza citata dal revisore:**

```
Nascono tools/demo-sharded.sh e tre bersagli nel Makefile — stato-03,
distribuzione-03, guasto-03 — che servono in sala prima che qui dentro.
```

**Perché sarebbe un problema:** Il commit 1b92a796 è classificato docs ma introduce strumenti che fermano e riavviano container. Analogamente, gli altri commit indicati dichiarano implementazioni di controlli o correzioni funzionali sotto tipi docs o test: il corpo le racconta, ma la classificazione della cronologia resta errata.

**Rimedio proposto:** Usare feat o fix per le modifiche operative; separare la documentazione quando costituisce un cambiamento indipendente.

### Verdetto

**Accolto in parte, e la parte accolta ha aperto la sede che mancava.** Dei quattro commit citati
uno è fuori discussione: `1b92a79`, tipo `docs:`, crea `tools/demo-sharded.sh` — 361 righe, uno
strumento nuovo — e tre bersagli del Makefile che fermano e riavviano container. Lo scopo di quel
lavoro non è documentare: è dare alla sala tre comandi che prima non c'erano. Doveva essere `feat:`.

Gli altri tre reggono peggio l'accusa. `b72510f` cambia dieci righe di uno script e dieci di un file
di init accanto a quattro pagine riscritte, e lo scopo dichiarato — riallineare pagine che una
decisione aveva reso false — è quello vero. `eb3c54a` e `bd0a091` sono chiusure di lavoro e
arbitrati di review, che sono documentazione per definizione.

Il rilievo però poggiava su una convenzione che questo repository non aveva mai scritto, e questa è
la parte che valeva più della singola classificazione. La sede ora esiste:
[ADR-0134](../Decision.md#adr-0134) fissa che **il tipo segue lo scopo del lavoro, non il tipo di
file toccato**, e — caso limite trovato proprio da questa review — che quando un commit registra una
decisione **e la applica** in modo che cambi ciò che il lab esegue, il tipo segue l'effetto su chi
esegue.

La storia non viene riscritta: `release/1.0` è pubblicata, e riscrivere commit già spinti costa più
di quanto valga la classificazione di quattro di essi. La regola vale da qui in avanti.

Schede: [V-104](../Sources.md#v-104), [ADR-0134](../Decision.md#adr-0134).

## C-5 — reset-01 esegue il comando vietato dal perimetro di revisione

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** Makefile, target reset-01

**Evidenza citata dal revisore:**

```
$(COMPOSE_01) down -v
```

**Perché sarebbe un problema:** Il dossier vieta esplicitamente docker compose down -v su questi stack, ma il target lo esegue. Il compose dello standalone non è incluso, quindi non è dimostrabile che qui venga cancellato un keyfile; la violazione del vincolo operativo è comunque esplicita.

**Rimedio proposto:** Fermare lo stack senza -v e cancellare esclusivamente i volumi dati identificati e verificati.

### Verdetto

**Respinto, e la misura dice perché.** Il rilievo chiede di nominare i volumi anche in `reset-01`,
come fa `reset-02`. Sarebbe il rimedio sbagliato: `reset-01` è `down -v`, e `-v` **segue la
selezione del progetto**. Nell'ambiente ostile di [C-4](#c-4--i-reset-possono-cancellare-i-volumi-di-un-progetto-diverso-da-quello-fermato) `reset-01` non cancella niente — cioè
sbaglia per difetto, e per difetto non fa danno. È `reset-02`, che nomina i volumi, a cancellarli
per nome letterale mentre il `down` che avrebbe dovuto smontarli prima non ha fatto niente.

Nominare i volumi in `reset-01` lo porterebbe **dentro** il difetto invece di toglierlo. Il rimedio
giusto per entrambi è un altro, ed è quello applicato: fissare il progetto con `-p`.

Schede: [V-098](../Sources.md#v-098), [ADR-0129](../Decision.md#adr-0129).

## C-6 — Il preflight tenta un download proprio quando manca l'immagine

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** tools/preflight.sh, verifica di avvio dell'immagine MongoDB

**Evidenza citata dal revisore:**

```
elif esito_avvio="$(docker run --rm --entrypoint mongod "${immagine_mongo}" --version 2>&1)"; then
```

**Perché sarebbe un problema:** Il preflight continua dopo il fallimento della verifica della cache. Questa invocazione docker run non impone --pull=never: se l'immagine manca, tenta di recuperarla dalla rete, violando il vincolo offline e introducendo un'attesa davanti alla sala.

**Rimedio proposto:** Aggiungere --pull=never alla sonda e distinguere l'immagine assente da quella presente ma non eseguibile.

### Verdetto

**Accolto.** Misurato con l'immagine assente: senza `--pull=never` il comando impiega **1,011 s** e
nel mezzo fa una richiesta a `docker.io`; con la flag risponde «No such image» in **0,023 s** e non
esce dalla macchina.

Quello che il rilievo non dice, e che è la ragione per cui pesa: il preflight esiste per una scena
sola — la sala, mezz'ora prima del talk, senza rete — e il caso da diagnosticare, «le immagini non
ci sono», è esattamente il caso in cui la sonda andava a chiederle alla rete che non c'è. La misura
di 1,011 s è stata presa con la rete funzionante, quindi **sottostima** il danno che descrive: in
sala quel ramo dura quanto il timeout di un client verso un server irraggiungibile.

Corretto: `--pull=never`. Il preflight ora è dicibile in una frase — «non esce dalla macchina» — ed
è una proprietà che si può promettere a chi lo lancia.

Schede: [V-100](../Sources.md#v-100), [ADR-0131](../Decision.md#adr-0131).

## C-7 — reset-demo dichiara riuscite pulizie e verifiche dei dati che possono essere fallite

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** tools/reset-demo.sh, blocchi collezioni, ripristino e impronta

**Evidenza citata dal revisore:**

```
ok "collezioni rimosse: ${tolte:-nessuna}"

  titolo "Il database che il ripristino costruisce"
```

**Perché sarebbe un problema:** Gli esiti delle interrogazioni di pulizia non vengono controllati: una chiamata fallita con output vuoto diventa «nessuna», e il drop del database può essere annunciato come riuscito con nome vuoto. Anche l'impronta viene soltanto stampata con ok, senza confrontarla con i valori attesi, permettendo un verdetto finale positivo con residui o dati errati.

**Rimedio proposto:** Controllare lo stato di ogni interrogazione, verificare dopo la pulizia che i bersagli siano assenti e confrontare l'impronta con quella attesa prima di dichiarare il ripristino riuscito.

### Verdetto

**Accolto.** Le tre pulizie toglievano le collezioni e poi annunciavano che erano state tolte, senza
rileggere; l'impronta dei dati caricati veniva confrontata con numeri scritti **in un commento**,
cioè con niente.

Corretto: dopo la rimozione si rilegge `getCollectionNames()`, e le risposte possibili sono **tre** —
quelle andate via, `RESIDUI:` con i nomi di quelle rimaste, e la risposta vuota, che è il terzo caso
e prima non esisteva: un'interrogazione che non risponde non è una pulizia riuscita. I numeri attesi
diventano due costanti, `IMPRONTA_50K` e `IMPRONTA_20K`, e il confronto stampa atteso e ottenuto
quando divergono.

La nota di metodo che ne è uscita vale oltre questo script: **un valore atteso scritto in un
commento non è una verifica, è una speranza documentata.**

Schede: [V-101](../Sources.md#v-101), [ADR-0132](../Decision.md#adr-0132).

## C-8 — La distribuzione del reset è approvata anche con uno shard vuoto

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** tools/reset-demo.sh, verifica finale dello stack 03

**Evidenza citata dal revisore:**

```
if [[ "${distribuzione}" == *" "* ]]; then
    ok "documenti su entrambi gli shard: ${distribuzione}"
```

**Perché sarebbe un problema:** La presenza di uno spazio dimostra soltanto che l'output contiene più parole. Una risposta come shard1rs=20000 shard2rs=0 passa e dichiara documenti su entrambi gli shard, proprio il difetto che questa verifica dovrebbe intercettare.

**Rimedio proposto:** Interpretare i conteggi, richiedere i due shard attesi e verificare che entrambi contengano documenti.

### Verdetto

**Accolto, e il caso è stato costruito davvero.** Il controllo che distingue uno sharded cluster da
un replica set travestito cercava **uno spazio** nella risposta. La risposta `shard1rs=0
shard2rs=5` uno spazio ce l'ha: un chunk vuoto su uno shard e cinque documenti sull'altro passavano
per «documenti su entrambi gli shard».

Il caso non è stato immaginato: è stato costruito su un database usa-e-getta spostando un chunk
vuoto sul secondo shard, e la prima stesura del controllo l'ha dichiarato verde davanti alla misura.

Corretto: si contano i token `nome=numero` e si chiedono due cose insieme — almeno due shard letti,
e tutti con documenti. Il riconoscitore è stato provato **staccato dallo script**, su cinque casi:
passa solo `shard1rs=10000 shard2rs=10000`; sono errori il falso verde originale, un solo shard, una
risposta vuota e un testo libero di errore. Provarlo in isolamento è ciò che ha reso possibile
costruire casi che sullo stack vero non si sanno provocare senza rompere qualcosa.

Schede: [V-101](../Sources.md#v-101), [ADR-0132](../Decision.md#adr-0132).

## C-9 — Il preflight considera del laboratorio qualsiasi container che occupi una porta

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** tools/preflight.sh, controllo delle porte

**Evidenza citata dal revisore:**

```
porte_dei_container="$(docker ps --format '{{.Ports}}' 2>/dev/null || true)"
```

**Perché sarebbe un problema:** La lista comprende tutti i container del demone, senza verificarne il progetto. Un container estraneo che pubblica una porta del laboratorio viene quindi accettato come parte del lab, e il successivo avvio fallisce per porta occupata dopo un preflight verde.

**Rimedio proposto:** Associare ogni porta al container proprietario e verificarne progetto e servizio tramite le etichette Compose.

### Verdetto

**Accolto.** Il filtro `label=com.docker.compose.project` seleziona **ogni** container avviato da
Compose sul demone, non i tre progetti di questo repository. Su una macchina di sviluppo con altri
stack accesi il preflight annunciava porte occupate che nessun bersaglio di questo `make` avrebbe
mai chiesto, e non aveva modo di dire quale delle proprie porte fosse davvero contesa.

Corretto come propone il rilievo: il conteggio guarda i container dei tre progetti del lab. Questo
crea però una seconda copia di una verità che vive nel Makefile, ed è un debito che va pagato subito
o non si paga più: la tiene onesta `test_il_preflight_conosce_i_progetti_del_makefile`, che legge i
due elenchi dai due file e li confronta. I due lettori sono stati verificati sui valori veri —
restituiscono entrambi i tre nomi — così la prova non passa a vuoto su due liste vuote.

Resta fuori portata, e va detto: una porta occupata da un processo che non è un container il
preflight non la vede. Quella la vede solo chi prova ad aprirla.

Schede: [V-100](../Sources.md#v-100), [ADR-0131](../Decision.md#adr-0131).

## G-3 — Variabile d'ambiente non quotata soggetta a word splitting

*Sollevato da Gemini Pro (agy).*

- **Categoria:** security
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** Makefile

**Evidenza citata dal revisore:**

```
PROFILO=$(PROFILO) ./tools/smoke-sharded.sh
```

**Perché sarebbe un problema:** L'assegnazione della variabile omette l'utilizzo dei doppi apici protettivi. Qualora l'input contenga spazi bianchi, la shell avvierà un word splitting, alterando i comandi e passando argomenti imprevisti allo script.

**Rimedio proposto:** Racchiudere sempre l'assegnazione di variabili che dipendono da input tra doppie virgolette: `PROFILO="$(PROFILO)" ./tools/smoke-sharded.sh`.

### Verdetto

**Accolto nel rimedio, non nella diagnosi.** Il word splitting descritto dal rilievo è reale — un
valore con uno spazio si spezzava in due parole — ma è il meno grave dei problemi di quella riga, e
metterlo a fuoco da solo avrebbe prodotto un rimedio insufficiente: le virgolette proposte
proteggono dallo spazio e non dall'apice, che chiude comunque la stringa, né dal metacarattere, che
`grep -qx` interpreta comunque.

Il rimedio applicato copre tutti e tre: il valore arriva per ambiente — così non è più dentro la
sintassi — e il confronto è `grep -qxF --`. È lo stesso rimedio di [G-2](#g-2--possibile-shell-injection-tramite-interpolazione-di-stringhe-nel-makefile), e i due rilievi si
chiudono insieme perché sono la stessa riga vista da due angoli.

Schede: [V-099](../Sources.md#v-099), [ADR-0130](../Decision.md#adr-0130).

## G-4 — Credenziale di prova inserita in chiaro nel codice versionato

*Sollevato da Gemini Pro (agy).*

- **Categoria:** security
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** Makefile

**Evidenza citata dal revisore:**

```
--variabile PASSWORD_AMMINISTRATORE=valore-finto-il-controllo-non-si-collega
```

**Perché sarebbe un problema:** Sebbene dichiarata come finta a scopi di test statico, la registrazione di password o segreti in chiaro nel codice versionato vìola palesemente le policy sulla gestione delle credenziali documentate (segreti mai in chiaro).

**Rimedio proposto:** Gestire il segreto di test senza scriverlo in chiaro nel Makefile, ad esempio delegando la generazione al file `.env` locale ignorato o passando un fallback da shell esterna.

### Verdetto

**Respinto.** Il valore non è una credenziale. È una sentinella che dichiara a voce alta di essere
finta — `valore-finto-il-controllo-non-si-collega` — e non raggiunge mai un `mongod`, perché
`check_stack.py` legge i file Compose e non avvia niente ([ADR-0042](../Decision.md#adr-0042)).

Esiste per una ragione precisa, già scritta nel commento sopra la riga: lo stack 02 dichiara la
password nella forma `${PASSWORD_AMMINISTRATORE:?...}`, e il file che la porta è fuori dal
repository per scelta ([ADR-0014](../Decision.md#adr-0014)). Su un clone appena fatto quel file non
esiste, e senza un valore qui `make stack-check` si fermerebbe prima di guardare una sola regola.

Il rimedio proposto — delegare al `.env` locale ignorato — riporterebbe esattamente il problema che
questa riga risolve: renderebbe `stack-check` ineseguibile proprio su un clone pulito, che è dove
serve di più. La policy che il rilievo invoca vieta i **segreti** in chiaro; una stringa che non
apre niente e lo dice nel proprio nome non è un segreto.

Nessuna modifica.

## G-5 — Downgrade di versione MongoDB mascherato da commit documentale

*Sollevato da Gemini Pro (agy).*

- **Categoria:** congruita-commit
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** 9154ad8c

**Evidenza citata dal revisore:**

```
make images-pull ha ripinnato l'immagine sul digest della 7.0.40
```

**Perché sarebbe un problema:** Il commit altera attivamente l'infrastruttura e il comportamento dello stack scaricando una versione di MongoDB differente (downgrade). Il tipo `docs:` nasconde una modifica architetturale sotto la promessa di una modifica solo documentale.

**Rimedio proposto:** Applicare un tipo adeguato (es. `fix:` o `chore:`) per l'aggiornamento dei pin operativi delle immagini scaricate.

### Verdetto

**Accolto sul tipo, respinto sull'accusa di mascheramento.** Il commit `9154ad8` è `docs:` e cambia
il digest dell'immagine in `tools/images.env`: sotto la regola che questa review ha reso esplicita —
il tipo segue l'effetto su chi esegue — doveva essere `chore:`. Su questo il rilievo ha ragione.

«Mascherato» però non regge alla lettura. Il soggetto del commit è «ADR-0028 accettata, **il lab
passa a MongoDB 7.0.40**»: la versione nuova è nel titolo, non nel corpo e non nel diff. Chi cerca
nella storia quando è cambiata la versione la trova alla prima riga. E il passaggio non è una
regressione silenziosa ma una decisione registrata: [ADR-0028](../Decision.md#adr-0028) supera
[ADR-0008](../Decision.md#adr-0008) con il motivo scritto — sul kernel della VM di Docker Desktop
nessuna 8.0 pubblicata si avvia, e la patch che lo risolve esiste nel changelog ma non in
distribuzione.

Il rilievo poggiava su una convenzione mai scritta. Ora è scritta, e questo caso limite è entrato
nella scheda proprio perché la review lo ha trovato: quando un commit registra una decisione **e la
applica** in modo che cambi ciò che il lab esegue, il tipo segue l'effetto. La storia non viene
riscritta.

Schede: [V-104](../Sources.md#v-104), [ADR-0134](../Decision.md#adr-0134).

## G-7 — Rottura di compatibilità operativa non dichiarata sull'isolamento credenziali

*Sollevato da Gemini Pro (agy).*

- **Categoria:** congruita-commit
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** b72510f4

**Evidenza citata dal revisore:**

```
Lo smoke test perde l'invariante che le credenziali del cluster non aprissero uno shard — vera fino a ieri, falsa per costruzione da adesso
```

**Perché sarebbe un problema:** L'alterazione costruttiva che rompe una garanzia di isolamento del cluster è un cambiamento netto della sicurezza e introduce un breaking change. Il commit omette ogni avviso visibile (es. `!`) della rottura di retrocompatibilità.

**Rimedio proposto:** Aggiungere il suffisso `!` al tipo (`feat!:`) o includere un avviso `BREAKING CHANGE:` nel corpo finale del commit.

### Verdetto

**Respinto come rottura di compatibilità, accolto come lacuna di una convenzione mancante.** La
notazione `!` e `BREAKING CHANGE:` che il rilievo chiede appartengono a Conventional Commits nella
forma completa, che questo repository non ha mai adottato — e non l'aveva scritto da nessuna parte,
il che rende il rilievo legittimo e la sua conclusione inapplicabile.

Nel merito: ciò che cambia non è un'interfaccia verso consumatori esterni. È l'invariante di una
prova di smoke, in un laboratorio didattico che non ha utenti a valle. Un `BREAKING CHANGE:` in
quel commit avvertirebbe chi non esiste. Il posto dove quel cambiamento va raccontato — e dove è
raccontato — è la scheda di decisione che lo motiva.

[ADR-0134](../Decision.md#adr-0134) chiude la lacuna dichiarando che cosa questo repository usa:
`tipo: soggetto`, cinque tipi, senza ambito e senza le notazioni di rottura, perché non c'è
compatibilità pubblica da rompere. Se e quando ce ne sarà — al momento della pubblicazione del
repository — sarà una modifica a quella scheda.

Schede: [V-104](../Sources.md#v-104), [ADR-0134](../Decision.md#adr-0134).

## G-8 — Uso di percorso temporaneo statico e altamente prevedibile

*Sollevato da Gemini Pro (agy).*

- **Categoria:** security
- **Gravità:** media
- **Confidenza:** media
- **Dove:** 61056324

**Evidenza citata dal revisore:**

```
/tmp/mongolab-backup sta dentro mongo-rs-1 e non e' ne' un database ne' un volume
```

**Perché sarebbe un problema:** L'utilizzo di un percorso temporaneo hardcoded ed estremamente prevedibile espone al rischio di abusi come file hijacking o conflitti sebbene il danno sia limitato dall'ambiente isolato del container; viola lo sviluppo sicuro sui file temporanei.

**Rimedio proposto:** Usare directory temporanee sicure generate dinamicamente, ad esempio tramite il comando standard `mktemp -d`.

### Verdetto

**Respinto, con il modello di minaccia che non si applica.** `/tmp/mongolab-backup` è un percorso
**dentro il container `mongo-rs-1`**, non sull'host: chi lo cerca sul portatile non lo trova, e la
pagina che descrive la scena lo dice esplicitamente. Il rischio di *file hijacking* che il rilievo
invoca presuppone una `/tmp` condivisa fra utenti diversi; qui la `/tmp` appartiene a un container
monoprocesso che contiene un `mongod` e nient'altro, e sparisce con lui.

La prevedibilità del nome non è una svista ma una scelta già argomentata nel codice: `demo
backup-live` e `demo restore` sono due comandi consecutivi mostrati dal vivo, e un percorso da
ricopiare fra l'uno e l'altro è un percorso da sbagliare davanti alla sala. Chi ne vuole due li
nomina con `--out`, che esiste. `/tmp` e non `/data` perché dentro l'immagine `/data/db` è il volume
e il resto di `/data` appartiene a root.

`mktemp -d`, il rimedio proposto, produrrebbe un nome diverso a ogni esecuzione: renderebbe la scena
irripetibile e costringerebbe a leggere il percorso dall'output per passarlo al comando successivo —
cioè esattamente ciò che la scelta attuale evita.

Nessuna modifica.

## C-1 — I commit omettono sistematicamente l'ambito richiesto

*Sollevato da Codex (codex).* Probabilmente lo stesso rilievo di G-1.

- **Categoria:** congruita-commit
- **Gravità:** bassa
- **Confidenza:** alta
- **Dove:** 63684269 e gli altri commit del dossier

**Evidenza citata dal revisore:**

```
test: analisi degli ADR in check_citations
```

**Perché sarebbe un problema:** I soggetti non seguono la forma tipo(ambito): soggetto richiesta dal repository. L'assenza dell'ambito impedisce di identificare dalla cronologia il progetto interessato.

**Rimedio proposto:** Inserire l'ambito corrispondente alla cartella toccata, separando i cambiamenti indipendenti che coinvolgono progetti diversi.

### Verdetto

**Respinto — la premessa è falsa, e verificarla ha aperto la sede che mancava.** Il rilievo afferma
che il repository richiede la forma `tipo(ambito): soggetto`. Misurato sui 164 commit della storia:
l'ambito compare **zero volte su 159** commit convenzionali. Non è un'omissione sistematica, è
l'assenza sistematica di una cosa che non è mai stata richiesta.

Da dove venga l'affermazione è a sua volta un difetto trovato da questa review, e sta a monte del
rilievo: il prompt del revisore diceva «`tipo(ambito): soggetto`, ambito uguale al nome della
cartella di progetto». Quella è la convenzione del repository da cui la skill di revisione è stata
importata, non di questo. Il revisore ha applicato correttamente una regola sbagliata.

Corretto in due punti, e prima della prossima revisione, non dopo: il prompt ora dichiara la
convenzione di qui e dice esplicitamente che l'assenza di ambito **non è un rilievo**; la skill che
portava la tabella d'origine ora le affianca quella valida qui.

E la sede che mancava — dichiarata mancante da [ADR-0123](../Decision.md#adr-0123) — ora esiste:
[ADR-0134](../Decision.md#adr-0134), ricavata dalla storia invece che dichiarata.

Schede: [V-104](../Sources.md#v-104), [ADR-0134](../Decision.md#adr-0134).

## G-1 — I messaggi di commit omettono sistematicamente l'ambito obbligatorio

*Sollevato da Gemini Pro (agy).* Probabilmente lo stesso rilievo di C-1.

- **Categoria:** congruita-commit
- **Gravità:** bassa
- **Confidenza:** alta
- **Dove:** 63684269

**Evidenza citata dal revisore:**

```
test: analisi degli ADR in check_citations
```

**Perché sarebbe un problema:** Il repository impone l'uso dei Conventional Commits richiedendo obbligatoriamente l'ambito pari al nome della cartella toccata. Tutti i commit (compreso questo) omettono l'ambito, fallendo nella promessa di categorizzazione del lavoro.

**Rimedio proposto:** Includere l'ambito di pertinenza tra parentesi sùbito dopo il tipo in tutti i commit futuri (es. `test(tools): ...`).

### Verdetto

**Respinto, per la stessa ragione di [C-1](#c-1--i-commit-omettono-sistematicamente-lambito-richiesto), che è il medesimo rilievo.** Due revisori
indipendenti hanno prodotto lo stesso rilievo dallo stesso prompt, e la convergenza non è una
conferma: è la stessa premessa sbagliata letta due volte.

Vale però registrare una cosa che la coincidenza rende visibile. Quando due recensori concordano su
un punto che nessuno dei due poteva verificare — perché la convenzione non era scritta da nessuna
parte nel repository, solo nel prompt che li istruiva — l'accordo misura la fonte comune, non il
codice. È l'argomento più forte a favore di arbitrare **eseguendo**: `git log --format=%s` ha
risposto in un secondo a una domanda su cui due modelli si erano trovati d'accordo.

Schede: [V-104](../Sources.md#v-104), [ADR-0134](../Decision.md#adr-0134).

## G-6 — Modifica di feature e correzione di difetto slegato accorpati nello stesso commit

*Sollevato da Gemini Pro (agy).*

- **Categoria:** congruita-commit
- **Gravità:** bassa
- **Confidenza:** alta
- **Dove:** 5f0276b8

**Evidenza citata dal revisore:**

```
Il prefisso è feat: perché il commit porta anche il codice che rende possibili quelle misure [...] più la correzione di un difetto in tools/check_citations.py.
```

**Perché sarebbe un problema:** Il commit agglomera in un'unica traccia l'introduzione di funzionalità e un bugfix su uno strumento completamente slegato dalla logica originale, unendo modifiche che andrebbero separate per mantenere la storia chiara.

**Rimedio proposto:** Separare i due interventi disgiunti in due commit differenti: uno di `feat:` per il carico e uno di `fix:` per il bug in check_citations.py.

### Verdetto

**Accolto in linea di principio, chiuso senza modifica.** Il commit `5f0276b` porta insieme il
carico di misura e la correzione di un difetto in `tools/check_citations.py`, e sono due cose
scollegate: separarli sarebbe stato meglio, e il corpo del commit lo dice già a chi legge, il che
attenua ma non annulla.

Non si riscrive: `release/1.0` è pubblicata, e riscrivere un commit già spinto per migliorare la
granularità della storia costa più di quanto la granularità valga. La regola che discende dal
rilievo vale da qui in avanti ed è ora scritta:
[ADR-0134](../Decision.md#adr-0134) chiede che il commit faccia una cosa sola e che il corpo spieghi
il perché.

Va detto anche il limite di questo genere di rilievo: la separazione dei commit è una virtù che si
paga in attenzione, e in un lavoro dove una correzione emerge **mentre** si misura qualcos'altro la
scelta fra «due commit puliti» e «un commit che racconta come sono andate le cose» non è ovvia. Qui
la storia è più utile della pulizia, ed è la ragione per cui il rilievo è accolto in principio e non
in pratica.

Schede: [V-104](../Sources.md#v-104), [ADR-0134](../Decision.md#adr-0134).

