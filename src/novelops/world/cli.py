"""世界观CLI命令

支持：
- world show: 显示世界观设定
- world edit: 编辑设定
- world generate: AI生成设定
- world import: 从bible导入
- world export: 导出到文件
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ..config import default_project_id, load_project
from ..paths import project_dir
from ..world.settings import WorldSettings, SETTING_CATEGORIES


def cmd_world_show(args: argparse.Namespace) -> int:
    """显示世界观设定"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    settings = WorldSettings(project_id, project_path)

    if args.category:
        # 显示特定分类
        summary = settings.get_category_summary(args.category)
        if summary:
            print(summary)
        else:
            print(f"分类 {args.category} 没有设定")
    elif args.key:
        # 显示特定设定
        category = args.category or _find_category_for_key(args.key)
        if not category:
            print(f"ERROR: 无法确定 {args.key} 的分类", file=sys.stderr)
            return 1

        setting = settings.get(category, args.key)
        if setting:
            print(f"分类: {category}")
            print(f"键: {setting.key}")
            print(f"描述: {setting.description}")
            print(f"AI生成: {'是' if setting.ai_generated else '否'}")
            print(f"\n值:")
            print(setting.value)
        else:
            print(f"设定不存在: {category}/{args.key}")
    else:
        # 显示所有分类
        all_settings = settings.list_all()
        if not all_settings:
            print("没有世界观设定")
            print("\n可用分类:")
            for cat_id, cat_info in SETTING_CATEGORIES.items():
                print(f"  {cat_id}: {cat_info['name']} - {cat_info['description']}")
            return 0

        # 按分类分组显示
        by_category: dict[str, list] = {}
        for s in all_settings:
            if s.category not in by_category:
                by_category[s.category] = []
            by_category[s.category].append(s)

        for cat_id, cat_settings in sorted(by_category.items()):
            cat_info = SETTING_CATEGORIES.get(cat_id, {})
            print(f"\n## {cat_info.get('name', cat_id)}")
            for s in cat_settings:
                ai_mark = " [AI]" if s.ai_generated else ""
                print(f"  - {s.key}{ai_mark}")

    return 0


def cmd_world_edit(args: argparse.Namespace) -> int:
    """编辑设定"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    settings = WorldSettings(project_id, project_path)

    # 确定分类
    category = args.category
    if not category:
        print("可用分类:")
        for cat_id, cat_info in SETTING_CATEGORIES.items():
            print(f"  {cat_id}: {cat_info['name']}")
        category = input("\n选择分类: ").strip()

    if category not in SETTING_CATEGORIES:
        print(f"ERROR: 无效分类: {category}", file=sys.stderr)
        return 1

    # 获取或创建设定
    key = args.key
    if not key:
        key = input("设定键名: ").strip()
    if not key:
        print("ERROR: 键名不能为空", file=sys.stderr)
        return 1

    existing = settings.get(category, key)
    if existing:
        print(f"当前值:\n{existing.value}")
        print("\n输入新值 (输入END结束):")
    else:
        print(f"创建新设定: {category}/{key}")
        print("输入值 (输入END结束):")

    value = _read_multiline()
    if not value:
        print("已取消")
        return 0

    description = input("描述 (可选): ").strip()

    settings.set(
        category=category,
        key=key,
        value=value,
        description=description,
    )

    print(f"已保存: {category}/{key}")
    return 0


def cmd_world_generate(args: argparse.Namespace) -> int:
    """AI生成设定"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    # 加载项目配置
    cfg = load_project(project_id)
    settings = WorldSettings(project_id, project_path)

    category = args.category
    if not category:
        print("可用分类:")
        for cat_id, cat_info in SETTING_CATEGORIES.items():
            print(f"  {cat_id}: {cat_info['name']}")
        category = input("\n选择分类: ").strip()

    if category not in SETTING_CATEGORIES:
        print(f"ERROR: 无效分类: {category}", file=sys.stderr)
        return 1

    cat_info = SETTING_CATEGORIES[category]
    print(f"\n将使用AI生成: {cat_info['name']}")
    print(f"描述: {cat_info['description']}")

    if not args.yes:
        confirm = input("\n确认生成？(y/N): ").strip().lower()
        if confirm != "y":
            print("已取消")
            return 0

    # 使用LLM生成
    try:
        from ..llm import LLMClient
        llm = LLMClient()

        # 构建提示词
        existing_settings = settings.list_category(category)
        existing_text = ""
        if existing_settings:
            existing_text = "\n已有设定:\n"
            for s in existing_settings:
                existing_text += f"- {s.key}: {s.value[:100]}...\n"

        prompt = f"""请为小说项目生成{cat_info['name']}设定。

项目类型: {cfg.get('genre', '未知')}
{existing_text}

请生成以下字段的设定:
{', '.join(cat_info['fields'])}

每个字段返回一个JSON对象，键为字段名，值为详细的设定内容。"""

        system = f"你是专业的小说世界观设定专家，擅长设计{cfg.get('genre', '')}类型的世界观。"

        result = llm.complete_json(prompt, system=system, stage="assistant")

        # 保存生成的设定
        for key, value in result.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, indent=2)
            settings.set(
                category=category,
                key=key,
                value=str(value),
                ai_generated=True,
            )
            print(f"  已生成: {key}")

        print(f"\n生成完成: {len(result)} 个设定")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    return 0


