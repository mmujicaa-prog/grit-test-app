#!/usr/bin/env python3
"""Incrusta un paquete en la consola como ejemplo cargable.

La consola es un unico archivo HTML sin peticiones de red, asi que el paquete
de demostracion tiene que viajar dentro. Este script lo mete en su sitio para
que la operacion sea repetible en vez de manual.

    python3 andy_garden/tools/incrustar_ejemplo.py [id_paquete]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONSOLA = RAIZ / "consola" / "andy_garden_comms.html"
PATRON = re.compile(r"var PAQUETE_EJEMPLO = .*?;\n", re.S)


def main(argv: list[str]) -> int:
    identificador = argv[1] if len(argv) > 1 else "2026-08-avance-obra"
    origen = RAIZ / "paquetes" / identificador / "paquete.json"
    if not origen.exists():
        print("No existe el paquete '%s'." % identificador)
        return 1

    paquete = json.loads(origen.read_text(encoding="utf-8"))
    # Se escapa '<' para que un '</script>' dentro del cuerpo HTML de un correo
    # no cierre antes de tiempo la etiqueta <script> que contiene este JSON.
    serializado = json.dumps(paquete, ensure_ascii=False, indent=2).replace("<", "\\u003c")

    texto = CONSOLA.read_text(encoding="utf-8")
    nuevo, sustituciones = PATRON.subn(
        lambda _: "var PAQUETE_EJEMPLO = " + serializado + ";\n", texto)
    if sustituciones != 1:
        print("Se esperaba una unica declaracion de PAQUETE_EJEMPLO y se encontraron %d."
              % sustituciones)
        return 1

    CONSOLA.write_text(nuevo, encoding="utf-8")
    print("Ejemplo '%s' incrustado en %s (%d envios)."
          % (identificador, CONSOLA.name, len(paquete.get("envios", []))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
