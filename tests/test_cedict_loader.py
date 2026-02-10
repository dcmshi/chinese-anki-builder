"""Tests for CC-CEDICT loading and parsing."""

import pytest
from process.cedict_loader import parse_cedict_line, DictEntry


class TestCEDICTLoader:
    """Test CC-CEDICT parsing functionality."""

    def test_parse_cedict_line_basic(self):
        """Test parsing a basic CEDICT line."""
        line = "你好 你好 [ni3 hao3] /hello/hi/how are you/"

        entry = parse_cedict_line(line)

        assert entry is not None
        assert entry.traditional == "你好"
        assert entry.simplified == "你好"
        assert entry.pinyin == "ni3 hao3"
        assert len(entry.definitions) == 3
        assert "hello" in entry.definitions
        assert "hi" in entry.definitions

    def test_parse_cedict_line_traditional_simplified(self):
        """Test parsing with different traditional/simplified forms."""
        line = "學習 学习 [xue2 xi2] /to learn/to study/"

        entry = parse_cedict_line(line)

        assert entry is not None
        assert entry.traditional == "學習"
        assert entry.simplified == "学习"
        assert entry.pinyin == "xue2 xi2"
        assert "to learn" in entry.definitions

    def test_parse_cedict_line_comment(self):
        """Test that comments are ignored."""
        line = "# This is a comment"

        entry = parse_cedict_line(line)

        assert entry is None

    def test_parse_cedict_line_empty(self):
        """Test that empty lines are ignored."""
        entry = parse_cedict_line("")
        assert entry is None

        entry = parse_cedict_line("   ")
        assert entry is None

    def test_parse_cedict_line_invalid(self):
        """Test handling of invalid lines."""
        invalid_lines = [
            "incomplete line",
            "你好 [ni3 hao3]",  # Missing simplified
            "你好 你好",  # Missing pinyin and definitions
        ]

        for line in invalid_lines:
            entry = parse_cedict_line(line)
            assert entry is None

    def test_dict_entry_get_first_definition(self):
        """Test getting the first definition."""
        entry = DictEntry(
            traditional="你好",
            simplified="你好",
            pinyin="ni3 hao3",
            definitions=["hello", "hi", "how are you"]
        )

        assert entry.get_first_definition() == "hello"

    def test_dict_entry_get_first_definition_empty(self):
        """Test getting first definition when list is empty."""
        entry = DictEntry(
            traditional="你好",
            simplified="你好",
            pinyin="ni3 hao3",
            definitions=[]
        )

        assert entry.get_first_definition() == ""

    def test_dict_entry_repr(self):
        """Test DictEntry string representation."""
        entry = DictEntry(
            traditional="你好",
            simplified="你好",
            pinyin="ni3 hao3",
            definitions=["hello"]
        )

        repr_str = repr(entry)
        assert "你好" in repr_str
        assert "ni3 hao3" in repr_str
        assert "hello" in repr_str
