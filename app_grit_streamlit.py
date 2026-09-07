
# app_grit_streamlit.py
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import altair as alt
import os
import time
import traceback
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# -----------------------
# Configuración
# -----------------------
DB_PATH = os.path.join("/tmp", "grit_responses.db")
ADMIN_PASSWORD = "Mm795415+"  # cambiar antes de publicar
st.set_page_config(page_title="Test Grit - App", layout="centered")

# -----------------------
# Ítems y escalas
# -----------------------
ITEMS = [
    (1, "He superado contratiempos para conseguir un reto importante.", "normal"),
    (2, "Las ideas y proyectos nuevos a menudo me distraen de los anteriores.", "invertida"),
    (3, "Mis intereses cambian de año a año.", "invertida"),
    (4, "Los contratiempos no me desaniman.", "normal"),
    (5, "Me he obsesionado con cierta idea, o proyecto, durante un periodo corto de tiempo, para después dejar de estar interesado.", "invertida"),
    (6, "Soy un/a trabajador/a duro/a.", "normal"),
    (7, "A menudo me pongo un objetivo para después perseguir otro diferente.", "invertida"),
    (8, "Tengo dificultad para mantener mi atención en proyectos que me reclaman más de varios meses llevarlos a cabo.", "invertida"),
    (9, "Termino todo lo que empiezo.", "normal"),
    (10, "He conseguido objetivos que me costaron años alcanzarlos.", "normal"),
    (11, "Me he llegado a interesar por nuevas actividades cada pocos meses.", "invertida"),
    (12, "Soy una persona diligente.", "normal"),
]

SCALE_NORMAL = [
    ("Muy parecido a mí", 5),
    ("Preferentemente como yo", 4),
    ("De algún modo como yo", 3),
    ("No como yo", 2),
    ("En absoluto se parece a mí", 1),
]

SCALE_INVERTED = [
    ("Muy parecido a mí", 1),
    ("Preferentemente como yo", 2),
    ("De algún modo como yo", 3),
    ("No como yo", 4),
    ("En absoluto se parece a mí", 5),
]

# -----------------------
# Funciones de base de datos y utilidades
# -----------------------
def get_connection(path=DB_PATH):
    return sqlite3.connect(path, timeout=30, check_same_thread=False)

def init_db(path=DB_PATH):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id TEXT,
            email TEXT,
            timestamp TEXT,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER, q6 INTEGER,
            q7 INTEGER, q8 INTEGER, q9 INTEGER, q10 INTEGER, q11 INTEGER, q12 INTEGER,
            perseverance REAL, consistency REAL, grit_total REAL, grit_level TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_response(participant_id, email, answers, perseverance, consistency, grit_total, grit_level, path=DB_PATH):
    placeholders = ",".join(["?"] * 19)
    sql = f"""
        INSERT INTO responses (
            participant_id, email, timestamp,
            q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,q12,
            perseverance, consistency, grit_total, grit_level
        )
        VALUES ({placeholders})
    """
    params = (
        participant_id or "",
        email or "",
        datetime.utcnow().isoformat(),
        *[int(a) for a in answers],
        float(perseverance), float(consistency), float(grit_total), str(grit_level)
    )
    max_retries = 6
    for attempt in range(1, max_retries + 1):
        try:
            conn = get_connection(path)
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            conn.close()
            return
        except sqlite3.OperationalError:
            if attempt == max_retries:
                raise
            time.sleep(0.2 * attempt)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            raise

def load_all_responses(path=DB_PATH):
    try:
        conn = get_connection(path)
        df = pd.read_sql_query("SELECT * FROM responses", conn)
        conn.close()
        return df
    except Exception:
        cols = [
            "id","participant_id","email","timestamp",
            "q1","q2","q3","q4","q5","q6","q7","q8","q9","q10","q11","q12",
            "perseverance","consistency","grit_total","grit_level"
        ]
        return pd.DataFrame(columns=cols)

