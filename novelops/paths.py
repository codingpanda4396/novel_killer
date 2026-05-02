from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = ROOT / "projects"
CONFIG_DIR = ROOT / "config"
RUNTIME_DIR = ROOT / "runtime"


def project_dir(project: str) -> Path:
    return PROJECTS_DIR / project


def all_project_dirs() -> list[Path]:
    if not PROJECTS_DIR.is_dir():
        return []
    return sorted(path for path in PROJECTS_DIR.iterdir() if (path / "project.json").is_file())


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)
