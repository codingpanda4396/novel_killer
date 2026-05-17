"""提示词SQLite存储层

管理提示词模板、示例的CRUD操作
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from ..db.engine import get_engine
from .engine import ParamDef, ParamType, PromptEngine, PromptTemplate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PromptStore:
    """提示词模板存储"""

    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path
        self._ensure_tables()

    def _get_engine(self):
        return get_engine(self._db_path)

    def _ensure_tables(self):
        """确保表存在"""
        engine = self._get_engine()
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS prompt_templates (
                    id TEXT PRIMARY KEY,
                    stage TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    system_prompt TEXT,
                    user_prompt_template TEXT,
                    params_schema TEXT,
                    genre TEXT,
                    is_default INTEGER DEFAULT 0,
                    version INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS prompt_examples (
                    id TEXT PRIMARY KEY,
                    template_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    input_context TEXT,
                    expected_output TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (template_id) REFERENCES prompt_templates(id)
                )
            """))
            conn.commit()

    def get(self, template_id: str) -> PromptTemplate | None:
        """获取模板"""
        engine = self._get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM prompt_templates WHERE id = :id"),
                {"id": template_id}
            ).fetchone()
            if not row:
                return None
            return self._row_to_template(row)

    def list_all(self, stage: str | None = None, genre: str | None = None) -> list[PromptTemplate]:
        """列出所有模板"""
        engine = self._get_engine()
        query = "SELECT * FROM prompt_templates WHERE 1=1"
        params: dict[str, Any] = {}

        if stage:
            query += " AND stage = :stage"
            params["stage"] = stage
        if genre:
            query += " AND (genre = :genre OR genre IS NULL)"
            params["genre"] = genre

        query += " ORDER BY stage, name"

        with engine.connect() as conn:
            rows = conn.execute(text(query), params).fetchall()
            return [self._row_to_template(row) for row in rows]

    def get_for_stage(self, stage: str, genre: str | None = None) -> PromptTemplate | None:
        """获取指定阶段的默认模板"""
        engine = self._get_engine()
        params: dict[str, Any] = {"stage": stage}

        if genre:
            query = "SELECT * FROM prompt_templates WHERE stage = :stage AND is_default = 1 AND (genre = :genre OR genre IS NULL) ORDER BY genre DESC LIMIT 1"
            params["genre"] = genre
        else:
            query = "SELECT * FROM prompt_templates WHERE stage = :stage AND is_default = 1 LIMIT 1"

        with engine.connect() as conn:
            row = conn.execute(text(query), params).fetchone()
            if row:
                return self._row_to_template(row)

            # 没有默认的，返回第一个
            if genre:
                query = "SELECT * FROM prompt_templates WHERE stage = :stage AND (genre = :genre OR genre IS NULL) LIMIT 1"
            else:
                query = "SELECT * FROM prompt_templates WHERE stage = :stage LIMIT 1"
            row = conn.execute(text(query), params).fetchone()
            return self._row_to_template(row) if row else None

    def create(self, template: PromptTemplate) -> PromptTemplate:
        """创建模板"""
        if not template.id:
            template.id = f"{template.stage}_{uuid.uuid4().hex[:8]}"

        engine = self._get_engine()
        now = _now()

        with engine.connect() as conn:
            conn.execute(
                text("""INSERT INTO prompt_templates
                   (id, stage, name, description, system_prompt, user_prompt_template,
                    params_schema, genre, is_default, version, created_at, updated_at)
                   VALUES (:id, :stage, :name, :description, :system_prompt, :user_prompt_template,
                    :params_schema, :genre, :is_default, :version, :created_at, :updated_at)"""),
                {
                    "id": template.id,
                    "stage": template.stage,
                    "name": template.name,
                    "description": template.description,
                    "system_prompt": template.system_prompt,
                    "user_prompt_template": template.user_prompt_template,
                    "params_schema": json.dumps([p.to_dict() for p in template.params], ensure_ascii=False),
                    "genre": template.genre,
                    "is_default": 1 if template.is_default else 0,
                    "version": template.version,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            conn.commit()

        return template

    def update(self, template: PromptTemplate) -> PromptTemplate:
        """更新模板"""
        engine = self._get_engine()
        template.version += 1

        with engine.connect() as conn:
            conn.execute(
                text("""UPDATE prompt_templates
                   SET name = :name, description = :description, system_prompt = :system_prompt,
                       user_prompt_template = :user_prompt_template, params_schema = :params_schema,
                       genre = :genre, is_default = :is_default, version = :version, updated_at = :updated_at
                   WHERE id = :id"""),
                {
                    "name": template.name,
                    "description": template.description,
                    "system_prompt": template.system_prompt,
                    "user_prompt_template": template.user_prompt_template,
                    "params_schema": json.dumps([p.to_dict() for p in template.params], ensure_ascii=False),
                    "genre": template.genre,
                    "is_default": 1 if template.is_default else 0,
                    "version": template.version,
                    "updated_at": _now(),
                    "id": template.id,
                }
            )
            conn.commit()

        return template

    def delete(self, template_id: str) -> bool:
        """删除模板"""
        engine = self._get_engine()
        with engine.connect() as conn:
            # 先删除关联的示例
            conn.execute(
                text("DELETE FROM prompt_examples WHERE template_id = :id"),
                {"id": template_id}
            )
            result = conn.execute(
                text("DELETE FROM prompt_templates WHERE id = :id"),
                {"id": template_id}
            )
            conn.commit()
            return result.rowcount > 0

    def set_default(self, template_id: str, stage: str) -> None:
        """设置为指定阶段的默认模板"""
        engine = self._get_engine()
        with engine.connect() as conn:
            # 取消同阶段其他默认
            conn.execute(
                text("UPDATE prompt_templates SET is_default = 0 WHERE stage = :stage"),
                {"stage": stage}
            )
            # 设置新的默认
            conn.execute(
                text("UPDATE prompt_templates SET is_default = 1 WHERE id = :id"),
                {"id": template_id}
            )
            conn.commit()

    # 示例管理
    def get_examples(self, template_id: str) -> list[dict[str, Any]]:
        """获取模板的示例"""
        engine = self._get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM prompt_examples WHERE template_id = :id ORDER BY created_at"),
                {"id": template_id}
            ).fetchall()
            return [
                {
                    "id": row[0],
                    "template_id": row[1],
                    "type": row[2],
                    "input_context": row[3],
                    "expected_output": row[4],
                    "notes": row[5],
                }
                for row in rows
            ]

    def add_example(
        self,
        template_id: str,
        example_type: str,
        input_context: str,
        expected_output: str,
        notes: str = "",
    ) -> str:
        """添加示例"""
        example_id = f"ex_{uuid.uuid4().hex[:8]}"
        engine = self._get_engine()

        with engine.connect() as conn:
            conn.execute(
                text("""INSERT INTO prompt_examples
                   (id, template_id, type, input_context, expected_output, notes)
                   VALUES (:id, :template_id, :type, :input_context, :expected_output, :notes)"""),
                {
                    "id": example_id,
                    "template_id": template_id,
                    "type": example_type,
                    "input_context": input_context,
                    "expected_output": expected_output,
                    "notes": notes,
                }
            )
            conn.commit()

        return example_id

    def delete_example(self, example_id: str) -> bool:
        """删除示例"""
        engine = self._get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("DELETE FROM prompt_examples WHERE id = :id"),
                {"id": example_id}
            )
            conn.commit()
            return result.rowcount > 0

    def create_engine_for_stage(self, stage: str, genre: str | None = None) -> PromptEngine | None:
        """为指定阶段创建引擎"""
        template = self.get_for_stage(stage, genre)
        if not template:
            return None
        return PromptEngine(template)

    def _row_to_template(self, row) -> PromptTemplate:
        """将数据库行转换为模板"""
        params_data = json.loads(row[6]) if row[6] else []
        return PromptTemplate(
            id=row[0],
            stage=row[1],
            name=row[2],
            description=row[3] or "",
            system_prompt=row[4] or "",
            user_prompt_template=row[5] or "",
            params=[ParamDef.from_dict(p) for p in params_data],
            genre=row[7],
            is_default=bool(row[8]),
            version=row[9] or 1,
        )
