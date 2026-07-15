# TODO — Repo Audit Action Items

## Audit 2026-07-15 — Translation state-of-the-art review

Deep audit of the translation stack against the mid-2026 open-model landscape,
plus a decision on deck-editing/QC UI. Architecture verdict: the pluggable
chain (quality-ranked fallback, raise-on-failure, failures never cached) is
sound, but the backends were two generations behind open SOTA for zh→en.

Field check (July 2026): Tencent **Hunyuan-MT-7B won WMT25** (1st place in
30/31 language pairs); its successor **HY-MT1.5** (1.8B + 7B, open-sourced
2025-12-30, arXiv 2512.24092) is the current open offline SOTA. On WMT25,
HY-MT1.5-7B scores XCOMET-XXL 0.6159 vs Seed-X-PPO-7B 0.4783 and
Tower-Plus-**72B** 0.4100. Official GGUF builds run locally via llama.cpp;
the 1.8B quantized (~1GB) matches the NLLB-600M int8 footprint with far
better zh→en. NLLB-200 (2022) remains the 200-language coverage king but is
no longer competitive for zh→en quality; Argos (Marian-era) further behind.

### Action items

> **Status: all action items complete (2026-07-15).** Suite 261 → 290
> tests, ruff-clean; verified end-to-end with a real deck build (Argos
> active, HY-MT/NLLB skipped as not installed, batch + persistent cache
> confirmed in the run output and cache file).

- [x] **HY-MT1.5 backend** — new top quality tier (95), opt-in via
  `uv sync --extra hymt` (llama-cpp-python + GGUF from
  `tencent/HY-MT1.5-1.8B-GGUF`; 7B overridable via config/env). Official
  prompt template; recommended sampling params from the model card.
- [x] **Batch translation** (old TRANSLATION.md roadmap item) — pipeline
  translated one sentence per call (`process/word_selector.py:193`), and the
  NLLB backend called CT2 `translate_batch` with a single item
  (`translate/nllb_backend.py:133`). Added `translate_batch` to the backend
  contract (native in NLLB, sequential default elsewhere), a cache-aware
  `TranslationManager.translate_batch`, and the pipeline now batches all
  example sentences in one deduplicated call.
- [x] **NLLB decoding guards** — beam_size 4, no_repeat_ngram_size 3, max
  input/decoding length 256 (all config-overridable).
- [x] **Deterministic model downloads** — revision pins for NLLB
  model/tokenizer (`nllb_model_revision` / `nllb_tokenizer_revision`, env
  `NLLB_CT2_REVISION` / `NLLB_TOKENIZER_REVISION`) and HY-MT
  (`hymt_revision` / `HYMT_REVISION`); Argos logs the installed zh→en
  package version at init.
- [x] **Persistent translation cache** — `data/cache/translations.json`,
  keyed by backend + language pair + text; toggle via `translation_cache`
  config (default on). Manager saves after each batch and on cleanup.
- [x] **Config passthrough bug (new, confirmed)** — `TranslationManager()`
  was constructed with no config (`main.py:193`), so the documented
  `nllb_model_repo` / `nllb_tokenizer_repo` YAML keys were dead (only the
  env vars worked). The loaded config now reaches all backends; regression
  test added.
- [x] **Translation config keys** — `preferred_backend`, `prefer_offline`
  (was hardcoded True), and `translation_cache` wired through main.py and
  documented in config.yaml.
- [x] **Docs refresh** — TRANSLATION.md / FEATURES.md / CLAUDE.md / README
  backend lists, quality table, roadmap checkboxes, extras; CHANGELOG 0.4.0.

### Deferred (recorded, not in this pass)

- [x] **Pre-import QC workflow** *(shipped 2026-07-15, follow-up pass)* —
  decision: **no web front end** (non-goal; Anki's Browse window already
  covers post-import editing). Implemented `--review cards.csv` (stops
  before TTS/deck build, one editable row per card, UTF-8 BOM for Excel)
  and `--from-review cards.csv` (builds from the reviewed file; every
  edited field authoritative — WordCard gained word_pinyin/definition
  overrides honored by both note types). Verified end-to-end: 9 exported →
  2 deleted + 1 translation edited → 7-note deck with the edit on the card.
  Optional static HTML preview still open (below).
- [x] **Static HTML card preview** *(shipped 2026-07-15, follow-up pass)* —
  `--preview cards.html` writes a self-contained page rendering every card
  front/back with the real card styling (regular + cloze); combines with
  `--review` and `--from-review`. Also shipped in the same pass: the two
  pre-audit pending features — known-words filtering (`--known-words` /
  `known_words_file`, excluded before top-N selection) and sentence audio
  (`--tts-sentences` / `enable_sentence_tts`, SentenceAudio field appended
  last on both models for reimport safety).
