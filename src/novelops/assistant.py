from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .config import ConfigError, default_project_id, load_project, threshold
from .corpus import list_chapters
from .generator import generate
from .indexer import connect, rebuild_index
from .llm import LLMClient
from .paths import all_project_dirs, project_dir, rel
from .planner import plan_next
from .project import STANDARD_DIRS, init_project
from .reviewer import review_chapter
from .schemas import to_dict


INTENTS = {
    "status",
    "check",
    "init_project",
    "plan_next",
    "generate",
    "review_chapter",
    "index",
    "explain_review",
    "show_revision_queue",
    "serve_help",
    "unknown",
    "radar_collect",
    "radar_analyze",
    "radar_report",
    "radar_analyze_text",
    "pipeline_run",
    "pipeline_status",
    "pipeline_approve",
    "pipeline_reject",
    "prepare_project",
    "readiness_check",
}
AUTO_EXECUTE = {"status", "check", "plan_next", "review_chapter", "index", "explain_review", "show_revision_queue", "serve_help", "pipeline_status"}
CONFIRM_EXECUTE = {"init_project", "generate", "radar_collect", "radar_analyze", "pipeline_run", "prepare_project"}
FORBIDDEN_PATTERNS = [
    ("delete", r"删除|移除|清空|rm\s+-rf"),
    ("overwrite_corpus", r"覆盖.*corpus|重写.*语料|覆盖.*正文语料"),
    ("publish_ready", r"发布到|publish/ready|上线|推送发布"),
    ("edit_state", r"修改.*(bible|outlines|state)|改写.*(bible|大纲|状态)"),
    ("batch_review", r"批量.*审|review-range|publish-check|发布检查"),
]


@dataclass(frozen=True)
class AssistantIntent:
    name: str = "unknown"
    project: str | None = None
    chapter: int | None = None
    project_id: str | None = None
    display_name: str | None = None
    genre: str | None = None
    target_platform: str | None = None
    missing_fields: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass(frozen=True)
class AssistantResponse:
    message: str
    intent: AssistantIntent
    actions: list[dict[str, Any]] = field(default_factory=list)
    requires_confirmation: bool = False
    result: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ask(message: str, default_project: str | None = None, execute: bool = False) -> AssistantResponse:
    orchestrator = AssistantOrchestrator(default_project=default_project)
    return orchestrator.handle(message, execute=execute)


