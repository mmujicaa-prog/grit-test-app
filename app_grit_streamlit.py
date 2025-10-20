
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import altair as alt
import os

# ✅ En Streamlit Cloud, solo /tmp tiene permisos de escritura
DB_PATH = os.path.join("/tmp", "grit_responses.db")

ADMIN_PASSWORD = "admin"
st.set_page_config(page_title="Test Grit - App", layout="centered")

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

def init_db(path=DB_PATH):
    conn = sqlite3.connect(path)
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
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT INTO responses (participant_id, email, timestamp, q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,q12,
                               perseverance, consistency, grit_total, grit_level)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
        participant_id, email, now,
        answers[0],answers[1],answers[2],answers[3],answers[4],answers[5],
        answers[6],answers[7],answers[8],answers[9],answers[10],answers[11],
        perseverance, consistency, grit_total, grit_level
    ))
    conn.commit()
    conn.close()

def load_all_responses(path=DB_PATH):
    conn = sqlite3.connect(path)
    df = pd.read_sql_query("SELECT * FROM responses", conn)
    conn.close()
    return df

def score_answers(raw_answers):
    perseverance_idx = [0,3,5,8,9,11]
    consistency_idx = [1,2,4,6,7,10]
    perseverance = sum(raw_answers[i] for i in perseverance_idx) / len(perseverance_idx)
    consistency = sum(raw_answers[i] for i in consistency_idx) / len(consistency_idx)
    grit_total = (perseverance + consistency) / 2
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

def main():
    init_db(DB_PATH)
    st.title("Test Escala de Grit — Aplicación")
    menu = st.sidebar.selectbox("Navegación", ["Aplicar test", "Panel administrativo"])

    if menu == "Aplicar test":
        st.header("Aplicar test")
        st.write("Responde las siguientes afirmaciones seleccionando la opción que más se parezca a ti.")

        with st.form("grit_form"):
            participant_id = st.text_input("ID del participante (opcional)")
            email = st.text_input("Correo electrónico (opcional)")
            answers = []
            for idx, (num, text, tipo) in enumerate(ITEMS):
                st.write(f"**{num}. {text}**")
                options = SCALE_NORMAL if tipo == "normal" else SCALE_INVERTED
                labels = [o[0] for o in options]
                values = [o[1] for o in options]
                choice_label = st.radio("", labels, key=f"q{num}")
                value = dict(zip(labels, values))[choice_label]
                answers.append(value)
            submitted = st.form_submit_button("Enviar respuestas")
            if submitted:
                perseverance, consistency, grit_total, level = score_answers(answers)
                save_response(participant_id, email, answers, perseverance, consistency, grit_total, level)
                st.success("Respuesta registrada correctamente ✅")
                st.markdown("### Resultado individual:")
                st.write(f"- **Perseverancia del esfuerzo:** {perseverance:.2f}")
                st.write(f"- **Consistencia del interés:** {consistency:.2f}")
                st.write(f"- **Puntaje total (1-5):** {grit_total:.2f} — **{level}**")

    elif menu == "Panel administrativo":
        st.header("Panel administrativo")
        pwd = st.text_input("Contraseña de administrador", type="password")
        if pwd != ADMIN_PASSWORD:
            st.warning("Introduce la contraseña correcta para ver los resultados.")
            return
        df = load_all_responses()
        st.subheader("Respuestas registradas")
        st.write(f"Total respuestas: {len(df)}")
        if len(df) == 0:
            st.info("No hay respuestas todavía.")
            return
        st.dataframe(df.sort_values("timestamp", ascending=False).drop(columns=["id"]))
        st.subheader("Estadísticas generales")
        stats = {
            "Promedio Perseverancia": df["perseverance"].mean(),
            "Promedio Consistencia": df["consistency"].mean(),
            "Promedio Grit Total": df["grit_total"].mean()
        }
        st.write(pd.DataFrame.from_dict(stats, orient="index", columns=["Valor"]))        
        chart_df = df[["perseverance", "consistency", "grit_total"]].melt(var_name="subescala", value_name="valor")
        chart = alt.Chart(chart_df).mark_boxplot().encode(x="subescala:N", y="valor:Q")
        st.altair_chart(chart, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar todas las respuestas (CSV)", data=csv, file_name="todas_respuestas_grit.csv", mime="text/csv")

if __name__ == "__main__":
    main()
