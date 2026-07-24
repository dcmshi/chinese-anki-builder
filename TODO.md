# TODO — Repo Audit Action Items

## Audit 2026-07-24 — Full-repo bug & improvement scan

Four-parallel-reviewer sweep of every module (process/, translate/, tts/,
anki/, extract/, utils/, main.py wiring). Baseline at scan time: **334/334
tests passing, ruff clean**. No test-suite failures — all findings below are
latent bugs or improvements not covered by the current tests.

> **Status: closed out 2026-07-24.** 36 of 38 findings actioned, 2 rejected
> after verification against the code/data (both marked *[rejected]* below,
> with the check that disproved them). Every fix carries a regression test:
> suite **334 → 454 tests**, 90% source coverage, ruff-clean. Shipped as
> 0.7.0. Two findings were narrowed rather than implemented as written —
> the over-long-sentence fix caps at selection instead of dropping splitter
> tails, and the mixed-token filter sits in the candidate filter instead of
> the tokenizer — reasons inline.

### P0 — High severity (real bugs)

- [x] **One bad sentence silently downgrades the whole book's translations**
  (`translate/manager.py:297-323`, `translate/base.py:94`,
  `translate/hymt_backend.py:167`). `translate_batch` is all-or-nothing: one
  exception in any item sends the *entire* book to the fallback chain, which
  skips the active backend (`manager.py:184`). `create_word_cards` submits
  the whole book as a single batch (`process/word_selector.py:210`), so one
  HY-MT echo / malformed sentence means every card gets lower-quality
  translations with only one log line as evidence. Fix: catch per-item
  exceptions in `base.py`'s default `translate_batch` (and HY-MT's
  override), return `""` for failures — the manager already routes empties
  through per-item fallback.
- [x] **EPUB extraction injects spaces mid-word**
  (`extract/epub_extractor.py:60`). `get_text(separator=" ", strip=True)`
  puts a space between *every* adjacent text node, so
  `<p>你<b>好</b>吗</p>` → `你 好 吗`. Chinese EPUBs routinely wrap
  characters in spans (ruby, fonts), so this is realistic; spaces pollute
  cards, pinyin, TTS text, and can break `word in sentence` checks
  downstream (highlight/cloze silently no-op). Fix: `separator=""` and join
  per-block elements with `"\n"`/space instead.
- [x] **Non-atomic cache writes leave permanently-trusted corrupt files** —
  same bug in four places: `process/cedict_loader.py:71` and
  `process/hsk_filter.py:96` (truncated dictionary/HSK list parses fine,
  just silently has fewer entries — forever), `tts/gtts_generator.py:85`
  (truncated MP3 served from cache), `translate/manager.py:165` (whole
  translation cache lost on crash mid-write; concurrent runs clobber each
  other). Fix everywhere: write to a sibling temp file + `os.replace()`.
- [x] **One malformed PDF page aborts the whole book**
  (`extract/pdf_extractor.py:103-106`). `page.extract_text()` raises on
  damaged/encrypted/oddly-encoded pages; no per-page try/except, so one bad
  page in a 500-page book kills the run with no partial output. Fix: catch,
  log page number, continue.

### P1 — Medium severity

- [x] **Interrupted NLLB download bricks the backend**
  (`translate/nllb_backend.py:93-103`). Cache check is just
  `model.bin` exists; a partial download makes `ctranslate2.Translator`
  raise on every subsequent run — the backend never self-heals. Fix: on load
  failure, delete the dir and retry the download once.
- [x] **All available backends' models load at startup, not just the active
  one** (`translate/manager.py:111-137`). With extras installed, HY-MT's
  GGUF LLM + NLLB-600M + Argos can all sit in RAM simultaneously (multiple
  GB) though only one is active. Fix: initialize fallbacks lazily on first
  use inside `_fallback_translate()`.
