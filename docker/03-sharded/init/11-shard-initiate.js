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
// QUESTO SCRIPT NON CREA UTENTI, ed è una decisione. Gli utenti del cluster
// vivono sul config server e valgono attraverso `mongos` (§4 dello spike). Uno
// shard resta quindi senza utenti finché `sh.addShard()` non lo aggancia al
// cluster, e in quella finestra l'eccezione localhost è aperta sul suo
// `localhost` — che dentro Compose non è raggiungibile da nessun altro
// container. Il caso «utente locale a uno shard», che serve per ispezionarlo
// direttamente, è un debito intestato al Task 9 del piano.

const NOME_REPLICA = process.env.NOME_REPLICA_SHARD;
const MEMBRI = (process.env.MEMBRI_SHARD || "")
  .split(",")
  .map((h) => h.trim())
  .filter((h) => h.length > 0);
const CANDIDATI = (process.env.CANDIDATI_SHARD || "")
  .split(",")
  .map((h) => h.trim())
  .filter((h) => h.length > 0);

const USCITA_PARAMETRI = 2;
const USCITA_ATTESA_SCADUTA = 3;
const USCITA_MEMBRO_ASSENTE = 4;
const USCITA_MEMBRO_DI_TROPPO = 5;

// Nessun valore predefinito, a differenza di `10-cfg-initiate.js`: là il config
// server è uno solo e il profilo `palco` è il caso normale, qui un predefinito
// sbagliato inizializzerebbe lo shard con i membri dell'altro. Meglio fermarsi.
if (!NOME_REPLICA || MEMBRI.length === 0 || CANDIDATI.length === 0) {
  print("ERRORE: NOME_REPLICA_SHARD, MEMBRI_SHARD o CANDIDATI_SHARD non valorizzate.");
  print("Le passa il file Compose: se mancano, è stato modificato quel file.");
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

print("shard «" + NOME_REPLICA + "» pronto, primario: " + db.hello().primary);
