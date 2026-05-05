from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .assistant import ask
from .chat_session import SessionManager, ChatSession
from .config import validate_invite_code
from .framework_importer import import_framework_project, preview_framework_import
from .indexer import connect, rebuild_index
from .paths import ROOT
from .project import init_project
from .session import get_session, set_session, clear_session, get_current_user
from .task_tracker import TaskTracker, AsyncTaskRunner
from .user import (
    get_user_projects,
    add_user_project,
    get_default_project,
    set_default_project,
    check_project_access,
    has_any_project,
)


templates = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))

session_manager = SessionManager()
task_tracker = TaskTracker()
async_runner = AsyncTaskRunner(task_tracker)


class AskRequest(BaseModel):
    message: str
    project: str | None = None
    execute: bool = False


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    execute: bool = False


class ImportFrameworkRequest(BaseModel):
    project_id: str
    framework_markdown: str
    name: str | None = None
    target_platform: str | None = None
    execute: bool = False


def require_user(request: Request) -> str:
    """要求用户已登录，返回user_id"""
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    return user_id


def require_auth(request: Request) -> str:
    """要求用户已登录，返回绑定的项目 ID（已废弃，保留向后兼容）"""
    user_id = require_user(request)
    project_id = get_default_project(user_id)
    if not project_id:
        raise HTTPException(status_code=404, detail="未找到默认项目")
    return project_id


