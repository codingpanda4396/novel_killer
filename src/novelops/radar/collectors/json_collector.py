from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .base import BaseCollector
from ..models import RawNovelSignal


class JSONCollector(BaseCollector):
    """JSON 文件采集器"""
    
    def __init__(self, json_path: Path, platform: str = "unknown"):
        self.json_path = json_path
        self.platform = platform
    
    @property
    def name(self) -> str:
        return f"JSON Collector ({self.json_path.name})"
    
    @property
    def source(self) -> str:
        return "manual"
    
    def collect(self) -> list[RawNovelSignal]:
        with open(self.json_path, encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            data = data.get("items", data.get("data", [data]))
        
        signals = []
        for item in data:
            signal = self._parse_item(item)
            if signal:
                signals.append(signal)
        return signals
    
    def _parse_item(self, item: dict) -> RawNovelSignal | None:
        title = item.get("title", "").strip()
        if not title:
            return None
        
        tags = item.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        
        return RawNovelSignal(
            signal_id=item.get("signal_id", str(uuid.uuid4())),
            source=item.get("source", self.source),
            source_type=item.get("source_type", "manual"),
            platform=item.get("platform", self.platform),
            rank_type=item.get("rank_type"),
            rank_position=item.get("rank_position"),
            title=title,
            author=item.get("author"),
            category=item.get("category"),
            sub_category=item.get("sub_category"),
            tags=tags,
            description=item.get("description"),
            hot_score=item.get("hot_score"),
            comment_count=item.get("comment_count"),
            like_count=item.get("like_count"),
            read_count=item.get("read_count"),
            collected_at=item.get("collected_at", datetime.now(timezone.utc).isoformat()),
            raw_payload=item,
        )
