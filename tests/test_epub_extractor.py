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

    def test_navigation_document_is_not_a_chapter(self, tmp_path):
        ch1 = _make_chapter("第一章", "ch1.xhtml", "第一章的正文内容在这里。")
        path = tmp_path / "book.epub"
        _write_epub(path, [ch1], spine=[ch1])

        chapters = extract_text_from_epub(str(path))

        # nav.xhtml is a manifest document but not in the spine; it must not
        # appear as a phantom chapter.
        assert len(chapters) == 1
        assert chapters[0].title == "第一章"
