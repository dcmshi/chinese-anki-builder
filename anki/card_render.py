"""Shared card appearance for the HTML preview and the editable review UI.

Both anki/preview.py (read-only) and anki/review_ui.py (editable) render the
same cards with the same styling, which has to stay in step with the real
card CSS in anki/templates.py. Keeping that in one place stops the two pages
from drifting apart -- the preview's whole value is that it matches what
Anki will show.
"""

import html
from dataclasses import dataclass
from typing import Dict, Optional

from anki.deck_builder import (
    cloze_sentence,
    highlight_word_in_sentence,
    resolve_definition,
    resolve_word_pinyin,
)
from process.cedict_loader import DictEntry
from process.word_selector import WordCard

# Mirrors the card CSS in anki/templates.py, plus page scaffolding. Kept
# inline so generated pages are fully self-contained.
PAGE_CSS = """
body {
    font-family: "Noto Sans CJK SC", "Microsoft YaHei", SimHei, sans-serif;
    background-color: #1e1e1e;
    color: #d0d0d0;
    margin: 0;
    padding: 24px;
}
h1 { font-size: 22px; color: #e8e8e8; }
.summary { color: #888; margin-bottom: 24px; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 16px; }
.card {
    background-color: #2b2b2b;
    border: 1px solid #444;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}
.side-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #777;
    text-align: left;
    margin-bottom: 6px;
}
.front { border-bottom: 1px dashed #555; padding-bottom: 12px; margin-bottom: 12px; }
.sentence { font-size: 24px; line-height: 1.6; color: #e8e8e8; margin-bottom: 8px; }
.sentence-pinyin { font-size: 15px; color: #b8b8b8; font-style: italic; margin-bottom: 10px; }
.word-highlight { font-size: 26px; font-weight: bold; color: #ff6b6b; margin: 10px 0; }
.target, .cloze { color: #ff6b6b; font-weight: bold; }
.pinyin { font-size: 17px; color: #a8a8a8; font-style: italic; margin: 6px 0; }
.definition { font-size: 15px; color: #d0d0d0; margin: 10px 0; line-height: 1.4; }
.sentence-translation {
    font-size: 14px;
    color: #c0c0c0;
    margin: 10px 0;
    padding: 8px;
    background-color: #3a3a3a;
    border-left: 3px solid #ff6b6b;
    font-style: italic;
    text-align: left;
}
.meta { font-size: 12px; color: #777; margin-top: 10px; font-style: italic; }
"""


def cloze_front(word: str, sentence: str) -> str:
    """Cloze front the way Anki shows it: the word becomes [...]."""
    marked = cloze_sentence(word, sentence)
    return marked.replace("{{c1::" + html.escape(word) + "}}", '<span class="cloze">[...]</span>')


def cloze_back(word: str, sentence: str) -> str:
    """Cloze back: the word revealed in highlight color."""
    marked = cloze_sentence(word, sentence)
    escaped = html.escape(word)
    return marked.replace("{{c1::" + escaped + "}}", f'<span class="cloze">{escaped}</span>')


@dataclass
class CardFaces:
    """Resolved card content, ready to render.

    The two sentence fields are HTML (they carry highlight or cloze markup
    and are already escaped). Every other field is raw text -- consumers
    escape for their own context, since the preview needs HTML escaping and
    the review UI needs JSON escaping.
    """

    front_sentence: str
    back_sentence: str
    word_pinyin: str
    definition: str
    translation: str
    sentence_pinyin: str
    chapter: str


def resolve_faces(
    card: WordCard,
    cedict: Optional[Dict[str, DictEntry]],
    cloze: bool = False,
) -> CardFaces:
    """
    Resolve one card into its display values.

    Args:
        card: The card to render
        cedict: Optional CC-CEDICT dictionary for pinyin/definition lookup
        cloze: Render a cloze front ([...] blank) instead of a highlight

    Returns:
        CardFaces with sentence fields as HTML and the rest as raw text
    """
    if cloze:
        front = cloze_front(card.word, card.sentence)
        back = cloze_back(card.word, card.sentence)
    else:
        front = highlight_word_in_sentence(card.word, card.sentence)
        back = front

    return CardFaces(
        front_sentence=front,
        back_sentence=back,
        word_pinyin=resolve_word_pinyin(card, cedict),
        definition=resolve_definition(card, cedict),
        translation=card.sentence_translation or "",
        sentence_pinyin=card.sentence_pinyin or "",
        chapter=card.chapter or "",
    )
