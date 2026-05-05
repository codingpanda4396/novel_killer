from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlmodel import SQLModel

from .engine import database_url, get_engine
from . import models  # noqa: F401 - imports table metadata


LEGACY_PROJECTS_SQL = """
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  genre TEXT,
  path TEXT NOT NULL,
  target_platform TEXT,
  current_volume INTEGER,
  next_chapter INTEGER,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


LEGACY_RADAR_SQL = """
CREATE TABLE IF NOT EXISTS raw_signals (
    signal_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_type TEXT NOT NULL,
    platform TEXT NOT NULL,
    rank_type TEXT,
    rank_position INTEGER,
    title TEXT NOT NULL,
    author TEXT,
    category TEXT,
    sub_category TEXT,
    tags TEXT,
    description TEXT,
    hot_score REAL,
    comment_count INTEGER,
    like_count INTEGER,
    read_count INTEGER,
    collected_at TEXT NOT NULL,
    raw_payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyzed_signals (
    signal_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_type TEXT NOT NULL,
    platform TEXT NOT NULL,
    rank_type TEXT,
    rank_position INTEGER,
    title TEXT NOT NULL,
    author TEXT,
    category TEXT,
    sub_category TEXT,
    tags TEXT,
    description TEXT,
    hot_score REAL,
    comment_count INTEGER,
    like_count INTEGER,
    read_count INTEGER,
    collected_at TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    extracted_genre TEXT,
    protagonist_template TEXT,
    golden_finger TEXT,
    core_hook TEXT,
    reader_desire TEXT,
    shuang_points TEXT,
    risk_points TEXT,
    platform_fit_score REAL,
    competition_score REAL,
    writing_difficulty_score REAL,
    commercial_potential_score REAL,
    analyzed_at TEXT NOT NULL,
    analyzer_version TEXT NOT NULL,
    llm_genre TEXT,
    llm_core_desire TEXT,
    llm_hook TEXT,
    llm_golden_finger TEXT,
    llm_reader_emotion TEXT,
    llm_risk TEXT
);

CREATE TABLE IF NOT EXISTS topic_opportunities (
    topic_id TEXT PRIMARY KEY,
    topic_name TEXT NOT NULL,
    target_platform TEXT NOT NULL,
    target_reader TEXT NOT NULL,
    core_tags TEXT NOT NULL,
    evidence_titles TEXT NOT NULL,
    hot_score REAL NOT NULL,
    competition_score REAL NOT NULL,
    platform_fit_score REAL NOT NULL,
    writing_difficulty_score REAL NOT NULL,
    final_score REAL NOT NULL,
    opening_hook TEXT NOT NULL,
    suggested_story_seed TEXT NOT NULL,
    risks TEXT NOT NULL,
    generated_at TEXT NOT NULL
);
"""


INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_user_projects_user ON user_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_user_projects_default ON user_projects(user_id, is_default);
CREATE INDEX IF NOT EXISTS idx_story_projects_updated ON story_projects(updated_at);
CREATE INDEX IF NOT EXISTS idx_chapter_plans_project_chapter ON chapter_plans(project_id, chapter);
CREATE INDEX IF NOT EXISTS idx_hot_items_source ON hot_items(source, source_type);
CREATE INDEX IF NOT EXISTS idx_hot_items_platform ON hot_items(platform);
CREATE INDEX IF NOT EXISTS idx_hot_items_collected ON hot_items(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_market_reports_score ON market_reports(commercial_potential_score DESC);
CREATE INDEX IF NOT EXISTS idx_topic_opportunities_score ON topic_opportunities(final_score DESC);
CREATE INDEX IF NOT EXISTS idx_raw_signals_source ON raw_signals(source, source_type);
CREATE INDEX IF NOT EXISTS idx_raw_signals_platform ON raw_signals(platform);
CREATE INDEX IF NOT EXISTS idx_raw_signals_collected ON raw_signals(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyzed_signals_score ON analyzed_signals(commercial_potential_score DESC);
CREATE INDEX IF NOT EXISTS idx_raw_observations_signal ON raw_signal_observations(signal_id, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_observations_snapshot ON raw_signal_observations(source, snapshot_date);
"""


SQLITE_INCREMENTAL_COLUMNS = {
    "projects": [
        ("target_platform", "TEXT"),
    ],
    "chapters": [
        ("content_path", "TEXT"),
        ("path", "TEXT"),
    ],
    "analyzed_signals": [
        ("llm_genre", "TEXT"),
        ("llm_core_desire", "TEXT"),
        ("llm_hook", "TEXT"),
        ("llm_golden_finger", "TEXT"),
        ("llm_reader_emotion", "TEXT"),
        ("llm_risk", "TEXT"),
    ],
}


def init_db(path: Path | None = None) -> Path | None:
    """Create all SQLModel tables and compatibility tables."""
    engine = get_engine(path)
    SQLModel.metadata.create_all(engine)
    url = database_url(path)
    if url.startswith("sqlite:///"):
        sqlite_path = Path(url[len("sqlite:///"):])
        migrate_db(sqlite_path)
        return sqlite_path
    return None


def migrate_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(LEGACY_PROJECTS_SQL)
        conn.executescript(LEGACY_RADAR_SQL)
        _add_sqlite_columns(conn)
        _rebuild_user_projects_if_needed(conn)
        _backfill_chapter_paths(conn)
        _copy_legacy_to_new(conn)
        conn.executescript(INDEX_SQL)
        conn.commit()
    finally:
        conn.close()


def _add_sqlite_columns(conn: sqlite3.Connection) -> None:
    for table, columns in SQLITE_INCREMENTAL_COLUMNS.items():
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, col_type in columns:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}")


