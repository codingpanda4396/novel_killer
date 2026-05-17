"""流水线CLI命令

支持：
- pipeline run: 运行流水线
- pipeline status: 查看状态
- pipeline show: 可视化显示工作流
- pipeline edit: 交互式编辑工作流
- pipeline approve: 增强的批准命令
- pipeline reject: 增强的拒绝命令
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ..config import ConfigError, default_project_id, load_app_config
from ..paths import project_dir
from ..project_paths import ProjectPaths
from .config import load_pipeline_config, save_pipeline_config
from .graph import compile_pipeline
from .state import create_initial_state


# 工作流节点定义
WORKFLOW_NODES = [
    {"id": "desire_synthesis", "name": "欲望合成", "description": "分析读者欲望和需求"},
    {"id": "market_research", "name": "市场调研", "description": "收集市场热点数据"},
    {"id": "concept_design", "name": "概念设计", "description": "设计小说核心概念"},
    {"id": "outline", "name": "大纲生成", "description": "生成章节大纲"},
    {"id": "chapter_plan", "name": "章节规划", "description": "规划具体章节内容"},
    {"id": "draft", "name": "初稿生成", "description": "生成章节初稿"},
    {"id": "commercial_review", "name": "商业审稿", "description": "优化爽点和冲突"},
    {"id": "continuity_check", "name": "连续性检查", "description": "检查逻辑连贯性"},
    {"id": "rewrite", "name": "改写优化", "description": "最终改写和润色"},
    {"id": "panel_review", "name": "面板审稿", "description": "多角色审稿评估"},
    {"id": "save", "name": "保存结果", "description": "保存章节到项目"},
]


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
    paths = ProjectPaths(project_path)

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
    generation_path = paths.generation
    if generation_path.exists():
        chapters = sorted(generation_path.glob("chapter_*"))
        print(f"\nGenerated chapters: {len(chapters)}")
        for chapter_dir in chapters[-5:]:  # 只显示最近 5 个
            print(f"  - {chapter_dir.name}")
    else:
        print("\nNo chapters generated yet.")

    return 0


def cmd_pipeline_show(args: argparse.Namespace) -> int:
    """可视化显示工作流"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    # 加载配置
    config = load_pipeline_config(project_path)
    mode = config.get("mode", "interactive")
    approval_points = set(config.get("approval_points", []))
    disabled_nodes = set(config.get("disabled_nodes", []))

    # 检查当前状态
    approval_file = project_path / ".pipeline_approval"
    feedback_file = project_path / ".pipeline_feedback"
    waiting_approval = approval_file.exists()
    has_feedback = feedback_file.exists()

    print(f"Pipeline: {project_id}")
    print(f"Mode: {mode}")
    print()

    # 显示节点
    for i, node in enumerate(WORKFLOW_NODES):
        node_id = node["id"]
        name = node["name"]
        desc = node["description"]

        # 状态标记
        if node_id in disabled_nodes:
            status = "[ ]"
            note = " (已禁用)"
        elif node_id in approval_points:
            status = "[!]"
            note = " (需审核)"
        elif waiting_approval and i == _get_waiting_node_index(config):
            status = "[→]"
            note = " ◀ 等待审核"
        else:
            status = "[✓]"
            note = ""

        # 连接线
        connector = " → " if i < len(WORKFLOW_NODES) - 1 else ""

        print(f"{status} {name}{note}")
        if args.verbose:
            print(f"     {desc}")

        if connector and i < len(WORKFLOW_NODES) - 1:
            next_node = WORKFLOW_NODES[i + 1]
            print(f"     │")
            print(f"     └─→ {next_node['name']}")

    # 显示等待状态
    if waiting_approval:
        print()
        print("当前状态: 等待审核批准")
        print("操作:")
        print("  novelops pipeline approve    # 批准继续")
        print("  novelops pipeline reject     # 拒绝并提供反馈")

    if has_feedback:
        print()
        try:
            feedback_data = json.loads(feedback_file.read_text(encoding="utf-8"))
            print(f"最近反馈: {feedback_data.get('feedback', '')}")
        except Exception:
            pass

    return 0


def _get_waiting_node_index(config: dict[str, Any]) -> int:
    """获取等待审核的节点索引"""
    approval_points = config.get("approval_points", [])
    if not approval_points:
        return -1

    # 找到第一个审核点
    for i, node in enumerate(WORKFLOW_NODES):
        if node["id"] in approval_points:
            return i

    return -1


