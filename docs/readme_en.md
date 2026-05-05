# NovelOps

[中文版本 (Chinese)](README.md)

NovelOps is a local creative operations center for Chinese web novel projects. It keeps project configuration, story bibles, outlines, corpus chapters, generated artifacts, review reports, revision queues, and a local Web dashboard in one repository. You can operate it through the CLI, the Web UI, the HTTP API, or Chinese natural-language requests.

The current version has no no-LLM/mock fallback. Natural-language parsing, reviewing, and generation all require live LLM access. By default, NovelOps uses official DeepSeek for structured tasks and Claude via RightCode for long-form drafting and revisions.

## Current Project

The repository includes a main/sample project:

```text
projects/life_balance
```

It currently contains:

- `corpus/volume_01/`: first-volume corpus, currently 50 chapters.
- `generation/chapter_051/`: generated artifacts for chapter 51.
- `reviews/`: chapter review JSON reports.
- `reviews/revision_queue/`: open revision items.
- `bible/`, `outlines/`, `state/`: worldbuilding, outlines, and continuity state.

The default project is read from `config/novelops.json`; if missing, NovelOps falls back to `config/novelops.example.json`, then to `life_balance`.

## Installation

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

If your system Python disallows global installs, use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## LLM Configuration

The active model configuration file is:

```text
config/models.json
```

Default routing:

| Stage | Provider | Model | Purpose |
| --- | --- | --- | --- |
| `assistant` | Official DeepSeek | `deepseek-chat` | Chinese natural-language command parsing |
| `planner` | Official DeepSeek | `deepseek-chat` | Chapter planning |
| `chapter_intent` | Official DeepSeek | `deepseek-chat` | Chapter intent refinement |
| `scene_chain` | Official DeepSeek | `deepseek-chat` | Scene-chain design |
| `reviewer` | Official DeepSeek | `deepseek-chat` | Chapter review |
| `scout` | Official DeepSeek | `deepseek-chat` | Topic/intelligence scouting |
| `draft_v1` | Claude via RightCode | `claude-sonnet-4-6` | First draft |
| `commercial_rewrite` | Claude via RightCode | `claude-sonnet-4-6` | Commercial rewrite |
| `humanize` | Claude via RightCode | `claude-sonnet-4-6` | Humanized polish |
| `revision` | Claude via RightCode | `claude-sonnet-4-6` | Post-review revision |

Provide both keys in your shell:

```bash
export DEEPSEEK_API_KEY="your DeepSeek key"
export RIGHTCODE_API_KEY="your RightCode key"
```

For persistent zsh configuration:

```bash
echo 'export DEEPSEEK_API_KEY="your DeepSeek key"' >> ~/.zshrc
echo 'export RIGHTCODE_API_KEY="your RightCode key"' >> ~/.zshrc
source ~/.zshrc
```

Verify that NovelOps reads the expected routing:

```bash
python3 - <<'PY'
from novelops.llm import settings_for_stage
for stage in ["assistant", "draft_v1", "reviewer", "revision"]:
    s = settings_for_stage(stage)
    print(stage, s.model, s.base_url, s.api_key_env)
PY
```

To change the RightCode relay URL or Claude model, edit the `generator` section in `config/models.json`. To change DeepSeek models, edit the DeepSeek-backed sections such as `assistant`, `planner`, and `reviewer`.

## Natural-Language Interface

You can operate NovelOps directly in Chinese:

```bash
python3 -m novelops.cli ask "查看 life_balance 状态"
python3 -m novelops.cli ask "检查 life_balance 现在能不能继续生成下一章"
python3 -m novelops.cli ask "解释 life_balance 第51章为什么审稿没过"
python3 -m novelops.cli ask "显示 life_balance 修订队列"
python3 -m novelops.cli ask "重建 life_balance 索引"
```

Use `--project` to provide the default project:

```bash
python3 -m novelops.cli --project life_balance ask "我现在下一步该做什么"
```

Actions that create a project or write large generated artifacts require explicit confirmation. By default, they only preview:

```bash
python3 -m novelops.cli --project life_balance ask "给当前项目生成下一章"
```

Confirm execution:

```bash
python3 -m novelops.cli --project life_balance ask "给当前项目生成下一章" --yes
```

The natural-language entry point will not execute destructive or high-risk requests such as deleting files, overwriting the corpus, writing directly to `publish/ready`, batch review, or batch publish checks.

## Common CLI Commands

Show default project status:

