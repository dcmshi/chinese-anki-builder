"""Abstract base class for translation backends."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class TranslationBackend(ABC):
    """Abstract base class for translation backends."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize translation backend.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._initialized = False
        # Remembers a failed initialize() so callers stop retrying it (a
        # standalone backend used after a failed init would otherwise re-run
        # the full download/model load on every single translate() call).
        self._init_failed = False

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the backend (download models, load resources, etc.).

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if backend is available and ready to use.

        Returns:
            True if backend can be used, False otherwise
        """
        pass

    @abstractmethod
    def translate(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> str:
        """
        Translate text from source language to target language.

        Args:
            text: Text to translate
            source_lang: Source language code (default: "zh" for Chinese)
            target_lang: Target language code (default: "en" for English)

        Returns:
            Translated text
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of this backend.

        Returns:
            Backend name (e.g., "Argos Translate", "Google Translate API")
        """
        pass

    @abstractmethod
    def requires_internet(self) -> bool:
        """
        Check if this backend requires internet connection.

        Returns:
            True if internet required, False for offline backends
        """
        pass

    def translate_batch(
        self, texts: List[str], source_lang: str = "zh", target_lang: str = "en"
    ) -> List[str]:
        """
        Translate several texts at once, preserving order.

        Default implementation loops over translate(); backends with a
        native batch API (e.g. CTranslate2) override this for throughput.
        Per-item failure contract: an item whose translate() raises yields
        "" (with a warning) instead of failing the whole batch, so the
        manager's fallback chain engages only for that item. Single
        translate() calls still raise on failure.

        Args:
            texts: Texts to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Translations in the same order as the inputs ("" on failure)
        """
        results = []
        for text in texts:
            try:
                results.append(self.translate(text, source_lang, target_lang))
            except Exception as e:
                print(f"Warning: {self.get_name()} failed to translate {text!r}: {e}")
                results.append("")
        return results

    def try_initialize(self) -> bool:
        """
        Initialize once, remembering failure.

        initialize() can be expensive (model download, multi-GB load) and is
        reached from several places: the manager at startup, the manager's
        lazy fallback path, and translate() on standalone use. Retrying a
        backend that has already failed just repeats that cost per sentence.

        Returns:
            True if the backend is ready to translate
        """
        if self._initialized:
            return True
        if self._init_failed:
            return False
        if self.initialize():
            return True
        self._init_failed = True
        return False

    def is_initialized(self) -> bool:
        """
        Whether initialize() has completed successfully.

        Returns:
            True if the backend is ready to translate, False otherwise
        """
        return self._initialized

    def get_quality_score(self) -> int:
        """
        Get a quality score for this backend (0-100).

        Higher scores indicate better translation quality.
        Used for automatic backend selection.

        Returns:
            Quality score (default: 50)
        """
        return 50

    def cleanup(self):
        """Clean up resources (optional)."""
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}(initialized={self._initialized})"
