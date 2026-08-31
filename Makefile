# Punto d'ingresso unico del repository. `make` senza argomenti elenca i target.
# Le feature successive aggiungono i propri target `up-*` / `down-*` senza toccare questi.

.DEFAULT_GOAL := help
.PHONY: help docs-check tools-test images-pull images-verify preflight stack-check \
        up-01 down-01 reset-01 logs-01 seed-01 smoke-01

# `--env-file tools/images.env` porta MONGO_IMAGE, che nei file Compose è dichiarato
# nella forma `${MONGO_IMAGE:?...}`: senza, Compose si ferma subito dicendo cosa manca
# invece di avviare un container con un'immagine vuota.
COMPOSE_01 := docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml
STACK_01   := docker/01-standalone/compose.yaml
STACK_02   := docker/02-replicaset/compose.yaml

# `FS` usa `.*` e non il `.*?` dell'idioma che gira in rete: `awk` parla ERE, dove il
# non-greedy non esiste, e POSIX dichiara indefinito il comportamento di due
# quantificatori adiacenti (XBD §9.4.6). Indefinito non vuol dire rotto — qui l'output
# delle due forme è identico byte per byte, misurato — vuol dire non garantito, ed è
# il motivo per cui la forma definita entra comunque: ADR-0029, fonti S-030 e S-031.
help: ## Elenca i target disponibili
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

tools-test: ## Esegue la suite degli strumenti di repository
	uv run --directory tools pytest -q

docs-check: ## Verifica il legame fra ADR e fonti, e i collegamenti fra le pagine
	uv run --project tools python tools/check_citations.py docs/Decision.md docs/Sources.md
	uv run --project tools python tools/check_links.py docs README.md

images-pull: ## Scarica le immagini e le pinna per digest (richiede rete)
	./tools/pull-images.sh --pull

images-verify: ## Verifica che le immagini pinnate siano presenti in locale (offline)
	./tools/pull-images.sh --verify

preflight: ## Controlli della mattina del talk
	./tools/preflight.sh

# `--variabile` non è una scorciatoia: lo stack 02 dichiara la password nella forma
# `${PASSWORD_AMMINISTRATORE:?...}`, e il file che la porta è fuori dal repository per
# scelta (ADR-0014). Su un clone appena fatto quel file non esiste, e senza un valore
# qui il controllo si fermerebbe prima di guardare una sola regola. Il valore che segue
# non è una password: dice a voce alta di essere finto, e non raggiunge mai un mongod
# perché `check_stack.py` legge i file e non avvia niente (ADR-0042).
stack-check: ## Verifica i file Compose contro le decisioni degli ADR
	uv run --project tools python tools/check_stack.py \
		--variabile PASSWORD_AMMINISTRATORE=valore-finto-il-controllo-non-si-collega \
		$(STACK_01) $(STACK_02)

# --- Stack 01 — istanza singola -------------------------------------------------------

# `--wait` restituisce il controllo solo a container sano, non appena avviato: senza,
# il comando successivo troverebbe un mongod che non accetta ancora connessioni.
up-01: ## Avvia lo stack 01 (istanza singola) e attende che sia sano
	$(COMPOSE_01) up -d --wait

# Conserva il volume. Per ripartire da zero serve `reset-01`, ed è deliberato che siano
# due comandi diversi: cancellare i dati non deve essere l'effetto collaterale di uno
# «spegni».
down-01: ## Ferma lo stack 01 conservando i dati
	$(COMPOSE_01) down

# L'unico modo di far rieseguire il seed all'entrypoint è togliergli il volume: gli
# script di /docker-entrypoint-initdb.d partono solo su un volume non inizializzato, e
# quando non partono non lo dicono (V-014).
reset-01: ## Ferma lo stack 01 e CANCELLA il volume: il seed ripartirà da zero
	$(COMPOSE_01) down -v

logs-01: ## Segue i log dello stack 01
	$(COMPOSE_01) logs -f

# La seconda strada per caricare i dati, su uno stack già in piedi e senza perdere il
# volume (ADR-0031). Lo script è lo stesso che esegue l'entrypoint, montato in sola
# lettura: una sorgente sola, due modi di eseguirla.
seed-01: ## Ricarica i dati di demo su uno stack 01 già avviato
	$(COMPOSE_01) exec -T mongo-standalone \
		mongosh --quiet --file /docker-entrypoint-initdb.d/10-dati-demo.js

smoke-01: ## Prova end-to-end dello stack 01 avviato
	./tools/smoke-standalone.sh
