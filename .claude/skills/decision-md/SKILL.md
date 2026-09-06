---
name: decision-md
description: Use when creating, extending or reviewing a project's Docs/Decision.md in the origin repository - the chronological Architecture Decision Record register that gives a project its decisional memory. Use also whenever a design decision is taken during work on a project, so it gets recorded at the moment it is made.
---

# Decision.md — registro delle decisioni di architettura (ADR)

Standard del repository d'origine. Fa coppia con la skill `sources-md`: le ADR citano le fonti, le
fonti dichiarano quali ADR sostengono, e i due file si verificano insieme.

## A che serve

Fra sei mesi il codice dirà *che cosa* fa, non *perché* non fa la cosa più ovvia. Il registro
esiste per quello: senza, le scelte non banali sembrano complicazioni gratuite e il primo che le
incontra le "semplifica", reintroducendo il problema che avevano risolto.

Una ADR va scritta quando la decisione **ha avuto un'alternativa credibile che è stata scartata**.
Non serve una ADR per ciò che si poteva fare in un modo solo.

## Dove vive

`<progetto>/Docs/Decision.md`, dove `<progetto>` è una cartella di primo livello del repo.
Accanto sta `<progetto>/Docs/Sources.md`. Il `README.md` del progetto resta alla **radice** della
cartella di progetto, non dentro `Docs/`: il repository d'origine è multiprogetto e GitHub usa
quel README come pagina di presentazione.

## Struttura del file

````markdown
# Registro delle decisioni di architettura (ADR)

<Due o tre paragrafi: che cosa raccoglie il registro, e soprattutto *perché serve a questo
progetto in particolare*. Se esiste un vincolo dominante da cui discendono molte scelte, dirlo
qui: è l'informazione che rende leggibile tutto il resto.>

Le fonti citate come `[SNN]` sono in [`Sources.md`](Sources.md).

## Come leggere le schede

| Stato | Significato |
|---|---|
| **accettata** | in vigore |
| **superata** | sostituita da una ADR successiva; resta a registro perché documenta una scelta che è stata realmente in vigore |

<Nota sulle date: quando sono state prese le decisioni.>

## Indice

