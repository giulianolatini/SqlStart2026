"""La macchina a stati della topologia, provata senza aspettare.

Queste prove sono state scritte **prima** di `mongolab.application.topologia`. Il caso
che conta non è uno stato ma un passaggio — primario → nessun primario → primario
**diverso** — ed è la ragione per cui `FakeInspector` riceve una *sequenza* di topologie
invece di una sola: quel doppio è stato disegnato al Task 4 leggendo questo task.

**Tutto in millisecondi.** La regola del design è scritta in decine di secondi («dopo
30 s senza primario, smetti di ritentare»); qui la pazienza vale un secondo e
l'intervallo un quarto, il tempo lo decide `FakeClock`, e la suite dura centesimi. Senza
la porta `Clock` quella regola resterebbe una frase: nessuno mette in una suite veloce
una prova che aspetta mezzo minuto, e una prova che nessuno esegue non protegge niente.

**I valori attesi sono esatti, non tolleranze.** Ogni durata asserita qui si calcola a
mano dall'intervallo e dal numero di giri. Se un giorno una di queste asserzioni avesse
bisogno di un `pytest.approx`, vorrebbe dire che il tempo è rientrato dalla finestra.
"""

from datetime import UTC, datetime

import pytest

from mongolab.application.topologia import (
    Bilancio,
    Interruzione,
    TopologyWatcher,
)
from mongolab.domain.eventi import (
    Evento,
    PrimaryWaitAbandoned,
    ServerStateChanged,
    TopologyChanged,
)
from mongolab.domain.modelli import (
    DescrizioneServer,
    DescrizioneTopologia,
    RuoloServer,
    TipoTopologia,
)
from mongolab.domain.porte import Clock, ClusterInspector, EventSink

from tests.aiutanti import specie
from tests.doppi import FakeClock, FakeInspector, RecordingSink

ISTANTE = datetime(2026, 9, 18, 9, 30, 0, tzinfo=UTC)

PRIMARIO = RuoloServer.PRIMARIO
SECONDARIO = RuoloServer.SECONDARIO
IRRAGGIUNGIBILE = RuoloServer.IRRAGGIUNGIBILE
SCONOSCIUTO = RuoloServer.SCONOSCIUTO


def _rs(*ruoli: RuoloServer) -> DescrizioneTopologia:
    """Un replica set di tre nodi, `mongo-1`, `mongo-2`, `mongo-3`, con questi ruoli.

    Il tipo della topologia **si deduce dai ruoli** invece di essere un parametro: una
    prova che potesse dichiarare «replica set con primario» su una tupla senza primari
    verificherebbe la propria distrazione.
    """
    server = tuple(
        DescrizioneServer(indirizzo=f"mongo-{numero}:27017", ruolo=ruolo)
        for numero, ruolo in enumerate(ruoli, start=1)
    )
    tipo = (
        TipoTopologia.REPLICA_SET_CON_PRIMARIO
        if PRIMARIO in ruoli
        else TipoTopologia.REPLICA_SET_SENZA_PRIMARIO
    )
    return DescrizioneTopologia(tipo=tipo, server=server, nome_set="rs0")


SANO = _rs(PRIMARIO, SECONDARIO, SECONDARIO)
CADUTO = _rs(IRRAGGIUNGIBILE, SECONDARIO, SECONDARIO)
ELETTO = _rs(IRRAGGIUNGIBILE, PRIMARIO, SECONDARIO)
"""La scena del Blocco 2 in tre fotogrammi: sano, senza primario, primario diverso."""


def _osservatore(
    *topologie: DescrizioneTopologia,
    intervallo_ms: float = 250.0,
    pazienza_ms: float = 1000.0,
) -> tuple[TopologyWatcher, FakeInspector, FakeClock, RecordingSink]:
    ispettore = FakeInspector(topologie)
    orologio = FakeClock(ISTANTE)
    sink = RecordingSink()
    watcher = TopologyWatcher(
        ispettore,
        orologio,
        sink,
        intervallo_ms=intervallo_ms,
        pazienza_ms=pazienza_ms,
    )
    return watcher, ispettore, orologio, sink


# --- La prima occhiata -----------------------------------------------------------------


