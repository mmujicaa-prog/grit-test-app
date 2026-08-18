# Cómo se opera

El sistema prepara comunicaciones **individuales** a los inversores de Andy Garden y las
deja como **borradores en tu carpeta de Borradores**. Nada se envía solo: tú abres cada
borrador y lo envías cuando quieras.

No hay calendario. Cada comunicación nace cuando tú la pides.

## Las piezas

| Pieza | Qué es |
|---|---|
| **Padrón** | Tu archivo de inversores. Ver [PADRON.md](PADRON.md) |
| **Plantilla** | El cuerpo base de un tipo de comunicación, en `config/plantillas/` |
| **Paquete** | Una comunicación concreta × sus inversores. Un envío por inversor |
| **Consola** | `consola/andy_garden_comms.html`: revisión visual del paquete |
| **Hoja de Drive** | El mismo paquete como hoja editable desde el móvil |
| **Agente** | `andy-garden-comms`: quien habla con Gmail y Drive |
| **Bitácora** | `bitacora.jsonl`: registro de todo borrador creado |

## El recorrido normal

Se lo pides al agente en lenguaje natural — *"prepara el avance de obra de septiembre
para todos los inversores, con el informe adjunto"* — y él recorre estos pasos. Puedes
hacerlos tú a mano si prefieres.

### 1. Validar el padrón

```bash
python3 andy_garden/tools/ag.py validar
```

Si hay errores, se corrigen antes de seguir. Nunca se generan correos sobre un padrón roto.

### 2. Generar el paquete

```bash
python3 andy_garden/tools/ag.py generar \
  --id 2026-09-avance-obra \
  --titulo "Avance de obra — septiembre 2026" \
  --plantilla avance_proyecto.html \
  --asunto "Andy Garden · Avance de obra {{periodo}} — {{nombre}}" \
  --campo periodo="septiembre de 2026"
```

- `--id` identifica el paquete para siempre. Usa `AAAA-MM-asunto`.
- `--campo` rellena lo que es igual para todos.
- `--incluir INV-001,INV-004` limita la comunicación a inversores concretos.
- `--incluir-todos` alcanza también a pausados y salidos.

Lo que no se pudo rellenar sale listado: es tu lista de trabajo.

### 3. Escribir el contenido de cada uno

El paquete se genera en `paquetes/<id>/`: `paquete.json` (el dato) y `paquete.csv` (la
hoja). Dos formas de trabajarlo, sobre el mismo contenido:

**Consola.** Abre `consola/andy_garden_comms.html` en el navegador o su versión publicada,
carga el `paquete.json` y edita envío a envío: asunto, cuerpo, copias, con vista previa del
correo tal como lo recibirá el inversor. Al terminar, **Copiar JSON** y pega el resultado
sobre `paquetes/<id>/paquete.json`.

> La consola copia al portapapeles en lugar de descargar porque el visor de artefactos
> bloquea las descargas.

**Hoja de Drive.** El agente sube `paquete.csv` a Drive como hoja de cálculo. La editas
desde donde estés y, cuando termines, se aplica de vuelta:

```bash
python3 andy_garden/tools/ag.py importar 2026-09-avance-obra --csv descargado.csv --simular
python3 andy_garden/tools/ag.py importar 2026-09-avance-obra --csv descargado.csv
```

`--simular` enseña los cambios sin guardarlos. La hoja manda sobre asunto, cuerpo, copias,
adjuntos, estado y notas; el `draft_id` nunca se toma de la hoja, es registro del sistema.

### 4. Adjuntos

```bash
python3 andy_garden/tools/ag.py adjuntar 2026-09-avance-obra \
  --nombre "Informe_septiembre.pdf" --drive-file-id "1AbC..." \
  --tamano-bytes 2410233 --inversor INV-001
```

Sin `--inversor` el adjunto va a todos. El tope es 18 MB por defecto, no 25: el adjunto
viaja codificado en base64 y crece cerca de un tercio, así que un archivo de 20 MB
produciría un mensaje que Gmail rechaza. Si un archivo lo supera, enlázalo en el cuerpo.

### 5. Aprobar

```bash
python3 andy_garden/tools/ag.py aprobar 2026-09-avance-obra
```

