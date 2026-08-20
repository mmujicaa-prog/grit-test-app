"""Lectura, normalizacion y validacion del padron de inversores de Andy Garden.

El padron lo mantiene el usuario en su propio archivo (Google Sheet, Excel o
CSV). Este modulo no impone nombres de columna exactos: normaliza los
encabezados y los resuelve contra una tabla de sinonimos, de modo que un
padron escrito con criterio humano se lee sin retoques.

Cualquier columna que no corresponda a un campo conocido se conserva como
campo extra y queda disponible como campo de combinacion en las plantillas.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

# Campo canonico -> sinonimos aceptados en el encabezado (ya normalizados).
SINONIMOS: dict[str, tuple[str, ...]] = {
    "id": ("id", "id_inversor", "codigo", "codigo_inversor", "identificador", "rut", "nif", "dni", "cif"),
    "nombre": ("nombre", "nombre_completo", "nombres", "razon_social", "inversor", "inversionista",
               "nombre_inversor", "cliente", "titular", "nombre_titular", "nombre_razon_social",
               "apellidos_nombre"),
    "tratamiento": ("tratamiento", "saludo", "trato", "titulo", "encabezado"),
    "email_principal": ("email", "email_principal", "correo", "correo_electronico", "correo_principal",
                        "mail", "e_mail", "email_inversor", "correo_inversor", "destinatario",
                        "correo_contacto", "email_contacto"),
    "emails_copia": ("cc", "copia", "copias", "emails_copia", "correos_copia", "en_copia", "copia_a",
                     "con_copia", "email_copia"),
    "emails_copia_oculta": ("bcc", "cco", "copia_oculta", "emails_copia_oculta", "con_copia_oculta",
                            "copias_ocultas"),
    "monto_comprometido": ("monto", "monto_comprometido", "monto_invertido", "inversion", "importe",
                           "aporte", "capital", "compromiso", "monto_inversion"),
    "moneda": ("moneda", "divisa", "currency"),
    "porcentaje": ("porcentaje", "participacion", "porcentaje_participacion", "pct", "porcentaje_propiedad",
                   "cuota", "share"),
    "fecha_ingreso": ("fecha_ingreso", "fecha", "fecha_inversion", "fecha_entrada", "fecha_suscripcion",
                      "ingreso", "fecha_aporte"),
    "tramo": ("tramo", "serie", "grupo", "clase", "tipo_inversor", "categoria"),
    "estado": ("estado", "status", "situacion", "vigencia"),
    "idioma": ("idioma", "lengua", "language", "lang"),
    "notas": ("notas", "nota", "observaciones", "comentarios", "obs", "detalle"),
}

# Indice inverso: encabezado normalizado -> campo canonico.
_INDICE_SINONIMOS = {alias: canonico
                     for canonico, alias_del_campo in SINONIMOS.items()
                     for alias in alias_del_campo}

# Conectores que un encabezado escrito por una persona lleva y una tabla de
# sinonimos no deberia tener que enumerar: "Fecha de ingreso", "Correo del
# inversor", "Monto en euros".
_PALABRAS_VACIAS = {"de", "del", "la", "el", "los", "las", "en", "y", "a", "por", "para", "al"}


def resolver_campo(encabezado: str) -> str | None:
    """Traduce un encabezado del padron al campo canonico, o None si no se reconoce."""
    normalizado = normalizar_encabezado(encabezado)
    if normalizado in _INDICE_SINONIMOS:
        return _INDICE_SINONIMOS[normalizado]
    compacto = "_".join(t for t in normalizado.split("_") if t not in _PALABRAS_VACIAS)
    return _INDICE_SINONIMOS.get(compacto)


_RE_EMAIL = re.compile(r"^[^@\s<>,;]+@[^@\s<>,;]+\.[A-Za-z]{2,}$")
_RE_EMAIL_EN_TEXTO = re.compile(r"<([^>]+)>")
_SEPARADORES_EMAIL = re.compile(r"[;,\n\r/|]+")

ESTADOS_ACTIVOS = {"activo"}
_MAPA_ESTADOS = {
    "activo": "activo", "activa": "activo", "vigente": "activo", "si": "activo", "s": "activo",
    "true": "activo", "1": "activo", "ok": "activo", "": "activo",
    "pausado": "pausado", "pausada": "pausado", "pausa": "pausado", "suspendido": "pausado",
    "en_pausa": "pausado", "espera": "pausado",
    "salido": "salido", "salida": "salido", "retirado": "salido", "baja": "salido",
    "inactivo": "salido", "no": "salido", "false": "salido", "0": "salido", "cerrado": "salido",
}


def normalizar_encabezado(texto: str) -> str:
    """Reduce un encabezado a su forma comparable: sin acentos, minusculas, con guion bajo."""
    sin_acentos = unicodedata.normalize("NFKD", str(texto or ""))
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    limpio = re.sub(r"[^a-z0-9]+", "_", sin_acentos.lower()).strip("_")
    return re.sub(r"_+", "_", limpio)


@dataclass
class Inversor:
    """Un inversor del padron, ya normalizado y listo para combinar en plantillas."""

    id: str
    nombre: str
    email_principal: str
    fila: int
    tratamiento: str = ""
    emails_copia: list[str] = field(default_factory=list)
    emails_copia_oculta: list[str] = field(default_factory=list)
    monto_comprometido: str = ""
    moneda: str = ""
    porcentaje: str = ""
    fecha_ingreso: str = ""
    tramo: str = ""
    estado: str = "activo"
    idioma: str = "es"
    notas: str = ""
    extras: dict[str, str] = field(default_factory=dict)

    @property
    def activo(self) -> bool:
        return self.estado in ESTADOS_ACTIVOS

    def campos_combinacion(self) -> dict[str, str]:
        """Diccionario plano de campos disponibles como {{campo}} en las plantillas."""
        campos = {
            "id": self.id,
            "nombre": self.nombre,
            "tratamiento": self.tratamiento,
            "monto": formatear_monto(self.monto_comprometido),
            "monto_comprometido": formatear_monto(self.monto_comprometido),
            "monto_crudo": self.monto_comprometido,
            "moneda": self.moneda,
            "porcentaje": self.porcentaje,
            "fecha_ingreso": self.fecha_ingreso,
            "tramo": self.tramo,
            "estado": self.estado,
            "idioma": self.idioma,
            "notas": self.notas,
            "primer_nombre": self.nombre.split()[0] if self.nombre.split() else self.nombre,
            "saludo": (self.tratamiento or "Estimado/a").strip() + " "
                      + (self.extras.get("nombre_corto") or self.nombre.split()[0] if self.nombre.split() else self.nombre),
        }
        campos.update(self.extras)
        return campos


@dataclass
class Incidencia:
    """Un problema detectado al validar el padron."""

    nivel: str  # "error" bloquea la generacion; "aviso" solo se reporta
    fila: int
    id_inversor: str
    mensaje: str


def separar_emails(valor: str) -> list[str]:
    """Separa una celda con varios correos y extrae la direccion de formatos 'Nombre <a@b.com>'."""
    if not valor:
        return []
    direcciones: list[str] = []
    for parte in _SEPARADORES_EMAIL.split(str(valor)):
        parte = parte.strip()
        if not parte:
            continue
        entre_angulos = _RE_EMAIL_EN_TEXTO.search(parte)
        if entre_angulos:
            parte = entre_angulos.group(1).strip()
        else:
            # "Juan Perez juan@x.com" -> nos quedamos con el token que parece correo
            tokens = [t for t in parte.split() if "@" in t]
            if tokens:
                parte = tokens[-1].strip("<>,;")
        if parte and parte not in direcciones:
            direcciones.append(parte)
    return direcciones


def email_valido(direccion: str) -> bool:
    return bool(_RE_EMAIL.match(direccion or ""))


def formatear_monto(valor: str) -> str:
    """Da formato espanol a un importe que venga como numero pelado.

    "250000" -> "250.000" y "250000.5" -> "250.000,50". Si el padron ya trae el
    importe formateado (o con texto), se respeta tal cual: quien lo escribio
    sabia lo que queria y reformatearlo solo introduciria errores.
    """
    texto = str(valor or "").strip().replace(" ", "")
    if not texto:
        return ""
    if re.fullmatch(r"\d+", texto):
        return "{:,}".format(int(texto)).replace(",", ".")
    if re.fullmatch(r"\d+[.,]\d{1,2}", texto):
        entero, _separador, decimales = re.split(r"([.,])", texto, maxsplit=1)
        return "{:,}".format(int(entero)).replace(",", ".") + "," + decimales.ljust(2, "0")
    return str(valor).strip()


def _normalizar_estado(valor: str) -> str:
    return _MAPA_ESTADOS.get(normalizar_encabezado(valor), normalizar_encabezado(valor) or "activo")


def _normalizar_fecha(valor: str) -> str:
    """Devuelve la fecha en ISO cuando se reconoce; si no, el valor original sin tocar."""
    texto = str(valor or "").strip()
    if not texto:
        return ""
    # Numero de serie de Excel (dias desde 1899-12-30).
    if re.fullmatch(r"\d{5}(\.\d+)?", texto):
        base = dt.date(1899, 12, 30)
        return (base + dt.timedelta(days=int(float(texto)))).isoformat()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(texto[:10], formato).date().isoformat()
        except ValueError:
            continue
    return texto


def _leer_matriz(ruta: Path, hoja: str | None) -> list[list[str]]:
    """Carga el archivo del padron como matriz de strings, sea CSV, TSV, XLSX o JSON."""
    sufijo = ruta.suffix.lower()
    if sufijo in (".csv", ".tsv", ".txt"):
        texto = ruta.read_text(encoding="utf-8-sig")
        delimitador = "\t" if sufijo == ".tsv" else _detectar_delimitador(texto)
        return [list(fila) for fila in csv.reader(texto.splitlines(), delimiter=delimitador)]
    if sufijo == ".json":
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        registros = datos["inversores"] if isinstance(datos, dict) else datos
        claves: list[str] = []
        for registro in registros:
            for clave in registro:
                if clave not in claves:
                    claves.append(clave)
        return [claves] + [[str(r.get(k, "")) for k in claves] for r in registros]
    if sufijo in (".xlsx", ".xlsm"):
        try:
            import openpyxl  # type: ignore

            libro = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
            pagina = libro[hoja] if hoja else libro.worksheets[0]
            return [["" if c is None else str(c) for c in fila] for fila in pagina.values]
        except ImportError:
            try:
                from . import xlsx_lite  # type: ignore
            except ImportError:
                import xlsx_lite  # type: ignore

            return xlsx_lite.leer_hoja(str(ruta), hoja)
    raise ValueError(
        "Formato de padron no soportado: %s. Usa .csv, .tsv, .xlsx o .json "
        "(una hoja de Google Sheets se exporta a CSV)." % sufijo
    )


def _detectar_delimitador(texto: str) -> str:
    """Elige el delimitador del CSV mirando la primera linea no vacia."""
    primera = next((linea for linea in texto.splitlines() if linea.strip()), "")
    return max((",", ";", "\t"), key=primera.count)


def _localizar_encabezado(matriz: list[list[str]]) -> int:
    """Encuentra la fila de encabezados: la primera que mapea al menos dos campos conocidos.

    Tolera padrones con titulo o filas en blanco arriba de la tabla.
    """
    for indice, fila in enumerate(matriz[:20]):
        reconocidos = {resolver_campo(c) for c in fila}
        reconocidos.discard(None)
        if len(reconocidos) >= 2:
            return indice
    return 0


def cargar_padron(ruta: str | Path, hoja: str | None = None) -> tuple[list[Inversor], list[Incidencia]]:
    """Lee el padron y devuelve (inversores, incidencias).

    Nunca lanza por datos malos: los problemas se reportan como incidencias para
    que el operador los vea todos de una vez en lugar de uno por ejecucion.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError("No existe el archivo de padron: %s" % ruta)

    matriz = [fila for fila in _leer_matriz(ruta, hoja)]
    if not matriz:
        return [], [Incidencia("error", 0, "", "El padron esta vacio")]

    fila_encabezado = _localizar_encabezado(matriz)
    encabezados = [normalizar_encabezado(c) for c in matriz[fila_encabezado]]
    mapa = {i: resolver_campo(h) for i, h in enumerate(encabezados)}

    incidencias: list[Incidencia] = []
    if not any(mapa.values()):
        incidencias.append(Incidencia(
            "error", fila_encabezado + 1, "",
            "No se reconocio ninguna columna. Revisa docs/PADRON.md para los encabezados esperados."))
        return [], incidencias

    for obligatorio in ("nombre", "email_principal"):
        if obligatorio not in mapa.values():
            incidencias.append(Incidencia(
                "error", fila_encabezado + 1, "",
                "Falta la columna obligatoria '%s' (o un sinonimo reconocido)" % obligatorio))

    inversores: list[Inversor] = []
    vistos_id: dict[str, int] = {}
    vistos_email: dict[str, str] = {}

    for desplazamiento, fila in enumerate(matriz[fila_encabezado + 1:], start=fila_encabezado + 2):
        crudo: dict[str, str] = {}
        extras: dict[str, str] = {}
        for indice, valor in enumerate(fila):
            valor = str(valor or "").strip()
            canonico = mapa.get(indice)
            if canonico:
                crudo[canonico] = valor
            elif indice < len(encabezados) and encabezados[indice] and valor:
                extras[encabezados[indice]] = valor

        if not any(crudo.get(c) for c in ("nombre", "email_principal", "id")):
            continue  # fila en blanco o separadora

        identificador = crudo.get("id") or normalizar_encabezado(crudo.get("nombre", "")) or "fila_%d" % desplazamiento
        inversor = Inversor(
            id=identificador,
            nombre=crudo.get("nombre", "").strip(),
            email_principal=(separar_emails(crudo.get("email_principal", "")) or [""])[0],
            fila=desplazamiento,
            tratamiento=crudo.get("tratamiento", "").strip(),
            emails_copia=separar_emails(crudo.get("emails_copia", "")),
            emails_copia_oculta=separar_emails(crudo.get("emails_copia_oculta", "")),
            monto_comprometido=crudo.get("monto_comprometido", "").strip(),
            moneda=crudo.get("moneda", "").strip(),
            porcentaje=crudo.get("porcentaje", "").strip(),
            fecha_ingreso=_normalizar_fecha(crudo.get("fecha_ingreso", "")),
            tramo=crudo.get("tramo", "").strip(),
            estado=_normalizar_estado(crudo.get("estado", "")),
            idioma=(normalizar_encabezado(crudo.get("idioma", "")) or "es")[:2],
            notas=crudo.get("notas", "").strip(),
            extras=extras,
        )
        incidencias.extend(_validar_inversor(inversor, vistos_id, vistos_email))
        inversores.append(inversor)

    if not inversores:
        incidencias.append(Incidencia("error", 0, "", "No se encontro ninguna fila de inversor con datos"))
    return inversores, incidencias


