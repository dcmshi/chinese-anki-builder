#!/usr/bin/env python3
"""
Anki Chinese Deck Builder

Generate Anki flashcards for learning Chinese from EPUB and PDF books.
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List
import yaml

# Fix Windows console encoding for Chinese characters
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Import modules
from extract.epub_extractor import extract_text_from_epub, get_full_text
from extract.pdf_extractor import extract_text_from_pdf
from process.text_cleaner import clean_text, split_sentences
from process.tokenizer import tokenize_text, compute_word_frequency, filter_multi_char_words
from process.cedict_loader import load_cedict
from process.word_selector import select_top_words, create_word_cards
from anki.deck_builder import build_deck
from translate.manager import TranslationManager


def load_config(config_path: str = None) -> dict:
    """Load configuration from YAML file."""
    if config_path and Path(config_path).exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    elif Path("config.yaml").exists():
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    else:
        return {}


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


def process_pipeline(
    input_path: str,
    deck_name: str = None,
    top_words: int = 150,
    min_freq: int = 2,
    output_dir: str = "output",
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
    """
    # Set deck name from filename if not provided
    if deck_name is None:
        deck_name = Path(input_path).stem

    print("=" * 60)
    print(f"Building Anki deck: {deck_name}")
    print("=" * 60)

    # Step 1: Extract text
    chapters = extract_book(input_path)
    full_text = get_full_text(chapters)

    # Step 2: Clean text
    print("\nCleaning text...")
    cleaned_text = clean_text(full_text)

    # Step 3: Split into sentences
    print("Splitting into sentences...")
    sentences = split_sentences(cleaned_text)
    print(f"Found {len(sentences)} sentences")

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
    translation_manager = TranslationManager()
    translation_manager.set_cedict(cedict)
    if translation_manager.initialize(prefer_offline=True):
        print(f"Active translation backend: {translation_manager.get_active_backend_name()}")
    else:
        print("Warning: No translation backend initialized")

    # Step 8: Create word cards (filter out words without definitions)
    print("\nCreating word cards...")
    cards = create_word_cards(
        selected_words,
        sentences,
        multi_char_freq,
        cedict=cedict,
        translation_manager=translation_manager
    )
    print(f"Created {len(cards)} cards with example sentences")

    if not cards:
        print("ERROR: No cards created. No suitable sentences found.")
        sys.exit(1)

    # Step 9: Build Anki deck
    print("\nBuilding Anki deck...")
    output_path = Path(output_dir) / f"{deck_name}.apkg"
    build_deck(deck_name, cards, cedict, str(output_path))

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

    parser.add_argument("--input", "-i", required=True, help="Input EPUB or PDF file")

    parser.add_argument("--deck", "-d", help="Deck name (default: filename)")

    parser.add_argument(
        "--top-words",
        "-n",
        type=int,
        default=150,
        help="Number of top words to select (default: 150)",
    )

    parser.add_argument(
        "--min-freq",
        "-m",
        type=int,
        default=2,
        help="Minimum word frequency (default: 2)",
    )

    parser.add_argument(
        "--output",
        "-o",
        default="output",
        help="Output directory (default: output)",
    )

    parser.add_argument(
        "--config",
        "-c",
        help="Config file (default: config.yaml)",
    )

    parser.add_argument(
        "--tts",
        action="store_true",
        help="Enable TTS audio generation (not implemented yet)",
    )

    args = parser.parse_args()

    # Load config and merge with args
    config = load_config(args.config)

    # Command line args override config
    params = {
        "input_path": args.input,
        "deck_name": args.deck,
        "top_words": args.top_words,
        "min_freq": args.min_freq,
        "output_dir": args.output,
        "enable_tts": args.tts,
    }

    # Merge config (config values used only if not specified in args)
    for key, value in config.items():
        if key in params and params[key] is None:
            params[key] = value

    try:
        process_pipeline(**params)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
