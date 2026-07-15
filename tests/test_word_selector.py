"""Tests for word selection and card creation."""

from collections import Counter
from process.word_selector import (
    build_sentence_index,
    select_top_words,
    find_sentence_for_word,
    create_word_cards,
    WordCard,
)
from process.cedict_loader import DictEntry


class TestWordSelector:
    """Test word selection functionality."""

    def test_select_top_words_basic(self):
        """Test basic word selection by frequency."""
        word_freq = Counter({"你好": 10, "世界": 8, "中国": 6, "学习": 4, "汉语": 2})

        selected = select_top_words(word_freq, top_n=3, min_freq=1)

        assert len(selected) == 3
        assert "你好" in selected  # Highest frequency
        assert "世界" in selected
        assert "中国" in selected

    def test_select_top_words_min_freq(self):
        """Test minimum frequency filtering."""
        word_freq = Counter({"你好": 10, "世界": 2, "中国": 1})

        selected = select_top_words(word_freq, top_n=10, min_freq=3)

        assert len(selected) == 1
        assert "你好" in selected
        assert "世界" not in selected
        assert "中国" not in selected

    def test_select_top_words_exclude(self):
        """Test word exclusion."""
        word_freq = Counter({"你好": 10, "世界": 8, "中国": 6})
        exclude = {"你好"}

        selected = select_top_words(word_freq, top_n=2, exclude_words=exclude)

        assert len(selected) == 2
        assert "你好" not in selected
        assert "世界" in selected
        assert "中国" in selected

    def test_find_sentence_for_word(self):
        """Test finding example sentences."""
        sentences = [
            "你好",  # Too short (< 10 chars)
            "你好世界这是一个测试",  # 10 chars, suitable
            "这是一个很长的句子包含了你好这个词语在里面测试用例",  # Long but acceptable
            "简短句子你好在这里",  # 9 chars, too short
        ]

        result = find_sentence_for_word("你好", sentences)

        assert result is not None
        assert "你好" in result
        # Should find a sentence in the acceptable range (10-100 chars)
        assert len(result) >= 10

    def test_find_sentence_no_match(self):
        """Test when word not found in sentences."""
        sentences = ["你好世界", "中国加油"]

        result = find_sentence_for_word("学习", sentences)

        assert result is None

    def test_create_word_cards_with_cedict(self):
        """Test card creation filters out words without definitions."""
        words = ["你好", "罗辑", "世界"]  # "罗辑" is a name, not in dict
        sentences = [
            "你好世界",
            "罗辑说话了",
            "这是世界",
        ]
        word_freq = Counter({"你好": 10, "罗辑": 5, "世界": 8})

        # Mock CEDICT with only some words
        cedict = {
            "你好": DictEntry("你好", "你好", "nǐ hǎo", ["hello"]),
            "世界": DictEntry("世界", "世界", "shì jiè", ["world"]),
        }

        cards = create_word_cards(words, sentences, word_freq, cedict=cedict)

        # Should only create cards for words in CEDICT
        assert len(cards) == 2
        card_words = [card.word for card in cards]
        assert "你好" in card_words
        assert "世界" in card_words
        assert "罗辑" not in card_words  # Filtered out - no definition

    def test_create_word_cards_without_cedict(self):
        """Test card creation without CEDICT filtering."""
        words = ["你好", "罗辑"]
        sentences = ["你好世界", "罗辑说话了"]
        word_freq = Counter({"你好": 10, "罗辑": 5})

        # Without cedict, should create cards for all words
        cards = create_word_cards(words, sentences, word_freq, cedict=None)

        assert len(cards) == 2

    def test_create_word_cards_no_sentence(self):
        """Test cards are not created when no suitable sentence found."""
        words = ["你好", "学习"]
        sentences = ["你好世界"]  # No sentence with "学习"
        word_freq = Counter({"你好": 10, "学习": 5})
        cedict = {
            "你好": DictEntry("你好", "你好", "nǐ hǎo", ["hello"]),
            "学习": DictEntry("学习", "学习", "xué xí", ["to study"]),
        }

        cards = create_word_cards(words, sentences, word_freq, cedict=cedict)

        # Only "你好" should have a card
        assert len(cards) == 1
        assert cards[0].word == "你好"

    def test_build_sentence_index_maps_bigrams_to_sentences(self):
        sentences = ["我在学习中文。", "他喜欢学习。", "你好世界。"]

        index = build_sentence_index(sentences)

        assert index["学习"] == [0, 1]
        assert index["你好"] == [2]
        # Bigrams spanning word boundaries are indexed too (习中 from 学习中文)
        assert index["习中"] == [0]

    def test_find_sentence_with_candidates_matches_full_scan(self):
        """The indexed path must return the same sentence the exhaustive
        substring scan would."""
        sentences = [
            "他每天都在图书馆学习到深夜。",
            "我们一起学习中文很开心。",
            "学习使人进步。",  # too short (< 10), in-range preferred
        ]
        index = build_sentence_index(sentences)
        candidates = [sentences[i] for i in index.get("学习", [])]

        via_index = find_sentence_for_word("学习", sentences, candidates=candidates)
        via_scan = find_sentence_for_word("学习", sentences)

        assert via_index == via_scan

    def test_substring_occurrences_still_found_via_index(self):
        """The bigram index must preserve exact substring semantics: a word
        embedded mid-sentence (regardless of tokenization) is still found."""
        words = ["你好"]
        sentences = ["这是一个包含你好字样的长句子。"]
        word_freq = Counter({"你好": 3})

        cards = create_word_cards(words, sentences, word_freq, cedict=None)

        assert len(cards) == 1
        assert "你好" in cards[0].sentence

    def test_absent_word_yields_no_card_via_index(self):
        words = ["宇宙"]
        sentences = ["这个句子里没有那个词汇存在。"]
        word_freq = Counter({"宇宙": 2})

        cards = create_word_cards(words, sentences, word_freq, cedict=None)

        assert cards == []

    def test_create_word_cards_fills_stats_out(self):
        """Skip counts are exposed for stats export, not just printed."""
        words = ["你好", "罗辑", "学习"]  # 罗辑: no definition; 学习: no sentence
        sentences = ["你好世界"]
        word_freq = Counter({"你好": 10, "罗辑": 5, "学习": 3})
        cedict = {
            "你好": DictEntry("你好", "你好", "ni3 hao3", ["hello"]),
            "学习": DictEntry("學習", "学习", "xue2 xi2", ["to study"]),
        }

        stats = {}
        cards = create_word_cards(words, sentences, word_freq, cedict=cedict, stats_out=stats)

        assert len(cards) == 1
        assert stats == {"skipped_no_definition": 1, "skipped_no_sentence": 1}

    def test_word_card_structure(self):
        """Test WordCard has correct structure."""
        card = WordCard(
            word="你好",
            sentence="你好世界",
            frequency=10,
            chapter="Chapter 1"
        )

        assert card.word == "你好"
        assert card.sentence == "你好世界"
        assert card.frequency == 10
        assert card.chapter == "Chapter 1"


