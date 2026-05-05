from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import load_project_path, write_json
from .continuity import update_continuity_after_chapter
from .llm import LLMClient, load_model_config
from .planner import plan_next
from .reviewer import review_text
from .schemas import DraftArtifact, to_dict


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
    """读取项目配置指定的上下文文件，构建项目摘要"""
    parts: list[str] = []
    
    # 尝试读取项目配置
    try:
        project_config = load_project_path(project_path)
        context_sources = project_config.get("planning", {}).get("context_sources", [])
    except Exception:
        # 如果读取配置失败，使用默认列表
        context_sources = ["bible/00_story_bible.md", "state/timeline.md", "state/current_context.md"]
    
    # 如果配置为空，使用默认列表
    if not context_sources:
        context_sources = ["bible/00_story_bible.md", "state/timeline.md", "state/current_context.md"]
    
    for source in context_sources:
        if source == "state":
            # 如果是 state 目录，读取所有 state 文件
            state_dir = project_path / "state"
            if state_dir.is_dir():
                for state_file in sorted(state_dir.glob("*.md")):
                    text = state_file.read_text(encoding="utf-8", errors="ignore").strip()
                    if text and len(text) > 50:  # 忽略空文件或占位文件
                        parts.append(f"## state/{state_file.name}\n{text[:limit]}")
        else:
            # 读取单个文件
            path = project_path / source
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="ignore").strip()
                if text and len(text) > 50:  # 忽略空文件或占位文件
                    parts.append(f"## {source}\n{text[:limit]}")
            elif path.is_dir():
                # 如果是目录，读取目录下所有 .md 文件
                for file in sorted(path.glob("*.md")):
                    text = file.read_text(encoding="utf-8", errors="ignore").strip()
                    if text and len(text) > 50:
                        parts.append(f"## {source}/{file.name}\n{text[:limit]}")
    
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


def _generate_live(project_path: Path, chapter: int, threshold: float, llm_client: LLMClient) -> DraftArtifact:
    plan, intent, chain = plan_next(project_path, chapter)
    target = project_path / "generation" / f"chapter_{chapter:03d}"
    context = _prompt_context(plan, intent, chain)

    # 尝试使用记忆层召回
    memory_context = ""
    try:
        from .memory import recall_for_chapter, format_memory_context
        memory_dict = recall_for_chapter(project_path, chapter, plan, intent, chain)
        memory_context = format_memory_context(memory_dict)
    except (ImportError, Exception) as e:
        # Chroma 不可用时降级到原有 project_summary
        pass

    # 使用 memory_context 或降级到 project_summary
    project_summary = memory_context if memory_context else _project_summary(project_path)

    intent_json = llm_client.complete_json(
        "基于固定章节计划、项目 bible/state 摘要，细化本章读者承诺、情绪转折、商业钩子和禁写项。"
        "必须返回 JSON 对象。\n\n"
        f"项目摘要：\n{project_summary}\n\n章节计划：\n{context}",
        system="你是长篇商业小说章节意图规划助手。只返回 JSON。",
        stage="chapter_intent",
    )
    write_json(target / "02_chapter_intent.json", intent_json)

    scene_json = llm_client.complete_json(
        "基于章节计划、章节意图和项目摘要，输出 3-6 个场景的 scene_chain JSON。"
        "每个场景要包含 name、purpose、conflict、turn、exit_hook。\n\n"
        + json.dumps({"project_summary": project_summary, "plan": to_dict(plan), "intent": intent_json}, ensure_ascii=False),
        system="你是长篇商业小说分场设计助手。只返回 JSON。",
        stage="scene_chain",
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

    result = review_text(chapter, final_text, threshold, llm_client=llm_client, project_path=project_path, attempt=0)
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
        second = review_text(chapter, revised_text, threshold, llm_client=llm_client, project_path=project_path, attempt=attempt)
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
    else:
        # 如果通过审稿，更新连续性文件
        try:
            update_continuity_after_chapter(project_path, chapter, current_text, llm_client)
        except Exception as e:
            # 连续性更新失败不应阻止生成流程
            print(f"Warning: Failed to update continuity: {e}")

        # 增量更新记忆库
        try:
            from .memory import get_store
            from .memory.indexer import index_chapter
            store = get_store()
            index_chapter(project_path, chapter, current_text, store)
        except Exception as e:
            # 记忆库更新失败不应阻止生成流程
            pass

    return DraftArtifact(
        chapter=chapter,
        stage=final_stage,
        path=str(final_path),
        word_count=len(final_path.read_text(encoding="utf-8")),
        llm_used=bool(getattr(llm_client, "live_call_count", 0)),
    )

def generate(
    project_path: Path,
    chapter: int,
    threshold: float,
    llm_client: LLMClient | None = None,
) -> DraftArtifact:
    return _generate_live(project_path, chapter, threshold, llm_client or LLMClient())
