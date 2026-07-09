"""Build Anki deck from word cards."""

import genanki
import html
from typing import List, Dict
from pathlib import Path
import hashlib
from tqdm import tqdm

from anki.templates import get_chinese_model
from process.word_selector import WordCard
from process.cedict_loader import DictEntry
from process.pinyin_converter import word_to_pinyin


def generate_note_guid(word: str, sentence: str) -> str:
    """
    Generate a deterministic note GUID from word and sentence.

    This ensures the same card always gets the same GUID. The full 128-bit
    hash is used: truncating (an earlier version kept 32 bits) makes birthday
    collisions realistic at deck sizes of a few thousand cards, and notes
    sharing a GUID silently overwrite each other on Anki import.

    Args:
        word: The word
        sentence: The sentence

    Returns:
        Hex-string GUID for the note
    """
    content = f"{word}::{sentence}"
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def highlight_word_in_sentence(word: str, sentence: str) -> str:
    """
    Return sentence HTML with every occurrence of word wrapped in a
    highlight span (styled by the card CSS).

    Both strings are HTML-escaped first so stray <, >, & from extraction
    can't break the card template.

    Args:
        word: The target word
        sentence: The example sentence containing it

    Returns:
        HTML string for the Sentence field
    """
    escaped_sentence = html.escape(sentence)
    escaped_word = html.escape(word)

    if not escaped_word:
        return escaped_sentence

    return escaped_sentence.replace(
        escaped_word, f'<span class="target">{escaped_word}</span>'
    )


def create_anki_note(
    card: WordCard,
    cedict: Dict[str, DictEntry],
    model: genanki.Model,
    include_audio: bool = False,
) -> genanki.Note:
    """
    Create an Anki note from a word card.

    Args:
        card: WordCard object
        cedict: CC-CEDICT dictionary
        model: Anki model
        include_audio: Whether to include audio (not implemented yet)

    Returns:
        genanki.Note object
    """
    # Get pinyin for the word
    pinyin = word_to_pinyin(card.word, cedict)

    # Get sentence pinyin
    sentence_pinyin = card.sentence_pinyin or ""

    # Get definition from CEDICT
    definition = ""
    if card.word in cedict:
        definition = cedict[card.word].get_first_definition()
    else:
        # Fallback for words not in dictionary (shouldn't happen after filtering)
        definition = "[Definition not found in CC-CEDICT]"
        print(f"Warning: No definition found for '{card.word}'")

    # Get sentence translation
    sentence_translation = card.sentence_translation or ""

    # For now, no audio
    audio = ""

    # Create note with deterministic ID (GUID from the raw sentence so
    # highlight markup changes don't orphan existing notes)
    note = genanki.Note(
        model=model,
        fields=[
            card.word,  # Word
            highlight_word_in_sentence(card.word, card.sentence),  # Sentence
            sentence_pinyin,  # SentencePinyin
            pinyin,  # Pinyin (word)
            definition,  # Definition
            sentence_translation,  # SentenceTranslation
            audio,  # Audio
            card.chapter,  # Chapter
        ],
        guid=generate_note_guid(card.word, card.sentence),
    )

    return note


def build_deck(
    deck_name: str,
    cards: List[WordCard],
    cedict: Dict[str, DictEntry],
    output_path: str,
    include_audio: bool = False,
) -> Path:
    """
    Build and save an Anki deck.

    Args:
        deck_name: Name of the deck
        cards: List of WordCard objects
        cedict: CC-CEDICT dictionary
        output_path: Path to save the .apkg file
        include_audio: Whether to include audio

    Returns:
        Path to the created .apkg file
    """
    # Generate deterministic deck ID from name
    deck_id = int(hashlib.md5(deck_name.encode("utf-8")).hexdigest()[:8], 16)

    # Create deck
    deck = genanki.Deck(deck_id, deck_name)

    # Get model
    model = get_chinese_model()

    # Create and add notes with progress bar
    for card in tqdm(cards, desc="Building deck", unit="card"):
        note = create_anki_note(card, cedict, model, include_audio)
        deck.add_note(note)

    # Save deck
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    genanki.Package(deck).write_to_file(str(output_path))

    print(f"Deck saved to {output_path}")
    return output_path
