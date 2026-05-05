# NovelOps v2 详细开发流程

> 项目背景：当前 `novel0` 已完成第一卷 50 章、约 12 万字，并已有 `bible/`、`outlines/`、`chapters/`、`progress/`、`prompts/`、`scripts/novel_workflow.py`、`Makefile` 等基础设施。  
> 本文档目标：在不推翻现有系统的前提下，用 2 天时间把系统升级为更成熟的 **NovelOps v2：自动选题情报 + 多阶段正文生成 + 自动审稿门禁**。

---

## 0. 本阶段目标

### 0.1 不是做什么

本阶段不要追求：

- 完全无人值守写书；
- 全自动发布番茄；
- 重构整个 repo；
- 一次性把所有 Agent 做完美；
- 做复杂前端 UI；
- 做数据库、后台服务、SaaS 化。

### 0.2 要做什么

本阶段只做一件事：

> 把现有小说生产系统升级成一个可运行、可审稿、可拒绝发布、可持续改进的工程化流水线。

最终系统应该支持：

```bash
make scout-topics
make generate-v2 CH=51
make review-chapter CH=51
make review-range START=1 END=10
make publish-check START=1 END=10
```

---

## 1. 最终形态

NovelOps v2 由三条流水线组成：

```text
1. Topic Scout      选题情报流水线
2. Draft Factory    正文生产流水线
3. Review Gate      审稿门禁流水线
```

三条流水线的关系：

```text
外部趋势 / 榜单 / 读者情绪
        ↓
Topic Scout 生成选题卡
        ↓
Story Bible / Volume Outline / Chapter Queue
        ↓
Draft Factory 生成章节候选
        ↓
Review Gate 自动审稿
        ↓
人工最终确认
        ↓
进入 final/ 或 revision_queue
```

核心原则：

```text
AI 可以自动生成，但不允许自动发布。
AI 可以自动评分，但最终商业判断由人确认。
AI 可以给修改建议，但不能绕过门禁进入 final。
```

---

## 2. 开发优先级

两天开发窗口内，优先级如下：

| 优先级 | 模块 | 原因 |
|---|---|---|
| P0 | Review Gate | 作品马上跑推荐，必须先降低质量翻车概率 |
| P0 | Publish Check | 前 10 章上线前必须有整体审稿报告 |
| P1 | Generate Chapter v2 | 提高后续生产质量，减少 AI 腔和水章 |
| P1 | Topic Scout MVP | 先做结构化情报接口，后续再增强联网能力 |
| P2 | 自动趋势分析增强 | 可以后置，不影响当前上线 |
| P2 | UI / 数据看板 | 暂时不做 |

---

## 3. 目标目录结构

在现有 repo 基础上新增以下目录：

```text
novel0/
├── intelligence/
│   ├── sources.yaml
│   ├── raw/
│   │   ├── fanqie_rankings/
│   │   ├── web_articles/
│   │   ├── douyin_signals/
│   │   └── manual_notes/
│   ├── processed/
│   │   ├── topic_candidates.jsonl
│   │   ├── trope_map.json
│   │   ├── title_patterns.md
│   │   └── opening_patterns.md
│   └── reports/
│       ├── daily_topic_report.md
│       └── topic_scoreboard.md
│
├── generation/
│   ├── chapter_intent/
│   ├── scene_chain/
│   ├── draft_v1/
│   ├── draft_v2_commercial/
│   ├── draft_v3_humanized/
│   └── final_candidate/
│
├── reviews/
│   ├── rubrics/
│   │   ├── platform_safety_rubric.md
│   │   ├── ai_trace_rubric.md
│   │   ├── commercial_rubric.md
│   │   ├── continuity_rubric.md
│   │   └── reader_retention_rubric.md
│   ├── chapter_reviews/
│   │   ├── json/
│   │   └── markdown/
│   └── aggregate/
│       ├── publish_check_report.md
│       ├── revision_queue.md
│       ├── repeated_ai_patterns.md
│       └── weak_points.md
│
├── config/
│   └── novelops_v2.json
│
└── scripts/
    ├── topic_scout.py
    ├── generate_chapter_v2.py
    ├── review_gate.py
    ├── publish_check.py
    └── lib/
        ├── llm_client.py
        ├── file_utils.py
        ├── schemas.py
        └── scoring.py
```

说明：

- `intelligence/`：负责选题、趋势、读者需求、题材信号。
- `generation/`：负责新一代章节生产中间产物。
- `reviews/`：负责自动审稿、风险判断、修改任务。
- `scripts/lib/`：把可复用代码抽出来，避免所有脚本都写成巨型文件。

---

## 4. 分支与安全开发流程

### 4.1 新建分支

```bash
git checkout -b feature/novelops-v2
```

### 4.2 保护现有成果

开发前先确认当前小说正文和配置不会被误覆盖：

```bash
git status
find chapters -maxdepth 2 -type f | sort | head
find progress -maxdepth 1 -type f | sort
```

### 4.3 所有新脚本默认不覆盖原文件

规则：

```text
review_gate.py 只读 chapters/ 和 progress/，写 reviews/
generate_chapter_v2.py 只写 generation/，不直接覆盖 chapters/
publish_check.py 只读 reviews/ 和 chapters/，写 reviews/aggregate/
topic_scout.py 只写 intelligence/
```

严禁脚本默认直接改：

```text
chapters/01-50.md
bible/
progress/
outlines/chapter_queue.md
```

如确实需要写入，必须加显式参数：

```bash
--apply
--overwrite
--confirm
```

本阶段建议不做自动 overwrite。

---

## 5. 配置文件设计

新增：`config/novelops_v2.json`

