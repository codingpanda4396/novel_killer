from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import tempfile
from typing import Any

from .config import ConfigError, write_json
from .llm import LLMClient
from .paths import project_dir
from .project import STANDARD_DIRS, default_project_config
from .readiness import ReadinessReport, check_framework_readiness


DEFAULT_TARGET_PLATFORM = "番茄免费阅读冷启动测试"


@dataclass
class ChapterCard:
    chapter: int
    title: str
    objective: str
    conflict: str
    payoff: str
    ending_hook: str
    must_continue_from: str


@dataclass
class FrameworkImportSpec:
    title: str
    genre: str
    target_platform: str
    one_sentence_pitch: str
    tags: list[str] = field(default_factory=list)
    commercial_positioning: str = ""
    core_selling_points: list[str] = field(default_factory=list)
    protagonist: dict[str, Any] = field(default_factory=dict)
    main_antagonists: list[dict[str, Any]] = field(default_factory=list)
    supporting_characters: list[dict[str, Any]] = field(default_factory=list)
    world_rules: list[str] = field(default_factory=list)
    power_system: dict[str, Any] = field(default_factory=dict)
    phase_targets: dict[str, str] = field(default_factory=dict)
    required_beats: list[str] = field(default_factory=list)
    forbidden_moves: list[str] = field(default_factory=list)
    hook_terms: list[str] = field(default_factory=list)
    forbidden_terms: list[str] = field(default_factory=list)
    chapter_cards: list[ChapterCard] = field(default_factory=list)


@dataclass
class ImportPreview:
    project_id: str
    spec: FrameworkImportSpec
    files: list[str]
    readiness: ReadinessReport | None = None

    def summary(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.spec.title,
            "genre": self.spec.genre,
            "target_platform": self.spec.target_platform,
            "chapter_cards": len(self.spec.chapter_cards),
            "first_40_complete": len(self.spec.chapter_cards) >= 40,
            "files": self.files,
            "readiness": _readiness_to_dict(self.readiness) if self.readiness else None,
        }


def extract_framework_spec(markdown: str, llm_client: LLMClient | None = None) -> FrameworkImportSpec:
    if not markdown.strip():
        raise ConfigError("framework markdown is empty")
    client = llm_client or LLMClient()
    data = client.complete_json(
        _extract_prompt(markdown),
        system="你是中文网文商业策划编辑。只返回符合要求的 JSON，不要附加解释。",
        stage="framework_extract",
    )
    return parse_framework_spec(data)


def parse_framework_spec(data: dict[str, Any]) -> FrameworkImportSpec:
    cards = [parse_chapter_card(item, idx + 1) for idx, item in enumerate(_list(data.get("chapter_cards")))]
    spec = FrameworkImportSpec(
        title=str(data.get("title") or "").strip(),
        genre=str(data.get("genre") or "").strip(),
        target_platform=str(data.get("target_platform") or DEFAULT_TARGET_PLATFORM).strip(),
        one_sentence_pitch=str(data.get("one_sentence_pitch") or "").strip(),
        tags=_string_list(data.get("tags")),
        commercial_positioning=str(data.get("commercial_positioning") or "").strip(),
        core_selling_points=_string_list(data.get("core_selling_points")),
        protagonist=_dict(data.get("protagonist")),
        main_antagonists=[_dict(item) for item in _list(data.get("main_antagonists"))],
        supporting_characters=[_dict(item) for item in _list(data.get("supporting_characters"))],
        world_rules=_string_list(data.get("world_rules")),
        power_system=_dict(data.get("power_system")),
        phase_targets=_dict(data.get("phase_targets")),
        required_beats=_string_list(data.get("required_beats")),
        forbidden_moves=_string_list(data.get("forbidden_moves")),
        hook_terms=_string_list(data.get("hook_terms")),
        forbidden_terms=_string_list(data.get("forbidden_terms")),
        chapter_cards=cards,
    )
    validate_framework_spec(spec)
    return spec


def parse_chapter_card(data: Any, default_chapter: int) -> ChapterCard:
    item = _dict(data)
    return ChapterCard(
        chapter=int(item.get("chapter") or item.get("章号") or default_chapter),
        title=str(item.get("title") or item.get("工作标题") or "").strip(),
        objective=str(item.get("objective") or item.get("核心任务") or "").strip(),
        conflict=str(item.get("conflict") or item.get("冲突") or "").strip(),
        payoff=str(item.get("爽点") or item.get("satisfaction") or item.get("payoff") or "").strip(),
        ending_hook=str(item.get("ending_hook") or item.get("章尾钩子") or "").strip(),
        must_continue_from=str(item.get("must_continue_from") or item.get("必须承接") or "").strip(),
    )


