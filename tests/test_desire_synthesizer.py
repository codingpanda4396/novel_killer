from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from novelops.desire.aggregators import (
    aggregate_desires,
    aggregate_emotions,
    aggregate_golden_fingers,
    aggregate_hooks,
    aggregate_risks,
    build_competitor_patterns,
    build_trope_library,
)
from novelops.desire.schemas import DemandStatement, ReaderPersonaProfile
from novelops.desire.synthesizer import DesireSynthesizer
from novelops.llm import LLMSettings


class FakeLLMClient:
    """Stub LLM client for testing."""

    def __init__(self, demand_result=None, persona_result=None):
        self._demand = demand_result or []
        self._persona = persona_result or []
        self.live_call_count = 0

    def complete_json(self, prompt, system=None, stage=None, schema=None):
        self.live_call_count += 1
        if "欲望集群" in prompt or "demand" in prompt.lower():
            return self._demand
        if "画像" in prompt or "persona" in prompt.lower():
            return self._persona
        return {}

    def settings_for(self, stage=None):
        return LLMSettings(model="fake")


class AggregatorTests(unittest.TestCase):
    def test_aggregate_emotions(self) -> None:
        signals = [
            {"llm_reader_emotion": '["爽", "期待"]'},
            {"llm_reader_emotion": '["爽", "紧张"]'},
            {"llm_reader_emotion": ""},
        ]
        result = aggregate_emotions(signals)
        self.assertEqual(result[0], ("爽", 2))
        self.assertEqual(result[1][0], "期待")
        self.assertEqual(result[2][0], "紧张")

    def test_aggregate_golden_fingers(self) -> None:
        signals = [
            {"llm_golden_finger": "系统面板"},
            {"llm_golden_finger": "系统面板"},
            {"llm_golden_finger": "无明显金手指"},
            {"llm_golden_finger": "重生记忆"},
        ]
        result = aggregate_golden_fingers(signals)
        self.assertEqual(result[0], ("系统面板", 2))
        self.assertEqual(len(result), 2)  # "无明显金手指" is excluded

    def test_aggregate_hooks(self) -> None:
        signals = [
            {"llm_hook": "开局被退婚"},
            {"llm_hook": "开局被退婚"},
            {"llm_hook": "开局被甩"},
        ]
        result = aggregate_hooks(signals)
        self.assertEqual(result[0], ("开局被退婚", 2))

    def test_aggregate_desires(self) -> None:
        signals = [
            {"llm_core_desire": "逆袭打脸"},
            {"llm_core_desire": "逆袭打脸"},
            {"llm_core_desire": "躺赢"},
        ]
        result = aggregate_desires(signals)
        self.assertEqual(result[0], ("逆袭打脸", 2))

    def test_build_trope_library(self) -> None:
        signals = [
            {"llm_genre": "都市重生", "llm_hook": "重生回高中", "llm_golden_finger": "重生记忆", "platform": "番茄"},
            {"llm_genre": "都市重生", "llm_hook": "重生回大学", "llm_golden_finger": "重生记忆", "platform": "起点"},
        ]
        result = build_trope_library(signals)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "都市重生")
        self.assertEqual(result[0]["frequency"], 2)

    def test_build_competitor_patterns(self) -> None:
        signals = [
            {"llm_genre": "仙侠", "llm_hook": "废材逆袭", "llm_risk": "同质化严重"},
        ]
        result = build_competitor_patterns(signals)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["genre"], "仙侠")


