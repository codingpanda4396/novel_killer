from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from novelops.config import write_json
from novelops.generator import generate
from novelops.indexer import rebuild_index
from novelops.llm import LLMClient, LLMSettings, settings_for_stage
from novelops.config import ConfigError, load_project
from novelops.corpus import get_chapter, list_chapters
from novelops.planner import plan_next
from novelops.project import init_project
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

    def test_review_uses_llm_client(self) -> None:
        class FakeClient:
            def complete_json(self, *args, **kwargs):
                return {
                    "score": 86,
                    "passed": True,
                    "issues": [],
                    "recommendations": ["保持章尾钩子清晰。"],
                    "scores": {},
                    "revision_tasks": [],
                    "suggested_action": "accept",
                }

            def settings_for(self, stage):
                return LLMSettings(model="fake-reviewer")

        result = review_text(1, get_chapter(self.project, 1).text, 80, llm_client=FakeClient())  # type: ignore[arg-type]
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

    def test_explicit_api_key_env_is_not_overridden_by_generic_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "models.json"
            config.write_text(
                json.dumps(
                    {
                        "assistant": {
                            "api_key_env": "DEEPSEEK_API_KEY",
                            "base_url": "https://api.deepseek.com",
                            "model": "deepseek-chat",
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"NOVELOPS_API_KEY": "generic-key", "DEEPSEEK_API_KEY": "deepseek-key"}, clear=False):
                settings = settings_for_stage("assistant", config)
                self.assertEqual(settings.api_key_env, "DEEPSEEK_API_KEY")
                self.assertEqual(settings.resolved_api_key, "deepseek-key")
                self.assertEqual(settings.base_url, "https://api.deepseek.com")

    def test_llm_complete_requires_api_key(self) -> None:
        client = LLMClient(settings=LLMSettings(api_key=None, api_key_env="MISSING_TEST_KEY"))
        with self.assertRaises(ConfigError):
            client.complete("hello", stage="draft_v1")

    def test_complete_json_parses_json_and_markdown_wrapper(self) -> None:
        class RawClient(LLMClient):
            def __init__(self, raw: str) -> None:
                super().__init__()
                self.raw = raw

            def complete(self, *args, **kwargs):
                return self.raw

        self.assertEqual(RawClient('{"ok": true}').complete_json("x"), {"ok": True})
        self.assertEqual(RawClient('```json\n{"ok": true}\n```').complete_json("x"), {"ok": True})
        with self.assertRaises(ConfigError):
            RawClient("not json").complete_json("x")

    def test_llm_json_review_parses_structured_result(self) -> None:
        class FakeClient:
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

    def test_llm_review_invalid_output_raises(self) -> None:
        class FakeClient:
            def complete_json(self, *args, **kwargs):
                raise ConfigError("bad json")

            def settings_for(self, stage):
                return LLMSettings(model="fake-reviewer")

        with self.assertRaises(ConfigError):
            review_text(51, "短正文", 80, llm_client=FakeClient())  # type: ignore[arg-type]

    def test_llm_review_clamps_scores_and_normalizes_action(self) -> None:
        class FakeClient:
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

    def test_init_project_creates_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("novelops.project.project_dir", lambda project_id: root / project_id):
                path = init_project("demo", "测试项目", "仙侠升级流")
            self.assertTrue((path / "project.json").is_file())
            self.assertTrue((path / "bible" / "00_story_bible.md").is_file())
            self.assertTrue((path / "corpus" / "volume_01").is_dir())
            data = json.loads((path / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(data["language"], "zh-CN")
            self.assertIn("rubric", data)

    def test_plan_next_reads_chapter_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            (project / "outlines").mkdir(parents=True)
            (project / "bible").mkdir()
            (project / "state").mkdir()
            (project / "corpus" / "volume_01").mkdir(parents=True)
            write_json(
                project / "project.json",
                {
                    "id": "demo",
                    "name": "测试项目",
                    "genre": "仙侠升级流",
                    "current_volume": {"number": 1},
                    "rubric": {"forbidden_terms": ["机械降神"]},
                },
            )
            (project / "outlines" / "chapter_queue.md").write_text(
                "| 章号 | 工作标题 | 核心任务 | 必须承接 | 状态 |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| 1 | 入山试炼 | 让主角进入宗门考核 | 村口冲突 | 待规划 |\n",
                encoding="utf-8",
            )
            plan, intent, _ = plan_next(project, 1)
            self.assertEqual(plan.title, "入山试炼")
            self.assertIn("宗门考核", plan.objective)
            self.assertIn("机械降神", intent.forbidden_moves)

    def test_cli_rejects_no_llm_flag_for_generation(self) -> None:
        from novelops.cli import build_parser

        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            build_parser().parse_args(["generate", "1", "--no-llm"])

    def test_index_life_balance_to_temp_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "novelops.sqlite3"
            path = rebuild_index("life_balance", db)
            self.assertTrue(path.is_file())
            import sqlite3

            conn = sqlite3.connect(path)
            try:
                count = conn.execute("SELECT COUNT(*) FROM projects WHERE id = 'life_balance'").fetchone()[0]
                chapters = conn.execute("SELECT COUNT(*) FROM chapters WHERE project_id = 'life_balance'").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(count, 1)
            self.assertGreaterEqual(chapters, 50)

    def test_web_routes_return_200(self) -> None:
        try:
            from fastapi.testclient import TestClient
            from novelops.web import create_app
        except Exception as exc:  # pragma: no cover
            self.skipTest(f"FastAPI test dependencies unavailable: {exc}")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"NOVELOPS_DB": str(Path(tmp) / "novelops.sqlite3")}, clear=False):
                rebuild_index("life_balance")
                client = TestClient(create_app())
                self.assertEqual(client.get("/").status_code, 200)
                self.assertEqual(client.get("/projects/life_balance").status_code, 200)
                self.assertEqual(client.get("/projects/life_balance/chapters/1").status_code, 200)
                self.assertEqual(client.get("/revision-queue").status_code, 200)

    def test_assistant_llm_status_and_explain_review(self) -> None:
        from novelops.assistant import AssistantOrchestrator

        class FakeAssistantClient:
            def complete_json(self, prompt, system=None, stage=None, schema=None):
                if "解释" in prompt:
                    return {"intent": "explain_review", "project": "life_balance", "chapter": 51, "confidence": 0.99}
                return {"intent": "status", "project": "life_balance", "confidence": 0.99}

        orchestrator = AssistantOrchestrator(default_project="life_balance", llm_client=FakeAssistantClient())  # type: ignore[arg-type]
        status = orchestrator.handle("查看 life_balance 状态")
        self.assertEqual(status.intent.name, "status")
        self.assertIn("下一章", status.message)
        self.assertEqual(status.result["next_chapter"], 51)

        review = orchestrator.handle("解释 life_balance 第51章为什么审稿没过")
        self.assertEqual(review.intent.name, "explain_review")
        self.assertFalse(review.result["passed"])
        self.assertIn("主要问题", review.message)

    def test_assistant_generate_requires_confirmation(self) -> None:
        from novelops.assistant import AssistantOrchestrator

        class FakeAssistantClient:
            def complete_json(self, prompt, system=None, stage=None, schema=None):
                return {"intent": "generate", "project": "life_balance", "confidence": 0.99}

        response = AssistantOrchestrator(default_project="life_balance", llm_client=FakeAssistantClient()).handle("给 life_balance 生成下一章")  # type: ignore[arg-type]
        self.assertEqual(response.intent.name, "generate")
        self.assertEqual(response.intent.chapter, 51)
        self.assertTrue(response.requires_confirmation)
        self.assertIsNone(response.result)
        self.assertIn("--yes", response.message)

    def test_assistant_init_project_missing_fields_and_forbidden(self) -> None:
        from novelops.assistant import AssistantOrchestrator

        class FakeAssistantClient:
            def complete_json(self, prompt, system=None, stage=None, schema=None):
                return {"intent": "init_project", "project_id": "demo", "name": "测试项目", "missing_fields": ["genre"]}

        missing = AssistantOrchestrator(default_project="life_balance", llm_client=FakeAssistantClient()).handle("创建一个新项目")  # type: ignore[arg-type]
        self.assertEqual(missing.intent.name, "init_project")
        self.assertIn("genre", missing.intent.missing_fields)
        self.assertIn("需要项目", missing.message)

        forbidden = AssistantOrchestrator(default_project="life_balance", llm_client=FakeAssistantClient()).handle("删除 life_balance 的 corpus")  # type: ignore[arg-type]
        self.assertTrue(forbidden.errors)
        self.assertIn("不会执行", forbidden.message)

    def test_assistant_llm_invalid_json_returns_error(self) -> None:
        class BadClient:
            def complete_json(self, *args, **kwargs):
                raise ConfigError("bad json")

        from novelops.assistant import AssistantOrchestrator

        response = AssistantOrchestrator(default_project="life_balance", llm_client=BadClient()).handle("检查 life_balance 状态")
        self.assertEqual(response.intent.name, "unknown")
        self.assertTrue(response.errors)
        self.assertIn("需要可用的 LLM", response.message)

    def test_web_api_ask_and_forms(self) -> None:
        try:
            from fastapi.testclient import TestClient
            from novelops.web import create_app
        except Exception as exc:  # pragma: no cover
            self.skipTest(f"FastAPI test dependencies unavailable: {exc}")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"NOVELOPS_DB": str(Path(tmp) / "novelops.sqlite3")}, clear=False):
                rebuild_index("life_balance")
                client = TestClient(create_app())
                def fake_ask(message, default_project=None, execute=False):
                    from novelops.assistant import AssistantIntent, AssistantResponse

                    if "生成" in message:
                        return AssistantResponse(
                            message="需要确认",
                            intent=AssistantIntent(name="generate", project=default_project, chapter=51),
                            requires_confirmation=True,
                        )
                    return AssistantResponse(
                        message="状态正常",
                        intent=AssistantIntent(name="status", project=default_project),
                        result={"project": default_project},
                    )

                with patch("novelops.web.ask", fake_ask):
                    response = client.post("/api/ask", json={"message": "查看状态", "project": "life_balance"})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["intent"]["name"], "status")
                    preview = client.post("/api/ask", json={"message": "给当前项目生成下一章", "project": "life_balance"})
                    self.assertTrue(preview.json()["requires_confirmation"])
                    self.assertIn("data-ask-form", client.get("/").text)
                    self.assertIn("data-ask-form", client.get("/projects/life_balance").text)


if __name__ == "__main__":
    unittest.main()
