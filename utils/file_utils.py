"""File utility functions."""

import json
import re
from pathlib import Path

# Characters Windows forbids in filenames (plus control chars); also unsafe
# as literal path segments elsewhere ("/" nests directories).
_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(name: str, fallback: str = "deck") -> str:
    """
    Make a string safe to use as a single filename component.

    Replaces path separators and Windows-forbidden characters with
    underscores and strips trailing dots/spaces (illegal on Windows).
    The original string (e.g. an Anki deck name) is not restricted --
    only its on-disk representation is.

    Args:
        name: Proposed filename (without extension)
        fallback: Used when sanitizing leaves nothing

    Returns:
        Safe filename component
    """
    sanitized = _UNSAFE_FILENAME_CHARS.sub("_", name).strip().rstrip(". ")
    return sanitized or fallback


def ensure_dir(directory: str | Path) -> Path:
    """Create directory if it doesn't exist."""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_data_dir() -> Path:
    """Get the data directory for caching resources."""
    data_dir = Path(__file__).parent.parent / "data"
    return ensure_dir(data_dir)


def get_cache_dir() -> Path:
    """Get the cache directory for TTS audio."""
    cache_dir = get_data_dir() / "cache"
    return ensure_dir(cache_dir)


def write_stats_json(path: str | Path, stats: dict) -> Path:
    """
    Write pipeline stats to a JSON file (UTF-8, human-readable).

    Args:
        path: Destination file path (parent dirs created as needed)
        stats: Stats dictionary to serialize

    Returns:
        Path the stats were written to
    """
    path = Path(path)
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return path
