from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from novelops.desire.feedback import (
    _build_feedback_section,
    _summarize_feedback,
    update_demand_from_feedback,
)


class FeedbackSummaryTests(unittest.TestCase):
    def test_summarize_empty_data(self) -> None:
        result = _summarize_feedback([])
        self.assertIsNone(result)

    def test_summarize_single_row(self) -> None:
        data = [{
            "impressions": 1000,
            "views": 100,
            "reads": 50,
            "collections": 10,
            "favorites": 5,
            "comments": 3,
            "follows": 2,
            "income": 1.5,
            "notes": "测试备注",
        }]
        result = _summarize_feedback(data)
        self.assertIsNotNone(result)
        self.assertEqual(result["total_impressions"], 1000)
        self.assertEqual(result["total_views"], 100)
        self.assertEqual(result["click_rate"], 10.0)
        self.assertEqual(result["read_rate"], 50.0)
        self.assertEqual(result["collection_rate"], 20.0)

    def test_build_feedback_section(self) -> None:
        summary = {
            "data_points": 5,
            "total_impressions": 5000,
            "total_views": 500,
            "total_reads": 250,
            "click_rate": 10.0,
            "read_rate": 50.0,
            "collection_rate": 10.0,
            "total_collections": 25,
            "total_favorites": 15,
            "total_comments": 10,
            "total_follows": 5,
            "total_income": 5.0,
            "notes_summary": "测试",
        }
        section = _build_feedback_section("2026-05-08", "exp001", summary)
        self.assertIn("## 实战回写 2026-05-08 — experiment_exp001", section)
        self.assertIn("5000", section)
        self.assertIn("10.0%", section)


class UpdateDemandTests(unittest.TestCase):
    def test_update_with_no_demand_file(self) -> None:
        """Should return False if demand_analysis.md doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "market").mkdir()
            result = update_demand_from_feedback(root, "exp001")
            self.assertFalse(result)

    def test_update_appends_section(self) -> None:
        """Should append a feedback section to demand_analysis.md."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            market = root / "market"
            market.mkdir()

            demand_path = market / "demand_analysis.md"
            demand_path.write_text("# 需求分析\n\n原始内容\n", encoding="utf-8")

            # Mock the DB call to return empty (no feedback data)
            with unittest.mock.patch(
                "novelops.desire.feedback._load_feedback",
                return_value=[{
                    "record_date": "2026-05-08",
                    "platform": "番茄",
                    "impressions": 1000,
                    "views": 100,
                    "reads": 50,
                    "read_rate": None,
                    "collections": 10,
                    "favorites": 5,
                    "comments": 3,
                    "follows": 2,
                    "income": 1.0,
                    "notes": "测试",
                }],
            ):
                result = update_demand_from_feedback(root, "exp001")
                self.assertTrue(result)

                content = demand_path.read_text(encoding="utf-8")
                self.assertIn("## 实战回写", content)
                self.assertIn("experiment_exp001", content)
                self.assertIn("原始内容", content)  # Original content preserved


if __name__ == "__main__":
    unittest.main()
