# Esta carpeta no se versiona

`.gitignore` bloquea todo lo que hay aquí salvo `padron_ejemplo.csv`, porque el
repositorio `grit-test-app` es **público** y el padrón contiene datos personales y
financieros de los inversores.

El padrón real vive en Drive. Lo que aparezca en esta carpeta es una copia de trabajo
temporal que el agente descarga para procesar y que desaparece con el contenedor.

Lo mismo vale para `../paquetes/` (cuerpos de correo y destinatarios reales) y para
`../bitacora.jsonl` (registro de borradores creados). La copia que perdura de todo eso
va a Drive, no a git.

Si prefieres que el histórico sí quede versionado, la vía correcta es mover este sistema
a un repositorio privado y quitar estas reglas de `.gitignore`.
