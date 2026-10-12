# this_file: src/vexy_subs/cues.py
"""Sentence-aware cue segmentation that never crosses speaker changes."""

import textwrap

from .types import Cue, Word


def make_cue(words: list[Word]) -> Cue:
    """Lay out existing words into at most two 42-character lines."""
    text = " ".join(w.text.replace("<unk>", "[unk]") for w in words)
    lines = textwrap.wrap(
        text, width=42, break_long_words=False, break_on_hyphens=False
    )
    return Cue(
        words[0].start,
        words[-1].end,
        "\n".join(lines),
        words[0].speaker,
    )


def segment(words: list[Word], max_duration: float = 6.0) -> list[Cue]:
    """Bound reading chunks and split at sentence ends, gaps and speaker changes."""
    cues = []
    group: list[Word] = []
    for index, word in enumerate(words):
        candidate = group + [word]
        lines = textwrap.wrap(
            " ".join(w.text for w in candidate),
            42,
            break_long_words=False,
            break_on_hyphens=False,
        )
        split = group and (
            word.speaker != group[-1].speaker
            or len(lines) > 2
            or word.end - group[0].start > max_duration
            or word.start - group[-1].end > 0.8
        )
        if split:
            if group[-1].end <= group[0].start:
                raise ValueError("Instantaneous token cannot cross a speaker boundary")
            carry = []
            if word.end == word.start and word.speaker == group[-1].speaker:
                while group:
                    carry.insert(0, group.pop())
                    if carry[0].end > carry[0].start:
                        break
            if group:
                cues.append(make_cue(group))
            group = carry
        group.append(word)
        upcoming = words[index + 1] if index + 1 < len(words) else None
        carries_instant = (
            upcoming
            and upcoming.end == upcoming.start
            and upcoming.speaker == word.speaker
        )
        if (
            word.text.endswith((".", "?", "!"))
            and word.end > group[0].start
            and not carries_instant
        ):
            cues.append(make_cue(group))
            group = []
    if group:
        cues.append(make_cue(group))
    # Subword alignment can straddle a display boundary. Keep raw word times.
    adjusted = []
    for index, cue in enumerate(cues):
        end = min(cue.end, cues[index + 1].start) if index + 1 < len(cues) else cue.end
        if end <= cue.start:
            raise ValueError("Nonmonotonic cue timing; inspect raw alignment")
        adjusted.append(Cue(cue.start, end, cue.text, cue.speaker))
    return adjusted
