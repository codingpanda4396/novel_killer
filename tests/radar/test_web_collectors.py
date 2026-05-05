from novelops.radar.collectors.web_collector import (
    normalize_metric,
    parse_metric_value,
    parse_rank_html,
)


def test_parse_rank_html_fixture():
    html = """
    <ul class="rank-list">
      <li class="book-item">
        <span>1</span>
        <a href="/page/123456789">重生2010：我有三千马甲</a>
        <p class="author">作者：码字狂人</p>
        <p class="intro">重回2010年，激活马甲系统，每个马甲都是一种人生。</p>
        <span>358.8万人在读</span>
        <span>都市 连载 120万字</span>
      </li>
      <li class="book-item">
        <span>2</span>
        <a href="/book/987654321">末世：开局签到百亿物资</a>
        <p>末世降临前三天，我激活了签到系统，获得百亿物资。</p>
        <span>92万点击</span>
      </li>
    </ul>
    """

    books = parse_rank_html(
        html,
        base_url="https://fanqienovel.com/rank",
        rank_type="hot",
        metric_name="人在读",
        limit=10,
    )

    assert len(books) == 2
    assert books[0].title == "重生2010：我有三千马甲"
    assert books[0].author == "码字狂人"
    assert books[0].rank_position == 1
    assert books[0].external_book_id == "123456789"
    assert books[0].metric_value == 3588000


def test_parse_metric_value_chinese_units():
    assert parse_metric_value("358.8万人在读") == 3588000
    assert parse_metric_value("12,345月票") == 12345
    assert parse_metric_value("1.2亿点击") == 120000000


def test_normalize_metric_range():
    assert 0 <= normalize_metric(3588000, "人在读") <= 100
    assert normalize_metric(None, rank_position=1) == 100
    assert normalize_metric(None, rank_position=50) == 51
