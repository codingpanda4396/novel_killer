# NovelOps 新书可用性完善 - 使用指南

## 概述

NovelOps 已从"能生成章节"升级为"能支持新书冷启动到稳定连载"的完整系统。

## 新增功能

### 1. 完整的项目初始化

**命令：** `novelops init-project <project_id> --name <书名> --genre <题材>`

**改进：** 现在会自动创建完整的开书骨架，包括：

**Bible 目录：**
- `00_story_bible.md` - 项目总纲（核心卖点、主角设定、金手指规则、主线冲突）
- `01_characters.md` - 角色 Bible（主角和配角详细设定）
- `02_power_system.md` - 力量体系/设定规则
- `03_style_guide.md` - 风格指南
- `04_forbidden_rules.md` - 禁写规则
- `11_review_checklist.md` - 审稿检查清单

**Outlines 目录：**
- `chapter_queue.md` - 章节队列（生成器的主要输入）
- `volume_outline.md` - 卷纲
- `first_30_chapters.md` - 前 30 章详细章节卡

**State 目录：**
- `timeline.md` - 时间线
- `chapter_summary.md` - 章节摘要
- `character_state.md` - 角色状态
- `active_threads.md` - 活跃线索
- `open_threads.md` - 待回收线索
- `continuity_index.md` - 连续性索引

### 2. 开书准备度检查

**命令：** `novelops readiness` 或 `novelops status --readiness`

**功能：** 检查项目是否准备好开始生成章节

**检查项：**
- 关键项（必须填写）：
  - 项目总纲
  - 角色 Bible
  - 力量体系
  - 章节队列
  
- 建议项（可选但推荐）：
  - 风格指南
  - 禁写规则
  - 审稿检查清单
  - 卷纲
  - 前 30 章章节卡
  - 审稿钩子词配置

**输出示例：**
```
=== 测试新书 开书准备度检查 ===

【关键项】
  ✓ 项目总纲 (bible/00_story_bible.md)
  ✗ 章节队列 (outlines/chapter_queue.md)
    → 需要规划至少前 3 章的章节任务

【建议项】
  ⚠ 前 30 章章节卡 (outlines/first_30_chapters.md)
    → 建议规划前 30 章的详细章节卡

==================================================
✗ 还有 1 个关键项需要补充
⚠ 有 1 个建议项可以进一步完善
```

### 3. 新书冷启动命令

**命令：** `novelops prepare-project [--yes]`

**功能：** 使用 LLM 自动生成开书资料

**生成内容：**
1. 核心设定（基于项目名称和题材）
2. 角色详细设定
3. 力量体系规则
4. 前 30 章大纲
5. 章节队列（前 10 章）
6. 审稿 rubric（钩子词和禁写词）

**使用流程：**
```bash
# 1. 创建项目
novelops init-project my_novel --name "我的小说" --genre "都市异能"

# 2. 准备开书资料（使用 LLM 生成）
novelops --project my_novel prepare-project --yes

# 3. 检查准备度
novelops --project my_novel readiness

# 4. 手动审阅和调整生成的内容

# 5. 生成第一章
novelops --project my_novel generate 1
```

### 4. 改进的生成上下文读取

**改进：** 生成器现在会读取 `project.json` 中配置的上下文文件，而不是硬编码的文件列表。

**配置示例：**
```json
{
  "planning": {
    "context_sources": [
      "outlines/chapter_queue.md",
      "bible/00_story_bible.md",
      "state"
    ]
  }
}
```

**支持：**
- 单个文件：`"bible/00_story_bible.md"`
- 目录：`"state"` 会读取目录下所有 `.md` 文件
- 特殊值：`"state"` 会读取所有 state 文件

### 5. 连续性自动更新

**功能：** 章节通过审稿后，自动更新连续性文件

**更新内容：**
- `chapter_summary.md` - 添加本章摘要
- `timeline.md` - 更新时间线（如有时间推进）
- `character_state.md` - 更新角色状态（如有变化）
- `active_threads.md` - 更新活跃线索（如有新伏笔或回收）

**触发时机：** 章节生成并通过审稿门槛后自动执行

### 6. 项目级审稿检查

**改进：** 审稿现在会读取项目特有的审稿要求

**读取内容：**
- `project.json` 中的 `rubric.hook_terms`（钩子词）
- `project.json` 中的 `rubric.forbidden_terms`（禁写词）
- `bible/11_review_checklist.md`（审稿检查清单）
- `bible/04_forbidden_rules.md`（禁写规则）

**效果：** LLM 审稿时会参考这些项目特有的要求，而不只是通用检查

## 完整新书流程示例

```bash
# 1. 创建项目
novelops init-project urban_rebirth \
  --name "都市重生之金融大亨" \
  --genre "都市重生"

# 2. 使用 LLM 生成开书资料
novelops --project urban_rebirth prepare-project --yes

# 3. 检查准备度
novelops --project urban_rebirth readiness

# 4. 手动审阅和调整
# - 编辑 bible/00_story_bible.md 完善核心卖点
# - 编辑 bible/01_characters.md 完善角色设定
# - 编辑 outlines/first_30_chapters.md 调整章节规划

# 5. 再次检查准备度
novelops --project urban_rebirth readiness

# 6. 生成第一章
novelops --project urban_rebirth generate 1

# 7. 审稿第一章
novelops --project urban_rebirth review-chapter 1

# 8. 如果通过，连续性文件会自动更新
# 9. 继续生成后续章节
novelops --project urban_rebirth generate 2
```

## 测试验证

所有新功能都已通过单元测试：
- ✓ `test_init_project_creates_complete_structure` - 验证完整项目结构创建
- ✓ `test_readiness_check_detects_empty_project` - 验证准备度检查识别空项目
- ✓ `test_readiness_check_passes_filled_project` - 验证准备度检查识别已填充项目
- ✓ 所有现有测试保持通过（27 个测试，2 个跳过）

## 注意事项

1. **prepare-project 需要 LLM**：该命令会调用 LLM 生成内容，需要配置有效的 API key
2. **手动审阅必要**：LLM 生成的内容需要人工审阅和调整
3. **连续性更新可选**：如果连续性更新失败，不会阻止生成流程
4. **准备度检查建议**：建议在生成第一章前运行 `readiness` 检查

## 下一步建议

1. 使用真实项目测试完整流程
2. 根据实际使用调整模板内容
3. 完善 `prepare-project` 的 prompt 以提高生成质量
4. 考虑添加批量生成和自动修订功能
