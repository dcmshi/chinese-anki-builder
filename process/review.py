"""Export cards for human review and load them back (pre-import QC).

Workflow: `--review cards.csv` stops the pipeline after card creation and
writes one row per card; the user edits or deletes rows in a spreadsheet or
editor; `--from-review cards.csv` builds the deck from the reviewed file.
Every column is authoritative on the way back in — including word pinyin
and definition, so a wrong CEDICT sense can be fixed by hand.

Files are UTF-8 with BOM so Excel on Windows opens the Chinese correctly.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional

from process.cedict_loader import DictEntry
from process.pinyin_converter import word_to_pinyin
from process.word_selector import WordCard

REVIEW_COLUMNS = [
    "word",
    "frequency",
    "chapter",
    "sentence",
    "sentence_pinyin",
    "sentence_translation",
    "word_pinyin",
    "definition",
]


def export_cards_to_csv(
    cards: List[WordCard],
    path: str,
    cedict: Optional[Dict[str, DictEntry]] = None,
) -> Path:
    """
    Write cards to a review CSV, one row per card.

    Word pinyin and definition are resolved the same way deck building
    resolves them, so the reviewer sees exactly what the card will show.

    Args:
        cards: Cards to export
        path: Destination CSV path (parent dirs created as needed)
        cedict: Optional CC-CEDICT dictionary for pinyin/definition lookup

    Returns:
        Path the review file was written to
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        for card in cards:
            definition = card.definition
            if not definition and cedict and card.word in cedict:
                definition = cedict[card.word].get_first_definition()
            writer.writerow(
                {
                    "word": card.word,
                    "frequency": card.frequency,
                    "chapter": card.chapter,
                    "sentence": card.sentence,
                    "sentence_pinyin": card.sentence_pinyin,
                    "sentence_translation": card.sentence_translation,
                    "word_pinyin": card.word_pinyin or word_to_pinyin(card.word, cedict),
                    "definition": definition,
                }
            )
    return path


def load_cards_from_csv(path: str) -> List[WordCard]:
    """
    Load reviewed cards back from a CSV written by export_cards_to_csv.

    Rows with a blank word or sentence are skipped (deleting a row and
    blanking it out are equivalent). All other fields are taken as-is —
    the reviewer's edits are authoritative.

    Args:
        path: Review CSV path

    Returns:
        List of WordCard objects

    Raises:
        FileNotFoundError: review file doesn't exist
        ValueError: required columns missing, or no usable rows
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Review file not found: {path}")

    cards = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        missing = [c for c in ("word", "sentence") if c not in fieldnames]
        if missing:
            raise ValueError(f"Review file is missing required columns: {', '.join(missing)}")

        for row in reader:
            word = (row.get("word") or "").strip()
            sentence = (row.get("sentence") or "").strip()
            if not word or not sentence:
                continue

            try:
                frequency = int(row.get("frequency") or 0)
            except ValueError:
                frequency = 0

            cards.append(
                WordCard(
                    word=word,
                    sentence=sentence,
                    frequency=frequency,
                    chapter=(row.get("chapter") or "").strip(),
                    sentence_translation=(row.get("sentence_translation") or "").strip(),
                    sentence_pinyin=(row.get("sentence_pinyin") or "").strip(),
                    word_pinyin=(row.get("word_pinyin") or "").strip(),
                    definition=(row.get("definition") or "").strip(),
                )
            )

    if not cards:
        raise ValueError(f"No usable card rows in review file: {path}")
    return cards
