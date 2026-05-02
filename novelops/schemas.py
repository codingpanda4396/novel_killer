from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TopicCandidate:
    title: str
    source: str
    score: float
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ChapterPlan:
    chapter: int
    title: str
    volume: int
    objective: str
    hooks: list[str]
    required_context: list[str]


@dataclass(frozen=True)
class ChapterIntent:
    chapter: int
    reader_promise: str
    emotional_turn: str
    commercial_hook: str
    forbidden_moves: list[str]


@dataclass(frozen=True)
class SceneChain:
    chapter: int
    scenes: list[dict[str, Any]]


@dataclass(frozen=True)
class DraftArtifact:
    chapter: int
    stage: str
    path: str
    word_count: int
    llm_used: bool


@dataclass(frozen=True)
class ReviewResult:
    chapter: int
    score: float
    threshold: float
    passed: bool
    issues: list[str]
    recommendations: list[str]
    scores: dict[str, float] = field(default_factory=dict)
    revision_tasks: list[str] = field(default_factory=list)
    suggested_action: str = "accept"
    model: str = "rules"
    attempt: int = 0
    llm_used: bool = False
    fallback_reason: str | None = None


@dataclass(frozen=True)
class PublishCheckReport:
    project: str
    start: int
    end: int
    checked: int
    passed: int
    failed: int
    average_score: float
    revision_queue: list[int]


def to_dict(value: Any) -> dict[str, Any]:
    return asdict(value)
