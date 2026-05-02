from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .assistant import ask
from .config import validate_invite_code
from .indexer import connect, rebuild_index
from .paths import ROOT
from .session import get_session, set_session, clear_session, get_current_project


templates = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))


class AskRequest(BaseModel):
    message: str
    project: str | None = None
    execute: bool = False


def require_auth(request: Request) -> str:
    """要求用户已登录，返回绑定的项目 ID"""
    project_id = get_current_project(request)
    if not project_id:
        raise HTTPException(status_code=401, detail="未登录")
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

        project_id = invite_info["project"]
        response = RedirectResponse(url="/", status_code=303)
        set_session(response, {"project_id": project_id, "invite_code": code})
        return response

    @app.post("/logout")
    def logout():
        response = RedirectResponse(url="/invite", status_code=303)
        clear_session(response)
        return response

    @app.post("/api/ask")
    def api_ask(request: Request, payload: AskRequest) -> dict:
        project_id = require_auth(request)
        # 忽略前端传来的 project，只使用 session 绑定的项目
        return ask(
            payload.message,
            default_project=project_id,
            execute=payload.execute,
        ).to_dict()

    @app.get("/", response_class=HTMLResponse)
    def workspace(request: Request):
        project_id = get_current_project(request)
        if not project_id:
            return RedirectResponse(url="/invite", status_code=303)

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

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    def project_detail(request: Request, project_id: str) -> HTMLResponse:
        current_project = require_auth(request)
        if project_id != current_project:
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
        current_project = require_auth(request)
        if project_id != current_project:
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
        project_id = require_auth(request)
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
