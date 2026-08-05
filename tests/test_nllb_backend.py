"""Tests for the NLLB-200 CTranslate2 backend.

These are intentionally lightweight: they never download a model or import the
heavy optional dependencies. They verify wiring, config resolution, language
code mapping, and graceful behavior when deps/models are absent.
"""

from pathlib import Path

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
        ((batch, kwargs),) = backend.translator.calls
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
        ((batch, _),) = backend.translator.calls
        assert len(batch) == 1  # only the real text hit the model

    def test_single_translate_delegates_to_batch(self):
        backend = make_initialized_backend()
        assert backend.translate("你好") == "Hello"
        assert len(backend.translator.calls) == 1

    def test_empty_batch_returns_empty_list(self):
        backend = NLLBTranslateBackend()
        assert backend.translate_batch([]) == []
        assert backend.is_initialized() is False

    def test_unknown_language_code_raises(self):
        """Regression: unknown codes fell back to zho_Hans/eng_Latn, so a
        typo'd code produced a plausible-looking translation of the wrong
        pair instead of an error (Argos raises here)."""
        backend = make_initialized_backend()

        with pytest.raises(ValueError, match="source language"):
            backend.translate("你好", source_lang="zz")
        with pytest.raises(ValueError, match="target language"):
            backend.translate("你好", target_lang="klingon")
        # Nothing reached the model.
        assert backend.translator.calls == []


class TestCorruptedModelRecovery:
    """An interrupted download leaves a model.bin that exists but won't load;
    the cache check only tested existence, so the backend never self-healed."""

    def _stub_deps(self, monkeypatch, tmp_path, loads_ok):
        import translate.nllb_backend as nllb_module

        model_dir = tmp_path / "nllb_ct2_model"
        model_dir.mkdir()
        (model_dir / "model.bin").write_bytes(b"truncated")
        monkeypatch.setattr(nllb_module, "get_data_dir", lambda: tmp_path)

        state = {"downloads": 0, "translator_attempts": 0}

        class FakeCT2:
            @staticmethod
            def Translator(path, device=None, compute_type=None):
                state["translator_attempts"] += 1
                if state["translator_attempts"] == 1 and not loads_ok:
                    raise RuntimeError("unable to load model.bin")
                return FakeTranslator()

        class FakeTransformers:
            class AutoTokenizer:
                @staticmethod
                def from_pretrained(repo, revision=None):
                    return FakeTokenizer()

        def fake_snapshot_download(repo_id, local_dir, revision=None):
            state["downloads"] += 1
            target = Path(local_dir)
            target.mkdir(parents=True, exist_ok=True)
            (target / "model.bin").write_bytes(b"complete model")

        import sys
        import types

        hub = types.ModuleType("huggingface_hub")
        hub.snapshot_download = fake_snapshot_download
        monkeypatch.setitem(sys.modules, "ctranslate2", FakeCT2)
        monkeypatch.setitem(sys.modules, "transformers", FakeTransformers)
        monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
        return state

    def test_unloadable_cached_model_is_replaced(self, monkeypatch, tmp_path):
        state = self._stub_deps(monkeypatch, tmp_path, loads_ok=False)
        backend = NLLBTranslateBackend()

        assert backend.initialize() is True
        assert state["downloads"] == 1  # discarded and fetched again
        assert state["translator_attempts"] == 2

    def test_healthy_cached_model_is_not_re_downloaded(self, monkeypatch, tmp_path):
        state = self._stub_deps(monkeypatch, tmp_path, loads_ok=True)
        backend = NLLBTranslateBackend()

        assert backend.initialize() is True
        assert state["downloads"] == 0
