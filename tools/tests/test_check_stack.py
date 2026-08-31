import pytest

from check_stack import carica, digest_noti_da, leggi_ambiente, main, risolvi, verifica


def conforme(**modifiche):
    """Un servizio che rispetta tutte le regole, da rompere una alla volta.

    I test negativi partono da qui e cambiano una cosa sola: così il problema
    segnalato è attribuibile alla modifica e non a un difetto del campione.
    """
    servizio = {
        "image": "mongo@sha256:aaa",
        "pull_policy": "never",
        "mem_limit": "1024m",
        "cpus": 1.0,
        "command": ["mongod", "--wiredTigerCacheSizeGB", "0.25"],
    }
    servizio.update(modifiche)
    return {"services": {"mongo": servizio}}


def test_una_cache_maggiore_del_limite_di_memoria_e_un_problema():
    # È il controllo che MongoDB non fa: V-009 ha misurato che una cache più
    # grande del mem_limit viene accettata senza un avviso che colleghi le due
    # cifre. Il file Compose è l'unico posto dove il controllo può esistere.
    documento = conforme(
        mem_limit="512m",
        command=["mongod", "--wiredTigerCacheSizeGB", "1.0"],
    )
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any(
        "wiredTigerCacheSizeGB" in problema and "mem_limit" in problema
        for problema in problemi
    ), problemi


def test_il_campione_conforme_non_produce_problemi():
    assert verifica(conforme(), digest_noti={"sha256:aaa"}) == []


def test_la_chiave_version_e_obsoleta():
    documento = conforme()
    documento["version"] = "3.8"
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("version" in problema for problema in problemi), problemi


def test_un_immagine_non_pinnata_per_digest_e_un_problema():
    documento = conforme(image="mongo:7.0.40")
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("digest" in problema for problema in problemi), problemi


def test_un_digest_sconosciuto_a_images_env_e_un_problema():
    documento = conforme(image="mongo@sha256:bbb")
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("images.env" in problema for problema in problemi), problemi


def test_il_tag_latest_e_vietato():
    # «The latest tag is always pulled even when the missing pull policy is
    # used»: con `latest` il vincolo offline salta senza preavviso (ADR-0018).
    documento = conforme(image="mongo:latest")
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("latest" in problema for problema in problemi), problemi


def test_pull_policy_diversa_da_never_e_un_problema():
    # `missing` scarica ciò che manca. In sala non c'è rete da cui scaricare, e
    # il tentativo è un minuto perso davanti al pubblico (ADR-0039).
    documento = conforme(pull_policy="missing")
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("never" in problema for problema in problemi), problemi


def test_pull_policy_non_puo_dipendere_da_una_variabile():
    # Risolta vale «never», e non basta: la garanzia starebbe in un file
    # d'ambiente che si può dimenticare di passare, invece che nell'artefatto.
    # Chi apre il file Compose deve leggere lì che cosa succederà.
    risolto = conforme(pull_policy="never")
    grezzo = conforme(pull_policy="${PULL_POLICY:-never}")
    problemi = verifica(risolto, digest_noti={"sha256:aaa"}, grezzo=grezzo)
    assert any("variabile" in problema for problema in problemi), problemi


def test_pull_policy_assente_e_un_problema():
    documento = conforme()
    del documento["services"]["mongo"]["pull_policy"]
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("pull_policy" in problema for problema in problemi), problemi


def test_mem_limit_assente_e_un_problema():
    documento = conforme()
    del documento["services"]["mongo"]["mem_limit"]
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("mem_limit" in problema for problema in problemi), problemi


def test_cpus_assente_e_un_problema():
    documento = conforme()
    del documento["services"]["mongo"]["cpus"]
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("cpus" in problema for problema in problemi), problemi


def test_un_mongod_senza_cache_dichiarata_e_un_problema():
    documento = conforme(command=["mongod"])
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("wiredTigerCacheSizeGB" in problema for problema in problemi), problemi


