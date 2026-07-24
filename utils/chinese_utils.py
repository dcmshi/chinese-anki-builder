"""Chinese text utility functions."""

import re


# Han character ranges. The CJK Unified Ideographs block (4E00-9FFF) covers
# virtually all modern text, but Extension A and the compatibility ideographs
# show up in older/classical material and in names; without them those
# characters are invisible to every caller here (counted as punctuation).
_HAN_RANGES = (
    ("\u4e00", "\u9fff"),  # CJK Unified Ideographs
    ("\u3400", "\u4dbf"),  # CJK Unified Ideographs Extension A
    ("\uf900", "\ufaff"),  # CJK Compatibility Ideographs
)


def is_chinese_char(char: str) -> bool:
    """Check if a character is Chinese."""
    return any(low <= char <= high for low, high in _HAN_RANGES)


def contains_chinese(text: str) -> bool:
    """Check if text contains any Chinese characters."""
    return any(is_chinese_char(char) for char in text)


def is_multi_char_word(word: str) -> bool:
    """Check if word is multi-character (2+ Chinese chars)."""
    chinese_chars = [char for char in word if is_chinese_char(char)]
    return len(chinese_chars) >= 2


def is_han_only(word: str) -> bool:
    """Whether every character is Han (no Latin letters, digits, punctuation)."""
    return bool(word) and all(is_chinese_char(char) for char in word)


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    return re.sub(r"\s+", " ", text).strip()
