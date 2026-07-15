#!/usr/bin/env python3
"""
Anki Chinese Deck Builder

Generate Anki flashcards for learning Chinese from EPUB and PDF books.
"""

import argparse
import sys
from pathlib import Path
from typing import List
import yaml
from tqdm import tqdm

# Fix Windows console encoding for Chinese characters. reconfigure() adjusts
# the stream in place -- rewrapping sys.stdout in a new TextIOWrapper broke
# pytest's capture (the wrapper closed pytest's temp stream when GC'd).
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")

# Import modules
from extract.epub_extractor import extract_text_from_epub
from extract.pdf_extractor import extract_text_from_pdf
from process.text_cleaner import clean_text, split_sentences
from process.tokenizer import tokenize_text, compute_word_frequency, filter_multi_char_words
from process.cedict_loader import load_cedict
from process.word_selector import select_top_words, create_word_cards
from process.hsk_filter import filter_by_hsk, parse_hsk_levels
from process.review import export_cards_to_csv, load_cards_from_csv
from anki.deck_builder import build_deck
from translate.manager import TranslationManager
from utils.file_utils import get_cache_dir, sanitize_filename, write_stats_json


def load_config(config_path: str = None) -> dict:
    """
    Load configuration from YAML file.

    An explicitly passed path must exist -- silently falling back to
    ./config.yaml would run with settings the user didn't choose.
    """
    if config_path:
        if not Path(config_path).exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    if Path("config.yaml").exists():
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    return {}


def resolve_setting(cli_value, config: dict, config_keys: List[str], default):
    """
    Resolve one setting with precedence: CLI > config.yaml > built-in default.

    Args:
        cli_value: Value from the CLI (None means the flag wasn't passed)
        config: Loaded config dictionary
        config_keys: Config keys to try in order (first present wins)
        default: Built-in default

    Returns:
        The effective setting value
    """
    if cli_value is not None:
        return cli_value
    for key in config_keys:
        if config.get(key) is not None:
            return config[key]
    return default


def extract_book(input_path: str):
    """Extract text from EPUB or PDF."""
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print(f"Extracting text from {path.name}...")

    if path.suffix.lower() == ".epub":
        chapters = extract_text_from_epub(str(path))
    elif path.suffix.lower() == ".pdf":
        chapters = extract_text_from_pdf(str(path))
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")

    print(f"Extracted {len(chapters)} chapter(s)")
    return chapters


def generate_word_audio(cards) -> List[str]:
    """
    Generate gTTS word audio for cards (requires internet + the tts extra).

    Sets card.audio_filename on success; gives up after repeated failures
    so a dead network doesn't stall the build.

    Args:
        cards: WordCard list to generate audio for

    Returns:
        Paths of generated media files to bundle into the .apkg
    """
    from tts.gtts_generator import get_or_create_audio, is_available as tts_available

    if not tts_available():
        print("Warning: gTTS not installed (uv sync --extra tts); skipping audio")
        return []

    media_files = []
    print("\nGenerating TTS audio (requires internet)...")
    consecutive_failures = 0
    for card in tqdm(cards, desc="Generating audio", unit="card"):
        audio_path = get_or_create_audio(card.word)
        if audio_path is not None:
            card.audio_filename = audio_path.name
            media_files.append(str(audio_path))
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if consecutive_failures >= 5:
                print("Warning: repeated TTS failures; continuing without audio")
                break
    print(f"Audio generated for {len(media_files)} of {len(cards)} cards")
    return media_files