class AssistantOrchestrator:
    def __init__(self, default_project: str | None = None, llm_client: LLMClient | None = None) -> None:
        self.default_project = default_project or default_project_id()
        self.llm_client = llm_client or LLMClient()

    def handle(self, message: str, execute: bool = False) -> AssistantResponse:
        text = message.strip()
        if not text:
            return _unknown("请告诉我你想查看、检查、规划、生成或审稿的内容。")
        forbidden = _forbidden_reason(text)
        if forbidden:
            return AssistantResponse(
                message=f"这个自然语言入口不会执行该操作：{forbidden}。请改用明确 CLI 命令并手动确认。",
                intent=AssistantIntent(name="unknown", project=self.default_project),
                errors=[forbidden],
            )
        try:
            intent = self._parse(text)
        except Exception as exc:
            return AssistantResponse(
                message=f"自然语言解析需要可用的 LLM，当前无法解析：{exc}",
                intent=AssistantIntent(name="unknown", project=self.default_project),
                errors=[str(exc)],
            )
        intent = self._with_defaults(intent)
        missing = _missing_fields(intent)
        if missing:
            intent = _replace_intent(intent, missing_fields=missing)
            return AssistantResponse(message=_missing_message(intent), intent=intent, actions=_preview_actions(intent), errors=[])
        if intent.name == "unknown":
            return _unknown(project=intent.project)
        actions = _preview_actions(intent)
        if intent.name in CONFIRM_EXECUTE and not execute:
            return AssistantResponse(
                message=_confirmation_message(intent),
                intent=intent,
                actions=actions,
                requires_confirmation=True,
            )
        try:
            result = self._execute(intent)
        except Exception as exc:
            return AssistantResponse(
                message=f"执行失败：{exc}",
                intent=intent,
                actions=actions,
                errors=[str(exc)],
            )
        return AssistantResponse(message=_success_message(intent, result), intent=intent, actions=actions, result=result)

    def _parse(self, text: str) -> AssistantIntent:
        data = self.llm_client.complete_json(
            _assistant_prompt(text, self.default_project),
            system="你是 NovelOps 自然语言命令解析器。只返回 JSON 对象，不要 Markdown。",
            stage="assistant",
            schema={"type": "json_object"},
        )
        return _normalize_intent(data, text, self.default_project)

    def _with_defaults(self, intent: AssistantIntent) -> AssistantIntent:
        project = intent.project or self.default_project
        chapter = intent.chapter
        if intent.name in {"plan_next", "generate"} and chapter is None and project:
            try:
                chapter = int(load_project(project).get("current_volume", {}).get("next_chapter") or 1)
            except Exception:
                chapter = None
        if intent.name in {"review_chapter", "explain_review"} and chapter is None and project:
            chapter = _latest_review_chapter(project) if intent.name == "explain_review" else _latest_available_chapter(project)
        return _replace_intent(intent, project=project, chapter=chapter)

    def _execute(self, intent: AssistantIntent) -> dict[str, Any]:
        if intent.name == "status":
            return project_status(_require_project(intent))
        if intent.name == "check":
            return project_check(_require_project(intent))
        if intent.name == "init_project":
            path = init_project(
                _require(intent.project_id, "project_id"),
                _require(intent.display_name, "name"),
                _require(intent.genre, "genre"),
                intent.target_platform or "中文网文连载平台",
            )
            rebuild_index(_require(intent.project_id, "project_id"))
            return {"project_id": intent.project_id, "path": rel(path)}
        if intent.name == "plan_next":
            plan, chapter_intent, chain = plan_next(project_dir(_require_project(intent)), _require_chapter(intent))
            rebuild_index(intent.project)
            return {"chapter": plan.chapter, "title": plan.title, "objective": plan.objective, "scene_count": len(chain.scenes), "intent": to_dict(chapter_intent)}
        if intent.name == "generate":
            cfg = load_project(_require_project(intent))
            artifact = generate(project_dir(intent.project), _require_chapter(intent), threshold(cfg))
            rebuild_index(intent.project)
            return to_dict(artifact)
        if intent.name == "review_chapter":
            cfg = load_project(_require_project(intent))
            result = review_chapter(project_dir(intent.project), _require_chapter(intent), threshold(cfg))
            rebuild_index(intent.project)
            return to_dict(result)
        if intent.name == "index":
            path = rebuild_index(intent.project)
            return {"project": intent.project or "all", "path": rel(path)}
        if intent.name == "explain_review":
            return explain_review(_require_project(intent), _require_chapter(intent))
        if intent.name == "show_revision_queue":
            return revision_queue(intent.project)
        if intent.name == "serve_help":
            return {"command": "python3 -m novelops.cli serve", "url": "http://127.0.0.1:8787"}
        if intent.name == "radar_collect":
            return self._execute_radar_collect(intent)
        if intent.name == "radar_analyze":
            return self._execute_radar_analyze(intent)
        if intent.name == "radar_report":
            return self._execute_radar_report(intent)
        if intent.name == "radar_analyze_text":
            return self._execute_radar_analyze_text(intent)
        if intent.name == "pipeline_run":
            return self._execute_pipeline_run(intent)
        if intent.name == "pipeline_status":
            return self._execute_pipeline_status(intent)
        if intent.name == "pipeline_approve":
            return self._execute_pipeline_approve(intent)
        if intent.name == "pipeline_reject":
            return self._execute_pipeline_reject(intent)
        if intent.name == "prepare_project":
            return self._execute_prepare_project(intent)
        if intent.name == "readiness_check":
            return self._execute_readiness_check(intent)
        raise ConfigError(f"Unsupported intent: {intent.name}")

    def _execute_radar_collect(self, intent: AssistantIntent) -> dict[str, Any]:
        from .radar.cli import cmd_collect_web
        import argparse
        args = argparse.Namespace(
            source="fanqie",
            all=False,
            rank="hot",
            category=None,
            limit=50,
            dry_run=False,
            playwright=False,
            ignore_robots=False,
        )
        result_code = cmd_collect_web(args)
        return {"status": "success" if result_code == 0 else "failed", "source": "fanqie"}

    def _execute_radar_analyze(self, intent: AssistantIntent) -> dict[str, Any]:
        from .radar.cli import cmd_analyze
        import argparse
        args = argparse.Namespace(limit=100, llm=False)
        result_code = cmd_analyze(args)
        return {"status": "success" if result_code == 0 else "failed"}

    def _execute_radar_report(self, intent: AssistantIntent) -> dict[str, Any]:
        from .radar.cli import cmd_report
        import argparse
        args = argparse.Namespace(limit=100)
        result_code = cmd_report(args)
        return {"status": "success" if result_code == 0 else "failed"}

    def _execute_radar_analyze_text(self, intent: AssistantIntent) -> dict[str, Any]:
        from .radar.cli import cmd_analyze_text
        import argparse
        args = argparse.Namespace(
            text=intent.display_name or "",
            json=False,
            title=None,
            category=None,
            tags=None,
            platform=None,
        )
        result_code = cmd_analyze_text(args)
        return {"status": "success" if result_code == 0 else "failed"}

    def _execute_pipeline_run(self, intent: AssistantIntent) -> dict[str, Any]:
        from .pipeline.cli import cmd_pipeline_run
        import argparse
        project_id = intent.project or self.default_project
        args = argparse.Namespace(
            project=project_id,
            topic=None,
            mode="interactive",
            from_stage=None,
            chapters=intent.chapter or 10,
        )
        result_code = cmd_pipeline_run(args)
        return {"status": "success" if result_code == 0 else "failed", "project": project_id}

    def _execute_pipeline_status(self, intent: AssistantIntent) -> dict[str, Any]:
        from .pipeline.cli import cmd_pipeline_status
        import argparse
        project_id = intent.project or self.default_project
        args = argparse.Namespace(project=project_id)
        result_code = cmd_pipeline_status(args)
        return {"status": "success" if result_code == 0 else "failed", "project": project_id}

    def _execute_pipeline_approve(self, intent: AssistantIntent) -> dict[str, Any]:
        from .pipeline.cli import cmd_pipeline_approve
        import argparse
        project_id = intent.project or self.default_project
        args = argparse.Namespace(project=project_id)
        result_code = cmd_pipeline_approve(args)
        return {"status": "success" if result_code == 0 else "failed", "project": project_id}

    def _execute_pipeline_reject(self, intent: AssistantIntent) -> dict[str, Any]:
        from .pipeline.cli import cmd_pipeline_reject
        import argparse
        project_id = intent.project or self.default_project
        args = argparse.Namespace(project=project_id, feedback="用户拒绝")
        result_code = cmd_pipeline_reject(args)
        return {"status": "success" if result_code == 0 else "failed", "project": project_id}

    def _execute_prepare_project(self, intent: AssistantIntent) -> dict[str, Any]:
        from .prepare import prepare_project_interactive
        project_id = intent.project or self.default_project
        base = project_dir(project_id)
        result = prepare_project_interactive(base)
        return {"status": "success", "project": project_id, **result}

    def _execute_readiness_check(self, intent: AssistantIntent) -> dict[str, Any]:
        from .readiness import check_readiness
        project_id = intent.project or self.default_project
        base = project_dir(project_id)
        result = check_readiness(base)
        return {"project": project_id, **result}


