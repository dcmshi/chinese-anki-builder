"""Tests for word-list loading and card building (--wordlist)."""

import sys

import pytest

import main
from anki.card_render import resolve_faces
from anki.deck_builder import build_deck, create_anki_note
from anki.templates import get_chinese_model
from process.cedict_loader import DictEntry
from process.wordlist import WordListEntry, load_wordlist
from process.word_selector import create_wordlist_cards


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def cedict():
    return {
        "学习": DictEntry("學習", "学习", "xue2 xi2", ["to learn", "to study"]),
        "朋友": DictEntry("朋友", "朋友", "peng2 you5", ["friend"]),
        "爱": DictEntry("愛", "爱", "ai4", ["to love"]),
    }


class TestLoadWordlist:
    def test_txt_one_word_per_line(self, tmp_path):
        path = _write(tmp_path, "hsk1.txt", "爱\n八\n\n# comment\n爸爸\n")
        assert [e.word for e in load_wordlist(path)] == ["爱", "八", "爸爸"]

    def test_txt_ignores_extra_columns(self, tmp_path):
        path = _write(tmp_path, "list.txt", "学习\txué xí\tto study\n朋友,péng you\n")
        assert [e.word for e in load_wordlist(path)] == ["学习", "朋友"]

    def test_duplicates_keep_first_occurrence(self, tmp_path):
        path = _write(tmp_path, "list.txt", "学习\n朋友\n学习\n")
        assert [e.word for e in load_wordlist(path)] == ["学习", "朋友"]

    def test_csv_header_matched_by_name(self, tmp_path):
        path = _write(
            tmp_path,
            "hsk.csv",
            "pinyin,simplified,meaning,example\n"
            "xué xí,学习,to study,我喜欢学习汉语。\n"
            "péng you,朋友,friend,\n",
        )
        assert load_wordlist(path) == [
            WordListEntry(
                "学习", sentence="我喜欢学习汉语。", pinyin="xué xí", definition="to study"
            ),
            WordListEntry("朋友", pinyin="péng you", definition="friend"),
        ]

    def test_csv_without_header_uses_first_column(self, tmp_path):
        path = _write(tmp_path, "list.csv", "学习,xué xí\n朋友,péng you\n")
        assert [e.word for e in load_wordlist(path)] == ["学习", "朋友"]

    def test_tsv_with_header(self, tmp_path):
        path = _write(tmp_path, "list.tsv", "word\tdefinition\n学习\tto study\n")
        assert load_wordlist(path) == [WordListEntry("学习", definition="to study")]

    def test_utf8_bom_tolerated(self, tmp_path):
        path = tmp_path / "bom.csv"
        path.write_bytes("word\n学习\n".encode("utf-8-sig"))
        assert [e.word for e in load_wordlist(path)] == ["学习"]

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_wordlist(tmp_path / "nope.txt")

    def test_unsupported_format_raises(self, tmp_path):
        with pytest.raises(ValueError):
            load_wordlist(_write(tmp_path, "list.json", "[]"))


