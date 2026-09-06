# Evidenza empirica per le decisioni sulle convenzioni

Numeri e fonti da usare durante il brainstorming per ancorare i pro/contro. Citare il dato, non recitare la lista.

## Dimensione di PR e review

- La densità di commenti di review *utili* cala al crescere del numero di file nel changeset; degrado marcato oltre ~20 file (Bosu, Greiler & Bird, MSR 2015, ~1,5M commenti su prodotti Microsoft — https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/bosu2015useful.pdf).
- Patch piccole: accettate più in fretta e con meno cicli di revisione (Baysal et al., EMSE — https://www.cs.ubc.ca/~rtholmes/papers/ese_2015_baysal.pdf). Efficacia della review inversamente proporzionale alla dimensione, crollo oltre 10 file (IET Software 2020).
- Sfumatura onesta: la correlazione tra dimensione e *tempo di merge* è debole (r_s=0,26 su 826k PR — Kudrjavets et al., MSR 2022). Le PR piccole migliorano la qualità della review, non automaticamente la velocità del flusso.
- Regola pratica Google: ~100 righe è una CL ragionevole, ~1.000 è troppo (https://google.github.io/eng-practices/review/developer/small-cls.html).
- Limiti operativi della singola review (SmartBear/Cisco 2006, 2.500 review): max 200–400 LOC per review, velocità sotto 300–500 LOC/h, sessioni sotto 60–90 min; oltre, la capacità di trovare difetti crolla (https://static0.smartbear.co/support/media/resources/cc/book/code-review-cisco-case-study.pdf).
- Due reviewer è l'ottimo misurato tra qualità e velocità (Rigby & Bird, *Convergent software peer review practices* — https://www.microsoft.com/research/publication/convergent-software-peer-review-practices/).
- La review trova meno difetti di quanto ci si aspetti (~14% dei commenti): i benefici dominanti sono knowledge transfer e comprensione condivisa (Bacchelli & Bird, ICSE 2013). Tutto ciò che aiuta la comprensione (PR piccole, descrizioni curate) moltiplica il valore della review.

## Batch size e delivery

- DORA lega da anni small batch e trunk-based development alle performance di delivery (report 2018/2022 — https://dora.dev/). Il report 2024 misura il rovescio: l'AI tende ad aumentare la dimensione dei changeset, con throughput −1,5% e stabilità −7,2% — argomento per batch piccoli proprio quando si lavora con agenti.

## Commit

- I "tangled commits" (cambiamenti non correlati nello stesso commit) inquinano bisect e analisi: fino al 15% dei commit di bug-fix è tangled, ~16,6% dei file associati erroneamente ai bug (Herzig, Just & Zeller, MSR 2013/EMSE 2016 — https://dl.acm.org/doi/10.1007/s10664-015-9376-6).
- ~44% dei messaggi di commit reali manca del "cosa" o del "perché" (Tian et al., ICSE 2022 — https://arxiv.org/abs/2202.02974); la qualità dei messaggi ha un effetto piccolo ma significativo sulla difettosità successiva (Li & Ahmed, ICSE 2023).
- GitLab sconsiglia esplicitamente lo squash di branch a vita lunga: rompe il tracciamento dell'antenato comune (https://docs.gitlab.com/user/project/merge_requests/squash_and_merge/).
- Lacuna dichiarata: nessuno studio peer-reviewed isola l'effetto dello squash su `git bisect`.

## Standard di riferimento

- Conventional Commits v1.0.0 — https://www.conventionalcommits.org/en/v1.0.0/
- Regola 50/72 e sette regole — T. Pope 2008 (https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html), C. Beams (https://cbea.ms/git-commit/)
- Conventional Comments — https://conventionalcomments.org/
- Branching semplice (feature branch + PR + main sano) — https://learn.microsoft.com/azure/devops/repos/git/git-branching-guidance
- Definition of Done — https://www.scrum.org/resources/definition-done
