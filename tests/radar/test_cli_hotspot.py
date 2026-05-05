import json
from unittest.mock import MagicMock, patch

import pytest

from novelops.radar.cli import cmd_analyze, cmd_analyze_text
from novelops.radar.hotspot_models import HotspotAnalysis
from novelops.radar.models import RawNovelSignal
from novelops.radar.storage import RadarStorage


SAMPLE_LLM_RESPONSE = HotspotAnalysis(
    genre="都市重生",
    core_desire="被压迫后的逆袭",
    hook="重回2010年，激活马甲系统",
    golden_finger="系统",
    reader_emotion=["爽", "期待"],
    risk="市场竞争激烈",
)


def test_analyze_text_json(tmp_path, capsys):
    """测试 analyze-text --json 输出目标 JSON"""
    mock_client = MagicMock()
    mock_client.complete_json.return_value = SAMPLE_LLM_RESPONSE.model_dump()

    with patch("novelops.radar.cli.LLMHotspotAnalyzer") as MockAnalyzer:
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_text.return_value = SAMPLE_LLM_RESPONSE
        MockAnalyzer.return_value = mock_analyzer

        args = MagicMock()
        args.text = "重生2010：我有三千马甲"
        args.json = True
        args.title = None
        args.category = None
        args.tags = None
        args.platform = None

        result = cmd_analyze_text(args)
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["genre"] == "都市重生"
        assert output["core_desire"] == "被压迫后的逆袭"


def test_analyze_text_plain(tmp_path, capsys):
    """测试 analyze-text 纯文本输出"""
    with patch("novelops.radar.cli.LLMHotspotAnalyzer") as MockAnalyzer:
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_text.return_value = SAMPLE_LLM_RESPONSE
        MockAnalyzer.return_value = mock_analyzer

        args = MagicMock()
        args.text = "重生2010：我有三千马甲"
        args.json = False
        args.title = None
        args.category = None
        args.tags = None
        args.platform = None

        result = cmd_analyze_text(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "题材：都市重生" in captured.out
        assert "核心欲望：被压迫后的逆袭" in captured.out


@patch("novelops.radar.cli.CompositeAnalyzer")
def test_analyze_with_llm(MockCompositeAnalyzer, tmp_path):
    """测试 analyze --llm 使用 fake client 后保存新增字段"""
    db_path = tmp_path / "test_radar.sqlite"
    storage = RadarStorage(db_path)
    storage.init_db()

    signal = RawNovelSignal(
        signal_id="test_001",
        source="fanqie",
        source_type="ranking",
        platform="番茄",
        title="重生2010：我有三千马甲",
        tags=["重生", "都市", "系统"],
        description="重回2010年，激活马甲系统",
        collected_at="2024-01-01",
    )
    storage.save_raw_signals([signal])

    mock_analyzer = MagicMock()
    mock_analyzed = MagicMock()
    mock_analyzed.signal_id = "test_001"
    mock_analyzed.source = "fanqie"
    mock_analyzed.source_type = "ranking"
    mock_analyzed.platform = "番茄"
    mock_analyzed.rank_type = None
    mock_analyzed.rank_position = None
    mock_analyzed.title = "重生2010：我有三千马甲"
    mock_analyzed.author = None
    mock_analyzed.category = None
    mock_analyzed.sub_category = None
    mock_analyzed.tags = ["重生", "都市", "系统"]
    mock_analyzed.description = "重回2010年，激活马甲系统"
    mock_analyzed.hot_score = None
    mock_analyzed.comment_count = None
    mock_analyzed.like_count = None
    mock_analyzed.read_count = None
    mock_analyzed.collected_at = "2024-01-01"
    mock_analyzed.raw_payload = {}
    mock_analyzed.extracted_genre = "都市重生"
    mock_analyzed.protagonist_template = "重生者"
    mock_analyzed.golden_finger = "系统"
    mock_analyzed.core_hook = "重生2010：我有三千马甲"
    mock_analyzed.reader_desire = "逆袭爽感"
    mock_analyzed.shuang_points = ["逆袭"]
    mock_analyzed.risk_points = []
    mock_analyzed.platform_fit_score = 90.0
    mock_analyzed.competition_score = 80.0
    mock_analyzed.writing_difficulty_score = 30.0
    mock_analyzed.commercial_potential_score = 0.0
    mock_analyzed.analyzed_at = "2024-01-01"
    mock_analyzer.analyzer_version = "1.0.0"
    mock_analyzed.llm_genre = "都市重生"
    mock_analyzed.llm_core_desire = "逆袭"
    mock_analyzed.llm_hook = "重回2010"
    mock_analyzed.llm_golden_finger = "系统"
    mock_analyzed.llm_reader_emotion = ["爽"]
    mock_analyzed.llm_risk = "竞争激烈"

    mock_analyzer.analyze.return_value = [mock_analyzed]
    MockCompositeAnalyzer.return_value = mock_analyzer

    args = MagicMock()
    args.limit = 100
    args.llm = True

    with patch("novelops.radar.cli.RadarStorage") as MockStorage:
        mock_storage = MagicMock()
        mock_storage.list_raw_signals.return_value = [signal]
        mock_storage.save_analyzed_signals.return_value = 1
        MockStorage.return_value = mock_storage

        result = cmd_analyze(args)
        assert result == 0

        MockCompositeAnalyzer.assert_called_once_with(use_llm=True)


@patch("novelops.radar.cli.CommercialScorer")
@patch("novelops.radar.cli.CompositeAnalyzer")
def test_analyze_llm_failure_fallback(MockCompositeAnalyzer, MockScorer, tmp_path):
    """测试 LLM 失败时批量 analyze 可回退规则分析"""
    mock_analyzer = MagicMock()
    mock_analyzed = MagicMock()
    mock_analyzed.signal_id = "test_001"
    mock_analyzed.llm_genre = None
    mock_analyzed.llm_core_desire = None

    mock_analyzer.analyze.return_value = [mock_analyzed]
    MockCompositeAnalyzer.return_value = mock_analyzer

    mock_scorer = MagicMock()
    mock_scorer.score_all.return_value = [mock_analyzed]
    MockScorer.return_value = mock_scorer

    args = MagicMock()
    args.limit = 100
    args.llm = True

    with patch("novelops.radar.cli.RadarStorage") as MockStorage:
        mock_storage = MagicMock()
        signal = RawNovelSignal(
            signal_id="test_001",
            source="fanqie",
            source_type="ranking",
            platform="番茄",
            title="测试小说",
            collected_at="2024-01-01",
        )
        mock_storage.list_raw_signals.return_value = [signal]
        mock_storage.save_analyzed_signals.return_value = 1
        MockStorage.return_value = mock_storage

        result = cmd_analyze(args)
        assert result == 0
