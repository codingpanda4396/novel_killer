from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .config import db_path, load_project_path
from .corpus import list_chapters, parse_title
from .paths import all_project_dirs, project_dir


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  genre TEXT,
  path TEXT NOT NULL,
  current_volume INTEGER,
  next_chapter INTEGER,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS chapters (
  project_id TEXT NOT NULL,
  chapter INTEGER NOT NULL,
  source_type TEXT NOT NULL,
  title TEXT,
  word_count INTEGER,
  path TEXT NOT NULL,
  status TEXT,
  PRIMARY KEY (project_id, chapter, source_type, path)
);
CREATE TABLE IF NOT EXISTS generation_runs (
  project_id TEXT NOT NULL,
  chapter INTEGER NOT NULL,
  final_stage TEXT,
  artifact_dir TEXT NOT NULL,
  llm_used INTEGER,
  final_score REAL,
  status TEXT,
  PRIMARY KEY (project_id, chapter, artifact_dir)
);
CREATE TABLE IF NOT EXISTS reviews (
  project_id TEXT NOT NULL,
  chapter INTEGER NOT NULL,
  score REAL,
  threshold_value REAL,
  passed INTEGER,
  action TEXT,
  model TEXT,
  fallback_reason TEXT,
  report_path TEXT NOT NULL,
  PRIMARY KEY (project_id, chapter, report_path)
);
CREATE TABLE IF NOT EXISTS revision_queue (
  project_id TEXT NOT NULL,
  chapter INTEGER NOT NULL,
  reason TEXT,
  source_report TEXT,
  status TEXT,
  path TEXT NOT NULL,
  PRIMARY KEY (project_id, chapter, path)
);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def rebuild_index(project_id: str | None = None, path: Path | None = None) -> Path:
    database = path or db_path()
    conn = connect(database)
    try:
        projects = [project_dir(project_id)] if project_id else all_project_dirs()
        if project_id:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            for table in ["chapters", "generation_runs", "reviews", "revision_queue"]:
                conn.execute(f"DELETE FROM {table} WHERE project_id = ?", (project_id,))
        else:
            for table in ["projects", "chapters", "generation_runs", "reviews", "revision_queue"]:
                conn.execute(f"DELETE FROM {table}")
        for project_path in projects:
            if (project_path / "project.json").is_file():
                index_project(conn, project_path)
        conn.commit()
    finally:
        conn.close()
    return database


def index_project(conn: sqlite3.Connection, project_path: Path) -> None:
    cfg = load_project_path(project_path)
    project_id = str(cfg["id"])
    current_volume = cfg.get("current_volume", {})
    conn.execute(
        "INSERT OR REPLACE INTO projects (id, name, genre, path, current_volume, next_chapter, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (
            project_id,
            cfg.get("name", project_id),
            cfg.get("genre"),
            str(project_path),
            current_volume.get("number"),
            current_volume.get("next_chapter"),
        ),
    )
    for chapter in list_chapters(project_path):
        _insert_chapter(conn, project_id, chapter.number, "corpus", chapter.title, chapter.word_count, chapter.path, "ready")
    _index_generated(conn, project_id, project_path)
    _index_reviews(conn, project_id, project_path)
    _index_revision_queue(conn, project_id, project_path)


def _insert_chapter(conn: sqlite3.Connection, project_id: str, chapter: int, source_type: str, title: str, word_count: int, path: Path, status: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO chapters (project_id, chapter, source_type, title, word_count, path, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (project_id, chapter, source_type, title, word_count, str(path), status),
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _word_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+", text))


def _index_generated(conn: sqlite3.Connection, project_id: str, project_path: Path) -> None:
    for directory in sorted((project_path / "generation").glob("chapter_*")):
        match = re.search(r"chapter_(\d+)", directory.name)
        if not match or not directory.is_dir():
            continue
        chapter = int(match.group(1))
        candidates = ["11_revision_v2.md", "09_revision_v1.md", "07_final_candidate.md", "06_humanized_rewrite.md", "04_draft_v1.md"]
        final_path = next((directory / name for name in candidates if (directory / name).is_file()), None)
        final_stage = final_path.stem if final_path else None
        final_score = None
        llm_used = 0
        status = "generated" if final_path else "planned"
        for review_name in ["12_revision_v2_review_gate.json", "10_revision_v1_review_gate.json", "08_review_gate.json"]:
            report = directory / review_name
            if report.is_file():
                data = _read_json(report)
                final_score = data.get("score")
                llm_used = 1 if data.get("llm_used") else 0
                status = "passed" if data.get("passed") else "needs_revision"
                break
        conn.execute(
            "INSERT OR REPLACE INTO generation_runs (project_id, chapter, final_stage, artifact_dir, llm_used, final_score, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, chapter, final_stage, str(directory), llm_used, final_score, status),
        )
        if final_path:
            text = final_path.read_text(encoding="utf-8", errors="ignore")
            _insert_chapter(conn, project_id, chapter, "generation", parse_title(text, final_path.stem), _word_count(text), final_path, status)


def _index_reviews(conn: sqlite3.Connection, project_id: str, project_path: Path) -> None:
    for report in sorted((project_path / "reviews").glob("chapter_*_review.json")):
        match = re.search(r"chapter_(\d+)_review", report.name)
        if not match:
            continue
        data = _read_json(report)
        conn.execute(
            "INSERT OR REPLACE INTO reviews (project_id, chapter, score, threshold_value, passed, action, model, fallback_reason, report_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                project_id,
                int(match.group(1)),
                data.get("score"),
                data.get("threshold"),
                1 if data.get("passed") else 0,
                data.get("suggested_action"),
                data.get("model"),
                data.get("fallback_reason"),
                str(report),
            ),
        )


def _index_revision_queue(conn: sqlite3.Connection, project_id: str, project_path: Path) -> None:
    for item in sorted((project_path / "reviews" / "revision_queue").glob("chapter_*.md")):
        match = re.search(r"chapter_(\d+)", item.name)
        if not match:
            continue
        text = item.read_text(encoding="utf-8", errors="ignore")
        reason = " ".join(line.strip("- ").strip() for line in text.splitlines() if line.strip() and not line.startswith("#"))[:300]
        conn.execute(
            "INSERT OR REPLACE INTO revision_queue (project_id, chapter, reason, source_report, status, path) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, int(match.group(1)), reason, None, "open", str(item)),
        )
