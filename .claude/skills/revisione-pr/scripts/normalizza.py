#!/usr/bin/env python3
"""Unisce le risposte dei revisori esterni in un unico foglio di triage.

Riceve la cartella di lavoro di una revisione e vi trova le risposte grezze
(gemini.txt, codex.txt). Ne estrae i rilievi, dà a ciascuno un identificatore
stabile e scrive rilievi.json (per le macchine) e rilievi.md (per chi decide).

Due scelte che spiegano il codice:

L'estrazione del JSON è difensiva a tre livelli. Ai due modelli è stato chiesto
un oggetto conforme allo schema, e i due CLI hanno un'opzione per imporglielo,
ma "ha un'opzione" non è "lo rispetta sempre": arrivano risposte avvolte in un
recinto markdown, o con una frase di cortesia davanti. Fallire lì
significherebbe buttare una revisione già pagata in tempo e in token.

Una risposta illeggibile NON viene silenziata. Diventa una voce di problema
nel foglio, perché "il revisore non ha risposto" e "il revisore non ha trovato
niente" sono due fatti opposti, e confonderli è il modo più veloce per credere
che una PR sia stata revisionata quando non lo è stata.
"""

import difflib
import json
import re
import sys
from pathlib import Path

FONTI = [
    ("gemini.txt", "G", "Gemini Pro (agy)"),
    ("codex.txt", "C", "Codex (codex)"),
]

CAMPI = [
    ("categoria", "Categoria"),
    ("gravita", "Gravità"),
    ("confidenza", "Confidenza"),
    ("dove", "Dove"),
    ("controllo_iso", "Controllo ISO"),
]


def estrai_json(testo):
    """Restituisce (oggetto, None) oppure (None, motivo)."""
    testo = testo.strip()
    if not testo:
        return None, "risposta vuota"

    try:
        return json.loads(testo), None
    except json.JSONDecodeError:
        pass

    recinto = re.search(r"```(?:json)?\s*(.+?)```", testo, re.S)
    if recinto:
        try:
            return json.loads(recinto.group(1)), None
        except json.JSONDecodeError:
            pass

    # Terzo tentativo: il primo oggetto bilanciato che comincia con una graffa.
    inizio = testo.find("{")
    while inizio != -1:
        livello = 0
        in_stringa = False
        fuga = False
        for i in range(inizio, len(testo)):
            c = testo[i]
            if in_stringa:
                if fuga:
                    fuga = False
                elif c == "\\":
                    fuga = True
                elif c == '"':
                    in_stringa = False
                continue
            if c == '"':
                in_stringa = True
            elif c == "{":
                livello += 1
            elif c == "}":
                livello -= 1
                if livello == 0:
                    try:
                        return json.loads(testo[inizio:i + 1]), None
                    except json.JSONDecodeError:
                        break
        inizio = testo.find("{", inizio + 1)

    return None, "nessun JSON leggibile nella risposta"


def sbusta(oggetto):
    """Toglie la busta del CLI, se c'è, e restituisce la risposta del modello.

    `agy --output-format json` non stampa la risposta: stampa una busta con
    dentro `status`, `usage`, la risposta come stringa in `response` e la stessa
    risposta già decodificata in `structured_output`. Il primo oggetto bilanciato
    della risposta grezza è quindi la busta, non i rilievi, e senza questo passo
    la revisione di Gemini risulterebbe «senza elenco rilievi» — cioè
    indistinguibile da un revisore che non ha trovato niente.
    """
    if not isinstance(oggetto, dict) or "rilievi" in oggetto:
        return oggetto

    dentro = oggetto.get("structured_output")
    if isinstance(dentro, dict):
        return dentro

    # `structured_output` manca quando il modello non ha rispettato lo schema:
    # resta `response`, che è la stessa cosa come stringa.
    testo = oggetto.get("response")
    if isinstance(testo, str) and testo.strip():
        riletto, _ = estrai_json(testo)
        if isinstance(riletto, dict):
            return riletto

    return oggetto


def leggi_fonte(cartella, nome_file, sigla, etichetta):
    percorso = cartella / nome_file
    if not percorso.exists():
        return [], f"{etichetta}: non interrogato (manca {nome_file})"

    oggetto, motivo = estrai_json(percorso.read_text(encoding="utf-8", errors="replace"))
    if oggetto is None:
        return [], f"{etichetta}: {motivo} — la risposta grezza è in {nome_file}"
    oggetto = sbusta(oggetto)

    grezzi = oggetto.get("rilievi")
    if not isinstance(grezzi, list):
        return [], f"{etichetta}: il JSON non contiene un elenco 'rilievi' — vedi {nome_file}"

    rilievi = []
    for n, r in enumerate(grezzi, 1):
        if not isinstance(r, dict):
            continue
        r = dict(r)
        r["id"] = f"{sigla}-{n}"
        r["fonte"] = etichetta
        rilievi.append(r)
    return rilievi, None


