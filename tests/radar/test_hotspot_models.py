import pytest
from pydantic import ValidationError

from novelops.radar.hotspot_models import HotspotAnalysis


def test_hotspot_analysis_valid():
    """测试合法 JSON 通过"""
    data = {
        "genre": "都市重生",
        "core_desire": "被压迫后的逆袭",
        "hook": "重回2010年，激活马甲系统",
        "golden_finger": "系统",
        "reader_emotion": ["爽", "期待"],
        "risk": "市场竞争激烈",
    }
    result = HotspotAnalysis.model_validate(data)
    assert result.genre == "都市重生"
    assert result.core_desire == "被压迫后的逆袭"
    assert result.hook == "重回2010年，激活马甲系统"
    assert result.golden_finger == "系统"
    assert result.reader_emotion == ["爽", "期待"]
    assert result.risk == "市场竞争激烈"


def test_hotspot_analysis_missing_field():
    """测试缺字段失败"""
    data = {
        "genre": "都市重生",
        "core_desire": "被压迫后的逆袭",
        # 缺少 hook
        "golden_finger": "系统",
        "reader_emotion": ["爽"],
        "risk": "市场竞争激烈",
    }
    with pytest.raises(ValidationError):
        HotspotAnalysis.model_validate(data)


def test_hotspot_analysis_invalid_type():
    """测试类型错误失败"""
    data = {
        "genre": "都市重生",
        "core_desire": "被压迫后的逆袭",
        "hook": "重回2010年，激活马甲系统",
        "golden_finger": "系统",
        "reader_emotion": "爽",  # 应该是列表
        "risk": "市场竞争激烈",
    }
    with pytest.raises(ValidationError):
        HotspotAnalysis.model_validate(data)


def test_hotspot_analysis_emotion_max_length():
    """测试 reader_emotion 最大长度"""
    data = {
        "genre": "都市重生",
        "core_desire": "被压迫后的逆袭",
        "hook": "重回2010年，激活马甲系统",
        "golden_finger": "系统",
        "reader_emotion": ["爽", "期待", "紧张", "兴奋", "感动"],  # 5个，刚好
        "risk": "市场竞争激烈",
    }
    result = HotspotAnalysis.model_validate(data)
    assert len(result.reader_emotion) == 5


def test_hotspot_analysis_emotion_too_long():
    """测试 reader_emotion 超过最大长度"""
    data = {
        "genre": "都市重生",
        "core_desire": "被压迫后的逆袭",
        "hook": "重回2010年，激活马甲系统",
        "golden_finger": "系统",
        "reader_emotion": ["爽", "期待", "紧张", "兴奋", "感动", "惊喜"],  # 6个，超过
        "risk": "市场竞争激烈",
    }
    with pytest.raises(ValidationError):
        HotspotAnalysis.model_validate(data)
