#!/usr/bin/env bash
#
# Genera il keyfile condiviso dello sharded cluster, dentro il volume nominato
# `keyfile`. Eseguito dal servizio one-shot `keyfile-init` prima che qualunque
# mongod parta.
#
# È lo stesso script dello stack 02, e la ripetizione è voluta: i due stack sono
# indipendenti per ADR-0003 e nessuno dei due deve poter rompere l'altro
# cambiando un file condiviso. Rispetto a quello dello stack 02 cambia una cosa
# sola — qui il segreto è condiviso da NOVE processi in TRE replica set diversi
# (cfgrs, shard1rs, shard2rs), non da tre membri di uno solo. È il motivo per cui
# il keyfile sta in un volume unico invece che in uno per componente: nello
# sharded cluster l'autenticazione interna è di cluster, non di replica set, e
# `mongos` deve presentare lo stesso segreto degli shard a cui si collega.
#
# Il keyfile non entra nel repository (ADR-0014): nasce qui, al primo avvio,
# sulla macchina di chi esegue.

set -euo pipefail

DESTINAZIONE=/keyfile/mongo-keyfile

# L'idempotenza non è eleganza: al secondo `make up-03` il volume esiste già, e
# rigenerare il keyfile significherebbe che i membri non si riconoscono più fra
# loro — con un errore di autenticazione che sembra tutt'altro. Qui il danno
# sarebbe più largo che nello stack 02: un keyfile nuovo scollegherebbe anche
# `mongos` dagli shard già registrati nel config server.
if [[ -s "${DESTINAZIONE}" ]]; then
  echo "keyfile già presente: non lo rigenero"
else
  # 756 byte in base64: la lunghezza che la documentazione MongoDB usa nei propri
  # esempi. Il contenuto deve stare fra 6 e 1024 caratteri della classe base64.
  openssl rand -base64 756 > "${DESTINAZIONE}"
  echo "keyfile generato"
fi

# chmod e chown stanno FUORI dal ramo condizionale, di proposito: un volume
# ripristinato da un backup può avere il contenuto giusto e i permessi sbagliati,
# e in quel caso il ramo `else` non passerebbe mai. Correggerli sempre costa due
# syscall e toglie di mezzo un guasto difficile da leggere.
#
# 400 e non 600: la documentazione ammette solo la sola lettura per il
# proprietario (S-005). 999:999 è l'utente `mongodb` dell'immagine ufficiale
# (S-023) — il processo mongod gira con quello, e un keyfile che non gli
# appartiene viene rifiutato quanto uno con i permessi larghi.
chmod 400 "${DESTINAZIONE}"
chown 999:999 "${DESTINAZIONE}"

ls -ln "${DESTINAZIONE}"
