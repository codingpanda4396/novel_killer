from __future__ import annotations

import re


def text_metrics(text: str) -> dict[str, float]:
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    tokens = re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+", text)
    dialogue = len(re.findall(r'["“”]', text))
    hook_terms = sum(text.count(term) for term in ["余额", "寿命", "命运", "代价", "规则", "天平"])
    return {
        "word_count": float(len(tokens)),
        "paragraphs": float(len(paragraphs)),
        "dialogue_marks": float(dialogue),
        "hook_terms": float(hook_terms),
    }


def score_text(text: str) -> tuple[float, list[str], list[str]]:
    metrics = text_metrics(text)
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

    if metrics["hook_terms"] >= 8:
        score += 10
    else:
        issues.append("核心卖点词汇出现不足，章节与项目题材绑定偏弱。")

    if re.search(r"(未完待续|敬请期待|作者)", text):
        score -= 12
        issues.append("出现平台正文不应包含的作者提示或尾注。")

    score = max(0.0, min(100.0, round(score, 2)))
    if not issues:
        recommendations.append("保留现有节奏，复核连续性细节后可进入候选池。")
    return score, issues, recommendations

