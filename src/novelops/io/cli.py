"""导入导出CLI命令

支持：
- export: 导出项目
- import: 导入项目
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ..config import default_project_id
from ..paths import project_dir
from ..io.exporter import ProjectExporter
from ..io.importer import ProjectImporter


def cmd_export(args: argparse.Namespace) -> int:
    """导出项目"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    exporter = ProjectExporter(project_id, project_path)

    output_path = Path(args.output) if args.output else None

    if args.format == "markdown":
        result = exporter.export_chapters_markdown(
            output_path=output_path,
            chapter_limit=args.limit,
        )
    else:
        result = exporter.export(
            output_path=output_path,
            include_chapters=not args.no_chapters,
            include_generation=args.with_generation,
            include_reviews=args.with_reviews,
            chapter_limit=args.limit,
        )

    print(f"已导出到: {result}")
    print(f"文件大小: {result.stat().st_size / 1024:.1f} KB")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    """导入项目"""
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"ERROR: 文件不存在: {file_path}", file=sys.stderr)
        return 1

    importer = ProjectImporter()

    # 预览
    if args.preview:
        preview = importer.preview_import(file_path)
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    # 导入
    try:
        suffix = file_path.suffix.lower()

        if suffix == ".json":
            result = importer.import_from_json(
                json_path=file_path,
                project_id=args.project_id,
                overwrite=args.overwrite,
            )
        elif suffix in (".md", ".txt"):
            if not args.project_id:
                print("ERROR: 导入Markdown/文本文件需要指定 --project-id", file=sys.stderr)
                return 1

            result = importer.import_from_markdown(
                md_path=file_path,
                project_id=args.project_id,
                name=args.name,
                genre=args.genre or "",
            )
        else:
            print(f"ERROR: 不支持的文件格式: {suffix}", file=sys.stderr)
            return 1

        print(f"已导入到: {result}")
        return 0

    except FileExistsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def register_io_commands(subparsers: argparse._SubParsersAction) -> None:
    """注册导入导出子命令"""
    # export
    export_parser = subparsers.add_parser("export", help="导出项目")
    export_parser.add_argument("--project", help="Project ID")
    export_parser.add_argument("--output", "-o", help="输出文件路径")
    export_parser.add_argument("--format", choices=["json", "markdown"], default="json", help="输出格式")
    export_parser.add_argument("--no-chapters", action="store_true", help="不包含正文")
    export_parser.add_argument("--with-generation", action="store_true", help="包含生成文件")
    export_parser.add_argument("--with-reviews", action="store_true", help="包含审稿报告")
    export_parser.add_argument("--limit", type=int, help="限制章节数量")
    export_parser.set_defaults(func=cmd_export)

    # import
    import_parser = subparsers.add_parser("import", help="导入项目")
    import_parser.add_argument("file", help="要导入的文件")
    import_parser.add_argument("--project-id", help="项目ID")
    import_parser.add_argument("--name", help="项目名称")
    import_parser.add_argument("--genre", help="类型")
    import_parser.add_argument("--overwrite", action="store_true", help="覆盖现有项目")
    import_parser.add_argument("--preview", action="store_true", help="预览导入结果")
    import_parser.set_defaults(func=cmd_import)
