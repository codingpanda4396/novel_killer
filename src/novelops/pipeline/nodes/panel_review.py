"""Panel review pipeline node: multi-persona chapter review."""

from __future__ import annotations

import json
from typing import Any

from ...config import write_json
from ...project_paths import ProjectPaths
from ...readers.panel import review_panel
from ..state import PipelineState


def panel_review_node(state: PipelineState) -> dict[str, Any]:
    """Panel review node: run 5 persona reviews on the final draft.

    Runs after rewrite_node if panel_review_enabled is True.
    Writes chapter_NNN_panel.json (separate from chapter_NNN_review.json).
    Does NOT block the pipeline on failure.
    """
    final_draft = state.get("final_draft")
    current_chapter = state.get("current_chapter", 1)
    project_path = state["project_path"]

    if not final_draft:
        return {}

    try:
        paths = ProjectPaths(project_path)
        report = review_panel(
            chapter=current_chapter,
            chapter_text=final_draft,
            project_path=project_path,
        )

        # Write panel report JSON
        panel_path = paths.panel_path(current_chapter)
        panel_path.parent.mkdir(parents=True, exist_ok=True)
        from dataclasses import asdict
        write_json(panel_path, asdict(report))

        return {}

    except Exception as e:
        # Panel failure should not block the pipeline
        return {}
