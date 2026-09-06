#!/usr/bin/env python3
"""Verifica la coerenza della coppia Decision.md / Sources.md di un progetto.

Uso:  python3 check-crosslinks.py <progetto>/Docs

Controlla, senza toccare i file:
  - ogni link Decision -> Sources punta a una scheda che esiste, e viceversa;
  - ogni ancora interna (#adr-NNN, #sNN) esiste;
  - nessuna fonte e' orfana: ogni scheda e' citata da almeno una ADR;
  - ogni ADR dichiara un blocco "**Fonti.**";
  - la numerazione delle ADR e' contigua e parte da 001.

Esce con codice 1 se trova un problema, cosi' e' usabile in un hook o in CI.
"""
import io
import os
import re
import sys


def read(path):
    if not os.path.isfile(path):
        sys.exit("manca %s" % path)
    return io.open(path, encoding="utf-8").read()


def main():
    docs = sys.argv[1] if len(sys.argv) > 1 else "Docs"
    dec = read(os.path.join(docs, "Decision.md"))
    src = read(os.path.join(docs, "Sources.md"))

    adr_defined = set(re.findall(r'<a id="(adr-\d+)"></a>', dec))
    src_defined = set(re.findall(r'<a id="(s\d+)"></a>', src))

    dec_to_src = set(re.findall(r"Sources\.md#(s\d+)", dec))
    src_to_dec = set(re.findall(r"Decision\.md#(adr-\d+)", src))
    dec_internal = set(re.findall(r"\]\(#(adr-\d+)\)", dec))
    src_internal = set(re.findall(r"\]\(#(s\d+)\)", src))

    problems = []

    def check(label, missing):
        if missing:
            problems.append("%s: %s" % (label, ", ".join(sorted(missing))))

    check("link Decision -> Sources senza scheda", dec_to_src - src_defined)
    check("link Sources -> Decision senza ADR", src_to_dec - adr_defined)
    check("ancore interne rotte in Decision.md", dec_internal - adr_defined)
    check("ancore interne rotte in Sources.md", src_internal - src_defined)
    check("fonti orfane, non citate da alcuna ADR", src_defined - dec_to_src)

    # Ogni ADR deve dichiarare le proprie fonti, fosse anche per dire che non ne ha.
    for block in re.split(r'(?=<a id="adr-\d+"></a>)', dec)[1:]:
        adr = re.search(r'<a id="(adr-\d+)"></a>', block).group(1)
        if "**Fonti.**" not in block:
            problems.append("%s non dichiara il blocco **Fonti.**" % adr)

    numbers = sorted(int(a.split("-")[1]) for a in adr_defined)
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        problems.append(
            "numerazione ADR non contigua: %s"
            % ", ".join("%03d" % n for n in numbers)
        )

    print("ADR definite: %d | fonti definite: %d" % (len(adr_defined), len(src_defined)))
    if problems:
        print("\nPROBLEMI:")
        for p in problems:
            print("  - %s" % p)
        return 1
    print("nessun riferimento rotto, nessuna fonte orfana")
    return 0


if __name__ == "__main__":
    sys.exit(main())
