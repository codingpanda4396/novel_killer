# 热点分析功能实现计划

## 现状分析

### 现有模型
- `RawNovelSignal` - 原始信号
- `AnalyzedNovelSignal` - 分析后信号（包含 extracted_genre, golden_finger, core_hook, reader_desire 等字段）
- `TopicOpportunity` - 选题机会
- `CompetitorAnalysis` - 竞品分析

### 现有分析器
- `RuleBasedRadarAnalyzer` - 基于规则的分析器

### 数据库
- `analyzed_signals` 表已有一些字段，但需要新增 LLM 分析的字段

### LLM 客户端
- `LLMClient` 类，有 `complete_json()` 方法

---

## 实现步骤

### 第一阶段：基础设施（依赖和模型）

#### 1. 添加 Pydantic 依赖
- 在 `pyproject.toml` 的 `dependencies` 中添加 `pydantic>=2.0.0`
- 在 `requirements.txt` 中添加 `pydantic>=2.0.0`

#### 2. 创建热点分析模型 `src/novelops/radar/hotspot_models.py`
```python
from pydantic import BaseModel, Field

class HotspotAnalysis(BaseModel):
    """LLM 热点分析结果"""
    genre: str = Field(description="简短题材名，如'仙侠''都市重生''末世囤货'")
    core_desire: str = Field(description="读者核心欲望，如'被压迫后的逆袭'")
    hook: str = Field(description="一句话核心钩子")
    golden_finger: str = Field(description="金手指机制；未知则填'无明显金手指'")
    reader_emotion: list[str] = Field(description="1-5 个短词", max_length=5)
    risk: str = Field(description="一句话市场或开局风险")
```

### 第二阶段：LLM 分析器

#### 3. 创建 LLM 热点分析器 `src/novelops/radar/llm_analyzer.py`
- 定义 system prompt（中文网文市场热点分析师角色）
- 定义 user prompt 模板（包含字段定义和取值要求）
- 实现 `LLMHotspotAnalyzer` 类：
  - `__init__(self, llm_client: LLMClient | None = None)`
  - `analyze_text(self, text: str, metadata: dict | None = None) -> HotspotAnalysis`
  - `analyze_signal(self, signal: RawNovelSignal) -> HotspotAnalysis`
  - `analyze_batch(self, signals: list[RawNovelSignal]) -> list[HotspotAnalysis | None]`（支持失败回退）

#### 4. 创建组合分析器 `src/novelops/radar/composite_analyzer.py`
- 实现 `CompositeAnalyzer` 类：
  - `__init__(self, use_llm: bool = False, llm_client: LLMClient | None = None)`
  - `analyze_one(self, signal: RawNovelSignal) -> AnalyzedNovelSignal`
  - `analyze(self, signals: list[RawNovelSignal]) -> list[AnalyzedNovelSignal]`
- 逻辑：
  1. 先用 `RuleBasedRadarAnalyzer` 填充现有字段
  2. 如果启用 LLM，调用 `LLMHotspotAnalyzer` 获取额外分析
  3. 将 LLM 结果映射到 `AnalyzedNovelSignal` 的新字段
  4. LLM 失败时回退到规则分析，不中断整批

### 第三阶段：数据模型扩展

#### 5. 扩展 `AnalyzedNovelSignal` 模型 `src/novelops/radar/models.py`
在 `AnalyzedNovelSignal` 中新增字段：
```python
# LLM 分析结果
llm_genre: str | None = None
llm_core_desire: str | None = None
llm_hook: str | None = None
llm_golden_finger: str | None = None
llm_reader_emotion: list[str] = field(default_factory=list)
llm_risk: str | None = None
```

#### 6. 扩展数据库 Schema `src/novelops/radar/storage.py`
- 在 `SCHEMA` 的 `analyzed_signals` 表中新增列：
  ```sql
  llm_genre TEXT,
  llm_core_desire TEXT,
  llm_hook TEXT,
  llm_golden_finger TEXT,
  llm_reader_emotion TEXT,
  llm_risk TEXT
  ```
- 修改 `init_db()` 方法，添加安全的 `ALTER TABLE ADD COLUMN` 逻辑：
  - 检查列是否存在
  - 不存在则添加
- 更新 `save_analyzed_signals()` 和 `_row_to_analyzed_signal()` 方法

### 第四阶段：CLI 扩展

#### 7. 更新 CLI `src/novelops/radar/cli.py`
- 修改 `cmd_analyze()` 函数：
  - 添加 `--llm` 参数
  - 启用 LLM 时使用 `CompositeAnalyzer`
- 新增 `cmd_analyze_text()` 函数：
  - 接收原始文本参数
  - 可选 `--json` 输出格式
  - 可选元数据参数（标题、分类、标签等）
- 更新 `build_parser()`：
  - 为 `analyze` 子命令添加 `--llm` 参数
  - 新增 `analyze-text` 子命令

### 第五阶段：测试

#### 8. 创建测试文件 `tests/radar/test_hotspot_models.py`
- 测试 `HotspotAnalysis` 模型：
  - 合法 JSON 通过
  - 缺字段失败
  - 类型错误失败

#### 9. 创建测试文件 `tests/radar/test_llm_analyzer.py`
- 使用 mock/fake LLM 测试：
  - 验证字段解析
  - 验证 schema 参数传递
  - 验证失败时的行为

#### 10. 创建测试文件 `tests/radar/test_composite_analyzer.py`
- 测试组合分析流程：
  - LLM 字段正确写入
  - LLM 失败时回退到规则分析
  - 批量处理不中断

#### 11. 创建测试文件 `tests/radar/test_storage_migration.py`
- 测试数据库迁移：
  - 新库创建包含新增列
  - 旧 schema 初始化后自动补列
  - 不丢旧数据

#### 12. 创建测试文件 `tests/radar/test_cli_hotspot.py`
- 测试 CLI 命令：
  - `analyze-text --json` 输出目标 JSON
  - `analyze --llm` 使用 fake client 后保存新增字段
  - LLM 失败时批量 analyze 可回退规则分析

### 第六阶段：回归测试

#### 13. 运行现有测试确保兼容
- 运行 `tests/radar/` 下所有现有测试
- 确保 `test_integration.py` 仍然通过
- 确保 `run-sample` 流程不受影响

---

## 文件清单

### 需要创建的文件
1. `src/novelops/radar/hotspot_models.py`
2. `src/novelops/radar/llm_analyzer.py`
3. `src/novelops/radar/composite_analyzer.py`
4. `tests/radar/test_hotspot_models.py`
5. `tests/radar/test_llm_analyzer.py`
6. `tests/radar/test_composite_analyzer.py`
7. `tests/radar/test_storage_migration.py`
8. `tests/radar/test_cli_hotspot.py`

### 需要修改的文件
1. `pyproject.toml` - 添加 pydantic 依赖
2. `requirements.txt` - 添加 pydantic 依赖
3. `src/novelops/radar/models.py` - 扩展 AnalyzedNovelSignal
4. `src/novelops/radar/storage.py` - 扩展 schema 和迁移逻辑
5. `src/novelops/radar/cli.py` - 添加新命令和参数

---

## 实现顺序

1. 先添加依赖和创建模型
2. 实现 LLM 分析器（独立模块，易于测试）
3. 扩展数据模型和存储
4. 实现组合分析器
5. 更新 CLI
6. 编写测试
7. 回归测试
