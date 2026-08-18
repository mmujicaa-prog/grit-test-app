# Comunicaciones a inversores — Andy Garden

Prepara comunicaciones **individuales** a los inversores del proyecto Andy Garden y las
deja como **borradores en la carpeta de Borradores** de `mm@ardatz.com`, uno por inversor,
con su propio asunto, su propio cuerpo, sus propias copias y sus propios adjuntos.

**El sistema nunca envía correo.** El envío lo haces tú, borrador a borrador.

Las comunicaciones se preparan a demanda, cuando las pidas. No hay calendario.

```
andy_garden/
├── config/
│   ├── ajustes.yaml          remitente, ubicación del padrón, tope de adjuntos, firma
│   └── plantillas/           cuerpos de correo en HTML
├── datos/                    el padrón (padron_ejemplo.csv es ficticio)
├── paquetes/<id>/            paquete.json + paquete.csv de cada comunicación
├── tools/                    ag.py y los módulos de datos
├── consola/                  consola web de revisión
├── docs/                     PADRON.md y OPERACION.md
└── bitacora.jsonl            registro de todo borrador creado
```

## Empezar

```bash
python3 andy_garden/tools/ag.py validar --padron andy_garden/datos/padron_ejemplo.csv
python3 andy_garden/tools/ag.py estado
python3 andy_garden/tools/ag.py plantillas
```

En una sesión de Claude Code basta con pedírselo al agente `andy-garden-comms`:

> Prepara el avance de obra de septiembre para todos los inversores activos, con el
> informe de obra adjunto.

## Datos reales

Este repositorio es **público**. `.gitignore` impide versionar el padrón, los paquetes y la
bitácora: sólo se versiona el material ficticio de ejemplo. Lo que debe perdurar va a
Drive, porque el contenedor de trabajo es efímero. Ver
[docs/OPERACION.md](docs/OPERACION.md#dónde-vive-cada-cosa).

## Documentación

- **[docs/PADRON.md](docs/PADRON.md)** — qué columnas debe tener tu padrón y qué tolera el lector.
- **[docs/OPERACION.md](docs/OPERACION.md)** — el recorrido completo, paso a paso.

## Requisitos

Python 3.11+ y PyYAML. `openpyxl` es opcional: sin él, los `.xlsx` se leen con un lector
propio de la biblioteca estándar.

```bash
pip install -r andy_garden/requirements.txt
```
