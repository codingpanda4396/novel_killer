# 04 改稿 Prompt

## 目标

根据审稿记录修改草稿，输出新版本草稿或定稿候选。

## 输入文件

- 草稿：`chapters/drafts/`
- 审稿记录：`chapters/records/`
- 章节卡：`chapters/scene_cards/`

## 执行要求

- 只处理审稿记录中列明的问题。
- 不新增未登记主线。
- 不改变章节卡核心任务，除非先更新章节卡。
- 修改后标注版本号。

## 输出位置

- 修改版草稿：`chapters/drafts/第XXX章_草稿_v2.md`
- 通过后定稿：`chapters/final/第XXX章.md`
