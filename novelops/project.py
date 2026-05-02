from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import ConfigError, write_json
from .paths import project_dir


STANDARD_DIRS = [
    "bible",
    "outlines",
    "state",
    "corpus",
    "generation",
    "reviews",
    "publish",
    "intelligence/raw/manual_notes",
    "intelligence/processed",
    "intelligence/reports",
]


def default_project_config(project_id: str, name: str, genre: str, target_platform: str = "中文网文连载平台") -> dict[str, Any]:
    return {
        "id": project_id,
        "name": name,
        "genre": genre,
        "target_platform": target_platform,
        "language": "zh-CN",
        "chapter_length": {"min": 1800, "target": 2500, "max": 3200},
        "review_thresholds": {"chapter": 80, "publish": 80},
        "current_volume": {"number": 1, "status": "planning", "last_completed_chapter": 0, "next_chapter": 1},
        "planning": {
            "default_strategy": "queue_first_then_bible_state",
            "context_sources": ["outlines/chapter_queue.md", "bible/00_story_bible.md", "state"],
            "require_chapter_queue": False,
        },
        "rubric": {
            "hook_terms": [],
            "forbidden_terms": [],
            "weights": {"word_count": 14, "paragraph_density": 8, "dialogue_density": 8, "hook_terms": 10},
        },
        "directories": {
            "bible": "bible",
            "outlines": "outlines",
            "corpus": "corpus",
            "state": "state",
            "generation": "generation",
            "reviews": "reviews",
            "intelligence": "intelligence",
            "publish": "publish",
        },
    }


def init_project(project_id: str, name: str, genre: str, target_platform: str = "中文网文连载平台") -> Path:
    if "/" in project_id or "\\" in project_id or not project_id.strip():
        raise ConfigError("project_id must be a simple directory name")
    path = project_dir(project_id)
    if path.exists():
        raise ConfigError(f"Project already exists: {path}")
    for item in STANDARD_DIRS:
        (path / item).mkdir(parents=True, exist_ok=True)
    (path / "corpus" / "volume_01").mkdir(parents=True, exist_ok=True)
    (path / "publish" / "ready").mkdir(parents=True, exist_ok=True)
    write_json(path / "project.json", default_project_config(project_id, name, genre, target_platform))
    _init_bible_files(path, name, genre)
    _init_outline_files(path)
    _init_state_files(path)
    return path


