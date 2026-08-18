"""Combinacion de plantillas con los datos de cada inversor.

La sustitucion es deliberadamente estrecha: solo {{campo}}. No hay logica ni
expresiones dentro de la plantilla, porque el texto de cada comunicacion lo
revisa una persona antes de que exista el borrador y una plantilla con logica
oculta hace mas dificil esa revision.

Los campos que quedan sin resolver se devuelven como faltantes en vez de
sustituirse por vacio: un '{{monto}}' literal en un correo a un inversor es
peor que un error temprano.
"""

from __future__ import annotations

import re
from pathlib import Path

_RE_CAMPO = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

DIRECTORIO_PLANTILLAS = Path(__file__).resolve().parent.parent / "config" / "plantillas"


def combinar(texto: str, campos: dict[str, str]) -> tuple[str, list[str]]:
    """Sustituye {{campo}} y devuelve (texto_resultante, campos_no_encontrados)."""
    faltantes: list[str] = []

    def reemplazo(coincidencia: re.Match[str]) -> str:
        nombre = coincidencia.group(1)
        valor = campos.get(nombre)
        if valor is None or str(valor).strip() == "":
            if nombre not in faltantes:
                faltantes.append(nombre)
            return coincidencia.group(0)
        return str(valor)

    return _RE_CAMPO.sub(reemplazo, texto or ""), faltantes


def campos_usados(texto: str) -> list[str]:
    """Lista los campos de combinacion que aparecen en un texto, en orden de aparicion."""
    vistos: list[str] = []
    for coincidencia in _RE_CAMPO.finditer(texto or ""):
        if coincidencia.group(1) not in vistos:
            vistos.append(coincidencia.group(1))
    return vistos


def cargar_plantilla(nombre: str) -> str:
    """Carga una plantilla por nombre de archivo o por ruta completa."""
    ruta = Path(nombre)
    if not ruta.exists():
        ruta = DIRECTORIO_PLANTILLAS / nombre
    if not ruta.exists() and not ruta.suffix:
        ruta = DIRECTORIO_PLANTILLAS / (nombre + ".html")
    if not ruta.exists():
        disponibles = ", ".join(sorted(p.name for p in DIRECTORIO_PLANTILLAS.glob("*.html"))) or "(ninguna)"
        raise FileNotFoundError("No existe la plantilla '%s'. Disponibles: %s" % (nombre, disponibles))
    return ruta.read_text(encoding="utf-8")


def listar_plantillas() -> list[str]:
    """Plantillas ofrecibles al operador; las que empiezan por '_' son internas."""
    return sorted(p.name for p in DIRECTORIO_PLANTILLAS.glob("*.html") if not p.name.startswith("_"))


# Marca interna para insertar el cuerpo ya combinado dentro del envoltorio sin
# que sus campos sin resolver se procesen (y se reporten) dos veces.
_MARCA_CONTENIDO = "\x00::contenido::\x00"


def componer(nombre_plantilla: str, campos: dict[str, str], firma_html: str = "") -> tuple[str, list[str]]:
    """Combina la plantilla y la envuelve en _base.html.

    Devuelve (html_final, campos_faltantes). Si no existe _base.html, la
    plantilla se usa tal cual: el envoltorio es una comodidad, no un requisito.
    """
    contenido, faltantes = combinar(cargar_plantilla(nombre_plantilla), campos)

    ruta_base = DIRECTORIO_PLANTILLAS / "_base.html"
    if not ruta_base.exists():
        return contenido + (firma_html or ""), faltantes

    campos_base = dict(campos)
    campos_base["contenido"] = _MARCA_CONTENIDO
    campos_base["firma"] = firma_html or ""
    envoltorio, faltantes_base = combinar(ruta_base.read_text(encoding="utf-8"), campos_base)

    for campo in faltantes_base:
        if campo not in faltantes:
            faltantes.append(campo)
    return _sin_comentarios(envoltorio.replace(_MARCA_CONTENIDO, contenido)), faltantes


def _sin_comentarios(html: str) -> str:
    """Quita los comentarios HTML: son notas para quien edita la plantilla."""
    return re.sub(r"<!--.*?-->\s*", "", html, flags=re.S)


def a_texto_plano(html: str) -> str:
    """Version en texto plano del cuerpo, para la alternativa del correo multiparte."""
    texto = re.sub(r"(?is)<(script|style).*?</\1>", "", html or "")
    texto = re.sub(r"(?i)<br\s*/?>", "\n", texto)
    texto = re.sub(r"(?i)</(p|div|tr|h[1-6]|li)>", "\n", texto)
    texto = re.sub(r"(?i)<li[^>]*>", "  - ", texto)
    texto = re.sub(r"<[^>]+>", "", texto)
    reemplazos = {"&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'"}
    for entidad, caracter in reemplazos.items():
        texto = texto.replace(entidad, caracter)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n\s*\n\s*\n+", "\n\n", texto)
    return texto.strip()
