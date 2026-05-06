from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import ConfigError, load_project_path, write_json
from .corpus import get_chapter
from .llm import LLMClient
from .platforms import get_platform, get_platform_review_focus, get_platform_risk_focus
from .schemas import ReviewResult, to_dict
from .scoring import score_text


SCORE_KEYS = ["hook", "conflict", "consistency", "continuity", "ai_trace", "retention", "risk"]
PLATFORM_SCORE_KEYS = [
    "opening_hook_score", "conflict_score", "payoff_score",
    "retention_score", "novelty_score", "long_term_arc_score", "platform_risk_score",
]
ALLOWED_ACTIONS = {"accept", "revise", "reject"}


def _build_platform_context(platform_id: str | None) -> str:
    if platform_id is None:
        return ""
    try:
        platform = get_platform(platform_id)
        review_focus = get_platform_review_focus(platform_id)
        risk_focus = get_platform_risk_focus(platform_id)
        context = f"\n\n目标平台：{platform['name']}\n"
        context += f"商业模式：{platform['business_model']}\n"
        if review_focus:
            context += f"审稿重点：{', '.join(review_focus)}\n"
        if risk_focus:
            context += f"风险重点：{', '.join(risk_focus)}\n"
        return context
    except KeyError:
        return ""


def _read_chapter_text(project_path: Path, chapter: int) -> str:
    try:
        return get_chapter(project_path, chapter).text
    except FileNotFoundError:
        generation = project_path / "generation" / f"chapter_{chapter:03d}"
        for name in ["11_revision_v2.md", "09_revision_v1.md", "07_final_candidate.md", "06_humanized_rewrite.md"]:
            path = generation / name
            if path.is_file():
                return path.read_text(encoding="utf-8")
        raise


