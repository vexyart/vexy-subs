# this_file: src/vexy_subs/typography.py
"""Conservative language-specific disfluency removal and Unicode typography."""

import re
import unicodedata
from dataclasses import replace

from .types import Word

FILLERS = {
    "en": {"uh", "uhh", "uhm", "um", "umm", "erm", "er", "err", "hmm"},
    "de": {"äh", "ähm", "öh", "hm"},
    "fr": {"euh", "heu", "hum"},
    "pl": {"yyy", "eee", "eem", "hmm"},
    "es": {"eh", "em", "mmm"},
    "it": {"ehm", "uhm", "mmm"},
    "nl": {"eh", "ehm", "uhm"},
    "pt": {"ahn", "hum", "hã"},
}
# Repeated auxiliaries/function words are likely restarts; preserve intensifiers,
# negatives, names and syntactically valid "had had" / "that that".
RESTARTS = {
    "en": {
        "i",
        "we",
        "you",
        "he",
        "she",
        "they",
        "a",
        "an",
        "the",
        "to",
        "and",
        "but",
        "so",
        "of",
        "in",
        "on",
        "it",
        "is",
        "are",
        "was",
        "were",
    },
    "de": {
        "ich",
        "wir",
        "du",
        "er",
        "sie",
        "ein",
        "eine",
        "der",
        "die",
        "das",
        "und",
        "oder",
    },
    "fr": {"je", "nous", "vous", "il", "elle", "le", "la", "les", "et", "ou"},
    "pl": {"ja", "my", "ty", "on", "ona", "i", "ale", "że"},
    "es": {"yo", "nosotros", "el", "la", "los", "las", "y", "pero"},
    "it": {"io", "noi", "il", "la", "gli", "le", "e", "ma"},
    "nl": {"ik", "wij", "je", "hij", "zij", "de", "het", "en", "maar"},
    "pt": {"eu", "nós", "ele", "ela", "o", "a", "os", "as", "e", "mas"},
}
QUOTES = {
    "de": ("„", "“", "‚", "‘"),
    "pl": ("„", "”", "‚", "’"),
    "fr": ("«\u202f", "\u202f»", "“", "”"),
    "ru": ("«", "»", "„", "“"),
    "it": ("«", "»", "‘", "’"),
    "es": ("«", "»", "‘", "’"),
    "pt": ("«", "»", "‘", "’"),
    "ja": ("「", "」", "『", "』"),
    "zh": ("“", "”", "‘", "’"),
}
KEEP_REPETITIONS = {
    "en": {"very", "really", "much", "more", "less", "no", "yes", "had", "that", "so"},
    "de": {"sehr", "nicht", "ja", "nein"},
    "fr": {"très", "non", "oui"},
    "pl": {"bardzo", "nie", "tak"},
    "es": {"muy", "no", "sí"},
    "it": {"molto", "no", "sì"},
    "nl": {"heel", "nee", "ja"},
    "pt": {"muito", "não", "sim"},
}


def lexical(text: str) -> str:
    """Compare lexical tokens without deleting punctuation inside identifiers."""
    return text.strip(".,;:!?…“”„«»\"'()[] -—").casefold()


def typograph(text: str, language: str) -> str:
    """Normalize typography on a whole speaker run so quotes can span cues."""
    text = unicodedata.normalize("NFC", text)
    text = re.sub("[“”„«»]", '"', text)
    text = re.sub(r"(?<=\w)['’](?=\w)", "’", text)
    text = re.sub(r"\.{3,}", "…", text)
    text = re.sub(r"\s*--\s*", " — ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    opening, closing, single_open, single_close = QUOTES.get(
        language, ("“", "”", "‘", "’")
    )
    double = False
    single = False
    result = []
    for index, char in enumerate(text):
        if char == '"':
            result.append(closing if double else opening)
            double = not double
        elif char == "'":
            # Leading elisions such as 'tis and '90s are apostrophes, not quotes.
            tail = text[index + 1 :]
            elision = bool(
                re.match(r"(?:\d{2}s|tis\b|twas\b|cause\b|em\b)", tail, re.IGNORECASE)
            )
            result.append("’" if elision else single_close if single else single_open)
            if not elision:
                single = not single
        else:
            result.append(char)
    text = "".join(result)
    if language == "fr":
        text = re.sub(r"\s*([;!?])", "\u202f" + r"\1", text)
        text = re.sub(r"\s*:(?!\d)", "\u00a0:", text)
    return text


def clean_words(words: list[Word], language: str) -> tuple[list[Word], list[dict]]:
    """Copy timed words; record every deletion, never cross a speaker boundary."""
    result, edits, origins = [], [], []
    for index, word in enumerate(words):
        token = lexical(word.text)
        filler = token in FILLERS.get(language, set())
        previous = result[-1] if result else None
        duplicate = bool(
            previous
            and previous.speaker == word.speaker
            and word.start - previous.end <= 0.5
            and lexical(previous.text) == token
            and not previous.text.endswith((".", "?", "!"))
            and (
                token in RESTARTS.get(language, set())
                or (token == "that" and previous.text.endswith(","))
                or (
                    language in KEEP_REPETITIONS
                    and token not in KEEP_REPETITIONS[language]
                    and not word.text[:1].isupper()
                    and not any(char.isdigit() for char in token)
                )
            )
        )
        if filler or duplicate:
            edits.append(
                {
                    "index": index,
                    "text": word.text,
                    "start": word.start,
                    "end": word.end,
                    "speaker": word.speaker,
                    "reason": "filler" if filler else "restart",
                }
            )
            if duplicate and previous:
                previous.end = max(previous.end, word.end)
                previous.text = previous.text.rstrip(".,!?;:")
                if word.text.endswith((".", "?", "!", ",", ";", ":")):
                    previous.text = previous.text.rstrip(".,!?;:") + word.text[-1]
            continue
        result.append(replace(word))
        origins.append(index)
    index = 0
    while index < len(result):
        collapsed = False
        for width in range(4, 1, -1):
            first, second = (
                result[index : index + width],
                result[index + width : index + 2 * width],
            )
            if len(second) != width:
                continue
            if (
                first[-1].text.endswith((",", "-", "—"))
                and lexical(first[0].text)
                not in {"thank", "thanks", "please", "sorry", "yes", "no"}
                and all(w.speaker == first[0].speaker for w in first + second)
                and second[0].start - first[-1].end <= 0.5
                and [lexical(w.text) for w in first]
                == [lexical(w.text) for w in second]
                and any(lexical(w.text) in RESTARTS.get(language, set()) for w in first)
                and not any(w.text.endswith((".", "?", "!")) for w in first)
            ):
                for position, word in enumerate(second, index + width):
                    edits.append(
                        {
                            "index": origins[position],
                            "text": word.text,
                            "start": word.start,
                            "end": word.end,
                            "speaker": word.speaker,
                            "reason": "phrase_restart",
                        }
                    )
                first[-1].end = max(first[-1].end, second[-1].end)
                first[-1].text = second[-1].text
                del result[index + width : index + 2 * width]
                del origins[index + width : index + 2 * width]
                collapsed = True
                break
        if not collapsed:
            index += 1
    return result, edits