Sólo aprueba lo que está completo. Deja fuera, diciéndolo, lo que tenga campos sin
resolver, falte destinatario, asunto o cuerpo. También puedes aprobar desde la consola.

Para dejar a alguien fuera de esta comunicación:

```bash
python3 andy_garden/tools/ag.py omitir 2026-09-avance-obra --inversor INV-003 --motivo "salió del vehículo"
```

### 6. Crear los borradores

Esto lo hace el agente: lee `ag.py pendientes <id>`, descarga los adjuntos de Drive y crea
un borrador por inversor en tu cuenta. Después de cada uno lo registra, así que si el
proceso se interrumpe se retoma sin duplicar nada.

### 7. Enviar

Tú, desde Gmail, uno a uno.

## Cómo se evita mandar algo dos veces

Tres capas:

1. El agente tiene prohibido `send_message`. Su única salida es `create_draft`.
2. `pendientes` descarta a quien la bitácora dice que ya tiene borrador de ese paquete.
3. El agente consulta además los borradores reales de Gmail, por si creaste alguno a mano.

Y `generar` se niega a sobrescribir un paquete existente sin `--sobrescribir`, para que
regenerar no borre textos ya escritos.

## Dónde vive cada cosa

`grit-test-app` es un repositorio **público**, así que ningún dato real de inversores se
versiona. `.gitignore` bloquea `datos/`, `paquetes/` y `bitacora.jsonl`; sólo se versiona
el material ficticio de ejemplo.

| Dato | Dónde perdura |
|---|---|
| Padrón | Drive (tuyo). En `datos/` sólo hay copias de trabajo temporales |
| Paquete de una comunicación | Drive, como hoja. El JSON local se pierde con el contenedor |
| Bitácora de borradores | Drive. El agente sube una copia al cerrar cada tanda |
| Código, plantillas, consola, documentación | El repositorio |

El contenedor donde corre todo esto es efímero: lo que no suba a Drive desaparece. Por eso
el agente sube el paquete y la bitácora al terminar.

Si prefieres que el histórico quede versionado junto al código, la vía limpia es mover
este sistema a un repositorio privado y retirar esas reglas de `.gitignore`.

## Estados de un envío

| Estado | Significa |
|---|---|
| `pendiente_revision` | Recién generado, esperando que lo revises |
| `aprobado` | Revisado y completo, listo para convertirse en borrador |
| `borrador_creado` | Ya está en tu carpeta de Borradores |
| `omitido` | Decidiste no incluirlo en esta comunicación |
| `error` | No se pudo crear el borrador. El motivo está en `notas` |

## Consultas

```bash
python3 andy_garden/tools/ag.py estado                      # todos los paquetes
python3 andy_garden/tools/ag.py estado 2026-09-avance-obra  # detalle de uno
python3 andy_garden/tools/ag.py bitacora                    # historial completo
python3 andy_garden/tools/ag.py plantillas                  # plantillas y sus campos
```

La pestaña **Histórico** de la consola cruza inversores × comunicaciones: carga varios
`paquete.json` a la vez y verás de un vistazo qué ha recibido cada uno.

## Plantillas

Están en `config/plantillas/`, son HTML con estilos en línea (los clientes de correo
ignoran las hojas de estilo) y sin imágenes externas (evita el aviso de "mostrar contenido
remoto").

| Plantilla | Para |
|---|---|
| `generica.html` | Cualquier comunicación puntual |
| `avance_proyecto.html` | Reporte de avance del proyecto |
| `distribucion.html` | Aviso de distribución o pago |
| `documento_firma.html` | Envío de un documento para firma |

`_base.html` es el envoltorio común: cabecera, cuerpo, firma y pie de confidencialidad.
Para una plantilla nueva, copia una existente, cambia el contenido y usa `{{campos}}`
donde el texto dependa del inversor. Los campos que no se resuelvan bloquean la
aprobación, así que sirven como recordatorio de lo que falta por escribir.

Si añades una plantilla y quieres ver qué campos espera:

```bash
python3 andy_garden/tools/ag.py plantillas
```

## Mantenimiento

Tras cambiar el paquete de ejemplo, vuelve a incrustarlo en la consola:

```bash
python3 andy_garden/tools/incrustar_ejemplo.py 2026-08-avance-obra
```
