# Anki Chinese Deck Builder

**Purpose**: Automatically generate Anki flashcards for learning Chinese from books (EPUB/PDF).

**Target users**: Chinese learners who read native content and want high-quality, low-noise Anki decks.

## What It Does

- Extracts text from Chinese books (EPUB/PDF)
- Detects chapters
- Tokenizes text using jieba
- Selects high-frequency multi-character words
- Generates word-in-sentence Anki cards with pinyin, definitions, and translations
- Outputs .apkg Anki deck
- Runs offline-first (downloads CC-CEDICT if missing)

## Core Requirements

**Input**: EPUB or PDF (Simplified Chinese only)
**Output**: Anki .apkg deck

**Card Format**:
- **Front**: Sentence in Chinese with target word highlighted
- **Back**: Sentence + pinyin, word pinyin, English definition (CC-CEDICT), sentence translation, chapter tag

## Project Structure

```
anki-chinese-deck/
├── main.py                      # Entry point
├── pyproject.toml               # uv dependencies
├── config.yaml
├── .venv/                       # Auto-created by uv
├── data/                        # Cached dictionaries
├── output/                      # Generated .apkg files
│
├── extract/                     # EPUB/PDF extraction
│   ├── epub_extractor.py
│   └── pdf_extractor.py
│
├── process/                     # Text processing
│   ├── text_cleaner.py
│   ├── tokenizer.py             # jieba tokenization
│   ├── cedict_loader.py         # CC-CEDICT dictionary
│   ├── word_selector.py         # Frequency analysis
│   ├── pinyin_converter.py
│   └── sentence_translator.py
│
├── translate/                   # Translation backends
│   ├── base.py                  # Abstract backend
│   ├── argos_backend.py         # Neural MT (Python 3.12-3.13)
│   ├── cedict_backend.py        # Fallback (all versions)
│   └── manager.py
│
├── anki/                        # Deck generation
│   ├── templates.py             # Card templates
│   └── deck_builder.py
│
├── tts/                         # TTS (future)
│   └── gtts_generator.py
│
├── utils/
│   ├── file_utils.py
│   └── chinese_utils.py
│
└── tests/                       # Unit tests (24 tests)
```

## Design Principles

- **Offline-first**: Download CC-CEDICT, cache locally
- **Deterministic**: Same input + config → same deck
- **Minimal magic**: Explicit pipelines over heuristics
- **Modular**: Each module does one thing

## Data Flow Pipeline

```
1. Input: EPUB/PDF file
2. Extract: Read chapters (epub_extractor/pdf_extractor)
3. Clean: Normalize text (text_cleaner)
4. Split: Break into sentences
5. Tokenize: Segment with jieba (tokenizer)
6. Analyze: Compute word frequencies (word_selector)
7. Filter: Keep multi-character words (2+ chars)
8. Select: Pick top N words by frequency
9. Dictionary: Load CC-CEDICT (cedict_loader, auto-download if needed)
10. Validate: Filter words without CEDICT definitions
11. Match: Find example sentences for each word
12. Enrich: Add pinyin, definition, translation
13. Build: Generate Anki deck (deck_builder)
14. Output: Save .apkg to output/
```

## CLI Usage

**Basic command** (using uv):
```bash
uv run python main.py \
  --input book.epub \
  --deck "Chinese Book Deck" \
  --top-words 300 \
  --min-freq 5
```

**Common workflows**:
```bash
# Quick test (50 cards)
uv run python main.py --input book.epub --deck "Test" --top-words 50 --min-freq 2

# Standard novel (90% coverage, ~2500 cards)
uv run python main.py --input book.epub --deck "Novel" --top-words 3000 --min-freq 5

# Beginner friendly (common words only)
uv run python main.py --input book.epub --deck "Beginner" --top-words 300 --min-freq 10
```

**Optional flags**:
```bash
--output <dir>          # Custom output directory
--config <file>         # Custom YAML config
--tts                   # Enable TTS (not implemented)
--hsk 1-5               # HSK filtering (not implemented)
--stats <file>          # Export stats (not implemented)
```

## Key Implementation Notes

**Tokenization**: jieba for segmentation, multi-character words (2+ chars), frequency analysis

**Dictionary**: CC-CEDICT (auto-download, cached locally), first definition used

**Pinyin**: pypinyin for sentences, CC-CEDICT primary for words (pypinyin fallback)

**Translation**:
- Argos Translate (neural MT, Python 3.12-3.13) - Recommended
- CC-CEDICT word-by-word (fallback, all Python versions) - Acceptable
- Pluggable backend system with automatic fallback

**Chapter Handling**: Detect chapters in EPUB/PDF, tag cards, fallback to single chapter

**Anki Deck**: genanki library, deterministic note IDs (hash-based), no duplicates

**Dependencies**: Managed by uv (no system Python required)

## Setup

```bash
# Install uv (first time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run
uv run python main.py --input book.epub --deck "My Deck"

# Run tests
uv run pytest tests/ -v
```

## Non-Goals (For Now)

- ❌ Cloud services
- ❌ OCR
- ❌ Traditional Chinese
- ❌ UI/web app
- ❌ Spaced repetition logic

## Status

**Production ready**: Text extraction, tokenization, word selection, dictionary lookup, pinyin, translation, deck generation, CLI

**Pending**: HSK filtering, TTS audio, stats export, cloze cards

See **FEATURES.md** for detailed implementation status, performance metrics, translation architecture, testing info, and recommended settings.
