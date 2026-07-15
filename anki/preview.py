"""Static HTML card preview for pre-import QC.

Renders every card the way Anki will show it (front above back, same dark
styling as the real card CSS) into one self-contained HTML file — no
external assets, no JavaScript — so a whole deck can be skimmed in a
browser before/alongside the CSV review step. Audio is not embedded; a
marker notes when a card will carry sound.
"""

import html
from pathlib import Path
from typing import Dict, List, Optional

from anki.deck_builder import (
    cloze_sentence,
    highlight_word_in_sentence,
    resolve_definition,
    resolve_word_pinyin,
)
from process.cedict_loader import DictEntry
from process.word_selector import WordCard

# Mirrors the card CSS in anki/templates.py, plus page scaffolding. Kept
# inline so the preview file is fully self-contained.
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


def _cloze_front(word: str, sentence: str) -> str:
    """Cloze front the way Anki shows it: the word becomes [...]."""
    marked = cloze_sentence(word, sentence)
    return marked.replace("{{c1::" + html.escape(word) + "}}", '<span class="cloze">[...]</span>')


def _cloze_back(word: str, sentence: str) -> str:
    """Cloze back: the word revealed in highlight color."""
    marked = cloze_sentence(word, sentence)
    escaped = html.escape(word)
    return marked.replace("{{c1::" + escaped + "}}", f'<span class="cloze">{escaped}</span>')


def _render_card(
    index: int,
    card: WordCard,
    cedict: Optional[Dict[str, DictEntry]],
    cloze: bool,
) -> str:
    pinyin = html.escape(resolve_word_pinyin(card, cedict))
    definition = html.escape(resolve_definition(card, cedict))
    translation = html.escape(card.sentence_translation or "")
    sentence_pinyin = html.escape(card.sentence_pinyin or "")
    chapter = html.escape(card.chapter or "")

    if cloze:
        front_sentence = _cloze_front(card.word, card.sentence)
        back_sentence = _cloze_back(card.word, card.sentence)
    else:
        front_sentence = highlight_word_in_sentence(card.word, card.sentence)
        back_sentence = front_sentence

    parts = [
        '<article class="card">',
        '<div class="front"><div class="side-label">Front</div>',
        f'<div class="sentence">{front_sentence}</div></div>',
        '<div class="back"><div class="side-label">Back</div>',
        f'<div class="sentence">{back_sentence}</div>',
    ]
    if sentence_pinyin:
        parts.append(f'<div class="sentence-pinyin">{sentence_pinyin}</div>')
    parts.append(f'<div class="word-highlight">{html.escape(card.word)}</div>')
    parts.append(f'<div class="pinyin">{pinyin}</div>')
    parts.append(f'<div class="definition">{definition}</div>')
    if translation:
        parts.append(f'<div class="sentence-translation">{translation}</div>')
    parts.append("</div>")

    meta = [f"#{index}", f"freq {card.frequency}"]
    if chapter:
        meta.append(chapter)
    if card.audio_filename or card.sentence_audio_filename:
        meta.append("has audio")
    parts.append(f'<div class="meta">{" · ".join(meta)}</div>')
    parts.append("</article>")
    return "\n".join(parts)


def export_cards_to_html(
    cards: List[WordCard],
    path: str,
    cedict: Optional[Dict[str, DictEntry]] = None,
    deck_name: str = "",
    cloze: bool = False,
) -> Path:
    """
    Write a self-contained HTML preview of the deck, one card per box.

    Args:
        cards: Cards to render
        path: Destination HTML path (parent dirs created as needed)
        cedict: Optional CC-CEDICT dictionary for pinyin/definition lookup
        deck_name: Shown in the page title/heading
        cloze: Render cloze fronts ([...] blanks) instead of highlights

    Returns:
        Path the preview was written to
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    title = html.escape(deck_name or "Deck preview")
    style = "regular (word-in-sentence)" if not cloze else "cloze deletion"
    rendered = [_render_card(i, card, cedict, cloze) for i, card in enumerate(cards, 1)]

    document = f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<title>{title} — preview</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<h1>{title}</h1>
<div class="summary">{len(cards)} cards · {style}</div>
<div class="cards">
{chr(10).join(rendered)}
</div>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")
    return path