def test_la_prima_occhiata_non_e_un_cambiamento() -> None:
    """Il primo sguardo stabilisce il ricordo, e non racconta niente.

    Un `TopologyChanged` emesso qui direbbe che il client ha cambiato idea rispetto a
    un'idea che non aveva: sarebbe un fatto falso nella cronaca, e proprio in cima, dove
    chi legge stabilisce quanto fidarsi del resto.
    """
    watcher, _, _, sink = _osservatore(SANO)

    watcher.guarda()

    assert sink.eventi == []


def test_la_prima_occhiata_diventa_il_ricordo() -> None:
    watcher, _, _, _ = _osservatore(SANO)

    assert watcher.vista is None
    watcher.guarda()
    assert watcher.vista == SANO


def test_guarda_restituisce_quello_che_ha_visto() -> None:
    watcher, _, _, _ = _osservatore(SANO)

    assert watcher.guarda() == SANO


# --- I ruoli che cambiano --------------------------------------------------------------


def test_un_server_che_cambia_ruolo_produce_un_evento() -> None:
    watcher, _, _, sink = _osservatore(SANO, CADUTO)

    watcher.guarda()
    watcher.guarda()

    cambi = specie(sink.eventi, ServerStateChanged)
    assert len(cambi) == 1
    assert cambi[0].indirizzo == "mongo-1:27017"
    assert cambi[0].precedente is PRIMARIO
    assert cambi[0].successivo is IRRAGGIUNGIBILE


def test_i_server_che_non_cambiano_non_producono_niente() -> None:
    """Due secondari restano due secondari: la cronaca non lo ripete a ogni giro.

    È la differenza fra una cronaca e un campionamento. Un evento per ogni server a ogni
    giro sarebbe tecnicamente vero e illeggibile: durante il failover la riga che conta
    scorrerebbe via in mezzo a decine di righe che dicono «tutto uguale».
    """
    watcher, _, _, sink = _osservatore(SANO, CADUTO)

    watcher.guarda()
    watcher.guarda()

    indirizzi = [evento.indirizzo for evento in specie(sink.eventi, ServerStateChanged)]
    assert indirizzi == ["mongo-1:27017"]


def test_due_server_che_cambiano_producono_due_eventi_in_ordine_di_indirizzo() -> None:
    """L'ordine è per indirizzo, e apposta: quello delle descrizioni non è garantito.

    Le due tuple arrivano da due letture diverse del driver, e niente promette che i
    server compaiano nello stesso ordine. Ordinare per indirizzo rende la cronaca
    riproducibile — e questa prova ripetibile, invece che ripetibile *quasi sempre*.
    """
    prima = _rs(PRIMARIO, SECONDARIO, SECONDARIO)
    dopo = _rs(IRRAGGIUNGIBILE, PRIMARIO, SECONDARIO)
    watcher, _, _, sink = _osservatore(prima, dopo)

    watcher.guarda()
    watcher.guarda()

    cambi = specie(sink.eventi, ServerStateChanged)
    assert [evento.indirizzo for evento in cambi] == [
        "mongo-1:27017",
        "mongo-2:27017",
    ]


def test_l_ordine_non_dipende_da_come_il_driver_ha_elencato_i_server() -> None:
    """La prova che serviva davvero: qui le due letture elencano in ordine **opposto**.

    La prova sopra non basta, e lo si è scoperto rompendo il codice apposta: togliendo
    l'ordinamento restava verde, perché anche l'ordine di comparsa era alfabetico. Una
    guardia si prova solo con un caso in cui, se non ci fosse, si vedrebbe.
    """
    prima = DescrizioneTopologia(
        tipo=TipoTopologia.REPLICA_SET_CON_PRIMARIO,
        server=(
            DescrizioneServer(indirizzo="mongo-2:27017", ruolo=SECONDARIO),
            DescrizioneServer(indirizzo="mongo-1:27017", ruolo=PRIMARIO),
        ),
        nome_set="rs0",
    )
    dopo = DescrizioneTopologia(
        tipo=TipoTopologia.REPLICA_SET_CON_PRIMARIO,
        server=(
            DescrizioneServer(indirizzo="mongo-2:27017", ruolo=PRIMARIO),
            DescrizioneServer(indirizzo="mongo-1:27017", ruolo=IRRAGGIUNGIBILE),
        ),
        nome_set="rs0",
    )
    watcher, _, _, sink = _osservatore(prima, dopo)

    watcher.guarda()
    watcher.guarda()

    cambi = specie(sink.eventi, ServerStateChanged)
    assert [evento.indirizzo for evento in cambi] == [
        "mongo-1:27017",
        "mongo-2:27017",
    ]


