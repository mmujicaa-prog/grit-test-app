"""Bitacora append-only de todo lo que el sistema ha hecho con Gmail.

Sirve a dos fines: dejar rastro auditable de que se creo, para quien y con que
adjuntos; y evitar duplicados, respondiendo a la pregunta "¿ya le genere el
borrador de esta comunicacion a este inversor?" sin depender de la memoria de
la sesion.

Es un JSONL: se anexa, nunca se reescribe.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

RUTA_BITACORA = Path(__file__).resolve().parent.parent / "bitacora.jsonl"


def registrar(paquete_id: str, id_inversor: str, accion: str, *, draft_id: str = "",
              asunto: str = "", to: list[str] | None = None, cc: list[str] | None = None,
              bcc: list[str] | None = None, adjuntos: list[str] | None = None,
              detalle: str = "") -> dict[str, object]:
    """Anexa un evento a la bitacora y devuelve el registro escrito."""
    evento = {
        "momento": dt.datetime.now().isoformat(timespec="seconds"),
        "paquete_id": paquete_id,
        "id_inversor": id_inversor,
        "accion": accion,
        "draft_id": draft_id,
        "asunto": asunto,
        "to": to or [],
        "cc": cc or [],
        "bcc": bcc or [],
        "adjuntos": adjuntos or [],
        "detalle": detalle,
    }
    RUTA_BITACORA.parent.mkdir(parents=True, exist_ok=True)
    with RUTA_BITACORA.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(evento, ensure_ascii=False) + "\n")
    return evento


def leer(paquete_id: str | None = None) -> list[dict[str, object]]:
    """Lee la bitacora completa o solo los eventos de un paquete."""
    if not RUTA_BITACORA.exists():
        return []
    eventos: list[dict[str, object]] = []
    for linea in RUTA_BITACORA.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        try:
            evento = json.loads(linea)
        except json.JSONDecodeError:
            continue  # una linea corrupta no debe cegar el resto de la bitacora
        if paquete_id is None or evento.get("paquete_id") == paquete_id:
            eventos.append(evento)
    return eventos


def borradores_creados(paquete_id: str) -> dict[str, str]:
    """Mapa id_inversor -> draft_id de los borradores ya creados para ese paquete.

    Es la defensa contra duplicados: antes de crear un borrador el agente
    consulta aqui, y ademas contrasta con los borradores reales de Gmail.
    """
    creados: dict[str, str] = {}
    for evento in leer(paquete_id):
        if evento.get("accion") == "borrador_creado" and evento.get("id_inversor"):
            creados[str(evento["id_inversor"])] = str(evento.get("draft_id", ""))
        elif evento.get("accion") == "borrador_descartado":
            creados.pop(str(evento.get("id_inversor", "")), None)
    return creados
