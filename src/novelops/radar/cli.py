from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyzer import RuleBasedRadarAnalyzer
from .collectors.csv_collector import CSVCollector
from .collectors.fanqie_collector import FanqieCollector
from .competitor import CompetitorAnalyzer
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
    
    storage = RadarStorage()
    storage.init_db()
    count = storage.save_raw_signals(signals)
    
    print(f"Imported {count} signals from Fanqie {args.rank_type} rank")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    storage = RadarStorage()
    raw_signals = storage.list_raw_signals(limit=args.limit)
    
    if not raw_signals:
        print("No raw signals to analyze. Import data first.")
        return 1
    
    analyzer = RuleBasedRadarAnalyzer()
    analyzed = analyzer.analyze(raw_signals)
    
    scorer = CommercialScorer()
    scored = scorer.score_all(analyzed)
    
    count = storage.save_analyzed_signals(scored)
    print(f"Analyzed {count} signals")
    return 0


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
    
    p = sub.add_parser("analyze", help="分析数据")
    p.add_argument("--limit", type=int, default=100, help="分析数量限制")
    
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
        "analyze": cmd_analyze,
        "report": cmd_report,
        "run-sample": cmd_run_sample,
    }
    
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