def cmd_world_import(args: argparse.Namespace) -> int:
    """从bible导入"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    settings = WorldSettings(project_id, project_path)

    # 查找bible文件
    bible_path = project_path / "bible" / "00_story_bible.md"
    if args.file:
        bible_path = Path(args.file)

    if not bible_path.exists():
        print(f"ERROR: Bible文件不存在: {bible_path}", file=sys.stderr)
        return 1

    print(f"从 {bible_path} 导入...")
    imported = settings.import_from_bible(bible_path)
    print(f"导入完成: {imported} 个设定")
    return 0


def cmd_world_export(args: argparse.Namespace) -> int:
    """导出到文件"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    settings = WorldSettings(project_id, project_path)

    output_path = Path(args.output) if args.output else project_path / "bible" / "world_settings.md"

    settings.export_to_file(output_path)
    print(f"已导出到: {output_path}")
    return 0


def _read_multiline() -> str:
    """读取多行输入"""
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def _find_category_for_key(key: str) -> str | None:
    """根据键名查找分类"""
    for cat_id, cat_info in SETTING_CATEGORIES.items():
        if key in cat_info.get("fields", []):
            return cat_id
    return None


def register_world_commands(subparsers: argparse._SubParsersAction) -> None:
    """注册世界观子命令"""
    world_parser = subparsers.add_parser("world", help="世界观设定管理")
    world_sub = world_parser.add_subparsers(dest="world_command", required=True)

    # world show
    show_parser = world_sub.add_parser("show", help="显示世界观设定")
    show_parser.add_argument("--project", help="Project ID")
    show_parser.add_argument("--category", "-c", help="分类")
    show_parser.add_argument("--key", "-k", help="设定键名")
    show_parser.set_defaults(func=cmd_world_show)

    # world edit
    edit_parser = world_sub.add_parser("edit", help="编辑设定")
    edit_parser.add_argument("--project", help="Project ID")
    edit_parser.add_argument("--category", "-c", help="分类")
    edit_parser.add_argument("--key", "-k", help="设定键名")
    edit_parser.set_defaults(func=cmd_world_edit)

    # world generate
    generate_parser = world_sub.add_parser("generate", help="AI生成设定")
    generate_parser.add_argument("--project", help="Project ID")
    generate_parser.add_argument("--category", "-c", help="分类")
    generate_parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    generate_parser.set_defaults(func=cmd_world_generate)

    # world import
    import_parser = world_sub.add_parser("import", help="从bible导入")
    import_parser.add_argument("--project", help="Project ID")
    import_parser.add_argument("--file", "-f", help="bible文件路径")
    import_parser.set_defaults(func=cmd_world_import)

    # world export
    export_parser = world_sub.add_parser("export", help="导出到文件")
    export_parser.add_argument("--project", help="Project ID")
    export_parser.add_argument("--output", "-o", help="输出文件路径")
    export_parser.set_defaults(func=cmd_world_export)
