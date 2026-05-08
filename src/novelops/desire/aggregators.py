"""Pure Python aggregators for Radar analyzed_signals."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def fetch_analyzed_signals(
    db_path: Path,
    window_days: int = 14,
    genre_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch analyzed signals from Radar DB within a time window.

    Args:
        db_path: Path to radar.sqlite
        window_days: Look back N days from now
        genre_filter: Optional genre to filter by (matches llm_genre)

    Returns:
        List of signal dicts
    """
    if not db_path.is_file():
        return []

    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).strftime("%Y-%m-%dT%H:%M:%S")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        query = """
            SELECT signal_id, title, platform, category, sub_category, tags,
                   llm_genre, llm_core_desire, llm_hook, llm_golden_finger,
                   llm_reader_emotion, llm_risk, analyzed_at
            FROM analyzed_signals
            WHERE analyzed_at >= ?
        """
        params: list[Any] = [cutoff]

        if genre_filter:
            query += " AND llm_genre LIKE ?"
            params.append(f"%{genre_filter}%")

        query += " ORDER BY analyzed_at DESC"

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def aggregate_emotions(signals: list[dict[str, Any]]) -> list[tuple[str, int]]:
    """Aggregate reader emotions from signals. Returns sorted (emotion, count) list."""
    counter: Counter[str] = Counter()
    for s in signals:
        raw = s.get("llm_reader_emotion") or ""
        if not raw:
            continue
        try:
            emotions = json.loads(raw) if raw.startswith("[") else [raw]
        except (json.JSONDecodeError, TypeError):
            emotions = [raw]
        for e in emotions:
            if isinstance(e, str) and e.strip():
                counter[e.strip()] += 1
    return counter.most_common(20)


def aggregate_golden_fingers(signals: list[dict[str, Any]]) -> list[tuple[str, int]]:
    """Aggregate golden finger types from signals."""
    counter: Counter[str] = Counter()
    for s in signals:
        gf = (s.get("llm_golden_finger") or "").strip()
        if gf and gf != "无明显金手指":
            counter[gf] += 1
    return counter.most_common(15)


def aggregate_hooks(signals: list[dict[str, Any]]) -> list[tuple[str, int]]:
    """Aggregate hooks from signals."""
    counter: Counter[str] = Counter()
    for s in signals:
        hook = (s.get("llm_hook") or "").strip()
        if hook:
            counter[hook] += 1
    return counter.most_common(15)


def aggregate_risks(signals: list[dict[str, Any]]) -> list[tuple[str, int]]:
    """Aggregate risks from signals."""
    counter: Counter[str] = Counter()
    for s in signals:
        risk = (s.get("llm_risk") or "").strip()
        if risk:
            counter[risk] += 1
    return counter.most_common(10)


def aggregate_desires(signals: list[dict[str, Any]]) -> list[tuple[str, int]]:
    """Aggregate core desires from signals."""
    counter: Counter[str] = Counter()
    for s in signals:
        desire = (s.get("llm_core_desire") or "").strip()
        if desire:
            counter[desire] += 1
    return counter.most_common(15)


def aggregate_genres(signals: list[dict[str, Any]]) -> list[tuple[str, int]]:
    """Aggregate genres from signals."""
    counter: Counter[str] = Counter()
    for s in signals:
        genre = (s.get("llm_genre") or "").strip()
        if genre:
            counter[genre] += 1
    return counter.most_common(10)


def build_trope_library(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build trope library from signals. Pure aggregation, no LLM."""
    genre_groups: dict[str, list[dict[str, Any]]] = {}
    for s in signals:
        genre = (s.get("llm_genre") or "未知").strip()
        genre_groups.setdefault(genre, []).append(s)

    tropes = []
    for genre, group in genre_groups.items():
        hooks = aggregate_hooks(group)
        gfs = aggregate_golden_fingers(group)
        tropes.append({
            "name": genre,
            "frequency": len(group),
            "platform_distribution": _platform_dist(group),
            "chapter_position": "开篇",
            "representative_works": [s.get("title", "") for s in group[:3]],
            "top_hooks": [h[0] for h in hooks[:3]],
            "top_golden_fingers": [g[0] for g in gfs[:3]],
        })

    tropes.sort(key=lambda t: t["frequency"], reverse=True)
    return tropes


def build_competitor_patterns(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build competitor patterns from signals. Pure aggregation, no LLM."""
    genre_groups: dict[str, list[dict[str, Any]]] = {}
    for s in signals:
        genre = (s.get("llm_genre") or "未知").strip()
        genre_groups.setdefault(genre, []).append(s)

    patterns = []
    for genre, group in genre_groups.items():
        hooks = aggregate_hooks(group)
        risks = aggregate_risks(group)
        patterns.append({
            "genre": genre,
            "opening_hooks": [h[0] for h in hooks[:5]],
            "saturation_warnings": [r[0] for r in risks[:3]],
        })

    patterns.sort(key=lambda p: len(genre_groups.get(p["genre"], [])), reverse=True)
    return patterns


def _platform_dist(signals: list[dict[str, Any]]) -> dict[str, int]:
    """Count signals per platform."""
    counter: Counter[str] = Counter()
    for s in signals:
        platform = (s.get("platform") or "unknown").strip()
        counter[platform] += 1
    return dict(counter)
