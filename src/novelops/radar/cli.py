from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyzer import RuleBasedRadarAnalyzer
from .collectors.csv_collector import CSVCollector
from .collectors.fanqie_collector import FanqieCollector
from .collectors.web_sources import (
    FanqieRankCollector,
    JjwxcRankCollector,
    QidianRankCollector,
    XxsyCategoryCollector,
    ZonghengRankCollector,
)
from .competitor import CompetitorAnalyzer
from .composite_analyzer import CompositeAnalyzer
from .hotspot_models import HotspotAnalysis
from .llm_analyzer import LLMHotspotAnalyzer
from .models import to_dict
from .report import ReportGenerator
from .scoring import CommercialScorer
from .storage import RadarStorage


def cmd_init(args: argparse.Namespace) -> int:
    storage = RadarStorage()
    storage.init_db()
    print(f"Database initialized: {storage.db_path}")
    return 0


def cmd_import_csv(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        print(f"Error: file not found: {csv_path}")
        return 1
    
    collector = CSVCollector(csv_path, platform=args.platform)
    signals = collector.collect()
    
    storage = RadarStorage()
    storage.init_db()
    count = storage.save_raw_signals(signals)
    
    print(f"Imported {count} signals from {csv_path}")
    return 0


def cmd_import_fanqie(args: argparse.Namespace) -> int:
    collector = FanqieCollector(rank_type=args.rank_type, use_sample=args.sample)
    signals = collector.collect()
    for issue in getattr(collector, "issues", []):
        print(f"fanqie: {issue.status} {issue.url} - {issue.message}")
    
    storage = RadarStorage()
    storage.init_db()
    count = storage.save_raw_signals(signals)
    if not args.sample:
        storage.save_raw_signal_observations(signals)
    
    print(f"Imported {count} signals from Fanqie {args.rank_type} rank")
    if not signals and not args.sample:
        return 1
    return 0


WEB_COLLECTORS = {
    "fanqie": FanqieRankCollector,
    "qidian": QidianRankCollector,
    "zongheng": ZonghengRankCollector,
    "jjwxc": JjwxcRankCollector,
    "xxsy": XxsyCategoryCollector,
}


def cmd_collect_web(args: argparse.Namespace) -> int:
    source_names = list(WEB_COLLECTORS) if args.all else [args.source]
    all_signals = []
    failures = []

    for source_name in source_names:
        collector_cls = WEB_COLLECTORS[source_name]
        collector = collector_cls(
            rank_type=args.rank,
            category=args.category,
            limit=args.limit,
            use_playwright=args.playwright,
            respect_robots=not args.ignore_robots,
        )
        signals = collector.collect()
        all_signals.extend(signals)
        print(f"{source_name}: parsed {len(signals)} signals")
        for issue in collector.issues:
            failures.append(issue)
            print(f"{source_name}: {issue.status} {issue.url} - {issue.message}")

    if args.dry_run:
        for signal in all_signals[: args.limit]:
            hot = f"{signal.hot_score:.1f}" if signal.hot_score is not None else "n/a"
            print(
                f"- [{signal.platform}] #{signal.rank_position or '-'} "
                f"{signal.title} / {signal.author or '未知作者'} "
                f"hot={hot}"
            )
        print(f"Dry run complete: {len(all_signals)} parsed, 0 saved")
        return 0 if all_signals or not failures else 1

    storage = RadarStorage()
    storage.init_db()
    saved = storage.save_raw_signals(all_signals)
    observations = storage.save_raw_signal_observations(all_signals)
    print(f"Saved {saved} raw signals and {observations} observations")
    if not all_signals and failures:
        return 1
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    storage = RadarStorage()
    raw_signals = storage.list_raw_signals(limit=args.limit)
    
    if not raw_signals:
        print("No raw signals to analyze. Import data first.")
        return 1
    
    use_llm = getattr(args, 'llm', False)
    analyzer = CompositeAnalyzer(use_llm=use_llm)
    analyzed = analyzer.analyze(raw_signals)
    
    scorer = CommercialScorer()
    scored = scorer.score_all(analyzed)
    
    count = storage.save_analyzed_signals(scored)
    mode = "LLM" if use_llm else "rule-based"
    print(f"Analyzed {count} signals ({mode} mode)")
    return 0


def cmd_analyze_text(args: argparse.Namespace) -> int:
    text = args.text
    if not text:
        print("Error: text is required")
        return 1
    
    metadata = {}
    if args.title:
        metadata["title"] = args.title
    if args.category:
        metadata["category"] = args.category
    if args.tags:
        metadata["tags"] = [t.strip() for t in args.tags.split(",")]
    if args.platform:
        metadata["platform"] = args.platform
    
    try:
        analyzer = LLMHotspotAnalyzer()
        result = analyzer.analyze_text(text, metadata if metadata else None)
        
        if args.json:
            import json
            print(result.model_dump_json(indent=2))
        else:
            print(f"题材：{result.genre}")
            print(f"核心欲望：{result.core_desire}")
            print(f"钩子：{result.hook}")
            print(f"金手指：{result.golden_finger}")
            print(f"读者情绪：{', '.join(result.reader_emotion)}")
            print(f"风险：{result.risk}")
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_report(args: argparse.Namespace) -> int:
    storage = RadarStorage()
    analyzed = storage.list_analyzed_signals(limit=args.limit)
    
    if not analyzed:
        print("No analyzed signals. Run 'analyze' first.")
        return 1
    
    scorer = CommercialScorer()
    topics = [scorer.generate_topic_opportunity(s) for s in analyzed]
    storage.save_topic_opportunities(topics)
    
    competitor = CompetitorAnalyzer()
    competitors = competitor.analyze_all_genres(analyzed)
    
    generator = ReportGenerator()
    report_path = generator.generate(analyzed, topics, competitors)
    
    print(f"Report generated: {report_path}")
    return 0


def cmd_run_sample(args: argparse.Namespace) -> int:
    print("=== NovelRadar Sample Pipeline ===\n")
    
    storage = RadarStorage()
    storage.init_db()
    print("[1/4] Database initialized")
    
    collector = FanqieCollector(use_sample=True)
    raw_signals = collector.collect()
    storage.save_raw_signals(raw_signals)
    print(f"[2/4] Imported {len(raw_signals)} sample signals")
    
    analyzer = RuleBasedRadarAnalyzer()
    analyzed = analyzer.analyze(raw_signals)
    
    scorer = CommercialScorer()
    scored = scorer.score_all(analyzed)
    storage.save_analyzed_signals(scored)
    print(f"[3/4] Analyzed {len(scored)} signals")
    
    topics = [scorer.generate_topic_opportunity(s) for s in scored]
    storage.save_topic_opportunities(topics)
    
    competitor = CompetitorAnalyzer()
    competitors = competitor.analyze_all_genres(scored)
    
    generator = ReportGenerator()
    report_path = generator.generate(scored, topics, competitors)
    print(f"[4/4] Report generated: {report_path}")
    
    print("\n=== Pipeline Complete ===")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="novelops.radar",
        description="NovelRadar - 中文网文需求情报引擎"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    
    sub.add_parser("init", help="初始化数据库")
    
    p = sub.add_parser("import-csv", help="导入 CSV 数据")
    p.add_argument("csv_path", help="CSV 文件路径")
    p.add_argument("--platform", default="unknown", help="平台名称")
    
    p = sub.add_parser("import-fanqie", help="导入番茄小说数据")
    p.add_argument("--rank-type", default="hot", choices=["hot", "new", "finish"])
    p.add_argument("--sample", action="store_true", help="使用样本数据")

    p = sub.add_parser("collect-web", help="采集公开网页榜单数据")
    p.add_argument("--source", choices=sorted(WEB_COLLECTORS), default="fanqie")
    p.add_argument("--all", action="store_true", help="采集所有已配置公开来源")
    p.add_argument("--rank", default="hot", help="榜单类型，如 hot/yuepiao/new/finish")
    p.add_argument("--category", help="分类参数，v1 仅记录并预留")
    p.add_argument("--limit", type=int, default=50, help="每个平台最多采集条数")
    p.add_argument("--dry-run", action="store_true", help="只解析并打印，不写数据库")
    p.add_argument("--playwright", action="store_true", help="静态页面不足时尝试 Playwright")
    p.add_argument("--ignore-robots", action="store_true", help="跳过 robots 检查，仅用于受控测试")
    
    p = sub.add_parser("analyze", help="分析数据")
    p.add_argument("--limit", type=int, default=100, help="分析数量限制")
    p.add_argument("--llm", action="store_true", help="使用 LLM 进行热点分析")
    
    p = sub.add_parser("analyze-text", help="分析单条文本")
    p.add_argument("text", help="要分析的原始文本")
    p.add_argument("--json", action="store_true", help="输出 JSON 格式")
    p.add_argument("--title", help="小说标题")
    p.add_argument("--category", help="分类")
    p.add_argument("--tags", help="标签，逗号分隔")
    p.add_argument("--platform", help="平台")
    
    p = sub.add_parser("report", help="生成报告")
    p.add_argument("--limit", type=int, default=100, help="数据数量限制")
    
    sub.add_parser("run-sample", help="运行完整示例流程")
    
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    commands = {
        "init": cmd_init,
        "import-csv": cmd_import_csv,
        "import-fanqie": cmd_import_fanqie,
        "collect-web": cmd_collect_web,
        "analyze": cmd_analyze,
        "analyze-text": cmd_analyze_text,
        "report": cmd_report,
        "run-sample": cmd_run_sample,
    }
    
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
