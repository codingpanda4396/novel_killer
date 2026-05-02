from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: Path | None = None) -> None:
    """从 .env 文件加载环境变量"""
    if path is None:
        # 尝试多个可能的位置
        candidates = [
            Path.cwd() / ".env",
            Path(__file__).resolve().parents[1] / ".env",
            Path.home() / ".novelops" / ".env",
        ]
        for candidate in candidates:
            if candidate.is_file():
                path = candidate
                break
        if path is None:
            return
    if not path.is_file():
        return
    loaded = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and not os.getenv(key):
                    os.environ[key] = value
                    loaded.append(key)
    if loaded:
        print(f"[dotenv] Loaded: {', '.join(loaded)}")


# 自动加载 - 在模块导入时立即执行
load_dotenv()
