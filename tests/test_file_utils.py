"""Tests for file utilities: atomic cache writes.

The regression net for the class of bug where an interrupted write left a
truncated cache file (dictionary, HSK list, MP3, translation cache) that every
later run then trusted forever.
"""

import os

import pytest

from utils.file_utils import (
    atomic_output_path,
    atomic_write_bytes,
    atomic_write_text,
    write_stats_json,
)


class TestAtomicWrites:
    def test_writes_bytes_and_text(self, tmp_path):
        target = tmp_path / "nested" / "file.bin"

        atomic_write_bytes(target, b"payload")
        assert target.read_bytes() == b"payload"

        atomic_write_text(target, "文本")
        assert target.read_text(encoding="utf-8") == "文本"

    def test_failed_write_leaves_previous_content_intact(self, tmp_path):
        target = tmp_path / "cache.json"
        atomic_write_text(target, "good content")

        with pytest.raises(RuntimeError):
            with atomic_output_path(target) as tmp:
                tmp.write_text("half-written", encoding="utf-8")
                raise RuntimeError("interrupted mid-write")

        # The old file is still whole -- not truncated, not replaced.
        assert target.read_text(encoding="utf-8") == "good content"

    def test_failed_write_leaves_no_temp_files_behind(self, tmp_path):
        target = tmp_path / "cache.json"

        with pytest.raises(ValueError):
            with atomic_output_path(target):
                raise ValueError("boom")

        assert list(tmp_path.iterdir()) == []

    def test_temp_file_is_a_sibling(self, tmp_path):
        """os.replace() is only atomic within one filesystem, so the temp file
        must live in the destination directory."""
        target = tmp_path / "sub" / "file.txt"
        seen = []

        with atomic_output_path(target) as tmp:
            seen.append(tmp.parent)
            tmp.write_text("x", encoding="utf-8")

        assert seen == [target.parent]

    def test_stats_json_is_written_atomically(self, tmp_path, monkeypatch):
        target = tmp_path / "stats.json"
        write_stats_json(target, {"cards_created": 1})

        def _explode(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(os, "replace", _explode)
        with pytest.raises(OSError):
            write_stats_json(target, {"cards_created": 2})

        assert '"cards_created": 1' in target.read_text(encoding="utf-8")