def test_un_server_nuovo_arriva_da_sconosciuto() -> None:
    """Un nodo che il client non aveva mai visto: prima non era irraggiungibile, era ignoto."""
    prima = _rs(PRIMARIO, SECONDARIO)
    dopo = _rs(PRIMARIO, SECONDARIO, SECONDARIO)
    watcher, _, _, sink = _osservatore(prima, dopo)

    watcher.guarda()
    watcher.guarda()

    cambi = specie(sink.eventi, ServerStateChanged)
    assert len(cambi) == 1
    assert cambi[0].indirizzo == "mongo-3:27017"
    assert cambi[0].precedente is SCONOSCIUTO
    assert cambi[0].successivo is SECONDARIO


def test_un_server_sparito_torna_sconosciuto() -> None:
    """Sparire dalla descrizione non è essere irraggiungibile: è non saperne più niente.

    La distinzione non è un cavillo. `IRRAGGIUNGIBILE` è un'osservazione — il client ha
    provato e non è riuscito; `SCONOSCIUTO` è l'assenza di un'osservazione. Scriverne una
    al posto dell'altra mette in cronaca un tentativo che nessuno ha fatto.
    """
    prima = _rs(PRIMARIO, SECONDARIO, SECONDARIO)
    dopo = _rs(PRIMARIO, SECONDARIO)
    watcher, _, _, sink = _osservatore(prima, dopo)

    watcher.guarda()
    watcher.guarda()

    cambi = specie(sink.eventi, ServerStateChanged)
    assert len(cambi) == 1
    assert cambi[0].indirizzo == "mongo-3:27017"
    assert cambi[0].precedente is SECONDARIO
    assert cambi[0].successivo is SCONOSCIUTO


# --- La forma dell'insieme -------------------------------------------------------------


def test_il_cambio_di_forma_produce_un_topology_changed() -> None:
    watcher, _, _, sink = _osservatore(SANO, CADUTO)

    watcher.guarda()
    watcher.guarda()

    cambi = specie(sink.eventi, TopologyChanged)
    assert len(cambi) == 1
    assert cambi[0].precedente.tipo is TipoTopologia.REPLICA_SET_CON_PRIMARIO
    assert cambi[0].successiva.tipo is TipoTopologia.REPLICA_SET_SENZA_PRIMARIO


def test_topology_changed_porta_entrambe_le_descrizioni_intere() -> None:
    """Non solo il tipo: le due descrizioni per intero.

    È la promessa scritta nella docstring dell'evento — «senza la precedente, chi legge
    la cronaca vede dove si è arrivati e non da dove» — e questa prova la tiene onesta.
    """
    watcher, _, _, sink = _osservatore(SANO, CADUTO)

    watcher.guarda()
    watcher.guarda()

    cambio = specie(sink.eventi, TopologyChanged)[0]
    assert cambio.precedente == SANO
    assert cambio.successiva == CADUTO


def test_una_topologia_identica_non_produce_niente() -> None:
    """Il confronto è sul valore, e le descrizioni sono congelate: due letture uguali sono
    la stessa cosa detta due volte."""
    watcher, _, _, sink = _osservatore(SANO, SANO, SANO)

    watcher.guarda()
    watcher.guarda()
    watcher.guarda()

    assert sink.eventi == []


def test_i_dettagli_precedono_il_riepilogo() -> None:
    """Prima i server, poi la forma: la forma è la conseguenza, e si legge dopo la causa."""
    watcher, _, _, sink = _osservatore(SANO, CADUTO)

    watcher.guarda()
    watcher.guarda()

    assert [type(evento) for evento in sink.eventi] == [
        ServerStateChanged,
        TopologyChanged,
    ]


def test_gli_eventi_portano_l_istante_dell_orologio() -> None:
    watcher, _, orologio, sink = _osservatore(SANO, CADUTO)

    watcher.guarda()
    orologio.avanza(0.4)
    watcher.guarda()

    assert [evento.istante for evento in sink.eventi] == [orologio.now()] * 2


