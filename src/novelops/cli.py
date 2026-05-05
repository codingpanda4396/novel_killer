from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .config import ConfigError, default_project_id, load_app_config, load_project, threshold
from .assistant import ask
from .corpus import list_chapters
from .db.engine import database_url
from .db.migrate import init_db
from .framework_importer import import_framework_project, preview_framework_import
from .generator import generate
from .indexer import rebuild_index
from .indexer import connect
from .paths import project_dir, rel
from .planner import plan_next
from .prepare import prepare_project_interactive
from .project import STANDARD_DIRS, init_project
from .publisher import publish_check
from .readiness import check_framework_readiness, check_project_readiness
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
    project_path = project_dir(args.project)
    chapters = list_chapters(project_path)
    latest_generation = sorted((project_path / "generation").glob("chapter_*"))
    latest_reviews = sorted((project_path / "reviews").glob("chapter_*_review.json"))
    queue = list((project_path / "reviews" / "revision_queue").glob("chapter_*.md"))
    print(f"Project: {cfg['name']} ({args.project})")
    print(f"Genre: {cfg.get('genre', 'unknown')}")
    print(f"Corpus: {len(chapters)} chapters")
    print(f"Current volume: {cfg.get('current_volume', {}).get('number')}")
    print(f"Next chapter: {cfg.get('current_volume', {}).get('next_chapter')}")
    print(f"Review threshold: {threshold(cfg)}")
    print(f"Latest generation: {latest_generation[-1].name if latest_generation else 'none'}")
    print(f"Latest review: {latest_reviews[-1].name if latest_reviews else 'none'}")
    print(f"Open revision queue: {len(queue)}")
    
    # 增加准备度检查
    if args.readiness:
        print("\n=== 开书准备度检查 ===")
        report = check_project_readiness(project_path, cfg)
        for item in report.items:
            status_symbol = "✓" if item.status == "ok" else ("✗" if item.critical else "⚠")
            print(f"{status_symbol} {item.name}: {item.message}")
        print(f"\n准备状态: {'可以开始生成' if report.ready else '需要补充关键资料'}")
        print(f"关键缺失: {report.critical_missing}, 建议补充: {report.warnings}")
    
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


def cmd_db_status(args: argparse.Namespace) -> int:
    path = init_db()
    print(f"Database URL: {database_url()}")
    if path is None:
        print("Table counts: unavailable for non-SQLite URL")
        return 0
    with connect(path) as conn:
        tables = [
            "story_projects",
            "projects",
            "chapters",
            "chapter_plans",
            "reviews",
            "revision_queue",
            "hot_items",
            "market_reports",
            "feedback_logs",
        ]
        for table in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {count}")
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


def cmd_memory_index(args: argparse.Namespace) -> int:
    """重建指定项目记忆库"""
    try:
        from .memory import index_project
    except ImportError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    project_path = project_dir(args.project)
    count = index_project(project_path)
    print(f"Indexed {count} documents for project: {args.project}")
    return 0


def cmd_memory_recall(args: argparse.Namespace) -> int:
    """预览指定章节召回结果"""
    try:
        from .memory import recall_for_chapter, format_memory_context
        from .planner import plan_next
    except ImportError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    project_path = project_dir(args.project)
    plan, intent, chain = plan_next(project_path, args.chapter)
    context = recall_for_chapter(project_path, args.chapter, plan, intent, chain)

    print(f"=== Chapter {args.chapter} Memory Recall ===\n")
    for section, content in context.items():
        print(f"## {section}")
        if content:
            print(content[:500] + "..." if len(content) > 500 else content)
        else:
            print("(empty)")
        print()

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


def cmd_readiness(args: argparse.Namespace) -> int:
    """检查项目开书准备度"""
    cfg = load_project(args.project)
    project_path = project_dir(args.project)
    report = check_framework_readiness(project_path, cfg) if getattr(args, "framework", False) else check_project_readiness(project_path, cfg)
    
    print(f"=== {cfg['name']} 开书准备度检查 ===\n")
    
    # 分类显示
    critical_items = [item for item in report.items if item.critical]
    optional_items = [item for item in report.items if not item.critical]
    
    print("【关键项】")
    for item in critical_items:
        status_symbol = "✓" if item.status == "ok" else "✗"
        print(f"  {status_symbol} {item.name}")
        if item.status != "ok":
            print(f"    → {item.message}")
    
    print("\n【建议项】")
    for item in optional_items:
        status_symbol = "✓" if item.status == "ok" else "⚠"
        print(f"  {status_symbol} {item.name}")
        if item.status != "ok":
            print(f"    → {item.message}")
    
    print(f"\n{'='*50}")
    if report.ready:
        print("✓ 项目已准备就绪，可以开始生成章节")
    else:
        print(f"✗ 还有 {report.critical_missing} 个关键项需要补充")
        print("  请先完善 bible 和 outlines 中的关键资料")
    
    if report.warnings > 0:
        print(f"⚠ 有 {report.warnings} 个建议项可以进一步完善")
    
    return 0 if report.ready else 1


