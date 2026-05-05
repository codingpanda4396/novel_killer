import sqlite3
from pathlib import Path

import pytest

from novelops.radar.models import AnalyzedNovelSignal
from novelops.radar.storage import RadarStorage


def test_new_db_has_llm_columns(tmp_path):
    """测试新库创建包含新增列"""
    db_path = tmp_path / "test_radar.sqlite"
    storage = RadarStorage(db_path)
    storage.init_db()

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(analyzed_signals)")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()

    assert "llm_genre" in columns
    assert "llm_core_desire" in columns
    assert "llm_hook" in columns
    assert "llm_golden_finger" in columns
    assert "llm_reader_emotion" in columns
    assert "llm_risk" in columns


def test_old_db_migration(tmp_path):
    """测试旧 schema 初始化后自动补列，不丢旧数据"""
    db_path = tmp_path / "test_radar.sqlite"

    conn = sqlite3.connect(db_path)
    conn.executescript("""
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
            analyzer_version TEXT NOT NULL
        );
    """)
    conn.execute(
        """INSERT INTO analyzed_signals 
        (signal_id, source, source_type, platform, title, collected_at, raw_payload,
         analyzed_at, analyzer_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("test_001", "fanqie", "ranking", "番茄", "测试小说", "2024-01-01", "{}",
         "2024-01-01", "1.0.0"),
    )
    conn.commit()
    conn.close()

    storage = RadarStorage(db_path)
    storage.init_db()

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(analyzed_signals)")
    columns = {row[1] for row in cursor.fetchall()}

    row = conn.execute(
        "SELECT * FROM analyzed_signals WHERE signal_id = ?",
        ("test_001",),
    ).fetchone()
    conn.close()

    assert "llm_genre" in columns
    assert "llm_core_desire" in columns
    assert "llm_hook" in columns
    assert "llm_golden_finger" in columns
    assert "llm_reader_emotion" in columns
    assert "llm_risk" in columns

    assert row is not None
    assert row[0] == "test_001"


def test_save_and_load_llm_fields(tmp_path):
    """测试保存和读取 LLM 字段"""
    db_path = tmp_path / "test_radar.sqlite"
    storage = RadarStorage(db_path)
    storage.init_db()

    signal = AnalyzedNovelSignal(
        signal_id="test_001",
        source="fanqie",
        source_type="ranking",
        platform="番茄",
        title="测试小说",
        collected_at="2024-01-01",
        raw_payload={},
        analyzed_at="2024-01-01",
        analyzer_version="1.0.0",
        llm_genre="都市重生",
        llm_core_desire="逆袭",
        llm_hook="重回2010",
        llm_golden_finger="系统",
        llm_reader_emotion=["爽", "期待"],
        llm_risk="竞争激烈",
    )
    storage.save_analyzed_signals([signal])

    loaded = storage.list_analyzed_signals(limit=1)
    assert len(loaded) == 1
    assert loaded[0].llm_genre == "都市重生"
    assert loaded[0].llm_core_desire == "逆袭"
    assert loaded[0].llm_hook == "重回2010"
    assert loaded[0].llm_golden_finger == "系统"
    assert loaded[0].llm_reader_emotion == ["爽", "期待"]
    assert loaded[0].llm_risk == "竞争激烈"
