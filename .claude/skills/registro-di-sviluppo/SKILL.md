---
name: registro-di-sviluppo
description: Use when opening, updating or closing the append-only development diary of SqlStart2026. Here it is a SINGLE file, docs/registro-operativo-sviluppo.md, not one file per date under Docs/registro/: entries are H2 headings '## AAAA-MM-GG — titolo' appended at the end, each closing with numbered 'Note di metodo' that continue across the whole register. Use also whenever a defect is found or a decision is taken during implementation, so it is recorded while still exact.
---

# Registro di sviluppo — il diario append-only del progetto

> [!IMPORTANT]
> **In SqlStart2026: governa, ma il file è uno solo.** Non `Docs/registro/<data>-registro-di-sviluppo.md`, uno per data, bensì un unico [`docs/registro-operativo-sviluppo.md`](../../../docs/registro-operativo-sviluppo.md) in cui le voci si aggiungono in coda come titoli di secondo livello `## AAAA-MM-GG — titolo`. Ogni voce si chiude con le **note di metodo**, numerate di seguito su tutto il registro — sono arrivate alla 251, e la numerazione non riparte. Il resto della disciplina vale parola per parola, compresa la parte che qui è costata di più: i difetti si registrano anche quando sono stati corretti subito, e una riga sbagliata si corregge **dicendo che è stata corretta**.
>
> Il corpo qui sotto è quello del repository d'origine, intatto. In caso di conflitto fra
> questa skill e una scheda accettata di [`docs/Decision.md`](../../../docs/Decision.md),
> **vince la scheda**. La provenienza e le divergenze misurate stanno in
> [`concetti-generali/README.md`](../../../docs/06-sviluppo/concetti-generali/README.md).

Standard del repository d'origine. È uno dei quattro registri del repo; il confine con gli altri è
in fondo.

## A che serve

Tenere traccia della **parte operativa** dello sviluppo: che cosa si è fatto, in che ordine, che
cosa si è rotto e come è stato aggiustato. Insieme alle ADR costituisce la cronologia del progetto
in ottica **ISO 27001** — la capacità di ricostruire a posteriori decisioni e interventi.

Il registro vale **perché è immutabile**. È questa la sua unica proprietà importante, e da essa
discendono tutte le regole che seguono: un registro corretto a posteriori smette di essere evidenza
e diventa un racconto.

Corollario spesso frainteso: **i difetti si registrano anche quando sono stati corretti subito**.
Un diario che contiene solo successi non è tracciabilità, è marketing — e priva chi verrà dopo
dell'informazione più utile, cioè dove il progetto è fragile.

## Dove vive

`<progetto>/Docs/registro/<AAAA-MM-GG>-registro-di-sviluppo.md`

La data nel nome è quella di **apertura** del registro, non dell'ultimo aggiornamento: il file
resta lo stesso per tutta la vita del progetto e si accoda. Una data nuova significa una fase
nuova, non un aggiornamento.

## Struttura

Il modello è quello collaudato su `create-VM`:

````markdown
# <progetto> — Registro di sviluppo

<Che cosa copre, da quando, e che cosa non copre.>

## 1. Cronologia
<Voci datate, in ordine. Che cosa è stato fatto, non che cosa si è deciso.>

## 2. Obiettivi raggiunti
<In forma verificabile: numeri, test, esiti.>

## 3. Decisioni prese durante l'implementazione
### 3.1 Diventate ADR
<Elenco con rimando: la decisione sta in Decision.md, qui resta la traccia di quando e perché
e' emersa durante il lavoro.>
### 3.2 Rimaste scelte d'implementazione
<Decisioni che non meritavano una ADR, con la ragione per cui non la meritavano. E' la sezione
che impedisce alle ADR di gonfiarsi.>

## 4. Difetti e svantaggi emersi durante lo sviluppo
<Uno per sottosezione, con: come si e' manifestato, causa, cosa si e' fatto, cosa resta esposto.
Compresi quelli corretti nel giro di dieci minuti.>

## 5. Ciò che resta non verificato
<Con il criterio che lo chiuderebbe. E' la sezione piu' consultata dopo un passaggio di mano.>

## 6. Sviluppi futuri

## 7. Revisione di conformità fra codice e documentazione
<Quando si controlla che i documenti dicano ancora la verità: cosa si è trovato disallineato.>
````

Non tutte le sezioni servono a tutti i progetti; l'ordine sì, perché rende i registri confrontabili
fra progetti diversi.

## Regole

1. **Si accoda, non si riscrive.** Se un'affermazione precedente diventa falsa, si aggiunge una
   voce nuova e datata che dice *che cosa è cambiato e quando*, lasciando intatta la vecchia.
2. **Ogni voce è datata.** Senza data non è cronologia.
3. **Nessuna ADR dentro il registro.** Le decisioni normative stanno in `Docs/Decision.md`
   (skill `decision-md`), perché hanno un ciclo di vita — possono essere superate — e un documento
   append-only non può contenere elementi mutevoli. Nel registro resta il *fatto* che la decisione
   è stata presa quel giorno, con il link alla scheda.
4. **Ogni decisione dell'implementazione va in §3.1 o in §3.2**, mai fuori: o è diventata una ADR,
   o si dichiara perché non lo è diventata.
5. **Niente stato corrente.** "Dove siamo adesso" e "che cosa fare dopo" appartengono a
   `Memory/stato-del-lavoro.md` (skill `project-memory`). Se finiscono qui invecchiano in silenzio
   dentro un documento che nessuno si aspetta di dover aggiornare — è esattamente ciò che è
   successo al §8 del registro di `create-VM`.

## Come si compila

- **Nel momento in cui la cosa accade.** Un difetto ricostruito a distanza perde la parte utile,
  cioè *come si è manifestato*.
- Scrivi i difetti dal sintomo alla causa, non viceversa: chi li rileggerà partirà dal sintomo.
- Le voci di §5 devono dire **che cosa le chiuderebbe**, non solo che sono aperte.

## Il confine con gli altri registri

| Domanda | Documento | Disciplina |
|---|---|---|
| Che cosa è successo, e quando | `Docs/registro/<data>-registro-di-sviluppo.md` | **append-only**, vale perché immutabile |
| Perché abbiamo deciso così | `Docs/Decision.md` (`decision-md`) | normativo, le schede si superano ma non si cancellano |
| Su quali fonti poggia | `Docs/Sources.md` (`sources-md`) | append-only, numerazione mai riusata |
| Dove siamo adesso, cosa fare dopo | `Memory/stato-del-lavoro.md` (`project-memory`) | **si sovrascrive**, vale perché attuale |

## Commit

```
docs(<scope>): registra <cosa> nel registro di sviluppo
```

`<scope>` è il nome esatto della cartella di progetto. Trailer `Co-Authored-By` come nel resto del
repo.

## Il costo in token

I registri giornalieri si accumulano, e la domanda tipica — «quando e' successo, e in che ordine» —
si risponde con `tokensave_context` sull'intera cartella invece che aprendo i file uno per uno. Il
registro del giorno in corso, che stai scrivendo, si legge dal disco.

I comandi si prefissano con `rtk`: `rtk ls Docs/registro/`, `rtk grep` per ritrovare un fatto.

Le regole per esteso — che cosa copre l'indice, che cosa no, e come si scavalca il hook quando
il server non risponde — stanno in «Il costo in token» di `CLAUDE.md`.