- [x] **Fallback translations never consult the persistent cache**
  (`translate/manager.py:178-200`). Fallback results *are* persisted but the
  cache is never *read* on the fallback path, so re-runs redo full model
  inference for sentences a fallback already translated. Fix: check
  `_persistent_get` per candidate backend in the `_fallback_translate` loop.
- [x] **`"5.0"`-style frequencies silently zeroed on review re-import**
  (`process/review.py:113`). Excel/LibreOffice reformat integer columns as
  floats; `int("5.0")` raises, the `except ValueError` swallows it, and the
  card comes back with `frequency=0` — silent data loss in the documented
  `--from-review` workflow. Fix: parse via `int(float(value))`.
- [x] **`……` not treated as a sentence ender**
  (`process/text_cleaner.py:10`). Very common in fiction; merged
  mega-sentences then exceed `max_sentence_length` and get skipped or land
  on cards over-length. Fix: treat a *run* of `…` (optionally followed by
  closers) as a soft ender — don't add single `…` to `_SENT_ENDERS`
  outright (it also appears mid-sentence).
- [x] **Over-long fallback sentences reach cards**
  (`process/word_selector.py:129-132` + `process/text_cleaner.py:95-98`).
  When no in-range sentence exists, `min(..., key=len)` picks the shortest
  match of *any* length; combined with unpunctuated trailing fragments kept
  by `split_sentences`, a multi-thousand-character blob can land on a card
  and in gTTS. Fix: cap or skip in the fallback; drop over-long tails in
  `split_sentences`.
  *Narrowed*: capped in the fallback only (accepts up to 3x
  `max_sentence_length`, else reports no sentence and the word counts as
  `skipped_no_sentence`). The splitter keeps its over-long tails on purpose —
  dropping content there would silently discard text that unusual punctuation
  made one long fragment, and the cap at selection already keeps blobs off
  cards and out of gTTS, which is the actual harm.
- [x] **Invalid cloze notes shipped when the word isn't in the sentence**
  (`anki/deck_builder.py:198-241`). Nothing enforces the
  callers-only-pass-containing-sentences assumption (and the EPUB-space bug
  above can cause exactly this); Anki flags "no cloze deletions" on import.
  Fix: skip (and count) notes whose cloze text lacks `{{c1::`.
- [x] **CEDICT backend reports initialized with no dictionary loaded**
  (`translate/cedict_backend.py:20-29`). `initialize()` sets
  `_initialized = True` unconditionally; a manager used without
  `set_cedict()` reports "✓ Initialized: CC-CEDICT", may select it as
  active, and produces empty translations for everything. Fix: return
  `self.cedict is not None` from `initialize()`.
- [x] **No error handling or cleanup around extractor file opening**
  (`extract/pdf_extractor.py:100`, `extract/epub_extractor.py:52`).
  `PdfReader` keeps the file handle open for its lifetime (locks the file on
  Windows); neither library's failures get a useful message. Fix: catch
  `OSError`/library exceptions and re-raise with the path; for pypdf, read
  bytes first (`PdfReader(io.BytesIO(...))`) or `reader.close()` in
  `finally`.

### P2 — Low severity

- [x] **`is_chinese_char` misses CJK Extension A** (`utils/chinese_utils.py:8`)
  — only U+4E00–U+9FFF covered, so `contains_chinese` /
  `is_multi_char_word` / `_chinese_char_count` undercount rare-but-real
  characters (older/classical texts). Extend to `\u3400-\u4dbf` (and
  possibly compatibility ideographs `\uf900-\ufaff`).
- [x] **Mixed tokens waste top-N slots** (`process/tokenizer.py:52`) —
  `contains_chinese` keeps tokens with ≥1 Han char ("QQ群", "A股"), which
  get selected then skipped as "no definition", shrinking the deck below
  `top_words`. Require purely-Han tokens in the filter.
  *Narrowed*: enforced in `filter_multi_char_words` (the card-candidate
  filter) rather than `tokenize_text`. Filtering at tokenization would also
  drop those tokens from the frequency/coverage statistics and from CC-CEDICT
  word-by-word translation, where a mixed token still carries meaning.
