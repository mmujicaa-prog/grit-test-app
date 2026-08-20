#!/usr/bin/env python3
"""CLI de comunicaciones Navalmanzano.

Reutiliza el motor de Andy Garden apuntando la raiz a este proyecto.

Uso:
    python3 navalmanzano/tools/ag.py <subcomando> --help
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Incorporar las herramientas compartidas de Andy Garden
_tools_ag = Path(__file__).resolve().parent.parent.parent / "andy_garden" / "tools"
if str(_tools_ag) not in sys.path:
    sys.path.insert(0, str(_tools_ag))

import ag as _ag  # noqa: E402

# Redirigir RAIZ y RUTA_AJUSTES a este proyecto
_ag.RAIZ = RAIZ
_ag.RUTA_AJUSTES = RAIZ / "config" / "ajustes.yaml"

if __name__ == "__main__":
    _ag.main()
