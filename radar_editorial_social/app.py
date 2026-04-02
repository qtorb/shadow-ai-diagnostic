"""MVP interno: Radar de Novedades Editoriales (Fase 2)."""

from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import datetime

import streamlit as st

from db import (
    BOOK_STATUSES,
    compute_editorial_score,
    create_book,
    create_exclusion,
    create_subtopic,
    create_topic,
    delete_topic,
    get_books,
    get_books_by_status,
    get_exclusions,
    get_shortlist_counts,
    get_subtopics,
    get_topic,
    get_topics,
    get_weekly_saved_books,
    init_db,
    topic_count,
    update_topic,
    update_book_status,
)
from services.google_books import search_google_books
from services.open_library import search_open_library

MAX_TOPICS = 12
MAX_SUBTOPICS_PER_TOPIC = 5


def setup_page() -> None:
    st.set_page_config(page_title="Radar de Novedades Editoriales", page_icon="📚", layout="wide")
    st.title("📚 Radar de Novedades Editoriales")
    st.caption("Detecta, prioriza y decide qué novedades editoriales merecen atención.")


def nav() -> str:
    return st.sidebar.radio(
        "Navegación",
        ["Inicio", "Configurar radar", "Novedades", "Shortlist", "Briefing"],
        key="nav_choice",
    )


def render_inicio_screen() -> None:
    st.header("Inicio")
    st.write(
        "Esta herramienta te ayuda a configurar tus temas editoriales, revisar novedades y "
        "construir una shortlist útil para decidir qué merece seguimiento."
    )

    active_topics = topic_count()
    shortlist_counts = get_shortlist_counts()
    weekly_saved = get_weekly_saved_books()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Temas activos", active_topics)
        st.caption("Puedes seguir hasta 12 temas.")
    with c2:
        total_shortlist = shortlist_counts["guardado"] + shortlist_counts["siguiendo"]
        st.metric("Items en shortlist", total_shortlist)
        st.caption("Guardados + siguiendo.")
    with c3:
        st.metric("Briefing semanal", "Disponible" if weekly_saved else "Pendiente")
        st.caption("Se activa cuando tienes guardados recientes.")

    st.divider()
    if active_topics == 0:
        st.info("Empieza creando tu primer tema para que el radar entienda qué te interesa.")
        if st.button("➡️ Configurar radar", type="primary"):
            st.session_state["nav_choice"] = "Configurar radar"
            st.rerun()
    else:
        st.success("Tu radar está configurado. Siguiente paso recomendado: revisar novedades.")
        if st.button("➡️ Ver novedades", type="primary"):
            st.session_state["nav_choice"] = "Novedades"
            st.rerun()


