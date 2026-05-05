from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from . import generator, reviewer
from .config import ConfigError, load_project, load_project_path, threshold
from .corpus import list_chapters
from .indexer import rebuild_index
from .llm import LLMClient
from .paths import project_dir, rel
from .readiness import check_project_readiness
from .schemas import to_dict


class WorkflowState(Enum):
    INIT = "init"
    FRAMEWORK_IMPORTED = "framework_imported"
    READY_FOR_CHAPTER = "ready_for_chapter"
    DRAFT_GENERATED = "draft_generated"
    REVIEWED = "reviewed"
    REVISION_REQUIRED = "revision_required"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class NextAction:
    action: str
    label: str
    reason: str
    project: str | None = None
    chapter: int | None = None
    runnable: bool = True


@dataclass(frozen=True)
class WorkflowReport:
    project: str | None
    project_path: str
    state: WorkflowState
    next_chapter: int | None
    corpus_count: int
    open_revisions: int
    latest_generation: str | None
    latest_review: dict[str, Any] | None
    readiness: dict[str, Any] | None
    blocking_issues: list[str] = field(default_factory=list)
    available_actions: list[NextAction] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data


@dataclass(frozen=True)
class ActionResult:
    action: str
    success: bool
    message: str
    project: str | None = None
    chapter: int | None = None
    data: dict[str, Any] | None = None
    next_state: WorkflowState | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["next_state"] = self.next_state.value if self.next_state else None
        return data


