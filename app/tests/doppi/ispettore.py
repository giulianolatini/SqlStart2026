"""L'ispettore che restituisce topologie preparate dalla prova."""

from typing import Mapping, Sequence

from mongolab.domain.modelli import ContoShard, DescrizioneTopologia

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

    I documenti di `serverStatus` e `dbStats` partono vuoti e la distribuzione degli shard
    parte vuota, come dice la porta per ciò che non è uno sharded cluster: un doppio che
    di suo restituisse due shard plausibili farebbe passare la scena del Blocco 3 contro
    un replica set.

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
        distribuzione: Sequence[ContoShard] = (),
    ) -> None:
        if not topologie:
            raise ValueError(
                "un FakeInspector vuole almeno una topologia: senza, non c'è niente da "
                "restituire e l'errore si vedrebbe lontano da dove è stato commesso."
            )
        self._topologie = tuple(topologie)
        self._server_status = dict(server_status or {})
        self._db_stats = dict(db_stats or {})
        self._distribuzione = tuple(distribuzione)
        self.letture = 0
        """Quante volte `topology()` è stato chiamato."""

    def topology(self) -> DescrizioneTopologia:
        indice = min(self.letture, len(self._topologie) - 1)
        self.letture += 1
        return self._topologie[indice]

    def server_status(self) -> Mapping[str, object]:
        return self._server_status

    def db_stats(self) -> Mapping[str, object]:
        return self._db_stats

    def shard_distribution(self) -> tuple[ContoShard, ...]:
        return self._distribuzione
