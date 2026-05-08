# NovelOps - 中文网文 CLI 生产流水线

NovelOps 是一个本地 CLI 工具，用于管理中文网文项目的市场情报、故事资产、章节生成、审稿、流水线、实验和记忆索引。当前版本已经取消浏览器工作台和登录入口，推荐通过明确 CLI 子命令完成核心操作；自然语言 `ask` 仅作为辅助入口。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp configs/models.example.json configs/models.json
# 编辑 configs/models.json 填入 LLM 配置
```

源码运行推荐：

```bash
.venv/bin/python -m novelops.cli --help
```

安装为包后也可以使用：

```bash
novelops --help
```

## 最小工作流

```bash
.venv/bin/python -m novelops.cli --project life_balance status --readiness
.venv/bin/python -m novelops.cli --project life_balance plan-next 51
.venv/bin/python -m novelops.cli --project life_balance generate 51
.venv/bin/python -m novelops.cli --project life_balance review-chapter 51
.venv/bin/python -m novelops.cli --project life_balance ask "查看待修订章节"
.venv/bin/python -m novelops.cli --project life_balance pipeline status
```

需要实际推进流水线时：

```bash
.venv/bin/python -m novelops.cli --project life_balance pipeline run
```

## 样例项目 life_balance

仓库包含 `projects/life_balance` 样例项目，可直接用于熟悉 CLI：

```bash
.venv/bin/python -m novelops.cli --project life_balance check
.venv/bin/python -m novelops.cli --project life_balance status --readiness
.venv/bin/python -m novelops.cli --project life_balance ask "查看项目状态"
```

## 常用命令

```bash
# 项目管理
.venv/bin/python -m novelops.cli init-project my_novel --name "我的小说" --genre "都市异能"
.venv/bin/python -m novelops.cli --project my_novel check
.venv/bin/python -m novelops.cli --project my_novel status --readiness
.venv/bin/python -m novelops.cli --project my_novel prepare-project

# 章节生产
.venv/bin/python -m novelops.cli --project my_novel plan-next 1
.venv/bin/python -m novelops.cli --project my_novel generate 1
.venv/bin/python -m novelops.cli --project my_novel review-chapter 1
.venv/bin/python -m novelops.cli --project my_novel review-range 1 10
.venv/bin/python -m novelops.cli --project my_novel publish-check 1 10

# 需求、实验、Radar、记忆
.venv/bin/python -m novelops.cli --project my_novel analyze-demand
.venv/bin/python -m novelops.cli --project my_novel experiment list
.venv/bin/python -m novelops.cli --project my_novel scout
.venv/bin/python -m novelops.cli --project my_novel memory-index
python3 -m novelops.radar collect-web --source fanqie --dry-run
```

## 配置

应用配置位于 `configs/novelops.json`，示例文件为 `configs/novelops.example.json`：

```json
{
  "default_project": "life_balance",
  "db_path": "runtime/novelops.sqlite3",
  "require_manual_publish_confirmation": true
}
```

模型配置位于 `configs/models.json`，示例文件为 `configs/models.example.json`。

## 目录结构

```text
novel0/
├── configs/
├── runtime/
├── src/novelops/
│   ├── cli.py
│   ├── assistant.py
│   ├── pipeline/
│   ├── radar/
│   ├── desire/
│   ├── readers/
│   └── memory/
├── projects/<id>/
│   ├── project.json
│   ├── market/
│   ├── story/
│   └── production/
└── tests/
```

## 技术栈

Python 3.10+、SQLModel/SQLAlchemy、ChromaDB、OpenAI SDK 兼容接口、LangGraph、Requests/BeautifulSoup/Playwright、pytest。