def _backfill_chapter_paths(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(chapters)")}
    if {"content_path", "path"}.issubset(existing):
        conn.execute("UPDATE chapters SET content_path = path WHERE content_path IS NULL AND path IS NOT NULL")
        conn.execute("UPDATE chapters SET path = content_path WHERE path IS NULL AND content_path IS NOT NULL")


def _rebuild_user_projects_if_needed(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(user_projects)").fetchall()
    if not rows:
        return
    defaults = {row[1]: row[4] for row in rows}
    if defaults.get("is_default") is not None and defaults.get("created_at") is not None:
        return
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS user_projects_new (
          user_id TEXT NOT NULL,
          project_id TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          is_default INTEGER DEFAULT 0,
          PRIMARY KEY (user_id, project_id)
        );
        INSERT OR IGNORE INTO user_projects_new (user_id, project_id, created_at, is_default)
        SELECT user_id, project_id, COALESCE(created_at, CURRENT_TIMESTAMP), COALESCE(is_default, 0)
        FROM user_projects;
        DROP TABLE user_projects;
        ALTER TABLE user_projects_new RENAME TO user_projects;
        """
    )


def _copy_legacy_to_new(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO story_projects
        (id, name, genre, path, target_platform, current_volume, next_chapter, updated_at)
        SELECT id, name, genre, path, target_platform, current_volume, next_chapter, updated_at
        FROM projects
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO hot_items
        (signal_id, source, source_type, platform, rank_type, rank_position, title, author,
         category, sub_category, tags, description, hot_score, comment_count, like_count,
         read_count, collected_at, raw_payload)
        SELECT signal_id, source, source_type, platform, rank_type, rank_position, title, author,
         category, sub_category, tags, description, hot_score, comment_count, like_count,
         read_count, collected_at, raw_payload
        FROM raw_signals
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO market_reports
        (report_id, hot_item_id, source, source_type, platform, rank_type, rank_position,
         title, author, category, sub_category, tags, description, hot_score, comment_count,
         like_count, read_count, collected_at, raw_payload, genre, protagonist_template,
         golden_finger, hook, core_desire, reader_emotion, risk, shuang_points, risk_points,
         platform_fit_score, competition_score, writing_difficulty_score,
         commercial_potential_score, analyzed_at, analyzer_version, model, report_json)
        SELECT signal_id, signal_id, source, source_type, platform, rank_type, rank_position,
         title, author, category, sub_category, tags, description, hot_score, comment_count,
         like_count, read_count, collected_at, raw_payload,
         COALESCE(llm_genre, extracted_genre), protagonist_template,
         COALESCE(llm_golden_finger, golden_finger), COALESCE(llm_hook, core_hook),
         COALESCE(llm_core_desire, reader_desire), llm_reader_emotion, llm_risk,
         shuang_points, risk_points, platform_fit_score, competition_score,
         writing_difficulty_score, commercial_potential_score, analyzed_at,
         analyzer_version, analyzer_version, NULL
        FROM analyzed_signals
        """
    )
