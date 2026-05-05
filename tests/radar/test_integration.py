from pathlib import Path

from novelops.radar.analyzer import RuleBasedRadarAnalyzer
from novelops.radar.collectors.fanqie_collector import FanqieCollector
from novelops.radar.report import ReportGenerator
from novelops.radar.scoring import CommercialScorer
from novelops.radar.storage import RadarStorage


def test_full_pipeline(tmp_path):
    db_path = tmp_path / "test_radar.sqlite"
    report_dir = tmp_path / "reports"
    
    storage = RadarStorage(db_path)
    storage.init_db()
    
    collector = FanqieCollector(use_sample=True)
    raw_signals = collector.collect()
    assert len(raw_signals) == 10
    
    count = storage.save_raw_signals(raw_signals)
    assert count == 10
    
    analyzer = RuleBasedRadarAnalyzer()
    analyzed = analyzer.analyze(raw_signals)
    assert len(analyzed) == 10
    
    scorer = CommercialScorer()
    scored = scorer.score_all(analyzed)
    assert len(scored) == 10
    
    for s in scored:
        assert 0 <= s.commercial_potential_score <= 100
    
    storage.save_analyzed_signals(scored)
    
    topics = [scorer.generate_topic_opportunity(s) for s in scored]
    assert len(topics) == 10
    storage.save_topic_opportunities(topics)
    
    generator = ReportGenerator(report_dir)
    report_path = generator.generate(scored, topics)
    
    assert report_path.exists()
    content = report_path.read_text()
    assert "选题机会报告" in content
    assert "题材热度排行" in content
