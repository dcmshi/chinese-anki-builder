"""Convert Chinese text to pinyin."""

from pypinyin import pinyin, Style
from typing import Dict
from process.cedict_loader import DictEntry


def word_to_pinyin(word: str, cedict: Dict[str, DictEntry] = None) -> str:
    """
    Convert a Chinese word to pinyin.

    Prefers CC-CEDICT pinyin if available, falls back to pypinyin.

    Args:
        word: Chinese word
        cedict: Optional CC-CEDICT dictionary for more accurate pinyin

    Returns:
        Pinyin with tone marks
    """
    # Try CC-CEDICT first for better accuracy
    if cedict and word in cedict:
        return cedict[word].pinyin

    # Fallback to pypinyin
    # Use TONE style for pinyin with tone marks (e.g., "nǐ hǎo")
    py = pinyin(word, style=Style.TONE)

    # Join syllables with spaces
    return " ".join([p[0] for p in py])


def sentence_to_pinyin(sentence: str) -> str:
    """
    Convert a Chinese sentence to pinyin.

    Args:
        sentence: Chinese sentence

    Returns:
        Pinyin with tone marks
    """
    py = pinyin(sentence, style=Style.TONE)
    return " ".join([p[0] for p in py])
