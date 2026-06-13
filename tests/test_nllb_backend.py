"""Tests for the NLLB-200 CTranslate2 backend.

These are intentionally lightweight: they never download a model or import the
heavy optional dependencies. They verify wiring, config resolution, language
code mapping, and graceful behavior when deps/models are absent.
"""

import pytest

from translate.nllb_backend import NLLBTranslateBackend, NLLB_LANG_CODES
from translate.manager import TranslationManager


class TestNLLBBackend:
    def test_module_imports_without_optional_deps(self):
        """Module + class import cleanly even if transformers isn't installed."""
        backend = NLLBTranslateBackend()
        assert backend is not None

    def test_metadata(self):
        backend = NLLBTranslateBackend()
        assert backend.get_quality_score() == 90  # above Argos (80)
        assert backend.requires_internet() is False
        assert "NLLB" in backend.get_name()
        assert backend.is_initialized() is False

    def test_language_code_mapping(self):
        assert NLLB_LANG_CODES["zh"] == "zho_Hans"
        assert NLLB_LANG_CODES["en"] == "eng_Latn"

    def test_config_overrides_model_repo(self):
        backend = NLLBTranslateBackend(config={"nllb_model_repo": "custom/repo"})
        assert backend.model_repo == "custom/repo"

    def test_empty_text_short_circuits_without_init(self):
        """Empty input must not trigger a model download/initialize."""
        backend = NLLBTranslateBackend()
        assert backend.translate("") == ""
        assert backend.translate("   ") == ""
        assert backend.is_initialized() is False  # never initialized

    def test_registered_first_in_default_manager_chain(self):
        """Manager should rank NLLB ahead of Argos by quality score."""
        manager = TranslationManager()
        names = [b.get_name() for b in manager.backends]
        assert any("NLLB" in n for n in names)
        # Sorted by quality desc, so NLLB precedes Argos
        nllb_idx = next(i for i, n in enumerate(names) if "NLLB" in n)
        argos_idx = next(i for i, n in enumerate(names) if "Argos" in n)
        assert nllb_idx < argos_idx
