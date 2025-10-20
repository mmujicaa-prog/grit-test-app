
# app_grit_streamlit.py
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import altair as alt
import os
import time
import traceback

# -----------------------
# Configuración
# -----------------------
# En Streamlit Cloud sólo /tmp es escribible
DB_PATH = os.path.join("/tmp", "grit_responses.db")
ADMIN_PASSWORD = "admin"  # cambia antes de publicar
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
# Funciones DB y utilidades
# -----------------------
def get_connection(path=DB_PATH):
    """
    Abrir conexión SQLite con parámetros que reducen
    la probabilidad de 'database is locked'.
    """
    # timeout mayor y permitir threads distintos (Streamlit puede usar hilos)
    return sqlite3.connect(path, timeout=30, check_same_thread=False)


def init_db(path=DB_PATH):
    """Crear tabla si no existe."""
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
    """
    Guarda una fila en la tabla responses.
    Implementa validación y reintentos ante bloqueo de DB.
    """
    # Validar longitud de answers
    if not isinstance(answers, (list, tuple)) or len(answers) != 12:
        raise ValueError(f"Se esperaban 12 respuestas; recibidas: {len(answers) if isinstance(answers, (list,tuple)) else 'tipo inválido'}")

    placeholders = ",".join(["?"] * 19)  # 19 parámetros a insertar
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
            return  # éxito
        except sqlite3.OperationalError as e:
            # reintentar con backoff corto
            if attempt == max_retries:
                # si falla al último intento, levantar error para que la app lo muestre/loguee
                raise
            time.sleep(0.2 * attempt)
        except Exception:
            # otros errores: cerrar conexión si abierta y relanzar
            try:
                conn.close()
            except Exception:
                pass
            raise


def load_all_responses(path=DB_PATH):
    """Lee todas las respuestas. Si la tabla no existe aún, devuelve df vacío."""
    try:
        conn = get_connection(path)
        df = pd.read_sql_query("SELECT * FROM responses", conn)
        conn.close()
        return df
    except Exception:
        # Si ocurre cualquier error (tabla no creada, archivo dañado), devolver df vacío con columnas esperadas
        cols = [
            "id","participant_id","email","timestamp",
            "q1","q2","q3","q4","q5","q6","q7","q8","q9","q10","q11","q12",
            "perseverance","consistency","grit_total","grit_level"
        ]
        return pd.DataFrame(columns=cols)


def score_answers(raw_answers):
    """Calcula subescalas y nivel de grit."""
    perseverance_idx = [0, 3, 5, 8, 9, 11]   # 1,4,6,9,10,12 (0-based)
    consistency_idx = [1, 2, 4, 6, 7, 10]    # 2,3,5,7,8,11
    # Forzar conversion a int
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
# Interfaz Streamlit
# -----------------------
def main():
    init_db(DB_PATH)
    st.title("🧭 Test Escala de Grit")
    menu = st.sidebar.selectbox("Navegación", ["Aplicar test", "Panel administrativo"])

    # -- Aplicar test --
    if menu == "Aplicar test":
        st.header("Aplicar test")
        st.write("Responde las afirmaciones seleccionando la opción que más se parezca a ti.")
        # Usar form para agrupar y validar
        with st.form("grit_form"):
            participant_id = st.text_input("ID del participante (opcional)")
            email = st.text_input("Correo electrónico (opcional)")
            answers = []
            # Mostrar cada pregunta
            for num, text, tipo in ITEMS:
                st.markdown(f"**{num}. {text}**")
                options = SCALE_NORMAL if tipo == "normal" else SCALE_INVERTED
                # extraer etiquetas y valores
                labels = [o[0] for o in options]
                values = [o[1] for o in options]
                # radio devuelve la etiqueta; la mapeamos al valor numérico
                choice_label = st.radio("", labels, key=f"q{num}")
                # por seguridad, comprobamos que exista en el diccionario
                mapping = dict(zip(labels, values))
                if choice_label not in mapping:
                    st.error("Error interno de las opciones. Intente recargar la página.")
                    return
                answers.append(mapping[choice_label])

            submitted = st.form_submit_button("Enviar respuestas")
            if submitted:
                # Validación por si no hay 12 respuestas (debería haberlas)
                if len(answers) != 12:
                    st.error(f"Se han detectado {len(answers)} respuestas (se requieren 12). Recarga la página e inténtalo de nuevo.")
                else:
                    try:
                        perc, cons, total, level = score_answers(answers)
                        # Guardar en DB con manejo de errores
                        try:
                            save_response(participant_id, email, answers, perc, cons, total, level)
                        except Exception as e:
                            # mostrar detalle resumido y registro en logs de servidor
                            st.error("Error al guardar la respuesta en la base de datos. Inténtalo de nuevo.")
                            st.write("Detalle técnico (solo para desarrollador):")
                            st.code(traceback.format_exc())
                            return

                        st.success("✅ Respuesta registrada correctamente")
                        st.markdown("### 🧾 Resultado individual:")
                        st.write(f"- **Perseverancia del esfuerzo:** {perc:.2f}")
                        st.write(f"- **Consistencia del interés:** {cons:.2f}")
                        st.write(f"- **Puntaje total (1-5):** {total:.2f} — **{level}**")
                    except Exception:
                        st.error("Error al procesar las respuestas. Recarga la página e inténtalo de nuevo.")
                        st.code(traceback.format_exc())

    # -- Panel administrativo --
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

        # Mostrar tabla (sin columna id si existe)
        to_show = df.copy()
        if "id" in to_show.columns:
            to_show = to_show.drop(columns=["id"])
        st.dataframe(to_show.sort_values("timestamp", ascending=False))

        # Estadísticas
        st.subheader("📈 Estadísticas generales")
        try:
            stats = {
                "Promedio Perseverancia": float(df["perseverance"].mean()),
                "Promedio Consistencia": float(df["consistency"].mean()),
                "Promedio Grit Total": float(df["grit_total"].mean())
            }
            st.write(pd.DataFrame.from_dict(stats, orient="index", columns=["Valor"]))
        except Exception:
            st.info("No se pudieron calcular estadísticas (datos insuficientes o formato inesperado).")

        # Gráfico (boxplot) con Altair
        try:
            chart_df = df[["perseverance", "consistency", "grit_total"]].melt(var_name="Subescala", value_name="Valor")
            chart = alt.Chart(chart_df).mark_boxplot().encode(x="Subescala:N", y="Valor:Q")
            st.altair_chart(chart, use_container_width=True)
        except Exception:
            pass

        # Descargar CSV
        try:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar todas las respuestas (CSV)", data=csv, file_name="todas_respuestas_grit.csv", mime="text/csv")
        except Exception:
            st.error("No se pudo generar el CSV para descarga.")


if __name__ == "__main__":
    main()
