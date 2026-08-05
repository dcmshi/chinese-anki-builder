# Editable Review UI — Design

**Date:** 2026-08-05
**Status:** Approved, pending implementation plan

## Problem

The pre-import QC step (`--review cards.csv`) asks the reviewer to judge
several thousand flashcards in a spreadsheet. The reviewer sees CSV columns,
not cards: no highlighted target word, no rendered pinyin, no sense of what
Anki will actually show. The step that exists to catch bad CEDICT senses and
bad machine translations is the step people skip.

`--preview` already renders every card exactly as Anki will show it
(`anki/preview.py`), but it is read-only and disconnected from the review
CSV. This design connects the two: a page that renders like `--preview` and
exports like `--review`.

## Goals

- Review cards as rendered cards, not spreadsheet rows
- Fix the three fields that are actually wrong in practice — word pinyin,
  definition, sentence translation — inline, seeing the result
- Drop junk cards (character names, bad example sentences) with one click
- Produce a CSV that `--from-review` already understands, unchanged

## Non-Goals

- No server, no network, no new runtime dependency (offline-first). Test
  tooling is exempt: Playwright is a `dev`-group dependency and never
  reaches the wheel or an end user.
- No build step or JS framework
- Not a replacement for the CSV: hand-editing the downloaded CSV remains
  the escape hatch for anything the UI does not expose

## CLI Surface

One new flag:

```
--review-ui PATH.html   Write an editable review page and stop the pipeline
```

Conventions it follows (from CLAUDE.md, "CLI Behavior Notes"):

- Defaults to `None` in argparse, so "not passed" stays distinguishable
- Errors when combined with `--from-review`, matching the existing guard for
  `--review` at `main.py:618-621`
- No `config.yaml` key — neither `--review` nor `--from-review` has one
- Honors `--stats` the same way `--review` does (`main.py:411-413`)
- May be combined with `--review`; both write their file and stop

Existing flags are unchanged. `--preview` keeps its current read-only
meaning — it is the only one of the three that still makes sense after a
`--from-review` build.

Placement: a new branch in step 8.4 of `main.py`, alongside the existing
`--review` stop, before TTS and deck building — so dropped cards never cost
audio downloads.

## Module Layout

```
anki/card_render.py     NEW    shared card appearance
  ├── anki/preview.py   EDIT   read-only page (output unchanged)
  └── anki/review_ui.py NEW    editable page
```

`card_render.py` receives the parts `preview.py` and `review_ui.py` both
need:

- `PAGE_CSS` — the card styling that mirrors `anki/templates.py`
- `cloze_front(word, sentence)` / `cloze_back(word, sentence)` — promoted
  from the private `_cloze_front` / `_cloze_back`
- `CardFaces` dataclass and `resolve_faces(card, cedict, cloze) -> CardFaces`

`CardFaces` holds resolved but **unescaped** values, so each consumer escapes
for its own context (HTML text vs. JSON payload):

| Field | Type | Notes |
|---|---|---|
| `front_sentence` | HTML | contains highlight or cloze markup |
| `back_sentence` | HTML | same |
| `word_pinyin` | text | via `resolve_word_pinyin` |
| `definition` | text | via `resolve_definition` |
| `translation` | text | may be empty |
| `sentence_pinyin` | text | may be empty |
| `chapter` | text | may be empty |

Rationale for extracting rather than duplicating: the preview's entire value
is that it matches real Anki styling. A second copy of `PAGE_CSS` would drift
from `templates.py` and quietly defeat the feature.

`tests/test_preview.py` exercises `export_cards_to_html` at the public API
level and references no internals, so it serves as the regression net for
this move.

## Page Contents

One self-contained HTML file, no external assets:

1. The card grid — same markup `preview.py` produces today, plus per-card
   controls
2. `<script type="application/json" id="cards">` holding the full card array,
   which is the authoritative model the JS edits
3. Roughly 120 lines of inline vanilla JS

### Editable vs. read-only fields

| Field | Editable | Why |
|---|---|---|
| `word_pinyin` | yes | wrong CEDICT sense is the most common defect |
| `definition` | yes | same |
| `sentence_translation` | yes | MT errors |
| `sentence` | yes | trim or fix a clumsy example |
| `sentence_pinyin` | yes | the remedy for staleness (see below) |
| `word` | no | load-bearing for highlight, cloze markup, and note GUID |
| `frequency` | no | derived metadata, no reason to edit |
| `chapter` | no | derived metadata, no reason to edit |

The three read-only fields round-trip untouched into the CSV. To change one,
drop the card or hand-edit the downloaded CSV.

### Stale sentence pinyin

`pypinyin` cannot run in the browser, so editing `sentence` cannot regenerate
`sentence_pinyin`. When a card's `sentence` differs from its original value
**and** `sentence_pinyin` has not been edited since, the card shows a visible
"sentence pinyin may be stale" marker. Editing `sentence_pinyin` clears the
marker. The marker is presentation only — it is never written to the CSV.

### Controls

- **Drop toggle** per card: dims the card and excludes it from export; the
  toggle becomes an undo
- **Filter box**: substring match over word, definition, and sentence; hides
  non-matching cards
- **Header counter**: `N cards · M dropped`
- **Download button**: serializes the model to CSV and triggers a Blob
  download named `<html stem>.csv`
