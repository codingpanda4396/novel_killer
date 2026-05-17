"""细粒度世界观设定管理

将bible拆分为结构化数据，支持独立AI生成和编辑
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from ..db.engine import get_engine


# 世界观设定分类
SETTING_CATEGORIES = {
    "origin": {
        "name": "世界起源",
        "description": "世界的基础设定和起源故事",
        "fields": ["creation_myth", "world_type", "magic_system_origin", "historical_eras"],
    },
    "environment": {
        "name": "自然环境",
        "description": "地理、气候、生态系统",
        "fields": ["geography", "climate", "flora_fauna", "natural_resources", "landmarks"],
    },
    "culture": {
        "name": "人文环境",
        "description": "社会结构、文化、政治体系",
        "fields": ["social_structure", "government", "religion", "economy", "education", "military", "customs"],
    },
    "power_system": {
        "name": "力量体系",
        "description": "修炼、能力、等级系统",
        "fields": ["system_type", "levels", "abilities", "limitations", "cultivation_methods"],
    },
    "character": {
        "name": "角色设定",
        "description": "主要角色的详细设定",
        "fields": ["name", "background", "personality", "appearance", "abilities", "relationships", "arc"],
    },
    "plot": {
        "name": "剧情设定",
        "description": "核心冲突、主线、伏笔",
        "fields": ["main_conflict", "subplots", "foreshadowing", "themes"],
    },
}


@dataclass
class WorldSetting:
    """单个世界观设定"""
    id: str | None = None
    project_id: str = ""
    category: str = ""
    key: str = ""
    value: str = ""
    description: str = ""
    ai_generated: bool = False
    last_generated_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "category": self.category,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "ai_generated": self.ai_generated,
            "last_generated_at": self.last_generated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorldSetting:
        return cls(
            id=data.get("id"),
            project_id=data.get("project_id", ""),
            category=data.get("category", ""),
            key=data.get("key", ""),
            value=data.get("value", ""),
            description=data.get("description", ""),
            ai_generated=data.get("ai_generated", False),
            last_generated_at=data.get("last_generated_at"),
            metadata=data.get("metadata", {}),
        )


class WorldSettings:
    """世界观设定管理器"""

    def __init__(self, project_id: str, project_path: Path | None = None):
        self.project_id = project_id
        self.project_path = project_path
        self._ensure_table()

    def _get_engine(self):
        return get_engine()

    def _ensure_table(self):
        """确保表存在"""
        engine = self._get_engine()
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS world_settings (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    description TEXT,
                    ai_generated INTEGER DEFAULT 0,
                    last_generated_at TEXT,
                    metadata TEXT,
                    UNIQUE(project_id, category, key)
                )
            """))
            conn.commit()

    def get(self, category: str, key: str) -> WorldSetting | None:
        """获取单个设定"""
        engine = self._get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                text("""SELECT * FROM world_settings
                     WHERE project_id = :project_id AND category = :category AND key = :key"""),
                {"project_id": self.project_id, "category": category, "key": key}
            ).fetchone()
            if not row:
                return None
            return self._row_to_setting(row)

    def list_category(self, category: str) -> list[WorldSetting]:
        """列出分类下的所有设定"""
        engine = self._get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text("""SELECT * FROM world_settings
                     WHERE project_id = :project_id AND category = :category
                     ORDER BY key"""),
                {"project_id": self.project_id, "category": category}
            ).fetchall()
            return [self._row_to_setting(row) for row in rows]

    def list_all(self) -> list[WorldSetting]:
        """列出项目的所有设定"""
        engine = self._get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text("""SELECT * FROM world_settings
                     WHERE project_id = :project_id
                     ORDER BY category, key"""),
                {"project_id": self.project_id}
            ).fetchall()
            return [self._row_to_setting(row) for row in rows]

    def set(
        self,
        category: str,
        key: str,
        value: str,
        description: str = "",
        ai_generated: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> WorldSetting:
        """设置设定值"""
        engine = self._get_engine()
        now = datetime.now(timezone.utc).isoformat()
        setting_id = f"{self.project_id}_{category}_{key}"

        with engine.connect() as conn:
            # 尝试更新
            result = conn.execute(
                text("""UPDATE world_settings
                     SET value = :value, description = :description,
                         ai_generated = :ai_generated, last_generated_at = :last_generated_at,
                         metadata = :metadata
                     WHERE id = :id"""),
                {
                    "id": setting_id,
                    "value": value,
                    "description": description,
                    "ai_generated": 1 if ai_generated else 0,
                    "last_generated_at": now if ai_generated else None,
                    "metadata": json.dumps(metadata or {}, ensure_ascii=False),
                }
            )

            if result.rowcount == 0:
                # 不存在，插入
                conn.execute(
                    text("""INSERT INTO world_settings
                         (id, project_id, category, key, value, description,
                          ai_generated, last_generated_at, metadata)
                         VALUES (:id, :project_id, :category, :key, :value, :description,
                          :ai_generated, :last_generated_at, :metadata)"""),
                    {
                        "id": setting_id,
                        "project_id": self.project_id,
                        "category": category,
                        "key": key,
                        "value": value,
                        "description": description,
                        "ai_generated": 1 if ai_generated else 0,
                        "last_generated_at": now if ai_generated else None,
                        "metadata": json.dumps(metadata or {}, ensure_ascii=False),
                    }
                )

            conn.commit()

        return WorldSetting(
            id=setting_id,
            project_id=self.project_id,
            category=category,
            key=key,
            value=value,
            description=description,
            ai_generated=ai_generated,
            last_generated_at=now if ai_generated else None,
            metadata=metadata or {},
        )

    def delete(self, category: str, key: str) -> bool:
        """删除设定"""
        engine = self._get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("""DELETE FROM world_settings
                     WHERE project_id = :project_id AND category = :category AND key = :key"""),
                {"project_id": self.project_id, "category": category, "key": key}
            )
            conn.commit()
            return result.rowcount > 0

    def get_category_summary(self, category: str) -> str:
        """获取分类的文本摘要"""
        settings = self.list_category(category)
        if not settings:
            return ""

        lines = []
        cat_info = SETTING_CATEGORIES.get(category, {})
        lines.append(f"## {cat_info.get('name', category)}")
        lines.append("")

        for setting in settings:
            if setting.value:
                lines.append(f"### {setting.key}")
                if setting.description:
                    lines.append(f"*{setting.description}*")
                lines.append("")
                lines.append(setting.value)
                lines.append("")

        return "\n".join(lines)

    def get_full_bible(self) -> str:
        """生成完整的bible文本"""
        sections = []
        for category in SETTING_CATEGORIES:
            summary = self.get_category_summary(category)
            if summary:
                sections.append(summary)

        return "\n\n---\n\n".join(sections)

    def import_from_bible(self, bible_path: Path) -> int:
        """从现有的bible文件导入设定"""
        if not bible_path.exists():
            return 0

        content = bible_path.read_text(encoding="utf-8")

        # 简单的解析：按## 分割章节
        sections = re.split(r'^## ', content, flags=re.MULTILINE)

        imported = 0
        for section in sections:
            if not section.strip():
                continue

            # 提取标题和内容
            lines = section.strip().split('\n', 1)
            title = lines[0].strip()
            content_text = lines[1].strip() if len(lines) > 1 else ""

            # 映射到分类
            category = self._map_title_to_category(title)
            if category:
                self.set(
                    category=category,
                    key=title,
                    value=content_text,
                    description=f"从bible导入: {title}",
                )
                imported += 1

        return imported

    def export_to_file(self, output_path: Path) -> None:
        """导出设定到文件"""
        bible_text = self.get_full_bible()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(bible_text, encoding="utf-8")

    def _map_title_to_category(self, title: str) -> str | None:
        """将标题映射到分类"""
        title_lower = title.lower()

        if any(kw in title_lower for kw in ["起源", "创世", "历史", "origin"]):
            return "origin"
        if any(kw in title_lower for kw in ["地理", "环境", "气候", "自然", "environment"]):
            return "environment"
        if any(kw in title_lower for kw in ["社会", "文化", "政治", "经济", "宗教", "culture"]):
            return "culture"
        if any(kw in title_lower for kw in ["力量", "修炼", "能力", "体系", "power"]):
            return "power_system"
        if any(kw in title_lower for kw in ["角色", "人物", "主角", "character"]):
            return "character"
        if any(kw in title_lower for kw in ["剧情", "冲突", "主线", "plot"]):
            return "plot"

        return "culture"  # 默认归类为文化

    def _row_to_setting(self, row) -> WorldSetting:
        """将数据库行转换为设定"""
        return WorldSetting(
            id=row[0],
            project_id=row[1],
            category=row[2],
            key=row[3],
            value=row[4] or "",
            description=row[5] or "",
            ai_generated=bool(row[6]),
            last_generated_at=row[7],
            metadata=json.loads(row[8]) if row[8] else {},
        )
