"""题材包管理器

管理不同网文题材的提示词风格和参数
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..paths import CONFIG_DIR


GENRE_PACKS_DIR = CONFIG_DIR / "genre_packs"


@dataclass
class GenrePack:
    """题材包"""
    id: str
    name: str
    display_name: str
    description: str
    style_guide: str
    default_params: dict[str, Any] = field(default_factory=dict)
    prompt_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    vocabulary: list[str] = field(default_factory=list)
    tropes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "style_guide": self.style_guide,
            "default_params": self.default_params,
            "prompt_overrides": self.prompt_overrides,
            "vocabulary": self.vocabulary,
            "tropes": self.tropes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenrePack:
        return cls(
            id=data["id"],
            name=data["name"],
            display_name=data["display_name"],
            description=data.get("description", ""),
            style_guide=data.get("style_guide", ""),
            default_params=data.get("default_params", {}),
            prompt_overrides=data.get("prompt_overrides", {}),
            vocabulary=data.get("vocabulary", []),
            tropes=data.get("tropes", []),
        )


class GenrePackManager:
    """题材包管理器"""

    def __init__(self, packs_dir: Path | None = None):
        self._packs_dir = packs_dir or GENRE_PACKS_DIR
        self._packs_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, GenrePack] = {}

    def list_packs(self) -> list[GenrePack]:
        """列出所有题材包"""
        packs = []
        for file_path in self._packs_dir.glob("*.json"):
            try:
                pack = self._load_pack(file_path)
                packs.append(pack)
            except Exception:
                continue

        # 如果没有自定义的，返回内置的
        if not packs:
            packs = list(_BUILTIN_PACKS.values())

        return sorted(packs, key=lambda p: p.name)

    def get_pack(self, pack_id: str) -> GenrePack | None:
        """获取题材包"""
        # 先检查缓存
        if pack_id in self._cache:
            return self._cache[pack_id]

        # 尝试从文件加载
        file_path = self._packs_dir / f"{pack_id}.json"
        if file_path.exists():
            pack = self._load_pack(file_path)
            self._cache[pack_id] = pack
            return pack

        # 尝试内置的
        if pack_id in _BUILTIN_PACKS:
            return _BUILTIN_PACKS[pack_id]

        return None

    def save_pack(self, pack: GenrePack) -> None:
        """保存题材包"""
        file_path = self._packs_dir / f"{pack.id}.json"
        file_path.write_text(
            json.dumps(pack.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._cache[pack.id] = pack

    def delete_pack(self, pack_id: str) -> bool:
        """删除题材包"""
        file_path = self._packs_dir / f"{pack_id}.json"
        if file_path.exists():
            file_path.unlink()
            self._cache.pop(pack_id, None)
            return True
        return False

    def get_default_params(self, pack_id: str) -> dict[str, Any]:
        """获取题材包的默认参数"""
        pack = self.get_pack(pack_id)
        if not pack:
            return {}
        return pack.default_params

    def get_prompt_override(self, pack_id: str, stage: str) -> dict[str, Any] | None:
        """获取题材包对特定阶段的提示词覆盖"""
        pack = self.get_pack(pack_id)
        if not pack:
            return None
        return pack.prompt_overrides.get(stage)

    def _load_pack(self, file_path: Path) -> GenrePack:
        """从文件加载题材包"""
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return GenrePack.from_dict(data)


# 内置题材包
_BUILTIN_PACKS: dict[str, GenrePack] = {}


def _init_builtin_packs():
    """初始化内置题材包"""
    global _BUILTIN_PACKS

    packs = [
        GenrePack(
            id="xianxia",
            name="xianxia",
            display_name="仙侠修真",
            description="修仙、渡劫、宗门、法宝等仙侠题材",
            style_guide="""仙侠小说风格指南：
