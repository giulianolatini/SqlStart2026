# Punto d'ingresso unico del repository. `make` senza argomenti elenca i target.
# Le feature successive aggiungono i propri target `up-*` / `down-*` senza toccare questi.

.DEFAULT_GOAL := help
.PHONY: help docs-check tools-test images-pull images-verify preflight stack-check \
        app-test app-check app-test-integration \
        app-stats app-watch app-workload \
        up-01 down-01 reset-01 logs-01 seed-01 smoke-01 reset-demo-01 \
        up-02 down-02 reset-02 logs-02 seed-02 smoke-02 reset-demo-02 \
        failover-02 failover-02-termina failover-02-maggioranza \
        up-03 down-03 reset-03 logs-03 seed-03 smoke-03 reset-demo-03 profilo-03 \
        stato-03 distribuzione-03 guasto-03

# `--env-file tools/images.env` porta MONGO_IMAGE, che nei file Compose è dichiarato
# nella forma `${MONGO_IMAGE:?...}`: senza, Compose si ferma subito dicendo cosa manca
# invece di avviare un container con un'immagine vuota.
COMPOSE_01 := docker compose --env-file tools/images.env -f docker/01-standalone/compose.yaml
STACK_01   := docker/01-standalone/compose.yaml
STACK_02   := docker/02-replicaset/compose.yaml
STACK_03   := docker/03-sharded/compose.yaml

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

# --- L'applicazione -------------------------------------------------------------------
#
# Due suite e due target, non uno: `app-test` non tocca Docker e finisce in un paio di
# secondi, `app-test-integration` accende uno stack e ci mette minuti. Tenerle insieme
# significherebbe che la suite veloce smette di essere veloce, e una suite che costa un
# minuto non si esegue prima di ogni commit — cioè smette di proteggere proprio nella
# fase in cui il TDD serve. La separazione è il §7 del design, letto insieme ad ADR-0020.

app-test: ## Esegue la suite unitaria dell'applicazione (senza Docker)
	uv run --directory app pytest -q

app-check: ## Verifica i tipi dell'applicazione con mypy --strict
	uv run --directory app mypy

# Dal Task 8 questo target è vero: accende gli stack che le prove chiedono — con questi
# stessi `up-01`, `up-02`, `up-03`, non con un facsimile (ADR-0020) — e ci gira contro.
# Non li spegne alla fine: fermare uno stack che l'operatore aveva già su sarebbe un
# effetto che le prove non hanno causato. Ciò che smontano sono i **dati**, e lo fanno
# con un database usa-e-getta per prova.
#
# Il ramo che traduceva l'uscita 5 di pytest — «non ho raccolto niente» — non serve più e
# non va rimesso: adesso un 5 vorrebbe dire che le prove sono sparite, ed è una notizia.
app-test-integration: ## Esegue la suite di integrazione dell'applicazione (accende gli stack; richiede Docker)
	uv run --directory app pytest -q tests/integration

# --- L'applicazione, eseguita ---------------------------------------------------------
#
# Tre target che non aggiungono niente alla riga di comando: la scrivono. Il §6.4 del
# design dice `mongolab stats --target rs`, e questi target sono quella riga più il
# `uv run --directory app` che serve a trovarla senza attivare a mano un virtualenv.
#
# `TARGET` non ha un valore predefinito, e la mancanza è deliberata. La CLI rifiuta di
# indovinare quale dei tre stack intendevi — un `--target` sbagliato si ferma prima di
# aprire un socket — e un `TARGET ?= rs` qui reintrodurrebbe dal Makefile esattamente
# l'assunzione implicita che la CLI si rifiuta di fare. Il messaggio elenca i tre nomi,
# perché un errore che dice solo «manca» costringe a cercare altrove ciò che serve.
#
# L'uscita è 2, la stessa con cui Typer respinge un parametro sbagliato: dal punto di
# vista di chi legge un CI, sbagliare la riga di `make` e sbagliare la riga di `mongolab`
# sono lo stesso errore, e meritano lo stesso codice.
CHIEDI_TARGET = @[ -n "$(TARGET)" ] || { echo "manca TARGET: make $@ TARGET=rs (standalone, rs, sharded)" >&2; exit 2; }

