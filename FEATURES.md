# Features & Implementation Status

Detailed feature documentation for the Anki Chinese Deck Builder.

## Current Implementation Status

### ✅ Core Features (Production Ready)

**Text Extraction**:
- EPUB extraction with chapter detection (ebooklib + BeautifulSoup4)
- PDF extraction (PyPDF2)
- Chapter tagging for cards
- Automatic text normalization

**Text Processing**:
- Text cleaning and sentence splitting
- Chinese tokenization (jieba)
- Word frequency analysis across entire book
- Multi-character word filtering (2+ chars)
- Top-N word selection by frequency
- Sentence-word matching for context

**Dictionary & Pinyin**:
- CC-CEDICT integration (auto-download and cache)
- Word definition lookup (first definition)
- Definition validation (skip words without definitions)
- Word pinyin: CC-CEDICT primary, pypinyin fallback
- Sentence pinyin: Full sentence with tone marks
- Deterministic dictionary caching

**Translation**:
- Pluggable translation backend system
- Argos Translate: Neural MT (Python 3.12-3.13)
- CC-CEDICT: Word-by-word fallback (all Python versions)
- Automatic backend selection and fallback
- Quality-based ranking (Argos 80/100, CEDICT 40/100)
- Improved word-by-word quality:
  - Removes grammatical particles (的, 了, 着, 过)
  - Strips "to" prefix from verbs
  - Handles question particles (吗, 呢 → "?")
  - Punctuation and capitalization cleanup

**Card Generation**:
- Anki deck generation (genanki)
- Beautiful card templates with CSS styling
- Front: Sentence + highlighted word (pinyin hidden)
- Back: Sentence pinyin, word pinyin, definition, translation
- Deterministic note IDs (hash-based, no duplicates)
- Chapter tags included in cards
- Automatic output directory creation

**Quality & Testing**:
- 24 unit tests covering core modules
- Test coverage: 52% overall
  - process/word_selector.py: 95%
  - process/cedict_loader.py: 59%
  - anki/deck_builder.py: 66%
- Definition validation
- Windows UTF-8 console encoding
- Offline operation after initial CEDICT download

**Configuration & CLI**:
- YAML configuration support
- CLI with argparse
- uv-based dependency management
- Progress bars (tqdm) for long operations
- Configurable word selection and filtering

### ⏳ Pending Features

- HSK level filtering (needs HSK word lists)
- TTS audio generation with gTTS
- Statistics export (JSON/CSV)
- Cloze deletion cards
- Advanced chapter detection
- Translation caching
- Known words filtering

### ❌ Future Extensions (Optional)

- Sentence difficulty scoring
- Skip known words via frequency lists
- Per-chapter decks
- Pleco export
- Better sense disambiguation
- Traditional Chinese support
- Online translation APIs (Google, DeepL)
- LLM-based translation

## Translation Architecture

### Backend System

**Abstract Base Class** (`TranslationBackend`):
- Pluggable architecture
- Quality scoring (0-100)
- Automatic fallback on failure
- Extensible for future backends

**Current Backends**:

1. **Argos Translate** (Neural MT)
   - Quality: 80/100
   - Python: 3.12-3.13 only (Pydantic v1 limitation)
   - Fully offline after model download
   - Natural, grammatical translations
   - Dependencies: PyTorch, transformers (~150MB models)
   - Speed: ~30-50 cards/second

2. **CC-CEDICT Word-by-Word** (Fallback)
   - Quality: 40/100
   - Python: All versions (3.9+)
   - Fast, minimal dependencies
   - Acceptable quality for beginners
   - Improvements: particle handling, cleanup
   - Speed: ~100+ cards/second

**Future Backend Support**:
- Online APIs: Google Translate, DeepL, Azure
- LLM-based: GPT-4, Claude, local LLMs
- Hybrid approaches
- Custom translation models

**Module Structure**:
```
translate/
├── base.py              # Abstract base class
├── argos_backend.py     # Argos Translate implementation
├── cedict_backend.py    # CC-CEDICT fallback
└── manager.py           # Translation orchestrator
```

### Python Version Compatibility

- **Core project**: Python 3.9+
- **Argos Translate**: Python 3.12-3.13 only
- **CC-CEDICT fallback**: Works with all Python versions

**Python 3.14+ behavior**:
- Argos Translate skipped (not compatible)
- Automatic fallback to CC-CEDICT
- Warning message displayed
- Deck generation continues normally

See **TRANSLATION.md** for detailed documentation.

## Performance Metrics

### Typical Processing Times

**Book Sizes**:
- Small novel (500KB): ~10 seconds
- Medium novel (1-2MB): ~30 seconds
- Large novel (3-5MB): ~60 seconds

