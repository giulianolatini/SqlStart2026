# Revisione della PR #documentazione-tecnica — foglio di triage

Prodotto da `.claude/skills/revisione-pr/scripts/revisione.sh`. I rilievi arrivano da due revisori esterni e **non sono ancora un giudizio**: lo diventano quando ogni scheda ha un verdetto motivato scritto sotto.

**9 rilievi** — Codex (codex): 7, Gemini Pro (agy): 2.

| ID | Gravità | Confidenza | Categoria | Titolo | Verdetto |
|---|---|---|---|---|---|
| C-4 | alta | alta | security | La pulizia di un dump fallito può cancellare una directory preesistente | **accolto · riprodotto · corretto** |
| C-5 | alta | alta | altro | La prova di restore cancella il database anche se il dump è fallito | **accolto · secondo rimedio respinto · corretto** |
| G-2 | alta | alta | security | Esposizione di credenziali in chiaro sulla riga di comando | **accolto sul fatto · rimedi respinti · pagina corretta** |
| C-2 | media | alta | congruita-commit | Un commit docs include una modifica al comportamento dello smoke test | **accolto sul fatto · esteso a dieci commit · sede da aprire** |
| C-3 | media | alta | security | Gli esempi espongono password e keyfile negli argomenti dei processi | **accolto in parte · falso sul keyfile · misura estesa** |
| C-6 | media | alta | altro | La perdita di uno shard è descritta come restituzione silenziosa di dati parziali | **accolto ed esteso · misurato · due sezioni corrette** |
| C-7 | media | alta | altro | La rotazione con cambio di identità è presentata come obbligatoria a ogni rinnovo | **accolto · la fonte era già nella pagina · corretto** |
| C-1 | bassa | alta | congruita-commit | I commit omettono sistematicamente l'ambito richiesto | **respinto sull'ambito · accolto in parte sul minuscolo · misurato** |
| G-1 | bassa | alta | congruita-commit | I messaggi di commit omettono l'ambito e non usano sempre il minuscolo | **respinto sull'ambito · come C-1 · esempio inventato** |

## C-4 — La pulizia di un dump fallito può cancellare una directory preesistente

*Sollevato da Codex (codex).*

- **Categoria:** security
- **Gravità:** alta
- **Confidenza:** alta
- **Dove:** docs/03-amministrazione/backup-restore.md, §5

**Evidenza citata dal revisore:**

```
mongodump --oplog --out "${DESTINAZIONE}" || { rm -rf "${DESTINAZIONE}"; exit 1; }
```

**Perché sarebbe un problema:** DESTINAZIONE non viene vincolata a una directory nuova e dedicata. Qualunque fallimento di mongodump, anche prima di scrivere per un errore di connessione, provoca la cancellazione ricorsiva dell'intera destinazione, inclusi eventuali backup precedenti o altri file.

**Rimedio proposto:** Creare una directory temporanea esclusiva con mktemp -d, cancellare soltanto quella in caso di errore e pubblicare il backup nella destinazione definitiva solo dopo la verifica.

### Verdetto

**Accolto, e riprodotto nel caso peggiore che il revisore nomina.** Il rilievo cita per esteso la
condizione che rende il difetto grave — «anche prima di scrivere, per un errore di connessione» —
ed è quella che è stata eseguita.

Sullo stack 02, una destinazione che contiene già qualcosa:

```
$ docker exec mongo-rs-1 ls -R /tmp/prova-c4
/tmp/prova-c4/dump-di-ieri/lab.bson

$ docker exec mongo-rs-1 mongodump --oplog --out /tmp/prova-c4 \
    -u admin -p credenziale-sbagliata --authenticationDatabase admin
Failed: can't create session: … auth error: … (AuthenticationFailed) Authentication failed.
uscita = 1

$ docker exec mongo-rs-1 rm -rf /tmp/prova-c4        # il ramo `||` della regola
$ docker exec mongo-rs-1 ls -la /tmp/prova-c4
ls: cannot access '/tmp/prova-c4': No such file or directory
```

`mongodump` è uscito **prima di creare un solo file**: ha fallito l'autenticazione, non ha scritto
nulla. La regola ha cancellato una cartella che quel comando non aveva mai toccato, e con essa il
backup che c'era dentro.

