#!/usr/bin/env bash
# Banco di prova di revisione.sh.
#
# I tre programmi esterni sono finti, e devono esserlo: la suite non ha rete,
# non spende token, e soprattutto non manda niente a nessuno. Una suite che per
# provare l'invio invia davvero e' esattamente il difetto che questo script
# esiste per impedire.
#
# Le cose che possono davvero andare storte, e che le prove sorvegliano:
#   - inviare senza che nessuno l'abbia chiesto,
#   - inviare un dossier che contiene una credenziale,
#   - accendere l'allarme segreti su un documento che nomina le credenziali
#     senza scriverle - cioe' INSTALL-ENV.md,
#   - scambiare "il revisore non ha risposto" per "non ha trovato niente",
#   - archiviare un triage a meta' facendolo sembrare completo.

set -uo pipefail

SK="$(cd "$(dirname "$0")/.." && pwd)"
RV="$SK/scripts/revisione.sh"
BANCO="$(mktemp -d)"

ripulisci () {
  cd /
  rm -rf "$BANCO" 2>/dev/null || rm -rf "$BANCO" 2>/dev/null
  [ -d "$BANCO" ] && printf "\nnota: %s non è stata rimossa del tutto (non è un fallimento delle prove).\n" "$BANCO"
  return 0
}
trap ripulisci EXIT
PASSATI=0; FALLITI=0

ok ()   { PASSATI=$((PASSATI+1)); printf '  ok   %s\n' "$1"; }
ko ()   { FALLITI=$((FALLITI+1)); printf '  KO   %s\n' "$1"; }
caso () { printf '\n== %s\n' "$1"; }

prova ()    { local d="$1"; shift; if "$@"; then ok "$d"; else ko "$d"; fi; }
prova_no () { local d="$1"; shift; if "$@"; then ko "$d"; else ok "$d"; fi; }
muto ()     { "$@" >/dev/null 2>&1; }
contiene () { case "$1" in *"$2"*) return 0 ;; *) return 1 ;; esac; }

R="$BANCO/repo"
FINTI="$BANCO/finti"
mkdir -p "$FINTI"

# ------------------------------------------------------- i tre programmi -----

# gh finto: risponde con la PR che gli mettiamo davanti, non con una vera.
cat > "$FINTI/gh" <<'FINTO'
#!/usr/bin/env bash
case "$1 $2" in
  "pr view") cat "$FINTO_META" ;;
  "pr diff") cat "$FINTO_DIFF" ;;
  *) exit 1 ;;
esac
FINTO

# agy finto: risponde con un JSON pulito, come chiede lo schema.
cat > "$FINTI/agy" <<'FINTO'
#!/usr/bin/env bash
printf '%s\n' "$FINTA_RISPOSTA_AGY"
FINTO

# codex finto: risponde con lo stesso JSON dentro un recinto markdown, che e'
# il modo piu' comune in cui un modello disubbidisce a uno schema.
cat > "$FINTI/codex" <<'FINTO'
#!/usr/bin/env bash
cat >/dev/null
printf 'Ecco la revisione:\n\n```json\n%s\n```\n' "$FINTA_RISPOSTA_CODEX"
FINTO

chmod +x "$FINTI/gh" "$FINTI/agy" "$FINTI/codex"

export REVISIONE_GH="$FINTI/gh"
export REVISIONE_AGY="$FINTI/agy"
export REVISIONE_CODEX="$FINTI/codex"

export FINTO_META="$BANCO/meta.json"
export FINTO_DIFF="$BANCO/diff.patch"

cat > "$FINTO_META" <<'META'
{
  "number": 7,
  "title": "aggiunge la scansione ad alfa",
  "author": { "login": "giuliano" },
  "baseRefName": "develop",
  "headRefName": "feature/alfa",
  "state": "OPEN",
  "url": "https://example.invalid/pr/7",
  "body": "Chiude il primo step di alfa.",
  "commits": [
    { "oid": "aaaaaaaaaaaaaaaa", "messageHeadline": "feat(alfa): aggiunge la scansione", "messageBody": "Serviva per il collaudo." },
    { "oid": "bbbbbbbbbbbbbbbb", "messageHeadline": "docs(alfa): riscrive la presentazione", "messageBody": "" }
  ],
  "files": [ { "path": "alfa/alfa.sh", "additions": 12, "deletions": 3 } ]
}
META

cat > "$FINTO_DIFF" <<'DIFF'
diff --git a/alfa/alfa.sh b/alfa/alfa.sh
--- a/alfa/alfa.sh
+++ b/alfa/alfa.sh
@@ -1,2 +1,3 @@
 #!/bin/sh
