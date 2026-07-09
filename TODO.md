# TODO — Repo Audit Action Items (2026-07-09)

Findings from a full audit of source, tests, packaging, and docs.
Test suite status at time of audit: **48/48 passing**.

## P0 — Bugs (broken or produces wrong output)

- [x] **`analyze_coverage.py` does not compile** — `SyntaxError: unterminated
  string literal` at line 44 (`print('uv run python main.py \')` — the `\'`
  escapes the closing quote). Fix the escaping or delete the script; it's a
  one-off with hardcoded stats that duplicates FEATURES.md content.
- [x] **Page-number removal in `clean_text` is dead code** —
  `normalize_whitespace()` (`utils/chinese_utils.py:24`) collapses **all**
  whitespace including newlines before `clean_text`
  (`process/text_cleaner.py:57`) tries to split on `"\n"` and drop digit-only
  lines. The whole book becomes one line, so PDF page numbers survive into
  sentences. Fix: collapse only spaces/tabs (`[ \t]+`) and preserve newlines,
  or drop digit lines before normalizing. (The limitation is even acknowledged
  in `tests/test_text_cleaner.py:110`.)
- [x] **Failed neural translation silently poisons cards** — on any error,
  `ArgosTranslateBackend.translate` (`translate/argos_backend.py:134`) and
  `NLLBTranslateBackend.translate` (`translate/nllb_backend.py:143`) return the
  **original Chinese text**. `TranslationManager.translate` treats any
  non-empty string as success, caches it, and never falls back to CEDICT — so
  cards can show the Chinese sentence as its own "translation". Fix: raise (or
  return `""`) so the manager's fallback chain actually engages.
- [x] **Wheel packaging is broken** — `[tool.hatch.build.targets.wheel]`
  (`pyproject.toml:47`) lists `["extract", "process", "tts", "anki", "utils"]`
  but omits the `translate/` package, and top-level `main.py` is not packaged
  at all even though `[project.scripts] anki-chinese = "main:main"` needs it.
  An installed (non-editable) wheel's CLI fails with ImportError. `uv sync`'s
  editable install masks this today.

## P1 — Correctness / quality issues

- [x] **CEDICT loader keeps only the last entry per simplified form**
  (`process/cedict_loader.py:136`). Words with multiple entries (的, 地, 了,
  行, …) get an arbitrary pronunciation/definition — often a proper noun or
  rare reading. Store all entries per key and pick sensibly (e.g., prefer
  non-capitalized pinyin / non-proper-noun senses).
- [x] **Note GUID is a 32-bit int** (`anki/deck_builder.py:31`, md5[:8]).
  Birthday collisions are plausible at 3k cards (~0.1%), and colliding notes
  silently overwrite each other on Anki import. Use the full hash string (or
  `genanki.guid_for`). Note: changing GUIDs breaks re-import dedup with
  existing decks — document that.
- [x] **Card front doesn't highlight the word *in* the sentence** — the
  template (`anki/templates.py:9`) shows the sentence and then the word
  separately below it. README/CLAUDE.md promise "sentence with target word
  highlighted". Wrap occurrences of the word in a styled span when building
  the note fields.
- [ ] **EPUB chapters are read in manifest order, not spine (reading) order**
  (`extract/epub_extractor.py:34` uses `book.get_items()`). Chapter tags can
  be mis-ordered/mis-attributed. Iterate the spine instead.
- [ ] **Word pinyin style is inconsistent with sentence pinyin** — CEDICT path
  returns numbered pinyin (`ni3 hao3`, `process/pinyin_converter.py:23`) while
  sentence pinyin uses tone marks via pypinyin. Convert CEDICT numbered pinyin
  to diacritics for display consistency.
- [ ] **`--config` pointing at a missing file is silently ignored** —
  `load_config` (`main.py:34`) falls back to `./config.yaml` without a
  warning. Error (or at least warn) when an explicitly passed config path
  doesn't exist.
- [ ] **Argos init hits the network every run** —
  `update_package_index()` (`translate/argos_backend.py:40`) is called before
  checking whether the zh→en model is already installed. Check installed
  packages first so cached/offline runs don't depend on the exception path.
