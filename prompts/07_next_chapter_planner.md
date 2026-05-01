# 07 下一章规划 Prompt

## 目标

基于当前定稿和进度文件，规划下一章队列项，不生成正文。

## 输入文件

- `progress/current_context.md`
- `progress/active_threads.md`
- `progress/timeline.md`
- `outlines/chapter_queue.md`
- 最新定稿：`chapters/final/`

## 输出内容

写入 `outlines/chapter_queue.md`：

- 下一章章号。
- 工作标题。
- 核心任务。
- 必须承接。
- 必须避免。
- 推荐章末钩子方向。

## 执行要求

- 不生成章节卡。
- 不生成正文。
- 不提前解决长期主线。
