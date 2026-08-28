# Punto d'ingresso unico del repository. `make` senza argomenti elenca i target.
# Le feature successive aggiungono i propri target `up-*` / `down-*` senza toccare questi.

.DEFAULT_GOAL := help
.PHONY: help docs-check tools-test images-pull images-verify preflight

# `FS` usa `.*` e non il `.*?` dell'idioma che gira in rete: `awk` parla ERE, dove il
# non-greedy non esiste, e POSIX dichiara indefinito il comportamento di due
# quantificatori adiacenti (XBD §9.4.6). Indefinito non vuol dire rotto — qui l'output
# delle due forme è identico byte per byte, misurato — vuol dire non garantito, ed è
# il motivo per cui la forma definita entra comunque: ADR-0029, fonti S-030 e S-031.
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
