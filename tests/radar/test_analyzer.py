from novelops.radar.analyzer import RuleBasedRadarAnalyzer
from novelops.radar.models import RawNovelSignal


def test_genre_extraction():
    analyzer = RuleBasedRadarAnalyzer()
    
    signal = RawNovelSignal(
        signal_id="test_001",
        source="fanqie",
        source_type="ranking",
        platform="番茄",
        title="重生2010：我有三千马甲",
        tags=["重生", "都市", "系统"],
        description="重回2010年，激活马甲系统",
    )
    
    result = analyzer.analyze_one(signal)
    assert "重生" in result.extracted_genre or "都市" in result.extracted_genre


def test_golden_finger_extraction():
    analyzer = RuleBasedRadarAnalyzer()
    
    signal = RawNovelSignal(
        signal_id="test_002",
        source="fanqie",
        source_type="ranking",
        platform="番茄",
        title="末世：开局签到百亿物资",
        tags=["末世", "签到", "系统"],
        description="末世降临前三天，我激活了签到系统",
    )
    
    result = analyzer.analyze_one(signal)
    assert result.golden_finger in ["系统", "签到"]


def test_shuang_points_extraction():
    analyzer = RuleBasedRadarAnalyzer()
    
    signal = RawNovelSignal(
        signal_id="test_003",
        source="fanqie",
        source_type="ranking",
        platform="番茄",
        title="赘婿逆袭：岳母跪求我原谅",
        tags=["赘婿", "逆袭", "打脸"],
        description="三年赘婿无人知，一朝逆袭天下惊",
    )
    
    result = analyzer.analyze_one(signal)
    assert len(result.shuang_points) > 0


def test_risk_detection():
    analyzer = RuleBasedRadarAnalyzer()
    
    signal = RawNovelSignal(
        signal_id="test_004",
        source="fanqie",
        source_type="ranking",
        platform="番茄",
        title="测试小说",
        tags=["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9"],
        description="",
        hot_score=30.0,
    )
    
    result = analyzer.analyze_one(signal)
    assert "卖点过散" in result.risk_points
    assert "缺少简介" in result.risk_points
