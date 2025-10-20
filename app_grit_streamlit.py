
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
DB_PATH = os.path.join("/tmp", "grit_responses.db")  # carpeta escribible en Streamlit Cloud
ADMIN_PASSWORD = "admin"  # cambiar antes de publicar
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
    if not isinstance(answers, (list, tuple)) or len(answers) != 12:
        raise ValueError(f"Se esperaban 12 respuestas; recibidas: {len(answers) if isinstance(answers,(list,tuple)) else 'tipo inválido'}")
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
        int(answers[0]), int(answers[1]), int(answers[2]), int(answers[3]),
        int(answers[4]), int(answers[5]), int(answers[6]), int(answers[7]),
        int(answers[8]), int(answers[9]), int(answers[10]), int(answers[11]),
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
# Función para generar PDF
# -----------------------
def generate_pdf(participant_id, email, answers, perseverance, consistency, grit_total, grit_level):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 50, "Informe del Test de Grit")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 90, f"ID del participante: {participant_id or 'No proporcionado'}")
    c.drawString(50, height - 110, f"Correo electrónico: {email or 'No proporcionado'}")
    c.drawString(50, height - 130, f"Fecha y hora: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    c.drawString(50, height - 170, "Resultados del Test:")
    c.drawString(70, height - 190, f"Perseverancia del esfuerzo: {perseverance:.2f}")
    c.drawString(70, height - 210, f"Consistencia del interés: {consistency:.2f}")
    c.drawString(70, height - 230, f"Puntaje total: {grit_total:.2f}")
    c.drawString(70, height - 250, f"Nivel de Grit: {grit_level}")
    interpret = {
        "Muy alto": "Excelente nivel de perseverancia y consistencia.",
        "Alto": "Buen nivel de perseverancia y consistencia.",
        "Moderado": "Nivel moderado; hay espacio para mejorar.",
        "Bajo": "Nivel bajo; se recomienda trabajar en la constancia.",
        "Muy bajo": "Nivel muy bajo; se recomienda reforzar hábitos de perseverancia."
    }
    c.drawString(50, height - 290, "Interpretación:")
    c.drawString(70, height - 310, interpret.get(grit_level, ""))
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# -----------------------
# Interfaz principal
# -----------------------
def main():
    init_db(DB_PATH)
    st.title("🧭 Test Escala de Grit")
    menu = st.sidebar.selectbox("Navegación", ["Aplicar test", "Panel administrativo"])

    if menu == "Aplicar test":
        st.header("Aplicar test")
        st.write("Responde las afirmaciones seleccionando la opción que más se parezca a ti.")
        with st.form("grit_form"):
            participant_id = st.text_input("ID del participante (opcional)")
            email = st.text_input("Correo electrónico (opcional)")
            answers = []
            for num, text, tipo in ITEMS:
                st.markdown(f"**{num}. {text}**")
                options = SCALE_NORMAL if tipo=="normal" else SCALE_INVERTED
                labels = [o[0] for o in options]
                values = [o[1] for o in options]
                choice_label = st.radio("", labels, key=f"q{num}")
                mapping = dict(zip(labels, values))
                answers.append(mapping[choice_label])

            submitted = st.form_submit_button("Enviar respuestas")
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