def validate_framework_spec(spec: FrameworkImportSpec) -> None:
    missing = []
    for attr in ["title", "genre", "target_platform", "one_sentence_pitch", "commercial_positioning"]:
        if not getattr(spec, attr):
            missing.append(attr)
    if len(spec.chapter_cards) < 40:
        missing.append("chapter_cards[1-40]")
    phases = {"0-2万字", "2-5万字", "5-8万字", "8-10万字"}
    if not phases.issubset(set(spec.phase_targets)):
        missing.append("phase_targets")
    for index, card in enumerate(spec.chapter_cards[:40], 1):
        if card.chapter != index:
            missing.append(f"chapter_cards[{index}].chapter")
        for attr in ["title", "objective", "conflict", "payoff", "ending_hook", "must_continue_from"]:
            if not getattr(card, attr):
                missing.append(f"chapter_cards[{index}].{attr}")
    if missing:
        raise ConfigError("Invalid framework import spec: missing " + ", ".join(missing[:12]))


def preview_framework_import(
    project_id: str,
    markdown: str,
    name: str | None = None,
    target_platform: str | None = None,
    llm_client: LLMClient | None = None,
) -> ImportPreview:
    spec = extract_framework_spec(markdown, llm_client=llm_client)
    apply_overrides(spec, name=name, target_platform=target_platform)
    return ImportPreview(project_id=project_id, spec=spec, files=planned_files(), readiness=preview_readiness(project_id, spec))


def import_framework_project(
    project_id: str,
    markdown: str,
    name: str | None = None,
    target_platform: str | None = None,
    llm_client: LLMClient | None = None,
) -> ImportPreview:
    preview = preview_framework_import(project_id, markdown, name=name, target_platform=target_platform, llm_client=llm_client)
    path = project_dir(project_id)
    if "/" in project_id or "\\" in project_id or not project_id.strip():
        raise ConfigError("project_id must be a simple directory name")
    if path.exists():
        raise ConfigError(f"Project already exists: {path}")
    for item in STANDARD_DIRS + ["corpus/volume_01", "publish/ready", "records"]:
        (path / item).mkdir(parents=True, exist_ok=True)
    write_import_files(path, project_id, preview.spec)
    preview.readiness = check_framework_readiness(path, _project_config(project_id, preview.spec))
    write_json(path / "import_report.json", preview.summary())
    if not preview.readiness.ready:
        raise ConfigError(f"Framework readiness failed: {preview.readiness.critical_missing} critical issue(s). Project kept at {path}")
    return preview


def apply_overrides(spec: FrameworkImportSpec, name: str | None = None, target_platform: str | None = None) -> None:
    if name:
        spec.title = name.strip()
    if target_platform:
        spec.target_platform = target_platform.strip()
    if not spec.target_platform:
        spec.target_platform = DEFAULT_TARGET_PLATFORM


def planned_files() -> list[str]:
    return [
        "project.json",
        "bible/00_story_bible.md",
        "bible/01_characters.md",
        "bible/02_power_system.md",
        "bible/03_style_guide.md",
        "bible/04_forbidden_rules.md",
        "bible/11_review_checklist.md",
        "outlines/volume_outline.md",
        "outlines/first_40_chapters.md",
        "outlines/chapter_queue.md",
        "state/timeline.md",
        "state/chapter_summary.md",
        "state/character_state.md",
        "state/active_threads.md",
        "records/upload_records.md",
        "records/data_feedback.md",
        "records/prompt_iterations.md",
        "import_report.json",
    ]


def preview_readiness(project_id: str, spec: FrameworkImportSpec) -> ReadinessReport:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / project_id
        for item in STANDARD_DIRS + ["corpus/volume_01", "publish/ready", "records"]:
            (path / item).mkdir(parents=True, exist_ok=True)
        write_import_files(path, project_id, spec)
        return check_framework_readiness(path, _project_config(project_id, spec))


