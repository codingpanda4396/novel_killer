from __future__ import annotations

from unittest.mock import MagicMock, patch

from novelops.reviewer import _build_platform_context, _llm_review, review_text
from novelops.schemas import ReviewResult


def test_build_platform_context_qidian():
    context = _build_platform_context("qidian")
    assert "起点中文网" in context
    assert "paid_serial" in context
    assert "设定新意" in context
    assert "同类竞争强" in context


def test_build_platform_context_fanqie():
    context = _build_platform_context("fanqie")
    assert "番茄小说" in context
    assert "free_reading" in context
    assert "开篇钩子" in context


def test_build_platform_context_none():
    context = _build_platform_context(None)
    assert context == ""


def test_build_platform_context_unknown():
    context = _build_platform_context("nonexistent")
    assert context == ""


def test_review_text_backward_compatibility():
    mock_client = MagicMock()
    mock_client.settings_for.return_value = MagicMock(model="test-model")
    mock_client.complete_json.return_value = {
        "score": 80,
        "passed": True,
        "issues": [],
        "recommendations": [],
        "scores": {
            "hook": 80,
            "conflict": 75,
            "consistency": 85,
            "continuity": 80,
            "ai_trace": 10,
            "retention": 78,
            "risk": 20,
        },
        "revision_tasks": [],
        "suggested_action": "accept",
    }

    result = review_text(
        chapter=1,
        text="测试文本",
        threshold=70,
        llm_client=mock_client,
    )

    assert isinstance(result, ReviewResult)
    assert result.score == 80
    assert result.passed is True
    assert result.platform_id is None
    assert result.opening_hook_score is None


def test_review_text_with_platform():
    mock_client = MagicMock()
    mock_client.settings_for.return_value = MagicMock(model="test-model")
    mock_client.complete_json.return_value = {
        "score": 75,
        "passed": True,
        "issues": [],
        "recommendations": [],
        "scores": {
            "hook": 75,
            "conflict": 70,
            "consistency": 80,
            "continuity": 75,
            "ai_trace": 15,
            "retention": 72,
            "risk": 25,
        },
        "revision_tasks": [],
        "suggested_action": "accept",
        "opening_hook_score": 80,
        "conflict_score": 70,
        "payoff_score": 75,
        "retention_score": 72,
        "novelty_score": 68,
        "long_term_arc_score": 70,
        "platform_risk_score": 30,
        "revision_focus": ["强化开篇钩子"],
    }

    result = review_text(
        chapter=1,
        text="测试文本",
        threshold=70,
        llm_client=mock_client,
        platform_id="qidian",
    )

    assert isinstance(result, ReviewResult)
    assert result.platform_id == "qidian"
    assert result.opening_hook_score == 80
    assert result.conflict_score == 70
    assert result.payoff_score == 75
    assert result.retention_score == 72
    assert result.novelty_score == 68
    assert result.long_term_arc_score == 70
    assert result.platform_risk_score == 30
    assert result.revision_focus == ["强化开篇钩子"]


def test_review_result_fields_default():
    result = ReviewResult(
        chapter=1,
        score=80,
        threshold=70,
        passed=True,
        issues=[],
        recommendations=[],
    )
    assert result.platform_id is None
    assert result.opening_hook_score is None
    assert result.platform_risk_score is None
    assert result.revision_focus == []
