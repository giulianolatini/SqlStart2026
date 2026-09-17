// Terzo anello della catena: forma il replica set di UNO shard.
//
// Lo stesso file serve tutti e due gli shard: quello che cambia — il nome del
// set e l'elenco dei membri — arriva dall'ambiente, perché i due shard sono la
// stessa cosa con nomi diversi. È l'unico punto dello stack in cui la
// fattorizzazione non nasconde niente di didattico: ADR-0059 vieta gli ancoraggi
// nel Compose perché lì mascherano la differenza fra i ruoli, mentre qui i due
// shard NON hanno nessuna differenza da mostrare.
//
// Gira dentro i servizi one-shot `shard1-init` e `shard2-init`, che condividono
// il namespace di rete del primo membro del rispettivo shard. Vale tutto quello
// che dice `10-cfg-initiate.js` sull'eccezione localhost, su `--file` con
// percorso assoluto e sui codici di uscita: lì c'è il perché, qui solo il cosa.
//
// QUESTO SCRIPT CREA UN UTENTE, e fino al Task 10 non lo faceva. Gli utenti
// del cluster vivono sul config server e valgono attraverso `mongos`: uno shard
// non ne riceve copia, quindi restava senza utenti per tutta la vita del
// container — cioè con l'eccezione localhost aperta, e chiunque potesse avviare
// un processo nel suo namespace di rete ne diventava `root` senza presentare
// niente (V-064). L'utente creato qui in fondo chiude quella porta.
//
// È la procedura del manuale — «Create the shard-local user administrator»,
// passo 4 della creazione dei replica set di shard (S-075) — eseguita con tre
// semplificazioni che valgono SOLO in questo laboratorio. Sono elencate, con
// accanto la forma canonica, in `docs/03-amministrazione/sicurezza-keyfile-x509.md`
// §4.2. Il dettaglio sta là; qui basti che il pezzo in fondo a questo file NON
// va copiato in un cluster di produzione così com'è.

const NOME_REPLICA = process.env.NOME_REPLICA_SHARD;
const MEMBRI = (process.env.MEMBRI_SHARD || "")
  .split(",")
  .map((h) => h.trim())
  .filter((h) => h.length > 0);
const CANDIDATI = (process.env.CANDIDATI_SHARD || "")
  .split(",")
  .map((h) => h.trim())
  .filter((h) => h.length > 0);

// Le stesse due variabili di `10-cfg-initiate.js`, e lo stesso valore: una sola
// password per il cluster e per i suoi shard. È una semplificazione di
// laboratorio, non un modo di fare — vedi la testata.
const UTENTE = process.env.UTENTE_AMMINISTRATORE;
const PASSWORD = process.env.PASSWORD_AMMINISTRATORE;

const USCITA_PARAMETRI = 2;
const USCITA_ATTESA_SCADUTA = 3;
const USCITA_MEMBRO_ASSENTE = 4;
const USCITA_MEMBRO_DI_TROPPO = 5;
const USCITA_MEMBRI_DIVERSI = 6;

// Nessun valore predefinito, a differenza di `10-cfg-initiate.js`: là il config
// server è uno solo e il profilo `palco` è il caso normale, qui un predefinito
// sbagliato inizializzerebbe lo shard con i membri dell'altro. Meglio fermarsi.
if (!NOME_REPLICA || MEMBRI.length === 0 || CANDIDATI.length === 0) {
  print("ERRORE: NOME_REPLICA_SHARD, MEMBRI_SHARD o CANDIDATI_SHARD non valorizzate.");
  print("Le passa il file Compose: se mancano, è stato modificato quel file.");
  quit(USCITA_PARAMETRI);
}

// Stesso codice di uscita, perché è la stessa causa — il file Compose non ha
// passato quello che doveva — ma messaggio diverso, perché la riparazione è
// diversa: là si guarda il file Compose, qui si guarda `.env`.
if (!UTENTE || !PASSWORD) {
  print("ERRORE: UTENTE_AMMINISTRATORE o PASSWORD_AMMINISTRATORE non valorizzate.");
  print("Copiare docker/03-sharded/.env.example in .env e riempire la password.");
  quit(USCITA_PARAMETRI);
}

function risponde(host) {
  try {
    const connessione = new Mongo(host);
    connessione.getDB("admin").hello();
    return true;
  } catch (errore) {
    return false;
  }
}

