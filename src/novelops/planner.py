from __future__ import annotations

from pathlib import Path
import re

from .config import ConfigError, load_project_path, write_json
from .corpus import latest_chapter
from .schemas import ChapterIntent, ChapterPlan, SceneChain, to_dict


QUEUE_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|")


def _read_text(path: Path, limit: int = 500) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").strip()[:limit]


def _chapter_queue_card(project_path: Path, chapter: int) -> dict[str, str] | None:
    path = project_path / "outlines" / "chapter_queue.md"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = QUEUE_ROW_RE.match(line.strip())
        if not match or int(match.group(1)) != chapter:
            continue
        return {
            "title": match.group(2).strip(),
            "objective": match.group(3).strip(),
            "context": match.group(4).strip(),
            "status": match.group(5).strip(),
        }
    return None


def plan_next(project_path: Path, chapter: int) -> tuple[ChapterPlan, ChapterIntent, SceneChain]:
    try:
        cfg = load_project_path(project_path)
    except ConfigError:
        cfg = {"genre": "中文网文", "current_volume": {"number": 1}, "rubric": {"forbidden_terms": []}}
    last = latest_chapter(project_path)
    queue_card = _chapter_queue_card(project_path, chapter)
    bible = _read_text(project_path / "bible" / "00_story_bible.md")
    state = _read_text(project_path / "state" / "chapter_summary.md") or _read_text(project_path / "state" / "timeline.md")
    genre = str(cfg.get("genre") or "中文网文")
    volume = int(cfg.get("current_volume", {}).get("number") or (1 if chapter <= 50 else 2))
    title = queue_card["title"] if queue_card else f"第{chapter:03d}章候选计划"
    objective = queue_card["objective"] if queue_card else f"承接第{last:03d}章，以{genre}的核心卖点推进主线冲突，并留下下一章追读钩子。"
    context_hint = queue_card["context"] if queue_card else (state or bible or "项目 bible 与当前状态")
    hooks = [item for item in [genre, "主线推进", "章尾钩子"] if item]
    plan = ChapterPlan(
        chapter=chapter,
        title=title,
        volume=volume,
        objective=objective,
        hooks=hooks,
        required_context=["project.json", "bible", "state", "chapter_queue" if queue_card else "latest_corpus"],
    )
    intent = ChapterIntent(
        chapter=chapter,
        reader_promise=f"读者能看到本章围绕“{objective}”产生明确推进。",
        emotional_turn="从既有局面进入新的压力或选择。",
        commercial_hook=f"章尾围绕“{title}”留下未解决问题。",
        forbidden_moves=list(cfg.get("rubric", {}).get("forbidden_terms", [])) or ["跳过关键因果", "直接写成终局", "无铺垫解决核心冲突"],
    )
    chain = SceneChain(
        chapter=chapter,
        scenes=[
            {"name": "承接", "purpose": f"接住前文：{context_hint}", "conflict": "现状暴露未解决压力"},
            {"name": "推进", "purpose": objective, "conflict": "主角目标与外部阻力正面碰撞"},
            {"name": "钩子", "purpose": "制造追读", "conflict": "新的信息迫使下一章继续行动"},
        ],
    )
    target = project_path / "generation" / f"chapter_{chapter:03d}"
    write_json(target / "01_chapter_plan.json", to_dict(plan))
    write_json(target / "02_chapter_intent.json", to_dict(intent))
    write_json(target / "03_scene_chain.json", to_dict(chain))
    return plan, intent, chain