def score_answers(raw_answers):
    perseverance_idx = [0,3,5,8,9,11]
    consistency_idx = [1,2,4,6,7,10]
    vals = [int(v) for v in raw_answers]
    perseverance = sum(vals[i] for i in perseverance_idx) / len(perseverance_idx)
    consistency = sum(vals[i] for i in consistency_idx) / len(consistency_idx)
    grit_total = (perseverance + consistency) / 2.0
    if grit_total >= 4.5:
        level = "Muy alto"
    elif grit_total >= 3.5:
        level = "Alto"
    elif grit_total >= 2.5:
        level = "Moderado"
    elif grit_total >= 1.5:
        level = "Bajo"
    else:
        level = "Muy bajo"
    return perseverance, consistency, grit_total, level

# -----------------------
# Función auxiliar para dividir texto en varias líneas según ancho disponible
# -----------------------
def split_text(text, max_width, canvas_obj):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if canvas_obj.stringWidth(test_line, "Helvetica", 12) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

# -----------------------
# Función para generar PDF con interpretación detallada
# -----------------------
def generate_pdf(participant_id, email, answers, perseverance, consistency, grit_total, grit_level):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 50
    line_height = 18
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, y, "Informe del Test de Grit")
    y -= 40

    c.setFont("Helvetica", 12)
    c.drawString(margin, y, f"ID del participante: {participant_id or 'No proporcionado'}")
    y -= line_height
    c.drawString(margin, y, f"Correo electrónico: {email or 'No proporcionado'}")
    y -= line_height
    c.drawString(margin, y, f"Fecha y hora: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    y -= line_height * 2

    # Resultados numéricos
    c.drawString(margin, y, "Resultados del Test:")
    y -= line_height
    c.drawString(margin + 20, y, f"Perseverancia del esfuerzo: {perseverance:.2f}")
    y -= line_height
    c.drawString(margin + 20, y, f"Consistencia del interés: {consistency:.2f}")
    y -= line_height
    c.drawString(margin + 20, y, f"Puntaje total: {grit_total:.2f}")
    y -= line_height
    c.drawString(margin + 20, y, f"Nivel de Grit: {grit_level}")
    y -= line_height * 2

    # Interpretación detallada
    c.drawString(margin, y, "Interpretación:")
    y -= line_height

    # Puntaje total
    grit_interp = {
        "Muy alto": "Excelente nivel general de Grit: alta perseverancia y consistencia.",
        "Alto": "Buen nivel general de Grit: mantiene esfuerzo y constancia en la mayoría de los proyectos.",
        "Moderado": "Nivel moderado de Grit: hay espacio para mejorar la perseverancia o consistencia.",
        "Bajo": "Nivel bajo de Grit: se recomienda trabajar en mantener el esfuerzo y la constancia.",
        "Muy bajo": "Nivel muy bajo de Grit: se necesita reforzar hábitos de perseverancia y constancia."
    }
    for line in split_text(grit_interp.get(grit_level, ""), width - 2*margin, c):
        c.drawString(margin + 20, y, line)
        y -= line_height

    # Perseverancia
    perc_interp = "Alta" if perseverance >= 4.0 else "Moderada" if perseverance >= 2.5 else "Baja"
    perc_text = {
        "Alta": "Mantiene un esfuerzo constante y enfrenta los contratiempos con determinación.",
        "Moderada": "Es capaz de esforzarse, pero a veces se distrae o se desanima.",
        "Baja": "Dificultad para mantener esfuerzo prolongado; puede abandonar proyectos con facilidad."
    }
    c.drawString(margin + 20, y, f"Perseverancia del esfuerzo: {perc_interp}")
    y -= line_height
    for line in split_text(perc_text[perc_interp], width - 2*margin, c):
        c.drawString(margin + 40, y, line)
        y -= line_height

    # Consistencia
    cons_interp = "Alta" if consistency >= 4.0 else "Moderada" if consistency >= 2.5 else "Baja"
    cons_text = {
        "Alta": "Intereses estables; mantiene enfoque en proyectos y metas a largo plazo.",
        "Moderada": "Intereses algo cambiantes; puede alternar entre proyectos con cierta frecuencia.",
        "Baja": "Intereses muy cambiantes; dificultad para mantener enfoque prolongado."
    }
    c.drawString(margin + 20, y, f"Consistencia del interés: {cons_interp}")
    y -= line_height
    for line in split_text(cons_text[cons_interp], width - 2*margin, c):
        c.drawString(margin + 40, y, line)
        y -= line_height

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# -----------------------
# Check-in diario de salud
# -----------------------
HEALTH_ATTACHMENTS_DIR = os.path.join("/tmp", "grit_health_attachments")
SEED_HEALTH_ATTACHMENTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assets", "health_checkins", "2026-09-07"
)