class TestBatchedTranslation:
    """create_word_cards translates all example sentences in one batch."""

    def test_manager_with_translate_batch_is_called_once(self):
        class BatchManager:
            def __init__(self):
                self.batch_calls = []
                self.single_calls = 0

            def translate(self, text, source_lang="zh", target_lang="en"):
                self.single_calls += 1
                return f"single:{text}"

            def translate_batch(self, texts, source_lang="zh", target_lang="en"):
                self.batch_calls.append(list(texts))
                return [f"batch:{t}" for t in texts]

        manager = BatchManager()
        # Both words share one sentence, so the batch must be deduplicated.
        sentences = ["你好世界这是一个测试句子。"]
        words = ["你好", "世界"]
        word_freq = Counter({"你好": 3, "世界": 2})

        cards = create_word_cards(
            words, sentences, word_freq, cedict=None, translation_manager=manager
        )

        assert len(cards) == 2
        assert manager.batch_calls == [["你好世界这是一个测试句子。"]]
        assert manager.single_calls == 0
        assert all(c.sentence_translation == "batch:你好世界这是一个测试句子。" for c in cards)

    def test_manager_without_translate_batch_still_works(self):
        """Simple managers/stubs exposing only translate() keep working."""

        class SingleManager:
            def translate(self, text, source_lang="zh", target_lang="en"):
                return f"single:{text}"

        cards = create_word_cards(
            ["你好"],
            ["你好世界这是一个测试句子。"],
            Counter({"你好": 3}),
            cedict=None,
            translation_manager=SingleManager(),
        )

        assert len(cards) == 1
        assert cards[0].sentence_translation == "single:你好世界这是一个测试句子。"
