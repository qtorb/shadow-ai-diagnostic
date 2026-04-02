"""Funciones de base de datos para Radar de Novedades Editoriales."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "radar_editorial_social.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"
BOOK_STATUSES = ["guardado", "descartado", "siguiendo"]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
        _ensure_topic_columns(conn)
        _migrate_signals_to_books_if_needed(conn)
        _ensure_signal_columns(conn)
        _migrate_status_values(conn)


def _ensure_topic_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(topics)").fetchall()}
    if "language" not in columns:
        conn.execute("ALTER TABLE topics ADD COLUMN language TEXT")
    if "non_fiction" not in columns:
        conn.execute("ALTER TABLE topics ADD COLUMN non_fiction INTEGER NOT NULL DEFAULT 0")
    if "time_window" not in columns:
        conn.execute("ALTER TABLE topics ADD COLUMN time_window INTEGER")
    if "preferred_authors" not in columns:
        conn.execute("ALTER TABLE topics ADD COLUMN preferred_authors TEXT")
    if "preferred_publishers" not in columns:
        conn.execute("ALTER TABLE topics ADD COLUMN preferred_publishers TEXT")


def _migrate_signals_to_books_if_needed(conn: sqlite3.Connection) -> None:
    """Recrea la tabla signals si tiene el CHECK de estados antiguo."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='signals'"
    ).fetchone()
    sql = (row["sql"] or "") if row else ""
    if "guardada" not in sql:
        return

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS signals_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER,
            subtopic_id INTEGER,
            title TEXT NOT NULL,
            author TEXT,
            publisher TEXT,
            publication_date TEXT,
            language TEXT,
            source TEXT,
            origin TEXT NOT NULL DEFAULT 'web/rss',
            notes TEXT,
            why_fit TEXT,
            relevance_score INTEGER NOT NULL DEFAULT 50,
            status TEXT NOT NULL DEFAULT 'siguiendo' CHECK (status IN ('guardado', 'descartado', 'siguiendo')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL,
            FOREIGN KEY (subtopic_id) REFERENCES subtopics(id) ON DELETE SET NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO signals_new(
            id, topic_id, subtopic_id, title, author, publisher, publication_date, language,
            source, origin, notes, why_fit, relevance_score, status, created_at
        )
        SELECT
            id,
            topic_id,
            subtopic_id,
            title,
            author,
            publisher,
            publication_date,
            language,
            source,
            COALESCE(origin, 'web/rss'),
            notes,
            why_fit,
            COALESCE(relevance_score, 50),
            CASE
                WHEN status = 'guardada' THEN 'guardado'
                WHEN status = 'idea' THEN 'siguiendo'
                ELSE 'descartado'
            END,
            created_at
        FROM signals
        """
    )
    conn.execute("DROP TABLE signals")
    conn.execute("ALTER TABLE signals_new RENAME TO signals")


def _ensure_signal_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(signals)").fetchall()}
    if "subtopic_id" not in columns:
        conn.execute("ALTER TABLE signals ADD COLUMN subtopic_id INTEGER")
    if "author" not in columns:
        conn.execute("ALTER TABLE signals ADD COLUMN author TEXT")
    if "publisher" not in columns:
        conn.execute("ALTER TABLE signals ADD COLUMN publisher TEXT")
    if "publication_date" not in columns:
        conn.execute("ALTER TABLE signals ADD COLUMN publication_date TEXT")
    if "language" not in columns:
        conn.execute("ALTER TABLE signals ADD COLUMN language TEXT")
    if "origin" not in columns:
        conn.execute("ALTER TABLE signals ADD COLUMN origin TEXT NOT NULL DEFAULT 'web/rss'")
    if "why_fit" not in columns:
        conn.execute("ALTER TABLE signals ADD COLUMN why_fit TEXT")
    if "relevance_score" not in columns:
        conn.execute("ALTER TABLE signals ADD COLUMN relevance_score INTEGER NOT NULL DEFAULT 50")

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_title_author_unique
        ON signals (LOWER(TRIM(title)), LOWER(TRIM(COALESCE(author, ''))))
        """
    )


def _migrate_status_values(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE signals
        SET status = CASE
            WHEN status = 'guardada' THEN 'guardado'
            WHEN status = 'idea' THEN 'siguiendo'
            WHEN status = 'descartada' THEN 'descartado'
            ELSE status
        END
        WHERE status IN ('guardada', 'idea', 'descartada')
        """
    )


def get_topics() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, name, language, non_fiction, time_window, preferred_authors, preferred_publishers
            FROM topics
            ORDER BY created_at ASC
            """
        ).fetchall()


def create_topic(
    name: str,
    language: str,
    non_fiction: bool,
    time_window: int,
    preferred_authors: str,
    preferred_publishers: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO topics(name, language, non_fiction, time_window, preferred_authors, preferred_publishers)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name.strip(),
                language.strip().lower(),
                1 if non_fiction else 0,
                time_window,
                preferred_authors.strip(),
                preferred_publishers.strip(),
            ),
        )


