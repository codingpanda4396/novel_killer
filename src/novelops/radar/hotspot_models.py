from __future__ import annotations

from pydantic import BaseModel, Field


class HotspotAnalysis(BaseModel):
    """LLM 热点分析结果"""

    genre: str = Field(
        description="简短题材名，如'仙侠''都市重生''末世囤货'"
    )
    core_desire: str = Field(
        description="读者核心欲望，如'被压迫后的逆袭'"
    )
    hook: str = Field(
        description="一句话核心钩子"
    )
    golden_finger: str = Field(
        description="金手指机制；未知则填'无明显金手指'"
    )
    reader_emotion: list[str] = Field(
        description="1-5 个短词",
        max_length=5,
    )
    risk: str = Field(
        description="一句话市场或开局风险"
    )
