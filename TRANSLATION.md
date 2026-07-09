# Translation System

## Overview

The Anki Chinese Deck Builder uses a **pluggable translation architecture** that supports multiple translation backends with automatic fallback.

## Architecture

```
translate/
├── base.py              # Abstract base class
├── nllb_backend.py      # NLLB-200 on CTranslate2 (opt-in, highest quality)
├── argos_backend.py     # Argos Translate (offline neural MT, default)
├── cedict_backend.py    # CC-CEDICT word-by-word (fallback)
└── manager.py           # Translation manager (orchestrator)
```

**Failure semantics:** a backend that cannot translate raises; it never
returns the source text. The manager catches the error, tries the next
backend by quality score, and never caches failures — so a transient error
can't poison cards with untranslated Chinese.

## Available Backends

### 0. NLLB-200 on CTranslate2 (Offline Neural MT) ⭐ Highest quality

**Quality Score:** 90/100

**Status:** Opt-in — install with `uv sync --extra nllb`

**Pros:**
- ✅ Best zh→en quality of the offline backends
- ✅ Fully offline after the one-time model download (~1GB distilled-600M)
- ✅ Runs on the same CTranslate2 engine Argos already uses (no PyTorch at inference)
- ✅ Model/tokenizer overridable via config keys `nllb_model_repo` /
  `nllb_tokenizer_repo` or env `NLLB_CT2_MODEL` / `NLLB_TOKENIZER`

**Cons:**
- ⚠️ Large first-run download
- ⚠️ Heavier optional dependencies (transformers, huggingface_hub)

### 1. Argos Translate (Offline Neural MT) — Default

**Quality Score:** 80/100

**Status:** Offline, neural machine translation

**Pros:**
- ✅ High-quality neural MT
- ✅ Fully offline after initial model download
- ✅ Better grammar than word-by-word
- ✅ Contextual understanding

**Cons:**
- ⚠️ Requires Python 3.9-3.13 (not compatible with 3.14+; the project caps requires-python accordingly)
- ⚠️ Large dependencies (~150MB with PyTorch)
- ⚠️ Slower than word-by-word

**Installation:**
```bash
# Already included in dependencies
uv sync
```

**Python Version Requirement:**
```bash
# Check your Python version
uv run python --version

# If using Python 3.14+, Argos will not work
# Use uv with Python 3.13:
uv python install 3.13
uv venv --python 3.13
uv sync
```

### 2. CC-CEDICT Word-by-Word (Fallback)

**Quality Score:** 40/100

**Status:** Always available, offline

**Pros:**
- ✅ Always works (fallback)
- ✅ Fast
- ✅ No extra dependencies
- ✅ Works with any Python version

**Cons:**
- ⚠️ Lower quality (word-by-word)
- ⚠️ No grammar
- ⚠️ Particle handling imperfect

**Example Translations:**

| Chinese | Argos Translate | CC-CEDICT |
|---------|----------------|-----------|
| 他说话了 | He spoke | He speak talk |
| 她很漂亮 | She is very beautiful | She very beautiful |
| 你好吗？ | How are you? | You good? |

## Adding New Backends

### Future Backend Examples

The architecture supports easy addition of new backends:

**Online API Backends:**
- Google Translate API
- DeepL API
- Azure Translator

**LLM Backends:**
- OpenAI GPT-4 (via API)
- Claude (via API)
- Local LLMs (via llama.cpp, ollama)

### Creating a New Backend

1. **Create backend class** inheriting from `TranslationBackend`:

```python
from translate.base import TranslationBackend

class MyBackend(TranslationBackend):
    def initialize(self) -> bool:
        # Setup code
        return True

    def is_available(self) -> bool:
        # Check if backend can be used
        return True

    def translate(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> str:
        # Translation logic
        return translated_text

    def get_name(self) -> str:
        return "My Translation Backend"

    def requires_internet(self) -> bool:
        return False  # or True for online backends

    def get_quality_score(self) -> int:
        return 70  # 0-100, higher = better quality
```

2. **Add to translation manager:**

```python
from translate.manager import TranslationManager
from my_backend import MyBackend

manager = TranslationManager(backends=[
    MyBackend(),
    ArgosTranslateBackend(),
    CEDICTBackend(),
])
```

## Usage

### Automatic (Recommended)

The translation manager automatically selects the best available backend:

```bash
# Just run normally - translation is automatic
uv run python main.py --input book.epub --deck "My Deck"
```

### Backend Selection Priority

1. **Quality Score** - Higher quality backends tried first
2. **Availability** - Backend must be initialized successfully
3. **Fallback** - If primary fails, tries next backend

### Configuration

Future: Add config options in `config.yaml`:

```yaml
translation:
  preferred_backend: "argos"  # argos, cedict, google, deepl, llm
  fallback_enabled: true
  timeout: 30  # seconds
  cache_translations: true
```

## Troubleshooting

### Argos Translate Not Working

**Error:** `unable to infer type for attribute "REGEX"`

**Cause:** Python 3.14+ compatibility issue

**Solution:**
```bash
# Option 1: Use Python 3.13
uv python install 3.13
uv venv --python 3.13
uv sync

# Option 2: Use CC-CEDICT fallback (automatic)
# The system will fall back automatically if Argos fails
```

### Slow Translation

**Issue:** Argos Translate is slow on first card

**Cause:** Model loading

**Solution:** Normal - subsequent translations are faster

### Low Quality Translations

**Issue:** Translations seem word-by-word

**Cause:** Likely using CC-CEDICT fallback

**Check:** Look for this in output:
```
→ Using: CC-CEDICT (Word-by-word)
```

**Solution:** Install Argos Translate with Python 3.13

## Performance

### Translation Speed

| Backend | First Translation | Subsequent |
|---------|------------------|------------|
| Argos Translate | ~2s (model load) | ~0.1s/sentence |
| CC-CEDICT | ~0.01s | ~0.01s/sentence |

### Quality Comparison

**Input:** 他看着她，慢慢地说。

| Backend | Translation |
|---------|-------------|
| Argos | He looked at her and spoke slowly. |
| CC-CEDICT | He look at she, slowly say. |

## Roadmap

### Planned Backends

- [ ] **Google Translate API** (online, high quality)
- [ ] **DeepL API** (online, highest quality)
- [ ] **Local LLM** (ollama/llama.cpp, offline, very high quality)
- [ ] **OpenAI GPT-4** (online API, highest quality, costs money)
- [ ] **Azure Translator** (online, high quality)

### Features

- [x] Translation caching (repeated sentences translate once per run)
- [ ] Batch translation (translate multiple sentences at once)
- [ ] Translation quality scoring
- [ ] A/B testing between backends
- [ ] User-selected backend preference in config

## Contributing

To add a new backend:

1. Create `translate/your_backend.py`
2. Inherit from `TranslationBackend`
3. Implement required methods
4. Add tests in `tests/test_translation.py`
5. Update this documentation
6. Submit PR

---

**Last Updated:** 2026-07-09
**Python Compatibility:** 3.9-3.13 (project caps requires-python below 3.14 for Argos)
**Status:** Stable — NLLB (opt-in) > Argos (default) > CC-CEDICT (fallback)
