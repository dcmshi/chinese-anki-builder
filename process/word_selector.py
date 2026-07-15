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
    # Optional overrides (set by the --from-review workflow); when empty,
    # deck building resolves both from CC-CEDICT as usual.
    word_pinyin: str = ""
    definition: str = ""
    audio_filename: str = ""  # media filename for [sound:...], set by TTS step

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


def build_sentence_index(sentences: List[str]) -> Dict[str, List[int]]:
    """
    Build an inverted index: character bigram -> indices of sentences
    containing it.

    Substring-scanning every sentence per word is O(words x sentences) --
    the dominant cost for large decks. Every word (always 2+ chars here)
    contains its own first bigram, so looking up word[:2] yields a superset
    of the sentences containing the word; the exact `word in sentence` check
    then filters it. Results are therefore IDENTICAL to a full scan, just
    without scanning unrelated sentences. Indices stay in sentence order so
    selection remains deterministic.

    Args:
        sentences: List of sentences to index

    Returns:
        Mapping of bigram -> list of sentence indices (in order)
    """
    index: Dict[str, List[int]] = {}
    for i, sentence in enumerate(sentences):
        seen = set()
        for j in range(len(sentence) - 1):
            bigram = sentence[j : j + 2]
            if bigram not in seen:
                seen.add(bigram)
                index.setdefault(bigram, []).append(i)
    return index


def find_sentence_for_word(
    word: str,
    sentences: List[str],
    min_len: int = 10,
    max_len: int = 100,
    candidates: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Find a good example sentence containing the word.

    Prefers shorter sentences for better readability.

    Args:
        word: The word to find
        sentences: List of sentences to search
        min_len: Minimum acceptable sentence length
        max_len: Maximum acceptable sentence length
        candidates: Optional prefiltered sentences (e.g. from
            build_sentence_index) to search instead of scanning everything

    Returns:
        Best sentence containing the word, or None
    """
    pool = candidates if candidates is not None else sentences
    matching = [sent for sent in pool if word in sent]

    if not matching:
        return None

    # Prefer shorter sentences (easier to understand)
    # But not too short (need context)
    in_range = [sent for sent in matching if min_len <= len(sent) <= max_len]

    # Return shortest suitable sentence (fall back to any match)
    return min(in_range or matching, key=len)


def create_word_cards(
    words: List[str],
    sentences: List[str],
    word_freq: Counter,
    cedict: Dict = None,
    translation_manager: Optional["TranslationManager"] = None,
    chapter: str = "",
    sentence_chapters: Optional[Dict[str, str]] = None,
    min_sentence_length: int = 10,
    max_sentence_length: int = 100,
    stats_out: Optional[Dict] = None,
) -> List[WordCard]:
    """
    Create word cards with example sentences.

    Args:
        words: List of words to create cards for
        sentences: List of sentences to search for examples
        word_freq: Word frequency counter
        cedict: Optional CC-CEDICT dictionary to filter words with definitions
        translation_manager: Optional translation manager for sentence translation
        chapter: Default chapter name (used when a sentence has no mapped chapter)
        sentence_chapters: Optional map of sentence text -> chapter title, used to
            tag each card with the chapter its example sentence came from
        min_sentence_length: Minimum acceptable example-sentence length
        max_sentence_length: Maximum acceptable example-sentence length
        stats_out: Optional dict that receives skip counts
            (skipped_no_definition / skipped_no_sentence) for stats export

    Returns:
        List of WordCard objects
    """
    cards = []
    skipped_no_sentence = 0
    skipped_no_definition = 0

    # One-time index so each word looks up its candidate sentences directly
    # instead of substring-scanning every sentence (O(words x sentences)).
    sentence_index = build_sentence_index(sentences)

    # Phase 1: pick each word's example sentence (no translation yet, so the
    # translation step below can run as one batch instead of per word).
    selections = []
    for word in tqdm(words, desc="Selecting sentences", unit="word"):
        # Check if word has a definition in CEDICT (skip proper nouns, names, etc.)
        if cedict is not None and word not in cedict:
            skipped_no_definition += 1
            continue

        if len(word) >= 2:
            candidates = [sentences[i] for i in sentence_index.get(word[:2], [])]
        else:
            candidates = None  # single-char word: bigram index can't answer
        sentence = find_sentence_for_word(
            word,
            sentences,
            min_len=min_sentence_length,
            max_len=max_sentence_length,
            candidates=candidates,
        )

        if sentence:
            selections.append((word, sentence))
        else:
            skipped_no_sentence += 1

    # Phase 2: translate every selected sentence in one batch call. The
    # manager dedupes repeats and serves cache hits; managers without a
    # translate_batch (simple stubs) fall back to per-sentence calls.
    translations: Dict[str, str] = {}
    if translation_manager is not None and selections:
        unique_sentences = list(dict.fromkeys(sent for _, sent in selections))
        print(f"Translating {len(unique_sentences)} example sentences...")
        batch = getattr(translation_manager, "translate_batch", None)
        if callable(batch):
            translated = batch(unique_sentences)
        else:
            translated = [
                translation_manager.translate(sent)
                for sent in tqdm(unique_sentences, desc="Translating", unit="sentence")
            ]
        translations = dict(zip(unique_sentences, translated))

    # Phase 3: assemble the cards (order still follows the input word list).
    for word, sentence in tqdm(selections, desc="Creating cards", unit="word"):
        sent_pinyin = sentence_to_pinyin(sentence)

        # Tag with the chapter the example sentence came from, if known
        card_chapter = chapter
        if sentence_chapters is not None:
            card_chapter = sentence_chapters.get(sentence, chapter)

        card = WordCard(
            word=word,
            sentence=sentence,
            frequency=word_freq[word],
            chapter=card_chapter,
            sentence_translation=translations.get(sentence, ""),
            sentence_pinyin=sent_pinyin,
        )
        cards.append(card)

    if skipped_no_definition > 0:
        print(f"Skipped {skipped_no_definition} words without dictionary definitions")
    if skipped_no_sentence > 0:
        print(f"Skipped {skipped_no_sentence} words without suitable sentences")

    if stats_out is not None:
        stats_out["skipped_no_definition"] = skipped_no_definition
        stats_out["skipped_no_sentence"] = skipped_no_sentence

    return cards
