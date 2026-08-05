"""Browser round-trip tests for the editable review page.

These drive a real headless Chromium, because the CSV writer in the page is
JavaScript and cannot be reached from plain pytest -- and its quoting is the
highest-risk code in the feature (CC-CEDICT definitions routinely contain
commas and quotes).

Skipped unless Playwright and its browser binary are installed:
    uv sync && uv run playwright install chromium
Run them deliberately with:  uv run pytest tests/ -m browser
"""

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from anki.review_ui import export_cards_to_review_ui  # noqa: E402
from process.cedict_loader import DictEntry  # noqa: E402
from process.review import load_cards_from_csv  # noqa: E402
from process.word_selector import WordCard  # noqa: E402

pytestmark = pytest.mark.browser

FAKE_CEDICT = {
    "你好": DictEntry("你好", "你好", "ni3 hao3", ["hello"]),
    "世界": DictEntry("世界", "世界", "shi4 jie4", ["world"]),
}


def make_cards():
    return [
        WordCard(
            word="你好",
            sentence="你好，这个世界很大。",
            frequency=5,
            chapter="第一章",
            sentence_translation="Hello, this world is big.",
            sentence_pinyin="nǐ hǎo, zhè ge shì jiè hěn dà.",
            definition='greeting, "hi", or hello',  # comma AND quotes on purpose
        ),
        WordCard(
            word="世界",
            sentence="这个世界非常有趣。",
            frequency=3,
            chapter="第二章",
            sentence_translation="This world is very interesting.",
            sentence_pinyin="zhè ge shì jiè fēi cháng yǒu qù.",
        ),
    ]


@pytest.fixture
def page_for(tmp_path):
    """Open a generated review page in headless Chromium."""
    created = {}

    def _open(cards, cloze=False):
        html_path = export_cards_to_review_ui(
            cards,
            tmp_path / "review.html",
            cedict=FAKE_CEDICT,
            deck_name="Test Deck",
            cloze=cloze,
        )
        playwright = sync_api.sync_playwright().start()
        # uv sync installs playwright for everyone, but the ~115MB browser
        # binary is a separate opt-in step. Without this guard a fresh
        # checkout fails here instead of skipping.
        try:
            browser = playwright.chromium.launch()
        except sync_api.Error as exc:
            playwright.stop()
            pytest.skip(f"chromium not installed (uv run playwright install chromium): {exc}")
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto(html_path.as_uri())
        created["stack"] = (playwright, browser, context)
        return page

    yield _open

    if "stack" in created:
        playwright, browser, context = created["stack"]
        context.close()
        browser.close()
        playwright.stop()


def download_csv(page, tmp_path, name="out.csv"):
    """Click Download and return the loaded WordCard list plus the CSV path."""
    with page.expect_download() as info:
        page.click("#download")
    target = tmp_path / name
    info.value.save_as(target)
    return load_cards_from_csv(str(target)), target


class TestPageLoads:
    def test_renders_every_card(self, page_for):
        page = page_for(make_cards())
        assert page.locator("article.card").count() == 2

    def test_counter_reports_totals(self, page_for):
        page = page_for(make_cards())
        assert "2 cards" in page.text_content("#counter")
