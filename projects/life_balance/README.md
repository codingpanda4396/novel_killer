# 我能看见人生余额开局救下白月光

这是 NovelOps 仓库内置的示例项目，项目 ID 为 `life_balance`，题材为都市异能悬疑爽文。

有效资产位于本目录：

- `project.json`：项目元数据、阈值、规划策略和本项目 rubric。
- `bible/`：世界观、人物、风格、禁写规则。
- `outlines/`：总纲、卷纲、章节队列。
- `corpus/volume_01/`：第 1-50 章参考语料。
- `generation/`：章节生成流水线产物。
- `reviews/`：审稿报告和人工修订队列。

示例项目不再是代码默认假设。代码只读取项目配置、bible、outlines、state 和 rubric；与“余额、寿命、命运、代价、规则、天平”等相关的评分关键词保存在本项目 `project.json.rubric` 中。
