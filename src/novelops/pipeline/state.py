from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    """流水线状态数据结构"""

    # 项目基本信息
    project_id: str
    project_path: Path
    mode: str  # "auto" | "interactive"

    # 市场调研阶段
    topic_id: str | None
    market_data: dict[str, Any] | None

    # 概念设计阶段
    concept: dict[str, Any] | None
    bible_created: bool

    # 大纲阶段
    outline: dict[str, Any] | None
    volume_outlines: list[dict[str, Any]] | None

    # 章节规划阶段
    chapter_queue: list[dict[str, Any]] | None
    current_chapter: int
    total_chapters: int

    # 章节生成阶段
    chapter_intent: dict[str, Any] | None
    scene_chain: dict[str, Any] | None
    draft: str | None
    commercial_draft: str | None
    final_draft: str | None

    # 审稿阶段
    review_result: dict[str, Any] | None
    continuity_check: dict[str, Any] | None

    # 控制流
    needs_approval: bool
    approved: bool
    retry_count: int
    max_retry_attempts: int
    errors: list[str]

    # 当前执行阶段
    current_node: str | None
    completed_nodes: list[str]


def create_initial_state(
    project_id: str,
    project_path: Path,
    mode: str = "interactive",
    topic_id: str | None = None,
    max_retry_attempts: int = 2,
) -> PipelineState:
    """创建初始流水线状态"""
    return PipelineState(
        project_id=project_id,
        project_path=project_path,
        mode=mode,
        topic_id=topic_id,
        market_data=None,
        concept=None,
        bible_created=False,
        outline=None,
        volume_outlines=None,
        chapter_queue=None,
        current_chapter=1,
        total_chapters=30,
        chapter_intent=None,
        scene_chain=None,
        draft=None,
        commercial_draft=None,
        final_draft=None,
        review_result=None,
        continuity_check=None,
        needs_approval=False,
        approved=False,
        retry_count=0,
        max_retry_attempts=max_retry_attempts,
        errors=[],
        current_node=None,
        completed_nodes=[],
    )
