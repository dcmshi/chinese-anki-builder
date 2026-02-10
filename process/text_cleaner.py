"""Clean and normalize extracted text."""

from utils.chinese_utils import normalize_whitespace, clean_punctuation


def clean_text(text: str) -> str:
    """
    Clean extracted text.

    Args:
        text: Raw text from book

    Returns:
        Cleaned text with normalized whitespace
    """
    # Remove excessive whitespace
    text = normalize_whitespace(text)

    # Remove page numbers and common artifacts
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip lines that are just numbers (likely page numbers)
        if line.isdigit():
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def split_sentences(text: str) -> list[str]:
    """
    Split text into sentences.

    Uses Chinese sentence-ending punctuation.

    Args:
        text: Cleaned text

    Returns:
        List of sentences
    """
    import re

    # Chinese sentence endings: 。！？
    # Also handle English punctuation just in case
    sentences = re.split(r"[。！？.!?]+", text)

    # Clean and filter
    cleaned_sentences = []
    for sent in sentences:
        sent = sent.strip()
        if sent and len(sent) > 3:  # Skip very short fragments
            cleaned_sentences.append(sent)

    return cleaned_sentences
