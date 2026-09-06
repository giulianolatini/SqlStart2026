# Registro operativo di sviluppo

Diario cronologico: cosa è stato fatto, cosa è fallito, cosa se ne è imparato. Una voce per
sessione, la più recente in fondo. Distinto da [`Decision.md`](Decision.md), che registra
le sole decisioni.

---

## 2026-08-24 — Brainstorming e design

**Fatto:** rilevazione dell'ambiente; esclusione di Apple `container` (V-001); design delle
tre architetture, dell'applicazione e dell'impianto documentale in
[`00-progetto/2026-08-24-design.md`](00-progetto/2026-08-24-design.md); diciassette ADR.

**Fallito:** il primo tentativo di usare Rancher Desktop come runtime — il binario `docker`
risolveva a Rancher mentre il contesto puntava al socket di Docker Desktop. Sostituito con
Docker Desktop; i residui in `~/.rd` restano un controllo del preflight.

**Imparato:** la VM Docker dispone di 7,65 GiB dei 16 dell'host. È il vincolo che ha
generato i due profili dello sharded cluster (ADR-0010).

---

## 2026-08-25 — Approvazione e fondamenta

**Fatto:** approvazione della specifica; ADR-0016 (filmati su YouTube con copia locale) e
ADR-0017 (il repository resta esaustivo, i tagli sono solo di scena); avvio di
`feature/00-fondamenta`. Poi, nell'ordine: igiene del repository (`.gitignore`,
`.editorconfig`, licenza GPL-3.0 confermata); verifica di ventisei fonti primarie e due
verifiche empiriche in [`Sources.md`](Sources.md), ciascuna con verdetto e riserve;
`tools/check_citations.py` scritto in TDD, nove test, che fallisce se un ADR cita una fonte
inesistente o se una fonte non è citata da nessuno; [`Decision.md`](Decision.md) con
ventiquattro ADR; questo registro e l'[indice della documentazione](README.md).

**Fallito:** leggere le pagine di `mongodb.com/docs` nella loro versione HTML. Il testo
tornava compresso, con parole funzionali cadute e passaggi elisi: sufficiente per farsi
un'idea, inservibile per una citazione letterale da mettere su una slide. Un paio di frasi
erano state trascritte così prima che il problema si notasse, e sono state rifatte.

**Imparato:**

1. Sia `mongodb.com/docs` sia `docs.docker.com` servono una variante Markdown della stessa
   pagina aggiungendo `.md` all'URL. È il testo esatto, senza impaginazione da togliere.
   Da qui in avanti le fonti si consultano così.
2. Verificare prima di scrivere cambia il progetto, non solo la bibliografia. Nove
   assunzioni di design non hanno retto al riscontro: una ha superato una decisione intera
   (ADR-0011 su testcontainers, sostituita da ADR-0020) e tre hanno fatto cadere la
   motivazione di ADR-0004, ADR-0009 e ADR-0013 lasciando in piedi la decisione. Le nove
   sono elencate in testa a `Sources.md`, perché un'assunzione non confermata resta
   un'assunzione anche quando funziona.
3. La documentazione ufficiale si contraddice, e va detto invece che scelto in silenzio:
   sul rilevamento dei limiti di memoria nei container, `core/wiredtiger` (S-001) e
   `reference/command/hostInfo` (S-026) affermano cose diverse, entrambe correnti, sulla
   stessa versione. Il Task 10 misurerà chi ha ragione qui.
4. L'ordine dei task ha reso il controllo automatico una specifica anziché un collaudo:
   i rimandi `Usata da:` erano già cablati in `Sources.md` prima che gli ADR esistessero,
   quindi scrivere `Decision.md` è stato riempire una forma già verificabile. È passato
   verde al primo tentativo, e non per fortuna.
5. La regola «esegui ogni comando che citi» ha ripagato subito. Il piano prevedeva
   `uv run --project tools pytest -q`: da radice fallisce con `ModuleNotFoundError`,
   perché `--project` non sposta la directory di lavoro e pytest, non trovando un
   `pyproject.toml` nella radice, non legge la riga `pythonpath` che sta in quello di
   `tools/`. La forma giusta è `uv run --directory tools pytest -q`. Il `Makefile` del
   Task 7 userà questa.
6. Il `Makefile` chiude la prima metà della feature. Tre dei sei target — `images-pull`,
   `images-verify`, `preflight` — puntano a script che arrivano coi Task 8 e 9 e fino ad
   allora falliscono. Sono rimasti nel file perché l'elenco dei target è anche il piano di
   lavoro di chi legge il repository a metà costruzione.

**Deciso in corsa:** portare a 12 GiB la memoria della VM Docker (ADR-0025), per poter
eseguire e registrare il profilo `completo` dello sharded cluster invece di lasciarlo una
promessa. Il numero non è ancora misurato: al momento della decisione il demone Docker era
spento. Lo verifica lo spike del Task 10.

**Altre due dal Task 8:**

7. `"${VARIABILE:-quella dell'host}"` non compila. Dentro un'espansione di parametro bash
   legge l'apostrofo come apertura di quote, e l'errore che riporta punta a una riga
   distante quindici righe da quella colpevole. Il valore va estratto in una variabile
   prima di usarlo.
8. Uno script di sicurezza va visto fallire, non solo riuscire. Guastando una cifra del
   digest in `tools/images.env`, `--verify` esce 1 in 0,15 secondi: è il tempo la prova
   che non ha tentato di contattare il registro, perché `docker image inspect` interroga
   soltanto il demone locale. Senza quella misura la promessa «non tocca la rete» sarebbe
   rimasta un'affermazione sul codice invece che sul comportamento.

**E una dal Task 9:**

9. Il preflight ha chiuso da solo una pendenza aperta il 24 agosto: `~/.rd` non esiste
   più, il controllo sui residui di Rancher Desktop non è scattato e `docker` risolve a
   `/usr/local/bin/docker`. La promozione dell'avviso sui filmati a errore bloccante è
   affidata alla data anziché a un promemoria: dal 2026-09-18 lo script cambia da sé
   comportamento, perché il giorno del talk nessuno rilegge il piano per ricordarsi di
   modificare uno script.

**E dal Task 10, lo spike sharded** — verbale in
[`00-progetto/2026-08-25-spike-sharded.md`](00-progetto/2026-08-25-spike-sharded.md):

10. **Il lab non può girare su MongoDB 8.** Sul kernel `7.0.12-linuxkit` della VM di Docker
    Desktop, `mongod` esce prima di leggere i parametri: la 8.0.29 e la 8.3.8 rifiutano, la
    8.2.12 parte solo perché precede l'introduzione del controllo, la 7.0.40 parte davvero.
    La correzione esiste ma è nella 8.0.30, che nel changelog c'è e in distribuzione no. È il
    guasto più grave incontrato finora, ed è arrivato dallo spike: [ADR-0028](Decision.md#adr-0028)
    lo mette per iscritto e propone la 7.0.40 con la 8.0.30 come traguardo, ma la scelta
    supera una decisione accettata e resta in stato **Proposta** finché non è approvata. Fino
    ad allora `tools/images.env` resta pinnato alla 8.0 e `make preflight` fallisce: è la
    verità sullo stato del lab, e nasconderla renderebbe verde un controllo su un lab rotto.
11. Il valore di uno spike sta nei fallimenti, e questo ne ha prodotti tre in mezz'ora, tutti
    su passaggi che il design dava per meccanici. `MONGO_INITDB_ROOT_*` non funziona su un
    config server, perché l'entrypoint toglie `--replSet` per creare l'utente ma non toglie
    `--configsvr`, e un config server standalone non esiste. `rs.initiate()` senza argomenti
    registra come host l'ID del container, che nessun altro container sa risolvere.
    L'eccezione localhost non copre `hostInfo`: consente solo di creare il primo utente, e
    dopo `sh.addShard()` per ispezionare uno shard da vicino serve un utente locale a quello
    shard. Nessuno dei tre si sarebbe visto leggendo la documentazione.
12. Il preflight misurava la proprietà sbagliata. Verificava che le immagini pinnate fossero
    **presenti** e passava, mentre nessuna di quelle immagini era in grado di **avviarsi**.
    Adesso esegue `mongod --version` nell'immagine pinnata ([ADR-0027](Decision.md#adr-0027)):
    mezzo secondo, e copre l'unica classe di guasto che sarebbe arrivata intatta fino al
    `compose up` sul palco. La lezione non è sul kernel, è sui controlli: un controllo che non
    è mai stato visto fallire su un guasto reale non è ancora un controllo.
13. Due domande aperte si sono chiuse per strada. La contraddizione fra
    [S-001](Sources.md#s-001) e [S-026](Sources.md#s-026) sui limiti di memoria nei container
    era apparente: le due pagine descrivono campi diversi. `hostInfo.system.memSizeMB` riporta
    la VM, `memLimitMB` riporta il `mem_limit`, ed è il secondo a guidare la cache — misurato,
    640 MiB di limite danno 256 MiB di cache e 4.096 ne danno 1.536. E la domanda «`compose up`
    contatta il registro?» era mal posta: invece di cercarne la prova, si mette
    `pull_policy: never` e non se ne parla più.
14. Undici container occupano 1,32 GiB reali contro 6 GiB di `mem_limit` dichiarati. La
    riserva di [ADR-0025](Decision.md#adr-0025) è sciolta, ma il numero va letto per quello
    che è: `mem_limit` è un tetto, non una prenotazione, e i 12 GiB servono al caso sotto
    carico — che è precisamente quello che l'applicazione del talk andrà a produrre.
15. Il Product Owner ha approvato [ADR-0028](Decision.md#adr-0028) il 2026-08-25: il lab passa
    a **MongoDB 7.0.40**, con la 8.0.30 come traguardo. [ADR-0008](Decision.md#adr-0008) è
    superata, non riscritta — a cadere è il numero di versione, non il pinning per digest, che
    anzi è ciò che ha reso il cambio un'operazione da un file solo. `make images-pull` ha
    riscritto `tools/images.env`, `make preflight` è tornato verde con `Superati: 8 · Avvisi: 1
    · Errori: 0`, e l'unico avviso è l'assenza dei filmati, che non sono ancora girati
    [V-008](Sources.md#v-008).
16. La citazione da slide chiesta dal relatore — «sulle architetture del talk 7.0 e 8.0 non
    differiscono, va detto dal palco» — è entrata in
    [`citazioni-riportare-slide.md`](citazioni-riportare-slide.md), ma **non nella forma in cui
    era stata dettata**. Prima di scriverla è stata controllata contro le note di compatibilità
    della 8.0 [S-029](Sources.md#s-029), e la pagina l'ha smentita su due punti: dalla 8.0 non
    si eseguono comandi collegandosi direttamente a uno shard senza il ruolo
    `directShardOperations`, e `majority` conferma sulla scrittura dell'oplog invece che
    sull'applicazione. Nessuno dei due ribalta la decisione — il primo rende la 7.0 più comoda
    per la demo — ma entrambi si vedono proprio in ciò che si mostra, e una promessa di
    identità piena sarebbe stata smentibile dal manuale in due righe. La slide porta la
    versione circostanziata.
17. La stessa verifica ha restituito qualcosa che non si cercava: la causa del blocco sul
    kernel, documentata. «Starting in MongoDB 8.0, MongoDB uses an upgraded version of TCMalloc
    that uses per-CPU caches, instead of per-thread caches» — è **la 8.0** a introdurre il
    meccanismo che il kernel dal 6.19 non tollera. La riserva di ADR-0028, che poggiava su due
    ticket Jira di cui uno chiuso «Gone away», si scioglie in parte: la 7.0 non aggira il
    problema per fortuna, lo precede per costruzione. Vale come metodo, e non solo qui: la
    spiegazione stava in una pagina di *compatibility changes*, cioè dove non si sarebbe andati
    a cercarla, perché il messaggio d'errore rimandava altrove.
18. Il Task 11 doveva scrivere
    [`06-sviluppo/gestione-risorse-compose.md`](06-sviluppo/gestione-risorse-compose.md)
    partendo dalle fonti già raccolte. Prima di scriverla si è preferito misurare, e le misure
    [V-009](Sources.md#v-009) hanno cambiato tre affermazioni su cui la pagina si sarebbe
    appoggiata. Vale la pena notare il metodo: nessuna delle tre si sarebbe scoperta
    rileggendo la documentazione, perché tutte e tre nascono da una documentazione o assente o
    imprecisa.
19. La prima. `deploy.resources.limits` **è** applicato da `docker compose up`: due servizi
    identici, uno con la sintassi breve e uno con `deploy`, producono `HostConfig.Memory` e
    `HostConfig.NanoCpus` uguali byte per byte. È la domanda che [S-004](Sources.md#s-004)
    lasciava aperta e che [ADR-0013](Decision.md#adr-0013) prometteva di chiudere con
    `docker inspect`. La decisione non cambia — la sintassi breve resta per leggibilità su
    proiettore — ma perde il suo argomento migliore, e la pagina lo dice invece di nasconderlo.
20. La seconda, ed è un errore nostro rimasto in un ADR per un giorno. La nota di revisione di
    [ADR-0004](Decision.md#adr-0004) affermava che `0.25` fosse sotto il minimo documentato di
    `0.256`. Il binario risponde `cacheSizeGB must be greater than or equal to 0.25`: il minimo
    è `0.25`, e `0.25` configura esattamente 268435456 byte, cioè 256 MiB, lo stesso valore che
    mongod sceglierebbe da solo. La cifra `0.256` del manuale è un GB decimale scritto dove
    l'implementazione usa GiB, e produce 262 MiB — un numero che non corrisponde a niente. La
    lezione è vecchia e continua a presentarsi: avevamo corretto una decisione giusta sulla
    base di una lettura, invece di provarla.
21. La terza è quella che sul palco pesa di più. Un container da 512 MiB con
    `--wiredTigerCacheSizeGB 4` **parte**, configura 4.096 MiB di cache e non emette un solo
    avviso che metta in relazione le due cifre. Supera l'healthcheck, risponde al `ping`, e
    muore alla prima scrittura seria. Quando muore, `docker logs` restituisce zero righe:
    `SIGKILL` non lascia messaggi, e l'unico posto dove il fatto è scritto è
    `docker inspect`, con `OOMKilled=true` ed `ExitCode=137`. Il comando da avere nelle dita
    davanti al pubblico è quello, non `docker logs`.

---

## 2026-08-25 — Chiusura di `feature/00-fondamenta`

**Fatto:** dodici task, ventisette commit, ventun file rispetto a `main`. Il branch consegna
l'impianto e nessuno stack, che è ciò per cui era stato aperto:
[`Sources.md`](Sources.md) con ventinove fonti primarie e nove verifiche empiriche, ciascuna
con verdetto e riserve; [`Decision.md`](Decision.md) con ventotto ADR, due delle quali già
superate e nessuna riscritta; `tools/check_citations.py`, scritto in TDD con nove test, che
lega le due cose e fallisce se il legame si rompe; il `Makefile` a sei target;
`tools/pull-images.sh` col pinning per digest e la verifica offline; `tools/preflight.sh`; lo
[spike sharded](00-progetto/2026-08-25-spike-sharded.md); la pagina sulla
[gestione delle risorse in Compose](06-sviluppo/gestione-risorse-compose.md); i
[limiti noti](00-progetto/limiti-noti.md); le
[citazioni da riportare in slide](citazioni-riportare-slide.md); i due indici.

Verifica finale su albero pulito, nell'ordine prescritto dal piano: `make tools-test` esce `0`
con nove test, `make docs-check` esce `0`, `make images-verify` esce `0`, `make preflight` esce
`0` e riporta `Superati: 8 · Avvisi: 1 · Errori: 0`. L'unico avviso è l'assenza della cartella
dei filmati di riserva, che non sono ancora girati e che dal 2026-09-18 lo script promuove da
sé a errore bloccante.

Prova del clone pulito: clonato il branch in una cartella temporanea ed eseguiti **soltanto** i
comandi scritti nel [`README.md`](../README.md), senza sapere nient'altro. I due dell'avvio
rapido escono `0`; escono `0` anche `make help`, `make images-verify` — perché
`tools/images.env` è versionato e l'immagine pinnata sta nella cache Docker dell'host, che è
esattamente la promessa — e il controllo che ogni rimando con ancora risolva.

**Fallito:** due cose, e nessuna delle due si vedeva prima di provare.

1. Il `git clone` dell'avvio rapido, preso alla lettera stamattina, non riproduce niente. Clona
   il ramo predefinito, e `main` contiene due file: `LICENSE` e `README.md`. Il criterio «un
   lettore riproduce il lab dalla sola documentazione» è verificato sul branch e diventa vero
   su `main` al merge di questa PR — ma fino a quel momento resta uno scostamento fra ciò che
   il README promette e ciò che un estraneo otterrebbe eseguendolo. Vale la pena averlo
   scritto: è la prima volta che la documentazione corre più veloce del ramo che la pubblica,
   e non sarà l'ultima.
2. Il controllo che i rimandi relativi risolvano è rimasto uno script usa-e-getta fuori dal
   repository. `check_citations.py` non vede quella classe di errore — lega ADR e fonti, non
   percorsi — e lo script buttato via ne aveva trovati sette reali. Finché non diventa un
   target stabile, quella verifica dipende dal fatto che qualcuno si ricordi di rifarla: la
   stessa forma di promemoria che il preflight ha già eliminato per i filmati, lasciata in
   piedi qui. La chiusura ne ha dato la prova doppia. La voce che state leggendo conteneva un
   rimando morto — `limiti-noti.md` cercato in `06-sviluppo/` mentre sta in `00-progetto/` —
   e nessun controllo del repository l'avrebbe intercettato. E lo stesso script, esteso a
   tutto `docs/`, ne ha segnalati altri quattro che erano **falsi positivi**: stanno dentro
   blocchi di codice recintati, dove sono campioni letterali di file che vivono altrove e
   nessun renderer li tratta come link. Quando diventerà un target dovrà saltare le
   recinzioni, altrimenti il primo effetto di un controllo nuovo è insegnare a ignorarlo. È
   il debito con cui questo branch si chiude.
3. Il criterio di completamento numero 5 non chiedeva «lo spike ha risposto alle cinque
   domande», chiedeva «**e [ADR-0025](Decision.md#adr-0025) registra l'esito**». Rileggendolo
   voce per voce invece che a memoria si è visto che non lo registrava: lo spike aveva
   misurato — 1.356 MiB reali contro 6.144 dichiarati — e l'ADR portava ancora la riserva
   aperta, con scritto che la verifica «appartiene allo spike sharded». Il numero esisteva da
   ore nel documento accanto e non era mai tornato indietro. La nota di verifica lo scioglie
   adesso, e ne approfitta per correggere il `0.256` rimasto fra le alternative scartate. La
   lezione riguarda la forma degli ADR: una riserva è un debito verso un documento, e un
   debito che nessun controllo automatico vede si paga solo se qualcuno rilegge.

**Imparato, e in evidenza perché cambia i piani: l'esito dello spike.** Il lab non gira su
MongoDB 8. Sul kernel della VM di Docker Desktop nessuna 8.0 pubblicata si avvia, la causa è
documentata — dalla 8.0 TCMalloc usa cache per-CPU invece che per-thread
[S-029](Sources.md#s-029) — e la correzione è annunciata in una 8.0.30 che nel changelog c'è e
in distribuzione no. Il lab passa a **7.0.40** ([ADR-0028](Decision.md#adr-0028)), e le tre
branch degli stack nascono su quella versione, non su quella scritta nel design del 24 agosto.
Il traguardo resta, e ha un comando invece di un proposito: `MONGO_IMAGE=mongo:8.0
make images-pull` seguito da `make preflight`. Dal palco la versione va detta per prima, nella
forma circostanziata registrata fra le citazioni: sulle architetture 7.0 e 8.0 non differiscono
in ciò che si mostra, con due eccezioni che si vedono proprio lì.

E tre note di metodo che questo branch ha pagato per imparare.

22. La verifica genera decisioni, non solo bibliografia. Il piano ne prevedeva ventiquattro e
    ne sono uscite ventotto, con ventinove fonti e nove verifiche al posto delle ventisei e due
    di partenza: ogni misura che ha smentito un'assunzione ha prodotto un ADR o una nota di
    revisione. La numerazione del piano non corrisponde più a quella del repository, e il
    repository ha ragione.
23. La proprietà «non tocca la rete» non si prova eseguendo il comando con la rete accesa. La
    si prova negando: `docker image inspect alpine:3.19` esce `1` mentre
    `docker manifest inspect alpine:3.19` esce `0` — la stessa immagine è nel registro e non è
    in cache, e `inspect` non va a prenderla. È il secondo modo usato per dimostrare la stessa
    cosa dopo la misura dei 0,15 secondi del Task 8, e serviva: `make images-verify` che esce
    `0` non distingue fra «l'ho trovata in locale» e «sono andato a scaricarla».
24. L'ultimo passo doveva confermare e invece ha scoperto, due volte: un rimando morto e una
    riserva rimasta aperta in un ADR mentre il documento che la scioglieva era già scritto.
    Nessuna delle due è grave, ed è esattamente il punto — la verifica finale ha trovato ciò
    che i singoli task non avevano chiuso da sé, che è il suo mestiere. A farle emergere è
    stato un criterio di completamento scritto in anticipo e riletto voce per voce invece che
    a memoria: «lo spike ha risposto» e «lo spike ha risposto **e l'ADR lo registra**» sono
    due criteri diversi, e solo il secondo era scritto.

---

## 2026-08-28 — Una review esterna su PR #1

**Fatto:** PR #1 è stata sottoposta a una review automatica esterna, per avere addosso uno
sguardo che non avesse partecipato a scriverla. Cinque rilievi puntuali. Quattro erano
fondati e sono stati corretti; il quinto prediceva un guasto che non esiste, e sotto la
predizione sbagliata aveva però un'osservazione vera.

I quattro accolti, in ordine di gravità.

1. **`tools/pull-images.sh` affermava ciò che il repository aveva già ritirato.**
   L'intestazione diceva «il talk gira senza rete: il digest è ciò che lo garantisce», e più
   sotto «se quel contenuto è già nella cache locale Compose non ha motivo di uscire». È
   esattamente la motivazione che la nota di revisione di [ADR-0009](Decision.md#adr-0009)
   ritira — il digest stabilisce *quale* immagine, non *se* si va in rete — e che il punto 2
   dei [limiti noti](00-progetto/limiti-noti.md) ripete. Anche il messaggio finale del
   comando, «il lab parte senza rete», affermava più di quanto avesse misurato: aveva
   guardato la cache, non il comportamento di Compose. Riscritti entrambi. La garanzia
   offline sta dove è documentata, in `pull_policy: never` ([ADR-0018](Decision.md#adr-0018),
   [ADR-0027](Decision.md#adr-0027)) più il pre-scaricamento; lo script prepara la cache e
   dice di aver preparato la cache.
2. **`Fonte` si dichiarava immutabile e non lo era.** La dataclass è `frozen=True` ma il
   campo `usata_da` arrivava come `set`: `frozen` congela i campi, non ciò che contengono.
   Verificato eseguendo — `hash(fonte)` solleva `TypeError: unhashable type: 'set'`, e
   `fonte.usata_da.add(...)` muta l'oggetto «immutabile». Ora il valore viene congelato in
   `__post_init__`, una volta sola, all'ingresso.
3. **Il controllo delle citazioni non vedeva una riga cancellata.** `parse_decisions`
   restituiva l'insieme vuoto sia per un ADR con `**Fonti:** nessuna (decisione
   organizzativa)` sia per un ADR a cui la riga fosse semplicemente caduta: due situazioni
   diverse, una scelta dichiarata e una svista, appiattite sullo stesso valore. Oggi i
   ventotto ADR hanno tutti la riga e due usano il marcatore, quindi il marcatore è una
   convenzione viva e l'assenza è un difetto. Ora l'assenza è `None` e produce un messaggio
   suo. La prova sta nel caso peggiore: togliendo la riga a [ADR-0015](Decision.md#adr-0015)
   — organizzativa, quindi senza collegamenti inversi da rompere — prima non se ne accorgeva
   nessuno, adesso il controllo esce `1`.
4. **Il `README.md` prometteva cartelle che non esistono.** La tabella «Cosa contiene»
   elencava `docker/` e `app/` accanto a `docs/` e `tools/`, senza distinguere. Le due
   sezioni successive lo dicevano, ma la tabella andava letta fino in fondo per scoprirlo.
   Ora ha una colonna «Stato». È lo stesso principio già applicato all'indice della
   documentazione, che ammette le proprie sezioni mancanti invece di far scoprire il buco a
   chi cerca: non era stato applicato all'indice della radice.

Il rilievo respinto riguardava l'`awk` del `Makefile`, dove `FS = ":.*?## "` avrebbe fatto
cercare un `?` letterale e «rischiava di rompere l'output di `make help`». La predizione era
falsificabile in un comando ed è falsa: se `FS` non trovasse mai corrispondenza, `$2` sarebbe
vuoto e le descrizioni sparirebbero: `make help` le stampa, ed esce `0`. Sotto, però, il
rilievo aveva ragione. `awk` usa gli ERE — «The `awk` utility shall make use of the extended
regular expression notation» — e negli ERE il non-greedy non esiste: quella `?` è solo un
secondo quantificatore attaccato al primo, e «The behavior of multiple adjacent duplication
symbols produces undefined results» (XBD §9.4.6). La modifica è stata fatta lo stesso, con
l'output verificato identico byte per byte prima e dopo, e la ragione con i due URL sta nel
commento sopra il target.

**Fallito.**

1. La correzione sul digest, il 25 agosto, ha attraversato tre documenti — la nota di
   revisione di [ADR-0009](Decision.md#adr-0009), il punto 2 dei limiti noti, una
   [citazione da slide](citazioni-riportare-slide.md) — e si è fermata prima del codice. Lo
   strumento che quella decisione la mette in pratica ha continuato per tre giorni ad
   affermare la tesi ritirata, in testa al file, dove la legge chi apre lo script per
   capirlo. Nessun controllo del repository confronta la prosa di `tools/` con gli ADR. È la
   seconda classe di errore in due giorni che nessuna verifica automatica vede, dopo i
   rimandi relativi, e le due si somigliano: entrambe riguardano il testo, che è il prodotto
   principale di questo repository e la sola parte senza rete di sicurezza.
2. `check_citations.py` è stato scritto in TDD con nove test, e nessuno dei nove chiedeva se
   `frozen=True` fosse vero. I test coprivano quello che la classe fa, non quello che
   dichiara di essere. Il difetto era latente — `hash()` su una `Fonte` non è mai servito a
   nessuno — ma la parola «frozen» nel sorgente era falsa, e chi legge il sorgente le crede.
   Il TDD garantisce che il comportamento provato funzioni, non che le promesse non provate
   siano mantenute.

E tre note di metodo.

25. Una review esterna trova cose che un criterio di completamento non può trovare. I dodici
    task e i sei criteri, riletti voce per voce, avevano scovato due difetti chiudendo il
    branch; un lettore che non aveva scritto niente ne ha trovati altri quattro in pochi
    minuti, e nessuno dei quattro cadeva nel perimetro di un criterio. Un criterio verifica
    ciò che sapevi già di dover verificare — è il suo pregio e il suo soffitto.
26. Un revisore che sbaglia la diagnosi può avere ragione sull'osservazione, e le due cose
    vanno separate eseguendo. Il rilievo sull'`awk` prediceva un guasto inesistente e
    l'osservazione sotto era corretta: respingerlo in blocco avrebbe buttato via la parte
    buona, accoglierlo in blocco avrebbe messo a registro un guasto che non c'è. Nessuna delle
    due si decide leggendo, si decidono lanciando il comando e aprendo lo standard.
27. La disciplina delle fonti ha un attrito che conviene nominare adesso che si è visto: ogni
    voce di [`Sources.md`](Sources.md) deve essere citata da un ADR, altrimenti il controllo
    la dichiara orfana — giustamente. Il testo POSIX che giustifica la modifica all'`awk`
    sarebbe una fonte legittima, ma promuoverlo sembrava richiedere l'apertura di un ADR per
    una correzione da un carattere, e la citazione era rimasta nel commento del `Makefile`,
    fuori da `docs/`, dove la regola non vincola. **Giuliano ha ribaltato la scelta il giorno
    stesso, e aveva ragione:** l'ADR mancava non perché la decisione fosse troppo piccola, ma
    perché in undici giorni nessuno aveva scritto una riga su `tools/` e sul `Makefile`, che
    pure sono la prima cosa che esegue chi clona. La proporzione andava misurata sulla sede
    mancante, non sul carattere corretto. [ADR-0029](Decision.md#adr-0029) governa adesso gli
    strumenti di repository, [S-030](Sources.md#s-030) e [S-031](Sources.md#s-031) hanno una
    casa, e la regola anti-orfane torna a fare quello per cui esiste — impedire la bibliografia
    decorativa — invece di impedire una fonte vera. La lezione è che una regola che ostacola è
    più spesso il sintomo di un buco altrove che un difetto della regola.

---

## 2026-08-28 — Chiusura di `feature/01-stack-standalone`

**Fatto:** tredici task, sedici commit, venticinque file rispetto a `develop` — quindici
nuovi e dieci modificati. Il branch
consegna il primo stack e le pagine che lo spiegano: `docker/01-standalone/compose.yaml` con
le risorse dichiarate e l'immagine pinnata per digest, il seed deterministico in
`init/10-dati-demo.js`, sei target `make` per governarlo, `tools/smoke-standalone.sh` con
dodici controlli, e `tools/check_stack.py` che verifica il file Compose contro gli ADR sulle
risorse. Sul lato documentazione: l'[istanza singola](02-architetture/standalone.md), le
[trappole di MongoDB in Docker](02-architetture/trappole-mongodb-in-docker.md), i
[log](03-amministrazione/log.md), la [guida a `mongosh`](04-mongosh/guida-mongosh.md) e le due
pagine di installazione su [Linux](01-installazione/linux.md) e
[Windows](01-installazione/windows.md). Nove ADR nuovi — da [ADR-0030](Decision.md#adr-0030) a
[ADR-0038](Decision.md#adr-0038) — ventitré fonti primarie e dodici verifiche empiriche, che
portano [`Sources.md`](Sources.md) a cinquantaquattro voci e ventuno misure.

L'ultimo commit salda un debito lasciato aperto alla chiusura di `feature/00`:
`tools/check_links.py` riapre ogni collegamento relativo di `docs/` e del
[`README.md`](../README.md) di radice, verifica che il file esista e che l'ancora ci sia — e
salta i blocchi recintati, che era la condizione esplicita posta allora. La suite degli
strumenti passa da trentotto a sessantatré test.

Verifica finale nell'ordine prescritto dal piano, su albero pulito: `make tools-test` esce `0`
con sessantatré test, `make docs-check` esce `0` su entrambi i controlli, `make stack-check`
esce `0`, `make images-verify` esce `0`, `make preflight` esce `0` con `Superati: 8 · Avvisi:
1 · Errori: 0`. Il ciclo completo dello stack — `make up-01`, `make smoke-01`, `make down-01`
— esce `0`, con il container sano e i dodici controlli superati. L'avvio è stato eseguito con
`PULL_POLICY=never`, cioè con il meccanismo su cui poggia la garanzia offline
([ADR-0018](Decision.md#adr-0018)): Compose non ha contattato nessun registry e il container è
diventato `healthy` in pochi secondi. L'unico avviso resta la cartella dei filmati di riserva,
che dal 2026-09-18 il preflight promuove da sé a errore bloccante.

**Fallito:** cinque cose, e quattro le ha trovate una macchina.

1. **La prova con il Wi-Fi spento non è stata eseguita.** Il piano la chiedeva alla lettera, e
   il suo surrogato — `PULL_POLICY=never` con l'immagine già in cache — copre il meccanismo ma
   non l'ambiente. Non è stata fatta perché spegnere la rete della macchina di sviluppo mentre
   il lavoro è in corso è un gesto che va deciso da chi la sta usando, non da chi ci sta
   lavorando sopra in background. Resta un comando solo, e va eseguito prima del 18 settembre:
   `PULL_POLICY=never make up-01` con la rete staccata. Finché non è stato fatto, la garanzia
   offline di questo branch è documentata e verosimile, non verificata nell'ambiente in cui
   conta.
2. **Il dataset di demo è stato corrotto durante la stesura della guida a `mongosh`.** Le prove
   sui comandi di scrittura sono state eseguite sulla collezione `lab.ordini`, cioè sui dati
   che lo smoke test usa come impronta. Il controllo se n'è accorto subito, perché l'impronta
   di `lab.ordini` non tornava più, e `make seed-01` ha rimesso tutto a posto. Che sia costato
   poco è merito del seed deterministico, non della prudenza di chi eseguiva: la lezione è che
   una guida che mostra comandi di scrittura ha
   bisogno di una collezione propria, e nel branch successivo l'avrà.
3. **Due affermazioni inventate in `01-installazione/linux.md`, corrette prima del commit.** La
   prima attribuiva a una sola pagina un'avvertenza che sta identica in entrambi i tutorial di
   installazione; la seconda descriveva una forma di pinning dei pacchetti — cinque nomi con
   la versione esatta più `apt-mark hold` — che la variante di pagina consultata **non
   riporta**. La fonte dice soltanto «You can install either the latest stable version of
   MongoDB or a specific version of MongoDB» ([S-048](Sources.md#s-048)), e i comandi stanno in
   una scheda che non è stata aperta. Il testo ora riporta quello che la fonte dice e manda il
   lettore alla scheda giusta. È il tipo di errore che la
   [gerarchia delle fonti](Decision.md#adr-0024) esiste per impedire, e che si commette
   comunque quando si scrive da memoria una pagina che si è appena letta.
4. **Tre blocchi di console della guida a `mongosh` contenevano numeri vecchi.** Erano stati
   presi durante la stesura e non rieseguiti: `db.stats` senza tre campi, un `uptime` di
   3127 secondi diventato 3471, un `totalCreated` di 1875 diventato 2118. Trovati rieseguendo
   i comandi esatti che la pagina stampa, e questa è la sola verifica che valga: una pagina che
   mostra output deve mostrare l'output che quei comandi producono oggi, non quello che
   producevano tre ore fa.
5. **Il primo giro di `check_links.py` ha segnalato un errore dentro l'ADR che lo giustificava.**
   [ADR-0038](Decision.md#adr-0038), spiegando che i blocchi di codice vanno saltati, conteneva
   un `[testo](url)` scritto fra apici inversi come esempio — e lo strumento, che saltava le
   recinzioni ma non il codice in linea, lo ha preso per un rimando rotto. Corretto lo
   strumento, non il testo. È il caso di scuola del punto 2 di quella stessa decisione: un
   controllore che ha ragione tre volte su quattro viene spento dopo il quarto falso allarme, e
   la prima occasione per sbagliarlo si presenta sempre nel documento che lo introduce.

**Note di metodo, per la prossima volta.**

- I task 2 e 3 del piano sono stati chiusi in un commit solo. Il piano li separava — il file
  Compose, poi l'healthcheck — ma l'healthcheck era la sola parte del file che ancora non era
  scritta, e due commit avrebbero raccontato un lavoro che non è avvenuto in due tempi. La
  granularità dei commit segue il lavoro, non il piano; quando divergono si scrive perché.
- La riga `**Fonti:**` degli ADR deve stare su **una riga fisica**, altrimenti
  `check_citations.py` ne legge solo la prima parte e dichiara orfane le fonti che seguono. È
  un vincolo di formato che nessun documento dichiarava e che si scopre solo sbagliandolo. Ora
  è scritto qui; se tornerà a costare tempo, diventerà un messaggio di errore dello strumento
  invece di una nota nel registro.

---

## 2026-08-31 — Una review esterna su PR #2

**Fatto:** PR #2 è stata sottoposta alla stessa review automatica esterna di PR #1. Un solo
rilievo puntuale, ed era fondato. I numeri della voce qui sopra — sedici commit, venticinque
file — restano quelli del branch alla chiusura: i commit di questo giro si contano a parte.

Il rilievo riguarda `RECINTO`, in `tools/check_links.py`: pretendeva i tre apici in colonna
zero, e in `docs/Sources.md` esistono recinti rientrati. La riga citata, la 1145, è esatta.
Un recinto dentro un elenco puntato rientra insieme al suo punto, e in `Sources.md` gli
esempi di codice stanno quasi tutti lì dentro.

Verificato prima di correggere, su una pagina costruita apposta, e il difetto è risultato più
largo di come il revisore lo descriveva. Il revisore prevedeva un falso positivo: un
`[testo](url)` scritto in un esempio rientrato viene preso per un rimando vero e segnalato
come rotto. Confermato. Ma la stessa svista produce anche il caso opposto, che il revisore
non nomina: un `<a id="...">` scritto in un esempio rientrato viene raccolto fra le ancore
buone, e allora un rimando rotto che citi quell'ancora **passa il controllo senza una
parola**. Un falso positivo lo vedi e ti arrabbi; un falso negativo non lo vedi.

Corretto ammettendo il rientro su apertura e chiusura, con i due test scritti rossi prima. La
suite passa da sessantatré a sessantacinque test. `make docs-check` restava a `0` anche
prima, e continua a restarci: dentro quel recinto oggi non c'è né un rimando né un'ancora,
quindi il difetto era latente e non attivo. È il motivo per cui né i sei criteri di
completamento né la verifica finale potevano scovarlo — nessuno dei due guarda ciò che uno
strumento *non* segnala.

`check_citations.py` è stato controllato per la stessa classe di errore e non ce l'ha: i suoi
punti d'ingresso sono ancorati a inizio riga con prefissi propri — `## ADR-`, `### S-`,
`- **URL:**` — e un blocco rientrato non li produce.

**Note di metodo.**

28. Un analizzatore va provato sul materiale che dovrà leggere, non su materiale costruito per
    provarlo. I venticinque test di `check_links.py` giravano su testi scritti a mano, tutti
    con i recinti in colonna zero, perché è così che li scrive chi li scrive apposta.
    `Sources.md`, che è la pagina più lunga del repository, li ha quasi tutti rientrati. Il
    caso che mancava non era un caso limite: era la forma normale del corpus vero.
29. Lo stesso strumento ha sbagliato due volte nello stesso punto — prima il codice in linea,
    ora il rientro — e le due volte per la stessa ragione: «che cosa non è prosa» è un'ipotesi
    sul Markdown, e un'ipotesi non provata contro un file vero è un falso allarme in attesa di
    turno. Le due volte la correzione è andata allo strumento e non al testo, ed è la sola
    direzione ammessa: un controllore che si adatta ai documenti che non sa leggere smette di
    controllarli.
30. Una review esterna che produce un rilievo solo non ha lavorato meno di una che ne produce
    cinque. Quel rilievo indicava il file, la riga e la conseguenza, e sotto ce n'era una
    seconda che il revisore non aveva visto. Il valore non stava nella diagnosi completa: era
    nell'aver guardato una riga che chi l'aveva scritta considerava chiusa.

---

## 2026-08-31 — Una seconda review esterna, sei rilievi

**Fatto:** la stessa PR è stata data a un secondo revisore automatico, di famiglia diversa dal
primo. Sei rilievi, tutti con file e riga. Arbitrati uno per uno eseguendo, come vuole la regola
del repository: **sei fondati su sei**. Quattro corretti qui, uno chiuso motivando, uno che non
si può correggere senza una decisione — perché il difetto non è nel codice.

**I quattro corretti.**

`tools/check_stack.py` risolveva `${VAR:-x}` e `${VAR:?x}` come se i due punti non ci fossero.
Provato contro Compose vero (v5.4.0), non contro la specifica: un file d'ambiente con
`PULL_POLICY=` e `docker compose config` restituisce `pull_policy: missing`, mentre lo
strumento leggeva la stringa vuota; e `MONGO_IMAGE=` con la forma `:?` fa fallire Compose
con «required variable MONGO_IMAGE is missing a value», mentre lo strumento la lasciava
passare. Il controllore giudicava uno stack diverso da quello che si avvia. Le due prove
stanno per intero nel messaggio di questo giro di commit e diventeranno una voce di verifica
in `Sources.md` insieme all'ADR che scioglie il sesto rilievo, che è l'ADR che le cita.

`tools/check_stack.py`, ancora: `DIGEST` accettava da tre a sessantaquattro cifre esadecimali.
Un digest SHA-256 ne ha sessantaquattro esatte, Docker rifiuta il resto, e la regola nata per
impedire i tag mobili approvava un pin inesistente. Il punto amaro: nove fixture dei test
usavano `sha256:abc`. I test non avevano mancato il caso — lo avevano scritto e promosso.

`tools/check_links.py` ignorava la quinta delle cinque regole di
[S-053](Sources.md#s-053), quella che il repository cita per esteso: «If the automatically
generated anchor for a heading is identical to an earlier anchor in the same document, a unique
identifier is generated by appending a hyphen and an auto-incrementing integer». Tre titoli
uguali danno `esempio`, `esempio-1`, `esempio-2`; lo strumento ne conosceva uno e avrebbe
segnalato come rotti due rimandi che su GitHub funzionano.

`tools/check_citations.py` perdeva un blocco intero quando un identificatore compariva due
volte: il dizionario che accumula gli ADR non sa dire «ce n'erano due», e il secondo
sovrascriveva il primo. Se i due blocchi citano la stessa fonte, il controllo stampa
«Citazioni coerenti.» su un documento a cui manca un pezzo.

**Quello chiuso senza correzione.** Lo stesso rilievo sulle ancore aggiungeva che i
collegamenti con la destinazione fra parentesi angolari — `[testo](<con spazi.md>)` — non
vengono riconosciuti. Vero, e senza conseguenze: nel corpus non esiste un solo file con uno
spazio nel nome, la convenzione è kebab-case, e ogni forma di parsing in più su un corpus che
non la usa è un falso positivo in attesa di turno. Chiuso dichiarando il motivo, non tacendo.

**Quello che non si corregge da solo.** Il rilievo sul `pull_policy` di
`docker/01-standalone/compose.yaml` era formulato come una difformità dall'ADR-0027, e nel
verificarlo è saltato fuori che il conflitto sta a monte:
[ADR-0018](Decision.md#adr-0018) prescrive `${PULL_POLICY:-missing}` con `never` esportato dal
profilo di palco, [ADR-0027](Decision.md#adr-0027) prescrive `never` fisso in ogni servizio di
ogni stack e argomenta contro `missing` per nome. **Sono entrambi Accettata, nessuno dei due
supera l'altro.** L'artefatto implementa il primo e `check_stack.py` lo fa rispettare. È una
questione da ADR, non da correzione: aspetta la decisione del Product Owner.

**Note di metodo.**

31. Un secondo revisore, di famiglia diversa dal primo, non ha trovato «gli stessi difetti
    meglio»: ne ha trovati sei che il primo non aveva nominato, nei tre strumenti che il primo
    aveva letto. La differenza non è la bravura, è dove si posa lo sguardo. Vale la pena
    pagare due volte.
32. Il rilievo più difficile da arbitrare è stato quello che alla prima prova sembrava
    infondato. Avevo costruito il caso con due ADR omonimi che citavano fonti diverse, e il
    controllo falliva — segno apparente che il difetto non c'era. Falliva per un'altra
    ragione, e con un messaggio fuorviante. Il caso giusto era l'altro, quello in cui i due
    blocchi citano la stessa fonte: lì il controllo tace. **Una prova che assolve va guardata
    con lo stesso sospetto di una che accusa**, perché un controesempio mal costruito difende
    il codice invece di metterlo alla prova.
33. Quattro rilievi su sei riguardano non ciò che il codice fa, ma ciò che il codice *crede*
    di un sistema esterno: come Compose interpola una variabile vuota, quante cifre ha un
    digest, come GitHub numera le ancore ripetute. Nessuno dei tre è verificabile leggendo il
    codice; tutti e tre lo sono in trenta secondi eseguendo. La regola che ne esce è la stessa
    per lo strumento e per la pagina di documentazione: **un'affermazione su un sistema che
    non è tuo va provata contro quel sistema**, e la prova va scritta.

---

## 2026-08-31 — `pull_policy: never`, e due ADR che non potevano stare insieme

**Fatto:** il Product Owner ha sciolto il conflitto emerso dalla review: governa
[ADR-0027](Decision.md#adr-0027), quindi `never` fisso e regola di `check_stack.py` rovesciata,
registrato in [ADR-0039](Decision.md#adr-0039) che **supera** [ADR-0018](Decision.md#adr-0018).
ADR-0018 non è stata riscritta: le è stato aggiornato lo stato e aggiunto il motivo del
superamento, come già per [ADR-0008](Decision.md#adr-0008).

Il motivo per cui ADR-0018 cade merita di essere scritto, perché non l'ha smontata un fatto nuovo:
l'ha smontata una sua riga. Fra le alternative scartate ADR-0018 respingeva `--pull never` da riga
di comando perché «si dimentica, e soprattutto non è scritto nel file: l'artefatto non
documenterebbe più il proprio comportamento». È l'argomento esatto che vale contro una variabile
d'ambiente. **La decisione conteneva la propria confutazione, e ci sono voluti sei giorni e due
revisori esterni perché qualcuno la leggesse.**

**Cos'è cambiato.** `docker/01-standalone/compose.yaml` porta `pull_policy: never` letterale;
`PULL_POLICY` sparisce da `.env.example`, che al suo posto spiega perché non c'è più. In
`tools/check_stack.py` la regola non chiede più che `pull_policy` esista: chiede che valga `never`
**e** che non provenga da un'interpolazione. Per poterlo chiedere lo strumento legge il file due
volte, prima e dopo la sostituzione delle variabili: le altre regole giudicano lo stack che si
avvia, questa giudica ciò che il file promette a chi lo apre. Due test rossi prima, suite da
settantaquattro a settantasei.

**Provato, non dedotto** ([V-022](Sources.md#v-022)): `make up-01` porta il container a `Healthy`,
`make smoke-01` passa dodici prove su dodici, e con un digest che non è in cache `up` fallisce in
**0,113 s** con `No such image` — lo stesso ordine di grandezza misurato dallo spike in
[V-006](Sources.md#v-006). Prima di correggere ho fatto girare `make stack-check` sul file vecchio
e la regola nuova: fallisce nominando il servizio. Un controllo che non si vede fallire non è un
controllo.

Le due pagine di piano hanno ricevuto una **nota di allineamento in testa**, non una riscrittura.
Restano da rifare i filmati? No: nessun filmato mostra quella riga.

**Una correzione a margine.** [ADR-0038](Decision.md#adr-0038) scrive che la numerazione delle
ancore ripetute «qui non è mai servita, e il giorno che servisse si vedrebbe subito». La seconda
metà è falsa, e il giro di review l'ha dimostrato: non si sarebbe vista affatto — si sarebbe vista
la segnalazione di un rimando rotto che rotto non è, cioè il contrario di ciò che è. L'ADR non si riscrive; la correzione sta qui
e nel codice, che ora la regola la implementa.

**Note di metodo.**

34. Due decisioni accettate e opposte sono peggio di nessuna delle due. Finché convivono, chi legge
    ne applica una a caso e ha ragione comunque — e lo strumento di controllo, che ne conosce una
    sola, difende attivamente quella sbagliata. `check_stack.py` ha passato sei giorni a far
    rispettare ADR-0018 contro ADR-0027. **Un controllo automatico amplifica la decisione che
    conosce: se è quella superata, amplifica l'errore** e gli dà l'autorevolezza di un test verde.
35. Il posto dove cercare l'errore di una decisione è la sua sezione «alternative scartate». È lì
    che chi decide scrive gli argomenti nella loro forma più nuda, ed è lì che si vede se ne ha
    applicato uno a metà. Vale la pena rileggere le alternative scartate degli ADR vecchi con gli
    occhi di oggi: costa dieci minuti e non richiede fonti nuove.
36. La differenza fra `${PULL_POLICY:-never}` e `never` è invisibile a chi esegue e decisiva per
    chi guarda. Il primo si comporta bene su questa macchina, oggi, con questo file d'ambiente. Il
    secondo **dice** come si comporta, a chiunque lo apra, per sempre. In un repository che è
    materiale didattico prima che infrastruttura, la seconda proprietà vale più della prima.

37. **Un consuntivo si conta all'ultimo commit, non al penultimo.** La prima stesura della riga
    qui sotto diceva «ventisei commit», e aveva contato il branch com'era *prima* del commit che la
    conteneva. È lo stesso errore corretto il 28 agosto da `fix: il conteggio della voce di chiusura
    era vecchio di un commit`, ricomparso tre giorni dopo nello stesso file — segno che stava in una
    riga di messaggio e non in una regola. La regola, adesso scritta: quando un numero descrive il
    branch e vive dentro il branch, si calcola includendo il commit che lo introduce.

**Consuntivo del branch, alla vigilia dell'unione.** Ventotto commit e ventinove file rispetto a
`develop`: i sedici della chiusura, i due del primo giro di review, i cinque del secondo, i tre di
ADR-0039 e i due di coda — questo compreso. La PR è `MERGEABLE` senza conflitti, l'unico filo di
commento è risolto, e nel
repository non gira alcun controllo automatico su GitHub — per scelta
([ADR-0038](Decision.md#adr-0038)): i tre controllori girano in locale, ed è lì che sono stati
eseguiti.

**Quello che resta aperto** non appartiene a questo branch e va scritto perché non si perda: la
prova con la rete fisicamente staccata. Dopo [ADR-0039](Decision.md#adr-0039) il comando non ha
più una variabile davanti — è `make up-01` con il Wi-Fi spento, e basta.

## 2026-08-31 — `feature/02`, Task 1: due documenti in contraddizione, tre strade provate, una che non era scritta

Il Task 1 del piano di `feature/02` esisteva per una ragione sola: il design (§5.4) e
[ADR-0026](Decision.md#adr-0026) prescrivono due catene di inizializzazione diverse per lo stesso
replica set, e la differenza non è di stile. In una, `MONGO_INITDB_ROOT_USERNAME` e
`MONGO_INITDB_ROOT_PASSWORD` stanno sul primo membro e una password di laboratorio finisce in
`.env.example`; nell'altra i `mongod` partono nudi e l'utente nasce sotto eccezione localhost. Il
piano aveva scritto, prima di sapere come sarebbe andata, che la contraddizione **non** si sarebbe
sciolta rileggendo i due testi: si sarebbero montate entrambe le strade e si sarebbe guardato.

Sono stati montati tre stack usa-e-getta fuori dal repository, nella cartella temporanea della
sessione, e smontati con `down -v` a misura presa. Il verbale integrale — comandi, risposte,
ambiente, riserve — è in [V-023](Sources.md#v-023). Qui sta quello che le misure hanno insegnato.

**Funzionano tutte e tre.** Era il risultato meno comodo e il più utile. La strada di ADR-0026
funziona anche su un replica set, non solo sullo sharded cluster per cui era stata scritta:
`rs.initiate()` passa, `createUser` passa, e la scrittura successiva riceve `Unauthorized code=13`
— che non è un fallimento ma la ricevuta che l'eccezione si è chiusa da sé, nel punto esatto in cui
[S-055](Sources.md#s-055) dice che si chiude. Funziona anche la strada del design, e con essa cade
un'idea che circolava nel repository da sei giorni: si era letto ADR-0026 come se dicesse che
l'entrypoint dell'immagine non sa creare l'utente su un nodo di replica set. Non lo dice. Il caso
che rompeva era `--configsvr`, che l'entrypoint non toglie e che da solo non esiste; `--replSet` lo
toglie eccome, e l'utente nasce. Una frase vera su un caso era stata applicata a un caso vicino
senza verificarla, ed è bastato provarla per accorgersene.

**La terza prova doveva chiudere una domanda e ne ha aperta una migliore.** Il design afferma che un
sidecar non gode dell'eccezione localhost. È vero, misurato: `Command replSetInitiate requires
authentication`. A quel punto il task era finito — c'era la risposta, si poteva scrivere l'ADR. È
stata invece fatta la domanda in più: *perché* fallisce? Non per la rete, perché il sidecar il
`mongod` lo raggiunge. Fallisce per l'indirizzo da cui arriva. E se il problema è l'indirizzo di
provenienza, si cambia l'indirizzo di provenienza: un container con `network_mode:
"service:mongo-rs-1"` non ha un'interfaccia di rete propria, usa quella del membro, e il suo
`localhost` è il `localhost` del `mongod`. Provato:

```console
NAMESPACE_CONDIVISO_OK {"ok":1}
UTENTE_CREATO da sidecar in namespace condiviso
CHIUSA_DOPO_IL_PRIMO_UTENTE codeName=Unauthorized code=13
```

Tre righe che tengono insieme il vantaggio di ADR-0026 (nessuna password nel repository) e quello
del design (tutto dentro Compose, `docker compose up -d` che basta da solo). Questa via non sta né
nel design né in ADR-0026: è saltata fuori da una domanda che il piano non prevedeva.

**Una riserva aperta il 25 agosto è stata riscossa.** [S-006](Sources.md#s-006) aveva dichiarato,
sei giorni fa, che il vincolo che tutti danno per ovvio — l'eccezione localhost vale solo da
loopback — **non è enunciato da nessuna fonte primaria**. La pagina è stata riletta sulla variante
v7.0, che è la serie che il lab pinna davvero ([S-055](Sources.md#s-055)): le stringhe `127.0.0.1`,
`::1`, «loopback» e «same host» non ci sono neanche lì; la formulazione più vicina è «connect to the
localhost interface», che nomina un'interfaccia senza dire quale. La fonte, cioè, chiama
l'eccezione «localhost» e non definisce «localhost». Adesso però c'è la misura: la prova C dimostra
che il vincolo esiste e che il prodotto lo applica. La riserva cambia stato — da «vero per
convenzione» a «vero, misurato qui, e ancora non scritto dalla fonte» — e diventa esattamente il
genere di cosa che vale la pena raccontare da un palco.

**Una misura di contorno ha risolto in anticipo il Task 5.** Il piano prevedeva un uovo e una
gallina: l'healthcheck dei membri non può chiedere «sei primario o secondario?», perché resterebbe
rosso fino a `rs.initiate()` e bloccherebbe il servizio che dovrebbe eseguirlo. La via d'uscita
andava misurata, non supposta, e la misura c'è: su un `mongod` con `--keyFile` non ancora
inizializzato, `hello()` risponde senza credenziali (`isWritablePrimary=false secondary=true`). Un
healthcheck che chiede «`hello()` risponde?» diventa verde prima dell'inizializzazione, e il nodo si
scioglie.

L'esito è in [ADR-0040](Decision.md#adr-0040), che propone la terza via. È il primo ADR del
repository in stato **Proposta**: gli altri trentanove registrano scelte che un vincolo tecnico
aveva già preso: qui le misure dicono che tutte le strade funzionano, e quindi non decidono niente.
Quel che resta da scegliere è il prezzo, e il prezzo lo sceglie chi presenta.

**Note di metodo.**

38. **Una contraddizione fra due documenti non si scioglie rileggendoli.** Rileggere produce
    un'opinione su chi dei due sia più autorevole; montare entrambe le strade produce una misura. Ed
    è servito: la rilettura avrebbe dato ragione ad ADR-0026 (è più recente e nasce da uno spike),
    e avrebbe portato con sé l'errore che ADR-0026 non conteneva ma che gli era stato attribuito —
    che l'entrypoint non sappia creare l'utente con `--replSet`.

39. **Quando una prova fallisce, chiedersi *perché* e non solo *se*.** La prova C aveva già dato la
    risposta che serviva al task, e il task poteva chiudersi lì. La domanda in più — perché quel
    sidecar non è ammesso? — è costata dieci minuti e ha prodotto la strada che è stata poi
    proposta. Una prova che fallisce sa sempre più cose di quelle che le sono state chieste.

40. **Una riserva dichiarata è un debito, non un disclaimer.** [S-006](Sources.md#s-006) aveva
    scritto il 25 agosto che il vincolo loopback non era documentato. Scriverlo è servito a due
    cose: a non affermarlo come citazione, e a lasciare in chiaro dove si sarebbe potuto misurare.
    Sei giorni dopo il debito è stato riscosso da una prova che non era stata pianificata per
    riscuoterlo. Le riserve si scrivono perché qualcuno, prima o poi, ci inciampi apposta.

41. **Un ADR può nascere non deciso.** Fin qui ogni ADR verbalizzava una scelta che un vincolo
    tecnico aveva già preso, e lo stato `Accettata` era l'unico che servisse. Quando le misure
    dicono che tutte le strade funzionano, il documento che le raccoglie non è una decisione: è una
    proposta, e chiamarla `Accettata` significherebbe far firmare a chi implementa una scelta che
    spetta a chi presenta. Da qui in poi lo stato `Proposta` esiste, e la modifica del corpo che lo
    porta ad `Accettata` è l'unica eccezione ammessa alla regola secondo cui un ADR si supera e non
    si riscrive — perché una proposta, finché è tale, non è ancora una decisione da proteggere.

42. **Una conferma che non può fallire non è una conferma.** Gli stack usa-e-getta sono stati
    smontati con `docker compose down -v > /dev/null 2>&1; echo "smontato"`, e il registro ha
    letto «smontato» tre volte. Non era vero: i file Compose usano `${MONGO_IMAGE:?…}`, la
    variabile non era nell'ambiente di quella shell, l'interpolazione falliva e `down` non
    rimuoveva niente — undici container, dieci volumi e tre reti sono rimasti in piedi finché non
    li ha trovati un `docker ps -a --filter name=spike` fatto per scrupolo. L'errore non è stato
    il comando sbagliato: è stato mettere accanto a un comando che poteva fallire un `echo` che
    non poteva. Due regole, adesso scritte. La prima: la riga che dichiara l'esito legge `$?`, o
    tace. La seconda: dopo una pulizia si guarda che cosa resta, perché è l'unica verifica che
    non passa per la parola del comando che ha pulito. (Chiuso con `docker compose -p <nome>
    down -v`, che non ha bisogno del file e quindi non interpola niente.)

## 2026-08-31 — `feature/02`, Task 2: il keyfile, e il messaggio d'errore che non ha la severità che dovrebbe

Scelta la strada C ([ADR-0040](Decision.md#adr-0040)), il Task 2 posa il primo anello:
`docker/02-replicaset/compose.yaml` con il solo servizio `keyfile-init`, e
`docker/02-replicaset/init/01-keyfile.sh` che genera il segreto condiviso dentro un volume
nominato. Il keyfile non entra nel repository ([ADR-0014](Decision.md#adr-0014)): nasce al primo
avvio, sulla macchina di chi esegue.

**Il caso dritto, misurato.** Prima esecuzione:

```console
$ docker compose --env-file tools/images.env -f docker/02-replicaset/compose.yaml run --rm keyfile-init
keyfile generato
-r-------- 1 999 999 1024 Aug 31 13:27 /keyfile/mongo-keyfile
```

Permessi `400`, proprietario `999:999`, 1024 byte. Seconda esecuzione, a volume già popolato:

```console
keyfile già presente: non lo rigenero
-r-------- 1 999 999 1024 Aug 31 13:27 /keyfile/mongo-keyfile
```

Stessa ora sul file: non è stato rigenerato. L'idempotenza qui non è pulizia formale — un keyfile
rigenerato al secondo `make up-02` significherebbe tre membri che smettono di riconoscersi, con un
errore di autenticazione che sembra tutt'altro.

**Il caso storto, che è quello che si incontra davvero.** Il piano chiedeva di montare di proposito
un keyfile con `chmod 644` e di prendere il messaggio d'errore *esatto*. Preso, ed è più
interessante del previsto:

```console
{"s":"I",  "c":"ACCESS",  "id":20254, "msg":"Read security file failed",
 "attr":{"error":{"code":30,"codeName":"InvalidPath",
                  "errmsg":"permissions on /keyfile/mongo-keyfile are too open"}}}
{"s":"F",  "c":"CONTROL", "id":20575, "msg":"Error creating service context",
 "attr":{"error":"Location5579201: Unable to acquire security key[s]"}}
```

`mongod` esce con codice `1`. Con lo stesso file riportato a `400` parte e arriva a
`Waiting for connections`, quindi la variabile isolata è il permesso e nient'altro.

La trappola non è che fallisca: è **quale delle due righe porta l'informazione**. La riga che dice
il perché — «permissions on … are too open» — ha severità `"s":"I"`, informativa. La riga fatale,
`"s":"F"`, dice soltanto «Unable to acquire security key[s]» e non nomina né i permessi né il file.
Chi filtra i log per severità, che è la prima cosa che si fa davanti a un container che muore
all'avvio, trova la riga inutile e perde quella utile. I due identificativi da cercare sono stabili
e valgono più del testo: **`id: 20254`** per la causa, **`id: 20575`** per l'effetto.

Materiale per il **Task 12**, dove la trappola va scritta con il suo sintomo testuale: una trappola
senza il messaggio che la annuncia non è ritrovabile da chi la sta subendo. La voce di
[`Sources.md`](Sources.md) che ospiterà questa misura nasce lì, insieme alla pagina che la spiega;
qui resta il verbale.

**Note di metodo.**

43. **Di un errore si prende il testo, non il riassunto.** «Fallisce se i permessi sono larghi» è
    vero e inservibile: nessuno lo ritrova cercando. `permissions on … are too open` e `id: 20254`
    si ritrovano. È la ragione per cui il piano chiedeva di provocare il guasto invece di
    descriverlo, e la ragione per cui è valsa la pena: descrivendolo non sarebbe emerso che la riga
    diagnostica è informativa e quella fatale è muta.

## 2026-08-31 — Punto di ripresa: `feature/02` si riprende dal Task 3

Sessione interrotta per esaurimento del limite, non per un problema del lavoro. Tutto quello che
c'è è committato e spinto su `origin/feature/02-stack-replicaset`; l'albero di lavoro è pulito.
Questa voce esiste perché la prossima sessione riparta senza ricostruire il contesto a memoria.

**Quello che è deciso e non va più discusso.** [ADR-0040](Decision.md#adr-0040) è `Accettata`: la
catena di inizializzazione del replica set usa la **strada C**. Nessun `mongod` riceve
`MONGO_INITDB_ROOT_*`; l'utente amministratore nasce sotto eccezione localhost da un servizio
one-shot `rs-init` che condivide il namespace di rete del primo membro
(`network_mode: "service:mongo-rs-1"`). Le tre strade sono state montate e misurate prima di
scegliere: il verbale è in [V-023](Sources.md#v-023), la fonte nella versione pinnata in
[S-055](Sources.md#s-055).

**Quello che è costruito.** Il Task 1 e il Task 2 del
[piano](00-progetto/2026-08-31-piano-feature-02-stack-replicaset.md) sono chiusi. Nel repository ci
sono `docker/02-replicaset/compose.yaml` — per ora il solo servizio `keyfile-init` — e
`docker/02-replicaset/init/01-keyfile.sh`, idempotente, che genera il keyfile a `400` e `999:999`
dentro il volume nominato `keyfile`.

**Quello che è già misurato e non va rimisurato.** Tre cose che i task successivi darebbero per
ignote e che invece hanno già una risposta:

- **Task 5, l'uovo e la gallina dell'healthcheck.** Su un `mongod` con `--keyFile` non ancora
  inizializzato, `hello()` risponde **senza credenziali** (`isWritablePrimary=false
  secondary=true`). Quindi l'healthcheck deve chiedere «`hello()` risponde?» e non «sei primario o
  secondario?», altrimenti resta rosso fino a `rs.initiate()` e blocca il servizio che dovrebbe
  eseguirlo.
- **Task 4, la corsa di `rs-init`.** `depends_on` con `condition: service_started` non basta: nella
  prova è arrivato mentre il membro era ancora nella fase del `mongod` temporaneo e ha preso
  `ECONNREFUSED`. Serve `service_healthy`, che l'healthcheck qui sopra rende raggiungibile.
- **Task 12, la trappola del keyfile.** Con `chmod 644` `mongod` esce con codice `1`. La riga che
  spiega il perché — `permissions on … are too open`, `id: 20254` — è di severità **informativa**;
  la riga fatale `id: 20575` dice solo `Unable to acquire security key[s]` e non nomina i permessi.
  La voce di [`Sources.md`](Sources.md) per questa misura **non è ancora stata creata**: nasce al
  Task 12, insieme alla pagina che la spiega. È l'unico debito documentale aperto dai due task
  chiusi.

**Da dove si riparte.** Task 3 del piano: i tre `mongod` con `--replSet`, `--keyFile`,
`--bind_ip_all`, `768m` di memoria, `0.25` GB di cache WiredTiger, `0.75` CPU per membro
([ADR-0004](Decision.md#adr-0004)) e le porte `27021`/`27022`/`27023`. Il piano ne porta lo YAML
completo per il membro 1.

**Come si verifica che lo stato sia quello descritto qui**, prima di toccare qualunque cosa:

```console
$ git log --oneline origin/develop..HEAD   # quattro commit
$ make docs-check                          # citazioni e collegamenti coerenti
$ make stack-check                         # lo stack 01 rispetta i suoi ADR
$ uv run --directory tools pytest -q       # 76 passati
```

**Note di metodo.**

44. **Una sessione che finisce non è una consegna che finisce.** Il lavoro era già tutto committato
    e spinto, quindi non si è perso niente di materiale — ma il contesto sì: quale strada fosse
    stata scelta e perché, che cosa fosse già stato misurato, dove stesse il debito aperto. Quel
    contesto vive nella testa di chi lavora e muore con la sessione, a meno che non venga scritto
    dove il lavoro vive. Da qui la regola: quando si sospende, l'ultimo commit non è il codice, è il
    punto di ripresa — e dice tre cose, che cosa è deciso, che cosa è già misurato, da quale passo
    si riparte.

## 2026-08-31 — `feature/02`, Task 3: i tre membri, e due controlli che non controllavano

Il task chiedeva di aggiungere i tre `mongod` al file Compose e di scrivere `.env.example`. La
parte prevista è andata come previsto; le due cose che valgono la pena di essere scritte sono
emerse dal contorno, e sono entrambe della stessa famiglia — un controllo che gira, esce `0`, e
non guarda quello che credevamo guardasse.

**Quello che è stato costruito.** `docker/02-replicaset/compose.yaml` ha adesso `mongo-rs-1`,
`mongo-rs-2` e `mongo-rs-3`: `--replSet`, `--keyFile`, `--bind_ip_all`, cache WiredTiger a
`0,25 GiB`, `768m` e `0.75` CPU per membro ([ADR-0004](Decision.md#adr-0004)), porte `27021`,
`27022`, `27023`, un volume dati per ciascuno e il keyfile montato in sola lettura. Accanto,
`docker/02-replicaset/.env.example` con i parametri modificabili e la password
dell'amministratore lasciata **vuota di proposito**: per Compose una variabile vuota vale quanto
una assente, quindi la forma `${...:?}` che il Task 4 userà farà fallire l'avvio con un messaggio
invece di creare un utente senza password.

I tre membri sono scritti per esteso, senza ancoraggi YAML e senza `extends`
([ADR-0003](Decision.md#adr-0003)). Trenta righe risparmiate a chi sa già leggere gli ancoraggi
costerebbero dieci minuti a chiunque altro, e questo file è materiale didattico prima che
configurazione.

**Prima scoperta: `make stack-check` non guardava questo file.** Il target usa un elenco esplicito
di file, e lo stack 02 non c'era. Passandogli il file del Task 2 a mano:

```console
$ uv run --project tools python tools/check_stack.py --ambiente tools/images.env docker/02-replicaset/compose.yaml
✗ keyfile-init: manca «mem_limit».
✗ keyfile-init: manca «cpus».
2 problemi negli stack.
```

Due violazioni di [ADR-0004](Decision.md#adr-0004) erano entrate nel repository con il commit del
Task 2 e ci sono rimaste, non perché il controllo fosse debole ma perché non era stato invitato a
guardare. Corrette qui: `keyfile-init` dichiara `128m` e `0.25` CPU — che non entrano nel bilancio
dei 2,25 GiB del design §5.1, visto che il servizio è già uscito quando il primo `mongod` parte.
Il Task 6 insegnerà al target l'elenco nuovo; il punto non è quello, è che l'elenco esiste.

**Seconda scoperta: lo YAML del piano avrebbe disarmato la regola sulla cache.** Il piano scriveva
il comando dei membri senza `mongod` in testa, cominciando da `--replSet`. Per Docker le due forme
sono equivalenti: l'entrypoint ufficiale antepone `mongod` da sé quando il primo argomento comincia
per trattino. Per `tools/check_stack.py` no — riconosce un `mongod` dal primo elemento del comando.
Due file minimi che differiscono solo in quello, entrambi con un `mongod` e **nessuna** cache
dichiarata:

```console
$ ... check_stack.py senza-mongod.yaml
Stack conformi: 1.
uscita=0

$ ... check_stack.py con-mongod.yaml
✗ membro: avvia mongod senza «--wiredTigerCacheSizeGB». Il valore va dichiarato a mano […]
uscita=1
```

Scritto come lo scriveva il piano, lo stack sarebbe passato conforme con tre `mongod` a cache non
dichiarata — cioè esattamente la cosa che [ADR-0004](Decision.md#adr-0004) esiste per impedire. Il
file adesso scrive `mongod` per esteso, che è anche la forma dello stack 01. Resta la lacuna nello
strumento: una regola che si può eludere scrivendo la stessa cosa in un altro modo legittimo non è
una regola, è una convenzione. Materiale per il **Task 6**, che sullo strumento ci deve tornare.

**Le misure, sullo stack avviato davvero.** Il piano si fermava a `config -q`; un file che non ha
mai avviato niente dice solo di essere sintatticamente valido. Avviato:

```console
$ docker inspect mongo-rs-1 mongo-rs-2 mongo-rs-3 --format '{{.Name}} memoria={{.HostConfig.Memory}} nanocpu={{.HostConfig.NanoCpus}}'
/mongo-rs-1 memoria=805306368 nanocpu=750000000
/mongo-rs-2 memoria=805306368 nanocpu=750000000
/mongo-rs-3 memoria=805306368 nanocpu=750000000
```

805306368 byte sono esattamente 768 MiB e 750000000 nanocpu sono 0,75 CPU: il runtime ha applicato
quello che il file dichiara. Nei log di `mongod`, `cache_size=256M`, cioè i `0,25 GiB` richiesti
letti come GiB e non come GB decimali — la conferma sullo stack vero di quanto
[V-009](Sources.md#v-009) aveva misurato in laboratorio. Il keyfile è lo stesso su tutti e tre (una
sola somma `md5`), è `-r-------- 999 999`, e un tentativo di scriverci sopra da dentro un membro
prende `Read-only file system`. Porta anche la data del Task 2: il volume è sopravvissuto fra due
sessioni senza essere rigenerato, che è l'idempotenza dello script vista da lontano.

**La correzione: `secondary=true` era di un membro già inizializzato.** Il punto di ripresa dava per
misurato che su un `mongod` con `--keyFile` non ancora inizializzato `hello()` risponde
`isWritablePrimary=false secondary=true`, e la stessa coppia sta nel blocco di console di
[V-023](Sources.md#v-023). Sui tre membri veri, con `rs.status()` che risponde
`NotYetInitialized code=94`, la risposta è un'altra:

```console
mongo-rs-1  isWritablePrimary=false secondary=false isreplicaset=true  ->  espressione del piano = false
mongo-rs-2  isWritablePrimary=false secondary=false isreplicaset=true  ->  espressione del piano = false
mongo-rs-3  isWritablePrimary=false secondary=false isreplicaset=true  ->  espressione del piano = false
```

Quei `secondary=true` venivano da un membro che l'inizializzazione l'aveva già ricevuta. La
*conclusione* di [V-023](Sources.md#v-023) era comunque giusta — «un controllo che chiedesse "sei
primario o secondario?" resterebbe rosso fino a `rs.initiate()`» — ed è la misura di oggi a
confermarla: l'espressione `hello().isWritablePrimary || hello().secondary`, che il Passo 1 del
Task 5 riporta dal design §5.4, vale `false` su tutti e tre. Mentre `hello().ok` vale `1`.

Il Passo 3 del Task 5 aveva già previsto il nodo e chiedeva di scioglierlo «misurando e non
ragionando»: la misura è questa, ed è arrivata due task in anticipo. Il marcatore utilizzabile è
`isreplicaset: true`, che un `mongod` avviato con `--replSet` espone finché non ha ricevuto una
configurazione. La voce formale di [`Sources.md`](Sources.md) nasce al Task 5, dove il Passo 2 la
prevede già; qui resta il verbale, e [V-023](Sources.md#v-023) riceve una nota di precisione in
testa — il corpo non si tocca.

**Note di metodo.**

45. **Un controllo non controlla i file a cui nessuno gliel'ha chiesto.** `make stack-check` ha
    otto regole buone e un elenco di file scritto a mano, e per un commit intero il file nuovo è
    stato fuori dall'elenco: le regole c'erano, il verde era vero, e non voleva dire niente sul
    file appena scritto. Un controllo ha due metà, le regole e l'ambito, e la seconda non si
    verifica leggendo le prime. Il modo di accorgersene è chiedersi, davanti a un verde, *su che
    cosa* è verde — e la risposta deve essere un elenco di nomi, non una sensazione.

46. **Due modi equivalenti per il sistema non sono equivalenti per chi lo controlla.** `mongod` in
    testa al comando o `--replSet` in testa avviano lo stesso processo, e nessuno dei due è
    sbagliato. Ma lo strumento riconosce il primo e non il secondo, quindi la scelta di come
    scrivere il file decide se una regola si applica o no — in silenzio, senza che nessuno prenda
    una decisione consapevole. È la stessa famiglia della nota 42: lì una conferma non poteva
    fallire, qui una regola non poteva scattare. Quando si scrive uno strumento che legge un
    formato, l'insieme delle scritture equivalenti nel formato è parte del formato.

## 2026-08-31 — `feature/02`, Task 4 e 5: la catena si chiude, e «fatto» viene detto due volte

**Perché due task in uno.** Il piano teneva separati il Task 4 (il servizio `rs-init` nel file
Compose) e il Task 5 (lo script `rs.initiate()` che quel servizio esegue). Separarli non era
possibile: `rs-init` dipende dai tre membri con `condition: service_healthy`, e
[`tools/check_stack.py`](../tools/check_stack.py) rifiuta un `service_healthy` verso un servizio
privo di `healthcheck`. Il Task 4 da solo sarebbe dunque nato rosso, e per farlo diventare verde
avrebbe dovuto scrivere l'healthcheck, che è del Task 5 — oppure dichiarare una dipendenza più
debole e correggerla subito dopo, cioè scrivere una cosa sbagliata di proposito per poterla
riscrivere. I due task sono stati fusi e verificati insieme. Il piano non viene modificato: resta
com'era, con questa nota che spiega perché è stato eseguito diversamente.

**Che cosa è stato costruito.** Il servizio `rs-init` in `docker/02-replicaset/compose.yaml` —
one-shot, `restart: "no"`, `network_mode: "service:mongo-rs-1"`, dipendente dai tre membri sani — e
lo script `docker/02-replicaset/init/10-rs-initiate.js` che esegue `rs.initiate()` con i tre membri
elencati per nome di servizio, attende l'elezione del primario e crea l'amministratore sotto
eccezione localhost. Le credenziali arrivano dall'ambiente, e la password non ha valore
predefinito. Con questo lo stack `02-replicaset` è completo: `keyfile-init` → tre `mongod` →
`rs-init`.

**L'idempotenza, e perché non si riconosce dal `catch`.** Lo script deve poter girare due volte.
La forma che viene in mente per prima è tentare `rs.status()` e trattare l'errore
`NotYetInitialized` come «non ancora inizializzato, procedi». Non funziona, e il modo in cui non
funziona è istruttivo: dopo che il primo utente è stato creato, l'eccezione localhost si richiude, e
una `rs.status()` **senza credenziali** su uno stack perfettamente sano non risponde
`NotYetInitialized` — risponde `Unauthorized (13)`. Un `catch` scritto su quel presupposto leggerebbe
uno stack a posto come uno stack rotto. Lo script usa invece `db.hello().setName`, che risponde
senza credenziali in tutti e due i casi: assente prima dell'inizializzazione, presente dopo.
Verificato: il secondo avvio stampa «già formato» e «già presente», ed esce 0.

**La catena, misurata.** Da volumi vuoti, quattro righe e codice 0:

```console
inizializzo il replica set «rs0»
primario eletto: mongo-rs-1:27017
utente amministratore «admin» creato
catena completata
```

Il set è formato con `mongo-rs-1` primario e gli altri due secondari, una scrittura con
`w: "majority"` viene confermata e si rilegge sul membro 3, e la stessa `rs.status()` senza
credenziali viene rifiutata con `Unauthorized (13)`. Il verbale completo è in
[V-024](Sources.md#v-024).

**Il debito di V-023 è saldato.** [ADR-0040](Decision.md#adr-0040) era stato deciso su una prova
che [V-023](Sources.md#v-023) dichiarava incompleta: `network_mode: "service:"` era stato provato
nella forma equivalente `docker run --network container:…`, non dentro un file Compose del
repository. Ora sì, e la prova è netta — l'identificatore che Compose scrive in `NetworkMode` è,
cifra per cifra, l'identificatore del container del membro 1, e nello spazio di rete condiviso
esiste un solo indirizzo, quello del `mongod`. `rs-init` non ha una rete propria: il suo `localhost`
è quello del membro, ed è per questo che l'eccezione localhost lo riconosce.

**Prima scoperta: `up --wait` esce con successo prima che la replica esista.** Misurato: il comando
ritorna 0 dopo otto secondi, `rs-init` in quell'istante è in stato `running`, e chi si collega
riceve `NotYetInitialized (94)`. Lo script finisce quattordici secondi più tardi.

```console
«up -d --wait» uscita=0 dopo 8 secondi
stato di rs-init in quell'istante: running
--- che cosa vede un client in quell'istante ---
NotYetInitialized (94)

rs-init uscito dopo 22 secondi dall'avvio, codice=0
scarto fra «up dice fatto» e «la replica c'e'»: 14 secondi
```

Non è un difetto di Compose. `--wait` è documentato come «Wait services be running|healthy»
([S-057](Sources.md#s-057)) e `rs-init` non ha un healthcheck, quindi la soglia applicabile è
`running` — che un container destinato a morire raggiunge nell'istante in cui comincia. Il rimedio
sta in un secondo comando, `docker compose wait rs-init`, che blocca fino all'uscita e ne riporta il
codice: la catena completa passa allora da otto a venti secondi, e subito dopo il set c'è. Le due
opzioni non sono alternative fra cui scegliere: `up --wait` serve ai tre membri, che devono essere
**sani**, e `compose wait` serve a `rs-init`, che deve essere **finito**. Lo stack ha bisogno di
entrambe perché contiene entrambi i generi di servizio. Registrato in
[ADR-0041](Decision.md#adr-0041), punti uno e tre.

**Seconda scoperta: `--env-file` non aggiunge un file, ne prende il posto.** Lo stack ha bisogno di
due ambienti — il pin dell'immagine in `tools/images.env`, la password in
`docker/02-replicaset/.env` — e passando solo il primo il secondo smette di essere letto, benché sia
accanto al file indicato con `-f`:

```console
uscita di «config» con un solo --env-file: 1
error while interpolating services.rs-init.environment.PASSWORD_AMMINISTRATORE: required variable
PASSWORD_AMMINISTRATORE is missing a value: assente — copiare docker/02-replicaset/.env.example in
.env e riempire la password
```

La documentazione lo dice — «Passing the `--env-file` argument overrides the default file path» —
ma **non sulla pagina dove uno andrebbe a cercarlo**: la pagina intitolata «Environment variables
precedence» non contiene mai quell'affermazione, che sta invece sotto il titolo «Interpolation»
([S-056](Sources.md#s-056)). La flag si può ripetere, e i file si leggono nell'ordine dato. Lo stack
02 si avvia quindi con due `--env-file`, in quest'ordine: prima il pin comune, poi il file dello
stack, che può sovrascriverlo.

**Il dettaglio che ha reso rumoroso l'errore.** Vale la pena guardare *come* si è manifestata la
seconda scoperta: non con un amministratore creato con password vuota, ma con un rifiuto che nomina
il file da copiare. Quel messaggio esiste perché la variabile è scritta nella forma
`${PASSWORD_AMMINISTRATORE:?…}`, decisa al Task 4 quando si è scritto `.env.example`. Nella forma
senza `:?` — che è la forma che quasi tutti scrivono — Compose avrebbe sostituito la stringa vuota,
`createUser` sarebbe riuscito, lo stack sarebbe partito, e l'amministratore del replica set avrebbe
avuto password vuota senza che nessuna riga di output lo dicesse.

**Una misura controintuitiva che non finisce in slide.** Cronometrando dall'avvio alla fine di
`compose wait rs-init`, l'avvio **a caldo** — con i volumi conservati — è risultato più lento di
quello da volumi vuoti: 24 secondi contro 19, 21 e 21. La spiegazione plausibile è che dopo uno
spegnimento completo il set debba rieleggere un primario prima che qualunque cosa funzioni. È il
genere di fatto che si racconta volentieri, ed è esattamente per questo che non è stato messo in
[`citazioni-riportare-slide.md`](citazioni-riportare-slide.md): l'avvio a caldo è stato misurato
**una volta sola**, contro tre giri a freddo, e la causa proposta non è stata isolata da nessuna
misura. Sta nelle riserve di [V-025](Sources.md#v-025) come cosa da rifare con più ripetizioni.

**Controlli.** `make docs-check` verde; `uv run --directory tools pytest -q`, 76 test verdi;
`check_stack.py` sul file 02 con un ambiente unito, conforme; smontaggio con `down -v` verificato —
zero container, zero volumi. Resta aperto il debito del Task 6: `make stack-check` continua a non
conoscere il file 02, `--ambiente` accetta un file solo, e `avvia_mongod` non riconosce la forma di
comando che comincia per trattino.

**Documentazione prodotta.** [S-056](Sources.md#s-056) e [S-057](Sources.md#s-057) fra le fonti
ufficiali; [V-024](Sources.md#v-024) e [V-025](Sources.md#v-025) fra le verifiche empiriche;
[ADR-0041](Decision.md#adr-0041) che le cita e rende obbligatoria la forma d'avvio a due comandi con
due `--env-file`; una voce in [`citazioni-riportare-slide.md`](citazioni-riportare-slide.md).

**Note di metodo.**

47. **Un comando che dice «fatto» sta rispondendo alla sua domanda, non alla tua.** `up --wait`
    aveva ragione: i servizi erano `running|healthy`, che è ciò che dichiara di attendere. Il
    codice 0 era corretto e inutile, perché la domanda a cui rispondeva non era quella che
    interessava. Il controllo da fare, davanti a un'opzione che aspetta qualcosa, è leggere che
    cosa aspetta e confrontarlo con la propria definizione di pronto — parola che in uno stesso
    file può significare *essere su* per un servizio e *essere finito* per quello accanto. Quando
    le due definizioni convivono, un comando solo non può bastare, e cercarne uno che basti è il
    modo di non trovarlo.

48. **L'assenza di una configurazione obbligatoria va scritta in modo che faccia rumore.** La
    stessa dimenticanza — un `--env-file` invece di due — ha prodotto un errore leggibile in otto
    secondi solo perché la variabile era dichiarata `${NOME:?messaggio}`. Nella forma comune
    avrebbe prodotto uno stack funzionante con l'amministratore senza password: un successo
    apparente, che è il modo peggiore in cui un errore di configurazione può presentarsi. La forma
    con `:?` costa un carattere e un messaggio, e il messaggio conviene scriverlo dicendo *che cosa
    fare*, non *che cosa manca*.

49. **Una riserva dichiarata è un debito; un'approssimazione taciuta diventa un presupposto.**
    [V-023](Sources.md#v-023) aveva provato `network_mode:` in una forma equivalente e aveva
    scritto, nero su bianco, che la forma definitiva restava da verificare — e su quella prova
    incompleta è stato deciso [ADR-0040](Decision.md#adr-0040). Decidere su una prova incompleta è
    legittimo; deciderlo senza dirlo non lo è. La riserva scritta è ciò che ha fatto sì che, sei
    ore dopo, qualcuno sapesse ancora che cosa andava misurato. Se non fosse stata scritta, oggi
    non ci sarebbe un errore: ci sarebbe una cosa che tutti danno per provata.

---

## 2026-08-31 — `feature/02`, Task 6: quattro regole nuove, e una vecchia che dormiva

**Il debito che il Task 5 aveva lasciato scritto.** Tre righe, in fondo alla sezione precedente:
`make stack-check` non conosce il file 02, `--ambiente` accetta un file solo, `avvia_mongod` non
riconosce la forma di comando che comincia per trattino. Il Task 6 le chiude tutte e tre, ed è
interessante che la terza — la più piccola — sia quella che ha insegnato qualcosa.

**Che cosa doveva imparare lo strumento.** Lo stack 02 porta tre modi di sbagliare che lo stack 01
non aveva, e sono i tre errori che questa feature ha commesso davvero, uno per Task: un membro senza
`--keyFile` che resta fuori dalla replica facendo sembrare la cosa un problema di rete (Task 2), un
keyfile montato da un percorso dell'host che `mongod` rifiuta per i permessi (Task 2), un
`depends_on` con la condizione sbagliata che riesce sulla macchina veloce e fallisce altrove
(Task 1). Ognuno era costato una misura. Le quattro regole nuove di `check_stack.py` sono quelle
misure trasformate in qualcosa che fallisce prima di avviare i container:
[ADR-0042](Decision.md#adr-0042) le elenca.

**La guardia, che è la parte che si sbaglia.** Il problema di una regola nuova, in un repository che
avrà tre stack, non è scriverla: è impedirle di scattare dove non deve. Lo stack 01 gira senza
autenticazione per scelta didattica, e pretendere un keyfile da lui sarebbe una regola che sbaglia
mira. La strada breve è un elenco di servizi esenti; la strada scelta è che **ogni regola legga il
file per decidere se la riguarda** — la regola sul keyfile si accende solo se qualcuno dichiara
`--replSet`, quella sulle condizioni solo se qualcuno dichiara `depends_on`. Un elenco di eccezioni
è un pezzo di configurazione che invecchia, e invecchia in silenzio: nessuno se ne accorge finché
non serve. Una guardia che legge il file invecchia insieme al file.

**Il difetto vecchio, che è il vero risultato del Task.** `avvia_mongod()` riconosceva un `mongod`
solo quando il comando cominciava con quella parola. L'entrypoint ufficiale antepone `mongod` da sé
quando il primo argomento comincia per trattino ([S-022](Sources.md#s-022)): per Docker `["mongod",
"--replSet", "rs0"]` e `["--replSet", "rs0"]` avviano lo stesso processo, e la seconda forma è
quella che gira in metà degli esempi in rete. Sulla seconda forma lo strumento non vedeva un
`mongod`, quindi non pretendeva la cache, quindi passava. Il file era conforme; la regola non aveva
guardato. Per mesi il bersaglio `stack-check` avrebbe potuto dare il verde a uno stack sbagliato, e
il verde sarebbe stato indistinguibile da quello di oggi.

**La prova che il verde valga qualcosa.** Da qui è nata la cosa che questo Task lascia in eredità.
Le quattro regole erano rosse sui campioni costruiti nei test e verdi sui due file veri — e verde su
un file vero **non prova niente**, perché non distingue «la regola ha guardato e ha approvato» da
«la regola non è mai entrata in funzione». Sono state fatte sei copie dello stack 02, ognuna con un
solo difetto introdotto, e passate allo strumento: sei messaggi distinti, ognuno quello giusto, e il
file intatto verde. È [V-026](Sources.md#v-026). Le mutazioni si introducono verificando prima
quante occorrenze esistono, così una modifica che non attecchisce si presenta come un errore invece
che come un verde — che è lo stesso genere di trappola, un livello più su.

**La password che non poteva stare da nessuna parte.** Un vincolo non ovvio: `make stack-check` deve
girare su un clone appena fatto, dove `docker/02-replicaset/.env` non esiste perché sta fuori dal
repository per [ADR-0014](Decision.md#adr-0014). Lo stack dichiara la password come
`${PASSWORD_AMMINISTRATORE:?…}`, e quella forma — la stessa che al Task 4 aveva reso rumoroso
l'errore — qui si rifiuta di risolversi e ferma il controllo prima della prima regola. La soluzione
diffusa, un `.env.esempio` committato, è stata scartata: mette nel repository un file che *ha la
forma* di un file di credenziali, e in un materiale didattico l'esempio pesa più dell'avvertenza che
lo accompagna. È entrata invece una flag `--variabile NOME=valore`, e il `Makefile` le passa un
valore che dice a voce alta di essere finto. `--ambiente` è diventata ripetibile con la stessa
semantica di `--env-file` di Compose ([S-056](Sources.md#s-056)) — gli ultimi vincono sui primi —
perché due strumenti che si usano nello stesso comando non devono avere due regole diverse per la
stessa cosa.

**Due test che passavano per il motivo sbagliato.** I primi due test scritti sull'ambiente ripetibile
erano verdi *anche senza la funzionalità*: con `--ambiente` non ripetibile `argparse` tiene l'ultimo
valore, e per caso l'esito coincideva. Sono stati resi discriminanti — uno guarda quale messaggio
d'errore esce, non solo il codice; l'altro mette una variabile obbligatoria **solo nel primo file**,
così tenere l'ultimo produrrebbe 2 invece di 0. E un test preesistente è diventato rosso quando è
entrata la regola sul `restart`: la diagnosi è stata che il campione era incompleto, non che la
regola fosse sbagliata, e si è corretto il campione.

**Controlli.** 14 rossi confermati prima di implementare, 95 verdi dopo (erano 76);
`make stack-check` → `Stack conformi: 2.`; `make docs-check` verde; le sei mutazioni di
[V-026](Sources.md#v-026).

**Documentazione prodotta.** [V-026](Sources.md#v-026) fra le verifiche empiriche;
[ADR-0042](Decision.md#adr-0042), che la cita insieme a [S-022](Sources.md#s-022) e
[S-056](Sources.md#s-056). **Nessuna citazione da slide**, ed è una scelta: la nota 50 è la frase
più riportabile uscita da questo Task, ma parla di come si scrivono i controlli, non di MongoDB, e
in un'ora davanti a chi arriva da SQL Server non c'è il posto per una digressione sul metodo di
test. Resta nel registro, dove serve a chi legge il repository.

**Note di metodo.**

50. **Una regola che non può fallire è peggio di una regola che manca.** Chi legge un controllo
    assente sa di non essere coperto; chi legge un verde crede di esserlo. `avvia_mongod` non ha
    mai sbagliato una risposta: non gli è mai stata posta la domanda, perché non riconosceva la
    forma in cui arrivava. Il modo di scoprirlo non è rileggere la regola — chi l'ha scritta la
    rilegge come l'ha pensata — ma **rompere il caso vero e pretendere il rosso**. Vale per ogni
    controllo che passa al primo colpo su materiale che non è stato costruito per farlo passare.

51. **Le guardie si scrivono leggendo, non elencando.** Una regola che vale per alcuni stack ha
    bisogno di sapere quando tacere, e ci sono due modi: un elenco di esenzioni, che è un secondo
    documento da tenere allineato al primo, o una condizione letta dal file stesso. Il primo modo
    è più veloce da scrivere e sbaglia in silenzio al primo stack aggiunto — l'errore non è che la
    regola scatti dove non deve, è che smetta di scattare dove deve. Il secondo costa una riga in
    più oggi e nessuna manutenzione poi.

52. **Un vincolo che sembra un ostacolo di solito difende qualcosa.** La password fuori dal
    repository ha impedito al controllo di girare, e la reazione naturale era ammorbidire il
    vincolo: un `.env.esempio`, o un `:?` in meno. Entrambe avrebbero funzionato, e entrambe
    avrebbero insegnato la cosa sbagliata a chi clona. La domanda giusta non è *come tolgo il
    vincolo*, è *di che cosa ha bisogno lo strumento che il vincolo non gli dà* — qui, un valore
    che esista senza somigliare a una credenziale — e la risposta è quasi sempre più piccola della
    deroga che si stava per concedere.

---

## 2026-08-31 — feature/02, Task 7: i dati di demo, e uno smoke che sa restare in piedi mentre un membro cade

**Deciso.** Lo stack 02 carica i suoi 50 000 ordini come **ultimo passo di `rs-init`**, con
`w: "majority"` e `wtimeout: 10000`, saltando il lavoro se il dataset c'è già e rifacendolo se glielo
si chiede con `RICARICA=1`. Sei bersagli nuovi nel `Makefile` e `tools/smoke-replicaset.sh` con 42
controlli. È [ADR-0043](Decision.md#adr-0043).

**Il quarto servizio che non è stato scritto.** La forma pulita era un servizio `dati-init` a valle
di `rs-init`, e per un quarto d'ora è stata la forma prevista. L'ha fermata
[ADR-0041](Decision.md#adr-0041), scritto poche ore prima: un secondo one-shot vuol dire un secondo
`docker compose wait`, cioè **due verdetti** dove ADR-0041 ne aveva appena stabilito uno solo. Due
verdetti sono la premessa di un `make up-02` che ne guarda uno e ignora l'altro, ed è lo stesso
genere di bug che ADR-0041 era nato per chiudere. Piegare la catena per tenere il verdetto unico ha
prodotto, per caso, la cosa migliore del Task: il caricamento dei dati è la **prima connessione
autenticata** dello stack, e sta nel file subito dopo il `createUser` che ha chiuso l'eccezione
localhost. Chi legge i due script di seguito vede la riga esatta in cui la password comincia a
servire.

**La misura che rispondeva sempre uguale.** Il piano chiedeva il ritardo di replica a riposo. Il
modo canonico è la differenza fra gli `optimeDate` di `rs.status()`, e su questo set risponde
`0 ms`. Tre volte, a cinque secondi di distanza, sempre zero — che non è un risultato, è la
granularità: `optimeDate` viene dal timestamp dell'oplog, che conta secondi. La misura vera si fa
scrivendo con `w: 1` — così il cronometro parte prima che i secondari sappiano qualcosa — e
interrogando un secondario in un ciclo stretto finché il documento non compare: ritardo mediano
**1 ms**, `w: "majority"` mediano **2 ms**. Le medie dicevano 1,6 · 1,9 · 6,2 ms, e sono state
buttate: ogni esecuzione aveva un valore fuori scala (3, 9, 46 ms) ed era sempre **il primo giro**,
cioè la connessione che si apre e si autentica. È [V-027](Sources.md#v-027), con la riserva che
conta scritta per esteso — tre membri sullo stesso portatile non hanno una rete, e quel millisecondo
descrive un bridge Docker, non la produzione.

**Lo smoke che si fermava proprio quando serviva.** `tools/smoke-replicaset.sh` è nato ricalcando
`smoke-standalone.sh`, e ha ereditato il suo cancello d'ingresso: se un nodo non è sano, esci. Su
un'istanza singola è giusto — senza il nodo non c'è niente da chiedere. Provato con `mongo-rs-3`
fermo, lo script usciva dopo tre righe: due verdi e un rosso, e nient'altro. Ma è **esattamente il
momento** in cui uno vuole sapere se c'è ancora un primario, se le scritture passano, se il dataset
è intatto. Il cancello è stato ristretto al caso «il container non esiste», e ora con un membro
fermo lo script dice 34 verdi e 8 rossi, e fra i verdi «primari: 1» e «scrittura con w: majority
accettata». Non è stato dedotto leggendo il codice: è stato visto fermando un container
([V-028](Sources.md#v-028)).

**La copia deliberata.** `20-dati-demo.js` è, per generatore seme epoca e liste, una copia di
`docker/01-standalone/init/20-dati-demo.js`. Fattorizzarli sarebbe stato l'istinto, ed è stato
scartato: i due stack devono poter divergere — sul write concern sono già divergenti — e un file
condiviso farebbe cambiare di nascosto il dataset dello stack 01 a chi tocca il 02. La duplicazione
è dichiarata in testa a entrambi i file e **sorvegliata dove conta**: i due script di prova
controllano la stessa terna `50000 124861860.70 150281`, quindi modificarne uno solo fa diventare
rosso l'altro. L'impronta misurata sullo stack 02 coincide con quella di [V-013](Sources.md#v-013)
al centesimo.

**Un numero di ieri che oggi è falso.** [V-025](Sources.md#v-025) si intitola «`up --wait` esce con
successo *quattordici* secondi prima che la replica esista». Da quando il seed vive dentro `rs-init`
lo scarto è di **ventidue** secondi. Il titolo non è stato riscritto — così è stato misurato quel
giorno, su quella configurazione — ma la voce ha ricevuto una **nota di allineamento in testa**, e
la citazione da slide ha ricevuto un paragrafo che dice di rimisurare la mattina stessa. La
conclusione di ADR-0041 non cambia di una virgola; cambia il numero, ed è la ragione per cui il
numero non va imparato a memoria.

**Controlli.** `make smoke-02` → `Superati: 42 · Errori: 0`, quattro esecuzioni di fila. Avvio a
freddo: `up --wait` 8 s, `compose wait rs-init` altri 22 s, seed di 50 000 documenti in 6 439 ms.
`make seed-02` ricarica in 7 658 ms lasciando l'impronta identica. `make reset-02` lascia in piedi
il solo volume del keyfile, e il segreto è byte per byte lo stesso prima e dopo. Con un membro
fermo: uscita 1, 34/8. Con lo stack giù: uscita 1, 0/3, «Mancano 3 container su 3». `make docs-check`
verde, `make tools-test` 95 verdi, `make stack-check` → `Stack conformi: 2.`

**Documentazione prodotta.** [V-027](Sources.md#v-027) e [V-028](Sources.md#v-028) fra le verifiche;
[ADR-0043](Decision.md#adr-0043), che le cita insieme a [S-022](Sources.md#s-022),
[S-035](Sources.md#s-035), [V-013](Sources.md#v-013) e [V-014](Sources.md#v-014); una citazione da
slide per il Blocco 2 sul costo della maggioranza, con dentro la riserva che la rende dicibile; la
nota di allineamento su [V-025](Sources.md#v-025).

**Note di metodo.**

53. **Uno strumento che risponde sempre la stessa cosa non sta misurando.** `optimeDate` dava
    `0 ms` a ogni lettura, e zero somiglia a una risposta: nessun ritardo. Non era una risposta,
    era la risoluzione dello strumento — un secondo — messa davanti a un fenomeno che vive nei
    millisecondi. È il parente stretto della nota 50, un piano più in là: là un controllo che non
    poteva fallire, qui una misura che non poteva variare. Il test è lo stesso e costa poco:
    **provocare il fenomeno e pretendere che il numero si muova.** Se non si muove, non si è
    misurato niente, e si è sul punto di scriverlo in una slide.

54. **Il primo giro di un ciclo di misura non è un dato.** In tutte e tre le esecuzioni il valore
    fuori scala era il primo, e sempre per lo stesso motivo — la connessione che si apre, la cache
    che si scalda, la pagina che si tocca per la prima volta. Una media su dieci giri di cui uno è
    riscaldamento è una media che descrive il riscaldamento. Si guardano **i valori grezzi e la
    mediana**, in quest'ordine: la mediana perché regge agli estremi, i grezzi perché mostrano
    *dove* stanno gli estremi, che è l'informazione che dice se buttarli è legittimo o comodo.

55. **Un controllo di salute portato da una topologia a un'altra porta con sé le sue assunzioni.**
    «Se un nodo non è sano, smetti di chiedere» è corretto su un'istanza singola e distruttivo su
    tre membri, dove il nodo malato è il motivo per cui si stanno facendo le domande. La copia non
    ha prodotto un errore: ha prodotto uno script che funziona benissimo finché tutto va bene, cioè
    la classe di strumenti che si scopre inutile nell'unico momento in cui la si usa davvero. Un
    diagnostico si prova rompendo qualcosa, e si giudica da **quante domande riesce ancora a
    rispondere**, non da quante ne fallisce.

56. **Una duplicazione dichiarata è più onesta di una fattorizzazione che lega.** Due file identici
    fanno male da guardare, e l'istinto è unirli. Prima conviene chiedersi se sono identici *per
    caso* o *per necessità*: se i due usi possono divergere legittimamente — e qui divergono già,
    sul write concern — un file condiviso trasforma ogni modifica in un effetto collaterale su un
    altro stack. La versione difendibile della copia ha due requisiti: **dichiararla in testa a
    entrambi i file**, e mettere un controllo che diventi rosso se le due copie smettono di
    coincidere dove devono coincidere. Senza il secondo requisito è solo copia-incolla con una
    scusa scritta bene.

---

## 2026-08-31 — feature/02, Task 8: dieci secondi contro mezzo, e il log che dice perché

**Deciso.** Due bersagli distinti per le due scene di failover — `make failover-02` con
`docker kill`, `make failover-02-termina` con lo `shutdown` — più `tools/reset-demo.sh <stack>`,
che salda un debito di `feature/01`. È [ADR-0044](Decision.md#adr-0044).

**Misurato.** `docker kill` sul primario: elezione in **9 812 / 10 619 / 10 943 ms**, container
`exited` con `RestartCount=0` e `ExitCode=137`. `shutdownServer()`: **574 / 480 / 486 ms**,
container di nuovo `running` con `RestartCount` che avanza. **Venti volte di differenza, nel verso
opposto all'intuizione**: il gesto brutale è quello lento. È [V-029](Sources.md#v-029), e conferma
su tre membri quello che [V-017](Sources.md#v-017) aveva misurato su uno solo — dopo un
`docker kill` la politica di riavvio non interviene, perché per il demone quella fermata l'ha
voluta un umano.

**Il debito di ADR-0035 è saldato.** Quella decisione aveva lasciato scritto che gli `id` delle
righe di elezione sarebbero stati inseriti «in `feature/02`, dopo averne vista una». Eccoli, in
[V-030](Sources.md#v-030), e portano con sé il risultato più bello del Task: fra `id=4615652`
(«Starting an election, since we've seen no PRIMARY in election timeout period», con
`electionTimeoutPeriodMillis: 10000` nell'attributo) e `id=21450` («Election succeeded, assuming
primary role») passano **sei millisecondi**. I dieci secondi non sono l'elezione: sono l'attesa
prima di cominciarla. E la caduta è notata dopo **tre decimi di secondo** — `id=21216`, con
«Connection refused» scritto nell'attributo. Il set sa subito e aspetta apposta.

**Un errore evitato per un soffio.** La prima versione dello script stampava le righe di log
dell'**osservatore**, cioè del nodo da cui si guardava. Ma l'osservatore quasi mai è l'eletto: chi
ha solo votato registra `id=23980 Responding to vote request` e nient'altro. Con quel filtro si
sarebbe concluso che un'elezione non lascia quasi traccia nel log — esattamente il contrario di
quello che V-030 dimostra. Lo script legge ora il log del nodo eletto, ricavato dall'esito della
misura.

**Il cronometro parte prima del colpo.** `mongosh` impiega quasi un secondo ad avviarsi e
autenticarsi. Lanciandolo dopo il `docker kill`, quel secondo sarebbe finito dentro la misura e la
scena sarebbe sembrata più lenta del vero. L'osservatore si collega prima, stampa `PRONTO` quando è
caldo, e solo allora chi lo ha lanciato uccide il primario.

**`reset-demo.sh` provato su uno stack sporco davvero.** Un `✓ collezioni rimosse: nessuna` su uno
stack pulito non prova niente — è la lezione della nota 50, un Task più tardi. Sono state create
due collezioni di scarto e cancellati cento `ordini`: lo script ha tolto `scratch` e
`prova_failover`, ha ricaricato il dataset, e l'impronta è tornata `50000 124861860.70 150281` con
lo smoke a 42/0.

**Controlli.** `make failover-02` → elezione in 9 481 ms, `RestartCount=0`, righe di log stampate.
`./tools/reset-demo.sh 02` su uno stack con un membro `exited` → tutto sano, `mongo-rs-1` di nuovo
primario, impronta intatta. `make docs-check` verde.

**Documentazione prodotta.** [V-029](Sources.md#v-029) e [V-030](Sources.md#v-030);
[ADR-0044](Decision.md#adr-0044), che le cita insieme a [S-044](Sources.md#s-044) e
[V-017](Sources.md#v-017); una citazione da slide per il Blocco 2 sui sei millisecondi. La frase
che [ADR-0034](Decision.md#adr-0034) mandava in `citazioni-riportare-slide.md` — «il gesto con cui
tutti simulano un guasto non simula un guasto» — **c'era già** da `feature/01`: il Passo 5 del
piano era soddisfatto prima di cominciare, e non è stato duplicato.

**Note di metodo.**

57. **Il cronometro va acceso prima del colpo, non dopo.** Lo strumento che misura ha un costo di
    avvio, e quel costo finisce dentro la misura se lo si avvia nel momento sbagliato. Qui erano
    quasi mille millisecondi su una scena da cinquecento: avrebbe raddoppiato il risultato della
    scena veloce senza che niente sembrasse strano. Il rimedio costa poche righe — l'osservatore
    dichiara di essere pronto, e solo allora si agisce — ed è la stessa disciplina della nota 54
    vista dall'altro capo: **là si scartava il primo giro, qui lo si tiene fuori dal cronometro.**

58. **Un diagnostico va puntato sull'oggetto giusto, e «giusto» non è «comodo».** Il log
    dell'elezione stava sul nodo eletto; lo script guardava quello dell'osservatore, perché
    l'osservatore era la variabile che aveva già in mano. Non avrebbe dato errore: avrebbe dato
    *poche righe plausibili*, che è il modo in cui uno strumento sbagliato passa inosservato. Il
    controllo che smaschera questi casi è chiedersi **quale nodo/processo/file dovrebbe contenere
    la prova**, e verificarlo prima di credere a un output scarno.

---

## Punto di ripresa — sospensione del 2026-08-31, sera

Sessione chiusa per limite, non per fine del lavoro. Si riprende con una sessione intera.

**Deciso e chiuso.** I Task 3, 4, 5, 6, 7 e 8 di `feature/02` sono committati e spinti su
`feature/02-stack-replicaset`. Lo stack 02 si avvia, si semina, si prova e sa cadere:
`up-02`, `down-02`, `reset-02`, `logs-02`, `seed-02`, `smoke-02`, `reset-demo-02`, `failover-02`,
`failover-02-termina`, più `reset-demo-01`. ADR da 0038 a 0044, verifiche da V-020 a V-030.

**Misurato oggi, e da non rimisurare.** Ritardo di replica a riposo 1 ms mediano, `w: "majority"`
2 ms ([V-027](Sources.md#v-027)); stack end-to-end e 42 controlli ([V-028](Sources.md#v-028));
failover 10 s contro 0,5 s ([V-029](Sources.md#v-029)); le righe di log dell'elezione
([V-030](Sources.md#v-030)).

**Prossimo passo, in ordine.**

1. **Chiudere il Task 8 misurando la maggioranza persa** — due membri su tre fermi, il set che
   diventa di sola lettura. È il caso che spiega perché i membri sono tre e non due, è dichiarato
   scoperto in [ADR-0043](Decision.md#adr-0043) e in [ADR-0044](Decision.md#adr-0044), e non è
   stato misurato. Serve prima del Task 9, che dovrà scriverlo.
2. **Task 9** — `docs/02-architetture/replica-set.md`, con i numeri misurati e non stimati.
3. **Task 12** — la pagina delle trappole ha ora quattro debiti aperti: il keyfile a 644,
   `--env-file` che sostituisce e non aggiunge, `up --wait` che esce presto, e il `$$` di Compose.
   Al Task 12 spetta anche togliere da `docs/03-amministrazione/log.md` la riserva di
   [ADR-0035](Decision.md#adr-0035), ora che gli `id` esistono in [V-030](Sources.md#v-030).
4. **Task 14** — la PR. **Mai `git flow feature finish`**: salta la revisione, ed è già successo
   con la PR #1.

**Attenzione per chi riprende.** Lo stack 02 è rimasto **avviato e sano** a fine sessione, con
l'impronta a posto. Se i container non ci fossero più, `make up-02` li ricrea; se ci fossero ma
malmessi dopo una prova, `./tools/reset-demo.sh 02` è più veloce.

---

## 2026-09-01 — `feature/02`, Task 8 (seguito): la maggioranza persa, e un log che taceva

**Deciso.** Una **terza** scena di failover, `make failover-02-maggioranza`, e un lettore di log che
controlla la propria fonte prima di crederle. È [ADR-0045](Decision.md#adr-0045).

**Deviazione dal piano, dichiarata.** Il Task 8 del
[piano](00-progetto/2026-08-31-piano-feature-02-stack-replicaset.md) ha sei passi e **nessuno**
nomina la maggioranza persa. Il piano non si tocca — è la regola del repository — quindi la
deviazione si spiega qui. Il motivo: [ADR-0043](Decision.md#adr-0043) e
[ADR-0044](Decision.md#adr-0044) dichiarano quel caso scoperto, e il Task 9 dovrà **scriverlo**.
Misurarlo dopo averlo scritto sarebbe stato l'ordine sbagliato.

**Misurato.** Fermando due membri su tre, il superstite si retrocede a `SECONDARY` in
**9 364 / 9 136 / 9 331 / 9 334 / 9 327 / 9 316 ms** — sei esecuzioni, mediana **9 329 ms**. Nove e
non dieci perché i 10 000 ms di `electionTimeoutMillis` si contano dall'**ultimo battito ricevuto**,
non dal colpo, e i battiti vanno ogni 2 000 ms: la misura cade fra 8 e 10 secondi a seconda di dove
capita il colpo. Impostazioni lette da `rs.conf()`, non supposte. È
[V-031](Sources.md#v-031).

La riga che chiude la scena è `id=21809`, «Can't see a majority of the set, **relinquishing**
primary». Non «ho perso la connessione»: «non vedo una maggioranza, quindi cedo». Stessa forma di
[V-030](Sources.md#v-030) — la caduta è notata in **quattro decimi di secondo**, e i nove che
seguono sono attesa deliberata.

**Il tranello della scena.** Il superstite retrocesso **legge ancora**: da `mongosh --host` escono
tutti e 50 000 i documenti, perché `mongosh` aggiunge `directConnection=true` da sé quando la
stringa non nomina un `replicaSet` ([S-045](Sources.md#s-045)). Chi prova la demo così conclude che
il set funziona. Le scritture rispondono `NotWritablePrimary` (code 10107), e con l'URI del replica
set e `readPreference` predefinita il driver non trova nessun server. Lo script stampa tutte e
quattro le risposte, perché la confusione è facile da fare e cara da fare in produzione.

**Trovato per caso, e più grave della scena.** Lavorando alla demo, `docker logs` ha smesso di
mostrare qualunque cosa. Il container era partito alle 08:05, `RestartCount=0`, `healthy`, e mongod
aveva scritto **2 548 righe** — `docker logs` ne mostrava **zero**, ferma all'ultima riga della sera
prima, l'istante in cui il demone Docker era caduto. Nessun errore: silenzio. Un container creato in
quel momento veniva catturato normalmente, quindi non è il demone a non catturare: è la cattura dei
container **preesistenti** al suo riavvio a non ripartire. E non è nemmeno stabile — un'ora dopo era
ripresa **da sola** su due membri su tre, lasciando un buco di nove minuti e mezzo che non si è più
richiuso. È [V-032](Sources.md#v-032).

Conta perché la sezione «righe di log» di **tutte e tre** le scene legge `docker logs`. Ora, prima
di leggere, lo script confronta l'ultima riga catturata con `.State.StartedAt`: se il log è più
vecchio dell'avvio non può essere di questa esecuzione, e le righe si chiedono a mongod con
`getLog: "global"`, stampando una riga che dice di essere ripiegato. Il confronto è **stretto** — a
parità di secondo si ripiega — perché chiedere a mongod non costa niente, mentre credere a un log
vecchio costa la scena.

**Il rilevatore ha un test, e il test è stato verificato non vuoto.**
`tools/tests/test_failover_log.py` estrae la funzione dallo script con `sed` — nessuna copia, che
divergerebbe — e la esegue con `docker` sostituito da un finto. I quattro casi sono costruiti sugli
istanti veri di [V-032](Sources.md#v-032). Rimettendo il difetto (`>=` al posto di `>`) la suite
segna **1 failed, 4 passed**: la prova serve davvero.

**Controlli.** `make failover-02-maggioranza` → **9 316 ms** e sette righe di log stampate.
`./tools/reset-demo.sh 02` → `mongo-rs-1` di nuovo primario, collezione di scarto
`prova_maggioranza` rimossa, impronta `50000 124861860.70 150281`. `bash -n` pulito.
`make tools-test` **100 passed** (erano 95). `make docs-check` verde su citazioni e collegamenti.
`make stack-check` → 2 stack conformi. `./tools/smoke-replicaset.sh` → **42 · 0**.

**Documentazione prodotta.** [V-031](Sources.md#v-031) e [V-032](Sources.md#v-032);
[ADR-0045](Decision.md#adr-0045), che le cita insieme a [S-033](Sources.md#s-033),
[S-035](Sources.md#s-035), [S-044](Sources.md#s-044) e [S-045](Sources.md#s-045); una citazione da
slide nel Blocco 2 — «tre membri, maggioranza due: un guasto tollerato» — con la sottrazione che
spiega perché i membri non sono due.

**Note di metodo.**

59. **Un diagnostico può essere morto mentre l'oggetto è vivo.** La nota 58 diceva di puntare lo
    strumento sull'oggetto giusto. Questa è il grado successivo: lo strumento era puntato bene,
    l'oggetto stava benissimo, e la **sorgente** in mezzo si era fermata. Un output vuoto non
    distingue «non è successo niente» da «non te lo sto più raccontando», e nessuno dei due dice
    quale dei due sia. Il controllo che li separa è confrontare la prova con un **istante
    indipendente** — qui l'avvio del container — invece di fidarsi del fatto che una risposta sia
    arrivata. Vale ogni volta che si legge un log attraverso qualcosa che non l'ha scritto.

60. **Una finestra di coda è un filtro implicito, e i cicli d'attesa la riempiono.** Le righe si
    leggevano con `tail -600`, che sembrava abbondante. Un ciclo d'attesa che riapriva `mongosh`
    ogni mezzo secondo ha prodotto circa **800 righe** di `NETWORK` e `ACCESS` in pochi minuti,
    spingendo fuori dalla finestra proprio le righe di `REPL` che si cercavano. Lo strumento con
    cui si aspettava l'evento ha cancellato la prova dell'evento. Quando si legge una coda di log,
    la domanda da farsi non è «quante righe mi servono» ma «quante ne scrive, nel frattempo, chi
    sta guardando».

---

## Punto di ripresa — 2026-09-01

**Deciso e chiuso.** Il Task 8 di `feature/02` è chiuso **per intero**, maggioranza persa compresa.
Lo stack 02 ha tre scene di failover — `failover-02`, `failover-02-termina`,
`failover-02-maggioranza` — e un lettore di log che non si fida di `docker logs`. ADR da 0038 a
**0045**, verifiche da V-020 a **V-032**.

**Misurato oggi, e da non rimisurare.** Retrocessione per maggioranza persa **9,3 s** su sei
esecuzioni, forbice teorica 8–10 s ([V-031](Sources.md#v-031)); rientro dei due membri 9–12 s; il
congelamento di `docker logs` dopo un riavvio del demone ([V-032](Sources.md#v-032)).

**Prossimo passo, in ordine.**

1. **Task 9** — `docs/02-architetture/replica-set.md`, con i numeri misurati e non stimati. Deve
   contenere la sottrazione per esteso: tre membri, maggioranza due, **un** guasto tollerato in
   scrittura — la scena la mostra, la pagina la deve dire.
2. **Task 12** — la pagina delle trappole ha ora **sei** debiti aperti: il keyfile a 644,
   `--env-file` che sostituisce e non aggiunge, `up --wait` che esce presto, il `$$` di Compose, il
   congelamento di `docker logs` ([V-032](Sources.md#v-032)), e l'errore
   `getaddrinfo ENOTFOUND` che nel lab prende il posto di un errore di selezione del server, perché
   un container fermo sparisce dal DNS di Compose ([V-031](Sources.md#v-031)) — la regola 1 di
   [ADR-0035](Decision.md#adr-0035) applicata ai messaggi dei driver. Al Task 12 spetta anche
   togliere da `docs/03-amministrazione/log.md` la riserva di [ADR-0035](Decision.md#adr-0035), ora
   che gli `id` esistono in [V-030](Sources.md#v-030).
3. **Task 14** — la PR. **Mai `git flow feature finish`**: salta la revisione, ed è già successo
   con la PR #1.

**Attenzione per chi riprende.** Lo stack 02 è **avviato, sano e con l'impronta a posto**; lo smoke
è stato rieseguito a fine sessione e fa 42/0. Se i container non ci fossero più, `make up-02` li
ricrea; se ci fossero ma malmessi dopo una prova, `./tools/reset-demo.sh 02` è più veloce. E se una
sezione «righe di log» stampasse il nulla, non è la scena che non è successa: è
[V-032](Sources.md#v-032), e lo script ora lo dice da sé.

---

## 2026-09-01 — `feature/02`, Task 9: la pagina del replica set, e il numero gemello che mancava

Il Task 9 chiede una pagina che risponda alla domanda lasciata aperta dallo stack 01 — **cosa si
ottiene** in più, e a quale prezzo. Cinque passi: topologia ed elezioni, write concern e read
preference come coppia, il confronto con l'istanza singola, il file Compose riga per riga,
`docs-check` e commit. Tutti e cinque sono stati eseguiti; due di essi hanno prodotto materiale che
il piano non prevedeva, e vale la pena dire perché.

**Il piano non è stato modificato, e la deviazione è dichiarata qui.** Il Passo 2 dà per scontato
che la read preference si possa spiegare con quello che il repository ha già. Non era vero: fra le
fonti registrate non ce n'era **nessuna** sulla read preference. Scriverla a memoria avrebbe
violato la regola di `Sources.md` — ogni affermazione tecnica cita almeno una voce — quindi la fonte
è stata cercata e registrata come [S-058](Sources.md#s-058), MongoDB Manual 7.0. Il ritrovamento
utile è che la frase del manuale sul modo `primary` — «If the primary is unavailable, read
operations produce an error or throw an exception» — è la controparte in prosa esatta di quello che
[V-031](Sources.md#v-031) aveva misurato il giorno prima senza saperlo.

**Il Passo 3 è stato misurato invece che argomentato.** [ADR-0032](Decision.md#adr-0032) rimanda a
questo branch il confronto sulla perdita di dati, e sull'istanza singola quel confronto ha un numero
che fa male: **100 scritture confermate al client e sparite** ([V-016](Sources.md#v-016)). Il numero
gemello non esisteva, e una pagina che avesse scritto «sul replica set i dati sono al sicuro»
sarebbe stata esattamente il tipo di frase che questo repository non scrive. La prova è stata
rifatta identica sullo stack 02 — scrittore con `w: "majority"`, `docker kill` sul primario a metà
corsa — ed è [V-033](Sources.md#v-033): **12 901 confermate, 0 perdute**, collezione completa senza
buchi.

**E la metà scomoda, che sta nella pagina con la stessa evidenza dell'altra.** Su 12 902 tentativi
l'applicazione ha visto **un** errore, `ERR 2698 connection … closed` — e il documento `n=2698` nel
database **c'è**. Scritto e mai confermato: l'immagine speculare della perdita sullo standalone. Là
il client crede di avere dati che non ha, qui crede di non avere dati che ha; la differenza è che il
secondo caso si sopravvive, **a patto che la scrittura si possa rifare senza danno**, e la
condizione va detta. Registrata anche la ragione per cui la scena sembra più bella di com'è: quasi
tutta l'invisibilità del guasto la fanno i **retryable write**, attivi per impostazione predefinita,
che hanno tenuto appesa una `insertOne` per **10 155 ms** invece di farla fallire. La prova con
`retryWrites=false` non è stata fatta, ed è dichiarata fra le cose che la pagina non dice.

**La pagina.** `docs/02-architetture/replica-set.md`, nella forma di `standalone.md`: sei sezioni,
«Cosa questa pagina non dice» in coda, piè di pagina con decisioni e fonti. Apre con la
sottrazione — tre membri, maggioranza due, **un** guasto tollerato — perché è la domanda a cui la
scena risponde senza dirla. Ogni numero porta la riserva sulla stessa riga e non in nota: il
millisecondo di `w: "majority"` è un salto su un bridge locale, i 9,3 secondi sono una forbice 8–10,
e i dieci secondi dell'elezione sono attesa deliberata, non elezione — che dura **sei
millisecondi**.

**I rimandi sono in tutte e due le direzioni.** `standalone.md` riceve cinque collegamenti nei punti
in cui prometteva un seguito: il failover che non c'è, `w: "majority"` che mente, il paragrafo dei
cento documenti persi — dove ora compare il numero gemello — la manutenzione che vuole una finestra
di fermo, e la domanda finale «quanto costa il tempo in cui non risponde nessuno». In `docs/README.md`
la riga passa da promessa a collegamento.

**Controlli.** `make docs-check` verde su citazioni e collegamenti — che qui conta più del solito,
perché `check_links.py` verifica anche le ancore generate dai titoli, e le quattro usate nei rimandi
inversi (`#1-perché-i-membri-sono-tre`, `#2-le-elezioni-cronometrate`,
`#31-qui-w-majority-vuol-dire-qualcosa`, `#4-il-confronto-con-listanza-singola`) sono state scritte
a mano e confermate dalla macchina. `make tools-test` **100 passed**. `make stack-check` → 2 stack
conformi. `./tools/smoke-replicaset.sh` → **42 · 0**. Lo stack è stato rimesso a posto dopo la prova
distruttiva: collezione di scarto `prova_perdita` rimossa, impronta `50000 124861860.70 150281`.

**Documentazione prodotta.** [S-058](Sources.md#s-058) e [V-033](Sources.md#v-033);
[ADR-0046](Decision.md#adr-0046), che le cita insieme a [S-035](Sources.md#s-035),
[S-037](Sources.md#s-037), [S-044](Sources.md#s-044), [V-016](Sources.md#v-016),
[V-027](Sources.md#v-027), [V-029](Sources.md#v-029), [V-030](Sources.md#v-030) e
[V-031](Sources.md#v-031); `docs/02-architetture/replica-set.md`; una citazione da slide nel
Blocco 2 — «cento contro zero, misurato sulla stessa prova».

**Note di metodo.**

61. **Il numero gemello vale il doppio del numero.** Cento scritture perse, da sole, sono un
    aneddoto sullo standalone. Zero scritture perse, da sole, sono pubblicità per il replica set.
    Le due misure **accanto**, ottenute con lo stesso gesto nello stesso pomeriggio, sono l'unica
    forma in cui il confronto significa qualcosa. Il costo è rifare una prova che si era già fatta
    una volta; il guadagno è che nessuno debba fidarsi di un aggettivo. Quando una pagina confronta
    due architetture, la domanda da farsi è se il secondo numero esiste o è sottinteso.

62. **La buona notizia si pubblica insieme al suo prezzo, o non è una notizia.** «Zero perse» era
    vero e sarebbe stato incompleto: nella stessa prova un documento è finito nel database senza che
    il client lo sapesse, e l'invisibilità del guasto era merito di un meccanismo del driver, non
    della replica. Tenere le tre cose sulla stessa pagina costa qualche riga e toglie alla slide un
    po' di brillantezza. La alternativa è che a scoprire il prezzo sia il pubblico, sei mesi dopo,
    in produzione — e a quel punto il costo lo paga qualcun altro.

63. **Una regola che vieta di scrivere senza fonte è una regola che manda a cercare la fonte.** Il
    vincolo di `Sources.md` avrebbe potuto essere aggirato in tre modi: non parlare di read
    preference, parlarne senza citare, o citare una fonte vicina fingendo che dicesse la stessa
    cosa. Il quarto modo — cercare la fonte che manca — è costato mezz'ora e ha prodotto la frase
    che tiene insieme la sezione. Le regole che ostacolano vanno usate come indice di ciò che
    manca, non come ostacoli da aggirare.

---

## Punto di ripresa — 2026-09-01, seconda sospensione

**Deciso e chiuso.** Il Task 9 di `feature/02` è chiuso: `docs/02-architetture/replica-set.md`
esiste, con i numeri misurati e le riserve accanto ai numeri. `standalone.md` ha i cinque rimandi
inversi e il rimando di [ADR-0032](Decision.md#adr-0032) è **saldato**. ADR da 0038 a **0046**,
verifiche da V-020 a **V-033**, fonti fino a **S-058**.

**Misurato oggi, e da non rimisurare.** Perdita di dati sul replica set con `w: "majority"` e
primario ucciso: **0 su 12 901 confermate**, un errore per il documento `n=2698` che nel database
c'è, pausa di **10 155 ms** dovuta ai retryable write ([V-033](Sources.md#v-033)).

**Prossimo passo, in ordine.**

1. **Task 10** — `docs/03-amministrazione/backup-restore.md`. La pagina esiste in questo branch e
   non prima perché `mongodump --oplog` **richiede** un oplog. Il piano è netto su un punto: i
   comandi che finiscono nella pagina sono comandi **eseguiti**, e il restore si verifica contando
   i documenti e confrontando l'impronta, come fa `smoke-02`.
2. **Task 11** — `docs/03-amministrazione/sicurezza-keyfile-x509.md`. La cartella
   `docs/04-sicurezza/` non esiste: la pagina va dove la mette il piano.
3. **Task 12** — la pagina delle trappole, con i **sei** debiti già elencati nel punto di ripresa
   precedente, che restano tutti aperti.
4. **Task 13** — `docs/05-talk/registrazioni/` e le prime registrazioni.
5. **Task 14** — ADR, fonti e chiusura del branch con la PR. **Mai `git flow feature finish`**.

Il punto di ripresa precedente nominava solo i Task 9, 12 e 14: era un elenco parziale, non una
decisione di saltare gli altri. Del piano di `feature/02` restano aperti **tutti** i task dal 10 al
14, e questa è la loro lista completa.

**Attenzione per chi riprende.** Lo stack 02 è avviato e sano, impronta `50000 124861860.70 150281`,
smoke 42/0 rieseguito a fine sessione. La prova di [V-033](Sources.md#v-033) crea una collezione di
scarto `prova_perdita`: se ricomparisse, `./tools/reset-demo.sh 02` la toglie.

---

## 2026-09-01 — `feature/02`, Task 10: il backup si documenta dopo averlo rotto

Il Task 10 chiede cinque passi: `mongodump` e `mongorestore` **eseguiti**, che cosa `--oplog`
garantisce e cosa no — con il fallimento per finestra di oplog mostrato **mentre fallisce** — il
restore verificato contando, le riserve dichiarate con la fonte, e `docs-check`. Tutti e cinque
eseguiti. Tre punti sono andati diversamente da come il piano se li aspettava, e vale la pena
scrivere quali.

**Il piano non è stato modificato; le deviazioni sono dichiarate qui.** Il Passo 2 chiede di
mostrare il fallimento sullo stack del lab. Non si può: la finestra dell'oplog di questo stack è di
**15,09 ore** dentro 2 032 MB riempiti al 6 % ([V-034](Sources.md#v-034)), e per superarla servirebbe
un dump di ore. Ridurre l'oplog dello stack non è una strada — `replSetResizeOplog` non scende sotto
~990 MB, e sporcherebbe lo stack che serve alle altre demo. Il guasto è stato quindi riprodotto su
un'**istanza usa-e-getta**, con l'immagine pinnata, senza keyfile e senza autenticazione, rimossa a
prova finita con `docker rm -f -v`.

**Il primo tentativo non è fallito, ed è la cosa più utile della giornata.** Con `--oplogSize 1` e
nient'altro, l'oplog **non** si è fermato a 1 MB: è arrivato a 429 MB con una finestra di 131
secondi, e il dump è passato. La spiegazione sta nel log del server, id **22402**: il taglio
dell'oplog è vincolato da un `pinnedOplogTimestamp`, cioè dall'ultimo checkpoint, perché il motore
non butta via voci che servirebbero a ripartire dopo un crash. I checkpoint sono ogni **60 secondi**.
Ne discende una cosa che nessuna pagina consultata dice: **la finestra dell'oplog non scende sotto
l'intervallo di checkpoint**, per quanto piccolo si faccia l'oplog. Con `--syncdelay 1` la finestra è
crollata a **1 secondo**, e il dump da 1,5 GB durato 3,4 secondi è finito come doveva:
`Failed: oplog overflow: mongodump was unable to capture all new oplog entries during execution`,
uscita **1** ([V-036](Sources.md#v-036)).

**Il pezzo che nessuno si aspetta.** Il comando fallisce **dopo** aver scritto tutte le collezioni:
sul disco restano 1,8 GB di BSON, completi e apribili, senza `oplog.bson` e senza `prelude.json`.
Non è un backup e ne ha tutto l'aspetto. L'unico segnale è il codice di uscita, cioè la cosa che gli
script di backup scritti in fretta non controllano. È la riga più utile della pagina, ed è finita
anche fra le citazioni da slide.

**Il Passo 4 chiedeva la riserva «con la fonte», e la fonte non era quella prevista.** Il piano dà
per scontato che il limite di `mongodump` per i database grandi sia dichiarato dalla pagina di
`mongodump`. Non lo è. Quella pagina elenca le combinazioni vietate e le operazioni che fanno
fallire il dump ([S-011](Sources.md#s-011)), ma **non nomina** il rotolamento dell'oplog e non dice
niente sulla dimensione del database. La dichiarazione sta altrove, nella pagina dei metodi di
backup — «tools for backing up and restoring **small** MongoDB deployments», con RTO alto, RPO alto e
coerenza «Not guaranteed» — registrata come [S-060](Sources.md#s-060). Registrata insieme alla
pagina di `mongorestore`, [S-059](Sources.md#s-059), che mancava del tutto.

**Dove la fonte e la misura non vanno d'accordo, si scrivono tutte e due.** La tabella di
[S-060](Sources.md#s-060) assegna a `mongodump` «impact on source: High, requires write lock». Sullo
stack, durante i **50 ms** del dump, le scritture sono proseguite e i documenti scritti in quella
finestra sono nel database ([V-035](Sources.md#v-035)). La dichiarazione dell'editore resta citata,
l'osservazione resta accanto, e la contraddizione resta visibile: risolverla scegliendo la versione
più comoda sarebbe stato più ordinato e meno vero.

**Il numero che dà senso a `--oplogReplay`.** Stesso file di dump, ripristinato due volte su una
destinazione svuotata: **733** documenti senza l'opzione, **740** con, `applied 12 oplog entries`.
Sette. Su un dump da cinquanta millisecondi sette documenti sono un aneddoto — e la pagina lo dice —
ma su un dump da mezz'ora sono mezz'ora di scritture. Più interessante è il terzo numero: alla fine
del dump i documenti erano **741**. Il punto di ripristino non è l'ultima riga di log del comando, è
l'istante dell'**ultima voce di oplog catturata**, e cade dentro l'esecuzione. Un documento scritto
in quel respiro finale è nel database e non nel backup ([V-035](Sources.md#v-035)).

**Una misura in più, che il piano non chiedeva.** [S-059](Sources.md#s-059) dichiara che
`--oplogReplay` non convive con le opzioni che restringono l'ambito del restore. Restava da sapere
**quando** se ne accorge: `mongorestore --oplogReplay --nsInclude 'lab.*'` risponde
`cannot use --oplogReplay with includes specified` con **zero documenti** toccati
([V-037](Sources.md#v-037)). Due righe di prova trasformano una nota della documentazione in un
fatto mostrato, ed è il rapporto costo/valore migliore della sessione.

**Controlli.** `make docs-check` verde — al primo giro ha bocciato cinque collegamenti perché
l'ancora esplicita `<a id="adr-0047"></a>` mancava: la convenzione degli ADR non si deduce dal
titolo, e il controllo l'ha ricordato al posto mio. `make tools-test` **100 passed**.
`make stack-check` → 2 stack conformi. `./tools/smoke-replicaset.sh` → **42 · 0**. Prima dello
smoke: istanza usa-e-getta rimossa, `/tmp/dump-02` cancellato da dentro `mongo-rs-1`,
`./tools/reset-demo.sh 02` eseguito due volte — collezione di scarto `movimenti` rimossa, impronta
`50000 124861860.70 150281`.

**Documentazione prodotta.** [S-059](Sources.md#s-059) e [S-060](Sources.md#s-060);
[V-034](Sources.md#v-034), [V-035](Sources.md#v-035), [V-036](Sources.md#v-036) e
[V-037](Sources.md#v-037); [ADR-0047](Decision.md#adr-0047), che le cita insieme a
[S-011](Sources.md#s-011) — la quale, citata dal solo [ADR-0022](Decision.md#adr-0022) dai tempi di
`feature/01`, acquisisce il suo secondo ADR; `docs/03-amministrazione/backup-restore.md`, prima
pagina della sezione `03-amministrazione` scritta in questo branch; tre citazioni da slide nella
sezione «Backup e restore».

**Note di metodo.**

64. **Quando la fonte primaria tace, il limite esiste lo stesso.** La pagina di `mongodump` non
    nomina il modo in cui `--oplog` fallisce davvero, e il programma ha il messaggio d'errore
    pronto. Di fronte a un silenzio del genere ci sono tre mosse: dedurlo e scriverlo come se fosse
    documentato, tacerlo perché non c'è la citazione, oppure provocarlo e registrare **due** cose —
    il comportamento misurato e il fatto che la fonte non lo dichiari. La terza costa un
    esperimento e produce l'unica affermazione difendibile. Il silenzio di una fonte è
    un'informazione, e va scritto come tale.

65. **Un esperimento forzato si pubblica con il suo fattore di compressione.** Per far fallire il
    dump in tre secondi sono serviti un oplog da 1 MB e un checkpoint al secondo: due valori che in
    produzione non esistono. Il meccanismo e il messaggio d'errore sono quelli veri; la scala no. Se
    lo si dice, la dimostrazione resta onesta e insegna. Se non lo si dice, il pubblico torna a casa
    convinto che `mongodump` fallisca dopo tre secondi, cioè con un'idea peggiore di quella che
    aveva prima. La differenza fra le due versioni sono due righe.

66. **Il tentativo che non funziona è materiale, non scarto.** `--oplogSize 1` non ha fatto fallire
    niente, e nel capire perché è venuto fuori il fatto più utile della giornata: la finestra
    dell'oplog ha un pavimento, ed è l'intervallo di checkpoint. Chi rimpicciolisce l'oplog per
    risparmiare spazio scoprirà che sotto una certa soglia non risparmia niente. Quel fatto non era
    nell'obiettivo, non è in nessuna pagina consultata, ed è finito in [V-036](Sources.md#v-036) e
    nella pagina. La tentazione, in quel momento, era cancellare il tentativo fallito e rifarlo
    meglio.

---

## Punto di ripresa — 2026-09-01, terza sospensione

**Deciso e chiuso.** Il Task 10 di `feature/02` è chiuso:
`docs/03-amministrazione/backup-restore.md` esiste, con i comandi eseguiti, i numeri misurati e il
fallimento mostrato mentre fallisce. ADR da 0038 a **0047**, verifiche fino a **V-037**, fonti fino
a **S-060**.

**Misurato oggi, e da non rimisurare.** Finestra dell'oplog dello stack 02: **15,09 ore** in
2 032 MB al 6 % ([V-034](Sources.md#v-034)). Dump a caldo sotto scrittura: **50 ms**, 12 voci di
oplog; restore **733** senza `--oplogReplay` e **740** con, contro **741** presenti a fine dump
([V-035](Sources.md#v-035)). Fallimento «oplog overflow» riprodotto con oplog da 1 MB e
`--syncdelay 1`, che lascia 1,8 GB di BSON senza `oplog.bson` e uscita **1**
([V-036](Sources.md#v-036)). `--oplogReplay` con `--nsInclude`: rifiuto a monte, zero documenti
toccati ([V-037](Sources.md#v-037)).

**Prossimo passo, in ordine.**

1. **Task 11** — `docs/03-amministrazione/sicurezza-keyfile-x509.md`. La cartella
   `docs/04-sicurezza/` non esiste: la pagina va dove la mette il piano.
2. **Task 12** — la pagina delle trappole, con i **sei** debiti aperti: il keyfile a 644,
   `--env-file` che sostituisce invece di aggiungere, `up --wait` che esce presto, la trappola del
   `$` in Compose, il congelamento di `docker logs` ([V-032](Sources.md#v-032)) e l'artefatto
   `getaddrinfo ENOTFOUND` di [V-031](Sources.md#v-031); più la rimozione della riserva di
   [ADR-0035](Decision.md#adr-0035) da `docs/03-amministrazione/log.md`.
3. **Task 13** — `docs/05-talk/registrazioni/` e le prime registrazioni.
4. **Task 14** — ADR, fonti e chiusura del branch con la PR. **Mai `git flow feature finish`**.

**Attenzione per chi riprende.** Lo stack 02 è avviato e sano, impronta `50000 124861860.70 150281`,
smoke **42 · 0** rieseguito a fine sessione. Non restano container usa-e-getta né dump dentro i
container. Se una prova futura avesse bisogno di una finestra di oplog stretta, la ricetta è in
[V-036](Sources.md#v-036) e va usata **solo** su un'istanza separata: `--syncdelay` non si tocca
sullo stack del lab.

---

## 2026-09-01 — `feature/02`, Task 11: il keyfile si difende dicendo a quali condizioni la fonte lo ammette

Il Task 11 chiede cinque passi: perché il lab usa il keyfile, perché MongoDB lo riserva a test e
sviluppo con le parole della fonte, come si passa a X.509, la distinzione fra utenti del cluster e
utenti locali a un nodo, e `docs-check`. Tutti e cinque eseguiti. Due sono andati oltre quello che il
piano chiedeva, e uno è costato tre tentativi.

**Il piano non è stato modificato; le deviazioni sono dichiarate qui.** Il Passo 3 dice «le
differenze concrete … se qualcosa non è stato eseguito su questo branch, è marcato come non
eseguito». La lettura minima era: descrivere X.509 dalla documentazione e marcare tutto come non
eseguito. È stata scelta la lettura massima — **eseguire quello che si poteva eseguire** su istanze
usa-e-getta con l'immagine pinnata — e ha prodotto tre fatti che nessuna delle tre pagine
consultate scrive.

**Il primo fatto è un rifiuto all'avvio.** `mongod --clusterAuthMode sendKeyFile` **non parte** senza
TLS: `BadValue: need to enable TLS via the tlsMode flag`, uscita 1. `sendKeyFile` è il modo di
*transizione*, quello che continua a mandare il keyfile e serve solo a non fermare il cluster
durante la migrazione. Se non parte senza TLS, allora il primo passo della migrazione verso X.509
non riguarda i certificati di membro: riguarda TLS, cioè tutti i client
([V-039](Sources.md#v-039)). È la riga che cambia la stima dei tempi, ed è finita anche fra le
citazioni da slide.

**Il secondo è sull'ordine.** [S-062](Sources.md#s-062) presenta i due `setParameter` del secondo
passo uno sotto l'altro, senza dire che il primo abiliti il secondo. Invertendoli, `clusterAuthMode`
viene rifiutato: `Illegal state transition … need to enable SSL for outgoing connections`. Il
vincolo è sulle connessioni **uscenti** — con `allowTLS` il nodo accetta TLS ma non lo usa per
chiamare gli altri — e `preferTLS` è il primo modo in cui le uscenti sono cifrate. Nell'ordine
giusto la sequenza completa passa a caldo, con il nodo che resta `PRIMARY` e scrivibile.

**Il terzo è che non si torna indietro.** `Location5579202: Illegal state transition for
clusterAuthMode from 'x509' to 'sendX509'`, e lo stesso per `tlsMode` da `requireTLS` in giù. Chi
sbaglia tappa riavvia il nodo. Un dettaglio osservato e **non spiegato**, scritto nelle riserve
perché serve a chi scriverà uno script: reimpostare `clusterAuthMode` al valore che ha già viene
rifiutato — la migrazione non è idempotente.

**Tre tentativi per una misura.** Il primo giro ha ucciso il container prima di poter provare le
transizioni, perché `sendKeyFile` non parte senza TLS e questo non lo sapevo ancora. Il secondo è
finito contro `Unauthorized` su ogni `setParameter`: l'eccezione localhost non copre `setParameter`,
e questo è a sua volta una conferma misurata di [S-006](Sources.md#s-006) e del terzo punto di
[ADR-0026](Decision.md#adr-0026). Il terzo giro, con `rs.initiate()` e un utente prima di tutto, ha
prodotto la tabella. Il conto è due container buttati per una tabella di otto righe, e vale il
prezzo: le otto righe sono l'unica parte della sezione X.509 che non è una parafrasi.

**Il debito nominale di ADR-0026, saldato con un messaggio d'errore.** «La distinzione fra utenti del
cluster e utenti locali allo shard è materia da `03-amministrazione/sicurezza-keyfile-x509.md`»,
scritto ad agosto. Lo shard non c'è, quindi la domanda è stata riformulata per il replica set — e la
risposta è netta: `createUser` sul database `local` risponde `Cannot create users in the local
database` ([V-038](Sources.md#v-038)). L'unico database che non viene replicato è precisamente
l'unico in cui non si possono mettere utenti. Tre righe di prova al posto di un paragrafo prudente;
il caso sharded resta marcato e dovuto a `feature/03`.

**Una misura che il piano non chiedeva, e che serviva.** Nel comando dei tre membri `--auth` non
compare. Era già dichiarato da due fonti dal `feature/00` ([S-002](Sources.md#s-002),
[S-005](Sources.md#s-005)) e non era mai stato mostrato. Adesso c'è la tabella dei rifiuti, con
l'unica cosa che passa — `hello()` — e la ragione per cui passa.

**Il keyfile misura 1024 byte, e non si sa se è un caso.** Il massimo dichiarato per la lunghezza di
una chiave è 1024 caratteri; `openssl rand -base64 756` produce 1008 caratteri base64 più sedici a
capo, cioè esattamente 1024 byte sul disco. Quale dei due numeri MongoDB confronti con il limite non
è scritto da nessuna parte. La riserva è in [V-038](Sources.md#v-038) invece di una frase sicura in
una direzione o nell'altra.

**Controlli.** `make docs-check` verde al primo giro — l'ancora `<a id="adr-0048"></a>` era già al
suo posto, lezione del Task 10 applicata. `make tools-test`, `make stack-check` e
`./tools/smoke-replicaset.sh` rieseguiti a fine task. Le tre istanze usa-e-getta sono state rimosse
con `docker rm -f -v`; sullo stack del lab l'unica scrittura è stata la creazione e la rimozione di
`lettore-demo`, con i tre membri tornati a un utente solo.

**Documentazione prodotta.** [S-061](Sources.md#s-061), [S-062](Sources.md#s-062) e
[S-063](Sources.md#s-063) — le prime fonti su X.509 del repository; [V-038](Sources.md#v-038),
[V-039](Sources.md#v-039) e [V-040](Sources.md#v-040); [ADR-0048](Decision.md#adr-0048);
`docs/03-amministrazione/sicurezza-keyfile-x509.md`; tre citazioni da slide nel Blocco 2.
[S-005](Sources.md#s-005) acquisisce il quarto ADR che la cita, [S-002](Sources.md#s-002) e
[S-006](Sources.md#s-006) il terzo: sono le fonti di `feature/00` che questo branch ha finalmente
messo alla prova invece di limitarsi a citarle.

**Note di metodo.**

67. **Una riserva della fonte si riporta con il preventivo dell'alternativa accanto.** «Use keyfiles
    only for testing and development environments» si può citare in due modi. Da sola, spaventa e
    non insegna: chi legge conclude che il lab è fatto male. Con accanto il costo di X.509 in questo
    stack — una CA, un certificato per membro con il `SAN` di ogni host, una rotazione in sei passi e
    tre giri di riavvii — la stessa frase diventa una descrizione di economia, e la scelta del lab
    diventa difendibile invece che imbarazzante. La citazione è la stessa; cambia solo che cosa le
    sta vicino.

68. **Il debito si salda dove è scritto, marcando la parte che manca.** [ADR-0026](Decision.md#adr-0026)
    intesta a questa pagina, per nome, una distinzione che riguarda gli shard, e gli shard sono di
    un'altra feature. Le uscite comode erano due: rimandare tutto a `feature/03`, oppure scrivere per
    analogia fingendo di aver provato. La terza è riformulare la domanda per la topologia che c'è,
    misurarla, e marcare esplicitamente il resto. Costa una sezione più corta e un riquadro «non
    eseguito», e lascia il debito visibile invece che sciolto in una frase.

69. **Un esperimento che muore tre volte non è tre fallimenti: è la misura che si sta formando.** Il
    primo container è morto perché `sendKeyFile` vuole TLS — ed è diventato il fatto principale della
    sezione. Il secondo è morto contro `Unauthorized` — ed è diventato una conferma di
    [S-006](Sources.md#s-006). Solo il terzo ha prodotto la tabella. La tentazione, al secondo, era
    scrivere la sezione dalla documentazione e chiudere: sarebbe costato un'ora in meno e avrebbe
    perso due fatti su tre, entrambi arrivati proprio dai tentativi andati male.

---

## 2026-09-01 — `feature/02`, Task 12: quattro debiti si chiudono eseguendo, e due frasi erano sbagliate

Il Task 12 chiede quattro passi: gli `id` dell'elezione in `log.md`, l'esecuzione dei comandi di
amministrazione marcati «non eseguiti» nella guida a `mongosh`, le due trappole nuove, `docs-check`.
Tutti e quattro eseguiti. Il risultato principale non è nessuno dei quattro: è che **due
affermazioni in pagina erano false**, e si sono viste solo perché si è eseguito invece di smarcare.

**Il piano non è stato modificato; le deviazioni sono dichiarate qui.** Il Passo 2 ammetteva la
lettura minima — il replica set adesso c'è, i comandi «ovviamente funzionano», via la marcatura. È
stata scelta di nuovo la lettura massima: eseguirli tutti, uno per uno, e correggere dove l'output
smentisce il testo. Sono quattro ore in più e due errori in meno.

**La prima frase sbagliata era una contraddizione interna.** La §3.2 della guida avvertiva che «un
secondario non risponde alle letture finché non glielo si dice». Misurato su `mongo-rs-2`:
`readPreference` a `primary`, nessun `setReadPref`, e `countDocuments` restituisce 50 000. Quello
che il secondario rifiuta è la **scrittura**. Il punto grave non è l'errore: è che la **stessa
pagina** lo diceva già giusto in §1.5, dove [S-045](Sources.md#s-045) spiega che una stringa con un
solo host parla con quell'host «anche se è un secondario». Due frasi contraddittorie a quaranta
righe di distanza, entrambe plausibili se lette da sole, sopravvissute a ogni rilettura
([V-042](Sources.md#v-042)).

**La seconda era una deduzione ragionevole.** `docs/03-amministrazione/log.md`, §3.1, sosteneva che
«la manutenzione ordinaria produce lo stesso tracciato nel log di un incidente»: dedotta da
[S-044](Sources.md#s-044), che elenca `rs.stepDown()` fra le cause di elezione, e mai verificata.
Il Passo 1 chiedeva solo di incollare gli `id` sotto quella frase. Prima di incollarli si è
controllata la frase, ed è falsa: le tre cause hanno tre `id` diversi e tre testi diversi alla
**prima riga** — `4615652` per il guasto, `4615661` per la dimissione, `4615660` per il rientro per
priorità ([V-044](Sources.md#v-044)). Entrambe le frasi restano in pagina, cancellate in un
riquadro «Correzione» invece che rimosse: l'errore insegna accanto alla correzione.

**La soglia del keyfile non è dove chiunque la metterebbe.** Il messaggio «too open» era misurato
dal Task 2 ma non era mai entrato in [`Sources.md`](Sources.md) — «l'unico debito documentale
aperto dai due task chiusi», rimasto tale per dieci task. Chiudendolo si è chiesto anche *dove passa
la soglia*, con sei container usa-e-getta: `400` e `600` partono, `640` `644` `444` **e `401`** no.
`401` non concede lettura a nessuno, eppure viene rifiutato: la regola è «nessun bit acceso fuori
dal proprietario», non «non leggibile da tutti» ([V-041](Sources.md#v-041)). E la riga fatale del
log — quella con `"s":"F"` — non nomina né il file né i permessi: chi guarda solo l'ultima riga di
un container morto cerca nella direzione sbagliata.

**Il driver riceve i nomi di dentro.** Da fuori, con `?replicaSet=rs0`, la connessione fallisce con
`getaddrinfo ENOTFOUND mongo-rs-2` — un host che nella stringa non c'è, e che a ogni tentativo
cambia. Tre ripetizioni identiche hanno nominato `mongo-rs-1`, `mongo-rs-2`, `mongo-rs-1`
([V-043](Sources.md#v-043)). La voce 13 dice anche quale rimedio **non** funziona, che è quello che
viene in mente per primo: elencare tutti e tre gli indirizzi pubblicati. Una seed list con più di un
host è la terza delle quattro eccezioni che spengono `directConnection`, quindi più indirizzi buoni
si scrivono e più si convince il driver a buttarli via.

**Due misure che il piano non chiedeva.** `rs.stepDown()` cronometrato tre volte: primario nuovo
dopo **8, 101 e 87 ms**, contro i ~500 di uno `shutdown` e i ~10 000 di un `docker kill` — è il
terzo punto della scala che il Task 8 aveva lasciata a due. E `mongo-rs-1`, a priorità 2, si
riprende il posto da solo dopo ~11 s: la scena è autopulente e per questo fragile da spiegare con
calma. Terza, minore ma insidiosa: `rs.reconfig()` **riscrive** il numero di versione della
configurazione prima di spedirla, quindi non protegge dalle modifiche concorrenti; il comando
grezzo `replSetReconfig` sì, con `NewReplicaSetConfigurationIncompatible`.

**Quello che non è stato eseguito, e perché.** `rs.add()` e `rs.remove()` nella forma che riesce:
servirebbe un quarto container, e togliere un membro vivo romperebbe le prove successive. Provate
solo nella forma che fallisce, su un secondario, dove sono innocue; le due righe restano marcate
nella tabella. La terza via d'uscita della voce 13 — riconfigurare il set con nomi risolvibili da
fuori — è descritta e **non presa**: cambierebbe lo stack del talk in modo permanente. Tutta la
§3.3 sullo sharded cluster resta marcata, dovuta a `feature/03`.

**Il conto delle trappole: due fatte, quattro ancora candidate.** Qui i due documenti non dicono la
stessa cosa, e la differenza va lasciata visibile invece che risolta di nascosto. Il piano, Passo 3,
nomina **due** trappole — permessi del keyfile, scoperta della topologia — e cita
[ADR-0033](Decision.md#adr-0033), che per `feature/02` nomina esattamente quelle due. I punti di
ripresa del Task 9 e del Task 10, scritti *dopo* il piano, elencano invece **sei** debiti della
pagina: oltre al keyfile, `--env-file` che sostituisce e non aggiunge, `up --wait` che esce presto
([V-025](Sources.md#v-025)), il `$$` di Compose, il congelamento di `docker logs`
([V-032](Sources.md#v-032)) e l'`ENOTFOUND` che nel lab prende il posto di un errore di selezione
del server perché un container fermo sparisce dal DNS ([V-031](Sources.md#v-031)).

Le due liste hanno statuti diversi: quella del piano è un contratto e discende da un ADR, quella dei
punti di ripresa è un inventario di candidati cresciuto misura dopo misura. Il Task 12 ha eseguito
il contratto. **I quattro candidati restano aperti**, tutti già misurati e con la loro fonte —
scriverli è trascrizione, non ricerca. Sono materia da decidere: o una coda del Task 14, o
`feature/03`, che alla pagina deve comunque tornare. Il debito resta scritto qui perché una lista di
candidati che sparisce senza che nessuno decida è esattamente il modo in cui le pagine restano
incomplete.

**Un effetto collaterale sullo stack, da sapere.** Tre `rs.stepDown()` e quattro `rs.reconfig()`
hanno portato la versione della configurazione del replica set da **1 a 4**. Non è un guasto e non
sopravvive a un `make down-02 && make up-02`, che ricrea il set da zero; ma chi legge `rs.conf()`
sullo stack acceso trova un numero che il file Compose non spiega. `mongo-rs-1` è tornato primario
da solo, e nessuna delle riconfigurazioni ha cambiato membri, priorità o `settings`.

**Controlli.** `make docs-check` verde. `./tools/smoke-replicaset.sh` eseguito dopo la sequenza di
`stepDown` e `reconfig`: **42 superati, 0 errori**, con il primario al suo posto. `make tools-test` e
`make stack-check` rieseguiti a fine task.

**Documentazione prodotta.** [V-041](Sources.md#v-041), [V-042](Sources.md#v-042),
[V-043](Sources.md#v-043) e [V-044](Sources.md#v-044); [ADR-0049](Decision.md#adr-0049);
`docs/03-amministrazione/log.md` §3.3 riscritta con i tre tracciati e §3.4 nuova;
`docs/04-mongosh/guida-mongosh.md` §3.2 smarcata e corretta; le voci **12** e **13** di
`docs/02-architetture/trappole-mongodb-in-docker.md`; il rinvio di
`docs/03-amministrazione/sicurezza-keyfile-x509.md` puntato alla voce 12, che adesso mantiene quello
che prometteva; tre righe dell'indice di `docs/README.md`; tre citazioni da slide nel Blocco 2.
[S-045](Sources.md#s-045) acquisisce il terzo ADR che la cita, [V-029](Sources.md#v-029) e
[V-030](Sources.md#v-030) il terzo.

**Note di metodo.**

70. **Prima di riempire una sezione, si legge la frase che le sta sopra.** Il Passo 1 chiedeva di
    incollare gli `id` sotto una premessa già scritta. La premessa era falsa, e nessuno l'avrebbe mai
    più guardata: sarebbe diventata *più* credibile, perché sotto ci sarebbero stati dei numeri veri
    a farle da prova. Un dato misurato incollato sotto una deduzione sbagliata non la corregge, la
    certifica.

71. **Una guida può contraddirsi a quaranta righe di distanza, e la rilettura non lo trova mai.** Le
    due frasi su cosa risponde un secondario erano entrambe plausibili prese da sole, e chi rilegge
    legge una sezione alla volta. Non è una svista di attenzione: è che la coerenza fra parti distanti
    non è una proprietà che si vede leggendo. Si vede solo eseguendo, perché l'esecuzione non sa in
    quale sezione si trova.

72. **Il rimedio che non funziona vale la stessa riga di quello che funziona.** La voce 13 poteva
    fermarsi alle due strade buone. Ne dedica una terza a quella cattiva — elencare i tre indirizzi
    pubblicati — perché è la prima che viene in mente e perché fallisce *più* silenziosamente: dà lo
    stesso errore di prima, quindi chi la prova conclude di non aver capito il problema. Una pagina
    di trappole che elenca solo i rimedi validi lascia al lettore il tempo che voleva risparmiargli.

73. **Uno strumento che risponde sbagliato è peggio di uno che fallisce.**
    `docker logs --since "$(date -u …)"` non ha filtrato niente — l'orologio del container e quello
    dell'host non coincidono — e ha restituito cinquanta chilobyte di righe vecchie *senza errore*.
    Per un attimo sono sembrate il tracciato dell'elezione appena provocata. Il ripiego è
    `--tail N | grep | tail`, che conta righe invece di fidarsi di un orologio; la lezione è che
    quando un filtro restituisce troppo, la prima ipotesi non è «è successo molto», è «il filtro non
    ha filtrato».

---

## 2026-09-01 — `feature/02`, Task 13: la riserva si gira con quello che c'è, e l'avviso resta acceso

Il Task 13 chiede l'indice delle registrazioni, le registrazioni del failover nelle due varianti, la
verifica con `preflight` e il commit. I primi due passi sono fatti. Il terzo **non dà il risultato
che il piano si aspettava**, e non per un intoppo: perché il piano chiedeva una cosa che questa
macchina non può produrre.

**Il piano non è stato modificato; la deviazione è dichiarata qui.** Il Passo 3 scrive: «Atteso:
l'avviso sui filmati sparisce». Non sparisce. `make preflight` esce `0` con `Superati: 8 · Avvisi: 1
· Errori: 0`, e l'avviso è sempre lo stesso: `cartella dei filmati assente:
/Users/giulianolatini/SqlStart2026-registrazioni`.

**Il motivo è che «registrazione» in questo repository sono due cose diverse.** Un filmato `.mp4` è
lo schermo *e la voce* del relatore, sta sul canale YouTube con copia locale obbligatoria
([ADR-0016](Decision.md#adr-0016)), e lo può girare solo il relatore. Una registrazione di terminale
è il tracciato di ciò che il terminale ha fatto, con i tempi dentro, e si produce eseguendo. Il
piano le chiama entrambe «registrazioni» perché al momento della scrittura la distinzione non
serviva; al momento dell'esecuzione serve, perché una delle due si può fare adesso e l'altra no.
Ne è nato [ADR-0050](Decision.md#adr-0050).

**Quattro scene girate, tredici kilobyte in tutto** ([V-045](Sources.md#v-045)): lo smoke completo
(16,9 s, `Superati: 42 · Errori: 0`), `docker kill` sul primario (17,2 s, elezione in 8617 ms,
`exited` `RestartCount=0` `ExitCode=137`), la terminazione pulita (25,1 s, elezione in 1039 ms,
`running` `RestartCount=1` `ExitCode=0`), la maggioranza persa (15,6 s, `SECONDARY` dopo 8634 ms).
Fra una scena e l'altra `./tools/reset-demo.sh 02`, sempre, con i tre membri `healthy` e l'impronta
del dataset ricontrollata: registrare una scena su uno stack reduce dalla precedente significa
registrare un'altra scena.

**Lo strumento sta nel repository invece di essere installato.** `tools/registra-terminale.py`,
duecento righe di sola libreria standard, scrive e rilegge il formato asciinema v2. Il formato è di
`asciinema` — chi ce l'ha usa quello — ma non serve averlo, ed è il punto: una riserva che per
essere vista richiede un `brew install` con la rete della sala non è una riserva. Il comando gira
dentro uno pseudo-terminale e non in una pipe, perché in una pipe i programmi smettono di colorare e
la scena registrata non sarebbe quella che il pubblico vede. Il formato è JSON su righe: si legge
con `cat`, si confronta con `diff`, e sta in tredici kilobyte invece che nei megabyte contro cui
[S-021](Sources.md#s-021) mette in guardia.

**Nessun `.mp4` finto per far tacere l'avviso.** Sarebbe bastato un file vuoto con l'estensione
giusta. L'avviso verifica una cosa che manca davvero e dal 18 settembre 2026 diventa errore
bloccante: zittirlo adesso significa scoprire il buco la mattina del talk, che è esattamente lo
scenario per cui il controllo esiste. Il criterio 8 di completamento del branch resta quindi
**soddisfatto a metà**, dichiarato per iscritto in [ADR-0050](Decision.md#adr-0050) e nella pagina
delle registrazioni invece che nascosto dietro un controllo verde.

**Un numero fuori posto, e non è un errore di misura.** La terminazione pulita ha segnato 1039 ms,
contro i 574, 480 e 486 di [V-029](Sources.md#v-029) — il doppio del massimo, con lo *stesso*
strumento: `tools/failover-replicaset.sh` avvia l'osservatore prima del colpo, lo aspetta finché non
dice `PRONTO`, e interroga `hello()` ogni 20 ms. Non contraddice V-029: ne conferma la riserva
scritta a suo tempo, che quel mezzo secondo è tempo di rete e di voto e non un timeout di
configurazione, quindi balla con il carico della macchina. La scena era la terza di quattro girate
di seguito. V-029 non è stata toccata: il numero nuovo sta in V-045, dove si può leggere accanto
alle condizioni che lo hanno prodotto.

**Controlli.** `make docs-check` verde dopo che il collegamento nuovo di `docs/README.md` ha trovato
la pagina che indica. `make preflight`: uscita `0`, otto controlli superati, un avviso, zero errori.
`make tools-test`: **108 superati**, otto dei quali nuovi. Le quattro registrazioni riprodotte tutte
con `--riproduci` prima di essere committate: una riserva che non è stata riletta non è una riserva.
Due titoli sono stati corretti a mano nell'intestazione JSON — dicevano «esce da se» e «tre giu» —
senza rigirare le scene: il titolo è metadato, non è il tracciato, e si vede proiettato.

**Documentazione prodotta.** `tools/registra-terminale.py` con
`tools/tests/test_registra_terminale.py`, otto casi sulla riga di comando — il primo è la
regressione del `--titolo` inghiottito, l'ultimo verifica che un comando inesistente non lasci
dietro di sé una registrazione da zero byte; le quattro registrazioni in
`docs/05-talk/registrazioni/`; `docs/05-talk/registrazioni/README.md` con le due specie di riserva,
i quattro filmati ancora dovuti e la procedura per rigirare le scene;
[V-045](Sources.md#v-045); [ADR-0050](Decision.md#adr-0050); la riga di `docs/README.md` che adesso
è un collegamento e dice «già nel repository». [S-021](Sources.md#s-021) acquisisce il secondo ADR
che la cita, [V-029](Sources.md#v-029) il quarto.

**Note di metodo.**

74. **Un avviso che si può spegnere con un file finto non stava controllando niente.** La tentazione
    era di un minuto: `touch` di un `.mp4` vuoto nella cartella giusta, `preflight` verde, Passo 3
    chiuso come il piano lo descrive. Il controllo però non esiste per essere verde: esiste per
    ricordare al relatore, ogni volta che lancia `preflight`, che i filmati non ci sono ancora. Un
    controllo aggirato non diventa silenzioso, diventa **bugiardo**, e la bugia scade il giorno in
    cui serviva la verità. Quando un passo del piano non si può soddisfare, la cosa da produrre è la
    motivazione scritta, non il verde.

75. **`argparse.REMAINDER` inghiotte le opzioni del programma, non solo quelle del comando.** La
    prima registrazione è morta con `comando non trovato: --titolo`: dopo il primo argomento
    posizionale, `REMAINDER` raccoglie *tutto*, comprese le opzioni dichiarate poche righe sopra.
    Il rimedio è dividere `sys.argv` a mano sul `--` letterale prima di chiamare `parse_args`, e sta
    nel file con il commento che spiega perché non si usa la scorciatoia. Nota accessoria dello
    stesso errore: il programma ha poi provato a leggere il `.cast` che non aveva scritto ed è
    esploso con `FileNotFoundError`, seppellendo il messaggio utile sotto uno inutile. Chi fallisce
    a metà deve fermarsi lì, non proseguire fino a inciampare in un secondo modo.

76. **Un numero preso una volta sola non è una misura, nemmeno con lo strumento giusto.** I 1039 ms
    della terza scena sono il doppio del peggiore dei tre giri di V-029, con metodo, harness e stack
    identici: cambiava solo che la macchina aveva appena girato altre due scene. Se quel numero
    fosse finito in pagina come «il tempo della terminazione pulita», avrebbe dimezzato il rapporto
    fra le due scene — che è la cosa che il talk racconta — senza che nulla apparisse sbagliato. Le
    misure stanno in [`Sources.md`](Sources.md) con le mediane e le condizioni; una registrazione è
    una scena, e una scena porta un numero d'esempio, non una misura.

## 2026-09-01 — `feature/02`, Task 14: le due decisioni che mancavano, e un criterio che ha dovuto obbedire a se stesso

Il Task 14 è la chiusura del branch: i due ADR ancora dovuti, le fonti che li reggono, questa voce,
il consuntivo, i quattro controlli e la PR. In coda ci è finita anche una decisione del Product
Owner presa a Task 12 già scritto — i candidati a trappola rimasti aperti si chiudono qui, non in
`feature/03` — e per rispettarla il Task 14 ha dovuto misurare una cosa che non aveva misurato.

**La priorità 2/1/1 stava nel codice da undici commit, la ragione non stava scritta da nessuna
parte.** `10-rs-initiate.js` scrive `priority: 2` sul primo membro dal Task 3, il design lo prescrive
al §5.2, i tre container sono per tutto il resto identici — e nessun ADR diceva perché. È un debito
di specie diversa da quelli soliti: il codice era giusto, mancava il motivo, e un motivo che non è
scritto è un motivo che il prossimo che legge deve reinventare (e magari, trovandolo arbitrario,
togliere). [ADR-0051](Decision.md#adr-0051) lo scrive, e il motivo è di scena prima che tecnico: le
demo del talk **nominano un container**. `make failover-02` uccide il primario, la pagina del
replica set stampa porte e ruoli, lo smoke verifica chi scrive. Su un set simmetrico il primario lo
decide l'ordine con cui i nodi si vedono all'avvio, che cambia ogni volta: ogni comando andrebbe
preceduto da «vediamo prima chi è», venti secondi buttati per ciascuna delle tre scene davanti a un
pubblico che da quell'attesa non impara niente. [S-065](Sources.md#s-065) documenta il meccanismo con
le parole della fonte — la priorità «affect both the timing and the outcome of elections for
primary» — e dice anche perché le altre due restano a `1` e non a `0`: un membro a zero non si
candida mai, e il set perderebbe la capacità di sopravvivere alla caduta di `mongo-rs-1`, che è
esattamente la scena che il talk mostra.

**Scrivere le conseguenze ha costretto a dire ad alta voce una cosa che si sapeva e si taceva.** Con
la priorità asimmetrica, il nodo fermato **si riprende il ruolo quando torna**: non è un effetto
collaterale da subire ma una seconda elezione, già misurata undici secondi dopo uno
`rs.stepDown(10)` ([V-042](Sources.md#v-042)). La conseguenza pratica è doppia e va detta al
pubblico. Da un lato la scena del failover è **autopulente** — dopo un minuto lo stack è com'era, e
`reset-demo.sh 02` non deve rimettere a posto niente se non aspettare che le priorità si
riassestino ([V-031](Sources.md#v-031)). Dall'altro è fragile da commentare con calma: se chi parla
si dilunga, la dimostrazione si annulla mentre la si spiega, e quello che il pubblico vede è un
primario che «non è mai caduto». È il motivo per cui
[`tools/failover-replicaset.sh`](../tools/failover-replicaset.sh) cronometra invece di lasciar
guardare ([ADR-0044](Decision.md#adr-0044)), ed è il tipo di frase che si scopre di dover scrivere
solo quando si compila la sezione «conseguenze» di un ADR invece di dichiararla ovvia.

**I candidati a trappola si chiudono nel branch che li ha misurati.** Il Task 12 aveva lasciato
aperti quattro fenomeni raccolti nei punti di ripresa dei Task 9 e 10 e un quinto nominato nel
registro, e aveva scritto perché li lasciava aperti: la lista del piano è un contratto, quella dei
punti di ripresa è un inventario cresciuto misura dopo misura, e mescolarle di nascosto avrebbe
tolto la differenza. Il Product Owner ha deciso di chiuderli qui.
[ADR-0052](Decision.md#adr-0052) ne ricava il criterio generale — una trappola **già misurata** si
scrive nel branch che l'ha misurata, anche quando il piano di quel branch non la nominava, perché il
criterio è la misura e non il piano — e con esso la pagina passa da 13 a **18 voci**: `--env-file`
che sostituisce il `.env` invece di aggiungersi, `up --wait` che esce con successo mentre il replica
set non esiste ancora, il dollaro che Compose consuma, il congelamento di `docker logs`, e il terzo
`ENOTFOUND`. Quest'ultimo chiude anche un'incoerenza che nessuno strumento poteva vedere: la voce
13, scritta al Task 12, rimandava già «fra le tre che danno `ENOTFOUND`» quando le voci esistenti
erano due. Tre delle cinque nuove non parlano di MongoDB affatto — sono trappole di Compose e del
runtime — e la riga d'apertura della pagina adesso lo dichiara, perché stanno lì per il solo motivo
che le incontra chi monta uno stack MongoDB.

**Il criterio si è applicato per primo all'ADR che lo scriveva.** ADR-0052 dice «misurata, non
prevista», e mentre lo si scriveva è saltato fuori che una delle cinque — il `$` di Compose — quella
misura non ce l'aveva: veniva da una lettura, non da un'esecuzione. Le strade oneste erano due,
indebolire il criterio o misurare. È stata presa la seconda, e costa quattro minuti: un `compose.yaml`
di nove righe fuori dal repository, un solo servizio `alpine:3`, una variabile `DENTRO` dichiarata
due righe sopra e un `sh -c 'echo "singolo=[$DENTRO]  doppio=[$$DENTRO]"'`. Risposta:
`singolo=[]  doppio=[valore-del-container]`. Con la stessa variabile esportata nella shell che
lancia, il singolo dollaro stampa **il valore dell'host**, non quello del container. `docker compose
config` esce `0` e avvisa: `The "DENTRO" variable is not set. Defaulting to a blank string`. Lo
stack è stato smontato a misura presa; il verbale è [V-046](Sources.md#v-046). Un criterio scritto
in un ADR è la prima cosa che l'ADR stesso deve superare.

**La fonte non stava nella pagina in cui la si sarebbe cercata.** La regola del dollaro doveva
venire da [S-056](Sources.md#s-056), la pagina di Compose sull'interpolazione delle variabili, già
citata da due ADR e apparentemente l'indirizzo giusto. Riletta per estrarne la frase, non contiene
la regola: dell'`$$` non dice nulla e si limita a rimandare al riferimento del formato. La frase sta
lì, in `/reference/compose-file/interpolation/`, che diventa [S-064](Sources.md#s-064). La
discrepanza non è stata nascosta: è scritta come riserva dentro S-064, perché chiunque cerchi quella
regola partirà dalla stessa pagina sbagliata, e sapere in anticipo che non ce la troverà vale quanto
la regola.

**Le «Usata da» si chiedono al controllore, non si indovinano.** I due ADR nuovi citano dieci fonti
in tutto; tre nascono con il proprio rimando già scritto, sette esistevano già e andavano
aggiornate. Aggiornate a mano ne sono state prese due, e cinque sono rimaste indietro:
`check_citations.py` le ha elencate tutte e cinque in una passata sola, con nome e ADR mancante. La
correzione è poi meccanica — si percorrono le ancore e si riscrive la riga con l'insieme ordinato —
ma il punto è l'ordine delle operazioni: si scrive l'ADR con le sue fonti, si chiede allo strumento
quali rimandi mancano, si correggono. Indovinare costa un giro in più e ne dimentica sempre qualcuno.

**Quello che è stato verificato.** I quattro controlli sono stati eseguiti due volte, prima con gli
stack **fermi** e poi con lo stack 02 avviato, con lo stesso esito. `make preflight`: uscita `0`,
`Superati: 8 · Avvisi: 1 · Errori: 0` — l'avviso è quello dei filmati, che resta acceso per scelta
([ADR-0050](Decision.md#adr-0050)). `make docs-check`: citazioni coerenti e collegamenti coerenti.
`make stack-check`: `Stack conformi: 2`. `make tools-test`: **108 superati**. Verificato anche, con
un `grep`, che in [`docs/README.md`](README.md) non resti alcuna riga che prometta `feature/02` come
lavoro futuro.

**Documentazione prodotta.** [ADR-0051](Decision.md#adr-0051) e
[ADR-0052](Decision.md#adr-0052); [S-064](Sources.md#s-064), [S-065](Sources.md#s-065) e
[V-046](Sources.md#v-046); cinque voci nuove in
[`trappole-mongodb-in-docker.md`](02-architetture/trappole-mongodb-in-docker.md), che passa a 18 e
guadagna una tabella a tre righe per distinguere i tre `ENOTFOUND` del laboratorio; le «Usata da» di
sette fonti allineate; e due voci nuove in
[`citazioni-riportare-slide.md`](citazioni-riportare-slide.md) — la priorità che decide anche i
tempi dell'elezione, nel Blocco 2, e il dollaro mangiato da Compose, fra le trappole di Docker.

**Note di metodo.**

77. **Un criterio scritto dentro un ADR va applicato per primo a quell'ADR.** ADR-0052 pretende che
    una trappola sia misurata e non prevista, e delle cinque che ammetteva quattro lo erano. La
    quinta no. Se fosse passata, l'ADR sarebbe nato falso nel punto esatto in cui pretende rigore, e
    la falsità sarebbe stata invisibile perché nessuno rilegge le premesse di una decisione appena
    presa. La misura è costata quattro minuti; scoprirla fra sei mesi sarebbe costata la fiducia
    nella regola. **Il primo caso di prova di una regola nuova è il documento che la introduce.**

78. **Una pagina che parla di un argomento non è la fonte di ogni regola su quell'argomento.** La
    pagina di Compose sull'interpolazione delle variabili non dice come si scrive un dollaro
    letterale: lo dice il riferimento del formato. La citazione stava per andare su S-056 perché il
    titolo combaciava, e sarebbe stata una citazione **plausibile e sbagliata** — la specie peggiore,
    perché chi la verifica apre la pagina, la trova pertinente e non legge fino in fondo. Il rimedio
    non è cercare meglio: è rileggere la pagina con l'obiettivo di **estrarne la frase esatta**. Se
    la frase non si trova, la fonte non è quella. E la discrepanza si scrive come riserva, perché il
    prossimo partirà dalla stessa pagina.

79. **Un invariante bidirezionale si fa verificare, non si tiene a mente.** Aggiungere due ADR
    significa aggiornare la riga «Usata da» di ogni fonte che citano; a mano ne sono state prese due
    su sette. Non per distrazione: la metà che si scrive è quella dell'ADR, e la metà che si
    dimentica è sempre l'altra. `check_citations.py` le ha elencate in una passata, e la correzione
    è diventata meccanica. **Quando esiste uno strumento che conosce l'invariante, l'ordine giusto è
    scrivere, chiedere, correggere** — non scrivere, ricordare, sperare.

80. **Un rimando scritto in anticipo è un debito con la scadenza già dentro.** La voce 13 delle
    trappole, al Task 12, parlava «fra le tre che danno `ENOTFOUND`» mentre le voci in pagina erano
    due. Nessun controllo poteva accorgersene: non era un collegamento con un'ancora rotta, era una
    frase in prosa, e si legge bene ad alta voce. È rimasta falsa per un intero task. Quando si
    scrive una promessa che dipende da qualcosa che non c'è ancora, o la si scrive al presente
    perché la si sta scrivendo nello stesso commit, oppure si nomina il debito nel registro — che è
    l'unico posto dove qualcuno lo va a ricontrollare.

**Consuntivo del branch, alla vigilia dell'unione.** Ventidue commit e trentaquattro file rispetto
a `develop`: il piano, tredici di task, quattro punti di ripresa, una nota di metodo isolata, il
Task 14 che chiude il lavoro e **due** giri di review della PR #3. Il numero è calcolato
**includendo il commit che lo introduce**, come prescrive la nota 37 dopo che era stato sbagliato
due volte — e questa riga è stata riscritta quattro volte proprio per rispettarla: diceva
«diciotto» quando fu scritta, «diciannove» dopo il punto di ripresa di `feature/03`, «venti» dopo
quello di `feature/04`, «ventuno» dopo la prima review, e adesso conta anche la seconda. Il conto
dei file non si muove: le review hanno toccato sei pagine e tre strumenti, tutti già dentro. Il
trentaquattresimo file resta il `README.md` alla radice, che dichiarava ancora
`docker/02-replicaset` «in lavorazione». I quattro controlli sono verdi in locale, con gli stack
fermi e con lo stack 02 acceso; su GitHub non ne gira nessuno, per scelta
([ADR-0038](Decision.md#adr-0038)).

**Quello che resta aperto** non appartiene a questo branch e va scritto perché non si perda: i
quattro filmati `.mp4`, che solo il relatore può girare, e l'avviso di `preflight` che li reclama —
acceso oggi, bloccante dal 2026-09-18. Le registrazioni di terminale che fanno da riserva ci sono
già ([ADR-0050](Decision.md#adr-0050)), e non sostituiscono i filmati: sostituiscono la demo dal
vivo se lo stack non parte.

## 2026-09-01 — Punto di ripresa: `feature/03-stack-sharded`, che non è la prossima

Questa voce non nasce da una sessione interrotta. Nasce dal fatto che `feature/02` è chiusa e in
attesa di revisione, e che il branch che eredita lo sharded cluster **non comincia adesso**. Il
calendario del [design](00-progetto/2026-08-24-design.md) mette dopo la PR #3 la
`feature/04-app-python` — dal 4 all'11 settembre, PR #4 — e solo il 14 e 15 settembre la
`feature/03-stack-sharded`, con la PR #5: l'applicazione viene prima perché è il pezzo più grande e
meno comprimibile, e conviene averla in mano finché c'è margine. Fra oggi e il primo commit dello
sharded ci sono quindi due settimane e un branch intero. È esattamente quella distanza a rendere il
punto di ripresa utile: quello che oggi è ovvio, fra due settimane va ricostruito.

**Quello che è deciso e non va più discusso.**

- **La versione.** [ADR-0028](Decision.md#adr-0028): il lab gira su **MongoDB 7.0.40**, con la
  8.0.30 come traguardo. Non c'è niente da ridiscutere, ma c'è una cosa da **verificare** prima di
  montare il terzo stack: se i binari della 8.0.30 sono stati pubblicati. La decisione ha la
  scadenza scritta dentro — si ripinna appena escono e si rigirano i filmati — e costa poco perché
  la versione è una variabile sola, `${MONGO_IMAGE}` negli stack e `tools/images.env` rigenerato da
  `make images-pull`.
- **La topologia è validata.** Lo spike del 25 agosto ha montato lo sharded cluster completo e lo ha
  misurato: [`2026-08-25-spike-sharded.md`](00-progetto/2026-08-25-spike-sharded.md). Il file
  Compose che ha funzionato è **dentro il verbale** e non nel repository, e non è una dimenticanza:
  codice non eseguito che resta in giro invecchia senza che nessuno se ne accorga.
- **I due profili.** Il profilo di palco e quello completo si comportano come servono, e
  `keyfile-init` resta **senza profilo** perché la dipendenza vada da un servizio con profilo verso
  uno senza — l'unica direzione su cui la documentazione di Compose si sbilancia
  ([S-015](Sources.md#s-015)). La riserva di [ADR-0010](Decision.md#adr-0010) resta aggirata per
  costruzione, non per fortuna, e va riletta prima di toccare i profili.
- **La catena di inizializzazione.** [ADR-0026](Decision.md#adr-0026) fissa che
  `MONGO_INITDB_ROOT_*` non funziona su un config server; [ADR-0040](Decision.md#adr-0040) ha scelto
  per il replica set la strada del namespace di rete condiviso dopo aver montato e misurato tutte e
  tre le alternative ([V-023](Sources.md#v-023)). `feature/03` non deve rifare quel confronto: deve
  decidere se la stessa forma regge con `mongos` davanti, che è una domanda più piccola.
- **La pagina delle trappole cresce per aggiunta** ([ADR-0033](Decision.md#adr-0033)) e **una
  trappola già misurata si scrive nel branch che l'ha misurata**
  ([ADR-0052](Decision.md#adr-0052)). La conseguenza pratica è che `feature/03` non eredita una lista
  di candidati aperti — `feature/02` ha chiuso la propria — e non deve accumularne una.
- **Lo stack è un argomento, non un ramo dentro il codice.** `reset-demo.sh 03` deve funzionare
  aggiungendo un caso, non riscrivendo lo strumento; lo stesso vale per i bersagli del Makefile.
- **Ciò che non si esegue si marca** ([ADR-0035](Decision.md#adr-0035),
  [ADR-0036](Decision.md#adr-0036)). Vale anche quando la marcatura è scomoda, ed è la regola che ha
  prodotto i debiti elencati più sotto.

**Quello che è costruito e si eredita.** Due stack che partono — `docker/01-standalone` e
`docker/02-replicaset` — con i loro bersagli nel Makefile; gli strumenti di palco
(`smoke-replicaset.sh`, `failover-replicaset.sh`, `reset-demo.sh`, `registra-terminale.py`) e i tre
controllori (`check_stack.py`, `check_citations.py`, `check_links.py`) più `preflight`; 108 test in
`tools/tests/`. Alla chiusura di `feature/02` i quattro controlli sono verdi, eseguiti con gli stack
fermi e con lo stack 02 avviato.

**Quello che è già misurato e non va rimisurato.** Dallo spike, sette risposte che un piano scritto
da zero rimetterebbe in dubbio: `MONGO_INITDB_ROOT_*` su un config server (§2); `rs.initiate()`
scritto con i nomi dei servizi Compose e non con gli IP (§3); l'eccezione localhost che concede meno
di quanto sembri (§4, e [S-055](Sources.md#s-055)); la topologia che funziona, failover compreso
(§5); i due profili contati in servizi (§6); la cache WiredTiger nei container e il comportamento di
`compose up` sulla rete (§7). Da `feature/02`, cinque trappole che colpiscono chiunque monti uno
stack Compose e che nello sharded si incontrano prima, non dopo: `--env-file` che sostituisce
invece di aggiungersi, `up --wait` che esce mentre la topologia non c'è ancora, il dollaro che
Compose consuma, `docker logs` che si congela dopo un riavvio del demone, e il terzo `ENOTFOUND` —
voci [14](02-architetture/trappole-mongodb-in-docker.md#t-14)–[18](02-architetture/trappole-mongodb-in-docker.md#t-18)
della pagina delle trappole.

**Quello che è dovuto, e sta già scritto in pagina come debito.** Non è una lista da ricostruire: è
già marcata nei documenti, e ogni riga ha un indirizzo.

- `docs/02-architetture/sharded-cluster.md` — la pagina non esiste, e
  l'[indice della documentazione](README.md) la promette per nome a `feature/03-stack-sharded`.
- `README.md` alla radice dichiara `docker/03-sharded` «in lavorazione»: è la riga che va chiusa.
- [`guida-mongosh.md`](04-mongosh/guida-mongosh.md) — la §3.3, *Sharded cluster*, è marcata per
  intero come non eseguita.
- [`sicurezza-keyfile-x509.md`](03-amministrazione/sicurezza-keyfile-x509.md) — gli **utenti locali
  a uno shard**, che là esistono davvero perché ogni shard è un replica set con il proprio `admin`,
  e l'eccezione localhost che «applies to each shard individually as well as to the cluster as a
  whole» ([S-006](Sources.md#s-006)). Marcato, mai provato.
- [`backup-restore.md`](03-amministrazione/backup-restore.md) — `--oplog` che la documentazione
  vieta sullo sharded cluster ([S-011](Sources.md#s-011)); il seguito è dovuto lì.
- [`trappole-mongodb-in-docker.md`](02-architetture/trappole-mongodb-in-docker.md) — le trappole dei
  **config server** e del **bilanciamento**, che ADR-0033 intesta per nome a `feature/03`.

**Il prossimo passo.** La PR #3 va revisionata e unita su GitHub, e **non** chiusa con
`git flow feature finish`. Poi, per calendario, si apre `feature/04-app-python`. Quando toccherà
allo sharded: si verifica se la 8.0.30 esiste, si scrive il piano in `docs/00-progetto/` sul
modello del [piano di `feature/02`](00-progetto/2026-08-31-piano-feature-02-stack-replicaset.md), e
si parte dal verbale dello spike invece che dalla pagina bianca — c'è dentro un Compose che ha già
funzionato.

**Note di metodo.**

81. **Un punto di ripresa si scrive quando la distanza è prevedibile, non solo quando la sessione si
    rompe.** La nota 44 lo aveva legato all'interruzione: si sospende, e l'ultimo commit non è il
    codice ma il contesto. Ma il contesto si perde anche senza interruzioni, e in modo più insidioso:
    qui fra la chiusura di `feature/02` e l'apertura di `feature/03` ci sono due settimane e un
    branch intero, dedicato a tutt'altro. Al ritorno non si ricorderà che lo spike aveva già montato
    la topologia, né che il Compose che funzionava è dentro un verbale invece che nel repository — e
    la reazione naturale a un dubbio è **rifare la misura**, che costa un giorno. La regola: quando
    fra due pezzi di lavoro correlati si sa già che passerà altro lavoro in mezzo, il punto di
    ripresa si scrive alla fine del primo, finché è gratis.

## 2026-09-01 — Punto di ripresa: `feature/04-app-python`, che è la prossima davvero

Il branch dell'applicazione apre il 4 settembre e chiude l'11, con la PR #4: è il pezzo più lungo
del progetto e l'unico che non produce uno stack. Il design gli dedica un capitolo intero
([§6](00-progetto/2026-08-24-design.md) e §7), scritto il 24 agosto — **prima** che esistesse
qualunque stack. Da allora tre decisioni lo hanno corretto, e la prima cosa da sapere ripartendo è
quali parti di quel capitolo non valgono più.

**Quello che è deciso, e che il design non dice più com'era.**

- **Niente `testcontainers`.** La §7 del design prescrive `testcontainers-python` per i test di
  integrazione e dichiara come rischio numero uno che la libreria non regga i replica set, con la
  verifica intestata al «primo passo di `feature/04`». Quel passo **è già stato fatto**:
  [ADR-0020](Decision.md#adr-0020) sostituisce [ADR-0011](Decision.md#adr-0011) e decide che i test
  di integrazione avviano gli **stack Compose del repository** e ci girano contro. `MongoDbContainer`
  non conosce i replica set — il modulo non nomina mai `replSet` né `rs.initiate` — e `DockerCompose`
  esiste nel codice della libreria ma non nella documentazione pubblicata. Il rischio è chiuso e la
  dipendenza non va aggiunta.
- **Cade con lui il piano delle fixture.** Il design vuole «un Compose minimale **proprio**» in
  `app/tests/fixtures/`, comprato al prezzo di «una piccola duplicazione in cambio
  dell'indipendenza». ADR-0020 compra l'opposto: i test verificano l'artefatto che il pubblico
  eseguirà davvero, non un facsimile. In cambio l'integrazione è più lenta e vuole Docker, quindi
  **due suite separate con due bersagli `make` distinti** — la veloce resta veloce.
- **L'applicazione gira in un container sulla rete degli stack**
  ([ADR-0012](Decision.md#adr-0012)) e si collega usando i nomi dei servizi.
  `directConnection=true` solo nella demo dello standalone, dove non c'è nulla da scoprire.
- **Il nucleo non conosce Rich** ([ADR-0007](Decision.md#adr-0007)): emette eventi verso un
  `EventSink`, e la frequenza di aggiornamento si dichiara invece di lasciarla al valore
  predefinito.
- **Python e `pymongo`, con i listener di monitoraggio registrati per client**
  ([ADR-0006](Decision.md#adr-0006)). Runtime `python:3.13-slim` e non l'interprete dell'host, che è
  3.14.7; dipendenze con `uv`, che è già lo strumento di `tools/`.

**Quello che è già misurato e non va rimisurato.** Una sola misura, e pesa: i callback di `pymongo`
sono **sincroni**, e il thread dell'applicazione resta fermo finché l'handler non ritorna —
«Application threads block waiting for event handlers to return» ([S-010](Sources.md#s-010)). È il
motivo per cui `SdamBridge` non deve disegnare niente dentro il listener ma solo depositare un
evento in coda: un handler lento non rallenta la grafica, rallenta il driver, e **falsa proprio le
misure di failover che la demo sta cronometrando**. Vale anche il contorno già costruito: due stack
che partono, gli strumenti di palco, i tre controllori, 108 test in `tools/tests/` come modello di
come si prova uno script in questo repository.

**Quello che è dovuto, e sta già scritto in pagina come debito.** Tre pagine promesse
dall'[indice](README.md) e tre misure rimandate per nome.

- `docs/06-sviluppo/architettura-app.md` e `docs/06-sviluppo/tdd-e-doppi.md` — la cartella
  `06-sviluppo/` non esiste ancora.
- `docs/03-amministrazione/statistiche-monitoraggio.md` — `serverStatus`, `dbStats`, metriche di
  replica, che cosa guardare sotto carico.
- **`j: true`**, che [ADR-0032](Decision.md#adr-0032) chiama «un debito onesto»: la misura di
  [V-016](Sources.md#v-016) non l'ha provato, e dovrebbe azzerare la perdita al prezzo della
  velocità.
- **`retryWrites=false` e `maxStalenessSeconds`**, e qualunque confronto di prestazioni: hanno senso
  solo sotto carico controllato. Le pagine [`standalone.md`](02-architetture/standalone.md) e
  [`replica-set.md`](02-architetture/replica-set.md) lo scrivono entrambe con la stessa formula —
  prima di allora «sarebbe aria».
- Gli strumenti che stanno nell'immagine ma non sono `mongosh`, e il backup a caldo dal lato
  applicativo ([`guida-mongosh.md`](04-mongosh/guida-mongosh.md)).

C'è un avvertimento da leggere prima di rimandare qualcosa di questa lista, e sta nelle alternative
scartate di [ADR-0046](Decision.md#adr-0046): «una decisione rimandata due volte è una decisione che
non si prende». Il rimando di ADR-0032 è già stato spostato una volta. `feature/04` è il posto dove
si salda, e non ce n'è un altro dopo.

**Una cosa da decidere presto, perché tocca le registrazioni.** Il design (§6.4) prevede che gli
scenari girino anche **senza** `--step`, e dice che è così che si producono le registrazioni di
riserva, «che per costruzione mostrano esattamente ciò che si farà dal vivo». Nel frattempo
[ADR-0050](Decision.md#adr-0050) ha deciso un'altra cosa: le riserve sono registrazioni di terminale
in formato testo, prodotte da `tools/registra-terminale.py`, e quattro esistono già. Le due strade
non si escludono — ma se `mongolab` sa girare da solo, le sue scene vanno registrate con lo
strumento che c'è, non con un secondo meccanismo. Va deciso quando l'interfaccia a riga di comando
prende forma, non alla fine.

**Il prossimo passo.** Unita la PR #3, si apre `feature/04-app-python` da `develop` e si scrive il
piano in `docs/00-progetto/` sul modello degli altri tre. Il primo task **non** è più la verifica di
`testcontainers`, che ADR-0020 ha già chiuso: è la stratificazione di
[§6.1](00-progetto/2026-08-24-design.md) con le porte come `typing.Protocol`, perché è la parte da
cui dipende tutto il resto e l'unica che non si può aggiustare dopo.

**Note di metodo.**

82. **Il design invecchia, e il primo compito di un punto di ripresa è dire quali sue parti sono
    morte.** Il capitolo sull'applicazione è del 24 agosto, scritto prima che esistesse un solo
    stack. Da allora [ADR-0020](Decision.md#adr-0020) ha rovesciato la strategia dei test di
    integrazione e con essa il piano delle fixture, e il «primo passo di `feature/04`» che il design
    prescrive — verificare `testcontainers` — è un lavoro già fatto e già deciso. Chi aprisse il
    branch leggendo il design come se fosse aggiornato aggiungerebbe una dipendenza scartata e
    spenderebbe il primo giorno su un rischio chiuso. Il design **non si riscrive**, per la stessa
    ragione per cui non si riscrivono gli ADR: è un documento datato e va letto per quello che era.
    Ma allora qualcuno deve tenere il conto di che cosa lo ha superato, e il punto di ripresa è il
    posto naturale perché è l'ultima cosa che si legge prima di ricominciare.

## 2026-09-01 — Review della PR #3: cinque rilievi, quattro veri, e uno che si smonta in dieci secondi

La PR #3 è aperta e il Product Owner l'ha revisionata. Ha poi chiesto una *review lite* a GitHub
Copilot, che ha lasciato **cinque commenti in linea**, e ha dato l'istruzione che vale per tutte le
review esterne: verificarli **eseguendo**, correggere quelli veri chiudendoli con una spiegazione,
chiudere gli altri dicendo perché non reggono. Nessuno è stato accettato o respinto leggendolo.

| # | Dove | Che cosa sosteneva | Verdetto |
|---|---|---|---|
| 1 | `tools/failover-replicaset.sh:190`, `:354` | `mktemp` senza argomenti fallisce su macOS/BSD con «too few X's in template» | **falso** |
| 2 | `tools/registra-terminale.py:95` | `os.execvpe` non protetta nel figlio: in caso di errore un traceback e un codice di uscita non controllato | **vero, e più largo** |
| 3 | `tools/registra-terminale.py:152` | `riproduci()` divide per `velocita` senza validarla: `--velocita 0` solleva `ZeroDivisionError` | **vero** |
| 4 | `tools/registra-terminale.py:190` | `--riproduci` viene cercato in tutta la riga, anche dopo `--` | **vero** |
| 5 | `tools/smoke-replicaset.sh:97`, `:99` | il commento promette che la password passa per `-e`, ma `mongosh` la riceve con `--password` | **vero, e nella direzione opposta** |

**Il primo si smonta eseguendolo.** `mktemp` su questa macchina restituisce
`/var/folders/gx/…/tmp.Mgs1q6sDpe` e esce `0`. Il manuale di macOS lo scrive: «If no arguments are
passed or if only the `-d` flag is passed mktemp behaves as if `-t tmp` was supplied». Il rilievo
descrive il comportamento di `mktemp` con un *template* privo di `X`, che è un'altra invocazione.
C'è anche una prova indiretta che non richiede il manuale: `failover-replicaset.sh` è lo strumento
che ha prodotto [V-042](Sources.md#v-042) e le altre misure di failover del branch — se `mktemp`
non avesse funzionato, quelle misure non esisterebbero.

**Il secondo era più grande di come è stato descritto.** Il rilievo parlava del codice di uscita;
la misura ([V-048](Sources.md#v-048)) ha mostrato che il traceback finisce **dentro il `.cast`**,
con i percorsi assoluti della macchina di chi registra, e che il file resta su disco sembrando una
registrazione buona. Il controllo preventivo che c'era guardava se il file *esiste*, non se si
*esegue*. Correzione in [ADR-0053](Decision.md#adr-0053): 127 e 126 come li usa la shell, e
`execvpe` racchiusa in un `try` che scrive una riga con `os.write` — non `print`, che dopo `fork`
ha un buffering su cui non si conta.

**Il terzo e il quarto sono piccoli e reali.** `--velocita 0` produceva un `ZeroDivisionError`
nella riproduzione, cioè un traceback al posto della riserva nel momento in cui la riserva serve.
Il quarto è l'immagine speculare della regressione che ha dato origine a questo strumento: là erano
le opzioni del programma a colare nel comando da registrare, qui era un'opzione del comando a
essere letta come propria — e `argparse` rispondeva «unrecognized arguments», incolpando chi
digitava. La divisione su `--` adesso vale nei due versi.

**Il quinto aveva ragione sul fatto e torto sul perché — e per un momento gli ho dato torto
anch'io nel modo sbagliato.** Il commento prometteva che la password non finisse sulla riga di
comando di `mongosh`; il codice ce la metteva. Fin qui il rilievo è esatto. La prima riscrittura
del commento diceva «dentro il container resta comunque leggibile in `ps`»: sembrava l'unica cosa
che potesse essere vera, e non è stata misurata. Poi è stata misurata ([V-047](Sources.md#v-047)),
ed è **falsa**: `mongosh` 2.10.0 riscrive il proprio `argv` e nella tabella dei processi del
container si legge `mongodb://<credentials>@…`, zero occorrenze della password. Dove si legge in
chiaro è **sull'host**, nella riga del client `docker`. E il `-e SEGRETO=` che il commento
presentava come cautela non era solo codice morto: ne metteva una **seconda** copia proprio su
quella riga. Correzione e criterio in [ADR-0054](Decision.md#adr-0054).

**Che cosa è cambiato in pagina e in codice.** Due misure nuove — [V-047](Sources.md#v-047) e
[V-048](Sources.md#v-048) — due ADR che le citano, una citazione da slide in coda al Blocco 2, e
cinque casi nuovi in `tools/tests/test_registra_terminale.py`, che passa da 8 a 13. Uno dei cinque
passava già prima della correzione: sta lì per impedire che la riscrittura degradasse in un
silenzioso «ignoro quello che hai scritto».

**Controlli.** `make tools-test` verde, 13 su 13 sul file toccato; `make docs-check` verde dopo che
i due ADR hanno ricevuto l'ancora esplicita e il separatore che gli altri hanno — `check_links.py`
li ha segnalati subito, che è il motivo per cui esiste; `bash -n` sullo smoke; e lo smoke eseguito
davvero contro lo stack avviato, **42 controlli superati, 0 errori**, perché togliere un argomento
a `compose exec` è una modifica al codice e non al commento.

**Note di metodo.**

83. **Un revisore automatico sbaglia in un modo che conviene conoscere: inventa dettagli
    verificabili in dieci secondi e vede difetti veri dove nessuno rilegge.** I cinque rilievi
    stanno tutti e due gli estremi. Quello su `mktemp` è una regola vera applicata a
    un'invocazione che nel codice non c'è: costa una riga di terminale smentirlo. Quello su
    `os.execvpe` sta dentro un blocco `fork`/`exec` che si scrive una volta e non si rilegge mai
    più, ed era vero e più grave del rilievo. L'asimmetria suggerisce la regola operativa: siccome
    il costo di verificare è quasi nullo e il costo di ignorare è un difetto che vive nella riserva
    del talk, **si verificano tutti**, compresi quelli che sembrano sbagliati a prima vista — e
    soprattutto quelli, perché è lì che si è tentati di rispondere a memoria.
84. **Quando un rilievo dice che un commento è falso, la correzione va misurata quanto il codice.**
    Qui il commento sbagliato è stato sostituito per un istante da un secondo commento sbagliato,
    scritto con la stessa fiducia: «in `ps` si vede lo stesso» è la frase che l'intuito produce, ed
    è falsa nel container e vera sull'host, cioè sbagliata due volte. Un commento non ha test che
    lo tengano onesto: l'unica cosa che lo tiene onesto è misurare la frase prima di scriverla.
    Vale il criterio inverso di [ADR-0024](Decision.md#adr-0024) — la pagina promette il sintomo
    come si è visto, non come dovrebbe presentarsi.
85. **Una review su cinque righe può costare due ADR, e non è sproporzione.** Il diff delle
    correzioni è di poche decine di righe; la documentazione che ne è uscita è più lunga del
    codice. Non è zelo: le due misure rispondono a domande che sarebbero tornate — «dove si vede
    davvero una password passata a un container» e «che cosa fa un `exec` che fallisce dentro un
    registratore» — e senza scriverle si sarebbe rifatta la stessa indagine al primo dubbio. La
    proporzione giusta di un repository didattico non è fra righe di codice e righe di prosa: è fra
    quello che si è imparato e quello che resta scritto.

## 2026-09-01 — Seconda review della PR #3: un rilievo solo, e la macchina di sviluppo lo nascondeva

Chiusa la prima review, il Product Owner ne ha chiesta una seconda a un revisore diverso — la
`codex` CLI, `codex review --base develop`, cioè esattamente il diff della PR. Ha prodotto **un solo
rilievo**, sullo stesso file dei tre precedenti e in un punto che nessuno dei tre aveva guardato: il
ciclo di cattura di `registra-terminale.py` ha due uscite, e la seconda perdeva lo stato del
processo.

**Che cosa perdeva.** Quando il comando registrato finisce **senza** chiudere lo pseudo-terminale —
succede se lascia dietro di sé un discendente — il ramo non bloccante
`os.waitpid(pid, os.WNOHANG)` si accorgeva che era finito e buttava via lo stato in un `_`. Ma il
processo a quel punto era già raccolto: la `waitpid` finale sollevava `ChildProcessError`, il
ripiego `stato = 0` entrava in funzione, e lo strumento riportava **successo**. Contraddice per
intero la promessa scritta nel proprio docstring, e il test che quella promessa la verifica
esisteva già dal Task 13 senza accorgersi di niente — perché prova un comando che esce `3` e
chiude il pty, cioè l'altra strada.

**La parte che vale più del rilievo.** Il revisore proponeva un caso di prova e non era riuscito a
eseguirlo: la sua sandbox glielo ha impedito. Provandolo qui, **non si riproduce**. Tre costruzioni
diverse — un `sleep` in background, un sottoshell immune a SIGHUP, un figlio che fa `setsid()` —
riportano tutte `7` correttamente, in meno di un decimo di secondo. Con tre esecuzioni verdi in
mano, la conclusione naturale era archiviarlo come falso positivo.

È BSD. Su macOS, quando muore il processo di controllo il kernel **revoca** il terminale di
controllo, e il pty si chiude anche se un discendente ne tiene ancora un descrittore: il ramo
difettoso non si raggiunge. Dentro un container `alpine:3` lo stesso identico comando riporta **0**
invece di `7`, e ci mette 0,25 secondi — il timeout di `select` più il giro non bloccante, cioè la
firma di quel ramo. Misura in [V-049](Sources.md#v-049), correzione e criterio in
[ADR-0055](Decision.md#adr-0055).

**Controlli.** `make tools-test` verde, e la suite del file eseguita **due volte**: 14 su 14 su
macOS e 14 su 14 dentro il container Linux. `make docs-check` verde.

**Note di metodo.**

86. **Un rilievo che non si riproduce sulla macchina di sviluppo non è ancora smentito.** La nota 83
    diceva di verificare eseguendo, e nel primo giro è bastata: `mktemp` si smonta con una riga di
    terminale. Qui la stessa regola, applicata con la stessa diligenza, avrebbe prodotto la
    conclusione opposta a quella giusta — tre prove, tutte eseguite davvero, tutte verdi, tutte
    sulla piattaforma sbagliata. La regola completa è: si esegue, e **quando l'esito può dipendere
    dal sistema operativo si esegue due volte**. Costa un `docker run` e dieci righe. Il laboratorio
    lo eseguirà gente su Linux e su WSL2 almeno quanto su macOS, e un difetto invisibile qui è
    visibile a loro — è l'unico tipo di difetto che chi scrive non può trovare rileggendo.
87. **Due revisori diversi trovano cose diverse nello stesso file, e il secondo non è ridondante.**
    Il primo giro ha trovato tre difetti in `registra-terminale.py` e non ha guardato il ciclo di
    cattura; il secondo ha guardato solo quello. Il costo di chiedere la seconda opinione è stato
    un comando; il difetto che ha trovato era il più grave dei quattro, perché è **silenzioso** —
    gli altri tre urlano un traceback, questo riporta successo. Vale la pena notare anche il
    contrario, per non trarne la lezione sbagliata: il secondo revisore non ha ritrovato nessuno
    dei tre difetti del primo giro, che a quel punto erano già corretti, e non ha prodotto rumore.
    Un rilievo, vero.

## 2026-09-01 — `feature/03`, apertura: un worktree si rimuove guardandoci dentro

`feature/02` è unita, la PR #3 è chiusa, il ramo è cancellato di qua e di là. Restava una cosa
sola, ed è quella che ha prodotto questa voce: il worktree che aveva ospitato il branch andava
rimosso, e la domanda «posso rimuoverlo?» si è rivelata più larga di come era stata posta.

**La domanda facile.** Nessuna modifica in sospeso, e la punta del ramo già dentro `develop`:
`git status --porcelain` vuoto, `git merge-base --is-ancestor HEAD origin/develop` vero. Due
comandi, risposta chiara, e a quel punto sembrava finita.

**La domanda vera.** Non è che cosa git conta, è che cosa git ha ricevuto istruzione di **non**
guardare. In questo repository quella categoria non è fatta solo di cache: `docker/02-replicaset/.env`
è ignorato per decisione ([ADR-0014](Decision.md#adr-0014)) perché contiene la password
dell'amministratore del lab. Il prezzo di quella scelta — mai scritto fino a oggi — è che il file
esiste in una copia sola, dove è stato creato.

**Due misure, e nessuna delle due è quella che si dava per scontata** ([V-050](Sources.md#v-050)).
`git worktree remove` si rifiuta di cancellare un worktree con dentro un file non tracciato, e lo
dice: `fatal: … contains modified or untracked files, use --force`. Con dentro un file **ignorato**
non dice niente: uscita `0`, directory sparita. La rete di sicurezza esiste e copre la categoria
sbagliata. Poi: il controllo non si può fare da fuori. Messi fianco a fianco un worktree annidato e
una directory normale, e chiesto a git di scendere con `-uall` — l'opzione che serve proprio a
quello — la risposta è `?? dirnormale/dentro.txt` per la seconda e `?? w3/` per il primo. Non è la
regola di ignore a fermarlo: è il **confine di repository**. Una directory che contiene un `.git`
git non la attraversa.

Il primo tentativo di controllo era stato fatto dal checkout principale e aveva restituito una riga
sola, `!! .claude/worktrees/feature+00-fondamenta/`, presa per un elenco completo. Era la soglia,
non il contenuto. Rifatto dall'interno, l'elenco aveva quattro voci, e una era il `.env`. Il
confronto con l'elenco del checkout principale ha aggiunto il pezzo che mancava: là il `.env` non
c'era. Non era una copia, era **la** copia.

Da qui [ADR-0056](Decision.md#adr-0056): l'elenco degli ignorati si fa dall'interno prima di ogni
rimozione, e la sede dei `.env` del laboratorio è il checkout principale, non un worktree.

**Perché sta in `feature/03` e non in `feature/02`.** Perché `feature/02` era già unita quando la
misura è stata presa. La regola del repository è che una trappola misurata si scrive nel branch che
l'ha misurata ([ADR-0052](Decision.md#adr-0052)); qui il branch che l'ha misurata non esisteva più,
e il primo aperto dopo è questo. Il consuntivo di `feature/02` resta quello che era: ventidue
commit, e non si riscrive per ospitare un fatto successivo.

**Note di metodo.**

88. **La rete di sicurezza di uno strumento definisce un confine, e va conosciuto invece che
    sperato.** `git worktree remove` protegge i file non tracciati. È un comportamento buono, ed è
    proprio la sua bontà a rendere il resto pericoloso: chi lo ha visto rifiutarsi una volta ne
    ricava che lo strumento «controlla prima di cancellare», e smette di controllare lui. Ma la
    protezione ha un bordo preciso — finisce dove comincia `.gitignore` — e il bordo non è
    annunciato: dall'altra parte non c'è un avviso più debole, c'è il silenzio. La regola generale:
    quando uno strumento ti ha protetto una volta, chiediti **da che cosa**, perché la risposta è
    quasi sempre più stretta di «dagli errori». Qui la distanza fra le due letture era la password
    dell'amministratore del lab.
89. **Il controllo va eseguito dal punto di vista di chi subisce l'operazione, non di chi la
    ordina.** Un worktree lo si rimuove standogli fuori, quindi è da fuori che viene naturale
    ispezionarlo — ed è l'unico posto da cui l'ispezione non funziona, perché git non attraversa il
    confine di un altro repository. Il guaio non è che dia una risposta parziale: è che ne dà una
    **ben formata**, una riga con la sintassi giusta, che sembra un elenco completo di un elemento.
    Un errore che si presenta come un risultato valido non lo si scopre rileggendo l'output; lo si
    scopre solo cambiando posto e rifacendo la domanda. Vale oltre git: ogni volta che si verifica
    qualcosa «da sopra», conviene chiedersi se da lì si veda davvero.

## 2026-09-01 — `feature/03`, avvio: due giorni restituiti, e un traguardo che non è arrivato

Il branch è aperto e ha due decisioni da scrivere prima di toccare un file Compose: perché comincia
adesso, e su quale versione.

**Perché adesso.** Il calendario del design mette `feature/04-app-python` prima dello sharded, e lo
motiva: l'applicazione è il pezzo più grande e meno comprimibile. Ma `feature/02` è stata unita il
1º settembre invece che il 3, e il calendario non dice che cosa fare di due giorni guadagnati — dice
un ordine, non come spendere l'anticipo. Il Product Owner ha deciso di spenderli qui, e le ragioni
reggono: allo sharded ne sono assegnati due, quindi è l'unico branch che ci entra per intero, ed è
quello che parte più avanti di tutti perché lo spike del 25 agosto ha già montato la topologia.
[ADR-0057](Decision.md#adr-0057) mette la decisione per iscritto **con la sua clausola**:
`feature/04` non si muove dal 4 settembre, e se il 3 lo sharded non è chiuso si sospende invece di
sforare. Un branch aperto «perché c'è tempo» è il modo classico di trasformare margine in debito, e
la difesa è una data, non una buona intenzione.

**Su quale versione.** Il punto di ripresa metteva come primo passo la verifica della 8.0.30, e
c'era una ragione pratica: montare il terzo stack su una versione e ripinnarlo il giorno dopo
significa rigirare le registrazioni. La risposta è no ([V-051](Sources.md#v-051)). Su Docker Hub il
filtro per nome esatto dà zero risultati e l'ultima 8.0 resta la 8.0.29; il feed ufficiale dei
download elenca 8.3.8, 8.2.12, 8.0.29, 7.0.40, 6.0.29, 5.0.34, 4.4.31. Ventisette giorni dopo la
scoperta del muro, la patch non è uscita — e non è un repository fermo: i tag mobili dell'immagine
ufficiale risultano aggiornati il 31 agosto, il giorno prima. Si resta su 7.0.40, che nel frattempo
è ancora la punta della sua linea, e [ADR-0058](Decision.md#adr-0058) trasforma la clausola
«appena escono» in due date: il 3 settembre e il 16, giorno della release.

**Una trappola schivata, che vale più della risposta.** La prima interrogazione chiedeva i tag con
`name=8.0` e leggeva l'elenco, che finiva su `8.0.29`. Sembrava la conferma. Non lo era: la
risposta è paginata a cento risultati su quattrocentotrentacinque, e l'ultimo della pagina era
`8.0.29-windowsservercore-ltsc2025` — in ordine lessicografico la `8.0.30` sarebbe stata la prima
della pagina dopo. Una risposta corretta a una domanda mal posta, con la forma esatta della
risposta giusta.

**Note di metodo.**

90. **Una clausola condizionale senza una data non ha un esecutore.** ADR-0028 diceva «si ripinna
    appena i binari escono», ed era una buona decisione con un buco: «appena» presuppone che
    qualcuno stia guardando, e nessuno era incaricato di farlo. In ventisette giorni la verifica
    non è stata fatta una volta — non per negligenza, ma perché non era il compito di nessun
    giorno. Ha funzionato solo perché un punto di ripresa l'ha nominata come primo passo di un
    branch, cioè perché per caso qualcosa l'ha agganciata a un momento. La regola: quando una
    decisione dipende da un evento esterno, si scrive **quando si guarda**, non solo che cosa si
    fa se è successo. Due date e un comando di un minuto costano meno di una decisione che aspetta
    da sola.
91. **Una risposta impaginata può avere la forma esatta della risposta che cerchi.** L'elenco dei
    tag finiva su `8.0.29` perché la pagina finiva lì, non perché la 8.0.30 non ci fosse — e
    l'elenco era corretto, completo per quel che prometteva, e leggibile come una conferma. È la
    categoria di errore della nota 89: non un risultato sbagliato, ma un risultato **ben formato**
    che risponde a una domanda diversa da quella posta. Con i servizi remoti ha una difesa
    specifica: non leggere elenchi per cercare un elemento, ma **chiederlo per nome** e guardare il
    conteggio. Un `count: 0` non dipende da dove cade il taglio della pagina.

---

## 2026-09-01 — `feature/03`, Task 1: lo scheletro, e un file di prova che portava due decisioni

Il piano del branch è scritto ([`2026-09-01-piano-feature-03-stack-sharded.md`](00-progetto/2026-09-01-piano-feature-03-stack-sharded.md)),
undici task, e la sua premessa è che questo branch non comincia dalla pagina bianca: lo spike del
25 agosto ha già montato la topologia, misurato la distribuzione dei documenti e provato il
failover di uno shard. Scrivendolo sono uscite quattro cose che il piano diceva male e sono state
corrette prima del commit — fra queste, la più utile: il `--configdb` di `mongos` elenca tutti e
tre i config server anche nel profilo `palco`, dove due non esistono, perché `mongos` li tratta da
semi e ignora gli irraggiungibili. Il piano ordinava di parametrizzarlo per profilo. Lo spike lo
aveva già misurato, e la misura toglie un ramo invece di aggiungerlo.

**Il Task 1 è fatto e verificato** ([V-052](Sources.md#v-052)): `keyfile-init` senza profilo, il
replica set dei config server, `.env.example`. I profili selezionano 2, 4 e 1 servizio come
previsto; `up --wait` con il profilo `palco` esce 0 dopo `keyfile-init` `Exited` → `cfg1`
`Healthy`; il keyfile risulta `-r-------- 1 999 999 1024`; `check_stack.py` lo trova già conforme
senza regole nuove.

**La misura che conta.** Su un config server avviato con `--replSet` e mai inizializzato,
`db.hello()` risponde `isWritablePrimary: false`, `secondary: false`, `isreplicaset: true`. I primi
due termini sono falsi. L'healthcheck che il design §5.4 suggerisce — la disgiunzione dei primi due
— resterebbe rosso per sempre, e la catena non arriverebbe mai a `rs.initiate()`. È lo stesso
risultato dello stack 02, ma su un ruolo diverso, con una porta predefinita diversa: valeva
rimisurarlo invece di ereditarlo.

**La decisione del task.** Il file dello spike usa gli ancoraggi YAML e risparmia duecento righe su
undici servizi. Gli altri due stack non li usano. [ADR-0059](Decision.md#adr-0059) sceglie il per
esteso anche qui, e non per coerenza: lo stack 03 esiste per mostrare che tre ruoli sono distinti —
`--configsvr`, `--shardsvr`, un `mongos` che non è un `mongod` — e un file in cui tutti ereditano
dallo stesso ancoraggio mette in evidenza ciò che hanno in comune e nasconde in una riga di
override ciò che li distingue, cioè il contenuto del Blocco 3. Il prezzo è dichiarato: circa
novecento righe a stack completo, e una manutenzione peggiore che tocca a `check_stack.py`
sorvegliare.

**Note di metodo.**

92. **Un file che ha già funzionato porta dentro più decisioni di quante se ne stiano copiando.**
    Il Compose dello spike si sarebbe potuto riportare così com'era: era la cosa ragionevole da
    fare, ed è quello che il verbale suggerisce. Ma dentro c'erano due scelte, non una: gli
    ancoraggi YAML — visibili, discutibili, discusse — e la sonda `db.adminCommand('ping').ok`,
    che non aveva l'aria di una scelta e risponde anche a un `mongod` che non è entrato in nessun
    replica set. La prima si vede aprendo il file. La seconda si sarebbe scoperta al primo avvio
    che dichiara pronto un cluster senza cluster. Il codice che ha funzionato altrove non è
    neutro: è un insieme di decisioni prese in un contesto diverso, e passa la frontiera tutto
    insieme se nessuno lo ferma. La regola: quando si importa un artefatto che funziona, si elenca
    che cosa decide, non solo che cosa fa. Le righe che nessuno commenterebbe sono quelle da
    guardare.
93. **Un permesso si prova al suo margine, non al suo centro.** L'eccezione localhost si racconta
    così: ci si collega da dentro e si crea il primo utente. Provandola al centro — `db.hello()` —
    passa, e la storia sembra confermata. Provandola al margine — `db.adminCommand({getCmdLineOpts:
    1})` — risponde `not authorized on admin`. L'eccezione non apre il server: apre la creazione
    del primo utente, e nient'altro. Sono due frasi che si assomigliano e descrivono superfici di
    attacco diverse. Vale per qualunque permesso documentato in prosa: la prova che informa non è
    quella che riesce, è quella che individua dove smette di riuscire. La pagina della sicurezza ha
    un debito in più, e questa volta con il comando che lo dimostra.

## 2026-09-01 — `feature/03`, Task 2: i tre replica set, e una riserva aperta da otto giorni

Sei `mongod` di shard, tre servizi di inizializzazione, e i tre replica set che si formano da soli
in tutti e due i profili. Il file Compose passa da 362 a 868 righe e resta dichiarato incompleto in
testa: mancano `mongos` e `sh.addShard()`, cioè l'unica cosa che trasforma tre replica set separati
in uno sharded cluster. La riga in testa lo dice con quelle parole, perché senza `mongos` non c'è
un cluster a cui manca un pezzo: ci sono tre set che non si conoscono.

**La riserva di ADR-0010 è chiusa, e ha cambiato il progetto del task.** Il piano prevedeva un
servizio di inizializzazione per componente, ciascuno con `depends_on` verso tutti i suoi membri.
Prima di scriverlo ho misurato la cosa che ADR-0010 aveva lasciato in sospeso il 24 agosto, e che
[S-015](Sources.md#s-015) dichiarava non documentata: che cosa succede quando un servizio
selezionato dipende da uno che il profilo attivo non seleziona. La risposta ([V-053](Sources.md#v-053))
è che **fallisce**, che la regola è **simmetrica** — non conta chi ha il profilo — e che Compose
rifiuta l'intero progetto prima di avviare qualsiasi cosa:

```
service "init-con-profilo" depends on undefined service "b": invalid compose project
```

Quattro casi, quattordici righe di `busybox`, e due riserve chiuse in dieci minuti. Il quarto caso
è quello che non mi aspettavo: **nominare un servizio sulla riga di comando non è come attivare il
suo profilo.** `docker compose create init-con-profilo` senza profili attivi esce 0 e crea anche la
dipendenza il cui profilo è spento. È esattamente la frase di S-015, e vale solo per il servizio
nominato. Due modi di selezionare lo stesso servizio, comportamento opposto davanti alla stessa
dipendenza.

**Che cosa ne è seguito** ([ADR-0060](Decision.md#adr-0060)): l'elenco dei membri arriva
dall'ambiente, per esteso e non come conteggio; ogni servizio di inizializzazione dipende da un solo
membro, quello presente in entrambi i profili; e siccome il numero di membri e il numero di
container adesso vengono da due sorgenti diverse per lo stesso fatto, i due script hanno una
guardia bilaterale. L'ho provata rompendola in tutte e due le direzioni
([V-054](Sources.md#v-054)): `--profile completo` con gli elenchi del `palco` fa uscire i tre
one-shot con **5**, `--profile palco` con gli elenchi del `completo` con **4**, e nel secondo caso
il messaggio nomina il container che non risponde. Il caso da temere era il primo, perché di suo
non fallirebbe: nove `mongod` in piedi, tre set a un membro solo, tutto verde, e la scena del
failover senza niente da mostrare.

**I tre set, verificati.** Con `completo`, `rs.status()` risponde `ok=1` con tre membri su tutti e
tre, e il primario è il membro «a» in tutti e tre — `priority: 2` di [ADR-0051](Decision.md#adr-0051)
funziona anche qui, il che per una demo cronometrata vuol dire sapere in anticipo quale container
fermare.

**`up --wait` esce 0 anche quando gli init falliscono**, ed è la riconferma di
[V-025](Sources.md#v-025) su uno stack diverso. Qui in una forma peggiore: Compose ha stampato
`Container sh-cfg-init Healthy` accanto a un container che `docker inspect` descrive come
`exited uscita=5`, e in un'altra prova è uscito 0 mentre i tre one-shot erano ancora in corsa.
[ADR-0041](Decision.md#adr-0041) aveva già deciso la cosa giusta per lo stack 02 — due comandi e non
uno — quindi qui non c'era nessun buco da tappare, solo da applicare. Con una novità che lo stack 02
non poteva mostrare: `docker compose wait cfg-init` **senza** `--profile` risponde `no containers
for project` ed esce 1. Vincolo per il Task 4.

**Il margine dell'eccezione localhost si è spostato.** La nota 93, scritta stamattina, concludeva
che l'eccezione «apre la creazione del primo utente, e nient'altro». Su uno shard senza utenti la
stessa sonda, spinta di una tacca, dice altro: `replSetGetStatus` risponde **piena** — set, membri,
`stateStr` — e `listDatabases` risponde `ok=1` con l'elenco **vuoto**. Negati restano
`getCmdLineOpts`, `serverStatus`, le letture e le scritture. Il confronto di controllo è su `cfg1`,
dove l'utente esiste e quindi l'eccezione è chiusa: lì `replSetGetStatus` e `listDatabases`
rispondono `Unauthorized`, e passa solo `hello()`. La differenza fra le due colonne è l'eccezione e
nient'altro.

**Note di metodo.**

94. **Una riserva aperta è un progetto scritto al buio.** ADR-0010 aveva dichiarato la riserva sui
    profili il 24 agosto e da allora il repository ci girava intorno: lo stack 03 la teneva
    «aggirata per costruzione» lasciando `keyfile-init` senza profilo, che è una soluzione elegante
    e un modo di non sapere. Il Task 2 non poteva più aggirarla, e la misura è costata dieci minuti
    e quattordici righe di `busybox`. Il conto vero non è quello: è che il piano approvato
    descriveva un `depends_on` che Compose avrebbe rifiutato, e sarebbe stato scritto, provato e
    riscritto. Una riserva costa poco finché nessuno progetta sopra il buco che copre. La regola:
    quando un task sta per appoggiarsi a una riserva, la si misura **prima** di scrivere il piano
    del task, non prima di eseguirlo.
95. **La stessa misura, una tacca più in là, può ribaltare la conclusione — e la conclusione
    precedente non era sbagliata a metà: era stretta.** La nota 93 diceva che l'eccezione localhost
    apre la creazione del primo utente «e nient'altro», e l'aveva dedotto da due comandi:
    `hello()` che passa, `getCmdLineOpts` che no. Sette comandi dicono un'altra cosa:
    `replSetGetStatus` passa e risponde per intero, `listDatabases` passa e risponde vuoto. Il
    confine ha una forma, non è una porta aperta o chiusa, e con due punti si può disegnare
    qualunque cosa. Vale in generale per i permessi documentati in prosa: due misure danno una
    retta, e una retta è quasi sempre la risposta sbagliata a una domanda sul perimetro. La
    correzione non va nel testo vecchio — questo registro è cronologico e non si riscrive, come
    le decisioni — va qui, e la voce nuova nomina quella vecchia.
96. **Un errore che nomina il colpevole vale il ciclo di attesa che è costato scrivere.** La
    guardia bilaterale è quaranta righe che Compose avrebbe fatto gratis se i profili lo avessero
    permesso, e la tentazione era di fidarsi del Makefile che tiene allineate le variabili. Regge
    finché nessuno lancia `docker compose` a mano — e questo repository è materiale didattico:
    qualcuno lo lancerà a mano, è anzi lo scopo. La prova di quelle quaranta righe non è che
    funzionano, è che rompendole si legge `il membro «cfg2:27017» non risponde dopo 30 secondi`
    invece di uno stack verde e sbagliato. Il valore di un controllo si misura sul testo che
    produce quando fallisce, non sul fatto che passi quando tutto va bene.

## 2026-09-01 — `feature/03`, Task 3: il router davanti, e una sonda che non poteva essere onesta

Con i due `mongos` e `init/20-add-shard.js` la topologia dello stack 03 è finita: nove `mongod`,
due router, e la riga in `config.shards` che trasforma tre replica set che non si conoscono in uno
sharded cluster. `compose.yaml` passa da 874 a 1109 righe, `.env.example` da 146 a 163, e il nuovo
script ne aggiunge 120.

**Il deadlock trovato prima di scriverlo.** Il piano, al Passo 2 del Task 4, dice: «la domanda è se
il router accetti connessioni prima che gli shard siano registrati. Se sì, l'healthcheck deve
verificare la registrazione, altrimenti `up-03` dichiarerà pronto un cluster senza shard.» La
misura risponde **sì** ([V-055](Sources.md#v-055)), e la conseguenza prescritta è impossibile.
`add-shard` gira dentro `mongos` e lo aspetta sano; se `mongos` diventasse sano solo con gli shard
registrati, il servizio che li registra non partirebbe mai. Lo stack si bloccherebbe indicando il
colpevole sbagliato: Compose direbbe che `mongos` non diventa sano, mentre il vero fermo è il
servizio in coda. Ho disegnato il grafo delle attese prima di scrivere l'healthcheck, e il cappio
si vede a occhio. [ADR-0061](Decision.md#adr-0061): la sonda di `mongos` è di **vita** —
`db.hello().ok === 1`, senza credenziali perché `hello()` non ne chiede — e il verdetto «il cluster
serve» è l'uscita di `add-shard`. È la stessa forma di [ADR-0041](Decision.md#adr-0041) sullo stack
02, non un'invenzione nuova. Il Passo 2 del Task 4 arriva quindi già risposto, con la conclusione
rovesciata rispetto a come il piano la immaginava.

**Un `mongos` senza shard è sano, e mente per omissione.** La misura completa è in V-055, e il
punto che non mi aspettavo è il secondo: `hello()`, `ping`, `listDatabases` e persino una `find`
passano. La `find` su un database inesistente risponde `[]` **senza errore**, identica alla
risposta di un cluster sano con la collezione vuota. Solo la scrittura distingue, e allora sì che
nomina la causa: `ShardNotFound — No shards found`. `sh.status()` intanto stampa `shards []` con
il balancer `Currently enabled: yes`, che è un balancer acceso senza niente da bilanciare.

**La catena si chiude.** `add-shard` esce **0**, registra i due shard e li rilegge; la scrittura
che un minuto prima falliva viene accettata e riletta. `sh.status()` mostra i due shard con
`state: 1`, `active mongoses [ { '7.0.40': 1 } ]` e il balancer attivo con zero giri falliti — è
il Passo 4 del Task 3, rifatto dentro il repository come il piano chiedeva. Riesecuzione con
`--force-recreate`: esce 0 e scrive `già registrato: non lo riaggiungo` per tutti e due.

**Il profilo `completo`, e il router che non ha niente da perdere.** Sedici container, tutti sani o
usciti 0. Con gli elenchi a tre membri `sh.addShard()` registra la composizione per intero, e
`config.mongos` elenca tutti e due i router. Ho fermato `sh-mongos` con `docker stop` e dato la
scrittura a `mongos2`: passa, e `mongos2` vede i due shard. Niente è andato perso perché su un
`mongos` non c'è niente da perdere — è l'unico servizio dello stack **senza volume**, e insieme
all'assenza di `--replSet` e di `--wiredTigerCacheSizeGB` (che passato a un `mongos` lo fa
fallire: non ha uno storage engine) sono le tre assenze che spiegano che cos'è un router. Il
`--keyFile` invece c'è: l'autenticazione interna è di tutto il cluster.

**Note di metodo.**

97. **Un `depends_on` verso una sonda che il dipendente stesso deve soddisfare è un cappio, e si
    vede solo disegnando il grafo delle attese.** La regola generale, che vale oltre Compose:
    quando B aspetta la sonda di A, e il lavoro di B è **cambiare ciò che quella sonda
    misurerebbe**, la sonda di A può solo chiedere se A è vivo. Renderla più severa è una
    tentazione che si presenta come rigore — «che `healthy` voglia dire davvero pronto» — e
    produce uno stack che non parte. La difesa non è averci pensato: è che prima di scrivere un
    `depends_on` con `service_healthy` guardo chi altro aspetta quella stessa sonda e che cosa fa
    a valle. Costa un minuto e si fa sulla carta.
98. **Un guasto che risponde bene costa più di uno che risponde male.** Un cluster senza shard
    restituisce `[]` a una lettura, che è la risposta giusta alla domanda sbagliata: chi legge
    conclude che il database è vuoto e va avanti. Se la verifica di prontezza che scriverò al Task
    7 facesse una `find`, passerebbe su un cluster inservibile. Perciò lo smoke **deve scrivere**,
    e il criterio non riguarda solo questo caso: una verifica che esercita solo il percorso di
    lettura sta misurando che il processo è vivo, non che il sistema funziona. Vale anche per la
    demo dal vivo, dove la prima scrittura arriva sempre dopo aver già detto al pubblico che il
    cluster è pronto.
99. **Un piano che decide in anticipo la conseguenza di una misura ha già smesso di misurare.** Il
    Passo 2 del Task 4 è scritto bene per metà: «provare … e **scegliere misurando**» è la forma
    giusta, e l'ho scritta io. Poi la frase dopo — «se sì, l'healthcheck deve verificare la
    registrazione» — infila la conclusione dentro la premessa, e quella conclusione era
    impossibile per una ragione che nessuna misura avrebbe mostrato, perché non stava nel
    comportamento di `mongos` ma nella forma del grafo delle dipendenze. Il costo qui è stato
    zero, perché la misura è caduta un task prima e il cappio si è visto. La regola: un passo di
    piano che dice «misura X, e se esce così fai Y» va riscritto come «misura X» e basta, a meno
    che Y non sia stato a sua volta verificato. Il piano approvato non si modifica quando
    l'esecuzione se ne scosta — è la fotografia di che cosa si era deciso, e riscriverlo
    cancellerebbe proprio lo scarto che vale la pena leggere. Lo scarto si registra qui, e il Task
    4 troverà il suo Passo 2 già evaso con l'esito opposto.

## 2026-09-01 — `feature/03`, Task 4: un servizio che non fa niente, e due misure senza valore

Il Task 4 arrivava già mezzo evaso. Il Passo 1 — gli healthcheck dei `mongod` — lo aveva scritto
il Task 2, disgiunzione a tre termini e commento che spiega perché differisce dal `ping` dello
spike. Il Passo 2 lo aveva evaso il Task 3, con la conclusione rovesciata rispetto a come il piano
la immaginava ([ADR-0061](Decision.md#adr-0061)). Restavano il Passo 3 e il Passo 4, che sono la
stessa domanda scritta due volte: si può fare in modo che `docker compose up --wait` esca 0
soltanto quando il cluster serve?

**Non si può verificare, si può costruire.** Così com'è la proprietà è falsa, e
[V-025](Sources.md#v-025) lo diceva dal 31 agosto. L'ho rimisurata qui perché la misura vecchia
era su un altro stack: senza sentinella `up --wait` esce **0 dopo diciotto secondi**, con
`add-shard` ancora in corsa e **zero shard registrati**. E — questo è il caso che conta — esce
**0 anche quando la catena è rotta**, cioè quando `add-shard` fallirà e nessuno shard esisterà
mai. Diciotto secondi per dichiarare pronto un cluster che non lo sarà.

La costruzione è un servizio che dipende da `add-shard` con `service_completed_successfully`, non
ha healthcheck e dorme. Non diventa `running` finché `add-shard` non è uscito 0, e `--wait`
aspetta che diventi `running`. Con la sentinella accesa: 0 a cluster fatto, con `sh.status()` già
utile nell'istante in cui `up` torna, oppure **1** con `service "add-shard" didn't complete
successfully: exit 6`. [ADR-0062](Decision.md#adr-0062).

**E il secondo comando qui farebbe danno.** `docker compose wait add-shard` dopo un `up --wait`
riuscito risponde `no containers for project` ed esce 1, con il profilo acceso: il container ha
già finito e `wait` vuole qualcosa di vivo. La forma che [ADR-0041](Decision.md#adr-0041)
prescrive allo stack 02 è la forma che sullo stack 03 fallisce sempre. Il Task 7 scriverà una riga
sola. Resta un dubbio sullo stack 02, che i due comandi li esegue davvero: lì funziona perché
`up --wait` torna prima che `rs-init` finisca, ma la distanza è di secondi e nessuno l'ha misurata
altrove. Debito per il Task 7.

**Il ramo d'errore che non era mai stato eseguito.** Rompendo apposta la stringa di uno shard è
venuto fuori che `sh.addShard()` **solleva** invece di rispondere `ok: 0`. Il controllo
`if (!esito.ok)` che avevo scritto ieri in `20-add-shard.js` non veniva quindi valutato mai:
mongosh usciva 1 per eccezione non gestita, l'uscita 6 era irraggiungibile e le due righe che
nominano le cause frequenti — quelle che secondo la nota 96 sono il valore del controllo — non si
stampavano. Con il `try/catch` il caso rotto esce 6 e le stampa.

**Note di metodo.**

100. **Un controllo che non controlla vale meno di nessun controllo, perché occupa il posto.**
     Per misurare lo stack «com'era prima della sentinella» ho scritto un file di override che
     metteva `profiles: ["mai"]` su `up-03`, convinto di spegnerlo. La Compose **accoda** le liste
     invece di sostituirle: la lista risultante era `["palco","completo","mai"]` e `--profile
     palco` continuava a selezionarlo. Due misure sono uscite con numeri plausibili — 61 secondi,
     due shard registrati — e le ho quasi scritte in `Sources.md` come prova che la sentinella non
     serviva. Erano lo stack con la sentinella accesa, misurato due volte. Le ha smontate una
     domanda sola, `config --services | grep -c up-03`, che risponde 1 dove doveva rispondere 0.
     La regola: quando un esperimento ha un braccio di controllo, la prima cosa da verificare non
     è il risultato, è **che il controllo sia diverso dal trattamento**. Costa un comando e
     protegge dalla peggiore specie di errore, quella che produce numeri credibili.
101. **Un ramo d'errore che non è mai stato eseguito non è codice: è un'intenzione.** Le sei righe
     dentro `if (!esito.ok)` erano scritte bene, nominavano le due cause frequenti, uscivano con
     il codice che ADR-0036 assegna. Erano irraggiungibili, perché `sh.addShard()` solleva invece
     di restituire. Non me ne sarei accorto scrivendo un altro test del percorso felice: me ne
     sono accorto perché il Passo 4 mi obbligava a rompere la catena per vedere che cosa fa
     `up --wait` quando fallisce, e rompendola ho letto l'uscita sbagliata. Vale come regola:
     ogni ramo d'errore va **eseguito almeno una volta**, e il modo di eseguirlo va scritto
     accanto. La nota 96 diceva che il valore di un controllo è il testo che produce quando
     fallisce; questa è la nota gemella, e dice che quel testo va letto davvero, una volta, con
     gli occhi.
102. **Il piano aveva ragione a chiedere una verifica impossibile.** Il Passo 4 chiedeva di
     verificare che `up --wait` esca 0 soltanto a cluster utile, e quella proprietà era falsa e
     già documentata come falsa. Un piano più prudente avrebbe scritto «prendere atto che
     `up --wait` non aspetta i one-shot e usare due comandi», e avrei scritto due comandi — che su
     questo stack falliscono. La richiesta impossibile ha costretto a chiedersi se la proprietà si
     potesse **costruire** invece che verificare, ed è saltato fuori sia il servizio sentinella sia
     il fatto che la ricetta dello stack 02 qui non funziona. Non è un invito a scrivere piani
     sbagliati: è che un passo di piano formulato come proprietà desiderata («deve valere X»)
     interroga meglio di uno formulato come procedura («fai Y»), perché quando X non vale
     costringe a cercare, mentre Y si esegue e basta.

## 2026-09-01 — `feature/03`, Task 5: le regole dei ruoli, e la scoperta che l'errore non era muto

Il Task 5 chiede di insegnare allo strumento le regole dello sharded, in TDD. Il piano ne elencava
sei. La prima cosa fatta è stata contarle contro il codice che c'era: **tre erano già in vigore** —
niente IP letterali, `mem_limit`/`cpus`/`pull_policy` su ogni servizio, cache non superiore alla
memoria su ogni `mongod` — e valgono sui ruoli nuovi senza che nessuno le abbia estese, perché non
guardano il ruolo. Una prova esisteva da prima che lo stack 03 esistesse: un test dello stack 01
usa un comando `mongos` proprio per dire che a lui la cache non si chiede. Sono entrate comunque
nella suite due verifiche che lo mettono per iscritto sui ruoli nuovi, perché «vale ancora» e «non
è mai stato messo alla prova» si somigliano troppo.

**Prima le misure, poi i test, poi il codice.** L'ordine del TDD dice test-codice; qui davanti a
tutti e due sono andate le misure, per un motivo di forma che questo repository ha già scelto: i
messaggi di `check_stack.py` citano il sintomo che prevengono, e un sintomo si cita dopo averlo
visto. Sei modi di sbagliare i ruoli, misurati uno per uno ([V-057](Sources.md#v-057)). Quattro
costano un `docker run` di tre secondi; due hanno richiesto una copia dello stack rotta apposta e
un avvio intero.

**La notizia è arrivata al contrario.** L'aspettativa era di trovare errori muti, che è la
giustificazione classica di una regola statica. Invece **cinque sintomi su sei nominano l'opzione
che manca**, in inglese, con una frase che si cerca in rete così com'è: «Cannot run addShard on a
node started without --shardsvr», «Nodes being used for config servers must be started with the
--configsvr flag», «shardsvr is not allowed when configsvr is specified». La giustificazione comoda
era falsa. Quella vera è più modesta e regge meglio: il guadagno non è tradurre un messaggio
oscuro, è **incontrarlo in due secondi su un file fermo invece che al minuto e ventuno di un avvio,
con dieci container accesi e il pubblico che guarda**.

Due commenti del repository sostenevano quella giustificazione e sono stati corretti. Il primo, su
`shard1a`, diceva che senza `--shardsvr` «il messaggio parla d'altro»: non parla d'altro, nomina
esattamente la riga che manca. Il secondo, su `cfg1`, diceva che sulla forma abbreviata del comando
la regola della cache non scatta: era vero fino al Task 3 di `feature/02`, che l'ha riparata
([ADR-0042](Decision.md#adr-0042)), ed è rimasto scritto per un mese oltre la sua scadenza.

**Il sesto sintomo però è muto sul serio, e ripaga tutte le regole da solo.** `cfgsr` per `cfgrs`
dentro `--configdb`: due lettere. Tutti i processi partono, `up --wait` esce 1 dopo
**novantaquattro secondi** — il caso più lento dei sei — il router resta `unhealthy` senza mai
aprire la porta, e nel suo log **la stringa `cfgrs` non compare nemmeno una volta**. Contata: zero
occorrenze. Quello che si legge è `HostUnreachable` su `cfg2` e `cfg3`, che nel profilo `palco`
sono irraggiungibili per costruzione, e `FailedToSatisfyReadPreference` sull'unico host che
risponde benissimo. La diagnosi indica la rete; la causa sono due lettere.

**Cinque regole, e il criterio che decide a chi si applicano.** La parte difficile non era
controllare due opzioni, era far **dedurre il ruolo** allo strumento senza chiederlo a un elenco di
nomi. La catena sta tutta nel file: il `mongos` nomina in `--configdb` il replica set dei config
server, ogni `mongod` nomina in `--replSet` il proprio, chi appartiene al primo è un config server
e chiunque altro è uno shard. Un test rinomina `cfg1` in `secondo` e `shard1a` in `primo` e pretende
zero problemi. Le regole tacciono sugli stack 01 e 02 perché quei file non hanno un `mongos`, non
perché siano in una lista di eccezioni — è il criterio di ADR-0042, ripreso identico
([ADR-0063](Decision.md#adr-0063)).

**Due deviazioni dal piano, dichiarate.** La prima: le regole implementate sono cinque, non tre. La
regola sui due ruoli insieme è venuta dietro alla stessa domanda — per decidere il ruolo bisogna
gestire prima il caso «tutti e due» — e quella sul `mongos` senza cache protegge il ruolo nuovo
dall'errore che un file didattico rende più probabile di ogni altro, copiare il blocco di un
`mongod` e cambiare solo la prima riga. La seconda: il piano scriveva «la stringa `--configdb`
nomina il set `cfgrs`», e `cfgrs` dentro lo strumento non ci è entrato. Avrebbe legato un controllo
generico al nome di un solo stack, contro il principio che lo stack è un argomento, e avrebbe perso
proprio il caso del refuso — dove il nome non è sbagliato in assoluto, è **incoerente con il resto
del file**. Il piano approvato non si tocca: la deviazione si registra qui.

**Una cosa presa dal Task 7 in anticipo.** Il Passo 4 chiede `make stack-check` con tre stack
conformi, e `STACK_03` nel `Makefile` era assegnato al Task 7. Entra ora, perché senza non esiste
il modo di evadere il passo. Al Task 7 resta tutto il resto: i bersagli `up-03`/`down-03` e
compagnia, `reset-demo.sh`, le porte in `preflight`.

**Verificato eseguendo.** I sette test nuovi rossi prima del codice, tutti con `AssertionError: []`
— nessuna regola, non un errore d'importazione. Dopo: `make tools-test` **125 passed**, erano 114.
`make stack-check` **tre stack conformi**. E la prova che ADR-0042 aveva stabilito e che un verde
non sostituisce: sette copie dello stack 03 vero, un difetto ciascuna, la copia intatta a zero
problemi e le altre sei a **un problema ciascuna**, sei messaggi distinti. Un problema per copia, e
non una cascata: la regola che scatta è quella del difetto introdotto. Ogni avvio chiuso con
`down -v`, nessun residuo.

**Note di metodo.**

103. **Misurare prima di scrivere la regola non serve a sapere se la regola serve: serve a sapere
     perché.** La regola sul `--shardsvr` sarebbe stata scritta identica anche senza misurare
     niente — il vincolo è documentato, il codice è lo stesso. Quello che sarebbe cambiato è la
     frase accanto, e con la frase la giustificazione dell'intera famiglia. Avrei scritto «senza
     questa regola l'errore è illeggibile», che è comodo, plausibile e **falso**, e sarebbe
     rimasto scritto in un ADR come motivo di una decisione. La regola generale: quando si
     costruisce una difesa, l'attacco va provato davvero, perché la difesa si scrive uguale ma la
     ragione no — e la ragione è la parte che gli altri leggeranno.
104. **Un commento che descrive il comportamento di un altro file è un'affermazione a termine, e
     nessuno le mette la scadenza.** Ne sono stati trovati due nello stesso file, tutti e due
     scritti da me: uno diceva che `check_stack.py` non riconosce la forma abbreviata del comando
     — vero fino al Task 3 di `feature/02`, che l'ha riparata, e rimasto scritto per un mese
     oltre — e uno diceva che `sh.addShard()` non nomina la causa, smentito dalla prima misura di
     oggi. Nessuno dei due era sbagliato quando è stato scritto. La differenza fra i due generi di
     commento è netta e vale la pena tenerla a mente scrivendo: «questa riga fa X» invecchia con
     la riga sotto, e la riga sotto è nello stesso schermo; «questo serve perché altrove succede
     Y» invecchia quando cambia Y, che è in un altro file, e non c'è nessun controllo automatico
     che possa accorgersene. La contromossa che costa poco è citare la misura — «V-057», «S-022»
     — così chi rilegge sa **dove** andare a verificare se vale ancora.
105. **Una regola generica non deve contenere il nome del caso particolare che l'ha fatta
     nascere.** Il piano chiedeva di verificare che `--configdb` nomini il set `cfgrs`, e la
     traduzione letterale — cercare la stringa `cfgrs` — sarebbe passata su tutti i test scritti
     per lo stack 03 e avrebbe fatto verde su `make stack-check`. Sbagliava due volte. Legava uno
     strumento che prende lo stack come argomento al nome usato da uno solo dei tre; e soprattutto
     avrebbe **mancato il caso vero**, perché il difetto che conta non è che il nome sia diverso
     da `cfgrs`, è che sia diverso da quello che i config server dello stesso file dichiarano. La
     forma generale — «il set nominato da `--configdb` deve essere dichiarato da qualche `mongod`
     di questo file» — è più corta da scrivere, non usa nessun nome proprio, e prende il refuso
     che quella letterale lasciava passare. Quando la versione generale di una regola è anche
     quella che cattura di più, è un segnale che il caso particolare era la formulazione sbagliata
     della domanda.

## 2026-09-01 — `feature/03`, Task 6: i dati distribuiti, e la prova che sa distinguere due shard da uno

Il Task 6 mette dentro lo stack la cosa per cui il Blocco 3 esiste: la shard key. Tutto il resto —
i tre ruoli, la catena, il router davanti — è impalcatura per arrivare a una riga,
`sh.shardCollection("lab.ordini", {_id: "hashed"})`, e a una domanda: perché quella e non un'altra.

**La fortuna del dataset.** Gli `ordini` generati dal seme `20260918` hanno `_id` interi
consecutivi `0 … n-1`. È esattamente il **caso peggiore** per una chiave per intervalli, e quindi
l'esempio migliore possibile per spiegare perché serve l'hash: con `{_id: 1}` ogni inserimento
cadrebbe nel chunk con estremo superiore `MaxKey`, che sta su un nodo solo. Nessuno l'aveva scelto
per questo — il generatore viene da `feature/01` e serviva a tutt'altro — ma il materiale del Blocco
3 si è scritto quasi da sé.

**Prima si distribuisce, poi si riempie, e il numero era già documentato.** Lo spike §5 aveva
misurato quattro chunk e li aveva annotati come una curiosità. Rileggendo il manuale prima di
scrivere il commento è venuto fuori che non è una curiosità: distribuendo una collezione **vuota**,
«the sharding operation creates empty chunks … by default, the operation creates 2 chunks per shard
and migrates across the cluster» ([S-066](Sources.md#s-066)). Due per shard, due shard, quattro. Da
misura senza spiegazione a valore predefinito con una fonte, che dal palco è tutta un'altra frase.
Sull'ordine inverso il manuale è altrettanto netto — su una collezione piena si crea **un** chunk
solo e poi tocca al balancer — e l'avvio del lab diventerebbe una gara col balancer, con
`sh.status()` che al primo colpo mostra 100 % / 0 %.

**Il seed diventa il sesto anello, ed è uno scostamento dal piano.** Il Task 6 nominava due file. Ne
è servito un terzo intervento, sul file Compose, per una ragione che si vede solo scrivendo lo
smoke: l'unica asserzione che distingue uno sharded cluster funzionante da uno rotto è la
distribuzione dei documenti, e per misurarla i documenti devono già esserci. Con il dataset affidato
a un comando separato, `make smoke-03` dopo `make up-03` sarebbe fallito — o peggio, sarebbe andato
verde saltando l'unico controllo che conta. Il one-shot `seed` entra dopo `add-shard`, la sentinella
`up-03` sposta la dipendenza su di lui, e quello che cambia è **che cosa promette `up --wait`**: non
più «i due shard sono registrati» ma «c'è anche il dataset», che è la promessa che gli altri due
stack fanno già ([ADR-0065](Decision.md#adr-0065)). Il piano approvato non si tocca: lo scostamento
si registra qui.

**Ventimila anche in `completo`, contro lo spike.** Il piano fissa 20 000 per `palco`; lo spike
usava 50 000 per `completo`. Sono 20 000 in tutti e due, perché i profili differiscono nella
topologia e non nei dati, e un dataset che cambia col profilo renderebbe i numeri mostrati dal palco
dipendenti da quale profilo sta girando. La misura dice che non si perde niente: distribuzione
identica nei due profili, 9860 e 10140, perché dipende dall'hash delle chiavi e i membri in più sono
copie dello stesso shard ([V-058](Sources.md#v-058)).

**Lo smoke è stato scritto al contrario.** La domanda da cui è partito non era «che cosa posso
controllare», era **«che cosa resterebbe verde su un cluster che ha messo tutti i ventimila
documenti su un solo shard»**. La risposta è: tutto. Un cluster così risponde, scrive, legge, e
`sh.status()` gli mostra due shard belli attivi. Da lì i controlli si sono scelti da soli — la
distribuzione per shard con una soglia al 40 %, e il baratto della chiave in forma eseguibile:
uguaglianza su `_id` → **uno** shard, intervallo sulla stessa chiave → **tutti e due**. Se un giorno
la seconda tornasse 1, la chiave non sarebbe più hashed, e nessun altro controllo se ne
accorgerebbe.

**Due cose imparate provando, che nessuno aveva previsto.** La prima: gli utenti di uno sharded
cluster vivono nel database `admin` dei **config server**, e la stessa coppia utente/password che
funziona sul router dà `Authentication failed` su uno shard interrogato in diretta. Non è un guasto,
è la regola, e lo smoke ora la asserisce come tale; la conseguenza pratica è che le misure interne
dei nodi si leggono da `docker inspect` e dalla riga `cache_size=…` del log di avvio, non da
`hostInfo()`. La seconda è l'unico rosso dell'intera prova: il controllo «il router non monta
`/data/db`» **fallisce su un cluster sano**, perché l'immagine di MongoDB dichiara `VOLUME /data/db`
nel proprio Dockerfile e Docker crea un volume anonimo su ogni container che ne nasce, `mongos`
compreso. Il discriminante vero è il volume **nominato**, e ora lo smoke controlla tutti e due i
versi: nessun `dati-…` sul router, uno per ciascun `mongod`.

**Le citazioni sono state riverificate, e la verifica ha cambiato il contenuto.** Sei frasi del
manuale erano state trascritte nel file dei dati attribuendole a una sola pagina. Rileggendo le
pagine per scrivere `Sources.md` è saltato fuori che **due erano dell'altra** — il testo era
verbatim, l'attribuzione no. La rilettura ha però portato anche una riga che nella prima stesura
mancava, e che cambia il racconto: «to optimize data distribution, the chunks that contain the
global `maxKey` (or `minKey`) do not stay on the same shard» ([S-067](Sources.md#s-067)). Il collo
di bottiglia di una chiave monotona **cambia nodo** man mano che i chunk si dividono; non sparisce,
ma non è il nodo unico e immobile che le spiegazioni brevi descrivono. Senza quella riga il Blocco 3
avrebbe raccontato una caricatura, e una caricatura si smonta alla prima domanda del pubblico.

**Verificato eseguendo, nei due profili.** `up -d --wait` a uscita 0 in **23 secondi** su `palco` e
**36** su `completo`, dataset compreso; il secondo `up` di seguito esce 0 e il seed stampa «ha già
20000 documenti: non ricarico». `tools/smoke-sharded.sh` chiude a **62 controlli superati e 0
errori** su `palco` e **99 e 0** su `completo`. `make tools-test` 125 passed, `make stack-check` tre
stack conformi, `make docs-check` verde. `.env` di scarto cancellato, `down -v` in coda a ogni giro,
residui contati a zero: nessun container, nessun volume, nessuna rete.

**Note di metodo.**

106. **La prova utile non è quella che passa: è quella che sarebbe verde sul guasto vero.** Scrivendo
     lo smoke la domanda produttiva è stata «che cosa resterebbe verde su un cluster rotto», e la
     risposta ha riscritto l'ordine dei controlli. Sessantadue asserzioni, e **una sola** distingue
     uno sharded cluster da un replica set travestito: la distribuzione. Le altre sessantuno sono
     utili, ma se ci fossero solo quelle la prova andrebbe verde su un cluster che non partiziona
     niente. Il modo in cui una suite cresce di solito è per aggiunta di controlli facili, che
     danno la sensazione di essere più protetti senza spostare la copertura di un millimetro: il
     controllo che vale è quello che si sa nominare **prima**, dicendo quale guasto lo farebbe
     diventare rosso.
107. **Quando un controllo ovvio fallisce su un sistema che hai ragione di credere sano, il primo
     sospettato è il controllo.** «Un router non ha dati, quindi non monta `/data/db`»: ineccepibile
     e falso, perché l'immagine dichiara `VOLUME /data/db` e Docker obbedisce su ogni container che
     ne nasce. Il punto generale non è la sorpresa in sé, è che `docker inspect` mostra allo stesso
     modo **quello che hai chiesto tu e quello che l'immagine ha imposto**, e i due si distinguono
     solo guardando se il volume ha un nome. Vale oltre Docker: ogni strumento che riporta uno
     stato mescola le tue dichiarazioni con i valori predefiniti di qualcun altro, e un controllo
     scritto senza sapere quale delle due sta leggendo è un controllo che prima o poi accusa la
     persona sbagliata.
108. **Una citazione attribuita alla pagina sbagliata è peggio di nessuna citazione, e riverificarla
     paga due volte.** Sei frasi verbatim, una sola fonte indicata, due in realtà venute da un'altra
     pagina: chi fosse andato a controllare non le avrebbe trovate, e avrebbe avuto ragione di
     dubitare anche delle altre quattro. Il costo della riverifica è stato due letture; il ricavo è
     stato doppio, perché rileggendo per sistemare l'attribuzione è comparsa una riga che nella
     prima stesura mancava e che ha cambiato il contenuto didattico, non la sua bibliografia. La
     regola operativa che ne esce: la fonte si rilegge **quando si scrive la voce in `Sources.md`**,
     non quando si copia la frase — sono due momenti diversi, e il secondo è l'unico in cui si sta
     guardando la pagina intera invece della frase che serviva.

## Punto di ripresa — 2026-09-01, quarta sospensione: `feature/03` riparte dal Task 7

**Deciso e chiuso.** I Task **1-6** del
[piano di `feature/03`](00-progetto/2026-09-01-piano-feature-03-stack-sharded.md) sono chiusi, tutti
verificati eseguendo. Lo stack 03 **è completo e funziona con un comando solo**: undici servizi nel
profilo `palco`, diciotto in `completo`, e una catena di sei anelli — `keyfile-init` →
(`cfg-init`, `shard1-init`, `shard2-init`) → `mongos` → `add-shard` → `seed` → sentinella `up-03`.
Decisioni fino a **ADR-0065**, verifiche fino a **V-058**, fonti fino a **S-067**, note di metodo
fino a **108**. Otto commit sul ramo, l'ultimo è `f15092b`, tutti spinti su
`origin/feature/03-stack-sharded`.

Quello che resta fuori dallo stack è **solo** ciò che non è topologia: i bersagli del `Makefile`
(Task 7) e le pagine (Task 8-10). Il file Compose non ha altri servizi da ricevere.

**Misurato oggi, e da non rimisurare.**

- **I sei modi di sbagliare i ruoli** ([V-057](Sources.md#v-057)): cinque su sei danno un messaggio
  che nomina l'opzione mancante. Il sesto — `cfgsr` per `cfgrs` dentro `--configdb` — è muto:
  `up --wait` esce 1 dopo **94 secondi** e la stringa giusta non compare **zero volte** nel log del
  router. È il caso che giustifica le cinque regole nuove di `check_stack.py`.
- **La distribuzione** ([V-058](Sources.md#v-058)): con `{_id: "hashed"}` su collezione vuota,
  **4 chunk** e **9860 / 10140** documenti, cioè 49,3 % / 50,7 %. **Identica nei due profili**, e i
  quattro chunk sono il predefinito documentato di [S-066](Sources.md#s-066), non un numero
  emergente.
- **Il baratto della shard key**, misurato: `{_id: 42}` interroga **uno** shard,
  `{_id: {$gte: 100, $lt: 200}}` li interroga **tutti e due**.
- **Gli utenti stanno sui config server**: le credenziali del cluster danno `Authentication failed`
  su uno shard interrogato in diretta, e funzionano su `cfg1`. Conseguenza operativa: le misure
  interne dei nodi si leggono da `docker inspect` e dalla riga `cache_size=…` del log, **non** da
  `hostInfo()`.
- **`/data/db` risulta montato anche su `mongos`**, perché l'immagine dichiara `VOLUME /data/db`.
  Il discriminante fra nodo e router è il volume **nominato**, non la destinazione.
- **Tempi e impronte:** `up -d --wait` a uscita 0 in **23 s** (`palco`) e **36 s** (`completo`),
  dataset compreso; secondo `up` idempotente. Impronta di `lab.ordini`:
  **`20000 50083417.93 60278`** — sono i primi 20 000 dei 50 000 degli stack 01 e 02, quindi
  **diversa** dall'impronta di `smoke-01` e `smoke-02`, e deve esserlo. Porte **27117** e **27118**.
- **Le prove:** `tools/smoke-sharded.sh` a **62 controlli · 0 errori** su `palco` e **99 · 0** su
  `completo`; `make tools-test` **125 passed**; `make stack-check` **tre stack conformi**;
  `make docs-check` verde.

**Prossimo passo, in ordine.**

1. **Task 7** — `Makefile`, `tools/reset-demo.sh`, `tools/preflight.sh`. Tre avvertenze che valgono
   più del passo: *(a)* lo stack 03 si avvia con **un** comando — `up -d --wait` e basta — mai con
   i due di `up-02`, perché la sentinella rende `up --wait` onesto ([ADR-0062](Decision.md#adr-0062))
   e `docker compose wait add-shard` dopo un `up` riuscito risponde «no containers for project» e
   esce 1; *(b)* `seed-03` va scritto come `seed-02`, cioè
   `$(COMPOSE_03) run --rm -e RICARICA=1 seed` (`Makefile:147` è il modello); *(c)* `STACK_03` e la
   riga di `stack-check` **esistono già**, sono entrate al Task 5.
2. **Task 8** — `docs/02-architetture/sharded-cluster.md`. Il materiale è già scritto e citato:
   il blocco `LA SHARD KEY` di `docker/03-sharded/init/30-dati-demo.js`,
   [ADR-0064](Decision.md#adr-0064) e le due fonti. La pagina lo raccoglie, non lo riscopre.
3. **Task 9** — i debiti marcati, che si chiudono **eseguendo** ([ADR-0049](Decision.md#adr-0049)).
4. **Task 10** — la riserva del Blocco 3.
5. **Task 11** — ADR, fonti e chiusura del ramo **con la PR**. Mai `git flow feature finish`.

**Un debito aperto, che il Task 7 dovrebbe guardare.** [ADR-0062](Decision.md#adr-0062) ha lasciato
in sospeso se il pattern a due comandi di `up-02` sia fragile: funziona solo perché `up --wait`
torna prima che `rs-init` abbia finito. Non è verificabile da questo worktree, perché il `.env`
dello stack 02 vive nel checkout principale ([ADR-0056](Decision.md#adr-0056)).

**Stato dell'ambiente alla sospensione, e come rimetterlo.** Dello stack 03 **non resta niente**:
zero container, zero volumi, zero reti, e nessun `.env` — quello usato per le prove era di scarto ed
è stato cancellato. Prima di qualunque avvio dello stack 03 va quindi **creato** il file:

```
cp docker/03-sharded/.env.example docker/03-sharded/.env   # poi riempire PASSWORD_AMMINISTRATORE
```

e per il profilo `completo` vanno **anche** scommentate le tre righe `MEMBRI_*` a tre membri, perché
il profilo da solo accende i container ma non cambia il numero di membri che gli init configurano —
si otterrebbero nove `mongod` accesi e tre replica set a un membro. Il file è ignorato da git e,
a merge avvenuto, la sua sede è il **checkout principale** (ADR-0056): dentro un worktree è
invisibile a `git status` e `git worktree remove` lo cancella in silenzio.

Restano invece accesi i tre `mongod` dello **stack 02** (`sqlstart-02-replicaset`), avviati dal
checkout principale e **lasciati deliberatamente dov'erano**: non appartengono a questa sessione, e
su un progetto con più sessioni in parallelo smontare un `up` altrui non è una pulizia, è una
perdita di dati per qualcun altro. Si fermano, volendo, con `make down-02` dal checkout principale.

**Comandi per verificare che lo stato sia quello descritto.**

```
git -C .claude/worktrees/feature-03-stack-sharded log --oneline -1   # f15092b
git status --porcelain                                              # vuoto
docker ps -a --filter name=sh- -q | wc -l                           # 0
docker volume ls --filter name=sqlstart-03 -q | wc -l               # 0
make tools-test && make stack-check && make docs-check              # 125 · 3 · verde
```

## 2026-09-02 — `feature/03`, prima del Task 7: il passo che manca a chi clona

Riprendendo il lavoro, il PO ha chiesto **chi** debba compilare il `.env` che il punto di ripresa
dava per mancante, e se la cosa sia chiarita dove la troverà **il pubblico del talk**, che il
laboratorio lo userà da solo dopo la presentazione. La prima è una domanda di un minuto; la seconda
ha scoperto un difetto.

**La risposta alla prima.** Il `.env` lo compila chi esegue il lab, e ha **una sola riga** da
scrivere: `PASSWORD_AMMINISTRATORE`. Tutto il resto di `.env.example` porta già i valori del lab.
La riga è vuota di proposito ([ADR-0040](Decision.md#adr-0040)) e il `Makefile` non la riempie: la
regola è su un **file**, e se manca si ferma stampando come crearlo. Per lo stack 03 la password è
stata copiata da quella dello stack 02 — un solo segreto per tutto il laboratorio, così dal palco
non se ne ricordano due — con il valore mai passato per la chat né per la riga di comando.

**Una correzione al punto di ripresa di ieri.** Diceva che il `.env` va nel checkout principale
(ADR-0056). Oggi **non è possibile**: il checkout principale è su `develop`, dove
`docker/03-sharded/` non esiste ancora perché il ramo non è unito. Finché dura `feature/03` quel
file vive nel worktree ed è per forza usa-e-getta, cancellato in silenzio da `git worktree remove`.
La sede indicata dall'ADR resta quella giusta, ma vale **da merge avvenuto**: è una precisazione,
non un cambio di decisione, e non serve un ADR nuovo.

**Il difetto, che la seconda domanda ha trovato.** La guida di avvio del `README.md` porta da
`git clone` a `make up-01` e finisce lì. Funziona, perché l'istanza singola non ha utenti e quindi
non ha `.env`. Ma dal secondo stack in poi il file serve, e nessuna pagina lo diceva **prima** del
comando che lo pretende: né il `README.md`, né la §6 «Provarlo in due minuti» della pagina sul
[replica set](02-architetture/replica-set.md), che comincia anch'essa da `make up-02`. Il vuoto era
doppio, perché la stessa riga del `README.md` affermava «dei tre stack Compose oggi c'è il primo»
mentre la tabella dello stato, dodici righe più in su, ne dichiarava **due** nel repository: un
paragrafo rimasto fermo a `feature/01`.

Non era un vicolo cieco — la regola del `Makefile` stampa il file mancante e il comando per crearlo,
ed è scritta apposta ([ADR-0014](Decision.md#adr-0014)) — ma è attrito: lo scopri sbagliando, e chi
prova il lab a casa la sera dopo il talk non ha nessuno a cui chiedere. Corretti tutti e due i
punti: il `README.md` ha una sezione «Dal secondo stack in poi serve un file che il repository non
contiene» che dice il perché prima del come, e la §6 una premessa di quattro righe.

Nessun ADR: non si è deciso niente di nuovo, si è scritto un passo che c'era già e che nessun lettore
poteva indovinare. Nessuna fonte: il contenuto viene da ADR-0040 e ADR-0014, già citati.

**Verificato:** `make docs-check` verde, `make tools-test` 125 passed.

109. **La documentazione di avvio la scrive sempre qualcuno che il primo passo l'ha già fatto, e
     per questo è il passo che sparisce.** Chi ha scritto la guida aveva il `.env` sul disco da
     settimane: per lui `make up-02` *è* il primo comando, e la sequenza gli sembrava completa
     perché sulla sua macchina lo era. Il difetto non si vede rileggendo — rileggendo si ricostruisce
     mentalmente lo stato che si ha già — e non lo prende nessun controllo automatico, perché
     `check_links` verifica che i rimandi esistano, non che la procedura sia eseguibile da zero.
     Lo prende una domanda sola, che conviene farsi a ogni pagina di istruzioni: **su una macchina
     appena clonata, il primo comando che scrivo funziona?** Qui la risposta era no, e nessuno se
     n'era accorto in due stack. Il corollario è che gli stati «già configurato» vanno elencati
     esplicitamente in cima a ogni procedura, perché sono invisibili proprio a chi la scrive.

## 2026-09-02 — `feature/03`, Task 7: i bersagli dello stack 03, e il difetto che li aspettava

Il Task 7 doveva essere il più corto del blocco: sei bersagli nel `Makefile` con gli stessi nomi
degli altri due stack, un caso in più in `reset-demo.sh`, le porte nuove in `preflight.sh`. Due dei
tre passi sono andati come previsto. Il terzo non c'era da fare, e nel provare i primi due è saltato
fuori un guasto che nessuno dei sei task precedenti aveva potuto vedere.

**Passo 1 — i bersagli, e il profilo come variabile.** `up-03`, `down-03`, `reset-03`, `logs-03`,
`seed-03`, `smoke-03`, con `PROFILO=palco` predefinito. L'alternativa era due famiglie di bersagli —
`up-03-palco`, `up-03-completo` e così via — e si è scartata perché basta sbagliare un suffisso una
volta, `up-03-completo` seguito da `down-03-palco`, per fermare metà cluster. `up-03` è **un**
comando solo, non i due di `up-02`: la sentinella del Task 5 rende onesto `--wait`, e quando torna
i due shard sono registrati e `lab.ordini` è distribuita e piena.

Poi la scelta è stata provata, e da sola non bastava. `down` agisce **solo sui servizi dei profili
attivi**: spegnere in `palco` uno stack acceso in `completo` toglie undici container, ne lascia
sette accesi, non riesce a rimuovere la rete e **esce zero**. Nessun errore. `down` senza
`--profile` si comporta allo stesso modo. La correzione è `--profile "*"` su `down`, `reset` e
`logs` — la forma documentata per dire «tutti» ([S-068](Sources.md#s-068)) — mentre `up` e `seed`
tengono il profilo scelto: [ADR-0066](Decision.md#adr-0066), misure in
[V-059](Sources.md#v-059).

**Passo 2 — un ramo in più, non una riscrittura.** Il caso `03` di `reset-demo.sh` è **+128 righe,
−2**, e le due righe tolte sono il commento di testa riscritto. Le funzioni condivise, i tempi di
attesa e il verdetto finale restano gli stessi per tutti e tre gli stack, che era la promessa scritta
nel file quando esisteva solo il caso `01`. Tre differenze dal caso `02`, e nessuna cambia la forma:
i container da rialzare dipendono dal profilo; non si aspetta un primario preferito ma che i due
shard risultino registrati; e il verdetto sui dati non è solo l'impronta, è anche che i documenti
stiano su **entrambi** gli shard. Provato su un cluster rotto apposta in tre punti — collezioni di
scarto, balancer spento, un container fermo — e non su uno sano, che è la nota di metodo 106.

**Passo 3 — niente da fare, e non è una svista.** Il piano chiedeva di aggiungere «le sette porte
nuove» a `preflight.sh`. Sono undici, non sette, e ci sono **già**: `git log -S` le data al commit
`7809f7e` del **2026-08-25**, cioè a `feature/00`, quando gli stack 02 e 03 non esistevano. L'elenco
delle quindici porte del lab è stato scritto in una volta sola guardando la mappa del design §5.2, e
questo passo è l'ultimo pezzo di quella previsione che si avvera. Il file non è stato toccato.

Resta però un debito, ed è il verso opposto: **niente lega l'elenco di `preflight.sh` alle porte
pubblicate dai file Compose.** Oggi coincidono perché qualcuno le ha copiate bene; se domani una
porta cambiasse, `preflight` continuerebbe a controllare quella vecchia senza dirlo. Segnato per il
Task 9.

**Passo 4 — le misure.** `make preflight` **8 · 1 · 0** due volte a stack fermi e due volte con lo
stack 03 acceso, dove riporta «4 già in uso da container del lab in esecuzione», che è il caso che
sa distinguere. `make up-03` uscita 0 in **24 s**, `make smoke-03` **62 · 0**, `make seed-03`
ricarica a 9860 / 10140 su quattro chunk, `make reset-demo-03` ripara il disastro a tre guasti e
chiude a 0 con impronta `20000 50083417.93 60278`.

---

**E poi il guasto.** Provando `up-03` su volumi già esistenti — cioè spegnendo e riaccendendo, che è
la sequenza più ordinaria che ci sia — il secondo avvio falliva:

```
shard già registrati: nessuno
ERRORE: sh.addShard(«shard2rs/shard2a:27017») ha risposto ok=0
Messaggio: can't add shard 'shard2rs/shard2a:27017' because a local database 'lab' exists in
another shard1rs
```

Il messaggio accusa la persona sbagliata. La riga che spiega tutto è la prima: **«shard già
registrati: nessuno»**, su un cluster che al giro prima ne aveva due. I config server perdevano
tutto a ogni spegnimento mentre gli shard conservavano i loro dati. Contato: `dati-cfg1` e
`dati-cfg2` **zero file**, `dati-shard1a` **ottantatré**.

La causa sono due fatti che si sommano, e nessuno dei due è un errore. L'entrypoint dell'immagine,
quando trova `--configsvr`, porta il dbpath predefinito a `/data/configdb`; e l'immagine dichiara
`VOLUME` su **entrambe** le cartelle dei dati, quindi Compose soddisfa quella non montata con un
volume **anonimo**, che `down` abbandona e che il `up` dopo rifà vuoto. I config server montavano
`dati-cfgN` su `/data/db` — il posto giusto per ogni altro mongod — e scrivevano altrove.

La riparazione è `--dbpath /data/db` dichiarato sui tre config server, più **due guardie** che
avrebbero dovuto prenderlo: una regola statica in `check_stack.py` che confronta il dbpath vero con
la destinazione del volume, e il controllo dello smoke che smette di accontentarsi dell'esistenza
del volume nominato. Entrambe provate rompendole. [ADR-0067](Decision.md#adr-0067),
[V-060](Sources.md#v-060).

Il ciclo adesso regge: `reset-03` 4 s, `up-03` 25 s con `dati-cfg1` a **99 file**, `down-03` 7 s,
`up-03` di nuovo **22 s** e a posto. Il ramo idempotente di `add-shard`, scritto al Task 4, è stato
**eseguito oggi per la prima volta**: prima di questa correzione i metadati non arrivavano mai al
secondo giro, quindi quel ramo era coperto dai test e irraggiungibile nella realtà.

**Scostamento dal piano, dichiarato.** Il Task 7 nominava tre file e ne ha toccati sei:
`compose.yaml` è del Task 3, `check_stack.py` del Task 5, `smoke-sharded.sh` del Task 6. Non è stato
rinviato al Task 9 perché non è un debito ma un guasto, e perché colpisce la sequenza che al talk
capita per prima — spegnere fra una parte e l'altra e riaccendere. Aggiunto anche un settimo
bersaglio non previsto, `reset-demo-03`, per non lasciare il caso `03` di `reset-demo.sh`
raggiungibile solo scrivendo il percorso dello script a mano.

**Verificato:** `make docs-check` verde, `make tools-test` **131 passed** (sei test nuovi),
`make stack-check` «Stack conformi: 3», `make smoke-03` 62 · 0.

110. **Il modo in cui pulisci fra una prova e l'altra decide quale classe di difetti non troverai
     mai.** Tutte le prove dei Task 3-6 finivano con `down -v`, che cancella i volumi e riparte da
     zero — abitudine giusta, perché tiene le misure confrontabili e la macchina pulita. Il prezzo
     è che una perdita di dati allo spegnimento è **strutturalmente invisibile** a chi riparte
     sempre da zero: non è che il controllo era debole, è che lo stato in cui il difetto si
     manifesta non veniva mai raggiunto. Quattro giorni di prove verdi su uno stack che non
     sopravviveva a un `down`. La regola che ne ricavo non è «non pulire», è che ogni procedura di
     prova ha un **punto cieco che coincide con ciò che la procedura cancella**, e che quel punto
     cieco va nominato per iscritto quando la si scrive. Qui il punto cieco erano i volumi, e la
     prova mancante era la più corta possibile: accendere, spegnere **senza** `-v`, riaccendere.

111. **Se verifichi con lo stesso parametro con cui hai agito, la verifica non è indipendente:
     conferma l'errore invece di scoprirlo.** Spegnendo con `--profile palco` uno stack acceso in
     `completo` restano sette container in piedi — ma `docker compose --profile palco ps`, cioè il
     comando che verrebbe naturale usare per controllare, risponde «nessun container». Non mente:
     guarda lo stesso insieme sbagliato che ha guardato `down`, e quell'insieme è davvero vuoto. Il
     parametro che ha causato l'errore è lo stesso che lo nasconde, e più il parametro è implicito
     — un profilo, un contesto, un namespace, una variabile d'ambiente ereditata — meno ci si pensa.
     La contromisura è banale e va ricordata proprio perché è banale: la verifica si fa con lo
     strumento **più stupido e meno parametrizzato** che esiste. Qui era `docker ps` senza filtri,
     ed è l'unico che diceva la verità.

## 2026-09-02 — Coda del Task 7: `alpine` resta fuori dalle immagini del lab

Chiudendo il Task 7 avevo segnalato che l'indagine sul guasto dei config server aveva tirato in
cache `alpine`, e il PO ha chiesto la cosa giusta: a che cosa è servita, per decidere se pinnarla
o buttarla. Le tre risposte, misurate invece che ricordate.

**A che cosa è servita.** A una sola cosa, sempre nella stessa forma: contare i file dentro un
volume nominato senza accendere un mongod — `docker run --rm -v <volume>:/v alpine sh -c 'ls -1 /v
| wc -l'`. È così che sono stati presi i numeri che hanno inchiodato il difetto: `dati-cfg1` a zero
file contro `dati-shard1a` a ottantatré, e poi `dati-cfg1` a novantanove dopo la riparazione
([V-060](Sources.md#v-060)).

**Se il repository la usa.** No: `grep -rn alpine` fuori da `docs/` non trova **niente**. Non è nei
file Compose, non nel `Makefile`, non negli script, non in `tools/images.env`. Nei documenti compare
solo dentro le verifiche empiriche, cioè come racconto di misure già prese, mai come qualcosa che il
lab esegue.

**Se serve pinnarla.** No, e non perché sia poco importante contare i file in un volume — quello
serve eccome — ma perché **l'immagine pinnata lo fa già**: `docker run --rm --entrypoint sh -v
<volume>:/v "$MONGO_IMAGE" -c 'ls -1 /v | wc -l'` risponde uguale, provato oggi. Pinnare `alpine`
vorrebbe dire allargare il fardello offline ([ADR-0009](Decision.md#adr-0009)) e aggiungere un
digest da mantenere per una capacità che il lab ha già. La riserva è scritta in coda a V-060, così
chi rifà quella misura scollegato trova subito la forma che funziona.

Un dettaglio che vale la pena aver guardato invece di darlo per scontato: `alpine:latest` e
`alpine:3` su questa macchina sono lo **stesso** identificatore d'immagine, `28bd5fe8b56d`.
`alpine:3` c'era già il 1º settembre — «dalla cache locale», dice l'ambiente di
[V-046](Sources.md#v-046) — quindi il `docker run alpine` del Task 7 non ha scaricato un byte: ha
attaccato una seconda etichetta alla stessa immagine. Tolta l'etichetta di troppo con
`docker image rm alpine:latest`, che risponde `Untagged` e non `Deleted`, il disco è esattamente
com'era.

---

## 2026-09-02 — Task 8: la pagina dello sharded cluster, scritta dopo aver visto sbagliare la chiave

L'[indice](README.md) prometteva `docs/02-architetture/sharded-cluster.md` per nome dalla
`feature/00`, e il design le assegna il Blocco 3: otto minuti, una slide, `sh.status()` a schermo.
Il materiale c'era, sparso in sette ADR, sei verifiche e un blocco di commento dentro
`30-dati-demo.js`. Raccoglierlo sarebbe bastato per una pagina onesta. Non è bastato per due
sezioni.

**Il balancer era un verbo senza misure.** Il repository lo nominava in tre punti e non sapeva se in
questa demo lavorasse. **La shard key sbagliata era una citazione** — tripla, ottima, e mai vista
accadere qui dentro: esattamente ciò che [ADR-0052](Decision.md#adr-0052) chiama una previsione, non
una trappola. Prima di scrivere la pagina sono andato a misurare tutte e due
([V-061](Sources.md#v-061)), e per fondarla su testo verificabile ho aggiunto tre pagine del manuale
7.0 come fonti: [S-069](Sources.md#s-069) l'ingresso allo sharding, [S-070](Sources.md#s-070) il
balancer, [S-071](Sources.md#s-071) le scritture in lotto.

**Il balancer non entra mai in scena.** `lab.ordini` pesa 2 437 499 byte in tutto, la differenza fra
i due shard è di **34 409 byte**, e la soglia perché una migrazione parta è tre volte la dimensione
di range configurata, cioè **384 MB** con i 128 predefiniti: un rapporto di uno a undicimila e
settecento. Il registro del cluster conferma: sei eventi in tutto, **zero** `moveChunk` e zero
`moveRange`. I quattro chunk della demo sono opera di `shardCollection()` su collezione vuota — «by
default, the operation creates 2 chunks per shard» — e i loro confini sono lo spazio a 64 bit tagliato
in quattro parti uguali, da `MinKey` a −2⁶²+2 a 0 a +2⁶²−2 a `MaxKey`. Non è bilanciamento: è
geometria decisa prima che esistesse un documento. Dire «e qui il balancer ridistribuisce» sarebbe
stata una didascalia falsa su una fotografia vera.

**La chiave sbagliata, provata.** Stessa forma di documento, stessi `_id` interi crescenti, cambiata
solo la chiave: `{_id: 1}` invece di `{_id: "hashed"}`. Su collezione vuota, **un** chunk su un
solo shard; dopo ventimila inserimenti, **20 000 documenti su uno shard e l'altro che non compare
nemmeno nella distribuzione**, ancora un chunk, zero migrazioni. La controprova con la chiave hashed
sulla stessa collezione: 9860 e 10140, gli stessi due numeri di [V-058](Sources.md#v-058).

E poi il pezzo che non cercavo. Su quella collezione cento-a-zero,
`sh.balancerCollectionStatus()` risponde **`balancerCompliant: true`**. Il cluster considera
bilanciata una distribuzione in cui uno dei due shard non sta facendo niente — e ha ragione, perché
la differenza è 1,2 MB contro una soglia di 384. L'errore irreversibile di questa architettura non
ha sintomo, e lo strumento che dovrebbe accorgersene conferma che va tutto bene. Quella riga è
diventata il centro della pagina e la prima delle due citazioni per le slide.

**La terza cosa, che nessuno cercava.** Misurando i tempi di caricamento delle due chiavi ho ottenuto
9718 ms per la hashed contro poche centinaia per la ranged: in contraddizione con
[V-058](Sources.md#v-058), che per gli stessi ventimila documenti aveva misurato 1202 ms. Prima di
pubblicare un numero che smentiva il repository ho alternato l'ordine su tre giri — hashed
9910/8180/10027, ranged 704/192/432 — e il divario è rimasto: non era rumore né effetto della cache.
La causa vera l'ha data il codice del lab, non il ragionamento: `30-dati-demo.js` alla riga 296 scrive
`ordered: false`, e le mie prove usavano il predefinito. Un esperimento due-per-due l'ha confermato:
hashed + `ordered: true` costa 11 328 e 9 393 ms, hashed + `ordered: false` 336 e 408 ms, la chiave
monotona costa uguale in tutte e due le forme. Il costo **non** è la chiave hashed: è la chiave
hashed insieme al lotto ordinato, perché «`mongos` attempts to send the writes to multiple shards
simultaneously» e con l'ordine da mantenere non può ([S-071](Sources.md#s-071)). È il difetto più
insidioso dei tre, perché colpisce chi ha scelto **bene** e non ha toccato il codice di caricamento
che funzionava sul replica set. Il lab scriveva la riga giusta dal primo giorno per allineamento con
gli altri due stack; da oggi sa perché.

Il valore fuori scala — 1947 ms per ranged + `ordered: false`, contro 192, 248 e 340 degli altri tre
casi ranged — è rimasto nella tabella con la sua riserva. Toglierlo sarebbe scegliere i dati.

**La forma della pagina** è fissata in [ADR-0068](Decision.md#adr-0068): apre sull'irreversibilità e
non sulla topologia, perché è l'unica informazione che cambia il *momento* in cui si decide; scrive
«quando non serve» dichiarando che il manuale non lo dice — la sezione «Considerations Before
Sharding» non contiene nessuna soglia, nessuna dimensione minima, nessuno sconsiglio circostanziato
([S-069](Sources.md#s-069), «cosa non afferma»), quindi il giudizio è di chi scrive e va attribuito a
chi scrive; e non ripete il file Compose riga per riga come fa la pagina del replica set, perché qui
il file non è il soggetto — restano solo i due punti che si capiscono guardandolo, la catena dei sei
anelli e il difetto del dbpath dei config server.

Tutte le prove hanno girato in un database `prova` buttato via alla fine. `lab.ordini` è stata
ricontata a ogni passaggio — 20 000, sempre — e `make smoke-03` chiude a 62 controlli e 0
fallimenti.

Chiuso il Task 8, l'indice non ha più promesse aperte fra le pagine di architettura: le tre stanno
tutte nel repository.

**Note di metodo.**

112. **Se una misura contraddice quello che il repository ha già scritto, la contraddizione è
     l'informazione — ma solo dopo aver escluso te stesso.** Il primo istinto davanti a 9718 ms
     contro 1202 è ripetere finché non torna, il secondo è pubblicare il numero nuovo dicendo «sul
     mio portatile fa così». Nessuno dei due serve. Quello che è servito è stato tenere la
     contraddizione aperta e cercare **che cosa avevo fatto di diverso**, che si scopre leggendo il
     codice del lab e non rieseguendo il proprio. La differenza era un parametro che non avevo
     nemmeno scritto, perché era il predefinito. Una misura che contraddice il registro è quasi
     sempre una misura di un'altra cosa: trovare quale altra cosa vale più della misura.
113. **Una trappola descritta bene resta una previsione: diventa una trappola quando la vedi
     scattare.** La chiave monotona era spiegata in questo repository con tre citazioni e un
     paragrafo di commento nel seed, e sembrava materiale finito. Provarla ha aggiunto la sola cosa
     che le mancava — che l'errore **non ha sintomo**, e che lo strumento di diagnosi lo dichiara
     conforme. Quella riga non sta in nessuna delle tre citazioni: si vede solo eseguendo. Vale come
     regola di dosaggio dello sforzo, perché provare costa ore: si prova ciò che il talk deve
     **mostrare**, e si cita ciò che il talk deve solo dire.

---

## 2026-09-02 — Punto di ripresa: chiuso il Task 8, si riparte dal Task 9

Sessione sospesa per limite di contesto, non per un ostacolo tecnico. Il branch
`feature/03-stack-sharded` è allineato con l'origine.

**Deciso.** La forma della pagina dello sharded cluster ([ADR-0068](Decision.md#adr-0068)): si apre
sull'irreversibilità, si dichiara che il manuale non dice quando *non* servirebbe, la chiave
sbagliata si mostra con i numeri invece di descriverla, e il file Compose non si ripete riga per
riga. Deciso anche che `alpine` resta fuori dalle immagini pinnate: la misura dei volumi si rifà con
l'immagine già pinnata scavalcando l'entrypoint, e la riserva è scritta in coda a
[V-060](Sources.md#v-060).

**Misurato.** [V-061](Sources.md#v-061): il balancer in questa demo non entra mai in scena — 34 409
byte di differenza contro una soglia di 384 MB, zero migrazioni su sei eventi; la chiave `{_id: 1}`
mette 20 000 documenti su un solo shard e il cluster risponde `balancerCompliant: true`; con chiave
hashed un `insertMany` ordinato costa fra venti e trenta volte uno non ordinato, mentre con chiave
monotona le due forme costano uguale. `make docs-check` verde, `make smoke-03` 62 controlli e 0
errori, `lab.ordini` a 20 000 documenti. Lo stack è stato spento con `make down-03`, che conserva i
volumi.

**Prossimo passo.** **Task 9** del [piano](00-progetto/2026-09-01-piano-feature-03-stack-sharded.md):
i debiti segnati si chiudono eseguendo, come vuole [ADR-0049](Decision.md#adr-0049). I due candidati
già annotati sono che niente lega le `PORTE` di `preflight.sh` ai file Compose, e che niente lega il
`Makefile` ai profili dichiarati nel Compose; resta da riguardare anche il debito di
[ADR-0062](Decision.md#adr-0062) sul doppio comando dello stack 02. Restano poi il Task 10 (la riserva del
Blocco 3) e il Task 11, che chiude il branch **con la pull request** e non con
`git flow feature finish`.

Stato: decisioni fino a **ADR-0068**, verifiche fino a **V-061**, fonti fino a **S-071**, note di
metodo fino alla **113**. Task 1–8 su 11 chiusi.

---

## 2026-09-02 — `feature/03`, Task 9: i debiti marcati, saldati eseguendo

Il Task 9 non aggiunge funzioni: toglie marcature. Quattro pagine dichiaravano di non aver provato
qualcosa, e [ADR-0049](Decision.md#adr-0049) dice come si chiude un debito così — **eseguendolo**.
La prima volta che quella regola è stata applicata, l'esecuzione ha trovato due righe sbagliate. È
successo di nuovo, quattro volte, e una prima ancora di cominciare.

**Una divergenza da dichiarare, prima di tutto il resto.** Il punto di ripresa del Task 8 nominava
come candidati del Task 9 due debiti diversi — che niente lega le `PORTE` di `preflight.sh` ai file
Compose, e che niente lega il `Makefile` ai profili dichiarati nel Compose — e la ripresa li ha
ripetuti. Il [piano](00-progetto/2026-09-01-piano-feature-03-stack-sharded.md) però intesta al
Task 9 sei passi che sono altri: la §3.3 della guida a `mongosh`, gli utenti locali a uno shard,
`--oplog` sullo sharded cluster, le trappole dei config server e del bilanciamento, la riga 55 del
`README`, il commit. Ha vinto il piano, che è il documento approvato; i due debiti degli strumenti
restano annotati e senza sede, insieme a quello di [ADR-0062](Decision.md#adr-0062) sul doppio
comando dello stack 02.

**La riga sbagliata trovata prima del primo passo.** Riaccendendo lo stack per lavorare, `sh.status()`
mostrava **due** chunk dove [V-061](Sources.md#v-061) ne aveva contati quattro poche ore prima, e su
quel numero era costruita la sezione 4 di [`sharded-cluster.md`](02-architetture/sharded-cluster.md).
Non era un errore di misura: era l'**AutoMerger**, che dalla 7.0 fonde i chunk contigui dello stesso
shard e che parte la prima volta che il balancer viene abilitato — cioè, in uno stack Compose, a
ogni `up`. Il registro del cluster ha data, ora e nodo: due `merge` alle `12:34:16.530Z` e alle
`12:34:31.450Z`, `server cfg1:27017`, 3,8 secondi dopo l'avvio del config server e sei secondi prima
che il router esistesse ([V-062](Sources.md#v-062)). La frase «il balancer non entra mai in scena»
era falsa e si corregge: [ADR-0069](Decision.md#adr-0069). Ne è seguita anche una modifica di
codice, l'unica del task — `tools/smoke-sharded.sh` verificava un'uguaglianza a quattro, e adesso
verifica un pavimento.

**Passo 1 — la §3.3 della guida, eseguita.** Era marcata non eseguita per intero, e documentava
l'errore **di un'altra architettura**: `sh.status()` su un nodo di shard non risponde
`MongoshInvalidInputError: This db does not have sharding enabled` — quello è lo standalone — ma un
avviso `[SHAPI-10003]` seguito da `MongoServerError: not authorized on config to execute command`.
Dieci comandi eseguiti con la colonna «eseguito» accanto, i due errori di `addShard`, la differenza
fra `getBalancerState()` e `isBalancerRunning()`, e quattro avvertenze — fra cui che
`sh.stopBalancer()` spegne anche l'AutoMerger, e che il codice di uscita di `mongosh` non è l'esito
([ADR-0036](Decision.md#adr-0036)). Restano marcati `sh.disableBalancing()` e
`sh.enableBalancing()` ([V-063](Sources.md#v-063)).

**Passo 2 — gli utenti locali a uno shard, provati.** È il passo che ha reso di più.
[S-074](Sources.md#s-074) afferma che su un cluster «the localhost exception applies to each shard
individually», e la misura lo conferma e lo estende. Gli utenti del cluster vivono sui config
server: gli shard sono replica set **senza utenti**, quindi con l'eccezione aperta, e da dentro il
container di uno shard si crea un `root` senza presentare niente. Le porte pubblicate sull'host
**non** aprono l'eccezione, perché a `mongod` la connessione arriva dal gateway di Docker
(`192.168.65.1`, letto con `whatsmyuri`); un container che condivide il *network namespace* dello
shard sì, e non gli serve il keyfile. Tre comportamenti che il manuale non scrive: il primo utente è
rifiutato se chiede ruoli su un database diverso da `admin` ma **accettato** con `roles: []`, il che
spende l'eccezione e chiude fuori chi l'ha usata; l'eccezione **non si riapre** cancellando l'ultimo
utente, perché è un fermo per processo che solo il riavvio rilascia; e il loopback serve davvero, il
che chiude per misura una riserva aperta in [S-006](Sources.md#s-006) dal 2026-08-25 — restando
aperta quella bibliografica, perché nessuna fonte primaria trovata lo scrive
([V-064](Sources.md#v-064)).

Da questa misura **non** è seguita una modifica allo stack. Il dovere che la documentazione
prescrive — «you must still prevent unauthorized access to the individual shards» — ha due rimedi, e
tutti e due sono decisioni di sicurezza: creare un amministratore sul primario di ogni shard, oppure
`enableLocalhostAuthBypass=0`, che applicato prima dell'inizializzazione impedisce `rs.initiate()` e
lascia lo stack spento. Sono scritte nella pagina come debito aperto e indirizzato, e la scelta
spetta a chi risponde del laboratorio.

**Passo 3 — `--oplog` sullo sharded cluster.** Il divieto è confermato — `can't use --oplog option
when dumping from a mongos` — ma ha una seconda faccia peggiore: con `--db` insieme, la risposta
diventa `bad option: --oplog mode only supported on full dumps`, che non nomina più il router e
manda a togliere l'opzione sbagliata. Il dump attraverso il `mongos` funziona ed emette sempre
l'avviso sul `readPreference` non primario, **anche passando `--readPreference=primary`**. Uno shard
singolo `--oplog` lo accetta, perché è un replica set. E il restore riporta ventimila documenti con
zero errori, ricrea l'indice `_id_hashed`, e lascia la collezione **non distribuita**, tutta sul
primary shard: nessun segnale, e il controllo che verrebbe naturale fare — contare i documenti —
conferma che è tutto a posto ([V-065](Sources.md#v-065)).

**Passo 4 — tre trappole in coda, e le diciotto intatte.** Voce **19**, il config server che scrive
in `/data/configdb` mentre il volume nominato è su `/data/db`, e Compose ci mette un volume anonimo
che `down` abbandona ([V-060](Sources.md#v-060)); voce **20**, i chunk che da quattro diventano due
fra due accensioni ([V-062](Sources.md#v-062)); voce **21**, l'eccezione localhost aperta shard per
shard ([V-064](Sources.md#v-064)). Le prime due sono i nomi che [ADR-0033](Decision.md#adr-0033)
aveva scritto in anticipo; la terza entra per [ADR-0052](Decision.md#adr-0052).

**Passo 5 — il `README`.** La riga 55 passa a «nel repository»; la riga 57, che dice l'applicazione
Python in lavorazione, resta intatta perché è vera fino a `feature/04`. Con la tabella cambiata,
«i primi due stack» due righe sotto sarebbe diventato falso: è diventato «i tre stack». Quattro
righe dell'indice di [`docs/README.md`](README.md) sono state allineate per la stessa ragione, fra
cui quella che prometteva i comandi dello sharded cluster «ancora solo scritti».

**Che cosa resta non eseguito, e dichiarato tale** ([ADR-0037](Decision.md#adr-0037)): i due comandi
di bilanciamento della guida; i secondari degli shard, provati solo sui primari; il restore
preceduto da `sh.shardCollection()`, che è dedotto e non misurato; gli «extra steps» che
[S-060](Sources.md#s-060) attribuisce al backup di un cluster e non elenca da nessuna parte; il
backup dei config server.

Le prove distruttive hanno lasciato l'ambiente pulito, verificato con l'identità interna: **zero
utenti su entrambi gli shard**, `lab.ordini_ripristinata` cancellata, tutte le cartelle di dump
rimosse. `make docs-check` verde, `make tools-test` **131 passed**, `make stack-check` «Stack
conformi: 3», `make smoke-03` **62 controlli e 0 errori**, `lab.ordini` a 20 000 documenti.

**Note di metodo.**

114. **Quando il punto di ripresa e il piano nominano debiti diversi, vince il piano — e la
     divergenza si scrive.** Il punto di ripresa è un appunto scritto di corsa alla fine di una
     sessione; il piano è il documento approvato. Seguire l'appunto perché è quello che si è letto
     per ultimo significa lasciare che la fretta di ieri decida il lavoro di oggi. La cosa da non
     fare è la terza: accorgersi della differenza e non dirla, perché allora i due debiti che
     l'appunto nominava sparirebbero senza che nessuno li abbia né fatti né rinviati.

115. **Un controllo che verifica un'uguaglianza su un numero che il sistema può cambiare da solo ha
     una data di scadenza che nessuno ha scritto in calendario.** `chunk == 4` è passato per giorni
     ed è diventato rosso senza che nessuno toccasse niente. Il valore che regge non è il numero
     osservato ma il **pavimento** che la struttura impone — almeno un chunk per shard, perché un
     chunk non può stare a cavallo di due shard — con i valori noti riconosciuti per nome e non
     imposti. La differenza fra le due forme si vede solo il giorno in cui il sistema si muove, ed
     è il giorno peggiore per scoprirla.

116. **Provare un divieto vuol dire provare anche il modo sbagliato di incontrarlo.** Il messaggio
     che la documentazione lascia prevedere — «can't use `--oplog` when dumping from a mongos» — si
     ottiene solo se tutto il resto del comando è corretto. Chi sbaglia due cose ne vede riferita
     una sola, e non è quella che conta. Documentare il solo messaggio «giusto» sarebbe stato più
     ordinato e avrebbe lasciato il lettore a togliere `--db` per scoprire il resto da solo.

117. **Misurare una falla non autorizza a chiuderla.** Il passo chiedeva di *provare* che
     l'eccezione localhost fosse aperta su ogni shard; provato, la tentazione era di aggiungere
     l'amministratore per shard e togliersi il pensiero. Sarebbe stata una modifica alla sicurezza
     dello stack decisa da chi stava saldando un debito di documentazione, con un rimedio — il
     parametro a `0` — che se messo nel posto sbagliato impedisce allo stack di partire. La misura
     si pubblica, il rimedio si propone, la scelta appartiene a chi risponde del laboratorio.

118. **Un debito saldato che ne lascia scoperti cinque non è un task fallito: è un task che ha
     guardato più da vicino.** Prima dell'esecuzione il debito era uno e generico — «non provato».
     Dopo sono cinque, ciascuno con un confine netto e una ragione. Contare i debiti aperti come
     misura della salute di un repository premia chi non guarda.

Stato: decisioni fino a **ADR-0070**, verifiche fino a **V-065**, fonti fino a **S-074**, note di
metodo fino alla **118**. Task 1–9 su 11 chiusi; restano il **Task 10** (la riserva del Blocco 3) e
il **Task 11**, che chiude il branch **con la pull request**.

---

## 2026-09-02 — Prima del Task 10: l'amministratore per shard, e la porta che si chiude

Il Task 9 ha chiuso lasciando una decisione al Product Owner, come prescrive la nota di metodo 117:
la misura si pubblica, il rimedio si propone, la scelta appartiene a chi risponde del laboratorio.
[V-064](Sources.md#v-064) aveva misurato che ogni shard di questo stack è un replica set **senza
utenti**, quindi con l'eccezione localhost aperta per tutta la vita del processo, e che un container
qualunque che ne condivide il *network namespace* ci diventa `root` senza presentare niente.
[ADR-0070](Decision.md#adr-0070) aveva deciso di non decidere.

Il Product Owner ha deciso: **si crea l'amministratore per shard**, con l'eccezione localhost, per
questo laboratorio, e la documentazione deve dire ad alta voce che la forma automatica non va
riprodotta in produzione, indicando la procedura canonica. È
[ADR-0071](Decision.md#adr-0071).

**Prima di scrivere una riga, cercare la procedura — e trovarla ha spostato l'avvertenza.** Il
tutorial di autenticazione a keyfile su sharded cluster ([S-075](Sources.md#s-075)) ha un passo 4
intitolato «Create the shard-local user administrator», e lo esegue **usando proprio l'eccezione
localhost**: ci si collega al primario dello shard e si crea lì il primo utente, perché su un nodo
che pretende autenticazione e non ha ancora nessuno da autenticare non c'è altra via. L'eccezione,
che era il problema, è anche l'unico strumento del rimedio. Le deviazioni di questo laboratorio sono
dunque altre tre, e sono quelle su cui puntare il dito: una **sola password** per il cluster e per i
due shard dove il manuale ne vuole una per shard; **letta da un file** da uno script non presidiato
dove il manuale vuole `passwordPrompt()`; il ruolo **`root`** invece del `userAdminAnyDatabase` del
passo 4, e senza il secondo utente `clusterAdmin` del passo 5.

**Dove va messo il `createUser`, e perché non dove sarebbe stato comodo.** Nel primario di ogni
shard, dentro `11-shard-initiate.js`, dopo l'attesa dell'elezione e **prima** che `add-shard`
registri gli shard. L'ordine è del manuale e la ragione è scritta lì — «Executing them now ensures
that there are users available for each shard to perform shard-level maintenance» — perché farlo
dopo lascerebbe una finestra in cui lo shard è in piedi, non ha utenti, e ha la porta aperta.
L'attesa del primario, che c'era già per `sh.addShard()`, adempie ora anche a «You must be connected
to the primary to create users»: un `createUser` su un nodo non ancora eletto risponde
`NotWritablePrimary`. I due `catch` che trattano `Unauthorized` e «already exists» come successo
sono la stessa scelta di `10-cfg-initiate.js`: un one-shot che fallisce al secondo `up` è un
`make up-03` che fallisce davanti al pubblico.

**Il ruolo si è scelto misurando, non ragionando.** La scelta ovvia era `userAdminAnyDatabase`,
perché è quello che prescrive il manuale ed è il minimo. Provato ([V-066](Sources.md#v-066), quinto
esito): non legge `lab.ordini`, si concede `root` **da solo in un comando**, e subito dopo la legge.
Fra i due ruoli, su quel nodo, non c'è una barriera di privilegio — c'è un comando in più. Con una
password condivisa il ruolo minimo avrebbe avuto l'aspetto della sicurezza senza la sostanza, e in
cambio avrebbe tolto alla demo l'unica cosa per cui [ADR-0026](Decision.md#adr-0026) prevede questi
utenti: ispezionare un singolo shard. `root`, dichiarato come deviazione.

**Che l'utente sia davvero locale non si dimostra autenticandosi.** La password è la stessa del
cluster, quindi un login riuscito non prova niente: proverebbe solo che la password funziona. Due
prove indirette lo hanno stabilito. La prima è **quello che vede**: 9 860 documenti di `lab.ordini`
sullo shard, contro i 20 000 che si contano dal router. La seconda è un utente con **un nome
diverso**, `solo-shard1`, creato apposta sul solo `shard1a`: accettato da `shard1a`, rifiutato dal
`mongos` con «Authentication failed». È il «you cannot connect to the `mongos` with shard-local
users» del manuale, in due righe. L'utente di prova è stato cancellato subito dopo, e la cancellazione
verificata.

**Quello che si guadagna, e quello che si perde.** Si guadagna che l'attacco di V-064 non passa più:
stesso container nel namespace dello shard, stesso `127.0.0.1` visto da `mongod`, nessun keyfile, e
la risposta è `Unauthorized`. Si perde che le porte pubblicate degli shard — 27141 e 27151 nel
profilo `palco` — adesso **riconoscono una credenziale**, quella del cluster, dove prima non c'era
niente da presentare loro. L'eccezione localhost non c'entra, quella via non l'ha mai aperta: cambia
che esiste un utente. Sul lab non sposta nulla ([ADR-0005](Decision.md#adr-0005)); su una macchina
raggiungibile sarebbe la prima cosa da guardare. Le due cose sono scritte insieme ovunque compaiano.

**Lo smoke test perde un'invariante e ne guadagna tre.** Il controllo che verificava che le
credenziali del cluster **non** aprissero uno shard ([V-058](Sources.md#v-058)) era vero e adesso è
falso per costruzione: `make smoke-03` è fallito al primo giro, ed è fallito bene, perché è così che
un repository chiede di aggiornare un'invariante. Al suo posto tre controlli: che l'amministratore
locale esista e sia locale (un utente solo, e una fetta della collezione, non i ventimila del
cluster) e che l'eccezione sia chiusa **su tutti e due** gli shard, perché è una condizione di
processo e un nodo riavviato senza il suo init la riaprirebbe da solo. Da 62 a **64** controlli.

**Che cosa è cambiato.** Nello stack: `docker/03-sharded/init/11-shard-initiate.js` (crea l'utente e
porta in testa l'avvertenza), `docker/03-sharded/compose.yaml` (passa le due credenziali ai due init,
e il commento che diceva «Nessun `createUser` qui» dice adesso il contrario e perché),
`docker/03-sharded/.env.example`, `tools/smoke-sharded.sh`. In documentazione: la nuova **§4.2** di
[`sicurezza-keyfile-x509.md`](03-amministrazione/sicurezza-keyfile-x509.md) con l'avvertenza in
evidenza, la procedura canonica citata passo per passo e la tabella delle tre differenze; la §4.1 che
resta com'era con davanti la data oltre la quale non si riproduce; la trappola **21** di
[`trappole-mongodb-in-docker.md`](02-architetture/trappole-mongodb-in-docker.md), che cambia esito;
due righe dell'indice; una citazione nuova e il seguito di una vecchia in
[`citazioni-riportare-slide.md`](citazioni-riportare-slide.md). E le fonti: [S-075](Sources.md#s-075)
con la verifica che l'accompagna, [V-066](Sources.md#v-066).

**I tre debiti degli strumenti: sede assegnata, ed è il Task 11.** Restavano annotati e senza sede —
niente lega le `PORTE` di `preflight.sh` ai file Compose, niente lega il `Makefile` ai profili
dichiarati nel Compose, e [ADR-0062](Decision.md#adr-0062) ne ha lasciato uno verso lo stack 02, dove
`up-02` esegue ancora i due comandi che la sentinella dello stack 03 ha reso inutili. Vanno chiusi
**eseguendo** ([ADR-0049](Decision.md#adr-0049)) nel **Task 11**, prima dei quattro controlli e della
pull request, e non nel Task 10, per tre ragioni. Sono **un solo genere di debito** — gli strumenti
del repository che si scollano dai file Compose — e un genere solo merita una sede sola e un giro di
verifica solo. Il Task 10 **registra terminali**: cambiare `preflight.sh` o il `Makefile` dopo aver
registrato `make up-03` significa avere registrazioni che mostrano un output che gli strumenti non
producono più, e [ADR-0055](Decision.md#adr-0055) chiede di riprodurre ogni registrazione per intero
prima di dichiararla buona. Il terzo debito, infine, tocca lo **stack 02**: per chiuderlo eseguendo
serve accendere quello stack, che è un ambiente diverso da quello del Task 10.

**Misurato.** `make smoke-03` **64 controlli e 0 errori** (era 62), `make stack-check` «Stack
conformi: 3», `make docs-check` verde, `make tools-test` **131 passed**, `lab.ordini` 20 000 documenti
dal router e 9 860 su `shard1a`. Le prove distruttive hanno lasciato l'ambiente pulito, verificato
con le credenziali: **un solo utente `admin` per shard**. Il secondo `up` è idempotente: i due init
rispondono «già presente» ed escono `0`. Lo stack è rimasto acceso nel profilo `palco`.

**Note di metodo.**

119. **Prima di dichiarare una deviazione, cercare la procedura: può darsi che la scorciatoia che si
     sta per confessare sia il manuale.** L'eccezione localhost sembrava evidentemente il trucco del
     lab, e l'avvertenza stava per finire lì sopra. Il manuale la usa. Puntare il dito nel posto
     sbagliato non è un errore innocuo: consuma l'attenzione di chi legge dove non serve, e la toglie
     dai tre punti — password sola, letta da un file, ruolo `root` — dove serviva davvero.

120. **Un ruolo minimo che può promuoversi non è una barriera, ed è una cosa che si misura in tre
     righe invece di dedurla.** «Amministra gli utenti ma non legge i dati» descrive due privilegi e
     nasconde che il primo contiene il secondo. La difesa vera non era il ruolo: era chi conosce la
     password. Scegliere il ruolo minimo per abitudine avrebbe prodotto sicurezza apparente e una
     demo mutilata.

121. **Un rimedio si documenta con la porta che apre, non solo con quella che chiude.** Creare
     l'amministratore per shard chiude l'eccezione localhost e nello stesso momento rende
     autenticabile una porta pubblicata che prima non accettava nulla, perché non c'era nessun utente
     da presentarle. Scrivere solo il guadagno avrebbe reso il documento più convincente e meno
     vero, e avrebbe lasciato la sorpresa a chi un giorno esporrà quelle porte.

122. **Uno smoke test che diventa rosso per una decisione, e non per un guasto, è il momento in cui
     un'invariante va riscritta — mai silenziata.** Il controllo diceva il vero fino al commit prima.
     La tentazione è cancellarlo, perché «adesso è normale che passi»: e così sparisce la sorveglianza
     insieme all'invariante vecchia. Al suo posto vanno le invarianti nuove, che qui erano tre e non
     una, e una di esse — l'eccezione chiusa **su entrambi** gli shard — controlla proprio la cosa che
     la decisione ha appena messo in gioco.

Stato: decisioni fino a **ADR-0071**, verifiche fino a **V-066**, fonti fino a **S-075**, note di
metodo fino alla **122**. Task 1–9 su 11 chiusi; il **Task 10** (la riserva del Blocco 3) comincia
adesso, e il **Task 11** chiude il branch **con la pull request** e con i tre debiti degli strumenti.

---

## 2026-09-02 — Il seguito di ADR-0071: quattro punti diventati falsi, e un errore che ne nascondeva un altro

Il Task 10 è cominciato da una lettura, non da una registrazione. Per aggiungere a
`tools/demo-sharded.sh` la scena del guasto serviva sapere come `tools/reset-demo.sh` rialza i nodi
che ha buttato giù, e tre righe sopra la funzione giusta c'era un commento che spiegava perché tutto
passa dal router: «le credenziali del cluster su uno shard danno *Authentication failed*». Da
[ADR-0071](Decision.md#adr-0071), cioè dal commit precedente, non è più vero.

Cercare il testo di quel messaggio nel repository ne ha trovati altri tre: un commento in
`docker/03-sharded/init/10-cfg-initiate.js`, un passaggio in §2.2 e uno in §6.1 di
`docs/02-architetture/sharded-cluster.md`, e il blocco `console` che apre la §3.3 di
`docs/04-mongosh/guida-mongosh.md`. Quattro affermazioni vere quando sono state scritte, rese false
da una modifica nostra, e vissute così per un commit intero.

**Rimisurare ha dato più di quello che serviva.** Le due risposte attese sono arrivate — senza
credenziali lo shard adesso dice `Command find requires authentication` invece di `not authorized on
config`, con le credenziali entra e conta 9 860 documenti — e dietro ne sono comparse altre quattro,
che nessuno stava cercando. La più importante è la peggiore: `sh.getBalancerState()` dato a uno
shard **risponde `true`**. Prima rispondeva `Unauthorized`. Non spedisce nessun comando: legge
`config.settings`, che sullo shard non esiste, e dal vuoto conclude che nessuno ha fermato il
bilanciatore. Finché la lettura veniva rifiutata, l'errore faceva da segnale d'indirizzo sbagliato;
adesso il segnale non c'è e al suo posto c'è una risposta plausibile.

Lo stesso meccanismo, all'incontrario, spiega una frase che questa guida aveva corretto in buona
fede. La §3.3 diceva che `MongoshInvalidInputError: This db does not have sharding enabled` è
l'errore di un'istanza singola e che su uno shard vero la risposta è un'altra. Autenticati, su uno
shard vero, la risposta è **esattamente quella frase**: il documento `config.version` sullo shard è
`null`, e finché la lettura era negata `mongosh` non arrivava a scoprirlo. Il primo errore ne
nascondeva un secondo — la stessa forma della trappola di `--oplog` misurata ieri
([V-065](Sources.md#v-065)), e stavolta il permesso mancante non c'era per un difetto ma per una
configurazione insicura che abbiamo appena tolto.

Le sei misure stanno in [V-067](Sources.md#v-067). La regola che le governa è
[ADR-0072](Decision.md#adr-0072): le pagine si riscrivono sulla misura di oggi, dentro il lavoro che
ha cambiato il comportamento; la misura vecchia si data in `Sources.md` invece di sparire
([V-058](Sources.md#v-058) e [V-063](Sources.md#v-063) hanno un «Seguito» ciascuna); e dove la
risposta nuova è più pericolosa della vecchia, la pagina lo dice. Restano fuori dalla regola i
verbali datati di `docs/00-progetto/` e le sezioni già marcate con la loro data, come la §4.1 della
pagina sulla sicurezza: riscriverle cancellerebbe l'informazione che portano.

La §3.3 della guida non si limita più a elencare i messaggi. Ha adesso la regola che li tiene
insieme, e che sopravvive al prossimo cambiamento: le funzioni di `sh` che si risolvono in una
**lettura** del database `config` su uno shard riescono e rispondono il vuoto; quelle che spediscono
un **comando** trovano un `mongod` che non ce l'ha, e lo dicono. `make docs-check`: citazioni e
collegamenti coerenti.

123. **Cercare le pagine che una decisione ha appena reso false è parte della decisione, non della
     pulizia successiva.** Il modo di cercarle è banale — si prende il testo del messaggio d'errore
     vecchio e lo si cerca nel repository — e non esiste nessuna automazione che lo faccia al posto
     di chi decide, perché nessun controllo sa quale frase la modifica ha invalidato. Qui il commit
     di ADR-0071 è passato verde attraverso tutti e quattro i controlli con quattro affermazioni
     false dentro, e a trovarle è stata una lettura fatta per un altro motivo.

124. **Rimisurare dopo una modifica non serve a confermare che la modifica ha funzionato: serve a
     scoprire che cosa è cambiato intorno.** Le risposte attese erano due e sono arrivate. Le altre
     quattro no, e fra quelle c'era l'unica che conta per chi userà lo stack: un errore sostituito da
     una risposta plausibile. Chi rimisura per confermare guarda le due, chiude, e non vede le
     quattro.

Stato: decisioni fino a **ADR-0072**, verifiche fino a **V-067**, fonti fino a **S-075**, note di
metodo fino alla **124**. Il **Task 10** riprende dal punto in cui si era interrotto: le tre scene
già registrate e verificate, la scena del guasto ancora da scrivere.

---

## 2026-09-02 — `feature/03`, Task 10: cinque scene per il Blocco 3, e il comando che le produce

Il Task 10 chiedeva quattro momenti registrati: l'avvio nel profilo `palco`, `sh.status()`, la
distribuzione dei documenti, il failover di un membro di shard. Ne sono venute **cinque**, e il
conto non torna per un motivo che vale la pena scrivere: nel profilo `palco` il failover di un
membro di shard **non può avvenire**, perché ogni shard ha un membro solo. La scena è stata quindi
registrata due volte — lo stesso comando, due profili. Nel `palco` finisce con un'attesa e un
errore; nel `completo` finisce con un'elezione. Prese insieme dicono la cosa che nessuna delle due
dice da sola: la disponibilità non è del cluster, è di ogni singolo shard.

**Il perimetro che il piano aveva dato non è bastato.** Task 10 era assegnato a
`docs/05-talk/registrazioni/`. Per il Blocco 2 sarebbe stato sufficiente: quelle scene erano
`make failover-02` e le sue varianti, comandi che esistevano già per la sala, e registrarli è
costato una riga. Per lo sharded no. `sh.status()`, il conteggio shard per shard e la sequenza del
guasto non erano comandi: erano gesti da battere dentro `docker exec`. Registrare un gesto produce
un artefatto che nessuno saprà rifare uguale, e che invecchia senza che niente lo segnali. Sono nati
`tools/demo-sharded.sh` con tre scene e tre bersagli nel `Makefile` — `stato-03`,
`distribuzione-03`, `guasto-03`. Il motivo e le sue conseguenze stanno in
[ADR-0073](Decision.md#adr-0073); il piano approvato non si tocca, e la deviazione è questa riga.

**Le scene misurano invece di raccontare.** Nessun numero è scritto nel copione: quanti membri ha
ogni shard lo chiede allo shard, i due `_id` da cercare li chiede ai due shard invece di
indovinarli, i secondi di ogni risposta li cronometra, e dopo il guasto il nuovo primario lo legge
da un membro superstite. Costa qualche riga in più e vale la differenza fra una scena che resta vera
quando cambia la configurazione e una che comincia a mentire senza dirlo. Il bersaglio si chiama
`guasto-03` e non `failover-03` per la stessa ragione: nel `palco` un failover non c'è, e un nome
vero in un solo profilo su due non è un nome.

**Il renderer di Compose pesava quarantaquattro volte il comando.** La prima registrazione
dell'avvio a freddo occupava **588 KB** per una ventina di secondi, ed era illeggibile: il renderer
predefinito ridisegna una tabella animata e riscrive ogni riga a ogni aggiornamento. Con
`COMPOSE_PROGRESS=plain` ogni container scrive la propria riga una volta sola e l'ordine della
catena si vede scorrere. Il confronto controllato — stesso `up`, stesso stack già acceso, due
registrazioni a nove secondi di distanza — dà **134 861 byte in 205 eventi** contro **3 050 byte in
28 eventi**, a parità di durata. Registrare l'uscita di uno strumento interattivo significa
registrare anche la sua animazione.

**Riprodurre serve a due cose, e una sola si può automatizzare.** Tutte e cinque le scene sono state
riaperte con `--riproduci` per intero prima di entrare nell'indice
([ADR-0055](Decision.md#adr-0055)), e per tutte e cinque la riproduzione dentro uno pseudo-terminale
coincide **byte per byte** con l'originale — dopo aver normalizzato il fatto che lo pseudo-terminale
traduce ogni `\n` in `\r\n`, e quindi restituisce `\r\r\n` dove la registrazione aveva `\r\n`. Quel
confronto però prova solo che il file si rivede fedelmente. Che la scena del profilo `completo`
*affermasse* l'elezione invece di mostrarla — scriveva che il router se n'era accorto, senza mai
chiedere chi fosse il nuovo primario — l'ha visto un occhio, non il confronto: la scena è stata
riscritta e rigirata.

**Il profilo `completo` e il file che non sta nel repository.** La quinta scena ha richiesto di
scambiare in `docker/03-sharded/.env` le tre righe `MEMBRI_*`, portare lo stack a tre membri per
insieme, registrare, e rimettere tutto com'era. Lo scambio è stato fatto con una trappola su `EXIT`
che ripristina il file anche se qualcosa fallisce a metà, ed è finito con lo stack riportato a
`palco` su volumi nuovi. Quel file è gitignored ([ADR-0014](Decision.md#adr-0014)): nessun controllo
si accorgerebbe di un `.env` lasciato a tre membri, e chi lo lascia così si ritrova il `palco` che
non riparte. Sta scritto nell'indice delle registrazioni, che è dove lo si legge nel momento in cui
serve.

**I filmati restano da girare, e `preflight` continua a dirlo** (Passo 4). Nessun `.mp4` finto è
stato creato per spegnere l'avviso: la cartella `~/SqlStart2026-registrazioni` è assente, il
controllo lo segnala, e dal 18 settembre diventerà bloccante. L'elenco dei filmati dovuti è passato
da quattro a sei, con le due scene del Blocco 3 aggiunte in coda.

Le misure delle cinque scene stanno in [V-068](Sources.md#v-068). L'indice
[`docs/05-talk/registrazioni/README.md`](05-talk/registrazioni/README.md) è stato riscritto: due
tabelle invece di una, i comandi per rifare ogni scena, il metodo di verifica, e la correzione della
riga che diceva «non contiene le scene degli altri stack». Una citazione nuova in
[`citazioni-riportare-slide.md`](citazioni-riportare-slide.md). Controlli: `make preflight`
8 superati, 1 avviso — i filmati — 0 errori; `make docs-check` citazioni e collegamenti coerenti;
`make stack-check` 3 stack conformi; `make tools-test` 131 passati; `make smoke-03` 64 controlli e
0 errori nel profilo `palco`.

125. **Una registrazione si giudica riproducendola, e il confronto automatico trova solo metà dei
     problemi.** Il confronto byte per byte prova che il file si rivede identico a com'è stato
     scritto: è una proprietà del file, non della scena. Che la scena mostri quello che dice di
     mostrare non è verificabile da nessuna macchina, perché la macchina non sa che cosa la scena
     doveva dimostrare. Le due verifiche vanno fatte tutt'e due, e quella che serve di più è quella
     che costa un paio di minuti di attenzione.

126. **Il peso di una registrazione di terminale dipende dal renderer, non dal comando.** Quarantaquattro
     volte, a parità di durata e di risultato. Prima di registrare l'uscita di uno strumento
     interattivo conviene chiedersi se quello strumento ha una modalità non interattiva: quasi
     sempre ce l'ha, quasi sempre è una variabile d'ambiente, e quasi sempre il risultato è anche
     più leggibile di quello animato.

127. **Una scena che vale in un solo profilo è mezza scena.** Lo stesso `make guasto-03` racconta due
     storie opposte nei due profili, e la condizione per poterlo scrivere una volta sola è stata
     scegliere un nome che descrivesse il **gesto** — si ferma un nodo — invece dell'esito.
     Nominare per esito significa promettere l'esito, e l'esito qui dipende dalla configurazione di
     chi esegue.

Stato: decisioni fino a **ADR-0073**, verifiche fino a **V-068**, fonti fino a **S-075**, note di
metodo fino alla **127**. Del piano di `feature/03` restano il **Task 11** — gli ADR e le fonti
mancanti, il consuntivo del branch, i tre debiti di strumentazione ancora aperti
([ADR-0049](Decision.md#adr-0049), [ADR-0062](Decision.md#adr-0062)), i quattro controlli eseguiti
due volte e la PR verso `develop`.

---

## 2026-09-02 — `feature/03`, Task 11: i tre debiti chiusi eseguendo, e la chiusura del branch

Il Task 11 chiedeva gli ADR mancanti, le fonti, il consuntivo, le citazioni, i quattro controlli
due volte e la PR. In coda gli erano stati rinviati **tre debiti di strumentazione**, e la regola
per chiuderli è quella di [ADR-0049](Decision.md#adr-0049): eseguendo, non ragionando.

**Il Passo 1 chiedeva un ADR che esisteva già.** «Almeno una è certa: l'esito del Passo 2 del Task 4,
l'healthcheck di `mongos`». È [ADR-0061](Decision.md#adr-0061), scritta il 1° settembre nel task che
la produsse. La riga del piano è stata scritta prima di sapere che quella decisione sarebbe stata
presa subito, e non c'era niente da aggiungere: scriverne una seconda avrebbe creato due sedi per
una decisione sola, che è precisamente ciò che [ADR-0002](Decision.md#adr-0002) vieta.

**Il primo debito non era un errore, ed era il più interessante dei tre.** Le porte pubblicate dai
tre file Compose e quelle controllate da `tools/preflight.sh` coincidono: quindici e quindici,
nessuna mancante, nessuna eccedente, in ordine, senza doppioni. Il debito non era uno sbaglio da
correggere: era che la coincidenza reggeva **per attenzione**. Sette delle quindici porte esistono
solo nel profilo `completo` — cioè sono esattamente quelle che nessuno vede quando lavora nel
`palco`, e quelle che si dimenticano.

**Il secondo aveva una manifestazione, e brutta.** Compose accetta qualunque stringa dopo
`--profile`. Un profilo che non esiste non seleziona niente, quindi restano i soli servizi che non
dichiarano `profiles:` — nel nostro file uno, `keyfile-init`. `make up-03 PROFILO=inesistente` avvia
quel container, lo aspetta, lo vede uscire 0 e muore con `container sh-keyfile-init exited (0)`,
uscita 2. Accusa l'unico pezzo che ha fatto il suo mestiere, e la parola «profilo» non compare in
nessuna delle cinque righe. Il rimedio è il bersaglio `profilo-03`, che chiede l'elenco dei profili
al file Compose con `config --profiles` invece di riscriverlo a mano; i sette bersagli che usano
`PROFILO` lo dichiarano fra i prerequisiti. Il motivo per cui l'elenco **non** si scrive nel
`Makefile` sta in [ADR-0074](Decision.md#adr-0074), insieme al resto.

**Il terzo era una domanda, e la risposta è migliore della domanda.** [ADR-0062](Decision.md#adr-0062)
temeva che `up-02` funzionasse per fortuna: due comandi, e il secondo regge solo finché `up --wait`
torna prima che `rs-init` finisca. Misurato su tre avvii a freddo, il margine è di **21,6 s**, e a
caldo `wait rs-init` blocca ancora **3,9 s**. Ma il dato che chiude il debito non è l'ampiezza:
`rs-init` è l'ultimo anello e non ha healthcheck, quindi la soglia di `--wait` per lui è `running`.
`up --wait` torna nell'istante in cui `rs-init` **comincia**, e la finestra del secondo comando
coincide con l'intera durata del suo lavoro. Non si restringe con una macchina più veloce: si
restringe solo se `rs-init` smette di lavorare. Il debito si chiude come **verificato**, non come
corretto, e quello che entra nel repository è il motivo, scritto accanto alla riga che lo sfrutta
([ADR-0075](Decision.md#adr-0075)).

**Il fallimento temuto esiste comunque, e mente sul motivo.** Dato `docker compose wait rs-init` a
cose finite, la risposta è `no containers for project "sqlstart-02-replicaset"` con uscita 1 — nello
stesso istante il progetto ha cinque container e `ps -a` li elenca tutti. `compose wait` guarda solo
i container vivi: il messaggio nomina l'intero progetto per dire che non ne trova uno. È il gemello
del messaggio che accusa il keyfile, e i due insieme sono diventati una citazione per le slide.

**Misurare lo stack 02 dentro il worktree di un altro branch.** Il `.env` dello stack 02 sta fuori
dal repository ([ADR-0014](Decision.md#adr-0014)) e nel worktree non c'era. È stato copiato dal
checkout principale per la durata della prova, e alla fine lo stack è stato smontato con i volumi
dei dati cancellati e il file rimosso: `git status` è tornato pulito. Una misura presa su un altro
stack non deve lasciare tracce nel branch che la prende, e in un worktree la traccia sarebbe
invisibile proprio perché quel file è ignorato.

**Le prove sono state viste fallire.** Le tre coerenze nuove vivono in
`tools/tests/test_coerenza_repo.py`, il primo modulo della suite che legge i file **veri** del
repository invece di campioni costruiti. Prima di considerarle buone sono state rotte una alla
volta: tolta la porta 27017 dall'elenco, tolto il guardiano a `guasto-03`, sostituito `$(PROFILO)`
con `palco` nella ricetta del guardiano. Tutte e tre hanno fallito, con il messaggio che nomina il
file da correggere. La suite passa da 131 a **139**.

I quattro controlli sono stati eseguiti due volte, come chiedeva il Passo 5. Con lo stack 03 acceso
nel profilo `palco`: `preflight` 8 superati, 1 avviso — i filmati — 0 errori, con 4 porte tenute dal
lab stesso; `docs-check` citazioni e collegamenti coerenti; `stack-check` 3 stack conformi;
`tools-test` 139 passati; e in più `smoke-03` 64 controlli e 0 errori. Con tutti gli stack fermi:
gli stessi esiti, e le 15 porte tutte libere.

128. **Un debito si chiude anche accertando che non c'era, e il valore sta in quello che si vede
     accertandolo.** Due dei tre debiti non erano errori il giorno in cui li si è misurati. Se ci si
     fosse limitati a guardarli, la conclusione sarebbe stata «va bene così» e la marcatura sarebbe
     stata tolta. Eseguendo si è visto **come** si manifesterebbero — cinque righe che accusano il
     keyfile, un messaggio che nomina un progetto intero per dire che non trova un container — e
     quelle due manifestazioni sono l'unica cosa che ha permesso di scrivere rimedi utili. Un debito
     accertato inesistente va chiuso trasformando «corretto per attenzione» in «corretto per
     costruzione», altrimenti lo si è solo rinviato con parole più belle.

129. **Un errore risponde alla domanda che gli è stata fatta, non a quella che si voleva fare.**
     `container sh-keyfile-init exited (0)` è vero. `no containers for project` è vero. Nessuno dei
     due strumenti ha mentito, e tutt'e due mandano a cercare nel posto sbagliato. Prima di credere
     a un messaggio d'errore conviene ricostruire **quale domanda** lo strumento si è posto: è lo
     stesso meccanismo per cui un cluster senza shard risponde `[]` invece di dichiararsi rotto.

130. **Una fragilità si scrive accanto alla modifica che la scatenerebbe, non accanto a una data.**
     Il pericolo di `up-02` non era il tempo: era che qualcuno leggesse due comandi dove ne pareva
     bastare uno e ne togliesse uno per pulizia. Un commento che dicesse «da riverificare» sarebbe
     invecchiato senza che nessuno lo leggesse; uno che dice «chi svuota `rs-init` deve togliere
     anche questa riga» si fa trovare esattamente da chi sta per romperla.

131. **Una prova che non si è vista fallire non è una prova.** Le tre coerenze nuove sono state
     rotte una per una prima di essere accettate, e il costo è stato due minuti. Una prova scritta
     dopo il codice passa al primo colpo, ed è il momento in cui è indistinguibile da una prova che
     non controlla niente — un `assert` su un dizionario vuoto passa sempre. Rompere ciò che si sta
     proteggendo è l'unico modo economico di sapere che la protezione tocca la cosa giusta.

**Consuntivo del branch, alla vigilia dell'unione.** **Ventiquattro** commit e **trentatré** file
rispetto a `develop`: il piano, undici di task, due punti di ripresa, il commit di avvio, quello
della nota di metodo lasciata da `feature/02`, la correzione del numero della PR e questo — che è
compreso nel conto, come prescrive la **nota 37**. La riga diceva «venti» quando fu scritta, e la
sta riscrivendo per la seconda volta lo stesso meccanismo che la nota 37 descrive: un numero che
parla del branch e vive dentro il branch cambia ogni volta che il branch cambia. Il trentatreesimo
file è `tools/tests/test_coerenza_repo.py`, nato oggi; il conto dei file non si muove perché gli
ultimi due commit toccano solo questa pagina. Su GitHub non gira nessun controllo, per scelta
([ADR-0038](Decision.md#adr-0038)): i quattro sono verdi in locale, due volte.

**Quello che resta aperto** e non appartiene a questo branch: i filmati `.mp4`, che solo il relatore
può girare, con l'avviso di `preflight` acceso e bloccante dal 2026-09-18; e i cinque debiti di
documentazione sui backup dei config server aperti da [ADR-0071](Decision.md#adr-0071). Lo scambio
delle righe `MEMBRI_*` in `docker/03-sharded/.env`, necessario per rifare la scena 9, resta un
passaggio che nessun controllo può sorvegliare perché quel file non sta nel repository: sta scritto
nell'indice delle registrazioni, che è dove lo si legge quando serve.

Stato: decisioni fino a **ADR-0075**, verifiche fino a **V-069**, fonti fino a **S-075**, note di
metodo fino alla **131**. Il piano di `feature/03` è completo: undici task su undici. La feature si
chiude unendo la **PR #5** su GitHub, e non con `git flow feature finish`: quella scorciatoia
salta la revisione, ed è già successo una volta.

**Correzione, mezz'ora dopo: la PR è la #4, non la #5.** Le righe qui sopra, il Passo 6 del piano e
la tabella §10 del design dicono tutti «PR #5», e si sbagliano per la stessa ragione. Il calendario
del design faceva chiudere `feature/04` per prima, con la #4, e a `feature/03` toccava la #5.
[ADR-0057](Decision.md#adr-0057) ha invertito i due branch il 1° settembre e ha riscritto le date,
ma nessuno ha ripensato ai numeri: GitHub li assegna in ordine di apertura, e con tre PR aperte —
#1, #2, #3 — e nessuna issue, questa è la **#4**. È
[https://github.com/giulianolatini/SqlStart2026/pull/4](https://github.com/giulianolatini/SqlStart2026/pull/4).

Le righe di prima restano come sono: il registro è cronologico e non si riscrive, e un numero
sbagliato con accanto la ragione per cui lo era vale più di un numero giusto comparso dal niente.
Il piano non si tocca per la regola di sempre. La tabella del design non si tocca perché ADR-0057 la
supera già per intero: chi la legge deve arrivare all'ADR comunque, e adesso ci arriva sapendo che
anche i numeri delle PR erano dentro il pacchetto invertito.

132. **Quando si inverte l'ordine di due cose, si inverte anche tutto quello che era numerato in
     quell'ordine.** ADR-0057 ha spostato date, motivazioni e dipendenze fra i due branch, e ha
     lasciato indietro l'unica cosa che nessuno assegna a mano: il numero che GitHub darà alla PR.
     Il costo qui è stato nullo — se ne è accorto `gh pr list` due minuti prima di aprirla — ma la
     forma dell'errore è la solita: un identificatore che sembra un'etichetta e invece è una
     posizione.

Stato aggiornato: note di metodo fino alla **132**.

---

## 2026-09-02 — Una review esterna su PR #4, e una fonte citata più larga di com'era stata misurata

Aperta la PR #4, Giuliano l'ha data in lettura a Copilot, come le tre precedenti. Due rilievi in
linea, entrambi in italiano, entrambi con file e riga. Arbitrati eseguendo, come vuole la regola
che vale dalla PR #1: prima si lancia il comando, poi si giudica.

**Il primo rilievo è mezzo giusto, e la metà giusta è più grave della metà sbagliata.** Su
`tools/check_stack.py` il recensore scrive che `nome_del_set()` può restituire una stringa vuota
se `--configdb` comincia con `/`, «e a quel punto il chiamante la tratta come un nome di replica
set valido». La prima parte è vera: chiamata su `/cfg1:27017` la funzione restituiva `''`, e con
uno spazio davanti restituiva lo spazio. La seconda è falsa: dato quel file a `verifica`, i
problemi restituiti sono **due** e lo stack viene bocciato. Nessun falso negativo, e nessuno stack
del repository è mai stato approvato per sbaglio.

Il difetto vero sta dove il rilievo non guardava. Il messaggio che usciva era quello del refuso, e
diceva due cose false in tre righe: «nomina il replica set «»», che non nomina niente, e
soprattutto «è l'unico caso in cui nessuno protesta: i processi partono tutti». Misurato:
`mongos --configdb /cfg1:27017` non parte, esce **2** e risponde `BadValue: configdb supports only
replica set connection string`. Lo strumento mandava a cercare un refuso di due lettere dentro i
`--replSet` del file mentre il difetto era una barra di troppo in bella vista — la stessa forma
d'errore della nota 129, incontrata per la terza volta in questo branch.

**E qui la misura ha trovato una cosa che nessuno cercava.** Il messaggio del `--configdb` senza
nome di set cita `FailedToParse: invalid url`. È una stringa vera, misurata in
[V-057](Sources.md#v-057) — sulla forma con la **virgola**, `a:27017,b:27017`. Su un host solo
`mongos` risponde `BadValue: configdb supports only replica set connection string`, cioè un'altra
cosa. E l'host solo è precisamente ciò che la prova del repository esercitava. Per tutto il Task 5
la prova ha verificato un caso e il messaggio ne ha promesso un altro, e sono nati nello stesso
commit. La fonte non ha mai sbagliato: a essere troppo larga era la citazione che ne facevo.

Il motivo per cui la cosa è passata sta nella prova: `assert any("--configdb" in problema …)`.
Quell'asserzione è vera per il messaggio giusto e per quello del refuso allo stesso modo, quindi
non poteva distinguerli. Era una prova che si era vista fallire — la nota 131 è rispettata — ma
che passava per una ragione più debole di quella per cui era stata scritta.

Correzioni: `nome_del_set` normalizza con `strip()` e restituisce `None` per il nome vuoto; il
messaggio porta entrambe le stringhe misurate, con la virgola come condizione che le distingue.
Due prove nuove, rotte prima di essere accettate: con il difetto rimesso, la prima riporta per
intero il messaggio del refuso e la seconda `assert '' is None`. La suite passa da 139 a **141**.
La decisione è [ADR-0076](Decision.md#adr-0076), la misura [V-070](Sources.md#v-070).

**Il secondo rilievo è giusto e basta.** Il `README.md` scriveva «lo sharded cluster, quando
arriverà, pure» a proposito del file `.env`, mentre la riga 55 dello stesso file dichiara
`docker/03-sharded` «nel repository». La contraddizione è nata in questa PR: la tabella dello stato
è stata aggiornata, il paragrafo sotto no. Guardandolo per correggerlo è venuta fuori la metà
operativa dello stesso difetto — la sezione si intitola «Dal secondo stack in poi» ma il blocco di
comandi copiava un file solo, e `docker/03-sharded/.env.example` esiste dal 2 settembre. Adesso il
paragrafo dice che i file sono due, il blocco li copia entrambi e la frase sugli indizi nomina
`make up-03` accanto a `make up-02`, perché il guardiano ce l'hanno tutti e due.

**Che cosa non è stato fatto.** Nessuno dei due rilievi tocca il perimetro del branch, e non è
stato aperto niente di nuovo per l'occasione. Il riepilogo della review elenca i file toccati senza
altri rilievi: i due commenti in linea sono tutto.

133. **Una fonte misurata su un caso non autorizza a parlare di tutti i casi della sua famiglia.**
     [V-057](Sources.md#v-057) ha misurato l'elenco di host separati da virgola e ha scritto
     esattamente quello. Il messaggio dello strumento ha citato la fonte e ha allargato: da «su
     questa forma risponde così» a «su un elenco nudo di host risponde così». L'allargamento è
     avvenuto nel passaggio dalla fonte al codice, dove nessun controllo guarda, ed è invisibile
     proprio perché la citazione è corretta — il numero della fonte esiste, la stringa è testuale,
     manca solo la condizione sotto cui vale. Citare una misura significa citarne anche il caso.

134. **Un'asserzione può essere così larga da passare per la ragione sbagliata.** La prova che
     copriva questo messaggio chiedeva che fra i problemi ce ne fosse uno contenente
     `--configdb`, ed era vera tanto per il messaggio corretto quanto per quello del refuso. È il
     grado sopra la nota 131: la prova era stata vista fallire, quindi controllava *qualcosa* — ma
     controllava che ci fosse **un** messaggio, non **quel** messaggio. Quando il valore di uno
     strumento è ciò che dice, l'asserzione deve leggere ciò che dice, e la forma che funziona è
     dichiarare anche ciò che il messaggio **non** deve contenere.

Stato aggiornato: decisioni fino a **ADR-0076**, verifiche fino a **V-070**, note di metodo fino
alla **134**. La suite è a **141** prove. La PR #4 resta aperta: i due thread sono stati chiusi con
la prova, e l'unione spetta al PO.

---

## 2026-09-02 — La seconda review su PR #4: tre falsi verdi, e in due casi l'avviso c'era già

Chiusa la prima review, Giuliano ha chiesto un secondo parere sulla stessa PR, a un altro modello,
con un incarico scritto: uno sguardo indipendente, non una conferma del primo. Il prompt diceva
dove guardare in ordine di valore, che cosa non segnalare — la lingua italiana, la verbosità dei
commenti, l'assenza di CI — e che cinque rilievi provati valgono più di venti supposti.

Ne sono arrivati tre. **Tutti e tre veri**, il che è una differenza di esito e non di merito
rispetto alla prima review: là un rilievo su due nasceva da una diagnosi sbagliata, qui nessuno.
Vale la pena scrivere perché, e la ragione non è che il secondo revisore sia più bravo. La prima
review guardava una funzione e ragionava sul valore di ritorno; questa guardava la catena di avvio
e ragionava sul **codice d'uscita**. Sono due punti d'osservazione, non due livelli di abilità.

**Il filo che lega i tre.** La testata della PR promette che «`make up-03` è **un** comando e il
suo codice d'uscita è il verdetto». Ognuno dei tre rilievi è un punto in cui quel verdetto è verde
su uno stack che non fa quello che la pagina accanto promette. E in due casi su tre — il seed, e il
log del router — **una frase che diceva la verità c'era già**, stampata, in italiano, corretta. Non
la leggeva nessuno, perché `up --wait` legge i codici e non le frasi.

**Primo — il router senza keyfile.** La regola che pretende `--keyFile` in `check_stack.py` sta
dentro il ramo di `avvia_mongod`, e un `mongos` non è un `mongod`. Verificato su un file vero e non
su un documento sintetico: tolte al router le sole due righe del keyfile,
`check_stack.py` rispondeva «Stack conformi: 1» e usciva **0** ([V-071](Sources.md#v-071)). Avviato,
quello stack esce **1** — «container sh-mongos is unhealthy» — e il router ripete in ciclo
`Command find requires authentication`, che è la frase della password sbagliata mentre la password
è giusta.

**Secondo — il cambio di profilo su uno stack già acceso.** Gli anelli di inizializzazione saltano
il lavoro se il replica set è già formato, e non guardano **con quali membri**.
[ADR-0060](Decision.md#adr-0060) aveva previsto due direzioni di disallineamento fra `MEMBRI_*` e
`--profile` e le sorveglia entrambe; questa è una terza, che non viene dall'ambiente ma dal disco.
Misurato: la catena stampa «config server pronto», esce **0**, e il set ha **un** membro mentre due
config server sani girano fuori dalla replica ([V-072](Sources.md#v-072)). Durante la stessa prova
una delle due guardie esistenti si è fatta viva da sé, fermando la catena con uscita **5**: ADR-0060
regge, il buco era accanto e non dentro.

**Terzo — il seed accetta qualunque ventimila.** Il caricamento si salta se `lab.ordini` ha già
ventimila documenti, e il conteggio non dice se sono distribuiti. Su una collezione piena e assente
dal catalogo, il seed stampa «ATTENZIONE: lab.ordini non risulta distribuita» ed esce **0**.

**Che cosa si è deciso, in [ADR-0077](Decision.md#adr-0077).** Una regola nuova per il router,
accanto a quella del `mongod` e non dentro. Un confronto fra membri configurati e membri chiesti nei
due anelli di init, con uscita **6** e i due elenchi stampati. Un'uscita **9** dal seed quando la
collezione manca dal catalogo. E il cheat sheet della pagina dello sharded, che chiedeva di
scommentare le tre righe `MEMBRI_*` senza dire che prima si azzera — mentre l'indice delle
registrazioni lo diceva: due pagine con metà manovra a testa.

**Che cosa si è deciso di NON fare.** Riconfigurare il set invece di fermarsi: `rs.reconfig()` su un
set con dati dentro non è un'operazione da `depends_on`. Bocciare anche i documenti finiti su un solo
shard: unire i chunk è una **scena** della demo ([ADR-0069](Decision.md#adr-0069)), e il `make up-03`
che segue quella scena non deve diventare rosso per averla eseguita. La distinzione fra «stato che
il seed non avrebbe prodotto» e «stato che nessuna scena può produrre» è la riga su cui passa la
correzione.

**Le prove.** Le due nuove di `check_stack.py` viste fallire con la regola neutralizzata; le
correzioni agli script riprodotte nei due versi — uscite 6 e 9 con membri e conteggi nominati, e poi
i giri leciti: `up-03` in `palco` e in `completo`, da zero e ripetuto, **0** tutte e quattro le
volte, `make seed-03` che ricostruisce la collezione distribuita, e `smoke-03 PROFILO=completo` a
«Superati: 101 · Errori: 0». Le cinque registrazioni asciinema non sono toccate: mostrano giri
leciti, e nei giri leciti niente cambia.

**Una nota sul revisore.** Non ha potuto lanciare la suite: la sua sandbox in sola lettura ha
bloccato l'inizializzazione della cache di `uv`. È un limite della sua esecuzione, non un difetto del
repository, e va scritto perché spiega la forma dei suoi rilievi — tutti e tre nascono da lettura del
codice, e la misura che li ha confermati l'abbiamo fatta qui.

135. **Un avviso che non cambia il codice d'uscita è un avviso che nessuno legge.** Il seed sapeva
     che la collezione non era distribuita e lo scriveva. Il router sapeva di non potersi
     autenticare e lo scriveva. In entrambi i casi la frase era corretta e finiva in uno stream che
     il chiamante automatico non guarda: `up --wait` raccoglie codici d'uscita e stati di salute, e
     una catena di sei anelli è fatta apposta perché nessuno debba leggere sei log. Un messaggio
     diagnostico e un codice d'uscita non sono due modi di dire la stessa cosa: il primo serve a chi
     è già andato a guardare, il secondo serve a farcelo andare. Se una condizione merita la frase,
     bisogna decidere esplicitamente se merita anche il codice — e scrivere la ragione quando la
     risposta è no, come qui per il singolo shard.

136. **Due revisori che trovano cose diverse non sono uno bravo e uno no: guardano da due punti.**
     Il primo revisore ha esaminato una funzione e ha ragionato sul suo valore di ritorno,
     trovando un difetto di messaggio e sbagliando la diagnosi. Il secondo ha esaminato la catena di
     avvio e ha ragionato sul codice d'uscita, trovando tre falsi verdi e nessuna diagnosi
     sbagliata. Nessuno dei due ha visto quello che ha visto l'altro. La conclusione utile non è
     «chiediamo al migliore» ma «la domanda che si pone al revisore decide che cosa può trovare»: il
     prompt di questa seconda review nominava esplicitamente codici d'uscita e comandi che
     falliscono in silenzio, e i tre rilievi sono arrivati esattamente da lì.

Stato aggiornato: decisioni fino a **ADR-0077**, verifiche fino a **V-072**, note di metodo fino
alla **136**. La suite resta a **143** prove. La PR #4 resta aperta: le due review sono state
arbitrate eseguendo, e l'unione spetta al PO.

---

## 2026-09-02 — `feature/04`, avvio: una data anticipata, un worktree che ha murato la sessione, e un rischio già chiuso

Il branch dell'applicazione è aperto, e come la `03` ha tre cose da mettere per iscritto prima di
toccare un file: perché comincia oggi invece del 4, che cosa è successo chiudendo il worktree
precedente, e quale pezzo del design non vale più.

**Perché oggi.** [ADR-0057](Decision.md#adr-0057) aveva chiuso l'anticipo della `03` con una
clausola secca: «`feature/04` non si muove dal 4 settembre». `feature/03` è finita il 2, con undici
task su undici e la PR #4 aperta. La tentazione era leggere la clausola come un divieto e aspettare
un giorno; la lettura giusta stava nelle **alternative scartate** dello stesso ADR, che bocciavano
«spostare `feature/04` di due giorni» perché avrebbe prodotto un branch **frammentato**, cioè
lavorato a pezzi separati. Chiudendo il 2, i giorni dal 2 all'11 sono contigui: la condizione la cui
assenza motivava il rifiuto c'è. [ADR-0078](Decision.md#adr-0078) modifica la clausola di data e
lascia intatto il resto — la scadenza dell'11 non si muove, e i due giorni guadagnati restano
margine.

**Un worktree rimosso ha murato la sessione.** Chiudendo la `03` il worktree è stato eliminato
mentre una sessione ci stava dentro, e da quel momento la sessione non ha più potuto fare niente:
ogni comando di shell e ogni scrittura rifiutati, perché nessuna directory di lavoro può risolvere
dentro un percorso che non esiste. Restava la sola lettura. L'isolamento non è uno stato del
filesystem né del repository: è un **percorso assoluto registrato all'avvio**, e `git worktree
remove` non ha modo di aggiornarlo. Il comando che ha fatto il danno era quello giusto, dato fuori
ordine.

La via d'uscita esiste ed è stata misurata ([V-073](Sources.md#v-073)): `ExitWorktree` in modalità
`keep` sgancia l'aggancio **anche quando il worktree è già stato cancellato** e **anche quando
l'isolamento veniva dall'avvio** invece che da un `EnterWorktree` — la sua documentazione dice il
contrario, e la documentazione ha torto. Poi `EnterWorktree` con il percorso nuovo. Il rientro
diretto non funziona, e il branch che il messaggio di successo annuncia non viene mai creato: un
messaggio corretto nella forma e falso nel contenuto, che è la categoria di errore più cara.
[ADR-0079](Decision.md#adr-0079) fissa l'ordine vincolante della chiusura — **si sgancia chi sta
dentro, poi si rimuove** — e la procedura completa, apertura e chiusura, sta in
[`06-sviluppo/worktree-e-branch-di-lavoro.md`](06-sviluppo/worktree-e-branch-di-lavoro.md), che
prima non esisteva: la manovra si tramandava a voce, ed è esattamente il modo in cui la si sbaglia
due volte.

È la seconda volta che il repository scopre la stessa cosa sullo stesso comando.
[ADR-0056](Decision.md#adr-0056) era nato perché `git worktree remove` porta via i file **ignorati**
insieme alla directory; ADR-0079 nasce perché porta via anche il terreno sotto i **processi**. In
entrambi i casi il comando esce `0` e in entrambi i casi la perdita è di qualcosa che git non
considera suo.

**Il rischio numero uno del design è chiuso da otto giorni, e il design non lo sa.** Il §7 di
[`2026-08-24-design.md`](00-progetto/2026-08-24-design.md) elenca come rischio 1 il supporto di
`testcontainers-python` ai replica set e scrive: «la verifica è il primo passo di `feature/04`;
l'esito è un ADR in ogni caso». Quell'ADR esiste dal 25 agosto: è
[ADR-0020](Decision.md#adr-0020), che supera [ADR-0011](Decision.md#adr-0011) e sceglie gli stack
del repository invece di un facsimile. Il primo passo di questo branch **non** è quella verifica, e
per la stessa ragione è superata la riga del §7 che vuole le fixture con «un Compose minimale
proprio, non quello di `docker/`»: ADR-0020 dice il contrario ed è del giorno dopo. Il piano lo
dichiara in testa, perché è l'unico posto dove chi esegue guarderà.

**Il primo passo vero è un appuntamento.** [ADR-0058](Decision.md#adr-0058) aveva trasformato la
clausola «appena escono i binari» in due date: il 3 settembre, «alla chiusura di `feature/03`», e il
16. Le due coordinate si sono separate — l'evento è arrivato il 2 — e ADR-0078 stabilisce che vale
**l'evento**, perché è l'evento a portare la ragione pratica: montare l'applicazione su una versione
e ripinnarla il giorno dopo significa rigirare le registrazioni. Il controllo della 8.0.30 è quindi
il Task 1 di questo branch, e lascia una voce in `Sources.md` in ogni caso.

**Il piano è scritto:** [`2026-09-02-piano-feature-04-app-python.md`](00-progetto/2026-09-02-piano-feature-04-app-python.md),
diciotto task. È l'opposto della `03`: lì lo spike del 25 agosto faceva da mappa e il branch partiva
con la topologia già montata, qui si comincia da **zero righe di codice** e la mappa è il §6 del
design. Il piano porta anche i debiti che quattro pagine hanno intestato per iscritto a questa
feature — le misure che «hanno senso solo sotto carico controllato» — e le tre pagine che
`docs/README.md` promette qui. Scrivendo l'indice è saltata fuori una quinta assenza: il piano della
`03` era stato scritto il 1º settembre e **mai iscritto** in `docs/README.md`. Il controllo dei
collegamenti verifica quelli che ci sono; una pagina che nessuno cita non ha un'ancora da
controllare.

**Note di metodo.**

137. **Le alternative scartate di un ADR contengono il ragionamento che la decisione comprime.** La
     clausola di ADR-0057 diceva «non prima del 4 settembre» e sembrava chiusa. Il perché stava
     dodici righe più sotto, fra le alternative: si era rifiutato di anticipare per non
     **frammentare** il branch, non per la data in sé. Con la `03` chiusa il 2, la frammentazione
     non c'era, e la decisione originale — letta per intero — **permetteva** ciò che la sua clausola
     sembrava vietare. La regola operativa: prima di concludere che una decisione passata vieta
     qualcosa, leggerne le alternative scartate. Una clausola è un riassunto, e i riassunti perdono
     proprio le condizioni.
138. **Un documento superato è più pericoloso dove assegna lavoro che dove afferma un fatto.** Il §7
     del design assegna a `feature/04` la verifica di `testcontainers`. Un'affermazione sbagliata
     dà fastidio quando qualcuno la controlla; un **compito** sbagliato invece si autoconserva,
     perché resta nella lista, sembra da fare, e chi lo esegue non ha motivo di sospettare — ha
     appena letto il documento che glielo assegna. ADR-0020 esisteva da otto giorni ed era corretto:
     nessuno dei due documenti era sbagliato da solo. Quando si supera una decisione, vale la pena
     chiedersi non solo quali affermazioni cadono, ma **quali compiti restano intestati a qualcuno**
     che non saprà di poterli saltare.
139. **Uno strumento che non vede lo stato di un altro non può proteggerlo, e la difesa è l'ordine.**
     `git worktree remove` non conosce le sessioni vive più di quanto conosca i file ignorati: esce
     `0` e ha ragione, perché tutto ciò che git considera suo è stato gestito. Il danno non viene da
     un difetto del comando, viene dal fatto che il suo dominio è più stretto di quello del
     problema. Quando due strumenti si dividono un pezzo di filesystem, l'unica protezione possibile
     non è un controllo — nessuno dei due può implementarlo — ma una **sequenza**: si sgancia prima
     di rimuovere, come si smonta un disco prima di staccarlo. Ed è per questo che una sequenza del
     genere va scritta in una pagina invece che ricordata: un controllo che non esiste non può
     ricordarsela al posto tuo.

Stato aggiornato: decisioni fino ad **ADR-0079**, verifiche fino a **V-073**, note di metodo fino
alla **139**. La suite resta a **143** prove. La PR #4 è stata unita in `develop` dal PO — il merge è
`ca6f3d0` — e questo branch ci parte sopra.

---

## 2026-09-02 — `feature/04`, Task 1: l'appuntamento onorato, e uno zero che stavolta si può leggere

Il primo passo del branch non è codice: è la data che [ADR-0058](Decision.md#adr-0058) aveva fissato
e che [ADR-0078](Decision.md#adr-0078) ha fatto cadere qui. **La 8.0.30 non è pubblicata**
([V-074](Sources.md#v-074)), e il lab resta su 7.0.40 — [ADR-0080](Decision.md#adr-0080).

**La risposta è la stessa di ieri, la verifica no.** V-051 aveva interrogato due canali; ADR-0028 ne
nominava tre, e il terzo — `mongodb/mongodb-community-server` — era rimasto scoperto, dichiarato fra
le riserve. Interrogato adesso, dà zero sulla 8.0.30 e **centosessantaquattro** tag sulla 8.0.29, fra
cui ricostruzioni marcate `20260902T071320Z`, cioè di stamattina. È la differenza fra un canale che
tace e un canale che parla e dice un'altra cosa. Chiusa anche la seconda riserva di V-051: riletto
il changelog, `SERVER-125742` è **ancora** sotto la 8.0.30 e non è slittato altrove
([S-028](Sources.md#s-028)) — il numero da attendere è rimasto quello. La documentazione della patch
è pubblicata, i binari no, e nessuna delle pagine consultate contiene una data prevista.

**Il piano si è sbagliato su se stesso, e il controllo l'ha visto.** Il Task 1 diceva: se la 8.0.30
non c'è, «non serve altro ADR — ADR-0058 prevede questo esito». Scritto V-074, `check_citations.py`
ha rifiutato: una fonte che nessun ADR cita è orfana. La regola aveva ragione, e non per un cavillo:
ADR-0058 aveva **programmato** un controllo, non preso in anticipo la decisione di oggi. Chi arriva
al 16 settembre — la seconda e ultima data — deve poter sapere che il primo controllo è stato fatto
e che cosa ha trovato, senza rifarlo di fretta. ADR-0080 è quella sede, ed estende la procedura da
due canali a tre.

**Note di metodo.**

140. **Un'assenza si legge solo accanto a una prova che il canale è vivo.** `count: 0` da un servizio
     remoto è indistinguibile da `count: 0` di un filtro rotto, di un endpoint deprecato o di un
     repository abbandonato: la risposta è identica in tutti e quattro i casi, ed è la risposta che
     si sperava. La difesa è una **seconda interrogazione di controllo** che deve dare un numero
     diverso da zero — qui `name=8.0.29` che ne dà 164, con marche temporali di poche ore prima. Non
     costa nulla e trasforma un'assenza dichiarata in un'assenza misurata. È il seguito della nota
     91: lì il problema era una risposta ben formata a una domanda diversa, qui è una risposta
     identica a domande diverse. In entrambi i casi la difesa non è leggere meglio, è **chiedere una
     seconda volta in un modo che sappia fallire**.
141. **Una regola che blocca non ha sempre torto: a volte segnala che manca una sede, non che è di
     troppo.** L'abitudine di questo repository, quando un controllo automatico ostacola qualcosa di
     legittimo, è aprire la sede che manca invece di aggirare la regola. Qui il caso si è presentato
     nella forma meno ovvia: era il **piano** a sbagliare, non il controllo. Il piano aveva concluso
     «nessun ADR» ragionando sull'esito — la versione non cambia, nessun file si tocca — mentre la
     decisione da registrare non era sulla versione ma sul **calendario**: due appuntamenti diventati
     uno. Un controllo che rifiuta va guardato prima come ipotesi che come attrito; qui ha trovato un
     buco che nessun essere umano aveva visto, e l'ha trovato contando.

Stato aggiornato: decisioni fino ad **ADR-0080**, verifiche fino a **V-074**, note di metodo fino
alla **141**. La suite resta a **143** prove. Prossimo passo: **Task 2** del
[piano](00-progetto/2026-09-02-piano-feature-04-app-python.md), lo scheletro di `app/`.

---

## 2026-09-02 — `feature/04`, Task 2: uno scheletro che non fa niente, e una guardia rotta apposta

`app/` esiste: `pyproject.toml`, il pacchetto `mongolab` con i quattro strati del §6.1 e
`cli.py`, la suite divisa in unitaria e di integrazione, tre bersagli `make`. Non fa niente, e lo
fa in modo verificabile — **5 prove**, `mypy --strict` verde su 12 file, `make tools-test` sempre a
143. L'ambiente è Python **3.13.15**, con `requires-python = ">=3.13,<3.14"`: l'host ha la 3.14.7,
che il design dichiara troppo recente per garantire il supporto di tutte le dipendenze di test, e il
tetto lo scrive invece di lasciarlo alla fortuna della risoluzione.

**La prova che conta è una guardia.** Percorre i sorgenti di `domain` e `application` con `ast` e
boccia ogni import che non sia della libreria standard o del pacchetto stesso. È il vincolo che
rende la suite unitaria istantanea, e adesso è codice invece che buona intenzione. **Ed è stata
rotta apposta:** aggiunto `import pymongo` a `domain/__init__.py`, la prova è fallita dicendo
`domain/__init__.py importa ['pymongo']`, e la violazione è stata tolta. Senza quel giro la guardia
sarebbe indistinguibile da una che non può fallire.

**Tre trappole schivate scrivendo, e una lasciata dov'era.** La prima: copiare
`tools/pyproject.toml` porterebbe con sé `pythonpath = ["."]`, che lì serve e qui disfarebbe il
layout `src/` — gli import continuerebbero a funzionare, ma dall'albero dei sorgenti invece che dal
pacchetto installato, cioè le prove smetterebbero di verificare ciò che si distribuisce. La seconda:
`testpaths = ["tests"]` avrebbe trascinato l'integrazione dentro la suite veloce dal Task 8 in poi,
senza che nessuno l'avesse deciso; è `tests/unit`, e l'integrazione si chiede per nome. La terza:
`mypy` ha rifiutato due `conftest.py` omonimi, e la soluzione è quella che suggerisce lui —
`__init__.py` nelle directory di test. La quarta non è mia e resta dov'è: `failover-02-maggioranza`
è lungo 23 caratteri e sballa già l'incolonnamento di `make help`, che ne prevede 16. Toccarlo
adesso vorrebbe dire cambiare la resa di tutti i bersagli dentro un commit che parla d'altro.

**Note di metodo.**

142. **Un controllo scritto quando non può fallire va rotto apposta, subito.** La guardia sul
     dominio è passata dal primo istante, perché in quell'istante `domain` conteneva solo una
     docstring. Un controllo che passa perché non ha niente da guardare e un controllo che passa
     perché tutto è a posto danno lo stesso verde, e la differenza si scopre mesi dopo, quando
     serviva. Costa trenta secondi introdurre la violazione, vedere il messaggio e toglierla — e
     quei trenta secondi verificano due cose in una: che il controllo scatti, e che quando scatta
     dica **dove**. Vale il doppio per le guardie architetturali, che per definizione nascono
     davanti a un albero vuoto.
143. **Un codice d'uscita che significa «non ho fatto niente» va tradotto, non nascosto.** Su una
     directory di prove vuota `pytest` esce **5**, che non è un errore e non è un successo: dice
     «non ho raccolto nulla». Lasciarlo passare come fallimento manda a cercare Docker chi non ha
     ancora niente da eseguire; sopprimerlo con un `|| true` insegna che il verde di quel bersaglio
     non vuol dire niente, e l'insegnamento sopravvive al Task 8, quando le prove ci saranno
     davvero. La terza via è tradurlo: intercettare **quel** codice e stampare la frase che spiega
     perché. È il rovescio della nota 135 — lì c'era il messaggio senza il codice, qui il codice
     senza il messaggio — e la regola è la stessa vista dall'altro lato: le due cose servono a due
     lettori diversi, e nessuna delle due copre l'altra.

Stato aggiornato: decisioni fino ad **ADR-0080**, verifiche fino a **V-074**, note di metodo fino
alla **143**. Le suite: **143** prove per gli strumenti, **5** per l'applicazione. Prossimo passo:
**Task 3** del [piano](00-progetto/2026-09-02-piano-feature-04-app-python.md), gli otto eventi
congelati e le cinque porte.

## 2026-09-02 — `feature/04`, Task 3: otto eventi congelati, cinque porte, e una guardia che si è rivelata superflua

Il dominio c'è: `modelli.py` con i dati che le porte si scambiano, `eventi.py` con gli otto eventi
del §6.3, `porte.py` con le cinque `Protocol` del §6.2. Nessun import di terze parti — la guardia
del Task 2 lo verifica adesso su codice vero e non più su un albero vuoto. **19 prove** per
l'applicazione, `mypy --strict` verde su 16 file, `make tools-test` sempre a 143, `docs-check`
pulito.

**Tre scelte prese scrivendo, e scritte dove servono.** La prima: gli eventi hanno una base
`Evento` che porta un solo campo, `istante`. Serve a dare a `EventSink.emit` un tipo solo da
accettare, e costa l'ordine dei parametri — `istante` viene sempre per primo. La seconda:
quell'istante è un **campo**, non una chiamata all'orologio dentro l'evento. È la condizione che
rende esatta un'asserzione con `FakeClock` invece che una tolleranza, ed è anche la differenza fra
il momento in cui il fatto è accaduto e quello in cui qualcuno si è ricordato di registrarlo — che
sotto carico è proprio la latenza che si sta misurando. La terza: `BackupTool.restore` restituisce
un `Iterator[Progress]` come `dump`, mentre il design nomina solo il tipo di ritorno di `dump`. Il
copione mostra anche il restore mentre avviene, e due firme diverse per due operazioni simmetriche
costringerebbero `presentation` a due strade dove ne basta una. La ragione sta nella docstring, non
qui: chi legge il codice deve trovarla lì.

**La guardia rotta apposta ha risposto una cosa che non mi aspettavo.** Applicando la nota 142 al
controllo riflessivo sugli eventi — quello che li scopre invece di elencarli — ho introdotto un
nono evento mutabile per vederlo fallire. Non è fallito: Python si è rifiutato di creare la classe,
`TypeError: cannot inherit non-frozen dataclass from a frozen one`. L'asserzione su `frozen` non
poteva fallire, perché il linguaggio la garantisce già a partire dalla base congelata; e per la
stessa ragione non poteva fallire quella sull'ordine dei campi, dato che i campi della base
precedono sempre quelli di chi eredita. Restava viva solo `slots`, che si dimentica in silenzio: un
nono evento `frozen=True` senza `slots=True` nasce senza protestare, e le sue istanze tornano ad
avere un `__dict__`. Quella variante ha fatto fallire due prove nominando la classe colpevole. Il
controllo è stato riscritto in due: uno sulla base — l'unico punto dove `frozen` e l'ordine si
possono ancora perdere, e infatti togliendo `slots=True` a `Evento` fallisce — e uno sulle
sottoclassi che asserisce solo ciò che può ancora andare storto.

**Il limite dei `Protocol` a runtime è scritto come prova, non come commento.** Le cinque porte sono
`@runtime_checkable` perché una prova mostri che a un oggetto incompleto la porta si chiude. Ma
`isinstance` contro un `Protocol` guarda i **nomi** dei metodi, non le firme: un orologio con
`sleep(self)` senza argomenti passa il controllo a runtime e viene bocciato da `mypy`. La prova che
lo dice **asserisce che quell'oggetto passa** — è verde, e sarebbe la prima a fallire se un giorno
Python stringesse la regola. Il guardiano vero resta `make app-check`; questa riga dice perché.

**Note di metodo.**

144. **Rompere una guardia apposta può rivelare che è superflua, non che è debole.** La nota 142
     prescrive di introdurre la violazione e vedere il messaggio. Ci sono tre esiti, non due: il
     controllo scatta e va bene; il controllo tace e va corretto; oppure **la violazione non è
     costruibile**, perché il linguaggio o il compilatore la vietano prima. Il terzo esito è il più
     facile da leggere male, perché somiglia al primo: entrambi finiscono con la suite verde. La
     differenza è che nel terzo caso l'asserzione è decorazione — controlla il compilatore, e chi
     la legge crede che stia sorvegliando qualcosa che invece nessuno può violare. Va tolta, e va
     tolta **nominando l'esperimento** che l'ha dimostrata superflua: senza, il prossimo lettore la
     riaggiunge in buona fede. Quel che resta è la sola proprietà che può ancora perdersi, e su
     quella la guardia va vista fallire davvero.
145. **Un limite noto si scrive come prova che passa, non come commento.** Che `isinstance` contro
     un `Protocol` guardi i nomi e non le firme è una frase che in un commento invecchia senza
     dirlo. Scritta come prova — un oggetto con la firma sbagliata che **supera** il controllo, e
     l'asserzione che dice proprio questo — diventa due cose insieme: documentazione che il lettore
     incontra dove serve, e sentinella che fallirebbe il giorno in cui il comportamento cambiasse.
     Costa una prova verde in più, e la si paga volentieri: è l'unico modo di far sì che un buco
     conosciuto resti conosciuto anche quando chi lo conosceva non c'è più.

Stato aggiornato: decisioni fino ad **ADR-0080**, verifiche fino a **V-074**, note di metodo fino
alla **145**. Le suite: **143** prove per gli strumenti, **19** per l'applicazione. Prossimo passo:
**Task 4** del [piano](00-progetto/2026-09-02-piano-feature-04-app-python.md), i doppi in memoria —
non mock, ma implementazioni vere delle porte.

---

## 2026-09-03 — `feature/04`, fuori dai task: la documentazione dell'applicazione, e tre modi di sbagliare che si assomigliano

Il PO ha chiesto una cosa che il piano non prevedeva, e aveva ragione a chiederla: molto di quello
che era stato spiegato scrivendo il dominio — perché `frozen` non basta, perché `isinstance` contro
un `Protocol` guarda i nomi e non le firme, perché il listener di PyMongo deve tacere e uscire — è
materiale didattico, ed è **esattamente** ciò che il talk esiste per trasmettere. Viveva in tre
posti dove invecchia male: nelle docstring, dove lo legge solo chi apre quel file; qui dentro, che è
cronologico e non si consulta per argomento; e in chat, che non è un posto.

**Nove pagine in `app/docs/`**, e [ADR-0081](Decision.md#adr-0081) che dice perché stanno lì e non
in `docs/06-sviluppo/`. Cinque sui principi — l'architettura esagonale, le porte e i doppi, gli
eventi congelati, la concorrenza dei listener, i tipi e le guardie — più un registro di sviluppo
dell'applicazione raccontato per task invece che per giornata, una mappa delle decisioni che la
vincolano, un `Sources.md` proprio e un indice.

**Perché non in `docs/`.** Due ostacoli, uno di lettore e uno di macchina. `docs/06-sviluppo/` ha un
altro lettore — chi ha visto il talk e non aprirà mai `app/src/` — e le sue due pagine
sull'applicazione sono promesse al Task 17, cioè dopo che il codice di cui parlano sarà già scritto.
L'ostacolo di macchina è più interessante: le fonti di queste spiegazioni sono documentazione di
linguaggio e di strumenti, che **nessun ADR cita né deve citare**, perché sono vincoli del
linguaggio e non scelte del progetto. Messe in `docs/Sources.md` sarebbero tutte orfane, e
`check_citations.py` avrebbe bocciato la build. La regola non aveva torto: stava dicendo che quelle
voci non appartengono a quel registro. Prefissi distinti — `A-` per le fonti esterne, `M-` per le
misure — e le voci canoniche si puntano, mai si copiano.

**Una citazione falsa, presa per caso.** Scrivendo `app/docs/Sources.md` avevo attribuito ad
[ADR-0024](Decision.md#adr-0024) la regola «il registro operativo non si riscrive». ADR-0024 dice
tutt'altro: parla della gerarchia delle fonti. E **nessun ADR** enuncia quella regola — è una pratica
costante del repository, con il precedente di [ADR-0068](Decision.md#adr-0068) («resta com'è, con la
sua data»), ma non è mai stata scritta come decisione. Il rimando è stato sostituito con un rinvio
alla pratica e a quel precedente.

**Una misura che ha corretto la voce di ieri.** Il Task 3 aveva scritto che senza `slots` gli eventi
«tornano ad avere un `__dict__` in cui due thread possono scriversi di nascosto». Misurato: il
`__dict__` c'è, ma l'assegnazione normale resta bloccata da `frozen`; passano solo
`object.__setattr__` e la scrittura diretta nel `__dict__`. La formulazione giusta è «`frozen`
protegge da una distrazione, `slots` protegge anche da chi conosce la scorciatoia». Questa voce non
si riscrive: la correzione sta in `app/docs/Sources.md` (M-003), nella pagina sugli eventi, e nella
docstring della prova, che portava la stessa frase troppo larga.

**Il controllo dei collegamenti è stato esteso, ed è servito.** `make docs-check` esegue ora
`check_links.py docs app/docs README.md`. Al primo passaggio, su nove pagine nuove e più di sessanta
rimandi ad ancore di `Decision.md` e `Sources.md`, un solo collegamento è risultato rotto — e non
era un'ancora sbagliata ma un rimando a una cartella invece che a un file. Fino a quel momento
**nessuno di quei sessanta rimandi era mai stato verificato**, compreso `#adr-0068` scritto mezz'ora
prima.

**Note di metodo.**

146. **Una citazione plausibile è più pericolosa di una mancante.** Un'affermazione senza fonte si
     vede: è nuda, e chi legge sa di doversi fidare dell'autore. Un'affermazione con accanto
     `[ADR-0024]` sembra già verificata, e nessuno la apre — men che meno in un repository dove
     citare è la norma, perché lì la presenza del rimando è il segnale di qualità e smette di essere
     una domanda. La difesa non è citare di meno, è **aprire il documento nel momento in cui si
     scrive il numero**, non dopo: il numero giusto si ricorda quasi sempre, e «quasi sempre» è
     precisamente la frequenza con cui questo errore passa. Vale il doppio quando si cita a memoria
     un documento che si è scritto, perché la fiducia nella propria memoria è più alta e la memoria
     non lo sa.
147. **Quando un controllo rifiuta materiale legittimo, la sede che manca può essere un registro
     intero, non una voce.** La nota 141 aveva stabilito che un controllo che ostacola qualcosa di
     legittimo va guardato come ipotesi: di solito segnala che manca una sede, e la sede era un ADR.
     Qui la stessa domanda ha dato una risposta di taglia diversa. Non mancava una voce in
     `Sources.md`: mancava un **secondo registro**, con un proprio spazio di numerazione, perché le
     fonti che non appartenevano lì non erano una o due ma un'intera categoria — la documentazione
     del linguaggio, che nessuna decisione di progetto cita né deve citare. Il segnale che distingue
     i due casi è **quante voci** il controllo rifiuterebbe: una è una dimenticanza, tutte quelle di
     un tipo sono una sede mancante. E aprire il secondo registro impone subito una scelta che
     conviene fare bene la prima volta, cioè prefissi diversi: due registri con la stessa
     numerazione producono `S-042` ambigui, e l'ambiguità arriva quando qualcuno cita di fretta.
148. **Un controllo che riceve i percorsi da esaminare non fallisce su ciò che non gli hanno dato:
     tace.** `check_links.py` prende i percorsi come argomenti, ed è la scelta giusta — decidere da
     sé che cosa guardare vorrebbe dire indovinare. La conseguenza è che un albero di documentazione
     nuovo nasce **invisibile**: nessun errore, nessun avviso, il verde di sempre. È la stessa forma
     della nota 142 — un controllo che passa perché non ha niente da guardare — con la differenza
     che qui il materiale c'è e la lacuna sta nella riga del `Makefile`. La regola operativa:
     **creare una cartella di documentazione e aggiungerla al bersaglio sono lo stesso atto**, e la
     verifica che l'atto sia compiuto è banale — introdurre un rimando rotto apposta e vedere il
     controllo nominarlo. Senza, la prima cosa che si scopre è quanti collegamenti erano rotti da
     mesi.

Stato aggiornato: decisioni fino ad **ADR-0081**, verifiche fino a **V-074**, note di metodo fino
alla **148**. Le suite: **143** prove per gli strumenti, **19** per l'applicazione. Prossimo passo:
**Task 4** del [piano](00-progetto/2026-09-02-piano-feature-04-app-python.md).

---

## 2026-09-03 — `feature/04`, Task 4: i doppi, e tre modi in cui un doppio può mentire

Cinque doppi, uno per porta, in `app/tests/doppi/`: `InMemoryStore`, `FakeInspector`, `FakeBackup`,
`FakeClock`, `RecordingSink`. Sono scritti **prima** dei casi d'uso che dovranno verificare — i Task
5 e 6 fanno TDD contro di loro — e la ragione è la stessa per cui si scrive prima la prova: un
doppio disegnato guardando il codice sotto prova concorda con lui per costruzione. Le prove
dell'applicazione passano da **19 a 54**.

La regola era già scritta in `app/docs/02-porte-e-doppi.md` prima che i doppi esistessero: **un
doppio implementa il comportamento, un mock registra le chiamate**. `InMemoryStore` conserva davvero
i documenti, li filtra davvero, li impagina davvero. `FakeClock` fa passare il tempo per davvero.
Scrivendoli è emerso che la regola ha un rovescio, ed è il rovescio che ha insegnato qualcosa.

**Il rovescio: che cosa fa un doppio quando non sa.**

`InMemoryStore` parla un dialetto piccolo — uguaglianza su campi di primo livello, `$match`,
`$limit`, `$count` — e tutto il resto solleva `NonSupportato` nominando ciò che non sa fare. La
tentazione opposta non è restituire un risultato sbagliato: è **ignorare in silenzio** l'operatore
che non si conosce. Un `$gt` ignorato restituisce tutti i documenti, la prova che lo usa diventa
verde, e nessuno ha scritto una riga di codice difettoso. Il difetto è nell'attrezzo di misura.

Che il rifiuto sia verificato quanto il comportamento non è un'opinione: rompendo `_corrisponde`
perché restituisse sempre `True` falliscono **sette** prove, e due delle sette falliscono con
`DID NOT RAISE NonSupportato` ([M-006](../app/docs/Sources.md#m-006)). Terzo esito della nota 144 —
la guardia c'è e si è vista sparare.

**Diversamente dal previsto — avevo rifiutato ciò che andava implementato.**

La prima versione di `InMemoryStore` rifiutava anche `{"campo": None}`, con questa motivazione
scritta nella docstring: `dict.get` restituisce `None` per un campo assente, quindi arriverebbe alla
semantica di MongoDB **per caso**, e per caso è il modo peggiore di essere giusti. Il ragionamento
sembrava solido finché non ho aperto il manuale: «The `{ metacritic : null }` query matches
documents that contain the `metacritic` field with a `null` value **or** do not contain the
`metacritic` field» ([A-006](../app/docs/Sources.md#a-006)).

Quella semantica è **dichiarata**. Non è un caso: è la regola, e una regola dichiarata si implementa
deliberatamente, con la citazione accanto e la prova che la fissa. Rifiutarla era la scelta più
debole, non la più prudente. Il rifiuto è rimasto dov'era giusto, cioè sul confronto con un
sottodocumento intero, che MongoDB risolve «including the field order»
([A-007](../app/docs/Sources.md#a-007)) mentre `dict` di Python l'ordine lo ignora.

Le due decisioni sembrano opposte e obbediscono allo stesso criterio, che è la nota 150.

**Diversamente dal previsto — una riga che cambia *quando*, e nessun tipo se ne accorge.**

`FakeBackup.dump` registra la richiesta e **restituisce** un generatore, invece di essere una
funzione generatrice. Scritta con `yield from` nel corpo — la forma che viene più naturale — la
chiamata non eseguirebbe niente: «The execution starts when one of the generator's methods is
called» ([A-005](../app/docs/Sources.md#a-005)). Nel doppio vuol dire che la richiesta non viene
registrata; nell'adattatore del Task 9 vorrà dire che `mongodump` non parte.

Rotta apposta, la forma sbagliata fa fallire **una** prova e lascia `mypy --strict` **verde**: le
due forme hanno lo stesso tipo annotato, `Iterator[Progress]`
([M-007](../app/docs/Sources.md#m-007)). Insieme a M-004 — `isinstance` contro un `Protocol` accetta
una firma sbagliata — compone un promemoria in due direzioni: mypy è l'unico posto in cui la
conformità alle porte è verificata, e non verifica tutto.

**Una riserva scritta male, e la misura che l'ha corretta.**

Scrivendo M-006 avevo aggiunto una riserva plausibile: la misura mostra che *quelle* prove reggono a
*quella* rottura, e non ad altre — per esempio un `$limit` che tagliasse dalla coda invece che dalla
testa. Sono andato a controllare prima di lasciarlo scritto: la prova sull'aggregazione asserisce
`[1, 2]`, quindi un `$limit` dalla coda **fallirebbe**. L'esempio era falso.

Cercando una rottura davvero scoperta l'ho trovata al secondo tentativo: togliendo da `_come_intero`
il rifiuto dei booleani le prove restano **54 verdi**, perché nessuna chiede `{"$limit": True}`.
Quel rifiuto è oggi una precauzione non verificata, ed è scritto nella riserva al posto
dell'esempio inventato.

**Che cosa è stato rimandato, e perché non è un debito.**

`$group` non c'è: nessuna prova l'ha chiesto. Un `topology()` che solleva non c'è: al Task 6 un
cluster irraggiungibile si racconta con una topologia senza primario. Uno store che fallisce le
scritture non c'è, e il Task 5 lo chiederà — arriverà allora, insieme alla prova che ne ha bisogno.
Ogni messaggio di `NonSupportato` dice per nome che cosa manca e che cosa farne, così chi lo incontra
non deve indovinare se sia una dimenticanza.

**Note di metodo.**

149. **Un doppio che tace su ciò che non sa è più pericoloso di uno che non c'è.** Un doppio
     mancante si nota: il codice non compila, la prova non parte. Un doppio che riceve un operatore
     che non conosce e lo ignora restituisce un risultato plausibile, e la prova diventa verde **per
     il motivo sbagliato** senza che nessuno abbia scritto una riga di codice difettoso — il difetto
     è nell'attrezzo di misura, che è il posto in cui si guarda per ultimo. La regola operativa è
     che ogni doppio dichiari il proprio dialetto e sollevi su tutto il resto, **nominando** ciò che
     non sa fare e dicendo che cosa farne: insegnarglielo insieme alla prova che lo verifica, mai
     riscrivere la prova per chiedergli qualcosa di più semplice. E il rifiuto va provato come il
     comportamento: senza un `pytest.raises`, il silenzio torna alla prima distrazione.
150. **Fra due imitazioni ugualmente ovvie, la fonte dice quale è giusta; se nessuna lo è, si
     rifiuta.** Imitare un sistema esterno costringe a scegliere nei punti in cui l'ovvio del
     linguaggio ospite diverge dall'originale, e i due casi vanno separati prima di decidere. Se
     l'originale **dichiara** il proprio comportamento — `{campo: null}` prende anche i documenti
     senza quel campo — allora un'implementazione giusta esiste, e la si scrive deliberatamente con
     la citazione accanto: arrivarci per caso e rifiutare per prudenza sono entrambi modi di non
     aver deciso. Se invece l'originale fa qualcosa che il linguaggio ospite non sa fare —
     confrontare documenti rispettando l'ordine delle chiavi — nessuna implementazione ovvia è
     quella giusta, e allora imitare male è peggio che dichiarare di non saper fare. Il discrimine
     non è la difficoltà: è se esista una risposta giusta da scrivere.
151. **Un errore di *quando* non è un errore di tipo.** Una funzione generatrice e una funzione che
     restituisce un generatore hanno la stessa annotazione, `Iterator[T]`, e `mypy --strict` le
     accetta entrambe; ma la prima non esegue niente finché qualcuno non scorre il risultato. Ogni
     effetto che la porta promette **alla chiamata** — registrare, avviare un processo, prendere un
     lock — sparisce senza che un tipo se ne accorga. La regola pratica è che quando una porta
     promette «avvia X e produce l'avanzamento mentre procede», l'implementazione fa l'avvio nel
     corpo e **restituisce** l'iteratore; e la prova che lo verifica è quella che chiama senza
     scorrere. Vale in generale: i sistemi di tipi controllano *che cosa*, quasi mai *quando*.
152. **Anche una riserva è un'affermazione, e va misurata come le altre.** Scrivere «questa misura
     non copre X» è il gesto più onesto della pagina, ed è proprio per questo che nessuno lo
     verifica: la modestia sembra al riparo dall'errore. Non lo è — un esempio di rottura scoperta
     inventato a tavolino può essere falso, e il mio lo era: la prova che credevo cieca vedeva
     benissimo. È la nota 146 applicata al proprio codice invece che alle proprie citazioni, con
     l'aggravante che qui il documento da aprire è la suite, e basta un minuto. Il modo di trovare
     una lacuna vera è **rompere e guardare**, non immaginare; e quando si rompe a caso si scopre
     l'altra faccia della cosa, cioè che una guardia scritta per prudenza e mai provata sopravvive
     alla revisione ma non alla mutazione.

Stato aggiornato: decisioni fino ad **ADR-0081**, verifiche fino a **V-074**, note di metodo fino
alla **152**. Le suite: **143** prove per gli strumenti, **54** per l'applicazione. Prossimo passo:
**Task 5** del [piano](00-progetto/2026-09-02-piano-feature-04-app-python.md), il generatore di
carico — che chiederà al doppio la prima cosa che oggi non sa fare: fallire.

---

## 2026-09-03 — `feature/04`, Task 5: il carico e i tentativi, un percentile che non era un numero, e una rottura che non fallisce

`WorkloadRunner` è il primo caso d'uso vero dell'applicazione: genera scritture, ritenta quelle che
falliscono, misura quanto ci mettono, e racconta tutto emettendo eventi. Non sa che esiste MongoDB —
parla con `DocumentStore`, `Clock` ed `EventSink`, e con nient'altro. Le prove
dell'applicazione passano da **54 a 106**, `mypy --strict` verde su 25 file.

Il debito che il Task 4 aveva dichiarato per nome è stato pagato qui: nessun doppio sapeva rompersi,
e una politica di tentativi non è provabile contro un archivio che riesce sempre. Sono nati
`ArchivioCheRompe` e `ArchivioLento`, che non riscrivono `InMemoryStore` ma lo **avvolgono** —
e si compongono fra loro, perché ciascuno annota l'archivio interno con la porta e non con la
classe. È la regola del repository applicata alla lettera: la capacità si aggiunge insieme alla
prova che ne ha bisogno, mai semplificando la prova.

**Il rosso c'era, ma era povero.**

Le prove scritte per prime fallivano tutte con un `ModuleNotFoundError`. È un rosso vero, ma dice
«manca tutto», non «questa guardia serve». Alla prima esecuzione dopo l'implementazione la suite è
passata intera, e a quel punto la domanda onesta non è «è verde?» ma «quali di queste prove
avrebbero visto un errore?». La risposta si compra solo rompendo: cinque rotture deliberate, una
alla volta, con ripristino da copia ([M-010](../app/docs/Sources.md#m-010)).

La quinta ha trovato una guardia **scoperta**. Togliendo da `PoliticaTentativi.attesa_ms` il rifiuto
del primo tentativo — quello che non attende, perché non ha niente da ritentare — la suite è rimasta
verde su 105. Nessuna prova la interrogava. La rottura non ha confermato una difesa: ne ha rivelato
l'assenza, che è il terzo esito della nota 144 nella sua forma più utile. La prova
`test_l_attesa_del_primo_tentativo_non_esiste` è nata lì, e da allora sono 106.

**Diversamente dal previsto — la quarta rottura non fallisce, si pianta.**

Il §6.3 del design impone che i worker non tocchino la TUI: pubblicano su una `queue.Queue`, e un
thread solo drena. `WorkloadRunner` applica la stessa disciplina un livello più in basso — i worker
non toccano il **sink** — e per sapere quando smettere di drenare conta le sentinelle: ogni worker,
qualunque cosa accada, mette in coda un `None` come ultimo gesto, dentro un `finally`.

Spostando quel `put` fuori dal `finally` mi aspettavo un rosso. Ho ottenuto un blocco. Il worker
muore prima di segnalare, il chiamante aspetta un `None` che non arriverà, e la suite resta ferma al
68 % finché il `timeout` non la uccide: `Error 143`. Nessun `FAILED`, nessun messaggio, nessun punto
del codice indicato.

Ai tre esiti della nota 144 se ne aggiunge un quarto, ed è il più difficile da leggere, perché
somiglia a un problema della macchina molto più che a un difetto: davanti a una suite che non torna
si pensa a Docker, alla rete, al portatile.

**Diversamente dal previsto — «p95» non era un numero.**

Avevo scritto `percentile` come una cosa ovvia. Poi ho misurato. Su un campione con un gradino — 95
latenze da 1 ms, poi 50, 60, 70, 80 e 900 — il novantacinquesimo percentile vale **1,0** per rango
più vicino, **3,45** con `statistics.quantiles(method='inclusive')`, **47,55** con `'exclusive'`; la
media, per confronto, 12,55 ([M-009](../app/docs/Sources.md#m-009)). Quarantasette volte l'uno
dall'altro, e nessuno dei tre sbaglia: rispondono a tre domande diverse. Le due forme di `quantiles`
stimano un quantile della popolazione e per farlo interpolano, e la documentazione lo dichiara
apertamente — «if a cut point falls one-third of the distance between two sample values, 100 and
112, the cut-point will evaluate to 104» ([A-009](../app/docs/Sources.md#a-009)).

La scelta non è cambiata: rango più vicino, perché ogni numero che finisce su una slide deve poter
essere ritrovato nel campione. È cambiato il suo statuto, da abitudine a decisione documentata, con
la fonte accanto e con la riserva scritta, che è scomoda: su quel campione il p95 per rango cade in
cima al pianerottolo e della coda non dice niente. Lì la coda la mostra il p99 (80,0) e la dice
tutta il massimo (900,0). È la ragione per cui il riepilogo porta **sei** numeri e non uno.

Nello stesso conto è caduta una domanda che poteva restare un dubbio: `ceil` su un prodotto in
virgola mobile è la combinazione in cui un ulp diventa un rango sbagliato di uno. Verificato contro
l'aritmetica esatta di `Fraction` su cinque quantili e duecentomila taglie di campione: zero
divergenze ([M-008](../app/docs/Sources.md#m-008)). Con la riserva giusta — è una verifica esaustiva
**su un intervallo**, non una dimostrazione.

**Lo zero che sembra una misura.** La prima stesura del riepilogo restituiva latenze a zero quando
non c'era nessun campione. Un p95 di zero millisecondi su una corsa in cui tutto è fallito legge
«velocissimo» dove la verità è «mai arrivato». Ora è `latenze=None`, e `riassumi` su un campione
vuoto solleva invece di inventare.

**Un aiutante di prova che spegneva il controllo.** Il filtro `_specie(eventi, WriteSucceeded)`
tornava `list[Evento]`, e `mypy --strict` ha bocciato **dieci** asserzioni in un colpo:
`"Evento" has no attribute "durata_ms"`. A runtime sarebbero passate tutte. La correzione è un
parametro di tipo — `def _specie[E: Evento](eventi: list[Evento], tipo: type[E]) -> list[E]`, PEP 695,
che mypy 1.13 su Python 3.13.15 accetta senza cerimonie.

**Che cosa resta aperto, dichiarato.** La saturazione di `maxPoolSize` è materiale didattico del
design, e qui non si può misurare: contro `InMemoryStore` non c'è nessun pool da saturare. Resta il
gancio — il parametro `scrittori` — e la misura è del Task 16, dove andrà guardata anche la coda,
che con `maxsize=0` è illimitata ([A-010](../app/docs/Sources.md#a-010)). E un avvertimento che vale
la pena portarsi dietro: oggi la violazione del §6.3 è vista *per quello che è* da **una sola**
prova, quella che confronta gli identificatori di thread; le altre cinque che falliscono insieme a
lei lo fanno per effetto collaterale, perché i conteggi vivono nel ciclo di drenaggio.

**Note di metodo.**

153. **Una rottura deliberata ha un quarto esito, e non fallisce: pianta.** La nota 144 ne elencava
     tre — la guardia scatta, la guardia tace, l'oggetto non è più costruibile. Ne manca uno, e si
     vede solo rompendo codice concorrente: togliendo la garanzia che un worker segnali sempre la
     propria fine, la suite non produce nessun `FAILED`, nessun messaggio, nessun punto del codice
     indicato — resta ferma finché un `timeout` non la uccide, e l'unica traccia è un codice
     d'uscita. È l'esito più insidioso perché **un blocco senza messaggio somiglia a un guasto
     dell'ambiente**: la reazione naturale è sospettare Docker, la rete, la macchina. La regola
     pratica ne discende: le prove concorrenti si eseguono sempre sotto un `timeout`, e il primo
     sospetto davanti a una suite che non torna dopo una modifica è la modifica, non il portatile.
154. **Un percentile senza la sua definizione non è un numero.** «p95 = 47,55 ms» sembra un fatto e
     non lo è: sullo stesso campione, tre modi legittimi di calcolarlo danno 1,0, 3,45 e 47,55 —
     quarantasette volte l'uno dall'altro — perché rispondono a tre domande diverse. Chi stima un
     quantile della popolazione interpola, e ottiene un valore che nessuno ha misurato; chi riferisce
     ciò che ha misurato prende un valore osservato, e paga con l'effetto pianerottolo. Nessuno dei
     due sbaglia; sbaglia chi pubblica il numero senza dire quale dei due sta facendo. La regola:
     ogni indicatore aggregato porta con sé la propria definizione, e mai da solo — un percentile che
     non è accompagnato almeno dal massimo è un modo di non guardare la coda.
155. **Zero è la peggiore risposta mancante, perché ha la faccia di una misura.** Restituire `0.0`
     per una latenza che non è stata misurata, `0` per un conteggio che non è stato fatto, una lista
     vuota per una domanda a cui non si è risposto: sono tutti valori che attraversano i controlli di
     tipo, si sommano, si stampano e si mediano. Un p95 di zero millisecondi su una corsa in cui ogni
     scrittura è fallita legge «velocissimo» dove la verità è «mai arrivato», e a differenza di
     un'eccezione non lo dice a nessuno. È la regola del doppio che solleva (nota 149) portata dai
     doppi ai dati: **dove non c'è una risposta giusta, il tipo deve poter dire di non averla** —
     `None`, o un errore, mai un valore neutro.
156. **Un aiutante di prova che perde il tipo spegne il controllo dove serviva di più.** Un filtro
     che riceve eventi di dieci specie e ne restituisce una sola ha, nella firma ingenua, il tipo
     della lista di partenza; le asserzioni che seguono toccano i campi della specie filtrata, cioè
     esattamente ciò che quel tipo non promette. `mypy --strict` ha bocciato dieci asserzioni in un
     colpo, e a runtime sarebbero passate tutte. La lezione non è «annotare meglio»: è che il codice
     di prova va tipizzato **almeno** quanto quello di produzione, perché è lì che le asserzioni sono
     più specifiche, ed è lì che una perdita di tipo passa inosservata più a lungo — nessuno rilegge
     un aiutante di tre righe. Quando un aiutante *sa* qualcosa che il chiamante userà, glielo si fa
     dire con un parametro di tipo.

Stato aggiornato: decisioni fino ad **ADR-0081**, verifiche fino a **V-074**, note di metodo fino
alla **156**. Le suite: **143** prove per gli strumenti, **106** per l'applicazione. Prossimo passo:
**Task 6** del [piano](00-progetto/2026-09-02-piano-feature-04-app-python.md), l'osservatore della
topologia — che chiederà a `FakeInspector` la sequenza di stati per cui è stato disegnato.

---

## 2026-09-03 — `feature/04`, Task 6: la macchina a stati della topologia, due numeri, e due volte l'arnese che mente

`TopologyWatcher` è l'occhio dell'applicazione sul cluster: guarda la topologia, racconta che cosa è
cambiato, e calcola i due numeri per cui il talk esiste — **quanto è durata l'interruzione** e
**quante scritture confermate sono sparite**. Come tutto ciò che sta in `application/`, non sa che
esiste MongoDB: parla con `ClusterInspector`, `Clock` ed `EventSink`. Le prove dell'applicazione
passano da **106 a 153**, `mypy --strict` verde su 28 file.

Il caso che conta non è uno stato, è un **passaggio**: primario, nessun primario, primario
**diverso**. Tre fotogrammi, e solo il terzo dice «failover» — se torna lo stesso primario è stata
un'interruzione, non un cambio di guardia. La distinzione vive in `Interruzione`, che tiene i due
indirizzi e non solo i due istanti.

I due numeri stanno qui e non nella TUI. Una durata calcolata dentro il ciclo di disegno la si può
provare solo aspettandola davvero; calcolata dietro la porta `Clock`, il valore atteso è **esatto** —
250,0 ms, non «fra 200 e 300» — e la prova gira in millisecondi. È la ragione per cui `Clock` è una
porta, scritta in ADR-0007 e finalmente riscossa.

**Diversamente dal previsto — la regola del §6.2 ha chiesto un nono evento, e una guardia gliel'ha
fatto pagare.**

«Dopo 30 s senza primario, smetti di ritentare» era una frase del design senza codice. Tradurla ha
chiesto che la resa fosse **detta**, e nessuno degli otto eventi del §6.3 sapeva dirla senza mentire:
`WriteFailed` racconta una scrittura che qui nessuno ha tentato, `RetryAttempted` annuncia un
tentativo che non ci sarà — al Task 5 era già stato stabilito, con una prova, che l'ultimo evento di
una resa non può essere un tentativo mai eseguito — e `TopologyChanged` riferisce il cluster, mentre
la resa è una decisione di chi osserva.

Aggiungere l'evento faceva fallire `test_gli_eventi_del_design_sono_otto_e_sono_quelli`, la guardia
scritta al Task 3 perché il dominio non crescesse in silenzio. Ha funzionato esattamente come doveva:
non ha impedito la modifica, ne ha reso **visibile il costo**, e ha costretto la decisione a passare
per la sede giusta. [ADR-0082](Decision.md#adr-0082) porta gli eventi a nove con
`PrimaryWaitAbandoned`, che dichiara `atteso_ms`, `pazienza_ms` e `ultimo_primario`. I due numeri
viaggiano insieme perché «ho aspettato 30 000 ms» non si legge finché non si sa quanta pazienza
c'era, e dal vivo la pazienza si abbassa apposta per non tenere ferma la sala.

**Diversamente dal previsto — due rapporti falsi prima di un rapporto vero.**

Ventun rotture deliberate sull'osservatore, una alla volta, con ripristino da copia
([M-011](../app/docs/Sources.md#m-011)). I primi due esiti erano sbagliati entrambi, e per ragioni
diverse.

Il primo diceva *ventuno su ventuno catturate*, e non aveva eseguito **una sola prova**: era rimasta
in riga di comando un'opzione inesistente, `pytest` usciva con **4** — errore d'uso — per tutte e
ventuno, e lo script leggeva «diverso da zero» come «una prova ha fallito». Il repository conosceva
già il codice 5, «nessuna prova raccolta» ([M-005](../app/docs/Sources.md#m-005)), e non aveva
imparato la lezione generale.

Il secondo attribuiva a rotture diverse la stessa prova fallita, il che è impossibile. Python decide
se ricompilare un modulo confrontando **data di modifica in secondi e dimensione in byte** del
sorgente: le rotture 5 e 6 sono la stessa sostituzione in due punti, producono file identici in
lunghezza — 16 036 byte — e vengono scritte a meno di un secondo l'una dall'altra. La corsa della 6
eseguiva il bytecode della 5. Stessa cosa per la coppia 9/10, entrambe 16 033.

Il segnale d'allarme, tutte e due le volte, è stato lo stesso: **un rapporto troppo pulito**. Ventuno
su ventuno era il risultato più desiderabile e il meno probabile; due mutazioni distinte catturate
dalla stessa identica prova era un'impossibilità logica travestita da conferma.

**Quattro guardie scoperte, e una prova che osservava il risultato giusto per il motivo sbagliato.**

Al netto degli arnesi: diciassette rosse, **quattro mute**. La più istruttiva è la quarta. Una prova
sull'ordine per indirizzo dei `ServerStateChanged` esisteva già; togliendo `sorted` restava verde,
perché in quella prova anche l'ordine di comparsa dei server era alfabetico. La guardia non era
provata — era **accompagnata** da un caso che le dava ragione senza interrogarla. La prova nuova
elenca i server al contrario nella descrizione di partenza.

**Che cosa resta aperto, dichiarato.** Questo osservatore **interroga**, non ascolta: la risoluzione
della misura è l'intervallo di campionamento, e l'errore sulla durata è al più un intervallo. Il
valore predefinito di 500 ms è scelto, non misurato. La misura vera arriva al Task 7, con
`SdamBridge` e i callback di PyMongo, che riferiscono il cambiamento quando accade invece che al
sondaggio successivo. Nessun `ClusterInspector` reale esiste ancora, e per il `TopologyWatcher` non
c'è l'invariante di thread che il Task 5 ha dato al generatore di carico.

**Note di metodo.**

157. **Un codice d'uscita non è un booleano, e trattarlo come tale rovescia il verdetto.** Uno script
     che rompe il codice apposta chiede a `pytest`: «hai fallito?». Ma `pytest` risponde con almeno
     quattro cose diverse — 0 tutto verde, 1 una prova ha fallito, 4 errore d'uso, 5 nessuna prova
     raccolta — e solo l'**1** è la risposta cercata. Un'opzione scritta male produce 4 su ogni
     corsa, e uno script che legge «diverso da zero» come «la guardia ha scattato» riferisce
     ventuno successi senza aver eseguito niente. La regola: un arnese che classifica esiti
     **elenca** i codici che conosce e tratta come guasto proprio quello che non riconosce; e chi lo
     scrive controlla che l'output non sia vuoto, perché un rapporto pieno di verdetti e privo di
     testo è il ritratto di uno strumento che non ha mai chiamato lo strumento vero. La forma più
     generale: **il caso più pericoloso non è la prova che fallisce, è la prova che non è stata
     eseguita** — le due si assomigliano solo se si guarda un numero invece di una riga.
158. **Due modifiche della stessa dimensione, scritte nello stesso secondo, sono la stessa modifica.**
     Python decide se ricompilare un sorgente confrontando la sua data di modifica **in secondi** e
     la sua dimensione **in byte** con quanto registrato nell'intestazione del `.pyc`; il contenuto
     non lo guarda. Un ciclo di rotture deliberate viola entrambe le ipotesi implicite di quel
     controllo: scrive più versioni al secondo, e produce versioni della stessa lunghezza ogni volta
     che sostituisce un nome con un altro della stessa misura. Il risultato è che una corsa esegue il
     bytecode della corsa prima, e il rapporto attribuisce a una mutazione l'effetto di un'altra. La
     regola pratica: chi genera codice a macchina disattiva il bytecode (`PYTHONDONTWRITEBYTECODE=1`)
     e cancella i `__pycache__` prima di ogni corsa. La regola generale: **ogni cache ha un criterio
     di invalidazione, e va conosciuto prima di usarla in un ciclo automatico** — quello di CPython è
     pensato per un umano che salva un file ogni tanto, non per uno script che ne salva venti al
     minuto.
159. **Una guardia si prova solo con un caso in cui, se non ci fosse, si vedrebbe.** Una prova
     asseriva che gli eventi escono in ordine di indirizzo; togliendo l'ordinamento restava verde,
     perché nel suo scenario i server comparivano già in ordine alfabetico. Osservava il risultato
     giusto per il motivo sbagliato: confermava l'ordine senza mai metterlo alla prova. È la forma
     più subdola di prova inutile, perché non è né sbagliata né incompleta — asserisce esattamente
     ciò che deve, e non potrebbe fallire. La regola sta prima della prova, nella sua costruzione:
     **prima di scriverla, si nomina la modifica al codice di produzione che la farebbe fallire**;
     se non se ne trova una, il caso scelto è complice. Per una guardia sull'ordine questo significa
     un ingresso disordinato; per una sul filtro, un elemento da scartare; per una sul limite, un
     valore oltre.
160. **Un numero può sbagliare verso il rassicurante, e può sbagliare verso lo spettacolare: il
     secondo è più difficile da vedere.** La nota 155 diceva di non inventare zeri. Il seguito è che
     l'errore ha due direzioni, e l'attenzione ne guarda una sola. Un'interruzione già in corso al
     primo sguardo, se la si misurasse dall'istante in cui la si è vista, darebbe un minimo:
     sbaglierebbe per difetto, e chi legge lo sospetta. Un'interruzione già chiusa, se ogni sguardo
     successivo ne spostasse la fine, crescerebbe a ogni giro: sbaglierebbe per eccesso, e nessuno lo
     sospetta, perché il numero grosso conferma la tesi che si sta esponendo. Nella prima corsa di
     rotture era il secondo caso a non essere coperto da nessuna prova. La regola: **quando un
     numero finisce su una slide a sostegno di un'affermazione, la prova che serve è quella che lo
     impedirebbe di crescere**, non quella che lo impedirebbe di sparire; e dove il valore onesto non
     esiste, il tipo dice `None` invece di scegliere una direzione.

Stato aggiornato: decisioni fino ad **ADR-0082**, verifiche fino a **V-074**, note di metodo fino
alla **160**. Le suite: **143** prove per gli strumenti, **153** per l'applicazione, `mypy --strict`
verde su 28 file. Prossimo passo: **Task 7** del
[piano](00-progetto/2026-09-02-piano-feature-04-app-python.md), `SdamBridge` — dove le topologie
smetteranno di essere finte, e i callback di PyMongo andranno **osservati**, non solo letti.

## 2026-09-03 — `feature/04`, Task 7: il ponte SDAM, una documentazione che sbaglia un'unità, e una rottura che non rompe

`SdamBridge` è il primo modulo che importa PyMongo davvero, e il punto in cui l'applicazione smette
di **interrogare** il cluster e comincia ad **ascoltarlo**. Quattro ascoltatori — server, topologia,
battiti, comandi — una coda sola, e una regola sola: ogni callback costruisce un evento congelato, lo
deposita, ritorna. Le prove dell'applicazione passano da **153 a 193**, `mypy --strict` verde su 30
file.

La regola non è igiene. La documentazione di PyMongo dice che «Application threads block waiting for
event handlers … to return» ([S-010](Sources.md#s-010)): il thread che aspetta è il monitor del
driver, quello che si accorge della caduta del primario. Un callback che disegna una tabella allunga
**proprio il failover che si sta cronometrando**. Il numero sulla slide diventerebbe più grande per
colpa dello strumento che lo misura — non una degradazione, una falsificazione.

**Quattro classi non sono una scelta di stile.** `ServerListener` e `TopologyListener` dichiarano gli
stessi tre metodi, e il driver smista per `isinstance`. Una classe che le implementasse entrambe
riceverebbe due tipi di evento sulla stessa firma, e dovrebbe distinguerli a mano nel percorso caldo
— esattamente ciò che [ADR-0019](Decision.md#adr-0019) vieta. Separate, la distinzione la fa il
driver, gratis.

**Diversamente dal previsto — la documentazione di PyMongo sbaglia un'unità di misura, e sarebbe
costata una tabella di zeri.**

La docstring di `ServerHeartbeatSucceededEvent.duration` dice «The duration of this heartbeat in
microseconds». Il valore che ci arriva è `round_trip_time`, che viene da `_monotonic_duration`, che
restituisce `max(0.0, time.monotonic() - start)`: **secondi**. Tre passaggi nel sorgente installato,
nessuna lettura alternativa possibile. L'altro evento, `CommandSucceededEvent.duration_micros`, è
invece davvero in microsecondi: due famiglie, due unità, e solo una documentata bene.

Credere alla docstring avrebbe prodotto latenze di battito nell'ordine di 10⁻⁶ ms, che nel riepilogo
dei percentili sarebbero comparse come **zeri**. È la nota 155 — uno zero inventato è la peggiore
risposta mancante — fatta scattare non da una scelta nostra ma da una riga di documentazione altrui.
Il patto di lettura di `app/docs` prevedeva questo caso in astratto («dove le due non concordano, la
riserva è scritta»); è la prima volta che capita, ed è registrato in
[`app/docs/Sources.md`, M-012](../app/docs/Sources.md#m-012) con i tre punti del sorgente.

**Il driver applica a sé stesso la regola di ADR-0019.** Misurando da quale thread arriva ciascun
callback si scopre che server e topologia **non** sono consegnati dal codice che scopre il
cambiamento: quel codice fa `self._events.put(...)`, e un thread di nome `pymongo_events_thread`
drena la coda e chiama i listener. Battiti e comandi invece arrivano sul thread del monitor e su
quello applicativo. Metà dei listener di PyMongo passano quindi dalla stessa forma — coda più
drenatore — che ADR-0019 impone all'applicazione, e nessuna pagina di documentazione lo dice
([M-014](../app/docs/Sources.md#m-014)). Vale come conferma indipendente della decisione, ed è un
punto che il talk può usare: non è un'idea del relatore, è quello che fa il driver.

La regola non cambia per questo. Quel thread è **uno solo**: un callback lento lì accoda tutti gli
altri cambi di topologia, compreso quello che annuncia il primario nuovo.

**Un valore nuovo nel dominio, e stavolta senza ADR.** `RuoloServer.ALTRO`. Il driver conosce
`RSOther`, `RSGhost`, `LoadBalancer`; mandarli su `SCONOSCIUTO` è una traduzione sbagliata proprio
nel momento della demo, perché un membro che riparte sta qualche secondo in `RECOVERING` e il driver
lo chiama `RSOther`. «Sconosciuto» direbbe *il client non ha capito*, mentre il client ha capito
benissimo. I tre stati dell'assenza sono ora distinti: `SCONOSCIUTO` è l'assenza di un'osservazione,
`IRRAGGIUNGIBILE` è un'osservazione, `ALTRO` è il contrario di entrambi. Nessun ADR perché
`RuoloServer` non è enumerato nel design — a differenza dei nove eventi, che al Task 6 avevano
richiesto [ADR-0082](Decision.md#adr-0082) per diventare nove. La guardia esiste dove il design
enumera; dove non enumera, la sede è il registro.

**I tipi hanno impedito una stringa sbagliata a schermo.** I callback non sono tipizzati con le
classi di PyMongo ma con sei `Protocol` scritti qui, che dichiarano solo gli attributi letti. Serve a
provare la traduzione **senza PyMongo vivo**; ma siccome le classi ereditano davvero da quelle del
driver, `mypy --strict` deve dimostrare che le classi vere soddisfino i nostri `Protocol` — un
controllo di compatibilità gratuito, a ogni `make app-check`. Ed è servito subito: la prima stesura
dichiarava `address: tuple[str, int]`, mypy ha rifiutato perché in PyMongo la porta è opzionale, e
senza quel rifiuto la cronaca avrebbe mostrato `mongo-1:None` — che nessun doppio scritto a mano
avrebbe colto, perché chi scrive il doppio la porta ce la mette sempre.

**Ventotto rotture, ventisette rosse, e nessuna prova nuova.** È il contrario del Task 6, dove
quattro guardie su ventuno mancavano: qui le prove erano state scritte contro un contratto già
**misurato**, non contro un'idea del comportamento. La ventottesima è quella che vale: una tabella di
Rich dentro il callback fa fallire la prova cronometrata con tre ordini di grandezza di margine. Il
vincolo di ADR-0019 non è un principio, è una cosa che si vede.

La quindicesima resta verde, e la prima ipotesi è sbagliata. Vedi la nota 161.

**Le protezioni delle note 157–159 c'erano dall'inizio, e la 153 è arrivata lo stesso.** Prima
batteria di rotture costruita con gli arnesi già a posto: esito letto dal codice di uscita mappato
per nome, bytecode disattivato, `__pycache__` cancellati, e la verifica che ogni sostituzione cambi
davvero il file. Nessun falso rapporto. Ma la rottura «`drena` guarda ma non svuota», nella sua prima
forma, era un ciclo infinito: la batteria si è piantata dopo sette minuti senza dire niente. Da lì
una quarta protezione — limite di 90 secondi per corsa, con un esito `APPESO` che ha un nome proprio
e non si confonde con un fallimento.

### Note di metodo

161. **Prima di concludere che manca una guardia, va escluso che manchi la differenza.** Una
     modifica deliberata ha lasciato la suite verde: leggere l'indirizzo del server dalla descrizione
     *di prima* invece che da quella *di dopo*. L'ipotesi ovvia — una guardia scoperta, come nella
     nota 159 — era falsa. Il driver pubblica quel cambio in un punto solo di tutto il suo codice, e
     ricava la descrizione vecchia indicizzando per l'indirizzo di quella nuova: i due lati portano
     **sempre** lo stesso indirizzo, per costruzione. Non sono due letture di cui una giusta, sono la
     stessa lettura scritta in due modi. Le tre uscite della nota 144, e la quarta della 153, danno
     tutte per scontato che una modifica cambi il comportamento; questa è la quinta, e va cercata
     per prima quando una rottura tace. La cura non è inventare una prova: costruire a mano il caso
     che il driver non può produrre farebbe passare la rottura da verde a rossa e sembrerebbe una
     guardia, ma aggiungerebbe copertura senza aggiungere verità. La cura è **verificare
     l'invariante alla fonte e scriverlo dove il codice lo usa**, con file e riga, così che chi
     rifarà la stessa domanda trovi la risposta invece di riscoprirla.
162. **Una soglia si misura prima di scriverla, e si dichiara che cosa non prende.** La prova che
     verifica il vincolo di ADR-0019 confronta il costo di un callback con quello di un inserimento
     in coda, e chiede che il rapporto stia sotto dieci. Il dieci non è un numero tondo scelto a
     occhio: viene da tre misure. Il callback onesto sta a 2,9, stabile su cinque ripetizioni; una
     tabella di Rich lo porta a 883. In mezzo c'è una `f-string`, che arriva a 5,5 e **passa** — cioè
     la prova non prende un caso che il codice vieta. Una soglia a quattro lo prenderebbe, e
     fallirebbe anche su una macchina carica, con un messaggio indistinguibile dal rumore; una prova
     che fallisce a caso viene disattivata da qualcuno, prima o poi. La regola ha due metà, e la
     seconda è quella che di solito manca: si sceglie la soglia dove il vincolo diventa un **danno
     misurabile** — a ottocento comandi al secondo, 386 µs per evento sono 0,31 secondi di CPU per
     ogni secondo di orologio — e si scrive accanto alla prova **che cosa resta fuori**, invece di
     lasciar credere che la copertura arrivi fino al divieto. Una soglia che non dichiara il proprio
     buco è una riserva non scritta, e la nota 152 dice che una riserva è un'asserzione.

Stato aggiornato: decisioni fino ad **ADR-0082**, verifiche fino a **V-074**, note di metodo fino
alla **162**. Le suite: **143** prove per gli strumenti, **193** per l'applicazione, `mypy --strict`
verde su 30 file. Prossimo passo: **Task 8** del
[piano](00-progetto/2026-09-02-piano-feature-04-app-python.md), gli adattatori veri contro uno stack
vero — dove i battiti e i cambi di ruolo, finora costruiti a mano, dovranno arrivare da un cluster
che cade sul serio.

---

## 2026-09-03 — `feature/04`, Task 8: il contratto che ha trovato il bugiardo prima che l'originale esistesse

Il Task 8 è il punto in cui l'applicazione incontra un MongoDB vero: `PymongoStore`,
`PymongoInspector`, un generatore deterministico, e una seconda suite che accende gli stack di
questo repository e ci gira contro — con i `make up-0X` che ci sono, non con un facsimile, perché
[ADR-0020](Decision.md#adr-0020) dice che si prova l'artefatto che il pubblico eseguirà. Le prove
dell'applicazione passano da **193 a 214** unitarie, più **33** di integrazione;
`mypy --strict` verde su **39** file.

La notizia non è che funzioni. È che cosa si è rotto, e quanto era invisibile prima.

**Il primo difetto è saltato fuori senza toccare un cluster.** Il Passo 4 chiedeva di far girare le
prove del Task 4 anche contro l'adattatore vero. L'ordine naturale sarebbe stato: scrivo
l'adattatore, poi condivido le prove. È stato fatto al contrario — prima il file condiviso,
`app/tests/contratto_archivio.py`, eseguito **soltanto** contro `InMemoryStore` — e la prima
esecuzione ha dato `1 failed, 10 passed`. Il doppio rispondeva `[{"quanti": 0}]` a un `$count` su
zero documenti; MongoDB non risponde niente, e nemmeno `$group` con `_id: null` lo fa. Un difetto
che stava lì da quattro task, invisibile perché nessuna prova aveva mai chiesto quel caso, e trovato
da un file che non conteneva ancora una riga di integrazione.

Il modo in cui sarebbe esploso merita di essere scritto: `risultato[0]["quanti"]` dà zero sul doppio
e `IndexError` contro il cluster, cioè la suite veloce resta verde e la demo si rompe al primo
fotogramma, quando la collezione è ancora vuota. È la **nota 155** vista dall'altro lato — lì una
risposta mancante scambiata per uno zero, qui uno zero inventato dove la risposta manca.

**Il secondo bugiardo era l'originale.** `find_page(quanti=0)` restituisce la lista vuota sul doppio
e la collezione intera contro MongoDB: «A `limit()` value of 0 (i.e. `.limit(0)`) is equivalent to
setting no limit». Il valore non lo digita nessuno, ci si arriva per sottrazione — quante righe
restano nella finestra, quanti mancano alla fine dell'elenco — cioè nel caso limite di un calcolo,
che è quello che nessuno prova a mano. In scena sarebbero state cinquantamila righe dove ne erano
state chieste zero.

**Una scelta che tutti consigliano, rifiutata da una misura.** `ordered=False` per il caricamento
massivo stava per essere adottato per abitudine. Ventimila documenti per configurazione, tre giri
alternati sullo stack 01: mediane per lotto fra 2,48 e 2,70 ms **da entrambe le parti**, con il
terzo giro in cui l'ordinato è il più veloce. Non c'è niente da guadagnare, e il predefinito dà in
cambio un errore più semplice da leggere. La riserva è scritta accanto ai numeri: loopback, istanza
singola, niente `w: majority`, niente sharding — le tre condizioni in cui il confronto potrebbe
ribaltarsi sono tutte fuori dalla misura.

**Due trappole della connessione che nessuna pagina dichiara.** `replicaSet=rs0` dall'host contro lo
stack 02 **sano** fallisce dopo 4,2 secondi con `ReplicaSetNoPrimary` e tutti e tre i membri
irrisolvibili, perché il set si annuncia con i nomi di servizio Compose:
[ADR-0021](Decision.md#adr-0021) visto dal lato che fa male, e una diagnosi indistinguibile da un
primario caduto davvero — cioè da quella che il Blocco 2 esiste per mostrare. La seconda è che
`tz_aware` è predefinito a `False`: le date tornano ingenue, il confronto con quelle scritte riesce
lo stesso, e lo sbaglio si vede come un orario storto sullo schermo. Un difetto che non fallisce è
l'unico caso in cui una guardia nel costruttore si giustifica, e `PymongoStore` ne ha esattamente
una.

**Una regola del repository ostacolava una cosa legittima, e mancava la sede.** Le prove accendono
gli stack, `make up-02` legge `PASSWORD_AMMINISTRATORE` dal `.env`, e
[ADR-0056](Decision.md#adr-0056) dice che quel file vive nel checkout principale, non in un
worktree. Copiarlo avrebbe creato una seconda copia di un segreto che invecchia in silenzio;
scrivere un percorso assoluto nelle prove avrebbe messo la macchina di chi sviluppa dentro un file
versionato. Invece di aggirare la regola si è aperta la sede mancante:
[ADR-0083](Decision.md#adr-0083), il collegamento simbolico — il file resta uno, il versionamento
non lo vede, e Compose non sa di nulla perché apre un percorso e il sistema operativo lo segue.

**Il manuale non diceva quello che stavo per fargli dire.** La prima stesura di `_chunk_per_shard`
spiegava che «dalla 5.0 `config.chunks` non contiene più il campo `ns`». Andata a controllare, la
pagina non lo afferma da nessuna parte e non nomina la 5.0 a questo proposito: prescrive l'unione
per `uuid`, e basta. La docstring è stata riscritta separando le due cose — il Tip è del manuale,
l'assenza di `ns` è una constatazione sul 7.0.40 di **questo** repository, dove nessuno dei cinque
chunk ha quel campo e cercarlo restituisce zero senza sollevare. Un difetto silenzioso perfetto:
zero chunk su uno shard che ne ha due, cioè «i dati non sono distribuiti» detto esattamente dove lo
sono.

**Un commento prometteva più di quanto la protezione mantenga.** Il `pyproject.toml` diceva che
`--strict-markers` protegge dagli errori di battitura nei marcatori. Eseguito: `@pytest.mark.stack3`
in un decoratore è intercettato con un errore di raccolta, ma `pytest -m stack3` sulla riga di
comando deseleziona trentatré prove ed esce zero, senza una parola. Il commento adesso dice
entrambe le cose, e il buco che resta è dichiarato accanto alla protezione che non lo copre.

**La rete di sicurezza che nessuno aveva chiesto.** Ogni prova di integrazione riceve un database
usa-e-getta col prefisso `mongolab_prove_`, e `sveglia()` accende lo stack se non risponde: da
`make down-01` a diciannove prove verdi in 8,1 secondi, senza che nessuno digiti `make up-01`. Gli
stack alla fine **non** si spengono, ed è deliberato — fermare uno stack che l'operatore aveva già
acceso sarebbe un effetto che le prove non hanno causato, e chi prepara la demo si troverebbe la
scena smontata da una suite di test.

### Note di metodo

163. **Estrarre un contratto condiviso è già una prova, prima ancora di condividerlo.** Il file che
     raccoglie le verifiche comuni fra un doppio e l'originale è stato scritto per essere eseguito
     in due posti, e ha trovato il primo difetto **eseguito in uno solo**. La ragione è che scrivere
     una verifica pensando «questa deve valere anche contro il server vero» costringe a formularla
     in termini di comportamento osservabile invece che di implementazione, e le domande che ne
     escono sono diverse da quelle che si pongono guardando il doppio. Il valore non sta tutto nel
     confronto: metà sta nel cambio di punto di vista che il confronto obbliga a fare.

164. **Quando esiste già una seconda implementazione corretta, il caso che giustifica una guardia
     non si inventa: si esegue.** La **nota 159** dice che una guardia è provata solo da un caso in
     cui la sua assenza si vedrebbe, e costruire quel caso è di solito la parte difficile. Con due
     implementazioni della stessa porta la difficoltà sparisce: si scrive la verifica, la si fa
     girare da entrambe le parti, e se una passa e l'altra no il caso è già lì. `find_page(quanti=0)`
     è stato scoperto così, e la guardia è stata scritta dopo aver visto la riga rossa.

165. **Una scelta che tutti consigliano va misurata come una qualsiasi.** La **nota 162** dice che
     una soglia si misura prima di scriverla; questa è il caso complementare, ed è più insidioso,
     perché non c'è nessun numero da inventare — c'è un consenso da ereditare. `ordered=False` è la
     raccomandazione standard per il caricamento massivo, e su questo carico non fa differenza. Il
     costo di misurarlo è stato di due minuti; il costo di non misurarlo sarebbe stato una riga di
     codice che nessuno avrebbe mai rimesso in discussione, perché «si sa».

166. **Una constatazione su una versione non è una regola di versione.** Misurare che il 7.0.40 non
     ha un certo campo autorizza a scrivere «sul 7.0.40 quel campo non c'è, misurato». Non
     autorizza a scrivere «dalla 5.0 quel campo è stato tolto», che è un'affermazione su tutte le
     versioni e va cercata nella documentazione — dove, in questo caso, non c'è. La differenza fra
     le due frasi non si vede leggendo, perché entrambe spiegano bene lo stesso codice; si vede il
     giorno in cui qualcuno ci costruisce sopra una decisione su una versione che non ha mai
     provato.

167. **Un commento che descrive una protezione va verificato come la protezione.** Il commento su
     `--strict-markers` era plausibile, utile e sbagliato per metà. Un commento del genere non è
     documentazione: è un'asserzione su un comportamento, e nessuno la rimetterà in discussione
     proprio perché sta accanto alla riga che dovrebbe garantirla. La **nota 152** dice che una
     riserva è un'asserzione; questa aggiunge che anche una rassicurazione lo è, e che si eseguono
     tutte e due.

Stato aggiornato: decisioni fino ad **ADR-0083**, verifiche fino a **V-074**, note di metodo fino
alla **167**. Le suite: **143** prove per gli strumenti, **214** per l'applicazione più **33** di
integrazione, `mypy --strict` verde su 39 file. Prossimo passo: **Task 9** del
[piano](00-progetto/2026-09-02-piano-feature-04-app-python.md).

---

## 2026-09-03 — `feature/04`, Task 9: lo strumento che ha perso cinquantamila documenti ed è uscito zero

Il Task 9 attacca la porta `BackupTool` a `mongodump` e `mongorestore`. È il primo adattatore che
non parla con una libreria ma con un **processo**, e le differenze rispetto a `PymongoStore` vengono
tutte da lì: la credenziale attraversa un confine di sistema operativo invece che una chiamata di
funzione, l'avanzamento è testo da riconoscere riga per riga invece che un valore di ritorno, il
verdetto è un intero che decide qualcun altro, e il processo **sopravvive** a chi lo ha lanciato.
Le prove dell'applicazione passano da **214 a 243** unitarie e da **33 a 43** di integrazione;
`mypy --strict` verde su **42** file.

Tre cose sono state scoperte eseguendo, e nessuna delle tre era nel piano.

**Il motivo scritto nel piano era sbagliato, mentre la regola era giusta.** Il Passo 2 prescrive di
lanciare il processo con gli argomenti in lista e mai con una stringa di shell, «perché una stringa
di shell fa comparire la password nella tabella dei processi di chiunque guardi». La lista è la
scelta giusta. Il motivo no: con `-p <valore>` come **elemento della lista** — nessuna shell
coinvolta da nessuna parte — un `ps -eo args` dentro il container mostra il segreto per intero,
sedici campioni su sedici presi a cinquanta millisecondi l'uno dall'altro. La tabella dei processi
legge `argv`, e ad `argv` non importa da dove è arrivato. Quello che protegge davvero il segreto è
**omettere `-p`**: gli strumenti allora chiedono la password e la leggono dallo `stdin` anche quando
lo `stdin` non è un terminale. La lista resta comunque necessaria, per la ragione che il piano non
nomina — senza shell non c'è nessuno a interpretare uno spazio, un apice o un `$` dentro una
password o dentro un percorso.

**`mongorestore` ha perso cinquantamila documenti ed è uscito zero.** Un restore ripetuto sulla
stessa destinazione ricade su `_id` che esistono già — lo strumento **inserisce**, non fonde — e
dichiara `0 document(s) restored successfully. 50000 document(s) failed to restore.` prima di
restituire **0** al sistema operativo. Chi controlla il processo nel modo in cui si controlla un
processo, cioè guardando l'intero che restituisce, riceve «riuscito». È
[ADR-0077](Decision.md#adr-0077) visto dal lato opposto: lì la regola nasceva guardando gli script
che scriviamo noi, qui è lo strumento ufficiale di MongoDB a scrivere l'avviso e a non cambiare il
codice d'uscita. Da qui [ADR-0084](Decision.md#adr-0084): quando lo strumento di qualcun altro
commette quell'errore, l'adattatore che lo incapsula è il posto in cui si ripara, e
`RestoreIncompleto` mette il verdetto che `mongorestore` non ha messo.

**Quella guardia non è stata progettata: l'ha scoperta il codice che la contiene.** Le prime due
prove di integrazione sul restore davano per **idempotente** un restore ripetuto, e la premessa era
scritta a chiare lettere nella docstring di una di loro, come una cosa ovvia. Eseguite,
`RestoreIncompleto` è stata sollevata, e la parte sbagliata era l'assunzione della prova. È il caso
speculare della **nota 164**: lì una seconda implementazione corretta rivela il difetto
dell'originale, qui il codice di produzione rivela il difetto dell'affermazione fatta dalla prova.

**Il comando arriva dal costruttore, e la ragione è un privilegio.** `SubprocessBackup` non sa come
si raggiunge `mongodump`: lo riceve, `("docker", "exec", "-i", "mongo-rs-1", "mongodump")` dalle
prove sull'host e `("mongodump",)` dal container al Task 12. Se la politica di esecuzione stesse
dentro l'adattatore, l'applicazione containerizzata di [ADR-0012](Decision.md#adr-0012) si
porterebbe dietro una dipendenza dal **socket Docker** — cioè il permesso di comandare il demone che
fa girare l'intero laboratorio — per fare una cosa che dal suo container sa già fare da sé. Un
adattatore che decide come raggiungere lo strumento decide anche, senza volerlo, quali privilegi
servono per usarlo.

**Le prove unitarie lanciano processi veri, e non è purismo.** Metà di ciò che l'adattatore deve
garantire — che il figlio parta alla chiamata e non al primo `next()`, che la password non finisca
fra i suoi argomenti, che l'iteratore abbandonato non lasci un processo orfano — riguarda proprio il
confine col sistema operativo, cioè esattamente la parte che un mock sostituirebbe con la propria
opinione. Un mock che dicesse «sì, ho ricevuto `kill`» non dimostrerebbe che il processo è morto. Al
posto di `mongodump` c'è un programma Python di sei righe che scrive pid e argomenti in un diario,
legge lo `stdin` e stampa su `stderr` **le righe misurate**; il pid nel diario è ciò che permette
alla prova sulla chiusura di chiedere al sistema operativo se quel processo è ancora vivo.

**Sei mutazioni, cinque rosse e una verde.** L'adattatore è stato rotto una volta alla volta —
password rimessa in `argv`, sommario ridotto ad avviso, `dump` trasformata in funzione generatrice,
`kill` tolto, codice d'uscita ignorato, base 1024 cambiata in 1000 — pretendendo che una prova
**precisa** se ne accorgesse. Le prime cinque sono diventate rosse subito. La sesta è rimasta verde,
perché l'unica prova sulle barre usava il formato senza unità di `mongodump`, dove il
moltiplicatore non entra mai in gioco. Le due prove nate da lì giudicano contro la dimensione vera
del file, letta con `stat` dentro il container: `6094260` byte annunciati come `5.81MB`, che in base
1000 farebbero `6.09`.

**La nota 158 si è ripresentata identica, e questo è il fatto interessante.** Alla prima esecuzione
della sesta mutazione `pytest` riportava un numero che nel sorgente su disco non c'era: `1024**2` e
`1000**2` hanno la **stessa lunghezza in byte**, lo script riscriveva il file entro lo stesso
secondo, e il `.pyc` vecchio è stato considerato valido. È esattamente la **nota 158**, scritta al
Task 5 di questo stesso branch, con la sua regola pratica già formulata —
`PYTHONDONTWRITEBYTECODE=1` e pulizia dei `__pycache__`. Non ha impedito niente, perché lo script
delle mutazioni del Task 9 è stato scritto da capo e nessuno rilegge le note di metodo prima di
scrivere venti righe di utilità. Vale la pena registrarlo così com'è: una lezione scritta protegge
chi la ricorda, e uno strumento nuovo non la eredita. La conseguenza è che le tre trappole
dell'arnese — il codice d'uscita che non è un booleano, il `.pyc` condiviso, e la mutazione verde
che era equivalente invece che scoperta — hanno adesso una sede versionata in
[`app/docs/05-tipi-prove-e-guardie.md`](../app/docs/05-tipi-prove-e-guardie.md), accanto alle prove,
che è dove si va a guardare prima di scrivere lo script e non dopo.

### Note di metodo

168. **Il motivo scritto accanto a una regola giusta va eseguito come la regola.** La **nota 167**
     dice che un commento che descrive una protezione è un'asserzione. Questa è la stessa cosa un
     passo prima: il «perché» scritto in un piano è formulato **prima** di misurare, quindi è
     un'ipotesi, e una regola giusta sostenuta da un'ipotesi sbagliata è più pericolosa di una
     regola assente — perché chi la legge smette di cercare. «Gli argomenti in lista, altrimenti la
     password finisce nella tabella dei processi» avrebbe fatto scrivere il codice giusto e
     smettere di pensare al punto esatto in cui il codice giusto non basta.

169. **Rompere il codice a mano trova l'asserzione che non hai scritto.** Una suite verde dice che
     le prove che ci sono passano, non che le prove che servono esistano. Il modo più economico di
     misurare la differenza è cambiare un comportamento alla volta e pretendere che una prova
     **nominata in anticipo** diventi rossa: se resta verde, non è la mutazione a essere innocua, è
     la prova a non esserci. Sull'adattatore del Task 9 il conto è stato cinque su sei, e la sesta
     mancava proprio dove il codice faceva la cosa meno ovvia.

170. **Una verifica giudicata contro una copia della stessa scelta non è una verifica.** La prova
     sulla conversione delle unità stava per confrontare un `1024**2` scritto nella prova con un
     `1024**2` scritto nel codice: due copie della stessa decisione coincidono sempre, anche quando
     la decisione è sbagliata. Il metro deve venire da fuori — qui la dimensione vera del file letta
     con `stat`. Vale ogni volta che una prova contiene una costante che il codice contiene uguale:
     quella costante non sta verificando niente.

171. **La docstring di una prova è un'asserzione, e può essere lei la parte sbagliata.** Il verso
     abituale è che la prova giudica il codice, e quando una prova diventa rossa la prima ipotesi è
     sempre che il codice sia da correggere. Qui è successo l'opposto: `RestoreIncompleto` ha
     bocciato una premessa scritta nella docstring della prova — «il restore è idempotente sulla
     stessa destinazione» — che era falsa e che nessuno avrebbe rimesso in discussione, perché il
     testo di una prova è la parte del repository che meno persone rileggono. La regola pratica:
     davanti a una prova rossa scritta contro codice nuovo, prima di correggere il codice si legge
     ad alta voce che cosa la prova **afferma**, e ci si chiede chi l'ha verificato. La **nota 164**
     dice che una seconda implementazione corretta rivela il difetto della prima; questa è il caso
     ulteriore, in cui a rivelare il difetto della prova è il codice che la prova doveva giudicare.

172. **Una lezione scritta protegge chi la ricorda, non chi scrive lo strumento dopo.** La **nota
     158** — due modifiche della stessa dimensione nello stesso secondo condividono il `.pyc` — è
     stata scritta al Task 5 e reincontrata identica al Task 9, sullo stesso branch, dalla stessa
     persona. Non ha impedito niente, perché lo script delle mutazioni è stato riscritto da capo e
     nessuno rilegge il registro prima di scrivere venti righe di utilità. La conseguenza operativa
     non è «rileggere di più»: è che una lezione utile va messa **dove verrà letta** — accanto al
     codice a cui si applica, non solo nel registro che la spiega. Le tre trappole delle rotture
     deliberate stanno ora in `app/docs/05-tipi-prove-e-guardie.md`, che è la pagina che si apre
     prima di scrivere una prova. Il registro resta la sede del *perché*; la sede del *promemoria* è
     un'altra, e vanno tenute distinte.

Stato aggiornato: decisioni fino ad **ADR-0084**, verifiche fino a **V-074**, note di metodo fino
alla **172**. Le suite: **143** prove per gli strumenti, **243** per l'applicazione più **43** di
integrazione, `mypy --strict` verde su 42 file. Prossimo passo: **Task 10** del
[piano](00-progetto/2026-09-02-piano-feature-04-app-python.md).

---

## 2026-09-03 — `feature/04`, Task 10: una promessa mantenuta per caso, e otto righe riservate a server che non esistono

Il Task 10 costruisce la presentazione: `RichTui` per la sala, `PlainSink` per le registrazioni e
per chi reindirizza su file, `NullSink` per le prove e per le misure del Task 16. Tre rese dello
stesso flusso di eventi, e un solo thread che disegna. I file previsti dal piano erano tre, quelli
scritti sono cinque: `presentation/righe.py` e `presentation/scena.py` esistono perché il Passo 4
vieta di provare `RichTui`, e tutto ciò che nella presentazione è una **decisione** — la riga di un
evento, il budget di sala, la coda, la cronaca — è stato spostato dove una prova può guardarlo. Le
prove unitarie passano da **243 a 280**, `mypy --strict` da 42 a **48** file; le 43 di integrazione
e le 143 degli strumenti restano quelle che erano, e restano verdi.

Quattro cose sono state scoperte eseguendo. Due sono errori del progetto, e sono le più utili.

**La promessa di ADR-0019 era falsa, e lo era da quando è stata scritta.** [ADR-0019](Decision.md#adr-0019)
prometteva «un solo thread tocca `Live`», e la prometteva sulla base di
[S-018](Sources.md#s-018): la documentazione di Rich non nomina mai i thread. Il progetto aveva
trattato quel silenzio come una garanzia — se non se ne parla, non ce ne sono — e aveva scelto il
disegno giusto per una ragione che nessuno aveva verificato. Aprendo `rich/live.py` della 15.0.0
installata si legge che con le impostazioni predefinite `Live.start()` avvia un `_RefreshThread`
demone che chiama `refresh()` per conto suo ([M-027](../app/docs/Sources.md#m-027)). Non sarebbe
stato scorretto: dentro `Live` c'è un `RLock`, e la libreria è pensata per reggerlo. Ma «corretto
per caso» e «corretto per costruzione» sono due cose diverse, e la seconda è l'unica che si può
scrivere in un ADR. Da lì `auto_refresh=False` e [ADR-0085](Decision.md#adr-0085), che mantiene la
decisione di ADR-0019 e ne sostituisce il presupposto con una misura.

**La prima sonda ha risposto di no alla domanda giusta.** Il primo tentativo di contare i thread
chiamava `threading.enumerate()` **dopo** `live.stop()`, trovava zero thread in più e concludeva
che non ce n'erano. La risposta era vera e inutile: il `_RefreshThread` viene fermato e unito
proprio da `stop()`. La domanda «esiste un thread in più?» ha senso solo nell'istante in cui la
risposta conta, cioè dentro il `with`. La prova che ora difende ADR-0085 confronta
`set(threading.enumerate())` prima e durante, e fallisce nominando il thread che ha trovato.

**Il prezzo si è potuto misurare, e il piano andava disatteso alla lettera per rispettarlo.** Il
Passo 1 chiede che `refresh_per_second` sia «passato esplicitamente, con il valore scritto accanto
alla ragione per cui è quello». Con `auto_refresh=False` quel parametro diventa **inerte**: mille
al secondo per mezzo secondo scrivono sette byte, cioè quelli dell'unico `refresh()` chiesto a mano
([M-027](../app/docs/Sources.md#m-027)). Passarlo a `Live` avrebbe messo nel codice un numero che
non fa niente, con accanto una motivazione che descrive un comportamento che non avviene: la forma
più difficile da smentire di una spiegazione sbagliata. Il numero vive quindi nel periodo del ciclo,
`self._periodo = 1.0 / ritmo`, dove agisce davvero. La deviazione è dichiarata in ADR-0085 e nella
pagina [11](../app/docs/11-tre-rese-e-un-solo-thread-che-disegna.md).

**Dieci al secondo, e il costo non è la ragione.** Un disegno della schermata più cara costa
**0,76 ms** ([M-028](../app/docs/Sources.md#m-028)): a dieci giri al secondo è lo 0,8% di un core,
e anche a sessanta si resterebbe sotto il 5%. Il ritmo lo decide l'altro lato — il ritardo massimo
fra un fatto e la sua comparsa, cento millisecondi a dieci, duecentocinquanta ai quattro
predefiniti di Rich. In una scena in cui i tempi **sono** il contenuto, quel quarto di secondo si
vede.

**Il numero che giustificava il ritmo era stato scritto prima di misurarlo.** La docstring di
`RITMO_PREDEFINITO` diceva «0,86 ms misurati» e citava un codice `M-0NN` di una misura che non
esisteva ancora: un segnaposto che avevo intenzione di sostituire dopo. È il modo in cui un
repository con una regola severa sulle fonti la viola senza rumore. Un numero senza fonte si nota
subito, perché la regola esiste apposta; un numero **con** una fonte ben formata attraversa ogni
rilettura. La misura vera, quando è arrivata, lo smentiva del 35%.

**Otto righe riservate a server che non esistono.** `SERVER_MOSTRATI = 8` era giustificato così:
«due shard da due membri, tre config server, un `mongos`». Sono due errori in una frase sola. Il
primo è di conteggio — gli shard dello stack 03 hanno **tre** membri ciascuno, e i container
`mongo` di quello stack sono undici. Il secondo riguarda il **modello**, ed è quello che conta: la
tabella dell'intestazione non elenca i container dello stack, elenca la `TopologyDescription` che
il driver espone, e **un client di un `mongos` vede il `mongos`**. Chiesto ai tre stack accesi, il
caso peggiore è **tre**: il replica set scoperto ([M-029](../app/docs/Sources.md#m-029)). Le
cinque righe di troppo non erano gratis — `ALTEZZA_INTESTAZIONE = 4 + SERVER_MOSTRATI`, e in una
schermata alta trenta ogni riga dell'intestazione è una riga tolta alla cronaca, che è passata da
sedici a ventuno. Corretto il layout, la misura del costo è stata rifatta: la prima correzione ha
aggiustato il numero, la seconda la cosa misurata.

**Il taglio non è silenzioso, e questa è una decisione.** Un replica set a cinque membri esiste
legittimamente fuori da questo lab. `server_da_mostrare` mostra i primi due e scrive «… e altri 3»:
un elenco troncato in silenzio non è una schermata incompleta, è una schermata che **afferma il
falso** — si legge come un cluster più piccolo di quello che è, e nessuno ha modo di accorgersene.

**Undici rotture, due sopravvissute, e il divieto del Passo 4 letto due volte.** Rompendo il codice
una riga alla volta, nove mutazioni su undici sono diventate rosse subito. Le due superstiti erano
tutte e due in `rich_tui.py`: `auto_refresh=True` — cioè la riga su cui poggia ADR-0085 — e
l'ultimo `aggiorna()` dopo il ciclo, cioè l'evento che chiude la scena e che nessuno vedrebbe mai.
Sopravvivevano perché il Passo 4 era stato letto come «di `RichTui` non si prova niente». Ma
nessuna delle due **è** disegno: la prima è quanti thread esistono, la seconda è se la coda è vuota
quando il ciclo finisce, e si osservano entrambe senza guardare un pixel. Con le due prove
aggiunte, undici su undici. Il fatto da tenere: le uniche due righe di quel modulo che il resto del
progetto **cita** — una in un ADR, una in ogni scenario del talk — erano anche le uniche senza
guardia.

Restano dichiarati aperti: `PlainSink` non gestisce `BrokenPipeError`; non esiste ancora un
`Orologio` di sistema, e sarà il Task 11 a fornirlo; nessuna prova guarda che cosa Rich disegna
davvero, e il controllo sarà la registrazione del Task 18; il costo di un disegno è misurato su
`StringIO` e non su un terminale vero; `_RefreshThread` è privato di Rich e può cambiare, e la
difesa è la prova che conta i thread.

### Note di metodo

173. **Quando una decisione si giustifica con il silenzio di una documentazione, quel silenzio va
     misurato prima di trattarlo come una garanzia.** ADR-0019 aveva fatto la cosa prudente —
     davanti a una lacuna, cambiare disegno invece di indovinare — e aveva scritto la prudenza come
     se fosse una proprietà della libreria. Ma un silenzio ha due letture, «non succede» e «non è
     documentato», e la seconda è quasi sempre quella giusta. La regola pratica: se una lacuna è
     abbastanza importante da entrare in un ADR, è abbastanza importante da andare a guardare nel
     sorgente installato, che è lì, sul disco, e risponde in cinque minuti. Il disegno scelto era
     giusto; la ragione scritta accanto era falsa, e sarebbe rimasta scritta.

174. **Un numero inventato accanto a una fonte ben formata è invisibile.** Un repository con una
     regola sulle fonti si difende bene dal numero **senza** citazione: la regola esiste, chi
     rilegge la conosce, la mancanza salta all'occhio. Non si difende affatto dal numero scritto
     insieme a un codice `M-0NN` sintatticamente perfetto che rimanda a una misura che si ha
     intenzione di fare dopo. La forma è quella conforme, e la conformità della forma è esattamente
     ciò che ferma la rilettura. La regola pratica è che la citazione si scrive **dopo** aver
     scritto la fonte, mai prima, e che un segnaposto, se proprio deve esistere, va scritto in una
     forma che non passa un controllo automatico.

175. **Una giustificazione plausibile è la forma più duratura di un errore di modello.**
     `SERVER_MOSTRATI = 8` non era un numero buttato lì: aveva accanto una frase che elencava
     shard, config server e `mongos`, cioè aveva l'aspetto di un numero derivato. Sbagliava il
     conteggio, ma soprattutto contava la cosa sbagliata — i container dello stack invece di ciò
     che il driver espone. Un numero nudo invita a chiedere «da dove viene?»; un numero con una
     derivazione plausibile scritta accanto chiude la domanda. La regola pratica: quando una
     costante descrive **quello che un sistema esterno mostrerà**, la si chiede al sistema esterno,
     e la prosa accanto riporta la misura, non il ragionamento che l'ha anticipata.

176. **Una sonda può rispondere di no alla domanda giusta.** Contare i thread dopo `live.stop()` è
     una misura corretta, ripetibile e priva di significato, perché è `stop()` a chiudere il thread
     che si stava cercando. Un risultato negativo va letto sempre due volte: la prima per il
     risultato, la seconda per chiedersi se lo strumento era acceso nel momento in cui il fenomeno
     accade. Vale in particolare per tutto ciò che nasce e muore dentro un blocco `with`.

177. **Un divieto di provare qualcosa si onora spostando altrove ciò che va provato, non
     rinunciando a provarlo.** «Non provare la TUI» significa «non provare Rich», e Rich ha già le
     sue prove. Non significa che le decisioni prese dentro quel modulo restino senza guardia: la
     riga di un evento, il budget di sala, la coda, il taglio dell'elenco sono decisioni del
     progetto e vanno in moduli che non conoscono Rich. Quello che resta dentro va guardato per
     ciò che **è osservabile senza disegnare**: un thread esiste o no, una coda è vuota o no. La
     regola pratica: davanti a un divieto di provare, chiedersi *che cosa* esattamente vieta, e
     spostare tutto il resto fuori.

178. **Un elenco troncato in silenzio non è una schermata incompleta: è una schermata che afferma
     il falso.** Mostrare tre server su cinque senza dirlo produce una lettura precisa e sbagliata
     — «il cluster ha tre membri» — e chi guarda non ha modo di sospettarlo. Il costo di dirlo è
     una riga, «… e altri 2». Vale per ogni resa che ha un budget di spazio: la parte omessa va
     dichiarata, e il numero degli omessi è il dato più importante fra quelli che stanno per essere
     nascosti.

Stato aggiornato: decisioni fino ad **ADR-0085**, verifiche fino a **V-074**, note di metodo fino
alla **178**. Le suite: **143** prove per gli strumenti, **280** per l'applicazione più **43** di
integrazione, `mypy --strict` verde su 48 file. Prossimo passo: **Task 11** del
[piano](00-progetto/2026-09-02-piano-feature-04-app-python.md).

---

## 2026-09-03 — `feature/04`, Task 11: la radice di composizione, e tre difetti che solo l'esecuzione poteva mostrare

Il Task 11 scrive `cli.py`, cioè l'unico punto dell'applicazione che conosce le classi concrete:
costruisce `PymongoStore`, `PymongoInspector`, `SdamBridge`, `SystemClock` e le tre rese, e le
inietta in componenti che continuano a vedere solo porte. Con lui arrivano i tre comandi diretti del
§6.4 — `stats`, `watch`, `workload` — la mappa fra `--target` e stack in un posto solo, e il
`--sink` come opzione invece che come condizione sparsa. Le prove unitarie passano da **280 a 425**,
`mypy --strict` da 48 a **57** file; le 43 d'integrazione e le 143 degli strumenti restano quelle
che erano, e restano verdi.

I file scritti sono più di quelli che il piano elenca, e l'allargamento è dichiarato:
`infrastructure/orologio.py` (la porta `Clock` non aveva un'implementazione di produzione),
`infrastructure/bersagli.py`, `infrastructure/zavorra.py` (`--doc-size`),
`presentation/rapporto.py` (l'uscita di `stats`), `--readers` e `--duration` in
`application/workload.py`, `[project.scripts]` in `app/pyproject.toml`, tre target nel `Makefile`.
Tutte le quattro opzioni di `workload` sono state implementate perché il Task 16 misurerà
**quella** riga di comando, e una riga misurata che non si può digitare non serve.

Poi lo stack 01 è stato acceso, e i tre comandi eseguiti per la prima volta contro un MongoDB vero.
**Due su tre erano sbagliati.** Nessuno dei due lo era per una svista: tutti e due vivevano nella
giuntura fra componenti che, presi uno per uno, erano corretti e provati.

**Il carico scriveva nella collezione seminata, e nessuno se ne accorgeva.** La prima corsa ha
risposto `38 scritture · 0 confermate · 38 fallite`, ed è uscita con **zero**. L'errore, per
intero: `E11000 duplicate key error collection: lab.ordini index: _id_ dup key: { _id: 0 }`
([M-032](../app/docs/Sources.md#m-032)). `DataGenerator` numera i documenti da zero — è ciò che
rende il dataset una funzione pura di `(seme, indice)` — e il seed occupa già gli `_id` da 0 a
49 999. La forma del guasto pesa più del guasto: la cronaca scorreva, le letture riuscivano — 4 833
su 4 833 — e lo schermo era pieno di attività. Dal fondo della sala è una demo che funziona.
Nessuna prova unitaria poteva trovarlo: `InMemoryStore` accetta gli `_id` che gli si danno e non ha
un seed, quindi il fatto vive in nessuno dei due componenti. Che il carico dovesse scrivere altrove
era peraltro già scritto in due posti — `generatore.py` («le due popolazioni non si incontrano mai
nella stessa collezione») e `tools/reset-demo.sh` (`const superstiti = ["ordini"]`). A sbagliare era
il cablaggio, non il disegno. La correzione è una collezione per corsa,
`lab.carico-<AAAAMMGG-hhmmss>`, e il comando che dice dove scrive prima di cominciare
([ADR-0088](Decision.md#adr-0088)). Rifatta la stessa corsa: **8 245 scritture, 8 245 confermate, 0
fallite.**

**Il failover si raccontava due volte, e la colpa non era di PyMongo.** `watch` stampava ogni
transizione due volte, a mezzo secondo di distanza. Invece di crederlo, il driver è stato messo alla
prova nudo — un `MongoClient` con un ascoltatore che stampa, e nient'altro in mezzo: la transizione
la emette **una volta sola** ([M-033](../app/docs/Sources.md#m-033)). Il doppione era nostro.
`watch` aveva due narratori sullo stesso fatto: `SdamBridge`, che traduce i callback (spinto), e
`TopologyWatcher`, che rilegge la stessa `TopologyDescription` ogni mezzo secondo (tirato). Il
ritardo di un giro fra i due rendeva la ripetizione difficile da riconoscere come tale — sembrava
che fosse successo due volte. Che è precisamente il danno: chi guarda **conta** le transizioni per
capire che cosa è successo, e la scena centrale del talk avrebbe mentito. La correzione è una riga
in meno nel cablaggio, non un filtro: il §6.3 assegna la cronaca al ponte, e la sentinella conserva
l'altra cosa che sa fare — misurare l'interruzione — per lo scenario di failover del Task 13
([ADR-0089](Decision.md#adr-0089)). Deduplicare nel sink era la scorciatoia ovvia, ed è stata
scartata per un motivo che vale la pena scrivere: due transizioni identiche e ravvicinate sono anche
la firma di un membro che *flappa*, cioè esattamente ciò che una demo di failover deve mostrare.

**La fotografia diceva `sconosciuto` di un server sano.** `mongolab stats --target standalone`
stampava `localhost:27017 sconosciuto` sopra tre righe che dimostravano il contrario.
`client.topology_description` riferisce ciò che il client crede **in questo istante**, e su un
client appena costruito quella credenza è «non lo so ancora»: il primo battito non è tornato
([M-031](../app/docs/Sources.md#m-031)). Non è un difetto del driver — è la proprietà che rende
visibile l'attimo in cui, durante un'elezione, il client non sa, cioè la scena per cui `watch`
esiste. Diventa un difetto solo se la si legge per prima. La correzione è nell'ordine di lettura di
`rapporto()`: `server_status()` per primo, perché esegue un comando e obbliga il driver a guardare;
`topology()` per ultimo. L'ordine di lettura è l'opposto dell'ordine di stampa, e siccome è
esattamente il genere di dettaglio che il prossimo refactoring cancella per errore, c'è una prova
che conta l'ordine delle chiamate — validata con una mutazione deliberata.

**L'orologio, che era una porta senza casa.** `Clock` esisteva come porta e come doppio; in
produzione nessuno. L'implementazione ovvia è una riga, `datetime.now().astimezone()`, ed è
sbagliata per l'uso che questa applicazione ne fa. La porta serve a **datare** e a **misurare**:
`WorkloadRunner._scrivi` sottrae due `now()` e chiama il risultato latenza. L'orologio da parete di
questa macchina dichiara `monotonic=False` ([M-030](../app/docs/Sources.md#m-030)), cioè per
contratto non promette di andare avanti; un salto all'indietro non solleva niente, produce una
latenza negativa che entra nei percentili. `SystemClock` legge il muro **una volta sola** e da lì
somma il contatore monotono, restituendo ore vere le cui differenze sono durate vere
([ADR-0086](Decision.md#adr-0086)). Nel fuso locale e non in UTC, perché a Ancona due ore di scarto
dall'orologio in fondo alla sala sarebbero la prima domanda del pubblico.

**Il `Makefile` non indovina.** `make app-stats` senza `TARGET` stampa «manca TARGET: make
app-stats TARGET=rs (standalone, rs, sharded)» ed esce con **2**, che è lo stesso codice con cui
Typer rifiuta un `--target` sbagliato ([M-034](../app/docs/Sources.md#m-034)). Sbagliare la riga di
`make` e sbagliare la riga di `mongolab` sono lo stesso errore per chi legge un CI, e meritano lo
stesso numero. `--target` non ha, e non avrà, un valore predefinito: durante il talk si passa da uno
stack all'altro tre volte, e un carico mandato al bersaglio sbagliato non fallisce — riesce,
altrove.

Restano dichiarati aperti, oltre a quelli che il registro dell'applicazione già elenca: sullo stack
03 la collezione del carico **non è distribuita**, perché `init/30-dati-demo.js` distribuisce solo
`lab.ordini`, e il confronto fra architetture del Task 16 dovrà o distribuirla o dichiarare che sta
misurando un solo shard — **è la prima cosa che quel task deve decidere**; la riga
`TOPOLOGIA singola → singola` è vera e non utile; il ciclo di `watch` vive in `cli.py` fino al Task
13; le letture fallite si contano ma non emettono nessun evento.

### Note di metodo

179. **Una suite verde non prova che il programma sia mai stato eseguito.** 425 prove unitarie, 43
     d'integrazione e `mypy --strict` su 57 file non hanno impedito che il primo `workload` vero
     fallisse ogni singola scrittura. I difetti stavano nella **giuntura** fra componenti corretti:
     un generatore che numera da zero e una collezione già numerata; un ponte e una sentinella che
     osservano la stessa struttura. Nessuno dei due appartiene a un componente, quindi nessuna prova
     di componente poteva vederli. La regola pratica: la prima esecuzione contro l'ambiente vero è
     una prova che nessuna suite contiene, e va messa in conto come un passo del lavoro, non come
     una formalità dopo il commit.

180. **Il guasto da temere non è quello che solleva: è quello che esce con zero e stampa numeri
     plausibili.** Il carico rotto usciva zero, riempiva lo schermo di letture riuscite e mostrava un
     consuntivo dall'aria normale. È la stessa forma dell'errore che [ADR-0084](Decision.md#adr-0084)
     ha trovato in `mongorestore` e della latenza negativa che
     [ADR-0086](Decision.md#adr-0086) previene: tre volte, in questo progetto, il pericolo è stato
     un'uscita che non si lamenta e non è vera. La regola pratica: davanti a un consuntivo, chiedersi
     quale suo numero sarebbe **zero** se tutto fosse rotto, e verificare che non lo sia.

181. **Prima di accusare la libreria, misurare la libreria nuda.** Che PyMongo emettesse due volte
     la stessa transizione era l'ipotesi più comoda: avrebbe spostato il difetto fuori dal nostro
     codice. Cinque minuti con un `MongoClient` e un ascoltatore che stampa hanno mostrato che la
     emette una volta sola, e da lì il colpevole era ovvio. Il costo della verifica è stato
     inferiore al costo di scrivere il filtro che avrebbe nascosto il problema vero.

182. **Su uno stesso fatto, un narratore solo.** Se due componenti osservano la stessa struttura,
     uno spinto (i callback) e uno tirato (l'interrogazione periodica), la ripetizione non è un
     rischio: è una certezza. Il ritardo fra i due la rende difficile da riconoscere come
     ripetizione — sembra che il fatto sia successo due volte. E la cura sbagliata è tentante:
     deduplicare a valle sopprime anche le ripetizioni **vere**, che in una demo di failover sono
     proprio la cosa che si vuole vedere. Si guarisce togliendo un osservatore, non aggiungendo un
     filtro.

183. **Quando l'ordine in cui si legge non è l'ordine in cui si stampa, serve una prova che conti le
     chiamate.** `rapporto()` interroga `server_status()` per primo perché *esegue un comando* e
     costringe il driver a una selezione, e `topology()` per ultimo perché fino a quel momento il
     driver non sa niente. Nel testo stampato l'ordine è l'inverso. Un dettaglio così non
     sopravvive a un riordino fatto per leggibilità, a meno che non ci sia un doppio che annota in
     che ordine gli è stato chiesto qualcosa. La prova è stata validata rimettendo `topology()` per
     prima e guardandola diventare rossa: una prova che non si è mai vista fallire non protegge
     niente.

184. **L'implementazione ovvia di una porta va guardata dal verso in cui sbaglia, non da quello in
     cui funziona.** `datetime.now()` come `Clock` è corretto quasi sempre, e la volta che non lo è
     produce numeri invece che eccezioni. Il criterio che ha deciso non è «funziona?» ma «che cosa
     succede quando la macchina si risincronizza mentre misuro una latenza?» — e la risposta,
     scritta nel flag `monotonic=False`, era già lì da leggere. La regola pratica: per ogni porta,
     enumerare gli usi (datare, misurare, ordinare) e chiedersi se una sola implementazione li
     soddisfa davvero tutti.

185. **Un valore predefinito comodo è un errore silenzioso in attesa.** `--target` senza predefinito
     costringe a scriverlo tre volte durante il talk; con un predefinito, una sola distrazione manda
     il carico allo stack sbagliato — e quel comando non fallisce, **riesce**, sul bersaglio
     sbagliato. La stessa severità è nel `Makefile`, che esce con 2 invece di indovinare. Il criterio
     per decidere se un predefinito è legittimo: se sbagliarlo produce un errore visibile, mettilo;
     se produce un risultato plausibile ma di un'altra cosa, non metterlo.

Stato aggiornato: decisioni fino ad **ADR-0089**, verifiche fino a **V-074**, note di metodo fino
alla **185**. Le suite: **143** prove per gli strumenti, **425** per l'applicazione più **43** di
integrazione, `mypy --strict` verde su 57 file. Prossimo passo: **Task 12** del
[piano](00-progetto/2026-09-02-piano-feature-04-app-python.md).

---

## 2026-09-03 — `feature/04`, Task 12: la riserva di ADR-0012 chiusa due volte, e una motivazione che era falsa

Il Task 12 mette `mongolab` dentro la rete Compose degli stack, che è il motivo per cui
[ADR-0012](Decision.md#adr-0012) esiste da due mesi: da fuori, un replica set con tre membri sani si
legge `ReplicaSetNoPrimary` ([M-019](../app/docs/Sources.md#m-019)), e per farlo funzionare bisogna
spegnere la scoperta — cioè spegnere la cosa che il talk deve mostrare. Ne escono un
[`app/Dockerfile`](../app/Dockerfile), un servizio `app` in ognuno dei tre `compose.yaml` sotto il
profilo `strumenti`, una variabile d'ambiente che dice da che parte si sta, e quattro ADR. Le prove
unitarie passano da **425 a 462**, quelle d'integrazione da **43 a 47**, quelle degli strumenti da
**143 a 166**; `mypy --strict` da 57 a **58** file; `make stack-check` dice «Stack conformi: 3.» e
il preflight chiude «Superati: 9 · Avvisi: 1 · Errori: 0 · Pronto.»

**La riserva di ADR-0012 si è chiusa due volte, e nessuna delle due nel posto in cui la cercava.**
L'ADR dichiarava che la documentazione di PyMongo non afferma che il driver usi gli host
memorizzati nella configurazione del set, e che per affermarlo bisognava mostrarlo in demo. È
ancora vero del manuale di PyMongo. Non è vero della specifica *Server Discovery And Monitoring* di
`mongodb/specifications` ([A-016](../app/docs/Sources.md#a-016)), che tutti i driver ufficiali
implementano e che lo prescrive in maiuscolo: «While no known primary, client MUST **add** servers
non-primaries' host lists, but MUST NOT remove». La stessa specifica definisce la *seed list* come
«server addresses provided client in initial configuration» — da dove si parte, non dove si arriva.
Un driver non implementa il proprio manuale: implementa una specifica scritta una volta per tutti i
linguaggi, e quella specifica sta in un repository pubblico che non ha l'aria della documentazione.

La seconda chiusura è una misura, e ha richiesto un disegno. La configurazione di produzione passa
**tre** semi al replica set, e con tre semi trovarne tre non dimostra niente. La prova parte da
**uno**, e non dal primario: `mongo-rs-2:27017`. Il client ha trovato tre membri e ha scritto su
`mongo-rs-1`, un nome che nessuno gli aveva mai dato ([M-036](../app/docs/Sources.md#m-036)). Resta
fuori il caso senza primario, che la specifica tratta a parte e che si vedrà al Task 13.

**Una decisione ha dovuto correggere la propria motivazione.**
[ADR-0093](Decision.md#adr-0093) stabilisce che un servizio che dichiara `build:` è esente dalla
regola sull'immagine pinnata e soggetto alla stessa regola un livello più in basso: le righe `FROM`
del suo Dockerfile devono essere pinnate per digest, e per un digest che `tools/images.env` conosce.
La regola regge. L'argomento con cui era stata scritta no: diceva che «un'immagine costruita in
locale non ha un digest», che suona ovvio ed è falso. Con l'archivio immagini di containerd —
quello attivo su questa Docker Desktop — l'`Id` di un'immagine **è** il digest del suo manifesto
anche per ciò che nessuno ha mai pubblicato, e `docker image inspect mongolab@sha256:…` la trova
([M-037](../app/docs/Sources.md#m-037)). Il punto vero è che quel digest **nessun registro l'ha mai
servito**: non è verificabile da fuori e cambia a ogni ricostruzione, quindi in `images.env` darebbe
a `pull-images.sh --verify` una cosa da cercare in rete che in rete non c'è. Quando la misura è
arrivata, la premessa sbagliata era già scritta in cinque posti.

**Un difetto trovato da un dato nuovo, non da una svista.** La prima esecuzione dal container ha
stampato `mongo-standalone:27017standalone`: `_riga_server` impaginava l'indirizzo su ventidue
colonne, e `mongo-standalone:27017` ne misura esattamente ventidue
([M-038](../app/docs/Sources.md#m-038)). Il modulo aveva ventuno prove verdi, e nessuna poteva
vederlo perché tutte usavano `localhost:<porta>`, che di colonne ne prende quindici. La larghezza
adesso si calcola sul più lungo degli indirizzi di quella fotografia, con ventidue come minimo.

**Un punto aperto che sembrava chiudersi, e non si è chiuso.** Il registro dell'applicazione
elencava «uccidere il client `docker exec` non uccide `mongodump` dentro il container», con Task 12
come scadenza e la motivazione che dal container non ci sarebbe più stato nessun `docker exec` in
mezzo. Prima di segnarlo chiuso è stato guardato: l'immagine contiene l'interprete e `mongolab`,
non gli strumenti da riga di comando di MongoDB ([M-039](../app/docs/Sources.md#m-039)). Oggi non fa
danno, perché nessun comando della CLI collega la porta `BackupTool`; la scelta fra installarli — con
una terza base da pinnare e un'immagine più pesante — e restare su `docker exec` è del Task 14.

### Note di metodo

186. **Quando una fonte tace, la risposta può stare a un livello diverso di quello in cui si
     cerca.** La riserva di ADR-0012 era formulata contro la documentazione di PyMongo, e contro
     quella era corretta. La frase che serviva stava nella specifica *cross-driver* che PyMongo
     implementa: un livello sopra, in un repository che nessuno apre perché non sembra
     documentazione. La regola pratica: prima di dichiarare che una cosa non è affermata da
     nessuna parte, chiedersi **di che cosa** quello strumento è un'implementazione, e andare a
     leggere quella.

187. **Una prova che non potrebbe fallire non dimostra niente, anche quando passa.** Misurare la
     scoperta dei membri con i tre semi della configurazione di produzione sarebbe stato circolare:
     trovare tre server avendone dati tre è compatibile con un driver che non scopre nulla. Il
     disegno che dimostra è un seme solo, scelto fra i **non** primari, e la verifica che il client
     finisca per parlare con un indirizzo che non gli è mai stato dato. La regola pratica: prima di
     scrivere l'asserzione, chiedersi quale osservazione la falsificherebbe — se non ce n'è una,
     l'esperimento è decorativo.

188. **Una premessa plausibile e mai verificata sopravvive a tutte le revisioni.** «Un'immagine
     costruita in locale non ha un digest» è falsa, ed è rimasta in piedi attraverso una decisione,
     una docstring, tre file Compose e un commento di preflight, perché nessuno mette in dubbio
     ciò che suona ovvio. A smentirla è bastato un `docker image inspect`. E c'è un'aggravante che
     vale come avvertimento: con il vecchio archivio a grafo di Docker quella premessa sarebbe
     stata **vera per caso**, il che l'avrebbe resa ancora più difficile da cogliere. La regola
     pratica: le frasi che iniziano con «ovviamente» sono candidate a diventare una misura.

189. **Una regola del repository che vieta qualcosa di legittimo si sposta di livello, non si
     eccettua.** Il controllo degli stack pretendeva un digest per ogni servizio, e il servizio
     dell'applicazione non poteva averne uno utile. L'eccezione avrebbe lasciato le sue basi libere
     di essere tag mobili — cioè avrebbe abbandonato lo scopo per salvare la lettera. Spostare la
     regola sulle righe `FROM` del Dockerfile la mantiene intera: nessun bit arriva dalla rete senza
     che qualcuno l'abbia fissato. La regola pratica: davanti a un divieto scomodo, chiedersi che
     cosa protegge, e cercare il livello a cui quella protezione continua a valere.

190. **Una guardia che passa alla prima esecuzione non è ancora una prova.** Le cinque prove nuove
     su `tools/tests/test_coerenza_repo.py` sorvegliano una configurazione già corretta, quindi
     erano verdi appena scritte — cioè indistinguibili da cinque prove che non controllano niente.
     Ognuna è stata mutata: si perturba il file sorvegliato, si verifica che la guardia scatti con
     un messaggio leggibile, si ripristina e si riverifica il verde. La regola pratica: per ogni
     guardia scritta su uno stato già conforme, la mutazione fa parte della scrittura, non della
     revisione.

191. **Tradurre uno strumento in un altro linguaggio ne cambia la semantica, e la mutazione lo
     scopre.** La prova che verifica il `sed` del preflight ne riscriveva l'espressione in Python
     con `[^ ]*`, che in Python attraversa gli a capo mentre `sed` lavora **una riga per volta**.
     L'asserzione falliva con `'mongolab:0.1.0\n\n' == 'mongolab:0.1.0'`: la prima delle cinque
     guardie, mutandola, ha trovato un difetto in sé stessa. La regola pratica: quando una prova
     riscrive in un linguaggio ciò che un altro strumento fa, la differenza da cercare non è nella
     sintassi dell'espressione, è nell'unità su cui lo strumento lavora.

192. **Un'asserzione banalmente vera passa con qualunque risultato.** La prova sullo sharded
     cercava `"sharded" in uscita`, e l'uscita comincia con il titolo `sharded (docker/03-sharded)`:
     sarebbe passata anche se la topologia letta fosse stata un'altra. Adesso prende la riga
     `topologia` e ne confronta le parole. La regola pratica: se la stringa cercata compare anche
     nell'intestazione, nel nome del bersaglio o nel comando, non sta provando ciò che sembra.

193. **Prima di segnare chiuso un punto aperto, guardare se lo è.** Il registro dava per chiuso al
     Task 12 il limite del `docker exec` sul dump, con una motivazione scritta tre task prima e mai
     riverificata. Un comando ha mostrato che nell'immagine `mongodump` non c'è. Un punto aperto
     chiuso per inerzia è peggio di un punto aperto: sparisce dall'elenco e riappare in sala. La
     regola pratica: le scadenze scritte nei registri sono previsioni, e alla data prevista si
     verificano come qualunque altra affermazione.

194. **Un dato nuovo trova i difetti che nessuna prova cercava.** L'indirizzo incollato al ruolo
     stava in un modulo con ventuno prove verdi, ed è comparso al primo indirizzo lungo ventidue
     caratteri — che dall'host non poteva esistere. Non è un buco nella copertura: è che il valore
     non era mai passato di lì. La regola pratica: quando cambia la **provenienza** dei dati — non
     il codice — vale la pena rieseguire a occhio le uscite che nessuno ha più guardato da quando
     erano corrette.

Stato aggiornato: decisioni fino ad **ADR-0093**, verifiche fino a **V-074**, note di metodo fino
alla **194**. Le suite: **166** prove per gli strumenti, **462** per l'applicazione più **47** di
integrazione, `mypy --strict` verde su 58 file. Prossimo passo: **Task 13** del
[piano](00-progetto/2026-09-02-piano-feature-04-app-python.md).

---

## 2026-09-04 — `feature/04`, Task 13: la scena centrale, la sesta porta, e i due numeri che tengono

Il Task 13 costruisce l'Atto II del Blocco 2: carico attivo, il primario che cade, la cronaca
dell'elezione con il timestamp al millisecondo, e in fondo **durata dell'interruzione** e
**scritture perse**. È la scena per cui l'applicazione esiste — le altre si potrebbero fare con
`mongosh` e pazienza, questa no. Ne escono `app/src/mongolab/application/scenari.py`, la sesta
porta del dominio, il decimo evento, la sottocomanda `demo failover`, e sei ADR. Le prove unitarie
passano da **462 a 523**, quelle d'integrazione da **47 a 48**, `mypy --strict` da 58 a **64** file.

**La scena, eseguita per la prima volta, si è rivelata impossibile per un processo solo.** La
cronaca dell'elezione esiste solo se il client fa scoperta, e la scoperta funziona solo da dentro
la rete Compose — è la conclusione del Task 12. Il guasto è un `docker compose kill`, e vuole il
socket del demone, che il container dell'applicazione **non ha** per una scelta deliberata dello
stesso Task 12. Dall'host, per giunta, il primario si chiama `localhost:27021`, che non è il nome
di nessun servizio che si possa fermare. Da qui [ADR-0095](Decision.md#adr-0095): la porta `Regia`
con quattro verbi e **due adattatori opposti** — `RegiaCompose` esegue e vive sull'host,
`RegiaAnnunciata` annuncia la riga esatta e si blocca finché un umano non l'ha eseguita. La
conseguenza va portata al PO: la scena dal vivo richiede due terminali.

**Il piano diceva `stop`, e le slide dicevano un altro numero.** Il Passo 2 nomina alla lettera
`docker compose stop`; eseguito, `stop` manda `SIGTERM`, e `mongod` cede il ruolo con ordine —
574, 480, 486 ms secondo [V-029](Sources.md#v-029), **senza elezione da raccontare**. Con `docker
kill` sono 9 812, 10 619 e 10 943 ms, che sono i numeri già proiettati come «forbice 8-10 s»
([V-031](Sources.md#v-031)). Le slide riportano una misura fatta, il piano ha una svista:
[ADR-0097](Decision.md#adr-0097) fissa `kill -s SIGKILL` come guasto predefinito e tiene `stop`
documentato e configurabile, perché il confronto è il pezzo di didattica migliore dei due.

**Guardare non è aspettare.** Contro un replica set sanissimo, `demo failover` usciva con «nessun
primario in vista su «rs»»: `Inspector.topology()` legge la descrizione che il driver **ha già**,
e subito dopo `connetti` quella descrizione è vuota, perché la scoperta comincia in quel momento
([M-042](../app/docs/Sources.md#m-042)). Gli altri comandi non ci inciampavano per caso — `stats`
chiede `serverStatus`, che aspetta la selezione, e `watch` guarda la topologia proprio mentre
cambia. La correzione è un `ping`, che essendo un comando su `admin` va sul primario per
impostazione predefinita ([A-017](../app/docs/Sources.md#a-017)) e quindi aspetta. Il posto comodo
era `cli.py`, e `test_pymongo_si_importa_solo_nell_infrastruttura` lo vieta: la guardia non è stata
toccata, e il codice è finito meglio di dove voleva andare
([ADR-0099](Decision.md#adr-0099)).

**Il confronto del Passo 5 è la vera chiusura del task.** Contro lo stack vero, dal container, con
un processo che faceva da umano: interruzione **10 019 ms**, **0 scritture perse** su 15 229
confermate, primario passato da `mongo-rs-1:27017` a `mongo-rs-3:27017`
([M-043](../app/docs/Sources.md#m-043)). I 10 019 ms cadono dentro la forbice di V-029; lo zero
ripete [V-033](Sources.md#v-033), che ne aveva confermate 12 901 e perdute nessuna. Il piano
chiedeva di fermarsi se non avessero coinciso: coincidono, e nessuno dei due va corretto.

Lo zero, però, ha una spiegazione che cambia la frase da dire in sala. Il `WriteConcern` del client
è **vuoto**: `mongolab` non chiede niente, e `w: majority` arriva dal server come default
*implicito* ([M-041](../app/docs/Sources.md#m-041), MongoDB 7.0.40). Non «la mia applicazione usa
`w: majority`», che sarebbe falso, ma «nessuno qui ha chiesto niente, e il server ha scelto bene».

**Un rifiuto invece di una gentilezza.** `--step` legge da stdin sul thread della scena, e il
`Live` di Rich ridisegna sul suo: il prompt «Invio per proseguire» finisce sotto il ridisegno
successivo, e chi tiene la tastiera dal palco non vede più che cosa sta aspettando. La
combinazione è rifiutata come errore di parametro, prima che la scena cominci
([ADR-0098](Decision.md#adr-0098)). Degradare in silenzio a `plain` sarebbe stato più gentile e
peggiore: una scena che cambia da sola la propria resa mostra dal vivo qualcosa di diverso da
quello che si è provato la sera prima.

Fuori copione, il ciclo di `watch` ha lasciato `cli.py` ed è diventato `sorveglia`: dentro la
radice di composizione era provabile solo aprendo una connessione, e la sua regola più delicata —
si aspetta `giri - 1` volte e non `giri` — non aveva nessuna prova.

### Note di metodo

195. **Quando due requisiti legittimi non stanno nello stesso processo, la risposta è una porta con
     due adattatori — non un compromesso.** La scena voleva la scoperta, che c'è solo dentro la rete,
     e il socket Docker, che c'è solo sull'host. Le vie di mezzo erano tutte peggiori: montare il
     socket nel container (e proiettare in sala il modo più diretto di prendere la macchina),
     rinunciare alla cronaca (e perdere metà dell'Atto II), o inventare un agente che riceva ordini
     dal container. Dichiarare il verbo come porta e dare due implementazioni ha lasciato intatti
     entrambi i vincoli, e ha reso il vincolo stesso **didattico**: in sala si vede che quel
     container non può toccare il demone. La regola pratica: davanti a due requisiti che non
     convivono, prima di cercare la scorciatoia, chiedersi se la separazione non sia essa stessa
     ciò che c'è da mostrare.

196. **Un piano è un documento, e la sua lettera si verifica come qualunque altra affermazione.**
     Il piano scriveva `docker compose stop`; eseguito, produce mezzo secondo e nessuna elezione,
     cioè una scena in cui non succede la cosa che il talk annuncia. Le slide, scritte da una
     misura, dicevano dieci secondi. La correzione è andata al piano e non alle slide, ed è stata
     scritta in un ADR invece che applicata in silenzio. La regola pratica: quando il piano e una
     misura si contraddicono, vince la misura — e la contraddizione va **registrata**, perché è la
     sola traccia che qualcuno ci ha pensato.

197. **Fra un fallimento immediato e un'informazione mancante, il costo è tutto dalla parte
     dell'informazione mancante.** `RegiaCompose` trasforma un'uscita diversa da zero in
     un'eccezione che ferma la scena. Se non lo facesse, un `kill` fallito lascerebbe il primario in
     piedi e la scena arriverebbe in fondo con zero millisecondi di interruzione e zero scritture
     perse: **i numeri di un failover perfetto**, prodotti dall'assenza del failover. La regola
     pratica: quando un'operazione fallita produce un risultato *plausibile* invece di un errore,
     fermarsi non è prudenza, è l'unica difesa che esista.

198. **Guardare non è aspettare, ed è una distinzione che i doppi non insegnano.** Una lettura pura
     che restituisce lo stato corrente e una chiamata che blocca finché lo stato non è quello giusto
     hanno la stessa firma e sembrano intercambiabili. Contro un doppio lo sono, perché il doppio
     risponde subito: cinquecento prove verdi non hanno visto niente. Contro un sistema vero, la
     prima è una fotografia di un istante in cui non era ancora successo nulla. La regola pratica:
     per ogni chiamata che legge uno stato appena creato, chiedersi **chi** garantisce che lo stato
     ci sia già — e se la risposta è «di solito fa in tempo», serve un'attesa esplicita.

199. **Una guardia che dà fastidio ha spesso ragione, e il codice esce migliore dall'averle
     obbedito.** L'attesa del primario stava comodamente in `cli.py`, e la guardia che vieta
     `pymongo` fuori dall'infrastruttura l'ha respinta. Obbedire ha prodotto due cose invece di una:
     `SenzaPrimario`, che è un fatto dell'infrastruttura, e `niente_da_fermare`, che è la frase che
     la riga di comando ne ricava — e che, restituendo l'eccezione invece di sollevarla, si prova
     senza dover fabbricare un replica set malato. La regola pratica: quando una regola del
     repository blocca qualcosa di legittimo, la prima ipotesi non è che la regola sia troppo
     rigida, è che il codice stia nel posto sbagliato.

200. **Una prova che ricostruisce un fatto invece di leggerlo dichiarato può passare per la ragione
     sbagliata.** L'asserzione sull'elezione prendeva la prima riga `SERVER … → primario`, che è la
     scoperta iniziale: nominava il primario di sempre. Il fallimento era rumoroso e innocuo; il
     pericolo era il caso opposto, perché una prova così passerebbe anche se il guasto non fosse
     mai arrivato. Adesso legge la riga di continuazione `da … a …`, che la cronaca stampa solo se
     qualcuno ha davvero preso il posto di qualcun altro — cioè verifica ciò che la sala legge. La
     regola pratica: quando una prova deriva un fatto da dati grezzi, chiedersi se esista una riga
     che quel fatto lo **dichiara**, e asserire su quella.

201. **Una banda larga scelta apposta prova più di una soglia stretta.** La prova d'integrazione
     accetta un'interruzione fra 5 e 15 secondi, non i 10 019 ms misurati. Non è indulgenza: la
     soglia stretta fallirebbe sul portatile di qualcun altro senza che niente sia rotto, e sarebbe
     spenta entro un mese. La banda intercetta l'errore di **categoria** — zero, cioè il guasto non
     è arrivato; sessanta secondi, cioè l'elezione non è avvenuta — e il numero preciso vive nel
     registro delle misure, che è il posto dei numeri precisi. La regola pratica: separare che cosa
     la suite deve **impedire** da che cosa il registro deve **ricordare**, e non chiedere alla
     prima di fare il mestiere del secondo.

202. **Un numero giusto per una ragione che non è la propria è una frase sbagliata in attesa di
     essere detta.** «Zero scritture perse» è vero, ed è facile attribuirlo all'applicazione. Il
     `WriteConcern` del client è vuoto: `w: majority` lo impone il server come default implicito, e
     `getDefaultRWConcern` lo dichiara. Detta male, la frase diventa falsa e — peggio — non
     riproducibile su un cluster con un default diverso. La regola pratica: prima di portare un
     numero su una slide, risalire a **chi** lo produce; se la risposta è «qualcun altro», è quella
     la cosa da dire.

Stato aggiornato: decisioni fino ad **ADR-0099**, verifiche fino a **V-074**, note di metodo fino
alla **202**. Le suite: **166** prove per gli strumenti, **523** per l'applicazione più **48** di
integrazione, `mypy --strict` verde su 64 file.

---

## 2026-09-04 — `feature/04`, Task 14: il backup a caldo, e una finestra che non si poteva scegliere

Il Task 14 costruisce l'Atto III del Blocco 2: `mongodump --readPreference=secondary --oplog`
**sotto carico**, con il ritmo di prima e quello di durante messi sulla stessa riga, e poi il
restore con i conteggi a schermo. Ne escono due sottocomandi — `demo backup-live` e `demo restore`
— tre ADR, cinque misure, e la §8 applicativa della pagina canonica dei backup. Le prove unitarie
passano da **523 a 582**, quelle d'integrazione da **48 a 49**, `mypy --strict` resta verde su 64
file.

**Il debito del Task 9 è stato saldato provando, e la strada corta non funziona.** Nell'immagine
dell'applicazione `mongodump` non c'è ([M-039](../app/docs/Sources.md#m-039)), e la scelta fra
installarlo e restare su `docker exec` era rimandata a qui. Un `Dockerfile` a due stadi che copia i
binari dall'immagine `mongo` pinnata dentro quella `python` pinnata **si costruisce senza un
avviso**, e poi esce con **127**: `libgssapi_krb5.so.2: cannot open shared object file`
([M-044](../app/docs/Sources.md#m-044)). I due strumenti sono compilati contro le librerie Kerberos
del sistema dell'immagine `mongo`, e `python:3.13-slim` è slim proprio perché non le ha. Il guasto
non arriva al `build`, che sarebbe il momento buono: arriva alla prima esecuzione.

Le altre tre strade sono state scartate senza provarle, ognuna perché avrebbe disfatto una
decisione già presa — `apt-get install mongodb-database-tools` aggiunge un pacchetto che nessun
`FROM` dichiara e vuole rete al `build` ([ADR-0093](Decision.md#adr-0093)); il socket Docker nel
container rovescia la decisione da cui è nata la sesta porta ([ADR-0095](Decision.md#adr-0095)); il
volume condiviso non serve, perché il dump sopravvive nel filesystem del nodo fra i due comandi. È
[ADR-0100](Decision.md#adr-0100): **gli strumenti restano dove sono già**, e l'Atto III si gira
dall'host — l'esatto contrario dell'Atto II, che dall'host si rifiuta.

**La finestra della seconda misura non si poteva scegliere.** Il `mongodump` della collezione della
demo dura **476 ms** ([M-045](../app/docs/Sources.md#m-045)). Se la fase «durante» durasse i venti
secondi che uno sceglierebbe a tavolino, il dump occuperebbe il due per cento del campione: un
crollo totale del throughput per tutta la sua durata comparirebbe come un calo del due per cento, e
la promessa del copione risulterebbe verificata da una misura incapace di smentirla. Da qui
`finche` in `WorkloadRunner.esegui`, che **si somma** al limite invece di sostituirlo, e il rifiuto
di riceverlo da solo con un `ValueError` invece che con un predefinito silenzioso
([ADR-0101](Decision.md#adr-0101)).

**Il calo esce negativo, e resta negativo.** Contro lo stack vero: `ritmo prima 595/s · durante
692/s · calo -16.2%` ([M-047](../app/docs/Sources.md#m-047)). Il ritmo è **salito**, perché la
finestra è mezzo secondo e su mezzo secondo il rumore pesa più del dump. Sarebbe stato facile
scrivere «il dump non ha impatto» e avere ragione quel giorno; il rapporto scrive la percentuale con
il segno e lascia concludere alla sala. I numeri che contano sono accanto: 279 scritture durante il
dump, tutte confermate, p95 da 66,3 a 68,7 ms.

**Un punto aperto di `feature/02` si chiude.** `docs/03-amministrazione/backup-restore.md` elencava
`--readPreference=secondary` fra le cose non misurate — «è probabilmente la prima cosa da fare in
produzione». Contando `serverStatus().opcounters.query` sui tre membri prima e dopo lo stesso dump:
senza l'opzione il primario prende **+15** letture, con l'opzione ne prende **+0** e le quindici si
spostano sui due secondari ([M-046](../app/docs/Sources.md#m-046)). La pagina riceve la sua §8
applicativa, e il rimando che
[`docs/04-mongosh/guida-mongosh.md`](04-mongosh/guida-mongosh.md) le faceva — «sono materia di
`feature/04`, insieme al backup a caldo» — diventa un collegamento vero.

**Un `ping` che riesce e non basta.** Dall'host si arriva a un nodo solo, con `directConnection`, e
su un secondario un `ping` riesce lo stesso perché la lettura è ammessa: il guasto comparirebbe alla
prima scrittura, con il carico partito e la collezione a metà. Serve un controllo esplicito su
`topology().ha_primario`, e serve sapere quanto si aspetta: dopo l'Atto II, `mongo-rs-1` si riprende
il ruolo in **4,0 secondi** grazie al suo `priority: 2` ([M-048](../app/docs/Sources.md#m-048)).
Sono quattro secondi di scaletta fra un atto e l'altro, e chi presenta li deve avere.

**Il restore scrive accanto, e non è solo prudenza.** `--into lab` è rifiutato perché i 106
documenti che alla copia mancano **sono ancora nell'originale**: un restore sopra `lab` li
lascerebbe dove sono, i conteggi combacerebbero, e la differenza sparirebbe *proprio perché* il
restore è riuscito. La scena mostrerebbe zero e insegnerebbe il contrario di quello che deve
insegnare ([ADR-0102](Decision.md#adr-0102)).

**Accettato dal PO, lo stesso giorno.** Le due conseguenze di palco sono state portate al PO
alla chiusura del task e accettate entrambe: l'Atto III si gira **da un altro terminale** rispetto
all'Atto II, e i **quattro secondi** di attesa del primario entrano in scaletta invece di essere
compressi. Resta aperto il caso diverso di [ADR-0095](Decision.md#adr-0095), dove i due terminali
non si alternano ma servono **contemporaneamente**.

### Note di metodo

203. **Provare la strada corta costa meno che discuterla, e il risultato è più solido.** La copia
     dei binari nell'immagine era la strada che sembrava ovvia. Provarla è costato cinque minuti e
     ha prodotto un fatto — exit 127, con il nome della libreria mancante — invece di
     un'argomentazione. La parte istruttiva è che **il `build` riesce**: una prova fermata al
     «compila?» avrebbe concluso il contrario. La regola pratica: quando una scelta d'architettura
     dipende da un fatto verificabile in cinque minuti, verificarlo, e assicurarsi che la verifica
     arrivi fino all'**esecuzione** e non si fermi alla costruzione.

204. **Una finestra di misura più larga dell'evento è una misura che non può smentire la propria
     tesi.** Venti secondi di fase attorno a mezzo secondo di dump diluiscono un crollo totale in un
     calo del due per cento: il numero sarebbe vero, la conclusione infondata, e nessuno se ne
     accorgerebbe perché la tesi verrebbe confermata. La regola pratica: prima di scegliere la
     durata di una misura, chiedersi quale risultato la smentirebbe; se nessuno lo può, la finestra
     è sbagliata, non lo strumento.

205. **Un limite che dipende da un processo esterno non è un limite.** `finche` è la condizione
     giusta — la corsa finisce quando finisce il dump — ma se `mongodump` si pianta resta vera per
     sempre. Riceverla da sola è un `ValueError` con la spiegazione dentro il messaggio, invece di
     un predefinito silenzioso che avrebbe funzionato in tutte le prove e fallito una volta, dal
     vivo. La regola pratica: ogni condizione di terminazione che interroga qualcosa fuori dal
     processo va accompagnata da un tetto, e il codice deve **pretenderlo** invece di supplirlo.

206. **La pulizia di una prova va scritta per il cammino che fallisce, non per quello che riesce.**
     Il helper che lancia la scena chiamava `check_returncode()` prima di restituire l'output, e
     lasciava spazzatura nel cluster: il nome della collezione da cancellare lo annuncia la scena
     stessa, sulla prima riga, quindi sollevando prima di restituire il testo il chiamante non ha
     mai saputo che cosa pulire — e la collezione era già stata creata e riempita. Il fallimento è
     esattamente il caso in cui la pulizia serve di più. La regola pratica: un helper di prova non
     solleva; restituisce il codice di uscita insieme all'output, e l'asserzione viene **dopo** che
     il chiamante ha raccolto quello che gli serve per rimettere a posto.

207. **Una prova che fallisce una volta e poi passa va spiegata, non rieseguita.** Una prova
     d'integrazione è caduta con «`mongo-rs-3` sconosciuto» e «`mongod` attivo da 1 m 14 s». Da
     sola: verde; l'intera suite da uno stack assestato: verde. La spiegazione è la scia dei
     failover fatti a mano poco prima — scoperta SDAM incompleta in un container appena avviato — e
     non un difetto del codice nuovo. Fermarsi al «ora passa» avrebbe lasciato in casa una prova
     ritenuta capricciosa, che è il primo passo verso una suite che nessuno guarda. La regola
     pratica: davanti a un fallimento non riproducibile, cercare **che cosa era diverso**, e
     scriverlo; se non si trova, dirlo, ma non archiviarlo come rumore.

Stato aggiornato: decisioni fino ad **ADR-0102**, verifiche fino a **V-074**, note di metodo fino
alla **207**. Le suite: **166** prove per gli strumenti, **582** per l'applicazione più **49** di
integrazione, `mypy --strict` verde su 64 file. Prossimo passo: **Task 15** del
[piano](00-progetto/2026-09-02-piano-feature-04-app-python.md), `demo sharding`, dove l'evento
`ChunkMigrated` trova finalmente chi lo emette — o si scopre che nessuno può.

## 2026-09-04 — `feature/04`, Task 15: nessuno emette `ChunkMigrated`, e la sala partiva da un client freddo

Il Task 15 costruisce il Blocco 3: la stessa corsa di scritture fatta **due volte**, su una
collezione che nessuno ha distribuito e su `lab.ordini` che lo è, con i conteggi per shard
accostati, più le due righe di `explain()` che contrappongono query mirata e scatter-gather. Ne
escono un sottocomando `demo sharding`, la settima porta, sei ADR, cinque misure — e un evento del
dominio **in meno**. Le prove unitarie passano da **582 a 619**, quelle d'integrazione da **49 a
58**, `mypy --strict` resta verde e sale da 64 a **66** file.

Tre dei quattro passi del piano hanno prodotto una risposta diversa da quella che chiedevano, e in
tutti e tre i casi perché sono stati eseguiti invece che ragionati.

**Il Passo 2 chiedeva chi emette `ChunkMigrated`, e la risposta è che nessuno può.** Il passo era
scritto con la sua via d'uscita già dentro — «se non è osservabile dal client, va detto» — ma la via
d'uscita è servita per un'altra ragione. Prima di scrivere l'emittente valeva la pena chiedersi se
ci fosse qualcosa da emettere: `balancerStatus` dice `mode: "full"` e **1 153 giri**, e
`config.changelog`, che conserva le voci dall'`addShard` del giorno dell'inizializzazione, ha **due
`merge` e zero migrazioni** — non una sola voce `moveChunk`, `moveRange` o `migrate`
([M-049](../app/docs/Sources.md#m-049)). Non è l'osservabilità a mancare: è la migrazione. Con una
chiave `{_id: "hashed"}` i due shard restano pari per costruzione, e non c'è nessuno squilibrio da
correggere — cosa che [ADR-0069](Decision.md#adr-0069) aveva già scritto un task prima, dal lato
dell'infrastruttura. L'evento è uscito dal dominio ([ADR-0103](Decision.md#adr-0103)), la guardia
dei nomi scende da dieci a nove, e al suo posto resta un commento che dice quando è uscito e con
quale misura.

**Due pagine erano stantìe da prima, e nessuna guardia le copriva.** Rimuovendo l'evento è venuto
fuori che `app/docs/03-eventi-immutabili.md` elencava dieci eventi ma **non aveva mai aggiunto
`FaseIniziata`**, arrivata al Task 13, e che `app/docs/02-porte-e-doppi.md` diceva ancora «Le
cinque porte» senza `Regia`, arrivata dallo stesso task. `make docs-check` verifica citazioni e
collegamenti; i conteggi raccontati in prosa non li vede nessuno.

**«Lo stesso carico due volte» non lo era.** La prima esecuzione vera, con il limite ancora
espresso in secondi come nelle altre tre scene, ha stampato `carico 4288 senza chiave · 4415 con
chiave · non è lo stesso carico` ([M-052](../app/docs/Sources.md#m-052)). La riga di garanzia ha
funzionato, e ciò che denunciava era un difetto di disegno: sei secondi per corsa incontrano due
throughput diversi e producono due conteggi diversi, e la differenza fra le colonne non è più
attribuibile alla sola chiave di shard. Nessuna prova unitaria poteva vederlo — i doppi scrivono
esattamente quanto il copione chiede, quindi `confrontabile` era sempre verde. Da lì `demo
sharding` è l'unica delle quattro scene **senza** `--carico`: il limite è `--scritture`,
predefinito 5 000 ([ADR-0107](Decision.md#adr-0107)), e le due corse diventano uguali per
costruzione. Il prezzo sono quattordici secondi invece di dieci.

**A client freddo la prima fotografia negava un cluster acceso.** Sullo stack 03 sano, la
fotografia di *prima* diceva `distribuita=False, primario=None, conti=()` di una `lab.ordini` che
le righe subito sotto mostravano ripartita su due shard, con la riga del bilancio a trattini
([M-053](../app/docs/Sources.md#m-053)). `PymongoInspector._e_sharded()` guardava la descrizione
della topologia **come il client la conosce**, e un client appena costruito non conosce niente:
PyMongo scopre i server alla prima operazione, non alla costruzione, e fino a lì ogni seme è
`SCONOSCIUTO` — che nel dominio significa «assenza di un'osservazione», non «osservato assente».
La correzione è un `ping` fatto **solo se nessun ruolo è ancora noto**, e con
`read_preference=NEAREST`: un comando su `admin` va sul primario per impostazione predefinita e non
torna finché un primario non c'è ([A-017](../app/docs/Sources.md#a-017)), quindi con la preferenza
predefinita quella riga avrebbe piantato `stats` durante l'Atto II
([ADR-0108](Decision.md#adr-0108)). È la **seconda volta** — [M-042](../app/docs/Sources.md#m-042)
è la stessa cosa un task prima, in `demo failover` — e la parte che vale è perché nessuna prova
d'integrazione la vedesse: la fixture di sessione chiama `spazza(client)` prima di consegnare il
client, quindi ogni prova partiva da un client già caldo. Solo la sala partiva da uno freddo.

**La tupla vuota aveva due significati, e adesso ne ha uno.** `shard_distribution()` restituiva
`()` sia per «non è uno sharded cluster» sia per «lo è, ma questa collezione non è distribuita»; la
pagina 09 lo dichiarava e concludeva che per le scene di questa applicazione la distinzione non
serviva. Il Blocco 3 è la scena in cui serve, perché accostare le due colonne è tutto il suo
contenuto. Il ritorno è `Distribuzione(collezione, distribuita, primario, conti)`
([ADR-0104](Decision.md#adr-0104)), e il criterio che separa i tre stati è stato **misurato**: su
una collezione distribuita e *vuota* `$shardedDataDistribution` produce comunque la sua riga con i
due shard a zero, su una non distribuita e piena di cinquanta documenti non ne produce nessuna
([M-050](../app/docs/Sources.md#m-050)). Nella stessa decisione la collezione è passata dal
costruttore dell'ispettore al metodo: la difesa scritta al Task 8 impediva la scena invece di un
errore, e si è spostata dal costruttore al **dato**, perché `Distribuzione` porta con sé il nome
della collezione di cui parla e la presentazione lo stampa.

**La settima porta.** `explain()` non stava in nessuna delle sei. Allargare `DocumentStore` era la
strada corta e sarebbe stata una promessa che la maggioranza delle sue implementazioni non
mantiene — i doppi in memoria non hanno un piano da restituire. `QueryPlanner` ha un metodo solo
([ADR-0105](Decision.md#adr-0105)), e che `PymongoStore` ne soddisfi due non è un'eccezione: è ciò
che si ottiene quando le porte sono `Protocol` strutturali e nessuno le eredita. Le tre cose lette
da `winningPlan` sono misurate sui tre stack ([M-051](../app/docs/Sources.md#m-051)): lo stadio sta
sempre in `winningPlan.stage` e va a schermo verbatim, gli shard compaiono solo attraverso un
router, e il loro ordine **non è stabile** — il server risponde `['shard2rs', 'shard1rs']` — quindi
l'adattatore li ordina prima di consegnarli.

**L'accoppiamento accettato dal PO non si è pagato.** La decisione era di scrivere in `lab.ordini`,
riaprendo l'accoppiamento col numero del seme che [ADR-0088](Decision.md#adr-0088) aveva scartato.
Misurato: `lab.ordini` contiene 34 415 documenti, 20 000 con `_id` intero che sono il seed e 14 415
con `_id` `ObjectId` che sono le corse dell'applicazione, e non si sono mai scontrati. **Non
possono**: le scene di `demo` scrivono con `documento_progressivo`, che l'`_id` non lo tocca, e
l'unico che numera gli `_id` da zero è `mongolab workload`, che ha la propria collezione per corsa
([ADR-0106](Decision.md#adr-0106)). L'invariante dichiarata in `generatore.py` — «le due
popolazioni non si incontrano mai nella stessa collezione» — è diventata falsa ed è stata
riscritta invece di essere lasciata a contraddire il codice; quella che regge riguarda solo l'`_id`,
e dà anche il criterio per la pulizia, `{_id: {$type: "objectId"}}`, che `tools/reset-demo.sh`
adesso conta prima che il seed ricostruisca la collezione.

**Per la stessa ragione la scena misura gli arrivi e non i totali.** Misurata sui totali, una corsa
finita per l'ottanta per cento su un solo shard risultava sbilanciata di **tre centesimi di punto**:
i ventimila documenti del seed diluiscono qualunque squilibrio, e la schermata avrebbe dichiarato un
equilibrio perfetto mentre il carico era tutto da una parte.

**Accettato dal PO, lo stesso giorno.** Le due decisioni di scena erano state portate al PO
all'apertura del task: scrivere in `lab.ordini` sapendo di riaprire l'accoppiamento, e girare lo
stesso carico due volte accettando lo sforo di scaletta — «sforo leggermente, ho margine». Sono i
quattordici secondi contro i dieci delle altre scene, ed è il prezzo della seconda colonna: senza,
la prima non dimostra niente.

### Note di metodo

208. **Prima di scrivere chi emette un evento, misurare se l'evento esiste.** Il passo del piano
     diceva «`ChunkMigrated` trova finalmente chi lo emette», e la strada naturale era attaccarsi al
     `changelog` o a un listener e vedere che cosa arriva. Cinque minuti di interrogazione hanno
     mostrato che in quel cluster non è mai arrivata **nemmeno una** migrazione da quando esiste, e
     hanno cambiato il passo da «implementare» a «rimuovere e documentare». La differenza pratica è
     che un'assenza misurata si può scrivere in un ADR con un numero accanto, mentre un emittente
     scritto e mai innescato sarebbe rimasto in casa come codice che sembra funzionare. La regola
     pratica: quando un piano chiede di produrre un segnale, la prima domanda non è «come lo
     produco» ma «quante volte è successo finora».

209. **Una riga di garanzia va lasciata a schermo anche quando il difetto che denunciava è stato
     corretto alla radice.** `confrontabile` è nato per dire in sala se le due corse hanno scritto
     lo stesso numero di documenti, ed è la riga che ha scoperto che con un limite di tempo non lo
     facevano. Corretto il limite — un conteggio invece di una durata — le due corse sono uguali per
     costruzione, e la tentazione era togliere il controllo diventato ridondante. Non lo è: se una
     delle due corse scrivesse meno per un altro motivo, il pubblico deve vedere il numero e la sua
     smentita. La regola pratica: una garanzia che nessuno controlla è una speranza, e il costo di
     tenerla è una riga.

210. **Una fixture che prepara l'ambiente nasconde i difetti dello stato iniziale che nessuno le ha
     chiesto di preparare.** Il difetto del client freddo era in produzione da due task e la suite
     d'integrazione non poteva vederlo, perché la fixture di sessione chiama `spazza(client)` prima
     di consegnare il client e la scoperta SDAM avveniva come **effetto collaterale della pulizia**.
     Ogni prova partiva da uno stato che in sala non esiste. La regola pratica: quando un difetto
     dipende dal primo istante di vita di un oggetto, la prova che lo copre deve costruire
     quell'oggetto da sé, fuori dalla fixture, e va scritto nel commento perché.

211. **Un'asserzione su una sottostringa corta può essere verde per il motivo sbagliato.** In fase
     rossa, `test_su_un_replica_set_non_c_e_nessun_router_a_cui_chiedere` **passava**: il messaggio
     di Typer per un comando che ancora non esisteva — «No such command 'sharding'» — contiene
     `shard`. La prova non stava verificando il rifiuto, stava verificando l'assenza del comando. Le
     asserzioni sono diventate `"sharded cluster"`, `"--target sharded"` e `"router"`. La regola
     pratica: quando si asserisce su un messaggio d'errore, scegliere una stringa che **non possa**
     comparire nel messaggio generico dello strumento che lo stamperebbe al posto tuo — e se la fase
     rossa è verde, la colpa è dell'asserzione, non del codice.

Stato aggiornato: decisioni fino ad **ADR-0108**, verifiche fino a **V-074**, note di metodo fino
alla **211**. Le suite: **166** prove per gli strumenti, **619** per l'applicazione più **58** di
integrazione, `mypy --strict` verde su 66 file. Le porte del dominio sono **sette**, gli eventi
**nove** — l'unico conteggio di questo registro che sia mai sceso. Prossimo passo: **Task 16** del
[piano](00-progetto/2026-09-02-piano-feature-04-app-python.md), il confronto fra le tre
architetture, che eredita da qui una scelta già fatta su dove scrivere.

---

## 2026-09-04 — `feature/04`, Task 16: i debiti di misura saldati, e il controllo che approvava un file rotto

Il Task 16 non aggiunge una scena: salda dei debiti. Quattro pagine di `docs/02-architetture`
avevano scritto per iscritto che una certa misura «ha senso solo sotto carico controllato, cioè con
l'applicazione Python di `feature/04`, e prima di allora sarebbe aria». Il piano lo colloca
**prima** delle pagine nuove del Task 17, con una motivazione che vale la pena ripetere: una pagina
scritta su misure che non esistono ancora è esattamente l'aria che quelle righe promettevano di
evitare.

Ne escono una funzione (`opzioni_di_misura`), quattro opzioni sulla riga di comando, **sette**
verifiche empiriche, **quattro** misure lato applicazione, **tre** ADR, sette righe di «cosa questa
pagina non dice» che diventano rimandi — e una correzione a uno strumento del repository. Le prove
unitarie passano da **619 a 634**, quelle degli strumenti da **166 a 168**, `mypy --strict` resta
verde su 66 file, l'integrazione resta a 58.

**Chi non chiede non riceve.** `opzioni_di_misura` restituisce una mappa in cui un argomento
lasciato a `None` **non compare**, e il client resta byte per byte quello di prima
([ADR-0109](Decision.md#adr-0109)). La tentazione era scrivere `journal=False` come predefinito,
«tanto è quello che fa già pymongo»: ma un valore scritto è un valore dichiarato, e il giorno in cui
il predefinito del driver cambia mentre il nostro resta fermo, due misure di due giorni diversi
smettono di essere accostabili senza che nessuno se ne accorga. Le altre tre regole: la staleness
non viaggia mai da sola (con `primary` è un `ConfigurationError` alla costruzione), la preferenza è
`secondary` e non `secondaryPreferred` perché la ricaduta silenziosa sul primario produrrebbe un
numero valido per una domanda diversa, e le chiavi portano i nomi dell'URI perché la riga stampata
a schermo si incolli in una stringa di connessione senza tradurla.

**Il numero dello standalone non era dello standalone.** Il confronto fra le tre architetture —
otto scrittori, quattro lettori, `--doc-size 2k`, trenta secondi, tre corse per stack, da dentro la
rete Compose — dava 1 712 scritture/s per lo standalone, 428 per il cluster sharded, 366 per il
replica set. Rialzando **solo** il client a `CPU_APP=4.0`, lo standalone sale a **2 334**, cioè
+40 %, mentre gli altri due si muovono del 3 % e del 9 %. Il container dell'applicazione ha
`cpus: 1.0`, e una CPU non basta a saturare uno standalone: la prima misura misurava l'interprete
Python ([M-056](../app/docs/Sources.md#m-056), [V-079](Sources.md#v-079)). Da lì
[ADR-0111](Decision.md#adr-0111): il confronto si pubblica **in coppia**, e la riserva sul ferro
viaggia sulla stessa riga del numero — una nota in fondo alla pagina non arriva sulla slide, il
numero sì.

**Il disegno che muoveva due variabili insieme.** Il gancio per `maxPoolSize` era scritto da due
task: `scrittori` doveva salire *sopra* il pool. Eseguito, quel disegno dava una resa che **scende**
— 4 118, 3 372, 2 632, 2 446 con 8, 16, 24, 32 scrittori — e la lettura comoda era «ecco la
saturazione». È falsa: un pool saturo non fa scendere la resa, la tiene e allunga le attese. Una
resa che scende aggiungendo lavoratori vuol dire che si perde lavoro altrove, e in un container con
una CPU quell'altrove è la contesa fra thread Python. Il disegno buono tiene `scrittori` fermo a 32
e stringe il pool: la resa non è la variabile (oscilla senza direzione da 2 a 100 connessioni), i
percentili *migliorano* stringendo — la coda si sposta dal server al driver — e il segnale sta nel
**massimo**, che salta da 102 ms a 20 000 ms esattamente quando il pool scende sotto il numero
degli scrittori ([V-080](Sources.md#v-080)).

**Il 23 % che era sbagliato di un nono.** Il prezzo di `j: true` calcolato sulle durate a orologio
dava −23 %. Dentro quei tempi c'è l'avvio dell'interprete: isolato con `--writes 1 --writers 1`
vale 0,67–0,78 s su corse di 1,7–2,2 s, cioè il 40 %. Al netto il prezzo è **−32 %**, e la perdita
si azzera davvero — zero documenti contro i due della corsa senza giornale, dove
[V-016](Sources.md#v-016) ne aveva contati cento in condizioni diverse
([V-075](Sources.md#v-075), [M-057](../app/docs/Sources.md#m-057)).

**Il controllo approvava un file rotto.** Con le sette voci `V-` e i tre ADR scritti,
`make docs-check` ha bocciato: V-079 e V-080 risultavano orfane pur essendo citate. La causa stava
nel controllo — `RIGA_FONTI` usava `(.+)$` con `re.MULTILINE`, cioè leggeva solo la **prima riga
fisica** di `**Fonti:**`, e un ADR con sei fonti va a capo. Tutto ciò che stava sotto la prima riga
spariva in silenzio. Corretto in TDD con due prove: una che il blocco raccolga le righe di
continuazione, una che si fermi alla prima riga vuota, alla prima etichetta in grassetto e al primo
separatore. Su centoundici ADR il buco ne toccava esattamente uno — quello appena scritto — e per
gli altri centodieci l'abitudine di tenere le fonti sulla prima riga aveva funzionato per caso.

**Le righe saldate diventano rimandi, e una si apre.** Le sette righe di «cosa questa pagina non
dice» sono state barrate e seguite da un **Saldato** con il collegamento alla misura, non
cancellate. `replica-set.md` guadagna una riga nuova: con un membro in pausa il replica set scrive
un ventisettesimo, la maggioranza si raggiunge ancora, e il perché resta aperto
([V-078](Sources.md#v-078)). Un task che salda debiti può aprirne, se ha misurato qualcosa che non
sa spiegare.

**`analyzeShardKey` funziona, e resta fuori lo stesso.** Lo scoperto di `sharded-cluster.md` diceva
che il comando «richiede un campione di query reali che una demo con dati generati non ha»: il
campione si fabbrica, e `configureQueryAnalyzer` più il carico di `mongolab` danno 576 letture
campionate, 77,6 % mirate contro un mix generato 75/25 ([V-081](Sources.md#v-081)). La motivazione
dello scoperto era sbagliata, e va detto. Il comando resta comunque fuori dall'applicazione
([ADR-0110](Decision.md#adr-0110)) per una ragione di forma: le sette porte servono cose che durano
ed emettono flussi, `analyzeShardKey` risponde una volta sola.

**Un fallimento intermittente, registrato invece che nascosto.** Su tre esecuzioni complete della suite d'integrazione, una è fallita: `test_dentro_la_rete_il_replica_set_ha_un_primario` non ha trovato il primario, e la stessa prova eseguita da sola passa. L'ipotesi è che una prova precedente riavvii `mongo-rs-1` e che questa arrivi durante l'elezione, ma è un'ipotesi: il fallimento non è ancora stato riprodotto a comando. È un punto aperto nel registro dell'applicazione, non una correzione — mettere un'attesa nella prova senza aver riprodotto il guasto renderebbe la suite verde senza sapere perché.

**Note di metodo.**

212. **Un predefinito «uguale a quello della libreria» non è uguale all'assenza.** Scrivere
     `journal=False` perché tanto è ciò che pymongo fa già sembra innocuo e cambia la natura della
     riga di base: da «non abbiamo chiesto niente» a «abbiamo chiesto questo». Il giorno in cui il
     predefinito della libreria cambia, l'assenza segue il cambiamento e il valore scritto no — e
     due misure di due giorni diversi smettono di essere accostabili senza che niente diventi
     rosso. La regola pratica: quando una funzione esiste per **rendere misurabile** un
     comportamento, il suo caso vuoto deve produrre un oggetto identico a quello che si sarebbe
     costruito senza di lei, e ci vuole una prova che lo asserisca — qui
     `assert opzioni_di_misura() == {}`.

213. **Una resa che scende quando si aggiungono lavoratori non è saturazione della risorsa
     condivisa: è contesa dal lato del chiamante.** La distinzione è la differenza fra un
     esperimento e un aneddoto. Un pool saturo mantiene la resa e allunga le attese, perché il
     server continua a essere servito allo stesso ritmo dalle connessioni che ci sono; se la resa
     *cala*, del lavoro si sta perdendo prima di arrivare al server. La regola pratica: prima di
     attribuire un numero al sistema sotto misura, chiedersi se il misuratore possa essere il collo
     di bottiglia — e la verifica costa una corsa, alzando il limite del **solo** client e
     guardando se le altre condizioni restano ferme. Se si muovono tutte, il sospetto è la
     macchina; se si muove una sola, il sospetto è confermato.

214. **Una mediana intatta con una coda molto più lunga è la firma della contesa dal lato di chi
     chiede.** Con `cpus: 1.0` il p50 dello standalone è 2,8 ms e il p99 è 40,6; con quattro CPU il
     p50 resta 2,8 e il p99 scende a 11,0. La maggior parte delle operazioni trova la strada
     libera e non si accorge di niente; quelle che aspettano aspettano il proprio processo. La
     regola pratica: quando un limite di risorsa si sposta e la mediana non si muove, guardare i
     percentili alti prima di concludere che non è cambiato niente.

215. **I percentili pesano le operazioni, non i thread: chi soffre di più è il meno
     rappresentato.** Con `maxPoolSize` a uno in meno del numero di scrittori c'è un thread che
     aspetta per tutta la corsa, e p50, p95 e p99 sono indistinguibili dal caso sano — perché quel
     thread, non scrivendo, non produce campioni. Solo il **massimo** lo denuncia, e il massimo è
     la statistica meno rispettabile che ci sia. La regola pratica: in un riepilogo di latenze i
     percentili descrivono il servizio e il massimo descrive il caso peggiore *che sia riuscito a
     completare*; toglierlo perché «è rumore» significa togliere l'unica colonna che vede la fame.

216. **Un costo fisso dentro una misura di durata non è un errore neutro: comprime le
     differenze.** Il prezzo di `j: true` calcolato sui tempi lordi dava −23 %, sui netti −32 %.
     Un addendo uguale sui due lati sposta sempre il rapporto **verso** l'uno, quindi l'errore
     rende sistematicamente le differenze più piccole di quanto siano. La regola pratica: il costo
     fisso si isola con la corsa più corta che lo strumento sappia fare e si sottrae prima di
     dividere — oppure si evita del tutto misurando a durata fissa e contando le operazioni,
     che è quello che fa il confronto fra architetture.

217. **Un controllo che nessuno controlla è una firma in bianco.** `check_citations.py` leggeva
     solo la prima riga fisica di `**Fonti:**`: le citazioni andate a capo sparivano in silenzio, e
     il file risultava coerente proprio mentre aveva perso un pezzo. Il difetto è emerso solo
     perché un file **legittimo** è stato bocciato; finché ha promosso file rotti, nessuno poteva
     accorgersene. La regola pratica: quando uno strumento di verifica boccia qualcosa che si
     ritiene corretto, la prima ipotesi da escludere è che abbia ragione lo strumento — ma la
     seconda, prima di aggirarlo, è leggerne il codice. E se il difetto c'è, si corregge con una
     prova che avrebbe fallito prima, non con un adattamento del documento.

Stato aggiornato: decisioni fino ad **ADR-0111**, verifiche fino a **V-081**, note di metodo fino
alla **217**. Le suite: **168** prove per gli strumenti, **634** per l'applicazione più **58** di
integrazione, `mypy --strict` verde su 66 file. Le porte del dominio restano **sette** e gli eventi
**nove**: questo task non ha toccato il dominio. Prossimo passo: **Task 17** del
[piano](00-progetto/2026-09-02-piano-feature-04-app-python.md), le tre pagine che `docs/README.md`
promette — e adesso hanno le misure di cui parlare.

---

## 2026-09-04 — `feature/04`, Task 17: le tre pagine dovute, e l'ultima cosa che il repository diceva di sé e non era più vera

Il Task 17 non scrive codice. Scrive le tre pagine che [`docs/README.md`](README.md) intestava a
questo branch da settimane — `06-sviluppo/architettura-app.md`, `06-sviluppo/tdd-e-doppi.md`,
`03-amministrazione/statistiche-monitoraggio.md` — e finché non esistevano, quelle righe dell'indice
erano promesse travestite da collegamenti.

Ne escono tre pagine per **1 037 righe**, **sei** verifiche empiriche nuove (`V-082`…`V-087`), una
misura lato applicazione (`M-058`), **due** ADR, sette citazioni per le slide, e sette righe d'indice
o di stato che il repository dedicava a sé stesso e che non erano più vere. Le suite non si muovono
— 634 unitarie, 58 di integrazione, 168 per gli strumenti, `mypy --strict` verde su 66 file — perché
non è stata toccata una riga di `app/src/`.

**La pagina sul monitoraggio non è un elenco di campi.** La forma ovvia sarebbe stata commentare i
campi di `serverStatus`, ed è anche la forma inutile: quell'elenco esiste già, è il manuale, ed è più
completo di qualunque cosa questo repository possa scrivere. La campagna di misura ha però prodotto
sei risultati che il manuale non dice e che contraddicono ciascuno una lettura corrente, e la pagina
si organizza attorno a quelli ([ADR-0112](Decision.md#adr-0112)): `serverStatus` risponde **45, 52 e
36 sezioni** sui tre nodi e al router ne mancano **venti**, fra cui `wiredTiger`, `globalLock` e
`repl`, senza che nessun errore lo segnali ([V-082](Sources.md#v-082)); sotto un carico che satura il
client il server non mette in coda **niente** e dichiara **67 µs** di latenza dove il client ne
misura **2,8 ms** ([V-083](Sources.md#v-083), [V-079](Sources.md#v-079)); il pool dei ticket di
scrittura non è la costante 128 che circola ma sta fra **7 e 12** e si muove da solo; il ritardo di
replica letto nel modo standard vale **10 000 ms su un insieme sano a riposo** e diventa **negativo**
se lo si chiede al secondario ([V-084](Sources.md#v-084)); ogni scrittura ripetibile costa
**un'operazione replicata in più** ([V-085](Sources.md#v-085)); e il router conta le operazioni del
client alla singola unità ma somma i filesystem degli shard, dichiarando un disco grande il doppio di
quello che esiste, senza dire che uno dei due shard non ha visto **nessuna** operazione
([V-086](Sources.md#v-086)).

La conseguenza operativa più scomoda è che **il ritardo di replica non si mostra dal vivo**, e la
pagina dice perché invece di esibirlo con una nota accanto: la nota non arriva sulla slide, il numero
sì ([ADR-0111](Decision.md#adr-0111)). Al suo posto la pagina indica `opcountersRepl.insert` sul
secondario — che nella misura coincide **esattamente** con le scritture confermate al client, 9 139
contro 9 139 — e `metrics.repl.buffer`, che è la coda vera.

**Il rapporto di compressione è una proprietà dei dati, non del motore.** Stessa istanza, stessa
`snappy`: `lab.ordini` restituisce **3,06×**, la collezione di carico **0,97×** — l'archiviazione è
più grande dei dati. La zavorra dei documenti di carico è base64 di uno `shake_128`, cioè byte
pseudocasuali, e i byte casuali non si comprimono; il 3 % in più è il costo delle strutture di
WiredTiger su un contenuto che non le ripaga. Nella stessa misura è emerso che il database `lab`
aveva **38 collezioni, 37 delle quali di carico**, per ~3 GB di `dataSize` che non interessano più a
nessuno: `dbStats` le somma tutte ([V-087](Sources.md#v-087)).

**«La suite unitaria non ha bisogno di Docker» è diventata una misura.** Era un'affermazione ripetuta
da tredici task e mai provata; basta un `import` di troppo perché smetta di essere vera senza rumore.
Eseguendo la suite con la variabile del client Docker puntata a un socket che non esiste: **634
passate in 3,86 s**, contro 3,96 s dell'esecuzione normale ([M-058](../app/docs/Sources.md#m-058)).
È il numero su cui poggia tutta la pagina sull'architettura, che lo mette accanto ai ~110 s della
suite di integrazione.

**Due pagine sullo stesso codice che `app/docs/` documenta già.** Senza una regola, l'esito è
garantito: o le pagine nuove riassumono i diciassette capitoli, e allora divergono alla prima
modifica del codice, oppure li ripetono, e il repository ha due verità sullo stesso soggetto.
[ADR-0113](Decision.md#adr-0113) risolve distinguendo **per lettore** e non per argomento —
`app/docs/` per chi apre i sorgenti, `docs/06-sviluppo/` per chi non li aprirà mai — e ne trae una
regola verificabile a occhio: **nelle due pagine nuove non compare nessun blocco di codice
dell'applicazione**. Il legame fra le due sedi diventa reciproco, e un collegamento rotto lo trova
`make docs-check`.

**L'ultima cosa che il repository diceva di sé e non era più vera.** Il `README.md` di radice
dichiarava `app/` «**non ancora nel repository**». Correggendola è saltata fuori la riga
immediatamente sopra: `docker/` diceva che «`01-standalone` è nel repository, gli altri due no»,
mentre la tabella quindici righe più in basso li dava tutti e tre dentro. Due righe della stessa
tabella, invecchiate insieme e per lo stesso motivo — nessuno rilegge una riga di stato quando ne sta
correggendo un'altra.

Resta nel registro, non annotata, la riga dell'entrata del 2 settembre che dice «la cartella
`06-sviluppo/` non esiste ancora»: era vera quando è stata scritta ed è diventata falsa lo stesso
giorno. Un registro cronologico non si riscrive; il saldo si legge qui.

### Note di metodo

218. **Un'assenza di dipendenza si prova togliendo la dipendenza, non leggendo gli `import`.**
    «Questa suite non ha bisogno di Docker» era stata affermata per tredici task senza che nessuno
    l'avesse tolta di mezzo per vedere. La lettura statica non basta: un adattatore costruito per
    comodità dentro una prova, un `import` in cima a un modulo di supporto, e la dipendenza rientra
    senza rumore. La regola pratica: si punta il client all'endpoint inesistente — un socket che non
    c'è, un host che non risolve — e si riesegue. Se la suite passa **identica**, l'affermazione è
    una misura; se cambia anche solo un tempo, era una speranza. Costa una corsa, e vale per
    qualunque dipendenza si dichiari assente.

219. **Due sedi che documentano lo stesso codice si distinguono per lettore, non per argomento.**
    Dividere per argomento è la scelta istintiva e non funziona, perché gli argomenti sono gli
    stessi: se una sede tratta «le porte» e l'altra pure, l'unica differenza possibile è la
    lunghezza, cioè un riassunto — e un riassunto diverge alla prima modifica del codice. Dividere
    per lettore dà invece due mestieri diversi sullo stesso soggetto: *com'è fatto* accanto al
    codice, *che cosa si guadagna* dove sta il pubblico. La regola pratica: la distinzione va scritta
    in testa a ciascuna delle due pagine, e le va data una forma **verificabile a occhio**. Qui è
    «nella pagina divulgativa non compare nessun blocco di codice»: chi la viola se ne accorge
    mentre scrive, non in revisione sei mesi dopo.

220. **Una media di sistema è la media di una popolazione che nessuno ha dichiarato.** `dbStats`
    riportava `avgObjSize` 1 984 B per il database `lab`, che non descrive **nessuna** delle sue
    collezioni: è la media pesata su una popolazione dominata dalle 37 collezioni di carico da
    2 048 B, mentre i documenti veri ne pesano 121. Lo stesso vale per il rapporto di compressione,
    che sul database non significa niente e sulla collezione significa tutto — 3,06× contro 0,97×.
    La regola pratica: prima di citare una media che uno strumento offre già calcolata, chiedersi
    **di che cosa** è la media; se la popolazione è mista e nessuno l'ha scelta, il numero descrive
    la storia dell'ambiente e non il sistema.

221. **Le righe di stato di un elenco invecchiano insieme, e si correggono insieme.** Il piano
    chiedeva di aggiornare *la* riga che dichiarava l'applicazione inesistente; la riga sopra, sugli
    stack, era falsa da tre branch. Nessuno la rileggeva perché non era quella che si stava
    correggendo. La regola pratica: quando si aggiorna un'affermazione che il repository fa su sé
    stesso, si rilegge **tutta la tabella o l'elenco che la contiene**, e si controlla che non la
    contraddica un'altra parte dello stesso documento — qui la stessa pagina si smentiva a quindici
    righe di distanza.

222. **Una metrica senza il nodo su cui leggerla è una ricetta rotta.** Le tre architetture di questo
    lab rispondono a `serverStatus` con tre insiemi di sezioni diversi, e al `mongos` ne mancano
    venti — fra cui quelle che un manuale di monitoraggio nomina per prime. Il modo in cui si
    sbaglia non è ricevere un errore: è ricevere un oggetto valido in cui la chiave cercata non c'è,
    e leggerla come uno zero perfettamente plausibile. La regola pratica: in una procedura di
    monitoraggio ogni metrica si scrive con il nodo accanto; e prima di concludere che un valore sia
    zero, si verifica che la **sezione** esista su quel ruolo.

Stato aggiornato: decisioni fino ad **ADR-0113**, verifiche fino a **V-087**, note di metodo fino
alla **222**. Le suite non si muovono: **168** prove per gli strumenti, **634** per l'applicazione
più **58** di integrazione, `mypy --strict` verde su 66 file. Porte **sette**, eventi **nove**:
questo task non ha toccato `app/src/`. Prossimo passo: **Task 18** del
[piano](00-progetto/2026-09-02-piano-feature-04-app-python.md), l'ultimo — la chiusura di
`feature/04` e la sua PR.

## 2026-09-04 — `feature/04`, fuori dai task: la quinta opzione di misura, e un debito che era vero solo sulla riga di comando

Il Task 17 si era chiuso registrando fra i punti aperti dell'applicazione che «il carico non sa
chiedere un write concern diverso dal predefinito, **quindi** la corsa con `w: 1` che isolerebbe i
18 390 µs del primario non è eseguibile». Il Product Owner ha obiettato al *quindi*: `w` è un
parametro della stringa di connessione, nella sezione dopo il `?`. Il manuale gli dà ragione
([S-076](Sources.md#s-076)) — le opzioni di write concern nell'URI sono `w`, `journal`, `wtimeoutMS`
— e nel codice il meccanismo c'era da tredici task: `opzioni_di_misura` parla i nomi dell'URI dal
Task 16, `connetti(**extra)` li porta al client dal Task 5. Mancava **la parola sulla riga di
comando**, non il meccanismo ([ADR-0114](Decision.md#adr-0114)).

Tre righe di codice: `--write-concern` per esteso e non `--w`, testo e non intero perché `majority`
è un valore legittimo quanto `1`, e `w` prima di `journal` nella mappa perché quello è l'ordine
dell'URI e le due opzioni si condizionano. Cinque prove nuove, tutte viste fallire: 639 unitarie.

**Il manuale ha cambiato il disegno della prova prima che partisse.** Con `j` non specificato,
`w: "majority"` **equivale a `j: true`** e `w: <numero>` equivale a `j: false`
([S-077](Sources.md#s-077)): scendere da `majority` a `1` spegne due cose insieme. Quindi tre corse
e non due ([V-088](Sources.md#v-088)) — il predefinito, `w: 1` con il giornale acceso, `w: 1` nudo.

La riserva di [V-083](Sources.md#v-083) si chiude e la lettura era giusta: `opLatencies.writes` sul
primario passa da **18 913 µs a 644**, un fattore 29. Ma a giornale costante la maggioranza costa
**1,38×** di resa, e a conferme costanti il giornale **2,24×**: la cosa cara che il predefinito fa
senza dirlo è **il disco, non la rete**. Un confronto a due corse avrebbe dato il numero giusto con
la spiegazione sbagliata, e non ci sarebbe stato modo di accorgersene guardando i risultati.

Due code sono venute dietro. I 644 µs che restano, contro i 67 dello standalone che non ha nessuno
da aspettare, sono **quanto costa essere un primario**, prima confuso dentro il fattore 274. E il
server non metteva in coda niente perché il freno era la maggioranza: con `w: 1`
`totalTimeQueuedMicros` passa da 10 388 µs a **308 413**, trenta volte tanto. La conclusione di
V-083 non si rovescia — resta l'1,5 % della latenza — ma la sua *ragione* sì.

Riscritte di conseguenza la sesta sezione di `03-amministrazione/statistiche-monitoraggio.md`, le
conseguenze di [ADR-0112](Decision.md#adr-0112) e le riserve di V-083. Tre citazioni per le slide.

### Note di metodo

223. **«Non è possibile» e «non è chiedibile» sono due debiti diversi, e uno dei due nessuno lo
    riapre.** La riga registrata al Task 17 diceva che la misura decisiva non era eseguibile; era
    vera per metà, e la metà sbagliata è quella che ha tenuto la riserva aperta per un task. Il
    meccanismo c'era, mancava l'opzione. La regola pratica: quando si registra un limite, si scrive
    **che cosa manca**, non che cosa non si può fare — «manca l'opzione X sulla riga di comando» si
    chiude in tre righe di codice, «non è eseguibile» resta lì finché qualcuno non la rilegge con
    sospetto. Il costo della parola sbagliata non si vede mai nel momento in cui la si scrive.
224. **Una variabile per volta, anche — soprattutto — quando il manuale ne accoppia due in una riga
    sola.** Il piano era due corse, `majority` contro `1`. Il manuale dice, dentro una tabella, che
    `majority` implica `j: true`: le due variabili viaggiano incollate, e un confronto a due avrebbe
    attribuito alla replica un costo che è per due terzi del disco. La regola pratica: prima di
    disegnare un confronto, leggere che cosa il valore predefinito **accende oltre a sé stesso**; se
    ne accende due, le corse sono tre.
225. **Un collo di bottiglia nasconde il successivo, e misurare a un solo punto di funzionamento
    significa fotografare quale limite era attivo quel giorno.** «Il server non mette in coda
    niente» era la conclusione che chiudeva l'indagine, ed era vera e fuorviante insieme: tolto il
    write concern, la stessa corsa fa il triplo delle scritture e l'attesa cumulativa per un ticket
    va a 308 ms. La regola pratica: una misura di saturazione vale per il regime in cui è stata
    presa; per dire *dov'è* il collo bisogna spostare il carico almeno una volta e guardare se il
    collo si sposta con lui.

---

## 2026-09-04 — `feature/04`, Task 18: le registrazioni del Blocco 2, e chi fa da seconda finestra

L'ultimo task del piano. Cinque registrazioni di terminale dell'applicazione — `stats`, `watch`,
`demo failover`, `demo backup-live`, `demo restore` — girate contro `docker/02-replicaset` con
`--sink plain` e **senza** `--step`, cioè con lo stesso codice della scena dal vivo: è la proprietà
che il Task 13 aveva costruito apposta ([ADR-0098](Decision.md#adr-0098)), ed è ciò che rende la
registrazione una copia invece di una ricostruzione. La cartella passa da nove scene a
**quattordici** ([V-089](Sources.md#v-089)).

**La scena centrale non era registrabile, e il motivo era buono.** `demo failover` gira
l'applicazione dentro la rete Compose, che è l'unico posto da cui si veda la cronaca dell'elezione:
dall'host il client è `directConnection` su una porta pubblicata, non fa scoperta, e la scena perde
esattamente ciò che deve mostrare. Ma dentro la rete non c'è il socket del demone, quindi
l'applicazione annuncia il comando che uccide il primario e si ferma su un `input()`. Dal palco quel
comando lo dà una persona con un secondo terminale aperto; `tools/registra-terminale.py` invece non
scriveva **mai** sul lato padrone dello pseudo-terminale, e la registrazione si sarebbe piantata per
sempre.

Quindi `--regia PREFISSO` ([ADR-0115](Decision.md#adr-0115)): chi registra esegue la riga annunciata
e poi manda l'Invio — in quest'ordine, perché invertirli produrrebbe una scena che riparte prima che
il guasto sia avvenuto, cioè un failover raccontato senza failover. Il prefisso è un argomento
obbligatorio e non un predefinito nascosto: la ricetta dichiara che cosa lo strumento è autorizzato
a eseguire. L'uscita del comando va su `stderr` di chi registra e **non** nel `.cast`, dove va solo
ciò che il pubblico vedrebbe. Quattro prove nuove, tutte viste fallire: **172** per gli strumenti.

**Il conto è arrivato alla prima corsa.** `make` fa l'eco della ricetta prima di eseguirla, e l'eco
comincia con `docker compose ` esattamente come il comando annunciato: la regia ha eseguito l'eco, e
la scena è ripartita da capo dentro se stessa. Si registra con `make -s`.

I numeri che le scene portano: `mongod 7.0.40` e 50 000 documenti nella fotografia; **10 035 ms** di
elezione senza carico; **10 019 ms** di interruzione con carico e **zero scritture perse**, 31 952
confermate contro 31 955 ritrovate; un dump a caldo che costa **l'1,3 %** del ritmo; e 5 886
documenti all'origine contro 5 740 nella copia, **differenza 146** — la finestra che il dump non
copre, che sta nell'oplog e che `mongorestore` senza `--oplogReplay` non riapplica.

**La scena del failover ha eletto due volte, e la seconda non era nel copione.** Avviene da sé otto
secondi dopo il rientro di `mongo-rs-1`, quando si riprende il ruolo: nel tracciato è un
`ERRORE NotPrimaryError` seguito da `RITENTO tentativo 2 dopo 50 ms`. I tentativi automatici del
driver l'hanno assorbita, e le scritture perse restano zero anche lì. Non era previsto e non è stato
tolto: è la miglior risposta che il branch abbia prodotto alla domanda «a che serve `retryWrites`?».

**Due scene su quattordici fanno il 99,9 % della cartella.** Le nove degli stack pesano 31 K, le tre
dell'applicazione senza carico 4,8 K, le due sotto carico **6,3 M**: `PlainSink` scrive una riga per
evento e trentaduemila scritture sono sessantaquattromila righe. Restano intere
([ADR-0116](Decision.md#adr-0116)) — una riserva che dura la metà della scena che sostituisce non è
la riserva di quella scena — e nel pacchetto del versionatore pesano ~640 K, perché sono righe quasi
identiche.

Tutte e quattordici sono state riprodotte dentro uno pseudo-terminale e confrontate con l'originale.
**La regola di normalizzazione scritta nell'indice era insufficiente** e la pagina è stata corretta:
le dodici corte coincidevano con `\r\r\n` → `\r\n`, le due lunghe fallivano a 66 354 byte, dopo che
due terzi del file avevano coinciso. La regola buona è comprimere `\r+\n` in `\n` da tutt'e due le
parti.

**Cinque righe dei punti aperti dicevano «Task 18, con la registrazione che è il controllo». Una
sola si chiude.** Le cinque scene sono `plain`, quindi non c'è nessun `Live` sopra cui un'eccezione
possa sparire (M-015 resta aperto), nessun disegno che possa risultare a scatti, e nessuno sguardo
vero sulla schermata `rich` — che `app/docs/11-tre-rese-e-un-solo-thread-che-disegna.md` prometteva
per questo task, e la promessa era sbagliata, non la scelta. Il Ctrl-C durante il dump non è stato
provato: la scena 13 è corsa fino in fondo, che è ciò che una riserva deve mostrare. Quello che si
chiude davvero è la riga più vecchia delle cinque: il sink testuale esisteva dal Task 10 e non era
mai stato collegato allo strumento di registrazione. Adesso lo è. Risposta anche alla domanda che il
piano assegnava a questo task sul `TopologyWatcher`: **nessun comando lo costruisce e nessuna scena
lo attraversa**; toglierlo è una scelta di progetto, e la raccomandazione è di toglierlo.

### Note di metodo

226. **Se una scena dal vivo ha bisogno di due finestre, lo strumento che la registra deve
    diventare la seconda — oppure si registra un'altra scena.** L'alternativa gratis c'era: girare
    la stessa demo dall'host, dove il guasto si dà da soli. Avrebbe prodotto un file con lo stesso
    nome, la stessa durata e senza la cosa da guardare, perché da lì il client non fa scoperta e non
    ha transizioni da annunciare. La regola pratica: prima di semplificare il modo in cui si
    registra una demo, chiedersi quale **osservabile** la semplificazione spegne; se l'osservabile è
    il motivo della scena, il lavoro è insegnare allo strumento a fare la cosa scomoda.
227. **Un prefisso su un canale di testo non distingue chi parla.** La regia eseguiva le righe che
    cominciavano con `docker compose `, e `make` stampa la ricetta prima di eseguirla: la prima
    registrazione è ripartita da capo dentro se stessa. È il difetto strutturale di ogni protocollo
    che viaggia sullo stesso canale del testo per gli umani — la stessa famiglia della SQL injection
    e dell'iniezione di prompt — in una forma abbastanza piccola da starci in tre righe. La regola
    pratica: quando si riconosce un comando dal testo, si mette per iscritto chi altro può produrre
    quel testo; qui la risposta era «lo strumento di build», e la difesa è una lettera.
228. **Una prova può passare per il motivo sbagliato quando asserisce su una stringa che
    l'infrastruttura stampa comunque.** La prova sul rifiuto di `--regia` durante una riproduzione
    cercava `--regia` in `stderr` — e argparse ci stampa la riga d'uso, che contiene tutte le
    opzioni. Passava prima dell'implementazione. Cambiata su una frase che solo il messaggio di
    rifiuto contiene, è tornata rossa. La regola pratica: se una prova è verde appena scritta,
    l'asserzione va spostata su qualcosa che **solo** il codice mancante può produrre; guardarla
    fallire non è un rituale, è l'unico modo di sapere che cosa sta guardando.
229. **Una regola di normalizzazione tarata sui casi corti fallisce sui lunghi, e fallisce nel modo
    che somiglia a un guasto vero.** `\r\r\n` → `\r\n` valeva per dodici registrazioni su
    quattordici; nelle due lunghe compaiono anche `\r\r\r\n`, e il confronto divergeva a due terzi
    del file dopo che tutto il resto aveva coinciso — cioè con la firma di una registrazione rotta.
    La diagnosi è venuta da una sonda banale: il **prefisso comune più lungo**, e i due byte che
    stanno subito dopo. La regola pratica: davanti a un confronto che fallisce tardi, prima si
    guarda *dove* diverge e cosa c'è in quel punto, poi si formula l'ipotesi; e una regola di
    pulizia va scritta come classe (`\r+`) e non come caso (`\r\r`).
230. **Un percentile calcolato su una finestra che contiene un'interruzione descrive i
    sopravvissuti.** La fase «durante» della scena dichiara un p95 di 49,5 ms, **più basso** delle
    fasi accanto: dura venticinque secondi, i primi dieci non contengono nessuna scrittura, e i
    quindici che restano girano contro un primario appena eletto e scarico. Le richieste peggiori
    non sono lente, sono assenti, e un cruscotto di latenze le conta zero volte. La regola pratica:
    accanto a un percentile che copre un guasto si scrive sempre il **conteggio** e la **durata
    dell'interruzione**; il numero che descrive un failover non è un percentile.
231. **Chiudere i punti aperti vuol dire anche dichiarare quali non si sono chiusi, e perché.**
    Cinque righe rimandavano a questo task «con la registrazione che è il controllo». La
    registrazione è `plain` e ne controlla una sola: le altre quattro riguardano la resa `rich`, che
    per ottime ragioni non è stata registrata. Riscriverle come chiuse sarebbe costato zero e
    nessuno se ne sarebbe accorto. La regola pratica: quando un task promesso arriva, si rilegge
    ogni riga che lo nominava e le si risponde **una per una** — «chiuso», «non controllato, ecco
    perché», «la promessa era sbagliata» sono tre esiti diversi, e solo il primo è una chiusura.

Stato aggiornato: decisioni fino ad **ADR-0116**, verifiche fino a **V-089**, note di metodo fino
alla **231**. I controlli, tutti: `make preflight` **9 superati · 1 avviso · 0 errori** — l'avviso è
la cartella dei filmati, che è vuota davvero e dal 18 settembre diventa bloccante —, `make
docs-check` verde, `make stack-check` **3 stack conformi**, `make tools-test` **172**, `make
app-test` **639**, `make app-check` con `mypy --strict` verde su **66** file, `make
app-test-integration` **58** in 87 s, con la prova intermittente passata. Registrazioni di
terminale: **14**. Porte **sette**, eventi **nove**; `app/src/` non è stata toccata. Prossimo passo:
**PR di `feature/04` verso `develop`**, mai la scorciatoia di git-flow che salta la revisione; la
fusione è del Product Owner, e a PR unita il worktree si chiude nell'ordine di
[ADR-0079](Decision.md#adr-0079) — prima si sgancia la sessione, poi si rimuove la directory — dopo
aver salvato i `.env` ([ADR-0056](Decision.md#adr-0056)).

## 2026-09-04 — La review di Copilot sulla PR #5: un rilievo solo, vero a metà e con il rimedio sbagliato

Il Product Owner ha chiesto una review automatica della PR #5 a GitHub Copilot. L'esito: 74 file
esaminati su 129, «review effort: Lite», nessun commento a livello di PR e **un solo commento in
linea**, su `tools/registra-terminale.py`. Dice che la regia confronta con
`vista.strip().startswith(regia)`, che `strip()` toglie anche gli spazi a sinistra e quindi «una
riga indentata può diventare eseguibile anche se il prefisso non è realmente a colonna 0»; propone
di non togliere niente a sinistra e limitarsi al `\r` finale; aggiunge che «lo stesso problema
compare anche alla riga 297».

Dentro cinque righe di testo ci sono tre esiti diversi, e per separarli è servito **eseguire**.

**La preoccupazione è fondata.** Riconoscere un comando dal testo che un altro programma stampa è la
famiglia di problemi della nota 227, e in questo branch il conto è già arrivato una volta: l'eco di
`make` cominciava con `docker compose ` come il comando annunciato, e la prima registrazione della
scena 12 è ripartita dentro se stessa. Chiedersi quanto è largo quel confronto è la domanda giusta.

**Il rimedio è sbagliato e romperebbe lo strumento.** `_da_un_altra_finestra`
(`app/src/mongolab/cli.py`) stampa «▸ da un'altra finestra…» e poi il comando **rientrato di due
spazi**, perché a schermo va staccato dal testo che lo introduce; la scena 12 registrata lo conferma
su tutt'e due le righe annunciate. Con il prefisso ancorato alla colonna zero la regia non
riconoscerebbe **mai** la riga vera. Applicato alla lettera, il rimedio è stato misurato: la suite
della regia non diventa rossa, **non finisce**. La scena resta appesa all'`input()` e il processo va
fermato a mano — che è precisamente il guasto che ADR-0115 esisteva per evitare.

**La riga 297 non contiene nessuno `strip()`.** È `uscita = registra(`, il punto di chiamata;
`strip().startswith` compare una volta sola in tutto il file, alla 191. Quella parte del rilievo è
inventata, ed è utile saperlo: un recensore che aggiunge un riferimento plausibile e falso costa più
di uno che non lo aggiunge.

**Quello che la review ha trovato davvero è un buco nelle prove.** Nessuna delle quattro prove della
regia passava per una riga **rientrata**, cioè per il caso di produzione: tutte annunciavano a
colonna zero, e il comportamento su cui poggia la scena 12 non era fissato da niente. Adesso ci sono
due prove in più — una riga rientrata **si esegue**, una riga che il prefisso ce l'ha *dentro*
invece che davanti **no** — e la seconda è quella che tiene aperta la distanza fra «spazi a
sinistra» e «prefisso ovunque». `make tools-test`: **174**.

E una correzione di parole, che è la parte del rilievo con cui Copilot aveva ragione senza saperlo:
ADR-0115, il docstring del modulo, la stringa di `--help` e la ricetta dell'indice delle
registrazioni dicevano tutti «le righe che cominciano con quel prefisso» — più stretto di ciò che il
codice fa. Adesso dicono che gli spazi ai due lati si ignorano, e perché; e accanto alla condizione
c'è il commento che spiega che quello `strip()` è portante e non è pulizia.

### Note di metodo

232. **Un rilievo di review si arbitra eseguendolo, perché «ha ragione» e «il suo rimedio funziona»
    sono due domande diverse.** Il commento conteneva una preoccupazione fondata, un rimedio che
    pianta lo strumento e un riferimento a una riga che non esiste. Applicare il rimedio è costato
    un minuto e ha prodotto la risposta che nessuna rilettura avrebbe dato: la suite non fallisce,
    si blocca — e un blocco, in una pipeline, si legge come un timeout e non come un difetto. La
    regola pratica: davanti al suggerimento di un recensore automatico la prima mossa è
    **applicarlo e girarlo**; e se il verdetto è «non pertinente», la motivazione scritta nel
    commento di chiusura deve contenere un fatto misurato, non un'opinione.
233. **Quando la documentazione descrive il codice più stretto di com'è, prima o poi qualcuno lo
    «corregge» verso la documentazione.** Quattro punti — una decisione, un docstring, un `--help` e
    una ricetta — dicevano «le righe che cominciano con quel prefisso», e il codice invece ignorava
    di proposito il rientro con cui l'applicazione annuncia. Il rilievo nasce esattamente lì:
    leggendo la promessa, il codice sembra troppo largo. La regola pratica: se una condizione
    tollera qualcosa **di proposito**, la tolleranza si scrive dove sta la condizione — nel commento
    accanto, non solo nella testa di chi l'ha scritta — e la stessa frase va nei documenti che la
    promettono, altrimenti la prossima review chiederà di stringere.

Stato aggiornato: decisioni fino ad **ADR-0116**, verifiche fino a **V-089**, note di metodo fino
alla **233**. Controlli: `make tools-test` **174** e `make docs-check` verde. `app/src/` non è stata
toccata: la modifica sta in `tools/`, e i tre documenti che la descrivono sono allineati. Nessuna
citazione nuova per le slide — il rilievo riguarda il metodo di lavoro e non il contenuto del talk.
Prossimo passo: chiusura del thread di Copilot sulla PR #5 con la motivazione misurata, poi la
review di `codex` sulla stessa PR.

## 2026-09-04 — La review di `codex` sulla PR #5: quattro rilievi, quattro veri

Dopo Copilot, la stessa PR è stata data a `codex exec` in sandbox di sola lettura, con un prompt che
dichiarava il contesto — materiale didattico, non software di produzione —, i file da saltare (i
`.cast`, due dei quali pesano megabyte) e le scelte già decise che non sono rilievi. Ha prodotto
**quattro rilievi**, tre P1 e un P2, e il verdetto «modifiche da richiedere prima del merge».

Arbitrati uno per uno, eseguendo. **Nessuno è un'allucinazione, e nessuno è un falso positivo.** È
la differenza che conta rispetto alla review precedente: là un rilievo su uno, con dentro un rimedio
che rompeva lo strumento e un riferimento a una riga inesistente; qui quattro su quattro, con il
percorso di verifica scritto accanto a ciascuno.

**1. `--tetto` ferma il carico, non la scena.** `ScenarioBackup._con_dump` passa `tetto_s` a
`WorkloadRunner` e poi resta, sul thread principale, dentro `for avanzamento in
self._strumento.dump(...)`. Se `mongodump` si pianta, il carico molla al tetto e la scena no.
Misurato con un iteratore che non torna mai e `tetto_s = 0,05 s`: dopo **15 secondi**, cioè
trecento volte il tetto, `esegui()` non era ancora tornata. Il punto che lo rende un difetto e non
una scomodità è che [ADR-0101](Decision.md#adr-0101) e `app/docs/15-…` promettono l'opposto — «il
tetto resta, come rete di sicurezza», «terminare la scena anche se il dump non torna più» — e il
caso che descrivono è precisamente quello che questa sonda ha riprodotto: «uno schermo fermo davanti
a duecento persone».

**2. Se l'elezione salta, il nodo resta a terra.** In `ScenarioFailover.esegui`, `rompe(...)` sta
alla riga 371 e `ripara(...)` alla 377, senza niente in mezzo che le leghi. Misurato con un carico
che solleva alla seconda fase: la regia riceve `[('ferma', 'mongo-rs-1')]` e basta, per tutti e due
i modi del guasto. Nel modo `sospendi` il container resta **congelato**. Il `finally` che c'è in
`cli.py` chiude il client e non tocca lo stack.

La correzione è meno ovvia di quanto sembri, ed è la ragione per cui questo punto va al Product
Owner e non risolto d'ufficio: dentro la rete Compose la regia è `RegiaAnnunciata`, che *annuncia*
il comando e si ferma su un `input()`. Un `finally` che ripara annuncerebbe la riparazione e
aspetterebbe l'Invio **proprio mentre qualcuno sta interrompendo la scena**, cioè trasformerebbe un
Ctrl-C in un blocco. La domanda vera è cosa deve fare il laboratorio quando la scena si rompe a metà:
rimettere in piedi, o lasciare com'è per farlo guardare.

**3. Il registratore conferma il guasto anche quando il comando è fallito.** `seconda_finestra`
esegue la riga annunciata, stampa il codice di uscita su `stderr` e poi manda l'Invio —
**sempre**. Misurato: con un comando annunciato che esce con **7**, la scena riparte, il `.cast`
contiene una scena in cui il primario non è mai caduto, e il registratore esce **0**. Il rilievo
è forte perché il repository ha già scritto perché questo è grave, nel docstring di `RegiaCompose`:
«un `stop` fallito lascerebbe il primario in piedi, e i due numeri finali sarebbero zero
millisecondi di interruzione e zero scritture perse — cioè un failover perfetto. La sala vedrebbe la
slide sbagliata senza che nessuno abbia modo di accorgersene.» L'adattatore dell'applicazione alza
`ComandoFallito` apposta; il percorso della registrazione, che sta al suo posto, non lo fa. È lo
stesso difetto, reintrodotto dall'altra parte.

**4. Un'eccezione dentro il generatore non ferma il dump — ma il caso grave è più stretto di come è
descritto.** In `_avanzamento`, `processo.kill()` sta solo nell'`except GeneratorExit`; un
`KeyboardInterrupt` sollevato mentre il generatore è fermo a leggere `stderr` passa dal solo
`finally`, che chiude la pipe. Qui l'esecuzione ha aggiunto una distinzione che il rilievo non
faceva, e che cambia la gravità:

- se l'interruzione arriva **solo al processo Python** — un supervisore, `interrupt_main()`, o una
  qualunque eccezione sollevata dentro il generatore — il figlio resta **vivo davvero**, stato `S`;
- se arriva al **gruppo di processi**, cioè il Ctrl-C vero digitato in un terminale, il figlio
  riceve `SIGINT` per conto suo e muore: quello che resta è uno **zombie non raccolto**, che il
  sistema riprende quando il processo padre esce.

La prima misura era sbagliata e va detto: `os.kill(pid, 0)` riesce anche su uno zombie, e leggendo
solo quella la sonda avrebbe dichiarato «vivo» in tutti e due i casi. La distinzione è venuta da
`ps -o state=`. Il difetto resta — due righe lo chiudono, e comprende il limite di `docker exec` che
il docstring già dichiara — ma «Ctrl-C dal palco lascia un `mongodump` orfano» non è quello che
succede.

**Che cosa si è fatto e che cosa no.** I quattro punti sono entrati nella tabella dei punti aperti
di `app/docs/registro-sviluppo-app.md`, ciascuno con la misura che lo dimostra. Nessuno è stato
corretto: tre stanno in `app/src/`, cioè nel codice che la PR sottopone al Product Owner, e due di
quei tre — il tetto sulla scena e la riparazione nel `finally` — sono scelte di disegno e non
sviste. Correggerli d'ufficio dentro una PR già consegnata vorrebbe dire decidere al posto di chi
deve fondere.

### Note di metodo

234. **Un recensore a cui si dichiara il contesto sbaglia meno di uno a cui non si dichiara
    niente.** Le due review della stessa PR sono confrontabili: una ha visto 74 file su 129 senza
    sapere che cos'è il repository, e ha prodotto un rilievo su uno con dentro un rimedio rotto;
    l'altra ha ricevuto tre paragrafi di contesto, l'elenco di ciò che è già deciso e la regola «cinque
    rilievi veri valgono più di venti plausibili», e ha prodotto quattro rilievi veri su quattro. La
    regola pratica: prima di chiedere una review automatica si scrive **che cosa non è un difetto**
    in questo progetto — le scelte deliberate, i debiti già registrati, i file generati da saltare —
    perché il costo di una review non è quello che trova, è quello che fa verificare per niente.
235. **Una sonda può dare la risposta giusta per una domanda che non è quella che si stava
    facendo.** Per sapere se un `Ctrl-C` lascia il `mongodump` orfano, la prima sonda ha usato
    `os.kill(pid, 0)` — che riesce anche su un processo già morto e non ancora raccolto. Rispondeva
    «vivo» in tutti e due i casi, e uno dei due era uno zombie innocuo. Con `ps -o state=` i due
    casi si separano, e il rilievo si ridimensiona da «il dump continua a girare» a «il dump continua
    a girare **se il segnale non arriva al gruppo di processi**». La regola pratica: quando la sonda
    conferma il sospetto al primo colpo, si controlla che stia misurando la cosa e non un suo
    surrogato — la conferma facile è il momento in cui si smette di guardare.
236. **Il difetto che un progetto ha già saputo descrivere può ricomparire dall'altra parte del
    confine.** Il docstring di `RegiaCompose` spiega, con precisione, perché un comando di guasto
    fallito e ignorato produce «un failover perfetto» che nessuno può smascherare — e alza
    un'eccezione. Il registratore, che quando si registra sta esattamente al posto di quella regia,
    manda l'Invio comunque. Nessuno ha sbagliato a ragionare: il ragionamento non ha attraversato il
    confine fra l'applicazione e gli strumenti. La regola pratica: quando si scrive un secondo
    pezzo di codice che **fa la stessa cosa** di uno esistente in un altro contesto — un doppio, un
    ponte, uno strumento da palco — si rileggono le invarianti scritte nel primo e ci si chiede una
    per una se valgono anche qui.

Stato aggiornato: decisioni fino ad **ADR-0116**, verifiche fino a **V-089**, note di metodo fino
alla **236**. Controlli: `make tools-test` **174**, `make app-test` **639**, `make docs-check`
verde. Nessuna riga di `app/src/` e di `tools/` è stata cambiata da questa voce: i quattro rilievi
sono **registrati, misurati e aperti**. Prossimo passo: la decisione del Product Owner su quali
correggere prima della fusione — la raccomandazione è di correggere subito il terzo e il quarto, che
non hanno alternative di disegno, e di discutere i primi due.

*Il Product Owner ha risposto lo stesso giorno, accogliendo la raccomandazione: il terzo e il quarto
si correggono subito, il primo e il secondo restano aperti per la discussione. Voce successiva.*


## 2026-09-04 — I due rilievi senza alternative: il registratore che confermava un guasto mancato, l'`except` che copriva solo il caso educato

Dei quattro rilievi della review di `codex`, il Product Owner ne ha mandati due in correzione
immediata — il terzo e il quarto — tenendo aperti i primi due, che sono scelte di disegno e non
sviste. Il criterio è quello proposto nella voce precedente: si corregge subito ciò che non ha
alternative, si discute ciò che ne ha.

Tutt'e due per prova prima e codice poi, e tutt'e due il rosso l'hanno dato per la ragione giusta.

**Il quarto: `_avanzamento` uccideva il processo solo su `GeneratorExit`.** La prova nuova apre un
dump finto, ne consuma il primo avanzamento, e poi rimanda dentro il generatore un
`KeyboardInterrupt` con `throw()` invece di chiuderlo con `close()`. La differenza è tutta lì:
`close()` solleva `GeneratorExit`, `throw()` solleva ciò che gli si dà, e il punto di sospensione è
lo stesso. Rossa, il figlio era ancora vivo dopo **dieci secondi** di attesa, e vivo davvero — non
uno zombie: nessuno gli aveva mandato niente. La correzione è una parola, `except BaseException` al
posto di `except GeneratorExit`, e regge perché quell'`except` fa una cosa sola e poi rilancia:
libera una risorsa esterna. Verde, l'intero file passa in mezzo secondo, cioè il figlio muore
subito. Resta il limite che il docstring già dichiarava: se il comando è `docker exec …`, ciò che
muore qui è il client, e lo strumento dentro il container tira dritto.

`throw()` al posto di un segnale vero non è una scorciatoia, è la misura giusta: un `SIGINT` al
gruppo di processi ammazzerebbe anche il figlio per conto suo, e la prova diventerebbe verde senza
che il codice sia cambiato. È lo stesso inganno della sonda di ieri, vista dall'altro lato.

**Il terzo: `seconda_finestra` confermava anche dopo un comando fallito.** Qui la correzione sono
tre cose insieme, e nessuna delle tre da sola basta — è [ADR-0117](Decision.md#adr-0117). L'Invio
parte solo se il comando annunciato è uscito con zero; la scena viene abbattuta con un `SIGTERM` al
gruppo, perché il figlio ha fatto `setsid()` ed è capogruppo; lo strumento esce con **125**, il
codice che `env` e `timeout` usano per «ha fallito lo strumento, non ciò che gli era stato chiesto
di fare», dato che 126 e 127 parlano già del comando registrato. La seconda delle tre è quella che
si dimentica: senza l'abbattimento, non mandare l'Invio vorrebbe dire lasciare la scena appesa
all'`input()` finché qualcuno non se ne accorge, che è il modo di fallire peggiore di tutti — la
stessa trappola in cui era caduto il rimedio proposto da Copilot poche ore prima, misurata quel
giorno stesso.

La prova rossa pretende codice 125, `ripartito` assente dal `.cast` e il motivo su `stderr`. C'è
però una quarta cosa che controlla, «uscita 7» su `stderr`, e quella **il codice rotto la passava
già**: verificato eseguendo la versione precedente dello strumento, che stampa `regia: … · uscita 7`
e poi esce **0** con la scena ripartita e il `.cast` che racconta un failover mai avvenuto. È la
misura esatta di che cosa non bastava.

**Che cosa resta aperto.** Il primo e il secondo, con la misura accanto, nella tabella di
`app/docs/registro-sviluppo-app.md`: il `--tetto` che ferma il carico e non la scena, e la
riparazione del nodo che non sta in un `finally`. Sul secondo la domanda per il Product Owner non è
tecnica: dentro la rete Compose la regia è `RegiaAnnunciata`, e un `finally` che ripara annuncerebbe
la riparazione fermandosi su un `input()` **mentre qualcuno sta interrompendo la scena**. Che cosa
deve fare il laboratorio quando la scena si rompe a metà — rimettere in piedi, o lasciare com'è per
farlo guardare — è una decisione sul laboratorio, non sul codice.

### Note di metodo

237. **Un `except` che nomina l'eccezione educata copre solo il caso educato.** `except
    GeneratorExit` copre il consumatore che se ne va con ordine, non quello che muore: un Ctrl-C
    che arriva mentre il generatore è fermo a leggere, un errore che chi disegna rimanda dentro. La
    domanda da farsi non è «quale eccezione mi aspetto» ma «da qui, il rimedio cambia a seconda di
    come me ne vado?» — e quando la risposta è no, perché il rimedio è rilasciare una risorsa
    esterna e rilanciare, la classe da nominare è la più larga. La regola pratica: un `except` che
    fa pulizia e rilancia prende `BaseException`; un `except` che **decide** qualcosa nomina ciò
    che sa gestire.
238. **Fra fallire e piantarsi, piantarsi è peggio — e va deciso quando si scrive il rimedio, non
    dopo.** Togliere la conferma a un comando fallito è metà correzione: qualcuno stava aspettando
    quella conferma, e senza di essa resta lì. La stessa forma dello sbaglio si era vista lo stesso
    giorno nel rimedio proposto dalla review precedente, che non faceva fallire la suite ma non la
    faceva finire. La regola pratica: ogni volta che si aggiunge un «in questo caso non lo
    facciamo», si cerca chi aspettava che lo facessimo, e gli si dice qualcosa.
239. **Un'asserzione che era già verde prima della correzione, dentro una prova che era rossa, non
    è di troppo: è la misura di ciò che non bastava.** Il registratore stampava già `uscita 7` su
    `stderr`, e usciva 0 lo stesso. Tenere quell'asserzione nella prova nuova dice due cose che
    altrove non si leggono — che l'informazione c'era, e che averla non è agire — e impedisce a
    qualcuno di «semplificare» via la diagnostica pensando che ora sia ridondante. La regola
    pratica: quando si corregge un difetto di cui il sistema *si lamentava già*, la prova nuova
    controlla anche il lamento vecchio.

Stato aggiornato: decisioni fino ad **ADR-0117**, verifiche fino a **V-089**, note di metodo fino
alla **239**. Controlli: `make tools-test` **175**, `make app-test` **640**, `make app-check`
(mypy `--strict`, 66 file) e `make docs-check` verdi. Prossimo passo: la discussione con il Product
Owner sui due rilievi rimasti, e la fusione della PR #5, che è sua.

## 2026-09-04 — I due rilievi discussi: il tetto che arrivava a metà, e la ripresa che non stava in un `finally`

I primi due rilievi di `codex` erano stati tenuti aperti perché sono scelte di disegno. Il Product
Owner li ha decisi tutti e due nella stessa direzione, e con parole che valgono più della decisione:
il tetto è «una guardia oltre la quale non si può andare», e sul secondo — «l'attrezzo ti fa una
domanda invece di uscire» — «per me è accettabile e l'approvo». Entrambe le correzioni dentro la
PR #5, per prova prima e codice poi.

**Il primo: `--tetto` fermava il carico e non la scena.** La misura del rilievo era già in tabella:
con `tetto_s = 0,05 s` e un iteratore che non torna, `ScenarioBackup.esegui()` era ancora ferma dopo
quindici secondi, trecento volte il tetto. La correzione ovvia — un thread di guardia che allo
scadere chiuda l'iteratore — **non esiste**, e la sonda che lo dimostra è la cosa che questa
giornata lascia: `close()` chiamata da un altro thread mentre il consumatore è dentro il frame,
fermo su una lettura bloccante, alza `ValueError: generator already executing`. Il dump resta vivo,
il ciclo resta dov'è. Nella stessa corsa il thread principale è uscito **solo** quando il guardiano
ha ucciso il processo ([M-059](../app/docs/Sources.md#m-059)).

Chi chiama la porta ha in mano un iteratore; chi la implementa ha in mano il processo. Solo il
secondo può onorare un tetto, e quindi il tetto è salito sulla porta:
`BackupTool.dump(destinazione, *, tetto_s=None)`. `SubprocessBackup` lo fa rispettare con un
`threading.Timer` che abbatte il figlio e alza `DumpTroppoLungo` — un'eccezione propria, perché dal
palco «mongodump è uscito con codice -9» è il rumore del rimedio e «ha superato il tetto di 300
secondi» è la notizia. Con lo stesso dump piantato e un tetto di due secondi, la scena esce dopo
**2,07 s**. È [ADR-0118](Decision.md#adr-0118).

Il dettaglio che si sarebbe dimenticato è il `poll()` nel guardiano. Il cronometro può scadere
nell'attimo fra la fine del figlio e la lettura del suo codice d'uscita — un dump riuscito mentre
chi guarda è lento a scorrere — e segnare «scaduto» lì vorrebbe dire dichiarare fallita in sala una
scena appena riuscita. C'è una prova apposta, e discrimina fra le due implementazioni.

`restore` **non** ha preso il parametro, ed è un debito dichiarato: un tetto lì vorrebbe dire un
`--tetto` su `demo restore`, cioè superficie di riga di comando che nessuno ha chiesto. È in
tabella.

**Il secondo: `ripara()` non stava in un `finally`.** `rompe` e `ripara` erano due righe consecutive
con in mezzo la fase più lunga della scena, e un Ctrl-C al prompt di `--step` — cioè il modo normale
di abbandonare una scena che va lunga — lasciava il nodo a terra. Col modo `sospendi` è peggio che a
terra: **in pausa**, cioè vivo, con la sua memoria, e senza rispondere a nessuno.

Due dettagli di posizione sono la correzione vera. Il `try` si apre **dopo** `rompe`: il `finally`
deve coprire ciò che è stato rotto, non ciò che non si è riusciti a rompere — se `ferma` solleva, il
nodo non è mai caduto, e con la regia annunciata una ripresa chiesta lì sopra sarebbe una riga sullo
schermo che dice a qualcuno di riavviare qualcosa che nessuno ha spento. E l'annuncio della ripresa
resta **dentro** il `try`, con `ripara` da solo nel `finally`: sul percorso normale non cambia
niente, su quello interrotto la riparazione avviene senza una seconda pausa. È
[ADR-0119](Decision.md#adr-0119).

Il prezzo che il Product Owner ha approvato è l'`input()` della regia annunciata su un percorso di
uscita. Vale però solo dove un umano c'è: `_gia_fatto` assorbe l'`EOFError`, perché un'eccezione
sollevata dentro un `finally` **prende il posto** di quella che passava, e senza terminale `input()`
alza all'istante. Senza quell'assorbimento, chi guarda leggerebbe «EOF when reading a line» invece
del motivo per cui la scena si è fermata.

**Le prove.** Sette in più, 640 → **647**. Tre sul tetto in `test_backup.py`, di cui una — il
predefinito `None` che non impone nessuna scadenza — era **già verde prima della correzione**: è
tenuta come guardia contro una regressione, non contabilizzata come guida. Due sulla scena
interrotta in `test_scenari.py`, una per modo. Una sul tetto che arriva allo strumento e non solo al
carico. Una in `test_cli.py` sulla conferma che non deve coprire l'errore che sta risalendo.

### Note di metodo

240. **Prima di scrivere il rimedio, misurare se il rimedio è possibile.** Il tetto sembrava una
    riga: un thread che allo scadere chiude l'iteratore. La sonda ha detto che quella riga alza
    `ValueError: generator already executing`, e la decisione è cambiata di posto — dal chiamante
    all'implementazione della porta. Trenta righe di sonda hanno risparmiato una correzione che
    sarebbe passata in revisione e sarebbe stata falsa in sala. La regola pratica: quando il rimedio
    ovvio tocca un meccanismo del linguaggio che non si usa tutti i giorni — generatori fra thread,
    segnali, `fork` — la prima cosa che si scrive non è il rimedio, è la sonda che dice se funziona.
241. **Un limite può essere onorato solo da chi tiene la risorsa, e questo decide su quale lato
    della porta vive.** Chi chiama `dump` ha un iteratore; chi lo implementa ha un processo. Un
    iteratore fermo dentro una lettura bloccante non si interrompe da fuori, un processo si ferma
    sempre. Il parametro è finito sulla firma della porta non per simmetria o per eleganza, ma
    perché di là non c'era niente su cui agire. La regola pratica: quando un parametro di controllo
    non «attacca» sul lato del chiamante, non serve un meccanismo in più — serve spostare il
    parametro.
242. **Un `finally` che chiede qualcosa a un umano deve saper stare zitto quando l'umano non
    c'è.** La ripresa del failover è finita in un `finally`, e la regia che la esegue fa una domanda
    con `input()`. Da lì, un'eccezione sollevata **sostituisce** quella che stava risalendo: senza
    terminale, chi guarda avrebbe letto «EOF when reading a line» al posto del vero motivo. La
    regola pratica: ogni chiamata che può sollevare dentro un `finally` va guardata due volte, e
    quelle che dipendono da un canale interattivo vanno rese innocue quando il canale non c'è.

Stato aggiornato: decisioni fino ad **ADR-0119**, verifiche fino a **V-089**, misure fino a
**M-059**, note di metodo fino alla **242**. Controlli: `make tools-test` **175**, `make app-test`
**647**, `make app-check` (mypy `--strict`, 66 file) e `make docs-check` verdi. I quattro rilievi
della review di `codex` sono chiusi. Prossimo passo: la fusione della PR #5, che è del Product
Owner.

## 2026-09-06 — `release/1.0` aperta in anticipo, e il runbook scritto per essere usato prima di essere discusso

Il Product Owner aveva lasciato aperta, la sera del 4, la scelta fra chiudere i punti rimasti e
anticipare la release. Il 6 ha cambiato ordine alle due cose, e la ragione vale più della
decisione: **prima il runbook, poi la discussione sui sospesi**, perché «preferisco vedere dal vero
cosa funziona e cosa no e poi discutere cosa risolvere e come mettere le priorità». Il runbook non
è il consuntivo del lavoro fatto: è lo strumento che misura che cosa manca davvero, e lo misura in
sala invece che in tabella.

`release/1.0` è aperta il **6 settembre**, dieci giorni prima della data del §10 del design, con lo
stesso ordine di apertura dei branch di feature — worktree in `.claude/worktrees/release-1.0`,
branch spinto subito su `origin` perché la PR sia un comando solo, i due `.env` degli stack
raggiunti per symlink ([ADR-0083](Decision.md#adr-0083)). Il prefisso e il punto di partenza sono
quelli che `.git/config` dichiara per `release/`: parte da `develop`, ha `main` per genitore.

**Il runbook è `docs/05-talk/runbook-demo.md`, ed è l'unico documento del talk**
([ADR-0015](Decision.md#adr-0015)). La struttura è quella promessa dal §9 del design — preflight e
stato atteso dei dati, copione minuto per minuto, piano delle registrazioni, tabella sintomo →
azione, criteri di rinuncia in appendice A, comandi di emergenza in appendice B — e la sola cosa
che è stata aggiunta è una §1.5 sulla disposizione dei terminali. Non è decorazione: nell'Atto II
l'applicazione gira **dentro** la rete Compose, perché la cronaca dell'elezione esiste solo da lì
([M-019](../app/docs/Sources.md#m-019)), e da lì non ha il socket del demone. Allora annuncia il
comando e aspetta un Invio. Sono due finestre, e chi non lo sa prima se ne accorge sul palco.

**Ogni «output atteso» del copione è un numero misurato, non stimato.** Vengono dalle quattordici
registrazioni e dalle verifiche che le hanno prodotte: `mongod 7.0.40` e tre membri per la
fotografia, **10 019 ms** e **0 scritture perse** per il failover, **546/s → 539/s** cioè l'1,3 %
per il backup a caldo, **5 886 contro 5 740** per il restore, **9 860 + 10 140 = 20 000** per la
distribuzione. Il documento dice anche che cosa sono: un metro per capire se la scena sta andando
come deve, non una promessa. Uno scarto del venti per cento non è un problema; un ordine di
grandezza manda alla §4.

**Una cosa scritta e poi tolta.** Nella prima stesura il punto 3 del Blocco 3 mostrava il comando
sbagliato — `make app-demo TARGET=sharded` — annotato con un «NO, vedi sotto», e sotto quello
giusto. È un espediente didattico che funziona in una pagina che si studia e non in una che si
legge sotto pressione: chi copia una riga da un runbook copia la prima che vede. È rimasta la frase
in prosa, che dice che `demo sharding` non ha un target nel Makefile e perché.

**Due debiti dichiarati in coda al documento**, invece che taciuti. Il primo: i tempi della §2 sono
quelli del design, coerenti con le durate delle registrazioni ma **mai cronometrati parlando
sopra** — è ciò che la prova generale del 17 deve produrre. Il secondo: aprire la release in
anticipo **non** sposta l'appuntamento di [ADR-0058](Decision.md#adr-0058) sulla 8.0.30, che è del
16 settembre perché è l'ultimo momento utile per ripinnare e rigirare le registrazioni, non perché
coincideva con la release.

### Note di metodo

243. **Un runbook si giudica da quanto poco lascia da decidere al momento.** Ogni volta che il
    documento diceva «se serve», «a discrezione» o «valutare», la riga è stata riscritta con un
    numero o con un ordine: trenta secondi prima di passare alla registrazione, T+18 come soglia
    per aprire i criteri di rinuncia, la scala dei tagli in quattro gradini numerati. Il numero non
    è preciso perché qualcuno l'abbia misurato — trenta secondi sono lunghi davanti a cento persone
    e brevi per un container — è preciso perché così non lo si sceglie sul palco. La regola
    pratica: in un documento operativo, un aggettivo di quantità è un lavoro rimandato al momento
    peggiore.
244. **Scrivere il documento che usa il lavoro è il modo più economico di sapere se il lavoro è
    finito.** Mettere in fila i comandi dei tre blocchi ha fatto emergere in un pomeriggio cose che
    nessuna lettura della tabella dei punti aperti aveva fatto emergere: che l'Atto II vuole due
    finestre e l'Atto III una terza, che `demo sharding` è l'unico comando del copione senza un
    target nel Makefile, che i tempi non sono mai stati presi parlando. Nessuna delle tre era in
    tabella, e tutte e tre sono operative. La regola pratica: quando si deve decidere che cosa
    chiudere di un lavoro quasi finito, il consuntivo più affidabile non è l'elenco dei debiti — è
    provare a usarlo.

Stato aggiornato: decisioni fino ad **ADR-0119**, verifiche fino a **V-089**, misure fino a
**M-059**, note di metodo fino alla **244**. Controlli: `make docs-check` verde. Prossimo passo: il
primo giro del Product Owner con il runbook in mano, e la discussione sui sospesi **dopo**, con in
mano quello che il giro avrà trovato.

## 2026-09-06 — Quattro scene, quattro bersagli, e tre guasti che solo l'esecuzione ha mostrato

Il Product Owner ha fatto accendere i tre stack per il suo primo giro col runbook, e ha posto una
domanda sul copione: perché `demo sharding` è l'unico comando senza un bersaglio nel `Makefile`, e
non si può aggiungerlo. La prima risposta è che **non era l'unico: erano tre** — `backup-live`,
`restore` e `sharding`. La nota di metodo 244, scritta ieri, dice «l'unico» perché chi l'ha scritta
ha contato a mente invece di contare col codice; il conteggio l'ha fatto la prova, ed è rossa con i
tre nomi in chiaro. La seconda risposta è che sì, si può, e il modo è
[ADR-0120](Decision.md#adr-0120): quattro bersagli per quattro scene, `CHIEDI_SOLO_HOST` per le due
dell'Atto III che il socket del demone non ce l'hanno, `ESEMPIO_TARGET` perché il suggerimento del
guardiano non mandi `app-sharding` contro `TARGET=rs`, e la legenda delle variabili in coda a
`make help`, che prima esistevano solo nei commenti del `Makefile`.

Il conteggio a mano non serve più: `test_ogni_scena_dell_applicazione_ha_un_bersaglio_nel_makefile`
legge i decoratori `@demo.command` con `ast` e le ricette del `Makefile`, e confronta gli insiemi.
Scritta prima, rossa, verde dopo.

**Poi si è provato, ed è lì che il pomeriggio ha reso.** Tre cose che nessuna rilettura del runbook
aveva mostrato, tutte e tre nell'Atto III.

1. **La riga del `restore` nel copione era incompleta.** Diceva `demo restore --target rs --step
   --sink plain`, senza `--collection`. Senza quell'opzione il comando parte lo stesso e conta
   `lab.ordini`, cinquantamila documenti da tutte e due le parti: i numeri attesi dal runbook —
   5 886 · 5 740 · 146 — non sarebbero mai usciti. La collezione di carico ha la data nel nome e la
   stampa la scena precedente, già completa: è l'unica riga del copione che **non** passa da `make`,
   e ora il runbook dice perché.
2. **`lab_ripristinato` non lo toglie nessuno.** `demo restore` lo costruisce; `reset-demo.sh 02`
   ripulisce le collezioni di `lab` e non guarda gli altri database; `down`/`up` conservano i
   volumi. Alla seconda corsa `mongorestore` ritrova i documenti già lì, li conta come falliti ed
   esce **zero** — la perdita silenziosa di [M-024](../app/docs/Sources.md#m-024) — e
   `RestoreIncompleto` ferma la scena. Misurato: **6 766 ripristinati, 55 740 persi**, dove 55 740 è
   esattamente `ordini` più il carico del 4 settembre; la prova che era quello e non altro è una
   corsa con `--into lab_prova_0906`, zero falliti. Sul palco vuol dire che **la prova generale
   rompe la replica**: chi prova l'Atto III il 17 e non azzera, il 18 lo vede morire. Il runbook ora
   lo dice nello stato atteso e nella tabella dei guasti; se `reset-demo.sh` debba togliere anche
   quel database è una decisione del PO, non una svista da tappare di nascosto.
3. **L'1,3 % dell'Atto III non si riproduce.** Quattro corse: **48,1 %** con Docker appena acceso e
   `lab` sporca, **16,2 %** con la resa Rich e tre stack accesi, **15,4 %** con `--sink plain` e
   tre stack, **11,9 %** col solo 02. La resa non c'entra, la contesa fra stack vale tre o quattro
   punti: l'1,3 % della registrazione 13 era una corsa fortunata. L'atteso del runbook è diventato
   un intervallo, 10–20 %, con la riga che conta: la percentuale non si annuncia prima di averla
   letta. Le quattro misure restano qui e nel runbook, e **non** in `Sources.md`: una verifica nuova
   dev'essere citata da un ADR per non restare orfana, e adottare un intervallo al posto del numero
   registrato è una decisione, non una misura.

Di passaggio, un quarto: lo stato atteso della §1.4 diceva «`ordini`, 50 000, si verifica con
`make app-stats`», ma `stats` stampa il totale del **database**, non della collezione. Con le
collezioni di carico delle prove dentro diceva **62 602**, e chi controllava avrebbe letto un guasto
dove non c'era.

Il laboratorio è rimasto pulito: `make reset-02`, `make up-02`, `smoke-02` a **42 · 0**, e
`reset-demo.sh 02` alla fine per togliere le tre collezioni di carico delle prove. `lab.ordini` è a
**50 000** e la sua impronta è quella del seed.

### Note di metodo

245. **Il primo dubbio da togliere è quello che costa meno, non quello che convince di più.** Il
    calo del 48 % aveva una spiegazione elegante e pronta — tre stack che si contendono la CPU — e
    verificarla voleva dire spegnere e riaccendere due stack, quattro minuti. L'ipotesi noiosa era
    che la resa Rich costasse: trenta secondi per riprovare con `--sink plain`. Si è cominciato da
    lì, e ha risposto no; poi si è fatta l'altra, e ha risposto «tre o quattro punti su undici». Due
    misure hanno lasciato in piedi una sola spiegazione — che il numero di partenza fosse fortunato
    — e nessuna delle due era quella che sembrava più promettente. La regola pratica: ordinare le
    ipotesi per costo della verifica, non per plausibilità.
246. **Una domanda del committente su una riga di documentazione va seguita fino a dove porta.** La
    domanda era piccola e legittima: perché quel comando non ha un bersaglio. Rispondere voleva dire
    aprire il `Makefile`, che ha mostrato che le scene scoperte erano tre; scrivere la prova, che ha
    mostrato che una era il `restore`; provare il `restore`, che ha mostrato la riga incompleta, il
    database che sopravvive e l'atteso che non si riproduce. Nessuna delle tre stava nella domanda,
    e nessuna si sarebbe vista rileggendo. La regola pratica: quando chi commissiona indica un
    punto, quel punto è un capo di filo — la risposta breve è quasi sempre corretta e quasi sempre
    incompleta.

Stato aggiornato: decisioni fino ad **ADR-0120**, verifiche fino a **V-089**, misure fino a
**M-059**, note di metodo fino alla **246**. Controlli: `make docs-check` verde, `make tools-test`
**176 passate**. Prossimo passo: il giro del PO con gli stack accesi, e la discussione sui sospesi
con dentro le tre cose di oggi — se `reset-demo.sh` debba togliere `lab_ripristinato`, se la
registrazione 13 vada rigirata, e con quale priorità rispetto a ciò che era già in lista.

## 2026-09-06 — Tre decisioni del PO eseguite, e tre numeri che mentivano

Il Product Owner ha risposto ai tre sospesi di stamattina in una volta: sì al drop di
`lab_ripristinato` in `reset-demo.sh`; l'ADR che adotta un intervallo per l'Atto III, con la
registrazione 13 rigirata accettando il numero che verrà; e `stats` che stampa il dettaglio per
collezione e poi il totale, «così da avere una fotografia chiara e verificabile». Tutte e tre fatte.
Tutte e tre hanno mostrato, **eseguendo**, qualcosa che nessuna delle tre domande conteneva.

**1. Il drop c'era, il verdetto mentiva.** La prova rossa scritta stamattina verificava che il nome
`lab_ripristinato` fosse scritto nello script accanto a `dropDatabase`, e quello era vero. Alla
prima corsa dal vivo lo script ha detto «database rimosso: lab_ripristinato», giusto — il database
c'era davvero. Alla seconda l'ha detto di nuovo, e non poteva. `dropDatabase()` risponde `dropped`
**anche per un database che non è mai esistito**: misurato, `lab_inesistente_0906` risponde
`{"ok":1,"dropped":"lab_inesistente_0906"}` come uno pieno. Il ramo «non c'era» non poteva accadere
mai, e lo script raccontava a chi prova la vigilia una pulizia che non aveva fatto. Ora la domanda
si fa prima, con `getDBNames().includes(nome)`, e le due facce sono state provate tutte e due dal
vivo. La regressione la vieta `test_il_verdetto_del_drop_non_si_fida_del_campo_dropped`; l'altra
prova cercava il nome e `dropDatabase` sulla **stessa riga** ed è saltata appena la stesura è
cambiata — era legata al testo, non al comportamento. Adesso leggono lo stesso blocco.

**2. La fotografia per collezione ha trovato due contatori fermi a zero.**
[ADR-0121](Decision.md#adr-0121): riga `collezioni` con un `countDocuments` per collezione in ordine
di nome, poi la riga `database` come prima. Il dettaglio **sopra** la somma, perché un totale
stampato sopra i suoi addendi si legge come il primo di essi — ed è precisamente l'errore di lettura
da cui la decisione viene. Le viste non si contano, `system.views` sì: è la collezione vera in cui
il database tiene le definizioni, e togliere una riga per far pulizia romperebbe l'unica proprietà
che rende la fotografia verificabile.

Girata contro i tre stack, ha detto subito a che cosa serviva: `ordini` 50 000 su 01 e 02, 20 000 su
03, e i totali dei database a **1 505 885** (01, trentotto collezioni), **55 386** (02) e **99 699**
(03) — residui delle registrazioni del 4 settembre. Poi il conto non è tornato: sullo **stack 01**,
che è uno standalone, le collezioni sommano **1 528 002** e `dbStats.objects` ne dichiara
**1 505 885**. Non è sharding, non sono orfani, non è una vista. Lo scarto — **22 117** — sta tutto
in due collezioni che nei metadati risultano a **zero** mentre contengono 7 847 e 14 270 documenti.
`validate()` su una delle due risponde **`valid: true`, zero avvisi**, e intanto rimette il
contatore a 7 847. La collezione non era corrotta: era stantio il numero, e nessuno lo segnalava.
L'altra è stata lasciata così apposta, perché chi rifà la misura veda la differenza.
[V-090](Sources.md#v-090). La causa dello zero è circoscritta e **non** dimostrata: il riavvio del 6
è dichiarato pulito dal giornale di `mongod`, e i giornali del 4 non ci sono più.

Due frasi scritte per prudenza sono diventate misure e sono state riscritte: la docstring
dell'ispettore diceva «la stima, dopo un arresto sporco, *può* restare indietro», e la prova
d'integrazione diceva «fuori da uno sharded cluster i due numeri **devono** coincidere» — una
generalizzazione fatta su sedici documenti, che il laboratorio ha smentito con un milione e mezzo.
La prova resta buona, perché lavora su un database appena creato; è la sua docstring che prometteva
troppo.

**3. La registrazione 13 è stata rigirata, ed è uscito −1,9 %.** Il ritmo è **salito** mentre il
dump girava: 506/s prima, 516/s durante. Prima di rassegnarsi al numero si è fatta una corsa di
controllo, e ha dato **−14,2 %**. A quel punto l'ipotesi «il portatile balla» non bastava più, e la
risposta era dentro il `.cast`, negli istanti delle fasi: la fase `carico` dura **dieci secondi** e
raccoglie cinquemila scritture, la fase `dump` dura **mezzo secondo** e ne raccoglie
duecentocinquanta. `lab` pesa 5,8 MB e `mongodump` la copia in meno di un secondo. La percentuale è
il rapporto fra una media su dieci secondi — che comprende l'avvio a freddo del client, primi
inserimenti a 65 ms contro i 6 di regime — e una media su mezzo secondo. Nove corse fra il 4 e il 6
danno da **−14,2 %** a **+53,7 %**, con tre valori negativi: non è rumore attorno a un valore, è un
rapporto fra due cose non confrontabili.

Quindi l'ADR che adotta un intervallo **non è stata scritta**, e la ragione va detta: un intervallo
che contiene −14 % e +54 % non è un atteso, è la confessione che la misura non misura. Il runbook
adesso dice che cosa non varia — le scritture non si fermano e sono tutte confermate, 275 su 275
nella registrazione attuale — e che la percentuale si legge sullo schermo qualunque sia. Rendere le
due finestre confrontabili, confrontando la **coda** della fase di carico lunga quanto il dump
invece dei dieci secondi interi, è una modifica alla scena e la decisione è del PO.

**Di passaggio, un quarto.** `/tmp/mongolab-backup` sta *dentro* `mongo-rs-1` e accumula un dump per
corsa, e non lo svuota `reset-demo.sh`. (La prima stesura di questa riga aggiungeva «né
`down`/`up`»: è falso, ed era un ragionamento e non una misura — `down` rimuove il container e
`/tmp` non è un volume, misurato poche ore dopo in [V-091](Sources.md#v-091).) Alla prima ripresa della scena 14 il
`mongorestore` ha rimesso in piedi **sei** collezioni di carico invece di una, e su uno schermo
proiettato è rumore. Tolto a mano per registrare, scritto nel runbook, e se debba entrare in
`reset-demo.sh` è la stessa domanda di stamattina su `lab_ripristinato`: la decide il PO.

Registrazioni rigirate: la **10** (2,3 s, `ordini · 50 000` e `lab · 50 000` sullo stack pulito), la
**13** (11,3 s, 506/s → 516/s, −1,9 %) e la **14** (3,7 s, 5 386 all'origine · 5 295 nella copia ·
differenza 91), che non poteva restare ferma perché conta ciò che la 13 ha copiato. Tutte e tre
riprodotte con `--riproduci` prima di dichiararle buone. Le due pagine che citano la vecchia uscita
di `stats` e la voce [V-089](Sources.md#v-089) **non** sono state toccate: sono verbali datati, non
descrizioni dello strumento di oggi.

### Note di metodo

247. **Una prova che legge il file non sostituisce una corsa che legge il server, e va programmata
    nello stesso compito.** La prova rossa del drop verificava un'affermazione vera — il nome è
    scritto nello script — mentre la cosa che contava, il verdetto, era falsa. Non è una prova
    scritta male: è una prova che non poteva sapere. Il difetto stava in una risposta del server, e
    solo il server poteva darla. La regola pratica: quando la prova può affermare solo sull'artefatto,
    la corsa dal vivo fa parte dello stesso compito, non del giro dopo — e le corse sono **due**, una
    per faccia del ramo.
248. **Prima di spiegare perché un rapporto varia, si controlla che i due termini siano
    confrontabili.** Del calo dell'Atto III si sono cercate le cause fuori — la resa Rich, la contesa
    fra stack, il portatile carico — per quattro corse. La risposta stava dentro, negli istanti delle
    fasi già scritti nel `.cast`: dieci secondi contro mezzo secondo. Leggerli è costato trenta
    secondi. La regola pratica: un rapporto fra due medie non si interpreta prima di aver guardato
    quanto dura, e quanto contiene, ciascuna delle due.
249. **Le parole «deve» e «sempre» in una docstring sono un debito, e si paga quando i dati
    crescono.** «Fuori da uno sharded cluster i due numeri devono coincidere» era vero per la prova
    che lo scriveva, sedici documenti in un database appena creato, e falso sullo stesso stack con un
    milione e mezzo. Una docstring che generalizza dal caso di prova promette a nome di un dominio
    che non ha autorizzato nessuno. La regola pratica: se la frase dice «deve», o c'è la misura che
    lo regge o si scrive che cosa vale **qui**.

Stato aggiornato: decisioni fino ad **ADR-0121**, verifiche fino a **V-090**, misure fino a
**M-059**, note di metodo fino alla **249**. Controlli: `make docs-check` verde, `make tools-test`
**178 passate**, `pytest` dell'applicazione **711 passate**, `mypy` pulito su 66 file. Prossimo
passo: le due decisioni che restano al PO — se rendere confrontabili le due finestre dell'Atto III,
e se `reset-demo.sh` debba svuotare anche `/tmp/mongolab-backup` — e la discussione sulle priorità,
che aspetta il suo giro con gli stack accesi.

## 2026-09-06 — La cartella che nessuno nominava

Il Product Owner ha risposto anche alla seconda domanda aperta: sì, `reset-demo.sh` deve svuotare
anche `/tmp/mongolab-backup`. Fatto — [ADR-0122](Decision.md#adr-0122), verificato in
[V-091](Sources.md#v-091) — e come le tre di prima ha lasciato per strada qualcosa che la domanda
non conteneva, stavolta una frase scritta poche ore prima in questo stesso registro.

**Il criterio di ADR-0088 si legge in avanti.** Quella decisione aveva dato la pulizia a
`reset-demo` con un criterio scritto dentro un database: «spazza tutto ciò che non è `ordini`». Ha
retto finché la demo lasciava in giro solo collezioni. La copia del backup non è una collezione e
non è un volume: è una cartella nel livello scrivibile di `mongo-rs-1`, e per questo non la toglieva
nessuno — non perché qualcuno avesse deciso di lasciarla, ma perché **nessuna delle regole scritte
la nominava**. Adesso lo script la toglie, e il criterio dice ciò che vuol dire: `reset-demo`
riporta allo stato da cui la scena comincia, e lo stato è tutto quello che una corsa lascia dietro.

**Il verdetto guarda prima, di nuovo.** `rm -rf` esce zero tanto se la cartella c'era quanto se non
c'era: è il difetto del `dropDatabase` di stamattina con un altro comando, e la prova
`test_il_verdetto_della_cartella_guarda_prima_di_togliere` lo vieta chiedendo che il `ls` stia prima
del `rm`. Il numero che lo script dice conta i `.bson` sotto `lab` e non i file del dump: nella
copia ci sono anche `admin/` e `oplog.bson`, che il restore esclude con `--nsInclude lab.*`, e il
numero da dire è quello che ricompare sullo schermo. Due rami, due corse dal vivo: «dump rimossi: 2
collezioni che il restore avrebbe rimesso in piedi» e, subito dopo, «nessun dump da togliere».

**E la frase sbagliata.** La voce di stamattina diceva che quella cartella «non la svuota nessuno,
né `reset-demo.sh` né `down`/`up`». La prima metà era misurata, la seconda no: era un'inferenza
detta con lo stesso tono. Misurata adesso — marcatore con `mkdir`, `make down-02`, `make up-02` — in
`/tmp` resta solo `mongodb-27017.sock`. `mongo-rs-1` monta `keyfile` e `dati-1:/data/db` e
nient'altro, quindi `/tmp` è il livello scrivibile del container e `docker compose down` il
container lo rimuove. La riga è stata corretta sul posto, dicendo che era stata corretta: un
registro che si riscrive in silenzio non è più un registro.

### Note di metodo

250. **Una frase che nasce da un ragionamento e una che nasce da una misura si scrivono uguali, e
    per questo bisogna scriverle diverse.** «Non lo svuota né `reset-demo.sh` né `down`/`up`»: la
    prima metà veniva da una corsa, la seconda da un'idea di come funzionano i container, e nel
    periodo stavano fianco a fianco con lo stesso tono. La regola pratica: quando un elenco mette
    insieme cose viste e cose dedotte, o si misura anche il resto o si spezza la frase — accanto a
    ciò che è misurato ci sta il comando, accanto al resto ci sta «probabilmente».
251. **Una prova che misura l'ordine dentro un file misura anche i commenti.** L'asserzione
    «il `ls` viene prima del `rm`» è fallita sul blocco appena scritto, e il blocco era giusto: a
    nominare `rm -rf` per primo era il commento che spiega perché `rm -rf` da solo non basta. La
    prova accusava la spiegazione al posto del codice. La regola pratica: se la proprietà riguarda i
    comandi, il testo su cui si misura sono i comandi — le righe di commento si tolgono prima, e la
    prova lo dice nel proprio corpo perché nessuno le rimetta.

Stato aggiornato: decisioni fino ad **ADR-0122**, verifiche fino a **V-091**, misure fino a
**M-059**, note di metodo fino alla **251**. Controlli: `make docs-check` verde, `make tools-test`
**180 passate**, `pytest` dell'applicazione **711 passate**. Resta aperta **una** decisione del PO:
se rendere confrontabili le due finestre dell'Atto III. Poi la discussione sulle priorità, che
aspetta il suo giro con gli stack accesi.

## 2026-09-06 — Dodici skill da un altro repository, e undici che qui non funzionavano

Il Product Owner ha chiesto di riprendere dal repository d'origine, ramo
`step/azure-policy/allineamento-e-fase-1`, il contenuto di `.claude/skills` e di
`Docs/Concetti-Generali`, e di incorporarlo nella release. Sembrava un trasporto di file. Era una
misura — [ADR-0123](Decision.md#adr-0123), verificata in [V-092](Sources.md#v-092).

**Una skill non è documentazione.** È l'unica cosa che entra in un repository e poi si accende da
sola: durante una sessione, quando il modello giudica che il caso sia suo, e da quel momento
indirizza il lavoro. Il campo che decide se si accende è la `description` del frontmatter, ed è
l'unica parte che non si può correggere da fuori — un blocco in testa, una nota nella pagina di
provenienza, una scheda: tutto arriva **dopo** che la skill si è già presentata.

**Undici su dodici, verbatim, erano o mute o fuori bersaglio.** Nove nominano il repository
d'origine come condizione, e qui non si sarebbero accese mai. Due lo nominano **per negazione** —
«use when the repository is NOT the origin one» — e quelle qui si accendono sempre, cioè
esattamente dove non dovrebbero. Una è generica e scrive gli ADR in `docs/adr/`, che qui non
esiste. Il censimento è sintattico e legge il testo, non il comportamento: la riserva sta scritta
in V-092.

**Il pericolo aveva la forma giusta.** Fra le due che si accendono c'è `git-flow`, e il suo
`references/comandi.md` elenca `git flow feature finish`: il comando vietato qui da quando, sulla
PR #1, chiuse un ramo saltando la revisione. Il modello dei rami di questo repository **ha la forma**
di Git Flow — `main`, `develop`, `feature/NN-nome`, `release/1.0` — e differisce solo nella
chiusura. Una skill che si accende da sola e propone quel comando non è un testo di riferimento
sbagliato di poco: è una trappola che somiglia alla verità.

**Verbatim prima, adattamento dopo.** Il pacchetto è entrato byte per byte in `65385ec`, verificato
con `diff -r` contro il clone e passato al setaccio dei segreti — una segnalazione, una fixture,
esclusa confrontando i prefissi SHA-256 senza stampare né l'una né l'altra. L'adattamento è il
commit successivo, `25b5df6`: dieci righe per file, 108 in tutto, la `description` e un blocco in
testa. **I corpi restano quelli del repository d'origine**, e non per pigrizia: con i corpi
intatti un miglioramento fatto a monte si riporta con un diff, con i corpi riscritti si riporta
con una fusione a mano. È il prezzo che il runbook d'origine dichiara, e conviene tenerlo basso.

**La regola che rende innocuo tutto il resto sta in dodici posti.** In conflitto fra una skill e una
scheda accettata di `docs/Decision.md`, vince la scheda — ripetuta nel blocco in testa a ognuna, non
solo nella pagina di provenienza, perché una skill si presenta in mezzo a un lavoro e la regola
deve stare dove arriva l'interruzione.

**Poi i tre documenti**, in `docs/06-sviluppo/concetti-generali/`. Due intatti; il runbook adattato
perché citava undici schede del repository d'origine con collegamenti relativi che qui puntano nel
vuoto, e un rimando che si apre sulla pagina sbagliata è peggio di nessun rimando. Il README nuovo
è la pagina che i dodici blocchi già citavano: provenienza, regola di precedenza, divergenze
misurate, verdetto per skill, e il prezzo dichiarato.

**Il vuoto che l'import ha scoperto.** Questo repository **non ha una scheda** che fissi il proprio
modello dei rami, la strategia di merge o lo standard dei messaggi di commit. La pratica c'è, è
coerente, ed è scritta in
[`worktree-e-branch-di-lavoro.md`](06-sviluppo/worktree-e-branch-di-lavoro.md) — ma non è mai stata
registrata come decisione, e in centoventitré schede nessuno se n'era accorto. Se n'è accorto adesso
un pacchetto importato che quelle decisioni le pretende: `git flow feature finish` è vietato, e
cercando la scheda che lo vieta non c'è.

### Note di metodo

252. **Ciò che si accende da sola va misurato prima di installarlo, e la misura è il suo testo di
    innesco.** Dodici skill sono arrivate come file, e la domanda ovvia era se funzionassero: le
    prove dicono di sì, 127 passate. La domanda giusta era un'altra — se si accendessero **qui** — e
    la risposta stava in dodici righe di frontmatter, non nelle 127 prove. La regola pratica: quando
    si importa materiale attivo, si legge per primo il campo che decide quando si attiva; il
    collaudo prova che il codice è portabile, non che sia pertinente.
253. **Un verdetto negativo scritto vale quanto uno positivo, e costa una riga.** Sette skill su
    dodici qui non governano, e la scelta era fra toglierle e tenerle con scritto sopra che non
    governano. Toglierle costa una ricerca il giorno che serviranno; tenerle mute costa un dubbio
    ogni volta che qualcuno le apre. Tenerle **con il verdetto in testa** costa una tabella. La
    regola pratica: quando si scarta qualcosa che potrebbe tornare utile, si scarta per iscritto e
    nel posto dove verrà riletto — «non governa qui, ed ecco perché» è informazione, il silenzio no.
254. **Una somiglianza forte è più pericolosa di una differenza.** `git-flow` non è stato pericoloso
    perché descriva un modello estraneo, ma perché ne descrive uno quasi identico al nostro: stessi
    nomi di ramo, stesse direzioni di merge, una sola differenza — la chiusura. Un testo palesemente
    fuori contesto lo si scarta a colpo d'occhio; uno che combacia per il 90% lo si segue fino al
    10% che non combacia. La regola pratica: quando si importa un modello simile al proprio, si
    documenta la differenza, non l'affinità.

Stato aggiornato: decisioni fino ad **ADR-0123**, verifiche fino a **V-092**, misure fino a
**M-059**, note di metodo fino alla **254**. Controlli: `make docs-check` verde, `make tools-test`
**180 passate**, `make app-test` **650 passate** (più le 61 di integrazione, che chiedono Docker:
711 in tutto), le tre suite delle skill **127 passate**. Resta aperta **una** decisione del PO: se
rendere confrontabili le due finestre dell'Atto III. Poi la discussione sulle priorità, che aspetta
il suo giro con gli stack accesi, e la review generale della release, chiesta e non ancora fatta.
