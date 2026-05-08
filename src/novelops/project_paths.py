from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Old directory names → new directory names
_DIR_ALIASES: dict[str, str] = {
    "intelligence": "market",
    "bible": "story/bible",
    "outlines": "story/outlines",
    "state": "story/state",
    "generation": "production/generation",
    "reviews": "production/reviews",
    "corpus": "production/corpus",
    "publish": "production/publish",
    "experiments": "production/experiments",
}

# New canonical subdirectories (used by init_project and check)
_NEW_STANDARD_DIRS: list[str] = [
    "market/raw/manual_notes",
    "market/processed",
    "market/reports",
    "story/bible",
    "story/outlines",
    "story/state",
    "production/generation",
    "production/reviews",
    "production/corpus",
    "production/publish",
    "production/experiments",
]


@dataclass
class ProjectPaths:
    """Unified project path resolver with three-tier fallback.

    Resolution order for each logical directory:
      1. ``project.json`` ``directories`` mapping (if key present and path exists)
      2. New canonical path (e.g. ``story/bible``) if it exists on disk
      3. Old legacy path (e.g. ``bible``) as final fallback
    """

    root: Path
    _dir_map: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        cfg_path = self.root / "project.json"
        if cfg_path.is_file():
            try:
                import json

                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                self._dir_map = dict(cfg.get("directories", {}))
            except Exception:
                self._dir_map = {}

    # ── helpers ──────────────────────────────────────────────────────

    def _resolve(self, logical: str, new_path: str, old_path: str) -> Path:
        """Three-tier resolution."""
        # 1. project.json mapping
        mapped = self._dir_map.get(logical)
        if mapped:
            candidate = self.root / mapped
            if candidate.is_dir():
                return candidate
        # 2. New canonical path
        candidate = self.root / new_path
        if candidate.is_dir():
            return candidate
        # 3. Old legacy path
        return self.root / old_path

    def _resolve_file(self, logical: str, new_path: str, old_path: str, filename: str) -> Path:
        """Resolve a file inside a logical directory."""
        return self._resolve(logical, new_path, old_path) / filename

    # ── market ───────────────────────────────────────────────────────

    @property
    def market(self) -> Path:
        return self._resolve("intelligence", "market", "intelligence")

    @property
    def market_raw_notes(self) -> Path:
        return self.market / "raw" / "manual_notes"

    @property
    def market_processed(self) -> Path:
        return self.market / "processed"

    @property
    def market_reports(self) -> Path:
        return self.market / "reports"

    # ── story ────────────────────────────────────────────────────────

    @property
    def story(self) -> Path:
        return self.root / "story"

    @property
    def bible(self) -> Path:
        return self._resolve("bible", "story/bible", "bible")

    @property
    def outlines(self) -> Path:
        return self._resolve("outlines", "story/outlines", "outlines")

    @property
    def state(self) -> Path:
        return self._resolve("state", "story/state", "state")

    # ── production ───────────────────────────────────────────────────

    @property
    def production(self) -> Path:
        return self.root / "production"

    @property
    def generation(self) -> Path:
        return self._resolve("generation", "production/generation", "generation")

    @property
    def reviews(self) -> Path:
        return self._resolve("reviews", "production/reviews", "reviews")

    @property
    def corpus(self) -> Path:
        return self._resolve("corpus", "production/corpus", "corpus")

    @property
    def publish(self) -> Path:
        return self._resolve("publish", "production/publish", "publish")

    @property
    def experiments(self) -> Path:
        return self._resolve("experiments", "production/experiments", "experiments")

    # ── convenience methods ──────────────────────────────────────────

    def chapter_dir(self, chapter: int) -> Path:
        return self.generation / f"chapter_{chapter:03d}"

    def review_path(self, chapter: int) -> Path:
        return self.reviews / f"chapter_{chapter:03d}_review.json"

    def panel_path(self, chapter: int) -> Path:
        return self.reviews / f"chapter_{chapter:03d}_panel.json"

    def revision_queue(self) -> Path:
        return self.reviews / "revision_queue"

    def bible_file(self, name: str) -> Path:
        return self.bible / name

    def state_file(self, name: str) -> Path:
        return self.state / name

    def outlines_file(self, name: str) -> Path:
        return self.outlines / name

    def corpus_volume(self, volume: int = 1) -> Path:
        return self.corpus / f"volume_{volume:02d}"

    # ── static helpers ───────────────────────────────────────────────

    @staticmethod
    def standard_dirs() -> list[str]:
        """Return the canonical list of new-style subdirectories."""
        return list(_NEW_STANDARD_DIRS)
