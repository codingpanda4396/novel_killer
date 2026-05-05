from __future__ import annotations

from .web_collector import RankPageCollector


class FanqieRankCollector(RankPageCollector):
    platform = "番茄"
    source_key = "fanqie"
    rank_urls = {
        "hot": "https://fanqienovel.com/rank",
        "new": "https://fanqienovel.com/rank/new",
        "finish": "https://fanqienovel.com/rank/finish",
    }
    rank_metric_names = {
        "hot": "人在读",
        "new": "人在读",
        "finish": "人在读",
    }


class QidianRankCollector(RankPageCollector):
    platform = "起点"
    source_key = "qidian"
    rank_urls = {
        "hot": "https://www.qidian.com/rank/",
        "yuepiao": "https://www.qidian.com/rank/yuepiao/",
        "readindex": "https://www.qidian.com/rank/readindex/",
        "recom": "https://www.qidian.com/rank/recom/",
        "collect": "https://www.qidian.com/rank/collect/",
        "new": "https://www.qidian.com/rank/newfans/",
    }
    rank_metric_names = {
        "yuepiao": "月票",
        "readindex": "阅读指数",
        "recom": "推荐",
        "collect": "收藏",
        "new": "人气",
    }


class ZonghengRankCollector(RankPageCollector):
    platform = "纵横"
    source_key = "zongheng"
    rank_urls = {
        "hot": "https://book.zongheng.com/rank.html",
        "yuepiao": "https://book.zongheng.com/rank.html",
        "sale24": "https://book.zongheng.com/rank.html",
        "new": "https://book.zongheng.com/rank.html",
        "click": "https://book.zongheng.com/rank.html",
        "recom": "https://book.zongheng.com/rank.html",
    }
    rank_metric_names = {
        "yuepiao": "月票",
        "sale24": "畅销",
        "new": "人气",
        "click": "点击",
        "recom": "推荐",
    }


class JjwxcRankCollector(RankPageCollector):
    platform = "晋江"
    source_key = "jjwxc"
    rank_urls = {
        "hot": "https://m.jjwxc.net/rank",
        "score": "https://m.jjwxc.net/rank",
        "kingticket": "https://m.jjwxc.com/ranks/kingticket",
    }
    rank_metric_names = {
        "hot": "总分",
        "score": "总分",
        "kingticket": "霸王票",
    }


class XxsyCategoryCollector(RankPageCollector):
    platform = "潇湘"
    source_key = "xxsy"
    rank_urls = {
        "hot": "https://www.xxsypro.com/category",
        "sale": "https://www.xxsypro.com/category?order=2",
        "collect": "https://www.xxsypro.com/category?order=3",
    }
    rank_metric_names = {
        "hot": "热度",
        "sale": "畅销",
        "collect": "收藏",
    }
