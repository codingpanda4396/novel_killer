# NovelOps

[English Version](README_EN.md)

NovelOps 是一个面向中文网文项目的本地创作中台。它把项目设定、故事 bible、章节大纲、正文语料、章节生成产物、审稿报告、修订队列和 Web 看板组织到同一个工程里，让你可以用 CLI、网页或中文自然语言请求来推进连载生产。

当前版本已经取消 no-LLM/mock fallback：所有自然语言解析、审稿和生成都要求真实 LLM 可用。默认配置使用 DeepSeek 官方接口处理结构化任务，使用 Claude via RightCode 处理中长篇正文写作和修订。

## 当前项目状态

仓库内已有示例/主项目：

```text
projects/life_balance
```

它目前包含：

- `corpus/volume_01/`：第一卷正文语料，当前 50 章。
- `generation/chapter_051/`：第 51 章生成过程产物。
- `reviews/`：章节审稿 JSON。
- `reviews/revision_queue/`：未过审章节的修订队列。
- `bible/`、`outlines/`、`state/`：世界观、章节规划和连续性状态。

默认项目来自 `configs/novelops.json`；如果该文件不存在，会读取 `configs/novelops.example.json`，再缺失才回退到 `life_balance`。

## 安装

建议先安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

如果系统 Python 不允许全局安装，可以使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## LLM 配置

生效配置文件是：

```text
configs/models.json
```

默认分工：

| Stage | Provider | Model | 用途 |
| --- | --- | --- | --- |
| `assistant` | DeepSeek 官方 | `deepseek-chat` | 中文自然语言请求解析 |
| `planner` | DeepSeek 官方 | `deepseek-chat` | 章节规划 |
| `chapter_intent` | DeepSeek 官方 | `deepseek-chat` | 章节意图细化 |
| `scene_chain` | DeepSeek 官方 | `deepseek-chat` | 分场设计 |
| `reviewer` | DeepSeek 官方 | `deepseek-chat` | 章节审稿 |
| `scout` | DeepSeek 官方 | `deepseek-chat` | 选题/情报分析 |
| `draft_v1` | Claude via RightCode | `claude-sonnet-4-6` | 初稿 |
| `commercial_rewrite` | Claude via RightCode | `claude-sonnet-4-6` | 商业化改稿 |
| `humanize` | Claude via RightCode | `claude-sonnet-4-6` | 降低机械感、润色 |
| `revision` | Claude via RightCode | `claude-sonnet-4-6` | 审稿后修订 |

需要在当前 shell 中提供两个环境变量：

```bash
export DEEPSEEK_API_KEY="你的 DeepSeek key"
export RIGHTCODE_API_KEY="你的 RightCode key"
```

长期生效可以写入 `~/.zshrc`：

```bash
echo 'export DEEPSEEK_API_KEY="你的 DeepSeek key"' >> ~/.zshrc
echo 'export RIGHTCODE_API_KEY="你的 RightCode key"' >> ~/.zshrc
source ~/.zshrc
```

检查配置是否被正确读取：

```bash
python3 - <<'PY'
from novelops.llm import settings_for_stage
for stage in ["assistant", "draft_v1", "reviewer", "revision"]:
    s = settings_for_stage(stage)
    print(stage, s.model, s.base_url, s.api_key_env)
PY
```

如果要改 RightCode 中转地址或 Claude 模型名，编辑 `configs/models.json` 的 `generator` 段；如果要改 DeepSeek 模型，编辑 `assistant`、`planner`、`reviewer` 等 DeepSeek 段。

## 自然语言入口

你可以直接用中文请求操作 NovelOps：

```bash
python3 -m novelops.cli ask "查看 life_balance 状态"
python3 -m novelops.cli ask "检查 life_balance 现在能不能继续生成下一章"
python3 -m novelops.cli ask "解释 life_balance 第51章为什么审稿没过"
python3 -m novelops.cli ask "显示 life_balance 修订队列"
python3 -m novelops.cli ask "重建 life_balance 索引"
```

`--project` 可以指定默认项目：

```bash
python3 -m novelops.cli --project life_balance ask "我现在下一步该做什么"
```

会写入大量产物或新增项目的操作需要显式确认。默认只预览：

```bash
python3 -m novelops.cli --project life_balance ask "给当前项目生成下一章"
```

确认执行：

```bash
python3 -m novelops.cli --project life_balance ask "给当前项目生成下一章" --yes
```

