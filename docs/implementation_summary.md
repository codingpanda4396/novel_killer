# Implementation Summary

NovelOps 当前实现目标是 CLI-only。本轮清理后，项目入口集中在 `src/novelops/cli.py` 及相关业务模块。

保留能力：

- 项目管理与路径抽象
- 章节规划、生成、审稿、发布检查
- 自然语言辅助命令 `ask`
- Pipeline、Desire、Experiment、Radar、Memory
- 本地 SQLite 索引和项目数据

已下线能力：

- 浏览器工作台
- 页面登录与会话
- 页面模板和页面任务追踪
- 服务命令
