from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..config import ConfigError, default_project_id, load_app_config
from ..paths import project_dir
from .config import load_pipeline_config, save_pipeline_config
from .graph import compile_pipeline
from .state import create_initial_state


def cmd_pipeline_run(args: argparse.Namespace) -> int:
    """运行流水线"""
    from ..project import init_project

    # 确定项目 ID
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    # 确定模式
    mode = "auto" if args.mode == "auto" else "interactive"

    # 加载配置
    config = load_pipeline_config(project_path)

    # 创建初始状态
    state = create_initial_state(
        project_id=project_id,
        project_path=project_path,
        mode=mode,
        topic_id=args.topic,
        max_retry_attempts=config.get("max_retry_attempts", 2),
    )

    # 设置总章节数
    if args.chapters:
        state["total_chapters"] = args.chapters

    print(f"Starting pipeline for project: {project_id}")
    print(f"Mode: {mode}")
    if args.topic:
        print(f"Topic ID: {args.topic}")
    if args.from_stage:
        print(f"Starting from stage: {args.from_stage}")

    # 编译并运行流水线
    try:
        pipeline = compile_pipeline()

        # 运行流水线
        result = pipeline.invoke(state)

        # 检查结果
        if result.get("errors"):
            print("\nPipeline completed with errors:")
            for error in result["errors"]:
                print(f"  - {error}")
            return 1

        if result.get("needs_approval"):
            print("\nPipeline waiting for approval.")
            print("Run 'novelops pipeline approve' to continue.")
            return 0

        # 检查是否完成
        completed = result.get("completed_nodes", [])
        if completed:
            print(f"\nPipeline completed successfully!")
            print(f"Completed chapters: {len(completed)}")
            for node in completed:
                print(f"  - {node}")
        else:
            print("\nPipeline completed but no chapters were generated.")

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_pipeline_status(args: argparse.Namespace) -> int:
    """查看流水线状态"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    # 加载配置
    config = load_pipeline_config(project_path)

    print(f"Project: {project_id}")
    print(f"Path: {project_path}")
    print(f"Mode: {config.get('mode', 'interactive')}")
    print(f"Approval points: {', '.join(config.get('approval_points', []))}")
    print(f"Max retry attempts: {config.get('max_retry_attempts', 2)}")

    # 检查已生成的章节
    generation_path = project_path / "generation"
    if generation_path.exists():
        chapters = sorted(generation_path.glob("chapter_*"))
        print(f"\nGenerated chapters: {len(chapters)}")
        for chapter_dir in chapters[-5:]:  # 只显示最近 5 个
            print(f"  - {chapter_dir.name}")
    else:
        print("\nNo chapters generated yet.")

    return 0


def cmd_pipeline_approve(args: argparse.Namespace) -> int:
    """批准当前等待的节点"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    # 这里应该实现实际的批准逻辑
    # 简化实现：创建一个状态文件表示已批准
    approval_file = project_path / ".pipeline_approval"
    approval_file.write_text(json.dumps({"approved": True}), encoding="utf-8")

    print(f"Approved pipeline for project: {project_id}")
    print("Run 'novelops pipeline run' to continue.")
    return 0


def cmd_pipeline_reject(args: argparse.Namespace) -> int:
    """拒绝并提供反馈"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)
    feedback = args.feedback or "No feedback provided"

    # 保存反馈
    feedback_file = project_path / ".pipeline_feedback"
    feedback_file.write_text(json.dumps({
        "rejected": True,
        "feedback": feedback,
    }), encoding="utf-8")

    print(f"Rejected pipeline for project: {project_id}")
    print(f"Feedback: {feedback}")
    return 0


def register_pipeline_commands(subparsers: argparse._SubParsersAction) -> None:
    """注册流水线子命令"""
    pipeline_parser = subparsers.add_parser("pipeline", help="Novel generation pipeline")
    pipeline_sub = pipeline_parser.add_subparsers(dest="pipeline_command", required=True)

    # pipeline run
    run_parser = pipeline_sub.add_parser("run", help="Run the pipeline")
    run_parser.add_argument("--topic", help="NovelRadar topic ID")
    run_parser.add_argument("--project", help="Project ID")
    run_parser.add_argument("--mode", choices=["auto", "interactive"], default="interactive",
                          help="Execution mode")
    run_parser.add_argument("--from-stage", help="Start from specific stage")
    run_parser.add_argument("--chapters", type=int, help="Number of chapters to generate")
    run_parser.set_defaults(func=cmd_pipeline_run)

    # pipeline status
    status_parser = pipeline_sub.add_parser("status", help="Show pipeline status")
    status_parser.add_argument("--project", help="Project ID")
    status_parser.set_defaults(func=cmd_pipeline_status)

    # pipeline approve
    approve_parser = pipeline_sub.add_parser("approve", help="Approve current waiting node")
    approve_parser.add_argument("--project", help="Project ID")
    approve_parser.set_defaults(func=cmd_pipeline_approve)

    # pipeline reject
    reject_parser = pipeline_sub.add_parser("reject", help="Reject with feedback")
    reject_parser.add_argument("--project", help="Project ID")
    reject_parser.add_argument("--feedback", help="Rejection feedback")
    reject_parser.set_defaults(func=cmd_pipeline_reject)
