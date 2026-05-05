# NovelRadar 中文网文需求情报引擎 MVP 实施方案

## 一、项目背景与目标

### 1.1 背景
NovelOps 是一个面向中文网文项目的本地创作中台，当前已实现章节生成、审稿、修订等核心功能。为了提升选题决策能力，需要新增一个情报引擎模块 NovelRadar，用于采集、整理、分析中文网文用户需求信号。

### 1.2 目标
- 构建可运行、可扩展、可验证的数据闭环
- 先不做大规模爬虫，优先落地"情报引擎骨架"
- 支持人工整理数据导入和公开榜单数据处理
- 输出"今日选题机会报告"，指导创作测试

### 1.3 合规边界
- ✅ 允许：公开榜单、公开评论、公开关键词、人工录入数据
- ❌ 禁止：付费正文抓取、绕过登录、破解接口、模拟用户刷数据

## 二、现有项目结构分析

### 2.1 项目组织
```
novel0/
├── src/novelops/          # 主要业务逻辑
│   ├── cli.py            # CLI 入口（使用 argparse）
│   ├── schemas.py        # 数据模型（使用 dataclass）
│   ├── config.py         # 配置管理
│   ├── indexer.py        # SQLite 索引
│   ├── llm.py            # LLM 调用
│   └── ...
├── projects/             # 项目实例
│   └── life_balance/
│       ├── intelligence/ # 已预留情报目录
│       │   ├── raw/
│       │   ├── processed/
│       │   └── reports/
│       └── ...
├── runtime/              # 运行时数据
│   └── novelops.sqlite3
├── configs/              # 配置文件
├── docs/                 # 文档
└── tests/                # 测试
```

### 2.2 技术栈特征
- **数据模型**：使用 `@dataclass(frozen=True)` 定义不可变数据类
- **CLI 框架**：argparse
- **存储方案**：SQLite（已有 `runtime/novelops.sqlite3`）
- **依赖管理**：pyproject.toml + requirements.txt
- **LLM 集成**：DeepSeek + Claude via RightCode
- **代码风格**：类型注解、函数式风格、简洁注释

### 2.3 关键发现
1. 项目已预留 `projects/*/intelligence/` 目录结构
2. 已有 SQLite 索引基础设施（`indexer.py`）
3. 已有 CLI 子命令扩展机制
4. 已有 LLM 调用封装（`llm.py`）
5. 使用 dataclass 而非 Pydantic

## 三、NovelRadar 模块设计

### 3.1 目录结构
```
src/novelops/
  radar/
    __init__.py
    models.py              # 数据模型定义
    storage.py             # SQLite 存储层
    importer.py            # CSV/JSON 导入器
    analyzer.py            # 规则分析器
    scoring.py             # 商业评分模型
    report.py              # 报告生成器
    cli.py                 # CLI 命令
    collectors/
      __init__.py
      base.py              # 采集器基类
      csv_collector.py     # CSV 采集器
      json_collector.py    # JSON 采集器
      fanqie_skeleton.py   # 番茄公开榜单骨架（预留）
    prompts/
      topic_analysis.md    # LLM 分析 prompt（预留）

runtime/
  radar/
    radar.sqlite           # Radar 专用数据库
    samples/
      sample_rankings.csv  # 示例数据
    reports/               # 生成的报告

docs/
  radar/
    mvp_guide.md          # MVP 使用指南
    data_schema.md        # 数据模型文档
    collector_guide.md    # 采集器开发指南
```

### 3.2 核心数据模型

#### RawNovelSignal（原始信号）
```python
@dataclass(frozen=True)
class RawNovelSignal:
    """原始网文需求信号"""
    signal_id: str                    # 唯一标识
    source: str                       # fanqie / qimao / qidian / douyin / manual
    source_type: str                  # ranking / search / comment / keyword / manual
    platform: str                     # 番茄 / 七猫 / 起点 / 抖音
    rank_type: str | None             # 仙侠热榜 / 新书榜 / 完结榜
    rank_position: int | None         # 榜单位置
    title: str                        # 小说标题
    author: str | None                # 作者
    category: str | None              # 分类
    sub_category: str | None          # 子分类
    tags: list[str]                   # 标签列表
    description: str | None           # 简介
    hot_score: float | None           # 热度分数
    comment_count: int | None         # 评论数
    like_count: int | None            # 点赞数
    read_count: int | None            # 阅读数
    collected_at: str                 # 采集时间（ISO 8601）
    raw_payload: dict[str, Any]       # 原始数据
```

