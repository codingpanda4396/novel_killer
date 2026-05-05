# NovelOps 现状与理想架构差距分析

## 一、当前系统现状

### 1.1 已实现的核心功能

✅ **基础架构**
- Python 单体系统 + FastAPI (web.py)
- SQLite/JSON 混合存储（项目配置用 JSON，部分数据结构化）
- Markdown 文件系统（章节、大纲、设定）
- LLM 集成（DeepSeek + Claude via RightCode）

✅ **核心模块**
- `generator.py` - 章节生成
- `reviewer.py` - 审稿系统
- `planner.py` - 章节规划
- `scout.py` - 选题情报（基础版，仅手动笔记）
- `continuity.py` - 连续性检查
- `indexer.py` - 索引构建
- `orchestrator.py` - 工作流编排
- `cli.py` - 命令行入口
- `web.py` - Web 界面

✅ **已有目录结构**
```
src/novelops/
├── agents/          # 空目录
├── workflows/       # 空目录
├── storage/         # 空目录
├── cli/             # CLI 相关
├── core/            # 核心逻辑
├── services/        # 服务层
├── utils/           # 工具函数
└── templates/       # Web 模板
```

### 1.2 当前技术栈

- **语言**: Python 3.8+
- **Web 框架**: FastAPI (web.py)
- **存储**: JSON 文件 + Markdown
- **LLM**: OpenAI SDK (兼容 DeepSeek + RightCode)
- **依赖管理**: pip + requirements.txt
- **CLI**: argparse
- **测试**: pytest

---

## 二、理想架构要求

### 2.1 核心技术栈

```
Python + FastAPI + SQLite/PostgreSQL + Playwright + LLM API + Markdown + ChromaDB + LangGraph
```

### 2.2 推荐模块结构

```
novelops/
  collectors/      # 热点采集 - ❌ 缺失
  analyzers/       # 热点分析 - ⚠️ 部分实现（scout.py 太简单）
  models/          # 数据模型 - ⚠️ 部分实现（schemas.py）
  prompts/         # prompt 模板 - ✅ 已有（configs/prompts/）
  workflows/       # LangGraph/状态机 - ⚠️ 目录存在但为空
  memory/          # 向量库与检索 - ❌ 缺失（indexer.py 不是向量库）
  generators/      # 大纲/章节生成 - ✅ 已有（generator.py）
  reviewers/       # 商业审稿 - ✅ 已有（reviewer.py）
  feedback/        # 数据反馈 - ❌ 缺失
  cli/             # 命令行入口 - ✅ 已有
  api/             # FastAPI - ✅ 已有（web.py）
```

---

## 三、差距分析

### 3.1 缺失的核心功能 ❌

#### 1. **热点采集系统（collectors/）**

**现状**: 
- `scout.py` 只能读取手动笔记，无自动采集能力
- 无 Playwright 集成
- 无 RSS/API 采集
- 无平台榜单抓取

**理想状态**:
```python
collectors/
  ├── __init__.py
  ├── base.py           # 采集器基类
  ├── playwright_collector.py  # 动态网页采集
  ├── rss_collector.py         # RSS 订阅
  ├── api_collector.py         # 平台 API
  └── manual_collector.py      # 手动导入（已有）
```

**差距**: 完全缺失自动化采集能力

---

#### 2. **向量数据库/知识库（memory/）**

**现状**:
- `indexer.py` 只是简单的文本索引
- 无向量检索能力
- 无语义搜索
- 无历史章节召回

**理想状态**:
```python
memory/
  ├── __init__.py
  ├── vector_store.py   # ChromaDB/Qdrant 封装
  ├── retriever.py      # 检索逻辑
  └── embeddings.py     # 向量化
```

**用途**:
- 生成章节前自动召回相关设定
- 检索历史章节避免重复
- 语义搜索人物/情节

**差距**: 完全缺失向量检索能力

---

#### 3. **工作流编排（workflows/）**

**现状**:
- `orchestrator.py` 有基础状态机
- `workflows/` 目录为空
- 无 LangGraph 集成

**理想状态**:
```python
workflows/
  ├── __init__.py
  ├── chapter_generation.py  # 章节生成流水线
  ├── review_pipeline.py     # 审稿流水线
  └── market_research.py     # 市场调研流水线
```

**差距**: 缺少结构化的工作流定义

---

#### 4. **数据反馈系统（feedback/）**

**现状**: 完全缺失

