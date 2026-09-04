#!/usr/bin/env python3
"""Registra una demo di terminale in formato asciinema v2.

Perché uno strumento invece di `asciinema`: la registrazione di riserva del talk
deve essere producibile su una macchina che non ha niente installato oltre a
Python e Docker (ADR-0016 — un piano B che richiede di installare qualcosa non è
un piano B). Il formato è quello di asciinema perché è JSON su righe: si legge,
si confronta con `diff`, e i tempi che contengono le scene di questo branch sono
proprio il contenuto della registrazione, non un dettaglio del contenitore.

Il comando gira dentro uno pseudo-terminale e non in una pipe, di proposito: in
una pipe i programmi che colorano l'output smettono di colorare, e la scena
registrata non sarebbe quella che il pubblico vede.

Riproduce anche, e senza `asciinema`: una registrazione di riserva che per essere
vista richiede di installare qualcosa non è una registrazione di riserva.

Con `--regia PREFISSO` fa anche da **seconda finestra**: le righe che il comando
registrato stampa e che cominciano con quel prefisso vengono eseguite qui, e poi
un Invio torna al comando. Serve alle scene che l'applicazione gira dentro la
rete Compose, dove vede la topologia ma non ha il socket del demone: annuncia il
comando che ferma il primario e aspetta che qualcuno lo dia altrove. Dal palco
quel qualcuno è una persona; per registrare la scena dev'essere questo strumento.

Uso:
    python3 tools/registra-terminale.py <destinazione.cast> -- <comando> [argomenti]
    python3 tools/registra-terminale.py --riproduci <registrazione.cast>

    python3 tools/registra-terminale.py \\
        docs/05-talk/registrazioni/failover-docker-kill.cast \\
        --titolo "Failover: docker kill sul primario" \\
        -- make failover-02
"""

from __future__ import annotations

import argparse
import json
import os
import pty
import select
import shlex
import shutil
import signal
import subprocess
import sys
import time

# Le dimensioni del terminale registrato. Fisse e non ereditate dalla finestra di
# chi registra: una registrazione di riserva va proiettata, e 100x30 sta su uno
# schermo da sala senza che il testo vada a capo dove non deve.
COLONNE = 100
RIGHE = 30

# Il pty consegna a blocchi; leggerne di più per volta non cambia i tempi, che
# vengono presi al momento della lettura.
BLOCCO = 65536


def imposta_dimensioni(discendente: int, righe: int, colonne: int) -> None:
    """Dichiara al pty quanto è grande, prima che il comando lo chieda."""
    import fcntl
    import struct
    import termios

    fcntl.ioctl(discendente, termios.TIOCSWINSZ, struct.pack("HHHH", righe, colonne, 0, 0))


def seconda_finestra(riga: str, canale: int) -> None:
    """Esegue la riga annunciata e manda l'Invio a chi la aspettava.

    L'ordine è l'unico possibile: prima il comando, poi la conferma. Invertirli
    vorrebbe dire una scena che riparte prima che il guasto sia avvenuto, cioè un
    failover raccontato senza failover — che è esattamente ciò che la conferma
    esiste per impedire.

    L'uscita del comando si cattura e si riassume su stderr invece di lasciarla
    andare: **non** deve finire nel .cast — nel .cast va ciò che il pubblico
    vedrebbe nella finestra di sinistra — e chi registra deve comunque sapere se
    il comando è riuscito.
    """
    esito = subprocess.run(shlex.split(riga), capture_output=True, text=True)
    print("regia: %s · uscita %d" % (riga, esito.returncode), file=sys.stderr)
    os.write(canale, b"\n")