| ADR | Decisione | Stato |
|---|---|---|
| [001](#adr-001) | <titolo in una riga> | accettata |
| [002](#adr-002) | <titolo in una riga> | **superata da [005](#adr-005)** |

---

<a id="adr-001"></a>
### ADR-001 — <titolo: la decisione, non il problema>

**Stato: accettata** (<data o ora>)

**Contesto.** <Qual era il problema e, soprattutto, **qual era la soluzione ovvia** che è stata
scartata. Se il lettore non capisce che cosa si sarebbe fatto istintivamente, non capirà perché
è stato fatto altro.>

**Decisione.** <Che cosa si è deciso, in forma affermativa. Se poggia su una fonte, citarla in
linea: ([S01](Sources.md#s01)).>

**Conseguenze.** <Che cosa si guadagna **e il prezzo pagato**. Una ADR senza costi dichiarati è
quasi sempre una ADR scritta male. Includere gli effetti a valle: che cosa dovrà fare chi
mantiene, che cosa può rompersi, che cosa resta scoperto.>

**Fonti.** [S01](Sources.md#s01), [S04](Sources.md#s04) ⚠.
````

## Regole

1. **Ordine cronologico**, non tematico né per importanza. Il registro racconta come si è arrivati
   qui; raggrupparlo per argomento cancella proprio l'informazione che lo rende utile.
2. **Numerazione mai riusata, mai rinumerata.** ADR-007 resta ADR-007 per sempre, anche se
   superata. Gli identificatori vengono citati nei commit e nelle altre ADR.
3. **Non si cancella una ADR: si marca superata.** `**Stato: superata da [ADR-013](#adr-013)**`,
   e la ADR che supera dichiara `supera [ADR-010](#adr-010)`. Nella scheda superata va aggiunto un
   paragrafo **Perché è stata superata**. Una decisione che è stata davvero in vigore spiega
   comportamenti del codice che altrimenti sembrano incoerenti — spessissimo il codice conserva la
   vecchia strada dietro un'opzione, ed è lì che il lettore va a sbattere.
4. **Ancora prima di ogni scheda:** `<a id="adr-001"></a>`, con numero a tre cifre.
5. **Ogni ADR dichiara `**Fonti.**`**, anche solo per dire che non ne ha: le formule usate sono
   `nessuna: decisione del committente`, `nessuna: scelta di metodo`, `nessuna: comportamento del
   prodotto, verificabile sul campo`. Il blocco vuoto non è ammesso: costringe a chiedersi se
   quell'affermazione fosse verificata o solo plausibile.
6. **L'indice si aggiorna sempre**, con lo stato accanto a ogni voce.
7. Se una decisione poggia solo su fonti marcate ⚠ in `Sources.md`, dirlo nelle **Conseguenze** e
   collegarlo al punto del collaudo che la verificherà.

## Come si compila

- **Durante il lavoro, non alla fine.** Una ADR ricostruita a posteriori perde il contesto: si
  ricorda che cosa si è scelto, non che cosa si stava per scegliere. Annota data/ora e alternativa
  scartata nel momento in cui la decisione si prende.
- **Anche le decisioni del committente sono ADR.** Anzi soprattutto: sono quelle che nessuno può
  dedurre dal codice. Registrare chi ha deciso e quando.
- **Anche i bug corretti in fase di revisione diventano ADR**, se la correzione stabilisce una
  regola (per esempio: quale parametro usare per registrare uno scheduled task). Il contesto
  racconta come è emerso il difetto: è la parte che impedisce la ricaduta.
- **Titolo = decisione.** "Tre selettori complementari invece di uno", non "Come filtrare gli
  eventi".
- Scrivi le **Conseguenze** come se dovessi convincere te stesso fra sei mesi che valeva la pena.
  Se non riesci a nominare un costo, probabilmente non hai capito la decisione.

## Verifica prima del commit

```bash
python3 .claude/skills/decision-md/scripts/check-crosslinks.py <progetto>/Docs
```

Controlla i link nei due sensi, le ancore interne, le fonti orfane, che ogni ADR dichiari le
proprie fonti e che la numerazione sia contigua. Esce con codice 1 se trova qualcosa, quindi è
usabile anche in un hook o in CI.

## Il confine con gli altri registri

| Domanda | Documento | Disciplina |
|---|---|---|
| Perché abbiamo deciso così | `Docs/Decision.md` (`decision-md`) | normativo, le schede si superano ma non si cancellano |
| Su quali fonti poggia | `Docs/Sources.md` (`sources-md`) | append-only, numerazione mai riusata |
| Che cosa è successo, e quando | `Docs/registro/<data>-registro-di-sviluppo.md` (`registro-di-sviluppo`) | **append-only**, vale perché immutabile |
| Dove siamo adesso, cosa fare dopo | `Memory/stato-del-lavoro.md` (`project-memory`) | **si sovrascrive**, vale perché attuale |

Regola di smistamento: una decisione normativa va in `Decision.md`, **mai** dentro il registro —
il registro è append-only e non può contenere schede che verranno superate. Nel registro resta il
fatto che quel giorno la decisione è stata presa, con il link alla scheda.

## Commit

```
docs(<scope>): registra le decisioni di architettura e le fonti documentali
```

`<scope>` è il **nome esatto della cartella di progetto** (`create-VM`, `Event-Viewer-Filters`).
Il corpo del commit riassume quante ADR, quali sono superate e perché, e riporta l'esito della
verifica dei link. Trailer `Co-Authored-By` come nel resto del repo.

## Il costo in token

`Docs/Decision.md` supera i 50 KB e cresce a ogni scheda: aprirlo intero per rispondere a «che cosa
dice ADR-009» costa piu' della risposta. Si parte da `tokensave_context` con la domanda in italiano.
Una scheda **appena scritta** fa eccezione e si legge dal disco: l'indice non si aggiorna da solo.

I comandi si prefissano con `rtk` — `rtk grep` per cercare un'ancora, `rtk git show` per rileggere una
versione precedente del registro.

Le regole per esteso — che cosa copre l'indice, che cosa no, e come si scavalca il hook quando
il server non risponde — stanno in «Il costo in token» di `CLAUDE.md`.
