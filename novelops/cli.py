from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import ConfigError, default_project_id, load_app_config, load_project, threshold
from .assistant import ask
from .corpus import list_chapters
from .generator import generate
from .indexer import rebuild_index
from .paths import project_dir, rel
from .planner import plan_next
from .project import STANDARD_DIRS, init_project
from .publisher import publish_check
from .reviewer import review_chapter
from .scout import scout


REQUIRED_PROJECT_DIRS = STANDARD_DIRS + ["corpus/volume_01", "publish/ready"]


def cmd_check(args: argparse.Namespace) -> int:
    failed = 0
    project_path = project_dir(args.project)
    cfg = load_project(args.project)
    for item in REQUIRED_PROJECT_DIRS:
        path = project_path / item
        print(("OK  " if path.is_dir() else "MISS ") + rel(path))
        failed |= 0 if path.is_dir() else 1
    for file_name in ["project.json", "bible/00_story_bible.md"]:
        path = project_path / file_name
        print(("OK  " if path.is_file() and path.stat().st_size else "MISS ") + rel(path))
        failed |= 0 if path.is_file() and path.stat().st_size else 1
    chapters = list_chapters(project_path)
    print(f"Corpus chapters: {len(chapters)}")
    if cfg.get("planning", {}).get("require_corpus") and len(chapters) == 0:
        failed = 1
    return failed


def cmd_status(args: argparse.Namespace) -> int:
    cfg = load_project(args.project)
    chapters = list_chapters(project_dir(args.project))
    latest_generation = sorted((project_dir(args.project) / "generation").glob("chapter_*"))
    latest_reviews = sorted((project_dir(args.project) / "reviews").glob("chapter_*_review.json"))
    queue = list((project_dir(args.project) / "reviews" / "revision_queue").glob("chapter_*.md"))
    print(f"Project: {cfg['name']} ({args.project})")
    print(f"Genre: {cfg.get('genre', 'unknown')}")
    print(f"Corpus: {len(chapters)} chapters")
    print(f"Current volume: {cfg.get('current_volume', {}).get('number')}")
    print(f"Next chapter: {cfg.get('current_volume', {}).get('next_chapter')}")
    print(f"Review threshold: {threshold(cfg)}")
    print(f"Latest generation: {latest_generation[-1].name if latest_generation else 'none'}")
    print(f"Latest review: {latest_reviews[-1].name if latest_reviews else 'none'}")
    print(f"Open revision queue: {len(queue)}")
    return 0


def cmd_init_project(args: argparse.Namespace) -> int:
    path = init_project(args.project_id, args.name, args.genre, args.target_platform)
    print(f"Created project: {rel(path)}")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    path = rebuild_index(args.index_project)
    target = args.index_project or "all projects"
    print(f"Indexed {target}: {rel(path)}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .web import ensure_index

    ensure_index()
    try:
        import uvicorn
    except ImportError as exc:
        raise ConfigError("Missing dependency: uvicorn. Install requirements.txt first.") from exc
    print(f"Serving NovelOps dashboard at http://{args.host}:{args.port}")
    uvicorn.run("novelops.web:create_app", factory=True, host=args.host, port=args.port)
    return 0


def cmd_review_chapter(args: argparse.Namespace) -> int:
    cfg = load_project(args.project)
    result = review_chapter(project_dir(args.project), args.chapter, threshold(cfg))
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
    artifact = generate(project_dir(args.project), args.chapter, threshold(cfg))
    print(f"Wrote {artifact.stage}: {rel(Path(artifact.path))}")
    return 0


def cmd_scout(args: argparse.Namespace) -> int:
    candidates = scout(project_dir(args.project))
    print(f"Topic candidates: {len(candidates)}")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    response = ask(args.message, default_project=args.project, execute=args.yes)
    print(response.message)
    if response.requires_confirmation:
        for action in response.actions:
            print(f"将执行：{action.get('command')}")
        return 0
    for error in response.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if response.errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="novelops", description="NovelOps v2 CLI")
    app_cfg = load_app_config()
    parser.add_argument("--project", default=default_project_id())
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init-project")
    p.add_argument("project_id")
    p.add_argument("--name", required=True)
    p.add_argument("--genre", required=True)
    p.add_argument("--target-platform", default="中文网文连载平台")
    p.set_defaults(func=cmd_init_project)
    p = sub.add_parser("index")
    p.add_argument("--project", dest="index_project")
    p.set_defaults(func=cmd_index)
    p = sub.add_parser("serve")
    p.add_argument("--host", default=str(app_cfg.get("web", {}).get("host", "127.0.0.1")))
    p.add_argument("--port", type=int, default=int(app_cfg.get("web", {}).get("port", 8787)))
    p.set_defaults(func=cmd_serve)
    sub.add_parser("check").set_defaults(func=cmd_check)
    sub.add_parser("status").set_defaults(func=cmd_status)
    p = sub.add_parser("review-chapter")
    p.add_argument("chapter", type=int)
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
    p.set_defaults(func=cmd_generate)
    sub.add_parser("scout").set_defaults(func=cmd_scout)
    p = sub.add_parser("ask")
    p.add_argument("message")
    p.add_argument("--yes", action="store_true", default=False)
    p.set_defaults(func=cmd_ask)
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
