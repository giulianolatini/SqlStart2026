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
