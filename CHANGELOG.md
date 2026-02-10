# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