def write_import_files(path: Path, project_id: str, spec: FrameworkImportSpec) -> None:
    write_json(path / "project.json", _project_config(project_id, spec))
    _write(path / "bible" / "00_story_bible.md", story_bible(spec))
    _write(path / "bible" / "01_characters.md", characters_bible(spec))
    _write(path / "bible" / "02_power_system.md", power_system_bible(spec))
    _write(path / "bible" / "03_style_guide.md", style_guide(spec))
    _write(path / "bible" / "04_forbidden_rules.md", forbidden_rules(spec))
    _write(path / "bible" / "11_review_checklist.md", review_checklist(spec))
    _write(path / "outlines" / "volume_outline.md", volume_outline(spec))
    _write(path / "outlines" / "first_40_chapters.md", first_40_chapters(spec))
    _write(path / "outlines" / "chapter_queue.md", chapter_queue(spec))
    _write(path / "state" / "timeline.md", "# 时间线\n\n## 导入初始状态\n- 开局从第 1 章章节队列开始推进。\n")
    _write(path / "state" / "chapter_summary.md", "# 章节摘要\n\n尚未生成正文。生成每章后在此记录核心事件、状态变化、伏笔埋设与回收。\n")
    _write(path / "state" / "character_state.md", "# 角色状态\n\n## 主角\n" + bullet_dict(spec.protagonist) + "\n")
    _write(path / "state" / "active_threads.md", "# 活跃线索\n\n" + bullets(spec.required_beats or ["按前 40 章队列推进冷启动测试。"]))
    _write(path / "state" / "open_threads.md", "# 待回收线索\n\n| 线索 | 埋设章节 | 预计回收章节 | 状态 |\n| --- | --- | --- | --- |\n")
    _write(path / "state" / "continuity_index.md", "# 连续性索引\n\n- 项目总纲：bible/00_story_bible.md\n- 力量体系：bible/02_power_system.md\n- 前 40 章队列：outlines/chapter_queue.md\n")
    _write(path / "records" / "upload_records.md", "# 上传记录\n\n| 日期 | 平台 | 章节范围 | 字数 | 备注 |\n| --- | --- | --- | --- | --- |\n")
    _write(path / "records" / "data_feedback.md", "# 数据反馈\n\n| 日期 | 章节范围 | 曝光 | 阅读 | 追读 | 收藏 | 备注 |\n| --- | --- | --- | --- | --- | --- | --- |\n")
    _write(path / "records" / "prompt_iterations.md", "# 提示词迭代\n\n| 日期 | 触发问题 | 调整内容 | 验证结果 |\n| --- | --- | --- | --- |\n")


def _project_config(project_id: str, spec: FrameworkImportSpec) -> dict[str, Any]:
    cfg = default_project_config(project_id, spec.title, spec.genre, spec.target_platform)
    cfg["planning"]["context_sources"] = [
        "outlines/chapter_queue.md",
        "bible/00_story_bible.md",
        "bible/02_power_system.md",
        "bible/11_review_checklist.md",
        "state",
    ]
    cfg["planning"]["require_chapter_queue"] = True
    cfg["rubric"]["hook_terms"] = spec.hook_terms
    cfg["rubric"]["forbidden_terms"] = spec.forbidden_terms
    return cfg


def story_bible(spec: FrameworkImportSpec) -> str:
    return f"""# {spec.title}

## 商业定位
{spec.commercial_positioning}

## 一句话卖点
{spec.one_sentence_pitch}

## 核心标签
{bullets(spec.tags)}

## 核心卖点
{bullets(spec.core_selling_points)}

## 主线冲突
{bullets(spec.required_beats)}

## 世界规则
{bullets(spec.world_rules)}

## 0-10 万字阶段目标
{phase_lines(spec.phase_targets)}
"""


def characters_bible(spec: FrameworkImportSpec) -> str:
    return f"""# 角色 Bible

## 主角设定
{bullet_dict(spec.protagonist)}

## 主要反派
{dict_list(spec.main_antagonists)}

## 关键配角
{dict_list(spec.supporting_characters) if spec.supporting_characters else "- 暂无，按章节队列逐步补充。"}

## 角色行为边界
{bullets(spec.forbidden_moves)}
"""


def power_system_bible(spec: FrameworkImportSpec) -> str:
    return f"""# 力量体系与设定规则

## 香火/金手指规则
{bullet_dict(_dict(spec.power_system.get("rules")) or spec.power_system)}

## 等级路径 / 成长路径
{bullet_any(spec.power_system.get("growth_path") or spec.power_system.get("levels") or spec.power_system.get("等级路径"))}

## 限制条件
{bullet_any(spec.power_system.get("limits") or spec.power_system.get("限制条件") or ["力量使用必须有代价、冷却或资源约束。"])}

## 每 10 章升级节奏要求
- 1-10 章：金手指出现，完成第一次显圣或反杀，并打出第一次大打脸。
- 11-20 章：规则边界扩大一次，但必须付出明确代价。
- 21-30 章：进入新层级冲突，反派能针对主角能力反制。
- 31-40 章：兑现 8 万字阶段目标，留下 8-10 万字推进钩子。
"""


def style_guide(spec: FrameworkImportSpec) -> str:
    return f"""# 风格指南

## 男频爽文节奏
- 每章必须有明确冲突、爽点兑现和章尾追读钩子。
- 三章内完成反杀或显圣，不拖慢开局承诺。
- 十章内完成第一次大打脸，建立读者信任。

## 每章生产要求
- 开篇承接上一章未解压力。
- 中段让主角主动破局，不靠机械降神。
- 章尾抛出新危机、新利益或新身份信息。

## 本书核心卖点
{bullets(spec.core_selling_points)}
"""