def project_status(project: str) -> dict[str, Any]:
    cfg = load_project(project)
    base = project_dir(project)
    chapters = list_chapters(base)
    latest_generation = sorted((base / "generation").glob("chapter_*"))
    latest_reviews = sorted((base / "reviews").glob("chapter_*_review.json"))
    queue = list((base / "reviews" / "revision_queue").glob("chapter_*.md"))
    return {
        "project": project,
        "name": cfg.get("name", project),
        "genre": cfg.get("genre", "unknown"),
        "corpus_chapters": len(chapters),
        "current_volume": cfg.get("current_volume", {}).get("number"),
        "next_chapter": cfg.get("current_volume", {}).get("next_chapter"),
        "review_threshold": threshold(cfg),
        "latest_generation": latest_generation[-1].name if latest_generation else None,
        "latest_review": latest_reviews[-1].name if latest_reviews else None,
        "open_revision_queue": len(queue),
    }


def project_check(project: str) -> dict[str, Any]:
    base = project_dir(project)
    cfg = load_project(project)
    required_dirs = STANDARD_DIRS + ["corpus/volume_01", "publish/ready"]
    items: list[dict[str, Any]] = []
    ok = True
    for item in required_dirs:
        exists = (base / item).is_dir()
        ok = ok and exists
        items.append({"path": rel(base / item), "ok": exists, "type": "dir"})
    for file_name in ["project.json", "bible/00_story_bible.md"]:
        path = base / file_name
        exists = path.is_file() and path.stat().st_size > 0
        ok = ok and exists
        items.append({"path": rel(path), "ok": exists, "type": "file"})
    chapters = list_chapters(base)
    if cfg.get("planning", {}).get("require_corpus") and not chapters:
        ok = False
    return {"project": project, "ok": ok, "items": items, "corpus_chapters": len(chapters)}


