# Punto d'ingresso unico del repository. `make` senza argomenti elenca i target.
# Le feature successive aggiungono i propri target `up-*` / `down-*` senza toccare questi.

.DEFAULT_GOAL := help
.PHONY: help docs-check tools-test images-pull images-verify preflight stack-check \
        up-01 down-01 reset-01 logs-01 seed-01 smoke-01 reset-demo-01 \
        up-02 down-02 reset-02 logs-02 seed-02 smoke-02 reset-demo-02 \
        failover-02 failover-02-termina failover-02-maggioranza

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

# Diverso da `reset-01`: quello ferma lo stack e cancella il volume, questo lavora sui
# container in piedi. Serve in prova generale, quando la stessa scena si ripete tre
# volte e ricostruire da zero ogni volta costa mezzo minuto a giro.
reset-demo-01: ## Riporta lo stack 01 allo stato di partenza senza ricostruirlo
	./tools/reset-demo.sh 01

# --- Stack 02 — replica set a tre membri ----------------------------------------------

# DUE `--env-file`, e il secondo non è ridondante: la flag non aggiunge un file, prende
# il posto del `.env` implicito. Passandone uno solo, il `.env` che sta accanto al file
# indicato con `-f` NON viene letto benché sia lì accanto (S-056, misurato in V-025).
COMPOSE_02 := docker compose --env-file tools/images.env --env-file docker/02-replicaset/.env -f docker/02-replicaset/compose.yaml
AMBIENTE_02 := docker/02-replicaset/.env

# I volumi dei dati, uno per membro. Il nome vero è il nome del progetto Compose
# (`name:` in cima al file) più quello dichiarato in `volumes:`.
PROGETTO_02 := sqlstart-02-replicaset
DATI_02 := $(PROGETTO_02)_dati-1 $(PROGETTO_02)_dati-2 $(PROGETTO_02)_dati-3

# Regola su un FILE, non su un target fittizio: se il file esiste, make la considera
# soddisfatta e non esegue niente. Se manca, si ferma qui con una frase che dice cosa
# fare, invece di lasciare a Compose un «env file not found» che non spiega perché quel
# file non è nel repository (ADR-0014).
$(AMBIENTE_02):
	@printf 'Manca %s.\n' "$(AMBIENTE_02)" >&2
	@printf 'Contiene la password dell'\''amministratore e sta fuori dal repository apposta.\n' >&2
	@printf 'Crearlo con: cp %s.example %s, poi riempire PASSWORD_AMMINISTRATORE.\n' \
		"$(AMBIENTE_02)" "$(AMBIENTE_02)" >&2
	@exit 1

# DUE comandi, non uno, ed è la decisione di ADR-0041. `up --wait` attende che i servizi
# siano «running|healthy»: rs-init non ha healthcheck perché deve morire, quindi per
# `--wait` è a posto nell'istante in cui parte, e il comando esce 0 quattordici secondi
# prima che il replica set esista (V-025). Il verdetto è il secondo comando, che blocca
# fino a che rs-init si ferma e ne restituisce il codice di uscita.
up-02: $(AMBIENTE_02) ## Avvia lo stack 02 (replica set) e attende che la replica esista
	$(COMPOSE_02) up -d --wait
	$(COMPOSE_02) wait rs-init

down-02: $(AMBIENTE_02) ## Ferma lo stack 02 conservando i dati e il keyfile
	$(COMPOSE_02) down

# `down -v` NON va bene qui, e la differenza è tutta in una parola: cancellerebbe anche
# il volume del keyfile. Rigenerarlo significa un segreto nuovo, quindi tre membri che
# non si riconoscono più fra loro finché non ripartono tutti insieme — un giro in più
# per niente, visto che si voleva solo azzerare i dati. Si tolgono i tre volumi dei dati
# per nome, e il keyfile resta.
reset-02: $(AMBIENTE_02) ## Ferma lo stack 02 e CANCELLA i dati, conservando il keyfile
	$(COMPOSE_02) down
	docker volume rm --force $(DATI_02)

logs-02: $(AMBIENTE_02) ## Segue i log dello stack 02
	$(COMPOSE_02) logs -f

# Rilancia lo STESSO servizio che ha seminato all'avvio, con `RICARICA=1` che gli dice di
# ricaricare anche se i dati ci sono già. Non è una scorciatoia: rs-init è idempotente
# per costruzione — trova la replica formata e non la reinizializza, trova
# l'amministratore e non lo ricrea — quindi rieseguirlo è sicuro, e mostra quell'
# idempotenza invece di raccontarla. È anche il motivo per cui la password non compare
# in questa riga: sta già nell'ambiente del servizio.
seed-02: $(AMBIENTE_02) ## Ricarica i dati di demo su uno stack 02 già avviato
	$(COMPOSE_02) run --rm -e RICARICA=1 rs-init

smoke-02: ## Prova end-to-end dello stack 02 avviato
	./tools/smoke-replicaset.sh

reset-demo-02: ## Riporta lo stack 02 allo stato di partenza senza ricostruirlo
	./tools/reset-demo.sh 02

# --- Le tre scene di failover ----------------------------------------------------------
#
# Sono TRE bersagli perché sono tre fenomeni diversi, e tenerli in uno solo con una
# variabile invita a mostrarne uno soltanto. `docker kill` è quello che il pubblico si
# aspetta e costa ~10 s di elezione perché nessuno ha avvisato nessuno; lo `shutdown`
# costa ~0,5 s ed è l'unico dei due in cui `restart: unless-stopped` interviene
# davvero. La differenza è la scena (ADR-0034, ADR-0044, misure in V-029).
#
# La terza non è una variante delle prime due: quelle mostrano un set che si ripara, e
# lasciano credere che un replica set regga «ai guasti», senza dire quanti. Fermandone
# due su tre il superstite resta vivo e sano e passa comunque in sola lettura dopo ~9 s.
# È l'unica scena che spiega perché i membri sono tre (ADR-0045, misure in V-031).
failover-02: ## Demo di failover: SPEGNE il primario con docker kill (~10 s di elezione)
	./tools/failover-replicaset.sh spegni

failover-02-termina: ## Demo di failover: il primario esce da sé (~0,5 s, e il container torna su)
	./tools/failover-replicaset.sh termina

failover-02-maggioranza: ## Demo: due membri su tre giù, il superstite va in sola lettura (~9 s)
	./tools/failover-replicaset.sh maggioranza