def test_un_servizio_che_non_avvia_mongod_non_deve_dichiarare_la_cache():
    # Un mongos instrada e non ha storage: pretendere una cache da lui sarebbe
    # una regola che sbaglia bersaglio.
    documento = conforme(command=["mongos", "--configdb", "cfgrs/config-1:27017"])
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert not any(
        "wiredTigerCacheSizeGB" in problema for problema in problemi
    ), problemi


def test_un_indirizzo_ip_letterale_e_un_problema():
    # Il replica set memorizza i nomi con cui i membri si chiamano fra loro e li
    # rimanda al client: un IP scritto a mano funziona finché la rete non cambia,
    # poi rompe la scoperta della topologia (ADR-0021).
    documento = conforme(
        command=["mongod", "--wiredTigerCacheSizeGB", "0.25", "--bind_ip", "172.18.0.2"]
    )
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("172.18.0.2" in problema for problema in problemi), problemi


def test_le_maschere_di_ascolto_non_sono_indirizzi_di_topologia():
    # `0.0.0.0` e `127.0.0.1` dicono su quali interfacce ascoltare, non dove
    # trovare un altro nodo: vietarli sarebbe una regola che sbaglia bersaglio.
    documento = conforme(
        command=["mongod", "--wiredTigerCacheSizeGB", "0.25", "--bind_ip", "0.0.0.0"]
    )
    assert verifica(documento, digest_noti={"sha256:aaa"}) == []


def test_depends_on_senza_condition_e_un_problema():
    documento = conforme()
    documento["services"]["mongo"]["depends_on"] = ["init"]
    documento["services"]["init"] = {
        "image": "mongo@sha256:aaa",
        "pull_policy": "never",
        "mem_limit": "128m",
        "cpus": 0.5,
        "healthcheck": {"test": ["CMD", "true"]},
    }
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("condition" in problema for problema in problemi), problemi


def test_attendere_un_servizio_privo_di_healthcheck_e_un_problema():
    documento = conforme()
    documento["services"]["mongo"]["depends_on"] = {
        "init": {"condition": "service_healthy"}
    }
    documento["services"]["init"] = {
        "image": "mongo@sha256:aaa",
        "pull_policy": "never",
        "mem_limit": "128m",
        "cpus": 0.5,
    }
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("healthcheck" in problema for problema in problemi), problemi


def test_attendere_il_completamento_non_richiede_healthcheck():
    # `service_completed_successfully` attende un container che esce, non uno
    # che diventa sano: pretendere un healthcheck da lui sarebbe un falso allarme.
    documento = conforme()
    documento["services"]["mongo"]["depends_on"] = {
        "init": {"condition": "service_completed_successfully"}
    }
    documento["services"]["init"] = {
        "image": "mongo@sha256:aaa",
        "pull_policy": "never",
        "mem_limit": "128m",
        "cpus": 0.5,
        # Aggiunto al Task 6, quando la regola sul `restart` dei one-shot ha
        # fatto diventare rosso questo test: il campione era incompleto, non la
        # regola sbagliata. Un servizio atteso come completato che Compose
        # rialzerebbe è un problema vero, e questo test non parla di quello.
        "restart": "no",
    }
    assert verifica(documento, digest_noti={"sha256:aaa"}) == []


def test_risolve_una_variabile_semplice():
    assert risolvi("${MONGO_IMAGE}", {"MONGO_IMAGE": "mongo@sha256:aaa"}) == (
        "mongo@sha256:aaa"
    )


def test_usa_il_valore_predefinito_quando_la_variabile_manca():
    assert risolvi("${PULL_POLICY:-missing}", {}) == "missing"


def test_il_valore_predefinito_cede_alla_variabile_presente():
    assert risolvi("${PULL_POLICY:-missing}", {"PULL_POLICY": "never"}) == "never"


def test_la_variabile_vuota_vale_come_assente():
    # Compose tratta la stringa vuota come «non impostata» nelle forme che
    # portano i due punti: `${VAR:-x}` dà `x`, non «». Un file d'ambiente con
    # `PULL_POLICY=` è la forma in cui questo capita davvero.
    assert risolvi("${PULL_POLICY:-missing}", {"PULL_POLICY": ""}) == "missing"