**Translation Speed**:
- Argos Translate: +0.1s per card (~30-50 cards/sec)
- CC-CEDICT: +0.01s per card (~100+ cards/sec)

**Example** (三体全集, 1.9MB EPUB):
- Chapters: 87
- Sentences: 23,844
- Total tokens: 457,776
- Unique words: 30,328
- Multi-char words: 28,723
- Processing time: ~30-45 seconds
- Output: 145KB .apkg (270 cards from 300 requested)

### Memory Usage

- Base: ~50MB
- With Argos Translate: ~200MB
- With large EPUB: ~100MB
- Peak during processing: ~250-300MB

### Output File Sizes

- 100 cards: ~20-30KB .apkg
- 300 cards: ~60-80KB .apkg
- 1,000 cards: ~150-200KB .apkg
- 3,000 cards: ~300-400KB .apkg

## Recommended Settings

### Coverage Goals (Based on Zipf's Law)

| Target Coverage | Cards | Min Freq | Use Case |
|----------------|-------|----------|----------|
| 45% | 100 | 10 | Quick vocabulary boost |
| 60% | 300 | 5 | Common vocabulary |
| 70% | 500 | 5 | Intermediate learners |
| 80% | 1,000 | 3 | Advanced learners |
| 85% | 2,000 | 3 | Comprehensive study |
| **90%** ⭐ | **3,000** | **5** | **Near-complete coverage** |
| 94% | 5,000 | 2 | Exhaustive study |

### Recommended: 90% Coverage

**Command**:
```bash
uv run python main.py \
  --input book.epub \
  --deck "Book Name - 90% Coverage" \
  --top-words 3000 \
  --min-freq 5
```

**Results**:
- Actual cards: ~2,500-2,700 (some filtered)
- Coverage: ~90% of book content
- Filters out: Character names, rare words, typos
- Focus: High-frequency, useful vocabulary

### Study Time Estimates

| Cards | Minutes/Day | Days to Complete | Total Hours |
|-------|-------------|------------------|-------------|
| 100 | 10 | 10 | 1.7 |
| 300 | 15 | 20 | 5 |
| 500 | 20 | 25 | 8 |
| 1,000 | 20 | 50 | 16 |
| 2,500 | 25 | 100 | 42 |
| 3,000 | 25 | 120 | 50 |

*(Assumes 20 seconds per card review, 25 new cards/day)*

### Best Practices

**Start Small**:
- Begin with 100-300 words to test
- Verify Anki import works
- Check card quality and formatting

**Iterate**:
- Generate small deck first (`--top-words 50`)
- Review in Anki
- Adjust `min-freq` if needed
- Generate full deck

**Quality Over Quantity**:
- `min-freq 5` is sweet spot for novels
- Higher = more common words only
- Lower = includes more rare words

**Use Chapter Tags**:
- Cards automatically tagged with chapters
- Filter by chapter in Anki
- Study chronologically if desired

## Testing & Quality Assurance

### Unit Tests

**Coverage**: 24 tests, 52% overall coverage

**Test Modules**:
- `test_word_selector.py`: 9 tests (95% coverage)
- `test_cedict_loader.py`: 8 tests (59% coverage)
- `test_deck_builder.py`: 7 tests (66% coverage)

**Run tests**:
```bash
uv run pytest tests/ -v
uv run pytest tests/ --cov=. --cov-report=term-missing
```

### Quality Checks

- ✅ Definition validation (cards only for words with CEDICT definitions)
- ✅ No duplicate notes (deterministic GUID generation)
- ✅ UTF-8 console output (Windows compatibility)
- ✅ Offline operation (works without internet after CEDICT download)
- ✅ Deterministic output (same input → same deck)

## Known Limitations

### Translation Quality

- Word-by-word translation (not grammatically perfect)
- No context-aware grammar transformations
- Particles removed (may lose nuance)
- Approximation for understanding, not literary translation
- *Mitigation*: Use Argos Translate (Python 3.12-3.13) for neural MT

### Dictionary Coverage

- Only simplified Chinese (no traditional)
- CC-CEDICT may not include:
  - Character names from novels
  - Very new slang/terminology
  - Specialized technical terms
  - Regional dialect words
- *Result*: These words automatically filtered out

### PDF Extraction

- Basic text extraction (no OCR)
- Chapter detection limited compared to EPUB
- Some PDFs may not extract cleanly
- *Recommendation*: Use EPUB when available

## Dependencies

### Core Dependencies

