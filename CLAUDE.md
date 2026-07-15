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
- **Front**: Sentence in Chinese with target word highlighted inline (or a
  cloze deletion with `--cloze`)
- **Back**: Sentence + pinyin, word pinyin, English definition (CC-CEDICT), sentence translation, optional word/sentence audio, chapter (field + `chapter::…` Anki tag)

## Project Structure

```
anki-chinese-deck/
├── main.py                      # Entry point
├── pyproject.toml               # uv dependencies
├── config.yaml
├── .venv/                       # Auto-created by uv
├── data/                        # Cached dictionaries, HSK lists, models, TTS audio
├── output/                      # Generated .apkg files
│
├── extract/                     # EPUB/PDF extraction
│   ├── epub_extractor.py        # Spine-order chapter extraction
│   └── pdf_extractor.py         # Heuristic chapter detection
│
├── process/                     # Text processing
│   ├── text_cleaner.py
│   ├── tokenizer.py             # jieba tokenization
│   ├── cedict_loader.py         # CC-CEDICT dictionary
│   ├── word_selector.py         # Frequency analysis + sentence index
│   ├── hsk_filter.py            # HSK 3.0 level filtering
│   ├── pinyin_converter.py      # Tone-mark pinyin (converts CEDICT numbers)
│   ├── review.py                # Pre-import QC CSV export/load
│   ├── known_words.py           # Known-words list loading (exclusion)
│   └── sentence_translator.py
│
├── translate/                   # Translation backends
│   ├── base.py                  # Abstract backend (translate + translate_batch)
│   ├── hymt_backend.py          # HY-MT1.5 llama.cpp (opt-in, highest quality)
│   ├── nllb_backend.py          # NLLB-200 CT2 (opt-in)
│   ├── argos_backend.py         # Neural MT (Python 3.9-3.13)
│   ├── cedict_backend.py        # Fallback (all versions)
│   └── manager.py               # Fallback chain, batching, persistent cache
│
├── anki/                        # Deck generation
│   ├── templates.py             # Card templates (regular + cloze)
│   ├── preview.py               # Static HTML card preview
│   └── deck_builder.py
│
├── tts/                         # TTS audio
│   └── gtts_generator.py        # gTTS word audio (optional extra)
│
├── utils/
│   ├── file_utils.py
│   └── chinese_utils.py
│
└── tests/                       # Unit tests (334 tests)
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
7. Filter: Keep multi-character words (2+ chars); optional HSK-level filter
8. Select: Pick top N words by frequency
9. Dictionary: Load CC-CEDICT (cedict_loader, auto-download if needed)
10. Validate: Filter words without CEDICT definitions
11. Match: Find example sentences for each word (bigram index)
12. Enrich: Add pinyin, definition, translation
13. Audio: Optional gTTS word audio (cached, bundled as media)
14. Build: Generate Anki deck (deck_builder; regular or cloze)
15. Output: Save .apkg to output/; optional stats JSON
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

**Optional flags** (wired into the CLI):
```bash
--output <dir>          # Custom output directory
--config <file>         # Custom YAML config (errors if the path doesn't exist)
--hsk <spec>            # HSK filtering: "3" (up to 3), "2-4", "1,3,5" (7 = 7-9 band)
--stats <file>          # Export pipeline stats to JSON
--cloze                 # Cloze-deletion cards instead of word-in-sentence
--tts                   # gTTS word audio (requires internet + `uv sync --extra tts`)
--tts-sentences         # Also generate example-sentence audio
--known-words <file>    # Exclude already-known words (one per line)
--preview <html>        # Static HTML preview of the cards (works with --review)
--review <csv>          # Write cards to a CSV for QC and stop (no deck built)
--from-review <csv>     # Build the deck from a reviewed CSV (replaces --input)
```

**Pre-import QC workflow**: `--review cards.csv` stops after card creation
and writes one editable row per card (word, sentence, pinyin, definition,
translation, chapter). Edit or delete rows (blank word/sentence = drop),
then `--from-review cards.csv` builds the deck — every edited field is
authoritative, including word pinyin and definition.

Settings read from `config.yaml` (CLI flags override these): `top_words`,
`min_frequency`, `output_dir`, `enable_tts`, `enable_sentence_tts`,
`known_words_file`, `cloze`, `hsk_levels`, `stats_file`,
`min_sentence_length`, `max_sentence_length`.
CLI > config.yaml > built-in default.

## Key Implementation Notes

**Tokenization**: jieba for segmentation, multi-character words (2+ chars), frequency analysis; example sentences found via a character-bigram index

**Dictionary**: CC-CEDICT (auto-download, cached locally), first definition used; duplicate entries resolved by preference (common word over proper noun, then most definitions)

**HSK filtering**: HSK 3.0 word lists (krmanik/HSK-3.0), auto-downloaded and cached under `data/hsk/`; applied to the candidate pool before top-N selection

**Pinyin**: pypinyin for sentences, CC-CEDICT primary for words (pypinyin fallback); CEDICT numbered pinyin is converted to tone marks so both styles match

**Translation**:
- HY-MT1.5 on llama.cpp (WMT25-winning LLM MT, highest quality) - opt-in via
  `uv sync --extra hymt`
- NLLB-200 on CTranslate2 (neural MT, batched with decoding guards) - opt-in
  via `uv sync --extra nllb`
- Argos Translate (neural MT, Python 3.9-3.13) - default neural backend
- CC-CEDICT word-by-word (fallback, all Python versions) - Acceptable
- Pluggable backend system with automatic fallback, ranked by quality score
  (HY-MT 95 > NLLB 90 > Argos 80 > CC-CEDICT 40). Opt-in backends are skipped
  automatically unless their optional deps are installed. Model repos/files
  are overridable and pinnable via config keys (`hymt_model_repo`,
  `hymt_revision`, `nllb_model_repo`, `nllb_model_revision`, ...) or env vars
  (`HYMT_GGUF_REPO`, `NLLB_CT2_MODEL`, ...). First run downloads the model
  (~1GB for HY-MT 1.8B Q4_K_M or NLLB distilled-600M).
- Example sentences are translated in one deduplicated `translate_batch` call
  (native CT2 batch for NLLB); translations persist across runs in
  `data/cache/translations.json`, keyed by backend + language pair + text.
  Config: `preferred_backend`, `prefer_offline`, `translation_cache`.

**Chapter Handling**: EPUB chapters in spine (reading) order; PDF chapters via heading heuristics (第X章 …); cards tagged with chapter (field + Anki tag); fallback to single chapter

**Anki Deck**: genanki library, deterministic note GUIDs (full 128-bit hash), no duplicates; regular and cloze decks use separate GUID namespaces

**TTS**: gTTS word audio (optional `tts` extra), cached under `data/cache/` by text hash, bundled into the .apkg as media

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

**Production ready**: Text extraction (EPUB + PDF chapters), tokenization, word selection, HSK filtering, known-words filtering, dictionary lookup, pinyin, translation, TTS audio (word + sentence), stats export, deck generation (regular + cloze), pre-import QC review workflow, static HTML preview, CLI

**Pending**: Context-aware translation (see TODO.md deferred items)

See **FEATURES.md** for detailed implementation status, performance metrics, translation architecture, testing info, and recommended settings. See **TODO.md** for the 2026-07-09 audit checklist.