# `ARGS` è la valvola: `--sink plain`, `--writers 16`, `--duration 30` passano di lì senza
# che il Makefile debba conoscerli. Un target per opzione invecchierebbe a ogni opzione
# nuova, e il posto in cui le opzioni sono dichiarate è già uno solo, `cli.py`.
app-stats: ## Fotografa uno stack: make app-stats TARGET=rs
	$(CHIEDI_TARGET)
	uv run --directory app mongolab stats --target $(TARGET) $(ARGS)

app-watch: ## Guarda la topologia cambiare: make app-watch TARGET=rs
	$(CHIEDI_TARGET)
	uv run --directory app mongolab watch --target $(TARGET) $(ARGS)

app-workload: ## Manda carico contro uno stack: make app-workload TARGET=rs
	$(CHIEDI_TARGET)
	uv run --directory app mongolab workload --target $(TARGET) $(ARGS)

docs-check: ## Verifica il legame fra ADR e fonti, e i collegamenti fra le pagine
	uv run --project tools python tools/check_citations.py docs/Decision.md docs/Sources.md
	uv run --project tools python tools/check_links.py docs app/docs README.md

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
		$(STACK_01) $(STACK_02) $(STACK_03)

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
#
# La seconda riga NON si toglie per semplificare, e il motivo per cui regge non è la
# fortuna. `compose wait` vuole un container vivo cui attaccarsi: su uno già finito
# risponde «no containers for project» e esce 1, cioè fallirebbe un avvio riuscito. Qui
# non capita perché rs-init è l'ULTIMO anello e non ha healthcheck: `up --wait` torna
# nell'istante in cui rs-init *comincia*, e la finestra a disposizione del secondo comando
# è l'intera durata del suo lavoro — 21,6 s a freddo e 3,9 s a caldo, misurati su tre giri
# ciascuno (V-069, che chiude il debito aperto da ADR-0062). Si chiuderebbe solo se
# rs-init smettesse di fare qualcosa: chi lo svuota deve togliere anche questa riga.
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

# --- Stack 03 — sharded cluster a due profili -----------------------------------------

# UN bersaglio per profilo sarebbe stato due famiglie di comandi: `up-03-palco`,
# `up-03-completo`, e così per gli altri sei. Il profilo è una VARIABILE, così `down`,
# `logs` e `reset` guardano per forza lo stesso insieme che `up` ha acceso — con due
# famiglie sarebbe bastato sbagliare suffisso una volta per fermare metà cluster.
#
#   make up-03                    undici servizi, il profilo del palco
#   make up-03 PROFILO=completo   diciotto, tre membri per componente
#
# Il valore predefinito è quello che deve partire su qualunque macchina: il `completo`
# vuole 12 GiB assegnati alla VM Docker (ADR-0025) e su un portatile da 8 non parte.
PROFILO ?= palco

# La forma senza `--profile`, che serve a due cose: comporre le altre due senza ripetere
# tre righe identiche, e interrogare il file Compose su quali profili dichiari — domanda
# che non ha senso porre già filtrando per uno di essi.
COMPOSE_03_BASE := docker compose --env-file tools/images.env --env-file docker/03-sharded/.env \
              -f docker/03-sharded/compose.yaml

COMPOSE_03 := $(COMPOSE_03_BASE) --profile $(PROFILO)

# DUE forme del comando, e la seconda non è una comodità: è una correzione a un difetto
# misurato. `down` agisce solo sui servizi dei profili ATTIVI, quindi `--profile palco
# down` dopo un avvio in `completo` toglie gli undici del palco, lascia i sette in piedi
# e nemmeno riesce a togliere la rete — «resource is still in use» — senza che il codice
# di uscita se ne accorga (V-059). Chi spegne dopo una prova generale si ritroverebbe
# mezzo cluster acceso e nessun avviso.
#
# `--profile "*"` accende tutti i profili insieme, ed è la forma documentata per dire
# «tutti» (S-068). Si spegne e si guardano i log SEMPRE così, perché al momento di
# spegnere non si sa con quale profilo qualcun altro ha acceso.
COMPOSE_03_OGNI := $(COMPOSE_03_BASE) --profile "*"

