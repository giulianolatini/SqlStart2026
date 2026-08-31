import pytest

from check_stack import carica, digest_noti_da, leggi_ambiente, main, risolvi, verifica


def conforme(**modifiche):
    """Un servizio che rispetta tutte le regole, da rompere una alla volta.

    I test negativi partono da qui e cambiano una cosa sola: così il problema
    segnalato è attribuibile alla modifica e non a un difetto del campione.
    """
    servizio = {
        "image": "mongo@sha256:aaa",
        "pull_policy": "missing",
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
        "pull_policy": "missing",
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
        "pull_policy": "missing",
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
        "pull_policy": "missing",
        "mem_limit": "128m",
        "cpus": 0.5,
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
    pull_policy: ${PULL_POLICY:-missing}
    mem_limit: 1024m
    cpus: 1.0
    command: [mongod, --wiredTigerCacheSizeGB, "0.25"]
"""


def test_carica_risolve_le_variabili_dentro_il_documento(tmp_path):
    percorso = tmp_path / "compose.yaml"
    percorso.write_text(COMPOSE_CONFORME, encoding="utf-8")
    documento = carica(percorso, {"MONGO_IMAGE": "mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b"})
    servizio = documento["services"]["mongo"]
    assert servizio["image"] == "mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b"
    assert servizio["pull_policy"] == "missing"


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
        COMPOSE_CONFORME.replace("    mem_limit: 1024m\n", ""), encoding="utf-8"
    )
    assert main(["--ambiente", str(ambiente), str(compose)]) == 1
    assert "compose.yaml" in capsys.readouterr().err


def test_main_esce_due_con_un_messaggio_se_il_file_non_esiste(tmp_path, capsys):
    ambiente = tmp_path / "images.env"
    ambiente.write_text("MONGO_IMAGE=mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b\n", encoding="utf-8")
    assert main(["--ambiente", str(ambiente), str(tmp_path / "assente.yaml")]) == 2
    assert "assente.yaml" in capsys.readouterr().err
