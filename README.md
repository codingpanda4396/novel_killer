# NovelOps - 中文网文 AI 辅助创作与商业化情报系统

NovelOps 是一个面向中文网文的 **AI 辅助创作与商业化情报平台**，集成了小说生成流水线、市场情报采集引擎（NovelRadar）、审稿质量门禁、Web Dashboard 和自然语言助手，为网文创作者提供从选题到成稿的全流程智能化支持。

---

## 核心功能

| 模块 | 功能 |
|------|------|
| **小说生成流水线** | 基于 LangGraph 的多阶段章节生成（意图→场景→草稿→改稿→润色） |
| **NovelRadar** | 多平台榜单采集与分析（番茄/起点/纵横/晋江/潇湘） |
| **审稿系统** | 规则+LLM 双重审稿，七维评分，自动修订 |
| **记忆层** | ChromaDB 语义向量存储，增强生成上下文连贯性 |
| **Web Dashboard** | FastAPI 应用，AI 聊天助手，SSE 实时进度推送 |
| **连续性追踪** | 自动生成时间线、角色状态、活跃线索 |

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
| 测试 | pytest + pytest-cov |
| CI/CD | GitHub Actions |

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

### 启动 Web 服务

```bash
# 启动 FastAPI 服务
python3 -m novelops.web

# 访问 http://localhost:8000
```

### 使用 CLI

```bash
# 创建新项目
python3 -m novelops init my_novel

# 开始生成章节
python3 -m novelops generate my_novel

# 运行 NovelRadar 市场调研
python3 -m novelops.radar run-sample
```

---

## 项目结构

```
novel0/
├── src/novelops/                    # 核心源码
│   ├── cli.py                       # CLI 入口
│   ├── web.py                       # FastAPI Web 应用
│   ├── llm.py                       # LLM 客户端
│   ├── generator.py                 # 章节生成器
│   ├── reviewer.py                  # 审稿系统
│   ├── pipeline/                    # LangGraph 流水线
│   │   ├── graph.py                 # 状态图构建
│   │   └── nodes/                   # 流水线节点
│   ├── radar/                       # NovelRadar 市场情报
│   │   ├── collectors/              # 数据采集器
│   │   ├── analyzer.py              # 规则分析器
│   │   └── llm_analyzer.py          # LLM 热点分析
│   ├── memory/                      # ChromaDB 记忆层
│   └── db/                          # 数据库层
├── configs/                         # 配置文件
│   ├── models.json                  # LLM 模型配置
│   └── prompts/                     # Prompt 模板
├── projects/                        # 小说项目目录
│   └── life_balance/                # 示例项目
├── docs/                            # 文档
├── deploy/                          # 部署配置
└── tests/                           # 测试
```

---

## 核心模块详解

### 小说生成流水线

基于 LangGraph 的有向状态图，支持人工审批点和自动重试：

```
market_research → concept_design → outline → chapter_plan → draft
    → commercial_review → continuity_check → rewrite → save
```

多阶段 LLM 调用链：
1. **chapter_intent**：细化读者承诺、情绪转折、商业钩子
2. **scene_chain**：3-6 个场景设计
3. **draft_v1**：初稿生成
4. **commercial_rewrite**：强化冲突/爽点/悬念
5. **humanize**：降低 AI 痕迹
6. 审稿门禁 + 最多 2 轮自动修订

### NovelRadar 市场情报引擎

- **数据采集**：番茄小说、起点、纵横、晋江、潇湘等平台公开榜单
- **规则分析**：自动识别题材、金手指、爽点、风险
- **LLM 热点分析**：深度分析读者欲望、钩子、风险
- **竞品分析**：同题材竞品对比、差异化机会
- **商业评分**：热度(35%) + 平台适配度(25%) + 读者欲望(20%) + 写作容易度(10%) + 趋势加成(10%) - 竞争惩罚

### 审稿系统

**规则评分维度**：
- 字数/段落密度/对话密度
- 钩子词命中率
- 禁写词检测

**LLM 七维评分**：
- hook（钩子）/ conflict（冲突）/ consistency（一致性）
- continuity（连续性）/ ai_trace（AI痕迹）/ retention（留存）/ risk（风险）

### 记忆层

基于 ChromaDB 的语义向量存储：
- 自动索引项目文档（bible/outlines/state/corpus）
- 章节生成时语义召回相关上下文
- 增量更新（每章生成后自动索引）

### Web Dashboard

- **邀请码登录**：用户-项目多对多关联
- **项目工作台**：查看项目状态、章节列表、审稿结果
- **AI 聊天**：自然语言命令解析 + SSE 实时进度推送
- **框架导入**：从 ChatGPT Markdown 框架一键导入新书项目

---

## CLI 命令参考

### NovelOps 主命令

```bash
# 创建新项目
python3 -m novelops init <project_name>

# 生成章节
python3 -m novelops generate <project_name> [--count N]

# 审稿检查
python3 -m novelops review <project_name>

# 查看项目状态
python3 -m novelops status <project_name>
```

### NovelRadar 命令

```bash
# 初始化数据库
python3 -m novelops.radar init

# 导入样本数据
python3 -m novelops.radar import-fanqie --sample

# 导入 CSV 数据
python3 -m novelops.radar import-csv data.csv --platform 番茄

# 运行分析
python3 -m novelops.radar analyze

# 生成报告
python3 -m novelops.radar report

# 一键完整流程
python3 -m novelops.radar run-sample
```

---

## 示例项目

**life_balance**（《我能看见人生余额开局救下白月光》）
- 题材：都市异能悬疑爽文
- 已完成：50 章（第一卷）
- 钩子词：余额、寿命、命运、代价、规则、天平
- 禁写项：自动复活已收束反派、跳过代价、直接写成终局

---

## 配置说明

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

### 环境变量 (.env)

```bash
OPENAI_API_KEY=your-api-key
DEEPSEEK_API_KEY=your-api-key
NOVELOPS_SECRET_KEY=your-session-secret
```

---

## 部署

详见 [deploy/DEPLOYMENT.md](deploy/DEPLOYMENT.md)，支持：
- ECS + Nginx + systemd
- Let's Encrypt SSL
- 自动备份脚本

---

## 合规边界

- ✅ 允许：公开榜单、公开评论、人工录入数据
- ❌ 禁止：付费正文、绕过登录、破解接口

---

## 后续发展

- **短期**：接入更多平台真实榜单、优化 LLM 分析质量
- **中期**：完善 Web Dashboard、增加趋势分析
- **长期**：作品数据反馈闭环、A/B 测试框架、多语言支持

---

## 许可证

[待定]

---

## 贡献

欢迎提交 Issue 和 Pull Request。
