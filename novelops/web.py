from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .assistant import ask
from .indexer import connect, rebuild_index
from .paths import ROOT


templates = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))


class AskRequest(BaseModel):
    message: str
    project: str | None = None
    execute: bool = False


def create_app() -> FastAPI:
    app = FastAPI(title="NovelOps")

    @app.post("/api/ask")
    def api_ask(payload: AskRequest) -> dict:
        return ask(
            payload.message,
            default_project=payload.project,
            execute=payload.execute,
        ).to_dict()

    @app.get("/", response_class=HTMLResponse)
    def projects(request: Request) -> HTMLResponse:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT p.*, COUNT(DISTINCT c.chapter) AS chapter_count,
                       (SELECT status FROM generation_runs g WHERE g.project_id = p.id ORDER BY chapter DESC LIMIT 1) AS latest_generation,
                       (SELECT score FROM reviews r WHERE r.project_id = p.id ORDER BY chapter DESC LIMIT 1) AS latest_review_score
                FROM projects p
                LEFT JOIN chapters c ON c.project_id = p.id
                GROUP BY p.id
                ORDER BY p.id
                """
            ).fetchall()
        return templates.TemplateResponse(request, "projects.html", {"projects": rows})

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    def project_detail(request: Request, project_id: str) -> HTMLResponse:
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
        with connect() as conn:
            rows = conn.execute(
                "SELECT * FROM revision_queue WHERE status = 'open' ORDER BY project_id, chapter"
            ).fetchall()
        return templates.TemplateResponse(request, "revision_queue.html", {"items": rows})

    return app


def _excerpt(path: Path, limit: int = 500) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").strip()[:limit]


def ensure_index() -> None:
    rebuild_index()
