// Dataset di demo dello stack 02, identico documento per documento a quello
// dello stack 01 — e scritto in un modo che lo stack 01 non poteva permettersi.
//
// Il generatore, il seme, l'epoca e le liste sono copiati alla lettera da
// `docker/01-standalone/init/10-dati-demo.js`, e la copia è deliberata: i due
// stack devono produrre lo STESSO dataset, perché una parte della demo confronta
// la stessa interrogazione sui due, e un dataset diverso renderebbe il confronto
// una recita. La copia si paga con un vincolo — se cambia uno, cambia l'altro —
// che `tools/smoke-standalone.sh` e `tools/smoke-replicaset.sh` fanno rispettare
// confrontando la stessa impronta di tre numeri.
//
// LA DIFFERENZA CHE CONTA: qui si scrive con `w: "majority"`, e non è un
// dettaglio di configurazione, è la prima cosa tangibile che un replica set
// concede e un'istanza singola no. Su uno standalone `w: 1` è tutto ciò che si
// può chiedere: significa «il processo che ha ricevuto la scrittura l'ha presa»,
// e se quel processo muore un istante dopo la scrittura non è mai esistita per
// nessuno. `w: "majority"` significa «la maggioranza dei membri che possono
// votare l'ha presa», cioè: qualunque primario venga eletto dopo un guasto
// avrà questa scrittura, perché due insiemi che sono entrambi maggioranza si
// intersecano sempre. È la differenza fra «l'ho salvato» e «l'ho salvato e
// resterà salvato» (ADR-0022).
//
// DOVE GIRA. Due strade, e la seconda è quella da conoscere:
//
//   1. automaticamente, come ultimo passo di `rs-init`, subito dopo che
//      l'amministratore è stato creato — quindi con una connessione
//      AUTENTICATA, perché l'eccezione localhost si è chiusa proprio con quel
//      `createUser`;
//   2. a mano su uno stack già in piedi, con `make seed-02`.
//
// Nello stack 01 il seed lo esegue l'entrypoint dell'immagine, che lo fa **solo
// se /data/db è vuota** e quando non lo fa non lo dice (V-014). Qui la stessa
// regola c'è, ma è scritta sotto, si legge, e si può forzare: la condizione è un
// `if` in questo file invece di una convenzione dentro un'immagine.

const DOCUMENTI = 50000;
const LOTTO = 5000;

// `make seed-02` la vale 1. Serve perché la regola predefinita — non ricaricare
// se i dati ci sono già — è quella giusta all'avvio e quella sbagliata quando si
// vuole tornare allo stato iniziale dopo aver fatto scempio della collezione
// durante una prova.
const RICARICA = process.env.RICARICA === "1";

// Generatore xorshift a 32 bit con seme fisso. Serve varietà, non casualità:
// numeri riproducibili su qualunque macchina e a qualunque riavvio. Il perché
// non sia un congruenziale lineare è spiegato per esteso nel file dello stack 01
// e misurato in V-013: in breve, il prodotto sfonda i 2^53 interi esatti di
// JavaScript e i bit bassi hanno periodo cortissimo.
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

// Il write concern, dichiarato una volta e usato ovunque si scriva. Senza
// `wtimeout` una scrittura con `w: "majority"` su un set che ha perso la
// maggioranza aspetta per sempre, e un seed che non finisce durante il talk è
// peggio di un seed che fallisce: quello almeno lo si legge.
const MAGGIORANZA = { w: "majority", wtimeout: 10000 };

// `lab`, non `db`: dichiarare `const db = db.getSiblingDB(...)` sembra naturale
// e non compila, perché la costante oscura il `db` globale già nella propria
// inizializzazione.
const lab = db.getSiblingDB("lab");

// --- Serve caricare? ---------------------------------------------------------

const presenti = lab.ordini.countDocuments();

if (presenti === DOCUMENTI && !RICARICA) {
  print(`lab.ordini ha già ${presenti} documenti: non ricarico.`);
  print("Per ricaricare comunque: «make seed-02», che passa RICARICA=1.");
} else {
  if (presenti > 0) {
    print(`lab.ordini ha ${presenti} documenti: la svuoto e ricarico.`);
  }
  // Anche il `drop` prende il write concern. Una collezione cancellata sul solo
  // primario e non ancora sulla maggioranza è uno stato che un failover può
  // riportare indietro, e la ricarica che segue troverebbe documenti che
  // credeva di aver tolto.
  lab.ordini.drop({ writeConcern: MAGGIORANZA });

  print(`Carico ${DOCUMENTI} ordini in lab.ordini con w: "majority"...`);
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
    // Il write concern si chiede al livello dell'operazione, non della
    // connessione: così questa riga dice da sola che cosa pretende, e chi la
    // legge non deve risalire alla stringa di connessione per saperlo.
    lab.ordini.insertMany(lotto, { ordered: false, writeConcern: MAGGIORANZA });
  }

  const durata = Date.now() - inizio;
  print(`Caricati ${lab.ordini.countDocuments()} ordini in ${durata} ms.`);
}

// NESSUN indice, ed è voluto, esattamente come nello stack 01: la demo confronta
// una query senza indice con la stessa query dopo `createIndex()`, e crearlo qui
// toglierebbe il «prima».
print("Nessun indice creato: il confronto con e senza indice è parte della demo.");
