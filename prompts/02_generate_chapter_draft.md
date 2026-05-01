# 02 生成章节草稿 Prompt

## 目标

只根据已批准的章节卡生成单章草稿。

## 输入文件

- `progress/current_context.md`
- `progress/continuity_index.md`
- `progress/chapter_summary.md`
- 必要时抽查前文正文：`chapters/*.md`
- 对应章节卡：`chapters/scene_cards/`
- `bible/03_style_guide.md`
- `bible/04_forbidden_rules.md`

## 执行要求

- 一次只生成一章。
- 不生成下一章内容。
- 不修改 `progress/`。
- 不直接写入 `chapters/final/`。
- 草稿必须等待审稿。
- 草稿必须严格执行章节卡中的“前文连续性承接”和“不可改写的前文事实”。
- 草稿不得新增未登记的核心设定；如确需新增，只能在草稿末尾标注“待登记设定”，等待审稿确认。

## 输出位置

- `chapters/drafts/第XXX章_草稿.md`
