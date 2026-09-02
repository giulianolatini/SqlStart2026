"""Le coerenze fra due file che nessuno dei due può controllare da solo.

Gli altri moduli di prova esercitano uno strumento su dati costruiti apposta, e vanno bene
così: provano una regola, non il repository. Questo modulo fa l'opposto — legge i file
**veri** e verifica che due posti diversi continuino a dire la stessa cosa.

Nasce da due debiti segnati in [ADR-0049] e chiusi eseguendo, non ragionando: l'elenco
delle porte di `tools/preflight.sh` era scritto a mano e slegato dai file Compose, e il
`Makefile` non sapeva quali profili il file Compose dichiarasse. Nessuno dei due era
sbagliato il giorno in cui li si è misurati: erano sbagliabili in silenzio, che è la
proprietà che questi controlli tolgono.
"""

import pathlib
import re

import pytest
import yaml

RADICE = pathlib.Path(__file__).resolve().parents[2]

COMPOSE = (
    RADICE / "docker/01-standalone/compose.yaml",
    RADICE / "docker/02-replicaset/compose.yaml",
    RADICE / "docker/03-sharded/compose.yaml",
)

PREFLIGHT = RADICE / "tools/preflight.sh"
MAKEFILE = RADICE / "Makefile"

# `${NOME:-valore}` e `${NOME:?spiegazione}`. Qui interessa solo la prima forma, perché è
# quella con cui i file Compose scrivono le porte: il valore predefinito è la porta della
# mappa del design, e la variabile serve a chi vuole spostarla senza toccare il file.
INTERPOLAZIONE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::([-?])([^}]*))?\}")


def senza_interpolazione(testo):
    """Sostituisce `${NOME:-valore}` con il suo valore predefinito.

    Non si passa da `docker compose config` apposta: quello richiede i file `.env` che
    stanno fuori dal repository (ADR-0014), e un controllo che non gira su un clone appena
    fatto è un controllo che non gira.
    """

    def sostituisci(trovato):
        return trovato.group(3) if trovato.group(2) == "-" else ""

    return INTERPOLAZIONE.sub(sostituisci, testo)


def porte_pubblicate():
    """Le porte dell'host che i tre file Compose espongono, con chi le espone.

    Restituisce `{porta: ["stack/servizio", ...]}`: il valore serve a far dire al
    fallimento **quale** servizio ha portato una porta nuova, che è l'informazione con cui
    si corregge `preflight.sh` in dieci secondi invece che in dieci minuti.
    """
    trovate = {}
    for percorso in COMPOSE:
        stack = percorso.parent.name
        documento = yaml.safe_load(percorso.read_text(encoding="utf-8"))
        for nome, servizio in (documento.get("services") or {}).items():
            for voce in servizio.get("ports") or []:
                if isinstance(voce, dict):
                    lato_host = str(voce.get("published", ""))
                else:
                    pezzi = senza_interpolazione(str(voce)).split(":")
                    lato_host = pezzi[-2] if len(pezzi) >= 2 else ""
                if lato_host:
                    trovate.setdefault(int(lato_host), []).append(f"{stack}/{nome}")
    return trovate


def porte_di_preflight():
    """L'elenco `PORTE=(...)` di `tools/preflight.sh`, nell'ordine in cui è scritto."""
    riga = re.search(
        r"^PORTE=\(([^)]*)\)", PREFLIGHT.read_text(encoding="utf-8"), re.MULTILINE
    )
    assert riga, "in tools/preflight.sh non c'è più una riga PORTE=(...)"
    return [int(porta) for porta in riga.group(1).split()]


def test_ogni_porta_pubblicata_dai_compose_e_controllata_da_preflight():
    # Il verso che conta la mattina del talk. Una porta pubblicata e non controllata è un
    # `up` che fallisce in sala per un processo che occupava quella porta da ieri sera, e
    # `preflight` che poco prima aveva detto che era tutto a posto.
    mancanti = {
        porta: chi for porta, chi in porte_pubblicate().items()
        if porta not in set(porte_di_preflight())
    }
    assert not mancanti, (
        "porte pubblicate dai file Compose e non controllate da preflight.sh: "
        f"{mancanti} — aggiungerle all'elenco PORTE di tools/preflight.sh"
    )


def test_preflight_non_controlla_porte_che_nessuno_pubblica():
    # Il verso opposto costa meno ma mente lo stesso: una porta rimasta nell'elenco dopo
    # che il servizio è stato tolto fa fallire il preflight di chi ha quella porta occupata
    # per motivi suoi, e nessuno riesce a capire quale servizio del lab la vorrebbe.
    eccedenti = sorted(set(porte_di_preflight()) - set(porte_pubblicate()))
    assert not eccedenti, (
        f"porte controllate da preflight.sh che nessun file Compose pubblica: {eccedenti} "
        "— toglierle dall'elenco PORTE, o è cambiato un file Compose"
    )


