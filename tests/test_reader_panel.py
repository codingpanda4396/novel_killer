from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from novelops.llm import LLMSettings
from novelops.readers.loader import load_all_personas, load_persona
from novelops.readers.panel import PanelReport, PersonaReview, review_panel
from novelops.readers.persona import PersonaSpec, parse_persona_file, parse_persona_text


FAST_FOOD_PROMPT = """---
name: reader_fast_food
display_name: 快餐读者
scoring_dimensions: [pacing, hook_strength, shuang_release, retention_to_next]
red_flags:
  - 大段心理描写超过 3 段
  - 章节末没有具体钩子
weight: 1.0
version: v1
---

你是一位快餐读者。只返回 JSON。
"""

EMOTIONAL_PROMPT = """---
name: reader_emotional
display_name: 情感读者
scoring_dimensions: [character_depth, emotional_resonance]
red_flags:
  - 角色行为不符合已建立的人设
weight: 0.8
version: v1
---

你是一位情感读者。只返回 JSON。
"""


class FakeLLMClient:
    def __init__(self, score: float = 80.0):
        self._score = score
        self.live_call_count = 0

    def complete_json(self, prompt, system=None, stage=None, schema=None):
        self.live_call_count += 1
        return {
            "overall_score": self._score,
            "dimension_scores": {"pacing": self._score, "hook_strength": self._score},
            "flagged_red_flags": [],
            "quotes": [],
            "verdict": "love" if self._score >= 70 else "okay",
            "revision_suggestions": [],
        }

    def settings_for(self, stage=None):
        return LLMSettings(model="fake")


class PersonaSpecTests(unittest.TestCase):
    def test_parse_frontmatter(self) -> None:
        spec = parse_persona_text(FAST_FOOD_PROMPT, "test")
        self.assertEqual(spec.name, "reader_fast_food")
        self.assertEqual(spec.display_name, "快餐读者")
        self.assertEqual(len(spec.scoring_dimensions), 4)
        self.assertIn("pacing", spec.scoring_dimensions)
        self.assertEqual(len(spec.red_flags), 2)
        self.assertEqual(spec.weight, 1.0)
        self.assertEqual(spec.version, "v1")
        self.assertIn("快餐读者", spec.system_prompt)

    def test_parse_persona_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.md"
            path.write_text(FAST_FOOD_PROMPT, encoding="utf-8")
            spec = parse_persona_file(path)
            self.assertEqual(spec.name, "reader_fast_food")


class LoaderTests(unittest.TestCase):
    def test_load_all_personas_from_real_dir(self) -> None:
        """Load all 5 persona prompts from the actual prompts/readers directory."""
        personas = load_all_personas()
        self.assertEqual(len(personas), 5)
        names = {p.name for p in personas}
        self.assertIn("reader_fast_food", names)
        self.assertIn("reader_emotional", names)
        self.assertIn("reader_setting_fan", names)
        self.assertIn("platform_editor", names)
        self.assertIn("cold_reader", names)

    def test_load_persona_by_name(self) -> None:
        spec = load_persona("reader_fast_food")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.name, "reader_fast_food")
        self.assertIn("pacing", spec.scoring_dimensions)


class PanelReviewTests(unittest.TestCase):
    def test_panel_with_stub_llm(self) -> None:
        """Test panel review with 2 stub personas."""
        spec1 = parse_persona_text(FAST_FOOD_PROMPT, "fast_food")
        spec2 = parse_persona_text(EMOTIONAL_PROMPT, "emotional")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "state").mkdir()
            (root / "story" / "bible").mkdir(parents=True)
            (root / "project.json").write_text(json.dumps({"directories": {}}), encoding="utf-8")

            fake_llm = FakeLLMClient(score=85.0)
            report = review_panel(
                chapter=1,
                chapter_text="这是测试章节内容。" * 100,
                project_path=root,
                llm_client=fake_llm,
                personas=[spec1, spec2],
            )

            self.assertEqual(report.chapter, 1)
            self.assertEqual(len(report.panel), 2)
            self.assertGreater(report.weighted_score, 0)
            self.assertFalse(report.dissent)  # Same score, no dissent

    def test_dissent_detection(self) -> None:
        """Test that dissent is detected when score spread > 25."""
        spec1 = parse_persona_text(FAST_FOOD_PROMPT, "fast_food")
        spec2 = parse_persona_text(EMOTIONAL_PROMPT, "emotional")

        class VaryingLLM:
            def __init__(self):
                self.live_call_count = 0
                self._scores = [90.0, 60.0]

            def complete_json(self, prompt, system=None, stage=None, schema=None):
                idx = self.live_call_count
                self.live_call_count += 1
                score = self._scores[idx] if idx < len(self._scores) else 70.0
                return {
                    "overall_score": score,
                    "dimension_scores": {},
                    "flagged_red_flags": [],
                    "quotes": [],
                    "verdict": "love" if score >= 70 else "okay",
                    "revision_suggestions": [],
                }

            def settings_for(self, stage=None):
                return LLMSettings(model="fake")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "state").mkdir()
            (root / "project.json").write_text(json.dumps({"directories": {}}), encoding="utf-8")

            report = review_panel(
                chapter=1,
                chapter_text="测试内容。" * 100,
                project_path=root,
                llm_client=VaryingLLM(),
                personas=[spec1, spec2],
            )

            self.assertTrue(report.dissent)
            self.assertGreater(report.score_spread, 25)

    def test_consensus_red_flags(self) -> None:
        """Test that red flags flagged by >= 2 personas become consensus."""
        spec1 = parse_persona_text(FAST_FOOD_PROMPT, "fast_food")
        spec2 = parse_persona_text(EMOTIONAL_PROMPT, "emotional")

        class RedFlagLLM:
            def __init__(self):
                self.live_call_count = 0

            def complete_json(self, prompt, system=None, stage=None, schema=None):
                self.live_call_count += 1
                return {
                    "overall_score": 70.0,
                    "dimension_scores": {},
                    "flagged_red_flags": ["大段心理描写超过 3 段"],
                    "quotes": [],
                    "verdict": "okay",
                    "revision_suggestions": ["减少心理描写"],
                }

            def settings_for(self, stage=None):
                return LLMSettings(model="fake")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "state").mkdir()
            (root / "project.json").write_text(json.dumps({"directories": {}}), encoding="utf-8")

            report = review_panel(
                chapter=1,
                chapter_text="测试内容。" * 100,
                project_path=root,
                llm_client=RedFlagLLM(),
                personas=[spec1, spec2],
            )

            self.assertEqual(len(report.consensus_red_flags), 1)
            self.assertIn("大段心理描写超过 3 段", report.consensus_red_flags)


if __name__ == "__main__":
    unittest.main()
