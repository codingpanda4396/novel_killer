# novel0 长篇连载小说自动生成系统

一键控制、批量生成、连续性保护的长篇小说生产系统。

## 系统简介

本系统用于生产长篇连载小说《我能看见人生余额开局救下白月光》，支持：

- **一键批量生成**：指定起始章节和数量，自动连续生产
- **断点续传**：中断后自动从上次位置继续
- **质量检查**：每章生成后自动运行连续性检查
- **连续性保护**：防止新章节与前文矛盾
- **完整流水线**：章节卡 → 草稿 → 审稿 → 连续性检查 → 定稿

## 快速开始

### 1. 配置 API

```bash
make init-config
export OPENAI_API_KEY=你的APIKey
```

编辑 `config/workflow.local.json`，设置 `provider.base_url` 和各阶段模型。

### 2. 一键批量生成

```bash
# 生成第31-40章（10章）
make run-batch START=31 COUNT=10

# 启用质量检查
make run-batch START=31 COUNT=10 CHECK=1

# 断点续传（中断后从上次位置继续）
make run-batch START=31 COUNT=10 RESUME=1

# 测试模式（不调用API，验证流程）
make run-batch START=31 COUNT=10 DRY_RUN=1
```

### 3. 单章生成

```bash
make run-full N=31 TITLE=章节标题
```

## 命令一览

| 命令 | 说明 |
|------|------|
| `make check` | 检查系统文件完整性 |
| `make status` | 查看当前生产状态 |
| `make init-config` | 初始化 API 配置 |
| `make run-batch START=31 COUNT=10` | **一键批量生成** |
| `make run-full N=31 TITLE=标题` | 单章完整生成 |
| `make run-stage STAGE=draft N=31 TITLE=标题` | 运行单个阶段 |
| `make new-chapter N=31 TITLE=标题` | 仅创建章节文件骨架 |
| `make context-pack N=31` | 仅生成上下文包 |

## 批量生成参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `START` | 是 | 起始章节号 |
| `COUNT` | 是 | 生成章节数量 |
| `CHECK` | 否 | 启用质量检查（`CHECK=1`） |
| `RESUME` | 否 | 断点续传（`RESUME=1`） |
| `DRY_RUN` | 否 | 测试模式（`DRY_RUN=1`） |

## 目录结构

```text
novel0/
├── bible/                  # 故事约束（世界观、人物、能力、文风）
├── outlines/               # 大纲、章节队列、修复方案
│   ├── 04_VOLUME_OUTLINE.md        # 六卷大纲
│   ├── chapter_queue.md            # 章节队列（第31-60章已规划）
│   └── volume_01_repair_plan.md    # 第一卷修复方案
├── chapters/
│   ├── *.md                # 第1-30章历史正文
│   ├── scene_cards/        # 章节卡
│   ├── drafts/             # 草稿
│   ├── final/              # 定稿
│   └── records/            # 审稿记录、连续性检查、上下文包
├── progress/               # 进度追踪
│   ├── current_context.md          # 当前上下文
│   ├── chapter_summary.md          # 章节总结
│   ├── continuity_index.md         # 连续性索引
│   ├── open_threads.md             # 未回收伏笔
│   ├── character_state.md          # 角色状态
│   └── batch_progress.json         # 批量生成进度（自动维护）
├── prompts/                # LLM 提示词模板（9个阶段）
├── scripts/
│   └── novel_workflow.py   # 核心自动化脚本
├── config/
│   ├── workflow.example.json       # 配置模板
│   └── workflow.local.json         # 本地配置（gitignored）
└── Makefile                # 命令入口
```

## 每章生产流水线

每章自动经过以下 7 个阶段：

1. **build_context**：更新当前上下文
2. **scene_card**：生成章节卡（前文承接、本章任务、禁止事项）
3. **draft**：根据章节卡生成草稿（2000-2500字）
4. **review**：审稿（商业性、人物、节奏、设定检查）
5. **continuity_check**：连续性检查（是否与前文矛盾）
6. **update_record**：更新进度文件（时间线、字数、伏笔等）
7. **next_planner**：规划下一章（仅入队列，不生成正文）

## 当前状态

- **第1-30章**：已完成（已通过降级方案修复终局化问题）
- **第31-60章**：已规划，可通过 `make run-batch START=31 COUNT=30` 生成
- **故事结构**：6卷320-360章，约70-80万字

## 故事简介

大学生陈默获得"人生余额可视"能力，能看见每个人头顶的寿命、财运、情缘等倒计时。他救下只剩3分钟寿命的林见鹿，卷入一个名为"天平会"的神秘组织，发现这个组织正在交易和收割人们的人生余额。陈默必须在保护所爱之人的同时，找到推翻这个系统的方法。

## 关键入口文件

| 类别 | 文件 |
|------|------|
| 故事总约束 | `bible/00_story_bible.md` |
| 人物设定 | `bible/01_characters.md` |
| 能力体系 | `bible/02_power_system.md` |
| 六卷大纲 | `outlines/04_VOLUME_OUTLINE.md` |
| 章节队列 | `outlines/chapter_queue.md` |
| 当前上下文 | `progress/current_context.md` |
| 章节总结 | `progress/chapter_summary.md` |
| 伏笔清单 | `progress/open_threads.md` |
| 角色状态 | `progress/character_state.md` |
