"""`SubprocessBackup`: un processo esterno letto riga per riga, senza `mongodump`.

**Queste prove lanciano processi veri.** Non c'è un `Mock` di `subprocess`, e non è
purismo: metà di ciò che l'adattatore deve garantire — che il figlio parta alla chiamata,
che la password non finisca fra i suoi argomenti, che l'iteratore abbandonato non lasci un
`mongodump` orfano — riguarda proprio il confine col sistema operativo, cioè esattamente
la parte che un mock sostituirebbe con la propria opinione. Al posto di `mongodump` c'è un
programma Python di sei righe che scrive su `stderr` le righe che la prova gli detta ed
esce col codice che la prova gli detta: un eseguibile vero, che si comporta come lo
strumento vero perché la prova gli ha detto come.

**Le righe dettate sono misurate, non inventate.** Ognuna delle costanti qui sotto è stata
osservata contro `mongodump`/`mongorestore` 100.18.0 sullo stack 02
([M-023](../../docs/Sources.md#m-023), [M-024](../../docs/Sources.md#m-024)). Se domani
una versione nuova cambia il formato, sono queste costanti a dover cambiare — e la prova
che le usa dirà dove.

La conformità alla porta la verifica `mypy --strict` sulle annotazioni `BackupTool` qui
sotto, non un `isinstance`: è la regola dei doppi, e vale per gli adattatori uguale.
"""

import ast
import os
import sys
import time
from pathlib import Path
from typing import Iterator, Sequence

import pytest

from mongolab.domain.modelli import Progress
from mongolab.domain.porte import BackupTool
from mongolab.infrastructure.backup import (
    ComandoFallito,
    RestoreIncompleto,
    SubprocessBackup,
    leggi_avanzamento,
)

# --- Le righe vere, come lo strumento le scrive ---------------------------------------

APERTURA = (
    "2026-09-03T12:08:29.824+0000\twriting `lab.ordini` to "
    "`/tmp/dump-02/lab/ordini.bson`"
)
BARRA = (
    "2026-09-03T12:08:32.811+0000\t[######################..]  lab.ordini  "
    "1863086/2000000  (93.2%)"
)
CHIUSURA = "2026-09-03T12:08:32.980+0000\tdone dumping `lab.ordini` (2000000 documents)"
OPLOG_APERTURA = "2026-09-03T12:06:51.934+0000\twriting captured oplog to ``"
OPLOG_CHIUSURA = "2026-09-03T12:06:51.935+0000\t\tdumped 1 oplog entry"
BARRA_RESTORE = (
    "2026-09-03T12:15:04.261+0000\t[#################.......]  lab_ripristinato.ordini  "
    "33.0MB/46.5MB  (71.0%)"
)
RESTORE_CHIUSURA = (
    "2026-09-03T12:15:10.057+0000\tfinished restoring `lab_ripristinato.ordini` "
    "(400000 documents, 0 failures)"
)
SOMMARIO_PULITO = (
    "2026-09-03T12:15:25.532+0000\t400000 document(s) restored successfully. "
    "0 document(s) failed to restore."
)
SOMMARIO_CON_PERDITE = (
    "2026-09-03T12:15:10.104+0000\t400000 document(s) restored successfully. "
    "50000 document(s) failed to restore."
)
FALLIMENTO = (
    "2026-09-03T12:15:10.190+0000\tFailed: cannot use --oplogReplay with namespace "
    "renames specified"
)
CHIESTA_PASSWORD = "2026-09-03T12:08:29.809+0000\treading password from standard input"
PROMPT = "Enter password for mongo user:"

BYTE_VERI_DEL_BSON = 48_760_014
"""Quanto misurava davvero il `.bson` che la barra qui sopra annuncia come `46.5MB`.

Letto con `stat -c %s` dentro il container, sullo stesso file che quel restore stava
leggendo ([M-026](../../docs/Sources.md#m-026)). È il metro con cui
`test_la_barra_del_restore_conta_byte` giudica la conversione: un'asserzione contro
`1024**2` scritto anche nella prova verificherebbe soltanto che due copie della stessa
scelta coincidono.
"""

