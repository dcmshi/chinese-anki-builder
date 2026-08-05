"""Tests for CLI/config plumbing in main.py."""

import json

import pytest

from main import load_config, main, normalize_hsk_levels, resolve_setting
from utils.file_utils import sanitize_filename, write_stats_json


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

    def test_config_with_bom_is_readable(self, tmp_path):
        """Regression: a config saved by Windows Notepad carries a BOM, which
        yaml.safe_load rejects with a cryptic scanner error."""
        cfg = tmp_path / "bom.yaml"
        cfg.write_text("top_words: 42\n", encoding="utf-8-sig")

        assert load_config(str(cfg)) == {"top_words": 42}


class TestNormalizeHskLevels:
    """Regression: an hsk_levels value from config.yaml reached filter_by_hsk
    unvalidated -- a scalar raised a raw TypeError deep in the pipeline."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, []),
            ([], []),
            (3, [1, 2, 3]),  # scalar reads like --hsk 3: everything up to 3
            ("2-4", [2, 3, 4]),
            ("1,3", [1, 3]),
            ([3], [3]),  # an explicit list means exactly those levels
            ([1, 3, 7], [1, 3, 7]),
        ],
    )
    def test_accepted_forms(self, value, expected):
        assert normalize_hsk_levels(value) == expected

    @pytest.mark.parametrize("value", [8, "abc", [0], [9], ["3"], {"level": 3}])
    def test_invalid_values_raise_value_error(self, value):
        with pytest.raises(ValueError):
            normalize_hsk_levels(value)

    def test_bad_config_value_prints_error_not_traceback(self, monkeypatch, capsys, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("hsk_levels: 99\n", encoding="utf-8")
        monkeypatch.setattr("sys.argv", ["main.py", "--input", "x.epub", "--config", str(cfg)])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "ERROR: Invalid HSK level" in err
        assert "Traceback" not in err


class TestNegatableBooleanFlags:
    """Regression: --cloze/--tts/--tts-sentences were store_true, so a
    `cloze: true` in config.yaml could not be switched off for one run."""

    def _resolved_params(self, monkeypatch, argv, config):
        captured = {}
        monkeypatch.setattr("sys.argv", ["main.py"] + argv)
        monkeypatch.setattr("main.load_config", lambda path=None: config)
        monkeypatch.setattr("main.process_pipeline", lambda **kwargs: captured.update(kwargs))
        main()
        return captured

    def test_no_flag_overrides_config_true(self, monkeypatch):
        params = self._resolved_params(
            monkeypatch,
            ["--input", "x.epub", "--no-cloze", "--no-tts", "--no-tts-sentences"],
            {"cloze": True, "enable_tts": True, "enable_sentence_tts": True},
        )

        assert params["cloze"] is False
        assert params["enable_tts"] is False
        assert params["enable_sentence_tts"] is False

    def test_flag_still_enables(self, monkeypatch):
        params = self._resolved_params(monkeypatch, ["--input", "x.epub", "--cloze", "--tts"], {})

        assert params["cloze"] is True
        assert params["enable_tts"] is True

    def test_config_value_used_when_flag_absent(self, monkeypatch):
        params = self._resolved_params(monkeypatch, ["--input", "x.epub"], {"cloze": True})

        assert params["cloze"] is True


class TestCliErrorHandling:
    """Regression: user-input errors (bad --config path, bad --hsk spec)
    used to escape main()'s error handler and dump raw tracebacks."""

    def _run_cli(self, monkeypatch, capsys, argv):
        monkeypatch.setattr("sys.argv", ["main.py"] + argv)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        return capsys.readouterr().err

    def test_missing_config_prints_error_not_traceback(self, monkeypatch, capsys):
        err = self._run_cli(monkeypatch, capsys, ["--input", "x.epub", "--config", "nope.yaml"])
        assert "ERROR: Config file not found" in err
        assert "Traceback" not in err

    def test_bad_hsk_spec_prints_error_not_traceback(self, monkeypatch, capsys):
        err = self._run_cli(monkeypatch, capsys, ["--input", "x.epub", "--hsk", "abc"])
        assert "ERROR: Invalid HSK level spec" in err
        assert "Traceback" not in err


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


class TestSanitizeFilename:
    """Regression: the deck name was used verbatim as the .apkg filename --
    'A/B' nested a directory and ':' crashed on Windows."""

    def test_replaces_separators_and_forbidden_chars(self):
        assert sanitize_filename("A/B") == "A_B"
        assert sanitize_filename("Deck: Test?") == "Deck_ Test_"
        assert sanitize_filename('a\\b<c>d"e|f*g') == "a_b_c_d_e_f_g"

    def test_strips_trailing_dots_and_spaces(self):
        # Trailing dots/spaces are silently dropped by Windows.
        assert sanitize_filename("deck. ") == "deck"

    def test_chinese_names_untouched(self):
        assert sanitize_filename("三体全集 - 90% Coverage") == "三体全集 - 90% Coverage"

    def test_empty_result_falls_back(self):
        assert sanitize_filename("") == "deck"
        assert sanitize_filename("...") == "deck"
        assert sanitize_filename("   ") == "deck"


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
