"""Direct tests for Chinese text utility helpers."""

import pytest

from utils.chinese_utils import (
    contains_chinese,
    is_chinese_char,
    is_multi_char_word,
    normalize_whitespace,
)


class TestIsChineseChar:
    @pytest.mark.parametrize("char", ["中", "文", "一", "鿕"])
    def test_han_characters(self, char):
        assert is_chinese_char(char) is True

    @pytest.mark.parametrize("char", ["a", "1", "。", "，", " ", "ん", "한"])
    def test_non_han_characters(self, char):
        assert is_chinese_char(char) is False


class TestContainsChinese:
    def test_pure_chinese(self):
        assert contains_chinese("你好") is True

    def test_mixed_text(self):
        assert contains_chinese("hello 世界") is True

    def test_no_chinese(self):
        assert contains_chinese("hello world 123!") is False

    def test_empty(self):
        assert contains_chinese("") is False


class TestIsMultiCharWord:
    def test_two_char_word(self):
        assert is_multi_char_word("你好") is True

    def test_single_char(self):
        assert is_multi_char_word("好") is False

    def test_counts_only_chinese_chars(self):
        # Two total chars but only one Han char.
        assert is_multi_char_word("A股") is False
        # Punctuation doesn't count toward the two-char minimum.
        assert is_multi_char_word("好。") is False

    def test_empty(self):
        assert is_multi_char_word("") is False


class TestNormalizeWhitespace:
    def test_collapses_runs_to_single_space(self):
        assert normalize_whitespace("你好   世界\t\n测试") == "你好 世界 测试"

    def test_strips_ends(self):
        assert normalize_whitespace("  你好  ") == "你好"

    def test_empty(self):
        assert normalize_whitespace("") == ""
