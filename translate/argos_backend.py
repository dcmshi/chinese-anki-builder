"""Argos Translate backend - offline neural machine translation."""

import os
from typing import Optional, Dict, Any
from translate.base import TranslationBackend


class ArgosTranslateBackend(TranslationBackend):
    """
    Argos Translate backend for offline neural MT.

    Uses argostranslate library for high-quality offline translation.
    Downloads language models on first use and caches them locally.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.argos = None
        self.installed_languages = None

    def initialize(self) -> bool:
        """Initialize Argos Translate and download required language packages."""
        import sys

        # Check Python version compatibility
        if sys.version_info >= (3, 14):
            print("Warning: Argos Translate may not be compatible with Python 3.14+")
            print("For best results, use Python 3.12 or 3.13")
            print("Falling back to CC-CEDICT translation...")
            return False

        try:
            import argostranslate.package
            import argostranslate.translate

            self.argos = argostranslate

            # Update package index
            print("Updating Argos Translate package index...")
            argostranslate.package.update_package_index()

            # Get available packages
            available_packages = argostranslate.package.get_available_packages()

            # Find Chinese -> English package
            zh_en_package = None
            for pkg in available_packages:
                if pkg.from_code == "zh" and pkg.to_code == "en":
                    zh_en_package = pkg
                    break

            if not zh_en_package:
                print("Error: Chinese -> English package not found in Argos Translate")
                return False

            # Check if already installed
            installed_packages = argostranslate.package.get_installed_packages()
            already_installed = any(
                pkg.from_code == "zh" and pkg.to_code == "en" for pkg in installed_packages
            )

            if not already_installed:
                print(f"Downloading Argos Translate model: {zh_en_package.package_version}")
                print("This may take a few minutes on first run...")
                argostranslate.package.install_from_path(
                    zh_en_package.download()
                )
                print("Model downloaded and installed successfully!")
            else:
                print("Using cached Argos Translate model")

            self.installed_languages = argostranslate.translate.get_installed_languages()
            self._initialized = True
            return True

        except ImportError:
            print("Error: argostranslate not installed")
            print("Install with: uv add argostranslate")
            return False
        except Exception as e:
            print(f"Error initializing Argos Translate: {e}")
            return False

    def is_available(self) -> bool:
        """Check if Argos Translate is available."""
        try:
            import argostranslate
            return True
        except ImportError:
            return False

    def translate(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> str:
        """
        Translate text using Argos Translate.

        Args:
            text: Chinese text to translate
            source_lang: Source language code (default: "zh")
            target_lang: Target language code (default: "en")

        Returns:
            Translated English text

        Raises:
            RuntimeError/ValueError on failure. Never returns the source text:
            a non-empty return is treated as success by TranslationManager and
            cached, which would silently disable its fallback chain and put
            the Chinese sentence on the card as its own "translation".
        """
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("Argos Translate not initialized")

        # Get translation language objects
        from_lang = next(
            (lang for lang in self.installed_languages if lang.code == source_lang),
            None
        )
        to_lang = next(
            (lang for lang in self.installed_languages if lang.code == target_lang),
            None
        )

        if not from_lang or not to_lang:
            raise ValueError(f"Language pair {source_lang}->{target_lang} not available")

        # Get translation
        translation = from_lang.get_translation(to_lang)

        if not translation:
            raise ValueError("Translation model not found")

        return translation.translate(text)

    def get_name(self) -> str:
        """Get backend name."""
        return "Argos Translate (Offline Neural MT)"

    def requires_internet(self) -> bool:
        """Argos Translate is offline after initial model download."""
        return False

    def get_quality_score(self) -> int:
        """
        Quality score for Argos Translate.

        Neural MT provides much better quality than word-by-word.
        """
        return 80  # High quality, better than word-by-word (50)
