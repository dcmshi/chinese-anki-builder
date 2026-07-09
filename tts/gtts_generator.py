"""Generate TTS audio using Google Text-to-Speech.

gTTS is an optional dependency (uv sync --extra tts) and requires internet.
Generated MP3s are cached under data/cache/ keyed by text hash, so re-runs
and overlapping decks never re-request audio.
"""

from pathlib import Path
import hashlib
from typing import Optional

from utils.file_utils import get_cache_dir


def _load_gtts():
    """Return the gTTS class, or None when the optional dep is missing."""
    try:
        from gtts import gTTS

        return gTTS
    except ImportError:
        return None


def is_available() -> bool:
    """Whether TTS generation can run (gtts extra installed)."""
    return _load_gtts() is not None


def get_audio_filename(text: str) -> str:
    """
    Generate a deterministic filename for audio.

    Args:
        text: Text to generate audio for

    Returns:
        Filename (hash-based)
    """
    hash_digest = hashlib.md5(text.encode("utf-8")).hexdigest()
    return f"zh_{hash_digest}.mp3"


def generate_audio(text: str, output_path: Path, lang: str = "zh-CN") -> bool:
    """
    Generate TTS audio for Chinese text.

    Args:
        text: Chinese text to convert to speech
        output_path: Path to save audio file
        lang: gTTS language code

    Returns:
        True if successful, False otherwise
    """
    gtts_cls = _load_gtts()
    if gtts_cls is None:
        print("gTTS not installed; install with: uv sync --extra tts")
        return False

    try:
        tts = gtts_cls(text=text, lang=lang)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tts.save(str(output_path))
        return True
    except Exception as e:
        print(f"TTS generation failed for '{text}': {e}")
        return False


def get_or_create_audio(text: str, cache_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Return cached audio for the text, generating it if missing.

    Args:
        text: Chinese text to speak
        cache_dir: Override cache directory (defaults to data/cache/)

    Returns:
        Path to the MP3, or None when generation failed/unavailable
    """
    if cache_dir is None:
        cache_dir = get_cache_dir()

    path = Path(cache_dir) / get_audio_filename(text)
    if path.exists():
        return path

    return path if generate_audio(text, path) else None
