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

### Coverage Targets

Current test coverage by module:

| Module | Coverage | Tests | Status |
|--------|----------|-------|--------|
| `process/word_selector.py` | ~95% | 9 tests | ✅ Excellent |
| `process/cedict_loader.py` | ~90% | 8 tests | ✅ Excellent |
| `anki/deck_builder.py` | ~85% | 7 tests | ✅ Good |
| `anki/templates.py` | ~60% | 1 test | ⚠️ Needs more |
| `extract/epub_extractor.py` | 0% | 0 tests | ❌ TODO |
| `extract/pdf_extractor.py` | 0% | 0 tests | ❌ TODO |
| `process/text_cleaner.py` | 0% | 0 tests | ❌ TODO |
| `process/tokenizer.py` | 0% | 0 tests | ❌ TODO |
| `process/pinyin_converter.py` | 0% | 0 tests | ❌ TODO |
| `utils/chinese_utils.py` | 0% | 0 tests | ❌ TODO |
| `utils/file_utils.py` | 0% | 0 tests | ❌ TODO |

**Total:** 24 tests covering 3 core modules

### Coverage Goals

- **Critical Path:** 80%+ coverage (word selection, deck building, dictionary)
- **Utilities:** 70%+ coverage
- **Overall Project:** 75%+ coverage

## Test Structure

### Current Test Files

```
tests/
├── __init__.py
├── test_word_selector.py      # Word selection & card creation (9 tests)
├── test_cedict_loader.py       # Dictionary parsing (8 tests)
└── test_deck_builder.py        # Anki deck generation (7 tests)
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

### High Priority

- [ ] `test_text_cleaner.py` - Test text cleaning and sentence splitting
- [ ] `test_tokenizer.py` - Test jieba tokenization and frequency analysis
- [ ] `test_chinese_utils.py` - Test Chinese character detection
- [ ] `test_epub_extractor.py` - Test EPUB chapter extraction

### Medium Priority

- [ ] `test_pinyin_converter.py` - Test pinyin conversion
- [ ] `test_file_utils.py` - Test directory creation and caching
- [ ] Integration tests for full pipeline (EPUB → Deck)

### Low Priority

- [ ] `test_pdf_extractor.py` - Test PDF extraction
- [ ] `test_hsk_filter.py` - Test HSK filtering (when implemented)
- [ ] `test_gtts_generator.py` - Test TTS (when implemented)

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

**Last Updated:** 2026-02-09
**Current Test Count:** 24 tests
**Current Coverage:** ~35% (3/11 core modules)
**Target Coverage:** 75%+
