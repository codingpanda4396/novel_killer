from unittest.mock import MagicMock, patch

import pytest

from novelops.radar.hotspot_models import HotspotAnalysis
from novelops.radar.llm_analyzer import LLMHotspotAnalyzer
from novelops.radar.models import RawNovelSignal


SAMPLE_LLM_RESPONSE = {
    "genre": "都市重生",
    "core_desire": "被压迫后的逆袭",
    "hook": "重回2010年，激活马甲系统",
    "golden_finger": "系统",
    "reader_emotion": ["爽", "期待"],
    "risk": "市场竞争激烈",
}


def test_analyze_text():
    """测试 analyze_text 方法"""
    mock_client = MagicMock()
    mock_client.complete_json.return_value = SAMPLE_LLM_RESPONSE

    analyzer = LLMHotspotAnalyzer(llm_client=mock_client)
    result = analyzer.analyze_text("重生2010：我有三千马甲")

    assert isinstance(result, HotspotAnalysis)
    assert result.genre == "都市重生"
    assert result.core_desire == "被压迫后的逆袭"
    mock_client.complete_json.assert_called_once()


def test_analyze_text_with_metadata():
    """测试带元数据的 analyze_text 方法"""
    mock_client = MagicMock()
    mock_client.complete_json.return_value = SAMPLE_LLM_RESPONSE

    analyzer = LLMHotspotAnalyzer(llm_client=mock_client)
    metadata = {
        "title": "重生2010：我有三千马甲",
        "category": "都市",
        "tags": ["重生", "系统"],
        "platform": "番茄",
    }
    result = analyzer.analyze_text("重生2010：我有三千马甲", metadata)

    assert isinstance(result, HotspotAnalysis)
    mock_client.complete_json.assert_called_once()


def test_analyze_signal():
    """测试 analyze_signal 方法"""
    mock_client = MagicMock()
    mock_client.complete_json.return_value = SAMPLE_LLM_RESPONSE

    analyzer = LLMHotspotAnalyzer(llm_client=mock_client)
    signal = RawNovelSignal(
        signal_id="test_001",
        source="fanqie",
        source_type="ranking",
        platform="番茄",
        title="重生2010：我有三千马甲",
        tags=["重生", "都市", "系统"],
        description="重回2010年，激活马甲系统",
    )
    result = analyzer.analyze_signal(signal)

    assert isinstance(result, HotspotAnalysis)
    assert result.genre == "都市重生"
    mock_client.complete_json.assert_called_once()


def test_analyze_batch():
    """测试 analyze_batch 方法"""
    mock_client = MagicMock()
    mock_client.complete_json.return_value = SAMPLE_LLM_RESPONSE

    analyzer = LLMHotspotAnalyzer(llm_client=mock_client)
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
    results = analyzer.analyze_batch(signals)

    assert len(results) == 2
    assert all(isinstance(r, HotspotAnalysis) for r in results)
    assert mock_client.complete_json.call_count == 2


def test_analyze_batch_with_failure():
    """测试 analyze_batch 方法中单个失败的情况"""
    mock_client = MagicMock()
    mock_client.complete_json.side_effect = [
        SAMPLE_LLM_RESPONSE,
        Exception("LLM call failed"),
    ]

    analyzer = LLMHotspotAnalyzer(llm_client=mock_client)
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
    results = analyzer.analyze_batch(signals)

    assert len(results) == 2
    assert isinstance(results[0], HotspotAnalysis)
    assert results[1] is None


def test_schema_passed_to_client():
    """测试 schema 参数传递"""
    mock_client = MagicMock()
    mock_client.complete_json.return_value = SAMPLE_LLM_RESPONSE

    analyzer = LLMHotspotAnalyzer(llm_client=mock_client)
    analyzer.analyze_text("测试文本")

    call_kwargs = mock_client.complete_json.call_args
    assert "schema" in call_kwargs.kwargs or len(call_kwargs.args) >= 4
