# NovelOps - 中文网文多平台商业实验系统

NovelOps 是一个面向中文网文的 **多平台商业实验闭环系统**，支持同一选题在不同平台（番茄/起点/手动平台）进行可复盘的商业测试。集成了小说生成流水线、市场情报采集引擎（NovelRadar）、审稿质量门禁、实验管理和决策系统，为网文创作者提供从选题到商业化验证的全流程支持。

---

## 核心定位

**不是单一平台工具，而是多平台商业实验系统。**

- 支持番茄（免费阅读）、起点（付费连载）、手动平台（任意平台数据录入）
- 每本书、每个平台、每次发布测试都视为一个实验
- 核心目标：让你能对同一个选题在不同平台形成可复盘的实验

---

## 核心功能

| 模块 | 功能 |
|------|------|
| **平台抽象** | 统一平台配置，支持番茄/起点/手动平台，可扩展 |
| **实验管理** | 实验生命周期管理（planning→drafting→publishing→retrospective） |
| **Metrics 导入** | 多平台指标数据导入，CSV 超集字段兼容 |
| **决策系统** | 基于数据的自动决策（CONTINUE/REVISE/KILL） |
| **审稿系统** | 规则+LLM 双重审稿，平台适配评分 |
| **NovelRadar** | 多平台榜单采集与分析（番茄/起点/纵横/晋江/潇湘） |
| **生成流水线** | 基于 LangGraph 的多阶段章节生成 |
| **记忆层** | ChromaDB 语义向量存储，增强上下文连贯性 |
| **Web Dashboard** | FastAPI 应用，AI 聊天助手，SSE 实时进度推送 |

---

## 技术栈

| 层面 | 技术 |
|------|------|
| 语言 | Python 3.8+（推荐 3.10） |
| Web 框架 | FastAPI + Uvicorn + Jinja2 |
| 数据库 | SQLModel + SQLAlchemy（SQLite） |
| 向量数据库 | ChromaDB |
| LLM 集成 | OpenAI SDK（兼容 DeepSeek/RightCode 等） |
| 工作流引擎 | LangGraph |
| 数据采集 | Requests + BeautifulSoup4 + Playwright |
| 测试 | pytest |

---

## 快速开始

### 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd novel0

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 配置模型

```bash
# 复制模型配置模板
cp configs/models.example.json configs/models.json
# 编辑 configs/models.json 配置 LLM 模型
```

### 查看支持的平台

```bash
# 列出所有平台
python3 -m novelops.cli platform list
# 输出：fanqie, qidian, manual
```

### 创建实验

```bash
# 初始化新实验
python3 -m novelops.cli experiment init qidian_xuanhuan_001 \
  --project my_project \
  --platform qidian \
  --hypothesis "测试起点玄幻新设定是否能获得收藏和追读"

# 列出项目的所有实验
python3 -m novelops.cli experiment list --project my_project
```

### 导入数据

```bash
# 导入指标数据
python3 -m novelops.cli experiment import-metrics qidian_xuanhuan_001 metrics.csv \
  --project my_project

# 生成实验报告
python3 -m novelops.cli experiment report qidian_xuanhuan_001 --project my_project

# 执行决策评估
python3 -m novelops.cli experiment decide qidian_xuanhuan_001 --project my_project
```

---

## 项目结构

```
novel0/
├── src/novelops/                    # 核心源码
│   ├── cli.py                       # CLI 入口
│   ├── web.py                       # FastAPI Web 应用
│   ├── platforms.py                 # 平台配置管理
│   ├── experiment.py                # 实验管理模块
│   ├── reviewer.py                  # 审稿系统（支持平台适配）
│   ├── generator.py                 # 章节生成器
│   ├── pipeline/                    # LangGraph 流水线
│   ├── radar/                       # NovelRadar 市场情报
│   ├── memory/                      # ChromaDB 记忆层
│   └── db/                          # 数据库层
├── configs/                         # 配置文件
│   ├── platforms.example.json       # 平台配置模板
│   ├── models.json                  # LLM 模型配置
│   └── prompts/                     # Prompt 模板
├── projects/                        # 小说项目目录
│   └── <project_id>/
│       ├── experiments/             # 实验目录
│       │   └── <experiment_id>/
│       │       ├── experiment.json  # 实验元数据
│       │       ├── hypothesis.md    # 假设文档
│       │       ├── market_samples.md
│       │       ├── concept_package.md
│       │       ├── chapters/
│       │       ├── metrics.csv
│       │       ├── review_report.md
│       │       └── retrospective.md
│       ├── bible/                   # 项目圣经文档
│       ├── corpus/                  # 语料库
│       └── project.json             # 项目配置
├── tests/                           # 测试
└── runtime/                         # 运行时数据（SQLite）
```

---

## 平台配置

平台配置文件：`configs/platforms.json`（不存在时回退到 `platforms.example.json`）

```json
{
  "fanqie": {
    "name": "番茄小说",
    "business_model": "free_reading",
    "primary_metrics": ["impressions", "reads", "favorites", "follows", "comments", "income"],
    "review_focus": ["开篇钩子", "低认知成本", "爽点密度", "章尾追读"],
    "risk_focus": ["题材同质化", "内容审核", "免费阅读转化"]
  },
  "qidian": {
    "name": "起点中文网",
    "business_model": "paid_serial",
    "primary_metrics": ["views", "collections", "recommendations", "comments", "chapter_follows", "income"],
    "review_focus": ["设定新意", "文风稳定", "长期主线", "读者期待管理"],
    "risk_focus": ["同类竞争强", "开篇慢热", "读者挑剔", "签约门槛"]
  },
  "manual": {
    "name": "手动平台",
    "business_model": "unknown",
    "primary_metrics": [],
    "review_focus": [],
    "risk_focus": []
  }
}
```