```json
{
  "project_name": "novel0",
  "target_platform": "fanqie",
  "language": "zh-CN",
  "chapter": {
    "target_min_chars": 2000,
    "target_max_chars": 2800,
    "preferred_scene_count": [3, 5]
  },
  "paths": {
    "bible_dir": "bible",
    "outlines_dir": "outlines",
    "chapters_dir": "chapters",
    "progress_dir": "progress",
    "generation_dir": "generation",
    "reviews_dir": "reviews",
    "intelligence_dir": "intelligence"
  },
  "review_gate": {
    "thresholds": {
      "hook_score_min": 7,
      "conflict_score_min": 7,
      "character_consistency_score_min": 8,
      "continuity_score_min": 8,
      "ai_trace_score_min": 7,
      "reader_retention_score_min": 7,
      "platform_risk_score_max": 5
    },
    "fatal_issue_limit": 0
  },
  "generation": {
    "stages": [
      "chapter_intent",
      "scene_chain",
      "draft_v1",
      "commercial_rewrite",
      "humanize",
      "final_candidate"
    ],
    "write_final_directly": false
  },
  "topic_scout": {
    "use_live_search": false,
    "use_mock_when_unavailable": true,
    "max_candidates": 20
  }
}
```

---

## 6. 数据结构设计

建议在 `scripts/lib/schemas.py` 中定义这些结构。可以先用 `dataclass`，不用一上来引入复杂依赖。

### 6.1 TopicCandidate

```json
{
  "topic_name": "寿命可视化 + 都市救赎",
  "target_reader": "喜欢都市异能、情绪救赎、命运反转的读者",
  "core_hook": "主角能看见别人的人生余额，救人要消耗自己的寿命",
  "reader_promise": "每个单元都有人生危机，每次救人都带来代价和反转",
  "market_signals": [
    "都市异能仍具稳定需求",
    "短剧市场偏好强钩子开局",
    "救赎/命运/代价类情绪适合单元剧"
  ],
  "differentiation": "不是单纯装逼异能，而是命运代价 + 情感救赎",
  "scores": {
    "reader_demand": 8,
    "supply_gap": 6,
    "platform_fit": 7,
    "serializability": 8,
    "ai_generation_difficulty": 5,
    "differentiation": 7,
    "compliance_risk": 3,
    "final_score": 7.1
  }
}
```

### 6.2 ChapterIntent

```json
{
  "chapter": 51,
  "title": "第51章 新能力者出现",
  "single_mission": "让陈默发现第一个被系统污染的新能力者",
  "reader_reward": "看到主角从被动救人转向主动建立组织",
  "core_conflict": "新能力者不相信陈默，并误以为陈默也是天平会的人",
  "emotional_hook": "林见鹿发现陈默开始把自己推到危险前线",
  "must_include": [
    "新能力者的异常倒计时",
    "陈默的寿命代价",
    "余额守护者组织雏形"
  ],
  "must_avoid": [
    "大段解释组织设定",
    "让主角无代价解决问题",
    "提前暴露第二卷最终反派"
  ],
  "ending_hook": "新能力者头顶的余额突然归零，但人没有死"
}
```

### 6.3 SceneChain

```json
{
  "chapter": 51,
  "scenes": [
    {
      "scene_id": 1,
      "purpose": "承接上一章，展示新组织刚成立后的现实困难",
      "location": "旧教学楼办公室",
      "characters": ["陈默", "林见鹿"],
      "conflict": "组织没有人手，也没有可信数据来源",
      "turning_point": "陈默看见远处有人头顶出现异常余额"
    },
    {
      "scene_id": 2,
      "purpose": "引入新能力者",
      "location": "校园天桥",
      "characters": ["陈默", "新能力者"],
      "conflict": "新能力者把陈默当成追捕者",
      "turning_point": "对方也能看见陈默头顶的寿命"
    }
  ]
}
```

### 6.4 ReviewResult

```json
{
  "chapter": 51,
  "publishable": false,
  "scores": {
    "hook_score": 7,
    "conflict_score": 6,
    "character_consistency_score": 8,
    "continuity_score": 9,
    "ai_trace_score": 5,
    "reader_retention_score": 6,
    "platform_risk_score": 2
  },
  "fatal_issues": [
    "中段 900 字解释组织设定，剧情推进不足",
    "AI 总结腔明显，角色对话过于工整"
  ],
  "revision_tasks": [
    "删减第 800-1500 字的设定解释，改成新能力者与陈默的误会冲突",
    "结尾增加异常视觉钩子：余额归零但人未死亡",
    "减少'他意识到'、'命运仿佛'等抽象总结句"
  ],
  "suggested_action": "rewrite_required"
}
```

---

## 7. 第一天开发计划：Review Gate 优先

第一天目标：

```text
可以对任意章节运行自动审稿，输出 JSON + Markdown，明确告诉你：能不能发布、哪里不行、怎么改。
```

---

### 7.1 Step 1：创建目录与 rubric 文件

执行：

```bash
mkdir -p reviews/rubrics
mkdir -p reviews/chapter_reviews/json
mkdir -p reviews/chapter_reviews/markdown
mkdir -p reviews/aggregate
mkdir -p scripts/lib
```

新增 `reviews/rubrics/ai_trace_rubric.md`：

```md
# AI Trace Rubric

检查目标：判断章节是否有明显 AI 生成痕迹。

重点问题：

1. 是否大量使用抽象总结句
   - 他意识到……
   - 这一刻，他终于明白……
   - 命运仿佛……
   - 世界仿佛安静下来……

2. 是否动作不足、心理过多

3. 是否人物对话过于工整

4. 是否每章结尾都用相似抒情句

5. 是否存在说明书式设定解释

6. 是否存在模型提示词残留
   - 根据前文
   - 本章需要
   - 接下来
   - 以下是
   - 综上
   - 作为一个

评分：
- 10：几乎无 AI 痕迹
- 8：可发布，少量润色即可
- 7：勉强可发布，需要人工检查
- 5：AI 味明显，需要重写
- 3：高风险，不可发布
```

新增 `reviews/rubrics/commercial_rubric.md`：

```md
# Commercial Rubric

检查目标：判断章节是否有商业网文的阅读驱动力。

检查项：

1. 本章是否有明确冲突？
2. 主角是否主动选择，而不是被剧情推着走？
3. 是否有读者可感知的收益？
   - 打脸
   - 救赎
   - 反转
   - 危机解除
   - 能力成长
   - 情感推进
4. 是否推进主线？
5. 是否推进人物关系？
6. 是否存在 500 字以上无剧情推进？
7. 结尾是否让人想点下一章？

评分：
- 10：强爽点、强钩子
- 8：可发布
- 6：偏平，需要加强
- 4：水章风险
```

新增 `reviews/rubrics/continuity_rubric.md`：