def init_health_checkin_db(path=DB_PATH):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS health_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            timestamp TEXT,
            recovery_pct REAL,
            hrv REAL,
            hrv_baseline REAL,
            rhr REAL,
            rhr_baseline REAL,
            resp_rate REAL,
            resp_rate_baseline REAL,
            sleep_score_pct REAL,
            sleep_score_baseline REAL,
            sleep_hours REAL,
            strain REAL,
            steps INTEGER,
            calories INTEGER,
            sleep_efficiency_pct REAL,
            stress_score REAL,
            stress_level TEXT,
            notes TEXT,
            attachments TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_health_checkin(data, attachment_paths, path=DB_PATH):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO health_checkins (
            date, timestamp, recovery_pct, hrv, hrv_baseline, rhr, rhr_baseline,
            resp_rate, resp_rate_baseline, sleep_score_pct, sleep_score_baseline,
            sleep_hours, strain, steps, calories, sleep_efficiency_pct,
            stress_score, stress_level, notes, attachments
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data["date"], datetime.utcnow().isoformat(),
        data["recovery_pct"], data["hrv"], data["hrv_baseline"],
        data["rhr"], data["rhr_baseline"],
        data["resp_rate"], data["resp_rate_baseline"],
        data["sleep_score_pct"], data["sleep_score_baseline"],
        data["sleep_hours"], data["strain"], data["steps"], data["calories"],
        data["sleep_efficiency_pct"], data["stress_score"], data["stress_level"],
        data["notes"], ",".join(attachment_paths)
    ))
    conn.commit()
    conn.close()

