from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...config import load_project_path
from ...llm import LLMClient
from ...schemas import to_dict
from ..state import PipelineState


def draft_node(state: PipelineState) -> dict[str, Any]:
    """章节草稿生成节点

    生成章节草稿（draft_v1）。

    输入: chapter_intent, scene_chain, concept
    输出: draft
    """
    project_path = state["project_path"]
    current_chapter = state.get("current_chapter", 1)
    chapter_intent = state.get("chapter_intent", {})
    scene_chain = state.get("scene_chain", {})
    concept = state.get("concept", {})

    if not chapter_intent or not scene_chain:
        return {"errors": ["Missing chapter_intent or scene_chain for draft generation"]}

    try:
        llm = LLMClient()

        # 尝试使用记忆层召回
        memory_context = ""
        try:
            from ...memory import recall_for_chapter, format_memory_context
            from ...schemas import ChapterPlan, ChapterIntent, SceneChain

            # 重建 plan 对象
            plan_data = {
                "chapter": current_chapter,
                "title": f"第{current_chapter}章",
                "volume": 1,
                "objective": chapter_intent.get("reader_promise", ""),
                "hooks": [],
                "required_context": [],
            }
            plan = ChapterPlan(**plan_data)
            intent = ChapterIntent(**chapter_intent)
            chain = SceneChain(**scene_chain)

            memory_dict = recall_for_chapter(project_path, current_chapter, plan, intent, chain)
            memory_context = format_memory_context(memory_dict)
        except (ImportError, Exception):
            pass

        # 如果记忆层不可用，使用项目摘要
        if not memory_context:
            memory_context = _project_summary(project_path)

        # 构建 prompt
        context = json.dumps({
            "chapter_intent": chapter_intent,
            "scene_chain": scene_chain,
            "concept": concept,
        }, ensure_ascii=False, indent=2)

        draft_prompt = f"""请根据以下计划写出完整章节初稿。

项目摘要：
{memory_context}

章节计划：
{context}

要求：
1. 中文网文风格，保留强钩子
2. 字数 1800-3200 字
3. 只输出正文，不要标题和说明
4. 章尾必须有追读钩子"""

        draft = llm.complete(
            draft_prompt,
            system="你是长篇商业小说写手，只输出章节正文。",
            stage="draft_v1",
        )

        # 写入文件
        target = project_path / "generation" / f"chapter_{current_chapter:03d}"
        target.mkdir(parents=True, exist_ok=True)
        (target / "04_draft_v1.md").write_text(draft.strip() + "\n", encoding="utf-8")

        return {"draft": draft}

    except Exception as e:
        return {"errors": [f"Failed to generate draft: {str(e)}"]}


def _project_summary(project_path: Path, limit: int = 3000) -> str:
    """读取项目配置指定的上下文文件，构建项目摘要"""
    parts: list[str] = []

    try:
        project_config = load_project_path(project_path)
        context_sources = project_config.get("planning", {}).get("context_sources", [])
    except Exception:
        context_sources = ["bible/00_story_bible.md", "state/timeline.md", "state/current_context.md"]

    if not context_sources:
        context_sources = ["bible/00_story_bible.md", "state/timeline.md", "state/current_context.md"]

    for source in context_sources:
        if source == "state":
            state_dir = project_path / "state"
            if state_dir.is_dir():
                for state_file in sorted(state_dir.glob("*.md")):
                    text = state_file.read_text(encoding="utf-8", errors="ignore").strip()
                    if text and len(text) > 50:
                        parts.append(f"## state/{state_file.name}\n{text[:limit]}")
        else:
            path = project_path / source
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="ignore").strip()
                if text and len(text) > 50:
                    parts.append(f"## {source}\n{text[:limit]}")
            elif path.is_dir():
                for file in sorted(path.glob("*.md")):
                    text = file.read_text(encoding="utf-8", errors="ignore").strip()
                    if text and len(text) > 50:
                        parts.append(f"## {source}/{file.name}\n{text[:limit]}")

    return "\n\n".join(parts) or "暂无可读项目摘要。"