PASSWORD_DI_PROVA = "non-e-un-segreto-e-non-lo-sara-mai"
"""Deliberatamente non una password vera: queste prove la cercano dentro `argv`, dentro il
diario del figlio e dentro il testo delle eccezioni, e una prova che maneggia il segreto
del laboratorio per verificare che non si veda è una prova che lo fa vedere quando fallisce."""


# --- Un eseguibile vero che non è mongodump -------------------------------------------

SORGENTE = '''\
import os, sys, time

with open({diario!r}, "w") as diario:
    diario.write(repr(os.getpid()) + "\\n")
    diario.write(repr(sys.argv[1:]) + "\\n")
    diario.write(repr(sys.stdin.read()) + "\\n")
    diario.write(repr(os.getcwd()) + "\\n")
for riga in {righe!r}:
    print(riga, file=sys.stderr, flush=True)
time.sleep({attesa!r})
sys.exit({codice!r})
'''


def strumento_finto(
    dove: Path,
    righe: Sequence[str] = (),
    codice: int = 0,
    attesa: float = 0.0,
) -> tuple[tuple[str, ...], Path]:
    """Un programma che si comporta come `mongodump`, e un diario di ciò che gli è arrivato.

    Il diario si scrive **prima** delle righe su `stderr`, così una prova che ha appena
    consumato il primo avanzamento sa che è già completo. Contiene il pid perché la prova
    sull'iteratore abbandonato deve poter chiedere al sistema operativo se quel processo
    esiste ancora, e chiederlo all'adattatore significherebbe fidarsi della sua parola.
    """
    diario = dove / "diario.txt"
    sorgente = dove / "finto.py"
    sorgente.write_text(
        SORGENTE.format(
            diario=str(diario), righe=list(righe), attesa=attesa, codice=codice
        )
    )
    return (sys.executable, str(sorgente)), diario


def diario_di(percorso: Path) -> tuple[int, list[str], str]:
    """Pid, argomenti ricevuti e testo arrivato su `stdin`, come il figlio li ha visti.

    Scarta le righe in più con `*_`: il diario ne ha una quarta — la directory di
    partenza — che interessa a una prova sola, e allargare qui la tupla vorrebbe dire
    ritoccare sette punti di lettura per un dato che sei di loro non guardano.
    """
    pid, argomenti, ingresso, *_ = percorso.read_text().splitlines()
    return int(pid), list(ast.literal_eval(argomenti)), str(ast.literal_eval(ingresso))


def partenza_di(percorso: Path) -> str:
    """La directory da cui il figlio è partito, com'è lui a vederla."""
    return str(ast.literal_eval(percorso.read_text().splitlines()[3]))


