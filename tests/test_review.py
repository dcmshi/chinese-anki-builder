"""Tests for the pre-import QC review workflow (--review / --from-review)."""

import csv
import sqlite3
import sys
import zipfile

import pytest

import main as main_module
from anki.deck_builder import create_anki_note, create_cloze_note
from anki.templates import get_chinese_model, get_chinese_cloze_model
from process.cedict_loader import DictEntry
from process.review import REVIEW_COLUMNS, export_cards_to_csv, load_cards_from_csv
from process.word_selector import WordCard

FIELD_SEP = "\x1f"  # Anki note field separator

FAKE_CEDICT = {
    "你好": DictEntry("你好", "你好", "ni3 hao3", ["hello"]),
    "世界": DictEntry("世界", "世界", "shi4 jie4", ["world"]),
}


def make_cards():
    return [
        WordCard(
            word="你好",
            sentence="你好，这个世界很大。",
            frequency=5,
            chapter="第一章",
            sentence_translation="Hello, this world is big.",
            sentence_pinyin="nǐ hǎo, zhè ge shì jiè hěn dà.",
        ),
        WordCard(
            word="世界",
            sentence="这个世界非常有趣。",
            frequency=3,
            chapter="第二章",
            sentence_translation="This world is very interesting.",
            sentence_pinyin="zhè ge shì jiè fēi cháng yǒu qù.",
        ),
    ]


