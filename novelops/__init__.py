from __future__ import annotations

from pathlib import Path


_SRC_PACKAGE = Path(__file__).resolve().parents[1] / "src" / "novelops"
if _SRC_PACKAGE.is_dir():
    __path__ = [str(_SRC_PACKAGE), *list(__path__)]  # type: ignore[name-defined]

