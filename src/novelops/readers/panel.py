"""ReaderPanel: parallel multi-persona chapter review."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..llm import LLMClient
from ..project_paths import ProjectPaths
from .loader import load_all_personas
from .persona import PersonaSpec


@dataclass
class PersonaReview:
    """Single persona's review of a chapter."""
    persona: str
    persona_version: str
    overall_score: float
    dimension_scores: dict[str, float]
    flagged_red_flags: list[str]
    quotes: list[str]
    verdict: str  # "love" | "okay" | "drop"
    revision_suggestions: list[str]


@dataclass
class PanelReport:
    """Aggregated panel review report."""
    chapter: int
    panel: list[PersonaReview]
    weighted_score: float
    score_spread: float
    dissent: bool
    consensus_red_flags: list[str]
    aggregated_revision_focus: list[str]
    generated_at: str


def review_panel(
    chapter: int,
    chapter_text: str,
    project_path: Path,
    llm_client: LLMClient | None = None,
    personas: list[PersonaSpec] | None = None,
) -> PanelReport:
    """Run parallel persona reviews on a chapter.

    Args:
        chapter: Chapter number
        chapter_text: Chapter text content
        project_path: Project root path
        llm_client: Optional LLM client
        personas: Optional list of persona specs (loads from prompts if None)

    Returns:
        PanelReport with aggregated results
    """
    paths = ProjectPaths(project_path)
    client = llm_client or LLMClient()
    specs = personas or load_all_personas()

    if not specs:
        return PanelReport(
            chapter=chapter,
            panel=[],
            weighted_score=0.0,
            score_spread=0.0,
            dissent=False,
            consensus_red_flags=[],
            aggregated_revision_focus=[],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    # Load extra context for specific personas
    character_state = ""
    world_rules = ""
    rubric: dict[str, Any] = {}

    try:
        char_path = paths.state_file("character_state.md")
        if char_path.is_file():
            character_state = char_path.read_text(encoding="utf-8")[:1500]
    except Exception:
        pass

    try:
        world_path = paths.bible_file("02_power_system.md")
        if world_path.is_file():
            world_rules = world_path.read_text(encoding="utf-8")[:1500]
    except Exception:
        pass

    try:
        cfg_path = project_path / "project.json"
        if cfg_path.is_file():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            rubric = cfg.get("rubric", {})
    except Exception:
        pass

    # Build review tasks
    def _run_persona(spec: PersonaSpec) -> PersonaReview:
        return _call_persona(spec, chapter, chapter_text, client, character_state, world_rules, rubric)

    # Parallel execution
    reviews: list[PersonaReview] = []
    with ThreadPoolExecutor(max_workers=min(5, len(specs))) as executor:
        futures = {executor.submit(_run_persona, spec): spec for spec in specs}
        for future in as_completed(futures):
            try:
                review = future.result()
                reviews.append(review)
            except Exception:
                spec = futures[future]
                reviews.append(PersonaReview(
                    persona=spec.name,
                    persona_version=spec.version,
                    overall_score=0.0,
                    dimension_scores={},
                    flagged_red_flags=[],
                    quotes=[],
                    verdict="drop",
                    revision_suggestions=[f"Persona {spec.name} failed to review"],
                ))

    # Sort by persona name for determinism
    reviews.sort(key=lambda r: r.persona)

    # Aggregate
    scores = [r.overall_score for r in reviews if r.overall_score > 0]
    weighted_score = sum(r.overall_score * (next((s.weight for s in specs if s.name == r.persona), 1.0)) for r in reviews) / max(sum(s.weight for s in specs), 1.0)
    score_spread = max(scores) - min(scores) if scores else 0.0
    dissent = score_spread > 25

    # Consensus red flags (flagged by >= 2 personas)
    red_flag_counts: dict[str, int] = {}
    for r in reviews:
        for flag in r.flagged_red_flags:
            red_flag_counts[flag] = red_flag_counts.get(flag, 0) + 1
    consensus_red_flags = [flag for flag, count in red_flag_counts.items() if count >= 2]

    # Aggregated revision focus
    revision_focus: list[str] = []
    for r in reviews:
        revision_focus.extend(r.revision_suggestions)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_focus: list[str] = []
    for item in revision_focus:
        if item not in seen:
            seen.add(item)
            unique_focus.append(item)

    return PanelReport(
        chapter=chapter,
        panel=reviews,
        weighted_score=round(weighted_score, 1),
        score_spread=round(score_spread, 1),
        dissent=dissent,
        consensus_red_flags=consensus_red_flags,
        aggregated_revision_focus=unique_focus[:10],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _call_persona(
    spec: PersonaSpec,
    chapter: int,
    chapter_text: str,
    client: LLMClient,
    character_state: str,
    world_rules: str,
    rubric: dict[str, Any],
) -> PersonaReview:
    """Call a single persona LLM for review."""
    # Build persona-specific context
    extra_context = ""
    if spec.name == "reader_emotional" and character_state:
        extra_context = f"\n\n角色状态：\n{character_state}"
    elif spec.name == "reader_setting_fan" and world_rules:
        extra_context = f"\n\n世界观规则：\n{world_rules}"
    elif spec.name == "platform_editor":
        hook_terms = rubric.get("hook_terms", [])
        forbidden = rubric.get("forbidden_terms", [])
        if hook_terms or forbidden:
            extra_context = "\n\n项目配置："
            if hook_terms:
                extra_context += f"\n钩子词：{', '.join(hook_terms)}"
            if forbidden:
                extra_context += f"\n禁写项：{', '.join(forbidden)}"

    user_prompt = (
        f"请以「{spec.display_name}」的视角审阅以下章节。\n"
        f"评分维度：{', '.join(spec.scoring_dimensions)}\n"
        f"红旗项：{', '.join(spec.red_flags)}\n\n"
        f"返回严格 JSON，字段：\n"
        f'{{"overall_score": 0-100, "dimension_scores": {{"维度": 分数}}, '
        f'"flagged_red_flags": [], "quotes": [], '
        f'"verdict": "love|okay|drop", "revision_suggestions": []}}\n\n'
        f"章节正文：\n{chapter_text[:8000]}"
        f"{extra_context}"
    )

    try:
        result = client.complete_json(user_prompt, system=spec.system_prompt, stage="assistant")
        return PersonaReview(
            persona=spec.name,
            persona_version=spec.version,
            overall_score=_clamp(result.get("overall_score", 0)),
            dimension_scores={k: _clamp(v) for k, v in (result.get("dimension_scores") or {}).items()},
            flagged_red_flags=result.get("flagged_red_flags", []),
            quotes=result.get("quotes", []),
            verdict=result.get("verdict", "okay"),
            revision_suggestions=result.get("revision_suggestions", []),
        )
    except Exception:
        return PersonaReview(
            persona=spec.name,
            persona_version=spec.version,
            overall_score=0.0,
            dimension_scores={},
            flagged_red_flags=[],
            quotes=[],
            verdict="drop",
            revision_suggestions=[f"LLM call failed for {spec.name}"],
        )


def _clamp(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return default
