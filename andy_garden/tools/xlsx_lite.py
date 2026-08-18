"""Lector minimo de .xlsx usando solo la biblioteca estandar.

Existe para que el padron de inversores pueda venir en Excel sin obligar a
instalar openpyxl. Si openpyxl esta disponible, padron.py lo prefiere.

Limitaciones conocidas: no evalua formulas (lee el ultimo valor cacheado),
no aplica formatos de numero (las fechas salen como numero de serie de Excel,
que padron.py convierte), y no lee hojas ocultas de forma distinta.
"""

from __future__ import annotations

import re
import zipfile
from xml.etree import ElementTree as ET

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _texto_de_celda_compartida(nodo: ET.Element) -> str:
    """Concatena los fragmentos de texto de una entrada de sharedStrings."""
    return "".join(t.text or "" for t in nodo.iter("{%s}t" % _NS["m"]))


def _indice_columna(ref: str) -> int:
    """Convierte la referencia de celda 'BC12' en el indice de columna 0-based."""
    letras = re.match(r"([A-Z]+)", ref or "")
    if not letras:
        return 0
    indice = 0
    for caracter in letras.group(1):
        indice = indice * 26 + (ord(caracter) - ord("A") + 1)
    return indice - 1


def leer_hoja(ruta: str, nombre_hoja: str | None = None) -> list[list[str]]:
    """Devuelve la hoja indicada (o la primera) como una matriz de strings."""
    with zipfile.ZipFile(ruta) as libro:
        compartidas: list[str] = []
        if "xl/sharedStrings.xml" in libro.namelist():
            raiz = ET.fromstring(libro.read("xl/sharedStrings.xml"))
            compartidas = [_texto_de_celda_compartida(si) for si in raiz]

        objetivo = _resolver_hoja(libro, nombre_hoja)
        filas: list[list[str]] = []
        raiz = ET.fromstring(libro.read(objetivo))
        for fila in raiz.iter("{%s}row" % _NS["m"]):
            valores: list[str] = []
            for celda in fila.iter("{%s}c" % _NS["m"]):
                columna = _indice_columna(celda.get("r", ""))
                while len(valores) <= columna:
                    valores.append("")
                valores[columna] = _valor_de_celda(celda, compartidas)
            filas.append(valores)
    return filas


def _resolver_hoja(libro: zipfile.ZipFile, nombre_hoja: str | None) -> str:
    """Traduce el nombre visible de una hoja a su ruta interna dentro del zip."""
    hojas = sorted(n for n in libro.namelist() if n.startswith("xl/worksheets/sheet"))
    if not hojas:
        raise ValueError("El archivo .xlsx no contiene hojas de calculo")
    if not nombre_hoja:
        return hojas[0]

    raiz = ET.fromstring(libro.read("xl/workbook.xml"))
    for posicion, hoja in enumerate(raiz.iter("{%s}sheet" % _NS["m"])):
        if (hoja.get("name") or "").strip().lower() == nombre_hoja.strip().lower():
            if posicion < len(hojas):
                return hojas[posicion]
    raise ValueError("No se encontro la hoja '%s' en el archivo" % nombre_hoja)


def _valor_de_celda(celda: ET.Element, compartidas: list[str]) -> str:
    """Extrae el valor de una celda resolviendo cadenas compartidas e inline."""
    tipo = celda.get("t")
    if tipo == "inlineStr":
        nodo = celda.find("m:is", _NS)
        return _texto_de_celda_compartida(nodo) if nodo is not None else ""

    valor = celda.find("m:v", _NS)
    if valor is None or valor.text is None:
        return ""
    if tipo == "s":
        indice = int(valor.text)
        return compartidas[indice] if 0 <= indice < len(compartidas) else ""
    if tipo == "b":
        return "true" if valor.text == "1" else "false"
    return valor.text
