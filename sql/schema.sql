-- Database schema for Streaming Retention & Engagement Analytics
-- Compatible with SQLite 3

CREATE TABLE IF NOT EXISTS content_catalog (
    content_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    release_date TEXT,
    runtime_minutes INTEGER,
    vote_average REAL,
    vote_count INTEGER,
    popularity REAL,
    genres TEXT,
    original_language TEXT,
    overview TEXT
);

CREATE TABLE IF NOT EXISTS viewer_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content_id INTEGER NOT NULL,
    started_at TEXT,
    watch_duration_minutes REAL,
    pause_count INTEGER,
    completion_pct REAL,
    finished INTEGER,
    FOREIGN KEY (content_id) REFERENCES content_catalog(content_id)
);

CREATE TABLE IF NOT EXISTS viewer_retention (
    user_id TEXT NOT NULL,
    observation_date TEXT NOT NULL,
    eligible_for_30d_retention INTEGER,
    retained_30d INTEGER,
    PRIMARY KEY (user_id, observation_date)
);

-- Denormalized/unified analytical view matching the ingestion interface
CREATE TABLE IF NOT EXISTS viewing_records (
    user_id TEXT NOT NULL,
    content_id INTEGER NOT NULL,
    watch_duration REAL,
    completion_rate REAL,
    pause_count INTEGER,
    sessions_per_week REAL,
    retained INTEGER,
    finished INTEGER DEFAULT 0
);
