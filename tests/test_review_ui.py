"""Tests for the editable review page (--review-ui), Python side."""

import json
import re

from anki.review_ui import export_cards_to_review_ui
from process.cedict_loader import DictEntry
from process.review import REVIEW_COLUMNS
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


def extract_payload(content):
    """Pull the embedded JSON model back out of a generated page."""
    match = re.search(
        r'<script type="application/json" id="cards-data">(.*?)</script>',
        content,
        re.DOTALL,
    )
    assert match, "page has no cards-data payload"
    return json.loads(match.group(1))


class TestReviewUiExport:
    def test_writes_self_contained_html(self, tmp_path):
        path = export_cards_to_review_ui(
            make_cards(), tmp_path / "r.html", cedict=FAKE_CEDICT, deck_name="My Deck"
        )
        content = path.read_text(encoding="utf-8")

        assert content.startswith("<!DOCTYPE html>")
        assert "My Deck" in content
        assert "http://" not in content and "https://" not in content

    def test_payload_has_one_entry_per_card_with_review_columns(self, tmp_path):
        path = export_cards_to_review_ui(make_cards(), tmp_path / "r.html", cedict=FAKE_CEDICT)
        payload = extract_payload(path.read_text(encoding="utf-8"))

        assert len(payload) == 2
        for row in payload:
            assert set(row.keys()) == set(REVIEW_COLUMNS)

    def test_payload_carries_resolved_values(self, tmp_path):
        path = export_cards_to_review_ui(make_cards(), tmp_path / "r.html", cedict=FAKE_CEDICT)
        payload = extract_payload(path.read_text(encoding="utf-8"))

        assert payload[0]["word"] == "你好"
        assert payload[0]["frequency"] == 5
        assert payload[0]["definition"] == "hello"
        assert payload[0]["chapter"] == "第一章"
        assert payload[0]["sentence"] == "你好，这个世界很大。"

    def test_payload_has_no_dropped_or_edited_state(self, tmp_path):
        """A fresh export is clean; drop/edit flags are runtime-only."""
        path = export_cards_to_review_ui(make_cards(), tmp_path / "r.html", cedict=FAKE_CEDICT)
        payload = extract_payload(path.read_text(encoding="utf-8"))

        for row in payload:
            assert not any(key.startswith("_") for key in row)

    def test_script_close_tag_cannot_break_the_page(self, tmp_path):
        """A book containing </script> must not terminate the payload."""
        card = WordCard(
            word="你好",
            sentence="你好</script><script>alert(1)</script>",
            frequency=1,
        )
        path = export_cards_to_review_ui([card], tmp_path / "r.html", cedict=FAKE_CEDICT)
        content = path.read_text(encoding="utf-8")

        # The payload survives parsing, with the text intact
        payload = extract_payload(content)
        assert payload[0]["sentence"] == "你好</script><script>alert(1)</script>"
        # and no raw < leaked into the JSON block
        block = re.search(r'id="cards-data">(.*?)</script>', content, re.DOTALL).group(1)
        assert "<" not in block

    def test_rendered_fields_are_html_escaped(self, tmp_path):
        card = WordCard(
            word="你好",
            sentence="你好<b>这里</b>。",
            frequency=1,
            sentence_translation='<img src=x onerror="alert(1)">',
        )
        path = export_cards_to_review_ui([card], tmp_path / "r.html", cedict=FAKE_CEDICT)
        content = path.read_text(encoding="utf-8")

        assert "<b>" not in content
        assert "<img" not in content

    def test_cloze_mode_blanks_the_front(self, tmp_path):
        path = export_cards_to_review_ui(
            make_cards(), tmp_path / "r.html", cedict=FAKE_CEDICT, cloze=True
        )
        content = path.read_text(encoding="utf-8")

        assert '<span class="cloze">[...]</span>' in content
        assert "{{c1::" not in content
        assert 'data-cloze="true"' in content

    def test_csv_name_derives_from_html_stem(self, tmp_path):
        path = export_cards_to_review_ui(make_cards(), tmp_path / "mydeck.html", cedict=FAKE_CEDICT)
        assert 'data-csv-name="mydeck.csv"' in path.read_text(encoding="utf-8")

    def test_every_card_has_editable_hooks(self, tmp_path):
        path = export_cards_to_review_ui(make_cards(), tmp_path / "r.html", cedict=FAKE_CEDICT)
        content = path.read_text(encoding="utf-8")

        assert 'data-card="0"' in content
        assert 'data-field="definition"' in content
        assert 'data-field="sentence"' in content
        assert 'id="download"' in content
        assert 'id="filter"' in content