- **`beforeunload` guard**: warns when edits or drops exist and nothing has
  been downloaded

## CSV Contract

The browser-generated CSV must be byte-compatible with `export_cards_to_csv`:

- Column order exactly `REVIEW_COLUMNS` (`process/review.py:20-29`)
- Leading U+FEFF byte-order mark, matching the `utf-8-sig` convention
- RFC 4180 quoting: quote a field when it contains `,`, `"`, `\r`, or `\n`;
  double any internal quote
- Dropped cards omitted entirely, which `review.py:109` already treats as
  equivalent to a deleted row
- `frequency` written as a plain integer

Quoting is not optional detail: CC-CEDICT definitions routinely contain ASCII
commas and quotes, so a naive comma join silently corrupts a large fraction
of a real deck.

## Correctness Requirements

1. **JSON payload escaping.** Card text containing `</script>` would
   terminate the payload block and break the page. Escape every `<` as the
   six-character JSON unicode escape for U+003C when serializing, so no
   literal `<` survives into the payload. This is a realistic input for a
   book corpus.
2. **HTML escaping.** All rendered text fields escape as they do today in
   `preview.py`.
3. **CSV quoting.** As specified above.
4. **BOM.** `load_cards_from_csv` opens with `utf-8-sig` and tolerates a
   missing BOM, but Excel does not, and matching the existing export is the
   correct behavior.
5. **Frequency round-trip.** Already defended at `review.py:116` against
   Excel's `5.0`; JS emits clean integers, so no new risk.

## Testing

New `tests/test_review_ui.py`, following the class-per-module convention in
TESTING.md:

- Exporter writes a file containing one JSON entry per card
- A fresh export carries no dropped or edited state
- Adversarial content survives the payload byte-exact: ASCII commas, double
  quotes, `</script>`, newlines, non-ASCII
- Rendered fields are HTML-escaped
- Cloze mode renders `[...]` fronts; regular mode renders highlights

Additions to `tests/test_main.py`:

- `--review-ui` stops the pipeline before TTS and deck building
- `--review-ui` combined with `--from-review` is a parser error
- `--review-ui` honors `--stats`

`tests/test_preview.py` runs unchanged, verifying the `card_render`
extraction preserved preview output.

### Browser round-trip tests

The JS CSV writer is the highest-risk code in this feature and is not
reachable from plain pytest, so `tests/test_review_ui_browser.py` drives a
real headless Chromium via Playwright. The test that matters:

1. Export a fixture deck with `export_cards_to_review_ui`
2. Load the page from `file://`
3. Edit a definition, edit a sentence, drop a card
4. Click Download and capture the file via `page.expect_download()`
5. Feed the captured bytes straight into `load_cards_from_csv`
6. Assert the resulting `WordCard` list matches expectations exactly

This tests the actual contract — the same function the real
`--from-review` build calls — rather than approximating it.

Cases to cover:

- Definitions containing ASCII commas and double quotes survive the round
  trip byte-exact (the corruption mode that matters most, since CC-CEDICT
  definitions routinely contain both)
- Dropped cards are absent from the loaded list
- Edited fields win over original values
- Untouched read-only fields (`word`, `frequency`, `chapter`) are unchanged
- A card whose text contains `</script>` does not break the page and round
  trips intact
- The downloaded bytes start with the U+FEFF byte-order mark

### Dependency and skip behavior

`playwright` joins the `dev` dependency group, next to pytest, ruff and
black. It is not a runtime dependency: it never enters the wheel and no end
user installs it, so the offline-first guarantee for the tool itself is
unaffected.

Because the browser binary is a separate ~150 MB `playwright install
chromium` step, these tests must not hard-fail for a contributor who has not
run it. They are guarded by `pytest.importorskip("playwright")` and marked
`@pytest.mark.browser`, registered in `pyproject.toml`, so:

- `uv run pytest tests/` still passes on a fresh checkout, skipping them
- `uv run pytest tests/ -m browser` runs them deliberately
- `uv run pytest tests/ -m "not browser"` deselects them in constrained
  environments

TESTING.md gains a short section on the one-time `playwright install
chromium` setup.

### Remaining manual check

One visual confirmation during implementation, which no automated test
replaces: open a real generated page and confirm the cards render as they do
in `--preview` and the grid is usable at a few thousand cards.

## Documentation to Update

- `README.md` — `--review-ui` in the CLI option list
- `FEATURES.md` — review workflow description
- `CLAUDE.md` — the `--review` / `--from-review` note under "CLI Behavior
  Notes", and `anki/review_ui.py` plus `anki/card_render.py` in the project
  structure tree
- `CHANGELOG.md` — new entry
- `TESTING.md` — the one-time `playwright install chromium` step and the
  `browser` marker

`pyproject.toml` changes are limited to the `dev` dependency group
(`playwright`) and registering the `browser` marker. The wheel is untouched:
`anki/` is already in `only-include`, so
`test_wheel_config_ships_all_first_party_code` stays green.

## Out of Scope

- Virtualized scrolling — 2,700 cards is roughly 3 MB of DOM, which browsers
  handle fine
- Undo history beyond the drop toggle
- Audio playback in the page
- Any server component
