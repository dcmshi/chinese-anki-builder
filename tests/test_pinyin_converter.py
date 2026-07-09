"""Tests for pinyin conversion, including CEDICT numbered-pinyin handling.

Regression suite for the inconsistency where word pinyin from CC-CEDICT
appeared numbered ("ni3 hao3") while sentence pinyin used tone marks.
"""

import pytest

from process.cedict_loader import DictEntry
from process.pinyin_converter import (
    numbered_to_tone_marks,
    sentence_to_pinyin,
    word_to_pinyin,
)


class TestNumberedToToneMarks:
    @pytest.mark.parametrize(
        "numbered,expected",
        [
            ("ni3 hao3", "nǐ hǎo"),
            ("xue2 xi2", "xué xí"),
            ("dong1 xi5", "dōng xi"),  # neutral tone: no mark
            ("kou3", "kǒu"),  # ou: mark goes on the o
            ("gui4", "guì"),  # no a/e/ou: mark on last vowel
            ("jiu3", "jiǔ"),
            ("xiong2", "xióng"),
            ("er2", "ér"),
            ("lu:4", "lǜ"),  # CEDICT ü spelled u:
            ("lv4", "lǜ"),  # CEDICT ü spelled v
            ("nu:3 er2", "nǚ ér"),
            ("Bei3 jing1", "Běi jīng"),  # capitals keep their case
        ],
    )
    def test_converts_numbered_syllables(self, numbered, expected):
        assert numbered_to_tone_marks(numbered) == expected

    def test_already_marked_pinyin_passes_through(self):
        assert numbered_to_tone_marks("nǐ hǎo") == "nǐ hǎo"

    def test_non_syllable_tokens_pass_through(self):
        # The · separator in transliterated foreign names survives untouched.
        assert numbered_to_tone_marks("sheng4 · dan4") == "shèng · dàn"


class TestWordToPinyin:
    def test_cedict_numbered_pinyin_is_converted(self):
        """Regression: CEDICT numbered pinyin used to leak onto cards."""
        cedict = {"你好": DictEntry("你好", "你好", "ni3 hao3", ["hello"])}
        assert word_to_pinyin("你好", cedict) == "nǐ hǎo"

    def test_pypinyin_fallback_has_tone_marks(self):
        result = word_to_pinyin("学习", cedict=None)
        assert result == "xué xí"

    def test_word_and_sentence_pinyin_share_style(self):
        """Word pinyin (CEDICT path) and sentence pinyin (pypinyin path)
        must both use tone marks -- no digits in either."""
        cedict = {"学习": DictEntry("學習", "学习", "xue2 xi2", ["to study"])}
        word_py = word_to_pinyin("学习", cedict)
        sent_py = sentence_to_pinyin("我在学习。")
        assert not any(c.isdigit() for c in word_py)
        assert not any(c.isdigit() for c in sent_py)


class TestSentenceToPinyin:
    def test_basic_sentence(self):
        result = sentence_to_pinyin("你好")
        assert result == "nǐ hǎo"
