from __future__ import annotations

import pytest

from novelops.platforms import (
    get_platform,
    get_platform_metrics,
    get_platform_review_focus,
    get_platform_risk_focus,
    list_platforms,
)


def test_list_platforms():
    platforms = list_platforms()
    assert "fanqie" in platforms
    assert "qidian" in platforms
    assert "manual" in platforms


def test_get_platform_fanqie():
    platform = get_platform("fanqie")
    assert platform["name"] == "番茄小说"
    assert platform["business_model"] == "free_reading"
    assert isinstance(platform["primary_metrics"], list)
    assert len(platform["primary_metrics"]) > 0


def test_get_platform_qidian():
    platform = get_platform("qidian")
    assert platform["name"] == "起点中文网"
    assert platform["business_model"] == "paid_serial"
    assert "views" in platform["primary_metrics"]
    assert "collections" in platform["primary_metrics"]


def test_get_platform_manual():
    platform = get_platform("manual")
    assert platform["name"] == "手动平台"
    assert platform["business_model"] == "unknown"


def test_get_platform_unknown():
    with pytest.raises(KeyError, match="Unknown platform"):
        get_platform("nonexistent")


def test_get_platform_metrics():
    metrics = get_platform_metrics("qidian")
    assert "views" in metrics
    assert "collections" in metrics
    assert "income" in metrics


def test_get_platform_review_focus():
    focus = get_platform_review_focus("fanqie")
    assert "开篇钩子" in focus
    assert "爽点密度" in focus


def test_get_platform_risk_focus():
    focus = get_platform_risk_focus("qidian")
    assert "同类竞争强" in focus
    assert "读者挑剔" in focus


def test_platform_fields_complete():
    platforms = list_platforms()
    required_fields = ["name", "business_model", "primary_metrics", "review_focus", "risk_focus"]
    for pid in platforms:
        platform = get_platform(pid)
        for field in required_fields:
            assert field in platform, f"Platform {pid} missing field {field}"
