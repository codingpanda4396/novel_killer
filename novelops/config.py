from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import project_dir


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


def load_project(project: str) -> dict[str, Any]:
    return read_json(project_dir(project) / "project.json")


def threshold(project_config: dict[str, Any], key: str = "chapter") -> float:
    return float(project_config.get("review_thresholds", {}).get(key, 80))

