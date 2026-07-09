"""Tests for PDF text extraction and heuristic chapter detection."""

import pytest

import extract.pdf_extractor as pdf_extractor
from extract.pdf_extractor import (
    FRONT_MATTER_TITLE,
    detect_chapter_heading,
    extract_text_from_pdf,
    split_text_into_chapters,
)


class TestDetectChapterHeading:
    @pytest.mark.parametrize(
        "line,expected",
        [
            ("第一章", "第一章"),
            ("第一章 疯狂年代", "第一章 疯狂年代"),
            ("第3回：标题", "第3回 标题"),
            ("  第十二章  寂静的春天  ", "第十二章 寂静的春天"),
            ("第２卷", "第２卷"),
        ],
    )
    def test_accepts_headings(self, line, expected):
        assert detect_chapter_heading(line) == expected

    @pytest.mark.parametrize(
        "line",
        [
            "第一章的内容非常精彩。",  # prose continuation
            "他读完了第一章，然后睡觉。",  # marker not at line start
            "第一章 这个标题实在太长了" + "长" * 30,  # over-long "title"
            "普通的一行正文。",
        ],
    )
    def test_rejects_prose(self, line):
        assert detect_chapter_heading(line) is None


class TestSplitTextIntoChapters:
    def test_splits_on_headings(self):
        text = (
            "第一章 起源\n"
            "第一章的正文内容在这里。\n"
            "第二章 发展\n"
            "第二章的正文内容在这里。\n"
        )
        chapters = split_text_into_chapters(text)

        assert [c.title for c in chapters] == ["第一章 起源", "第二章 发展"]
        assert "第一章的正文内容" in chapters[0].text
        assert "第二章的正文内容" in chapters[1].text

    def test_front_matter_before_first_heading(self):
        text = "序言的内容。\n第一章\n正文。\n"
        chapters = split_text_into_chapters(text)

        assert chapters[0].title == FRONT_MATTER_TITLE
        assert "序言的内容" in chapters[0].text
        assert chapters[1].title == "第一章"

    def test_no_headings_falls_back_to_single_chapter(self):
        text = "只是一些没有章节标记的内容。\n更多内容。"
        chapters = split_text_into_chapters(text)

        assert len(chapters) == 1
        assert chapters[0].title == "PDF Book"
        assert "更多内容" in chapters[0].text

    def test_empty_text_gives_no_chapters(self):
        assert split_text_into_chapters("") == []


class TestExtractTextFromPdf:
    def test_extracts_chapters_from_pages(self, monkeypatch):
        class FakePage:
            def __init__(self, text):
                self._text = text

            def extract_text(self):
                return self._text

        class FakeReader:
            def __init__(self, path):
                self.pages = [
                    FakePage("第一章 起源\n第一章的正文。"),
                    FakePage("第二章 发展\n第二章的正文。"),
                ]

        monkeypatch.setattr(pdf_extractor, "PdfReader", FakeReader)

        chapters = extract_text_from_pdf("fake.pdf")

        assert [c.title for c in chapters] == ["第一章 起源", "第二章 发展"]
