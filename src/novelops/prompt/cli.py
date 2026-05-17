"""提示词CLI命令

支持：
- prompt list: 列出所有模板
- prompt show: 查看模板详情
- prompt edit: 编辑模板
- prompt create: 创建新模板
- prompt test: 测试模板
- prompt examples: 管理示例
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ..prompt.store import PromptStore
from ..prompt.engine import PromptTemplate, ParamDef, ParamType


def cmd_prompt_list(args: argparse.Namespace) -> int:
    """列出所有模板"""
    store = PromptStore()
    templates = store.list_all(stage=args.stage, genre=args.genre)

    if not templates:
        print("没有找到模板")
        return 0

    print(f"共 {len(templates)} 个模板:\n")
    for t in templates:
        default_mark = " [默认]" if t.is_default else ""
        genre_mark = f" ({t.genre})" if t.genre else ""
        print(f"  {t.id}: {t.name}{genre_mark}{default_mark}")
        print(f"    阶段: {t.stage}, 参数: {len(t.params)}, 版本: {t.version}")

    return 0


def cmd_prompt_show(args: argparse.Namespace) -> int:
    """查看模板详情"""
    store = PromptStore()
    template = store.get(args.template_id)

    if not template:
        print(f"ERROR: 模板不存在: {args.template_id}", file=sys.stderr)
        return 1

    print(f"ID: {template.id}")
    print(f"名称: {template.name}")
    print(f"阶段: {template.stage}")
    print(f"题材: {template.genre or '通用'}")
    print(f"版本: {template.version}")
    print(f"默认: {'是' if template.is_default else '否'}")
    print(f"\n描述: {template.description}")

    print(f"\n系统提示词:")
    print(template.system_prompt)

    print(f"\n用户提示词模板:")
    print(template.user_prompt_template)

    if template.params:
        print(f"\n参数 ({len(template.params)}):")
        for p in template.params:
            required = " [必填]" if p.required else ""
            default = f" (默认: {p.default})" if p.default is not None else ""
            print(f"  - {p.name} ({p.type.value}){required}{default}")
            if p.description:
                print(f"    {p.description}")
            if p.min is not None or p.max is not None:
                print(f"    范围: {p.min or '无限制'} - {p.max or '无限制'}")
            if p.options:
                print(f"    选项: {', '.join(p.options)}")

    # 显示示例
    examples = store.get_examples(template.id)
    if examples:
        print(f"\n示例 ({len(examples)}):")
        for ex in examples:
            print(f"  [{ex['type']}] {ex.get('notes', '')}")

    return 0


def cmd_prompt_create(args: argparse.Namespace) -> int:
    """创建新模板"""
    store = PromptStore()

    print("创建新提示词模板")
    print()

    # 收集信息
    template_id = input("模板ID (留空自动生成): ").strip()
    name = input("模板名称: ").strip()
    if not name:
        print("ERROR: 名称不能为空", file=sys.stderr)
        return 1

    stage = input("阶段 (draft/review/outline/concept等): ").strip()
    if not stage:
        print("ERROR: 阶段不能为空", file=sys.stderr)
        return 1

    description = input("描述: ").strip()
    genre = input("题材 (留空为通用): ").strip() or None

    print("\n系统提示词 (输入END结束):")
    system_prompt = _read_multiline()

    print("\n用户提示词模板 (输入END结束，使用{{变量名}}定义参数):")
    user_prompt = _read_multiline()

    # 解析参数
    params = _extract_params(user_prompt)

    template = PromptTemplate(
        id=template_id if template_id else None,
        stage=stage,
        name=name,
        description=description,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt,
        params=params,
        genre=genre,
    )

    # 保存
    created = store.create(template)
    print(f"\n已创建模板: {created.id}")
    return 0


def cmd_prompt_edit(args: argparse.Namespace) -> int:
    """编辑模板"""
    store = PromptStore()
    template = store.get(args.template_id)

    if not template:
        print(f"ERROR: 模板不存在: {args.template_id}", file=sys.stderr)
        return 1

    print(f"编辑模板: {template.id} - {template.name}")
    print()

    while True:
        print("可用操作:")
        print("  1. 修改名称")
        print("  2. 修改描述")
        print("  3. 修改系统提示词")
        print("  4. 修改用户提示词模板")
        print("  5. 设置为默认")
        print("  6. 保存并退出")
        print("  7. 不保存退出")

        choice = input("\n请选择操作 [1-7]: ").strip()

        if choice == "1":
            new_name = input(f"新名称 (当前: {template.name}): ").strip()
            if new_name:
                template.name = new_name
        elif choice == "2":
            new_desc = input(f"新描述 (当前: {template.description}): ").strip()
            if new_desc:
                template.description = new_desc
        elif choice == "3":
            print(f"当前系统提示词:\n{template.system_prompt}")
            print("\n输入新的系统提示词 (输入END结束):")
            template.system_prompt = _read_multiline()
        elif choice == "4":
            print(f"当前用户提示词模板:\n{template.user_prompt_template}")
            print("\n输入新的用户提示词模板 (输入END结束):")
            template.user_prompt_template = _read_multiline()
            template.params = _extract_params(template.user_prompt_template)
        elif choice == "5":
            store.set_default(template.id, template.stage)
            print(f"已设置为 {template.stage} 阶段的默认模板")
        elif choice == "6":
            store.update(template)
            print("已保存")
            return 0
        elif choice == "7":
            print("已退出，未保存修改")
            return 0
        else:
            print("无效选择")

        print()


def cmd_prompt_test(args: argparse.Namespace) -> int:
    """测试模板"""
    store = PromptStore()
    template = store.get(args.template_id)

    if not template:
        print(f"ERROR: 模板不存在: {args.template_id}", file=sys.stderr)
        return 1

    print(f"测试模板: {template.id} - {template.name}")
    print()

    # 收集参数值
    params = {}
    for p in template.params:
        if p.required:
            value = input(f"{p.name} ({p.description}): ").strip()
            params[p.name] = value
        elif p.default is not None:
            value = input(f"{p.name} (默认: {p.default}): ").strip()
            if value:
                params[p.name] = value
            else:
                params[p.name] = p.default

    # 渲染
    from ..prompt.engine import PromptEngine
    engine = PromptEngine(template)

    try:
        system, user = engine.render(params)
        print("\n" + "="*50)
        print("系统提示词:")
        print("="*50)
        print(system)
        print("\n" + "="*50)
        print("用户提示词:")
        print("="*50)
        print(user)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1

    return 0


def cmd_prompt_examples(args: argparse.Namespace) -> int:
    """管理示例"""
    store = PromptStore()
    template = store.get(args.template_id)

    if not template:
        print(f"ERROR: 模板不存在: {args.template_id}", file=sys.stderr)
        return 1

    if args.action == "list":
        examples = store.get_examples(template.id)
        if not examples:
            print("没有示例")
            return 0

        print(f"模板 {template.id} 的示例:")
        for ex in examples:
            print(f"\n[{ex['type']}] {ex.get('notes', '')}")
            if ex.get('input_context'):
                print(f"  输入: {ex['input_context'][:100]}...")
            if ex.get('expected_output'):
                print(f"  输出: {ex['expected_output'][:100]}...")

    elif args.action == "add":
        print("添加示例")
        ex_type = input("类型 (positive/negative): ").strip()
        if ex_type not in ("positive", "negative"):
            print("ERROR: 类型必须是 positive 或 negative", file=sys.stderr)
            return 1

        print("输入上下文 (输入END结束):")
        input_ctx = _read_multiline()

        print("期望输出 (输入END结束):")
        expected = _read_multiline()

        notes = input("备注: ").strip()

        ex_id = store.add_example(template.id, ex_type, input_ctx, expected, notes)
        print(f"已添加示例: {ex_id}")

    elif args.action == "delete":
        if not args.example_id:
            print("ERROR: 需要指定示例ID", file=sys.stderr)
            return 1

        if store.delete_example(args.example_id):
            print("已删除示例")
        else:
            print("ERROR: 示例不存在", file=sys.stderr)
            return 1

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


def _extract_params(template_text: str) -> list[ParamDef]:
    """从模板文本中提取参数定义"""
    import re

    # 匹配 {{variable}} 或 {{variable | default_value}}
    pattern = re.compile(r"\{\{\s*(\w+)(?:\s*\|\s*(.+?))?\s*\}\}")
    matches = pattern.findall(template_text)

    params = []
    seen = set()

    for var_name, default_value in matches:
        if var_name in seen:
            continue
        seen.add(var_name)

        # 猜测参数类型
        param_type = ParamType.TEXT
        if default_value:
            if default_value.lower() in ("true", "false"):
                param_type = ParamType.BOOLEAN
            elif default_value.isdigit():
                param_type = ParamType.INT
            else:
                try:
                    float(default_value)
                    param_type = ParamType.FLOAT
                except ValueError:
                    pass

        params.append(ParamDef(
            name=var_name,
            type=param_type,
            default=default_value if default_value else None,
        ))

    return params


def register_prompt_commands(subparsers: argparse._SubParsersAction) -> None:
    """注册提示词子命令"""
    prompt_parser = subparsers.add_parser("prompt", help="提示词模板管理")
    prompt_sub = prompt_parser.add_subparsers(dest="prompt_command", required=True)

    # prompt list
    list_parser = prompt_sub.add_parser("list", help="列出所有模板")
    list_parser.add_argument("--stage", help="按阶段筛选")
    list_parser.add_argument("--genre", help="按题材筛选")
    list_parser.set_defaults(func=cmd_prompt_list)

    # prompt show
    show_parser = prompt_sub.add_parser("show", help="查看模板详情")
    show_parser.add_argument("template_id", help="模板ID")
    show_parser.set_defaults(func=cmd_prompt_show)

    # prompt create
    create_parser = prompt_sub.add_parser("create", help="创建新模板")
    create_parser.set_defaults(func=cmd_prompt_create)

    # prompt edit
    edit_parser = prompt_sub.add_parser("edit", help="编辑模板")
    edit_parser.add_argument("template_id", help="模板ID")
    edit_parser.set_defaults(func=cmd_prompt_edit)

    # prompt test
    test_parser = prompt_sub.add_parser("test", help="测试模板")
    test_parser.add_argument("template_id", help="模板ID")
    test_parser.set_defaults(func=cmd_prompt_test)

    # prompt examples
    examples_parser = prompt_sub.add_parser("examples", help="管理示例")
    examples_parser.add_argument("template_id", help="模板ID")
    examples_parser.add_argument("action", choices=["list", "add", "delete"], help="操作")
    examples_parser.add_argument("--example-id", help="示例ID (用于删除)")
    examples_parser.set_defaults(func=cmd_prompt_examples)