def get_topic(topic_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()


def count_subtopics(topic_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM subtopics WHERE topic_id = ?", (topic_id,)).fetchone()
        return int(row["total"])


def create_subtopic(topic_id: int, name: str) -> None:
    with get_connection() as conn:
        conn.execute("INSERT INTO subtopics(topic_id, name) VALUES (?, ?)", (topic_id, name.strip()))


def get_subtopics(topic_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, name FROM subtopics WHERE topic_id = ? ORDER BY created_at ASC",
            (topic_id,),
        ).fetchall()


def create_exclusion(topic_id: int, phrase: str) -> None:
    with get_connection() as conn:
        conn.execute("INSERT INTO exclusions(topic_id, phrase) VALUES (?, ?)", (topic_id, phrase.strip()))


def get_exclusions(topic_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, phrase FROM exclusions WHERE topic_id = ? ORDER BY created_at ASC",
            (topic_id,),
        ).fetchall()


def _tokens(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def compute_editorial_score(
    topic: sqlite3.Row,
    subtopic_name: str,
    title: str,
    description: str,
    author: str,
    publisher: str,
    language: str,
    publication_date: str,
) -> tuple[int, str]:
    score = 40
    reasons: list[str] = []
    text = f"{title} {description}".lower()

    topic_name = str(topic["name"] or "").lower()
    if topic_name and topic_name in text:
        score += 20
        reasons.append("coincide con el tema")

    if subtopic_name and subtopic_name.lower() in text:
        score += 15
        reasons.append("coincide con subtema")

    expected_language = str(topic["language"] or "").lower()
    if expected_language and language.lower() == expected_language:
        score += 10
        reasons.append("idioma preferido")

    preferred_authors = _tokens(str(topic["preferred_authors"] or ""))
    if author and any(pref in author.lower() for pref in preferred_authors):
        score += 10
        reasons.append("autor preferido")

    preferred_publishers = _tokens(str(topic["preferred_publishers"] or ""))
    if publisher and any(pref in publisher.lower() for pref in preferred_publishers):
        score += 10
        reasons.append("editorial preferida")

    time_window = int(topic["time_window"] or 0)
    if publication_date and time_window in {30, 60, 90}:
        score += 5
        reasons.append("novedad editorial reciente")

    if not author or not publisher:
        score -= 8
        reasons.append("metadatos incompletos")

    bounded = max(0, min(100, score))
    why_fit = ", ".join(reasons) if reasons else "encaje general por tema"
    return bounded, why_fit


def book_exists(title: str, author: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM signals
            WHERE LOWER(TRIM(title)) = LOWER(TRIM(?))
              AND LOWER(TRIM(COALESCE(author, ''))) = LOWER(TRIM(COALESCE(?, '')))
            LIMIT 1
            """,
            (title.strip(), author.strip()),
        ).fetchone()
        return row is not None


def create_book(
    topic_id: int | None,
    subtopic_id: int | None,
    title: str,
    author: str,
    publisher: str,
    publication_date: str,
    language: str,
    description: str,
    source: str,
    origin: str,
    score: int,
    why_fit: str,
    status: str = "siguiendo",
) -> bool:
    if book_exists(title, author):
        return False

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO signals(
                topic_id, subtopic_id, title, author, publisher, publication_date, language,
                notes, source, origin, relevance_score, why_fit, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic_id,
                subtopic_id,
                title.strip(),
                author.strip(),
                publisher.strip(),
                publication_date.strip(),
                language.strip().lower(),
                description.strip(),
                source.strip(),
                origin.strip(),
                score,
                why_fit.strip(),
                status,
            ),
        )
    return True


def get_books(topic_id: int | None = None, status: str = "todos") -> list[sqlite3.Row]:
    query = """
        SELECT s.id,
               s.title,
               s.author,
               s.publisher,
               s.publication_date,
               s.language,
               s.source,
               s.origin,
               s.notes,
               s.why_fit,
               s.relevance_score,
               s.status,
               s.created_at,
               t.name AS topic_name,
               st.name AS subtopic_name
        FROM signals s
        LEFT JOIN topics t ON t.id = s.topic_id
        LEFT JOIN subtopics st ON st.id = s.subtopic_id
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

    query += " ORDER BY s.relevance_score DESC, s.created_at DESC, s.id DESC"

    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


def update_book_status(book_id: int, status: str) -> None:
    if status not in BOOK_STATUSES:
        return
    with get_connection() as conn:
        conn.execute("UPDATE signals SET status = ? WHERE id = ?", (status, book_id))


def get_books_by_status(status: str) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT s.id, s.title, s.author, s.publisher, s.relevance_score, t.name AS topic_name
            FROM signals s
            LEFT JOIN topics t ON t.id = s.topic_id
            WHERE s.status = ?
            ORDER BY s.relevance_score DESC, s.created_at DESC
            """,
            (status,),
        ).fetchall()


def get_weekly_saved_books() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT s.id, s.title, s.author, s.publisher, s.relevance_score, s.why_fit, t.name AS topic_name
            FROM signals s
            LEFT JOIN topics t ON t.id = s.topic_id
            WHERE s.status = 'guardado'
              AND datetime(s.created_at) >= datetime('now', '-7 days')
            ORDER BY s.relevance_score DESC, s.created_at DESC
            """
        ).fetchall()


def topic_count() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM topics").fetchone()
        return int(row["total"])


def get_topic_map() -> dict[str, int]:
    return {str(row["name"]): int(row["id"]) for row in get_topics()}
