---
name: project-memory
description: Use at the START of any session on a project that keeps its working memory inside the repository, in Memory/stato-del-lavoro.md, and again before finishing. SqlStart2026 does NOT: its working memory lives outside the repository, in Claude Code's own session memory (~/.claude/projects/<progetto>/memory/), one fact per file with frontmatter and an index in MEMORY.md. This skill does not govern there.
---

# Memory — la memoria di progetto

> [!IMPORTANT]
> **In SqlStart2026: non governa.** La memoria di lavoro di questo progetto non sta nel repository. Sta nella memoria di sessione di Claude Code, in `~/.claude/projects/-Users-…-SqlStart2026/memory/`, un fatto per file con il suo frontmatter e un indice in `MEMORY.md`. La differenza non è solo di percorso: quella memoria **non è versionata e non è evidenza**, mentre `docs/registro-operativo-sviluppo.md` lo e'. La regola di smistamento in coda a questa skill resta valida e vale la lettura: ciò che si sovrascrive sta nella memoria, ciò che è append-only sta nel registro.
>
> Il corpo qui sotto è quello del repository d'origine, intatto. In caso di conflitto fra
> questa skill e una scheda accettata di [`docs/Decision.md`](../../../docs/Decision.md),
> **vince la scheda**. La provenienza e le divergenze misurate stanno in
> [`concetti-generali/README.md`](../../../docs/06-sviluppo/concetti-generali/README.md).

Standard del repository d'origine. È uno dei quattro registri del repo; il confine con gli altri è
in fondo.

## A che serve

Conservare, **insieme al codice e alla documentazione**, ciò che di solito resta solo nella testa
di chi ha lavorato: dove siamo, qual è il prossimo passo, quali trappole sono già state pagate e
che cosa può far *sembrare* rotto un lavoro che non lo è.

È la parte di valore che si perde per dimenticanza — quella che non è finita nella documentazione
non perché fosse irrilevante, ma perché non aveva una casella dove stare. Versionandola col
progetto, sopravvive al cambio di postazione, al cambio di sessione e al passaggio di mano.

## Che cosa NON è

**Non è la memoria dell'assistente e non si carica da sola.** La memoria di Claude Code è
indicizzata sul percorso della cartella di lavoro: un file dentro il repo non viene letto
automaticamente da un'altra postazione. È documentazione che **va aperta**, ed è il motivo per cui
esiste il protocollo qui sotto e la regola nel `CLAUDE.md` alla radice del repo.

## Dove vive

`<progetto>/Memory/stato-del-lavoro.md` — **un solo file, senza data nel nome.**

Niente data, e non è un dettaglio: la Memory vale perché è *attuale*, e una cartella di istantanee
datate produce l'unica domanda che non deve mai porsi, «quale di questi è ancora vero?». La
cronologia esiste già ed è migliore: `git log -p <progetto>/Memory/` dà data, autore, diff e
messaggio di commit per ogni revisione. Mettere una data nel nome del file è controllo di versione
fatto a mano sopra un controllo di versione vero.

Il documento porta una riga **`Aggiornato il <data>`** in testa: è lì che la data serve, perché è
visibile leggendo.

Se serve un'istantanea *congelata* a fini di evidenza, non è questo il posto: è il registro di
sviluppo (skill `registro-di-sviluppo`), che è append-only per costruzione.

## Struttura

````markdown
# <progetto> — Stato del lavoro

**Aggiornato il <data>.** <Una riga: che cos'è questo file e che non si carica da solo.>

## Dove siamo
<Tabella: fatto / non fatto / branch e stato del push.>

### Il prossimo passo
<Il comando o l'azione concreta, non l'intenzione.>

## Che cosa può far sembrare rotto un lavoro che non lo è
<Le due o tre cose che a un occhio esterno sembrano difetti e non lo sono, con il rimando
all'ADR che le spiega. E' la sezione che risparmia piu' tempo in assoluto.>

