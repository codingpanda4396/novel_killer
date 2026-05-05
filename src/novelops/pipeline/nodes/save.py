from __future__ import annotations

from pathlib import Path
from typing import Any

from ...continuity import update_continuity_after_chapter
from ...llm import LLMClient
from ..state import PipelineState


def save_node(state: PipelineState) -> dict[str, Any]:
    """保存节点

    保存最终章节，更新记忆库和连续性文件。

    输入: final_draft, review_result
    输出: 完成标志
    """
    final_draft = state.get("final_draft")
    review_result = state.get("review_result", {})
    current_chapter = state.get("current_chapter", 1)
    total_chapters = state.get("total_chapters", 30)
    project_path = state["project_path"]
    completed_nodes = state.get("completed_nodes", [])

    if not final_draft:
        return {"errors": ["No final draft available to save"]}

    try:
        # 更新连续性文件
        try:
            llm = LLMClient()
            update_continuity_after_chapter(project_path, current_chapter, final_draft, llm)
        except Exception as e:
            # 连续性更新失败不应阻止保存
            pass

        # 增量更新记忆库
        try:
            from ...memory import get_store
            from ...memory.indexer import index_chapter
            store = get_store()
            index_chapter(project_path, current_chapter, final_draft, store)
        except Exception:
            # 记忆库更新失败不应阻止保存
            pass

        # 更新项目配置中的章节进度
        try:
            from ...config import load_project_path, write_json
            cfg = load_project_path(project_path)
            if "current_volume" in cfg:
                cfg["current_volume"]["last_completed_chapter"] = current_chapter
                cfg["current_volume"]["next_chapter"] = current_chapter + 1
            write_json(project_path / "project.json", cfg)
        except Exception:
            pass

        # 判断是否还有下一章
        has_next = current_chapter < total_chapters
        next_chapter = current_chapter + 1 if has_next else current_chapter

        # 更新完成节点列表
        new_completed = completed_nodes + [f"chapter_{current_chapter:03d}"]

        return {
            "current_chapter": next_chapter,
            "completed_nodes": new_completed,
            # 如果还有下一章，重置 retry_count
            "retry_count": 0 if has_next else state.get("retry_count", 0),
        }

    except Exception as e:
        return {"errors": [f"Failed to save chapter: {str(e)}"]}
