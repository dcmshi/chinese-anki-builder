"""Tests for the HY-MT1.5 llama.cpp backend.

Intentionally lightweight, mirroring the NLLB backend tests: no model
download, no import of the heavy optional deps. They verify wiring, config
resolution, the official prompt templates, and chain placement.
"""

from translate.hymt_backend import HYMTTranslateBackend, build_prompt
from translate.manager import TranslationManager


class TestHYMTBackend:
    def test_module_imports_without_optional_deps(self):
        """Module + class import cleanly even if llama_cpp isn't installed."""
        backend = HYMTTranslateBackend()
        assert backend is not None

    def test_metadata(self):
        backend = HYMTTranslateBackend()
        assert backend.get_quality_score() == 95  # above NLLB (90)
        assert backend.requires_internet() is False
        assert "HY-MT" in backend.get_name()
        assert backend.is_initialized() is False

    def test_config_overrides(self):
        backend = HYMTTranslateBackend(
            config={
                "hymt_model_repo": "custom/repo",
                "hymt_model_file": "*Q8_0.gguf",
                "hymt_revision": "abc123",
            }
        )
        assert backend.model_repo == "custom/repo"
        assert backend.model_file == "*Q8_0.gguf"
        assert backend.revision == "abc123"

    def test_empty_text_short_circuits_without_init(self):
        """Empty input must not trigger a model download/initialize."""
        backend = HYMTTranslateBackend()
        assert backend.translate("") == ""
        assert backend.translate("   ") == ""
        assert backend.is_initialized() is False

    def test_registered_first_in_default_manager_chain(self):
        """Manager should rank HY-MT ahead of NLLB and Argos by quality."""
        manager = TranslationManager()
        names = [b.get_name() for b in manager.backends]
        hymt_idx = next(i for i, n in enumerate(names) if "HY-MT" in n)
        nllb_idx = next(i for i, n in enumerate(names) if "NLLB" in n)
        assert hymt_idx < nllb_idx


class TestPromptTemplates:
    """HY-MT's model card prescribes a Chinese instruction for pairs
    involving Chinese and an English instruction otherwise."""

    def test_zh_to_en_uses_chinese_template(self):
        prompt = build_prompt("他说话了。", "zh", "en")
        assert "翻译成英文" in prompt
        assert "不要额外解释" in prompt
        assert prompt.endswith("他说话了。")

    def test_en_to_zh_uses_chinese_template(self):
        prompt = build_prompt("He spoke.", "en", "zh")
        assert "翻译成中文" in prompt

    def test_non_chinese_pair_uses_english_template(self):
        prompt = build_prompt("Bonjour.", "fr", "en")
        assert prompt.startswith("Translate the following segment into English")
        assert prompt.endswith("Bonjour.")