#### AnalyzedNovelSignal（分析后信号）
```python
@dataclass(frozen=True)
class AnalyzedNovelSignal:
    """分析后的网文需求信号"""
    # 继承 RawNovelSignal 所有字段
    signal_id: str
    source: str
    # ... (省略重复字段)
    
    # 分析结果
    extracted_genre: str | None           # 提取的题材
    protagonist_template: str | None      # 主角模板
    golden_finger: str | None             # 金手指类型
    core_hook: str | None                 # 核心钩子
    reader_desire: str | None             # 读者欲望
    shuang_points: list[str]              # 爽点列表
    risk_points: list[str]                # 毒点风险
    
    # 评分
    platform_fit_score: float             # 平台适配度 0-100
    competition_score: float              # 竞争度 0-100
    writing_difficulty_score: float       # 写作难度 0-100
    commercial_potential_score: float     # 商业潜力 0-100
    
    analyzed_at: str                      # 分析时间
    analyzer_version: str                 # 分析器版本
```

#### TopicOpportunity（选题机会）
```python
@dataclass(frozen=True)
class TopicOpportunity:
    """选题机会"""
    topic_id: str                     # 选题 ID
    topic_name: str                   # 选题名称
    target_platform: str              # 目标平台
    target_reader: str                # 目标读者
    core_tags: list[str]              # 核心标签
    evidence_titles: list[str]        # 证据样本标题
    
    # 综合评分
    hot_score: float                  # 热度分数
    competition_score: float          # 竞争度
    platform_fit_score: float         # 平台适配度
    writing_difficulty_score: float   # 写作难度
    final_score: float                # 最终评分
    
    # 创作建议
    opening_hook: str                 # 推荐开篇钩子
    suggested_story_seed: str         # 建议故事种子
    risks: list[str]                  # 主要风险
    
    generated_at: str                 # 生成时间
```

### 3.3 存储方案

#### 数据库设计
使用独立的 SQLite 数据库：`runtime/radar/radar.sqlite`

**表结构**：
```sql
-- 原始信号表
CREATE TABLE raw_signals (
    signal_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_type TEXT NOT NULL,
    platform TEXT NOT NULL,
    rank_type TEXT,
    rank_position INTEGER,
    title TEXT NOT NULL,
    author TEXT,
    category TEXT,
    sub_category TEXT,
    tags TEXT,  -- JSON array
    description TEXT,
    hot_score REAL,
    comment_count INTEGER,
    like_count INTEGER,
    read_count INTEGER,
    collected_at TEXT NOT NULL,
    raw_payload TEXT NOT NULL  -- JSON
);

-- 分析信号表
CREATE TABLE analyzed_signals (
    signal_id TEXT PRIMARY KEY,
    -- 原始字段（同上）
    ...
    -- 分析字段
    extracted_genre TEXT,
    protagonist_template TEXT,
    golden_finger TEXT,
    core_hook TEXT,
    reader_desire TEXT,
    shuang_points TEXT,  -- JSON array
    risk_points TEXT,    -- JSON array
    platform_fit_score REAL,
    competition_score REAL,
    writing_difficulty_score REAL,
    commercial_potential_score REAL,
    analyzed_at TEXT NOT NULL,
    analyzer_version TEXT NOT NULL,
    FOREIGN KEY (signal_id) REFERENCES raw_signals(signal_id)
);

-- 选题机会表
CREATE TABLE topic_opportunities (
    topic_id TEXT PRIMARY KEY,
    topic_name TEXT NOT NULL,
    target_platform TEXT NOT NULL,
    target_reader TEXT NOT NULL,
    core_tags TEXT NOT NULL,  -- JSON array
    evidence_titles TEXT NOT NULL,  -- JSON array
    hot_score REAL NOT NULL,
    competition_score REAL NOT NULL,
    platform_fit_score REAL NOT NULL,
    writing_difficulty_score REAL NOT NULL,
    final_score REAL NOT NULL,
    opening_hook TEXT NOT NULL,
    suggested_story_seed TEXT NOT NULL,
    risks TEXT NOT NULL,  -- JSON array
    generated_at TEXT NOT NULL
);

-- 索引
CREATE INDEX idx_raw_signals_source ON raw_signals(source, source_type);
CREATE INDEX idx_raw_signals_platform ON raw_signals(platform);
CREATE INDEX idx_raw_signals_collected ON raw_signals(collected_at DESC);
CREATE INDEX idx_analyzed_signals_score ON analyzed_signals(commercial_potential_score DESC);
CREATE INDEX idx_topic_opportunities_score ON topic_opportunities(final_score DESC);
```