def registra(
    destinazione: str,
    comando: list[str],
    titolo: str,
    righe: int,
    colonne: int,
    regia: str | None = None,
) -> int:
    """Esegue `comando` in uno pseudo-terminale e ne scrive la registrazione.

    Restituisce il codice di uscita del comando: una registrazione di una demo
    fallita è ancora una registrazione, ma chi la produce deve saperlo subito.
    """
    # Due controlli e due codici, gli stessi che usa la shell: 127 se il comando non
    # c'è, 126 se c'è e non si può eseguire. La distinzione non è pedanteria — chi
    # registra deve capire in un secondo se ha sbagliato a scrivere il nome o a dare
    # il permesso, e senza il secondo controllo `execvpe` falliva più avanti, quando
    # lo pseudo-terminale era già aperto e la registrazione già cominciata.
    if shutil.which(comando[0]) is None:
        if not os.path.exists(comando[0]):
            print("comando non trovato: %s" % comando[0], file=sys.stderr)
            return 127
        if not os.access(comando[0], os.X_OK):
            print("comando non eseguibile: %s" % comando[0], file=sys.stderr)
            return 126

    figlio, discendente = pty.openpty()
    imposta_dimensioni(discendente, righe, colonne)

    ambiente = dict(os.environ)
    ambiente["TERM"] = ambiente.get("TERM", "xterm-256color")
    # `LINES` e `COLUMNS` non li imposta il pty: i programmi che li leggono invece
    # di interrogare il terminale vedrebbero la finestra di chi registra.
    ambiente["LINES"] = str(righe)
    ambiente["COLUMNS"] = str(colonne)

    inizio = time.time()
    pid = os.fork()
    if pid == 0:
        os.close(figlio)
        os.setsid()
        import fcntl
        import termios

        fcntl.ioctl(discendente, termios.TIOCSCTTY, 0)
        os.dup2(discendente, 0)
        os.dup2(discendente, 1)
        os.dup2(discendente, 2)
        if discendente > 2:
            os.close(discendente)
        try:
            os.execvpe(comando[0], comando, ambiente)
        except OSError as errore:
            # Qui siamo già dentro lo pseudo-terminale che si sta registrando: un
            # traceback di Python finirebbe **nel .cast**, con i percorsi assoluti
            # della macchina di chi registra, e la riserva del talk mostrerebbe
            # quello. Si scrive una riga sola, con `os.write` perché dopo `fork` il
            # buffering di `print` non è cosa su cui contare.
            os.write(2, ("non eseguibile: %s: %s\n" % (comando[0], errore.strerror)).encode())
        os._exit(126)  # non si arriva qui se execvpe riesce

    os.close(discendente)

    intestazione = {
        "version": 2,
        "width": colonne,
        "height": righe,
        "timestamp": int(inizio),
        "env": {"SHELL": ambiente.get("SHELL", "/bin/sh"), "TERM": ambiente["TERM"]},
        "title": titolo,
    }

    # Ciò che è arrivato dal pty e non è ancora una riga intera. La regia guarda le
    # righe e non i blocchi: il pty consegna quando gli pare, e un comando annunciato
    # spezzato a metà fra due letture non comincerebbe con il prefisso.
    sospeso = ""

    # Lo stato del comando, se a raccoglierlo è il ramo non bloccante qui sotto: da
    # quel momento il processo non esiste più, e la `waitpid` finale non lo troverebbe.
    raccolto = None

    with open(destinazione, "w", encoding="utf-8") as uscita:
        uscita.write(json.dumps(intestazione, ensure_ascii=False) + "\n")
        while True:
            try:
                pronti, _, _ = select.select([figlio], [], [], 0.2)
            except InterruptedError:
                continue
            if pronti:
                try:
                    dati = os.read(figlio, BLOCCO)
                except OSError:
                    # Il discendente ha chiuso il suo lato: è la fine normale.
                    break
                if not dati:
                    break
                trascorso = round(time.time() - inizio, 6)
                testo = dati.decode("utf-8", errors="replace")
                uscita.write(json.dumps([trascorso, "o", testo], ensure_ascii=False) + "\n")
                uscita.flush()
                if regia is not None:
                    sospeso += testo
                    *complete, sospeso = sospeso.split("\n")
                    for vista in complete:
                        if vista.strip().startswith(regia):
                            seconda_finestra(vista.strip(), figlio)
            else:
                # Nessun output: si controlla se il comando è finito senza chiudere
                # il pty — succede quando lascia dietro di sé un figlio. Lo stato si
                # tiene: questa `waitpid` il processo lo ha già raccolto, e buttarlo
                # via qui significava riportare 0 qualunque cosa fosse successo.
                finito, stato = os.waitpid(pid, os.WNOHANG)
                if finito == pid:
                    raccolto = stato
                    break

    os.close(figlio)
    if raccolto is None:
        try:
            _, raccolto = os.waitpid(pid, 0)
        except ChildProcessError:
            raccolto = 0
    stato = raccolto

    if os.WIFSIGNALED(stato):
        return 128 + os.WTERMSIG(stato)
    return os.WEXITSTATUS(stato)