def explain_review(project: str, chapter: int) -> dict[str, Any]:
    path = project_dir(project) / "reviews" / f"chapter_{chapter:03d}_review.json"
    if not path.is_file():
        raise ConfigError(f"Missing review report: {rel(path)}")
    data = json.loads(path.read_text(encoding="utf-8"))
    issues = [str(item) for item in data.get("issues") or []]
    recommendations = [str(item) for item in data.get("recommendations") or []]
    tasks = [str(item) for item in data.get("revision_tasks") or []]
    summary = f"第{chapter:03d}章审稿得分 {data.get('score')}/{data.get('threshold')}，{'已通过' if data.get('passed') else '未通过'}。"
    if issues:
        summary += " 主要问题：" + "；".join(issues[:3]) + "。"
    if tasks or recommendations:
        summary += " 建议优先处理：" + "；".join((tasks or recommendations)[:3]) + "。"
    return {
        "project": project,
        "chapter": chapter,
        "passed": bool(data.get("passed")),
        "score": data.get("score"),
        "threshold": data.get("threshold"),
        "issues": issues,
        "recommendations": recommendations,
        "revision_tasks": tasks,
        "summary": summary,
        "path": rel(path),
    }


def revision_queue(project: str | None = None) -> dict[str, Any]:
    rebuild_index(project)
    query = "SELECT * FROM revision_queue WHERE status = 'open'"
    params: tuple[Any, ...] = ()
    if project:
        query += " AND project_id = ?"
        params = (project,)
    query += " ORDER BY project_id, chapter"
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    items = [dict(row) for row in rows]
    return {"project": project or "all", "count": len(items), "items": items[:20]}


def _assistant_prompt(text: str, default_project: str) -> str:
    projects = [{"id": p.name} for p in all_project_dirs()]
    return (
        "把用户中文请求解析成 NovelOps 意图 JSON。字段：intent, project, chapter, project_id, name, genre, "
        "target_platform, missing_fields, confidence。\n"
        f"固定意图：{', '.join(sorted(INTENTS))}。\n"
        f"默认项目：{default_project}。已知项目：{json.dumps(projects, ensure_ascii=False)}。\n"
        f"用户请求：{text}"
    )


def _normalize_intent(data: dict[str, Any], text: str, default_project: str) -> AssistantIntent:
    name = str(data.get("intent") or data.get("name") or "unknown")
    if name not in INTENTS:
        name = "unknown"
    chapter = _coerce_int(data.get("chapter"))
    confidence = _coerce_float(data.get("confidence"), 0.7)
    return AssistantIntent(
        name=name,
        project=str(data.get("project") or "") or _extract_project(text) or default_project,
        chapter=chapter or _extract_chapter(text),
        project_id=str(data.get("project_id") or "") or None,
        display_name=str(data.get("name") or "") or None,
        genre=str(data.get("genre") or "") or None,
        target_platform=str(data.get("target_platform") or "") or None,
        missing_fields=[str(item) for item in data.get("missing_fields") or []],
        confidence=confidence,
    )


def _extract_project(text: str) -> str | None:
    for path in all_project_dirs():
        if path.name in text:
            return path.name
    match = re.search(r"项目\s*([A-Za-z0-9_\-]+)", text)
    return match.group(1) if match else None


def _extract_chapter(text: str) -> int | None:
    match = re.search(r"第\s*(\d{1,4})\s*章|chapter[_\s-]*(\d{1,4})", text, flags=re.I)
    if not match:
        return None
    return int(match.group(1) or match.group(2))


