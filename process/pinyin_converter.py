"""Convert Chinese text to pinyin."""

import re

from pypinyin import pinyin, Style
from typing import Dict
from process.cedict_loader import DictEntry


# Tone-marked vowels indexed by tone number - 1 (tones 1-4).
_TONE_MARKS = {
    "a": "āáǎà",
    "e": "ēéěè",
    "i": "īíǐì",
    "o": "ōóǒò",
    "u": "ūúǔù",
    "ü": "ǖǘǚǜ",
}

# Combining marks for the rare vowel-less syllables (ń, ň, ǹ, m̀ ...).
_COMBINING_MARKS = {1: "̄", 2: "́", 3: "̌", 4: "̀"}

_NUMBERED_SYLLABLE_RE = re.compile(r"^([A-Za-zü:]+)([1-5])$")


def _mark_vowel_index(base_lower: str) -> int:
    """Index of the vowel that carries the tone mark (standard placement)."""
    if "a" in base_lower:
        return base_lower.index("a")
    if "e" in base_lower:
        return base_lower.index("e")
    if "ou" in base_lower:
        return base_lower.index("o")
    for i in range(len(base_lower) - 1, -1, -1):
        if base_lower[i] in "aeiouü":
            return i
    return -1


def _convert_syllable(syllable: str) -> str:
    """Convert one numbered syllable (e.g. "hao3") to tone marks ("hǎo")."""
    match = _NUMBERED_SYLLABLE_RE.match(syllable)
    if not match:
        return syllable  # not numbered pinyin; pass through untouched

    base, tone = match.group(1), int(match.group(2))
    # CC-CEDICT writes ü as "u:" (lu:4) or "v" (lv4).
    base = base.replace("u:", "ü").replace("U:", "Ü").replace("v", "ü").replace("V", "Ü")

    if tone == 5:  # neutral tone carries no mark
        return base

    idx = _mark_vowel_index(base.lower())
    if idx < 0:
        # Vowel-less syllable (ń, ǹ, m̀ ...): combining mark on the last letter.
        return base + _COMBINING_MARKS[tone]

    vowel = base[idx]
    marked = _TONE_MARKS[vowel.lower()][tone - 1]
    if vowel.isupper():
        marked = marked.upper()
    return base[:idx] + marked + base[idx + 1 :]


def numbered_to_tone_marks(pinyin_str: str) -> str:
    """
    Convert CC-CEDICT numbered pinyin ("ni3 hao3") to tone marks ("nǐ hǎo").

    Tokens that aren't numbered syllables (already-marked pinyin,
    punctuation like the · in foreign names) pass through unchanged, so
    the function is safe to apply to any pinyin string.
    """
    return " ".join(_convert_syllable(tok) for tok in pinyin_str.split())


def word_to_pinyin(word: str, cedict: Dict[str, DictEntry] = None) -> str:
    """
    Convert a Chinese word to pinyin.

    Prefers CC-CEDICT pinyin if available, falls back to pypinyin. Either
    way the result uses tone marks ("nǐ hǎo"), never tone numbers -- CEDICT
    stores numbered pinyin, which used to leak onto cards while sentence
    pinyin used marks.

    Args:
        word: Chinese word
        cedict: Optional CC-CEDICT dictionary for more accurate pinyin

    Returns:
        Pinyin with tone marks
    """
    # Try CC-CEDICT first for better accuracy
    if cedict and word in cedict:
        return numbered_to_tone_marks(cedict[word].pinyin)

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
