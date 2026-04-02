"""MVP interno: Radar Editorial Social (Fase 1)."""

from __future__ import annotations

import sqlite3
from datetime import datetime

import streamlit as st

from db import (
    create_exclusion,
    create_signal,
    create_subtopic,
    create_topic,
    get_exclusions,
    get_signals,
    get_signals_by_status,
    get_subtopics,
    get_topic_map,
    get_topics,
    get_weekly_saved_signals,
    init_db,
    topic_count,
    update_signal_status,
)

MAX_TOPICS = 3
MAX_SUBTOPICS_PER_TOPIC = 3
STATUSES = ["guardada", "descartada", "idea"]


def setup_page() -> None:
    st.set_page_config(page_title="Radar Editorial Social", page_icon="🛰️", layout="wide")
    st.title("🛰️ Radar Editorial Social")
    st.caption("MVP interno - Fase 1")


def nav() -> str:
    return st.sidebar.radio("Pantallas", ["Temas", "Radar", "Memoria", "Briefing"])


def render_topics_screen() -> None:
    st.header("1) Temas")
    st.write("Define hasta 3 temas, hasta 3 subtemas por tema y exclusiones.")

    current_topics = get_topics()
    st.subheader("Crear tema")

    if len(current_topics) >= MAX_TOPICS:
        st.info("Ya alcanzaste el máximo de 3 temas para esta fase.")
    else:
        with st.form("topic_form", clear_on_submit=True):
            topic_name = st.text_input("Nombre del tema")
            submitted = st.form_submit_button("Guardar tema")

            if submitted:
                if not topic_name.strip():
                    st.warning("El nombre del tema no puede estar vacío.")
                else:
                    try:
                        create_topic(topic_name)
                        st.success("Tema guardado.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.warning("Ese tema ya existe.")

    st.divider()
    st.subheader("Temas configurados")

    if not current_topics:
        st.info("Aún no hay temas.")
        return

    for topic in current_topics:
        topic_id = int(topic["id"])
        topic_name = str(topic["name"])

        with st.container(border=True):
            st.markdown(f"### {topic_name}")

            subtopics = get_subtopics(topic_id)
            exclusions = get_exclusions(topic_id)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Subtemas**")
                if subtopics:
                    for subtopic in subtopics:
                        st.write(f"- {subtopic['name']}")
                else:
                    st.caption("Sin subtemas todavía.")

                if len(subtopics) >= MAX_SUBTOPICS_PER_TOPIC:
                    st.caption("Límite de 3 subtemas alcanzado.")
                else:
                    with st.form(f"subtopic_form_{topic_id}", clear_on_submit=True):
                        subtopic_name = st.text_input("Añadir subtema", key=f"subtopic_input_{topic_id}")
                        add_subtopic = st.form_submit_button("Guardar subtema")
                        if add_subtopic:
                            if not subtopic_name.strip():
                                st.warning("El subtema no puede estar vacío.")
                            else:
                                try:
                                    create_subtopic(topic_id, subtopic_name)
                                    st.success("Subtema guardado.")
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    st.warning("Ese subtema ya existe en este tema.")

            with col2:
                st.markdown("**Exclusiones**")
                if exclusions:
                    for exclusion in exclusions:
                        st.write(f"- {exclusion['phrase']}")
                else:
                    st.caption("Sin exclusiones todavía.")

                with st.form(f"exclusion_form_{topic_id}", clear_on_submit=True):
                    exclusion_phrase = st.text_input("Añadir exclusión", key=f"exclusion_input_{topic_id}")
                    add_exclusion = st.form_submit_button("Guardar exclusión")
                    if add_exclusion:
                        if not exclusion_phrase.strip():
                            st.warning("La exclusión no puede estar vacía.")
                        else:
                            try:
                                create_exclusion(topic_id, exclusion_phrase)
                                st.success("Exclusión guardada.")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.warning("Esa exclusión ya existe en este tema.")


def render_radar_screen() -> None:
    st.header("2) Radar")
    st.write("Carga señales manuales y clasifícalas rápidamente.")

    topic_map = get_topic_map()
    topic_options = {"(Sin tema)": None}
    topic_options.update({name: topic_id for topic_id, name in topic_map.items()})

    st.subheader("Carga manual de señal")
    with st.form("signal_form", clear_on_submit=True):
        selected_topic_name = st.selectbox("Tema", list(topic_options.keys()))
        title = st.text_input("Título de la señal *")
        source = st.text_input("Fuente (opcional)")
        notes = st.text_area("Notas (opcional)")
        submitted = st.form_submit_button("Guardar señal")

        if submitted:
            if not title.strip():
                st.warning("El título es obligatorio.")
            else:
                create_signal(topic_options[selected_topic_name], title, source, notes)
                st.success("Señal guardada en Radar.")
                st.rerun()

    st.divider()
    st.subheader("Señales en Radar")

    signals = get_signals()
    if not signals:
        st.info("Aún no hay señales cargadas.")
        return

    for signal in signals:
        signal_id = int(signal["id"])
        topic_name = signal["topic_name"] or "Sin tema"
        created_at = datetime.fromisoformat(signal["created_at"]).strftime("%Y-%m-%d %H:%M")

        with st.container(border=True):
            st.markdown(f"**{signal['title']}**")
            st.caption(f"Tema: {topic_name} | Fuente: {signal['source'] or 'N/A'} | Fecha: {created_at}")
            if signal["notes"]:
                st.write(signal["notes"])

            col_status, col_action = st.columns([2, 1])
            with col_status:
                new_status = st.radio(
                    "Estado",
                    STATUSES,
                    horizontal=True,
                    index=STATUSES.index(signal["status"]),
                    key=f"status_{signal_id}",
                )
            with col_action:
                if st.button("Actualizar", key=f"update_{signal_id}"):
                    update_signal_status(signal_id, new_status)
                    st.success("Estado actualizado.")
                    st.rerun()


def render_memory_screen() -> None:
    st.header("3) Memoria")
    st.write("Vista por estado: guardada, descartada e idea.")

    col_saved, col_discarded, col_idea = st.columns(3)

    status_to_column = {
        "guardada": col_saved,
        "descartada": col_discarded,
        "idea": col_idea,
    }

    for status, column in status_to_column.items():
        with column:
            st.subheader(status.capitalize())
            items = get_signals_by_status(status)
            if not items:
                st.caption("Sin señales.")
                continue

            for signal in items:
                topic = signal["topic_name"] or "Sin tema"
                st.markdown(f"- **{signal['title']}** ({topic})")


def render_briefing_screen() -> None:
    st.header("4) Briefing")
    st.write("Resumen semanal simple basado en señales guardadas de los últimos 7 días.")

    weekly_saved = get_weekly_saved_signals()

    if not weekly_saved:
        st.info("No hay señales guardadas en la última semana.")
        return

    st.subheader("Briefing semanal")
    st.markdown(f"**Total de señales guardadas (7 días):** {len(weekly_saved)}")

    grouped_by_topic: dict[str, list[str]] = {}
    for signal in weekly_saved:
        topic_name = signal["topic_name"] or "Sin tema"
        grouped_by_topic.setdefault(topic_name, []).append(signal["title"])

    for topic_name, titles in grouped_by_topic.items():
        st.markdown(f"### {topic_name}")
        for title in titles:
            st.markdown(f"- {title}")


def run_app() -> None:
    init_db()
    setup_page()

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Temas creados: {topic_count()}/{MAX_TOPICS}")

    current_screen = nav()

    if current_screen == "Temas":
        render_topics_screen()
    elif current_screen == "Radar":
        render_radar_screen()
    elif current_screen == "Memoria":
        render_memory_screen()
    else:
        render_briefing_screen()


if __name__ == "__main__":
    run_app()
