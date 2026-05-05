from __future__ import annotations

import json
from typing import Any

from ...config import load_project_path, write_json
from ...planner import plan_next
from ..state import PipelineState


def chapter_plan_node(state: PipelineState) -> dict[str, Any]:
    """章节规划节点

    基于大纲生成章节队列和当前章节计划。

    输入: volume_outlines, current_chapter
    输出: chapter_queue, chapter_intent, scene_chain
    """
    project_path = state["project_path"]
    current_chapter = state.get("current_chapter", 1)

    try:
        # 复用现有 planner 逻辑
        plan, intent, chain = plan_next(project_path, current_chapter)

        # 转换为字典格式
        from ...schemas import to_dict

        chapter_intent = to_dict(intent)
        scene_chain = to_dict(chain)

        return {
            "chapter_intent": chapter_intent,
            "scene_chain": scene_chain,
            "current_chapter": current_chapter,
        }

    except Exception as e:
        return {"errors": [f"Failed to generate chapter plan: {str(e)}"]}
