"""Tests for the static HTML card preview (--preview)."""

from anki.preview import export_cards_to_html
from process.cedict_loader import DictEntry
from process.word_selector import WordCard

FAKE_CEDICT = {
    "你好": DictEntry("你好", "你好", "ni3 hao3", ["hello"]),
    "世界": DictEntry("世界", "世界", "shi4 jie4", ["world"]),
}


def make_cards():
    return [
        WordCard(
            word="你好",
            sentence="你好，这个世界很大。",
            frequency=5,
            chapter="第一章",
            sentence_translation="Hello, this world is big.",
            sentence_pinyin="nǐ hǎo, zhè ge shì jiè hěn dà.",
        ),
        WordCard(
            word="世界",
            sentence="这个世界非常有趣。",
            frequency=3,
            chapter="第二章",
            sentence_translation="This world is very interesting.",
            sentence_pinyin="zhè ge shì jiè fēi cháng yǒu qù.",
        ),
    ]


class TestPreviewExport:
    def test_writes_self_contained_html(self, tmp_path):
        path = export_cards_to_html(
            make_cards(), tmp_path / "preview.html", cedict=FAKE_CEDICT, deck_name="My Deck"
        )
        content = path.read_text(encoding="utf-8")

        assert content.startswith("<!DOCTYPE html>")
        assert "My Deck" in content
        assert "2 cards" in content
        # No external assets: everything inline
        assert "http://" not in content and "https://" not in content
        assert "<style>" in content

    def test_renders_card_content(self, tmp_path):
        path = export_cards_to_html(make_cards(), tmp_path / "p.html", cedict=FAKE_CEDICT)
        content = path.read_text(encoding="utf-8")

        # Highlighted word inside the sentence, plus resolved back fields
        assert '<span class="target">你好</span>' in content
        assert "hello" in content  # definition from CEDICT
        assert "Hello, this world is big." in content
        assert "第一章" in content

    def test_cloze_preview_blanks_the_word_on_front(self, tmp_path):
        path = export_cards_to_html(
            make_cards(), tmp_path / "p.html", cedict=FAKE_CEDICT, cloze=True
        )
        content = path.read_text(encoding="utf-8")

        assert '<span class="cloze">[...]</span>' in content  # front blank
        assert '<span class="cloze">你好</span>' in content  # back reveal
        assert "{{c1::" not in content  # raw cloze markup never leaks

    def test_html_in_fields_is_escaped(self, tmp_path):
        card = WordCard(
            word="你好",
            sentence="你好<b>这里</b>。",
            frequency=1,
            sentence_translation='<script>alert("x")</script>',
        )
        path = export_cards_to_html([card], tmp_path / "p.html", cedict=FAKE_CEDICT)
        content = path.read_text(encoding="utf-8")

        assert "<script>" not in content
        assert "<b>" not in content

    def test_reviewer_overrides_shown(self, tmp_path):
        card = make_cards()[0]
        card.definition = "greeting (fixed sense)"
        card.word_pinyin = "nǐ hǎo!"
        path = export_cards_to_html([card], tmp_path / "p.html", cedict=FAKE_CEDICT)
        content = path.read_text(encoding="utf-8")

        assert "greeting (fixed sense)" in content
        assert "nǐ hǎo!" in content
