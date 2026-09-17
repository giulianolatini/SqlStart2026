# Anatomia del razionale (e come non scriverlo male)

Il razionale è la parte dell'ADR che invecchia meglio o peggio di tutte. Un record senza giustificazione perde valore nel tempo: quando il contesto cambia, nessuno può più valutare se la decisione sia ancora valida.

## Le quattro domande a cui il razionale risponde

1. **Quale problema stavamo risolvendo?** Il contesto, con i fatti rilevanti al momento della decisione (carico atteso, dimensione del team, vincoli di budget o normativi). I fatti di contesto sono ciò che permette, anni dopo, di capire se la decisione va riconsiderata.
2. **Quali requisiti e vincoli hanno pesato?** Funzionali e non funzionali, in ordine di importanza. Sono i "decision driver": la decisione si giustifica *rispetto a questi*, non in astratto.
3. **Quali alternative abbiamo scartato e perché?** Le alternative scartate sono la metà del valore del record: impediscono di ridiscutere da zero e mostrano che la scelta è stata una scelta.
4. **Quali trade-off accettiamo consapevolmente?** Ogni decisione significativa ha conseguenze negative. Nasconderle (intenzionalmente o per ottimismo) è il difetto che rende un ADR inutile.

## Confidence level

Registra il grado di confidenza (alto / medio / basso) e cosa lo determinerebbe diversamente ("bassa confidenza: non abbiamo dati di carico reali; rivalutare dopo il primo mese in produzione"). Una decisione a bassa confidenza registrata onestamente vale più di una a falsa alta confidenza.

## Errori tipici da evitare

- **Record-fatto-compiuto**: una sola opzione, nessuna alternativa. Documenta un evento, non una decisione.
- **Record-design-guide**: l'ADR degenera in documento di progettazione. La decisione deve stare in piedi da sola; il materiale di design va linkato come supplemento.
- **Razionale circolare**: "abbiamo scelto X perché è la scelta migliore". Il perché va ancorato ai driver.
- **Conseguenze solo positive**: segnale quasi certo di trade-off nascosti.
- **Prolissità**: il record deve essere conciso, assertivo, fattuale. Se supera le due pagine, sta assorbendo contenuto che appartiene altrove.

## Radici e riferimenti per approfondire

- M. Nygard, *Documenting Architecture Decisions* (2011) — https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions — il post che ha coniato il termine e il template a quattro sezioni.
- Microsoft Well-Architected, *Maintain an architecture decision record* — https://learn.microsoft.com/azure/well-architected/architect-role/architecture-decision-record — append-only, superseding, confidence level, cosa è "architecturally significant".
- AWS Prescriptive Guidance, *Architectural decision record process* — https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html — ciclo Proposed → Accepted/Rejected → Superseded, immutabilità dei record accettati.
- U. Zdun, R. Capilla, H. Tran, O. Zimmermann, *Sustainable Architectural Design Decisions*, IEEE Software 2013 — https://doi.org/10.1109/MS.2013.97 — origine degli Y-statement.
- MADR — https://adr.github.io/madr/ — template con decision driver e pro/contro strutturati.
- D. Parnas, P. Clements, *A Rational Design Process: How and Why to Fake It* (1986) — la radice teorica: il processo razionale si documenta anche quando il percorso reale è stato disordinato.

## Evidenza empirica utile in brainstorming

- L'adozione reale degli ADR è spesso superficiale: circa metà dei repository che li adottano ne contiene solo 1–5, e il 63% dei record nasce direttamente "accepted" saltando la fase deliberativa (Buchgeher et al., IEEE Access 2023; ICSA 2026). Antidoti: filtro di significatività severo, record brevi, processo leggero.
- In un esperimento controllato il template Nygard batte MADR in comprensibilità complessiva, mentre MADR cattura meglio il dettaglio strutturale (Nogueira et al., 2026, preprint). Da qui la regola: Nygard default, MADR quando il confronto tra opzioni lo merita.
