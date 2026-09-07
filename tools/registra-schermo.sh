#!/usr/bin/env bash
# Registra lo schermo in un `.mp4`, con o senza microfono, dentro la cartella che
# `tools/preflight.sh` controlla.
#
#   ./tools/registra-schermo.sh 02-failover-docker-kill          # con voce
#   AUDIO=no ./tools/registra-schermo.sh 02-failover-docker-kill # muto
#   ./tools/registra-schermo.sh 02-failover-docker-kill 240      # si ferma da sé a 4 minuti
#
# È l'altra metà di `tools/registra-terminale.py`, e le due non si sostituiscono: quella
# registra ciò che il terminale ha fatto, questa registra ciò che il pubblico vedrebbe —
# lo schermo e la voce di chi parla (ADR-0016). Il piano B del talk le vuole entrambe.
#
# LE DUE PASSATE, che sono il motivo per cui `AUDIO=no` esiste. Si gira prima il muto, lo
# si guarda, e solo dopo si rifà parlando: così la voce commenta una scena già vista
# invece di inseguirla. Il muto non è materiale di scarto — è quello che si acclude alla
# presentazione, dove una voce fuori campo darebbe fastidio.
#
# PERCHÉ L'ENCODER È QUELLO HARDWARE. `h264_videotoolbox` comprime nel chip e non nella
# CPU. Non è una preferenza estetica: le scene che questo strumento filma sono
# cronometrate — un failover dichiara i millisecondi di interruzione — e un encoder
# software che si prende i core mentre la scena gira falsa il numero che la scena esiste
# per mostrare. Si paga in byte: misurati sullo stesso schermo, `libx264 -crf 23` fa
# ~107 KB/s e questo ~848 KB/s, cioè circa 200 MB per quattro minuti (V-106). Chi ha
# bisogno di file più piccoli abbassa `BITRATE`, non cambia encoder.
#
# I NUMERI DI UN FILMATO NON SONO LA MISURA, per la stessa ragione per cui non lo sono
# quelli di una registrazione di terminale: è **una** esecuzione, e per giunta con un
# encoder acceso accanto. Le misure stanno in V-029 e V-031, che hanno tre giri e le
# mediane.
#
# GLI INDICI DEI DISPOSITIVI NON SONO CABLATI. AVFoundation li assegna nell'ordine in cui
# li trova, e l'ordine cambia: sulla macchina di sviluppo lo schermo è `[3]` perché prima
# vengono una webcam e due camere virtuali, ma basta installare o togliere un programma
# perché diventi `[2]` o `[4]`. Uno script che scrivesse `3` registrerebbe un giorno la
# webcam del relatore invece dello schermo, e se ne accorgerebbe riguardando il file.
# Quindi si chiedono a ffmpeg ogni volta, e si stampa che cosa si è scelto: il controllo
# è che tu legga quel nome prima di cominciare a parlare.
#
# Variabili:
#   AUDIO=si|no        con o senza microfono (predefinito: si)
#   SCHERMO=0          quale schermo, se ce n'è più d'uno (predefinito: 0)
#   MICROFONO="parte del nome"  quale ingresso audio; predefinito, il primo che si
#                      chiami «Microphone», altrimenti il primo dell'elenco
#   BITRATE=6M         qualità del video (predefinito: 6M)
#   DEMO_VIDEOS_DIR    dove finiscono i file; lo stesso che legge preflight
#
# Niente `set -e`: i controlli qui sotto sanno dire perché si fermano, e un `set -e` li
# farebbe uscire muti.
set -uo pipefail

FFMPEG="${FFMPEG:-ffmpeg}"
FFPROBE="${FFPROBE:-ffprobe}"
CARTELLA="${DEMO_VIDEOS_DIR:-${HOME}/SqlStart2026-registrazioni}"
AUDIO="${AUDIO:-si}"
SCHERMO="${SCHERMO:-0}"
MICROFONO="${MICROFONO:-}"
BITRATE="${BITRATE:-6M}"

ROSSO=$'\033[31m'; VERDE=$'\033[32m'; GIALLO=$'\033[33m'; NEUTRO=$'\033[0m'
if [[ ! -t 1 ]]; then ROSSO=''; VERDE=''; GIALLO=''; NEUTRO=''; fi

errore() { printf '%serrore%s  %s\n' "${ROSSO}" "${NEUTRO}" "$1" >&2; }
nota()   { printf '        %s\n' "$1" >&2; }

