# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.6.0] - 2026-07-15

### Added

- **Static HTML card preview** (`--preview cards.html`): self-contained
  page rendering every card front/back with the real card styling
  (regular and cloze); works alongside `--review` and `--from-review`
- **Known-words filtering** (`--known-words` / `known_words_file`): plain
  text list (one per line; comma/space separated accepted; `#` comments)
  excluded before top-N selection so decks fill with new vocabulary;
  excluded count exported in stats
- **Sentence audio** (`--tts-sentences` / `enable_sentence_tts`): gTTS
  audio for the example sentence, cached and deduplicated across cards.
  Both note models gain a SentenceAudio field appended last, so decks
  built before this version reimport with fields still aligned

## [0.5.0] - 2026-07-15

### Added

- **Pre-import QC review workflow**: `--review cards.csv` stops the
  pipeline after card creation and writes one editable row per card
  (UTF-8 BOM, Excel-friendly); `--from-review cards.csv` builds the deck
  from the reviewed file with no re-extraction or re-translation. Deleted
  or blanked rows drop cards; every edited field is authoritative —
  WordCard gained `word_pinyin` / `definition` overrides that both note
  types honor, so a wrong CEDICT sense can be fixed by hand

## [0.4.0] - 2026-07-15

Translation state-of-the-art release: findings from the 2026-07-15 audit
(see TODO.md), all action items implemented. Suite 261 → 290 tests.

### Added

- **HY-MT1.5 backend** (`uv sync --extra hymt`): Tencent's WMT25-winning
  translation model line on llama.cpp (GGUF), new top quality tier (95).
  Default 1.8B Q4_K_M (~1GB); 7B build and revision pinning via config/env
- **Batch translation**: example sentences are translated in one
  deduplicated `translate_batch` call — a single CTranslate2 batch for
  NLLB (several times faster than per-sentence calls); failed items degrade
  through the per-item fallback chain
- **Persistent translation cache** (`data/cache/translations.json`): keyed
  by backend + language pair + text, so re-running a book skips
  re-translation and backend upgrades never serve stale output
  (`translation_cache: false` to disable)
- **Translation config keys**: `preferred_backend` (force hymt/nllb/argos/
  cedict), `prefer_offline` (was hardcoded), `translation_cache`, NLLB
  decoding params, model revision pins

### Changed

- NLLB decoding hardened: beam 4, no-repeat-ngram 3, input/decoding length
  caps (NLLB is prone to repetition loops on noisy input)
- Argos init logs the installed zh→en package version (audit trail; Argos
  has no revision pinning)

### Fixed

- The YAML config is now passed through to translation backends —
  documented keys like `nllb_model_repo` previously only worked as env vars

## [0.3.0] - 2026-07-09

Full-repo audit release: every P0-P6 item in TODO.md addressed, one commit
per fix/feature, with regression tests throughout (48 → 223 tests, 85%
coverage).

### Added

- **HSK level filtering** (`--hsk` / `hsk_levels` config): HSK 3.0 word
  lists auto-downloaded and cached; applied before top-N selection
- **TTS word audio** (`--tts`): gTTS MP3s, cached by text hash, bundled
  into the .apkg as media with `[sound:...]` fields
- **Stats export** (`--stats` / `stats_file`): counts, skip reasons, token
  coverage, active backend, and per-card word list as JSON
- **Cloze deletion cards** (`--cloze` / `cloze` config) with their own
  note type and GUID namespace
- **PDF chapter detection**: heuristic splitting on 第X章/节/回 headings
  with front-matter handling and single-chapter fallback
- **Chapter Anki tags** (`chapter::<title>`) for per-chapter filtering
- **Inline word highlighting**: the target word is highlighted inside the
  example sentence (HTML-escaped), front shows just the sentence

### Changed

- EPUB chapters extracted in spine (reading) order; navigation documents
  no longer appear as chapters
- CC-CEDICT duplicate entries resolved by preference (common words over
  proper nouns, then most definitions) instead of last-line-wins
- Word pinyin from CC-CEDICT converted from numbered (`ni3 hao3`) to tone
  marks (`nǐ hǎo`) to match sentence pinyin
- Note GUIDs use the full 128-bit hash (were truncated to 32 bits, risking
  silent overwrites on import; old decks re-import as new notes)
- Example-sentence lookup uses a character-bigram index (~10x faster at
  novel scale, byte-identical results)
