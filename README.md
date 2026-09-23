<p align="center">
  <img src="logo.png" alt="Anki Chinese Deck Builder logo" width="160">
</p>

# Anki Chinese Deck Builder

Automatically generate Anki flashcards for learning Chinese from EPUB and PDF books.

## Features

- 📚 Extract text from EPUB and PDF files (with chapter detection for both)
- 🔤 Tokenize Chinese text using jieba
- 🎯 Select high-frequency multi-character words, optionally filtered by HSK level
- 📝 Generate word-in-sentence Anki cards (target word highlighted in the sentence)
- 🧩 Optional cloze-deletion cards (`--cloze`)
- ✅ Pre-import QC: export cards to CSV, edit/delete rows, rebuild (`--review` / `--from-review`)
- 👀 Static HTML card preview for visual skimming (`--preview`)
- ✏️ Editable browser review page: edit and drop rendered cards, download the
  CSV (`--review-ui`)
- 🚫 Known-words filtering so decks contain only new vocabulary (`--known-words`)
- 📋 Build straight from a vocabulary list such as an HSK level (`--wordlist`),
  optionally taking example sentences from a book
- 🔉 Optional word and sentence audio (`--tts`, `--tts-sentences`)
- 🗣️ Add pinyin (word + sentence, tone marks) and English definitions
- 🌐 Pluggable translation backends (HY-MT1.5, NLLB-200, Argos Translate neural MT, or CC-CEDICT fallback)
- 🔊 Optional TTS word audio via gTTS (`--tts`, requires the `tts` extra)
- 📊 Stats export (`--stats`): counts, coverage, and the selected word list as JSON
- 💾 Offline-first: downloads required resources only if missing
- ✅ Quality checks: filters words without definitions, 200+ unit tests

## Installation

This project uses **uv** for Python and dependency management (no system Python required).

### Install uv

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Project Dependencies

```bash
# uv will automatically install Python and dependencies
uv sync
```

## Quick Start

```bash
# Basic usage
uv run python main.py --input book.epub --deck "My Chinese Deck"

# Select top 200 words with minimum frequency of 3
uv run python main.py --input book.epub --deck "Chinese Book" --top-words 200 --min-freq 3

# Specify output directory
uv run python main.py --input book.pdf --output my_decks
```

**Note**: Always use `uv run` to execute commands - this ensures project dependencies are used.

## Usage

```bash
uv run python main.py --input <file> [options]
uv run python main.py --wordlist <file> [--input <book>] [options]
```

**Options:**
- `--input, -i` - Input EPUB or PDF file (required unless `--wordlist` or `--from-review`)
- `--wordlist, -w` - Build one card per word in a TXT/CSV/TSV list (see below)
- `--deck, -d` - Deck name (default: filename)
- `--top-words, -n` - Number of top words to select (default: 150)
- `--min-freq, -m` - Minimum word frequency (default: 2)
- `--output, -o` - Output directory (default: output)
- `--config, -c` - Config file (default: config.yaml)
- `--hsk` - Only include HSK words: `3` (up to level 3), `2-4`, or `1,3,5` (7 = 7-9 band)
- `--stats` - Export pipeline stats to a JSON file
- `--cloze` / `--no-cloze` - Build cloze-deletion cards (word blanked out of the sentence)
- `--tts` / `--no-tts` - Generate word audio with gTTS (requires internet and `uv sync --extra tts`)
- `--tts-sentences` / `--no-tts-sentences` - Also generate example-sentence audio
- `--known-words` - Text file of already-known words to exclude (one per line)
- `--preview` - Write a static HTML preview of the cards (combines with `--review`)
- `--review` - Write cards to a CSV for QC and stop before deck build
- `--review-ui` - Write an editable HTML review page and stop before deck build
- `--from-review` - Build the deck from a reviewed CSV (replaces `--input`)

The three boolean flags have `--no-` forms so a `true` in `config.yaml` can be
switched off for a single run.

**Cache location**: downloaded dictionaries, HSK lists, models and TTS audio
go to `data/` in the checkout. Set `ANKI_CHINESE_DATA_DIR` to put them
elsewhere (an installed copy defaults to a per-user data directory instead of
the package location).

**Quality-control workflow**: export the cards for review, fix or delete
rows in any spreadsheet, then build:

```bash
uv run python main.py --input book.epub --deck "My Deck" --review cards.csv
# ... edit cards.csv in Excel / your editor ...
uv run python main.py --from-review cards.csv --deck "My Deck"
```

