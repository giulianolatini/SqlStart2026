# ADR-0001: Squash merge come strategia di merge, con Conventional Commits sul messaggio finale

> Nel contesto di repository sviluppati da una persona con il supporto di agenti AI (Claude Code), di fronte alla necessità di una storia di main leggibile senza imporre disciplina atomica su ogni commit intermedio, abbiamo deciso di adottare lo squash merge con messaggio finale in formato Conventional Commits, per ottenere una main lineare e machine-readable, accettando la perdita della granularità dei commit interni alla feature.

- **Stato:** Proposed
- **Data:** 2026-08-07
- **Decisori:** Giuliano (owner), Claude (advisor)
- **Confidence:** media — da rivalutare se il volume di codice generato dagli agenti renderà preziosa la granularità interna (in quel caso: stacked PR o rebase, vedi Conseguenze)

## Contesto

I repository del progetto sono sviluppati da un singolo sviluppatore in coppia con agenti AI. Le PR sono l'unità di review; i commit intermedi dei branch sono spesso lavoro in corso, non curati singolarmente. Decision driver, in ordine: (1) storia di main leggibile e rilasciabile in ogni punto; (2) minima frizione durante lo sviluppo (libertà di commit WIP); (3) messaggi machine-readable per changelog/SemVer futuri; (4) bisect praticabile almeno a granularità di PR. Vincolo: GitLab e GitHub sconsigliano lo squash su branch a vita lunga — le nostre PR devono restare piccole e brevi (target < 400 righe, branch < pochi giorni).

## Decisione

Adotteremo lo **squash merge** come unica strategia consentita sui branch protetti. Il messaggio del commit di squash segue **Conventional Commits v1.0.0** (`type(scope): description`, body con il *perché*, footer `BREAKING CHANGE:` quando serve) e viene curato al momento del merge, derivandolo dal titolo e dalla descrizione della PR.

Alternative considerate e scartate:
- **Merge commit** — scartato perché il suo valore (conservare la storia interna) richiede commit atomici e curati in ogni branch, disciplina che non vogliamo imporre al flusso di lavoro con gli agenti; senza quella disciplina produce solo un grafo rumoroso.
- **Rebase merge** — scartato per lo stesso motivo: conserva commit intermedi che nel nostro flusso sono WIP, riscrivendone gli SHA.
- **Status quo (nessuna policy)** — scartato: convenzioni non scritte non esistono, e la storia diventa incoerente.

## Conseguenze

Diventa più facile: leggere e annullare la storia di main (un commit = una PR revisionata); automatizzare changelog e versioning in futuro. Diventa più difficile: fare bisect *dentro* una feature (granularità limitata alla PR — accettato: la mitigazione è tenere le PR piccole); recuperare i passi intermedi (sopravvivono solo nella PR sulla piattaforma, non in Git). Impatti collegati: la policy del repo limiterà i merge type a squash; il template di PR deve produrre descrizioni da cui derivare un buon messaggio di squash; se in futuro adotteremo stacked PR per cambi grandi, questo ADR andrà superato, non modificato.
