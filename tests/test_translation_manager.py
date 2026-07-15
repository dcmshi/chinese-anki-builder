"""Tests for TranslationManager fallback behavior.

Regression tests for the bug where neural backends returned the ORIGINAL
Chinese text on failure; the manager treated any non-empty string as success,
cached it, and never fell back -- cards showed the Chinese sentence as its own
"translation".
"""

import pytest

from translate.base import TranslationBackend
from translate.manager import TranslationManager
from translate.argos_backend import ArgosTranslateBackend
from translate.nllb_backend import NLLBTranslateBackend


class StubBackend(TranslationBackend):
    """Configurable in-memory backend for manager tests."""

    def __init__(self, name, quality, result=None, error=None):
        super().__init__()
        self._name = name
        self._quality = quality
        self._result = result
        self._error = error
        self.calls = 0
        self.batch_calls = []  # list of the text lists passed to translate_batch

    def initialize(self):
        self._initialized = True
        return True

    def is_available(self):
        return True

    def translate(self, text, source_lang="zh", target_lang="en"):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._result

    def translate_batch(self, texts, source_lang="zh", target_lang="en"):
        self.batch_calls.append(list(texts))
        if self._error is not None:
            raise self._error
        return [self._result for _ in texts]

    def get_name(self):
        return self._name

    def requires_internet(self):
        return False

    def get_quality_score(self):
        return self._quality


def make_manager(*backends):
    manager = TranslationManager(backends=list(backends))
    manager.initialize()
    return manager


class TestManagerFallback:
    def test_falls_back_when_primary_raises(self):
        primary = StubBackend("primary", 90, error=RuntimeError("model exploded"))
        fallback = StubBackend("fallback", 40, result="a translation")
        manager = make_manager(primary, fallback)

        assert manager.translate("这是一个句子。") == "a translation"
        assert primary.calls == 1
        assert fallback.calls == 1

    def test_falls_back_when_primary_returns_empty(self):
        primary = StubBackend("primary", 90, result="")
        fallback = StubBackend("fallback", 40, result="a translation")
        manager = make_manager(primary, fallback)

        assert manager.translate("这是一个句子。") == "a translation"

    def test_failure_result_is_not_cached(self):
        primary = StubBackend("primary", 90, error=RuntimeError("boom"))
        manager = make_manager(primary)

        assert manager.translate("这是一个句子。") == ""
        # A later retry must reach the backend again, not a cached failure.
        assert manager.translate("这是一个句子。") == ""
        assert primary.calls == 2

    def test_success_is_cached(self):
        primary = StubBackend("primary", 90, result="a translation")
        manager = make_manager(primary)

        assert manager.translate("这是一个句子。") == "a translation"
        assert manager.translate("这是一个句子。") == "a translation"
        assert primary.calls == 1


class TestBackendsRaiseInsteadOfEchoing:
    """A failing backend must raise -- returning the source text would be
    interpreted as a successful translation by the manager."""

    def test_argos_raises_on_missing_language_pair(self):
        backend = ArgosTranslateBackend()
        backend._initialized = True
        backend.installed_languages = []  # no zh/en available

        with pytest.raises(Exception):
            backend.translate("这是一个句子。")

    def test_nllb_raises_when_tokenizer_fails(self):
        class ExplodingTokenizer:
            def convert_ids_to_tokens(self, ids):
                return ids

            def encode(self, text):
                raise RuntimeError("tokenizer exploded")

        backend = NLLBTranslateBackend()
        backend._initialized = True
        backend.tokenizer = ExplodingTokenizer()
        backend.translator = object()

        with pytest.raises(RuntimeError):
            backend.translate("这是一个句子。")

    def test_manager_never_returns_source_text_when_all_backends_fail(self):
        source = "这是一个句子。"
        primary = StubBackend("primary", 90, error=RuntimeError("boom"))
        secondary = StubBackend("secondary", 40, error=RuntimeError("boom too"))
        manager = make_manager(primary, secondary)

        assert manager.translate(source) == ""


class MapBackend(StubBackend):
    """Stub whose batch output is looked up per text (\"\" when missing)."""

    def __init__(self, name, quality, mapping):
        super().__init__(name, quality)
        self._mapping = mapping

    def translate(self, text, source_lang="zh", target_lang="en"):
        self.calls += 1
        return self._mapping.get(text, "")

    def translate_batch(self, texts, source_lang="zh", target_lang="en"):
        self.batch_calls.append(list(texts))
        return [self._mapping.get(t, "") for t in texts]


