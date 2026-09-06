---
name: modello-dei-rami
description: Use when work in the origin repository touches the branching model — opening or closing a feature, archiving a project on main as a release, needing a fix on something already released, checking that the branches still respect the model, or when someone mentions "git flow", "develop", "release branch", "taglia la release", "apri una feature", "chiudi la release", "hotfix urgente", "bump di versione". Also use when comparing the origin repository's model with the original Git Flow, or when setting up a branching model in a different repository.
---

# Il modello dei rami del repository d'origine — e dove diverge da Git Flow

> [!IMPORTANT]
> **Questa skill non è Git Flow, e non si chiama così apposta.** Descrive il modello del repository d'origine,
> che da Git Flow deriva e su quattro punti se ne allontana. Le divergenze sono **decisioni
> registrate**, non approssimazioni: in caso di conflitto fra questa skill e una scheda accettata di
> `Docs/Decision.md`, vince la scheda — ed è il caso di dirlo a voce.
>
> **Git Flow originale sta accanto a questa skill, intatto**, in `.claude/skills/git-flow/`: è stato
> lasciato apposta perché la differenza si veda per confronto diretto invece di essere data per
> scontata ([ADR-026](../../../Docs/Decision.md#adr-026)). Quella skill dichiara in testa che qui non si
> applica; questa dichiara dove diverge. Le due si leggono insieme.

Le **operazioni** si fanno con la skill `worktree-di-step`, che ha lo script. Questa skill serve a
sapere *qual è il modello*, a riconoscere quando qualcosa lo sta violando, e a spiegare Git Flow
com'è davvero quando il repository di destinazione è un altro.

Lingua: rispondi nella lingua dell'utente. Prima di ogni operazione leggi lo stato reale del repo,
non assumerlo.

## I quattro punti in cui il modello d'origine diverge

| | Git Flow (Driessen) | modello d'origine | Dove sta scritto |
|---|---|---|---|
| **Vita di una feature** | giorni; un branch = una funzionalità | quanto il progetto: una feature **è** un progetto, uno a uno, e non viene mai estratta | ADR-002, ADR-010 |
| **Chiusura** | `merge --no-ff` in `develop`, poi il branch si cancella | **fast-forward**, e il ramo resta finché il progetto vive | ADR-010, ADR-015 |
| **`main`** | linea di produzione, con `merge --no-ff` e tag annotati `vX.Y.Z` | **archivio di istantanee**: una release archivia un progetto, con un commit per progetto | ADR-009 |
| **Release branch** | `release/x.y.z` per la stabilizzazione | non esiste. La validazione avviene sul ramo di feature, prima che arrivi su `develop` | ADR-009 |

I percorsi sono dalla radice del repository: `Docs/Decision.md`, con le ancore `#adr-002` e seguenti.

Il livello che Git Flow non ha affatto è quello sotto la feature: `step/<prj>/<nome>`, uno spazio di
lavoro isolato in un worktree, che rientra nella feature in fast-forward. È lì che si lavora, ed è la
ragione per cui il fast-forward è **garantito** invece che fortunato: un agent lavora su una feature
alla volta e apre uno step alla volta.

```
main            archivio delle release
  ↑ istantanea, un commit per progetto archiviato (ADR-009)
develop         integrazione: infrastruttura, skill, configurazione
  ↑ fast-forward
feature/<prj>   la vita del progetto
  ↑ fast-forward
step/<prj>/<n>  spazio isolato, uno alla volta
```

## Come si opera qui

| Operazione | Che cosa si usa | Nota |
|---|---|---|
| Aprire un lavoro | `.claude/skills/worktree-di-step/scripts/step.sh apri <prj> <nome>` | poi `EnterWorktree(path: …)`, **mai** con `name:` (ADR-011) |
| Chiudere un lavoro | `step.sh chiudi` | fa il fast-forward sulla feature e spinge. Se **rifiuta**, il rifiuto è informazione: la feature si è mossa. Non si inventa un merge |
| Raccontare che cosa è cambiato | `.claude/skills/changelog-di-chiusura/scripts/changelog.sh feature <prj> --scrivi` | dal ramo della feature, nell'ultimo commit dello step |
| Archiviare un progetto su `main` | la procedura di ADR-009, e `changelog.sh rilascio <prj> <n>` | è l'unico modo in cui si arriva a `main` |
| Far revisionare prima di fondere | skill `revisione-pr` | `interroga` senza `--invia` non manda niente |

**Un fix su un progetto già archiviato non è un hotfix**: un progetto chiuso su `main` non si
riapre, e la sua evoluzione nasce come **feature nuova** (ADR-009). Se qualcuno chiede un
`hotfix/…`, la risposta è questa, non un branch.

## Riconoscere che il modello è stato violato

Sono i sintomi che vanno segnalati subito, prima di procedere con altro:

- un ramo `feature/<qualcosa>` che **non** corrisponde a una cartella di progetto — rompe
  l'invariante uno-a-uno di ADR-002, e con essa la raccolta dei commit per il CHANGELOG (ADR-020);
- un commit di merge dove doveva esserci un fast-forward, o due step aperti sulla stessa feature;
- un ramo di step fuso e cancellato senza aver verificato l'ancestralità (`git merge-base
  --is-ancestor`) — `git branch -d` da solo qui mente, vedi ADR-015;
- lavoro committato direttamente su `develop` invece che su una feature.

## Il Git Flow originale, come riferimento

Serve quando il repository di destinazione **non** è questo. Due branch permanenti — `main` =
produzione, `develop` = integrazione — e tre di supporto con origini e destinazioni fisse:

- **feature**: da `develop`, rientra in `develop` (via PR, o `merge --no-ff`); vita breve; mai
  direttamente in `main`.
- **release**: `release/x.y.z` da `develop` quando il rilascio è deciso; solo stabilizzazione e bump.
  Finish = merge `--no-ff` in `main`, **tag annotato**, **back-merge in `develop`**, poi si cancella.
  Il back-merge non è opzionale ed è il passo che i team dimenticano.
- **hotfix**: da `main`, solo il fix minimo. Finish = merge in `main` + tag, back-merge in `develop`,
  **e anche in un release branch aperto se esiste** — è l'errore classico del modello.

Il testo completo, non adattato, è nella skill `git-flow` qui accanto, con le sequenze esatte in
`.claude/skills/git-flow/references/comandi.md`: git puro, variante PR con `gh`, equivalenti
`git flow` AVH. Non sono ricopiate qui apposta — un modello tenuto in due posti diverge, e la
differenza fra i due si vede meglio leggendo l'originale intatto.

Prima di proporre Git Flow a un repo nuovo: non imporlo a un progetto che fa continuous delivery su
versione singola. La politica di branching è una decisione da registrare — skill `adr-brainstorm`.

## Guardrail

- Mai commit diretti su `main`; mai force-push su rami condivisi; mai `git rebase` di un ramo già su
  `origin`. Per riallineare una feature si usa `git merge develop` **dentro** la feature.
- Prima di qualunque operazione di rilascio o distruttiva, riepiloga che cosa stai per fare e ottieni
  conferma. `step.sh abbandona … --mandato` è irreversibile e richiede il mandato del proprietario
  (ADR-013).
- Se noti un disallineamento dal modello, **segnalalo e fermati**: proponi la riconciliazione, non
  eseguirla di iniziativa.

## I percorsi si scrivono con il case esatto

Questo repository vive su macOS, dove il filesystem non distingue maiuscole e minuscole, ma può
essere clonato su Linux, dove le distingue. Un percorso scritto con il case sbagliato funziona sulla
prima macchina e crea **una seconda cartella** sulla seconda.

| Si scrive così | Non così |
|---|---|
| `Docs/` | `docs/` |
| `Docs/Decision.md`, `Docs/Sources.md` | `docs/adr/`, `DECISION.md` |
| `.claude/skills/` | `.Claude/Skills/` |
| `.github/` (minuscolo: lo impone GitHub) | `.GitHub/` |

Vale per i percorsi che scrivi nei file **e** per quelli che passi a `git add`: git registra la
stringa che gli hai dato, non quella che il filesystem ti mostra.

## Il costo in token

Le sequenze qui sopra sono gia' scritte con `rtk` davanti, e vanno usate cosi': e' copiando un blocco
non prefissato che la regola si perde. Vale anche dentro le catene con `&&`, dove ogni comando vuole
il suo `rtk`.

Le skill e gli script di `.claude/` **non** sono indicizzati da tokensave: su `step.sh` e
`changelog.sh` si legge con `rtk read`, non si interroga l'indice.

Le regole per esteso — che cosa copre l'indice, che cosa no, e come si scavalca il hook quando
il server non risponde — stanno in «Il costo in token» di `CLAUDE.md`.
