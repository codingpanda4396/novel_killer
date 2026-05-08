# NovelOps — 中文网文商业连载流水线

NovelOps 是一个面向中文网文的 **端到端商业连载流水线**，覆盖「市场需求发现 → 选题验证 → 故事资产构建 → 连载生产 → 多读者反馈 → 真实数据反哺」完整闭环。

---

## 核心架构

```
市场情报 (Radar)          故事资产 (Story)           连载生产 (Production)
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────────┐
│ market/         │      │ story/          │      │ production/         │
│  ├ raw/         │      │  ├ bible/       │      │  ├ generation/      │
│  ├ processed/   │──────│  ├ outlines/    │──────│  ├ reviews/         │
│  ├ reports/     │      │  └ state/       │      │  ├ corpus/          │
│  ├ demand_analysis│     │                 │      │  ├ publish/         │
│  └ reader_personas│     │                 │      │  └ experiments/     │
└─────────────────┘      └─────────────────┘      └─────────────────────┘
```

---

## 核心功能

| 模块 | 功能 | 状态 |
|------|------|------|
| **ProjectPaths** | 统一路径抽象，三段式 fallback（project.json → 新路径 → 旧路径） | ✅ |
| **LangGraph 流水线** | 11 节点多阶段章节生成，条件路由，人工审批点 | ✅ |
| **Desire 合成** | 聚合 Radar 信号 → demand_analysis / reader_personas / trope_library / competitor_patterns | ✅ |
| **Reader Panel** | 5 persona 并行审稿（快餐/情感/设定党/平台编辑/路人），dissent 检测 | ✅ |
| **商业审稿** | 规则 + LLM 双重审稿，平台适配评分 | ✅ |
| **NovelRadar** | 多平台榜单采集 + LLM 结构化分析（core_desire / hook / golden_finger / risk） | ✅ |
| **Experiment 闭环** | CSV 指标导入 → 决策评估 → 复盘报告 → demand_analysis 反哺 | ✅ |
| **记忆层** | ChromaDB 语义向量存储，增量索引 | ✅ |
| **Web Dashboard** | FastAPI 应用，AI 聊天助手 | ✅ |

---

## 项目结构

```
novel0/
├── configs/                         # 配置文件
├── runtime/                         # 运行时数据（SQLite, 不入 git）
├── scripts/
│   └── migrate_project_dirs.py      # 一次性目录迁移脚本
├── src/novelops/
│   ├── project_paths.py             # ProjectPaths 统一路径抽象
│   ├── desire/                      # 需求合成模块
│   │   ├── schemas.py               # DemandStatement, ReaderPersonaProfile, ...
│   │   ├── aggregators.py           # 纯 Python 信号聚合
│   │   ├── synthesizer.py           # DesireSynthesizer（2 次 LLM 调用）
│   │   ├── feedback.py              # 真实数据反哺
│   │   └── cli.py                   # analyze-demand 命令
│   ├── readers/                     # 读者团模块
│   │   ├── persona.py               # PersonaSpec + frontmatter 解析
│   │   ├── loader.py                # 加载 persona prompt 文件
│   │   └── panel.py                 # ReaderPanel（5 并行 persona）
│   ├── prompts/readers/             # 5 个 persona prompt（markdown + frontmatter）
│   ├── pipeline/                    # LangGraph 流水线
│   │   ├── graph.py                 # 状态图构建
│   │   ├── config.py                # 流水线配置（开关控制）
│   │   └── nodes/                   # 11 个节点
│   ├── radar/                       # NovelRadar 市场情报
│   ├── memory/                      # ChromaDB 记忆层
│   ├── db/                          # SQLModel 数据层
│   └── ...                          # 其他模块
├── projects/<id>/                   # 小说项目
│   ├── project.json                 # 项目配置（含 directories 映射）
│   ├── market/                      # 市场情报 + 需求分析
│   ├── story/                       # bible + outlines + state
│   └── production/                  # generation + reviews + corpus + publish
└── tests/                           # 153 个测试
```

---

## 快速开始

```bash
# 克隆 & 安装
git clone <repository-url>
cd novel0
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 配置
cp configs/models.example.json configs/models.json
# 编辑 configs/models.json 填入 LLM 配置

# 创建项目
python3 -m novelops.cli init-project my_novel --name "我的小说" --genre "都市异能"

# 查看项目状态
python3 -m novelops.cli status --project my_novel --readiness

# 运行测试
pytest tests/
```

---

## CLI 命令

### 项目管理

```bash
novelops init-project <id> --name "书名" --genre "题材"
novelops check --project <id>
novelops status --project <id> --readiness
novelops prepare-project --project <id>
```

### 章节生成

```bash
novelops generate <chapter> --project <id>
novelops review-chapter <chapter> --project <id>
novelops review-range <start> <end> --project <id>
novelops publish-check <start> <end> --project <id>
```

### 流水线

```bash
novelops pipeline run --project <id> --mode auto
novelops pipeline status --project <id>
```

### 需求分析

```bash
novelops analyze-demand --project <id> --window 14d
novelops analyze-demand --project <id> --force   # 忽略幂等性
```

### 实验管理

```bash
novelops experiment init <exp_id> --project <id> --platform fanqie --hypothesis "..."
novelops experiment import-metrics <exp_id> metrics.csv --project <id>
novelops experiment report <exp_id> --project <id>
novelops experiment decide <exp_id> --project <id>
```

### NovelRadar

```bash
novelops scout --project <id>
python3 -m novelops.radar collect <source> --platform fanqie
python3 -m novelops.radar analyze
```

### Web Dashboard

```bash
novelops serve --host 127.0.0.1 --port 8787
```

---

## 流水线节点

```
desire_synthesis (可选) → market_research → concept_design → outline
→ chapter_plan → draft → commercial_review → continuity_check → rewrite
→ panel_review (可选) → save
```

开关控制（`pipeline_config.json`）：

```json
{
  "desire_synthesis_enabled": false,
  "panel_review_enabled": false
}
```

---

## Reader Panel (5 Persona)

| Persona | 关注点 | 额外输入 |
|---------|--------|---------|
| `reader_fast_food` | 节奏、爽点、追读冲动 | 章节正文 |
| `reader_emotional` | 人物关系、情绪拉扯 | + state/character_state.md |
| `reader_setting_fan` | 金手指自洽、世界观 | + bible/02_power_system.md |
| `platform_editor` | 开篇留存、题材热度 | + project.json rubric |
| `cold_reader` | 路人前 3 章弃文风险 | 章节正文（隔离上下文） |

Panel 与 reviewer 互不替换：`chapter_NNN_review.json` 是商业编辑产物，`chapter_NNN_panel.json` 是读者团产物。

---

## 目录迁移

从旧结构迁移到新结构（一次性）：

```bash
# 预览
python3 scripts/migrate_project_dirs.py --project life_balance --dry-run

# 执行（自动备份）
python3 scripts/migrate_project_dirs.py --project life_balance --force

# 不备份
python3 scripts/migrate_project_dirs.py --project life_balance --force --no-backup
```

---

## 技术栈

| 层面 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| Web | FastAPI + Uvicorn + Jinja2 |
| 数据库 | SQLModel + SQLAlchemy (SQLite) |
| 向量数据库 | ChromaDB |
| LLM | OpenAI SDK（兼容 DeepSeek 等） |
| 工作流 | LangGraph |
| 数据采集 | Requests + BeautifulSoup4 + Playwright |
| 测试 | pytest (153 tests) |

---

## 许可证

[待定]