### 3.4 规则分析器设计

#### 题材识别规则
```python
GENRE_RULES = {
    "仙侠修真": ["修仙", "仙尊", "长生", "宗门", "筑基", "金丹", "元婴"],
    "都市重生": ["重生", "回到", "穿越", "前世", "今生"],
    "都市逆袭": ["首富", "商业", "赚钱", "创业", "逆袭"],
    "年代文": ["空间", "年代", "下乡", "军婚", "七零", "八零"],
    "末世囤货": ["末世", "囤货", "丧尸", "灾难", "求生"],
    "系统流": ["系统", "面板", "词条", "模拟器", "签到"],
    "女频爽文": ["真假千金", "豪门", "退婚", "打脸", "虐渣"],
    "高武觉醒": ["高武", "觉醒", "武道", "灵气复苏"],
}

GOLDEN_FINGER_RULES = {
    "系统": ["系统", "面板"],
    "空间": ["空间", "随身"],
    "重生": ["重生", "回到"],
    "词条": ["词条", "天赋"],
    "模拟器": ["模拟器", "推演"],
}

SHUANG_POINT_RULES = [
    "杀伐果断", "无敌", "横推", "打脸", "装逼",
    "逆袭", "复仇", "虐渣", "爽文", "碾压",
]

RISK_POINT_RULES = {
    "卖点过散": lambda signal: len(signal.tags) > 8,
    "题材混杂": lambda signal: _check_genre_conflict(signal),
    "缺少简介": lambda signal: not signal.description or len(signal.description) < 20,
    "热度不足": lambda signal: signal.hot_score and signal.hot_score < 10,
}
```

### 3.5 商业评分模型

#### 评分公式（v1.0）
```python
def calculate_commercial_potential(signal: AnalyzedNovelSignal) -> float:
    """
    商业潜力评分公式
    
    final_score = 
        hot_score * 0.35              # 热度权重
        + platform_fit_score * 0.25   # 平台适配度
        + reader_desire_score * 0.20  # 读者欲望强度
        + writing_ease * 0.10         # 写作容易度（难度的反向）
        + trend_bonus * 0.10          # 趋势加成
        - competition_penalty         # 竞争惩罚
    
    范围：0-100
    """
    
    # 热度分数（归一化）
    hot = normalize_hot_score(signal.hot_score or 50)
    
    # 平台适配度（番茄偏好）
    platform_fit = calculate_platform_fit(signal)
    
    # 读者欲望强度
    desire = calculate_reader_desire(signal)
    
    # 写作容易度
    ease = 100 - signal.writing_difficulty_score
    
    # 趋势加成
    trend = calculate_trend_bonus(signal)
    
    # 竞争惩罚
    competition = calculate_competition_penalty(signal)
    
    final = (
        hot * 0.35
        + platform_fit * 0.25
        + desire * 0.20
        + ease * 0.10
        + trend * 0.10
        - competition
    )
    
    return max(0, min(100, final))
```

#### 平台适配度规则（番茄小说）
```python
FANQIE_FIT_SCORES = {
    # 高适配（80-95）
    "都市重生": 90,
    "赘婿逆袭": 88,
    "高武觉醒": 85,
    "末世囤货": 85,
    "系统流": 82,
    
    # 中高适配（65-79）
    "凡人修仙": 75,
    "年代文": 72,
    "女频爽文": 70,
    
    # 中等适配（50-64）
    "玄幻": 60,
    "历史": 55,
    
    # 低适配（<50）
    "硬科幻": 40,
    "纯文学": 30,
}
```

### 3.6 报告生成器