# --- Il failover: i tre fotogrammi -----------------------------------------------------


def test_il_failover_apre_e_chiude_un_interruzione() -> None:
    watcher, _, _, _ = _osservatore(SANO, CADUTO, ELETTO)

    watcher.guarda()
    assert watcher.interruzione is None

    watcher.guarda()
    aperta = watcher.interruzione
    assert aperta is not None
    assert not aperta.chiusa

    watcher.guarda()
    chiusa = watcher.interruzione
    assert chiusa is not None
    assert chiusa.chiusa


def test_l_interruzione_ricorda_i_due_primari() -> None:
    watcher, _, _, _ = _osservatore(SANO, CADUTO, ELETTO)

    watcher.guarda()
    watcher.guarda()
    watcher.guarda()

    interruzione = watcher.interruzione
    assert interruzione is not None
    assert interruzione.primario_prima == "mongo-1:27017"
    assert interruzione.primario_dopo == "mongo-2:27017"
    assert interruzione.e_un_failover


def test_lo_stesso_primario_che_torna_non_e_un_failover() -> None:
    """Un'interruzione c'è stata, un'elezione no.

    Distinguerle non è pedanteria da slide: «il primario è tornato» e «ne è stato eletto
    un altro» sono due scene diverse, e la seconda è quella che il Blocco 2 esiste per
    mostrare. Un riavvio veloce del nodo produce la prima.
    """
    watcher, _, _, _ = _osservatore(SANO, CADUTO, SANO)

    watcher.guarda()
    watcher.guarda()
    watcher.guarda()

    interruzione = watcher.interruzione
    assert interruzione is not None
    assert interruzione.chiusa
    assert interruzione.primario_dopo == "mongo-1:27017"
    assert not interruzione.e_un_failover


def test_un_interruzione_aperta_non_ha_durata() -> None:
    """`None`, non zero.

    Uno zero qui direbbe «l'interruzione è durata niente» dove la verità è «non è ancora
    finita», ed è la peggiore risposta mancante perché ha la faccia di una misura. È la
    stessa regola per cui il riepilogo del carico porta `latenze=None` quando nessuna
    scrittura è riuscita (nota di metodo 155).
    """
    watcher, _, _, _ = _osservatore(SANO, CADUTO)

    watcher.guarda()
    watcher.guarda()

    interruzione = watcher.interruzione
    assert interruzione is not None
    assert interruzione.durata_ms is None


def test_un_interruzione_che_non_si_e_vista_cominciare_non_si_misura() -> None:
    """Il client che arriva a primario già caduto non sa da quando: e non lo inventa.

    Aprire l'interruzione al primo sguardo produrrebbe una durata più corta del vero, e
    più è tardi che si guarda più corta viene — cioè un numero che sbaglia **verso il
    rassicurante**. Meglio nessuna misura di una misura ottimista.
    """
    watcher, _, _, _ = _osservatore(CADUTO, ELETTO)

    watcher.guarda()
    watcher.guarda()

    assert watcher.interruzione is None


def test_la_durata_e_esatta_perche_l_orologio_e_finto() -> None:
    watcher, _, orologio, _ = _osservatore(SANO, CADUTO, CADUTO, ELETTO)

    watcher.guarda()
    orologio.avanza(0.25)
    watcher.guarda()
    orologio.avanza(0.25)
    watcher.guarda()
    orologio.avanza(0.25)
    watcher.guarda()

    interruzione = watcher.interruzione
    assert interruzione is not None
    assert interruzione.durata_ms == 500.0


def test_un_interruzione_chiusa_non_si_allunga_a_ogni_sguardo() -> None:
    """Chiusa è chiusa: gli sguardi che seguono non spostano la fine.

    Senza questa prova la misura crescerebbe finché qualcuno guarda, e il numero
    sbaglierebbe **verso lo spettacolare** — l'errore opposto a quello che si teme di
    solito, e più difficile da notare proprio perché la slide ne guadagna.
    """
    watcher, _, orologio, _ = _osservatore(SANO, CADUTO, ELETTO)

    watcher.guarda()
    orologio.avanza(0.25)
    watcher.guarda()
    orologio.avanza(0.25)
    watcher.guarda()
    orologio.avanza(1.0)
    watcher.guarda()

    interruzione = watcher.interruzione
    assert interruzione is not None
    assert interruzione.durata_ms == 250.0
    assert interruzione.primario_dopo == "mongo-2:27017"