自然语言入口不会执行删除文件、覆盖 corpus、直接发布到 `publish/ready`、批量审稿或批量发布检查这类高风险请求。

## 常用 CLI

查看默认项目状态：

```bash
python3 -m novelops.cli status
```

检查项目目录和关键文件：

```bash
python3 -m novelops.cli --project life_balance check
```

重建 SQLite 索引：

```bash
python3 -m novelops.cli index
python3 -m novelops.cli index --project life_balance
```

规划下一章：

```bash
python3 -m novelops.cli --project life_balance plan-next 51
```

生成章节：

```bash
python3 -m novelops.cli --project life_balance generate 51
```

审稿章节：

```bash
python3 -m novelops.cli --project life_balance review-chapter 51
```

发布前检查一段章节：

```bash
python3 -m novelops.cli --project life_balance publish-check 1 50
```

`review-chapter` 或 `publish-check` 返回退出码 `2` 表示内容未过阈值，需要修订；这不是程序崩溃。

## Web 看板

启动本地看板：

```bash
python3 -m novelops.cli serve --host 127.0.0.1 --port 8787
```

打开：

```text
http://127.0.0.1:8787
```

Web 页面包含：

- 项目列表。
- 项目详情。
- 章节详情。
- open 修订队列。
- 顶部中文自然语言输入框。

Web 自然语言输入框会调用同一个 `/api/ask`。需要确认的操作会先显示将执行的动作，并要求点击“确认执行”。

## API

自然语言 API：

```http
POST /api/ask
Content-Type: application/json

{
  "message": "解释第51章为什么审稿没过",
  "project": "life_balance",
  "execute": false
}
```

需要确认的请求把 `execute` 设为 `true` 再提交：

```json
{
  "message": "给当前项目生成下一章",
  "project": "life_balance",
  "execute": true
}
```

## 创建新项目

```bash
python3 -m novelops.cli init-project demo_xianxia --name 测试仙侠 --genre 仙侠升级流
python3 -m novelops.cli --project demo_xianxia check
python3 -m novelops.cli index --project demo_xianxia
```

也可以走自然语言入口，但会要求确认：

```bash
python3 -m novelops.cli ask "帮我创建一个仙侠项目，项目ID demo_xianxia，名字叫测试仙侠，题材仙侠升级流"
```

## 项目目录结构

`init-project` 会创建：

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

关键文件说明：

- `project.json`：项目 ID、项目名、题材、目标平台、章节长度、审稿阈值、当前卷、规划策略和 rubric。
- `bible/`：世界观、角色、风格、安全规则、生产规范。
- `outlines/`：总纲、卷纲、章节队列。
- `state/`：连续性索引、时间线、角色状态、章节摘要。
- `corpus/`：已完成正文语料。
- `generation/chapter_XXX/`：规划、分场、初稿、改稿、审稿 gate、修订稿等生成产物。
- `reviews/`：章节审稿 JSON 和修订队列。
- `runtime/novelops.sqlite3`：SQLite 索引数据库。

正文、bible、outlines 和审稿报告仍以 Markdown/JSON 原件为准；SQLite 只做查询索引。

## 典型工作流

1. 确认状态：

```bash
python3 -m novelops.cli ask "查看 life_balance 状态"
```

2. 检查是否可继续：

```bash
python3 -m novelops.cli ask "检查 life_balance 现在能不能继续生成下一章"
```

3. 规划下一章：

```bash
python3 -m novelops.cli --project life_balance plan-next 51
```

4. 生成下一章：

```bash
python3 -m novelops.cli --project life_balance ask "给当前项目生成下一章" --yes
```

5. 查看审稿解释：

```bash
python3 -m novelops.cli --project life_balance ask "解释第51章为什么审稿没过"
```

6. 查看修订队列：

```bash
python3 -m novelops.cli --project life_balance ask "显示修订队列"
```

## 测试

基础测试：

```bash
python3 -m unittest discover -s tests
```

如果你使用虚拟环境：

```bash
.venv/bin/python -m unittest discover -s tests
```

## 注意事项

- 当前系统要求真实 LLM；缺少 `DEEPSEEK_API_KEY` 或 `RIGHTCODE_API_KEY` 时会直接失败。
- 不要把真实 API key 写进仓库文件。
- 自然语言入口有安全边界：高风险写入需要确认，禁止删除、覆盖语料和自动发布。
- 发布目录 `publish/ready` 不会被自然语言入口自动写入。