// --- La guardia -------------------------------------------------------------
//
// Vedi `10-cfg-initiate.js` per il ragionamento. In sintesi: il numero di membri
// arriva dall'ambiente e il numero di container da `--profile`, e le due
// direzioni di disallineamento hanno guasti opposti — quella che configura più
// membri di quanti ne girano appende l'avvio, quella che ne configura meno non
// fallisce affatto ed è la pericolosa. Qui la seconda ha una conseguenza in più:
// uno shard a un membro solo non ha niente da mostrare nella scena di failover
// del Blocco 3, che è metà del motivo per cui questo stack esiste.

const TENTATIVI = 60;
const PAUSA_MS = 500;

print("shard «" + NOME_REPLICA + "», membri da configurare: " + MEMBRI.join(", "));

for (const membro of MEMBRI) {
  let vivo = false;
  for (let tentativo = 1; tentativo <= TENTATIVI && !vivo; tentativo += 1) {
    vivo = risponde(membro);
    if (!vivo) {
      sleep(PAUSA_MS);
    }
  }
  if (!vivo) {
    print("ERRORE: il membro «" + membro + "» non risponde dopo " +
      ((TENTATIVI * PAUSA_MS) / 1000) + " secondi.");
    print("Di solito significa che MEMBRI_SHARD elenca più membri di quanti il");
    print("profilo attivo ne avvii. Con «--profile palco» ogni shard ha un membro solo.");
    quit(USCITA_MEMBRO_ASSENTE);
  }
}

for (const candidato of CANDIDATI) {
  if (!MEMBRI.includes(candidato) && risponde(candidato)) {
    print("ERRORE: «" + candidato + "» è in piedi ma non è fra i membri da configurare.");
    print("Di solito significa «--profile completo» con MEMBRI_SHARD lasciato al valore");
    print("del profilo palco. Lo shard nascerebbe a un membro solo mentre ne girano tre,");
    print("e la scena di failover non avrebbe niente da mostrare.");
    quit(USCITA_MEMBRO_DI_TROPPO);
  }
}

// --- Il set è già formato? --------------------------------------------------

const primoSguardo = db.hello();

if (primoSguardo.setName) {
  // Formato sì — ma con QUALI membri? È la terza direzione del disallineamento
  // descritto sopra, e le due guardie non la vedono. Se lo stack è già stato
  // inizializzato in `palco` e adesso arriva MEMBRI_SHARD con tre nomi, tutti e
  // tre i container rispondono (la prima guardia è contenta) e nessun candidato è
  // di troppo (la seconda pure). Poi questo ramo salta l'inizializzazione e il set
  // resta com'era, mentre i container nuovi girano fuori dalla replica.
  //
  // Misurato: la catena stampa «pronto» ed esce **0** con un set a un membro solo
  // e due mongod sani che non ne fanno parte (V-072). È il guasto che ADR-0060
  // chiamava «il pericoloso, perché non fallisce», arrivato da una porta che
  // quella guardia non sorvegliava.
  //
  // I membri configurati li porta `hello()`, di nuovo senza credenziali. Si
  // sommano anche `passives` e `arbiters`: in questo lab non ce ne sono, ma un
  // membro con `priority: 0` finirebbe in `passives` e non in `hosts`, e un
  // confronto che lo perdesse accuserebbe una differenza inesistente.
  const configurati = (primoSguardo.hosts || [])
    .concat(primoSguardo.passives || [])
    .concat(primoSguardo.arbiters || [])
    .sort();
  const chiesti = MEMBRI.slice().sort();

  if (configurati.join(",") !== chiesti.join(",")) {
    print("ERRORE: il replica set «" + primoSguardo.setName + "» esiste già con altri membri.");
    print("  configurati adesso: " + configurati.join(", "));
    print("  chiesti da MEMBRI_SHARD: " + chiesti.join(", "));
    print("Di solito significa un cambio di profilo su uno stack già inizializzato.");
    print("Questo script NON riconfigura un set esistente: i dati sul disco sono");
    print("quelli di prima, e una riconfigurazione non è un'operazione da avvio.");
    print("Per cambiare profilo: «make reset-03», poi «make up-03 PROFILO=…».");
    quit(USCITA_MEMBRI_DIVERSI);
  }

  print("replica set «" + primoSguardo.setName + "» già formato: non lo reinizializzo");
} else {
  print("inizializzo lo shard «" + NOME_REPLICA + "»");

  // NIENTE `configsvr: true` qui: è la riga che distingue questo file dall'altro,
  // e metterla renderebbe lo shard un config server agli occhi del cluster.
  // Il ruolo `--shardsvr` sta invece sulla riga di comando del `mongod`, nel file
  // Compose: un mongod avviato senza `--shardsvr` viene rifiutato da
  // `sh.addShard()`.
  //
  // `priority: 2` sul primo membro non è cosmetica. Rende prevedibile chi è
  // primario, e ha un effetto visibile nella scena di failover: quando il nodo
  // fermato torna, si riprende il ruolo. Va detto al pubblico invece di lasciarlo
  // sembrare magia.
  rs.initiate({
    _id: NOME_REPLICA,
    members: MEMBRI.map((host, indice) => ({
      _id: indice,
      host: host,
      priority: indice === 0 ? 2 : 1,
    })),
  });
}