def test_un_secondo_guasto_apre_un_interruzione_nuova() -> None:
    """Due failover di fila: il secondo si misura da sé, non dal primo."""
    ricaduto = _rs(IRRAGGIUNGIBILE, IRRAGGIUNGIBILE, SECONDARIO)
    watcher, _, orologio, _ = _osservatore(SANO, CADUTO, ELETTO, ricaduto)

    watcher.guarda()
    orologio.avanza(0.25)
    watcher.guarda()
    orologio.avanza(0.25)
    watcher.guarda()
    orologio.avanza(0.25)
    watcher.guarda()

    interruzione = watcher.interruzione
    assert interruzione is not None
    assert not interruzione.chiusa
    assert interruzione.primario_prima == "mongo-2:27017"


# --- `segui`: i giri, le attese, le uscite ---------------------------------------------


def test_segui_interroga_una_volta_per_giro() -> None:
    watcher, ispettore, _, _ = _osservatore(SANO, SANO, SANO)

    watcher.segui(giri=3)

    assert ispettore.letture == 3


def test_segui_attende_fra_un_giro_e_l_altro_ma_non_dopo_l_ultimo() -> None:
    """Tre sguardi, due attese. L'attesa dopo l'ultimo sguardo non serve a nessuno, e in
    una demo dal vivo sarebbe un quarto di secondo di schermo fermo alla fine di ogni
    scena."""
    watcher, _, orologio, _ = _osservatore(SANO, SANO, SANO)

    watcher.segui(giri=3)

    assert orologio.attese == [0.25, 0.25]


def test_segui_si_ferma_quando_il_failover_si_chiude() -> None:
    """Il limite di giri è generoso: a fermarla è il fatto, non il conteggio."""
    watcher, ispettore, _, _ = _osservatore(SANO, CADUTO, ELETTO)

    interruzione = watcher.segui(giri=100)

    assert ispettore.letture == 3
    assert interruzione is not None
    assert interruzione.chiusa
    assert interruzione.durata_ms == 250.0


def test_segui_senza_niente_da_raccontare_restituisce_niente() -> None:
    watcher, _, _, sink = _osservatore(SANO, SANO)

    assert watcher.segui(giri=2) is None
    assert sink.eventi == []


def test_segui_non_restituisce_il_failover_della_corsa_precedente() -> None:
    """Chi richiama `segui` chiede notizie nuove, non la ripetizione delle vecchie.

    Restituire l'interruzione già chiusa fermerebbe il ciclo al primo giro, per sempre:
    l'osservatore smetterebbe di guardare senza dirlo a nessuno, che è il modo peggiore
    di smettere — la resa almeno lo annuncia.
    """
    watcher, ispettore, _, _ = _osservatore(SANO, CADUTO, ELETTO)

    primo = watcher.segui(giri=100)
    letture_del_primo = ispettore.letture
    secondo = watcher.segui(giri=2)

    assert primo is not None and primo.chiusa
    assert secondo is None
    assert ispettore.letture == letture_del_primo + 2


def test_segui_vuole_almeno_un_giro() -> None:
    watcher, _, _, _ = _osservatore(SANO)

    with pytest.raises(ValueError, match="giri"):
        watcher.segui(giri=0)


# --- La pazienza che finisce -----------------------------------------------------------


def test_senza_primario_oltre_la_pazienza_smette_di_guardare() -> None:
    """Sei letture su cento giri concessi: ha smesso perché ha deciso, non perché è finito.

    Il conto si fa a mano, ed è il motivo per cui questa prova vale. L'interruzione si
    apre alla seconda lettura, a 250 ms; da lì servono quattro intervalli per arrivare a
    1000 ms di attesa, cioè la lettura numero sei.
    """
    watcher, ispettore, _, _ = _osservatore(SANO, CADUTO, pazienza_ms=1000.0)

    watcher.segui(giri=100)

    assert ispettore.letture == 6
    assert watcher.pazienza_esaurita