```md
# Continuity Rubric

检查目标：判断章节是否破坏前文设定。

检查项：

1. 人物当前状态是否与 character_state.md 一致？
2. 能力规则是否与 02_power_system.md 一致？
3. 伏笔是否被误回收或遗忘？
4. 时间线是否连续？
5. 人物关系是否突然变化？
6. 主角能力是否越权？
7. 是否推翻前文已经确定的事实？

评分：
- 10：完全一致
- 8：小问题，可发布
- 6：明显风险，需要修
- 4：不可发布
```

新增 `reviews/rubrics/platform_safety_rubric.md`：

```md
# Platform Safety Rubric

检查目标：降低平台审核与推荐风险。

检查项：

1. 是否存在明显违规、低俗、血腥、极端描写？
2. 是否存在不适合商业平台推荐的敏感表达？
3. 是否存在过度阴暗、价值导向不稳定的问题？
4. 是否存在标题党但正文不兑现的问题？
5. 是否存在大篇幅疑似 AI 水文？
6. 是否存在平台可能判定为低质生成内容的模式？

评分：
- 1-2：风险很低
- 3-5：可接受，但需人工检查
- 6-8：明显风险，不建议发布
- 9-10：高风险，必须重写
```

新增 `reviews/rubrics/reader_retention_rubric.md`：

```md
# Reader Retention Rubric

检查目标：判断章节是否能让读者继续看下一章。

检查项：

1. 前 300 字是否快速进入冲突？
2. 本章是否有情绪波动？
3. 本章是否有信息增量？
4. 是否有一个具体可视化的结尾钩子？
5. 是否有读者关心的人物处于不确定状态？
6. 是否有未解决问题驱动下一章？

评分：
- 10：强追读
- 8：可发布
- 6：读者可能流失
- 4：明显留存风险
```

---

### 7.2 Step 2：实现基础工具函数

新增 `scripts/lib/file_utils.py`：

功能：

```text
read_text(path)
write_text(path, content)
ensure_dir(path)
load_json(path)
save_json(path, data)
find_chapter_file(chapter_number)
```

要求：

- 所有读取失败要给出清晰错误；
- 写文件前自动创建目录；
- `find_chapter_file(1)` 能找到 `chapters/01.md` 或 `chapters/1.md` 或 `chapters/final/01.md`；
- 如果同时存在多个候选，优先顺序为：

```text
chapters/final/
chapters/
generation/final_candidate/
generation/draft_v3_humanized/
generation/draft_v2_commercial/
generation/draft_v1/
```

---

### 7.3 Step 3：实现 LLM 客户端适配层

新增 `scripts/lib/llm_client.py`。

目标：先复用你现有的 `novel_workflow.py` 里的 LLM 调用逻辑。如果暂时无法复用，就先写一个最小接口。

接口设计：

```python
class LLMClient:
    def __init__(self, config_path: str = "config/workflow.local.json"):
        pass

    def complete(self, prompt: str, system: str | None = None) -> str:
        pass
```

要求：

1. 如果现有项目已有 API 调用方式，直接封装复用。
2. 如果没有 API key，允许返回 mock 文本，不能让脚本崩溃。
3. 所有脚本通过这个客户端调用模型，不要在每个脚本里重复写 API 逻辑。

---

### 7.4 Step 4：实现 `review_gate.py`

新增：`scripts/review_gate.py`

命令形式：

```bash
python scripts/review_gate.py --chapter 1
python scripts/review_gate.py --chapter 1 --no-llm
python scripts/review_gate.py --chapter 1 --input generation/final_candidate/ch051.md
```

Makefile：

```makefile
review-chapter:
	python scripts/review_gate.py --chapter $(CH)
```

`review_gate.py` 工作流程：

```text
1. 读取 config/novelops_v2.json
2. 找到章节正文
3. 读取 bible/、progress/、reviews/rubrics/
4. 构造审稿 prompt
5. 调用 LLM 输出结构化 JSON
6. 如果 LLM 输出不是合法 JSON，尝试修复一次
7. 根据阈值计算 publishable
8. 写入 reviews/chapter_reviews/json/chXXX_review.json
9. 写入 reviews/chapter_reviews/markdown/chXXX_review.md
10. 在终端打印简短结论
```

审稿 Prompt 模板：

```text
你是商业网文冷启动审稿编辑，目标平台是番茄小说。

你要判断下面这一章是否适合发布。

请严格从以下维度评分：
1. hook_score：章节钩子强度，1-10
2. conflict_score：冲突强度，1-10
3. character_consistency_score：人物一致性，1-10
4. continuity_score：连续性，1-10
5. ai_trace_score：去 AI 痕迹程度，1-10，分数越高越像人写
6. reader_retention_score：追读潜力，1-10
7. platform_risk_score：平台风险，1-10，分数越高风险越大

硬门禁：
- hook_score < 7，不可发布
- conflict_score < 7，不可发布
- character_consistency_score < 8，不可发布
- continuity_score < 8，不可发布
- ai_trace_score < 7，不可发布
- reader_retention_score < 7，不可发布
- platform_risk_score > 5，不可发布

你必须输出合法 JSON，不要输出 Markdown，不要输出解释性废话。

JSON 格式如下：
{
  "chapter": 章节号,
  "publishable": true 或 false,
  "scores": {
    "hook_score": 数字,
    "conflict_score": 数字,
    "character_consistency_score": 数字,
    "continuity_score": 数字,
    "ai_trace_score": 数字,
    "reader_retention_score": 数字,
    "platform_risk_score": 数字
  },
  "fatal_issues": ["问题1", "问题2"],
  "revision_tasks": ["任务1", "任务2"],
  "best_parts": ["优点1", "优点2"],
  "suggested_action": "publish" 或 "minor_revision" 或 "rewrite_required"
}

以下是故事设定：
{bible_context}

以下是当前进度：
{progress_context}

以下是审稿标准：
{rubrics}

以下是章节正文：
{chapter_text}
```

终端输出示例：

```text
Chapter 003 Review
Publishable: false
Scores:
- hook: 8
- conflict: 6
- continuity: 9
- ai_trace: 5
- platform_risk: 2
Fatal Issues:
1. 中段解释过多，冲突不足
2. AI 总结腔明显
Revision Tasks:
1. 删除第 900-1300 字设定解释，改成陈默和周野的动作冲突
2. 结尾增加寿命减少的视觉钩子
```

