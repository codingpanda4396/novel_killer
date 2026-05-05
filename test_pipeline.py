#!/usr/bin/env python3
"""Test script for the pipeline module"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from novelops.pipeline import (
    PipelineState,
    create_initial_state,
    build_pipeline_graph,
    compile_pipeline,
    load_pipeline_config,
)


def test_state_creation():
    """测试状态创建"""
    state = create_initial_state(
        project_id="test_project",
        project_path=Path("projects/test_project"),
        mode="interactive",
        topic_id="test_topic",
    )

    assert state["project_id"] == "test_project"
    assert state["mode"] == "interactive"
    assert state["topic_id"] == "test_topic"
    assert state["current_chapter"] == 1
    assert state["retry_count"] == 0
    print("✓ State creation test passed")


def test_config_loading():
    """测试配置加载"""
    config = load_pipeline_config()

    assert "mode" in config
    assert "approval_points" in config
    assert "max_retry_attempts" in config
    print("✓ Config loading test passed")


def test_graph_building():
    """测试图构建"""
    graph = build_pipeline_graph()

    # 检查节点是否存在
    nodes = list(graph.nodes)
    expected_nodes = [
        "market_research",
        "concept_design",
        "outline",
        "chapter_plan",
        "draft",
        "commercial_review",
        "continuity_check",
        "rewrite",
        "save",
        "error",
        "wait_approval",
    ]

    for node in expected_nodes:
        assert node in nodes, f"Missing node: {node}"

    print("✓ Graph building test passed")


def test_pipeline_compilation():
    """测试流水线编译"""
    pipeline = compile_pipeline()

    assert pipeline is not None
    print("✓ Pipeline compilation test passed")


if __name__ == "__main__":
    print("Running pipeline tests...\n")

    try:
        test_state_creation()
        test_config_loading()
        test_graph_building()
        test_pipeline_compilation()

        print("\n✓ All tests passed!")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
