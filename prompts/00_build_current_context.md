# 00 构建当前上下文 Prompt

## 目标

读取现有控制文件、进度文件和章节队列，更新 `progress/current_context.md`，为下一次章节生产提供唯一可信上下文。

## 输入文件

- `README.md`
- `bible/00_story_bible.md`
- `bible/01_characters.md`
- `bible/02_power_system.md`
- `bible/03_style_guide.md`
- `bible/04_forbidden_rules.md`
- `outlines/02_cold_start_0_80k.md`
- `outlines/chapter_queue.md`
- `progress/continuity_index.md`
- `progress/chapter_summary.md`
- `progress/active_threads.md`
- `progress/timeline.md`
- `progress/word_count.md`
- `progress/current_context.md`
- 必要时抽查对应前文正文：`chapters/*.md`

## 执行要求

- 不生成小说正文。
- 只总结当前必须承接的信息。
- 标注下一章是否允许进入章节卡阶段。
- 若发现主线、时间线、能力或人物状态冲突，先列为阻塞问题。
- 必须明确“前一章结尾”“当前人物状态”“当前能力阶段”“未回收伏笔”“禁止推翻的前文事实”。
- 若无法确认第 1-30 章是否作为正式前文承接，必须标注为阻塞，不允许进入章节卡阶段。

## 输出位置

- 更新 `progress/current_context.md`。
