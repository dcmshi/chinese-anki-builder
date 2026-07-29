# Anki Chinese Deck Builder

**Purpose**: Generate Anki flashcards for learning Chinese from books
(EPUB/PDF). Target users are Chinese learners who read native content and
want high-quality, low-noise decks.

**Input**: EPUB or PDF (Simplified Chinese only) → **Output**: Anki `.apkg`

## Where the Docs Live

Keep these authoritative and don't restate them here:

| Doc | Owns |
|-----|------|
| `README.md` | Install, full CLI option list, card format, dependency list |
| `FEATURES.md` | Feature status, performance metrics, recommended settings, example workflows |
| `TRANSLATION.md` | Backend architecture, model config/env overrides, troubleshooting |
| `TESTING.md` | Test layout, coverage workflow, fixture/mocking conventions |
| `TODO.md` | Audit checklists (latest: 2026-07-24, closed out) and deferred items |
| `CHANGELOG.md` | Released versions (current: 0.7.0) |
| `QUICKSTART.md` | First-run walkthrough for end users |

## Project Structure

```
chinese-anki-builder/
├── main.py                      # CLI entry point (also the `anki-chinese` script)
├── analyze_coverage.py          # One-off Zipf coverage estimate (hardcoded 三体 stats)
├── pyproject.toml               # uv deps, ruff/black config, wheel contents
├── config.yaml
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
├── tts/gtts_generator.py        # gTTS word/sentence audio (optional extra)
├── utils/                       # file_utils, chinese_utils
└── tests/
```

## Design Principles

- **Offline-first**: download resources once, cache locally
- **Deterministic**: same input + config → same deck
- **Minimal magic**: explicit pipelines over heuristics
- **Modular**: each module does one thing

## Data Flow Pipeline

```
extract → clean → split sentences → tokenize (jieba) → frequency analysis
→ filter (multi-char 2+, optional HSK, optional known-words) → top-N select
→ CEDICT lookup (drop words with no definition) → match example sentences
(bigram index) → enrich (pinyin, definition, translation) → optional TTS
→ build deck (regular or cloze) → write .apkg
```

## Dev Commands

```bash
uv sync                                   # install (add --extra tts/nllb/hymt as needed)
uv run python main.py --input book.epub --deck "My Deck"
uv run pytest tests/ -v
uv run pytest tests/ --cov=. --cov-report=term-missing
uv run ruff check .                       # tests/test_repo_health.py enforces this
uv run black .                            # line-length 100, target py39
```

**Packaging invariant**: `pyproject.toml`'s
`[tool.hatch.build.targets.wheel] only-include` must list every first-party
package plus `main.py`. `test_wheel_config_ships_all_first_party_code`
fails if a new top-level package isn't added.

## CLI Behavior Notes

Full flag list is in README.md. What matters when changing the CLI:

- Precedence is **CLI > config.yaml > built-in default**. Flags default to
  `None` in argparse so "not passed" is distinguishable from "passed a
  falsy value" — preserve this when adding flags.
- `--cloze`, `--tts`, `--tts-sentences` are `BooleanOptionalAction`, so
  `--no-*` turns a config `true` off for one run.
- `--config` errors if the path doesn't exist (no silent fallback).
- `--hsk` accepts `3` (up to 3), `2-4`, `1,3,5`; 7 = the 7-9 band. The
  `hsk_levels` config key accepts a list (exactly those levels), a scalar
  (up to that level), or a spec string.
- `--review cards.csv` stops after card creation and writes one editable
  row per card; blank word/sentence drops the row. `--from-review cards.csv`
  then builds the deck and **every edited field is authoritative**,
  including word pinyin and definition. `--from-review` replaces `--input`.

Config keys: `top_words`, `min_frequency`, `output_dir`, `enable_tts`,
`enable_sentence_tts`, `known_words_file`, `cloze`, `hsk_levels`,
`stats_file`, `min_sentence_length`, `max_sentence_length`,
`preferred_backend`, `prefer_offline`, `translation_cache`, plus the model
repo/revision pins documented in `config.yaml`.

**Cache location**: `get_data_dir()` resolves `ANKI_CHINESE_DATA_DIR` first,
then `<repo>/data` for a source checkout, then a per-user data directory
(installed copies must not write ~1GB of models into `site-packages`).

## Key Implementation Notes

**Tokenization**: jieba segmentation; only multi-character words (2+ chars)
become cards; example sentences found via a character-bigram index.

**Dictionary**: CC-CEDICT, auto-downloaded and cached. First definition
used; duplicate entries resolved by preference (common word over proper
noun, then most definitions).

**HSK filtering**: HSK 3.0 lists (krmanik/HSK-3.0), cached under `data/hsk/`,
applied to the candidate pool *before* top-N selection — same for
known-words exclusion.

**Pinyin**: pypinyin for sentences; CC-CEDICT primary for words with a
pypinyin fallback. CEDICT numbered pinyin is converted to tone marks so both
styles match.

**Translation**: pluggable backends ranked by quality score (HY-MT 95 >
NLLB 90 > Argos 80 > CC-CEDICT 40), with automatic fallback. Opt-in backends
are skipped unless their extras are installed. Example sentences go through
one deduplicated `translate_batch` call; per-item failures return `""` and
fall back individually rather than downgrading the whole book. Translations
persist in `data/cache/translations.json`, keyed by backend + language pair
+ text.

**Chapters**: EPUB in spine (reading) order; PDF via heading heuristics
(第X章 …); fallback to a single chapter. Every card carries a chapter field
and a `chapter::…` Anki tag.

**Deck**: genanki, deterministic note GUIDs (full 128-bit hash), no
duplicates. Regular and cloze decks use separate GUID namespaces.

**Caches are written atomically** (temp file + `os.replace`) — CEDICT, HSK
lists, TTS MP3s, translation cache, stats JSON. Keep it that way; a
truncated cache file parses fine and is then trusted forever.

**Python**: `requires-python = ">=3.9,<3.14"`, capped because Argos is
incompatible with 3.14+.

## Non-Goals (For Now)

- ❌ Cloud services
- ❌ OCR
- ❌ Traditional Chinese
- ❌ UI/web app
- ❌ Spaced repetition logic
