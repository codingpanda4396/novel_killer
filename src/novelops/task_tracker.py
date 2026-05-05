from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .paths import ROOT

TASK_DIR = ROOT / "runtime" / "tasks"


@dataclass
class TaskProgress:
    step: str
    detail: str = ""
    percent: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Task:
    task_id: str
    user_id: str
    session_id: str
    intent: str
    project_id: str | None = None
    status: str = "pending"
    progress: list[TaskProgress] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_progress(self, step: str, detail: str = "", percent: int = 0) -> None:
        self.progress.append(TaskProgress(step=step, detail=detail, percent=percent))
        self.updated_at = datetime.now().isoformat()

    def set_status(self, status: str) -> None:
        self.status = status
        self.updated_at = datetime.now().isoformat()

    def set_result(self, result: dict[str, Any]) -> None:
        self.result = result
        self.status = "completed"
        self.updated_at = datetime.now().isoformat()

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = "failed"
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        progress = [TaskProgress(**p) for p in data.get("progress", [])]
        return cls(
            task_id=data["task_id"],
            user_id=data["user_id"],
            session_id=data["session_id"],
            intent=data["intent"],
            project_id=data.get("project_id"),
            status=data.get("status", "pending"),
            progress=progress,
            result=data.get("result"),
            error=data.get("error"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


class TaskTracker:
    def __init__(self) -> None:
        TASK_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def create_task(
        self,
        user_id: str,
        session_id: str,
        intent: str,
        project_id: str | None = None,
    ) -> str:
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            task_id=task_id,
            user_id=user_id,
            session_id=session_id,
            intent=intent,
            project_id=project_id,
        )
        self._save_task(task)
        return task_id

    def get_task(self, task_id: str) -> Task | None:
        path = TASK_DIR / f"{task_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Task.from_dict(data)
        except Exception:
            return None

    def update_progress(
        self, task_id: str, step: str, detail: str = "", percent: int = 0
    ) -> None:
        with self._lock:
            task = self.get_task(task_id)
            if task:
                task.add_progress(step, detail, percent)
                self._save_task(task)

    def set_status(self, task_id: str, status: str) -> None:
        with self._lock:
            task = self.get_task(task_id)
            if task:
                task.set_status(status)
                self._save_task(task)

    def set_result(self, task_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            task = self.get_task(task_id)
            if task:
                task.set_result(result)
                self._save_task(task)

    def set_error(self, task_id: str, error: str) -> None:
        with self._lock:
            task = self.get_task(task_id)
            if task:
                task.set_error(error)
                self._save_task(task)

    def get_user_tasks(self, user_id: str, limit: int = 20) -> list[Task]:
        tasks = []
        for path in TASK_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("user_id") == user_id:
                    tasks.append(Task.from_dict(data))
            except Exception:
                continue
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    def _save_task(self, task: Task) -> None:
        path = TASK_DIR / f"{task.task_id}.json"
        path.write_text(
            json.dumps(task.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def cleanup_old_tasks(self, days: int = 7) -> int:
        cleaned = 0
        cutoff = datetime.now().timestamp() - (days * 86400)
        for path in TASK_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                created = datetime.fromisoformat(data.get("created_at", "")).timestamp()
                if created < cutoff:
                    path.unlink()
                    cleaned += 1
            except Exception:
                pass
        return cleaned


class AsyncTaskRunner:
    def __init__(self, tracker: TaskTracker) -> None:
        self.tracker = tracker

    def run_in_background(
        self,
        task_id: str,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        def wrapper() -> None:
            try:
                self.tracker.set_status(task_id, "running")
                result = func(task_id, *args, **kwargs)
                self.tracker.set_result(task_id, result or {})
            except Exception as e:
                self.tracker.set_error(task_id, str(e))

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
