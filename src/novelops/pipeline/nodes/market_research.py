from __future__ import annotations

import json
from typing import Any

from ..state import PipelineState


def market_research_node(state: PipelineState) -> dict[str, Any]:
    """市场调研节点

    从 NovelRadar 获取市场调研数据，或接受手动输入。

    输入: topic_id 或手动输入的市场数据
    输出: market_data
    """
    topic_id = state.get("topic_id")
    project_path = state["project_path"]

    if topic_id:
        # 从 NovelRadar 获取数据
        try:
            from ...radar.storage import RadarStorage

            storage = RadarStorage()
            # 尝试获取 topic opportunity
            conn = storage.connect()
            try:
                row = conn.execute(
                    "SELECT * FROM topic_opportunities WHERE topic_id = ?",
                    (topic_id,)
                ).fetchone()

                if row:
                    market_data = {
                        "topic_id": row["topic_id"],
                        "topic_name": row["topic_name"],
                        "target_platform": row["target_platform"],
                        "target_reader": row["target_reader"],
                        "core_tags": json.loads(row["core_tags"]) if row["core_tags"] else [],
                        "evidence_titles": json.loads(row["evidence_titles"]) if row["evidence_titles"] else [],
                        "hot_score": row["hot_score"],
                        "competition_score": row["competition_score"],
                        "platform_fit_score": row["platform_fit_score"],
                        "writing_difficulty_score": row["writing_difficulty_score"],
                        "final_score": row["final_score"],
                        "opening_hook": row["opening_hook"],
                        "suggested_story_seed": row["suggested_story_seed"],
                        "risks": json.loads(row["risks"]) if row["risks"] else [],
                    }
                    return {"market_data": market_data}
            finally:
                conn.close()

            # 如果没找到 topic，尝试从 analyzed_signals 获取
            conn = storage.connect()
            try:
                row = conn.execute(
                    "SELECT * FROM analyzed_signals WHERE signal_id = ?",
                    (topic_id,)
                ).fetchone()

                if row:
                    market_data = {
                        "signal_id": row["signal_id"],
                        "title": row["title"],
                        "source": row["source"],
                        "platform": row["platform"],
                        "category": row["category"],
                        "tags": json.loads(row["tags"]) if row["tags"] else [],
                        "description": row["description"],
                        "hot_score": row["hot_score"],
                        "extracted_genre": row["extracted_genre"],
                        "protagonist_template": row["protagonist_template"],
                        "golden_finger": row["golden_finger"],
                        "core_hook": row["core_hook"],
                        "reader_desire": row["reader_desire"],
                        "llm_genre": row["llm_genre"],
                        "llm_core_desire": row["llm_core_desire"],
                        "llm_hook": row["llm_hook"],
                        "llm_golden_finger": row["llm_golden_finger"],
                    }
                    return {"market_data": market_data}
            finally:
                conn.close()

        except Exception as e:
            return {"errors": [f"Failed to fetch market data: {str(e)}"]}

    # 如果没有 topic_id 或获取失败，返回空数据让后续节点处理
    return {"market_data": None}
