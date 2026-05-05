from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import load_app_config, read_json, write_json


DEFAULT_PIPELINE_CONFIG = {
    "mode": "interactive",
    "approval_points": [
        "concept_design",
        "outline",
        "chapter_plan",
    ],
    "max_retry_attempts": 2,
    "chapters_per_run": 1,
    "integrate_radar": True,
    "default_genre": "urban_fantasy",
    "default_platform": "fanqie",
}


def load_pipeline_config(project_path: Path | None = None) -> dict[str, Any]:
    """加载流水线配置

    优先级：
    1. 项目级配置 (project_path / pipeline_config.json)
    2. 全局配置 (~/.novelops/pipeline.json)
    3. 默认配置
    """
    config = dict(DEFAULT_PIPELINE_CONFIG)

    # 尝试加载全局配置
    app_cfg = load_app_config()
    if "pipeline" in app_cfg:
        config.update(app_cfg["pipeline"])

    # 尝试加载项目级配置
    if project_path:
        project_config_path = project_path / "pipeline_config.json"
        if project_config_path.is_file():
            try:
                project_config = read_json(project_config_path)
                config.update(project_config)
            except Exception:
                pass

    return config


def save_pipeline_config(project_path: Path, config: dict[str, Any]) -> None:
    """保存项目级流水线配置"""
    config_path = project_path / "pipeline_config.json"
    write_json(config_path, config)


def get_approval_points(config: dict[str, Any]) -> list[str]:
    """获取需要人工确认的节点列表"""
    return list(config.get("approval_points", []))


def is_auto_mode(config: dict[str, Any]) -> bool:
    """检查是否为全自动模式"""
    return config.get("mode") == "auto"


def get_max_retry_attempts(config: dict[str, Any]) -> int:
    """获取最大重试次数"""
    return int(config.get("max_retry_attempts", 2))
