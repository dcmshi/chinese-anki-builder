"""Tests for HSK level filtering (offline via temp cache directories)."""

import pytest

import process.hsk_filter as hsk_filter
from process.hsk_filter import (
    _parse_hsk_words,
    filter_by_hsk,
    load_hsk_words,
    parse_hsk_levels,
)


def _seed_cache(cache_dir, level_key, words):
    (cache_dir / f"hsk_{level_key}.txt").write_text("\n".join(words), encoding="utf-8")


class TestParseHskLevels:
    @pytest.mark.parametrize(
        "spec,expected",
        [
            ("3", [1, 2, 3]),  # single level means "up to"
            ("1", [1]),
            ("2-4", [2, 3, 4]),
            ("1,3,5", [1, 3, 5]),
            ("7", [1, 2, 3, 4, 5, 6, 7]),
        ],
    )
    def test_valid_specs(self, spec, expected):
        assert parse_hsk_levels(spec) == expected

    @pytest.mark.parametrize("spec", ["0", "8", "abc", "1-9", "", "2,8"])
    def test_invalid_specs_raise(self, spec):
        with pytest.raises(ValueError):
            parse_hsk_levels(spec)


class TestParseHskWords:
    def test_one_word_per_line(self):
        assert _parse_hsk_words("爱\n吧\n爸爸\n") == {"爱", "吧", "爸爸"}

    def test_strips_homograph_markers(self):
        # The source lists disambiguate homographs as 本1 / 本2 etc.
        assert _parse_hsk_words("本1\n地2\n你好\n") == {"本", "地", "你好"}

    def test_ignores_blank_lines(self):
        assert _parse_hsk_words("爱\n\n  \n吧\n") == {"爱", "吧"}


class TestLoadAndFilter:
    def test_load_unions_levels_from_cache(self, tmp_path):
        _seed_cache(tmp_path, "1", ["爱", "爸爸"])
        _seed_cache(tmp_path, "2", ["帮助", "报纸"])

        words = load_hsk_words([1, 2], cache_dir=tmp_path)

        assert words == {"爱", "爸爸", "帮助", "报纸"}

    def test_filter_keeps_only_hsk_words_in_order(self, tmp_path):
        _seed_cache(tmp_path, "1", ["爸爸", "喜欢"])

        result = filter_by_hsk(["智子", "喜欢", "爸爸", "面壁"], [1], cache_dir=tmp_path)

        assert result == ["喜欢", "爸爸"]

    def test_empty_levels_is_a_no_op(self):
        words = ["任何", "词语"]
        assert filter_by_hsk(words, []) == words

    def test_invalid_level_raises(self, tmp_path):
        with pytest.raises(ValueError):
            load_hsk_words([9], cache_dir=tmp_path)

    def test_download_failure_raises_actionable_error(self, tmp_path, monkeypatch):
        def _no_network(*args, **kwargs):
            raise hsk_filter.requests.ConnectionError("offline")

        monkeypatch.setattr(hsk_filter.requests, "get", _no_network)

        with pytest.raises(RuntimeError, match="place a word list"):
            load_hsk_words([1], cache_dir=tmp_path)
