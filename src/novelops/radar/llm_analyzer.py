from __future__ import annotations

from typing import Any

from ..llm import LLMClient
from .hotspot_models import HotspotAnalysis
from .models import RawNovelSignal

SYSTEM_PROMPT = """你是一位资深的中文网文市场热点分析师。你的任务是分析网文作品或题材，提取关键的市场热点要素。

你必须严格按照要求的 JSON 格式输出分析结果，不要添加任何解释或额外文字。"""

USER_PROMPT_TEMPLATE = """请分析以下网文内容，提取热点要素：

{text}

{metadata_section}

请严格按照以下 JSON 格式输出分析结果：
{{
    "genre": "简短题材名，如'仙侠''都市重生''末世囤货'",
    "core_desire": "读者核心欲望，如'被压迫后的逆袭'",
    "hook": "一句话核心钩子",
    "golden_finger": "金手指机制；未知则填'无明显金手指'",
    "reader_emotion": ["短词1", "短词2"],
    "risk": "一句话市场或开局风险"
}}

字段说明：
- genre: 题材名称，2-6个字
- core_desire: 读者阅读此类型作品的核心心理需求
- hook: 最吸引读者的一句话卖点
- golden_finger: 主角的特殊能力或优势；如果看不出明显金手指，填"无明显金手指"
- reader_emotion: 1-5个短词描述读者阅读时的情绪反应
- risk: 市场竞争或开局设计可能存在的风险"""


def _build_metadata_section(metadata: dict[str, Any] | None) -> str:
    if not metadata:
        return ""

    parts = []
    if metadata.get("title"):
        parts.append(f"标题：{metadata['title']}")
    if metadata.get("category"):
        parts.append(f"分类：{metadata['category']}")
    if metadata.get("tags"):
        tags = metadata["tags"]
        if isinstance(tags, list):
            tags = ", ".join(tags)
        parts.append(f"标签：{tags}")
    if metadata.get("platform"):
        parts.append(f"平台：{metadata['platform']}")
    if metadata.get("rank_type"):
        parts.append(f"榜单：{metadata['rank_type']}")

    if not parts:
        return ""

    return "元数据：\n" + "\n".join(parts)


class LLMHotspotAnalyzer:
    """基于 LLM 的热点分析器"""

    VERSION = "llm-1.0.0"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def analyze_text(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> HotspotAnalysis:
        metadata_section = _build_metadata_section(metadata)
        prompt = USER_PROMPT_TEMPLATE.format(
            text=text,
            metadata_section=metadata_section,
        )

        schema = HotspotAnalysis.model_json_schema()
        result = self.llm_client.complete_json(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            stage="radar_analysis",
            schema=schema,
        )

        return HotspotAnalysis.model_validate(result)

    def analyze_signal(self, signal: RawNovelSignal) -> HotspotAnalysis:
        text_parts = [signal.title]
        if signal.description:
            text_parts.append(signal.description)
        if signal.tags:
            text_parts.append("标签：" + ", ".join(signal.tags))

        text = "\n".join(text_parts)

        metadata = {
            "title": signal.title,
            "category": signal.category,
            "tags": signal.tags,
            "platform": signal.platform,
            "rank_type": signal.rank_type,
        }

        return self.analyze_text(text, metadata)

    def analyze_batch(
        self,
        signals: list[RawNovelSignal],
    ) -> list[HotspotAnalysis | None]:
        results: list[HotspotAnalysis | None] = []

        for signal in signals:
            try:
                result = self.analyze_signal(signal)
                results.append(result)
            except Exception:
                results.append(None)

        return results
