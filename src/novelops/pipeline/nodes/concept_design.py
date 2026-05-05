from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...config import write_json
from ...llm import LLMClient
from ...project import init_project
from ..state import PipelineState


def concept_design_node(state: PipelineState) -> dict[str, Any]:
    """概念设计节点

    基于市场数据生成概念设计（世界观、人设、能力体系等）。

    输入: market_data
    输出: concept, bible_created
    """
    market_data = state.get("market_data")
    project_id = state["project_id"]
    project_path = state["project_path"]

    # 如果项目已存在，跳过创建
    if project_path.exists() and (project_path / "project.json").is_file():
        return {"bible_created": True}

    # 确定题材和平台
    genre = "urban_fantasy"
    platform = "fanqie"
    topic_name = "未命名项目"

    if market_data:
        genre = market_data.get("extracted_genre") or market_data.get("llm_genre") or genre
        platform = market_data.get("target_platform") or market_data.get("platform") or platform
        topic_name = market_data.get("topic_name") or market_data.get("title") or topic_name

    try:
        # 创建项目目录结构
        init_project(project_id, topic_name, genre, platform)

        # 使用 LLM 生成概念设计
        llm = LLMClient()

        market_context = ""
        if market_data:
            market_context = f"""
市场调研数据：
- 选题名称：{market_data.get('topic_name', market_data.get('title', '未知'))}
- 目标读者：{market_data.get('target_reader', '网文读者')}
- 核心标签：{', '.join(market_data.get('core_tags', market_data.get('tags', [])))}
- 开篇钩子：{market_data.get('opening_hook', market_data.get('core_hook', ''))}
- 故事种子：{market_data.get('suggested_story_seed', '')}
- 题材类型：{genre}
"""

        concept_prompt = f"""基于以下市场调研数据，为一部{genre}类型的小说生成详细的概念设计。

{market_context}

请生成以下内容（JSON 格式）：
1. world_setting: 世界观设定（时代背景、社会结构、关键设定）
2. protagonist: 主角设定（姓名、年龄、职业、性格、核心目标、初始困境）
3. supporting_characters: 2-3 个重要配角设定
4. power_system: 力量体系/金手指设定（能力描述、使用规则、限制条件、成长路径）
5. main_conflict: 主线冲突（核心矛盾、主要对手、冲突升级路径）
6. hook_points: 3-5 个核心卖点/钩子
7. style_guide: 写作风格指南（叙事视角、节奏、语言风格）

只返回 JSON 对象。"""

        concept = llm.complete_json(
            concept_prompt,
            system="你是资深网文策划编辑，擅长设计商业化小说概念。",
            stage="concept_design",
        )

        # 更新项目配置
        from ...config import load_project_path
        project_config = load_project_path(project_path)
        project_config["genre"] = genre
        project_config["target_platform"] = platform
        write_json(project_path / "project.json", project_config)

        # 写入 bible 文件
        _write_bible_files(project_path, topic_name, genre, concept)

        return {
            "concept": concept,
            "bible_created": True,
        }

    except Exception as e:
        return {
            "errors": [f"Failed to create concept design: {str(e)}"],
            "bible_created": False,
        }


def _write_bible_files(project_path: Path, name: str, genre: str, concept: dict[str, Any]) -> None:
    """写入 bible 文件"""
    bible_path = project_path / "bible"

    # 写入 story_bible.md
    world_setting = concept.get("world_setting", {})
    protagonist = concept.get("protagonist", {})
    power_system = concept.get("power_system", {})
    main_conflict = concept.get("main_conflict", {})

    story_bible = f"""# {name}

## 项目信息
- 书名：{name}
- 题材：{genre}
- 目标平台：中文网文连载平台
- 语言：简体中文

## 核心卖点
{chr(10).join(f'- {hook}' for hook in concept.get('hook_points', ['待补充']))}

## 主角设定
- 姓名：{protagonist.get('name', '待定')}
- 年龄：{protagonist.get('age', '待定')}
- 职业：{protagonist.get('occupation', '待定')}
- 性格：{protagonist.get('personality', '待定')}
- 核心目标：{protagonist.get('goal', '待定')}
- 初始困境：{protagonist.get('initial_dilemma', '待定')}

## 金手指/核心设定
- 能力描述：{power_system.get('description', '待定')}
- 使用规则：{power_system.get('rules', '待定')}
- 限制条件：{power_system.get('limitations', '待定')}
- 成长路径：{power_system.get('growth_path', '待定')}

## 主线冲突
- 核心矛盾：{main_conflict.get('core_conflict', '待定')}
- 主要对手：{main_conflict.get('antagonist', '待定')}
- 冲突升级路径：{main_conflict.get('escalation', '待定')}

## 世界观框架
{json.dumps(world_setting, ensure_ascii=False, indent=2) if isinstance(world_setting, dict) else str(world_setting)}
"""

    (bible_path / "00_story_bible.md").write_text(story_bible, encoding="utf-8")

    # 写入 characters.md
    characters_content = "# 角色 Bible\n\n## 主角\n"
    characters_content += json.dumps(protagonist, ensure_ascii=False, indent=2) if protagonist else "待补充"
    characters_content += "\n\n## 主要配角\n"

    for i, char in enumerate(concept.get("supporting_characters", []), 1):
        characters_content += f"\n### 配角 {i}\n"
        characters_content += json.dumps(char, ensure_ascii=False, indent=2)

    (bible_path / "01_characters.md").write_text(characters_content, encoding="utf-8")

    # 写入 power_system.md
    power_content = f"""# 力量体系与设定规则

## 核心设定
{json.dumps(power_system, ensure_ascii=False, indent=2) if power_system else '待补充'}
"""
    (bible_path / "02_power_system.md").write_text(power_content, encoding="utf-8")

    # 写入 style_guide.md
    style_guide = concept.get("style_guide", {})
    style_content = f"""# 风格指南

## 叙事风格
{json.dumps(style_guide, ensure_ascii=False, indent=2) if style_guide else '待补充'}

## 商业化要求
- 每章必须有冲突或悬念
- 章尾必须有追读钩子
- 避免大段心理描写和环境描写
- 对话要推动剧情
"""
    (bible_path / "03_style_guide.md").write_text(style_content, encoding="utf-8")
