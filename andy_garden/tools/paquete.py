"""Modelo del paquete de envio: una comunicacion x todos sus inversores.

Un paquete es la unidad de trabajo del sistema. Se genera a demanda (no hay
calendario: cada comunicacion nace de una solicitud concreta), se revisa fila
a fila, y solo entonces se convierte en borradores de Gmail.

El paquete vive como JSON (fuente para la consola y para el agente) y se
espeja a CSV para la hoja de Drive, que es donde el operador edita comodamente
asunto, cuerpo, copias y adjuntos de cada inversor.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

DIRECTORIO_PAQUETES = Path(__file__).resolve().parent.parent / "paquetes"

# Estados de un envio individual dentro del paquete.
PENDIENTE = "pendiente_revision"   # generado, esperando revision humana
APROBADO = "aprobado"              # revisado, listo para convertirse en borrador
BORRADOR_CREADO = "borrador_creado"  # ya existe en la carpeta Borradores de Gmail
OMITIDO = "omitido"                # el operador decidio no enviarlo esta vez
ERROR = "error"                    # no se pudo crear el borrador; ver el campo notas

ESTADOS_VALIDOS = (PENDIENTE, APROBADO, BORRADOR_CREADO, OMITIDO, ERROR)

COLUMNAS_CSV = ("id_inversor", "nombre", "to", "cc", "bcc", "asunto",
                "cuerpo_html", "adjuntos", "estado", "draft_id", "notas")


@dataclass
class Adjunto:
    """Un archivo de Drive que acompana a la comunicacion."""

    nombre: str
    drive_file_id: str = ""
    tamano_bytes: int = 0
    mime_type: str = ""

    def descripcion(self) -> str:
        return "%s|%s" % (self.nombre, self.drive_file_id) if self.drive_file_id else self.nombre


@dataclass
class Envio:
    """La comunicacion dirigida a un inversor concreto."""

    id_inversor: str
    nombre: str
    to: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    asunto: str = ""
    cuerpo_html: str = ""
    adjuntos: list[Adjunto] = field(default_factory=list)
    estado: str = PENDIENTE
    draft_id: str = ""
    campos_faltantes: list[str] = field(default_factory=list)
    notas: str = ""

    @property
    def listo(self) -> bool:
        """Un envio esta listo si fue aprobado y no arrastra problemas conocidos."""
        return (self.estado == APROBADO and bool(self.to) and bool(self.asunto.strip())
                and bool(self.cuerpo_html.strip()) and not self.campos_faltantes)


@dataclass
class Paquete:
    """Conjunto de envios de una misma comunicacion."""

    paquete_id: str
    titulo: str
    remitente: str
    creado: str = ""
    actualizado: str = ""
    plantilla: str = ""
    asunto_plantilla: str = ""
    notas: str = ""
    envios: list[Envio] = field(default_factory=list)

    # -- persistencia ------------------------------------------------------
    @property
    def ruta(self) -> Path:
        return DIRECTORIO_PAQUETES / self.paquete_id / "paquete.json"

    def guardar(self) -> Path:
        self.actualizado = dt.datetime.now().isoformat(timespec="seconds")
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.ruta.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        return self.ruta

    @classmethod
    def cargar(cls, referencia: str | Path) -> "Paquete":
        """Carga un paquete por id o por ruta al JSON."""
        ruta = Path(referencia)
        if not ruta.exists():
            ruta = DIRECTORIO_PAQUETES / str(referencia) / "paquete.json"
        if not ruta.exists():
            disponibles = ", ".join(sorted(p.name for p in DIRECTORIO_PAQUETES.glob("*") if p.is_dir())) or "(ninguno)"
            raise FileNotFoundError("No existe el paquete '%s'. Disponibles: %s" % (referencia, disponibles))
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        envios = [Envio(**{**e, "adjuntos": [Adjunto(**a) for a in e.get("adjuntos", [])]})
                  for e in datos.pop("envios", [])]
        return cls(envios=envios, **datos)

    # -- espejo en CSV para la hoja de Drive -------------------------------
    def a_csv(self) -> str:
        """Serializa el paquete al CSV que se sube a Drive como hoja editable."""
        salida = io.StringIO()
        escritor = csv.writer(salida)
        escritor.writerow(COLUMNAS_CSV)
        for envio in self.envios:
            escritor.writerow([
                envio.id_inversor,
                envio.nombre,
                "; ".join(envio.to),
                "; ".join(envio.cc),
                "; ".join(envio.bcc),
                envio.asunto,
                envio.cuerpo_html,
                "; ".join(a.descripcion() for a in envio.adjuntos),
                envio.estado,
                envio.draft_id,
                envio.notas,
            ])
        return salida.getvalue()

    def actualizar_desde_csv(self, texto_csv: str) -> list[str]:
        """Vuelca de vuelta al paquete lo editado en la hoja de Drive.

        La hoja manda sobre el contenido editable (asunto, cuerpo, copias,
        adjuntos, estado, notas). El draft_id nunca se toma de la hoja: es
        registro del sistema, no un campo editable.

        Devuelve la lista de cambios aplicados, para poder mostrarla antes de guardar.
        """
        por_id = {e.id_inversor: e for e in self.envios}
        cambios: list[str] = []
        for fila in csv.DictReader(io.StringIO(texto_csv)):
            identificador = (fila.get("id_inversor") or "").strip()
            envio = por_id.get(identificador)
            if not envio:
                cambios.append("AVISO: la hoja trae el inversor '%s', que no esta en el paquete" % identificador)
                continue
            for campo, valor_nuevo in (
                ("asunto", (fila.get("asunto") or "").strip()),
                ("cuerpo_html", fila.get("cuerpo_html") or ""),
                ("notas", (fila.get("notas") or "").strip()),
            ):
                if valor_nuevo != getattr(envio, campo):
                    setattr(envio, campo, valor_nuevo)
                    cambios.append("%s: %s actualizado" % (identificador, campo))
            for campo in ("to", "cc", "bcc"):
                nuevos = _separar_lista(fila.get(campo, ""))
                if nuevos != getattr(envio, campo):
                    setattr(envio, campo, nuevos)
                    cambios.append("%s: %s actualizado" % (identificador, campo))
            adjuntos = _parsear_adjuntos(fila.get("adjuntos", ""))
            if [a.descripcion() for a in adjuntos] != [a.descripcion() for a in envio.adjuntos]:
                envio.adjuntos = adjuntos
                cambios.append("%s: adjuntos actualizados" % identificador)
            estado = (fila.get("estado") or "").strip()
            if estado and estado != envio.estado:
                if estado in ESTADOS_VALIDOS:
                    envio.estado = estado
                    cambios.append("%s: estado -> %s" % (identificador, estado))
                else:
                    cambios.append("AVISO: %s tiene el estado desconocido '%s'; se deja como estaba"
                                   % (identificador, estado))
            envio.campos_faltantes = [c for c in envio.campos_faltantes
                                      if "{{%s}}" % c in envio.asunto + envio.cuerpo_html]
        return cambios

    # -- consultas ---------------------------------------------------------
    def por_estado(self) -> dict[str, int]:
        conteo: dict[str, int] = {}
        for envio in self.envios:
            conteo[envio.estado] = conteo.get(envio.estado, 0) + 1
        return conteo

    def listos(self) -> list[Envio]:
        return [e for e in self.envios if e.listo]

    def bloqueados(self) -> list[tuple[Envio, str]]:
        """Envios aprobados que aun no pueden convertirse en borrador, con el motivo."""
        problemas: list[tuple[Envio, str]] = []
        for envio in self.envios:
            if envio.estado != APROBADO:
                continue
            if not envio.to:
                problemas.append((envio, "sin destinatario"))
            elif not envio.asunto.strip():
                problemas.append((envio, "sin asunto"))
            elif not envio.cuerpo_html.strip():
                problemas.append((envio, "sin cuerpo"))
            elif envio.campos_faltantes:
                problemas.append((envio, "campos sin combinar: " + ", ".join(envio.campos_faltantes)))
        return problemas


def _separar_lista(valor: str) -> list[str]:
    return [p.strip() for p in re.split(r"[;,\n]+", valor or "") if p.strip()]


def _parsear_adjuntos(valor: str) -> list[Adjunto]:
    """Lee la columna 'adjuntos' con formato 'nombre|driveFileId; nombre|driveFileId'."""
    adjuntos: list[Adjunto] = []
    for parte in _separar_lista(valor):
        if "|" in parte:
            nombre, identificador = parte.split("|", 1)
            adjuntos.append(Adjunto(nombre=nombre.strip(), drive_file_id=identificador.strip()))
        else:
            adjuntos.append(Adjunto(nombre=parte))
    return adjuntos


def listar_paquetes() -> list[dict[str, object]]:
    """Resumen de todos los paquetes existentes, del mas reciente al mas antiguo."""
    resumenes: list[dict[str, object]] = []
    for carpeta in sorted(DIRECTORIO_PAQUETES.glob("*"), reverse=True):
        archivo = carpeta / "paquete.json"
        if not archivo.exists():
            continue
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        estados: dict[str, int] = {}
        for envio in datos.get("envios", []):
            estados[envio["estado"]] = estados.get(envio["estado"], 0) + 1
        resumenes.append({
            "paquete_id": datos.get("paquete_id", carpeta.name),
            "titulo": datos.get("titulo", ""),
            "creado": datos.get("creado", ""),
            "actualizado": datos.get("actualizado", ""),
            "envios": len(datos.get("envios", [])),
            "estados": estados,
        })
    return resumenes
