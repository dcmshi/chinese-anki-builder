"""Tests for Anki deck building."""

import pytest
from collections import Counter
from process.word_selector import WordCard
from process.cedict_loader import DictEntry
from anki.deck_builder import generate_note_guid, create_anki_note, highlight_word_in_sentence
from anki.templates import get_chinese_model, FRONT_TEMPLATE, CARD_CSS


class TestDeckBuilder:
    """Test Anki deck building functionality."""

    def test_generate_note_guid_deterministic(self):
        """Test that note GUIDs are deterministic."""
        word = "你好"
        sentence = "你好世界"

        guid1 = generate_note_guid(word, sentence)
        guid2 = generate_note_guid(word, sentence)

        assert guid1 == guid2
        assert isinstance(guid1, str)

    def test_generate_note_guid_uses_full_hash(self):
        """Regression: GUIDs were truncated to 32 bits, making birthday
        collisions realistic in ~3k-card decks (colliding notes silently
        overwrite each other on Anki import)."""
        guid = generate_note_guid("你好", "你好世界")
        assert len(guid) == 32  # full md5 hex digest, not a truncation

    def test_generate_note_guid_different_inputs(self):
        """Test that different inputs produce different GUIDs."""
        guid1 = generate_note_guid("你好", "你好世界")
        guid2 = generate_note_guid("世界", "你好世界")
        guid3 = generate_note_guid("你好", "你好中国")

        assert guid1 != guid2
        assert guid1 != guid3
        assert guid2 != guid3

    def test_create_anki_note_with_definition(self):
        """Test creating an Anki note with a valid definition."""
        card = WordCard(
            word="你好",
            sentence="你好世界",
            frequency=10,
            chapter="Chapter 1"
        )

        cedict = {
            "你好": DictEntry("你好", "你好", "nǐ hǎo", ["hello", "hi"])
        }

        model = get_chinese_model()
        note = create_anki_note(card, cedict, model)

        assert note.fields[0] == "你好"  # Word
        # Sentence carries the inline highlight of the target word
        assert note.fields[1] == '<span class="target">你好</span>世界'
        assert note.fields[3] == "nǐ hǎo"  # Pinyin (word)
        assert note.fields[4] == "hello"  # Definition (first one)
        assert note.fields[7] == "Chapter 1"  # Chapter

    def test_create_anki_note_without_definition(self):
        """Test creating an Anki note when word not in dictionary."""
        card = WordCard(
            word="罗辑",  # Character name, not in dictionary
            sentence="罗辑说话了",
            frequency=5,
            chapter="Chapter 2"
        )

        cedict = {}  # Empty dictionary

        model = get_chinese_model()
        note = create_anki_note(card, cedict, model)

        # Should have fallback definition
        assert note.fields[0] == "罗辑"
        assert note.fields[4] == "[Definition not found in CC-CEDICT]"

    def test_create_anki_note_pinyin_fallback(self):
        """Test that pinyin uses pypinyin when not in CEDICT."""
        card = WordCard(
            word="测试",
            sentence="这是测试",
            frequency=3
        )

        cedict = {}  # Not in dictionary

        model = get_chinese_model()
        note = create_anki_note(card, cedict, model)

        # Should still have pinyin from pypinyin
        assert note.fields[3] != ""  # Pinyin field (word) not empty
        assert "ce" in note.fields[3].lower() or "cè" in note.fields[3]

    def test_anki_note_guid_consistency(self):
        """Test that GUID is set correctly and consistently."""
        card = WordCard(word="你好", sentence="你好世界", frequency=10)
        cedict = {"你好": DictEntry("你好", "你好", "nǐ hǎo", ["hello"])}
        model = get_chinese_model()

        note1 = create_anki_note(card, cedict, model)
        note2 = create_anki_note(card, cedict, model)

        # GUIDs should be the same for same card
        assert note1.guid == note2.guid

    def test_highlight_wraps_all_occurrences(self):
        result = highlight_word_in_sentence("学习", "学习使人进步，我爱学习。")
        assert result.count('<span class="target">学习</span>') == 2

    def test_highlight_escapes_html(self):
        # Stray markup from extraction must not break the card template.
        result = highlight_word_in_sentence("你好", "你好<b>世界</b> & 朋友")
        assert "<b>" not in result
        assert "&amp;" in result
        assert '<span class="target">你好</span>' in result

    def test_highlight_word_absent_leaves_sentence_alone(self):
        assert highlight_word_in_sentence("学习", "你好世界") == "你好世界"

    def test_front_template_highlights_word_in_sentence(self):
        """Regression: the front used to show the word separately below the
        sentence instead of highlighting it inside (as README promises)."""
        assert "{{Sentence}}" in FRONT_TEMPLATE
        assert "{{Word}}" not in FRONT_TEMPLATE  # answer side only
        assert ".target" in CARD_CSS

    def test_chinese_model_structure(self):
        """Test that the Chinese model has correct structure."""
        model = get_chinese_model()

        # Check field names
        field_names = [f["name"] for f in model.fields]
        assert "Word" in field_names
        assert "Sentence" in field_names
        assert "Pinyin" in field_names
        assert "Definition" in field_names
        assert "Audio" in field_names
        assert "Chapter" in field_names

        # Check template exists
        assert len(model.templates) > 0
        assert model.templates[0]["name"] == "Card 1"