+echo "scansione in corso"
DIFF

# Il $ dentro l'evidenza deve restare letterale: e' la citazione di uno script
# che il revisore accusa di non quotare una variabile. Espanderlo la
# cancellerebbe, e la prova che l'evidenza arriva intatta non proverebbe piu'
# niente.
# shellcheck disable=SC2016
export FINTA_RISPOSTA_AGY='{"rilievi":[{"titolo":"variabile non quotata","categoria":"security","gravita":"alta","confidenza":"alta","dove":"alfa/alfa.sh:2","evidenza":"echo $x","perche":"word splitting","rimedio":"quotare","controllo_iso":"A.8.28"}]}'
# shellcheck disable=SC2016
export FINTA_RISPOSTA_CODEX='{"rilievi":[{"titolo":"variabile non quotata nello script","categoria":"security","gravita":"alta","confidenza":"media","dove":"alfa/alfa.sh:2","evidenza":"echo $x","perche":"idem","rimedio":"quotare","controllo_iso":""},{"titolo":"il messaggio promette meno del diff","categoria":"congruita-commit","gravita":"bassa","confidenza":"bassa","dove":"aaaaaaaa","evidenza":"feat(alfa): aggiunge la scansione","perche":"tocca anche altro","rimedio":"riscrivere","controllo_iso":""}]}'

# ------------------------------------------------------------- il repo ------

git init -q -b develop "$R"
git -C "$R" config user.email banco@prova
git -C "$R" config user.name Banco
git -C "$R" config gc.auto 0
git -C "$R" config maintenance.auto false
mkdir -p "$R/alfa"
echo '#!/bin/sh' > "$R/alfa/alfa.sh"
git -C "$R" add alfa/alfa.sh
git -C "$R" commit -qm "feat(alfa): primo abbozzo"

cd "$R" || exit 1
LAV="$R/.revisioni/pr-7"

# ------------------------------------------------------------- 1. dossier ---

caso "1. dossier: mette la PR in un file solo"
prova "esce senza errore"        muto "$RV" dossier 7
prova "crea il dossier"          test -f "$LAV/dossier.md"
d="$(cat "$LAV/dossier.md")"
prova "intesta con numero e titolo" contiene "$d" "# Dossier della PR #7 — aggiunge la scansione ad alfa"
prova "porta i commit"              contiene "$d" "feat(alfa): aggiunge la scansione"
prova "porta i corpi dei commit"    contiene "$d" "Serviva per il collaudo."
prova "porta il diff"               contiene "$d" "+echo \"scansione in corso\""
prova "dice da dove parte la PR"    contiene "$d" 'feature/alfa'

# ------------------------------------------------------------- 2. segreti ---

caso "2. segreti: distingue il valore dal nome"
prova "dossier pulito: esce 0" muto "$RV" segreti 7

cp "$LAV/dossier.md" "$BANCO/pulito.md"
printf '\n+PERPLEXITY_API_KEY sta in ~/.claude/settings.json e va revocata per prima.\n' >> "$LAV/dossier.md"
prova "il NOME di una credenziale non fa scattare l'allarme" muto "$RV" segreti 7

cp "$BANCO/pulito.md" "$LAV/dossier.md"
printf '\n+PERPLEXITY_API_KEY=pplx-4f9b2c7d1e8a6b3f5c0d9e2a7b4c1f8e\n' >> "$LAV/dossier.md"
prova_no "il VALORE di una credenziale ferma tutto" muto "$RV" segreti 7

u="$("$RV" segreti 7 2>&1)"
prova    "dice dove guardare"                contiene "$u" "dossier.md"
prova_no "e NON ristampa la chiave intera"   contiene "$u" "pplx-4f9b2c7d1e8a6b3f5c0d9e2a7b4c1f8e"

caso "3. segreti: le altre forme che contano"
cp "$BANCO/pulito.md" "$LAV/dossier.md"
printf '\n+-----BEGIN OPENSSH PRIVATE KEY-----\n' >> "$LAV/dossier.md"
prova_no "una chiave privata"                    muto "$RV" segreti 7
cp "$BANCO/pulito.md" "$LAV/dossier.md"
printf '\n+curl https://utente:segretissimo@interno.example/x\n' >> "$LAV/dossier.md"
prova_no "una credenziale dentro un URL"         muto "$RV" segreti 7
cp "$BANCO/pulito.md" "$LAV/dossier.md"
# Anche qui il $ e' il punto della prova: la riga deve arrivare al setaccio
# come rimando a una variabile, non come il suo valore.
# shellcheck disable=SC2016
printf '\n+password: ${PASSWORD_DI_PROVA}\n' >> "$LAV/dossier.md"
prova    "un rimando a variabile d'\''ambiente no" muto "$RV" segreti 7

