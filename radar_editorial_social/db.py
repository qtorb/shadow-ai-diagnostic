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


def create_signal(topic_id: int | None, title: str, source: str, notes: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO signals(topic_id, title, source, notes) VALUES (?, ?, ?, ?)",
            (topic_id, title.strip(), source.strip(), notes.strip()),
        )


def get_signals() -> list[sqlite3.Row]:
    query = """
        SELECT s.id,
               s.title,
               s.source,
               s.notes,
               s.status,
               s.created_at,
               t.name AS topic_name
        FROM signals s
        LEFT JOIN topics t ON t.id = s.topic_id
        ORDER BY s.created_at DESC, s.id DESC
    """
    with get_connection() as conn:
        return conn.execute(query).fetchall()


def update_signal_status(signal_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE signals SET status = ? WHERE id = ?", (status, signal_id))


def get_signals_by_status(status: str) -> list[sqlite3.Row]:
    query = """
        SELECT s.id,
               s.title,
               s.source,
               s.notes,
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
               s.notes,
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