class TestCreateWordlistCards:
    def test_keeps_list_order_and_single_chars(self, cedict):
        entries = [WordListEntry("朋友"), WordListEntry("爱"), WordListEntry("学习")]
        cards = create_wordlist_cards(entries, cedict=cedict)
        assert [c.word for c in cards] == ["朋友", "爱", "学习"]

    def test_book_sentence_preferred_over_list_sentence(self, cedict):
        book = ["我每天都在图书馆学习汉语。"]
        cards = create_wordlist_cards(
            [WordListEntry("学习", sentence="列表里的学习例句。")],
            sentences=book,
            cedict=cedict,
            sentence_chapters={book[0]: "第一章"},
        )
        assert cards[0].sentence == book[0]
        assert cards[0].chapter == "第一章"
        assert cards[0].sentence_pinyin

    def test_single_char_word_found_in_book(self, cedict):
        cards = create_wordlist_cards(
            [WordListEntry("爱")], sentences=["我很爱我的家人和朋友们。"], cedict=cedict
        )
        assert cards[0].sentence == "我很爱我的家人和朋友们。"

    def test_falls_back_to_list_sentence(self, cedict):
        cards = create_wordlist_cards(
            [WordListEntry("学习", sentence="我喜欢学习汉语。")],
            sentences=["没有这个词的句子。"],
            cedict=cedict,
        )
        assert cards[0].sentence == "我喜欢学习汉语。"

    def test_word_only_card_when_no_sentence(self, cedict):
        stats = {}
        cards = create_wordlist_cards([WordListEntry("朋友")], cedict=cedict, stats_out=stats)
        assert cards[0].sentence == ""
        assert cards[0].sentence_pinyin == ""
        assert stats["word_only"] == 1

    def test_skips_words_without_any_definition(self, cedict):
        stats = {}
        cards = create_wordlist_cards(
            [WordListEntry("学习"), WordListEntry("不存在词")], cedict=cedict, stats_out=stats
        )
        assert [c.word for c in cards] == ["学习"]
        assert stats["skipped_no_definition"] == 1

    def test_list_overrides_become_card_overrides(self, cedict):
        cards = create_wordlist_cards(
            [WordListEntry("打电话", pinyin="dǎ diànhuà", definition="to make a phone call")],
            cedict=cedict,
        )
        note = create_anki_note(cards[0], cedict, get_chinese_model())
        assert note.fields[3] == "dǎ diànhuà"
        assert note.fields[4] == "to make a phone call"

    def test_only_sentences_are_translated(self, cedict):
        class StubTranslator:
            def __init__(self):
                self.calls = []

            def translate_batch(self, sentences):
                self.calls.append(list(sentences))
                return [f"EN:{s}" for s in sentences]

        stub = StubTranslator()
        cards = create_wordlist_cards(
            [WordListEntry("学习", sentence="我喜欢学习汉语。"), WordListEntry("朋友")],
            cedict=cedict,
            translation_manager=stub,
        )
        assert stub.calls == [["我喜欢学习汉语。"]]
        assert cards[0].sentence_translation == "EN:我喜欢学习汉语。"
        assert cards[1].sentence_translation == ""


class TestWordOnlyRendering:
    def test_preview_front_shows_word(self, cedict):
        card = create_wordlist_cards([WordListEntry("朋友")], cedict=cedict)[0]
        assert "朋友" in resolve_faces(card, cedict).front_sentence

    def test_cloze_build_drops_word_only_cards(self, cedict, tmp_path, capsys):
        cards = create_wordlist_cards(
            [WordListEntry("学习", sentence="我喜欢学习汉语。"), WordListEntry("朋友")],
            cedict=cedict,
        )
        out = tmp_path / "deck.apkg"
        build_deck("Cloze", cards, cedict, str(out), cloze=True)
        assert out.exists()
        assert "skipped 1 card" in capsys.readouterr().out


class TestWordlistCli:
    @pytest.mark.parametrize(
        "extra",
        [["--hsk", "3"], ["--review", "r.csv"], ["--top-words", "10"], ["--stats", "s.json"]],
    )
    def test_incompatible_flags_rejected(self, monkeypatch, extra):
        monkeypatch.setattr(sys, "argv", ["main.py", "--wordlist", "hsk1.txt", *extra])
        with pytest.raises(SystemExit) as exc:
            main.main()
        assert exc.value.code == 2

    def test_builds_deck_without_book(self, monkeypatch, tmp_path, cedict):
        wordlist = _write(tmp_path, "HSK 1.csv", "word,definition\n爱,to love\n朋友,\n")
        known = _write(tmp_path, "known.txt", "爱\n")
        monkeypatch.setattr(main, "load_cedict", lambda: cedict)
        # No sentences anywhere -> the translation system must not be loaded.
        monkeypatch.setattr(
            main, "init_translation_manager", lambda *a, **k: pytest.fail("translator loaded")
        )
        monkeypatch.setattr(
            sys,
            "argv",
            ["main.py", "-w", str(wordlist), "-o", str(tmp_path), "--known-words", str(known)],
        )

        main.main()

        assert (tmp_path / "HSK 1.apkg").exists()
