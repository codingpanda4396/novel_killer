"""CLI command for desire synthesis."""

from __future__ import annotations

import argparse

from ..config import ConfigError
from ..llm import LLMClient
from ..paths import project_dir
from .synthesizer import DesireSynthesizer


def cmd_analyze_demand(args: argparse.Namespace) -> int:
    """Run desire synthesis for a project."""
    project_path = project_dir(args.project)

    if not project_path.is_dir():
        print(f"ERROR: Project not found: {args.project}")
        return 1

    window = args.window or "14d"
    window_days = int(window.replace("d", ""))
    force = args.force

    print(f"Analyzing demand for project: {args.project}")
    print(f"Window: {window_days} days, Force: {force}")

    try:
        synthesizer = DesireSynthesizer(project_path)
        result = synthesizer.run(window_days=window_days, force=force)
        print(f"\nSynthesis complete.")
        print(f"  Signals analyzed: {result.signal_count}")
        print(f"  Demand clusters: {len(result.demands)}")
        print(f"  Reader personas: {len(result.personas)}")
        return 0
    except ConfigError as e:
        print(f"ERROR: {e}")
        return 1


def register_desire_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register desire synthesis CLI commands."""
    p = subparsers.add_parser("analyze-demand", help="分析市场需求并生成需求分析文档")
    p.add_argument("--project", default=None, help="项目ID")
    p.add_argument("--window", default="14d", help="分析窗口，如 14d")
    p.add_argument("--force", action="store_true", help="强制重新分析（忽略幂等性）")
    p.set_defaults(func=cmd_analyze_demand)
