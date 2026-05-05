from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RawNovelSignal:
    """原始网文需求信号"""
    signal_id: str                    # 唯一标识
    source: str                       # fanqie / qimao / qidian / douyin / manual
    source_type: str                  # ranking / search / comment / keyword / manual
    platform: str                     # 番茄 / 七猫 / 起点 / 抖音
    rank_type: str | None = None      # 仙侠热榜 / 新书榜 / 完结榜
    rank_position: int | None = None  # 榜单位置
    title: str = ""                   # 小说标题
    author: str | None = None         # 作者
    category: str | None = None       # 分类
    sub_category: str | None = None   # 子分类
    tags: list[str] = field(default_factory=list)  # 标签列表
    description: str | None = None    # 简介
    hot_score: float | None = None    # 热度分数
    comment_count: int | None = None  # 评论数
    like_count: int | None = None     # 点赞数
    read_count: int | None = None     # 阅读数
    collected_at: str = ""            # 采集时间（ISO 8601）
    raw_payload: dict[str, Any] = field(default_factory=dict)  # 原始数据


@dataclass(frozen=True)
class AnalyzedNovelSignal:
    """分析后的网文需求信号"""
    signal_id: str
    source: str
    source_type: str
    platform: str
    rank_type: str | None = None
    rank_position: int | None = None
    title: str = ""
    author: str | None = None
    category: str | None = None
    sub_category: str | None = None
    tags: list[str] = field(default_factory=list)
    description: str | None = None
    hot_score: float | None = None
    comment_count: int | None = None
    like_count: int | None = None
    read_count: int | None = None
    collected_at: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)
    
    # 分析结果
    extracted_genre: str | None = None          # 提取的题材
    protagonist_template: str | None = None     # 主角模板
    golden_finger: str | None = None            # 金手指类型
    core_hook: str | None = None                # 核心钩子
    reader_desire: str | None = None            # 读者欲望
    shuang_points: list[str] = field(default_factory=list)  # 爽点列表
    risk_points: list[str] = field(default_factory=list)    # 毒点风险
    
    # 评分
    platform_fit_score: float = 0.0         # 平台适配度 0-100
    competition_score: float = 0.0          # 竞争度 0-100
    writing_difficulty_score: float = 0.0   # 写作难度 0-100
    commercial_potential_score: float = 0.0 # 商业潜力 0-100
    
    analyzed_at: str = ""                   # 分析时间
    analyzer_version: str = ""              # 分析器版本


@dataclass(frozen=True)
class TopicOpportunity:
    """选题机会"""
    topic_id: str                     # 选题 ID
    topic_name: str                   # 选题名称
    target_platform: str              # 目标平台
    target_reader: str                # 目标读者
    core_tags: list[str]              # 核心标签
    evidence_titles: list[str]        # 证据样本标题
    
    # 综合评分
    hot_score: float = 0.0            # 热度分数
    competition_score: float = 0.0    # 竞争度
    platform_fit_score: float = 0.0   # 平台适配度
    writing_difficulty_score: float = 0.0  # 写作难度
    final_score: float = 0.0          # 最终评分
    
    # 创作建议
    opening_hook: str = ""            # 推荐开篇钩子
    suggested_story_seed: str = ""    # 建议故事种子
    risks: list[str] = field(default_factory=list)  # 主要风险
    
    generated_at: str = ""            # 生成时间


@dataclass(frozen=True)
class CompetitorAnalysis:
    """竞品分析"""
    genre: str                        # 题材
    total_count: int                  # 同题材作品数
    top_titles: list[str]             # Top作品标题
    common_golden_fingers: list[str]  # 常见金手指
    common_shuang_points: list[str]   # 常见爽点
    average_hot_score: float          # 平均热度
    competition_level: str            # 竞争等级: low/medium/high
    differentiation_opportunities: list[str]  # 差异化机会
    analyzed_at: str = ""


def to_dict(value: Any) -> dict[str, Any]:
    return asdict(value)
