"""End-to-end pipeline test: generated EPUB in, real .apkg out.

Network is stubbed at the pipeline seams (CEDICT load, translation manager);
everything else -- extraction, cleaning, tokenization, selection, pinyin,
deck build -- runs for real, and assertions read the produced .apkg SQLite.
"""

import sqlite3
import zipfile

import jieba
import pytest
from ebooklib import epub

import main as main_module
from main import process_pipeline
from process.cedict_loader import DictEntry

FIELD_SEP = "\x1f"  # Anki packs note fields into one column with 0x1f

CHAPTER_SENTENCES = {
    "第一章": [
        "他每天早上都要去公园里跑步锻炼身体。",
        "我们的老师认真地给学生讲解这个问题。",
        "他每天早上都要去公园里跑步锻炼身体。",
    ],
    "第二章": [
        "科学家们正在努力研究宇宙深处的秘密。",
        "朋友之间应该互相帮助并且真诚相待。",
        "科学家们正在努力研究宇宙深处的秘密。",
    ],
}


@pytest.fixture
def book_epub(tmp_path):
    book = epub.EpubBook()
    book.set_identifier("integration-test")
    book.set_title("集成测试")
    book.set_language("zh")
    chapters = []
    for i, (title, sentences) in enumerate(CHAPTER_SENTENCES.items(), start=1):
        ch = epub.EpubHtml(title=title, file_name=f"ch{i}.xhtml", lang="zh")
        ch.content = f"<html><body><h1>{title}</h1><p>{''.join(sentences)}</p></body></html>"
        book.add_item(ch)
        chapters.append(ch)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = chapters
    path = tmp_path / "book.epub"
    epub.write_epub(str(path), book)
    return path


class StubTranslationManager:
    """Offline stand-in matching the TranslationManager surface main.py uses."""

    def __init__(self, config=None, cache_path=None, **kwargs):
        pass

    def set_cedict(self, cedict):
        pass

    def initialize(self, prefer_offline=True):
        return True

    def get_active_backend_name(self):
        return "Stub"

    def translate(self, text, source_lang="zh", target_lang="en"):
        return f"[translation of {text[:8]}]"

    def translate_batch(self, texts, source_lang="zh", target_lang="en"):
        return [self.translate(text, source_lang, target_lang) for text in texts]

    def cleanup(self):
        pass


@pytest.fixture
def offline_pipeline(monkeypatch):
    """Stub the two network seams; every real token gets a CEDICT entry."""
    all_text = "".join(s for sents in CHAPTER_SENTENCES.values() for s in sents)
    fake_cedict = {
        token: DictEntry(token, token, "ce4 shi4", ["test definition"])
        for token in jieba.cut(all_text)
        if len(token) >= 2
    }
    monkeypatch.setattr(main_module, "load_cedict", lambda: fake_cedict)
    monkeypatch.setattr(main_module, "TranslationManager", StubTranslationManager)
    return fake_cedict


def read_notes(apkg_path, tmp_path):
    with zipfile.ZipFile(apkg_path) as z:
        z.extract("collection.anki2", tmp_path / "unpacked")
    db = sqlite3.connect(tmp_path / "unpacked" / "collection.anki2")
    try:
        return db.execute("SELECT flds, tags FROM notes").fetchall()
    finally:
        db.close()


class TestFullPipeline:
    def test_epub_to_apkg(self, book_epub, offline_pipeline, tmp_path, capsys):
        process_pipeline(
            input_path=str(book_epub),
            deck_name="IntegrationTest",
            top_words=8,
            min_freq=1,
            output_dir=str(tmp_path / "out"),
            stats_file=str(tmp_path / "stats.json"),
        )

        apkg = tmp_path / "out" / "IntegrationTest.apkg"
        assert apkg.exists() and apkg.stat().st_size > 0

        notes = read_notes(apkg, tmp_path)
        assert 0 < len(notes) <= 8

        for flds, tags in notes:
            fields = flds.split(FIELD_SEP)
            word, sentence, sent_pinyin, word_pinyin, definition, translation = fields[:6]
            assert word  # Word present
            assert 'class="target"' in sentence  # inline highlight survived
            assert sent_pinyin and word_pinyin  # both pinyin fields filled
            assert not any(c.isdigit() for c in word_pinyin)  # tone marks, not numbers
            assert definition == "test definition"
            assert translation.startswith("[translation of")
            assert "chapter::" in tags  # chapter tag applied

        # Stats JSON reflects the same run
        import json

        stats = json.loads((tmp_path / "stats.json").read_text(encoding="utf-8"))
        assert stats["cards_created"] == len(notes)
        assert stats["chapters"] == 2
        assert stats["translation_backend"] == "Stub"

    def test_epub_to_cloze_apkg(self, book_epub, offline_pipeline, tmp_path, capsys):
        process_pipeline(
            input_path=str(book_epub),
            deck_name="IntegrationCloze",
            top_words=5,
            min_freq=1,
            output_dir=str(tmp_path / "out"),
            cloze=True,
        )

        notes = read_notes(tmp_path / "out" / "IntegrationCloze.apkg", tmp_path)
        assert notes
        for flds, _tags in notes:
            assert "{{c1::" in flds.split(FIELD_SEP)[0]  # Text field is a cloze

    def test_unsafe_deck_name_writes_sanitized_file(
        self, book_epub, offline_pipeline, tmp_path, capsys
    ):
        process_pipeline(
            input_path=str(book_epub),
            deck_name="A/B: test?",
            top_words=5,
            min_freq=1,
            output_dir=str(tmp_path / "out"),
        )

        assert (tmp_path / "out" / "A_B_ test_.apkg").exists()