def accoppia(rilievi):
    """Segnala le coppie che parlano probabilmente della stessa cosa.

    Serve a chi decide: due revisori indipendenti che alzano lo stesso rilievo
    è il segnale più forte che ci sia, e va visto come una cosa sola invece che
    valutato due volte in punti diversi del foglio.
    """
    for a in rilievi:
        simili = []
        for b in rilievi:
            if a is b or a["fonte"] == b["fonte"]:
                continue
            punteggio = difflib.SequenceMatcher(
                None, a.get("titolo", "").lower(), b.get("titolo", "").lower()
            ).ratio()
            if punteggio >= 0.6:
                simili.append(b["id"])
        a["simile_a"] = simili


ORDINE_GRAVITA = {"alta": 0, "media": 1, "bassa": 2}


def scrivi_markdown(cartella, numero, rilievi, problemi):
    righe = []
    righe.append(f"# Revisione della PR #{numero} — foglio di triage")
    righe.append("")
    righe.append(
        "Prodotto da `.claude/skills/revisione-pr/scripts/revisione.sh`. I rilievi arrivano da due "
        "revisori esterni e **non sono ancora un giudizio**: lo diventano quando ogni scheda ha un "
        "verdetto motivato scritto sotto."
    )
    righe.append("")

    if problemi:
        righe.append("> [!WARNING]")
        righe.append("> **Non tutti i revisori hanno risposto.**")
        for p in problemi:
            righe.append(f"> - {p}")
        righe.append("")

    per_fonte = {}
    for r in rilievi:
        per_fonte[r["fonte"]] = per_fonte.get(r["fonte"], 0) + 1
    conteggio = ", ".join(f"{k}: {v}" for k, v in sorted(per_fonte.items())) or "nessuno"
    righe.append(f"**{len(rilievi)} rilievi** — {conteggio}.")
    righe.append("")

    if not rilievi:
        righe.append("Nessun rilievo. Se sopra non c'è un avviso, i due revisori hanno")
        righe.append("guardato la PR e non hanno trovato niente da dire.")
        righe.append("")
    else:
        righe.append("| ID | Gravità | Confidenza | Categoria | Titolo | Verdetto |")
        righe.append("|---|---|---|---|---|---|")
        for r in rilievi:
            righe.append(
                "| {id} | {gravita} | {confidenza} | {categoria} | {titolo} | _da compilare_ |".format(
                    id=r["id"],
                    gravita=r.get("gravita", "?"),
                    confidenza=r.get("confidenza", "?"),
                    categoria=r.get("categoria", "?"),
                    titolo=r.get("titolo", "").replace("|", "\\|"),
                )
            )
        righe.append("")

    for r in rilievi:
        righe.append(f"## {r['id']} — {r.get('titolo', 'senza titolo')}")
        righe.append("")
        righe.append(f"*Sollevato da {r['fonte']}.*" + (
            f" Probabilmente lo stesso rilievo di {', '.join(r['simile_a'])}."
            if r.get("simile_a") else ""
        ))
        righe.append("")
        for chiave, etichetta in CAMPI:
            valore = str(r.get(chiave, "") or "").strip()
            if valore:
                righe.append(f"- **{etichetta}:** {valore}")
        righe.append("")
        if r.get("evidenza"):
            righe.append("**Evidenza citata dal revisore:**")
            righe.append("")
            righe.append("```")
            righe.append(str(r["evidenza"]).rstrip())
            righe.append("```")
            righe.append("")
        if r.get("perche"):
            righe.append(f"**Perché sarebbe un problema:** {r['perche']}")
            righe.append("")
        if r.get("rimedio"):
            righe.append(f"**Rimedio proposto:** {r['rimedio']}")
            righe.append("")
        righe.append("### Verdetto")
        righe.append("")
        righe.append("_da compilare_")
        righe.append("")

    (cartella / "rilievi.md").write_text("\n".join(righe) + "\n", encoding="utf-8")


def main():
    if len(sys.argv) != 3:
        print("uso: normalizza.py <cartella-di-lavoro> <numero-pr>", file=sys.stderr)
        return 2

    cartella = Path(sys.argv[1])
    numero = sys.argv[2]
    if not cartella.is_dir():
        print(f"normalizza: {cartella} non esiste.", file=sys.stderr)
        return 1

    rilievi = []
    problemi = []
    for nome_file, sigla, etichetta in FONTI:
        trovati, problema = leggi_fonte(cartella, nome_file, sigla, etichetta)
        rilievi.extend(trovati)
        if problema:
            problemi.append(problema)

    accoppia(rilievi)
    rilievi.sort(key=lambda r: (ORDINE_GRAVITA.get(r.get("gravita"), 3), r["id"]))

    (cartella / "rilievi.json").write_text(
        json.dumps({"pr": numero, "rilievi": rilievi, "problemi": problemi},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    scrivi_markdown(cartella, numero, rilievi, problemi)

    print(f"{len(rilievi)} rilievi in {cartella / 'rilievi.md'}")
    for p in problemi:
        print(f"  attenzione: {p}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
