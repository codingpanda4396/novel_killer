from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import ConfigError, load_project, threshold
from .corpus import list_chapters
from .generator import generate
from .paths import project_dir, rel
from .planner import plan_next
from .publisher import publish_check
from .reviewer import review_chapter
from .scout import scout


REQUIRED_PROJECT_DIRS = [
    "bible",
    "outlines",
    "corpus/volume_01",
    "state",
    "generation",
    "reviews",
    "intelligence/raw/manual_notes",
    "intelligence/processed",
    "intelligence/reports",
    "publish/ready",
]


def cmd_check(args: argparse.Namespace) -> int:
    failed = 0
    project_path = project_dir(args.project)
    for item in REQUIRED_PROJECT_DIRS:
        path = project_path / item
        print(("OK  " if path.is_dir() else "MISS ") + rel(path))
        failed |= 0 if path.is_dir() else 1
    for file_name in ["project.json", "bible/00_story_bible.md", "state/timeline.md"]:
        path = project_path / file_name
        print(("OK  " if path.is_file() and path.stat().st_size else "MISS ") + rel(path))
        failed |= 0 if path.is_file() and path.stat().st_size else 1
    chapters = list_chapters(project_path)
    print(f"Corpus chapters: {len(chapters)}")
    if len(chapters) != 50:
        failed = 1
    return failed


def cmd_status(args: argparse.Namespace) -> int:
    cfg = load_project(args.project)
    chapters = list_chapters(project_dir(args.project))
    print(f"Project: {cfg['name']} ({args.project})")
    print(f"Genre: {cfg.get('genre', 'unknown')}")
    print(f"Volume 01 corpus: {len(chapters)} chapters")
    print(f"Current volume: {cfg.get('current_volume', {}).get('number')}")
    print(f"Review threshold: {threshold(cfg)}")
    return 0


def cmd_review_chapter(args: argparse.Namespace) -> int:
    cfg = load_project(args.project)
    result = review_chapter(project_dir(args.project), args.chapter, threshold(cfg), no_llm=args.no_llm)
    print(f"Chapter {args.chapter:03d}: {result.score}/{result.threshold} {'PASS' if result.passed else 'REVISION'}")
    return 0 if result.passed else 2


def cmd_review_range(args: argparse.Namespace) -> int:
    cfg = load_project(args.project)
    failed = 0
    for chapter in range(args.start, args.end + 1):
        result = review_chapter(project_dir(args.project), chapter, threshold(cfg))
        print(f"Chapter {chapter:03d}: {result.score}/{result.threshold} {'PASS' if result.passed else 'REVISION'}")
        failed += 0 if result.passed else 1
    return 0 if failed == 0 else 2


def cmd_publish_check(args: argparse.Namespace) -> int:
    cfg = load_project(args.project)
    report = publish_check(args.project, project_dir(args.project), args.start, args.end, threshold(cfg, "publish"))
    print(f"Checked {report.checked}; passed {report.passed}; failed {report.failed}; average {report.average_score}")
    return 0 if report.failed == 0 else 2


def cmd_plan_next(args: argparse.Namespace) -> int:
    plan, _, _ = plan_next(project_dir(args.project), args.chapter)
    print(f"Wrote plan for chapter {plan.chapter:03d}: {plan.title}")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    cfg = load_project(args.project)
    artifact = generate(project_dir(args.project), args.chapter, threshold(cfg), no_llm=args.no_llm)
    print(f"Wrote {artifact.stage}: {rel(Path(artifact.path))}")
    return 0


def cmd_scout(args: argparse.Namespace) -> int:
    candidates = scout(project_dir(args.project))
    print(f"Topic candidates: {len(candidates)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="novelops", description="NovelOps v2 CLI")
    parser.add_argument("--project", default="life_balance")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check").set_defaults(func=cmd_check)
    sub.add_parser("status").set_defaults(func=cmd_status)
    p = sub.add_parser("review-chapter")
    p.add_argument("chapter", type=int)
    p.add_argument("--no-llm", action="store_true", default=False)
    p.set_defaults(func=cmd_review_chapter)
    p = sub.add_parser("review-range")
    p.add_argument("start", type=int)
    p.add_argument("end", type=int)
    p.set_defaults(func=cmd_review_range)
    p = sub.add_parser("publish-check")
    p.add_argument("start", type=int)
    p.add_argument("end", type=int)
    p.set_defaults(func=cmd_publish_check)
    p = sub.add_parser("plan-next")
    p.add_argument("chapter", type=int)
    p.set_defaults(func=cmd_plan_next)
    p = sub.add_parser("generate")
    p.add_argument("chapter", type=int)
    p.add_argument("--no-llm", action="store_true", default=False)
    p.set_defaults(func=cmd_generate)
    sub.add_parser("scout").set_defaults(func=cmd_scout)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (ConfigError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