**理想状态**:
```python
feedback/
  ├── __init__.py
  ├── metrics.py        # 数据指标收集
  ├── analytics.py      # 分析报告
  └── dashboard.py      # 数据看板
```

**差距**: 无法追踪发布后的数据表现

---

### 3.2 需要增强的功能 ⚠️

#### 1. **热点分析（analyzers/）**

**现状**: `scout.py` 功能太简单，只能打分

**需要增强**:
- LLM 结构化分析（提取类型、核心欲望、金手指等）
- 市场趋势分析
- 竞品分析

---

#### 2. **数据模型（models/）**

**现状**: `schemas.py` 有基础数据类

**需要增强**:
- 使用 SQLModel 替代纯 dataclass
- 支持数据库持久化
- 添加更多业务模型

---

#### 3. **CLI 体验**

**现状**: 使用 argparse，功能完整但体验一般

**建议升级**:
```bash
# 当前
python3 -m novelops.cli ask "查看状态"

# 理想（使用 Typer + Rich）
novelops trend collect
novelops trend analyze
novelops story create
novelops chapter plan 001
novelops chapter write 001
```

---

### 3.3 已实现但可优化的功能 ✅

1. **章节生成** (`generator.py`) - 功能完整，可考虑模块化
2. **审稿系统** (`reviewer.py`) - 功能完整，可增加更多维度
3. **Web 界面** (`web.py`) - 基础功能完整，可优化 UI

---

## 四、开发优先级建议

### 阶段 1: 补齐核心缺失（2-3 周）

#### P0 - 向量知识库 🔥

**为什么优先**:
- 直接提升生成质量
- 避免设定冲突
- 减少人工检查成本

**实现步骤**:
1. 安装 ChromaDB: `pip install chromadb`
2. 创建 `src/novelops/memory/` 模块
3. 实现向量存储和检索
4. 在 `generator.py` 中集成召回逻辑

**预期收益**: 章节连贯性提升 30%+

---

#### P0 - 热点采集系统 🔥

**为什么优先**:
- 市场驱动的核心功能
- 决定选题方向

**实现步骤**:
1. 安装 Playwright: `pip install playwright && playwright install`
2. 创建 `src/novelops/collectors/` 模块
3. 实现番茄/抖音榜单采集（先做半自动）
4. 结构化存储到数据库

**预期收益**: 选题效率提升 5 倍

---

#### P1 - 数据库迁移

**当前问题**: JSON 文件不适合复杂查询

**实现步骤**:
1. 安装 SQLModel: `pip install sqlmodel`
2. 设计数据表结构
3. 迁移现有 JSON 数据
4. 保留 Markdown 文件系统（章节正文）

**数据表设计**:
```sql
hot_items          -- 热点原始数据
market_reports     -- 热点分析报告
story_projects     -- 小说项目
chapter_plans      -- 章节计划
chapters           -- 章节元数据（正文仍用 Markdown）
reviews            -- 审稿报告
feedback_logs      -- 发布后数据
```

---

### 阶段 2: 增强现有功能（1-2 周）

#### P1 - LangGraph 工作流

**实现步骤**:
1. 安装: `pip install langgraph`
2. 将 `orchestrator.py` 的状态机改为 LangGraph
3. 定义清晰的节点和边

**示例流程**:
```python
market_research_node
↓
concept_design_node
↓
outline_node
↓
chapter_plan_node
↓
draft_node
↓
commercial_review_node
↓
continuity_check_node
↓
rewrite_node
↓
save_node
```

---

#### P2 - 热点分析增强

**实现步骤**:
1. 创建 `src/novelops/analyzers/` 模块
2. 使用 LLM 结构化分析热点
3. 输出 JSON Schema 格式

**输出示例**:
```json
{
  "genre": "仙侠",
  "core_desire": "被压迫后的逆袭",
  "hook": "废柴少年觉醒神秘炉鼎",
  "golden_finger": "吞噬灵根升级",
  "reader_emotion": ["爽", "期待", "打脸"],
  "risk": "开局同质化严重"
}
```

---

#### P2 - CLI 体验升级

**实现步骤**:
1. 安装: `pip install typer rich`
2. 重构 `cli.py` 使用 Typer
3. 添加 Rich 输出美化

---

### 阶段 3: 数据闭环（1 周）

#### P2 - 数据反馈系统

**实现步骤**:
1. 创建 `src/novelops/feedback/` 模块
2. 收集发布后数据（阅读量、留存、评论）
3. 生成分析报告
4. 反馈到选题和生成策略

---

## 五、具体技术实现建议

