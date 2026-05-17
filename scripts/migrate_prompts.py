"""迁移硬编码提示词到SQLite数据库

扫描所有pipeline nodes中的提示词，提取并导入到数据库
"""
from __future__ import annotations

import sys
from pathlib import Path

# 添加项目根目录到path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from novelops.prompt.store import PromptStore
from novelops.prompt.engine import PromptTemplate, ParamDef, ParamType


# 从现有代码中提取的提示词模板
EXTRACTED_TEMPLATES = [
    PromptTemplate(
        id="draft_v1",
        stage="draft",
        name="章节初稿生成",
        description="生成章节初稿",
        system_prompt="你是长篇商业小说写手，只输出章节正文。",
        user_prompt_template="""请根据以下计划写出完整章节初稿。

项目摘要：
{{memory_context}}

章节计划：
{{chapter_context}}

要求：
1. 中文网文风格，保留强钩子
2. 字数 {{min_words}}-{{max_words}} 字
3. 只输出正文，不要标题和说明
4. 章尾必须有追读钩子""",
        params=[
            ParamDef(
                name="memory_context",
                type=ParamType.TEXT,
                description="项目记忆上下文",
                required=True,
            ),
            ParamDef(
                name="chapter_context",
                type=ParamType.TEXT,
                description="章节计划上下文",
                required=True,
            ),
            ParamDef(
                name="min_words",
                type=ParamType.SLIDER,
                description="最小字数",
                default=1800,
                min=1000,
                max=3000,
            ),
            ParamDef(
                name="max_words",
                type=ParamType.SLIDER,
                description="最大字数",
                default=3200,
                min=2000,
                max=5000,
            ),
        ],
        is_default=True,
    ),
    PromptTemplate(
        id="commercial_review",
        stage="commercial_review",
        name="商业审稿",
        description="强化冲突、爽点、悬念和章尾追读",
        system_prompt="你是网文商业优化专家，专注于提升章节的商业吸引力。",
        user_prompt_template="""请强化以下章节的冲突、爽点、悬念和章尾追读，不改变核心事实。

原文：
{{draft_content}}

优化要求：
1. 增强冲突和矛盾
2. 添加爽点和反转
3. 强化悬念和章尾钩子
4. 保持原有情节主线
5. 字数 {{min_words}}-{{max_words}} 字""",
        params=[
            ParamDef(
                name="draft_content",
                type=ParamType.TEXT,
                description="原始草稿内容",
                required=True,
            ),
            ParamDef(
                name="min_words",
                type=ParamType.SLIDER,
                description="最小字数",
                default=1800,
                min=1000,
                max=3000,
            ),
            ParamDef(
                name="max_words",
                type=ParamType.SLIDER,
                description="最大字数",
                default=3200,
                min=2000,
                max=5000,
            ),
        ],
        is_default=True,
    ),
    PromptTemplate(
        id="continuity_check",
        stage="continuity_check",
        name="连续性检查",
        description="检查逻辑连贯性和润色",
        system_prompt="你是专业的网文编辑，负责检查章节的连续性和逻辑性。",
        user_prompt_template="""请对以下章节进行连续性检查和润色。

章节内容：
{{chapter_content}}

前文摘要：
{{previous_summary}}

检查要求：
1. 时间线是否连贯
2. 人物行为是否一致
3. 情节逻辑是否合理
4. 发现问题请标注并给出修改建议
5. 如无问题，直接返回润色后的版本""",
        params=[
            ParamDef(
                name="chapter_content",
                type=ParamType.TEXT,
                description="章节内容",
                required=True,
            ),
            ParamDef(
                name="previous_summary",
                type=ParamType.TEXT,
                description="前文摘要",
                default="",
            ),
        ],
        is_default=True,
    ),
    PromptTemplate(
        id="outline_v1",
        stage="outline",
        name="大纲生成",
        description="生成章节大纲",
        system_prompt="你是专业的小说大纲策划师。",
        user_prompt_template="""基于以下概念设计，为一部小说生成详细大纲。

概念设计：
{{concept}}

生成要求：
1. 包含世界观设定
2. 主要人物设定
3. 前30章的章节大纲
4. 每章包含：标题、主要事件、冲突点、钩子""",
        params=[
            ParamDef(
                name="concept",
                type=ParamType.TEXT,
                description="概念设计内容",
                required=True,
            ),
        ],
        is_default=True,
    ),
    PromptTemplate(
        id="concept_design",
        stage="concept_design",
        name="概念设计",
        description="基于市场调研生成小说概念",
        system_prompt="你是资深网文策划专家，擅长设计有商业潜力的小说概念。",
        user_prompt_template="""基于以下市场调研数据，为一部{{genre}}类型的小说生成详细的概念设计。

市场数据：
{{market_data}}

设计要求：
1. 核心设定（世界观、核心冲突）
2. 主角模板（背景、金手指、成长路径）
3. 核心爽点和钩子
4. 目标读者画像
5. 差异化竞争点""",
        params=[
            ParamDef(
                name="genre",
                type=ParamType.SELECT,
                description="小说类型",
                options=["仙侠修真", "都市异能", "现代言情", "悬疑推理", "玄幻奇幻", "历史军事"],
                default="都市异能",
            ),
            ParamDef(
                name="market_data",
                type=ParamType.TEXT,
                description="市场调研数据",
                required=True,
            ),
        ],
        is_default=True,
    ),
    PromptTemplate(
        id="review_v1",
        stage="review",
        name="审稿评估",
        description="对章节进行审稿评分",
        system_prompt="你是专业的网文审稿编辑，负责评估章节质量。",
        user_prompt_template="""请审稿第 {{chapter}} 章，阈值 {{threshold}}。

章节内容：
{{chapter_content}}

审稿维度：
1. 字数和格式（{{weight_word_count}}分）
2. 段落密度（{{weight_paragraph}}分）
3. 对话密度（{{weight_dialogue}}分）
4. 钩子词使用（{{weight_hook}}分）
5. 情节推进（{{weight_plot}}分）
6. 人物塑造（{{weight_character}}分）

请返回JSON格式的审稿结果：
{
  "score": 总分,
  "passed": true/false,
  "dimension_scores": {},
  "issues": [],
  "suggestions": []
}""",
        params=[
            ParamDef(
                name="chapter",
                type=ParamType.INT,
                description="章节号",
                required=True,
            ),
            ParamDef(
                name="threshold",
                type=ParamType.SLIDER,
                description="通过阈值",
                default=80,
                min=60,
                max=100,
            ),
            ParamDef(
                name="chapter_content",
                type=ParamType.TEXT,
                description="章节内容",
                required=True,
            ),
            ParamDef(
                name="weight_word_count",
                type=ParamType.SLIDER,
                description="字数权重",
                default=14,
                min=0,
                max=30,
            ),
            ParamDef(
                name="weight_paragraph",
                type=ParamType.SLIDER,
                description="段落密度权重",
                default=8,
                min=0,
                max=20,
            ),
            ParamDef(
                name="weight_dialogue",
                type=ParamType.SLIDER,
                description="对话密度权重",
                default=8,
                min=0,
                max=20,
            ),
            ParamDef(
                name="weight_hook",
                type=ParamType.SLIDER,
                description="钩子词权重",
                default=10,
                min=0,
                max=20,
            ),
            ParamDef(
                name="weight_plot",
                type=ParamType.SLIDER,
                description="情节推进权重",
                default=15,
                min=0,
                max=30,
            ),
            ParamDef(
                name="weight_character",
                type=ParamType.SLIDER,
                description="人物塑造权重",
                default=10,
                min=0,
                max=20,
            ),
        ],
        is_default=True,
    ),
    PromptTemplate(
        id="chapter_plan",
        stage="chapter_plan",
        name="章节规划",
        description="规划具体章节内容",
        system_prompt="你是网文章节规划专家，擅长设计有吸引力的章节结构。",
        user_prompt_template="""请为第 {{chapter}} 章生成详细的章节计划。

前文摘要：
{{previous_summary}}

大纲要求：
{{outline_requirements}}

规划内容：
1. 章节标题
2. 核心目标（本章要达成什么）
3. 主要场景（2-3个关键场景）
4. 冲突设计（核心矛盾）
5. 钩子设计（章尾悬念）
6. 预计字数""",
        params=[
            ParamDef(
                name="chapter",
                type=ParamType.INT,
                description="章节号",
                required=True,
            ),
            ParamDef(
                name="previous_summary",
                type=ParamType.TEXT,
                description="前文摘要",
                default="",
            ),
            ParamDef(
                name="outline_requirements",
                type=ParamType.TEXT,
                description="大纲要求",
                required=True,
            ),
        ],
        is_default=True,
    ),
]


def migrate_prompts():
    """迁移提示词到数据库"""
    print("开始迁移提示词到数据库...")

    store = PromptStore()

    migrated = 0
    skipped = 0

    for template in EXTRACTED_TEMPLATES:
        existing = store.get(template.id)
        if existing:
            print(f"  跳过已存在: {template.id}")
            skipped += 1
            continue

        store.create(template)
        print(f"  已迁移: {template.id} - {template.name}")
        migrated += 1

    print(f"\n迁移完成: {migrated} 新增, {skipped} 跳过")


def verify_migration():
    """验证迁移结果"""
    print("\n验证迁移结果:")

    store = PromptStore()
    templates = store.list_all()

    print(f"数据库中共有 {len(templates)} 个模板:")
    for t in templates:
        print(f"  - {t.id}: {t.name} (stage={t.stage}, params={len(t.params)})")


if __name__ == "__main__":
    migrate_prompts()
    verify_migration()