---

### 7.5 Step 5：实现 `publish_check.py`

新增：`scripts/publish_check.py`

命令形式：

```bash
python scripts/publish_check.py --start 1 --end 10
```

Makefile：

```makefile
review-range:
	python scripts/publish_check.py --start $(START) --end $(END) --review-missing

publish-check:
	python scripts/publish_check.py --start $(START) --end $(END)
```

工作流程：

```text
1. 遍历 START 到 END
2. 检查每章是否已有 review JSON
3. 如果传入 --review-missing，则自动调用 review_gate
4. 汇总每章 publishable 状态
5. 输出整体上线建议
6. 写 reviews/aggregate/publish_check_report.md
7. 写 reviews/aggregate/revision_queue.md
```

聚合报告格式：

```md
# Publish Check Report

## 范围

第 1 章 - 第 10 章

## 总体结论

- 可发布章节：7/10
- 需要小修：2/10
- 必须重写：1/10

## 高风险章节

| 章节 | 问题 | 建议 |
|---|---|---|
| 第3章 | AI 腔明显，冲突不足 | 重写中段 |

## 共性问题

1. 前 3 章设定解释偏多
2. 章节结尾钩子有重复句式
3. 主角内心独白偏抽象

## 上线前必须完成

- [ ] 修第 3 章中段
- [ ] 强化第 1 章前 300 字钩子
- [ ] 删除第 2 章过度解释句
```

---

## 8. 第二天开发计划：Generate v2 + Topic Scout

第二天目标：

```text
正文生成从“一步写章”升级为“章节意图 → 场景链 → 草稿 → 商业改写 → 去 AI 腔 → 定稿候选”。
```

---

### 8.1 Step 1：创建 generation 目录

```bash
mkdir -p generation/chapter_intent
mkdir -p generation/scene_chain
mkdir -p generation/draft_v1
mkdir -p generation/draft_v2_commercial
mkdir -p generation/draft_v3_humanized
mkdir -p generation/final_candidate
```

---

### 8.2 Step 2：实现 `generate_chapter_v2.py`

新增：`scripts/generate_chapter_v2.py`

命令形式：

```bash
python scripts/generate_chapter_v2.py --chapter 51
python scripts/generate_chapter_v2.py --chapter 51 --stage chapter_intent
python scripts/generate_chapter_v2.py --chapter 51 --from-stage scene_chain
```

Makefile：

```makefile
generate-v2:
	python scripts/generate_chapter_v2.py --chapter $(CH)
```

工作流程：

```text
1. 读取 Bible
2. 读取 progress/current_context.md
3. 读取 progress/chapter_summary.md
4. 读取 progress/character_state.md
5. 读取 outlines/chapter_queue.md
6. 生成 Chapter Intent
7. 生成 Scene Chain
8. 生成 Draft v1
9. 生成 Commercial Rewrite
10. 生成 Humanized Draft
11. 输出 Final Candidate
12. 自动调用 review_gate 审稿
```

每一阶段都要保存中间文件：

```text
generation/chapter_intent/ch051_intent.json
generation/scene_chain/ch051_scene_chain.json
generation/draft_v1/ch051_draft_v1.md
generation/draft_v2_commercial/ch051_draft_v2.md
generation/draft_v3_humanized/ch051_draft_v3.md
generation/final_candidate/ch051_final_candidate.md
```

---

### 8.3 Stage 1：Chapter Intent

Prompt：

```text
你是商业网文主编。请根据故事 Bible、当前进度和章节队列，为第 {chapter} 章生成 Chapter Intent。

目标：先明确这一章的功能，再写正文。

要求：
1. 本章必须只有一个核心任务。
2. 必须说明读者看完本章获得什么。
3. 必须说明本章冲突是什么。
4. 必须说明本章情绪钩子是什么。
5. 必须列出 must_include 和 must_avoid。
6. 必须给出结尾钩子。

输出合法 JSON：
{
  "chapter": 数字,
  "title": "章节标题",
  "single_mission": "本章唯一任务",
  "reader_reward": "读者收益",
  "core_conflict": "核心冲突",
  "emotional_hook": "情绪钩子",
  "must_include": [],
  "must_avoid": [],
  "ending_hook": "结尾钩子"
}

故事 Bible：
{bible_context}

当前进度：
{progress_context}

章节队列：
{chapter_queue}
```

验收标准：

- JSON 可解析；
- `single_mission` 不超过 80 字；
- `must_avoid` 至少 3 条；
- `ending_hook` 必须具体可视化，不能是抽象句。

---

### 8.4 Stage 2：Scene Chain

Prompt：

```text
你是商业网文章节导演。请根据 Chapter Intent 设计本章场景链。

要求：
1. 本章 3-5 个场景。
2. 每个场景必须有 purpose、location、characters、conflict、turning_point。
3. 每个场景都必须推动剧情，不能只是解释设定。
4. 场景之间要有因果关系。
5. 最后一个场景必须形成结尾钩子。

输出合法 JSON：
{
  "chapter": 数字,
  "scenes": [
    {
      "scene_id": 1,
      "purpose": "场景功能",
      "location": "地点",
      "characters": [],
      "conflict": "冲突",
      "turning_point": "转折"
    }
  ]
}

Chapter Intent：
{chapter_intent}

故事上下文：
{context}
```

验收标准：

- 3-5 个场景；
- 每个场景都有 conflict；
- 最后一个 turning_point 是钩子；
- 不允许出现“介绍设定”“补充背景”作为主要 purpose。

---

### 8.5 Stage 3：Draft v1

Prompt：

```text
你是番茄小说商业连载作者。请根据 Chapter Intent 和 Scene Chain 写第 {chapter} 章正文草稿。

要求：
1. 字数 2000-2800 中文字。
2. 开头 300 字内进入冲突。
3. 每个场景都要有动作、对话、情绪变化。
4. 不要大段解释设定。
5. 不要写成大纲。
6. 不要出现提示词痕迹。
7. 结尾必须形成强钩子。
8. 文风要接近前文，保持人物一致性。

禁止：
- 根据前文
- 本章需要
- 接下来
- 他意识到命运如何如何
- 仿佛整个世界如何如何
- 大段哲理总结

Chapter Intent：
{chapter_intent}

Scene Chain：
{scene_chain}

前文摘要：
{progress_context}

人物状态：
{character_state}
```

