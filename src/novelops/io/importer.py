"""项目导入器

支持从JSON、Markdown等格式导入项目
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..project import init_project
from ..paths import project_dir
from ..project_paths import ProjectPaths


class ProjectImporter:
    """项目导入器"""

    def __init__(self):
        pass

    def import_from_json(
        self,
        json_path: Path,
        project_id: str | None = None,
        overwrite: bool = False,
    ) -> Path:
        """从JSON导入项目

        Args:
            json_path: JSON文件路径
            project_id: 项目ID，None则使用导出时的ID
            overwrite: 是否覆盖现有项目

        Returns:
            项目路径
        """
        if not json_path.exists():
            raise FileNotFoundError(f"文件不存在: {json_path}")

        data = json.loads(json_path.read_text(encoding="utf-8"))

        # 获取项目ID
        export_meta = data.get("export_meta", {})
        pid = project_id or export_meta.get("project_id")
        if not pid:
            raise ValueError("无法确定项目ID，请指定 project_id")

        # 检查项目是否存在
        p_path = project_dir(pid)
        if p_path.exists() and not overwrite:
            raise FileExistsError(f"项目已存在: {pid}，使用 overwrite=True 覆盖")

        # 创建项目
        project_data = data.get("project", {})
        init_project(
            project_id=pid,
            name=project_data.get("name", pid),
            genre=project_data.get("genre", ""),
            target_platform=project_data.get("target_platform", ""),
        )

        paths = ProjectPaths(p_path)

        # 恢复bible
        bible_data = data.get("bible", {})
        for filename, content in bible_data.items():
            file_path = paths.bible / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        # 恢复大纲
        outlines_data = data.get("outlines", {})
        for filename, content in outlines_data.items():
            file_path = paths.outlines / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        # 恢复章节
        chapters_data = data.get("chapters", {})
        for chapter_num, chapter_info in chapters_data.items():
            content = chapter_info.get("content", "")
            if content:
                # 保存到corpus
                volume = 1  # 默认卷
                volume_dir = paths.corpus_volume(volume)
                volume_dir.mkdir(parents=True, exist_ok=True)
                file_path = volume_dir / f"chapter_{int(chapter_num):03d}.md"
                file_path.write_text(content, encoding="utf-8")

        # 恢复状态
        state_data = data.get("state", {})
        for filename, content in state_data.items():
            file_path = paths.state / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        return p_path

    def import_from_markdown(
        self,
        md_path: Path,
        project_id: str,
        name: str | None = None,
        genre: str = "",
        split_chapters: bool = True,
    ) -> Path:
        """从Markdown导入

        Args:
            md_path: Markdown文件路径
            project_id: 项目ID
            name: 项目名称
            genre: 类型
            split_chapters: 是否按章节分割

        Returns:
            项目路径
        """
        if not md_path.exists():
            raise FileNotFoundError(f"文件不存在: {md_path}")

        content = md_path.read_text(encoding="utf-8")

        # 创建项目
        p_path = init_project(
            project_id=project_id,
            name=name or project_id,
            genre=genre,
        )

        paths = ProjectPaths(p_path)

        if split_chapters:
            # 按章节分割
            chapters = self._split_chapters(content)
            volume_dir = paths.corpus_volume(1)
            volume_dir.mkdir(parents=True, exist_ok=True)

            for i, chapter_content in enumerate(chapters, 1):
                file_path = volume_dir / f"chapter_{i:03d}.md"
                file_path.write_text(chapter_content, encoding="utf-8")

            print(f"导入了 {len(chapters)} 章")
        else:
            # 保存为单个文件
            file_path = paths.bible / "imported_content.md"
            file_path.write_text(content, encoding="utf-8")

        return p_path

    def import_from_text(
        self,
        text_path: Path,
        project_id: str,
        name: str | None = None,
        genre: str = "",
        encoding: str = "utf-8",
    ) -> Path:
        """从纯文本导入

        Args:
            text_path: 文本文件路径
            project_id: 项目ID
            name: 项目名称
            genre: 类型
            encoding: 文件编码

        Returns:
            项目路径
        """
        if not text_path.exists():
            raise FileNotFoundError(f"文件不存在: {text_path}")

        content = text_path.read_text(encoding=encoding)

        # 尝试按章节分割
        chapters = self._split_chapters(content)

        # 创建项目
        p_path = init_project(
            project_id=project_id,
            name=name or project_id,
            genre=genre,
        )

        paths = ProjectPaths(p_path)

        if chapters:
            volume_dir = paths.corpus_volume(1)
            volume_dir.mkdir(parents=True, exist_ok=True)

            for i, chapter_content in enumerate(chapters, 1):
                file_path = volume_dir / f"chapter_{i:03d}.md"
                file_path.write_text(chapter_content, encoding="utf-8")

            print(f"导入了 {len(chapters)} 章")
        else:
            # 保存为单个文件
            file_path = paths.bible / "imported_content.md"
            file_path.write_text(content, encoding="utf-8")

        return p_path

    def _split_chapters(self, content: str) -> list[str]:
        """按章节分割内容

        支持的格式：
        - # 第X章
        - ## 第X章
        - 第X章
        - Chapter X
        """
        # 匹配章节标题的正则表达式
        patterns = [
            r'^#{1,2}\s+第\d+章',  # # 第X章 或 ## 第X章
            r'^第\d+章',           # 第X章
            r'^#{1,2}\s+Chapter\s+\d+',  # # Chapter X
            r'^Chapter\s+\d+',     # Chapter X
        ]

        # 尝试找到分割点
        split_points = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            for pattern in patterns:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    split_points.append(i)
                    break

        if not split_points:
            # 没有找到章节分割，返回整个内容
            return [content] if content.strip() else []

        # 分割章节
        chapters = []
        for i, start in enumerate(split_points):
            end = split_points[i + 1] if i + 1 < len(split_points) else len(lines)
            chapter_lines = lines[start:end]
            chapter_content = '\n'.join(chapter_lines).strip()
            if chapter_content:
                chapters.append(chapter_content)

        return chapters

    def preview_import(self, file_path: Path) -> dict[str, Any]:
        """预览导入结果

        Args:
            file_path: 文件路径

        Returns:
            预览信息
        """
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = file_path.suffix.lower()
        preview: dict[str, Any] = {
            "file": str(file_path),
            "size": file_path.stat().st_size,
            "format": suffix,
        }

        if suffix == ".json":
            data = json.loads(file_path.read_text(encoding="utf-8"))
            meta = data.get("export_meta", {})
            project = data.get("project", {})

            preview["project_id"] = meta.get("project_id")
            preview["project_name"] = project.get("name")
            preview["genre"] = project.get("genre")
            preview["exported_at"] = meta.get("exported_at")

            chapters = data.get("chapters", {})
            preview["chapters_count"] = len(chapters)

            bible = data.get("bible", {})
            preview["bible_files"] = list(bible.keys())

        elif suffix in (".md", ".txt"):
            content = file_path.read_text(encoding="utf-8")
            chapters = self._split_chapters(content)
            preview["chapters_count"] = len(chapters)
            preview["total_chars"] = len(content)

        return preview
