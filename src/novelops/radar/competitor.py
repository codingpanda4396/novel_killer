from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from .models import AnalyzedNovelSignal, CompetitorAnalysis


class CompetitorAnalyzer:
    """竞品分析器"""
    
    def analyze_competitors(
        self, signals: list[AnalyzedNovelSignal], genre: str
    ) -> CompetitorAnalysis:
        now = datetime.now(timezone.utc).isoformat()
        
        genre_signals = [s for s in signals if genre in (s.extracted_genre or "")]
        
        if not genre_signals:
            return CompetitorAnalysis(
                genre=genre,
                total_count=0,
                top_titles=[],
                common_golden_fingers=[],
                common_shuang_points=[],
                average_hot_score=0.0,
                competition_level="unknown",
                differentiation_opportunities=["无数据"],
                analyzed_at=now,
            )
        
        top_signals = sorted(genre_signals, key=lambda s: s.hot_score or 0, reverse=True)[:5]
        top_titles = [s.title for s in top_signals]
        
        gf_counter = Counter()
        sp_counter = Counter()
        for s in genre_signals:
            if s.golden_finger:
                gf_counter[s.golden_finger] += 1
            for sp in s.shuang_points:
                sp_counter[sp] += 1
        
        hot_scores = [s.hot_score for s in genre_signals if s.hot_score]
        avg_hot = sum(hot_scores) / len(hot_scores) if hot_scores else 0.0
        
        count = len(genre_signals)
        if count >= 10:
            level = "high"
        elif count >= 5:
            level = "medium"
        else:
            level = "low"
        
        opportunities = self._find_opportunities(gf_counter, sp_counter)
        
        return CompetitorAnalysis(
            genre=genre,
            total_count=count,
            top_titles=top_titles,
            common_golden_fingers=[gf for gf, _ in gf_counter.most_common(3)],
            common_shuang_points=[sp for sp, _ in sp_counter.most_common(3)],
            average_hot_score=avg_hot,
            competition_level=level,
            differentiation_opportunities=opportunities,
            analyzed_at=now,
        )
    
    def _find_opportunities(
        self, gf_counter: Counter, sp_counter: Counter
    ) -> list[str]:
        opportunities = []
        
        all_gf = ["系统", "空间", "重生", "词条", "模拟器", "马甲"]
        used_gf = set(gf_counter.keys())
        unused_gf = set(all_gf) - used_gf
        if unused_gf:
            opportunities.append(f"金手指差异：可尝试 {', '.join(list(unused_gf)[:2])}")
        
        if len(sp_counter) < 3:
            opportunities.append("爽点组合较少，可增加差异化爽点")
        
        if not opportunities:
            opportunities.append("竞争激烈，需要在开篇和人设上做差异化")
        
        return opportunities
    
    def analyze_all_genres(
        self, signals: list[AnalyzedNovelSignal]
    ) -> list[CompetitorAnalysis]:
        genres = set()
        for s in signals:
            if s.extracted_genre:
                for g in s.extracted_genre.split("+"):
                    genres.add(g)
        
        return [self.analyze_competitors(signals, g) for g in sorted(genres)]