- [ ] **Context-aware translation** — all backends translate sentences in
  isolation; the HY-MT LLM backend makes a previous-sentence-context mode
  feasible later (pronoun/referent fidelity in literary text). Hold until
  there's eval evidence: the official HY-MT prompt is strictly
  single-segment, so deviating risks quality.

### Quality validation (2026-07-15, local)

HY-MT1.5-1.8B (official Tencent Q4_K_M GGUF, via Ollama in Docker) tested
head-to-head against Argos on 7 probe sentences (idioms, proverbs, literary
register, dialogue). The 1.8B won every discriminating case: 老人 rendered
correctly ("the old man" vs Argos "old people"), 七上八下 and 天下没有不散的筵席
translated idiomatically ("all good things must come to an end" vs "there is
no endless feast"), 冷笑 as "snickered" (Argos: "smiled" — wrong), dialogue
register natural. ~0.5s/sentence on CPU after model load. Validates the
backend choice and the 1.8B default.

### Confirmations of earlier findings

- 2026-07-09 audit close-out re-verified this pass: full suite green and
  ruff-clean via the lint gate (see below for the original checklist).
- First-pass (2026-07-15 morning) findings folded in above; two were
  superseded rather than actioned: NLLB's distilled-600M default stays (the
  HY-MT tier now owns "highest quality"; 1.3B/3.3B remain config/env
  overrides), and NLLB opt-in discoverability is addressed by documenting
  HY-MT as the recommended quality extra.

---

## Audit 2026-07-09 (original)

Findings from a full audit of source, tests, packaging, and docs.
Test suite status at time of audit: **48/48 passing**.

> **Status: all items complete.** Every P0–P6 item below was fixed in its own
> commit with regression tests where feasible; docs were refreshed in a
> consolidated 0.3.0 commit. Suite grew from 48 to 225 tests (86% coverage).

## Re-audit (2026-07-09, post-fix)

A second full pass after all fixes landed. Verified end-to-end by building
real decks from a generated EPUB and inspecting the .apkg SQLite contents
(highlight span, tone-mark pinyin, neural translation, chapter tag, 32-char
GUID, cloze marker all confirmed).

- [x] **CLI input errors dumped raw tracebacks** — `load_config()` and
  `parse_hsk_levels()` ran outside `main()`'s try/except, so a missing
  `--config` file or bad `--hsk` spec bypassed the friendly `ERROR:` line.
  Moved settings resolution inside the handler; regression tests drive
  `main()` with bad args and assert no traceback reaches stderr.
- [x] **Leftover doc drift** — FEATURES.md still called the Audio field a
  placeholder and cited Argos as "Python 3.12-3.13"; TRANSLATION.md had the
  same stale range. (CHANGELOG 0.1/0.2 entries left as-is: historical.)
- [x] **Vestigial `include_audio` parameter** removed from deck building
  (audio is driven by `card.audio_filename` since the TTS feature landed).

No further correctness, performance, or packaging issues found.

## Third pass (2026-07-09, post-push)

Deeper sweep after pushing: ruff over the whole tree, model/template
cross-checks, and filename/ID edge cases.

- [x] **Cloze decks silently drop TTS audio** — the cloze model has no
  Audio field, so `--tts --cloze` generates and bundles MP3s that no note
  references (wasted downloads, orphaned media in the .apkg). Add an Audio
  field + template block to the cloze model and populate it in
  `create_cloze_note`.
- [x] **Deck ID is a 32-bit truncated hash** (`anki/deck_builder.py:237`) —
  same birthday-collision class as the note-GUID bug: two deck names
  hashing to the same ID are treated as the *same deck* by Anki. Widen to
  the safe genanki/Anki range.
- [x] **Deck name is used unsanitized as the output filename** — `--deck
  "A/B"` writes to a nested directory; `:` or `?` in a name crashes on
  Windows. Sanitize the filename only (the deck keeps its display name).
- [x] **16 ruff findings** — 15 unused imports across 10 files plus one
  E713 (`not x in` → `x not in`). Add a lint gate so the tree stays clean.
- [x] **Integration test for the full pipeline** (TESTING.md TODO) — EPUB →
  .apkg end-to-end with a stubbed CEDICT, asserting on the built deck.
- [x] **Direct tests for `utils/chinese_utils.py`** (TESTING.md TODO) —
  currently only covered indirectly.

All third-pass items complete. Final state: **261 tests, 90% coverage**,
ruff-clean with a lint gate in the suite.

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
- [x] **EPUB chapters are read in manifest order, not spine (reading) order**
  (`extract/epub_extractor.py:34` uses `book.get_items()`). Chapter tags can
  be mis-ordered/mis-attributed. Iterate the spine instead.
