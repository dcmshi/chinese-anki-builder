"""Tests for cloze-deletion card generation."""

import sqlite3
import zipfile

import genanki

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


def read_notes(apkg_path, tmp_path):
    """Note rows (flds, tags) straight out of the built .apkg."""
    with zipfile.ZipFile(apkg_path) as z:
        z.extract("collection.anki2", tmp_path / "unpacked")
    db = sqlite3.connect(tmp_path / "unpacked" / "collection.anki2")
    try:
        return db.execute("SELECT flds, tags FROM notes").fetchall()
    finally:
        db.close()


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

    def test_cloze_note_references_audio(self):
        """Regression: the cloze model had no Audio field, so --tts --cloze
        bundled MP3s that no note referenced (orphaned media)."""
        card = make_card(audio_filename="zh_abc123.mp3")

        note = create_cloze_note(card, CEDICT, get_chinese_cloze_model())

        assert "[sound:zh_abc123.mp3]" in note.fields

    def test_cloze_note_without_audio_has_empty_field(self):
        note = create_cloze_note(make_card(), CEDICT, get_chinese_cloze_model())
        field_names = [f["name"] for f in get_chinese_cloze_model().fields]
        assert note.fields[field_names.index("Audio")] == ""

    def test_cloze_model_field_count_matches_note(self):
        model = get_chinese_cloze_model()
        note = create_cloze_note(make_card(), CEDICT, model)
        assert len(note.fields) == len(model.fields)


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

    def test_cards_without_a_deletion_are_skipped(self, tmp_path, capsys):
        """A cloze note with no {{c1::...}} is rejected by Anki on import with
        "no cloze deletions found". The condition is reachable whenever the
        word isn't a literal substring of the sentence (e.g. extraction
        injected a space, or a --from-review row was hand-edited)."""
        good = make_card()
        bad = make_card(word="学习", sentence="这个句子里没有那个词。")
        output = tmp_path / "cloze.apkg"

        build_deck("测试 Cloze", [good, bad], CEDICT, str(output), cloze=True)

        notes = read_notes(output, tmp_path)
        assert len(notes) == 1
        assert "{{c1::学习}}" in notes[0][0]
        assert "skipped 1 card" in capsys.readouterr().out

    def test_regular_deck_keeps_cards_whose_word_is_absent(self, tmp_path):
        """Only cloze notes are invalid without the word; a regular card still
        teaches the word, so it must not be dropped."""
        bad = make_card(word="学习", sentence="这个句子里没有那个词。")
        output = tmp_path / "regular.apkg"

        build_deck("测试 Regular", [bad], CEDICT, str(output))

        assert len(read_notes(output, tmp_path)) == 1
