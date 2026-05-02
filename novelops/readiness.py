from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ReadinessItem:
    """单个准备度检查项"""
    name: str
    status: str  # "ok", "empty", "missing"
    message: str
    critical: bool = True


@dataclass
class ReadinessReport:
    """准备度检查报告"""
    items: list[ReadinessItem]
    ready: bool
    critical_missing: int
    warnings: int


def _check_file_content(path: Path, min_size: int = 100) -> str:
    """检查文件是否存在且有实质内容"""
    if not path.is_file():
        return "missing"
    content = path.read_text(encoding="utf-8", errors="ignore").strip()
    if len(content) < min_size:
        return "empty"
    # 检查是否只是模板占位符（更严格的检查）
    placeholder_count = content.count("【待补充")
    total_lines = len([line for line in content.split('\n') if line.strip()])
    # 如果占位符数量超过总行数的 30%，认为是空模板
    if placeholder_count > 0 and placeholder_count >= total_lines * 0.3:
        return "empty"
    return "ok"


def check_project_readiness(project_path: Path, project_config: dict[str, Any]) -> ReadinessReport:
    """检查项目是否准备好开始生成章节
    
    检查项包括：
    - 核心 bible 文件是否填写
    - 章节队列是否规划
    - 状态文件是否初始化
    - 审稿 rubric 是否配置
    """
    items: list[ReadinessItem] = []
    
    # 1. 检查项目总纲
    status = _check_file_content(project_path / "bible" / "00_story_bible.md", 200)
    items.append(ReadinessItem(
        name="项目总纲 (bible/00_story_bible.md)",
        status=status,
        message="需要填写核心卖点、主角设定、金手指规则、主线冲突" if status != "ok" else "已填写",
        critical=True
    ))
    
    # 2. 检查角色 bible
    status = _check_file_content(project_path / "bible" / "01_characters.md", 150)
    items.append(ReadinessItem(
        name="角色 Bible (bible/01_characters.md)",
        status=status,
        message="需要填写主角和主要配角的详细设定" if status != "ok" else "已填写",
        critical=True
    ))
    
    # 3. 检查力量体系/设定规则
    status = _check_file_content(project_path / "bible" / "02_power_system.md", 100)
    items.append(ReadinessItem(
        name="力量体系 (bible/02_power_system.md)",
        status=status,
        message="需要填写核心设定规则和限制条件" if status != "ok" else "已填写",
        critical=True
    ))
    
    # 4. 检查风格指南
    status = _check_file_content(project_path / "bible" / "03_style_guide.md", 100)
    items.append(ReadinessItem(
        name="风格指南 (bible/03_style_guide.md)",
        status=status,
        message="需要确定叙事风格和商业化要求" if status != "ok" else "已填写",
        critical=False
    ))
    
    # 5. 检查禁写规则
    status = _check_file_content(project_path / "bible" / "04_forbidden_rules.md", 50)
    items.append(ReadinessItem(
        name="禁写规则 (bible/04_forbidden_rules.md)",
        status=status,
        message="需要明确平台红线和题材禁忌" if status != "ok" else "已填写",
        critical=False
    ))
    
    # 6. 检查审稿检查清单
    status = _check_file_content(project_path / "bible" / "11_review_checklist.md", 100)
    items.append(ReadinessItem(
        name="审稿检查清单 (bible/11_review_checklist.md)",
        status=status,
        message="需要补充项目特有的审稿检查项" if status != "ok" else "已填写",
        critical=False
    ))
    
    # 7. 检查章节队列
    queue_path = project_path / "outlines" / "chapter_queue.md"
    status = _check_file_content(queue_path, 150)
    items.append(ReadinessItem(
        name="章节队列 (outlines/chapter_queue.md)",
        status=status,
        message="需要规划至少前 3 章的章节任务" if status != "ok" else "已规划",
        critical=True
    ))
    
    # 8. 检查卷纲
    status = _check_file_content(project_path / "outlines" / "volume_outline.md", 100)
    items.append(ReadinessItem(
        name="卷纲 (outlines/volume_outline.md)",
        status=status,
        message="需要规划第一卷的整体结构" if status != "ok" else "已规划",
        critical=False
    ))
    
    # 9. 检查前 30 章卡
    status = _check_file_content(project_path / "outlines" / "first_30_chapters.md", 200)
    items.append(ReadinessItem(
        name="前 30 章章节卡 (outlines/first_30_chapters.md)",
        status=status,
        message="建议规划前 30 章的详细章节卡" if status != "ok" else "已规划",
        critical=False
    ))
    
    # 10. 检查 rubric 配置
    rubric = project_config.get("rubric", {})
    hook_terms = rubric.get("hook_terms", [])
    forbidden_terms = rubric.get("forbidden_terms", [])
    
    if len(hook_terms) == 0:
        items.append(ReadinessItem(
            name="审稿钩子词 (project.json rubric.hook_terms)",
            status="empty",
            message="需要在 project.json 中配置项目特有的钩子词",
            critical=False
        ))
    else:
        items.append(ReadinessItem(
            name="审稿钩子词 (project.json rubric.hook_terms)",
            status="ok",
            message=f"已配置 {len(hook_terms)} 个钩子词",
            critical=False
        ))
    
    # 11. 检查状态文件初始化
    state_files = [
        ("timeline.md", "时间线"),
        ("chapter_summary.md", "章节摘要"),
        ("character_state.md", "角色状态"),
        ("active_threads.md", "活跃线索"),
    ]
    
    for filename, display_name in state_files:
        path = project_path / "state" / filename
        if not path.is_file():
            items.append(ReadinessItem(
                name=f"{display_name} (state/{filename})",
                status="missing",
                message=f"缺少 state/{filename} 文件",
                critical=False
            ))
        else:
            items.append(ReadinessItem(
                name=f"{display_name} (state/{filename})",
                status="ok",
                message="文件已创建",
                critical=False
            ))
    
    # 统计结果
    critical_missing = sum(1 for item in items if item.critical and item.status != "ok")
    warnings = sum(1 for item in items if not item.critical and item.status != "ok")
    ready = critical_missing == 0
    
    return ReadinessReport(
        items=items,
        ready=ready,
        critical_missing=critical_missing,
        warnings=warnings
    )
