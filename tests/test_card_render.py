"""Tests for shared card appearance (anki/card_render.py)."""

from anki.card_render import PAGE_CSS, CardFaces, cloze_back, cloze_front, resolve_faces
from process.cedict_loader import DictEntry
from process.word_selector import WordCard

FAKE_CEDICT = {
    "你好": DictEntry("你好", "你好", "ni3 hao3", ["hello"]),
}


class TestClozeHelpers:
    def test_front_blanks_the_word(self):
        assert cloze_front("你好", "你好世界") == '<span class="cloze">[...]</span>世界'

    def test_back_reveals_the_word(self):
        assert cloze_back("你好", "你好世界") == '<span class="cloze">你好</span>世界'


class TestResolveFaces:
    def test_regular_mode_highlights_word_on_both_faces(self):
        card = WordCard(word="你好", sentence="你好世界", frequency=3)
        faces = resolve_faces(card, FAKE_CEDICT)

        assert faces.front_sentence == '<span class="target">你好</span>世界'
        assert faces.back_sentence == faces.front_sentence

    def test_cloze_mode_blanks_front_only(self):
        card = WordCard(word="你好", sentence="你好世界", frequency=3)
        faces = resolve_faces(card, FAKE_CEDICT, cloze=True)

        assert "[...]" in faces.front_sentence
        assert "[...]" not in faces.back_sentence

    def test_text_fields_are_raw_not_escaped(self):
        """Consumers escape for their own context, so faces stay unescaped."""
        card = WordCard(
            word="你好",
            sentence="你好世界",
            frequency=1,
            sentence_translation="a & b",
            definition="<tag>",
        )
        faces = resolve_faces(card, FAKE_CEDICT)

        assert faces.translation == "a & b"
        assert faces.definition == "<tag>"

    def test_reviewer_overrides_win(self):
        card = WordCard(
            word="你好",
            sentence="你好世界",
            frequency=1,
            word_pinyin="custom pinyin",
            definition="custom definition",
        )
        faces = resolve_faces(card, FAKE_CEDICT)

        assert faces.word_pinyin == "custom pinyin"
        assert faces.definition == "custom definition"

    def test_falls_back_to_cedict(self):
        card = WordCard(word="你好", sentence="你好世界", frequency=1)
        faces = resolve_faces(card, FAKE_CEDICT)

        assert faces.definition == "hello"
        assert faces.word_pinyin  # tone-mark pinyin resolved from CEDICT

    def test_returns_cardfaces_instance(self):
        card = WordCard(word="你好", sentence="你好世界", frequency=1)
        assert isinstance(resolve_faces(card, FAKE_CEDICT), CardFaces)

    def test_page_css_is_non_empty(self):
        assert ".card" in PAGE_CSS
