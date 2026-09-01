// Sesto anello, e l'unico che riguarda i dati invece della topologia: distribuisce
// `lab.ordini` e la riempie.
//
// Gira dentro il one-shot `seed`, dopo `add-shard` e prima della sentinella `up-03`:
// quando `make up-03` torna, il cluster ha due shard registrati E i documenti dentro,
// perché è così che si comportano già gli stack 01 e 02, e una demo che dopo l'avvio
// chiede ancora un comando è una demo con un passo in più da ricordare a memoria.
//
// Parla a `mongos`, autenticato, come `20-add-shard.js` e per la stessa ragione:
// `sh.shardCollection()` è un comando da router.
//
// ============================================================================
// LA SHARD KEY. È la scelta che il Blocco 3 del talk esiste per spiegare, e sta
// qui per intero perché questo è l'unico posto dove sta accanto al comando che
// la applica.
// ============================================================================
//
// La chiave è `{_id: "hashed"}`. Non è la chiave giusta in assoluto — non esiste — è
// quella giusta per QUESTO dataset e per quello che la demo deve mostrare.
//
// PERCHÉ UNA CHIAVE HASHED DISTRIBUISCE. MongoDB non partiziona sul valore della
// chiave, partiziona sull'hash del valore. Gli `_id` di questo dataset sono gli
// interi 0, 1, 2, … 19 999: valori contigui, che crescono di uno alla volta. I loro
// hash no — sono sparsi su tutto l'intervallo a 64 bit, e due documenti consecutivi
// finiscono con altissima probabilità in chunk diversi, quindi su shard diversi. Il
// manuale lo dice partendo dal problema: «Hashed keys are ideal for shard keys with
// fields that change monotonically like ObjectId values or timestamps»
// ([S-066](../../../docs/Sources.md#s-066)).
//
// PERCHÉ UNA CHIAVE MONOTONA NO, ED È IL PUNTO DELLA DEMO. Con `{_id: 1}` — la stessa
// chiave, senza hash — la partizione sarebbe per intervalli, e in ogni cluster esiste
// un chunk il cui estremo superiore è `MaxKey`, cioè «più grande di qualunque valore».
// Un `_id` che cresce sempre è sempre più grande di tutti quelli già scritti: **ogni**
// inserimento cade in quel chunk, che sta su **uno** shard. Il manuale: «If the shard
// key value is always increasing, all new inserts are routed to the chunk with
// `maxKey` as the upper bound. The shard containing that chunk becomes the bottleneck
// for write operations» ([S-067](../../../docs/Sources.md#s-067)). Il risultato è un
// cluster con due shard che scrive come se ne avesse uno, più il costo del
// bilanciamento — perché il balancer poi i chunk li sposta, e li sposta mentre il
// carico che li ha squilibrati continua.
//
// UNA PRECISAZIONE CHE IL MANUALE FA E CHE VA RIPORTATA, perché senza il difetto
// diventa una caricatura: MongoDB il chunk caldo non lo lascia fermo dov'è. «To
// optimize data distribution, the chunks that contain the global `maxKey` (or
// `minKey`) do not stay on the same shard. When a chunk is split, the new chunk with
// the `maxKey` (or `minKey`) chunk is located on a different shard» (S-067). Il collo
// di bottiglia quindi **cambia nodo** invece di restare sempre lo stesso. Quello che
// non fa è sparire: in ogni istante gli inserimenti stanno andando tutti in un posto
// solo, e il cluster paga in più le migrazioni che servono a spostare il posto.
//
// La cosa da dire dal palco è che l'errore non si vede: il cluster funziona, le
// scritture riescono, `sh.status()` mostra due shard. Quello che non si vede è che uno
// dei due non sta facendo niente.
//
// QUELLO CHE LA CHIAVE HASHED COSTA, detto qui e non nascosto. Si perde la località:
// documenti con `_id` vicini stanno apposta lontani, quindi una query per intervallo —
// `{_id: {$gte: 100, $lt: 200}}` — il router non può indirizzarla a nessuno in
// particolare e la manda a tutti gli shard. «Post-hash, documents with "close" shard
// key values are unlikely to be on the same chunk or shard - the mongos is more likely
// to perform Broadcast Operations to fulfill a given ranged query. mongos can target
// queries with equality matches to a single shard» (S-066). Resta mirata solo
// l'uguaglianza: `{_id: 42}` va a uno shard solo.
//
// È il baratto che sta dentro ogni shard key, e in una frase sola: si sceglie fra
// distribuire le scritture e tenere vicine le letture contigue. Non si ottengono tutte
// e due.
//
// E l'hash non è una garanzia, il manuale lo dice espressamente: «a shard key that does
// not change monotonically does not, on its own, guarantee even distribution of data
// across the sharded cluster. The cardinality and frequency of the shard key also
// contribute to the distribution of the data» (S-067). Qui distribuisce perché gli
// `_id` sono ventimila valori distinti, uno per documento — cardinalità massima e
// frequenza uniforme. Su un campo con dieci valori l'hash non salverebbe niente.
//
// PERCHÉ `_id` E NON UN CAMPO DELLA DEMO. Perché è l'unico campo garantito presente e
// unico in ogni documento, e perché così il dataset resta identico a quello degli altri
// due stack. In un'applicazione vera la chiave si sceglie sul modo in cui si interroga
// la collezione, non sulla comodità: `citta` sarebbe leggibile, e sarebbe la scelta
// peggiore fra quelle disponibili qui. Ha cardinalità dieci, e «the cardinality of a
// shard key determines the maximum number of chunks the balancer can create» (S-067):
// dieci valori distinti, al massimo dieci chunk per l'intero cluster. Il manuale fa lo
// stesso conto su un campo `continent` da sette valori — «this constrains the number of
// effective shards in the cluster to `7` as well - adding more than seven shards would
// not provide any benefit» — e con dieci al posto di sette la conclusione è la stessa.
//
// ============================================================================
// L'ORDINE: PRIMA SI DISTRIBUISCE, POI SI RIEMPIE. Non è indifferente.
// ============================================================================
//
// Distribuire una collezione VUOTA con una chiave hashed fa una cosa che distribuire
// una collezione piena non fa: MongoDB crea i chunk in anticipo e li spalma sugli
// shard prima che esista un documento. «The sharding operation creates empty chunks to
// cover the entire range of the shard key values and performs an initial chunk
// distribution. By default, the operation creates 2 chunks per shard and migrates
// across the cluster» (S-066).
//
// Due chunk per shard, due shard: **quattro chunk**, ed è il numero che lo spike aveva
// misurato senza sapere che fosse un valore predefinito documentato. Se un giorno ne
// comparissero di più è un'informazione da leggere, non un guasto da nascondere: o gli
// shard sono diventati tre, o qualcuno ha passato `numInitialChunks`, o un chunk si è
// diviso crescendo.
//
// Sull'altro ordine il manuale è altrettanto esplicito: su una collezione già piena
// «the sharding operation creates an initial chunk to cover all of the shard key
// values», uno solo, e tocca al balancer spostare i pezzi dopo. Funziona, ma l'avvio
// del lab diventerebbe una gara col balancer, e la distribuzione al primo
// `sh.status()` sarebbe 100 % / 0 %.