cp "$BANCO/pulito.md" "$LAV/dossier.md"

# ----------------------------------------------------------- 4. interroga ---

caso "4. interroga: senza --invia non esce niente"
u="$("$RV" interroga 7 2>&1)"
prova    "lo dice a chiare lettere"     contiene "$u" "PROVA A VUOTO"
prova    "nomina i due destinatari"     contiene "$u" "Google"
prova    "e l'altro"                    contiene "$u" "OpenAI"
prova    "scrive il testo che uscirebbe" test -f "$LAV/prompt.txt"
prova_no "NON ha interrogato Gemini"    test -f "$LAV/gemini.txt"
prova_no "NON ha interrogato Codex"     test -f "$LAV/codex.txt"

p="$(cat "$LAV/prompt.txt")"
prova "il prompt porta le istruzioni" contiene "$p" "congruita-commit"
prova "e il dossier"                  contiene "$p" "aggiunge la scansione ad alfa"

caso "5. interroga: un segreto ferma l'invio anche con --invia"
printf '\n+token=ghp_9f2c7d1e8a6b3f5c0d9e2a7b4c1f8e3d5a7b\n' >> "$LAV/dossier.md"
prova_no "l'invio viene rifiutato"   muto "$RV" interroga 7 --invia
prova_no "e Gemini resta non chiamato" test -f "$LAV/gemini.txt"
cp "$BANCO/pulito.md" "$LAV/dossier.md"

caso "6. interroga --invia: chiama tutti e due"
prova "esce senza errore"     muto "$RV" interroga 7 --invia
prova "risposta di Gemini"    test -s "$LAV/gemini.txt"
prova "risposta di Codex"     test -s "$LAV/codex.txt"

# ------------------------------------------------------------- 7. rilievi ---

caso "7. rilievi: unisce le due risposte"
prova "esce senza errore" muto "$RV" rilievi 7
prova "crea il foglio"    test -f "$LAV/rilievi.md"
prova "crea il json"      test -f "$LAV/rilievi.json"
r="$(cat "$LAV/rilievi.md")"
prova "identificatore di Gemini"                 contiene "$r" "G-1"
prova "identificatori di Codex"                  contiene "$r" "C-2"
prova "estrae il JSON anche dal recinto markdown" contiene "$r" "il messaggio promette meno del diff"
prova "accoppia i rilievi gemelli"               contiene "$r" "Probabilmente lo stesso rilievo"
prova "lascia i verdetti da compilare"           contiene "$r" "_da compilare_"
prova "riporta l'evidenza citata"                contiene "$r" "echo \$x"
prova "riporta il controllo ISO quando c'è"      contiene "$r" "A.8.28"

caso "8. rilievi: una risposta illeggibile si vede"
printf 'mi dispiace, non posso aiutarti.\n' > "$LAV/gemini.txt"
muto "$RV" rilievi 7
r="$(cat "$LAV/rilievi.md")"
prova    "avvisa che un revisore non ha risposto" contiene "$r" "Non tutti i revisori hanno risposto"
prova_no "e NON lo spaccia per zero rilievi"      contiene "$r" "non hanno trovato niente"
prova    "gli altri rilievi restano"              contiene "$r" "C-1"

# ------------------------------------------------------------ 9. archivia ---

caso "9. archivia: rifiuta un triage a metà"
prova_no "con verdetti aperti esce in errore" muto "$RV" archivia 7 --scrivi
prova_no "e non scrive niente"                test -d "$R/alfa/Docs/revisioni"

caso "10. archivia: compilato, va nella cartella del progetto"
sed -i '' 's/_da compilare_/accolto — corretto nel commit successivo/g' "$LAV/rilievi.md"
prova    "la prova a vuoto non copia"  muto "$RV" archivia 7
prova_no "e infatti non c'è niente"    test -d "$R/alfa/Docs/revisioni"
prova    "con --scrivi esce bene"      muto "$RV" archivia 7 --scrivi
prova    "il file è dentro il progetto" test -f "$R/alfa/Docs/revisioni/$(date '+%Y-%m-%d')-pr-7.md"

# -------------------------------------------------------------- 11. stato ---

