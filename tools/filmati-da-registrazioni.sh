#!/usr/bin/env bash
# Fabbrica i filmati di riserva `.mp4` dalle registrazioni di terminale già archiviate,
# senza riaccendere nessuno stack.
#
#   ./tools/filmati-da-registrazioni.sh              # tutti: cinque montaggi e otto scene
#   ./tools/filmati-da-registrazioni.sh --elenco     # che cosa uscirebbe, senza produrlo
#   ./tools/filmati-da-registrazioni.sh 03-maggioranza-persa-muto   # uno solo
#
# È il terzo strumento della famiglia, e non sostituisce gli altri due. Il primo,
# `registra-terminale.py`, conserva quello che il terminale ha fatto; il secondo,
# `registra-schermo.sh`, conserva quello che il pubblico avrebbe visto. Questo prende il
# primo e ne ricava il secondo: le scene sono già state eseguite davvero, con i tempi che
# hanno avuto, e rigirarle costerebbe due stack, uno scambio di `.env` e un pomeriggio —
# per ottenere comunque una esecuzione diversa da quella misurata.
#
# QUELLO CHE QUESTO STRUMENTO NON PUÒ FARE. Un `.cast` contiene il terminale e nient'altro:
# niente finestra di Compass, niente grafico che si muove, niente barra dei menu. Le scene
# che vivono fuori dal terminale — il filmato 4, che dimostra l'avvio con la rete spenta
# mostrando l'icona del Wi-Fi — si girano con `make filmato` e non da qui.
#
# ESCE MUTO, SEMPRE, e non è una limitazione: un `.cast` non ha voce da restituire, e il
# filmato muto è esattamente quello che va DENTRO le slide, dove una voce registrata
# sovrapposta a quella di chi parla dal vivo è un difetto (ADR-0140). La passata parlata
# è un'altra cosa, va su YouTube, e si gira con l'altro strumento.
#
# DUE FLAG TENGONO IN PIEDI LA DURATA, e tolti non rompono niente tranne il senso.
#
#   Il limite di inattività di `agg` vale cinque secondi se non glielo si dice, e comprime
#   a cinque ogni pausa più lunga. Su queste scene la pausa non è tempo morto: nella scena
#   8 i quindici secondi prima dell'errore *sono* la risposta alla domanda. Misurato: 40,1 s
#   di scena uscivano 21,3 s, meno della metà (V-107). Un valore «spento» non esiste, e si
#   alza a un'ora — più lunga di qualunque scena che abbia senso girare.
#
#   Il passo dei fotogrammi va forzato costante. Una GIF ha fotogrammi a durata variabile;
#   il `.mp4` che ne nasce eredita timestamp fuori ordine, e `ffmpeg`, incollandone due
#   senza ricodificare, scarta ciò che non sa incastrare avvisando in una riga che scorre
#   via. Misurato: il filmato 05 usciva 47,1 s invece di 52,5 (V-107).
#
# E PER QUESTO SI CONTA. Nessuno dei due guasti si vede guardando il filmato: scorre, si
# apre, sembra riuscito. Si vedono contando, quindi ogni filmato viene confrontato con la
# somma delle scene che lo compongono, e una differenza sopra il mezzo secondo è un errore
# e non un avviso: una riserva che dura la metà della scena che sostituisce non è la
# riserva di quella scena (ADR-0116).
#
# Variabili:
#   AGG, FFMPEG, FFPROBE   i tre programmi, se non sono nel PATH con il nome consueto
#   CORPO=28               il corpo del carattere; 28 su 100 colonne riempie uno schermo
#   TEMA=asciinema         uno dei temi di agg
#   CODA=2                 secondi di fermo immagine finale, per far leggere l'ultima riga
#   DEMO_VIDEOS_DIR        dove finiscono i file; lo stesso che legge preflight
#
# Niente `set -e`: i controlli qui sotto sanno dire perché si fermano.
set -uo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCENE="${RADICE}/docs/05-talk/registrazioni"
USCITA="${DEMO_VIDEOS_DIR:-${HOME}/SqlStart2026-registrazioni}"

