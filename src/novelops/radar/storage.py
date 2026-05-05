from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import AnalyzedNovelSignal, RawNovelSignal, TopicOpportunity


SCHEMA = """
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
    llm_risk TEXT,
    FOREIGN KEY (signal_id) REFERENCES raw_signals(signal_id)
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

CREATE TABLE IF NOT EXISTS raw_signal_observations (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT NOT NULL,
    source TEXT NOT NULL,
    platform TEXT NOT NULL,
    rank_type TEXT,
    rank_position INTEGER,
    hot_score REAL,
    rank_metric_name TEXT,
    rank_metric_value REAL,
    source_url TEXT,
    snapshot_date TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    FOREIGN KEY (signal_id) REFERENCES raw_signals(signal_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_signals_source ON raw_signals(source, source_type);
CREATE INDEX IF NOT EXISTS idx_raw_signals_platform ON raw_signals(platform);
CREATE INDEX IF NOT EXISTS idx_raw_signals_collected ON raw_signals(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyzed_signals_score ON analyzed_signals(commercial_potential_score DESC);
CREATE INDEX IF NOT EXISTS idx_topic_opportunities_score ON topic_opportunities(final_score DESC);
CREATE INDEX IF NOT EXISTS idx_raw_observations_signal ON raw_signal_observations(signal_id, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_observations_snapshot ON raw_signal_observations(source, snapshot_date);
"""


