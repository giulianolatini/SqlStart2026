// Quinto e ultimo anello: registra i due shard nel cluster.
//
// È il comando che fa la differenza fra tre replica set e uno sharded cluster.
// Prima di `sh.addShard()` esistono `cfgrs`, `shard1rs` e `shard2rs`, tutti e tre
// funzionanti, e nessuno dei tre sa che gli altri esistono. Dopo, il config
// server sa che i due shard sono posti dove mettere documenti, e `mongos` sa a
// chi chiedere. Nient'altro cambia sui nodi: gli stessi processi, gli stessi
// dati, una riga in più nella collezione `config.shards`.
//
// Gira dentro il servizio one-shot `add-shard`, che condivide il namespace di
// rete di `mongos`. A differenza dei tre init del Task 2 questo è AUTENTICATO:
// quelli lavoravano sotto eccezione localhost su nodi che non avevano ancora
// nessun utente, qui l'amministratore esiste — l'ha creato `10-cfg-initiate.js` —
// e l'eccezione localhost si è chiusa nel momento stesso in cui è stato creato.
// Le credenziali arrivano sulla riga di comando di mongosh, dal file Compose.
//
// PERCHÉ SI PARLA A `mongos` E NON A UN CONFIG SERVER. `sh.addShard()` è un
// comando da router. Dato a un `mongod` — anche a quello che tiene i metadati —
// fallisce, perché è `mongos` a possedere la vista del cluster. È una delle
// trappole che la pagina del Task 9 deve raccogliere, insieme al suo gemello: uno
// shard avviato senza `--shardsvr` viene rifiutato qui, e il messaggio nomina
// esattamente l'opzione che manca — «Cannot run addShard on a node started without
// --shardsvr». Fino al Task 5 qui c'era scritto che «parla d'altro»: misurato in
// V-057, è falso, e la correzione vale anche come promemoria che un commento su un
// altro programma è un'affermazione a termine (nota di metodo 104).

const SHARD_1 = process.env.SHARD_1;
const SHARD_2 = process.env.SHARD_2;

// Fra 1 e 125 (ADR-0036), e distinti da quelli degli altri script perché un
// guasto qui ha cause diverse.
const USCITA_PARAMETRI = 2;
const USCITA_ADD_FALLITA = 6;
const USCITA_CLUSTER_INCOMPLETO = 7;

if (!SHARD_1 || !SHARD_2) {
  print("ERRORE: SHARD_1 o SHARD_2 non valorizzate.");
  print("Le passa il file Compose: se mancano, è stato modificato quel file.");
  quit(USCITA_PARAMETRI);
}

const DA_REGISTRARE = [SHARD_1, SHARD_2];

// --- Chi c'è già? -------------------------------------------------------------
//
// La domanda si fa alla collezione `config.shards`, che è la verità del cluster,
// e non a `sh.status()`, che è una funzione di presentazione: stampa e non
// restituisce niente di interrogabile.
//
// Serve perché al secondo `up` gli shard sono già dentro. `sh.addShard()` con uno
// shard già registrato non è distruttivo, ma risponde in modi che dipendono da
// che cosa è cambiato nella stringa, e un one-shot che fallisce al secondo avvio
// è un `make up-03` che fallisce davanti al pubblico.

function nomeSetDi(stringa) {
  return stringa.split("/")[0];
}

const configurazione = db.getSiblingDB("config");
const registrati = configurazione.shards
  .find({}, { _id: 1 })
  .toArray()
  .map((s) => s._id);

print("shard già registrati: " + (registrati.length ? registrati.join(", ") : "nessuno"));

// --- La registrazione -----------------------------------------------------------
//
// La stringa è `nome-set/host:porta,host:porta`, e i nomi sono NOMI DI SERVIZIO
// Compose con la porta interna 27017 (ADR-0021). Qui la regola morde più che
// altrove: questa stringa non resta nel file, finisce SCRITTA nel config server e
// da lì torna a ogni client che scopre la topologia. Un indirizzo IP messo qui
// diventa un indirizzo IP nella configurazione del cluster, e ce lo si ritrova
// dentro la prima volta che una macchina cambia rete.
//
// Basta nominare UN membro per shard: `mongos` si collega, chiede al replica set
// chi altro ne fa parte e registra la composizione reale. Elencarli tutti è
// comunque preferibile — se il membro nominato è giù, la registrazione non parte.

for (const stringa of DA_REGISTRARE) {
  const nome = nomeSetDi(stringa);

  if (registrati.includes(nome)) {
    print("shard «" + nome + "» già registrato: non lo riaggiungo");
    continue;
  }

  print("registro lo shard «" + nome + "» -> " + stringa);

  // Il try/catch non è prudenza generica: senza, il ramo qui sotto è CODICE
  // MORTO. `sh.addShard()` non risponde `ok: 0` quando fallisce, SOLLEVA — con
  // un nome di replica set irraggiungibile alza
  // `Could not find host matching read preference { mode: "primary" } for set X`.
  // mongosh allora esce 1 per eccezione non gestita, e tutto quello che c'è
  // scritto sotto — le due cause frequenti, il codice di uscita 6 che ADR-0036
  // gli assegna — non arriva mai a chi guarda. Misurato in V-056, rompendo la
  // stringa di uno shard apposta.
  let esito;
  try {
    esito = sh.addShard(stringa);
  } catch (errore) {
    esito = { ok: 0, errmsg: errore.message };
  }

  if (!esito.ok) {
    print("ERRORE: sh.addShard(«" + stringa + "») ha risposto ok=" + esito.ok);
    print("Messaggio: " + (esito.errmsg || "nessuno"));
    print("Le due cause frequenti: il mongod non è stato avviato con --shardsvr,");
    print("oppure il replica set nominato non ha un primario eletto.");
    quit(USCITA_ADD_FALLITA);
  }
}

// --- Il controllo finale --------------------------------------------------------
//
// Non è una formalità e non ripete il ciclo qui sopra: `sh.addShard()` può
// rispondere `ok: 1` per ciascuno e lasciare comunque un cluster con un solo
// shard, se una delle due stringhe nomina per errore il set già registrato. Il
// controllo guarda il risultato invece degli esiti, che è la differenza fra
// verificare e fidarsi.
//
// Due shard sono il minimo perché lo sharding abbia senso: con uno solo si
// ottiene un cluster che funziona e non partiziona niente (ADR-0010).

const finali = configurazione.shards.find({}, { _id: 1, host: 1 }).toArray();

if (finali.length < 2) {
  print("ERRORE: il cluster ha " + finali.length + " shard, ne servono almeno due.");
  print("Con uno shard solo il cluster funziona e non partiziona niente.");
  quit(USCITA_CLUSTER_INCOMPLETO);
}

for (const shard of finali) {
  print("shard nel cluster: " + shard._id + " -> " + shard.host);
}

print("cluster pronto: " + finali.length + " shard registrati");
