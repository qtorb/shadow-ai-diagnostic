CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    language TEXT,
    non_fiction INTEGER NOT NULL DEFAULT 0,
    time_window INTEGER,
    preferred_authors TEXT,
    preferred_publishers TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS subtopics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(topic_id, name),
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS exclusions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    phrase TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(topic_id, phrase),
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS signals (
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
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_title_author_unique
ON signals (LOWER(TRIM(title)), LOWER(TRIM(COALESCE(author, ''))));
