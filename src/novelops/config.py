from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .paths import CONFIG_DIR, RUNTIME_DIR, project_dir


class ConfigError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_app_config() -> dict[str, Any]:
    path = CONFIG_DIR / "novelops.json"
    if path.is_file():
        return read_json(path)
    example = CONFIG_DIR / "novelops.example.json"
    if example.is_file():
        return read_json(example)
    return {}


def default_project_id() -> str:
    return str(load_app_config().get("default_project") or "life_balance")


def db_path() -> Path:
    env = os.environ.get("NOVELOPS_DB")
    if env:
        return Path(env)
    configured = load_app_config().get("db_path")
    if configured:
        path = Path(str(configured))
        return path if path.is_absolute() else RUNTIME_DIR.parent / path
    return RUNTIME_DIR / "novelops.sqlite3"


def load_project(project: str) -> dict[str, Any]:
    return read_json(project_dir(project) / "project.json")


def load_project_path(project_path: Path) -> dict[str, Any]:
    return read_json(project_path / "project.json")


def threshold(project_config: dict[str, Any], key: str = "chapter") -> float:
    return float(project_config.get("review_thresholds", {}).get(key, 80))


def load_invites() -> dict[str, dict[str, str]]:
    """加载邀请码配置"""
    app_cfg = load_app_config()
    return app_cfg.get("invites", {})


def validate_invite_code(code: str) -> dict[str, str] | None:
    """验证邀请码，返回邀请码信息或 None

    支持两种格式：
    1. 新格式：{"user_id": "xxx", "username": "xxx"}
    2. 旧格式（向后兼容）：{"project": "xxx", "label": "xxx"}
    """
    invites = load_invites()
    invite_info = invites.get(code)
    if not invite_info:
        return None

    # 如果是旧格式（包含project字段），转换为新格式
    if "project" in invite_info and "user_id" not in invite_info:
        return {
            "user_id": invite_info["project"],  # 使用项目ID作为用户ID
            "username": invite_info.get("label", invite_info["project"]),
            "_legacy_project": invite_info["project"]  # 保留原始项目ID用于迁移
        }

    return invite_info


def get_session_secret() -> str:
    """获取 session 密钥"""
    app_cfg = load_app_config()
    secret = app_cfg.get("web", {}).get("session_secret")
    if not secret or secret == "CHANGE_THIS_IN_PRODUCTION":
        import os
        if os.environ.get("NOVELOPS_ENV") == "production":
            raise ConfigError("生产环境必须配置 web.session_secret")
        # 开发环境使用默认值
        return "dev-secret-key-not-for-production"
    return str(secret)
