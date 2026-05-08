from __future__ import annotations

from pydantic import BaseModel, Field


class DemandStatement(BaseModel):
    """A synthesized demand cluster from Radar signals."""
    cluster_name: str = Field(description="欲望集群名称，如'逆袭欲'")
    desire_statement: str = Field(description="一句话欲望陈述")
    frequency: int = Field(description="出现频次")
    representative_titles: list[str] = Field(description="代表作品标题", max_length=5)
    linked_emotions: list[str] = Field(description="关联情绪词", max_length=5)
    recommended_golden_fingers: list[str] = Field(description="推荐金手指", max_length=3)
    risk: str = Field(description="市场或开局风险")


class ReaderPersonaProfile(BaseModel):
    """A synthesized reader persona."""
    name: str = Field(description="persona 标识名，如 fast_food")
    display_name: str = Field(description="显示名，如'快餐读者'")
    wants: list[str] = Field(description="想要看到的元素", max_length=5)
    dislikes: list[str] = Field(description="讨厌看到的元素", max_length=5)
    typical_emotions: list[str] = Field(description="典型情绪反应", max_length=5)
    representative_works: list[str] = Field(description="代表作品", max_length=5)
    share_pct: float = Field(description="预估占比百分比", ge=0, le=100)


class TropeEntry(BaseModel):
    """A trope/meme in the genre."""
    name: str = Field(description="套路名称")
    frequency: int = Field(description="出现频次")
    platform_distribution: dict[str, int] = Field(default_factory=dict, description="平台分布")
    chapter_position: str = Field(default="", description="常见章节位置")
    representative_works: list[str] = Field(default_factory=list, max_length=5)


class CompetitorPattern(BaseModel):
    """Competitor pattern analysis."""
    genre: str = Field(description="题材")
    opening_hooks: list[str] = Field(description="常见开篇钩子", max_length=5)
    saturation_warnings: list[str] = Field(description="饱和警告", max_length=3)


class DesireSynthesisResult(BaseModel):
    """Complete result of desire synthesis."""
    demands: list[DemandStatement]
    personas: list[ReaderPersonaProfile]
    tropes: list[TropeEntry]
    competitors: list[CompetitorPattern]
    signal_count: int
    window_days: int
    max_analyzed_at: str
