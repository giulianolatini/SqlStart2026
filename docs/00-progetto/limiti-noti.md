# Limiti noti del progetto

Registro dei confini dichiarati: dove il lab semplifica, dove la documentazione ufficiale non
ci copre, e dove un'affermazione comune non regge alla verifica. Sta qui perché un limite
taciuto diventa una domanda imbarazzante dal palco, mentre un limite scritto diventa
credibilità.

Ogni voce indica **come lo gestiamo**, perché un limite senza contromisura è solo una scusa.

---

## 1. Precisione delle unità: MiB, non MB

I limiti di GitHub sui file sono espressi in **mebibyte**: avviso a 50 MiB, blocco a 100 MiB,
25 MiB per il caricamento da browser, e la raccomandazione di restare sotto 1 GB di
repository. Scrivere «100 MB» è tecnicamente impreciso — 100 MiB sono 104.857.600 byte — ed è
esattamente il dettaglio che qualcuno fa notare.

**Come lo gestiamo:** in slide e in documentazione si scrive MiB. Fonte:
[S-021](../Sources.md#s-021).

---

## 2. Il funzionamento offline non è una modalità documentata di Compose

La parola «offline» non compare su nessuna pagina Docker consultata. Non esiste un interruttore
globale che dica a Compose di non toccare la rete. Il digest garantisce **quale** immagine
viene usata, non **se** si contatta il registry: nessuna pagina ufficiale afferma che
un'immagine pinnata a digest e già presente in cache eviti la rete.

**Come lo gestiamo:** `pull_policy: never` scritto fisso in ogni servizio di ogni file Compose,
senza variabile che possa sovrascriverlo ([ADR-0039](../Decision.md#adr-0039), che supera
[ADR-0018](../Decision.md#adr-0018)). `never` è l'unico valore con una frase documentale esplicita
sul non contattare il registry, e fallisce in modo rumoroso se l'immagine manca — comportamento
desiderabile: meglio scoprirlo al preflight che davanti al pubblico. Misurato: senza l'immagine in
cache l'avvio fallisce in 0,113 s, che è un tentativo di rete mai iniziato
([V-022](../Sources.md#v-022)). Fonte: [S-019](../Sources.md#s-019).

---

## 3. L'applicazione dei limiti di risorsa fuori da Swarm non è documentata

La pagina «Compose Deploy Specification» non contiene una sola occorrenza di «Swarm»,
«ignored» o «not supported» nel corpo dell'articolo. La frase storica che affermava
l'esclusione apparteneva al riferimento del formato v3, oggi ritirato e non più mantenuto. La
documentazione odierna **non conferma né smentisce** che `deploy.resources.limits` sia
applicato da `docker compose up`.

**Come lo gestiamo:** il lab usa la sintassi breve `mem_limit`/`cpus` per leggibilità e
portabilità, e l'efficacia dei limiti viene dimostrata **empiricamente** con `docker inspect`
sui campi `HostConfig.Memory` e `HostConfig.NanoCpus`, non asserita per citazione. Da notare
che la documentazione non presenta le due forme come alternative ma ne richiede la coerenza.
Fonti: [S-003](../Sources.md#s-003), [S-004](../Sources.md#s-004).

---

## 4. Il minimo della cache WiredTiger è al confine dei nostri limiti di memoria

La documentazione 8.x dichiara «Values can range from 0.256GB to 10000GB». Il progetto aveva
scelto `0.25 GB`, che sta **sotto** quel minimo. La frase è però sintatticamente ambigua —
compare in un periodo dedicato a `--wiredTigerCacheSizePct` — quindi il rischio è possibile,
non certo.

**Come lo gestiamo:** verifica empirica su MongoDB 8.x nello spike, prima di fissare i numeri.
Se `0.256` è il minimo reale, il bilancio delle risorse si stringe: un config server con
`mem_limit: 512m` e 256 MiB di cache lascia poco margine al resto del processo. Fonte:
[S-002](../Sources.md#s-002).

---

## 5. Due pagine del manuale MongoDB si contraddicono sui container

«WiredTiger Storage Engine» afferma che WiredTiger «may not account for the memory limits of
the specific container in certain cases» e prescrive di impostare la cache a mano. La pagina
`hostInfo`, stesso manuale e stessa versione, afferma l'opposto. Il manuale v5.0 archiviato era
affermativo senza riserve: la formulazione è stata indebolita, non chiarita.

**Come lo gestiamo:** non si afferma il rilevamento automatico. In demo si mostra il valore
reale con `db.hostInfo()` e la cache si imposta comunque in modo esplicito. Fonti:
[S-001](../Sources.md#s-001), [S-026](../Sources.md#s-026).

---

## 6. Affermazioni diffuse che nessuna fonte primaria enuncia

Tre cose che «si sanno» ma non risultano scritte in nessuna pagina ufficiale trovata:

| Affermazione | Stato reale | Fonte |
|---|---|---|
| L'eccezione localhost vale solo per connessioni da `127.0.0.1`/`::1` | il vincolo è implicito nel nome, mai enunciato; le stringhe `127.0.0.1`, `::1`, «loopback» non compaiono | [S-006](../Sources.md#s-006) |
| Con permessi troppo aperti sul keyfile mongod rifiuta di avviarsi | documentato il requisito, non il comportamento in caso di violazione; su Windows i permessi non sono controllati affatto | [S-005](../Sources.md#s-005) |
| I client si connettono ai membri usando i nomi host della configurazione del replica set | deducibile, mai affermato; esiste solo evidenza operativa indiretta | [S-020](../Sources.md#s-020) |

**Come lo gestiamo:** se una di queste compare in una spiegazione, va qualificata come
comportamento noto o osservato, mai introdotta con «la documentazione dice».

---

## 7. Due comportamenti di Compose da verificare sul campo

La documentazione dei profili copre una sola direzione: servizio con profilo esplicitamente
invocato che avvia le proprie dipendenze. Il caso inverso — un servizio **senza** profilo che
dichiara `depends_on` verso un servizio **con** profilo non attivo — non è trattato né nella
guida né nel riferimento dell'attributo. Analogamente, l'efficacia reale dei limiti di risorsa
resta da osservare (punto 3).

**Come lo gestiamo:** entrambi finiscono nello spike, e l'esito diventa una verifica empirica
`V-NNN` citabile. Fonte: [S-015](../Sources.md#s-015).

---

## 8. Limiti di `mongodump --oplog`

Non utilizzabile su sharded cluster. Incompatibile con `--db`, `--collection`,
`--dumpDbUsersAndRoles` e `--query`: serve il dump completo di un membro del replica set.
Fallisce se durante l'esecuzione un client esegue `renameCollection`, `$out`, `mapReduce`,
operazioni su utenti o ruoli, o `setDefaultRWConcern`.

**Come lo gestiamo:** la demo di backup a caldo avviene sul replica set, non sullo sharded, ed
è una scelta dichiarata, non una svista. Fonte: [S-011](../Sources.md#s-011).

---

## 9. Il keyfile è una semplificazione didattica

MongoDB raccomanda i keyfile «only for testing and development environments because of their
limited manageability and cryptographic strength», e indica X.509 per la produzione.

**Come lo gestiamo:** il lab usa il keyfile perché è l'autenticazione interna minima che rende
dimostrabile un replica set in pochi minuti. Il confronto esteso fra keyfile e X.509 appartiene
alla documentazione di amministrazione, non a una battuta sul palco. TLS resta documentato ma
non dimostrato dal vivo. Fonte: [S-005](../Sources.md#s-005).

---

## 10. Strumenti di test: nessuna scorciatoia disponibile

`testcontainers-python` non copre il caso d'uso: `MongoDbContainer` avvia solo istanze
standalone, e la classe `DockerCompose` esiste nel sorgente ma non compare nella documentazione
pubblicata. Costruirci sopra significherebbe dipendere da un'API senza garanzie di stabilità.

**Come lo gestiamo:** i test di integrazione girano contro gli stack Compose del repository.
Meno dipendenze, e i test eseguono esattamente ciò che il pubblico eseguirà a casa. Fonte:
[S-013](../Sources.md#s-013).

---

## 11. La thread-safety di Rich `Live` non è documentata

La parola «thread» non compare né nella guida al display dinamico né nel riferimento delle API.
Non esiste avvertenza documentata, né in un senso né nell'altro.

**Come lo gestiamo:** il problema viene aggirato invece che risolto. Il listener del driver
deposita un evento in una coda e ritorna subito; il ciclo di disegno legge dalla coda sul
thread principale. Un solo thread tocca `Live`, quindi la domanda non si pone. Fonti:
[S-018](../Sources.md#s-018), [S-010](../Sources.md#s-010).

---

## 12. Non tutte le pagine di un produttore sono documentazione

Le pagine sotto `/resources/products/fundamentals/` di MongoDB sono materiale divulgativo:
nessun comando, nessun file di configurazione, nessuna versione, nessuna data. Non possono
sostenere affermazioni versionate.

**Come lo gestiamo:** valgono come raccolta di collegamenti verso il manuale, mai come
citazione normativa. Fonte: [S-014](../Sources.md#s-014).
