"""`mongolab` — l'applicazione dimostrativa del lab MongoDB di SqlStart 2026.

Mostra ciò che vede un client e che `mongosh` non può mostrare: la scoperta della
topologia, la cronaca di un failover al millisecondo, e i due numeri che chiudono la
scena — durata dell'interruzione e scritture perse.

Le dipendenze puntano solo verso l'interno. `domain` e `application` non importano
alcuna libreria di terze parti, ed è la ragione per cui la suite unitaria gira in
millisecondi senza Docker acceso. La regola non è una convenzione: è verificata da
`tests/unit/test_scheletro.py`.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
