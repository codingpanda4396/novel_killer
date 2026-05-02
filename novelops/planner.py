from __future__ import annotations

from pathlib import Path

from .config import write_json
from .corpus import latest_chapter
from .schemas import ChapterIntent, ChapterPlan, SceneChain, to_dict


def plan_next(project_path: Path, chapter: int) -> tuple[ChapterPlan, ChapterIntent, SceneChain]:
    last = latest_chapter(project_path)
    title = f"第{chapter:03d}章候选计划"
    plan = ChapterPlan(
        chapter=chapter,
        title=title,
        volume=2 if chapter > 50 else 1,
        objective=f"承接第{last:03d}章后的新卷开局，提出新的外部压力和余额规则疑问。",
        hooks=["新能力者", "规则代价", "白塔残留线索"],
        required_context=["bible", "state", "volume_01_corpus"],
    )
    intent = ChapterIntent(
        chapter=chapter,
        reader_promise="主角没有退回日常，而是在第一卷后果中被迫做出新选择。",
        emotional_turn="从短暂平静转向新的不安。",
        commercial_hook="章尾抛出一个无法用旧规则解释的余额异常。",
        forbidden_moves=["自动复活已收束反派", "跳过代价", "直接写成终局"],
    )
    chain = SceneChain(
        chapter=chapter,
        scenes=[
            {"name": "aftershock", "purpose": "展示第一卷后果", "conflict": "平静被打断"},
            {"name": "new_case", "purpose": "引入第二卷问题", "conflict": "旧规则无法解释"},
            {"name": "hook", "purpose": "制造追读", "conflict": "主角必须介入"},
        ],
    )
    target = project_path / "generation" / f"chapter_{chapter:03d}"
    write_json(target / "01_chapter_plan.json", to_dict(plan))
    write_json(target / "02_chapter_intent.json", to_dict(intent))
    write_json(target / "03_scene_chain.json", to_dict(chain))
    return plan, intent, chain

