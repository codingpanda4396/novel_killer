# novel0 长期连载小说生产系统

本 repo 用于把《我能看见人生余额开局救下白月光》从已有章节资产，整理为可持续生产的长期连载小说工程。当前目标不是重写旧章节，而是在保护前文连续性的前提下，稳定生产前 8 万字冷启动内容，并为后续长篇连载留下可维护的工作流。

## 我们已经完成了什么

本轮系统初始化已经完成以下工作：

- 将当前目录初始化为 Git repo，当前分支为 `main`。
- 审计现有项目结构，生成 `progress/system_audit.md`。
- 保留原有目录：`bible/`、`chapters/`、`outlines/`、`progress/`、`prompts/`。
- 在 `chapters/` 下建立生产工作区：
  - `chapters/scene_cards/`：章节卡。
  - `chapters/drafts/`：草稿。
  - `chapters/final/`：定稿。
  - `chapters/records/`：审稿、连续性检查、上下文包、记录更新建议。
- 在 `bible/`、`outlines/`、`progress/`、`prompts/` 下补齐长期连载生产所需的骨架文件。
- 建立 `progress/continuity_index.md`，用于保护第 1-30 章已有连续性。
- 更新所有核心 prompt，使后续章节必须先过“上下文、章节卡、草稿、审稿、连续性检查、记录更新”的流程。
- 新增 Python 自动化总工作流：`scripts/novel_workflow.py`。
- 新增模型配置模板：`config/workflow.example.json`。
- 新增 `Makefile`，提供常用命令入口。
- 新增 `.gitignore`，避免提交本地 API 配置和缓存文件。

## 当前目标：前8万字冷启动

- 目标字数：前 8 万字。
- 目标用途：验证稳定、可追踪、可审稿、可续写的生产链路。
- 生产原则：先规划、再章节卡、再草稿、再审稿、再定稿、再更新记录。
- 当前最大风险：已有第 1-30 章包含“过早终局化”内容，后续生产前必须先明确哪些内容作为正式前文承接，哪些内容需要降级为阶段性胜利、误判或局部真相。

## 目录说明

```text
novel0/
├─ bible/              # 长期不轻易变更的故事约束
├─ outlines/           # 全书、分卷、前8万字和章节队列
├─ chapters/
│  ├─ *.md             # 历史正文资产，第1-30章，暂不移动不覆盖
│  ├─ scene_cards/     # 每章写作前的章节卡
│  ├─ drafts/          # 草稿，不直接发布
│  ├─ final/           # 定稿，可发布版本
│  └─ records/         # 上下文包、审稿记录、连续性检查、记录更新建议
├─ progress/           # 当前上下文、连续性、时间线、伏笔、字数、发布记录
├─ prompts/            # 固定生产提示词
├─ scripts/            # Python 自动化工作流
├─ config/             # 模型 API 配置模板和本地配置
└─ Makefile            # 常用命令入口
```

现有根目录下的 `chapters/*.md` 是历史正文资产。新生产内容必须进入 `chapters/scene_cards/`、`chapters/drafts/`、`chapters/final/` 和 `chapters/records/`。

## 关键入口文件

- 故事总约束：`bible/00_story_bible.md`
- 人物约束：`bible/01_characters.md`
- 能力体系：`bible/02_power_system.md`
- 文风规范：`bible/03_style_guide.md`
- 禁止规则：`bible/04_forbidden_rules.md`
- 前 8 万字规划：`outlines/02_cold_start_0_80k.md`
- 章节队列：`outlines/chapter_queue.md`
- 当前上下文：`progress/current_context.md`
- 连续性索引：`progress/continuity_index.md`
- 章节总结：`progress/chapter_summary.md`
- 系统审计：`progress/system_audit.md`

## 模型配置

首次使用先生成本地配置：

```bash
make init-config
```

这会从 `config/workflow.example.json` 复制出：

```text
config/workflow.local.json
```

然后编辑 `config/workflow.local.json`：

- `provider.base_url`：OpenAI-compatible API 地址，例如 `https://api.openai.com/v1`。
- `provider.api_key_env`：API Key 所在环境变量名，例如 `OPENAI_API_KEY`。
- `stages.*.model`：每个阶段使用的模型。

示例策略：

