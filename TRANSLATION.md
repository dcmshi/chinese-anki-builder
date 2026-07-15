# Translation System

## Overview

The Anki Chinese Deck Builder uses a **pluggable translation architecture** that supports multiple translation backends with automatic fallback.

## Architecture

```
translate/
├── base.py              # Abstract base class (translate + translate_batch)
├── hymt_backend.py      # HY-MT1.5 on llama.cpp (opt-in, highest quality)
├── nllb_backend.py      # NLLB-200 on CTranslate2 (opt-in)
├── argos_backend.py     # Argos Translate (offline neural MT, default)
├── cedict_backend.py    # CC-CEDICT word-by-word (fallback)
└── manager.py           # Translation manager (orchestrator)
```

**Failure semantics:** a backend that cannot translate raises; it never
returns the source text. The manager catches the error, tries the next
backend by quality score, and never caches failures — so a transient error
can't poison cards with untranslated Chinese. The batch path degrades the
same way: items a batch fails on go through the per-item fallback chain.

**Batching:** the pipeline collects every selected example sentence and
translates them in one `translate_batch` call. The manager deduplicates,
serves cache hits, and hands the rest to the active backend — a single
CTranslate2 batch call for NLLB (several times faster than per-sentence
calls on CPU), a sequential loop for backends without a native batch API.

**Persistent cache:** translations are cached across runs in
`data/cache/translations.json`, keyed by backend + language pair + text, so
re-running the same book skips re-translation and installing a better
backend never serves the old backend's output. Disable with
`translation_cache: false`.

## Available Backends

### 0. HY-MT1.5 on llama.cpp (Offline Neural MT) ⭐ Highest quality

**Quality Score:** 95/100

**Status:** Opt-in — install with `uv sync --extra hymt`

Tencent's Hunyuan-MT-7B won WMT25 (first place in 30/31 language pairs);
HY-MT1.5 (open-sourced 2025-12-30) is its successor and the current open
offline state of the art for zh→en. Default here is the official 1.8B GGUF
build (Q4_K_M, ~1GB) — the same footprint class as NLLB distilled-600M with
far better literary Chinese.

**Pros:**
- ✅ Best zh→en quality of any offline backend (WMT25-winning model line)
- ✅ zh-centric training (Tencent), strong on idioms and dialogue
- ✅ Fully offline after the one-time GGUF download
- ✅ 7B build available for more RAM: `hymt_model_repo: tencent/HY-MT1.5-7B-GGUF`
- ✅ Overridable via config `hymt_model_repo` / `hymt_model_file` /
  `hymt_revision` or env `HYMT_GGUF_REPO` / `HYMT_GGUF_FILE` / `HYMT_REVISION`

**Cons:**
- ⚠️ Slower than batched NLLB (LLM decoding; ~0.5s/sentence on CPU for the 1.8B)
- ⚠️ Tencent community license (not Apache/MIT) — fine for personal use,
  read the model repo's License.txt before redistribution

### 1. NLLB-200 on CTranslate2 (Offline Neural MT)

**Quality Score:** 90/100

**Status:** Opt-in — install with `uv sync --extra nllb`

**Pros:**
- ✅ Strong zh→en quality with very fast batched CPU inference
- ✅ Fully offline after the one-time model download (~1GB distilled-600M)
- ✅ Runs on the same CTranslate2 engine Argos already uses (no PyTorch at inference)
- ✅ Model/tokenizer overridable via config keys `nllb_model_repo` /
  `nllb_tokenizer_repo` or env `NLLB_CT2_MODEL` / `NLLB_TOKENIZER`;
  pin downloads with `nllb_model_revision` / `nllb_tokenizer_revision`
  (env `NLLB_CT2_REVISION` / `NLLB_TOKENIZER_REVISION`)
- ✅ Decoding guards against NLLB's repetition loops (beam 4,
  no-repeat-ngram 3, input/decoding length caps; all config-overridable)

**Cons:**
- ⚠️ Large first-run download
- ⚠️ Heavier optional dependencies (transformers, huggingface_hub)
- ⚠️ 2022-era MT model — noticeably below HY-MT1.5 on literary text

### 2. Argos Translate (Offline Neural MT) — Default

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

### 3. CC-CEDICT Word-by-Word (Fallback)

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

Translation keys read from `config.yaml` (all optional):

```yaml
preferred_backend: hymt      # force one of: hymt, nllb, argos, cedict
prefer_offline: true         # skip backends that require the network
translation_cache: true      # persist translations under data/cache/

# Model overrides / reproducibility pins
hymt_model_repo: tencent/HY-MT1.5-7B-GGUF
hymt_model_file: "*Q4_K_M.gguf"
hymt_revision: <commit>
nllb_model_repo: entai2965/nllb-200-distilled-600M-ctranslate2
nllb_model_revision: <commit>
nllb_tokenizer_revision: <commit>
nllb_beam_size: 4
nllb_no_repeat_ngram_size: 3
```

If `preferred_backend` fails to initialize (e.g. its extra isn't
installed), the normal quality-ranked order takes over.

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
| HY-MT1.5 (1.8B Q4, CPU) | ~4s (model load) | ~0.5s/sentence (measured) |
| NLLB-200 (600M int8, CPU) | ~3s (model load) | ~0.05s/sentence batched |
| Argos Translate | ~2s (model load) | ~0.1s/sentence |
| CC-CEDICT | ~0.01s | ~0.01s/sentence |

Re-runs of the same book are near-instant regardless of backend: the
persistent cache answers before any model loads a sentence.

### Quality Comparison

**Input:** 他看着她，慢慢地说。

| Backend | Translation |
|---------|-------------|
| Argos | He looked at her and spoke slowly. |
| CC-CEDICT | He look at she, slowly say. |

## Roadmap

### Planned Backends

- [x] **Local LLM** (llama.cpp, offline, very high quality) — shipped as the
  HY-MT1.5 backend
- [ ] **Google Translate API** (online, high quality)
- [ ] **DeepL API** (online, highest quality)
- [ ] **OpenAI GPT-4** (online API, highest quality, costs money)
- [ ] **Azure Translator** (online, high quality)

### Features

- [x] Translation caching (in-run + persistent across runs)
- [x] Batch translation (one CT2 call for all sentences; manager dedupes)
- [x] User-selected backend preference in config (`preferred_backend`)
- [ ] Context-aware translation (previous sentence as context via HY-MT)
- [ ] Translation quality scoring
- [ ] A/B testing between backends

## Contributing

To add a new backend:

1. Create `translate/your_backend.py`
2. Inherit from `TranslationBackend`
3. Implement required methods
4. Add tests in `tests/test_translation.py`
5. Update this documentation
6. Submit PR

---

**Last Updated:** 2026-07-15
**Python Compatibility:** 3.9-3.13 (project caps requires-python below 3.14 for Argos)
**Status:** Stable — HY-MT1.5 (opt-in) > NLLB (opt-in) > Argos (default) > CC-CEDICT (fallback)
