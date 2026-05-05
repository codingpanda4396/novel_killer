import pytest
from pathlib import Path


@pytest.fixture
def sample_csv(tmp_path):
    csv_content = """signal_id,source,source_type,platform,rank_type,rank_position,title,author,category,tags,description,hot_score,comment_count,read_count
test_001,manual,manual,测试,测试榜,1,测试小说,测试作者,都市,重生|都市|系统,这是一本测试小说,85.0,1000,50000
test_002,manual,manual,测试,测试榜,2,测试小说2,测试作者2,玄幻,仙侠|修仙|无敌,这是另一本测试小说,75.0,800,40000
"""
    csv_path = tmp_path / "test_data.csv"
    csv_path.write_text(csv_content, encoding="utf-8")
    return csv_path
