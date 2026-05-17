"""项目导出器

支持导出完整项目为JSON格式
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..project_paths import ProjectPaths


class ProjectExporter:
    """项目导出器"""

    def __init__(self, project_id: str, project_path: Path):
        self.project_id = project_id
        self.project_path = project_path
        self.paths = ProjectPaths(project_path)

    def export(
        self,
        output_path: Path | None = None,
        include_chapters: bool = True,
        include_generation: bool = False,
        include_reviews: bool = False,
        chapter_limit: int | None = None,
    ) -> Path:
        """导出项目

        Args:
            output_path: 输出文件路径，None则自动生成
            include_chapters: 是否包含正文
            include_generation: 是否包含生成文件
            include_reviews: 是否包含审稿报告
            chapter_limit: 限制章节数量

        Returns:
            输出文件路径
        """
        # 收集数据
        data = self._collect_project_data(
            include_chapters=include_chapters,
            include_generation=include_generation,
            include_reviews=include_reviews,
            chapter_limit=chapter_limit,
        )

        # 确定输出路径
        if output_path is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"{self.project_id}_export_{timestamp}.json")

        # 写入文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return output_path

    def export_chapters_markdown(
        self,
        output_path: Path | None = None,
        chapter_limit: int | None = None,
    ) -> Path:
        """导出章节为单个Markdown文件

        Args:
            output_path: 输出文件路径
            chapter_limit: 限制章节数量

        Returns:
            输出文件路径
        """
        chapters = self._collect_chapters(limit=chapter_limit)

        if output_path is None:
            output_path = Path(f"{self.project_id}_chapters.md")

        lines = [f"# {self.project_id}\n"]

        for chapter_num in sorted(chapters.keys()):
            chapter_data = chapters[chapter_num]
            title = chapter_data.get("title", f"第{chapter_num}章")
            content = chapter_data.get("content", "")

            lines.append(f"\n## {title}\n")
            lines.append(content)
            lines.append("\n---\n")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")

        return output_path

    def _collect_project_data(
        self,
        include_chapters: bool = True,
        include_generation: bool = False,
        include_reviews: bool = False,
        chapter_limit: int | None = None,
    ) -> dict[str, Any]:
        """收集项目数据"""
        data: dict[str, Any] = {
            "export_meta": {
                "project_id": self.project_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "version": "2.0",
            },
        }

        # 项目配置
        project_json = self.project_path / "project.json"
        if project_json.exists():
            data["project"] = json.loads(project_json.read_text(encoding="utf-8"))

        # 世界观设定
        data["bible"] = self._collect_bible()

        # 大纲
        data["outlines"] = self._collect_outlines()

        # 章节
        if include_chapters:
            data["chapters"] = self._collect_chapters(limit=chapter_limit)

        # 生成文件
        if include_generation:
            data["generation"] = self._collect_generation(limit=chapter_limit)

        # 审稿报告
        if include_reviews:
            data["reviews"] = self._collect_reviews(limit=chapter_limit)

        # 状态文件
        data["state"] = self._collect_state()

        return data

    def _collect_bible(self) -> dict[str, str]:
        """收集bible文件"""
        bible: dict[str, str] = {}
        bible_dir = self.project_path / "bible"

        if bible_dir.exists():
            for md_file in bible_dir.glob("*.md"):
                try:
                    bible[md_file.name] = md_file.read_text(encoding="utf-8")
                except Exception:
                    pass

        return bible

    def _collect_outlines(self) -> dict[str, str]:
        """收集大纲文件"""
        outlines: dict[str, str] = {}
        outlines_dir = self.project_path / "outlines"

        if outlines_dir.exists():
            for md_file in outlines_dir.glob("*.md"):
                try:
                    outlines[md_file.name] = md_file.read_text(encoding="utf-8")
                except Exception:
                    pass

        return outlines

    def _collect_chapters(self, limit: int | None = None) -> dict[int, dict[str, Any]]:
        """收集章节"""
        chapters: dict[int, dict[str, Any]] = {}
        corpus_dir = self.paths.corpus

        if not corpus_dir.exists():
            return chapters

        # 查找所有卷
        for volume_dir in sorted(corpus_dir.glob("volume_*")):
            if not volume_dir.is_dir():
                continue

            for md_file in sorted(volume_dir.glob("chapter_*.md")):
                try:
                    # 解析章节号
                    chapter_num = int(md_file.stem.split("_")[1])
                    content = md_file.read_text(encoding="utf-8")

                    # 提取标题（第一行）
                    lines = content.split("\n")
                    title = lines[0].strip("# ").strip() if lines else f"第{chapter_num}章"

                    chapters[chapter_num] = {
                        "title": title,
                        "content": content,
                        "file": str(md_file.relative_to(self.project_path)),
                    }

                    if limit and len(chapters) >= limit:
                        return chapters

                except (ValueError, IndexError):
                    continue

        return chapters

    def _collect_generation(self, limit: int | None = None) -> dict[str, Any]:
        """收集生成文件"""
        generation: dict[str, Any] = {}
        gen_dir = self.paths.generation

        if not gen_dir.exists():
            return generation

        chapter_dirs = sorted(gen_dir.glob("chapter_*"))
        if limit:
            chapter_dirs = chapter_dirs[-limit:]

        for chapter_dir in chapter_dirs:
            if not chapter_dir.is_dir():
                continue

            chapter_data: dict[str, str] = {}
            for file in chapter_dir.glob("*"):
                if file.is_file():
                    try:
                        chapter_data[file.name] = file.read_text(encoding="utf-8")
                    except Exception:
                        pass

            generation[chapter_dir.name] = chapter_data

        return generation

    def _collect_reviews(self, limit: int | None = None) -> dict[str, Any]:
        """收集审稿报告"""
        reviews: dict[str, Any] = {}
        reviews_dir = self.paths.reviews

        if not reviews_dir.exists():
            return reviews

        review_files = sorted(reviews_dir.glob("*.json"))
        if limit:
            review_files = review_files[-limit:]

        for review_file in review_files:
            try:
                reviews[review_file.stem] = json.loads(
                    review_file.read_text(encoding="utf-8")
                )
            except Exception:
                pass

        return reviews

    def _collect_state(self) -> dict[str, str]:
        """收集状态文件"""
        state: dict[str, str] = {}
        state_dir = self.paths.state

        if state_dir.exists():
            for file in state_dir.glob("*"):
                if file.is_file():
                    try:
                        state[file.name] = file.read_text(encoding="utf-8")
                    except Exception:
                        pass

        return state
