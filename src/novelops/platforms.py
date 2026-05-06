from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import ROOT


_DEFAULT_PLATFORMS_FILE = ROOT / "configs" / "platforms.example.json"
_PLATFORMS_FILE = ROOT / "configs" / "platforms.json"


def _load_platforms() -> dict[str, Any]:
    path = _PLATFORMS_FILE if _PLATFORMS_FILE.exists() else _DEFAULT_PLATFORMS_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get_platform(platform_id: str) -> dict[str, Any]:
    platforms = _load_platforms()
    if platform_id not in platforms:
        raise KeyError(f"Unknown platform: {platform_id}")
    return platforms[platform_id]


def list_platforms() -> list[str]:
    return list(_load_platforms().keys())


def get_platform_metrics(platform_id: str) -> list[str]:
    return get_platform(platform_id).get("primary_metrics", [])


def get_platform_review_focus(platform_id: str) -> list[str]:
    return get_platform(platform_id).get("review_focus", [])


def get_platform_risk_focus(platform_id: str) -> list[str]:
    return get_platform(platform_id).get("risk_focus", [])
