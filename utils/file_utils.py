"""File utility functions."""

import contextlib
import json
import os
import re
import tempfile
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


@contextlib.contextmanager
def atomic_output_path(path: str | Path):
    """
    Yield a temporary path to write to, then move it into place atomically.

    A plain ``open(path, "w")`` truncates the target first, so an interrupted
    write (Ctrl-C, crash, full disk) leaves a half-written file behind that
    later runs happily treat as a valid cache -- a truncated dictionary
    parses fine, it just silently has fewer entries, forever. Writing to a
    sibling temp file and ``os.replace()``-ing it means readers only ever see
    the complete old file or the complete new one, and concurrent writers
    can't interleave.

    Args:
        path: Final destination path (parent dirs created as needed)

    Yields:
        Path to write to (same directory, so the replace stays on one volume)
    """
    path = Path(path)
    ensure_dir(path.parent)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        yield tmp_path
        os.replace(tmp_path, path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp_path.unlink()
        raise


def atomic_write_bytes(path: str | Path, data: bytes) -> Path:
    """Write bytes to path atomically (see atomic_output_path)."""
    with atomic_output_path(path) as tmp:
        tmp.write_bytes(data)
    return Path(path)


def atomic_write_text(path: str | Path, text: str, encoding: str = "utf-8") -> Path:
    """Write text to path atomically (see atomic_output_path)."""
    return atomic_write_bytes(path, text.encode(encoding))


def write_stats_json(path: str | Path, stats: dict) -> Path:
    """
    Write pipeline stats to a JSON file (UTF-8, human-readable).

    Args:
        path: Destination file path (parent dirs created as needed)
        stats: Stats dictionary to serialize

    Returns:
        Path the stats were written to
    """
    return atomic_write_text(path, json.dumps(stats, ensure_ascii=False, indent=2))
