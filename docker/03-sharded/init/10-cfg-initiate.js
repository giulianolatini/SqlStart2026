// Secondo anello della catena: forma il replica set dei config server e crea
// l'amministratore del cluster.
//
// Gira dentro il servizio one-shot `cfg-init`, che condivide il namespace di rete
// di `cfg1` (`network_mode: "service:cfg1"`). È l'intera ragione per cui questo
// file può esistere: `localhost` qui dentro è il `localhost` del `mongod`, quindi
// la connessione gode dell'eccezione localhost e può eseguire `replSetInitiate` e
// `createUser` su un nodo che pretende autenticazione ma non ha ancora nessun
// utente da autenticare (ADR-0026, ADR-0040).
//
// PERCHÉ NON `MONGO_INITDB_ROOT_USERNAME`. Su un config server non funziona, ed è
// misurato (§2 dello spike del 25 agosto). L'entrypoint ufficiale avvia un mongod
// temporaneo per creare l'utente, e quel mongod parte SENZA `--configsvr`:
// l'utente nasce in un contesto che poi non esiste più. Non riprovarci.
//
// Si passa a mongosh con `--file` e percorso ASSOLUTO, mai per pipe: dentro un
// container la directory di lavoro non è quella da cui si è digitato il comando,
// `load()` non ha percorso di ricerca, e sullo standard input mongosh crede di
// avere una sessione interattiva e ci stampa sopra i prompt (ADR-0036, S-047).

const NOME_REPLICA = process.env.NOME_REPLICA_CFG || "cfgrs";
const UTENTE = process.env.UTENTE_AMMINISTRATORE;
const PASSWORD = process.env.PASSWORD_AMMINISTRATORE;

// L'elenco dei membri da configurare, e l'elenco di TUTTI i membri possibili di
// questo componente. Il primo dipende dal profilo — un membro con `palco`, tre
// con `completo` — il secondo no. Servono tutti e due: vedi «la guardia».
const MEMBRI = (process.env.MEMBRI_CFG || "cfg1:27017")
  .split(",")
  .map((h) => h.trim())
  .filter((h) => h.length > 0);
const CANDIDATI = (process.env.CANDIDATI_CFG || "cfg1:27017,cfg2:27017,cfg3:27017")
  .split(",")
  .map((h) => h.trim())
  .filter((h) => h.length > 0);

// I codici di uscita restano fra 1 e 125 (ADR-0036): `quit(300)` arriva al
// chiamante come 44 ed `exit(-1)` come 255, e Compose riporterebbe un guasto
// diverso da quello avvenuto.
const USCITA_CREDENZIALI = 2;
const USCITA_ATTESA_SCADUTA = 3;
const USCITA_MEMBRO_ASSENTE = 4;
const USCITA_MEMBRO_DI_TROPPO = 5;

if (!UTENTE || !PASSWORD) {
  print("ERRORE: UTENTE_AMMINISTRATORE o PASSWORD_AMMINISTRATORE non valorizzate.");
  print("Copiare docker/03-sharded/.env.example in .env e riempire la password.");
  quit(USCITA_CREDENZIALI);
}

// --- Risponde? --------------------------------------------------------------
//
// `hello()` è l'unico comando che passa senza credenziali su un nodo con
// `--keyFile` e nessun utente: l'eccezione localhost NON apre il server, apre la
// creazione del primo utente, e `db.adminCommand({getCmdLineOpts: 1})` risponde
// «not authorized» anche da dentro (V-052). Qui per giunta si interroga un ALTRO
// container, dove nessuna eccezione localhost si applica: `hello()` è quindi la
// sola domanda che si possa fare, ed è abbastanza.

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
// Il numero di membri arriva da una variabile d'ambiente, il numero di container
// da `--profile`, e sono due sorgenti diverse per lo stesso fatto. Il Makefile le
// tiene allineate, ma chi lancia `docker compose` a mano no, e le due direzioni
// di disallineamento hanno guasti opposti:
//
//   MEMBRI=3 con --profile palco     -> si configura un set a tre membri con un
//                                       container solo: nessuna maggioranza,
//                                       nessun primario, avvio appeso.
//   MEMBRI=1 con --profile completo  -> si configura un set a un membro mentre
//                                       ne girano tre: due container inutili, e
//                                       la demo di failover non ha niente da
//                                       mostrare. Nessun errore da nessuna parte.
//
// Il secondo è il pericoloso, perché non fallisce. La guardia li rende entrambi
// rumorosi: ogni membro elencato DEVE rispondere (con attesa, perché in
// `completo` gli altri due possono essere ancora in avvio), e nessun candidato
// NON elencato deve rispondere.

const TENTATIVI = 60;
const PAUSA_MS = 500;

print("membri da configurare: " + MEMBRI.join(", "));

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
    print("Di solito significa che MEMBRI_CFG elenca più membri di quanti il");
    print("profilo attivo ne avvii. Con «--profile palco» il config server è uno solo.");
    quit(USCITA_MEMBRO_ASSENTE);
  }
}

