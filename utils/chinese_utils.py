"""Chinese text utility functions."""

import re


def is_chinese_char(char: str) -> bool:
    """Check if a character is Chinese."""
    return "\u4e00" <= char <= "\u9fff"


def contains_chinese(text: str) -> bool:
    """Check if text contains any Chinese characters."""
    return any(is_chinese_char(char) for char in text)


def is_multi_char_word(word: str) -> bool:
    """Check if word is multi-character (2+ Chinese chars)."""
    chinese_chars = [char for char in word if is_chinese_char(char)]
    return len(chinese_chars) >= 2


def clean_punctuation(text: str) -> str:
    """Remove or normalize Chinese and English punctuation."""
    # Replace Chinese punctuation with spaces
    chinese_punct = "。，、；：？！""''（）《》【】—…"
    for punct in chinese_punct:
        text = text.replace(punct, " ")

    # Replace English punctuation with spaces
    text = re.sub(r'[,\.;:\?!\(\)\[\]"\'—\-]', " ", text)

    return text


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    return re.sub(r"\s+", " ", text).strip()