def test_la_variabile_vuota_non_soddisfa_la_forma_obbligatoria():
    with pytest.raises(KeyError, match="MONGO_IMAGE"):
        risolvi("${MONGO_IMAGE:?eseguire make images-pull}", {"MONGO_IMAGE": ""})


def test_la_forma_senza_operatore_lascia_passare_il_vuoto():
    # Senza i due punti non c'è alternativa da scegliere: `${VAR}` di una
    # variabile vuota è una stringa vuota, e va restituita tale.
    assert risolvi("prefisso-${VUOTA}", {"VUOTA": ""}) == "prefisso-"


def test_la_forma_obbligatoria_fallisce_dicendo_cosa_manca():
    # `${VAR:?messaggio}` esiste per far fallire Compose subito e con una spiegazione.
    # Lo strumento deve fallire nello stesso punto, non sorvolare.
    with pytest.raises(KeyError, match="MONGO_IMAGE"):
        risolvi("${MONGO_IMAGE:?eseguire make images-pull}", {})


def test_legge_le_variabili_ignorando_commenti_e_righe_vuote(tmp_path):
    percorso = tmp_path / "images.env"
    percorso.write_text(
        "# Immagini del lab, pinnate per digest.\n"
        "\n"
        "MONGO_IMAGE=mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b\n",
        encoding="utf-8",
    )
    assert leggi_ambiente(percorso) == {"MONGO_IMAGE": "mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b"}


def test_un_digest_troppo_corto_non_conta_come_digest():
    # `sha256:abc` non è un riferimento che Docker accetti: un digest SHA-256 ha
    # sessantaquattro cifre esadecimali. Riconoscerlo come pin valido farebbe
    # approvare uno stack che non si avvia.
    assert digest_noti_da({"MONGO_IMAGE": "mongo@sha256:abc"}) == set()


def test_estrae_i_digest_dalle_variabili_di_ambiente():
    ambiente = {"MONGO_IMAGE": "mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b", "PULL_POLICY": "never"}
    assert digest_noti_da(ambiente) == {"sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b"}


COMPOSE_CONFORME = """
name: prova
services:
  mongo:
    image: ${MONGO_IMAGE}
    pull_policy: never
    mem_limit: ${MEMORIA:-1024m}
    cpus: 1.0
    command: [mongod, --wiredTigerCacheSizeGB, "0.25"]
"""


def test_carica_risolve_le_variabili_dentro_il_documento(tmp_path):
    percorso = tmp_path / "compose.yaml"
    percorso.write_text(COMPOSE_CONFORME, encoding="utf-8")
    documento = carica(percorso, {"MONGO_IMAGE": "mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b"})
    servizio = documento["services"]["mongo"]
    assert servizio["image"] == "mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b"
    assert servizio["mem_limit"] == "1024m"


def test_main_esce_zero_su_un_file_conforme(tmp_path, capsys):
    ambiente = tmp_path / "images.env"
    ambiente.write_text("MONGO_IMAGE=mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b\n", encoding="utf-8")
    compose = tmp_path / "compose.yaml"
    compose.write_text(COMPOSE_CONFORME, encoding="utf-8")
    assert main(["--ambiente", str(ambiente), str(compose)]) == 0


def test_main_esce_uno_e_nomina_il_file_che_non_va(tmp_path, capsys):
    ambiente = tmp_path / "images.env"
    ambiente.write_text("MONGO_IMAGE=mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b\n", encoding="utf-8")
    compose = tmp_path / "compose.yaml"
    compose.write_text(
        COMPOSE_CONFORME.replace("    mem_limit: ${MEMORIA:-1024m}\n", ""), encoding="utf-8"
    )
    assert main(["--ambiente", str(ambiente), str(compose)]) == 1
    assert "compose.yaml" in capsys.readouterr().err


def test_main_esce_due_con_un_messaggio_se_il_file_non_esiste(tmp_path, capsys):
    ambiente = tmp_path / "images.env"
    ambiente.write_text("MONGO_IMAGE=mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b\n", encoding="utf-8")
    assert main(["--ambiente", str(ambiente), str(tmp_path / "assente.yaml")]) == 2
    assert "assente.yaml" in capsys.readouterr().err