class ProjectOrchestrator:
    """Thin workflow coordinator for project state, generation, and review."""

    def __init__(self, default_project: str | None = None, llm_client: LLMClient | None = None) -> None:
        self.default_project = default_project
        self.llm_client = llm_client

    def get_project_state(
        self,
        project_name: str | None = None,
        project_path: str | Path | None = None,
    ) -> WorkflowReport:
        resolved_path, config = self._resolve_project(project_name, project_path)
        project = str(config.get("id") or project_name) if config else project_name
        readiness_data = None
        blocking_issues: list[str] = []
        try:
            chapters = list_chapters(resolved_path) if resolved_path.is_dir() else []
        except Exception:
            chapters = []
        latest_generation = _latest_generation(resolved_path)
        latest_review = _latest_review(resolved_path)
        open_revisions = _open_revision_count(resolved_path)

        if config:
            try:
                readiness_report = check_project_readiness(resolved_path, config)
                readiness_data = _readiness_to_dict(readiness_report)
                blocking_issues = [
                    item["message"]
                    for item in readiness_data["items"]
                    if item["critical"] and item["status"] != "ok"
                ]
            except Exception as exc:
                blocking_issues = [str(exc)]

        state = _infer_state(resolved_path, config, readiness_data, latest_generation, latest_review, open_revisions)
        next_chapter = _next_chapter(config, chapters)
        actions = _available_actions(state, project, next_chapter)
        return WorkflowReport(
            project=project,
            project_path=rel(resolved_path),
            state=state,
            next_chapter=next_chapter,
            corpus_count=len(chapters),
            open_revisions=open_revisions,
            latest_generation=latest_generation,
            latest_review=latest_review,
            readiness=readiness_data,
            blocking_issues=blocking_issues,
            available_actions=actions,
        )

    def recommend_next_action(
        self,
        project_name: str | None = None,
        project_path: str | Path | None = None,
    ) -> NextAction:
        report = self.get_project_state(project_name, project_path)
        if report.available_actions:
            return report.available_actions[0]
        return NextAction(
            action="inspect",
            label="检查项目",
            reason="当前状态无法自动推荐生成或审稿动作。",
            project=report.project,
            chapter=report.next_chapter,
            runnable=False,
        )

    def generate_next_chapter(
        self,
        project_name: str | None = None,
        project_path: str | Path | None = None,
        chapter: int | None = None,
        threshold_value: float | None = None,
        llm_client: LLMClient | None = None,
    ) -> ActionResult:
        try:
            resolved_path, config = self._resolve_project(project_name, project_path)
            chapter_number = chapter or _next_chapter(config, list_chapters(resolved_path))
            if chapter_number is None:
                raise ConfigError("Cannot infer next chapter.")
            review_threshold = threshold_value if threshold_value is not None else threshold(config or {})
            artifact = generator.generate(
                resolved_path,
                chapter_number,
                review_threshold,
                llm_client=llm_client or self.llm_client,
            )
            _rebuild_if_named(config)
            state = self.get_project_state(project_name, resolved_path).state
            return ActionResult(
                action="generate_next_chapter",
                success=True,
                message=f"Generated chapter {chapter_number}.",
                project=str(config.get("id")) if config else project_name,
                chapter=chapter_number,
                data=to_dict(artifact),
                next_state=state,
            )
        except Exception as exc:
            return ActionResult(
                action="generate_next_chapter",
                success=False,
                message=f"Generation failed: {exc}",
                project=project_name,
                chapter=chapter,
                errors=[str(exc)],
            )

    def review_chapter(
        self,
        project_name: str | None = None,
        project_path: str | Path | None = None,
        chapter: int | None = None,
        threshold_value: float | None = None,
        llm_client: LLMClient | None = None,
    ) -> ActionResult:
        try:
            resolved_path, config = self._resolve_project(project_name, project_path)
            chapter_number = chapter or _latest_chapter_number(resolved_path) or _next_chapter(config, list_chapters(resolved_path))
            if chapter_number is None:
                raise ConfigError("Cannot infer chapter to review.")
            review_threshold = threshold_value if threshold_value is not None else threshold(config or {})
            result = reviewer.review_chapter(
                resolved_path,
                chapter_number,
                review_threshold,
                llm_client=llm_client or self.llm_client,
            )
            _rebuild_if_named(config)
            state = self.get_project_state(project_name, resolved_path).state
            return ActionResult(
                action="review_chapter",
                success=True,
                message=f"Reviewed chapter {chapter_number}.",
                project=str(config.get("id")) if config else project_name,
                chapter=chapter_number,
                data=to_dict(result),
                next_state=state,
            )
        except Exception as exc:
            return ActionResult(
                action="review_chapter",
                success=False,
                message=f"Review failed: {exc}",
                project=project_name,
                chapter=chapter,
                errors=[str(exc)],
            )

    def run_chapter_pipeline(
        self,
        project_name: str | None = None,
        project_path: str | Path | None = None,
        chapter: int | None = None,
        threshold_value: float | None = None,
        llm_client: LLMClient | None = None,
    ) -> ActionResult:
        generated = self.generate_next_chapter(
            project_name=project_name,
            project_path=project_path,
            chapter=chapter,
            threshold_value=threshold_value,
            llm_client=llm_client,
        )
        if not generated.success:
            return generated
        reviewed = self.review_chapter(
            project_name=project_name,
            project_path=project_path,
            chapter=generated.chapter,
            threshold_value=threshold_value,
            llm_client=llm_client,
        )
        return ActionResult(
            action="run_chapter_pipeline",
            success=reviewed.success,
            message="Chapter pipeline completed." if reviewed.success else reviewed.message,
            project=reviewed.project or generated.project,
            chapter=generated.chapter,
            data={"generate": generated.to_dict(), "review": reviewed.to_dict()},
            next_state=reviewed.next_state,
            errors=reviewed.errors,
        )

    def _resolve_project(
        self,
        project_name: str | None = None,
        project_path: str | Path | None = None,
    ) -> tuple[Path, dict[str, Any] | None]:
        if project_path is not None:
            resolved = Path(project_path)
            if not resolved.is_absolute():
                resolved = resolved.resolve()
            config = load_project_path(resolved) if (resolved / "project.json").is_file() else None
            return resolved, config
        name = project_name or self.default_project
        if not name:
            raise ConfigError("project_name or project_path is required.")
        resolved = project_dir(name)
        return resolved, load_project(name) if (resolved / "project.json").is_file() else None


