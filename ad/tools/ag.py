#!/usr/bin/env python3
"""CLI de comunicaciones Agnessa Dom (AD).

Reutiliza el motor de Andy Garden apuntando la raiz a este proyecto.

Uso:
    python3 ad/tools/ag.py <subcomando> --help
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
import plantillas as _mod_plantillas  # noqa: E402

# Redirigir RAIZ, RUTA_AJUSTES y directorio de paquetes a este proyecto
_ag.RAIZ = RAIZ
_ag.RUTA_AJUSTES = RAIZ / "config" / "ajustes.yaml"
_ag.mod_paquete.DIRECTORIO_PAQUETES = RAIZ / "paquetes"
_mod_plantillas.DIRECTORIO_PLANTILLAS = RAIZ / "config" / "plantillas"

# Inyectar copias_fijas de ajustes.yaml en cada envio.
# Se añaden al CC deduplicando contra To/CC/BCC ya presentes.
_orig_destinatarios = _ag.mod_padron.destinatarios


def _destinatarios_con_copias_fijas(inversor):
    destinos = _orig_destinatarios(inversor)

    # Añadir emails adicionales de To desde la columna extras del padrón
    emails_to_extra = inversor.extras.get("emails_to_adicionales", "")
    if emails_to_extra:
        ya_en_to = {e.lower() for e in destinos["to"]}
        for raw in _ag.mod_padron.separar_emails(emails_to_extra):
            if raw.lower() not in ya_en_to:
                destinos["to"].append(raw)
                ya_en_to.add(raw.lower())

    ajustes = _ag.cargar_ajustes()
    copias_fijas = ajustes.get("copias_fijas") or []
    usados = {d.lower() for d in destinos["to"] + destinos["cc"] + destinos["bcc"]}
    extras = [c for c in copias_fijas if c.lower() not in usados]
    destinos["cc"] = destinos["cc"] + extras
    return destinos


_ag.mod_padron.destinatarios = _destinatarios_con_copias_fijas

if __name__ == "__main__":
    _ag.main()