---

## 实验状态流转

```
planning → drafting → reviewing → publishing → collecting_data → retrospective
    ↓           ↓          ↓            ↓              ↓
  killed      killed     killed       killed         continued
```

**决策值**：
- `CONTINUE`：有明显正反馈，继续投入
- `REVISE`：有曝光但转化弱，需要调整
- `KILL`：连续数据弱且审稿低，停止投入
- `UNKNOWN`：数据不足，无法判断

---

## Metrics CSV 格式

统一 CSV 字段为超集，没有的数据留空：

```csv
date,platform,book_id,chapter_start,chapter_end,impressions,views,reads,read_rate,collections,favorites,recommendations,comments,follows,chapter_follows,income,notes
2026-05-01,qidian,book001,1,10,5000,3000,2000,0.67,150,80,50,30,20,10,15.5,第一周数据
```

**平台主要字段**：
- 番茄：`impressions`, `reads`, `favorites`, `comments`, `follows`, `income`
- 起点：`views`, `collections`, `recommendations`, `comments`, `chapter_follows`, `income`

---

## CLI 命令参考

### 平台管理

```bash
# 列出所有平台
python3 -m novelops.cli platform list
```

### 实验管理

```bash
# 初始化新实验
python3 -m novelops.cli experiment init <experiment_id> \
  --project <project_id> \
  --platform <platform_id> \
  --hypothesis "<假设描述>"

# 列出项目的所有实验
python3 -m novelops.cli experiment list --project <project_id>

# 导入指标数据
python3 -m novelops.cli experiment import-metrics <experiment_id> <csv_file> \
  --project <project_id>

# 生成实验报告
python3 -m novelops.cli experiment report <experiment_id> --project <project_id>

# 执行决策评估
python3 -m novelops.cli experiment decide <experiment_id> --project <project_id>

# 生成平台适配概念包
python3 -m novelops.cli experiment concept-from-radar <experiment_id> --project <project_id>
```

### 项目管理

```bash
# 创建新项目
python3 -m novelops.cli init-project <project_id> --name "书名" --genre "玄幻"

# 查看项目状态
python3 -m novelops.cli status --project <project_id>

# 准备项目（LLM 生成设定和大纲）
python3 -m novelops.cli prepare-project --project <project_id>
```

### 章节生成与审稿

```bash
# 生成章节
python3 -m novelops.cli generate <chapter_number> --project <project_id>

# 审稿单章
python3 -m novelops.cli review-chapter <chapter_number> --project <project_id>

# 批量审稿
python3 -m novelops.cli review-range <start> <end> --project <project_id>

# 发布前检查
python3 -m novelops.cli publish-check <start> <end> --project <project_id>
```

### NovelRadar 市场情报

```bash
# 采集数据
python3 -m novelops.radar collect <source> --platform <platform>

# 分析热点
python3 -m novelops.radar analyze

# 生成报告
python3 -m novelops.radar report
```

### Web 服务

```bash
# 启动 Web Dashboard
python3 -m novelops.cli serve --host 127.0.0.1 --port 8787
```

---

## 审稿系统

### 平台适配评分

审稿时可指定平台，获得平台相关的评分维度：

- `opening_hook_score`：开篇钩子
- `conflict_score`：冲突设计
- `payoff_score`：爽点释放
- `retention_score`：追读动力
- `novelty_score`：设定新意
- `long_term_arc_score`：长期主线潜力
- `platform_risk_score`：平台风险

### 七维基础评分

- `hook`：钩子强度
- `conflict`：冲突质量
- `consistency`：一致性
- `continuity`：连续性
- `ai_trace`：AI 痕迹（越低越好）
- `retention`：留存潜力
- `risk`：风险指数

---

## 示例实验流程

### 1. 创建实验

```bash
python3 -m novelops.cli experiment init qidian_xuanhuan_001 \
  --project my_novel \
  --platform qidian \
  --hypothesis "验证玄幻新设定在起点是否有收藏和追读潜力"
```

### 2. 生成内容

```bash
# 生成 10 章
for i in {1..10}; do
  python3 -m novelops.cli generate $i --project my_novel
done
```

### 3. 导入数据

```bash
# 准备 metrics.csv 后导入
python3 -m novelops.cli experiment import-metrics qidian_xuanhuan_001 metrics.csv \
  --project my_novel
```

### 4. 分析决策

```bash
# 生成报告
python3 -m novelops.cli experiment report qidian_xuanhuan_001 --project my_novel

# 执行决策
python3 -m novelops.cli experiment decide qidian_xuanhuan_001 --project my_novel
# 输出：Decision: CONTINUE / REVISE / KILL / UNKNOWN
```

---

## 配置说明

### 环境变量 (.env)

```bash
OPENAI_API_KEY=your-api-key
DEEPSEEK_API_KEY=your-api-key
NOVELOPS_SECRET_KEY=your-session-secret
```

### 模型配置 (configs/models.json)

```json
{
  "default": {
    "provider": "openai",
    "model": "gpt-4",
    "api_key": "your-api-key"
  },
  "deepseek": {
    "provider": "deepseek",
    "model": "deepseek-chat",
    "api_key": "your-api-key",
    "base_url": "https://api.deepseek.com"
  }
}
```

---

## 合规边界

- ✅ 允许：公开榜单、公开评论、人工录入数据
- ❌ 禁止：付费正文、绕过登录、破解接口

---

## 许可证

[待定]

---

## 贡献

欢迎提交 Issue 和 Pull Request。
