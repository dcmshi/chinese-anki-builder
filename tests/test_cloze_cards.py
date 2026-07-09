"""Tests for cloze-deletion card generation."""

import genanki
import pytest

from anki.deck_builder import (
    build_deck,
    cloze_sentence,
    create_anki_note,
    create_cloze_note,
)
from anki.templates import get_chinese_cloze_model, get_chinese_model
from process.cedict_loader import DictEntry
from process.word_selector import WordCard


CEDICT = {"学习": DictEntry("學習", "学习", "xue2 xi2", ["to study", "to learn"])}


def make_card(**overrides):
    defaults = dict(
        word="学习",
        sentence="我每天都在学习中文。",
        frequency=12,
        chapter="第一章",
        sentence_pinyin="wǒ měi tiān dōu zài xué xí zhōng wén",
        sentence_translation="I study Chinese every day.",
    )
    defaults.update(overrides)
    return WordCard(**defaults)


class TestClozeSentence:
    def test_wraps_word_in_cloze_marker(self):
        assert cloze_sentence("学习", "我在学习。") == "我在{{c1::学习}}。"

    def test_wraps_all_occurrences_as_same_cloze(self):
        result = cloze_sentence("学习", "学习让我快乐，我爱学习。")
        assert result.count("{{c1::学习}}") == 2

    def test_word_absent_returns_escaped_sentence(self):
        assert cloze_sentence("学习", "你好世界") == "你好世界"

    def test_escapes_html(self):
        result = cloze_sentence("学习", "学习<b>标签</b>")
        assert "<b>" not in result
        assert "{{c1::学习}}" in result


class TestCreateClozeNote:
    def test_note_fields(self):
        note = create_cloze_note(make_card(), CEDICT, get_chinese_cloze_model())

        assert note.fields[0] == "我每天都在{{c1::学习}}中文。"  # Text
        assert note.fields[1] == "学习"  # Word
        assert note.fields[2] == "xué xí"  # Pinyin (tone marks)
        assert note.fields[3] == "to study"  # Definition
        assert note.tags == ["chapter::第一章"]

    def test_cloze_guid_differs_from_regular_note(self):
        """A cloze deck and a regular deck from the same book must not
        collide on import."""
        card = make_card()
        regular = create_anki_note(card, CEDICT, get_chinese_model())
        cloze = create_cloze_note(card, CEDICT, get_chinese_cloze_model())

        assert regular.guid != cloze.guid

    def test_cloze_model_is_cloze_type(self):
        assert get_chinese_cloze_model().model_type == genanki.Model.CLOZE


class TestBuildClozeDeck:
    def test_writes_apkg(self, tmp_path):
        output = tmp_path / "cloze.apkg"

        result = build_deck("测试 Cloze", [make_card()], CEDICT, str(output), cloze=True)

        assert result.exists()
        assert result.stat().st_size > 0

    def test_regular_deck_still_writes(self, tmp_path):
        output = tmp_path / "regular.apkg"

        result = build_deck("测试 Regular", [make_card()], CEDICT, str(output))

        assert result.exists()
