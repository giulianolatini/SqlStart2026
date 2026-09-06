---
name: revisione-pr
description: Use when a SqlStart2026 pull request — or a release branch that has no pull request yet — needs an outside review before merging, when asking Gemini Pro (via agy) or Codex (via codex) for an independent opinion on commits, security or documentation coherence, and when triaging what those external reviewers reported: deciding which findings are real, which are hallucinated, fixing the real ones and closing the rest with a written reason. Sending a dossier is an irreversible publication to third parties: `interroga` without --invia sends nothing, and the secret sieve is blocking.
---

# revisione-pr — due revisori esterni, e un triage che risponde di sé

> [!IMPORTANT]
> **In SqlStart2026: governa, ed è stata estesa.** Le regole valgono tutte, a partire da quella che governa il file: mandare un dossier a Gemini e a Codex è una pubblicazione verso terzi e non si torna indietro. Due cose sono diverse. La prima: qui una release si revisiona **prima** che la PR esista, perché la PR la apre e la fonde il Product Owner — quindi il dossier si costruisce da un intervallo di rami e non da un numero di PR: `revisione.sh dossier-rami <etichetta> <base>..<head> [percorso...]`, dove i percorsi servono perché una release intera non entra in un prompt solo e un revisore che riceve undici megabyte non revisiona, scorre. Da lì in avanti `segreti`, `interroga`, `rilievi` e `archivia` accettano l'etichetta al posto del numero. La seconda: il foglio archiviato va in `docs/revisioni/`, perché questo repository non ha cartelle di progetto di primo livello — e la cartella dei documenti lo script la **scopre** invece di presumerla, perché `Docs` e `docs` sono la stessa cosa su macOS e due cartelle diverse su Linux.
>
> Il corpo qui sotto è quello del repository d'origine, intatto. In caso di conflitto fra
> questa skill e una scheda accettata di [`docs/Decision.md`](../../../docs/Decision.md),
> **vince la scheda**. La provenienza e le divergenze misurate stanno in
> [`concetti-generali/README.md`](../../../docs/06-sviluppo/concetti-generali/README.md).

Standard del repository d'origine. Fa revisionare una PR da **Gemini Pro** (via `agy`) e da
**Codex** (via `codex`), poi mette le due risposte in un unico foglio dove ogni rilievo riceve un
verdetto scritto.

I due modelli **propongono**. Il verdetto è di chi conduce la sessione, e le decisioni di merito
restano del Product Owner. Un rilievo senza verdetto non è stato valutato, e lo script si rifiuta di
archiviarlo come se lo fosse.

## A che serve

Chi scrive il codice e chi lo revisiona qui sono spesso lo stesso agent, che quindi rilegge i propri
assunti con gli occhi che li hanno prodotti. Due revisori esterni, indipendenti fra loro e diversi
da chi ha scritto, sono il modo più economico di rompere quel circolo.

Due invece di uno perché il confronto è informazione: **quando entrambi alzano lo stesso rilievo, è
il segnale più forte disponibile**; quando uno solo lo alza, vale come opinione da verificare.

## La regola che governa tutto

> [!CAUTION]
> **Mandare una PR a Gemini e a Codex è una pubblicazione verso terzi, e non si torna indietro.**
> Il diff finisce sui sistemi di Google e di OpenAI, dove può essere conservato e registrato anche
> se poi la PR viene chiusa. Per questo `interroga` **senza `--invia` non manda niente**: mostra a
> chi si manderebbe cosa, quanto grande, e passa il dossier al setaccio dei segreti.

Il setaccio è bloccante e non ha una scorciatoia da riga di comando: se trova una credenziale,
l'invio non parte. La via d'uscita è togliere la credenziale dal ramo, non forzare lo strumento.

Cerca **valori**, non nomi. `INSTALL-ENV.md` nomina apposta tutte le credenziali del repository per
poterle revocare, e un controllo che si accendesse su quel documento verrebbe spento in una
settimana — e allora non proteggerebbe più niente.

## Il protocollo

Tutti i comandi sono `.claude/skills/revisione-pr/scripts/revisione.sh`.

