from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import write_json
from .llm import LLMClient, load_model_config
from .planner import plan_next
from .reviewer import review_text
from .schemas import DraftArtifact, to_dict


def _mock_draft(chapter: int) -> str:
    return f"""# 第{chapter}章 新的余额异常

陈默以为自己终于能把第一卷留下的伤口压进日常里。

可那天傍晚，他在医院走廊里看见了一个不该出现的数字。

【人生余额：--:--:--】

不是归零，也不是倒计时，而是一段被人为擦掉的空白。

林见鹿站在他身侧，声音很低：“这不是天平会留下的格式。”

陈默没有立刻回答。他想起白塔崩塌前最后一瞬，那些从规则缝隙里逃出去的暗纹。旧秩序被打碎，不代表新的秩序不会长出来。

走廊尽头，一个少年回头看了他一眼。

少年头顶没有寿命，没有财运，没有遗憾值，只有一行灰色提示。

【观测者已被观测。】
"""


def _prompt_context(plan: Any, intent: Any, chain: Any) -> str:
    return json.dumps(
        {
            "plan": to_dict(plan),
            "intent": to_dict(intent),
            "scene_chain": to_dict(chain),
        },
        ensure_ascii=False,
        indent=2,
    )


def _project_summary(project_path: Path, limit: int = 3000) -> str:
    parts: list[str] = []
    for name in ["bible/00_story_bible.md", "state/timeline.md", "state/current_context.md"]:
        path = project_path / name
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
            if text:
                parts.append(f"## {name}\n{text[:limit]}")
    return "\n\n".join(parts) or "暂无可读项目摘要。"


def _write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return content.strip() + "\n"


def _max_revision_attempts() -> int:
    config = load_model_config()
    try:
        return min(2, max(0, int(config.get("max_revision_attempts", 2))))
    except (TypeError, ValueError):
        return 2