def test_la_pazienza_non_scade_un_giro_prima() -> None:
    """«Smette quando deve e **non** prima»: un millisecondo di pazienza in più è un giro
    in più."""
    watcher, ispettore, _, _ = _osservatore(SANO, CADUTO, pazienza_ms=1001.0)

    watcher.segui(giri=100)

    assert ispettore.letture == 7


def test_smettendo_lo_dice_con_un_evento() -> None:
    """La resa è un fatto, e i fatti di questa applicazione si raccontano emettendo.

    Nessuno degli otto eventi del §6.3 sapeva dirlo: `WriteFailed` parla di una scrittura
    che qui nessuno ha tentato, `RetryAttempted` annuncia un tentativo che non ci sarà.
    Il nono evento è arrivato con ADR-0082, e questa è la prova che lo ha chiesto.
    """
    watcher, _, _, sink = _osservatore(SANO, CADUTO, pazienza_ms=1000.0)

    watcher.segui(giri=100)

    rese = specie(sink.eventi, PrimaryWaitAbandoned)
    assert len(rese) == 1


def test_la_resa_dice_quanto_ha_aspettato_e_quanta_pazienza_aveva() -> None:
    """Entrambi i numeri, perché il secondo è la sola cosa che rende leggibile il primo."""
    watcher, _, _, sink = _osservatore(SANO, CADUTO, pazienza_ms=1000.0)

    watcher.segui(giri=100)

    resa = specie(sink.eventi, PrimaryWaitAbandoned)[0]
    assert resa.atteso_ms == 1000.0
    assert resa.pazienza_ms == 1000.0
    assert resa.ultimo_primario == "mongo-1:27017"


def test_la_resa_e_l_ultimo_evento_della_cronaca() -> None:
    """Dopo la resa non si racconta più niente: chi ha smesso di guardare non ha notizie."""
    watcher, _, _, sink = _osservatore(SANO, CADUTO, pazienza_ms=1000.0)

    watcher.segui(giri=100)

    assert isinstance(sink.eventi[-1], PrimaryWaitAbandoned)


def test_un_primario_che_torna_prima_della_pazienza_non_fa_scattare_la_resa() -> None:
    watcher, _, _, sink = _osservatore(SANO, CADUTO, CADUTO, ELETTO, pazienza_ms=1000.0)

    watcher.segui(giri=100)

    assert specie(sink.eventi, PrimaryWaitAbandoned) == []
    assert not watcher.pazienza_esaurita


def test_dopo_la_resa_non_riprende_a_guardare() -> None:
    """Chiamare `segui` di nuovo non riapre gli occhi: la resa è uno stato, non un giro
    andato male. Riprendere richiede un `TopologyWatcher` nuovo, cioè una decisione di chi
    chiama."""
    watcher, ispettore, _, _ = _osservatore(SANO, CADUTO, pazienza_ms=1000.0)

    watcher.segui(giri=100)
    letture_alla_resa = ispettore.letture
    watcher.segui(giri=100)

    assert ispettore.letture == letture_alla_resa


def test_la_resa_non_chiude_l_interruzione() -> None:
    """Aver smesso di aspettare non vuol dire che sia finita: la durata resta `None`."""
    watcher, _, _, _ = _osservatore(SANO, CADUTO, pazienza_ms=1000.0)

    watcher.segui(giri=100)

    interruzione = watcher.interruzione
    assert interruzione is not None
    assert not interruzione.chiusa
    assert interruzione.durata_ms is None


def test_dopo_un_failover_la_pazienza_riparte_da_zero() -> None:
    """Il guasto è finito, e con lui il conto dell'attesa.

    Se l'istante in cui il primario è sparito non venisse dimenticato quando torna,
    l'osservatore si arrenderebbe più tardi guardando un cluster **sano**: una resa
    annunciata a schermo mentre a schermo c'è un primario, cioè la cronaca che smentisce
    sé stessa.
    """
    watcher, _, _, sink = _osservatore(SANO, CADUTO, ELETTO, pazienza_ms=1000.0)

    watcher.segui(giri=100)
    watcher.segui(giri=20)

    assert specie(sink.eventi, PrimaryWaitAbandoned) == []
    assert not watcher.pazienza_esaurita


# --- I due numeri che giustificano l'applicazione --------------------------------------