- [x] **`sanitize_filename` misses Windows reserved names**
  (`utils/file_utils.py:12`) — `CON`, `PRN`, `NUL`, `AUX`, `COM1-9`,
  `LPT1-9` pass through; the project targets Windows. Append `_` when the
  sanitized stem matches the reserved set.
- [x] **`get_data_dir()` anchored to the package source tree**
  (`utils/file_utils.py:39`) — caches (CC-CEDICT, HSK, translations, TTS)
  land in `site-packages` (potentially read-only) when installed from the
  wheel. Resolve via cwd/platformdirs when installed, or fall back
  gracefully when unwritable.
- [x] **Boolean config flags can't be overridden from the CLI**
  (`main.py:509-527`) — `--cloze`/`--tts`/`--tts-sentences` are
  `store_true` with `default=None`, so `cloze: true` in config.yaml can't be
  turned off per-run. Use `argparse.BooleanOptionalAction`.
- [x] **`--stats` and `--tts` silently ignored in `--review` mode**
  (`main.py:355-381`) — the early return after writing the review CSV
  produces no stats and no warning. Export stats before the return, or warn.
- [x] **`multi_char_words` stat mislabeled when HSK filtering is active**
  (`main.py:365`) — reports the post-filter count. Capture the pre-filter
  count and export both.
- [x] **`hsk_levels` from config used unvalidated** (`main.py:602-604`) — a
  scalar `hsk_levels: 3` in config.yaml raises a raw `TypeError`. Normalize
  scalar → list / spec-string → `parse_hsk_levels` in the resolve step.
- [x] **Dead regex in `improve_translation`**
  (`process/sentence_translator.py:110`) — `re.sub(r'\b[的了着过]\b', '', result)`
  operates on an English string where those particles were already stripped;
  at best it can delete characters from an untranslated name. Remove it (and
  move the function-local `import re` to module top).
- [x] **NLLB silently maps unknown language codes to zh→en**
  (`translate/nllb_backend.py:166`) — a typo'd code yields a
  plausible-looking translation instead of an error (Argos raises
  `ValueError` in the same situation). Raise or at least warn.
- [x] **HSK spec with trailing comma gives a raw `int('')` error**
  (`process/hsk_filter.py:45`) — filter empties before `int()` for the
  friendly `ValueError`.
- [x] **HSK list file read without BOM tolerance**
  (`process/hsk_filter.py:126`) — `utf-8` leaves `\ufeff` glued to the first
  word of a manually-placed file; `known_words.py` already uses `utf-8-sig`.
- [x] **TTS cache key ignores `lang`** (`tts/gtts_generator.py:30-41`) —
  changing voice (zh-CN → zh-TW) would serve stale audio. Include `lang` in
  the hash.
- [ ] **CEDICT `line.split("/")` mangles definitions with embedded slashes**
  *[rejected]* (`process/cedict_loader.py:97`) — senses like `24/7` split
  into bogus fragments. Partition the trailing `/` first (`rsplit("/", 1)`),
  then split senses.
  **Verified false against the data**: `/` is CC-CEDICT's reserved sense
  separator, so no sense contains one. Scanned all 124,782 lines of the
  cached dictionary: zero lines lack the trailing `/`, and every
  digit-only sense (`/seven/7/`, `/three-dimensional/3D/`) is a genuine
  separate sense, not a split `24/7`. The proposed `rsplit` wouldn't change
  the outcome for an embedded slash anyway — the format is ambiguous there
  by construction. *Actioned the adjacent real weakness instead*: only the
  final empty field is dropped now, so a hand-placed file without the
  trailing `/` keeps its last sense (was silently discarded).
- [x] **`zip(unique_sentences, translated)` silently truncates on backend
  length mismatch** (`process/word_selector.py:216`) — tail sentences get
  empty translations with no warning. Check lengths and log/fall back.
