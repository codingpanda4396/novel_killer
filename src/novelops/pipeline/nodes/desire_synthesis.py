"""Desire synthesis pipeline node."""

from __future__ import annotations

from typing import Any

from ...desire.synthesizer import DesireSynthesizer
from ...project_paths import ProjectPaths
from ..state import PipelineState


def desire_synthesis_node(state: PipelineState) -> dict[str, Any]:
    """Desire synthesis node: aggregate Radar signals into demand analysis.

    Runs before market_research_node if enabled.
    Fills state["market_data"] with synthesized demand summaries.
    """
    project_path = state["project_path"]

    try:
        synthesizer = DesireSynthesizer(project_path)
        result = synthesizer.run(window_days=14, force=False)

        if result.signal_count == 0:
            return {"market_data": None}

        # Fill market_data with synthesis summaries for downstream nodes
        market_data = {
            "source": "desire_synthesis",
            "signal_count": result.signal_count,
            "demand_clusters": [d.model_dump() for d in result.demands],
            "reader_personas": [p.model_dump() for p in result.personas],
        }
        return {"market_data": market_data}

    except Exception as e:
        # Don't block pipeline on synthesis failure
        return {"market_data": None, "errors": [f"Desire synthesis failed: {e}"]}
