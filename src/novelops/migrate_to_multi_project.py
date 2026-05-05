#!/usr/bin/env python3
"""
数据迁移脚本：将现有的邀请码-项目绑定迁移到用户-项目关联模型

运行方式：
    python -m novelops.migrate_to_multi_project
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from novelops.config import load_invites
from novelops.indexer import connect, rebuild_index
from novelops.user import add_user_project


def migrate_existing_projects() -> None:
    """将现有的邀请码-项目绑定迁移到用户-项目关联"""
    print("=" * 60)
    print("NovelOps 数据迁移：邀请码-项目 → 用户-项目")
    print("=" * 60)

    invites = load_invites()
    if not invites:
        print("未找到邀请码配置，跳过迁移")
        return

    print(f"\n找到 {len(invites)} 个邀请码配置")

    migrated_count = 0
    skipped_count = 0

    with connect() as conn:
        for code, info in invites.items():
            # 检查是否是旧格式（包含project字段）
            if "project" in info and "user_id" not in info:
                project_id = info["project"]
                user_id = project_id  # 使用项目ID作为用户ID
                username = info.get("label", project_id)

                print(f"\n处理邀请码: {code}")
                print(f"  项目ID: {project_id}")
                print(f"  用户ID: {user_id}")
                print(f"  用户名: {username}")

                # 检查项目是否存在
                project = conn.execute(
                    "SELECT id FROM projects WHERE id = ?",
                    (project_id,)
                ).fetchone()

                if not project:
                    print(f"  ⚠ 项目不存在，跳过")
                    skipped_count += 1
                    continue

                # 检查是否已经关联
                existing = conn.execute(
                    "SELECT 1 FROM user_projects WHERE user_id = ? AND project_id = ?",
                    (user_id, project_id)
                ).fetchone()

                if existing:
                    print(f"  ✓ 已关联，跳过")
                    skipped_count += 1
                    continue

                # 创建用户-项目关联
                add_user_project(user_id, project_id, is_default=True)
                print(f"  ✓ 迁移成功")
                migrated_count += 1

            elif "user_id" in info:
                print(f"\n邀请码 {code} 已是新格式，跳过")
                skipped_count += 1
            else:
                print(f"\n⚠ 邀请码 {code} 格式不正确，跳过")
                skipped_count += 1

    print("\n" + "=" * 60)
    print(f"迁移完成：成功 {migrated_count} 个，跳过 {skipped_count} 个")
    print("=" * 60)

    if migrated_count > 0:
        print("\n建议：")
        print("1. 更新 config/novelops.json 中的邀请码配置为新格式")
        print("2. 重建索引：python -m novelops.cli index")
        print("3. 重启服务：sudo systemctl restart novelops")


def main() -> int:
    try:
        migrate_existing_projects()
        return 0
    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
