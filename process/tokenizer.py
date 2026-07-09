"""Tokenize Chinese text using jieba."""

import jieba
from collections import Counter
from typing import List
from utils.chinese_utils import is_multi_char_word, contains_chinese


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

        # Skip empty tokens
        if not token:
            continue

        # Skip pure whitespace
        if token.isspace():
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
    Filter to keep only multi-character words (2+ Chinese characters).

    Args:
        word_freq: Counter of word frequencies

    Returns:
        Counter with only multi-character words
    """
    return Counter({word: count for word, count in word_freq.items() if is_multi_char_word(word)})
