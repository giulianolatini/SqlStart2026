# Punto d'ingresso unico del repository. `make` senza argomenti elenca i target.
# Le feature successive aggiungono i propri target `up-*` / `down-*` senza toccare questi.

.DEFAULT_GOAL := help
.PHONY: help docs-check tools-test images-pull images-verify preflight

# `FS` usa `.*` e non il `.*?` dell'idioma che gira in rete. POSIX: «The awk utility
# shall make use of the extended regular expression notation», e negli ERE il
# non-greedy non esiste — quella `?` è solo un secondo quantificatore attaccato al
# primo, di cui «The behavior of multiple adjacent duplication symbols ('+', '*', '?',
# and intervals) produces undefined results» (XBD §9.4.6).
#   https://pubs.opengroup.org/onlinepubs/9699919799/utilities/awk.html
#   https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap09.html
# In pratica qui non cambia niente, ed è stato misurato: nessuna descrizione contiene
# un secondo `## `, e l'output delle due forme è identico byte per byte. Ma `help` è
# anche il target predefinito, e non vale la pena farlo poggiare su un costrutto che
# lo standard dichiara indefinito quando la forma definita costa un carattere in meno.
help: ## Elenca i target disponibili
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

tools-test: ## Esegue la suite degli strumenti di repository
	uv run --directory tools pytest -q

docs-check: ## Verifica il legame fra ADR e fonti
	uv run --project tools python tools/check_citations.py docs/Decision.md docs/Sources.md

images-pull: ## Scarica le immagini e le pinna per digest (richiede rete)
	./tools/pull-images.sh --pull

images-verify: ## Verifica che le immagini pinnate siano presenti in locale (offline)
	./tools/pull-images.sh --verify

preflight: ## Controlli della mattina del talk
	./tools/preflight.sh