# --- Task 6: le regole che nascono con il replica set -----------------------
#
# Quattro regole nuove più un difetto vecchio. Tutte hanno in comune un vincolo
# che vale la pena scrivere: NON DEVONO SCATTARE SULLO STACK 01, che non ha né
# replica né catena. Ognuna si autolimita guardando il file, non un elenco di
# nomi: se il file non parla di replica set, la regola tace.


def replica(**modifiche):
    """Due membri di un replica set, conformi, da rompere uno alla volta."""
    membro = {
        "image": "mongo@sha256:aaa",
        "pull_policy": "never",
        "mem_limit": "1024m",
        "cpus": 1.0,
        "command": [
            "mongod",
            "--replSet",
            "rs0",
            "--keyFile",
            "/keyfile/mongo-keyfile",
            "--wiredTigerCacheSizeGB",
            "0.25",
        ],
        "volumes": ["keyfile:/keyfile:ro"],
    }
    primo = dict(membro)
    primo.update(modifiche)
    return {"services": {"mongo-rs-1": primo, "mongo-rs-2": dict(membro)}}


def test_il_campione_di_replica_non_produce_problemi():
    assert verifica(replica(), digest_noti={"sha256:aaa"}) == []


# Regola 1 — il keyfile arriva da un volume nominato, non dall'host.


def test_un_keyfile_montato_da_un_percorso_dell_host_e_un_problema():
    # ADR-0014 esiste perché su macOS un bind mount non conserva i permessi del
    # file, e mongod rifiuta un keyfile leggibile da altri. Il sintomo è un
    # membro che non parte, e la causa è a due file di distanza.
    documento = replica(volumes=["./keyfile:/keyfile:ro"])
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any(
        "keyfile" in problema.lower() and "ADR-0014" in problema
        for problema in problemi
    ), problemi


def test_un_keyfile_da_volume_nominato_non_e_un_problema():
    problemi = verifica(replica(), digest_noti={"sha256:aaa"})
    assert not any("ADR-0014" in problema for problema in problemi), problemi


def test_un_keyfile_dichiarato_e_non_montato_da_nessuna_parte_e_un_problema():
    # Il caso peggiore: mongod riceve --keyFile e il percorso non esiste. Parte
    # e muore, e il file Compose sembra a posto perché la riga c'è.
    documento = replica(volumes=["dati:/data/db"])
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("keyfile" in problema.lower() for problema in problemi), problemi


# Regola 2 — dove c'è `--replSet` ci deve essere `--keyFile`.


def test_un_membro_con_replset_e_senza_keyfile_e_un_problema():
    # Parte lo stesso e resta fuori dalla replica senza dirlo: gli altri due lo
    # rifiutano all'handshake, e nei log compare come un problema di rete.
    documento = replica(
        command=["mongod", "--replSet", "rs0", "--wiredTigerCacheSizeGB", "0.25"]
    )
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("--keyFile" in problema for problema in problemi), problemi


def test_uno_stack_senza_replica_non_pretende_il_keyfile():
    # La guardia che tiene verde lo stack 01, che gira senza autenticazione per
    # scelta didattica (ADR-0005). La regola si accende solo se QUALCUNO nel
    # file dichiara --replSet.
    problemi = verifica(conforme(), digest_noti={"sha256:aaa"})
    assert not any("--keyFile" in problema for problema in problemi), problemi


# Regola 3 — un servizio atteso «completato» deve poter morire.


def catena(**modifiche):
    """Un one-shot e un membro che lo attende, conformi."""
    uno_shot = {
        "image": "mongo@sha256:aaa",
        "pull_policy": "never",
        "mem_limit": "128m",
        "cpus": 0.25,
        "restart": "no",
        "command": ["sh", "-c", "echo fatto"],
    }
    uno_shot.update(modifiche)
    membro = {
        "image": "mongo@sha256:aaa",
        "pull_policy": "never",
        "mem_limit": "1024m",
        "cpus": 1.0,
        "command": ["mongod", "--wiredTigerCacheSizeGB", "0.25"],
        "depends_on": {"init": {"condition": "service_completed_successfully"}},
    }
    return {"services": {"init": uno_shot, "mongo": membro}}