```toml
jieba >= 0.42.1              # Chinese tokenization
pypinyin >= 0.51.0           # Pinyin generation
genanki >= 0.13.0            # Anki deck creation
ebooklib >= 0.18             # EPUB extraction
beautifulsoup4 >= 4.12.0     # HTML parsing
PyPDF2 >= 3.0.1              # PDF extraction
pyyaml >= 6.0.1              # Config files
requests >= 2.31.0           # CC-CEDICT download
tqdm >= 4.66.0               # Progress bars
```

### Optional Dependencies

```toml
argostranslate >= 1.9.0      # Neural MT (Python 3.12-3.13 only)
gtts >= 2.5.0                # TTS (future)
```

### Development Dependencies

```toml
pytest >= 8.4.2              # Testing
pytest-cov >= 7.0.0          # Coverage
black >= 23.0.0              # Formatting
ruff >= 0.1.0                # Linting
```

## User Experience Improvements

### Progress Bars (tqdm)

**Card Creation Progress**:
- Shows: percentage, visual bar, count, time, speed
- Example: `Creating cards: 42%|████▎ | 1260/3000 [00:45<01:02, 28.0word/s]`
- This is the slowest step (neural translation)
- Speed: ~30-50 words/second with Argos Translate

**Deck Building Progress**:
- Shows: progress through Anki note creation
- Example: `Building deck: 100%|██████████| 2546/2546 [00:00<00:00, 52341card/s]`
- Very fast (no translation, just object creation)
- Speed: 50k+ cards/second

**Benefits**:
- User knows process is running (not frozen)
- Accurate time estimates (ETA)
- Processing speed visibility
- Better UX for large decks (1000+ cards)

## Recent Updates

### 2026-02-09: Translation & Quality Improvements

**Phase 1: Initial Setup**
- ✅ Created project structure
- ✅ Implemented EPUB/PDF extraction
- ✅ Added jieba tokenization
- ✅ CC-CEDICT integration
- ✅ Basic word selection

**Phase 2: Quality Improvements**
- ✅ Added definition filtering
- ✅ Sentence pinyin generation
- ✅ Word-by-word translation (CEDICT)
- ✅ Improved translation quality (particle handling)
- ✅ Unit tests (24 tests)
- ✅ Windows UTF-8 encoding fix
- ✅ Test coverage tracking (52%)

**Phase 3: Translation Architecture**
- ✅ Pluggable backend system
- ✅ Argos Translate integration (neural MT)
- ✅ Quality-based backend selection
- ✅ Automatic fallback
- ✅ Python 3.13 compatibility testing
- ✅ Translation documentation (TRANSLATION.md)

**Phase 4: User Experience**
- ✅ Progress bars (tqdm) for card creation
- ✅ Progress bars for deck building
- ✅ Processing speed indicators
- ✅ Accurate ETA estimates

**Current State**: Fully functional with high-quality neural MT translations (Python 3.13) or reliable word-by-word fallback (any Python version).

## Card Fields Reference

Generated card fields (genanki model):
- **Word**: Chinese characters (target word)
- **Sentence**: Chinese characters (example sentence)
- **SentencePinyin**: Full sentence with tone marks
- **Pinyin**: Word-level pinyin with tone marks
- **Definition**: English definition from CC-CEDICT
- **SentenceTranslation**: Word-by-word or neural MT
- **Audio**: Placeholder (empty for now, future TTS)
- **Chapter**: Chapter name from book structure

## Example Workflows

### Quick Test (50 cards)
```bash
uv run python main.py \
  --input book.epub \
  --deck "Test" \
  --top-words 50 \
  --min-freq 2
```

### Standard Novel (90% coverage)
```bash
uv run python main.py \
  --input book.epub \
  --deck "Novel Name" \
  --top-words 3000 \
  --min-freq 5
```

### Beginner Friendly (common words only)
```bash
uv run python main.py \
  --input book.epub \
  --deck "Beginner" \
  --top-words 300 \
  --min-freq 10
```

### Advanced/Exhaustive
```bash
uv run python main.py \
  --input book.epub \
  --deck "Complete" \
  --top-words 5000 \
  --min-freq 2
```

## Translation Backend Selection

### Current Status (Python 3.13)
- ✅ Argos Translate (Neural MT) - Active
- ✅ CC-CEDICT (Fallback) - Available

### Python 3.14+ Users
- ⚠️  Argos Translate - Not compatible
- ✅ CC-CEDICT (Fallback) - Automatic

### Production Recommendations

**For Best Translation Quality**:
- Use Python 3.12 or 3.13
- Argos Translate provides neural MT
- Translations are natural and grammatical

**For Maximum Compatibility**:
- Any Python version works (3.9+)
- CC-CEDICT fallback is reliable
- Translations are acceptable for learning