**La forma del difetto conta più del difetto.** La regola non è arbitraria: è stata estratta da un
guasto vero ([V-036](../Sources.md#v-036)) — lì il dump falliva **dopo** aver scritto 1,8 GB e
lasciava sul disco un oggetto che pesava come un backup e non lo era. Per quel guasto la regola è
giusta, e `rm -rf` è la risposta corretta: quei file li aveva creati il comando fallito. Il salto
è averla applicata a **tutti** i modi di fallire. Un fallimento precoce non lascia niente da
pulire, e la pulizia diventa distruzione di roba altrui. È un errore di quantificatore: misurato
su un caso, scritto come se valesse su una classe.

**Il rimedio proposto è giusto, e va accolto per intero** — anche perché non complica la regola,
la **fonda**. `mktemp -d` non serve a scegliere un percorso comodo: serve a stabilire che la
cartella l'ha creata lo script, ed è l'unico titolo che autorizza a cancellarla ricorsivamente. La
pubblicazione dopo la verifica è la seconda metà dello stesso ragionamento: finché il dump non ha
`oplog.bson` non è un backup, e non deve occupare il posto di quello buono.

Correzione applicata a `§5`: la regola passa da due righe a quattro, e la prima è quella che rende
lecite le altre.

## C-5 — La prova di restore cancella il database anche se il dump è fallito

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** alta
- **Confidenza:** alta
- **Dove:** docs/03-amministrazione/backup-restore.md, §7

**Evidenza citata dal revisore:**

```
--eval 'db.getSiblingDB("lab").dropDatabase()'
```

**Perché sarebbe un problema:** Il blocco copiabile esegue dump, cancellazione e restore come comandi indipendenti, senza interrompersi se il primo fallisce. È proprio il caso descritto nella stessa pagina: un dump fallito può lasciare file incompleti, mentre il comando successivo elimina comunque l'originale.

**Rimedio proposto:** Interrompere esplicitamente la procedura se il dump o la sua verifica falliscono; preferire una destinazione di restore usa-e-getta per la dimostrazione.

### Verdetto

**Accolto sul primo rimedio, respinto sul secondo.** La parte più affilata del rilievo non è nelle
parole del revisore: **§7 contraddice §5 della stessa pagina**. Due sezioni prima, con un guasto
misurato, la pagina stabilisce che un dump fallito lascia sul disco un oggetto che pesa come un
backup e non lo è, e che **l'unico segnale è il codice di uscita 1**. Poi §7 consegna al lettore
un blocco copiabile in cui nessuno legge quel codice di uscita, e in cui il secondo comando è
irreversibile. Una regola che non sta dentro il blocco che il lettore esegue non è una regola: è
un'osservazione.

Misurato sullo stack 02, sul caso esatto:

```
$ docker exec mongo-rs-1 mongodump --oplog --out /tmp/dump-c5 -u admin -p sbagliata …
Failed: … (AuthenticationFailed) Authentication failed.
uscita mongodump = 1

$ docker exec mongo-rs-1 test -f /tmp/dump-c5/oplog.bson
uscita test -f = 1
```

La guardia che la pagina già conosceva avrebbe fermato proprio questo. Che il seguito parta lo
stesso è misurato in **C-4**, qui sopra: lì il comando dopo il fallimento ha cancellato un backup
vero.

**Il secondo rimedio va respinto, per un motivo di merito.** «Preferire una destinazione di
restore usa-e-getta per la dimostrazione» toglie alla dimostrazione ciò che dimostra. Il punto di
§7 è perdere l'originale e riaverlo: è l'unico modo di vedere che il backup **è** un backup.
Ripristinare altrove prova che `mongorestore` scrive dei file, non che quei file bastano. La rete
di sicurezza esiste già ed è nominata nella pagina — `make reset-demo-02`.

**Un buco in più, trovato correggendo.** Il passo 1 scriveva in `/tmp/dump-02` senza svuotarlo: un
tentativo precedente lasciato lì avrebbe superato `test -f oplog.bson`, autorizzato la
cancellazione e fatto ripristinare i dati di ieri. Un `rm -rf /tmp/dump-02` prima del dump lo
chiude, ed è lecito perché quel percorso lo sceglie la pagina, dentro un container usa-e-getta: la
precondizione di **C-4**, rispettata.

Correzione applicata a `§7`: la cartella parte vuota, e il passo irreversibile sta dietro a un
`&&` che lo lega al controllo.

## G-2 — Esposizione di credenziali in chiaro sulla riga di comando

*Sollevato da Gemini Pro (agy).*

- **Categoria:** security
- **Gravità:** alta
- **Confidenza:** alta
- **Dove:** docs/02-architetture/replica-set.md

**Evidenza citata dal revisore:**

```
$ docker exec mongo-rs-1 mongosh --quiet -u admin -p "$PASSWORD" \
```

**Perché sarebbe un problema:** Passare una password tramite l'argomento `-p` sulla riga di comando la espone in chiaro nella lista dei processi (visibile a chiunque esegua `ps` sulla macchina host). Questo viola i principi base della gestione e manipolazione sicura dei segreti.

**Rimedio proposto:** Rimuovere l'argomento `-p "$PASSWORD"` dal comando per fare in modo che `mongosh` chieda la password interattivamente, oppure passarla in modo sicuro tramite variabile d'ambiente interpretata internamente dal container.

### Verdetto

**Accolto sul fatto, respinti tutti e due i rimedi, e il processo indicato è quello sbagliato.**
L'esposizione c'è. Non è dove il revisore la mette.

Questo repository l'ha già misurata ([V-047](../Sources.md#v-047)): `mongosh` 2.10.0 **riscrive il
proprio `argv`**, e nella tabella dei processi del container la password in chiaro compare
**zero** volte — si legge `mongodb://<credentials>@127.0.0.1:27017/…`. Dove resta in chiaro è
**sull'host**, nella riga di comando del client `docker`, che nessuno riscrive. Il rilievo dice
«visibile a chiunque esegua `ps` sulla macchina host» e su questo ha ragione; dice anche che a
esporla è l'argomento `-p` di `mongosh`, e su questo no. Espone il processo che lo lancia, non
quello lanciato — differenza che conta, perché suggerisce rimedi sul processo sbagliato. Ed è
esattamente quello che è successo.

**Primo rimedio — «rimuovere `-p` e far chiedere la password interattivamente». Provato, non
funziona nella forma che la pagina usa:**

```
$ docker exec mongo-rs-1 mongosh --quiet -u admin --authenticationDatabase admin --eval '…'
Enter password:
MongoServerError: Authentication failed.
uscita = 1
```

`docker exec` senza `-it` non dà un terminale: `mongosh` stampa la richiesta, legge il vuoto e
fallisce. Il rimedio richiederebbe di cambiare anche `docker exec` in `docker exec -it`, e
varrebbe solo per un umano che digita: gli stessi comandi, dentro `tools/`, resterebbero senza
soluzione. Una pagina che mostra una forma che gli script non possono usare insegna una forma che
non sopravvive all'automazione.

**Secondo rimedio — «passarla tramite variabile d'ambiente interpretata dal container». Non
esiste, ed è già stato provato che la sua realizzazione più vicina peggiora le cose.** `mongosh
--help` sulla 2.10.0 elenca **due** sole opzioni per una password, entrambe con argomento sulla
riga di comando: nessuna variabile d'ambiente. E il tentativo di avvicinarcisi con `-e SEGRETO=…`
sul client `docker` è stato misurato: mette una **seconda** copia della password proprio sulla
riga che espone davvero, contate due invece di una. Era codice che nessuno leggeva e che il
commento presentava come cautela; [ADR-0054](../Decision.md#adr-0054) l'ha rimosso per questo.
Adottare il rimedio proposto significherebbe rimettere il difetto che una revisione precedente ha
già fatto togliere.

**Che cosa mancava davvero.** [ADR-0054](../Decision.md#adr-0054) non decide solo dove passa la
password: decide che **chi mostra il comando descriva l'esposizione vera**. Lo chiedeva al
commento di uno script, e il commento è stato corretto. La pagina no — nominava `.env` fuori dal
repository e taceva la tabella dei processi. Una decisione applicata in una sede sola non è
applicata: è un'abitudine di quella sede.

Correzione applicata a `§6`: la pagina dice dove la password si legge e dove non si legge, con la
misura accanto.

## C-2 — Un commit docs include una modifica al comportamento dello smoke test

*Sollevato da Codex (codex).*

- **Categoria:** congruita-commit
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** 9d95b55e

**Evidenza citata dal revisore:**

```
tools/smoke-sharded.sh verificava un'uguaglianza a quattro, adesso
verifica un pavimento.
```

**Perché sarebbe un problema:** Il corpo dichiara una modifica alle condizioni con cui un controllo automatico accetta lo stack, mentre il tipo docs presenta il commit come documentale. Il diff dello script non è incluso, quindi non è verificabile la correttezza della modifica, ma la discrepanza di classificazione è esplicita nel messaggio.

**Rimedio proposto:** Separare la correzione dello smoke test in un commit fix e mantenere in docs il relativo aggiornamento documentale.

### Verdetto

**Accolto sul fatto, esteso dalla misura, e senza azione retroattiva.**

Il rilievo è vero, e la sua prova è il corpo del commit che contesta. Verificato: `9d95b55e` è
tipizzato `docs:`, tocca 12 file, e uno è `tools/smoke-sharded.sh` — 20 righe aggiunte, 8 tolte.
Il diff sostituisce `CHUNK_ATTESI=4`, un'uguaglianza esatta, con `CHUNK_MINIMI=2` e
`CHUNK_INIZIALI=4`, cioè un pavimento: l'AutoMerger fonde i chunk contigui a ogni `up`, e
l'uguaglianza a quattro falliva per un comportamento normale di MongoDB. La modifica è fondata —
cita S-072, V-062 e ADR-0069 — ed è dichiarata per esteso nel corpo. Resta che il criterio con cui
un controllo automatico accetta lo stack è cambiato dentro un commit che si presenta come
documentale.

**Non è un caso isolato: è il decimo.** Misurato su tutta la storia del ramo — 63 commit toccano
`tools/` o il codice dell'applicazione, e **dieci di questi sono tipizzati `docs:`**, per 682
righe di codice aggiunte e 36 tolte. Due creano un file intero:

| commit | righe | che cosa |
|---|---|---|
| `1b92a79` | 365 | crea `tools/demo-sharded.sh` e tre bersagli del Makefile |
| `eb3c54a` | 188 | crea `tools/tests/test_coerenza_repo.py` |
| `bd0a091` | 59 | cambia `tools/check_stack.py` e la sua prova |
| `9d95b55` | 20 | **questo** |
| altri sei | 50 | script di supporto, versioni delle immagini |

Il revisore ha trovato l'istanza più **trasparente** dell'abitudine, non la peggiore. `9d95b55e`
dichiara la sua riga di codice in tre righe di corpo che la spiegano; `1b92a79` dichiara la
nascita di uno script da 361 righe — quello che oggi fornisce `make guasto-03`. Il corpo è sempre
onesto. È il tipo che non lo è.

**Perché succede, e non è distrazione.** Qui il tipo del commit descrive **lo scopo del task**,
non gli artefatti toccati. Un task che salda debiti di documentazione resta `docs:` anche se per
saldarli tocca correggere lo script che quei debiti aveva prodotto. Il revisore legge il tipo come
una promessa sul contenuto — «qui dentro non c'è codice» — e ha ragione a leggerlo così, perché è
quello che Conventional Commits promette. Sono due convenzioni diverse che usano le stesse cinque
lettere.

Il costo è concreto e si paga due volte: chi cerca nella storia quando è cambiato il criterio di
accettazione dello smoke test non guarda fra i `docs:`, e un `revert` della documentazione
porterebbe via con sé la correzione del test.

**Il rimedio proposto non è applicabile.** «Separare la correzione in un commit `fix`» chiede di
dividere un commit già unito e già spinto, dentro una storia che cinque PR hanno chiuso. Il valore
che si comprerebbe riscrivendola — la ricercabilità — si compra meglio in avanti, e a un prezzo
molto più basso.

**Quello che manca davvero è la sede, e il repository lo sa già.**
[ADR-0123](../Decision.md#adr-0123) si chiude dichiarando esattamente questo vuoto: «questo
repository non ha una scheda che fissi il proprio modello dei rami, la strategia di merge o lo
standard dei messaggi di commit». Finché la regola non è scritta qui, ogni revisione esterna andrà
a prenderla dove la trova — e dove la trova oggi è il prompt importato, che descrive la
convenzione del repository d'origine. È la stessa lacuna su cui poggiano C-1 e G-1 qui sotto, e i
cinque gemelli già chiusi negli altri dossier.

Azione, in avanti: la scheda che fissa la convenzione va scritta, e deve dire **anche** che cosa
fa il tipo quando un task ne attraversa due. Non è un dettaglio di forma. È la differenza fra
dieci commit conformi e dieci commit fuori regola, a parità di storia.

## C-3 — Gli esempi espongono password e keyfile negli argomenti dei processi

*Sollevato da Codex (codex).*

- **Categoria:** security
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** docs/03-amministrazione/sicurezza-keyfile-x509.md, §4.1; docs/03-amministrazione/backup-restore.md, §§2 e 7

**Evidenza citata dal revisore:**

```
mongosh -u __system -p "$(tr -d '\n\r ' < /keyfile/mongo-keyfile)" --authenticationDatabase local
```

**Perché sarebbe un problema:** La sostituzione inserisce il segreto interno del cluster direttamente in argv; altri esempi fanno lo stesso con la password amministrativa. Il dossier dimostra già che «un ps -eo args dentro il container lo mostra a chiunque»: usare una variabile o leggere il keyfile non evita questa esposizione.

**Rimedio proposto:** Usare il prompt interattivo oppure il passaggio protetto tramite stdin già adottato dall'applicazione, eliminando password e contenuto del keyfile da argv.

### Verdetto

**Accolto in parte, e la parte respinta è quella che il revisore riteneva dimostrata.** Il rilievo
mette insieme due esempi che si comportano in modo **opposto**, e la differenza è misurabile.

**Sul keyfile (`sicurezza-keyfile-x509.md` §4.1): respinto, per due ragioni indipendenti.**

La prima è di fatto. Il comando citato è `mongosh`, e `mongosh` 2.10.0 riscrive il proprio `argv`:
dentro il container `ps -eo args` conta **zero** occorrenze del segreto e mostra
`mongodb://<credentials>@…` ([V-047](../Sources.md#v-047)). La frase che il rilievo cita come
prova — «un `ps -eo args` dentro il container lo mostra a chiunque» — sta a `backup-restore.md`
§8, dove parla di `mongodump` e `mongorestore`, e per quegli strumenti è vera. Applicarla a
`mongosh` è trasportare una misura da uno strumento a un altro dove la stessa misura dice il
contrario. Va aggiunto che nemmeno l'host la vede: la sostituzione `$(tr -d … < /keyfile/…)` la
esegue la shell **dentro** il container, e sull'host — se ci si arriva da `docker exec` — resta il
testo letterale `$(tr …)`, non il valore.

La seconda è di modello di minaccia, e da sola basterebbe. Chi può eseguire `ps` dentro quel
container può eseguire `cat /keyfile/mongo-keyfile`. Il keyfile **è montato lì**: è il presupposto
del comando, non un suo effetto collaterale. Nascondere il segreto in `argv` proteggerebbe da un
osservatore che ha già tutto ciò che serve — è la pagina stessa a dirlo due righe sotto: «Chi lo
ha, **è** il cluster».

**Sui comandi di backup (`backup-restore.md` §§2 e 7): accolto sul fatto, già scritto, e la misura
è stata estesa.** Lì l'esposizione dentro il container è reale.
[M-025](../../app/docs/Sources.md#m-025) l'aveva misurata su `mongorestore` 100.18.0 — 16 campioni
su 16 — e chiudeva dichiarando una riserva: «Non è stato verificato se `mongodump` riscriva `argv`
dopo l'avvio». Verificato adesso, con una sentinella al posto della password:

```
$ docker exec mongo-rs-1 ps -eo args | grep mongodump
mongodump --host 192.0.2.1:27017 -u admin -p SENTINELLA-NON-E-UNA-PASSWORD-VERA …
```

`mongodump` non si oscura ([V-096](../Sources.md#v-096)). La riserva di M-025 si chiude, e la
regola che ne esce non è «`-p` espone» ma «**dipende dallo strumento, e il modo di saperlo è
provarlo**».

**Il rimedio proposto esiste già ed è adottato dove conta.** «Il passaggio protetto tramite stdin
già adottato dall'applicazione» è [ADR-0054](../Decision.md#adr-0054), ed è la ragione per cui il
§8 mostra una riga proiettabile senza password. Il §7 mostra apposta l'altra: è la sezione in cui
i comandi si danno a mano per scoprire che cosa fanno, e trasformarla nella versione
dell'applicazione cancellerebbe il confronto che i due blocchi accostati esistono per fare.

Quello che mancava è che il §7 tacesse ciò che il §8 dice, a centoventi righe di distanza — e il
lettore che copia il §7 non arriva al §8.

Correzione applicata a `§7`: la nota su dove la credenziale si legge sta accanto ai comandi che la
mostrano, con la differenza fra gli strumenti e la misura di ciascuno.

## C-6 — La perdita di uno shard è descritta come restituzione silenziosa di dati parziali

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** docs/02-architetture/sharded-cluster.md, §1.2

**Evidenza citata dal revisore:**

```
continua a rispondere **su una parte dei dati**, senza dire al client che l'altra parte non c'è
```

**Perché sarebbe un problema:** La frase suggerisce che una query possa ricevere normalmente risultati incompleti senza errore. La §6.4 dello stesso documento precisa invece che una query diretta allo shard indisponibile o in broadcast fallisce: la disponibilità parziale riguarda quali query possono riuscire, non una mutilazione silenziosa generalizzata dei risultati.

**Rimedio proposto:** Allineare l'apertura alla §6.4, distinguendo le query interamente servite dagli shard sani dalle query che richiedono shard indisponibili.

### Verdetto

**Accolto, ed esteso: aveva ragione il revisore, e la sezione con cui chiedeva di allineare
affermava a sua volta più di quanto la sua fonte dicesse.**

La contraddizione è reale. Il §1.2 scriveva «senza dire al client che l'altra parte non c'è», cioè
risultati parziali restituiti in silenzio; il §6.4 diceva che le query sullo shard perduto
falliscono. Delle due, quella da tenere è la seconda — ma nessuna delle due era misurata: il §6.4
citava [S-069](../Sources.md#s-069), che dice soltanto «reads or writes directed at the available
shards can still succeed» e **non** dice che le altre falliscano.

Misurato eseguendo la scena che il repository ha già, `make guasto-03` — che ferma un membro e lo
rialza da sé:

```
$ docker compose stop shard1a
  l'ordine su shard2rs: trovato: 3   [1 s]
  l'ordine su shard1rs: ✗ FailedToSatisfyReadPreference: Could not find host matching
                          read preference { mode: "primary" } for set shard1rs   [16 s]
  il conteggio totale:  ✗ FailedToSatisfyReadPreference: … for set shard1rs        [16 s]
$ docker compose start shard1a
  shard1a è tornato e il totale è di nuovo 20000   [3 s dal comando]
```

Il §1.2 era **falso** su tutti e due i punti che affermava. Il client viene informato — riceve un
errore, non dati mutilati — e l'errore **nomina** lo shard che manca. La disponibilità parziale
non è una fetta silenziosa di verità: è un fallimento esplicito su un sottoinsieme di query.

**Quello che la misura aggiunge, e che nessuna delle due sezioni aveva.** Il costo non è la
silenziosità, è il **tempo**: sedici secondi prima dell'errore, contro un secondo per la query che
passa. È il router che cerca un primario per `shard1rs` finché la selezione del server non scade.
Detta così la lezione cambia destinatario: non «attento, potresti leggere dati incompleti», ma
«attento, un ramo delle tue query smetterà di rispondere per sedici secondi alla volta». La prima
mette in guardia da un pericolo che non c'è; la seconda descrive quello che succede davvero.

**Resta dichiarato ciò che non è stato provato.** «Una in broadcast fallisce anche se i dati che
le servivano stavano dalla parte viva» era, ed è, un ragionamento: deve valere per costruzione,
perché il router manda a tutti proprio in quanto non sa dove siano i documenti. Il conteggio
totale misurato è un broadcast che i due shard li vuole entrambi, quindi non discrimina il caso.
La frase resta, marcata come dedotta invece che vista.

Correzioni applicate: `§1.2` dice che l'errore arriva e chi nomina; `§6.4` porta l'errore per
esteso, i due tempi, e la riserva sul broadcast.

## C-7 — La rotazione con cambio di identità è presentata come obbligatoria a ogni rinnovo

*Sollevato da Codex (codex).*

- **Categoria:** altro
- **Gravità:** media
- **Confidenza:** alta
- **Dove:** docs/03-amministrazione/sicurezza-keyfile-x509.md, §3.5

**Evidenza citata dal revisore:**

```
Tre giri di riavvii, da programmare prima della scadenza,
per ogni cluster, per sempre.
```

**Perché sarebbe un problema:** La procedura descritta parte esplicitamente dalla sostituzione con un certificato avente DN diverso e introduce un override per accettare entrambe le identità. La scadenza non implica il cambiamento degli attributi identificativi: generalizzare quel costo a ogni rinnovo sovrastima la manutenzione X.509 e altera il confronto con il keyfile.

**Rimedio proposto:** Separare il rinnovo dei certificati a identità invariata dalla migrazione degli attributi O, OU e DC; attribuire i tre giri di riavvii soltanto alla seconda procedura descritta.

### Verdetto

**Accolto, e il documento conteneva già la fonte che lo smentiva.** Il §3.5 citava
[S-063](../Sources.md#s-063) per esteso — «The certificates match if their subjects contain the
same values for the Organization (`O`), Organizational Unit (`OU`), and Domain Component (`DC`)
attributes» — e poi ne traeva la conclusione opposta. Se il confronto guarda quei tre attributi,
un certificato rinnovato che li conserva **corrisponde**: la scadenza non entra nel confronto, e i
nodi continuano a riconoscersi. Il parametro-ponte serve quando il `DN` cambia, non quando il
certificato invecchia.

Nessuna misura da fare: la citazione era già nella pagina, tre paragrafi sopra la frase che la
contraddiceva. È il modo più comune di sbagliare una pagina documentata — la fonte è giusta, il
riassunto no, e nessuno rilegge il riassunto contro la fonte perché la fonte l'ha scelta lui.

**Quanto pesa l'errore.** La frase «Tre giri di riavvii, da programmare prima della scadenza, per
ogni cluster, per sempre» sta nel punto in cui la pagina tira la somma del confronto fra X.509 e
keyfile. Moltiplicava per tre proprio la voce su cui quel confronto si regge, e lo faceva
nell'unica riga che un lettore di fretta si porta via. Un argomento gonfiato non è più forte: è
più fragile, perché chi conosce X.509 lo smonta in una domanda e con esso smonta la parte vera.

**La parte vera resta, e adesso è difendibile.** Il rinnovo è manutenzione periodica obbligatoria:
un rolling restart a ogni scadenza, per ogni cluster, per sempre. Un keyfile non scade. Il divario
di gestibilità c'è tutto, alla sua misura, che è un terzo di quella dichiarata prima.

**Corretta anche la riserva, che ripeteva l'errore in forma più netta.** Diceva che la fonte
presenta l'override «come una scelta organizzativa … non come una manutenzione periodica
obbligata, che è invece quello che è». Sull'override la fonte ha ragione e la pagina aveva torto.
Ciò che è manutenzione periodica obbligata è il rinnovo, che l'override non lo usa.

**Il silenzio della fonte, che il revisore non tocca, resta e vale più dell'errore corretto.** La
pagina non dice come accorgersi che i certificati stanno per scadere, né che cosa succeda a un
cluster i cui certificati scadono mentre è in esercizio. Con il costo per scadenza ridimensionato,
quella lacuna diventa la voce più cara delle due: un giro di riavvii programmato costa poco, un
cluster che si spacca perché nessuno guardava il calendario costa tutto.

Correzione applicata a `§3.5`: rinnovo a identità invariata e migrazione del `DN` sono due
procedure separate, con il loro numero di riavvii ciascuna, e la somma finale è fatta sulla prima.

## C-1 — I commit omettono sistematicamente l'ambito richiesto

*Sollevato da Codex (codex).*

- **Categoria:** congruita-commit
- **Gravità:** bassa
- **Confidenza:** alta
- **Dove:** ed573f45 e gli altri 22 commit del dossier

**Evidenza citata dal revisore:**

```
docs: l'istanza singola con quattro limiti citabili, uno dei quali silenzioso
```

**Perché sarebbe un problema:** Tutti i soggetti omettono l'ambito, obbligatorio secondo la convenzione dichiarata del repository. Diversi soggetti introducono inoltre «Task» con iniziale maiuscola, contrariamente alla regola del soggetto italiano minuscolo.

**Rimedio proposto:** Uniformare i soggetti al formato tipo(ambito): soggetto, scegliendo l'ambito dalla cartella di progetto effettivamente interessata.

### Verdetto

**Respinto sul merito — sesto della stessa famiglia — con una parte accolta che i cinque gemelli
precedenti non contenevano.**

**Sull'ambito: respinto, per la ragione già scritta cinque volte.** La regola che entrambi i
revisori applicano sta in `.claude/skills/revisione-pr/prompt/revisione.md:12-13`, arrivata ieri
*verbatim* con l'import delle skill, e descrive la convenzione del repository d'origine. Misurato
di nuovo su tutta la storia: **0 commit con ambito su 160**, dei quali 155 hanno un prefisso
convenzionale — gli altri cinque sono quattro merge di PR e il commit iniziale. Zero su 155 non è
una violazione sistematica: è la convenzione di questo repository, applicata senza eccezioni da
agosto. E il rimedio proposto riscriverebbe una storia già spinta su `origin` e già chiusa da
cinque PR per allinearla a un metro che qui non è mai stato adottato.

**Sul minuscolo: accolto in parte, e la misura ridimensiona il resto.** Contati i soggetti che
cominciano con una maiuscola: **29 su 155**, e si dividono in due gruppi che non si giudicano allo
stesso modo.

- **13 sono identificatori:** `docs: ADR-0121 …`, `docs: V-004 …`, `chore: Makefile come punto
d'ingresso unico`, `docs: README di radice …`. Nessuna convenzione sensata li vuole minuscoli:
`adr-0121` non è lo stesso nome di `ADR-0121`, e in un repository dove ogni affermazione cita una
scheda, sminuscolarli renderebbe i soggetti meno cercabili senza renderli più conformi.
- **16 sono `Task N`,** il numero del task nel piano di implementazione — `feat: Task 8 — la
maggioranza persa, e un log che taceva`. Questo è il caso vero, e resta discutibile in entrambi i
sensi: è il riferimento a un artefatto numerato, come `ADR-0121`, ma è anche un nome comune con la
maiuscola. Misurata la loro distribuzione: stanno **tutti e sedici in due giorni**, il 31 agosto e
il 1 settembre, e dopo la forma non ricompare mai più. Non è un'abitudine in corso: è un'abitudine
finita, che i revisori hanno trovato perché il dossier legge la storia intera.

**Nessuna categoria residua:** zero soggetti cominciano con una maiuscola che non sia un
identificatore o `Task N`. La regola del minuscolo, di fatto, questo repository la rispetta — con
una convenzione implicita sulle eccezioni che nessuno ha mai scritto.

**Che cosa cambia rispetto ai cinque gemelli, e non è poco.** Due cose, emerse tutt'e due oggi.

La prima è **C-2, qui sopra**: il tipo del commit, qui, descrive lo scopo del task e non gli
artefatti toccati. La divergenza dal repository d'origine quindi non è una — l'ambito assente — ma
due, e la seconda non l'aveva notata nessuno perché nessun revisore l'aveva ancora contraddetta.

La seconda è che **la sede mancante adesso è dichiarata**: [ADR-0123](../Decision.md#adr-0123)
registra che questo repository non ha una scheda che fissi il proprio standard dei messaggi di
commit. Fino a ieri la convenzione era consuetudine; da oggi è consuetudine con un vuoto scritto
accanto. Sei rilievi su due revisori nascono da quel vuoto: la regola c'è, ma non essendo scritta
dove un revisore la cerca, ognuno va a prenderla dove la trova.

**Azione, doppia.** Correggere `prompt/revisione.md` — ambito **assente**, soggetto minuscolo
**salvo identificatori** — prima della prossima revisione e non dopo, perché finché resta com'è
produce rilievi plausibili e falsi, che è la stessa forma di guasto di
[ADR-0124](../Decision.md#adr-0124). E scrivere la scheda che manca, con dentro le tre cose che
oggi si sanno solo eseguendo `git log`: l'ambito non si usa, il tipo segue lo scopo del task, gli
identificatori tengono la maiuscola.

## G-1 — I messaggi di commit omettono l'ambito e non usano sempre il minuscolo

*Sollevato da Gemini Pro (agy).*

- **Categoria:** congruita-commit
- **Gravità:** bassa
- **Confidenza:** alta
- **Dove:** ed573f45

**Evidenza citata dal revisore:**

```
ed573f45 — docs: l'istanza singola con quattro limiti citabili, uno dei quali silenzioso
```

**Perché sarebbe un problema:** Il repository impone l'uso di Conventional Commits in cui l'ambito è obbligatorio e deve corrispondere alla cartella toccata (es. `docs(02-architetture): ...`). Tutti i commit nel dossier omettono l'ambito, e in alcuni casi il soggetto inizia con la lettera maiuscola contravvenendo alla regola indicata.

**Rimedio proposto:** Riscrivere i messaggi di commit aggiungendo l'ambito tra parentesi e uniformando l'iniziale del soggetto al minuscolo.

### Verdetto

**Respinto sull'ambito, accolto in parte sul minuscolo: stesso rilievo di C-1, sollevato
dall'altro revisore sullo stesso commit.** Il verdetto è quello, con le misure che lo reggono — 0
commit con ambito su 160, e 29 soggetti con la maiuscola di cui 13 identificatori e 16 `Task N`
concentrati in due giorni.

Vale la pena registrare una differenza fra i due, perché dice qualcosa sul metodo. Codex scrive
che l'ambito è «obbligatorio secondo la convenzione dichiarata del repository»; Gemini Pro va
oltre e inventa un esempio — «(es. `docs(02-architetture): ...`)» — che nel repository non compare
**mai**. La forma è verosimile, la cartella esiste davvero, e un lettore distratto la prenderebbe
per una citazione. Non lo è: è una ricostruzione a partire dalla regola letta nel prompt.

È lo stesso guasto di [ADR-0124](../Decision.md#adr-0124), un giro più in là. Là un doppio di
prova diceva sempre di sì; qui un revisore, ricevuto un metro sbagliato, non si limita ad
applicarlo — lo completa, riempiendo con un esempio plausibile lo spazio che la regola lasciava
vuoto. Un metro sbagliato non produce solo misure sbagliate: produce prove che sembrano citazioni.

