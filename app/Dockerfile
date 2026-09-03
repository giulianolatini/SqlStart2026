# L'immagine di `mongolab`. Esiste per una ragione sola, ed è ADR-0012: dentro la rete
# Compose il client scopre i membri del replica set e parla con il primario, e quella
# scoperta è ciò che il talk mostra. Dall'host non funziona — i nomi che il set rimanda
# sono nomi di servizi Compose, che l'host non risolve (M-019).
#
# NON c'è la direttiva `# syntax=docker/dockerfile:1` in cima, e la sua assenza è una
# decisione. Quella riga fa scaricare al demone l'immagine del frontend BuildKit dal
# registro: una dipendenza di rete in più, non pinnata, in un repository il cui vincolo
# principale è costruire e girare senza rete (ADR-0009). La sintassi predefinita basta
# per tutto ciò che serve qui.

# Le due basi arrivano da fuori come argomenti, e arrivano **pinnate per digest** da
# tools/images.env. Scriverle qui come `python:3.13-slim` funzionerebbe e sarebbe la
# stessa promessa dei file Compose senza il digest: un tag mobile, che domani è un altro
# contenuto. Il valore lo passa `make app-image`, e `check_stack.py` verifica che ogni
# `FROM` di questo file sia pinnato e conosciuto (ADR-0093).
ARG PYTHON_IMAGE
ARG UV_IMAGE

# Primo stadio: serve solo a prendere il binario di `uv`. L'immagine ufficiale contiene
# `/uv` e nient'altro di utile, e copiarne un file solo costa meno che installare uv con
# pip dentro l'immagine finale — che vorrebbe dire una risoluzione di dipendenze in più,
# fatta in rete, per ottenere lo strumento che serve a non farne.
FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE}

COPY --from=uv /uv /usr/local/bin/uv

# `PYTHONDONTWRITEBYTECODE` non è igiene generica: il sorgente arriva da un bind mount
# dell'host, e senza questa riga il container ci scriverebbe dentro i propri
# `__pycache__` — file di un'altra architettura, di proprietà di un altro utente, in
# mezzo al codice di chi sviluppa. La stessa variabile ha già una storia in questo
# repository: al Task 6 due mutazioni della stessa dimensione scritte nello stesso
# secondo hanno condiviso il `.pyc` e una prova ha mentito (M-011).
#
# `PYTHONUNBUFFERED` riguarda la demo. Quando l'uscita non è un terminale — `make
# app-watch | tee`, o una registrazione con `tools/registra-terminale.py` — Python
# bufferizza a blocchi, e la cronaca del failover comparirebbe a scatti da 8 KiB invece
# che riga per riga. Il fatto da mostrare è *quando* le cose succedono: un buffer lo
# distrugge.
#
# `UV_PROJECT_ENVIRONMENT` sposta l'ambiente virtuale FUORI da /app, ed è ciò che rende
# possibile il bind mount del Passo 1: se stesse in /app/.venv, montare il sorgente
# dell'host sopra /app lo coprirebbe — o peggio, ci metterebbe sopra il `.venv` di macOS,
# che dentro Linux non è eseguibile.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/mongolab \
    UV_LINK_MODE=copy \
    PATH=/opt/mongolab/bin:$PATH

WORKDIR /app

# Prima il manifesto e il lock, poi il sorgente: sono due `COPY` invece di uno perché il
# primo cambia di rado e il secondo a ogni modifica. Con un `COPY . .` solo, ogni riga
# toccata in `cli.py` invaliderebbe il livello che installa pymongo, typer e rich — cioè
# l'unico che va in rete.
COPY pyproject.toml uv.lock ./
COPY src ./src

# `--frozen` è la riga che rende ripetibile la costruzione: uv usa `uv.lock` così com'è e
# **fallisce** se il lock non corrisponde a `pyproject.toml`, invece di risolvere di
# nuovo le versioni e installare in silenzio qualcosa di diverso da ciò che le prove
# hanno visto sull'host.
#
# `--no-dev` lascia fuori pytest e mypy: in questa immagine non si prova niente. Le due
# suite girano sull'host, dove hanno il repository intero e il socket Docker con cui
# accendono gli stack veri (ADR-0020).
#
# Il progetto stesso è installato **in modo modificabile**: è il comportamento
# predefinito di `uv sync` per la radice del progetto, e qui è ciò che serve, perché il
# collegamento punta a /app/src — lo stesso percorso su cui il bind mount monterà il
# sorgente dell'host. Modificare un file e rieseguire il comando basta: nessuna
# ricostruzione (§6.5 del design).
RUN uv sync --frozen --no-dev

# Utente non privilegiato. Non protegge un gran che — il container non pubblica porte e
# vive quanto un comando — ma questo file è materiale didattico prima che infrastruttura,
# e in sala si vedrà. L'ambiente sta in /opt/mongolab, di proprietà di root e leggibile da
# tutti: all'utente serve solo eseguirlo.
RUN useradd --create-home --uid 1000 mongolab
USER mongolab

# L'immagine **è** l'applicazione: `docker compose run --rm app stats --target rs` passa
# le tre parole finali come argomenti. Con `CMD` al posto di `ENTRYPOINT` la stessa riga
# avrebbe cercato un eseguibile di nome «stats».
ENTRYPOINT ["mongolab"]
CMD ["--help"]