输出到：

```text
generation/draft_v1/chXXX_draft_v1.md
```

---

### 8.6 Stage 4：Commercial Rewrite

Prompt：

```text
你是商业网文责编。请对以下草稿做商业化强化，但不要改变核心剧情。

强化目标：
1. 开头更快进入冲突。
2. 中段减少解释，增加动作和对抗。
3. 主角选择更主动。
4. 爽点更明确。
5. 情绪波动更强。
6. 结尾钩子更具体。

不要做：
1. 不要改变已确定设定。
2. 不要新增大段世界观。
3. 不要让主角无代价开挂。
4. 不要把文风改得浮夸。

请直接输出改写后的完整章节正文。

原草稿：
{draft_v1}

Chapter Intent：
{chapter_intent}

Scene Chain：
{scene_chain}
```

输出到：

```text
generation/draft_v2_commercial/chXXX_draft_v2.md
```

---

### 8.7 Stage 5：Humanize / 去 AI 腔

Prompt：

```text
你是人类小说编辑。请对以下章节做去 AI 腔处理。

重点修改：
1. 删除抽象总结句。
2. 把“他意识到”改成动作、表情、对话或具体画面。
3. 减少整齐排比句。
4. 让人物说话更自然。
5. 避免每段都解释情绪。
6. 保留剧情，不大改结构。
7. 保持商业网文节奏。

常见需要删除或改写的表达：
- 他意识到
- 这一刻
- 命运仿佛
- 世界仿佛
- 他终于明白
- 某种意义上
- 这不是……而是……
- 所有人都不知道的是

请直接输出去 AI 腔后的完整章节正文。

原文：
{draft_v2}
```

输出到：

```text
generation/draft_v3_humanized/chXXX_draft_v3.md
```

---

### 8.8 Stage 6：Final Candidate + 自动审稿

`generate_chapter_v2.py` 完成后，将 `draft_v3` 复制为：

```text
generation/final_candidate/chXXX_final_candidate.md
```

然后自动调用：

```bash
python scripts/review_gate.py --chapter XXX --input generation/final_candidate/chXXX_final_candidate.md
```

如果审稿不通过，不要写入 `chapters/final/`。

终端输出：

```text
Chapter 051 generated.
Final candidate: generation/final_candidate/ch051_final_candidate.md
Review: reviews/chapter_reviews/markdown/ch051_review.md
Publishable: false
Suggested action: minor_revision
```

---

## 9. Topic Scout 开发计划

Topic Scout 的目标不是“全网爬虫”，而是：

> 把外部题材信号结构化成可比较、可评分、可进入创作决策的选题卡。

### 9.1 新增目录

```bash
mkdir -p intelligence/raw/fanqie_rankings
mkdir -p intelligence/raw/web_articles
mkdir -p intelligence/raw/douyin_signals
mkdir -p intelligence/raw/manual_notes
mkdir -p intelligence/processed
mkdir -p intelligence/reports
```

### 9.2 sources.yaml

新增：`intelligence/sources.yaml`

```yaml
sources:
  - name: fanqie_manual_rankings
    type: manual
    description: 手动粘贴番茄榜单、书名、简介、评论信号
    input_dir: intelligence/raw/fanqie_rankings

  - name: web_articles
    type: manual_or_search
    description: 公开网页上的网文趋势、短剧趋势、平台活动信息
    input_dir: intelligence/raw/web_articles

  - name: douyin_signals
    type: manual
    description: 手动记录抖音短剧、关键词、爆款标题、评论情绪
    input_dir: intelligence/raw/douyin_signals

  - name: manual_notes
    type: manual
    description: 人工观察、灵感、编辑反馈、读者评论
    input_dir: intelligence/raw/manual_notes
```

### 9.3 不做违规采集

Topic Scout 只允许处理：

```text
1. 你手动粘贴的公开榜单信息；
2. 公开网页资料；
3. 你自己作品的后台数据；
4. 读者公开评论；
5. 你自己记录的观察笔记。
```

不做：

```text
1. 绕过登录；
2. 绕过反爬；
3. 批量抓取平台内部数据；
4. 自动模拟人工操作；
5. 侵犯其他作者版权内容。
```

### 9.4 实现 `topic_scout.py`

命令形式：

```bash
python scripts/topic_scout.py
python scripts/topic_scout.py --input intelligence/raw/manual_notes/today.md
```

Makefile：

```makefile
scout-topics:
	python scripts/topic_scout.py
```

工作流程：

```text
1. 读取 intelligence/sources.yaml
2. 扫描 raw/ 下的所有 md/txt/json 文件
3. 提取高频题材、金手指、书名模式、简介钩子、读者情绪
4. 生成 topic_candidates.jsonl
5. 生成 topic_scoreboard.md
6. 生成 daily_topic_report.md
```

### 9.5 选题评分公式

```text
final_score =
reader_demand * 0.25
+ supply_gap * 0.20
+ platform_fit * 0.20
+ serializability * 0.15
+ ai_generation_fit * 0.10
+ differentiation * 0.10
- compliance_risk * 0.30
```

评分解释：

| 指标 | 含义 |
|---|---|
| reader_demand | 读者需求强度 |
| supply_gap | 是否存在同质化后的新切口 |
| platform_fit | 是否适合番茄读者和推荐机制 |
| serializability | 能否撑 80 万字以上 |
| ai_generation_fit | 是否适合 AI 稳定批量生产 |
| differentiation | 与同类题材差异化程度 |
| compliance_risk | 平台风险，越高越扣分 |

### 9.6 Topic Scout Prompt

