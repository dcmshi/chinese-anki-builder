"""Clean and normalize extracted text."""

import re

from utils.chinese_utils import normalize_whitespace, is_chinese_char


# Sentence-ending punctuation (Chinese full stop / exclamation / question + ASCII !?).
# ASCII "." is intentionally excluded so decimals like "1.5万" aren't split.
_SENT_ENDERS = "。！？!?"
# Closing quotes/brackets that belong WITH the sentence they terminate.
_CLOSERS = "”’』」）》】)]"
# Opening quotes/brackets.
_OPENERS = "“‘『「（《【(["
# Marks that should never start a sentence (orphaned closers + stray mid punctuation).
_LEADING_JUNK = "，,、；;：:。．·…—–-　 " + _CLOSERS

# One sentence = text up to an ender run, plus any closing quotes that trail it,
# so `…理论。”` stays whole instead of orphaning the ” onto the next sentence.
# Class contents are escaped because _CLOSERS contains "]".
_SENTENCE_RE = re.compile(
    "[^" + re.escape(_SENT_ENDERS) + "]*"
    "[" + re.escape(_SENT_ENDERS) + "]+"
    "[" + re.escape(_CLOSERS) + "]*"
)


def _chinese_char_count(text: str) -> int:
    """Count Han characters (used to filter out punctuation-only fragments)."""
    return sum(1 for c in text if is_chinese_char(c))


def _tidy_sentence(sent: str) -> str:
    """Trim orphaned leading punctuation and dangling opening quotes."""
    sent = sent.strip()
    # Drop leading orphaned closers / stray punctuation (e.g. a leading ”).
    sent = sent.lstrip(_LEADING_JUNK)
    # Drop a dangling opening quote/bracket at the end (its quote continues elsewhere).
    sent = sent.rstrip(_OPENERS + " 　")
    return sent.strip()


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


def split_sentences(text: str, min_chinese_chars: int = 2) -> list[str]:
    """
    Split text into sentences on Chinese sentence-ending punctuation.

    Terminal punctuation and trailing closing quotes are kept with their
    sentence (so `…。”` stays whole), each sentence is tidied of orphaned
    leading/dangling punctuation, and punctuation-only fragments are dropped.

    Args:
        text: Cleaned text
        min_chinese_chars: Minimum Han characters for a sentence to be kept

    Returns:
        List of cleaned sentences
    """
    matches = list(_SENTENCE_RE.finditer(text))
    sentences = [m.group() for m in matches]

    # Keep any trailing remainder that has no ending punctuation.
    end = matches[-1].end() if matches else 0
    tail = text[end:]
    if tail.strip():
        sentences.append(tail)

    cleaned_sentences = []
    for sent in sentences:
        sent = _tidy_sentence(sent)
        if _chinese_char_count(sent) >= min_chinese_chars:
            cleaned_sentences.append(sent)

    return cleaned_sentences
