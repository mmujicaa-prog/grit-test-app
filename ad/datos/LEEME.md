# Datos de inversores — Agnessa Dom

Esta carpeta contiene el padrón real de inversores y está excluida del repositorio
por `.gitignore`. Su contenido no se versiona porque este repositorio es público.

Para trabajar con el padrón:

1. Copia aquí el archivo `padron.csv` con los datos reales de inversores.
2. Actualiza `ad/config/ajustes.yaml` → `padron.ruta` con la ruta o el ID de Drive.
3. Ejecuta `python3 ad/tools/ag.py validar` antes de generar cualquier paquete.

El archivo `padron_ejemplo.csv` (sí versionado) contiene datos ficticios de
demostración y sirve como referencia del formato esperado.
