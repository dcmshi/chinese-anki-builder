"""File utility functions."""

import os
from pathlib import Path


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
