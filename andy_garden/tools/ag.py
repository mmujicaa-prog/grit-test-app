#!/usr/bin/env python3
"""Interfaz de linea de comandos del sistema de comunicaciones de Andy Garden.

Todo el trabajo con datos pasa por aqui: validar el padron, generar un paquete
de envio, espejarlo a la hoja de Drive, recoger las ediciones, aprobar y
consultar. Lo unico que este programa NO hace es tocar Gmail ni Drive: de eso
se encarga el agente a traves de los conectores, para que no haya credenciales
guardadas en el repositorio.

Uso:
    python3 andy_garden/tools/ag.py <subcomando> --help
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bitacora  # noqa: E402
import padron as mod_padron  # noqa: E402
import paquete as mod_paquete  # noqa: E402
import plantillas  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
RUTA_AJUSTES = RAIZ / "config" / "ajustes.yaml"


# --------------------------------------------------------------------------
# Ajustes
# --------------------------------------------------------------------------
def cargar_ajustes() -> dict:
    """Lee config/ajustes.yaml. Usa PyYAML si esta disponible."""
    try:
        import yaml  # type: ignore

        return yaml.safe_load(RUTA_AJUSTES.read_text(encoding="utf-8")) or {}
    except ImportError:
        raise SystemExit("Falta PyYAML. Instalalo con: pip install pyyaml")


def resolver_ruta_padron(ajustes: dict, sobrescritura: str | None) -> Path:
    """Convierte el ajuste 'padron.ruta' en una ruta local utilizable."""
    ruta = sobrescritura or (ajustes.get("padron") or {}).get("ruta") or ""
    if not ruta:
        raise SystemExit(
            "No hay padron configurado. Indica su ubicacion en config/ajustes.yaml "
            "(padron.ruta) o pasala con --padron.")
    if ruta.startswith(("sheet:", "drive:")):
        raise SystemExit(
            "El padron apunta a Drive (%s). El agente debe descargarlo primero a "
            "andy_garden/datos/ y volver a ejecutar con --padron apuntando al archivo local." % ruta)
    candidata = Path(ruta)
    return candidata if candidata.is_absolute() else (RAIZ / ruta)


def cargar_inversores(ajustes: dict, sobrescritura: str | None) -> tuple[list, list]:
    ruta = resolver_ruta_padron(ajustes, sobrescritura)
    hoja = (ajustes.get("padron") or {}).get("hoja") or None
    return mod_padron.cargar_padron(ruta, hoja)


# --------------------------------------------------------------------------
# Presentacion
# --------------------------------------------------------------------------
def imprimir_incidencias(incidencias: list) -> int:
    """Muestra las incidencias agrupadas y devuelve el numero de errores."""
    errores, avisos = mod_padron.resumen_incidencias(incidencias)
    for nivel, etiqueta in (("error", "ERROR"), ("aviso", "AVISO")):
        for incidencia in [i for i in incidencias if i.nivel == nivel]:
            referencia = "fila %d" % incidencia.fila if incidencia.fila else "padron"
            sufijo = " [%s]" % incidencia.id_inversor if incidencia.id_inversor else ""
            print("  %-5s %s%s: %s" % (etiqueta, referencia, sufijo, incidencia.mensaje))
    print("\n  %d errores, %d avisos" % (errores, avisos))
    return errores


# --------------------------------------------------------------------------
# Subcomandos
# --------------------------------------------------------------------------
def cmd_validar(args: argparse.Namespace) -> int:
    ajustes = cargar_ajustes()
    inversores, incidencias = cargar_inversores(ajustes, args.padron)

    print("Padron: %s" % resolver_ruta_padron(ajustes, args.padron))
    print("Inversores leidos: %d (activos: %d)\n"
          % (len(inversores), sum(1 for i in inversores if i.activo)))

    for inversor in inversores:
        destinos = mod_padron.destinatarios(inversor)
        marca = "*" if inversor.activo else "-"
        print("  %s %-24s %-32s cc:%d bcc:%d  [%s]"
              % (marca, inversor.id[:24], inversor.email_principal[:32],
                 len(destinos["cc"]), len(destinos["bcc"]), inversor.estado))

    print()
    errores = imprimir_incidencias(incidencias) if incidencias else 0
    if not incidencias:
        print("  Sin incidencias.")
    return 1 if errores else 0


def cmd_plantillas(args: argparse.Namespace) -> int:
    for nombre in plantillas.listar_plantillas():
        campos = plantillas.campos_usados(plantillas.cargar_plantilla(nombre))
        print("  %-26s campos: %s" % (nombre, ", ".join(campos) or "(ninguno)"))
    return 0


def cmd_generar(args: argparse.Namespace) -> int:
    ajustes = cargar_ajustes()
    inversores, incidencias = cargar_inversores(ajustes, args.padron)

    errores = [i for i in incidencias if i.nivel == "error"]
    if errores and not args.forzar:
        print("El padron tiene errores; corrigelos o repite con --forzar:\n")
        imprimir_incidencias(incidencias)
        return 1

    existente = mod_paquete.DIRECTORIO_PAQUETES / args.id / "paquete.json"
    if existente.exists() and not args.sobrescribir:
        print("Ya existe el paquete '%s'. Regenerarlo borraria los textos ya editados." % args.id)
        print("Usa otro --id, o repite con --sobrescribir si de verdad quieres empezar de cero.")
        return 1

    seleccion = _filtrar_inversores(inversores, ajustes, args)
    if not seleccion:
        print("Ningun inversor cumple los filtros indicados.")
        return 1

    extra = dict(par.split("=", 1) for par in args.campo) if args.campo else {}
    firma = ajustes.get("firma_html", "")

    paq = mod_paquete.Paquete(
        paquete_id=args.id,
        titulo=args.titulo,
        remitente=ajustes.get("remitente", ""),
        creado=dt.datetime.now().isoformat(timespec="seconds"),
        plantilla=args.plantilla,
        asunto_plantilla=args.asunto,
        notas=args.notas or "",
    )

    for inversor in seleccion:
        campos = {**inversor.campos_combinacion(), **extra}
        asunto, faltan_asunto = plantillas.combinar(args.asunto, campos)
        cuerpo, faltan_cuerpo = plantillas.componer(args.plantilla, campos, firma)
        destinos = mod_padron.destinatarios(inversor)
        paq.envios.append(mod_paquete.Envio(
            id_inversor=inversor.id,
            nombre=inversor.nombre,
            to=destinos["to"],
            cc=destinos["cc"],
            bcc=destinos["bcc"],
            asunto=asunto,
            cuerpo_html=cuerpo,
            campos_faltantes=sorted(set(faltan_asunto + faltan_cuerpo)),
        ))

    ruta = paq.guardar()
    (ruta.parent / "paquete.csv").write_text(paq.a_csv(), encoding="utf-8")

    print("Paquete '%s' generado con %d envios." % (paq.paquete_id, len(paq.envios)))
    print("  JSON: %s" % ruta)
    print("  CSV : %s  (esta es la hoja que se sube a Drive)" % (ruta.parent / "paquete.csv"))

    pendientes = {c for e in paq.envios for c in e.campos_faltantes}
    if pendientes:
        print("\n  Campos por completar antes de aprobar: %s" % ", ".join(sorted(pendientes)))
        print("  Editalos en la hoja de Drive o en la consola; ningun envio con campos")
        print("  sin resolver puede convertirse en borrador.")
    return 0


def _filtrar_inversores(inversores: list, ajustes: dict, args: argparse.Namespace) -> list:
    """Aplica los filtros de estado e inclusion/exclusion explicita."""
    solo_activos = (ajustes.get("padron") or {}).get("solo_activos", True)
    if args.incluir_todos:
        solo_activos = False

    seleccion = [i for i in inversores if i.activo or not solo_activos]
    if args.incluir:
        pedidos = {p.strip() for p in args.incluir.split(",") if p.strip()}
        seleccion = [i for i in seleccion if i.id in pedidos]
        desconocidos = pedidos - {i.id for i in seleccion}
        if desconocidos:
            print("AVISO: no estan en el padron (o fueron filtrados): %s" % ", ".join(sorted(desconocidos)))
    if args.excluir:
        fuera = {p.strip() for p in args.excluir.split(",") if p.strip()}
        seleccion = [i for i in seleccion if i.id not in fuera]
    return seleccion


def cmd_estado(args: argparse.Namespace) -> int:
    if not args.id:
        resumenes = mod_paquete.listar_paquetes()
        if not resumenes:
            print("No hay paquetes generados todavia.")
            return 0
        for resumen in resumenes:
            estados = ", ".join("%s=%d" % (k, v) for k, v in sorted(resumen["estados"].items()))
            print("  %-28s %-38s %d envios  [%s]"
                  % (resumen["paquete_id"], str(resumen["titulo"])[:38], resumen["envios"], estados))
        return 0

    paq = mod_paquete.Paquete.cargar(args.id)
    print("Paquete: %s" % paq.paquete_id)
    print("Titulo : %s" % paq.titulo)
    print("Creado : %s   Actualizado: %s\n" % (paq.creado, paq.actualizado))
    for envio in paq.envios:
        aviso = ""
        if envio.campos_faltantes:
            aviso = "  <- faltan: %s" % ", ".join(envio.campos_faltantes)
        print("  %-20s %-30s %-18s %s%s"
              % (envio.id_inversor[:20], (envio.to[0] if envio.to else "SIN DESTINATARIO")[:30],
                 envio.estado, envio.draft_id or "-", aviso))
    print("\n  " + ", ".join("%s=%d" % (k, v) for k, v in sorted(paq.por_estado().items())))

    bloqueados = paq.bloqueados()
    if bloqueados:
        print("\n  Aprobados pero bloqueados:")
        for envio, motivo in bloqueados:
            print("    %-20s %s" % (envio.id_inversor[:20], motivo))
    return 0


def cmd_exportar(args: argparse.Namespace) -> int:
    paq = mod_paquete.Paquete.cargar(args.id)
    destino = Path(args.salida) if args.salida else paq.ruta.parent / "paquete.csv"
    destino.write_text(paq.a_csv(), encoding="utf-8")
    print("CSV escrito en %s (%d filas)" % (destino, len(paq.envios)))
    return 0


def cmd_importar(args: argparse.Namespace) -> int:
    paq = mod_paquete.Paquete.cargar(args.id)
    texto = Path(args.csv).read_text(encoding="utf-8-sig")
    cambios = paq.actualizar_desde_csv(texto)
    if not cambios:
        print("Sin cambios respecto al paquete actual.")
        return 0
    for cambio in cambios:
        print("  %s" % cambio)
    if args.simular:
        print("\n(simulacion: no se guardo nada)")
        return 0
    paq.guardar()
    print("\n%d cambios aplicados a %s" % (len(cambios), paq.ruta))
    return 0


def cmd_aprobar(args: argparse.Namespace) -> int:
    paq = mod_paquete.Paquete.cargar(args.id)
    objetivo = ({p.strip() for p in args.inversor.split(",") if p.strip()} if args.inversor else None)

    aprobados, rechazados = [], []
    for envio in paq.envios:
        if objetivo is not None and envio.id_inversor not in objetivo:
            continue
        if envio.estado in (mod_paquete.BORRADOR_CREADO, mod_paquete.OMITIDO):
            continue
        if envio.campos_faltantes:
            rechazados.append((envio.id_inversor, "campos sin combinar: " + ", ".join(envio.campos_faltantes)))
            continue
        if not envio.to:
            rechazados.append((envio.id_inversor, "sin destinatario"))
            continue
        if not envio.asunto.strip() or not envio.cuerpo_html.strip():
            rechazados.append((envio.id_inversor, "asunto o cuerpo vacio"))
            continue
        envio.estado = mod_paquete.APROBADO
        aprobados.append(envio.id_inversor)

    paq.guardar()
    print("Aprobados: %d" % len(aprobados))
    for identificador in aprobados:
        print("  + %s" % identificador)
    if rechazados:
        print("\nNo aprobados: %d" % len(rechazados))
        for identificador, motivo in rechazados:
            print("  - %-20s %s" % (identificador[:20], motivo))
    return 0


def cmd_omitir(args: argparse.Namespace) -> int:
    paq = mod_paquete.Paquete.cargar(args.id)
    objetivo = {p.strip() for p in args.inversor.split(",") if p.strip()}
    tocados = 0
    for envio in paq.envios:
        if envio.id_inversor in objetivo and envio.estado != mod_paquete.BORRADOR_CREADO:
            envio.estado = mod_paquete.OMITIDO
            envio.notas = (envio.notas + " | " if envio.notas else "") + (args.motivo or "omitido por el operador")
            tocados += 1
    paq.guardar()
    print("%d envios marcados como omitidos." % tocados)
    return 0


def cmd_pendientes(args: argparse.Namespace) -> int:
    """Emite en JSON los envios listos para convertirse en borrador de Gmail.

    Es la entrada que consume el agente: cada elemento trae ya resueltos
    destinatarios, asunto, cuerpo y adjuntos. Los que ya tienen borrador segun
    la bitacora quedan fuera, para no duplicar.
    """
    paq = mod_paquete.Paquete.cargar(args.id)
    ajustes = cargar_ajustes()
    ya_creados = bitacora.borradores_creados(paq.paquete_id)

    salida = []
    omitidos_por_duplicado = []
    for envio in paq.listos():
        if envio.id_inversor in ya_creados and not args.rehacer:
            omitidos_por_duplicado.append(envio.id_inversor)
            continue
        salida.append({
            "id_inversor": envio.id_inversor,
            "nombre": envio.nombre,
            "to": envio.to,
            "cc": envio.cc,
            "bcc": envio.bcc,
            "asunto": envio.asunto,
            "cuerpo_html": envio.cuerpo_html,
            "cuerpo_texto": plantillas.a_texto_plano(envio.cuerpo_html),
            "adjuntos": [{"nombre": a.nombre, "drive_file_id": a.drive_file_id,
                          "tamano_bytes": a.tamano_bytes} for a in envio.adjuntos],
        })

    print(json.dumps({
        "paquete_id": paq.paquete_id,
        "remitente": paq.remitente or ajustes.get("remitente", ""),
        "limite_adjunto_mb": (ajustes.get("adjuntos") or {}).get("limite_mb", 18),
        "total_listos": len(salida),
        "omitidos_por_duplicado": omitidos_por_duplicado,
        "envios": salida,
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_registrar(args: argparse.Namespace) -> int:
    """Deja constancia de un borrador creado en Gmail y actualiza el paquete."""
    paq = mod_paquete.Paquete.cargar(args.id)
    envio = next((e for e in paq.envios if e.id_inversor == args.inversor), None)
    if envio is None:
        print("El inversor '%s' no esta en el paquete '%s'." % (args.inversor, args.id))
        return 1

    if args.error:
        envio.estado = mod_paquete.ERROR
        envio.notas = (envio.notas + " | " if envio.notas else "") + args.error
        bitacora.registrar(paq.paquete_id, envio.id_inversor, "error", asunto=envio.asunto,
                           to=envio.to, cc=envio.cc, bcc=envio.bcc, detalle=args.error)
        paq.guardar()
        print("Registrado el error de %s." % envio.id_inversor)
        return 0

    envio.estado = mod_paquete.BORRADOR_CREADO
    envio.draft_id = args.draft_id or ""
    bitacora.registrar(paq.paquete_id, envio.id_inversor, "borrador_creado",
                       draft_id=envio.draft_id, asunto=envio.asunto, to=envio.to,
                       cc=envio.cc, bcc=envio.bcc,
                       adjuntos=[a.nombre for a in envio.adjuntos])
    paq.guardar()
    print("Borrador registrado: %s -> %s" % (envio.id_inversor, envio.draft_id or "(sin id)"))
    return 0


def cmd_adjuntar(args: argparse.Namespace) -> int:
    """Asocia un archivo de Drive como adjunto de uno o varios envios."""
    paq = mod_paquete.Paquete.cargar(args.id)
    ajustes = cargar_ajustes()
    limite = float((ajustes.get("adjuntos") or {}).get("limite_mb", 18)) * 1024 * 1024

    if args.tamano_bytes and args.tamano_bytes > limite:
        print("AVISO: '%s' pesa %.1f MB y el tope util para adjuntar es %.0f MB."
              % (args.nombre, args.tamano_bytes / 1024 / 1024, limite / 1024 / 1024))
        print("Gmail rechazaria el borrador. Considera enlazar el archivo en el cuerpo.")
        if not args.forzar:
            return 1

    objetivo = ({p.strip() for p in args.inversor.split(",") if p.strip()} if args.inversor else None)
    tocados = 0
    for envio in paq.envios:
        if objetivo is not None and envio.id_inversor not in objetivo:
            continue
        if any(a.drive_file_id == args.drive_file_id for a in envio.adjuntos):
            continue
        envio.adjuntos.append(mod_paquete.Adjunto(
            nombre=args.nombre, drive_file_id=args.drive_file_id,
            tamano_bytes=args.tamano_bytes or 0, mime_type=args.mime_type or ""))
        tocados += 1
    paq.guardar()
    print("Adjunto '%s' asociado a %d envios." % (args.nombre, tocados))
    return 0


def cmd_bitacora(args: argparse.Namespace) -> int:
    eventos = bitacora.leer(args.id)
    if not eventos:
        print("Bitacora vacia.")
        return 0
    for evento in eventos[-args.ultimos:]:
        print("  %s  %-22s %-18s %-16s %s"
              % (evento["momento"], str(evento["paquete_id"])[:22], str(evento["id_inversor"])[:18],
                 evento["accion"], evento.get("draft_id") or evento.get("detalle") or ""))
    return 0


# --------------------------------------------------------------------------
def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ag", description="Comunicaciones a inversores de Andy Garden")
    subs = parser.add_subparsers(dest="subcomando", required=True)

    p = subs.add_parser("validar", help="lee el padron y reporta problemas")
    p.add_argument("--padron", help="ruta del padron (ignora la de ajustes.yaml)")
    p.set_defaults(funcion=cmd_validar)

    p = subs.add_parser("plantillas", help="lista las plantillas y sus campos")
    p.set_defaults(funcion=cmd_plantillas)

    p = subs.add_parser("generar", help="crea un paquete de envio a demanda")
    p.add_argument("--id", required=True, help="identificador del paquete, p.ej. 2026-08-avance-obra")
    p.add_argument("--titulo", required=True, help="descripcion legible de la comunicacion")
    p.add_argument("--plantilla", required=True, help="archivo de config/plantillas")
    p.add_argument("--asunto", required=True, help="asunto base, admite {{campos}}")
    p.add_argument("--padron", help="ruta del padron")
    p.add_argument("--campo", action="append", metavar="CLAVE=VALOR",
                   help="valor comun para un campo de la plantilla (repetible)")
    p.add_argument("--incluir", help="solo estos id de inversor, separados por coma")
    p.add_argument("--excluir", help="excluye estos id de inversor")
    p.add_argument("--incluir-todos", action="store_true",
                   help="incluye tambien inversores pausados o salidos")
    p.add_argument("--notas", help="nota interna del paquete")
    p.add_argument("--forzar", action="store_true", help="genera aunque el padron tenga errores")
    p.add_argument("--sobrescribir", action="store_true",
                   help="reemplaza un paquete existente con el mismo id, perdiendo sus ediciones")
    p.set_defaults(funcion=cmd_generar)

    p = subs.add_parser("estado", help="resumen de un paquete o de todos")
    p.add_argument("id", nargs="?", help="id del paquete; omitelo para ver la lista")
    p.set_defaults(funcion=cmd_estado)

    p = subs.add_parser("exportar", help="escribe el CSV que se sube a Drive")
    p.add_argument("id")
    p.add_argument("--salida", help="ruta del CSV de salida")
    p.set_defaults(funcion=cmd_exportar)

    p = subs.add_parser("importar", help="aplica al paquete lo editado en la hoja de Drive")
    p.add_argument("id")
    p.add_argument("--csv", required=True, help="CSV descargado de la hoja")
    p.add_argument("--simular", action="store_true", help="muestra los cambios sin guardarlos")
    p.set_defaults(funcion=cmd_importar)

    p = subs.add_parser("aprobar", help="marca envios como listos para generar borrador")
    p.add_argument("id")
    p.add_argument("--inversor", help="id concretos separados por coma; omitelo para todos")
    p.set_defaults(funcion=cmd_aprobar)

    p = subs.add_parser("omitir", help="excluye envios de esta comunicacion")
    p.add_argument("id")
    p.add_argument("--inversor", required=True)
    p.add_argument("--motivo")
    p.set_defaults(funcion=cmd_omitir)

    p = subs.add_parser("adjuntar", help="asocia un archivo de Drive a los envios")
    p.add_argument("id")
    p.add_argument("--nombre", required=True)
    p.add_argument("--drive-file-id", required=True)
    p.add_argument("--tamano-bytes", type=int)
    p.add_argument("--mime-type")
    p.add_argument("--inversor", help="id concretos separados por coma; omitelo para todos")
    p.add_argument("--forzar", action="store_true", help="adjunta aunque supere el tope de tamano")
    p.set_defaults(funcion=cmd_adjuntar)

    p = subs.add_parser("pendientes", help="JSON de los envios listos para crear borrador")
    p.add_argument("id")
    p.add_argument("--rehacer", action="store_true",
                   help="incluye tambien los que ya tienen borrador en la bitacora")
    p.set_defaults(funcion=cmd_pendientes)

    p = subs.add_parser("registrar", help="anota el borrador creado (o el error) de un envio")
    p.add_argument("id")
    p.add_argument("--inversor", required=True)
    p.add_argument("--draft-id")
    p.add_argument("--error", help="registra un fallo en lugar de un borrador")
    p.set_defaults(funcion=cmd_registrar)

    p = subs.add_parser("bitacora", help="muestra el historial de acciones")
    p.add_argument("id", nargs="?")
    p.add_argument("--ultimos", type=int, default=40)
    p.set_defaults(funcion=cmd_bitacora)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    return args.funcion(args)


if __name__ == "__main__":
    raise SystemExit(main())
