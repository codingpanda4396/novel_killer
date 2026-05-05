"""语义召回模块 - 为章节生成召回相关记忆"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .store import MemoryStore


def _safe_join(docs: list[str] | None, separator: str = "\n---\n") -> str:
    """安全拼接文档列表"""
    if not docs:
        return ""
    return separator.join(docs)


def recall_for_chapter(
    project_path: Path,
    chapter: int,
    plan: Any,
    intent: Any,
    chain: Any,
    store: MemoryStore
) -> dict[str, str]:
    """返回分组后的生成上下文"""
    project_id = project_path.name
    context = {}

    # 1. 固定召回：主角设定（5 条）
    try:
        protagonist = store.query(
            query_texts=["主角设定 人物性格 能力 背景"],
            n_results=5,
            where={"$and": [{"project_id": project_id}, {"doc_type": "protagonist_setting"}]}
        )
        context["protagonist_setting"] = _safe_join(protagonist.get("documents", [[]])[0])
    except Exception:
        context["protagonist_setting"] = ""

    # 2. 固定召回：前 3 章（3 条）
    try:
        first_chapters = store.query(
            query_texts=["故事开头 开篇 第一章"],
            n_results=3,
            where={"$and": [{"project_id": project_id}, {"doc_type": "first_chapters"}]}
        )
        context["first_chapters"] = _safe_join(first_chapters.get("documents", [[]])[0])
    except Exception:
        context["first_chapters"] = ""

    # 3. 固定召回：最近 5 章状态（5 条）
    try:
        recent_state = store.query(
            query_texts=[f"第{chapter}章之前 最近剧情 状态变化 角色状态"],
            n_results=5,
            where={"$and": [{"project_id": project_id}, {"doc_type": "recent_state"}]}
        )
        context["recent_state"] = _safe_join(recent_state.get("documents", [[]])[0])
    except Exception:
        context["recent_state"] = ""

    # 4. 固定召回：当前卷大纲（3 条）
    try:
        volume = getattr(plan, "volume", 1)
        volume_outline = store.query(
            query_texts=[f"第{volume}卷 大纲 剧情走向 卷纲"],
            n_results=3,
            where={"$and": [{"project_id": project_id}, {"doc_type": "volume_outline"}]}
        )
        context["volume_outline"] = _safe_join(volume_outline.get("documents", [[]])[0])
    except Exception:
        context["volume_outline"] = ""

    # 5. 固定召回：禁写规则（3 条）
    try:
        forbidden = store.query(
            query_texts=["禁写规则 禁止事项 不能写 避免"],
            n_results=3,
            where={"$and": [{"project_id": project_id}, {"doc_type": "forbidden_rules"}]}
        )
        context["forbidden_rules"] = _safe_join(forbidden.get("documents", [[]])[0])
    except Exception:
        context["forbidden_rules"] = ""

    # 6. 动态召回：基于章节计划/意图/场景链的相关剧情（5 条）
    try:
        title = getattr(plan, "title", "")
        objective = getattr(plan, "objective", "")
        reader_promise = getattr(intent, "reader_promise", "")
        dynamic_query = f"{title} {objective} {reader_promise}"
        related = store.query(
            query_texts=[dynamic_query],
            n_results=5,
            where={"project_id": project_id}
        )
        context["related_history"] = _safe_join(related.get("documents", [[]])[0])
    except Exception:
        context["related_history"] = ""

    # 7. 动态召回：热点案例（3 条）
    try:
        hotspot = store.query(
            query_texts=[dynamic_query],
            n_results=3,
            where={"$and": [{"project_id": project_id}, {"doc_type": "hotspot_case"}]}
        )
        context["hotspot_cases"] = _safe_join(hotspot.get("documents", [[]])[0])
    except Exception:
        context["hotspot_cases"] = ""

    return context


def format_memory_context(context: dict[str, str], limit: int = 4000) -> str:
    """将分组上下文格式化为 prompt 字符串，控制总长度"""
    if not context:
        return ""

    # 计算每个 section 的平均长度限制
    non_empty = {k: v for k, v in context.items() if v}
    if not non_empty:
        return ""

    section_limit = limit // len(non_empty)
    sections = []

    for section_name, content in non_empty.items():
        if content:
            truncated = content[:section_limit] if len(content) > section_limit else content
            sections.append(f"## {section_name}\n{truncated}")

    return "\n\n".join(sections)
