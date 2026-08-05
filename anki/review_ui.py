"""Editable HTML review page for pre-import QC (--review-ui).

Renders every card the way anki/preview.py does, then adds inline editing,
a drop toggle, and a button that downloads a CSV byte-compatible with
process/review.py -- so the reviewer QCs rendered cards in a browser instead
of CSV rows in a spreadsheet, and --from-review consumes the result
unchanged.

Self-contained: no external assets, no server, no framework. The embedded
JSON payload is the authoritative model; the rendered grid is its initial
view.
"""

import html
import json
from pathlib import Path
from typing import Dict, List, Optional

from anki.card_render import PAGE_CSS, resolve_faces
from process.cedict_loader import DictEntry
from process.review import REVIEW_COLUMNS
from process.word_selector import WordCard

# Columns the reviewer may edit in the page. The rest (word, frequency,
# chapter) round-trip untouched -- word is load-bearing for the highlight,
# cloze markup and note GUID, so changing it means dropping the card or
# hand-editing the downloaded CSV.
EDITABLE_COLUMNS = (
    "sentence",
    "sentence_pinyin",
    "sentence_translation",
    "word_pinyin",
    "definition",
)

UI_CSS = """
.toolbar {
    position: sticky; top: 0; z-index: 10;
    background-color: #1e1e1e; padding: 12px 0 16px;
    display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
}
#filter {
    flex: 1 1 240px; min-width: 200px;
    background-color: #2b2b2b; color: #e8e8e8;
    border: 1px solid #555; border-radius: 6px; padding: 8px 10px; font-size: 14px;
}
#download {
    background-color: #ff6b6b; color: #1e1e1e; font-weight: bold;
    border: none; border-radius: 6px; padding: 9px 16px; font-size: 14px; cursor: pointer;
}
#counter { color: #888; font-size: 13px; }
.card.hidden { display: none; }
.card.dropped { opacity: 0.35; }
.card.dropped .editor { display: none; }
.editor { text-align: left; margin-top: 12px; border-top: 1px dashed #555; padding-top: 10px; }
.editor label {
    display: block; font-size: 10px; text-transform: uppercase;
    letter-spacing: 1px; color: #777; margin-top: 8px;
}
.editor [data-field] {
    display: block; background-color: #333; border: 1px solid #4a4a4a;
    border-radius: 4px; padding: 6px 8px; margin-top: 3px;
    font-size: 14px; color: #e8e8e8; min-height: 1.2em; white-space: pre-wrap;
}
.editor [data-field]:focus { outline: 2px solid #ff6b6b; background-color: #3a3a3a; }
.stale-warning { display: none; color: #ffcc66; font-size: 12px; margin-top: 8px; }
.card.stale .stale-warning { display: block; }
.drop-toggle {
    background: none; border: 1px solid #555; color: #999;
    border-radius: 4px; padding: 2px 8px; font-size: 12px; cursor: pointer;
}
.card.dropped .drop-toggle { color: #ff6b6b; border-color: #ff6b6b; }
"""