def rewrite_rows(path, transform):
    """Load a review CSV's rows, apply transform(rows) -> rows, rewrite."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    rows = transform(rows)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def read_notes(apkg_path, tmp_path):
    with zipfile.ZipFile(apkg_path) as z:
        z.extract("collection.anki2", tmp_path / "unpacked")
    db = sqlite3.connect(tmp_path / "unpacked" / "collection.anki2")
    try:
        return db.execute("SELECT flds FROM notes").fetchall()
    finally:
        db.close()


class TestRoundTrip:
    def test_export_then_load_preserves_fields(self, tmp_path):
        path = export_cards_to_csv(make_cards(), tmp_path / "cards.csv", cedict=FAKE_CEDICT)
        loaded = load_cards_from_csv(path)

        assert len(loaded) == 2
        first = loaded[0]
        assert first.word == "你好"
        assert first.sentence == "你好，这个世界很大。"
        assert first.frequency == 5
        assert first.chapter == "第一章"
        assert first.sentence_translation == "Hello, this world is big."
        # Export resolves pinyin/definition so the reviewer sees the real card
        assert first.definition == "hello"
        assert first.word_pinyin and not any(c.isdigit() for c in first.word_pinyin)

    def test_file_is_excel_friendly_utf8_bom(self, tmp_path):
        path = export_cards_to_csv(make_cards(), tmp_path / "cards.csv", cedict=FAKE_CEDICT)
        assert path.read_bytes().startswith(b"\xef\xbb\xbf")

    def test_blanked_word_drops_the_row(self, tmp_path):
        path = export_cards_to_csv(make_cards(), tmp_path / "cards.csv", cedict=FAKE_CEDICT)
        rewrite_rows(path, lambda rows: [dict(rows[0], word="")] + rows[1:])
        loaded = load_cards_from_csv(path)
        assert [c.word for c in loaded] == ["世界"]

    def test_reviewer_edits_are_authoritative(self, tmp_path):
        path = export_cards_to_csv(make_cards(), tmp_path / "cards.csv", cedict=FAKE_CEDICT)

        def edit(rows):
            rows[0]["sentence_translation"] = "Fixed translation."
            rows[0]["definition"] = "greeting (fixed sense)"
            rows[0]["word_pinyin"] = "nǐ hǎo!"
            return rows

        rewrite_rows(path, edit)
        first = load_cards_from_csv(path)[0]
        assert first.sentence_translation == "Fixed translation."
        assert first.definition == "greeting (fixed sense)"
        assert first.word_pinyin == "nǐ hǎo!"


class TestLoadValidation:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_cards_from_csv(tmp_path / "nope.csv")

    def test_missing_required_columns_raises(self, tmp_path):
        path = tmp_path / "bad.csv"
        path.write_text("foo,bar\n1,2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="missing required columns"):
            load_cards_from_csv(path)

    def test_header_only_file_raises(self, tmp_path):
        path = export_cards_to_csv([], tmp_path / "empty.csv", cedict=FAKE_CEDICT)
        with pytest.raises(ValueError, match="No usable card rows"):
            load_cards_from_csv(path)

    def test_unparseable_frequency_defaults_to_zero(self, tmp_path):
        path = export_cards_to_csv(make_cards(), tmp_path / "cards.csv", cedict=FAKE_CEDICT)
        rewrite_rows(path, lambda rows: [dict(rows[0], frequency="often")] + rows[1:])
        assert load_cards_from_csv(path)[0].frequency == 0


class TestOverridesReachNotes:
    def test_regular_note_uses_overrides(self):
        card = make_cards()[0]
        card.definition = "greeting (fixed sense)"
        card.word_pinyin = "nǐ hǎo!"
        note = create_anki_note(card, FAKE_CEDICT, get_chinese_model())
        # Fields: Word, Sentence, SentencePinyin, Pinyin, Definition, ...
        assert note.fields[3] == "nǐ hǎo!"
        assert note.fields[4] == "greeting (fixed sense)"

    def test_cloze_note_uses_overrides(self):
        card = make_cards()[0]
        card.definition = "greeting (fixed sense)"
        card.word_pinyin = "nǐ hǎo!"
        note = create_cloze_note(card, FAKE_CEDICT, get_chinese_cloze_model())
        # Fields: Text, Word, Pinyin, Definition, ...
        assert note.fields[2] == "nǐ hǎo!"
        assert note.fields[3] == "greeting (fixed sense)"

    def test_blank_overrides_fall_back_to_cedict(self):
        note = create_anki_note(make_cards()[0], FAKE_CEDICT, get_chinese_model())
        assert note.fields[4] == "hello"


class TestBuildFromReview:
    def test_builds_apkg_honoring_edits_and_deletions(self, tmp_path, monkeypatch):
        path = export_cards_to_csv(make_cards(), tmp_path / "cards.csv", cedict=FAKE_CEDICT)

        def edit(rows):
            rows[0]["sentence_translation"] = "Fixed translation."
            return rows[:1]  # delete the 世界 row

        rewrite_rows(path, edit)
        monkeypatch.setattr(main_module, "load_cedict", lambda: FAKE_CEDICT)

        main_module.build_from_review(
            str(path), deck_name="Reviewed", output_dir=str(tmp_path / "out")
        )

        apkg = tmp_path / "out" / "Reviewed.apkg"
        assert apkg.exists()
        notes = read_notes(apkg, tmp_path)
        assert len(notes) == 1
        fields = notes[0][0].split(FIELD_SEP)
        assert fields[0] == "你好"
        assert fields[5] == "Fixed translation."

    def test_cli_from_review_dispatch(self, tmp_path, monkeypatch):
        path = export_cards_to_csv(make_cards(), tmp_path / "cards.csv", cedict=FAKE_CEDICT)
        monkeypatch.setattr(main_module, "load_cedict", lambda: FAKE_CEDICT)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "main.py",
                "--from-review",
                str(path),
                "--deck",
                "CLI Reviewed",
                "--output",
                str(tmp_path / "out"),
            ],
        )

        main_module.main()

        assert (tmp_path / "out" / "CLI Reviewed.apkg").exists()

    def test_cli_requires_input_or_from_review(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["main.py"])
        with pytest.raises(SystemExit):
            main_module.main()
        assert "--input is required" in capsys.readouterr().err

    def test_cli_rejects_input_with_from_review(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(
            sys, "argv", ["main.py", "--input", "x.epub", "--from-review", "y.csv"]
        )
        with pytest.raises(SystemExit):
            main_module.main()
        assert "do not also pass --input" in capsys.readouterr().err
