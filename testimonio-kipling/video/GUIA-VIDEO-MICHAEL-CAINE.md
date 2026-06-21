# Guía de montaje · Vídeo de cierre con Michael Caine

Cierre de la charla: Michael Caine recitando *If—* de Kipling, con subtítulos en español.

---

## 1. Localizar el clip
- Busca en YouTube: **"Michael Caine If Kipling"**.
- La lectura más difundida de Caine dura **~2 minutos**: voz grave, ritmo lento, pausas dramáticas. Es la idónea para el cierre.
- **Descárgalo en local** (no dependas de streaming en directo el día del evento).

> ⚖️ **Derechos:** la grabación de Caine es contenido protegido. Para un evento privado/sin ánimo de lucro suele ser aceptable. Si vas a **grabar o publicar** tu charla, cita la fuente en los créditos y valora usar solo un fragmento breve o pedir permiso.

---

## 2. Subtítulos en español (ya hechos)
Archivo: **`subtitulos-if-michael-caine-ES.srt`** (en esta misma carpeta).

- Traducción literaria que respeta la cadencia del poema.
- 17 cues, temporizados para una recitación de ~2 min con pausas.
- 2 líneas por subtítulo, legibles desde el fondo de la sala.

### ⚠️ Ajuste de sincronía (importante)
Las marcas de tiempo del `.srt` son una **estimación** sobre una lectura de ~2:08.
Tu clip concreto puede empezar antes/después o tener otro ritmo. Haz esto:

1. Abre el vídeo + el `.srt` en un editor (CapCut, DaVinci Resolve —gratis—, Premiere, o el editor de subtítulos de YouTube).
2. Reproduce y comprueba que cada verso aparece **justo cuando Caine lo dice**.
3. Si todo va adelantado/atrasado por igual, aplica un **desplazamiento global** (shift) de todos los subtítulos.
4. Si hay desajustes puntuales (sus pausas), arrastra esos cues uno a uno.
5. Respeta sus silencios: deja que el subtítulo desaparezca en las pausas largas.

---

## 3. Estilo visual de los subtítulos
- **Posición:** tercio inferior, con margen de seguridad.
- **Color:** blanco con sombra suave o caja semitransparente (legible sobre cualquier fondo).
- **Tamaño:** grande.
- **Máximo 2 líneas**, ~42 caracteres por línea.
- **Fuente:** sans limpia (Inter, Helvetica) o la serif de tu presentación si quieres coherencia.

---

## 4. Cómo "quemar" los subtítulos (opciones)
- **Fácil:** CapCut o DaVinci Resolve → importar vídeo + `.srt` → exportar con subtítulos incrustados.
- **Avanzado (ffmpeg):**
  ```
  ffmpeg -i caine_if.mp4 -vf "subtitles=subtitulos-if-michael-caine-ES.srt:force_style='FontSize=24,PrimaryColour=&HFFFFFF&,Outline=2'" salida_subtitulada.mp4
  ```
- **En directo:** algunos reproductores cargan el `.srt` junto al vídeo si tienen el mismo nombre. Menos fiable en proyectores ajenos → mejor incrustarlos.

---

## 5. Checklist del día del evento
- [ ] Vídeo final (con subtítulos incrustados) en **local**, en el portátil de la presentación.
- [ ] **Copia de seguridad** en un segundo dispositivo / USB.
- [ ] Probado en el **proyector y sonido reales** de la sala.
- [ ] Volumen ajustado (la voz de Caine debe llenar la sala sin saturar).
- [ ] Tu **frase-puente** ensayada justo antes: *"Hay un hombre que lo dice mejor que yo."*
- [ ] Durante el vídeo: te quedas quieto, mirando la pantalla con el público. No hablas.
- [ ] Tras el vídeo: 2-3 s de silencio antes de tu frase final + "Gracias".

---

## 6. El texto (referencia)
La traducción usada en el `.srt` está alineada verso a verso con el original.
Si prefieres otra versión española (existen varias literarias célebres), avísame
y reajusto el `.srt` manteniendo la temporización.
