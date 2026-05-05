from __future__ import annotations

from ..llm import LLMClient
from .analyzer import RuleBasedRadarAnalyzer
from .hotspot_models import HotspotAnalysis
from .llm_analyzer import LLMHotspotAnalyzer
from .models import AnalyzedNovelSignal, RawNovelSignal


class CompositeAnalyzer:
    """组合分析器：整合规则分析和 LLM 分析"""

    def __init__(
        self,
        use_llm: bool = False,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.use_llm = use_llm
        self.rule_analyzer = RuleBasedRadarAnalyzer()
        self.llm_analyzer = LLMHotspotAnalyzer(llm_client) if use_llm else None

    def analyze_one(self, signal: RawNovelSignal) -> AnalyzedNovelSignal:
        base_result = self.rule_analyzer.analyze_one(signal)

        if not self.use_llm or not self.llm_analyzer:
            return base_result

        try:
            llm_result = self.llm_analyzer.analyze_signal(signal)
            return self._merge_results(base_result, llm_result)
        except Exception:
            return base_result

    def analyze(self, signals: list[RawNovelSignal]) -> list[AnalyzedNovelSignal]:
        if not self.use_llm or not self.llm_analyzer:
            return self.rule_analyzer.analyze(signals)

        base_results = self.rule_analyzer.analyze(signals)
        llm_results = self.llm_analyzer.analyze_batch(signals)

        merged: list[AnalyzedNovelSignal] = []
        for base, llm in zip(base_results, llm_results):
            if llm is not None:
                merged.append(self._merge_results(base, llm))
            else:
                merged.append(base)

        return merged

    def _merge_results(
        self,
        base: AnalyzedNovelSignal,
        llm: HotspotAnalysis,
    ) -> AnalyzedNovelSignal:
        return AnalyzedNovelSignal(
            signal_id=base.signal_id,
            source=base.source,
            source_type=base.source_type,
            platform=base.platform,
            rank_type=base.rank_type,
            rank_position=base.rank_position,
            title=base.title,
            author=base.author,
            category=base.category,
            sub_category=base.sub_category,
            tags=base.tags,
            description=base.description,
            hot_score=base.hot_score,
            comment_count=base.comment_count,
            like_count=base.like_count,
            read_count=base.read_count,
            collected_at=base.collected_at,
            raw_payload=base.raw_payload,
            extracted_genre=base.extracted_genre,
            protagonist_template=base.protagonist_template,
            golden_finger=base.golden_finger,
            core_hook=base.core_hook,
            reader_desire=base.reader_desire,
            shuang_points=base.shuang_points,
            risk_points=base.risk_points,
            platform_fit_score=base.platform_fit_score,
            competition_score=base.competition_score,
            writing_difficulty_score=base.writing_difficulty_score,
            commercial_potential_score=base.commercial_potential_score,
            analyzed_at=base.analyzed_at,
            analyzer_version=base.analyzer_version,
            llm_genre=llm.genre,
            llm_core_desire=llm.core_desire,
            llm_hook=llm.hook,
            llm_golden_finger=llm.golden_finger,
            llm_reader_emotion=llm.reader_emotion,
            llm_risk=llm.risk,
        )
