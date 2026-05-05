"""从项目文件建立/重建向量索引"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .store import MemoryStore


def _chunk_markdown(file_path: Path, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    """将 Markdown 文件分块"""
    if not file_path.exists():
        return []

    text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
    if len(text) < 50:
        return []

    return _chunk_text(text, chunk_size, overlap)


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    """将文本分块"""
    if len(text) < 50:
        return []

    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = current_chunk[-overlap:] + "\n\n" + para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def _chunk_jsonl(file_path: Path) -> list[dict[str, Any]]:
    """读取 JSONL 文件，每行作为一个文档"""
    if not file_path.exists():
        return []

    chunks = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return chunks


def _index_protagonist_setting(project_path: Path, project_id: str) -> tuple[list[str], list[str], list[dict]]:
    """索引主角设定"""
    ids, documents, metadatas = [], [], []
    protagonist_files = [
        "bible/01_characters.md",
        "bible/03_CHARACTER_BIBLE.md",
        "bible/00_story_bible.md"
    ]
    for file in protagonist_files:
        chunks = _chunk_markdown(project_path / file)
        for i, chunk in enumerate(chunks):
            ids.append(f"{project_id}_protagonist_{Path(file).stem}_{i}")
            documents.append(chunk)
            metadatas.append({
                "project_id": project_id,
                "doc_type": "protagonist_setting",
                "source": file
            })
    return ids, documents, metadatas


def _index_first_chapters(project_path: Path, project_id: str) -> tuple[list[str], list[str], list[dict]]:
    """索引前 3 章"""
    ids, documents, metadatas = [], [], []
    for chapter_num in range(1, 4):
        chapter_file = project_path / "corpus" / "volume_01" / f"chapter_{chapter_num:03d}.md"
        chunks = _chunk_markdown(chapter_file)
        for i, chunk in enumerate(chunks):
            ids.append(f"{project_id}_first_ch{chapter_num}_{i}")
            documents.append(chunk)
            metadatas.append({
                "project_id": project_id,
                "doc_type": "first_chapters",
                "chapter": chapter_num
            })
    return ids, documents, metadatas


def _index_recent_state(project_path: Path, project_id: str) -> tuple[list[str], list[str], list[dict]]:
    """索引最近 5 章状态"""
    ids, documents, metadatas = [], [], []
    state_files = ["state/chapter_summary.md", "state/character_state.md"]
    for file in state_files:
        chunks = _chunk_markdown(project_path / file)
        # 只取最后 5 个 chunk（约对应最近 5 章）
        for i, chunk in enumerate(chunks[-5:]):
            ids.append(f"{project_id}_recent_state_{Path(file).stem}_{i}")
            documents.append(chunk)
            metadatas.append({
                "project_id": project_id,
                "doc_type": "recent_state",
                "source": file
            })
    return ids, documents, metadatas


def _index_volume_outline(project_path: Path, project_id: str) -> tuple[list[str], list[str], list[dict]]:
    """索引当前卷大纲"""
    ids, documents, metadatas = [], [], []
    outline_files = [
        "outlines/01_volume_outline.md",
        "outlines/04_VOLUME_OUTLINE.md"
    ]
    for file in outline_files:
        chunks = _chunk_markdown(project_path / file)
        for i, chunk in enumerate(chunks):
            ids.append(f"{project_id}_volume_outline_{Path(file).stem}_{i}")
            documents.append(chunk)
            metadatas.append({
                "project_id": project_id,
                "doc_type": "volume_outline",
                "source": file
            })
    return ids, documents, metadatas


def _index_forbidden_rules(project_path: Path, project_id: str) -> tuple[list[str], list[str], list[dict]]:
    """索引禁写规则"""
    ids, documents, metadatas = [], [], []
    forbidden_files = [
        "bible/04_forbidden_rules.md",
        "bible/13_FORBIDDEN_DEVIATIONS.md"
    ]
    for file in forbidden_files:
        chunks = _chunk_markdown(project_path / file)
        for i, chunk in enumerate(chunks):
            ids.append(f"{project_id}_forbidden_{Path(file).stem}_{i}")
            documents.append(chunk)
            metadatas.append({
                "project_id": project_id,
                "doc_type": "forbidden_rules",
                "source": file
            })

    # 从 project.json 读取 forbidden_terms
    try:
        project_config = json.loads((project_path / "project.json").read_text())
        forbidden_terms = project_config.get("rubric", {}).get("forbidden_terms", [])
        if forbidden_terms:
            ids.append(f"{project_id}_forbidden_terms_0")
            documents.append("禁写项: " + ", ".join(forbidden_terms))
            metadatas.append({
                "project_id": project_id,
                "doc_type": "forbidden_rules",
                "source": "project.json"
            })
    except Exception:
        pass

    return ids, documents, metadatas


def _index_hotspot_cases(project_path: Path, project_id: str) -> tuple[list[str], list[str], list[dict]]:
    """索引热点案例"""
    ids, documents, metadatas = [], [], []
    hotspot_files = [
        "intelligence/processed/topic_candidates.jsonl",
        "intelligence/reports/topic_scoreboard.md"
    ]
    for file in hotspot_files:
        if file.endswith(".jsonl"):
            chunks = _chunk_jsonl(project_path / file)
            for i, chunk in enumerate(chunks):
                ids.append(f"{project_id}_hotspot_{i}")
                documents.append(json.dumps(chunk, ensure_ascii=False))
                metadatas.append({
                    "project_id": project_id,
                    "doc_type": "hotspot_case",
                    "source": file
                })
        else:
            chunks = _chunk_markdown(project_path / file)
            for i, chunk in enumerate(chunks):
                ids.append(f"{project_id}_hotspot_{Path(file).stem}_{i}")
                documents.append(chunk)
                metadatas.append({
                    "project_id": project_id,
                    "doc_type": "hotspot_case",
                    "source": file
                })
    return ids, documents, metadatas


def index_project(project_path: Path, store: MemoryStore) -> int:
    """重建指定项目的记忆库，返回索引文档数"""
    project_id = project_path.name

    # 删除旧索引，重建
    store.delete_collection()

    all_ids = []
    all_documents = []
    all_metadatas = []

    # 索引各类文档
    for index_func in [
        _index_protagonist_setting,
        _index_first_chapters,
        _index_recent_state,
        _index_volume_outline,
        _index_forbidden_rules,
        _index_hotspot_cases
    ]:
        ids, documents, metadatas = index_func(project_path, project_id)
        all_ids.extend(ids)
        all_documents.extend(documents)
        all_metadatas.extend(metadatas)

    # 批量写入 Chroma
    if all_ids:
        store.upsert(ids=all_ids, documents=all_documents, metadatas=all_metadatas)

    return len(all_ids)


def index_chapter(project_path: Path, chapter: int, chapter_text: str, store: MemoryStore) -> None:
    """章节通过审稿后，增量更新记忆库"""
    project_id = project_path.name

    # 读取章节摘要（如果已存在）
    summary_path = project_path / "state" / "chapter_summary.md"
    if summary_path.exists():
        summary_text = summary_path.read_text(encoding="utf-8")
        # 提取最新章节摘要
        pattern = rf"## 第 {chapter} 章\n(.*?)(?=\n## 第|\Z)"
        match = re.search(pattern, summary_text, re.DOTALL)
        if match:
            summary = match.group(1).strip()

            # 索引章节摘要
            store.upsert(
                ids=[f"{project_id}_recent_ch{chapter}_0"],
                documents=[summary],
                metadatas=[{
                    "project_id": project_id,
                    "doc_type": "recent_state",
                    "chapter": chapter,
                    "source": "chapter_summary"
                }]
            )

    # 索引章节正文
    chunks = _chunk_text(chapter_text)
    ids = []
    documents = []
    metadatas = []
    for i, chunk in enumerate(chunks):
        ids.append(f"{project_id}_corpus_ch{chapter}_{i}")
        documents.append(chunk)
        metadatas.append({
            "project_id": project_id,
            "doc_type": "corpus",
            "chapter": chapter
        })

    if ids:
        store.upsert(ids=ids, documents=documents, metadatas=metadatas)