- [x] **`_tidy_sentence` strips legitimate leading ellipsis/dashes**
  (`process/text_cleaner.py:16,37`) — `_LEADING_JUNK` includes `…—–-`;
  dialogue like `……我不知道。` loses its opener.
- [ ] **Highlighting hits substrings inside other words** *[rejected]*
  (`anki/deck_builder.py:37-60`) — word `人` highlights inside `人们`.
  Consider highlighting only the jieba-selected occurrence.
  **Premise doesn't hold for this pipeline**: card words always carry 2+ Han
  characters (`filter_multi_char_words`), so the single-character example
  can't occur. For the 2-char cases that can (`学习` inside `学习者`) the
  nested match is the same morpheme, and highlighting it is defensible
  pedagogy rather than a defect. Selecting one occurrence would mean
  re-tokenizing the sentence in the deck builder and agreeing with jieba's
  segmentation of hand-edited `--from-review` rows — real complexity and a
  determinism risk for no clear gain. Behaviour documented as intentional in
  `highlight_word_in_sentence`.
- [x] **`media_files: List[str] = None` wrong annotation**
  (`anki/deck_builder.py:250`) — should be `Optional[List[str]]`.
- [x] **Per-card `print` warnings spam on large decks**
  (`anki/deck_builder.py:133,157`) — one line per missing definition floods
  output and garbles the tqdm bar. Collect and print a single summary.
- [x] **`Word`/`Chapter` fields not HTML-escaped** (`anki/deck_builder.py:181-189,226-239`)
  — `Sentence` is escaped but chapter titles from EPUB headings aren't;
  `preview.py` already escapes chapter, so preview and deck disagree.
- [x] **Non-linear EPUB spine items extracted as chapters**
  (`extract/epub_extractor.py:31`) — `linear="no"` aux content is included
  in reading order.
- [x] **Argos/NLLB/HY-MT re-run full `initialize()` on every `translate()`
  call when uninitialized** (`translate/argos_backend.py:117-119`) —
  standalone use after a failed init hammers the network per sentence.
  Cache the init failure and raise immediately.
- [x] **`config.yaml` read as plain `utf-8`** (`main.py:49,53`) — a BOM
  (Windows Notepad) breaks `yaml.safe_load` with a cryptic error; the rest
  of the project tolerates BOMs. Use `utf-8-sig`.
- [x] **Dead `isspace()` check** (`process/tokenizer.py:48-49`) —
  unreachable after `token.strip()` + empty check. Remove.
- [x] **PDF chapter headings split across page boundaries are missed**
  (`extract/pdf_extractor.py:108`) — inherent to the heuristic; document the
  limitation in the docstring.

### Found while closing this audit (not in the original scan, not fixed)

- [ ] **Chapter headings bleed into the first example sentence.** A heading
  carries no sentence-ending punctuation, and `clean_text` joins all lines
  with a space (correctly, so hard-wrapped PDF lines don't break
  mid-sentence), so the first sentence of every chapter becomes
  `第二章 研究 科学家们正在努力研究宇宙深处的秘密。`. Verified identical
  before and after this pass's extraction change, i.e. long-standing, not a
  regression. In an 11-card smoke deck, 5 cards carried heading text and one
  translation degraded to "The second chapter of the study is that
  scientists...". Fix needs a way to keep EPUB block boundaries as sentence
  boundaries while still joining PDF's hard-wrapped lines — extraction now
  emits `\n` only at semantic block boundaries, so the information is
  available; `clean_text`/`split_sentences` would need to distinguish the two
  sources (e.g. an explicit `join_lines` flag set per extractor).
- [ ] **`requires-python = ">=3.9"` is not achievable.** `utils/file_utils.py`
  annotates `str | Path` (PEP 604), which is evaluated at def time and raises
  `TypeError` on 3.9. The real floor is 3.10. Either drop the annotations to
  `Union[...]`/add `from __future__ import annotations`, or raise the pin —
  a release decision, so left alone here.

---

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
