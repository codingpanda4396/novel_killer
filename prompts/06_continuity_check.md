# 06 连续性检查 Prompt

## 目标

检查当前定稿与已有设定、人物、时间线、能力规则、活跃线索是否冲突。

## 输入文件

- `bible/00_story_bible.md`
- `bible/01_characters.md`
- `bible/02_power_system.md`
- `bible/04_forbidden_rules.md`
- `progress/current_context.md`
- `progress/continuity_index.md`
- `progress/chapter_summary.md`
- `progress/active_threads.md`
- `progress/timeline.md`
- 必要时抽查历史正文：`chapters/*.md`
- 最新定稿：`chapters/final/`

## 输出内容

- 冲突列表。
- 风险等级。
- 需要修复的文件。
- 是否允许规划下一章。
- 是否破坏第 1-30 章连续性。
- 是否出现人物状态跳跃、能力越级、时间线错乱、伏笔遗忘或主线提前终局。

## 判定规则

- 发现高风险冲突时，结论必须是“不允许规划下一章”。
- 冲突不能通过忽略前文解决，只能通过改稿、补记录或重建当前上下文解决。
- 如果新章对前文作出反转解释，必须列明前文依据和解释方式。

## 输出位置

- `chapters/records/第XXX章_连续性检查.md`
