# 小说生产系统审计报告

## 当前目录结构

当前仓库根目录包含以下目标目录与文件：

```text
novel0/
├─ README.md
├─ bible/
│  ├─ 00_MASTER_CONTROL.md
│  ├─ 01_PROJECT_BIBLE.md
│  ├─ 02_WORLD_RULES.md
│  ├─ 03_CHARACTER_BIBLE.md
│  ├─ 05_CHAPTER_PRODUCTION_SPEC.md
│  ├─ 07_STYLE_AND_TONE.md
│  ├─ 08_CONTENT_SAFETY_AND_PLATFORM_RULES.md
│  ├─ 09_CONTINUITY_TRACKER.md
│  ├─ 10_CHAPTER_CARD_TEMPLATE.md
│  ├─ 11_REVIEW_CHECKLIST.md
│  ├─ 12_DAILY_PRODUCTION_WORKFLOW.md
│  ├─ 13_FORBIDDEN_DEVIATIONS.md
│  └─ 14_FIRST_30_CHAPTER_CARDS.md
├─ chapters/
│  ├─ 01 我看见她只剩三分钟可活.md
│  ├─ ...
│  └─ 30 我的寿命，只剩三十天.md
├─ outlines/
│  └─ 04_VOLUME_OUTLINE.md
├─ progress/
│  ├─ chapter_summary.md
│  └─ system_audit.md
└─ prompts/
   └─ generate_chapter.template
```

已确认目录状态：

- `bible/`：存在，含 13 个控制文件。
- `chapters/`：存在，含第 1-30 章正文文件。
- `outlines/`：存在，含六卷大纲文件。
- `progress/`：存在，含章节总结追踪文件，本审计文件新增于此。
- `prompts/`：存在，含章节生成模板。
- `README.md`：存在，定义项目定位、推荐结构、使用顺序和核心工作流。

命名映射关系：

- README 推荐的 `control/` 当前实际为 `bible/`。
- README 推荐的 `notes/` 当前实际拆为 `progress/`。
- README 使用顺序中的 `04_VOLUME_OUTLINE.md` 当前实际位置为 `outlines/04_VOLUME_OUTLINE.md`，不是 `bible/04_VOLUME_OUTLINE.md`。
- `bible/09_CONTINUITY_TRACKER.md` 是连续性记录模板，实际进度记录目前由 `progress/chapter_summary.md` 承担。

## 已有资产

当前 repo 已具备以下能力：

- 项目总控能力：`bible/00_MASTER_CONTROL.md` 定义核心卖点、完结结构、成长弧线、主题和单章硬性要求。
- 故事底层设定能力：`bible/01_PROJECT_BIBLE.md` 定义题材、商业公式、读者期待、核心世界观和核心冲突。
- 世界观与能力规则能力：`bible/02_WORLD_RULES.md` 定义寿命、财运、情缘、遗憾值、厄运倒计时、命运点、天平会和协议规则。
- 人物管理能力：`bible/03_CHARACTER_BIBLE.md` 定义主角、女主、配角、反派、父亲和补充角色。
- 全书宏观大纲能力：`outlines/04_VOLUME_OUTLINE.md` 已有六卷结构，覆盖 320-360 章目标。
- 单章生产规范能力：`bible/05_CHAPTER_PRODUCTION_SPEC.md` 定义章节参数、输入格式、输出格式、开头钩子、结尾钩子、节奏比例和禁用章节类型。
- 文风约束能力：`bible/07_STYLE_AND_TONE.md` 定义叙事视角、语言、节奏、数值面板、台词风格和禁止文风。
- 平台安全能力：`bible/08_CONTENT_SAFETY_AND_PLATFORM_RULES.md` 定义内容安全、敏感桥段替代方案和发布前检查。
- 连续性模板能力：`bible/09_CONTINUITY_TRACKER.md` 提供当前进度、人物状态、线索、协议、案件、关系和伏笔记录模板。
- 章节卡能力：`bible/10_CHAPTER_CARD_TEMPLATE.md` 提供标准章节卡；`bible/14_FIRST_30_CHAPTER_CARDS.md` 已提供前 30 章卡。
- 审稿能力：`bible/11_REVIEW_CHECKLIST.md` 提供基础、商业性、人物、设定、情节、过审和钩子强度检查。
- 日更流程能力：`bible/12_DAILY_PRODUCTION_WORKFLOW.md` 定义每日、每周、每月流程和阶段性目标。
- 防跑偏能力：`bible/13_FORBIDDEN_DEVIATIONS.md` 定义世界观、人物、剧情、能力、情感线、商业节奏、过审和完结禁止偏离项。
- 已生产正文资产：`chapters/` 已有第 1-30 章正文。
- 已有进度资产：`progress/chapter_summary.md` 已总结第 1-30 章，并含第一卷总结。
- 已有提示词资产：`prompts/generate_chapter.template` 可作为生成章节的基础提示。

