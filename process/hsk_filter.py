"""Filter words by HSK level."""

from typing import Set, List
from utils.file_utils import get_data_dir

# TODO: Implement HSK filtering
# This is a placeholder for future implementation


def load_hsk_words(levels: List[int]) -> Set[str]:
    """
    Load HSK words for specified levels.

    Args:
        levels: List of HSK levels (1-6)

    Returns:
        Set of words in those HSK levels
    """
    # Placeholder - needs HSK word list data
    print(f"HSK filtering not yet implemented (requested levels: {levels})")
    return set()


def filter_by_hsk(words: List[str], hsk_levels: List[int]) -> List[str]:
    """
    Filter words to only those in specified HSK levels.

    Args:
        words: List of words to filter
        hsk_levels: HSK levels to include

    Returns:
        Filtered list of words
    """
    if not hsk_levels:
        return words

    hsk_words = load_hsk_words(hsk_levels)

    if not hsk_words:
        return words

    return [word for word in words if word in hsk_words]
