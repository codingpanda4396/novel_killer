from __future__ import annotations

import os
from pathlib import Path

from sqlmodel import create_engine

from novelops.paths import RUNTIME_DIR


DEFAULT_SQLITE_PATH = RUNTIME_DIR / "novelops.sqlite3"


def database_url(path: Path | None = None) -> str:
    """Return the configured SQLAlchemy URL for the main NovelOps database."""
    if path is not None:
        return f"sqlite:///{path}"
    env_url = os.environ.get("NOVELOPS_DB_URL")
    if env_url:
        return env_url
    legacy_path = os.environ.get("NOVELOPS_DB")
    if legacy_path:
        return f"sqlite:///{Path(legacy_path)}"
    return f"sqlite:///{DEFAULT_SQLITE_PATH}"


def engine_from_url(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    if url.startswith("sqlite:///"):
        Path(url[len("sqlite:///"):]).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, connect_args=connect_args)


def get_engine(path: Path | None = None):
    return engine_from_url(database_url(path))