#### 报告模板
```markdown
# NovelRadar 中文网文选题机会报告

**生成时间**：{generated_at}  
**数据来源**：{data_sources}  
**分析样本**：{total_signals} 条

---

## 一、总体观察

- 今日共分析 **{total_signals}** 条数据
- 高潜力题材 Top 5：{top_genres}
- 风险较高题材 Top 3：{risky_genres}
- 平均商业潜力评分：{avg_score:.1f}/100

---

## 二、题材热度排行

| 排名 | 题材 | 样本数 | 平均热度 | 平台适配度 | 竞争度 | 推荐指数 |
|:---:|:---|---:|---:|---:|---:|---:|
| 1 | {genre_1} | {count_1} | {hot_1} | {fit_1} | {comp_1} | ⭐⭐⭐⭐⭐ |
| 2 | {genre_2} | {count_2} | {hot_2} | {fit_2} | {comp_2} | ⭐⭐⭐⭐ |
| ... | ... | ... | ... | ... | ... | ... |

---

## 三、推荐测试选题

### 选题 1：{topic_name_1}

**目标平台**：{target_platform}  
**目标读者**：{target_reader}  
**核心标签**：{core_tags}  
**综合评分**：{final_score:.1f}/100

**证据样本**：
- {evidence_title_1}
- {evidence_title_2}
- {evidence_title_3}

**推荐开篇钩子**：
{opening_hook}

**可测试故事种子**：
{story_seed}

**主要风险**：
- {risk_1}
- {risk_2}

---

## 四、下一步创作建议

1. **优先测试选题**：{top_3_topics}
2. **开篇策略**：每个选题生成 3 个开篇变体，控制在 2000-3000 字
3. **测试重点**：前三章留存率、评论区反馈、收藏转化
4. **避免陷阱**：不要追求神作，先测试题材和钩子的市场反应

---

## 五、数据质量说明

- 数据时效性：{data_freshness}
- 样本覆盖度：{coverage}
- 分析器版本：{analyzer_version}
- 建议更新频率：每日或每周

---

*本报告由 NovelRadar 自动生成，仅供参考。最终选题决策需结合个人写作能力和市场实测。*
```

## 四、实施步骤

### 阶段 0：准备工作
- [x] 理解现有项目结构
- [ ] 创建 `src/novelops/radar/` 目录
- [ ] 创建 `runtime/radar/` 目录
- [ ] 创建 `docs/radar/` 目录

### 阶段 1：核心数据模型（models.py）
- [ ] 定义 `RawNovelSignal` dataclass
- [ ] 定义 `AnalyzedNovelSignal` dataclass
- [ ] 定义 `TopicOpportunity` dataclass
- [ ] 添加辅助函数（序列化、反序列化）

### 阶段 2：存储层（storage.py）
- [ ] 实现 `RadarStorage` 类
- [ ] 实现数据库初始化（`init_db`）
- [ ] 实现原始信号存储（`save_raw_signals`）
- [ ] 实现分析信号存储（`save_analyzed_signals`）
- [ ] 实现选题机会存储（`save_topic_opportunities`）
- [ ] 实现查询方法（`list_*`, `get_*`）

### 阶段 3：数据导入（importer.py + collectors/）
- [ ] 实现 `CSVCollector`
  - 支持标准字段映射
  - 支持多种标签分隔符（中文逗号、英文逗号、竖线）
  - 容错处理（缺失字段、格式错误）
- [ ] 实现 `JSONCollector`
- [ ] 创建示例数据 `runtime/radar/samples/sample_rankings.csv`
  - 10 条虚构但合理的中文网文榜单数据

### 阶段 4：规则分析器（analyzer.py）
- [ ] 实现 `RuleBasedRadarAnalyzer` 类
- [ ] 题材识别规则
- [ ] 金手指识别规则
- [ ] 爽点识别规则
- [ ] 毒点风险识别规则
- [ ] 生成 `AnalyzedNovelSignal`

### 阶段 5：商业评分（scoring.py）
- [ ] 实现热度归一化
- [ ] 实现平台适配度计算（番茄偏好）
- [ ] 实现读者欲望强度计算
- [ ] 实现写作难度评估
- [ ] 实现趋势加成计算
- [ ] 实现竞争度惩罚
- [ ] 实现综合评分公式

### 阶段 6：报告生成（report.py）
- [ ] 实现题材聚合统计
- [ ] 实现选题机会提取
- [ ] 实现 Markdown 报告生成
- [ ] 报告保存到 `runtime/radar/reports/`

### 阶段 7：CLI 集成（cli.py）
- [ ] 实现 `radar init` 命令
- [ ] 实现 `radar import-csv` 命令
- [ ] 实现 `radar import-json` 命令
- [ ] 实现 `radar analyze` 命令
- [ ] 实现 `radar report` 命令
- [ ] 实现 `radar run-sample` 命令（完整流程）
- [ ] 集成到主 CLI（`src/novelops/cli.py`）

