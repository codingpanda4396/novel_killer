# Project Status

> 最后更新：2026-05-03  
> 总结当前 NovelOps（novel_killer）项目现状，供 Agent 参考

## 1. 项目概述

NovelOps 是一个面向中文网文作者的 AI 辅助创作中台。它把项目设定、故事 bible、章节大纲、正文语料、章节生成产物、审稿报告、修订队列和 Web 看板组织到同一个工程里，支持通过 CLI、Web 界面或中文自然语言请求推进连载生产。

当前版本要求真实 LLM 可用，默认使用 DeepSeek 官方接口处理结构化任务，使用 Claude via RightCode 处理中长篇正文写作和修订。

## 2. 现有模块职责

### 核心业务模块

| 模块 | 文件路径 | 职责 |
|------|----------|------|
| **assistant** | `novelops/assistant.py` | 智能助手逻辑，处理自然语言请求，意图识别（状态查询、章节生成、审稿解释、项目初始化等），支持操作确认机制 |
| **generator** | `novelops/generator.py` | 章节生成核心逻辑，基于项目设定和章节队列自动生成草稿，内置多轮审稿-修订流程 |
| **reviewer** | `novelops/reviewer.py` | 章节审稿逻辑，输出结构化评分（总分、分项分）、问题列表、修订建议，支持分数钳制和动作标准化 |
| **planner** | `novelops/planner.py` | 章节规划，读取章节队列，生成章节规划目标和意图 |
| **prepare** | `novelops/prepare.py` | 准备阶段相关逻辑 |
| **scout** | `novelops/scout.py` | 选题/情报分析功能 |

### 项目与配置管理

| 模块 | 文件路径 | 职责 |
|------|----------|------|
| **config** | `novelops/config.py` | 配置管理、项目加载（`load_project`）、JSON 写入（`write_json`）、邀请码验证 |
| **project** | `novelops/project.py` | 项目初始化（`init_project`）、项目目录结构创建 |
| **paths** | `novelops/paths.py` | 路径管理，定义项目根目录、项目目录获取函数 |
| **readiness** | `novelops/readiness.py` | 项目准备度检查，检测项目核心文件完整性、章节队列、大纲等是否达标 |
| **framework_importer** | `novelops/framework_importer.py` | 框架导入功能，支持从 Markdown 格式创作框架直接导入，自动生成章节卡、故事设定 |

### LLM 与 AI

| 模块 | 文件路径 | 职责 |
|------|----------|------|
| **llm** | `novelops/llm.py` | LLM 客户端封装（`LLMClient`、`LLMSettings`），支持模型配置按阶段覆盖、环境变量回退、API 密钥管理 |
| **schemas** | `novelops/schemas.py` | 数据模式和结构体定义 |

### 数据与存储

| 模块 | 文件路径 | 职责 |
|------|----------|------|
| **indexer** | `novelops/indexer.py` | SQLite 索引管理，存储项目元信息、章节索引、审稿记录、修订队列，支持索引重建 |
| **corpus** | `novelops/corpus.py` | 语料库操作，章节读取、章节列表、章节信息解析 |
| **continuity** | `novelops/continuity.py` | 连续性管理，维护故事时间线、角色状态、章节摘要等 |
| **scoring** | `novelops/scoring.py` | 评分相关逻辑 |
| **publisher** | `novelops/publisher.py` | 发布相关功能 |

### 用户与 Web

| 模块 | 文件路径 | 职责 |
|------|----------|------|
| **user** | `novelops/user.py` | 用户系统，管理用户-项目关联关系、默认项目设置、项目访问权限检查 |
| **session** | `novelops/session.py` | Session 管理（itsdangerous 签名），登录态获取和设置 |
| **web** | `novelops/web.py` | FastAPI Web 服务，实现项目列表、工作台、章节详情、修订队列、框架导入等页面和 API |
| **cli** | `novelops/cli.py` | 命令行接口，提供 status、check、index、plan-next、generate、review-chapter、publish-check、serve、ask 等命令 |
| **dotenv_loader** | `novelops/dotenv_loader.py` | 环境变量自动加载（支持 `.env` 文件） |

### 迁移与工具

| 模块 | 文件路径 | 职责 |
|------|----------|------|
| **migrate_to_multi_project** | `novelops/migrate_to_multi_project.py` | 迁移脚本，从单项目迁移到多项目架构 |

## 3. 示例项目

仓库内包含示例项目 `projects/life_balance`：
- `corpus/volume_01/`：第一卷正文语料，当前 50 章
- `generation/chapter_051/`：第 51 章生成过程产物
- `reviews/`：章节审稿 JSON 和修订队列
- `bible/`、`outlines/`、`state/`：世界观、章节规划和连续性状态

## 4. 测试覆盖

测试文件：`tests/test_novelops.py`（37 个测试用例）

覆盖模块：
- 项目配置加载和验证
- 语料库章节读取和解析
- 审稿功能（含 Fake LLM 客户端）
- LLM 设置和客户端（含环境变量、配置覆盖、JSON 解析）
- 章节生成流程（含修订循环）
- 项目初始化和目录结构创建
- 章节规划
- CLI 参数解析
- SQLite 索引重建
- Web 路由和 API（含认证）
- 助手意图识别和响应
- 框架导入（预览和执行）
- 项目准备度检查

## 5. 技术栈

- **语言**：Python 3.10+
- **Web 框架**：FastAPI
- **存储**：SQLite 3
- **Session**：itsdangerous (URLSafeTimedSerializer)
- **测试**：unittest
- **CI/CD**：GitHub Actions

## 6. 当前状态

- ✅ 核心创作流程（初始化 → 生成 → 审稿 → 修订）完全可用
- ✅ 多用户、多项目、框架导入、Web 服务均已实现
- ✅ 自然语言入口（中文请求解析）已上线
- ✅ CI/CD 流程完善，测试自动运行
- ✅ 最近修复了 Web 测试的认证问题（401 错误）
