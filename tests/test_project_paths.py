from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from novelops.project_paths import ProjectPaths


class ProjectPathsTests(unittest.TestCase):
    def test_standard_dirs_returns_new_structure(self) -> None:
        dirs = ProjectPaths.standard_dirs()
        self.assertIn("market/raw/manual_notes", dirs)
        self.assertIn("story/bible", dirs)
        self.assertIn("story/outlines", dirs)
        self.assertIn("story/state", dirs)
        self.assertIn("production/generation", dirs)
        self.assertIn("production/reviews", dirs)
        self.assertIn("production/corpus", dirs)
        self.assertIn("production/publish", dirs)
        self.assertIn("production/experiments", dirs)

    def test_fallback_to_old_paths(self) -> None:
        """When only old dirs exist, ProjectPaths should resolve to them."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create old-style directories
            (root / "bible").mkdir()
            (root / "outlines").mkdir()
            (root / "state").mkdir()
            (root / "generation").mkdir()
            (root / "reviews").mkdir()
            (root / "corpus").mkdir()
            (root / "publish").mkdir()
            (root / "intelligence").mkdir()
            (root / "experiments").mkdir()
            # Write minimal project.json
            (root / "project.json").write_text(json.dumps({"directories": {}}), encoding="utf-8")

            paths = ProjectPaths(root)
            self.assertEqual(paths.bible, root / "bible")
            self.assertEqual(paths.outlines, root / "outlines")
            self.assertEqual(paths.state, root / "state")
            self.assertEqual(paths.generation, root / "generation")
            self.assertEqual(paths.reviews, root / "reviews")
            self.assertEqual(paths.corpus, root / "corpus")
            self.assertEqual(paths.publish, root / "publish")
            self.assertEqual(paths.experiments, root / "experiments")

    def test_resolve_to_new_paths(self) -> None:
        """When new dirs exist, ProjectPaths should resolve to them."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create new-style directories
            (root / "story" / "bible").mkdir(parents=True)
            (root / "story" / "outlines").mkdir(parents=True)
            (root / "story" / "state").mkdir(parents=True)
            (root / "production" / "generation").mkdir(parents=True)
            (root / "production" / "reviews").mkdir(parents=True)
            (root / "production" / "corpus").mkdir(parents=True)
            (root / "production" / "publish").mkdir(parents=True)
            (root / "market").mkdir(parents=True)
            (root / "production" / "experiments").mkdir(parents=True)
            (root / "project.json").write_text(json.dumps({"directories": {}}), encoding="utf-8")

            paths = ProjectPaths(root)
            self.assertEqual(paths.bible, root / "story" / "bible")
            self.assertEqual(paths.outlines, root / "story" / "outlines")
            self.assertEqual(paths.state, root / "story" / "state")
            self.assertEqual(paths.generation, root / "production" / "generation")
            self.assertEqual(paths.reviews, root / "production" / "reviews")
            self.assertEqual(paths.corpus, root / "production" / "corpus")
            self.assertEqual(paths.publish, root / "production" / "publish")
            self.assertEqual(paths.experiments, root / "production" / "experiments")

    def test_project_json_mapping_priority(self) -> None:
        """project.json directories mapping should take priority."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create custom directory
            (root / "custom_bible").mkdir()
            (root / "project.json").write_text(
                json.dumps({"directories": {"bible": "custom_bible"}}),
                encoding="utf-8",
            )

            paths = ProjectPaths(root)
            self.assertEqual(paths.bible, root / "custom_bible")

    def test_chapter_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "generation").mkdir()
            (root / "project.json").write_text(json.dumps({"directories": {}}), encoding="utf-8")
            paths = ProjectPaths(root)
            self.assertEqual(paths.chapter_dir(5), root / "generation" / "chapter_005")
            self.assertEqual(paths.chapter_dir(51), root / "generation" / "chapter_051")

    def test_review_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reviews").mkdir()
            (root / "project.json").write_text(json.dumps({"directories": {}}), encoding="utf-8")
            paths = ProjectPaths(root)
            self.assertEqual(paths.review_path(10), root / "reviews" / "chapter_010_review.json")

    def test_panel_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reviews").mkdir()
            (root / "project.json").write_text(json.dumps({"directories": {}}), encoding="utf-8")
            paths = ProjectPaths(root)
            self.assertEqual(paths.panel_path(10), root / "reviews" / "chapter_010_panel.json")

    def test_bible_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bible").mkdir()
            (root / "project.json").write_text(json.dumps({"directories": {}}), encoding="utf-8")
            paths = ProjectPaths(root)
            self.assertEqual(paths.bible_file("00_story_bible.md"), root / "bible" / "00_story_bible.md")

    def test_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "state").mkdir()
            (root / "project.json").write_text(json.dumps({"directories": {}}), encoding="utf-8")
            paths = ProjectPaths(root)
            self.assertEqual(paths.state_file("timeline.md"), root / "state" / "timeline.md")

    def test_corpus_volume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "corpus").mkdir()
            (root / "project.json").write_text(json.dumps({"directories": {}}), encoding="utf-8")
            paths = ProjectPaths(root)
            self.assertEqual(paths.corpus_volume(1), root / "corpus" / "volume_01")
            self.assertEqual(paths.corpus_volume(2), root / "corpus" / "volume_02")


if __name__ == "__main__":
    unittest.main()
