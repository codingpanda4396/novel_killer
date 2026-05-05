from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .models import AnalyzedNovelSignal, CompetitorAnalysis, TopicOpportunity


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or Path("runtime/radar/reports")
    
    def generate(
        self,
        signals: list[AnalyzedNovelSignal],
        topics: list[TopicOpportunity],
        competitors: list[CompetitorAnalysis] | None = None,
    ) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        now = datetime.now()
        filename = f"topic_report_{now.strftime('%Y%m%d_%H%M')}.md"
        output_path = self.output_dir / filename
        
        content = self._build_report(signals, topics, competitors or [])
        output_path.write_text(content, encoding="utf-8")
        
        return output_path
    
    def _build_report(
        self,
        signals: list[AnalyzedNovelSignal],
        topics: list[TopicOpportunity],
        competitors: list[CompetitorAnalysis],
    ) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        
        sections = [
            self._header(now, len(signals)),
            self._overall_observation(signals),
            self._genre_ranking(signals),
            self._recommended_topics(topics),
            self._competitor_analysis(competitors),
            self._creation_suggestions(topics),
            self._data_quality(),
        ]
        
        return "\n".join(sections)
    
    def _header(self, now: str, count: int) -> str:
        return f"""# NovelRadar 中文网文选题机会报告

**生成时间**：{now}  
**数据来源**：番茄小说公开榜单  
**分析样本**：{count} 条

---

"""
    
    def _overall_observation(self, signals: list[AnalyzedNovelSignal]) -> str:
        genres = defaultdict(int)
        for s in signals:
            genre = s.extracted_genre or "未知"
            genres[genre] += 1
        
        sorted_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)
        top_genres = ", ".join(g for g, _ in sorted_genres[:3])
        
        scores = [s.commercial_potential_score for s in signals if s.commercial_potential_score]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        risky = [s for s in signals if len(s.risk_points) >= 2]
        
        return f"""## 一、总体观察

- 今日共分析 **{len(signals)}** 条数据
- 高潜力题材 Top 3：{top_genres}
- 风险较高题材：{len(risky)} 条
- 平均商业潜力评分：{avg_score:.1f}/100

---

"""
    
    def _genre_ranking(self, signals: list[AnalyzedNovelSignal]) -> str:
        genre_stats = defaultdict(lambda: {"count": 0, "hot": [], "fit": [], "comp": []})
        
        for s in signals:
            genre = s.extracted_genre or "未知"
            genre_stats[genre]["count"] += 1
            if s.hot_score:
                genre_stats[genre]["hot"].append(s.hot_score)
            genre_stats[genre]["fit"].append(s.platform_fit_score)
            genre_stats[genre]["comp"].append(s.competition_score)
        
        sorted_genres = sorted(
            genre_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        lines = [
            "## 二、题材热度排行\n",
            "| 排名 | 题材 | 样本数 | 平均热度 | 平台适配度 | 竞争度 | 推荐指数 |",
            "|:---:|:---|---:|---:|---:|---:|---:|",
        ]
        
        for i, (genre, stats) in enumerate(sorted_genres[:10], 1):
            count = stats["count"]
            avg_hot = sum(stats["hot"]) / len(stats["hot"]) if stats["hot"] else 0
            avg_fit = sum(stats["fit"]) / len(stats["fit"]) if stats["fit"] else 0
            avg_comp = sum(stats["comp"]) / len(stats["comp"]) if stats["comp"] else 0
            
            stars = self._calculate_stars(avg_hot, avg_fit, avg_comp)
            
            lines.append(
                f"| {i} | {genre} | {count} | {avg_hot:.1f} | {avg_fit:.1f} | {avg_comp:.1f} | {stars} |"
            )
        
        lines.append("\n---\n")
        return "\n".join(lines)
    
    def _calculate_stars(self, hot: float, fit: float, comp: float) -> str:
        score = (hot + fit) / 2 - comp / 4
        if score >= 80:
            return "⭐⭐⭐⭐⭐"
        elif score >= 65:
            return "⭐⭐⭐⭐"
        elif score >= 50:
            return "⭐⭐⭐"
        elif score >= 35:
            return "⭐⭐"
        return "⭐"
    
    def _recommended_topics(self, topics: list[TopicOpportunity]) -> str:
        if not topics:
            return "## 三、推荐测试选题\n\n暂无推荐选题。\n\n---\n"
        
        lines = ["## 三、推荐测试选题\n"]
        
        for i, t in enumerate(sorted(topics, key=lambda x: x.final_score, reverse=True)[:5], 1):
            lines.append(f"""### 选题 {i}：{t.topic_name}

**目标平台**：{t.target_platform}  
**目标读者**：{t.target_reader}  
**核心标签**：{', '.join(t.core_tags)}  
**综合评分**：{t.final_score:.1f}/100

**证据样本**：
{chr(10).join(f'- {title}' for title in t.evidence_titles)}

**推荐开篇钩子**：
{t.opening_hook}

**可测试故事种子**：
{t.suggested_story_seed}

**主要风险**：
{chr(10).join(f'- {r}' for r in t.risks) if t.risks else '- 暂无明显风险'}

---

""")
        
        return "\n".join(lines)
    
    def _competitor_analysis(self, competitors: list[CompetitorAnalysis]) -> str:
        if not competitors:
            return ""
        
        lines = ["## 四、竞品分析\n"]
        
        for c in competitors:
            if c.total_count == 0:
                continue
            
            lines.append(f"""### {c.genre}题材

- **竞品数量**：{c.total_count} 部
- **竞争等级**：{c.competition_level}
- **平均热度**：{c.average_hot_score:.1f}
- **头部作品**：{', '.join(c.top_titles[:3])}
- **常见金手指**：{', '.join(c.common_golden_fingers)}
- **常见爽点**：{', '.join(c.common_shuang_points)}
- **差异化机会**：
{chr(10).join(f'  - {o}' for o in c.differentiation_opportunities)}

""")
        
        return "\n".join(lines)
    
    def _creation_suggestions(self, topics: list[TopicOpportunity]) -> str:
        top_topics = sorted(topics, key=lambda x: x.final_score, reverse=True)[:3]
        topic_names = ", ".join(t.topic_name for t in top_topics) if top_topics else "暂无"
        
        return f"""## 五、下一步创作建议

1. **优先测试选题**：{topic_names}
2. **开篇策略**：每个选题生成 3 个开篇变体，控制在 2000-3000 字
3. **测试重点**：前三章留存率、评论区反馈、收藏转化
4. **避免陷阱**：不要追求神作，先测试题材和钩子的市场反应

---

"""
    
    def _data_quality(self) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        return f"""## 六、数据质量说明

- 数据时效性：{now}
- 分析器版本：1.0.0
- 建议更新频率：每日或每周

---

*本报告由 NovelRadar 自动生成，仅供参考。最终选题决策需结合个人写作能力和市场实测。*
"""
