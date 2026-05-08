# NovelOps

NovelOps is a local CLI tool for Chinese web novel operations. It keeps project configuration, story bibles, outlines, corpus chapters, generated artifacts, review reports, revision queues, market intelligence, experiments, and memory indexes in one repository.

The browser interface has been removed. Use explicit CLI subcommands for core workflows; the Chinese natural-language `ask` command remains as a helper.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

```bash
cp configs/novelops.example.json configs/novelops.json
cp configs/models.example.json configs/models.json
```

`configs/novelops.json` contains CLI application settings such as `default_project`, `db_path`, and publish confirmation. `configs/models.json` contains LLM routing and API settings.

## Sample Project

The repository includes `projects/life_balance`.

```bash
.venv/bin/python -m novelops.cli --project life_balance status --readiness
.venv/bin/python -m novelops.cli --project life_balance check
.venv/bin/python -m novelops.cli --project life_balance ask "查看项目状态"
```

## Common Workflow

```bash
.venv/bin/python -m novelops.cli --project life_balance plan-next 51
.venv/bin/python -m novelops.cli --project life_balance generate 51
.venv/bin/python -m novelops.cli --project life_balance review-chapter 51
.venv/bin/python -m novelops.cli --project life_balance ask "查看待修订章节"
.venv/bin/python -m novelops.cli --project life_balance pipeline status
```

`review-chapter` and `publish-check` may return exit code `2` when content fails the configured threshold. That means revision is required; it is not a program crash.