| Fase | Comando | Che cosa succede |
|---|---|---|
| 1. Raccolta | `dossier <n>` | la PR diventa un file solo: metadati, commit interi, diff |
| 2. Lettura | apri `.revisioni/pr-<n>/dossier.md` | è tutto quello che uscirà: guardalo prima |
| 3. Prova a vuoto | `interroga <n>` | dice a chi, quanto, e se il setaccio è pulito. **Non invia** |
| 4. Invio | `interroga <n> --invia` | i due revisori partono insieme |
| 5. Unione | `rilievi <n>` | un foglio di triage con identificatori stabili |
| 6. **Triage** | *lo fai tu* | il cuore della skill — vedi sotto |
| 7. Archiviazione | `archivia <n> --scrivi` | verifica che nessun verdetto manchi, e mette il foglio nel repo |

La cartella di lavoro `.revisioni/` è ignorata da git: le risposte grezze e il dossier sono materiale
di lavorazione. Nel repository entra soltanto il foglio archiviato, che va aggiunto al commit con un
percorso esplicito.

## Fase 6 — Il triage

Il foglio `rilievi.md` ha una scheda per rilievo e, sotto ciascuna, un `### Verdetto` che dice
`_da compilare_`. Compilarli è il lavoro.

### Prima di tutto: verifica l'evidenza

Ogni rilievo porta un campo **Evidenza**, che il revisore ha copiato dal dossier. Cercala nel
dossier prima di qualunque altra considerazione:

```bash
rtk grep -n '<il frammento citato>' .revisioni/pr-<n>/dossier.md
```

**Se l'evidenza non c'è, il rilievo è inventato**, e questo lo stabilisce una ricerca, non
un'opinione. È il controllo più veloce e quello che scarta più errori: un modello che allucina un
problema allucina anche la riga da cui l'avrebbe visto.

Vale anche al contrario: un'evidenza che c'è **non rende vero il rilievo**. Dice solo che il
revisore ha guardato la cosa giusta, e che vale la pena valutarlo.

### I tre esiti

| Esito | Quando | Che cosa comporta |
|---|---|---|
| **accolto** | il problema è reale e vale la pena risolverlo adesso | applichi la modifica, poi scrivi il verdetto citando il commit |
| **respinto** | non è un problema: evidenza inesistente, ragionamento sbagliato, o vero in generale ma non qui | scrivi **perché** non lo è, in modo che regga a chi lo rilegge fra un anno |
| **rinviato** | il rilievo è giusto ma è fuori dal perimetro di questa PR | dici dove va a finire: una scheda in `Decision.md`, una voce nel piano, un lavoro futuro |

`rinviato` esiste perché senza di esso la scelta è fra risolvere fuori perimetro e respingere una
cosa vera. Entrambe sono peggio.

### Come si respinge bene

Un respinto è un documento, non una liberatoria. Deve dire **quale passaggio del ragionamento non
regge**, non che il rilievo è irrilevante. Le forme che ricorrono:

- *l'evidenza non esiste nel dossier* — la citazione non compare da nessuna parte; il rilievo nasce
  da un file che il revisore ha immaginato;
- *è vero in generale, non qui* — il difetto esiste come categoria, ma il codice in questione non ha
  quel percorso, quell'input o quel privilegio;
- *il controllo ISO citato non copre questo* — capita che il numero sia decorativo. Verificalo: un
  numero sbagliato lasciato passare mette in dubbio tutto il resto del foglio;
- *è già garantito altrove* — c'è un controllo a monte che il revisore non poteva vedere. Dì dove
  sta, altrimenti stai chiedendo fiducia.

> [!WARNING]
> **Non respingere un rilievo perché è scomodo da risolvere.** Se è vero ma costoso, è `rinviato` e
> si dice dove va. Se lo respingi, la spiegazione deve essere una che mostreresti al revisore.

### Che cosa riferire in chat

Il foglio archiviato non sostituisce la conversazione. Riferisci al Product Owner, in poche righe:

- quanti rilievi, quanti accolti, quanti respinti, quanti rinviati;
- **ogni rilievo di gravità alta che hai respinto**, con la ragione — è il punto in cui un errore di
  giudizio costa di più, e va visto da un essere umano;
- i rilievi su cui i due revisori si sono contraddetti.

## Che cosa NON è

**Non decide se la PR si fonde.** Decide il Product Owner. La skill produce l'istruttoria.

