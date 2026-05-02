#!/usr/bin/env python3
"""
用户项目管理功能测试
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from novelops.indexer import connect
from novelops.user import (
    get_user_projects,
    add_user_project,
    get_default_project,
    set_default_project,
    check_project_access,
    has_any_project,
)


class TestUserProjects(unittest.TestCase):
    def setUp(self):
        """每个测试前创建临时数据库"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        # 初始化数据库
        with connect(self.db_path) as conn:
            # 创建测试项目
            conn.execute(
                "INSERT INTO projects (id, name, genre, path) VALUES (?, ?, ?, ?)",
                ("test_project_1", "测试项目1", "仙侠", "/tmp/test1")
            )
            conn.execute(
                "INSERT INTO projects (id, name, genre, path) VALUES (?, ?, ?, ?)",
                ("test_project_2", "测试项目2", "玄幻", "/tmp/test2")
            )
            conn.commit()

    def tearDown(self):
        """每个测试后删除临时数据库"""
        if self.db_path.exists():
            self.db_path.unlink()

    def test_add_user_project(self):
        """测试添加用户项目关联"""
        with connect(self.db_path) as conn:
            # 添加关联
            conn.execute(
                "INSERT INTO user_projects (user_id, project_id) VALUES (?, ?)",
                ("user1", "test_project_1")
            )
            conn.commit()

            # 验证关联
            row = conn.execute(
                "SELECT * FROM user_projects WHERE user_id = ? AND project_id = ?",
                ("user1", "test_project_1")
            ).fetchone()
            self.assertIsNotNone(row)

    def test_check_project_access(self):
        """测试权限检查"""
        with connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO user_projects (user_id, project_id) VALUES (?, ?)",
                ("user1", "test_project_1")
            )
            conn.commit()

        # 有权限
        self.assertTrue(check_project_access("user1", "test_project_1", self.db_path))
        # 无权限
        self.assertFalse(check_project_access("user1", "test_project_2", self.db_path))
        self.assertFalse(check_project_access("user2", "test_project_1", self.db_path))

    def test_has_any_project(self):
        """测试用户是否有项目"""
        # 用户1没有项目
        self.assertFalse(has_any_project("user1", self.db_path))

        with connect(self.db_path) as conn:
            # 添加项目
            conn.execute(
                "INSERT INTO user_projects (user_id, project_id) VALUES (?, ?)",
                ("user1", "test_project_1")
            )
            conn.commit()

        # 用户1有项目
        self.assertTrue(has_any_project("user1", self.db_path))

    def test_default_project(self):
        """测试默认项目"""
        with connect(self.db_path) as conn:
            # 添加两个项目
            conn.execute(
                "INSERT INTO user_projects (user_id, project_id, is_default) VALUES (?, ?, ?)",
                ("user1", "test_project_1", 0)
            )
            conn.execute(
                "INSERT INTO user_projects (user_id, project_id, is_default) VALUES (?, ?, ?)",
                ("user1", "test_project_2", 1)
            )
            conn.commit()

        # 获取默认项目
        default = get_default_project("user1", self.db_path)
        self.assertEqual(default, "test_project_2")


if __name__ == "__main__":
    unittest.main()
