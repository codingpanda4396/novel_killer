from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlmodel import Session

from .engine import get_engine


@contextmanager
def session_scope(path: Path | None = None) -> Iterator[Session]:
    session = Session(get_engine(path))
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
