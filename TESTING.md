# Testing Guide

## Running Tests

### Quick Start

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_word_selector.py -v

# Run specific test class
uv run pytest tests/test_word_selector.py::TestWordSelector -v

# Run specific test
uv run pytest tests/test_word_selector.py::TestWordSelector::test_create_word_cards_with_cedict -v
```

### Test Output Options

```bash
# Verbose output with test names
uv run pytest tests/ -v

# Show print statements
uv run pytest tests/ -v -s

# Stop on first failure
uv run pytest tests/ -x

# Show locals in tracebacks
uv run pytest tests/ -v -l

# Run tests matching pattern
uv run pytest tests/ -k "cedict" -v
```

## Test Coverage

### Install Coverage Tools

Coverage tracking is included with pytest:

```bash
# Add pytest-cov for coverage reports
uv add --dev pytest-cov
```

### Generate Coverage Reports

```bash
# Run tests with coverage
uv run pytest tests/ --cov=. --cov-report=term

# Generate HTML coverage report
uv run pytest tests/ --cov=. --cov-report=html

# View HTML report (opens in browser)
# Look in htmlcov/index.html

# Generate coverage report with missing lines
uv run pytest tests/ --cov=. --cov-report=term-missing

# Only show coverage for specific modules
uv run pytest tests/ --cov=process --cov=anki --cov-report=term-missing
```

### Coverage Status

**Total:** 223 tests, 85% overall coverage (run the coverage command above
for the current per-module breakdown). Every module has direct tests: word
selection, CEDICT loading, deck building (regular + cloze), text cleaning,
tokenization, pinyin conversion, EPUB/PDF extraction, HSK filtering, TTS,
translation backends and manager fallback, CLI/config plumbing, plus
repo-health checks (every file compiles, wheel config ships all packages).

### Coverage Goals

- **Critical Path:** 80%+ coverage (word selection, deck building, dictionary)
- **Utilities:** 70%+ coverage
- **Overall Project:** 75%+ coverage

## Test Structure

### Current Test Files

```
tests/
├── __init__.py
├── test_word_selector.py         # Word selection, sentence index, card creation
├── test_cedict_loader.py         # Dictionary parsing, duplicate preference, download errors
├── test_deck_builder.py          # Anki notes, GUIDs, highlighting, chapter tags
├── test_cloze_cards.py           # Cloze note type and deck building
├── test_text_cleaner.py          # Cleaning, page numbers, sentence splitting
├── test_tokenizer.py             # jieba tokenization and frequency analysis
├── test_pinyin_converter.py      # Tone-mark conversion (incl. CEDICT numbered pinyin)
├── test_epub_extractor.py        # EPUB round-trip, spine order
├── test_pdf_extractor.py         # PDF chapter-heading heuristics
├── test_hsk_filter.py            # HSK level parsing, lists, filtering
├── test_tts.py                   # gTTS generation, caching, [sound:] fields
├── test_translation_manager.py   # Backend fallback and cache semantics
├── test_argos_backend.py         # Offline init with cached model
├── test_nllb_backend.py          # NLLB wiring and config
├── test_sentence_translator.py   # Word-by-word translation quality
├── test_main.py                  # Config loading, settings precedence, stats export
└── test_repo_health.py           # Every file compiles; wheel ships all packages
```

### Test Organization

Each test file follows this structure:

```python
"""Module description."""

import pytest
from module import function_to_test


class TestModuleName:
    """Test class for related functionality."""

    def test_specific_behavior(self):
        """Test description."""
        # Arrange
        input_data = ...

        # Act
        result = function_to_test(input_data)

        # Assert
        assert result == expected
```

## Writing New Tests

### Test Naming Conventions

- **File:** `test_<module_name>.py`
- **Class:** `TestModuleName`
- **Method:** `test_<specific_behavior>`

### Example Test

```python
def test_word_selection_filters_by_frequency(self):
    """Test that words below min frequency are filtered out."""
    # Arrange
    word_freq = Counter({"你好": 10, "世界": 2, "中国": 1})

    # Act
    selected = select_top_words(word_freq, top_n=10, min_freq=3)

    # Assert
    assert len(selected) == 1
    assert "你好" in selected
```

### What to Test

✅ **DO Test:**
- Core business logic (word selection, frequency analysis)
- Data transformations (CEDICT parsing, pinyin conversion)
- Edge cases (empty input, missing data, invalid formats)
- Error handling (file not found, malformed data)
- Output validation (card structure, note IDs)

❌ **DON'T Test:**
- External libraries (jieba, pypinyin, genanki)
- Simple getters/setters
- Print statements
- File I/O details (use mocks/fixtures)

## Test Fixtures & Mocking

### Creating Test Data

```python
@pytest.fixture
def sample_cedict():
    """Fixture providing sample CEDICT entries."""
    return {
        "你好": DictEntry("你好", "你好", "nǐ hǎo", ["hello"]),
        "世界": DictEntry("世界", "世界", "shì jiè", ["world"]),
    }

def test_with_fixture(sample_cedict):
    """Test using fixture."""
    assert "你好" in sample_cedict
```

### Mocking External Calls

```python
from unittest.mock import Mock, patch

@patch('process.cedict_loader.download_cedict')
def test_cedict_loading(mock_download):
    """Test CEDICT loading without actual download."""
    mock_download.return_value = Path("fake/cedict.txt")
    # Test logic here
```

## Continuous Testing

### Watch Mode

```bash
# Install pytest-watch
uv add --dev pytest-watch

# Run tests automatically on file changes
uv run ptw tests/
```

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
uv run pytest tests/ --tb=short || exit 1
```

## Debugging Failed Tests

### Show Full Output

```bash
# Show all print statements and full tracebacks
uv run pytest tests/ -vv -s --tb=long

# Drop into debugger on failure
uv run pytest tests/ --pdb
```

### Common Issues

**Issue:** Test passes locally but fails in CI
- **Fix:** Ensure deterministic behavior, check file paths

**Issue:** Import errors in tests
- **Fix:** Check PYTHONPATH, ensure `__init__.py` files exist

**Issue:** Flaky tests (pass/fail randomly)
- **Fix:** Remove dependencies on timing, order, or external state

## Test Coverage Workflow

### Weekly Coverage Check

```bash
# Generate coverage report
uv run pytest tests/ --cov=. --cov-report=html --cov-report=term

# Review htmlcov/index.html
# Identify modules with <75% coverage
# Write tests for uncovered code
```

### Coverage Badge

Add to README.md:

```markdown
![Coverage](https://img.shields.io/badge/coverage-75%25-yellow)
```

## TODO: Tests to Add

- [ ] Integration test for the full pipeline (EPUB → deck) using a generated
      fixture book and a stubbed CEDICT (avoid network in tests)
- [ ] `test_chinese_utils.py` - direct tests for character helpers (currently
      covered indirectly via text_cleaner/tokenizer)

## Performance Testing

### Benchmark Tests

```python
import time

def test_large_deck_performance():
    """Test deck generation with 1000 cards."""
    start = time.time()
    # Generate deck
    elapsed = time.time() - start
    assert elapsed < 30  # Should complete in <30s
```

### Memory Testing

```python
import tracemalloc

def test_memory_usage():
    """Test memory usage stays reasonable."""
    tracemalloc.start()
    # Run operation
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < 500 * 1024 * 1024  # <500MB
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**Last Updated:** 2026-07-09
**Current Test Count:** 223 tests
**Current Coverage:** 85% overall
**Target Coverage:** 75%+ (met)