AMBIENTE_03 := docker/03-sharded/.env

# Nove volumi dei dati, uno per mongod, più `keyfile` che NON è in questa lista: vale
# qui la stessa ragione dello stack 02, cioè che rigenerarlo significa un segreto nuovo.
# `addprefix` invece di nove nomi scritti a mano perché nove nomi scritti a mano sono
# nove occasioni di scriverne uno sbagliato, e un volume mancato da `reset-03` non dà
# errore: dà dati vecchi al giro dopo, che è molto peggio.
PROGETTO_03 := sqlstart-03-sharded
DATI_03 := $(addprefix $(PROGETTO_03)_dati-, \
             cfg1 cfg2 cfg3 shard1a shard1b shard1c shard2a shard2b shard2c)

# Stessa regola su file dello stack 02, stesso motivo: se il `.env` manca ci si ferma
# qui con una frase che dice cosa fare (ADR-0014), invece di lasciare a Compose un «env
# file not found» che non spiega perché quel file non è nel repository.
$(AMBIENTE_03):
	@printf 'Manca %s.\n' "$(AMBIENTE_03)" >&2
	@printf 'Contiene la password dell'"'"'amministratore e sta fuori dal repository apposta.\n' >&2
	@printf 'Crearlo con: cp %s.example %s, poi riempire PASSWORD_AMMINISTRATORE.\n' \
		"$(AMBIENTE_03)" "$(AMBIENTE_03)" >&2
	@exit 1

# Il guardiano di `PROFILO`, e nasce da una misura, non da uno scrupolo. Compose accetta
# qualunque stringa dopo `--profile`: se non corrisponde a niente non protesta, seleziona
# i soli servizi che non dichiarano `profiles:` — qui uno solo, `keyfile-init` — e
# `up -d --wait` muore dicendo «container sh-keyfile-init exited (0)». Cioè accusa il
# one-shot di aver fatto esattamente il suo mestiere, e la parola «profilo» non compare in
# nessuna delle cinque righe stampate (V-069). Un refuso in `PROFILO=complteo` manda a
# leggere i log del keyfile.
#
# L'elenco dei profili validi NON si scrive qui. `config --profiles` lo chiede al file
# Compose, che è l'unico posto dove quell'elenco è vero: un profilo nuovo nel file diventa
# valido qui senza che nessuno si ricordi di aggiornare il Makefile, ed è la stessa ragione
# per cui `DATI_03` si costruisce con `addprefix` invece che con nove nomi a mano.
profilo-03: $(AMBIENTE_03)
	@$(COMPOSE_03_BASE) config --profiles | grep -qx '$(PROFILO)' || { \
		printf 'PROFILO=%s non è un profilo di docker/03-sharded/compose.yaml.\n' \
			'$(PROFILO)' >&2; \
		printf 'Quelli dichiarati sono: %s\n' \
			"$$($(COMPOSE_03_BASE) config --profiles | tr '\n' ' ')" >&2; \
		printf 'Senza questo controllo Compose non protesta: sceglie i soli servizi senza\n' >&2; \
		printf 'profilo e l'"'"'avvio muore accusando il keyfile (V-069).\n' >&2; \
		exit 1; }

# UN comando, non i due di `up-02`, ed è la differenza che ADR-0062 ha reso possibile.
# Lo stack 02 ha bisogno del secondo perché `up --wait` gli torna quattordici secondi
# prima che la replica esista (V-025). Qui l'ultimo anello della catena è la sentinella
# `up-03`, che `--wait` aspetta come qualunque altro servizio: quando il comando torna,
# i due shard sono registrati e `lab.ordini` è distribuita e piena.
#
# Aggiungerne un secondo per simmetria sarebbe peggio che inutile: `compose wait` su un
# one-shot che ha già finito risponde «no containers for project» e esce 1, cioè
# trasformerebbe un avvio riuscito in un errore.
up-03: $(AMBIENTE_03) profilo-03 ## Avvia lo stack 03 (sharded, PROFILO=palco|completo) e attende il cluster
	$(COMPOSE_03) up -d --wait