// Il controllo inverso. Va fatto DOPO l'attesa qui sopra, così i container lenti
// hanno già avuto il loro tempo: un candidato che risponde adesso è un container
// che gira davvero, non uno che stava partendo.
for (const candidato of CANDIDATI) {
  if (!MEMBRI.includes(candidato) && risponde(candidato)) {
    print("ERRORE: «" + candidato + "» è in piedi ma non è fra i membri da configurare.");
    print("Di solito significa «--profile completo» con MEMBRI_CFG lasciato al valore");
    print("del profilo palco. Il set nascerebbe a un membro solo mentre ne girano tre.");
    quit(USCITA_MEMBRO_DI_TROPPO);
  }
}

// --- Il set è già formato? --------------------------------------------------
//
// La domanda si fa a `hello()` e non a `rs.status()`, e non è un dettaglio:
// `rs.status()` richiede autenticazione appena esiste un utente, quindi al
// secondo avvio risponderebbe `Unauthorized` e bisognerebbe distinguere un errore
// di permessi da un set inesistente. `hello()` risponde senza credenziali in
// entrambi gli stati: prima dell'inizializzazione porta `isreplicaset: true` e
// nessun `setName` (V-052), dopo porta il `setName`.

const primoSguardo = db.hello();

if (primoSguardo.setName) {
  print("replica set «" + primoSguardo.setName + "» già formato: non lo reinizializzo");
} else {
  print("inizializzo il replica set dei config server «" + NOME_REPLICA + "»");

  // `configsvr: true` è OBBLIGATORIO qui e vietato altrove: è la riga che
  // dichiara al set che il suo ruolo è tenere i metadati del cluster. Senza,
  // `mongos` rifiuta il `--configdb` con un errore che parla d'altro.
  //
  // I membri si elencano con il NOME DI SERVIZIO Compose e la porta INTERNA
  // 27017 — mai la porta pubblicata sull'host, mai un indirizzo (ADR-0021).
  // `rs.initiate()` senza argomenti userebbe l'hostname del container, che è
  // l'ID generato da Docker: il set si formerebbe, sembrerebbe funzionare, e poi
  // `mongos` non lo raggiungerebbe (§3 dello spike).
  //
  // `priority: 2` sul primo membro rende PREVEDIBILE chi sarà primario
  // all'avvio, che per una demo cronometrata vale più della simmetria.
  rs.initiate({
    _id: NOME_REPLICA,
    configsvr: true,
    members: MEMBRI.map((host, indice) => ({
      _id: indice,
      host: host,
      priority: indice === 0 ? 2 : 1,
    })),
  });
}

// --- Attendere il primario --------------------------------------------------
//
// Obbligatorio prima di creare il primo utente: «You must wait until the replica
// set elects a primary before you can add the first user» (S-055). Un
// `createUser` lanciato subito dopo `rs.initiate()` arriva su un nodo che non è
// ancora primario e fallisce con `NotWritablePrimary`.
//
// L'attesa è un ciclo di tentativi limitato, non un `sleep` fisso: un `sleep`
// tarato sulla macchina di chi sviluppa è lungo in sala e corto sul portatile
// scarico. Il limite esiste perché un'attesa infinita in una catena Compose è un
// avvio che non finisce e non dice perché.

let primario = false;
for (let tentativo = 1; tentativo <= TENTATIVI && !primario; tentativo += 1) {
  primario = db.hello().isWritablePrimary === true;
  if (!primario) {
    sleep(PAUSA_MS);
  }
}

if (!primario) {
  print(
    "ERRORE: nessun primario eletto dopo " +
      ((TENTATIVI * PAUSA_MS) / 1000) +
      " secondi. Guardare i log dei config server: «docker compose logs cfg1»."
  );
  quit(USCITA_ATTESA_SCADUTA);
}

print("primario del config server eletto: " + db.hello().primary);

// --- L'amministratore del cluster -------------------------------------------
//
// Sotto eccezione localhost, che si chiude con questa stessa chiamata: da qui in
// poi ogni comando su questo nodo vuole credenziali. È il motivo per cui la
// creazione dell'utente è l'ULTIMA cosa che questo script fa.
//
// L'utente nasce QUI e non su uno shard perché gli utenti creati sul config
// server sono gli utenti DEL CLUSTER: valgono attraverso `mongos`. Per collegarsi
// direttamente a uno shard servono credenziali locali a quello shard, e con
// queste la connessione diretta risponde `Authentication failed` (§4 dello
// spike). Non è un difetto da correggere: è il contenuto di una sezione della
// pagina sulla sicurezza, e il Task 9 del piano la deve scrivere eseguendo.
//
// Due esiti vanno trattati come successo, e non è indulgenza: al secondo `up`
// l'utente esiste già, e in quel caso il nodo risponde `Unauthorized` (l'eccezione
// è chiusa) oppure «User already exists». Entrambi significano che lo stato
// desiderato c'è. Un one-shot che fallisce al secondo avvio è un `make up-03` che
// fallisce davanti al pubblico.

try {
  db.getSiblingDB("admin").createUser({
    user: UTENTE,
    pwd: PASSWORD,
    roles: [{ role: "root", db: "admin" }],
  });
  print("utente amministratore «" + UTENTE + "» creato");
} catch (errore) {
  const gia = errore.codeName === "Unauthorized" || errore.codeName === "Location51003";
  const esiste = /already exists/i.test(errore.message || "");
  if (gia || esiste) {
    print("utente amministratore già presente: non lo ricreo");
  } else {
    throw errore;
  }
}

print("config server pronto");
