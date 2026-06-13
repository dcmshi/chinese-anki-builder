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


def load_cedict() -> Dict[str, DictEntry]:
    """
    Load CC-CEDICT into a dictionary.

    Returns:
        Dictionary mapping simplified Chinese words to DictEntry objects
    """
    dict_path = download_cedict()

    print("Parsing CC-CEDICT...")
    cedict = {}

    with open(dict_path, "r", encoding="utf-8") as f:
        for line in f:
            entry = parse_cedict_line(line)
            if entry:
                # Use simplified as key
                cedict[entry.simplified] = entry

    print(f"Loaded {len(cedict)} dictionary entries")
    return cedict
