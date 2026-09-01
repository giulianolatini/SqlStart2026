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
