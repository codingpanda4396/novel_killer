from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_project_path, write_json
from .llm import LLMClient


def prepare_project_interactive(project_path: Path, llm_client: LLMClient | None = None) -> dict[str, Any]:
    """交互式准备新书项目
    
    通过 LLM 辅助，帮助用户填充：
    - 核心卖点
    - 主角设定
    - 金手指规则
    - 前 30 章大纲
    - 审稿 rubric
    """
    client = llm_client or LLMClient()
    project_config = load_project_path(project_path)
    
    result = {
        "story_bible_updated": False,
        "characters_updated": False,
        "power_system_updated": False,
        "chapter_queue_updated": False,
        "first_30_chapters_updated": False,
        "rubric_updated": False,
    }
    
    # 读取现有内容
    story_bible_path = project_path / "bible" / "00_story_bible.md"
    story_bible = story_bible_path.read_text(encoding="utf-8") if story_bible_path.exists() else ""
    
    # 1. 生成核心卖点和主角设定
    print("正在生成项目核心设定...")
    core_prompt = f"""请基于以下项目信息，生成详细的小说核心设定：

项目名称：{project_config.get('name')}
题材：{project_config.get('genre')}
目标平台：{project_config.get('target_platform')}

请生成：
1. 3-5 个核心卖点（每个 1-2 句话）
2. 主角基本设定（姓名、年龄、职业、性格、核心目标、初始困境）
3. 金手指/核心设定（能力描述、使用规则、限制条件、成长路径）
4. 主线冲突（主线冲突、主要对手、核心矛盾）

请以 Markdown 格式输出，结构清晰。
"""
    
    core_setting = client.complete(
        core_prompt,
        system="你是资深网文策划编辑，擅长设计商业化小说的核心设定。",
        stage="prepare_core_setting"
    )
    
    # 更新 story_bible
    story_bible_path.write_text(core_setting, encoding="utf-8")
    result["story_bible_updated"] = True
    print(f"✓ 已更新 {story_bible_path.relative_to(project_path)}")
    
    # 2. 生成角色 bible
    print("正在生成角色详细设定...")
    characters_prompt = f"""基于以下核心设定，生成详细的角色 Bible：

{core_setting}

请生成：
1. 主角的详细设定（基本信息、性格特征、行为模式、说话风格、价值观、关系网络）
2. 3-5 个主要配角的设定（姓名、与主角关系、作用、性格）

请以 Markdown 格式输出。
"""
    
    characters = client.complete(
        characters_prompt,
        system="你是资深网文策划编辑，擅长设计立体的小说角色。",
        stage="prepare_characters"
    )
    
    characters_path = project_path / "bible" / "01_characters.md"
    characters_path.write_text(characters, encoding="utf-8")
    result["characters_updated"] = True
    print(f"✓ 已更新 {characters_path.relative_to(project_path)}")
    
    # 3. 生成力量体系
    print("正在生成力量体系/设定规则...")
    power_prompt = f"""基于以下核心设定，生成详细的力量体系与设定规则：

{core_setting}

请生成：
1. 核心设定的详细规则
2. 力量等级划分（如适用）
3. 使用限制（避免无限膨胀）
4. 成长路径

请以 Markdown 格式输出。
"""
    
    power_system = client.complete(
        power_prompt,
        system="你是资深网文策划编辑，擅长设计平衡的力量体系。",
        stage="prepare_power_system"
    )
    
    power_path = project_path / "bible" / "02_power_system.md"
    power_path.write_text(power_system, encoding="utf-8")
    result["power_system_updated"] = True
    print(f"✓ 已更新 {power_path.relative_to(project_path)}")
    
    # 4. 生成前 30 章大纲
    print("正在生成前 30 章大纲...")
    outline_prompt = f"""基于以下核心设定和角色设定，生成前 30 章的详细章节卡：

核心设定：
{core_setting}

角色设定：
{characters}

请为前 30 章生成章节卡，每章包括：
- 章节标题
- 核心任务（本章要完成什么）
- 冲突/钩子（本章的主要冲突或吸引点）
- 章尾钩子（让读者继续追读的悬念）
- 推进主线（如何推进主线剧情）

前 3 章要特别详细，后面章节可以简略一些。
请以 Markdown 格式输出。
"""
    
    first_30 = client.complete(
        outline_prompt,
        system="你是资深网文策划编辑，擅长设计商业化的章节节奏。",
        stage="prepare_first_30_chapters"
    )
    
    first_30_path = project_path / "outlines" / "first_30_chapters.md"
    first_30_path.write_text(first_30, encoding="utf-8")
    result["first_30_chapters_updated"] = True
    print(f"✓ 已更新 {first_30_path.relative_to(project_path)}")
    
    # 5. 生成章节队列（前 10 章）
    print("正在生成章节队列...")
    queue_prompt = f"""基于前 30 章大纲，提取前 10 章的核心信息，生成章节队列表格：

{first_30[:2000]}

请生成一个 Markdown 表格，格式如下：
| 章号 | 工作标题 | 核心任务 | 必须承接 | 状态 |
| --- | --- | --- | --- | --- |
| 1 | ... | ... | 无 | 待生成 |

只输出表格，不要其他内容。
"""
    
    queue = client.complete(
        queue_prompt,
        system="你是网文策划助手，擅长提取章节核心信息。",
        stage="prepare_chapter_queue"
    )
    
    queue_path = project_path / "outlines" / "chapter_queue.md"
    queue_path.write_text(f"# 章节队列\n\n{queue}\n", encoding="utf-8")
    result["chapter_queue_updated"] = True
    print(f"✓ 已更新 {queue_path.relative_to(project_path)}")
    
    # 6. 生成审稿 rubric
    print("正在生成审稿 rubric...")
    rubric_prompt = f"""基于以下项目设定，提取 5-10 个项目特有的钩子词和禁写词：

{core_setting}

请生成：
1. hook_terms: 项目特有的钩子词（如金手指关键词、核心设定词）
2. forbidden_terms: 禁写内容（如违反设定的行为、逻辑漏洞）

只输出 JSON 格式：
{{
  "hook_terms": ["词1", "词2", ...],
  "forbidden_terms": ["禁写1", "禁写2", ...]
}}
"""
    
    rubric_json = client.complete_json(
        rubric_prompt,
        system="你是网文审稿助手，擅长提取项目关键词。",
        stage="prepare_rubric"
    )
    
    # 更新 project.json 的 rubric
    project_config["rubric"]["hook_terms"] = rubric_json.get("hook_terms", [])
    project_config["rubric"]["forbidden_terms"] = rubric_json.get("forbidden_terms", [])
    write_json(project_path / "project.json", project_config)
    result["rubric_updated"] = True
    print(f"✓ 已更新 project.json 的 rubric 配置")
    
    print("\n" + "="*50)
    print("✓ 新书准备完成！")
    print("已生成：")
    for key, value in result.items():
        if value:
            print(f"  - {key}")
    print("\n建议下一步：")
    print("  1. 运行 novelops readiness 检查准备度")
    print("  2. 手动审阅和调整生成的内容")
    print("  3. 运行 novelops generate 1 生成第一章")
    
    return result

