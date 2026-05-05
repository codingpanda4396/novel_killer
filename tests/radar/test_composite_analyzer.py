from unittest.mock import MagicMock, patch

import pytest

from novelops.radar.composite_analyzer import CompositeAnalyzer
from novelops.radar.hotspot_models import HotspotAnalysis
from novelops.radar.models import AnalyzedNovelSignal, RawNovelSignal


SAMPLE_LLM_RESPONSE = HotspotAnalysis(
    genre="都市重生",
    core_desire="被压迫后的逆袭",
    hook="重回2010年，激活马甲系统",
    golden_finger="系统",
    reader_emotion=["爽", "期待"],
    risk="市场竞争激烈",
)


def test_composite_analyzer_without_llm():
    """测试不使用 LLM 的组合分析器"""
    analyzer = CompositeAnalyzer(use_llm=False)
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

    assert isinstance(result, AnalyzedNovelSignal)
    assert result.llm_genre is None
    assert result.llm_core_desire is None


@patch("novelops.radar.composite_analyzer.LLMHotspotAnalyzer")
def test_composite_analyzer_with_llm(MockLLMAnalyzer):
    """测试使用 LLM 的组合分析器"""
    mock_llm_analyzer = MagicMock()
    mock_llm_analyzer.analyze_signal.return_value = SAMPLE_LLM_RESPONSE
    MockLLMAnalyzer.return_value = mock_llm_analyzer

    analyzer = CompositeAnalyzer(use_llm=True)
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

    assert isinstance(result, AnalyzedNovelSignal)
    assert result.llm_genre == "都市重生"
    assert result.llm_core_desire == "被压迫后的逆袭"
    assert result.llm_hook == "重回2010年，激活马甲系统"
    assert result.llm_golden_finger == "系统"
    assert result.llm_reader_emotion == ["爽", "期待"]
    assert result.llm_risk == "市场竞争激烈"


@patch("novelops.radar.composite_analyzer.LLMHotspotAnalyzer")
def test_composite_analyzer_llm_failure(MockLLMAnalyzer):
    """测试 LLM 失败时回退到规则分析"""
    mock_llm_analyzer = MagicMock()
    mock_llm_analyzer.analyze_signal.side_effect = Exception("LLM call failed")
    MockLLMAnalyzer.return_value = mock_llm_analyzer

    analyzer = CompositeAnalyzer(use_llm=True)
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

    assert isinstance(result, AnalyzedNovelSignal)
    assert result.llm_genre is None
    assert result.llm_core_desire is None


@patch("novelops.radar.composite_analyzer.LLMHotspotAnalyzer")
def test_composite_analyzer_batch(MockLLMAnalyzer):
    """测试批量分析"""
    mock_llm_analyzer = MagicMock()
    mock_llm_analyzer.analyze_batch.return_value = [
        SAMPLE_LLM_RESPONSE,
        SAMPLE_LLM_RESPONSE,
    ]
    MockLLMAnalyzer.return_value = mock_llm_analyzer

    analyzer = CompositeAnalyzer(use_llm=True)
    signals = [
        RawNovelSignal(
            signal_id="test_001",
            source="fanqie",
            source_type="ranking",
            platform="番茄",
            title="重生2010：我有三千马甲",
            tags=["重生", "都市", "系统"],
        ),
        RawNovelSignal(
            signal_id="test_002",
            source="fanqie",
            source_type="ranking",
            platform="番茄",
            title="末世：开局签到百亿物资",
            tags=["末世", "签到", "系统"],
        ),
    ]
    results = analyzer.analyze(signals)

    assert len(results) == 2
    assert all(isinstance(r, AnalyzedNovelSignal) for r in results)
    assert all(r.llm_genre == "都市重生" for r in results)


@patch("novelops.radar.composite_analyzer.LLMHotspotAnalyzer")
def test_composite_analyzer_batch_with_failure(MockLLMAnalyzer):
    """测试批量分析中单个失败的情况"""
    mock_llm_analyzer = MagicMock()
    mock_llm_analyzer.analyze_batch.return_value = [
        SAMPLE_LLM_RESPONSE,
        None,
    ]
    MockLLMAnalyzer.return_value = mock_llm_analyzer

    analyzer = CompositeAnalyzer(use_llm=True)
    signals = [
        RawNovelSignal(
            signal_id="test_001",
            source="fanqie",
            source_type="ranking",
            platform="番茄",
            title="重生2010：我有三千马甲",
            tags=["重生", "都市", "系统"],
        ),
        RawNovelSignal(
            signal_id="test_002",
            source="fanqie",
            source_type="ranking",
            platform="番茄",
            title="末世：开局签到百亿物资",
            tags=["末世", "签到", "系统"],
        ),
    ]
    results = analyzer.analyze(signals)

    assert len(results) == 2
    assert results[0].llm_genre == "都市重生"
    assert results[1].llm_genre is None
