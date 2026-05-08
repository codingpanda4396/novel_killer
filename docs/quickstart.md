# NovelOps CLI 快速启动

当前版本仅保留 CLI 模式，浏览器工作台和登录入口已经下线。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置

```bash
cp configs/novelops.example.json configs/novelops.json
cp configs/models.example.json configs/models.json
```

编辑 `configs/models.json` 填入 LLM 配置。`configs/novelops.json` 只保留 CLI 运行所需字段，例如：

```json
{
  "default_project": "life_balance",
  "db_path": "runtime/novelops.sqlite3",
  "require_manual_publish_confirmation": true
}
```

## 使用样例项目

```bash
.venv/bin/python -m novelops.cli --project life_balance status --readiness
.venv/bin/python -m novelops.cli --project life_balance check
.venv/bin/python -m novelops.cli --project life_balance ask "查看项目状态"
```

## 最小生产流程

```bash
.venv/bin/python -m novelops.cli --project life_balance plan-next 51
.venv/bin/python -m novelops.cli --project life_balance generate 51
.venv/bin/python -m novelops.cli --project life_balance review-chapter 51
.venv/bin/python -m novelops.cli --project life_balance ask "查看待修订章节"
.venv/bin/python -m novelops.cli --project life_balance pipeline status
```

`ask` 是辅助入口；生成、审稿、发布检查等关键操作优先使用明确 CLI 子命令。