1. 语言风格：古风典雅，适当使用文言词汇，但保持易懂
2. 核心元素：修炼体系、宗门势力、法宝丹药、渡劫飞升
3. 爽点设计：打脸、突破、获得传承、以弱胜强
4. 常用词汇：灵气、真元、神识、道友、前辈、晚辈、宗门、长老、秘境、机缘
5. 节奏特点：前期铺垫修炼，中期宗门争斗，后期大能对决""",
            default_params={
                "genre_style": "仙侠修真",
                "min_words": 2000,
                "max_words": 3500,
                "tone": "古风典雅",
                "pacing": "渐进式",
            },
            vocabulary=["灵气", "真元", "神识", "道友", "前辈", "宗门", "长老", "秘境", "机缘", "渡劫", "法宝", "丹药", "阵法", "功法"],
            tropes=["废材逆袭", "宗门大比", "秘境探险", "以弱胜强", "获得传承", "打脸"],
        ),
        GenrePack(
            id="romance",
            name="romance",
            display_name="现代言情",
            description="都市爱情、甜宠、虐恋等言情题材",
            style_guide="""现代言情风格指南：
1. 语言风格：清新自然，对话感强，情感细腻
2. 核心元素：男女主互动、情感发展、误会冲突、甜蜜时刻
3. 爽点设计：甜蜜互动、误会解除、身份揭秘、宠溺场景
4. 常用词汇：心跳、脸红、温柔、霸道、宠溺、吃醋、表白、约会
5. 节奏特点：相遇→误会→相知→冲突→和解→在一起""",
            default_params={
                "genre_style": "现代言情",
                "min_words": 1800,
                "max_words": 3000,
                "tone": "清新甜蜜",
                "pacing": "情感驱动",
            },
            vocabulary=["心跳", "脸红", "温柔", "霸道", "宠溺", "吃醋", "表白", "约会", "牵手", "拥抱", "亲吻", "思念"],
            tropes=["先婚后爱", "青梅竹马", "霸道总裁", "破镜重圆", "暗恋成真", "契约婚姻"],
        ),
        GenrePack(
            id="suspense",
            name="suspense",
            display_name="悬疑推理",
            description="破案、推理、惊悚等悬疑题材",
            style_guide="""悬疑推理风格指南：
1. 语言风格：简洁有力，节奏紧凑，细节丰富
2. 核心元素：案件、线索、推理、反转、真相
3. 爽点设计：推理成功、真相大白、智商碾压、反转震撼
4. 常用词汇：线索、嫌疑人、动机、证据、推理、真相、凶手、诡计
5. 节奏特点：案发→调查→推理→反转→破案""",
            default_params={
                "genre_style": "悬疑推理",
                "min_words": 2000,
                "max_words": 3200,
                "tone": "紧张悬疑",
                "pacing": "快节奏",
            },
            vocabulary=["线索", "嫌疑人", "动机", "证据", "推理", "真相", "凶手", "诡计", "密室", "不在场证明", "心理侧写"],
            tropes=["密室杀人", "不可能犯罪", "连环杀手", "身份反转", "时间诡计", "叙述性诡计"],
        ),
        GenrePack(
            id="urban",
            name="urban",
            display_name="都市异能",
            description="都市背景下的超能力、系统流等题材",
            style_guide="""都市异能风格指南：
1. 语言风格：现代都市感，接地气，爽感强
2. 核心元素：异能觉醒、系统任务、都市冒险、势力争斗
3. 爽点设计：能力升级、打脸装逼、财富积累、势力扩张
4. 常用词汇：异能、系统、任务、升级、属性、技能、副本、Boss
5. 节奏特点：觉醒→升级→挑战→更强→更大的挑战""",
            default_params={
                "genre_style": "都市异能",
                "min_words": 1800,
                "max_words": 3000,
                "tone": "爽快直接",
                "pacing": "快节奏",
            },
            vocabulary=["异能", "系统", "任务", "升级", "属性", "技能", "副本", "Boss", "觉醒", "进化", "血脉"],
            tropes=["系统流", "重生复仇", "透视眼", "读心术", "时间暂停", "空间异能"],
        ),
    ]

    for pack in packs:
        _BUILTIN_PACKS[pack.id] = pack


# 初始化内置题材包
_init_builtin_packs()