def cmd_pipeline_edit(args: argparse.Namespace) -> int:
    """交互式编辑工作流"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    # 加载配置
    config = load_pipeline_config(project_path)

    print(f"编辑工作流: {project_id}")
    print()

    while True:
        print("可用操作:")
        print("  1. 查看当前配置")
        print("  2. 启用/禁用节点")
        print("  3. 设置审核点")
        print("  4. 修改执行模式")
        print("  5. 修改重试次数")
        print("  6. 保存并退出")
        print("  7. 不保存退出")

        choice = input("\n请选择操作 [1-7]: ").strip()

        if choice == "1":
            _show_config(config)
        elif choice == "2":
            _edit_disabled_nodes(config)
        elif choice == "3":
            _edit_approval_points(config)
        elif choice == "4":
            _edit_mode(config)
        elif choice == "5":
            _edit_retry_attempts(config)
        elif choice == "6":
            save_pipeline_config(project_path, config)
            print("配置已保存")
            return 0
        elif choice == "7":
            print("已退出，未保存修改")
            return 0
        else:
            print("无效选择，请重试")

        print()


def _show_config(config: dict[str, Any]):
    """显示当前配置"""
    print("\n当前配置:")
    print(f"  模式: {config.get('mode', 'interactive')}")
    print(f"  审核点: {', '.join(config.get('approval_points', [])) or '无'}")
    print(f"  禁用节点: {', '.join(config.get('disabled_nodes', [])) or '无'}")
    print(f"  最大重试: {config.get('max_retry_attempts', 2)}")


def _edit_disabled_nodes(config: dict[str, Any]):
    """编辑禁用节点"""
    disabled = set(config.get("disabled_nodes", []))

    print("\n可用节点:")
    for i, node in enumerate(WORKFLOW_NODES, 1):
        status = "✗" if node["id"] in disabled else "✓"
        print(f"  {i}. [{status}] {node['name']} ({node['id']})")

    print(f"\n当前禁用: {', '.join(disabled) or '无'}")
    print("输入节点编号切换状态，多个用逗号分隔，回车确认:")

    try:
        input_str = input("> ").strip()
        if not input_str:
            return

        indices = [int(x.strip()) for x in input_str.split(",")]
        for idx in indices:
            if 1 <= idx <= len(WORKFLOW_NODES):
                node_id = WORKFLOW_NODES[idx - 1]["id"]
                if node_id in disabled:
                    disabled.remove(node_id)
                    print(f"  已启用: {WORKFLOW_NODES[idx - 1]['name']}")
                else:
                    disabled.add(node_id)
                    print(f"  已禁用: {WORKFLOW_NODES[idx - 1]['name']}")

        config["disabled_nodes"] = list(disabled)
    except ValueError:
        print("输入无效")


def _edit_approval_points(config: dict[str, Any]):
    """编辑审核点"""
    approval_points = set(config.get("approval_points", []))

    print("\n可用节点:")
    for i, node in enumerate(WORKFLOW_NODES, 1):
        status = "✓" if node["id"] in approval_points else " "
        print(f"  {i}. [{status}] {node['name']} ({node['id']})")

    print(f"\n当前审核点: {', '.join(approval_points) or '无'}")
    print("输入节点编号切换状态，多个用逗号分隔，回车确认:")

    try:
        input_str = input("> ").strip()
        if not input_str:
            return

        indices = [int(x.strip()) for x in input_str.split(",")]
        for idx in indices:
            if 1 <= idx <= len(WORKFLOW_NODES):
                node_id = WORKFLOW_NODES[idx - 1]["id"]
                if node_id in approval_points:
                    approval_points.remove(node_id)
                    print(f"  已移除审核点: {WORKFLOW_NODES[idx - 1]['name']}")
                else:
                    approval_points.add(node_id)
                    print(f"  已添加审核点: {WORKFLOW_NODES[idx - 1]['name']}")

        config["approval_points"] = list(approval_points)
    except ValueError:
        print("输入无效")


def _edit_mode(config: dict[str, Any]):
    """编辑执行模式"""
    current_mode = config.get("mode", "interactive")
    print(f"\n当前模式: {current_mode}")
    print("可用模式:")
    print("  1. interactive (交互式，需要审核)")
    print("  2. auto (自动，无需审核)")

    choice = input("选择模式 [1-2]: ").strip()
    if choice == "1":
        config["mode"] = "interactive"
        print("已设置为交互式模式")
    elif choice == "2":
        config["mode"] = "auto"
        print("已设置为自动模式")


def _edit_retry_attempts(config: dict[str, Any]):
    """编辑重试次数"""
    current = config.get("max_retry_attempts", 2)
    print(f"\n当前最大重试次数: {current}")

    try:
        new_value = input("输入新的重试次数 (0-10): ").strip()
        if new_value:
            value = int(new_value)
            if 0 <= value <= 10:
                config["max_retry_attempts"] = value
                print(f"已设置为 {value} 次")
            else:
                print("数值超出范围")
    except ValueError:
        print("输入无效")


def cmd_pipeline_approve(args: argparse.Namespace) -> int:
    """批准当前等待的节点（增强版）"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    # 检查是否有待审核的内容
    approval_file = project_path / ".pipeline_approval"
    feedback_file = project_path / ".pipeline_feedback"

    # 显示当前状态
    config = load_pipeline_config(project_path)
    waiting_node_idx = _get_waiting_node_index(config)

    if waiting_node_idx >= 0:
        node = WORKFLOW_NODES[waiting_node_idx]
        print(f"待审核节点: {node['name']} - {node['description']}")

    # 检查是否有最近生成的内容
    paths = ProjectPaths(project_path)
    latest_chapters = sorted(paths.generation.glob("chapter_*"))
    if latest_chapters:
        latest = latest_chapters[-1]
        print(f"最新生成: {latest.name}")

        # 显示审稿结果（如果有）
        review_files = sorted(latest.glob("*review*.json"))
        if review_files:
            try:
                review_data = json.loads(review_files[-1].read_text(encoding="utf-8"))
                score = review_data.get("score", "N/A")
                passed = review_data.get("passed", False)
                print(f"审稿分数: {score}")
                print(f"审稿结果: {'通过' if passed else '需要修改'}")
            except Exception:
                pass

    # 确认批准
    if not args.yes:
        confirm = input("\n确认批准继续执行？(y/N): ").strip().lower()
        if confirm != "y":
            print("已取消")
            return 0

    # 保存批准状态
    approval_data = {
        "approved": True,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "node": WORKFLOW_NODES[waiting_node_idx]["id"] if waiting_node_idx >= 0 else None,
    }
    approval_file.write_text(json.dumps(approval_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 清除反馈文件
    if feedback_file.exists():
        feedback_file.unlink()

    print(f"\n已批准项目 {project_id}")
    print("运行 'novelops pipeline run' 继续执行")
    return 0


def cmd_pipeline_reject(args: argparse.Namespace) -> int:
    """拒绝并提供反馈（增强版）"""
    project_id = args.project or default_project_id()
    project_path = project_dir(project_id)

    if not project_path.exists():
        print(f"ERROR: Project not found: {project_id}", file=sys.stderr)
        return 1

    # 显示当前状态
    config = load_pipeline_config(project_path)
    waiting_node_idx = _get_waiting_node_index(config)

    if waiting_node_idx >= 0:
        node = WORKFLOW_NODES[waiting_node_idx]
        print(f"待审核节点: {node['name']} - {node['description']}")

    # 获取反馈
    feedback = args.feedback
    if not feedback:
        print("\n请输入拒绝原因和修改建议:")
        feedback = input("> ").strip()
        if not feedback:
            feedback = "未提供具体反馈"

    # 保存反馈
    feedback_data = {
        "rejected": True,
        "feedback": feedback,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "node": WORKFLOW_NODES[waiting_node_idx]["id"] if waiting_node_idx >= 0 else None,
    }
    feedback_file = project_path / ".pipeline_feedback"
    feedback_file.write_text(json.dumps(feedback_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 清除批准文件
    approval_file = project_path / ".pipeline_approval"
    if approval_file.exists():
        approval_file.unlink()

    print(f"\n已拒绝项目 {project_id}")
    print(f"反馈: {feedback}")
    print("\n修改后可重新运行 'novelops pipeline run'")
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

    # pipeline show
    show_parser = pipeline_sub.add_parser("show", help="Visualize workflow")
    show_parser.add_argument("--project", help="Project ID")
    show_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed info")
    show_parser.set_defaults(func=cmd_pipeline_show)

    # pipeline edit
    edit_parser = pipeline_sub.add_parser("edit", help="Edit workflow interactively")
    edit_parser.add_argument("--project", help="Project ID")
    edit_parser.set_defaults(func=cmd_pipeline_edit)

    # pipeline approve
    approve_parser = pipeline_sub.add_parser("approve", help="Approve current waiting node")
    approve_parser.add_argument("--project", help="Project ID")
    approve_parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    approve_parser.set_defaults(func=cmd_pipeline_approve)

    # pipeline reject
    reject_parser = pipeline_sub.add_parser("reject", help="Reject with feedback")
    reject_parser.add_argument("--project", help="Project ID")
    reject_parser.add_argument("--feedback", help="Rejection feedback")
    reject_parser.set_defaults(func=cmd_pipeline_reject)