def test_le_scritture_perse_sono_le_confermate_meno_le_ritrovate() -> None:
    watcher, _, _, _ = _osservatore(SANO, CADUTO, ELETTO)
    watcher.segui(giri=100)

    bilancio = watcher.bilancio(confermate=1200, ritrovate=1183)

    assert bilancio.scritture_perse == 17


def test_ritrovare_piu_del_confermato_non_e_una_perdita_negativa() -> None:
    """L'altro esito del failover, che non ha un nome sulle slide e ne meriterebbe uno.

    Una scrittura può essere applicata dal server e non confermata al client — la
    conferma si perde per strada mentre il primario cade. Chiamarla «meno diciassette
    perse» sarebbe aritmetica sensata e cronaca sbagliata: sono due fenomeni opposti, e
    il riepilogo li tiene su due numeri, entrambi non negativi.
    """
    watcher, _, _, _ = _osservatore(SANO)
    watcher.guarda()

    bilancio = watcher.bilancio(confermate=1183, ritrovate=1200)

    assert bilancio.scritture_perse == 0
    assert bilancio.scritture_non_confermate == 17


def test_il_bilancio_porta_la_durata_dell_interruzione() -> None:
    watcher, _, _, _ = _osservatore(SANO, CADUTO, ELETTO)
    watcher.segui(giri=100)

    bilancio = watcher.bilancio(confermate=10, ritrovate=10)

    assert bilancio.durata_interruzione_ms == 250.0


def test_il_bilancio_di_un_cluster_che_non_e_mai_caduto_non_ha_durata() -> None:
    watcher, _, _, _ = _osservatore(SANO, SANO)
    watcher.segui(giri=2)

    bilancio = watcher.bilancio(confermate=10, ritrovate=10)

    assert bilancio.interruzione is None
    assert bilancio.durata_interruzione_ms is None


def test_i_conteggi_negativi_non_sono_un_bilancio() -> None:
    watcher, _, _, _ = _osservatore(SANO)

    with pytest.raises(ValueError, match="negativ"):
        watcher.bilancio(confermate=-1, ritrovate=0)


# --- Le porte --------------------------------------------------------------------------


def test_l_osservatore_parla_solo_attraverso_le_porte() -> None:
    """Le annotazioni sono la prova: è `mypy --strict` a eseguirla davvero."""
    ispettore: ClusterInspector = FakeInspector([SANO])
    orologio: Clock = FakeClock(ISTANTE)
    sink: EventSink = RecordingSink()

    watcher = TopologyWatcher(ispettore, orologio, sink)
    vista: DescrizioneTopologia = watcher.guarda()

    assert vista == SANO


def test_l_intervallo_e_la_pazienza_devono_essere_positivi() -> None:
    """Un intervallo di zero è un ciclo che gira a vuoto contro il driver; una pazienza di
    zero è una resa prima ancora di guardare."""
    ispettore = FakeInspector([SANO])

    with pytest.raises(ValueError, match="intervallo"):
        TopologyWatcher(ispettore, FakeClock(ISTANTE), RecordingSink(), intervallo_ms=0.0)

    with pytest.raises(ValueError, match="pazienza"):
        TopologyWatcher(ispettore, FakeClock(ISTANTE), RecordingSink(), pazienza_ms=0.0)


def test_l_interruzione_e_congelata() -> None:
    """Attraversa la coda come gli eventi, e per la stessa ragione non si tocca."""
    interruzione = Interruzione(inizio=ISTANTE, primario_prima="mongo-1:27017")

    with pytest.raises(AttributeError):
        interruzione.fine = ISTANTE  # type: ignore[misc]


def test_il_bilancio_e_congelato() -> None:
    bilancio = Bilancio(interruzione=None, confermate=0, ritrovate=0)

    with pytest.raises(AttributeError):
        bilancio.confermate = 1  # type: ignore[misc]


def test_gli_eventi_emessi_sono_solo_quelli_del_dominio() -> None:
    """Nessuna specie di comodo: ciò che esce dal sink sta in `domain/eventi.py`."""
    watcher, _, _, sink = _osservatore(SANO, CADUTO, ELETTO)

    watcher.segui(giri=100)

    assert sink.eventi
    assert all(isinstance(evento, Evento) for evento in sink.eventi)
