#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera la presentación 'Si' (testimonio + If de Kipling) en formato .pptx.
Tema oscuro, versos en serif, palabra-ancla en acento, guion completo en notas del orador."""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# --- Paleta ---
BG      = RGBColor(0x0D, 0x0D, 0x0D)   # fondo casi negro
WHITE   = RGBColor(0xF2, 0xF0, 0xEB)   # blanco roto (texto)
ACCENT  = RGBColor(0xC9, 0xA2, 0x27)   # dorado tenue (palabra-ancla)
MUTED   = RGBColor(0x8A, 0x8A, 0x8A)   # gris (apoyos)

SERIF = "Georgia"
SANS  = "Calibri"

prs = Presentation()
prs.slide_width  = Inches(13.333)   # 16:9
prs.slide_height = Inches(7.5)
SW, SH = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]

def slide(notes=""):
    s = prs.slides.add_slide(BLANK)
    # fondo
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s

def textbox(s, text, *, font=SANS, size=28, color=WHITE, bold=False, italic=False,
            align=PP_ALIGN.CENTER, top=None, height=None, left=Inches(1), width=None):
    if width is None:
        width = SW - Inches(2)
    if top is None:
        top = Inches(3)
    if height is None:
        height = Inches(1.5)
    tb = s.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run(); r.text = text
    f = r.font
    f.name = font; f.size = Pt(size); f.bold = bold; f.italic = italic
    f.color.rgb = color
    return tb

def verse_slide(verse, anchor_word, notes):
    """Slide de verso: verso en serif + palabra-ancla grande en dorado debajo."""
    s = slide(notes)
    textbox(s, anchor_word.upper(), font=SANS, size=20, color=ACCENT, bold=True,
            top=Inches(1.0), height=Inches(0.8))
    tb = s.shapes.add_textbox(Inches(1.2), Inches(2.4), SW - Inches(2.4), Inches(3))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = verse
    f = r.font; f.name = SERIF; f.size = Pt(34); f.italic = True; f.color.rgb = WHITE
    return s

def line_slide(text, notes, color=WHITE, size=34, font=SERIF, italic=True):
    s = slide(notes)
    textbox(s, text, font=font, size=size, color=color, italic=italic,
            top=Inches(2.6), height=Inches(2.3))
    return s

def black_slide(notes, hint=""):
    s = slide(notes)
    if hint:
        textbox(s, hint, font=SANS, size=14, color=RGBColor(0x33,0x33,0x33),
                top=Inches(6.7), height=Inches(0.5))
    return s

def photo_slide(placeholder, notes):
    """Slide pensado para una foto: deja un marco/etiqueta de marcador de posición."""
    s = slide(notes)
    box = s.shapes.add_textbox(Inches(2.5), Inches(3.0), SW - Inches(5), Inches(1.5))
    tf = box.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = "🖼️  " + placeholder
    f = r.font; f.name = SANS; f.size = Pt(18); f.color.rgb = MUTED; f.italic = True
    return s

def title_slide(title, subtitle, notes):
    s = slide(notes)
    textbox(s, title, font=SERIF, size=72, color=WHITE, top=Inches(2.6), height=Inches(1.6))
    if subtitle:
        textbox(s, subtitle, font=SANS, size=22, color=MUTED, top=Inches(4.3), height=Inches(1))
    return s

# ============================================================
# SLIDES (sincronizados con GUION-DESARROLLADO.md)
# ============================================================

# 0 — Pre-charla
title_slide("Si", "Miguel Mujica  ·  un testimonio sobre el poema «If» de Rudyard Kipling",
    "PANTALLA PREVIA mientras entra el público. No empieces hasta el silencio.")

# 1 — HOOK
black_slide(
    "HOOK (negro total).\n\n"
    "\"Hay una puerta. Y detrás de ella, mi familia espera. Felices. Aguardando que yo salga "
    "con dos buenas noticias: acaban de nacer mis mellizos.\"\n\n(Pausa.)",
    "")

# 2 — HOOK
black_slide(
    "HOOK (sigue en negro).\n\n"
    "\"Pero de este lado de la puerta, yo acabo de ver cómo un equipo de médicos se lanzaba "
    "sobre mi segundo hijo. Azul. Inerte. Peleando por devolverlo a la vida.\"\n\n"
    "(Pausa, más lento.)\n"
    "\"Y ahora tengo que poner la mano en el pomo… y salir a dar calma. A contener a todos. "
    "Mientras por dentro me estoy muriendo.\"\n\n"
    "(Silencio. 3 segundos.)\n"
    "\"Tenía que mantener la cabeza cuando todo —dentro de mí— se derrumbaba. Lo que yo no sabía "
    "entonces… es que un poema escrito hace más de cien años ya me había explicado cómo.\"",
    "")

# 3 — PROMESA (título poema)
title_slide("If —", "",
    "PROMESA (sube luz suave, apareces).\n\n"
    "\"Me llamo Miguel Mujica. Y durante años llevé un poema en el bolsillo. No es mío: lo escribió "
    "Rudyard Kipling hace más de un siglo, para su hijo. Se llama If — Si.\"")

# 4 — PROMESA (mapa)
photo_slide("Tu mano con el poema / un libro gastado  (opcional; si no, deja negro)",
    "\"Yo no lo leí como literatura. Lo leí como un mapa. Cada vez que la vida me ponía a prueba, "
    "una de sus líneas me decía qué clase de hombre tenía que ser para salir adelante.\"\n\n"
    "\"Hoy quiero contaros mi historia a través de ese mapa. Cuatro pruebas. Cuatro versos. Y al "
    "final, dejaré que un hombre os lea el poema entero, mucho mejor de lo que yo podría hacerlo. "
    "Empecemos por esa puerta.\"")

# 5 — ACTO I verso
verse_slide("«Si puedes mantener la cabeza cuando todos a tu alrededor\nla pierden y te culpan a ti…»",
    "Serenidad",
    "ACTO I — SERENIDAD (luz baja, voz en confidencia). Lee el verso despacio. Pausa 2 s.")

# 6 — ACTO I historia (negro)
black_slide(
    "ACTO I — historia (negro, máxima intimidad).\n\n"
    "\"Volvamos a esa sala de partos. Nace mi primer hijo. Llora. Respira. Está vivo, está perfecto. "
    "Y por un instante el mundo es exactamente como lo había soñado.\"\n"
    "\"Pero esperábamos mellizos. Detrás venía el segundo.\"\n\n"
    "(Bajar el ritmo.)\n"
    "\"Iñaki nace azul. Inerte. No llora. No se mueve.\"\n"
    "(Silencio 2-3 s.) \"No respira.\"\n"
    "\"Y entonces la sala estalla. El equipo médico se lanza sobre él. Reanimación. Unos segundos "
    "que duran años.\"\n\n"
    "(Tensión.)\n"
    "\"Y yo sabía algo que no podía probar. Lo intuía: aquello quizá podría haberse evitado. Algo se "
    "había retrasado más de la cuenta. Sentí subir la rabia… pero ese no era el momento de la rabia.\"\n\n"
    "(Payoff del hook: cruzamos la puerta.)\n"
    "\"Y así llegué a aquella puerta del principio. Detrás esperaba mi familia, feliz, aguardando dos "
    "buenas noticias. Y me tocaba a mí salir y contarles lo de Iñaki.\"\n"
    "\"Era el minuto de dar calma. De contener. De sostener a todos los demás… mientras yo me moría "
    "por dentro. Salí. Di la calma. Y solo cuando todos estuvieron tranquilos, me permití temblar.\"\n\n"
    "(Desenlace sobrio.)\n"
    "\"Tres días luchando por su vida. Dos semanas en la UCI. Iñaki sobrevivió. Vive. Con secuelas, "
    "sí. Pero vive.\"",
    "")

# 7 — ACTO I cierre
line_slide("La serenidad no es la ausencia de la tormenta.\nEs lo que decides hacer dentro de ella.",
    "Cierre del acto, mirando al público:\n\n"
    "\"Ese día aprendí que mantener la cabeza no es dejar de sentir. Es sentirlo todo —el miedo, la "
    "rabia, el dolor— y aun así ser el lugar firme donde los demás se apoyan…\"")

# 8 — ACTO II verso
verse_slide("«Si puedes encontrarte con el Triunfo y el Desastre\ny tratar igual a esos dos impostores…»",
    "Equilibrio",
    "ACTO II — EQUILIBRIO (tono narrativo). Lee el verso.\n\n"
    "\"Impostores. Esa palabra me costó años entenderla. Dejadme contaros por qué.\"")

# 9 — ACTO II triunfo (foto)
photo_slide("Un hito urbano / proyecto de Parque Arauco que lideraste  (o logo PA)",
    "EL TRIUNFO.\n\n"
    "\"Tras años aprendiendo de grandes jefes, me invitan a una gran compañía: Parque Arauco. Empresa "
    "en bolsa, recién capitalizada nada menos que por Sam Zell, el gurú inmobiliario norteamericano, "
    "con un plan de expansión por toda la región. Y me piden a mí que lidere esa expansión.\"\n"
    "\"Era jugar en una liga de clase mundial. Y jugué. Los proyectos volaban, creábamos hitos urbanos, "
    "trataba a diario con la alta dirección. Se me abrían todas las puertas. Mi prestigio tocaba techo. "
    "Todo fluía.\"\n\n"
    "(El precio oculto.)\n"
    "\"El triunfo, eso sí, cobraba su precio en silencio: vivía más fuera de casa que dentro, la espalda "
    "empezó a pasarme factura, el estrés era brutal. Pero… ¿quién se queja cuando todo brilla?\"")

# 10 — ACTO II giro (negro)
black_slide(
    "EL GIRO.\n\n"
    "\"Hasta que un día me avisan: el vicepresidente ejecutivo se va. Llega otro. Y en menos de seis "
    "meses, el nuevo decide reestructurar la compañía y desarmar, entera, el área de expansión. Mi área.\"\n"
    "\"Me ofrecen dos caminos: seguir desde fuera, como externo, o quedarme dentro… en un puesto que era, "
    "claramente, un paso atrás.\"\n"
    "(Pausa.) \"En ese minuto, todo se venía abajo. ¿Qué hago? ¿Cómo lo hago?\"\n\n"
    "(La reconstrucción.)\n"
    "\"Decidí independizarme. Montar mi propia empresa de servicios inmobiliarios de alta especialización.\"\n"
    "\"Y ahí descubrí lo que de verdad significa reconstruir con las herramientas gastadas. Porque "
    "emprender es difícil… pero más difícil es domar el ego.\"\n"
    "\"Mi antiguo equipo pasó a ser mi cliente. Cada vez que llegaba a las oficinas de Chile, de Perú, "
    "de Colombia, tenía que presentarme. Esperar a que me recibieran. Perseguir el pago de mis facturas.\"\n"
    "\"Pasé de ser el jefe exitoso a un proveedor que tenía todo por demostrar. Y flotaba una pregunta "
    "razonable —que yo también me hacía—: «Miguel Mujica, fuera de Parque Arauco, ¿seguirá siendo el "
    "mismo profesional?»\"\n\n"
    "(La lección.)\n"
    "\"Entonces entendí a Kipling. El Triunfo me había hecho creer que aquel éxito era enteramente "
    "mío… cuando buena parte era de la institución. Y el Desastre quería convencerme de que, sin ella, "
    "no era nadie. Los dos mentían.\"\n"
    "\"Mi nueva vida exigió humildad. Convencer en vez de ordenar. La soledad de no tener equipo. Ser, "
    "a la vez, el director general, el de operaciones, el comercial y el técnico.\"",
    "")

# 11 — ACTO II Ardatz
def ardatz_slide():
    s = slide(
        "EL DESENLACE.\n\n"
        "\"Trece años después, esa empresa —Ardatz— ha crecido y opera hoy en varios países.\"")
    textbox(s, "ARDATZ", font=SERIF, size=60, color=WHITE, top=Inches(2.4), height=Inches(1.3))
    textbox(s, "13 años  ·  varios países", font=SANS, size=22, color=ACCENT,
            top=Inches(3.9), height=Inches(0.8))
    textbox(s, "🖼️ logo de Ardatz + mapa de países (sustituir)", font=SANS, size=13,
            color=MUTED, italic=True, top=Inches(5.0), height=Inches(0.6))
    return s
ardatz_slide()

# 12 — ACTO II cierre
line_slide("El triunfo y el desastre te dicen quién crees que eres.\nLa verdad la escribes tú, después.",
    "\"…Pero ninguno de los dos dice la verdad. La verdad la escribes tú, después, con lo que decides "
    "reconstruir.\"")

# 13 — ACTO III verso
verse_slide("«…resistir cuando ya nada te queda,\nsalvo la Voluntad que dice: ¡Resistid!»",
    "Resiliencia",
    "ACTO III — RESILIENCIA · CLÍMAX (luz más baja). Lee el verso despacio.")

# 14 — ACTO III cima (foto)
photo_slide("Madrid / tu familia llegando / skyline  (opcional)",
    "LA CIMA.\n\n"
    "\"Salíamos de la pandemia y decidí dar otro salto: me llevo a la familia a Madrid, para abrir "
    "Ardatz a Europa. Ilusión nueva, una ciudad segura, calidad de vida, desafíos por delante. Una "
    "aventura fantástica.\"")

# 15 — ACTO III cuerpo (foto rugby)
photo_slide("Foto antigua de rugby  (recomendada: cierra el círculo del 'segundo tiempo')",
    "LA DEUDA DEL CUERPO.\n\n"
    "\"Pero la huella de mi vida no me dejaba tranquilo. De joven jugué al rugby, y aquellas lesiones "
    "de disco llevaban treinta años esperando. Por fin llego a quirófano: me operan en Chile y me "
    "recupero en España.\"\n"
    "\"Me dan el alta. Empiezo a reincorporarme al deporte con un equipo increíble. Pero a los tres "
    "meses no avanzo. Me mandan a hacer pruebas.\"")

# 16 — ACTO III golpe (negro)
line_slide("Esclerosis múltiple.",
    "EL GOLPE (negro absoluto, que la palabra caiga sin imagen).\n\n"
    "\"Llegan los resultados: lesiones en la mielina de mi columna.\"\n(Pausa.) \"Esclerosis múltiple.\"\n\n"
    "(Tu hermano.)\n"
    "\"Mi hermano, que es médico, intenta consolarme: «Lo bueno es que esto no mata» —pensando, por "
    "ejemplo, en un cáncer. Y es verdad: no mata. Pero es neurodegenerativa. La calidad de vida se va "
    "deteriorando, poco a poco.\"\n"
    "\"Tenía cuarenta y nueve años. Y sentí que empezaba el segundo tiempo de mi vida.\"",
    color=WHITE, size=44, italic=False, font=SERIF)

# 17 — ACTO III fondo (negro)
black_slide(
    "EL FONDO DEL POZO — la pérdida de control. Lo más íntimo.\n\n"
    "\"Entender la enfermedad me llevó tiempo. Pronto supe que no era ELA, y eso —dentro de todo— fue "
    "un alivio. Pero saber que llevas dentro algo que ataca tu sistema nervioso central… y que no "
    "avisa: eso fue lo que más me costó sobrellevar.\"\n"
    "\"Porque yo, toda mi vida, he sido un hombre de planes. Planificar. Ejecutar lo planificado. "
    "Aprender de lo vivido. Y si algo cambiaba, reaccionar rápido y volver a planificar.\"\n"
    "(Pausa.) \"Y de golpe, con la esclerosis, nada —nada— estaba bajo mi control. Solo me quedaba "
    "confiar. Y esperar que mi equipo médico tomara, por mí, las decisiones que yo siempre había "
    "tomado solo.\"\n\n"
    "(El duelo compartido.)\n"
    "\"El duelo de una enfermedad así es largo. Empieza en uno mismo. Pero pronto entiendes que tu "
    "familia, tus amigos, la gente que trabaja contigo… también están viviendo el suyo.\"",
    "")

# 18 — ACTO III chispa (velero)
def sail_slide():
    s = slide(
        "LA CHISPA — la Voluntad. La metáfora de las velas.\n\n"
        "\"Y aun así, la vida continúa. Hoy, con un buen tratamiento que frena la enfermedad, he vuelto "
        "a ser el protagonista de mi propia vida. Y aprendí algo que no estaba en ninguno de mis planes: "
        "que no puedo controlar el viento… pero sí puedo ajustar las velas cuando cambian las condiciones.\"")
    textbox(s, "No puedo controlar el viento.", font=SERIF, size=34, color=WHITE, italic=True,
            top=Inches(2.3), height=Inches(1.0))
    textbox(s, "Pero puedo ajustar las velas.", font=SERIF, size=34, color=ACCENT, italic=True,
            top=Inches(3.5), height=Inches(1.0))
    textbox(s, "🖼️ fondo: velero / velas al viento (opcional)", font=SANS, size=13,
            color=MUTED, italic=True, top=Inches(5.2), height=Inches(0.6))
    return s
sail_slide()

# 19 — ACTO III giro (4 preguntas)
line_slide("¿Cómo?   ¿Con quién?   ¿Dónde?\ny, sobre todo… ¿para qué?",
    "EL GIRO — el «para qué», puente al Acto IV. Pausa larga después.\n\n"
    "\"Y entonces la pregunta cambió. Ya no era «¿cuánto voy a vivir?». Era otra, mucho más "
    "importante…\"",
    color=WHITE, size=36)

# 20 — ACTO IV verso
verse_slide("«…llenar el implacable minuto\ncon sesenta segundos de esfuerzo cumplido…»",
    "Integridad",
    "ACTO IV — INTEGRIDAD Y PROPÓSITO (luz cálida, cercano). Lee el verso.\n\n"
    "(Reyes y trato sencillo — vivido literalmente.)\n"
    "\"He caminado con reyes: me he sentado con la alta dirección, he tratado con gurús de los negocios. "
    "Y también he esperado, de pie, en una recepción, a que un antiguo colaborador me recibiera. Os "
    "confieso una cosa: aprendí más en la sala de espera.\"\n\n"
    "(Callback del minuto.)\n"
    "\"¿Recordáis aquel minuto en la sala de partos? El minuto en que tuve que dar calma mientras me "
    "moría por dentro. Kipling lo llama «el implacable minuto». La vida entera está hecha de minutos "
    "así. Y la pregunta ya no es cuántos me quedan. Es con cuántos segundos de verdad los lleno.\"")

# 21 — ACTO IV síntesis (foto)
photo_slide("Foto tuya actual / con tu familia / en 'tu camino'",
    "LA TRANSFORMACIÓN — el «para qué».\n\n"
    "\"Yo fui un hombre de planes. Planificaba cada paso para llegar a un punto: el cargo, el proyecto, "
    "la meta siguiente. Y la vida me enseñó —a golpes— la lección que más me costó aprender: que tanto "
    "planificar era para alcanzar un destino… cuando lo que de verdad importa es la travesía.\"\n"
    "\"Hoy tengo claro mi para qué. Quiero ser el protagonista de mi vida; no el espectador de mi "
    "enfermedad ni de mis circunstancias. ¿Con quién? Con los míos —los mismos que estuvieron al otro "
    "lado de aquella puerta—. ¿Para qué? Para recorrer el camino, no para coleccionar metas.\"")

# 22 — RECAP
def recap_slide():
    s = slide(
        "RECAPITULACIÓN (las cuatro palabras en cascada).\n\n"
        "\"Cuatro versos. Cuatro pruebas. Serenidad cuando todo arde. Equilibrio ante el triunfo y el "
        "desastre. Resistir cuando no queda nada. E integridad para elegir, cada día, quién quiero ser.\"\n"
        "\"Kipling no escribió una lista de logros. Escribió una lista de decisiones. Casi todo el poema "
        "es un «si puedes…» —el camino—, y solo el final es la recompensa. Hasta Kipling lo sabía: la "
        "meta… es el camino.\"")
    palabras = ["Serenidad", "Equilibrio", "Resiliencia", "Integridad"]
    tb = s.shapes.add_textbox(Inches(1), Inches(2.4), SW - Inches(2), Inches(2.7))
    tf = tb.text_frame; tf.word_wrap = True
    for i, w in enumerate(palabras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = w
        f = r.font; f.name = SERIF; f.size = Pt(30); f.color.rgb = ACCENT if i % 2 else WHITE
    return s
recap_slide()

# 23 — IDEA-FUERZA
line_slide("La meta no es el destino.\nLa meta es el camino.\nY de ti depende ser su protagonista.",
    "IDEA-FUERZA — la frase que el público se lleva a casa.\n\n"
    "\"Así que esto es lo que me gustaría que os llevarais…\"",
    color=WHITE, size=34)

# 24 — PUENTE
black_slide(
    "PUENTE AL VÍDEO (negro; prepara el reproductor).\n\n"
    "\"Os dije que dejaría que alguien os leyera el poema entero. Hay un hombre que lo dice mejor que "
    "yo. Escuchadlo.\"",
    "")

# 25 — VÍDEO
def video_slide():
    s = slide(
        "VÍDEO — Michael Caine recita «If—» con subtítulos en español.\n\n"
        "Inserta aquí el clip (carpeta video/ del repo: subtitulos-if-michael-caine-ES.srt).\n"
        "NO hablas. Quédate quieto, mirando la pantalla con el público.\n"
        "Recuerda: vídeo en local + copia de seguridad. Audio probado en la sala.")
    textbox(s, "▶  [ INSERTAR VÍDEO DE MICHAEL CAINE — «If» con subtítulos ES ]",
            font=SANS, size=20, color=MUTED, top=Inches(3.2), height=Inches(1.1))
    return s
video_slide()

# 26 — FRASE FINAL
photo_slide("Foto de Iñaki HOY (caminando), tenue  ·  o deja negro",
    "FRASE FINAL (el vídeo termina; 2-3 s de silencio total).\n\n"
    "\"Aquel segundo hijo que nació azul… Iñaki… hoy camina a mi lado. Con sus secuelas, sí. Pero "
    "camina. Y cada paso suyo me recuerda que la meta siempre fue esta: el camino. Juntos.\"\n"
    "(Pausa.) \"Gracias.\"")

# 27 — CIERRE
title_slide("Gracias", "",
    "Mantén esta pantalla. El silencio es el aplauso. No añadas nada más.")

prs.save("testimonio-kipling/presentacion/Si_testimonio_Kipling.pptx")
print("OK ->", len(prs.slides.__iter__.__self__._sldIdLst), "slides")
