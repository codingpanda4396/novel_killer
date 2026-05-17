"""快照CLI命令

支持：
- snapshot create: 创建手动快照
- snapshot list: 列出快照
- snapshot restore: 恢复快照
- snapshot show: 查看快照详情
- snapshot delete: 删除快照
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ..config import default_project_id
from ..paths import project_dir
from ..snapshot.manager import SnapshotManager


def cmd_snapshot_create(args: argparse.Namespace) -> int:
    """创建手动快照"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    manager = SnapshotManager(project_id, project_path)

    description = args.description or "手动快照"
    info = manager.create_snapshot(
        description=description,
        snapshot_type="manual",
    )

    print(f"已创建快照: {info.id}")
    print(f"  描述: {info.description}")
    print(f"  大小: {info.size_bytes / 1024:.1f} KB")
    return 0


def cmd_snapshot_list(args: argparse.Namespace) -> int:
    """列出快照"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    manager = SnapshotManager(project_id, project_path)
    snapshots = manager.list_snapshots(snapshot_type=args.type)

    if not snapshots:
        print("没有快照")
        return 0

    print(f"项目 {project_id} 的快照:")
    print()

    for snap in snapshots:
        type_mark = "[手动]" if snap.type == "manual" else "[自动]"
        print(f"  {snap.id} {type_mark}")
        print(f"    描述: {snap.description}")
        print(f"    时间: {snap.created_at}")
        print(f"    大小: {snap.size_bytes / 1024:.1f} KB")
        print()

    return 0


def cmd_snapshot_show(args: argparse.Namespace) -> int:
    """查看快照详情"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    manager = SnapshotManager(project_id, project_path)
    data = manager.get_snapshot(args.snapshot_id)

    if not data:
        print(f"ERROR: 快照不存在: {args.snapshot_id}", file=sys.stderr)
        return 1

    meta = data.get("_meta", {})
    print(f"快照ID: {meta.get('snapshot_id')}")
    print(f"项目ID: {meta.get('project_id')}")
    print(f"类型: {meta.get('type')}")
    print(f"描述: {meta.get('description')}")
    print(f"创建时间: {meta.get('created_at')}")

    files = data.get("files", {})
    print(f"\n包含文件 ({len(files)}):")
    for rel_path in sorted(files.keys()):
        content = files[rel_path]
        print(f"  - {rel_path} ({len(content)} 字符)")

    return 0


def cmd_snapshot_restore(args: argparse.Namespace) -> int:
    """恢复快照"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    manager = SnapshotManager(project_id, project_path)
    data = manager.get_snapshot(args.snapshot_id)

    if not data:
        print(f"ERROR: 快照不存在: {args.snapshot_id}", file=sys.stderr)
        return 1

    meta = data.get("_meta", {})
    files = data.get("files", {})

    print(f"将恢复快照: {meta.get('description')}")
    print(f"包含 {len(files)} 个文件")

    if not args.yes:
        confirm = input("\n确认恢复？这将覆盖现有文件 (y/N): ").strip().lower()
        if confirm != "y":
            print("已取消")
            return 0

    # 恢复文件
    restored = 0
    for rel_path, content in files.items():
        file_path = project_path / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        restored += 1
        print(f"  已恢复: {rel_path}")

    print(f"\n恢复完成: {restored} 个文件")
    return 0


def cmd_snapshot_delete(args: argparse.Namespace) -> int:
    """删除快照"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    manager = SnapshotManager(project_id, project_path)

    if not args.yes:
        confirm = input(f"确认删除快照 {args.snapshot_id}？(y/N): ").strip().lower()
        if confirm != "y":
            print("已取消")
            return 0

    if manager.delete_snapshot(args.snapshot_id):
        print("已删除快照")
    else:
        print("ERROR: 快照不存在", file=sys.stderr)
        return 1

    return 0


def register_snapshot_commands(subparsers: argparse._SubParsersAction) -> None:
    """注册快照子命令"""
    snapshot_parser = subparsers.add_parser("snapshot", help="项目快照管理")
    snapshot_sub = snapshot_parser.add_subparsers(dest="snapshot_command", required=True)

    # snapshot create
    create_parser = snapshot_sub.add_parser("create", help="创建手动快照")
    create_parser.add_argument("--project", help="Project ID")
    create_parser.add_argument("--description", "-d", help="快照描述")
    create_parser.set_defaults(func=cmd_snapshot_create)

    # snapshot list
    list_parser = snapshot_sub.add_parser("list", help="列出快照")
    list_parser.add_argument("--project", help="Project ID")
    list_parser.add_argument("--type", choices=["auto", "manual"], help="按类型筛选")
    list_parser.set_defaults(func=cmd_snapshot_list)

    # snapshot show
    show_parser = snapshot_sub.add_parser("show", help="查看快照详情")
    show_parser.add_argument("--project", help="Project ID")
    show_parser.add_argument("snapshot_id", help="快照ID")
    show_parser.set_defaults(func=cmd_snapshot_show)

    # snapshot restore
    restore_parser = snapshot_sub.add_parser("restore", help="恢复快照")
    restore_parser.add_argument("--project", help="Project ID")
    restore_parser.add_argument("snapshot_id", help="快照ID")
    restore_parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    restore_parser.set_defaults(func=cmd_snapshot_restore)

    # snapshot delete
    delete_parser = snapshot_sub.add_parser("delete", help="删除快照")
    delete_parser.add_argument("--project", help="Project ID")
    delete_parser.add_argument("snapshot_id", help="快照ID")
    delete_parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    delete_parser.set_defaults(func=cmd_snapshot_delete)