def render_topics_screen() -> None:
    st.header("Configurar radar")
    st.write(
        "Define los temas que quieres seguir. Cada tema te ayuda a encontrar novedades más relevantes."
    )

    current_topics = get_topics()
    st.subheader("Añadir tema")

    if len(current_topics) >= MAX_TOPICS:
        st.info("Ya tienes 12 temas activos. Edita o elimina uno para añadir otro.")
    else:
        with st.form("topic_form", clear_on_submit=True):
            topic_name = st.text_input("Nombre del tema")
            language = st.selectbox("Idioma principal", ["", "es", "en", "ca", "fr", "pt"])
            non_fiction = st.checkbox("Solo no ficción")
            time_window = st.selectbox("Ventana temporal", [30, 60, 90], index=1)
            preferred_authors = st.text_input("Autores preferidos (separados por coma)")
            preferred_publishers = st.text_input("Editoriales preferidas (separadas por coma)")
            submitted = st.form_submit_button("Añadir tema")

            if submitted:
                if not topic_name.strip():
                    st.warning("El nombre del tema no puede estar vacío.")
                else:
                    try:
                        create_topic(
                            topic_name,
                            language,
                            non_fiction,
                            int(time_window),
                            preferred_authors,
                            preferred_publishers,
                        )
                        st.success("Tema añadido.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.warning("Ese tema ya existe.")

    st.divider()
    st.subheader("Tus temas")

    if not current_topics:
        st.info("Aún no tienes temas. Empieza creando uno para activar el radar.")
        return

    for topic in current_topics:
        topic_id = int(topic["id"])
        topic_name = str(topic["name"])

        with st.container(border=True):
            st.markdown(f"### {topic_name}")
            st.caption(
                " | ".join(
                    [
                        f"Idioma: {topic['language'] or 'cualquiera'}",
                        f"No ficción: {'sí' if topic['non_fiction'] else 'no'}",
                        f"Ventana: {topic['time_window'] or 60} días",
                    ]
                )
            )
            st.caption(
                f"Autores preferidos: {topic['preferred_authors'] or 'N/D'} | "
                f"Editoriales preferidas: {topic['preferred_publishers'] or 'N/D'}"
            )

            action_col_1, action_col_2 = st.columns([1, 1])
            with action_col_1:
                with st.expander("Editar tema"):
                    with st.form(f"edit_topic_form_{topic_id}"):
                        edit_name = st.text_input("Nombre", value=topic_name)
                        edit_language = st.selectbox(
                            "Idioma principal",
                            ["", "es", "en", "ca", "fr", "pt"],
                            index=["", "es", "en", "ca", "fr", "pt"].index(str(topic["language"] or "")),
                            key=f"edit_lang_{topic_id}",
                        )
                        edit_non_fiction = st.checkbox(
                            "Solo no ficción", value=bool(topic["non_fiction"]), key=f"edit_nf_{topic_id}"
                        )
                        current_window = int(topic["time_window"] or 60)
                        edit_time_window = st.selectbox(
                            "Ventana temporal", [30, 60, 90], index=[30, 60, 90].index(current_window)
                        )
                        edit_authors = st.text_input(
                            "Autores preferidos", value=str(topic["preferred_authors"] or "")
                        )
                        edit_publishers = st.text_input(
                            "Editoriales preferidas", value=str(topic["preferred_publishers"] or "")
                        )
                        if st.form_submit_button("Guardar cambios"):
                            if not edit_name.strip():
                                st.warning("El nombre del tema no puede estar vacío.")
                            else:
                                try:
                                    update_topic(
                                        topic_id=topic_id,
                                        name=edit_name,
                                        language=edit_language,
                                        non_fiction=edit_non_fiction,
                                        time_window=int(edit_time_window),
                                        preferred_authors=edit_authors,
                                        preferred_publishers=edit_publishers,
                                    )
                                    st.success("Tema actualizado.")
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    st.warning("Ya existe un tema con ese nombre.")
            with action_col_2:
                if st.button("Eliminar tema", key=f"delete_topic_{topic_id}"):
                    delete_topic(topic_id)
                    st.success("Tema eliminado.")
                    st.rerun()

            st.divider()
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
                    st.caption("Límite de 5 subtemas alcanzado.")
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


def _search_and_store_books(topic_id: int, per_query: int) -> tuple[int, int, list[str]]:
    topic = get_topic(topic_id)
    if topic is None:
        return 0, 0, ["Tema no encontrado"]

    subtopics = get_subtopics(topic_id)
    queries = [str(topic["name"])] + [str(subtopic["name"]) for subtopic in subtopics]
    errors: list[str] = []
    created = 0
    duplicated = 0

    for query in queries:
        google_books, google_error = search_google_books(
            query=query,
            language=str(topic["language"] or ""),
            max_results=per_query,
            non_fiction_only=bool(topic["non_fiction"]),
        )
        if google_error:
            errors.append(google_error)

        open_library_books, open_error = search_open_library(
            query=query,
            language=str(topic["language"] or ""),
            max_results=per_query,
            non_fiction_only=bool(topic["non_fiction"]),
        )
        if open_error:
            errors.append(open_error)

        for book in google_books + open_library_books:
            subtopic_id = next(
                (
                    int(st_row["id"])
                    for st_row in subtopics
                    if str(st_row["name"]).lower() in f"{book['titulo']} {book['descripcion']}".lower()
                ),
                None,
            )
            subtopic_name = next(
                (str(st_row["name"]) for st_row in subtopics if int(st_row["id"]) == subtopic_id),
                "",
            )
            score, why_fit = compute_editorial_score(
                topic=topic,
                subtopic_name=subtopic_name,
                title=book["titulo"],
                description=book["descripcion"],
                author=book["autor"],
                publisher=book["editorial"],
                language=book["idioma"],
                publication_date=book["fecha_publicacion"],
            )

            was_created = create_book(
                topic_id=topic_id,
                subtopic_id=subtopic_id,
                title=book["titulo"],
                author=book["autor"],
                publisher=book["editorial"],
                publication_date=book["fecha_publicacion"],
                language=book["idioma"],
                description=book["descripcion"],
                source=book["source_url"],
                origin=book["fuente_origen"],
                score=score,
                why_fit=why_fit,
                status="siguiendo",
            )
            if was_created:
                created += 1
            else:
                duplicated += 1

    return created, duplicated, errors


def render_novedades_screen() -> None:
    st.header("Novedades")
    st.write("Revisa novedades editoriales y guarda lo más prometedor para tu shortlist.")

    topics = get_topics()
    if not topics:
        st.info("Añade un tema en Configurar radar para empezar a detectar novedades.")
        return

    topic_options = {str(topic["name"]): int(topic["id"]) for topic in topics}

    with st.form("books_ingest_form"):
        selected_topic = st.selectbox("Tema a explorar", list(topic_options.keys()))
        per_query = st.slider("Resultados por tema/subtema", min_value=2, max_value=8, value=4)
        submitted = st.form_submit_button("Buscar novedades reales")

        if submitted:
            created, duplicated, errors = _search_and_store_books(topic_options[selected_topic], per_query)
            st.success(f"Hemos encontrado {created} novedades nuevas ({duplicated} duplicadas).")
            if errors:
                st.warning("Alguna fuente no respondió, pero el radar siguió funcionando:")
                for error in sorted(set(errors)):
                    st.caption(f"- {error}")
            st.rerun()

    st.divider()

    filter_col_1, filter_col_2 = st.columns(2)
    with filter_col_1:
        filter_topic_name = st.selectbox("Filtrar por tema", ["(Todos)"] + list(topic_options.keys()))
    with filter_col_2:
        filter_status = st.selectbox("Filtrar por estado", ["todos"] + BOOK_STATUSES)

    selected_topic_id = topic_options.get(filter_topic_name) if filter_topic_name != "(Todos)" else None
    books = get_books(topic_id=selected_topic_id, status=filter_status)

    if not books:
        st.info("Todavía no tienes novedades revisadas. Lanza una búsqueda para empezar.")
        return

    for book in books:
        book_id = int(book["id"])
        created_at = datetime.fromisoformat(book["created_at"]).strftime("%Y-%m-%d %H:%M")

        with st.container(border=True):
            st.markdown(f"### {book['title']}")
            st.caption(
                " | ".join(
                    [
                        f"Autor: {book['author'] or 'N/D'}",
                        f"Editorial: {book['publisher'] or 'N/D'}",
                        f"Fecha pub.: {book['publication_date'] or 'N/D'}",
                        f"Idioma: {book['language'] or 'N/D'}",
                    ]
                )
            )
            st.caption(
                " | ".join(
                    [
                        f"Tema: {book['topic_name'] or 'Sin tema'}",
                        f"Subtema: {book['subtopic_name'] or 'N/D'}",
                        f"Fuente origen: {book['origin']}",
                        f"Score: {book['relevance_score']}",
                        f"Estado: {book['status']}",
                        f"Detectado: {created_at}",
                    ]
                )
            )
            if book["notes"]:
                st.write(book["notes"])
            st.caption(f"Por qué encaja: {book['why_fit'] or 'Encaje general con el tema'}")

            if book["source"]:
                st.link_button("Ver fuente", book["source"])

            col_status, col_action = st.columns([2, 1])
            with col_status:
                new_status = st.radio(
                    "Estado",
                    BOOK_STATUSES,
                    horizontal=True,
                    index=BOOK_STATUSES.index(book["status"]),
                    key=f"status_{book_id}",
                )
            with col_action:
                if st.button("Actualizar", key=f"update_{book_id}"):
                    update_book_status(book_id, new_status)
                    st.success("Estado actualizado.")
                    st.rerun()


def render_shortlist_screen() -> None:
    st.header("Shortlist")
    st.write("Organiza tus decisiones editoriales en tres bloques claros.")

    tabs = st.tabs(["Guardados", "Siguiendo", "Descartados"])
    status_by_tab = [("guardado", tabs[0]), ("siguiendo", tabs[1]), ("descartado", tabs[2])]
    for status, tab in status_by_tab:
        with tab:
            items = get_books_by_status(status)
            if not items:
                st.caption("Tu shortlist está vacía en esta sección.")
                continue
            for book in items:
                with st.container(border=True):
                    st.markdown(f"**{book['title']}**")
                    st.caption(
                        f"{book['author'] or 'Autor N/D'} | {book['topic_name'] or 'Sin tema'} | "
                        f"Score {book['relevance_score']}"
                    )


def render_briefing_screen() -> None:
    st.header("Briefing")
    st.write("Una síntesis editorial para decidir qué merece atención esta semana.")

    weekly_books = get_weekly_saved_books()
    if not weekly_books:
        st.info("Aún no hay guardados recientes. Revisa novedades y guarda lo más prometedor.")
        return

    st.subheader("Libros nuevos más relevantes")
    for book in weekly_books[:10]:
        st.markdown(
            f"- **{book['title']}** · {book['author'] or 'Autor N/D'} "
            f"(score {book['relevance_score']})"
        )

    topic_counter = Counter(str(book["topic_name"] or "Sin tema") for book in weekly_books)
    author_counter = Counter(str(book["author"] or "") for book in weekly_books if book["author"])
    publisher_counter = Counter(str(book["publisher"] or "") for book in weekly_books if book["publisher"])

    st.subheader("Patrones por tema")
    for topic_name, count in topic_counter.most_common(5):
        st.markdown(f"- {topic_name}: {count} libros guardados")

    st.subheader("Autores/editoriales que se repiten")
    repeated_authors = [item for item in author_counter.items() if item[1] > 1]
    repeated_publishers = [item for item in publisher_counter.items() if item[1] > 1]

    if repeated_authors:
        st.markdown("**Autores**")
        for author, count in repeated_authors[:5]:
            st.markdown(f"- {author} ({count})")

    if repeated_publishers:
        st.markdown("**Editoriales**")
        for publisher, count in repeated_publishers[:5]:
            st.markdown(f"- {publisher} ({count})")

    st.subheader("Posibles libros prometedores para seguir o reseñar")
    following_or_high_score = [
        book
        for book in weekly_books
        if int(book["relevance_score"]) >= 70 or (book["why_fit"] and "prefer" in str(book["why_fit"]).lower())
    ]
    if not following_or_high_score:
        st.caption("No hay candidatos claros todavía.")
    else:
        for book in following_or_high_score[:5]:
            st.markdown(f"- **{book['title']}** ({book['why_fit']})")


def run_app() -> None:
    init_db()
    setup_page()

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Temas activos: {topic_count()}/{MAX_TOPICS}")

    current_screen = nav()
    if current_screen == "Inicio":
        render_inicio_screen()
    elif current_screen == "Configurar radar":
        render_topics_screen()
    elif current_screen == "Novedades":
        render_novedades_screen()
    elif current_screen == "Shortlist":
        render_shortlist_screen()
    else:
        render_briefing_screen()


if __name__ == "__main__":
    run_app()
