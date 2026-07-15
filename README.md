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
```

**Options:**
- `--input, -i` - Input EPUB or PDF file (required)
- `--deck, -d` - Deck name (default: filename)
- `--top-words, -n` - Number of top words to select (default: 150)
- `--min-freq, -m` - Minimum word frequency (default: 2)
- `--output, -o` - Output directory (default: output)
- `--config, -c` - Config file (default: config.yaml)
- `--hsk` - Only include HSK words: `3` (up to level 3), `2-4`, or `1,3,5` (7 = 7-9 band)
- `--stats` - Export pipeline stats to a JSON file
- `--cloze` - Build cloze-deletion cards (word blanked out of the sentence)
- `--tts` - Generate word audio with gTTS (requires internet and `uv sync --extra tts`)

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
