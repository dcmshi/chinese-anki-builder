"""Tests for CEDICT word-by-word translation and its backend wrapper."""

import pytest

from process.cedict_loader import DictEntry
from process.sentence_translator import improve_translation, translate_sentence
from translate.cedict_backend import CEDICTBackend


def entry(simplified, pinyin, *definitions):
    return DictEntry(simplified, simplified, pinyin, list(definitions))


CEDICT = {
    "我": entry("我", "wo3", "I", "me"),
    "喜欢": entry("喜欢", "xi3 huan5", "to like", "to be fond of"),
    "中文": entry("中文", "Zhong1 wen2", "Chinese language"),
    "你": entry("你", "ni3", "you"),
    "好": entry("好", "hao3", "good"),
}


class TestTranslateSentence:
    def test_word_by_word_translation(self):
        result = translate_sentence("我喜欢中文", CEDICT)
        # "to " prefix is stripped from verbs
        assert result == "I like Chinese language"

    def test_particles_are_dropped(self):
        result = translate_sentence("我喜欢中文了", CEDICT)
        assert "了" not in result

    def test_question_particle_becomes_question_mark(self):
        result = translate_sentence("你好吗", CEDICT)
        assert "?" in result

    def test_unknown_word_passes_through(self):
        result = translate_sentence("罗辑喜欢中文", CEDICT)
        # Likely a name: kept in Chinese rather than dropped
        assert "罗" in result and "辑" in result

    def test_empty_sentence(self):
        assert translate_sentence("", CEDICT) == ""


class TestImproveTranslation:
    def test_capitalizes_and_terminates(self):
        assert improve_translation("like Chinese") == "Like Chinese."

    def test_collapses_spaces(self):
        assert "  " not in improve_translation("I  like   Chinese")

    def test_keeps_existing_terminal_punctuation(self):
        assert improve_translation("really?").endswith("?")


class TestCEDICTBackend:
    def test_returns_empty_without_cedict(self):
        backend = CEDICTBackend()
        backend.initialize()
        assert backend.translate("我喜欢中文") == ""

    def test_translates_with_cedict(self):
        backend = CEDICTBackend()
        backend.initialize()
        backend.set_cedict(CEDICT)

        result = backend.translate("我喜欢中文")

        assert result  # non-empty
        assert "like" in result.lower()

    def test_metadata(self):
        backend = CEDICTBackend()
        assert backend.is_available() is True
        assert backend.requires_internet() is False
        assert backend.get_quality_score() == 40
