from __future__ import annotations

from typing import Any

from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer

from .config import get_session_secret


SESSION_COOKIE_NAME = "novelops_session"
SESSION_MAX_AGE = 30 * 24 * 3600  # 30 天


def get_serializer() -> URLSafeTimedSerializer:
    """获取 session 序列化器"""
    return URLSafeTimedSerializer(get_session_secret())


def get_session(request: Request) -> dict[str, Any]:
    """从请求中获取 session 数据"""
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        return {}

    try:
        serializer = get_serializer()
        data = serializer.loads(cookie, max_age=SESSION_MAX_AGE)
        return data if isinstance(data, dict) else {}
    except (BadSignature, Exception):
        return {}


def set_session(response: Response, data: dict[str, Any]) -> None:
    """设置 session 数据到响应"""
    serializer = get_serializer()
    cookie_value = serializer.dumps(data)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=cookie_value,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )


def clear_session(response: Response) -> None:
    """清除 session"""
    response.delete_cookie(SESSION_COOKIE_NAME)


def get_current_project(request: Request) -> str | None:
    """获取当前用户绑定的项目 ID"""
    session = get_session(request)
    return session.get("project_id")
