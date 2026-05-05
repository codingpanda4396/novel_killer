# NovelRadar - 中文网文需求情报引擎

NovelRadar 是一个面向中文网文的商业化情报采集与分析系统，用于采集、整理、分析市场需求信号，输出"选题机会报告"。

## 核心功能

- **数据采集**：支持番茄小说公开榜单、CSV/JSON 导入
- **规则分析**：自动识别题材、金手指、爽点、风险
- **竞品分析**：分析同题材竞品，发现差异化机会
- **商业评分**：量化评估选题潜力（番茄偏好）
- **报告生成**：输出可执行的选题机会报告

## 快速开始

```bash
# 一键运行完整流程
python3 -m novelops.radar run-sample
```

预期输出：
```
=== NovelRadar Sample Pipeline ===
[1/4] Database initialized
[2/4] Imported 10 sample signals
[3/4] Analyzed 10 signals
[4/4] Report generated: runtime/radar/reports/topic_report_YYYYMMDD_HHMM.md
=== Pipeline Complete ===
```

## CLI 命令

```bash
# 初始化数据库
python3 -m novelops.radar init

# 导入番茄样本数据
python3 -m novelops.radar import-fanqie --sample

# 导入 CSV 数据
python3 -m novelops.radar import-csv data.csv --platform 番茄

# 分析数据
python3 -m novelops.radar analyze

# 生成报告
python3 -m novelops.radar report
```

## 模块结构

```
src/novelops/radar/
├── models.py              # 数据模型
├── storage.py             # SQLite 存储层
├── analyzer.py            # 规则分析器
├── competitor.py          # 竞品分析器
├── scoring.py             # 商业评分
├── report.py              # 报告生成
├── cli.py                 # CLI 命令
├── collectors/
│   ├── base.py            # 采集器基类
│   ├── csv_collector.py   # CSV 采集器
│   ├── json_collector.py  # JSON 采集器
│   └── fanqie_collector.py # 番茄采集器
└── prompts/
    └── topic_analysis.md  # LLM prompt（预留）
```

## 评分模型

```
final_score = 
    热度(35%) + 平台适配度(25%) + 读者欲望(20%)
    + 写作容易度(10%) + 趋势加成(10%) - 竞争惩罚
```

番茄平台适配度：
- 高适配（80-95）：都市重生、赘婿逆袭、高武觉醒、末世囤货
- 中高适配（65-79）：仙侠修真、年代文、女频爽文
- 低适配（<50）：硬科幻、纯文学

## 报告示例

生成的报告包含：
- 总体观察（样本数、高潜力题材）
- 题材热度排行表格
- 推荐测试选题 Top5（含开篇钩子、故事种子）
- 竞品分析（差异化机会）
- 创作建议

## 合规边界

- ✅ 允许：公开榜单、公开评论、人工录入数据
- ❌ 禁止：付费正文、绕过登录、破解接口

## 后续扩展

- 短期：接入番茄真实榜单（Playwright）、LLM 自动分析
- 中期：Web Dashboard、趋势分析
- 长期：作品数据反馈闭环、A/B 测试框架

## 依赖

仅使用 Python 标准库（sqlite3, json, pathlib, dataclasses），无额外依赖。