- [ ] **`.gitignore` doesn't cover new data caches** — only
  `data/cedict.txt(.gz)` is ignored; the NLLB model dir
  (`data/nllb_ct2_model/`, ~1GB) and `data/cache/` (TTS cache) are not.
  Consider ignoring `data/` wholesale.
- [ ] **Uncaught `BadGzipFile` on corrupted CEDICT download** —
  `gzip.decompress` (`process/cedict_loader.py:61`) sits outside the
  try/except; a truncated download crashes with a raw traceback instead of the
  friendly retry message.

## P2 — Pending features (docs already promise or roadmap items)

- [ ] **HSK filtering** — `process/hsk_filter.py` is a stub; needs HSK word
  lists, a `hsk_levels` config hookup, and a `--hsk` CLI flag.
- [ ] **TTS audio** — `tts/gtts_generator.py` is a placeholder; `--tts` is
  accepted and silently ignored (`main.py:248` resolves `enable_tts`, but
  `process_pipeline` swallows it via `**kwargs`). Either wire it up or make
  the flag print a clear "not implemented" notice.
- [ ] **Stats export** — `stats_file` exists in `config.yaml:16` but nothing
  reads it; no `--stats` flag.
- [ ] **PDF chapter detection** — whole PDF is one "PDF Book" chapter
  (`extract/pdf_extractor.py:33` TODO); FEATURES.md oversells this.
- [ ] **Cloze deletion cards** — roadmap item, not started.
- [ ] **Chapter as real Anki tag** — chapter is only a note *field*;
  FEATURES.md suggests "filter by chapter in Anki", which wants genanki
  `tags` (sanitized: no spaces) in addition to the field.

## P3 — Performance

- [ ] **`find_sentence_for_word` is O(words × sentences) substring scans**
  (`process/word_selector.py:82`), and its fallback re-scans all sentences
  (line 93). For 3000 words × 20k+ sentences this dominates runtime alongside
  translation. Build an inverted index (word → candidate sentences) once.

## P4 — Dead code / cleanup

- [ ] Remove unused `translate_with_context`
  (`process/sentence_translator.py:127`) — its "context" logic is a no-op
  `pass` anyway.
- [ ] Remove unused `get_full_text` (`extract/epub_extractor.py:63`).
- [ ] Consolidate duplicated dev dependencies — both
  `[project.optional-dependencies].dev` (pytest>=7.4.0, black, ruff) and
  `[dependency-groups].dev` (pytest>=8.4.2, pytest-cov) exist in
  `pyproject.toml` with conflicting pins.

## P5 — Documentation drift

- [ ] **Test counts stale everywhere**: CLAUDE.md, FEATURES.md, and
  CHANGELOG say "24 tests / 52% coverage"; the suite is now **48 tests**
  (test_text_cleaner and test_nllb_backend aren't mentioned in the docs'
  test-module lists). Re-run coverage and refresh numbers.
- [ ] **FEATURES.md translation section predates NLLB** — module structure
  omits `translate/nllb_backend.py`; backend list/quality table omits NLLB
  (90). Also says Argos is "Python 3.12–3.13 only" while code/pyproject
  support 3.9–3.13.
- [ ] **Dependency lists are wrong** — README and FEATURES.md cite `PyPDF2`;
  the project uses `pypdf`. FEATURES.md lists `argostranslate` as optional;
  it's a core dependency in pyproject.
- [ ] **QUICKSTART.md says "Python 3.14.3"** — pyproject caps
  `requires-python <3.14` and the venv runs 3.13.14; Argos doesn't work on
  3.14. Fix the claim.
- [ ] **README card-format section** says front shows the sentence with the
  word highlighted — align with reality once the P1 highlight item is done.

## P6 — Test coverage gaps

- [ ] No tests for: EPUB/PDF extractors, `tokenizer.py`,
  `pinyin_converter.py`, CEDICT word-by-word translation quality
  (`sentence_translator.py` / `cedict_backend.py`), `TranslationManager`
  fallback logic (would have caught the P0 translation-fallback bug), or
  `main.py`'s CLI/config `resolve()` precedence.
