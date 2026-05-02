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
from novelops.framework_importer import import_framework_project, preview_framework_import
from novelops.planner import plan_next
from novelops.project import init_project
from novelops.paths import project_dir
from novelops.readiness import check_framework_readiness, check_project_readiness
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

    def test_init_project_creates_complete_structure(self) -> None:
        """测试 init_project 创建完整的新书骨架"""
        with tempfile.TemporaryDirectory() as tmp:
            with patch("novelops.paths.PROJECTS_DIR", Path(tmp)):
                project_path = init_project("test_novel", "测试小说", "都市异能")
                
                # 检查基础目录
                self.assertTrue((project_path / "bible").is_dir())
                self.assertTrue((project_path / "outlines").is_dir())
                self.assertTrue((project_path / "state").is_dir())
                
                # 检查 bible 文件
                self.assertTrue((project_path / "bible" / "00_story_bible.md").exists())
                self.assertTrue((project_path / "bible" / "01_characters.md").exists())
                self.assertTrue((project_path / "bible" / "02_power_system.md").exists())
                self.assertTrue((project_path / "bible" / "03_style_guide.md").exists())
                self.assertTrue((project_path / "bible" / "04_forbidden_rules.md").exists())
                self.assertTrue((project_path / "bible" / "11_review_checklist.md").exists())
                
                # 检查 outlines 文件
                self.assertTrue((project_path / "outlines" / "chapter_queue.md").exists())
                self.assertTrue((project_path / "outlines" / "volume_outline.md").exists())
                self.assertTrue((project_path / "outlines" / "first_30_chapters.md").exists())
                
                # 检查 state 文件
                self.assertTrue((project_path / "state" / "timeline.md").exists())
                self.assertTrue((project_path / "state" / "chapter_summary.md").exists())
                self.assertTrue((project_path / "state" / "character_state.md").exists())
                self.assertTrue((project_path / "state" / "active_threads.md").exists())
                self.assertTrue((project_path / "state" / "open_threads.md").exists())
                self.assertTrue((project_path / "state" / "continuity_index.md").exists())
                
                # 检查 project.json
                config = load_project("test_novel")
                self.assertEqual(config["name"], "测试小说")
                self.assertEqual(config["genre"], "都市异能")

    def test_readiness_check_detects_empty_project(self) -> None:
        """测试准备度检查能识别空项目"""
        with tempfile.TemporaryDirectory() as tmp:
            with patch("novelops.paths.PROJECTS_DIR", Path(tmp)):
                project_path = init_project("empty_novel", "空项目", "玄幻")
                config = load_project("empty_novel")
                
                report = check_project_readiness(project_path, config)
                
                # 新项目应该不 ready（因为文件都是模板）
                self.assertFalse(report.ready)
                self.assertGreater(report.critical_missing, 0)
                
                # 检查是否识别出关键缺失项
                critical_items = [item for item in report.items if item.critical and item.status != "ok"]
                self.assertGreater(len(critical_items), 0)

    def test_readiness_check_passes_filled_project(self) -> None:
        """测试准备度检查能识别已填充项目"""
        # life_balance 项目应该是 ready 的
        config = load_project("life_balance")
        report = check_project_readiness(self.project, config)
        
        # 应该通过准备度检查
        self.assertTrue(report.ready)
        self.assertEqual(report.critical_missing, 0)

    def test_import_framework_dry_run_returns_structured_spec(self) -> None:
        preview = preview_framework_import("xianghuo_demo", "# 框架", llm_client=FakeFrameworkClient())  # type: ignore[arg-type]
        self.assertEqual(preview.spec.title, "香火成神")
        self.assertEqual(len(preview.spec.chapter_cards), 40)
        self.assertFalse(Path("projects/xianghuo_demo").exists())

    def test_import_framework_creates_project_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("novelops.paths.PROJECTS_DIR", Path(tmp)):
                preview = import_framework_project("xianghuo_demo", "# 框架", llm_client=FakeFrameworkClient())  # type: ignore[arg-type]
                project = Path(tmp) / "xianghuo_demo"
                self.assertTrue((project / "project.json").is_file())
                self.assertTrue((project / "bible" / "02_power_system.md").is_file())
                self.assertTrue((project / "outlines" / "first_40_chapters.md").is_file())
                self.assertTrue((project / "records" / "data_feedback.md").is_file())
                queue_rows = [line for line in (project / "outlines" / "chapter_queue.md").read_text(encoding="utf-8").splitlines() if line.startswith("| ") and line[2].isdigit()]
                self.assertEqual(len(queue_rows), 40)
                config = json.loads((project / "project.json").read_text(encoding="utf-8"))
                self.assertGreaterEqual(len(config["rubric"]["hook_terms"]), 5)
                self.assertGreaterEqual(len(config["rubric"]["forbidden_terms"]), 5)
                self.assertTrue(preview.readiness.ready)

    def test_import_framework_rejects_existing_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("novelops.paths.PROJECTS_DIR", Path(tmp)):
                existing = Path(tmp) / "xianghuo_demo"
                existing.mkdir()
                marker = existing / "keep.txt"
                marker.write_text("keep", encoding="utf-8")
                with self.assertRaises(ConfigError):
                    import_framework_project("xianghuo_demo", "# 框架", llm_client=FakeFrameworkClient())  # type: ignore[arg-type]
                self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_framework_readiness_fails_when_queue_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("novelops.paths.PROJECTS_DIR", Path(tmp)):
                import_framework_project("xianghuo_demo", "# 框架", llm_client=FakeFrameworkClient())  # type: ignore[arg-type]
                project = Path(tmp) / "xianghuo_demo"
                (project / "outlines" / "chapter_queue.md").write_text("| 章号 | 工作标题 | 核心任务 | 必须承接 | 状态 |\n", encoding="utf-8")
                config = json.loads((project / "project.json").read_text(encoding="utf-8"))
                report = check_framework_readiness(project, config)
                self.assertFalse(report.ready)

    def test_framework_readiness_fails_without_first_three_payoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("novelops.paths.PROJECTS_DIR", Path(tmp)):
                import_framework_project("xianghuo_demo", "# 框架", llm_client=FakeFrameworkClient())  # type: ignore[arg-type]
                project = Path(tmp) / "xianghuo_demo"
                queue = project / "outlines" / "chapter_queue.md"
                queue.write_text(queue.read_text(encoding="utf-8").replace("显圣反杀", "公开胜利"), encoding="utf-8")
                config = json.loads((project / "project.json").read_text(encoding="utf-8"))
                report = check_framework_readiness(project, config)
                self.assertFalse(report.ready)

    def test_web_import_framework_preview_and_execute(self) -> None:
        try:
            from fastapi.testclient import TestClient
            from novelops.session import SESSION_COOKIE_NAME, get_serializer
            from novelops.web import create_app
        except Exception as exc:  # pragma: no cover
            self.skipTest(f"FastAPI test dependencies unavailable: {exc}")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"NOVELOPS_DB": str(Path(tmp) / "novelops.sqlite3")}, clear=False), \
                 patch("novelops.paths.PROJECTS_DIR", Path(tmp)), \
                 patch("novelops.framework_importer.LLMClient", lambda: FakeFrameworkClient()):
                client = TestClient(create_app())
                client.cookies.set(SESSION_COOKIE_NAME, get_serializer().dumps({"user_id": "user1"}))
                payload = {"project_id": "xianghuo_demo", "framework_markdown": "# 框架", "execute": False}
                preview = client.post("/api/import-framework", json=payload)
                self.assertEqual(preview.status_code, 200)
                self.assertFalse((Path(tmp) / "xianghuo_demo").exists())
                execute = client.post("/api/import-framework", json={**payload, "execute": True})
                self.assertEqual(execute.status_code, 200)
                self.assertTrue((Path(tmp) / "xianghuo_demo" / "project.json").is_file())
                self.assertEqual(execute.json()["status"], "created")


