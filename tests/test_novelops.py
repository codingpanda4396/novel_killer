from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from novelops.generator import generate
from novelops.llm import LLMClient, LLMSettings, settings_for_stage
from novelops.config import ConfigError, load_project
from novelops.corpus import get_chapter, list_chapters
from novelops.paths import project_dir
from novelops.reviewer import review_text


class NovelOpsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = project_dir("life_balance")

    def test_project_config_loads(self) -> None:
        config = load_project("life_balance")
        self.assertEqual(config["id"], "life_balance")
        self.assertEqual(config["current_volume"]["next_chapter"], 51)

    def test_volume_one_corpus_has_50_chapters(self) -> None:
        chapters = list_chapters(self.project)
        self.assertEqual(len(chapters), 50)
        self.assertEqual(chapters[0].number, 1)
        self.assertEqual(chapters[-1].number, 50)

    def test_chapter_title_is_parsed(self) -> None:
        chapter = get_chapter(self.project, 1)
        self.assertEqual(chapter.title, "我看见她只剩三分钟可活")
        self.assertGreater(chapter.word_count, 1000)

    def test_review_is_deterministic(self) -> None:
        result = review_text(1, get_chapter(self.project, 1).text, 80)
        self.assertEqual(result.chapter, 1)
        self.assertGreaterEqual(result.score, 0)
        self.assertLessEqual(result.score, 100)
        self.assertIn("hook", result.scores)

    def test_llm_settings_stage_override_and_masking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "models.json"
            config.write_text(
                json.dumps(
                    {
                        "defaults": {"model": "base", "api_key": "secret-key", "temperature": 0.5},
                        "reviewer": {"model": "review-model", "temperature": 0.1},
                    }
                ),
                encoding="utf-8",
            )
            settings = settings_for_stage("reviewer", config)
            self.assertEqual(settings.model, "review-model")
            self.assertEqual(settings.temperature, 0.1)
            self.assertEqual(settings.masked()["api_key"], "***")

    def test_llm_settings_env_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "models.json"
            config.write_text(json.dumps({"defaults": {"temperature": 0.5}}), encoding="utf-8")
            with patch.dict(
                os.environ,
                {
                    "NOVELOPS_API_KEY": "env-key",
                    "NOVELOPS_BASE_URL": "https://example.test/v1",
                    "NOVELOPS_MODEL": "env-model",
                },
                clear=False,
            ):
                settings = settings_for_stage("draft_v1", config)
            self.assertEqual(settings.resolved_api_key, "env-key")
            self.assertEqual(settings.base_url, "https://example.test/v1")
            self.assertEqual(settings.model, "env-model")

    def test_llm_complete_falls_back_without_key(self) -> None:
        client = LLMClient(settings=LLMSettings(api_key=None, api_key_env="MISSING_TEST_KEY"))
        text = client.complete("hello", stage="draft_v1")
        self.assertIn("NO_LLM_MOCK", text)
        self.assertTrue(client.last_used_mock)

    def test_complete_json_parses_json_and_markdown_wrapper(self) -> None:
        class RawClient(LLMClient):
            def __init__(self, raw: str) -> None:
                super().__init__(no_llm=True)
                self.raw = raw

            def complete(self, *args, **kwargs):
                return self.raw

        self.assertEqual(RawClient('{"ok": true}').complete_json("x"), {"ok": True})
        self.assertEqual(RawClient('```json\n{"ok": true}\n```').complete_json("x"), {"ok": True})
        with self.assertRaises(ConfigError):
            RawClient("not json").complete_json("x")

    def test_llm_json_review_parses_structured_result(self) -> None:
        class FakeClient:
            no_llm = False

            def complete_json(self, *args, **kwargs):
                return {
                    "score": 78,
                    "passed": False,
                    "issues": ["冲突不足"],
                    "recommendations": ["加强对抗"],
                    "scores": {"hook": 80, "conflict": 70},
                    "revision_tasks": ["补一个压力场景"],
                    "suggested_action": "revise",
                }

            def settings_for(self, stage):
                return LLMSettings(model="fake-reviewer")

        result = review_text(51, "短正文", 80, llm_client=FakeClient())  # type: ignore[arg-type]
        self.assertFalse(result.passed)
        self.assertEqual(result.model, "fake-reviewer")
        self.assertTrue(result.llm_used)
        self.assertEqual(result.revision_tasks, ["补一个压力场景"])
        self.assertEqual(result.suggested_action, "revise")

    def test_llm_review_invalid_output_falls_back_to_rules(self) -> None:
        class FakeClient:
            no_llm = False

            def complete_json(self, *args, **kwargs):
                raise ConfigError("bad json")

            def settings_for(self, stage):
                return LLMSettings(model="fake-reviewer")

        result = review_text(51, "短正文", 80, llm_client=FakeClient())  # type: ignore[arg-type]
        self.assertFalse(result.llm_used)
        self.assertEqual(result.model, "rules")
        self.assertEqual(result.fallback_reason, "bad json")

    def test_llm_review_clamps_scores_and_normalizes_action(self) -> None:
        class FakeClient:
            no_llm = False

            def complete_json(self, *args, **kwargs):
                return {
                    "score": 140,
                    "passed": True,
                    "issues": [],
                    "recommendations": [],
                    "scores": {"hook": -10, "conflict": 120},
                    "revision_tasks": [],
                    "suggested_action": "ship",
                }

            def settings_for(self, stage):
                return LLMSettings(model="fake-reviewer")

        result = review_text(51, "正文有一个清晰章尾钩子。", 80, llm_client=FakeClient())  # type: ignore[arg-type]
        self.assertEqual(result.score, 100)
        self.assertEqual(result.scores["hook"], 0)
        self.assertEqual(result.scores["conflict"], 100)
        self.assertEqual(result.suggested_action, "accept")

    def test_generate_fake_llm_runs_revision_loop(self) -> None:
        class FakeClient:
            no_llm = False

            def __init__(self) -> None:
                self.reviews = 0

            def complete_json(self, prompt, system=None, stage=None, schema=None):
                if stage == "reviewer":
                    self.reviews += 1
                    score = 70 if self.reviews == 1 else 88
                    return {
                        "score": score,
                        "passed": score >= 80,
                        "issues": [] if score >= 80 else ["节奏偏平"],
                        "recommendations": ["通过"] if score >= 80 else ["增加章尾反转"],
                        "scores": {},
                        "revision_tasks": [] if score >= 80 else ["增加章尾反转"],
                        "suggested_action": "accept" if score >= 80 else "revise",
                    }
                return {"stage": stage, "items": []}

            def complete(self, prompt, system=None, stage=None, response_format=None):
                if stage == "revision":
                    return "# 修订稿\n\n新的反转落在章尾。"
                return f"# {stage}\n\n生成正文。"

            def settings_for(self, stage):
                return LLMSettings(model=f"fake-{stage}")

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            (project / "corpus" / "volume_01").mkdir(parents=True)
            (project / "corpus" / "volume_01" / "chapter_01.md").write_text("# 第1章 起点\n\n正文", encoding="utf-8")
            artifact = generate(project, 2, 80, llm_client=FakeClient())  # type: ignore[arg-type]
            target = project / "generation" / "chapter_002"
            self.assertEqual(artifact.stage, "revision_v1")
            self.assertTrue((target / "08_review_gate.json").is_file())
            self.assertTrue((target / "09_revision_v1.md").is_file())
            self.assertTrue((target / "10_revision_v1_review_gate.json").is_file())

    def test_generate_fake_llm_writes_two_failed_revisions_and_queue(self) -> None:
        class FakeClient:
            no_llm = False

            def complete_json(self, prompt, system=None, stage=None, schema=None):
                if stage == "reviewer":
                    return {
                        "score": 50,
                        "passed": False,
                        "issues": ["冲突不足"],
                        "recommendations": ["增强压力"],
                        "scores": {},
                        "revision_tasks": ["增强压力"],
                        "suggested_action": "reject",
                    }
                return {"stage": stage, "items": []}

            def complete(self, prompt, system=None, stage=None, response_format=None):
                return f"# {stage}\n\n仍未达标。"

            def settings_for(self, stage):
                return LLMSettings(model=f"fake-{stage}")

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            (project / "corpus" / "volume_01").mkdir(parents=True)
            (project / "corpus" / "volume_01" / "chapter_01.md").write_text("# 第1章 起点\n\n正文", encoding="utf-8")
            artifact = generate(project, 2, 80, llm_client=FakeClient())  # type: ignore[arg-type]
            target = project / "generation" / "chapter_002"
            self.assertEqual(artifact.stage, "revision_v2")
            self.assertTrue((target / "11_revision_v2.md").is_file())
            self.assertTrue((target / "12_revision_v2_review_gate.json").is_file())
            self.assertTrue((project / "reviews" / "revision_queue" / "chapter_002.md").is_file())


if __name__ == "__main__":
    unittest.main()
