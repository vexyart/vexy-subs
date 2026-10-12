# this_file: src/vexy_subs/editorial.py
"""Remove English discourse padding while protecting literal uses and word times."""

from collections import Counter
from dataclasses import replace

from .punctuation import FUNCTION_WORDS
from .types import Word
from .typography import lexical

LITERAL_KIND = {
    "a",
    "the",
    "this",
    "that",
    "what",
    "which",
    "any",
    "some",
    "same",
    "each",
    "every",
    "different",
    "another",
    "new",
    "specific",
    "certain",
    "these",
    "those",
    "one",
    "particular",
    "other",
    "such",
    "all",
    "anyother",
}
COMMON = FUNCTION_WORDS | {
    "is",
    "are",
    "was",
    "were",
    "be",
    "being",
    "been",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "can",
    "could",
    "will",
    "would",
    "should",
    "must",
    "not",
    "just",
    "also",
    "only",
    "really",
    "very",
    "much",
    "more",
    "most",
    "about",
    "into",
    "out",
    "up",
    "down",
    "all",
    "some",
    "any",
    "something",
    "everything",
    "nothing",
    "let",
    "let’s",
    "let's",
    "it's",
    "it’s",
    "that's",
    "that’s",
    "there's",
    "there’s",
    "we're",
    "we’re",
    "you're",
    "you’re",
    "almost",
    "even",
    "still",
    "maybe",
    "instead",
    "rather",
    "however",
    "therefore",
}


def discourse(words: list[Word]) -> tuple[list[Word], list[dict]]:
    """Delete padding and immediate restarts, preserving answers and literal phrases."""
    result, edits = [], []
    index = 0
    while index < len(words):
        word = words[index]
        token = lexical(word.text)
        previous = words[index - 1] if index else None
        following = words[index + 1] if index + 1 < len(words) else None
        start = (
            not previous
            or previous.speaker != word.speaker
            or previous.text.endswith((".", "?", "!"))
        )
        width, reason = 0, "discourse_filler"
        if (
            following
            and following.speaker == word.speaker
            and token in {"yes", "yeah", "okay", "ok"}
            and lexical(following.text) == token
            and word.text.endswith(",")
        ):
            width, reason = 1, "restart"
        elif token == "basically":
            width = 1
        elif (
            token in {"yeah", "okay", "ok", "well"}
            and word.text.endswith(",")
            and (start or (previous and previous.text.endswith(",")))
        ):
            # Complete responses stay; comma-delimited conversational padding goes.
            width = (
                1 if following and not following.text.endswith((".", "?", "!")) else 0
            )
        elif token in {"so", "like"} and word.text.endswith(","):
            width = 1 if following and (start or token == "like") else 0
        elif (
            following
            and following.speaker == word.speaker
            and following.start - word.end < 0.8
        ):
            pair = (token, lexical(following.text))
            after = words[index + 2] if index + 2 < len(words) else None
            if pair in {("kind", "of"), ("sort", "of")}:
                # A noun phrase ("this kind of font") is not a hesitation hedge.
                context = words[max(0, index - 3) : index]
                article = any(lexical(w.text) in {"a", "an", "the"} for w in context)
                if (
                    previous
                    and lexical(previous.text) not in LITERAL_KIND
                    and not article
                    and after
                ):
                    width = 2
            elif (
                pair in {("you", "know"), ("i", "mean")}
                and following.text.endswith(",")
                and (
                    not previous
                    or previous.text.endswith(",")
                    or lexical(previous.text)
                    not in {
                        "what",
                        "that",
                        "whether",
                        "if",
                        "do",
                        "did",
                        "does",
                        "can",
                        "could",
                        "would",
                        "will",
                        "should",
                        "everything",
                        "all",
                        "things",
                        "something",
                        "how",
                        "who",
                    }
                )
            ):
                width = 2
        if not width:
            for size in range(8, 1, -1):
                first = words[index : index + size]
                second = words[index + size : index + size * 2]
                if len(second) != size:
                    continue
                if (
                    all(w.speaker == word.speaker for w in first + second)
                    and second[0].start - first[-1].end <= 0.5
                    and not any(w.text.endswith((".", "?", "!")) for w in first)
                    and [lexical(w.text) for w in first]
                    == [lexical(w.text) for w in second]
                    and token
                    not in {
                        "thank",
                        "thanks",
                        "please",
                        "sorry",
                        "yes",
                        "no",
                        "very",
                        "really",
                    }
                    and not any(any(c.isdigit() for c in w.text) for w in first)
                ):
                    width, reason = size, "phrase_restart"
                    break
        if width:
            removed = words[index : index + width]
            edits.extend(
                {
                    "index": index + i,
                    "text": w.text,
                    "start": w.start,
                    "end": w.end,
                    "speaker": w.speaker,
                    "reason": reason,
                }
                for i, w in enumerate(removed)
            )
            if result and result[-1].speaker == word.speaker:
                terminal = removed[-1].text[-1:]
                if terminal in {".", "?", "!"} and not result[-1].text.endswith(
                    (".", "?", "!")
                ):
                    result[-1].text = result[-1].text.rstrip(",;:") + terminal
                elif token in {"you", "i", "like"} and reason == "discourse_filler":
                    result[-1].text = result[-1].text.rstrip(",")
            index += width
        else:
            result.append(replace(word))
            index += 1
    return result, edits


def sentence_case(words: list[Word]) -> list[Word]:
    """Capitalize sentence starts, normalize function words, retain names and acronyms."""
    lower = Counter(lexical(w.text) for w in words if w.text[:1].islower())
    upper = Counter(lexical(w.text) for w in words if w.text[:1].isupper())
    result = []
    for index, original in enumerate(words):
        word = replace(original)
        previous = result[-1] if result else None
        if (
            previous
            and previous.speaker == word.speaker
            and previous.text.endswith(",")
            and lexical(word.text) in {"thank", "thanks"}
        ):
            previous.text = previous.text[:-1] + "."
        start = (
            not previous
            or previous.speaker != word.speaker
            or previous.text.rstrip("”\"')]").endswith((".", "?", "!"))
        )
        token = lexical(word.text)
        if (
            not start
            and (
                token in COMMON
                or (lower[token] >= 5 and lower[token] > upper[token] * 4)
            )
            and not word.text.isupper()
            and not any(c.isupper() for c in word.text[1:])
        ):
            word.text = word.text.lower()
        if token == "i" or token.startswith(("i’", "i'")):
            word.text = word.text[:1].upper() + word.text[1:]
        if start:
            for position, char in enumerate(word.text):
                if char.isalpha():
                    word.text = (
                        word.text[:position] + char.upper() + word.text[position + 1 :]
                    )
                    break
        result.append(word)
    for index, word in enumerate(result):
        following = result[index + 1] if index + 1 < len(result) else None
        if (
            word.text.endswith(",")
            and lexical(word.text)
            in {"yes", "no", "yeah", "okay", "ok", "nice", "excellent", "nevermind"}
            and (
                not following
                or following.speaker != word.speaker
                or following.start - word.end > 0.5
            )
        ):
            word.text = word.text[:-1] + "."
            if following and following.text:
                following.text = following.text[:1].upper() + following.text[1:]
    return result
