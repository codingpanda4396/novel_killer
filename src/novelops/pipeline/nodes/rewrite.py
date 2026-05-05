from __future__ import annotations

from typing import Any

from ...llm import LLMClient
from ...reviewer import review_text
from ..state import PipelineState


def rewrite_node(state: PipelineState) -> dict[str, Any]:
    """审稿门禁节点

    判断是否需要重写。

    输入: final_draft
    输出: review_result, 决定是否进入 save 或重试
    """
    final_draft = state.get("final_draft")
    current_chapter = state.get("current_chapter", 1)
    project_path = state["project_path"]
    retry_count = state.get("retry_count", 0)
    max_retry_attempts = state.get("max_retry_attempts", 2)

    if not final_draft:
        return {"errors": ["No final draft available for review"]}

    try:
        llm = LLMClient()

        # 读取项目配置获取阈值
        from ...config import load_project_path, threshold
        try:
            cfg = load_project_path(project_path)
            review_threshold = threshold(cfg)
        except Exception:
            review_threshold = 80.0

        # 执行审稿
        result = review_text(
            chapter=current_chapter,
            text=final_draft,
            threshold=review_threshold,
            llm_client=llm,
            project_path=project_path,
            attempt=retry_count,
        )

        # 转换为字典
        from ...schemas import to_dict
        review_result = to_dict(result)

        # 写入审稿结果
        target = project_path / "generation" / f"chapter_{current_chapter:03d}"
        target.mkdir(parents=True, exist_ok=True)
        from ...config import write_json
        write_json(target / "08_review_gate.json", review_result)

        # 判断是否通过
        if result.passed and result.suggested_action == "accept":
            return {
                "review_result": review_result,
                "retry_count": retry_count,
            }
        else:
            # 未通过，检查是否可以重试
            if retry_count < max_retry_attempts:
                return {
                    "review_result": review_result,
                    "retry_count": retry_count + 1,
                    "errors": [f"Review failed (attempt {retry_count + 1}): {', '.join(result.issues[:3])}"],
                }
            else:
                # 超过最大重试次数
                return {
                    "review_result": review_result,
                    "retry_count": retry_count,
                    "errors": [f"Review failed after {max_retry_attempts} attempts: {', '.join(result.issues[:3])}"],
                }

    except Exception as e:
        return {"errors": [f"Failed to perform review: {str(e)}"]}
