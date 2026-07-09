"""Extract text from PDF files."""

import re
from pypdf import PdfReader
from typing import List, Optional
from extract.epub_extractor import Chapter


# Chapter markers like 第一章 / 第12回 / 第３卷, optionally followed by a title.
_CHAPTER_MARKER_RE = re.compile(
    r"^\s*(第[一二三四五六七八九十百千万零两0-9０-９]{1,6}[章节回卷部篇])(.*)$"
)
# Sentence punctuation never appears in a real heading; its presence means the
# line is prose that merely starts with a chapter reference.
_SENTENCE_PUNCT_RE = re.compile(r"[。！？，、；.!?,;]")
# Particles that continue a sentence ("第一章的内容...") rather than title it.
_PROSE_CONTINUATIONS = "的了是在就都也和与被把"

# Title given to content appearing before the first detected heading.
FRONT_MATTER_TITLE = "Front Matter"


def detect_chapter_heading(line: str) -> Optional[str]:
    """
    Return the chapter title if the line looks like a chapter heading.

    Accepts "第一章", "第一章 疯狂年代", "第3回：标题" etc.; rejects prose
    that happens to start with a chapter reference.
    """
    match = _CHAPTER_MARKER_RE.match(line)
    if not match:
        return None

    marker, rest = match.group(1), match.group(2).strip()
    if not rest:
        return marker
    if len(rest) > 30 or _SENTENCE_PUNCT_RE.search(rest):
        return None
    if rest[0] in _PROSE_CONTINUATIONS:
        return None

    title = rest.lstrip(":：-—·").strip()
    return f"{marker} {title}" if title else marker


def split_text_into_chapters(full_text: str, fallback_title: str = "PDF Book") -> List[Chapter]:
    """
    Split raw PDF text into chapters on heading lines.

    Args:
        full_text: Text of the whole PDF, newline-separated
        fallback_title: Title used when no headings are detected

    Returns:
        List of Chapter objects; a single fallback chapter if no headings
        were found
    """
    chapters: List[Chapter] = []
    current_title: Optional[str] = None
    current_lines: List[str] = []

    def flush():
        text = "\n".join(current_lines).strip()
        if text:
            title = current_title if current_title is not None else FRONT_MATTER_TITLE
            chapters.append(Chapter(title=title, text=text))

    for line in full_text.split("\n"):
        heading = detect_chapter_heading(line)
        if heading is not None:
            flush()
            current_title = heading
            current_lines = []
        else:
            current_lines.append(line)
    flush()

    # No headings anywhere: single-chapter fallback (previous behavior).
    if not any(c.title != FRONT_MATTER_TITLE for c in chapters):
        text = full_text.strip()
        return [Chapter(title=fallback_title, text=text)] if text else []

    return chapters


def extract_text_from_pdf(pdf_path: str) -> List[Chapter]:
    """
    Extract text from PDF file with heuristic chapter detection.

    Chapters are split on heading lines such as 第一章 / 第12回; PDFs
    without recognizable headings fall back to a single chapter.
    Note: basic text extraction without OCR.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of Chapter objects
    """
    reader = PdfReader(pdf_path)

    all_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            all_text.append(text)

    return split_text_into_chapters("\n".join(all_text))
