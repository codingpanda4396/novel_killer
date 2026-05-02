# NovelOps

[中文版本 (Chinese)](README.md)

NovelOps is a local creative operation center for Chinese web novel projects. It organizes project settings, chapter planning, generated content, review reports, and publishing candidates into a unified directory structure, with SQLite providing read-only indexing for CLI automation and local web dashboard queries.

The original texts, bible, outlines, and review reports remain in Markdown/JSON format; SQLite is used only for indexing and status queries.

## Quick Start

```bash
python3 -m unittest discover -s tests
python3 -m novelops.cli status
python3 -m novelops.cli index
python3 -m novelops.cli serve --host 127.0.0.1 --port 8787
```

Create a new project:

```bash
python3 -m novelops.cli init-project demo_xianxia --name "Test Xianxia" --genre "Xianxia Progression"
python3 -m novelops.cli --project demo_xianxia check
python3 -m novelops.cli --project demo_xianxia generate 1 --no-llm
python3 -m novelops.cli index --project demo_xianxia
```

The default project is read from `config/novelops.json`; falls back to `config/novelops.example.json` if missing, then to `life_balance`.

## Project Directory

`init-project` creates a standard structure:

```text
projects/<id>/
├── project.json
├── bible/
├── outlines/
├── state/
├── corpus/volume_01/
├── generation/
├── reviews/
├── publish/ready/
└── intelligence/
```

`project.json` contains project name, genre, target platform, language, chapter length, review thresholds, current volume, planning strategy, and project rubric. Scoring uses `rubric.hook_terms` and `rubric.forbidden_terms`; falls back to basic scoring when not configured.

## Common Commands

```bash
python3 -m novelops.cli init-project <project_id> --name <name> --genre <genre>
python3 -m novelops.cli --project <project_id> check
python3 -m novelops.cli --project <project_id> status
python3 -m novelops.cli --project <project_id> plan-next 1
python3 -m novelops.cli --project <project_id> generate 1 --no-llm
python3 -m novelops.cli --project <project_id> review-chapter 1 --no-llm
python3 -m novelops.cli --project <project_id> publish-check 1 10
python3 -m novelops.cli index --project <project_id>
python3 -m novelops.cli serve --host 127.0.0.1 --port 8787
```

`review-chapter` returns exit code `2` if the chapter fails to meet the threshold, indicating revision is needed (this is not a program error).

## SQLite Index

Default database is `runtime/novelops.sqlite3`, configurable via `NOVELOPS_DB`. Refresh manually with:

```bash
python3 -m novelops.cli index
python3 -m novelops.cli index --project life_balance
```

Indexed tables include `projects`, `chapters`, `generation_runs`, `reviews`, `revision_queue`.

## Web Dashboard

Install dependencies and launch the read-only dashboard:

```bash
python3 -m pip install -r requirements.txt
python3 -m novelops.cli serve --host 127.0.0.1 --port 8787
```

Pages include project list, project details, chapter details, and open revision queue. The initial web version does not edit files or trigger generation tasks.

## LLM Configuration

Runs offline by default. For real LLM usage, configure via `config/models.json` or environment variables:

```text
API key:  NOVELOPS_API_KEY -> OPENAI_API_KEY -> API_KEY
Base URL: NOVELOPS_BASE_URL -> OPENAI_BASE_URL -> BASE_URL
Model:    NOVELOPS_MODEL -> OPENAI_MODEL -> MODEL
```

Generated content is written to `projects/<id>/generation/chapter_XXX/`, review reports to `projects/<id>/reviews/`, and the publish directory is not automatically written to.