# Vanilla ES5-compatible JS, inlined so the page stays self-contained.
# The embedded JSON is the authoritative model: edits mutate it, the
# rendered card is a view of it, and the CSV is serialized from it.
REVIEW_UI_JS = r"""
(function () {
  var MODEL = JSON.parse(document.getElementById("cards-data").textContent);
  var COLUMNS = JSON.parse(document.getElementById("columns-data").textContent);
  var CLOZE = document.body.dataset.cloze === "true";
  var CSV_NAME = document.body.dataset.csvName;
  var dirty = false;

  function cardEl(i) {
    return document.querySelector('[data-card="' + i + '"]');
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // Mirrors highlight_word_in_sentence / cloze_front in Python: replace every
  // occurrence, since card words are 2+ Han characters and a nested match is
  // the same morpheme rather than a coincidence.
  function markedSentence(row, marker) {
    var sentence = escapeHtml(row.sentence);
    var word = escapeHtml(row.word);
    if (!word) return sentence;
    return sentence.split(word).join(marker(word));
  }

  function frontHtml(row) {
    return markedSentence(row, function (word) {
      return CLOZE
        ? '<span class="cloze">[...]</span>'
        : '<span class="target">' + word + "</span>";
    });
  }

  // Cloze backs reveal the word; regular backs look like the front.
  function backHtml(row) {
    return markedSentence(row, function (word) {
      return CLOZE
        ? '<span class="cloze">' + word + "</span>"
        : '<span class="target">' + word + "</span>";
    });
  }

  function renderCard(i) {
    var row = MODEL[i];
    var el = cardEl(i);
    el.querySelector('[data-display="front"]').innerHTML = frontHtml(row);
    el.querySelector('[data-display="back"]').innerHTML = backHtml(row);
    el.querySelector('[data-display="sentence-pinyin"]').textContent = row.sentence_pinyin;
    el.querySelector('[data-display="pinyin"]').textContent = row.word_pinyin;
    el.querySelector('[data-display="definition"]').textContent = row.definition;
    el.querySelector('[data-display="translation"]').textContent = row.sentence_translation;
    el.classList.toggle("stale", !!row._sentenceEdited && !row._pinyinEdited);
  }

  function updateCounter() {
    var dropped = MODEL.filter(function (r) { return r._dropped; }).length;
    document.getElementById("counter").textContent =
      MODEL.length + " cards · " + dropped + " dropped";
  }

  // RFC 4180: quote when the field holds a comma, quote, CR or LF; double
  // any internal quote. CC-CEDICT definitions routinely contain commas and
  // quotes, so this is the difference between a clean deck and a corrupt one.
  function csvCell(value) {
    var s = value === null || value === undefined ? "" : String(value);
    return /[",\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }

  function toCSV() {
    var lines = [COLUMNS.join(",")];
    MODEL.forEach(function (row) {
      if (row._dropped) return;
      lines.push(COLUMNS.map(function (c) { return csvCell(row[c]); }).join(","));
    });
    // Leading BOM matches export_cards_to_csv's utf-8-sig; CRLF matches
    // Python csv's default lineterminator. fromCharCode rather than a
    // literal BOM so the character stays visible in source.
    var bom = String.fromCharCode(0xFEFF);
    return bom + lines.join("\r\n") + "\r\n";
  }

  document.querySelectorAll("[data-field]").forEach(function (el) {
    el.addEventListener("input", function () {
      var i = Number(el.dataset.cardIndex);
      var field = el.dataset.field;
      MODEL[i][field] = el.textContent;
      if (field === "sentence") MODEL[i]._sentenceEdited = true;
      if (field === "sentence_pinyin") MODEL[i]._pinyinEdited = true;
      dirty = true;
      renderCard(i);
    });
  });

  document.querySelectorAll("[data-drop]").forEach(function (button) {
    button.addEventListener("click", function () {
      var i = Number(button.dataset.drop);
      MODEL[i]._dropped = !MODEL[i]._dropped;
      cardEl(i).classList.toggle("dropped", !!MODEL[i]._dropped);
      button.textContent = MODEL[i]._dropped ? "undo" : "drop";
      dirty = true;
      updateCounter();
    });
  });

  document.getElementById("filter").addEventListener("input", function (event) {
    var needle = event.target.value.trim().toLowerCase();
    MODEL.forEach(function (row, i) {
      var haystack = (row.word + " " + row.definition + " " + row.sentence).toLowerCase();
      cardEl(i).classList.toggle("hidden", needle !== "" && haystack.indexOf(needle) === -1);
    });
  });

  document.getElementById("download").addEventListener("click", function () {
    var blob = new Blob([toCSV()], { type: "text/csv;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = CSV_NAME;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    dirty = false;
  });

  window.addEventListener("beforeunload", function (event) {
    if (!dirty) return;
    event.preventDefault();
    event.returnValue = "";
  });

  updateCounter();
})();
"""


def _card_row(card: WordCard, cedict: Optional[Dict[str, DictEntry]]) -> dict:
    """One payload row, holding exactly the REVIEW_COLUMNS values."""
    faces = resolve_faces(card, cedict)
    return {
        "word": card.word,
        "frequency": card.frequency,
        "chapter": faces.chapter,
        "sentence": card.sentence,
        "sentence_pinyin": faces.sentence_pinyin,
        "sentence_translation": faces.translation,
        "word_pinyin": faces.word_pinyin,
        "definition": faces.definition,
    }


