from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import project_dir
from .platforms import get_platform, get_platform_review_focus, get_platform_risk_focus


_EXPERIMENT_TEMPLATE_FILES = [
    "hypothesis.md",
    "market_samples.md",
    "concept_package.md",
    "outline_30.md",
    "platform_strategy.md",
    "review_report.md",
    "retrospective.md",
]

_EXPERIMENT_STATUSES = [
    "planning", "drafting", "reviewing", "publishing",
    "collecting_data", "retrospective", "continued", "killed",
]

_EXPERIMENT_DECISIONS = ["CONTINUE", "REVISE", "KILL", "UNKNOWN"]

_METRICS_CSV_FIELDS = [
    "date", "platform", "book_id", "chapter_start", "chapter_end",
    "impressions", "views", "reads", "read_rate", "collections",
    "favorites", "recommendations", "comments", "follows",
    "chapter_follows", "income", "notes",
]

_NUMERIC_FIELDS = {
    "impressions", "views", "reads", "read_rate", "collections",
    "favorites", "recommendations", "comments", "follows",
    "chapter_follows", "income",
}

_INT_FIELDS = {
    "impressions", "views", "reads", "collections",
    "favorites", "recommendations", "comments", "follows",
    "chapter_follows", "chapter_start", "chapter_end",
}


def _experiments_dir(project_id: str) -> Path:
    return project_dir(project_id) / "experiments"


def _experiment_dir(project_id: str, experiment_id: str) -> Path:
    return _experiments_dir(project_id) / experiment_id


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _generate_experiment_json(
    experiment_id: str,
    project_id: str,
    platform_id: str,
    hypothesis: str,
) -> dict[str, Any]:
    now = _now_iso()
    return {
        "id": experiment_id,
        "project_id": project_id,
        "platform_id": platform_id,
        "status": "drafting",
        "hypothesis": hypothesis,
        "created_at": now,
        "updated_at": now,
        "decision": "UNKNOWN",
    }


