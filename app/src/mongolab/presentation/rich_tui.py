"""L'unico modulo del progetto che conosce Rich, e l'unico thread che disegna.

**La promessa e la sorpresa.** [ADR-0019](../../../../docs/Decision.md#adr-0019) dice «il
ciclo di disegno gira sul thread principale», e la ragione è che la documentazione di
Rich non nomina mai i thread ([S-018](../../../../docs/Sources.md#s-018)): di fronte a
una lacuna, il progetto ha cambiato disegno invece di indovinare. Scrivendo questo modulo
si è scoperto che con le impostazioni predefinite quella promessa **non sarebbe stata
mantenuta**: `Live(...)` avvia un `_RefreshThread` demone che chiama `refresh()` quattro
volte al secondo per conto suo ([M-027](../../../../app/docs/Sources.md#m-027)). Non è
insicuro — dentro `Live` c'è un `RLock` — ma è esattamente la condizione in cui il
progetto aveva deciso di non mettersi: sicurezza che dipende da un dettaglio non
documentato.

Da qui `auto_refresh=False` e il `refresh()` chiamato dal ciclo. Il prezzo, misurato, è
che in quella configurazione `refresh_per_second` diventa **inerte**: nessuno lo legge
più. Il numero quindi non si passa a `Live` per finta; vive nel periodo del ciclo, che è
il posto in cui agisce davvero.

**Che cosa resta qui dentro.** Un ciclo di cinque righe e un disegno. Tutto ciò che c'è
da provare — la coda, i conteggi, la cronaca, la riga di ogni evento — sta in `scena.py`
e in `righe.py`, che non importano Rich e hanno le loro prove.
"""

from contextlib import contextmanager
from typing import Callable, Iterator

from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.live import Live

from mongolab.domain.eventi import Evento
from mongolab.domain.porte import Clock
from mongolab.presentation.righe import (
    ALTEZZA_INTESTAZIONE,
    RIGHE_CRONACA,
    server_da_mostrare,
)
from mongolab.presentation.scena import Scena

__all__ = ["RITMO_PREDEFINITO", "RichTui"]

RITMO_PREDEFINITO = 10.0
"""Aggiornamenti al secondo, e il numero è scelto fra due costi che si guardano.

Verso il basso: il ritmo è anche il ritardo massimo fra un fatto e la sua comparsa. A
quattro al secondo — il valore che Rich userebbe da solo — una cronaca può aspettare 250
ms, e in una scena in cui i tempi *sono* il contenuto quel ritardo si vede.

Verso l'alto: ogni giro ridisegna la schermata intera, e chi disegna è lo stesso processo
che sta misurando il failover. Un disegno costa **0.76 ms** nel caso peggiore — tre server
e cronaca piena — misurati ([M-028](../../../../app/docs/Sources.md#m-028)): a dieci al
secondo è lo 0.8% di un core, a cento sarebbe il 7.6% speso per aggiornare un testo che
nessuno riesce a leggere a quella velocità.

Dieci al secondo: cento millisecondi di ritardo, l'un per cento e poco più di costo. Il
numero non è al centro di un intervallo stretto — fra quattro e venti al secondo cambia
poco tanto il ritardo quanto il costo — ed è scelto perché a dieci entrambi i lati
restano piccoli senza che nessuno dei due debba essere difeso.
"""