- Argos initialization checks for a cached model before touching the
  network; cached/offline runs make no requests
- An explicitly passed `--config` path that doesn't exist is now an error
- Dev dependencies consolidated into the `dev` dependency group

### Fixed

- Page-number lines are actually removed now (line filtering ran after
  newlines had been collapsed, so it never matched)
- Neural backends raise on failure instead of returning the source text,
  so the fallback chain engages and Chinese never appears as its own
  "translation" (failures are also never cached)
- Wheel packaging ships `translate/` and `main.py` (the installed
  `anki-chinese` entry point previously crashed with ImportError)
- `analyze_coverage.py` had unterminated string literals (didn't compile)
  and crashed on Windows cp1252 consoles
- Corrupted CC-CEDICT downloads raise actionable guidance instead of a raw
  `BadGzipFile` traceback
- `.gitignore` covers all of `data/` (NLLB model dir, TTS cache)
- Removed dead code (`translate_with_context`, `get_full_text`)

## [0.2.0] - 2026-02-09

### Added

#### Translation System (Major Feature)
- **Pluggable translation architecture** with multiple backend support
- **Argos Translate backend** - Offline neural machine translation (quality: 80/100)
- **CC-CEDICT backend** - Word-by-word fallback translation (quality: 40/100)
- **TranslationManager** - Automatic backend selection and fallback
- Quality-based backend ranking and selection
- Python version compatibility checking (Argos requires 3.12-3.13)
- Translation documentation (TRANSLATION.md)

#### User Experience
- **Progress bars** using tqdm for long-running operations
  - Card creation progress (shows speed, ETA, percentage)
  - Deck building progress
- **Dark theme** optimized for Anki's charcoal background
  - High contrast text (#e8e8e8 on #2b2b2b)
  - Improved readability for all text elements
  - WCAG AAA accessibility compliance

#### Quality Improvements
- **Sentence pinyin** generation (full sentence with tone marks)
- **Sentence translation** with improved quality
  - Particle handling (的, 了, 着, 过, 吗, 呢)
  - Verb prefix cleaning
  - Better punctuation and capitalization
- **Definition filtering** - Cards only created for words with valid definitions
- **Unit tests** - 24 tests covering core functionality (52% coverage)
- Test coverage tracking with pytest-cov

#### Documentation
- TESTING.md - Comprehensive testing guide
- TRANSLATION.md - Translation backend documentation
- QUICKSTART.md - Step-by-step usage guide
- Recommended deck sizes and coverage goals
- Example workflows for different use cases

### Changed
- Card template now hides pinyin on front (revealed on back)
- Improved translation quality with particle filtering
- Updated card CSS for dark theme compatibility
- CC-CEDICT integration now auto-downloads on first run

### Fixed
- Windows console UTF-8 encoding for Chinese characters
- Definition validation to prevent empty cards
- Character name filtering (excluded from decks)

## [0.1.0] - 2026-02-09

### Added

#### Core Features
- **EPUB extraction** with chapter detection (ebooklib + BeautifulSoup4)
- **PDF extraction** (PyPDF2)
- **Text processing**
  - Chinese tokenization using jieba
  - Word frequency analysis
  - Multi-character word filtering (2+ characters)
  - Top-N word selection by frequency
- **Dictionary integration**
  - CC-CEDICT auto-download and caching
  - Word definition lookup
  - Pinyin conversion (pypinyin with CEDICT fallback)
- **Anki deck generation**
  - Beautiful card templates with CSS
  - Deterministic note IDs (hash-based)
  - Chapter tagging
- **CLI interface** with argparse
- **Configuration** support (YAML)

#### Project Setup
- uv-based dependency management (Python 3.9+)
- Modular project structure
- pyproject.toml for package management
- Comprehensive documentation (README.md, CLAUDE.md)

### Technical Details

#### Dependencies (pyproject.toml)

**Core:**
- jieba >= 0.42.1 (Chinese tokenization)
- pypinyin >= 0.51.0 (Pinyin conversion)
- genanki >= 0.13.0 (Anki deck generation)
- ebooklib >= 0.18 (EPUB parsing)
- beautifulsoup4 >= 4.12.0 (HTML parsing)
- PyPDF2 >= 3.0.1 (PDF extraction)
- pyyaml >= 6.0.1 (Configuration)
- requests >= 2.31.0 (Downloads)
- argostranslate >= 1.11.0 (Neural MT)
- tqdm >= 4.67.3 (Progress bars)

**Dev:**
- pytest >= 8.4.2 (Testing)
- pytest-cov >= 7.0.0 (Coverage)
- black >= 23.0.0 (Formatting)
- ruff >= 0.1.0 (Linting)

## Implementation Status

### ✅ Production Ready

- [x] EPUB extraction with chapters
- [x] PDF extraction (basic)
- [x] Text cleaning and sentence splitting
- [x] Chinese tokenization (jieba)
- [x] Word frequency analysis
- [x] Multi-character word filtering
- [x] Top-N word selection
- [x] CC-CEDICT integration
- [x] Pinyin generation (word + sentence)
- [x] Sentence translation (neural MT + fallback)
- [x] Example sentence matching
- [x] Definition validation
- [x] Anki deck generation
- [x] Dark theme card templates
- [x] Progress bars
- [x] Unit tests (24 tests)
- [x] CLI interface
- [x] Configuration support

### ⏳ Planned / Not Implemented

- [ ] HSK level filtering (needs HSK word lists)
- [ ] TTS audio generation with gTTS
- [ ] Statistics export (JSON/CSV)
- [ ] Cloze deletion cards
- [ ] Advanced chapter detection
- [ ] Translation caching
- [ ] Batch translation optimization

## Performance Benchmarks

### 三体全集 (The Three-Body Problem)

**Input:**
- File size: 1.9MB EPUB
- Chapters: 87
- Sentences: 23,844
- Total tokens: 457,776
- Unique words: 30,328
- Multi-character words: 28,723

**Processing Times:**
- Extraction & cleaning: ~5 seconds
- Tokenization: ~3 seconds
- Word selection: <1 second
- Card creation (300 words): ~10 seconds
- Card creation (3000 words): ~90 seconds
- Deck building: <1 second

**Output (90% coverage, 3000 words, min-freq 5):**
- Cards created: 2,546
- File size: 1.1MB .apkg
- Coverage: ~90% of book content

**Translation Speed:**
- Argos Translate: ~30-50 words/second
- CC-CEDICT: ~100+ words/second (faster but lower quality)

## Coverage Analysis

Word frequency follows Zipf's law distribution:

| Cards | Coverage | Use Case |
|-------|----------|----------|
| 100 | ~45% | Quick vocabulary boost |
| 300 | ~60% | Common vocabulary |
| 500 | ~68% | Intermediate learners |
| 1,000 | ~77% | Advanced learners |
| 2,000 | ~85% | Comprehensive study |
| 3,000 | ~90% | Near-complete coverage (recommended) |
| 5,000 | ~94% | Exhaustive study |

## Breaking Changes

None yet (initial release).

## Migration Guide

N/A (initial release).

## Known Issues

### Python 3.14+ Compatibility
- **Issue:** Argos Translate not compatible with Python 3.14+
- **Cause:** Pydantic v1 limitation in argostranslate dependencies
- **Workaround:** Use Python 3.12 or 3.13, or use CC-CEDICT fallback (automatic)
- **Impact:** Translation quality lower with fallback (acceptable for learning)

### Progress Bar Display on Windows
- **Issue:** Progress bars may not display correctly in some terminals
- **Workaround:** Use Windows Terminal or another modern terminal emulator
- **Impact:** Minor visual glitch, functionality unaffected

## Future Roadmap

### v0.3.0 (Planned)
- [ ] HSK level filtering
- [ ] Translation caching for performance
- [ ] Google Translate API backend
- [ ] Better chapter detection

### v0.4.0 (Planned)
- [ ] TTS audio generation
- [ ] Cloze deletion cards
- [ ] Statistics export
- [ ] Local LLM translation backend (ollama)

### v1.0.0 (Planned)
- [ ] Stable API
- [ ] Complete test coverage (80%+)
- [ ] All core features implemented
- [ ] Production-tested with multiple books

## Contributors

- Claude Sonnet 4.5 (AI Assistant)
- Project initiated: 2026-02-09

---

For detailed documentation, see:
- [README.md](README.md) - Installation and quick start
- [CLAUDE.md](CLAUDE.md) - Project reference
- [TESTING.md](TESTING.md) - Testing guide
- [TRANSLATION.md](TRANSLATION.md) - Translation backends
- [QUICKSTART.md](QUICKSTART.md) - Step-by-step usage
