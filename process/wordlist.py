"""Load a vocabulary word list (e.g. an HSK level) to build cards from.

Unlike --known-words (a set to exclude), a word list is the deck itself:
one card per listed word, in list order.

Formats (UTF-8, BOM tolerated):
  - .txt: one word per line; anything after the first tab or comma is
    ignored, so "学习<TAB>xué xí<TAB>to study" lines work as-is.
  - .csv / .tsv: when the first row is a header with a recognized word
    column (word, simplified, hanzi, ...), columns are matched by name,
    including optional sentence, pinyin and definition columns. Without a
    recognized header, the first column is the word.

Blank lines and lines starting with `#` are skipped. Duplicate words keep
their first occurrence.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Header names recognized for each column (compared lower-cased)
_WORD_COLUMNS = {"word", "simplified", "hanzi", "chinese", "汉字", "词语", "词汇"}
_SENTENCE_COLUMNS = {"sentence", "example", "example_sentence", "例句"}
_PINYIN_COLUMNS = {"pinyin", "word_pinyin", "拼音"}
_DEFINITION_COLUMNS = {"definition", "meaning", "english", "translation", "释义"}


@dataclass
class WordListEntry:
    """One word from a word list, with its optional per-word overrides."""

    word: str
    sentence: str = ""
    pinyin: str = ""
    definition: str = ""


def _find_column(header: List[str], names: set) -> Optional[int]:
    for i, name in enumerate(header):
        if name.strip().lower() in names:
            return i
    return None


def _cell(row: List[str], index: Optional[int]) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def load_wordlist(path: str) -> List[WordListEntry]:
    """
    Load a word list file.

    Args:
        path: Word list path (.txt, .csv or .tsv)

    Returns:
        Entries in file order, duplicates removed

    Raises:
        FileNotFoundError: the file doesn't exist
        ValueError: unsupported extension
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Word list not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in (".txt", ".csv", ".tsv"):
        raise ValueError(f"Unsupported word list format: {path.suffix} (use .txt, .csv or .tsv)")

    with open(path, encoding="utf-8-sig", newline="") as f:
        if suffix == ".txt":
            rows = [[line.replace("\t", ",").split(",", 1)[0]] for line in f.read().splitlines()]
        else:
            rows = list(csv.reader(f, delimiter="\t" if suffix == ".tsv" else ","))

    rows = [
        row
        for row in rows
        if any(cell.strip() for cell in row) and not row[0].strip().startswith("#")
    ]

    word_col, sentence_col, pinyin_col, definition_col = 0, None, None, None
    if rows and suffix != ".txt":
        header_word_col = _find_column(rows[0], _WORD_COLUMNS)
        if header_word_col is not None:
            header = rows[0]
            word_col = header_word_col
            sentence_col = _find_column(header, _SENTENCE_COLUMNS)
            pinyin_col = _find_column(header, _PINYIN_COLUMNS)
            definition_col = _find_column(header, _DEFINITION_COLUMNS)
            rows = rows[1:]

    entries: List[WordListEntry] = []
    seen = set()
    for row in rows:
        word = _cell(row, word_col)
        if not word or word in seen:
            continue
        seen.add(word)
        entries.append(
            WordListEntry(
                word=word,
                sentence=_cell(row, sentence_col),
                pinyin=_cell(row, pinyin_col),
                definition=_cell(row, definition_col),
            )
        )
    return entries
