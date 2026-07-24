"""Tokenize Chinese text using jieba."""

import jieba
from collections import Counter
from typing import List
from utils.chinese_utils import is_han_only, is_multi_char_word, contains_chinese


class TokenStats:
    """Statistics about tokenized text."""

    def __init__(self):
        self.word_freq: Counter = Counter()
        self.total_words: int = 0
        self.unique_words: int = 0

    def __repr__(self):
        return (
            f"TokenStats(total={self.total_words}, "
            f"unique={self.unique_words}, "
            f"top_5={self.word_freq.most_common(5)})"
        )


def tokenize_text(text: str) -> List[str]:
    """
    Tokenize Chinese text using jieba.

    Args:
        text: Chinese text to tokenize

    Returns:
        List of tokens (words)
    """
    # Use jieba for segmentation
    tokens = jieba.cut(text)

    # Filter and collect valid tokens
    valid_tokens = []
    for token in tokens:
        token = token.strip()

        # Skip empty tokens (also covers whitespace-only: token is stripped)
        if not token:
            continue

        # Only keep tokens with Chinese characters
        if contains_chinese(token):
            valid_tokens.append(token)

    return valid_tokens


def compute_word_frequency(tokens: List[str]) -> TokenStats:
    """
    Compute word frequency statistics.

    Args:
        tokens: List of tokens from tokenize_text

    Returns:
        TokenStats object with frequency information
    """
    stats = TokenStats()
    stats.word_freq = Counter(tokens)
    stats.total_words = len(tokens)
    stats.unique_words = len(stats.word_freq)

    return stats


def filter_multi_char_words(word_freq: Counter) -> Counter:
    """
    Filter to the card-candidate pool: words of 2+ Chinese characters with no
    other scripts mixed in.

    Mixed tokens like "QQ群" or "iPhone手机" carry Han characters, so a
    contains-Chinese test keeps them; they then consume top-N slots and get
    dropped later as "no dictionary definition", shrinking the deck below the
    requested word count. Requiring Han-only text costs the rare loanword
    CC-CEDICT does list (卡拉OK) and buys a pool where every candidate can
    plausibly become a card. Token statistics upstream stay unfiltered.

    Args:
        word_freq: Counter of word frequencies

    Returns:
        Counter with only Han-only multi-character words
    """
    return Counter(
        {
            word: count
            for word, count in word_freq.items()
            if is_multi_char_word(word) and is_han_only(word)
        }
    )