def _editor_field(index: int, column: str, value: str) -> str:
    label = column.replace("_", " ")
    return (
        f"<label>{label}</label>"
        f'<div contenteditable="true" spellcheck="false" '
        f'data-field="{column}" data-card-index="{index}">{html.escape(value)}</div>'
    )


def _render_card(
    index: int,
    card: WordCard,
    row: dict,
    cloze: bool,
    cedict: Optional[Dict[str, DictEntry]],
) -> str:
    faces = resolve_faces(card, cedict, cloze)

    meta = [f"#{index + 1}", f"freq {card.frequency}"]
    if faces.chapter:
        meta.append(faces.chapter)

    parts = [
        f'<article class="card" data-card="{index}">',
        '<div class="front"><div class="side-label">Front</div>',
        f'<div class="sentence" data-display="front">{faces.front_sentence}</div></div>',
        '<div class="back"><div class="side-label">Back</div>',
        f'<div class="sentence" data-display="back">{faces.back_sentence}</div>',
        f'<div class="sentence-pinyin" data-display="sentence-pinyin">'
        f"{html.escape(faces.sentence_pinyin)}</div>",
        f'<div class="word-highlight">{html.escape(card.word)}</div>',
        f'<div class="pinyin" data-display="pinyin">{html.escape(faces.word_pinyin)}</div>',
        f'<div class="definition" data-display="definition">'
        f"{html.escape(faces.definition)}</div>",
        f'<div class="sentence-translation" data-display="translation">'
        f"{html.escape(faces.translation)}</div>",
        "</div>",
        '<div class="stale-warning">sentence pinyin may be stale — edit it or check '
        "before building</div>",
        '<div class="editor">',
    ]
    for column in EDITABLE_COLUMNS:
        parts.append(_editor_field(index, column, str(row[column])))
    parts.append("</div>")
    parts.append(
        f'<div class="meta">{" · ".join(html.escape(m) for m in meta)} '
        f'<button type="button" class="drop-toggle" data-drop="{index}">drop</button></div>'
    )
    parts.append("</article>")
    return "\n".join(parts)


def export_cards_to_review_ui(
    cards: List[WordCard],
    path: str,
    cedict: Optional[Dict[str, DictEntry]] = None,
    deck_name: str = "",
    cloze: bool = False,
) -> Path:
    """
    Write a self-contained editable review page.

    Args:
        cards: Cards to review
        path: Destination HTML path (parent dirs created as needed)
        cedict: Optional CC-CEDICT dictionary for pinyin/definition lookup
        deck_name: Shown in the page title/heading
        cloze: Render cloze fronts ([...] blanks) instead of highlights

    Returns:
        Path the page was written to
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = [_card_row(card, cedict) for card in cards]
    rendered = [
        _render_card(i, card, row, cloze, cedict) for i, (card, row) in enumerate(zip(cards, rows))
    ]

    # ensure_ascii=False keeps the Chinese readable in the source; escaping
    # every < as its JSON unicode escape is what stops a card containing
    # </script> from terminating the block early. It stays valid JSON and
    # decodes to exactly the same string.
    payload = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c")

    title = html.escape(deck_name or "Deck review")
    csv_name = html.escape(path.with_suffix(".csv").name)
    columns = json.dumps(list(REVIEW_COLUMNS))

    document = f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<title>{title} — review</title>
<style>{PAGE_CSS}{UI_CSS}</style>
</head>
<body data-csv-name="{csv_name}" data-cloze="{'true' if cloze else 'false'}">
<h1>{title}</h1>
<div class="toolbar">
<input id="filter" type="search" placeholder="Filter by word, definition or sentence…">
<span id="counter"></span>
<button type="button" id="download">Download reviewed CSV</button>
</div>
<div class="cards">
{chr(10).join(rendered)}
</div>
<script type="application/json" id="cards-data">{payload}</script>
<script id="columns-data" type="application/json">{columns}</script>
<script>{REVIEW_UI_JS}</script>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")
    return path
