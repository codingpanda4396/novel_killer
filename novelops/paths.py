from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = ROOT / "projects"
CONFIG_DIR = ROOT / "config"


def project_dir(project: str) -> Path:
    return PROJECTS_DIR / project


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))