```text
你是商业网文选题分析师。请根据以下市场信号，生成可用于番茄小说的选题候选。

你不要简单追热点，而要寻找：
1. 稳定读者需求；
2. 可复制章节结构；
3. 差异化金手指；
4. 低平台风险；
5. 适合长篇连载；
6. 适合 AI 辅助持续生产。

请输出 JSONL，每行一个选题候选。

每个候选格式：
{
  "topic_name": "选题名称",
  "target_reader": "目标读者",
  "core_hook": "一句话核心钩子",
  "reader_promise": "读者持续追读承诺",
  "market_signals": [],
  "differentiation": "差异化说明",
  "scores": {
    "reader_demand": 1-10,
    "supply_gap": 1-10,
    "platform_fit": 1-10,
    "serializability": 1-10,
    "ai_generation_fit": 1-10,
    "differentiation": 1-10,
    "compliance_risk": 1-10,
    "final_score": 数字
  },
  "first_3_chapters": [
    "第1章钩子",
    "第2章推进",
    "第3章付费/追读点"
  ],
  "risk_notes": []
}

市场信号：
{market_notes}
```

---

## 10. Makefile 修改

在现有 `Makefile` 中新增：

```makefile
.PHONY: scout-topics generate-v2 review-chapter review-range publish-check

scout-topics:
	python scripts/topic_scout.py

generate-v2:
	python scripts/generate_chapter_v2.py --chapter $(CH)

review-chapter:
	python scripts/review_gate.py --chapter $(CH)

review-range:
	python scripts/publish_check.py --start $(START) --end $(END) --review-missing

publish-check:
	python scripts/publish_check.py --start $(START) --end $(END)
```

使用示例：

```bash
make review-chapter CH=1
make review-range START=1 END=10
make publish-check START=1 END=10
make generate-v2 CH=51
make scout-topics
```

---

## 11. Codex 执行 Prompt 系列

下面这些 prompt 可以分阶段喂给 Codex。不要一次性让它做完全部，否则容易改崩。

---

### Prompt 1：检查 repo 并制定改动计划

```text
你是我的 AI 小说工业化系统工程师。当前 repo 是 novel0，一个面向番茄小说商业连载的长篇小说生产系统。

请先只做检查，不要修改文件。

任务：
1. 扫描当前目录结构；
2. 找出已有的 bible、outlines、chapters、progress、prompts、scripts、Makefile；
3. 阅读 scripts/novel_workflow.py，判断现有 LLM 调用逻辑、章节生成逻辑、review 逻辑是否可以复用；
4. 输出一份 NovelOps v2 改造计划；
5. 明确哪些文件会新增，哪些文件会修改，哪些文件不能动。

限制：
- 不要重构现有 novel_workflow.py；
- 不要修改已完成章节；
- 不要覆盖 bible 和 progress；
- 只输出计划，不要写代码。
```

验收：Codex 应该输出文件清单和实施顺序。

---

### Prompt 2：创建目录、配置、rubric

```text
根据上一步计划，现在开始执行 NovelOps v2 的第一阶段。

请完成：
1. 新增目录：
   - intelligence/raw/fanqie_rankings
   - intelligence/raw/web_articles
   - intelligence/raw/douyin_signals
   - intelligence/raw/manual_notes
   - intelligence/processed
   - intelligence/reports
   - generation/chapter_intent
   - generation/scene_chain
   - generation/draft_v1
   - generation/draft_v2_commercial
   - generation/draft_v3_humanized
   - generation/final_candidate
   - reviews/rubrics
   - reviews/chapter_reviews/json
   - reviews/chapter_reviews/markdown
   - reviews/aggregate
   - scripts/lib

2. 新增 config/novelops_v2.json。

3. 新增 intelligence/sources.yaml。

4. 新增以下 rubric 文件：
   - reviews/rubrics/ai_trace_rubric.md
   - reviews/rubrics/commercial_rubric.md
   - reviews/rubrics/continuity_rubric.md
   - reviews/rubrics/platform_safety_rubric.md
   - reviews/rubrics/reader_retention_rubric.md

限制：
- 不要修改现有章节；
- 不要修改 novel_workflow.py；
- 不要引入复杂依赖；
- 完成后输出新增文件列表。
```

验收：目录和文件存在。

---

### Prompt 3：实现通用工具库

```text
现在实现 NovelOps v2 的通用工具库。

请新增或完善：
1. scripts/lib/file_utils.py
2. scripts/lib/scoring.py
3. scripts/lib/llm_client.py

要求：
file_utils.py 提供：
- read_text(path)
- write_text(path, content)
- ensure_dir(path)
- load_json(path)
- save_json(path, data)
- find_chapter_file(chapter_number, preferred_input=None)

scoring.py 提供：
- apply_review_thresholds(review_result, config)
- calculate_topic_score(scores)

llm_client.py 提供：
- LLMClient.complete(prompt, system=None)

优先复用现有 scripts/novel_workflow.py 里的 LLM 调用逻辑。如果复用困难，先做一个最小可运行版本，并清楚标注 TODO。

限制：
- 不要让没有 API key 时脚本直接崩溃；
- 不要把 API key 写进代码；
- 不要修改现有正文。

完成后运行基础语法检查。
```

验收：

```bash
python -m py_compile scripts/lib/file_utils.py scripts/lib/scoring.py scripts/lib/llm_client.py
```

---

### Prompt 4：实现 review_gate.py

```text
现在实现 NovelOps v2 最重要的模块：scripts/review_gate.py。

命令要求：
python scripts/review_gate.py --chapter 1
python scripts/review_gate.py --chapter 1 --input path/to/chapter.md
python scripts/review_gate.py --chapter 1 --no-llm

功能要求：
1. 读取 config/novelops_v2.json；
2. 自动找到章节文件；
3. 读取 bible、progress、reviews/rubrics；
4. 构造商业网文审稿 prompt；
5. 调用 LLM，要求输出 JSON；
6. 如果 --no-llm，则使用规则和启发式生成一个 mock review；
7. 根据阈值判断 publishable；
8. 输出 JSON 到 reviews/chapter_reviews/json/chXXX_review.json；
9. 输出 Markdown 到 reviews/chapter_reviews/markdown/chXXX_review.md；
10. 终端打印简短结论。

评分维度：
- hook_score
- conflict_score
- character_consistency_score
- continuity_score
- ai_trace_score
- reader_retention_score
- platform_risk_score

硬门禁：
- hook_score < 7，不可发布
- conflict_score < 7，不可发布
- character_consistency_score < 8，不可发布
- continuity_score < 8，不可发布
- ai_trace_score < 7，不可发布
- reader_retention_score < 7，不可发布
- platform_risk_score > 5，不可发布

限制：
- 不要修改章节正文；
- 不要写入 chapters/final；
- 输出必须可被 publish_check.py 读取。
```

