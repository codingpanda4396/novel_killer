from __future__ import annotations

import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .base import BaseCollector
from ..models import RawNovelSignal


class CSVCollector(BaseCollector):
    """CSV 文件采集器"""
    
    def __init__(self, csv_path: Path, platform: str = "unknown"):
        self.csv_path = csv_path
        self.platform = platform
    
    @property
    def name(self) -> str:
        return f"CSV Collector ({self.csv_path.name})"
    
    @property
    def source(self) -> str:
        return "manual"
    
    def collect(self) -> list[RawNovelSignal]:
        signals = []
        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                signal = self._parse_row(row)
                if signal:
                    signals.append(signal)
        return signals
    
    def _parse_row(self, row: dict[str, str]) -> RawNovelSignal | None:
        title = row.get("title", "").strip()
        if not title:
            return None
        
        tags = self._parse_tags(row.get("tags", ""))
        
        return RawNovelSignal(
            signal_id=row.get("signal_id", str(uuid.uuid4())),
            source=row.get("source", self.source),
            source_type=row.get("source_type", "manual"),
            platform=row.get("platform", self.platform),
            rank_type=row.get("rank_type"),
            rank_position=self._safe_int(row.get("rank_position")),
            title=title,
            author=row.get("author"),
            category=row.get("category"),
            sub_category=row.get("sub_category"),
            tags=tags,
            description=row.get("description"),
            hot_score=self._safe_float(row.get("hot_score")),
            comment_count=self._safe_int(row.get("comment_count")),
            like_count=self._safe_int(row.get("like_count")),
            read_count=self._safe_int(row.get("read_count")),
            collected_at=row.get("collected_at", datetime.now(timezone.utc).isoformat()),
            raw_payload=dict(row),
        )
    
    def _parse_tags(self, tags_str: str) -> list[str]:
        if not tags_str:
            return []
        for sep in ["|", "，", ",", "、"]:
            if sep in tags_str:
                return [t.strip() for t in tags_str.split(sep) if t.strip()]
        return [tags_str.strip()] if tags_str.strip() else []
    
    def _safe_int(self, value: str | None) -> int | None:
        if not value:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_float(self, value: str | None) -> float | None:
        if not value:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