def riproduci(sorgente: str, velocita: float) -> int:
    """Riscrive la registrazione su stdout rispettandone i tempi.

    I tempi *sono* il contenuto di queste scene — un failover che si vede tutto
    insieme non racconta niente — quindi si aspetta davvero invece di stampare e
    basta. `velocita` serve alle prove, non alla sala: la scena si mostra a 1.
    """
    with open(sorgente, encoding="utf-8") as file:
        intestazione = json.loads(file.readline())
        if intestazione.get("title"):
            print("── %s ──\n" % intestazione["title"], file=sys.stderr)
        inizio = time.time()
        for riga in file:
            quando, tipo, testo = json.loads(riga)
            if tipo != "o":
                continue
            ritardo = quando / velocita - (time.time() - inizio)
            if ritardo > 0:
                time.sleep(ritardo)
            sys.stdout.write(testo)
            sys.stdout.flush()
    return 0


def main(argomenti: list[str] | None = None) -> int:
    analizzatore = argparse.ArgumentParser(
        description="Registra una demo di terminale in formato asciinema v2.",
        epilog="Il comando da registrare va dopo `--`.",
    )
    analizzatore.add_argument("destinazione", help="file .cast da scrivere")
    analizzatore.add_argument("--titolo", default="", help="titolo della registrazione")
    analizzatore.add_argument("--righe", type=int, default=RIGHE)
    analizzatore.add_argument("--colonne", type=int, default=COLONNE)

    analizzatore.add_argument(
        "--riproduci", action="store_true", help="riproduce la registrazione invece di crearla"
    )
    analizzatore.add_argument("--velocita", type=float, default=1.0)
    # Il prefisso è un valore e non un predefinito nascosto: qui si dichiara che cosa
    # questo strumento è autorizzato a eseguire, e lo si legge nella riga di comando
    # che ha prodotto la registrazione. Un `--regia` senza argomento eseguirebbe ciò
    # che un comando registrato decide di stampare, e la riga non lo direbbe.
    analizzatore.add_argument(
        "--regia",
        metavar="PREFISSO",
        default=None,
        help="esegue le righe che cominciano così, e poi manda un Invio",
    )

    # La divisione su `--` si fa a mano invece che con `argparse.REMAINDER`, che
    # dopo il primo argomento posizionale inghiotte anche le opzioni di questo
    # programma: `--titolo` finirebbe nel comando da registrare. E la divisione vale
    # nei due versi: anche `--riproduci` si cerca **solo prima** di `--`, se no un
    # comando che ha per conto suo un'opzione con quel nome non si riesce a registrare.
    tutti = list(sys.argv[1:] if argomenti is None else argomenti)
    taglio = tutti.index("--") if "--" in tutti else len(tutti)
    miei, comando = tutti[:taglio], tutti[taglio + 1 :]

    if "--riproduci" in miei:
        letti = analizzatore.parse_args(miei)
        if comando:
            analizzatore.error("--riproduci non registra niente: togliere il comando dopo `--`")
        if letti.regia is not None:
            analizzatore.error(
                "--regia fa da seconda finestra mentre la scena gira: una "
                "riproduzione non ne ha una"
            )
        if letti.velocita <= 0:
            # Dividere per zero qui vuol dire un traceback al posto della riserva, il
            # giorno in cui la demo dal vivo è già fallita una volta.
            analizzatore.error("--velocita vuole un numero maggiore di zero")
        return riproduci(letti.destinazione, letti.velocita)

    if "--" not in tutti or not comando:
        analizzatore.error("manca il comando da registrare (dopo `--`)")
    letti = analizzatore.parse_args(miei)

    # Ctrl-C durante una registrazione deve fermare il comando, non lasciare un
    # .cast troncato senza che nessuno lo sappia.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    uscita = registra(
        letti.destinazione, comando, letti.titolo, letti.righe, letti.colonne, letti.regia
    )
    if not os.path.exists(letti.destinazione):
        return uscita

    durata = 0.0
    with open(letti.destinazione, encoding="utf-8") as file:
        file.readline()
        for riga in file:
            durata = json.loads(riga)[0]
    print(
        "registrato: %s · %.1f s · uscita %d" % (letti.destinazione, durata, uscita),
        file=sys.stderr,
    )
    return uscita


if __name__ == "__main__":
    raise SystemExit(main())