class FakeFrameworkClient:
    def complete_json(self, *args, **kwargs):
        return fake_framework_spec()


def fake_framework_spec() -> dict[str, object]:
    cards = []
    for chapter in range(1, 41):
        if chapter == 1:
            objective = "被逐受辱危机开局，主角失去庙产"
        elif chapter == 2:
            objective = "香火金手指出现，主角确认神道规则"
        elif chapter == 3:
            objective = "第一次显圣反杀，夺回村民信任"
        elif chapter == 8:
            objective = "第一次大打脸，乡绅阴谋败露"
        else:
            objective = f"推进第 {chapter} 章冷启动阶段目标"
        cards.append(
            {
                "chapter": chapter,
                "title": f"第{chapter}章香火试炼",
                "objective": objective,
                "conflict": "信众利益与反派压迫正面碰撞",
                "爽点": "香火显威，凡人得到实际好处",
                "ending_hook": "新的神像裂纹暴露更大敌人",
                "must_continue_from": "承接上一章香火变化",
            }
        )
    return {
        "title": "香火成神",
        "genre": "玄幻神道",
        "target_platform": "番茄免费阅读冷启动测试",
        "one_sentence_pitch": "落魄庙祝靠香火金手指护凡人成神。",
        "tags": ["香火", "神道", "凡人流", "打脸", "升级"],
        "commercial_positioning": "男频免费阅读冷启动爽文，前三章兑现显圣反杀。",
        "core_selling_points": ["香火规则可视化", "凡人利益强绑定", "反派压迫持续打脸"],
        "protagonist": {"name": "陈玄", "goal": "重建山神庙", "boundary": "不圣母"},
        "main_antagonists": [{"name": "刘乡绅", "role": "开局压迫者"}],
        "supporting_characters": [{"name": "阿禾", "role": "第一个信众"}],
        "world_rules": ["香火来自真实信任", "显圣必须消耗香火"],
        "power_system": {"rules": ["香火入账后才能显圣"], "growth_path": ["庙祝", "山神"], "limits": ["信众背弃会反噬"]},
        "phase_targets": {
            "0-2万字": "完成危机、金手指、显圣反杀和第一次打脸。",
            "2-5万字": "扩大村落信众，建立反派反制。",
            "5-8万字": "打穿乡镇线，证明神道规则可持续。",
            "8-10万字": "进入县城新地图，留下更大敌人。",
        },
        "required_beats": ["被逐受辱", "金手指出现", "显圣反杀", "第一次大打脸"],
        "forbidden_moves": ["主角圣母", "机械降神", "凡人背景板", "跳过代价", "无冲突升级"],
        "hook_terms": ["显圣", "香火", "反杀", "打脸", "神像裂纹"],
        "forbidden_terms": ["涉政", "色情", "血腥猎奇", "封建迷信宣扬", "机械降神"],
        "chapter_cards": cards,
    }


if __name__ == "__main__":
    unittest.main()