def _json_or_mock(llm_client: LLMClient, prompt: str, system: str, stage: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return llm_client.complete_json(prompt, system=system, stage=stage)
    except Exception as exc:
        return {
            **fallback,
            "mock": True,
            "fallback_reason": str(exc),
        }


def _generate_live(project_path: Path, chapter: int, threshold: float, llm_client: LLMClient) -> DraftArtifact:
    plan, intent, chain = plan_next(project_path, chapter)
    target = project_path / "generation" / f"chapter_{chapter:03d}"
    context = _prompt_context(plan, intent, chain)
    project_summary = _project_summary(project_path)

    intent_json = _json_or_mock(
        llm_client,
        "基于固定章节计划、项目 bible/state 摘要，细化本章读者承诺、情绪转折、商业钩子和禁写项。"
        "必须返回 JSON 对象。\n\n"
        f"项目摘要：\n{project_summary}\n\n章节计划：\n{context}",
        system="你是长篇商业小说章节意图规划助手。只返回 JSON。",
        stage="chapter_intent",
        fallback=to_dict(intent),
    )
    write_json(target / "02_chapter_intent.json", intent_json)

    scene_json = _json_or_mock(
        llm_client,
        "基于章节计划、章节意图和项目摘要，输出 3-6 个场景的 scene_chain JSON。"
        "每个场景要包含 name、purpose、conflict、turn、exit_hook。\n\n"
        + json.dumps({"project_summary": project_summary, "plan": to_dict(plan), "intent": intent_json}, ensure_ascii=False),
        system="你是长篇商业小说分场设计助手。只返回 JSON。",
        stage="scene_chain",
        fallback=to_dict(chain),
    )
    write_json(target / "03_scene_chain.json", scene_json)

    draft = llm_client.complete(
        "请根据以下计划写出完整章节初稿，中文网文风格，保留强钩子。只输出正文。\n\n"
        + json.dumps(
            {"project_summary": project_summary, "plan": to_dict(plan), "intent": intent_json, "scene_chain": scene_json},
            ensure_ascii=False,
            indent=2,
        ),
        system="你是长篇商业小说写手，只输出章节正文。",
        stage="draft_v1",
    )
    _write_text(target / "04_draft_v1.md", draft)

    commercial = llm_client.complete(
        "请强化以下章节的冲突、爽点、悬念和章尾追读，不改变核心事实。\n\n" + draft,
        system="你是商业化改稿编辑，只输出改稿正文。",
        stage="commercial_rewrite",
    )
    _write_text(target / "05_commercial_rewrite.md", commercial)

    humanized = llm_client.complete(
        "请降低机械痕迹，增强人物微反应、节奏停顿和自然中文表达，不改变剧情。\n\n" + commercial,
        system="你是中文小说润色编辑，只输出最终候选正文。",
        stage="humanize",
    )
    final_text = _write_text(target / "06_humanized_rewrite.md", humanized)
    _write_text(target / "07_final_candidate.md", final_text)

    result = review_text(chapter, final_text, threshold, llm_client=llm_client, no_llm=False, attempt=0)
    write_json(target / "08_review_gate.json", to_dict(result))

    final_path = target / "07_final_candidate.md"
    final_stage = "final_candidate"
    max_attempts = _max_revision_attempts()
    current_text = final_text
    for attempt in range(1, max_attempts + 1):
        if result.passed and result.suggested_action == "accept":
            break
        revision = llm_client.complete(
            "请按审稿意见修订章节。只输出修订后的完整章节正文。\n\n"
            + json.dumps(to_dict(result), ensure_ascii=False, indent=2)
            + "\n\n原文：\n"
            + current_text,
            system="你是长篇商业小说修订编辑。",
            stage="revision",
        )
        revision_name = "09_revision_v1.md" if attempt == 1 else "11_revision_v2.md"
        review_name = "10_revision_v1_review_gate.json" if attempt == 1 else "12_revision_v2_review_gate.json"
        revised_text = _write_text(target / revision_name, revision)
        second = review_text(chapter, revised_text, threshold, llm_client=llm_client, no_llm=False, attempt=attempt)
        write_json(target / review_name, to_dict(second))
        final_path = target / revision_name
        final_stage = f"revision_v{attempt}"
        current_text = revised_text
        result = second

    if not result.passed:
        queue = project_path / "reviews" / "revision_queue" / f"chapter_{chapter:03d}.md"
        queue.parent.mkdir(parents=True, exist_ok=True)
        queue.write_text(
            f"# Chapter {chapter:03d}\n\nGenerated candidate failed gate: {result.score}/{threshold}\n\n"
            + "\n".join(f"- {item}" for item in result.issues + result.revision_tasks)
            + "\n",
            encoding="utf-8",
        )

    return DraftArtifact(
        chapter=chapter,
        stage=final_stage,
        path=str(final_path),
        word_count=len(final_path.read_text(encoding="utf-8")),
        llm_used=bool(getattr(llm_client, "live_call_count", 0)),
    )


def _generate_mock(project_path: Path, chapter: int, threshold: float) -> DraftArtifact:
    plan_next(project_path, chapter)
    target = project_path / "generation" / f"chapter_{chapter:03d}"
    draft = _mock_draft(chapter)
    stages = [
        ("04_draft_v1.md", draft),
        ("05_commercial_rewrite.md", draft + "\n\n章尾的灰色提示，让陈默第一次意识到：规则也会反过来看他。\n"),
        ("06_humanized_rewrite.md", draft + "\n\n他没有喊林见鹿的名字，只把手伸过去，确认她还在身边。\n"),
        ("07_final_candidate.md", draft),
    ]
    for name, content in stages:
        _write_text(target / name, content)
    result = review_text(chapter, draft, threshold, no_llm=True)
    write_json(target / "08_review_gate.json", to_dict(result))
    final_path = target / "07_final_candidate.md"
    final_stage = "final_candidate"
    current_text = draft
    for attempt in range(1, _max_revision_attempts() + 1):
        if result.passed and result.suggested_action == "accept":
            break
        revised = current_text + f"\n\n第{attempt}轮修订：陈默把异常余额和新的规则代价直接联系起来，章尾压力更明确。\n"
        revision_name = "09_revision_v1.md" if attempt == 1 else "11_revision_v2.md"
        review_name = "10_revision_v1_review_gate.json" if attempt == 1 else "12_revision_v2_review_gate.json"
        current_text = _write_text(target / revision_name, revised)
        result = review_text(chapter, current_text, threshold, no_llm=True, attempt=attempt)
        write_json(target / review_name, to_dict(result))
        final_path = target / revision_name
        final_stage = f"revision_v{attempt}"
    if not result.passed:
        queue = project_path / "reviews" / "revision_queue" / f"chapter_{chapter:03d}.md"
        queue.parent.mkdir(parents=True, exist_ok=True)
        queue.write_text(f"# Chapter {chapter:03d}\n\nGenerated candidate failed gate: {result.score}/{threshold}\n", encoding="utf-8")
    return DraftArtifact(
        chapter=chapter,
        stage=final_stage,
        path=str(final_path),
        word_count=len(final_path.read_text(encoding="utf-8")),
        llm_used=False,
    )


def generate(
    project_path: Path,
    chapter: int,
    threshold: float,
    no_llm: bool = False,
    llm_client: LLMClient | None = None,
) -> DraftArtifact:
    if no_llm:
        return _generate_mock(project_path, chapter, threshold)
    return _generate_live(project_path, chapter, threshold, llm_client or LLMClient())
