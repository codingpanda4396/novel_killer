from __future__ import annotations

from pathlib import Path

from .config import write_json
from .corpus import get_chapter
from .reviewer import review_text
from .schemas import PublishCheckReport, to_dict


def publish_check(project: str, project_path: Path, start: int, end: int, threshold: float) -> PublishCheckReport:
    results = []
    revision_queue: list[int] = []
    for chapter in range(start, end + 1):
        item = get_chapter(project_path, chapter)
        result = review_text(chapter, item.text, threshold)
        results.append(result)
        if not result.passed:
            revision_queue.append(chapter)

    checked = len(results)
    passed = sum(1 for result in results if result.passed)
    average = round(sum(result.score for result in results) / checked, 2) if checked else 0.0
    report = PublishCheckReport(
        project=project,
        start=start,
        end=end,
        checked=checked,
        passed=passed,
        failed=checked - passed,
        average_score=average,
        revision_queue=revision_queue,
    )
    report_path = project_path / "reviews" / f"publish_check_{start:03d}_{end:03d}.json"
    write_json(report_path, to_dict(report) | {"chapters": [to_dict(result) for result in results]})
    queue_path = project_path / "reviews" / "revision_queue.md"
    queue_path.write_text(
        "# Revision Queue\n\n"
        + ("\n".join(f"- Chapter {chapter:03d}" for chapter in revision_queue) or "No chapters below threshold.")
        + "\n",
        encoding="utf-8",
    )
    return report

