"""L'ispettore che restituisce topologie preparate dalla prova."""

from typing import Mapping, Sequence

from mongolab.domain.modelli import DescrizioneTopologia, Distribuzione

__all__ = ["FakeInspector"]


class FakeInspector:
    """Un `ClusterInspector` che dice ciò che la prova ha deciso che il client vede.

    **Una sequenza, non un valore.** Ciò che il Task 6 deve provare non è uno stato ma un
    passaggio: primario → nessun primario → primario **diverso**. Un doppio che
    restituisse sempre la stessa topologia potrebbe far provare «come sta il cluster» e
    mai «che cosa è appena successo», che è l'unica delle due cose che il talk mostra.

    **Finite le topologie resta sull'ultima**, invece di sollevare. Quante volte il
    `TopologyWatcher` interrogherà dipende dalla sua politica di attesa, cioè è
    esattamente ciò che la prova sta verificando: un doppio che si esaurisse farebbe
    fallire la prova per il numero di giri e non per il comportamento, e chi la legge
    aggiusterebbe il numero di topologie finché il rosso sparisce — adattando la prova al
    doppio invece che al contrario.

    **`letture` è un'asserzione, non un contatore di servizio.** «Smette di ritentare» si
    verifica anche mostrando che ha smesso di guardare.

    I documenti di `serverStatus` e `dbStats` partono vuoti, e la distribuzione di una
    collezione di cui nessuno ha detto niente è quella di chi non sta in uno sharded
    cluster: un doppio che di suo restituisse due shard plausibili farebbe passare la
    scena del Blocco 3 contro un replica set.

    **Le distribuzioni sono una mappa per nome**, perché dopo ADR-0104 la domanda è per
    collezione e la scena del Blocco 3 ne accosta due dello stesso cluster. Un doppio che
    rispondesse la stessa cosa a tutte e due renderebbe le due colonne identiche per
    costruzione, cioè farebbe passare una scena in cui non c'è niente da vedere.

    **E per ogni nome una sequenza, non un valore**, per la stessa ragione delle topologie
    scritta più sopra: la scena dello sharding guarda la stessa collezione due volte, prima
    e dopo il carico, e ciò che mostra è la differenza. Un doppio con una risposta sola per
    collezione renderebbe le due fotografie identiche per costruzione, cioè proverebbe che
    il codice guarda e mai che accosta. Anche qui, finite le risposte si resta sull'ultima.

    Ciò che questo doppio **non** sa ancora fare è fallire: un cluster irraggiungibile si
    racconta qui con una topologia senza primario, non con un'eccezione. Il giorno in cui
    una prova avrà bisogno di un `topology()` che solleva, l'iniezione dell'errore arriva
    insieme a quella prova.
    """

    def __init__(
        self,
        topologie: Sequence[DescrizioneTopologia],
        server_status: Mapping[str, object] | None = None,
        db_stats: Mapping[str, object] | None = None,
        distribuzioni: Mapping[str, Sequence[Distribuzione]] | None = None,
    ) -> None:
        if not topologie:
            raise ValueError(
                "un FakeInspector vuole almeno una topologia: senza, non c'è niente da "
                "restituire e l'errore si vedrebbe lontano da dove è stato commesso."
            )
        self._topologie = tuple(topologie)
        self._server_status = dict(server_status or {})
        self._db_stats = dict(db_stats or {})
        self._distribuzioni = {
            nome: tuple(risposte) for nome, risposte in (distribuzioni or {}).items()
        }
        self.letture = 0
        """Quante volte `topology()` è stato chiamato."""
        self.distribuzioni_chieste: list[str] = []
        """Di quali collezioni è stata chiesta la distribuzione, nell'ordine e con le
        ripetizioni. «Prima e dopo sono due letture» si verifica anche così."""

    def topology(self) -> DescrizioneTopologia:
        indice = min(self.letture, len(self._topologie) - 1)
        self.letture += 1
        return self._topologie[indice]

    def server_status(self) -> Mapping[str, object]:
        return self._server_status

    def db_stats(self) -> Mapping[str, object]:
        return self._db_stats

    def shard_distribution(self, collezione: str) -> Distribuzione:
        preparate = self._distribuzioni.get(collezione)
        quante = self.distribuzioni_chieste.count(collezione)
        self.distribuzioni_chieste.append(collezione)
        if preparate:
            return preparate[min(quante, len(preparate) - 1)]
        # Non un'eccezione: «di questa collezione non so niente» e «questo non è uno
        # sharded cluster» danno lo stesso schermo, ed è quello che la porta descrive.
        return Distribuzione(
            collezione=collezione, distribuita=False, primario=None, conti=()
        )
