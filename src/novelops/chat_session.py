from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .paths import ROOT

SESSION_DIR = ROOT / "runtime" / "chat_sessions"
SESSION_TIMEOUT = timedelta(minutes=30)


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatSession:
    session_id: str
    user_id: str
    project_id: str | None
    messages: list[ChatMessage] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_message(self, role: str, content: str, metadata: dict | None = None) -> None:
        msg = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {},
        )
        self.messages.append(msg)
        self.last_activity = datetime.now().isoformat()

    def get_recent_messages(self, limit: int = 10) -> list[dict[str, Any]]:
        return [asdict(m) for m in self.messages[-limit:]]

    def update_context(self, key: str, value: Any) -> None:
        self.context[key] = value
        self.last_activity = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatSession:
        messages = [ChatMessage(**m) for m in data.get("messages", [])]
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            project_id=data.get("project_id"),
            messages=messages,
            context=data.get("context", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_activity=data.get("last_activity", datetime.now().isoformat()),
        )


class SessionManager:
    def __init__(self) -> None:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

    def create_session(self, user_id: str, project_id: str | None = None) -> ChatSession:
        session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            project_id=project_id,
        )
        self._save_session(session)
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        path = SESSION_DIR / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            session = ChatSession.from_dict(data)
            last_activity = datetime.fromisoformat(session.last_activity)
            if datetime.now() - last_activity > SESSION_TIMEOUT:
                self.delete_session(session_id)
                return None
            return session
        except Exception:
            return None

    def save_session(self, session: ChatSession) -> None:
        self._save_session(session)

    def _save_session(self, session: ChatSession) -> None:
        path = SESSION_DIR / f"{session.session_id}.json"
        path.write_text(
            json.dumps(session.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def delete_session(self, session_id: str) -> None:
        path = SESSION_DIR / f"{session_id}.json"
        if path.exists():
            path.unlink()

    def get_user_sessions(self, user_id: str) -> list[ChatSession]:
        sessions = []
        for path in SESSION_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("user_id") == user_id:
                    session = ChatSession.from_dict(data)
                    last_activity = datetime.fromisoformat(session.last_activity)
                    if datetime.now() - last_activity <= SESSION_TIMEOUT:
                        sessions.append(session)
            except Exception:
                continue
        return sorted(sessions, key=lambda s: s.last_activity, reverse=True)

    def cleanup_expired_sessions(self) -> int:
        cleaned = 0
        for path in SESSION_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                last_activity = datetime.fromisoformat(data.get("last_activity", ""))
                if datetime.now() - last_activity > SESSION_TIMEOUT:
                    path.unlink()
                    cleaned += 1
            except Exception:
                pass
        return cleaned
