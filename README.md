# Anki Chinese Deck Builder

Automatically generate Anki flashcards for learning Chinese from EPUB and PDF books.

## Features

- 📚 Extract text from EPUB and PDF files
- 🔤 Tokenize Chinese text using jieba
- 🎯 Select high-frequency multi-character words
- 📝 Generate word-in-sentence Anki cards
- 🗣️ Add pinyin (word + sentence) and English definitions
- 🌐 **NEW:** Pluggable translation backends (Argos Translate neural MT or CC-CEDICT fallback)
- 🔊 Optional TTS audio support (coming soon)
- 💾 Offline-first: downloads required resources only if missing
- ✅ Quality checks: filters words without definitions, unit tested

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
- `--tts` - Enable TTS audio (not yet implemented)

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

- **Front**: Sentence with the target word highlighted
- **Back**:
  - Word in Chinese
  - Pinyin with tones
  - English definition
  - Optional audio
  - Chapter tag (if available)

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
- `PyPDF2` - PDF extraction

## Roadmap

- [x] Basic EPUB support
- [x] Basic PDF support
- [x] CC-CEDICT integration
- [x] Word frequency analysis
- [x] Anki deck generation
- [ ] HSK level filtering
- [ ] TTS audio generation
- [ ] Better chapter detection
- [ ] Cloze deletion cards
- [ ] Statistics export

## License

MIT

## Credits

- [CC-CEDICT](https://cc-cedict.org/) - Chinese-English dictionary
- [jieba](https://github.com/fxsjy/jieba) - Chinese text segmentation
- [genanki](https://github.com/kerrickstaley/genanki) - Anki deck generation