// Fra 1 e 125 (ADR-0036), e distinti da quelli degli altri script della catena.
const USCITA_NON_E_UN_ROUTER = 2;
const USCITA_SHARDING_FALLITO = 8;

const DOCUMENTI = 20000;
const LOTTO = 5000;
const COLLEZIONE = "lab.ordini";
const CHIAVE = { _id: "hashed" };

// `make seed-03` la vale 1: la regola predefinita — non ricaricare se i dati ci sono —
// è quella giusta all'avvio e quella sbagliata quando si vuole tornare allo stato
// iniziale dopo aver fatto scempio della collezione durante una prova.
const RICARICA = process.env.RICARICA === "1";

// --- Si sta parlando a un router? ---------------------------------------------
//
// `sh.shardCollection()` dato a un `mongod` fallisce, e fallisce senza nominare il
// router. Questa riga costa niente e trasforma quel caso in una frase che dice dove
// andare a guardare. `isdbgrid` è la risposta che solo un `mongos` dà.
const saluto = db.hello();
if (saluto.msg !== "isdbgrid") {
  print("ERRORE: questo script va eseguito su mongos, non su un mongod.");
  print("Risposta di hello(): msg=" + (saluto.msg || "assente"));
  print("Nel file Compose il servizio «seed» condivide la rete di «mongos».");
  quit(USCITA_NON_E_UN_ROUTER);
}