caso "11. stato"
u="$("$RV" stato 2>&1)"
prova "elenca la revisione aperta" contiene "$u" "PR #7"
prova "e dice a che punto è"       contiene "$u" "risposto"

# ------------------------------------------------------------- 12. errori ---

caso "12. errori"
prova_no "numero non valido"      muto "$RV" dossier abc
prova_no "comando sconosciuto"    muto "$RV" comando-che-non-esiste
prova_no "rilievi senza risposte" muto "$RV" rilievi 99
prova    "--help esce 0"          muto "$RV" --help

# ------------------------------------------------------------------ esito ---

# ------------------------------------------------- 13. dossier da rami ------
#
# Qui una release si revisiona PRIMA che la PR esista, perche' la PR la apre e
# la fonde il Product Owner. Il dossier deve quindi sapersi costruire da un
# intervallo di rami, e da un sottoinsieme di percorsi: la release intera non
# entra in un prompt solo, e un revisore che riceve undici megabyte non
# revisiona, scorre.

caso "13. dossier-rami: che cosa rifiuta"

prova_no "senza argomenti"                muto "$RV" dossier-rami
prova_no "senza intervallo"               muto "$RV" dossier-rami area
prova_no "un'etichetta con una barra"     muto "$RV" dossier-rami a/b main..lavoro
prova_no "un'etichetta con maiuscole"     muto "$RV" dossier-rami Area main..lavoro
prova_no "un'etichetta che inizia per -"  muto "$RV" dossier-rami -area main..lavoro
prova_no "un intervallo senza i due punti" muto "$RV" dossier-rami area lavoro
prova_no "un ramo che non esiste"         muto "$RV" dossier-rami area main..inesistente

u="$("$RV" dossier-rami area lavoro 2>&1)"
prova "e quando manca l'intervallo lo spiega" contiene "$u" "base>..<head"

caso "14. dossier-rami: che cosa produce"

# Un ramo con due commit e due cartelle: una da revisionare, una da lasciare
# fuori. Serve a provare che il pathspec restringe davvero.
git -C "$R" checkout -q -b lavoro
mkdir -p "$R/beta" "$R/pesante"
printf 'uno\n' > "$R/beta/beta.sh"
git -C "$R" add beta/beta.sh
git -C "$R" commit -qm "feat(beta): il primo pezzo

Con un corpo, per vedere se arriva."
printf 'due\n' > "$R/pesante/registrazione.cast"
git -C "$R" add pesante/registrazione.cast
git -C "$R" commit -qm "chore: una registrazione che nessuno legge"
git -C "$R" checkout -q develop
git -C "$R" checkout -q lavoro

prova "il comando riesce" muto "$RV" dossier-rami area develop..lavoro

D="$R/.revisioni/area/dossier.md"
prova "la cartella non si chiama pr-area" test ! -d "$R/.revisioni/pr-area"
prova "il dossier esiste"                 test -f "$D"

d="$(cat "$D" 2>/dev/null || true)"
prova "dice l'intervallo"                 contiene "$d" "develop..lavoro"
prova "dice l'etichetta"                  contiene "$d" "area"
prova "elenca il primo commit"            contiene "$d" "feat(beta): il primo pezzo"
prova "riporta il corpo del commit"       contiene "$d" "Con un corpo, per vedere se arriva."
prova "elenca il secondo commit"          contiene "$d" "una registrazione che nessuno legge"
prova "elenca i file toccati"             contiene "$d" "beta/beta.sh"
prova "e porta il diff"                   contiene "$d" "+uno"

caso "15. dossier-rami: il pathspec restringe davvero"

prova "il comando riesce con un percorso" muto "$RV" dossier-rami ristretta develop..lavoro beta

d="$(cat "$R/.revisioni/ristretta/dossier.md" 2>/dev/null || true)"
prova    "dice quali percorsi ha guardato" contiene "$d" "beta"
prova    "il diff di beta c'è"             contiene "$d" "+uno"
prova_no "quello di pesante no"            contiene "$d" "+due"

prova "e l'esclusione funziona" muto "$RV" dossier-rami esclusa develop..lavoro . ':(exclude)*.cast'
d="$(cat "$R/.revisioni/esclusa/dossier.md" 2>/dev/null || true)"
prova    "beta resta"                      contiene "$d" "+uno"
prova_no "il .cast se ne va"               contiene "$d" "+due"

caso "16. dossier-rami: il resto del giro funziona uguale"

prova "il setaccio gira sul dossier da rami" muto "$RV" segreti area

u="$("$RV" interroga area 2>&1)"
prova "interroga lo trova"          contiene "$u" "PROVA A VUOTO"
prova "e non manda niente"          contiene "$u" "non e' stato mandato niente"

