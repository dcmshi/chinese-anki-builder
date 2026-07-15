"""Tests for example-sentence TTS audio (--tts-sentences)."""

from pathlib import Path

import main as main_module
from anki.deck_builder import create_anki_note, create_cloze_note
from anki.templates import get_chinese_model, get_chinese_cloze_model
from process.cedict_loader import DictEntry
from process.word_selector import WordCard

FAKE_CEDICT = {
    "你好": DictEntry("你好", "你好", "ni3 hao3", ["hello"]),
}


def make_card(**overrides):
    defaults = dict(word="你好", sentence="你好，世界很大。", frequency=5)
    defaults.update(overrides)
    return WordCard(**defaults)


class TestModels:
    def test_both_models_have_sentence_audio_last(self):
        """Appended last so pre-existing decks reimport with fields aligned."""
        for model in (get_chinese_model(), get_chinese_cloze_model()):
            assert model.fields[-1]["name"] == "SentenceAudio"

    def test_field_count_matches_note_fields(self):
        card = make_card()
        note = create_anki_note(card, FAKE_CEDICT, get_chinese_model())
        assert len(note.fields) == len(get_chinese_model().fields)
        cloze = create_cloze_note(card, FAKE_CEDICT, get_chinese_cloze_model())
        assert len(cloze.fields) == len(get_chinese_cloze_model().fields)


class TestNoteFields:
    def test_sentence_audio_reference_on_regular_note(self):
        card = make_card(sentence_audio_filename="zh_abc.mp3")
        note = create_anki_note(card, FAKE_CEDICT, get_chinese_model())
        assert note.fields[-1] == "[sound:zh_abc.mp3]"

    def test_sentence_audio_reference_on_cloze_note(self):
        card = make_card(sentence_audio_filename="zh_abc.mp3")
        note = create_cloze_note(card, FAKE_CEDICT, get_chinese_cloze_model())
        assert note.fields[-1] == "[sound:zh_abc.mp3]"

    def test_empty_when_no_sentence_audio(self):
        note = create_anki_note(make_card(), FAKE_CEDICT, get_chinese_model())
        assert note.fields[-1] == ""


class TestGenerateAudioFiles:
    def _patch_tts(self, monkeypatch, tmp_path, fail_for=()):
        """Route gTTS to a fake that just creates files, tracking requests."""
        requests = []

        def fake_get_or_create(text, cache_dir=None):
            requests.append(text)
            if text in fail_for:
                return None
            path = tmp_path / f"zh_{abs(hash(text))}.mp3"
            path.write_bytes(b"mp3")
            return path

        import tts.gtts_generator as gen

        monkeypatch.setattr(gen, "get_or_create_audio", fake_get_or_create)
        monkeypatch.setattr(gen, "is_available", lambda: True)
        return requests

    def test_words_and_sentences_generated(self, monkeypatch, tmp_path):
        requests = self._patch_tts(monkeypatch, tmp_path)
        cards = [make_card(), make_card(word="世界", sentence="世界真奇妙。")]

        media = main_module.generate_audio_files(cards, words=True, sentences=True)

        assert len(media) == 4  # 2 words + 2 distinct sentences
        assert all(card.audio_filename for card in cards)
        assert all(card.sentence_audio_filename for card in cards)
        assert set(requests) == {"你好", "世界", "你好，世界很大。", "世界真奇妙。"}

    def test_sentences_only(self, monkeypatch, tmp_path):
        self._patch_tts(monkeypatch, tmp_path)
        cards = [make_card()]

        media = main_module.generate_audio_files(cards, words=False, sentences=True)

        assert len(media) == 1
        assert cards[0].audio_filename == ""
        assert cards[0].sentence_audio_filename != ""

    def test_shared_sentence_media_deduplicated(self, monkeypatch, tmp_path):
        self._patch_tts(monkeypatch, tmp_path)
        shared = "你好，世界很大。"
        cards = [make_card(), make_card(word="世界", sentence=shared)]

        media = main_module.generate_audio_files(cards, words=False, sentences=True)

        assert len(media) == 1  # same sentence -> one media file
        assert Path(media[0]).exists()

    def test_failures_leave_card_without_audio(self, monkeypatch, tmp_path):
        self._patch_tts(monkeypatch, tmp_path, fail_for={"你好，世界很大。"})
        cards = [make_card()]

        media = main_module.generate_audio_files(cards, words=True, sentences=True)

        assert cards[0].audio_filename != ""  # word audio still landed
        assert cards[0].sentence_audio_filename == ""
        assert len(media) == 1