**Same workflow in a browser**: `--review-ui` writes a self-contained page
that renders every card the way Anki will show it, with inline editing and a
drop button. Fix a wrong dictionary sense or a clumsy translation while
looking at the card rather than at a spreadsheet row:

```bash
uv run python main.py --input book.epub --deck "My Deck" --review-ui cards.html
# ... open cards.html, edit and drop cards, click "Download reviewed CSV" ...
uv run python main.py --from-review ~/Downloads/cards.csv --deck "My Deck"
```

**Word-list decks** (e.g. one deck per HSK level): `--wordlist` makes one
card per listed word, in list order, single characters included, instead of
picking words by frequency.

```bash
# List only: sentence/pinyin/definition from the list if present, else CC-CEDICT
uv run python main.py --wordlist hsk1.csv --deck "HSK 1"

# List + book: example sentences come from the book
uv run python main.py --wordlist hsk3.csv --input reader.epub --deck "HSK 3 in context"
```

- `.txt`: one word per line (anything after the first tab or comma is ignored)
- `.csv` / `.tsv`: columns matched by header name: word (`word`, `simplified`,
  `hanzi`, ...), and optional `sentence`/`example`, `pinyin`, and
  `definition`/`meaning`. Without a recognized header the first column is the word.
- Example sentence priority: book > list `sentence` column > none. Cards with
  no sentence are word-only (the word on the front); `--cloze` drops them.
- List pinyin/definition override CC-CEDICT, and a listed word missing from
  CC-CEDICT is kept when the list defines it.
- Combines with `--known-words`, `--preview`, `--cloze`, `--tts`. Not with
  `--hsk`, `--top-words`, `--min-freq`, `--stats`, `--review`, `--review-ui`
  (the list already is the selection; edit it directly instead of reviewing).

Word, frequency and chapter are read-only in the page and round-trip
untouched; sentence, sentence pinyin, translation, word pinyin and
definition are editable. Editing the sentence flags its pinyin as possibly
stale, since pinyin cannot be regenerated in the browser.

## Configuration

Edit `config.yaml` to set default values:

```yaml
top_words: 150
min_frequency: 2
enable_tts: false
output_dir: "output"
```

## Card Format

Each card shows:

- **Front**: Sentence with the target word highlighted inline
- **Back**:
  - Sentence + full-sentence pinyin
  - Word in Chinese with pinyin (tone marks)
  - English definition (CC-CEDICT)
  - Sentence translation
  - Optional audio
  - Chapter (also added as a `chapter::…` Anki tag for filtering)

With `--cloze`, the front instead shows the sentence with the target word
blanked out (`{{c1::…}}` cloze deletion).

## How It Works

1. **Extract**: Read text from EPUB/PDF and detect chapters
2. **Clean**: Normalize whitespace and remove artifacts
3. **Tokenize**: Segment Chinese text using jieba
4. **Analyze**: Compute word frequencies across the book
5. **Select**: Pick top N multi-character words
6. **Lookup**: Get pinyin and definitions from CC-CEDICT
7. **Match**: Find example sentences for each word
8. **Generate**: Create Anki deck (.apkg file)

## Project Structure

```
anki-chinese-deck/
├── main.py              # CLI entry point
├── config.yaml          # Configuration
├── extract/             # Text extraction
├── process/             # Text processing & tokenization
├── anki/                # Anki deck generation
├── utils/               # Utilities
└── data/                # Cached dictionaries
```

## Dependencies

- `jieba` - Chinese text segmentation
- `pypinyin` - Pinyin conversion
- `genanki` - Anki deck generation
- `ebooklib` - EPUB parsing
- `BeautifulSoup4` - HTML parsing
- `pypdf` - PDF extraction
- `argostranslate` - Offline neural MT
- Optional extras: `hymt` (HY-MT1.5 on llama.cpp, highest quality), `nllb`
  (NLLB-200 on CTranslate2), `tts` (gTTS audio)

## Roadmap

- [x] Basic EPUB support
- [x] Basic PDF support
- [x] CC-CEDICT integration
- [x] Word frequency analysis
- [x] Anki deck generation
- [x] HSK level filtering
- [x] TTS audio generation
- [x] Better chapter detection (EPUB spine order, PDF heading heuristics)
- [x] Cloze deletion cards
- [x] Statistics export

## License

MIT

## Credits

- [CC-CEDICT](https://cc-cedict.org/) - Chinese-English dictionary
- [jieba](https://github.com/fxsjy/jieba) - Chinese text segmentation
- [genanki](https://github.com/kerrickstaley/genanki) - Anki deck generation
