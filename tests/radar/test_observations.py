from datetime import datetime, timezone

from novelops.radar.collectors.web_collector import ParsedBook, parsed_book_to_signal
from novelops.radar.storage import RadarStorage


def test_observations_append_without_replacing_raw_signal(tmp_path):
    storage = RadarStorage(tmp_path / "radar.sqlite")
    storage.init_db()

    collected_at = datetime.now(timezone.utc).isoformat()
    book = ParsedBook(
        title="测试榜单书",
        author="测试作者",
        rank_position=1,
        source_url="https://example.com/book/10001",
        external_book_id="10001",
        metric_name="月票",
        metric_value=1200,
    )
    signal = parsed_book_to_signal(book, "qidian", "起点", "yuepiao", collected_at)

    assert storage.save_raw_signals([signal]) == 1
    assert storage.save_raw_signal_observations([signal]) == 1
    assert storage.save_raw_signals([signal]) == 1
    assert storage.save_raw_signal_observations([signal]) == 1

    assert storage.count_raw_signals() == 1
    assert storage.count_raw_signal_observations() == 2
