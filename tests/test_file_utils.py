"""Tests for file utilities: atomic writes, reserved names, data dir resolution.

The atomic-write tests are the regression net for the class of bug where an
interrupted write left a truncated cache file (dictionary, HSK list, MP3,
translation cache) that every later run then trusted forever.
"""

import os

import pytest

import utils.file_utils as file_utils
from utils.file_utils import (
    atomic_output_path,
    atomic_write_bytes,
    atomic_write_text,
    get_data_dir,
    sanitize_filename,
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


class TestSanitizeFilenameReservedNames:
    """Windows refuses to create CON/NUL/COM1... with or without extension."""

    @pytest.mark.parametrize("name", ["CON", "con", "PRN", "AUX", "NUL", "COM1", "LPT9"])
    def test_reserved_names_get_suffixed(self, name):
        assert sanitize_filename(name) == f"{name}_"

    def test_reserved_name_with_extension_is_handled(self):
        # Windows resolves the device from the text before the first dot.
        assert sanitize_filename("NUL.deck") == "NUL_.deck"

    @pytest.mark.parametrize("name", ["CONSOLE", "COM", "COM10", "NULL", "三体"])
    def test_similar_but_legal_names_untouched(self, name):
        assert sanitize_filename(name) == name


class TestGetDataDir:
    def test_env_override_wins(self, tmp_path, monkeypatch):
        override = tmp_path / "custom-data"
        monkeypatch.setenv("ANKI_CHINESE_DATA_DIR", str(override))

        assert get_data_dir() == override
        assert override.is_dir()

    def test_source_checkout_uses_repo_data_dir(self, monkeypatch):
        monkeypatch.delenv("ANKI_CHINESE_DATA_DIR", raising=False)
        repo_root = file_utils.Path(file_utils.__file__).parent.parent

        # This test suite always runs from the checkout, where pyproject.toml
        # sits next to the packages.
        assert (repo_root / "pyproject.toml").exists()
        assert get_data_dir() == repo_root / "data"

    def test_installed_copy_uses_per_user_dir(self, tmp_path, monkeypatch):
        """Regression: anchoring to the package put ~1GB of models inside
        site-packages, which may be read-only."""
        monkeypatch.delenv("ANKI_CHINESE_DATA_DIR", raising=False)
        fake_user_dir = tmp_path / "user-data"
        monkeypatch.setattr(file_utils, "_user_data_dir", lambda: fake_user_dir)
        # Pretend the package is installed (no pyproject.toml next to it).
        monkeypatch.setattr(file_utils, "__file__", str(tmp_path / "pkg" / "file_utils.py"))

        assert get_data_dir() == fake_user_dir
        assert fake_user_dir.is_dir()

    def test_falls_back_to_cwd_when_user_dir_unwritable(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANKI_CHINESE_DATA_DIR", raising=False)
        monkeypatch.setattr(file_utils, "__file__", str(tmp_path / "pkg" / "file_utils.py"))
        monkeypatch.setattr(file_utils, "_user_data_dir", lambda: tmp_path / "denied")

        real_ensure = file_utils.ensure_dir

        def _deny_user_dir(directory):
            if str(directory).endswith("denied"):
                raise OSError("read-only file system")
            return real_ensure(directory)

        monkeypatch.setattr(file_utils, "ensure_dir", _deny_user_dir)
        monkeypatch.chdir(tmp_path)

        assert get_data_dir() == file_utils.Path("data")
