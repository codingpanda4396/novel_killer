from __future__ import annotations

from pathlib import Path

from .config import write_json
from .schemas import TopicCandidate, to_dict


def scout(project_path: Path) -> list[TopicCandidate]:
    raw_dir = project_path / "intelligence" / "raw" / "manual_notes"
    candidates: list[TopicCandidate] = []
    for path in sorted(raw_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        lines = [line.strip("# -\t ") for line in text.splitlines() if line.strip()]
        title = lines[0] if lines else path.stem
        score = min(100.0, 40.0 + len(text) / 50.0)
        candidates.append(TopicCandidate(title=title, source=str(path), score=round(score, 2), reasons=["manual_note"]))

    processed = project_path / "intelligence" / "processed" / "topic_candidates.jsonl"
    processed.parent.mkdir(parents=True, exist_ok=True)
    processed.write_text("\n".join(__import__("json").dumps(to_dict(item), ensure_ascii=False) for item in candidates) + ("\n" if candidates else ""), encoding="utf-8")

    report = project_path / "intelligence" / "reports" / "topic_scoreboard.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# Topic Scoreboard\n\n"
        + ("\n".join(f"- {item.score}: {item.title}" for item in candidates) or "No manual notes found.")
        + "\n",
        encoding="utf-8",
    )
    return candidates

