"""Translation module with pluggable backends."""

from translate.base import TranslationBackend
from translate.manager import TranslationManager

__all__ = ["TranslationBackend", "TranslationManager"]