验收：

```bash
python scripts/review_gate.py --chapter 1 --no-llm
ls reviews/chapter_reviews/json
ls reviews/chapter_reviews/markdown
```

---

### Prompt 5：实现 publish_check.py

```text
请实现 scripts/publish_check.py。

命令要求：
python scripts/publish_check.py --start 1 --end 10
python scripts/publish_check.py --start 1 --end 10 --review-missing

功能：
1. 遍历指定章节范围；
2. 检查每章是否已有 review JSON；
3. 如果传入 --review-missing，自动调用 review_gate.py 生成缺失 review；
4. 汇总 publishable、minor_revision、rewrite_required；
5. 输出 reviews/aggregate/publish_check_report.md；
6. 输出 reviews/aggregate/revision_queue.md；
7. 终端打印整体结论。

限制：
- 不要修改章节正文；
- 不要覆盖已有 review，除非显式传入 --force；
- 报告要适合我上线前快速检查。
```

验收：

```bash
python scripts/publish_check.py --start 1 --end 3 --review-missing
cat reviews/aggregate/publish_check_report.md
```

---

### Prompt 6：实现 generate_chapter_v2.py

```text
请实现 scripts/generate_chapter_v2.py。

命令要求：
python scripts/generate_chapter_v2.py --chapter 51
python scripts/generate_chapter_v2.py --chapter 51 --stage chapter_intent
python scripts/generate_chapter_v2.py --chapter 51 --from-stage scene_chain

功能流程：
1. 读取 Bible、progress、outlines/chapter_queue.md；
2. 生成 chapter_intent，保存到 generation/chapter_intent/chXXX_intent.json；
3. 生成 scene_chain，保存到 generation/scene_chain/chXXX_scene_chain.json；
4. 生成 draft_v1，保存到 generation/draft_v1/chXXX_draft_v1.md；
5. 商业化改写，保存到 generation/draft_v2_commercial/chXXX_draft_v2.md；
6. 去 AI 腔，保存到 generation/draft_v3_humanized/chXXX_draft_v3.md；
7. 复制为 final_candidate，保存到 generation/final_candidate/chXXX_final_candidate.md；
8. 自动调用 review_gate.py 审稿。

限制：
- 不要直接写入 chapters/；
- 不要直接写入 chapters/final/；
- 如果某阶段已有文件，默认复用；
- 只有传入 --force-stage 时才重跑该阶段；
- 如果审稿不通过，必须提示 revision path。
```

验收：

```bash
python scripts/generate_chapter_v2.py --chapter 51
ls generation/final_candidate
ls reviews/chapter_reviews/markdown
```

---

### Prompt 7：实现 topic_scout.py

```text
请实现 scripts/topic_scout.py。

命令要求：
python scripts/topic_scout.py
python scripts/topic_scout.py --input intelligence/raw/manual_notes/today.md

功能：
1. 读取 intelligence/sources.yaml；
2. 扫描 intelligence/raw 下的 md/txt/json 文件；
3. 汇总市场信号；
4. 调用 LLM 生成 topic_candidates.jsonl；
5. 计算 final_score；
6. 输出 intelligence/reports/topic_scoreboard.md；
7. 输出 intelligence/reports/daily_topic_report.md。

要求：
- 如果 raw 目录没有内容，则生成一份示例 mock 报告；
- 不做爬虫，不绕过登录，不模拟人工操作；
- 输出必须结构化，方便之后进入选题决策。
```

验收：

```bash
python scripts/topic_scout.py
cat intelligence/reports/topic_scoreboard.md
```

---

### Prompt 8：更新 Makefile 和 README

```text
请更新 Makefile，新增以下命令：
- make scout-topics
- make generate-v2 CH=数字
- make review-chapter CH=数字
- make review-range START=数字 END=数字
- make publish-check START=数字 END=数字

同时新增或更新 docs/NovelOps_v2_usage.md，说明：
1. 每个命令怎么用；
2. 输出文件在哪里；
3. 上线前应该跑哪些命令；
4. 生成新章节应该跑哪些命令；
5. 如何查看 revision_queue。

限制：
- 不要删除现有 Makefile 命令；
- 不要破坏原来的 run-batch 流程。
```

验收：

```bash
make review-chapter CH=1
make publish-check START=1 END=3
make scout-topics
```

---

## 12. 上线前工作流

你现在马上要跑真实推荐，所以上线前按这个流程：

```bash
# 1. 先审前 3 章
make review-range START=1 END=3

# 2. 再审前 10 章
make review-range START=1 END=10

# 3. 生成发布检查报告
make publish-check START=1 END=10

# 4. 打开报告
cat reviews/aggregate/publish_check_report.md
cat reviews/aggregate/revision_queue.md
```

判断规则：

```text
前 3 章：必须全部 publishable
前 10 章：至少 8 章 publishable，且不能有 rewrite_required
第 1 章：hook_score 必须 >= 8
第 1 章：reader_retention_score 必须 >= 8
第 3 章：ending_hook 必须强
```

上线前人工重点检查：

```text
1. 第 1 章前 300 字是否进入冲突；
2. 第 1 章是否有明确金手指或异常；
3. 第 2 章是否承接第 1 章，而不是开始讲设定；
4. 第 3 章是否形成追读/付费欲望；
5. 前 10 章是否每章都有本章功能；
6. 是否有明显 AI 腔；
7. 是否有平台风险。
```

---

## 13. 日常生产工作流

### 13.1 生成新章节

```bash
make generate-v2 CH=51
```

然后查看：

```bash
cat reviews/chapter_reviews/markdown/ch051_review.md
```

如果通过：

```text
人工阅读 generation/final_candidate/ch051_final_candidate.md
确认无问题后，再手动复制到 chapters/final/ 或发布后台。
```

如果不通过：

```bash
cat reviews/aggregate/revision_queue.md
```

然后根据 revision_tasks 修改。

### 13.2 批量审稿

```bash
make review-range START=51 END=55
```

### 13.3 每天选题/趋势扫描

先把手动观察写进：

```text
intelligence/raw/manual_notes/2026-05-02.md
```