// --- Attendere il primario --------------------------------------------------
//
// Qui non c'è nessun `createUser` da proteggere, ma l'attesa serve lo stesso, e
// per un motivo che si vede solo più avanti: `sh.addShard()` nel Task 3 vuole uno
// shard con un primario eletto. Aspettare qui significa che il guasto, se c'è, si
// presenta con il nome dello shard invece che come un `addShard` che fallisce
// senza dire quale dei due.

let primario = false;
for (let tentativo = 1; tentativo <= TENTATIVI && !primario; tentativo += 1) {
  primario = db.hello().isWritablePrimary === true;
  if (!primario) {
    sleep(PAUSA_MS);
  }
}

if (!primario) {
  print(
    "ERRORE: nessun primario eletto per «" + NOME_REPLICA + "» dopo " +
      ((TENTATIVI * PAUSA_MS) / 1000) + " secondi."
  );
  quit(USCITA_ATTESA_SCADUTA);
}

print("primario dello shard «" + NOME_REPLICA + "» eletto: " + db.hello().primary);

// --- L'amministratore locale a questo shard ----------------------------------
//
// PRIMA DI COPIARE QUESTO PEZZO ALTROVE, leggere
// `docs/03-amministrazione/sicurezza-keyfile-x509.md` §4.2. Il manuale crea
// questo utente in due passi, con due utenti distinti e due password digitate a
// `passwordPrompt()`; qui è uno solo, con la password del cluster, letta da un
// file. In produzione NON si fa così.
//
// L'ECCEZIONE LOCALHOST NON È LA SCORCIATOIA. Anche il manuale crea questo
// utente sotto eccezione localhost, collegato al primario dello shard: è il solo
// modo di creare il PRIMO utente su un nodo che pretende autenticazione e non ha
// ancora nessuno da autenticare (S-075, ADR-0026, ADR-0040). Quello che questo
// script fa di suo è farlo senza nessuno davanti.
//
// PERCHÉ QUI E NON DOPO `sh.addShard()`. Il manuale mette questi passi prima di
// registrare gli shard: «Executing them now ensures that there are users
// available for each shard to perform shard-level maintenance» (S-075). Farlo
// dopo lascerebbe una finestra — fra `rs.initiate()` e la creazione dell'utente
// — in cui lo shard è in piedi e non ha utenti, che è la condizione che apre
// l'eccezione.
//
// PERCHÉ DOPO L'ATTESA DEL PRIMARIO. «You must be connected to the primary to
// create users» (S-075): un `createUser` su un nodo non ancora eletto fallisce
// con `NotWritablePrimary`. L'attesa qui sopra serviva già a `sh.addShard()`;
// adesso serve anche a questo.
//
// DUE ESITI VANNO TRATTATI COME SUCCESSO, per la ragione di
// `10-cfg-initiate.js`: al secondo `up` l'utente esiste già, e il nodo risponde
// `Unauthorized` (l'eccezione è chiusa dietro di lui) oppure «User already
// exists». Un one-shot che fallisce al secondo avvio è un `make up-03` che
// fallisce davanti al pubblico.

try {
  db.getSiblingDB("admin").createUser({
    user: UTENTE,
    pwd: PASSWORD,
    roles: [{ role: "root", db: "admin" }],
  });
  print("amministratore locale «" + UTENTE + "» creato su «" + NOME_REPLICA + "»");
} catch (errore) {
  const gia = errore.codeName === "Unauthorized" || errore.codeName === "Location51003";
  const esiste = /already exists/i.test(errore.message || "");
  if (gia || esiste) {
    print("amministratore locale già presente su «" + NOME_REPLICA + "»: non lo ricreo");
  } else {
    throw errore;
  }
}

print("shard «" + NOME_REPLICA + "» pronto, eccezione localhost chiusa");
