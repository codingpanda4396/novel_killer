from __future__ import annotations

from pathlib import Path
from typing import Any

from .llm import LLMClient


def update_continuity_after_chapter(
    project_path: Path,
    chapter: int,
    chapter_text: str,
    llm_client: LLMClient | None = None
) -> dict[str, bool]:
    """章节生成/过审后，更新连续性文件
    
    更新内容：
    - chapter_summary.md: 添加本章摘要
    - timeline.md: 更新时间线
    - character_state.md: 更新角色状态
    - active_threads.md: 更新活跃线索
    """
    client = llm_client or LLMClient()
    result = {
        "chapter_summary_updated": False,
        "timeline_updated": False,
        "character_state_updated": False,
        "active_threads_updated": False,
    }
    
    state_dir = project_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 生成章节摘要
    summary_prompt = f"""请为以下章节生成简洁摘要，包括：
- 核心事件（2-3 句话）
- 状态变化（主角或世界的变化）
- 新增角色（如有）
- 伏笔埋设（如有）

章节正文：
{chapter_text[:2000]}

只输出摘要内容，不要其他说明。
"""
    
    summary = client.complete(
        summary_prompt,
        system="你是小说连续性追踪助手，擅长提取章节核心信息。",
        stage="continuity_summary"
    )
    
    # 追加到 chapter_summary.md
    summary_path = state_dir / "chapter_summary.md"
    existing_summary = summary_path.read_text(encoding="utf-8") if summary_path.exists() else "# 章节摘要\n\n"
    new_summary = f"{existing_summary}\n## 第 {chapter} 章\n{summary}\n"
    summary_path.write_text(new_summary, encoding="utf-8")
    result["chapter_summary_updated"] = True
    
    # 2. 更新时间线
    timeline_prompt = f"""基于以下章节内容，提取时间线信息：

{chapter_text[:2000]}

如果本章有明确的时间推进（如"第二天"、"三天后"等），请输出时间线更新。
如果没有明确时间推进，输出"无明确时间推进"。

只输出时间线信息，格式如：
- 第 X 天：发生了什么事件
"""
    
    timeline_update = client.complete(
        timeline_prompt,
        system="你是小说连续性追踪助手，擅长提取时间线信息。",
        stage="continuity_timeline"
    )
    
    if "无明确时间推进" not in timeline_update:
        timeline_path = state_dir / "timeline.md"
        existing_timeline = timeline_path.read_text(encoding="utf-8") if timeline_path.exists() else "# 时间线\n\n"
        new_timeline = f"{existing_timeline}\n{timeline_update}\n"
        timeline_path.write_text(new_timeline, encoding="utf-8")
        result["timeline_updated"] = True
    
    # 3. 更新角色状态
    character_prompt = f"""基于以下章节内容，提取主要角色的状态变化：

{chapter_text[:2000]}

请列出：
- 主角的状态变化（位置、能力、物品、关系等）
- 主要配角的状态变化

如果没有明显变化，输出"无明显状态变化"。
"""
    
    character_update = client.complete(
        character_prompt,
        system="你是小说连续性追踪助手，擅长追踪角色状态。",
        stage="continuity_character"
    )
    
    if "无明显状态变化" not in character_update:
        character_path = state_dir / "character_state.md"
        existing_character = character_path.read_text(encoding="utf-8") if character_path.exists() else "# 角色状态\n\n"
        new_character = f"{existing_character}\n## 第 {chapter} 章后\n{character_update}\n"
        character_path.write_text(new_character, encoding="utf-8")
        result["character_state_updated"] = True
    
    # 4. 更新活跃线索
    threads_prompt = f"""基于以下章节内容，提取剧情线索信息：

{chapter_text[:2000]}

请列出：
- 本章推进的主线/支线
- 本章埋设的新伏笔
- 本章回收的旧伏笔

如果没有明显线索变化，输出"无明显线索变化"。
"""
    
    threads_update = client.complete(
        threads_prompt,
        system="你是小说连续性追踪助手，擅长追踪剧情线索。",
        stage="continuity_threads"
    )
    
    if "无明显线索变化" not in threads_update:
        threads_path = state_dir / "active_threads.md"
        existing_threads = threads_path.read_text(encoding="utf-8") if threads_path.exists() else "# 活跃线索\n\n"
        new_threads = f"{existing_threads}\n## 第 {chapter} 章\n{threads_update}\n"
        threads_path.write_text(new_threads, encoding="utf-8")
        result["active_threads_updated"] = True
    
    return result