down-03: $(AMBIENTE_03) ## Ferma lo stack 03 conservando i dati e il keyfile
	$(COMPOSE_03_OGNI) down

reset-03: $(AMBIENTE_03) ## Ferma lo stack 03 e CANCELLA i dati, conservando il keyfile
	$(COMPOSE_03_OGNI) down
	docker volume rm --force $(DATI_03)

logs-03: $(AMBIENTE_03) ## Segue i log dello stack 03
	$(COMPOSE_03_OGNI) logs -f

# Rilancia lo STESSO servizio che semina all'avvio, con `RICARICA=1` che gli dice di
# ricaricare anche se i ventimila documenti ci sono già. La collezione resta distribuita:
# `30-dati-demo.js` chiama `sh.shardCollection()` prima di riempire e la trova già fatta,
# che è idempotente per costruzione. La password non compare qui perché sta già
# nell'ambiente del servizio.
seed-03: $(AMBIENTE_03) profilo-03 ## Ricarica i dati di demo su uno stack 03 già avviato
	$(COMPOSE_03) run --rm -e RICARICA=1 seed

# Il profilo arriva allo smoke per ambiente e non per argomento, perché è la stessa
# variabile che sceglie i servizi: passarla due volte in due modi diversi è il modo di
# ritrovarsi a provare `palco` su un cluster avviato in `completo`.
smoke-03: profilo-03 ## Prova end-to-end dello stack 03 avviato (PROFILO=palco|completo)
	PROFILO=$(PROFILO) ./tools/smoke-sharded.sh

reset-demo-03: profilo-03 ## Riporta lo stack 03 allo stato di partenza senza ricostruirlo
	PROFILO=$(PROFILO) ./tools/reset-demo.sh 03

# --- Le tre scene del Blocco 3 ---------------------------------------------------------
#
# Esistono come bersagli, e non come due righe di `docker exec` da copiare dalla
# documentazione, per la ragione delle scene dello stack 02: le registrazioni di riserva
# si girano registrando un comando (ADR-0050), e la registrazione di un comando che
# nessuno può rieseguire non è una riserva. La seconda ragione è che la password sta in
# `.env` e non deve comparire a schermo mentre si registra (ADR-0014, ADR-0054).
#
# Tre e non una: `sh.status()` mostra la struttura e la si guarda una volta; la
# distribuzione mostra l'unica cosa che distingue un cluster che partiziona da uno che
# ha messo tutto su un nodo, e si guarda ogni volta che si tocca la chiave; il guasto
# mostra che cosa resta quando uno shard se ne va, ed è l'unica delle tre che il pubblico
# non può dedurre dalle altre due.
stato-03: profilo-03 ## Mostra il cluster 03 come si presenta: sh.status() e le righe che contano
	PROFILO=$(PROFILO) ./tools/demo-sharded.sh stato

distribuzione-03: profilo-03 ## Mostra dove stanno davvero i documenti di lab.ordini, shard per shard
	PROFILO=$(PROFILO) ./tools/demo-sharded.sh distribuzione

# L'unica delle tre che TOCCA il cluster: ferma un container e lo riaccende, e alla fine
# lo stack è come l'ha trovato. In `palco` non c'è nessuna elezione da fare e la scena
# dura una quarantina di secondi, quasi tutti spesi ad aspettare che il router si arrenda;
# in `completo` finisce con un'elezione. Non è `failover-03` perché nel profilo del talk
# un failover non può avvenire, e chiamarlo così prometterebbe quello che non fa.
guasto-03: profilo-03 ## Ferma il primario di uno shard 03 e misura che cosa risponde ancora (~40 s)
	PROFILO=$(PROFILO) ./tools/demo-sharded.sh guasto