def test_l_elenco_delle_porte_e_ordinato_e_senza_ripetizioni():
    # Non è pedanteria tipografica: quindici numeri su una riga sola si leggono solo se
    # sono in ordine, e un doppione non dà nessun errore — dà un controllo eseguito due
    # volte e un altro dimenticato, senza che si veda.
    elencate = porte_di_preflight()
    assert elencate == sorted(elencate), "l'elenco PORTE non è in ordine crescente"
    doppie = sorted({p for p in elencate if elencate.count(p) > 1})
    assert not doppie, f"porte ripetute nell'elenco PORTE: {doppie}"


def bersagli_del_makefile():
    """`{nome: (prerequisiti, righe della ricetta)}` per i bersagli del Makefile.

    Un parser minimo e volutamente ottuso: una riga che comincia a colonna zero con un
    nome seguito da `:` apre un bersaglio, le righe che cominciano con una tabulazione ne
    sono la ricetta. Non gestisce le regole con più bersagli né i nomi calcolati con una
    variabile, e non deve: qui servono i bersagli scritti a mano.
    """
    intestazione = re.compile(r"^([A-Za-z][A-Za-z0-9_.-]*)\s*:(?!=)\s*(.*)$")
    bersagli = {}
    corrente = None
    for riga in MAKEFILE.read_text(encoding="utf-8").splitlines():
        if riga.startswith("\t"):
            if corrente:
                bersagli[corrente][1].append(riga)
            continue
        trovato = intestazione.match(riga)
        if trovato:
            corrente = trovato.group(1)
            prerequisiti = trovato.group(2).split("##")[0].split()
            bersagli[corrente] = (prerequisiti, [])
        elif riga.strip() and not riga.startswith("#"):
            corrente = None
    return bersagli


def test_ogni_bersaglio_che_usa_il_profilo_dichiara_il_guardiano():
    # Compose accetta qualunque stringa dopo `--profile`. Con un refuso seleziona i soli
    # servizi che non dichiarano `profiles:` — uno — e l'avvio muore accusando il keyfile
    # di essere uscito 0, senza mai nominare il profilo (V-069). Il guardiano `profilo-03`
    # trasforma quel messaggio in una frase che dice qual è il problema, ma vale solo per i
    # bersagli che se lo dichiarano: questo controllo è ciò che rende difficile scordarlo
    # al prossimo bersaglio.
    senza_guardiano = sorted(
        nome
        for nome, (prerequisiti, ricetta) in bersagli_del_makefile().items()
        if nome != "profilo-03"
        and any("$(PROFILO)" in riga for riga in ricetta)
        and "profilo-03" not in prerequisiti
    )
    assert not senza_guardiano, (
        f"bersagli che usano $(PROFILO) senza dipendere da profilo-03: {senza_guardiano} "
        "— aggiungere profilo-03 ai loro prerequisiti"
    )


def test_il_guardiano_chiede_i_profili_al_file_compose():
    # La tentazione, la prossima volta che qualcuno tocca questa riga, è scrivere
    # `palco|completo` e chiudere la questione. Sarebbe il debito di prima con un nome
    # nuovo: un terzo profilo nel file Compose resterebbe rifiutato dal Makefile, e il
    # messaggio d'errore direbbe con sicurezza una cosa falsa.
    guardiano = bersagli_del_makefile().get("profilo-03")
    assert guardiano, "il bersaglio profilo-03 non esiste più nel Makefile"
    ricetta = "\n".join(guardiano[1])
    assert "config --profiles" in ricetta, (
        "profilo-03 non chiede più i profili al file Compose con «config --profiles»"
    )
    for scritto_a_mano in ("palco", "completo"):
        assert scritto_a_mano not in ricetta, (
            f"profilo-03 nomina «{scritto_a_mano}» nella ricetta: l'elenco dei profili "
            "validi deve venire dal file Compose, non dal Makefile"
        )


@pytest.mark.parametrize("percorso", COMPOSE, ids=lambda p: p.parent.name)
def test_i_file_compose_letti_dai_controlli_esistono(percorso):
    # Se un file Compose venisse spostato, i controlli qui sopra non fallirebbero: il
    # dizionario delle porte pubblicate si svuoterebbe e l'unico a protestare sarebbe
    # quello sulle porte eccedenti, con un messaggio che accusa preflight.sh di un
    # difetto che non ha.
    assert percorso.is_file(), f"file Compose atteso e non trovato: {percorso}"