AGG="${AGG:-agg}"
FFMPEG="${FFMPEG:-ffmpeg}"
FFPROBE="${FFPROBE:-ffprobe}"
CORPO="${CORPO:-28}"
TEMA="${TEMA:-asciinema}"
CODA="${CODA:-2}"

ROSSO=$'\033[31m'; VERDE=$'\033[32m'; NEUTRO=$'\033[0m'
if [[ ! -t 1 ]]; then ROSSO=''; VERDE=''; NEUTRO=''; fi

# Il catalogo: a sinistra il filmato, a destra le scene che lo compongono, nell'ordine in
# cui vanno viste. I cinque montaggi sono quelli della tabella in
# docs/05-talk/registrazioni/README.md; le otto scene singole servono a chi, in slide, le
# vuole separate invece che di fila.
catalogo() {
  cat <<'FINE'
01-failover-docker-kill-muto: 02-failover-docker-kill
02-failover-i-due-gesti-muto: 02-failover-docker-kill 03-failover-terminazione-pulita
03-maggioranza-persa-muto: 04-maggioranza-persa
05-guasto-shard-nei-due-profili-muto: 08-guasto-shard-palco 09-failover-membro-shard
06-blocco-3-per-intero-muto: 05-avvio-sharded 06-stato-sharded 07-distribuzione-sharded
scena-02-failover-docker-kill-muto: 02-failover-docker-kill
scena-03-failover-terminazione-pulita-muto: 03-failover-terminazione-pulita
scena-04-maggioranza-persa-muto: 04-maggioranza-persa
scena-05-avvio-sharded-muto: 05-avvio-sharded
scena-06-stato-sharded-muto: 06-stato-sharded
scena-07-distribuzione-sharded-muto: 07-distribuzione-sharded
scena-08-guasto-shard-palco-muto: 08-guasto-shard-palco
scena-09-failover-membro-shard-muto: 09-failover-membro-shard
FINE
}

scene_di() {
  catalogo | awk -F': ' -v n="$1" '$1 == n { print $2 }'
}

# L'istante dell'ultimo evento di una registrazione: è la sua durata vera. `LC_NUMERIC=C`
# non è un vezzo — in locale italiana `awk` legge il punto di `40.123456` come fine del
# numero e ne ricava `40`, che è il guasto già incontrato in V-106.
durata_cast() {
  tail -n 1 "${SCENE}/$1.cast" \
    | LC_NUMERIC=C awk -F, '{ gsub(/[^0-9.]/, "", $1); print $1 }'
}

manca() {
  printf '%sManca %s%s: %s\n' "${ROSSO}" "$1" "${NEUTRO}" "$2" >&2
  exit 3
}

# --- Il catalogo, senza produrre niente ------------------------------------------------

if [[ "${1:-}" == "--elenco" ]]; then
  catalogo
  exit 0
fi

