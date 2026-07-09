"""Tests for TTS audio generation (no network, no gtts install required)."""

import pytest

import tts.gtts_generator as gtts_generator
from tts.gtts_generator import (
    generate_audio,
    get_audio_filename,
    get_or_create_audio,
)
from anki.deck_builder import create_anki_note
from anki.templates import get_chinese_model
from process.cedict_loader import DictEntry
from process.word_selector import WordCard


class FakeGTTS:
    """Stands in for gtts.gTTS; writes a marker file instead of calling out."""

    instances = 0

    def __init__(self, text, lang="zh-CN"):
        FakeGTTS.instances += 1
        self.text = text
        self.lang = lang

    def save(self, path):
        with open(path, "wb") as f:
            f.write(b"fake mp3 bytes")


@pytest.fixture(autouse=True)
def _reset_fake_counter():
    FakeGTTS.instances = 0


class TestAudioFilename:
    def test_deterministic_mp3_name(self):
        name = get_audio_filename("你好")
        assert name == get_audio_filename("你好")
        assert name.endswith(".mp3")

    def test_different_text_different_name(self):
        assert get_audio_filename("你好") != get_audio_filename("世界")


class TestGenerateAudio:
    def test_writes_file_with_fake_gtts(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gtts_generator, "_load_gtts", lambda: FakeGTTS)
        out = tmp_path / "audio" / "hello.mp3"

        assert generate_audio("你好", out) is True
        assert out.read_bytes() == b"fake mp3 bytes"

    def test_returns_false_when_gtts_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gtts_generator, "_load_gtts", lambda: None)

        assert generate_audio("你好", tmp_path / "x.mp3") is False
        assert not (tmp_path / "x.mp3").exists()

    def test_returns_false_when_gtts_raises(self, tmp_path, monkeypatch):
        class ExplodingGTTS:
            def __init__(self, text, lang="zh-CN"):
                pass

            def save(self, path):
                raise ConnectionError("no internet")

        monkeypatch.setattr(gtts_generator, "_load_gtts", lambda: ExplodingGTTS)

        assert generate_audio("你好", tmp_path / "x.mp3") is False


class TestGetOrCreateAudio:
    def test_generates_then_caches(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gtts_generator, "_load_gtts", lambda: FakeGTTS)

        first = get_or_create_audio("你好", cache_dir=tmp_path)
        second = get_or_create_audio("你好", cache_dir=tmp_path)

        assert first == second
        assert first.exists()
        # Second call must hit the cache, not regenerate.
        assert FakeGTTS.instances == 1

    def test_returns_none_on_failure(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gtts_generator, "_load_gtts", lambda: None)

        assert get_or_create_audio("你好", cache_dir=tmp_path) is None


class TestAudioOnNotes:
    def test_note_references_audio_file(self):
        card = WordCard(
            word="你好",
            sentence="你好世界",
            frequency=10,
            audio_filename="zh_abc123.mp3",
        )
        cedict = {"你好": DictEntry("你好", "你好", "ni3 hao3", ["hello"])}

        note = create_anki_note(card, cedict, get_chinese_model())

        assert note.fields[6] == "[sound:zh_abc123.mp3]"

    def test_note_without_audio_has_empty_field(self):
        card = WordCard(word="你好", sentence="你好世界", frequency=10)
        cedict = {"你好": DictEntry("你好", "你好", "ni3 hao3", ["hello"])}

        note = create_anki_note(card, cedict, get_chinese_model())

        assert note.fields[6] == ""
