# Definition of Done

Un incremento di lavoro è **Done** solo quando soddisfa tutti i punti. La DoD è unica per tutto il lavoro del repository; protegge dalla "quasi-finitezza", la forma più subdola di debito tecnico.

1. Il codice compila e la build CI è verde.
2. I test automatici che coprono il comportamento nuovo/modificato sono inclusi e passano (ciclo Red-Green-Refactor dove applicabile).
3. Il codice è stato revisionato tramite PR secondo le convenzioni del repo; tutti i commenti sono risolti.
4. Lint/format/analisi statica passano senza nuove violazioni.
5. La documentazione toccata dal cambiamento è aggiornata (README, ADR, commenti sul "perché").
6. Le decisioni architetturalmente significative emerse sono registrate nel registro delle decisioni del repo: qui `Docs/Decision.md`, altrove tipicamente `docs/adr/`.
7. Nessun segreto, credenziale o dato sensibile nel diff.

<!-- Adattare allo stack: coverage minima, migrazioni DB, changelog, deploy su staging, ecc. -->
