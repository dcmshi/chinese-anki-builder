"""CEDICT word-by-word translation backend (fallback)."""

from typing import Optional, Dict, Any
from translate.base import TranslationBackend
from process.sentence_translator import translate_sentence, improve_translation


class CEDICTBackend(TranslationBackend):
    """
    CEDICT word-by-word translation backend.

    This is a fallback backend that uses CC-CEDICT for word-by-word translation.
    Lower quality than neural MT, but always available offline.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.cedict = None

    def initialize(self) -> bool:
        """Initialize CEDICT backend."""
        # CEDICT is loaded separately in the main pipeline
        # This backend is always ready
        self._initialized = True
        return True

    def is_available(self) -> bool:
        """CEDICT backend is always available."""
        return True

    def translate(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> str:
        """
        Translate using word-by-word CEDICT lookup.

        Args:
            text: Chinese text to translate
            source_lang: Source language (ignored, assumes Chinese)
            target_lang: Target language (ignored, outputs English)

        Returns:
            Word-by-word translation
        """
        if not self.cedict:
            # If cedict not provided, return empty string
            # This will be set by the translation manager
            return ""

        translation = translate_sentence(text, self.cedict)
        return improve_translation(translation)

    def set_cedict(self, cedict: Dict):
        """
        Set the CEDICT dictionary for this backend.

        Args:
            cedict: CC-CEDICT dictionary
        """
        self.cedict = cedict

    def get_name(self) -> str:
        """Get backend name."""
        return "CC-CEDICT (Word-by-word)"

    def requires_internet(self) -> bool:
        """CEDICT is fully offline."""
        return False

    def get_quality_score(self) -> int:
        """
        Quality score for word-by-word translation.

        Lower quality than neural MT, but acceptable as fallback.
        """
        return 40  # Lower than Argos (80), but functional
