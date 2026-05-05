from datetime import datetime, timezone

from novelops.radar import cli
from novelops.radar.models import RawNovelSignal


class FakeCollector:
    def __init__(self, *args, **kwargs):
        self.issues = []

    def collect(self):
        return [
            RawNovelSignal(
                signal_id="fake_001",
                source="fake",
                source_type="ranking",
                platform="测试平台",
                rank_type="hot",
                rank_position=1,
                title="测试小说",
                hot_score=90,
                collected_at=datetime.now(timezone.utc).isoformat(),
            )
        ]


def test_collect_web_dry_run_does_not_write(monkeypatch, tmp_path):
    monkeypatch.setitem(cli.WEB_COLLECTORS, "fake", FakeCollector)
    monkeypatch.chdir(tmp_path)

    code = cli.main(["collect-web", "--source", "fake", "--dry-run"])

    assert code == 0
    assert not (tmp_path / "runtime" / "radar" / "radar.sqlite").exists()