def _infer_state(
    project_path: Path,
    config: dict[str, Any] | None,
    readiness_data: dict[str, Any] | None,
    latest_generation: str | None,
    latest_review: dict[str, Any] | None,
    open_revisions: int,
) -> WorkflowState:
    if not config or not (project_path / "project.json").is_file():
        return WorkflowState.INIT
    if open_revisions > 0:
        return WorkflowState.REVISION_REQUIRED
    if latest_review is not None:
        return WorkflowState.REVIEWED if latest_review.get("passed") else WorkflowState.REVISION_REQUIRED
    if latest_generation is not None:
        return WorkflowState.DRAFT_GENERATED
    if readiness_data and readiness_data.get("ready"):
        return WorkflowState.READY_FOR_CHAPTER
    return WorkflowState.FRAMEWORK_IMPORTED


def _available_actions(state: WorkflowState, project: str | None, chapter: int | None) -> list[NextAction]:
    if state == WorkflowState.INIT:
        return [NextAction("check_readiness", "检查准备度", "项目尚未完成初始化或缺少 project.json。", project, chapter, False)]
    if state == WorkflowState.FRAMEWORK_IMPORTED:
        return [NextAction("check_readiness", "检查准备度", "项目资料尚未满足章节生成条件。", project, chapter, True)]
    if state == WorkflowState.READY_FOR_CHAPTER:
        return [NextAction("generate_next_chapter", "生成下一章", "项目已满足生成准备度。", project, chapter, True)]
    if state == WorkflowState.DRAFT_GENERATED:
        return [NextAction("review_chapter", "审稿章节", "已有生成稿，下一步应进入审稿。", project, chapter, True)]
    if state == WorkflowState.REVIEWED:
        return [NextAction("generate_next_chapter", "继续生成", "最新审稿已通过，可以推进下一章。", project, chapter, True)]
    if state == WorkflowState.REVISION_REQUIRED:
        return [NextAction("review_chapter", "复核修订", "存在未通过审稿或修订队列。", project, chapter, True)]
    return []


def _next_chapter(config: dict[str, Any] | None, chapters: list[Any]) -> int | None:
    if config:
        value = config.get("current_volume", {}).get("next_chapter")
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                pass
    if chapters:
        return max(chapter.number for chapter in chapters) + 1
    return 1 if config else None


def _latest_chapter_number(project_path: Path) -> int | None:
    numbers = []
    for directory in (project_path / "generation").glob("chapter_*"):
        try:
            numbers.append(int(directory.name.rsplit("_", 1)[1]))
        except (IndexError, ValueError):
            pass
    return max(numbers) if numbers else None


def _latest_generation(project_path: Path) -> str | None:
    directories = sorted(path for path in (project_path / "generation").glob("chapter_*") if path.is_dir())
    return directories[-1].name if directories else None


def _latest_review(project_path: Path) -> dict[str, Any] | None:
    reports = sorted((project_path / "reviews").glob("chapter_*_review.json"))
    if not reports:
        generation_reports = sorted((project_path / "generation").glob("chapter_*/*review_gate.json"))
        reports = generation_reports
    if not reports:
        return None
    try:
        return json.loads(reports[-1].read_text(encoding="utf-8"))
    except Exception:
        return {"path": str(reports[-1]), "passed": False, "error": "invalid review json"}


def _open_revision_count(project_path: Path) -> int:
    return len(list((project_path / "reviews" / "revision_queue").glob("chapter_*.md")))


def _readiness_to_dict(report: Any) -> dict[str, Any]:
    return {
        "ready": bool(report.ready),
        "critical_missing": int(report.critical_missing),
        "warnings": int(report.warnings),
        "items": [asdict(item) for item in report.items],
    }


def _rebuild_if_named(config: dict[str, Any] | None) -> None:
    if config and config.get("id"):
        rebuild_index(str(config["id"]))

