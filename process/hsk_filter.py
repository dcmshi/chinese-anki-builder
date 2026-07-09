"""Filter words by HSK level.

Word lists are the HSK 3.0 lists from https://github.com/krmanik/HSK-3.0
(levels 1-6 plus the combined 7-9 band, addressed here as level 7). Like
CC-CEDICT, they are downloaded on first use and cached under data/hsk/.
"""

import re
import requests
from pathlib import Path
from typing import Set, List, Optional

from utils.file_utils import ensure_dir, get_data_dir

# Raw files inside the krmanik/HSK-3.0 repo ("New HSK (2025)/HSK Words/").
HSK_WORDLIST_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/krmanik/HSK-3.0/main/"
    "New%20HSK%20(2025)/HSK%20Words/HSK_Level_{level}_words.txt"
)

# Level 7 means the combined HSK 7-9 band (that's how HSK 3.0 publishes it).
_LEVEL_FILE_KEYS = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7-9"}

# Entries like 本1 / 地2 carry homograph markers that aren't part of the word.
_HOMOGRAPH_MARKER_RE = re.compile(r"\d+$")


def parse_hsk_levels(spec: str) -> List[int]:
    """
    Parse a --hsk CLI value into a list of levels.

    Accepted forms:
        "3"      -> [1, 2, 3]        (everything up to level 3)
        "2-4"    -> [2, 3, 4]        (inclusive range)
        "1,3,5"  -> [1, 3, 5]        (explicit list)

    Level 7 stands for the combined HSK 7-9 band.
    """
    spec = spec.strip()

    if re.fullmatch(r"\d+-\d+", spec):
        start, end = (int(x) for x in spec.split("-"))
        levels = list(range(start, end + 1))
    elif "," in spec:
        levels = [int(x) for x in spec.split(",")]
    elif spec.isdigit():
        levels = list(range(1, int(spec) + 1))
    else:
        raise ValueError(f"Invalid HSK level spec: {spec!r} (use e.g. '3', '2-4', '1,3')")

    for level in levels:
        if level not in _LEVEL_FILE_KEYS:
            raise ValueError(f"Invalid HSK level {level}: must be 1-7 (7 = the 7-9 band)")
    if not levels:
        raise ValueError(f"Invalid HSK level spec: {spec!r}")

    return levels


def _hsk_cache_dir(cache_dir: Optional[Path] = None) -> Path:
    if cache_dir is not None:
        return ensure_dir(cache_dir)
    return ensure_dir(get_data_dir() / "hsk")


def download_hsk_list(level: int, cache_dir: Optional[Path] = None, force: bool = False) -> Path:
    """
    Download the word list for one HSK level if not already cached.

    Args:
        level: HSK level (1-7, 7 = the 7-9 band)
        cache_dir: Override cache directory (defaults to data/hsk/)
        force: Force re-download even if cached

    Returns:
        Path to the cached word list
    """
    file_key = _LEVEL_FILE_KEYS[level]
    path = _hsk_cache_dir(cache_dir) / f"hsk_{file_key}.txt"

    if path.exists() and not force:
        return path

    url = HSK_WORDLIST_URL_TEMPLATE.format(level=file_key)
    print(f"Downloading HSK {file_key} word list...")
    try:
        response = requests.get(url, timeout=(10, 60))
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(
            f"Failed to download HSK {file_key} word list from {url}: {e}. "
            f"Check your internet connection, or place a word list (one word "
            f"per line) manually at {path}."
        ) from e

    path.write_bytes(response.content)
    return path


def _parse_hsk_words(text: str) -> Set[str]:
    """One word per line; strip homograph markers (本1) and blanks."""
    words = set()
    for line in text.splitlines():
        word = _HOMOGRAPH_MARKER_RE.sub("", line.strip())
        if word:
            words.add(word)
    return words


def load_hsk_words(levels: List[int], cache_dir: Optional[Path] = None) -> Set[str]:
    """
    Load HSK words for specified levels.

    Args:
        levels: List of HSK levels (1-7, 7 = the 7-9 band)
        cache_dir: Override cache directory (defaults to data/hsk/)

    Returns:
        Set of words in those HSK levels
    """
    words: Set[str] = set()
    for level in levels:
        if level not in _LEVEL_FILE_KEYS:
            raise ValueError(f"Invalid HSK level {level}: must be 1-7 (7 = the 7-9 band)")
        path = download_hsk_list(level, cache_dir=cache_dir)
        words |= _parse_hsk_words(path.read_text(encoding="utf-8"))
    return words


def filter_by_hsk(
    words: List[str], hsk_levels: List[int], cache_dir: Optional[Path] = None
) -> List[str]:
    """
    Filter words to only those in specified HSK levels.

    Args:
        words: List of words to filter
        hsk_levels: HSK levels to include (empty list = no filtering)
        cache_dir: Override cache directory (defaults to data/hsk/)

    Returns:
        Filtered list of words (original order preserved)
    """
    if not hsk_levels:
        return words

    hsk_words = load_hsk_words(hsk_levels, cache_dir=cache_dir)
    return [word for word in words if word in hsk_words]