def create_app() -> FastAPI:
    app = FastAPI(title="NovelOps")

    @app.get("/invite", response_class=HTMLResponse)
    def invite_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "invite.html", {"error": None})

    @app.post("/invite")
    def invite_submit(request: Request, code: str = Form(...)):
        invite_info = validate_invite_code(code)
        if not invite_info:
            return templates.TemplateResponse(
                request, "invite.html", {"error": "邀请码无效，请检查后重试"}
            )

        user_id = invite_info["user_id"]
        username = invite_info.get("username", user_id)
        response = RedirectResponse(url="/projects", status_code=303)
        set_session(response, {"user_id": user_id, "username": username, "invite_code": code})

        # 如果是旧格式邀请码（包含_legacy_project），自动关联项目
        if "_legacy_project" in invite_info:
            legacy_project = invite_info["_legacy_project"]
            if not check_project_access(user_id, legacy_project):
                add_user_project(user_id, legacy_project, is_default=True)

        return response

    @app.post("/logout")
    def logout():
        response = RedirectResponse(url="/invite", status_code=303)
        clear_session(response)
        return response

    @app.get("/projects", response_class=HTMLResponse)
    def projects_list(request: Request):
        """项目列表页"""
        user_id = require_user(request)
        projects = get_user_projects(user_id)
        return templates.TemplateResponse(
            request,
            "projects_list.html",
            {"projects": projects}
        )

    @app.get("/projects/new", response_class=HTMLResponse)
    def project_new_form(request: Request):
        """创建项目表单页"""
        require_user(request)
        return templates.TemplateResponse(request, "project_new.html", {"error": None})

    @app.get("/projects/import-framework", response_class=HTMLResponse)
    def import_framework_form(request: Request):
        require_user(request)
        return templates.TemplateResponse(request, "import_framework.html", {"error": None})

    @app.post("/projects/new")
    def project_new_submit(
        request: Request,
        name: str = Form(...),
        genre: str = Form(...),
        target_platform: str = Form("中文网文连载平台")
    ):
        """处理创建项目请求"""
        user_id = require_user(request)

        # 生成项目ID：user_id + 时间戳
        project_id = f"{user_id}_{int(time.time())}"

        try:
            # 创建项目目录和文件
            project_path = init_project(project_id, name, genre, target_platform)

            # 关联用户和项目，设为默认项目
            add_user_project(user_id, project_id, is_default=True)

            # 重建索引
            rebuild_index(project_id)

            # 重定向到项目工作台
            return RedirectResponse(url=f"/projects/{project_id}/workspace", status_code=303)
        except Exception as e:
            return templates.TemplateResponse(
                request,
                "project_new.html",
                {"error": f"创建项目失败: {str(e)}"}
            )

    @app.post("/api/import-framework")
    def api_import_framework(request: Request, payload: ImportFrameworkRequest) -> dict:
        user_id = require_user(request)
        try:
            if payload.execute:
                result = import_framework_project(
                    payload.project_id,
                    payload.framework_markdown,
                    name=payload.name,
                    target_platform=payload.target_platform,
                )
                add_user_project(user_id, payload.project_id, is_default=True)
                rebuild_index(payload.project_id)
                return {"status": "created", "redirect_url": f"/projects/{payload.project_id}", **result.summary()}
            preview = preview_framework_import(
                payload.project_id,
                payload.framework_markdown,
                name=payload.name,
                target_platform=payload.target_platform,
            )
            return {"status": "preview", **preview.summary()}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/projects/{project_id}/set-default")
    def project_set_default(request: Request, project_id: str):
        """设置默认项目"""
        user_id = require_user(request)
        if not check_project_access(user_id, project_id):
            raise HTTPException(status_code=403, detail="无权访问此项目")
        set_default_project(user_id, project_id)
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def workspace(request: Request):
        user_id = get_current_user(request)
        if not user_id:
            return RedirectResponse(url="/invite", status_code=303)

        # 如果用户没有项目，重定向到项目列表
        if not has_any_project(user_id):
            return RedirectResponse(url="/projects", status_code=303)

        project_id = get_default_project(user_id)
        if not project_id:
            return RedirectResponse(url="/projects", status_code=303)

        return RedirectResponse(url=f"/projects/{project_id}/workspace", status_code=303)

    @app.get("/projects/{project_id}/workspace", response_class=HTMLResponse)
    def project_workspace(request: Request, project_id: str):
        """项目工作台"""
        user_id = require_user(request)
        if not check_project_access(user_id, project_id):
            raise HTTPException(status_code=403, detail="无权访问此项目")

        with connect() as conn:
            project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not project:
                raise HTTPException(status_code=404, detail="项目不存在")

            chapter_count = conn.execute(
                "SELECT COUNT(DISTINCT chapter) FROM chapters WHERE project_id = ?",
                (project_id,)
            ).fetchone()[0]

            latest_review = conn.execute(
                "SELECT score FROM reviews WHERE project_id = ? ORDER BY chapter DESC LIMIT 1",
                (project_id,)
            ).fetchone()

            open_queue = conn.execute(
                "SELECT COUNT(*) FROM revision_queue WHERE project_id = ? AND status = 'open'",
                (project_id,)
            ).fetchone()[0]

        return templates.TemplateResponse(
            request,
            "workspace.html",
            {
                "project": project,
                "chapter_count": chapter_count,
                "next_chapter": project["next_chapter"] or 1,
                "latest_review_score": latest_review[0] if latest_review else None,
                "open_queue": open_queue,
            },
        )

    @app.post("/api/ask")
    def api_ask(request: Request, payload: AskRequest) -> dict:
        user_id = require_user(request)
        project_id = get_default_project(user_id)
        if not project_id:
            raise HTTPException(status_code=404, detail="未找到默认项目")
        return ask(
            payload.message,
            default_project=project_id,
            execute=payload.execute,
        ).to_dict()

    @app.post("/api/chat")
    def api_chat(request: Request, payload: ChatRequest) -> dict:
        user_id = require_user(request)
        message = payload.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="消息不能为空")

        session_id = payload.session_id
        if session_id:
            session = session_manager.get_session(session_id)
            if not session or session.user_id != user_id:
                session = session_manager.create_session(user_id, get_default_project(user_id))
        else:
            session = session_manager.create_session(user_id, get_default_project(user_id))

        session.add_message("user", message)
        response = ask(message, default_project=session.project_id, execute=payload.execute)
        session.add_message("assistant", response.message, {
            "intent": response.intent.name,
            "requires_confirmation": response.requires_confirmation,
            "actions": response.actions,
        })
        session_manager.save_session(session)

        return {
            "session_id": session.session_id,
            "message": response.message,
            "intent": response.intent.name,
            "requires_confirmation": response.requires_confirmation,
            "actions": response.actions,
            "result": response.result,
            "errors": response.errors,
        }

    @app.post("/api/chat/execute")
    def api_chat_execute(request: Request, payload: dict) -> dict:
        user_id = require_user(request)
        session_id = payload.get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required")

        session = session_manager.get_session(session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=404, detail="会话不存在")

        last_user_msg = next((m for m in reversed(session.messages) if m.role == "user"), None)
        if not last_user_msg:
            raise HTTPException(status_code=400, detail="没有待执行的操作")

        response = ask(last_user_msg.content, default_project=session.project_id, execute=True)

        long_tasks = {"generate", "pipeline_run", "radar_collect", "radar_analyze", "prepare_project"}
        if response.intent.name in long_tasks:
            task_id = task_tracker.create_task(
                user_id=user_id,
                session_id=session.session_id,
                intent=response.intent.name,
                project_id=session.project_id,
            )
            session.add_message("assistant", f"任务已启动，任务ID: {task_id}", {"task_id": task_id})
            session_manager.save_session(session)
            return {
                "session_id": session.session_id,
                "task_id": task_id,
                "message": "任务已启动，请通过/api/stream/{task_id}查看进度",
            }

        session.add_message("assistant", response.message, {"result": response.result})
        session_manager.save_session(session)

        return {
            "session_id": session.session_id,
            "message": response.message,
            "result": response.result,
            "errors": response.errors,
        }

    @app.get("/api/stream/{task_id}")
    async def stream_task_progress(task_id: str, request: Request):
        user_id = require_user(request)
        task = task_tracker.get_task(task_id)
        if not task or task.user_id != user_id:
            raise HTTPException(status_code=404, detail="任务不存在")

        async def event_generator():
            while True:
                task = task_tracker.get_task(task_id)
                if not task:
                    break
                yield f"data: {json.dumps(task.to_dict(), ensure_ascii=False)}\n\n"
                if task.status in ["completed", "failed"]:
                    break
                await asyncio.sleep(1)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    @app.get("/api/chat/history/{session_id}")
    def get_chat_history(session_id: str, request: Request) -> dict:
        user_id = require_user(request)
        session = session_manager.get_session(session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=404, detail="会话不存在")
        return session.to_dict()

    @app.get("/api/chat/sessions")
    def get_user_chat_sessions(request: Request) -> dict:
        user_id = require_user(request)
        sessions = session_manager.get_user_sessions(user_id)
        return {"sessions": [s.to_dict() for s in sessions]}

    @app.get("/api/tasks")
    def get_user_tasks(request: Request) -> dict:
        user_id = require_user(request)
        tasks = task_tracker.get_user_tasks(user_id)
        return {"tasks": [t.to_dict() for t in tasks]}

    @app.get("/chat", response_class=HTMLResponse)
    def chat_page(request: Request):
        user_id = get_current_user(request)
        if not user_id:
            return RedirectResponse(url="/invite", status_code=303)
        if not has_any_project(user_id):
            return RedirectResponse(url="/projects", status_code=303)
        project_id = get_default_project(user_id)
        if not project_id:
            return RedirectResponse(url="/projects", status_code=303)
        return templates.TemplateResponse(request, "chat.html", {"project_id": project_id})

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    def project_detail(request: Request, project_id: str) -> HTMLResponse:
        user_id = require_user(request)
        if not check_project_access(user_id, project_id):
            raise HTTPException(status_code=403, detail="无权访问此项目")

        with connect() as conn:
            project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not project:
                raise HTTPException(status_code=404)
            chapters = conn.execute(
                "SELECT chapter, source_type, title, word_count, status FROM chapters WHERE project_id = ? ORDER BY chapter, source_type",
                (project_id,),
            ).fetchall()
            open_queue = conn.execute("SELECT COUNT(*) AS count FROM revision_queue WHERE project_id = ? AND status = 'open'", (project_id,)).fetchone()
        base = Path(project["path"])
        summaries = []
        for rel in ["bible/00_story_bible.md", "outlines/chapter_queue.md", "state/timeline.md", "state/chapter_summary.md"]:
            path = base / rel
            summaries.append({"name": rel, "exists": path.is_file(), "excerpt": _excerpt(path)})
        return templates.TemplateResponse(
            request,
            "project_detail.html",
            {"project": project, "chapters": chapters, "summaries": summaries, "open_queue": open_queue["count"]},
        )

    @app.get("/projects/{project_id}/chapters/{chapter}", response_class=HTMLResponse)
    def chapter_detail(request: Request, project_id: str, chapter: int) -> HTMLResponse:
        user_id = require_user(request)
        if not check_project_access(user_id, project_id):
            raise HTTPException(status_code=403, detail="无权访问此项目")

        with connect() as conn:
            project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not project:
                raise HTTPException(status_code=404)
            chapters = conn.execute("SELECT * FROM chapters WHERE project_id = ? AND chapter = ? ORDER BY source_type", (project_id, chapter)).fetchall()
            runs = conn.execute("SELECT * FROM generation_runs WHERE project_id = ? AND chapter = ?", (project_id, chapter)).fetchall()
            reviews = conn.execute("SELECT * FROM reviews WHERE project_id = ? AND chapter = ?", (project_id, chapter)).fetchall()
            queue = conn.execute("SELECT * FROM revision_queue WHERE project_id = ? AND chapter = ?", (project_id, chapter)).fetchall()
        artifacts = []
        for run in runs:
            directory = Path(run["artifact_dir"])
            artifacts.extend(sorted(str(path.relative_to(ROOT)) for path in directory.glob("*") if path.is_file()))
        return templates.TemplateResponse(
            request,
            "chapter_detail.html",
            {"project": project, "chapter": chapter, "chapters": chapters, "runs": runs, "reviews": reviews, "queue": queue, "artifacts": artifacts},
        )

    @app.get("/revision-queue", response_class=HTMLResponse)
    def revision_queue(request: Request) -> HTMLResponse:
        user_id = require_user(request)
        project_id = get_default_project(user_id)
        if not project_id:
            raise HTTPException(status_code=404, detail="未找到默认项目")

        with connect() as conn:
            rows = conn.execute(
                "SELECT * FROM revision_queue WHERE project_id = ? AND status = 'open' ORDER BY chapter",
                (project_id,)
            ).fetchall()
        return templates.TemplateResponse(request, "revision_queue.html", {"items": rows})

    return app


def _excerpt(path: Path, limit: int = 500) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").strip()[:limit]


def ensure_index() -> None:
    rebuild_index()