## Il punto più esposto
<Dove il progetto e' fragile, e perche'. Se qualcosa poggia su conoscenza operativa invece che
su una fonte, si dice qui.>

## Convenzioni e politiche che non si deducono dal repo
<Politiche di lavoro, vincoli, cose da non toccare.>

## Trappole già pagate, da non ripagare
<Errori concreti gia' commessi, con la lezione. Costano poco a scrivere e molto a riscoprire.>

## Dove sta il resto
<Tabella di rimandi a README, runbook, Decision.md, Sources.md.>
````

## Regole

1. **Si sovrascrive, non si accumula.** Il file è sempre uno e sempre attuale.
2. **Non duplica la documentazione.** Il *perché* sta nelle ADR, le fonti in `Sources.md`, la
   procedura nel runbook, la cronologia nel registro. Qui sta solo ciò che **non è scritto
   altrove**. Se una frase potrebbe stare in un altro documento, il suo posto è l'altro documento.
3. **Perimetro: solo questo progetto.** Non si copia mai la directory di memoria dell'assistente
   così com'è: è indicizzata per postazione e contiene note su lavori estranei al repo, talvolta di
   clienti e talvolta relative a segreti. Si estrae a mano ciò che riguarda il progetto, e basta.
   Un repo privato non è un repo che non verrà mai condiviso.
4. **Ogni affermazione dev'essere azionabile.** «Il collaudo è da fare» è inutile; «il collaudo
   T1–T5 è nel runbook §10, il test che conta è T3 perché valida il selettore SCM» è utile.
5. **Nessuna cronologia.** Il registro di sviluppo esiste apposta ed è append-only; la Memory
   guarda avanti, non indietro.

## Protocollo di sessione

**All'inizio**, lavorando su un progetto del repo:

```bash
cat <progetto>/Memory/stato-del-lavoro.md
```

**Prima di chiudere**, se il lavoro ha cambiato lo stato — qualcosa è stato completato, è emersa
una trappola, il prossimo passo è diverso — si aggiorna il file e si aggiorna la riga
`Aggiornato il`. Va fatto **nello stesso commit del lavoro** o in uno immediatamente successivo:
una Memory aggiornata la settimana dopo è una Memory che non descrive nulla.

Se il lavoro non ha cambiato lo stato, non si tocca: un aggiornamento vuoto sporca il `git log` e
fa perdere fiducia nella riga della data.

## Il confine con gli altri registri

| Domanda | Documento | Disciplina |
|---|---|---|
| Dove siamo adesso, cosa fare dopo | `Memory/stato-del-lavoro.md` | **si sovrascrive**, vale perché attuale |
| Che cosa è successo, e quando | `Docs/registro/<data>-registro-di-sviluppo.md` (`registro-di-sviluppo`) | **append-only**, vale perché immutabile |
| Perché abbiamo deciso così | `Docs/Decision.md` (`decision-md`) | normativo, le schede si superano |
| Su quali fonti poggia | `Docs/Sources.md` (`sources-md`) | append-only |

La prova del nove: se una frase resterà vera fra un anno, non è Memory.

## Commit

```
docs(<scope>): aggiorna la memoria di progetto
```

`<scope>` è il nome esatto della cartella di progetto. Il corpo dice che cosa è cambiato nello
stato, non ripete il contenuto. Trailer `Co-Authored-By` come nel resto del repo.

## Il costo in token

Il file di memoria e' breve per costruzione, e si legge per intero: non e' li' che si spende. Si legge
pero' **da git**, e il comando si prefissa: `rtk git show feature/<progetto>:<progetto>/Memory/stato-del-lavoro.md`.

Se cercare qualcosa richiede di aprire i registri lunghi — `Docs/Decision.md`, i registri di sviluppo —
la domanda va prima a `tokensave_context`.

Le regole per esteso — che cosa copre l'indice, che cosa no, e come si scavalca il hook quando
il server non risponde — stanno in «Il costo in token» di `CLAUDE.md`.
