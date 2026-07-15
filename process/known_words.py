"""Load a user's known-words list to exclude from deck building.

Format: plain text, UTF-8 (BOM tolerated). One word per line is the
canonical layout, but comma- or whitespace-separated words on a line also
work, so lists exported from Anki, Pleco, or a spreadsheet paste in
directly. Blank lines and `#` comments are ignored.
"""

import re
from pathlib import Path
from typing import Set

_SEPARATORS = re.compile(r"[,\s、，]+")  # commas (ASCII + Chinese), 、, whitespace


def load_known_words(path: str) -> Set[str]:
    """
    Load the set of known words from a text file.

    Args:
        path: Known-words file path

    Returns:
        Set of words to exclude from selection

    Raises:
        FileNotFoundError: the file doesn't exist
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Known-words file not found: {path}")

    words: Set[str] = set()
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            words.update(w for w in _SEPARATORS.split(line) if w)
    return words
