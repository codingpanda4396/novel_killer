# 01 生成章节卡 Prompt

## 目标

基于 `progress/current_context.md` 和 `outlines/chapter_queue.md` 为单章生成章节卡。

## 输入文件

- `progress/current_context.md`
- `progress/continuity_index.md`
- `progress/chapter_summary.md`
- `progress/active_threads.md`
- `progress/timeline.md`
- `outlines/chapter_queue.md`
- `bible/00_story_bible.md`
- `bible/01_characters.md`
- `bible/02_power_system.md`
- `bible/03_style_guide.md`
- `bible/04_forbidden_rules.md`

## 输出模板

```markdown
# 第X章 章节卡

## 前文连续性承接

## 本章任务

## 上章承接

## 本章必须出现

## 本章禁止出现

## 不可改写的前文事实

## 场景列表

## 人物变化

## 主线推进

## 章末钩子

## 需要更新的记录
```

## 阻塞规则

- 如果无法写清“前文连续性承接”，不得生成章节卡。
- 如果本章任务会推翻前文事实，必须先回到 `prompts/00_build_current_context.md` 修复上下文。
- 章节卡不得通过“失忆、梦境、误会”等便利手段抹除前文事件，除非前文已有证据支持。

## 输出位置

- `chapters/scene_cards/第XXX章_章节卡.md`
