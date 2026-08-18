# El padrón de inversores

El padrón lo mantienes tú, en el archivo y el sitio que prefieras. El sistema se
adapta a él, no al revés: lee Google Sheets exportado a CSV, Excel (`.xlsx`), CSV,
TSV y JSON, y **no exige nombres de columna exactos**.

Cuando lo tengas listo, indica su ubicación en `config/ajustes.yaml`:

```yaml
padron:
  ruta: "sheet:1AbC..."   # id de Google Sheet
  # ruta: "drive:1AbC..." # id de archivo en Drive
  # ruta: "datos/padron.xlsx"  # ruta dentro del repositorio
  hoja: "Inversores"      # nombre de la pestaña, si hay varias
```

## Columnas

Sólo dos son obligatorias: **nombre** y **correo principal**. El resto mejora la
personalización de los correos, pero el sistema funciona sin ellas.

| Campo | Para qué se usa | Sinónimos que se reconocen |
|---|---|---|
| `id_inversor` | Clave única. Evita duplicados y permite dirigirse a un inversor concreto. Si falta, se deriva del nombre | id, código, identificador, RUT, NIF, DNI, CIF |
| `nombre` **(obligatorio)** | Saludo y asunto | nombre completo, razón social, inversor, cliente, titular |
| `tratamiento` | Encabezado del saludo (`Estimado`, `Estimada`, `Estimados`) | saludo, trato, título |
| `email_principal` **(obligatorio)** | Destinatario (To) | email, correo, correo electrónico, mail, correo del inversor |
| `emails_copia` | Copia (CC). Varios separados por `;` | cc, copia, copias, en copia, con copia |
| `emails_copia_oculta` | Copia oculta (BCC) | bcc, cco, copia oculta |
| `monto_comprometido` | Campo de combinación `{{monto}}` | monto, importe, aporte, capital, inversión, compromiso |
| `moneda` | Campo `{{moneda}}` | divisa, currency |
| `porcentaje` | Campo `{{porcentaje}}` | participación, cuota, pct |
| `fecha_ingreso` | Campo `{{fecha_ingreso}}` | fecha, fecha de inversión, fecha de entrada, fecha de suscripción |
| `tramo` | Distinguir series o grupos con condiciones distintas | serie, grupo, clase, categoría |
| `estado` | Filtra a quién se le genera comunicación | status, situación, vigencia |
| `idioma` | `es` / `en` | lengua, language |
| `notas` | Contexto que verás al revisar. No viaja en el correo | observaciones, comentarios |

### Lo que el lector tolera

- **Preposiciones en los encabezados.** "Fecha de ingreso", "Correo del inversor" y
  "Nombre del titular" se reconocen igual que sus formas cortas.
- **Mayúsculas, tildes y espacios.** "PARTICIPACIÓN" y "participacion" son lo mismo.
- **Filas de título encima de la tabla.** Busca la primera fila que parezca cabecera
  dentro de las 20 primeras.
- **Correos con nombre.** `Luis Ficticio <luis@ejemplo.com>` se reduce a la dirección.
- **Varios correos en una celda**, separados por `;`, `,` o salto de línea.
- **Formatos de fecha** `dd/mm/aaaa`, `aaaa-mm-dd`, `dd-mm-aaaa` y el número de serie de Excel.
- **Columnas propias.** Cualquier columna que no esté en la tabla anterior se conserva
  y queda disponible como campo de combinación con su propio nombre. Si añades una
  columna "Banco", en las plantillas tendrás `{{banco}}`.

### Estado

Se normaliza a tres valores. Por defecto sólo se comunica con los **activos**:

| Valor | Se escribe también | Recibe comunicaciones |
|---|---|---|
| `activo` | activa, vigente, sí, ok, 1, celda vacía | Sí |
| `pausado` | pausada, suspendido, en pausa, espera | No, salvo `--incluir-todos` |
| `salido` | retirado, baja, inactivo, no, cerrado | No, salvo `--incluir-todos` |

## Validación

Antes de generar nada, comprueba el padrón:

```bash
python3 andy_garden/tools/ag.py validar --padron datos/padron.xlsx
```

Distingue **errores**, que impiden generar, de **avisos**, que sólo informan:

| Nivel | Caso |
|---|---|
| Error | Falta el nombre o el correo principal |
| Error | Correo con formato inválido, en el destinatario o en las copias |
| Error | Id de inversor repetido |
| Error | No se reconoce ninguna columna |
| Aviso | El correo principal aparece también en copia (se quita el duplicado) |
| Aviso | Un correo se repite entre CC y BCC (se deja sólo en CC) |
| Aviso | Dos inversores comparten correo principal: recibirían dos borradores |
| Aviso | Estado no reconocido |

## Ejemplo

`datos/padron_ejemplo.csv` es un padrón completo con inversores ficticios: tiene fila de
título, encabezados en lenguaje natural, copias múltiples, un correo con nombre entre
ángulos y un inversor dado de baja. Sirve de referencia de formato y para probar el
sistema sin tocar datos reales.