def process_pipeline(
    input_path: str,
    deck_name: str = None,
    top_words: int = 150,
    min_freq: int = 2,
    output_dir: str = "output",
    min_sentence_length: int = 10,
    max_sentence_length: int = 100,
    stats_file: str = None,
    cloze: bool = False,
    enable_tts: bool = False,
    hsk_levels: List[int] = None,
    translation_config: dict = None,
    review_file: str = None,
    **kwargs,
):
    """
    Main processing pipeline.

    Args:
        input_path: Path to EPUB or PDF file
        deck_name: Name for the Anki deck
        top_words: Number of top words to select
        min_freq: Minimum word frequency
        output_dir: Output directory
        min_sentence_length: Minimum example-sentence length
        max_sentence_length: Maximum example-sentence length
        stats_file: Optional path to export pipeline stats as JSON
        cloze: Build cloze-deletion cards instead of word-in-sentence cards
        enable_tts: Generate word audio with gTTS (requires internet + tts extra)
        hsk_levels: Only keep words from these HSK levels (empty/None = all words)
        translation_config: Raw config dict passed to the translation system
            (backend overrides, preferred_backend, prefer_offline,
            translation_cache)
        review_file: Write cards to this CSV for pre-import QC and stop
            before TTS/deck build (resume with --from-review)
    """
    # Set deck name from filename if not provided
    if deck_name is None:
        deck_name = Path(input_path).stem

    print("=" * 60)
    print(f"Building Anki deck: {deck_name}")
    print("=" * 60)

    # Step 1: Extract text
    chapters = extract_book(input_path)

    # Step 2-3: Clean and split each chapter, tracking which chapter each
    # sentence came from so cards can be tagged with their source chapter.
    print("\nCleaning text and splitting into sentences...")
    sentences = []
    sentence_chapters = {}
    cleaned_chapter_texts = []
    for chapter in chapters:
        cleaned = clean_text(chapter.text)
        if not cleaned:
            continue
        cleaned_chapter_texts.append(cleaned)
        for sent in split_sentences(cleaned):
            sentences.append(sent)
            # First chapter containing a given sentence wins
            sentence_chapters.setdefault(sent, chapter.title)
    cleaned_text = "\n".join(cleaned_chapter_texts)
    print(f"Found {len(sentences)} sentences across {len(chapters)} chapter(s)")

    # Step 4: Tokenize
    print("\nTokenizing text...")
    tokens = tokenize_text(cleaned_text)
    stats = compute_word_frequency(tokens)
    print(f"Total tokens: {stats.total_words}")
    print(f"Unique words: {stats.unique_words}")

    # Step 5: Filter to multi-character words
    print("\nFiltering to multi-character words...")
    multi_char_freq = filter_multi_char_words(stats.word_freq)
    print(f"Multi-character words: {len(multi_char_freq)}")

    # Step 5.5: HSK filtering (optional) -- restrict the candidate pool BEFORE
    # top-N selection so the deck still gets the full requested word count.
    if hsk_levels:
        print(f"\nFiltering to HSK levels {hsk_levels}...")
        candidates = filter_by_hsk(list(multi_char_freq.keys()), hsk_levels)
        multi_char_freq = type(multi_char_freq)(
            {word: multi_char_freq[word] for word in candidates}
        )
        print(f"Words within HSK levels: {len(multi_char_freq)}")

    # Step 6: Select top words
    print(f"\nSelecting top {top_words} words...")
    selected_words = select_top_words(multi_char_freq, top_n=top_words, min_freq=min_freq)
    print(f"Selected {len(selected_words)} words")

    if not selected_words:
        print("ERROR: No words selected. Try lowering min_freq or increasing top_words.")
        sys.exit(1)

    # Step 7: Load dictionary
    print("\nLoading CC-CEDICT dictionary...")
    cedict = load_cedict()

    # Step 7.5: Initialize translation system
    print("\nInitializing translation system...")
    translation_config = translation_config or {}
    # Persistent cross-run cache (re-running the same book skips
    # re-translation); disable with `translation_cache: false` in config.
    cache_path = None
    if translation_config.get("translation_cache", True):
        cache_path = get_cache_dir() / "translations.json"
    translation_manager = TranslationManager(config=translation_config, cache_path=cache_path)
    translation_manager.set_cedict(cedict)
    prefer_offline = translation_config.get("prefer_offline", True)
    if translation_manager.initialize(prefer_offline=prefer_offline):
        print(f"Active translation backend: {translation_manager.get_active_backend_name()}")
    else:
        print("Warning: No translation backend initialized")

    # Step 8: Create word cards (filter out words without definitions)
    print("\nCreating word cards...")
    card_stats = {}
    cards = create_word_cards(
        selected_words,
        sentences,
        multi_char_freq,
        cedict=cedict,
        translation_manager=translation_manager,
        sentence_chapters=sentence_chapters,
        min_sentence_length=min_sentence_length,
        max_sentence_length=max_sentence_length,
        stats_out=card_stats,
    )
    print(f"Created {len(cards)} cards with example sentences")

    # Flush the persistent translation cache and release backend models.
    translation_manager.cleanup()

    if not cards:
        print("ERROR: No cards created. No suitable sentences found.")
        sys.exit(1)

    # Step 8.4: Pre-import QC stop — write the review file and end the run
    # before TTS/deck build, so deleted rows never cost audio downloads.
    if review_file:
        review_path = export_cards_to_csv(cards, review_file, cedict=cedict)
        print(f"\nReview file written to {review_path}")
        print("Edit or delete rows (blank word/sentence = drop), then build with:")
        print(f'  uv run python main.py --from-review "{review_path}" --deck "{deck_name}"')
        return

    # Step 8.5: Generate TTS audio (optional, requires internet)
    media_files = generate_word_audio(cards) if enable_tts else []

    # Step 9: Build Anki deck. The deck keeps its display name; only the
    # filename is sanitized (deck names like "A/B: test" are valid in Anki
    # but illegal or directory-nesting as paths).
    print("\nBuilding Anki deck...")
    output_path = Path(output_dir) / f"{sanitize_filename(deck_name)}.apkg"
    build_deck(
        deck_name, cards, cedict, str(output_path), cloze=cloze, media_files=media_files
    )

    # Step 10: Export stats if requested
    if stats_file:
        covered_tokens = sum(card.frequency for card in cards)
        export = {
            "input": str(input_path),
            "deck_name": deck_name,
            "output": str(output_path),
            "chapters": len(chapters),
            "sentences": len(sentences),
            "total_tokens": stats.total_words,
            "unique_words": stats.unique_words,
            "multi_char_words": len(multi_char_freq),
            "words_selected": len(selected_words),
            "cards_created": len(cards),
            "skipped_no_definition": card_stats.get("skipped_no_definition", 0),
            "skipped_no_sentence": card_stats.get("skipped_no_sentence", 0),
            "token_coverage": round(covered_tokens / stats.total_words, 4)
            if stats.total_words
            else 0.0,
            "translation_backend": translation_manager.get_active_backend_name(),
            "cards": [
                {"word": card.word, "frequency": card.frequency, "chapter": card.chapter}
                for card in cards
            ],
        }
        write_stats_json(stats_file, export)
        print(f"Stats exported to {stats_file}")

    print("\n" + "=" * 60)
    print("✓ Deck generation complete!")
    print(f"✓ Output: {output_path}")
    print(f"✓ Total cards: {len(cards)}")
    print("=" * 60)


