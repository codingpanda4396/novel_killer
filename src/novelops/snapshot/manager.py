"""项目快照管理器

支持自动快照（每5分钟，保留20条）和手动快照（永久保留）
"""
from __future__ import annotations

import gzip
import json
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..paths import RUNTIME_DIR


@dataclass
class SnapshotInfo:
    """快照信息"""
    id: str
    project_id: str
    type: str  # "auto" or "manual"
    description: str
    created_at: str
    file_path: str
    size_bytes: int
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SnapshotManager:
    """快照管理器

    自动快照：每5分钟，保留20条
    手动快照：永久保留
    """

    AUTO_SNAPSHOT_INTERVAL = 300  # 5分钟
    MAX_AUTO_SNAPSHOTS = 20

    def __init__(self, project_id: str, project_path: Path):
        self.project_id = project_id
        self.project_path = project_path
        self._snapshot_dir = RUNTIME_DIR / "snapshots" / project_id
        self._auto_dir = self._snapshot_dir / "auto"
        self._manual_dir = self._snapshot_dir / "manual"
        self._ensure_dirs()

        self._auto_timer: threading.Timer | None = None
        self._running = False

    def _ensure_dirs(self):
        """确保目录存在"""
        self._auto_dir.mkdir(parents=True, exist_ok=True)
        self._manual_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(
        self,
        description: str = "",
        snapshot_type: str = "manual",
        data: dict[str, Any] | None = None,
    ) -> SnapshotInfo:
        """创建快照

        Args:
            description: 快照描述
            snapshot_type: "auto" 或 "manual"
            data: 自定义数据，如果为None则自动收集项目状态

        Returns:
            SnapshotInfo
        """
        now = datetime.now(timezone.utc)
        snapshot_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # 收集数据
        if data is None:
            data = self._collect_project_state()

        # 添加元数据
        data["_meta"] = {
            "snapshot_id": snapshot_id,
            "project_id": self.project_id,
            "type": snapshot_type,
            "description": description,
            "created_at": now.isoformat(),
        }

        # 确定存储路径
        if snapshot_type == "auto":
            target_dir = self._auto_dir
            expires_at = (now + timedelta(days=7)).isoformat()  # 自动快照7天后过期
        else:
            target_dir = self._manual_dir
            expires_at = None

        # 保存
        file_path = target_dir / f"{snapshot_id}.json.gz"
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        with gzip.open(file_path, "wt", encoding="utf-8") as f:
            f.write(json_str)

        size_bytes = file_path.stat().st_size

        info = SnapshotInfo(
            id=snapshot_id,
            project_id=self.project_id,
            type=snapshot_type,
            description=description,
            created_at=now.isoformat(),
            file_path=str(file_path),
            size_bytes=size_bytes,
            expires_at=expires_at,
        )

        # 清理过期自动快照
        if snapshot_type == "auto":
            self._cleanup_auto_snapshots()

        return info

    def list_snapshots(self, snapshot_type: str | None = None) -> list[SnapshotInfo]:
        """列出快照"""
        snapshots = []

        if snapshot_type is None or snapshot_type == "auto":
            snapshots.extend(self._list_dir(self._auto_dir, "auto"))
        if snapshot_type is None or snapshot_type == "manual":
            snapshots.extend(self._list_dir(self._manual_dir, "manual"))

        # 按时间倒序
        snapshots.sort(key=lambda s: s.created_at, reverse=True)
        return snapshots

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        """获取快照数据"""
        # 查找文件
        for dir_path in [self._auto_dir, self._manual_dir]:
            file_path = dir_path / f"{snapshot_id}.json.gz"
            if file_path.exists():
                with gzip.open(file_path, "rt", encoding="utf-8") as f:
                    return json.load(f)
        return None

    def restore_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """恢复快照

        Returns:
            快照数据，调用者负责实际恢复操作
        """
        data = self.get_snapshot(snapshot_id)
        if data is None:
            raise FileNotFoundError(f"快照不存在: {snapshot_id}")
        return data

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """删除快照"""
        for dir_path in [self._auto_dir, self._manual_dir]:
            file_path = dir_path / f"{snapshot_id}.json.gz"
            if file_path.exists():
                file_path.unlink()
                return True
        return False

    def start_auto_snapshot(self):
        """启动自动快照"""
        if self._running:
            return
        self._running = True
        self._schedule_next()

    def stop_auto_snapshot(self):
        """停止自动快照"""
        self._running = False
        if self._auto_timer:
            self._auto_timer.cancel()
            self._auto_timer = None

    def _schedule_next(self):
        """调度下一次自动快照"""
        if not self._running:
            return
        self._auto_timer = threading.Timer(
            self.AUTO_SNAPSHOT_INTERVAL,
            self._auto_snapshot_task,
        )
        self._auto_timer.daemon = True
        self._auto_timer.start()

    def _auto_snapshot_task(self):
        """自动快照任务"""
        try:
            self.create_snapshot(
                description="自动快照",
                snapshot_type="auto",
            )
        except Exception:
            pass  # 静默失败
        finally:
            self._schedule_next()

    def _cleanup_auto_snapshots(self):
        """清理过期的自动快照，保留最新的MAX_AUTO_SNAPSHOTS条"""
        snapshots = self._list_dir(self._auto_dir, "auto")

        # 按时间排序
        snapshots.sort(key=lambda s: s.created_at)

        now = datetime.now(timezone.utc)
        to_delete = []

        for snap in snapshots:
            # 删除过期的
            if snap.expires_at:
                expires = datetime.fromisoformat(snap.expires_at)
                if now > expires:
                    to_delete.append(snap)

        # 如果超过最大数量，删除最旧的
        remaining = [s for s in snapshots if s not in to_delete]
        if len(remaining) > self.MAX_AUTO_SNAPSHOTS:
            excess = remaining[:len(remaining) - self.MAX_AUTO_SNAPSHOTS]
            to_delete.extend(excess)

        for snap in to_delete:
            try:
                Path(snap.file_path).unlink(missing_ok=True)
            except Exception:
                pass

    def _list_dir(self, dir_path: Path, snap_type: str) -> list[SnapshotInfo]:
        """列出目录中的快照"""
        snapshots = []
        if not dir_path.exists():
            return snapshots

        for file_path in dir_path.glob("*.json.gz"):
            try:
                snapshot_id = file_path.stem.replace(".json", "")
                # 读取元数据
                with gzip.open(file_path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
                    meta = data.get("_meta", {})

                snapshots.append(SnapshotInfo(
                    id=snapshot_id,
                    project_id=self.project_id,
                    type=snap_type,
                    description=meta.get("description", ""),
                    created_at=meta.get("created_at", ""),
                    file_path=str(file_path),
                    size_bytes=file_path.stat().st_size,
                    expires_at=meta.get("expires_at"),
                ))
            except Exception:
                continue

        return snapshots

    def _collect_project_state(self) -> dict[str, Any]:
        """收集项目当前状态"""
        state: dict[str, Any] = {
            "project_id": self.project_id,
            "project_path": str(self.project_path),
            "files": {},
        }

        # 收集关键文件
        key_files = [
            "project.json",
            "bible/00_story_bible.md",
        ]

        for rel_path in key_files:
            file_path = self.project_path / rel_path
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    state["files"][rel_path] = content
                except Exception:
                    pass

        # 收集大纲
        outlines_dir = self.project_path / "outlines"
        if outlines_dir.exists():
            for md_file in outlines_dir.glob("*.md"):
                try:
                    rel = f"outlines/{md_file.name}"
                    state["files"][rel] = md_file.read_text(encoding="utf-8")
                except Exception:
                    pass

        # 收集状态文件
        state_dir = self.project_path / "state"
        if state_dir.exists():
            for json_file in state_dir.glob("*.json"):
                try:
                    rel = f"state/{json_file.name}"
                    state["files"][rel] = json_file.read_text(encoding="utf-8")
                except Exception:
                    pass

        # 收集最近生成的章节（最多5章）
        generation_dir = self.project_path / "generation"
        if generation_dir.exists():
            chapter_dirs = sorted(generation_dir.glob("chapter_*"))[-5:]
            for chapter_dir in chapter_dirs:
                if chapter_dir.is_dir():
                    for md_file in chapter_dir.glob("*.md"):
                        try:
                            rel = f"generation/{chapter_dir.name}/{md_file.name}"
                            state["files"][rel] = md_file.read_text(encoding="utf-8")
                        except Exception:
                            pass

        return state
