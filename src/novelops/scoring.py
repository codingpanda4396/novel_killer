from __future__ import annotations

import re
from typing import Any


def text_metrics(text: str, rubric: dict[str, Any] | None = None) -> dict[str, float]:
    rubric = rubric or {}
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    tokens = re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+", text)
    dialogue = len(re.findall(r'["“”]', text))
    hook_terms_cfg = [str(term) for term in rubric.get("hook_terms", []) if str(term)]
    hook_terms = sum(text.count(term) for term in hook_terms_cfg)
    forbidden_terms = sum(text.count(str(term)) for term in rubric.get("forbidden_terms", []) if str(term))
    return {
        "word_count": float(len(tokens)),
        "paragraphs": float(len(paragraphs)),
        "dialogue_marks": float(dialogue),
        "hook_terms": float(hook_terms),
        "forbidden_terms": float(forbidden_terms),
    }


def score_text(text: str, rubric: dict[str, Any] | None = None) -> tuple[float, list[str], list[str]]:
    rubric = rubric or {}
    metrics = text_metrics(text, rubric)
    score = 60.0
    issues: list[str] = []
    recommendations: list[str] = []

    words = metrics["word_count"]
    if words >= 2200:
        score += 14
    elif words >= 1600:
        score += 9
    else:
        issues.append("篇幅偏短，低于连载章节的稳定承载量。")
        recommendations.append("补足场景推进、反应链和章尾钩子。")

    if metrics["paragraphs"] >= 25:
        score += 8
    else:
        issues.append("段落密度不足，可能缺少可读的节奏切分。")

    if metrics["dialogue_marks"] >= 10:
        score += 8
    else:
        recommendations.append("增加角色对话或即时冲突，避免纯叙述推进。")

    if rubric.get("hook_terms"):
        if metrics["hook_terms"] >= 3:
            score += 10
        else:
            issues.append("项目 rubric 中的核心卖点词出现不足，章节与题材绑定偏弱。")
    else:
        recommendations.append("项目 rubric 未配置 hook_terms，本次只使用通用基础评分。")

    if metrics["forbidden_terms"] > 0:
        score -= 15
        issues.append("正文包含项目 rubric 标记的禁写项。")

    if re.search(r"(未完待续|敬请期待|作者)", text):
        score -= 12
        issues.append("出现平台正文不应包含的作者提示或尾注。")

    score = max(0.0, min(100.0, round(score, 2)))
    if not issues:
        recommendations.append("保留现有节奏，复核连续性细节后可进入候选池。")
    return score, issues, recommendations