def build_from_review(
    review_file: str,
    deck_name: str = None,
    output_dir: str = "output",
    cloze: bool = False,
    enable_tts: bool = False,
):
    """
    Build a deck straight from a reviewed CSV — no extraction, selection,
    or translation. Every field the reviewer edited is authoritative.

    Args:
        review_file: CSV written by --review (and hand-edited)
        deck_name: Name for the Anki deck (default: review filename)
        output_dir: Output directory
        cloze: Build cloze-deletion cards instead of word-in-sentence cards
        enable_tts: Generate word audio with gTTS (requires internet + tts extra)
    """
    if deck_name is None:
        deck_name = Path(review_file).stem

    print("=" * 60)
    print(f"Building Anki deck from review file: {deck_name}")
    print("=" * 60)

    cards = load_cards_from_csv(review_file)
    print(f"Loaded {len(cards)} reviewed cards from {review_file}")

    # CEDICT still backs any blank pinyin/definition cells (e.g. rows the
    # reviewer added by hand).
    print("\nLoading CC-CEDICT dictionary...")
    cedict = load_cedict()

    media_files = generate_word_audio(cards) if enable_tts else []

    print("\nBuilding Anki deck...")
    output_path = Path(output_dir) / f"{sanitize_filename(deck_name)}.apkg"
    build_deck(
        deck_name, cards, cedict, str(output_path), cloze=cloze, media_files=media_files
    )

    print("\n" + "=" * 60)
    print("✓ Deck generation complete!")
    print(f"✓ Output: {output_path}")
    print(f"✓ Total cards: {len(cards)}")
    print("=" * 60)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Anki flashcards for learning Chinese from books",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--input", "-i", help="Input EPUB or PDF file (required unless --from-review)"
    )

    parser.add_argument("--deck", "-d", help="Deck name (default: filename)")

    # Defaults are None so we can tell whether the user actually passed a
    # flag; precedence (CLI > config.yaml > built-in default) is resolved below.
    parser.add_argument(
        "--top-words",
        "-n",
        type=int,
        default=None,
        help="Number of top words to select (default: 150)",
    )

    parser.add_argument(
        "--min-freq",
        "-m",
        type=int,
        default=None,
        help="Minimum word frequency (default: 2)",
    )

    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output directory (default: output)",
    )

    parser.add_argument(
        "--config",
        "-c",
        help="Config file (default: config.yaml)",
    )

    parser.add_argument(
        "--hsk",
        default=None,
        help="Only include HSK words: '3' (up to level 3), '2-4', or '1,3,5'; 7 = 7-9 band",
    )

    parser.add_argument(
        "--stats",
        default=None,
        help="Export pipeline stats to this JSON file (default: config stats_file)",
    )

    parser.add_argument(
        "--cloze",
        action="store_true",
        default=None,
        help="Build cloze-deletion cards (word blanked out of the sentence)",
    )

    parser.add_argument(
        "--tts",
        action="store_true",
        default=None,
        help="Generate word audio with gTTS (requires internet and the tts extra)",
    )

    parser.add_argument(
        "--review",
        default=None,
        metavar="CSV",
        help="Write cards to this CSV for QC and stop before deck build "
        "(edit/delete rows, then use --from-review)",
    )

    parser.add_argument(
        "--from-review",
        default=None,
        metavar="CSV",
        help="Build the deck from a reviewed CSV (skips extraction and translation)",
    )

    args = parser.parse_args()

    if args.from_review and args.input:
        parser.error("--from-review builds from the review file; do not also pass --input")
    if args.from_review and args.review:
        parser.error("--review and --from-review cannot be combined")
    if not args.from_review and not args.input:
        parser.error("--input is required (or use --from-review)")

    # Everything from config loading onward sits inside the error handler so
    # user-input problems (missing --config file, bad --hsk spec) print a
    # friendly ERROR line instead of a traceback.
    try:
        # Resolve settings with precedence: CLI > config.yaml > default
        config = load_config(args.config)

        def resolve(cli_value, config_keys, default):
            return resolve_setting(cli_value, config, config_keys, default)

        if args.from_review:
            build_from_review(
                args.from_review,
                deck_name=resolve(args.deck, ["deck_name"], None),
                output_dir=resolve(args.output, ["output_dir"], "output"),
                cloze=resolve(args.cloze, ["cloze"], False),
                enable_tts=resolve(args.tts, ["enable_tts"], False),
            )
            return

        params = {
            "input_path": args.input,
            "deck_name": resolve(args.deck, ["deck_name"], None),
            "top_words": resolve(args.top_words, ["top_words"], 150),
            "min_freq": resolve(args.min_freq, ["min_freq", "min_frequency"], 2),
            "output_dir": resolve(args.output, ["output_dir"], "output"),
            "enable_tts": resolve(args.tts, ["enable_tts"], False),
            "min_sentence_length": resolve(None, ["min_sentence_length"], 10),
            "max_sentence_length": resolve(None, ["max_sentence_length"], 100),
            "stats_file": resolve(args.stats, ["stats_file"], None),
            "cloze": resolve(args.cloze, ["cloze"], False),
            "hsk_levels": resolve(
                parse_hsk_levels(args.hsk) if args.hsk else None, ["hsk_levels"], []
            ),
            # The translation system reads its own keys (preferred_backend,
            # prefer_offline, translation_cache, model overrides) from the
            # raw config, so documented YAML keys actually reach the backends.
            "translation_config": config,
            "review_file": args.review,
        }

        process_pipeline(**params)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