**Non sostituisce le prove.** Un rilievo accolto si risolve con una modifica che ha la sua verifica,
come qualunque altra modifica del repository.

**Non è un adempimento ISO 27001.** Il repository non è un sistema certificato: la lente ISO serve a
guardare la PR da un'angolazione utile — segreti, accessi, tracciabilità, gestione delle modifiche —
non a produrre evidenza di conformità.

## Le cose da non fare

| # | Cosa | Perché | Che cosa fare invece |
|---|---|---|---|
| 1 | `interroga --invia` senza aver letto il dossier | esce roba che non hai guardato, e non rientra | prova a vuoto, lettura, poi invio |
| 2 | Aggirare il setaccio dei segreti | esisterebbe per niente | togliere la credenziale dal ramo |
| 3 | Accogliere senza verificare l'evidenza | si finisce per «correggere» un problema inventato, e il codice peggiora | `grep` sul dossier, sempre |
| 4 | Respingere in blocco i rilievi di un revisore | è comodo e non è un giudizio | uno per uno, ciascuno con la sua ragione |
| 5 | Committare `.revisioni/` | è materiale di lavorazione, ed è ignorato apposta | `archivia --scrivi`, e percorso esplicito |
| 6 | Archiviare con verdetti aperti | direbbe che è stato valutato ciò che non lo è | lo script lo rifiuta: compila e rilancia |

## Quando le cose vanno male

**Un revisore non risponde, o risponde qualcosa che non è JSON.** Il foglio lo dichiara in un
riquadro d'avviso, e la risposta grezza resta in `.revisioni/pr-<n>/`. Non è la stessa cosa di «non
ha trovato niente»: se il riquadro c'è, la PR è stata guardata da un revisore solo, e va detto.

**Il dossier è enorme.** Sopra i 200 KB arriva un avviso, sopra i 700 KB l'invio si ferma: oltre
quella soglia il prompt non entra più negli argomenti di un processo e arriverebbe troncato senza
che nessuno lo dica. Una revisione su un diff enorme è comunque una revisione distratta: la risposta
giusta è chiudere la PR in due.

**Un falso positivo del setaccio.** Aggiungi la riga in `scripts/segreti.esclusioni`, **con il
commento che dice perché**. Ogni riga di quel file è un falso positivo già pagato: toglierla
significa riaverlo.

## Verifica

```bash
.claude/skills/revisione-pr/tests/test-revisione.sh
```

Cinquantatré controlli, con `gh`, `agy` e `codex` finti: la suite non ha rete, non spende token e
soprattutto non manda niente a nessuno. Le cinque cose che esiste per impedire sono inviare senza
che nessuno l'abbia chiesto, inviare un dossier con dentro una credenziale, accendere l'allarme su
un documento che le credenziali le nomina soltanto, scambiare «non ha risposto» per «non ha trovato
niente», e archiviare un triage a metà.

## Il confine con gli altri registri

| Domanda | Documento | Disciplina |
|---|---|---|
| Che cosa ha detto la revisione, e come è stata decisa | `<prj>/Docs/revisioni/<data>-pr-<n>.md` (questa skill) | append-only, uno per PR |
| Perché abbiamo deciso così, in generale | `Docs/Decision.md` (`decision-md`) | normativo |
| Che cosa è successo, e quando | `<prj>/Docs/registro/…` (`registro-di-sviluppo`) | append-only |
| Che cosa è cambiato nel prodotto | `CHANGELOG.md` (`changelog-di-chiusura`) | derivato |

## Commit

```
docs(<scope>): archivia la revisione esterna della PR #<n>
```

Se il triage ha prodotto modifiche, quelle vanno nei loro commit, con il loro perché; il foglio
archiviato le cita per sha.

## Il costo in token

Qui la spesa e' il diff e il dossier, non i registri. Si prefissa tutto: `rtk git diff`,
`rtk git log`, `rtk gh pr view`, `rtk grep` dentro il dossier. Sul diff di una PR il filtro di RTK
taglia circa l'80%.

`.revisioni/` non e' indicizzato da tokensave — e' materiale di lavoro, non tracciato — quindi li' si
legge, per intervallo di righe.

Le regole per esteso — che cosa copre l'indice, che cosa no, e come si scavalca il hook quando
il server non risponde — stanno in «Il costo in token» di `CLAUDE.md`.
