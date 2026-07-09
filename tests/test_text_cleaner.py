"""Tests for text cleaning and sentence splitting, including quality gates.

The quality-gate tests assert structural properties of splitter output (no
orphaned leading punctuation, balanced-quote preservation, etc.) that would
have caught the dialogue-quote-orphaning bug.
"""

import pytest

from process.text_cleaner import clean_text, split_sentences


# Characters that should never legitimately start a sentence.
_STRAY_LEADING = "，,；;：:、。”’』」）》】)]"


class TestSplitSentences:
    def test_basic_split_on_chinese_punctuation(self):
        result = split_sentences("太阳升起了。月亮落下了。鸟儿在歌唱！")
        assert result == ["太阳升起了。", "月亮落下了。", "鸟儿在歌唱！"]

    def test_terminal_punctuation_is_kept(self):
        result = split_sentences("他走进房间。")
        assert result == ["他走进房间。"]
        assert result[0].endswith("。")

    def test_closing_quote_stays_with_its_sentence(self):
        # The bug: splitting on 。 orphaned the ” onto the next sentence.
        text = "古典理论。”叶哲泰回答说。"
        result = split_sentences(text)
        assert result[0] == "古典理论。”"  # closer kept attached
        assert result[1] == "叶哲泰回答说。"
        # Critically, no sentence begins with the orphaned closer.
        assert not result[1].startswith("”")

    def test_opening_quote_at_start_is_preserved(self):
        result = split_sentences("“相对论是对的。”")
        assert result[0].startswith("“")
        assert result[0] == "“相对论是对的。”"

    def test_orphaned_leading_punctuation_is_stripped(self):
        # A stray closer/comma left at the head of a sentence must be trimmed.
        result = split_sentences("，他说了一句话。")
        assert result[0] == "他说了一句话。"

    def test_ascii_bracket_orphan_is_stripped(self):
        result = split_sentences(")连同那些冷兵器构成历史。")
        assert not result[0].startswith(")")
        assert result[0] == "连同那些冷兵器构成历史。"

    def test_punctuation_only_fragments_dropped(self):
        # No Han characters -> dropped entirely.
        assert split_sentences("。。。！！") == []

    def test_too_short_fragment_dropped(self):
        # Single Han char is below the default min_chinese_chars=2.
        result = split_sentences("好。这是一个完整的句子。")
        assert "好" not in result
        assert result == ["这是一个完整的句子。"]

    def test_decimal_number_is_not_split(self):
        # ASCII "." is not a sentence ender, so 1.5 stays intact.
        result = split_sentences("价格是1.5万元。")
        assert result == ["价格是1.5万元。"]

    def test_trailing_text_without_ender_is_kept(self):
        result = split_sentences("第一句。最后没有句号的内容")
        assert result[-1] == "最后没有句号的内容"

    def test_collapses_repeated_enders(self):
        result = split_sentences("真的吗？？？是的。")
        assert result[0] == "真的吗？？？"
        assert result[1] == "是的。"


class TestSplitterQualityGates:
    """Structural guarantees over a realistic multi-sentence dialogue blob."""

    DIALOGUE = (
        "“相对论已经成为物理学的古典理论。”叶哲泰回答说。"
        "“爱因斯坦是反动的学术权威！”旁边的女红卫兵厉声说。"
        "他沉默着，忍受着痛苦，不值得回应的问题就沉默了。"
        "她转向台下：“同志们，我们应该认清它的反动本质。”"
    )

    def test_no_sentence_starts_with_stray_punctuation(self):
        sentences = split_sentences(self.DIALOGUE)
        offenders = [s for s in sentences if s and s[0] in _STRAY_LEADING]
        assert offenders == [], f"sentences started with stray punctuation: {offenders}"

    def test_every_sentence_has_chinese_content(self):
        sentences = split_sentences(self.DIALOGUE)
        for s in sentences:
            assert any("一" <= c <= "鿿" for c in s), f"no Han chars in {s!r}"

    def test_no_sentence_ends_with_a_dangling_opening_quote(self):
        sentences = split_sentences(self.DIALOGUE)
        offenders = [s for s in sentences if s and s[-1] in "“‘『「（《【(["]
        assert offenders == [], f"sentences ended with a dangling opener: {offenders}"

    def test_splitter_is_deterministic(self):
        assert split_sentences(self.DIALOGUE) == split_sentences(self.DIALOGUE)


class TestCleanText:
    def test_collapses_whitespace(self):
        assert clean_text("你好   世界\n\n这是   测试") == "你好 世界 这是 测试"

    def test_drops_page_number_lines(self):
        assert clean_text("123") == ""

    def test_drops_page_number_lines_between_text(self):
        # Regression: digit-only lines used to survive because whitespace was
        # collapsed (destroying line structure) before line filtering ran.
        result = clean_text("第一段结束。\n42\n第二段开始。")
        assert "42" not in result
        assert result == "第一段结束。 第二段开始。"

    def test_page_number_with_surrounding_spaces_dropped(self):
        result = clean_text("正文内容。\n  307  \n更多内容。")
        assert "307" not in result

    def test_digits_inside_running_text_survive(self):
        # Only digit-ONLY lines are page numbers; numbers in prose stay.
        result = clean_text("价格是1.5万元。\n15\n他买了3本书。")
        assert "1.5万元" in result
        assert "3本书" in result
        assert " 15 " not in f" {result} "

    def test_empty_input(self):
        assert clean_text("") == ""