## 缺失的核心文件

以下文件或能力目前缺失，建议后续逐项补齐：

- `progress/current_state.md`：缺少一个“当前可继续写作状态”文件。应记录当前章号、当前卷、真实主线进度、主角能力状态、命运点、关键人物状态、未解决危机和下一章入口。
- `progress/continuity_log.md`：缺少实际连续性台账。当前只有 `bible/09_CONTINUITY_TRACKER.md` 模板和 `progress/chapter_summary.md` 摘要，无法精确追踪道具、数值、伏笔、协议、伤病、时间线和人物位置。
- `progress/open_threads.md`：缺少未回收伏笔清单。长期连载需要明确每条伏笔的首次出现章节、预计回收卷、回收条件、风险等级。
- `progress/character_state.md`：缺少动态人物状态表。`03_CHARACTER_BIBLE.md` 是静态设定，不能替代“当前关系、已知信息、心理变化、能力变化、伤病状态”。
- `progress/episode_cases.md`：缺少单元案件台账。当前故事采用单元救赎结构，需要记录每个案件的受害者、协议类型、解决方式、获得线索、是否回流主线。
- `progress/volume_progress.md`：缺少分卷推进表。六卷大纲存在，但没有把每卷拆成“章节区间、阶段目标、阶段反派、关键反转、卷末爆点、不能提前揭露的信息”。
- `outlines/volume_01_repair_plan.md`：缺少第一卷修复方案。现有第 1-30 章已经提前完成大量终局内容，需要决定这些内容是重写为“第一卷小高潮”，还是锁定为短篇完结版本。
- `outlines/chapter_cards_031_060.md`：缺少第 31-60 章章节卡。长期连载不能从第 31 章直接自由生成。
- `prompts/review_chapter.template`：缺少审稿提示词模板。已有审稿清单，但没有可直接执行的审稿 prompt。
- `prompts/update_progress.template`：缺少更新进度提示词模板。需要把每章产出后的状态更新标准化。
- `prompts/create_chapter_card.template`：缺少章节卡生成提示词。后续应先生成章节卡，再生成正文。
- `README.md` 结构修订：README 推荐结构与当前实际结构不一致，后续应更新为当前 repo 真实结构，避免执行者按错误路径读取文件。
- `bible/06_*`：编号缺口存在。未必必须补文件，但需要明确 `06` 是否保留给“主线悬念/反派组织/分卷节奏”等能力，否则编号会造成维护疑惑。

## 当前最大风险

最大风险是“长期连载目标”和“现有 1-30 章实际完成度”发生结构冲突。

README 与总控目标是半年连载、70-80 万字、320-360 章、6 卷完结；但 `progress/chapter_summary.md` 中第 21-30 章已经完成了以下终局级事件：

- 命运点达到 10/10。
- 解锁最终能力“规则重写”。
- 作废所有协议。
- 父亲和 300 多个锚点获救。
- 天平会崩溃，顾咨询师被捕。
- 陈默和林见鹿确认关系、结婚生子。
- 陈默遗憾值降为 0，获得真正自由。
- 文件明确标注“第一卷完结”，但内容强度接近全书完结。

这会导致后续 31-360 章出现三个直接问题：

- 主线已被提前清算，后续缺少足够强的长期目标。
- 能力体系已提前到终局，后续升级空间不足。
- 情感线和父亲线已过早闭合，人物关系缺少持续张力。

落地处理建议：

- 先暂停继续生成正文。
- 先确定项目版本方向：短篇完结版，或长期连载修复版。
- 若选择长期连载修复版，第 21-30 章需要重新定位为“第一卷阶段性胜利”，不能作为全书终局。
- 第 30 章后的新章节必须建立在新的 `current_state.md` 和 `volume_progress.md` 上，否则继续写会扩大设定债务。

## 建议的最终目录结构

建议保留当前 `bible/` 命名，不强行改成 README 里的 `control/`，以降低迁移成本：

