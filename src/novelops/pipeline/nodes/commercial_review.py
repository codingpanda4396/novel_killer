from __future__ import annotations

from typing import Any

from ...llm import LLMClient
from ..state import PipelineState


def commercial_review_node(state: PipelineState) -> dict[str, Any]:
    """商业化改写节点

    强化冲突、爽点、悬念。

    输入: draft
    输出: commercial_draft
    """
    draft = state.get("draft")
    current_chapter = state.get("current_chapter", 1)
    project_path = state["project_path"]

    if not draft:
        return {"errors": ["No draft available for commercial rewrite"]}

    try:
        llm = LLMClient()

        commercial_prompt = f"""请强化以下章节的冲突、爽点、悬念和章尾追读，不改变核心事实。

要求：
1. 强化开头钩子，前 200 字必须抓住读者
2. 增加冲突张力和情绪起伏
3. 强化爽点和打脸节奏
4. 章尾必须留下追读钩子
5. 保持原有剧情走向不变
6. 只输出改稿正文，不要其他说明

原文：
{draft}"""

        commercial = llm.complete(
            commercial_prompt,
            system="你是商业化改稿编辑，只输出改稿正文。",
            stage="commercial_rewrite",
        )

        # 写入文件
        target = project_path / "generation" / f"chapter_{current_chapter:03d}"
        target.mkdir(parents=True, exist_ok=True)
        (target / "05_commercial_rewrite.md").write_text(commercial.strip() + "\n", encoding="utf-8")

        return {"commercial_draft": commercial}

    except Exception as e:
        return {"errors": [f"Failed to generate commercial rewrite: {str(e)}"]}
