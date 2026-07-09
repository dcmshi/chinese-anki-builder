"""Anki card templates for Chinese learning."""

import genanki

# Model IDs - random but fixed for consistency
CHINESE_MODEL_ID = 1607392319
CHINESE_CLOZE_MODEL_ID = 1607392320

# Card template. The Sentence field carries inline HTML highlighting of the
# target word (see anki.deck_builder.highlight_word_in_sentence), so the front
# is just the sentence -- word, pinyin, and meaning are revealed on the back.
FRONT_TEMPLATE = """
<div class="sentence">{{Sentence}}</div>
"""

BACK_TEMPLATE = """
<div class="sentence">{{Sentence}}</div>
{{#SentencePinyin}}
<div class="sentence-pinyin">{{SentencePinyin}}</div>
{{/SentencePinyin}}
<div class="word-highlight">{{Word}}</div>

<hr>

<div class="pinyin">{{Pinyin}}</div>
<div class="definition">{{Definition}}</div>

{{#SentenceTranslation}}
<div class="sentence-translation">{{SentenceTranslation}}</div>
{{/SentenceTranslation}}

{{#Audio}}
<div class="audio">{{Audio}}</div>
{{/Audio}}

{{#Chapter}}
<div class="chapter-tag">Chapter: {{Chapter}}</div>
{{/Chapter}}
"""

# CSS styling - Optimized for Anki's dark background
CARD_CSS = """
.card {
    font-family: "Noto Sans CJK SC", "Microsoft YaHei", SimHei, sans-serif;
    font-size: 24px;
    text-align: center;
    color: #d0d0d0;
    background-color: #2b2b2b;
    padding: 20px;
}

.sentence {
    font-size: 28px;
    line-height: 1.6;
    margin-bottom: 10px;
    color: #e8e8e8;
}

.sentence-pinyin {
    font-size: 18px;
    color: #b8b8b8;
    margin-bottom: 15px;
    font-style: italic;
    line-height: 1.4;
}

.word-highlight {
    font-size: 32px;
    font-weight: bold;
    color: #ff6b6b;
    margin: 15px 0;
}

/* Target word highlighted inline within the example sentence */
.target {
    color: #ff6b6b;
    font-weight: bold;
}

/* Anki cloze deletions share the highlight color */
.cloze {
    color: #ff6b6b;
    font-weight: bold;
}

.pinyin {
    font-size: 20px;
    color: #a8a8a8;
    margin: 10px 0;
    font-style: italic;
}

.definition {
    font-size: 18px;
    color: #d0d0d0;
    margin: 15px 0;
    line-height: 1.4;
}

.sentence-translation {
    font-size: 16px;
    color: #c0c0c0;
    margin: 15px 0;
    padding: 10px;
    background-color: #3a3a3a;
    border-left: 3px solid #ff6b6b;
    line-height: 1.5;
    font-style: italic;
}

.chapter-tag {
    font-size: 14px;
    color: #888;
    margin-top: 20px;
    font-style: italic;
}

hr {
    border: none;
    border-top: 1px solid #555;
    margin: 20px 0;
}
"""


# Cloze card: the sentence with the target word blanked out on the front,
# full details on the back.
CLOZE_FRONT_TEMPLATE = """
<div class="sentence">{{cloze:Text}}</div>
"""

CLOZE_BACK_TEMPLATE = """
<div class="sentence">{{cloze:Text}}</div>
{{#SentencePinyin}}
<div class="sentence-pinyin">{{SentencePinyin}}</div>
{{/SentencePinyin}}

<hr>

<div class="word-highlight">{{Word}}</div>
<div class="pinyin">{{Pinyin}}</div>
<div class="definition">{{Definition}}</div>

{{#SentenceTranslation}}
<div class="sentence-translation">{{SentenceTranslation}}</div>
{{/SentenceTranslation}}

{{#Audio}}
<div class="audio">{{Audio}}</div>
{{/Audio}}

{{#Chapter}}
<div class="chapter-tag">Chapter: {{Chapter}}</div>
{{/Chapter}}
"""


def get_chinese_cloze_model():
    """
    Create and return the Anki cloze model for Chinese sentence cards.

    Returns:
        genanki.Model (cloze type) for word-blanked sentence cards
    """
    return genanki.Model(
        CHINESE_CLOZE_MODEL_ID,
        "Chinese Word Cloze",
        model_type=genanki.Model.CLOZE,
        fields=[
            {"name": "Text"},
            {"name": "Word"},
            {"name": "Pinyin"},
            {"name": "Definition"},
            {"name": "SentencePinyin"},
            {"name": "SentenceTranslation"},
            {"name": "Audio"},
            {"name": "Chapter"},
        ],
        templates=[
            {
                "name": "Cloze",
                "qfmt": CLOZE_FRONT_TEMPLATE,
                "afmt": CLOZE_BACK_TEMPLATE,
            },
        ],
        css=CARD_CSS,
    )


def get_chinese_model():
    """
    Create and return the Anki model for Chinese cards.

    Returns:
        genanki.Model configured for Chinese word cards
    """
    model = genanki.Model(
        CHINESE_MODEL_ID,
        "Chinese Word in Sentence",
        fields=[
            {"name": "Word"},
            {"name": "Sentence"},
            {"name": "SentencePinyin"},
            {"name": "Pinyin"},
            {"name": "Definition"},
            {"name": "SentenceTranslation"},
            {"name": "Audio"},
            {"name": "Chapter"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": FRONT_TEMPLATE,
                "afmt": BACK_TEMPLATE,
            },
        ],
        css=CARD_CSS,
    )

    return model
