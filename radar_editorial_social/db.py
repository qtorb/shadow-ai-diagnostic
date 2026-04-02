"""Funciones de base de datos para el MVP Radar Editorial Social."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "radar_editorial_social.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """Devuelve una conexión SQLite con resultados tipo diccionario."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Crea las tablas al inicio usando el archivo schema.sql."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
        _ensure_signal_columns(conn)


def _ensure_signal_columns(conn: sqlite3.Connection) -> None:
    """Aplica migraciones simples para instalaciones previas del MVP."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(signals)").fetchall()}
    if "origin" not in columns:
        conn.execute("ALTER TABLE signals ADD COLUMN origin TEXT NOT NULL DEFAULT 'web/rss'")
    if "relevance_score" not in columns:
        conn.execute("ALTER TABLE signals ADD COLUMN relevance_score INTEGER NOT NULL DEFAULT 50")


def get_topics() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT id, name FROM topics ORDER BY created_at ASC").fetchall()


def create_topic(name: str) -> None:
    with get_connection() as conn:
        conn.execute("INSERT INTO topics(name) VALUES (?)", (name.strip(),))


def count_subtopics(topic_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM subtopics WHERE topic_id = ?", (topic_id,)).fetchone()
        return int(row["total"])


def create_subtopic(topic_id: int, name: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO subtopics(topic_id, name) VALUES (?, ?)",
            (topic_id, name.strip()),
        )


def get_subtopics(topic_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, name FROM subtopics WHERE topic_id = ? ORDER BY created_at ASC",
            (topic_id,),
        ).fetchall()


def create_exclusion(topic_id: int, phrase: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO exclusions(topic_id, phrase) VALUES (?, ?)",
            (topic_id, phrase.strip()),
        )


def get_exclusions(topic_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, phrase FROM exclusions WHERE topic_id = ? ORDER BY created_at ASC",
            (topic_id,),
        ).fetchall()


def compute_initial_relevance(topic_id: int | None, title: str, notes: str) -> int:
    """Calcula un score inicial simple en función de tema/subtemas/exclusiones."""
    score = 50
    text = f"{title} {notes}".lower()

    with get_connection() as conn:
        if topic_id is not None:
            topic = conn.execute("SELECT name FROM topics WHERE id = ?", (topic_id,)).fetchone()
            if topic and str(topic["name"]).lower() in text:
                score += 10

            subtopics = conn.execute(
                "SELECT name FROM subtopics WHERE topic_id = ?",
                (topic_id,),
            ).fetchall()
            for subtopic in subtopics:
                if str(subtopic["name"]).lower() in text:
                    score += 15

            exclusions = conn.execute(
                "SELECT phrase FROM exclusions WHERE topic_id = ?",
                (topic_id,),
            ).fetchall()
            for exclusion in exclusions:
                if str(exclusion["phrase"]).lower() in text:
                    score -= 20

    return max(0, min(100, score))


def signal_exists(title: str, source: str) -> bool:
    """Comprueba duplicados simples por título + fuente."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM signals WHERE title = ? AND COALESCE(source, '') = COALESCE(?, '') LIMIT 1",
            (title.strip(), source.strip()),
        ).fetchone()
        return row is not None


def create_signal(topic_id: int | None, title: str, source: str, notes: str, origin: str = "web/rss") -> bool:
    """Inserta señal si no es duplicada. Devuelve True cuando guarda."""
    clean_title = title.strip()
    clean_source = source.strip()
    clean_notes = notes.strip()

    if signal_exists(clean_title, clean_source):
        return False

    relevance_score = compute_initial_relevance(topic_id, clean_title, clean_notes)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO signals(topic_id, title, source, origin, notes, relevance_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (topic_id, clean_title, clean_source, origin, clean_notes, relevance_score),
        )
    return True


def get_signals(topic_id: int | None = None, status: str = "todos") -> list[sqlite3.Row]:
    query = """
        SELECT s.id,
               s.title,
               s.source,
               s.origin,
               s.notes,
               s.relevance_score,
               s.status,
               s.created_at,
               t.name AS topic_name
        FROM signals s
        LEFT JOIN topics t ON t.id = s.topic_id
    """
    params: list[Any] = []
    conditions: list[str] = []

    if topic_id is not None:
        conditions.append("s.topic_id = ?")
        params.append(topic_id)

    if status != "todos":
        conditions.append("s.status = ?")
        params.append(status)

    if conditions:
        query += f" WHERE {' AND '.join(conditions)}"

    query += " ORDER BY s.created_at DESC, s.id DESC"

    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


def update_signal_status(signal_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE signals SET status = ? WHERE id = ?", (status, signal_id))


def get_signals_by_status(status: str) -> list[sqlite3.Row]:
    query = """
        SELECT s.id,
               s.title,
               s.source,
               s.origin,
               s.notes,
               s.relevance_score,
               s.created_at,
               t.name AS topic_name
        FROM signals s
        LEFT JOIN topics t ON t.id = s.topic_id
        WHERE s.status = ?
        ORDER BY s.created_at DESC, s.id DESC
    """
    with get_connection() as conn:
        return conn.execute(query, (status,)).fetchall()


def get_weekly_saved_signals() -> list[sqlite3.Row]:
    query = """
        SELECT s.id,
               s.title,
               s.source,
               s.origin,
               s.notes,
               s.relevance_score,
               s.created_at,
               t.name AS topic_name
        FROM signals s
        LEFT JOIN topics t ON t.id = s.topic_id
        WHERE s.status = 'guardada'
          AND datetime(s.created_at) >= datetime('now', '-7 days')
        ORDER BY s.created_at DESC, s.id DESC
    """
    with get_connection() as conn:
        return conn.execute(query).fetchall()


def topic_count() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM topics").fetchone()
        return int(row["total"])


def get_topic_map() -> dict[int, str]:
    return {int(row["id"]): str(row["name"]) for row in get_topics()}


def to_dict_rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]
