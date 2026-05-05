from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, StateGraph

from .config import get_approval_points, is_auto_mode, load_pipeline_config
from .nodes import (
    chapter_plan_node,
    commercial_review_node,
    concept_design_node,
    continuity_check_node,
    draft_node,
    market_research_node,
    outline_node,
    rewrite_node,
    save_node,
)
from .state import PipelineState


def _should_continue_to_market_research(state: PipelineState) -> str:
    """判断是否继续到市场调研"""
    return "market_research"


def _should_continue_to_concept_design(state: PipelineState) -> str:
    """判断是否继续到概念设计"""
    if state.get("errors"):
        return "error"
    return "concept_design"


def _should_continue_to_outline(state: PipelineState) -> str:
    """判断是否继续到大纲生成"""
    if state.get("errors"):
        return "error"
    config = load_pipeline_config(state.get("project_path"))
    approval_points = get_approval_points(config)

    if "concept_design" in approval_points and state.get("mode") == "interactive":
        if not state.get("approved"):
            return "wait_approval"
    return "outline"


def _should_continue_to_chapter_plan(state: PipelineState) -> str:
    """判断是否继续到章节规划"""
    if state.get("errors"):
        return "error"
    config = load_pipeline_config(state.get("project_path"))
    approval_points = get_approval_points(config)

    if "outline" in approval_points and state.get("mode") == "interactive":
        if not state.get("approved"):
            return "wait_approval"
    return "chapter_plan"


def _should_continue_to_draft(state: PipelineState) -> str:
    """判断是否继续到草稿生成"""
    if state.get("errors"):
        return "error"
    config = load_pipeline_config(state.get("project_path"))
    approval_points = get_approval_points(config)

    if "chapter_plan" in approval_points and state.get("mode") == "interactive":
        if not state.get("approved"):
            return "wait_approval"
    return "draft"


def _should_continue_after_rewrite(state: PipelineState) -> str:
    """审稿后判断是否通过"""
    if state.get("errors"):
        # 检查是否是审稿失败的错误
        errors = state.get("errors", [])
        review_failed = any("Review failed" in e for e in errors)

        if review_failed:
            retry_count = state.get("retry_count", 0)
            max_retry = state.get("max_retry_attempts", 2)

            if retry_count <= max_retry:
                return "draft"  # 重试
            else:
                return "save"  # 超过最大重试次数，强制保存
        return "error"

    review_result = state.get("review_result", {})
    if review_result.get("passed") and review_result.get("suggested_action") == "accept":
        return "save"

    # 未通过但没有错误，也进入保存（可能是边界情况）
    return "save"


def _should_continue_after_save(state: PipelineState) -> str:
    """保存后判断是否继续下一章"""
    if state.get("errors"):
        return "error"

    current_chapter = state.get("current_chapter", 1)
    total_chapters = state.get("total_chapters", 30)

    if current_chapter <= total_chapters:
        return "chapter_plan"  # 继续下一章

    return "end"


def _handle_error(state: PipelineState) -> dict[str, Any]:
    """处理错误状态"""
    # 不做任何修改，直接返回状态
    return {}


def _wait_approval(state: PipelineState) -> dict[str, Any]:
    """等待人工确认"""
    return {"needs_approval": True, "approved": False}


def build_pipeline_graph() -> StateGraph:
    """构建流水线状态图"""

    # 创建状态图
    graph = StateGraph(PipelineState)

    # 添加节点
    graph.add_node("market_research", market_research_node)
    graph.add_node("concept_design", concept_design_node)
    graph.add_node("outline", outline_node)
    graph.add_node("chapter_plan", chapter_plan_node)
    graph.add_node("draft", draft_node)
    graph.add_node("commercial_review", commercial_review_node)
    graph.add_node("continuity_check", continuity_check_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("save", save_node)
    graph.add_node("error", _handle_error)
    graph.add_node("wait_approval", _wait_approval)

    # 设置入口点
    graph.set_entry_point("market_research")

    # 添加边
    graph.add_conditional_edges(
        "market_research",
        _should_continue_to_concept_design,
        {
            "concept_design": "concept_design",
            "error": "error",
        },
    )

    graph.add_conditional_edges(
        "concept_design",
        _should_continue_to_outline,
        {
            "outline": "outline",
            "wait_approval": "wait_approval",
            "error": "error",
        },
    )

    graph.add_conditional_edges(
        "outline",
        _should_continue_to_chapter_plan,
        {
            "chapter_plan": "chapter_plan",
            "wait_approval": "wait_approval",
            "error": "error",
        },
    )

    graph.add_conditional_edges(
        "chapter_plan",
        _should_continue_to_draft,
        {
            "draft": "draft",
            "wait_approval": "wait_approval",
            "error": "error",
        },
    )

    # 草稿生成后的线性流程
    graph.add_edge("draft", "commercial_review")
    graph.add_edge("commercial_review", "continuity_check")
    graph.add_edge("continuity_check", "rewrite")

    # 审稿后的条件路由
    graph.add_conditional_edges(
        "rewrite",
        _should_continue_after_rewrite,
        {
            "draft": "draft",  # 重试
            "save": "save",
            "error": "error",
        },
    )

    # 保存后的条件路由
    graph.add_conditional_edges(
        "save",
        _should_continue_after_save,
        {
            "chapter_plan": "chapter_plan",  # 继续下一章
            "end": END,
            "error": "error",
        },
    )

    # 错误和等待确认状态直接结束
    graph.add_edge("error", END)
    graph.add_edge("wait_approval", END)

    return graph


def compile_pipeline():
    """编译流水线"""
    graph = build_pipeline_graph()
    return graph.compile()