### 阶段 8：文档（docs/radar/）
- [ ] 编写 `mvp_guide.md`
  - NovelRadar 是什么
  - 为什么不直接大规模爬虫
  - 如何运行 sample
  - 如何导入真实数据
  - 合规边界说明
- [ ] 编写 `data_schema.md`
  - 数据模型详细说明
  - CSV 格式示例
  - JSON 格式示例
- [ ] 编写 `collector_guide.md`
  - 如何开发新的 collector
  - 公开榜单采集指南
  - 合规检查清单

### 阶段 9：测试（tests/radar/）
- [ ] CSV 导入测试
- [ ] 标签解析测试
- [ ] 规则分析器测试
- [ ] 评分模型测试
- [ ] 完整流程测试（`run-sample`）

### 阶段 10：LLM 集成预留
- [ ] 创建 `prompts/topic_analysis.md`
- [ ] 在 `analyzer.py` 中预留 LLM 接口
- [ ] 文档说明如何启用 LLM 分析

## 五、验收标准

### 最小可运行路径
```bash
# 1. 初始化数据库
python -m novelops.radar init

# 2. 导入示例数据
python -m novelops.radar import-csv runtime/radar/samples/sample_rankings.csv

# 3. 分析数据
python -m novelops.radar analyze

# 4. 生成报告
python -m novelops.radar report

# 或者一键运行完整流程
python -m novelops.radar run-sample
```

### 预期输出
```
NovelRadar sample pipeline completed.
Imported: 10 signals
Analyzed: 10 signals
Report generated: runtime/radar/reports/topic_report_20260505_1230.md
```

### 报告文件检查
- 文件存在：`runtime/radar/reports/topic_report_*.md`
- 包含完整 Markdown 结构
- 包含题材排行表格
- 包含至少 3 个推荐选题
- 包含创作建议

## 六、技术约束与风险

### 技术约束
1. **不破坏现有功能**：所有新增代码在 `src/novelops/radar/` 下，不修改现有模块
2. **遵循现有风格**：使用 dataclass、类型注解、函数式风格
3. **依赖最小化**：优先使用标准库，避免引入重型依赖
4. **路径兼容性**：所有路径使用 `pathlib.Path`，兼容 macOS

### 风险与缓解
| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 示例数据不够真实 | 测试效果差 | 参考真实榜单构造虚拟数据 |
| 规则分析器准确度低 | 分析结果不可信 | 先做保守规则，后续迭代优化 |
| 评分模型不合理 | 推荐选题偏差 | 提供可调参数，支持人工校准 |
| CLI 集成冲突 | 破坏现有命令 | 使用独立子命令 `radar` |

## 七、后续扩展方向

### 短期（1-2 周）
1. 接入番茄小说公开榜单 collector（Playwright）
2. 接入 LLM 自动分析（DeepSeek）
3. 支持多平台数据源（七猫、起点）

### 中期（1 个月）
1. Web Dashboard 可视化
2. 选题趋势分析（时间序列）
3. 与 NovelOps 生成流程打通（自动创建项目）

### 长期（3 个月）
1. 作品数据反馈闭环（发布后数据回流）
2. A/B 测试框架（多开篇对比）
3. 读者画像分析

## 八、关键文件清单

### 新增文件
```
src/novelops/radar/
  __init__.py
  models.py
  storage.py
  importer.py
  analyzer.py
  scoring.py
  report.py
  cli.py
  collectors/
    __init__.py
    base.py
    csv_collector.py
    json_collector.py
  prompts/
    topic_analysis.md

runtime/radar/
  radar.sqlite
  samples/
    sample_rankings.csv
  reports/

docs/radar/
  mvp_guide.md
  data_schema.md
  collector_guide.md

tests/radar/
  test_importer.py
  test_analyzer.py
  test_scoring.py
  test_integration.py
```

### 修改文件
```
src/novelops/cli.py  # 添加 radar 子命令
```

## 九、开发原则

1. ✅ **先做可运行 MVP**，不做大而全平台爬虫
2. ✅ **优先保证模块清晰、可扩展、可测试**
3. ✅ **不破坏已有 novelops 功能**
4. ✅ **不引入重型依赖**，除非项目已经使用
5. ✅ **所有路径兼容 macOS**
6. ✅ **代码适合后续被 AI 工具继续接手**
7. ✅ **每完成一个阶段就运行相关测试**
8. ✅ **如果现有结构冲突，优先适配现有项目**

---

**文档版本**：v1.0  
**创建时间**：2026-05-05  
**作者**：Claude Code  
**状态**：待审核
