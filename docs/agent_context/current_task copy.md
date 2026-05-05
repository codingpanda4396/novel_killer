当前任务：实现 NovelOps v0.2 Orchestrator 主控状态机。

范围：
- 新增 novelops/orchestrator.py
- 不删除现有 generator.py / reviewer.py / assistant.py
- 不重构 Web 页面
- 不接入 Billing
- 不接入 Analytics
- 增加 unittest 覆盖状态判断和下一步动作推荐

验收：
- 现有测试全部通过
- 新增 Orchestrator 可根据项目准备度、章节队列、修订队列判断 next_action
- 不破坏现有 CLI 和 Web