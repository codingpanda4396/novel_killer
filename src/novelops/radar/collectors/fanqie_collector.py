from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .base import BaseCollector
from ..models import RawNovelSignal


class FanqieCollector(BaseCollector):
    """番茄小说公开榜单采集器
    
    采集番茄小说公开榜单数据，包括：
    - 热榜
    - 新书榜
    - 完结榜
    
    注意：仅采集公开可见数据，不采集付费内容
    """
    
    # 番茄榜单URL（公开页面）
    RANK_URLS = {
        "hot": "https://fanqienovel.com/rank",
        "new": "https://fanqienovel.com/rank/new",
        "finish": "https://fanqienovel.com/rank/finish",
    }
    
    def __init__(self, rank_type: str = "hot", use_sample: bool = False):
        self.rank_type = rank_type
        self.use_sample = use_sample
    
    @property
    def name(self) -> str:
        return f"Fanqie {self.rank_type} Collector"
    
    @property
    def source(self) -> str:
        return "fanqie"
    
    def collect(self) -> list[RawNovelSignal]:
        if self.use_sample:
            return self._get_sample_data()
        
        # TODO: 实现实际爬取逻辑（需要 Playwright）
        # 暂时返回样本数据
        return self._get_sample_data()
    
    def _get_sample_data(self) -> list[RawNovelSignal]:
        """返回番茄风格的样本数据"""
        now = datetime.now(timezone.utc).isoformat()
        
        samples = [
            {
                "title": "重生2010：我有三千马甲",
                "author": "码字狂人",
                "category": "都市",
                "tags": ["重生", "都市", "系统", "逆袭", "打脸"],
                "description": "重回2010年，激活马甲系统，每个马甲都是一种人生。",
                "hot_score": 95.5,
                "comment_count": 12580,
                "read_count": 3580000,
            },
            {
                "title": "末世：开局签到百亿物资",
                "author": "末世老司机",
                "category": "科幻",
                "tags": ["末世", "囤货", "签到", "系统", "生存"],
                "description": "末世降临前三天，我激活了签到系统，获得百亿物资。",
                "hot_score": 92.3,
                "comment_count": 8960,
                "read_count": 2890000,
            },
            {
                "title": "离婚后，前妻跪求复合",
                "author": "都市情圣",
                "category": "都市",
                "tags": ["都市", "逆袭", "打脸", "虐渣", "豪门"],
                "description": "三年冷婚，一朝离婚，前妻才发现我是隐藏首富。",
                "hot_score": 91.8,
                "comment_count": 15600,
                "read_count": 4200000,
            },
            {
                "title": "高武：我有无限模拟器",
                "author": "武道宗师",
                "category": "玄幻",
                "tags": ["高武", "模拟器", "无敌", "横推", "觉醒"],
                "description": "穿越高武世界，激活无限模拟器，模拟未来获取奖励。",
                "hot_score": 89.5,
                "comment_count": 7800,
                "read_count": 2150000,
            },
            {
                "title": "七零军嫂：空间在手养崽崽",
                "author": "年代小甜",
                "category": "言情",
                "tags": ["年代文", "空间", "军婚", "甜宠", "种田"],
                "description": "穿越七零，嫁给糙汉军官，空间在手养崽发家。",
                "hot_score": 88.2,
                "comment_count": 6500,
                "read_count": 1890000,
            },
            {
                "title": "仙尊归来：从都市开始无敌",
                "author": "修仙大佬",
                "category": "仙侠",
                "tags": ["仙侠", "重生", "都市", "无敌", "打脸"],
                "description": "渡劫失败重回地球，这一世我要逍遥都市。",
                "hot_score": 87.6,
                "comment_count": 9200,
                "read_count": 2680000,
            },
            {
                "title": "赘婿逆袭：岳母跪求我原谅",
                "author": "逆袭之王",
                "category": "都市",
                "tags": ["赘婿", "逆袭", "打脸", "豪门", "虐渣"],
                "description": "三年赘婿无人知，一朝逆袭天下惊。",
                "hot_score": 86.9,
                "comment_count": 11200,
                "read_count": 3100000,
            },
            {
                "title": "全民转职：我有隐藏职业死神",
                "author": "游戏狂人",
                "category": "游戏",
                "tags": ["系统", "转职", "无敌", "横推", "觉醒"],
                "description": "全民转职时代，我获得隐藏职业死神，一刀秒杀。",
                "hot_score": 85.3,
                "comment_count": 5800,
                "read_count": 1650000,
            },
            {
                "title": "穿书反派：开局抢了主角机缘",
                "author": "反派专业户",
                "category": "玄幻",
                "tags": ["穿书", "反派", "系统", "无敌", "爽文"],
                "description": "穿成书中反派，抢主角机缘，夺主角气运。",
                "hot_score": 84.7,
                "comment_count": 7200,
                "read_count": 2050000,
            },
            {
                "title": "神医下山：开局就被退婚",
                "author": "神医无敌",
                "category": "都市",
                "tags": ["神医", "下山", "退婚", "逆袭", "打脸"],
                "description": "下山第一天就被退婚，殊不知我医术通神。",
                "hot_score": 83.5,
                "comment_count": 6800,
                "read_count": 1920000,
            },
        ]
        
        signals = []
        for i, s in enumerate(samples, 1):
            signals.append(RawNovelSignal(
                signal_id=f"fanqie_{self.rank_type}_{i:03d}",
                source="fanqie",
                source_type="ranking",
                platform="番茄",
                rank_type=f"{self.rank_type}榜",
                rank_position=i,
                title=s["title"],
                author=s["author"],
                category=s["category"],
                sub_category=None,
                tags=s["tags"],
                description=s["description"],
                hot_score=s["hot_score"],
                comment_count=s["comment_count"],
                like_count=None,
                read_count=s["read_count"],
                collected_at=now,
                raw_payload=s,
            ))
        
        return signals
