"""Tests for the Argos Translate backend initialization behavior."""

import pytest

from translate.argos_backend import ArgosTranslateBackend


class FakeZhEnPackage:
    from_code = "zh"
    to_code = "en"


def test_initialize_skips_index_update_when_model_cached(monkeypatch):
    """Regression: initialize() used to call update_package_index() (a
    network request) before checking for an installed model, so cached and
    offline runs still depended on the network."""
    pkg_mod = pytest.importorskip("argostranslate.package")
    tr_mod = pytest.importorskip("argostranslate.translate")

    monkeypatch.setattr(pkg_mod, "get_installed_packages", lambda: [FakeZhEnPackage()])
    monkeypatch.setattr(tr_mod, "get_installed_languages", lambda: ["zh", "en"])

    def _network_call(*args, **kwargs):
        raise AssertionError("update_package_index() must not run with a cached model")

    monkeypatch.setattr(pkg_mod, "update_package_index", _network_call)
    monkeypatch.setattr(pkg_mod, "get_available_packages", _network_call)

    backend = ArgosTranslateBackend()

    assert backend.initialize() is True
    assert backend.is_initialized()
    assert backend.installed_languages == ["zh", "en"]
