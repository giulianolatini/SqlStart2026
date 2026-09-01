// Secondo anello della catena: forma il replica set e crea l'amministratore.
//
// Gira dentro il servizio one-shot `rs-init`, che condivide il namespace di rete
// del primo membro (`network_mode: "service:mongo-rs-1"`). È l'intera ragione per
// cui questo file può esistere: `localhost` qui dentro è il `localhost` del
// `mongod`, quindi la connessione gode dell'eccezione localhost e può eseguire
// `replSetInitiate` e `createUser` su un nodo che pretende autenticazione ma non
// ha ancora nessun utente da autenticare (ADR-0040, V-023).
//
// Si passa a mongosh con `--file` e percorso ASSOLUTO, mai per pipe: dentro un
// container la directory di lavoro non è quella da cui si è digitato il comando,
// `load()` non ha percorso di ricerca, e sullo standard input mongosh crede di
// avere una sessione interattiva e ci stampa sopra i prompt (ADR-0036, S-047).

const NOME_REPLICA = process.env.NOME_REPLICA || "rs0";
const UTENTE = process.env.UTENTE_AMMINISTRATORE;
const PASSWORD = process.env.PASSWORD_AMMINISTRATORE;

// I codici di uscita restano fra 1 e 125 (ADR-0036): `quit(300)` arriva al
// chiamante come 44 ed `exit(-1)` come 255, e Compose riporterebbe un guasto
// diverso da quello avvenuto.
const USCITA_CREDENZIALI = 2;
const USCITA_ATTESA_SCADUTA = 3;

if (!UTENTE || !PASSWORD) {
  print("ERRORE: UTENTE_AMMINISTRATORE o PASSWORD_AMMINISTRATORE non valorizzate.");
  print("Copiare docker/02-replicaset/.env.example in .env e riempire la password.");
  quit(USCITA_CREDENZIALI);
}

// --- Il set è già formato? --------------------------------------------------
//
// La domanda si fa a `hello()` e non a `rs.status()`, e non è un dettaglio:
// `rs.status()` richiede autenticazione appena esiste un utente, quindi al
// secondo avvio risponderebbe `Unauthorized` e bisognerebbe distinguere un
// errore di permessi da un set inesistente. `hello()` risponde senza credenziali
// in entrambi gli stati (misurato in V-023 e V-024): prima
// dell'inizializzazione porta `isreplicaset: true` e nessun `setName`, dopo
// porta il `setName`.

const primoSguardo = db.hello();

if (primoSguardo.setName) {
  print("replica set «" + primoSguardo.setName + "» già formato: non lo reinizializzo");
} else {
  print("inizializzo il replica set «" + NOME_REPLICA + "»");

  // I membri si elencano con il NOME DI SERVIZIO Compose e la porta INTERNA
  // 27017 — mai la porta pubblicata sull'host, mai un indirizzo (ADR-0021).
  // Il motivo è più sottile del solito: questi nomi finiscono dentro la
  // configurazione della replica, e sono i nomi che il driver riceverà quando
  // scoprirà la topologia. Un client fuori dalla rete Compose li riceve e non
  // li risolve: è la seconda trappola del talk, e nasce esattamente qui.
  //
  // `priority: 2` sul primo membro non è cosmetica: rende PREVEDIBILE chi sarà
  // primario all'avvio, che per una demo cronometrata vale più della simmetria.
  // Ha anche un effetto visibile nella scena di failover — quando il nodo
  // fermato torna, si riprende il ruolo — e va detto al pubblico invece di
  // lasciarlo sembrare magia.
  rs.initiate({
    _id: NOME_REPLICA,
    members: [
      { _id: 0, host: "mongo-rs-1:27017", priority: 2 },
      { _id: 1, host: "mongo-rs-2:27017", priority: 1 },
      { _id: 2, host: "mongo-rs-3:27017", priority: 1 },
    ],
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
// scarico. Il limite esiste perché un'attesa infinita in una catena Compose è
// un avvio che non finisce e non dice perché.

const TENTATIVI = 60;
const PAUSA_MS = 500;

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
      " secondi. Guardare i log dei tre membri: «docker compose logs mongo-rs-1»."
  );
  quit(USCITA_ATTESA_SCADUTA);
}

print("primario eletto: " + db.hello().primary);

// --- L'amministratore -------------------------------------------------------
//
// Sotto eccezione localhost, che si chiude con questa stessa chiamata: da qui in
// poi ogni comando su questo nodo vuole credenziali. È il motivo per cui la
// creazione dell'utente è l'ULTIMA cosa che questo script fa.
//
// Due esiti vanno trattati come successo, e non è indulgenza: al secondo
// `up` l'utente esiste già, e in quel caso il nodo risponde `Unauthorized`
// (l'eccezione è chiusa) oppure «User already exists». Entrambi significano che
// lo stato desiderato c'è. Un one-shot che fallisce al secondo avvio è un
// `make up-02` che fallisce davanti al pubblico.

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

print("catena completata");