def _forbidden_reason(text: str) -> str | None:
    for reason, pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, flags=re.I):
            return reason
    return None


def _missing_fields(intent: AssistantIntent) -> list[str]:
    if intent.name in {"status", "check", "plan_next", "generate", "review_chapter", "explain_review"} and not intent.project:
        return ["project"]
    if intent.name in {"plan_next", "generate", "review_chapter", "explain_review"} and intent.chapter is None:
        return ["chapter"]
    if intent.name == "init_project":
        return [field for field, value in [("project_id", intent.project_id), ("name", intent.display_name), ("genre", intent.genre)] if not value]
    return []


def _preview_actions(intent: AssistantIntent) -> list[dict[str, Any]]:
    command = _equivalent_command(intent)
    return [{"intent": intent.name, "project": intent.project, "chapter": intent.chapter, "command": command}]


def _equivalent_command(intent: AssistantIntent) -> str:
    prefix = "python3 -m novelops.cli"
    if intent.project and intent.name not in {"init_project", "index"}:
        prefix += f" --project {intent.project}"
    if intent.name == "status":
        return f"{prefix} status"
    if intent.name == "check":
        return f"{prefix} check"
    if intent.name == "init_project":
        return f"python3 -m novelops.cli init-project {intent.project_id or '<project_id>'} --name {intent.display_name or '<name>'} --genre {intent.genre or '<genre>'}"
    if intent.name == "plan_next":
        return f"{prefix} plan-next {intent.chapter or '<chapter>'}"
    if intent.name == "generate":
        return f"{prefix} generate {intent.chapter or '<chapter>'}"
    if intent.name == "review_chapter":
        return f"{prefix} review-chapter {intent.chapter or '<chapter>'}"
    if intent.name == "index":
        return "python3 -m novelops.cli index" + (f" --project {intent.project}" if intent.project else "")
    if intent.name == "explain_review":
        return f"{prefix} ask \"解释第{intent.chapter or '<chapter>'}章审稿为什么没过\""
    if intent.name == "show_revision_queue":
        return f"{prefix} ask \"显示修订队列\""
    if intent.name == "serve_help":
        return "python3 -m novelops.cli serve"
    if intent.name == "radar_collect":
        return "python3 -m novelops.radar collect-web"
    if intent.name == "radar_analyze":
        return "python3 -m novelops.radar analyze"
    if intent.name == "radar_report":
        return "python3 -m novelops.radar report"
    if intent.name == "radar_analyze_text":
        return "python3 -m novelops.radar analyze-text <text>"
    if intent.name == "pipeline_run":
        return "python3 -m novelops.cli pipeline run"
    if intent.name == "pipeline_status":
        return "python3 -m novelops.cli pipeline status"
    if intent.name == "pipeline_approve":
        return "python3 -m novelops.cli pipeline approve"
    if intent.name == "pipeline_reject":
        return "python3 -m novelops.cli pipeline reject"
    if intent.name == "prepare_project":
        return "python3 -m novelops.cli prepare"
    if intent.name == "readiness_check":
        return "python3 -m novelops.cli readiness"
    return f"{prefix} ask <request>"


