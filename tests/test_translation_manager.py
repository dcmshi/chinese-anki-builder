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
