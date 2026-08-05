"""Static HTML card preview for pre-import QC.

Renders every card the way Anki will show it (front above back, same dark
styling as the real card CSS) into one self-contained HTML file — no
external assets, no JavaScript — so a whole deck can be skimmed in a
browser before/alongside the CSV review step. Audio is not embedded; a
marker notes when a card will carry sound.

Card appearance itself lives in anki/card_render.py, shared with the
editable review UI (anki/review_ui.py).
"""

import html
from pathlib import Path
from typing import Dict, List, Optional

from anki.card_render import PAGE_CSS, resolve_faces
from process.cedict_loader import DictEntry
from process.word_selector import WordCard


def _render_card(
    index: int,
    card: WordCard,
    cedict: Optional[Dict[str, DictEntry]],
    cloze: bool,
) -> str:
    faces = resolve_faces(card, cedict, cloze)
    pinyin = html.escape(faces.word_pinyin)
    definition = html.escape(faces.definition)
    translation = html.escape(faces.translation)
    sentence_pinyin = html.escape(faces.sentence_pinyin)
    chapter = html.escape(faces.chapter)
    front_sentence = faces.front_sentence
    back_sentence = faces.back_sentence

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
