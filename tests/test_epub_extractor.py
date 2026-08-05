"""Tests for EPUB extraction, built on real EPUB files written to disk."""

import pytest
from ebooklib import epub

from extract.epub_extractor import extract_text_from_epub


def _make_chapter(title: str, file_name: str, body: str) -> epub.EpubHtml:
    chapter = epub.EpubHtml(title=title, file_name=file_name, lang="zh")
    chapter.content = f"<html><body><h1>{title}</h1><p>{body}</p></body></html>"
    return chapter


def _write_epub(path, chapters, spine):
    book = epub.EpubBook()
    book.set_identifier("test-book")
    book.set_title("测试书")
    book.set_language("zh")
    for chapter in chapters:
        book.add_item(chapter)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine
    epub.write_epub(str(path), book)


class TestEpubExtraction:
    def test_extracts_chapters_with_titles_and_text(self, tmp_path):
        ch1 = _make_chapter("第一章", "ch1.xhtml", "第一章的正文内容在这里。")
        ch2 = _make_chapter("第二章", "ch2.xhtml", "第二章的正文内容在这里。")
        path = tmp_path / "book.epub"
        _write_epub(path, [ch1, ch2], spine=[ch1, ch2])

        chapters = extract_text_from_epub(str(path))

        assert [c.title for c in chapters] == ["第一章", "第二章"]
        assert "第一章的正文内容" in chapters[0].text
        assert "第二章的正文内容" in chapters[1].text

    def test_chapters_follow_spine_not_manifest_order(self, tmp_path):
        """Regression: chapters were read via get_items() (manifest order),
        which can shuffle reading order and mis-tag cards."""
        ch1 = _make_chapter("第一章", "ch1.xhtml", "第一章的正文内容在这里。")
        ch2 = _make_chapter("第二章", "ch2.xhtml", "第二章的正文内容在这里。")
        path = tmp_path / "book.epub"
        # Manifest gets ch1 then ch2, but the spine says ch2 reads first.
        _write_epub(path, [ch1, ch2], spine=[ch2, ch1])

        chapters = extract_text_from_epub(str(path))

        assert [c.title for c in chapters] == ["第二章", "第一章"]

    def test_inline_markup_does_not_inject_spaces_into_words(self, tmp_path):
        """Regression: get_text(separator=" ") put a space between every pair
        of adjacent text nodes, so per-character markup (ruby, font spans --
        routine in Chinese EPUBs) turned 你好吗 into 你 好 吗. Those spaces
        reach cards, pinyin and TTS, and break the `word in sentence` checks
        that highlighting and cloze deletion depend on."""
        ch = epub.EpubHtml(title="第一章", file_name="ch1.xhtml", lang="zh")
        ch.content = (
            "<html><body><h1>第一章</h1>" "<p>他<b>说</b>了一<span>句</span>话。</p></body></html>"
        )
        path = tmp_path / "book.epub"
        _write_epub(path, [ch], spine=[ch])

        text = extract_text_from_epub(str(path))[0].text

        assert "他说了一句话。" in text
        assert "他 说" not in text

    def test_block_elements_stay_separated(self, tmp_path):
        """Removing the separator must not run neighbouring blocks together:
        two unpunctuated paragraphs would merge into one "sentence"."""
        ch = epub.EpubHtml(title="第一章", file_name="ch1.xhtml", lang="zh")
        ch.content = "<html><body><h1>第一章</h1><p>第一段内容</p><p>第二段内容</p></body></html>"
        path = tmp_path / "book.epub"
        _write_epub(path, [ch], spine=[ch])

        text = extract_text_from_epub(str(path))[0].text

        assert "第一段内容" in text
        assert "第二段内容" in text
        assert "第一段内容第二段内容" not in text

    def test_non_linear_spine_items_are_skipped(self, tmp_path):
        """`linear="no"` marks auxiliary content (notes, ads, backmatter)
        that isn't part of the reading flow."""
        ch1 = _make_chapter("第一章", "ch1.xhtml", "第一章的正文内容在这里。")
        aux = _make_chapter("附录", "aux.xhtml", "附录里的辅助内容在这里。")
        aux.is_linear = False
        path = tmp_path / "book.epub"
        _write_epub(path, [ch1, aux], spine=[ch1, aux])

        chapters = extract_text_from_epub(str(path))

        assert [c.title for c in chapters] == ["第一章"]

    def test_unreadable_file_raises_error_naming_path(self, tmp_path):
        not_an_epub = tmp_path / "broken.epub"
        not_an_epub.write_bytes(b"this is not a zip archive")

        with pytest.raises(ValueError, match="broken.epub"):
            extract_text_from_epub(str(not_an_epub))

    def test_missing_file_raises_error_naming_path(self, tmp_path):
        with pytest.raises(ValueError, match="missing.epub"):
            extract_text_from_epub(str(tmp_path / "missing.epub"))

    def test_navigation_document_is_not_a_chapter(self, tmp_path):
        ch1 = _make_chapter("第一章", "ch1.xhtml", "第一章的正文内容在这里。")
        path = tmp_path / "book.epub"
        _write_epub(path, [ch1], spine=[ch1])

        chapters = extract_text_from_epub(str(path))

        # nav.xhtml is a manifest document but not in the spine; it must not
        # appear as a phantom chapter.
        assert len(chapters) == 1
        assert chapters[0].title == "第一章"
