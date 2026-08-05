"""Build Anki deck from word cards."""

import genanki
import html
import re
from typing import List, Dict, Optional
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

    Every occurrence is highlighted, including one nested inside a longer word
    (学习 inside 学习者). That is deliberate: card words always carry 2+ Han
    characters, so a nested match is the same morpheme rather than a
    coincidence, and marking it needs no re-tokenization of the sentence --
    which would also have to agree with jieba's segmentation of hand-edited
    --from-review rows.

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

    return escaped_sentence.replace(escaped_word, f'<span class="target">{escaped_word}</span>')


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


def resolve_word_pinyin(card: WordCard, cedict: Dict[str, DictEntry]) -> str:
    """Reviewer override wins, otherwise CEDICT/pypinyin tone-mark pinyin."""
    return card.word_pinyin or word_to_pinyin(card.word, cedict)


def resolve_definition(
    card: WordCard,
    cedict: Dict[str, DictEntry],
    missing_out: Optional[List[str]] = None,
) -> str:
    """
    Reviewer override wins, otherwise the preferred CEDICT sense.

    Args:
        card: The card being rendered
        cedict: CC-CEDICT dictionary
        missing_out: Optional list that collects words with no definition, so
            build_deck can print one summary instead of a line per card
            (which flooded output and garbled the progress bar)
    """
    if card.definition:
        return card.definition
    if cedict and card.word in cedict:
        return cedict[card.word].get_first_definition()
    # Fallback for words not in dictionary (shouldn't happen after filtering)
    if missing_out is not None:
        missing_out.append(card.word)
    return "[Definition not found in CC-CEDICT]"


def create_anki_note(
    card: WordCard,
    cedict: Dict[str, DictEntry],
    model: genanki.Model,
    missing_out: Optional[List[str]] = None,
) -> genanki.Note:
    """
    Create an Anki note from a word card.

    Audio is driven by card.audio_filename (set by the TTS step); the media
    file itself ships via the package's media_files.

    Every text field is HTML-escaped: Anki renders fields as HTML, so a stray
    "<" or "&" from extraction (chapter titles taken from EPUB headings are
    raw markup text) would otherwise mangle the card. Audio fields hold
    generated [sound:...] references and are left alone.

    Args:
        card: WordCard object
        cedict: CC-CEDICT dictionary
        model: Anki model
        missing_out: Optional list collecting words with no definition

    Returns:
        genanki.Note object
    """
    pinyin = resolve_word_pinyin(card, cedict)
    definition = resolve_definition(card, cedict, missing_out=missing_out)

    # Get sentence pinyin
    sentence_pinyin = card.sentence_pinyin or ""

    # Get sentence translation
    sentence_translation = card.sentence_translation or ""

    # Audio references (media files themselves ship via the package's media_files)
    audio = f"[sound:{card.audio_filename}]" if card.audio_filename else ""
    sentence_audio = (
        f"[sound:{card.sentence_audio_filename}]" if card.sentence_audio_filename else ""
    )

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
            html.escape(card.word),  # Word
            highlight_word_in_sentence(card.word, card.sentence),  # Sentence
            html.escape(sentence_pinyin),  # SentencePinyin
            html.escape(pinyin),  # Pinyin (word)
            html.escape(definition),  # Definition
            html.escape(sentence_translation),  # SentenceTranslation
            audio,  # Audio
            html.escape(card.chapter),  # Chapter
            sentence_audio,  # SentenceAudio (appended last: safest for reimports)
        ],
        guid=generate_note_guid(card.word, card.sentence),
    )

    return note


def create_cloze_note(
    card: WordCard,
    cedict: Dict[str, DictEntry],
    model: genanki.Model,
    missing_out: Optional[List[str]] = None,
) -> genanki.Note:
    """
    Create a cloze note (sentence with the target word blanked) from a card.

    Args:
        card: WordCard object
        cedict: CC-CEDICT dictionary
        model: Anki cloze model
        missing_out: Optional list collecting words with no definition

    Returns:
        genanki.Note object
    """
    pinyin = resolve_word_pinyin(card, cedict)
    definition = resolve_definition(card, cedict, missing_out=missing_out)

    tag = chapter_to_tag(card.chapter)

    audio = f"[sound:{card.audio_filename}]" if card.audio_filename else ""
    sentence_audio = (
        f"[sound:{card.sentence_audio_filename}]" if card.sentence_audio_filename else ""
    )

    # Distinct GUID namespace so a cloze deck and a regular deck built from
    # the same book never collide on import.
    return genanki.Note(
        model=model,
        tags=[tag] if tag else [],
        fields=[
            cloze_sentence(card.word, card.sentence),  # Text
            html.escape(card.word),  # Word
            html.escape(pinyin),  # Pinyin
            html.escape(definition),  # Definition
            html.escape(card.sentence_pinyin or ""),  # SentencePinyin
            html.escape(card.sentence_translation or ""),  # SentenceTranslation
            audio,  # Audio
            html.escape(card.chapter),  # Chapter
            sentence_audio,  # SentenceAudio (appended last: safest for reimports)
        ],
        guid=generate_note_guid(card.word, f"cloze::{card.sentence}"),
    )


def build_deck(
    deck_name: str,
    cards: List[WordCard],
    cedict: Dict[str, DictEntry],
    output_path: str,
    cloze: bool = False,
    media_files: Optional[List[str]] = None,
) -> Path:
    """
    Build and save an Anki deck.

    Cloze notes whose text carries no deletion are dropped: Anki rejects them
    on import with "no cloze deletions found", and the condition is reachable
    whenever a card's word isn't a literal substring of its sentence.

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

    # Create and add notes with progress bar. Warnings are collected rather
    # than printed per card (one line per card garbles the progress bar).
    missing_definitions: List[str] = []
    invalid_cloze: List[str] = []
    for card in tqdm(cards, desc="Building deck", unit="card"):
        if cloze:
            note = create_cloze_note(card, cedict, model, missing_out=missing_definitions)
            if "{{c1::" not in note.fields[0]:
                invalid_cloze.append(card.word)
                continue
        else:
            note = create_anki_note(card, cedict, model, missing_out=missing_definitions)
        deck.add_note(note)

    if missing_definitions:
        sample = ", ".join(missing_definitions[:5])
        more = f" (+{len(missing_definitions) - 5} more)" if len(missing_definitions) > 5 else ""
        print(
            f"Warning: no definition found for {len(missing_definitions)} word(s): {sample}{more}"
        )
    if invalid_cloze:
        sample = ", ".join(invalid_cloze[:5])
        more = f" (+{len(invalid_cloze) - 5} more)" if len(invalid_cloze) > 5 else ""
        print(
            f"Warning: skipped {len(invalid_cloze)} card(s) whose word is absent from "
            f"the sentence, so no cloze deletion could be made: {sample}{more}"
        )

    # Save deck
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    genanki.Package(deck, media_files=media_files or []).write_to_file(str(output_path))

    print(f"Deck saved to {output_path}")
    return output_path
