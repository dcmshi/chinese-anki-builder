"""Translate Chinese sentences using CC-CEDICT word-by-word translation."""

from typing import Dict, List
from process.cedict_loader import DictEntry
from process.tokenizer import tokenize_text


def translate_sentence(sentence: str, cedict: Dict[str, DictEntry]) -> str:
    """
    Translate a Chinese sentence using word-by-word CEDICT lookup.

    This is a basic translation - not grammatically perfect, but gives
    learners a rough understanding of the sentence meaning.

    Args:
        sentence: Chinese sentence to translate
        cedict: CC-CEDICT dictionary

    Returns:
        English translation (word-by-word)
    """
    # Tokenize the sentence
    tokens = tokenize_text(sentence)

    if not tokens:
        return ""

    # Chinese grammatical particles that often don't need translation or need special handling
    particles = {
        "的": "",  # Possessive/descriptive particle
        "了": "",  # Completion/change of state (handled contextually)
        "着": "",  # Progressive aspect
        "过": "",  # Experiential aspect
        "吗": "?",  # Question particle
        "呢": "?",  # Question particle
        "吧": "",  # Suggestion particle
        "啊": "",  # Exclamation
        "呀": "",  # Exclamation
        "嘛": "",  # Obviousness particle
    }

    # Translate each token
    translations = []
    for i, token in enumerate(tokens):
        # Check if it's a particle
        if token in particles:
            particle_trans = particles[token]
            if particle_trans:
                translations.append(particle_trans)
            continue

        if token in cedict:
            # Get first (primary) definition
            definition = cedict[token].get_first_definition()

            # Clean up the definition
            # Remove grammatical notes in parentheses/brackets
            definition = definition.split('(')[0].strip()
            definition = definition.split('[')[0].strip()

            # Take first meaning if multiple are separated by comma or semicolon
            definition = definition.split(',')[0].strip()
            definition = definition.split(';')[0].strip()

            # Remove "to " prefix for verbs to make translation more natural
            if definition.startswith("to "):
                definition = definition[3:]

            translations.append(definition)
        else:
            # Keep original token if no translation found (likely a name)
            translations.append(token)

    # Join with spaces and clean up
    translation = " ".join(translations)

    return translation


def improve_translation(translation: str) -> str:
    """
    Apply basic improvements to word-by-word translation.

    Args:
        translation: Raw word-by-word translation

    Returns:
        Slightly improved translation
    """
    result = translation

    # Common improvements
    improvements = {
        " of ": " ",
        " 's ": "'s ",
        "  ": " ",  # Double spaces
        " ? ": "? ",  # Clean up question marks
        " ?": "?",
    }

    for old, new in improvements.items():
        result = result.replace(old, new)

    # Fix common patterns
    # Pattern: "one [classifier] [noun]" -> "a [noun]"
    import re
    result = re.sub(r'\bone (piece|item|one) ', r'a ', result)

    # Remove isolated single-letter particles
    result = re.sub(r'\b[的了着过]\b', '', result)

    # Clean up multiple spaces
    result = re.sub(r'\s+', ' ', result)

    # Capitalize first letter
    result = result.strip()
    if result:
        result = result[0].upper() + result[1:]

    # Ensure proper punctuation at end
    if result and not result[-1] in '.!?。！？':
        result += "."

    return result
