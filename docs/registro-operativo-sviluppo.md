# Registro operativo di sviluppo

Diario cronologico: cosa è stato fatto, cosa è fallito, cosa se ne è imparato. Una voce per
sessione, la più recente in fondo. Distinto da [`Decision.md`](Decision.md), che registra
le sole decisioni.

---

## 2026-08-24 — Brainstorming e design

**Fatto:** rilevazione dell'ambiente; esclusione di Apple `container` (V-001); design delle
tre architetture, dell'applicazione e dell'impianto documentale in
[`00-progetto/2026-08-24-design.md`](00-progetto/2026-08-24-design.md); diciassette ADR.

**Fallito:** il primo tentativo di usare Rancher Desktop come runtime — il binario `docker`
risolveva a Rancher mentre il contesto puntava al socket di Docker Desktop. Sostituito con
Docker Desktop; i residui in `~/.rd` restano un controllo del preflight.

**Imparato:** la VM Docker dispone di 7,65 GiB dei 16 dell'host. È il vincolo che ha
generato i due profili dello sharded cluster (ADR-0010).

---

## 2026-08-25 — Approvazione e fondamenta

**Fatto:** approvazione della specifica; ADR-0016 (filmati su YouTube con copia locale) e
ADR-0017 (il repository resta esaustivo, i tagli sono solo di scena); avvio di
`feature/00-fondamenta`. Poi, nell'ordine: igiene del repository (`.gitignore`,
`.editorconfig`, licenza GPL-3.0 confermata); verifica di ventisei fonti primarie e due
verifiche empiriche in [`Sources.md`](Sources.md), ciascuna con verdetto e riserve;
`tools/check_citations.py` scritto in TDD, nove test, che fallisce se un ADR cita una fonte
inesistente o se una fonte non è citata da nessuno; [`Decision.md`](Decision.md) con
ventiquattro ADR; questo registro e l'[indice della documentazione](README.md).

**Fallito:** leggere le pagine di `mongodb.com/docs` nella loro versione HTML. Il testo
tornava compresso, con parole funzionali cadute e passaggi elisi: sufficiente per farsi
un'idea, inservibile per una citazione letterale da mettere su una slide. Un paio di frasi
erano state trascritte così prima che il problema si notasse, e sono state rifatte.

**Imparato:**

1. Sia `mongodb.com/docs` sia `docs.docker.com` servono una variante Markdown della stessa
   pagina aggiungendo `.md` all'URL. È il testo esatto, senza impaginazione da togliere.
   Da qui in avanti le fonti si consultano così.
2. Verificare prima di scrivere cambia il progetto, non solo la bibliografia. Nove
   assunzioni di design non hanno retto al riscontro: una ha superato una decisione intera
   (ADR-0011 su testcontainers, sostituita da ADR-0020) e tre hanno fatto cadere la
   motivazione di ADR-0004, ADR-0009 e ADR-0013 lasciando in piedi la decisione. Le nove
   sono elencate in testa a `Sources.md`, perché un'assunzione non confermata resta
   un'assunzione anche quando funziona.
3. La documentazione ufficiale si contraddice, e va detto invece che scelto in silenzio:
   sul rilevamento dei limiti di memoria nei container, `core/wiredtiger` (S-001) e
   `reference/command/hostInfo` (S-026) affermano cose diverse, entrambe correnti, sulla
   stessa versione. Il Task 10 misurerà chi ha ragione qui.
4. L'ordine dei task ha reso il controllo automatico una specifica anziché un collaudo:
   i rimandi `Usata da:` erano già cablati in `Sources.md` prima che gli ADR esistessero,
   quindi scrivere `Decision.md` è stato riempire una forma già verificabile. È passato
   verde al primo tentativo, e non per fortuna.