printf '\n+PERPLEXITY_API_KEY=pplx-4f9b2c7d1e8a6b3f5c0d9e2a7b4c1f8e\n' >> "$D"
prova_no "un segreto lo ferma anche qui" muto "$RV" interroga area --invia

u="$("$RV" stato 2>&1)"
prova "stato elenca la revisione da rami" contiene "$u" "area"
prova "e non la chiama PR"                test "$(printf '%s' "$u" | grep -c 'PR #area')" -eq 0

caso "17. archivia: la cartella dei documenti si scopre, non si presume"

# Il repository di prova non ha ne' docs/ ne' Docs/: resta il valore storico,
# che e' quello del repository d'origine. La prova 10 qui sopra lo verifica gia'.
# Quando invece docs/ minuscolo esiste - come in SqlStart2026 - il foglio va
# li', perche' una cartella con il case sbagliato su Linux ne diventa due.
mkdir -p "$R/docs"
sed -i.bak 's/_da compilare_/accolto: verificato/' "$LAV/rilievi.md" 2>/dev/null
muto "$RV" archivia 7 --scrivi
prova "con docs/ presente il case segue quello trovato" \
      test -f "$R/alfa/docs/revisioni/$(date '+%Y-%m-%d')-pr-7.md"
rm -rf "$R/docs" "$R/alfa/docs"

caso "18. segreti: le tre esclusioni aggiunte qui, e cio' che non spengono"

# Le tre righe aggiunte in fondo a segreti.esclusioni sono state pagate su
# fascicoli veri della release/1.0. Il rischio di un'esclusione non e' che sia
# inutile: e' che spenga anche il segreto vero. Per ognuna c'e' quindi una prova
# che il falso positivo tace, e accanto una prova che il segreto continua a
# gridare nella stessa forma.

cp "$BANCO/pulito.md" "$LAV/dossier.md"
printf '\n+        password=credenziali.password,\n' >> "$LAV/dossier.md"
prova    "un attributo di un oggetto non e' un valore"   muto "$RV" segreti 7

cp "$BANCO/pulito.md" "$LAV/dossier.md"
printf '\n+        password=PASSWORD_DI_PROVA,\n' >> "$LAV/dossier.md"
prova    "il nome di una costante non e' un valore"      muto "$RV" segreti 7

cp "$BANCO/pulito.md" "$LAV/dossier.md"
printf '\n+FINTA = Credenziali(password="non-e-un-segreto-e-non-lo-sara-mai")\n' >> "$LAV/dossier.md"
prova    "una frase italiana fra virgolette nemmeno"     muto "$RV" segreti 7

# --- e adesso quello che le tre righe NON devono spegnere ---

# Senza l'underscore obbligatorio, la seconda esclusione avrebbe spento anche
# questa: e' la ragione per cui l'underscore c'e'.
cp "$BANCO/pulito.md" "$LAV/dossier.md"
printf '\n+aws_secret_access_key=AKIAIOSFODNN7EXAMPLE,\n' >> "$LAV/dossier.md"
prova_no "una chiave AWS resta un segreto"               muto "$RV" segreti 7

cp "$BANCO/pulito.md" "$LAV/dossier.md"
printf '\n+        password=pplx-4f9b2c7d1e8a6b3f5c0d9e2a7b4c1f8e,\n' >> "$LAV/dossier.md"
prova_no "una chiave vera senza virgolette resta un segreto" muto "$RV" segreti 7

cp "$BANCO/pulito.md" "$LAV/dossier.md"
printf '\n+        password="ghp_9f2b4c8d1e6a3f7b5c0d9e2a4b8c1f6e3a7d",\n' >> "$LAV/dossier.md"
prova_no "un token GitHub fra virgolette resta un segreto"   muto "$RV" segreti 7

# La terza esclusione chiede parole tutte minuscole: una vera credenziale con
# un trattino in mezzo ha cifre o maiuscole, e quindi non le somiglia.
cp "$BANCO/pulito.md" "$LAV/dossier.md"
printf '\n+        password="Xk7-Qm2-Zt9-Rb4-Pv6-Lw1",\n' >> "$LAV/dossier.md"
prova_no "una password con trattini ma non minuscola resta un segreto" \
         muto "$RV" segreti 7

cp "$BANCO/pulito.md" "$LAV/dossier.md"

printf '\n%d passate, %d fallite\n' "$PASSATI" "$FALLITI"
[ "$FALLITI" -eq 0 ]
