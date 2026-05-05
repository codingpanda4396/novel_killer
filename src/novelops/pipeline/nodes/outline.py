from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...config import write_json
from ...llm import LLMClient
from ..state import PipelineState


def outline_node(state: PipelineState) -> dict[str, Any]:
    """大纲生成节点

    生成全书大纲和分卷大纲。

    输入: concept, market_data
    输出: outline, volume_outlines
    """
    concept = state.get("concept", {})
    market_data = state.get("market_data", {})
    project_path = state["project_path"]
    total_chapters = state.get("total_chapters", 30)

    if not concept:
        return {"errors": ["No concept data available for outline generation"]}

    try:
        llm = LLMClient()

        # 构建上下文
        concept_summary = json.dumps(concept, ensure_ascii=False, indent=2)
        market_summary = ""
        if market_data:
            market_summary = f"""
市场数据：
- 目标读者：{market_data.get('target_reader', '网文读者')}
- 核心标签：{', '.join(market_data.get('core_tags', market_data.get('tags', [])))}
- 开篇钩子：{market_data.get('opening_hook', market_data.get('core_hook', ''))}
"""

        # 生成全书大纲
        outline_prompt = f"""基于以下概念设计，为一部小说生成详细大纲。

概念设计：
{concept_summary}
{market_summary}

总章节数：{total_chapters} 章（约 3 卷，每卷 10 章）

请生成以下内容（JSON 格式）：
1. title: 小说标题
2. logline: 一句话概括（50 字内）
3. theme: 核心主题
4. main_plot: 主线剧情概述
5. subplots: 支线剧情列表（2-3 条）
6. climax_points: 关键高潮点（3-5 个）
7. ending: 结局走向
8. volumes: 分卷结构（每卷包含：volume_number, title, goal, chapters, key_events）

只返回 JSON 对象。"""

        outline = llm.complete_json(
            outline_prompt,
            system="你是资深网文大纲策划师，擅长设计商业化长篇小说结构。",
            stage="outline",
        )

        # 写入大纲文件
        outlines_path = project_path / "outlines"
        outlines_path.mkdir(parents=True, exist_ok=True)

        # 写入 full_outline.md
        full_outline_content = f"""# {outline.get('title', '未命名')} - 全书大纲

## 一句话概括
{outline.get('logline', '待补充')}

## 核心主题
{outline.get('theme', '待补充')}

## 主线剧情
{outline.get('main_plot', '待补充')}

## 支线剧情
"""
        for i, subplot in enumerate(outline.get('subplots', []), 1):
            full_outline_content += f"\n### 支线 {i}\n{subplot}\n"

        full_outline_content += "\n## 关键高潮点\n"
        for i, climax in enumerate(outline.get('climax_points', []), 1):
            full_outline_content += f"\n### 高潮 {i}\n{climax}\n"

        full_outline_content += f"\n## 结局走向\n{outline.get('ending', '待补充')}\n"

        (outlines_path / "full_outline.md").write_text(full_outline_content, encoding="utf-8")

        # 写入分卷大纲
        volume_outlines = []
        for vol in outline.get("volumes", []):
            vol_num = vol.get("volume_number", 1)
            vol_content = f"""# 第 {vol_num} 卷：{vol.get('title', f'第{vol_num}卷')}

## 卷目标
{vol.get('goal', '待补充')}

## 章节数
{vol.get('chapters', 10)} 章

## 关键事件
"""
            for event in vol.get("key_events", []):
                vol_content += f"- {event}\n"

            (outlines_path / f"volume_{vol_num:02d}.md").write_text(vol_content, encoding="utf-8")
            volume_outlines.append(vol)

        # 写入 chapter_queue.md
        _generate_chapter_queue(outlines_path, outline, total_chapters)

        return {
            "outline": outline,
            "volume_outlines": volume_outlines,
        }

    except Exception as e:
        return {"errors": [f"Failed to generate outline: {str(e)}"]}


def _generate_chapter_queue(outlines_path: Path, outline: dict[str, Any], total_chapters: int) -> None:
    """生成章节队列"""
    queue_content = """# 章节队列

| 章号 | 工作标题 | 核心任务 | 必须承接 | 状态 |
| --- | --- | --- | --- | --- |
"""

    volumes = outline.get("volumes", [])
    chapter_num = 1

    for vol in volumes:
        vol_chapters = vol.get("chapters", 10)
        key_events = vol.get("key_events", [])

        for i in range(vol_chapters):
            if chapter_num > total_chapters:
                break

            # 确定章节核心任务
            if i == 0:
                task = f"第{vol.get('volume_number', 1)}卷开篇，引入新冲突"
            elif i == vol_chapters - 1:
                task = f"第{vol.get('volume_number', 1)}卷高潮/收尾"
            elif key_events and i < len(key_events):
                task = key_events[i]
            else:
                task = f"推进第{vol.get('volume_number', 1)}卷主线"

            prev = "无" if chapter_num == 1 else f"第{chapter_num - 1}章"
            queue_content += f"| {chapter_num} | 第{chapter_num}章 | {task} | {prev} | 待规划 |\n"
            chapter_num += 1

    (outlines_path / "chapter_queue.md").write_text(queue_content, encoding="utf-8")
