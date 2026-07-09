"""Tests for CLI/config plumbing in main.py."""

import pytest

from main import load_config


class TestLoadConfig:
    def test_explicit_missing_config_raises(self, tmp_path):
        """Regression: a --config path that didn't exist was silently
        ignored and ./config.yaml used instead."""
        with pytest.raises(FileNotFoundError):
            load_config(str(tmp_path / "nope.yaml"))

    def test_explicit_config_is_loaded(self, tmp_path):
        cfg = tmp_path / "custom.yaml"
        cfg.write_text("top_words: 42\nmin_freq: 7\n", encoding="utf-8")

        config = load_config(str(cfg))

        assert config == {"top_words": 42, "min_freq": 7}

    def test_empty_config_file_gives_empty_dict(self, tmp_path):
        cfg = tmp_path / "empty.yaml"
        cfg.write_text("", encoding="utf-8")

        assert load_config(str(cfg)) == {}
