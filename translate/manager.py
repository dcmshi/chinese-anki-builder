"""Translation manager for coordinating multiple backends."""

from typing import List, Optional, Dict, Any
from translate.base import TranslationBackend
from translate.argos_backend import ArgosTranslateBackend
from translate.cedict_backend import CEDICTBackend


class TranslationManager:
    """
    Manages multiple translation backends with automatic fallback.

    Tries backends in order of quality score, falling back if one fails.
    """

    def __init__(self, backends: Optional[List[TranslationBackend]] = None):
        """
        Initialize translation manager.

        Args:
            backends: List of translation backends (auto-creates default if None)
        """
        if backends is None:
            # Default backends: Argos (preferred) -> CEDICT (fallback)
            self.backends = [
                ArgosTranslateBackend(),
                CEDICTBackend(),
            ]
        else:
            self.backends = backends

        # Sort by quality score (highest first)
        self.backends.sort(key=lambda b: b.get_quality_score(), reverse=True)

        self.active_backend: Optional[TranslationBackend] = None

    def initialize(self, prefer_offline: bool = True) -> bool:
        """
        Initialize translation backends.

        Args:
            prefer_offline: Prefer offline backends (default: True)

        Returns:
            True if at least one backend initialized successfully
        """
        initialized_count = 0

        for backend in self.backends:
            # Skip online backends if preferring offline
            if prefer_offline and backend.requires_internet():
                print(f"Skipping {backend.get_name()} (requires internet)")
                continue

            # Check availability
            if not backend.is_available():
                print(f"Skipping {backend.get_name()} (not available)")
                continue

            # Try to initialize
            try:
                if backend.initialize():
                    print(f"✓ Initialized: {backend.get_name()}")
                    initialized_count += 1

                    # Set as active if first successful backend
                    if self.active_backend is None:
                        self.active_backend = backend
                        print(f"→ Using: {backend.get_name()}")
                else:
                    print(f"✗ Failed to initialize: {backend.get_name()}")
            except Exception as e:
                print(f"✗ Error initializing {backend.get_name()}: {e}")

        return initialized_count > 0

    def set_cedict(self, cedict: Dict):
        """
        Set CEDICT dictionary for CEDICT backend.

        Args:
            cedict: CC-CEDICT dictionary
        """
        for backend in self.backends:
            if isinstance(backend, CEDICTBackend):
                backend.set_cedict(cedict)

    def translate(
        self,
        text: str,
        source_lang: str = "zh",
        target_lang: str = "en",
        fallback: bool = True,
    ) -> str:
        """
        Translate text using available backends.

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            fallback: Try fallback backends if primary fails (default: True)

        Returns:
            Translated text
        """
        if not text or not text.strip():
            return ""

        # Try active backend first
        if self.active_backend:
            try:
                result = self.active_backend.translate(text, source_lang, target_lang)
                if result and result.strip():
                    return result
            except Exception as e:
                print(f"Translation failed with {self.active_backend.get_name()}: {e}")

        # Try fallback backends if enabled
        if fallback:
            for backend in self.backends:
                if backend == self.active_backend:
                    continue  # Already tried

                if not backend._initialized:
                    continue

                try:
                    result = backend.translate(text, source_lang, target_lang)
                    if result and result.strip():
                        print(f"Used fallback: {backend.get_name()}")
                        return result
                except Exception as e:
                    print(f"Fallback {backend.get_name()} failed: {e}")

        # If all failed, return empty string
        return ""

    def get_active_backend_name(self) -> str:
        """Get the name of the currently active backend."""
        if self.active_backend:
            return self.active_backend.get_name()
        return "None"

    def list_backends(self) -> List[Dict[str, Any]]:
        """
        List all available backends with their status.

        Returns:
            List of backend info dictionaries
        """
        return [
            {
                "name": backend.get_name(),
                "initialized": backend._initialized,
                "quality": backend.get_quality_score(),
                "offline": not backend.requires_internet(),
                "active": backend == self.active_backend,
            }
            for backend in self.backends
        ]

    def cleanup(self):
        """Clean up all backends."""
        for backend in self.backends:
            try:
                backend.cleanup()
            except Exception as e:
                print(f"Cleanup error for {backend.get_name()}: {e}")