```bash
python3 -m novelops.cli status
```

Check project folders and required files:

```bash
python3 -m novelops.cli --project life_balance check
```

Rebuild the SQLite index:

```bash
python3 -m novelops.cli index
python3 -m novelops.cli index --project life_balance
```

Plan a chapter:

```bash
python3 -m novelops.cli --project life_balance plan-next 51
```

Generate a chapter:

```bash
python3 -m novelops.cli --project life_balance generate 51
```

Review a chapter:

```bash
python3 -m novelops.cli --project life_balance review-chapter 51
```

Run a pre-publish check:

```bash
python3 -m novelops.cli --project life_balance publish-check 1 50
```

`review-chapter` or `publish-check` may return exit code `2` when content fails the configured threshold. That means revision is required; it is not a program crash.

## Web Dashboard

Start the local dashboard:

```bash
python3 -m novelops.cli serve --host 127.0.0.1 --port 8787
```

Open:

```text
http://127.0.0.1:8787
```

The Web UI includes:

- Project list.
- Project detail.
- Chapter detail.
- Open revision queue.
- A Chinese natural-language input box at the top.

The Web natural-language input calls the same `/api/ask` endpoint. Requests that require confirmation first show the planned action and then require pressing the confirmation button.

## API

Natural-language API:

```http
POST /api/ask
Content-Type: application/json

{
  "message": "解释第51章为什么审稿没过",
  "project": "life_balance",
  "execute": false
}
```

For confirmed actions, send `execute: true`:

```json
{
  "message": "给当前项目生成下一章",
  "project": "life_balance",
  "execute": true
}
```

## Creating a New Project

```bash
python3 -m novelops.cli init-project demo_xianxia --name "Test Xianxia" --genre "Xianxia Progression"
python3 -m novelops.cli --project demo_xianxia check
python3 -m novelops.cli index --project demo_xianxia
```

You can also use the natural-language interface, which will require confirmation:

```bash
python3 -m novelops.cli ask "帮我创建一个仙侠项目，项目ID demo_xianxia，名字叫测试仙侠，题材仙侠升级流"
```

## Project Directory Layout

`init-project` creates:

```text
projects/<id>/
├── project.json
├── bible/
├── outlines/
├── state/
├── corpus/
│   └── volume_01/
├── generation/
├── reviews/
│   └── revision_queue/
├── publish/
│   └── ready/
└── intelligence/
    ├── raw/manual_notes/
    ├── processed/
    └── reports/
```

Important files and folders:

- `project.json`: project ID, name, genre, target platform, chapter length, review thresholds, current volume, planning strategy, and rubric.
- `bible/`: worldbuilding, characters, style, safety rules, and production specs.
- `outlines/`: full outline, volume outline, and chapter queue.
- `state/`: continuity index, timeline, character state, and chapter summaries.
- `corpus/`: completed chapter text.
- `generation/chapter_XXX/`: plans, scene chains, drafts, rewrites, review gates, and revisions.
- `reviews/`: review JSON reports and revision queue items.
- `runtime/novelops.sqlite3`: SQLite index database.

Markdown/JSON source files remain the source of truth. SQLite is only an index for querying and dashboard display.

## Typical Workflow

1. Check status:

```bash
python3 -m novelops.cli ask "查看 life_balance 状态"
```

2. Check whether the project can continue:

```bash
python3 -m novelops.cli ask "检查 life_balance 现在能不能继续生成下一章"
```

3. Plan the next chapter:

```bash
python3 -m novelops.cli --project life_balance plan-next 51
```

4. Generate the next chapter:

```bash
python3 -m novelops.cli --project life_balance ask "给当前项目生成下一章" --yes
```

5. Explain a failed review:

```bash
python3 -m novelops.cli --project life_balance ask "解释第51章为什么审稿没过"
```

6. Show the revision queue:

```bash
python3 -m novelops.cli --project life_balance ask "显示修订队列"
```

## Tests

Run the base test suite:

```bash
python3 -m unittest discover -s tests
```

If using a virtual environment:

```bash
.venv/bin/python -m unittest discover -s tests
```

## Notes

- NovelOps requires live LLM access. Missing `DEEPSEEK_API_KEY` or `RIGHTCODE_API_KEY` will fail fast.
- Do not commit real API keys into repository files.
- The natural-language layer has safety boundaries: high-risk writes require confirmation, and deletion, corpus overwrite, and automatic publishing are blocked.
- The `publish/ready` directory is not written by the natural-language entry point.
