from __future__ import annotations

from .models import AnalyzedNovelSignal, TopicOpportunity


FANQIE_FIT_SCORES = {
    "都市重生": 90,
    "赘婿逆袭": 88,
    "高武觉醒": 85,
    "末世囤货": 85,
    "系统流": 82,
    "神医": 80,
    "穿书反派": 78,
    "仙侠修真": 75,
    "年代文": 72,
    "女频爽文": 70,
    "都市逆袭": 68,
}

READER_DESIRE_SCORES = {
    "逆袭爽感": 90,
    "打脸快感": 85,
    "甜蜜恋爱": 80,
    "生存刺激": 75,
    "轻松娱乐": 60,
}

TREND_BONUS = {
    "末世囤货": 15,
    "穿书反派": 12,
    "年代文": 10,
    "系统流": 8,
    "都市重生": 5,
}


class CommercialScorer:
    """商业潜力评分器"""
    
    def score_signal(self, signal: AnalyzedNovelSignal) -> float:
        hot = self._normalize_hot_score(signal.hot_score)
        platform_fit = signal.platform_fit_score
        desire = self._calculate_desire_score(signal)
        ease = 100 - signal.writing_difficulty_score
        trend = self._calculate_trend_bonus(signal)
        competition_penalty = self._calculate_competition_penalty(signal)
        
        final = (
            hot * 0.35
            + platform_fit * 0.25
            + desire * 0.20
            + ease * 0.10
            + trend * 0.10
            - competition_penalty
        )
        
        return max(0, min(100, final))
    
    def score_all(self, signals: list[AnalyzedNovelSignal]) -> list[AnalyzedNovelSignal]:
        scored = []
        for s in signals:
            new_score = self.score_signal(s)
            scored.append(AnalyzedNovelSignal(
                signal_id=s.signal_id,
                source=s.source,
                source_type=s.source_type,
                platform=s.platform,
                rank_type=s.rank_type,
                rank_position=s.rank_position,
                title=s.title,
                author=s.author,
                category=s.category,
                sub_category=s.sub_category,
                tags=s.tags,
                description=s.description,
                hot_score=s.hot_score,
                comment_count=s.comment_count,
                like_count=s.like_count,
                read_count=s.read_count,
                collected_at=s.collected_at,
                raw_payload=s.raw_payload,
                extracted_genre=s.extracted_genre,
                protagonist_template=s.protagonist_template,
                golden_finger=s.golden_finger,
                core_hook=s.core_hook,
                reader_desire=s.reader_desire,
                shuang_points=s.shuang_points,
                risk_points=s.risk_points,
                platform_fit_score=s.platform_fit_score,
                competition_score=s.competition_score,
                writing_difficulty_score=s.writing_difficulty_score,
                commercial_potential_score=new_score,
                analyzed_at=s.analyzed_at,
                analyzer_version=s.analyzer_version,
            ))
        return scored
    
    def _normalize_hot_score(self, hot_score: float | None) -> float:
        if hot_score is None:
            return 50.0
        return min(100, hot_score)
    
    def _calculate_desire_score(self, signal: AnalyzedNovelSignal) -> float:
        if signal.reader_desire:
            return READER_DESIRE_SCORES.get(signal.reader_desire, 60.0)
        return 60.0
    
    def _calculate_trend_bonus(self, signal: AnalyzedNovelSignal) -> float:
        genre = signal.extracted_genre or ""
        for key, bonus in TREND_BONUS.items():
            if key in genre:
                return bonus
        return 0.0
    
    def _calculate_competition_penalty(self, signal: AnalyzedNovelSignal) -> float:
        competition = signal.competition_score
        if competition > 80:
            return 10.0
        elif competition > 60:
            return 5.0
        return 0.0
    
    def generate_topic_opportunity(
        self, signal: AnalyzedNovelSignal
    ) -> TopicOpportunity:
        return TopicOpportunity(
            topic_id=f"topic_{signal.signal_id}",
            topic_name=f"{signal.extracted_genre or '未知'} - {signal.golden_finger or '未知'}",
            target_platform=signal.platform,
            target_reader=self._infer_target_reader(signal),
            core_tags=signal.tags[:5],
            evidence_titles=[signal.title],
            hot_score=signal.hot_score or 0.0,
            competition_score=signal.competition_score,
            platform_fit_score=signal.platform_fit_score,
            writing_difficulty_score=signal.writing_difficulty_score,
            final_score=signal.commercial_potential_score,
            opening_hook=self._generate_hook(signal),
            suggested_story_seed=self._generate_story_seed(signal),
            risks=signal.risk_points,
            generated_at=signal.analyzed_at,
        )
    
    def _infer_target_reader(self, signal: AnalyzedNovelSignal) -> str:
        genre = signal.extracted_genre or ""
        if "女频" in genre or "甜宠" in genre:
            return "女性读者"
        if "都市" in genre or "赘婿" in genre:
            return "都市男性读者"
        if "仙侠" in genre or "高武" in genre:
            return "玄幻爱好者"
        return "网文读者"
    
    def _generate_hook(self, signal: AnalyzedNovelSignal) -> str:
        genre = signal.extracted_genre or ""
        gf = signal.golden_finger or ""
        
        if "重生" in genre or "重生" in gf:
            return f"重回关键时刻，{gf}激活，这一次不再留遗憾。"
        if "系统" in gf:
            return f"意外激活{gf}，从此人生开挂。"
        if "末世" in genre:
            return f"末世降临前三天，{gf}觉醒，开始疯狂囤货。"
        
        return f"获得{gf}能力，开启逆袭人生。"
    
    def _generate_story_seed(self, signal: AnalyzedNovelSignal) -> str:
        return (
            f"以{signal.extracted_genre or '目标题材'}为核心，"
            f"采用{signal.golden_finger or '独特'}金手指，"
            f"主打{signal.reader_desire or '爽感'}，"
            f"前三章快速建立冲突并展示金手指威力。"
        )
