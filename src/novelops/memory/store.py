"""ChromaDB 存储封装"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..paths import RUNTIME_DIR


class MemoryStore:
    """封装 Chroma PersistentClient，提供简化的向量存储接口"""

    def __init__(self, runtime_dir: Path | None = None):
        self._chroma_dir = (runtime_dir or RUNTIME_DIR) / "chroma"
        self._client = None
        self._collection = None

    @property
    def client(self):
        """懒加载 ChromaDB 客户端"""
        if self._client is None:
            from . import _check_chromadb
            chromadb = _check_chromadb()
            self._chroma_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self._chroma_dir))
        return self._client

    def collection(self, name: str = "novel_memory"):
        """获取或创建 collection"""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]]
    ) -> None:
        """批量插入或更新文档"""
        if not ids:
            return
        self.collection().upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def query(
        self,
        query_texts: list[str],
        n_results: int = 5,
        where: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """查询相似文档"""
        kwargs = {
            "query_texts": query_texts,
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where
        return self.collection().query(**kwargs)

    def delete_collection(self, name: str = "novel_memory") -> None:
        """删除 collection（用于重建索引）"""
        try:
            self.client.delete_collection(name)
            self._collection = None
        except Exception:
            pass

    def count(self) -> int:
        """返回 collection 中的文档数量"""
        return self.collection().count()