- `build_context`：用较便宜模型整理上下文。
- `scene_card`：用中高质量模型生成章节卡。
- `draft`：用最强写作模型生成正文草稿。
- `review`、`continuity_check`：用稳定、低温度模型审稿和查连续性。
- `rewrite`：用强模型按审稿意见改稿。

配置 API Key：

```bash
export OPENAI_API_KEY=你的APIKey
```

`config/workflow.local.json` 已被 `.gitignore` 忽略，不应提交到仓库。

## 最终使用方法

先检查系统状态：

```bash
make check
make status
```

为某一章创建生产文件：

```bash
make context-pack N=31
make new-chapter N=31 TITLE=章节标题
```

分阶段生成，推荐用于正式生产：

```bash
make run-stage STAGE=build_context
make run-stage STAGE=scene_card N=31 TITLE=章节标题
make run-stage STAGE=draft N=31 TITLE=章节标题
make run-stage STAGE=review N=31 TITLE=章节标题
make run-stage STAGE=continuity_check N=31 TITLE=章节标题
make run-stage STAGE=rewrite N=31 TITLE=章节标题
make run-stage STAGE=update_record N=31 TITLE=章节标题
make run-stage STAGE=next_planner N=31 TITLE=章节标题
```

一键串联，适合流程稳定后使用：

```bash
make run-full N=31 TITLE=章节标题
```

等价 Python 命令：

```bash
python3 scripts/novel_workflow.py check
python3 scripts/novel_workflow.py status
python3 scripts/novel_workflow.py init-config
python3 scripts/novel_workflow.py new-chapter 31 章节标题
python3 scripts/novel_workflow.py context-pack 31
python3 scripts/novel_workflow.py run-stage draft --number 31 --title 章节标题
python3 scripts/novel_workflow.py run-full --number 31 --title 章节标题
```

调试 prompt，不调用模型 API：

```bash
python3 scripts/novel_workflow.py run-stage build_context --print-prompt
python3 scripts/novel_workflow.py run-stage draft --number 31 --title 章节标题 --print-prompt
```

## 每章生产流程

每章必须按以下顺序执行：

1. `build_context`：更新 `progress/current_context.md`。
2. `context-pack`：生成本章上下文包。
3. `new-chapter`：创建章节卡、草稿、审稿记录、连续性检查文件。
4. `scene_card`：生成章节卡，明确前文承接和本章任务。
5. `draft`：只根据章节卡生成草稿。
6. `review`：审稿，检查商业性、人物、节奏、设定。
7. `continuity_check`：检查是否破坏第 1-30 章连续性。
8. `rewrite`：必要时按审稿意见改稿。
9. `update_record`：更新当前上下文、连续性、时间线、字数、发布记录。
10. `next_planner`：规划下一章，不生成正文。

## 连续性保护规则

- 后续所有章节必须承接现有 `chapters/*.md` 和 `progress/chapter_summary.md`。
- 每次生成章节卡前，必须读取 `progress/continuity_index.md`、`progress/current_context.md`、`progress/active_threads.md` 和 `progress/timeline.md`。
- 如果无法确认当前章号、前一章结尾、人物状态、能力阶段或未回收伏笔，禁止进入正文生成。
- 新章节可以制造反转，但不能无证据推翻前文事实。
- 任何新人物、新能力、新组织线索、新协议、新数值变化，都必须在定稿后写回 `progress/continuity_index.md` 或相关进度文件。

## 禁止事项

- 禁止一次生成多章正文。
- 禁止跳过章节卡直接写正文。
- 禁止覆盖历史正文文件。
- 禁止把草稿直接当定稿发布。
- 禁止在没有更新 `progress/current_context.md` 的情况下继续生产下一章。
- 禁止为了后续剧情方便而改写、忽略或覆盖前文连续性。
- 禁止为追求爽点提前清算长期主线。
- 禁止新增未登记的核心设定、能力、反派组织和人物关系转折。

## 日常建议

- 前几章务必分阶段运行，不建议直接使用 `run-full`。
- 每天开始先运行 `make status`，确认当前章节卡、草稿、定稿数量。
- 每天最多推进 1-2 章，优先保证连续性。
- 每章完成后检查 `progress/current_context.md`、`progress/continuity_index.md`、`progress/timeline.md` 是否已更新。
- 如果连续性检查给出高风险冲突，停止生成正文，先修复 outline 或 progress 文件。
