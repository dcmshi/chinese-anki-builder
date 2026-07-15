"""Tests for the NLLB-200 CTranslate2 backend.

These are intentionally lightweight: they never download a model or import the
heavy optional dependencies. They verify wiring, config resolution, language
code mapping, and graceful behavior when deps/models are absent.
"""


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

    def test_revision_pins_resolved_from_config(self):
        backend = NLLBTranslateBackend(
            config={
                "nllb_model_revision": "abc123",
                "nllb_tokenizer_revision": "def456",
            }
        )
        assert backend.model_revision == "abc123"
        assert backend.tokenizer_revision == "def456"


class FakeTokenizer:
    """Minimal tokenizer stand-in for exercising the CT2 batch path."""

    def __init__(self):
        self.src_lang = None

    def encode(self, text):
        return [101, 102]

    def convert_ids_to_tokens(self, ids):
        return [f"t{i}" for i in ids]

    def convert_tokens_to_ids(self, tokens):
        return list(range(len(tokens)))

    def decode(self, ids):
        return "Hello"


class FakeResult:
    def __init__(self, hypothesis):
        self.hypotheses = [hypothesis]


class FakeTranslator:
    def __init__(self):
        self.calls = []

    def translate_batch(self, batch, **kwargs):
        self.calls.append((batch, kwargs))
        return [FakeResult(["eng_Latn", "▁Hello"]) for _ in batch]


def make_initialized_backend():
    backend = NLLBTranslateBackend()
    backend._initialized = True
    backend.translator = FakeTranslator()
    backend.tokenizer = FakeTokenizer()
    return backend


class TestNLLBBatchDecoding:
    def test_batch_passes_decoding_guards_to_ct2(self):
        """Repetition/length guards must reach CTranslate2 — NLLB loops on
        noisy input without them."""
        backend = make_initialized_backend()

        results = backend.translate_batch(["你好", "再见"])

        assert results == ["Hello", "Hello"]
        (batch, kwargs), = backend.translator.calls
        assert len(batch) == 2
        assert kwargs["beam_size"] == 4
        assert kwargs["no_repeat_ngram_size"] == 3
        assert kwargs["max_input_length"] == 256
        assert kwargs["max_decoding_length"] == 256
        assert kwargs["target_prefix"] == [["eng_Latn"], ["eng_Latn"]]

    def test_batch_preserves_empty_positions_without_model_calls(self):
        backend = make_initialized_backend()

        results = backend.translate_batch(["", "你好", "   "])

        assert results == ["", "Hello", ""]
        (batch, _), = backend.translator.calls
        assert len(batch) == 1  # only the real text hit the model

    def test_single_translate_delegates_to_batch(self):
        backend = make_initialized_backend()
        assert backend.translate("你好") == "Hello"
        assert len(backend.translator.calls) == 1

    def test_empty_batch_returns_empty_list(self):
        backend = NLLBTranslateBackend()
        assert backend.translate_batch([]) == []
        assert backend.is_initialized() is False
