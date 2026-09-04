"""Il nucleo: porte, eventi e modelli. Non importa nulla di terze parti.

Le porte sono `typing.Protocol`, quindi un doppio le soddisfa perché ha i metodi
giusti — senza ereditarietà, e con `mypy --strict` a verificarlo. Gli eventi sono
congelati perché nascono dentro un callback di pymongo e vengono letti dal thread
principale: un oggetto immutabile rende la coda un punto di consegna invece che una
condivisione di stato.
"""