```text
novel0/
├─ README.md
├─ bible/
│  ├─ 00_MASTER_CONTROL.md
│  ├─ 01_PROJECT_BIBLE.md
│  ├─ 02_WORLD_RULES.md
│  ├─ 03_CHARACTER_BIBLE.md
│  ├─ 04_VOLUME_OUTLINE_INDEX.md
│  ├─ 05_CHAPTER_PRODUCTION_SPEC.md
│  ├─ 06_MAIN_THREAD_AND_MYSTERY_RULES.md
│  ├─ 07_STYLE_AND_TONE.md
│  ├─ 08_CONTENT_SAFETY_AND_PLATFORM_RULES.md
│  ├─ 09_CONTINUITY_TRACKER_TEMPLATE.md
│  ├─ 10_CHAPTER_CARD_TEMPLATE.md
│  ├─ 11_REVIEW_CHECKLIST.md
│  ├─ 12_DAILY_PRODUCTION_WORKFLOW.md
│  ├─ 13_FORBIDDEN_DEVIATIONS.md
│  └─ 14_FIRST_30_CHAPTER_CARDS.md
├─ outlines/
│  ├─ 04_VOLUME_OUTLINE.md
│  ├─ volume_01_repair_plan.md
│  ├─ volume_01_outline.md
│  ├─ volume_02_outline.md
│  ├─ ...
│  ├─ chapter_cards_031_060.md
│  ├─ chapter_cards_061_090.md
│  └─ ...
├─ chapters/
│  ├─ volume_01/
│  │  ├─ 001 我看见她只剩三分钟可活.md
│  │  └─ ...
│  ├─ volume_02/
│  └─ ...
├─ progress/
│  ├─ system_audit.md
│  ├─ current_state.md
│  ├─ chapter_summary.md
│  ├─ continuity_log.md
│  ├─ open_threads.md
│  ├─ character_state.md
│  ├─ episode_cases.md
│  ├─ volume_progress.md
│  └─ daily_log.md
└─ prompts/
   ├─ generate_chapter.template
   ├─ create_chapter_card.template
   ├─ review_chapter.template
   └─ update_progress.template
```

迁移原则：

- 不移动已存在正文，除非另开一次“结构整理任务”。
- 先补进度与控制文件，再决定是否按卷归档正文。
- 新正文从 31 章开始前，必须先有第 31-60 章章节卡。

## 下一步执行计划

建议按以下顺序执行，避免继续扩大结构风险：

1. 冻结正文生成：在完成状态修复前，不生成第 31 章，不改写已有正文。
2. 建立 `progress/current_state.md`：从第 1-30 章总结中抽取当前真实状态，并标注“短篇完结状态”和“长期连载可修复状态”的差异。
3. 建立 `outlines/volume_01_repair_plan.md`：决定第 21-30 章中哪些终局事件降级为误判、局部胜利、假崩溃、替身系统或阶段性副本。
4. 建立 `progress/open_threads.md`：列出父亲线、天平会线、顾沉舟线、沈微澜线、命运协议线、林见鹿寿命线的开启与回收状态。
5. 建立 `progress/character_state.md`：记录陈默、林见鹿、周野、程砚、许棠、沈微澜、顾沉舟、陈远山的当前状态。
6. 建立 `progress/continuity_log.md`：把命运点、寿命余额、协议、能力阶段、组织线索、关键道具统一成表。
7. 修订 `README.md`：把推荐结构改成当前真实结构，并明确每次生成前要读取的实际路径。
8. 生成 `outlines/chapter_cards_031_060.md`：只生成章节卡，不生成正文；每章必须承接修复后的第一卷状态。
9. 补齐 `prompts/review_chapter.template` 与 `prompts/update_progress.template`：让生成、审稿、状态更新三步分离。
10. 完成一次第 31 章试运行：先章节卡，后正文，再审稿，再更新进度。

## 不确定信息与假设

不确定信息：

- 第 1-30 章是否被作者视为正式正文，还是一次试生产样章。
- “第一卷完结”是否真的代表第一卷结束，还是误写成全书结局。
- 项目是否仍坚持 README 中的 320-360 章、70-80 万字目标。
- 是否允许后续重写第 21-30 章，或只能从第 31 章开始补救。
- `bible/06_*` 是否曾经存在但未纳入当前 repo。
- README 推荐结构是否是旧模板，还是未来仍想迁移到 `control/chapters/notes` 结构。
- `prompts/generate_chapter.template` 中的 Windows 绝对路径是否仍是实际生产环境路径。

当前审计假设：

- 不修改已有正文内容。
- 不生成新小说正文。
- 当前 `chapters/` 中第 1-30 章按“已有资产”处理，不判断文学质量。
- 当前目标仍是搭建长期连载小说生成系统，而不是把 30 章短篇版本直接收尾。
- 后续最优先任务不是写第 31 章，而是建立可持续追踪文件和修复第一卷终局化风险。

## 系统字段

- 文件职责：记录 repo 结构审计、风险识别和系统初始化依据。
- 更新频率：低，目录结构或生产系统规则发生重大变化时更新。
- 使用阶段：系统维护、流程调整、冷启动复盘。
- 禁止写入：章节正文、章节草稿、具体新剧情。
- 最近系统初始化：已建立前 8 万字冷启动目录骨架，包括章节工作区、bible 入口文件、outline 入口文件、progress 台账和 prompts 流程链。
