"""Tests for known-words loading and exclusion (--known-words)."""

import pytest

from process.known_words import load_known_words
from process.word_selector import select_top_words
from collections import Counter


class TestLoadKnownWords:
    def test_one_word_per_line(self, tmp_path):
        path = tmp_path / "known.txt"
        path.write_text("你好\n世界\n学习\n", encoding="utf-8")
        assert load_known_words(path) == {"你好", "世界", "学习"}

    def test_comments_and_blank_lines_ignored(self, tmp_path):
        path = tmp_path / "known.txt"
        path.write_text("# HSK 1\n你好\n\n世界  # from lesson 2\n", encoding="utf-8")
        assert load_known_words(path) == {"你好", "世界"}

    def test_comma_and_space_separated(self, tmp_path):
        path = tmp_path / "known.txt"
        path.write_text("你好, 世界，学习 朋友、老师\n", encoding="utf-8")
        assert load_known_words(path) == {"你好", "世界", "学习", "朋友", "老师"}

    def test_utf8_bom_tolerated(self, tmp_path):
        path = tmp_path / "known.txt"
        path.write_bytes("﻿你好\n".encode("utf-8"))
        assert load_known_words(path) == {"你好"}

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_known_words(tmp_path / "nope.txt")


class TestExclusionInSelection:
    def test_known_words_never_selected(self):
        freq = Counter({"你好": 50, "世界": 40, "学习": 30, "朋友": 20})
        selected = select_top_words(freq, top_n=3, min_freq=1, exclude_words={"你好", "学习"})
        assert selected == ["世界", "朋友"]

    def test_pool_refills_to_requested_count(self):
        """Exclusion happens before top-N, so the deck still gets N words."""
        freq = Counter({"你好": 50, "世界": 40, "学习": 30, "朋友": 20})
        selected = select_top_words(freq, top_n=2, min_freq=1, exclude_words={"你好"})
        assert selected == ["世界", "学习"]