### 5.1 向量知识库实现

```python
# src/novelops/memory/vector_store.py
import chromadb
from chromadb.config import Settings

class NovelMemory:
    def __init__(self, project_path):
        self.client = chromadb.PersistentClient(
            path=str(project_path / ".chroma")
        )
        self.collection = self.client.get_or_create_collection(
            name="novel_memory",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_chapter(self, chapter_num, text, metadata):
        """添加章节到向量库"""
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[f"chapter_{chapter_num:03d}"]
        )
    
    def recall_context(self, query, n_results=5):
        """召回相关上下文"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
```

**集成到生成流程**:
```python
# 在 generator.py 中
memory = NovelMemory(project_path)

# 生成前召回
context = memory.recall_context(
    f"主角：{protagonist}，当前情节：{current_plot}",
    n_results=5
)

# 将 context 加入 prompt
```

---

### 5.2 热点采集实现

```python
# src/novelops/collectors/playwright_collector.py
from playwright.sync_api import sync_playwright

class TomatoCollector:
    def collect_ranking(self, category="仙侠"):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 访问番茄榜单
            page.goto(f"https://fanqienovel.com/rank/{category}")
            
            # 提取数据
            items = page.query_selector_all(".rank-item")
            results = []
            for item in items:
                title = item.query_selector(".title").inner_text()
                author = item.query_selector(".author").inner_text()
                intro = item.query_selector(".intro").inner_text()
                results.append({
                    "title": title,
                    "author": author,
                    "intro": intro,
                    "platform": "fanqie",
                    "category": category
                })
            
            browser.close()
            return results
```

---

### 5.3 数据库模型

```python
# src/novelops/models/hot_item.py
from sqlmodel import SQLModel, Field
from datetime import datetime

class HotItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    platform: str
    title: str
    author: str
    intro: str
    category: str
    rank: int
    collected_at: datetime = Field(default_factory=datetime.now)

class MarketReport(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hot_item_id: int = Field(foreign_key="hotitem.id")
    genre: str
    core_desire: str
    hook: str
    golden_finger: str
    reader_emotions: str  # JSON string
    risk_assessment: str
    score: float
    analyzed_at: datetime = Field(default_factory=datetime.now)
```

---

## 六、最小可行路径（MVP）

如果时间有限，按这个顺序做：

### 第 1 周
1. ✅ 安装 ChromaDB
2. ✅ 实现向量知识库
3. ✅ 集成到章节生成

### 第 2 周
4. ✅ 安装 Playwright
5. ✅ 实现半自动热点采集（人工提供链接，系统解析）
6. ✅ LLM 结构化分析

### 第 3 周
7. ✅ SQLModel 数据库迁移
8. ✅ 数据表设计和迁移脚本

### 第 4 周（可选）
9. ⚠️ LangGraph 工作流重构
10. ⚠️ Typer CLI 升级
11. ⚠️ 数据反馈系统

---

## 七、依赖更新

需要添加到 `pyproject.toml`:

```toml
dependencies = [
    "openai>=1.0.0",
    "tiktoken>=0.5.0",
    "python-dotenv>=1.0.0",
    "requests>=2.31.0",
    "pyyaml>=6.0",
    # 新增
    "chromadb>=0.4.0",           # 向量数据库
    "playwright>=1.40.0",        # 网页采集
    "sqlmodel>=0.0.14",          # 数据库 ORM
    "langgraph>=0.0.20",         # 工作流编排
    "typer[all]>=0.9.0",         # CLI 框架
    "rich>=13.0.0",              # 终端美化
]
```

---

## 八、总结

### 核心差距

1. **❌ 完全缺失**: 热点采集、向量知识库、数据反馈
2. **⚠️ 需要增强**: 热点分析、工作流编排、数据模型
3. **✅ 已实现**: 章节生成、审稿系统、Web 界面

### 最高 ROI 行动

**立即做**:
1. 向量知识库（ChromaDB）- 提升生成质量
2. 热点采集（Playwright）- 市场驱动选题

**尽快做**:
3. 数据库迁移（SQLModel）- 支撑复杂查询
4. 热点分析增强（LLM 结构化）- 提取市场洞察

**可以延后**:
5. LangGraph 重构 - 现有 orchestrator 够用
6. CLI 美化 - 不影响核心功能
7. 数据反馈 - 需要先有发布数据

### 一句话建议

**先做向量知识库和热点采集，这两个功能会立即提升系统的实用价值。数据库迁移和工作流重构可以边用边优化。**