def _write_once(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _init_bible_files(path: Path, name: str, genre: str) -> None:
    """初始化 bible 目录的完整开书资料"""
    bible = path / "bible"
    
    # 00_story_bible.md - 项目总纲
    _write_once(bible / "00_story_bible.md", f"""# {name}

## 项目信息
- 书名：{name}
- 题材：{genre}
- 目标平台：中文网文连载平台
- 语言：简体中文

## 核心卖点
【待补充：3-5 个核心卖点，每个卖点 1-2 句话】

1. 
2. 
3. 

## 主角设定
【待补充：主角姓名、年龄、职业、性格、核心目标、初始困境】

- 姓名：
- 年龄：
- 职业：
- 性格：
- 核心目标：
- 初始困境：

## 金手指/核心设定
【待补充：金手指规则、限制、成长路径】

- 能力描述：
- 使用规则：
- 限制条件：
- 成长路径：

## 主线冲突
【待补充：主线冲突、对手、核心矛盾】

- 主线冲突：
- 主要对手：
- 核心矛盾：

## 世界观框架
【待补充：故事发生的世界、时代背景、社会结构】

""")
    
    # 01_characters.md - 角色 bible
    _write_once(bible / "01_characters.md", """# 角色 Bible

## 主角
【待补充：主角详细设定】

### 基本信息
- 姓名：
- 年龄：
- 职业：
- 外貌：

### 性格特征
- 核心性格：
- 行为模式：
- 说话风格：
- 价值观：

### 关系网络
- 家庭：
- 朋友：
- 敌人：

## 主要配角
【待补充：每个重要配角的设定】

### 配角 1
- 姓名：
- 关系：
- 作用：
- 性格：

""")
    
    # 02_power_system.md - 力量体系/设定规则
    _write_once(bible / "02_power_system.md", f"""# 力量体系与设定规则

## 核心设定
【待补充：{genre} 的核心设定规则】

## 力量等级
【如适用，补充力量等级划分】

## 使用限制
【待补充：设定的限制条件，避免无限膨胀】

## 成长路径
【待补充：主角如何成长、突破】

""")
    
    # 03_style_guide.md - 风格指南
    _write_once(bible / "03_style_guide.md", f"""# 风格指南

## 叙事风格
- 视角：第三人称全知/第一人称（待确定）
- 节奏：快节奏爽文/慢热剧情向（待确定）
- 语言风格：网文口语化/文学化（待确定）

## {genre} 类型要求
【待补充：该题材的典型写法、读者期待】

## 商业化要求
- 每章必须有冲突或悬念
- 章尾必须有追读钩子
- 避免大段心理描写和环境描写
- 对话要推动剧情

## 禁写规则
【待补充：平台禁忌、题材禁忌】

""")
    
    # 04_forbidden_rules.md - 禁写规则
    _write_once(bible / "04_forbidden_rules.md", """# 禁写规则

## 平台红线
【待补充：目标平台的内容审核红线】

- 政治敏感
- 色情暴力
- 封建迷信
- 其他

## 题材禁忌
【待补充：本题材特有的禁写内容】

## 逻辑禁忌
【待补充：设定内不能违反的逻辑】

## AI 痕迹规避
【待补充：需要规避的 AI 写作痕迹】

- 避免"仿佛"、"似乎"等模糊词
- 避免过度对称的句式
- 避免机械化的情绪描写

""")
    
    # 11_review_checklist.md - 审稿检查清单
    _write_once(bible / "11_review_checklist.md", f"""# 审稿检查清单

## 基础指标
- [ ] 字数：1800-3200 字
- [ ] 段落密度：合理
- [ ] 对话密度：合理

## 题材卖点
【待补充：本项目特有的卖点检查项】

- [ ] 核心卖点是否体现
- [ ] 金手指使用是否符合规则
- [ ] 

## 人物一致性
- [ ] 主角行为符合人设
- [ ] 配角表现一致
- [ ] 对话风格统一

## 设定合规
- [ ] 未违反力量体系规则
- [ ] 未违反世界观设定
- [ ] 未违反禁写规则

## 商业化要求
- [ ] 章内有冲突或悬念
- [ ] 章尾有追读钩子
- [ ] 节奏流畅不拖沓

## AI 痕迹检查
- [ ] 无明显 AI 写作痕迹
- [ ] 语言自然流畅
- [ ] 情绪表达真实

## 平台风险
- [ ] 无政治敏感内容
- [ ] 无色情暴力内容
- [ ] 无其他平台禁忌

""")


def _init_outline_files(path: Path) -> None:
    """初始化 outlines 目录的规划文件"""
    outlines = path / "outlines"
    
    # chapter_queue.md - 章节队列
    _write_once(outlines / "chapter_queue.md", """# 章节队列

【说明：章节队列是生成器的主要输入，每一行代表一章的核心任务】

| 章号 | 工作标题 | 核心任务 | 必须承接 | 状态 |
| --- | --- | --- | --- | --- |
| 1 | 【待补充】 | 【待补充：第 1 章要完成什么】 | 无 | 待规划 |
| 2 | 【待补充】 | 【待补充：第 2 章要完成什么】 | 第 1 章 | 待规划 |
| 3 | 【待补充】 | 【待补充：第 3 章要完成什么】 | 第 2 章 | 待规划 |

""")
    
    # volume_outline.md - 卷纲
    _write_once(outlines / "volume_outline.md", """# 卷纲

## 第一卷：【待补充卷名】

### 卷目标
【待补充：本卷要完成什么故事目标】

### 卷结构
- 开局（1-10 章）：【待补充】
- 发展（11-20 章）：【待补充】
- 高潮（21-30 章）：【待补充】

### 卷末状态
【待补充：本卷结束时，主角达到什么状态，世界发生什么变化】

""")
    
    # first_30_chapters.md - 前 30 章卡
    _write_once(outlines / "first_30_chapters.md", """# 前 30 章章节卡

【说明：前 30 章是新书最关键的部分，需要详细规划每一章】

## 第 1 章：【待补充章节标题】
- 核心任务：【待补充】
- 冲突/钩子：【待补充】
- 章尾钩子：【待补充】
- 推进主线：【待补充】

## 第 2 章：【待补充章节标题】
- 核心任务：【待补充】
- 冲突/钩子：【待补充】
- 章尾钩子：【待补充】
- 推进主线：【待补充】

## 第 3 章：【待补充章节标题】
- 核心任务：【待补充】
- 冲突/钩子：【待补充】
- 章尾钩子：【待补充】
- 推进主线：【待补充】

【继续补充到第 30 章】

""")


def _init_state_files(path: Path) -> None:
    """初始化 state 目录的连续性追踪文件"""
    state = path / "state"
    
    # timeline.md - 时间线
    _write_once(state / "timeline.md", """# 时间线

【说明：记录故事内时间流逝和重要事件】

## 第 1 天
- 【待补充：第 1 天发生的事件】

## 第 2 天
- 【待补充：第 2 天发生的事件】

""")
    
    # chapter_summary.md - 章节摘要
    _write_once(state / "chapter_summary.md", """# 章节摘要

【说明：每章生成后，记录该章的核心事件和状态变化】

## 第 1 章
- 核心事件：【待补充】
- 状态变化：【待补充】
- 新增角色：【待补充】
- 伏笔埋设：【待补充】

""")
    
    # character_state.md - 角色状态
    _write_once(state / "character_state.md", """# 角色状态

【说明：追踪主要角色的当前状态、位置、关系】

## 主角
- 当前位置：【待补充】
- 当前状态：【待补充】
- 能力等级：【待补充】
- 重要物品：【待补充】

## 主要配角
### 配角 1
- 当前位置：【待补充】
- 当前状态：【待补充】
- 与主角关系：【待补充】

""")
    
    # active_threads.md - 活跃线索
    _write_once(state / "active_threads.md", """# 活跃线索

【说明：追踪当前正在推进的剧情线索和伏笔】

## 主线
- 【待补充：当前主线进展】

## 支线
- 【待补充：当前支线进展】

## 伏笔
- 【待补充：已埋设但未回收的伏笔】

""")
    
    # open_threads.md - 待回收线索
    _write_once(state / "open_threads.md", """# 待回收线索

【说明：记录已埋设但尚未回收的伏笔和线索】

| 线索 | 埋设章节 | 预计回收章节 | 状态 |
| --- | --- | --- | --- |
| 【待补充】 | 【待补充】 | 【待补充】 | 待回收 |

""")
    
    # continuity_index.md - 连续性索引
    _write_once(state / "continuity_index.md", """# 连续性索引

【说明：快速查找关键设定和事件的索引】

## 关键设定
- 金手指规则：见 bible/02_power_system.md
- 主角人设：见 bible/01_characters.md

## 重要事件
- 【待补充：重要事件及其发生章节】

## 角色首次登场
- 主角：第 1 章
- 【待补充：其他角色】

""")
