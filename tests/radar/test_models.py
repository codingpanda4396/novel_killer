from novelops.radar.models import RawNovelSignal, AnalyzedNovelSignal, TopicOpportunity


def test_raw_signal_creation():
    signal = RawNovelSignal(
        signal_id="test_001",
        source="fanqie",
        source_type="ranking",
        platform="番茄",
        title="测试小说",
        tags=["都市", "重生"],
        hot_score=85.0,
    )
    assert signal.signal_id == "test_001"
    assert signal.title == "测试小说"
    assert len(signal.tags) == 2


def test_raw_signal_defaults():
    signal = RawNovelSignal(
        signal_id="test_002",
        source="manual",
        source_type="manual",
        platform="unknown",
    )
    assert signal.title == ""
    assert signal.tags == []
    assert signal.hot_score is None


def test_analyzed_signal_creation():
    signal = AnalyzedNovelSignal(
        signal_id="test_003",
        source="fanqie",
        source_type="ranking",
        platform="番茄",
        title="测试小说",
        extracted_genre="都市重生",
        golden_finger="重生",
        shuang_points=["逆袭", "打脸"],
        platform_fit_score=90.0,
    )
    assert signal.extracted_genre == "都市重生"
    assert "逆袭" in signal.shuang_points


def test_topic_opportunity():
    topic = TopicOpportunity(
        topic_id="topic_001",
        topic_name="都市重生 - 系统",
        target_platform="番茄",
        target_reader="都市男性读者",
        core_tags=["都市", "重生"],
        evidence_titles=["重生2010"],
        final_score=85.5,
        opening_hook="重回关键时刻",
    )
    assert topic.final_score == 85.5
    assert "重生" in topic.core_tags
