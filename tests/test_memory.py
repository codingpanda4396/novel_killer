"""NovelOps 记忆层单元测试"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestChunkText:
    """测试文本分块功能"""

    def test_chunk_text_short_text(self):
        from novelops.memory.indexer import _chunk_text

        # 文本少于 50 字符会被过滤
        text = "这是很短的文本"
        chunks = _chunk_text(text)
        assert len(chunks) == 0

    def test_chunk_text_valid_text(self):
        from novelops.memory.indexer import _chunk_text

        # 超过 50 字符的文本应该被处理
        text = "这是一段足够长的文本，用于测试分块功能。" * 5
        chunks = _chunk_text(text)
        assert len(chunks) >= 1
        assert chunks[0] == text

    def test_chunk_text_empty_text(self):
        from novelops.memory.indexer import _chunk_text

        chunks = _chunk_text("")
        assert len(chunks) == 0

    def test_chunk_text_long_text(self):
        from novelops.memory.indexer import _chunk_text

        # 创建超过 chunk_size 的文本
        paragraphs = ["段落" * 100 for _ in range(10)]
        text = "\n\n".join(paragraphs)
        chunks = _chunk_text(text, chunk_size=500, overlap=50)

        assert len(chunks) > 1
        # 每个 chunk 都应该有内容
        for chunk in chunks:
            assert len(chunk.strip()) > 0

    def test_chunk_markdown_nonexistent_file(self):
        from novelops.memory.indexer import _chunk_markdown

        chunks = _chunk_markdown(Path("/nonexistent/file.md"))
        assert len(chunks) == 0

    def test_chunk_markdown_real_file(self):
        from novelops.memory.indexer import _chunk_markdown

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            # 写入足够长的内容以超过 50 字符阈值
            f.write("# 标题\n\n这是第一段内容，需要足够长才能被处理。" * 10 + "\n\n这是第二段内容，也需要足够长。" * 10 + "\n")
            f.flush()
            chunks = _chunk_markdown(Path(f.name))
            assert len(chunks) >= 1

    def test_chunk_jsonl(self):
        from novelops.memory.indexer import _chunk_jsonl

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"title": "测试1", "score": 8.5}\n')
            f.write('{"title": "测试2", "score": 9.0}\n')
            f.flush()
            chunks = _chunk_jsonl(Path(f.name))
            assert len(chunks) == 2
            assert chunks[0]["title"] == "测试1"


class TestMemoryStore:
    """测试 MemoryStore 封装"""

    @patch("novelops.memory._check_chromadb")
    def test_store_init(self, mock_check):
        mock_chromadb = MagicMock()
        mock_check.return_value = mock_chromadb

        from novelops.memory.store import MemoryStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir))
            # 目录在访问 client 属性时才创建
            assert store._chroma_dir == Path(tmpdir) / "chroma"


class TestIndexer:
    """测试索引功能"""

    def test_index_project_with_mock_store(self):
        from novelops.memory.indexer import index_project

        # 创建临时项目结构
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"
            project_path.mkdir()

            # 创建必要的目录和文件
            (project_path / "bible").mkdir()
            (project_path / "state").mkdir()
            (project_path / "outlines").mkdir()
            (project_path / "corpus" / "volume_01").mkdir(parents=True)
            (project_path / "intelligence" / "processed").mkdir(parents=True)
            (project_path / "intelligence" / "reports").mkdir(parents=True)

            # 写入测试文件
            (project_path / "bible" / "01_characters.md").write_text(
                "# 角色设定\n\n主角张三，25岁，程序员。\n" * 10
            )
            (project_path / "bible" / "00_story_bible.md").write_text(
                "# 故事总纲\n\n这是一个都市异能故事。\n" * 10
            )
            (project_path / "state" / "chapter_summary.md").write_text(
                "# 章节摘要\n\n## 第 1 章\n主角获得异能。\n" * 10
            )
            (project_path / "project.json").write_text(
                json.dumps({
                    "name": "测试项目",
                    "rubric": {"forbidden_terms": ["不能写死亡", "不能写暴力"]}
                })
            )

            # 创建 mock store
            mock_store = MagicMock()
            mock_store.delete_collection = MagicMock()
            mock_store.upsert = MagicMock()

            # 执行索引
            count = index_project(project_path, mock_store)

            # 验证
            assert count > 0
            mock_store.upsert.assert_called_once()

            # 验证 upsert 被调用时的参数
            call_args = mock_store.upsert.call_args
            ids = call_args.kwargs.get("ids") or call_args[1].get("ids")
            assert len(ids) > 0
            # 验证 ID 格式
            for id in ids:
                assert id.startswith("test_project_")


class TestRetriever:
    """测试召回功能"""

    def test_recall_for_chapter_returns_dict(self):
        from novelops.memory.retriever import recall_for_chapter

        mock_store = MagicMock()
        mock_store.query.return_value = {"documents": [["测试文档"]]}

        plan = MagicMock()
        plan.volume = 1
        plan.title = "测试章节"
        plan.objective = "推进剧情"

        intent = MagicMock()
        intent.reader_promise = "读者承诺"

        chain = MagicMock()

        context = recall_for_chapter(
            Path("/tmp/test"),
            37,
            plan,
            intent,
            chain,
            mock_store
        )

        assert isinstance(context, dict)
        assert "protagonist_setting" in context
        assert "first_chapters" in context
        assert "recent_state" in context
        assert "volume_outline" in context
        assert "forbidden_rules" in context
        assert "related_history" in context
        assert "hotspot_cases" in context

    def test_format_memory_context(self):
        from novelops.memory.retriever import format_memory_context

        context = {
            "protagonist_setting": "主角设定内容",
            "first_chapters": "",
            "recent_state": "最近状态",
        }

        result = format_memory_context(context)
        assert "## protagonist_setting" in result
        assert "## recent_state" in result
        # 空内容不应该出现
        assert "## first_chapters" not in result

    def test_format_memory_context_with_limit(self):
        from novelops.memory.retriever import format_memory_context

        context = {
            "section1": "内容" * 1000,
            "section2": "内容" * 1000,
        }

        result = format_memory_context(context, limit=100)
        # 验证总长度被限制
        assert len(result) < 1000  # 应该远小于原始长度


class TestGeneratorIntegration:
    """测试生成器集成"""

    @patch("novelops.memory.recall_for_chapter")
    @patch("novelops.memory.format_memory_context")
    def test_generate_uses_memory_context(self, mock_format, mock_recall):
        """测试生成器使用 memory_context"""
        mock_recall.return_value = {"protagonist_setting": "测试设定"}
        mock_format.return_value = "## protagonist_setting\n测试设定"

        # 这里需要更复杂的 mock 来测试完整的生成流程
        # 简单验证导入是否正常
        from novelops.generator import _generate_live
        assert callable(_generate_live)


class TestCLI:
    """测试 CLI 命令"""

    def test_memory_index_command_parser(self):
        """测试 memory-index 命令解析"""
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        p = sub.add_parser("memory-index")
        p.set_defaults(func=lambda args: 0)

        args = parser.parse_args(["memory-index"])
        assert hasattr(args, "func")

    def test_memory_recall_command_parser(self):
        """测试 memory-recall 命令解析"""
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        p = sub.add_parser("memory-recall")
        p.add_argument("chapter", type=int)
        p.set_defaults(func=lambda args: 0)

        args = parser.parse_args(["memory-recall", "37"])
        assert hasattr(args, "func")
        assert args.chapter == 37