def create_experiment(
    experiment_id: str,
    project_id: str,
    platform_id: str,
    hypothesis: str,
) -> Path:
    exp_dir = _experiment_dir(project_id, experiment_id)
    if exp_dir.exists():
        raise FileExistsError(f"Experiment already exists: {exp_dir}")

    exp_dir.mkdir(parents=True, exist_ok=False)
    (exp_dir / "chapters").mkdir()

    exp_data = _generate_experiment_json(experiment_id, project_id, platform_id, hypothesis)
    (exp_dir / "experiment.json").write_text(
        json.dumps(exp_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (exp_dir / "hypothesis.md").write_text(
        f"# 假设\n\n{hypothesis}\n",
        encoding="utf-8",
    )
    for fname in _EXPERIMENT_TEMPLATE_FILES:
        if fname == "hypothesis.md":
            continue
        (exp_dir / fname).write_text(f"# {fname.replace('.md', '').replace('_', ' ').title()}\n\n", encoding="utf-8")

    return exp_dir


def load_experiment(project_id: str, experiment_id: str) -> dict[str, Any]:
    path = _experiment_dir(project_id, experiment_id) / "experiment.json"
    if not path.exists():
        raise FileNotFoundError(f"Experiment not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_experiment(project_id: str, experiment_id: str, data: dict[str, Any]) -> None:
    data["updated_at"] = _now_iso()
    path = _experiment_dir(project_id, experiment_id) / "experiment.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_experiments(project_id: str) -> list[str]:
    exp_dir = _experiments_dir(project_id)
    if not exp_dir.is_dir():
        return []
    return sorted(
        p.name for p in exp_dir.iterdir()
        if p.is_dir() and (p / "experiment.json").is_file()
    )


def experiment_path(project_id: str, experiment_id: str) -> Path:
    return _experiment_dir(project_id, experiment_id)


def import_metrics(
    project_id: str,
    experiment_id: str,
    csv_path: str | Path,
) -> dict[str, Any]:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    exp = load_experiment(project_id, experiment_id)
    platform_id = exp["platform_id"]
    exp_dir = _experiment_dir(project_id, experiment_id)

    rows = []
    errors = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            if not row.get("date"):
                errors.append(f"Row {i}: missing date")
                continue
            if row.get("platform") and row["platform"] != platform_id:
                errors.append(f"Row {i}: platform mismatch (expected {platform_id}, got {row['platform']})")
                continue
            cleaned = {}
            for field in _METRICS_CSV_FIELDS:
                val = row.get(field, "")
                if field in _NUMERIC_FIELDS and val:
                    try:
                        if field in _INT_FIELDS:
                            cleaned[field] = int(float(val))
                        else:
                            cleaned[field] = float(val)
                    except ValueError:
                        errors.append(f"Row {i}: invalid number for {field}: {val}")
                        break
                else:
                    cleaned[field] = val if val else None
            else:
                rows.append(cleaned)

    if errors:
        return {"success": False, "errors": errors, "imported": 0}

    dest_csv = exp_dir / "metrics.csv"
    shutil.copy2(csv_path, dest_csv)

    _write_metrics_to_db(project_id, experiment_id, platform_id, rows)

    return {"success": True, "imported": len(rows), "csv_path": str(dest_csv)}


def _write_metrics_to_db(
    project_id: str,
    experiment_id: str,
    platform: str,
    rows: list[dict[str, Any]],
) -> None:
    from .db.session import session_scope
    from .db.models import FeedbackLog

    with session_scope() as session:
        for row in rows:
            log = FeedbackLog(
                project_id=project_id,
                experiment_id=experiment_id,
                chapter=0,
                platform=platform,
                book_id=row.get("book_id"),
                chapter_start=row.get("chapter_start"),
                chapter_end=row.get("chapter_end"),
                impressions=row.get("impressions"),
                clicks=None,
                views=row.get("views"),
                reads=row.get("reads"),
                read_rate=row.get("read_rate"),
                collections=row.get("collections"),
                favorites=row.get("favorites"),
                recommendations=row.get("recommendations"),
                comments=row.get("comments"),
                follows=row.get("follows"),
                chapter_follows=row.get("chapter_follows"),
                income=row.get("income"),
                notes=row.get("notes"),
                record_date=row["date"],
            )
            session.add(log)


def generate_experiment_report(project_id: str, experiment_id: str) -> str:
    exp = load_experiment(project_id, experiment_id)
    exp_dir = _experiment_dir(project_id, experiment_id)

    try:
        platform = get_platform(exp["platform_id"])
        platform_name = platform["name"]
        platform_metrics = platform.get("primary_metrics", [])
    except KeyError:
        platform_name = exp["platform_id"]
        platform_metrics = []

    chapters_dir = exp_dir / "chapters"
    chapter_count = len(list(chapters_dir.glob("*.md"))) if chapters_dir.is_dir() else 0

    metrics_data = _load_metrics_from_db(project_id, experiment_id)
    metrics_summary = _summarize_metrics(metrics_data, platform_metrics)

    market_path = exp_dir / "market_samples.md"
    market_summary = ""
    if market_path.exists():
        content = market_path.read_text(encoding="utf-8").strip()
        if content and content != "# Market Samples":
            market_summary = content[:500]

    gaps = []
    if not market_summary:
        gaps.append("缺少市场样本")
    if chapter_count == 0:
        gaps.append("缺少章节数据")
    if not metrics_data:
        gaps.append("缺少发布数据")
    if exp.get("status") == "drafting" and chapter_count == 0:
        gaps.append("尚未开始写作")

    suggestions = _generate_suggestions(exp, metrics_summary, chapter_count)

    report = f"""# 实验报告：{experiment_id}

## 基本信息
- 实验ID：{exp['id']}
- 项目：{exp['project_id']}
- 平台：{platform_name} ({exp['platform_id']})
- 状态：{exp['status']}
- 创建时间：{exp['created_at']}
- 更新时间：{exp.get('updated_at', 'N/A')}

## 假设
{exp.get('hypothesis', '未设定')}

## 市场样本摘要
{market_summary if market_summary else '暂无'}

## 章节生成情况
- 已生成章节：{chapter_count}

## 数据表现
{metrics_summary}

## 信息缺口
{chr(10).join(f'- [ ] {gap}' for gap in gaps) if gaps else '- 无明显缺口'}

## 建议动作
{suggestions}
"""
    report_path = exp_dir / "review_report.md"
    report_path.write_text(report, encoding="utf-8")
    return str(report_path)


def _load_metrics_from_db(project_id: str, experiment_id: str) -> list[dict[str, Any]]:
    from .db.session import session_scope
    from .db.models import FeedbackLog
    from sqlmodel import select

    with session_scope() as session:
        statement = select(FeedbackLog).where(
            FeedbackLog.project_id == project_id,
            FeedbackLog.experiment_id == experiment_id,
        )
        results = session.exec(statement).all()
        return [
            {
                "date": r.record_date,
                "impressions": r.impressions,
                "views": r.views,
                "reads": r.reads,
                "read_rate": r.read_rate,
                "collections": r.collections,
                "favorites": r.favorites,
                "recommendations": r.recommendations,
                "comments": r.comments,
                "follows": r.follows,
                "chapter_follows": r.chapter_follows,
                "income": r.income,
            }
            for r in results
        ]


def _summarize_metrics(data: list[dict[str, Any]], primary_metrics: list[str]) -> str:
    if not data:
        return "暂无数据"

    lines = ["| 指标 | 总计 | 平均 |", "| --- | --- | --- |"]
    for metric in primary_metrics:
        values = [r.get(metric) for r in data if r.get(metric) is not None]
        if values:
            total = sum(values)
            avg = total / len(values)
            if isinstance(total, float):
                lines.append(f"| {metric} | {total:.2f} | {avg:.2f} |")
            else:
                lines.append(f"| {metric} | {total} | {avg:.1f} |")

    if len(lines) == 2:
        return "暂无数据"

    return "\n".join(lines)


def _generate_suggestions(
    exp: dict[str, Any],
    metrics_summary: str,
    chapter_count: int,
) -> str:
    suggestions = []

    if exp.get("status") == "drafting":
        if chapter_count == 0:
            suggestions.append("开始生成章节内容")
        elif chapter_count < 10:
            suggestions.append("继续生成更多章节，建议至少10章进行测试")

    if metrics_summary == "暂无数据" and chapter_count > 0:
        suggestions.append("发布后导入数据以进行分析")

    if exp.get("decision") == "UNKNOWN" and metrics_summary != "暂无数据":
        suggestions.append("运行 `experiment decide` 进行决策评估")

    if not suggestions:
        suggestions.append("继续观察数据，等待更多反馈")

    return "\n".join(f"- {s}" for s in suggestions)


def update_experiment_decision(project_id: str, experiment_id: str) -> str:
    exp = load_experiment(project_id, experiment_id)
    metrics_data = _load_metrics_from_db(project_id, experiment_id)

    if not metrics_data:
        decision = "UNKNOWN"
    else:
        decision = _evaluate_decision(metrics_data)

    exp["decision"] = decision
    save_experiment(project_id, experiment_id, exp)
    return decision


def _evaluate_decision(metrics_data: list[dict[str, Any]]) -> str:
    total_impressions = sum(r.get("impressions") or 0 for r in metrics_data)
    total_views = sum(r.get("views") or 0 for r in metrics_data)
    total_reads = sum(r.get("reads") or 0 for r in metrics_data)
    total_collections = sum(r.get("collections") or 0 for r in metrics_data)
    total_favorites = sum(r.get("favorites") or 0 for r in metrics_data)
    total_recommendations = sum(r.get("recommendations") or 0 for r in metrics_data)
    total_comments = sum(r.get("comments") or 0 for r in metrics_data)
    total_follows = sum(r.get("follows") or 0 for r in metrics_data)
    total_chapter_follows = sum(r.get("chapter_follows") or 0 for r in metrics_data)

    positive_signals = 0
    if total_collections > 100 or total_favorites > 50:
        positive_signals += 1
    if total_recommendations > 30 or total_comments > 20:
        positive_signals += 1
    if total_follows > 20 or total_chapter_follows > 10:
        positive_signals += 1

    if positive_signals >= 2:
        return "CONTINUE"

    weak_signals = 0
    if total_impressions > 5000 and total_collections < 50:
        weak_signals += 1
    if total_views > 2000 and total_favorites < 20:
        weak_signals += 1
    if total_reads > 1000 and total_follows < 10:
        weak_signals += 1

    if weak_signals >= 2:
        return "REVISE"

    return "UNKNOWN"


def concept_from_radar(project_id: str, experiment_id: str) -> str:
    exp = load_experiment(project_id, experiment_id)
    exp_dir = _experiment_dir(project_id, experiment_id)
    platform_id = exp["platform_id"]

    try:
        platform = get_platform(platform_id)
        platform_name = platform["name"]
        review_focus = get_platform_review_focus(platform_id)
        risk_focus = get_platform_risk_focus(platform_id)
    except KeyError:
        platform_name = platform_id
        review_focus = []
        risk_focus = []

    market_path = exp_dir / "market_samples.md"
    market_content = ""
    if market_path.exists():
        content = market_path.read_text(encoding="utf-8").strip()
        if content and content != "# Market Samples":
            market_content = content

    hypothesis = exp.get("hypothesis", "")

    concept = f"""# 概念包：{experiment_id}

## 平台适配判断

### {platform_name} ({platform_id})
- 优势：{', '.join(review_focus[:3]) if review_focus else '待评估'}
- 风险：{', '.join(risk_focus[:3]) if risk_focus else '待评估'}
- 开篇策略：根据{platform_name}读者偏好优化
- 简介策略：突出核心卖点
- 章节节奏：符合{platform_name}阅读习惯

## 核心设定
{hypothesis if hypothesis else '待补充'}

## 市场参考
{market_content if market_content else '暂无市场样本，请补充 market_samples.md'}

## 商业潜力评估
待数据验证

## 下一步
1. 补充市场样本（market_samples.md）
2. 完善核心设定
3. 生成章节内容
4. 发布后导入数据
"""
    concept_path = exp_dir / "concept_package.md"
    concept_path.write_text(concept, encoding="utf-8")
    return str(concept_path)