if [[ "${1:-}" == "--aiuto" || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 0
fi

# --- I nomi chiesti, o tutti ------------------------------------------------------------

RICHIESTI=("$@")
if [[ ${#RICHIESTI[@]} -eq 0 ]]; then
  # `mapfile` non c'è su bash 3.2, che è quello che macOS installa.
  RICHIESTI=()
  while IFS= read -r riga; do RICHIESTI+=("${riga%%:*}"); done < <(catalogo)
fi

for nome in "${RICHIESTI[@]}"; do
  if [[ -z "$(scene_di "${nome}")" ]]; then
    printf '%s«%s» non è nel catalogo.%s Quello che c'"'"'è:\n' "${ROSSO}" "${nome}" "${NEUTRO}" >&2
    catalogo | sed 's/^/  /' >&2
    exit 2
  fi
done

# --- I prerequisiti, prima di cominciare ------------------------------------------------

command -v "${AGG}" >/dev/null 2>&1 \
  || manca "agg" "è il programma che disegna una registrazione di terminale. Si installa con «brew install agg»."
command -v "${FFMPEG}" >/dev/null 2>&1 \
  || manca "ffmpeg" "serve a trasformare in .mp4 quello che agg disegna. Si installa con «brew install ffmpeg»."
command -v "${FFPROBE}" >/dev/null 2>&1 \
  || manca "ffprobe" "arriva insieme a ffmpeg, e serve a rileggere quello che è uscito."

LAVORO="$(mktemp -d)"
trap 'rm -rf "${LAVORO}"' EXIT
mkdir -p "${USCITA}"

# --- Da .cast a .mp4 muto ---------------------------------------------------------------

rendi() {
  local scena="$1"
  [[ -f "${LAVORO}/${scena}.mp4" ]] && return 0
  "${AGG}" --quiet --font-size "${CORPO}" --theme "${TEMA}" \
      --last-frame-duration "${CODA}" --idle-time-limit 3600 --fps-cap 15 \
      "${SCENE}/${scena}.cast" "${LAVORO}/${scena}.gif" || return 1
  "${FFMPEG}" -hide_banner -loglevel warning -y -i "${LAVORO}/${scena}.gif" \
      -vf 'scale=trunc(iw/2)*2:trunc(ih/2)*2' -r 15 -fps_mode cfr \
      -c:v h264_videotoolbox -b:v 6M -pix_fmt yuv420p -color_range mpeg -an \
      "${LAVORO}/${scena}.mp4"
}

monta() {
  local nome="$1"
  local elenco="${LAVORO}/${nome}.txt"
  local scena atteso=0
  : > "${elenco}"

  for scena in $(scene_di "${nome}"); do
    rendi "${scena}" || return 1
    printf "file '%s'\n" "${LAVORO}/${scena}.mp4" >> "${elenco}"
    atteso=$(LC_NUMERIC=C awk -v a="${atteso}" -v b="$(durata_cast "${scena}")" \
      -v c="${CODA}" 'BEGIN { printf "%.2f", a + b + c }')
  done

  "${FFMPEG}" -hide_banner -loglevel warning -y -f concat -safe 0 -i "${elenco}" \
      -c copy "${USCITA}/${nome}.mp4" || return 1

  local misurato byte
  misurato=$("${FFPROBE}" -v error -show_entries format=duration -of csv=p=0:nk=1 \
      "${USCITA}/${nome}.mp4")
  byte=$("${FFPROBE}" -v error -show_entries format=size -of csv=p=0:nk=1 \
      "${USCITA}/${nome}.mp4")

  if LC_NUMERIC=C awk -v m="${misurato}" -v a="${atteso}" \
       'BEGIN { d = m - a; if (d < 0) d = -d; exit (d > 0.5) }'; then
    LC_NUMERIC=C awk -v n="${nome}.mp4" -v m="${misurato}" -v a="${atteso}" \
      -v b="${byte}" -v v="${VERDE}" -v z="${NEUTRO}" \
      'BEGIN { printf "  %s✓%s %-46s %5.1f s (attesi %.1f) · %d byte\n", v, z, n, m, a, b }'
    return 0
  fi

  LC_NUMERIC=C awk -v n="${nome}.mp4" -v m="${misurato}" -v a="${atteso}" \
    -v r="${ROSSO}" -v z="${NEUTRO}" \
    'BEGIN { printf "  %s✗%s %-46s %5.1f s, ma le sue scene ne fanno %.1f\n", r, z, n, m, a }' >&2
  return 1
}

# --- La corsa ----------------------------------------------------------------------------

printf 'Filmati di riserva, in %s:\n' "${USCITA}"

GUASTI=0
for nome in "${RICHIESTI[@]}"; do
  monta "${nome}" || GUASTI=$((GUASTI + 1))
done

if [[ ${GUASTI} -gt 0 ]]; then
  printf '\n%s%d filmati non durano quanto le scene che sostituiscono.%s\n' \
    "${ROSSO}" "${GUASTI}" "${NEUTRO}" >&2
  printf 'Non vanno messi nelle slide: racconterebbero una scena più corta di quella vera.\n' >&2
  exit 1
fi

printf '\nNessuno di questi è la scena 4 — «make up-02 da zero, con la rete spenta»: quella\n'
printf 'non ha una registrazione di terminale da cui nascere, perché la prova sta fuori dal\n'
printf 'terminale, nell'"'"'icona del Wi-Fi spenta. Si gira con «make filmato».\n'