def _success_message(intent: AssistantIntent, result: dict[str, Any]) -> str:
    if intent.name == "status":
        return f"{result['name']} 当前语料 {result['corpus_chapters']} 章，下一章 {result['next_chapter']}，open 修订 {result['open_revision_queue']} 个。"
    if intent.name == "check":
        return f"{intent.project} 检查{'通过' if result['ok'] else '发现缺项'}，语料 {result['corpus_chapters']} 章。"
    if intent.name == "init_project":
        return f"已创建项目 {result['project_id']}：{result['path']}"
    if intent.name == "plan_next":
        return f"已写入第{result['chapter']:03d}章计划：{result['title']}"
    if intent.name == "generate":
        return f"已生成第{result['chapter']:03d}章 {result['stage']}：{rel(Path(result['path']))}"
    if intent.name == "review_chapter":
        return f"第{result['chapter']:03d}章审稿 {result['score']}/{result['threshold']}，{'通过' if result['passed'] else '需要修订'}。"
    if intent.name == "index":
        return f"已重建索引：{result['path']}"
    if intent.name == "explain_review":
        return str(result["summary"])
    if intent.name == "show_revision_queue":
        return f"当前 open 修订队列 {result['count']} 项。"
    if intent.name == "serve_help":
        return f"启动看板：{result['command']}，默认地址 {result['url']}"
    if intent.name == "radar_collect":
        return f"市场数据采集{'成功' if result.get('status') == 'success' else '失败'}。来源：{result.get('source', '未知')}"
    if intent.name == "radar_analyze":
        return f"市场数据分析{'完成' if result.get('status') == 'success' else '失败'}。"
    if intent.name == "radar_report":
        return f"市场报告{'已生成' if result.get('status') == 'success' else '生成失败'}。"
    if intent.name == "pipeline_run":
        return f"流水线{'已启动' if result.get('status') == 'success' else '启动失败'}。项目：{result.get('project', '未知')}"
    if intent.name == "pipeline_status":
        return f"流水线状态查询{'完成' if result.get('status') == 'success' else '失败'}。"
    if intent.name == "pipeline_approve":
        return f"流水线节点{'已批准' if result.get('status') == 'success' else '批准失败'}。"
    if intent.name == "prepare_project":
        return f"项目准备{'完成' if result.get('status') == 'success' else '失败'}。项目：{result.get('project', '未知')}"
    if intent.name == "readiness_check":
        return f"准备度检查完成。项目：{result.get('project', '未知')}"
    return "已完成。"


def _confirmation_message(intent: AssistantIntent) -> str:
    command = _equivalent_command(intent)
    if intent.name == "generate":
        return f"生成章节会写入 generation 和 reviews 产物，需要确认。等价命令：{command}。CLI 可加 --yes 执行。"
    if intent.name == "init_project":
        return f"创建项目会新增项目目录，需要确认。等价命令：{command}。CLI 可加 --yes 执行。"
    if intent.name == "radar_collect":
        return f"将采集市场数据，需要确认。等价命令：{command}。"
    if intent.name == "radar_analyze":
        return f"将分析市场数据，需要确认。等价命令：{command}。"
    if intent.name == "pipeline_run":
        return f"将运行生成流水线，需要确认。等价命令：{command}。"
    if intent.name == "prepare_project":
        return f"将准备新书项目（生成核心设定、角色、大纲等），需要确认。等价命令：{command}。"
    return f"该操作需要确认。等价命令：{command}"


def _missing_message(intent: AssistantIntent) -> str:
    fields = "、".join(intent.missing_fields)
    if intent.name == "init_project":
        return f"需要项目 ID、项目名和题材才能创建项目；当前缺少：{fields}。"
    return f"需要补充：{fields}。"


def _unknown(message: str | None = None, project: str | None = None) -> AssistantResponse:
    return AssistantResponse(
        message=message
        or "我能处理：查看状态、检查项目、规划/生成下一章、审稿、解释审稿、重建索引、查看修订队列、市场情报分析、流水线管理、项目准备。例如：查看 life_balance 状态；解释第51章审稿为什么没过；给当前项目生成下一章；采集市场热点；运行生成流水线；准备新书项目。",
        intent=AssistantIntent(name="unknown", project=project),
    )


def _latest_available_chapter(project: str) -> int | None:
    chapters = list_chapters(project_dir(project))
    return chapters[-1].number if chapters else _latest_review_chapter(project)


def _latest_review_chapter(project: str) -> int | None:
    reports = sorted((project_dir(project) / "reviews").glob("chapter_*_review.json"))
    if not reports:
        return None
    match = re.search(r"chapter_(\d+)_review", reports[-1].name)
    return int(match.group(1)) if match else None


def _replace_intent(intent: AssistantIntent, **changes: Any) -> AssistantIntent:
    data = asdict(intent)
    data.update(changes)
    return AssistantIntent(**data)


def _require(value: str | None, name: str) -> str:
    if not value:
        raise ConfigError(f"Missing {name}")
    return value


def _require_project(intent: AssistantIntent) -> str:
    return _require(intent.project, "project")


def _require_chapter(intent: AssistantIntent) -> int:
    if intent.chapter is None:
        raise ConfigError("Missing chapter")
    return intent.chapter


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
