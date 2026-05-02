from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import ConfigError, write_json
from .paths import project_dir


STANDARD_DIRS = [
    "bible",
    "outlines",
    "state",
    "corpus",
    "generation",
    "reviews",
    "publish",
    "intelligence/raw/manual_notes",
    "intelligence/processed",
    "intelligence/reports",
]


def default_project_config(project_id: str, name: str, genre: str, target_platform: str = "中文网文连载平台") -> dict[str, Any]:
    return {
        "id": project_id,
        "name": name,
        "genre": genre,
        "target_platform": target_platform,
        "language": "zh-CN",
        "chapter_length": {"min": 1800, "target": 2500, "max": 3200},
        "review_thresholds": {"chapter": 80, "publish": 80},
        "current_volume": {"number": 1, "status": "planning", "last_completed_chapter": 0, "next_chapter": 1},
        "planning": {
            "default_strategy": "queue_first_then_bible_state",
            "context_sources": ["outlines/chapter_queue.md", "bible/00_story_bible.md", "state"],
            "require_chapter_queue": False,
        },
        "rubric": {
            "hook_terms": [],
            "forbidden_terms": [],
            "weights": {"word_count": 14, "paragraph_density": 8, "dialogue_density": 8, "hook_terms": 10},
        },
        "directories": {
            "bible": "bible",
            "outlines": "outlines",
            "corpus": "corpus",
            "state": "state",
            "generation": "generation",
            "reviews": "reviews",
            "intelligence": "intelligence",
            "publish": "publish",
        },
    }


def init_project(project_id: str, name: str, genre: str, target_platform: str = "中文网文连载平台") -> Path:
    if "/" in project_id or "\\" in project_id or not project_id.strip():
        raise ConfigError("project_id must be a simple directory name")
    path = project_dir(project_id)
    if path.exists():
        raise ConfigError(f"Project already exists: {path}")
    for item in STANDARD_DIRS:
        (path / item).mkdir(parents=True, exist_ok=True)
    (path / "corpus" / "volume_01").mkdir(parents=True, exist_ok=True)
    (path / "publish" / "ready").mkdir(parents=True, exist_ok=True)
    write_json(path / "project.json", default_project_config(project_id, name, genre, target_platform))
    _write_once(path / "bible" / "00_story_bible.md", f"# {name}\n\n- 题材：{genre}\n- 核心卖点：待补充\n- 主角：待补充\n")
    _write_once(path / "outlines" / "chapter_queue.md", "# 章节队列\n\n| 章号 | 工作标题 | 核心任务 | 必须承接 | 状态 |\n| --- | --- | --- | --- | --- |\n")
    _write_once(path / "state" / "timeline.md", "# 时间线\n\n待补充。\n")
    _write_once(path / "state" / "chapter_summary.md", "# 章节摘要\n\n待补充。\n")
    return path


def _write_once(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")
