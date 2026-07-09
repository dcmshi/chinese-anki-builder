"""Load and parse CC-CEDICT dictionary."""

import requests
import gzip
from pathlib import Path
from typing import Dict, List, Optional
from utils.file_utils import get_data_dir


CEDICT_URL = "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz"


class DictEntry:
    """Represents a CC-CEDICT dictionary entry."""

    def __init__(self, traditional: str, simplified: str, pinyin: str, definitions: List[str]):
        self.traditional = traditional
        self.simplified = simplified
        self.pinyin = pinyin
        self.definitions = definitions

    def get_first_definition(self) -> str:
        """Get the first (primary) definition."""
        return self.definitions[0] if self.definitions else ""

    def __repr__(self):
        return f"DictEntry({self.simplified}, {self.pinyin}, {self.get_first_definition()})"


def download_cedict(force: bool = False) -> Path:
    """
    Download CC-CEDICT if not already cached.

    Args:
        force: Force re-download even if cached

    Returns:
        Path to downloaded dictionary file
    """
    data_dir = get_data_dir()
    dict_path = data_dir / "cedict.txt"

    if dict_path.exists() and not force:
        print(f"Using cached CC-CEDICT at {dict_path}")
        return dict_path

    print(f"Downloading CC-CEDICT from {CEDICT_URL}...")

    try:
        # (connect timeout, read timeout) so a stalled server can't hang forever
        response = requests.get(CEDICT_URL, stream=True, timeout=(10, 60))
        response.raise_for_status()
        compressed_data = response.content
    except requests.RequestException as e:
        raise RuntimeError(
            f"Failed to download CC-CEDICT from {CEDICT_URL}: {e}. "
            f"Check your internet connection, or place a cedict.txt manually at {dict_path}."
        ) from e

    # Decompress
    decompressed_data = gzip.decompress(compressed_data)

    # Write to file
    dict_path.write_bytes(decompressed_data)

    print(f"CC-CEDICT downloaded to {dict_path}")
    return dict_path


def parse_cedict_line(line: str) -> Optional[DictEntry]:
    """
    Parse a single line from CC-CEDICT.

    Format: 繁體 简体 [pin yin] /definition1/definition2/

    Args:
        line: Line from CC-CEDICT file

    Returns:
        DictEntry object or None if line is invalid
    """
    line = line.strip()

    # Skip comments and empty lines
    if not line or line.startswith("#"):
        return None

    try:
        # Split into word part and definition part
        parts = line.split("/")

        # Extract words and pinyin
        word_part = parts[0].strip()
        word_parts = word_part.split("[")

        if len(word_parts) != 2:
            return None

        # Get traditional and simplified
        words = word_parts[0].strip().split()
        if len(words) != 2:
            return None

        traditional = words[0]
        simplified = words[1]

        # Get pinyin
        pinyin = word_parts[1].replace("]", "").strip()

        # Get definitions (filter empty ones)
        definitions = [d.strip() for d in parts[1:-1] if d.strip()]

        return DictEntry(traditional, simplified, pinyin, definitions)

    except (IndexError, ValueError):
        return None


def _is_proper_noun(entry: DictEntry) -> bool:
    """CC-CEDICT capitalizes the pinyin of proper nouns (Dong1 hai3 etc.)."""
    return bool(entry.pinyin) and entry.pinyin[0].isupper()


def prefer_entry(existing: DictEntry, new: DictEntry) -> DictEntry:
    """
    Pick which of two entries for the same simplified form to keep.

    CC-CEDICT has multiple entries for many words (different pronunciations,
    proper-noun senses). Blindly keeping the last line gives learners
    arbitrary readings, e.g. 东西 dong1 xi1 "east and west" instead of
    dong1 xi5 "thing". Heuristics: prefer common words over proper nouns,
    then the entry with more definitions (usually the dominant sense).
    """
    if _is_proper_noun(existing) != _is_proper_noun(new):
        return existing if _is_proper_noun(new) else new
    if len(new.definitions) > len(existing.definitions):
        return new
    return existing


def load_cedict(dict_path: Optional[Path] = None) -> Dict[str, DictEntry]:
    """
    Load CC-CEDICT into a dictionary.

    Args:
        dict_path: Optional path to an existing CC-CEDICT file. Defaults to
            the cached copy, downloading it first if missing.

    Returns:
        Dictionary mapping simplified Chinese words to DictEntry objects
    """
    if dict_path is None:
        dict_path = download_cedict()

    print("Parsing CC-CEDICT...")
    cedict = {}

    with open(dict_path, "r", encoding="utf-8") as f:
        for line in f:
            entry = parse_cedict_line(line)
            if entry:
                # Use simplified as key; resolve duplicates by preference,
                # not file order.
                key = entry.simplified
                if key in cedict:
                    cedict[key] = prefer_entry(cedict[key], entry)
                else:
                    cedict[key] = entry

    print(f"Loaded {len(cedict)} dictionary entries")
    return cedict