class SynthesizerTests(unittest.TestCase):
    def test_synthesizer_with_no_signals(self) -> None:
        """Synthesizer should handle empty signals gracefully."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create market dir
            (root / "market").mkdir()
            (root / "project.json").write_text(
                json.dumps({"id": "test", "genre": "都市", "directories": {}}),
                encoding="utf-8",
            )
            # Patch radar DB path to return empty
            with patch("novelops.desire.synthesizer.fetch_analyzed_signals", return_value=[]):
                synthesizer = DesireSynthesizer(root)
                result = synthesizer.run(window_days=14, force=True)
                self.assertEqual(result.signal_count, 0)
                self.assertEqual(len(result.demands), 0)

    def test_synthesizer_with_stub_llm(self) -> None:
        """Synthesizer should produce markdown files with stub LLM."""
        fake_demands = [
            {
                "cluster_name": "逆袭欲",
                "desire_statement": "被压迫后逆袭打脸",
                "frequency": 10,
                "representative_titles": ["赘婿", "龙王"],
                "linked_emotions": ["爽", "期待"],
                "recommended_golden_fingers": ["系统面板"],
                "risk": "同质化",
            }
        ]
        fake_personas = [
            {
                "name": "fast_food",
                "display_name": "快餐读者",
                "wants": ["快节奏", "爽点密集"],
                "dislikes": ["大段描写"],
                "typical_emotions": ["爽"],
                "representative_works": ["赘婿"],
                "share_pct": 40.0,
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "market").mkdir()
            (root / "project.json").write_text(
                json.dumps({"id": "test", "genre": "都市", "directories": {}}),
                encoding="utf-8",
            )

            fake_signals = [
                {
                    "signal_id": "s1",
                    "title": "测试书",
                    "platform": "番茄",
                    "llm_genre": "都市",
                    "llm_core_desire": "逆袭",
                    "llm_hook": "开局被退婚",
                    "llm_golden_finger": "系统",
                    "llm_reader_emotion": '["爽"]',
                    "llm_risk": "同质化",
                    "analyzed_at": "2026-05-08T00:00:00",
                }
            ]

            with patch("novelops.desire.synthesizer.fetch_analyzed_signals", return_value=fake_signals):
                fake_llm = FakeLLMClient(demand_result=fake_demands, persona_result=fake_personas)
                synthesizer = DesireSynthesizer(root, llm_client=fake_llm)
                result = synthesizer.run(window_days=14, force=True)

                self.assertEqual(result.signal_count, 1)
                self.assertEqual(len(result.demands), 1)
                self.assertEqual(result.demands[0].cluster_name, "逆袭欲")
                self.assertEqual(len(result.personas), 1)

                # Check markdown files exist
                self.assertTrue((root / "market" / "demand_analysis.md").is_file())
                self.assertTrue((root / "market" / "reader_personas.md").is_file())
                self.assertTrue((root / "market" / "trope_library.md").is_file())
                self.assertTrue((root / "market" / "competitor_patterns.md").is_file())
                self.assertTrue((root / "market" / ".desire_synthesis.json").is_file())

                # Check demand_analysis.md content
                content = (root / "market" / "demand_analysis.md").read_text()
                self.assertIn("逆袭欲", content)
                self.assertIn("被压迫后逆袭打脸", content)

    def test_idempotency(self) -> None:
        """Second run with same signals should skip."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "market").mkdir()
            (root / "project.json").write_text(
                json.dumps({"id": "test", "genre": "都市", "directories": {}}),
                encoding="utf-8",
            )

            fake_signals = [
                {"signal_id": "s1", "title": "t", "platform": "p", "llm_genre": "g",
                 "llm_core_desire": "d", "llm_hook": "h", "llm_golden_finger": "gf",
                 "llm_reader_emotion": "[]", "llm_risk": "r", "analyzed_at": "2026-05-08T00:00:00"}
            ]

            with patch("novelops.desire.synthesizer.fetch_analyzed_signals", return_value=fake_signals):
                fake_llm = FakeLLMClient(demand_result=[], persona_result=[])
                synthesizer = DesireSynthesizer(root, llm_client=fake_llm)

                # First run
                result1 = synthesizer.run(window_days=14, force=True)
                self.assertEqual(fake_llm.live_call_count, 2)

                # Second run (should skip)
                fake_llm.live_call_count = 0
                result2 = synthesizer.run(window_days=14, force=False)
                self.assertEqual(fake_llm.live_call_count, 0)


if __name__ == "__main__":
    unittest.main()
