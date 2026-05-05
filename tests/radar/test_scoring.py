from novelops.radar.models import AnalyzedNovelSignal
from novelops.radar.scoring import CommercialScorer


def test_score_range():
    scorer = CommercialScorer()
    
    signal = AnalyzedNovelSignal(
        signal_id="test_001",
        source="fanqie",
        source_type="ranking",
        platform="番茄",
        title="测试小说",
        extracted_genre="都市重生",
        golden_finger="重生",
        hot_score=90.0,
        platform_fit_score=85.0,
        writing_difficulty_score=30.0,
        competition_score=60.0,
    )
    
    score = scorer.score_signal(signal)
    assert 0 <= score <= 100


def test_high_score_for_good_signal():
    scorer = CommercialScorer()
    
    signal = AnalyzedNovelSignal(
        signal_id="test_002",
        source="fanqie",
        source_type="ranking",
        platform="番茄",
        title="重生2010",
        extracted_genre="都市重生",
        golden_finger="重生",
        reader_desire="逆袭爽感",
        hot_score=95.0,
        platform_fit_score=90.0,
        writing_difficulty_score=30.0,
        competition_score=50.0,
    )
    
    score = scorer.score_signal(signal)
    assert score >= 70


def test_topic_generation():
    scorer = CommercialScorer()
    
    signal = AnalyzedNovelSignal(
        signal_id="test_003",
        source="fanqie",
        source_type="ranking",
        platform="番茄",
        title="测试小说",
        extracted_genre="末世囤货",
        golden_finger="系统",
        tags=["末世", "系统", "囤货"],
        hot_score=85.0,
        platform_fit_score=85.0,
        writing_difficulty_score=40.0,
        competition_score=50.0,
        commercial_potential_score=80.0,
    )
    
    topic = scorer.generate_topic_opportunity(signal)
    assert topic.target_platform == "番茄"
    assert "末世" in topic.topic_name
    assert topic.final_score == 80.0