def test_il_campione_di_catena_non_produce_problemi():
    assert verifica(catena(), digest_noti={"sha256:aaa"}) == []


def test_un_one_shot_atteso_come_completato_senza_restart_no_e_un_problema():
    # Con `unless-stopped` Compose rialza il container appena esce, la
    # condizione `service_completed_successfully` non diventa mai vera, e lo
    # stack resta fermo a metà senza un errore che lo dica.
    documento = catena(restart="unless-stopped")
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("restart" in problema for problema in problemi), problemi


def test_un_one_shot_atteso_come_completato_senza_chiave_restart_e_un_problema():
    documento = catena()
    del documento["services"]["init"]["restart"]
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("restart" in problema for problema in problemi), problemi


# Regola 4 — la condizione deve corrispondere al genere di servizio atteso.


def test_attendere_un_mongod_con_service_started_e_un_problema():
    # `service_started` scatta mentre l'entrypoint è ancora nella fase del
    # mongod temporaneo: misurato al Task 1, ECONNREFUSED al primo colpo.
    documento = replica()
    documento["services"]["mongo-rs-2"]["depends_on"] = {
        "mongo-rs-1": {"condition": "service_started"}
    }
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("service_healthy" in problema for problema in problemi), problemi


def test_attendere_un_one_shot_con_service_started_e_un_problema():
    documento = catena()
    documento["services"]["mongo"]["depends_on"] = {
        "init": {"condition": "service_started"}
    }
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any(
        "service_completed_successfully" in problema for problema in problemi
    ), problemi


# Il difetto vecchio: due scritture equivalenti, una sola riconosciuta.


def test_un_comando_che_comincia_per_trattino_avvia_comunque_mongod():
    # L'entrypoint ufficiale antepone `mongod` da sé quando il primo argomento
    # comincia per trattino (S-022): per Docker le due forme avviano lo stesso
    # processo. Finché lo strumento ne riconosceva una sola, la regola sulla
    # cache non poteva fallire sull'altra — misurato al Task 3.
    documento = conforme(command=["--replSet", "rs0", "--bind_ip_all"])
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("wiredTigerCacheSizeGB" in problema for problema in problemi), problemi


def test_una_stringa_che_comincia_per_trattino_avvia_comunque_mongod():
    documento = conforme(command="--replSet rs0 --bind_ip_all")
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert any("wiredTigerCacheSizeGB" in problema for problema in problemi), problemi


def test_un_comando_che_non_e_mongod_resta_fuori_dalla_regola():
    # Il bersaglio della regola sono i processi che hanno storage: pretendere
    # una cache da `mongos` o da una shell sarebbe una regola che sbaglia mira.
    documento = conforme(command=["sh", "-c", "echo fatto"])
    problemi = verifica(documento, digest_noti={"sha256:aaa"})
    assert not any("wiredTigerCacheSizeGB" in problema for problema in problemi), problemi


# --- Task 6: l'ambiente si passa come lo passa Compose ----------------------

DIGEST_PINNATO = (
    "mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b"
)


def test_il_secondo_file_di_ambiente_viene_davvero_letto(tmp_path, capsys):
    # Lo stack 02 si avvia con due `--env-file` (ADR-0041): lo strumento che lo
    # controlla deve poter ricevere gli stessi due file, o controlla un file
    # diverso da quello che verrà avviato. La prova che il secondo sia letto non
    # può essere un verde — un verde lo darebbe anche ignorandolo. È un rosso:
    # il secondo file stringe la memoria sotto la cache, e la regola scatta.
    immagini = tmp_path / "images.env"
    immagini.write_text(f"MONGO_IMAGE={DIGEST_PINNATO}\n", encoding="utf-8")
    stack = tmp_path / "stack.env"
    stack.write_text("MEMORIA=128m\n", encoding="utf-8")
    compose = tmp_path / "compose.yaml"
    compose.write_text(COMPOSE_CONFORME, encoding="utf-8")

    assert main(["--ambiente", str(immagini), str(compose)]) == 0

    # Non basta guardare il codice di uscita: tenendo solo l'ultimo file lo
    # strumento uscirebbe 1 lo stesso, ma per «manca image». Il messaggio
    # distingue «ho letto tutti e due i file» da «ne ho letto uno».
    assert (
        main(["--ambiente", str(immagini), "--ambiente", str(stack), str(compose)]) == 1
    )
    errori = capsys.readouterr().err
    assert "wiredTigerCacheSizeGB" in errori, errori
    assert "image" not in errori, errori