格式：

```md
# 今日观察

## 榜单书名
- xxx
- xxx

## 高频钩子
- 开局 xxx
- 我能看见 xxx
- 全家 xxx

## 评论区情绪
- 读者喜欢主角果断
- 读者讨厌解释太多
- 读者期待女主更主动

## 可借鉴结构
- 第 1 章必须快速给金手指
- 第 3 章必须有第一次能力代价
```

再运行：

```bash
make scout-topics
```

---

## 14. 质量门禁标准

### 14.1 章节发布硬标准

```text
hook_score >= 7
conflict_score >= 7
character_consistency_score >= 8
continuity_score >= 8
ai_trace_score >= 7
reader_retention_score >= 7
platform_risk_score <= 5
fatal_issues 数量 = 0
```

### 14.2 前 3 章更严格

```text
hook_score >= 8
conflict_score >= 8
reader_retention_score >= 8
ai_trace_score >= 8
platform_risk_score <= 4
```

### 14.3 不可发布典型情况

```text
1. 中段超过 500 字无剧情推进；
2. 章节结尾只是抒情，没有钩子；
3. 主角没有主动选择；
4. 人物突然说出不像自己的话；
5. 能力规则被随意突破；
6. 大段解释设定；
7. AI 腔明显；
8. 内容存在平台风险。
```

---

## 15. Git 提交节奏

建议每完成一个稳定模块就提交一次。

```bash
git add config/novelops_v2.json intelligence/sources.yaml reviews/rubrics
 git commit -m "feat: add NovelOps v2 config and review rubrics"

 git add scripts/lib
 git commit -m "feat: add shared utilities for NovelOps v2"

 git add scripts/review_gate.py
 git commit -m "feat: add chapter review gate"

 git add scripts/publish_check.py
 git commit -m "feat: add publish readiness checker"

 git add scripts/generate_chapter_v2.py
 git commit -m "feat: add multi-stage chapter generation pipeline"

 git add scripts/topic_scout.py Makefile docs
 git commit -m "feat: add topic scout and NovelOps v2 commands"
```

注意：上面命令里的缩进如果复制到终端，去掉行首空格。

---

## 16. 两天时间表

### Day 1 上午：审稿基础设施

目标：先让审稿跑起来。

任务：

```text
1. 建分支
2. 新增目录
3. 新增 config
4. 新增 rubrics
5. 新增 scripts/lib
```

验收：

```bash
python -m py_compile scripts/lib/*.py
```

### Day 1 下午：Review Gate + Publish Check

任务：

```text
1. 实现 review_gate.py
2. 实现 publish_check.py
3. 更新 Makefile
4. 跑前 3 章审稿
5. 跑前 10 章审稿
```

验收：

```bash
make review-range START=1 END=3
make publish-check START=1 END=10
```

当天必须产出：

```text
reviews/aggregate/publish_check_report.md
reviews/aggregate/revision_queue.md
```

### Day 2 上午：Generate v2

任务：

```text
1. 实现 generate_chapter_v2.py
2. 跑第 51 章测试
3. 检查每阶段中间产物
4. 自动调用 review_gate
```

验收：

```bash
make generate-v2 CH=51
```

必须产出：

```text
generation/chapter_intent/ch051_intent.json
generation/scene_chain/ch051_scene_chain.json
generation/draft_v1/ch051_draft_v1.md
generation/draft_v2_commercial/ch051_draft_v2.md
generation/draft_v3_humanized/ch051_draft_v3.md
generation/final_candidate/ch051_final_candidate.md
reviews/chapter_reviews/markdown/ch051_review.md
```

### Day 2 下午：Topic Scout + 文档收口

任务：

```text
1. 实现 topic_scout.py
2. 加入 Makefile 命令
3. 写使用文档
4. 跑完整 smoke test
5. 提交 git
```

验收：

```bash
make scout-topics
make review-chapter CH=1
make publish-check START=1 END=3
```

---

## 17. Smoke Test 清单

开发完成后跑：

```bash
python -m py_compile scripts/lib/*.py
python -m py_compile scripts/review_gate.py
python -m py_compile scripts/publish_check.py
python -m py_compile scripts/generate_chapter_v2.py
python -m py_compile scripts/topic_scout.py

make review-chapter CH=1
make publish-check START=1 END=3
make scout-topics
```

检查输出：

```bash
ls reviews/chapter_reviews/json
ls reviews/chapter_reviews/markdown
ls reviews/aggregate
ls intelligence/reports
```

---

## 18. Definition of Done

本阶段完成标准：

```text
1. review_gate.py 可对单章输出 JSON + Markdown 审稿报告；
2. publish_check.py 可对前 10 章输出上线检查报告；
3. generate_chapter_v2.py 可生成第 51 章完整候选，并自动审稿；
4. topic_scout.py 可生成选题候选和评分表；
5. Makefile 命令可用；
6. 所有新增脚本不破坏已有章节；
7. 所有中间产物有明确保存位置；
8. 系统能明确拒绝低质量章节进入 final。
```

---

## 19. 本阶段最重要的判断

不要把系统成熟度定义为：

```text
它能自动写多少字。
```

要定义为：

```text
它能否稳定判断一章是否值得发布。
它能否指出哪里会损害留存。
它能否把外部市场信号转化成选题卡。
它能否让正文生成过程变得可控、可复盘、可修正。
```

真正成熟的 NovelOps 不是一个“写作机器人”，而是一个小型编辑部：

```text
能观察市场，
能规划章节，
能生产草稿，
能商业化改写，
能去 AI 腔，
能自动审稿，
能拒绝发布，
能记录修改原因，
能把真实反馈反哺下一轮生产。
```

---

## 20. 最终建议

你的当前阶段最优路线：

```text
先做 Review Gate，保上线质量；
再做 Generate v2，保后续产能；
最后做 Topic Scout，保长期选题能力。
```

两天内不要追求完整 SaaS，不要做漂亮 UI，不要做复杂数据库。  
只要这五个命令稳定可用，你的系统就会从“能生成小说”升级为“能运营小说生产”。

```bash
make scout-topics
make generate-v2 CH=51
make review-chapter CH=51
make review-range START=1 END=10
make publish-check START=1 END=10
```