class RichTui:
    """La TUI: accetta eventi da chiunque, disegna da un thread solo.

    L'orologio arriva dalla porta e non da `time.sleep` per la stessa ragione per cui ci
    arriva ovunque: il tempo di questo progetto entra da un punto solo. Qui in più
    significa che il ritmo del disegno è **visibile** nel composition root, accanto a
    tutto il resto che si può regolare.
    """

    def __init__(
        self,
        orologio: Clock,
        *,
        console: Console | None = None,
        ritmo: float = RITMO_PREDEFINITO,
        righe_cronaca: int = RIGHE_CRONACA,
    ) -> None:
        if ritmo <= 0:
            raise ValueError(f"il ritmo è in aggiornamenti al secondo, ricevuto {ritmo}")
        self._orologio = orologio
        self._console = console if console is not None else Console()
        self._scena = Scena(righe_cronaca=righe_cronaca)
        self._periodo = 1.0 / ritmo
        self._live: Live | None = None

    # --- Il lato di chi produce --------------------------------------------------------

    def emit(self, evento: Evento) -> None:
        """Deposita e ritorna. Chi chiama può essere un thread qualunque."""
        self._scena.emit(evento)

    @property
    def in_coda(self) -> int:
        """Quanti eventi aspettano di essere disegnati.

        È il numero che dice se il disegno è rimasto indietro, e la schermata lo mostra
        quando non è zero. Fuori dalla schermata serve a una cosa sola, ma importante:
        rende **osservabile** che il ciclo ha finito di assorbire, e quindi verificabile
        senza guardare un pixel.
        """
        return self._scena.in_coda

    # --- Il lato di chi disegna: solo il thread che ha aperto `acceso` -----------------

    @contextmanager
    def acceso(self) -> Iterator["RichTui"]:
        """Apre il display e lo chiude, qualunque cosa accada nel mezzo.

        `auto_refresh=False` è la riga che tiene in piedi la promessa di ADR-0019, e
        `vertical_overflow="crop"` è quella che tiene la scena dentro lo schermo: senza,
        una schermata più alta del terminale scorrerebbe, e una TUI che scorre in sala
        non è più una TUI.
        """
        with Live(
            self._disegna(),
            console=self._console,
            auto_refresh=False,
            vertical_overflow="crop",
        ) as live:
            self._live = live
            try:
                yield self
            finally:
                self._live = None

    def aggiorna(self) -> int:
        """Un giro senza attesa: assorbe quello che c'è e ridisegna. Torna quanti."""
        assorbiti = self._scena.assorbi()
        if self._live is not None:
            self._live.update(self._disegna(), refresh=True)
        return assorbiti

    def giro(self) -> int:
        """Un giro completo, attesa compresa. È il passo del ciclo."""
        assorbiti = self.aggiorna()
        self._orologio.sleep(self._periodo)
        return assorbiti

    def esegui(self, finche: Callable[[], bool]) -> None:
        """Il ciclo di disegno, sul thread che lo chiama.

        L'ultimo `aggiorna` fuori dal ciclo non è pignoleria: senza, gli eventi arrivati
        fra l'ultimo giro e la fine non si vedrebbero mai — e fra quelli c'è sempre
        l'ultimo, che è quello che chiude la scena.
        """
        with self.acceso():
            while finche():
                self.giro()
            self.aggiorna()

    # --- Il disegno ---------------------------------------------------------------------

    def _disegna(self) -> RenderableType:
        return Group(self._intestazione(), self._cronaca())

    def _intestazione(self) -> RenderableType:
        """La topologia e i conteggi, in un pannello di altezza fissa.

        Fissa e non elastica: se il pannello crescesse con il numero di server, la
        cronaca si accorcerebbe da sola nel momento peggiore — quando il cluster si
        scompone e le righe da leggere sono tante.
        """
        return Panel(
            Group(self._server(), Rule(style="dim"), self._conteggi()),
            title=self._titolo(),
            height=ALTEZZA_INTESTAZIONE,
            padding=(0, 1),
        )

    def _titolo(self) -> str:
        topologia = self._scena.topologia
        if topologia is None:
            return "mongolab"
        nome = f" «{topologia.nome_set}»" if topologia.nome_set else ""
        return f"mongolab — {topologia.tipo.value}{nome}"

    def _server(self) -> RenderableType:
        topologia = self._scena.topologia
        if topologia is None:
            return Text("in attesa del primo sguardo sul cluster", style="dim")

        tabella = Table.grid(padding=(0, 2))
        tabella.add_column(justify="left")
        tabella.add_column(justify="left")
        tabella.add_column(justify="right")
        # Chi decide che cosa mostrare — e che cosa dire di quello che non mostra — è
        # `server_da_mostrare`, che non conosce Rich e ha le sue prove. Qui si disegna.
        for indirizzo, ruolo, ritardo in server_da_mostrare(topologia):
            tabella.add_row(indirizzo, ruolo, ritardo)
        return tabella

    def _conteggi(self) -> RenderableType:
        conteggi = self._scena.conteggi
        parti = [
            f"scritture {conteggi.scritture}",
            f"documenti {conteggi.documenti}",
            f"errori {conteggi.fallimenti}",
            f"ritenti {conteggi.ritentativi}",
        ]
        if conteggi.ultima_latenza_ms is not None:
            parti.append(f"ultima {conteggi.ultima_latenza_ms:.1f} ms")
        avanzamento = self._scena.avanzamento
        if avanzamento is not None:
            percentuale = avanzamento.percentuale
            quanto = "—" if percentuale is None else f"{percentuale:.1f}%"
            parti.append(f"{avanzamento.fase} {quanto}")
        # In coda si mostra solo se c'è: è il numero che dice che il disegno è rimasto
        # indietro, e se è zero occupa spazio per dire che va tutto bene.
        if self._scena.in_coda:
            parti.append(f"in coda {self._scena.in_coda}")
        return Text("   ".join(parti))

    def _cronaca(self) -> RenderableType:
        """Le righe, senza andare a capo: `righe.riga` le ha già tagliate a cento."""
        return Text("\n".join(self._scena.cronaca), no_wrap=True, overflow="ellipsis")
