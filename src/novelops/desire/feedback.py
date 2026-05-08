"""Feedback loop: update demand_analysis.md with real experiment data."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..db.models import FeedbackLog
from ..db.session import session_scope
from ..project_paths import ProjectPaths
from sqlmodel import select


def update_demand_from_feedback(project_path: Path, experiment_id: str) -> bool:
    """Append a "实战回写" section to demand_analysis.md based on real feedback data.

    Args:
        project_path: Project root path
        experiment_id: Experiment ID to pull feedback from

    Returns:
        True if a section was appended, False otherwise
    """
    paths = ProjectPaths(project_path)
    demand_path = paths.market / "demand_analysis.md"

    if not demand_path.is_file():
        return False

    # Load feedback data
    feedback_data = _load_feedback(project_path.name, experiment_id)
    if not feedback_data:
        return False

    # Compute summary metrics
    summary = _summarize_feedback(feedback_data)
    if not summary:
        return False

    # Build the "实战回写" section
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    section = _build_feedback_section(today, experiment_id, summary)

    # Append to demand_analysis.md
    try:
        existing = demand_path.read_text(encoding="utf-8")
        demand_path.write_text(existing.rstrip() + "\n\n" + section + "\n", encoding="utf-8")
        return True
    except Exception:
        return False


def _load_feedback(project_id: str, experiment_id: str) -> list[dict[str, Any]]:
    """Load feedback logs from DB."""
    try:
        with session_scope() as session:
            statement = select(FeedbackLog).where(
                FeedbackLog.project_id == project_id,
                FeedbackLog.experiment_id == experiment_id,
            )
            results = session.exec(statement).all()
            if not results:
                return []
            return [
                {
                    "record_date": r.record_date,
                    "platform": r.platform,
                    "impressions": r.impressions,
                    "views": r.views,
                    "reads": r.reads,
                    "read_rate": r.read_rate,
                    "collections": r.collections,
                    "favorites": r.favorites,
                    "comments": r.comments,
                    "follows": r.follows,
                    "chapter_follows": r.chapter_follows,
                    "income": r.income,
                    "notes": r.notes,
                }
                for r in results
            ]
    except Exception:
        return []


def _summarize_feedback(data: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Compute summary metrics from feedback data."""
    if not data:
        return None

    total_impressions = sum(d.get("impressions") or 0 for d in data)
    total_views = sum(d.get("views") or 0 for d in data)
    total_reads = sum(d.get("reads") or 0 for d in data)
    total_collections = sum(d.get("collections") or 0 for d in data)
    total_favorites = sum(d.get("favorites") or 0 for d in data)
    total_comments = sum(d.get("comments") or 0 for d in data)
    total_follows = sum(d.get("follows") or 0 for d in data)
    total_income = sum(d.get("income") or 0.0 for d in data)

    # Compute rates
    click_rate = (total_views / total_impressions * 100) if total_impressions > 0 else 0.0
    read_rate = (total_reads / total_views * 100) if total_views > 0 else 0.0
    collection_rate = (total_collections / total_reads * 100) if total_reads > 0 else 0.0

    # Find notes/comments keywords
    all_notes = [d.get("notes", "") for d in data if d.get("notes")]
    notes_summary = "; ".join(all_notes[:3]) if all_notes else ""

    return {
        "data_points": len(data),
        "total_impressions": total_impressions,
        "total_views": total_views,
        "total_reads": total_reads,
        "click_rate": round(click_rate, 2),
        "read_rate": round(read_rate, 2),
        "collection_rate": round(collection_rate, 2),
        "total_collections": total_collections,
        "total_favorites": total_favorites,
        "total_comments": total_comments,
        "total_follows": total_follows,
        "total_income": round(total_income, 2),
        "notes_summary": notes_summary,
    }


def _build_feedback_section(date: str, experiment_id: str, summary: dict[str, Any]) -> str:
    """Build the markdown section for feedback."""
    lines = [
        f"## 实战回写 {date} — experiment_{experiment_id}\n",
        f"### 数据概览",
        f"- 数据点数: {summary['data_points']}",
        f"- 总曝光: {summary['total_impressions']}",
        f"- 总阅读: {summary['total_reads']}",
        f"- 点击率: {summary['click_rate']}%",
        f"- 完读率: {summary['read_rate']}%",
        f"- 收藏率: {summary['collection_rate']}%",
        f"- 总收藏: {summary['total_collections']}",
        f"- 总关注: {summary['total_follows']}",
        f"- 总收入: {summary['total_income']}",
    ]

    if summary["notes_summary"]:
        lines.append(f"\n### 平台备注")
        lines.append(f"- {summary['notes_summary']}")

    lines.append(f"\n### demand_analysis 修正")
    lines.append(f"- [待人工分析] 对比预测与实测数据，修正欲望集群")

    lines.append(f"\n### reader_personas 修正")
    lines.append(f"- [待人工分析] 对比预测与实测数据，修正读者画像")

    return "\n".join(lines)
