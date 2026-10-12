# this_file: src/vexy_subs/layout.py
"""Measured proportional-font balancing with language-aware boundary penalties."""

from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from .typography import lexical

GLUE = {
    "en": {
        "a",
        "an",
        "the",
        "this",
        "that",
        "these",
        "those",
        "my",
        "your",
        "our",
        "his",
        "her",
        "its",
        "their",
        "i",
        "we",
        "you",
        "he",
        "she",
        "they",
        "am",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "have",
        "has",
        "had",
        "will",
        "would",
        "can",
        "could",
        "should",
        "must",
        "not",
        "very",
        "more",
        "most",
        "to",
        "of",
        "in",
        "on",
        "at",
        "with",
        "from",
        "for",
        "by",
    },
    "de": {
        "der",
        "die",
        "das",
        "ein",
        "eine",
        "einer",
        "einem",
        "den",
        "dem",
        "des",
        "ich",
        "wir",
        "du",
        "er",
        "sie",
        "es",
        "nicht",
        "ist",
        "sind",
        "hat",
        "haben",
        "zu",
        "mit",
        "von",
        "für",
    },
    "fr": {
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "du",
        "de",
        "je",
        "tu",
        "il",
        "elle",
        "nous",
        "vous",
        "ils",
        "elles",
        "ne",
        "pas",
        "est",
        "sont",
        "à",
        "au",
        "avec",
    },
    "pl": {
        "ten",
        "ta",
        "to",
        "te",
        "ja",
        "ty",
        "my",
        "wy",
        "on",
        "ona",
        "nie",
        "do",
        "od",
        "na",
        "w",
        "z",
        "ze",
        "dla",
    },
    "es": {
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "yo",
        "tú",
        "él",
        "ella",
        "no",
        "de",
        "a",
        "con",
        "para",
    },
    "it": {
        "il",
        "lo",
        "la",
        "gli",
        "le",
        "un",
        "una",
        "io",
        "tu",
        "lui",
        "lei",
        "non",
        "di",
        "a",
        "con",
        "per",
    },
    "nl": {
        "de",
        "het",
        "een",
        "ik",
        "wij",
        "jij",
        "hij",
        "zij",
        "niet",
        "van",
        "met",
        "voor",
    },
    "pt": {
        "o",
        "a",
        "os",
        "as",
        "um",
        "uma",
        "eu",
        "tu",
        "ele",
        "ela",
        "não",
        "de",
        "da",
        "do",
        "com",
        "para",
    },
}
BOUNDARY = {
    "en": {
        "and",
        "but",
        "or",
        "because",
        "although",
        "while",
        "if",
        "when",
        "before",
        "after",
        "to",
        "of",
        "in",
        "on",
        "with",
        "for",
        "from",
    },
    "de": {"und", "aber", "oder", "weil", "wenn", "mit", "von", "für"},
    "fr": {"et", "mais", "ou", "car", "quand", "avec", "pour", "dans"},
    "pl": {"i", "ale", "lub", "bo", "ponieważ", "gdy", "w", "na", "z", "do"},
    "es": {"y", "pero", "o", "porque", "cuando", "con", "para", "en"},
    "it": {"e", "ma", "o", "perché", "quando", "con", "per"},
    "nl": {"en", "maar", "of", "omdat", "wanneer", "met", "voor"},
    "pt": {"e", "mas", "ou", "porque", "quando", "com", "para"},
}


@lru_cache(maxsize=8)
def font_metrics(path: str = ""):
    """Use Arial when installed; otherwise Pillow's reproducible bundled font."""
    candidates = (
        [path]
        if path
        else [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, 46)
    if path:
        raise FileNotFoundError(f"Subtitle measurement font missing: {path}")
    return ImageFont.load_default(size=46)


def boundary_cost(
    left: str, right: str, language: str, left_tag: str = "", right_tag: str = ""
) -> float:
    """Prefer clause starts, avoiding determiners/auxiliaries and proper-name splits."""
    a, b = lexical(left), lexical(right)
    if left.endswith((".", "?", "!", "…", ",", ";", ":")):
        return 0
    cost = (
        1000
        if a in GLUE.get(language, set())
        or a
        in {
            "and",
            "but",
            "or",
            "because",
            "although",
            "if",
            "when",
            "it's",
            "it’s",
            "i’m",
            "i'm",
            "we’re",
            "we're",
            "they’re",
            "they're",
        }
        else 3
    )
    if (
        (left_tag.startswith(("DT", "JJ")) and right_tag.startswith(("JJ", "NN")))
        or (left_tag == "PRP" and right_tag.startswith(("VB", "MD")))
        or (left_tag in {"MD", "TO"} and right_tag.startswith("VB"))
        or (left_tag.startswith("NNP") and right_tag.startswith("NNP"))
        or (left_tag.startswith("RB") and right_tag.startswith(("VB", "JJ", "RB")))
    ):
        cost += 24
    if b in BOUNDARY.get(language, set()):
        cost -= 3
    if left[:1].isupper() and right[:1].isupper():
        cost += 12
    # Common adjective morphology protects adjective+noun groups without a parser.
    if language == "en" and a.endswith(
        ("ful", "less", "ous", "ive", "able", "ible", "al")
    ):
        cost += 8
    return max(0, cost)


@lru_cache(maxsize=65536)
def token_width(token: str, font: str) -> float:
    """Cache measured advances per token; preserve proportional glyph widths."""
    return font_metrics(font).getlength(token)


@lru_cache(maxsize=32768)
def balanced_lines(
    text: str,
    language: str,
    limit: int = 42,
    font: str = "",
    tags: tuple[str, ...] = (),
) -> str:
    """Choose the least disruptive two-line split using actual rendered advances."""
    if len(text) <= limit:
        return text
    tokens = text.split(" ")
    widths = [token_width(token, font) for token in tokens]
    space = token_width(" ", font)
    total = sum(widths) + space * (len(tokens) - 1)
    left_width = -space
    choices = []
    for index in range(1, len(tokens)):
        left_width += widths[index - 1] + space
        left, right = " ".join(tokens[:index]), " ".join(tokens[index:])
        if max(len(left), len(right)) > limit:
            continue
        a, b = left_width, total - left_width - space
        imbalance = abs(a - b) / max(a, b, 1)
        # Phrase integrity has priority; severe orphan lines remain expensive.
        cost = (
            boundary_cost(
                tokens[index - 1],
                tokens[index],
                language,
                tags[index - 1] if tags else "",
                tags[index] if tags else "",
            )
            + 12 * imbalance**2
        )
        if min(a, b) / max(a, b, 1) < 0.35:
            cost += 15
        choices.append((cost, left + "\n" + right))
    if not choices:
        raise ValueError("Text cannot fit two subtitle lines without splitting a word")
    return min(choices)[1]
