"""Extract text from EPUB files."""

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from typing import List, Dict


class Chapter:
    """Represents a chapter with text content."""

    def __init__(self, title: str, text: str):
        self.title = title
        self.text = text

    def __repr__(self):
        return f"Chapter(title='{self.title}', text_len={len(self.text)})"


def extract_text_from_epub(epub_path: str) -> List[Chapter]:
    """
    Extract text from EPUB file, organized by chapters.

    Args:
        epub_path: Path to the EPUB file

    Returns:
        List of Chapter objects containing title and text
    """
    book = epub.read_epub(epub_path)
    chapters = []

    # Get all document items (chapters)
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            # Parse HTML content
            soup = BeautifulSoup(item.get_content(), "html.parser")

            # Extract text
            text = soup.get_text(separator=" ", strip=True)

            # Skip empty chapters
            if not text.strip():
                continue

            # Try to get chapter title from item or use a default
            title = item.get_name() or f"Chapter {len(chapters) + 1}"

            # Try to extract h1/h2 title from content
            heading = soup.find(["h1", "h2", "h3"])
            if heading:
                title = heading.get_text(strip=True) or title

            chapters.append(Chapter(title=title, text=text))

    # If no chapters found, treat whole book as one chapter
    if not chapters:
        chapters.append(Chapter(title="Book", text=""))

    return chapters


def get_full_text(chapters: List[Chapter]) -> str:
    """Combine all chapter texts into a single string."""
    return "\n\n".join(chapter.text for chapter in chapters)
