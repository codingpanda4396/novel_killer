# Coding Rules

> 最后更新：2026-05-03  
> NovelOps 项目编码规范，所有 Agent 和贡献者必须遵守

## 1. 核心原则

### 1.1 不破坏现有测试

**规则**：任何代码修改都必须确保现有测试全部通过。

**具体要求**：
- 修改代码前，先运行完整测试套件：`python3 -m unittest discover -s tests`
- 修改后，再次运行测试确保无回归
- 如果修改导致测试失败，必须修复测试或回退修改
- 新增功能必须附带相应测试，保持或提升测试覆盖率

**禁止行为**：
- ❌ 禁止通过删除测试来"修复"测试失败
- ❌ 禁止修改测试逻辑来适配有 bug 的代码
- ❌ 禁止在不确定影响范围的情况下大幅重构

**例外情况**：
- 仅当测试本身有 bug（如缺少认证、错误断言）时，可以修复测试
- 必须提供清晰的 commit message 说明测试修复原因

---

### 1.2 不引入重型依赖

**规则**：保持项目轻量级，避免引入重型框架和库。

**当前依赖理念**：
- ✅ 使用标准库优先
- ✅ 必要时使用轻量级第三方库（如 `fastapi`、`itsdangerous`、`jinja2`）
- ❌ 禁止引入重型框架（如 `django`、`flask` 已足够时的 `fastapi` 情况除外）
- ❌ 禁止引入前端框架（如 `react`、`vue`、`angular`）
- ❌ 禁止引入重型数据处理库（如 `pandas`、`numpy`），除非确有必要

**新增依赖审核标准**：
1. 该依赖是否可以通过标准库或现有依赖实现？
2. 该依赖的打包大小是否 < 5MB？
3. 该依赖是否有已知的严重安全漏洞？
4. 该依赖是否维护活跃？

**推荐替代方案**：
| 需求 | 不推荐 | 推荐 |
|------|--------|------|
| HTML 模板 | React + Next.js | Jinja2 |
| 数据可视化 | ECharts 完整版 | Chart.js 或 ECharts 精简版 |
| HTTP 请求 | Requests | 标准库 `urllib`（如确需再考虑 requests） |
| 数据验证 | Pydantic（已有） | 继续使用 Pydantic |

---

### 1.3 每个新模块必须有 unittest

**规则**：所有新增的功能模块必须包含对应的单元测试。

**具体要求**：
- 每个新模块（如 `novelops/billing.py`）必须有对应的测试（`tests/test_billing.py` 或添加到 `tests/test_novelops.py`）
- 测试覆盖率目标：≥ 80%（核心逻辑 ≥ 90%）
- 测试必须可独立运行，不依赖外部服务（使用 Fake/Mock 对象模拟 LLM 等外部依赖）

**测试编写规范**：
```python
# 好的测试示例
class BillingTests(unittest.TestCase):
    def setUp(self) -> None:
        # 使用临时目录和 Mock 对象
        self.tmp_dir = tempfile.mkdtemp()
        self.fake_llm = FakeLLMClient()
    
    def test_record_api_call(self) -> None:
        """测试记录 API 调用"""
        billing = BillingRecorder(db_path=Path(self.tmp_dir) / "test.db")
        billing.record_call(model="test-model", tokens=100, cost=0.01)
        self.assertEqual(billing.get_total_cost(), 0.01)
    
    def test_cost_limit_alert(self) -> None:
        """测试成本超限告警"""
        billing = BillingRecorder(budget=1.0)
        billing.record_call(model="test", tokens=10000, cost=1.5)
        self.assertTrue(billing.is_over_budget())
```

**测试必须覆盖**：
- ✅ 正常流程（happy path）
- ✅ 边界情况（空输入、最大值、最小值）
- ✅ 错误处理（异常捕获、错误返回）
- ✅ Mock 外部依赖（LLM API、文件系统错误等）

---

## 2. 代码风格

### 2.1 类型注解

- 所有函数和方法必须有类型注解（参数和返回值）
- 使用 `from __future__ import annotations` 支持延迟注解评估

```python
from __future__ import annotations

def process_chapter(chapter_id: int, project: str) -> ChapterResult:
    ...
```

### 2.2 文档字符串

- 公共 API 和复杂逻辑必须有文档字符串
- 使用 Google 风格或 NumPy 风格（保持项目一致）

```python
def generate_chapter(project: str, chapter: int) -> GenerationResult:
    """生成指定项目的指定章节
    
    Args:
        project: 项目 ID
        chapter: 章节号
    
    Returns:
        生成结果，包含生成的章节内容和审稿信息
    
    Raises:
        ConfigError: 当 LLM 配置无效时
    """
    ...
```

### 2.3 错误处理

- 使用项目自定义的异常类（如 `ConfigError`）
- 不要使用裸 `except:`，要捕获具体异常
- 错误信息要清晰，便于调试

```python
# 好的做法
try:
    settings = settings_for_stage("reviewer")
except ConfigError as e:
    logger.error(f"Failed to load reviewer settings: {e}")
    raise

# 坏的做法
try:
    settings = settings_for_stage("reviewer")
except:
    pass  # 不要这样做
```

---

## 3. Git 提交规范

### 3.1 Commit Message 格式

使用 Conventional Commits 风格：

```
<type>: <subject>

<body>
```

**类型（type）**：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行的变动）
- `refactor`: 重构（既不是新功能也不是修复 bug）
- `test`: 测试相关改动
- `chore`: 构建过程或辅助工具的变动

**示例**：
```
feat: add billing module for LLM cost tracking

- Add BillingRecorder class to novelops/billing.py
- Add unit tests for billing module
- Integrate billing recorder into LLM client
```

### 3.2 提交频率

- 小步快跑：每个独立功能或修复单独提交
- 不要在一个 commit 中混合多个不相关的改动
- 提交前运行测试确保通过

---

## 4. 安全规范

### 4.1 API 密钥管理

- ❌ 禁止将 API 密钥、密码等敏感信息提交到仓库
- ✅ 使用环境变量或 `.env` 文件（已加入 `.gitignore`）
- ✅ 提供 `.env.example` 作为模板

### 4.2 用户输入验证

- 所有 Web API 输入必须使用 Pydantic 模型验证
- 文件路径必须使用 `pathlib.Path` 并验证安全性
- SQL 查询必须使用参数化查询（已有 `sqlite3` 参数化支持）

---

## 5. 审查清单

提交代码前，请确认：

- [ ] 所有现有测试通过
- [ ] 新增功能有对应测试
- [ ] 没有引入新的重型依赖
- [ ] 代码有完整的类型注解
- [ ] Commit message 符合规范
- [ ] 没有提交敏感信息（API 密钥等）
- [ ] 运行了 `git diff` 检查改动范围

---

## 6. 违规处理

违反上述规则的代码将：
1. 在代码审查中被要求修改
2. CI/CD 流程中可能失败（如测试不通过）
3. 严重者可能被 revert

---

## 7. 更新记录

| 日期 | 修订内容 |
|------|----------|
| 2026-05-03 | 初始版本，定义核心编码规范 |
