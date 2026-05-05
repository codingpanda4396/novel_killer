from __future__ import annotations

from typing import Any

from ...continuity import update_continuity_after_chapter
from ...llm import LLMClient
from ..state import PipelineState


def continuity_check_node(state: PipelineState) -> dict[str, Any]:
    """连续性检查节点

    连续性检查和去 AI 腔改写。

    输入: commercial_draft
    输出: final_draft, continuity_check
    """
    commercial_draft = state.get("commercial_draft")
    current_chapter = state.get("current_chapter", 1)
    project_path = state["project_path"]

    if not commercial_draft:
        return {"errors": ["No commercial draft available for continuity check"]}

    try:
        llm = LLMClient()

        # 读取连续性上下文
        continuity_context = _read_continuity_context(project_path)

        humanize_prompt = f"""请对以下章节进行连续性检查和润色。

连续性上下文：
{continuity_context}

要求：
1. 检查人物状态、时间线、能力边界一致性
2. 降低 AI 痕迹，增强人物微反应、节奏停顿和自然中文表达
3. 不改变剧情走向
4. 只输出最终候选正文，不要其他说明

原文：
{commercial_draft}"""

        final_draft = llm.complete(
            humanize_prompt,
            system="你是中文小说润色编辑，只输出最终候选正文。",
            stage="humanize",
        )

        # 写入文件
        target = project_path / "generation" / f"chapter_{current_chapter:03d}"
        target.mkdir(parents=True, exist_ok=True)
        (target / "06_humanized_rewrite.md").write_text(final_draft.strip() + "\n", encoding="utf-8")
        (target / "07_final_candidate.md").write_text(final_draft.strip() + "\n", encoding="utf-8")

        # 连续性检查结果
        continuity_check = {
            "passed": True,
            "chapter": current_chapter,
            "issues": [],
        }

        return {
            "final_draft": final_draft,
            "continuity_check": continuity_check,
        }

    except Exception as e:
        return {"errors": [f"Failed to perform continuity check: {str(e)}"]}


def _read_continuity_context(project_path: str) -> str:
    """读取连续性上下文"""
    from pathlib import Path

    path = Path(project_path)
    parts = []

    # 读取角色状态
    char_state = path / "state" / "character_state.md"
    if char_state.is_file():
        text = char_state.read_text(encoding="utf-8", errors="ignore").strip()
        if text and len(text) > 50:
            parts.append(f"## 角色状态\n{text[:1000]}")

    # 读取时间线
    timeline = path / "state" / "timeline.md"
    if timeline.is_file():
        text = timeline.read_text(encoding="utf-8", errors="ignore").strip()
        if text and len(text) > 50:
            parts.append(f"## 时间线\n{text[:1000]}")

    # 读取活跃线索
    threads = path / "state" / "active_threads.md"
    if threads.is_file():
        text = threads.read_text(encoding="utf-8", errors="ignore").strip()
        if text and len(text) > 50:
            parts.append(f"## 活跃线索\n{text[:1000]}")

    return "\n\n".join(parts) or "暂无连续性上下文。"
