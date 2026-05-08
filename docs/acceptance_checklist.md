# Acceptance Checklist

NovelOps 当前收敛为纯 CLI 工具。历史浏览器工作台、登录入口和页面验收项已经下线，不再作为验收范围。

## CLI 验收项

- `.venv/bin/python -m novelops.cli --help` 不包含已下线的服务命令。
- `.venv/bin/python -m novelops.cli --project life_balance status --readiness` 可运行。
- `.venv/bin/python -m novelops.cli --project life_balance check` 可运行。
- `.venv/bin/python -m novelops.cli --project life_balance ask "查看项目状态"` 可运行。
- `.venv/bin/python -m pytest tests/` 可运行。