def load_health_checkins(path=DB_PATH):
    try:
        conn = get_connection(path)
        df = pd.read_sql_query("SELECT * FROM health_checkins ORDER BY date DESC, id DESC", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def seed_health_checkin_if_empty(path=DB_PATH):
    """Carga el check-in del 2026-09-07 con las capturas de WHOOP aportadas por el usuario, si la tabla aún está vacía."""
    if len(load_health_checkins(path)) > 0:
        return
    if not os.path.isdir(SEED_HEALTH_ATTACHMENTS_DIR):
        return
    attachment_paths = sorted(
        os.path.join(SEED_HEALTH_ATTACHMENTS_DIR, f) for f in os.listdir(SEED_HEALTH_ATTACHMENTS_DIR)
    )
    data = {
        "date": "2026-09-07",
        "recovery_pct": 30, "hrv": 16, "hrv_baseline": 23,
        "rhr": 67, "rhr_baseline": 58,
        "resp_rate": 15.7, "resp_rate_baseline": 14.5,
        "sleep_score_pct": 67, "sleep_score_baseline": 77,
        "sleep_hours": None, "strain": None, "steps": None, "calories": None,
        "sleep_efficiency_pct": None, "stress_score": None, "stress_level": None,
        "notes": (
            "Datos WHOOP. Recuperación baja (30%) con HRV por debajo de la media móvil (16 vs 23), "
            "FC en reposo elevada (67 vs 58) y calificación del sueño por debajo de la media (67% vs 77%). "
            "Señal de carga acumulada: revisar comportamientos del día anterior."
        ),
    }
    save_health_checkin(data, attachment_paths, path)

# -----------------------
# Interfaz principal
# -----------------------
def main():
    init_db(DB_PATH)
    init_health_checkin_db(DB_PATH)
    seed_health_checkin_if_empty(DB_PATH)
    st.title("🧭 Test Escala de Grit")
    menu = st.sidebar.selectbox(
        "Navegación", ["Aplicar test", "Check-in diario de salud", "Panel administrativo"]
    )

    if menu == "Aplicar test":
        st.header("Aplicar test")
        st.write("Responde las afirmaciones seleccionando la opción que más se parezca a ti.")

        answers = []

        # --- FORMULARIO ---
        with st.form("grit_form"):
            participant_id = st.text_input("ID del participante (opcional)")
            email = st.text_input("Correo electrónico (opcional)")

            for num, text, tipo in ITEMS:
                st.markdown(f"**{num}. {text}**")
                options = SCALE_NORMAL if tipo=="normal" else SCALE_INVERTED
                labels = [o[0] for o in options]
                values = [o[1] for o in options]
                choice_label = st.radio("", labels, key=f"q{num}")
                mapping = dict(zip(labels, values))
                answers.append(mapping[choice_label])

            submitted = st.form_submit_button("Enviar respuestas")

        # --- FUERA DEL FORMULARIO ---
        if submitted:
            if len(answers) != 12:
                st.error(f"Se han detectado {len(answers)} respuestas (se requieren 12).")
            else:
                try:
                    perc, cons, total, level = score_answers(answers)
                    save_response(participant_id, email, answers, perc, cons, total, level)
                    st.success("✅ Respuesta registrada correctamente")
                    st.markdown("### 🧾 Resultado individual:")
                    st.write(f"- **Perseverancia del esfuerzo:** {perc:.2f}")
                    st.write(f"- **Consistencia del interés:** {cons:.2f}")
                    st.write(f"- **Puntaje total (1-5):** {total:.2f} — **{level}**")

                    # PDF con interpretación detallada
                    pdf_buffer = generate_pdf(participant_id, email, answers, perc, cons, total, level)
                    st.download_button(
                        label="📄 Descargar reporte PDF",
                        data=pdf_buffer,
                        file_name=f"Reporte_Grit_{participant_id or 'participante'}.pdf",
                        mime="application/pdf"
                    )
                except Exception:
                    st.error("Error al procesar las respuestas. Recarga la página e inténtalo de nuevo.")
                    st.code(traceback.format_exc())

    elif menu == "Check-in diario de salud":
        st.header("🩺 Check-in diario de salud")
        st.write(
            "Registra tus métricas diarias de recuperación, sueño y esfuerzo, y adjunta capturas "
            "de tu app de salud (ej. WHOOP)."
        )

        with st.form("health_checkin_form"):
            checkin_date = st.date_input("Fecha", value=datetime.utcnow().date())
            col1, col2 = st.columns(2)
            with col1:
                recovery_pct = st.number_input("Recuperación (%)", 0, 100, 0)
                hrv = st.number_input("HRV (ms)", 0.0, 300.0, 0.0)
                rhr = st.number_input("FC en reposo (bpm)", 0, 200, 0)
                resp_rate = st.number_input("Frecuencia respiratoria (rpm)", 0.0, 40.0, 0.0)
                sleep_score_pct = st.number_input("Calificación del sueño (%)", 0, 100, 0)
            with col2:
                sleep_hours = st.number_input("Horas de sueño", 0.0, 24.0, 0.0)
                strain = st.number_input("Esfuerzo (Strain)", 0.0, 21.0, 0.0)
                steps = st.number_input("Pasos", 0, 100000, 0)
                calories = st.number_input("Calorías", 0, 10000, 0)
                sleep_efficiency_pct = st.number_input("Eficiencia del sueño (%)", 0, 100, 0)
            stress_score = st.number_input("Nivel de estrés (0-3)", 0.0, 3.0, 0.0)
            stress_level = st.selectbox("Categoría de estrés", ["", "Bajo", "Medio", "Alto"])
            notes = st.text_area("Notas")
            uploaded_files = st.file_uploader(
                "Adjuntos (capturas de la app de salud)",
                type=["png", "jpg", "jpeg"],
                accept_multiple_files=True,
            )
            submitted_health = st.form_submit_button("Guardar check-in")

        if submitted_health:
            os.makedirs(HEALTH_ATTACHMENTS_DIR, exist_ok=True)
            saved_paths = []
            for f in uploaded_files or []:
                dest = os.path.join(HEALTH_ATTACHMENTS_DIR, f"{checkin_date.isoformat()}_{f.name}")
                with open(dest, "wb") as out:
                    out.write(f.getbuffer())
                saved_paths.append(dest)
            data = {
                "date": checkin_date.isoformat(),
                "recovery_pct": recovery_pct, "hrv": hrv, "hrv_baseline": None,
                "rhr": rhr, "rhr_baseline": None,
                "resp_rate": resp_rate, "resp_rate_baseline": None,
                "sleep_score_pct": sleep_score_pct, "sleep_score_baseline": None,
                "sleep_hours": sleep_hours, "strain": strain, "steps": steps,
                "calories": calories, "sleep_efficiency_pct": sleep_efficiency_pct,
                "stress_score": stress_score, "stress_level": stress_level or None,
                "notes": notes,
            }
            save_health_checkin(data, saved_paths)
            st.success("✅ Check-in guardado correctamente")

        st.subheader("📅 Historial de check-ins")
        health_df = load_health_checkins()
        if len(health_df) == 0:
            st.info("Todavía no hay check-ins registrados.")
        else:
            for _, row in health_df.iterrows():
                label = f"{row['date']} — Recuperación {row['recovery_pct']}% · Sueño {row['sleep_score_pct']}%"
                with st.expander(label):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Recuperación", f"{row['recovery_pct']}%")
                    hrv_delta = None if pd.isna(row["hrv_baseline"]) else row["hrv"] - row["hrv_baseline"]
                    c2.metric("HRV", f"{row['hrv']} ms", delta=hrv_delta)
                    rhr_delta = None if pd.isna(row["rhr_baseline"]) else row["rhr"] - row["rhr_baseline"]
                    c3.metric("FC en reposo", f"{row['rhr']} bpm", delta=rhr_delta, delta_color="inverse")
                    if row["notes"]:
                        st.write(row["notes"])
                    attachments = [p for p in (row["attachments"] or "").split(",") if p]
                    if attachments:
                        st.write("**Adjuntos:**")
                        cols = st.columns(min(len(attachments), 4))
                        for i, path in enumerate(attachments):
                            if os.path.exists(path):
                                cols[i % len(cols)].image(path, use_container_width=True)

    elif menu == "Panel administrativo":
        st.header("Panel administrativo")
        pwd = st.text_input("Contraseña de administrador", type="password")
        if pwd != ADMIN_PASSWORD:
            st.warning("Introduce la contraseña correcta para ver los resultados.")
            return

        df = load_all_responses()
        st.subheader("📊 Respuestas registradas")
        st.write(f"Total respuestas: {len(df)}")

        if len(df) == 0:
            st.info("No hay respuestas todavía.")
            return

        to_show = df.copy()
        if "id" in to_show.columns:
            to_show = to_show.drop(columns=["id"])
        st.dataframe(to_show.sort_values("timestamp", ascending=False))

        st.subheader("📈 Estadísticas generales")
        try:
            stats = {
                "Promedio Perseverancia": float(df["perseverance"].mean()),
                "Promedio Consistencia": float(df["consistency"].mean()),
                "Promedio Grit Total": float(df["grit_total"].mean())
            }
            st.write(pd.DataFrame.from_dict(stats, orient="index", columns=["Valor"]))
        except Exception:
            st.info("No se pudieron calcular estadísticas.")

        try:
            chart_df = df[["perseverance","consistency","grit_total"]].melt(var_name="Subescala", value_name="Valor")
            chart = alt.Chart(chart_df).mark_boxplot().encode(x="Subescala:N", y="Valor:Q")
            st.altair_chart(chart, use_container_width=True)
        except Exception:
            pass

        try:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar todas las respuestas (CSV)", data=csv, file_name="todas_respuestas_grit.csv", mime="text/csv")
        except Exception:
            st.error("No se pudo generar el CSV.")

if __name__ == "__main__":
    main()


