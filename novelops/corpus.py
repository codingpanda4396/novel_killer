from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


CHAPTER_RE = re.compile(r"chapter_(\d{2,3})\.md$")
TITLE_RE = re.compile(r"^#\s*第\s*(\d+)\s*章\s*(.+?)\s*$")


@dataclass(frozen=True)
class CorpusChapter:
    number: int
    title: str
    path: Path
    text: str

    @property
    def word_count(self) -> int:
        return len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+", self.text))


def volume_dir(project_path: Path, volume: int = 1) -> Path:
    return project_path / "corpus" / f"volume_{volume:02d}"


def parse_title(text: str, fallback: str) -> str:
    for line in text.splitlines()[:8]:
        match = TITLE_RE.match(line.strip())
        if match:
            return match.group(2).strip()
    return fallback


def list_chapters(project_path: Path, volume: int = 1) -> list[CorpusChapter]:
    chapters: list[CorpusChapter] = []
    for path in sorted(volume_dir(project_path, volume).glob("chapter_*.md")):
        match = CHAPTER_RE.match(path.name)
        if not match:
            continue
        text = path.read_text(encoding="utf-8")
        number = int(match.group(1))
        chapters.append(CorpusChapter(number, parse_title(text, path.stem), path, text))
    return chapters


def get_chapter(project_path: Path, chapter: int, volume: int = 1) -> CorpusChapter:
    path = volume_dir(project_path, volume) / f"chapter_{chapter:02d}.md"
    text = path.read_text(encoding="utf-8")
    return CorpusChapter(chapter, parse_title(text, path.stem), path, text)


def latest_chapter(project_path: Path, volume: int = 1) -> int:
    chapters = list_chapters(project_path, volume)
    return max((chapter.number for chapter in chapters), default=0)

