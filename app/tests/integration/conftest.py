"""Configurazione della suite di integrazione.

Vuota: le prove arrivano al Task 8 del piano, e girano contro **gli stack di questo
repository** avviati con i `make up-0X` che già esistono — non contro un facsimile, e
non con `testcontainers` (ADR-0020, che supera ADR-0011). Il §7 del design dice ancora
il contrario e va letto insieme a quell'ADR.

La directory esiste già perché git non versiona le cartelle vuote e il target
`make app-test-integration` la nomina: senza un file dentro, su un clone appena fatto
quel comando fallirebbe per un motivo che non c'entra niente con l'integrazione.
"""
