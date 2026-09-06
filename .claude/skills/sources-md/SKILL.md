---
name: sources-md
description: Use when creating, extending or reviewing a project's Docs/Sources.md in the origin repository - the chronological register of documentation sources consulted, cross-linked to the ADRs in Decision.md. Use also right after consulting official documentation during design work, so the source is recorded while it is still fresh.
---

# Sources.md — registro delle fonti documentali

Standard del repository d'origine. Fa coppia con la skill `decision-md`: le fonti dichiarano quali
ADR sostengono, le ADR citano le fonti, e i due file si verificano insieme.

## A che serve

Due cose, entrambe pratiche:

1. **Rendere verificabile** ogni affermazione del progetto che non sia deducibile dal codice —
   tipicamente i limiti e i comportamenti dei prodotti su cui si poggia.
2. **Permettere di rifare la stessa verifica** quando il prodotto cambierà idea, perché lo farà.
   Sapere *quale pagina* stabiliva *quale cosa* trasforma una riverifica da mezza giornata a dieci
   minuti.

C'è un terzo effetto, meno ovvio ma più prezioso: costringersi a scrivere che cosa una fonte
stabilisce fa emergere le volte in cui **non lo stabilisce affatto**, e si stava per costruire su
un'impressione.

## Dove vive

`<progetto>/Docs/Sources.md`, accanto a `<progetto>/Docs/Decision.md`.

## Struttura del file

````markdown
# Fonti documentali

Le fonti consultate per le decisioni di architettura di `<progetto>`, in **ordine cronologico di
consultazione**, con l'indicazione di che cosa ciascuna stabilisce e di quale ADR sostiene.

<Un paragrafo su perché servono a questo progetto in particolare.>

## Come leggere le schede

| Simbolo | Significato |
|---|---|
| ✅ | **fonte ufficiale** — documentazione del prodotto, o dichiarazione di un suo manutentore |
| ⚠ | **fonte secondaria o parziale** — forum, blog, oppure documentazione che stabilisce qualcosa di adiacente ma non esattamente ciò che serve. Utile come indizio, non come garanzia: ciò che poggia solo su queste è marcato come da verificare al collaudo |

**Nota metodologica.** <Opzionale ma preziosa: le trappole incontrate cercando. Pagine che gli
strumenti troncano, documentazione che non esiste, percorsi di ricerca che non portano da nessuna
parte. Serve a non far ripetere la stessa perdita di tempo.>

---

## <data>, ore <HH:MM> — <che cosa si stava cercando>

Contesto: <perché si è aperta questa ricerca, in una riga>.

<a id="s01"></a>
### S01 ✅ <Titolo della pagina, come si chiama davvero>

<https://url-esatto-con-ancora-di-sezione>

<Che cosa **stabilisce**, non che cosa contiene. Le affermazioni decisive vanno citate alla
lettera fra virgolette basse, perché è su quelle che poggia una decisione.>

Sostiene: [ADR-002](Decision.md#adr-002), [ADR-004](Decision.md#adr-004).
````

## Regole

1. **Ordine cronologico di consultazione**, non di importanza. Le sezioni raggruppano per *momento*
   di ricerca, con una riga `Contesto:` che dice che cosa si stava cercando. Così il registro
   racconta anche il percorso, non solo l'esito.
2. **Numerazione S01, S02… mai riusata, mai rinumerata**, con ancora `<a id="s01"></a>`.
3. **✅ o ⚠ subito dopo il numero.** Il simbolo è una dichiarazione di quanto peso può reggere
   quella fonte, e va deciso con onestà: la tentazione è promuovere a ✅ ciò che serve.
4. **Scrivi che cosa la fonte stabilisce, non un riassunto della pagina.** «Stabilisce che le
   uniche funzioni ammesse sono X, Y, Z» è utile; «parla dei limiti dell'XPath» non lo è. Le frasi
   su cui si regge una decisione vanno **citate testualmente**.
5. **Ogni scheda finisce con `Sostiene:`** e i link alle ADR. Una fonte che non sostiene nulla è un
   sintomo: o non serviva, o manca una ADR.
6. **Le fonti parziali vanno dichiarate per quello che sono.** Se una pagina documenta qualcosa di
   adiacente ma non esattamente il punto, marcala ⚠ e **scrivi esplicitamente che cosa non copre**.
   Poi dillo anche nella ADR e collegalo al punto del collaudo che colmerà il buco.
7. **Se una cosa non è documentata, scrivilo.** È informazione di prima qualità: risparmia la
   ricerca a chi verrà dopo e rende evidente quale parte del progetto poggia su conoscenza
   operativa invece che su una fonte.

## Come si compila

- **Nel momento in cui consulti**, non a fine progetto. Registra l'URL **con l'ancora di sezione**
  se la pagina ne ha una: mandare qualcuno su una pagina di quattromila parole non è una citazione.
- Registra anche le ricerche **fallite**, nella nota metodologica. "Questa cosa su Learn non c'è"
  vale quanto una fonte trovata.
- Quando una fonte **corregge o completa** una precedente, dillo nella scheda nuova citando la
  vecchia: è il modo in cui il registro mostra dove il ragionamento aveva sbagliato.
- Se stai scrivendo la scheda e non riesci a dire che cosa la fonte stabilisce, **fermati**: quasi
  sempre significa che la decisione che dovrebbe sostenere non è ancora chiara.

## Verifica prima del commit

```bash
python3 .claude/skills/decision-md/scripts/check-crosslinks.py <progetto>/Docs
```

Lo script sta nella skill `decision-md` perché verifica **la coppia** dei due file: link nei due
sensi, ancore interne, fonti orfane, ADR senza blocco fonti, numerazione contigua.

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
docs(<scope>): registra le fonti documentali e collegale alle ADR
```

`<scope>` è il **nome esatto della cartella di progetto**. Il corpo riassume quante fonti, quali
sono marcate ⚠ e che cosa resta scoperto, e riporta l'esito della verifica dei link. Trailer
`Co-Authored-By` come nel resto del repo.

## Il costo in token

`Docs/Sources.md` e' oltre i 19 KB e ha la stessa forma di crescita del registro delle decisioni: per
sapere se una fonte c'e' gia', o quale scheda regge, si chiede a `tokensave_context` invece di
scorrere il file. Una fonte appena aggiunta si rilegge dal disco, perche' l'indice e' fermo alla
sessione precedente.

I comandi si prefissano con `rtk`, `rtk grep` compreso.

Le regole per esteso — che cosa copre l'indice, che cosa no, e come si scavalca il hook quando
il server non risponde — stanno in «Il costo in token» di `CLAUDE.md`.
