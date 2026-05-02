from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .indexer import connect


def get_user_projects(user_id: str, db_path: Path | None = None) -> list[dict[str, Any]]:
    """获取用户的所有项目，按创建时间倒序"""
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT p.*, up.created_at, up.is_default,
                   (SELECT COUNT(DISTINCT chapter) FROM chapters WHERE project_id = p.id) as chapter_count,
                   (SELECT SUM(word_count) FROM chapters WHERE project_id = p.id AND source_type = 'corpus') as total_words,
                   (SELECT AVG(score) FROM reviews WHERE project_id = p.id) as avg_review_score,
                   (SELECT COUNT(*) FROM revision_queue WHERE project_id = p.id AND status = 'open') as open_revisions
            FROM user_projects up
            JOIN projects p ON up.project_id = p.id
            WHERE up.user_id = ?
            ORDER BY up.is_default DESC, up.created_at DESC
            """,
            (user_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def add_user_project(user_id: str, project_id: str, is_default: bool = False, db_path: Path | None = None) -> None:
    """关联用户和项目"""
    with connect(db_path) as conn:
        # 如果设为默认，先取消其他项目的默认状态
        if is_default:
            conn.execute(
                "UPDATE user_projects SET is_default = 0 WHERE user_id = ?",
                (user_id,)
            )

        conn.execute(
            "INSERT OR REPLACE INTO user_projects (user_id, project_id, is_default, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (user_id, project_id, 1 if is_default else 0)
        )
        conn.commit()


def get_default_project(user_id: str, db_path: Path | None = None) -> str | None:
    """获取用户的默认项目ID"""
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT project_id FROM user_projects WHERE user_id = ? AND is_default = 1",
            (user_id,)
        ).fetchone()
        if row:
            return row["project_id"]

        # 如果没有默认项目，返回最新创建的项目
        row = conn.execute(
            "SELECT project_id FROM user_projects WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        ).fetchone()
        return row["project_id"] if row else None


def set_default_project(user_id: str, project_id: str, db_path: Path | None = None) -> None:
    """设置用户的默认项目"""
    with connect(db_path) as conn:
        # 先取消所有默认状态
        conn.execute(
            "UPDATE user_projects SET is_default = 0 WHERE user_id = ?",
            (user_id,)
        )
        # 设置新的默认项目
        conn.execute(
            "UPDATE user_projects SET is_default = 1 WHERE user_id = ? AND project_id = ?",
            (user_id, project_id)
        )
        conn.commit()


def check_project_access(user_id: str, project_id: str, db_path: Path | None = None) -> bool:
    """检查用户是否有权访问项目"""
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM user_projects WHERE user_id = ? AND project_id = ?",
            (user_id, project_id)
        ).fetchone()
        return row is not None


def has_any_project(user_id: str, db_path: Path | None = None) -> bool:
    """检查用户是否有任何项目"""
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM user_projects WHERE user_id = ? LIMIT 1",
            (user_id,)
        ).fetchone()
        return row is not None