- [x] **Word pinyin style is inconsistent with sentence pinyin** — CEDICT path
  returns numbered pinyin (`ni3 hao3`, `process/pinyin_converter.py:23`) while
  sentence pinyin uses tone marks via pypinyin. Convert CEDICT numbered pinyin
  to diacritics for display consistency.
- [x] **`--config` pointing at a missing file is silently ignored** —
  `load_config` (`main.py:34`) falls back to `./config.yaml` without a
  warning. Error (or at least warn) when an explicitly passed config path
  doesn't exist.
- [x] **Argos init hits the network every run** —
  `update_package_index()` (`translate/argos_backend.py:40`) is called before
  checking whether the zh→en model is already installed. Check installed
  packages first so cached/offline runs don't depend on the exception path.
- [x] **`.gitignore` doesn't cover new data caches** — only
  `data/cedict.txt(.gz)` is ignored; the NLLB model dir
  (`data/nllb_ct2_model/`, ~1GB) and `data/cache/` (TTS cache) are not.
  Consider ignoring `data/` wholesale.
- [x] **Uncaught `BadGzipFile` on corrupted CEDICT download** —
  `gzip.decompress` (`process/cedict_loader.py:61`) sits outside the
  try/except; a truncated download crashes with a raw traceback instead of the
  friendly retry message.

## P2 — Pending features (docs already promise or roadmap items)

- [x] **HSK filtering** — `process/hsk_filter.py` is a stub; needs HSK word
  lists, a `hsk_levels` config hookup, and a `--hsk` CLI flag.
- [x] **TTS audio** — `tts/gtts_generator.py` is a placeholder; `--tts` is
  accepted and silently ignored (`main.py:248` resolves `enable_tts`, but
  `process_pipeline` swallows it via `**kwargs`). Either wire it up or make
  the flag print a clear "not implemented" notice.
- [x] **Stats export** — `stats_file` exists in `config.yaml:16` but nothing
  reads it; no `--stats` flag.
- [x] **PDF chapter detection** — whole PDF is one "PDF Book" chapter
  (`extract/pdf_extractor.py:33` TODO); FEATURES.md oversells this.
- [x] **Cloze deletion cards** — roadmap item, not started.
- [x] **Chapter as real Anki tag** — chapter is only a note *field*;
  FEATURES.md suggests "filter by chapter in Anki", which wants genanki
  `tags` (sanitized: no spaces) in addition to the field.

## P3 — Performance

- [x] **`find_sentence_for_word` is O(words × sentences) substring scans**
  (`process/word_selector.py:82`), and its fallback re-scans all sentences
  (line 93). For 3000 words × 20k+ sentences this dominates runtime alongside
  translation. Build an inverted index (word → candidate sentences) once.

## P4 — Dead code / cleanup

- [x] Remove unused `translate_with_context`
  (`process/sentence_translator.py:127`) — its "context" logic is a no-op
  `pass` anyway.
- [x] Remove unused `get_full_text` (`extract/epub_extractor.py:63`).
- [x] Consolidate duplicated dev dependencies — both
  `[project.optional-dependencies].dev` (pytest>=7.4.0, black, ruff) and
  `[dependency-groups].dev` (pytest>=8.4.2, pytest-cov) exist in
  `pyproject.toml` with conflicting pins.

## P5 — Documentation drift

- [x] **Test counts stale everywhere**: CLAUDE.md, FEATURES.md, and
  CHANGELOG say "24 tests / 52% coverage"; the suite is now **48 tests**
  (test_text_cleaner and test_nllb_backend aren't mentioned in the docs'
  test-module lists). Re-run coverage and refresh numbers.
- [x] **FEATURES.md translation section predates NLLB** — module structure
  omits `translate/nllb_backend.py`; backend list/quality table omits NLLB
  (90). Also says Argos is "Python 3.12–3.13 only" while code/pyproject
  support 3.9–3.13.
- [x] **Dependency lists are wrong** — README and FEATURES.md cite `PyPDF2`;
  the project uses `pypdf`. FEATURES.md lists `argostranslate` as optional;
  it's a core dependency in pyproject.
- [x] **QUICKSTART.md says "Python 3.14.3"** — pyproject caps
  `requires-python <3.14` and the venv runs 3.13.14; Argos doesn't work on
  3.14. Fix the claim.
- [x] **README card-format section** says front shows the sentence with the
  word highlighted — align with reality once the P1 highlight item is done.

## P6 — Test coverage gaps

- [x] No tests for: EPUB/PDF extractors, `tokenizer.py`,
  `pinyin_converter.py`, CEDICT word-by-word translation quality
  (`sentence_translator.py` / `cedict_backend.py`), `TranslationManager`
  fallback logic (would have caught the P0 translation-fallback bug), or
  `main.py`'s CLI/config `resolve()` precedence.
