"""Tests for jieba tokenization and frequency analysis."""

from collections import Counter

from process.tokenizer import (
    compute_word_frequency,
    filter_multi_char_words,
    tokenize_text,
)


class TestTokenizeText:
    def test_segments_chinese_text(self):
        tokens = tokenize_text("我在学习中文")
        assert "学习" in tokens
        assert "中文" in tokens

    def test_drops_pure_punctuation_and_whitespace(self):
        tokens = tokenize_text("你好，世界！  \n")
        assert "，" not in tokens
        assert "！" not in tokens
        assert all(t.strip() for t in tokens)

    def test_drops_non_chinese_tokens(self):
        tokens = tokenize_text("我有3个apple和一本书")
        assert "apple" not in tokens
        assert "3" not in tokens
        # Chinese content survives (jieba segments 一本书 as 一/本书)
        assert "本书" in tokens

    def test_empty_input(self):
        assert tokenize_text("") == []


class TestComputeWordFrequency:
    def test_counts_tokens(self):
        stats = compute_word_frequency(["学习", "中文", "学习"])

        assert stats.total_words == 3
        assert stats.unique_words == 2
        assert stats.word_freq["学习"] == 2

    def test_empty_tokens(self):
        stats = compute_word_frequency([])
        assert stats.total_words == 0
        assert stats.unique_words == 0


class TestFilterMultiCharWords:
    def test_keeps_only_two_plus_chinese_chars(self):
        freq = Counter({"学习": 5, "我": 9, "中文课": 2, "了": 20})

        result = filter_multi_char_words(freq)

        assert set(result) == {"学习", "中文课"}
        assert result["学习"] == 5
