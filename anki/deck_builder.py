"""Build Anki deck from word cards."""

import genanki
import html
import re
from typing import List, Dict
from pathlib import Path
import hashlib
from tqdm import tqdm

from anki.templates import get_chinese_model, get_chinese_cloze_model
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


def cloze_sentence(word: str, sentence: str) -> str:
    """
    Return sentence HTML with every occurrence of word turned into an Anki
    cloze deletion ({{c1::word}}).

    Args:
        word: The target word to blank out
        sentence: The example sentence containing it

    Returns:
        Cloze-marked HTML string for the Text field
    """
    escaped_sentence = html.escape(sentence)
    escaped_word = html.escape(word)

    if not escaped_word or escaped_word not in escaped_sentence:
        # A cloze note without a deletion is invalid in Anki; callers only
        # pass sentences known to contain the word, but stay safe.
        return escaped_sentence

    return escaped_sentence.replace(escaped_word, "{{c1::" + escaped_word + "}}")


def generate_deck_id(deck_name: str) -> int:
    """
    Deterministic deck ID from name. 15 hex chars = 60 bits: within Anki's
    signed-int64 range but wide enough that two deck names colliding (and
    thus being treated as the SAME deck by Anki) is no longer a realistic
    birthday risk, unlike the earlier 32-bit truncation.

    Args:
        deck_name: Name of the deck

    Returns:
        Integer deck ID
    """
    return int(hashlib.md5(deck_name.encode("utf-8")).hexdigest()[:15], 16)


def chapter_to_tag(chapter: str) -> str:
    """
    Turn a chapter title into a valid Anki tag.

    Anki tags cannot contain whitespace, so runs of it become underscores.
    The chapter:: prefix groups all chapter tags hierarchically in Anki's
    browser sidebar.

    Args:
        chapter: Chapter title (may be empty)

    Returns:
        Tag string, or "" for an empty/blank chapter
    """
    sanitized = re.sub(r"\s+", "_", chapter.strip())
    return f"chapter::{sanitized}" if sanitized else ""


def create_anki_note(
    card: WordCard,
    cedict: Dict[str, DictEntry],
    model: genanki.Model,
) -> genanki.Note:
    """
    Create an Anki note from a word card.

    Audio is driven by card.audio_filename (set by the TTS step); the media
    file itself ships via the package's media_files.

    Args:
        card: WordCard object
        cedict: CC-CEDICT dictionary
        model: Anki model

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

    # Audio reference (media file itself ships via the package's media_files)
    audio = f"[sound:{card.audio_filename}]" if card.audio_filename else ""

    # Chapter as a real Anki tag (in addition to the field) so decks can be
    # filtered/studied per chapter in Anki's browser.
    tag = chapter_to_tag(card.chapter)
    tags = [tag] if tag else []

    # Create note with deterministic ID (GUID from the raw sentence so
    # highlight markup changes don't orphan existing notes)
    note = genanki.Note(
        model=model,
        tags=tags,
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


def create_cloze_note(
    card: WordCard,
    cedict: Dict[str, DictEntry],
    model: genanki.Model,
) -> genanki.Note:
    """
    Create a cloze note (sentence with the target word blanked) from a card.

    Args:
        card: WordCard object
        cedict: CC-CEDICT dictionary
        model: Anki cloze model

    Returns:
        genanki.Note object
    """
    pinyin = word_to_pinyin(card.word, cedict)

    definition = ""
    if card.word in cedict:
        definition = cedict[card.word].get_first_definition()
    else:
        definition = "[Definition not found in CC-CEDICT]"

    tag = chapter_to_tag(card.chapter)

    audio = f"[sound:{card.audio_filename}]" if card.audio_filename else ""

    # Distinct GUID namespace so a cloze deck and a regular deck built from
    # the same book never collide on import.
    return genanki.Note(
        model=model,
        tags=[tag] if tag else [],
        fields=[
            cloze_sentence(card.word, card.sentence),  # Text
            card.word,  # Word
            pinyin,  # Pinyin
            definition,  # Definition
            card.sentence_pinyin or "",  # SentencePinyin
            card.sentence_translation or "",  # SentenceTranslation
            audio,  # Audio
            card.chapter,  # Chapter
        ],
        guid=generate_note_guid(card.word, f"cloze::{card.sentence}"),
    )


def build_deck(
    deck_name: str,
    cards: List[WordCard],
    cedict: Dict[str, DictEntry],
    output_path: str,
    cloze: bool = False,
    media_files: List[str] = None,
) -> Path:
    """
    Build and save an Anki deck.

    Args:
        deck_name: Name of the deck
        cards: List of WordCard objects
        cedict: CC-CEDICT dictionary
        output_path: Path to save the .apkg file
        cloze: Build cloze-deletion cards instead of word-in-sentence cards
        media_files: Paths of audio files to bundle into the .apkg

    Returns:
        Path to the created .apkg file
    """
    # Create deck with a deterministic ID
    deck = genanki.Deck(generate_deck_id(deck_name), deck_name)

    # Get model
    model = get_chinese_cloze_model() if cloze else get_chinese_model()

    # Create and add notes with progress bar
    for card in tqdm(cards, desc="Building deck", unit="card"):
        if cloze:
            note = create_cloze_note(card, cedict, model)
        else:
            note = create_anki_note(card, cedict, model)
        deck.add_note(note)

    # Save deck
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    genanki.Package(deck, media_files=media_files or []).write_to_file(str(output_path))

    print(f"Deck saved to {output_path}")
    return output_path