// `lab`, non `db`: dichiarare `const db = db.getSiblingDB(...)` sembra naturale e non
// compila, perché la costante oscura il `db` globale già nella propria inizializzazione.
const lab = db.getSiblingDB("lab");
const configurazione = db.getSiblingDB("config");

// Senza `wtimeout` una scrittura con `w: "majority"` su un set che ha perso la
// maggioranza aspetta per sempre, e un seed che non finisce durante il talk è peggio di
// un seed che fallisce: quello almeno lo si legge.
const MAGGIORANZA = { w: "majority", wtimeout: 10000 };

// --- Il generatore, copiato alla lettera dagli altri due stack -----------------
//
// Seme, epoca, liste e ORDINE DELLE CHIAMATE sono identici a
// `docker/01-standalone/init/10-dati-demo.js` e al gemello dello stack 02. La
// conseguenza è precisa e vale la pena dirla: questi 20 000 documenti sono i **primi
// 20 000** di quei 50 000, uguali campo per campo. Non un dataset simile — lo stesso,
// troncato. Chi confronta la stessa interrogazione sui tre stack confronta gli stessi
// documenti.
//
// Perché xorshift e non un congruenziale lineare è spiegato per esteso nel file dello
// stack 01 e misurato in V-013: il prodotto sfonda i 2^53 interi esatti di JavaScript
// e i bit bassi hanno periodo cortissimo.
let seme = 20260918;
function prossimo(limite) {
  seme ^= seme << 13;
  seme ^= seme >>> 17;
  seme ^= seme << 5;
  seme = seme >>> 0; // da 32 bit con segno a 32 bit senza segno
  return seme % limite;
}

const CITTA = [
  "Ancona", "Bologna", "Cagliari", "Firenze", "Genova",
  "Milano", "Napoli", "Palermo", "Roma", "Torino",
];
const STATI = ["ricevuto", "in lavorazione", "spedito", "consegnato", "annullato"];

// Epoca fissa: 1 gennaio 2026, 00:00:00 UTC. Mai `Date.now()`.
const EPOCA = new Date("2026-01-01T00:00:00Z").getTime();
const GIORNO = 24 * 60 * 60 * 1000;

// --- Come si guarda una distribuzione -------------------------------------------
//
// `getShardDistribution()` è il comando da conoscere e da mostrare dal vivo, ma STAMPA
// e non restituisce niente: da uno script non è interrogabile, esattamente come
// `sh.status()`. `$shardedDataDistribution` invece torna documenti, ed è la stessa
// distinzione fra presentazione e verità che `20-add-shard.js` fa scegliendo
// `config.shards` al posto di `sh.status()`.
function distribuzione() {
  const righe = db
    .getSiblingDB("admin")
    .aggregate([{ $shardedDataDistribution: {} }, { $match: { ns: COLLEZIONE } }])
    .toArray();
  if (!righe.length) {
    return [];
  }
  return righe[0].shards
    .map((s) => ({ shard: s.shardName, documenti: s.numOwnedDocuments }))
    .sort((a, b) => (a.shard < b.shard ? -1 : 1));
}

function racconta() {
  const meta = configurazione.collections.findOne({ _id: COLLEZIONE });
  if (!meta) {
    print("ATTENZIONE: " + COLLEZIONE + " non risulta distribuita.");
    return;
  }
  const chunk = configurazione.chunks.countDocuments({ uuid: meta.uuid });
  print("shard key: " + JSON.stringify(meta.key) + " · chunk: " + chunk);

  const parti = distribuzione();
  const totale = parti.reduce((somma, p) => somma + p.documenti, 0);
  for (const parte of parti) {
    const quota = totale ? ((parte.documenti / totale) * 100).toFixed(1) : "0.0";
    print("  " + parte.shard + ": " + parte.documenti + " documenti (" + quota + " %)");
  }
  if (parti.length < 2) {
    print("ATTENZIONE: i documenti risultano su " + parti.length + " shard.");
    print("Un solo shard significa un cluster che funziona e non partiziona niente.");
  }
}

// --- Serve caricare? --------------------------------------------------------------

const presenti = lab.ordini.countDocuments();

