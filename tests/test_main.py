"""Tests for CLI/config plumbing in main.py."""

import json

import pytest

from main import load_config, resolve_setting
from utils.file_utils import write_stats_json


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


class TestResolveSetting:
    """CLI > config.yaml > built-in default."""

    def test_cli_value_wins(self):
        assert resolve_setting(300, {"top_words": 150}, ["top_words"], 50) == 300

    def test_config_used_when_cli_absent(self):
        assert resolve_setting(None, {"top_words": 150}, ["top_words"], 50) == 150

    def test_default_when_neither_set(self):
        assert resolve_setting(None, {}, ["top_words"], 50) == 50

    def test_first_present_config_key_wins(self):
        config = {"min_frequency": 5}  # legacy key name
        assert resolve_setting(None, config, ["min_freq", "min_frequency"], 2) == 5

    def test_explicit_none_config_value_is_skipped(self):
        assert resolve_setting(None, {"stats_file": None}, ["stats_file"], "x") == "x"

    def test_false_cli_value_is_respected(self):
        # False is a real value (e.g. a negated flag), not "absent".
        assert resolve_setting(False, {"cloze": True}, ["cloze"], True) is False


class TestStatsExport:
    def test_write_stats_json_roundtrip(self, tmp_path):
        stats = {
            "deck_name": "三体",
            "cards_created": 2,
            "cards": [{"word": "你好", "frequency": 10, "chapter": "第一章"}],
        }
        path = tmp_path / "nested" / "stats.json"

        write_stats_json(path, stats)

        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded == stats
        # Chinese must be stored readably, not as \uXXXX escapes.
        assert "三体" in path.read_text(encoding="utf-8")