def _rule_review(chapter: int, text: str, threshold: float, project_path: Path | None = None, attempt: int = 0) -> ReviewResult:
    rubric = {}
    if project_path is not None and (project_path / "project.json").is_file():
        rubric = load_project_path(project_path).get("rubric", {})
    score, issues, recommendations = score_text(text, rubric)
    scores = {key: score for key in SCORE_KEYS}
    action = "accept" if score >= threshold else "revise"
    return ReviewResult(
        chapter=chapter,
        score=score,
        threshold=threshold,
        passed=score >= threshold,
        issues=issues,
        recommendations=recommendations,
        scores=scores,
        revision_tasks=recommendations if score < threshold else [],
        suggested_action=action,
        model="rules",
        attempt=attempt,
        llm_used=False,
    )


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_score(value: Any, default: float = 0.0) -> float:
    return max(0.0, min(100.0, _coerce_float(value, default)))


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _llm_review(
    chapter: int,
    text: str,
    threshold: float,
    llm_client: LLMClient,
    project_path: Path | None = None,
    attempt: int = 0,
    platform_id: str | None = None,
) -> ReviewResult:
    # 读取项目级审稿要求
    project_context = ""
    if project_path is not None:
        try:
            # 读取项目配置
            project_config = load_project_path(project_path)
            rubric = project_config.get("rubric", {})
            hook_terms = rubric.get("hook_terms", [])
            forbidden_terms = rubric.get("forbidden_terms", [])
            
            # 读取审稿检查清单
            checklist_path = project_path / "bible" / "11_review_checklist.md"
            checklist = ""
            if checklist_path.exists():
                checklist = checklist_path.read_text(encoding="utf-8", errors="ignore")[:1000]
            
            # 读取禁写规则
            forbidden_path = project_path / "bible" / "04_forbidden_rules.md"
            forbidden_rules = ""
            if forbidden_path.exists():
                forbidden_rules = forbidden_path.read_text(encoding="utf-8", errors="ignore")[:800]
            
            # 构建项目上下文
            if hook_terms or forbidden_terms or checklist or forbidden_rules:
                project_context = "\n\n项目审稿要求：\n"
                if hook_terms:
                    project_context += f"- 钩子词（应出现）：{', '.join(hook_terms)}\n"
                if forbidden_terms:
                    project_context += f"- 禁写内容：{', '.join(forbidden_terms)}\n"
                if checklist:
                    project_context += f"\n审稿检查清单：\n{checklist}\n"
                if forbidden_rules:
                    project_context += f"\n禁写规则：\n{forbidden_rules}\n"
        except Exception:
            pass
    
    platform_context = _build_platform_context(platform_id)
    
    system = (
        "你是商业长篇小说的严苛审稿人。只返回 JSON 对象，不要 Markdown。"
        "评分范围 0-100，suggested_action 只能是 accept、revise、reject。"
    )
    
    platform_fields = ""
    if platform_id:
        platform_fields = """
如果指定了平台，还需返回平台相关评分字段：
opening_hook_score（开篇钩子）, conflict_score（冲突）, payoff_score（爽点释放）,
retention_score（追读）, novelty_score（新意）, long_term_arc_score（长期主线）, platform_risk_score（平台风险）。
以及 revision_focus（针对平台的修订重点，数组）。"""
    
    prompt = f"""请审稿第 {chapter:03d} 章，阈值 {threshold}。

必须返回字段：
score, passed, issues, recommendations, scores, revision_tasks, suggested_action。
scores 必须包含 hook, conflict, consistency, continuity, ai_trace, retention, risk。
{platform_fields}
{project_context}{platform_context}

章节正文：
{text}
"""
    schema = {
        "type": "json_object",
    }
    data = llm_client.complete_json(prompt, system=system, stage="reviewer", schema=schema)
    score = _clamp_score(data.get("score"))
    scores_raw = data.get("scores") if isinstance(data.get("scores"), dict) else {}
    scores = {key: _clamp_score(scores_raw.get(key), score) for key in SCORE_KEYS}
    action = str(data.get("suggested_action") or ("accept" if score >= threshold else "revise"))
    if action not in ALLOWED_ACTIONS:
        action = "revise" if score < threshold else "accept"
    passed = bool(data.get("passed", score >= threshold)) and score >= threshold and action == "accept"
    
    return ReviewResult(
        chapter=chapter,
        score=score,
        threshold=threshold,
        passed=passed,
        issues=_coerce_list(data.get("issues")),
        recommendations=_coerce_list(data.get("recommendations")),
        scores=scores,
        revision_tasks=_coerce_list(data.get("revision_tasks")),
        suggested_action=action,
        model=llm_client.settings_for("reviewer").model,
        attempt=attempt,
        llm_used=True,
        platform_id=platform_id,
        opening_hook_score=_clamp_score(data.get("opening_hook_score")) if data.get("opening_hook_score") is not None else None,
        conflict_score=_clamp_score(data.get("conflict_score")) if data.get("conflict_score") is not None else None,
        payoff_score=_clamp_score(data.get("payoff_score")) if data.get("payoff_score") is not None else None,
        retention_score=_clamp_score(data.get("retention_score")) if data.get("retention_score") is not None else None,
        novelty_score=_clamp_score(data.get("novelty_score")) if data.get("novelty_score") is not None else None,
        long_term_arc_score=_clamp_score(data.get("long_term_arc_score")) if data.get("long_term_arc_score") is not None else None,
        platform_risk_score=_clamp_score(data.get("platform_risk_score")) if data.get("platform_risk_score") is not None else None,
        revision_focus=_coerce_list(data.get("revision_focus")),
    )


def review_text(
    chapter: int,
    text: str,
    threshold: float,
    llm_client: LLMClient | None = None,
    project_path: Path | None = None,
    attempt: int = 0,
    platform_id: str | None = None,
) -> ReviewResult:
    result = _llm_review(
        chapter, text, threshold, llm_client or LLMClient(),
        project_path=project_path, attempt=attempt, platform_id=platform_id,
    )

    if project_path is not None:
        out = project_path / "reviews" / f"chapter_{chapter:03d}_review.json"
        write_json(out, to_dict(result))
    return result


def review_chapter(
    project_path: Path,
    chapter: int,
    threshold: float,
    llm_client: LLMClient | None = None,
) -> ReviewResult:
    text = _read_chapter_text(project_path, chapter)
    result = review_text(chapter, text, threshold, llm_client=llm_client, project_path=project_path)
    if not result.passed:
        queue = project_path / "reviews" / "revision_queue" / f"chapter_{chapter:03d}.md"
        queue.parent.mkdir(parents=True, exist_ok=True)
        queue.write_text(
            f"# Chapter {chapter:03d} Revision Required\n\n"
            f"Score: {result.score}/{result.threshold}\n\n"
            + "\n".join(f"- {issue}" for issue in result.issues + result.revision_tasks)
            + "\n",
            encoding="utf-8",
        )
    return result
