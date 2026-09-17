// Dataset di demo, deliberatamente DETERMINISTICO.
//
// Stesso contenuto a ogni avvio, `_id` compresi: nessun `new Date()` senza
// argomento, nessun `Math.random()`. Il motivo non è pedanteria. Se il dataset
// cambia a ogni avvio non si può più confrontare la demo dal vivo con la
// registrazione di riserva — ed è esattamente il confronto che si fa quando la
// demo va storta davanti al pubblico.
//
// Lo stesso file servirà agli stack 02 e 03 e all'applicazione: nasce qui in una
// forma che gli altri branch possano riusare senza copiarla.
//
// ATTENZIONE: l'entrypoint dell'immagine ufficiale esegue gli script di
// /docker-entrypoint-initdb.d SOLO se /data/db è vuota. Su un volume già
// popolato questo file non viene eseguito, e non lo dice nessuno.

const DOCUMENTI = 50000;
const LOTTO = 5000;

// Generatore xorshift a 32 bit con seme fisso. Serve varietà, non casualità:
// numeri riproducibili su qualunque macchina e a qualunque riavvio.
//
// Il congruenziale lineare che si scrive d'istinto — `seme * 1103515245 + 12345`
// modulo 2^31 — qui sarebbe sbagliato due volte, e la prima versione di questo
// file lo era. Primo: in JavaScript quel prodotto arriva a 2,4·10^18 e sfonda i
// 2^53 interi rappresentabili esatti, quindi il modulo si applica a un numero
// già arrotondato. Secondo, e più visibile: i bit bassi di un LCG hanno periodo
// cortissimo, e `seme % 10` per scegliere la città produceva cinque città con
// diecimila ordini e cinque con qualche decina. Misurato in V-013.
//
// Lo xorshift usa solo operatori bit a bit, che JavaScript definisce su interi
// a 32 bit con segno: nessun arrotondamento possibile, e i bit bassi valgono
// quanto gli altri.
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

// `lab`, non `db`: dichiarare `const db = db.getSiblingDB(...)` sembra naturale
// e non compila, perché la costante oscura il `db` globale già nella propria
// inizializzazione.
const lab = db.getSiblingDB("lab");
lab.ordini.drop();

print(`Carico ${DOCUMENTI} ordini in lab.ordini...`);
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
  lab.ordini.insertMany(lotto, { ordered: false });
}

// NESSUN indice, ed è voluto. La demo confronta una query senza indice con la
// stessa query dopo `createIndex()`: creare l'indice qui toglierebbe il «prima».
print(`Caricati ${lab.ordini.countDocuments()} ordini in ${Date.now() - inizio} ms.`);
print("Nessun indice creato: il confronto con e senza indice è parte della demo.");