def test_l_ultimo_file_di_ambiente_vince_sul_primo(tmp_path):
    # «Later files can override variables from earlier files» (S-056): lo
    # strumento fonde nello stesso ordine, o direbbe una cosa e Compose un'altra.
    # Il primo file porta due variabili, il secondo ne corregge una sola: se lo
    # strumento tenesse solo l'ultimo file, la variabile obbligatoria che sta
    # nel primo sparirebbe e l'esito sarebbe 2, non 0.
    primo = tmp_path / "primo.env"
    primo.write_text(
        "MONGO_IMAGE=mongo:7.0.40\nMEMORIA_OBBLIGATORIA=1024m\n", encoding="utf-8"
    )
    secondo = tmp_path / "secondo.env"
    secondo.write_text(f"MONGO_IMAGE={DIGEST_PINNATO}\n", encoding="utf-8")
    compose = tmp_path / "compose.yaml"
    compose.write_text(
        COMPOSE_CONFORME.replace(
            "    mem_limit: ${MEMORIA:-1024m}\n",
            "    mem_limit: ${MEMORIA_OBBLIGATORIA:?assente}\n",
        ),
        encoding="utf-8",
    )

    assert main(["--ambiente", str(primo), str(compose)]) == 1
    assert main(["--ambiente", str(primo), "--ambiente", str(secondo), str(compose)]) == 0


def test_main_accetta_una_variabile_da_riga_di_comando(tmp_path):
    # Serve a controllare un file che dichiara `${NOME:?…}` senza avere il `.env`
    # vero: il `.env` dello stack 02 è ignorato da git, e `make stack-check` deve
    # funzionare su un clone appena fatto. Il valore passato qui non avvia
    # niente, serve solo a far interpolare il documento.
    immagini = tmp_path / "images.env"
    immagini.write_text(f"MONGO_IMAGE={DIGEST_PINNATO}\n", encoding="utf-8")
    compose = tmp_path / "compose.yaml"
    compose.write_text(
        COMPOSE_CONFORME.replace(
            "    mem_limit: ${MEMORIA:-1024m}\n",
            "    mem_limit: ${MEMORIA_OBBLIGATORIA:?assente}\n",
        ),
        encoding="utf-8",
    )

    assert main(["--ambiente", str(immagini), str(compose)]) == 2
    assert (
        main(
            [
                "--ambiente",
                str(immagini),
                "--variabile",
                "MEMORIA_OBBLIGATORIA=1024m",
                str(compose),
            ]
        )
        == 0
    )


def test_una_variabile_da_riga_di_comando_vince_sui_file(tmp_path):
    immagini = tmp_path / "images.env"
    immagini.write_text("MONGO_IMAGE=mongo:7.0.40\n", encoding="utf-8")
    compose = tmp_path / "compose.yaml"
    compose.write_text(COMPOSE_CONFORME, encoding="utf-8")

    assert (
        main(
            [
                "--ambiente",
                str(immagini),
                "--variabile",
                f"MONGO_IMAGE={DIGEST_PINNATO}",
                str(compose),
            ]
        )
        == 0
    )


def test_una_variabile_scritta_male_e_un_errore_d_uso(tmp_path, capsys):
    immagini = tmp_path / "images.env"
    immagini.write_text(f"MONGO_IMAGE={DIGEST_PINNATO}\n", encoding="utf-8")
    compose = tmp_path / "compose.yaml"
    compose.write_text(COMPOSE_CONFORME, encoding="utf-8")

    assert (
        main(["--ambiente", str(immagini), "--variabile", "SENZA_UGUALE", str(compose)])
        == 2
    )
    assert "SENZA_UGUALE" in capsys.readouterr().err