def _validar_inversor(inversor: Inversor, vistos_id: dict[str, int],
                      vistos_email: dict[str, str]) -> list[Incidencia]:
    """Valida un inversor contra las reglas que impiden un envio correcto."""
    problemas: list[Incidencia] = []

    def anotar(nivel: str, mensaje: str) -> None:
        problemas.append(Incidencia(nivel, inversor.fila, inversor.id, mensaje))

    if not inversor.nombre:
        anotar("error", "Sin nombre: el saludo del correo quedaria incompleto")
    if not inversor.email_principal:
        anotar("error", "Sin correo principal: no se puede generar el borrador")
    elif not email_valido(inversor.email_principal):
        anotar("error", "Correo principal invalido: '%s'" % inversor.email_principal)

    for copia in inversor.emails_copia + inversor.emails_copia_oculta:
        if not email_valido(copia):
            anotar("error", "Correo en copia invalido: '%s'" % copia)

    en_copia = {c.lower() for c in inversor.emails_copia}
    if inversor.email_principal.lower() in en_copia:
        anotar("aviso", "El correo principal tambien aparece en copia; se eliminara el duplicado")
    ocultas = {c.lower() for c in inversor.emails_copia_oculta}
    if en_copia & ocultas:
        anotar("aviso", "Hay correos repetidos entre copia y copia oculta; se dejaran solo en copia")

    if inversor.id in vistos_id:
        anotar("error", "Id duplicado, ya usado en la fila %d" % vistos_id[inversor.id])
    else:
        vistos_id[inversor.id] = inversor.fila

    if inversor.email_principal:
        clave = inversor.email_principal.lower()
        if clave in vistos_email and vistos_email[clave] != inversor.id:
            anotar("aviso", "El correo principal se repite con el inversor '%s': recibiria dos borradores"
                   % vistos_email[clave])
        vistos_email.setdefault(clave, inversor.id)

    if inversor.estado not in ("activo", "pausado", "salido"):
        anotar("aviso", "Estado no reconocido '%s': se tratara como no activo" % inversor.estado)

    return problemas


def destinatarios(inversor: Inversor) -> dict[str, list[str]]:
    """Resuelve To/CC/BCC finales del inversor, sin duplicados entre campos."""
    para = [inversor.email_principal] if inversor.email_principal else []
    usados = {d.lower() for d in para}
    copia = [c for c in inversor.emails_copia if c.lower() not in usados]
    usados.update(c.lower() for c in copia)
    oculta = [c for c in inversor.emails_copia_oculta if c.lower() not in usados]
    return {"to": para, "cc": copia, "bcc": oculta}


def resumen_incidencias(incidencias: list[Incidencia]) -> tuple[int, int]:
    """Cuenta (errores, avisos)."""
    errores = sum(1 for i in incidencias if i.nivel == "error")
    return errores, len(incidencias) - errores