uso() {
  cat >&2 <<'TESTO'
uso: ./tools/registra-schermo.sh <nome-della-scena> [durata-in-secondi]

  <nome-della-scena>   senza estensione: il file esce come <nome>.mp4
  [durata]             se manca, si registra finché non premi «q»

  AUDIO=no             gira il muto, da guardare prima di rifarla parlando
TESTO
}

# --- Argomenti ----------------------------------------------------------------------

NOME="${1:-}"
DURATA="${2:-}"

if [[ -z "${NOME}" ]]; then
  errore "manca il nome della scena"
  uso
  exit 2
fi

if [[ "${NOME}" == */* ]]; then
  errore "il nome della scena non può contenere «/»: è un nome, non un percorso"
  nota "la cartella si sceglie con DEMO_VIDEOS_DIR"
  exit 2
fi

NOME="${NOME%.mp4}"

if [[ -n "${DURATA}" && ! "${DURATA}" =~ ^[0-9]+$ ]]; then
  errore "la durata si scrive in secondi interi: «${DURATA}» non lo è"
  exit 2
fi

case "${AUDIO}" in
  si|sì|yes|1) CON_VOCE=1 ;;
  no|0)        CON_VOCE=0 ;;
  *) errore "AUDIO=«${AUDIO}» non esiste: «si» registra la voce, «no» gira il muto"; exit 2 ;;
esac

# --- Prerequisiti -------------------------------------------------------------------

if ! command -v "${FFMPEG}" >/dev/null 2>&1; then
  errore "ffmpeg non è installato, e questo strumento non sa girare senza"
  nota "su macOS: brew install ffmpeg"
  nota "è l'unico strumento del repository che chiede un'installazione, e chiede di"
  nota "farla ADESSO e non la sera prima del talk"
  exit 3
fi

# --- Dove va il file ----------------------------------------------------------------

DESTINAZIONE="${CARTELLA}/${NOME}.mp4"

if [[ -e "${DESTINAZIONE}" ]]; then
  errore "esiste già: ${DESTINAZIONE}"
  nota "una registrazione non si sovrascrive: se quella vecchia non serve più, spostala"
  nota "o cancellala a mano, così la decisione è tua e non di uno script"
  exit 2
fi

if ! mkdir -p "${CARTELLA}"; then
  errore "non riesco a creare la cartella: ${CARTELLA}"
  exit 2
fi

# --- Quali dispositivi, chiesti adesso ----------------------------------------------

# `-list_devices true` scrive su stderr e poi esce con errore: è il suo modo di
# funzionare, non un guasto, quindi lo stato di uscita qui non si guarda.
DISPOSITIVI="$("${FFMPEG}" -hide_banner -f avfoundation -list_devices true -i "" 2>&1)"

leggi_video() {
  printf '%s\n' "${DISPOSITIVI}" | awk -v cerca="Capture screen ${SCHERMO}" '
    /AVFoundation video devices:/ { sezione = "video"; next }
    /AVFoundation audio devices:/ { sezione = "audio"; next }
    sezione == "video" && match($0, /\[[0-9]+\]/) {
      indice = substr($0, RSTART + 1, RLENGTH - 2)
      nome = substr($0, RSTART + RLENGTH + 1)
      gsub(/^ +| +$/, "", nome)
      if (!trovato && index(nome, cerca) > 0) { print indice "\t" nome; trovato = 1 }
    }'
}

leggi_audio() {
  printf '%s\n' "${DISPOSITIVI}" | awk -v cerca="${MICROFONO}" '
    /AVFoundation video devices:/ { sezione = "video"; next }
    /AVFoundation audio devices:/ { sezione = "audio"; next }
    sezione == "audio" && match($0, /\[[0-9]+\]/) {
      indice = substr($0, RSTART + 1, RLENGTH - 2)
      nome = substr($0, RSTART + RLENGTH + 1)
      gsub(/^ +| +$/, "", nome)
      if (!visto_primo) { primo = indice; primo_nome = nome; visto_primo = 1 }
      if (!visto_scelto) {
        if (cerca != "" && index(tolower(nome), tolower(cerca)) > 0) {
          scelto = indice; scelto_nome = nome; visto_scelto = 1
        } else if (cerca == "" && index(tolower(nome), "microphone") > 0) {
          scelto = indice; scelto_nome = nome; visto_scelto = 1
        }
      }
    }
    END {
      if (visto_scelto)     print scelto "\t" scelto_nome
      else if (visto_primo) print primo "\t" primo_nome
    }'
}

VIDEO="$(leggi_video)"
if [[ -z "${VIDEO}" ]]; then
  errore "non trovo «Capture screen ${SCHERMO}» fra i dispositivi di AVFoundation"
  nota "l'elenco di questa macchina, così scegli il numero giusto in SCHERMO:"
  printf '%s\n' "${DISPOSITIVI}" | grep -E 'devices:|\[[0-9]+\]' >&2
  nota "se l'elenco è vuoto, manca il permesso «Registrazione schermo» per il terminale"
  exit 3
fi
INDICE_VIDEO="${VIDEO%%$'\t'*}"
NOME_VIDEO="${VIDEO#*$'\t'}"

INGRESSO="${INDICE_VIDEO}"
NOME_AUDIO=''
if (( CON_VOCE )); then
  AUDIO_SCELTO="$(leggi_audio)"
  if [[ -z "${AUDIO_SCELTO}" ]]; then
    errore "nessun ingresso audio disponibile, e AUDIO=si lo pretende"
    nota "gira il muto con AUDIO=no, oppure collega un microfono"
    nota "se il microfono c'è ma non compare, manca il permesso «Microfono» per il"
    nota "terminale — e concederlo RIAVVIA il terminale, quindi fallo prima"
    exit 3
  fi
  INDICE_AUDIO="${AUDIO_SCELTO%%$'\t'*}"
  NOME_AUDIO="${AUDIO_SCELTO#*$'\t'}"
  INGRESSO="${INDICE_VIDEO}:${INDICE_AUDIO}"
fi

# --- Si gira ------------------------------------------------------------------------

printf '%sScena%s     %s\n' "${VERDE}" "${NEUTRO}" "${NOME}"
printf '%sSchermo%s   [%s] %s\n' "${VERDE}" "${NEUTRO}" "${INDICE_VIDEO}" "${NOME_VIDEO}"
if (( CON_VOCE )); then
  printf '%sVoce%s      [%s] %s\n' "${VERDE}" "${NEUTRO}" "${INDICE_AUDIO}" "${NOME_AUDIO}"
  printf '          %sleggi quel nome prima di parlare%s\n' "${GIALLO}" "${NEUTRO}"
else
  printf '%sVoce%s      muto (AUDIO=no)\n' "${VERDE}" "${NEUTRO}"
fi
printf '%sFile%s      %s\n' "${VERDE}" "${NEUTRO}" "${DESTINAZIONE}"
if [[ -n "${DURATA}" ]]; then
  printf '%sDurata%s    %s secondi, poi si ferma da sé\n' "${VERDE}" "${NEUTRO}" "${DURATA}"
else
  printf '%sPer finire%s premi «q» in questa finestra\n' "${VERDE}" "${NEUTRO}"
fi
printf '\n'

# Le opzioni d'ingresso qui sotto sono quelle che restano dopo averle provate una per
# una su questa macchina; la misura sta in V-106.
#
# `-capture_cursor 1` perché il puntatore fa parte della spiegazione: chi guarda deve
# vedere dove sta guardando chi parla.
#
# `-pixel_format uyvy422` PRIMA di `-i` dichiara il formato dell'INGRESSO. Senza, ffmpeg
# prova a chiedere allo schermo il formato dell'uscita — `yuv420p`, che AVFoundation non
# offre — e stampa a ogni corsa cinque righe di avviso su un file che poi produce
# comunque. L'avviso è innocuo e la riga senza avviso è leggibile: si sceglie la seconda.
#
# `-framerate 30` non c'è perché non serve: misurato con e senza, `-t 3` dà 2,966667 e
# 2,966668 secondi, e in tutti e due i casi il flusso esce a 30 fps — è la cadenza che
# lo schermo offre già. AVFoundation lo dice pure, nella riga di rumore qui sotto: la
# configurazione chiesta non la applica, ripiega sulla propria. Un'opzione che il
# dispositivo ignora è un'opzione che confonde chi legge il comando; e per mezz'ora ha
# confuso anche chi lo scriveva, perché sembrava lei la causa dei file «lunghi la metà».
# La causa era la riga che *stampava* la durata: vedi il commento a SECONDI, più sotto.
#
# `-color_range mpeg` dichiara in uscita l'intervallo che videotoolbox avrebbe scelto
# comunque. Non cambia l'immagine: toglie una riga di avviso dicendo esplicitamente la
# cosa su cui ffmpeg avvisava di stare indovinando.
#
# Restano tre righe di rumore, e nessuna delle tre è un guasto:
#   - `objc[...]: class NSKVONotifying_AVCaptureScreenInput not linked into
#     application`, ripetuto tre volte: viene da AVFoundation, non da qui;
#   - `Configuration of video device failed, falling back to default.`: compare anche
#     senza nessuna opzione d'ingresso — provato — e il «default» è esattamente ciò che
#     si vuole, cioè lo schermo intero a 30 fps;
#   - `Stream #0: not enough frames to estimate rate`: ffmpeg lo dice all'avvio, quando
#     di fotogrammi ne ha ancora visti troppo pochi per contarli.
# Nessuna si può zittire senza zittire anche gli errori veri, e un `-loglevel error` che
# nasconde tutto è il modo di non accorgersi della quarta riga, quella vera.
COMANDO=(
  "${FFMPEG}" -hide_banner -loglevel warning
  -f avfoundation -pixel_format uyvy422 -capture_cursor 1
  -i "${INGRESSO}"
)
if [[ -n "${DURATA}" ]]; then
  COMANDO+=(-t "${DURATA}")
fi
COMANDO+=(-c:v h264_videotoolbox -b:v "${BITRATE}" -pix_fmt yuv420p -color_range mpeg)
if (( CON_VOCE )); then
  COMANDO+=(-c:a aac -b:a 128k)
else
  COMANDO+=(-an)
fi
COMANDO+=("${DESTINAZIONE}")

# Senza `-nostdin`, e di proposito: è così che «q» arriva a ffmpeg e chiude il file per
# bene. Ctrl-C funziona lo stesso, ma «q» è quello che si dice a chi non lo sa.
"${COMANDO[@]}"
ESITO=$?

# --- Che cosa è uscito --------------------------------------------------------------

if [[ ! -s "${DESTINAZIONE}" ]]; then
  errore "non è stato prodotto nessun file (ffmpeg è uscito con ${ESITO})"
  exit 1
fi

printf '\n'
if ! command -v "${FFPROBE}" >/dev/null 2>&1; then
  printf '%sFatto%s     %s\n' "${VERDE}" "${NEUTRO}" "${DESTINAZIONE}"
  exit 0
fi

# Il verdetto non è «il comando è finito bene»: è che il file contenga le tracce che
# doveva contenere. Un `.mp4` senza traccia audio, girato credendo di parlarci sopra, è
# esattamente il guasto che si scopre troppo tardi (ADR-0055).
LETTURA="$("${FFPROBE}" -hide_banner -v error \
  -show_entries format=duration,size \
  -show_entries stream=codec_type,width,height \
  -of default=noprint_wrappers=1 "${DESTINAZIONE}" 2>/dev/null)"

# `LC_NUMERIC=C` non è pignoleria: ffprobe scrive `duration=2.966668` col punto, sempre,
# perché è un formato dati; awk con la locale italiana legge quel punto come fine del
# numero e ne ricava 2. Un file di tre secondi veniva così annunciato come «2,0 s», e la
# colpa sembrava dell'acquisizione. Si legge il numero alla maniera dei dati e lo si
# scrive alla maniera di chi legge: sono due cose diverse, e confonderle qui è costato
# un'indagine su un guasto che non c'era.
SECONDI="$(printf '%s\n' "${LETTURA}" \
  | LC_NUMERIC=C awk -F= '/^duration=/ { s = sprintf("%.1f", $2); sub(/\./, ",", s); print s }')"
BYTE="$(printf '%s\n' "${LETTURA}" | awk -F= '/^size=/ { print $2 }')"
LARGHEZZA="$(printf '%s\n' "${LETTURA}" | awk -F= '/^width=/ { print $2; exit }')"
ALTEZZA="$(printf '%s\n' "${LETTURA}" | awk -F= '/^height=/ { print $2; exit }')"
TRACCE_AUDIO="$(printf '%s\n' "${LETTURA}" | grep -c '^codec_type=audio')"

printf '%sFatto%s     %s\n' "${VERDE}" "${NEUTRO}" "${DESTINAZIONE}"
printf '          %s×%s · %s s · %s byte · tracce audio: %s\n' \
  "${LARGHEZZA}" "${ALTEZZA}" "${SECONDI}" "${BYTE}" "${TRACCE_AUDIO}"

if (( CON_VOCE )) && (( TRACCE_AUDIO == 0 )); then
  errore "hai chiesto la voce e il file non ha traccia audio"
  exit 1
fi
if (( ! CON_VOCE )) && (( TRACCE_AUDIO > 0 )); then
  errore "hai chiesto il muto e il file ha una traccia audio"
  exit 1
fi

printf '          riguardalo prima di dichiararlo buono: «open %s»\n' "${DESTINAZIONE}"
exit 0