class RadarStorage:
    """NovelRadar 存储层"""
    
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or Path("runtime/radar/radar.sqlite")
    
    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self) -> None:
        conn = self.connect()
        try:
            conn.executescript(SCHEMA)
            self._migrate_analyzed_signals(conn)
            conn.commit()
        finally:
            conn.close()
    
    def _migrate_analyzed_signals(self, conn: sqlite3.Connection) -> None:
        """安全地为 analyzed_signals 表添加新列"""
        new_columns = [
            ("llm_genre", "TEXT"),
            ("llm_core_desire", "TEXT"),
            ("llm_hook", "TEXT"),
            ("llm_golden_finger", "TEXT"),
            ("llm_reader_emotion", "TEXT"),
            ("llm_risk", "TEXT"),
        ]
        
        cursor = conn.execute("PRAGMA table_info(analyzed_signals)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                conn.execute(f"ALTER TABLE analyzed_signals ADD COLUMN {col_name} {col_type}")
    
    def save_raw_signals(self, signals: list[RawNovelSignal]) -> int:
        conn = self.connect()
        try:
            count = 0
            for s in signals:
                conn.execute(
                    """INSERT OR REPLACE INTO raw_signals 
                    (signal_id, source, source_type, platform, rank_type, rank_position,
                     title, author, category, sub_category, tags, description,
                     hot_score, comment_count, like_count, read_count,
                     collected_at, raw_payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (s.signal_id, s.source, s.source_type, s.platform,
                     s.rank_type, s.rank_position, s.title, s.author,
                     s.category, s.sub_category, json.dumps(s.tags, ensure_ascii=False),
                     s.description, s.hot_score, s.comment_count,
                     s.like_count, s.read_count, s.collected_at,
                     json.dumps(s.raw_payload, ensure_ascii=False))
                )
                count += 1
            conn.commit()
            return count
        finally:
            conn.close()

    def save_raw_signal_observations(self, signals: list[RawNovelSignal]) -> int:
        conn = self.connect()
        try:
            count = 0
            for s in signals:
                payload = s.raw_payload or {}
                conn.execute(
                    """INSERT INTO raw_signal_observations
                    (signal_id, source, platform, rank_type, rank_position, hot_score,
                     rank_metric_name, rank_metric_value, source_url, snapshot_date,
                     collected_at, raw_payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        s.signal_id,
                        s.source,
                        s.platform,
                        s.rank_type,
                        s.rank_position,
                        s.hot_score,
                        payload.get("rank_metric_name"),
                        payload.get("rank_metric_value"),
                        payload.get("source_url"),
                        payload.get("snapshot_date") or s.collected_at[:10],
                        s.collected_at,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
                count += 1
            conn.commit()
            return count
        finally:
            conn.close()
    
    def save_analyzed_signals(self, signals: list[AnalyzedNovelSignal]) -> int:
        conn = self.connect()
        try:
            count = 0
            for s in signals:
                conn.execute(
                    """INSERT OR REPLACE INTO analyzed_signals 
                    (signal_id, source, source_type, platform, rank_type, rank_position,
                     title, author, category, sub_category, tags, description,
                     hot_score, comment_count, like_count, read_count,
                     collected_at, raw_payload,
                     extracted_genre, protagonist_template, golden_finger,
                     core_hook, reader_desire, shuang_points, risk_points,
                     platform_fit_score, competition_score, writing_difficulty_score,
                     commercial_potential_score, analyzed_at, analyzer_version,
                     llm_genre, llm_core_desire, llm_hook, llm_golden_finger,
                     llm_reader_emotion, llm_risk)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (s.signal_id, s.source, s.source_type, s.platform,
                     s.rank_type, s.rank_position, s.title, s.author,
                     s.category, s.sub_category, json.dumps(s.tags, ensure_ascii=False),
                     s.description, s.hot_score, s.comment_count,
                     s.like_count, s.read_count, s.collected_at,
                     json.dumps(s.raw_payload, ensure_ascii=False),
                     s.extracted_genre, s.protagonist_template, s.golden_finger,
                     s.core_hook, s.reader_desire,
                     json.dumps(s.shuang_points, ensure_ascii=False),
                     json.dumps(s.risk_points, ensure_ascii=False),
                     s.platform_fit_score, s.competition_score,
                     s.writing_difficulty_score, s.commercial_potential_score,
                     s.analyzed_at, s.analyzer_version,
                     s.llm_genre, s.llm_core_desire, s.llm_hook,
                     s.llm_golden_finger,
                     json.dumps(s.llm_reader_emotion, ensure_ascii=False),
                     s.llm_risk)
                )
                count += 1
            conn.commit()
            return count
        finally:
            conn.close()
    
    def save_topic_opportunities(self, topics: list[TopicOpportunity]) -> int:
        conn = self.connect()
        try:
            count = 0
            for t in topics:
                conn.execute(
                    """INSERT OR REPLACE INTO topic_opportunities 
                    (topic_id, topic_name, target_platform, target_reader,
                     core_tags, evidence_titles, hot_score, competition_score,
                     platform_fit_score, writing_difficulty_score, final_score,
                     opening_hook, suggested_story_seed, risks, generated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (t.topic_id, t.topic_name, t.target_platform, t.target_reader,
                     json.dumps(t.core_tags, ensure_ascii=False),
                     json.dumps(t.evidence_titles, ensure_ascii=False),
                     t.hot_score, t.competition_score, t.platform_fit_score,
                     t.writing_difficulty_score, t.final_score, t.opening_hook,
                     t.suggested_story_seed,
                     json.dumps(t.risks, ensure_ascii=False),
                     t.generated_at)
                )
                count += 1
            conn.commit()
            return count
        finally:
            conn.close()
    
    def list_raw_signals(self, limit: int = 100) -> list[RawNovelSignal]:
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM raw_signals ORDER BY collected_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [self._row_to_raw_signal(row) for row in rows]
        finally:
            conn.close()
    
    def list_analyzed_signals(self, limit: int = 100) -> list[AnalyzedNovelSignal]:
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM analyzed_signals ORDER BY commercial_potential_score DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [self._row_to_analyzed_signal(row) for row in rows]
        finally:
            conn.close()
    
    def list_topic_opportunities(self, limit: int = 50) -> list[TopicOpportunity]:
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM topic_opportunities ORDER BY final_score DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [self._row_to_topic_opportunity(row) for row in rows]
        finally:
            conn.close()
    
    def get_raw_signal(self, signal_id: str) -> RawNovelSignal | None:
        conn = self.connect()
        try:
            row = conn.execute(
                "SELECT * FROM raw_signals WHERE signal_id = ?",
                (signal_id,)
            ).fetchone()
            return self._row_to_raw_signal(row) if row else None
        finally:
            conn.close()
    
    def count_raw_signals(self) -> int:
        conn = self.connect()
        try:
            row = conn.execute("SELECT COUNT(*) FROM raw_signals").fetchone()
            return row[0]
        finally:
            conn.close()
    
    def count_analyzed_signals(self) -> int:
        conn = self.connect()
        try:
            row = conn.execute("SELECT COUNT(*) FROM analyzed_signals").fetchone()
            return row[0]
        finally:
            conn.close()

    def count_raw_signal_observations(self) -> int:
        conn = self.connect()
        try:
            row = conn.execute("SELECT COUNT(*) FROM raw_signal_observations").fetchone()
            return row[0]
        finally:
            conn.close()
    
    def _row_to_raw_signal(self, row: sqlite3.Row) -> RawNovelSignal:
        return RawNovelSignal(
            signal_id=row["signal_id"],
            source=row["source"],
            source_type=row["source_type"],
            platform=row["platform"],
            rank_type=row["rank_type"],
            rank_position=row["rank_position"],
            title=row["title"],
            author=row["author"],
            category=row["category"],
            sub_category=row["sub_category"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            description=row["description"],
            hot_score=row["hot_score"],
            comment_count=row["comment_count"],
            like_count=row["like_count"],
            read_count=row["read_count"],
            collected_at=row["collected_at"],
            raw_payload=json.loads(row["raw_payload"]) if row["raw_payload"] else {},
        )
    
    def _row_to_analyzed_signal(self, row: sqlite3.Row) -> AnalyzedNovelSignal:
        return AnalyzedNovelSignal(
            signal_id=row["signal_id"],
            source=row["source"],
            source_type=row["source_type"],
            platform=row["platform"],
            rank_type=row["rank_type"],
            rank_position=row["rank_position"],
            title=row["title"],
            author=row["author"],
            category=row["category"],
            sub_category=row["sub_category"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            description=row["description"],
            hot_score=row["hot_score"],
            comment_count=row["comment_count"],
            like_count=row["like_count"],
            read_count=row["read_count"],
            collected_at=row["collected_at"],
            raw_payload=json.loads(row["raw_payload"]) if row["raw_payload"] else {},
            extracted_genre=row["extracted_genre"],
            protagonist_template=row["protagonist_template"],
            golden_finger=row["golden_finger"],
            core_hook=row["core_hook"],
            reader_desire=row["reader_desire"],
            shuang_points=json.loads(row["shuang_points"]) if row["shuang_points"] else [],
            risk_points=json.loads(row["risk_points"]) if row["risk_points"] else [],
            platform_fit_score=row["platform_fit_score"] or 0.0,
            competition_score=row["competition_score"] or 0.0,
            writing_difficulty_score=row["writing_difficulty_score"] or 0.0,
            commercial_potential_score=row["commercial_potential_score"] or 0.0,
            analyzed_at=row["analyzed_at"],
            analyzer_version=row["analyzer_version"],
            llm_genre=row["llm_genre"],
            llm_core_desire=row["llm_core_desire"],
            llm_hook=row["llm_hook"],
            llm_golden_finger=row["llm_golden_finger"],
            llm_reader_emotion=json.loads(row["llm_reader_emotion"]) if row["llm_reader_emotion"] else [],
            llm_risk=row["llm_risk"],
        )
    
    def _row_to_topic_opportunity(self, row: sqlite3.Row) -> TopicOpportunity:
        return TopicOpportunity(
            topic_id=row["topic_id"],
            topic_name=row["topic_name"],
            target_platform=row["target_platform"],
            target_reader=row["target_reader"],
            core_tags=json.loads(row["core_tags"]) if row["core_tags"] else [],
            evidence_titles=json.loads(row["evidence_titles"]) if row["evidence_titles"] else [],
            hot_score=row["hot_score"] or 0.0,
            competition_score=row["competition_score"] or 0.0,
            platform_fit_score=row["platform_fit_score"] or 0.0,
            writing_difficulty_score=row["writing_difficulty_score"] or 0.0,
            final_score=row["final_score"] or 0.0,
            opening_hook=row["opening_hook"],
            suggested_story_seed=row["suggested_story_seed"],
            risks=json.loads(row["risks"]) if row["risks"] else [],
            generated_at=row["generated_at"],
        )
