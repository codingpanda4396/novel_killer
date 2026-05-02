# NovelOps

[English Version](README_EN.md)

NovelOps 是一个面向中文网文项目的本地创作中台。它把项目设定、章节规划、生成产物、审稿报告和发布候选区组织成统一目录，并用 SQLite 建立只读索引，方便 CLI 自动化和本地 Web 看板查询。

正文、bible、outlines、审稿报告仍以 Markdown/JSON 原件为准；SQLite 只做索引和状态查询。

## 快速开始

```bash
python3 -m unittest discover -s tests
python3 -m novelops.cli status
python3 -m novelops.cli index
python3 -m novelops.cli serve --host 127.0.0.1 --port 8787
```

创建新项目：

```bash
python3 -m novelops.cli init-project demo_xianxia --name 测试仙侠 --genre 仙侠升级流
python3 -m novelops.cli --project demo_xianxia check
python3 -m novelops.cli --project demo_xianxia generate 1 --no-llm
python3 -m novelops.cli index --project demo_xianxia
```

默认项目从 `config/novelops.json` 读取；缺失时使用 `config/novelops.example.json`，再缺失才回退到 `life_balance`。

## 项目目录

`init-project` 会创建标准结构：

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

`project.json` 包含项目名、题材、目标平台、语言、章节长度、审稿阈值、当前卷、规划策略和项目 rubric。评分会读取 `rubric.hook_terms` 与 `rubric.forbidden_terms`，未配置时只使用通用基础评分。

## 常用命令

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

`review-chapter` 返回退出码 `2` 表示章节未过阈值，需要修订；这不是程序错误。

## SQLite 索引

默认数据库为 `runtime/novelops.sqlite3`，可用 `NOVELOPS_DB` 覆盖。第一版通过显式命令刷新：

```bash
python3 -m novelops.cli index
python3 -m novelops.cli index --project life_balance
```

索引表包括 `projects`、`chapters`、`generation_runs`、`reviews`、`revision_queue`。

## Web 看板

安装依赖后启动只读看板：

```bash
python3 -m pip install -r requirements.txt
python3 -m novelops.cli serve --host 127.0.0.1 --port 8787
```

页面包括项目列表、项目详情、章节详情和 open 修订队列。Web 第一版不编辑文件，也不触发生成任务。

## LLM 配置

默认可以无网络运行。真实 LLM 使用 `config/models.json` 或环境变量：

```text
API key:  NOVELOPS_API_KEY -> OPENAI_API_KEY -> API_KEY
Base URL: NOVELOPS_BASE_URL -> OPENAI_BASE_URL -> BASE_URL
Model:    NOVELOPS_MODEL -> OPENAI_MODEL -> MODEL
```

生成产物写入 `projects/<id>/generation/chapter_XXX/`，审稿报告写入 `projects/<id>/reviews/`，发布目录不会自动写入。