if (presenti === DOCUMENTI && !RICARICA) {
  print("lab.ordini ha già " + presenti + " documenti: non ricarico.");
  print("Per ricaricare comunque: «make seed-03», che passa RICARICA=1.");
  racconta();
  quit(0);
}

if (presenti > 0) {
  print("lab.ordini ha " + presenti + " documenti: la svuoto e ricarico.");
}

// Il `drop` prende il write concern per la ragione dello stack 02 — una collezione
// cancellata sul solo primario è uno stato che un failover può riportare indietro — e
// qui ne ha una in più: cancellare una collezione DISTRIBUITA toglie anche la sua riga
// da `config.collections` e i suoi chunk. Dopo questo `drop` la collezione non è più
// distribuita, e il `shardCollection` qui sotto non è una ripetizione, è necessario.
lab.ordini.drop({ writeConcern: MAGGIORANZA });

// --- Distribuire, con la collezione ancora vuota -----------------------------------

// `enableSharding` su un database già abilitato risponde `ok: 1`, quindi il secondo
// avvio non ha bisogno di saperlo. Dalla 6.0 `shardCollection` lo farebbe anche da sé:
// resta scritto perché è il comando che si spiega, e uno script che si legge come una
// spiegazione vale il decimo di secondo che costa.
try {
  sh.enableSharding("lab");
} catch (errore) {
  print("ERRORE: sh.enableSharding(«lab») non è riuscita.");
  print("Messaggio: " + errore.message);
  quit(USCITA_SHARDING_FALLITO);
}

print("distribuisco " + COLLEZIONE + " con shard key " + JSON.stringify(CHIAVE));

let esito;
try {
  esito = sh.shardCollection(COLLEZIONE, CHIAVE);
} catch (errore) {
  // Stessa lezione di V-056 e V-057: dentro la stessa famiglia di comandi c'è chi
  // solleva e chi risponde `ok: 0`, e un ramo solo ne perderebbe metà.
  esito = { ok: 0, errmsg: errore.message };
}

if (!esito.ok) {
  print("ERRORE: sh.shardCollection() ha risposto ok=" + esito.ok);
  print("Messaggio: " + (esito.errmsg || "nessuno"));
  print("Le due cause frequenti: il database non è abilitato allo sharding,");
  print("oppure la collezione è già distribuita con una chiave diversa.");
  quit(USCITA_SHARDING_FALLITO);
}

// --- Riempire ----------------------------------------------------------------------

print('carico ' + DOCUMENTI + " ordini in " + COLLEZIONE + ' con w: "majority"...');
const inizio = Date.now();

for (let base = 0; base < DOCUMENTI; base += LOTTO) {
  const lotto = [];
  for (let scarto = 0; scarto < LOTTO && base + scarto < DOCUMENTI; scarto++) {
    const indice = base + scarto;
    lotto.push({
      _id: indice,
      cliente: `cliente-${String(prossimo(2000)).padStart(4, "0")}`,
      citta: CITTA[prossimo(CITTA.length)],
      stato: STATI[prossimo(STATI.length)],
      importo: prossimo(500000) / 100,
      righe: 1 + prossimo(5),
      data: new Date(EPOCA + prossimo(240) * GIORNO),
    });
  }
  // Il write concern si chiede al livello dell'operazione, non della connessione: così
  // questa riga dice da sola che cosa pretende. `ordered: false` come negli altri due
  // stack, e qui in più significa che `mongos` può mandare agli shard in parallelo i
  // pezzi del lotto che li riguardano, invece di rispettare un ordine che non serve.
  lab.ordini.insertMany(lotto, { ordered: false, writeConcern: MAGGIORANZA });
}

const durata = Date.now() - inizio;
print("caricati " + lab.ordini.countDocuments() + " ordini in " + durata + " ms.");

racconta();

// Un indice c'è, e non l'ha chiesto nessuno: `shardCollection` con una chiave hashed
// crea l'indice hashed che le serve. È la sola differenza rispetto agli altri due
// stack, dove `lab.ordini` ha il solo `_id_` perché la demo confronta una query prima e
// dopo `createIndex()`. Qui il «prima» resta identico: `_id_hashed` non serve a nessuna
// delle query della demo, che filtrano su `citta` e su `stato`.
print("indici: " + lab.ordini.getIndexes().map((i) => i.name).join(", "));
