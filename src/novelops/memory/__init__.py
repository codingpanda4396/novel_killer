"""NovelOps 记忆层 - 基于 ChromaDB 的语义召回模块"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _check_chromadb():
    """检查 chromadb 是否已安装，未安装时给出清晰错误提示"""
    try:
        import chromadb
        return chromadb
    except ImportError:
        raise ImportError(
            "ChromaDB 未安装。请运行: pip install chromadb>=0.5\n"
            "记忆层功能需要 ChromaDB 支持。"
        )


def get_store(runtime_dir: Path | None = None):
    """获取 MemoryStore 实例（懒加载）"""
    from .store import MemoryStore
    return MemoryStore(runtime_dir)


def index_project(project_path: Path, store=None) -> int:
    """重建指定项目的记忆库，返回索引文档数"""
    _check_chromadb()
    from .indexer import index_project as _index_project
    if store is None:
        store = get_store()
    return _index_project(project_path, store)


def recall_for_chapter(
    project_path: Path,
    chapter: int,
    plan: Any,
    intent: Any,
    chain: Any,
    store=None
) -> dict[str, str]:
    """返回分组后的生成上下文"""
    _check_chromadb()
    from .retriever import recall_for_chapter as _recall_for_chapter
    if store is None:
        store = get_store()
    return _recall_for_chapter(project_path, chapter, plan, intent, chain, store)


def format_memory_context(context: dict[str, str], limit: int = 4000) -> str:
    """将分组上下文格式化为 prompt 字符串，控制总长度"""
    from .retriever import format_memory_context as _format_memory_context
    return _format_memory_context(context, limit)


__all__ = [
    "get_store",
    "index_project",
    "recall_for_chapter",
    "format_memory_context",
]