class TestBatchTranslation:
    def test_batch_dedupes_and_preserves_order(self):
        primary = StubBackend("primary", 90, result="T")
        manager = make_manager(primary)

        results = manager.translate_batch(["a", "b", "a", ""])

        assert results == ["T", "T", "T", ""]
        # One batch call, and only the two unique non-empty texts hit it.
        assert primary.batch_calls == [["a", "b"]]

    def test_batch_serves_in_memory_cache(self):
        primary = StubBackend("primary", 90, result="T")
        manager = make_manager(primary)

        assert manager.translate("a") == "T"
        assert manager.translate_batch(["a", "a"]) == ["T", "T"]
        assert primary.batch_calls == []  # everything came from the cache

    def test_batch_falls_back_per_item_when_batch_raises(self):
        primary = StubBackend("primary", 90, error=RuntimeError("batch exploded"))
        fallback = StubBackend("fallback", 40, result="fb")
        manager = make_manager(primary, fallback)

        assert manager.translate_batch(["a", "b"]) == ["fb", "fb"]
        assert fallback.calls == 2

    def test_batch_empty_item_falls_back_individually(self):
        primary = MapBackend("primary", 90, {"b": "ok"})  # "a" -> ""
        fallback = StubBackend("fallback", 40, result="fb")
        manager = make_manager(primary, fallback)

        assert manager.translate_batch(["a", "b"]) == ["fb", "ok"]
        assert fallback.calls == 1  # only the failed item fell back

    def test_batch_returns_empty_when_everything_fails(self):
        primary = StubBackend("primary", 90, error=RuntimeError("boom"))
        manager = make_manager(primary)

        assert manager.translate_batch(["a", "b"]) == ["", ""]


class TestPersistentCache:
    def test_cache_survives_across_manager_instances(self, tmp_path):
        cache_file = tmp_path / "translations.json"

        first = StubBackend("primary", 90, result="T")
        manager_a = TranslationManager(backends=[first], cache_path=cache_file)
        manager_a.initialize()
        assert manager_a.translate("这是一个句子。") == "T"
        manager_a.cleanup()
        assert cache_file.exists()

        second = StubBackend("primary", 90, result="DIFFERENT")
        manager_b = TranslationManager(backends=[second], cache_path=cache_file)
        manager_b.initialize()
        # Served from the persistent cache; the backend is never called.
        assert manager_b.translate("这是一个句子。") == "T"
        assert second.calls == 0

    def test_cache_is_keyed_by_backend_name(self, tmp_path):
        cache_file = tmp_path / "translations.json"

        old = StubBackend("old-backend", 90, result="old output")
        manager_a = TranslationManager(backends=[old], cache_path=cache_file)
        manager_a.initialize()
        manager_a.translate("这是一个句子。")
        manager_a.cleanup()

        # A different (better) backend must re-translate, not serve stale output.
        new = StubBackend("new-backend", 95, result="new output")
        manager_b = TranslationManager(backends=[new], cache_path=cache_file)
        manager_b.initialize()
        assert manager_b.translate("这是一个句子。") == "new output"
        assert new.calls == 1

    def test_no_cache_file_written_without_cache_path(self, tmp_path):
        primary = StubBackend("primary", 90, result="T")
        manager = make_manager(primary)
        manager.translate("这是一个句子。")
        manager.cleanup()  # must not raise or write anywhere

    def test_corrupt_cache_file_is_ignored(self, tmp_path):
        cache_file = tmp_path / "translations.json"
        cache_file.write_text("{not json", encoding="utf-8")

        primary = StubBackend("primary", 90, result="T")
        manager = TranslationManager(backends=[primary], cache_path=cache_file)
        manager.initialize()
        assert manager.translate("这是一个句子。") == "T"


class TestConfigWiring:
    def test_preferred_backend_overrides_quality_order(self):
        high = StubBackend("shiny-neural", 90, result="high")
        low = StubBackend("plain-dict", 40, result="low")
        manager = TranslationManager(
            backends=[high, low], config={"preferred_backend": "plaindict"}
        )
        manager.initialize()

        assert manager.active_backend is low
        assert manager.translate("这是一个句子。") == "low"

    def test_unknown_preferred_backend_falls_back_to_quality_order(self):
        high = StubBackend("shiny-neural", 90, result="high")
        low = StubBackend("plain-dict", 40, result="low")
        manager = TranslationManager(
            backends=[high, low], config={"preferred_backend": "nonexistent"}
        )
        manager.initialize()

        assert manager.active_backend is high

    def test_config_reaches_default_backends(self):
        """Regression: main.py used to construct the manager without config,
        so documented YAML keys like nllb_model_repo never reached backends."""
        manager = TranslationManager(
            config={
                "nllb_model_repo": "custom/nllb-repo",
                "hymt_model_repo": "custom/hymt-repo",
            }
        )
        nllb = next(b for b in manager.backends if "NLLB" in b.get_name())
        hymt = next(b for b in manager.backends if "HY-MT" in b.get_name())
        assert nllb.model_repo == "custom/nllb-repo"
        assert hymt.model_repo == "custom/hymt-repo"
