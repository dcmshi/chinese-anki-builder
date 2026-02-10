"""Abstract base class for translation backends."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


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
