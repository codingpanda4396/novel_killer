from __future__ import annotations

from datetime import datetime, timezone

from .models import AnalyzedNovelSignal, RawNovelSignal


GENRE_RULES = {
    "仙侠修真": ["修仙", "仙尊", "长生", "宗门", "筑基", "金丹", "元婴", "仙侠"],
    "都市重生": ["重生", "回到", "穿越", "前世", "重回"],
    "都市逆袭": ["首富", "商业", "赚钱", "创业", "逆袭", "都市"],
    "年代文": ["空间", "年代", "下乡", "军婚", "七零", "八零", "六零"],
    "末世囤货": ["末世", "囤货", "丧尸", "灾难", "求生"],
    "系统流": ["系统", "面板", "词条", "模拟器", "签到", "转职"],
    "女频爽文": ["真假千金", "豪门", "退婚", "打脸", "虐渣", "甜宠"],
    "高武觉醒": ["高武", "觉醒", "武道", "灵气复苏", "横推"],
    "赘婿逆袭": ["赘婿", "上门", "岳母", "离婚"],
    "穿书反派": ["穿书", "反派", "抢机缘"],
    "神医": ["神医", "医术", "下山"],
}

GOLDEN_FINGER_RULES = {
    "系统": ["系统", "面板", "签到", "任务"],
    "空间": ["空间", "随身", "仓库"],
    "重生": ["重生", "回到", "重回", "前世记忆"],
    "词条": ["词条", "天赋", "属性"],
    "模拟器": ["模拟器", "推演", "无限"],
    "马甲": ["马甲", "身份", "伪装"],
}

SHUANG_POINT_RULES = [
    "杀伐果断", "无敌", "横推", "打脸", "装逼",
    "逆袭", "复仇", "虐渣", "爽文", "碾压",
    "打脸", "逆袭", "甜宠",
]


class RuleBasedRadarAnalyzer:
    """基于规则的分析器"""
    
    VERSION = "1.0.0"
    
    def analyze(self, signals: list[RawNovelSignal]) -> list[AnalyzedNovelSignal]:
        return [self.analyze_one(s) for s in signals]
    
    def analyze_one(self, signal: RawNovelSignal) -> AnalyzedNovelSignal:
        now = datetime.now(timezone.utc).isoformat()
        
        text = f"{signal.title} {signal.description or ''} {' '.join(signal.tags)}"
        
        genre = self._extract_genre(text, signal.category)
        golden_finger = self._extract_golden_finger(text)
        shuang_points = self._extract_shuang_points(text)
        risk_points = self._extract_risk_points(signal)
        
        platform_fit = self._calculate_platform_fit(genre)
        competition = self._estimate_competition(genre)
        writing_difficulty = self._estimate_writing_difficulty(genre, golden_finger)
        
        return AnalyzedNovelSignal(
            signal_id=signal.signal_id,
            source=signal.source,
            source_type=signal.source_type,
            platform=signal.platform,
            rank_type=signal.rank_type,
            rank_position=signal.rank_position,
            title=signal.title,
            author=signal.author,
            category=signal.category,
            sub_category=signal.sub_category,
            tags=signal.tags,
            description=signal.description,
            hot_score=signal.hot_score,
            comment_count=signal.comment_count,
            like_count=signal.like_count,
            read_count=signal.read_count,
            collected_at=signal.collected_at,
            raw_payload=signal.raw_payload,
            extracted_genre=genre,
            protagonist_template=self._extract_protagonist_template(genre),
            golden_finger=golden_finger,
            core_hook=self._extract_core_hook(signal.title),
            reader_desire=self._extract_reader_desire(genre, shuang_points),
            shuang_points=shuang_points,
            risk_points=risk_points,
            platform_fit_score=platform_fit,
            competition_score=competition,
            writing_difficulty_score=writing_difficulty,
            commercial_potential_score=0.0,
            analyzed_at=now,
            analyzer_version=self.VERSION,
        )
    
    def _extract_genre(self, text: str, category: str | None) -> str:
        matched_genres = []
        for genre, keywords in GENRE_RULES.items():
            if any(kw in text for kw in keywords):
                matched_genres.append(genre)
        
        if matched_genres:
            return "+".join(matched_genres[:2])
        
        if category:
            return category
        return "未知"
    
    def _extract_golden_finger(self, text: str) -> str:
        for gf, keywords in GOLDEN_FINGER_RULES.items():
            if any(kw in text for kw in keywords):
                return gf
        return "未知"
    
    def _extract_shuang_points(self, text: str) -> list[str]:
        return [p for p in SHUANG_POINT_RULES if p in text]
    
    def _extract_risk_points(self, signal: RawNovelSignal) -> list[str]:
        risks = []
        
        if len(signal.tags) > 8:
            risks.append("卖点过散")
        
        if not signal.description or len(signal.description) < 20:
            risks.append("缺少简介")
        
        if signal.hot_score and signal.hot_score < 50:
            risks.append("热度不足")
        
        return risks
    
    def _extract_protagonist_template(self, genre: str) -> str:
        templates = {
            "都市重生": "重生者",
            "赘婿逆袭": "隐忍赘婿",
            "末世囤货": "末世生存者",
            "系统流": "系统宿主",
            "高武觉醒": "觉醒者",
            "仙侠修真": "修仙者",
            "年代文": "穿越者",
            "穿书反派": "穿书反派",
        }
        for key, template in templates.items():
            if key in genre:
                return template
        return "普通人"
    
    def _extract_core_hook(self, title: str) -> str:
        return title
    
    def _extract_reader_desire(self, genre: str, shuang_points: list[str]) -> str:
        if "逆袭" in shuang_points:
            return "逆袭爽感"
        if "打脸" in shuang_points:
            return "打脸快感"
        if "甜宠" in shuang_points:
            return "甜蜜恋爱"
        if "末世" in genre:
            return "生存刺激"
        return "轻松娱乐"
    
    def _calculate_platform_fit(self, genre: str) -> float:
        fit_scores = {
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
        
        for key, score in fit_scores.items():
            if key in genre:
                return score
        return 50.0
    
    def _estimate_competition(self, genre: str) -> float:
        high_competition = ["都市重生", "赘婿逆袭", "系统流"]
        medium_competition = ["仙侠修真", "都市逆袭", "高武觉醒"]
        
        for g in high_competition:
            if g in genre:
                return 80.0
        for g in medium_competition:
            if g in genre:
                return 60.0
        return 40.0
    
    def _estimate_writing_difficulty(self, genre: str, golden_finger: str) -> float:
        if "系统" in golden_finger:
            return 30.0
        if "重生" in golden_finger:
            return 35.0
        if "仙侠" in genre:
            return 60.0
        if "末世" in genre:
            return 55.0
        return 45.0