def vivo(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def strumento(
    comando: Sequence[str],
    password: str | None = PASSWORD_DI_PROVA,
    dove: Path | None = None,
) -> SubprocessBackup:
    return SubprocessBackup(
        host="rs0/mongo-rs-1:27017",
        comando_dump=comando,
        comando_restore=comando,
        utente="admin" if password is not None else None,
        password=password,
        database="lab",
        dove=dove,
    )


# --- Il lettore di righe ---------------------------------------------------------------


def test_la_barra_di_avanzamento_porta_i_due_numeri() -> None:
    """L'unica riga di `mongodump` con un denominatore, ed è quella che disegna la barra."""
    avanzamento = leggi_avanzamento(BARRA)

    assert avanzamento == Progress(
        fase="lab.ordini",
        completati=1_863_086,
        totali=2_000_000,
        messaggio="[######################..]  lab.ordini  1863086/2000000  (93.2%)",
    )


def test_la_percentuale_si_ricalcola_e_coincide_con_quella_dello_strumento() -> None:
    """Se divergessero, uno dei due numeri sarebbe letto male e la barra mentirebbe."""
    avanzamento = leggi_avanzamento(BARRA)

    assert avanzamento is not None
    assert avanzamento.percentuale is not None
    assert round(avanzamento.percentuale, 1) == 93.2


def test_l_apertura_di_una_collezione_non_ha_totale() -> None:
    """`writing` annuncia il lavoro senza dire quanto è: `totali` resta `None`, non zero.

    È la ragione per cui `Progress.totali` è opzionale. Uno zero al denominatore sarebbe
    un totale inventato, e `percentuale` lo tratterebbe come una divisione impossibile
    invece che come una barra che non si può ancora disegnare.
    """
    avanzamento = leggi_avanzamento(APERTURA)

    assert avanzamento is not None
    assert avanzamento.fase == "lab.ordini"
    assert avanzamento.completati == 0
    assert avanzamento.totali is None
    assert avanzamento.percentuale is None


def test_la_chiusura_di_una_collezione_e_completa_al_cento_per_cento() -> None:
    avanzamento = leggi_avanzamento(CHIUSURA)

    assert avanzamento is not None
    assert avanzamento.fase == "lab.ordini"
    assert avanzamento.completati == 2_000_000
    assert avanzamento.totali == 2_000_000
    assert avanzamento.percentuale == 100.0


def test_l_oplog_e_una_fase_col_suo_nome() -> None:
    """`writing captured oplog to \\`\\`` non nomina nessun namespace: il backtick è vuoto."""
    assert leggi_avanzamento(OPLOG_APERTURA) == Progress(
        fase="oplog", completati=0, totali=None, messaggio="writing captured oplog to ``"
    )


def test_una_sola_voce_di_oplog_si_legge_al_singolare() -> None:
    """`dumped 1 oplog entry`, non `entries`. E la riga arriva con due tabulazioni."""
    avanzamento = leggi_avanzamento(OPLOG_CHIUSURA)

    assert avanzamento is not None
    assert avanzamento.fase == "oplog"
    assert avanzamento.completati == 1
    assert avanzamento.totali == 1


def test_la_barra_del_restore_conta_byte() -> None:
    """`mongorestore` misura in byte quello che `mongodump` misura in documenti.

    Due unità nello stesso campo, e nessun campo che dica quale: è una scomodità
    dichiarata in `leggi_avanzamento`, non un difetto di questa prova.
    """
    avanzamento = leggi_avanzamento(BARRA_RESTORE)

    assert avanzamento is not None
    assert avanzamento.fase == "lab_ripristinato.ordini"
    assert avanzamento.totali == 48_758_784


def test_la_barra_del_restore_usa_la_base_1024_e_non_la_1000() -> None:
    """Il giudice è la dimensione vera del file, non il moltiplicatore scritto nel codice.

    In base 1000 `46.5MB` varrebbe 46 500 000 byte, cioè il 4,6% in meno del file che lo
    strumento stava leggendo: una barra che a metà dump direbbe di aver già finito.
    """
    avanzamento = leggi_avanzamento(BARRA_RESTORE)

    assert avanzamento is not None
    assert avanzamento.totali is not None
    scarto = abs(avanzamento.totali - BYTE_VERI_DEL_BSON) / BYTE_VERI_DEL_BSON
    assert scarto < 0.001, f"scarto {scarto:.1%} dalla dimensione vera del .bson"


def test_la_chiusura_di_un_restore_porta_i_documenti_scritti() -> None:
    avanzamento = leggi_avanzamento(RESTORE_CHIUSURA)

    assert avanzamento is not None
    assert avanzamento.fase == "lab_ripristinato.ordini"
    assert avanzamento.completati == 400_000
    assert avanzamento.totali == 400_000


@pytest.mark.parametrize(
    "riga",
    [
        CHIESTA_PASSWORD,
        PROMPT,
        FALLIMENTO,
        SOMMARIO_PULITO,
        "2026-09-03T12:15:10.250+0000\tbuilding a list of collections to restore",
        "",
    ],
)
def test_cio_che_non_e_avanzamento_non_diventa_avanzamento(riga: str) -> None:
    """Comprese le due righe della password, che sono la parte più delicata.

    Se `Enter password for mongo user:` diventasse un `Progress`, la TUI mostrerebbe a
    schermo, in scena, una riga che chiede una password.
    """
    assert leggi_avanzamento(riga) is None


# --- Il processo -----------------------------------------------------------------------


def test_gli_avanzamenti_arrivano_nell_ordine_in_cui_lo_strumento_li_scrive(
    tmp_path: Path,
) -> None:
    comando, _ = strumento_finto(tmp_path, righe=[APERTURA, BARRA, CHIUSURA])
    backup: BackupTool = strumento(comando)

    avanzamenti = list(backup.dump(tmp_path / "dump"))

    assert [(a.fase, a.completati) for a in avanzamenti] == [
        ("lab.ordini", 0),
        ("lab.ordini", 1_863_086),
        ("lab.ordini", 2_000_000),
    ]


def test_il_processo_parte_alla_chiamata_non_al_primo_next(tmp_path: Path) -> None:
    """La porta promette che qualcosa accade **chiamando** `dump`, non scorrendolo.

    Un eseguibile che non esiste è il modo più netto di verificarlo: se `dump` fosse una
    funzione generatrice il corpo non partirebbe, `Popen` non verrebbe mai costruito, e
    questa riga passerebbe senza sollevare niente. È la stessa proprietà che la docstring
    di `FakeBackup` dichiara di imitare.
    """
    backup = strumento(("questo-eseguibile-non-esiste-da-nessuna-parte",))

    with pytest.raises(FileNotFoundError):
        backup.dump(tmp_path / "dump")


def test_un_uscita_diversa_da_zero_solleva_col_codice_e_col_messaggio(
    tmp_path: Path,
) -> None:
    """[ADR-0077](../../../docs/Decision.md#adr-0077): il verdetto è il codice d'uscita."""
    comando, _ = strumento_finto(tmp_path, righe=[FALLIMENTO], codice=1)
    backup = strumento(comando)

    with pytest.raises(ComandoFallito) as caduta:
        list(backup.dump(tmp_path / "dump"))

    assert caduta.value.codice == 1
    assert "cannot use --oplogReplay with namespace renames specified" in (
        caduta.value.messaggio
    )


def test_gli_avanzamenti_gia_prodotti_arrivano_prima_dell_errore(tmp_path: Path) -> None:
    """Il caso che serve davvero: il dump si rompe **dopo** aver scritto qualcosa.

    È lo stesso caso per cui `FakeBackup` accetta un `errore` da sollevare dopo la
    cronaca. Qui non è un doppio a deciderlo: è un processo che è uscito diverso da zero
    dopo aver stampato due righe, e ciò che la TUI ha già mostrato non va disfatto.
    """
    comando, _ = strumento_finto(tmp_path, righe=[APERTURA, BARRA, FALLIMENTO], codice=1)
    backup = strumento(comando)

    visti = []
    with pytest.raises(ComandoFallito):
        for avanzamento in backup.dump(tmp_path / "dump"):
            visti.append(avanzamento.completati)

    assert visti == [0, 1_863_086]


def test_chiudere_l_iteratore_ferma_il_processo(tmp_path: Path) -> None:
    """Un dump abbandonato a metà non deve restare a girare contro il cluster.

    È il rovescio della medaglia del Passo 1: se l'avanzamento si consuma man mano, allora
    esiste un consumatore che può smettere — un Ctrl-C, una schermata chiusa — e il
    processo esterno non se ne accorge da solo.
    """
    comando, diario = strumento_finto(tmp_path, righe=[APERTURA], attesa=120.0)
    backup = strumento(comando)

    avanzamenti = backup.dump(tmp_path / "dump")
    next(avanzamenti)
    pid, _, _ = diario_di(diario)
    assert vivo(pid)

    avanzamenti.close()  # type: ignore[attr-defined]

    scadenza = time.monotonic() + 10.0
    while vivo(pid) and time.monotonic() < scadenza:
        time.sleep(0.02)
    assert not vivo(pid)


def test_un_eccezione_dentro_l_iteratore_ferma_il_processo(tmp_path: Path) -> None:
    """Non solo la chiusura ordinata: anche un'interruzione deve fermare il dump.

    `close()` solleva `GeneratorExit` dentro il generatore, ed è il caso educato. Ma il
    consumatore può anche morire in un altro modo — un `KeyboardInterrupt` che arriva
    mentre il generatore è fermo a leggere `stderr`, un errore sollevato da chi disegna
    l'avanzamento — e allora l'eccezione che passa dal punto di sospensione non è
    `GeneratorExit`. Il processo non deve sopravvivere neanche a quelle: da qui il figlio
    non si distingue, ed è lui che sta leggendo il cluster.
    """
    comando, diario = strumento_finto(tmp_path, righe=[APERTURA], attesa=120.0)
    backup = strumento(comando)

    avanzamenti = backup.dump(tmp_path / "dump")
    next(avanzamenti)
    pid, _, _ = diario_di(diario)
    assert vivo(pid)

    with pytest.raises(KeyboardInterrupt):
        avanzamenti.throw(KeyboardInterrupt())  # type: ignore[attr-defined]

    scadenza = time.monotonic() + 10.0
    while vivo(pid) and time.monotonic() < scadenza:
        time.sleep(0.02)
    assert not vivo(pid)


# --- La credenziale ---------------------------------------------------------------------


def test_la_password_non_compare_fra_gli_argomenti_del_processo(tmp_path: Path) -> None:
    """La misura che ha deciso il progetto di questo adattatore.

    Passare `-p <valore>` come elemento di `argv` **non** tiene il segreto fuori dalla
    tabella dei processi: dentro il container `ps -eo args` lo mostra per intero
    ([M-025](../../docs/Sources.md#m-025)). La lista al posto della stringa di shell serve
    a un'altra cosa — nessuna interpretazione di metacaratteri — e da sola non basta.
    """
    comando, diario = strumento_finto(tmp_path, righe=[APERTURA])
    backup = strumento(comando)

    list(backup.dump(tmp_path / "dump"))

    _, argomenti, _ = diario_di(diario)
    assert PASSWORD_DI_PROVA not in argomenti
    assert not any(PASSWORD_DI_PROVA in argomento for argomento in argomenti)
    assert "-p" not in argomenti
    assert "--password" not in argomenti


def test_la_password_arriva_su_stdin_e_lo_stdin_si_chiude(tmp_path: Path) -> None:
    """Senza la chiusura il figlio resterebbe a leggere per sempre, e il dump non finirebbe."""
    comando, diario = strumento_finto(tmp_path, righe=[APERTURA])
    backup = strumento(comando)

    list(backup.dump(tmp_path / "dump"))

    _, argomenti, ingresso = diario_di(diario)
    assert ingresso == PASSWORD_DI_PROVA + "\n"
    assert "--username" in argomenti


def test_senza_credenziale_su_stdin_non_si_scrive_niente(tmp_path: Path) -> None:
    """Lo stack 01 non ha autenticazione, e uno strumento che aspetta una password lì si pianta."""
    comando, diario = strumento_finto(tmp_path, righe=[APERTURA])
    backup = strumento(comando, password=None)

    list(backup.dump(tmp_path / "dump"))

    _, argomenti, ingresso = diario_di(diario)
    assert ingresso == ""
    assert "--username" not in argomenti


def test_l_errore_non_mostra_la_password(tmp_path: Path) -> None:
    """Un `ComandoFallito` finisce in un traceback, e un traceback finisce in una slide."""
    comando, _ = strumento_finto(tmp_path, righe=[FALLIMENTO], codice=1)
    backup = strumento(comando)

    with pytest.raises(ComandoFallito) as caduta:
        list(backup.dump(tmp_path / "dump"))

    assert PASSWORD_DI_PROVA not in str(caduta.value)
    assert PASSWORD_DI_PROVA not in repr(caduta.value)


# --- Gli argomenti che l'adattatore costruisce -------------------------------------------


def test_il_dump_riceve_la_destinazione_che_gli_e_stata_chiesta(tmp_path: Path) -> None:
    comando, diario = strumento_finto(tmp_path, righe=[APERTURA])
    backup = strumento(comando)
    destinazione = tmp_path / "dump-02"

    list(backup.dump(destinazione))

    _, argomenti, _ = diario_di(diario)
    assert argomenti[argomenti.index("--out") + 1] == str(destinazione)


def test_il_restore_isola_il_database_di_origine_e_lo_rinomina(tmp_path: Path) -> None:
    """`--nsFrom/--nsTo` **rinomina**, non filtra.

    Misurato: un restore dell'intera directory di dump con solo `--nsFrom/--nsTo` ha
    ripristinato anche ciò che non corrispondeva — `lab.ordini` sopra sé stessa, con
    cinquantamila chiavi duplicate, e gli utenti da `admin/system.users.bson`
    ([M-024](../../docs/Sources.md#m-024)). Serve `--nsInclude` accanto, ed è la ragione
    per cui questa prova esiste.
    """
    comando, diario = strumento_finto(tmp_path, righe=[RESTORE_CHIUSURA])
    backup: BackupTool = strumento(comando)
    origine = tmp_path / "dump-02"

    list(backup.restore(origine, "lab_ripristinato"))

    _, argomenti, _ = diario_di(diario)
    assert argomenti[argomenti.index("--nsInclude") + 1] == "lab.*"
    assert argomenti[argomenti.index("--nsFrom") + 1] == "lab.*"
    assert argomenti[argomenti.index("--nsTo") + 1] == "lab_ripristinato.*"
    assert argomenti[-1] == str(origine)


def test_le_opzioni_del_copione_arrivano_allo_strumento(tmp_path: Path) -> None:
    """`--readPreference=secondary --oplog`: la forma che il Blocco 2 Atto III mostra."""
    comando, diario = strumento_finto(tmp_path, righe=[APERTURA])
    backup = SubprocessBackup(
        host="rs0/mongo-rs-1:27017",
        comando_dump=comando,
        comando_restore=comando,
        utente="admin",
        password=PASSWORD_DI_PROVA,
        database="lab",
        opzioni_dump=("--readPreference=secondary", "--oplog"),
    )

    list(backup.dump(tmp_path / "dump"))

    _, argomenti, _ = diario_di(diario)
    assert "--readPreference=secondary" in argomenti
    assert "--oplog" in argomenti


# --- Il verdetto che lo strumento non dà ------------------------------------------------


def test_un_restore_che_perde_documenti_non_e_un_restore_riuscito(tmp_path: Path) -> None:
    """Misurato: `mongorestore` perde cinquantamila documenti ed esce **zero**.

    ADR-0077 dice che un avviso che non cambia il codice d'uscita è un avviso che nessuno
    legge. Qui l'avviso è dello strumento esterno, e il codice d'uscita che non cambia è il
    suo: l'adattatore mette il verdetto che `mongorestore` non ha messo
    ([ADR-0084](../../../docs/Decision.md#adr-0084)).
    """
    comando, _ = strumento_finto(
        tmp_path, righe=[RESTORE_CHIUSURA, SOMMARIO_CON_PERDITE], codice=0
    )
    backup = strumento(comando)

    with pytest.raises(RestoreIncompleto) as caduta:
        list(backup.restore(tmp_path / "dump", "lab_ripristinato"))

    assert caduta.value.restaurati == 400_000
    assert caduta.value.falliti == 50_000


def test_un_restore_senza_perdite_non_solleva(tmp_path: Path) -> None:
    """Altrimenti la guardia sopra passerebbe anche contando male, o non contando affatto."""
    comando, _ = strumento_finto(
        tmp_path, righe=[RESTORE_CHIUSURA, SOMMARIO_PULITO], codice=0
    )
    backup = strumento(comando)

    avanzamenti: Iterator[Progress] = backup.restore(tmp_path / "dump", "lab_ripristinato")

    assert [a.completati for a in avanzamenti] == [400_000]


# --- Da dove parte il comando -----------------------------------------------------------


def test_lo_strumento_parte_dalla_directory_che_gli_e_stata_detta(tmp_path: Path) -> None:
    """`docker compose -f docker/02-replicaset/compose.yaml` è un percorso **relativo**.

    Il frasario li tiene relativi apposta, perché la riga annunciata dalla scena si possa
    incollare in un terminale aperto nella radice del repository e funzioni identica. Chi
    la esegue però non parte per forza di lì: `mongolab demo backup-live` si lancia da
    qualunque directory, e senza questo parametro `docker compose` risponderebbe «no
    configuration file provided» ovunque tranne che nella radice.

    È lo stesso `dove` di `RegiaCompose`, e lo stesso valore — `radice()` — glielo passa
    la stessa riga della radice di composizione. Due nomi diversi per la stessa cosa
    sarebbero due cose da tenere allineate.
    """
    comando, diario = strumento_finto(tmp_path, righe=[APERTURA])
    partenza = tmp_path / "altrove"
    partenza.mkdir()
    backup = strumento(comando, dove=partenza)

    list(backup.dump(tmp_path / "dump"))

    assert partenza_di(diario) == str(partenza)


def test_senza_indicazione_lo_strumento_parte_da_dove_sta(tmp_path: Path) -> None:
    """Il predefinito è `None`, che per `Popen` vuol dire «la directory di chi chiama».

    Contro `mongodump` installato e nel `PATH` non cambia niente, ed è il caso delle prove
    d'integrazione che invocano `docker exec` per nome: chiedere una directory anche lì
    vorrebbe dire chiedere un dato che non serve a nessuno.
    """
    comando, diario = strumento_finto(tmp_path, righe=[APERTURA])
    backup = strumento(comando)

    list(backup.dump(tmp_path / "dump"))

    assert partenza_di(diario) == os.getcwd()


def test_anche_il_restore_parte_da_li(tmp_path: Path) -> None:
    """Le due righe entrano nello stesso nodo con lo stesso frasario: partono dallo stesso
    posto, o la seconda scena fallirebbe dopo che la prima è riuscita."""
    comando, diario = strumento_finto(tmp_path, righe=[RESTORE_CHIUSURA])
    partenza = tmp_path / "altrove"
    partenza.mkdir()
    backup = strumento(comando, dove=partenza)

    list(backup.restore(tmp_path / "dump", "lab_ripristinato"))

    assert partenza_di(diario) == str(partenza)


# --- La riga che si può mostrare --------------------------------------------------------


def test_gli_argomenti_del_dump_sono_quelli_che_il_processo_riceve(tmp_path: Path) -> None:
    """Ciò che l'adattatore dichiara di eseguire e ciò che esegue sono la stessa tupla.

    Se fossero due costruzioni distinte — una per mostrare, una per eseguire — la scena
    potrebbe mostrare una riga e lanciarne un'altra, che è il difetto peggiore che una
    demo possa avere: il pubblico verificherebbe qualcosa che non è successo.
    """
    comando, diario = strumento_finto(tmp_path, righe=[APERTURA])
    backup = strumento(comando)
    destinazione = tmp_path / "dump"

    dichiarati = backup.argomenti_dump(destinazione)
    list(backup.dump(destinazione))

    _, ricevuti, _ = diario_di(diario)
    assert list(dichiarati) == list(comando) + ricevuti


def test_gli_argomenti_del_restore_sono_quelli_che_il_processo_riceve(
    tmp_path: Path,
) -> None:
    comando, diario = strumento_finto(tmp_path, righe=[RESTORE_CHIUSURA])
    backup = strumento(comando)
    origine = tmp_path / "dump"

    dichiarati = backup.argomenti_restore(origine, "lab_ripristinato")
    list(backup.restore(origine, "lab_ripristinato"))

    _, ricevuti, _ = diario_di(diario)
    assert list(dichiarati) == list(comando) + ricevuti


def test_la_riga_da_mostrare_non_contiene_la_password() -> None:
    """È [ADR-0054](../../../docs/Decision.md#adr-0054) diventata una proprietà leggibile.

    La riga si può stampare in scena — e la scena del backup a caldo la stampa, perché
    `mongodump --readPreference=secondary --oplog` è la cosa che il Blocco 2 sta
    spiegando — proprio perché il segreto non ci passa: viaggia su `stdin`, e questa prova
    è ciò che impedisce a un rifacimento di rimetterlo fra gli argomenti.
    """
    backup = strumento(("mongodump",))

    riga = " ".join(backup.argomenti_dump(Path("/tmp/dump")))

    assert PASSWORD_DI_PROVA not in riga
    assert "--username" in riga