def cmd_import_framework(args: argparse.Namespace) -> int:
    """从 ChatGPT Markdown 框架导入新书项目。"""
    markdown = _read_framework_input(args)
    if args.dry_run or not args.yes:
        preview = preview_framework_import(
            args.project_id,
            markdown,
            name=args.name,
            target_platform=args.target_platform,
        )
        print(json.dumps(preview.summary(), ensure_ascii=False, indent=2))
        if not args.dry_run and not args.yes:
            print("\n未创建项目。确认创建请加 --yes。")
        return 0

    preview = import_framework_project(
        args.project_id,
        markdown,
        name=args.name,
        target_platform=args.target_platform,
    )
    print(f"Created project: {rel(project_dir(args.project_id))}")
    print(json.dumps(preview.summary(), ensure_ascii=False, indent=2))
    return 0


def _read_framework_input(args: argparse.Namespace) -> str:
    if args.framework_file:
        return Path(args.framework_file).read_text(encoding="utf-8")
    return sys.stdin.read()


def cmd_prepare_project(args: argparse.Namespace) -> int:
    """准备新书项目（生成核心设定和前 30 章大纲）"""
    project_path = project_dir(args.project)
    if not project_path.exists():
        print(f"错误：项目不存在 {project_path}")
        print("请先运行 novelops init-project 创建项目")
        return 1
    
    print(f"开始准备项目：{args.project}")
    print("这将使用 LLM 生成核心设定、角色、大纲等内容...")
    print("预计需要 2-5 分钟\n")
    
    if not args.yes:
        confirm = input("是否继续？(y/N): ")
        if confirm.lower() != "y":
            print("已取消")
            return 0
    
    result = prepare_project_interactive(project_path)
    return 0


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
    sub.add_parser("db-status", help="显示数据库 URL、核心表数量和迁移状态").set_defaults(func=cmd_db_status)
    p = sub.add_parser("serve")
    p.add_argument("--host", default=str(app_cfg.get("web", {}).get("host", "127.0.0.1")))
    p.add_argument("--port", type=int, default=int(app_cfg.get("web", {}).get("port", 8787)))
    p.set_defaults(func=cmd_serve)
    sub.add_parser("check").set_defaults(func=cmd_check)
    p = sub.add_parser("status")
    p.add_argument("--readiness", action="store_true", help="显示开书准备度检查")
    p.set_defaults(func=cmd_status)
    p = sub.add_parser("readiness")
    p.add_argument("--framework", action="store_true", help="执行框架导入专项准备度检查")
    p.set_defaults(func=cmd_readiness)
    p = sub.add_parser("import-framework", help="从 ChatGPT Markdown 框架导入新书项目")
    p.add_argument("project_id")
    p.add_argument("--framework-file")
    p.add_argument("--name")
    p.add_argument("--target-platform")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", action="store_true", help="确认创建项目；不加时只预览")
    p.set_defaults(func=cmd_import_framework)
    p = sub.add_parser("prepare-project", help="准备新书项目（生成核心设定和大纲）")
    p.add_argument("--yes", action="store_true", help="跳过确认")
    p.set_defaults(func=cmd_prepare_project)
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
    p = sub.add_parser("memory-index", help="重建项目记忆库")
    p.set_defaults(func=cmd_memory_index)
    p = sub.add_parser("memory-recall", help="预览章节召回结果")
    p.add_argument("chapter", type=int)
    p.set_defaults(func=cmd_memory_recall)
    p = sub.add_parser("ask")
    p.add_argument("message")
    p.add_argument("--yes", action="store_true", default=False)
    p.set_defaults(func=cmd_ask)

    # 注册 pipeline 子命令
    from .pipeline.cli import register_pipeline_commands
    register_pipeline_commands(sub)

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