def forbidden_rules(spec: FrameworkImportSpec) -> str:
    return f"""# 禁写规则

## 平台风险
{bullets(spec.forbidden_terms)}

## AI 痕迹规避
- 禁止机械复述设定。
- 禁止连续使用对称排比和空泛情绪词。
- 禁止用总结代替场景动作。

## 题材逻辑禁忌
{bullets(spec.forbidden_moves)}

## 框架约束
- 主角不能圣母，关键选择必须服务生存、变强和主线推进。
- 凡人不能变背景板，香火/神道规则必须持续影响现实利益。
- 不能跳过代价、限制和反派反制。
"""


def review_checklist(spec: FrameworkImportSpec) -> str:
    return f"""# 审稿检查清单

- [ ] 是否体现核心卖点：{spec.one_sentence_pitch}
- [ ] 是否有明确冲突
- [ ] 是否有爽点兑现
- [ ] 是否有章尾追读钩子
- [ ] 是否符合香火/神道规则
- [ ] 是否推进 8 万字阶段目标
- [ ] 是否有 AI 机械感
- [ ] 是否存在平台风险
- [ ] 主角行为是否符合人设且不圣母
- [ ] 是否承接上一章状态和伏笔
"""


def volume_outline(spec: FrameworkImportSpec) -> str:
    return "# 卷纲\n\n" + phase_lines(spec.phase_targets)


def first_40_chapters(spec: FrameworkImportSpec) -> str:
    lines = ["# 前 40 章章节卡", ""]
    for card in spec.chapter_cards[:40]:
        lines.extend(
            [
                f"## 第 {card.chapter} 章：{card.title}",
                f"- 核心任务：{card.objective}",
                f"- 冲突：{card.conflict}",
                f"- 爽点：{card.payoff}",
                f"- 章尾钩子：{card.ending_hook}",
                f"- 必须承接：{card.must_continue_from}",
                "",
            ]
        )
    return "\n".join(lines)


def chapter_queue(spec: FrameworkImportSpec) -> str:
    lines = [
        "# 章节队列",
        "",
        "| 章号 | 工作标题 | 核心任务 | 必须承接 | 状态 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for card in spec.chapter_cards[:40]:
        objective = f"{card.objective}；冲突：{card.conflict}；爽点：{card.payoff}；钩子：{card.ending_hook}"
        lines.append(f"| {card.chapter} | {clean_cell(card.title)} | {clean_cell(objective)} | {clean_cell(card.must_continue_from)} | 待生成 |")
    return "\n".join(lines) + "\n"


def phase_lines(phases: dict[str, Any]) -> str:
    ordered = ["0-2万字", "2-5万字", "5-8万字", "8-10万字"]
    return "\n".join(f"- {key}：{phases.get(key, '')}" for key in ordered)


def bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- 待补充"


def bullet_dict(data: dict[str, Any]) -> str:
    if not data:
        return "- 待补充"
    return "\n".join(f"- {key}：{format_value(value)}" for key, value in data.items())


def dict_list(items: list[dict[str, Any]]) -> str:
    if not items:
        return "- 待补充"
    lines: list[str] = []
    for item in items:
        name = item.get("name") or item.get("姓名") or "角色"
        lines.append(f"### {name}")
        lines.append(bullet_dict(item))
    return "\n".join(lines)


def bullet_any(value: Any) -> str:
    if isinstance(value, list):
        return bullets([format_value(item) for item in value])
    if isinstance(value, dict):
        return bullet_dict(value)
    if value:
        return f"- {value}"
    return "- 待补充"


def format_value(value: Any) -> str:
    if isinstance(value, list):
        return "；".join(format_value(item) for item in value)
    if isinstance(value, dict):
        return "；".join(f"{key}={format_value(val)}" for key, val in value.items())
    return str(value)


def clean_cell(value: str) -> str:
    return value.replace("|", "，").replace("\n", " ").strip()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _readiness_to_dict(report: ReadinessReport | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "ready": report.ready,
        "critical_missing": report.critical_missing,
        "warnings": report.warnings,
        "items": [asdict(item) for item in report.items],
    }


def _extract_prompt(markdown: str) -> str:
    return f"""请把下面的 ChatGPT 小说选题/框架 Markdown 抽取并补齐为 JSON。

要求：
- 必须生成前 40 章 chapter_cards。
- phase_targets 必须包含：0-2万字、2-5万字、5-8万字、8-10万字。
- chapter_cards 每章包含 chapter、title、objective、conflict、爽点、ending_hook、must_continue_from。
- hook_terms 和 forbidden_terms 各至少 5 个。
- 不要输出 Markdown，只输出 JSON 对象。

输入：
{markdown}
"""
