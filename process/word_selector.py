"""Select words for Anki cards based on frequency and criteria."""

from collections import Counter
from typing import List, Set, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass
from process.pinyin_converter import sentence_to_pinyin
from tqdm import tqdm

if TYPE_CHECKING:
    from translate.manager import TranslationManager


@dataclass
class WordCard:
    """Represents a word card with context sentence."""

    word: str
    sentence: str
    frequency: int
    chapter: str = ""
    sentence_translation: str = ""
    sentence_pinyin: str = ""

    def __repr__(self):
        return f"WordCard({self.word}, freq={self.frequency}, chapter={self.chapter})"


def select_top_words(
    word_freq: Counter,
    top_n: int = 150,
    min_freq: int = 2,
    exclude_words: Set[str] = None,
) -> List[str]:
    """
    Select top N words by frequency.

    Args:
        word_freq: Counter of word frequencies
        top_n: Number of words to select
        min_freq: Minimum frequency threshold
        exclude_words: Optional set of words to exclude

    Returns:
        List of selected words, sorted by frequency (descending)
    """
    if exclude_words is None:
        exclude_words = set()

    # Filter by minimum frequency and exclusions
    filtered = {
        word: count
        for word, count in word_freq.items()
        if count >= min_freq and word not in exclude_words
    }

    # Get top N words
    top_words = [word for word, count in Counter(filtered).most_common(top_n)]

    return top_words


def find_sentence_for_word(word: str, sentences: List[str]) -> Optional[str]:
    """
    Find a good example sentence containing the word.

    Prefers shorter sentences for better readability.

    Args:
        word: The word to find
        sentences: List of sentences to search

    Returns:
        Best sentence containing the word, or None
    """
    candidates = [sent for sent in sentences if word in sent]

    if not candidates:
        return None

    # Prefer shorter sentences (easier to understand)
    # But not too short (need context)
    candidates = [sent for sent in candidates if 10 <= len(sent) <= 100]

    if not candidates:
        # Fallback to any sentence with the word
        candidates = [sent for sent in sentences if word in sent]

    if not candidates:
        return None

    # Return shortest suitable sentence
    return min(candidates, key=len)


def create_word_cards(
    words: List[str],
    sentences: List[str],
    word_freq: Counter,
    cedict: Dict = None,
    translation_manager: Optional["TranslationManager"] = None,
    chapter: str = "",
) -> List[WordCard]:
    """
    Create word cards with example sentences.

    Args:
        words: List of words to create cards for
        sentences: List of sentences to search for examples
        word_freq: Word frequency counter
        cedict: Optional CC-CEDICT dictionary to filter words with definitions
        translation_manager: Optional translation manager for sentence translation
        chapter: Optional chapter name

    Returns:
        List of WordCard objects
    """
    cards = []
    skipped_no_sentence = 0
    skipped_no_definition = 0

    # Progress bar for word card creation
    for word in tqdm(words, desc="Creating cards", unit="word"):
        # Check if word has a definition in CEDICT (skip proper nouns, names, etc.)
        if cedict is not None and word not in cedict:
            skipped_no_definition += 1
            continue

        sentence = find_sentence_for_word(word, sentences)

        if sentence:
            # Generate sentence translation using translation manager
            translation = ""
            if translation_manager is not None:
                translation = translation_manager.translate(sentence)

            # Generate sentence pinyin
            sent_pinyin = sentence_to_pinyin(sentence)

            card = WordCard(
                word=word,
                sentence=sentence,
                frequency=word_freq[word],
                chapter=chapter,
                sentence_translation=translation,
                sentence_pinyin=sent_pinyin,
            )
            cards.append(card)
        else:
            skipped_no_sentence += 1

    if skipped_no_definition > 0:
        print(f"Skipped {skipped_no_definition} words without dictionary definitions")
    if skipped_no_sentence > 0:
        print(f"Skipped {skipped_no_sentence} words without suitable sentences")

    return cards
